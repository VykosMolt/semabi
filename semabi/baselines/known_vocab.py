"""Baseline 5: known action vocabulary.

The learner is GIVEN the hidden schema (types, attributes, relations) and the
operator signatures (names and typed parameters), executes operators directly
through the application's JSON API with perfect state observation, and must
learn only preconditions and effects. This isolates how much of the problem is
vocabulary induction versus pre/effect learning.
"""
from __future__ import annotations

import argparse
import json
import random
import urllib.request
from collections import defaultdict
from pathlib import Path

from semabi import relmodel as rm
from semabi.compiler.model import LearnedModel
from semabi.env.server import World, serve
from semabi.hidden.taskdomain import make_domain


def api(base: str, path: str, body: dict | None = None):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"}, method="POST" if body is not None else "GET")
    return json.loads(urllib.request.urlopen(req, timeout=5).read())


def state_diff(a: rm.State, b: rm.State):
    added = [o for k, o in b.objects.items() if k not in a.objects]
    removed = [o for k, o in a.objects.items() if k not in b.objects]
    attr = [(k, at, oa.attrs.get(at), b.objects[k].attrs.get(at)) for k, oa in a.objects.items() if k in b.objects
            for at in set(oa.attrs) | set(b.objects[k].attrs) if oa.attrs.get(at) != b.objects[k].attrs.get(at)]
    rel = [(r, k, a.get_rel(r, k), b.get_rel(r, k)) for r in set(a.rels) | set(b.rels) for k in a.objects if k in b.objects
           and a.get_rel(r, k) != b.get_rel(r, k)]
    return added, removed, attr, rel


def lift_effects(dom: rm.Domain, s: rm.State, s2: rm.State, binding: dict) -> tuple:
    """Lift a concrete transition to effect templates with the known params."""
    inv = {v: p for p, v in binding.items()}
    def lv(v):
        return inv.get(v, v)
    added, removed, attr, rel = state_diff(s, s2)
    effs = []
    for i, o in enumerate(added):
        effs.append(("Create", o.type, tuple(sorted((k, lv(v)) for k, v in o.attrs.items())), f"?new{i}",
                     tuple(sorted((r, lv(s2.get_rel(r, o.id))) for r in dom.relations if s2.get_rel(r, o.id)))))
    # objects not bound to params: try to anchor on a relation to a param (forall), else constant
    def anchor(oid):
        for r, rd in dom.relations.items():
            for p, v in binding.items():
                if isinstance(v, str) and v in s.objects and s.get_rel(r, oid) == v:
                    return ("forall", r, p)
        return None
    groups = defaultdict(list)
    for o in removed:
        if o.id in inv:
            effs.append(("Delete", inv[o.id]))
        else:
            groups[("Delete", anchor(o.id))].append(o.id)
    for k, at, old, new in attr:
        if k in inv:
            effs.append(("SetAttr", inv[k], at, lv(new)))
        else:
            groups[("SetAttr", anchor(k), at, lv(new))].append(k)
    for r, k, old, new in rel:
        if k in inv:
            effs.append(("SetRel", r, inv[k], lv(new)))
        else:
            groups[("SetRel", anchor(k), r, lv(new))].append(k)
    for key, ids in groups.items():
        kind, anc = key[0], key[1]
        if anc is None:
            return None  # unexplained effect on unrelated objects: cannot lift
        _, r, p = anc
        covered = set()
        for x in s.objects:
            if s.get_rel(r, x) != binding[p]:
                continue
            if kind == "SetAttr" and s.objects[x].attrs.get(key[2]) == key[3]:
                continue  # already holds: vacuous
            if kind == "SetRel" and inv.get(s.get_rel(key[2], x), s.get_rel(key[2], x)) == key[3]:
                continue
            covered.add(x)
        if set(ids) != covered:
            return None
        if kind == "Delete":
            effs.append(("DeleteIncoming", r, p))
        elif kind == "SetAttr":
            effs.append(("SetAttrIncoming", r, p, key[2], key[3]))
        else:
            effs.append(("MoveIncoming", key[2], p, key[3]))
    return tuple(sorted(effs, key=str))


def literals(dom: rm.Domain, s: rm.State, op: rm.Operator, b: dict) -> set:
    lits = set()
    objs = {p: s.objects.get(v) for p, t in op.params if t not in ("str",) for v in [b[p]]}
    for p, o in objs.items():
        if o is None:
            continue
        for at, v in o.attrs.items():
            lits.add(("AttrEq", p, at, v))
        for q, o2 in objs.items():
            if q == p or o2 is None:
                continue
            for r in dom.relations:
                lits.add(("RelHolds", r, p, q, s.get_rel(r, o.id) != o2.id))
        for r in dom.relations:
            lits.add(("NoIncoming", r, p, len(s.incoming(r, o.id)) != 0))
    for p, t in op.params:
        if t == "str" and b[p] != "":
            lits.add(("Distinct", p, ""))
    return lits


def to_effects(e: tuple) -> list[rm.Effect]:
    if e[0] == "Create":
        return [rm.Create(e[1], e[2], e[3])] + [rm.SetRel(r, e[3], t) for r, t in e[4]]
    return [to_effect(e)]


def to_effect(e: tuple) -> rm.Effect:
    k = e[0]
    if k == "Create":
        return rm.Create(e[1], e[2], e[3])
    if k == "Delete":
        return rm.Delete(e[1])
    if k == "SetAttr":
        return rm.SetAttr(e[1], e[2], e[3])
    if k == "SetRel":
        return rm.SetRel(e[1], e[2], e[3])
    if k == "DeleteIncoming":
        return rm.DeleteIncoming(e[1], e[2])
    if k == "SetAttrIncoming":
        return rm.SetAttrIncoming(e[1], e[2], e[3], e[4])
    if k == "MoveIncoming":
        return rm.MoveIncoming(e[1], e[2], e[3])
    raise ValueError(k)


def to_literal(l: tuple) -> rm.Literal:
    if l[0] == "AttrEq":
        return rm.AttrEq(l[1], l[2], l[3])
    if l[0] == "RelHolds":
        return rm.RelHolds(l[1], l[2], l[3], negate=l[4])
    if l[0] == "NoIncoming":
        return rm.NoIncoming(l[1], l[2], negate=l[3])
    if l[0] == "Distinct":
        return rm.Distinct(l[1], l[2])
    raise ValueError(l)


def learn(base: str, hidden: rm.Domain, trials_per_op: int, rng: random.Random) -> tuple[rm.Domain, dict]:
    schema = rm.Domain("known", dict(hidden.types), dict(hidden.relations), {})
    pool = ["k1", "k2", "k3", ""]
    records: dict[str, list] = defaultdict(list)
    n_calls = 0
    for name, hop in hidden.operators.items():
        sig = rm.Operator(name, list(hop.params))  # signature only
        for t in range(trials_per_op):
            if t % 6 == 0:
                api(base, "/reset", {"seed": rng.randrange(1000)})
            s = rm.State.from_json(api(base, "/api/state"))
            gs = list(rm.groundings(schema, s, sig, pool))
            if not gs:
                continue
            b = rng.choice(gs)
            res = api(base, "/api/op", {"op": name, "args": {k[1:]: v for k, v in b.items()}})
            n_calls += 1
            s2 = rm.State.from_json(api(base, "/api/state"))
            records[name].append((s, b, res["ok"], s2))
    ops = {}
    stats = {"api_calls": n_calls}
    for name, hop in hidden.operators.items():
        sig = rm.Operator(name, list(hop.params))
        by_eff: dict[tuple, list] = defaultdict(list)
        for s, b, ok, s2 in records[name]:
            eff = lift_effects(schema, s, s2, b)
            if eff is None:
                continue
            by_eff[eff].append((s, b))
        if not by_eff:
            continue
        # each distinct effect template becomes an operator variant; the empty effect is failure.
        # Vacuous merge: a template that differs from another only by forall-effects whose anchor
        # sets were empty in all its transitions is the same operator.
        def anchor_empty(eff_extra, s, b):
            for e in eff_extra:
                r, p = e[1], e[2]
                if any(s.get_rel(r, x) == b[p] for x in s.objects):
                    return False
            return True
        keys = [k for k in by_eff if k]
        for k1 in list(keys):
            for k2 in keys:
                if k1 == k2 or k1 not in by_eff or k2 not in by_eff:
                    continue
                if set(k1) < set(k2) and all(e[0].endswith("Incoming") for e in set(k2) - set(k1)):
                    extra = [e for e in k2 if e not in k1]
                    if all(anchor_empty(extra, s, b) for s, b in by_eff[k1]):
                        by_eff[k2].extend(by_eff.pop(k1))
                        break
        variants = [(eff, trs) for eff, trs in by_eff.items() if eff]
        for vi, (eff, trs) in enumerate(sorted(variants, key=lambda kv: -len(kv[1]))):
            common = None
            for s, b in trs:
                l = literals(schema, s, sig, b)
                common = l if common is None else common & l
            negs = [literals(schema, s, sig, b) for e2, trs2 in by_eff.items() if e2 != eff for s, b in trs2]
            chosen = []
            remaining = list(range(len(negs)))
            while remaining:
                best, cov = None, 0
                for l in sorted(common, key=str):
                    c = sum(1 for i in remaining if l not in negs[i])
                    if c > cov:
                        best, cov = l, c
                if best is None:
                    break
                chosen.append(best)
                remaining = [i for i in remaining if best in negs[i]]
            opname = name if vi == 0 else f"{name}_v{vi}"
            ops[opname] = rm.Operator(opname, list(hop.params), [to_literal(l) for l in chosen], [x for e in eff for x in to_effects(e)])
            stats[opname] = {"support": len(trs), "unexplained_failures": len(remaining)}
    return rm.Domain("known_vocab", dict(hidden.types), dict(hidden.relations), ops), stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="standard")
    ap.add_argument("--trials", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--port", type=int, default=8990)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    world = World(a.variant, a.seed)
    srv = serve(world, a.port)
    try:
        dom, stats = learn(f"http://127.0.0.1:{a.port}", make_domain(a.variant), a.trials, random.Random(a.seed))
    finally:
        srv.shutdown()
    M = LearnedModel(dom, {}, {"Project": "name", "Task": "title"}, meta={"baseline": "known_vocab", **stats})
    Path(a.out).mkdir(parents=True, exist_ok=True)
    M.save(Path(a.out) / "model.json")
    (Path(a.out) / "model.txt").write_text(str(dom))
    print(dom)
    print(stats)


if __name__ == "__main__":
    main()
