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

from semabi.compiler.v4.conditional import CLEAN, CONTRADICTED, explain

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
            # Both page checks count.  A reading whose whole action-effect model is about
            # objects appearing and going away makes no value claim, and reading only the
            # value column would report it as untested when it was tested and passed.
            decided = sum(r["value_coverage"]["tested"]
                          + r.get("existence_coverage", {}).get("tested", 0) for r in live)
            refuted = sum(r["value"].get("REFUTED", 0)
                          + r.get("existence", {}).get("REFUTED", 0) for r in live)
            supported = sum(r["value"].get("SUPPORTED", 0)
                            + r.get("existence", {}).get("SUPPORTED", 0) for r in live)
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
                bucket["decided"] += (r["value_coverage"]["tested"]
                                      + r.get("existence_coverage", {}).get("tested", 0))
                bucket["refuted"] += (r["value"].get("REFUTED", 0)
                                      + r.get("existence", {}).get("REFUTED", 0))
    return {"basis": PROBE, "readings": per,
            "control_caveat": ("the mutation controls rewrite a predicted literal, which does "
                               "nothing to a claim that an object goes away; the existence "
                               "check's discrimination is measured separately, by running it "
                               "over every object in every held-out pre-state"),
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


def elimination(rows: list[dict], conditional: list[dict], readings: list[str]) -> dict[str, Any]:
    """Which readings a held-out contradiction is entitled to remove, and which it is not.

    A refutation on its own does not eliminate: a rule the learner under-specified fails on
    held-out steps too, and repairing it is ordinary learning rather than evidence against the
    representation.  What eliminates is a contradiction the reading cannot repair *in its own
    vocabulary* with a condition chosen on the prefix -- because that is the case where the
    thing the effect depends on is something the reading cannot say.

    Nothing here is a score and nothing is tuned.  A reading is removed when it was refuted on
    every history that reached it and no prefix-chosen literal over the objects its rules bind
    removes those refutations without also discarding the successes.

    Two of those repairs now happen inside fitting rather than here, and every candidate gets
    both: a precondition learned from the rule's own counterexamples, and the dropping of
    effect values the action does not determine -- which is what stops a reading being blamed
    for a memorised constant.  What this stage adds is the residual question, so a reading is
    only removed after the learner has already done what it can for it.
    """
    verdicts: dict[str, str] = {}
    for reading in readings:
        mine = [r for r in conditional if r["reading"] == reading]
        verdicts[reading] = explain(mine) if mine else "NOT_ANALYSED"
    refuted_everywhere = {
        reading for reading in readings
        if any(r["value"].get("REFUTED", 0) + r.get("existence", {}).get("REFUTED", 0)
               for r in rows if r["name"] == reading and r["mutation"] == "none"
               and r["correspondence_rule"] == "masked")}
    contradicted = {r for r in readings
                    if verdicts.get(r) == CONTRADICTED and r in refuted_everywhere}
    # A contradiction every candidate shares is evidence about the machinery they all use,
    # not about the choice between them.  Blend is the case: every reading there predicts a
    # counter's next value as the constant it took last time, so all of them are refuted the
    # same way by the same arithmetic, and removing them would empty the version space over a
    # failure none of them is responsible for.  Elimination is therefore relative to the
    # retained set -- a reading goes only when some other reading survives the same test.
    reached = {r for r in readings
               if any(row["value_coverage"]["tested"]
                      + row.get("existence_coverage", {}).get("tested", 0)
                      for row in rows if row["name"] == r and row["mutation"] == "none"
                      and row["correspondence_rule"] == "masked")}
    # The surviving reading has to have said something.  Without that, a reading that makes no
    # testable claim would count as surviving the test and license removing one that made
    # claims and got some of them wrong -- which is the vacuity pathology in a new place.
    survivor = [r for r in readings if r not in contradicted and r in reached
                and verdicts.get(r) not in (None, "NOT_ANALYSED")]
    removed = sorted(contradicted) if survivor else []
    return {"criterion": ("refuted on every history that reached it; no prefix-chosen literal "
                          "over the objects its rules bind removes those refutations without "
                          "discarding its successes; and some other candidate survives the "
                          "same test, so the contradiction is about this reading rather than "
                          "about the apparatus they share"),
            "explanations": dict(sorted(verdicts.items())),
            "contradicted": sorted(contradicted),
            "shared_by_every_candidate": bool(contradicted) and not survivor,
            "removed": removed,
            "retained": sorted(set(readings) - set(removed))}


NO_FRONTIER = {"basis": "no frontier was run on this application",
               "outcome": "NOT_RUN", "survivors": [], "selected": None,
               "classifications": {}, "identification": None,
               "classes_among_survivors": []}


def build(app: str, consequence: list[Path], conditional: list[Path]) -> dict[str, Any]:
    frontier = ROOT / f"docs/data/v4/frontier_{app}.json"
    # An application the frontier never ran on still has a prospective status, and it is the
    # one status that does not depend on the comparison having been made.
    report = json.loads(frontier.read_text()) if frontier.exists() else None
    rows: list[dict] = []
    for path in consequence:
        trace = path.stem.replace("consequence_", "")
        for row in json.loads(path.read_text()):
            rows.append({**row, "trace": trace})
    cond: list[dict] = []
    for path in conditional:
        cond.extend(json.loads(path.read_text()))
    readings = sorted({row["name"] for row in rows}) or (
        [r["name"] for r in report["survivors"]] if report else [])
    prospect = prospective(rows, readings)
    selected = (structural(report) if report else NO_FRONTIER).get("selected")
    identification = None
    if selected is not None:
        status = prospect["readings"].get(selected, {}).get("status")
        # Viable and identified are different facts.  A reading that survived because it never
        # said anything the evidence could contradict has not been identified by it, and the
        # difference needs no threshold: the instrument either decided something for it or it
        # decided nothing.
        identification = ("SELECTED_AND_MAKES_TESTABLE_CLAIMS" if status and status != NOT_REACHED
                          else "SELECTED_BUT_MAKES_NO_TESTABLE_CLAIM")
    return {"application": app,
            "identification": identification,
            "structural": structural(report) if report else NO_FRONTIER,
            "retrospective": retrospective(report) if report else NO_FRONTIER,
            "prospective": prospect,
            "prospective_elimination": elimination(rows, cond, readings)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", required=True)
    parser.add_argument("--consequence", type=Path, action="append", default=[])
    parser.add_argument("--conditional", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build(args.app, args.consequence, args.conditional)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n")
    print(f"== {payload['application']}")
    print(f"  structural     {payload['structural']['outcome']}: "
          f"{payload['structural']['survivors']}")
    if payload["identification"]:
        print(f"  identification {payload['identification']}")
    print(f"  retrospective  {payload['retrospective']['outcome']}  "
          f"{payload['retrospective']['identification']}")
    for name, row in sorted(payload["prospective"]["readings"].items()):
        print(f"  prospective    {name[:34]:36} {row['status']}")
        for trace, t in sorted(row["traces"].items()):
            print(f"       {trace:22} decided {t['decided']:5d} supported {t['supported']:5d} "
                  f"refuted {t['refuted']:5d}  {t['landing']}")
    for name, row in sorted(payload["prospective"]["controls"].items()):
        print(f"  controls       {name[:34]:36} {row}")
    elim = payload["prospective_elimination"]
    for name, why in sorted(elim["explanations"].items()):
        print(f"  refutations    {name[:34]:36} {why}")
    print(f"  ELIMINATED     {elim['removed']}")
    print(f"  RETAINED       {elim['retained']}")


if __name__ == "__main__":
    main()
