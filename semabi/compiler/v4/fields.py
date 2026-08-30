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
history rendered, and nothing over any other field.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

MIN_DISTINCT = 3       # a field with fewer distinct numbers has no order to speak of
GE, LT = "attr_ge", "attr_lt"


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


def holds(literal: tuple, obj) -> bool | None:
    """Whether an ordered literal is true of an object, or None when it has no number there."""
    head, _role, slot, v = literal
    x = numeric(getattr(obj, "attrs", {}).get(slot))
    if x is None:
        return None
    return x >= numeric(v) if head == GE else x < numeric(v)


def adopted(models: dict, candidates_: dict[int, dict[str, list[str]]]) -> dict[int, dict[str, list[str]]]:
    """The candidate fields some control's fitted rule orders *and* is justified in ordering:
    the rule's ordered literal covers fitting occasions with at least two distinct values of
    the field, which is what an equality on the field could not have done."""
    out: dict[int, dict[str, list[str]]] = defaultdict(dict)
    for model in models.values():
        ev = model.evidence
        if ev is None:
            continue
        for rule in model.rules:
            for lit in rule.condition:
                if lit[0] not in (GE, LT):
                    continue
                _head, role, slot, _v = lit
                tid = getattr(model.roles.get(role), "tid", None)
                if tid is None or slot not in candidates_.get(tid, {}):
                    continue
                bits = [ev.index[l] for l in rule.condition if l in ev.index]
                if len(bits) != len(rule.condition):
                    continue
                cond = 0
                for b in bits:
                    cond |= 1 << b
                covered = [i for i, m in enumerate(ev.masks) if m & cond == cond]
                values = set()
                for i in covered:
                    for l, b in ev.index.items():
                        if l[0] == "attr" and l[1] == role and l[2] == slot and ev.masks[i] & (1 << b):
                            values.add(l[3])
                if len(values) >= 2:
                    out[tid][slot] = candidates_[tid][slot]
    return dict(out)
