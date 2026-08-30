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

    _vary: tuple[int, set[str]] | None = None

    def varying_tokens(self) -> set[str]:
        """Tokens that vary across the distinct strings at this position (< 80% of them)."""
        if len(self.strings) < 2:
            return set()
        if self._vary is not None and self._vary[0] == len(self.strings):
            return self._vary[1]
        per = Counter()
        for s in self.strings:
            for t in set(tokens(s)):
                if t[0].isalnum():
                    per[t] += 1
        out = {t for t, c in per.items() if c < 0.8 * len(self.strings)}
        self._vary = (len(self.strings), out)
        return out

    def sentence_length(self) -> bool:
        """Four or more alphanumeric tokens in some string here: the length at which a text
        is a sentence rather than a name, a value or a phrase."""
        return any(sum(1 for t in tokens(st) if t[0].isalnum()) >= 4 for st in self.strings)


# Containers the accessibility tree declares as collections.  Their children are members of
# one listing -- the rows of a table, the items of a list -- and what differs between members
# at the same slot is content, whichever member it happens to be in.
COLLECTIONS = {"table", "rowgroup", "list", "grid", "treegrid", "listbox", "menu", "tree"}
WIDGET_ROLES = {"button", "link", "checkbox", "radio", "combobox", "textbox"}


class ObsGraph:
    # Whether variation is judged across the members of a declared collection.  Off, it is
    # judged per indexed position only -- the reading every report before `docs/v4_open_world.md`
    # was computed under -- which on a listing whose rows never reorder makes every constant
    # cell of every row a label, and every row its own type.  Kept as a switch so that the
    # two readings can be put side by side; nothing sets it but an experiment.
    judge_by_collection: bool = True

    def __init__(self):
        self.nodes: dict[tuple[str, int], NodeDesc] = {}
        self.obs: dict[str, Observation] = {}
        self.templates: dict[str, TextTemplate] = {}  # position -> template
        self.position_of: dict[tuple[str, int], str] = {}
        self.variation_key: dict[tuple[str, int], tuple] = {}  # (sig, node) -> templates_v key
        self._in_nonwidget: set[str] = set()  # tokens seen in a non-widget text or an input value
        self._whole: set[str] = set()  # complete texts / option labels / input values (lowercase data values)
        self._data: set[str] | None = None
        self._listed_only: set[str] = set()   # values by collection variation alone
        self._declared_headers: set[str] = set()  # texts of header rows in a row group of their own
        self._pooled_views: dict[tuple, TextTemplate] = {}
        self._seen: set[str] = set()   # every token the corpus read anywhere, headers and options included
        self._value_paths: set[str] | None = None
        self.templates_v: dict[tuple, TextTemplate] = {}  # (position, indexed position, view skeleton) -> strings
        self.header: set[tuple[str, int]] = set()  # (sig, node) cells of a table's first row
        self.header_strings: dict[tuple[str, int], set[str]] = defaultdict(set)  # (table path, col) -> strings
        self.learning: bool = True  # False once fitted: read new observations, learn nothing from them

    def data_set(self) -> set[str]:
        """Data tokens: numbers, and tokens that vary within a position, except tokens that
        only ever occur in static control labels (buttons/links whose text never appears in
        data text anywhere)."""
        if self._data is None:
            d0 = set()
            # variation is judged within one view: a heading that differs between views is
            # not data, a label that differs between the hives a panel shows is
            for tt in self.templates_v.values():
                d0 |= tt.varying_tokens()
            d0 = {t for t in d0 if t[0].isdigit() or t in self._in_nonwidget}
            # a lowercase word is a value only when it occurs on its own somewhere (a status
            # word in a cell, an option); inside sentences it is wording, not data
            d = {t for t in d0 if t[0].isdigit() or t[0].isupper() or t in self._whole}
            if not self.judge_by_collection:
                # prose positions (sentences with a vocabulary of >= 4 constant words) vary in
                # wording, not in data: their varying tokens count only if data elsewhere
                prose = set()
                for pos, tt in self.templates.items():
                    vocab = {t for st in tt.strings for t in tokens(st) if t[0].isalpha() and t not in d}
                    if len(vocab) >= 4 and len(tt.strings) >= 2:
                        prose.add(pos)
                if prose:
                    d2 = set()
                    for (pos, _, _), tt in self.templates_v.items():
                        if pos not in prose:
                            d2 |= tt.varying_tokens()
                    d = {t for t in d if t[0].isdigit() or t in d2}
                self._data = d
                return self._data
            # Prose -- a position whose strings are sentences, with a vocabulary of >= 4
            # constant words, varying in wording rather than in data -- is judged where the
            # variation is judged, per position, and not over every node in the application
            # that shares a role path and a token pattern.  Pooled by role path, every
            # two-word table cell of harbour was one position, the call sheet's field names
            # (`Length overall`, `Hazardous cargo`) were its constant vocabulary, and the
            # position was prose: so `United Kingdom`, `Ardent Rose` and `Aoife Marr`, which
            # occur only in such cells, were wording -- labels -- and every vessel and pilot
            # row a type of its own, while a name the prefix never saw was a value at the
            # same cell.  A varying token at a prose position counts only if it is data at a
            # position that is not prose.
            # A cell is not a sentence.  The vocabulary test alone called harbour's vessel
            # cells prose because the cargo words (`drummed solvents`, `frozen fish`) are
            # lowercase and never stand alone -- constant vocabulary by the letter of the rule
            # -- and vet's appointment reasons the same; a sentence has the length of one.
            prose = set()
            for key, tt in self.templates_v.items():
                if not tt.sentence_length():
                    continue
                vocab = {t for st in tt.strings for t in tokens(st) if t[0].isalpha() and t not in d}
                if len(vocab) >= 4 and len(tt.strings) >= 2:
                    prose.add(key)
            plain, listed = set(), set()
            for key, tt in self.templates_v.items():
                if key in prose:
                    continue
                v = tt.varying_tokens()
                plain |= v
                if any(x == "*" for _, x in key[1]):
                    listed |= v
            d = {t for t in d if t[0].isdigit() or t in plain}
            # Inside a member of a declared collection the lowercase rule does not apply: what
            # differs between the rows of one table at one cell is the cell's value whether
            # or not it is ever shown on its own -- `on duty` / `off duty`, `single varietal`
            # / `a blend` -- and reading it as wording made the duty of a pilot a difference
            # between two row templates rather than an attribute of one.  Such a word is a
            # value where it varies and wording anywhere else (`Sign on`): see `is_data_at`.
            self._listed_only = {t for t in d0 if t in listed} - d
            d |= self._listed_only
            self._data = d
            # The same position seen in several views, for judging a page whose view the
            # corpus never saw.
            self._pooled_views = {}
            for (pos, ppos, _skel), tt in self.templates_v.items():
                merged = self._pooled_views.setdefault((pos, ppos), TextTemplate(pos))
                merged.strings.update(tt.strings)
                merged.n += tt.n
        return self._data

    def _is_member(self, obs, i: int) -> bool:
        """Is this node a member of a declared collection -- a row of a table, an item of a
        list -- directly or through the grouping containers `sections.normalise` inserts?"""
        n = obs.node(i)
        while n.parent >= 0:
            p = obs.node(n.parent)
            if p.role in COLLECTIONS:
                return True
            if p.role != "group":
                return False
            n = p
        return False

    def position_pooled(self, obs, i: int) -> tuple:
        """Indexed role path in which a member of a declared collection is unindexed.

        The rows of a table are one listing: what differs between them at the same cell is
        content, and which row it stands in is not part of the position.  Everything else
        keeps its ordinal, so the headings of two sections stay two positions.
        """
        out = []
        x = i
        while x >= 0:
            n = obs.node(x)
            if n.parent >= 0:
                leaf = not obs.children(x)
                if self._is_member(obs, x):
                    out.append((n.role, "*"))
                else:
                    sibs = [c for c in obs.children(n.parent)
                            if obs.node(c).role == n.role and (not obs.children(c)) == leaf]
                    out.append((n.role, sibs.index(x) * 2 + (1 if leaf else 0)))
            else:
                out.append((n.role, 0))
            x = n.parent
        return tuple(reversed(out))

    def position_idx(self, obs, i: int) -> tuple:
        """Indexed role path with leaf-aware ordinals (optional leaf siblings such as a
        feedback line do not shift structured siblings)."""
        out = []
        x = i
        while x >= 0:
            n = obs.node(x)
            if n.parent >= 0:
                leaf = not obs.children(x)
                sibs = [c for c in obs.children(n.parent) if obs.node(c).role == n.role and (not obs.children(c)) == leaf]
                out.append((n.role, sibs.index(x) * 2 + (1 if leaf else 0)))
            else:
                out.append((n.role, 0))
            x = n.parent
        return tuple(reversed(out))

    # ------------------------------------------------------------------ build
    def add(self, sig: str, obs: Observation) -> None:
        """Take an observation into the graph.

        Two different things happen here, and once a model is frozen only one of them may.
        Per-observation structure -- the node descriptors, the role paths, which cells sit in a
        table's first row -- is what makes *this* observation readable at all, and reading a
        held-out page requires it.  The corpus statistics are different: the text-variation
        templates and the data-token vocabulary are the learned judgement about which text on a
        page is a value rather than a label, and they are as much part of the model as the type
        system is.  Letting a held-out observation contribute to them is the chronology leak in
        miniature -- the suffix teaching the model the vocabulary it is about to be judged with.

        So a frozen graph reads the observation and declines to learn from it.  A position the
        prefix never saw simply has no template, and ``is_prose`` answers False for it: the
        frozen model has no evidence about that position, which is a smaller claim than the
        alternative and never a claim about the application.
        """
        if sig in self.obs:
            return
        self.obs[sig] = obs
        depth = {}
        paths = {}
        # Walked from the root rather than taken in list order: `sections.normalise` appends
        # its containers, so a parent can sit after its children in the list while the tree
        # itself stays perfectly well formed.
        stack = [n.i for n in obs.nodes if n.parent < 0]
        for r in stack:
            depth[r], paths[r] = 0, obs.node(r).role
        while stack:
            x = stack.pop()
            for c in obs.children(x):
                depth[c] = depth[x] + 1
                paths[c] = paths[x] + "/" + obs.node(c).role
                stack.append(c)
        for n in obs.nodes:                      # nodes unreachable from any root, if any
            depth.setdefault(n.i, 0)
            paths.setdefault(n.i, n.role)
        # table header cells: the first row of a table (labels even when they vary between
        # tables) -- unless the cell's text varies over time at that position (a matrix header)
        table_headers: dict[int, tuple] = {}
        for n in obs.nodes:
            if n.role == "table":
                rows = sorted(x for x in obs.subtree(n.i) if obs.node(x).role == "row")
                if rows:
                    # a header row in a row group of its own (a `thead`) is the interface
                    # declaring it; a first row among the others may be one or may not
                    declared = len(rows) > 1 and obs.node(rows[0]).parent != obs.node(rows[1]).parent
                    if declared:
                        table_headers[n.i] = tuple(node_text(obs.node(c)) for c in obs.children(rows[0]))
                    for k, c in enumerate(obs.children(rows[0])):
                        self.header.add((sig, c))
                        if self.learning:
                            self.header_strings[(paths[n.i], k)].add(node_text(obs.node(c)))
                            if declared:
                                self._declared_headers.add(node_text(obs.node(c)))
        # Row headers.  A key-value table -- harbour's call sheet, `Flag | United Kingdom`
        # -- names its fields down the first column, and judged across the members of the
        # collection those names vary as its values do.  What tells a field name from a value
        # is that the interface uses the same text as a declared column header elsewhere;
        # such a first cell is a header, with the same escape as a column header
        # (`is_header`).
        if self.judge_by_collection:
            known = {t for t in self._declared_headers if t}
            for n in obs.nodes:
                if n.role != "table":
                    continue
                rows = sorted(x for x in obs.subtree(n.i) if obs.node(x).role == "row")
                for r in rows[1:]:
                    cells = obs.children(r)
                    if cells and node_text(obs.node(cells[0])) in known:
                        self.header.add((sig, cells[0]))
        shapes = {}
        order = []                               # post-order, for the same reason as `depth`
        stack = [(n.i, False) for n in obs.nodes if n.parent < 0]
        while stack:
            x, done = stack.pop()
            if done:
                order.append(x)
                continue
            stack.append((x, True))
            for c in obs.children(x):
                stack.append((c, False))
        for x in order:
            ch = obs.children(x)
            shapes[x] = obs.node(x).role + ("(" + ",".join(shapes[c] for c in ch) + ")" if ch else "")
        for n in obs.nodes:
            shapes.setdefault(n.i, n.role)
        skel = hash(frozenset(paths.values()))  # which view this is (set of role paths)
        for n in obs.nodes:
            d = NodeDesc(sig, n.i, n.role, paths[n.i], shapes[n.i], tokens(node_text(n)), depth[n.i], list(obs.children(n.i)), n.parent)
            self.nodes[(sig, n.i)] = d
            # structural position of a text: role path + parent's shape (what surrounds it)
            pos = paths[n.i] + "|" + token_pattern(node_text(n))
            self.position_of[(sig, n.i)] = pos
            # variation is judged per (position, indexed position of the *parent*, view): two
            # headings under different containers are different positions; the rows of one
            # listing share theirs -- which the parent's plain index did not give a cell,
            # whose parent is its own row: see `position_pooled`.
            key_pos = pos
            skel_key = skel
            if n.parent < 0:
                ppos: tuple = ()
            elif self.judge_by_collection:
                ppos = self.position_pooled(obs, n.parent)
                if self._is_member(obs, n.parent):
                    # A member's fields are its slots, by their place among its children --
                    # the column -- whatever shape a value takes.  Keyed by token pattern
                    # as well, blend's `Ticket 4` (a labelled number) was one position with
                    # `Block 12` (a name with a number) from another column of the same
                    # rows, `Ticket` varied, and every draw was keyed `Ticket`.
                    sibs = [c for c in obs.children(n.parent) if obs.node(c).role == n.role]
                    header = self.column_header(sig, n.i) if sig in self.obs else None
                    # a column with a declared header is that column wherever it stands:
                    # judged by its header, not by its index (`semabi.eval.v4_columns`)
                    ppos = ppos + ((n.role, f"@{header}" if header else sibs.index(n.i)),)
                    key_pos = paths[n.i]
                    # and in every view that renders the same table.  The view skeleton
                    # told two tables apart that stand at the same place in two views
                    # (vet's vets and its patients) and split one table by whatever else
                    # the view showed (blend's draws with and without a placeholder row).
                    # A table declares what it is: its header row.
                    t = n.parent
                    while t >= 0 and obs.node(t).role != "table":
                        t = obs.node(t).parent
                    if t >= 0 and t in table_headers:
                        # the set of declared headers, not their order: the same table
                        # rendered with its columns rearranged is the same table
                        skel_key = ("headers",) + tuple(sorted(table_headers[t]))
                elif n.role in WIDGET_ROLES:
                    # Two buttons side by side are two controls, not one control with two
                    # values: `Sign on` and `Sign off` are told apart by their place, and
                    # each is pooled only with itself in the other rows.
                    sibs = [c for c in obs.children(n.parent) if obs.node(c).role == n.role]
                    ppos = ppos + ((n.role, sibs.index(n.i)),)
            else:
                ppos = self.position_idx(obs, n.parent)
            self.variation_key[(sig, n.i)] = (key_pos, ppos, skel_key)
            if not self.learning:
                continue
            tt = self.templates.setdefault(pos, TextTemplate(pos))
            tv = self.templates_v.setdefault((key_pos, ppos, skel_key), TextTemplate(key_pos))
            self._seen.update(tokens(node_text(n)))
            for o in n.options or ():
                self._seen.update(tokens(o))
            if node_text(n) and (sig, n.i) not in self.header:
                tt.strings[node_text(n)] += 1
                tt.n += 1
                tv.strings[node_text(n)] += 1
                tv.n += 1
                if n.role not in ("button", "link", "checkbox", "radio") or n.role in ("textbox", "combobox"):
                    self._in_nonwidget.update(tokens(node_text(n)))
                self._whole.add(node_text(n).strip())
                for o in n.options or ():
                    self._whole.add(o.strip())
        if self.learning:
            self._data = None
            self._value_paths = None

    def forget(self, sig: str) -> None:
        """Drop one observation's per-observation structure so it can be re-read.

        Used only to replace a page with its section-normalised form, which happens once, on
        first sight, before anything has been read off it.  Corpus statistics are deliberately
        left alone: the normalised page carries exactly the same text.
        """
        self.obs.pop(sig, None)
        for key in [k for k in self.nodes if k[0] == sig]:
            self.nodes.pop(key, None)
        for key in [k for k in self.position_of if k[0] == sig]:
            self.position_of.pop(key, None)
            self.variation_key.pop(key, None)
        for key in [k for k in self.header if k[0] == sig]:
            self.header.discard(key)

    def is_data(self, t: str) -> bool:
        return t in self.data_set() or t[0].isdigit()

    def value_paths(self) -> set[str]:
        """Role paths at which the corpus has seen a value.

        Computed from the text templates, which stop growing when the graph is frozen, so
        for a frozen graph this is a fact about the fitting corpus and nothing else.
        """
        if self._value_paths is None:
            d = self.data_set()
            self._value_paths = {
                pos.split("|")[0] for pos, tt in self.templates.items()
                if any(t in d or t[0].isdigit()
                       for s in tt.strings for t in tokens(s) if t[0].isalnum())}
        return self._value_paths

    def is_data_at(self, sig: str, i: int, t: str) -> bool:
        """Is this token, at this node, a value?

        The corpus vocabulary decides for every token the corpus has seen.  A token it has
        *never* seen is a different case, and the frozen model has one piece of evidence
        about it: where it is.  At a position the corpus read values from -- the name cell
        of a row, a button whose label carries the row's name -- an unseen word is a value,
        because that is what the position holds; elsewhere the model has no evidence and
        the token is left as it would have been.  Nothing changes during fitting, when every
        token has been seen; what changes is that a frozen model can recognise a row whose
        name contains a word the prefix never used -- blend's `Block 12`, which was not an
        object on any of the 267 held-out pages that rendered it.
        """
        if t[0].isdigit():
            return True
        d = self.data_set()
        if self.judge_by_collection:
            # A word admitted as a value only because it varies between the members of a
            # collection -- `on` in the duty cell, `varietal` in the style cell -- is a value
            # where it varies and wording anywhere else: `Sign on` keeps its label.  Every
            # other data token is data wherever it stands, as before.  The alternative --
            # judging every token at its position -- was tried and reads an entity name as
            # wording wherever it was the only entity ever rendered there: `North Wall` in
            # every one of a seed's return-ticket buttons, `S1` in a select whose choice
            # never changed.  Which is the same thing a global vocabulary gets wrong about
            # `Open` on the `Open North Wall` button, and there is no telling a name from a
            # state word at this layer; the name is the costlier one to lose.
            n = self.obs[sig].node(i)
            if n.role in ("combobox", "textbox"):
                return t[0].isalnum()      # what an input holds is its value, all of it
            key = self.variation_key.get((sig, i))
            if key is not None and key[1] and key[1][-1][1] != "*" and any(
                    x == "*" for _, x in key[1]) and n.role not in WIDGET_ROLES:
                # A field of a collection member -- a table column -- is judged in its
                # column, where the evidence is: what every member's value carries is the
                # column's label, what differs is the value.  `Dr` heads every name in the
                # vets table and is a label there; in the appointments' vet column, beside
                # `(unassigned)`, it is part of a value.  A vocabulary answering for the
                # whole application would have to say one thing for both.  A column with
                # a single distinct value is no evidence, and falls to the vocabulary.
                tt = self.templates_v.get(key)
                if tt is not None and len(tt.strings) >= 2 and (
                        t in tt.varying_tokens() or any(t in tokens(st) for st in tt.strings)):
                    return t in tt.varying_tokens()
                # a token the column never held is judged as any unseen token is, below
            if t in d:
                if t not in self._listed_only:
                    return True
                key = self.variation_key.get((sig, i))
                tt = self.templates_v.get(key) if key is not None else None
                if tt is None and key is not None:
                    tt = self._pooled_views.get(key[:2])
                return tt is not None and t in tt.varying_tokens()
        elif t in d:
            return True
        if t in self._seen or self.learning:
            return False
        pos = self.position_of.get((sig, i))
        return pos is not None and pos.split("|")[0] in self.value_paths()

    def is_header(self, sig: str, i: int) -> bool:
        """A first-row cell is a label row unless its text is data elsewhere (a matrix whose
        column headers name entities shown in other places)."""
        if (sig, i) not in self.header:
            return False
        n = self.obs[sig].node(i)
        d = self.data_set()
        toks = [t for t in tokens(node_text(n)) if t[0].isalnum()]
        return not toks or not any(t in d for t in toks)

    def data_tokens(self, sig: str, i: int) -> list[str]:
        """Data *spans*: maximal runs of consecutive data tokens ("Ines Halli", "Two Sisters")."""
        if self.is_header(sig, i):
            return []
        n = self.obs[sig].node(i)
        out: list[str] = []
        run: list[str] = []
        for t in tokens(node_text(n)):
            if self.is_data_at(sig, i, t):
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
        lab = self.labels(sig, i)
        if len(lab) >= 3:
            return True
        if not lab:
            # Nothing in this string is a constant word, so whatever else shares its
            # structural position, *this* string is a value and not a sentence about values.
            # The pooled test below is a corpus heuristic for feedback lines and it misfires
            # when a position collects unrelated texts: cellar's hall headings sit at the same
            # position as `Finish fermentation` and `Receive fruit`, whose four constant words
            # made `Press Hall` prose and cost the hall its key.  A sentence needs words.
            return False
        tt = (self.templates_v.get(self.variation_key.get((sig, i))) if self.judge_by_collection
              else self.templates.get(self.position_of[(sig, i)]))
        if tt is None:
            return False
        d = self.data_set()
        vocab = {t for st in tt.strings for t in tokens(st) if t[0].isalpha() and t not in d}
        return len(vocab) >= 4

    def labels(self, sig: str, i: int) -> set[str]:
        n = self.obs[sig].node(i)
        if self.is_header(sig, i):
            return set(tokens(node_text(n)))
        return {t for t in tokens(node_text(n)) if not self.is_data_at(sig, i, t)}

    def column_header(self, sig: str, i: int) -> str | None:
        """The declared header text of the column a cell stands in, or None.

        Only a table whose header row sits in a row group of its own (a `thead`) declares
        its columns; there the header is the interface's own name for the column and the
        cell's position is presentation (`semabi.eval.v4_columns`).  A cell of any other
        row, or a column with an empty header, has no column name and keeps its position."""
        obs = self.obs[sig]
        n = obs.node(i)
        if n.role != "cell" or n.parent < 0:
            return None
        cache = self.__dict__.setdefault("_column_header_cache", {})
        if (sig, i) in cache:
            return cache[(sig, i)]
        row = n.parent
        table = obs.node(row).parent
        while table >= 0 and obs.node(table).role != "table":
            table = obs.node(table).parent
        out = None
        if table >= 0:
            rows = sorted(x for x in obs.subtree(table) if obs.node(x).role == "row")
            declared = len(rows) > 1 and obs.node(rows[0]).parent != obs.node(rows[1]).parent
            if declared and row != rows[0]:
                cells = obs.children(row)
                header_cells = obs.children(rows[0])
                # a row not shaped like the header row -- the one spanning cell of "No draws
                # recorded." -- is not a member of the table's columns; giving its cell the
                # first column's name by its offset put the placeholder's words into that
                # column, where against a single ticket they made the column's own label
                # vary, and a key was named by the split that followed
                col = cells.index(i) if i in cells and len(cells) == len(header_cells) else -1
                if 0 <= col < len(header_cells):
                    text = node_text(obs.node(header_cells[col])).strip()
                    out = text or None
        cache[(sig, i)] = out
        return out

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
