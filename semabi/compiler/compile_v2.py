"""V2 compile: observation graph -> unit/entity hypotheses -> V2 abstractor -> V0 inducer/model."""
from __future__ import annotations

from pathlib import Path

from semabi.compiler.compile import Compiled
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.induce import Inducer
from semabi.compiler.model import build_model, relation_names, type_name
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses


def compile_v2(run_dir: Path, min_support: int = 1, refine_hypotheses: bool = False) -> Compiled:
    run_dir = Path(run_dir)
    log = EvidenceLog(run_dir)
    G = ObsGraph()
    for sig, obs in log.observations.items():
        G.add(sig, obs)
    H = Hypotheses(G)
    H.fit(step_sigs=[s.after for s in log.steps], step_targets=[(s.before, s.action.target) for s in log.steps], step_kinds=[s.action.kind for s in log.steps], reload_pairs=[(s.before, s.after) for i, s in enumerate(log.steps)
                        if s.action.kind == "reload" and i > 0 and log.steps[i - 1].action.kind not in ("reset", "reload")])
    if refine_hypotheses:
        from semabi.compiler.v2.score import refine
        notes: list[str] = []
        A, score, moves = refine(H, G, log, log_fn=notes.append)
        (run_dir / "refine_v2.log").write_text("\n".join(notes) + "\n")
    else:
        A = V2Abstractor(G, H)
        A.fit_view_controls(log)
    I = Inducer(A, log)
    I.run()
    M = build_model(A, I.operators, min_support=min_support, view_ops=I.view_ops)
    rels = relation_names(A)
    link_types = {}
    for tid in set(A.link_pairs.values()):
        ends = [rels[(tid, k)] for k in A.types[tid].refs if k.startswith("rel:") and (tid, k) in rels]
        if len(ends) == 2:
            link_types[type_name(tid)] = ends
    M.meta = {"v2": True, "n_steps": len(log.steps), "n_transitions": len(I.transitions), "n_operators": len(I.operators),
              "link_types": link_types}
    M.save(run_dir / "model_v2.json")
    (run_dir / "model_v2.txt").write_text(str(M) + "\n\n" + I.report() + "\n\n" + A.summary())
    return Compiled(log, None, A, I, M)
