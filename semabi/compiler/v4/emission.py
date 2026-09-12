"""What an interaction *returned*, as distinct from what it changed.

A click on a control can produce a meaningful observable response without the domain
transition it was aimed at happening at all.  Blend answers that the destination is already
bottled; cellar answers that nothing is chosen in the vessel list; harbour answers that a
berth is already open.  Those sentences are the application stating the contract -- usually
naming the precondition it refused on, and the object it refused about -- and until now
nothing downstream could hold them: :attr:`Diff.domain_changed` is ``added or removed or
attr_changes or rel_changes``, so a transition whose only difference is a sentence went to
``noops``.

Making a sentence count as a domain change would be the wrong repair; nothing about the world
changed, and that distinction is what keeps view navigation from looking causal.  This module
supplies the third category instead: an **observable output**, carried on a transition beside
its state delta, that an operator may predict and a held-out step may refute.

Two decisions here are worth stating because they are the ones that could be wrong.

**An output is observed only where the live region's text changed.**  Blend rewrites its
status line on every click; harbour and cellar leave it standing when a navigation or
selection click says nothing.  From the page alone those two cases are indistinguishable when
the text is the same as before -- a re-emission of the identical sentence, or silence -- so an
unchanged live region yields no output observation rather than a guessed one.  It costs blend
the 14 refusals that repeat the previous refusal verbatim, and it never invents evidence.

**The event vocabulary is earned from the page, not from English.**  A message is split into a
*frame* and *arguments* by masking the maximal spans of it that are rendered as whole values
elsewhere on the page -- an object's name, a cell's contents, one component of a select
option.  ``Festival White is already bottled.`` becomes ``<> is already bottled .`` with the
argument ``Festival White``, and the argument is then grounded to the object that renders it.
Nothing here knows that "already" means refusal, that "Drew" means success, or that these
applications are about wine; the frames are whatever recurs once the page's own data is taken
out of the sentence, and two messages have the same frame exactly when what is left is equal.

The masking is candidate-independent: it reads the raw accessibility tree, never a reading's
objects, so an outcome class cannot be defined by the model that is about to be scored on it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from semabi.compiler.observation import Observation

# Live regions: the ARIA roles whose content is written by the application in response to an
# interaction rather than describing the state of the page.
#
# `alert` is not here, and the reason is a decision rather than a claim.  It is the same kind
# of region -- the V0/V1 environment renders its error text with `role="alert"` -- but the
# parser reads it as an ordinary leaf and has since V0, so the whole frozen V0/V1 line was
# derived with alert content in the state.  A role must be one thing or the other: state or
# output, never both, or a message is counted twice and a status-only change becomes a domain
# change.  Moving `alert` across is a one-line change here and in `parse.DATA_ROLES`, and its
# cost is re-deriving results that are not about live regions at all.
LIVE_ROLES = ("status",)

# A rendered value is short.  The guard exists to keep an application's prose -- a page
# heading, an instructional paragraph -- from becoming a vocabulary of values that would mask
# half of every sentence.
MAX_VALUE_TOKENS = 4

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-']*|[^\sA-Za-z0-9]")
SPLIT_RE = re.compile(r"[,;()]| - |·|/")

PLACEHOLDER = "<>"


def tokens(text: str) -> list[str]:
    """Tokens, with a sentence-final period split off a word but kept inside initials."""
    out = []
    for t in TOKEN_RE.findall(text or ""):
        # A sentence-final period is punctuation; a period inside a token ("T.S.", "4000.5")
        # belongs to it.  Splitting matters because a message ends on the value it names --
        # "...call C-102." has to tokenise to the same "C-102" the page renders.
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
    """The live-region content, or ``None`` where the application renders no live region.

    ``None`` and ``""`` are different answers: an application without a status line has no
    output channel at all, and one whose status line is empty has said nothing this time.
    """
    ns = live_nodes(obs)
    if not ns:
        return None
    return "\n".join(_text(obs.node(i)) for i in ns)


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
    """Every short value the pages render, tokenised, excluding labels and the live region.

    Both the whole text of a node and its comma/dash-separated components count, because an
    application that renders ``T1 - tank - 4000 L - dirty - Ferment Shed`` in a select option
    is rendering five values and one of them may be what a message names.
    """
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
        for obs in observations:
            self.learn(obs)

    def learn(self, obs: Observation) -> None:
        if self.frozen:
            return
        self.values |= rendered_values(obs)

    def freeze(self) -> None:
        self.frozen = True

    def for_pages(self, *pages: Observation) -> set[tuple[str, ...]]:
        return self.values | rendered_values(*pages)


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
    """The output this transition produced, or ``None`` where the page does not say.

    ``None`` covers both an application with no live region and one whose live region did not
    change -- see the module docstring for why the second is not read as silence.
    """
    a, b = live_text(before), live_text(after)
    if b is None or a == b:
        return None
    if a is not None and ("\n" in a or "\n" in b):
        # Several live regions: what this interaction said is the line that was not standing
        # before it -- dispatch's seal verdict stays on the page while the check answers
        # beside it, and "Dispatch ready" is the output, not "Dispatch ready Seal held".
        said = [line for line in b.split("\n") if line not in a.split("\n")]
        if not said:
            return None
        b = "\n".join(said)
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
