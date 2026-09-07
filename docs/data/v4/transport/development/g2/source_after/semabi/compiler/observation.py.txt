"""Observation representation: a flattened tree of visible UI nodes."""
from __future__ import annotations

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

    def key(self) -> tuple:
        return (self.role, self.name, self.value, self.checked, tuple(self.options or ()), self.placeholder, self.current)

    def to_json(self) -> dict:
        d = {"i": self.i, "parent": self.parent, "role": self.role, "name": self.name}
        for k in ("value", "checked", "options", "placeholder", "current"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        d["bbox"] = list(self.bbox)
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Node":
        return cls(d["i"], d["parent"], d["role"], d["name"], d.get("value"), d.get("checked"),
                   d.get("options"), d.get("placeholder"), d.get("current"), tuple(d.get("bbox", (0, 0, 0, 0))))


@dataclass
class Observation:
    nodes: list[Node]
    url: str = ""
    _children: dict[int, list[int]] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self._children = {}
        for n in self.nodes:
            self._children.setdefault(n.parent, []).append(n.i)

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

    def structural_signature(self) -> str:
        """Hash of (role, name, value, checked, structure) ignoring bbox."""
        parts = [(n.parent, *n.key()) for n in self.nodes]
        return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]

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
            lines.append(f"{'  ' * depth[n.i]}[{n.i}] {n.role} {n.name!r} {' '.join(extra)}".rstrip())
        return "\n".join(lines)
