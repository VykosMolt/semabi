"""One identity search over a twin-ledger corpus, everything retained.

Usage: twin_search.py <run_dir> <out_json>
Reports chosen readings, withheld unions, promoted families, open questions
and every search move, so the union-vs-withheld deliberation is inspectable
rather than summarized.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")

from semabi.compiler.compile_v4 import build_hypotheses
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import search as v4_search
from semabi.compiler.v4.identity import family_key


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    log = EvidenceLog(run)
    lines = []
    H0, G = build_hypotheses(run, log)
    result = v4_search.search(H0, G, log, run_dir=run,
                              log_fn=lambda *a: lines.append(" ".join(map(str, a))))
    rep = {
        "run": run.name, "steps": len(log.steps),
        "chosen": {family_key(t): {"key": r.key_slot, "status": r.status}
                   for t, r in result.chosen.items()},
        "withheld_unions": [list(p) for p in result.withheld_unions],
        "promoted": sorted(map(str, getattr(result, "promoted", []))),
        "open_questions": [{"family": q.template,
                            "left": q.left.key_slot, "right": q.right.key_slot,
                            "why": getattr(q, "why", None)}
                           for q in result.open_questions],
        "moves": result.moves,
        "search_log": lines,
    }
    out.write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps({k: rep[k] for k in
                      ("chosen", "withheld_unions", "promoted", "open_questions")},
                     indent=1, default=str))


if __name__ == "__main__":
    main()
