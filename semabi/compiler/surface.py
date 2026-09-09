"""Observation-local controls and regions, without persistent entity claims.

Local node numbers are valid only in their observation. Descriptors are learned
from rendered labels and visible control structure, then resolved afresh. A
region or repeated value is never implicitly a semantic reference.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from semabi.compiler.observation import Observation


SUBMIT_WORDS = re.compile(r"\b(save|submit|create|add|post|send|apply|confirm|publish)\b", re.I)

def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def argument_name(label: str) -> str:
    name = re.sub(r"[^\w]+", "_", label.casefold(), flags=re.UNICODE).strip("_")
    return name[:80] or "value"


@dataclass
class Surface:
    observation: Observation
    controls: dict[int, dict]
    forms: dict[int, dict]
    settled: bool = True

    def descriptor(self, node: int) -> dict:
        control = self.controls[node]
        return {key: control[key] for key in ("role", "label", "input_type")}

    def resolve(self, descriptor: dict, within: int | None = None) -> list[int]:
        members = set(self.observation.subtree(within)) if within is not None else None
        return [node for node, control in self.controls.items()
                if (members is None or node in members)
                and all(control.get(key) == value for key, value in descriptor.items()
                        if key in {"role", "label", "input_type"})]


def local_regions(observation: Observation) -> list[dict]:
    """Retain row/field/selection evidence even if every global key is unknown."""
    explicit = {"row", "listitem", "article"}
    repeated = set()
    for parent in observation.nodes:
        siblings = observation.children(parent.i)
        shapes: dict[tuple, list[int]] = {}
        for index in siblings:
            node = observation.node(index)
            shape = (node.role, tuple(observation.node(child).role
                                     for child in observation.children(index)))
            shapes.setdefault(shape, []).append(index)
        for shape, indices in shapes.items():
            if len(indices) > 1 and shape[0] in {"group", "row", "listitem", "article"}:
                repeated.update(indices)
    signature = observation.structural_signature()
    regions = []
    for node in observation.nodes:
        if node.role not in explicit and node.i not in repeated:
            continue
        fields = [{"node": index, "role": field.role, "label": field.name,
                   "value": field.value, "checked": field.checked,
                   "parent": field.parent}
                  for index in observation.subtree(node.i)
                  if (field := observation.node(index)).name or field.value is not None
                  or field.checked is not None]
        regions.append({"observation": signature, "root": node.i, "role": node.role,
                        "basis": "visible_row" if node.role in explicit else "repeated_siblings",
                        "fields": fields, "identity": "UNESTABLISHED", "references": []})
    return regions


def form_candidates(surface: Surface) -> list[dict]:
    """Propose visible form scopes. Proposal is not observed operation support."""
    obs = surface.observation
    candidates = []
    for submit, button in surface.controls.items():
        if button["role"] != "button" or not button["label"]:
            continue
        native_root = button.get("form")
        roots = [native_root] if native_root is not None else obs.ancestors(submit)
        for root in roots:
            members = set(obs.subtree(root))
            if any(control["input_type"] == "password" for node, control in surface.controls.items()
                   if node in members):
                break
            editable = [(node, control) for node, control in surface.controls.items()
                        if node in members and control["role"] in {"textbox", "combobox", "checkbox"}
                        and (native_root is not None or control.get("form") is None)
                        and not control.get("readonly") and not control.get("disabled")]
            if not editable:
                continue
            # Authentication belongs to connection setup, never a learned operation.
            if any(control["input_type"] == "password" for _, control in editable):
                break
            if any(control["input_type"] in {"file", "hidden", "range", "color"}
                   for _, control in editable):
                break
            if native_root is not None and not button.get("submit"):
                break
            buttons = [index for index in members if index in surface.controls
                       and surface.controls[index]["role"] == "button"]
            # An untyped page-wide button is not automatically a form submitter.
            if native_root is None and len(buttons) > 5:
                break
            fields = []
            names = set()
            for node, control in editable:
                label = control["label"]
                if not label:
                    descriptor = surface.descriptor(node)
                    uniquely_described = sum(surface.descriptor(other) == descriptor
                                             for other, _ in editable) == 1
                    label = "value" if uniquely_described else ""
                name = argument_name(label)
                if not label or name in names:
                    fields = []
                    break
                names.add(name)
                fields.append({"argument": name, "node": node,
                               "descriptor": surface.descriptor(node),
                               "required": control.get("required", False),
                               "role": control["role"], "input_type": control["input_type"],
                               "min": control.get("min"), "max": control.get("max"),
                               "max_length": control.get("max_length"),
                               "options": control.get("options", []),
                               "value": obs.node(node).value,
                               "checked": obs.node(node).checked})
            if fields:
                # A field may reveal its own controls as its value changes (for
                # example, an ordinary clear button). Their containing scope
                # owns exactly one field and excludes the submitter. Keep them
                # out of the form-level action context, while still checking
                # every field descriptor and value before submission.
                field_nodes = {node for node, _ in editable}
                auxiliary_buttons = set()
                for index in buttons:
                    if index == submit:
                        continue
                    for owner in obs.ancestors(index):
                        if owner == root:
                            break
                        owned = set(obs.subtree(owner))
                        if submit not in owned and len(owned & field_nodes) == 1:
                            auxiliary_buttons.add(index)
                            break
                semantic = {"submit": surface.descriptor(submit),
                            "context_controls": sorted([surface.descriptor(index) for index in buttons
                                                        if index != submit and index not in auxiliary_buttons], key=digest),
                            "fields": sorted([{key: field[key] for key in
                                               ("argument", "descriptor", "required", "role", "input_type",
                                                "min", "max", "max_length", "options")}
                                              for field in fields], key=lambda value: value["argument"])}
                candidates.append({"root": root, "submit_node": submit, "fields": fields,
                                   "descriptor": semantic, "signature": digest(semantic),
                                   "proposal_basis": "native_form" if native_root is not None else "local_control_group"})
            break
    unique = {}
    for candidate in candidates:
        unique[(candidate["root"], candidate["submit_node"])] = candidate
    return list(unique.values())


def matching_forms(surface: Surface, descriptor: dict) -> list[dict]:
    return [candidate for candidate in form_candidates(surface)
            if candidate["descriptor"] == descriptor]


def form_state(surface: Surface, root: int) -> dict | None:
    """Capture value controls by unique descriptors, including disabled defaults.

    Node numbers and DOM order are observation-local. Ambiguous descriptors
    cannot establish that the same field remained unchanged across observations.
    """
    states = {}
    for node in surface.observation.subtree(root):
        control = surface.controls.get(node, {})
        if control.get("role") not in {"textbox", "combobox", "checkbox", "radio"}:
            continue
        descriptor = surface.descriptor(node)
        key = digest(descriptor)
        if key in states:
            return None
        field = surface.observation.node(node)
        states[key] = {"descriptor": descriptor, "value": field.value,
                       "checked": field.checked,
                       **{name: control.get(name) for name in
                          ("disabled", "readonly", "required", "min", "max", "max_length", "options")}}
    return states


def editor_scopes(surface: Surface) -> set[int]:
    """Structural editor scopes, including disabled inputs and incomplete forms.

    Preview exclusion must not depend on whether a form is learnable at this
    moment: submission can disable its inputs without making its preview a record.
    """
    obs = surface.observation
    # A form can wrap a list solely for bulk checkbox actions. It is an
    # editor/preview scope only when it contains a rendered value editor.
    native_editors = {root for root in surface.forms if any(
        control["role"] in {"textbox", "combobox"} and control.get("input_type") != "search"
        for index, control in surface.controls.items() if index in obs.subtree(root))}
    scopes = set(native_editors)
    for index, button in surface.controls.items():
        if button["role"] != "button":
            continue
        if button.get("form") is not None:
            if button["form"] in native_editors:
                scopes.add(button["form"])
            continue
        for root in obs.ancestors(index):
            members = set(obs.subtree(root))
            controls = [control for node, control in surface.controls.items() if node in members]
            if any(control["role"] == "textbox" and control.get("form") is None for control in controls):
                if sum(control["role"] == "button" for control in controls) <= 5:
                    scopes.add(root)
                break
    submit_scopes = native_editors | {candidate["root"] for candidate in form_candidates(surface)
                                          if SUBMIT_WORDS.search(candidate["descriptor"]["submit"]["label"])}
    return {root for root in scopes if root in submit_scopes or not any(
            narrower != root and narrower in obs.subtree(root) for narrower in scopes)}


def relative_value_slots(surface: Surface, root: int, value: str) -> list[dict]:
    """Local field paths with distinct text and link-destination channels."""
    obs = surface.observation
    members = obs.subtree(root)
    exact = {node for node in members if obs.node(node).name.strip() == value.strip()}
    leaves = [(node, "text") for node in exact if not (set(obs.subtree(node)) - {node}) & exact]
    leaves.extend((node, "link_destination") for node in members
                  if surface.controls.get(node, {}).get("role") == "link"
                  and surface.controls[node].get("destination") == value)
    paths = []
    for node, channel in leaves:
        path = []
        while node != root:
            field = obs.node(node)
            siblings = [sibling for sibling in obs.children(field.parent)
                        if obs.node(sibling).role == field.role]
            path.append([field.role, siblings.index(node)])
            node = field.parent
        paths.append({"path": list(reversed(path)), "channel": channel})
    return sorted(paths, key=digest)


def visible_record_matches(surface: Surface, value: str) -> list[dict]:
    """Find complete visible values in record-like scopes, excluding form echoes.

    This is an observable read-back witness, not a claim of business identity.
    General group scopes require another visible field and a local action/link.
    """
    obs = surface.observation
    matches = []
    used = set()
    editors = editor_scopes(surface)
    for node in obs.nodes:
        if node.role in {"textbox", "combobox", "checkbox", "radio", "button"}:
            continue
        destination_match = (node.role == "link"
                             and surface.controls.get(node.i, {}).get("destination") == value)
        if node.name.strip() != value.strip() and not destination_match:
            continue
        if any(root in editors or
               (root in surface.controls and surface.controls[root]["role"] in
                {"textbox", "combobox"}) for root in [node.i, *obs.ancestors(node.i)]):
            continue
        ancestors = [node.i, *obs.ancestors(node.i)]
        explicit_roots = [root for root in ancestors
                          if obs.node(root).role in {"row", "listitem", "article"}]
        # Prefer the nearest explicit record over an inner link/text wrapper.
        for root in explicit_roots[:1] or ancestors:
            parent = obs.node(root)
            if parent.role not in {"row", "listitem", "article", "group"}:
                continue
            members = set(obs.subtree(root))
            controls = [control for index, control in surface.controls.items() if index in members]
            if any(control["role"] in {"textbox", "combobox"}
                   for control in controls):
                break
            texts = [obs.node(index).name for index in members if obs.node(index).name]
            destinations = [control["destination"] for control in controls
                            if control["role"] == "link" and control.get("destination")]
            explicit = parent.role in {"row", "listitem", "article"}
            local_action = any(control["role"] in {"button", "link"} for control in controls)
            if not explicit and not (local_action and len(set(texts)) >= 2):
                continue
            if root not in used:
                used.add(root)
                matches.append({"root": root, "value_node": node.i, "role": parent.role,
                                "texts": texts, "link_destinations": destinations,
                                "basis": "visible_local_record",
                                "observation": obs.structural_signature()})
            break
    return matches
