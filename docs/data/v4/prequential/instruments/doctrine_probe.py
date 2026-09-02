"""Doctrine-interaction probe: which hypotheses the search's doctrines foreclosed
without any evidence judging them.

For one corpus: the entity-type unions the hypothesis builder forms under its own
keys; the unions that survive the search's chosen keys; for each union that
vanished, the move responsible (a key withdrawn as unearned, a withheld union, a
link decision) and whether the foreclosed alternative survives anywhere as an open
question or was silently deleted.  Also every link-type decision the created-later
doctrine imposed, since those are structural, not judged.

Usage: doctrine_probe.py <run_dir> <out_json>
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")

from semabi.compiler.compile_v4 import build_hypotheses
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import search as v4_search
from semabi.compiler.v4.identity import family_key


def unions_of(H) -> dict:
    """tid -> sorted families sharing it (only tids joining >1 family)."""
    by_tid = defaultdict(set)
    for template, tid in H.tid_of_template.items():
        by_tid[tid].add(family_key(template))
    return {tid: sorted(f) for tid, f in by_tid.items() if len(f) > 1}


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    log = EvidenceLog(run)
    # before: the builder's own keys
    H0, G = build_hypotheses(run, log)
    H0._build_entity_types()
    keys_before = {u.template: u.key_slot for u in H0.units.values()}
    unions_before = unions_of(H0)
    links = [{"unit": u.template[:70], "evidence": e[:140]}
             for u in H0.units.values() for e in u.evidence if "link type" in e]
    # after: the search's chosen keys, applied to a fresh build
    H1, G1 = build_hypotheses(run, log)
    result = v4_search.search(H1, G1, log, run_dir=run)
    chosen = {t: r.key_slot for t, r in result.chosen.items()}
    # the search's own final hypotheses carry the chosen keys, the harmonised
    # composites and the withheld unions as it built them
    H2 = result.hypotheses
    if not getattr(H2, "tid_of_template", None):
        H2._build_entity_types()
    unions_after = unions_of(H2)
    before_sets = {frozenset(f) for f in unions_before.values()}
    after_sets = {frozenset(f) for f in unions_after.values()}
    open_fams = {q.template for q in result.open_questions} | {family_key(q.template) for q in result.open_questions}
    withheld = [sorted(p) for p in getattr(result, "withheld_unions", [])]
    lost = []
    for fams in sorted(before_sets - after_sets, key=sorted):
        fams = sorted(fams)
        withdrawn = [f for f in fams for t, k in chosen.items()
                     if family_key(t) == f and k is None and any(
                         keys_before.get(t2) for t2 in keys_before if family_key(t2) == f)]
        judged = any(set(w) <= set(fams) for w in withheld)
        lost.append({"union": fams,
                     "cause": ("withheld by trial" if judged else
                               f"key withdrawn: {sorted(set(withdrawn))}" if withdrawn else "unknown"),
                     "ambiguity_survives_as_question": any(f in open_fams for f in fams),
                     "judged_by_evidence": judged})
    rec = {"run": run.name, "steps": len(log.steps),
           "unions_under_builder_keys": sorted(unions_before.values()),
           "unions_under_chosen_keys": sorted(unions_after.values()),
           "unions_lost": lost, "withheld_unions": withheld,
           "link_decisions": links,
           "moves": [{"move": m.get("move"), "family": (m.get("family") or "")[:60],
                      "decided_by": m.get("decided_by")} for m in result.moves],
           "open_questions": [{"family": q.template[:60], "left": q.left.key_slot,
                               "right": q.right.key_slot} for q in result.open_questions]}
    out.write_text(json.dumps(rec, indent=1, default=str))
    silent = [l for l in lost if not l["judged_by_evidence"] and not l["ambiguity_survives_as_question"]]
    print(f"{run.name}: unions builder={len(unions_before)} chosen={len(unions_after)} "
          f"lost={len(lost)} (silently deleted: {len(silent)}) | links={len(links)} | withheld={len(withheld)}")
    for l in lost:
        print("   lost:", [f[:34] for f in l["union"]], "|", l["cause"], "| question survives:", l["ambiguity_survives_as_question"])


if __name__ == "__main__":
    main()
