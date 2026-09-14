"""Turn an undecided identity reading into an experiment the application can settle.

Both readings of a page are consistent with the page. What separates them is what happens
when the value one of them calls the identity is changed: if the slot names the object,
editing it replaces one object with another; if it does not, the instance stays itself and
carries a new value.

So the probe is generic: find an instance where the contested value is rendered by a control
the learner can operate, change it, and rescore both readings on the longer trace.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

EDITABLE = ("textbox", "combobox", "checkbox")


@dataclass
class Probe:
    family: str
    contested_slot: str
    sig: str                       # observation the probe must be performed in
    node: int                      # node to operate
    kind: str                      # type | select | click
    text: str | None
    rationale: str
    predictions: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {"family": self.family, "contested_slot": self.contested_slot, "sig": self.sig,
                "node": self.node, "kind": self.kind, "text": self.text,
                "rationale": self.rationale, "predictions": self.predictions}


def _contested(question) -> str | None:
    """The slot one reading calls identity and the other does not."""
    left = set(question.left.slots)
    right = set(question.right.slots)
    only = (left - right) or (right - left)
    return sorted(only)[0] if only else None


def derive(question, H, G, typed_tokens: list[str] | None = None) -> Probe | None:
    """A probe for one open question, or None when nothing in the page can settle it."""
    slot = _contested(question)
    if slot is None:
        return None
    templates = [t for t in H.units if t == question.template] or \
                [t for t in H.units if t.startswith(question.template.split("[")[0])]
    from semabi.compiler.v4.search import family_templates
    templates = family_templates(H, question.template) or templates
    typed_tokens = typed_tokens or []

    best: Probe | None = None
    for template in templates:
        unit = H.units.get(template)
        if unit is None:
            continue
        for instance in unit.instances:
            node_index = instance.slot_nodes.get(slot)
            if node_index is None:
                continue
            obs = G.obs.get(instance.sig)
            if obs is None or node_index >= len(obs.nodes):
                continue
            node = obs.node(node_index)
            # the contested value may be static text, so look at the node and its children
            # for the control that actually carries it
            for candidate in [node] + [obs.node(c) for c in obs.children(node_index)]:
                if candidate.role not in EDITABLE:
                    continue
                if candidate.role == "combobox":
                    options = [o for o in (candidate.options or []) if o != candidate.value]
                    if not options:
                        continue
                    probe = Probe(question.template, slot, instance.sig, candidate.i, "select",
                                  options[0], "change the contested value on one instance")
                elif candidate.role == "checkbox":
                    probe = Probe(question.template, slot, instance.sig, candidate.i, "click",
                                  None, "toggle the contested value on one instance")
                else:
                    fresh = f"probe{len(typed_tokens) + 1}"
                    probe = Probe(question.template, slot, instance.sig, candidate.i, "type",
                                  fresh, "change the contested value on one instance")
                probe.predictions = {
                    (question.left.key_slot or "no-identity"):
                        ("this instance is replaced by a different object"
                         if slot in question.left.slots else
                         "this instance keeps its identity and carries a new value"),
                    (question.right.key_slot or "no-identity"):
                        ("this instance is replaced by a different object"
                         if slot in question.right.slots else
                         "this instance keeps its identity and carries a new value"),
                }
                if best is None:
                    best = probe
                if probe.kind == "type":
                    return probe          # a free value is the cleanest change
    return best


def locate(question, H, G, obs, sig: str, typed_tokens: list[str] | None = None) -> Probe | None:
    """Find the contested control in an observation the browser is actually looking at.

    A probe needs a situation, not one exact page: the contested slot reappears whenever the
    family is rendered, and any instance of it will do.
    """
    from semabi.compiler.v4.identity import family_key
    slot = _contested(question)
    if slot is None:
        return None
    if sig not in G.obs:
        G.add(sig, obs)
    from semabi.compiler.v4.search import family_templates
    templates = set(family_templates(H, question.template))
    typed_tokens = typed_tokens or []
    for instance in H.parse_units(sig):
        if instance.template not in templates:
            continue
        node_index = instance.slot_nodes.get(slot)
        if node_index is None or node_index >= len(obs.nodes):
            continue
        node = obs.node(node_index)
        for candidate in [node] + [obs.node(c) for c in obs.children(node_index)]:
            if candidate.role not in EDITABLE:
                continue
            if candidate.role == "combobox":
                options = [o for o in (candidate.options or []) if o != candidate.value]
                if not options:
                    continue
                return Probe(question.template, slot, sig, candidate.i, "select", options[0],
                             "change what this instance shows, then ask whether it persisted")
            if candidate.role == "checkbox":
                return Probe(question.template, slot, sig, candidate.i, "click", None,
                             "toggle what this instance shows, then ask whether it persisted")
            return Probe(question.template, slot, sig, candidate.i, "type",
                         f"probe{len(typed_tokens) + 1}",
                         "change what this instance shows, then ask whether it persisted")
    return None


# --------------------------------------------------------------------------
# probes aimed at missing evidence rather than at a disagreement
#
# An ambiguity can survive because the observation that would separate the two readings was
# never made. The remedy is to go and make it. What can be collected this way is limited: a
# second instance cannot be conjured where the application renders one, and saying so beats
# guessing.

ACQUIRABLE = {
    "NO_RELOAD_WITNESS": "reach a page that renders the family and reload it",
    "NO_CROSS_VIEW_RECURRENCE": "look for the family in the other views this page offers",
}


@dataclass
class Acquisition:
    """A bounded plan to collect one named kind of missing evidence."""
    family: str
    missing: str
    plan: str
    max_primitives: int = 8

    def to_json(self) -> dict[str, Any]:
        return {"family": self.family, "missing": self.missing, "plan": self.plan,
                "max_primitives": self.max_primitives}


def acquisition_for(family: str, missing: list[str]) -> Acquisition | None:
    """The cheapest missing observation this environment can be asked for, if any."""
    for code in missing:
        if code in ACQUIRABLE:
            return Acquisition(family, code, ACQUIRABLE[code])
    return None


def renders_family(H, G, obs, sig: str, family: str) -> bool:
    """Is this family on screen right now?"""
    from semabi.compiler.v4.search import family_templates
    if sig not in G.obs:
        G.add(sig, obs)
    members = set(family_templates(H, family))
    return any(i.template in members for i in H.parse_units(sig))
