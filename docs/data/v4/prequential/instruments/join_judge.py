"""Judge P21 from the fits: what the Allocate berth control learned on the dev corpus
under the new code and under the pre-change code, and how each scored on the holdout.

Usage: join_judge.py <scratchpad_dir> <out_json>
"""
import json
import sys
from pathlib import Path

CTRL = "button:Allocate berth"


def control_row(report: dict) -> dict:
    m = report.get("outcome_model") or {}
    row = dict((m.get("by_control") or {}).get(CTRL) or {})
    row["list"] = (m.get("lists") or {}).get(CTRL)
    row["wrong"] = [w for w in (m.get("wrong") or []) if CTRL in json.dumps(w)]
    return row


def main():
    S, out = Path(sys.argv[1]), Path(sys.argv[2])
    load = lambda name: json.loads((S / name).read_text()) if (S / name).exists() else None
    new, base = load("join_inspect_dev.json"), load("join_inspect_dev_base.json")
    hold, hold_base = load("outcome_join_hold.json"), load("outcome_join_hold_base.json")
    ft = load("ft_join_dev.json")
    rec = {"dev": {"new": new and {k: new[k] for k in ("roles", "rules", "events", "ordered")},
                   "base": base and {k: base[k] for k in ("roles", "rules", "events", "ordered")}},
           "holdout": {"new": hold and control_row(hold), "base": hold_base and control_row(hold_base)},
           "field_theory": ft and [{k: f[k] for k in ("slot", "adopted")} | {"rules": [u["rule"] for u in f["rules"]]}
                                   for f in ft["fields"]]}
    comparison = [r for r in (new or {}).get("rules", []) if ">= " in r and "(" in r.split(">=")[1] or " < " in r and "(" in r.split(" < ")[1]]
    rec["P21"] = {"comparison_rule_learned": bool(comparison), "comparison_rules": comparison,
                  "both_fields_adopted": bool(new) and all(
                      any(s in slots for slots in new["ordered"].values()) for s in
                      ("attr:Length overall#0", "attr:Takes up to#0"))}
    out.write_text(json.dumps(rec, indent=1, default=str))
    print(json.dumps(rec["P21"], indent=1))
    for side in ("new", "base"):
        d = rec["dev"][side]
        print(f"\n[{side}] roles: {list((d or {}).get('roles', {}))}")
        for r in (d or {}).get("rules", []):
            print("   ", r)
        h = rec["holdout"][side] or {}
        print(f"[{side}] holdout Allocate: " + ", ".join(f"{k}={v}" for k, v in h.items() if k not in ("list", "wrong")))


if __name__ == "__main__":
    main()
