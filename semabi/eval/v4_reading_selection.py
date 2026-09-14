"""Checks whether behaviour before the cut can choose among candidate readings, and
whether what comes after agrees. Scores each reading with the V4 objective on the prefix
(what a causal model may learn from) and with the durable-effect ledger on the suffix
(never seen during selection); a reading preferred on both is earned, refused on both is
rejected, and disagreement is reported rather than resolved. The cut keeps this
non-circular: the objective reads nothing after it, the ledger nothing before it. Readings
are data here, never changed or fit.

Three views: every candidate reading in a chain manifest; the chosen reading with each
keyed family read as no entity in turn (`--ablate`); and one family re-keyed by each of
several slots in turn (`--rekey` with `--slots`), to check whether the search's chosen key
is the one the transitions actually preserve.
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
                                 "conflicts": beh.conflicts, "named": beh.named,
                                 "positional": beh.positional,
                                 "unexplained": beh.unexplained},
            "suffix_ledger": _ledger(csq.score(model)), "_behaviour": beh}


def compare(run_dir: Path, chain: Path, *, split: float = 0.5, ablate: str | None = None,
            rekey: tuple[str, str, list[str]] | None = None) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    candidates = {c.name: c.reading for c in _candidates(chain)}
    rows = []
    if rekey is not None:
        reading_name, family, slots = rekey
        base = candidates[reading_name]
        chosen_slot = base.families[family].key_slot
        chosen = measure(run_dir, base, f"keyed by {chosen_slot} (chosen)", split=split)
        rows.append(chosen)
        for slot in slots:
            if slot == chosen_slot:
                continue
            row = measure(run_dir, base.variant(family, slot, f"keyed by {slot}"),
                          f"keyed by {slot}", split=split)
            if "_behaviour" in row and "_behaviour" in chosen:
                row["prefix_objective_prefers"] = row["_behaviour"].better_than(chosen["_behaviour"])
            rows.append(row)
    elif ablate is None:
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
            "rekeyed": None if rekey is None else {"reading": rekey[0], "family": rekey[1]},
            "readings": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--ablate", default=None, help="the reading whose keyed families are removed in turn")
    ap.add_argument("--reading", default=None, help="with --rekey: the reading whose family is re-keyed")
    ap.add_argument("--rekey", default=None, help="the family to key by each of --slots in turn")
    ap.add_argument("--slots", default=None, help="comma-separated key slots, e.g. 'cell#0|cell#0@3,cell#0@3'")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    rekey = None
    if a.rekey:
        if not (a.reading and a.slots):
            ap.error("--rekey needs --reading and --slots")
        rekey = (a.reading, a.rekey, a.slots.split(","))
    r = compare(Path(a.run), Path(a.chain), split=a.split, ablate=a.ablate, rekey=rekey)
    print(f"\n{r['run']}  split={a.split}" + (f"  ablating {a.ablate!r}" if a.ablate else "")
          + (f"  re-keying {a.rekey!r} of {a.reading!r}" if a.rekey else ""))
    for row in r["readings"]:
        if "failed" in row:
            print(f"  {row['reading'][:48]:48} FAILED {row['failed']}")
            continue
        po, led = row["prefix_objective"], row["suffix_ledger"]
        flag = ("  <- the prefix objective accepts this removal" if row.get("prefix_objective_accepts_removal")
                else "  <- the prefix objective prefers this key" if row.get("prefix_objective_prefers")
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
