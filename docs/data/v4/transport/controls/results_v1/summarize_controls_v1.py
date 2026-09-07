#!/usr/bin/env python3
"""Read-only summary of completed T1 controls and their preserved saved queries."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
FIRST = ROOT / "docs/data/v4/transport/first_pass"
STAGES = ("initial_v2", "contested_1701", "untargeted_1701", "contested_1702", "untargeted_1702")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    summary = {"kind": "ORACLE_SUPPLIED_POST_PRESERVATION_CONTROL_SUMMARY",
               "created_utc": datetime.now(timezone.utc).isoformat(), "inputs": {}, "matrix": [],
               "source_file": str(Path(__file__).relative_to(ROOT)), "source_sha256": sha(Path(__file__)),
               "all_counts_reuse_same_evaluation_cases": True, "models": 0}
    totals = defaultdict(Counter)
    for fixture in ("dispatch", "workshop"):
        decisions_path = FIRST / fixture / "evaluation_v2/decisions.jsonl"
        decisions = [json.loads(line) for line in decisions_path.read_text().splitlines()]
        targets = {d["step"] for d in decisions if d.get("task_target")}
        summary["inputs"][str(decisions_path.relative_to(ROOT))] = sha(decisions_path)
        for stage in STAGES:
            control_path = HERE / f"{fixture}_{stage}.json"
            score_path = FIRST / fixture / "scores" / f"{stage}.json"
            control, score = json.loads(control_path.read_text()), json.loads(score_path.read_text())
            for path in (control_path, score_path):
                summary["inputs"][str(path.relative_to(ROOT))] = sha(path)
            row = {"fixture": fixture, "stage": stage, "task_denominator_per_model": control["task_denominator_per_model"],
                   "models": {}}
            for name, measured in control["models"].items():
                summary["models"] += 1
                group = "current_inferred" if name == "current_inferred" else "pinned_candidates"
                for metric, counts in measured["summary"].items():
                    totals[group + ":" + metric].update(counts)
                model = score["models"][name]
                queries = [q for q in model["queries"] if q["step"] in targets]
                statuses = Counter(str(q["status"]) if isinstance(q["status"], str) else "role_status" for q in queries)
                theories = []
                for q in queries:
                    theory = model["model"]["outcomes"].get(q.get("control"), {}).get("field_theory", {})
                    theories.append({key: bool(theory.get(key)) for key in ("candidates", "adopted", "adopted_pairs", "clocks")})
                diagnostic = {
                    "metrics": measured["summary"], "query_statuses": dict(statuses),
                    "any_bound_object": sum(bool(q.get("binding")) for q in queries),
                    "owner_present": sum(q.get("owner") is not None for q in queries),
                    "heading_retained_in_view": sum("heading#0" in q.get("view", {}) for q in queries),
                    "textbox_retained_in_view": sum("textbox#0" in q.get("view", {}) for q in queries),
                    "any_comparison_query_literal": sum(any(l[0] in ("attr_cmp_ge", "attr_cmp_lt")
                                                             for l in q.get("query_literals", [])) for q in queries),
                    "field_theory_presence": {key: sum(t[key] for t in theories)
                                              for key in ("candidates", "adopted", "adopted_pairs", "clocks")},
                    "runtime_failure_at_H_parse_units_G_obs": sum(q.get("status") == "RUNTIME_FAILURE"
                                                                  and "obs = self.G.obs[sig]" in q.get("traceback", "")
                                                                  for q in queries),
                }
                if stage == "initial_v2" and name in ("candidate_00", "candidate_02", "current_inferred"):
                    diagnostic["representative_query"] = queries[0]
                row["models"][name] = diagnostic
            summary["matrix"].append(row)
    summary["totals_by_model_group"] = dict(totals)
    for relative, expected in summary["inputs"].items():
        if sha(ROOT / relative) != expected:
            raise RuntimeError("Input changed during summary: " + relative)
    with (HERE / "summary_v1.json").open("x") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"models": summary["models"], "matrix_cells": len(summary["matrix"]),
                      "summary_sha256": sha(HERE / "summary_v1.json")}))


if __name__ == "__main__":
    main()
