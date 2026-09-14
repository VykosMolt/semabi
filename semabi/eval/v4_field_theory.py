"""Reports which fields the fitted model orders, and on what evidence. Prints, for one
reading of one history, every candidate numeric field, whether ORDERED was adopted, and
the rules that order it, so an intended ordered field and a nominal negative control can
be told apart. Then reports the version space's answer for a named control at the values
a held-out history or intervention rendered.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import fields as field_theory
from semabi.compiler.v4 import outcome as oc

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def theory(run_dir: Path, reading, *, split: float = 0.5) -> dict:
    model = csq.fit(Path(run_dir), reading, split=split)
    A = model.abstractor
    any_model = next(iter(model.outcomes.values()), None)
    ft = getattr(any_model, "field_theory", {"candidates": {}, "adopted": {}})

    def name(tid: int, slot: str) -> str:
        return slot          # a candidate field is named by its attribute already

    fields = []
    for tid, slots in ft["candidates"].items():
        for slot, thresholds in slots.items():
            using = []
            for control, m in model.outcomes.items():
                for rule in m.rules:
                    if any(slot in [s for _, s in field_theory.ordered_fields(l)] for l in rule.condition):
                        using.append({"control": control, "rule": str(rule)})
            fields.append({"tid": tid, "slot": slot, "attribute": name(tid, slot),
                           "thresholds": thresholds,
                           "adopted": slot in ft["adopted"].get(tid, {}), "rules": using})
    return {"run": Path(run_dir).name, "reading": reading.name, "split": split,
            "fields": fields, "model": model}


def corroborate(intervention: Path, attribute: str, into: list[Path]) -> dict:
    """Write what a retained intervention established about a field beside the histories
    to be fitted: the theory, the attribute, the intervention and its verdicts."""
    results = json.loads((Path(intervention) / "results.json").read_text())
    hypotheses = json.loads((Path(intervention) / "hypotheses.json").read_text()) \
        if (Path(intervention) / "hypotheses.json").is_file() else {}
    record = {"attribute": attribute, "theory": "ORDERED",
              "corroborated_by": str(intervention), "hypotheses": hypotheses,
              "results": results,
              "why": "the frozen ordered hypothesis was right at values no history contained "
                     "and the equality guard was refuted there"}
    for run_dir in into:
        path = Path(run_dir) / field_theory.SIDECAR
        payload = json.loads(path.read_text()) if path.is_file() else {"theories": []}
        payload["theories"] = [t for t in payload["theories"] if t["attribute"] != attribute] + [record]
        path.write_text(json.dumps(payload, indent=1, default=str))
    return record


def main(argv=None) -> int:
    from semabi.eval.v4_consequence_run import _candidates

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corroborate", default=None, help="a retained intervention directory")
    ap.add_argument("--attribute", default=None, help="the attribute the intervention was about")
    ap.add_argument("--into", nargs="*", default=[], help="histories to write the sidecar beside")
    a0, _ = ap.parse_known_args(argv)
    if a0.corroborate:
        rec = corroborate(Path(a0.corroborate), a0.attribute, [Path(p) for p in a0.into])
        print(json.dumps({"wrote": [str(Path(p) / "field_theories_v4.json") for p in a0.into],
                          "attribute": rec["attribute"]}, indent=1))
        return 0
    ap.add_argument("--run", required=False)
    ap.add_argument("--chain", required=False)
    ap.add_argument("--reading", required=False)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--control", default=None, help="a control to ask at every held-out state")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if not (a.run and a.chain and a.reading):
        ap.error("--run, --chain and --reading are required (or --corroborate)")
    readings = {c.name: c.reading for c in _candidates(Path(a.chain))}
    r = theory(Path(a.run), readings[a.reading], split=a.split)
    model = r.pop("model")
    print(f"\n{r['run']}  {r['reading']!r}  split={a.split}")
    for f in r["fields"]:
        flag = "ORDERED" if f["adopted"] else "nominal"
        print(f"  {flag:8} T{f['tid']} {f['attribute']:28} thresholds={f['thresholds']}")
        for u in f["rules"][:4]:
            print(f"           {u['control']}: {u['rule'][:110]}")
    if a.control:
        verdicts = []
        for step in model.log.steps[model.cut:]:
            if step.action.kind != "click" or step.action.target is None:
                continue
            vs = oc.score_step_admissible(model, step, corroborated=True, hypothesis=oc.RULE)
            if vs.get("control") == a.control:
                verdicts.append({"step": step.step, "verdict": vs["verdict"],
                                 "admissible": vs.get("admissible"), "observed": vs.get("observed")})
        r["verdicts"] = verdicts
        print(f"  {a.control}: {len(verdicts)} held-out clicks")
        for v in verdicts[:30]:
            print(f"    step {v['step']:4} {v['verdict'][:60]:60} admissible={v['admissible']} observed={str(v['observed'])[:50]}")
    if a.out:
        path = OUT / a.out if not str(a.out).startswith("/") else Path(a.out)
        path.write_text(json.dumps(r, indent=1, default=str))
        print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
