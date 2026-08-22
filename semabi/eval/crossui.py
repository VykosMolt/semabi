"""Cross-UI structural equivalence: compare two learned models directly,
without any hidden-domain information.

Searches over type bijections, attribute correspondences (with value maps),
and relation correspondences; operators are matched behaviourally by
simulation on synthetic states in model A's vocabulary translated to B.
"""
from __future__ import annotations

import itertools
import random
from collections import defaultdict
from dataclasses import dataclass

from semabi import relmodel as rm
from semabi.compiler.model import LearnedModel
from semabi.eval.matching import Mapping, match_operators


def _value_sets(model: LearnedModel) -> dict[tuple[str, str], set]:
    """Constant attribute values mentioned by the model's operators, per (type, attr)."""
    vals: dict[tuple[str, str], set] = defaultdict(set)
    ptypes = {}
    for op in model.domain.operators.values():
        ptypes = dict(op.params)
        for e in op.effects:
            if isinstance(e, rm.SetAttr) and not rm.is_var(e.value):
                vals[(ptypes.get(e.obj, "?"), e.attr)].add(e.value)
            if isinstance(e, rm.Create):
                for a, v in e.attrs:
                    if not rm.is_var(v):
                        vals[(e.type, a)].add(v)
        for l in op.pre:
            if isinstance(l, rm.AttrEq) and not rm.is_var(l.value):
                vals[(ptypes.get(l.obj, "?"), l.attr)].add(l.value)
    for t, td in model.domain.types.items():
        for a, kind in td.attrs.items():
            if kind == "bool":
                vals[(t, a)] |= {True, False}
    return vals


def random_states(model: LearnedModel, rng: random.Random, n: int = 30, max_objs: int = 4) -> list[rm.State]:
    vals = _value_sets(model)
    out = []
    dom = model.domain
    for i in range(n):
        s = rm.State()
        for t, td in dom.types.items():
            for k in range(rng.randint(1, max_objs)):
                key = f"{t.lower()}{i}_{k}"
                attrs = {}
                for a, kind in td.attrs.items():
                    if a == model.key_slots[t]:
                        attrs[a] = key
                    else:
                        vs = sorted(vals.get((t, a), set()), key=str)
                        attrs[a] = rng.choice(vs) if vs else None
                s.objects[f"{t}:{key}"] = rm.Obj(f"{t}:{key}", t, attrs)
        for r, rd in dom.relations.items():
            dsts = [o.id for o in s.of_type(rd.dst)]
            for o in s.of_type(rd.src):
                if dsts:
                    s.set_rel(r, o.id, rng.choice(dsts))
        out.append(s)
    return out


@dataclass
class CrossResult:
    type_map: dict
    attr_map: dict
    rel_map: dict
    ops_a: int
    ops_b: int
    equivalent: int  # A-operators with a behaviourally equivalent B-operator
    per_op: list

    @property
    def score(self) -> float:
        return self.equivalent / max(1, max(self.ops_a, self.ops_b))

    def report(self) -> str:
        lines = [f"cross-UI equivalence: {self.equivalent}/{self.ops_a} operators of A matched in B (B has {self.ops_b}); score={self.score:.2f}",
                 f"  types {self.type_map} attrs {self.attr_map} rels {self.rel_map}"]
        for r in self.per_op:
            lines.append(f"   {r['a']:6s} -> {str(r['b']):6s} pre={r['pre']:.2f} eff={r['eff']:.2f}")
        return "\n".join(lines)


def _attr_candidates(A: LearnedModel, B: LearnedModel, ta: str, tb: str, vals_a, vals_b):
    """Yield attr maps for one type pair: dict (tb, attr_b) -> (attr_a, value map a->b)."""
    attrs_a = [a for a in A.domain.types[ta].attrs if a != A.key_slots[ta]]
    attrs_b = [b for b in B.domain.types[tb].attrs if b != B.key_slots[tb]]
    if not attrs_b:
        yield {}
        return
    # each B attr maps to an A attr or nothing (injective)
    for assign in itertools.product([None] + attrs_a, repeat=len(attrs_b)):
        used = [a for a in assign if a is not None]
        if len(used) != len(set(used)):
            continue
        # value maps: bijections between value sets (when sizes match), else skip
        options = []
        for b, a in zip(attrs_b, assign):
            if a is None:
                options.append([None])
                continue
            va = sorted(vals_a.get((ta, a), set()), key=str)
            vb = sorted(vals_b.get((tb, b), set()), key=str)
            if len(va) != len(vb) or not va:
                options.append([])
                continue
            options.append([dict(zip(va, perm)) for perm in itertools.permutations(vb)])
        for combo in itertools.product(*options):
            m = {}
            for b, a, vm in zip(attrs_b, assign, combo):
                if a is not None:
                    m[(tb, b)] = (a, vm)
            yield m


def compare_models(A: LearnedModel, B: LearnedModel, seed: int = 0, n_states: int = 30) -> CrossResult:
    rng = random.Random(seed)
    states = random_states(A, rng, n_states)
    vals_a, vals_b = _value_sets(A), _value_sets(B)
    ta_names, tb_names = list(A.domain.types), list(B.domain.types)
    best: CrossResult | None = None
    for k in range(min(len(ta_names), len(tb_names)), 0, -1):
        for tb_sub in itertools.combinations(tb_names, k):
            for ta_perm in itertools.permutations(ta_names, k):
                type_map = dict(zip(tb_sub, ta_perm))  # B type -> A type  (B plays "learned", A plays "hidden")
                key_attr = {tb: A.key_slots[ta] for tb, ta in type_map.items()}
                attr_iters = [list(_attr_candidates(A, B, ta, tb, vals_a, vals_b)) for tb, ta in type_map.items()]
                # relation map: B rel -> A rel with matching src/dst under the type map
                rel_options = []
                for rb, rdb in B.domain.relations.items():
                    if rdb.src not in type_map or rdb.dst not in type_map:
                        rel_options.append([(rb, None)])
                        continue
                    cands = [ra for ra, rda in A.domain.relations.items() if rda.src == type_map[rdb.src] and rda.dst == type_map[rdb.dst]]
                    rel_options.append([(rb, ra) for ra in cands] or [(rb, None)])
                for attr_combo in itertools.product(*attr_iters):
                    for rel_combo in itertools.product(*rel_options):
                        m = Mapping(type_map=dict(type_map), key_attr=key_attr)
                        for d in attr_combo:
                            m.attr_map.update(d)
                        m.rel_map = {rb: ra for rb, ra in rel_combo if ra is not None}
                        res = match_operators(A.domain, B, m, states, seed)
                        eq = [r for r in res if r.learned_op and r.eff_agree >= 0.9 and r.pre_agree >= 0.9]
                        cr = CrossResult(dict(type_map), {f"{t}.{b}": a for (t, b), (a, _) in m.attr_map.items()}, dict(m.rel_map),
                                         len(A.domain.operators), len(B.domain.operators), len(eq),
                                         [{"a": r.hidden_op, "b": r.learned_op, "pre": r.pre_agree, "eff": r.eff_agree} for r in res])
                        if best is None or cr.equivalent > best.equivalent:
                            best = cr
        if best and best.equivalent > 0:
            break
    return best
