"""Baseline: an LLM proposes the semantic model from the (random-phase) evidence
log, in the shared relational language, without any active verification.

The LLM sees exactly what the compiler sees: rendered observations and primitive
actions. Its output is scored with the same structural/behavioural matcher.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from semabi import relmodel as rm
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.model import LearnedModel
from semabi.llm import ask, extract_json

SCHEMA = """Output ONE JSON object with this exact schema (no prose before or after it):
{
 "types": [{"name": "<TypeName>", "attrs": {"<attr>": "str"|"bool"}, "key": "<attr that identifies an object (a str attr)>"}],
 "relations": [{"name": "<rel>", "src": "<TypeName>", "dst": "<TypeName>"}],
 "operators": [{
   "name": "<op>",
   "params": [["?p", "<TypeName>|str"], ...],
   "pre": [ {"kind":"AttrEq","obj":"?p","attr":"<attr>","value":<const>,"negate":false}
          | {"kind":"RelHolds","rel":"<rel>","a":"?p","b":"?q","negate":false}
          | {"kind":"NoIncoming","rel":"<rel>","obj":"?p","negate":false}
          | {"kind":"Distinct","a":"?p","b":""} ],
   "effects": [ {"kind":"Create","type":"<TypeName>","attrs":[["<attr>", "?p or const"], ...],"bind":"?result"}
              | {"kind":"Delete","obj":"?p"}
              | {"kind":"SetAttr","obj":"?p","attr":"<attr>","value":"?p or const"}
              | {"kind":"SetRel","rel":"<rel>","a":"?p","b":"?q"}
              | {"kind":"DeleteIncoming","rel":"<rel>","obj":"?p"}
              | {"kind":"MoveIncoming","rel":"<rel>","src":"?p","dst":"?q"}
              | {"kind":"SetAttrIncoming","rel":"<rel>","obj":"?p","attr":"<attr>","value":<const>} ]
 }]
}
Relations are functional (each src object relates to at most one dst). Every operator must be a distinct semantic
operation of the application (not a UI step). Only include what the evidence supports."""


def build_prompt(log: EvidenceLog, max_steps: int = 120, rng: random.Random | None = None) -> str:
    rng = rng or random.Random(0)
    steps = [s for s in log.steps if s.action.kind not in ("reset",)]
    first = log.obs(log.steps[0].after)
    lines = ["You are reverse-engineering the semantic data model of an unknown web application purely from black-box",
             "interaction traces. You see rendered accessibility trees and primitive actions (click/type/select/reload).",
             "Infer object types, their attributes, relations between types, and the parameterized semantic operators",
             "(with preconditions and effects) that the UI exposes. Names are yours to choose.", "",
             "INITIAL SCREEN:", first.render(), ""]
    chosen = steps[:max_steps] if len(steps) <= max_steps else sorted(rng.sample(steps, max_steps), key=lambda s: s.step)
    lines.append(f"TRACE ({len(chosen)} steps; '+'/'-' are texts that appeared/disappeared; 'reload' tests persistence):")
    for s in chosen:
        b, a = log.obs(s.before), log.obs(s.after)
        plus = sorted(a.texts() - b.texts())
        minus = sorted(b.texts() - a.texts())
        lines.append(f"[ep{s.episode}] {s.action}{'' if s.ok else ' (FAILED)'}  +{plus} -{minus}")
    lines += ["", "A few full screens after actions:"]
    for s in chosen[:: max(1, len(chosen) // 4)][:4]:
        lines += [f"--- after {s.action}:", log.obs(s.after).render(120)]
    lines += ["", SCHEMA]
    return "\n".join(lines)


def parse_model(j: dict) -> LearnedModel:
    types = {t["name"]: rm.TypeDef(t["name"], dict(t.get("attrs", {}))) for t in j["types"]}
    key_slots = {t["name"]: t.get("key") or next(iter(t.get("attrs", {"name": "str"}))) for t in j["types"]}
    for t in j["types"]:
        if key_slots[t["name"]] not in types[t["name"]].attrs:
            types[t["name"]].attrs[key_slots[t["name"]]] = "str"
    dom = rm.domain_from_json({"name": "llm", "types": [{"name": n, "attrs": td.attrs} for n, td in types.items()],
                               "relations": j.get("relations", []), "operators": j.get("operators", [])})
    return LearnedModel(dom, {}, key_slots, meta={"source": "llm_passive"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run dir with an evidence log (random phase is used)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--max-steps", type=int, default=120)
    ap.add_argument("--random-only", action="store_true", default=True)
    a = ap.parse_args()
    log = EvidenceLog(Path(a.run))
    if a.random_only:
        # restrict to the random exploration phase: steps before the first experiment record
        exp = Path(a.run) / "experiments.jsonl"
        if exp.exists():
            first_exp_step = min(json.loads(l)["steps"][0] for l in exp.read_text().splitlines() if json.loads(l).get("steps"))
            log.steps = [s for s in log.steps if s.step < first_exp_step]
    prompt = build_prompt(log, a.max_steps)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "prompt.txt").write_text(prompt)
    text = ask(prompt, model=a.model, cache_dir=Path("runs/llm_cache"))
    (Path(a.out) / "response.txt").write_text(text)
    j = extract_json(text)
    M = parse_model(j)
    M.save(Path(a.out) / "model.json")
    (Path(a.out) / "model.txt").write_text(str(M))
    print(M)


if __name__ == "__main__":
    main()
