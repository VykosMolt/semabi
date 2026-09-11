"""A field's theory: what kind of thing its values are, as a hypothesis behaviour decides.

Every field is NOMINAL until shown otherwise: its values are names, and a guard may say a
value is or is not one of them.  ORDERED is a candidate theory for a field whose values are
numbers -- blend's committed gallons, where the application bottles at 2, 3, 4 and 5 and
refuses at 0 and 1, and where a frozen ordered hypothesis was right at 9 and at 0, values no
history had shown, while the learner's equality guard was refuted at 0
(`docs/v4_frontier.md`).  A ticket number is also a number, and it is nominal: draws are
keyed by it and nothing compares two.  So the theory is decided per field and never by the
shape of a token: ORDERED is *proposed* for a numeric field and *adopted* only when an
ordered rule over it is justified on the history and says something an equality cannot --
it covers occasions with more than one value of the field.  Adopted, it gives the outcome
language two literals over that field, ``x >= v`` and ``x < v`` for the thresholds the
history rendered, and nothing over any other field.  Between two bound objects it also gives
``p.a >= q.b`` and ``p.a < q.b`` over their ordered fields -- a berth takes a vessel no longer
than its capacity -- judged and adopted by the same discipline, over pairs of values.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

MIN_DISTINCT = 3       # a field with fewer distinct numbers has no order to speak of
GE, LT = "attr_ge", "attr_lt"
CMP_GE, CMP_LT = "attr_cmp_ge", "attr_cmp_lt"


def numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def candidates(states, types) -> dict[int, dict[str, list[str]]]:
    """ORDERED candidates: ``tid -> slot -> thresholds`` for every non-key attribute whose
    rendered values are all numbers and take at least ``MIN_DISTINCT`` distinct ones."""
    seen: dict[tuple[int, str], dict[float, str]] = defaultdict(dict)
    bad: set[tuple[int, str]] = set()
    for state in states:
        for o in state.objs.values():
            key_slot = getattr(types.get(o.tid), "key_slot", None) if hasattr(types, "get") else None
            for slot, value in o.attrs.items():
                if value is None or slot == key_slot or (o.tid, slot) in bad:
                    continue
                x = numeric(value)
                if x is None:
                    bad.add((o.tid, slot))
                    continue
                seen[(o.tid, slot)].setdefault(x, str(value).strip())
    out: dict[int, dict[str, list[str]]] = defaultdict(dict)
    for (tid, slot), values in seen.items():
        if (tid, slot) in bad or len(values) < MIN_DISTINCT:
            continue
        out[tid][slot] = [values[x] for x in sorted(values)]
    return dict(out)


def clocks(sequences, candidates_: dict[int, dict[str, list[str]]]) -> set[tuple[int, str]]:
    """The candidate fields that rise on some object and never fall on any, within any
    episode of the history: a value that only ever rises is a clock, and an order over it
    is an order over time.  Harbour's *calls logged* separated bookings from refusals on
    the corpus that was built to separate a comparison from a pair of thresholds, by the
    accident of when each was asked; the history alone does not adopt such an order, a
    retained intervention still can.  ``sequences`` are the states of each episode in step
    order; a rise needs two witnesses, as a rule does."""
    rises: dict[tuple[int, str], int] = defaultdict(int)
    falls: dict[tuple[int, str], int] = defaultdict(int)
    for states in sequences:
        last: dict[tuple, float] = {}
        for state in states:
            for o in state.objs.values():
                for slot in candidates_.get(o.tid, {}):
                    x = numeric(o.attrs.get(slot))
                    if x is None:
                        continue
                    key = (o.tid, o.key, slot)
                    if key in last and x != last[key]:
                        (rises if x > last[key] else falls)[(o.tid, slot)] += 1
                    last[key] = x
    return {field for field, n in rises.items() if n >= 2 and not falls[field]}


def literals(role: str, obj, ordered: dict[int, dict[str, list[str]]]) -> set[tuple]:
    """The ordered literals true of one bound object under the fields' theories."""
    out: set[tuple] = set()
    for slot, thresholds in ordered.get(getattr(obj, "tid", None), {}).items():
        x = numeric(getattr(obj, "attrs", {}).get(slot))
        if x is None:
            continue
        for v in thresholds:
            out.add((GE, role, slot, v) if x >= numeric(v) else (LT, role, slot, v))
    return out


def pair_literals(binding: dict, ordered: dict[int, dict[str, list[str]]],
                  pairs: frozenset | None = None) -> set[tuple]:
    """The comparisons true between the ordered fields of any two bound objects, or
    between two ordered fields of one (a job's required span against the work span of the
    station its page shows).

    ``pairs`` restricts them to the comparisons a fitted rule justified (`adopted_pairs`):
    a field is ordered only where a rule ordered it, and a comparison between two fields is
    in the language only where a rule compared them -- a ticket's length against a vessel's
    is one, a ticket's length against a count of calls is not.  None leaves every pair
    available, which is what the first learning pass needs to find them."""
    fields_ = []
    for role, obj in binding.items():
        tid = getattr(obj, "tid", None)
        for slot in ordered.get(tid, {}):
            x = numeric(getattr(obj, "attrs", {}).get(slot))
            if x is not None:
                fields_.append((role, tid, slot, x))
    return {(CMP_GE if xp >= xq else CMP_LT, p, sp, q, sq)
            for p, tp, sp, xp in fields_ for q, tq, sq, xq in fields_
            if (p != q or sp != sq) and (pairs is None or frozenset(((tp, sp), (tq, sq))) in pairs)}


def holds(literal: tuple, obj) -> bool | None:
    """Whether an ordered literal is true of an object, or None when it has no number there."""
    head, _role, slot, v = literal
    x = numeric(getattr(obj, "attrs", {}).get(slot))
    if x is None:
        return None
    return x >= numeric(v) if head == GE else x < numeric(v)


def holds_pair(literal: tuple, p_obj, q_obj) -> bool | None:
    head, _p, slot_p, _q, slot_q = literal
    xp = numeric(getattr(p_obj, "attrs", {}).get(slot_p))
    xq = numeric(getattr(q_obj, "attrs", {}).get(slot_q))
    if xp is None or xq is None:
        return None
    return xp >= xq if head == CMP_GE else xp < xq


def ordered_fields(literal: tuple) -> tuple[tuple[str, str], ...]:
    """The (role, slot) fields an ordered literal compares; none for any other literal."""
    if literal[0] in (GE, LT):
        return ((literal[1], literal[2]),)
    if literal[0] in (CMP_GE, CMP_LT):
        return ((literal[1], literal[2]), (literal[3], literal[4]))
    return ()


SIDECAR = "field_theories_v4.json"


def corroborated(run_dir, candidates_) -> set[tuple[int, str]]:
    """Field theories a retained intervention corroborated, beside a history.

    Blend's committed gallons: the fitting prefix refuses at 0 only, so the history alone
    cannot tell an order from an equality there -- what did was the frozen ordered
    hypothesis being right at 9 and at 0 on the live application while the equality guard
    was refuted (`runs/v4/blend_bottle_intervention`).  That answer is written beside the
    history as ``field_theories_v4.json`` -- the theory, the attribute, the intervention --
    and read here, so the learner that posed the question consumes it as evidence.  A
    candidate field is named by its attribute (`attr:Committed gal#0`), as the sidecar is."""
    from pathlib import Path
    import json

    path = Path(run_dir) / SIDECAR
    if not path.is_file():
        return set()
    wanted = {t["attribute"] for t in json.loads(path.read_text()).get("theories", [])
              if t.get("theory") == "ORDERED"}
    return {(tid, slot) for tid, slots in candidates_.items() for slot in slots if slot in wanted}


def adopted(models: dict, candidates_: dict[int, dict[str, list[str]]],
            corroborated_: set | None = None, clocks_: set | None = None) -> dict[int, dict[str, list[str]]]:
    """The candidate fields some control's fitted rule orders *and* is justified in ordering,
    or that a retained intervention corroborated (`corroborated`).

    A clock (`clocks`) is not adopted from the history alone.  Two things must hold of the
    rule's ordered literal ``x >= v`` (or ``x < v``) on the control's fitting occasions.  It covers occasions with at least two distinct values of
    the field -- what an equality could not have said.  And its threshold is witnessed on
    *both* sides: occasions of the rule's event on the side it names, and occasions of some
    other event on the other side.  Blend's `committed >= 2 -> bottled` has refusals at 0
    and 1 below it; cellar's `capacity < 4000 -> already washed` had every washed vessel
    below 4000 and one vessel above -- a threshold witnessed on the far side by a single
    value is that instance, not an order, so the far side needs two values as well
    (the version space's own `MIN_COVER` for a rule, applied to the order).  A comparison
    between two objects' fields is judged the same way over pairs of values, and adopts
    both fields."""
    out: dict[int, dict[str, list[str]]] = defaultdict(dict)
    for tid, slot in (corroborated_ or ()):
        if slot in candidates_.get(tid, {}):
            out[tid][slot] = candidates_[tid][slot]
    for _lit, fields_ in _justified(models, candidates_):
        if any((t, slot_t) in (clocks_ or ()) and (t, slot_t) not in (corroborated_ or ())
               for t, slot_t in fields_):
            continue
        for t, slot_t in fields_:
            out[t][slot_t] = candidates_[t][slot_t]
    return dict(out)


def adopted_pairs(models: dict, candidates_: dict[int, dict[str, list[str]]],
                  adopted_: dict | None = None) -> frozenset:
    """The comparisons some fitted rule justified, as unordered pairs of (type, field),
    over the adopted fields."""
    return frozenset(frozenset(fields_) for lit, fields_ in _justified(models, candidates_)
                     if lit[0] in (CMP_GE, CMP_LT)
                     and (adopted_ is None or all(slot in adopted_.get(t, {}) for t, slot in fields_)))


def _justified(models: dict, candidates_: dict[int, dict[str, list[str]]]):
    """Every ordered literal of a fitted rule that passes the discipline, with its
    (type, field) pairs."""
    for model in models.values():
        ev = model.evidence
        if ev is None:
            continue
        for rule in model.rules:
            bits = [ev.index[l] for l in rule.condition if l in ev.index]
            if len(bits) != len(rule.condition):
                continue
            cond = 0
            for b in bits:
                cond |= 1 << b
            covered = [i for i, m in enumerate(ev.masks) if m & cond == cond]
            for lit in rule.condition:
                fields_ = [(getattr(model.roles.get(role), "tid", None), slot)
                           for role, slot in ordered_fields(lit)]
                if not fields_ or any(slot not in candidates_.get(tid, {}) for tid, slot in fields_):
                    continue
                if lit[0] in (GE, LT):
                    value_of = _field_values(ev, lit[1], lit[2])
                    threshold = numeric(lit[3])
                    named_side = (lambda x: x >= threshold) if lit[0] == GE else (lambda x: x < threshold)
                else:
                    value_of = _pair_values(ev, lit[1], lit[2], lit[3], lit[4])
                    named_side = (lambda x: x[0] >= x[1]) if lit[0] == CMP_GE else (lambda x: x[0] < x[1])
                values = {value_of[i] for i in covered if i in value_of}
                other_side = {x for i, x in value_of.items()
                              if not named_side(x) and ev.events[i] != rule.event}
                # more than one value on the far side as well: a single instance there is
                # that instance -- cellar's one 4000-gallon vessel -- and not an order.
                # A comparison must vary in each of its fields on each side: distinct
                # pairs are cheap, and a field constant across them is not ordered.
                if _varies(values) and _varies(other_side):
                    yield lit, fields_


def _varies(values: set) -> bool:
    if len(values) < 2:
        return False
    if not isinstance(next(iter(values)), tuple):
        return True
    return all(len({v[k] for v in values}) >= 2 for k in (0, 1))


def _pair_values(ev, p: str, slot_p: str, q: str, slot_q: str) -> dict[int, tuple[float, float]]:
    a, b = _field_values(ev, p, slot_p), _field_values(ev, q, slot_q)
    return {i: (a[i], b[i]) for i in a if i in b}


def _field_values(ev, role: str, slot: str) -> dict[int, float]:
    """Each fitting occasion's numeric value of a field, from the equality literals."""
    out: dict[int, float] = {}
    for l, b in ev.index.items():
        if l[0] == "attr" and l[1] == role and l[2] == slot:
            x = numeric(l[3])
            if x is None:
                continue
            for i, m in enumerate(ev.masks):
                if m & (1 << b):
                    out[i] = x
    return out
