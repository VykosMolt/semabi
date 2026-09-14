"""Generate the candidate readings from the source history alone.

The source proposes an incumbent, controls for promoted leaves, and at most one alternative
per family. The transfer and holdout histories are not passed in and cannot influence the
set. The freeze script is the caller; loading a manifest never runs this.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

from semabi.compiler.compile_v4 import build_hypotheses
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import pinned as v4_pinned, promote
from semabi.compiler.v4 import search as v4_search
from semabi.compiler.v4.identity import family_key, family_readings


MAX_CANDIDATES = 8


def _refuted(refuted: Mapping[str, set[str | None]], family: str,
             key_slot: str | None) -> bool:
    """Whether an exact SOURCE refutation covers one generated family/key claim."""
    return key_slot in refuted.get(family, set())


def _better_discriminating(result) -> dict[str, object]:
    """Per family, the alternative whose discrimination beats the chosen key's.

    The incumbent is what the objective preferred; discrimination counts how often the named
    value actually tells co-present instances apart. Where the two disagree, the more
    discriminating key is a real rival. ``None`` means no discrimination evidence at all, and
    is never an improvement in either direction.
    """
    out: dict[str, object] = {}
    for family, templates in sorted(result.families.items()):
        chosen = result.chosen[templates[0]]
        incumbent_discrimination = chosen.evidence.discrimination
        if incumbent_discrimination is None:
            continue
        best = None
        for alternative in result.readings.get(templates[0], []):
            if alternative.key_slot == chosen.key_slot or alternative.status == "REFUTED":
                continue
            if alternative.status not in ("SUPPORTED", "NO_IDENTITY"):
                continue
            value = alternative.evidence.discrimination
            if value is None or value <= incumbent_discrimination:
                continue
            if best is None or value > best.evidence.discrimination:
                best = alternative
        if best is not None:
            out[family] = best
    return out


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
    records: list[dict] | None = None,
):
    """Every reading the source history makes plausible, including the one it prefers.

    Generating alternatives is the source's job; deciding between them is not.
    """
    H, G = build_hypotheses(source, log)
    if records is not None:
        # a refutation binds by the values its slot held, not by its name; one whose slot
        # no longer holds them, or never said, cannot be frozen
        stale = v4_search.stale_refutations(records, H)
        if stale:
            raise ValueError("retained refutations do not bind to this history: "
                             + "; ".join(f"{s['family'][:40]}={s['key_slot']} {s['state']}"
                                         f" held={s.get('held')} holds={s.get('holds')}" for s in stale)
                             + " -- re-derive the experiment before freezing")
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

    # Readings that promote a repeated leaf come first: the objective declines exactly these,
    # which is why the comparison exists, so a cap must not be what drops them.
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
        best = next((r for r in family_readings([unit], reload_pairs, view_of, allow_prose=True, spoken=v4_search.spoken_values(log))
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

    # One reading a single edit cannot reach: re-key every family the source says is
    # improvable, at once. One family at a time gives two rivals that disagree everywhere and
    # cannot be ordered, while the reading that fixes both is never proposed.
    improvable = _better_discriminating(result)
    if len(improvable) > 1:
        joint = incumbent
        for family, alternative in sorted(improvable.items()):
            family_reading = v4_pinned.FamilyReading(
                family, alternative.key_slot, alternative.status,
                alternative.evidence.discrimination,
            )
            joint = joint.variant(family, family_reading, "")
        name = f"joint discrimination x{len(improvable)}"
        joint.name = name
        already = {c.fingerprint() for c in candidates}
        refuted_here = any(_refuted(exact_refuted, family, alternative.key_slot)
                           for family, alternative in improvable.items())
        if joint.fingerprint() not in already and not refuted_here:
            candidates.append(joint)
            for family, alternative in sorted(improvable.items()):
                notes.append(_alternative_note(name, family, alternative))
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


# Public name for freeze scripts; the private one stays for callers that reproduce the
# previous runner exactly.
source_candidates = _source_candidates
