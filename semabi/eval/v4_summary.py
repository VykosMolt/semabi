"""One table over the V4 development evidence.

Development evidence on gauntlet-v3, never fresh generalization.  Coverage, precision,
object-layer quality and cost stay separate columns; there is no combined score.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

APPS = ["grok_01_landing_board", "grok_02_blend_book", "harbour", "opus_02_cellar",
        "vet_clinic", "sonnet_02_barter_market"]
AUTHOR = {"grok_01_landing_board": "Grok 4.6", "grok_02_blend_book": "Grok 4.6",
          "harbour": "Opus 5", "opus_02_cellar": "Opus 5",
          "vet_clinic": "Sonnet 5", "sonnet_02_barter_market": "Sonnet 5"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="docs/data/v4")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    data = Path(a.data)
    rows = []
    held = sorted(data.glob("heldout_*.json")) + sorted(data.glob("prospective_*.json"))
    for app in APPS + [p.stem for p in held]:
        path = data / f"compare_{app}.json"
        if not path.exists():
            path = data / f"{app}.json"
        if not path.exists():
            continue
        blob = json.loads(path.read_text())
        row: dict = {"app": app, "author": AUTHOR.get(app, "held-out"),
                     "trace": blob.get("run"), "primitives": None}
        for name in ("v2", "v4", "v4_pinned"):
            cond = blob["conditions"].get(name)
            if cond is None:
                continue
            row[name] = {
                "rtc": cond["rtc"],
                "strict_precision": cond["strict_registered_delta_precision"],
                "registered_deltas": cond["registered_deltas"],
                "matched": cond["matched_registered_deltas"],
                "view_fp": cond["view_false_positive_rate"],
                "types": [cond["types"]["recovered"], cond["types"]["hidden"]],
                "operators": [cond["operators"]["recovered"], cond["operators"]["observed_in_trace"]],
                "object_layer": cond["object_layer"],
                "false_delta_categories": cond["false_delta_categories"],
                "primitives": cond["cost_primitives"],
            }
        row["search"] = blob.get("v4_search", {}).get("final")
        row["open_questions"] = len(blob.get("v4_search", {}).get("open_questions", []))
        probe = data / f"probe_{app}.json"
        if probe.exists():
            p = json.loads(probe.read_text())
            row["probe"] = {"outcome": p["outcome"], "primitives": p["primitives_spent"],
                            "results": [{"outcome": x.get("outcome"), "eliminated": x.get("eliminated")}
                                        for x in p["probes"]]}
        rows.append(row)

    report = {"version": 1, "suite": "gauntlet-v3 (development)", "apps": rows}
    report["summary"] = {
        "apps_measured": len(rows),
        "v4_better_strict_precision": sum(1 for r in rows if "v4" in r and "v2" in r
                                          and (r["v4"]["strict_precision"] or 0) > (r["v2"]["strict_precision"] or 0)),
        "v4_worse_rtc": sum(1 for r in rows if "v4" in r and "v2" in r and r["v4"]["rtc"] < r["v2"]["rtc"]),
        "v4_better_rtc": sum(1 for r in rows if "v4" in r and "v2" in r and r["v4"]["rtc"] > r["v2"]["rtc"]),
        "v4_fewer_false_deltas": sum(1 for r in rows if "v4" in r and "v2" in r
                                     and r["v4"]["registered_deltas"] < r["v2"]["registered_deltas"]),
        "probe_primitives": sum((r.get("probe") or {}).get("primitives", 0) for r in rows),
    }
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(report, indent=1))
    head = f"{'app':26s} {'author':9s} {'RTC v2->v4':>16s} {'prec v2->v4':>16s} {'deltas':>12s} {'viewFP':>14s}"
    print(head)
    for r in rows:
        if "v4" not in r or "v2" not in r:
            continue
        v2, v4 = r["v2"], r["v4"]
        print(f"{r['app'][:26]:26s} {r['author'][:9]:9s} "
              f"{v2['rtc']:6.3f}->{v4['rtc']:<9.3f} "
              f"{(v2['strict_precision'] or 0):6.3f}->{(v4['strict_precision'] or 0):<9.3f} "
              f"{v2['registered_deltas']:5d}->{v4['registered_deltas']:<6d} "
              f"{v2['view_fp']:6.3f}->{v4['view_fp']:<7.3f}")
    print(json.dumps(report["summary"], indent=1))


if __name__ == "__main__":
    main()
