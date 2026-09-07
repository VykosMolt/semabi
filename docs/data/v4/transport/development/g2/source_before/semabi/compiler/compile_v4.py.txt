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
from semabi.compiler.v2.graph import ObsGraph
from semabi.compiler.v2.hypotheses import Hypotheses
from semabi.compiler.v2 import sections
from semabi.compiler.v4.abstractor import V4Abstractor
from semabi.compiler.v4 import pinned as v4_pinned, promote, search as v4_search

READINGS_FILE = "identity_readings_v4.json"


def _normalise_sections(log: EvidenceLog, stats_from: EvidenceLog | None = None) -> None:
    """Re-read this log's pages with heading-delimited sections made explicit, in place.

    Two passes are needed and one suffices.  Deciding that a span of siblings is an object
    requires knowing which of its tokens are *data*, which is a corpus statistic and is not
    complete until every page is in a graph; and the containers `normalise` appends carry no
    text, so the statistics are unchanged afterwards and the fixed point is immediate.

    The rewrite happens on the log rather than on the graph because a signature must name
    exactly one `Observation` everywhere.  Holding a normalised page in the graph while callers
    still passed the raw one around meant two objects with different node counts and the same
    signature, and an index taken from one and applied to the other is out of range.  The
    containers are appended, so every node keeps the index it had and a recorded action target
    still names the element it named.
    """
    # Which tokens count as *data* is a corpus statistic, and under a regime it is the
    # regime's corpus: `stats_from` is the prefix the model is allowed, so a page's section
    # structure is decided by evidence that existed before the action it is read for.
    source = stats_from if stats_from is not None else log
    probe = ObsGraph()
    for sig, obs in source.observations.items():
        probe.add(sig, obs)
    for sig, obs in log.observations.items():
        if sig not in probe.obs:
            probe.add(sig, obs)      # readable, but contributing no statistics
    fixed = {sig: sections.normalise(probe, sig, obs) for sig, obs in log.observations.items()}
    if all(fixed[sig] is obs for sig, obs in log.observations.items()):
        return
    # A page's signature is a hash of its structure, so adding containers changes it.  Every
    # recorded signature has to move with it or code that recomputes one will not find the
    # page it names.  Node *indices* are untouched, so actions still name their elements.
    remap = {old: new.structural_signature() for old, new in fixed.items()}
    log.observations.clear()
    for old, obs in fixed.items():
        log.observations[remap[old]] = obs
    for step in log.steps:
        step.before = remap.get(step.before, step.before)
        step.after = remap.get(step.after, step.after)


def build_hypotheses(run_dir: Path, log: EvidenceLog,
                     promoted: set[str] | None = None) -> tuple[Hypotheses, ObsGraph]:
    _normalise_sections(log)
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
               identity: dict[str, str | None] | None = None,
               pinned: "v4_pinned.PinnedReading | None" = None,
               evidence_log: EvidenceLog | None = None,
               read_outputs: bool = True) -> Compiled:
    """Compile with V4 identity selection.

    `pinned` carries a whole frozen reading from another interaction history and applies it
    here without searching: no key is re-chosen, no family is rebuilt as a hypothesis, and a
    claim that cannot be instantiated is recorded rather than repaired.  This is the only
    supported way to transport a reading.

    `identity` is the older, weaker form -- a bare family-to-key map applied on top of a
    hypothesis structure that was otherwise refitted here.  It is kept because the earlier
    development evidence was produced with it, and it is not transport.

    When both are None the behavioural search decides locally.
    """
    run_dir = Path(run_dir)
    log = evidence_log if evidence_log is not None else EvidenceLog(run_dir)
    # A provided log is immutable custody evidence.  Diagnostics would write beside a
    # potentially mutable path and are therefore disabled at this boundary.
    if evidence_log is not None:
        write_diagnostics = False
    search_run_dir = None if evidence_log is not None else run_dir
    transport = None
    if pinned is not None:
        probe_H, probe_G = build_hypotheses(run_dir, log)
        leaves, absent = v4_pinned.promoted_templates(probe_H, probe_G, pinned)
        H, G = build_hypotheses(run_dir, log, leaves) if leaves else (probe_H, probe_G)
        transport = v4_pinned.apply(H, pinned, absent)
    else:
        H, G = build_hypotheses(run_dir, log)

    notes: list[str] = []
    if pinned is not None:
        result = None
    elif identity is None:
        result = v4_search.search(H, G, log, max_steps=max_steps, log_fn=notes.append,
                                  run_dir=search_run_dir)
        # whether a repeated leaf is a value of its container or an object of its own is the
        # other half of the observation model, and it is decided the same way: on trial,
        # kept only on a strict improvement
        promoted: set[str] = set()
        base_H, base_G = build_hypotheses(run_dir, log)
        for candidate in promote.candidates(base_H, base_G):
            trial_H, trial_G = build_hypotheses(run_dir, log, promoted | {candidate})
            try:
                trial = v4_search.search(trial_H, trial_G, log, max_steps=max_steps,
                                         log_fn=lambda _m: None, run_dir=search_run_dir)
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
        G = H.G                       # search copies hypotheses together with their graph
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
    # An entity is the set of its mentions.  Off, a second mention of an object on a page
    # is dropped and the first -- in DOM order -- speaks for it; under a reading in which
    # the calls table and the vessels table are one type keyed by the vessel's name
    # (`docs/v4_open_world.md`), that left every vessel with a call on the board without
    # its flag, its cargo or its current-call reference.  V2 switched this on by refinement
    # decision only; here it is the reading of a page, and conflicts between mentions are
    # still recorded rather than resolved.
    A = V4Abstractor(G, H, conservative_belief=conservative_belief, merge_mentions=True)
    A.fit_view_controls(log)
    I = Inducer(A, log, read_outputs=read_outputs)
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
    compiled.transport = transport  # type: ignore[attr-defined]
    compiled.pinned = pinned  # type: ignore[attr-defined]
    compiled.hypotheses = H  # type: ignore[attr-defined]
    if write_diagnostics:
        M.save(run_dir / "model_v4.json")
        (run_dir / "model_v4.txt").write_text(str(M) + "\n\n" + I.report() + "\n\n" + A.summary())
    return compiled
