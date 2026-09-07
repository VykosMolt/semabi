"""Observe one unchanged native fit; export stored fields without native callbacks.

Importing this module uses only the standard library. ``native_bindings`` imports
the public learner modules when a separately admitted runner is ready to fit.
The observer never calls a fit, abstraction, denotation or learning method.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import dis
import hashlib
import importlib
import json
import math
import sys
import threading

SCHEMA = "semabi.transport.j1_normal_fit_trace.v1"
PROJECTION_SCHEMA = "semabi.transport.j1_fit_projection.v1"
MISSING = object()

# Explicit stored dataclass fields. Additional instance data is reported as
# unsupported; methods/properties are never used to complete a record.
RECORDS = {
    "abstract": {
        "SlotInfo": "key n_present n_total values seen_after_reload presence_lost_on_reload value_kept value_lost unique_in_obs obs_count typed_hits present_with_key n_identified values_with_key",
        "TypeInfo": "tid n_instances seen_after_reload lost_on_reload key_slot slots merged merged_map parent_tids refs keys_survive_reload selector_of",
        "AbsObj": "tid key attrs parent refs ordinal node positional",
        "AbstractState": "objs view partial unidentified provisional parsed unknown_is_none",
        "Diff": "added removed attr_changes rel_changes view_changes",
    },
    "parse": {
        "Instance": "root tid parent slots context anchor positional",
        "ParsedObs": "obs instances statics node_instance node_key row_named",
    },
    "browser": {"Primitive": "kind target text target_desc"},
    "observation": {
        "Node": "i parent role name value checked options placeholder current bbox",
        "Observation": "nodes url _children",
    },
    "evidence": {"Step": "step episode action ok error before after typed_tokens"},
    "induce": {
        "Locator": "slot owner_tid trans_tid trans_slot ui_slot",
        "ActT": "kind loc owner arg",
        "EffT": "kind tid obj slot old new attrs parent refs anchor_rel",
        "Transition": "episode steps macro before after d acts effs binding param_types ambiguous ext emission",
        "ViewOp": "slot acts param tid support",
        "OperatorHyp": "name acts effs params positives negatives pre common alternatives unexplained_negatives verified failed",
    },
    "v2.hypotheses": {
        "UnitInstance": "sig root template slots slot_nodes nested parent_root positional",
        "SlotStat": "id values n unique_in_parent crowded numeric n_obs_values",
        "UnitHyp": "template instances slots key_slot key_score max_per_obs evidence",
        "EntityType": "tid units key_slot attr_slots ref_slots link_parent matrix contain evidence",
    },
    "v2.units": {"UnitType": "template instances fillings n_obs max_per_obs"},
    "v2.controls": {
        "ControlDescriptor": "role label template path",
        "ControlFamily": "id role label path templates options occurrences",
        "ControlFamilies": "families by_node by_descriptor by_key",
    },
    "v4.emission": {"Event": "frame args text"},
    "v4.pinned": {
        "FamilyReading": "family key_slot status discrimination",
        "PinnedReading": "families promoted_families refuted provenance name withheld_unions",
    },
    "v4.referring": {
        "Query": "kind variable detail given form",
        "Grounding": "operator params action_bound effect_variables output_variables created witnesses queries unreachable positives basis",
    },
    "v4.outcome": {
        "Alias": "name parts tid evidence",
        "Role": "name kind form tid anchor",
        "Rule": "condition event covered",
        "ControlOutcome": "control roles rules default fitted events evidence defaults ordered pairs simplest deltas arg_roles",
    },
}

INDUCER_FIELDS = (
    "read_outputs", "_state_cache", "_tracked_before", "_tracked_after", "_changing_steps",
    "view_transitions", "view_ops", "_view_steps", "queries", "reattributed", "_seen_keys",
    "delayed_resolutions", "unattributed_sensing_changes",
)
ABSTRACTOR_FIELDS = (
    "types", "static_slots", "_cache", "merge_mentions", "conservative_belief", "data",
    "_controls", "_assigned", "tid_map", "link_pairs", "record_by_anchor", "explicit_link_types",
    "view_controls", "verified_view_controls", "heuristic_view_controls", "verified_domain_controls",
    "mention_conflicts", "_mention_conflict_keys", "family_refs", "registry", "probe_status", "probe_by_step",
)
HYPOTHESIS_FIELDS = (
    "unit_types", "promoted", "units", "entity_types", "tid_of_template", "allowed", "ctx_split",
    "transient", "transient_positions", "mirror_positions", "mirror_keys", "force_link", "withheld_unions",
    "_page_instances", "alias_map", "key_overrides", "persistent_widgets", "slot_attachments",
    "contextual_identity", "mention_type_assignments", "raw_mention_assignments", "raw_context_assignments",
    "record_splits", "_split_done", "frozen", "step_sigs", "reload_pairs", "step_targets", "step_kinds",
)
EVIDENCE_FIELDS = ("subjects", "_blocks", "events", "index", "masks", "by_event", "of_bit", "occasion_obs", "about")


@dataclass(frozen=True)
class RecordSpec:
    label: str
    fields: tuple
    optional: tuple = ()


@dataclass(frozen=True)
class Bindings:
    """Exact code/type objects; explicit injection supports invented hook checks."""
    codes: dict
    records: dict
    types: dict
    sentinels: tuple = ()


def native_bindings():
    modules = {name: importlib.import_module("semabi.compiler." + name) for name in RECORDS}
    modules["compile_v4"] = importlib.import_module("semabi.compiler.compile_v4")
    modules["v4.consequence"] = importlib.import_module("semabi.compiler.v4.consequence")
    modules["v4.abstractor"] = importlib.import_module("semabi.compiler.v4.abstractor")
    records = {}
    for module_name, classes in RECORDS.items():
        for name, text in classes.items():
            cls = vars(modules[module_name])[name]
            names = tuple(text.split())
            if set(vars(cls)["__dataclass_fields__"]) != set(names):
                raise ValueError("Native dataclass schema differs: " + module_name + "." + name)
            optional = {"ControlOutcome": ("field_theory",),
                        "ParsedObs": ("_member_positioned_cache",)}.get(name, ())
            records[cls] = RecordSpec("semabi.compiler." + module_name + "." + name, names, optional)
    inducer = modules["induce"].Inducer
    consequence = modules["v4.consequence"]
    outcome = modules["v4.outcome"]
    functions = {
        "fit": consequence.fit, "compile": modules["compile_v4"].compile_v4,
        "run": inducer.run, "lift": inducer.lift, "ground": modules["v4.referring"].ground,
        "view_cluster": inducer._cluster_view_ops,
        "inducer_queries": inducer.learn_queries, "consequence_queries": consequence._learn_queries,
        "controls": outcome._learn_controls, "roles": outcome.roles_of,
    }
    return Bindings(
        {name: function.__code__ for name, function in functions.items()}, records,
        {"inducer": inducer, "transition": modules["induce"].Transition,
         "operator": modules["induce"].OperatorHyp, "fit": consequence.Fit,
         "state": modules["abstract"].AbstractState, "observation": modules["observation"].Observation,
         "evidence": outcome.Evidence, "abstractor": modules["v4.abstractor"].V4Abstractor,
         "hypotheses": modules["v2.hypotheses"].Hypotheses, "log": modules["evidence"].EvidenceLog,
         "vocabulary": modules["v4.emission"].Vocabulary},
        ((modules["induce"].VARIES, "semabi.compiler.induce.VARIES"),),
    )


def canonical(value):
    # Native mappings have already become ordered entry lists. Sorting envelope
    # keys here cannot change their evidence or insertion order.
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def stored(value):
    """Use only an actual instance dictionary, never getattr/property fallback."""
    result = object.__getattribute__(value, "__dict__")
    if type(result) is not dict:
        raise TypeError("Expected an ordinary stored instance dictionary")
    return result


def sequence(value):
    if type(value) is not list:
        raise TypeError("Expected a stored native list; iterators are not consumed")
    return value


def mapping(value):
    if type(value) is not dict:
        raise TypeError("Expected a stored native dictionary")
    return value


class IdentityTable:
    def __init__(self, prefix):
        self.prefix = prefix
        self.entries = []
        self.by_id = {}

    def add(self, value):
        key = id(value)
        if key in self.by_id:
            original, label = self.by_id[key]
            if original is not value:
                raise ValueError("Object identity was reused despite retained ownership")
            return label
        label = self.prefix + format(len(self.entries), "06d")
        self.entries.append((value, label))
        self.by_id[key] = (value, label)  # Hold the object, not just its id.
        return label


class Copier:
    """Typed copies with transition identities and deduplicated state/page data."""
    def __init__(self, bindings):
        self.bindings = bindings
        self.errors = []
        self.snapshots = {}
        self.transitions = IdentityTable("transition_")

    def unknown(self, reason, path, *, incomplete=True):
        record = {"reason": reason, "path": path}
        if incomplete:
            self.errors.append(record)
        return {"$unknown": record}

    def copy(self, value, path="root", *, transition_body=False):
        try:
            return self._copy(value, path, set(), transition_body=transition_body)
        except BaseException as error:
            return self.unknown("copy_exception:" + type(error).__name__, path)

    def fields(self, value, names, path, *, optional=()):
        try:
            data = stored(value)
            return {name: self.copy(data[name], path + "." + name) if name in data else
                    self.unknown("not_stored", path + "." + name, incomplete=name not in optional)
                    for name in names}
        except BaseException as error:
            return self.unknown("stored_fields_exception:" + type(error).__name__, path)

    def _copy(self, value, path, active, *, transition_body=False):
        kind = type(value)
        if value is None or kind in (str, bool):
            return value
        if kind is int:
            return value if -(2 ** 53) < value < 2 ** 53 else {"$integer_decimal": format(value, "d")}
        if kind is float:
            return value if math.isfinite(value) else self.unknown("nonfinite_float", path)
        if value is MISSING:
            return self.unknown("not_stored", path, incomplete=False)
        for sentinel, label in self.bindings.sentinels:
            if value is sentinel:
                return {"$sentinel": label}
        if kind is self.bindings.types.get("transition") and not transition_body:
            return {"$transition": self.transitions.add(value)}
        key = id(value)
        if key in active:
            return self.unknown("cycle", path)
        active.add(key)
        try:
            if kind in (list, tuple):
                items = [self._copy(item, path + "[" + format(index, "d") + "]", active)
                         for index, item in enumerate(value)]
                return items if kind is list else {"$tuple": items}
            if kind in (dict, Counter, defaultdict):
                items = [[self._copy(k, path + ".key", active), self._copy(v, path + ".value", active)]
                         for k, v in dict.items(value)]
                return {"$mapping": kind.__name__, "items": items}
            if kind in (set, frozenset):
                items = [self._copy(item, path + ".member", active) for item in value]
                items.sort(key=canonical)
                return {"$set": kind.__name__, "items": items}
            if kind is self.bindings.types.get("evidence"):
                data = stored(value)
                result = {name: self._copy(data[name], path + "." + name, active) if name in data else
                          self.unknown("not_stored", path + "." + name) for name in EVIDENCE_FIELDS}
                result["refuse_runtime_handle"] = {"stored": "refuse" in data,
                    "present": data.get("refuse") is not None,
                    "scope": "Computational predicate handle excluded; never executed or rendered"}
                extra = set(data) - set(EVIDENCE_FIELDS) - {"refuse"}
                if extra:
                    result["unsupported_fields"] = [self.unknown("unsupported_stored_field", path + "." + name)
                                                    for name in sorted(extra)]
                return {"$record": "semabi.compiler.v4.outcome.Evidence", "fields": result}
            spec = self.bindings.records.get(kind)
            if spec is None:
                return self.unknown("unsupported_type", path)
            data = stored(value)
            fields = {}
            for name in spec.fields + spec.optional:
                fields[name] = (self._copy(data[name], path + "." + name, active) if name in data else
                                self.unknown("not_stored", path + "." + name, incomplete=name not in spec.optional))
            for name in data:
                if name not in spec.fields and name not in spec.optional:
                    fields[name] = self.unknown("unsupported_stored_field", path + "." + name)
            result = {"$record": spec.label, "fields": fields}
            if kind in (self.bindings.types.get("state"), self.bindings.types.get("observation")):
                address = sha(result)
                self.snapshots.setdefault(address, result)
                return {"$snapshot": address}
            return result
        finally:
            active.remove(key)


def plain_snapshot(value):
    """Take ownership of caller-supplied JSON data without invoking its methods."""
    active = set()
    def take(item):
        kind = type(item)
        if item is None or kind in (str, int, bool):
            return item
        if kind is float and math.isfinite(item):
            return item
        if kind not in (dict, list, tuple) or id(item) in active:
            raise TypeError("raw_records must be acyclic ordinary JSON data")
        active.add(id(item))
        try:
            if kind is dict:
                if any(type(key) is not str for key in item):
                    raise TypeError("raw_records dictionary keys must be strings")
                return {key: take(child) for key, child in item.items()}
            return [take(child) for child in item]
        finally:
            active.remove(id(item))
    return take(value)


def membership(transition, inducer, operators):
    data = stored(inducer)
    transitions, noops = sequence(data["transitions"]), sequence(data["noops"])
    views = sequence(data["view_transitions"])
    if any(type(item) is not tuple or len(item) != 4 for item in views):
        raise TypeError("Expected retained native view-transition tuples")
    operators = sequence(operators)
    for operator in operators:
        sequence(stored(operator)["positives"])
        sequence(stored(operator)["negatives"])
    return {
        "transitions": [i for i, item in enumerate(transitions) if item is transition],
        "noops": [i for i, item in enumerate(noops) if item is transition],
        "view_transitions": [i for i, item in enumerate(views) if item[0] is transition],
        "operator_positives": [{"operator_index": oi, "position": ti}
            for oi, op in enumerate(operators) for ti, item in enumerate(stored(op)["positives"])
            if item is transition],
        "operator_negatives": [{"operator_index": oi, "position": ti}
            for oi, op in enumerate(operators) for ti, item in enumerate(stored(op)["negatives"])
            if item is transition],
    }


def _raw_mapping(raw_records, log, copier):
    """Join actual retained step records; never recompute an observation hash."""
    if raw_records is None:
        return copier.unknown("raw_records_not_supplied", "raw_mapping")
    raw = plain_snapshot(raw_records)
    if type(raw) is not dict or set(raw) != {"steps", "observations"}:
        return copier.unknown("raw_records_require_steps_and_observations", "raw_mapping")
    raw_steps, raw_observations = raw["steps"], raw["observations"]
    if type(raw_steps) is not list or type(raw_observations) is not list:
        return copier.unknown("raw_records_require_lists", "raw_mapping")
    normalized = stored(log)
    native_steps, native_observations = sequence(normalized["steps"]), mapping(normalized["observations"])
    indexed = {}
    for step in native_steps:
        row = stored(step)
        key = row["step"]
        if type(key) is not int or key in indexed:
            return copier.unknown("duplicate_or_invalid_normalized_step", "raw_mapping")
        indexed[key] = row
    raw_pages = {}
    for row in raw_observations:
        if type(row) is not dict or type(row.get("sig")) is not str or row["sig"] in raw_pages or "obs" not in row:
            return copier.unknown("duplicate_or_invalid_raw_observation", "raw_mapping")
        raw_pages[row["sig"]] = row["obs"]
    seen, mappings, signatures = set(), [], {}
    for raw_step in raw_steps:
        if type(raw_step) is not dict or type(raw_step.get("step")) is not int or raw_step["step"] in seen:
            return copier.unknown("duplicate_or_invalid_raw_step", "raw_mapping")
        key = raw_step["step"]
        seen.add(key)
        row = indexed.get(key)
        if row is None:
            mappings.append({"step": key, "mapping": copier.unknown("raw_step_absent_from_normalized_log", "raw_mapping")})
            continue
        action = stored(row["action"])
        given_action = raw_step.get("action")
        if (type(given_action) is not dict or any(given_action.get(name) != action[name]
                for name in ("kind", "target", "text", "target_desc"))
                or raw_step.get("episode") != row["episode"] or raw_step.get("ok") != row["ok"]
                or raw_step.get("error") != row["error"]):
            mappings.append({"step": key, "mapping": copier.unknown("raw_normalized_step_disagreement", "raw_mapping")})
            continue
        associations = {}
        for side in ("before", "after"):
            original, revised = raw_step.get(side), row[side]
            if original not in raw_pages or revised not in native_observations:
                associations[side] = copier.unknown("observation_mapping_missing_page", "raw_mapping")
                continue
            signatures.setdefault(original, [])
            if revised not in signatures[original]:
                signatures[original].append(revised)
            associations[side] = {"raw_signature": original, "normalized_signature": revised}
        mappings.append({"step": key, "episode": row["episode"], "raw_action": given_action, **associations})
    if seen != set(indexed):
        copier.unknown("raw_normalized_step_inventory_disagreement", "raw_mapping")
    observations = []
    for signature in raw_pages:
        matches = signatures.get(signature, [])
        observations.append({"raw_signature": signature, "normalized_signatures": matches,
                             "association": "STEP_ID_AND_SIDE" if matches else
                             copier.unknown("raw_observation_has_no_step_association", "raw_mapping")})
        if len(matches) > 1:
            copier.unknown("one_raw_signature_has_multiple_normalized_signatures", "raw_mapping")
    return {"raw_records": raw, "raw_records_sha256": sha(raw),
            "step_associations": mappings, "observation_associations": observations,
            "method": "Actual step ID, episode and primitive correspondence; original signatures supplied before fit"}


def project_fit(fit, *, raw_records=None, primary_steps=(), bindings=None):
    """Common final projection for matched processes, including an unprofiled fit."""
    bindings = native_bindings() if bindings is None else bindings
    copier = Copier(bindings)
    result = {"schema": PROJECTION_SCHEMA, "scope": "Stored final-fit data only; no native methods called"}
    try:
        if type(fit) is not bindings.types["fit"]:
            raise TypeError("Expected the actual native Fit type")
        model = stored(fit)
        inducer = model["inducer"]
        if type(inducer) is not bindings.types["inducer"]:
            raise TypeError("Expected the actual native Inducer type")
        native = stored(inducer)
        operators = sequence(model["operators"])
        # Register final identities in a deterministic order independent of the
        # profiler's earlier temporary objects. Common projections contain no IDs
        # from the in-flight trace and no process addresses.
        for transition in sequence(native["transitions"]) + sequence(native["noops"]):
            copier.transitions.add(transition)
        for operator in operators:
            for transition in sequence(stored(operator)["positives"]) + sequence(stored(operator)["negatives"]):
                copier.transitions.add(transition)
        result["fit"] = copier.fields(fit, ("reading", "cut", "split", "regime", "read_outputs", "queries", "outcomes"), "fit")
        result["operators"] = copier.copy(operators, "operators")
        result["inducer"] = copier.fields(inducer, INDUCER_FIELDS, "inducer")
        result["transition_order"] = [copier.transitions.add(row) for row in native["transitions"]]
        result["noop_order"] = [copier.transitions.add(row) for row in native["noops"]]
        abstractor = model["abstractor"]
        if type(abstractor) is not bindings.types["abstractor"]:
            raise TypeError("Expected the actual native V4Abstractor type")
        abstract_data = stored(abstractor)
        result["abstractor"] = copier.fields(abstractor, ABSTRACTOR_FIELDS, "abstractor",
            optional=("probe_status", "probe_by_step"))
        hypotheses = abstract_data["H"]
        if type(hypotheses) is not bindings.types["hypotheses"]:
            raise TypeError("Expected the actual native Hypotheses type")
        result["hypotheses"] = copier.fields(hypotheses, HYPOTHESIS_FIELDS, "hypotheses",
            optional=("step_sigs", "reload_pairs", "step_targets", "step_kinds"))
        vocabulary = abstract_data["emissions"]
        if type(vocabulary) is not bindings.types["vocabulary"]:
            raise TypeError("Expected the actual native emission Vocabulary type")
        result["emission_vocabulary"] = copier.fields(vocabulary, ("values", "frozen"), "emission_vocabulary")
        for name in ("log", "evidence"):
            log = model[name]
            if type(log) is not bindings.types["log"]:
                raise TypeError("Expected an actual EvidenceLog")
            result[name] = copier.fields(log, ("steps", "observations", "typed_tokens"), name)
        result["raw_mapping"] = _raw_mapping(raw_records, model["log"], copier)
        permitted = [stored(step)["step"] for step in sequence(stored(model["evidence"])["steps"])]
        result["permitted_evidence_step_ids"] = permitted
        selected_steps = plain_snapshot(primary_steps)
        if type(selected_steps) is not list or any(type(step) is not int for step in selected_steps):
            raise TypeError("Primary step selector must contain plain integer IDs")
        result["primary_step_associations"] = []
        # Copy the registry to a fixed point: stored view transitions may add
        # legitimate temporary objects while their bodies are copied.
        result["transitions"] = []
        index = 0
        while index < len(copier.transitions.entries):
            transition, identity = copier.transitions.entries[index]
            result["transitions"].append({"identity": identity,
                "membership": membership(transition, inducer, operators),
                "snapshot": copier.copy(transition, "transitions." + identity, transition_body=True)})
            index += 1
        for step in selected_steps:
            associations = []
            for transition, identity in copier.transitions.entries:
                tr = stored(transition)
                effective, macro = step in sequence(tr["steps"]), step in sequence(tr["macro"])
                if effective or macro:
                    associations.append({"transition": identity, "effective": effective,
                                         "macro": macro, "macro_only": macro and not effective,
                                         "membership": membership(transition, inducer, operators)})
            if step not in permitted and associations:
                copier.unknown("transition_association_outside_permitted_evidence", "primary_step_associations")
            result["primary_step_associations"].append({"step": step,
                "permitted_fitting_step": step in permitted, "associations": associations,
                "status": "ASSOCIATED" if associations else "NO_FITTING_ASSOCIATION"})
        result["declared_nondata_exclusions"] = [
            "Abstractor/parser/graph execution handles and hypothesis graph/memo caches",
            "EvidenceLog filesystem handles; permitted input paths and hashes belong to the runner freeze",
            "Evidence refusal predicate handle; masks/events/index and subjects/about are copied",
            "Native properties and computed summaries; only their stored constituent fields are copied",
        ]
    except BaseException as error:
        copier.unknown("projection_exception:" + type(error).__name__, "projection")
    result["snapshots"] = copier.snapshots
    result["incomplete_reasons"] = copier.errors
    result["status"] = "INCOMPLETE" if copier.errors else "COMPLETE"
    return result


class FitObserver:
    """Scoped profiler around one caller-owned normal fit; no fit invocation API."""
    def __init__(self, *, raw_records=None, primary_steps=(), bindings=None):
        self.bindings = native_bindings() if bindings is None else bindings
        self.raw_records = None if raw_records is None else plain_snapshot(raw_records)
        self.primary_steps = plain_snapshot(primary_steps)
        self.copier = Copier(self.bindings)
        self.operators = IdentityTable("operator_")
        self.events = []
        self.pending_ground = {}
        self.pending_controls = {}
        self.control_outputs = []
        self.fit_calls = 0
        self.selected_calls = 0
        self.omitted_inducer_calls = []
        self.lift_counts = {}
        self.boundary_index = 0
        self.capture_codes = {self.bindings.codes[name] for name in
                              ("fit", "run", "lift", "ground", "controls", "roles")}
        self.selected = None
        self.fit_result = None
        self.fit_frame = None
        self.previous = None
        self.owner_thread = None
        self.active = False
        self.closed = False
        self.restored = False

    def __enter__(self):
        if self.active or self.closed:
            raise RuntimeError("A FitObserver identity is single-use")
        self.previous = sys.getprofile()
        if self.previous is not None:
            raise RuntimeError("Refuse to replace an already active profiler")
        self.owner_thread = threading.get_ident()
        self.active = True
        try:
            sys.setprofile(self._profile)
        except BaseException:
            self.active = False
            sys.setprofile(self.previous)
            raise
        return self

    def __exit__(self, exception_type, exception, traceback):
        try:
            if threading.get_ident() != self.owner_thread:
                self.copier.unknown("context_exit_on_another_thread", "context")
                raise RuntimeError("FitObserver must exit on its owning thread")
            if sys.getprofile() != self._profile:
                self.copier.unknown("profile_hook_replaced_during_fit", "context")
            sys.setprofile(self.previous)
            self.restored = sys.getprofile() is self.previous
        finally:
            self.active = False
            self.closed = True
            self.fit_frame = None
        if exception_type is not None:
            self.copier.unknown("native_fit_raised:" + exception_type.__name__, "context")
        if self.fit_calls != 1 or self.selected_calls != 1:
            self.copier.unknown("expected_exactly_one_fit_and_final_inducer_run", "context")
        if self.pending_ground or self.pending_controls:
            self.copier.unknown("observed_calls_without_return", "context")
        return False

    def _event(self, kind):
        record = {"event_index": len(self.events), "boundary_index": self.boundary_index, "kind": kind}
        self.events.append(record)
        return record

    def _belongs_to_fit(self, frame):
        current = frame
        while current is not None:
            if current is self.fit_frame:
                return True
            current = current.f_back
        return False

    def _transition(self, transition, path):
        if type(transition) is not self.bindings.types["transition"]:
            raise TypeError("Expected the actual transition type")
        return {"identity": self.copier.transitions.add(transition),
                "snapshot": self.copier.copy(transition, path, transition_body=True)}

    def _operator(self, operator, path):
        if type(operator) is not self.bindings.types["operator"]:
            raise TypeError("Expected the actual operator type")
        data = stored(operator)
        return {"identity": self.operators.add(operator), "snapshot": self.copier.copy(operator, path),
                "positives": [self._transition(tr, path + ".positives") for tr in sequence(data["positives"])],
                "negatives": [self._transition(tr, path + ".negatives") for tr in sequence(data["negatives"])]}

    def _control_rows(self, by_control):
        if type(by_control) is not dict:
            raise TypeError("Expected the actual ordered control dictionary")
        output = []
        for control, rows in by_control.items():
            if type(rows) is not list:
                raise TypeError("Control rows must be a retained list")
            copied = []
            for index, item in enumerate(rows):
                if type(item) is not tuple or len(item) != 4:
                    raise TypeError("Expected the native four-field control row")
                transition, step, observation, event = item
                copied.append({"row_index": index, "transition": self._transition(transition, "control_row.transition"),
                               "step": self.copier.copy(step, "control_row.step"),
                               "observation": self.copier.copy(observation, "control_row.observation"),
                               "event": self.copier.copy(event, "control_row.event"),
                               "emission_missing": event is None})
            output.append({"control": self.copier.copy(control), "rows": copied,
                           "all_events_missing": all(item[3] is None for item in rows),
                           "event_present_row_indices": [i for i, item in enumerate(rows) if item[3] is not None]})
        return output

    def _profile(self, frame, event, argument):
        if event not in ("call", "return") or frame.f_code not in self.capture_codes:
            return
        try:
            self.boundary_index += 1
            self._observe(frame, event, argument)
        except BaseException as error:
            # Callback failures invalidate observation, never the native learner.
            self.copier.unknown("callback_exception:" + type(error).__name__, "profile." + event)

    def _observe(self, frame, event, argument):
        codes, code = self.bindings.codes, frame.f_code
        if code is codes["fit"]:
            if event == "call":
                self.fit_calls += 1
                if self.fit_calls == 1:
                    self.fit_frame = frame
                else:
                    self.copier.unknown("additional_fit_call", "fit")
            elif frame is self.fit_frame:
                self.fit_result = argument
            return
        if not self._belongs_to_fit(frame):
            return
        local, parent = frame.f_locals, frame.f_back
        if code is codes["run"] and event == "call":
            if parent is not None and parent.f_code is codes["compile"]:
                self.selected_calls += 1
                instance = local["self"]
                if type(instance) is not self.bindings.types["inducer"]:
                    raise TypeError("Selected run has a nonnative inducer")
                if self.selected is None:
                    self.selected = instance
                else:
                    self.copier.unknown("additional_final_inducer_run", "run")
            else:
                self.omitted_inducer_calls.append({"boundary_index": self.boundary_index,
                    "caller": self._caller(parent),
                    "scope": "Nonselected Inducer.run call; caller identity retained without classifying it as a search trial"})
            return
        if self.selected is None:
            return
        if code is codes["lift"] and event == "return" and local.get("self") is self.selected:
            record = self._event("lift_return")
            record["transition"] = self._transition(local["tr"], "lift.transition")
            identity = record["transition"]["identity"]
            self.lift_counts[identity] = self.lift_counts.get(identity, 0) + 1
            record["lift_ordinal_for_transition"] = self.lift_counts[identity]
            record["first_observed_lift"] = self.lift_counts[identity] == 1
            record["caller"] = self._caller(parent)
            record["view_cluster_lift"] = parent is not None and parent.f_code is codes.get("view_cluster")
            record["normal_return"] = self._normal_return(frame)
            if not record["normal_return"]:
                self.copier.unknown("lift_exception_unwind", "lift")
            record["locals"] = {name: {"present": name in local, "value": self.copier.copy(local.get(name, MISSING), "lift." + name)}
                                for name in ("obj_param", "str_param", "view_sources", "ren")}
            return
        if code is codes["ground"]:
            caller = None
            if parent is not None and parent.f_code is codes["inducer_queries"] and parent.f_locals.get("self") is self.selected:
                caller = "Inducer.learn_queries"
            elif parent is not None and parent.f_code is codes["consequence_queries"] and parent.f_locals.get("inducer") is self.selected:
                caller = "consequence._learn_queries"
            if caller is None:
                return
            if event == "call":
                record = self._event("ground")
                record["call_id"] = "ground_" + format(record["event_index"], "06d")
                record["caller"] = caller
                record["entry"] = {"operator": self._operator(local["op"], "ground.operator"),
                    **{name: self.copier.copy(local[name], "ground." + name)
                       for name in ("evidence", "action_bound", "enabling", "collections")},
                    "refusal_predicate": "Actual argument retained by native call; never invoked by observer"}
                self.pending_ground[id(frame)] = (frame, record)
            else:
                original, record = self.pending_ground.pop(id(frame))
                if original is not frame:
                    raise ValueError("Grounding frame identity differs")
                record["return_boundary_index"] = self.boundary_index
                record["normal_return"] = self._normal_return(frame)
                record["wanted"] = {"present": "wanted" in local,
                                    "value": self.copier.copy(local.get("wanted", MISSING), "ground.wanted")}
                record["returned"] = self.copier.copy(argument, "ground.returned")
                record["returned_none"] = argument is None
                if argument is None or not record["normal_return"]:
                    self.copier.unknown("ground_returned_no_result_or_raised", "ground")
            return
        if code is codes["controls"] and local.get("inducer") is self.selected:
            if event == "call":
                record = self._event("control_pass")
                record["call_id"] = "control_pass_" + format(len(self.control_outputs), "06d")
                out = mapping(local["out"])
                ops_by_control = mapping(local["ops_by_control"])
                by_control = mapping(local["by_control"])
                self.control_outputs.append((out, record))
                record["entry"] = {"rows": self._control_rows(local["by_control"]),
                    "eligible_operators": [{"control": self.copier.copy(control),
                        "operators": [self._operator(op, "control_pass.operator") for op in sequence(ops)]}
                        for control, ops in ops_by_control.items()],
                    "control_operator_resolution": [{"control": self.copier.copy(control),
                        "dictionary_entry_present": control in ops_by_control,
                        "operators": [self._operator(op, "control_pass.control_operator")
                                      for op in sequence(ops_by_control.get(control, []))],
                        "empty_operator_set": not ops_by_control.get(control, [])} for control in by_control],
                    **{name: self.copier.copy(local[name], "control_pass." + name) for name in (
                        "first_view", "ordered", "pairs", "permute", "subject_restricted", "structural", "touched", "about", "simplest")},
                    "output_before": self.copier.copy(out, "control_pass.output_before")}
                self.pending_controls[id(frame)] = (frame, record)
            else:
                original, record = self.pending_controls.pop(id(frame))
                if original is not frame:
                    raise ValueError("Control-pass frame identity differs")
                record["returned_value"] = self.copier.copy(argument, "control_pass.returned_value")
                record["output_after"] = self.copier.copy(local["out"], "control_pass.output_after")
                record["return_boundary_index"] = self.boundary_index
                record["normal_return"] = self._normal_return(frame)
                if not record["normal_return"]:
                    self.copier.unknown("control_pass_exception_unwind", "control_pass")
            return
        if code is codes["roles"] and event == "return" and local.get("inducer") is self.selected:
            record = self._event("roles_return")
            current = self.pending_controls.get(id(parent)) if parent is not None else None
            record["control_pass"] = current[1]["call_id"] if current is not None and current[0] is parent else None
            record["control"] = {"present": parent is not None and "control" in parent.f_locals,
                                 "value": self.copier.copy(parent.f_locals.get("control", MISSING) if parent else MISSING)}
            record["operators"] = [self._operator(op, "roles.operator") for op in sequence(local["operators"])]
            record["returned"] = self.copier.copy(argument, "roles.returned")
            record["normal_return"] = self._normal_return(frame)
            if argument is None or not record["normal_return"]:
                self.copier.unknown("roles_returned_no_result_or_raised", "roles")

    def export(self, fit=None):
        if not self.closed or self.active:
            raise RuntimeError("Export only after the profiling context has restored its predecessor")
        fit = self.fit_result if fit is None else fit
        if fit is not self.fit_result:
            self.copier.unknown("export_fit_differs_from_actual_return", "export")
        projection = None
        memberships = []
        adopted = []
        operator_memberships = []
        if type(fit) is self.bindings.types["fit"]:
            if stored(fit).get("inducer") is not self.selected:
                self.copier.unknown("final_fit_inducer_is_not_selected_instance", "export")
            else:
                operators = stored(fit)["operators"]
                projection = project_fit(fit, raw_records=self.raw_records, primary_steps=self.primary_steps, bindings=self.bindings)
                for transition, identity in self.copier.transitions.entries:
                    memberships.append({"identity": identity,
                        "membership": membership(transition, self.selected, operators),
                        "current_snapshot": self.copier.copy(transition, "export." + identity, transition_body=True)})
                for out, record in self.control_outputs:
                    match = out is stored(fit)["outcomes"]
                    adopted.append({"call_id": record["call_id"], "is_final_fit_outcomes": match})
                for operator, identity in self.operators.entries:
                    operator_memberships.append({"identity": identity,
                        "final_operator_positions": [i for i, item in enumerate(operators) if item is operator],
                        "current_snapshot": self.copier.copy(operator, "export." + identity)})
                if stored(fit)["read_outputs"] and (len(self.control_outputs) == 0 or sum(r["is_final_fit_outcomes"] for r in adopted) != 1):
                    self.copier.unknown("expected_one_adopted_outcome_dictionary", "export")
        else:
            self.copier.unknown("fit_did_not_return_native_result", "export")
        incomplete = bool(self.copier.errors or projection is None or projection["status"] != "COMPLETE" or not self.restored)
        return {"schema": SCHEMA, "status": "INCOMPLETE" if incomplete else "COMPLETE",
            "fit_calls": self.fit_calls, "selected_final_run_calls": self.selected_calls,
            "omitted_inducer_run_calls": self.omitted_inducer_calls,
            "profiler_restored": self.restored, "events": self.events,
            "observed_transition_membership": memberships, "observed_operator_membership": operator_memberships,
            "outcome_pass_adoption": adopted,
            "snapshots": self.copier.snapshots, "projection": projection,
            "incomplete_reasons": self.copier.errors,
            "scope": "Natural calls of the final compile_v4 inducer only; no injected parameter, formula, query, fit or refusal-predicate call",
            "unobserved": "Search-trial internals, rejected candidate proposals and individual bind calls are outside this trace; their omission is not negative evidence"}

    @staticmethod
    def _caller(frame):
        return None if frame is None else {"file": frame.f_code.co_filename,
            "function": frame.f_code.co_name, "first_line": frame.f_code.co_firstlineno}

    @staticmethod
    def _normal_return(frame):
        # sys.setprofile also emits a return event on exception unwinding. Read
        # the actual bytecode position to distinguish it from a native None return.
        code = frame.f_code.co_code
        return (0 <= frame.f_lasti < len(code)
                and dis.opname[code[frame.f_lasti]] in ("RETURN_VALUE", "RETURN_CONST"))
