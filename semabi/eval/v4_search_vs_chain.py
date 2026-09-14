"""Compares what the identity search chooses on its own against the reading a chain
manifest carries. Chain manifests pin readings chosen by earlier sessions' frontier tools,
while `semabi.compiler.v4.search` is what fresh generation actually runs. This runs the
search on a run's prefix under the certified regime and scores its reading and the
chain's on the same suffix: a tie means the instruments' numbers stand for the search;
a difference is a fact about the objective.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from semabi.compiler.compile_v4 import _normalise_sections, build_hypotheses
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import pinned as pn
from semabi.compiler.v4 import search as v4_search
from semabi.eval.v4_reading_selection import _ledger

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def compare(run_dir: Path, chain: Path, chain_reading: str, *, split: float = 0.5) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    run_dir = Path(run_dir)
    full = EvidenceLog(run_dir)
    cut = int(len(full.steps) * split)
    _normalise_sections(full, stats_from=full.through(cut))
    prefix = full.through(cut)
    H, G = build_hypotheses(run_dir, prefix)
    notes: list[str] = []
    result = v4_search.search(H, G, prefix, log_fn=notes.append, run_dir=run_dir)
    by_tid: dict[int, list] = defaultdict(list)
    for template, tid in result.hypotheses.tid_of_template.items():
        by_tid[tid].append({"template": template, "key_slot": result.hypotheses.units[template].key_slot})
    reading = pn.from_search(result, run_dir, name="search")
    search_ledger = _ledger(csq.score(csq.fit(run_dir, reading, split=split)))
    chain_r = {c.name: c.reading for c in _candidates(chain)}[chain_reading]
    chain_ledger = _ledger(csq.score(csq.fit(run_dir, chain_r, split=split)))
    return {"run": run_dir.name, "chain": str(chain), "chain_reading": chain_reading, "split": split,
            "cut": cut, "search": {"final": result.final.to_json(), "moves": result.moves,
                                   "withheld_unions": [list(p) for p in result.withheld_unions],
                                   "open_questions": [q.to_json() for q in result.open_questions],
                                   "entity_types": {str(t): us for t, us in sorted(by_tid.items())},
                                   "reading": reading.to_json(), "notes": notes},
            "suffix_ledger": {"search": search_ledger, "chain": chain_ledger},
            "families": {fam: {"search": reading.families[fam].key_slot if fam in reading.families else None,
                               "chain": chain_r.families[fam].key_slot if fam in chain_r.families else None}
                         for fam in sorted(set(reading.families) | set(chain_r.families))}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True, help="the chain's reading to compare with")
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    r = compare(Path(a.run), Path(a.chain), a.reading, split=a.split)
    print(f"\n{r['run']}  split={a.split}")
    for m in r["search"]["moves"]:
        print("  move", {k: v for k, v in m.items() if k != "score"})
    for fam, d in r["families"].items():
        flag = "" if d["search"] == d["chain"] else "   <- differs"
        print(f"  {fam[:60]:60} search={d['search']!s:22} chain={d['chain']!s:22}{flag}")
    print(f"  suffix ledger: search {r['suffix_ledger']['search']}  chain {r['suffix_ledger']['chain']}")
    if a.out:
        path = OUT / a.out if not str(a.out).startswith("/") else Path(a.out)
        path.write_text(json.dumps(r, indent=1, default=str))
        print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
