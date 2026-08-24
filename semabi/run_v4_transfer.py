"""SOURCE -> TRANSFER -> HOLDOUT: choose a reading with evidence it was not fitted to.

Compiler side.  Hidden state is never read here; the evaluator looks at the result
afterwards and says whether the reading that transported was also the right one.

The three roles are kept apart in code because they are different kinds of evidence and
collapsing them is how a fit gets mistaken for a prediction:

* SOURCE may generate readings and reject obviously bad ones locally;
* TRANSFER may compare frozen source readings and refute them, and may never afterwards be
  called independent validation;
* HOLDOUT may confirm or contradict the reading that transfer selected, and takes no part
  in selecting it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.compile_v4 import build_hypotheses, compile_v4
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import objective, pinned as v4_pinned, promote, sufficiency, transfer
from semabi.compiler.v4 import search as v4_search
from semabi.compiler.v4.identity import family_key, family_readings

MAX_CANDIDATES = 6


def _source_candidates(source: Path, log: EvidenceLog, max_candidates: int = MAX_CANDIDATES):
    """Every reading the source history makes plausible, frozen, including the one it
    prefers.  Generating alternatives is the source's job; deciding between them is not."""
    H, G = build_hypotheses(source, log)
    result = v4_search.search(H, G, log, log_fn=lambda _m: None, run_dir=source)
    incumbent = v4_pinned.from_search(result, source, "source_choice")
    candidates = [incumbent]
    notes = []

    # Readings that promote a repeated leaf to an object of its own come first.  The local
    # objective declines exactly these, which is the reason this whole comparison exists, so
    # they must not be the ones a candidate cap truncates.
    reload_pairs = v4_search._reload_pairs(log)
    view_of = v4_search._view_of(H)
    for leaf in promote.candidates(H, G):
        leaf_family = family_key(leaf)
        if leaf_family in incumbent.promoted_families:
            continue
        promoted_H, _ = build_hypotheses(source, log, {leaf})
        unit = promoted_H.units.get(leaf)
        if unit is None:
            continue
        best = next((r for r in family_readings([unit], reload_pairs, view_of, allow_prose=True)
                     if r.is_identity and r.status == "SUPPORTED"), None)
        if best is None:
            continue
        name = f"promote {leaf_family[:22]}={best.key_slot}"
        candidates.append(incumbent.with_promotion(leaf_family, best.key_slot, name))
        notes.append({"family": leaf_family, "promotion": best.key_slot,
                      "discrimination": best.evidence.discrimination,
                      "copresent_pairs": best.evidence.copresent_pairs})
        if len(candidates) >= max_candidates:
            return result, candidates[:max_candidates], notes, H, G

    for family, templates in sorted(result.families.items()):
        chosen = result.chosen[templates[0]]
        for alternative in result.readings.get(templates[0], []):
            if alternative.key_slot == chosen.key_slot or alternative.status == "REFUTED":
                continue
            if alternative.status not in ("SUPPORTED", "NO_IDENTITY"):
                continue
            name = f"{family[:24]}={alternative.key_slot}"
            candidates.append(incumbent.variant(family, alternative.key_slot, name))
            notes.append({"family": family, "alternative": alternative.key_slot,
                          "status": alternative.status,
                          "discrimination": alternative.evidence.discrimination})
            break            # one alternative per family keeps the comparison small
        if len(candidates) >= max_candidates:
            break
    return result, candidates[:max_candidates], notes, H, G


def _evidence(run: Path, reading: v4_pinned.PinnedReading, min_support: int) -> transfer.TransferEvidence:
    compiled = compile_v4(run, min_support=min_support, write_diagnostics=False, pinned=reading)
    behaviour = objective.evaluate(compiled.abstractor, compiled.log, None)
    keys = {f: r.key_slot for f, r in sorted(reading.families.items())}
    # the frozen reading's identity claims, put to this history: does each named value still
    # separate the instances it names?  Nothing is re-chosen; the claim is only tested.
    separated = v4_pinned.separation(compiled.hypotheses, reading)
    return transfer.from_behaviour(reading.name, behaviour, compiled.transport, keys, separated)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--transfer", required=True)
    ap.add_argument("--holdout")
    ap.add_argument("--min-support", type=int, default=2)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    source, transfer_run = Path(a.source), Path(a.transfer)
    holdout = Path(a.holdout) if a.holdout else None

    log = EvidenceLog(source)
    result, candidates, notes, H, G = _source_candidates(source, log)
    report: dict = {
        "roles": {"SOURCE": str(source), "TRANSFER": str(transfer_run),
                  "HOLDOUT": str(holdout) if holdout else None},
        "role_semantics": {
            "SOURCE": "generated the readings and rejected some locally; not validation",
            "TRANSFER": "compared frozen readings and may refute them; not validation",
            "HOLDOUT": "took no part in selection; the only evidence that validates"},
        "source": {"local_final": result.final.to_json(),
                   "families": {f: len(t) for f, t in sorted(result.families.items())},
                   "open_questions": [q.to_json() for q in result.open_questions],
                   "alternatives_generated": notes},
        "candidates": [{"name": c.name, "fingerprint": c.fingerprint(),
                        "promoted": c.promoted_families,
                        "reading": c.to_json()} for c in candidates],
    }

    if len(candidates) < 2:
        report["outcome"] = "NO_COMPETING_READING"
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(json.dumps(report, indent=1))
        print(json.dumps({"outcome": report["outcome"]}, indent=1))
        return

    evidence = {c.name: _evidence(transfer_run, c, a.min_support) for c in candidates}
    report["transfer"] = {name: ev.to_json() for name, ev in evidence.items()}

    incumbent = candidates[0]
    decisions = []
    for candidate in candidates[1:]:
        decision = transfer.decide(evidence[incumbent.name], evidence[candidate.name])
        decisions.append({"left": incumbent.name, "right": candidate.name, **decision.to_json()})
        if decision.outcome == "RIGHT":
            incumbent = candidate
    report["transfer_decisions"] = decisions
    report["selected"] = {"name": incumbent.name, "fingerprint": incumbent.fingerprint(),
                          "reading": incumbent.to_json()}
    report["selection_changed_the_source_choice"] = incumbent.name != candidates[0].name

    # what the transfer history could not answer, and what it would have taken
    targeted = sufficiency.targeted_families(H, log)
    unresolved = []
    for question in result.open_questions:
        templates = result.families.get(question.template, [])
        reading = result.chosen.get(templates[0]) if templates else None
        if reading is None:
            continue
        present = question.template in {f for f in evidence[incumbent.name].transport.get("applied", {})}
        unresolved.append(sufficiency.assess(reading, targeted, present).to_json())
    report["evidence_sufficiency"] = unresolved

    if holdout is not None:
        runner_up = next((c for c in candidates if c.name != incumbent.name), None)
        held = {incumbent.name: _evidence(holdout, incumbent, a.min_support)}
        if runner_up is not None:
            held[runner_up.name] = _evidence(holdout, runner_up, a.min_support)
        report["holdout"] = {name: ev.to_json() for name, ev in held.items()}
        chosen_ev = held[incumbent.name]
        if runner_up is not None:
            verdict = transfer.decide(chosen_ev, held[runner_up.name])
            report["holdout_differential"] = verdict.to_json()
        if chosen_ev.applicability == 0.0:
            report["holdout_outcome"] = "INCONCLUSIVE_NOT_APPLICABLE"
        elif not chosen_ev.makes_predictions:
            report["holdout_outcome"] = "INCONCLUSIVE_NO_PREDICTIONS"
        elif chosen_ev.errors == 0 and chosen_ev.explained > 0:
            report["holdout_outcome"] = "CONFIRMED"
        elif chosen_ev.explained > 0:
            report["holdout_outcome"] = "PARTIALLY_CONTRADICTED"
        else:
            report["holdout_outcome"] = "CONTRADICTED"

    report["outcome"] = "SELECTED"
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(report, indent=1))
    print(json.dumps({
        "candidates": [c.name for c in candidates],
        "decisions": [{k: d[k] for k in ("left", "right", "outcome", "reason")} for d in decisions],
        "selected": incumbent.name,
        "changed": report["selection_changed_the_source_choice"],
        "holdout_outcome": report.get("holdout_outcome"),
    }, indent=1))


if __name__ == "__main__":
    main()
