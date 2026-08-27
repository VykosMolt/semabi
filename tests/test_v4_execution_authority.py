"""Load-bearing regressions for the V4 authoritative import authority.

Every attack here is run twice where that is meaningful: once under a plain isolated
interpreter, to show the attack really does change what executes, and once under
``scripts/v4_authority.py``, which must refuse it or authenticate the right file.  A test
that only checked the launcher would still pass if the mechanism were deleted.

The fixtures are throwaway Git repositories containing a tiny synthetic ``semabi``
package and a copy of the real launcher, so the attack surface exercised is the real
authority code with none of the real pipeline's cost.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import marshal
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LAUNCHER = REPO / "scripts" / "v4_authority.py"
DATA = REPO / "docs" / "data" / "v4"

# The retained attestations bind the bytes that ran.  The subject of the study has since moved
# and is expected to keep moving, so the attestations no longer match the working tree.  What
# may drift is enumerated here rather than inferred from a path prefix, because the prefix rule
# silently granted permission to every future file under it.  ``semabi/relmodel.py`` is on the
# list because the learned action model is what is under study: pre-state binding of the
# parameters an action does not supply is part of the exported operator semantics, not an
# analysis layer sitting above them.  Nothing in the authority or the manifest machinery is on
# the list, and the two assertions below keep it that way.
SUBJECT_UNDER_STUDY_PREFIXES = ("semabi/compiler/",)
SUBJECT_UNDER_STUDY_FILES = ("semabi/relmodel.py",)


def _load_launcher():
    spec = importlib.util.spec_from_file_location("_v4_authority_under_test", LAUNCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


authority_module = _load_launcher()


# --------------------------------------------------------------------------- fixtures

MARKER = "marker.txt"


def _marker(value: str) -> str:
    """Source that records, at the checkout root, which bytes actually executed."""

    return (
        "import pathlib as _p\n"
        "_r = next(a for a in _p.Path(__file__).resolve().parents if (a / '.git').exists())\n"
        f"_r.joinpath({MARKER!r}).write_text({value!r})\n"
    )

BASE_FILES = {
    "semabi/__init__.py": "ORIGIN = 'authentic'\n",
    "semabi/alpha.py": _marker("authentic") + "NAME = 'alpha'\n",
    "semabi/pkg/__init__.py": "from . import child\nNAME = 'pkg'\n",
    "semabi/pkg/child.py": "NAME = 'child'\n",
    "semabi/dyn.py": (
        "import importlib\n"
        "loaded = importlib.import_module('semabi.pkg.child')\n"
    ),
}

FORGED_SOURCE = _marker("forged") + "NAME = 'alpha'\n"


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
    )


def _make_repo(tmp_path: Path, extra: dict[str, str] | None = None) -> Path:
    root = tmp_path / "candidate"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(LAUNCHER, root / "scripts" / "v4_authority.py")
    for relative, text in {**BASE_FILES, **(extra or {})}.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(
        root,
        "-c", "user.email=regression@example.invalid",
        "-c", "user.name=regression",
        "commit", "-qm", "candidate",
    )
    return root


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _authority(root: Path, *args: str, flags: tuple[str, ...] = ("-I", "-S", "-B")):
    return subprocess.run(
        [sys.executable, *flags, str(root / "scripts" / "v4_authority.py"),
         "--no-site-packages", *args],
        capture_output=True,
        text=True,
        cwd=str(root.parent),
    )


def _plain_import(root: Path, module: str):
    """Import under a plain isolated interpreter, with no authority at all."""

    return subprocess.run(
        [sys.executable, "-I", "-S", "-c",
         f"import sys; sys.path.insert(0, {str(root)!r}); "
         f"import {module} as m; print(getattr(m, '__file__', None))"],
        capture_output=True,
        text=True,
        cwd=str(root.parent),
    )


def _refusal(result) -> dict:
    assert result.returncode == 3, (result.returncode, result.stdout[-2000:], result.stderr[-2000:])
    return json.loads(result.stderr)


def _attestation(result) -> dict:
    assert result.returncode == 0, (result.stdout[-4000:], result.stderr[-4000:])
    return json.loads(result.stdout)["attestation"]


def _paths(attestation: dict) -> set[str]:
    return {row["path"] for row in attestation["project_modules"]}


def _cache_path(source_path: Path) -> Path:
    """The cache path the *subprocess* would use.

    The test process may run under ``PYTHONPYCACHEPREFIX``; the authoritative and plain
    subprocesses run under ``-I``, which ignores it, so the prefix has to be neutralised
    here or the attack would be planted where nothing looks for it.
    """

    saved = sys.pycache_prefix
    sys.pycache_prefix = None
    try:
        return Path(importlib.util.cache_from_source(str(source_path)))
    finally:
        sys.pycache_prefix = saved


def _timestamp_pyc(source_path: Path, forged: str) -> bytes:
    """A cache CPython would load in place of ``source_path``."""

    info = source_path.stat()
    code = compile(forged, str(source_path), "exec", dont_inherit=True)
    return (
        importlib.util.MAGIC_NUMBER
        + (0).to_bytes(4, "little")
        + (int(info.st_mtime) & 0xFFFFFFFF).to_bytes(4, "little")
        + (info.st_size & 0xFFFFFFFF).to_bytes(4, "little")
        + marshal.dumps(code)
    )


def _hash_pyc(source_path: Path, forged: str, checked: bool) -> bytes:
    code = compile(forged, str(source_path), "exec", dont_inherit=True)
    flags = 0b1 | (0b10 if checked else 0)
    return (
        importlib.util.MAGIC_NUMBER
        + flags.to_bytes(4, "little")
        + importlib.util.source_hash(source_path.read_bytes())
        + marshal.dumps(code)
    )


# ------------------------------------------------------------------- resolution rules


def test_the_loader_table_is_cpythons_own_table_in_cpythons_own_order():
    from importlib import _bootstrap_external

    expected = [
        (loader, tuple(suffixes))
        for loader, suffixes in _bootstrap_external._get_supported_file_loaders()
    ]
    actual = [
        (loader, tuple(suffixes)) for loader, suffixes in authority_module.LOADER_DETAILS
    ]
    assert actual == expected


def test_package_shadow_executes_without_authority_and_is_refused_with_it(tmp_path):
    root = _make_repo(tmp_path)
    _write(root, "semabi/alpha/__init__.py", FORGED_SOURCE)

    plain = _plain_import(root, "semabi.alpha")
    assert plain.returncode == 0, plain.stderr
    assert plain.stdout.strip().endswith("semabi/alpha/__init__.py")
    assert (root / MARKER).read_text() == "forged"

    refusal = _refusal(_authority(root, "attest", "--module", "semabi.alpha"))
    assert refusal["code"] == "PROJECT_MODULE_NOT_IN_CANDIDATE_TREE"
    assert "semabi/alpha/__init__.py" in refusal["detail"]


def test_reverse_shadow_authenticates_the_package_cpython_actually_selects(tmp_path):
    root = _make_repo(tmp_path)
    _write(root, "semabi/pkg.py", FORGED_SOURCE)

    plain = _plain_import(root, "semabi.pkg")
    assert plain.stdout.strip().endswith("semabi/pkg/__init__.py")

    attestation = _attestation(_authority(root, "attest", "--module", "semabi.pkg"))
    assert "semabi/pkg/__init__.py" in _paths(attestation)
    assert "semabi/pkg.py" not in _paths(attestation)
    assert not (root / MARKER).exists()


def test_project_extension_module_is_refused(tmp_path):
    from importlib.machinery import EXTENSION_SUFFIXES

    root = _make_repo(tmp_path)
    _write(root, "semabi/alpha" + EXTENSION_SUFFIXES[0], "not a real shared object")
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.alpha"))
    assert refusal["code"] == "DISALLOWED_PROJECT_LOADER"
    assert "ExtensionFileLoader" in refusal["detail"]


def test_namespace_package_portion_is_refused(tmp_path):
    root = _make_repo(tmp_path)
    (root / "semabi" / "space").mkdir()
    _write(root, "semabi/space/leaf.py", "NAME = 'leaf'\n")
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.space"))
    assert refusal["code"] == "NAMESPACE_PACKAGE_PORTION"


def test_symlinked_project_origin_is_refused(tmp_path):
    root = _make_repo(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text(FORGED_SOURCE)
    os.symlink(outside, root / "semabi" / "linked.py")
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.linked"))
    assert refusal["code"] == "SYMLINKED_PROJECT_ORIGIN"


def test_tracked_symlink_to_python_source_is_refused_at_startup(tmp_path):
    root = _make_repo(tmp_path)
    os.symlink("alpha.py", root / "semabi" / "aliased.py")
    _git(root, "add", "-A")
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.alpha"))
    assert refusal["code"] == "TRACKED_PYTHON_PATH_IS_NOT_A_REGULAR_FILE"


# ------------------------------------------------------------------------- membership


def test_untracked_module_under_the_checkout_is_not_authorised(tmp_path):
    root = _make_repo(tmp_path)
    _write(root, "semabi/rogue.py", FORGED_SOURCE)
    plain = _plain_import(root, "semabi.rogue")
    assert plain.returncode == 0 and (root / MARKER).read_text() == "forged"

    refusal = _refusal(_authority(root, "attest", "--module", "semabi.rogue"))
    assert refusal["code"] == "PROJECT_MODULE_NOT_IN_CANDIDATE_TREE"


def test_modified_tracked_module_is_refused(tmp_path):
    root = _make_repo(tmp_path)
    _write(root, "semabi/alpha.py", FORGED_SOURCE)
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.alpha"))
    assert refusal["code"] == "PROJECT_MODULE_BYTES_DIFFER_FROM_CANDIDATE_TREE"


def test_staging_the_change_is_what_authenticates_it(tmp_path):
    """Membership is the checkout's content, not merely 'a file under the root'."""

    root = _make_repo(tmp_path)
    _write(root, "semabi/alpha.py", FORGED_SOURCE)
    _git(root, "add", "-A")
    attestation = _attestation(_authority(root, "attest", "--module", "semabi.alpha"))
    assert (root / MARKER).read_text() == "forged"
    digest = hashlib.sha256(FORGED_SOURCE.encode()).hexdigest()
    assert {row["sha256"] for row in attestation["project_modules"]
            if row["path"] == "semabi/alpha.py"} == {digest}


# --------------------------------------------------------------------------- bytecode


def test_malicious_timestamp_pycache_executes_without_authority_and_is_ignored_with_it(tmp_path):
    root = _make_repo(tmp_path)
    source = root / "semabi" / "alpha.py"
    cache = _cache_path(source)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(_timestamp_pyc(source, FORGED_SOURCE))

    plain = _plain_import(root, "semabi.alpha")
    assert plain.returncode == 0, plain.stderr
    assert (root / MARKER).read_text() == "forged", "the cache attack is not live"

    attestation = _attestation(_authority(root, "attest", "--module", "semabi.alpha"))
    assert (root / MARKER).read_text() == "authentic"
    assert "semabi/alpha.py" in _paths(attestation)
    assert attestation["policy"]["project_bytecode"] == (
        "NEVER_READ_SOURCE_IS_COMPILED_IN_MEMORY"
    )


@pytest.mark.parametrize("checked", [False, True])
def test_hash_based_pycache_is_ignored(tmp_path, checked):
    root = _make_repo(tmp_path)
    source = root / "semabi" / "alpha.py"
    cache = _cache_path(source)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(_hash_pyc(source, FORGED_SOURCE, checked))
    _attestation(_authority(root, "attest", "--module", "semabi.alpha"))
    assert (root / MARKER).read_text() == "authentic"


def test_stale_cache_plus_authentic_source_still_executes_the_source(tmp_path):
    root = _make_repo(tmp_path)
    source = root / "semabi" / "alpha.py"
    cache = _cache_path(source)
    cache.parent.mkdir(parents=True, exist_ok=True)
    data = bytearray(_timestamp_pyc(source, FORGED_SOURCE))
    data[8:12] = (0).to_bytes(4, "little")  # a header the interpreter would discard
    cache.write_bytes(bytes(data))
    _attestation(_authority(root, "attest", "--module", "semabi.alpha"))
    assert (root / MARKER).read_text() == "authentic"


def test_sourceless_project_bytecode_is_refused(tmp_path):
    root = _make_repo(tmp_path)
    forged = compile(FORGED_SOURCE, "semabi/only.py", "exec", dont_inherit=True)
    (root / "semabi" / "only.pyc").write_bytes(
        importlib.util.MAGIC_NUMBER
        + (0).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + marshal.dumps(forged)
    )
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.only"))
    assert refusal["code"] == "DISALLOWED_PROJECT_LOADER"
    assert "SourcelessFileLoader" in refusal["detail"]


# -------------------------------------------------------------- environment isolation


def test_a_site_directory_offering_the_project_name_is_refused(tmp_path):
    root = _make_repo(tmp_path)
    site = tmp_path / "site-packages"
    (site / "semabi").mkdir(parents=True)
    (site / "semabi" / "__init__.py").write_text("ORIGIN = 'installed'\n")
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(root / "scripts" / "v4_authority.py"),
         "--site-packages", str(site), "attest", "--module", "semabi"],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    refusal = _refusal(result)
    assert refusal["code"] == "SITE_PACKAGES_PROVIDES_PROJECT_NAME"


def test_an_editable_style_pth_pointing_at_another_checkout_contributes_nothing(tmp_path):
    """The exact shape of the editable installation in this project's own venv."""

    root = _make_repo(tmp_path)
    other = _make_repo(tmp_path / "elsewhere")
    _write(other, "semabi/alpha.py", FORGED_SOURCE)
    _git(other, "add", "-A")

    site = tmp_path / "site-packages"
    site.mkdir()
    (site / "__editable__.semabi-0.0.0.pth").write_text(
        "import __editable___semabi_finder; __editable___semabi_finder.install()\n"
    )
    (site / "__editable___semabi_finder.py").write_text(
        "import sys\n"
        "from importlib.machinery import PathFinder\n"
        f"MAPPING = {{'semabi': {str(other / 'semabi')!r}}}\n"
        "class _EditableFinder:\n"
        "    @classmethod\n"
        "    def find_spec(cls, fullname, path=None, target=None):\n"
        "        top = fullname.partition('.')[0]\n"
        "        if top in MAPPING:\n"
        "            return PathFinder.find_spec(fullname, path=[MAPPING[top] + '/..'])\n"
        "        return None\n"
        "def install():\n"
        "    sys.meta_path.insert(0, _EditableFinder)\n"
    )

    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(root / "scripts" / "v4_authority.py"),
         "--site-packages", str(site), "attest", "--module", "semabi.alpha"],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    attestation = _attestation(result)
    environment = json.loads(result.stdout)["environment"]
    declared = environment["declared_third_party"][0]
    assert declared["pth_files_mentioning_the_project"] == ["__editable__.semabi-0.0.0.pth"]
    assert declared["pth_processing"] == "DISABLED_BY_-S_NONE_READ_OR_EXECUTED"
    assert "_EditableFinder" not in environment["sys_meta_path"]
    assert environment["sys_meta_path"][0] == "ProjectImportAuthority"
    assert (root / MARKER).read_text() == "authentic"
    assert not (other / MARKER).exists()
    assert _paths(attestation) == {"semabi/__init__.py", "semabi/alpha.py"}


def test_non_isolated_startup_is_refused(tmp_path):
    root = _make_repo(tmp_path)
    for flags in (("-B",), ("-I", "-B"), ("-S", "-B"), ("-I", "-S")):
        refusal = _refusal(
            _authority(root, "attest", "--module", "semabi.alpha", flags=flags)
        )
        assert refusal["code"] == "NON_ISOLATED_STARTUP"


def test_a_modified_launcher_is_refused(tmp_path):
    root = _make_repo(tmp_path)
    launcher = root / "scripts" / "v4_authority.py"
    launcher.write_text(launcher.read_text() + "\n# tampered\n")
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.alpha"))
    assert refusal["code"] == "LAUNCHER_BYTES_DIFFER_FROM_CANDIDATE_TREE"


def test_a_new_top_level_project_package_cannot_appear_unclaimed(tmp_path):
    root = _make_repo(tmp_path, extra={"extra_pkg/__init__.py": "NAME = 'extra'\n"})
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.alpha"))
    assert refusal["code"] == "TOP_LEVEL_PROJECT_NAMES_DRIFTED"


# ---------------------------------------------------------------- runtime execution set


def test_relative_and_dynamic_imports_stay_inside_the_authority(tmp_path):
    root = _make_repo(tmp_path)
    attestation = _attestation(_authority(root, "attest", "--module", "semabi.dyn"))
    assert _paths(attestation) == {
        "semabi/__init__.py",
        "semabi/dyn.py",
        "semabi/pkg/__init__.py",
        "semabi/pkg/child.py",
    }
    assert all(row["executed_from_verified_memory"] for row in attestation["project_modules"])
    assert all(row["loader"] == "V4_VERIFIED_SOURCE_LOADER"
               for row in attestation["project_modules"])


def test_a_dynamic_import_of_an_untracked_module_is_refused(tmp_path):
    root = _make_repo(
        tmp_path,
        extra={"semabi/loader.py": "import importlib\n"
                                   "importlib.import_module('semabi.hidden_rogue')\n"},
    )
    _write(root, "semabi/hidden_rogue.py", FORGED_SOURCE)
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.loader"))
    assert refusal["code"] == "PROJECT_MODULE_NOT_IN_CANDIDATE_TREE"


def test_an_injected_meta_path_finder_cannot_supply_project_code(tmp_path):
    outside = tmp_path / "outside"
    (outside / "semabi").mkdir(parents=True)
    (outside / "semabi" / "victim.py").write_text("NAME = 'victim from outside'\n")
    root = _make_repo(
        tmp_path,
        extra={
            "semabi/hook.py": (
                "import sys\n"
                "from importlib.machinery import PathFinder\n"
                f"OUTSIDE = {str(outside)!r}\n"
                "class _Injected:\n"
                "    @classmethod\n"
                "    def find_spec(cls, fullname, path=None, target=None):\n"
                "        if fullname == 'semabi.victim':\n"
                "            return PathFinder.find_spec(fullname, path=[OUTSIDE + '/semabi'])\n"
                "        return None\n"
                "sys.meta_path.insert(0, _Injected)\n"
                "import semabi.victim\n"
            )
        },
    )
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.hook"))
    assert refusal["code"] in {"META_PATH_DISPLACED", "UNAUTHORISED_MODULE_ORIGIN"}


def test_the_exit_audit_rejects_unauthenticated_project_local_execution(tmp_path):
    """Even authenticated code cannot smuggle project-local bytes past the audit."""

    root = _make_repo(
        tmp_path,
        extra={
            "semabi/sneak.py": (
                "import importlib.util, pathlib, sys\n"
                "target = pathlib.Path(__file__).resolve().parent / 'ghost.py'\n"
                "spec = importlib.util.spec_from_file_location('ghost', target)\n"
                "module = importlib.util.module_from_spec(spec)\n"
                "sys.modules['ghost'] = module\n"
                "spec.loader.exec_module(module)\n"
            )
        },
    )
    _write(root, "semabi/ghost.py", FORGED_SOURCE)
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.sneak"))
    assert refusal["code"] == "UNAUTHORISED_MODULE_ORIGIN"
    assert "ghost" in refusal["detail"]


def test_the_exit_audit_rejects_a_namespace_portion_inside_the_checkout(tmp_path):
    """A module with no origin is classified by what it would search, not waved through."""

    root = _make_repo(
        tmp_path,
        extra={
            "semabi/ghost_namespace.py": (
                "import pathlib, sys, types\n"
                "root = next(a for a in pathlib.Path(__file__).resolve().parents\n"
                "            if (a / '.git').exists())\n"
                "module = types.ModuleType('ghostns')\n"
                "module.__path__ = [str(root / 'ghostdir')]\n"
                "sys.modules['ghostns'] = module\n"
            )
        },
    )
    (root / "ghostdir").mkdir()
    refusal = _refusal(_authority(root, "attest", "--module", "semabi.ghost_namespace"))
    assert refusal["code"] == "UNAUTHORISED_MODULE_ORIGIN"
    assert "namespace package inside the checkout" in refusal["detail"]


def test_the_attestation_is_byte_reproducible_across_checkouts(tmp_path):
    first = _make_repo(tmp_path)
    second = _make_repo(tmp_path / "second")
    one = _attestation(_authority(first, "attest", "--module", "semabi.dyn"))
    two = _attestation(_authority(second, "attest", "--module", "semabi.dyn"))
    assert one == two
    assert json.dumps(one).find(str(first)) == -1


# ------------------------------------------------------------- declared static closure


def test_execution_outside_the_declared_closure_is_refused(tmp_path):
    """``executed`` must be a subset of what the manifests hash."""

    from semabi.compiler.v4 import manifests

    closure = authority_module.closure_comparison

    class _Fake:
        records = {"semabi.x": {"path": "semabi/not_declared.py"}}

    with pytest.raises(authority_module.AuthorityViolation) as caught:
        closure(_Fake(), "replay")
    assert caught.value.code == "EXECUTED_OUTSIDE_DECLARED_CLOSURE"
    assert set(manifests.REPLAY_IMPLEMENTATION_FILES)


def test_static_discovery_refuses_the_names_it_cannot_describe(tmp_path):
    from semabi.compiler.v4 import manifests

    root = tmp_path / "tree"
    (root / "pkgmod").mkdir(parents=True)
    (root / "pkgmod" / "__init__.py").write_text("")
    (root / "pkgmod.py").write_text("")
    with pytest.raises(manifests.ManifestError, match="ambiguous"):
        manifests._module_path(root, "pkgmod")

    from importlib.machinery import EXTENSION_SUFFIXES

    (root / ("native" + EXTENSION_SUFFIXES[0])).write_text("")
    with pytest.raises(manifests.ManifestError, match="extension module"):
        manifests._module_path(root, "native")

    (root / "plain.py").write_text("")
    assert manifests._module_path(root, "plain") == root / "plain.py"
    (root / "onlypkg").mkdir()
    (root / "onlypkg" / "__init__.py").write_text("")
    assert manifests._module_path(root, "onlypkg") == root / "onlypkg" / "__init__.py"


# --------------------------------------------------------------------- process policy


def test_no_authoritative_closure_file_starts_a_subprocess():
    from semabi.compiler.v4 import manifests

    forbidden = {
        "subprocess", "multiprocessing", "runpy", "os.system", "os.popen",
        "os.execv", "os.execve", "os.execvp", "os.spawnv", "os.spawnl", "pty",
    }
    closure: set[str] = set()
    for entrypoints in (
        manifests.GENERATOR_ENTRYPOINTS,
        manifests.CHAIN_BUILDER_ENTRYPOINTS,
        manifests.REPLAY_ENTRYPOINTS,
    ):
        closure |= set(manifests.local_import_closure(None, entrypoints))
    for relative in sorted(closure):
        tree = ast.parse((REPO / relative).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, f"{relative}: {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                assert node.module.split(".")[0] not in forbidden, f"{relative}: {node.module}"
            elif isinstance(node, ast.Attribute):
                assert node.attr not in {"system", "popen", "execv", "execve", "spawnv"}, (
                    f"{relative}: os.{node.attr}"
                )


# ----------------------------------------------------------------- retained artifacts


def test_ordinary_execution_never_claims_the_authority():
    from semabi.compiler.v4 import manifests

    state = manifests.execution_authority()
    assert state["state"] == manifests.EXECUTION_AUTHORITY_ABSENT
    assert state["project_execution_sha256"] is None


def test_retained_reports_claim_the_authority_and_match_their_attestation():
    summary = json.loads((DATA / "frontier_summary.json").read_text())
    for app, row in summary["applications"].items():
        report = json.loads((REPO / row["report"]).read_text())
        state = report["authority"]["execution_authority"]
        assert state["state"] == "V4_IMPORT_AUTHORITY_ACTIVE", app
        assert state["attestation_schema"] == "semabi.v4.execution-attestation.v1"

        attestation_path = REPO / row["attestation"]
        assert hashlib.sha256(attestation_path.read_bytes()).hexdigest() == (
            row["attestation_sha256"]
        )
        attestation = json.loads(attestation_path.read_text())
        assert attestation["schema"] == "semabi.v4.execution-attestation.v1"
        assert attestation["project_execution_sha256"] == state["project_execution_sha256"]
        assert attestation["artifact"]["path"] == row["report"]
        assert attestation["artifact"]["sha256"] == row["report_sha256"]
        assert attestation["declared_static_closure"]["executed_outside_declared_closure"] == []
        assert attestation["rejections"] == []
        assert attestation["unauthorised_module_origins"] == []
        assert all(row["loader"] == "V4_VERIFIED_SOURCE_LOADER"
                   for row in attestation["project_modules"])
        # The attestation binds the bytes that ran.  Whether the working tree still holds
        # those bytes is a different question, and the answer is now no: the inducer is under
        # active development.  What must remain true is that the attestation is complete and
        # internally consistent, that the drift is confined to the subject under study, and
        # that the authority's own implementation has not moved -- an attestation produced by
        # a changed authority would be worth nothing.
        drifted = []
        for module in attestation["project_modules"]:
            assert not Path(module["path"]).is_absolute()
            if hashlib.sha256((REPO / module["path"]).read_bytes()).hexdigest() != (
                module["sha256"]
            ):
                drifted.append(module["path"])
        assert all(path.startswith(SUBJECT_UNDER_STUDY_PREFIXES)
                   or path in SUBJECT_UNDER_STUDY_FILES for path in drifted), drifted
        assert not any(path.startswith("semabi/compiler/v4/manifests") for path in drifted)
        assert not any("authority" in path for path in drifted)


def test_every_retained_attestation_binds_an_existing_artifact():
    directory = DATA / "attestations"
    retained = sorted(directory.glob("*.execution.json"))
    assert len(retained) >= 3
    for path in retained:
        attestation = json.loads(path.read_text())
        artifact = REPO / attestation["artifact"]["path"]
        assert artifact.is_file(), attestation["artifact"]["path"]
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == (
            attestation["artifact"]["sha256"]
        )
        assert attestation["authority"] == "V4_IMPORT_AUTHORITY_ACTIVE"
        assert attestation["entrypoint"]["kind"] in {
            "replay", "freeze-source", "freeze-chain"
        }
