"""Compare complete G1/G2 corpus semantics under the predeclared projection."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
G1 = HERE.parent / "g1"
CASES = ("allocation_positive", "allocation_refusals", "pilot", "separating", "separating_extended")
COMPONENTS = ("reading", "fit", "dev_steps", "outcome_cut", "development", "holdout")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def differences(a, b, path=""):
    if type(a) is not type(b):
        return [{"path": path, "G1": a, "G2": b, "kind": "type"}]
    if isinstance(a, dict):
        result = []
        for key in sorted(set(a) | set(b)):
            child = path + "/" + str(key).replace("~", "~0").replace("/", "~1")
            if key not in a or key not in b:
                row = {"path": child, "kind": "added" if key not in a else "removed"}
                row.update({"G2": b[key]} if key not in a else {"G1": a[key]})
                result.append(row)
            else:
                result.extend(differences(a[key], b[key], child))
        return result
    if isinstance(a, list):
        result = []
        for i in range(max(len(a), len(b))):
            if i >= len(a) or i >= len(b):
                row = {"path": f"{path}/{i}", "kind": "added" if i >= len(a) else "removed"}
                row.update({"G2": b[i]} if i >= len(a) else {"G1": a[i]})
                result.append(row)
            else:
                result.extend(differences(a[i], b[i], f"{path}/{i}"))
        return result
    return [] if a == b else [{"path": path, "G1": a, "G2": b, "kind": "value"}]


def main():
    output = HERE / "corpus_comparison_v1.json"
    if output.exists():
        raise FileExistsError(output)
    inputs = {}

    def read(path):
        raw = path.read_bytes()
        inputs[str(path.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    phases = {"G1": G1, "G2": HERE}
    freezes = {name: read(base / "freeze_v1.json") for name, base in phases.items()}
    assert freezes["G1"]["schema"] == "semabi.transport.development_freeze.v1"
    assert freezes["G2"]["schema"] == "semabi.transport.g2_development_freeze.v1"
    assert freezes["G2"]["prior_development"] == {
        "path": str((G1 / "freeze_v1.json").relative_to(ROOT)), "sha256": sha(G1 / "freeze_v1.json")}
    assert freezes["G1"]["corpora"] == freezes["G2"]["corpora"]
    corpus_info = freezes["G2"]["corpora"]
    corpus_manifest_path = ROOT / corpus_info["manifest"]
    assert sha(corpus_manifest_path) == corpus_info["manifest_sha256"]
    corpus_manifest = read(corpus_manifest_path)
    corpus_root = (ROOT / corpus_info["root"]).resolve()
    assert corpus_manifest["root"] == corpus_info["root"]
    assert sha(Path(__file__)) == freezes["G2"]["verification_files"][str(Path(__file__).relative_to(ROOT))]
    g1_manifest = read(G1 / "results_manifest_v1.json")
    assert sha(G1 / "results_manifest_v1.json") == freezes["G2"]["verification_files"][
        str((G1 / "results_manifest_v1.json").relative_to(ROOT))]
    results = {}
    for case in CASES:
        values = {}
        consumed = {}
        for phase, base in phases.items():
            directory = base / "corpora" / case
            path = directory / f"{case}.json"
            result = read(path)
            if phase == "G1":
                assert sha(path) == g1_manifest["files"][str(path.relative_to(ROOT))]["sha256"]
            freeze_path = base / "freeze_v1.json"
            snapshot = directory / "source_snapshot.json"
            assert read(snapshot) == freezes[phase]
            assert result["provenance"]["source_snapshot_sha256"] == sha(snapshot) == sha(freeze_path)
            inner_path = directory / f"{case}_process.json"
            inner = read(inner_path)
            if phase == "G1":
                assert sha(inner_path) == g1_manifest["files"][str(inner_path.relative_to(ROOT))]["sha256"]
            assert inner["state"] == "completed" and inner["case"] == case
            assert inner["result_sha256"] == sha(path) and inner["changed_inputs"] == []
            assert inner["source_snapshot_sha256"] == sha(snapshot)
            measurement_path = "docs/data/v4/transport/baseline/check_corpora.py"
            assert inner["instrument_sha256"] == freezes[phase]["verification_files"][measurement_path]
            consumed[phase] = result["provenance"]["input_files"]
            assert inner["input_files"] == consumed[phase]
            for name, expected in consumed[phase].items():
                input_path = Path(name)
                relative = input_path.resolve().relative_to(corpus_root).as_posix()
                assert input_path == corpus_root / relative
                assert corpus_manifest["files"][relative] == expected == sha(input_path)
                inputs[str(input_path.relative_to(ROOT))] = expected
            job_path = base / "jobs" / f"corpus_{case}" / "process.json"
            job = read(job_path)
            assert job["status"] == "FINISHED" and job["returncode"] == 0 and job["child_terminated"]
            assert job["source_head"] == freezes[phase]["source_head"]
            assert job["command"] == [".venv/bin/python", "-B", str((base / "run_corpus.py").relative_to(ROOT)),
                                      case, str(directory.relative_to(ROOT)), str(freeze_path.relative_to(ROOT))]
            assert job["cwd"] == str(ROOT)
            assert job["python_hash_seed"] == "0" and job["thread_limits"] == {
                "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1"}
            assert sha(job_path.parent / "output.log") == job["log_sha256"]
            for name, expected in freezes[phase]["files"].items():
                if name.startswith("semabi/"):
                    assert job["source_hashes"][name] == expected
            assert set(result) == {"provenance", *COMPONENTS}
            projection = copy.deepcopy({key: result[key] for key in COMPONENTS})
            projection["reading"]["provenance"].pop("source_run", None)
            values[phase] = projection
        assert consumed["G1"] == consumed["G2"], f"Consumed inputs differ: {case}"
        results[case] = {
            "components_equal": {key: values["G1"][key] == values["G2"][key] for key in COMPONENTS},
            "differences": differences(values["G1"], values["G2"]),
            "semantic_payloads_equal": values["G1"] == values["G2"],
        }
    for name, expected in inputs.items():
        assert sha(ROOT / name) == expected, f"Input changed during comparison: {name}"
    record = {"schema": "semabi.transport.g2_corpus_comparison.v1", "inputs": inputs,
              "source_sha256": sha(Path(__file__)), "comparisons": results,
              "projection": "All reading/fit/dev_steps/outcome_cut/development/holdout fields; "
                            "only reading.provenance.source_run and top-level execution provenance excluded.",
              "scope": "Same-seed retained G1 to G2 regression. Every difference retained; no transport claim."}
    with output.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "sha256": sha(output),
                      "differences": {name: len(row["differences"]) for name, row in results.items()}}))


if __name__ == "__main__":
    main()
