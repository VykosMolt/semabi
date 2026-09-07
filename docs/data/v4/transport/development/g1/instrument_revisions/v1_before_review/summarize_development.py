"""Compare G1 to the saved T1 scores on their unchanged disclosed task surface."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
T1 = ROOT / "docs/data/v4/transport"


def main():
    output = HERE / "summary_v1.json"
    if output.exists():
        raise FileExistsError(output)
    spec = importlib.util.spec_from_file_location("t1_summary", T1 / "acquisition_summary.py")
    summary = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(summary)
    inputs = summary.Inputs(ROOT)
    results = {}
    for fixture in ("dispatch", "workshop"):
        prefix = Path("docs/data/v4/transport/first_pass") / fixture
        decisions = inputs.read(str(prefix / "evaluation_v2/decisions.jsonl"), lines=True)
        targets = [row for row in decisions if row.get("task_target")]
        summary.require(len(targets) == (10 if fixture == "dispatch" else 8), "target count")
        for stage in ("initial_v2", "contested_1701", "contested_1702"):
            old_path = prefix / "scores" / (stage + ".json")
            new_path = HERE.relative_to(ROOT) / "scores" / fixture / (stage + ".json")
            old, new = inputs.read(str(old_path)), inputs.read(str(new_path))
            for score in (old, new):
                summary.require(score["status"] == "FINISHED" and not score["pending_models"],
                                f"incomplete score: {fixture}/{stage}")
                summary.require(len(score["models"]) == 8, "all readings remain in scope")
            summary.require(set(old["models"]) == set(new["models"]), "reading IDs changed")
            for key in ("train", "evaluation", "candidate_file_sha256", "candidate_set_sha256"):
                summary.require(old[key] == new[key], f"different compared evidence: {key}")
            models = {}
            for name in old["models"]:
                before, after = old["models"][name], new["models"][name]
                metrics = {}
                for label, record in (("T1", before), ("G1", after)):
                    task_steps = {row["step"] for row in targets}
                    queries = summary.index_steps(record["queries"], "query")
                    summary.require(task_steps <= set(queries), "missing target query")
                    metrics[label] = {
                        "fit_error": record.get("fit_error"),
                        "state_failure_count": len(record["state"]["failures"]),
                        "task_query_runtime_failures": sum(
                            isinstance(queries[step].get("status"), str)
                            and "RUNTIME_FAILURE" in queries[step]["status"] for step in task_steps),
                        "task_owners_present": sum(queries[step].get("owner") is not None for step in task_steps),
                        "task_count": len(targets),
                        "tasks": {channel: summary.fixed_summary(
                            summary.target_rows(record, targets, channel), channel)
                                  for channel in summary.CHANNELS},
                        "all_clicks": {channel: record["emission"][channel]["summary"]
                                       for channel in summary.CHANNELS},
                    }
                models[name] = {
                    "complete_saved_record_equal": before == after,
                    "training_model_equal": before.get("model") == after.get("model"),
                    "metrics": metrics,
                }
            results[f"{fixture}/{stage}"] = {
                "models": models,
                "identity": {"T1": summary.identity_summary(old), "G1": summary.identity_summary(new)},
            }
    inputs.verify_unchanged()
    record = {
        "schema": "semabi.transport.g1_development_summary.v1",
        "scope": "Same disclosed T1 evidence under a repaired implementation. Two initial "
                 "and four distinct terminal histories; identical arm pairs scored once. "
                 "No new acquisition or fresh generalization claim.",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "reused_summary_sha256": hashlib.sha256((T1 / "acquisition_summary.py").read_bytes()).hexdigest(),
        "inputs": inputs.files,
        "comparisons": results,
    }
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"output": str(output), "comparisons": len(results),
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
