"""Local counterexample-guided abstraction hypotheses and decisions.

The deterministic V2 front end remains a proposal generator.  This module keeps
small ambiguity components around one counterexample, records the alternatives
and their evidence, and exposes only supported refinements to the abstractor.
No global partition beam is constructed.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.counterexamples import Counterexample
from semabi.compiler.v2.graph import node_text, tokens


HYPOTHESES_FILE = "hypotheses_v2.json"
DECISIONS_FILE = "refinements_v2.json"
COUNTEREXAMPLES_FILE = "counterexamples_v2.jsonl"
INTERVENTIONS_FILE = "interventions_v2.jsonl"


def _id(*parts: object) -> str:
    raw = json.dumps(parts, sort_keys=True, default=str).encode()
    return hashlib.sha1(raw).hexdigest()[:12]


@dataclass
class EvidenceContribution:
    evidence_class: str
    source: str
    step: int | None
    observation_sigs: list[str]
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class LocalHypothesis:
    id: str
    kind: str
    status: str
    complexity: int
    target: dict[str, Any]
    predicted_outcomes: dict[str, Any]
    evidence: list[EvidenceContribution] = field(default_factory=list)


@dataclass
class AmbiguityComponent:
    id: str
    counterexample_steps: list[int]
    scope: dict[str, Any]
    hypotheses: list[LocalHypothesis]
    selected_intervention: dict[str, Any] | None = None


@dataclass
class RefinementDecision:
    id: str
    component_id: str
    kind: str
    status: str
    target: dict[str, Any]
    accepted_hypothesis: str
    evidence: list[dict[str, Any]]


def _unit_slot(A, sig: str, node: int):
    """Return the current owner/slot plus a unique co-local sibling mention, if any."""
    obs = A.G.obs[sig]
    units = A.H.parse_units(sig)
    owner = None
    slot = None
    for ui in units:
        for sid, ni in ui.slot_nodes.items():
            if ni == node:
                owner, slot = ui, sid
                break
        if owner is not None:
            break
    if owner is None or slot is None:
        return None
    parent = obs.node(node).parent
    siblings = []
    for ui in units:
        if ui is owner or obs.node(ui.root).parent != parent:
            continue
        u = A.H.units.get(ui.template)
        if u is None or not u.key_slot or u.key_slot not in ui.slots:
            continue
        siblings.append((ui, u, ui.slots[u.key_slot]))
    sibling = siblings[0] if len(siblings) == 1 else None
    return owner, slot.rstrip("~"), sibling


def _correspondence_bridge(A, log: EvidenceLog, mention_template: str) -> dict[str, Any] | None:
    """A local one-to-one code/name bridge already present in candidate relations.

    This is only a proposal: a semantic link object can also be one-to-one.  A view
    intervention must still show that acting through the coded representation reveals
    the paired representation without changing persistent state.
    """
    H = A.H
    mention_tid = H.tid_of_template.get(mention_template)
    if mention_tid is None:
        return None
    mention_values = H.units[mention_template].primary_key_values()

    def embedded_key(value: str) -> str | None:
        value_tokens = tokens(value)
        matches = []
        for candidate in mention_values:
            needle = tokens(candidate)
            if any(value_tokens[i:i + len(needle)] == needle for i in range(len(value_tokens) - len(needle) + 1)):
                matches.append(candidate)
        return matches[0] if len(matches) == 1 else None

    for et in H.entity_types.values():
        for template in et.units:
            u = H.units[template]
            if not u.key_slot:
                continue
            code_refs = [sid for (t, sid), tid in et.ref_slots.items() if t == template and tid == mention_tid]
            target_refs = [(sid, tid) for (t, sid), tid in et.ref_slots.items()
                           if t == template and tid != mention_tid]
            if u.key_slot not in code_refs or not target_refs:
                continue
            for target_sid, target_tid in target_refs:
                pairs = []
                row_overrides = []
                for ui in u.instances:
                    raw, b = ui.slots.get(u.key_slot), ui.slots.get(target_sid)
                    a = embedded_key(raw) if raw is not None else None
                    if a is not None and b is not None:
                        pairs.append((a, b))
                        row_overrides.append({"sig": ui.sig, "template": template, "from": raw, "to": a})
                if len({a for a, _ in pairs}) < 2:
                    continue
                canonical = H.entity_types.get(target_tid)
                if canonical is None:
                    continue
                canonical_templates = set(canonical.units)
                overrides = list(row_overrides)
                observed_pairs: set[tuple[str, str]] = set()
                active_code: dict[int, str] = {}
                for step in log.steps:
                    before = log.obs(step.before)
                    source_code = None
                    if step.action.kind == "click" and step.action.target is not None:
                        for source in H.parse_units(step.before):
                            if step.action.target not in before.subtree(source.root):
                                continue
                            su = H.units.get(source.template)
                            if su is None or not su.key_slot:
                                continue
                            rendered = source.slots.get(su.key_slot)
                            if source.template == mention_template:
                                source_code = rendered
                            elif source.template == template:
                                source_code = embedded_key(rendered) if rendered is not None else None
                            if source_code in mention_values:
                                break
                            source_code = None
                    after_units = [x for x in H.parse_units(step.after) if x.template in canonical_templates]
                    if source_code is not None and len(after_units) == 1:
                        active_code[step.episode] = source_code
                    if step.action.kind == "reset":
                        active_code.pop(step.episode, None)
                    code = active_code.get(step.episode)
                    if code is not None and len(after_units) == 1:
                        target = after_units[0]
                        tu = H.units.get(target.template)
                        raw_target = target.slots.get(tu.key_slot) if tu and tu.key_slot else None
                        if raw_target is not None:
                            observed_pairs.add((code, raw_target))
                            overrides.append({"sig": step.after, "template": target.template,
                                              "from": raw_target, "to": code})
                    if step.action.kind == "reload" and not after_units:
                        active_code.pop(step.episode, None)
                unique_overrides = {(x["sig"], x["template"], x["from"]): x for x in overrides}
                if not observed_pairs:
                    continue
                return {"bridge_template": template, "bridge_key_slot": u.key_slot,
                        "target_slot": target_sid, "canonical_templates": canonical.units,
                        "observed_pairs": [list(x) for x in sorted(observed_pairs)],
                        "key_overrides": list(unique_overrides.values()),
                        "status": "UNTESTED"}
    return None


def _component_for_widget(A, log: EvidenceLog, ce: Counterexample) -> AmbiguityComponent | None:
    step = log.steps[ce.step]
    if step.action.target is None or step.action.kind not in ("select", "click"):
        return None
    before = log.obs(step.before)
    node = before.node(step.action.target)
    if node.role not in ("combobox", "textbox", "checkbox", "radio"):
        return None
    binding = _unit_slot(A, step.before, step.action.target)
    if binding is None:
        return None
    owner, slot, sibling = binding
    component_id = "amb-" + _id(owner.template, slot, node.role)
    common = {
        "source_template": owner.template,
        "source_slot": slot,
        "widget_role": node.role,
    }
    hs: list[LocalHypothesis] = []
    hs.append(LocalHypothesis(
        "h-" + _id(component_id, "view"), "VIEW_STATE", "UNTESTED", 0, dict(common),
        {"reload_value": "reverts", "persistent_domain_delta": False},
    ))
    hs.append(LocalHypothesis(
        "h-" + _id(component_id, "owner"), "ATTRIBUTE_ON_ENCLOSING_MENTION", "UNTESTED", 1,
        dict(common), {"reload_value": "persists", "owner": "enclosing_unit"},
    ))
    if sibling is not None:
        ui, u, key = sibling
        target = dict(common)
        target.update({"target_template": ui.template, "target_key_slot": u.key_slot,
                       "observed_target_key": key, "attachment_relation": "UNIQUE_SHARED_PARENT"})
        bridge = _correspondence_bridge(A, log, ui.template)
        if bridge:
            target["correspondence_bridge"] = bridge
        contextual = False
        keys_by_parent: dict[str | None, set[str]] = {}
        parents_by_key: dict[str, set[str | None]] = {}
        for x in u.instances:
            k = x.slots.get(u.key_slot)
            if k is None:
                continue
            pk = A.H._parent_key(x)
            keys_by_parent.setdefault(pk, set()).add(k)
            parents_by_key.setdefault(k, set()).add(pk)
        duplicate_across_context = any(len(ps) > 1 for ps in parents_by_key.values())
        if duplicate_across_context:
            contextual = True
            target["identity_policy"] = "ENCLOSING_KEY_PLUS_MENTION_KEY"
        h = LocalHypothesis(
            "h-" + _id(component_id, "sibling"), "ATTRIBUTE_ON_COLOCAL_MENTION", "UNTESTED", 2,
            target, {"reload_value": "persists", "only_target_mention_changes": True},
        )
        # One widget and one keyed mention sharing a parent is association evidence, not
        # ontology truth.  Duplicate mention keys across enclosing contexts are direct
        # evidence that a bare visible key is insufficient.
        h.evidence.append(EvidenceContribution(
            "VIEW_INVARIANCE_SUPPORT", "structural_colocation", ce.step, [step.before],
            {"relation": "unique keyed mention and widget share an immediate parent"},
        ))
        if bridge:
            h.evidence.append(EvidenceContribution(
                "UNDETERMINED", "bijective_candidate_reference", ce.step, [step.before],
                {"observed_pairs": bridge["observed_pairs"], "reason": "a candidate view transition may connect alternate representations or merely related entities"},
            ))
        if contextual:
            h.evidence.append(EvidenceContribution(
                "DOMAIN_SUPPORT", "duplicate_separation", ce.step, [step.before],
                {"reason": "the same mention key occurs under multiple enclosing entity keys"},
            ))
        hs.append(h)

        # If one enclosing entity simultaneously carries several independently valued
        # copies of this widget, a single-valued enclosing attribute is contradicted.
        values_by_owner: dict[tuple[str, str | None], set[str]] = {}
        for x in A.H.units[owner.template].instances:
            owner_key = x.slots.get(A.H.units[owner.template].key_slot) if A.H.units[owner.template].key_slot else None
            for sid, value in x.slots.items():
                if sid.rstrip("~").startswith(slot.split("@")[0]):
                    values_by_owner.setdefault((x.sig, owner_key), set()).add(value)
        if any(len(vs) > 1 for vs in values_by_owner.values()):
            enclosing = hs[1]
            enclosing.status = "CONTRADICTED"
            enclosing.evidence.append(EvidenceContribution(
                "DOMAIN_CONTRADICTION", "co_present_multiplicity", ce.step, [step.before],
                {"reason": "one enclosing entity simultaneously carries multiple values at the candidate slot"},
            ))

    return AmbiguityComponent(component_id, [ce.step], common, hs)


def _reveal_correspondence_components(A, log: EvidenceLog, counterexamples: list[Counterexample]) -> list[AmbiguityComponent]:
    """Propose local same-entity assignments from action-conditioned mention reveals.

    A click on one keyed mention followed by a differently structured keyed mention with
    the same rendered key is correspondence evidence.  It is not sufficient by itself:
    the alternatives remain unresolved until a reload/survey intervention establishes a
    view-only transition.  Assignments are observation-local so a generic button template
    cannot drag unrelated controls into the target entity type.
    """
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    ce_by_step = {c.step: c for c in counterexamples}
    for step in log.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        before = log.obs(step.before)
        source_node = before.node(step.action.target)
        if source_node.role not in ("button", "link") or not source_node.name:
            continue
        source_template = A.H.template(step.before, step.action.target)
        source_key = source_node.name
        candidates = []
        for target in A.H.parse_units(step.after):
            if target.template == source_template:
                continue
            u = A.H.units.get(target.template)
            if u is not None and u.key_slot and target.slots.get(u.key_slot) == source_key:
                candidates.append((target, u))
        target_templates = {x.template for x, _ in candidates}
        if len(target_templates) != 1:
            continue
        target_template = next(iter(target_templates))
        target_instance = next(x for x, _ in candidates if x.template == target_template)
        if len(log.obs(step.after).subtree(target_instance.root)) <= 1:
            continue  # prefer a compact mention revealing a richer representation
        g = groups.setdefault((source_template, target_template), {
            "source_template": source_template,
            "source_role": source_node.role,
            "target_template": target_template,
            "observations": [],
            "keys": set(),
            "reveal_steps": [],
        })
        g["keys"].add(source_key)
        g["reveal_steps"].append(step.step)
        g["observations"].append({"step": step.step, "before_sig": step.before,
                                  "after_sig": step.after, "key": source_key,
                                  "action": str(step.action)})

    out = []
    for (source_template, target_template), g in groups.items():
        if len(g["keys"]) < 2 or len(g["reveal_steps"]) < 2:
            continue
        assignments = []
        for sig, obs in A.G.obs.items():
            for node in obs.nodes:
                if node.role != g["source_role"] or node.name not in g["keys"]:
                    continue
                if A.H.template(sig, node.i) == source_template:
                    assignments.append({"sig": sig, "node": node.i, "template": source_template,
                                        "key": node.name, "target_template": target_template})
        # Connect the identity ambiguity to unresolved events whose raw fragments mention
        # one of the affected keys.  Reveal steps remain provenance but do not become a
        # false persistent-change denominator merely because they are sensing actions.
        affected = []
        for ce in counterexamples:
            if ce.status != "UNGROUNDED":
                continue
            if any(ch.old in g["keys"] or ch.new in g["keys"] for ch in ce.changes):
                affected.append(ce.step)
        component_id = "amb-" + _id("reveal", source_template, target_template)
        common = {"source_template": source_template, "source_role": g["source_role"],
                  "target_template": target_template, "observed_keys": sorted(g["keys"]),
                  "mention_assignments": assignments, "reveal_steps": g["reveal_steps"]}
        separate = LocalHypothesis(
            "h-" + _id(component_id, "related"), "RELATED_CONTEXT_SELECTION", "UNTESTED", 0,
            dict(common), {"revealed_key": "may_match", "persistent_state_changed": False},
        )
        same = LocalHypothesis(
            "h-" + _id(component_id, "same"), "SAME_ENTITY_MENTION_SET", "UNTESTED", 1,
            dict(common), {"revealed_key": "same", "persistent_state_changed": False},
            [EvidenceContribution("VIEW_INVARIANCE_SUPPORT", "action_conditioned_equal_key_reveal", None,
                                  sorted({x["after_sig"] for x in g["observations"]}),
                                  {"observations": g["observations"][:20]})],
        )
        out.append(AmbiguityComponent(component_id, affected, common, [separate, same], {
            "kind": "IDENTITY_CORRESPONDENCE_PROBE", "disagreement_score": 1, "cost": 1,
            "risk": "VIEW_NAVIGATION", "target_hypotheses": [separate.id, same.id],
            "predictions": {separate.id: separate.predicted_outcomes, same.id: same.predicted_outcomes},
        }))
    return out


def _matrix_context(A, sig: str, cell: int) -> str | None:
    """Key of the header mention above a matrix cell, if the graph exposes one."""
    obs = A.G.obs[sig]
    row = obs.node(cell).parent
    if row < 0 or obs.node(row).role != "row":
        return None
    table = obs.node(row).parent
    while table >= 0 and obs.node(table).role != "table":
        table = obs.node(table).parent
    if table < 0:
        return None
    rows = [i for i in obs.subtree(table) if obs.node(i).role == "row"]
    if not rows or row == rows[0]:
        return None
    cells = obs.children(row)
    header_cells = obs.children(rows[0])
    if cell not in cells or cells.index(cell) >= len(header_cells):
        return None
    header = header_cells[cells.index(cell)]
    for ui in A.H.parse_units(sig):
        if ui.root != header:
            continue
        u = A.H.units.get(ui.template)
        if u and u.key_slot:
            return ui.slots.get(u.key_slot)
    values = A.G.data_tokens(sig, header)
    return values[0] if values else None


def _matrix_record_components(A, log: EvidenceLog, counterexamples: list[Counterexample]) -> list[AmbiguityComponent]:
    """Propose anchor-vs-record splits when row/column cells reveal rich records."""
    out = []
    H = A.H
    for et in H.entity_types.values():
        row_templates = [t for t in et.units if any(H.G.obs[x.sig].node(x.root).role == "row"
                                                    for x in H.units[t].instances[:1])]
        detail_templates = [t for t in et.units if t not in row_templates and len([
            1 for (t2, _), _tid in et.ref_slots.items() if t2 == t
        ]) >= 2 and et.attr_slots.get(t)]
        if not row_templates or not detail_templates:
            continue
        for detail in detail_templates:
            refs = [(sid, tid) for (t, sid), tid in et.ref_slots.items() if t == detail]
            if len({tid for _, tid in refs}) < 2:
                continue
            detail_u = H.units[detail]
            # Slots that demonstrably change while key and references are unchanged are
            # record state.  Slots fixed by the anchor key remain anchor attributes.
            changed_kinds: dict[str, set[str]] = {}
            changed_counts: Counter = Counter()
            by_sig = {ui.sig: ui for ui in detail_u.instances}
            ref_slots = {sid for sid, _ in refs}
            for step in log.steps:
                a, b = by_sig.get(step.before), by_sig.get(step.after)
                if a is None or b is None or a.slots.get(detail_u.key_slot) != b.slots.get(detail_u.key_slot):
                    continue
                if any(a.slots.get(s) != b.slots.get(s) for s in ref_slots):
                    continue
                for sid in et.attr_slots[detail]:
                    if a.slots.get(sid) != b.slots.get(sid):
                        changed_kinds.setdefault(sid, set()).add(step.action.kind)
                        changed_counts[sid] += 1
            click_attrs = {sid for sid, kinds in changed_kinds.items() if "click" in kinds}
            best_support = max((changed_counts[sid] for sid in click_attrs), default=0)
            # Minimal refinement: retain only the state distinction with the strongest
            # independent action support.  We can add another slot after a later
            # counterexample; representing every co-changing value invites overfitting.
            record_attrs = {sid for sid in click_attrs if changed_counts[sid] == best_support}
            if not record_attrs:
                continue
            stable_attrs = set()
            for sid in et.attr_slots[detail] - record_attrs:
                values_by_key: dict[str, set[str]] = {}
                for ui in detail_u.instances:
                    k, v = ui.slots.get(detail_u.key_slot), ui.slots.get(sid)
                    if k is not None and v is not None:
                        values_by_key.setdefault(k, set()).add(v)
                if values_by_key and all(len(vs) == 1 for vs in values_by_key.values()):
                    stable_attrs.add(sid)

            cells = []
            target_counts: Counter = Counter()
            context_counts: Counter = Counter()
            for t in row_templates:
                for ui in H.units[t].instances:
                    obs = H.G.obs[ui.sig]
                    row_cells = [c for c in obs.children(ui.root) if obs.node(c).role == "cell"]
                    for cell in row_cells[1:]:
                        context = _matrix_context(A, ui.sig, cell)
                        if context is None:
                            continue
                        for node_i in obs.subtree(cell):
                            node = obs.node(node_i)
                            if node.role not in ("button", "link") or not node.name:
                                continue
                            matching_tids = [tid for tid, other in H.entity_types.items()
                                             if node.name in {v for ot in other.units for v in H.units[ot].primary_key_values()}]
                            if len(matching_tids) != 1:
                                continue
                            target_tid = matching_tids[0]
                            context_tids = [tid for tid, other in H.entity_types.items()
                                            if context in {v for ot in other.units for v in H.units[ot].primary_key_values()}]
                            if len(context_tids) != 1:
                                continue
                            context_tid = context_tids[0]
                            target_counts[target_tid] += 1
                            context_counts[context_tid] += 1
                            row_u = H.units[t]
                            cells.append({"sig": ui.sig, "row_template": t, "row_root": ui.root,
                                          "cell": cell, "button": node_i, "anchor_key": ui.slots[row_u.key_slot],
                                          "context_key": context, "target_key": node.name})
            if len(cells) < 2 or not target_counts or not context_counts:
                continue
            target_tid = target_counts.most_common(1)[0][0]
            context_tid = context_counts.most_common(1)[0][0]
            detail_context = next((sid for sid, tid in refs if tid == context_tid), None)
            detail_target = next((sid for sid, tid in refs if tid == target_tid), None)
            if detail_context is None or detail_target is None:
                continue
            spec = {
                "anchor_entity_tid": et.tid, "row_templates": row_templates,
                "detail_template": detail, "detail_context_slot": detail_context,
                "detail_target_slot": detail_target, "context_entity_tid": context_tid,
                "target_entity_tid": target_tid, "record_attr_slots": sorted(record_attrs),
                # Entity tids are run-local.  A decision transferred to an independently
                # collected trace must resolve its endpoints by unit template, never by id.
                "anchor_entity_templates": sorted(et.units),
                "context_entity_templates": sorted(H.entity_types[context_tid].units),
                "target_entity_templates": sorted(H.entity_types[target_tid].units),
                "anchor_attr_slots": sorted(stable_attrs), "matrix_cells": cells,
                "contradiction_evidence": {
                    "kind": "ONE_ANCHOR_KEY_HAS_MULTIPLE_SIMULTANEOUS_RECORD_CONTEXTS",
                    "observed_record_mentions": len(cells),
                },
            }
            component_id = "amb-" + _id("matrix-record", et.tid, detail, context_tid, target_tid)
            flat = LocalHypothesis("h-" + _id(component_id, "flat"), "ROW_IS_ENTITY", "UNTESTED", 0,
                                   spec, {"detail_identity": "row_key_only"})
            split = LocalHypothesis("h-" + _id(component_id, "split"), "RELATIONAL_RECORD_SPLIT", "UNTESTED", 2,
                                    spec, {"detail_identity": "row_key_plus_column_context",
                                           "cell_target_matches_detail_target": True})
            split.evidence.append(EvidenceContribution(
                "DOMAIN_SUPPORT", "same_key_different_context_state", None,
                sorted({x["sig"] for x in cells}),
                {"record_attrs": sorted(record_attrs), "n_matrix_cells": len(cells)},
            ))
            out.append(AmbiguityComponent(component_id, [], spec, [flat, split], {
                "kind": "MATRIX_RECORD_CORRESPONDENCE_PROBE", "disagreement_score": 1,
                "cost": 1, "risk": "VIEW_NAVIGATION", "target_hypotheses": [flat.id, split.id],
                "predictions": {flat.id: flat.predicted_outcomes, split.id: split.predicted_outcomes},
            }))
    return out


def _preceding_heading_context(obs, node_i: int) -> str | None:
    """Nearest preceding heading at any enclosing sibling level.

    This is a generic observation relation, not a claim that the heading is an entity.
    It gives the refinement layer a local alternative for mentions that move between
    rendered regions after an action.
    """
    child = node_i
    parent = obs.node(child).parent
    while parent >= 0:
        siblings = obs.children(parent)
        if child in siblings:
            for sibling in reversed(siblings[:siblings.index(child)]):
                if obs.node(sibling).role == "heading":
                    value = node_text(obs.node(sibling))
                    if value:
                        return value
        child, parent = parent, obs.node(parent).parent
    return None


def _embedded_key(value: str | None, candidates: set[str]) -> str | None:
    value_tokens = tokens(value or "")
    matches = []
    for candidate in candidates:
        needle = tokens(candidate)
        if needle and any(value_tokens[i:i + len(needle)] == needle
                          for i in range(len(value_tokens) - len(needle) + 1)):
            matches.append(candidate)
    # Longest exact token sequence wins only if it is unique at that length.  This lets a
    # composite key dominate one of its components without silently resolving duplicates.
    if not matches:
        return None
    width = max(len(tokens(x)) for x in matches)
    best = [x for x in matches if len(tokens(x)) == width]
    return best[0] if len(best) == 1 else None


def _context_membership_components(A, log: EvidenceLog,
                                   counterexamples: list[Counterexample]) -> list[AmbiguityComponent]:
    """Local alternatives for an entity mention moving between heading contexts.

    A before/after context move is only a proposal.  The view-state and duplicate-mention
    alternatives remain live until an action -> reload -> cross-view survey shows that the
    same mention stays in the new context and no copy remains in the old one.
    """
    proposals: dict[tuple, dict[str, Any]] = {}

    def mentions(obs, keys):
        out: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
        for node in obs.nodes:
            if node.role not in ("button", "link", "group", "text"):
                continue
            context = _preceding_heading_context(obs, node.i)
            key = _embedded_key(node_text(node), keys)
            if context is not None and key is not None:
                out[key].append((node.i, context, node_text(node) or ""))
        return out

    def anchored_mentions(sig, template, keys):
        """Key mentions from the existing rich entity representation only.

        Accessible names elsewhere on the screen often repeat an entity key beneath a
        page-level heading.  Treating all of those as source memberships would turn UI
        chrome into candidate domain state.  The current entity hypothesis already gives
        us a narrower, generic proposal anchor: its key-slot node.  The destination remains
        a raw mention because discovering an alternative representation is the purpose of
        the refinement.
        """
        obs = A.G.obs[sig]
        unit = A.H.units[template]
        first_key_slot = unit.key_slot.split("|")[0] if unit.key_slot else None
        out: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
        if first_key_slot is None:
            return out
        for ui in A.H.parse_units(sig):
            if ui.template != template:
                continue
            key = ui.slots.get(first_key_slot)
            node_i = ui.slot_nodes.get(first_key_slot)
            if key not in keys or node_i is None:
                continue
            context = _preceding_heading_context(obs, node_i)
            if context is not None:
                out[key].append((node_i, context, node_text(obs.node(node_i)) or ""))
        return out

    for et in A.H.entity_types.values():
        keys = {
            value for template in et.units
            for value in A.H.units[template].primary_key_values()
            if isinstance(value, str) and value
        }
        if len(keys) < 2:
            continue
        # Prefer the richest existing representation as the entity type anchor.  Raw
        # contextual mentions contribute identity/context only.
        target_template = max(
            et.units,
            key=lambda template: max((len(A.G.obs[x.sig].subtree(x.root))
                                      for x in A.H.units[template].instances), default=0),
        )
        if max((len(A.G.obs[x.sig].subtree(x.root))
                for x in A.H.units[target_template].instances), default=0) < 4:
            continue
        for ce in counterexamples:
            if ce.status not in ("UNDETERMINED", "UNGROUNDED"):
                continue
            step = log.steps[ce.step]
            if step.action.kind not in ("click", "press"):
                continue
            before = log.obs(step.before)
            mb = anchored_mentions(step.before, target_template, keys)
            future = []
            for later_i in range(ce.step, min(len(log.steps), ce.step + 13)):
                later = log.steps[later_i]
                if later.episode != step.episode:
                    break
                future.append((later_i, later.after, mentions(log.obs(later.after), keys)))
            for key in sorted(mb):
                if len(mb[key]) != 1:
                    continue
                # The candidate action must remove the current rich representation.  If
                # that representation remains visible, a later occurrence in another
                # context is not evidence about this action (it can be caused by one of
                # the intervening sensing actions instead).
                if key in anchored_mentions(step.after, target_template, keys):
                    continue
                source_node, source_context, source_text = mb[key][0]
                revealed = None
                for later_i, later_sig, ma in future:
                    candidates = [x for x in ma.get(key, []) if x[1] != source_context]
                    if len(candidates) == 1:
                        revealed = (later_i, later_sig, candidates[0])
                        break
                if revealed is None:
                    continue
                reveal_step, reveal_sig, (target_node, target_context, target_text) = revealed
                if source_context == target_context:
                    continue
                # Locate the action that selected this mention, then retain only the short
                # displayed control tail ending in the candidate state-changing step.
                start = None
                for prior_i in range(ce.step - 1, max(-1, ce.step - 7), -1):
                    prior = log.steps[prior_i]
                    if prior.episode != step.episode or prior.action.kind in ("reset", "reload"):
                        break
                    if prior.action.target is None:
                        continue
                    prior_obs = log.obs(prior.before)
                    if _embedded_key(node_text(prior_obs.node(prior.action.target)), {key}) == key:
                        start = prior_i
                        break
                if start is None:
                    continue
                boundary = start - 1
                while boundary >= 0 and log.steps[boundary].episode == step.episode \
                        and log.steps[boundary].action.kind not in ("reset", "reload"):
                    boundary -= 1
                prefix = []
                replayable = True
                for action_step in log.steps[boundary + 1:start + 1]:
                    action = action_step.action
                    desc = action.target_desc or {}
                    if action.kind not in ("click", "press") or (action.kind == "click" and not desc.get("role")):
                        replayable = False
                        break
                    prefix.append({"kind": action.kind, "role": desc.get("role"),
                                   "name": desc.get("name"), "text": action.text})
                tail = []
                for action_step in log.steps[start + 1:ce.step + 1]:
                    action = action_step.action
                    desc = action.target_desc or {}
                    if action.kind not in ("click", "press") or (action.kind == "click" and not desc.get("role")):
                        replayable = False
                        break
                    tail.append({"kind": action.kind, "role": desc.get("role"),
                                 "name": desc.get("name"), "text": action.text})
                if not replayable or not prefix or not tail:
                    continue
                reset_seed = None
                for prior in reversed(log.steps[:start + 1]):
                    if prior.episode != step.episode:
                        continue
                    if prior.action.kind == "reset":
                        reset_seed = prior.action.text
                        break
                pkey = (target_template, source_context, target_context,
                        json.dumps(prefix, sort_keys=True), json.dumps(tail, sort_keys=True))
                proposal = proposals.setdefault(pkey, {
                    "target_entity_tid": et.tid, "target_template": target_template,
                    "keys": keys, "source_context": source_context,
                    "target_context": target_context, "replay_prefix": prefix,
                    "replay_tail": tail,
                    "reset_seed": reset_seed, "events": [],
                })
                proposal["events"].append({
                    "step": ce.step, "key": key,
                    "source_node": source_node, "target_node": target_node,
                    "source_text": source_text, "target_text": target_text,
                    "target_role": log.obs(reveal_sig).node(target_node).role,
                    "before_sig": step.before, "after_sig": reveal_sig,
                    "reveal_step": reveal_step, "reveal_delay": reveal_step - ce.step,
                })

    out = []
    for (_target, _source_context, _target_context, _prefix, _tail), proposal in proposals.items():
        keys = proposal.pop("keys")
        target_template = proposal["target_template"]
        # Observation-scoped assignments transfer the verified relation pattern while
        # refusing keys that occur in more than one context in one observation.
        assignments = []
        conflicts = []
        for sig, obs in A.G.obs.items():
            by_key: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
            allowed_contexts = {proposal["source_context"], proposal["target_context"]}
            for node in obs.nodes:
                if node.role not in ("button", "link", "group", "text"):
                    continue
                context = _preceding_heading_context(obs, node.i)
                key = _embedded_key(node_text(node), keys)
                if context in allowed_contexts and key is not None:
                    by_key[key].append((node.i, context, node.role))
            for key, rows in by_key.items():
                rows = list({(node, context, role) for node, context, role in rows})
                contexts = {x[1] for x in rows}
                if len(contexts) != 1:
                    conflicts.append({"sig": sig, "key": key, "contexts": sorted(contexts)})
                    continue
                # Prefer an actionable leaf over its accessible-name container.
                role_order = {"button": 0, "link": 0, "group": 1, "text": 2}
                rows.sort(key=lambda x: (role_order.get(x[2], 3), x[0]))
                node, context, _role = rows[0]
                assignments.append({
                    "sig": sig, "node": node, "target_template": target_template,
                    "key": key, "context": context,
                })
        events = proposal["events"]
        component_id = "amb-" + _id(
            "context-membership", target_template, proposal["source_context"],
            proposal["target_context"], proposal["replay_prefix"], proposal["replay_tail"],
        )
        scope = {
            **proposal, "context_assignments": assignments,
            "assignment_conflicts": conflicts,
            "observed_keys": sorted({x["key"] for x in events}),
            "max_reveal_delay": max(x["reveal_delay"] for x in events),
            "destination_is_non_actionable": any(
                x["target_role"] not in ("button", "link") for x in events
            ),
        }
        view = LocalHypothesis(
            "h-" + _id(component_id, "view"), "CONTEXT_IS_VIEW_STATE", "UNTESTED", 0,
            dict(scope), {"after_reload_context": proposal["source_context"],
                          "persistent_domain_delta": False},
        )
        duplicate = LocalHypothesis(
            "h-" + _id(component_id, "duplicate"), "DISTINCT_SAME_KEY_MENTIONS", "UNTESTED", 1,
            dict(scope), {"after_survey_contexts": [proposal["source_context"], proposal["target_context"]]},
        )
        persistent = LocalHypothesis(
            "h-" + _id(component_id, "persistent"), "PERSISTENT_CONTEXT_MEMBERSHIP", "UNTESTED", 1,
            dict(scope), {"after_reload_context": proposal["target_context"],
                          "old_context_absent": True, "persistent_domain_delta": True},
            [EvidenceContribution(
                "UNDETERMINED", "direct_before_after_context_move", x["step"],
                [x["before_sig"], x["after_sig"]],
                {"key": x["key"], "source_context": proposal["source_context"],
                 "target_context": proposal["target_context"]},
            ) for x in events],
        )
        out.append(AmbiguityComponent(
            component_id, [x["step"] for x in events], scope,
            [view, duplicate, persistent], {
                "kind": "CONTEXT_MEMBERSHIP_PERSISTENCE_PROBE",
                "disagreement_score": 3,
                "cost": len(proposal["replay_prefix"]) + len(proposal["replay_tail"]) + 2,
                "risk": "RESETTABLE_DOMAIN_ACTION",
                "target_hypotheses": [view.id, duplicate.id, persistent.id],
                "predictions": {x.id: x.predicted_outcomes for x in (view, duplicate, persistent)},
            },
        ))
    return out


def build_components(A, log: EvidenceLog, counterexamples: list[Counterexample]) -> list[AmbiguityComponent]:
    """Build factorized alternatives; identical local scopes share one component."""
    by_id: dict[str, AmbiguityComponent] = {}
    for ce in counterexamples:
        if ce.status != "UNGROUNDED" or not any(ch.channel == "WIDGET" for ch in ce.changes):
            continue
        comp = _component_for_widget(A, log, ce)
        if comp is None:
            continue
        if comp.id in by_id:
            by_id[comp.id].counterexample_steps.append(ce.step)
        else:
            by_id[comp.id] = comp
    for comp in _reveal_correspondence_components(A, log, counterexamples):
        by_id.setdefault(comp.id, comp)
    for comp in _matrix_record_components(A, log, counterexamples):
        by_id.setdefault(comp.id, comp)
    for comp in _context_membership_components(A, log, counterexamples):
        by_id.setdefault(comp.id, comp)
    return list(by_id.values())


def select_intervention(component: AmbiguityComponent) -> dict[str, Any]:
    """Select the cheapest live probe with maximal disagreement among unresolved alternatives."""
    live = [h for h in component.hypotheses if h.status not in ("CONTRADICTED",)]
    outcomes = {json.dumps(h.predicted_outcomes, sort_keys=True) for h in live}
    plan = {
        "kind": "PERSISTENCE_PROBE",
        "disagreement_score": len(outcomes),
        "cost": 1,
        "risk": "RESETTABLE_VALUE_CHANGE",
        "target_hypotheses": [h.id for h in live],
        "predictions": {h.id: h.predicted_outcomes for h in live},
    }
    component.selected_intervention = plan
    return plan


def intervention_utility(component: AmbiguityComponent) -> float:
    """Crude discrimination per estimated primitive, used only for scheduling."""
    plan = component.selected_intervention or select_intervention(component)
    disagreement = max(0.0, float(plan.get("disagreement_score", 0)))
    cost = max(1.0, float(plan.get("cost", 1)))
    return disagreement / cost


def choose_intervention_component(components: list[AmbiguityComponent]) -> AmbiguityComponent | None:
    """Prefer high disagreement per primitive without inventing semantic confidence."""
    if not components:
        return None
    return sorted(
        components,
        key=lambda component: (
            -intervention_utility(component),
            -len(component.counterexample_steps),
            component.id,
        ),
    )[0]


def apply_intervention_result(component: AmbiguityComponent, result: dict[str, Any]) -> RefinementDecision | None:
    """Update statuses from observed persistence and choose a supported local refinement."""
    persisted = result.get("same_mention_value_persisted") is True
    if not persisted:
        return None
    for h in component.hypotheses:
        contribution = EvidenceContribution(
            "DOMAIN_SUPPORT" if h.kind != "VIEW_STATE" else "VIEW_DOMAIN_LEAK_CONTRADICTION",
            "controlled_persistence_probe", result.get("action_step"),
            [x for x in (result.get("before_sig"), result.get("after_sig"), result.get("reload_sig")) if x],
            {"chosen_value": result.get("chosen_value"), "reload_value": result.get("reload_value")},
        )
        h.evidence.append(contribution)
        if h.kind == "VIEW_STATE":
            h.status = "CONTRADICTED"
        elif h.status != "CONTRADICTED":
            h.status = "SUPPORTED"
    supported = [h for h in component.hypotheses if h.status == "SUPPORTED"]
    # Prefer the smallest supported attachment that survives existing contradictions.
    supported.sort(key=lambda h: (h.complexity, h.id))
    colocal = [h for h in supported if h.kind == "ATTRIBUTE_ON_COLOCAL_MENTION"]
    accepted = (colocal or supported)[:1]
    if not accepted:
        return None
    h = accepted[0]
    target = dict(h.target)
    target["merge_compatible_mentions"] = True
    return RefinementDecision(
        "ref-" + _id(component.id, h.id, result.get("action_step")), component.id,
        "ATTACH_PERSISTENT_WIDGET", "PROVISIONAL", target, h.id,
        [{"intervention": result}, *[asdict(e) for e in h.evidence]],
    )


def apply_context_membership_result(component: AmbiguityComponent,
                                    result: dict[str, Any]) -> RefinementDecision | None:
    """Accept contextual state only after reload/survey eliminates local alternatives."""
    supported = (result.get("target_context_persisted") is True
                 and result.get("source_context_absent") is True
                 and result.get("same_key_in_both_contexts") is False)
    if not supported:
        return None
    for hypothesis in component.hypotheses:
        if hypothesis.kind == "PERSISTENT_CONTEXT_MEMBERSHIP":
            hypothesis.status = "SUPPORTED"
            evidence_class = "DOMAIN_SUPPORT"
        elif hypothesis.kind == "CONTEXT_IS_VIEW_STATE":
            hypothesis.status = "CONTRADICTED"
            evidence_class = "VIEW_DOMAIN_LEAK_CONTRADICTION"
        elif hypothesis.kind == "DISTINCT_SAME_KEY_MENTIONS":
            hypothesis.status = "CONTRADICTED"
            evidence_class = "DOMAIN_CONTRADICTION"
        else:
            continue
        hypothesis.evidence.append(EvidenceContribution(
            evidence_class, "controlled_context_membership_probe",
            result.get("action_step"),
            [x for x in (result.get("before_sig"), result.get("after_sig"),
                         result.get("reload_sig")) if x],
            {"entity_key": result.get("entity_key"),
             "affordance_key": result.get("key"),
             "before_contexts": result.get("before_contexts"),
             "after_contexts": result.get("after_contexts")},
        ))
    accepted = next((h for h in component.hypotheses
                     if h.kind == "PERSISTENT_CONTEXT_MEMBERSHIP"
                     and h.status == "SUPPORTED"), None)
    if accepted is None:
        return None
    return RefinementDecision(
        "ref-" + _id(component.id, accepted.id, result.get("action_step")),
        component.id, "ATTACH_CONTEXT_MEMBERSHIP", "PROVISIONAL",
        dict(accepted.target), accepted.id,
        [{"intervention": result}, *[asdict(e) for e in accepted.evidence]],
    )


def apply_correspondence_result(component: AmbiguityComponent, result: dict[str, Any]) -> RefinementDecision | None:
    if result.get("view_invariance_supported") is not True or result.get("equal_key_revealed") is not True:
        return None
    for h in component.hypotheses:
        h.evidence.append(EvidenceContribution(
            "VIEW_INVARIANCE_SUPPORT", "controlled_identity_correspondence_probe", result.get("step"),
            [x for x in (result.get("before_sig"), result.get("after_sig"), result.get("reload_sig")) if x],
            {"source_key": result.get("source_key"), "revealed_key": result.get("revealed_key")},
        ))
        if h.kind == "SAME_ENTITY_MENTION_SET":
            h.status = "SUPPORTED"
    accepted = next((h for h in component.hypotheses if h.kind == "SAME_ENTITY_MENTION_SET" and h.status == "SUPPORTED"), None)
    if accepted is None:
        return None
    target = dict(accepted.target)
    target["merge_compatible_mentions"] = True
    return RefinementDecision(
        "ref-" + _id(component.id, accepted.id, result.get("step")), component.id,
        "ASSOCIATE_MENTION_TYPE", "PROVISIONAL", target, accepted.id,
        [{"intervention": result}, *[asdict(e) for e in accepted.evidence]],
    )


def apply_matrix_record_result(component: AmbiguityComponent, result: dict[str, Any]) -> RefinementDecision | None:
    if result.get("view_invariance_supported") is not True or result.get("triple_revealed") is not True:
        return None
    accepted = next((h for h in component.hypotheses if h.kind == "RELATIONAL_RECORD_SPLIT"), None)
    if accepted is None:
        return None
    accepted.status = "SUPPORTED"
    accepted.evidence.append(EvidenceContribution(
        "VIEW_INVARIANCE_SUPPORT", "controlled_matrix_detail_probe", result.get("step"),
        [x for x in (result.get("before_sig"), result.get("after_sig"), result.get("reload_sig")) if x],
        {"anchor_key": result.get("anchor_key"), "context_key": result.get("context_key"),
         "target_key": result.get("target_key")},
    ))
    return RefinementDecision(
        "ref-" + _id(component.id, accepted.id, result.get("step")), component.id,
        "SPLIT_RELATIONAL_RECORD", "PROVISIONAL", dict(accepted.target), accepted.id,
        [{"intervention": result}, *[asdict(e) for e in accepted.evidence]],
    )


def write_counterexamples(run_dir: Path, counterexamples: list[Counterexample]) -> None:
    path = Path(run_dir) / COUNTEREXAMPLES_FILE
    path.write_text("".join(json.dumps(asdict(ce), sort_keys=True, default=str) + "\n" for ce in counterexamples))


def write_components(run_dir: Path, components: list[AmbiguityComponent]) -> None:
    path = Path(run_dir) / HYPOTHESES_FILE
    merged: dict[str, dict] = {}
    if path.exists():
        try:
            merged = {c["id"]: c for c in json.loads(path.read_text()).get("components", [])}
        except (json.JSONDecodeError, KeyError, TypeError):
            merged = {}
    merged.update({c.id: asdict(c) for c in components})
    path.write_text(json.dumps({"version": 1, "components": list(merged.values())}, indent=1))


def read_components(run_dir: Path) -> list[AmbiguityComponent]:
    data = json.loads((Path(run_dir) / HYPOTHESES_FILE).read_text())
    out = []
    for c in data.get("components", []):
        hs = []
        for h in c["hypotheses"]:
            h_data = dict(h)
            ev = [EvidenceContribution(**e) for e in h_data.pop("evidence", [])]
            hs.append(LocalHypothesis(**h_data, evidence=ev))
        out.append(AmbiguityComponent(c["id"], c["counterexample_steps"], c["scope"], hs, c.get("selected_intervention")))
    return out


def write_decisions(run_dir: Path, decisions: list[RefinementDecision]) -> None:
    (Path(run_dir) / DECISIONS_FILE).write_text(json.dumps({"version": 2, "decisions": [asdict(d) for d in decisions]}, indent=1))


def read_decisions(run_dir: Path) -> list[dict[str, Any]]:
    path = Path(run_dir) / DECISIONS_FILE
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("decisions", [])


def load_decisions(run_dir: Path, include_provisional: bool = False) -> list[dict[str, Any]]:
    """Load canonical decisions, optionally including candidates under validation.

    ``SUPPORTED`` is the legacy spelling for a probe-supported decision.  It is treated
    as PROVISIONAL, never as canonical, so old development artifacts cannot silently
    bypass the independent-prediction gate.
    """
    allowed = {"VALIDATED"}
    if include_provisional:
        allowed.update({"PROVISIONAL", "SUPPORTED"})
    return [d for d in read_decisions(run_dir) if d.get("status") in allowed]


def configure_hypotheses(H, decisions: list[dict[str, Any]]) -> bool:
    """Install caller-authorized local choices before fitting; return merge policy."""
    merge_mentions = False
    for d in decisions:
        if d.get("kind") == "ASSOCIATE_MENTION_TYPE":
            t = d["target"]
            for assignment in t.get("mention_assignments", []):
                if "node" in assignment:
                    H.raw_mention_assignments[(assignment["sig"], assignment["node"])] = \
                        (assignment["target_template"], assignment["key"])
                else:
                    H.mention_type_assignments[(assignment["sig"], assignment["template"], assignment["key"])] = \
                        assignment["target_template"]
            merge_mentions = merge_mentions or bool(t.get("merge_compatible_mentions"))
            continue
        if d.get("kind") == "SPLIT_RELATIONAL_RECORD":
            H.record_splits.append(dict(d["target"]))
            continue
        if d.get("kind") == "ATTACH_CONTEXT_MEMBERSHIP":
            for assignment in d["target"].get("context_assignments", []):
                H.raw_context_assignments[(assignment["sig"], assignment["node"])] = (
                    assignment["target_template"], assignment["key"], assignment["context"],
                )
            merge_mentions = True
            continue
        if d.get("kind") != "ATTACH_PERSISTENT_WIDGET":
            continue
        t = d["target"]
        source = (t["source_template"], t["source_slot"])
        H.persistent_widgets.add(source)
        if t.get("target_template"):
            H.slot_attachments[source] = t["target_template"]
            if t.get("identity_policy") == "ENCLOSING_KEY_PLUS_MENTION_KEY":
                H.contextual_identity.add(t["target_template"])
        for alias in t.get("aliases", []):
            H.alias_map[(alias["template"], alias["from"])] = alias["to"]
        for override in t.get("key_overrides", []):
            H.key_overrides[(override["sig"], override["template"], override["from"])] = override["to"]
        merge_mentions = merge_mentions or bool(t.get("merge_compatible_mentions"))
    return merge_mentions
