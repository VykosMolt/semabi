"""Compiler entry point: evidence log -> learned semantic model."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from semabi import relmodel as rm
from semabi.compiler.abstract import Abstractor
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.induce import Inducer
from semabi.compiler.model import LearnedModel, abstract_to_state, build_model
from semabi.compiler.parse import Parser


@dataclass
class Compiled:
    log: EvidenceLog
    parser: Parser
    abstractor: Abstractor
    inducer: Inducer
    model: LearnedModel

    def learned_state_after(self, step: int) -> rm.State:
        return abstract_to_state(self.abstractor, self.inducer.tracked_after(step))

    def visible_state_after(self, step: int) -> rm.State:
        """What the learner can see at this step (no carried belief); unseen attributes are None."""
        s = self.log.steps[step]
        return abstract_to_state(self.abstractor, self.abstractor.abstract(self.log.obs(s.after)))


def compile_log(run_dir: Path, min_support: int = 1) -> Compiled:
    log = EvidenceLog(run_dir)
    P = Parser()
    P.fit([log.obs(s.after) for s in log.steps] + ([log.obs(log.steps[0].before)] if log.steps else []), log.typed_tokens)
    A = Abstractor(P)
    A.fit(log)
    I = Inducer(A, log)
    I.run()
    M = build_model(A, I.operators, min_support=min_support, view_ops=I.view_ops)
    M.meta = {"n_steps": len(log.steps), "n_observations": len(log.observations), "n_transitions": len(I.transitions),
              "n_operators": len(I.operators), "typed_tokens": len(log.typed_tokens)}
    M.save(Path(run_dir) / "model.json")
    (Path(run_dir) / "model.txt").write_text(str(M) + "\n\n" + I.report() + "\n\n" + A.summary())
    return Compiled(log, P, A, I, M)
