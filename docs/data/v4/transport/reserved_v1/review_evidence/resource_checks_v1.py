"""Independent narrow resource checks on invented records and public source only."""
from __future__ import annotations

import ast
from collections import Counter
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[6]
HERE = ROOT / "docs/data/v4/transport/reserved_v1"
OUT = HERE / "review_evidence"
COUNTS = Counter()


def require(condition, name):
    if not condition:
        raise AssertionError(name)
    COUNTS[name] += 1


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, name):
    module = ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_text(), str(path), "exec"), module.__dict__)
    return module


def helper_functions(preserver, base):
    path = OUT / "job_inventory_review_v1.py"
    tree = ast.parse(path.read_text())
    names = {"sha", "stamp", "setup", "alter", "extra_job", "extra_file", "extra_symlink", "replace_directory"}
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    require({node.name for node in body} == names, "retained synthetic helpers found")
    module = ModuleType("invented_resource_helpers")
    module.__dict__.update(module=preserver, BASE=base, HEAD="invented-source-head", Path=Path,
                           datetime=datetime, timedelta=timedelta, timezone=timezone,
                           hashlib=hashlib, json=json, deepcopy=deepcopy)
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), module.__dict__)
    return module


def source_continuity():
    old = (HERE / "instrument_revisions/preserve_first_pass.py.before_resource_restore.txt").read_text()
    current = (HERE / "preserve_first_pass.py").read_text()
    revised = old.replace(
        'HERE / "custody_review_v1.md", HERE / "freeze.py", HELPER, RUNNER,',
        'HERE / "custody_review_v1.md", HERE / "resource_review_v1.md",\n'
        '                TRANSPORT / "development/g2/resource_override_v3.json", HERE / "freeze.py", HELPER, RUNNER,')
    revised = revised.replace('    for left, right in zip(scores, scores[1:]):\n'
                              '        require(time(left["end_utc"]) <= time(right["start_utc"]), "Score jobs overlapped")\n', '')
    require(revised == current, "preserver has only approved dependency and score-overlap edits")
    old = (HERE / "instrument_revisions/freeze.py.before_resource_restore.txt").read_text()
    current = (HERE / "freeze.py").read_text()
    revised = old.replace('"preserve_first_pass.py", "summarize.py", "custody_plan_v1.md", "custody_review_v1.md",\n',
                          '"preserve_first_pass.py", "summarize.py", "custody_plan_v1.md", "custody_review_v1.md",\n'
                          '        "resource_review_v1.md",\n')
    revised = revised.replace('    verification = {relative(p): sha(p) for p in verification_paths}\n',
                              '    verification_paths.append(TRANSPORT / "development/g2/resource_override_v3.json")\n'
                              '    verification = {relative(p): sha(p) for p in verification_paths}\n')
    revised = revised.replace('"heavy_workers": 1,', '"heavy_workers": 24,')
    require(revised == current, "freezer has only approved dependencies and worker-ceiling edits")
    for name in ("preserve_first_pass.py", "freeze.py"):
        draft = (HERE / "instrument_revisions" / (name + ".before_all_24_cpus.txt")).read_text()
        revised = draft.replace("resource_override_v2.json", "resource_override_v3.json")
        if name == "freeze.py":
            revised = revised.replace('"heavy_workers": 12,', '"heavy_workers": 24,')
        require(revised == (HERE / name).read_text(), "24-CPU source differs from unexecuted draft only as declared")


def dependency_paths():
    """Run only unconditional public dependency-list construction, with no I/O."""
    path = HERE / "freeze.py"
    tree = ast.parse(path.read_text())
    build = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build")
    def assigns(node, name):
        return isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    start = next(index for index, node in enumerate(build.body) if assigns(node, "verification_paths"))
    stop = next(index for index, node in enumerate(build.body) if assigns(node, "verification"))
    campaign = next(index for index, node in enumerate(build.body) if isinstance(node, ast.If)
                    and ast.unparse(node.test) == "stage == 'campaign'")
    require(start < stop < campaign, "verification inventory constructed before phase branch")
    record = next(node.value for node in build.body if assigns(node, "record"))
    record_entries = dict(zip((key.value for key in record.keys), record.values))
    require(isinstance(record_entries["verification_files"], ast.Name)
            and record_entries["verification_files"].id == "verification", "both phases emit the common verification inventory")
    resource = record_entries["resource"]
    resource_entries = dict(zip((key.value for key in resource.keys), resource.values))
    require(ast.literal_eval(resource_entries["heavy_workers"]) == 24
            and ast.literal_eval(resource_entries["numerical_threads"]) == 1
            and ast.literal_eval(resource_entries["python_hash_seed"]) == "0", "freezer records ceiling 24 and unchanged numerical settings")
    fake_root = Path("/invented_resource_root")
    fake_here = fake_root / "docs/data/v4/transport/reserved_v1"
    expected = {"docs/data/v4/transport/reserved_v1/resource_review_v1.md",
                "docs/data/v4/transport/development/g2/resource_override_v3.json"}
    maps = []
    for stage in ("implementation", "campaign"):
        namespace = {"HERE": fake_here, "TRANSPORT": fake_here.parent, "ROOT": fake_root,
                     "stage": stage, "result_path": fake_root / "invented_results.json",
                     "prior_path": fake_root / "invented_prior.json",
                     "relative": lambda value: str(value.relative_to(fake_root)),
                     "sha": lambda value: hashlib.sha256(str(value).encode()).hexdigest()}
        exec(compile(ast.Module(body=build.body[start:stop + 1], type_ignores=[]), str(path), "exec"), namespace)
        require(expected <= set(namespace["verification"]), "new review and v3 record in each phase verification list")
        maps.append(namespace["verification"])
    require(maps[0] == maps[1], "both phase dependency commitments identical")
    preserver = ast.parse((HERE / "preserve_first_pass.py").read_text())
    freezes = next(node for node in preserver.body if isinstance(node, ast.FunctionDef) and node.name == "freezes")
    required = next(node for node in freezes.body if assigns(node, "required"))
    namespace = {"Path": Path, "__file__": str(fake_here / "preserve_first_pass.py"),
                 "HERE": fake_here, "TRANSPORT": fake_here.parent,
                 "HELPER": fake_here.parent / "acquisition_summary.py", "RUNNER": fake_here.parent / "run_job.py"}
    exec(compile(ast.Module(body=[required], type_ignores=[]), str(HERE / "preserve_first_pass.py"), "exec"), namespace)
    require(expected <= {str(value.relative_to(fake_root)) for value in namespace["required"]},
            "preserver requires both new verification dependencies")
    return {"executed_scope": "unchanged unconditional AST dependency-list statements only; invented path strings and hashes; no freezer build",
            "phase_verification_entries": len(maps[0]), "required_new_paths": sorted(expected)}


def job_checks(base):
    rows = []
    sources = {"current_24": HERE / "preserve_first_pass.py",
               "archived_one": HERE / "instrument_revisions/preserve_first_pass.py.before_resource_restore.txt",
               "archived_twelve": HERE / "instrument_revisions/preserve_first_pass.py.before_all_24_cpus.txt"}
    for version, path in sources.items():
        module = load(path, "resource_review_" + version)
        helper = helper_functions(module, base)

        def overlap(root, here, names, records):
            for index, name in enumerate("score_" + stage for stage in module.STAGES):
                helper.alter(here, name, records[name], start_utc=helper.stamp(21), end_utc=helper.stamp(25 + index))

        def hidden(root, here, names, records):
            path = here / "jobs/.unreported_running_score"
            path.mkdir()
            (path / "process.json").write_text(json.dumps({"status": "RUNNING", "child_terminated": False}))

        def update(name_fn, **changes):
            return lambda root, here, names, records: helper.alter(here, name_fn(names), records[name_fn(names)], **changes)

        checks = [("sequential_fixed_13", lambda *args: None, True),
                  ("all_five_scores_overlap_after_service", overlap, version != "archived_one")]
        if version == "current_24":
            checks += [
                ("score_starts_at_service_end", update(lambda names: names[8], start_utc=helper.stamp(20)), True),
                ("score_before_service_reaping", update(lambda names: names[8], start_utc=helper.stamp(19)), False),
                ("service_ends_after_scoring", update(lambda names: names[0], end_utc=helper.stamp(50)), False),
                ("service_ends_before_evaluation", update(lambda names: names[0], end_utc=helper.stamp(1)), False),
                ("overlapping_acquisition_arms", update(lambda names: names[4], start_utc=helper.stamp(5)), False),
                ("overlapping_initial_preparation", update(lambda names: names[2], start_utc=helper.stamp(1)), False),
                ("overlapping_evaluation", update(lambda names: names[7], start_utc=helper.stamp(11)), False),
                ("hidden_running_job", hidden, False),
                ("extra_running_job", helper.extra_job, False),
                ("running_expected_score", update(lambda names: names[8], status="RUNNING", returncode=None, child_terminated=False), False),
                ("unreaped_expected_score", update(lambda names: names[8], child_terminated=False), False),
                ("failed_expected_score", update(lambda names: names[8], status="FAILED", returncode=1), False),
                ("wrong_score_source", update(lambda names: names[8], source_head="foreign-head"), False),
                ("changed_score_log", lambda root, here, names, records: (here / "jobs" / names[8] / "output.log").write_text("changed\n"), False),
                ("extra_top_file", helper.extra_file, False),
                ("extra_top_symlink", helper.extra_symlink, False),
                ("expected_directory_symlink", helper.replace_directory, False),
            ]
        for label, mutate, accepted in checks:
            root, here, names, records, campaign = helper.setup(version + "_" + label)
            mutate(root, here, names, records)
            try:
                actual = module.jobs(module.Inventory(), helper.HEAD, campaign)
                status, detail = True, {"jobs": len(actual)}
            except (ValueError, OSError, KeyError) as error:
                status, detail = False, {"error": str(error)}
            require(status == accepted, "resource scheduling case meets frozen expectation")
            rows.append({"source_version": version, "case": label, "expected_accepted": accepted,
                         "observed_accepted": status, **detail})
        if version == "current_24":
            root, here, names, records, campaign = helper.setup("current_24_late_hidden_job")
            overlap(root, here, names, records)
            inventory = module.Inventory()
            require(len(module.jobs(inventory, helper.HEAD, campaign)) == 13, "overlapped-score inventory initially complete")
            hidden(root, here, names, records)
            try:
                inventory.verify_unchanged()
            except ValueError as error:
                require(True, "late hidden job fails final inventory recheck")
                rows.append({"source_version": version, "case": "late_hidden_job", "expected_accepted": False,
                             "observed_accepted": False, "error": str(error)})
            else:
                raise AssertionError("Late hidden job accepted")
    return rows


def main():
    manifest_path = OUT / "resource_source_manifest_v1.json"
    manifest = json.loads(manifest_path.read_text())
    for relative, expected in manifest["sha256"].items():
        require(sha(ROOT / relative) == expected, "review input precheck fingerprint")
    source_continuity()
    dependency = dependency_paths()
    with tempfile.TemporaryDirectory(prefix="resource_tmp_", dir=OUT) as temporary:
        jobs = job_checks(Path(temporary))
    resource = json.loads((ROOT / "docs/data/v4/transport/development/g2/resource_override_v3.json").read_text())
    require(resource["maximum_logical_cpus"] == 24 and resource["worker_cpu_pool"] == list(range(24))
            and resource["new_worker_nice"] == 0 and resource["numerical_threads_per_worker"] == 1
            and resource["python_hash_seed"] == "0", "public resource v3 matches all-24 instruction")
    require(not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules), "no native SemABI import")
    for relative, expected in manifest["sha256"].items():
        require(sha(ROOT / relative) == expected, "review input postcheck fingerprint")
    result = {"schema": "semabi.r1.resource_review_checks.v1", "status": "PASS",
              "source_manifest_sha256": sha(manifest_path), "assertions": sum(COUNTS.values()),
              "assertion_classes": len(COUNTS), "checks": dict(COUNTS), "job_cases": jobs,
              "job_case_count": len(jobs), "dependency_construction": dependency,
              "cpu_affinity": sorted(os.sched_getaffinity(0)), "nice": os.getpriority(os.PRIO_PROCESS, 0),
              "execution_scope": "public stdlib instrument source, unchanged synthetic helper functions, invented temporary job records and AST dependency-list construction only",
              "native_imports_browser_server_fits_actual_r1_records": False,
              "actual_freeze_build_or_preservation_executed": False}
    with (OUT / "resource_results_v1.json").open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "assertions": sum(COUNTS.values()), "job_cases": len(jobs),
                      "actual_r1_execution": False}))


if __name__ == "__main__":
    main()
