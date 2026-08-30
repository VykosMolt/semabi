"""Structural parsing of observations into anonymous typed instances.

No label semantics are used. Instances are found as groups of structurally
similar siblings (wrapper-induction style) and clustered across observations
into anonymous types. Each instance exposes slots (leaf values at relative
role paths) and context slots (varying leaves of its non-instance ancestors).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.observation import Node, Observation

WIDGETS = {"button", "link", "checkbox", "radio", "combobox", "textbox"}
# Live regions are not here.  `status` was added to this set once, to stop the application's
# account of the last action being dropped before any learner saw it, and that was right about
# the evidence and wrong about where to put it: as an ordinary leaf the sentence becomes a slot
# -- of the page's view state where the node sits alone, of a *unit* where it sits inside one,
# which makes a status-only change a domain change and produces operators whose effect is
# `attr:status#0(?o) := 'Closed Creek Bed'`.  A live region is what the transition *returned*;
# it belongs on the transition, and `semabi.compiler.v4.emission` is where it now goes.
#
# `alert` stays, and that is a compatibility decision rather than a claim.  It is the same kind
# of live region and by this argument does not belong in the state either, but it is inside
# frozen V0/V1 history on a corpus with no `status` anywhere, and moving those results is not
# what this change is about.  `emission.LIVE_ROLES` reads both.
DATA_ROLES = {"text", "heading", "cell", "listitem", "alert"}
LEAF_ROLES = WIDGETS | DATA_ROLES

SIM_THRESHOLD = 0.5


def leaf_value(n: Node) -> Any:
    if n.role in ("checkbox", "radio"):
        return n.checked
    if n.role in ("combobox", "textbox"):
        return n.value
    if n.role in ("button", "link"):
        return True
    return n.name


def leaf_label(n: Node) -> str:
    """Static identity text of a leaf (its name for widgets/data, placeholder for textboxes)."""
    if n.role == "textbox":
        return n.placeholder or ""
    if n.role == "combobox":
        return ""
    return n.name


# --------------------------------------------------------------------------
# Per-observation instance detection
# --------------------------------------------------------------------------

def _rolepaths(obs: Observation, root: int) -> frozenset[str]:
    out = set()
    stack = [(root, obs.node(root).role)]
    while stack:
        i, p = stack.pop()
        out.add(p)
        for c in obs.children(i):
            stack.append((c, p + "/" + obs.node(c).role))
    return frozenset(out)


def _leafpairs(obs: Observation, root: int) -> frozenset[tuple[str, str]]:
    out = set()
    stack = [(root, obs.node(root).role)]
    while stack:
        i, p = stack.pop()
        n = obs.node(i)
        if n.role in LEAF_ROLES and leaf_label(n):
            out.add((p, leaf_label(n)))
        for c in obs.children(i):
            stack.append((c, p + "/" + obs.node(c).role))
    return frozenset(out)


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def _buttons(leaves: frozenset) -> frozenset:
    return frozenset(l for l in leaves if l[0].rsplit("/", 1)[-1] == "button")


def _similar(sa, la, sb, lb) -> bool:
    if _jaccard(sa, sb) < SIM_THRESHOLD:
        return False
    if la & lb:
        return True
    if sa != sb:
        return False
    ba, bb = _buttons(la), _buttons(lb)
    # identical shapes but disjoint button labels: different widgets, not instances
    return not (ba and bb and not (ba & bb))


@dataclass
class TypeTemplate:
    tid: int
    role: str
    anchor: str  # role path from document root to instance root (indices stripped)
    shapes: set[frozenset] = field(default_factory=set)
    labels: set[tuple[str, str]] = field(default_factory=set)  # leaf pairs seen in >=2 instances
    n_instances: int = 0

    def matches(self, role: str, anchor: str, shape: frozenset, leaves: frozenset) -> bool:
        if role != self.role or anchor != self.anchor:
            return False
        best = max((_jaccard(shape, s) for s in self.shapes), default=0.0)
        if best < SIM_THRESHOLD:
            return False
        if leaves & self.labels:
            return True
        if shape not in self.shapes:
            return False
        b = _buttons(leaves)
        return not (b and _buttons(frozenset(self.labels)) and not (b & self.labels))


@dataclass
class Instance:
    root: int
    tid: int
    parent: int | None  # index of enclosing instance in ParsedObs.instances
    slots: dict[str, tuple[str, Any]]  # relpath -> (label, value)
    context: dict[str, tuple[str, Any]]  # non-instance-ancestor leaves (absolute keys)
    anchor: str
    positional: bool = False  # the key repeated among siblings and position told them apart

    @property
    def values(self) -> dict[str, Any]:
        return {k: v for k, (_, v) in self.slots.items()}


@dataclass
class ParsedObs:
    obs: Observation
    instances: list[Instance]
    statics: dict[str, tuple[str, Any]]  # leaves outside any instance, keyed by absolute indexed path
    node_instance: dict[int, int]  # node index -> instance index (innermost)
    node_key: dict[int, str] = field(default_factory=dict)  # leaf node index -> slot key

    def instances_of(self, tid: int) -> list[Instance]:
        return [x for x in self.instances if x.tid == tid]

    def instance_of_node(self, i: int) -> int | None:
        return self.node_instance.get(i)


class Parser:
    """Stateful across observations: accumulates type templates."""

    def __init__(self):
        self.templates: list[TypeTemplate] = []
        self.data_positions: set[tuple[int, str]] = set()  # (tid, rolepath) where typed tokens appeared
        self.typed_tokens: set[str] = set()

    def fit(self, observations, typed_tokens) -> None:
        """Pre-pass: build templates and mark widget positions that ever carried
        an agent-typed token (hence data, not labels)."""
        self.typed_tokens = set(typed_tokens)
        for obs in observations:
            self.detect_roots(obs)
        # per (tid, rolepath): were labels ever shared by two co-present instances? were there >= 2 instances?
        shared_ever: set[tuple[int, str]] = set()
        multi_ever: set[tuple[int, str]] = set()
        for obs in observations:
            roots = self.detect_roots(obs)
            owner: dict[int, int] = {}
            root_of: dict[int, int] = {}
            relpath: dict[int, str] = {}
            labels_at: dict[tuple[int, str], list[tuple[int, str]]] = {}
            for i, n in enumerate(obs.nodes):
                p = n.parent
                if i in roots:
                    owner[i] = roots[i]
                    root_of[i] = i
                    relpath[i] = n.role
                    continue
                if p >= 0 and p in owner:
                    owner[i] = owner[p]
                    root_of[i] = root_of[p]
                    relpath[i] = relpath[p] + "/" + n.role
                    if n.role in WIDGETS and leaf_label(n):
                        if leaf_label(n) in self.typed_tokens:
                            self.data_positions.add((owner[i], relpath[i]))
                        labels_at.setdefault((owner[i], relpath[i]), []).append((root_of[i], leaf_label(n)))
            for key, items in labels_at.items():
                labs = [l for _, l in items]
                if len(set(r for r, _ in items)) >= 2:
                    multi_ever.add(key)
                    if len(labs) != len(set(labs)):
                        shared_ever.add(key)
        # labels always pairwise distinct across co-present instances -> data (e.g. links named after objects)
        for key in multi_ever - shared_ever:
            self.data_positions.add(key)

    # ---- template registry
    def _find_template(self, role, anchor, shape, leaves) -> TypeTemplate | None:
        for t in self.templates:
            if t.matches(role, anchor, shape, leaves):
                return t
        return None

    def _register_group(self, role: str, anchor: str, members: list[tuple[frozenset, frozenset]]) -> TypeTemplate:
        t = None
        for shape, leaves in members:
            t = self._find_template(role, anchor, shape, leaves)
            if t:
                break
        if t is None:
            t = TypeTemplate(len(self.templates), role, anchor)
            self.templates.append(t)
        # shared labels = leaf pairs in >= 2 members (or in the template already)
        from collections import Counter
        cnt = Counter(p for _, leaves in members for p in leaves)
        for shape, leaves in members:
            t.shapes.add(shape)
            t.n_instances += 1
        for p, c in cnt.items():
            if c >= 2:
                t.labels.add(p)
        return t

    # ---- detection
    def _anchor(self, obs: Observation, i: int) -> str:
        return "/".join(obs.node(a).role for a in reversed(obs.ancestors(i))) + "/" + obs.node(i).role

    def detect_roots(self, obs: Observation) -> dict[int, int]:
        """Return node index -> template id for instance roots."""
        roots: dict[int, int] = {}
        shape_cache: dict[int, frozenset] = {}
        leaf_cache: dict[int, frozenset] = {}

        def shape(i):
            if i not in shape_cache:
                shape_cache[i] = _rolepaths(obs, i)
            return shape_cache[i]

        def leaves(i):
            if i not in leaf_cache:
                leaf_cache[i] = _leafpairs(obs, i)
            return leaf_cache[i]

        # pass 1: sibling repeat groups (top-down order by node index)
        for p in range(len(obs.nodes)):
            kids = obs.children(p)
            if len(kids) < 2:
                continue
            by_role: dict[str, list[int]] = {}
            for c in kids:
                n = obs.node(c)
                if n.role in ("alert", "option") or not obs.children(c):
                    continue
                by_role.setdefault(n.role, []).append(c)
            for role, members in by_role.items():
                if len(members) < 2:
                    continue
                # single-linkage components
                comp = {m: m for m in members}

                def find(x):
                    while comp[x] != x:
                        comp[x] = comp[comp[x]]
                        x = comp[x]
                    return x

                for a_i, a in enumerate(members):
                    for b in members[a_i + 1:]:
                        if _similar(shape(a), leaves(a), shape(b), leaves(b)):
                            comp[find(a)] = find(b)
                groups: dict[int, list[int]] = {}
                for m in members:
                    groups.setdefault(find(m), []).append(m)
                for g in groups.values():
                    if len(g) < 2:
                        continue
                    anchor = self._anchor(obs, g[0])
                    t = self._register_group(role, anchor, [(shape(m), leaves(m)) for m in g])
                    for m in g:
                        roots[m] = t.tid
        # pass 2: singletons matching known templates
        for i, n in enumerate(obs.nodes):
            if i in roots or n.role in ("alert", "option") or not obs.children(i):
                continue
            if n.parent < 0:
                continue
            anchor = self._anchor(obs, i)
            t = self._find_template(n.role, anchor, shape(i), leaves(i))
            if t is not None:
                roots[i] = t.tid
                t.shapes.add(shape(i))
                t.n_instances += 1
        return roots

    def parse(self, obs: Observation) -> ParsedObs:
        roots = self.detect_roots(obs)
        # innermost instance for every node
        node_instance: dict[int, int] = {}
        instances: list[Instance] = []
        root_to_idx: dict[int, int] = {}
        for r in sorted(roots):
            root_to_idx[r] = len(instances)
            inst = Instance(r, roots[r], None, {}, {}, self._anchor(obs, r))
            if obs.node(r).name:
                inst.slots[f"{obs.node(r).role}@self"] = (obs.node(r).name, obs.node(r).name)
            instances.append(inst)
        for i in range(len(obs.nodes)):
            p = obs.node(i).parent
            if i in root_to_idx:
                node_instance[i] = root_to_idx[i]
                if p >= 0 and p in node_instance:
                    instances[root_to_idx[i]].parent = node_instance[p]
            elif p >= 0 and p in node_instance:
                node_instance[i] = node_instance[p]
        # slots: widget leaves keyed by their static label (if the label is a shared label of
        # the type), data leaves / unlabeled widgets keyed by role order within the owner.
        statics: dict[str, tuple[str, Any]] = {}
        node_key: dict[int, str] = {}
        relpath: dict[int, str] = {}
        rolecount: dict[tuple[int | None, str], int] = {}
        for i, n in enumerate(obs.nodes):
            p = n.parent
            if i in root_to_idx or p < 0:
                relpath[i] = ""
                continue
            relpath[i] = (relpath[p] + "/" + n.role) if relpath[p] else n.role
            if not (n.role in LEAF_ROLES and (leaf_label(n) or n.role in WIDGETS or n.role == "alert")):
                continue
            owner = node_instance.get(i)
            lab = leaf_label(n)
            shared = False
            if owner is not None and n.role in WIDGETS and lab:
                rp = obs.node(instances[owner].root).role + "/" + relpath[i]
                shared = (instances[owner].tid, rp) not in self.data_positions and lab not in self.typed_tokens
            elif owner is None and n.role in WIDGETS and lab:
                shared = True  # static page widgets are labels by construction
            if shared:
                key = f"{n.role}:{lab}"
                entry = (lab, leaf_value(n))
            else:
                k = rolecount.get((owner, n.role), 0)
                rolecount[(owner, n.role)] = k + 1
                key = f"{n.role}@{k}"
                entry = (lab, n.name if n.role in ("button", "link") else leaf_value(n))
            if owner is None:
                statics[key] = entry
            else:
                instances[owner].slots[key] = entry
            relpath[i] = key  # leaves: remember key for context lookup
            node_key[i] = key
        # context: static leaves whose parent container is an ancestor of the instance root
        for inst in instances:
            anc = set(obs.ancestors(inst.root))
            ctx = {}
            for i, n in enumerate(obs.nodes):
                if i in node_instance or n.parent < 0:
                    continue
                key = relpath.get(i)
                if key in statics and n.parent in anc:
                    ctx[key] = statics[key]
            inst.context = ctx
        return ParsedObs(obs, instances, statics, node_instance, node_key)


def describe(po: ParsedObs) -> str:
    lines = []
    for k, inst in enumerate(po.instances):
        par = f" in #{inst.parent}" if inst.parent is not None else ""
        lines.append(f"#{k} T{inst.tid} root={inst.root}{par} anchor={inst.anchor}")
        for path, (lab, val) in inst.slots.items():
            lines.append(f"      {path} [{lab!r}] = {val!r}")
        if inst.context:
            lines.append(f"      ctx: {inst.context}")
    lines.append("statics: " + ", ".join(f"{k}={v}" for k, v in po.statics.items()))
    return "\n".join(lines)
