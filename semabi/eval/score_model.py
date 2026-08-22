"""Score any model.json (ours, LLM baseline, known-vocabulary baseline) against a
hidden domain with the direct structural/behavioural comparison (no paired data)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.model import LearnedModel
from semabi.eval.crossui import compare_models
from semabi.hidden.taskdomain import make_domain

HIDDEN_KEYS = {"Project": "name", "Task": "title"}


def hidden_as_model(variant: str) -> LearnedModel:
    return LearnedModel(make_domain(variant), {}, dict(HIDDEN_KEYS))


def score(model_path: Path, variant: str, seed: int = 0) -> dict:
    H = hidden_as_model(variant)
    M = LearnedModel.load(model_path)
    r = compare_models(H, M, seed=seed, n_states=30)
    per = {x["a"]: x for x in r.per_op}
    return {"variant": variant, "model": str(model_path), "types_matched": len(r.type_map), "hidden_types": len(H.domain.types),
            "learned_types": len(M.domain.types), "attr_map": r.attr_map, "rel_map": r.rel_map,
            "ops_recovered": r.equivalent, "hidden_ops": r.ops_a, "learned_ops": r.ops_b,
            "op_precision": r.equivalent / max(1, r.ops_b),
            "mean_pre_agree": sum(x["pre"] for x in r.per_op) / len(r.per_op), "mean_eff_agree": sum(x["eff"] for x in r.per_op) / len(r.per_op),
            "per_op": per}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--variant", default="standard")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = score(Path(a.model), a.variant)
    print(f"types {r['types_matched']}/{r['hidden_types']} (learned {r['learned_types']}); ops {r['ops_recovered']}/{r['hidden_ops']} "
          f"(learned {r['learned_ops']}, precision {r['op_precision']:.2f}); pre {r['mean_pre_agree']:.2f} eff {r['mean_eff_agree']:.2f}")
    for k, x in r["per_op"].items():
        print(f"   {k:16s} -> {str(x['b']):8s} pre={x['pre']:.2f} eff={x['eff']:.2f}")
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
