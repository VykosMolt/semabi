"""Cross-UI comparisons for all UI pairs of a matrix prefix (same variant/labels/seed)."""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

from semabi.compiler.model import LearnedModel
from semabi.eval.crossui import compare_models


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="final")
    ap.add_argument("--out", default="runs/crossui.json")
    a = ap.parse_args()
    runs = sorted(p for p in Path("runs").glob(f"{a.prefix}_*_s*") if (p / "model.json").exists())
    groups: dict[tuple, list[Path]] = {}
    for r in runs:
        v, l, ui, seed = r.name.split("_")[1:5]
        groups.setdefault((v, l, seed), []).append(r)
    results = []
    for key, rs in sorted(groups.items()):
        for ra, rb in itertools.combinations(rs, 2):
            A, B = LearnedModel.load(ra / "model.json"), LearnedModel.load(rb / "model.json")
            c = compare_models(A, B)
            results.append({"a": ra.name, "b": rb.name, "equivalent": c.equivalent, "ops_a": c.ops_a, "ops_b": c.ops_b, "score": c.score,
                            "type_map": c.type_map, "attr_map": c.attr_map, "rel_map": c.rel_map})
            print(f"{ra.name} vs {rb.name}: {c.equivalent}/{c.ops_a} (B has {c.ops_b}) score={c.score:.2f}", flush=True)
    Path(a.out).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
