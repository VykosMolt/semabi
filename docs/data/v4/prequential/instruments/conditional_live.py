"""Closure over schedules with conditional bases, live on a (private copy of a) corpus.

Usage: conditional_live.py <run_dir> <name> <emission|shared> <out_json>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from attack import stamp, endpoint
from conditional import make_conditional
from semabi.eval.v4_identity_ties import (closure_over_schedules, EMISSION_COMPARATOR,
                                          SHARED_COMPARATOR)


def main():
    run_dir, name, variant, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    comparator = EMISSION_COMPARATOR if variant == "emission" else SHARED_COMPARATOR
    sidecar = run_dir / "identity_refutations_v4.json"
    original = json.loads(sidecar.read_text()) if sidecar.exists() else {"refuted": []}
    raw = [r for r in original.get("refuted", []) if "premises" not in r]
    sidecar.write_text(json.dumps({"refuted": raw}, indent=1))
    prep, derive = make_conditional(run_dir, comparator)
    r = closure_over_schedules(prep, derive, raw, ("fwd", "rev"))
    rec = {"stamp": stamp(), "run": str(run_dir), "name": name, "comparator": comparator,
           "bases": "conditional", "outcome": r["outcome"], "disputed": r["disputed"],
           "endpoint": [list(k) for k in sorted({(x["family"], str(x["refuted_key"])) for x in r["rows"]})],
           "per_schedule": {o: {"outcome": v["outcome"], "base": v["base"], "rows": v["rows"]}
                            for o, v in r["per_schedule"].items()},
           "events": r["events"]}
    out.write_text(json.dumps(rec, indent=1, default=str))
    print(r["outcome"], name, comparator, json.dumps(rec["endpoint"], default=str))


if __name__ == "__main__":
    main()
