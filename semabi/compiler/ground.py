"""Execute learned groundings (action templates) on the live application, and
keep a tracked abstract state of the live page."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.abstract import Abstractor, AbstractState
from semabi.compiler.belief import Tracker
from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.induce import ActT, Locator
from semabi.compiler.observation import Observation


@dataclass
class ExecResult:
    ok: bool
    reason: str | None = None
    steps: list[int] = field(default_factory=list)


class Live:
    """Live browser + evidence logging + tracked abstract state."""

    def __init__(self, browser: Browser, log: EvidenceLog, abstractor: Abstractor, model=None):
        self.b = browser
        self.log = log
        self._A = abstractor
        self.tracker = Tracker(abstractor)
        self.model = model
        self.obs: Observation | None = None
        self.state: AbstractState | None = None
        self.episode = browser.episode

    @property
    def A(self) -> Abstractor:
        return self._A

    @A.setter
    def A(self, abstractor: Abstractor) -> None:
        self._A = abstractor
        self.tracker = Tracker(abstractor)
        self.state = None

    def refresh(self) -> AbstractState:
        self.obs = self.b.observe()
        self.state, _ = self.tracker.observe(self.obs, "noop")
        return self.state

    def do(self, p: Primitive) -> tuple[bool, str | None, int]:
        before = self.obs if self.obs is not None else self.b.observe()
        res = self.b.act(p)
        if p.kind == "reset":
            self.episode = self.b.episode
        after = self.b.observe()
        step = self.log.add_step(self.episode, p, res.ok, res.error, before, after)
        self.obs = after
        self.state, _ = self.tracker.observe(after, p.kind)
        return res.ok, res.error, step.step

    def context_value(self, slot: str):
        return self.tracker.ctx.get(slot)

    def set_context(self, slot: str, key: str) -> bool:
        """Achieve a view context through a learned view operator."""
        if self.model is None or slot not in self.model.view_ops:
            return False
        vg = self.model.view_ops[slot]
        r = self.execute(vg.grounding.acts, {vg.param: key})
        return r.ok and self.context_value(slot) == key

    def _bring_into_view(self, tid: int, key: str) -> bool:
        """If the object is believed to live in another view scope, navigate there."""
        o = self.state.objs.get((tid, key)) if self.state else None
        if o is None:
            return False
        for k, ref in o.refs.items():
            if k.startswith("ctx:") and ref is not None and self.context_value(k[4:]) != ref[1]:
                return self.set_context(k[4:], ref[1])
        return False

    def survey(self, force: bool = False) -> None:
        """Visit every scope so that the belief covers all scoped objects."""
        if self.model is None:
            return
        for slot, vg in self.model.view_ops.items():
            keys = [o.key for o in self.state.objs.values() if o.tid == vg.tid]
            for k in keys:
                if force or (slot, k) not in self.tracker.visited:
                    self.set_context(slot, k)

    def reset(self, seed: int) -> AbstractState:
        if self.obs is None:
            self.b.goto()
            self.obs = self.b.observe()
        self.do(Primitive("reset", text=str(seed)))
        return self.state

    # -------------------------------------------------------------- locate
    def locate(self, loc: Locator, owner_key: Any) -> int | None:
        po = self.A.parsed(self.obs)
        if loc.owner_tid is None and loc.trans_tid is None:
            for node, key in po.node_key.items():
                if key == loc.slot and node not in po.node_instance:
                    return node
            return None
        if loc.owner_tid is not None:
            ti = self.A.types[loc.owner_tid]
            by_node = {o.node: o for o in self.state.objs.values()} if self.state else {}
            for idx, inst in enumerate(po.instances):
                if inst.tid != loc.owner_tid:
                    continue
                key = inst.slots.get(ti.key_slot, (None, None))[1]
                if key is None and inst.root in by_node:
                    key = by_node[inst.root].key
                if key != owner_key:
                    continue
                for node, k in po.node_key.items():
                    if k == loc.slot and self._owner_idx(po, node) == idx:
                        return node
            return None
        for idx, inst in enumerate(po.instances):
            if inst.tid != loc.trans_tid:
                continue
            if inst.slots.get(loc.trans_slot, (None, None))[1] != owner_key:
                continue
            for node, k in po.node_key.items():
                if k == loc.slot and po.node_instance.get(node) == idx:
                    return node
        return None

    def _owner_idx(self, po, node: int) -> int | None:
        idx = po.node_instance.get(node)
        while idx is not None:
            inst = po.instances[idx]
            ti = self.A.types.get(inst.tid)
            if ti and ti.persistent and ti.key_slot:
                return idx
            idx = inst.parent
        return None

    # -------------------------------------------------------------- execute
    def execute(self, acts: list[ActT], binding: dict[str, Any]) -> ExecResult:
        """binding: param -> object key (str) for object params, str for string params."""
        steps = []
        skipped: list[str] = []
        for a in acts:
            if a.kind == "context":
                want = binding.get(a.arg)
                if self.context_value(a.loc.slot) != want:
                    if not self.set_context(a.loc.slot, want):
                        return ExecResult(False, f"context {a.loc.slot}={self.context_value(a.loc.slot)!r} != {want!r} and no view operator", steps)
                continue
            if a.kind == "press":
                ok, err, st = self.do(Primitive("press", text=a.arg))
                steps.append(st)
                continue
            owner_key = binding.get(a.owner) if a.owner else None
            node = self.locate(a.loc, owner_key)
            if node is None and a.loc.owner_tid is not None and self._bring_into_view(a.loc.owner_tid, owner_key):
                node = self.locate(a.loc, owner_key)
            if node is None:
                # redundant/unlocatable action: skip it (the executed sequence is logged as-is)
                skipped.append(str(a))
                continue
            if a.kind == "click":
                p = Primitive("click", node)
            elif a.kind == "type":
                p = Primitive("type", node, str(binding.get(a.arg, "")))
            elif a.kind == "select":
                p = Primitive("select", node, str(binding.get(a.arg, a.arg)))
            else:
                return ExecResult(False, f"unknown act {a.kind}", steps)
            ok, err, st = self.do(p)
            steps.append(st)
            if not ok:
                return ExecResult(False, err, steps)
        if skipped and len(skipped) == len([a for a in acts if a.kind != "context"]):
            return ExecResult(False, "cannot locate: " + "; ".join(skipped), steps)
        return ExecResult(True, ("skipped: " + "; ".join(skipped)) if skipped else None, steps)
