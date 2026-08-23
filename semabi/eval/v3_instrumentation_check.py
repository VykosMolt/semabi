"""Check that an instrumented copy is identical to its original in the compiler's language.

Drives both applications through the same primitive sequence and compares the structural
signature after every step. Attributes are not part of the compiler's observation, so a
correct annotation changes nothing here; any difference means the copy is not a valid
stand-in and its trace may not be compared with the original's.
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.parse import WIDGETS


def serve(app: Path, port: int) -> subprocess.Popen:
    app = app.resolve()
    proc = subprocess.Popen([sys.executable, str(app), "--port", str(port)], cwd=app.parent,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        time.sleep(0.25)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2).read()
            return proc
        except Exception:
            continue
    raise RuntimeError(f"{app} did not serve on {port}")


def drive(port: int, seed: int, steps: int) -> list[str]:
    base = f"http://127.0.0.1:{port}"
    browser = Browser(base + "/", base + "/reset")
    signatures = []
    try:
        browser.reset(seed)
        obs = browser.observe()
        rng = random.Random(seed)
        signatures.append(obs.structural_signature())
        for _ in range(steps):
            widgets = [n for n in obs.nodes if n.role in WIDGETS]
            if not widgets:
                browser.act(Primitive("reload"))
            else:
                node = widgets[rng.randrange(len(widgets))]
                if node.role == "combobox" and node.options:
                    browser.act(Primitive("select", target=node.i,
                                          text=node.options[rng.randrange(len(node.options))]))
                elif node.role == "textbox":
                    browser.act(Primitive("type", target=node.i, text=str(rng.randrange(1, 9))))
                else:
                    browser.act(Primitive("click", target=node.i))
            obs = browser.observe()
            signatures.append(obs.structural_signature())
    finally:
        browser.close()
    return signatures


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--original", required=True)
    ap.add_argument("--instrumented", required=True)
    ap.add_argument("--port", type=int, default=8960)
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--output")
    a = ap.parse_args()
    rows = []
    for seed in [int(x) for x in a.seeds.split(",")]:
        procs = [serve(Path(a.original), a.port), serve(Path(a.instrumented), a.port + 1)]
        try:
            left = drive(a.port, seed, a.steps)
            right = drive(a.port + 1, seed, a.steps)
        finally:
            for proc in procs:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        mismatches = [i for i, (x, y) in enumerate(zip(left, right)) if x != y]
        rows.append({"seed": seed, "steps": len(left), "compared": min(len(left), len(right)),
                     "mismatches": mismatches, "identical": not mismatches and len(left) == len(right)})
        print(f"seed {seed}: {len(left)} snapshots, {len(mismatches)} mismatches")
    out = {"original": a.original, "instrumented": a.instrumented, "runs": rows,
           "identical_in_the_compilers_language": all(r["identical"] for r in rows)}
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "runs"}, indent=1))
    sys.exit(0 if out["identical_in_the_compilers_language"] else 1)


if __name__ == "__main__":
    main()
