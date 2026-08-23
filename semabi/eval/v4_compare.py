"""Evaluator-side comparison of the V2 and V4 observation models on one trace.

Diagnostic only.  Hidden state and the per-node entity annotations are read after
compilation, never by the compiler, and no metric here is an objective the compiler
optimises (`semabi.compiler.v4.objective` sees none of this).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.compile_v2 import compile_v2
from semabi.compiler.compile_v4 import compile_v4
from semabi.eval.oracle import evaluate
from semabi.eval.oracle_hook import align_records, load_records
from semabi.eval import oracle
from semabi.eval.v3_ladder import V3_LATENT

OBJECT_KEYS = ("grounded_frac", "pair_precision", "pair_recall", "learned_keys_merging_entities",
               "entities_split_across_keys", "entities_grounded", "duplicate_name_separation",
               "cross_view_identity")


def slim(res: dict) -> dict:
    rtc, ops = res["rtc"], res["operators"]
    return {
        "rtc": rtc["rtc"],
        "registered_transitions": rtc["transitions"],
        "registered_deltas": rtc["registered_deltas"],
        "matched_registered_deltas": rtc["strict_matched_registered_deltas"],
        "strict_registered_delta_precision": rtc["strict_registered_delta_precision"],
        "false_delta_categories": rtc.get("false_registered_delta_diagnostics", {}).get("classification_counts", {}),
        "gtc": res["gtc"]["gtc"],
        "view_false_positive_rate": res["view_false_positives"]["rate"],
        "types": res["types"], "predicates": res["predicates"],
        "operators": {k: v for k, v in ops.items() if k != "per_op"},
        "operators_per_op": {k: [v["successes"], v["explained"]] for k, v in ops.get("per_op", {}).items()},
        "object_layer": {k: res["object_layer"].get(k) for k in OBJECT_KEYS},
        "argument_binding": {k: round(v.get("action_arguments_grounded_rate") or 0.0, 3)
                             for k, v in res.get("argument_binding", {}).get("per_op", {}).items()},
        "cost_primitives": res["cost"]["primitives"],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--tag", required=True, help="V3 app tag, for the latent declaration")
    ap.add_argument("--min-support", type=int, default=2)
    ap.add_argument("--identity-from", help="pin the identity readings chosen on another run "
                                            "(a prospective test: they were not chosen here)")
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    run = Path(a.run)
    oracle.LATENT[run.name] = V3_LATENT[a.tag]

    pinned = None
    if a.identity_from:
        source = json.loads((Path(a.identity_from) / "identity_readings_v4.json").read_text())
        # transfer by family: a template string carries the tokens one trace rendered
        pinned = {}
        for family, templates in source.get("families", {}).items():
            for template in templates:
                row = source["chosen"].get(template)
                if row is not None:
                    pinned[family] = row["key_slot"]
                    break
        out_note = {"identity_from": a.identity_from, "pinned_families": len(pinned),
                    "keyed_by": "family"}
    else:
        out_note = None

    out: dict = {"run": str(run), "tag": a.tag, "conditions": {}, "prospective": out_note}
    conditions = [("v2", compile_v2(run, min_support=a.min_support, llm=None,
                                    apply_refinements=True, write_diagnostics=False)),
                  ("v4", compile_v4(run, min_support=a.min_support, write_diagnostics=True))]
    if pinned is not None:
        conditions.append(("v4_pinned", compile_v4(run, min_support=a.min_support,
                                                   write_diagnostics=False, identity=pinned)))
    for name, compiled in conditions:
        records = align_records(compiled.log, load_records(run))
        result = evaluate(compiled, run, records, v1_like=True, tag=name, abstr_ids=False)
        out["conditions"][name] = slim(result)
        if name == "v4" and getattr(compiled, "v4", None) is not None:
            out["v4_search"] = {"initial": compiled.v4.initial.to_json(),
                                "final": compiled.v4.final.to_json(),
                                "moves": compiled.v4.moves,
                                "open_questions": [q.to_json() for q in compiled.v4.open_questions],
                                "families": {f: len(t) for f, t in compiled.v4.families.items()}}
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=1))
    for name, row in out["conditions"].items():
        o, t, p = row["operators"], row["types"], row["predicates"]
        print(f"{name}: rtc={row['rtc'] if row['rtc'] is not None else float('nan'):.3f} strictprec={row['strict_registered_delta_precision']} "
              f"deltas={row['registered_deltas']} matched={row['matched_registered_deltas']} "
              f"types={t['recovered']}/{t['hidden']} attrs={p['recovered_attrs']}/{p['hidden_attrs']} "
              f"rels={p['recovered_rels']}/{p['hidden_rels']} ops={o['recovered']}/{o['observed_in_trace']} "
              f"viewFP={row['view_false_positive_rate']:.3f}")
        print(f"    object layer: {row['object_layer']}")
        print(f"    false deltas: {row['false_delta_categories']}")


if __name__ == "__main__":
    main()
