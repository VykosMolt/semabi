"""Is a repeated line of text a value of the thing that shows it, or a thing of its own?

The parser answers structurally and always the same way: a childless text node is a slot of
the unit around it. For a card's title that is right; for a list rendered one patient per
line it is exactly wrong. So candidates are proposed here and put on trial the way identity
keys are, and kept only if reading them as objects explains more of what the application did.
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
