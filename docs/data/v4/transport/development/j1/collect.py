"""Script-only evaluator scope adapter over the unchanged retained collector.

Scopes select public observation ancestry. They remain in evaluator decisions;
the normal Primitive contains only the original raw target node and public text.
The native collector and SemABI are imported only by an authenticated invocation.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[6]
ADAPTER = "docs/data/v4/transport/development/j1/collect.py"
VERIFICATION_FILES = frozenset({
    ADAPTER,
    "scripts/transport_collect.py",
    "semabi/compiler/browser.py",
    "semabi/compiler/observation.py",
    "semabi/compiler/evidence.py",
})


def verify_instrument(manifest_path, root=ROOT):
    """Authenticate only the declared instrument paths, never evaluator payloads.

    The retained collector still verifies its unchanged `files` allowlist. Its
    verification policy is neither patched nor expanded by this separate section.
    """
    raw = Path(manifest_path).read_bytes()
    manifest = json.loads(raw)
    declared = manifest.get("verification_files")
    if not isinstance(declared, dict) or set(declared) != VERIFICATION_FILES:
        raise RuntimeError("J1 verification_files must contain exactly the required instrument paths")
    root = Path(root).resolve()
    verified = {}
    for relative in sorted(VERIFICATION_FILES):
        expected = declared[relative]
        if (not isinstance(expected, str) or len(expected) != 64
                or any(char not in "0123456789abcdef" for char in expected)):
            raise RuntimeError(f"Invalid instrument SHA-256: {relative}")
        path = root / relative
        if path.resolve() != path or not path.is_file():
            raise RuntimeError(f"Instrument path is missing or noncanonical: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Instrument source changed: {relative}")
        verified[relative] = actual
    return {"manifest_sha256": hashlib.sha256(raw).hexdigest(), "verification_files": verified}


def _parents(nodes):
    """Validate the original flattened node indices and bounded parent graph."""
    count = len(nodes)
    parents = []
    for index, node in enumerate(nodes):
        if (type(node.i) is not int or node.i != index or type(node.parent) is not int
                or node.parent < -1 or node.parent >= count):
            raise ValueError("invalid_public_indices")
        parents.append(node.parent)
    completed = set()
    for index in range(count):
        path = set()
        cursor = index
        while cursor != -1 and cursor not in completed:
            if cursor in path:
                raise ValueError("cyclic_public_ancestry")
            path.add(cursor)
            cursor = parents[cursor]
        completed.update(path)
    return parents


def _descendant(index, group, parents):
    cursor = parents[index]
    for _ in range(len(parents)):
        if cursor == -1:
            return False
        if cursor == group:
            return True
        cursor = parents[cursor]
    return False


def scoped_resolver(original, primitive_type):
    """Wrap one collector's resolver without modifying observations or indices."""
    def resolve(obs, action):
        if "scope" not in action:
            return original(obs, action)

        kind = action.get("kind")
        role, name = action.get("role"), action.get("name")

        def failed(reason, **details):
            # Only this evaluator-side request annotation contains scope details.
            # The failure Primitive and learner-visible error omit them entirely.
            action["scope_resolution"] = {"status": "failed", "reason": reason, **details}
            descriptor = {"role": role if isinstance(role, str) else "",
                          "name": name if isinstance(name, str) else ""}
            primitive = primitive_type(kind if isinstance(kind, str) else "noop",
                                       text=action.get("value"), target_desc=descriptor)
            return primitive, "Script target is unavailable or ambiguous"

        scope = action["scope"]
        if (not isinstance(scope, dict) or set(scope) != {"role", "name", "exact"}
                or scope["role"] != "group" or not isinstance(scope["name"], str)
                or scope["exact"] is not True):
            return failed("malformed_scope")
        if (kind not in ("click", "type", "select") or not isinstance(role, str)
                or not isinstance(name, str) or action.get("exact") is not True):
            return failed("malformed_scoped_target")
        try:
            nodes = obs.nodes
            parents = _parents(nodes)
        except (AttributeError, TypeError, ValueError) as error:
            return failed("malformed_public_ancestry", detail=type(error).__name__)
        groups = [node for node in nodes if node.role == scope["role"] and node.name == scope["name"]]
        if len(groups) != 1:
            return failed("nonunique_scope", matches=len(groups))
        group = groups[0].i
        descendants = [node for node in nodes if _descendant(node.i, group, parents)]
        matches = [node for node in descendants if node.role == role and node.name == name]
        alias = False
        if not matches and role == "spinbutton":
            matches = [node for node in descendants if node.role == "textbox" and node.name == name]
            alias = bool(matches)
        if len(matches) != 1:
            return failed("nonunique_descendant", matches=len(matches))
        target = matches[0].i
        action["scope_resolution"] = {"status": "resolved", "group_node": group, "target_node": target}
        if alias:
            action["observation_role_translation"] = "spinbutton -> textbox"
        return primitive_type(kind, target, action.get("value", action.get("text"))), None

    return resolve


@contextmanager
def scoped_resolution(collector):
    original = collector.resolve
    collector.resolve = scoped_resolver(original, collector.Primitive)
    try:
        yield
    finally:
        collector.resolve = original


def _invocation(argv):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("mode", choices=("script",))
    parser.add_argument("--freeze", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args, _ = parser.parse_known_args(argv)
    return args


def _load_collector():
    path = ROOT / "scripts/transport_collect.py"
    spec = importlib.util.spec_from_file_location("_j1_retained_transport_collect", path)
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    return collector


def invoke_retained(collector, argv):
    _invocation(argv)  # Acquisition cannot enter even through this helper.
    original_argv = sys.argv
    try:
        sys.argv = [str(ROOT / ADAPTER), *argv]
        with scoped_resolution(collector):
            return collector.main()
    finally:
        sys.argv = original_argv


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = _invocation(argv)
    before = verify_instrument(args.freeze)
    output_existed = args.out.exists()
    started = datetime.now(timezone.utc).isoformat()
    collection_error = verification_error = None
    after = None
    try:
        return invoke_retained(_load_collector(), argv)
    except BaseException as error:
        collection_error = f"{type(error).__name__}: {error}"
        raise
    finally:
        try:
            after = verify_instrument(args.freeze)
            if after != before:
                raise RuntimeError("J1 instrument manifest changed during collection")
        except BaseException as error:
            verification_error = f"{type(error).__name__}: {error}"
            raise
        finally:
            # Preserve the retained run record. A separate completion gate records
            # adapter verification; callers require both records and exit code zero.
            if not output_existed and (args.out / "run.json").is_file():
                record = {
                    "schema": "semabi.j1.collector_instrument_verification.v1",
                    "status": "PASS" if collection_error is None and verification_error is None else "ERROR",
                    "start_utc": started, "end_utc": datetime.now(timezone.utc).isoformat(),
                    "before": before, "after": after, "collection_error": collection_error,
                    "verification_error": verification_error,
                }
                with (args.out / "collector_verification.json").open("x") as stream:
                    json.dump(record, stream, indent=2, sort_keys=True)
                    stream.write("\n")


if __name__ == "__main__":
    main()
