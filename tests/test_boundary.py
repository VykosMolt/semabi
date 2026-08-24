"""The compiler must never import evaluator-only code or touch hidden endpoints."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "semabi"
FORBIDDEN = ("semabi.hidden", "semabi.env", "semabi.eval", "semabi.baselines")


def forbidden(name: str) -> bool:
    return any(name == f or name.startswith(f + ".") for f in FORBIDDEN)


def compiler_files():
    # The V2 compiler lives in nested packages.  A shallow glob left exactly the new
    # decision/refinement boundary outside this gate.  The compiler-side runners drive the
    # browser and must be inside it too: V4's probe runner executes experiments against a
    # live application and would be the natural place for hidden state to leak in.
    runners = [
        ROOT / "run_v2_refine.py",
        ROOT / "run_v2_validate.py",
        ROOT / "run_v4_probe.py",
        ROOT / "run_v4_transfer.py",
    ]
    return (list((ROOT / "compiler").rglob("*.py")) + [ROOT / "relmodel.py", ROOT / "eval_free_canon.py"]
            + [r for r in runners if r.exists()])


def test_compiler_imports_are_clean():
    for f in compiler_files():
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            for n in names:
                assert not forbidden(n), f"{f.name} imports {n}"


def test_compiler_never_references_evaluator_endpoint():
    for f in compiler_files():
        text = f.read_text()
        assert "_evaluator" not in text, f.name
        assert "hidden.jsonl" not in text, f.name
        assert not re.search(r"\bapi/state\b", text), f.name


def test_relmodel_has_no_domain_content():
    text = (ROOT / "relmodel.py").read_text()
    for word in ("Project", "Task", "belongs_to", "kanban"):
        assert word not in text


def test_compiler_never_reads_oracle_annotations():
    """The oracle ladder's ground truth (data-eid annotations, oracle.jsonl) is evaluator-only."""
    for f in compiler_files():
        text = f.read_text()
        assert "data-eid" not in text and "data-erefs" not in text and "data-oid" not in text, f.name
        assert "oracle.jsonl" not in text, f.name
        assert "hidden_domain.json" not in text, f.name


def test_v4_closure_is_local_and_includes_function_local_compiler_modules():
    from semabi.compiler.v4 import manifests

    for closure in (manifests.GENERATOR_IMPLEMENTATION_FILES,
                    manifests.REPLAY_IMPLEMENTATION_FILES):
        assert "semabi/compiler/grounder.py" in closure
        assert "semabi/compiler/mentions.py" in closure
        assert "semabi/__init__.py" in closure
        assert "semabi/compiler/__init__.py" in closure
        assert "semabi/compiler/v2/__init__.py" in closure
        assert "semabi/compiler/v4/__init__.py" in closure
        assert all(not name.startswith(("semabi/hidden", "semabi/env", "semabi/eval/"))
                   for name in closure)
