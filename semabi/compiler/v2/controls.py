"""Latent control families: which surface controls are observations of one semantic action.

The action alphabet used to identify a control by the slot key its enclosing entity
instance assigns it (`combobox#0`) plus that entity's run-local type id.  That key is a
per-instance role ordinal, so it fails in both directions at once: two structurally
different controls in different unit templates of one entity type receive the *same*
identity (climbing's grade selector and a route card's wall selector), while two
renderings of the *same* control in one instance receive different ones.  The first kind
of error fabricates lifted semantics; the second fragments support.

A surface control occurrence is therefore treated the way a UI fragment is treated for
entities: as an observation of a latent family.  A family is described by evidence that
does not depend on the run:

* the interaction role (`combobox`, `button`, ...);
* the control's label with its data masked (`Close _`), when any constant token remains;
* the role path from the root of the innermost recurring unit that properly contains it.

Occurrences agreeing on all three are the same family across unit-template variants, but
only when the entity layer already judges those templates to be renderings of one kind of
thing -- a card rendered with and without an extra line is one card, and its buttons are
one control -- and only when their option vocabularies are not *disjoint*, which is
positive evidence that two different controls have been merged.  Merging therefore needs
agreement on structure, on the latent entity the control belongs to, and on values; any
one of them disagreeing splits, because a false merge fabricates lifted semantics while a
false split only fragments support.  The entity grouping is consulted as evidence, never
as identity: no type id enters a family descriptor.  Nothing here reads a control's effects, so family
identity remains available as selection evidence that later behavioural validation can
confirm or refute without circularity.  Nothing here reads entity type ids, hash order,
DOM node indices or per-instance ordinals, so the alphabet is stable across runs.

Controls outside every recurring unit (navigation, filters, global forms) keep the
identity they already had: view/sensing separation is unchanged by this module.

The families are a *model*, applied to pages the induction never read: `ControlFamilies.assign`
classifies a new page's controls by the same descriptor (`docs/v4_identity.md`).  Until it
existed, every held-out click on every application fell through to a per-instance ordinal.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.parse import WIDGETS, leaf_label
from semabi.compiler.v2.graph import tokens


def _digest(templates: frozenset[str]) -> str:
    import hashlib
    return hashlib.sha1("\u0000".join(sorted(templates)).encode()).hexdigest()[:6]


@dataclass(frozen=True)
class ControlDescriptor:
    """One surface control occurrence, in run-independent terms."""
    role: str
    label: str      # "" when the control carries no stable non-data label
    template: str   # template of the innermost recurring unit containing the control
    path: str       # role path from that unit's root


@dataclass
class ControlFamily:
    id: str
    role: str
    label: str
    path: str
    templates: frozenset[str] = frozenset()
    options: frozenset[str] = frozenset()
    occurrences: int = 0

    def descriptor(self) -> dict[str, Any]:
        """Run-independent description used to align families across runs."""
        return {"role": self.role, "label": self.label, "path": self.path,
                "templates": sorted(self.templates), "options_seen": len(self.options),
                "occurrences": self.occurrences}


def masked_label(node, data_tokens, *, is_data=None) -> str:
    """The control's label with its data masked, or "" when nothing but data remains.

    ``Close North Wall``, ``Bottle Cloister`` and ``Return ticket 4 (1 gal from North Wall
    out of Picnic)`` each carry an entity's name, and the first version of this blanked any
    label that did -- so all three, and ``Open North Wall`` and ``Disgorge Cloister`` with
    them, were label-less controls distinguished by nothing but the digest of their unit
    template, which the layers above then dropped.  Five hidden operators became one control.

    The name of an action is what is left of its label when the data is taken out of it, and
    that is a masking the abstraction already performs on every template: ``Close _``,
    ``Bottle _``, ``Return ticket _ gal from _ out of _``.  Only a label with no constant token
    at all is label-less.  ``is_data`` is the graph's judgement at this node where the caller
    has one -- so a word the corpus never saw, in a label where it saw names, is masked too
    (`Close Block 12` is `Close _`) -- and the frozen corpus vocabulary otherwise.
    """
    if is_data is None:
        is_data = data_tokens.__contains__
    parts: list[str] = []
    for t in tokens(leaf_label(node)):
        if not t[0].isalnum():
            continue      # punctuation is neither label nor data
        m = "_" if is_data(t) else t
        if m == "_" and parts and parts[-1] == "_":
            continue      # a run of data tokens is one slot
        parts.append(m)
    if all(p == "_" for p in parts):
        return ""
    return " ".join(parts)


def _judge(G, sig: str, node, data_tokens):
    """How to tell data from label at this node: the graph's positional judgement if it has one."""
    at = getattr(G, "is_data_at", None)
    if at is None:
        return None
    return lambda t: at(sig, node.i, t)


def rendered_name(role: str, label: str, path: str) -> str:
    return f"{role}:{label}" if label else f"{role}#{path}"


def identity(slot: str) -> str:
    """What names a control, from a family id, a static slot key or a locator slot.

    Three kinds of string reach the behavioural layers as a control's identity, and they
    have to be compared on one footing:

    * ``button:Close@54dcf8`` -- a labelled family, disambiguated from another family with
      the same label and path that the entity layer keeps apart.  The label is the
      interface's own name for the action, and the layers above have always pooled these;
      the digest is dropped.
    * ``button#button@bb8f76`` -- a label-less family.  Nothing but its template family
      names it, so the digest *is* the identity and stays.  Dropping it pooled blend's
      ``Open`` buttons with every other label-less button at the same path.
    * ``button:Walls@57`` -- a static slot key whose ``@`` carries a node index, dropped.
    """
    head, sep, tail = slot.partition("@")
    if not sep:
        return slot
    if ":" in head or tail.isdigit():
        return head
    return slot


def _unit_root(units: dict, obs, node) -> int:
    """The innermost recurring unit that *properly* contains this control, or the control
    itself when it is a unit and nothing encloses it, or -1.

    A button whose whole name is data -- a ship's name, `Open North Wall` where `Open` is
    also a cell value -- recurs with a varying filling and so is a unit in its own right.
    Read as its own innermost unit its descriptor says nothing but `button[_]` at path
    `button`, and every such button on the page, whichever entity's row it sits in, is one
    family: on harbour 477 occurrences of buttons naming ships, berths and pilots.  Where in a
    recurring structure a control sits is what the descriptor is for, so the unit that
    encloses it is the one to read.
    """
    root = node.parent
    while root >= 0 and root not in units:
        root = obs.node(root).parent
    if root >= 0:
        return root
    return node.i if node.i in units else -1


def _components(members: list[str], vocabulary: dict[str, frozenset[str]],
                entity_group: dict[str, Any]) -> list[list[str]]:
    """Partition templates that share a role/label/path into families.

    Two templates may hold the same control only if the entity layer groups them into one
    latent entity -- otherwise they are different things that happen to expose a control at
    the same place -- and only if their option vocabularies are not disjoint.  Two
    renderings of one control share values; two different controls at the same path do
    not.  A control without options never splits on the value evidence alone."""
    parent = {t: t for t in members}

    def find(t: str) -> str:
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    for i, a in enumerate(members):
        for b in members[i + 1:]:
            ga, gb = entity_group.get(a), entity_group.get(b)
            # Two entity types are positive evidence that two same-shaped controls are two
            # things.  A unit the entity layer does not read as an entity at all -- a page,
            # a form -- is no evidence either way, and splitting on it fragmented blend's
            # `Record draw` seven ways by page-template variant.
            compatible_entity = ga is None or gb is None or ga == gb
            va, vb = vocabulary[a], vocabulary[b]
            compatible_values = not va or not vb or bool(va & vb)
            if compatible_entity and compatible_values:
                parent[find(a)] = find(b)
    groups: dict[str, list[str]] = defaultdict(list)
    for t in members:
        groups[find(t)].append(t)
    return [sorted(g) for g in sorted(groups.values(), key=lambda g: sorted(g))]


@dataclass
class ControlFamilies:
    """The families of one run plus the occurrence -> family map."""
    families: dict[str, ControlFamily] = field(default_factory=dict)
    by_node: dict[str, dict[int, str]] = field(default_factory=dict)   # sig -> node -> family id
    by_descriptor: dict[ControlDescriptor, str] = field(default_factory=dict)
    by_key: dict[tuple[str, str, str], list[str]] = field(default_factory=dict)

    def of(self, sig: str, node: int) -> str | None:
        return self.by_node.get(sig, {}).get(node)

    def assign(self, H, obs, sig: str, data_tokens: set[str]) -> dict[int, str]:
        """Node -> family, for a page these families were not induced from.

        ``by_node`` is a memo of the pages the induction read.  A frozen model applied to a
        page it never saw has to *classify* the page's controls by the same run-independent
        descriptor the families were built from, or the families are not a model at all --
        and until this existed they were not: every held-out click on every application fell
        through to its per-instance ordinal, so ``Close``, ``Bottle`` and ``Return ticket``
        were all ``button#0`` while the prefix had fitted them under their families.

        Exact descriptor first.  A unit template the induction never saw falls back on the
        role, label and path: one family with those is the answer; several are told apart by
        the entity group the frozen hypotheses assign the new template, where they assign one;
        otherwise the rendered name alone, which is what the layers above compare labelled
        families by anyway, and which for a label-less control names nothing fitted.
        """
        units = {ui.root: ui for ui in H.parse_units(sig)}
        out: dict[int, str] = {}
        for node in obs.nodes:
            if node.role not in WIDGETS:
                continue
            root = _unit_root(units, obs, node)
            if root < 0:
                continue      # outside every recurring unit: the caller names it
            d = ControlDescriptor(node.role,
                                  masked_label(node, data_tokens,
                                               is_data=_judge(getattr(H, "G", None), sig, node, data_tokens)),
                                  units[root].template, H._relpath(obs, root, node.i))
            fid = self.by_descriptor.get(d)
            if fid is None:
                fid = self._nearest(d, H.tid_of_template.get(d.template), H.tid_of_template)
            out[node.i] = fid
        return out

    def _nearest(self, d: ControlDescriptor, group, tid_of_template: dict) -> str:
        candidates = self.by_key.get((d.role, d.label, d.path), [])
        if len(candidates) == 1:
            return candidates[0]
        if candidates and group is not None:
            same = [f for f in candidates
                    if any(tid_of_template.get(t) == group for t in self.families[f].templates)]
            if len(same) == 1:
                return same[0]
        return rendered_name(d.role, d.label, d.path)

    def report(self) -> dict[str, Any]:
        return {"families": {fid: f.descriptor() for fid, f in sorted(self.families.items())}}


def induce(G, H, data_tokens: set[str]) -> ControlFamilies:
    """Group every control occurrence in the observation graph into latent families."""
    occurrences: dict[ControlDescriptor, dict[str, Any]] = defaultdict(
        lambda: {"n": 0, "options": set(), "nodes": []})
    for sig in sorted(G.obs):
        obs = G.obs[sig]
        units = {ui.root: ui for ui in H.parse_units(sig)}
        for node in obs.nodes:
            if node.role not in WIDGETS:
                continue
            root = _unit_root(units, obs, node)
            if root < 0:
                continue      # outside every recurring unit: keeps its existing identity
            descriptor = ControlDescriptor(
                node.role, masked_label(node, data_tokens, is_data=_judge(G, sig, node, data_tokens)),
                units[root].template, H._relpath(obs, root, node.i),
            )
            row = occurrences[descriptor]
            row["n"] += 1
            row["options"].update(str(o) for o in (node.options or ()))
            row["nodes"].append((sig, node.i))

    # Which templates the entity layer already treats as one kind of thing.  Used only to
    # decide whether two structurally matching occurrences may share a family; the group
    # itself never appears in a family's identity.
    entity_group = {t: H.tid_of_template.get(t) for d in occurrences for t in (d.template,)}

    by_key: dict[tuple[str, str, str], list[ControlDescriptor]] = defaultdict(list)
    for descriptor in occurrences:
        by_key[(descriptor.role, descriptor.label, descriptor.path)].append(descriptor)

    families: dict[str, ControlFamily] = {}
    by_node: dict[str, dict[int, str]] = defaultdict(dict)
    rendered: dict[str, list[ControlFamily]] = defaultdict(list)
    for key in sorted(by_key):
        role, label, path = key
        descriptors = by_key[key]
        vocabulary = {d.template: frozenset(occurrences[d]["options"]) for d in descriptors}
        by_template = {d.template: d for d in descriptors}
        for group in _components(sorted(by_template), vocabulary, entity_group):
            members = [by_template[t] for t in group]
            name = rendered_name(role, label, path)
            family = ControlFamily(
                name, role, label, path,
                frozenset(group),
                frozenset().union(*(frozenset(occurrences[d]["options"]) for d in members)),
                sum(occurrences[d]["n"] for d in members),
            )
            rendered[name].append(family)
            for d in members:
                for sig, node in occurrences[d]["nodes"]:
                    by_node[sig][node] = family   # replaced by the final id below
    # Deterministic disambiguation only where one rendering covers several families.  The
    # suffix is a digest of the family's own templates, so it does not depend on which
    # other families the run happened to observe; cross-run alignment matches descriptors,
    # not these strings.
    for name, group in sorted(rendered.items()):
        group.sort(key=lambda f: sorted(f.templates))
        for family in group:
            family.id = name if len(group) == 1 else f"{name}@{_digest(family.templates)}"
            families[family.id] = family
    for sig, nodes in by_node.items():
        for node, family in list(nodes.items()):
            nodes[node] = family.id
    by_descriptor: dict[ControlDescriptor, str] = {}
    by_key: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for fid, family in families.items():
        by_key[(family.role, family.label, family.path)].append(fid)
        for t in family.templates:
            by_descriptor[ControlDescriptor(family.role, family.label, t, family.path)] = fid
    return ControlFamilies(families, dict(by_node), by_descriptor,
                           {k: sorted(v) for k, v in by_key.items()})
