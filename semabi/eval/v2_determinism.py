"""Compiled models and the action alphabet must not depend on PYTHONHASHSEED.

Runs the same compiles in a fresh interpreter per hash seed and compares a structural
digest of the learned model together with the full control-family registry.  Any
difference means some iteration order leaked into the abstraction, which would make every
other result unreproducible.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROBE = r'''
import json
from pathlib import Path
from semabi.compiler.compile_v2 import compile_v2
from semabi.compiler.v2.refinement import read_decisions
from semabi.compiler.v2.validation import _compile_digest

out = {}
for run, src in json.loads(__import__("sys").argv[1]):
    decisions = [d for d in read_decisions(Path(src))
                 if d.get("status") in ("SUPPORTED", "PROVISIONAL", "MISPREDICTED", "VALIDATED")]
    for refine in (False, True):
        c = compile_v2(Path(run), min_support=2, llm=None, apply_refinements=refine,
                       refinement_decisions=decisions if refine else None, write_diagnostics=False)
        out[f"{Path(run).name}|refined={refine}"] = {
            "model": _compile_digest(c),
            "control_families": {k: v.descriptor() for k, v in sorted(c.abstractor.controls.families.items())},
        }
print(json.dumps(out, sort_keys=True, default=str))
'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", action="append", required=True, help="RUN:DECISION_SOURCE_RUN")
    parser.add_argument("--seed", action="append", default=["0", "1", "7"])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    pairs = [p.rsplit(":", 1) for p in args.pair]
    results = {}
    for seed in args.seed:
        env = {**os.environ, "PYTHONHASHSEED": str(seed), "PYTHONPATH": "."}
        proc = subprocess.run([sys.executable, "-c", PROBE, json.dumps(pairs)],
                              capture_output=True, text=True, env=env)
        if proc.returncode != 0:
            raise RuntimeError(f"probe failed for seed {seed}: {proc.stderr[-2000:]}")
        results[seed] = json.loads(proc.stdout)
    seeds = list(results)
    reference = results[seeds[0]]
    differing = sorted(k for k in reference
                       for other in seeds[1:] if results[other].get(k) != reference[k])
    report = {
        "version": 1,
        "question": "does the compiled model or the control-family alphabet depend on PYTHONHASHSEED?",
        "hash_seeds": seeds,
        "compiles": sorted(reference),
        "identical_across_hash_seeds": not differing,
        "differing_compiles": differing,
        "families_per_compile": {k: len(v["control_families"]) for k, v in sorted(reference.items())},
        "digests": {k: v["model"] for k, v in sorted(reference.items())},
        "control_families": {k: v["control_families"] for k, v in sorted(reference.items())},
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({k: report[k] for k in
                      ("hash_seeds", "identical_across_hash_seeds", "differing_compiles",
                       "families_per_compile")}, indent=1))


if __name__ == "__main__":
    main()
