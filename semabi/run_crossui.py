"""CLI: compare learned models from two runs (no hidden information used)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.model import LearnedModel
from semabi.eval.crossui import compare_models


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_a")
    ap.add_argument("run_b")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    A = LearnedModel.load(Path(a.run_a) / "model.json")
    B = LearnedModel.load(Path(a.run_b) / "model.json")
    r = compare_models(A, B)
    print(r.report())
    if a.out:
        Path(a.out).write_text(json.dumps({"type_map": r.type_map, "attr_map": r.attr_map, "rel_map": r.rel_map,
                                           "ops_a": r.ops_a, "ops_b": r.ops_b, "equivalent": r.equivalent, "score": r.score,
                                           "per_op": r.per_op}, indent=1))


if __name__ == "__main__":
    main()
