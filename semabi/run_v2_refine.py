"""Run one local counterexample-guided V2 abstraction refinement loop.

This command is compiler-side: it reads rendered evidence and controls the browser,
but never reads hidden state or evaluator annotations.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.compile_v2 import compile_v2
from semabi.compiler.v2.counterexamples import classify
from semabi.compiler.v2.explore import SurveyExplorer
from semabi.compiler.v2.refinement import (
    RefinementDecision,
    apply_correspondence_result,
    apply_intervention_result,
    apply_matrix_record_result,
    build_components,
    load_decisions,
    read_components,
    select_intervention,
    write_components,
    write_decisions,
    _matrix_context,
)
from semabi.compiler.v2.graph import tokens


def _candidate_targets(A, obs, component) -> list[dict]:
    """Rendered widgets matching a local ambiguity component in this observation."""
    sig = A.ensure(obs)
    units = A.H.parse_units(sig)
    source_template = component.scope["source_template"]
    source_slot = component.scope["source_slot"]
    colocal = next((h for h in component.hypotheses if h.kind == "ATTRIBUTE_ON_COLOCAL_MENTION"), None)
    target_template = colocal.target.get("target_template") if colocal else None
    out = []
    for owner in units:
        if owner.template != source_template:
            continue
        u = A.H.units.get(owner.template)
        owner_key = owner.slots.get(u.key_slot) if u and u.key_slot else None
        for sid, node_i in owner.slot_nodes.items():
            if sid.rstrip("~") != source_slot:
                continue
            node = obs.node(node_i)
            alternatives = [v for v in (node.options or []) if v != node.value]
            if node.role == "checkbox":
                alternatives = [not bool(node.checked)]
            if not alternatives:
                continue
            identity = {"source_template": source_template, "source_slot": source_slot,
                        "source_owner_key": owner_key, "widget_role": node.role}
            if target_template:
                siblings = []
                for candidate in units:
                    if candidate.template != target_template or obs.node(candidate.root).parent != node.parent:
                        continue
                    cu = A.H.units.get(candidate.template)
                    if cu and cu.key_slot and cu.key_slot in candidate.slots:
                        siblings.append((candidate, cu, candidate.slots[cu.key_slot]))
                if len(siblings) != 1:
                    continue
                candidate, cu, key = siblings[0]
                identity.update({"target_template": target_template, "target_key": key,
                                 "target_parent_key": A.H._parent_key(candidate)})
            out.append({"node": node_i, "current": node.value if node.role != "checkbox" else node.checked,
                        "alternatives": alternatives, "identity": identity})
    return out


def _value_of(A, obs, identity):
    sig = A.ensure(obs)
    units = A.H.parse_units(sig)
    for owner in units:
        if owner.template != identity["source_template"]:
            continue
        u = A.H.units.get(owner.template)
        owner_key = owner.slots.get(u.key_slot) if u and u.key_slot else None
        if owner_key != identity.get("source_owner_key"):
            continue
        for sid, node_i in owner.slot_nodes.items():
            if sid.rstrip("~") != identity["source_slot"]:
                continue
            node = obs.node(node_i)
            if identity.get("target_template"):
                matches = []
                for candidate in units:
                    if candidate.template != identity["target_template"] or obs.node(candidate.root).parent != node.parent:
                        continue
                    cu = A.H.units.get(candidate.template)
                    if cu and cu.key_slot and candidate.slots.get(cu.key_slot) == identity.get("target_key") \
                            and A.H._parent_key(candidate) == identity.get("target_parent_key"):
                        matches.append(candidate)
                if len(matches) != 1:
                    continue
            return node.checked if node.role == "checkbox" else node.value
    return None


def _status_counts(counterexamples) -> dict[str, int]:
    return dict(Counter(c.status for c in counterexamples))


def _historical_bridge_action(A, log, bridge):
    canonical_templates = set(bridge["canonical_templates"])
    observed_codes = {a for a, _ in bridge["observed_pairs"]}

    def source_code(value):
        ts = tokens(value or "")
        matches = [code for code in observed_codes if any(ts[i:i + len(tokens(code))] == tokens(code)
                                                           for i in range(len(ts) - len(tokens(code)) + 1))]
        return matches[0] if len(matches) == 1 else None

    for step in log.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        before = log.obs(step.before)
        after = log.obs(step.after)
        source = None
        for ui in A.H.parse_units(step.before):
            if ui.template == bridge["bridge_template"] and step.action.target in before.subtree(ui.root):
                key = ui.slots.get(bridge["bridge_key_slot"])
                code = source_code(key)
                if code is not None:
                    source = (ui, code)
                    break
        if source is None:
            continue
        revealed = False
        for ui in A.H.parse_units(step.after):
            if ui.template not in canonical_templates:
                continue
            u = A.H.units.get(ui.template)
            if u and u.key_slot and ui.slots.get(u.key_slot) is not None:
                revealed = True
                break
        if revealed:
            node = before.node(step.action.target)
            return {"role": node.role, "name": node.name, "source_key": source[1],
                    "observed_target_keys": [b for a, b in bridge["observed_pairs"] if a == source[1]]}
    return None


def _run_correspondence_probe(explorer, browser, A, component, seed: int) -> dict | None:
    colocal = next((h for h in component.hypotheses if h.kind == "ATTRIBUTE_ON_COLOCAL_MENTION"), None)
    bridge = colocal.target.get("correspondence_bridge") if colocal else None
    if not bridge:
        return None
    action = _historical_bridge_action(A, explorer.log, bridge)
    if action is None:
        return None

    obs = browser._last_obs or browser.observe()
    obs = explorer.step(obs, browser.episode + 1, Primitive("reset", text=str(seed)))
    episode = browser.episode
    explorer.note(obs)
    explorer.last_view_obs = {}
    obs, _ = explorer.survey(obs, episode)
    baseline_views = dict(explorer.last_view_obs)
    obs = explorer.step(obs, episode, Primitive("reload"))
    explorer.note(obs)

    # Navigate using only the already discovered static-control set until the bridge
    # representation is visible.
    def bridge_units(current):
        sig = A.ensure(current)
        return [ui for ui in A.H.parse_units(sig) if ui.template == bridge["bridge_template"]]

    if not bridge_units(obs):
        for name in explorer.nav_names():
            target = next((n for n in explorer._static_buttons(obs) if n.name == name), None)
            if target is None:
                continue
            obs = explorer.step(obs, episode, Primitive("click", target.i))
            explorer.note(obs)
            if bridge_units(obs):
                break
    units = bridge_units(obs)
    observed_codes = {a for a, _ in bridge["observed_pairs"]}

    def source_code(value):
        ts = tokens(value or "")
        matches = [code for code in observed_codes if any(ts[i:i + len(tokens(code))] == tokens(code)
                                                           for i in range(len(ts) - len(tokens(code)) + 1))]
        return matches[0] if len(matches) == 1 else None

    chosen = None
    for ui in units:
        source_key = source_code(ui.slots.get(bridge["bridge_key_slot"]))
        if source_key is None:
            continue
        for i in obs.subtree(ui.root):
            node = obs.node(i)
            if node.role == action["role"] and node.name == action["name"]:
                chosen = (ui, source_key, i)
                break
        if chosen:
            break
    if chosen is None:
        return None
    _, source_key, node_i = chosen
    before_sig = obs.structural_signature()
    action_step = len(explorer.log.steps)
    after = explorer.step(obs, episode, Primitive("click", node_i))
    explorer.note(after)
    after_sig = after.structural_signature()
    revealed_mentions = []
    for ui in A.H.parse_units(A.ensure(after)):
        if ui.template not in set(bridge["canonical_templates"]):
            continue
        u = A.H.units.get(ui.template)
        if u and u.key_slot:
            value = ui.slots.get(u.key_slot)
            if value is not None:
                revealed_mentions.append({"template": ui.template, "key": value})
    reloaded = explorer.step(after, episode, Primitive("reload"))
    explorer.note(reloaded)
    reload_sig = reloaded.structural_signature()
    surveyed, _ = explorer.survey(reloaded, episode)
    changed_views = sorted(name for name, sig in explorer.last_view_obs.items()
                           if name in baseline_views and baseline_views[name] != sig)
    supported = len(revealed_mentions) == 1 and not changed_views
    record = {"step": action_step, "status": "VIEW" if supported else "UNDETERMINED",
              "controlled": True, "kind": "IDENTITY_CORRESPONDENCE_PROBE",
              "component_id": component.id, "action": action,
              "source_key": source_key, "predicted_target_keys": action["observed_target_keys"],
              "revealed_target_keys": [x["key"] for x in revealed_mentions],
              "revealed_mentions": revealed_mentions, "before_sig": before_sig,
              "after_sig": after_sig, "reload_sig": reload_sig,
              "changed_views": changed_views, "view_invariance_supported": supported}
    with (Path(explorer.log.dir) / "interventions_v2.jsonl").open("a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _run_equal_key_reveal_probe(explorer, browser, A, component, seed: int) -> dict | None:
    """Repeat a compact-mention -> rich-representation reveal under reload/survey control."""
    scope = component.scope
    source_template = scope["source_template"]
    source_role = scope["source_role"]
    target_template = scope["target_template"]
    observed_keys = set(scope["observed_keys"])
    def lexical_prefix(value):
        match = re.match(r"[A-Za-z]+", value or "")
        return match.group(0).lower() if match else None

    observed_prefixes = {lexical_prefix(k) for k in observed_keys if lexical_prefix(k)}

    def matches_source(sig, node):
        observed_template = A.H.template(sig, node.i)
        # A fresh reset can introduce a key token absent from the fitted data vocabulary,
        # turning ``button[_]`` into a literal template temporarily.  Role plus the local
        # lexical proposal may select it for the probe; only the rich equal-key reveal can
        # accept it, and the refreshed fit then records its exact template/node provenance.
        return observed_template == source_template or "[_]" in source_template

    obs = browser._last_obs or browser.observe()
    obs = explorer.step(obs, browser.episode + 1, Primitive("reset", text=str(seed)))
    episode = browser.episode
    explorer.note(obs)
    explorer.last_view_obs = {}
    explorer.pending = []
    explorer.last_reload_obs = obs.structural_signature()
    if explorer.default_skeleton is None:
        explorer.default_skeleton = explorer.skeleton(obs)
    obs, _ = explorer.survey(obs, episode)
    explorer.post_reload_views = dict(explorer.last_view_obs)
    baseline_views = dict(explorer.last_view_obs)
    obs = explorer.step(obs, episode, Primitive("reload"))
    explorer.note(obs)

    def source_units(current):
        sig = A.ensure(current)
        out = []
        for node in current.nodes:
            if node.role != source_role or not matches_source(sig, node):
                continue
            key = node.name
            prefix = lexical_prefix(key)
            # Reset seeds legitimately introduce unseen entity keys.  A shared leading
            # lexical token is only a proposal prior; the executed equal-key rich reveal
            # below remains the evidence that can accept the association.
            if key in observed_keys or prefix in observed_prefixes:
                out.append((node.i, key))
        return out

    if not source_units(obs):
        # One unresolved mention can sit behind another contextual mention.  Try a small
        # generic sensing expansion using units from the same proposal template, stopping
        # as soon as the target candidate set appears.  The final reload/survey still
        # rejects the whole sequence if any persistent domain state leaked.
        obs = explorer.step(obs, episode, Primitive("reload"))
        explorer.note(obs)
        current_sig = A.ensure(obs)
        for node in list(obs.nodes)[:80]:
            if node.role != source_role or not matches_source(current_sig, node):
                continue
            node_i = node.i
            if node.name in explorer.nav_names():
                continue
            obs = explorer.step(obs, episode, Primitive("click", node_i))
            explorer.note(obs)
            if source_units(obs):
                break
            obs = explorer.step(obs, episode, Primitive("reload"))
            explorer.note(obs)
    if not source_units(obs):
        for name in explorer.nav_names():
            target = next((n for n in explorer._static_buttons(obs) if n.name == name), None)
            if target is None:
                continue
            obs = explorer.step(obs, episode, Primitive("click", target.i))
            explorer.note(obs)
            if source_units(obs):
                break
    candidates = source_units(obs)
    if not candidates:
        return None
    click_node, source_key = candidates[seed % len(candidates)]

    before_sig = obs.structural_signature()
    action_step = len(explorer.log.steps)
    after = explorer.step(obs, episode, Primitive("click", click_node))
    explorer.note(after)
    after_sig = after.structural_signature()
    revealed = []
    for ui in A.H.parse_units(A.ensure(after)):
        if ui.template != target_template:
            continue
        u = A.H.units.get(ui.template)
        if u and u.key_slot and ui.slots.get(u.key_slot) is not None:
            revealed.append(ui.slots[u.key_slot])
    reloaded = explorer.step(after, episode, Primitive("reload"))
    explorer.note(reloaded)
    reload_sig = reloaded.structural_signature()
    surveyed, _ = explorer.survey(reloaded, episode)
    changed_views = sorted(name for name, sig in explorer.last_view_obs.items()
                           if name in baseline_views and baseline_views[name] != sig)
    equal = revealed == [source_key]
    supported = equal and not changed_views
    record = {
        "step": action_step, "status": "VIEW" if supported else "UNDETERMINED",
        "controlled": True, "kind": "IDENTITY_CORRESPONDENCE_PROBE",
        "component_id": component.id, "source_template": source_template,
        "target_template": target_template, "source_key": source_key,
        "revealed_key": revealed[0] if len(revealed) == 1 else None,
        "revealed_keys": revealed, "equal_key_revealed": equal,
        "before_sig": before_sig, "after_sig": after_sig, "reload_sig": reload_sig,
        "changed_views": changed_views, "view_invariance_supported": supported,
    }
    with (Path(explorer.log.dir) / "interventions_v2.jsonl").open("a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _run_reveal_loop(run_dir, base, seed, baseline, before_counterexamples, components):
    components.sort(key=lambda c: (-len(c.counterexample_steps), c.id))
    component = components[0]
    browser = Browser(base.rstrip("/") + "/", base.rstrip("/") + "/reset")
    explorer = SurveyExplorer(browser, baseline.log, seed=seed, survey_prob=0.0)
    for obs in baseline.log.observations.values():
        explorer.note(obs)
    try:
        browser.goto()
        browser.observe()
        intervention = _run_equal_key_reveal_probe(explorer, browser, baseline.abstractor, component, seed)
    finally:
        browser.close()
    if intervention is None:
        raise RuntimeError("the selected reveal correspondence could not be executed")
    decision = apply_correspondence_result(component, intervention)
    if decision is None:
        raise RuntimeError("the reveal intervention did not support a mention association")

    refreshed = compile_v2(run_dir, llm=None, apply_refinements=False, write_diagnostics=False)
    refreshed_components = build_components(refreshed.abstractor, refreshed.log,
                                             classify(refreshed.abstractor, refreshed.log))
    fresh = next((c for c in refreshed_components if c.id == component.id), None)
    if fresh is not None:
        decision.target["mention_assignments"] = fresh.scope["mention_assignments"]
        decision.target["observed_keys"] = fresh.scope["observed_keys"]
    existing = [RefinementDecision(**d) for d in load_decisions(run_dir)]
    decisions = [d for d in existing if d.component_id != decision.component_id] + [decision]
    write_components(run_dir, [component])
    write_decisions(run_dir, decisions)

    refined = compile_v2(run_dir, llm=None, apply_refinements=True)
    after_counterexamples = classify(refined.abstractor, refined.log)
    before_status = {c.step: c.status for c in before_counterexamples}
    after_status = {c.step: c.status for c in after_counterexamples}
    domain_steps = {c.step for c in before_counterexamples if c.probe_status == "DOMAIN"}
    selected = [s for s in component.counterexample_steps if s in domain_steps][:1]
    resolved = [s for s in selected if before_status.get(s) == "UNGROUNDED"
                and after_status.get(s) == "EXPLAINED"]
    report = {
        "version": 1, "run": str(run_dir), "component_id": component.id,
        "selected_counterexamples": selected,
        "affected_counterexamples": component.counterexample_steps,
        "resolved_counterexamples": resolved,
        "counterexample_resolution_rate": round(len(resolved) / len(selected), 3) if selected else None,
        "resolution_mode": "DIAGNOSTIC_INTERVENTION",
        "selected_abstraction_contradictions": [component.id],
        "before_status_counts": _status_counts(before_counterexamples),
        "after_status_counts": _status_counts(after_counterexamples),
        "intervention": intervention, "decision": decision.__dict__,
        "mention_conflicts": refined.abstractor.mention_conflicts[:100],
    }
    (Path(run_dir) / "refinement_result_v2.json").write_text(json.dumps(report, indent=1, default=str))
    return report


def _run_matrix_probe(explorer, browser, A, component, seed):
    scope = component.scope
    obs = browser._last_obs or browser.observe()
    obs = explorer.step(obs, browser.episode + 1, Primitive("reset", text=str(seed)))
    episode = browser.episode
    explorer.note(obs)
    explorer.last_view_obs = {}
    explorer.pending = []
    explorer.last_reload_obs = obs.structural_signature()
    if explorer.default_skeleton is None:
        explorer.default_skeleton = explorer.skeleton(obs)
    obs, _ = explorer.survey(obs, episode)
    explorer.post_reload_views = dict(explorer.last_view_obs)
    baseline_views = dict(explorer.last_view_obs)
    obs = explorer.step(obs, episode, Primitive("reload"))
    explorer.note(obs)

    def live_cells(current):
        sig = A.ensure(current)
        target_keys = {v for t in A.H.entity_types[scope["target_entity_tid"]].units
                       for v in A.H.units[t].primary_key_values()}
        found = []
        for ui in A.H.parse_units(sig):
            if ui.template not in scope["row_templates"]:
                continue
            row_u = A.H.units.get(ui.template)
            anchor = ui.slots.get(row_u.key_slot) if row_u and row_u.key_slot else None
            for cell in [c for c in current.children(ui.root) if current.node(c).role == "cell"]:
                context = _matrix_context(A, sig, cell)
                if context is None:
                    continue
                for node_i in current.subtree(cell):
                    node = current.node(node_i)
                    if node.role in ("button", "link") and node.name in target_keys:
                        found.append((node_i, anchor, context, node.name))
        return found

    if not live_cells(obs):
        for name in explorer.nav_names():
            target = next((n for n in explorer._static_buttons(obs) if n.name == name), None)
            if target is None:
                continue
            obs = explorer.step(obs, episode, Primitive("click", target.i))
            explorer.note(obs)
            if live_cells(obs):
                break
    candidates = live_cells(obs)
    if not candidates:
        return None
    node_i, anchor_key, context_key, target_key = candidates[seed % len(candidates)]
    before_sig = obs.structural_signature()
    action_step = len(explorer.log.steps)
    after = explorer.step(obs, episode, Primitive("click", node_i))
    explorer.note(after)
    after_sig = after.structural_signature()
    triples = []
    for ui in A.H.parse_units(A.ensure(after)):
        if ui.template != scope["detail_template"]:
            continue
        u = A.H.units.get(ui.template)
        triples.append((ui.slots.get(u.key_slot), ui.slots.get(scope["detail_context_slot"]),
                        ui.slots.get(scope["detail_target_slot"])))
    reloaded = explorer.step(after, episode, Primitive("reload"))
    explorer.note(reloaded)
    reload_sig = reloaded.structural_signature()
    surveyed, _ = explorer.survey(reloaded, episode)
    changed_views = sorted(name for name, sig in explorer.last_view_obs.items()
                           if name in baseline_views and baseline_views[name] != sig)
    triple = (anchor_key, context_key, target_key)
    supported = triples == [triple] and not changed_views
    record = {
        "step": action_step, "status": "VIEW" if supported else "UNDETERMINED",
        "controlled": True, "kind": "MATRIX_RECORD_CORRESPONDENCE_PROBE",
        "component_id": component.id, "anchor_key": anchor_key,
        "context_key": context_key, "target_key": target_key,
        "revealed_triples": triples, "triple_revealed": triples == [triple],
        "before_sig": before_sig, "after_sig": after_sig, "reload_sig": reload_sig,
        "changed_views": changed_views, "view_invariance_supported": supported,
    }
    with (Path(explorer.log.dir) / "interventions_v2.jsonl").open("a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _run_matrix_loop(run_dir, base, seed, baseline, before_counterexamples, components):
    components.sort(key=lambda c: (-len(c.scope.get("matrix_cells", [])), c.id))
    component = components[0]
    browser = Browser(base.rstrip("/") + "/", base.rstrip("/") + "/reset")
    explorer = SurveyExplorer(browser, baseline.log, seed=seed, survey_prob=0.0)
    for obs in baseline.log.observations.values():
        explorer.note(obs)
    try:
        browser.goto()
        browser.observe()
        intervention = _run_matrix_probe(explorer, browser, baseline.abstractor, component, seed)
    finally:
        browser.close()
    if intervention is None:
        raise RuntimeError("the selected matrix-record probe could not be executed")
    decision = apply_matrix_record_result(component, intervention)
    if decision is None:
        raise RuntimeError("the matrix-record intervention did not support a split")
    refreshed = compile_v2(run_dir, llm=None, apply_refinements=False, write_diagnostics=False)
    fresh_components = build_components(refreshed.abstractor, refreshed.log,
                                        classify(refreshed.abstractor, refreshed.log))
    fresh = next((c for c in fresh_components if c.id == component.id), None)
    if fresh is not None:
        decision.target = dict(fresh.scope)
    existing = [RefinementDecision(**d) for d in load_decisions(run_dir)]
    decisions = [d for d in existing if d.component_id != decision.component_id] + [decision]
    write_components(run_dir, [component])
    write_decisions(run_dir, decisions)
    refined = compile_v2(run_dir, llm=None, apply_refinements=True)
    after_counterexamples = classify(refined.abstractor, refined.log)
    before_status = {c.step: c.status for c in before_counterexamples}
    after_status = {c.step: c.status for c in after_counterexamples}
    selected = []
    resolved = [s for s in selected if before_status.get(s) == "UNGROUNDED"
                and after_status.get(s) == "EXPLAINED"]
    report = {
        "version": 1, "run": str(run_dir), "component_id": component.id,
        "selected_counterexamples": selected, "affected_counterexamples": component.counterexample_steps,
        "resolved_counterexamples": resolved,
        "counterexample_resolution_rate": round(len(resolved) / len(selected), 3) if selected else None,
        "resolution_mode": "DIAGNOSTIC_INTERVENTION",
        "selected_abstraction_contradictions": [component.id],
        "before_status_counts": _status_counts(before_counterexamples),
        "after_status_counts": _status_counts(after_counterexamples),
        "intervention": intervention, "decision": decision.__dict__,
        "mention_conflicts": refined.abstractor.mention_conflicts[:100],
    }
    (Path(run_dir) / "refinement_result_v2.json").write_text(json.dumps(report, indent=1, default=str))
    return report


def run_loop(run_dir: Path, base: str, seed: int = 0, max_attempts: int = 6) -> dict:
    run_dir = Path(run_dir)
    baseline = compile_v2(run_dir, llm=None, apply_refinements=False)
    before_counterexamples = classify(baseline.abstractor, baseline.log)
    before_status = {c.step: c.status for c in before_counterexamples}
    components = read_components(run_dir)
    widget_components = [c for c in components if any(h.kind == "ATTRIBUTE_ON_COLOCAL_MENTION" for h in c.hypotheses)]
    if not widget_components:
        matrix_components = [c for c in components if any(h.kind == "RELATIONAL_RECORD_SPLIT" for h in c.hypotheses)]
        if matrix_components:
            return _run_matrix_loop(run_dir, base, seed, baseline, before_counterexamples, matrix_components)
        reveal_components = [c for c in components if any(h.kind == "SAME_ENTITY_MENTION_SET" for h in c.hypotheses)]
        if reveal_components:
            return _run_reveal_loop(run_dir, base, seed, baseline, before_counterexamples, reveal_components)
        raise RuntimeError("no local widget/entity ambiguity was generated from an UNGROUNDED transition")
    components = widget_components
    components.sort(key=lambda c: (-len(c.counterexample_steps), c.id))
    component = components[0]
    plan = select_intervention(component)
    write_components(run_dir, components)

    browser = Browser(base.rstrip("/") + "/", base.rstrip("/") + "/reset")
    explorer = SurveyExplorer(browser, baseline.log, seed=seed, survey_prob=0.0)
    # Reuse the broad trace to identify static navigation controls; no semantic label is
    # imported and no diagnostic action displaces the already collected coverage trace.
    for obs in baseline.log.observations.values():
        explorer.note(obs)
    result = None
    decision = None
    correspondence = None
    try:
        browser.goto()
        obs = browser.observe()
        for attempt in range(max_attempts):
            obs = explorer.step(obs, browser.episode + 1, Primitive("reset", text=str(seed + attempt)))
            episode = browser.episode
            explorer.note(obs)
            explorer.last_view_obs = {}
            explorer.pending = []
            explorer.last_reload_obs = obs.structural_signature()
            if explorer.default_skeleton is None:
                explorer.default_skeleton = explorer.skeleton(obs)
            obs, _ = explorer.survey(obs, episode)
            explorer.post_reload_views = dict(explorer.last_view_obs)
            # Surveys may finish on another view; reload returns to the default view where
            # the counterexample's structural component was originally observed.
            obs = explorer.step(obs, episode, Primitive("reload"))
            explorer.note(obs)
            targets = _candidate_targets(baseline.abstractor, obs, component)
            if not targets:
                continue
            target = targets[attempt % len(targets)]
            chosen = target["alternatives"][attempt % len(target["alternatives"])]
            if isinstance(chosen, bool):
                primitive = Primitive("click", target["node"])
            else:
                primitive = Primitive("select", target["node"], str(chosen))
            obs, record = explorer.controlled_persistence_probe(
                obs, episode, primitive, component.id, target["identity"],
                lambda current, identity: _value_of(baseline.abstractor, current, identity), plan["predictions"],
            )
            record["attempt"] = attempt
            if record["same_mention_value_persisted"]:
                result = record
                break
        if result is None:
            write_components(run_dir, components)
            raise RuntimeError(f"no controlled value change persisted after {max_attempts} attempts")
        decision = apply_intervention_result(component, result)
        if decision is None:
            raise RuntimeError("the intervention did not support an applicable refinement")
        correspondence = _run_correspondence_probe(explorer, browser, baseline.abstractor, component,
                                                    seed + max_attempts + 1)
    finally:
        browser.close()
    assert decision is not None
    bridge = decision.target.get("correspondence_bridge")
    if correspondence and correspondence.get("view_invariance_supported") and bridge:
        # Refit the proposal layer over the augmented trace.  The persistence attempts and
        # the identity probe introduce new observation signatures; an old point-in-time
        # override list would leave those mentions unassociated.  The accepted intervention
        # authorizes only the same local bridge, while the refreshed proposal supplies all
        # observation-scoped instances now supported by the accumulated action history.
        refreshed = compile_v2(run_dir, llm=None, apply_refinements=False, write_diagnostics=False)
        refreshed_components = build_components(
            refreshed.abstractor,
            refreshed.log,
            classify(refreshed.abstractor, refreshed.log),
        )
        fresh_component = next((c for c in refreshed_components if c.id == component.id), None)
        fresh_colocal = next(
            (h for h in (fresh_component.hypotheses if fresh_component else [])
             if h.kind == "ATTRIBUTE_ON_COLOCAL_MENTION"),
            None,
        )
        fresh_bridge = fresh_colocal.target.get("correspondence_bridge") if fresh_colocal else None
        if fresh_bridge is not None:
            decision.target["correspondence_bridge"] = fresh_bridge
            decision.target["key_overrides"] = fresh_bridge["key_overrides"]
        decision.evidence.append({"evidence_class": "VIEW_INVARIANCE_SUPPORT",
                                  "source": "controlled_identity_correspondence_probe",
                                  "intervention": correspondence})
    existing = [RefinementDecision(**d) for d in load_decisions(run_dir)]
    decisions = [d for d in existing if d.component_id != decision.component_id] + [decision]
    write_components(run_dir, components)
    write_decisions(run_dir, decisions)

    refined = compile_v2(run_dir, llm=None, apply_refinements=True)
    after_counterexamples = classify(refined.abstractor, refined.log)
    after_status = {c.step: c.status for c in after_counterexamples}
    # One representative counterexample was selected for this intervention.  Other
    # structurally equivalent events may become representable too, but they are not
    # counted as independently attempted/resolved examples.
    selected_steps = component.counterexample_steps[:1]
    affected_steps = component.counterexample_steps
    resolved = [s for s in selected_steps if before_status.get(s) == "UNGROUNDED" and after_status.get(s) == "EXPLAINED"]
    report = {
        "version": 1,
        "run": str(run_dir),
        "component_id": component.id,
        "selected_counterexamples": selected_steps,
        "affected_counterexamples": affected_steps,
        "resolved_counterexamples": resolved,
        "counterexample_resolution_rate": round(len(resolved) / len(selected_steps), 3) if selected_steps else None,
        "resolution_mode": "DIAGNOSTIC_INTERVENTION",
        "before_status_counts": _status_counts(before_counterexamples),
        "after_status_counts": _status_counts(after_counterexamples),
        "intervention": result,
        "correspondence_intervention": correspondence,
        "decision": decision.__dict__,
        "mention_conflicts": refined.abstractor.mention_conflicts[:100],
    }
    (run_dir / "refinement_result_v2.json").write_text(json.dumps(report, indent=1, default=str))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-attempts", type=int, default=6)
    args = ap.parse_args()
    report = run_loop(Path(args.run), args.base, args.seed, args.max_attempts)
    print(json.dumps(report, indent=1, default=str))


if __name__ == "__main__":
    main()
