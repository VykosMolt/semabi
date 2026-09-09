"""Bounded driver error-path checks with no native imports or fit calls.

Only the actual main exception handlers, partial writer, finalizer and return
expression execute. The main try body, verify and origins are explicit synthetic
seams; these checks make no claim about native setup or the control's science.
"""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


class ControlSetupLimit(Exception):
    pass


CASES = (
    ("driver_admission", "driver", 0, False, False, None, "SETUP_LIMIT", "SETUP_LIMIT"),
    ("owner_admission", "control", 1, True, False, None, "SETUP_LIMIT", "SETUP_LIMIT"),
    ("unexpected_before_fit", "io", 0, False, False, None, "SETUP_LIMIT", "CONTROL_INCOMPLETE"),
    ("unexpected_during_fit", "type", 1, False, False, None, "FIT_INCOMPLETE", "CONTROL_INCOMPLETE"),
    ("unexpected_after_fit", "type", 1, True, False, None, "SETUP_LIMIT", "CONTROL_INCOMPLETE"),
    ("interrupt_before_control", "interrupt", 1, False, False, None, "FIT_INCOMPLETE", "CONTROL_INCOMPLETE"),
    ("exception_after_control_call", "control", 1, True, True, None, "CONTROL_INCOMPLETE", "CONTROL_INCOMPLETE"),
    ("postflight_failure", "driver", 0, False, False, "postflight", "SETUP_LIMIT", "CONTROL_INCOMPLETE"),
    ("partial_write_failure", "control", 1, True, False, "setup_partial_v1.json", "SETUP_LIMIT", "CONTROL_INCOMPLETE"),
    ("receipt_write_failure", None, 1, True, True, "execution_receipt_v1.json", "CONTROL_CAPTURED", "CONTROL_INCOMPLETE"),
    ("returned_setup_limit", None, 1, True, True, "returned_setup", "SETUP_LIMIT", "SETUP_LIMIT"),
    ("captured_control", None, 1, True, True, None, "CONTROL_CAPTURED", "CONTROL_CAPTURED"),
)


def exercise(path, case, expected):
    name, raised_kind, fit_calls, fit_returned, control_called, failure, _, _ = case
    tree = ast.parse(path.read_text(), filename=str(path))
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    guarded = next(node for node in main.body if isinstance(node, ast.Try))
    handlers = ast.dump(ast.Module(body=guarded.handlers + guarded.finalbody, type_ignores=[]), include_attributes=False)
    guarded.body = ast.parse("""
out = _out
freeze = {}
control = _control
copier = _copier
setup = _setup
fit_calls = _fit_calls
fit_returned = _fit_returned
control_called = _control_called
status = _returned_status
if _raised is not None:
    raise _raised
""").body
    assert handlers == ast.dump(ast.Module(body=guarded.handlers + guarded.finalbody, type_ignores=[]), include_attributes=False)
    namespace = {"__name__": "_j1_preparation_status_unit", "__file__": str(path)}
    exec(compile(ast.fix_missing_locations(tree), str(path), "exec"), namespace)
    errors = {"driver": namespace["SetupLimit"]("declared admission"),
              "control": ControlSetupLimit("owner unavailable"),
              "io": OSError("invented read failure"),
              "type": TypeError("invented runtime failure"),
              "interrupt": KeyboardInterrupt("invented interruption")}
    snapshots = {"retained_snapshot": {"synthetic": "stored rejected state"}}
    original_open = Path.open

    def checked_open(path, *args, **kwargs):
        if path.name == failure:
            raise OSError("invented exclusive write failure")
        return original_open(path, *args, **kwargs)

    def verify(*_args):
        if failure == "postflight":
            raise OSError("invented postflight read failure")
        return {}, {"synthetic_verification": True}

    def no_loader(*_args, **_kwargs):
        raise AssertionError("Native and control loading are forbidden in this status-only check")

    with TemporaryDirectory(prefix="j1-preparation-status-") as temporary:
        output = Path(temporary)
        namespace.update(_out=output, _control=SimpleNamespace(SetupLimit=ControlSetupLimit),
                         _copier=SimpleNamespace(snapshots=deepcopy(snapshots), errors=[]),
                         _setup={"states": {"synthetic": {"$snapshot": "retained_snapshot"}}},
                         _fit_calls=fit_calls, _fit_returned=fit_returned, _control_called=control_called,
                         _returned_status="SETUP_LIMIT" if failure == "returned_setup" else "CONTROL_CAPTURED",
                         _raised=errors.get(raised_kind), verify=verify,
                         origins=lambda *_args: {"synthetic_origins": True}, load_file=no_loader)
        stdout = StringIO()
        argv = [str(path), "--freeze", str(output / "unused.freeze"), "--freeze-sha256", "synthetic",
                "--output-identity", "synthetic-status-unit"]
        with patch.object(sys, "argv", argv), patch.object(Path, "open", checked_open), redirect_stdout(stdout):
            exit_code = namespace["main"]()
        final = json.loads(stdout.getvalue())
        assert final["status"] == expected, (path.name, name, final["status"], expected)
        assert exit_code == (0 if name == "captured_control" else 2), (path.name, name, exit_code)
        retained = {item.name: json.loads(item.read_text()) for item in output.iterdir()}
        assert retained.get("execution_receipt_v1.json", final)["status"] == final["status"]
        partial = retained.get("setup_partial_v1.json")
        if path.name == "run_control_v2.py.template" and partial is not None:
            assert partial["typed_snapshots"] == snapshots and partial["typed_copy_errors"] == []
        return {"status": final["status"], "exit_code": exit_code, "final": final,
                "retained_outputs": retained}


def main():
    before = {name for name in sys.modules if name == "semabi" or name.startswith("semabi.")}
    assert not before
    results = []
    for case in CASES:
        results.append({"case": case[0], "held_v1": exercise(HERE / "run_control_v1.py.template", case, case[-2]),
                        "candidate_v2": exercise(HERE / "run_control_v2.py.template", case, case[-1])})
    assert not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules)
    result = {"schema": "semabi.j1.receiver_view_preparation_status_checks.v2", "status": "PASS",
              "cases": results, "case_count_per_version": len(CASES), "native_execution": False,
              "scope": __doc__, "seams": ["main try body", "verify", "origins", "selected Path.open failures"],
              "not_tested": ["source/runtime freeze admission", "native fit", "native mappings", "A/B queries"]}
    with (HERE / "preparation_checks_v2.json").open("x") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "PASS", "cases_per_version": len(CASES), "native_execution": False}))


if __name__ == "__main__":
    main()
