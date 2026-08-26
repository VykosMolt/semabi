"""Three different facts about a reading, kept apart.

The frontier reports one outcome per application and it has been carrying three claims at
once.  They come from different evidence and they can disagree, so conflating them lets a
weak one inherit a strong one's authority.

* **Structural** -- which readings the candidate space still contains after transfer.  This
  is about the search, and a singleton here means the comparison eliminated the others, not
  that the world did.
* **Retrospective** -- which of them the already-observed history contradicted, and which
  produced identical observable state deltas at every step of it.  A reading survives this
  by describing what happened; two readings can both survive by describing it differently.
* **Prospective** -- what happened when rules fitted on a prefix predicted a suffix and the
  prediction was checked at the raw structure the action affected.  This is the only one of
  the three that can be *wrong* about something it had not seen.

The probe family is part of the claim.  Everything here is measured under single clicks on
the controls these applications render, checked one step ahead at the affected node; two
readings equal under that probe are equal under that probe and nothing more.  Saying so is
not a hedge -- an equivalence between models is always relative to the experiments allowed,
and the interesting cases below are exactly the ones where the probe cannot reach the
decision the readings disagree about.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

PROBE = ("single clicks on the controls the application renders, one step ahead, checked at "
         "the raw node the effect names, with the predicted field masked from correspondence")

REFUTED_EVERYWHERE = "REFUTED_ON_EVERY_TRACE_THAT_REACHED_IT"
REFUTED_SOMEWHERE = "REFUTED_ON_SOME_TRACES_AND_NOT_OTHERS"
UNREFUTED = "UNREFUTED_WHERE_THE_INSTRUMENT_REACHED_IT"
NOT_REACHED = "THE_INSTRUMENT_MADE_NO_TESTABLE_CLAIM_FOR_THIS_READING"


def structural(report: dict) -> dict[str, Any]:
    return {"basis": "pairwise transfer comparison on a second spent history",
            "outcome": report["outcome"],
            "survivors": [row["name"] for row in report["survivors"]],
            "selected": (report["selected"] or {}).get("name")}


def retrospective(report: dict) -> dict[str, Any]:
    classes = report.get("indistinguishable_classes") or {}
    return {"basis": classes.get("basis", "observable state deltas over the whole history"),
            "outcome": report["holdout_outcome"],
            "classifications": report["holdout"]["classifications"],
            "identification": report.get("identification"),
            "classes_among_survivors": classes.get("survivor_classes", [])}


def prospective(rows: list[dict], readings: list[str]) -> dict[str, Any]:
    """Verdicts per reading per trace, under the instrument and under its controls."""
    per: dict[str, dict[str, Any]] = {}
    controls: dict[str, dict[str, dict[str, int]]] = defaultdict(dict)
    for reading in readings:
        traces: dict[str, dict[str, Any]] = {}
        for trace, trace_rows in sorted(_by_trace(rows).items()):
            live = [r for r in trace_rows if r["name"] == reading
                    and r["mutation"] == "none" and r["correspondence_rule"] == "masked"]
            if not live:
                continue
            decided = sum(r["value_coverage"]["tested"] for r in live)
            refuted = sum(r["value"].get("REFUTED", 0) for r in live)
            supported = sum(r["value"].get("SUPPORTED", 0) for r in live)
            traces[trace] = {
                "splits": sorted({r["split"] for r in live}),
                "modes": sorted({r["applicability"] for r in live}),
                "decided": decided, "supported": supported, "refuted": refuted,
                "reached": decided > 0,
                "landing": _merge_landing(live),
            }
        reached = [t for t in traces.values() if t["reached"]]
        if not reached:
            status = NOT_REACHED
        elif all(t["refuted"] for t in reached):
            status = REFUTED_EVERYWHERE
        elif any(t["refuted"] for t in reached):
            status = REFUTED_SOMEWHERE
        else:
            status = UNREFUTED
        per[reading] = {"status": status, "traces": traces}
        for trace, trace_rows in sorted(_by_trace(rows).items()):
            for r in trace_rows:
                if r["name"] != reading:
                    continue
                key = f"{r['correspondence_rule']}/{r['mutation']}"
                bucket = controls[reading].setdefault(key, {"decided": 0, "refuted": 0})
                bucket["decided"] += r["value_coverage"]["tested"]
                bucket["refuted"] += r["value"].get("REFUTED", 0)
    return {"basis": PROBE, "readings": per,
            "controls": {k: dict(sorted(v.items())) for k, v in sorted(controls.items())},
            "predictive_classes": _classes(rows)}


def _by_trace(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        out[row["trace"]].append(row)
    return out


def _merge_landing(rows: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        for verdict, where in row["value_landing"].items():
            for place, count in where.items():
                out.setdefault(verdict, {}).setdefault(place, 0)
                out[verdict][place] += count
    return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}


def _classes(rows: list[dict]) -> list[dict[str, Any]]:
    """Readings that made exactly the same claims and got exactly the same answers.

    Grouped per trace, split, applicability and correspondence rule, because an equivalence
    that only holds under one setting of the instrument is not the same fact as one that
    holds under all of them.  A reading that made no testable claim is listed as untested
    rather than as a class of its own.
    """
    groups: dict[tuple, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    untested: dict[tuple, list[str]] = defaultdict(list)
    for row in rows:
        key = (row["trace"], row["split"], row["applicability"], row["correspondence_rule"],
               row["mutation"])
        if row["predictions_signed"]:
            groups[key][row["prediction_signature_digest"]].append(row["name"])
        else:
            untested[key].append(row["name"])
    out = []
    for key, by_digest in sorted(groups.items()):
        out.append({"trace": key[0], "split": key[1], "applicability": key[2],
                    "correspondence_rule": key[3], "mutation": key[4],
                    "classes": [sorted(v) for v in by_digest.values()],
                    "untested": sorted(untested.get(key, []))})
    return out


def build(app: str, consequence: list[Path]) -> dict[str, Any]:
    report = json.loads((ROOT / f"docs/data/v4/frontier_{app}.json").read_text())
    rows: list[dict] = []
    for path in consequence:
        trace = path.stem.replace(f"consequence_", "")
        for row in json.loads(path.read_text()):
            rows.append({**row, "trace": trace})
    readings = sorted({row["name"] for row in rows}) or [r["name"] for r in report["survivors"]]
    return {"application": app,
            "structural": structural(report),
            "retrospective": retrospective(report),
            "prospective": prospective(rows, readings)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--consequence", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build(args.app, args.consequence)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(f"== {payload['application']}")
    print(f"  structural     {payload['structural']['outcome']}: "
          f"{payload['structural']['survivors']}")
    print(f"  retrospective  {payload['retrospective']['outcome']}  "
          f"{payload['retrospective']['identification']}")
    for name, row in sorted(payload["prospective"]["readings"].items()):
        print(f"  prospective    {name[:34]:36} {row['status']}")
        for trace, t in sorted(row["traces"].items()):
            print(f"       {trace:22} decided {t['decided']:5d} supported {t['supported']:5d} "
                  f"refuted {t['refuted']:5d}  {t['landing']}")
    for name, row in sorted(payload["prospective"]["controls"].items()):
        print(f"  controls       {name[:34]:36} {row}")


if __name__ == "__main__":
    main()
