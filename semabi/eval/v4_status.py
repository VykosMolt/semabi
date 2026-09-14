"""Three different facts about a reading, reported separately instead of merged into one.

* Structural -- which readings the candidate space still contains after transfer.
* Retrospective -- which the already-observed history contradicted or agreed with.
* Prospective -- whether rules fitted on a prefix correctly predicted a held-out suffix.

All three are measured under single clicks on the application's own controls, checked one
step ahead; an equivalence found here holds only for that probe.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
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


def prospective(rows: list[dict], readings: list[str],
                baseline: dict[str, Any] | None = None) -> dict[str, Any]:
    """Verdicts per reading per trace, under the instrument and under its controls."""
    baseline = baseline or {}
    per: dict[str, dict[str, Any]] = {}
    controls: dict[str, dict[str, dict[str, int]]] = defaultdict(dict)
    for reading in readings:
        traces: dict[str, dict[str, Any]] = {}
        for trace, trace_rows in sorted(_by_trace(rows).items()):
            live = [r for r in trace_rows if r["name"] == reading
                    and r["mutation"] == "none" and r["correspondence_rule"] == "masked"]
            if not live:
                continue
            # Both page checks count: a reading whose model is only about objects
            # appearing/disappearing makes no value claim, so the value column alone
            # would wrongly show it as untested.
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
                "existence_landing": _merge_landing(live, "existence_landing"),
                # How well the reading's rules pin down the object the action affected;
                # a reading that can't relate the click to the object reads POSSIBLE
                # everywhere, which looks inconclusive unless shown beside this.
                "binding": _merge_binding(live),
                # Whether the rules are well-formed: an effect on an object the pre-state
                # never pins down can be neither supported nor refuted usefully.
                "schema": _merge_schema(live),
                "removals_would_be_right_anyway": baseline.get(reading),
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
                               "nothing to a claim that an object goes away; that check's "
                               "discrimination is the base rate reported beside each reading, "
                               "measured by semabi/eval/v4_existence_baseline.py over every "
                               "object in every held-out pre-state with no rule involved -- "
                               "0.99 on harbour and 0.84 on the landing board, where a removal "
                               "claim is therefore worth almost nothing, against 0.21-0.39 on "
                               "the vet clinic, where it is worth something"),
            "controls": {k: dict(sorted(v.items())) for k, v in sorted(controls.items())},
            "predictive_classes": _classes(rows)}


def _by_trace(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        out[row["trace"]].append(row)
    return out


def _merge_binding(rows: list[dict]) -> dict[str, Any]:
    status: Counter = Counter()
    largest = 0
    for row in rows:
        for key, count in row.get("binding", {}).get("status", {}).items():
            status[key] += count
        largest = max(largest, row.get("binding", {}).get("largest", 0))
    total = sum(status.values())
    unique = status.get("UNIQUE", 0)
    return {"status": dict(sorted(status.items())), "largest_assignment_set": largest,
            "determined": f"{unique}/{total}" if total else "0/0"}


def _merge_schema(rows: list[dict]) -> dict[str, Any]:
    """How the operators divide, pooled over the rows this reading was scored on.

    Pooled by kind, not by operator identity, since each fit numbers its own rules.
    """
    kinds: Counter = Counter()
    ill = 0
    for row in rows:
        for kind, count in row.get("schema", {}).get("kinds", {}).items():
            kinds[kind] += count
        ill += len(row.get("schema", {}).get("ill_formed", ()))
    return {"operator_kinds": dict(sorted(kinds.items())),
            "effects_on_an_object_the_state_does_not_pin_down": ill}


def _merge_landing(rows: list[dict], field: str = "value_landing") -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        for verdict, where in (row.get(field) or {}).items():
            for place, count in where.items():
                out.setdefault(verdict, {}).setdefault(place, 0)
                out[verdict][place] += count
    return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}


def _classes(rows: list[dict]) -> list[dict[str, Any]]:
    """Readings that made exactly the same claims and got exactly the same answers.

    Grouped per trace, split, applicability and correspondence rule, since an equivalence
    under one setting is not the same fact as one under all of them. A reading with no
    testable claim is listed as untested, not as a class of its own.
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

    A refutation alone doesn't eliminate: an under-specified rule can be repaired by a
    prefix-chosen condition, which is ordinary learning, not evidence against the reading.
    A reading is removed only when it was refuted everywhere it was reached and no such
    repair, in its own vocabulary, removes the refutations without losing its successes.
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
    # A contradiction every candidate shares is about the shared machinery, not the choice
    # between readings, so elimination is relative to the retained set: a reading goes only
    # when some other reading survives the same test.
    reached = {r for r in readings
               if any(row["value_coverage"]["tested"]
                      + row.get("existence_coverage", {}).get("tested", 0)
                      for row in rows if row["name"] == r and row["mutation"] == "none"
                      and row["correspondence_rule"] == "masked")}
    # The surviving reading has to have said something, or a reading with no testable
    # claim would count as surviving and license removing one that took a real risk.
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


def build(app: str, consequence: list[Path], conditional: list[Path],
          existence_baseline: list[Path] = ()) -> dict[str, Any]:
    frontier = ROOT / f"docs/data/v4/frontier_{app}.json"
    # An application the frontier never ran on still has a prospective status, since that
    # one does not depend on the comparison having been made.
    report = json.loads(frontier.read_text()) if frontier.exists() else None
    rows: list[dict] = []
    for path in consequence:
        trace = path.stem.replace("consequence_", "")
        for row in json.loads(path.read_text()):
            rows.append({**row, "trace": trace})
    cond: list[dict] = []
    for path in conditional:
        cond.extend(json.loads(path.read_text()))
    # How often an object stops being rendered regardless of any rule; a removal claim
    # is only worth the amount by which it beats this base rate.
    base: dict[str, Any] = {}
    for path in existence_baseline:
        for row in json.loads(path.read_text()):
            base.setdefault(row["reading"], {})[row["split"]] = row["base_rate_gone"]
    readings = sorted({row["name"] for row in rows}) or (
        [r["name"] for r in report["survivors"]] if report else [])
    prospect = prospective(rows, readings, base)
    selected = (structural(report) if report else NO_FRONTIER).get("selected")
    identification = None
    if selected is not None:
        status = prospect["readings"].get(selected, {}).get("status")
        # Viable and identified are different facts: a reading that survived only because
        # it never said anything testable has not actually been identified.
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
    parser.add_argument("--existence-baseline", type=Path, action="append",
                        default=[], dest="existence_baseline")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = build(args.app, args.consequence, args.conditional,
                    args.existence_baseline)
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
                  f"refuted {t['refuted']:5d}  bindings {t['binding']['status']} "
                  f"determined {t['binding']['determined']} max {t['binding']['largest_assignment_set']}")
            if t.get("removals_would_be_right_anyway"):
                print(f"       {'':22} a removal claim is right anyway "
                      f"{t['removals_would_be_right_anyway']} of the time")
    for name, row in sorted(payload["prospective"]["controls"].items()):
        print(f"  controls       {name[:34]:36} {row}")
    elim = payload["prospective_elimination"]
    for name, why in sorted(elim["explanations"].items()):
        print(f"  refutations    {name[:34]:36} {why}")
    print(f"  ELIMINATED     {elim['removed']}")
    print(f"  RETAINED       {elim['retained']}")


if __name__ == "__main__":
    main()
