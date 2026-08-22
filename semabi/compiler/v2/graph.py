"""Observation graph: per-node structural descriptors and text templates.

No unit detector lives here. The graph exposes, for every node of every
observation, (a) a *shape* (roles of the subtree), (b) a *template* (shape +
the label tokens that are constant across all nodes sharing the shape at the
same structural position), (c) the *data tokens* (the tokens that vary), so
that later hypotheses can be stated over recurring templates wherever they
occur: among siblings, across views, or across time.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from semabi.compiler.observation import Node, Observation

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-']*|[^\sA-Za-z0-9]")
LEAF = {"button", "link", "checkbox", "radio", "combobox", "textbox", "text", "heading", "cell", "listitem", "alert", "status", "group"}


def tokens(text: str) -> list[str]:
    out = []
    for t in TOKEN_RE.findall(text or ""):
        # sentence punctuation glued to a word ("Ewer.") is not part of the value; initials ("T.S.") are
        if t.endswith(".") and any(c.islower() for c in t):
            out.append(t.rstrip("."))
            out.append(".")
        else:
            out.append(t)
    return out


def token_pattern(text: str) -> str:
    """Coarse shape of a text: one letter per token (N number, a word, p punctuation)."""
    out = []
    for t in tokens(text):
        out.append("N" if t[0].isdigit() else ("a" if t[0].isalnum() else "p"))
    return "".join(out)


def node_text(n: Node) -> str:
    if n.role in ("textbox", "combobox"):
        return n.value or ""
    return n.name or ""


@dataclass
class NodeDesc:
    obs: str  # observation signature
    i: int
    role: str
    path: str  # role path from root, indices stripped
    shape: str  # roles of the subtree in DFS order (own text excluded)
    own_tokens: list[str]
    depth: int
    children: list[int]
    parent: int


@dataclass
class TextTemplate:
    """Per structural position (role path + token pattern): the strings seen there."""
    position: str
    strings: Counter = field(default_factory=Counter)
    n: int = 0

    def varying_tokens(self) -> set[str]:
        """Tokens that vary across the distinct strings at this position (< 80% of them)."""
        if len(self.strings) < 2:
            return set()
        per = Counter()
        for s in self.strings:
            for t in set(tokens(s)):
                if t[0].isalnum():
                    per[t] += 1
        return {t for t, c in per.items() if c < 0.8 * len(self.strings)}


class ObsGraph:
    def __init__(self):
        self.nodes: dict[tuple[str, int], NodeDesc] = {}
        self.obs: dict[str, Observation] = {}
        self.templates: dict[str, TextTemplate] = {}  # position -> template
        self.position_of: dict[tuple[str, int], str] = {}
        self._in_nonwidget: set[str] = set()  # tokens seen in a non-widget text or an input value
        self._data: set[str] | None = None
        self.header: set[tuple[str, int]] = set()  # (sig, node) cells of a table's first row

    def data_set(self) -> set[str]:
        """Data tokens: numbers, and tokens that vary within a position, except tokens that
        only ever occur in static control labels (buttons/links whose text never appears in
        data text anywhere)."""
        if self._data is None:
            d = set()
            for tt in self.templates.values():
                d |= tt.varying_tokens()
            self._data = {t for t in d if t[0].isdigit() or t in self._in_nonwidget}
        return self._data

    # ------------------------------------------------------------------ build
    def add(self, sig: str, obs: Observation) -> None:
        if sig in self.obs:
            return
        self.obs[sig] = obs
        depth = {}
        paths = {}
        for n in obs.nodes:
            depth[n.i] = 0 if n.parent < 0 else depth[n.parent] + 1
            paths[n.i] = n.role if n.parent < 0 else paths[n.parent] + "/" + n.role
        # table header cells: the first row of a table (labels even when they vary between tables)
        for n in obs.nodes:
            if n.role == "table":
                rows = [x for x in obs.subtree(n.i) if obs.node(x).role == "row"]
                if rows:
                    for c in obs.children(rows[0]):
                        self.header.add((sig, c))
        shapes = {}
        for n in reversed(obs.nodes):
            ch = obs.children(n.i)
            shapes[n.i] = n.role + ("(" + ",".join(shapes[c] for c in ch) + ")" if ch else "")
        for n in obs.nodes:
            d = NodeDesc(sig, n.i, n.role, paths[n.i], shapes[n.i], tokens(node_text(n)), depth[n.i], list(obs.children(n.i)), n.parent)
            self.nodes[(sig, n.i)] = d
            # structural position of a text: role path + parent's shape (what surrounds it)
            pos = paths[n.i] + "|" + token_pattern(node_text(n))
            self.position_of[(sig, n.i)] = pos
            tt = self.templates.setdefault(pos, TextTemplate(pos))
            if node_text(n) and (sig, n.i) not in self.header:
                tt.strings[node_text(n)] += 1
                tt.n += 1
                if n.role not in ("button", "link", "checkbox", "radio") or n.role in ("textbox", "combobox"):
                    self._in_nonwidget.update(tokens(node_text(n)))
        self._data = None

    def is_data(self, t: str) -> bool:
        return t in self.data_set() or t[0].isdigit()

    def data_tokens(self, sig: str, i: int) -> list[str]:
        """Data *spans*: maximal runs of consecutive data tokens ("Ines Halli", "Two Sisters")."""
        if (sig, i) in self.header:
            return []
        n = self.obs[sig].node(i)
        out: list[str] = []
        run: list[str] = []
        for t in tokens(node_text(n)):
            if self.is_data(t):
                if run and run[-1][0].isdigit() != t[0].isdigit():
                    out.append(" ".join(run))  # a number next to a name is a different value
                    run = []
                run.append(t)
            else:
                if run:
                    out.append(" ".join(run))
                run = []
                if not t[0].isalnum() and t not in ("/", "·", "-", "—"):
                    pass
        if run:
            out.append(" ".join(run))
        return out

    def is_prose(self, sig: str, i: int) -> bool:
        """A sentence position: its strings use a vocabulary of >= 4 distinct constant words
        (feedback lines), or this string alone carries >= 3 constant words."""
        n = self.obs[sig].node(i)
        if len(self.labels(sig, i)) >= 3:
            return True
        tt = self.templates.get(self.position_of[(sig, i)])
        if tt is None:
            return False
        d = self.data_set()
        vocab = {t for st in tt.strings for t in tokens(st) if t[0].isalpha() and t not in d}
        return len(vocab) >= 4

    def labels(self, sig: str, i: int) -> set[str]:
        n = self.obs[sig].node(i)
        if (sig, i) in self.header:
            return set(tokens(node_text(n)))
        d = self.data_set()
        return {t for t in tokens(node_text(n)) if t not in d and not t[0].isdigit()}

    # ------------------------------------------------------------------ subtree template
    def subtree_template(self, sig: str, i: int) -> str:
        """Shape plus label tokens of every node in the subtree (data tokens removed)."""
        obs = self.obs[sig]
        parts = []
        stack = [i]
        while stack:
            x = stack.pop()
            n = obs.node(x)
            lab = self.labels(sig, x)
            txt = " ".join(t if t in lab else "_" for t in tokens(node_text(n)))  # (uncollapsed; units.py collapses)
            parts.append(f"{n.role}[{txt}]")
            stack.extend(reversed(obs.children(x)))
        return ";".join(parts)

    def subtree_template_text(self, sig: str, i: int) -> str:
        """Full text content of a subtree (for reload persistence checks)."""
        obs = self.obs[sig]
        return "|".join(node_text(obs.node(x)) for x in obs.subtree(i))

    def subtree_data(self, sig: str, i: int) -> list[tuple[int, str]]:
        """(node, data token) pairs inside the subtree."""
        obs = self.obs[sig]
        out = []
        stack = [i]
        while stack:
            x = stack.pop()
            for t in self.data_tokens(sig, x):
                out.append((x, t))
            stack.extend(reversed(obs.children(x)))
        return out
