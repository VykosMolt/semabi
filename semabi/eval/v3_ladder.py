"""Oracle localization ladder for the V3 applications (evaluator side, post-freeze).

Runs after the ordinary V3 result is recorded. The frozen compiler is never given any of
this: the rungs replace only the Abstractor/Tracker the V0 inducer consumes, exactly as in
`docs/v2_oracle.md`, and the ladder's output never returns to the compiler.

Rungs C, D and K need only the hidden state and hidden log, which the evaluator already
recorded during the official run; A, B and Bv additionally need per-node entity
annotations, which only an instrumented copy of an application can supply.

The latent-attribute declarations are read from each application's own
`/_evaluator/domain` notes and injected here rather than edited into `oracle.py`, so the
evaluator that produced the ordinary result stays byte-identical.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.eval import oracle

# Declared by the authors in their `notes` field. Three of the four applications state
# that every attribute is rendered somewhere; the cellar has exactly one attribute that
# is never rendered and never read by a precondition or effect.
V3_LATENT = {
    # the two applications the V2 runtime could not trace at all; both authors state that
    # every attribute is rendered somewhere (their /_evaluator/domain notes)
    "grok_01_landing_board": set(),
    "grok_02_blend_book": set(),
    "opus_01_harbour": set(),
    "opus_02_cellar": {("Block", "rootstock")},
    "sonnet_01_vet_clinic": set(),
    "sonnet_02_barter_market": set(),
}


def install(tag: str, extra: str | None = None) -> None:
    for suffix in ("loop", "seed11", "seed12", "seed13"):
        oracle.LATENT[f"{tag}_{suffix}"] = V3_LATENT[tag]
    if extra:
        oracle.LATENT[extra] = V3_LATENT[tag]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--runs", default="runs/v3")
    ap.add_argument("--rungs", default="C,D,K")
    ap.add_argument("--min-support", type=int, default=2)
    ap.add_argument("--run", help="explicit run directory (an annotated trace)")
    ap.add_argument("--output")
    a = ap.parse_args()
    run_dir = Path(a.run) if a.run else Path(a.runs) / f"{a.tag}_loop"
    install(a.tag, run_dir.name)
    results = oracle.run_ladder(run_dir, a.rungs.split(","), min_support=a.min_support)
    summary = {}
    for rung, res in results.items():
        ops = res["operators"]
        summary[rung] = {
            "types": [res["types"]["recovered"], res["types"]["hidden"]],
            "attrs": [res["predicates"]["recovered_attrs"], res["predicates"]["hidden_attrs"]],
            "rels": [res["predicates"]["recovered_rels"], res["predicates"]["hidden_rels"]],
            "operators_recovered": ops["recovered"],
            "operators_observed": ops["observed_in_trace"],
            "operators_hidden": ops["hidden"],
            "operators_learned": ops["learned"],
            "spurious_learned": len(ops["spurious_learned"]),
            "failure_rejection_rate": ops["failure_rejection_rate"],
            "gtc": res["gtc"]["gtc"],
            "rtc": res.get("rtc", {}).get("rtc"),
            "per_op": {k: [v["successes"], v["explained"]] for k, v in ops["per_op"].items()},
        }
    out = {"tag": a.tag, "rungs": summary, "latent": sorted(V3_LATENT[a.tag])}
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(out, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
