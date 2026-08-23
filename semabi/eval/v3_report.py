"""Assemble the ordinary V3 result from the artifacts the official run produced.

Nothing is averaged across applications and no single score is formed.  Coverage,
precision, semantic validity, operator recovery, planning and interaction cost stay
separate columns, and the three ways a behaviour can fail to be represented --
never exercised, exercised and left silent, exercised and claimed wrongly -- stay
distinct.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CONDITIONS = ("v2_baseline", "v2_supported_point_estimate", "v2_provisional", "v2_validated")


def _load(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def _condition(runs: Path, tag: str, name: str) -> dict | None:
    """The full evaluation record each ablation condition leaves in the run directory."""
    return _load(runs / f"{tag}_loop" / f"eval_{name}.json")


def _slim(row: dict | None) -> dict | None:
    if row is None:
        return None
    rtc, ops = row["rtc"], row["operators"]
    return {
        "rtc": rtc["rtc"],
        "registered_transitions": rtc["transitions"],
        "registered_delta_precision": rtc["registered_delta_precision"],
        "strict_registered_delta_precision": rtc["strict_registered_delta_precision"],
        "spurious_registered_delta_rate": rtc["spurious_registered_delta_rate"],
        "false_delta_classes": rtc.get("false_registered_delta_diagnostics", {}).get("classification_counts", {}),
        "gtc": row["gtc"]["gtc"],
        "view_false_positive_rate": row["view_false_positives"]["rate"],
        "view_false_positives": row["view_false_positives"]["without_hidden_change"],
        "learned_transitions": row["view_false_positives"]["learned_transitions"],
        "types": row["types"],
        "predicates": row["predicates"],
        "operators": {k: v for k, v in ops.items() if k != "per_op"},
        "operators_per_op": {k: {"successes": v["successes"], "explained": v["explained"],
                                 "rate": v["explained_rate"], "failures": v["failures"],
                                 "rejected": v["rejected"]}
                             for k, v in ops.get("per_op", {}).items()},
        "counterexamples": row.get("counterexamples", {}).get("status_counts", {}),
        "abstraction_contradictions": len(row.get("abstraction_contradictions", []) or []),
        "argument_binding": row.get("argument_binding"),
        "cost_primitives": row["cost"]["primitives"],
    }


def app_row(out: Path, runs: Path, tag: str) -> dict:
    row: dict = {"tag": tag, "conditions": {},
                 "ablation_summary": _load(out / f"ablation_{tag}.json")}
    for name in CONDITIONS:
        row["conditions"][name] = _slim(_condition(runs, tag, name))

    loop = runs / f"{tag}_loop"
    decisions = []
    path = loop / "refinements_v2.json"
    if path.exists():
        decisions = json.loads(path.read_text()).get("decisions", [])
    row["decisions"] = [{"id": d.get("id"), "kind": d.get("kind"), "status": d.get("status"),
                         "support": d.get("support")} for d in decisions]
    row["decision_statuses"] = sorted({d.get("status") for d in decisions})

    row["validation"] = []
    for seed in (11, 12, 13):
        rec = _load(out / f"validation_{tag}_seed{seed}.json")
        if rec is None:
            continue
        differential = rec.get("differential_evidence") or {}
        row["validation"].append({
            "seed": seed,
            "status": rec.get("status"),
            "reason": rec.get("reason"),
            "predictions": len(rec.get("source_predictions", [])),
            "tested_predictions": rec.get("tested_source_predictions"),
            "prospective_schema_accuracy": rec.get("prospective_schema_accuracy"),
            "matched": len(rec.get("matched_predictions", [])),
            "mispredictions": len(rec.get("mispredictions", [])),
            "novel_binding_matches": len(rec.get("novel_binding_matches", [])),
            "untestable": len(rec.get("untestable_predictions", [])),
            "quantifier_counterexamples": len(rec.get("quantifier_counterexamples", []) or []),
            "differential": {k: v for k, v in differential.items() if k != "cases"},
            "independence": rec.get("independence"),
        })

    tasks = _load(out / f"tasks_{tag}.json")
    if tasks is not None:
        row["tasks"] = {k: v for k, v in tasks.items() if k != "cases"}
        row["tasks"]["failures"] = sorted({c.get("failure") for c in tasks.get("cases", [])
                                           if c.get("failure")})

    row["falsification"] = _load(out / f"falsification_{tag}.json")

    costs = {}
    for name in ("loop", "seed11", "seed12", "seed13"):
        run_dir = runs / f"{tag}_{name}" if name != "loop" else loop
        steps = run_dir / "steps.jsonl"
        if steps.exists():
            costs[name] = sum(1 for _ in steps.open())
    row["trace_primitives"] = costs
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", default="docs/data/v3")
    ap.add_argument("--runs", default="runs/v3")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    apps = json.loads(Path(a.manifest).read_text())
    out, runs = Path(a.out), Path(a.runs)
    rows = [app_row(out, runs, app["tag"]) for app in apps]
    report = {"version": 1, "apps": rows, "n_apps": len(rows)}

    def canonical(row):
        return (row["conditions"].get("v2_validated") or {}) or {}
    report["summary"] = {
        "apps_with_a_refinement_decision": sum(1 for r in rows if r["decisions"]),
        "apps_with_a_validated_decision": sum(1 for r in rows
                                              if any(d["status"] == "VALIDATED" for d in r["decisions"])),
        "apps_with_a_mispredicted_decision": sum(1 for r in rows
                                                 if any(d["status"] == "MISPREDICTED" for d in r["decisions"])),
        "apps_with_no_decision": sum(1 for r in rows if not r["decisions"]),
        "apps_with_nonzero_canonical_rtc": sum(1 for r in rows if (canonical(r).get("rtc") or 0) > 0),
        "apps_recovering_at_least_one_operator": sum(
            1 for r in rows if (canonical(r).get("operators") or {}).get("recovered", 0) > 0),
        "hidden_operators": sum((canonical(r).get("operators") or {}).get("hidden", 0) for r in rows),
        "hidden_operators_observed": sum((canonical(r).get("operators") or {}).get("observed_in_trace", 0)
                                         for r in rows),
        "hidden_operators_recovered": sum((canonical(r).get("operators") or {}).get("recovered", 0)
                                          for r in rows),
        "task_goals_attempted": sum((r.get("tasks") or {}).get("attempted", 0) for r in rows),
        "task_goals_succeeded": sum((r.get("tasks") or {}).get("succeeded", 0) for r in rows),
        "total_primitives": sum(sum(r["trace_primitives"].values()) for r in rows),
    }
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(report, indent=1))
    print(json.dumps(report["summary"], indent=1))
    header = f"{'app':28s} {'RTC':>6s} {'prec':>6s} {'viewFP':>7s} {'types':>8s} {'ops':>10s} {'tasks':>7s} {'prims':>7s}"
    print(header)
    for r in rows:
        c = canonical(r)
        if not c:
            print(f"{r['tag']:28s} (no ablation)")
            continue
        t, o = c["types"], c["operators"]
        tasks = r.get("tasks") or {}
        print(f"{r['tag']:28s} {c['rtc']:6.3f} {c['strict_registered_delta_precision'] or 0:6.3f} "
              f"{c['view_false_positive_rate']:7.3f} {t['recovered']:3d}/{t['hidden']:<4d} "
              f"{o['recovered']:3d}/{o['observed_in_trace']:<6d} "
              f"{tasks.get('succeeded', 0):3d}/{tasks.get('attempted', 0):<3d} "
              f"{sum(r['trace_primitives'].values()):7d}")


if __name__ == "__main__":
    main()
