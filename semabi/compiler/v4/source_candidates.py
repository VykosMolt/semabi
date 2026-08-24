"""SOURCE-only generation of the bounded V4 candidate set.

This is the source-side mechanism formerly kept in ``run_v4_transfer``.  It is
deliberately a straight copy of that mechanism: the source history generates an
incumbent, promoted-leaf controls, and at most one ordinary alternative per family.
The transfer and holdout histories are not passed here and cannot influence the
candidate set.

The freeze script is the intended caller.  Manifest loading never imports this module
and therefore never runs search as a side effect.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

from semabi.compiler.compile_v4 import build_hypotheses
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import pinned as v4_pinned, promote
from semabi.compiler.v4 import search as v4_search
from semabi.compiler.v4.identity import family_key, family_readings


MAX_CANDIDATES = 6


def _refuted(refuted: Mapping[str, set[str | None]], family: str,
             key_slot: str | None) -> bool:
    """Whether an exact SOURCE refutation covers one generated family/key claim."""
    return key_slot in refuted.get(family, set())


def _alternative_note(name: str, family: str, reading, *, promotion: bool = False):
    """Serialize the exact generated candidate metadata used by SOURCE custody."""
    row = {
        "candidate": name,
        "family": family,
        "status": reading.status,
        "discrimination": reading.evidence.discrimination,
    }
    if promotion:
        row["promotion"] = reading.key_slot
    else:
        row["alternative"] = reading.key_slot
    return row


def _source_candidates(
    source: Path,
    log: EvidenceLog,
    max_candidates: int = MAX_CANDIDATES,
    *,
    refuted: Mapping[str, set[str | None]] | None = None,
):
    """Every reading the source history makes plausible, frozen, including the one it
    prefers.  Generating alternatives is the source's job; deciding between them is not.
    """
    H, G = build_hypotheses(source, log)
    result = v4_search.search(
        H, G, log, log_fn=lambda _m: None,
        run_dir=None if refuted is not None else source,
        refuted=None if refuted is None else {k: set(v) for k, v in refuted.items()},
    )
    exact_refuted = (
        {family: set(keys) for family, keys in refuted.items()}
        if refuted is not None
        else {family: set(keys) for family, keys in v4_search.read_refutations(source).items()}
    )
    incumbent = v4_pinned.from_search(
        result, source, "source_choice", refuted=exact_refuted
    )
    candidates = [incumbent]
    notes = []
    if max_candidates <= len(candidates):
        return result, candidates[:max_candidates], notes, H, G

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
        if _refuted(exact_refuted, leaf_family, best.key_slot):
            continue
        family_reading = v4_pinned.FamilyReading(
            leaf_family, best.key_slot, best.status, best.evidence.discrimination
        )
        candidates.append(incumbent.with_promotion(leaf_family, family_reading, name))
        notes.append(_alternative_note(name, leaf_family, best, promotion=True))
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
            if _refuted(exact_refuted, family, alternative.key_slot):
                continue
            family_reading = v4_pinned.FamilyReading(
                family, alternative.key_slot, alternative.status,
                alternative.evidence.discrimination,
            )
            candidates.append(incumbent.variant(family, family_reading, name))
            notes.append(_alternative_note(name, family, alternative))
            break            # one alternative per family keeps the comparison small
        if len(candidates) >= max_candidates:
            break
    return result, candidates[:max_candidates], notes, H, G


# A public spelling is useful to freeze scripts and keeps the historical private name
# available to callers that reproduce the previous runner exactly.
source_candidates = _source_candidates
