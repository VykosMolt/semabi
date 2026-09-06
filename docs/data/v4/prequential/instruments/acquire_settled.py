"""Acquire, on the live application, the occasions the version space is unsure about for
one control, under a corpus's settled reading; refit that control's evidence with them;
re-score a held-out history before and after.

Usage: acquire_settled.py <dev_run> <hold_run> <base_url> <seed> <policy> <control_key> <button> <out_json>
"""
import json
import os
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def ledger(m, control):
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4.consequence import clicked_control
    whole, mine, rows = Counter(), Counter(), []
    for step in m.log.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        whole[v["verdict"]] += 1
        if v.get("control") == control:
            mine[v["verdict"]] += 1
            rows.append({"step": step.step, "verdict": v["verdict"], "admissible": v.get("admissible"), "observed": v.get("observed")})
    return {"whole": dict(whole), "control": dict(mine), "rows": rows}


def main():
    dev, hold, base, seed, policy, control, button, out = sys.argv[1:9]
    seed = int(seed)
    from link_probe import settled_reading
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.eval import v4_acquire as acq
    reading = settled_reading(Path(dev))
    model = csq.fit(Path(dev), reading, split=0.999)
    other = EvidenceLog(Path(hold))
    m = replace(model, log=other, cut=0)
    before = ledger(m, control)
    print("before:", before["control"], flush=True)
    got = acq.acquire(model, control, button, base, seed=seed, budget=40, want=12, policy=policy)
    if "error" in got:
        print(got["error"]); raise SystemExit(1)
    usable = [r for r in got["acquired"] if r["frame"] is not None]
    print(f"acquired {len(got['acquired'])}, usable {len(usable)}, discriminating {got['discriminating']}, "
          f"states by set size {got['states_examined']}", flush=True)
    print("  frames:", dict(Counter(r["frame"] for r in usable)), flush=True)
    original = model.outcomes[control]
    after = {}
    for label, only in (("discriminating_only", True), ("every_occasion", False)):
        refit = acq.refit_with(model, control, got["acquired"], only)
        m2 = replace(model, log=other, cut=0)
        m2.outcomes[control] = refit
        after[label] = ledger(m2, control)
        print(f"after ({label}):", after[label]["control"], flush=True)
        model.outcomes[control] = original
    rec = {"dev": dev, "hold": hold, "seed": seed, "policy": policy, "control": control,
           "states_examined": got["states_examined"], "discriminating": got["discriminating"],
           "acquired": [{k: v for k, v in r.items() if k not in ("state", "owner")} for r in got["acquired"]],
           "before": before, "after": after}
    Path(out).write_text(json.dumps(rec, indent=1, default=str))


if __name__ == "__main__":
    main()
