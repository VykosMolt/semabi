"""Is a repeated leaf a value of its container, or a thing in its own right?

The frozen parser answers this structurally and once: a childless text node is a slot of
the unit that encloses it.  For a card whose title is a line of text that is right, and for
a list of patients rendered one per line it is exactly wrong -- no reading of identity can
make a patient an object if patients are values of the owner that lists them.  The question
is not about lists or cards; it is the observation-model question of whether an emission
belongs to the latent object it sits inside or to one of its own.

So it is asked the same way as identity: propose leaves that recur as siblings, put each
proposal on trial, and keep it only if reading it as an object explains more of what the
application did without inventing anything.
"""
from __future__ import annotations

from collections import Counter, defaultdict

MIN_SIBLINGS = 2      # a leaf that never repeats under one parent proposes nothing
MIN_OBSERVATIONS = 2  # and one page is not a pattern
MAX_CANDIDATES = 6


def candidates(H, G) -> list[str]:
    """Leaf templates that recur as siblings: proposals, not decisions."""
    siblings: dict[str, Counter] = defaultdict(Counter)
    seen: dict[str, set[str]] = defaultdict(set)
    role_of: dict[str, str] = {}
    for sig in sorted(G.obs):
        obs = G.obs[sig]
        by_parent: dict[int, Counter] = defaultdict(Counter)
        for node in obs.nodes:
            if obs.children(node.i) or node.parent < 0:
                continue                      # only childless nodes are in question here
            if node.role in ("combobox", "textbox", "checkbox", "radio", "button", "link"):
                continue                      # controls are not values of their container
            template = H.template(sig, node.i)
            role_of.setdefault(template, node.role)
            by_parent[node.parent][template] += 1
        for _, counts in by_parent.items():
            for template, n in counts.items():
                if n >= MIN_SIBLINGS:
                    siblings[template][sig] += n
                    seen[template].add(sig)
    # only leaves the parser currently refuses to read as objects are in question
    out = [t for t in siblings
           if len(seen[t]) >= MIN_OBSERVATIONS
           and not H.is_unit_template(t, role_of[t], has_children=False)]
    out.sort(key=lambda t: (-sum(siblings[t].values()), t))
    return out[:MAX_CANDIDATES]
