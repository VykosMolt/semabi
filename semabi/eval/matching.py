"""Structural + behavioral matching of a learned model against the hidden domain.

Names are never compared. Types are aligned through paired (hidden, learned)
states recorded during exploration; attributes/relations through value
co-variation on paired objects; operators through simulation: apply the hidden
operator and the candidate learned operator to translated states and compare
applicability and outcomes.
"""
from __future__ import annotations

import itertools
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from semabi import relmodel as rm
from semabi.compiler.model import LearnedModel


@dataclass
class Mapping:
    type_map: dict[str, str] = field(default_factory=dict)  # learned type -> hidden type
    key_attr: dict[str, str] = field(default_factory=dict)  # learned type -> hidden attr that equals the key
    attr_map: dict[tuple[str, str], tuple[str, dict]] = field(default_factory=dict)  # (L, a) -> (hidden attr, value map hidden->learned)
    rel_map: dict[str, str] = field(default_factory=dict)  # learned rel -> hidden rel
    attr_as_rel: dict[tuple[str, str], str] = field(default_factory=dict)  # (L, a) -> hidden rel (attr holds target key)
    op_map: dict[str, tuple[str, dict[str, str], float, float]] = field(default_factory=dict)  # hidden op -> (learned op, param map h->l, pre_agree, eff_agree)

    def hidden_types_covered(self) -> set[str]:
        return set(self.type_map.values())


# --------------------------------------------------------------------------
# Alignment from paired states
# --------------------------------------------------------------------------


def _pair_objects(h: rm.State, l: rm.State, m: Mapping) -> dict[str, str]:
    """learned obj id -> hidden obj id, by key attribute equality."""
    out = {}
    for L, H in m.type_map.items():
        ka = m.key_attr[L]
        by_val: dict[Any, list[str]] = defaultdict(list)
        for o in h.of_type(H):
            by_val[o.attrs.get(ka)].append(o.id)
        for o in l.of_type(L):
            key = o.attrs.get(_learned_key(l, L, o))
            cands = by_val.get(key, [])
            if len(cands) == 1:
                out[o.id] = cands[0]
    return out


def _learned_key(l: rm.State, L: str, o: rm.Obj) -> str:
    # learned object ids are "L:key"; key attr is the attr whose value equals the id suffix
    suffix = o.id.split(":", 1)[1]
    for a, v in o.attrs.items():
        if v == suffix:
            return a
    return next(iter(o.attrs))


def align(hidden_dom: rm.Domain, learned: LearnedModel, pairs: list[tuple[rm.State, rm.State]], min_agree: float = 0.75) -> Mapping:
    m = Mapping()
    ld = learned.domain
    # 1. types via key/attr set overlap
    scores = []
    for L, lt in ld.types.items():
        kl = learned.key_slots[L]
        for H, ht in hidden_dom.types.items():
            for a, kind in ht.attrs.items():
                if kind != "str":
                    continue
                js = []
                for h, l in pairs:
                    lk = set(o.attrs.get(kl) for o in l.of_type(L))
                    hk = set(o.attrs.get(a) for o in h.of_type(H))
                    if not lk and not hk:
                        continue
                    js.append(len(lk & hk) / len(lk | hk))
                if js:
                    scores.append((sum(js) / len(js), L, H, a))
    used_h = set()
    for sc, L, H, a in sorted(scores, reverse=True):
        if sc < min_agree or L in m.type_map or H in used_h:
            continue
        m.type_map[L] = H
        m.key_attr[L] = a
        used_h.add(H)
    # 2. attributes and relations via paired objects
    for L, H in m.type_map.items():
        for a in ld.types[L].attrs:
            if a == learned.key_slots[L]:
                continue
            # candidate hidden attrs
            best = None
            for b, kind in hidden_dom.types[H].attrs.items():
                if b == m.key_attr[L]:
                    continue
                co: dict[Any, Counter] = defaultdict(Counter)
                n = 0
                for h, l in pairs:
                    po = _pair_objects(h, l, m)
                    for lo in l.of_type(L):
                        ho = po.get(lo.id)
                        if ho is None:
                            continue
                        co[h.objects[ho].attrs.get(b)][lo.attrs.get(a)] += 1
                        n += 1
                if n < 3 or len(co) < 2:
                    continue
                vmap = {hv: c.most_common(1)[0][0] for hv, c in co.items()}
                agree = sum(c[vmap[hv]] for hv, c in co.items()) / n
                injective = len(set(vmap.values())) == len(vmap)
                if agree >= 0.95 and injective and (best is None or agree > best[0]):
                    best = (agree, b, vmap)
            if best:
                m.attr_map[(L, a)] = (best[1], best[2])
                continue
            # attr holding the key of a related object?
            for rname, r in hidden_dom.relations.items():
                if r.src != H:
                    continue
                L2 = next((x for x, y in m.type_map.items() if y == r.dst), None)
                if L2 is None:
                    continue
                n = hit = 0
                for h, l in pairs:
                    po = _pair_objects(h, l, m)
                    for lo in l.of_type(L):
                        ho = po.get(lo.id)
                        if ho is None:
                            continue
                        tgt = h.get_rel(rname, ho)
                        n += 1
                        if tgt and h.objects[tgt].attrs.get(m.key_attr[L2]) == lo.attrs.get(a):
                            hit += 1
                if n >= 3 and hit / n >= 0.95:
                    m.attr_as_rel[(L, a)] = rname
    for lr, lrel in ld.relations.items():
        if lrel.src not in m.type_map or lrel.dst not in m.type_map:
            continue
        for hr, hrel in hidden_dom.relations.items():
            if hrel.src != m.type_map[lrel.src] or hrel.dst != m.type_map[lrel.dst]:
                continue
            n = hit = 0
            for h, l in pairs:
                po = _pair_objects(h, l, m)
                for lo in l.of_type(lrel.src):
                    ho = po.get(lo.id)
                    if ho is None:
                        continue
                    lt = l.get_rel(lr, lo.id)
                    ht = h.get_rel(hr, ho)
                    n += 1
                    if (lt is None and ht is None) or (lt is not None and po.get(lt) == ht):
                        hit += 1
            if n >= 3 and hit / n >= 0.95:
                m.rel_map[lr] = hr
    return m


# --------------------------------------------------------------------------
# Translation hidden -> learned
# --------------------------------------------------------------------------


def translate_state(h: rm.State, hidden_dom: rm.Domain, learned: LearnedModel, m: Mapping) -> tuple[rm.State, dict[str, str]]:
    """Returns learned state and hidden id -> learned id map."""
    l = rm.State()
    idmap: dict[str, str] = {}
    inv_type = {H: L for L, H in m.type_map.items()}
    for o in h.objects.values():
        L = inv_type.get(o.type)
        if L is None:
            continue
        key = o.attrs.get(m.key_attr[L])
        lid = f"{L}:{key}"
        attrs = {learned.key_slots[L]: key}
        for a in learned.domain.types[L].attrs:
            if a == learned.key_slots[L]:
                continue
            if (L, a) in m.attr_map:
                b, vmap = m.attr_map[(L, a)]
                attrs[a] = vmap.get(o.attrs.get(b))
            elif (L, a) in m.attr_as_rel:
                r = m.attr_as_rel[(L, a)]
                tgt = h.get_rel(r, o.id)
                L2 = inv_type.get(hidden_dom.relations[r].dst)
                attrs[a] = h.objects[tgt].attrs.get(m.key_attr[L2]) if tgt and L2 else None
            else:
                attrs[a] = None
        l.objects[lid] = rm.Obj(lid, L, attrs)
        idmap[o.id] = lid
    for lr, hr in m.rel_map.items():
        for a, b in h.rels.get(hr, {}).items():
            if a in idmap and b in idmap:
                l.set_rel(lr, idmap[a], idmap[b])
    return l, idmap


def canonical_keys(s: rm.State, learned: LearnedModel) -> tuple:
    """Id-free canonical form using key attributes as identity."""
    def key_of(oid):
        o = s.objects[oid]
        return (o.type, o.attrs.get(learned.key_slots.get(o.type, ""), oid))
    objs = tuple(sorted((o.type, tuple(sorted((k, v) for k, v in o.attrs.items()))) for o in s.objects.values()))
    rels = tuple(sorted((r, key_of(a), key_of(b)) for r, d in s.rels.items() for a, b in d.items() if a in s.objects and b in s.objects))
    return (objs, rels)


# --------------------------------------------------------------------------
# Operator matching by simulation
# --------------------------------------------------------------------------


@dataclass
class OpMatchResult:
    hidden_op: str
    learned_op: str | None
    param_map: dict[str, str]
    pre_agree: float
    eff_agree: float
    n_both_applicable: int
    n_samples: int


def _param_bijections(hop: rm.Operator, lop: rm.Operator, m: Mapping):
    inv_type = {H: L for L, H in m.type_map.items()}
    hp = hop.params
    lp = lop.params
    if len(hp) != len(lp):
        return
    for perm in itertools.permutations(range(len(lp))):
        ok = True
        pm = {}
        for (hn, ht), j in zip(hp, perm):
            ln, lt = lp[j]
            if ht == "str":
                if lt != "str":
                    ok = False
                    break
            elif inv_type.get(ht) != lt:
                ok = False
                break
            pm[hn] = ln
        if ok:
            yield pm


def simulate_match(hidden_dom: rm.Domain, learned: LearnedModel, m: Mapping, hop: rm.Operator, lop: rm.Operator,
                   pm: dict[str, str], states: list[rm.State], rng: random.Random, n_samples: int = 60) -> tuple[float, float, int]:
    """Balanced sampling: half of the samples from bindings where the hidden
    precondition holds, half where it does not (when available)."""
    pool = ["zz1", "zz2", ""]
    applicable, inapplicable = [], []
    for h in states:
        for hb in rm.groundings(hidden_dom, h, hop, pool):
            (applicable if rm.check_pre(hop, hidden_dom, h, hb) is None else inapplicable).append((h, hb))
    if not applicable and not inapplicable:
        return 0.0, 0.0, 0
    k = n_samples // 2
    samples = []
    if applicable:
        samples += [applicable[i] for i in rng.sample(range(len(applicable)), min(k, len(applicable)))]
    if inapplicable:
        samples += [inapplicable[i] for i in rng.sample(range(len(inapplicable)), min(k, len(inapplicable)))]
    pre_ok = eff_ok = both = 0
    for h, hb in samples:
        h_reason = rm.check_pre(hop, hidden_dom, h, hb)
        l, idmap = translate_state(h, hidden_dom, learned, m)
        lb = {}
        for hn, v in hb.items():
            ln = pm[hn]
            lb[ln] = idmap.get(v, v) if isinstance(v, str) and v in h.objects else v
        l_reason = rm.check_pre(lop, learned.domain, l, lb)
        if (h_reason is None) == (l_reason is None):
            pre_ok += 1
        if h_reason is None and l_reason is None:
            both += 1
            h2, _ = rm.apply_effects(hop, h, hb)
            l2_pred, _ = rm.apply_effects(lop, l, lb)
            l2_true, _ = translate_state(h2, hidden_dom, learned, m)
            if canonical_keys(l2_pred, learned) == canonical_keys(l2_true, learned):
                eff_ok += 1
    n = len(samples)
    return pre_ok / n, (eff_ok / both if both else 0.0), both


def match_operators(hidden_dom: rm.Domain, learned: LearnedModel, m: Mapping, states: list[rm.State], seed: int = 0) -> list[OpMatchResult]:
    rng = random.Random(seed)
    results = []
    used = set()
    cands = []
    for hn, hop in hidden_dom.operators.items():
        for ln, lop in learned.domain.operators.items():
            for pm in _param_bijections(hop, lop, m):
                pre, eff, both = simulate_match(hidden_dom, learned, m, hop, lop, pm, states, rng)
                cands.append((eff, pre, both, hn, ln, pm))
    matched = {}
    for eff, pre, both, hn, ln, pm in sorted(cands, key=lambda x: (x[0], x[1]), reverse=True):
        if hn in matched or ln in used or both < 3:
            continue
        matched[hn] = OpMatchResult(hn, ln, pm, pre, eff, both, 0)
        used.add(ln)
    for hn in hidden_dom.operators:
        results.append(matched.get(hn, OpMatchResult(hn, None, {}, 0.0, 0.0, 0, 0)))
    m.op_map = {r.hidden_op: (r.learned_op, r.param_map, r.pre_agree, r.eff_agree) for r in results if r.learned_op}
    return results


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------


def evaluate(hidden_dom: rm.Domain, learned: LearnedModel, pairs: list[tuple[rm.State, rm.State]], states: list[rm.State],
             eff_threshold: float = 0.9, seed: int = 0) -> dict:
    m = align(hidden_dom, learned, pairs)
    ops = match_operators(hidden_dom, learned, m, states, seed)
    n_ht = len(hidden_dom.types)
    n_lt = len(learned.domain.types)
    # predicates: hidden non-key attrs + relations
    hidden_preds = [(H, a) for H, t in hidden_dom.types.items() for a in t.attrs if a not in m.key_attr.values()]
    hidden_rels = list(hidden_dom.relations)
    recovered_attrs = set((m.type_map[L], b) for (L, a), (b, _) in m.attr_map.items())
    recovered_rels = set(m.rel_map.values()) | set(m.attr_as_rel.values())
    op_recovered = [r for r in ops if r.learned_op and r.eff_agree >= eff_threshold]
    n_lo = len(learned.domain.operators)
    res = {
        "types": {"hidden": n_ht, "learned": n_lt, "recovered": len(m.type_map), "recall": len(m.type_map) / n_ht,
                  "precision": len(m.type_map) / n_lt if n_lt else 0.0, "map": dict(m.type_map)},
        "predicates": {"hidden_attrs": len(hidden_preds), "recovered_attrs": len(recovered_attrs & set(hidden_preds)),
                       "hidden_rels": len(hidden_rels), "recovered_rels": len(recovered_rels & set(hidden_rels)),
                       "recall": (len(recovered_attrs & set(hidden_preds)) + len(recovered_rels & set(hidden_rels))) / max(1, len(hidden_preds) + len(hidden_rels)),
                       "attr_map": {f"{L}.{a}": b for (L, a), (b, _) in m.attr_map.items()},
                       "rel_map": dict(m.rel_map), "attr_as_rel": {f"{L}.{a}": r for (L, a), r in m.attr_as_rel.items()}},
        "operators": {"hidden": len(hidden_dom.operators), "learned": n_lo, "recovered": len(op_recovered),
                      "recall": len(op_recovered) / len(hidden_dom.operators),
                      "precision": len(op_recovered) / n_lo if n_lo else 0.0,
                      "mean_pre_agree": sum(r.pre_agree for r in ops) / len(ops),
                      "mean_eff_agree": sum(r.eff_agree for r in ops) / len(ops),
                      "per_op": [{"hidden": r.hidden_op, "learned": r.learned_op, "params": r.param_map,
                                  "pre_agree": round(r.pre_agree, 3), "eff_agree": round(r.eff_agree, 3), "n_both": r.n_both_applicable} for r in ops]},
    }
    return res


def format_report(res: dict) -> str:
    t, p, o = res["types"], res["predicates"], res["operators"]
    lines = [f"types: {t['recovered']}/{t['hidden']} recovered (learned {t['learned']}) map={t['map']}",
             f"predicates: attrs {p['recovered_attrs']}/{p['hidden_attrs']}, rels {p['recovered_rels']}/{p['hidden_rels']} "
             f"attr_map={p['attr_map']} rel_map={p['rel_map']} attr_as_rel={p['attr_as_rel']}",
             f"operators: {o['recovered']}/{o['hidden']} recovered (learned {o['learned']}, precision {o['precision']:.2f}); "
             f"mean pre-agreement {o['mean_pre_agree']:.2f}, mean effect-agreement {o['mean_eff_agree']:.2f}"]
    for r in o["per_op"]:
        lines.append(f"   {r['hidden']:16s} -> {str(r['learned']):6s} pre={r['pre_agree']:.2f} eff={r['eff_agree']:.2f} n={r['n_both']} {r['params']}")
    return "\n".join(lines)
