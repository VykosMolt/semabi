"""Can behaviour before the cut choose among readings, and does what comes after agree?

A reading -- which recurring structures are objects and what names them -- is proposed from
page structure alone (`semabi.compiler.v4.identity`).  Several are always plausible, and the
question this instrument asks of each is the one a black-box learner can legitimately ask:
what does the V4 objective (`semabi.compiler.v4.objective`) make of it on the **prefix**,
the completed transitions a causal model may learn from, and what does the durable-effect
ledger make of it on the **suffix**, which the selection never saw.  A reading the prefix
objective prefers and the suffix confirms is a distinction that earned its place; a reading
the objective refuses that the suffix also punishes is a distinction behaviour rejects;
and where the two disagree, the instrument says so rather than choosing.

Circularity is kept out by the cut: the objective reads nothing after it, and the ledger
reads nothing before it.  Nothing here changes a reading or fits one; readings are data, and
this compares them.

Two views: every candidate reading in a chain manifest, and the chosen reading with each of
its keyed families read as no entity in turn (`--ablate`), which asks of every type
whether the evidence before the cut wanted it.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import objective
from semabi.eval import v4_claim_substance as cs

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/data/v4"


def _ledger(result) -> dict[str, int]:
    at: dict = defaultdict(Counter)
    for p in result.predictions:
        if p.kind in cs.STATE_CLAIMS:
            at[(p.step, p.control)][p.verdict] += 1
    led: Counter = Counter()
    for c in at.values():
        sup, ref, poss = c[csq.SUPPORTED], c[csq.REFUTED], c[csq.POSSIBLE]
        led["right" if sup and not ref else "disagreed" if sup and ref else "contradicted" if ref
            else "undecidable" if poss else "unbound" if c[csq.UNKNOWN] else "no rule"] += 1
    return dict(led)


def measure(run_dir: Path, reading, label: str, *, split: float = 0.5) -> dict:
    try:
        model = csq.fit(Path(run_dir), reading, split=split)
    except Exception as exc:  # noqa: BLE001 - a reading that cannot be built is reported as such
        return {"reading": label, "failed": f"{type(exc).__name__}: {exc}"[:120]}
    beh = objective.evaluate(model.abstractor, model.log, model.cut)
    return {"reading": label, "types": len(model.abstractor.types),
            "prefix_objective": {"explained": beh.explained, "errors": beh.errors,
                                 "visibility": beh.visibility, "churn": beh.churn,
                                 "spurious": beh.spurious, "contradictions": beh.contradictions,
                                 "unexplained": beh.unexplained},
            "suffix_ledger": _ledger(csq.score(model)), "_behaviour": beh}


def compare(run_dir: Path, chain: Path, *, split: float = 0.5, ablate: str | None = None) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    candidates = {c.name: c.reading for c in _candidates(chain)}
    rows = []
    if ablate is None:
        for name, reading in candidates.items():
            rows.append(measure(run_dir, reading, name, split=split))
    else:
        base = candidates[ablate]
        chosen = measure(run_dir, base, ablate, split=split)
        rows.append(chosen)
        for family, fr in sorted(base.families.items()):
            if fr.key_slot is None:
                continue
            row = measure(run_dir, base.variant(family, None, f"without {family}"),
                          f"without {family}", split=split)
            if "_behaviour" in row and "_behaviour" in chosen:
                row["prefix_objective_accepts_removal"] = row["_behaviour"].better_than(chosen["_behaviour"])
            rows.append(row)
    for row in rows:
        row.pop("_behaviour", None)
    return {"run": Path(run_dir).name, "chain": str(chain), "split": split, "ablated": ablate,
            "readings": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--ablate", default=None, help="the reading whose keyed families are removed in turn")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    r = compare(Path(a.run), Path(a.chain), split=a.split, ablate=a.ablate)
    print(f"\n{r['run']}  split={a.split}" + (f"  ablating {a.ablate!r}" if a.ablate else ""))
    for row in r["readings"]:
        if "failed" in row:
            print(f"  {row['reading'][:48]:48} FAILED {row['failed']}")
            continue
        po, led = row["prefix_objective"], row["suffix_ledger"]
        flag = ("  <- the prefix objective accepts this removal" if row.get("prefix_objective_accepts_removal")
                else "")
        print(f"  {row['reading'][:48]:48} types={row['types']:2}  prefix explained={po['explained']:3} "
              f"errors={po['errors']:3} (visibility {po['visibility']}, churn {po['churn']})  "
              f"suffix {led}{flag}")
    if a.out:
        path = OUT / a.out if not str(a.out).startswith("/") else Path(a.out)
        path.write_text(json.dumps(r, indent=1))
        print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
