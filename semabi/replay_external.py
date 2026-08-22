"""Corrected replay of stored V1 gauntlet runs (measurement audit, docs/v2_oracle.md).

The V1 evaluation paired hidden.jsonl line i with evidence-log step i, but the
hidden recorder also logged the reset inside `view_sweep` that the evidence log
does not contain, so the hidden states were one step ahead. This script
re-evaluates a stored run from its own trace and cached schema (no exploration,
no LLM call) with both pairings and reports the difference. Operator
explanation uses the hidden trace alone and is unaffected; type/attribute/
relation alignment is what can move."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.compile_v1 import compile_v1
from semabi.eval.external import check_failures, domain_from_description, explain_transitions, state_from_json, summarize
from semabi.eval.matching import align
from semabi.eval.recorder import load_hidden


def evaluate(run_dir: Path, offset: int) -> dict:
    desc = json.loads((run_dir / "hidden_domain.json").read_text())
    hidden_dom = domain_from_description(desc)
    C = compile_v1(run_dir, min_support=2)  # schema.json cached -> deterministic, identical model
    hidden = load_hidden(run_dir)
    n = min(len(hidden) - offset, len(C.log.steps))
    pairs = [(state_from_json(hidden[i + offset]["state"]), C.visible_state_after(i)) for i in range(n)]
    m = align(hidden_dom, C.model, pairs, attr_agree=0.85, rel_agree=0.8)
    scores, used = explain_transitions(hidden_dom, C.model, m, hidden)
    check_failures(hidden_dom, C.model, m, hidden, scores)
    res = summarize(hidden_dom, C.model, m, scores, used)
    return {"types": res["types"]["recovered"], "hidden_types": res["types"]["hidden"],
            "attrs": res["predicates"]["recovered_attrs"], "hidden_attrs": res["predicates"]["hidden_attrs"],
            "rels": res["predicates"]["recovered_rels"], "hidden_rels": res["predicates"]["hidden_rels"],
            "ops": res["operators"]["recovered"], "hidden_ops": res["operators"]["hidden"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", default="docs/data/replay_v1.json")
    a = ap.parse_args()
    out = {}
    rows = ["| run | pairing | types | attrs | rels | ops |", "|---|---|---|---|---|---|"]
    for r in a.runs:
        rd = Path(r)
        orig = evaluate(rd, 0)
        corr = evaluate(rd, 1)
        out[rd.name] = {"original": orig, "corrected": corr}
        for tag, e in (("original", orig), ("corrected", corr)):
            rows.append(f"| {rd.name} | {tag} | {e['types']}/{e['hidden_types']} | {e['attrs']}/{e['hidden_attrs']} | {e['rels']}/{e['hidden_rels']} | {e['ops']}/{e['hidden_ops']} |")
        print(rows[-2]); print(rows[-1], flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))
    Path(a.out).with_suffix(".md").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    main()
