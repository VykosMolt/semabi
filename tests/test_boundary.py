"""The compiler must never import evaluator-only code or touch hidden endpoints."""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "semabi"
FORBIDDEN = ("semabi.hidden", "semabi.env", "semabi.eval", "semabi.baselines")


def forbidden(name: str) -> bool:
    return any(name == f or name.startswith(f + ".") for f in FORBIDDEN)


def compiler_files():
    return list((ROOT / "compiler").glob("*.py")) + [ROOT / "relmodel.py", ROOT / "eval_free_canon.py"]


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
