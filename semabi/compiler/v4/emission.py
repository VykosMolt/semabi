"""What an interaction returned, as distinct from what it changed.

A click can produce a message without changing anything: "already bottled", "nothing
chosen". That is neither a state change nor navigation, so it gets its own category
here, carried alongside the state delta.

A message counts only when the live region's text changed, because an unchanged
region may be silence or the same sentence again and the page does not say which.
The message is then split into a frame and its arguments by masking the spans the
page renders as values elsewhere, so "Festival White is already bottled." becomes
"<> is already bottled ." with one argument. The masking reads the raw page, never
a candidate reading.
"""
from __future__ import annotations

import re
from collections import Counter, OrderedDict
from dataclasses import dataclass

from semabi.compiler.observation import Observation

# Roles the application writes to in response to an action, rather than to describe
# the page. `alert` belongs here too, but the parser has always read it as state, and
# a role must be one or the other or its text is counted twice.
LIVE_ROLES = ("status",)

# Values are short. Without a cap, a heading or a paragraph would become a "value"
# and mask half of every message.
MAX_VALUE_TOKENS = 4

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-']*|[^\sA-Za-z0-9]")
SPLIT_RE = re.compile(r"[,;()]| - |·|/")

PLACEHOLDER = "<>"


def tokens(text: str) -> list[str]:
    """Tokens, with a sentence-final period split off a word but kept inside initials."""
    out = []
    for t in TOKEN_RE.findall(text or ""):
        # A final period is punctuation; one inside a token ("T.S.", "4000.5") is part of
        # it. A message often ends on the value it names.
        if t.endswith(".") and "." not in t[:-1] and len(t) > 1:
            out.append(t[:-1])
            out.append(".")
        else:
            out.append(t)
    return out


def _text(n) -> str:
    if n.role in ("textbox", "combobox"):
        return n.value or ""
    return n.name or ""


@dataclass(frozen=True)
class Event:
    """One observable output: a lifted frame and the page values it names."""
    frame: str
    args: tuple[str, ...] = ()
    text: str = ""

    def __str__(self) -> str:
        if not self.args:
            return f"emit {self.frame!r}"
        return f"emit {self.frame!r}({', '.join(self.args)})"


def live_nodes(obs: Observation) -> list[int]:
    return [n.i for n in obs.nodes if n.role in LIVE_ROLES]


def live_text(obs: Observation) -> str | None:
    """The live-region text, or None where the page has no live region at all.

    None and "" differ: no channel, against a channel that said nothing."""
    ns = live_nodes(obs)
    if not ns:
        return None
    return "\n".join(_text(obs.node(i)) for i in ns)


@dataclass(frozen=True)
class ResponseObservation:
    """The live-region texts before and after an action, kept whole.

    A change here is not evidence of a cause."""
    before_regions: tuple[tuple[int, str], ...]
    after_regions: tuple[tuple[int, str], ...]
    newly_visible_texts: tuple[str, ...]
    attribution: str = "UNESTABLISHED"


def observe_response(before: Observation, after: Observation) -> ResponseObservation:
    before_regions = tuple((i, _text(before.node(i))) for i in live_nodes(before))
    after_regions = tuple((i, _text(after.node(i))) for i in live_nodes(after))
    standing = Counter(text for _, text in before_regions)
    newly_visible = []
    for _, text in after_regions:
        if standing[text]:
            standing[text] -= 1
        else:
            newly_visible.append(text)
    return ResponseObservation(before_regions, after_regions, tuple(newly_visible))


def response_region_path(obs: Observation, node: int) -> tuple[tuple[str, int], ...]:
    """Where a live region sits, by role and sibling position rather than by its text.

    A changed layout invalidates the path; node indices never cross pages."""
    path = []
    for index in reversed([node, *obs.ancestors(node)]):
        here = obs.node(index)
        siblings = [i for i in obs.children(here.parent) if obs.node(i).role == here.role]
        path.append((here.role, siblings.index(index)))
    return tuple(path)


def response_locations(before: Observation, after: Observation) -> list[dict]:
    """Where newly visible response text could have come from.

    All possible sources are kept: duplicated text must not resolve to an arbitrary node."""
    response = observe_response(before, after)
    novel = set(response.newly_visible_texts)
    return [{"node": node, "path": response_region_path(after, node), "text": text}
            for node, text in response.after_regions if text in novel]


def header_cells(obs: Observation) -> set[int]:
    """Cells of each table's first row: labels, not values."""
    out: set[int] = set()
    for n in obs.nodes:
        if n.role != "table":
            continue
        rows = sorted(x for x in obs.subtree(n.i) if obs.node(x).role == "row")
        if rows:
            out.update(obs.children(rows[0]))
    return out


def rendered_values(*observations: Observation) -> set[tuple[str, ...]]:
    """Every short value the pages render, tokenised, minus labels and the live region.

    A node's whole text counts and so do its comma- or dash-separated parts: one option
    can render five values, and a message may name any of them."""
    out: set[tuple[str, ...]] = set()
    for obs in observations:
        if obs is None:
            continue
        skip = set(live_nodes(obs)) | header_cells(obs)
        for n in obs.nodes:
            if n.i in skip:
                continue
            pieces = [_text(n)]
            pieces += list(n.options or ())
            for piece in list(pieces):
                pieces.extend(SPLIT_RE.split(piece))
            for piece in pieces:
                toks = tuple(tokens(piece.strip()))
                if not toks or len(toks) > MAX_VALUE_TOKENS:
                    continue
                if "." in toks or not any(t[0].isalnum() for t in toks):
                    continue
                out.add(toks)
    return out


RENDERED_VALUE_CACHE_SIZE = 128


class Vocabulary:
    """Which token spans are page data, learned over a corpus and then frozen.

    A frame read off one page alone is unstable: ``Berth S1 cannot be closed while call C-101
    holds it.`` masks ``closed`` on a page that renders a closed berth and leaves it standing
    on a page that does not, and the same message then belongs to two different events.  The
    vocabulary is therefore a corpus statistic, learned from exactly the observations a regime
    allows and frozen with the rest of the model, in the same way and for the same reason as
    the observation graph's data tokens.

    Reading a held-out page still contributes that page's own rendered values, because a
    message naming an object the prefix never saw has to be readable at all; what a held-out
    page may not do is change the vocabulary the model carries.
    """

    def __init__(self, observations=()):
        self.values: set[tuple[str, ...]] = set()
        self.frozen = False
        self._rendered_cache = OrderedDict()
        for obs in observations:
            self.learn(obs)

    def __getstate__(self):
        # Derived page values are ephemeral, not fitted knowledge. In particular,
        # copying an abstractor must not duplicate its recently visited pages.
        return {key: value for key, value in self.__dict__.items() if key != '_rendered_cache'}

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._rendered_cache = OrderedDict()

    def _rendered(self, obs: Observation) -> frozenset[tuple[str, ...]]:
        # This exact key includes every input rendered_values reads. Do not use
        # the short structural signature, graph vocabulary, or inferred identity.
        # Actual child traversal can diverge from parent fields after mutation.
        key = tuple((node.i, node.parent, node.role, node.name, node.value,
                     tuple(node.options or ()), tuple(obs.children(node.i))) for node in obs.nodes)
        cached = self._rendered_cache.get(key)
        if cached is None:
            cached = frozenset(rendered_values(obs))
            self._rendered_cache[key] = cached
            if len(self._rendered_cache) > RENDERED_VALUE_CACHE_SIZE:
                self._rendered_cache.popitem(last=False)
        else:
            self._rendered_cache.move_to_end(key)
        return cached

    def learn(self, obs: Observation) -> None:
        if self.frozen or obs is None:
            return
        # Re-union even on a cache hit: values can legitimately be replaced when
        # restoring or revising a vocabulary. This is not learned-once suppression.
        self.values |= self._rendered(obs)

    def freeze(self) -> None:
        self.frozen = True

    def for_pages(self, *pages: Observation) -> set[tuple[str, ...]]:
        values = set(self.values)
        for page in pages:
            if page is not None:
                values.update(self._rendered(page))
        return values


def lift_event(text: str, *pages: Observation, vocabulary: "Vocabulary | None" = None) -> Event:
    """Split a message into the frame that recurs and the page values it names.

    Longest match wins, so ``Creek Bed`` is one argument rather than two, and adjacent
    arguments stay separate -- ``Closed Creek Bed.`` names the gate state and the vat, and
    collapsing them would make it the same event as ``Opened Mill Race.``
    """
    values = (vocabulary.for_pages(*pages) if vocabulary is not None
              else rendered_values(*pages))
    toks = tokens(text or "")
    frame: list[str] = []
    args: list[str] = []
    i = 0
    while i < len(toks):
        hit = 0
        for span in range(min(MAX_VALUE_TOKENS, len(toks) - i), 0, -1):
            if tuple(toks[i:i + span]) in values:
                hit = span
                break
        if hit:
            frame.append(PLACEHOLDER)
            args.append(" ".join(toks[i:i + hit]))
            i += hit
        else:
            frame.append(toks[i])
            i += 1
    return Event(" ".join(frame), tuple(args), text or "")


def observed(before: Observation, after: Observation,
             vocabulary: "Vocabulary | None" = None) -> Event | None:
    """A changed output surface, not proof of the action that caused it.

    ``None`` covers both an application with no live region and one whose live region did not
    change -- see the module docstring for why the second is not read as silence.
    """
    response = observe_response(before, after)
    if not response.newly_visible_texts:
        return None
    b = "\n".join(response.newly_visible_texts)
    return lift_event(b, after, before, vocabulary=vocabulary)


def render(frame: str, args) -> str:
    """A frame and its arguments back as one string, for reading a prediction."""
    out, k = [], 0
    for token in frame.split(" "):
        if token == PLACEHOLDER and k < len(args):
            out.append(str(args[k]))
            k += 1
        else:
            out.append(token)
    return " ".join(out)
