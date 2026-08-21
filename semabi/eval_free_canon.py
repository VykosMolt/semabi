"""Compiler-side canonical form for learned states (id-free, key-based).
Separate module so the compiler never imports semabi.eval."""
from __future__ import annotations

from semabi import relmodel as rm


def canonical_learned(s: rm.State, model) -> tuple:
    def key_of(oid):
        o = s.objects[oid]
        return (o.type, o.attrs.get(model.key_slots.get(o.type, ""), oid))
    objs = tuple(sorted((o.type, tuple(sorted((k, v) for k, v in o.attrs.items()))) for o in s.objects.values()))
    rels = tuple(sorted((r, key_of(a), key_of(b)) for r, d in s.rels.items() for a, b in d.items() if a in s.objects and b in s.objects))
    return (objs, rels)
