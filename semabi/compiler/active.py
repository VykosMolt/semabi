"""Active experimentation: verification replays, precondition probes and
systematic affordance sweeps, all executed on the live app and logged as
ordinary evidence so that re-induction incorporates them."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from semabi import relmodel as rm
from semabi.compiler.abstract import diff
from semabi.compiler.browser import Primitive
from semabi.compiler.compile import Compiled, compile_log
from semabi.compiler.explorer import fresh_token
from semabi.compiler.ground import Live
from semabi.compiler.induce import ActT, Locator, OperatorHyp
from semabi.compiler.model import abstract_to_state
from semabi.eval_free_canon import canonical_learned  # compiler-side canonical form (no hidden access)


@dataclass
class Experiment:
    kind: str  # verify | probe | sweep
    op: str | None
    binding: dict[str, Any]
    acts: list[ActT]
    note: str = ""
    literal: tuple | None = None
    priority: float = 0.0
    setup: list[tuple[str, dict[str, Any]]] = field(default_factory=list)  # (op name, binding) to run first

    def to_json(self) -> dict:
        return {"kind": self.kind, "op": self.op, "binding": {k: list(v) if isinstance(v, tuple) else v for k, v in self.binding.items()},
                "acts": [str(a) for a in self.acts], "note": self.note, "literal": list(self.literal) if self.literal else None}


class ActiveExplorer:
    def __init__(self, live: Live, run_dir: Path, seed: int = 0):
        self.live = live
        self.run_dir = Path(run_dir)
        self.rng = random.Random(seed)
        self.C: Compiled | None = None
        self.swept: set[str] = set()
        self.records: list[dict] = []
        p = self.run_dir / "sweep_done.json"
        if p.exists():
            self.swept = set(json.loads(p.read_text()))
        self.exp_path = self.run_dir / "experiments.jsonl"
        self.use_counts: dict[tuple[str, str], int] = {}
        self.probe_memo: dict[tuple, int] = {}
        self.sweep_noeffect: dict[str, int] = {}  # situ -> times tried without effect
        self.sweep_effect: set[str] = set()  # akeys that produced a domain effect at least once

    # ---------------------------------------------------------------- utils
    def recompile(self) -> Compiled:
        self.probe_memo = {}
        self.C = compile_log(self.run_dir)
        self.live.A = self.C.abstractor
        self.live.model = self.C.model
        self.live.refresh()
        return self.C

    def _save(self):
        (self.run_dir / "sweep_done.json").write_text(json.dumps(sorted(self.swept)))

    def _record(self, exp: Experiment, outcome: dict):
        rec = {"experiment": exp.to_json(), **outcome}
        self.records.append(rec)
        with self.exp_path.open("a") as f:
            f.write(json.dumps(rec) + "\n")

    def _objects(self, tid: int):
        return [o for o in self.live.state.objs.values() if o.tid == tid]

    def _fresh(self) -> str:
        return fresh_token(self.rng, set(self.live.log.typed_tokens) | self.live.obs.texts())

    def _op(self, name: str) -> OperatorHyp | None:
        return next((o for o in self.C.inducer.operators if o.name == name), None)

    # ---------------------------------------------------------------- bindings
    def _sample_binding(self, op: OperatorHyp, avoid: dict | None = None, prefer_unused: bool = True) -> dict | None:
        b: dict[str, Any] = {}
        for p, t in op.params.items():
            if p.startswith("?new"):
                continue
            if t == "str":
                b[p] = self._fresh()
                continue
            objs = [o for o in self._objects(t) if o.id not in b.values()]
            if avoid and p in avoid:
                objs = [o for o in objs if o.id != avoid[p]]
            if not objs:
                return None
            if prefer_unused:
                objs.sort(key=lambda o: self.use_counts.get((op.name, o.key), 0))
                objs = [o for o in objs if self.use_counts.get((op.name, o.key), 0) == self.use_counts.get((op.name, objs[0].key), 0)]
            b[p] = self.rng.choice(objs).id
        return b

    def _exec_binding(self, b: dict) -> dict:
        return {p: (v[1] if isinstance(v, tuple) else v) for p, v in b.items()}

    def _predict(self, op_name: str, b: dict) -> tuple[str | None, rm.State | None]:
        """Apply the learned operator to the current learned state."""
        st = abstract_to_state(self.C.abstractor, self.live.state)
        rop = self.C.model.domain.operators.get(op_name)
        if rop is None:
            return "no rm op", None
        rb = {p: (f"T{v[0]}:{v[1]}" if isinstance(v, tuple) else v) for p, v in b.items()}
        reason = rm.check_pre(rop, self.C.model.domain, st, rb)
        if reason:
            return reason, None
        s2, _ = rm.apply_effects(rop, st, rb)
        return None, s2

    # ---------------------------------------------------------------- experiments
    def propose_verifies(self) -> list[Experiment]:
        out = []
        for op in self.C.inducer.operators:
            n_done = op.verified + op.failed
            b = self._sample_binding(op)
            setup = None
            if b is None:
                continue
            reason, _ = self._predict(op.name, b)
            if reason is not None:
                # try a binding satisfying the precondition
                for _ in range(6):
                    b = self._sample_binding(op, prefer_unused=False)
                    if b is None:
                        break
                    reason, _ = self._predict(op.name, b)
                    if reason is None:
                        break
                if b is not None and reason is not None and any(l[0] == "empty" for l in op.pre):
                    # setup: a freshly created object of the constrained type satisfies no_children
                    for p, t in op.params.items():
                        if t != "str" and not p.startswith("?new") and any(l[0] == "empty" and l[1] == p for l in op.pre):
                            st = self._setup_fresh_object(t)
                            if st is not None:
                                setup, key = st
                                b[p] = (t, key)
                                break
                if b is None:
                    continue
            pr = 0.9 if op.support + op.verified < 3 else 0.4 / (1 + n_done)
            ex = Experiment("verify", op.name, b, list(op.acts), priority=pr)
            if setup:
                ex.setup = setup
            out.append(ex)
        return out

    def _setup_fresh_object(self, tid: int):
        """Find a create-operator for `tid` without object params; returns (setup, key)."""
        for cop in self.C.inducer.operators:
            if any(e.kind == "add" and e.tid == tid for e in cop.effs) and all(t == "str" or p.startswith("?new") for p, t in cop.params.items()):
                sb = self._sample_binding(cop, prefer_unused=False)
                if sb is None:
                    continue
                key = next((v for v in sb.values() if isinstance(v, str)), None)
                if key:
                    return [(cop.name, sb)], key
        return None

    def propose_probes(self) -> list[Experiment]:
        out = []
        for op in self.C.inducer.operators:
            cands = [(l, True) for l in op.pre] + [(l, False) for l in op.common if l not in op.pre]
            for lit, in_pre in cands:
                if self.probe_memo.get((op.name, lit), 0) >= 2:
                    continue
                b = self._violating_binding(op, lit)
                if b is None:
                    continue
                pr = 0.8 if not in_pre else 0.5
                if in_pre and lit in op.alternatives:
                    pr = 0.85  # competing explanations: discriminate them first
                out.append(Experiment("probe", op.name, b, list(op.acts), note=("confirm" if in_pre else "challenge"), literal=lit, priority=pr))
        return out

    def _violating_binding(self, op: OperatorHyp, lit: tuple) -> dict | None:
        k = lit[0]
        b = self._sample_binding(op, prefer_unused=False)
        if b is None:
            return None
        st = self.live.state
        if k == "nonempty_str":
            b[lit[1]] = ""
            return b
        if k == "str_ne_attr":
            o = st.objs.get(b.get(lit[2]))
            if o is None:
                return None
            key_slot = self.C.abstractor.types[o.tid].key_slot
            b[lit[1]] = o.key if lit[3] == key_slot else o.attrs.get(lit[3])
            return b if isinstance(b[lit[1]], str) else None
        if k in ("attr", "attr_ne"):
            p, slot, v = lit[1], lit[2], lit[3]
            tid = op.params[p]
            key_slot = self.C.abstractor.types[tid].key_slot
            objs = [o for o in self._objects(tid) if ((o.key if slot == key_slot else o.attrs.get(slot)) != v) == (k == "attr")]
            if not objs:
                return None
            b[p] = self.rng.choice(objs).id
            return b
        if k in ("parent_ne", "parent"):
            p, q = lit[1], lit[2]
            o = st.objs.get(b[p])
            if o is None:
                return None
            if k == "parent_ne":
                if o.parent is None:
                    return None
                b[q] = o.parent
            else:
                others = [x for x in self._objects(op.params[q]) if x.id != o.parent]
                if not others:
                    return None
                b[q] = self.rng.choice(others).id
            return b
        if k in ("ref_ne", "ref"):
            p, slot, q = lit[1], lit[2], lit[3]
            o = st.objs.get(b[p])
            if o is None:
                return None
            cur = o.refs.get(slot)
            if k == "ref_ne":
                if cur is None:
                    return None
                b[q] = cur
            else:
                others = [x for x in self._objects(op.params[q]) if x.id != cur]
                if not others:
                    return None
                b[q] = self.rng.choice(others).id
            return b
        if k == "empty":
            p = lit[1]
            tid = op.params[p]
            with_children = [o for o in self._objects(tid) if any(x.parent == o.id or o.id in x.refs.values() for x in st.objs.values())]
            if with_children:
                b[p] = self.rng.choice(with_children).id
                return b
            # setup: create a child under b[p] using a known create operator
            for cop in self.C.inducer.operators:
                for e in cop.effs:
                    if e.kind == "add" and (e.parent in cop.params or any(v in cop.params for _, v in e.refs)):
                        par = e.parent if e.parent else next(v for _, v in e.refs if v in cop.params)
                        if cop.params.get(par) == tid:
                            sb = self._sample_binding(cop, prefer_unused=False)
                            if sb is None:
                                continue
                            sb[par] = b[p]
                            ex = Experiment("probe", op.name, b, list(op.acts), literal=lit)
                            ex.setup = [(cop.name, sb)]
                            return b if not ex.setup else (b | {"__setup__": ex.setup})
            return None
        return None

    def propose_sweeps(self, max_owners: int = 2) -> list[Experiment]:
        """Untried affordances on the current page, with form completion: every
        textbox/combobox/radio in the button's nearest form container is set."""
        out = []
        obs = self.live.obs
        po = self.C.abstractor.parsed(obs)
        A = self.C.abstractor
        by_node = {o.node: o for o in self.live.state.objs.values()}

        def owner_of(node):
            idx = po.node_instance.get(node)
            trans = None
            while idx is not None:
                inst = po.instances[idx]
                if inst.root in by_node:
                    return by_node[inst.root], trans
                ti = A.types.get(inst.tid)
                if ti and not ti.persistent and trans is None:
                    trans = (inst.tid, inst)
                idx = inst.parent
            return None, trans

        def form_container(node):
            """Nearest ancestor whose subtree holds a form element, without crossing the owner's root."""
            owner, _ = owner_of(node)
            stop = owner.node if owner else -1
            cur = obs.node(node).parent
            while cur >= 0:
                sub = obs.subtree(cur)
                if any(obs.node(x).role in ("textbox", "combobox", "radio") for x in sub if x != node):
                    return sub
                if cur == stop:
                    break
                cur = obs.node(cur).parent
            return []

        ctx_key = tuple(sorted((k, v) for k, v in self.live.tracker.ctx.items()))
        for node, key in po.node_key.items():
            n = obs.node(node)
            if n.role not in ("button", "link", "checkbox", "radio", "combobox"):
                continue
            owner, trans = owner_of(node)
            owner_tid = owner.tid if owner else None
            variants = [None]
            if n.role == "combobox":
                variants = [o for o in (n.options or []) if o != n.value]
            for var in variants:
                akey = f"{owner_tid}|{trans[0] if trans else None}|{key}|{'opt' if var else ''}"
                situ = f"{akey}|{owner.key if owner else ''}|{ctx_key if owner is None else ''}"
                if situ in self.swept or sum(1 for x in self.swept if x.startswith(akey + "|")) >= max_owners:
                    continue
                acts = []
                binding = {}
                if n.role == "button":
                    radios_done = set()
                    for node2 in form_container(node):
                        key2 = po.node_key.get(node2)
                        if key2 is None or node2 == node:
                            continue
                        n2 = obs.node(node2)
                        o2, t2 = owner_of(node2)
                        if n2.role == "textbox":
                            pname = f"?s{len(binding)}"
                            binding[pname] = self._fresh()
                            acts.append(ActT("type", self._loc(key2, o2.tid if o2 else None, t2), "?own2" if o2 else None, pname))
                            if o2:
                                binding["?own2"] = o2.key
                        elif n2.role == "combobox" and n2.options:
                            others = [o for o in n2.options if o != n2.value]
                            if others:
                                pname = f"?v{len(binding)}"
                                binding[pname] = self.rng.choice(others)
                                acts.append(ActT("select", self._loc(key2, o2.tid if o2 else None, t2), "?own2" if o2 else None, pname))
                                if o2:
                                    binding["?own2"] = o2.key
                        elif n2.role == "radio" and t2 is not None and t2[0] not in radios_done and not n2.checked:
                            # pick one unchecked radio of this transient group at random
                            group = [x for x in form_container(node) if obs.node(x).role == "radio" and not obs.node(x).checked]
                            pick = self.rng.choice(group)
                            op2, tp = owner_of(pick)
                            ident = next((v for k3, (_, v) in tp[1].slots.items() if isinstance(v, str) and v), None) if tp else None
                            if ident:
                                acts.append(ActT("click", self._loc(po.node_key[pick], None, tp), "?rad", None))
                                binding["?rad"] = ident
                            radios_done.add(t2[0])
                if n.role == "combobox":
                    pname = "?v0"
                    binding[pname] = var
                    acts.append(ActT("select", self._loc(key, owner_tid, trans), "?own" if owner else None, pname))
                else:
                    acts.append(ActT("click", self._loc(key, owner_tid, trans), "?own" if owner or trans else None, None))
                if owner:
                    binding["?own"] = owner.key
                elif trans:
                    ident = next((v for k3, (_, v) in trans[1].slots.items() if isinstance(v, str) and v), None)
                    if ident:
                        binding["?own"] = ident
                pr = 0.6 if self.sweep_noeffect.get(situ, 0) else 1.0
                if akey in self.sweep_effect:
                    pr = 0.3  # its effect is known; verification takes over
                out.append(Experiment("sweep", None, binding, acts, note=situ, priority=pr))
        return out

    def _loc(self, key: str, owner_tid: int | None, trans) -> Locator:
        if trans is not None:
            slot = next((k for k, (_, v) in trans[1].slots.items() if isinstance(v, str) and v), None)
            return Locator(key, None, trans[0], slot)
        return Locator(key, owner_tid)

    # ---------------------------------------------------------------- execution
    def run_experiment(self, exp: Experiment) -> dict:
        live = self.live
        before = live.state
        setup = exp.binding.pop("__setup__", None) if exp.kind == "probe" else None
        setup = setup or exp.setup
        if setup:
            for op_name, sb in setup:
                sop = self._op(op_name)
                r = live.execute(list(sop.acts), self._exec_binding(sb))
                if not r.ok:
                    return {"outcome": "setup_failed", "reason": r.reason}
            before = live.state
        predicted_reason, predicted = (None, None)
        if exp.op:
            predicted_reason, predicted = self._predict(exp.op, exp.binding)
            for p, v in exp.binding.items():
                if isinstance(v, tuple):
                    self.use_counts[(exp.op, v[1])] = self.use_counts.get((exp.op, v[1]), 0) + 1
        if exp.kind == "probe":
            self.probe_memo[(exp.op, exp.literal)] = self.probe_memo.get((exp.op, exp.literal), 0) + 1
        r = live.execute(exp.acts, self._exec_binding(exp.binding))
        after = live.state
        d = diff(before, after)
        out = {"executed": r.ok, "reason": r.reason, "steps": r.steps, "domain_changed": d.domain_changed, "diff": str(d)}
        if exp.kind == "sweep":
            self.swept.add(exp.note)
            if not d.domain_changed:
                self.sweep_noeffect[exp.note] = self.sweep_noeffect.get(exp.note, 0) + 1
            else:
                self.sweep_effect.add(exp.note.rsplit("|", 2)[0])
        # a scoped object vanished: look everywhere so the inducer can tell deleted from moved
        if d.removed and self.live.model is not None and self.live.model.view_ops:
            from semabi.compiler.belief import scoped_ids
            if any(o.id in scoped_ids(before, self.live.tracker.scopes) for o in d.removed):
                self.live.survey(force=True)
        if exp.op:
            op = self._op(exp.op)
            if predicted is not None:
                match = canonical_learned(predicted, self.C.model) == canonical_learned(abstract_to_state(self.C.abstractor, after), self.C.model)
                out["predicted_effect_matched"] = match
                if exp.kind == "verify":
                    if match:
                        op.verified += 1
                    else:
                        op.failed += 1
            else:
                out["predicted_inapplicable"] = predicted_reason
                out["observed_change"] = d.domain_changed
        return out

    def round(self, budget: int, reset_every: int = 12) -> int:
        """Run experiments until `budget` primitives are used. Returns primitives used."""
        n_exp = 0
        start = self.live.b.n_primitives
        while self.live.b.n_primitives - start < budget and n_exp < budget * 2:
            if n_exp % reset_every == 0:
                self.live.reset(self.rng.randrange(10_000))
                self.live.survey()
                # affordances that never did anything get another chance in the new state
                for situ, k in list(self.sweep_noeffect.items()):
                    if k < 4:
                        self.swept.discard(situ)
            exps = self.propose_sweeps() + self.propose_probes() + self.propose_verifies()
            if not exps:
                break
            exps.sort(key=lambda e: -e.priority)
            top = [e for e in exps if e.priority >= exps[0].priority - 1e-9]
            exp = self.rng.choice(top)
            outcome = self.run_experiment(exp)
            self._record(exp, outcome)
            n_exp += 1
            if len(self.live.state.objs) > 14:
                self.live.reset(self.rng.randrange(10_000))
        self._save()
        return self.live.b.n_primitives - start
