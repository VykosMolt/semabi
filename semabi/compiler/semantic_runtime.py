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


def _owned_region_nodes(surface, root):
    obs = surface.observation
    members = set(obs.subtree(root))
    nested = {region["root"] for region in local_regions(obs)
              if region["root"] != root and region["root"] in members}
    excluded = {i for child in nested for i in obs.subtree(child)}
    return [obs.node(i) for i in obs.subtree(root) if i not in excluded]


def local_anchor(surface, root, control_node=None):
    """A unique observed row anchor, not a persistent identity or complete listing.

    Heading anchors also work beside constant controls. Otherwise a leaf's value
    may be repeated by a control label. A lone row-owned control can itself supply
    its full label, but this is only a proposal: publication must constrain what
    labels callers may execute. Descendant rows own their own controls.
    """
    obs = surface.observation
    nodes = _owned_region_nodes(surface, root)
    if control_node is not None and control_node not in {n.i for n in nodes}:
        return None
    headings = [n for n in nodes if n.role == "heading" and n.name]
    if len(headings) == 1:
        return headings[0]
    controls = ([control_node] if control_node is not None else
                [n.i for n in nodes if n.i in surface.controls])
    candidates = [n for n in nodes if n.role in {"cell", "text"} and n.name
                  and not obs.children(n.i) and n.i not in surface.controls
                  and any(surface.controls[i]["label"].count(n.name) == 1 for i in controls)]
    if candidates:
        return candidates[0] if len(candidates) == 1 else None
    own_controls = [n for n in nodes if n.i in surface.controls]
    if (len(own_controls) == 1 and own_controls[0].role in {"button", "link", "radio"}
            and own_controls[0].name and
            (control_node is None or own_controls[0].i == control_node)):
        return own_controls[0]
    return None


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
        spec = {"descriptor": descriptor, "region_role": obs.node(root).role,
                "anchor_role": anchor.role, "value": value}
        if anchor.i in surface.controls:
            spec["full_control_label"] = True
        return spec
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
                 sum(n.role == spec["anchor_role"] and n.name == value
                     for n in (_owned_region_nodes(surface, region["root"])
                               if spec.get("full_control_label") else
                               [obs.node(i) for i in obs.subtree(region["root"])])) == 1]
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


def _return_context(surface, context):
    return procedure_context(surface) if context.get("return_context_version") == 2 else shape(surface)


def _return_policy(context, blocked):
    """Finite strong policy over observed outcomes, without a fairness assumption.

    A view can hide navigation history: the same button may return to several
    observed contexts. Admit it only when every recorded destination already
    has a strictly shorter policy to entry. Cycles needing a lucky outcome,
    unknown destinations, and blocked controls supply no terminating policy.
    """
    transitions = {}
    for edge in context["returns"]:
        key = (edge["before"], digest(edge["descriptor"]))
        transition = transitions.setdefault(key, {"descriptor": edge["descriptor"], "outcomes": set()})
        transition["outcomes"].add(edge["after"])
    reached, policy = {context["entry_shape"]}, {}
    # Each successful layer adds at least one source context. This bound is
    # independent of how many times an action was recorded during onboarding.
    for rank in range(1, len({before for before, _ in transitions}) + 1):
        layer = {}
        for (before, descriptor), transition in sorted(transitions.items()):
            if before in reached or (before, descriptor) in blocked:
                continue
            if transition["outcomes"] <= reached:
                layer.setdefault(before, {"descriptor": transition["descriptor"], "rank": rank,
                                          "outcomes": sorted(transition["outcomes"])})
        if not layer:
            break
        policy.update(layer)
        reached.update(layer)
    return policy


def _return_choices(surface):
    from semabi.compiler.runtime import EXCLUDED_WORDS
    choices = []
    for node, control in surface.controls.items():
        if (control["role"] not in {"button", "link", "radio"} or control["disabled"]
                or EXCLUDED_WORDS.search(control["label"])):
            continue
        descriptor = surface.descriptor(node)
        if len(surface.resolve(descriptor)) != 1:
            continue
        # English navigation words are only an acquisition ranking prior. A
        # forward choice or unlabeled-purpose commit can also reveal an exit.
        rank = (0 if re.search(r"\b(back|return|close|cancel)\b", control["label"], re.I)
                else 1 if selector(surface, node) else 2)
        choices.append((rank, node, descriptor))
    return sorted(choices, key=lambda choice: choice[:2])


def replay(browser, trace, entry, route, arguments=None, *, context=None, acquiring=False):
    before = trace.read(browser)
    surface = trace.navigate(browser, entry)
    trace.log.add_step(0, Primitive("navigate", text=entry), True, None,
                       before.observation, surface.observation)
    if context is not None:
        if "entry_shape" not in context:
            context["return_context_version"] = 2
            context["entry_shape"] = procedure_context(surface)
        context.setdefault("returns", [])
        attempted = set()
        # Finite edge exploration, not a retry loop. The ordinary Trace budget
        # also charges every navigation/selection, including unsuccessful exits.
        while _return_context(surface, context) != context["entry_shape"] and len(attempted) < 48:
            old_shape = _return_context(surface, context)
            choice = _return_policy(context, attempted).get(old_shape)
            if choice:
                if (trace.budget.actions + choice["rank"] > trace.budget.max_actions
                        or trace.budget.writes + choice["rank"] > trace.budget.max_writes
                        or choice["rank"] > 48 - len(attempted)):
                    _stop("Insufficient remaining budget for the observed return policy")
                descriptor = choice["descriptor"]
                trace.emit({"type": "semantic_return_choice", "before": old_shape, **choice,
                            "scope": "All observed branches terminate; unseen outcomes are not supported"})
            elif acquiring:
                choices = [(node, descriptor) for _, node, descriptor in _return_choices(surface)
                           if (old_shape, digest(descriptor)) not in attempted]
                if not choices:
                    _stop("No untried observable return edge within the acquired context")
                descriptor = choices[0][1]
            else:
                _stop("No supported return path to the entry view")
            attempted.add((old_shape, digest(descriptor)))
            hits = surface.resolve(descriptor)
            if len(hits) != 1 or surface.controls[hits[0]]["disabled"]:
                # A different already observed path may still be available.
                continue
            surface = trace.act(browser, surface, Primitive("click", hits[0]))
            edge = {"before": old_shape, "after": _return_context(surface, context), "descriptor": descriptor}
            if acquiring and edge not in context["returns"]:
                context["returns"].append(edge)
            elif not acquiring and edge not in context["returns"]:
                _stop("Learned return transition changed", stale=True)
        if _return_context(surface, context) != context["entry_shape"]:
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


def acquisition_priority_context(surface, route):
    """Search priority only, never an assertion of world-state equivalence.

    The most recent scoped target and native selection distinguish identical
    chooser/detail views reached for different arguments. Alternate histories
    remain queued with their full bindings even when this small priority key ties.
    """
    latest = {}
    for step in route:
        if "selector" in step:
            kind = "native_selection" if step.get("postcondition") else "target"
            latest[kind] = step["selector"]
    return digest([surface.observation.structural_signature(), latest])


def _save_learning(trace, trials, edits, context):
    """Replace a small resumable plan; observations/actions remain append-only."""
    path = trace.log.dir / "learning.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"trials": trials, "edits": edits, "context": context}))
    temporary.replace(path)


def _new_frontier(entry):
    return {"version": 1, "entry": entry, "pending": [{"route": [], "ancestors": []}],
            "deferred": [], "completed": [], "queued": [digest([])],
            "completed_routes": {}, "observed_priority": [], "active": None,
            "totals": {"actions": 0, "writes": 0, "jobs": 0}}


def _frontier_report(frontier):
    return {"type": "acquisition_frontier", "visited_contexts": len(frontier["completed"]),
            "pending_contexts": len(frontier["pending"]) + len(frontier["deferred"]) + int(frontier["active"] is not None),
            "deferred_contexts": len(frontier["deferred"]),
            "active_partial_route": deepcopy(frontier["active"]["route"]) if frontier["active"] else None,
            "in_flight": deepcopy(frontier.get("in_flight")),
            "retained_totals": dict(frontier["totals"]),
            "accounting_scope": frontier.get("accounting_scope", "Charged acquisition actions across retained jobs; per-job setup remains in request metrics"),
            "priority": "new rendered observations before retained alternate paths",
            "context_limit": 48, "depth_limit": 6,
            "bounded_frontier_exhausted": not frontier["pending"] and not frontier["deferred"] and frontier["active"] is None,
            "scope": "Bounded sampled routes; not complete application enumeration"}


def _acquisition_buttons(surface, route):
    from semabi.compiler.runtime import EXCLUDED_WORDS
    from semabi.compiler.v4.fields import MIN_DISTINCT
    buttons, counts = [], {}
    for node, control in surface.controls.items():
        if control["role"] not in {"button", "link", "radio"} or control["disabled"] or EXCLUDED_WORDS.search(control["label"]):
            continue
        step = step_for(surface, node, route)
        pattern = route_key([step])
        counts[pattern] = counts.get(pattern, 0) + 1
        if "selector" in step and counts[pattern] > (MIN_DISTINCT if route else 2):
            continue
        buttons.append(step)
    return buttons[:10]


def _acquisition_numeric(surface):
    numeric = [(surface.descriptor(node), numeric_probes(surface, node))
               for node, control in surface.controls.items()
               if control["role"] == "textbox" and control["input_type"] == "number"
               and not control["disabled"] and not control["readonly"]]
    return [{"descriptor": descriptor, "value": value}
            for descriptor, probes in numeric[:2] for value in probes]


def acquire(browser, trace, entry, emit, trials, numeric_trials, context):
    """Bounded graph traversal. Observed view changes supply composition edges.

    Supplied search bounds: at most 48 contexts, depth six, at most two visits to
    the same discrete context per route, two initial target exemplars and at least
    the field language's minimum distinct examples for subsequent selectors.
    All replays, failed candidates and fills charge the ordinary Trace budget.
    """
    frontier = context.setdefault("acquisition_frontier", _new_frontier(entry))
    if frontier.get("version") != 1 or frontier.get("entry") != entry:
        _stop("Acquisition checkpoint version or entry does not match")
    if frontier.get("in_flight"):
        _stop("Acquisition write requires reconciliation before further exploration")
    start_actions, start_writes = trace.budget.actions, trace.budget.writes
    retained = dict(frontier["totals"])

    def checkpoint():
        frontier["totals"] = {"actions": retained["actions"] + trace.budget.actions - start_actions,
                              "writes": retained["writes"] + trace.budget.writes - start_writes,
                              "jobs": retained["jobs"] + 1}
        frontier["evidence"] = {"steps": len(trace.log.steps),
                                "last": trace.log.steps[-1].to_json() if trace.log.steps else None}
        _save_learning(trace, trials, numeric_trials, context)

    def revisit(route):
        checkpoint()  # active route/cursor survives even interruption inside a replay
        return replay(browser, trace, entry, route, context=context, acquiring=True)

    original_act = trace.act

    def fenced_act(browser, surface, primitive, **kwargs):
        # A replay can itself dispatch several writes. Fence the actual primitive,
        # not merely the outer trial, and never turn an uncertain write into a retry.
        trace.budget.check_deadline()
        if (trace.budget.actions >= trace.budget.max_actions
                or trace.budget.writes >= trace.budget.max_writes):
            _stop("Interaction budget exhausted")
        counts = (trace.budget.actions, trace.budget.writes)
        frontier["in_flight"] = {"before": surface.observation.structural_signature(),
                                 "action": primitive.to_json(), "status": "DISPATCH_UNRESOLVED"}
        checkpoint()
        try:
            after = original_act(browser, surface, primitive, **kwargs)
        except BaseException:
            if counts == (trace.budget.actions, trace.budget.writes):
                # Budget/deadline rejection before dispatch is a clean interruption.
                frontier.pop("in_flight", None)
            checkpoint()
            raise
        frontier.pop("in_flight", None)
        checkpoint()
        return after

    trace.act = fenced_act
    try:
        while (frontier["active"] or frontier["pending"] or frontier["deferred"]) and len(frontier["completed"]) < 48:
            if frontier["active"] is None:
                queue = frontier["pending"] if frontier["pending"] else frontier["deferred"]
                frontier["active"] = queue.pop(0)
            active = frontier["active"]
            route, ancestors = active["route"], active["ancestors"]
            key = digest(route)
            if key in frontier["completed"]:
                frontier["active"] = None
                continue
            surface = revisit(route)
            signature = acquisition_priority_context(surface, route)
            if signature not in frontier["observed_priority"]:
                frontier["observed_priority"].append(signature)
            initial_shape = procedure_context(surface)
            if "buttons" not in active:
                active.update(observation=surface.observation.structural_signature(),
                              shape=shape(surface), buttons=_acquisition_buttons(surface, route),
                              button_index=0, stable_buttons=[])
            elif active["shape"] != shape(surface):
                _stop("Acquisition partial route no longer reaches its observed context")
            checkpoint()
            while active["button_index"] < len(active["buttons"]):
                step = active["buttons"][active["button_index"]]
                surface = revisit(route)
                node = resolve_step(surface, step)
                before = surface
                checkpoint()
                after = act_step(browser, trace, before, step)
                trials.append({"route": deepcopy(route), "action": step,
                               "before": before.observation.structural_signature(),
                               "after": after.observation.structural_signature(), "node": node})
                before_context, next_shape = procedure_context(before), procedure_context(after)
                if next_shape == before_context:
                    if before.controls[node]["role"] != "radio":
                        active["stable_buttons"].append(step)
                elif len(route) < 6 and [*ancestors, before_context].count(next_shape) < 2:
                    new_route = [*route, step]
                    candidate = digest(new_route)
                    if candidate not in frontier["queued"]:
                        frontier["queued"].append(candidate)
                        signature = acquisition_priority_context(after, new_route)
                        queue = frontier["pending"] if signature not in frontier["observed_priority"] else frontier["deferred"]
                        if signature not in frontier["observed_priority"]:
                            frontier["observed_priority"].append(signature)
                        queue.append({"route": new_route, "ancestors": [*ancestors, before_context]})
                active["button_index"] += 1
                checkpoint()
            stable_buttons = active["stable_buttons"]
            if "numeric" not in active:
                surface = revisit(route) if stable_buttons else surface
                active.update(numeric=_acquisition_numeric(surface) if stable_buttons else [], numeric_index=0,
                              numeric_observation=surface.observation.structural_signature(), numeric_results=[])
                checkpoint()
            while active["numeric_index"] < len(active["numeric"]):
                proposal = active["numeric"][active["numeric_index"]]
                descriptor, value = proposal["descriptor"], proposal["value"]
                surface = revisit(route)
                hits = surface.resolve(descriptor)
                receipt = {"status": "NO_UNIQUE_CONTROL", "observation": surface.observation.structural_signature()}
                if len(hits) == 1:
                    before = surface
                    edited_node = hits[0]
                    checkpoint()
                    surface = trace.act(browser, surface, Primitive("type", edited_node, value))
                    receipt = {"status": "REJECTED_VALUE", "before": before.observation.structural_signature(),
                               "after": surface.observation.structural_signature(), "node": edited_node}
                    hits = surface.resolve(descriptor)
                    if len(hits) != 1 or surface.observation.node(hits[0]).value != value:
                        emit({"type": "acquisition_rejected_edit", "field": descriptor, "value": value})
                    else:
                        receipt["status"] = "OBSERVED_VALUE"
                        numeric_trials.append({"route": deepcopy(route), "descriptor": descriptor, "value": value,
                                               "before": before.observation.structural_signature(),
                                               "after": surface.observation.structural_signature()})
                        for step in stable_buttons:
                            try:
                                node = resolve_step(surface, step)
                            except Exception:
                                break
                            before = surface
                            checkpoint()
                            surface = trace.act(browser, surface, Primitive("click", node))
                            trials.append({"route": deepcopy(route), "action": step, "node": node,
                                           "before": before.observation.structural_signature(),
                                           "after": surface.observation.structural_signature()})
                            if procedure_context(surface) != initial_shape:
                                break
                        restored = revisit(route)
                        checkpoint()
                        restored = reload_observed(browser, trace)
                        hits = restored.resolve(descriptor)
                        if len(hits) == 1 and restored.observation.node(hits[0]).value == value:
                            numeric_trials[-1]["persisted"] = restored.observation.structural_signature()
                active["numeric_results"].append(receipt)
                active["numeric_index"] += 1
                checkpoint()
            frontier["completed"].append(key)
            frontier["completed_routes"][key] = active
            frontier["active"] = None
            checkpoint()
    finally:
        trace.act = original_act
        checkpoint()
        emit(_frontier_report(frontier))
    return trials, numeric_trials


def _learning_surfaces(log):
    surfaces = {}
    for line in (log.dir / "surfaces.jsonl").read_text().splitlines():
        item = json.loads(line)
        sig = item["observation"]
        if sig in log.observations:
            surfaces[sig] = Surface(log.observations[sig],
                                    {int(k): v for k, v in item["controls"].items()}, {},
                                    item.get("settled", True),
                                    {int(k): v for k, v in item.get("text_boundaries", {}).items()})
    return surfaces


def _validate_learning_trials(log, surfaces, trials):
    observed = {(step.before, step.after, step.action.kind, step.action.target,
                 step.action.text) for step in log.steps if step.ok}
    edges = {}
    for trial in trials:
        before, after = surfaces[trial["before"]], surfaces[trial["after"]]
        step = trial["action"]
        if ((trial["before"], trial["after"], step["kind"], trial["node"], step.get("text")) not in observed
                or resolve_step(before, step) != trial["node"]):
            raise ValueError("Acquisition trial has no matching rendered transition")
        edges.setdefault(digest([*trial["route"], step]), trial)
    for trial in trials:
        for length in range(1, len(trial["route"]) + 1):
            if digest(trial["route"][:length]) not in edges:
                raise ValueError("Acquisition route has no observed prefix")
    return edges


def _validate_frontier(frontier, log, surfaces, trials, edges):
    if frontier["version"] != 1:
        raise ValueError("Unknown acquisition frontier version")
    entries = {step.action.text for step in log.steps if step.action.kind == "navigate"}
    if entries and frontier["entry"] not in entries:
        raise ValueError("Acquisition entry has no navigation evidence")
    if frontier.get("in_flight"):
        fence = frontier["in_flight"]
        if (fence["status"] != "DISPATCH_UNRESOLVED"
                or fence["action"]["target"] not in surfaces[fence["before"]].controls):
            raise ValueError("Acquisition write fence lacks its source observation")
    evidence = frontier["evidence"]
    count = evidence["steps"]
    if not 0 <= count <= len(log.steps) or evidence["last"] != (log.steps[count - 1].to_json() if count else None):
        raise ValueError("Acquisition checkpoint does not match raw history")
    completed = frontier["completed"]
    if len(completed) > 48 or set(completed) != set(frontier["completed_routes"]):
        raise ValueError("Invalid completed acquisition contexts")
    contexts = [*frontier["pending"], *frontier["deferred"], *frontier["completed_routes"].values()]
    if frontier["active"] is not None:
        contexts.append(frontier["active"])
    keys = [digest(item["route"]) for item in contexts]
    if len(keys) != len(set(keys)) or set(keys) != set(frontier["queued"]):
        raise ValueError("Acquisition queues disagree")
    for item in contexts:
        route, ancestors = item["route"], item["ancestors"]
        if len(route) > 6 or len(route) != len(ancestors):
            raise ValueError("Acquisition route exceeds its language bounds")
        if any(ancestors.count(value) > 2 for value in ancestors):
            raise ValueError("Acquisition route exceeds its context visit bound")
        for length in range(1, len(route) + 1):
            if not any(digest([*trial["route"], trial["action"]]) == digest(route[:length])
                       and procedure_context(surfaces[trial["before"]]) == ancestors[length - 1]
                       for trial in trials):
                raise ValueError("Acquisition ancestor lacks observation support")
        if "buttons" in item:
            surface = surfaces[item["observation"]]
            if item["shape"] != shape(surface) or item["buttons"] != _acquisition_buttons(surface, route):
                raise ValueError("Acquisition controls differ from their source observation")
            index = item["button_index"]
            if not 0 <= index <= len(item["buttons"]):
                raise ValueError("Invalid acquisition cursor")
            for step in item["buttons"][:index]:
                if not any(trial["route"] == route and trial["action"] == step for trial in trials):
                    raise ValueError("Completed acquisition action lacks a trial")
            for step in item["stable_buttons"]:
                if step not in item["buttons"][:index] or not any(
                        trial["route"] == route and trial["action"] == step
                        and procedure_context(surfaces[trial["before"]]) == procedure_context(surfaces[trial["after"]])
                        and surfaces[trial["before"]].controls[trial["node"]]["role"] != "radio" for trial in trials):
                    raise ValueError("Stable acquisition action lacks a matching transition")
            if "numeric" in item:
                expected = _acquisition_numeric(surfaces[item["numeric_observation"]]) if item["stable_buttons"] else []
                if item["numeric"] != expected or not 0 <= item["numeric_index"] <= len(expected):
                    raise ValueError("Numeric acquisition plan lacks its observed proposal source")
                if len(item["numeric_results"]) != item["numeric_index"]:
                    raise ValueError("Numeric acquisition progress lacks outcome evidence")
                for proposal, receipt in zip(expected, item["numeric_results"]):
                    descriptor, value = proposal["descriptor"], proposal["value"]
                    if receipt["status"] == "NO_UNIQUE_CONTROL":
                        if len(surfaces[receipt["observation"]].resolve(descriptor)) == 1:
                            raise ValueError("Skipped numeric proposal had a unique observed control")
                    else:
                        before, after = surfaces[receipt["before"]], surfaces[receipt["after"]]
                        if (before.resolve(descriptor) != [receipt["node"]] or not any(
                                step.ok and step.before == receipt["before"] and step.after == receipt["after"]
                                and step.action.kind == "type" and step.action.target == receipt["node"]
                                and step.action.text == value for step in log.steps)):
                            raise ValueError("Numeric proposal lacks its recorded edit")
                        hits = after.resolve(descriptor)
                        observed = len(hits) == 1 and after.observation.node(hits[0]).value == value
                        if receipt["status"] != ("OBSERVED_VALUE" if observed else "REJECTED_VALUE"):
                            raise ValueError("Numeric proposal outcome differs from its observation")
                if digest(route) in completed and item["numeric_index"] != len(expected):
                    raise ValueError("Completed context has unfinished field probes")
            if digest(route) in completed and index != len(item["buttons"]):
                raise ValueError("Completed context has unfinished actions")
        elif digest(route) in completed:
            raise ValueError("Completed context lacks its observation")
    if any(not isinstance(frontier["totals"][key], int) or frontier["totals"][key] < 0
           for key in ("actions", "writes", "jobs")):
        raise ValueError("Invalid retained acquisition accounting")


def _legacy_frontier(log, surfaces, trials, edits, context, edges):
    """Only saved acquisition trials establish traversal progress, not replay clicks."""
    entries = {step.action.text for step in log.steps if step.action.kind == "navigate"}
    failed = [step for step in log.steps if not step.ok and step.action.kind not in {"navigate", "reload"}]
    if len(entries) != 1 or (not trials and not failed):
        return None
    frontier = _new_frontier(next(iter(entries)))
    last = digest(trials[-1]["route"]) if trials else digest([])
    candidates = {digest([]): {"route": [], "ancestors": []}}
    for trial in trials:
        before, after = surfaces[trial["before"]], surfaces[trial["after"]]
        route = trial["route"]
        ancestors = [procedure_context(surfaces[edges[digest(route[:i])]["before"]])
                     for i in range(1, len(route) + 1)]
        candidates.setdefault(digest(route), {"route": route, "ancestors": ancestors})
        priority = acquisition_priority_context(before, route)
        if priority not in frontier["observed_priority"]:
            frontier["observed_priority"].append(priority)
        if (procedure_context(before) != procedure_context(after) and len(route) < 6
                and [*ancestors, procedure_context(before)].count(procedure_context(after)) < 2):
            child = [*route, trial["action"]]
            priority = acquisition_priority_context(after, child)
            candidates.setdefault(digest(child), {"route": child, "ancestors": [*ancestors, procedure_context(before)],
                                                  "deferred": priority in frontier["observed_priority"]})
            if priority not in frontier["observed_priority"]:
                frontier["observed_priority"].append(priority)
    frontier["pending"] = []
    for key, item in candidates.items():
        deferred = item.pop("deferred", False)
        group = [trial for trial in trials if trial["route"] == item["route"]]
        if group and key != last:
            surface = surfaces[group[0]["before"]]
            buttons = _acquisition_buttons(surface, item["route"])
            has_numeric = any(control["input_type"] == "number" for control in surface.controls.values())
            if not has_numeric and all(any(trial["action"] == step for trial in group) for step in buttons):
                item.update(observation=group[0]["before"], shape=shape(surface), buttons=buttons,
                            button_index=len(buttons), stable_buttons=[], numeric=[], numeric_index=0,
                            numeric_observation=group[0]["before"], numeric_results=[])
                frontier["completed"].append(key)
                frontier["completed_routes"][key] = item
                continue
        if key == last:
            frontier["active"] = item  # no reliable legacy cursor: redo only this partial route
        else:
            frontier["deferred" if deferred else "pending"].append(item)
    frontier["queued"] = list(candidates)
    frontier["totals"] = {"actions": len(log.steps), "writes": sum(step.action.kind not in {"navigate", "reload"} for step in log.steps), "jobs": 1}
    frontier["accounting_scope"] = "Legacy totals count recorded actions; unrecorded interrupted attempts are unknown"
    if failed:
        step = failed[-1]
        frontier["in_flight"] = {"before": step.before, "action": step.action.to_json(),
                                 "status": "DISPATCH_UNRESOLVED"}
    frontier["evidence"] = {"steps": len(log.steps), "last": log.steps[-1].to_json() if log.steps else None}
    _validate_frontier(frontier, log, surfaces, trials, edges)
    return frontier


def recover_learning(log):
    """Recover observed paths from an interrupted/unpublished onboarding log.

    This reads only recorded browser surfaces and primitives. It supplies no
    target names or procedure steps that were absent from ordinary onboarding.
    """
    from semabi.compiler.runtime import StopOperation
    surfaces = _learning_surfaces(log)
    saved = log.dir / "learning.json"
    recovery_error = None
    if saved.exists():
        try:
            retained = json.loads(saved.read_text())
            trials, edits, context = retained["trials"], retained["edits"], retained["context"]
            edges = _validate_learning_trials(log, surfaces, trials)
            frontier = context.get("acquisition_frontier")
            if frontier is not None:
                _validate_frontier(frontier, log, surfaces, trials, edges)
            else:
                frontier = _legacy_frontier(log, surfaces, trials, edits, context, edges)
                if frontier is not None:
                    context["acquisition_frontier"] = frontier
            return trials, edits, context
        except (KeyError, ValueError, TypeError, IndexError, StopOperation) as error:
            # Invalid plans do not confer completed paths or authorize new writes.
            # Raw evidence below remains usable for source-only fitting.
            recovery_error = str(error)
    if not log.steps or log.steps[0].before not in surfaces:
        return [], [], {}
    context = {"entry_shape": procedure_context(surfaces[log.steps[0].before]), "returns": [],
               "return_context_version": 2}
    if recovery_error is not None:
        context["frontier_recovery"] = {"status": "UNESTABLISHED", "reason": recovery_error,
                                        "scope": "Raw evidence retained for fitting; no exploration plan recovered"}
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
            if step.ok and procedure_context(before) != procedure_context(after):
                edge = {"before": procedure_context(before), "after": procedure_context(after),
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
    if (log.dir / "surfaces.jsonl").exists():
        with (trace.log.dir / "surfaces.jsonl").open("a") as stream:
            stream.write((log.dir / "surfaces.jsonl").read_text())


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


def selector_argument_properties(group, owner_binding):
    """Constrain control-label proposals before any invocation or repair action."""
    properties = {}
    for step in group[0]["route"]:
        if "selector" not in step:
            continue
        argument = step["argument"]
        prop = {"type": "string", "minLength": 1,
                "description": "Exact observed anchor in one uniquely resolved local collection row"}
        if step["selector"].get("full_control_label"):
            prefix, suffix = owner_binding["prefix"], owner_binding["suffix"]
            if argument == owner_binding["argument"] and (prefix or suffix):
                prop.update(pattern="^" + re.escape(prefix).replace(r"\ ", " ") + ".+"
                            + re.escape(suffix).replace(r"\ ", " ") + "$",
                            minLength=len(prefix) + len(suffix) + 1,
                            description="Full observed control label, constrained by its learned owner correspondence")
            else:
                prop.update(enum=sorted({_argument_value(trial["route"], argument) for trial in group}
                                        - {None}),
                            description="Full observed control label; only choices observed in supporting trials")
        properties[argument] = prop
    return properties


def learn(runtime, connection, settings, trace, emit):
    from semabi.compiler.semantic import fit_semantics, training_evidence_digest
    from semabi.compiler.runtime import source_hashes
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
            if not recovered and not recovered_context.get("acquisition_frontier"):
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
            elif not existing and context.get("acquisition_frontier"):
                emit({"type": "semantic_acquisition_resumed", "reason": "Retained unpublished traversal has a frontier"})
                acquire(browser, trace, connection["url"], emit, trials, edits, context)
            # Authorized repair acquires missing persistence witnesses. It does
            # not replay customer invocations or treat a cached prediction as data.
            selected = {}
            for edit in edits if not repair and not context.get("acquisition_frontier") else []:
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
    _save_learning(trace, trials, edits, context)
    if not trials:
        return {"status": "UNESTABLISHED", "operations": [], "attempts": [],
                "metrics": trace.metrics(), "invalidations": [], "repair": repair_report}
    emit({"type": "semantic_fit_started", "steps": len(trace.log.steps), "fit_pass": 1})
    artifact = fit_semantics(trace.log.dir)
    fit_seconds = artifact.metadata["fit_seconds"]
    frozen = artifact.to_json()
    emit({"type": "semantic_fit_completed", "controls": len(artifact.operations()), "fit_pass": 1})
    if source_hashes() != runtime.source_sha256:
        _stop("Source changed during learning; evidence retained, restart and refit before publication")
    publication = []
    operations = publish_operations(runtime, browser, connection, settings, trace, artifact,
                                    frozen, trials, edits, context, publication)
    attempts = [{"semantic_controls": artifact.operations(), "procedure_trials": len(trials), "fit_pass": 1,
                 "publication": publication}]
    if repair_witness is not None:
        old_artifact, before, after, node = repair_witness
        repair_report["predictive_change"] = artifact.acquisition_change(old_artifact, before, after, node)
        emit({"type": "semantic_repair_refitted", **repair_report})
    (trace.log.dir / "semantic.json").write_text(json.dumps(frozen))
    return {"status": "COMPLETED" if operations else "UNESTABLISHED", "operations": operations,
            "attempts": attempts,
            "metrics": {**trace.metrics(), "reused_training_steps": reused,
                        "fit_seconds": fit_seconds, "fit_passes": len(attempts),
                        "acquisition": _frontier_report(context["acquisition_frontier"]) if context.get("acquisition_frontier") else None},
            "invalidations": [], "repair": repair_report}


def publish_operations(runtime, browser, connection, settings, trace, artifact, frozen, trials, edits, context,
                       diagnostics=None):
    """Publish only observed procedures with shared learned semantic support."""
    from semabi.compiler.runtime import POLICY_VERSION, bind_contract
    operations = []
    diagnostics = [] if diagnostics is None else diagnostics
    for learned in artifact.operations():
        if not learned["comparison"]:
            diagnostics.append({"control": learned["control"], "status": "UNESTABLISHED",
                                "stage": "language", "reason": "Current semantic publication requires a learned comparison"})
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
        if not matches:
            diagnostics.append({"control": control, "status": "UNESTABLISHED", "stage": "binding",
                                "reason": "No observed procedure trial resolves this control to a learned-key owner",
                                "examined_trials": len(trials)})
        groups = {}
        for trial in matches:
            groups.setdefault(route_key([*trial["route"], trial["action"]]), []).append(trial)
        for group in groups.values():
            route = group[0]["route"]
            selectors = [step for step in route if "selector" in step]
            diagnostic = {"control": control, "route": digest(route_key(route)), "trials": len(group),
                          "status": "UNESTABLISHED"}
            diagnostics.append(diagnostic)
            owner_binding = owner_correspondence(group)
            if owner_binding is None:
                diagnostic.update(stage="binding", reason="No supported route-argument to action-owner correspondence")
                continue
            response_owners, response_paths = {}, {}
            retained_owner_trials, recognized_response_trials = 0, 0
            for trial in group:
                # This slice learns a response while its action owner remains
                # observable. Navigational completion needs a different learned
                # correspondence; an anonymous response alone cannot supply it.
                post = artifact.candidates(trace.log.observations[trial["after"]], control)
                if (len(post) != 1 or not post[0].get("owner")
                        or any(post[0]["owner"].get(key) != trial["owner"].get(key)
                               for key in ("type", "key", "identity"))):
                    continue
                retained_owner_trials += 1
                observed = artifact.observe(trace.log.observations[trial["before"]],
                                            trace.log.observations[trial["after"]], control)
                event = observed.get("event")
                if event and event.get("path") is not None and event["frame"] in learned["outcomes"]:
                    recognized_response_trials += 1
                    path_key = digest(event["path"])
                    response_owners.setdefault(path_key, set()).add(trial["owner"]["key"])
                    response_paths[path_key] = event["path"]
            supported_paths = [response_paths[key] for key, owners in response_owners.items() if len(owners) >= 2]
            diagnostic.update(retained_owner_trials=retained_owner_trials,
                              recognized_response_trials=recognized_response_trials,
                              response_path_owner_counts=sorted(len(owners) for owners in response_owners.values()))
            if not supported_paths:
                diagnostic.update(stage="confirmation",
                                  reason="No recognized response path with the intended owner retained on two distinct owners")
                continue
            procedure = {"entry_url": connection["url"], "navigation": route, "return_context": context,
                         "action": group[0]["action"], "control": control, "owner_binding": owner_binding}
            props = selector_argument_properties(group, owner_binding)
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
            diagnostic.update(status="PUBLISHED", stage="publication", operation_id=op_id, guarded_fields=[])
            relevant = {}
            for trial in group:
                for field in artifact.relevant_editables(trace.log.observations[trial["before"]], trial["node"]):
                    if field["owner"]["type"] == owner_binding["type"]:
                        relevant[(field["descriptor"]["label"], field["slot"])] = field
            for (label, slot), field in relevant.items():
                persisted = [edit for edit in edits if edit.get("persisted")
                             and route_key(edit["route"]) == route_key(route)
                             and edit["descriptor"]["label"] == label]
                owners = len({_argument_value(edit["route"], owner_binding["argument"]) for edit in persisted} - {None})
                values = len({edit["value"] for edit in persisted})
                field_diagnostic = {"slot": slot, "persisted_owners": owners, "persisted_values": values,
                                    "status": "UNESTABLISHED"}
                diagnostic["guarded_fields"].append(field_diagnostic)
                if owners < 2 or values < 2:
                    field_diagnostic["reason"] = "Guarded editing requires persisted edits on two owners and two values"
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
                guarded["effect_checks"] += ["Requested field and empirical condition on intended owner after terminal reopening and reload",
                                              "Detail persistence witness bracketed by matching rendered entry inventories",
                                              "Observed sibling rows unchanged before terminal target verification; no simultaneous global-state guarantee"]
                bind_contract(guarded)
                operations.append(guarded)
                field_diagnostic.update(status="PUBLISHED", operation_id=guarded_id)
    return operations


def validate(schema, arguments):
    if not isinstance(arguments, dict) or set(arguments) != set(schema["properties"]):
        _stop("Arguments must match the learned schema exactly")
    for name, value in arguments.items():
        prop = schema["properties"][name]
        if not isinstance(value, str) or not value.strip() or value != " ".join(value.split()):
            _stop("Arguments require nonempty normalized text")
        if len(value) > prop.get("maxLength", 10000):
            _stop("Argument exceeds its supported length")
        if len(value) < prop.get("minLength", 1):
            _stop("Argument is shorter than its learned anchor constraint")
        if prop.get("pattern") and re.fullmatch(prop["pattern"], value) is None:
            _stop("Argument does not satisfy its learned control-label constraint")
        if "enum" in prop and value not in prop["enum"]:
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
    anchors = {region["root"]: anchor for region in local_regions(obs)
               if region["role"] in {"article", "row", "listitem"}
               and (anchor := local_anchor(surface, region["root"])) is not None}
    for root, anchor in anchors.items():
        members = set(obs.subtree(root))
        # Nested anchored rows have their own inventory entries. Keep the parent's
        # own state and intermediate groups; do not double-count its children's
        # changes as a collateral effect on the parent. Unanchored content stays.
        excluded = {i for child in anchors if child != root and child in members for i in obs.subtree(child)}
        nodes = [obs.node(i) for i in obs.subtree(root) if i not in excluded]
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


def _terminal_guarded_witness(browser, trace, artifact, procedure, arguments, *, expected_response=None):
    """Finish on a freshly reloaded target, never act after the final witness.

    Returning to a collection can change a field absent from its rows; opening
    details can restore a stale draft. Neither preserves an earlier persistence
    witness. Neighbor observations remain explicitly earlier, not simultaneous.
    """
    restored = replay(browser, trace, procedure["entry_url"], procedure["navigation"], arguments,
                      context=procedure["return_context"])
    restored = reload_observed(browser, trace)
    action_node = resolve_step(restored, procedure["action"], arguments)
    prediction = artifact.predict(restored.observation, action_node, procedure["control"])
    _check_owner(prediction, procedure, arguments)
    field_node = resolve_step(restored, {"descriptor": procedure["guarded_field"]["descriptor"]})
    if restored.observation.node(field_node).value != arguments["value"]:
        _stop("Requested target field did not persist through terminal reopening and reload", stale=True)
    if expected_response is not None and (prediction.get("status") != "supported"
            or set(prediction.get("alternatives", {})) != {expected_response}):
        _stop("Learned condition no longer agrees with the requested response at terminal verification")
    final = trace.read(browser)
    if _live_signature(final) != _live_signature(restored):
        _stop("Relevant interface state changed during terminal target verification")
    witness = final.observation.structural_signature()
    trace.emit({"type": "semantic_terminal_target_witness", "observation": witness,
                "prediction": prediction, "scope": "Reloaded target after the last procedure action"})
    return witness


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
        # The supplied guarded wrapper has a finite mandatory tail: fill/check,
        # two collection replays, two detail replays, and two reloads. Refuse a
        # knowingly unaffordable write; additional learned return edges still
        # consume the ordinary budget and are not promised by this lower bound.
        route_actions = 2 * (len(collection_prefix) + len(procedure["navigation"]))
        if (trace.budget.actions + 8 + route_actions > trace.budget.max_actions
                or trace.budget.writes + 2 + route_actions > trace.budget.max_writes):
            _stop("Remaining interaction budget cannot cover the mandatory guarded verification procedure")
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
            _stop("Requested target field did not persist through reopening and reload", stale=True)
        persisted = restored.observation.structural_signature()
        final_entry = replay(browser, trace, procedure["entry_url"], collection_prefix, arguments,
                             context=procedure["return_context"])
        final_inventory = _inventory(final_entry)
        trace.emit({"type": "semantic_inventory_witness", "phase": "after_detail_check",
                    "observation": final_entry.observation.structural_signature(),
                    "detail_observation": persisted})
        if target not in remaining or final_inventory != remaining:
            _stop("Rendered owner-collection inventory changed during persistence verification")
        terminal = _terminal_guarded_witness(browser, trace, artifact, procedure, arguments,
                                            expected_response=arguments["expect"])
        return {"outcome": "CONFIRMED", "prediction": prediction, "counterfactual": counterfactual,
                "effect": {"kind": "guarded_field_update", "response": response,
                           "target_arguments": arguments, "field": guard, "persisted": terminal,
                           "inventory_bracket": {"before_detail": first_inventory,
                                                 "detail": persisted,
                                                 "after_detail": final_entry.observation.structural_signature(),
                                                 "scope": "Matching rendered owner-collection inventories surrounding an earlier detail witness, before terminal target verification; not complete or simultaneous global state",
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
    report["targeting_attempted"] = True
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
    report["targeting_engaged"] = True
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
    edit["persisted"] = _terminal_guarded_witness(browser, trace, artifact, procedure, arguments)
    report.update(status="OBSERVED_EXPERIMENT", targeting_engaged=True,
                  observation=artifact.observe(before.observation, after.observation, procedure["control"]),
                  persisted=edit["persisted"], inventory_bracket=[
                      observed_collection.observation.structural_signature(), final.observation.structural_signature()],
                  attribution="Observed experiment and persisted field, not exclusive causality or proven rule")
    trace.emit({"type": "semantic_repair_observed", **report})
    return artifact, before.observation, after.observation, node
