"""Fit one history under the pinned reading and print every control's rules, for a seed test.

Usage: PYTHONHASHSEED=<n> fit_seed.py <run_dir> <chain> <reading> <out_json>
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))


def main():
    run, chain, reading_name, out = sys.argv[1:5]
    from semabi.compiler.v4 import consequence as csq
    from semabi.eval.v4_consequence_run import _candidates
    reading = {c.name: c.reading for c in _candidates(Path(chain))}[reading_name]
    model = csq.fit(Path(run), reading, split=0.5)
    rec = {"seed": os.environ.get("PYTHONHASHSEED"), "controls": {}}
    for control, m in sorted(model.outcomes.items()):
        rec["controls"][control] = {"rules": [str(r) for r in m.rules], "default": m.default,
                                    "fitted": m.fitted, "ordered": {str(k): v for k, v in (m.ordered or {}).items()}}
    Path(out).write_text(json.dumps(rec, indent=1, default=str))
    for c, d in rec["controls"].items():
        print(c, len(d["rules"]), d["default"][:40], [r[:70] for r in d["rules"][:2]])


if __name__ == "__main__":
    main()
