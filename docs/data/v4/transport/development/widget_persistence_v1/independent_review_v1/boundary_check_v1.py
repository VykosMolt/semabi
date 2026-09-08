"""One invented multi-pair/multi-slot W1 boundary; no fit or corpus execution."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
WIDGETS = ("combobox#0~", "textbox#0~")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(unit):
    return {"instances": [asdict(instance) for instance in unit.instances],
            "slots": {sid: {"id": stat.id, "n": stat.n, "values": dict(stat.values),
                             "unique_in_parent": stat.unique_in_parent, "crowded": stat.crowded,
                             "numeric": stat.numeric, "n_obs_values": dict(stat.n_obs_values)}
                      for sid, stat in unit.slots.items()}, "evidence": list(unit.evidence)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--input-sha256", required=True)
    parser.add_argument("--script-sha256", required=True)
    args = parser.parse_args()
    input_path, output = HERE / "invented_inputs_v1.json", HERE / "boundary_result_v1.json"
    require(not output.exists(), "Independent boundary result already exists")
    cache, imported, source_association, outcome, fatal = None, [], None, None, None
    original_prefix, original_bytecode = sys.pycache_prefix, sys.dont_write_bytecode
    try:
        require(sha(input_path) == args.input_sha256 and sha(Path(__file__)) == args.script_sha256,
                "Independent source or input commitment differs")
        inputs = json.loads(input_path.read_bytes())
        worktree = Path(inputs["worktree"])

        def recheck():
            for name, wanted in {**inputs["native_source_files"], **inputs["reviewed_evidence"]}.items():
                path = ROOT / name
                require(path.resolve() == path and not path.is_symlink() and sha(path) == wanted,
                        "Reviewed source/evidence changed: " + name)
            require(sha(worktree / "tests/test_v2_collection_variation.py") == inputs["candidate_test_sha256"], "Candidate test changed")
            require(sha(ROOT / "semabi/compiler/v2/hypotheses.py") == inputs["main_hypotheses_sha256"], "Main native source changed")
            require(sha(input_path) == args.input_sha256 and sha(Path(__file__)) == args.script_sha256, "Independent inputs changed")
            for directory in (ROOT, worktree):
                require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip() == inputs["source_head"],
                        "Main or worktree HEAD changed")

        recheck()
        package = HERE.parent
        before_manifest = json.loads((package / "source_before/manifest.json").read_bytes())
        candidate_manifest = json.loads((package / "source_candidate_v1/manifest.json").read_bytes())
        base_job = json.loads((package / "jobs/base_focused_v1/process.json").read_bytes())
        candidate_job = json.loads((package / "jobs/candidate_focused_v1/process.json").read_bytes())
        for manifest in (before_manifest, candidate_manifest):
            require(manifest["files"]["tests/test_v2_collection_variation.py"]["sha256"] == inputs["candidate_test_sha256"],
                    "Focused tests differ between source snapshots")
            for value in manifest["files"].values():
                require(sha(ROOT / value["snapshot"]) == value["sha256"], "Source snapshot differs")
        jobs = []
        for name, job, expected_status, returncode in (("base_focused_v1", base_job, "FAILED", 1),
                                                      ("candidate_focused_v1", candidate_job, "FINISHED", 0)):
            require(job["status"] == expected_status and job["returncode"] == returncode and job["child_terminated"] is True
                    and job["cwd"] == str(worktree) and job["owner"] == "/root", "Focused process identity/status differs")
            require(sha(package / "jobs" / name / "output.log") == job["log_sha256"], "Focused log digest differs")
            jobs.append({"name": name, "returncode": returncode, "child_pid": job["child_pid"],
                         "child_terminated": True, "hypotheses_sha256": job["source_hashes"]["semabi/compiler/v2/hypotheses.py"],
                         "log_sha256": job["log_sha256"]})
        differences = sorted(name for name in set(base_job["source_hashes"]) | set(candidate_job["source_hashes"])
                             if base_job["source_hashes"].get(name) != candidate_job["source_hashes"].get(name))
        require(differences == ["semabi/compiler/v2/hypotheses.py"], "Recorded native inventory changed outside W1")
        require(base_job["source_hashes"][differences[0]] == before_manifest["files"][differences[0]]["sha256"]
                and candidate_job["source_hashes"][differences[0]] == candidate_manifest["files"][differences[0]]["sha256"],
                "Executed native source differs from the held snapshots")
        source_association = {"jobs": jobs, "recorded_native_inventory_differences": differences,
                              "identical_test_snapshot_sha256": inputs["candidate_test_sha256"]}
        require(os.sched_getaffinity(0) == {22}, "Independent CPU ownership differs")
        require(not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules), "Preloaded semabi module")
        cache = Path(tempfile.mkdtemp(prefix="source_import_cache-", dir=HERE))
        require(not list(cache.iterdir()), "Independent import cache was not empty")
        sys.pycache_prefix, sys.dont_write_bytecode = str(cache), True
        sys.path.insert(0, str(worktree))
        native = importlib.import_module("semabi.compiler.v2.hypotheses")
        graph = importlib.import_module("semabi.compiler.v2.graph")
        for name in sorted(name for name in sys.modules if name == "semabi" or name.startswith("semabi.")):
            path = Path(sys.modules[name].__file__)
            relative = str(path.relative_to(ROOT))
            require(relative in inputs["native_source_files"] and sha(path) == inputs["native_source_files"][relative],
                    "Native import came from an unbound source: " + name)
            imported.append({"module": name, "path": relative, "sha256": sha(path)})
        hypothesis = native.Hypotheses(graph.ObsGraph())
        hypothesis.reload_pairs = [tuple(pair) for pair in inputs["reload_pairs"]]
        units = []
        for specification in (inputs["ambiguous_template"], inputs["unrelated_template"]):
            instances = []
            for sig, rows in specification["observations"].items():
                for index, (parent, key, value, other) in enumerate(rows):
                    root = 100 + index * 4
                    instances.append(native.UnitInstance(sig, root, specification["name"],
                        {"label#0": key, WIDGETS[0]: value, WIDGETS[1]: other},
                        {"label#0": root + 1, WIDGETS[0]: root + 2, WIDGETS[1]: root + 3}, [], parent))
            unit = native.UnitHyp(specification["name"], instances, key_slot="label#0",
                                  max_per_obs=max(Counter(instance.sig for instance in instances).values()))
            hypothesis._slot_stats(unit)
            hypothesis.units[unit.template] = unit
            units.append(unit)
        ambiguous, unrelated = units
        before = {unit.template: snapshot(unit) for unit in units}
        hypothesis._promote_persistent_widgets()
        after = {unit.template: snapshot(unit) for unit in units}
        require(after[ambiguous.template]["instances"] == before[ambiguous.template]["instances"]
                and after[ambiguous.template]["slots"] == before[ambiguous.template]["slots"],
                "Later-pair ambiguity allowed a partial slot promotion or changed input metadata")
        require(len(ambiguous.evidence) == 1 and "ambiguous within a reload observation" in ambiguous.evidence[0],
                "Ambiguous correspondence was not recorded")
        require(hypothesis.persistent_widgets == {(unrelated.template, sid[:-1]) for sid in WIDGETS},
                "Ambiguity leaked across templates or allowed an ambiguous promotion")
        for old, new in zip(before[unrelated.template]["instances"], unrelated.instances, strict=True):
            for sid in WIDGETS:
                require(sid not in new.slots and sid not in new.slot_nodes
                        and new.slots[sid[:-1]] == old["slots"][sid]
                        and new.slot_nodes[sid[:-1]] == old["slot_nodes"][sid], "Unrelated positive changed its values or associations")
        require(all(unrelated.slots[sid[:-1]].n == len(unrelated.instances) for sid in WIDGETS), "Positive slot stats were not refreshed")
        require(not list(cache.rglob("*")), "Native imports wrote bytecode cache files")
        recheck()
        outcome = {"status": "PASS", "reload_pairs": inputs["reload_pairs"], "template_order": [unit.template for unit in units],
                   "before": before, "after": after, "persistent_widgets": sorted(hypothesis.persistent_widgets),
                   "ambiguous_slots_withheld": list(WIDGETS), "unrelated_slots_promoted": [sid[:-1] for sid in WIDGETS],
                   "ambiguous_values_nodes_stats_unchanged": True, "unrelated_values_nodes_preserved": True,
                   "stubs": [], "graph_observations": len(hypothesis.G.obs)}
    except BaseException as error:
        fatal = {"type": type(error).__name__, "detail": str(error)}
    finally:
        sys.pycache_prefix, sys.dont_write_bytecode = original_prefix, original_bytecode
    result = {"schema": "semabi.w1.independent_boundary_result.v1", "status": "PASS" if fatal is None else "FAIL",
              "fatal_error": fatal, "source_association": source_association, "boundary": outcome,
              "inputs_sha256": args.input_sha256, "script_sha256": args.script_sha256, "native_imports": imported,
              "unique_cache_prefix": None if cache is None else str(cache.relative_to(ROOT)),
              "cache_empty_after": cache is not None and not list(cache.rglob("*")),
              "execution": {"owner": "/root/sidecar_review", "pid": os.getpid(), "ppid": os.getppid(),
                            "cpu_affinity": sorted(os.sched_getaffinity(0)), "environment": {name: os.environ.get(name) for name in (
                                "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
                                "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE")}},
              "scope": "One direct invented native-unit boundary with two reload pairs, two widget slots and two templates. No stubs, Fit, full tests, corpora, prediction, browser or actual J1 payload."}
    with output.open("x") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"status": result["status"], "out": str(output.relative_to(ROOT)), "sha256": sha(output),
                      "fatal_error": fatal}, sort_keys=True))
    return 0 if fatal is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
