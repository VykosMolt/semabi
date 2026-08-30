"""Which fields the fitted model orders, and on what evidence.

`semabi.compiler.v4.fields` proposes ORDERED for every numeric field and adopts it only where
a fitted rule orders the field and is justified in doing so.  This prints the proposal and
the adoption for one reading of one history -- every candidate field, whether it was
adopted, and the rules that order it -- so that the intended field (blend's committed
gallons) can be seen to carry the theory and the negative control (a ticket number, also
numeric, nominal) can be seen not to.  Then the version space's answer for a named control
at the values a held-out history or an intervention rendered.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import outcome as oc

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def theory(run_dir: Path, reading, *, split: float = 0.5) -> dict:
    model = csq.fit(Path(run_dir), reading, split=split)
    A = model.abstractor
    any_model = next(iter(model.outcomes.values()), None)
    ft = getattr(any_model, "field_theory", {"candidates": {}, "adopted": {}})

    def name(tid: int, slot: str) -> str:
        et = A.H.entity_types.get(tid)
        template = next((t for t in et.units if slot in A.H.units[t].slots), None) if et else None
        return A.attr_name(et, template, slot) if template else f"attr:{slot}"

    fields = []
    for tid, slots in ft["candidates"].items():
        for slot, thresholds in slots.items():
            using = []
            for control, m in model.outcomes.items():
                for rule in m.rules:
                    if any(l[0] in ("attr_ge", "attr_lt") and l[2] == slot for l in rule.condition):
                        using.append({"control": control, "rule": str(rule)})
            fields.append({"tid": tid, "slot": slot, "attribute": name(tid, slot),
                           "thresholds": thresholds,
                           "adopted": slot in ft["adopted"].get(tid, {}), "rules": using})
    return {"run": Path(run_dir).name, "reading": reading.name, "split": split,
            "fields": fields, "model": model}


def main(argv=None) -> int:
    from semabi.eval.v4_consequence_run import _candidates

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--control", default=None, help="a control to ask at every held-out state")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
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
