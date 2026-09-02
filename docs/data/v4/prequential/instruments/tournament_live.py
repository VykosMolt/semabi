"""Run the R4 tournament closure live on a (private copy of a) corpus.

Usage: tournament_live.py <run_dir> <name> <fwd|rev> <out_json>
Raw floor = the sidecar's rows without `premises` (executed experiments);
derived rows from any earlier run are dropped before starting.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from attack import make_prep_derive, stamp, endpoint
from tournament import tournament_fixpoint


def main():
    run_dir, name, order, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
    sidecar = run_dir / "identity_refutations_v4.json"
    original = json.loads(sidecar.read_text()) if sidecar.exists() else {"refuted": []}
    raw = [r for r in original.get("refuted", []) if "premises" not in r]
    sidecar.write_text(json.dumps({"refuted": raw}, indent=1))
    prep, derive = make_prep_derive(run_dir)
    key = (lambda f: f) if order == "fwd" else (lambda f: "".join(chr(255 - ord(c)) for c in f))
    r = tournament_fixpoint(prep, derive, raw, fam_key=key)
    rec = {"stamp": stamp(), "run": str(run_dir), "name": name, "order": order,
           "raw_floor": [(x["family"], str(x["key_slot"])) for x in raw],
           "outcome": r["outcome"], "endpoint": endpoint(r["rows"]), "base": r.get("base"),
           "disputed": r.get("disputed"), "events": r["events"]}
    out.write_text(json.dumps(rec, indent=1, default=str))
    print(r["outcome"], name, order, json.dumps(rec["endpoint"], default=str))


if __name__ == "__main__":
    main()
