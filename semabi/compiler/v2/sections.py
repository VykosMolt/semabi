"""Objects an interface renders as a run of siblings rather than as a subtree.

Objecthood is normally asked of a node: does its template recur with a filling that
varies? That cannot reach an object with no node of its own, such as a hall rendered as a
heading, a line of prose and a table, three times over, flat inside one group. No node has
the hall's extent, so no template recurs per hall.

The repair is to ask the same question of spans of siblings: a span runs from one boundary
template to the next, at least two spans under one parent share a shape, and their values
differ. A span of one is a subtree and is already handled.

Nothing here is about headings or prose. A card, fieldset or panel laid out flat passes
the same test; a run of form controls does not, because its labels are labels.

Spans that pass become real containers: a synthetic group is appended per span and its
members are reparented, so every layer above sees an ordinary node. The containers are
appended, never inserted, so existing node indices keep their meaning and a recorded
action still names the element it named.
"""
from __future__ import annotations

from collections import Counter

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.units import collapsed_template

MIN_SPANS = 2       # a shape seen once is not a recurring shape
ENABLED = True      # measured with and without; see docs/v4_sections.md


def _span_template(G, sig: str, members: list[int], memo: dict) -> str:
    parts: list[str] = []
    for m in members:
        t = collapsed_template(G, sig, m, memo)
        if parts and parts[-1] == t:
            continue      # repeated members count once, as for a node's children
        parts.append(t)
    return "|".join(parts)


def _span_filling(G, sig: str, members: list[int]) -> tuple:
    out: list[str] = []
    for m in members:
        out.extend(t for _, t in G.subtree_data(sig, m))
    return tuple(out)


def candidates(G, sig: str, memo: dict | None = None) -> list[dict]:
    """Sibling spans under one parent that answer the objecthood question a node would."""
    memo = {} if memo is None else memo
    obs = G.obs[sig]
    out: list[dict] = []
    for p in range(len(obs.nodes)):
        kids = obs.children(p)
        if len(kids) < 3:
            continue
        tm = [collapsed_template(G, sig, k, memo) for k in kids]
        best: dict | None = None
        for boundary, n in Counter(tm).items():
            if n < MIN_SPANS:
                continue
            at = [j for j, t in enumerate(tm) if t == boundary]
            raw = [kids[at[a]:(at[a + 1] if a + 1 < len(at) else len(kids))]
                   for a in range(len(at))]
            # The modal shape fixes the extent.  Without this the final span absorbs whatever
            # else the parent ends with -- in cellar, two unrelated form groups.
            shapes = Counter(_span_template(G, sig, s, memo) for s in raw)
            modal, seen = shapes.most_common(1)[0]
            if seen < MIN_SPANS:
                continue
            spans = []
            for s in raw:
                if _span_template(G, sig, s, memo) == modal:
                    spans.append(s)
                    continue
                for cut in range(len(s), 0, -1):     # trim a ragged tail back to the shape
                    if _span_template(G, sig, s[:cut], memo) == modal:
                        spans.append(s[:cut])
                        break
            if len(spans) < MIN_SPANS or all(len(s) == 1 for s in spans):
                continue
            fills = {_span_filling(G, sig, s) for s in spans}
            if len(fills) < MIN_SPANS or any(not f for f in fills):
                continue      # one shared filling is one object, no filling is chrome
            cand = {"parent": p, "boundary": boundary, "shape": modal, "spans": spans,
                    "covers": sum(len(s) for s in spans)}
            # Several boundaries describe the same periodic run at different offsets; the one
            # that accounts for most of the parent's children is the segmentation it supports.
            if best is None or (len(cand["spans"]), cand["covers"]) > (len(best["spans"]), best["covers"]):
                best = cand
        if best is not None:
            out.append(best)
    return out


def normalise(G, sig: str, obs: Observation) -> Observation:
    """The same observation with a container appended per accepted span.

    Returns the observation unchanged when nothing qualifies, which is every observation in
    three of the four applications.
    """
    if not ENABLED:
        return obs
    found = candidates(G, sig)
    if not found:
        return obs
    nodes = [Node(n.i, n.parent, n.role, n.name, n.value, n.checked,
                  list(n.options) if n.options is not None else None,
                  n.placeholder, n.current, n.bbox) for n in obs.nodes]
    nxt = len(nodes)
    for cand in found:
        for members in cand["spans"]:
            box = Node(nxt, cand["parent"], "group", "")
            nodes.append(box)
            for m in members:
                nodes[m].parent = nxt
            nxt += 1
    return Observation(nodes, obs.url)
