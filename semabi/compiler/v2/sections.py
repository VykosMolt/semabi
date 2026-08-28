"""Objects an interface renders as a run of siblings rather than as a subtree.

`find_unit_types` asks of every *node* whether its collapsed template recurs with a data
filling that varies, and that question is the whole of SemABI's notion of objecthood.  It is a
good question.  What it cannot reach is an object with no node of its own.

Cellar renders its halls like this, three times, flat inside one group::

    heading 'Ferment Shed'
    text    'Temperature 22 C. Room for 3 vessels; 2 standing here.'
    table   ...the vessels standing there...

There is no per-hall element.  The hall is a *span* of siblings delimited by a heading, and the
enclosing group's own template collapses the three spans into one because repeated child
templates count once.  So no node has a hall's extent, no template recurs per hall, and the
abstraction cannot form the concept -- which is why `Move vessel`'s outcome rule could not
mention a hall however much evidence was acquired.

The repair is not to admit `heading` as an entity role.  It is to ask the existing objecthood
question of sibling *spans* as well as of subtrees:

* **bounded extent** -- a span runs from one occurrence of a boundary template to the next;
* **recurring shape** -- at least two spans under one parent share a span template;
* **varying values** -- their data fillings differ, which is `UnitType.recurrence >= 2`;
* **not already a node** -- a span of one is a subtree and is handled already.

Nothing here is specific to headings, prose or Cellar.  A card, fieldset, panel or labelled
cluster laid out flat satisfies the same test; a run of form controls does not, because its
labels are labels rather than data and its filling does not vary.

Spans that pass become real containers: `normalise` appends a synthetic ``group`` per span and
reparents the span's members to it, so every layer above -- units, entity types, referring
queries, controls, outcomes -- sees an ordinary node and needs no notion of a span at all.  The
containers are *appended*, never inserted, so existing node indices keep their meaning and a
recorded action still names the element it named.
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
