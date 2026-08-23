"""V4 compile: mentions -> candidate observation/identity readings chosen by behaviour -> frozen V0 inducer.

The downstream is deliberately unchanged.  The V0 inducer, its effect language and the
model builder are exactly the frozen ones; what V4 replaces is the step that decides which
rendered mentions are observations of which latent entity, and it decides it by asking
which reading explains the application's behaviour rather than by scoring the page.
"""
from __future__ import annotations

import json
from pathlib import Path

from semabi.compiler.compile import Compiled
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.induce import Inducer
from semabi.compiler.model import build_model, relation_names, type_name
from semabi.compiler.v2.abstractor import V2Abstractor
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses
from semabi.compiler.v4 import promote, search as v4_search

READINGS_FILE = "identity_readings_v4.json"


def build_hypotheses(run_dir: Path, log: EvidenceLog,
                     promoted: set[str] | None = None) -> tuple[Hypotheses, ObsGraph]:
    G = ObsGraph()
    for sig, obs in log.observations.items():
        G.add(sig, obs)
    H = Hypotheses(G)
    if promoted:
        H.promoted = set(promoted)
    H.fit(step_sigs=[s.after for s in log.steps],
          step_targets=[(s.before, s.action.target) for s in log.steps],
          step_kinds=[s.action.kind for s in log.steps],
          reload_pairs=[(s.before, s.after) for i, s in enumerate(log.steps)
                        if s.action.kind == "reload" and i > 0
                        and log.steps[i - 1].action.kind not in ("reset", "reload")])
    return H, G


def compile_v4(run_dir: Path, min_support: int = 1, conservative_belief: bool = True,
               max_steps: int | None = None, write_diagnostics: bool = True,
               identity: dict[str, str | None] | None = None) -> Compiled:
    """Compile with V4 identity selection.

    `identity` pins a chosen reading, keyed either by unit template or by family.  A
    template string carries the tokens the page happened to render, so it does not survive
    a different seed; the family does, which is why a reading is transferred to another
    trace by family and never by template.  When `identity` is None the search decides.
    """
    run_dir = Path(run_dir)
    log = EvidenceLog(run_dir)
    H, G = build_hypotheses(run_dir, log)

    notes: list[str] = []
    if identity is None:
        result = v4_search.search(H, G, log, max_steps=max_steps, log_fn=notes.append,
                                  run_dir=run_dir)
        # whether a repeated leaf is a value of its container or an object of its own is the
        # other half of the observation model, and it is decided the same way: on trial,
        # kept only on a strict improvement
        promoted: set[str] = set()
        base_H, base_G = build_hypotheses(run_dir, log)
        for candidate in promote.candidates(base_H, base_G):
            trial_H, trial_G = build_hypotheses(run_dir, log, promoted | {candidate})
            try:
                trial = v4_search.search(trial_H, trial_G, log, max_steps=max_steps,
                                         log_fn=lambda _m: None, run_dir=run_dir)
            except Exception as exc:  # noqa: BLE001 - a promotion that cannot be built loses
                notes.append(f"v4 promote {candidate}: build failed ({type(exc).__name__})")
                continue
            if trial.final.better_than(result.final):
                notes.append(f"v4 promote {candidate}: {result.final} -> {trial.final}")
                promoted.add(candidate)
                result, G = trial, trial_G
                result.moves.append({"move": "promote_leaf", "template": candidate,
                                     "score": trial.final.to_json()})
            else:
                notes.append(f"v4 promote {candidate}: rejected ({trial.final})")
        result.promoted = sorted(promoted)   # type: ignore[attr-defined]
        H = result.hypotheses          # the readings are already applied and materialised
        if write_diagnostics:
            (run_dir / READINGS_FILE).write_text(json.dumps(result.to_json(), indent=1))
            (run_dir / "search_v4.log").write_text("\n".join(notes) + "\n")
    else:
        from semabi.compiler.v4.identity import family_key
        result = None
        for template, unit in H.units.items():
            if template in identity:
                key_slot = identity[template]
            elif family_key(template) in identity:
                key_slot = identity[family_key(template)]
            else:
                continue
            if key_slot and key_slot not in unit.slots and "|" not in key_slot:
                key_slot = None       # the reading names a value this trace does not render
            unit.key_slot = key_slot
            if key_slot and "|" in key_slot:
                v4_search._materialise(unit, key_slot)

    H._build_entity_types()
    A = V2Abstractor(G, H, conservative_belief=conservative_belief)
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
    M.meta = {"v4": True, "n_steps": len(log.steps), "n_transitions": len(I.transitions),
              "n_operators": len(I.operators), "link_types": link_types,
              "belief_policy": "conservative_complete_collections" if conservative_belief else "legacy_visible_type_complete"}
    compiled = Compiled(log, None, A, I, M)
    compiled.v4 = result  # type: ignore[attr-defined]
    if write_diagnostics:
        M.save(run_dir / "model_v4.json")
        (run_dir / "model_v4.txt").write_text(str(M) + "\n\n" + I.report() + "\n\n" + A.summary())
    return compiled
