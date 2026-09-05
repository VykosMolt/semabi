"""What the outcome layer makes of one control on a corpus: roles, rules, adopted
fields, and per-occasion the ordered and comparison literals it saw.

Usage: join_inspect.py <run_dir> <chain|search> <reading> <control> <out_json> [split]
With `search` as the chain, the reading is the search's own settled reading of the corpus.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    run, chain, reading_name, control, out = sys.argv[1:6]
    split = float(sys.argv[6]) if len(sys.argv) > 6 else 0.999
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import fields
    from semabi.eval.v4_consequence_run import _candidates
    if chain == "search":
        from link_probe import settled_reading
        reading = settled_reading(Path(run))
        families = {k: (v.key_slot, v.status) for k, v in reading.families.items()} \
            if hasattr(reading, "families") else None
    else:
        reading = {c.name: c.reading for c in _candidates(Path(chain))}[reading_name]
        families = None
    model = csq.fit(Path(run), reading, split=split)
    m = model.outcomes.get(control)
    if m is None:
        print("controls:", sorted(model.outcomes)); raise SystemExit(f"no model for {control}")
    ev = m.evidence
    occasions = []
    for i, (mask, event) in enumerate(zip(ev.masks, ev.events)):
        lits = [ev.of_bit[b] for b in range(len(ev.of_bit)) if mask & (1 << b)]
        occasions.append({"event": event,
                          "ordered": [l for l in lits if fields.ordered_fields(l)],
                          "attrs": [l for l in lits if l[0] == "attr"][:12]})
    rec = {"run": str(run), "control": control, "split": split, "families": families,
           "roles": {k: {"kind": r.kind, "form": r.form, "tid": r.tid, "anchor": r.anchor}
                     for k, r in m.roles.items()},
           "rules": [str(r) for r in m.rules], "default": m.default,
           "events": m.events, "ordered": m.ordered,
           "field_theory": getattr(m, "field_theory", None), "occasions": occasions}
    Path(out).write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps({k: rec[k] for k in ("families", "roles", "rules", "events", "ordered")}, indent=1, default=str))
    for o in occasions:
        print(f"  {o['event'][:50]:50s} {o['ordered']}")


if __name__ == "__main__":
    main()
