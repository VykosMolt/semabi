"""How a reading's identity claims stand, on a surface every candidate addresses.

The behavioural ledger cannot see what the identity layer changes: fourteen prefix
closures of harbour with materially different verdict states scored every probed claim
identically (docs/v4_retained.md, Part XII).  Identity needs its own scoreboard, and the
one thing it must not do is count claims -- a finer ontology makes claims a coarser one
cannot, and out-claimed the true reading 79 to 47 on the twin ledger without being more
right about anything both addressed (Part XIII).  So every term here is scored over the
*shared* surface: state claims keyed by kind and page node -- an ontology-neutral
coordinate two readings share whatever they call the slot or the subject -- and emission
claims keyed by step, counted only where every candidate makes one.  Claims only some
candidates make are reported as provenance and never as units.

Per candidate reading of a chain's source manifest: transfer identification and the
holdout verdict from the retained frontier; coverage and contradictions on the shared
state surface; right and wrong on the shared emission steps; unshared volume on both
channels, as provenance; the survivor set the frontier could not distinguish; and the
assumptions the reading declares beyond its keys (promoted families, withheld unions).
On harbour and blend it reproduces the frontier's judgments; on vet's development
history it declines to judge -- fifteen shared atoms on which every candidate scores
alike -- and on vet's transfer history the candidates separate (Parts XIV-XV).
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"
SPLIT = 0.5


def claims_for(args) -> tuple:
    """One candidate's node-keyed state claims and per-step emission claims on the
    frozen-prefix suffix.  Module-level so a process pool can run it."""
    from dataclasses import replace
    run, name, reading_json, split = args
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4 import pinned as v4_pinned
    from semabi.eval.v4_identity_ties import RIGHT, WRONG
    reading = v4_pinned.PinnedReading.from_json(reading_json)
    model = csq.fit(Path(run), reading, split=split)
    state = {}
    for p in csq.score(model).predictions:
        coord = p.feature_node if p.feature_node is not None else p.slot
        state[f"{p.step}|{p.kind}|{coord}"] = [p.verdict, str(p.expected)]
    log = EvidenceLog(Path(run))
    cut = int(len(log.steps) * split)
    m = replace(model, log=log, cut=0)
    emission = {}
    for step in log.steps:
        if step.step < cut or step.action.kind != "click" or step.action.target is None:
            continue
        v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        if v["verdict"] in RIGHT:
            emission[step.step] = "right"
        elif v["verdict"] in WRONG:
            emission[step.step] = "wrong"
    return name, {"state": state, "emission": emission}


def score(results: dict, assumptions: dict) -> dict:
    """The scoreboard from each candidate's claims: shared surfaces, units on them,
    unshared volume as provenance.  Pure, so it can be attacked without a fit."""
    shared = set.intersection(*[set(r["state"]) for r in results.values()]) if results else set()
    shared_em = set.intersection(*[set(r["emission"]) for r in results.values()]) if results else set()
    board = {}
    for name, r in results.items():
        atoms, em = r["state"], r["emission"]
        board[name] = {
            "shared_surface": len(shared),
            "coverage_on_shared": sum(1 for k in shared if atoms[k][0] == "SUPPORTED"
                                      and atoms[k][1] not in ("", "None")),
            "contradictions_on_shared": sum(1 for k in shared if atoms[k][0] == "REFUTED"),
            "unshared_claims_provenance": len(atoms) - len(shared),
            "emission_shared_steps": len(shared_em),
            "emission_right_on_shared": sum(1 for k in shared_em if em[k] == "right"),
            "emission_wrong_on_shared": sum(1 for k in shared_em if em[k] == "wrong"),
            "emission_unshared_claims": len(em) - len(shared_em),
            "assumptions": assumptions.get(name, {"promoted_families": 0, "withheld_unions": 0}),
        }
    return board


def scoreboard(chain: Path, run: Path, frontier: Path, *, split: float = SPLIT,
               workers: int = 4) -> dict:
    from semabi.eval.v4_consequence_run import _candidates
    cands = _candidates(chain)
    front = json.loads(frontier.read_text())
    jobs = [(str(run), c.name, c.reading.to_json() if hasattr(c.reading, "to_json") else c.reading, split)
            for c in cands]
    with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as ex:
        results = dict(ex.map(claims_for, jobs))
    assumptions = {c.name: {"promoted_families": len(getattr(c.reading, "promoted_families", []) or []),
                            "withheld_unions": len(getattr(c.reading, "withheld_unions", []) or [])}
                   for c in cands}
    selected = front.get("selected")
    return {"chain": str(chain), "run": str(run), "split": split,
            "transfer_identification": front.get("identification"),
            "holdout_outcome": front.get("holdout_outcome"),
            "survivor_set": front.get("indistinguishable_classes"),
            "selected": selected.get("name") if isinstance(selected, dict) else selected,
            "candidates": score(results, assumptions)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--frontier", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", type=float, default=SPLIT)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    rec = scoreboard(Path(a.chain), Path(a.run), Path(a.frontier), split=a.split, workers=a.workers)
    path = OUT / a.out if not str(a.out).startswith("/") else Path(a.out)
    path.write_text(json.dumps(rec, indent=1, default=str))
    shared = next(iter(rec["candidates"].values()))["shared_surface"] if rec["candidates"] else 0
    print(f"{Path(a.run).name}: transfer={rec['transfer_identification']} "
          f"holdout={rec['holdout_outcome']} shared atoms={shared}")
    for n, b in rec["candidates"].items():
        print(f"  {n[:40]:40s} state {b['coverage_on_shared']:3d}/{b['contradictions_on_shared']:<3d} "
              f"unshared={b['unshared_claims_provenance']:4d} | emission "
              f"{b['emission_right_on_shared']:3d}/{b['emission_wrong_on_shared']:<3d} of "
              f"{b['emission_shared_steps']} shared, unshared={b['emission_unshared_claims']}")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
