"""Identity scoreboard v0: how a reading's identity claims stand, without claim counts.

Terms (per candidate reading of a chain's source manifest):
  - transfer distinction / holdout confirmation: read from the retained frontier;
  - explanatory coverage and contradictions over the SHARED, node-keyed evidence
    surface: state claims all candidates make about the same page atoms (kind, node),
    scored as supported / refuted -- atoms only one candidate speaks to are counted as
    unshared provenance and never as coverage (Finding 5: raw claim volume is
    contaminated by ontology granularity);
  - survivor-set size: candidates the frontier could not distinguish;
  - declared assumptions: promoted families and withheld unions a reading carries
    beyond its keys.

Usage: identity_scoreboard.py --chain <manifest> --run <source run> --frontier <json> --out <json>
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")

SPLIT = 0.5


def atoms_for(args):
    """One candidate's node-keyed state claims on the frozen-prefix suffix."""
    run, name, reading_json = args
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import pinned as v4_pinned
    reading = v4_pinned.PinnedReading.from_json(reading_json)
    model = csq.fit(Path(run), reading, split=SPLIT)
    out = {}
    for p in csq.score(model).predictions:
        coord = p.feature_node if p.feature_node is not None else p.slot
        out[f"{p.step}|{p.kind}|{coord}"] = [p.verdict, str(p.expected)]
    return name, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--frontier", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    from semabi.eval.v4_consequence_run import _candidates
    cands = _candidates(Path(a.chain))
    frontier = json.loads(Path(a.frontier).read_text())
    jobs = [(a.run, c.name, c.reading.to_json() if hasattr(c.reading, "to_json") else c.reading)
            for c in cands]
    with ProcessPoolExecutor(max_workers=min(a.workers, len(jobs))) as ex:
        results = dict(ex.map(atoms_for, jobs))
    shared = set.intersection(*[set(r) for r in results.values()]) if results else set()
    board = {}
    for c in cands:
        atoms = results[c.name]
        supported = sum(1 for k in shared if atoms[k][0] == "SUPPORTED" and atoms[k][1] not in ("", "None"))
        refuted = sum(1 for k in shared if atoms[k][0] == "REFUTED")
        rd = c.reading
        board[c.name] = {
            "shared_surface": len(shared),
            "coverage_on_shared": supported, "contradictions_on_shared": refuted,
            "unshared_claims_provenance": len(atoms) - len(shared),
            "assumptions": {"promoted_families": len(getattr(rd, "promoted_families", []) or []),
                            "withheld_unions": len(getattr(rd, "withheld_unions", []) or [])},
        }
    rec = {"chain": a.chain, "run": a.run,
           "transfer_identification": frontier.get("identification"),
           "holdout_outcome": frontier.get("holdout_outcome"),
           "survivor_set": frontier.get("indistinguishable_classes"),
           "selected": (frontier.get("selected") or {}).get("name") if isinstance(frontier.get("selected"), dict) else frontier.get("selected"),
           "candidates": board}
    Path(a.out).write_text(json.dumps(rec, indent=1, default=str))
    print(f"{Path(a.run).name}: transfer={rec['transfer_identification']} holdout={rec['holdout_outcome']} shared atoms={len(shared)}")
    for n, b in board.items():
        print(f"  {n[:40]:40s} coverage={b['coverage_on_shared']:4d} contradictions={b['contradictions_on_shared']:3d} "
              f"unshared={b['unshared_claims_provenance']:4d} assumptions={b['assumptions']}")


if __name__ == "__main__":
    main()
