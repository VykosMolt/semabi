"""Unit hypotheses from template recurrence.

A *unit template* is a subtree template (roles + label tokens, repeated child
templates collapsed) that occurs with at least two distinct data fillings
anywhere in the evidence: among siblings, in different views, or at different
times (a detail panel shown for different objects). Every such template is a
candidate unit type; instances are the subtrees matching it. Nothing is
decided globally here — nested candidates coexist, and the later hypothesis
scoring chooses among them by behaviour.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from semabi.compiler.v2.graph import ObsGraph, node_text, tokens


def collapsed_template(G: ObsGraph, sig: str, i: int, memo: dict) -> str:
    key = (sig, i)
    if key in memo:
        return memo[key]
    obs = G.obs[sig]
    n = obs.node(i)
    lab = G.labels(sig, i)
    parts = []
    for t in tokens(node_text(n)):
        if not t[0].isalnum():
            continue  # punctuation is neither label nor data
        m = t if t in lab else "_"
        if m == "_" and parts and parts[-1] == "_":
            continue  # a run of data tokens is one slot
        parts.append(m)
    ch = [collapsed_template(G, sig, c, memo) for c in obs.children(i)]
    if not parts and not ch and n.role in ("cell", "text", "group", "listitem", "heading"):
        parts = ["_"]  # an empty data cell is a slot without a value
    txt = " ".join(parts)
    out = []
    for c in ch:
        if out and out[-1] == c:
            continue  # repeated child templates count once (multiplicity-insensitive)
        out.append(c)
    t = f"{n.role}[{txt}]" + ("(" + ",".join(out) + ")" if out else "")
    memo[key] = t
    return t


@dataclass
class UnitType:
    template: str
    instances: list[tuple[str, int]] = field(default_factory=list)  # (sig, root)
    fillings: Counter = field(default_factory=Counter)  # data filling -> count
    n_obs: int = 0  # observations in which it occurs
    max_per_obs: int = 0

    @property
    def recurrence(self) -> int:
        return len(self.fillings)


def data_filling(G: ObsGraph, sig: str, i: int) -> tuple[str, ...]:
    return tuple(t for _, t in G.subtree_data(sig, i))


def find_unit_types(G: ObsGraph, min_fillings: int = 2, min_tokens: int = 1) -> dict[str, UnitType]:
    memo: dict = {}
    types: dict[str, UnitType] = {}
    per_obs: dict[str, Counter] = defaultdict(Counter)
    for sig, obs in G.obs.items():
        for n in obs.nodes:
            if n.parent < 0:
                continue  # the document root is not a unit
            t = collapsed_template(G, sig, n.i, memo)
            fill = data_filling(G, sig, n.i)
            if len(fill) < min_tokens:
                continue
            ut = types.setdefault(t, UnitType(t))
            ut.instances.append((sig, n.i))
            ut.fillings[fill] += 1
            per_obs[t][sig] += 1
    out = {}
    for t, ut in types.items():
        if ut.recurrence < min_fillings:
            continue
        ut.n_obs = len(per_obs[t])
        ut.max_per_obs = max(per_obs[t].values())
        out[t] = ut
    return out
