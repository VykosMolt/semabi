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


def compile_v2(run_dir: Path, min_support: int = 1, refine_hypotheses: bool = False, llm: str | None = "opus",
               apply_refinements: bool = True, write_diagnostics: bool = True,
               conservative_belief: bool = True,
               include_provisional_refinements: bool = False,
               refinement_decisions: list[dict] | None = None) -> Compiled:
    run_dir = Path(run_dir)
    log = EvidenceLog(run_dir)
    G = ObsGraph()
    for sig, obs in log.observations.items():
        G.add(sig, obs)
    H = Hypotheses(G)
    merge_mentions = False
    if apply_refinements:
        from semabi.compiler.v2.refinement import configure_hypotheses, load_decisions
        decisions = (refinement_decisions if refinement_decisions is not None else
                     load_decisions(run_dir, include_provisional=include_provisional_refinements))
        merge_mentions = configure_hypotheses(H, decisions)
    H.fit(step_sigs=[s.after for s in log.steps], step_targets=[(s.before, s.action.target) for s in log.steps], step_kinds=[s.action.kind for s in log.steps], reload_pairs=[(s.before, s.after) for i, s in enumerate(log.steps)
                        if s.action.kind == "reload" and i > 0 and log.steps[i - 1].action.kind not in ("reset", "reload")])
    if llm:
        from semabi.compiler.v2.llm_propose import verified_aliases
        aliases = verified_aliases(H, [s.after for s in log.steps], run_dir, model=llm)
        if aliases:
            H.apply_aliases(aliases)
    if refine_hypotheses:
        from semabi.compiler.v2.score import refine
        notes: list[str] = []
        A, score, moves = refine(H, G, log, log_fn=notes.append)
        A.conservative_belief = conservative_belief
        (run_dir / "refine_v2.log").write_text("\n".join(notes) + "\n")
    else:
        A = V2Abstractor(G, H, merge_mentions=merge_mentions,
                         conservative_belief=conservative_belief)
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
    for tid, endpoint_tids in A.explicit_link_types.items():
        ends = [rels[(tid, f"rel:{target}")] for target in endpoint_tids
                if (tid, f"rel:{target}") in rels]
        if len(ends) == len(endpoint_tids):
            link_types[type_name(tid)] = ends
    M.meta = {"v2": True, "n_steps": len(log.steps), "n_transitions": len(I.transitions), "n_operators": len(I.operators),
              "link_types": link_types,
              "belief_policy": "conservative_complete_collections" if conservative_belief else "legacy_visible_type_complete"}
    M.save(run_dir / "model_v2.json")
    (run_dir / "model_v2.txt").write_text(str(M) + "\n\n" + I.report() + "\n\n" + A.summary())
    if write_diagnostics:
        import json
        from semabi.compiler.v2.counterexamples import abstraction_contradictions, classify
        from semabi.compiler.v2.refinement import build_components, write_components, write_counterexamples
        counterexamples = classify(A, log)
        write_counterexamples(run_dir, counterexamples)
        write_components(run_dir, build_components(A, log, counterexamples))
        (run_dir / "abstraction_contradictions_v2.json").write_text(
            json.dumps(abstraction_contradictions(I), indent=1, default=str)
        )
    return Compiled(log, None, A, I, M)
