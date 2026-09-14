"""Which part of the later page is the continuation of this part of the earlier one?

A predicted change is about a particular thing on the page, so checking it needs to know
which node in the later observation is that thing. Asking only whether the value turned up
anywhere is far too weak: a value gained in an untouched row would confirm a prediction about
a row that never changed.

This has to work below the competing readings, so it knows nothing about objects, keys or
types -- only roles, rendered text, values and tree shape. The field a prediction is about is
hidden while the match is made, and hidden from every ancestor too, or the match would be
found by the very property being tested and would fail exactly when the prediction is true.
Position on screen is deliberately unused: boxes are mostly stable but not always, and a
tolerance would be the arbitrary rule this module exists to do without.

Matching descends from the root along the node's ancestors, aligning each parent's children
to the corresponding parent's children in order, on the strongest description that places the
node at all. Where the evidence does not single out one continuation, every admissible one is
returned and the status is ``AMBIGUOUS``; where none is admissible it is ``NONE``. There is no
score and no tie-break: a forced wrong match manufactures refutations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from semabi.compiler.observation import Node, Observation


class _Wildcard:
    """Stands in for a field the prediction is about.  Compatible with anything."""
    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<masked>"


MASK = _Wildcard()

UNIQUE = "UNIQUE"
AMBIGUOUS = "AMBIGUOUS"
NONE = "NONE"

DEEP = "DEEP"       # the whole masked subtree matched
LOCAL = "LOCAL"     # node fields plus one level of children
SHAPE = "SHAPE"     # role and whether it has descendants; rendered text dropped entirely

FIELDS = ("name", "value", "checked", "options", "placeholder", "current")


def outcome_field(node: Node) -> str:
    """The field a slot value is read from, and therefore the field a prediction masks.

    Mirrors :func:`semabi.compiler.parse.leaf_value`: a combobox's ``value``, a checkbox's
    ``checked``, and for everything else the rendered ``name``.
    """
    if node.role in ("checkbox", "radio"):
        return "checked"
    if node.role in ("combobox", "textbox"):
        return "value"
    return "name"


def mask_outcome(obs: Observation, index: int) -> dict[int, frozenset[str]]:
    """The mask for a prediction about node ``index``'s displayed value."""
    return {index: frozenset({outcome_field(obs.node(index))})}


@dataclass(frozen=True)
class Correspondence:
    """The admissible continuations of one pre-transition node."""
    pre: int
    admissible: tuple[int, ...]
    status: str
    layers: tuple[str, ...] = ()
    detail: str = ""

    @property
    def unique(self) -> int | None:
        return self.admissible[0] if self.status == UNIQUE else None

    def to_json(self) -> dict[str, Any]:
        return {"pre": self.pre, "admissible": list(self.admissible), "status": self.status,
                "layers": list(self.layers), "detail": self.detail}


# ---------------------------------------------------------------- descriptors

def _fields(obs: Observation, i: int, masked: Mapping[int, frozenset[str]]) -> tuple:
    node = obs.node(i)
    hidden = masked.get(i) or ()
    out: list[Any] = [node.role]
    for name in FIELDS:
        if name in hidden:
            out.append(MASK)
        elif name == "options":
            out.append(tuple(node.options or ()))
        else:
            out.append(getattr(node, name))
    return tuple(out)


class _Descriptors:
    """Descriptor computation, with the unmasked results cached per observation.

    Only nodes between the root and a masked node have mask-dependent descriptors, so the
    expensive deep ones are computed once and reused across predictions.
    """

    def __init__(self) -> None:
        self._deep: dict[tuple[int, int], tuple] = {}

    def deep(self, obs: Observation, i: int, masked: Mapping[int, frozenset[str]],
             tainted: frozenset[int]) -> tuple:
        if i not in tainted:
            key = (id(obs), i)
            hit = self._deep.get(key)
            if hit is None:
                hit = (_fields(obs, i, {}),
                       tuple(self.deep(obs, c, {}, frozenset()) for c in obs.children(i)))
                self._deep[key] = hit
            return hit
        return (_fields(obs, i, masked),
                tuple(self.deep(obs, c, masked, tainted) for c in obs.children(i)))

    def local(self, obs: Observation, i: int, masked: Mapping[int, frozenset[str]]) -> tuple:
        return (_fields(obs, i, masked),
                tuple((obs.node(c).role, _fields(obs, c, masked)[1], len(obs.children(c)))
                      for c in obs.children(i)))

    @staticmethod
    def shape(obs: Observation, i: int) -> tuple:
        """Role and whether the node has descendants, and nothing else.

        Blind to how many children there are on purpose: a container that gained or lost a
        row still has to be matchable, since the evidence is one level below it. A match that
        gets no further than this layer is positional; see :attr:`Correspondence.layers`.
        """
        return (obs.node(i).role, bool(obs.children(i)))


def tainted_nodes(obs: Observation, masked: Iterable[int]) -> frozenset[int]:
    """Nodes whose subtree contains a masked node, and therefore whose descriptor moves."""
    out: set[int] = set()
    for i in masked:
        out.add(i)
        out.update(obs.ancestors(i))
    return frozenset(out)


def compatible(a: Any, b: Any) -> bool:
    """Structural equality in which a masked field matches whatever is in its place."""
    if a is MASK or b is MASK:
        return True
    if isinstance(a, tuple) or isinstance(b, tuple):
        if not (isinstance(a, tuple) and isinstance(b, tuple)) or len(a) != len(b):
            return False
        return all(compatible(x, y) for x, y in zip(a, b))
    return a == b


# ---------------------------------------------------------------- alignment

def admissible_matches(n: int, m: int, match: Callable[[int, int], bool],
                       tolerance: int = 0) -> tuple[dict[int, set[int]], list[bool]]:
    """Order-preserving alignment, reporting every match a good alignment can make.

    For each left index: the right indices it is paired with in at least one alignment within
    ``tolerance`` of the longest, and whether such an alignment can leave it unpaired. Taking
    the union over equally good alignments rather than one of them keeps real ambiguity
    visible instead of resolving it by preference. A left index with exactly one partner is
    determined; more than one, and the evidence does not fix the pairing.

    Widening ``tolerance`` can only add continuations, so it can only turn a refutation into a
    ``POSSIBLE`` -- which makes it a one-way robustness check on anything reported here.
    """
    suffix = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        row, nxt = suffix[i], suffix[i + 1]
        for j in range(m - 1, -1, -1):
            best = nxt[j] if nxt[j] >= row[j + 1] else row[j + 1]
            if match(i, j) and 1 + nxt[j + 1] > best:
                best = 1 + nxt[j + 1]
            row[j] = best
    prefix = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        row, prev = prefix[i], prefix[i - 1]
        for j in range(1, m + 1):
            best = prev[j] if prev[j] >= row[j - 1] else row[j - 1]
            if match(i - 1, j - 1) and 1 + prev[j - 1] > best:
                best = 1 + prev[j - 1]
            row[j] = best
    floor = suffix[0][0] - tolerance
    pairs: dict[int, set[int]] = {i: set() for i in range(n)}
    skippable = [False] * n
    for i in range(n):
        for j in range(m):
            if match(i, j) and prefix[i][j] + 1 + suffix[i + 1][j + 1] >= floor:
                pairs[i].add(j)
        skippable[i] = any(prefix[i][j] + suffix[i + 1][j] >= floor for j in range(m + 1))
    return pairs, skippable


# ---------------------------------------------------------------- descent

def _place(desc: _Descriptors, pre_obs: Observation, post_obs: Observation,
           pre_children: list[int], post_children: list[int], k: int,
           masked: Mapping[int, frozenset[str]], tainted: frozenset[int],
           tolerance: int = 0, ladder: tuple[str, ...] = (DEEP, LOCAL, SHAPE)
           ) -> tuple[str | None, list[int], bool]:
    """Where among ``post_children`` may ``pre_children[k]`` have continued?"""
    layers = [
        (DEEP, lambda o, i, m: desc.deep(o, i, m, tainted if m else frozenset())),
        (LOCAL, desc.local),
        (SHAPE, lambda o, i, m: desc.shape(o, i)),
    ]
    layers = [(name, fn) for name, fn in layers if name in ladder]
    for name, fn in layers:
        left = [fn(pre_obs, c, masked) for c in pre_children]
        right = [fn(post_obs, c, {}) for c in post_children]
        pairs, skippable = admissible_matches(
            len(left), len(right), lambda i, j: compatible(left[i], right[j]), tolerance)
        if pairs[k]:
            return name, [post_children[j] for j in sorted(pairs[k])], skippable[k]
    return None, [], True


def correspond(pre_obs: Observation, post_obs: Observation, pre_index: int,
               masked: Mapping[int, frozenset[str]] | None = None,
               *, descriptors: _Descriptors | None = None,
               tolerance: int = 0, ladder: tuple[str, ...] = (DEEP, LOCAL, SHAPE)
               ) -> Correspondence:
    """Admissible continuations of ``pre_index`` in ``post_obs``, given the masked fields.

    ``ladder`` restricts the fallback. A caller asking whether a structure *survived* must not
    let the descent reach the layer that matches on role and position alone: a panel replaced
    by a different panel of the same shape would look like the same panel, and the answer to
    "is it gone" would always be no.
    """
    masked = dict(masked or {})
    desc = descriptors or _Descriptors()
    tainted = tainted_nodes(pre_obs, masked)
    chain = list(reversed(pre_obs.ancestors(pre_index))) + [pre_index]

    current: list[int] = [-1]           # the virtual parent of the root nodes
    layers: list[str] = []
    may_have_been_dropped = False
    parent = -1
    for child in chain:
        pre_children = pre_obs.children(parent)
        k = pre_children.index(child)
        found: list[int] = []
        used: set[str] = set()
        for post_parent in current:
            layer, cands, skippable = _place(
                desc, pre_obs, post_obs, pre_children, post_obs.children(post_parent), k,
                masked, tainted, tolerance, ladder)
            if layer is None:
                continue
            used.add(layer)
            # An alignment that is just as good with this structure unmatched has not
            # settled that it survived, however few continuations are admissible.
            may_have_been_dropped |= skippable
            found.extend(cands)
        if not found:
            return Correspondence(
                pre_index, (), NONE, tuple(layers),
                f"no admissible continuation for the {pre_obs.node(child).role} at depth "
                f"{len(layers)}; the structure around it did not survive the transition")
        layers.append("/".join(sorted(used)))
        current = sorted(set(found))
        parent = child

    if len(current) == 1 and not may_have_been_dropped:
        return Correspondence(pre_index, tuple(current), UNIQUE, tuple(layers),
                              "one continuation is admissible under the unmasked evidence")
    if len(current) == 1:
        return Correspondence(pre_index, tuple(current), AMBIGUOUS, tuple(layers),
                              "one continuation is admissible, but an equally good alignment "
                              "leaves the structure unmatched, so its survival is not settled")
    return Correspondence(pre_index, tuple(current), AMBIGUOUS, tuple(layers),
                          f"{len(current)} continuations are equally admissible under the "
                          f"unmasked evidence")


@dataclass
class Corresponder:
    """A reusable :func:`correspond` with the descriptor cache kept across calls."""
    descriptors: _Descriptors = field(default_factory=_Descriptors)
    tolerance: int = 0
    ladder: tuple[str, ...] = (DEEP, LOCAL, SHAPE)

    def __call__(self, pre_obs: Observation, post_obs: Observation, pre_index: int,
                 masked: Mapping[int, frozenset[str]] | None = None) -> Correspondence:
        return correspond(pre_obs, post_obs, pre_index, masked, descriptors=self.descriptors,
                          tolerance=self.tolerance, ladder=self.ladder)
