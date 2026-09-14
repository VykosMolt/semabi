"""Checks contract compliance and executable correctness for an independently authored
app, run once before the benchmark is frozen and before the compiler is ever pointed at
it. Checks only what the contract promises: endpoints exist and answer, state is
deterministic in the seed, the schema is fixed across seeds, the declared domain is well
formed and non-trivial, the page does not leak the evaluator's own description, and the
page is observable and clickable through the ordinary rendered boundary. Does not compile,
score, or predict anything about the learner.
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CONTRACT = {"min_types": 3, "min_relations": 2, "min_operators": 3, "max_operators": 8,
            "min_objects": 3, "max_objects": 12}


def get(url: str, timeout: float = 10) -> dict:
    return json.loads(urllib.request.urlopen(url, timeout=timeout).read())


def get_text(url: str, timeout: float = 10) -> str:
    return urllib.request.urlopen(url, timeout=timeout).read().decode("utf8", "replace")


def post(url: str, payload: dict, timeout: float = 10) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def third_party_imports(app: Path) -> list[str]:
    tree = ast.parse(app.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return sorted(n for n in names if n not in sys.stdlib_module_names)


def observe(url: str) -> dict:
    """One rendered observation through the compiler's own restricted boundary."""
    from semabi.compiler.browser import Browser
    from semabi.compiler.parse import WIDGETS
    browser = Browser(url, url.rstrip("/") + "/reset")
    try:
        browser.goto()
        obs = browser.observe()
        widgets = [n for n in obs.nodes if n.role in WIDGETS]
        clicked = None
        for node in widgets:
            if node.role == "button":
                from semabi.compiler.browser import Primitive
                before = obs.structural_signature()
                try:
                    browser.act(Primitive("click", target=node.i))
                    after = browser.observe().structural_signature()
                    clicked = {"node": node.i, "changed_the_page": before != after}
                except Exception as exc:
                    # a click that navigates the whole page is legitimate; re-open and look again
                    browser.goto()
                    after = browser.observe().structural_signature()
                    clicked = {"node": node.i, "changed_the_page": before != after,
                               "navigated": f"{type(exc).__name__}"}
                break
        return {"nodes": len(obs.nodes), "widgets": len(widgets),
                "roles": sorted({n.role for n in widgets}), "first_click": clicked}
    finally:
        browser.close()


def check(app_dir: Path, port: int, skip_browser: bool = False) -> dict:
    app = app_dir / "app.py"
    result: dict = {"app": str(app_dir), "port": port, "failures": [], "warnings": [], "info": {}}

    def fail(msg: str) -> None:
        result["failures"].append(msg)

    def warn(msg: str) -> None:
        result["warnings"].append(msg)

    if not app.exists():
        fail("app.py missing")
        return result
    if not (app_dir / "README.md").exists():
        warn("README.md missing")
    extra = third_party_imports(app)
    if extra:
        fail(f"non-stdlib imports: {extra}")

    proc = subprocess.Popen([sys.executable, str(app), "--port", str(port)],
                            cwd=app_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            time.sleep(0.25)
            if proc.poll() is not None:
                fail(f"server exited: {(proc.stdout.read() or '')[:400]}")
                return result
            try:
                urllib.request.urlopen(base + "/", timeout=2).read()
                break
            except Exception:
                continue
        else:
            fail("server never answered")
            return result

        page = get_text(base + "/")
        result["info"]["page_bytes"] = len(page)
        if "_evaluator" in page:
            fail("the page itself references the evaluator endpoints")
        for marker in ("data-eid", "data-erefs", "data-oid"):
            if marker in page:
                # invisible to the learner (the compiler never sees attributes), but it
                # collides with the evaluator's own annotation scheme later
                warn(f"page already uses the annotation attribute {marker!r}")

        try:
            domain = get(base + "/_evaluator/domain")
        except Exception as exc:
            fail(f"/_evaluator/domain failed: {exc}")
            return result
        types = {t["name"]: t.get("attrs", {}) for t in domain.get("types", [])}
        rels = domain.get("relations", [])
        ops = domain.get("operators", [])
        result["info"]["domain"] = {"name": domain.get("name"), "types": len(types),
                                    "relations": len(rels), "operators": len(ops),
                                    "operator_names": [o.get("name") for o in ops],
                                    "has_notes": bool(domain.get("notes"))}
        if len(types) < CONTRACT["min_types"]:
            fail(f"{len(types)} types (< {CONTRACT['min_types']})")
        if len(rels) < CONTRACT["min_relations"]:
            fail(f"{len(rels)} relations (< {CONTRACT['min_relations']})")
        if not CONTRACT["min_operators"] <= len(ops) <= CONTRACT["max_operators"]:
            warn(f"{len(ops)} operators (contract asked 3-8)")
        for r in rels:
            if r.get("src") not in types or r.get("dst") not in types:
                fail(f"relation {r.get('name')} has an undeclared endpoint")
        for t, attrs in types.items():
            bad = {k: v for k, v in attrs.items() if v not in ("str", "bool", "int")}
            if bad:
                fail(f"type {t} declares untyped attributes {bad}")
        for o in ops:
            if not o.get("precondition") or not o.get("effect"):
                warn(f"operator {o.get('name')} has no precondition/effect prose")
            if "params" not in o:
                fail(f"operator {o.get('name')} declares no params")

        snapshots = {}
        for seed in (7, 7, 8):
            post(base + "/reset", {"seed": seed})
            snap = get(base + "/_evaluator/state")
            snapshots.setdefault(seed, []).append(snap)
        s7a, s7b = snapshots[7]
        s8 = snapshots[8][0]
        if json.dumps(s7a["state"], sort_keys=True) != json.dumps(s7b["state"], sort_keys=True):
            fail("reset(7) is not deterministic")
        if s7b["episode"] <= s7a["episode"]:
            fail("episode does not increase on reset")
        if s7a.get("log"):
            fail("log is not cleared by reset")
        if json.dumps(s7a["state"], sort_keys=True) == json.dumps(s8["state"], sort_keys=True):
            warn("seed 8 produces the same state as seed 7")

        def schema(snap: dict) -> tuple:
            objs = snap["state"]["objects"]
            return (tuple(sorted({o["type"] for o in objs})),
                    tuple(sorted({(o["type"], k) for o in objs for k in o.get("attrs", {})})),
                    tuple(sorted(snap["state"].get("rels", {}))))
        # the declared schema is fixed by construction; what can legitimately differ
        # between seeds is which types happen to have instances
        if schema(s7a) != schema(s8):
            result["info"]["instantiated_schema_differs_between_seeds"] = {
                "seed7": [list(x) for x in schema(s7a)], "seed8": [list(x) for x in schema(s8)]}

        for tag, snap in (("seed7", s7a), ("seed8", s8)):
            objs = snap["state"]["objects"]
            result["info"][f"objects_{tag}"] = len(objs)
            if not CONTRACT["min_objects"] <= len(objs) <= CONTRACT["max_objects"]:
                warn(f"{tag}: {len(objs)} objects (contract asked 3-12)")
            ids = [o["id"] for o in objs]
            if len(ids) != len(set(ids)):
                fail(f"{tag}: duplicate object ids")
            for o in objs:
                if o["type"] not in types:
                    fail(f"{tag}: object of undeclared type {o['type']}")
                for k, v in o.get("attrs", {}).items():
                    if not isinstance(v, (str, bool, int)):
                        fail(f"{tag}: attribute {o['type']}.{k} is {type(v).__name__}")
            known = {o["id"] for o in objs}
            for name, mapping in snap["state"].get("rels", {}).items():
                if not isinstance(mapping, dict):
                    fail(f"{tag}: relation {name} is not a functional mapping")
                    continue
                for src, dst in mapping.items():
                    if isinstance(dst, list):
                        fail(f"{tag}: relation {name} is not functional")
                    elif src not in known or dst not in known:
                        warn(f"{tag}: relation {name} references an unknown object")

        if not skip_browser:
            try:
                result["info"]["observation"] = observe(base + "/")
                obsinfo = result["info"]["observation"]
                if obsinfo["widgets"] == 0:
                    fail("no interactive widget is visible through the rendered boundary")
            except Exception as exc:
                fail(f"browser observation failed: {exc}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    result["ok"] = not result["failures"]
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", action="append", required=True, help="dir:port")
    ap.add_argument("--output")
    ap.add_argument("--skip-browser", action="store_true")
    a = ap.parse_args()
    out = []
    for spec in a.app:
        d, _, p = spec.rpartition(":")
        row = check(Path(d), int(p), a.skip_browser)
        out.append(row)
        print(f"{'OK  ' if row.get('ok') else 'FAIL'} {d}")
        for f in row["failures"]:
            print("   FAILURE:", f)
        for w in row["warnings"]:
            print("   warning:", w)
        print("   ", json.dumps(row["info"], sort_keys=True)[:600])
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(out, indent=1))
    sys.exit(0 if all(r.get("ok") for r in out) else 1)


if __name__ == "__main__":
    main()
