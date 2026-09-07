"""Reproduce the first G2 sealer's comparison custody gap with invented files.

Execute the exact AST subsection from comparison_path through the corpus checks,
stopping before required_reports and all inventory/output creation. This is a
subsection test, not a full-sealer acceptance claim. No learner is imported.
"""
import ast
import hashlib
from importlib.machinery import SourceFileLoader
import importlib.util
import json
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parents[1]
SOURCE = HERE / "instrument_revisions/preserve_results_before_review_v1.py.txt"
EXPECTED = "7c78cbe05ffcfaa4fc33aa89b4f62c0e1b430e9115fd9c3cd4fe40ce1ba2de5a"
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
spec = importlib.util.spec_from_loader("original_g2_sealer", SourceFileLoader("original_g2_sealer", str(SOURCE)))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
tree = ast.parse(SOURCE.read_text())
main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")


def assignment(node, name):
    return isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)


start = next(i for i, node in enumerate(main.body) if assignment(node, "comparison_path"))
end = next(i for i, node in enumerate(main.body) if assignment(node, "required_reports"))
block = ast.fix_missing_locations(ast.Module(body=main.body[start:end], type_ignores=[]))
root = Path(tempfile.mkdtemp(prefix="semabi-g2-comparison-public-review-"))
module.ROOT = root
module.HERE = root / "docs/data/v4/transport/development/g2"
module.G1 = module.HERE.parent / "g1"


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) if not isinstance(value, str) else value)


corpus = root / "invented_corpus"
for name in ("observations.jsonl", "steps.jsonl"):
    put(corpus / name, "{}\n")
manifest = {"root": "invented_corpus", "files": {
    name: module.sha(corpus / name) for name in ("observations.jsonl", "steps.jsonl")}}
manifest_path = root / "invented_input_manifest.json"
put(manifest_path, manifest)
freeze = {"corpora": {"root": "invented_corpus", "manifest": "invented_input_manifest.json",
                     "manifest_sha256": module.sha(manifest_path)}}
freeze_path = module.HERE / "freeze_v1.json"
put(freeze_path, freeze)
module.FREEZE_SHA = module.sha(freeze_path)
put(module.HERE / "run_corpus.py", "# invented adapter\n")
put(module.HERE / "compare_corpora.py", "# invented comparison instrument\n")
consumed = {str(corpus / name): digest for name, digest in manifest["files"].items()}
inputs = {}
for case in module.CASES:
    directory = module.HERE / "corpora" / case
    result_path = directory / (case + ".json")
    inner_path = directory / (case + "_process.json")
    snapshot = directory / "source_snapshot.json"
    job = module.HERE / "jobs" / ("corpus_" + case) / "process.json"
    put(result_path, {"provenance": {"source_snapshot_sha256": module.FREEZE_SHA,
                                    "input_files": consumed}})
    put(inner_path, {"state": "completed", "case": case, "result_sha256": module.sha(result_path),
                     "changed_inputs": [], "source_snapshot_sha256": module.FREEZE_SHA,
                     "input_files": consumed})
    put(snapshot, freeze)
    put(job, {})
    put(directory / "adapter.json", {"adapter_sha256": module.sha(module.HERE / "run_corpus.py"),
        "input_manifest_sha256": module.sha(manifest_path), "source_snapshot": str(freeze_path)})
    inputs.update({module.relative(path): module.sha(path) for path in (result_path, inner_path, snapshot, job)})
comparison = {"schema": "semabi.transport.g2_corpus_comparison.v1",
              "source_sha256": module.sha(module.HERE / "compare_corpora.py"),
              "comparisons": {case: {"differences": []} for case in module.CASES}, "inputs": inputs}
put(module.HERE / "corpus_comparison_v1.json", comparison)
assert not module.G1.exists()
namespace = {**vars(module), "freeze": freeze, "freeze_path": freeze_path}
exec(compile(block, str(SOURCE), "exec"), namespace)
assert not (module.HERE / "results_manifest_v1.json").exists()
print(json.dumps({"schema": "semabi.g2.comparison_gate_review.v1", "original_source_sha256": EXPECTED,
    "checked_subsection": "comparison_path assignment through corpus loop; before required_reports",
    "invented_filesystem_only": True, "comparison_gate_accepted_without_any_g1_files": True,
    "comparison_input_entries": len(inputs), "real_sealer_executed": False,
    "real_preservation_manifest_written": False, "learner_imported": False}, indent=2, sort_keys=True))
