"""Cost-bounded novel predictive probes for provisional V2 refinements."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import affordance_key
from semabi.compiler.v2.explore import SurveyExplorer
from semabi.compiler.v2.graph import node_text
from semabi.compiler.v2.refinement import _embedded_key, _preceding_heading_context


def _source_probe(decision: dict[str, Any]) -> dict[str, Any]:
    for item in decision.get("evidence", []):
        intervention = item.get("intervention")
        if isinstance(intervention, dict):
            return intervention
    return {}


def _buttons(obs, excluded=()):
    excluded = set(excluded)
    return [node for node in obs.nodes
            if node.role == "button" and node.name and node.name not in excluded]


def _contexts(observations, key: str) -> list[str]:
    found = set()
    for obs in observations:
        for node in obs.nodes:
            if node.role not in ("button", "link", "group", "text"):
                continue
            if _embedded_key(node_text(node), {key}) != key:
                continue
            context = _preceding_heading_context(obs, node.i)
            if context is not None:
                found.add(context)
    return sorted(found)


def run_context_validation_probe(source_run: Path, validation_run: Path, base: str,
                                 decision: dict[str, Any], seed: int,
                                 browser_hook=None, max_context_trials: int = 3) -> dict:
    """Vary both container and entity, then test a frozen prediction about a context move.

    Candidate controls are found only through rendered roles and names, and through the
    affordances the earlier decision recorded. The entity key and reset seed used here must
    be absent from the evidence that supported that decision.
    """
    if decision.get("kind") != "ATTACH_CONTEXT_MEMBERSHIP":
        raise ValueError("context validation requires ATTACH_CONTEXT_MEMBERSHIP")
    source_run, validation_run = Path(source_run), Path(validation_run)
    validation_run.mkdir(parents=True, exist_ok=True)
    log = EvidenceLog(validation_run)
    browser = Browser(base.rstrip("/") + "/", base.rstrip("/") + "/reset")
    if browser_hook is not None:
        browser.step_hooks.append(browser_hook)
    explorer = SurveyExplorer(browser, log, seed=seed, survey_prob=0.0)
    target = decision["target"]
    source_probe = _source_probe(decision)
    source_keys = set(target.get("observed_keys", []))
    source_seed = str(target.get("reset_seed"))
    source_context = target["source_context"]
    target_context = target["target_context"]
    prefix_names = [x.get("name") for x in target.get("replay_prefix", []) if x.get("name")]
    tail_names = [x.get("name") for x in target.get("replay_tail", []) if x.get("name")]
    domain_action_name = next((name for name in tail_names if name), None)
    terminal_name = next((name for name in reversed(tail_names) if name != domain_action_name), None)
    view_names = [
        (x.get("key") or [None, None, None])[2]
        for x in source_probe.get("sensing_actions", [])
        if len(x.get("key") or []) >= 3 and (x.get("key") or [None, None, None])[2]
    ]
    if domain_action_name is None or terminal_name is None:
        raise RuntimeError("source decision has no replayable domain/terminal affordance")

    phases: list[dict[str, Any]] = []
    chosen_key = chosen_context = None
    before_obs = after_obs = reload_obs = None
    test_observations = []
    prediction_frozen = {
        "entity_key_not_in_support": True,
        "reset_seed_differs_from_support": str(seed) != source_seed,
        "after_reload_context": target_context,
        "old_context_absent": True,
        "persistent_domain_delta": True,
    }
    try:
        browser.goto()
        obs = browser.observe()
        initial_buttons = set()
        context_candidates = []
        for trial in range(max_context_trials):
            start = len(log.steps)
            obs = explorer.step(obs, browser.episode + 1, Primitive("reset", text=str(seed + trial)))
            explorer.note(obs)
            initial_buttons = {node.name for node in _buttons(obs, [*view_names, *tail_names])}
            context_candidates = [node for node in _buttons(obs, [*view_names, *tail_names, *prefix_names])]
            phases.append({"kind": "CONTEXT_TRIAL_RESET", "trial": trial,
                           "steps": list(range(start, len(log.steps)))})
            for context_node in context_candidates:
                context_start = len(log.steps)
                context_name = context_node.name
                obs = explorer.step(obs, browser.episode, Primitive("click", context_node.i))
                explorer.note(obs)
                entity_candidates = [node for node in _buttons(obs, [*view_names, *tail_names])
                                     if node.name not in initial_buttons and node.name not in source_keys]
                for entity_node in entity_candidates:
                    key = entity_node.name
                    detail = explorer.step(obs, browser.episode, Primitive("click", entity_node.i))
                    explorer.note(detail)
                    has_source = source_context in _contexts([detail], key)
                    has_action = any(node.name == domain_action_name for node in _buttons(detail))
                    if has_source and has_action:
                        chosen_key, chosen_context, before_obs = key, context_name, detail
                        obs = detail
                        phases.append({"kind": "NOVEL_CONTEXT_AND_ENTITY_SELECTION",
                                       "context": context_name, "entity_key": key,
                                       "steps": list(range(context_start, len(log.steps)))})
                        break
                    # Return to the selected context without exploring another branch of
                    # the application.  One new entity per context is enough.
                    obs = explorer.step(detail, browser.episode, Primitive("reset", text=str(seed + trial)))
                    explorer.note(obs)
                    replacement = next((node for node in _buttons(obs) if node.name == context_name), None)
                    if replacement is None:
                        break
                    obs = explorer.step(obs, browser.episode, Primitive("click", replacement.i))
                    explorer.note(obs)
                if chosen_key is not None:
                    break
                obs = explorer.step(obs, browser.episode, Primitive("reset", text=str(seed + trial)))
                explorer.note(obs)
            if chosen_key is not None:
                break
        if chosen_key is None or before_obs is None:
            raise RuntimeError("no novel rendered context/entity pair exposed the predicted action")

        action_start = len(log.steps)
        action_button = next(node for node in _buttons(obs) if node.name == domain_action_name)
        obs = explorer.step(obs, browser.episode, Primitive("click", action_button.i))
        explorer.note(obs)
        terminal = next((node for node in _buttons(obs) if node.name == terminal_name), None)
        if terminal is None:
            raise RuntimeError("novel entity did not expose the predicted terminal affordance")
        terminal_step = len(log.steps)
        obs = explorer.step(obs, browser.episode, Primitive("click", terminal.i))
        explorer.note(obs)
        after_obs = obs
        phases.append({"kind": "NOVEL_PREDICTIVE_DOMAIN_TEST",
                       "steps": list(range(action_start, len(log.steps)))})

        reload_start = len(log.steps)
        obs = explorer.step(obs, browser.episode, Primitive("reload"))
        explorer.note(obs)
        reload_obs = obs
        test_observations.extend([after_obs, reload_obs])
        for view_name in dict.fromkeys(view_names):
            target_node = next((node for node in _buttons(obs) if node.name == view_name), None)
            if target_node is None:
                continue
            obs = explorer.step(obs, browser.episode, Primitive("click", target_node.i))
            explorer.note(obs)
            test_observations.append(obs)
        phases.append({"kind": "VALIDATION_RELOAD_AND_RELEVANT_VIEW_SURVEY",
                       "steps": list(range(reload_start, len(log.steps)))})
    finally:
        browser.close()

    after_contexts = _contexts(test_observations, chosen_key)
    target_persisted = target_context in after_contexts
    source_absent = source_context not in after_contexts
    directly_validated = (chosen_key not in source_keys and str(seed) != source_seed
                          and target_persisted and source_absent)
    record = {
        "version": 1,
        "kind": "NOVEL_CONTEXT_MEMBERSHIP_PREDICTION_TEST",
        "decision_ids": [decision["id"]],
        "source_run": str(source_run),
        "validation_run": str(validation_run),
        "status": "SUPPORTED" if directly_validated else "MISPREDICTED",
        "prediction_frozen_before_action": prediction_frozen,
        "actual": {
            "reset_seed": seed,
            "context_control": chosen_context,
            "entity_key": chosen_key,
            "contexts_after_reload_and_survey": after_contexts,
            "target_context_persisted": target_persisted,
            "source_context_absent": source_absent,
            "terminal_action_step": terminal_step,
        },
        "novelty": {
            "entity_key_not_in_support": chosen_key not in source_keys,
            "reset_seed_differs_from_support": str(seed) != source_seed,
            "context_control_differs_from_support": chosen_context not in prefix_names,
        },
        "primitive_cost": {
            "total": len(log.steps),
            "by_phase": phases,
            "hypothesis_validation_primitives": sum(
                len(row["steps"]) for row in phases
                if row["kind"] in ("NOVEL_PREDICTIVE_DOMAIN_TEST", "VALIDATION_RELOAD_AND_RELEVANT_VIEW_SURVEY")
            ),
        },
        "compiler_reads_hidden_snapshots": False,
    }
    (validation_run / "prospective_intervention_v2.json").write_text(
        json.dumps(record, indent=1, default=str)
    )
    with (validation_run / "interventions_v2.jsonl").open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    return record
