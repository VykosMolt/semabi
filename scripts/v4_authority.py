#!/usr/bin/env python3
"""V4 authoritative launcher and project-import authority.

This file is the root of trust for authenticated V4 execution.  It is stdlib-only, is
never imported by SemABI, and must be started by an isolated interpreter::

    .venv/bin/python -I -S -B scripts/v4_authority.py <command> ...

What it establishes, in order:

1.  an explicitly controlled import environment.  ``-I`` drops the script directory,
    the user site directory and every ``PYTHON*`` variable; ``-S`` stops ``site`` from
    running at all, so no ``.pth`` file is read and no ``.pth`` import line executes.
    An editable SemABI installation is implemented by exactly such a ``.pth`` line, so
    it cannot contribute anything here.  This is checked, not assumed.
2.  the exact candidate checkout, derived from this file's own resolved location.
3.  the authenticated project source bytes.  Every tracked ``*.py`` path in the Git
    index is read **from Git's object store**, not from the working tree, so the
    authenticated content is the content the candidate commit will contain.  Bytes are
    compared directly; the Git object id is only an index key, never a security hash.
4.  a project-import authority installed at ``sys.meta_path[0]``.  It never predicts
    Python's import resolution: it hands the search to CPython's own ``FileFinder``
    (with CPython's own loader table, so package-before-module and
    extension-before-source ordering are CPython's, not ours), cross-checks the
    selection against ``PathFinder``, authenticates the origin CPython actually
    selected, reads its bytes once, compares them with the authenticated content, and
    executes those in-memory bytes.  The path is never reopened, and project bytecode
    is never consulted.
5.  an exit audit proving every module that actually executed was authenticated project
    code, interpreter stdlib, or a declared third-party directory.
6.  a byte-reproducible execution attestation, plus a non-reproducible environment
    record (absolute paths, commit, interpreter) printed to stdout.

It is not a sandbox.  ``docs/v4_execution_authority.md`` states the declared threat
model and the explicit non-goals.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import sys
import types

ATTESTATION_SCHEMA = "semabi.v4.execution-attestation.v1"
ENVIRONMENT_SCHEMA = "semabi.v4.execution-environment.v1"
AUTHORITY_MODULE = "_semabi_v4_authority"
AUTHORITY_ACTIVE = "V4_IMPORT_AUTHORITY_ACTIVE"
LOADER_KIND = "V4_VERIFIED_SOURCE_LOADER"
RESOLVER_KIND = "CPYTHON_FILEFINDER_CROSSCHECKED_WITH_PATHFINDER"
MEMBERSHIP_SOURCE = "GIT_INDEX_BLOB_CONTENT_OF_THE_CANDIDATE_CHECKOUT"

# The only importable top-level project name.  Verified against the tracked tree at
# startup so a new top-level package cannot silently escape the authority.
PROJECT_TOP_LEVEL = ("semabi",)

# CPython's own loader table, in CPython's own order.  This is exactly what
# ``importlib._bootstrap_external._get_supported_file_loaders`` returns; it is spelled
# out here only because that function is private.  A test pins the equality.
LOADER_DETAILS = (
    (importlib.machinery.ExtensionFileLoader, importlib.machinery.EXTENSION_SUFFIXES),
    (importlib.machinery.SourceFileLoader, importlib.machinery.SOURCE_SUFFIXES),
    (importlib.machinery.SourcelessFileLoader, importlib.machinery.BYTECODE_SUFFIXES),
)

# Authoritative entrypoints.  ``semabi/run_v4_transfer.py`` is imported as a module;
# the two freeze scripts are executed from authenticated bytes under a private name.
ENTRYPOINTS = {
    "freeze-source": "scripts/v4_freeze_source_candidates.py",
    "freeze-chain": "scripts/v4_freeze_chain_manifest.py",
    "replay": "semabi/run_v4_transfer.py",
}


class AuthorityViolation(BaseException):
    """A refusal to execute.  Deliberately not an ``Exception``.

    Import failures are routinely caught by ``except ImportError`` or ``except
    Exception``; an authority refusal must never be swallowed by ordinary code, so it
    derives from ``BaseException`` and terminates the run.
    """

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _fail(code: str, detail: str) -> "AuthorityViolation":
    return AuthorityViolation(code, detail)


# --------------------------------------------------------------------------- startup


def require_isolated_startup() -> dict[str, bool]:
    """Refuse to run unless the interpreter was started with -I -S -B."""

    flags = {
        "isolated": bool(sys.flags.isolated),
        "no_site": bool(sys.flags.no_site),
        "dont_write_bytecode": bool(sys.flags.dont_write_bytecode),
        "ignore_environment": bool(sys.flags.ignore_environment),
        "no_user_site": bool(sys.flags.no_user_site),
        "safe_path": bool(getattr(sys.flags, "safe_path", 0)),
    }
    missing = sorted(name for name, value in flags.items() if not value)
    if missing:
        raise _fail(
            "NON_ISOLATED_STARTUP",
            "authoritative execution requires "
            f"`{os.path.basename(sys.executable)} -I -S -B {os.path.basename(__file__)}`; "
            f"missing interpreter state: {', '.join(missing)}",
        )
    sys.dont_write_bytecode = True
    return flags


def repo_root() -> str:
    """The exact candidate checkout, taken from this file, not from the cwd."""

    launcher = os.path.realpath(__file__)
    root = os.path.dirname(os.path.dirname(launcher))
    if not os.path.isdir(os.path.join(root, ".git")) and not os.path.isfile(
        os.path.join(root, ".git")
    ):
        raise _fail("CANDIDATE_ROOT_IS_NOT_A_CHECKOUT", root)
    return root


# ------------------------------------------------------------------------------- git


def _git(root: str, *args: str) -> bytes:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    proc = subprocess.run(
        ["git", "--no-optional-locks", "-C", root, *args],
        capture_output=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise _fail(
            "GIT_QUERY_FAILED",
            f"git {' '.join(args)} -> {proc.returncode}: "
            f"{proc.stderr.decode('utf-8', 'replace').strip()}",
        )
    return proc.stdout


def _index_entries(root: str) -> dict[str, tuple[str, str]]:
    """Return ``{relative path: (mode, blob id)}`` for every staged file."""

    out = _git(root, "ls-files", "--stage", "-z")
    entries: dict[str, tuple[str, str]] = {}
    for record in out.split(b"\x00"):
        if not record:
            continue
        meta, sep, raw_path = record.partition(b"\t")
        if not sep:
            raise _fail("GIT_INDEX_UNPARSEABLE", repr(record[:80]))
        fields = meta.split(b" ")
        if len(fields) != 3:
            raise _fail("GIT_INDEX_UNPARSEABLE", repr(meta[:80]))
        mode, blob, stage = fields
        if stage != b"0":
            raise _fail("GIT_INDEX_UNMERGED", raw_path.decode("utf-8", "replace"))
        entries[raw_path.decode("utf-8")] = (mode.decode(), blob.decode())
    if not entries:
        raise _fail("GIT_INDEX_EMPTY", root)
    return entries


def _cat_blobs(root: str, blob_ids: list[str]) -> dict[str, bytes]:
    """Read the exact committed bytes of each blob from the object store."""

    if not blob_ids:
        return {}
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    proc = subprocess.run(
        ["git", "--no-optional-locks", "-C", root, "cat-file", "--batch"],
        input="\n".join(blob_ids).encode() + b"\n",
        capture_output=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise _fail("GIT_CAT_FILE_FAILED", proc.stderr.decode("utf-8", "replace").strip())
    data = proc.stdout
    out: dict[str, bytes] = {}
    offset = 0
    for _ in blob_ids:
        newline = data.find(b"\n", offset)
        if newline < 0:
            raise _fail("GIT_CAT_FILE_TRUNCATED", "missing object header")
        header = data[offset:newline].split(b" ")
        if len(header) != 3 or header[1] != b"blob":
            raise _fail("GIT_CAT_FILE_TRUNCATED", data[offset:newline].decode("utf-8", "replace"))
        oid, size = header[0].decode(), int(header[2])
        start = newline + 1
        out[oid] = data[start:start + size]
        offset = start + size + 1
    return out


def authenticated_sources(root: str) -> tuple[dict[str, bytes], dict[str, tuple[str, str]]]:
    """Authenticated content for every tracked Python file of the candidate checkout."""

    entries = _index_entries(root)
    wanted: dict[str, str] = {}
    for relative, (mode, blob) in entries.items():
        if not relative.endswith(".py"):
            continue
        if mode not in ("100644", "100755"):
            # 120000 is a symlink and 160000 a submodule; neither is authenticable
            # Python source, and neither may become executable project code.
            raise _fail("TRACKED_PYTHON_PATH_IS_NOT_A_REGULAR_FILE", f"{relative} mode {mode}")
        wanted[relative] = blob
    blobs = _cat_blobs(root, sorted(set(wanted.values())))
    sources = {relative: blobs[blob] for relative, blob in wanted.items()}
    return sources, entries


def derived_top_level(sources: dict[str, bytes]) -> tuple[str, ...]:
    """Importable top-level project names implied by the tracked tree."""

    names: set[str] = set()
    for relative in sources:
        parts = relative.split("/")
        if len(parts) == 1:
            names.add(parts[0][:-3])
        elif len(parts) == 2 and parts[1] == "__init__.py":
            names.add(parts[0])
    return tuple(sorted(names))


# ------------------------------------------------------------------------------ path


def _real(path: str) -> str:
    return os.path.realpath(path)


def _under(path: str, directory: str) -> bool:
    directory = directory.rstrip(os.sep)
    return path == directory or path.startswith(directory + os.sep)


def default_site_packages() -> str:
    """The declared third-party directory of the interpreter's own environment.

    ``sys.executable`` is used unresolved on purpose: a virtual environment's
    interpreter is a symlink to the base interpreter, so resolving it would name the
    base installation's directories instead of the environment's.
    """

    base = os.path.dirname(os.path.dirname(sys.executable))
    if not os.path.isfile(os.path.join(base, "pyvenv.cfg")):
        raise _fail(
            "NOT_A_VIRTUAL_ENVIRONMENT",
            f"{base} has no pyvenv.cfg; pass --site-packages explicitly",
        )
    candidate = os.path.join(
        base, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"
    )
    if not os.path.isdir(candidate):
        raise _fail(
            "SITE_PACKAGES_NOT_FOUND",
            f"no site-packages under {base}; pass --site-packages explicitly",
        )
    return candidate


def prepare_site_packages(
    root: str, entries: dict[str, tuple[str, str]], explicit: list[str] | None, enabled: bool
) -> tuple[list[str], list[dict[str, object]]]:
    """Add declared third-party directories as ordinary paths, never as site dirs.

    ``site`` never runs here, so no ``.pth`` file in these directories is read or
    executed.  Any ``.pth`` that mentions the candidate checkout is recorded as
    evidence that it was present and inert -- that is how an editable installation of
    this very project is shown to contribute nothing.

    A declared directory may sit inside the candidate checkout (a ``.venv`` beside the
    sources is ordinary), but only if it holds no tracked path at all, so it can never
    overlap authenticated project space.  Its *contents* are trusted, not authenticated:
    see the declared trusted computing base in docs/v4_execution_authority.md.
    """

    if not enabled:
        return [], []
    chosen = [_real(p) for p in (explicit or [default_site_packages()])]
    records: list[dict[str, object]] = []
    for directory in chosen:
        if not os.path.isdir(directory):
            raise _fail("SITE_PACKAGES_NOT_A_DIRECTORY", directory)
        inside = _under(directory, root)
        if inside:
            prefix = os.path.relpath(directory, root).replace(os.sep, "/") + "/"
            tracked = sorted(rel for rel in entries if rel.startswith(prefix))
            if tracked:
                raise _fail(
                    "SITE_PACKAGES_OVERLAPS_AUTHENTICATED_PROJECT_SPACE",
                    f"{directory} contains {len(tracked)} tracked paths, first {tracked[0]}",
                )
        for name in PROJECT_TOP_LEVEL:
            collisions = [
                entry
                for entry in os.listdir(directory)
                if entry == name or entry.startswith(name + ".")
            ]
            packages = [
                entry
                for entry in collisions
                if entry == name
                or any(entry == name + suffix for _, suffixes in LOADER_DETAILS for suffix in suffixes)
            ]
            if packages:
                raise _fail(
                    "SITE_PACKAGES_PROVIDES_PROJECT_NAME",
                    f"{directory} contains {sorted(packages)} for project name {name!r}",
                )
        pth = sorted(entry for entry in os.listdir(directory) if entry.endswith(".pth"))
        mentions_root = []
        for entry in pth:
            try:
                text = open(os.path.join(directory, entry), "rb").read().decode("utf-8", "replace")
            except OSError:
                text = ""
            if root in text or any(name in text for name in PROJECT_TOP_LEVEL):
                mentions_root.append(entry)
        records.append(
            {
                "path": directory,
                "inside_candidate_root": inside,
                "tracked_paths_inside": 0,
                "provides_project_top_level_name": False,
                "pth_files_present": pth,
                "pth_files_mentioning_the_project": mentions_root,
                "pth_processing": "DISABLED_BY_-S_NONE_READ_OR_EXECUTED",
                "contents": "TRUSTED_NOT_AUTHENTICATED_DECLARED_THIRD_PARTY",
            }
        )
    for directory in chosen:
        if directory not in sys.path:
            sys.path.append(directory)
    return chosen, records


# ---------------------------------------------------------------------------- loader


class VerifiedSourceLoader:
    """Execute exactly the authenticated bytes; never reopen or read bytecode."""

    def __init__(self, fullname: str, origin: str, source: bytes, is_package: bool) -> None:
        self.name = fullname
        self.origin = origin
        self._source = source
        self._is_package = is_package

    def create_module(self, spec):  # noqa: D401 - default module creation semantics
        return None

    def exec_module(self, module) -> None:
        exec(self.get_code(self.name), module.__dict__)

    def get_code(self, fullname: str):
        if fullname != self.name:
            raise ImportError(f"loader for {self.name} asked for {fullname}")
        return compile(self._source, self.origin, "exec", dont_inherit=True)

    def get_source(self, fullname: str) -> str:
        if fullname != self.name:
            raise ImportError(f"loader for {self.name} asked for {fullname}")
        return importlib.util.decode_source(self._source)

    def get_filename(self, fullname: str) -> str:
        return self.origin

    def is_package(self, fullname: str) -> bool:
        return self._is_package

    def get_data(self, path: str) -> bytes:
        raise OSError(
            "the V4 verified loader never reads from a path; "
            f"refused a read of {path} for {self.name}"
        )

    def __repr__(self) -> str:
        return f"<{LOADER_KIND} {self.name} {self.origin}>"


# --------------------------------------------------------------------------- authority


class ProjectImportAuthority:
    """Let CPython resolve project modules, then authenticate what it selected."""

    def __init__(
        self,
        root: str,
        sources: dict[str, bytes],
        interpreter_dirs: list[str],
        third_party_dirs: list[str],
    ) -> None:
        self.root = root
        self.sources = sources
        self.digests = {rel: hashlib.sha256(data).hexdigest() for rel, data in sources.items()}
        self.interpreter_dirs = [_real(d) for d in interpreter_dirs]
        self.third_party_dirs = [_real(d) for d in third_party_dirs]
        self.allowed_dirs = self.interpreter_dirs + self.third_party_dirs
        self.records: dict[str, dict[str, object]] = {}
        self.rejections: list[dict[str, str]] = []
        self.third_party: set[str] = set()
        self._finders: dict[str, importlib.machinery.FileFinder] = {}
        self._installed = False

    # -- installation -------------------------------------------------------

    def install(self) -> None:
        preloaded = sorted(name for name in sys.modules if self.claims(name))
        if preloaded:
            raise _fail("PRELOADED_PROJECT_MODULE", ", ".join(preloaded))
        for entry in sys.path:
            if not isinstance(entry, str) or not entry:
                continue
            real = _real(entry)
            if _under(real, self.root) and not any(
                _under(real, directory) for directory in self.allowed_dirs
            ):
                raise _fail("PROJECT_PATH_ON_SYS_PATH", entry)
        sys.meta_path.insert(0, self)
        self._installed = True

    def claims(self, fullname: str) -> bool:
        return any(
            fullname == name or fullname.startswith(name + ".") for name in PROJECT_TOP_LEVEL
        )

    # -- resolution ---------------------------------------------------------

    def _file_finder(self, directory: str) -> importlib.machinery.FileFinder:
        finder = self._finders.get(directory)
        if finder is None:
            finder = importlib.machinery.FileFinder(directory, *LOADER_DETAILS)
            self._finders[directory] = finder
        return finder

    def _search_locations(self, fullname: str, path) -> list[str]:
        if fullname in PROJECT_TOP_LEVEL:
            return [self.root]
        if path is None:
            raise _fail("PROJECT_SUBMODULE_WITHOUT_PACKAGE_PATH", fullname)
        locations: list[str] = []
        for entry in list(path):
            if not isinstance(entry, str) or not entry:
                raise _fail("SEARCH_PATH_ENTRY_IS_NOT_A_PATH", f"{fullname}: {entry!r}")
            real = _real(entry)
            if real != entry or not _under(real, self.root):
                raise _fail("SEARCH_PATH_OUTSIDE_CANDIDATE_ROOT", f"{fullname}: {entry}")
            locations.append(entry)
        if not locations:
            raise _fail("PROJECT_SUBMODULE_WITHOUT_PACKAGE_PATH", fullname)
        return locations

    def _resolve(self, fullname: str, locations: list[str]):
        selected = None
        for directory in locations:
            spec = self._file_finder(directory).find_spec(fullname)
            if spec is not None:
                selected = spec
                break
        cross = importlib.machinery.PathFinder.find_spec(fullname, list(locations))
        mine = (getattr(selected, "origin", None), type(getattr(selected, "loader", None)).__name__)
        theirs = (getattr(cross, "origin", None), type(getattr(cross, "loader", None)).__name__)
        if mine != theirs:
            raise _fail(
                "RESOLUTION_DISAGREEMENT",
                f"{fullname}: FileFinder {mine} != PathFinder {theirs}",
            )
        return selected

    def find_spec(self, fullname: str, path=None, target=None):
        if not self.claims(fullname):
            return None
        if not self._installed or not sys.meta_path or sys.meta_path[0] is not self:
            raise _fail("META_PATH_DISPLACED", f"{fullname}: authority is not sys.meta_path[0]")
        spec = self._resolve(fullname, self._search_locations(fullname, path))
        if spec is None:
            return None
        return self._authenticate(fullname, spec)

    # -- authentication -----------------------------------------------------

    def _reject(self, code: str, fullname: str, detail: str):
        self.rejections.append({"code": code, "module": fullname, "detail": detail})
        raise _fail(code, f"{fullname}: {detail}")

    def _authenticate(self, fullname: str, spec):
        loader = getattr(spec, "loader", None)
        if loader is None:
            self._reject(
                "NAMESPACE_PACKAGE_PORTION",
                fullname,
                f"CPython selected a namespace portion at "
                f"{list(getattr(spec, 'submodule_search_locations', []) or [])}; "
                "SemABI declares no namespace packages",
            )
        if type(loader) is not importlib.machinery.SourceFileLoader:
            self._reject(
                "DISALLOWED_PROJECT_LOADER",
                fullname,
                f"CPython selected {type(loader).__name__} for {spec.origin!r}; "
                "only source modules and source packages are authenticable",
            )
        origin = spec.origin
        if not isinstance(origin, str) or not origin:
            self._reject("PROJECT_ORIGIN_IS_NOT_A_PATH", fullname, repr(origin))
        if _real(origin) != origin:
            self._reject(
                "SYMLINKED_PROJECT_ORIGIN", fullname, f"{origin} resolves to {_real(origin)}"
            )
        if not _under(origin, self.root):
            self._reject("PROJECT_ORIGIN_OUTSIDE_CANDIDATE_ROOT", fullname, origin)
        relative = os.path.relpath(origin, self.root).replace(os.sep, "/")
        if not relative.endswith(".py"):
            self._reject("PROJECT_ORIGIN_IS_NOT_PYTHON_SOURCE", fullname, relative)
        expected = self.sources.get(relative)
        if expected is None:
            self._reject(
                "PROJECT_MODULE_NOT_IN_CANDIDATE_TREE",
                fullname,
                f"{relative} is not a tracked Python file of the candidate checkout",
            )
        data = _read_once(origin, fullname)
        if data != expected:
            self._reject(
                "PROJECT_MODULE_BYTES_DIFFER_FROM_CANDIDATE_TREE",
                fullname,
                f"{relative} on disk differs from the authenticated candidate content",
            )
        is_package = os.path.basename(origin) == "__init__.py"
        verified = VerifiedSourceLoader(fullname, origin, data, is_package)
        authentic = importlib.machinery.ModuleSpec(
            fullname, verified, origin=origin, is_package=is_package
        )
        authentic.has_location = True
        if is_package:
            authentic.submodule_search_locations = [os.path.dirname(origin)]
        self._record(fullname, relative, origin, is_package)
        return authentic

    def _record(self, fullname: str, relative: str, origin: str, is_package: bool) -> None:
        self.records[fullname] = {
            "module": fullname,
            "path": relative,
            "sha256": self.digests[relative],
            "size": len(self.sources[relative]),
            "is_package": is_package,
            "package_search_locations": (
                [os.path.dirname(relative)] if is_package else []
            ),
            "resolved_by": RESOLVER_KIND,
            "loader": LOADER_KIND,
            "executed_from_verified_memory": True,
        }

    # -- entry files --------------------------------------------------------

    def load_entry_file(self, relative: str, module_name: str):
        """Execute an authoritative entry script from authenticated bytes."""

        expected = self.sources.get(relative)
        if expected is None:
            raise _fail("ENTRYPOINT_NOT_IN_CANDIDATE_TREE", relative)
        origin = os.path.join(self.root, *relative.split("/"))
        if _real(origin) != origin:
            raise _fail("SYMLINKED_PROJECT_ORIGIN", origin)
        data = _read_once(origin, module_name)
        if data != expected:
            raise _fail("PROJECT_MODULE_BYTES_DIFFER_FROM_CANDIDATE_TREE", relative)
        loader = VerifiedSourceLoader(module_name, origin, data, False)
        spec = importlib.machinery.ModuleSpec(module_name, loader, origin=origin)
        spec.has_location = True
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        self._record(module_name, relative, origin, False)
        loader.exec_module(module)
        return module

    # -- audit --------------------------------------------------------------

    def project_execution_sha256(self) -> str:
        payload = json.dumps(
            [self.records[name] for name in sorted(self.records)],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def audit(self) -> dict[str, object]:
        """Prove every module that actually executed had an authorised origin."""

        if not sys.meta_path or sys.meta_path[0] is not self:
            raise _fail("META_PATH_DISPLACED", "authority is no longer sys.meta_path[0]")
        unclassified: list[str] = []
        counts = {
            "builtin_or_frozen": 0,
            "interpreter_stdlib": 0,
            "declared_third_party": 0,
            "project": 0,
        }
        for name in sorted(sys.modules):
            module = sys.modules.get(name)
            if module is None:
                continue
            if name == "__main__":
                continue
            if name in self.records:
                loader = getattr(module, "__loader__", None)
                if not isinstance(loader, VerifiedSourceLoader):
                    unclassified.append(
                        f"{name} was authenticated but is loaded by {type(loader).__name__}"
                    )
                counts["project"] += 1
                continue
            if self.claims(name):
                unclassified.append(f"{name} is a project name that bypassed the authority")
                continue
            spec = getattr(module, "__spec__", None)
            origin = getattr(spec, "origin", None) or getattr(module, "__file__", None)
            if origin in (None, "built-in", "frozen") or not isinstance(origin, str):
                # A namespace package has no origin at all, so classify it by the
                # directories it would search rather than letting it pass as builtin.
                for entry in list(getattr(module, "__path__", None) or []):
                    if not isinstance(entry, str):
                        continue
                    location = _real(entry)
                    if any(_under(location, d) for d in self.allowed_dirs):
                        continue
                    if _under(location, self.root):
                        unclassified.append(
                            f"{name} is a namespace package inside the checkout: {entry}"
                        )
                    else:
                        unclassified.append(
                            f"{name} is a namespace package with an undeclared portion: {entry}"
                        )
                counts["builtin_or_frozen"] += 1
                continue
            real = _real(origin)
            if any(_under(real, directory) for directory in self.third_party_dirs):
                counts["declared_third_party"] += 1
                self.third_party.add(name.split(".")[0])
                continue
            if any(_under(real, directory) for directory in self.interpreter_dirs):
                counts["interpreter_stdlib"] += 1
                continue
            if _under(real, self.root):
                unclassified.append(f"{name} executed unauthenticated project-local code: {origin}")
                continue
            unclassified.append(f"{name} has an undeclared origin: {origin}")
        if unclassified:
            raise _fail("UNAUTHORISED_MODULE_ORIGIN", "; ".join(sorted(unclassified)))
        return counts


def _read_once(origin: str, fullname: str) -> bytes:
    """Open the selected origin exactly once and keep its bytes.

    ``O_NOFOLLOW`` refuses a symlinked final component, and the mode is taken from the
    open descriptor rather than from a second ``stat`` of the name.
    """

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        handle = os.open(origin, flags)
    except OSError as exc:
        raise _fail("CANNOT_READ_PROJECT_ORIGIN", f"{fullname}: {origin}: {exc}") from exc
    try:
        info = os.fstat(handle)
        if not stat.S_ISREG(info.st_mode):
            raise _fail("PROJECT_ORIGIN_IS_NOT_A_REGULAR_FILE", f"{fullname}: {origin}")
        chunks: list[bytes] = []
        while True:
            block = os.read(handle, 1 << 20)
            if not block:
                break
            chunks.append(block)
    finally:
        os.close(handle)
    return b"".join(chunks)


# ------------------------------------------------------------------- static closure


def _declared_closure(entry_kind: str) -> tuple[str, ...]:
    from semabi.compiler.v4 import manifests

    mapping = {
        "freeze-source": manifests.GENERATOR_ENTRYPOINTS,
        "freeze-chain": manifests.CHAIN_BUILDER_ENTRYPOINTS,
        "replay": manifests.REPLAY_ENTRYPOINTS,
    }
    return manifests.local_import_closure(None, mapping[entry_kind])


def closure_comparison(authority: ProjectImportAuthority, entry_kind: str | None) -> dict:
    """Compare the declared static closure with the set that actually executed.

    The static closure is a *declaration* discovered by scanning literal imports.  It
    is what the manifests hash, so nothing outside it may execute.  It is not a proof
    of completeness, and it may legitimately over-approximate: a declared file that no
    run imports is recorded, not rejected.
    """

    executed = sorted({str(row["path"]) for row in authority.records.values()})
    if entry_kind is None:
        return {
            "entrypoint_kind": None,
            "declared": None,
            "executed": executed,
            "executed_outside_declared_closure": None,
            "declared_but_not_executed": None,
        }
    declared = sorted(_declared_closure(entry_kind))
    outside = sorted(set(executed) - set(declared))
    if outside:
        raise _fail("EXECUTED_OUTSIDE_DECLARED_CLOSURE", ", ".join(outside))
    return {
        "entrypoint_kind": entry_kind,
        "declared": declared,
        "executed": executed,
        "executed_outside_declared_closure": [],
        "declared_but_not_executed": sorted(set(declared) - set(executed)),
    }


# ---------------------------------------------------------------------- attestation


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build_attestation(
    authority: ProjectImportAuthority,
    entry_kind: str | None,
    artifact: str | None,
    root: str,
    closure: dict,
) -> dict:
    record = {
        "schema": ATTESTATION_SCHEMA,
        "authority": AUTHORITY_ACTIVE,
        "policy": {
            "resolution": RESOLVER_KIND,
            "membership": MEMBERSHIP_SOURCE,
            "loader": LOADER_KIND,
            "allowed_project_loaders": ["SourceFileLoader"],
            "project_namespace_packages": "REJECTED",
            "project_extension_modules": "REJECTED",
            "project_bytecode": "NEVER_READ_SOURCE_IS_COMPILED_IN_MEMORY",
            "project_symlinks": "REJECTED",
            "untracked_project_modules": "REJECTED",
            "site_pth_processing": "DISABLED",
            "project_directories_on_sys_path": "NONE",
        },
        "runtime": {
            "implementation": sys.implementation.name,
            "version": "%d.%d.%d" % sys.version_info[:3],
        },
        "entrypoint": {
            "kind": entry_kind,
            "file": ENTRYPOINTS.get(entry_kind) if entry_kind else None,
        },
        "project_modules": [authority.records[name] for name in sorted(authority.records)],
        "project_execution_sha256": authority.project_execution_sha256(),
        "declared_static_closure": closure,
        "third_party_top_level_executed": sorted(authority.third_party),
        "rejections": authority.rejections,
        "unauthorised_module_origins": [],
    }
    if artifact is not None:
        relative = os.path.relpath(_real(artifact), root).replace(os.sep, "/")
        record["artifact"] = {"path": relative, "sha256": _sha256_file(artifact)}
    return record


def build_environment(
    root: str,
    flags: dict,
    entries: dict[str, tuple[str, str]],
    site_records: list,
    initial_path: list[str],
    counts: dict,
) -> dict:
    head = _git(root, "rev-parse", "--verify", "HEAD").decode().strip()
    dirty_index = _git(root, "diff", "--cached", "--name-only", "-z", "HEAD").decode()
    return {
        "schema": ENVIRONMENT_SCHEMA,
        "reproducible": False,
        "note": (
            "absolute paths, the checkout commit and interpreter locations are recorded "
            "here rather than in the attestation, so the attestation stays byte-identical "
            "across checkouts of the same code"
        ),
        "candidate_commit": head,
        "candidate_root": root,
        "index_matches_head": dirty_index == "",
        "index_paths_differing_from_head": sorted(p for p in dirty_index.split("\x00") if p),
        "tracked_paths": len(entries),
        "sys_executable": sys.executable,
        "sys_prefix": sys.prefix,
        "sys_base_prefix": sys.base_prefix,
        "interpreter_flags": flags,
        "initial_sys_path": initial_path,
        "final_sys_path": list(sys.path),
        "sys_meta_path": [type(finder).__name__ if not isinstance(finder, type) else finder.__name__
                          for finder in sys.meta_path],
        "sys_path_hooks": [getattr(hook, "__name__", type(hook).__name__) for hook in sys.path_hooks],
        "declared_third_party": site_records,
        "module_origin_counts": counts,
        "subprocesses": {
            "python": "NONE_STARTED_BY_AUTHORITATIVE_CODE",
            "git": "READ_ONLY_INDEX_AND_OBJECT_QUERIES_BY_THIS_LAUNCHER",
        },
        "launcher": {
            "path": os.path.relpath(_real(__file__), root).replace(os.sep, "/"),
            "tracked": os.path.relpath(_real(__file__), root).replace(os.sep, "/") in entries,
            "sha256": _sha256_file(_real(__file__)),
            "self_check": (
                "BYTES_MATCH_THE_CANDIDATE_TREE_BUT_A_MODIFIED_LAUNCHER_COULD_SKIP_THIS; "
                "THE_LAUNCHER_IDENTITY_COMES_FROM_THE_CHECKOUT_IT_IS_RUN_FROM"
            ),
        },
    }


def _write_json(path: str, payload: dict) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False)
            + "\n"
        )


# --------------------------------------------------------------------------- commands


def _publish(authority: ProjectImportAuthority) -> None:
    """Expose the authority state to authenticated code, by object not by import."""

    module = types.ModuleType(AUTHORITY_MODULE)
    module.AUTHORITY_ACTIVE = AUTHORITY_ACTIVE
    module.ATTESTATION_SCHEMA = ATTESTATION_SCHEMA
    module.authority_state = lambda: {
        "state": AUTHORITY_ACTIVE,
        "attestation_schema": ATTESTATION_SCHEMA,
        "project_execution_sha256": authority.project_execution_sha256(),
    }
    sys.modules[AUTHORITY_MODULE] = module


def _run_replay(authority: ProjectImportAuthority, args) -> str:
    module = __import__("semabi.run_v4_transfer", fromlist=["replay"])
    module.replay(args.manifest, args.output)
    return args.output


def _run_freeze_source(authority: ProjectImportAuthority, args) -> str:
    module = authority.load_entry_file(
        ENTRYPOINTS["freeze-source"], "_v4_entrypoint_freeze_source"
    )
    from pathlib import Path

    module.freeze(Path(args.source), Path(args.output))
    return args.output


def _run_freeze_chain(authority: ProjectImportAuthority, args) -> str:
    module = authority.load_entry_file(
        ENTRYPOINTS["freeze-chain"], "_v4_entrypoint_freeze_chain"
    )
    from pathlib import Path

    module.freeze(
        Path(args.source_manifest),
        Path(args.transfer),
        Path(args.holdout),
        Path(args.output),
        source=Path(args.source) if args.source else None,
    )
    return args.output


def _run_attest(authority: ProjectImportAuthority, args) -> str | None:
    for name in args.module:
        __import__(name)
    if args.entry_file:
        authority.load_entry_file(args.entry_file, "_v4_entrypoint_attested")
    return None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an authoritative V4 entrypoint.")
    parser.add_argument("--attestation", help="where to write the execution attestation")
    parser.add_argument(
        "--site-packages",
        action="append",
        default=None,
        help="declared third-party directory (repeatable); defaults to the venv's",
    )
    parser.add_argument(
        "--no-site-packages",
        action="store_true",
        help="declare no third-party dependencies at all",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    replay = sub.add_parser("replay")
    replay.add_argument("--manifest", required=True)
    replay.add_argument("--output", required=True)

    freeze_source = sub.add_parser("freeze-source")
    freeze_source.add_argument("--source", required=True)
    freeze_source.add_argument("--output", required=True)

    freeze_chain = sub.add_parser("freeze-chain")
    freeze_chain.add_argument("--source-manifest", required=True)
    freeze_chain.add_argument("--transfer", required=True)
    freeze_chain.add_argument("--holdout", required=True)
    freeze_chain.add_argument("--output", required=True)
    freeze_chain.add_argument("--source", default=None)

    attest = sub.add_parser("attest")
    attest.add_argument("--module", action="append", default=[])
    attest.add_argument("--entry-file", default=None)
    attest.add_argument("--entry-kind", default=None, choices=sorted(ENTRYPOINTS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    flags = require_isolated_startup()
    root = repo_root()
    initial_path = list(sys.path)
    sources, entries = authenticated_sources(root)
    declared = derived_top_level(sources)
    if declared != tuple(sorted(PROJECT_TOP_LEVEL)):
        raise _fail(
            "TOP_LEVEL_PROJECT_NAMES_DRIFTED",
            f"tracked tree implies {declared}, authority claims {PROJECT_TOP_LEVEL}",
        )
    launcher_relative = os.path.relpath(_real(__file__), root).replace(os.sep, "/")
    launcher_expected = sources.get(launcher_relative)
    if launcher_expected is None:
        raise _fail("LAUNCHER_NOT_IN_CANDIDATE_TREE", launcher_relative)
    if open(_real(__file__), "rb").read() != launcher_expected:
        raise _fail("LAUNCHER_BYTES_DIFFER_FROM_CANDIDATE_TREE", launcher_relative)
    site_dirs, site_records = prepare_site_packages(
        root, entries, args.site_packages, not args.no_site_packages
    )
    authority = ProjectImportAuthority(root, sources, initial_path, site_dirs)
    authority.install()
    _publish(authority)

    runner = {
        "replay": _run_replay,
        "freeze-source": _run_freeze_source,
        "freeze-chain": _run_freeze_chain,
        "attest": _run_attest,
    }[args.command]
    artifact = runner(authority, args)

    entry_kind = args.command if args.command in ENTRYPOINTS else getattr(args, "entry_kind", None)
    # The comparison imports the manifests module, so run it before the exit audit and
    # before the execution digest is taken: nothing may execute after either.
    closure = closure_comparison(authority, entry_kind)
    counts = authority.audit()
    attestation = build_attestation(authority, entry_kind, artifact, root, closure)
    if args.command == "replay":
        report = json.loads(open(artifact, encoding="utf-8").read())
        claimed = report.get("authority", {}).get("execution_authority", {})
        if claimed.get("state") != AUTHORITY_ACTIVE:
            raise _fail("REPORT_DOES_NOT_RECORD_THE_AUTHORITY", json.dumps(claimed))
        if claimed.get("project_execution_sha256") != attestation["project_execution_sha256"]:
            raise _fail(
                "PROJECT_EXECUTION_SET_CHANGED_AFTER_THE_REPORT",
                f"{claimed.get('project_execution_sha256')} != "
                f"{attestation['project_execution_sha256']}",
            )
    if args.attestation:
        _write_json(args.attestation, attestation)
    environment = build_environment(root, flags, entries, site_records, initial_path, counts)
    print(
        json.dumps(
            {
                "attestation": attestation,
                "environment": environment,
                "attestation_path": args.attestation,
            },
            indent=1,
            sort_keys=True,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuthorityViolation as violation:
        sys.stderr.write(
            json.dumps({"authority": "REFUSED", "code": violation.code,
                        "detail": violation.detail}, indent=1) + "\n"
        )
        raise SystemExit(3)
