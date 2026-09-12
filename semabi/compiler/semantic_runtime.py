"""Bounded composition of observed navigation, selection and semantic actions.

The supplied language is a sequence of scoped clicks and field fills. Repeated
local headings propose selector arguments; observed transitions supply the
sequence, and V4 supplies the owner, relation and response condition. No UI
action word, application route or business field is an integration answer.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
import json
import math
import re

from semabi.compiler.browser import Primitive
from semabi.compiler.surface import Surface, argument_name, digest, local_regions


def _stop(reason, *, stale=False):
    from semabi.compiler.runtime import StopOperation
    raise StopOperation(reason, stale=stale)


def has_onboarding_history(runtime, connection):
    root = runtime.data_dir / connection["id"] / "evidence"
    return any(json.loads(line).get("action", {}).get("kind") == "navigate"
               for path in root.glob("*/steps.jsonl") for line in path.read_text().splitlines())


def local_anchor(surface, root, control_node=None):
    """A unique observed row anchor, not a persistent identity or complete listing.

    Heading anchors also work beside constant controls. Otherwise a leaf's value
    must be repeated by a control label; neither column order nor word shape names
    the record. Competing anchors remain unresolved.
    """
    obs = surface.observation
    nodes = [obs.node(i) for i in obs.subtree(root)]
    headings = [n for n in nodes if n.role == "heading" and n.name]
    if len(headings) == 1:
        return headings[0]
    controls = ([control_node] if control_node is not None else
                [n.i for n in nodes if n.i in surface.controls])
    candidates = [n for n in nodes if n.role in {"cell", "text"} and n.name
                  and not obs.children(n.i) and n.i not in surface.controls
                  and any(surface.controls[i]["label"].count(n.name) == 1 for i in controls)]
    return candidates[0] if len(candidates) == 1 else None


def selector(surface, node):
    """An anchored control in one observed local row, not a business key."""
    obs = surface.observation
    regions = {region["root"] for region in local_regions(obs)}
    for root in obs.ancestors(node):
        if root not in regions:
            continue
        anchor = local_anchor(surface, root, node)
        if anchor is None:
            continue
        value = anchor.name
        descriptor = surface.descriptor(node)
        label = descriptor["label"]
        # The same heading may be restated in a button, or a constant control
        # may sit next to it. Neither makes the heading globally unique.
        if label.count(value) == 1:
            prefix, suffix = label.split(value)
            descriptor["label"] = {"prefix": prefix, "suffix": suffix}
        return {"descriptor": descriptor, "region_role": obs.node(root).role,
                "anchor_role": anchor.role, "value": value}
    return None


def step_for(surface, node, route):
    selected = selector(surface, node)
    if selected:
        index = 1 + sum("selector" in step for step in route)
        step = {"kind": "click", "selector": selected,
                "argument": "target" if index == 1 else f"selection_{index}"}
    else:
        step = {"kind": "click", "descriptor": surface.descriptor(node)}
    if surface.observation.node(node).role == "radio":
        step["postcondition"] = {"checked": True}
    return step


def resolve_step(surface, step, arguments=None):
    if "selector" not in step:
        hits = surface.resolve(step["descriptor"])
    else:
        spec = step["selector"]
        value = (arguments or {}).get(step["argument"], spec["value"])
        descriptor = deepcopy(spec["descriptor"])
        if isinstance(descriptor["label"], dict):
            descriptor["label"] = descriptor["label"]["prefix"] + value + descriptor["label"]["suffix"]
        obs = surface.observation
        roots = [region["root"] for region in local_regions(obs)
                 if region["role"] == spec["region_role"] and
                 sum(obs.node(i).role == spec["anchor_role"] and obs.node(i).name == value
                     for i in obs.subtree(region["root"])) == 1]
        hits = sorted({node for root in roots for node in surface.resolve(descriptor, within=root)})
    if len(hits) != 1:
        _stop("Scoped target has no match" if not hits else "Scoped target has multiple matches")
    if surface.controls[hits[0]]["disabled"]:
        _stop("Resolved control is disabled")
    return hits[0]


def route_key(route):
    route = deepcopy(route)
    for step in route:
        if "selector" in step:
            step["selector"].pop("value", None)
    return digest(route)


def shape(surface):
    """Navigation evidence ignores response contents and changing field values."""
    obs = surface.observation
    skip = {i for n in obs.nodes if n.role in {"status", "alert", "log"}
            for i in obs.subtree(n.i)}
    kept = [n for n in obs.nodes if n.i not in skip]
    indices = {n.i: index for index, n in enumerate(kept)}
    return digest([(indices.get(n.parent, -1), n.role) for n in kept])


def procedure_context(surface):
    """Finite discrete UI context; text/numeric values do not create graph nodes."""
    states = [(n.role, n.checked, n.selected, n.pressed) for n in surface.observation.nodes
              if n.i in surface.controls and
              (n.checked is not None or n.selected is not None or n.pressed is not None)]
    return digest([shape(surface), states]) if states else shape(surface)


def act_step(browser, trace, surface, step, arguments=None):
    node = resolve_step(surface, step, arguments)
    after = trace.act(browser, surface, Primitive(step["kind"], node, step.get("text")))
    if step.get("postcondition"):
        selected = after.observation.node(resolve_step(after, step, arguments))
        if any(getattr(selected, name, None) != value for name, value in step["postcondition"].items()):
            _stop("Selection did not reach its observable postcondition")
    return after


def replay(browser, trace, entry, route, arguments=None, *, context=None, acquiring=False):
    before = trace.read(browser)
    surface = trace.navigate(browser, entry)
    trace.log.add_step(0, Primitive("navigate", text=entry), True, None,
                       before.observation, surface.observation)
    if context is not None:
        context.setdefault("entry_shape", shape(surface))
        context.setdefault("returns", [])
        for _ in range(4):
            if shape(surface) == context["entry_shape"]:
                break
            candidates = [edge for edge in context["returns"] if edge["before"] == shape(surface)]
            if candidates:
                descriptor = candidates[0]["descriptor"]
                hits = surface.resolve(descriptor)
            elif acquiring:
                # Navigation words propose an experiment. Only the actual
                # observed edge is retained for execution, with its endpoints.
                hits = [node for node, control in surface.controls.items()
                        if control["role"] in {"button", "link"} and not control["disabled"]
                        and re.search(r"\b(back|return|close|cancel)\b", control["label"], re.I)]
                if not hits:
                    from semabi.compiler.runtime import EXCLUDED_WORDS
                    # A dialog may expose only forward selection. Explore an
                    # enabled local choice to discover its outgoing edge.
                    choices = [node for node, control in surface.controls.items()
                               if control["role"] in {"button", "link"} and not control["disabled"]
                               and not EXCLUDED_WORDS.search(control["label"])
                               and selector(surface, node)]
                    hits = choices[:1]
                descriptor = surface.descriptor(hits[0]) if len(hits) == 1 else None
            else:
                hits, descriptor = [], None
            if len(hits) != 1:
                _stop("No unique learned return path to the entry view")
            old_shape = shape(surface)
            surface = trace.act(browser, surface, Primitive("click", hits[0]))
            edge = {"before": old_shape, "after": shape(surface), "descriptor": descriptor}
            if acquiring and edge not in context["returns"]:
                context["returns"].append(edge)
            elif not acquiring and edge not in context["returns"]:
                _stop("Learned return transition changed", stale=True)
        if shape(surface) != context["entry_shape"]:
            _stop("Return procedure did not reach its observed entry view")
    for step in route:
        surface = act_step(browser, trace, surface, step, arguments)
    return surface


def numeric_probes(surface, node):
    """Finite boundary proposals from rendered numbers, with rises and falls."""
    values = []
    for field in surface.observation.nodes:
        for text in (field.value, field.name):
            if text:
                values.extend(float(value) for value in re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?", text))
    control = surface.controls[node]
    current = surface.observation.node(node).value
    try:
        value = float(current)
    except (TypeError, ValueError):
        return []
    finite = [x for x in values if math.isfinite(x)]
    if not finite:
        return []
    # Boundary crossing is a proposal, never proof of comparison direction.
    probes = [max(finite) + 1, min(finite), value]
    minimum = float(control["min"]) if control.get("min") else -math.inf
    maximum = float(control["max"]) if control.get("max") else math.inf
    return list(dict.fromkeys(format(x, ".12g") for x in probes if minimum <= x <= maximum))


def reload_observed(browser, trace):
    before = trace.read(browser)
    after = trace.reload(browser)
    trace.log.add_step(0, Primitive("reload"), True, None, before.observation, after.observation)
    return after


def acquire(browser, trace, entry, emit, trials, numeric_trials, context):
    """Bounded graph traversal. Observed view changes supply composition edges.

    Supplied search bounds: at most 48 contexts, depth six, at most two visits to
    the same discrete context per route, two initial target exemplars and at least
    the field language's minimum distinct examples for subsequent selectors.
    All replays, failed candidates and fills charge the ordinary Trace budget.
    """
    pending = deque([([], ())])
    seen, queued = set(), set()
    while pending and len(seen) < 48:
        route, ancestors = pending.popleft()
        key = digest(route)
        if key in seen:
            continue
        seen.add(key)
        surface = replay(browser, trace, entry, route, context=context, acquiring=True)
        initial_shape = procedure_context(surface)
        buttons = []
        selector_counts = {}
        from semabi.compiler.runtime import EXCLUDED_WORDS
        for node, control in surface.controls.items():
            if control["role"] not in {"button", "link", "radio"} or control["disabled"] or EXCLUDED_WORDS.search(control["label"]):
                continue
            step = step_for(surface, node, route)
            pattern = route_key([step])
            selector_counts[pattern] = selector_counts.get(pattern, 0) + 1
            from semabi.compiler.v4.fields import MIN_DISTINCT
            if "selector" in step and selector_counts[pattern] > (MIN_DISTINCT if route else 2):
                continue
            buttons.append(step)
        stable_buttons = []
        for step in buttons[:10]:
            surface = replay(browser, trace, entry, route, context=context, acquiring=True)
            node = resolve_step(surface, step)
            before = surface
            after = act_step(browser, trace, before, step)
            trial = {"route": route, "action": step,
                     "before": before.observation.structural_signature(),
                     "after": after.observation.structural_signature(), "node": node}
            trials.append(trial)
            before_context, next_shape = procedure_context(before), procedure_context(after)
            if next_shape == before_context:
                if before.controls[node]["role"] != "radio":
                    stable_buttons.append(step)
            elif len(route) < 6 and (*ancestors, before_context).count(next_shape) < 2:
                new_route = [*route, step]
                candidate = digest(new_route)
                if candidate not in queued:
                    queued.add(candidate)
                    pending.append((new_route, (*ancestors, before_context)))
        if stable_buttons:
            surface = replay(browser, trace, entry, route, context=context, acquiring=True)
            numeric = [(surface.descriptor(node), numeric_probes(surface, node))
                       for node, control in surface.controls.items()
                       if control["role"] == "textbox" and control["input_type"] == "number"
                       and not control["disabled"] and not control["readonly"]]
            for descriptor, probes in numeric[:2]:
                for value in probes:
                    surface = replay(browser, trace, entry, route, context=context, acquiring=True)
                    hits = surface.resolve(descriptor)
                    if len(hits) != 1:
                        continue
                    before = surface
                    surface = trace.act(browser, surface, Primitive("type", hits[0], value))
                    hits = surface.resolve(descriptor)
                    if len(hits) != 1 or surface.observation.node(hits[0]).value != value:
                        emit({"type": "acquisition_rejected_edit", "field": descriptor, "value": value})
                        continue
                    numeric_trials.append({"route": route, "descriptor": descriptor, "value": value,
                                           "before": before.observation.structural_signature(),
                                           "after": surface.observation.structural_signature()})
                    for step in stable_buttons:
                        try:
                            node = resolve_step(surface, step)
                        except Exception:
                            break
                        before = surface
                        surface = trace.act(browser, surface, Primitive("click", node))
                        trials.append({"route": route, "action": step, "node": node,
                                       "before": before.observation.structural_signature(),
                                       "after": surface.observation.structural_signature()})
                        if procedure_context(surface) != initial_shape:
                            break
                    restored = replay(browser, trace, entry, route, context=context, acquiring=True)
                    restored = reload_observed(browser, trace)
                    hits = restored.resolve(descriptor)
                    if len(hits) == 1 and restored.observation.node(hits[0]).value == value:
                        numeric_trials[-1]["persisted"] = restored.observation.structural_signature()
    emit({"type": "acquisition_frontier", "visited_contexts": len(seen), "pending_contexts": len(pending),
          "context_limit": 48, "depth_limit": 6, "bounded_frontier_exhausted": not pending,
          "scope": "Bounded sampled routes; not complete application enumeration"})
    return trials, numeric_trials


def recover_learning(log):
    """Recover observed paths from an interrupted/unpublished onboarding log.

    This reads only recorded browser surfaces and primitives. It supplies no
    target names or procedure steps that were absent from ordinary onboarding.
    """
    surfaces = {}
    for line in (log.dir / "surfaces.jsonl").read_text().splitlines():
        item = json.loads(line)
        sig = item["observation"]
        if sig in log.observations:
            surfaces[sig] = Surface(log.observations[sig],
                                    {int(k): v for k, v in item["controls"].items()}, {},
                                    item.get("settled", True),
                                    {int(k): v for k, v in item.get("text_boundaries", {}).items()})
    if not log.steps or log.steps[0].before not in surfaces:
        return [], [], {}
    context = {"entry_shape": shape(surfaces[log.steps[0].before]), "returns": []}
    entry_context = procedure_context(surfaces[log.steps[0].before])
    trials, edits, route = [], [], []
    for step in log.steps:
        before, after = surfaces.get(step.before), surfaces.get(step.after)
        if before is None or after is None:
            continue
        if procedure_context(before) == entry_context:
            route = []
        if step.action.kind == "click" and step.action.target in before.controls:
            action = step_for(before, step.action.target, route)
            trials.append({"route": deepcopy(route), "action": action, "node": step.action.target,
                           "before": step.before, "after": step.after})
            if re.search(r"\b(back|return|close|cancel)\b", before.controls[step.action.target]["label"], re.I):
                edge = {"before": shape(before), "after": shape(after),
                        "descriptor": before.descriptor(step.action.target)}
                if edge not in context["returns"]:
                    context["returns"].append(edge)
            if procedure_context(before) != procedure_context(after):
                route = [*route, action]
        elif step.action.kind == "type" and step.action.target in before.controls:
            edits.append({"route": deepcopy(route), "descriptor": before.descriptor(step.action.target),
                          "value": step.action.text, "before": step.before, "after": step.after})
        elif step.action.kind == "reload":
            for edit in edits:
                matches = after.resolve(edit["descriptor"])
                if (edit["route"] == route and len(matches) == 1
                        and after.observation.node(matches[0]).value == edit["value"]):
                    edit["persisted"] = step.after
        if procedure_context(after) == entry_context:
            route = []
    return trials, edits, context


def _reuse_training(log, trace):
    for observation in log.observations.values():
        trace.log.add_observation(observation)
    for step in log.steps:
        trace.log.add_step(step.episode, step.action, step.ok, step.error,
                           log.observations[step.before], log.observations[step.after])


def owner_correspondence(group):
    """Unique empirical argument-to-owner wrapper across distinct supported owners.

    Earlier selectors can name prerequisite collections. Equal competing sources
    remain ambiguous; their repeated names are not independent identity evidence.
    """
    if not group or len({trial["owner"]["key"] for trial in group
                         if trial.get("prediction_status") == "supported"}) < 2:
        return None
    candidates = []
    for index, step in enumerate(group[0]["route"]):
        if "selector" not in step:
            continue
        wrappers, values = set(), set()
        for trial in group:
            if index >= len(trial["route"]):
                break
            source = trial["route"][index]
            value = source.get("selector", {}).get("value", "")
            key = trial["owner"]["key"]
            if source.get("argument") != step["argument"] or not key or value.count(key) != 1:
                break
            prefix, suffix = value.split(key)
            wrappers.add((prefix, suffix, trial["owner"]["type"]))
            values.add(value)
        else:
            if len(wrappers) == 1 and len(values) >= 2:
                prefix, suffix, owner_type = wrappers.pop()
                candidates.append({"argument": step["argument"], "prefix": prefix,
                                   "suffix": suffix, "type": owner_type})
    return candidates[0] if len(candidates) == 1 else None


def owner_collection_prefix(procedure):
    """Observed route preceding the argument that supplied the final action owner."""
    argument = procedure["owner_binding"]["argument"]
    matches = [index for index, step in enumerate(procedure["navigation"])
               if "selector" in step and step.get("argument") == argument]
    if len(matches) != 1:
        _stop("Learned owner has no unique collection prefix", stale=True)
    return procedure["navigation"][:matches[0]]


def _argument_value(route, argument):
    values = [step["selector"]["value"] for step in route
              if "selector" in step and step.get("argument") == argument]
    return values[0] if len(values) == 1 else None


def learn(runtime, connection, settings, trace, emit):
    from semabi.compiler.semantic import fit_semantics, training_evidence_digest
    from semabi.compiler.runtime import POLICY_VERSION, bind_contract, source_hashes
    browser = runtime._browser(connection)
    from semabi.compiler.runtime import StopOperation
    trials, edits, context = [], [], {}
    existing = [op for op in settings.get("_semantic_training_operations", settings.get("_existing_operations", []))
                if op.get("kind", "").startswith("semantic_") and op.get("support", {}).get("semantic_artifact")]
    reused = 0
    repair = settings.get("_semantic_repair")
    repair_report = {"execution_id": repair["execution_id"], "status": "NOT_STARTED",
                     "field_write_attempted": False} if repair else None
    repair_witness = None
    # Before any operation has ever been published, these connection traces
    # cannot contain service invocations. Refit prior onboarding after a source
    # repair rather than repeating the same exploratory writes.
    if not existing and not settings.get("_operation_versions"):
        from semabi.compiler.evidence import EvidenceLog
        directories = [p for p in (runtime.data_dir / connection["id"] / "evidence").iterdir()
                       if p != trace.log.dir and (p / "steps.jsonl").exists() and (p / "surfaces.jsonl").exists()]
        for directory in sorted(directories, key=lambda p: (p / "steps.jsonl").stat().st_mtime, reverse=True):
            old = EvidenceLog(directory)
            recovered, recovered_edits, recovered_context = recover_learning(old)
            if not recovered:
                continue
            _reuse_training(old, trace)
            trials, edits, context, reused = recovered, recovered_edits, recovered_context, len(old.steps)
            break
    if existing:
        from semabi.compiler.evidence import EvidenceLog
        previous = max(existing, key=lambda op: op["version"])
        revision = previous["support"]["semantic_artifact"]["metadata"]["representation_revision"]
        compatible = [op for op in existing if op["support"]["semantic_artifact"]["metadata"]["representation_revision"] == revision]
        inherited_trials = {digest(trial): trial for op in compatible for trial in op["support"]["trials"]}
        needed = {trial[side] for trial in inherited_trials.values() for side in ("before", "after")}
        transitions = {(trial["before"], trial["after"], trial["action"]["kind"], trial["node"],
                        trial["action"].get("text")) for trial in inherited_trials.values()}
        metadata = previous["support"]["semantic_artifact"]["metadata"]
        reference = metadata.get("training_evidence")
        candidates = {}
        for directory in sorted((runtime.data_dir / connection["id"] / "evidence").iterdir(), reverse=True):
            if directory == trace.log.dir or not (directory / "steps.jsonl").exists():
                continue
            if reference and directory.name != reference.get("directory"):
                continue
            old = EvidenceLog(directory)
            observed = {(step.before, step.after, step.action.kind, step.action.target,
                         step.action.text) for step in old.steps}
            if (needed and needed <= old.observations.keys() and transitions <= observed
                    and len(old.steps) == metadata["fitted_steps"]):
                evidence_digest = training_evidence_digest(old)
                if reference and evidence_digest != reference.get("digest"):
                    continue
                candidates.setdefault(evidence_digest, old)
        # Legacy artifacts lack an exact training reference. Identical retained
        # copies are interchangeable; distinct matching histories are not.
        if len(candidates) == 1:
            old = next(iter(candidates.values()))
            _reuse_training(old, trace)
            reused = len(old.steps)
            trials = list(inherited_trials.values())
            edits = list({digest(edit): edit for op in compatible for edit in op["support"].get("edits", [])}.values())
            context = deepcopy(previous["procedure"]["return_context"])
        else:
            emit({"type": "semantic_training_unavailable", "matching_histories": len(candidates),
                  "reason": "Prior raw training is absent, changed, or not uniquely identified"})
    try:
        if reused:
            emit({"type": "semantic_evidence_reused", "steps": reused, "scope": "same connection's prior onboarding"})
            if repair:
                repair_witness = acquire_repair(runtime, browser, trace, repair, trials, edits, repair_report)
            # Authorized repair acquires missing persistence witnesses. It does
            # not replay customer invocations or treat a cached prediction as data.
            selected = {}
            for edit in edits if not repair else []:
                if not edit.get("persisted") and edit["route"] and "selector" in edit["route"][0]:
                    selected.setdefault((route_key(edit["route"]), edit["descriptor"]["label"],
                                         edit["route"][0]["selector"]["value"]), []).append(edit)
            for proposals in list(selected.values())[:4]:
                for proposal in proposals[:2]:
                    route = proposal["route"]
                    surface = replay(browser, trace, connection["url"], route, context=context, acquiring=True)
                    hits = surface.resolve(proposal["descriptor"])
                    if len(hits) != 1:
                        continue
                    before = surface
                    surface = trace.act(browser, surface, Primitive("type", hits[0], proposal["value"]))
                    edit = {**proposal, "before": before.observation.structural_signature(),
                            "after": surface.observation.structural_signature()}
                    restored = replay(browser, trace, connection["url"], route, context=context, acquiring=True)
                    restored = reload_observed(browser, trace)
                    hits = restored.resolve(proposal["descriptor"])
                    if len(hits) == 1 and restored.observation.node(hits[0]).value == proposal["value"]:
                        edit["persisted"] = restored.observation.structural_signature()
                        edits.append(edit)
        elif not repair:
            acquire(browser, trace, connection["url"], emit, trials, edits, context)
        else:
            repair_report.update(status="TRAINING_UNAVAILABLE",
                                 reason="Exact prior raw training is required before targeted repair")
    except StopOperation as error:
        emit({"type": "acquisition_stopped", "reason": str(error)})
        if repair_report is not None:
            repair_report.update(status="UNCERTAIN" if trace.possible_effect else "STOPPED",
                                 reason=str(error))
    (trace.log.dir / "learning.json").write_text(json.dumps({"trials": trials, "edits": edits, "context": context}))
    if not trials:
        return {"status": "UNESTABLISHED", "operations": [], "attempts": [],
                "metrics": trace.metrics(), "invalidations": [], "repair": repair_report}
    emit({"type": "semantic_fit_started", "steps": len(trace.log.steps)})
    artifact = fit_semantics(trace.log.dir)
    if repair_witness is not None:
        old_artifact, before, after, node = repair_witness
        repair_report["predictive_change"] = artifact.acquisition_change(old_artifact, before, after, node)
        emit({"type": "semantic_repair_refitted", **repair_report})
    frozen = artifact.to_json()
    (trace.log.dir / "semantic.json").write_text(json.dumps(frozen))
    emit({"type": "semantic_fit_completed", "controls": len(artifact.operations())})
    if source_hashes() != runtime.source_sha256:
        _stop("Source changed during learning; evidence retained, restart and refit before publication")
    operations = []
    for learned in artifact.operations():
        if not learned["comparison"]:
            continue
        control = learned["control"]
        matches = []
        for trial in trials:
            obs = trace.log.observations[trial["before"]]
            prediction = artifact.predict(obs, trial["node"])
            if (prediction.get("control") == control and prediction.get("owner")
                    and prediction["owner"].get("identity") == "learned_key"):
                trial = {**trial, "owner": prediction["owner"], "prediction_status": prediction["status"]}
                matches.append(trial)
        groups = {}
        for trial in matches:
            groups.setdefault(route_key([*trial["route"], trial["action"]]), []).append(trial)
        for group in groups.values():
            route = group[0]["route"]
            selectors = [step for step in route if "selector" in step]
            owner_binding = owner_correspondence(group)
            if owner_binding is None:
                continue
            response_owners, response_paths = {}, {}
            for trial in group:
                # This slice learns a response while its action owner remains
                # observable. Navigational completion needs a different learned
                # correspondence; an anonymous response alone cannot supply it.
                post = artifact.candidates(trace.log.observations[trial["after"]], control)
                if (len(post) != 1 or not post[0].get("owner")
                        or any(post[0]["owner"].get(key) != trial["owner"].get(key)
                               for key in ("type", "key", "identity"))):
                    continue
                observed = artifact.observe(trace.log.observations[trial["before"]],
                                            trace.log.observations[trial["after"]], control)
                event = observed.get("event")
                if event and event.get("path") is not None and event["frame"] in learned["outcomes"]:
                    path_key = digest(event["path"])
                    response_owners.setdefault(path_key, set()).add(trial["owner"]["key"])
                    response_paths[path_key] = event["path"]
            supported_paths = [response_paths[key] for key, owners in response_owners.items() if len(owners) >= 2]
            if not supported_paths:
                continue
            procedure = {"entry_url": connection["url"], "navigation": route, "return_context": context,
                         "action": group[0]["action"], "control": control, "owner_binding": owner_binding}
            props = {step["argument"]: {"type": "string", "minLength": 1,
                     "description": "Exact observed anchor in one uniquely resolved local collection row"}
                     for step in selectors}
            schema = {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
            op_id = "op_" + digest([procedure["entry_url"], control, route_key(route)])[:20]
            operation = {"id": op_id, "version": settings.get("_operation_versions", {}).get(op_id, 0) + 1,
                         "name": argument_name(control), "kind": "semantic_action", "status": "ACTIVE",
                         "argument_schema": schema,
                         "output_schema": {"type": "object", "description": "Learned prediction, raw response, observed effect and attribution limits"},
                         "procedure": procedure,
                         "prerequisites": ["Unique scoped argument resolution", "Live V4 owner and relation bindings",
                                           "Observed sequence and unchanged control descriptors"],
                         "effect_checks": ["Fresh live region change after the selected action",
                                           "Learned action owner remains uniquely observable after the action",
                                           "Response checked separately from the learned prediction"],
                         "scope": {"origin": browser.allowed_origin, "identity": "Local observed-anchor selector; V4 owner re-resolved per view",
                                   "procedure_language": "Observed finite sequence of scoped clicks",
                                   "unsupported": ["Global uniqueness", "Exactly-once effects", "Exclusive causal attribution",
                                                   "Complete collections without scope evidence"]},
                         "support": {"policy_version": POLICY_VERSION, "source_sha256": runtime.source_sha256,
                                     "semantic_artifact": frozen, "learned": learned,
                                     "trials": group, "edits": edits, "response_paths": supported_paths}}
            bind_contract(operation)
            operations.append(operation)
            relevant = {}
            for trial in group:
                for field in artifact.relevant_editables(trace.log.observations[trial["before"]], trial["node"]):
                    if field["owner"]["type"] == owner_binding["type"]:
                        relevant[(field["descriptor"]["label"], field["slot"])] = field
            for (label, slot), field in relevant.items():
                persisted = [edit for edit in edits if edit.get("persisted")
                             and route_key(edit["route"]) == route_key(route)
                             and edit["descriptor"]["label"] == label]
                if (len({_argument_value(edit["route"], owner_binding["argument"]) for edit in persisted}
                        - {None}) < 2
                        or len({edit["value"] for edit in persisted}) < 2):
                    continue
                guarded = deepcopy(operation)
                guarded_id = "op_" + digest([op_id, slot, "guarded_update"])[:20]
                guarded.update(id=guarded_id, version=settings.get("_operation_versions", {}).get(guarded_id, 0) + 1,
                               kind="semantic_guarded_update", name=operation["name"] + "_set_if")
                guarded["procedure"]["guarded_field"] = {"descriptor": persisted[0]["descriptor"], "slot": slot}
                guarded["argument_schema"]["properties"].update({
                    "value": {"type": "string", "description": "New value of " + label},
                    "expect": {"type": "string", "enum": [event for event in learned["outcomes"] if not event.startswith("\x00")],
                               "description": "Requested response; write only if all supported empirical alternatives agree"}})
                guarded["argument_schema"]["required"] += ["value", "expect"]
                guarded["support"]["persisted_edits"] = persisted
                guarded["scope"]["guard"] = "Caller-requested empirical prediction agreement, not a necessary/sufficient application guarantee"
                guarded["effect_checks"] += ["Requested field bound to intended owner after fill and re-opening",
                                              "Detail persistence witness bracketed by matching rendered entry inventories",
                                              "Observed sibling rows unchanged; no simultaneous global-state guarantee"]
                bind_contract(guarded)
                operations.append(guarded)
    return {"status": "COMPLETED" if operations else "UNESTABLISHED", "operations": operations,
            "attempts": [{"semantic_controls": artifact.operations(), "procedure_trials": len(trials)}],
            "metrics": {**trace.metrics(), "reused_training_steps": reused,
                        "fit_seconds": artifact.metadata["fit_seconds"]}, "invalidations": [],
            "repair": repair_report}


def validate(schema, arguments):
    if not isinstance(arguments, dict) or set(arguments) != set(schema["properties"]):
        _stop("Arguments must match the learned schema exactly")
    for name, value in arguments.items():
        prop = schema["properties"][name]
        if not isinstance(value, str) or not value.strip() or value != " ".join(value.split()):
            _stop("Arguments require nonempty normalized text")
        if len(value) > prop.get("maxLength", 10000):
            _stop("Argument exceeds its supported length")
        if prop.get("enum") and value not in prop["enum"]:
            _stop("Argument is outside the learned alternatives")


def _check_owner(prediction, procedure, arguments):
    binding = procedure["owner_binding"]
    selected = arguments[binding["argument"]]
    prefix, suffix = binding["prefix"], binding["suffix"]
    if not selected.startswith(prefix) or not selected.endswith(suffix):
        _stop("Target does not satisfy its learned identity correspondence")
    expected_key = selected[len(prefix):len(selected) - len(suffix) if suffix else None]
    owner = prediction.get("owner") or {}
    if (prediction.get("control") != procedure["control"] or owner.get("key") != expected_key
            or owner.get("type") != binding["type"] or owner.get("identity") != "learned_key"):
        _stop("Learned action owner does not correspond to the selected target", stale=True)


def _inventory(surface):
    obs = surface.observation
    result = {}
    for region in local_regions(obs):
        if region["role"] not in {"article", "row", "listitem"}:
            continue
        nodes = [obs.node(i) for i in obs.subtree(region["root"])]
        anchor = local_anchor(surface, region["root"])
        if anchor is None:
            continue
        positions = {n.i: index for index, n in enumerate(nodes)}
        # A node's own visible text/state does not disappear when it contains
        # a control. Relative containment survives fresh observation indices.
        def control_state(index):
            control = dict(surface.controls.get(index, {}))
            form = control.get("form")
            if form is not None:
                if form in positions:
                    control["form"] = ("within_row", positions[form])
                else:
                    path = [*reversed(obs.ancestors(form)), form]
                    control["form"] = ("outside_row", [
                        (obs.node(i).role, obs.children(obs.node(i).parent).index(i)
                         if obs.node(i).parent >= 0 else 0) for i in path],
                        obs.node(form).key(), surface.forms.get(form))
            return control

        result.setdefault(anchor.name, []).append([
            (positions.get(n.parent, -1), n.key(), control_state(n.i)) for n in nodes])
    return {key: sorted(occurrences, key=digest) for key, occurrences in result.items()}


def _live_signature(surface):
    # Control state such as readonly, bounds and destinations is visible evidence
    # retained beside the node tree; comparing only Node keys drops that evidence.
    return digest([surface.observation.structural_signature(), surface.controls, surface.forms])


def invoke(runtime, browser, operation, arguments, trace):
    from semabi.compiler.semantic import SemanticArtifact
    artifact = SemanticArtifact.from_json(operation["support"]["semantic_artifact"])
    procedure = operation["procedure"]
    # A learned persistent value may be populated. An unrelated editor cannot
    # borrow that support to justify discarding its draft during navigation.
    initial = trace.read(browser)
    allowed = {digest(edit["descriptor"]) for edit in operation["support"].get("edits", [])
               if edit.get("persisted")}
    for index, control in initial.controls.items():
        if (control["role"] == "textbox" and initial.observation.node(index).value
                and not control["readonly"] and control["input_type"] != "search"
                and digest(initial.descriptor(index)) not in allowed):
            _stop("Current editor has a populated field without learned persistence support")
    collection_prefix = owner_collection_prefix(procedure)
    entry = replay(browser, trace, procedure["entry_url"], collection_prefix, arguments,
                   context=procedure["return_context"])
    neighbors = _inventory(entry)
    surface = replay(browser, trace, procedure["entry_url"], procedure["navigation"], arguments,
                     context=procedure["return_context"])
    node = resolve_step(surface, procedure["action"], arguments)
    prediction = artifact.predict(surface.observation, node, procedure["control"])
    # Prediction is disclosed before the writing action; uncertainty is not
    # secretly replaced by a point-model authorization decision.
    trace.emit({"type": "semantic_preflight", "prediction": prediction})
    _check_owner(prediction, procedure, arguments)
    guard = procedure.get("guarded_field")
    counterfactual = None
    if guard:
        matches = surface.resolve(guard["descriptor"])
        if len(matches) != 1:
            _stop("Learned editable field is absent or ambiguous", stale=True)
        if surface.controls[matches[0]]["readonly"] or surface.controls[matches[0]]["disabled"]:
            _stop("Learned editable field is no longer writable", stale=True)
        try:
            number = float(arguments["value"])
        except ValueError:
            _stop("Learned numeric field requires a number")
        if not math.isfinite(number):
            _stop("Learned numeric field requires a finite number")
        counterfactual = artifact.simulate_edit(surface.observation, node, matches[0], arguments["value"])
        proposed = counterfactual.get("prediction", {})
        trace.emit({"type": "semantic_counterfactual", "prediction": counterfactual})
        alternatives = proposed.get("alternatives", {})
        if counterfactual.get("status") != "represented" or proposed.get("status") != "supported":
            return {"outcome": "PREDICTION_UNAVAILABLE", "prediction": counterfactual,
                    "effect": {"field_write_attempted": False, "reason": "No agreed empirical response for requested value"},
                    "metrics": trace.metrics()}
        if set(alternatives) != {arguments["expect"]}:
            return {"outcome": "PREDICTED_REFUSAL", "prediction": counterfactual,
                    "effect": {"field_write_attempted": False, "reason": "Supported response excludes caller's requested response"},
                    "metrics": trace.metrics()}
        _check_owner(proposed, procedure, arguments)
    current = trace.read(browser)
    if _live_signature(current) != _live_signature(surface):
        _stop("Relevant interface state changed during semantic preflight")
    if guard:
        field_node = resolve_step(current, {"descriptor": guard["descriptor"]})
        current = trace.act(browser, current, Primitive("type", field_node, arguments["value"]))
        field_node = resolve_step(current, {"descriptor": guard["descriptor"]})
        if current.observation.node(field_node).value != arguments["value"]:
            _stop("Application did not retain the requested field value")
        node = resolve_step(current, procedure["action"], arguments)
        prediction = artifact.predict(current.observation, node, procedure["control"])
        _check_owner(prediction, procedure, arguments)
        if prediction.get("status") != "supported" or set(prediction.get("alternatives", {})) != {arguments["expect"]}:
            _stop("Related state changed after fill; requested response is no longer supported")
        revalidated = trace.read(browser)
        if _live_signature(revalidated) != _live_signature(current):
            _stop("Related state changed during the final semantic check")
        current = revalidated
    after = trace.act(browser, current, Primitive("click", node))
    post_node = resolve_step(after, procedure["action"], arguments)
    post_prediction = artifact.predict(after.observation, post_node, procedure["control"])
    trace.emit({"type": "semantic_post_action_owner", "prediction": post_prediction})
    _check_owner(post_prediction, procedure, arguments)
    response = artifact.verify_response(current.observation, after.observation, node,
                                        procedure["control"], prediction=prediction)
    event = response.get("event")
    if event is None or event.get("path") not in operation["support"].get("response_paths", []):
        response["verified"] = False
        response["verification_reason"] = "Response source lacks learned correspondence to this action"
    if guard:
        if not response["verified"] or response["event"]["frame"] != arguments["expect"]:
            return {"outcome": "UNCERTAIN", "prediction": prediction, "effect": {
                    "field_write_attempted": True, "response": response, "reason": "Actual response did not confirm requested completion"},
                    "metrics": trace.metrics()}
        entry_after = replay(browser, trace, procedure["entry_url"], collection_prefix, arguments,
                             context=procedure["return_context"])
        remaining = _inventory(entry_after)
        target = arguments[procedure["owner_binding"]["argument"]]
        if not neighbors or {key: val for key, val in neighbors.items() if key != target} != {
                key: val for key, val in remaining.items() if key != target}:
            _stop("Observed neighboring records changed or could not be checked")
        first_inventory = entry_after.observation.structural_signature()
        trace.emit({"type": "semantic_inventory_witness", "phase": "before_detail_check",
                    "observation": first_inventory})
        restored = replay(browser, trace, procedure["entry_url"], procedure["navigation"], arguments,
                          context=procedure["return_context"])
        restored = reload_observed(browser, trace)
        action_node = resolve_step(restored, procedure["action"], arguments)
        restored_prediction = artifact.predict(restored.observation, action_node, procedure["control"])
        _check_owner(restored_prediction, procedure, arguments)
        field_node = resolve_step(restored, {"descriptor": guard["descriptor"]})
        if restored.observation.node(field_node).value != arguments["value"]:
            _stop("Requested target field did not persist through reopening and reload")
        persisted = restored.observation.structural_signature()
        final_entry = replay(browser, trace, procedure["entry_url"], collection_prefix, arguments,
                             context=procedure["return_context"])
        final_inventory = _inventory(final_entry)
        trace.emit({"type": "semantic_inventory_witness", "phase": "after_detail_check",
                    "observation": final_entry.observation.structural_signature(),
                    "detail_observation": persisted})
        if target not in remaining or final_inventory != remaining:
            _stop("Rendered owner-collection inventory changed during persistence verification")
        return {"outcome": "CONFIRMED", "prediction": prediction, "counterfactual": counterfactual,
                "effect": {"kind": "guarded_field_update", "response": response,
                           "target_arguments": arguments, "field": guard, "persisted": persisted,
                           "inventory_bracket": {"before_detail": first_inventory,
                                                 "after_detail": final_entry.observation.structural_signature(),
                                                 "scope": "Matching rendered owner-collection inventories surrounding the detail witness; not complete or simultaneous global state",
                                                 "collection_prefix": collection_prefix},
                           "checked_neighbors": sorted(key for key in neighbors if key != target),
                           "attribution": "Observed requested field effect; concurrent external causes not excluded"},
                "metrics": trace.metrics()}
    return {"outcome": "CONFIRMED" if response.get("verified") else "UNCERTAIN",
            "prediction": prediction, "effect": {"kind": "observed_response", "response": response,
            "target_arguments": arguments, "before": current.observation.structural_signature(),
            "after": after.observation.structural_signature(),
            "attribution": "Observed after action; concurrent external causes not excluded"}, "metrics": trace.metrics()}


def acquire_repair(runtime, browser, trace, repair, trials, edits, report):
    """One task-directed experiment during explicitly authorized learning only.

    The supplied request proposes a value, not its answer. Complete empirical
    outcome alternatives must disagree both on simulation and on the actual
    edited view. All setup, unsuccessful actions and verification use Trace.
    Neither a selected point answer nor the caller's `expect` labels training.
    """
    from semabi.compiler.semantic import SemanticArtifact
    operation, arguments = repair["operation"], repair["arguments"]
    runtime._check_operation(operation)
    validate(operation["argument_schema"], arguments)
    artifact = SemanticArtifact.from_json(operation["support"]["semantic_artifact"])
    procedure = operation["procedure"]
    guard = procedure["guarded_field"]
    allowed = {digest(edit["descriptor"]) for edit in operation["support"].get("edits", [])
               if edit.get("persisted")}
    initial = trace.read(browser)
    for index, control in initial.controls.items():
        if (control["role"] == "textbox" and initial.observation.node(index).value
                and not control["readonly"] and control["input_type"] != "search"
                and digest(initial.descriptor(index)) not in allowed):
            _stop("Repair cannot discard an editor without learned persistence support")
    collection_route = owner_collection_prefix(procedure)
    collection = replay(browser, trace, procedure["entry_url"], collection_route, arguments,
                        context=procedure["return_context"])
    neighbors = _inventory(collection)
    target = arguments[procedure["owner_binding"]["argument"]]
    if not neighbors or target not in neighbors:
        _stop("Repair lacks an observable scoped collection witness for the intended target")
    surface = replay(browser, trace, procedure["entry_url"], procedure["navigation"], arguments,
                     context=procedure["return_context"])
    node = resolve_step(surface, procedure["action"], arguments)
    prediction = artifact.predict(surface.observation, node, procedure["control"])
    _check_owner(prediction, procedure, arguments)
    field = resolve_step(surface, {"descriptor": guard["descriptor"]})
    control = surface.controls[field]
    if control["readonly"] or control["disabled"]:
        _stop("Repair field is not writable")
    try:
        number = float(arguments["value"])
        minimum = float(control["min"]) if control.get("min") else -math.inf
        maximum = float(control["max"]) if control.get("max") else math.inf
    except (TypeError, ValueError):
        _stop("Repair value or visible numeric bounds are not represented")
    if not math.isfinite(number) or not minimum <= number <= maximum:
        _stop("Repair value is outside the observed numeric field bounds")
    opportunity = artifact.acquisition_opportunity(surface.observation, node,
                                                   editable_node=field, value=arguments["value"])
    report["opportunity"] = opportunity
    trace.emit({"type": "semantic_repair_opportunity", **report})
    if not opportunity["eligible"]:
        report.update(status="NOT_ENGAGED", reason=opportunity["kind"])
        return None
    _check_owner(opportunity["prediction"], procedure, arguments)
    current = trace.read(browser)
    if _live_signature(current) != _live_signature(surface):
        _stop("Interface changed before the repair experiment")
    # Check budget before marking the fill as possibly attempted. The actual
    # action's write-intent remains durably emitted by Trace before browser work.
    trace.budget.check_deadline()
    if trace.budget.writes >= trace.budget.max_writes or trace.budget.actions >= trace.budget.max_actions:
        _stop("Repair budget cannot admit the experimental field write")
    report["field_write_attempted"] = True
    filled = trace.act(browser, current, Primitive("type", field, arguments["value"]))
    field = resolve_step(filled, {"descriptor": guard["descriptor"]})
    if filled.observation.node(field).value != arguments["value"]:
        _stop("Repair edit was rejected or changed; no automatic retry")
    node = resolve_step(filled, procedure["action"], arguments)
    actual = artifact.acquisition_opportunity(filled.observation, node)
    report["actual_opportunity"] = actual
    _check_owner(actual["prediction"], procedure, arguments)
    if not actual["eligible"]:
        _stop("The actual edited view does not retain the predicted rival outcomes")
    before = trace.read(browser)
    if _live_signature(before) != _live_signature(filled):
        _stop("Interface changed before the repair response action")
    after = trace.act(browser, before, Primitive("click", node))
    post_node = resolve_step(after, procedure["action"], arguments)
    _check_owner(artifact.predict(after.observation, post_node, procedure["control"]), procedure, arguments)

    def concrete(route):
        route = deepcopy(route)
        for step in route:
            if "selector" in step:
                step["selector"]["value"] = arguments[step["argument"]]
        return route

    route = concrete(procedure["navigation"])
    trials.append({"route": route, "action": concrete([procedure["action"]])[0], "node": node,
                   "before": before.observation.structural_signature(),
                   "after": after.observation.structural_signature()})
    edit = {"route": route, "descriptor": guard["descriptor"], "value": arguments["value"],
            "before": current.observation.structural_signature(), "after": filled.observation.structural_signature()}
    edits.append(edit)
    observed_collection = replay(browser, trace, procedure["entry_url"], collection_route, arguments,
                                 context=procedure["return_context"])
    remaining = _inventory(observed_collection)
    if target not in remaining or {k: v for k, v in neighbors.items() if k != target} != {
            k: v for k, v in remaining.items() if k != target}:
        _stop("Repair changed neighboring observed records or lost its target")
    restored = replay(browser, trace, procedure["entry_url"], procedure["navigation"], arguments,
                      context=procedure["return_context"])
    restored = reload_observed(browser, trace)
    restored_node = resolve_step(restored, procedure["action"], arguments)
    _check_owner(artifact.predict(restored.observation, restored_node, procedure["control"]), procedure, arguments)
    field = resolve_step(restored, {"descriptor": guard["descriptor"]})
    if restored.observation.node(field).value != arguments["value"]:
        _stop("Repair value did not persist on the intended owner")
    final = replay(browser, trace, procedure["entry_url"], collection_route, arguments,
                   context=procedure["return_context"])
    if _inventory(final) != remaining:
        _stop("Scoped inventory changed during repair persistence checking")
    edit["persisted"] = restored.observation.structural_signature()
    report.update(status="OBSERVED_EXPERIMENT", targeting_engaged=True,
                  observation=artifact.observe(before.observation, after.observation, procedure["control"]),
                  persisted=edit["persisted"], inventory_bracket=[
                      observed_collection.observation.structural_signature(), final.observation.structural_signature()],
                  attribution="Observed experiment and persisted field, not exclusive causality or proven rule")
    trace.emit({"type": "semantic_repair_observed", **report})
    return artifact, before.observation, after.observation, node
