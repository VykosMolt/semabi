"""Tabulate external-environment runs (gauntlet) into a markdown table."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="g1")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows = ["| app | types | attrs | rels | operators recovered (observed) | learned / spurious | failures rejected | goals | primitives |",
            "|---|---|---|---|---|---|---|---|---|"]
    tot_rec = tot_hid = 0
    for d in sorted(Path("runs").glob(f"{a.prefix}_*")):
        p = d / "eval.json"
        if not p.exists():
            rows.append(f"| {d.name} | crash/incomplete | | | | | | | |")
            continue
        r = json.loads(p.read_text())
        t, pr, o = r["types"], r["predicates"], r["operators"]
        pl = r.get("planning", {})
        tot_rec += o["recovered"]; tot_hid += o["hidden"]
        rows.append(f"| {d.name} | {t['recovered']}/{t['hidden']} | {pr['recovered_attrs']}/{pr['hidden_attrs']} | {pr['recovered_rels']}/{pr['hidden_rels']} | "
                    f"{o['recovered']}/{o['hidden']} ({o['observed_in_trace']}) | {o['learned']} / {len(o['spurious_learned'])} | {o['failure_rejection_rate']} | "
                    f"{pl.get('success', '-')}/{pl.get('n', '-')} | {r['cost']['primitives']} |")
    rows.append(f"| **total** | | | | **{tot_rec}/{tot_hid}** | | | | |")
    txt = "\n".join(rows)
    print(txt)
    if a.out:
        Path(a.out).write_text(txt + "\n")


if __name__ == "__main__":
    main()
