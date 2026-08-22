"""Evaluation against an EXTERNAL environment (e.g. the gauntlet apps) that
exposes `/_evaluator/state` and `/_evaluator/domain` but no executable hidden
operator semantics. Scoring is trace-based:

* types / attributes / relations: paired-state alignment (as in matching.align);
* operators: every hidden transition recorded during exploration (one hidden
  operator applied successfully) must be *explained* by some learned operator
  whose application to the translated pre-state yields the translated post-state;
  failed hidden attempts must be rejected by the learned counterpart's precondition;
* planning: goals are atoms that held in previously observed reachable states.
"""
from __future__ import annotations

import json
import random
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from semabi import relmodel as rm
from semabi.compiler.model import LearnedModel
from semabi.compiler.planner import apply_learned, unsatisfied
from semabi.eval.matching import Mapping, align, canonical_keys, translate_state


def fetch(url: str) -> dict:
    return json.loads(urllib.request.urlopen(url, timeout=10).read())


def domain_from_description(j: dict) -> rm.Domain:
    types = {t["name"]: rm.TypeDef(t["name"], dict(t.get("attrs", {}))) for t in j["types"]}
    rels = {r["name"]: rm.RelationDef(r["name"], r["src"], r["dst"]) for r in j.get("relations", [])}
    ops = {o["name"]: rm.Operator(o["name"], [tuple(p) for p in o.get("params", [])]) for o in j.get("operators", [])}
    return rm.Domain(j.get("name", "external"), types, rels, ops)


def state_from_json(j: dict) -> rm.State:
    s = rm.State()
    for o in j["objects"]:
        s.objects[str(o["id"])] = rm.Obj(str(o["id"]), o["type"], dict(o.get("attrs", {})))
    for r, d in j.get("rels", {}).items():
        for a, b in d.items():
            if b is not None:
                s.set_rel(r, str(a), str(b))
    return s


@dataclass
class OpScore:
    hidden_op: str
    n_success: int = 0
    explained: int = 0
    explained_by: Counter = field(default_factory=Counter)
    n_fail: int = 0
    rejected: int = 0  # failed attempts the learned counterpart also rejects
    unbound_fail: int = 0  # failures we could not bind to the counterpart
    invisible: int = 0  # successes with no change in the learned vocabulary


def _bindings(dom: rm.Domain, s: rm.State, op: rm.Operator, pool: list[str]):
    return list(rm.groundings(dom, s, op, pool))


def explain_transitions(hidden_dom: rm.Domain, learned: LearnedModel, m: Mapping, hidden_states: list[dict],
                        max_bindings: int = 4000) -> tuple[dict[str, OpScore], Counter]:
    """For each recorded step whose hidden log grew by one successful operation,
    search for a learned operator reproducing the translated post-state."""
    scores: dict[str, OpScore] = {h: OpScore(h) for h in hidden_dom.operators}
    used_learned: Counter = Counter()
    ld = learned.domain
    prev = None
    for rec in hidden_states:
        cur, prev = rec, prev
        last = prev
        prev = cur
        if last is not None and cur["episode"] == last["episode"] and cur["log_len"] == last["log_len"] + 1 and cur.get("last_op"):
            entry = cur["last_op"]
            h = entry.get("op")
            if h not in scores:
                scores[h] = OpScore(h)
            hs0, hs1 = state_from_json(last["state"]), state_from_json(cur["state"])
            if entry.get("ok", True):
                scores[h].n_success += 1
                l0, _ = translate_state(hs0, hidden_dom, learned, m)
                l1, _ = translate_state(hs1, hidden_dom, learned, m)
                target = canonical_keys(l1, learned)
                if canonical_keys(l0, learned) == target:
                    scores[h].invisible += 1  # no change in the learned vocabulary (e.g. latent attribute)
                    continue
                pool = sorted({v for o in hs1.objects.values() for v in o.attrs.values() if isinstance(v, str)} - {""})
                found = None
                for ln, lop in ld.operators.items():
                    bs = _bindings(ld, l0, lop, pool)
                    if len(bs) > max_bindings:
                        bs = bs[:max_bindings]
                    for b in bs:
                        if rm.check_pre(lop, ld, l0, b) is not None:
                            continue
                        try:
                            s2 = apply_learned(learned, l0, lop, b)
                        except (KeyError, TypeError):
                            continue
                        if canonical_keys(s2, learned) == target:
                            found = ln
                            break
                    if found:
                        break
                if found:
                    scores[h].explained += 1
                    scores[h].explained_by[found] += 1
                    used_learned[found] += 1
            else:
                scores[h].n_fail += 1
    return scores, used_learned


def check_failures(hidden_dom: rm.Domain, learned: LearnedModel, m: Mapping, hidden_states: list[dict], scores: dict[str, OpScore]) -> None:
    """Failed hidden attempts: the learned counterpart (dominant explainer) should be
    inapplicable under the corresponding binding. Binding correspondence is found by
    value: hidden object args map to learned ids, strings stay strings."""
    ld = learned.domain
    prev = None
    for rec in hidden_states:
        cur = rec
        if prev is not None and cur["episode"] == prev["episode"] and cur["log_len"] == prev["log_len"] + 1 and cur.get("last_op"):
            entry = cur["last_op"]
            h = entry.get("op")
            if not entry.get("ok", True) and h in scores and scores[h].explained_by:
                ln = scores[h].explained_by.most_common(1)[0][0]
                lop = ld.operators[ln]
                hs0 = state_from_json(prev["state"])
                l0, idmap = translate_state(hs0, hidden_dom, learned, m)
                # candidate learned bindings consistent with the hidden args' values
                hvals = []
                for v in entry.get("args", {}).values():
                    if isinstance(v, str) and v in hs0.objects:
                        hvals.append(idmap.get(v))
                    else:
                        hvals.append(v)
                matched = False
                rejected = True
                for b in rm.groundings(ld, l0, lop, [v for v in hvals if isinstance(v, str) and v not in l0.objects] + [""]):
                    if all(v in b.values() for v in hvals if v is not None):
                        matched = True
                        if rm.check_pre(lop, ld, l0, b) is None:
                            rejected = False
                            break
                if matched:
                    scores[h].rejected += int(rejected)
                else:
                    scores[h].unbound_fail += 1
        prev = cur


def goals_from_trace(hidden_states: list[dict], hidden_dom: rm.Domain, rng: random.Random, n: int = 6, max_atoms: int = 3) -> list[dict]:
    """Goals = atoms true in a reachable state of an exploration episode (>= 3
    successful operations after the reset) but false in that episode's initial
    state. Returns dicts with the seed episode and hidden atoms."""
    by_ep: dict[int, list[dict]] = defaultdict(list)
    for rec in hidden_states:
        by_ep[rec["episode"]].append(rec)
    cands = []
    for ep, recs in by_ep.items():
        init = state_from_json(recs[0]["state"])
        for rec in recs[1:]:
            if rec["log_len"] - recs[0]["log_len"] < 3:
                continue
            st = state_from_json(rec["state"])
            atoms = []
            for o in st.objects.values():
                if o.id not in init.objects:
                    rels = {r: st.get_rel(r, o.id) for r in hidden_dom.relations if st.get_rel(r, o.id) and st.get_rel(r, o.id) in init.objects}
                    atoms.append(("exists", o.type, {k: v for k, v in o.attrs.items()}, rels))
                else:
                    io = init.objects[o.id]
                    for k, v in o.attrs.items():
                        if io.attrs.get(k) != v:
                            atoms.append(("attr", o.id, k, v))
                    for r in hidden_dom.relations:
                        if st.get_rel(r, o.id) != init.get_rel(r, o.id) and st.get_rel(r, o.id) in init.objects:
                            atoms.append(("rel", r, o.id, st.get_rel(r, o.id)))
            for o in init.objects.values():
                if o.id not in st.objects:
                    atoms.append(("not_exists", o.type, dict(o.attrs)))
            if atoms:
                cands.append((ep, atoms))
    rng.shuffle(cands)
    out = []
    for ep, atoms in cands[: n * 3]:
        k = min(max_atoms, len(atoms))
        out.append({"episode": ep, "hidden": rng.sample(atoms, k)})
        if len(out) >= n:
            break
    return out


def hidden_goal_holds(goal: list[tuple], s: rm.State) -> bool:
    for g in goal:
        if g[0] == "exists":
            _, t, attrs, rels = g
            if not any(all(o.attrs.get(k) == v for k, v in attrs.items()) and all(s.get_rel(r, o.id) == tg for r, tg in rels.items())
                       for o in s.of_type(t)):
                return False
        elif g[0] == "not_exists":
            _, t, attrs = g
            if any(all(o.attrs.get(k) == v for k, v in attrs.items()) for o in s.of_type(t)):
                return False
        elif g[0] == "attr":
            _, oid, a, v = g
            if oid not in s.objects or s.objects[oid].attrs.get(a) != v:
                return False
        elif g[0] == "rel":
            _, r, oid, t = g
            if s.get_rel(r, oid) != t:
                return False
    return True


def translate_goal_generic(goal: list[tuple], hs: rm.State, hidden_dom: rm.Domain, learned: LearnedModel, m: Mapping) -> list[tuple] | None:
    inv_type = {H: L for L, H in m.type_map.items()}
    inv_rel = {H: L for L, H in m.rel_map.items()}
    attr_as_rel_inv = {(m.type_map[L], r): (L, a) for (L, a), r in m.attr_as_rel.items()}

    def lid(hid):
        o = hs.objects.get(hid)
        L = inv_type.get(o.type) if o else None
        return f"{L}:{o.attrs.get(m.key_attr[L])}" if L else None

    def lattrs(H, attrs):
        L = inv_type.get(H)
        if L is None:
            return None
        out = {}
        for b, v in attrs.items():
            if b == m.key_attr[L]:
                out[learned.key_slots[L]] = v
                continue
            hit = [(a, vmap) for (L2, a), (b2, vmap) in m.attr_map.items() if L2 == L and b2 == b]
            if not hit:
                continue  # attribute unknown to the learner: dropped from the goal (reported as partial)
            a, vmap = hit[0]
            if v not in vmap:
                return None
            out[a] = vmap[v]
        return out

    out = []
    for g in goal:
        if g[0] in ("exists", "not_exists"):
            attrs = lattrs(g[1], g[2])
            if attrs is None:
                return None
            L = inv_type[g[1]]
            if g[0] == "not_exists":
                out.append(("not_exists", L, attrs))
                continue
            rels = {}
            for r, tgt in g[3].items():
                t = lid(tgt)
                if t is None:
                    return None
                if r in inv_rel:
                    rels[inv_rel[r]] = t
                elif (g[1], r) in attr_as_rel_inv:
                    attrs[attr_as_rel_inv[(g[1], r)][1]] = t.split(":", 1)[1]
                else:
                    return None
            out.append(("exists", L, attrs, rels))
        elif g[0] == "attr":
            o = hs.objects[g[1]]
            l = lid(g[1])
            attrs = lattrs(o.type, {g[2]: g[3]})
            if l is None or attrs is None:
                return None
            if not attrs:
                return None  # latent / unknown attribute
            for a, lv in attrs.items():
                if a == learned.key_slots[inv_type[o.type]]:
                    out.append(("exists", inv_type[o.type], {a: lv}, {}))
                    out.append(("not_exists", inv_type[o.type], {a: l.split(":", 1)[1]}))
                else:
                    out.append(("attr", l, a, lv))
        elif g[0] == "rel":
            o = hs.objects[g[2]]
            l, t = lid(g[2]), lid(g[3])
            if l is None or t is None:
                return None
            if g[1] in inv_rel:
                out.append(("rel", inv_rel[g[1]], l, t))
            elif (o.type, g[1]) in attr_as_rel_inv:
                out.append(("attr", l, attr_as_rel_inv[(o.type, g[1])][1], t.split(":", 1)[1]))
            else:
                return None
    return out


def summarize(hidden_dom: rm.Domain, learned: LearnedModel, m: Mapping, scores: dict[str, OpScore], used: Counter) -> dict:
    n_ht = len(hidden_dom.types)
    hidden_preds = [(H, a) for H, t in hidden_dom.types.items() for a in t.attrs if a not in m.key_attr.values()]
    rec_attrs = {(m.type_map[L], b) for (L, a), (b, _) in m.attr_map.items()}
    rec_rels = set(m.rel_map.values()) | set(m.attr_as_rel.values())
    per_op = {}
    for h, sc in scores.items():
        per_op[h] = {"successes": sc.n_success, "explained": sc.explained, "invisible": sc.invisible,
                     "explained_rate": round(sc.explained / sc.n_success, 2) if sc.n_success else None,
                     "by": dict(sc.explained_by), "failures": sc.n_fail, "rejected": sc.rejected, "unbound_failures": sc.unbound_fail}
    observed = [h for h, sc in scores.items() if sc.n_success]
    recovered = [h for h in observed if scores[h].n_success and scores[h].explained / scores[h].n_success >= 0.8]
    learned_ops = list(learned.domain.operators)
    spurious = [ln for ln in learned_ops if used[ln] == 0]
    return {
        "types": {"hidden": n_ht, "learned": len(learned.domain.types), "recovered": len(m.type_map), "map": dict(m.type_map)},
        "predicates": {"hidden_attrs": len(hidden_preds), "recovered_attrs": len(rec_attrs & set(hidden_preds)),
                       "hidden_rels": len(hidden_dom.relations), "recovered_rels": len(rec_rels & set(hidden_dom.relations)),
                       "attr_map": {f"{L}.{a}": b for (L, a), (b, _) in m.attr_map.items()}, "rel_map": dict(m.rel_map)},
        "operators": {"hidden": len(hidden_dom.operators), "observed_in_trace": len(observed), "recovered": len(recovered),
                      "recovered_ops": recovered, "learned": len(learned_ops), "spurious_learned": spurious,
                      "precision": round((len(learned_ops) - len(spurious)) / len(learned_ops), 2) if learned_ops else 0.0,
                      "failure_rejection_rate": round(sum(s.rejected for s in scores.values()) / max(1, sum(s.n_fail - s.unbound_fail for s in scores.values())), 2),
                      "per_op": per_op},
    }
