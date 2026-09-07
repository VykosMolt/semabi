"""Invented-only focused controls for corrected preservation and result boundaries."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1] / "evaluation_preservation_checks_v1.py"
BASE_SHA = "e7b7adf30461016c893aca4016986568a81a8f434b48003dd54467c092ff62ab"
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == BASE_SHA
spec = importlib.util.spec_from_file_location("_focused_base_harness", BASE)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)
h.HELD = HERE / "held_sources"
# Suite.finish binds the script actually scheduling these focused cases.
h.__file__ = __file__


def assert_reject_without_output(c, destination, *, mode, fragment):
    try:
        c.evaluate(destination) if mode == "evaluate" else c.preserve(destination)
    except Exception as error:
        assert fragment in str(error), str(error)
        assert not destination.exists() and not destination.is_symlink()
        assert c.helper_calls == 0, "Rejected destination reached native helpers"
        return {"rejection": str(error), "native_helper_calls": 0}
    raise AssertionError("Protected output destination was accepted")


def descendant(c, index, mode):
    if mode == "evaluate":
        c.preserve()
    root = c.root / c.e.output_roots(c.frozen)[index]
    # A future control-file identity must remain protected even when absent.
    if root.is_file():
        root.unlink()
    return assert_reject_without_output(c, root / "invented_result.json", mode=mode,
                                       fragment="overlaps frozen evidence")


def sibling(c, index, mode):
    root = c.root / c.e.output_roots(c.frozen)[index]
    out = Path(str(root) + "_disjoint_review.json")
    if mode == "evaluate":
        c.preserve()
        code, result = c.evaluate(out)
        assert code == 0 and c.helper_calls == 1
        h.full_denominators(result, invalid=False)
        c.e.verify_preservation(c.frozen, c.freeze_path, c.preserved_path)
    else:
        result = c.preserve(out)
        assert result["status"] == "PRESERVED"
        c.e.verify_preservation(c.frozen, c.freeze_path, out)
    return {"sibling_allowed": True, "preservation_still_valid": True}


def future_ancestor(c, kind, mode):
    parent = h.OUTPUT + "/invented_future_" + kind
    target = parent + "/reserved_identity"
    if kind == "predictor":
        c.frozen["predictor_directory"] = target
    elif kind == "receipts":
        c.frozen["execution_receipts_directory"] = target
    elif kind == "control":
        c.frozen["controls"][0]["path"] = target + ".json"
    elif kind == "job":
        c.frozen["jobs"][0]["path"] = target
    else:
        raise AssertionError(kind)
    c.write(c.freeze_path, c.frozen)
    if mode == "evaluate":
        c.preserve()
    assert not (c.root / parent).exists()
    return assert_reject_without_output(c, c.root / parent, mode=mode,
                                       fragment="overlaps frozen evidence")


def input_identity(c, kind, mode):
    if mode == "evaluate" or kind == "preserved":
        c.preserve()
    out = {"source": c.here / "trace.py", "fixed": c.root / c.frozen["actor_freeze"]["path"],
           "freeze": c.freeze_path, "preserved": c.preserved_path}[kind]
    before = out.read_bytes()
    try:
        c.evaluate(out) if mode == "evaluate" else c.preserve(out)
    except Exception as error:
        assert "identity already exists" in str(error), str(error)
        assert out.read_bytes() == before and c.helper_calls == 0
        return {"input_unchanged": True, "native_helper_calls": 0}
    raise AssertionError("Existing input identity was overwritten")


def future_protected_input(c, kind, relation):
    identity = c.root / h.OUTPUT / ("invented_uncreated_" + kind) / "identity.json"
    protected = ()
    if kind in {"source", "fixed"}:
        mapping = "source_files" if kind == "source" else "fixed_inputs"
        c.frozen[mapping][str(identity.relative_to(c.root))] = "f" * 64
    else:
        protected = (identity,)
    out = {"exact": identity, "ancestor": identity.parent, "descendant": identity / "result.json"}[relation]
    try:
        c.e.validate_output_destination(c.frozen, out, protected_inputs=protected)
    except Exception as error:
        assert "overlaps frozen evidence" in str(error), str(error)
        assert not out.exists()
        return {"future_input_guarded": True, "relation": relation}
    raise AssertionError("A missing protected input identity was accepted as output")


def symlink_parent(c, mode, *, dangling=False):
    if mode == "evaluate":
        c.preserve()
    real = c.root / h.OUTPUT / "invented_actual_parent"
    alias = c.root / h.OUTPUT / "invented_alias_parent"
    if not dangling:
        real.mkdir()
    alias.symlink_to(real, target_is_directory=True)
    result = assert_reject_without_output(c, alias / "result.json", mode=mode,
                                         fragment="path is not canonical")
    assert not (real / "result.json").exists()
    return result


def non_directory_parent(c, mode):
    if mode == "evaluate":
        c.preserve()
    parent = c.root / h.OUTPUT / "invented_regular_parent"
    c.write(parent, b"Invented non-directory parent\n")
    return assert_reject_without_output(c, parent / "result.json", mode=mode,
                                       fragment="parent is not a directory")


def metadata_path(c, kind):
    if kind == "process":
        return c.root / c.frozen["jobs"][0]["path"] / "process.json"
    return c.directory / (kind + ".json")


def metadata_partial(c, kind, raw):
    file = metadata_path(c, kind)
    c.write(file, raw)
    saved = file.read_bytes()
    manifest = c.preserve()
    assert manifest["status"] == "PRESERVED_PARTIAL"
    relative = str(file.relative_to(c.root))
    assert manifest["files"][relative] == hashlib.sha256(saved).hexdigest()
    assert file.read_bytes() == saved
    defect = next(row for row in manifest["job_completion_defects"] if row["path"] == relative)
    assert defect["reason"] == "UNREADABLE_PROCESS_METADATA" and defect["liveness"] == "UNKNOWN"
    c.e.verify_preservation(c.frozen, c.freeze_path, c.preserved_path)
    return {"raw_metadata_preserved": True, "liveness": defect["liveness"], "reason": defect["reason"]}


def pid_partial(c, kind, field, value, *, missing=False):
    file = metadata_path(c, kind)
    def mutate(row):
        row.pop(field, None) if missing else row.update({field: value})
    c.alter(file, mutate)
    manifest = c.preserve()
    assert manifest["status"] == "PRESERVED_PARTIAL"
    relative = str(file.relative_to(c.root))
    defect = next(row for row in manifest["job_completion_defects"]
                  if row["path"] == relative and row["reason"] == "UNKNOWN_PROCESS_IDENTITY")
    assert field in defect["fields"] and defect["liveness"] == "UNKNOWN"
    assert manifest["files"][relative] == h.sha(file)
    return {"unknown_field": field, "liveness": "UNKNOWN", "raw_metadata_preserved": True}


def malformed_then_live(c, malformed_kind, live_kind, live_field):
    bad = metadata_path(c, malformed_kind)
    c.write(bad, b'{"invented_truncation":')
    if live_kind == "other_process":
        file = c.root / c.frozen["jobs"][1]["path"] / "process.json"
    else:
        file = metadata_path(c, live_kind)
    assert file != bad
    c.alter(file, lambda row: row.update({live_field: 1}))
    assert Path("/proc/1").exists(), "Review requires a known present PID for the liveness control"
    try:
        c.preserve()
    except Exception as error:
        assert "owned job PID is present" in str(error), str(error)
        assert not c.preserved_path.exists()
        assert bad.read_bytes() == b'{"invented_truncation":'
        return {"known_live_pid_blocks_sealing": True, "no_manifest_written": True}
    raise AssertionError("Malformed metadata hid a known live owned PID")


def status_partial(c, value):
    file = metadata_path(c, "process")
    c.alter(file, lambda row: row.update(status=value))
    manifest = c.preserve()
    assert manifest["status"] == "PRESERVED_PARTIAL"
    assert any(row["reason"] == "MISSING_TERMINAL_CUSTODY" for row in manifest["job_completion_defects"])
    assert manifest["files"][str(file.relative_to(c.root))] == h.sha(file)
    return {"malformed_status_preserved": True}


def late_inventory_change(c, source):
    c.preserve()
    def changed_helpers():
        helpers = c.native_helpers()
        if source:
            c.write(c.here / "trace.py", b"# Invented late source mutation\n")
        else:
            c.write(c.directory / "invented_late_output.json", {"invented_late_change": True})
        return helpers
    c.e.native_helpers = changed_helpers
    try:
        c.evaluate()
    except Exception as error:
        assert ("Frozen input changed" if source else "artifact inventory changed") in str(error), str(error)
        assert c.helper_calls == 1 and not c.score_path.exists()
        return {"final_inventory_gate_rejects_without_score": True}
    raise AssertionError("An inventory change during evaluation was admitted")


def main():
    before_native = {name for name in sys.modules if name == "semabi" or name.startswith("semabi.")}
    suite = h.Suite(HERE / "focused_results")
    labels = ["predictor", "receipts", "primary", "invariance", "primary_control", "invariance_control", "shutdown_control",
              "invariance_actor_job", "invariance_checkpoint_job", "invariance_service_job", "predictor_job",
              "primary_actor_job", "primary_checkpoint_job", "primary_service_job", "shutdown_job"]
    for index, label in enumerate(labels):
        for mode in ("evaluate", "preserve"):
            suite.check(mode + "_rejects_descendant_" + label,
                        lambda c, index=index, mode=mode: descendant(c, index, mode))
            suite.check(mode + "_allows_disjoint_prefix_sibling_" + label,
                        lambda c, index=index, mode=mode: sibling(c, index, mode))
    for kind in ("predictor", "receipts", "control", "job"):
        for mode in ("evaluate", "preserve"):
            suite.check(mode + "_rejects_future_root_ancestor_" + kind,
                        lambda c, kind=kind, mode=mode: future_ancestor(c, kind, mode))
    for kind in ("source", "fixed", "freeze", "preserved"):
        for mode in ("evaluate", "preserve"):
            suite.check(mode + "_protects_existing_" + kind,
                        lambda c, kind=kind, mode=mode: input_identity(c, kind, mode))
        for relation in ("exact", "ancestor", "descendant"):
            suite.check("future_" + kind + "_input_" + relation,
                        lambda c, kind=kind, relation=relation: future_protected_input(c, kind, relation))
    for mode in ("evaluate", "preserve"):
        for dangling in (False, True):
            suite.check(mode + "_refuses_" + ("dangling_" if dangling else "") + "symlink_parent",
                        lambda c, mode=mode, dangling=dangling: symlink_parent(c, mode, dangling=dangling))
        suite.check(mode + "_refuses_nondirectory_parent", lambda c, mode=mode: non_directory_parent(c, mode))
    for kind in ("process", "startup", "ready"):
        for label, raw in (("truncated", b'{"invented_truncation":'), ("array", []),
                           ("duplicate_keys", b'{"pid":4,"pid":5}\n')):
            suite.check(kind + "_" + label + "_hashes_raw_and_marks_unknown",
                        lambda c, kind=kind, raw=raw: metadata_partial(c, kind, raw))
        fields = ("runner_pid", "child_pid") if kind == "process" else ("pid",)
        for field in fields:
            for label, value in (("none", None), ("zero", 0), ("negative", -1), ("true", True), ("false", False),
                                 ("string", "1"), ("array", []), ("object", {})):
                suite.check(kind + "_" + field + "_" + label + "_explicit_unknown",
                            lambda c, kind=kind, field=field, value=value: pid_partial(c, kind, field, value))
            suite.check(kind + "_" + field + "_missing_explicit_unknown",
                        lambda c, kind=kind, field=field: pid_partial(c, kind, field, None, missing=True))
    live_cases = [("process", "other_process", "runner_pid"), ("process", "other_process", "child_pid"),
                  ("process", "startup", "pid"), ("process", "ready", "pid"),
                  ("startup", "ready", "pid"), ("ready", "startup", "pid")]
    for malformed_kind, live_kind, field in live_cases:
        suite.check("malformed_" + malformed_kind + "_cannot_hide_live_" + live_kind + "_" + field,
                    lambda c, malformed_kind=malformed_kind, live_kind=live_kind, field=field:
                        malformed_then_live(c, malformed_kind, live_kind, field))
    for label, value in (("array", ["FINISHED"]), ("object", {"status": "FINISHED"})):
        suite.check("malformed_status_" + label + "_partial", lambda c, value=value: status_partial(c, value))
    for source in (False, True):
        suite.check("late_" + ("source" if source else "output") + "_mutation_not_admitted",
                    lambda c, source=source: late_inventory_change(c, source))
    after_native = {name for name in sys.modules if name == "semabi" or name.startswith("semabi.")}
    assert after_native == before_native, "Focused review imported a native module"
    return suite.finish()


if __name__ == "__main__":
    raise SystemExit(main())
