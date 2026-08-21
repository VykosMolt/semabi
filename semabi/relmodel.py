"""Domain-free typed relational action language.

Used both by the hidden evaluator domains and by the compiler's learned
models, so that the two can be compared structurally. Contains no domain
content.

A State is a set of typed objects with attributes plus functional binary
relations. Operators have typed parameters, preconditions (conjunction of
literals) and effects (ordered list of primitive effects).
"""
from __future__ import annotations

import copy
import itertools
from dataclasses import dataclass, field
from typing import Any, Iterator

ObjId = str


# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------

@dataclass
class TypeDef:
    name: str
    attrs: dict[str, str] = field(default_factory=dict)  # attr -> "str"|"bool"|"int"


@dataclass
class RelationDef:
    name: str
    src: str  # type name
    dst: str  # type name
    # all relations are functional in src (each src object has <= 1 dst)


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------

@dataclass
class Obj:
    id: ObjId
    type: str
    attrs: dict[str, Any] = field(default_factory=dict)


@dataclass
class State:
    objects: dict[ObjId, Obj] = field(default_factory=dict)
    rels: dict[str, dict[ObjId, ObjId]] = field(default_factory=dict)
    _counter: int = 0

    def copy(self) -> "State":
        s = State.__new__(State)
        s.objects = {k: Obj(o.id, o.type, dict(o.attrs)) for k, o in self.objects.items()}
        s.rels = {r: dict(d) for r, d in self.rels.items()}
        s._counter = self._counter
        return s

    def fresh_id(self, prefix: str = "o") -> ObjId:
        self._counter += 1
        return f"{prefix}{self._counter}"

    def add(self, type_: str, attrs: dict[str, Any] | None = None, id_: ObjId | None = None) -> Obj:
        oid = id_ or self.fresh_id(type_[:1].lower())
        o = Obj(oid, type_, dict(attrs or {}))
        self.objects[oid] = o
        return o

    def remove(self, oid: ObjId) -> None:
        self.objects.pop(oid, None)
        for rel in self.rels.values():
            rel.pop(oid, None)
            for k in [k for k, v in rel.items() if v == oid]:
                rel.pop(k)

    def set_rel(self, rel: str, a: ObjId, b: ObjId | None) -> None:
        d = self.rels.setdefault(rel, {})
        if b is None:
            d.pop(a, None)
        else:
            d[a] = b

    def get_rel(self, rel: str, a: ObjId) -> ObjId | None:
        return self.rels.get(rel, {}).get(a)

    def incoming(self, rel: str, b: ObjId) -> list[ObjId]:
        return sorted(a for a, v in self.rels.get(rel, {}).items() if v == b)

    def of_type(self, t: str) -> list[Obj]:
        return [o for o in self.objects.values() if o.type == t]

    def canonical(self) -> tuple:
        """Hashable canonical form (ids included; use `canonical_up_to_ids` for
        id-insensitive comparison)."""
        objs = tuple(sorted((o.id, o.type, tuple(sorted(o.attrs.items()))) for o in self.objects.values()))
        rels = tuple(sorted((r, tuple(sorted(d.items()))) for r, d in self.rels.items() if d))
        return (objs, rels)

    def to_json(self) -> dict:
        return {
            "objects": [{"id": o.id, "type": o.type, "attrs": o.attrs} for o in self.objects.values()],
            "rels": {r: dict(d) for r, d in self.rels.items()},
            "counter": self._counter,
        }

    @classmethod
    def from_json(cls, j: dict) -> "State":
        s = cls()
        for o in j["objects"]:
            s.objects[o["id"]] = Obj(o["id"], o["type"], dict(o["attrs"]))
        s.rels = {r: dict(d) for r, d in j["rels"].items()}
        s._counter = j.get("counter", 0)
        return s


# --------------------------------------------------------------------------
# Formulas (preconditions) and effects
# --------------------------------------------------------------------------
# Terms: parameter names (strings starting with '?'), or constants.

def is_var(t: Any) -> bool:
    return isinstance(t, str) and t.startswith("?")


@dataclass(frozen=True)
class AttrEq:
    """attr(obj) == value. value may be a constant or a ?param."""
    obj: str
    attr: str
    value: Any
    negate: bool = False

    def __str__(self) -> str:
        op = "!=" if self.negate else "=="
        return f"{self.attr}({self.obj}) {op} {self.value!r}"


@dataclass(frozen=True)
class RelHolds:
    """rel(a, b). b may be a ?param."""
    rel: str
    a: str
    b: str
    negate: bool = False

    def __str__(self) -> str:
        s = f"{self.rel}({self.a}, {self.b})"
        return f"not {s}" if self.negate else s


@dataclass(frozen=True)
class NoIncoming:
    """No object x with rel(x, obj)."""
    rel: str
    obj: str
    negate: bool = False

    def __str__(self) -> str:
        s = f"no_incoming({self.rel}, {self.obj})"
        return f"not {s}" if self.negate else s


@dataclass(frozen=True)
class Distinct:
    a: str
    b: str

    def __str__(self) -> str:
        return f"{self.a} != {self.b}"


Literal = AttrEq | RelHolds | NoIncoming | Distinct


@dataclass(frozen=True)
class Create:
    type: str
    attrs: tuple[tuple[str, Any], ...] = ()  # attr -> const or ?param
    bind: str = "?result"

    def __str__(self) -> str:
        a = ", ".join(f"{k}={v}" for k, v in self.attrs)
        return f"{self.bind} := new {self.type}({a})"


@dataclass(frozen=True)
class Delete:
    obj: str

    def __str__(self) -> str:
        return f"delete {self.obj}"


@dataclass(frozen=True)
class SetAttr:
    obj: str
    attr: str
    value: Any

    def __str__(self) -> str:
        return f"{self.attr}({self.obj}) := {self.value!r}"


@dataclass(frozen=True)
class SetRel:
    rel: str
    a: str
    b: str | None  # None clears

    def __str__(self) -> str:
        return f"{self.rel}({self.a}) := {self.b}"


@dataclass(frozen=True)
class DeleteIncoming:
    """Delete every x with rel(x, obj) (cascade)."""
    rel: str
    obj: str

    def __str__(self) -> str:
        return f"delete all x: {self.rel}(x, {self.obj})"


@dataclass(frozen=True)
class MoveIncoming:
    """For every x with rel(x, src): rel(x) := dst."""
    rel: str
    src: str
    dst: str  # ?param or constant obj id

    def __str__(self) -> str:
        return f"forall x: {self.rel}(x, {self.src}) -> {self.rel}(x) := {self.dst}"


@dataclass(frozen=True)
class SetAttrIncoming:
    """For every x with rel(x, obj): attr(x) := value."""
    rel: str
    obj: str
    attr: str
    value: Any

    def __str__(self) -> str:
        return f"forall x: {self.rel}(x, {self.obj}) -> {self.attr}(x) := {self.value!r}"


Effect = Create | Delete | SetAttr | SetRel | DeleteIncoming | MoveIncoming | SetAttrIncoming


@dataclass
class Operator:
    name: str
    params: list[tuple[str, str]]  # (?name, type) ; type "str" for free strings
    pre: list[Literal] = field(default_factory=list)
    effects: list[Effect] = field(default_factory=list)

    def __str__(self) -> str:
        ps = ", ".join(f"{n}: {t}" for n, t in self.params)
        lines = [f"{self.name}({ps})"]
        if self.pre:
            lines.append("  pre: " + " & ".join(str(p) for p in self.pre))
        for e in self.effects:
            lines.append("  eff: " + str(e))
        return "\n".join(lines)


@dataclass
class Domain:
    name: str
    types: dict[str, TypeDef]
    relations: dict[str, RelationDef]
    operators: dict[str, Operator]

    def __str__(self) -> str:
        out = [f"domain {self.name}"]
        for t in self.types.values():
            out.append(f"type {t.name}({', '.join(f'{a}: {k}' for a, k in t.attrs.items())})")
        for r in self.relations.values():
            out.append(f"rel {r.name}({r.src}, {r.dst})")
        for o in self.operators.values():
            out.append(str(o))
        return "\n".join(out)


# --------------------------------------------------------------------------
# Interpreter
# --------------------------------------------------------------------------

class PreconditionError(Exception):
    pass


def _resolve(term: Any, binding: dict[str, Any]) -> Any:
    if is_var(term):
        if term not in binding:
            raise KeyError(f"unbound {term}")
        return binding[term]
    return term


def check_literal(lit: Literal, state: State, binding: dict[str, Any]) -> bool:
    if isinstance(lit, AttrEq):
        oid = _resolve(lit.obj, binding)
        if oid not in state.objects:
            return False
        val = state.objects[oid].attrs.get(lit.attr)
        res = val == _resolve(lit.value, binding)
        return (not res) if lit.negate else res
    if isinstance(lit, RelHolds):
        a = _resolve(lit.a, binding)
        b = _resolve(lit.b, binding)
        res = state.get_rel(lit.rel, a) == b
        return (not res) if lit.negate else res
    if isinstance(lit, NoIncoming):
        o = _resolve(lit.obj, binding)
        res = len(state.incoming(lit.rel, o)) == 0
        return (not res) if lit.negate else res
    if isinstance(lit, Distinct):
        return _resolve(lit.a, binding) != _resolve(lit.b, binding)
    raise TypeError(lit)


def check_pre(op: Operator, domain: Domain, state: State, binding: dict[str, Any]) -> str | None:
    """Return None if applicable, else a reason string."""
    for pname, ptype in op.params:
        if pname not in binding:
            return f"missing {pname}"
        v = binding[pname]
        if ptype in ("str", "int", "bool"):
            continue
        if v not in state.objects:
            return f"{pname}: no such object {v}"
        if state.objects[v].type != ptype:
            return f"{pname}: {v} is {state.objects[v].type}, expected {ptype}"
    for lit in op.pre:
        if not check_literal(lit, state, binding):
            return f"precondition failed: {lit}"
    return None


def apply_effects(op: Operator, state: State, binding: dict[str, Any]) -> tuple[State, dict[str, Any]]:
    s = state.copy()
    b = dict(binding)
    for e in op.effects:
        if isinstance(e, Create):
            attrs = {k: _resolve(v, b) for k, v in e.attrs}
            o = s.add(e.type, attrs)
            b[e.bind] = o.id
        elif isinstance(e, Delete):
            s.remove(_resolve(e.obj, b))
        elif isinstance(e, SetAttr):
            oid = _resolve(e.obj, b)
            if oid in s.objects:
                s.objects[oid].attrs[e.attr] = _resolve(e.value, b)
        elif isinstance(e, SetRel):
            s.set_rel(e.rel, _resolve(e.a, b), None if e.b is None else _resolve(e.b, b))
        elif isinstance(e, DeleteIncoming):
            for x in s.incoming(e.rel, _resolve(e.obj, b)):
                s.remove(x)
        elif isinstance(e, MoveIncoming):
            dst = _resolve(e.dst, b)
            for x in s.incoming(e.rel, _resolve(e.src, b)):
                s.set_rel(e.rel, x, dst)
        elif isinstance(e, SetAttrIncoming):
            val = _resolve(e.value, b)
            for x in s.incoming(e.rel, _resolve(e.obj, b)):
                if x in s.objects:
                    s.objects[x].attrs[e.attr] = val
        else:
            raise TypeError(e)
    return s, b


def apply(domain: Domain, state: State, op_name: str, binding: dict[str, Any]) -> tuple[State, dict[str, Any]]:
    op = domain.operators[op_name]
    reason = check_pre(op, domain, state, binding)
    if reason is not None:
        raise PreconditionError(reason)
    return apply_effects(op, state, binding)


def groundings(domain: Domain, state: State, op: Operator, string_pool: list[str]) -> Iterator[dict[str, Any]]:
    """Enumerate bindings (objects of the right type; strings from pool)."""
    choices = []
    for pname, ptype in op.params:
        if ptype == "str":
            choices.append(list(string_pool))
        elif ptype == "bool":
            choices.append([True, False])
        else:
            choices.append([o.id for o in state.of_type(ptype)])
    for combo in itertools.product(*choices):
        yield dict(zip([p for p, _ in op.params], combo))


# --------------------------------------------------------------------------
# Serialization (JSON) of domains
# --------------------------------------------------------------------------

def _lit_to_json(l: Literal) -> dict:
    d = {"kind": type(l).__name__}
    d.update(l.__dict__)
    return d


def _eff_to_json(e: Effect) -> dict:
    d = {"kind": type(e).__name__}
    for k, v in e.__dict__.items():
        d[k] = [list(x) if isinstance(x, tuple) else x for x in v] if isinstance(v, tuple) else v
    return d


_LIT = {c.__name__: c for c in (AttrEq, RelHolds, NoIncoming, Distinct)}
_EFF = {c.__name__: c for c in (Create, Delete, SetAttr, SetRel, DeleteIncoming, MoveIncoming, SetAttrIncoming)}


def _lit_from_json(d: dict) -> Literal:
    d = dict(d)
    return _LIT[d.pop("kind")](**d)


def _eff_from_json(d: dict) -> Effect:
    d = dict(d)
    k = d.pop("kind")
    if k == "Create":
        d["attrs"] = tuple((a, v) for a, v in d.get("attrs", []))
    return _EFF[k](**d)


def domain_to_json(dom: Domain) -> dict:
    return {
        "name": dom.name,
        "types": [{"name": t.name, "attrs": t.attrs} for t in dom.types.values()],
        "relations": [{"name": r.name, "src": r.src, "dst": r.dst} for r in dom.relations.values()],
        "operators": [
            {
                "name": o.name,
                "params": [list(p) for p in o.params],
                "pre": [_lit_to_json(l) for l in o.pre],
                "effects": [_eff_to_json(e) for e in o.effects],
            }
            for o in dom.operators.values()
        ],
    }


def domain_from_json(j: dict) -> Domain:
    types = {t["name"]: TypeDef(t["name"], dict(t["attrs"])) for t in j["types"]}
    rels = {r["name"]: RelationDef(r["name"], r["src"], r["dst"]) for r in j["relations"]}
    ops = {}
    for o in j["operators"]:
        ops[o["name"]] = Operator(
            o["name"],
            [tuple(p) for p in o["params"]],
            [_lit_from_json(l) for l in o["pre"]],
            [_eff_from_json(e) for e in o["effects"]],
        )
    return Domain(j["name"], types, rels, ops)
