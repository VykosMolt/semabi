"""Matching mentions across views by what happens to them.

Two mentions in different views are the same entity if what happens to one happens to the
other: both change, appear or disappear in overlapping intervals. Repeated co-change with
no conflicting partner is evidence for the match.

This verifies matches proposed elsewhere and proposes its own. Each carries a status:
untested, supported by two or more consistent events, contradicted by a co-change with a
different partner, or unresolved where the evidence goes both ways.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from semabi.compiler.v2.hypotheses import Hypotheses, UnitHyp, UnitInstance


@dataclass
class Alias:
    a_template: str
    a_key: str
    b_template: str
    b_key: str
    status: str = "UNTESTED"
    support: int = 0
    conflicts: int = 0
    source: str = "cochange"


@dataclass
class ChangeEvent:
    template: str
    key: str
    lo: int  # last visit step where the old filling was seen (exclusive)
    hi: int  # visit step where the new filling was seen (inclusive)
    kind: str  # change | appear | vanish
    new_values: frozenset = frozenset()  # values that appeared in the filling (change/appear)


class Associator:
    def __init__(self, H: Hypotheses, step_sigs: list[str]):
        self.H = H
        self.step_sigs = step_sigs
        self.events: list[ChangeEvent] = []
        self.aliases: dict[tuple[str, str, str], Alias] = {}  # (a_template, a_key, b_template) -> alias

    # ------------------------------------------------------------ events
    def collect(self, min_gap: int = 1) -> None:
        """Change events per (unit template, key) between consecutive visits of the unit's region."""
        H = self.H
        fill_at: dict[str, dict[str, dict[str, tuple]]] = defaultdict(lambda: defaultdict(dict))  # t -> sig -> key -> filling
        seen_region: dict[str, set[str]] = defaultdict(set)  # template -> sigs in which the region (any instance) is visible
        for t, u in H.units.items():
            if not u.key_slot:
                continue
            for ui in u.instances:
                k = ui.slots.get(u.key_slot)
                if k is None:
                    continue
                f = [(s, v) for s, v in ui.slots.items() if not s.endswith("~") and not s.endswith("!") and "|" not in s and s != u.key_slot]
                pk = H._parent_key(ui)
                if pk is not None:
                    f.append(("@parent", pk))  # where it is shown is part of what happened to it
                fill_at[t][ui.sig][k] = tuple(sorted(f))
                seen_region[t].add(ui.sig)
        for t in fill_at:
            last_visit: int | None = None
            last: dict[str, tuple] = {}
            for i, sig in enumerate(self.step_sigs):
                if sig not in seen_region[t]:
                    continue
                cur = fill_at[t].get(sig, {})
                if last_visit is not None:
                    for k, f in cur.items():
                        if k not in last:
                            self.events.append(ChangeEvent(t, k, last_visit, i, "appear", frozenset(v for _, v in f)))
                        elif last[k] != f:
                            nv = frozenset(v for _, v in f) - frozenset(v for _, v in last[k])
                            self.events.append(ChangeEvent(t, k, last_visit, i, "change", nv))
                    for k in last:
                        if k not in cur:
                            self.events.append(ChangeEvent(t, k, last_visit, i, "vanish"))
                last, last_visit = cur, i

    # ------------------------------------------------------------ co-change
    def cochange(self, pairs: list[tuple[str, str]] | None = None, min_support: int = 2) -> list[Alias]:
        """Aliases between keys of unit templates whose change events overlap in time.
        Events are precise when the interval is short; an alias needs >= min_support
        co-change events and must be the dominant partner on both sides."""
        by_t: dict[str, list[ChangeEvent]] = defaultdict(list)
        for e in self.events:
            by_t[e.template].append(e)
        templates = list(by_t)
        cand = pairs or [(a, b) for i, a in enumerate(templates) for b in templates[i + 1:]]
        out = []
        for ta, tb in cand:
            if ta == tb or not by_t.get(ta) or not by_t.get(tb):
                continue
            co: Counter = Counter()
            for ea in by_t[ta]:
                for eb in by_t[tb]:
                    if ea.hi - ea.lo > 2 and eb.hi - eb.lo > 2:
                        continue  # both imprecise (neither region was revisited soon)
                    if not (ea.lo < eb.hi and eb.lo < ea.hi):
                        continue  # intervals do not overlap
                    # the same thing happened to both: a shared new value (a gallery name in the
                    # catalogue row and the gallery the floor slot appeared in), or both vanished
                    if ea.kind == "vanish" or eb.kind == "vanish":
                        if ea.kind != eb.kind:
                            continue
                    elif not (ea.new_values & eb.new_values):
                        continue
                    co[(ea.key, eb.key)] += 1
            if not co:
                continue
            tot_a: Counter = Counter()
            tot_b: Counter = Counter()
            for (ka, kb), c in co.items():
                tot_a[ka] += c
                tot_b[kb] += c
            for (ka, kb), c in co.items():
                if c < max(3, min_support):
                    continue
                if c / tot_a[ka] < 0.8 or c / tot_b[kb] < 0.8:
                    continue  # not the dominant partner
                al = Alias(ta, ka, tb, kb, "SUPPORTED", c, tot_a[ka] - c + tot_b[kb] - c)
                self.aliases[(ta, ka, tb)] = al
                out.append(al)
        return out

    def verify(self, al: Alias) -> Alias:
        """Status of a proposed alias from the co-change record."""
        by_t: dict[str, list[ChangeEvent]] = defaultdict(list)
        for e in self.events:
            by_t[e.template].append(e)
        sup = con = 0
        for ea in by_t.get(al.a_template, []):
            if ea.key != al.a_key:
                continue
            partners = {eb.key for eb in by_t.get(al.b_template, [])
                        if not (ea.hi - ea.lo > 2 and eb.hi - eb.lo > 2) and ea.lo < eb.hi and eb.lo < ea.hi
                        and ((ea.kind == "vanish") == (eb.kind == "vanish")) and (ea.kind == "vanish" or (ea.new_values & eb.new_values))}
            if al.b_key in partners:
                sup += 1
            elif partners:
                con += 1
        al.support, al.conflicts = sup, con
        al.status = "SUPPORTED" if sup >= 2 and con == 0 else "CONTRADICTED" if con >= 2 and sup == 0 else "UNRESOLVED" if sup and con else "UNTESTED"
        return al

    def report(self) -> str:
        lines = [f"{len(self.events)} change events"]
        for al in self.aliases.values():
            lines.append(f"  {al.a_key!r} ({al.a_template[:30]}) ~ {al.b_key!r} ({al.b_template[:30]}): {al.status} +{al.support} -{al.conflicts} [{al.source}]")
        return "\n".join(lines)
