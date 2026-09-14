"""Narrow questions put to an LLM, whose answers are hypotheses and never facts.

Two kinds are asked. *Aliases*: two unit types show identifiers that never match as strings
but may name the same objects under some transformation (initials, codes, abbreviations); the
model sees both value lists with their label context and returns candidate pairs, each of
which then goes through the co-change verifier. *Subject*: a unit with several identifying
slots, such as a detail panel with a breadcrumb; the model is asked which slot names the
thing the panel's attributes belong to.

Prompts, responses and the model id are cached under runs/llm_cache and written to the run
directory. Nothing the model says is accepted as semantics: an alias is provisional identity
and carries its status with it.
"""
from __future__ import annotations

import json
from pathlib import Path

from semabi.compiler.v2.association import Alias, Associator
from semabi.compiler.v2.hypotheses import Hypotheses, UnitHyp
from semabi.llm import ask, extract_json

ALIAS_SYSTEM = ("You help a program that learns the object model of an unfamiliar web application from the rendered UI. "
                "You are shown identifiers that appear in two different parts of the UI. Decide whether they denote the same "
                "objects under a different naming convention (initials, abbreviation, code, short form). Answer only with JSON. "
                "Do not invent pairs that are not clearly supported by the strings; an empty list is a fine answer.")


def _context(H: Hypotheses, u: UnitHyp, k: int = 3) -> str:
    """Label words around the unit's key slot and sample fillings."""
    G = H.G
    samples = []
    for ui in u.instances[:200]:
        if u.key_slot in ui.slots:
            node = ui.slot_nodes.get(u.key_slot.split("|")[0])
            text = G.obs[ui.sig].node(node).name if node is not None else ""
            samples.append(text)
        if len(set(samples)) >= k:
            break
    return " | ".join(sorted(set(samples))[:k])


def alias_candidates(H: Hypotheses) -> list[tuple[UnitHyp, UnitHyp]]:
    """Pairs of keyed unit types of different entity types whose keys never overlap but have
    comparable cardinality (3-30 values) and non-numeric keys."""
    keyed = [u for u in H.units.values() if u.key_slot and 3 <= len(u.primary_key_values()) <= 30]
    out = []
    for i, a in enumerate(keyed):
        for b in keyed[i + 1:]:
            if H.tid_of_template.get(a.template) == H.tid_of_template.get(b.template):
                continue
            ka, kb = a.primary_key_values(), b.primary_key_values()
            if ka & kb:
                continue
            if all(v[0].isdigit() for v in ka) or all(v[0].isdigit() for v in kb):
                continue
            out.append((a, b))
    # most plausible first: similar cardinality, both carrying attributes
    def plaus(pair):
        a, b = pair
        na, nb = len(a.primary_key_values()), len(b.primary_key_values())
        attrs = min(len(a.slots), len(b.slots))
        return (min(na, nb) / max(na, nb)) + 0.1 * min(attrs, 4)
    out.sort(key=plaus, reverse=True)
    return out


def propose_aliases(H: Hypotheses, run_dir: Path, model: str = "opus", max_pairs: int = 20) -> list[Alias]:
    cands = alias_candidates(H)[:max_pairs]
    out: list[Alias] = []
    log_path = run_dir / "llm_aliases.jsonl"
    for a, b in cands:
        ka, kb = sorted(a.primary_key_values()), sorted(b.primary_key_values())
        prompt = (f"List A (shown as: {_context(H, a)}):\n{json.dumps(ka)}\n\n"
                  f"List B (shown as: {_context(H, b)}):\n{json.dumps(kb)}\n\n"
                  'Return JSON {"pairs": [["a value", "b value"], ...]} with the pairs that name the same object, or {"pairs": []}.')
        try:
            text = ask(prompt, model=model, system=ALIAS_SYSTEM, cache_dir=Path("runs/llm_cache"))
            j = extract_json(text)
        except Exception as e:  # noqa: BLE001 - a failed proposal is no proposal
            with log_path.open("a") as f:
                f.write(json.dumps({"a": a.template[:80], "b": b.template[:80], "error": str(e)[:200]}) + "\n")
            continue
        pairs = [(x, y) for x, y in j.get("pairs", []) if x in ka and y in kb]
        with log_path.open("a") as f:
            f.write(json.dumps({"model": model, "a": a.template[:80], "b": b.template[:80], "prompt": prompt, "response": text, "accepted_pairs": pairs}) + "\n")
        for x, y in pairs:
            out.append(Alias(a.template, x, b.template, y, "UNTESTED", source=f"llm:{model}"))
    return out


def verified_aliases(H: Hypotheses, step_sigs: list[str], run_dir: Path, model: str = "opus") -> list[Alias]:
    """LLM proposals checked against co-change evidence; plus co-change's own discoveries."""
    A = Associator(H, step_sigs)
    A.collect()
    found = A.cochange()
    for al in found:
        a, b = H.units[al.a_template], H.units[al.b_template]
        if (a.primary_key_values() & b.primary_key_values()) or H._same_family(a, b) or \
                H.tid_of_template.get(al.a_template) == H.tid_of_template.get(al.b_template):
            al.status = "REDUNDANT"
    proposed = propose_aliases(H, run_dir, model=model)
    for al in proposed:
        A.verify(al)
        A.aliases[(al.a_template, al.a_key, al.b_template)] = al
    (run_dir / "aliases_v2.txt").write_text(A.report() + "\n")
    # only aliases the interaction record supports are adopted; proposals stay on file
    return [al for al in A.aliases.values() if al.status == "SUPPORTED"]
