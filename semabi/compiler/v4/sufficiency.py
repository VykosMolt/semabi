"""Why the evidence never separated two readings of a family.

Usually the answer is a particular observation that was never made: the family was never
rendered twice at once, nothing was reloaded while it was on screen, it never appeared in a
second view. Naming that turns "unresolved" into something an explorer can act on.

These are predicates over evidence that was or was not collected, not thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

MISSING = {
    "NO_COPRESENT_PEER": "the family never rendered two instances at the same time, so no "
                         "value has been given the chance to tell instances apart",
    "NO_RELOAD_WITNESS": "no reload happened while the family was on screen, so nothing "
                         "shows whether its values are facts or interface state",
    "NO_CROSS_VIEW_RECURRENCE": "the family appears in one view only, so no value has had "
                                "to be recognised again somewhere else",
    "NO_DISCRIMINATING_ACTION": "no action was ever aimed inside an instance of this "
                                "family, so nothing has tested what belongs to it",
    "NO_TRANSFERABLE_OCCURRENCE": "the family is not rendered in the transfer history, so "
                                  "the reading could not be tested there",
    "NO_ALTERNATIVE_VALUE": "the contested value takes one value only, so changing it has "
                            "never been possible",
}


@dataclass
class Sufficiency:
    family: str
    missing: list[str] = field(default_factory=list)
    have: list[str] = field(default_factory=list)

    @property
    def decidable(self) -> bool:
        return not self.missing

    @property
    def status(self) -> str:
        return "SUFFICIENT" if self.decidable else "INSUFFICIENT_EVIDENCE"

    def to_json(self) -> dict[str, Any]:
        return {"family": self.family, "status": self.status,
                "missing": [{"code": m, "means": MISSING[m]} for m in self.missing],
                "have": self.have}


def assess(reading, targeted_families: set[str] | None = None,
           present_in_transfer: bool | None = None) -> Sufficiency:
    """Which kinds of evidence this reading has, and which it has never been offered."""
    ev = reading.evidence
    out = Sufficiency(reading.template)
    (out.have if ev.copresent_pairs else out.missing).append(
        "NO_COPRESENT_PEER" if not ev.copresent_pairs else "COPRESENT_PEER")
    reload_seen = (ev.reload_kept + ev.reload_lost) > 0
    (out.have if reload_seen else out.missing).append(
        "RELOAD_WITNESS" if reload_seen else "NO_RELOAD_WITNESS")
    (out.have if ev.cross_view_values else out.missing).append(
        "CROSS_VIEW_RECURRENCE" if ev.cross_view_values else "NO_CROSS_VIEW_RECURRENCE")
    (out.have if ev.distinct_values > 1 else out.missing).append(
        "ALTERNATIVE_VALUE" if ev.distinct_values > 1 else "NO_ALTERNATIVE_VALUE")
    if targeted_families is not None:
        targeted = reading.template in targeted_families
        (out.have if targeted else out.missing).append(
            "DISCRIMINATING_ACTION" if targeted else "NO_DISCRIMINATING_ACTION")
    if present_in_transfer is not None and not present_in_transfer:
        out.missing.append("NO_TRANSFERABLE_OCCURRENCE")
    out.missing = [m for m in out.missing if m in MISSING]
    return out


def targeted_families(H, log) -> set[str]:
    """Families some action was aimed inside, which is what makes them testable at all."""
    from semabi.compiler.v4.identity import family_key
    out: set[str] = set()
    for step in log.steps:
        if step.action.target is None or step.action.kind not in ("click", "select", "type", "press"):
            continue
        sig = step.before
        if sig not in H.G.obs:
            continue
        obs = H.G.obs[sig]
        if step.action.target >= len(obs.nodes):
            continue
        for instance in H.parse_units(sig):
            if step.action.target in obs.subtree(instance.root):
                out.add(family_key(instance.template))
    return out
