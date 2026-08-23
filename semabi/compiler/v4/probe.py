"""Turning an undecided identity reading into an experiment the application can settle.

An identity reading is not falsified by a single observation -- both readings of a page are
consistent with the page.  What separates them is what happens when the value one of them
calls the identity is *changed*.  If a slot really names the object, editing it replaces
one object with another: everything else the instance shows would have to have been
recreated identically by coincidence.  If it does not name the object, the instance simply
carries a new value and stays itself.

So the probe is generic: find an instance where the contested value is rendered by a
control the learner can operate, change it, and let the behavioural objective rescore both
readings on the extended trace.  Nothing here inspects what kind of application this is; it
asks which rendered value is under dispute and whether that value can be operated.
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
    from semabi.compiler.v4.identity import family_key
    templates = [t for t in H.units if family_key(t) == question.template] or templates
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
            # the contested value itself may be static text; the control that carries it is
            # the one the learner can operate, so look at the node and its immediate children
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

    A probe needs a *situation*, not a page that hashes to a particular value: the same
    contested slot reappears whenever the family is rendered, and any instance of it will
    do. This is the whole of V4's multi-step reachability -- enough to get to the control a
    current hypothesis disagreement needs, and no more.
    """
    from semabi.compiler.v4.identity import family_key
    slot = _contested(question)
    if slot is None:
        return None
    if sig not in G.obs:
        G.add(sig, obs)
    templates = {t for t in H.units if family_key(t) == question.template}
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
