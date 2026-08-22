"""V1 front end, part 2: grounding-schema proposals from an LLM.

The LLM sees the mention catalog and a sample of observed dynamics and proposes
how surface slots map onto latent entity types, attributes, references and
view contexts. Proposals are hypotheses: they are applied by the grounder and
validated against the evidence (coherence) and by interventions; nothing the
LLM says about semantics is trusted without interaction evidence.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.mentions import Catalog
from semabi.llm import ask, extract_json

SCHEMA_DOC = """Return ONE JSON object (no prose) with this structure:
{
 "types": [{"name": "<EntityType>", "key": "<attribute that identifies an entity across views>",
            "attrs": {"<attr>": "str"|"int"|"bool", ...}}],
 "units": {
   "<unit id>": {"type": "<EntityType>" | null,   // null: the unit is not an entity listing (e.g. a table header row, a wizard picker whose items use "picks")
                 "presence": "all" | "subset",     // does this unit list ALL entities of the type when shown, or only some (e.g. only the ones related to something)?
                 "slots": {
                   "<slot id>": {"attr": "<attr>", "transform": "<transform>", "ignore": ["<value>", ...]}
                               | {"ref": {"type": "<EntityType>", "attr": "<attr of the referenced entity shown here>"}, "relation": "<relation name>", "transform": "<transform>", "ignore": ["—", ...]}
                               | {"presence_attr": "<bool attr>"}      // the slot (e.g. a button) is present only when the attribute is true
                               | {"picks": [{"type": "<EntityType>", "attr": "<attr>", "transform": "<transform>"}, ...]}   // a picker/option list: clicking this slot selects the entity whose attribute equals the (transformed) text; give one alternative per entity type the list can show (e.g. a wizard reusing one list for several steps)
                               | {"ignore": true}                        // a label or control with no entity meaning
                 }}
 },
 "statics": {
   "<slot id>": {"context_ref": {"type": "<EntityType>", "attr": "<attr>"}, "transform": "<transform>"}   // a top-level slot showing which entity is currently selected / in focus
               | {"entity": {"type": "<EntityType>", "attr": "<attr>"}, "transform": "<transform>"}        // a top-level slot that IS a mention of an entity (e.g. one tab button per container object)
               | {"ignore": true}
 },
 "correspondences": [{"type": "<EntityType>", "attr": "<attr shown in some views>", "key_pairs": {"<attr value>": ["<key value>", ...]}}],
 "view_families": [{"views": ["<family view name>", ...], "parameter_type": "<EntityType>", "attr": "<attr the button label shows>",
                    "units": {"<unit id>": "<relation name>"}}],   // a FAMILY view (same screen, one button per entity) is parameterised by the entity whose attribute the button label shows; the listed units show entities related to that entity by the given relation
 "notes": "<short free text: anything uncertain, e.g. which attributes look mutable, what the wizard does>"
}
Transforms (apply to the raw slot text before interpreting it): "none", "number" (first integer in the text),
"strip_star" (remove a trailing ' *'), "before_paren" (text before ' ('), "in_paren" (text inside parentheses),
"after_space" (text after the first space), "before_slash" (text before ' /'), "after_slash" (text after '/ '),
"after_dot" (text after '· '). Use "ignore" lists for header/placeholder values (e.g. 'slot', 'deep', '—').
Rules: every entity type must have a key attribute that is shown directly in at least one unit OR reachable through a
correspondence from an attribute shown there. Attribute names are yours. Relations are functional (each source entity
has at most one target). Only describe what the catalog supports; put speculation in "notes"."""


def dynamics_sample(log: EvidenceLog, cat: Catalog, rng: random.Random, k: int = 60) -> str:
    """Compact per-step change descriptions in catalog vocabulary."""
    lines = []
    steps = [s for s in log.steps if s.action.kind not in ("reset",)]
    chosen = steps if len(steps) <= k else sorted(rng.sample(steps, k), key=lambda s: s.step)
    view_before = None
    for s in chosen:
        vb = cat.view_of_step.get(s.step - 1, cat.initial_view) if s.step > 0 else cat.initial_view
        va = cat.view_of_step.get(s.step, vb)
        pb, pa = cat.parse(log.obs(s.before), vb), cat.parse(log.obs(s.after), va)
        act = str(s.action)
        if s.action.target is not None and s.action.target_desc:
            # locate the clicked node's mention
            for m in pb.mentions:
                if m.node == s.action.target:
                    where = f"{m.sid}" + (f" of {m.unit}#{m.unit_index} (value {m.value!r})" if m.unit else f" (static, value {m.value!r})")
                    act = f"{s.action.kind} {where}" + (f" text={s.action.text!r}" if s.action.kind in ('type', 'select') else "")
                    break
        def keyed(pm):
            out = {}
            for m in pm.mentions:
                out.setdefault((m.unit, m.unit_index), {})[m.sid] = m.value
            return out
        kb, ka = keyed(pb), keyed(pa)
        changes = []
        for key in sorted(set(kb) | set(ka), key=str):
            b, a = kb.get(key), ka.get(key)
            if b == a:
                continue
            name = f"{key[0]}#{key[1]}" if key[0] else "statics"
            if b is None:
                changes.append(f"+{name}{a}")
            elif a is None:
                changes.append(f"-{name}{b}")
            else:
                diff = {k2: (b.get(k2), a.get(k2)) for k2 in set(b) | set(a) if b.get(k2) != a.get(k2)}
                changes.append(f"{name}{diff}")
        ch = "; ".join(changes)[:400] if changes else "(no change)"
        lines.append(f"[{vb}->{va}] {act}{'' if s.ok else ' (FAILED)'}: {ch}")
    return "\n".join(lines)


def build_prompt(log: EvidenceLog, cat: Catalog, seed: int = 0) -> str:
    rng = random.Random(seed)
    return "\n".join([
        "You are reverse-engineering the hidden data model of an unknown web application from black-box interaction traces.",
        "Below is a CATALOG of what the page shows: views (switched by static tab buttons), repeated units (rows, cards,",
        "list items) and slots (positions carrying text or widget state) with the values observed, followed by a SAMPLE OF",
        "DYNAMICS (what changed after each primitive action). The same latent entity is often shown differently in",
        "different views (full name in one, a short code in another, an option in a picker elsewhere). Your job is to",
        "propose the latent entity types, which units list them, which slots show which attribute (or a reference to",
        "another entity), which static slots show the currently selected entity, and how representations correspond.",
        "", "=== CATALOG ===", cat.describe(12), "", "=== DYNAMICS SAMPLE ===", dynamics_sample(log, cat, rng), "",
        "=== OUTPUT ===", SCHEMA_DOC])


def propose(run_dir: Path, model: str = "opus", seed: int = 0, cache: bool = True) -> tuple[dict, Catalog]:
    log = EvidenceLog(run_dir)
    cat = Catalog()
    cat.fit_log(log)
    prompt = build_prompt(log, cat, seed)
    (run_dir / "schema_prompt.txt").write_text(prompt)
    text = ask(prompt, model=model, cache_dir=Path("runs/llm_cache") if cache else None)
    (run_dir / "schema_response.txt").write_text(text)
    schema = extract_json(text)
    (run_dir / "schema.json").write_text(json.dumps(schema, indent=1))
    return schema, cat


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--model", default="opus")
    a = ap.parse_args()
    schema, cat = propose(Path(a.run), a.model)
    print(json.dumps(schema, indent=1))
