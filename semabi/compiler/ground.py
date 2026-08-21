"""Execute learned groundings (action templates) on the live application, and
keep a tracked abstract state of the live page."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from semabi.compiler.abstract import Abstractor, AbstractState, resolve_masked
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

    def __init__(self, browser: Browser, log: EvidenceLog, abstractor: Abstractor):
        self.b = browser
        self.log = log
        self.A = abstractor
        self.obs: Observation | None = None
        self.state: AbstractState | None = None
        self.episode = browser.episode

    def refresh(self) -> AbstractState:
        self.obs = self.b.observe()
        raw = self.A.abstract(self.obs)
        self.state = resolve_masked(self.A, self.state, raw) if self.state is not None else raw
        return self.state

    def do(self, p: Primitive) -> tuple[bool, str | None, int]:
        before = self.obs if self.obs is not None else self.b.observe()
        res = self.b.act(p)
        if p.kind == "reset":
            self.episode = self.b.episode
            self.state = None
        after = self.b.observe()
        step = self.log.add_step(self.episode, p, res.ok, res.error, before, after)
        self.obs = after
        raw = self.A.abstract(after)
        self.state = resolve_masked(self.A, self.state, raw) if (self.state is not None and p.kind not in ("reload", "reset")) else raw
        return res.ok, res.error, step.step

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
                po = self.A.parsed(self.obs)
                v = po.statics.get(a.loc.slot, (None, None))[1]
                if v != binding.get(a.arg):
                    return ExecResult(False, f"context {a.loc.slot}={v!r} != {binding.get(a.arg)!r}", steps)
                continue
            if a.kind == "press":
                ok, err, st = self.do(Primitive("press", text=a.arg))
                steps.append(st)
                continue
            owner_key = binding.get(a.owner) if a.owner else None
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
