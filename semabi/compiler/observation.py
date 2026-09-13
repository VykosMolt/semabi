"""Observation representation: a flattened tree of visible UI nodes."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from dataclasses import dataclass, field

INTERACTIVE = {"button", "link", "textbox", "checkbox", "radio", "combobox"}


@dataclass
class Node:
    i: int
    parent: int  # -1 for root
    role: str
    name: str  # accessible name / text
    value: str | None = None
    checked: bool | None = None
    options: list[str] | None = None
    placeholder: str | None = None
    current: bool | None = None
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)
    expanded: bool | None = None
    busy: bool | None = None
    row_count: int | None = None
    row_index: int | None = None
    set_size: int | None = None
    pos_in_set: int | None = None
    selected: bool | None = None
    pressed: bool | str | None = None

    def key(self) -> tuple:
        legacy = (self.role, self.name, self.value, self.checked, tuple(self.options or ()), self.placeholder, self.current)
        scope = tuple((k, getattr(self, k)) for k in SCOPE_FIELDS if getattr(self, k) is not None)
        # Keep the signatures of existing corpora stable when no scope was observed.
        return legacy + (scope,) if scope else legacy

    def to_json(self) -> dict:
        d = {"i": self.i, "parent": self.parent, "role": self.role, "name": self.name}
        for k in ("value", "checked", "options", "placeholder", "current", *SCOPE_FIELDS):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        d["bbox"] = list(self.bbox)
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Node":
        return cls(d["i"], d["parent"], d["role"], d["name"], d.get("value"), d.get("checked"),
                   d.get("options"), d.get("placeholder"), d.get("current"), tuple(d.get("bbox", (0, 0, 0, 0))),
                   **{k: d.get(k) for k in SCOPE_FIELDS})


SCOPE_FIELDS = ("expanded", "busy", "row_count", "row_index", "set_size", "pos_in_set", "selected", "pressed")
COLLECTION_ROLES = {"table", "grid", "treegrid", "list", "listbox", "tree"}


@dataclass
class Observation:
    nodes: list[Node]
    url: str = ""
    _children: dict[int, list[int]] = field(default_factory=dict, repr=False)
    _signature: str | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        self._children = {}
        self._signature = None
        for n in self.nodes:
            self._children.setdefault(n.parent, []).append(n.i)

    def __deepcopy__(self, memo):
        # A copy is a new observation: whatever it is mutated into afterwards
        # (a hypothetical widget value) gets its own signature, not this one's.
        return Observation(deepcopy(self.nodes, memo), self.url)

    def children(self, i: int) -> list[int]:
        return self._children.get(i, [])

    def node(self, i: int) -> Node:
        return self.nodes[i]

    def interactive(self) -> list[Node]:
        return [n for n in self.nodes if n.role in INTERACTIVE]

    def ancestors(self, i: int) -> list[int]:
        out = []
        p = self.nodes[i].parent
        while p >= 0:
            out.append(p)
            p = self.nodes[p].parent
        return out

    def subtree(self, i: int) -> list[int]:
        out = [i]
        stack = [i]
        while stack:
            x = stack.pop()
            for c in self.children(x):
                out.append(c)
                stack.append(c)
        return out

    def collection_scope(self, root: int) -> tuple | None:
        """The visible query/selection context of one rendered collection.

        This is an observation-local scope, not a global object identity. Member controls
        are excluded because changing the members must not itself change the query scope.
        The caller must separately establish correspondence of the collection's holder.
        """
        holder = self.node(root)
        if holder.role not in COLLECTION_ROLES:
            return None
        members = self.collection_members(root)
        inside_members = {i for member in members for i in self.subtree(member.i)}
        context = tuple((n.role, n.name, n.value, n.checked, n.current, n.expanded, n.selected, n.pressed)
                        for n in self.nodes if n.i not in inside_members
                        and (n.role in INTERACTIVE or n.expanded is not None
                             or n.selected is not None or n.pressed is not None))
        return holder.role, holder.name, context

    def collection_members(self, root: int) -> list[Node]:
        role = "row" if self.node(root).role in {"table", "grid", "treegrid"} else {
            "list": "listitem", "listbox": "option", "tree": "treeitem",
        }.get(self.node(root).role)
        return [n for n in self.nodes if n.role == role and root in self.ancestors(n.i)
                and not any(self.node(a).role in COLLECTION_ROLES
                            for a in self.ancestors(n.i)[:self.ancestors(n.i).index(root)])]

    def complete_collection(self, root: int) -> bool:
        """Explicit ARIA enumeration covers this scope; rendered multiplicity does not.

        rowcount/rowindex include header rows. Unknown totals, missing indices, nested
        collections, busy or collapsed regions cannot establish absence. The declaration
        is interface evidence, not a guarantee about hidden application state.
        """
        if self.collection_scope(root) is None:
            return False
        affected = self.subtree(root) + self.ancestors(root)
        if any(self.node(i).busy is True or self.node(i).expanded is False for i in affected):
            return False
        members = self.collection_members(root)
        holder = self.node(root)
        if holder.role in {"table", "grid", "treegrid"}:
            total = holder.row_count
            indices = [n.row_index for n in members]
        else:
            totals = {n.set_size for n in members}
            if len(totals) != 1:
                return False
            total = next(iter(totals))
            indices = [n.pos_in_set for n in members]
        return (type(total) is int and total >= 0 and len(indices) == total
                and all(type(i) is int for i in indices)
                and sorted(indices) == list(range(1, total + 1)))

    def structural_signature(self) -> str:
        """Hash of (role, name, value, checked, structure) ignoring bbox.

        Computed once per observation: the learner asks for it on every parse of
        every page, and a fit on a history of nine-hundred-node pages spent its
        hours hashing the same nodes again."""
        if self._signature is None:
            parts = [(n.parent, *n.key()) for n in self.nodes]
            self._signature = hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]
        return self._signature

    def texts(self) -> set[str]:
        out = set()
        for n in self.nodes:
            if n.name:
                out.add(n.name)
            if n.value:
                out.add(n.value)
        return out

    def to_json(self) -> dict:
        return {"url": self.url, "nodes": [n.to_json() for n in self.nodes]}

    @classmethod
    def from_json(cls, d: dict) -> "Observation":
        return cls([Node.from_json(n) for n in d["nodes"]], d.get("url", ""))

    def render(self, max_nodes: int = 400) -> str:
        """Human/LLM readable indented dump."""
        depth = {}
        lines = []
        for n in self.nodes[:max_nodes]:
            depth[n.i] = 0 if n.parent < 0 else depth[n.parent] + 1
            extra = []
            if n.value is not None:
                extra.append(f"value={n.value!r}")
            if n.checked is not None:
                extra.append(f"checked={n.checked}")
            if n.options is not None:
                extra.append(f"options={n.options}")
            if n.placeholder is not None:
                extra.append(f"placeholder={n.placeholder!r}")
            if n.current:
                extra.append("current")
            for key in SCOPE_FIELDS:
                if getattr(n, key) is not None:
                    extra.append(f"{key}={getattr(n, key)!r}")
            lines.append(f"{'  ' * depth[n.i]}[{n.i}] {n.role} {n.name!r} {' '.join(extra)}".rstrip())
        return "\n".join(lines)
