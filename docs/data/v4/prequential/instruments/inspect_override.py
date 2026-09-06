"""Fit one control under the search's settled reading with one family's key overridden.

Usage: inspect_override.py <run_dir> <family_substring> <key_slot|none> <control> <out_json>
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    run, needle, key, control, out = sys.argv[1:6]
    from link_probe import settled_reading
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import fields
    from semabi.compiler.v4.pinned import PinnedReading
    from semabi.eval.v4_identity_ties import _override
    reading = settled_reading(Path(run))
    fam = [f for f in reading.families if needle in f]
    assert len(fam) == 1, fam
    overridden = PinnedReading.from_json(_override(reading.to_json(), fam[0], None if key == "none" else key))
    rec = {}
    for label, rd in (("settled", reading), ("overridden", overridden)):
        model = csq.fit(Path(run), rd, split=0.999)
        m = model.outcomes.get(control)
        rec[label] = {"sheet_key": rd.families[fam[0]].key_slot,
                      "roles": {k: (r.kind, r.form) for k, r in (m.roles if m else {}).items()},
                      "rules": [str(r) for r in (m.rules if m else [])], "ordered": (m.ordered if m else None),
                      "operators_touching": sorted({op.name for op in model.inducer.operators
                                                    if any(control.split(":", 1)[1] in str(a) for a in getattr(op, "acts", []))})[:12]}
        print(label, "sheet key", rec[label]["sheet_key"], "| roles", rec[label]["roles"], flush=True)
        print("   rules", [r[:80] for r in rec[label]["rules"][:5]], "| ordered", rec[label]["ordered"], flush=True)
        print("   operators touching:", rec[label]["operators_touching"], flush=True)
    Path(out).write_text(json.dumps(rec, indent=1, default=str))


if __name__ == "__main__":
    main()
