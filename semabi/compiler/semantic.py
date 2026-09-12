"""Persisted V4 semantics shared by onboarding and live operation execution.

The artifact freezes the learned observation model and outcome language. Loading it
does not search, learn from a customer page, or use process-global outcome state.
Predictions describe empirical alternatives; they are not authorization to act.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import fields, is_dataclass
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from types import SimpleNamespace

from semabi.compiler.abstract import SlotInfo, TypeInfo
from semabi.compiler.browser import Primitive
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.induce import Inducer
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.controls import ControlDescriptor, ControlFamily, ControlFamilies
from semabi.compiler.v2.graph import NodeDesc, ObsGraph, TextTemplate
from semabi.compiler.v2.hypotheses import EntityType, Hypotheses, SlotStat, UnitHyp, UnitInstance
from semabi.compiler.v2.units import UnitType
from semabi.compiler.v2 import sections
from semabi.compiler.v4 import consequence, emission, outcome
from semabi.compiler.v4.abstractor import V4Abstractor

VERSION = 1
FIT_INPUT_FILES = ("observations.jsonl", "steps.jsonl", "probes.jsonl",
                   "probes.acquired.jsonl", "field_theories_v4.json")
FIT_RECIPE = {"version": 1, "reading": None, "min_support": 2,
              "regime": consequence.FROZEN_PREFIX, "read_outputs": True,
              "permute_outcomes": None, "subject_restricted": False,
              "cut": "all_recorded_steps"}


def fit_source_hashes(root: Path | None = None) -> dict:
    """Conservative loaded fitting/serialization boundary, not workflow policy.

    Keep whole shared files, including inference used after deserialization. Only
    these four browser workflow modules are outside the ordinary fitting closure.
    A change in a caller that starts using them invalidates its own shared hash.
    """
    root = Path(__file__).parent if root is None else Path(root)
    excluded = {"runtime.py", "semantic_runtime.py", "surface.py", "browser_session.py"}
    paths = [path for path in sorted(root.rglob("*.py"))
             if str(path.relative_to(root)) not in excluded]
    paths.append(root.parent / "relmodel.py")
    return {str(path.relative_to(root.parent)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths}


LOADED_FIT_SOURCE = fit_source_hashes()


def capture_fit_inputs(directory: Path) -> dict[str, bytes | None]:
    """Capture all filesystem inputs to the ordinary fit, including absence."""
    captured = {}
    for name in FIT_INPUT_FILES:
        try:
            captured[name] = (Path(directory) / name).read_bytes()
        except FileNotFoundError:
            captured[name] = None
    return captured


def _fit_provenance(captured: dict, recipe: dict) -> dict:
    return {"version": 1, "recipe": deepcopy(recipe),
            "source": dict(LOADED_FIT_SOURCE),
            "inputs": {name: None if raw is None else hashlib.sha256(raw).hexdigest()
                       for name, raw in captured.items()}}


def _check_fit_inputs(directory: Path, captured: dict) -> None:
    if capture_fit_inputs(directory) != captured:
        raise ValueError("Fitting inputs changed; retained observations must be reconciled before publication")
    if fit_source_hashes() != LOADED_FIT_SOURCE:
        raise ValueError("Fitting source changed; restart before fitting or reusing semantics")


def reuse_semantics(run_dir: Path, candidate: dict | None, *, recipe: dict | None = None):
    """Reuse only a newly provenance-bound fit; publication remains a separate step."""
    started = monotonic()
    recipe = FIT_RECIPE if recipe is None else recipe
    captured = capture_fit_inputs(run_dir)
    _check_fit_inputs(run_dir, captured)
    if (not isinstance(candidate, dict) or not isinstance(candidate.get("metadata"), dict)
            or candidate["metadata"].get("fit_provenance")
            != _fit_provenance(captured, recipe)):
        return None
    artifact = SemanticArtifact.from_json(candidate)
    _check_fit_inputs(run_dir, captured)
    # Input equality, not a retroactive source-hash rewrite, supports this new
    # directory reference. Original fitting cost and provenance stay unchanged.
    artifact.metadata = deepcopy(artifact.metadata)
    artifact.metadata["training_evidence"]["directory"] = Path(run_dir).name
    artifact.metadata["fit_reuse_seconds"] = round(monotonic() - started, 6)
    return artifact


_CLASSES = {cls.__name__: cls for cls in (
    SlotInfo, TypeInfo, Node, Observation, ControlDescriptor, ControlFamily,
    ControlFamilies, NodeDesc, TextTemplate, EntityType, SlotStat, UnitHyp,
    UnitInstance, UnitType, outcome.Role, outcome.Alias, outcome.Rule,
)}
_FACTORIES = {"set": set, "list": list, "dict": dict, "Counter": Counter}


def _pack(value):
    """A closed JSON vocabulary; no executable Python deserialization."""
    if value is None or type(value) in (str, int, float, bool):
        return value
    if isinstance(value, defaultdict):
        factory = value.default_factory
        name = next((k for k, v in _FACTORIES.items() if v is factory), None)
        if name is None:
            raise TypeError("unsupported artifact mapping factory")
        return {"$": "defaultdict", "factory": name,
                "items": [[_pack(k), _pack(v)] for k, v in value.items()]}
    if isinstance(value, dict):
        return {"$": "Counter" if isinstance(value, Counter) else "dict",
                "items": [[_pack(k), _pack(v)] for k, v in value.items()]}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = sorted(value, key=repr) if isinstance(value, (set, frozenset)) else value
        return {"$": type(value).__name__, "items": [_pack(v) for v in items]}
    if is_dataclass(value) and type(value).__name__ in _CLASSES:
        return {"$": type(value).__name__, "fields": {
            f.name: _pack(getattr(value, f.name)) for f in fields(value)}}
    raise TypeError(f"unsupported semantic artifact value: {type(value).__name__}")


def _unpack(value):
    if not isinstance(value, dict):
        return value
    kind = value["$"]
    if kind in ("dict", "Counter", "defaultdict"):
        data = {_unpack(k): _unpack(v) for k, v in value["items"]}
        if kind == "defaultdict":
            return defaultdict(_FACTORIES[value["factory"]], data)
        return Counter(data) if kind == "Counter" else data
    if kind in ("list", "tuple", "set", "frozenset"):
        constructor = {"list": list, "tuple": tuple, "set": set, "frozenset": frozenset}[kind]
        return constructor(_unpack(v) for v in value["items"])
    cls = _CLASSES.get(kind)
    if cls is None:
        raise ValueError(f"unknown semantic artifact class: {kind}")
    return cls(**{k: _unpack(v) for k, v in value["fields"].items()})


def _public(value):
    if isinstance(value, dict):
        return {str(k): _public(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_public(v) for v in (sorted(value, key=repr) if isinstance(value, (set, frozenset)) else value)]
    if is_dataclass(value):
        return {f.name: _public(getattr(value, f.name)) for f in fields(value)}
    return value


def _owner_record(owner, state):
    if owner is None:
        return None
    local = owner.positional or owner.id in getattr(state, "provisional", ())
    return {"type": owner.tid, "key": owner.key, "node": owner.node,
            "identity": "observation_local" if local else "learned_key",
            "positional": owner.positional}


class SemanticArtifact:
    def __init__(self, abstractor, outcomes, metadata):
        self.abstractor = abstractor
        self.outcomes = outcomes
        self.metadata = metadata
        # _literals needs only A. Never use outcome.bind_language's process global:
        # two connections can carry incompatible type and field vocabularies.
        self.inducer = Inducer(abstractor, None)

    def prepare(self, obs):
        """Apply fitting's section builder with frozen statistics; indices survive."""
        sig = self.abstractor.ensure(obs)
        return sections.normalise(self.abstractor.G, sig, obs)

    def abstract(self, obs):
        return self.abstractor.abstract(self.prepare(obs))

    def to_json(self):
        A = self.abstractor
        controls = {}
        for name, got in self.outcomes.items():
            state = {k: v for k, v in vars(got).items() if k != "evidence"}
            evidence = got.evidence
            controls[name] = {"model": _pack(state), "evidence": None if evidence is None else {
                "state": _pack({k: v for k, v in vars(evidence).items()
                                if k not in ("refuse", "_blocks")})}}
        return {"version": VERSION, "metadata": self.metadata,
                "graph": _pack(vars(A.G)),
                "hypotheses": _pack({k: v for k, v in vars(A.H).items() if k != "G"}),
                "abstractor": _pack({k: getattr(A, k) for k in (
                    "types", "_controls", "view_controls", "verified_view_controls",
                    "heuristic_view_controls", "verified_domain_controls")}),
                "vocabulary": _pack(A.emissions.values), "outcomes": controls}

    @classmethod
    def from_json(cls, data):
        if data.get("version") != VERSION:
            raise ValueError("unsupported semantic artifact version")
        G = ObsGraph()
        graph_state = _unpack(data["graph"])
        G.__dict__.update(graph_state)
        # Old artifacts retain their learned template partition; only randomized
        # dictionary keys are migrated. New fits persist the revised policy.
        G.response_independent_structure = graph_state.get("response_independent_structure", False)
        G.restore_stable_skeletons()
        H = Hypotheses(G)
        H.__dict__.update(_unpack(data["hypotheses"]))
        A = V4Abstractor(G, H, merge_mentions=True, conservative_belief=True)
        A.__dict__.update(_unpack(data["abstractor"]))
        A.emissions.values = _unpack(data["vocabulary"])
        A.freeze()
        models = {}
        for name, item in data["outcomes"].items():
            got = outcome.ControlOutcome(name)
            got.__dict__.update(_unpack(item["model"]))
            ev = item["evidence"]
            if ev is not None:
                # Rows already exclude identity-memorizing literals. This artifact is
                # read-only; authorized acquisition refits from the ordinary raw log.
                got.evidence = outcome.Evidence([])
                got.evidence.__dict__.update(_unpack(ev["state"]))
            models[name] = got
        return cls(A, models, dict(data["metadata"]))

    def operations(self):
        result = []
        for control, got in sorted(self.outcomes.items()):
            roles = _public(got.roles)
            empirical = {"rows": got.evidence.rows_for_refit() if got.evidence else [],
                         "default": got.default, "deltas": got.deltas,
                         "arguments": got.arg_roles, "defaults": got.defaults}
            dependencies = {"roles": roles, "ordered": _public(got.ordered),
                            "pairs": _public(got.pairs), "rules": _public(got.rules),
                            "evidence_revision": hashlib.sha256(json.dumps(_pack(empirical), sort_keys=True).encode()).hexdigest()[:16],
                            "representation_revision": self.metadata.get("representation_revision")}
            revision = hashlib.sha256(json.dumps(dependencies, sort_keys=True).encode()).hexdigest()[:16]
            result.append({"control": control, "owner_type": getattr(got.roles.get(outcome.OWNER), "tid", None),
                           "roles": roles, "rules": _public(got.rules),
                           "default": got.default, "outcomes": dict(got.events),
                           "fitted_occasions": got.fitted, "dependencies": dependencies,
                           "revision": revision,
                           "relational": any(getattr(r, "path", False) or getattr(r, "anchor", None)
                                             for r in got.roles.values()),
                           "comparison": any(l[0] in ("attr_cmp_ge", "attr_cmp_lt")
                                             for rule in got.rules for l in rule.condition),
                           "scope": "currently rendered objects; learned identity; no complete-collection claim",
                           "prediction_guarantee": "empirical alternatives in the declared hypothesis language"})
        return result

    def control_at(self, obs, node):
        obs = self.prepare(obs)
        n = obs.node(node)
        step = SimpleNamespace(action=Primitive("click", node, target_desc={"role": n.role, "name": n.name}))
        return consequence.clicked_control(self.abstractor, obs, step)

    def owner_at(self, obs, node):
        """The learned object owning a local occurrence, including its key's raw source.

        The caller can compare this before and after observed navigation. Equal display
        strings alone do not establish that two occurrences denote the same object.
        """
        obs = self.prepare(obs)
        state = self.abstract(obs)
        owner = consequence._owner_object(self.abstractor, self.abstractor.parsed(obs), state, node)
        record = _owner_record(owner, state)
        if record is None:
            return None
        bridge = consequence.slot_nodes(self.abstractor, obs)
        return {**record, "observation": obs.structural_signature(), "queried_node": node,
                "key_source_node": bridge.get((owner.node, "id")),
                "basis": "learned parsed instance ancestry"}

    def relevant_editables(self, obs, control_node):
        """Editable occurrences supplying fields used by this control's learned guards.

        Provenance is the unit parser's slot-to-node map, never equality of displayed
        values. Widget persistence is included as fitted evidence; it does not establish
        that an arbitrary fill procedure commits a write.
        """
        obs = self.prepare(obs)
        got = self.outcomes.get(self.control_at(obs, control_node))
        if got is None:
            return []
        state = self.abstract(obs)
        A = self.abstractor
        po = A.parsed(obs)
        owner = consequence._owner_object(A, po, state, control_node)
        bound, _ = got.bind(state, owner)
        used = set()
        for rule in got.rules:
            for literal in rule.condition:
                if literal[0] in ("attr", "attr_ge", "attr_lt"):
                    used.add((literal[1], literal[2]))
                elif literal[0] in ("attr_cmp_ge", "attr_cmp_lt"):
                    used.update(((literal[1], literal[2]), (literal[3], literal[4])))
        units = A.H.parse_units(A.ensure(obs))
        result = {}
        for role, slot in sorted(used):
            obj = bound.get(role)
            if obj is None or slot not in obj.attrs:
                continue
            roots = {inst.root for inst in po.instances if inst.tid == obj.tid
                     and inst.slots.get("id", (None, None))[1] == obj.key}
            roots.add(obj.node)
            for unit in units:
                if unit.root not in roots:
                    continue
                et_id = A.H.tid_of_template.get(unit.template)
                if et_id is None:
                    continue
                entity = A.H.entity_types[et_id]
                for slot_id in sorted(entity.attr_slots.get(unit.template, ())):
                    if A.attr_name(entity, unit.template, slot_id) != slot:
                        continue
                    field_node = unit.slot_nodes.get(slot_id)
                    if field_node is None or not 0 <= field_node < len(obs.nodes):
                        continue
                    raw = obs.node(field_node)
                    if raw.role != "textbox" or raw.value is None:
                        continue
                    key = (field_node, obj.id, slot)
                    row = result.setdefault(key, {
                        "node": field_node, "descriptor": {"role": raw.role, "label": raw.name},
                        "owner": _owner_record(obj, state), "slot": slot, "roles": [],
                        "value": raw.value, "semantic_value": obj.attrs[slot], "provenance": []})
                    if role not in row["roles"]:
                        row["roles"].append(role)
                    source = {"observation": obs.structural_signature(), "template": unit.template,
                              "slot_id": slot_id, "object_node": unit.root, "field_node": field_node,
                              "persistent_widget": (unit.template, slot_id) in A.H.persistent_widgets,
                              "reload_persistence": (unit.template, slot_id) in A.H._reload_persistent_widgets,
                              "mirror_persistence": (unit.template, slot_id) in A.H._mirror_persistent_widgets}
                    if source not in row["provenance"]:
                        row["provenance"].append(source)
        return sorted(result.values(), key=lambda row: (row["node"], row["slot"]))

    def simulate_edit(self, obs, control_node, editable_node, value):
        """Re-read a hypothetical widget value; never claim the application accepted it."""
        if not isinstance(value, str):
            raise ValueError("simulated textbox values must be strings")
        fields_ = [row for row in self.relevant_editables(obs, control_node)
                   if row["node"] == editable_node]
        if len(fields_) != 1:
            return {"status": "unavailable", "reason": "editable occurrence has no unique learned guard-field binding"}
        field_ = fields_[0]
        before = self.predict(obs, control_node)
        hypothetical = deepcopy(obs)
        hypothetical.node(editable_node).value = value
        after = self.predict(hypothetical, control_node)
        proposed_fields = self.relevant_editables(hypothetical, control_node)
        matching = [row for row in proposed_fields if row["node"] == editable_node
                    and row["slot"] == field_["slot"]
                    and (row["owner"]["type"], row["owner"]["key"]) == (
                        field_["owner"]["type"], field_["owner"]["key"])]
        # A copied widget can be readable without changing the semantic field (for
        # example, a persistent mirrored text remains authoritative until commit).
        represented = len(matching) == 1 and matching[0]["semantic_value"] == value
        return {"status": "represented" if represented else "unavailable",
                "reason": "hypothetical value enters the learned field" if represented else
                          "widget change does not establish the requested semantic field value",
                "field": field_, "value": value, "prediction_before": before,
                "prediction": after, "application_effect": "not executed",
                "owner_preserved": before.get("owner") == after.get("owner")}

    def candidates(self, obs, control):
        obs = self.prepare(obs)
        state = self.abstract(obs)
        po = self.abstractor.parsed(obs)
        result = []
        for n in obs.interactive():
            if self.control_at(obs, n.i) != control:
                continue
            owner = consequence._owner_object(self.abstractor, po, state, n.i)
            result.append({"node": n.i, "name": n.name,
                           "owner": _owner_record(owner, state),
                           "prediction": self.predict(obs, n.i, control)})
        return result

    def acquisition_opportunity(self, obs, node, *, editable_node=None, value=None):
        """Classify a possible question, without authorizing or executing exploration.

        These are the corroborated LIST alternatives under this artifact's
        observation model, not a frontier over every possible ontology.
        """
        if (editable_node is None) != (value is None):
            raise ValueError("an acquisition edit requires both editable_node and value")
        simulation = (self.simulate_edit(obs, node, editable_node, value)
                      if editable_node is not None else None)
        prediction = simulation.get("prediction") if simulation is not None else None
        if prediction is None:
            prediction = self.predict(obs, node)
        alternatives = prediction.get("alternatives", {})
        if simulation is not None and simulation.get("status") != "represented":
            kind = "UNREPRESENTED_INTERVENTION"
        elif prediction.get("control") not in self.outcomes:
            kind = "UNSUPPORTED_CONTROL"
        elif prediction.get("owner") is None:
            kind = "UNBOUND_TARGET"
        elif prediction.get("alternatives_complete") is False:
            kind = "SEARCH_INCOMPLETE"
        elif len(alternatives) > 1:
            kind = "RIVAL_OUTCOMES"
        elif not alternatives:
            kind = "NO_ADMISSIBLE_INTERPRETATION"
        elif prediction.get("status") == "supported":
            kind = "AGREED_OUTCOME"
        else:
            kind = "INSUFFICIENT_CORROBORATION"
        return {"kind": kind, "eligible": kind == "RIVAL_OUTCOMES",
                "outcomes": sorted(alternatives), "prediction": prediction, "simulation": simulation,
                "query": {"observation": obs.structural_signature(), "node": node,
                          "editable_node": editable_node, "value": value},
                "representation_revision": self.metadata.get("representation_revision")}

    def acquisition_change(self, previous, before, after, node, *, question=None, question_node=None):
        """Compare admitted outcomes after ordinary refitting on new raw evidence.

        Both models rebuild the same raw question. A changed short witness is
        not elimination if some conjunction/list still supports that outcome.
        Response recognition is deliberately not an eligibility gate: unfamiliar
        observations remain data for the ordinary fitter.
        """
        question = before if question is None else question
        question_node = node if question_node is None else question_node
        prior = previous.acquisition_opportunity(question, question_node)
        current = self.acquisition_opportunity(question, question_node)
        old, new = set(prior["outcomes"]), set(current["outcomes"])
        searches_complete = (prior["prediction"].get("alternatives_complete", True)
                             and current["prediction"].get("alternatives_complete", True))

        def local_owner(opportunity):
            owner = opportunity["prediction"].get("owner")
            return None if owner is None else (owner.get("node"), owner.get("key"))

        owner_changed = local_owner(prior) != local_owner(current)
        prior_control, current_control = previous.control_at(before, node), self.control_at(before, node)
        observed_before = previous.observe(before, after, prior_control)
        observed_after = self.observe(before, after, current_control)
        old_event, event = observed_before.get("event"), observed_after.get("event")
        old_model = previous.outcomes.get(prior_control)
        same_question = (question.structural_signature() == before.structural_signature()
                         and question_node == node)
        consistent = (event["frame"] in new if event is not None and same_question
                      and current["prediction"].get("alternatives_complete", True) else None)
        question_matches_action = (prior["prediction"].get("control") == prior_control
                                   and current["prediction"].get("control") == current_control)
        same_control = (prior_control is not None and prior_control == current_control
                        and question_matches_action)
        # A refit may change how the same rendered response is segmented into a
        # frame and arguments. That is a representation change, not evidence that
        # an old outcome has been ruled out in a shared response language.
        def event_meaning(observed_event):
            return None if observed_event is None else (observed_event["frame"], observed_event["args"])

        response_changed = event_meaning(old_event) != event_meaning(event)
        # Fitting can change the available primitives, not just reject models
        # with new evidence. Even additive fields can change the admitted LIST
        # surface. Report that joint change without calling it rival elimination
        # in a fixed language. Point rules are intentionally not grammar here.
        current_model = self.outcomes.get(current_control)
        language_changes = [component for component in ("roles", "ordered", "pairs", "defaults")
                            if _public(getattr(old_model, component, None)) !=
                               _public(getattr(current_model, component, None))]
        return {"before": prior, "after": current,
                "removed_outcomes": sorted(old - new) if searches_complete else None,
                "added_outcomes": sorted(new - old) if searches_complete else None,
                "found_set_differences": {"missing_after": sorted(old - new), "newly_found": sorted(new - old)},
                "remaining_ambiguity": True if len(new) > 1 else False if searches_complete else None,
                "no_admissible_interpretation": not new if searches_complete else None,
                "searches_complete": searches_complete,
                "rival_outcome_elimination": bool(searches_complete and len(old) > 1 and new and new < old
                                                   and not owner_changed and same_control
                                                   and not response_changed and not language_changes),
                "fitted_language_changes": language_changes,
                "predictive_alternatives_reduced": bool(searches_complete and new and new < old),
                "owner_interpretation_changed": owner_changed,
                "representation_changed": prior["representation_revision"] != current["representation_revision"],
                "same_control": same_control,
                "question_matches_action": question_matches_action,
                "response_interpretation_changed": response_changed,
                "observed": {"previous_model": observed_before, "current_model": observed_after},
                "additional_observed_frame": bool(old_event is not None and (
                    old_model is None or old_event["frame"] not in old_model.events)),
                "observation_consistent_with_current_prediction": consistent,
                "false_certainty": current["kind"] == "AGREED_OUTCOME" and consistent is False,
                "scope": "locally supported retained guard-prefix alternatives at one raw question, not globally complete response models; fixed-language elimination is withheld on incomplete search or changed primitives; not a count of syntactic clauses or proof of targeting advantage"}

    def predict(self, obs, node, control=None, *, search_budget=None):
        obs = self.prepare(obs)
        actual = self.control_at(obs, node)
        control = control or actual
        got = self.outcomes.get(control)
        base = {"control": control, "observation": obs.structural_signature(), "node": node}
        if actual != control or got is None:
            return {**base, "status": "unavailable", "reason": "control is not supported by this artifact"}
        state = self.abstract(obs)
        owner = consequence._owner_object(self.abstractor, self.abstractor.parsed(obs), state, node)
        bound, binding_status = got.bind(state, owner)
        literals = outcome.query_literals(self, got, state, bound, binding_status)
        point = got.predict(literals)
        # Match ControlOutcome.answer's declared language and corroboration policy.
        result = got.admissibility(literals, corroborated=True, hypothesis=outcome.LIST,
                                   search_budget=search_budget)
        options = result.options
        alternatives = {}
        for event, witness in sorted(options.items()):
            shape, how = got.delta(event)
            alternatives[event] = {"condition": _public(witness.condition), "witnesses": list(witness.witnesses),
                                   "sole": witness.sole, "ordered_after": list(witness.preceded_by),
                                   "delta": _public(shape), "delta_status": how,
                                   "arguments": _public(got.arguments(event, bound))}
        return {**base, "status": "unavailable" if not result.complete else
                "supported" if len(options) == 1 and not next(iter(options.values())).sole
                else "ambiguous" if options else "unavailable", "point": point,
                "owner": _owner_record(owner, state),
                "hypothesis": outcome.LIST, "alternatives": alternatives,
                "alternatives_complete": result.complete,
                "search": {"reason": result.reason, "scope": result.scope, **result.work},
                "ordered_witnesses": _public(result.witnesses),
                "bindings": {name: {"type": obj.tid, "key": obj.key, "node": obj.node,
                                     "attributes": dict(obj.attrs), "references": _public(obj.refs)}
                             for name, obj in bound.items()},
                "binding_status": binding_status, "literals": _public(literals),
                "reason": "LIST search incomplete" if not result.complete else
                          "one empirical alternative" if len(options) == 1 else
                          "several supported alternatives" if options else "no supported interpretation here"}

    def observe(self, before, after, control):
        response = emission.observe_response(before, after)
        locations = [location for location in emission.response_locations(before, after)
                     if location["text"].strip()]
        events = [emission.lift_event(location["text"], after, before, vocabulary=self.abstractor.emissions)
                  for location in locations]
        event = events[0] if len(events) == 1 else None
        return {"control": control, "before": before.structural_signature(), "after": after.structural_signature(),
                "status": "observed_response" if event is not None else "unconfirmed_response",
                "changed": event is not None,
                "event": None if event is None else {"frame": event.frame, "args": list(event.args), "text": event.text,
                                                     "node": locations[0]["node"], "path": _public(locations[0]["path"])},
                "candidates": [{"frame": e.frame, "args": list(e.args), "text": e.text,
                                "node": location["node"], "path": _public(location["path"])}
                               for e, location in zip(events, locations)],
                "regions": {"before": _public(response.before_regions), "after": _public(response.after_regions)},
                "attribution": "changed live region after action; exclusive causality not established"}

    def verify_response(self, before, after, node, control=None, *, prediction=None):
        """Check an observed response's learned frame and bound object arguments.

        A surprising known branch can be confirmed. The point prediction is never
        used as the answer key. Novel frames and unnamed/fresh arguments remain visible
        but unconfirmed; creation needs its own independent freshness/effect check.
        """
        prediction = prediction if prediction is not None else self.predict(before, node, control)
        control = control or prediction.get("control")
        response = self.observe(before, after, control)
        response.update(verified=False, recognized=False, arguments_match=False)
        got = self.outcomes.get(control)
        if prediction.get("control") != control or got is None:
            response["verification_reason"] = "action control does not match the learned response model"
            return response
        event = response.get("event")
        if not response["changed"] or event is None:
            response["verification_reason"] = "no uniquely distinguishable new response"
            return response
        frame = event["frame"]
        if frame not in got.events:
            response["verification_reason"] = "response frame is outside the learned outcome vocabulary"
            return response
        response["recognized"] = True
        # ControlOutcome.arguments currently projects object keys only. Reconstruct that
        # narrow view from this action's own preflight bindings, not the response text.
        bound = {role: SimpleNamespace(key=obj["key"])
                 for role, obj in prediction.get("bindings", {}).items() if obj and "key" in obj}
        expected = got.arguments(frame, bound)
        response["expected_arguments"] = _public(expected)
        positions = set(range(len(event["args"]))) | set(got.arg_roles.get(frame, {}))
        unresolved = sorted(position for position in positions
                            if position not in expected or expected[position] == outcome.FRESH)
        disagreements = {position: {"expected": value,
                                   "observed": event["args"][position] if position < len(event["args"]) else None}
                         for position, value in expected.items()
                         if position >= len(event["args"]) or event["args"][position] != value}
        response["unresolved_arguments"] = unresolved
        response["argument_disagreements"] = _public(disagreements)
        response["arguments_match"] = not unresolved and not disagreements
        response["verified"] = response["arguments_match"]
        response["verification_reason"] = ("response arguments require additional grounding" if unresolved else
                                           "response names a different object" if disagreements else
                                           "observed known response with grounded arguments" if positions else
                                           "observed known response frame; no object arguments asserted")
        response["verification_scope"] = "response after selected action; durable state effect and exclusive causality require separate checks"
        return response


def training_evidence_digest(log: EvidenceLog) -> str:
    """Identify the raw action and observation input to a reusable fitted artifact."""
    evidence = {"steps": [step.to_json() for step in log.steps],
                "observations": [{"signature": sig, "observation": obs.to_json()}
                                 for sig, obs in log.observations.items()]}
    return hashlib.sha256(json.dumps(evidence, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def fit_semantics(run_dir: Path, *, recipe: dict | None = None) -> SemanticArtifact:
    started = monotonic()
    run_dir = Path(run_dir)
    recipe = deepcopy(FIT_RECIPE if recipe is None else recipe)
    if set(recipe) != set(FIT_RECIPE) or recipe["version"] != 1 or recipe["cut"] != "all_recorded_steps":
        raise ValueError("unsupported semantic fitting recipe")
    if recipe["reading"] is not None:
        raise ValueError("ordinary semantic fitting does not accept supplied readings")
    captured = capture_fit_inputs(run_dir)
    _check_fit_inputs(run_dir, captured)
    # Legacy fit helpers reopen their EvidenceLog and three sidecars. Give every
    # read the same private byte snapshot, not a mutable source directory. This
    # does not change probe parsing, prefix semantics, or outcome field policy.
    with TemporaryDirectory(prefix="semabi-fit-") as temporary:
        frozen_dir = Path(temporary)
        for name, raw in captured.items():
            if raw is not None:
                (frozen_dir / name).write_bytes(raw)
        log = EvidenceLog(frozen_dir)
        options = {key: value for key, value in recipe.items()
                   if key not in ("version", "reading", "cut")}
        fitted = consequence.fit(frozen_dir, None, at=len(log.steps), **options)
    _check_fit_inputs(run_dir, captured)
    H = fitted.abstractor.H
    representation = {"entities": H.entity_types, "keys": {k: u.key_slot for k, u in H.units.items()},
                      "response_independent_structure": fitted.abstractor.G.response_independent_structure,
                      "unions": H.withheld_unions, "persistence": H.persistent_widgets,
                      "contextual_identity": H.contextual_identity, "record_splits": H.record_splits,
                      "aliases": H.alias_map, "slot_attachments": H.slot_attachments,
                      "mention_assignments": H.raw_mention_assignments,
                      "context_assignments": H.raw_context_assignments}
    revision = hashlib.sha256(json.dumps(_pack(representation), sort_keys=True).encode()).hexdigest()[:16]
    metadata = {"fitted_steps": len(log.steps), "fitted_observations": len(log.observations),
                "training_evidence": {"directory": run_dir.name, "digest": training_evidence_digest(log)},
                "fit_provenance": _fit_provenance(captured, recipe),
                "fit_seconds": round(monotonic() - started, 6), "regime": fitted.regime,
                "representation_revision": revision,
                "language_version": VERSION, "source": "ordinary rendered EvidenceLog"}
    return SemanticArtifact(fitted.abstractor, fitted.outcomes, metadata)
