"""Summarise the oracle ladder: runs/oracle/<app>/eval_<cond>.json -> runs/oracle/results.json + markdown."""
from __future__ import annotations

import json
from pathlib import Path

CONDS = ["base", "A", "B", "Bv", "C", "D", "K"]
APPS = ["grok_01_apiary", "grok_02_observatory", "grok_03_pharmacy", "grok_04_climbing",
        "claude_01_airport_gates", "claude_02_pharmacy_dispensary", "claude_03_museum_loans", "claude_04_datacenter_racks"]


def main():
    root = Path("runs/oracle")
    out = {"apps": {}, "totals": {}}
    for app in APPS:
        out["apps"][app] = {}
        for c in CONDS:
            p = root / app / f"eval_{c}.json"
            if not p.exists():
                continue
            e = json.loads(p.read_text())
            o = e["operators"]
            out["apps"][app][c] = {
                "types": [e["types"]["recovered"], e["types"]["hidden"]],
                "attrs": [e["predicates"]["recovered_attrs"], e["predicates"]["hidden_attrs"]],
                "rels": [e["predicates"]["recovered_rels"], e["predicates"]["hidden_rels"]],
                "ops": [o["recovered"], o["hidden"], o["observed_in_trace"]],
                "recovered_ops": o["recovered_ops"],
                "learned": o["learned"], "spurious": len(o["spurious_learned"]),
                "failure_rejection": o["failure_rejection_rate"],
                "gtc": e["gtc"]["gtc"], "rtc": e.get("rtc", {}).get("rtc"),
                "object_layer": e.get("object_layer"), "view_false_positives": e.get("view_false_positives"),
                "per_op": {h: [x["explained"], x["successes"], len(x["by"])] for h, x in o["per_op"].items() if x["successes"]},
            }
    for c in CONDS:
        rec = hid = obs = 0
        for app in APPS:
            r = out["apps"][app].get(c)
            if r:
                rec += r["ops"][0]
                hid += r["ops"][1]
                obs += r["ops"][2]
        out["totals"][c] = {"recovered": rec, "hidden": hid, "observed": obs}
    (root / "results.json").write_text(json.dumps(out, indent=1))
    # markdown
    lines = ["| app | " + " | ".join(CONDS) + " |", "|---|" + "---|" * len(CONDS)]
    for app in APPS:
        cells = []
        for c in CONDS:
            r = out["apps"][app].get(c)
            cells.append(f"{r['ops'][0]}/{r['ops'][1]}" if r else "-")
        obs = next(iter(out["apps"][app].values()))["ops"][2]
        lines.append(f"| {app} ({obs} observed) | " + " | ".join(cells) + " |")
    lines.append("| **total** | " + " | ".join(f"**{out['totals'][c]['recovered']}/{out['totals'][c]['hidden']}**" for c in CONDS) + " |")
    lines.append("")
    lines.append("| app | cond | types | attrs | rels | RTC | GTC | learned / spurious | view-FP transitions | fail. rejection |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for app in APPS:
        for c in CONDS:
            r = out["apps"][app].get(c)
            if not r:
                continue
            v = r["view_false_positives"] or {}
            lines.append(f"| {app} | {c} | {r['types'][0]}/{r['types'][1]} | {r['attrs'][0]}/{r['attrs'][1]} | {r['rels'][0]}/{r['rels'][1]} | "
                         f"{r['rtc'] if r['rtc'] is not None else '-'} | {r['gtc']} | {r['learned']} / {r['spurious']} | "
                         f"{v.get('without_hidden_change', '-')}/{v.get('learned_transitions', '-')} | {r['failure_rejection']} |")
    (root / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))
    print(json.dumps(out["totals"]))


if __name__ == "__main__":
    main()
