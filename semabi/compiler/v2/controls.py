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
* the control's stable label, when it has one that is not entity data;
* the role path from the root of the innermost recurring unit that contains it.

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


def _stable_label(node, data_tokens: set[str]) -> str:
    label = leaf_label(node)
    if not label or set(tokens(label)) & data_tokens:
        return ""      # entity data, not a control name
    return label


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
            same_entity = (entity_group.get(a) is not None and entity_group.get(a) == entity_group.get(b))
            va, vb = vocabulary[a], vocabulary[b]
            compatible_values = not va or not vb or bool(va & vb)
            if same_entity and compatible_values:
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

    def of(self, sig: str, node: int) -> str | None:
        return self.by_node.get(sig, {}).get(node)

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
            root = node.i
            while root >= 0 and root not in units:
                root = obs.node(root).parent
            if root < 0:
                continue      # outside every recurring unit: keeps its existing identity
            descriptor = ControlDescriptor(
                node.role, _stable_label(node, data_tokens), units[root].template,
                H._relpath(obs, root, node.i),
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
            name = f"{role}:{label}" if label else f"{role}#{path}"
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
    return ControlFamilies(families, dict(by_node))
