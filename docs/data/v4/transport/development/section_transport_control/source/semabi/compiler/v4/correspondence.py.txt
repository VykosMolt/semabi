"""What in the later observation is the continuation of this raw structure?

A reading's semantic delta says an object's slot took a new value.  Checking that against
the page needs an answer to a question the reading cannot be allowed to answer: *which* part
of the later observation is the thing it was talking about.  The page-global check in
:mod:`semabi.compiler.v4.prospective` avoids the question by asking only whether the value
appeared anywhere, which is far too weak -- a value gained in an untouched row confirms a
prediction about a row that never changed.  Scoping the check needs correspondence.

The correspondence has to live *below* the competing readings.  Harbour's live disagreement
is over what the page's entities are: one reading names each table row by its identifying
column, the other keeps rows keyed by a column that does not identify them and additionally
makes every bare cell an entity named by its own rendered text.  A correspondence rule that
relocates rows assumes the first answer and one that relocates cells assumes the second, so
this module knows nothing about readings, objects, keys or families.  It works on :class:`Observation` alone: roles,
rendered text, values, and tree structure.

**Outcome masking.**  The feature a prediction is about may not be used to find the thing
the prediction is about.  If a reading predicts a cell's text becomes ``'open'``, then that
cell's text is unavailable evidence -- otherwise the correspondence would be found by the
very property being tested, and would fail exactly when the prediction is true.  Masking is
per node and per field, and it propagates: a masked node's text is hidden from its own
descriptor and from every ancestor descriptor that contains it.  On the later observation
nothing is masked, because which node is the continuation is not yet known; the mask is a
wildcard that matches whatever is there.

Geometry is deliberately not used.  ``Node.bbox`` is recorded and would be strong evidence
where content fails, but on the transitions that matter it is only mostly stable: of 816 true
correspondents across the blend history's node-adding transitions, 26 have a different box.
Using it as hard evidence would invent that many failures to relocate, and using it softly
needs a tolerance -- which is the arbitrary rule this module exists to do without.

**Ambiguity is preserved.**  Correspondence is set-valued.  Where the admissible evidence
does not single out one continuation, every admissible one is returned and the status is
``AMBIGUOUS``; where nothing is admissible the status is ``NONE``.  There is no score, no
threshold, and no tie-break: a forced wrong match manufactures semantic refutations, which
is a worse failure than saying nothing.

**How a continuation is found.**  Descent from the root along the pre-node's ancestor chain.
At each level the parent's children are aligned to the corresponding parent's children by an
order-preserving alignment (longest common subsequence under a compatibility predicate,
which is where the wildcard enters).  A pre-child's admissible continuations are the
post-children it is matched to in *some* optimal alignment; if it can also be left unmatched
by an optimal alignment, that counts as ambiguity too.  Levels are aligned on the strongest
descriptor that places the target at all -- full masked subtree, then a depth-two local
summary, then role and whether it has descendants -- and the backoff is per level and
recorded, never used to break a tie.
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

    Mirrors :func:`semabi.compiler.parse.leaf_value`, which is what the abstractor reads
    when it fills a slot: a combobox's slot value is its ``value``, a checkbox's is
    ``checked``, and everything else is the rendered ``name``.
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
    """Descriptor computation with a per-observation cache for the unmasked case.

    Only nodes on the path from the root to a masked node have mask-dependent descriptors;
    every other subtree is identical whether or not a mask is in force, so the expensive
    deep descriptors are computed once per observation and reused across predictions.
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

        Deliberately blind to how many children there are: a container that gained or lost a
        row still has to be matchable, since it is the level *below* it that carries the
        evidence.  A correspondence that gets no further than this layer is positional, and
        callers that care should read :attr:`Correspondence.layers`.
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

    Returns, for each left index, the set of right indices it is paired with in at least one
    alignment within ``tolerance`` of the maximum length, and whether such an alignment can
    leave it unpaired.  Taking the union over co-optimal alignments rather than one of them is
    what keeps genuine ambiguity visible instead of resolving it by an arbitrary preference.

    This is the sequence-alignment notion of a *safe* pairing (Grigorjew et al., 2023, after
    Naor and Brutlag, 1994): a partial solution is safe when it appears in every optimal path
    of the alignment graph, and their generalisation admits paths within a suboptimality
    budget as well, on the observation that the single best-scoring alignment is not reliably
    the right one.  A left index with exactly one admissible partner here is safe in that
    sense; more than one, and the evidence does not determine the pairing.  ``tolerance`` is
    the suboptimality budget.  Widening it can only add admissible continuations, so it can
    only turn a refutation into a ``POSSIBLE`` -- which makes it a one-directional robustness
    check on any refutation this instrument reports.
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

    ``ladder`` restricts the backoff.  A caller asking whether a structure *survived* must not
    let the descent fall through to the layer that matches on role and position alone: a panel
    replaced by a different panel of the same shape would then look like the same panel, and
    the answer to "is it gone" would always be no.
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
