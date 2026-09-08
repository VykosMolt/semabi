"""Stored-field checkpoints for one resident native Fit.

The trace instrument remains unchanged. This local extension accounts for live
interpretation caches and graph data without executing a native export method.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


trace = _module("_j1_live_trace", Path(__file__).with_name("trace.py"))
FIT_FIELDS = tuple("reading abstractor operators log cut split inducer regime evidence queries read_outputs outcomes".split())
GRAPH_FROZEN = tuple("templates templates_v _in_nonwidget _whole _listed_only _declared_headers _seen header_strings learning".split())
GRAPH_LOOKUPS = tuple("nodes obs position_of variation_key header".split())
GRAPH_MEMOS = ("_data", "_value_paths", "_pooled_views")
EVIDENCE_RECORD = "semabi.compiler.v4.outcome.Evidence"
TYPED_CACHE_FIELDS = {
    "semabi.compiler.observation.Observation": {"_children"},
    "semabi.compiler.parse.ParsedObs": {"_member_positioned_cache"},
}
EXTENSIONS = {
    "v4.outcome": {"Vouch": "event witnesses condition covers sole preceded_by"},
    "v2.graph": {
        "TextTemplate": "position strings n _vary",
        "NodeDesc": "obs i role path shape own_tokens depth children parent",
    },
}


def native_bindings():
    original = trace.native_bindings()
    records = dict(original.records)
    for suffix, classes in EXTENSIONS.items():
        module = importlib.import_module("semabi.compiler." + suffix)
        for name, fields in classes.items():
            cls = vars(module)[name]
            names = tuple(fields.split())
            if set(vars(cls)["__dataclass_fields__"]) != set(names):
                raise ValueError("Native live record schema differs: " + suffix + "." + name)
            records[cls] = trace.RecordSpec("semabi.compiler." + suffix + "." + name, names)
    types = dict(original.types)
    types["graph"] = vars(importlib.import_module("semabi.compiler.v2.graph"))["ObsGraph"]
    return trace.Bindings(original.codes, records, types, original.sentinels)


def public_signature(observation):
    """The public Node-key hash, without native methods or display fallbacks."""
    parts = [(n["parent"], n["role"], n["name"], n.get("value"), n.get("checked"),
              tuple(n.get("options") or ()), n.get("placeholder"), n.get("current"))
             for n in observation["nodes"]]
    return hashlib.sha1(json.dumps(parts, sort_keys=True, allow_nan=False).encode()).hexdigest()[:16]


def _same_copied_value(value, expected):
    """Compare copied containers and scalars without Python numeric aliases."""
    if type(value) is not type(expected):
        return False
    if type(expected) is dict:
        return set(value) == set(expected) and all(
            _same_copied_value(value[key], item) for key, item in expected.items())
    if type(expected) is list:
        return len(value) == len(expected) and all(
            _same_copied_value(item, other) for item, other in zip(value, expected))
    return value == expected


def _copied_nonnegative_integer(value):
    """Accept only the frozen trace copier's exact integer representation."""
    if type(value) is int and 0 <= value < 2 ** 53:
        return value
    if type(value) is dict and set(value) == {"$integer_decimal"}:
        text = value["$integer_decimal"]
        if type(text) is str and text.isascii() and text.isdecimal():
            number = int(text)
            if number >= 2 ** 53 and text == str(number):
                return number
    raise ValueError("Invalid copied Evidence nonnegative integer")


def evidence_pair_blocks(fields):
    """Derive and validate the exact native pair cache from copied evidence only."""
    if type(fields) is not dict or not {"events", "masks", "by_event", "_blocks"} <= set(fields):
        raise ValueError("Missing copied Evidence cache or inputs")
    events, masks = fields["events"], fields["masks"]
    if type(events) is not list or type(masks) is not list or len(events) != len(masks):
        raise ValueError("Invalid copied Evidence event/mask lists")
    if any(type(event) is not str for event in events):
        raise ValueError("Invalid copied Evidence event type")
    masks = [_copied_nonnegative_integer(mask) for mask in masks]
    groups = {}
    for index, event in enumerate(events):
        groups.setdefault(event, []).append(index)
    ordered_groups = {"$mapping": "dict", "items": [[event, indices] for event, indices in groups.items()]}
    if not _same_copied_value(fields["by_event"], ordered_groups):
        raise ValueError("Copied Evidence grouping differs from ordered events")
    blocks = []
    for event, indices in groups.items():
        for a in range(len(indices)):
            for b in range(a + 1, len(indices)):
                condition = masks[indices[a]] & masks[indices[b]]
                cover = sum(1 << j for j, mask in enumerate(masks) if condition & mask == condition)
                values = [value if value < 2 ** 53 else {"$integer_decimal": str(value)}
                          for value in (condition, cover)]
                blocks.append({"$tuple": [*values, event]})
    if fields["_blocks"] is not None and not _same_copied_value(fields["_blocks"], blocks):
        raise ValueError("Populated Evidence cache differs from its exact ordered derivation")
    return blocks


def resolve(value, snapshots, *, omit_typed_caches=False, normalize_evidence_caches=False, active=()):
    """Resolve addresses before changing any referenced record's fields."""
    if type(value) is list:
        return [resolve(item, snapshots, omit_typed_caches=omit_typed_caches,
                        normalize_evidence_caches=normalize_evidence_caches, active=active) for item in value]
    if type(value) is not dict:
        return value
    if set(value) == {"$snapshot"}:
        key = value["$snapshot"]
        if key in active or key not in snapshots:
            raise ValueError("Missing or cyclic copied snapshot")
        return resolve(snapshots[key], snapshots, omit_typed_caches=omit_typed_caches,
                       normalize_evidence_caches=normalize_evidence_caches, active=active + (key,))
    out = {key: resolve(item, snapshots, omit_typed_caches=omit_typed_caches,
                        normalize_evidence_caches=normalize_evidence_caches, active=active)
           for key, item in value.items()}
    if omit_typed_caches and out.get("$record") in TYPED_CACHE_FIELDS:
        for name in TYPED_CACHE_FIELDS[out["$record"]]:
            out["fields"].pop(name, None)
    if normalize_evidence_caches and out.get("$record") == EVIDENCE_RECORD:
        out["fields"]["_blocks"] = evidence_pair_blocks(out.get("fields"))
    return out


def learned_view(projection):
    common = {name: value for name, value in projection["common"].items() if name != "snapshots"}
    common = resolve(common, projection["snapshots"], omit_typed_caches=True, normalize_evidence_caches=True)
    for name in ("_cache", "_assigned"):
        common["abstractor"].pop(name)
    common["hypotheses"].pop("_page_instances")
    return {"common": common,
            "stored_key_inventory": projection["stored_key_inventory"],
            "graph_frozen": resolve(projection["graph_frozen"], projection["snapshots"],
                                    omit_typed_caches=True, normalize_evidence_caches=True),
            "graph_policy": projection["graph_policy"],
            "execution_handles": projection["execution_handles"]}


def collection_changes(before, after):
    """Report complete copied-cache differences without discarding either copy."""
    def items(value):
        if type(value) is dict and "$mapping" in value:
            rows = value["items"]
            return [(trace.canonical(key), key, item) for key, item in rows]
        if type(value) is dict and "$set" in value:
            return [(trace.canonical(item), item, item) for item in value["items"]]
        raise ValueError("Expected copied mapping or set")
    left, right = items(before), items(after)
    a, b = {key: item for key, _, item in left}, {key: item for key, _, item in right}
    return {"before_count": len(left), "after_count": len(right),
            "added": [key for token, key, _ in right if token not in a],
            "removed": [key for token, key, _ in left if token not in b],
            "changed": [key for token, key, item in right if token in a and trace.canonical(a[token]) != trace.canonical(item)],
            "old_entry_order_preserved": [key for key, _, _ in left if key in b] == [key for key, _, _ in right if key in a]}


def typed_cache_summary(projection):
    copies = {label + "." + name: [] for label, fields in TYPED_CACHE_FIELDS.items() for name in fields}
    def visit(value):
        if type(value) is list:
            for item in value:
                visit(item)
        elif type(value) is dict:
            label = value.get("$record")
            if label in TYPED_CACHE_FIELDS:
                for name in TYPED_CACHE_FIELDS[label]:
                    if name in value["fields"]:
                        copies[label + "." + name].append(trace.canonical(value["fields"][name]))
            for item in value.values():
                visit(item)
    # Snapshot entries are visited once here; their addresses are not compared.
    visit({**projection, "common": {key: value for key, value in projection["common"].items() if key != "snapshots"}})
    return {name: {"copied_occurrences": len(values), "values_sha256": trace.sha(sorted(values))}
            for name, values in copies.items()}


def evidence_cache_summary(projection):
    """Retain raw cache population/content separately from its normalized value."""
    values = []
    def visit(value):
        if type(value) is list:
            for item in value:
                visit(item)
        elif type(value) is dict:
            if value.get("$record") == EVIDENCE_RECORD:
                fields = resolve(value, projection["snapshots"]).get("fields")
                evidence_pair_blocks(fields)
                values.append(fields["_blocks"])
            for item in value.values():
                visit(item)
    # Visit each stored snapshot payload once, matching typed_cache_summary.
    visit({**projection, "common": {key: value for key, value in projection["common"].items() if key != "snapshots"}})
    return {EVIDENCE_RECORD + "._blocks": {
        "copied_occurrences": len(values),
        "populated_occurrences": sum(value is not None for value in values),
        "values_sha256": trace.sha(sorted(trace.canonical(value) for value in values)),
    }}


class LiveMonitor:
    def __init__(self, fit, raw_records, bindings):
        self.fit = fit
        self.raw_records = trace.plain_snapshot(raw_records)
        self.bindings = bindings
        data = trace.stored(fit)
        self.inducer = data["inducer"]
        self.abstractor = data["abstractor"]
        abstract = trace.stored(self.abstractor)
        self.hypotheses = abstract["H"]
        self.graph = abstract["G"]
        self.vocabulary = abstract["emissions"]
        self.log, self.evidence = data["log"], data["evidence"]
        self.operators = data["operators"]
        self.pid = os.getpid()
        self.interpreted = {key: len(trace.stored(obs)["nodes"])
                            for key, obs in trace.mapping(trace.stored(self.graph)["obs"]).items()}
        self.baseline = None
        self.previous = None
        self.failed = False

    def note_observation(self, observation):
        self.interpreted[public_signature(observation)] = len(observation["nodes"])

    def capture(self):
        common = trace.project_fit(self.fit, raw_records=self.raw_records, primary_steps=[], bindings=self.bindings)
        copier = trace.Copier(self.bindings)
        result = {"schema": "semabi.j1.live_projection.v1", "common": common,
                  "stored_key_inventory": {}, "execution_handles": {}}
        try:
            objects = {"fit": self.fit, "inducer": self.inducer, "abstractor": self.abstractor,
                       "hypotheses": self.hypotheses, "graph": self.graph,
                       "vocabulary": self.vocabulary, "log": self.log, "evidence": self.evidence}
            expected = {
                "fit": set(FIT_FIELDS),
                "inducer": set(trace.INDUCER_FIELDS) | {"A", "log", "transitions", "noops", "operators"},
                "abstractor": set(trace.ABSTRACTOR_FIELDS) | {"G", "H", "parser", "emissions", "cat"},
                "hypotheses": set(trace.HYPOTHESIS_FIELDS) | {"G", "memo"},
                "graph": set(GRAPH_FROZEN + GRAPH_LOOKUPS + GRAPH_MEMOS) | {"judge_by_collection"},
                "vocabulary": {"values", "frozen"},
                "log": {"steps", "observations", "typed_tokens", "dir", "obs_path", "steps_path"},
                "evidence": {"steps", "observations", "typed_tokens", "dir", "obs_path", "steps_path"},
            }
            optional = {"abstractor": {"probe_status", "probe_by_step", "cat"},
                        "hypotheses": {"step_sigs", "reload_pairs", "step_targets", "step_kinds"},
                        "graph": {"judge_by_collection"}}
            for name, obj in objects.items():
                expected_type = self.bindings.types[{"vocabulary": "vocabulary", "evidence": "log"}.get(name, name)]
                if type(obj) is not expected_type:
                    copier.unknown("unexpected_native_object_type", name)
                fields = trace.stored(obj)
                result["stored_key_inventory"][name] = sorted(fields)
                for key in sorted(set(fields) - expected[name]):
                    copier.unknown("unsupported_stored_field", name + "." + key)
                for key in sorted(expected[name] - set(fields) - optional.get(name, set())):
                    copier.unknown("not_stored", name + "." + key)
            model, native = trace.stored(self.fit), trace.stored(self.inducer)
            abstract, hypotheses = trace.stored(self.abstractor), trace.stored(self.hypotheses)
            relationships = {
                "same_pid": os.getpid() == self.pid,
                "fit_inducer": model["inducer"] is self.inducer,
                "fit_abstractor": model["abstractor"] is self.abstractor,
                "fit_log": model["log"] is self.log,
                "fit_evidence": model["evidence"] is self.evidence,
                "fit_operators": model["operators"] is self.operators is native["operators"],
                "inducer_abstractor": native["A"] is self.abstractor,
                "inducer_evidence": native["log"] is self.evidence,
                "abstractor_hypotheses": abstract["H"] is self.hypotheses,
                "shared_graph": abstract["G"] is hypotheses["G"] is self.graph,
                "abstractor_vocabulary": abstract["emissions"] is self.vocabulary,
                "parser_is_none": abstract["parser"] is None,
                "graph_frozen": trace.stored(self.graph)["learning"] is False,
                "emission_frozen": trace.stored(self.vocabulary)["frozen"] is True,
            }
            if "cat" in abstract:
                cat = abstract["cat"]
                relationships["cat_has_no_instance_fields"] = trace.stored(cat) == {}
                relationships["cat_view_controls"] = vars(type(cat)).get("view_controls") is abstract["view_controls"]
            result["ownership"] = relationships
            for name, valid in relationships.items():
                if not valid:
                    copier.unknown("ownership_or_frozen_state_changed", name)
            result["identity_attestation"] = {"pid": self.pid,
                "objects": {name: id(obj) for name, obj in objects.items()},
                "scope": "Strong references and identity checks within this resident process"}
            result["execution_handles"]["abstractor"] = {"parser": None, "cat": "derived view_controls handle" if "cat" in abstract else "absent"}
            for name in ("log", "evidence"):
                fields = trace.stored(objects[name])
                paths = {}
                for key in ("dir", "obs_path", "steps_path"):
                    value = fields[key]
                    if value is not None and type(value) is not type(Path()):
                        copier.unknown("unsupported_execution_path", name + "." + key)
                        paths[key] = {"unsupported": True}
                    else:
                        paths[key] = None if value is None else os.fspath(value)
                result["execution_handles"][name] = paths
            graph = trace.stored(self.graph)
            result["graph_frozen"] = copier.fields(self.graph, GRAPH_FROZEN, "graph")
            result["graph_lookups"] = copier.fields(self.graph, GRAPH_LOOKUPS, "graph")
            result["graph_memos"] = copier.fields(self.graph, GRAPH_MEMOS, "graph")
            class_policy = vars(type(self.graph)).get("judge_by_collection", trace.MISSING)
            result["graph_policy"] = {"class": copier.copy(class_policy, "graph.class.judge_by_collection"),
                "instance_override_present": "judge_by_collection" in graph,
                "instance": copier.copy(graph.get("judge_by_collection", trace.MISSING), "graph.judge_by_collection")}
            if type(class_policy) is not bool or ("judge_by_collection" in graph and type(graph["judge_by_collection"]) is not bool):
                copier.unknown("unsupported_graph_policy", "graph.judge_by_collection")
            result["hypotheses_memo"] = copier.copy(hypotheses["memo"], "hypotheses.memo")
            result["interpretation_caches"] = {
                "abstractor._cache": copier.copy(abstract["_cache"], "abstractor._cache"),
                "abstractor._assigned": copier.copy(abstract["_assigned"], "abstractor._assigned"),
                "hypotheses._page_instances": copier.copy(hypotheses["_page_instances"], "hypotheses._page_instances"),
            }
        except BaseException as error:
            copier.unknown("live_projection_exception:" + type(error).__name__, "live_projection")
        result["snapshots"] = {**common.get("snapshots", {}), **copier.snapshots}
        result["typed_cache_summary"] = typed_cache_summary(result)
        result["incomplete_reasons"] = common.get("incomplete_reasons", []) + copier.errors
        result["status"] = "COMPLETE" if common.get("status") == "COMPLETE" and not result["incomplete_reasons"] else "INCOMPLETE"
        return result

    def checkpoint(self):
        projection = self.capture()
        record = {"schema": "semabi.j1.live_checkpoint.v1", "projection": projection,
                  "instrument_status": "INCOMPLETE", "checks": {}, "changes": {}}
        if projection["status"] != "COMPLETE":
            self.failed = True
            return record
        try:
            learned = learned_view(projection)
            record["derived_cache_summary"] = evidence_cache_summary(projection)
            record["learned_commitment"] = learned
            record["learned_commitment_sha256"] = trace.sha(learned)
            memo = resolve(projection["hypotheses_memo"], projection["snapshots"], omit_typed_caches=True)
            lookups = resolve(projection["graph_lookups"], projection["snapshots"], omit_typed_caches=True)
            if self.baseline is None:
                self.baseline = {"learned": learned, "memo": memo, "lookups": lookups}
            checks = {"complete_projection": True, "no_prior_checkpoint_failure": not self.failed,
                      "learned_commitment_unchanged": trace.canonical(learned) == trace.canonical(self.baseline["learned"])}
            memo_changes = collection_changes(self.baseline["memo"], memo)
            previous_memo = self.baseline["memo"] if self.previous is None else resolve(
                self.previous["hypotheses_memo"], self.previous["snapshots"], omit_typed_caches=True)
            recent_memo = collection_changes(previous_memo, memo)
            def unchanged(change):
                return not change["removed"] and not change["changed"] and change["old_entry_order_preserved"]
            checks["old_memo_entries_unchanged_since_startup"] = unchanged(memo_changes)
            checks["old_memo_entries_unchanged_since_previous_checkpoint"] = unchanged(recent_memo)
            def admitted(key):
                if type(key) is not dict or set(key) != {"$tuple"} or len(key["$tuple"]) != 2:
                    return False
                signature, node = key["$tuple"]
                return type(signature) is str and signature in self.interpreted and type(node) is int and 0 <= node < self.interpreted[signature]
            checks["new_memo_entries_belong_to_interpreted_observations"] = all(admitted(key) for key in memo_changes["added"])
            record["changes"]["hypotheses.memo"] = {"since_startup": memo_changes, "since_previous": recent_memo}
            previous_lookups = self.baseline["lookups"] if self.previous is None else resolve(
                self.previous["graph_lookups"], self.previous["snapshots"], omit_typed_caches=True)
            for name in GRAPH_LOOKUPS:
                change = collection_changes(self.baseline["lookups"][name], lookups[name])
                recent = collection_changes(previous_lookups[name], lookups[name])
                record["changes"]["graph." + name] = {"since_startup": change, "since_previous": recent}
                checks["old_graph_" + name + "_entries_unchanged_since_startup"] = unchanged(change)
                checks["old_graph_" + name + "_entries_unchanged_since_previous_checkpoint"] = unchanged(recent)
                checks["new_graph_" + name + "_entries_belong_to_interpreted_observations"] = all(
                    type(key) is str and key in self.interpreted if name == "obs" else admitted(key)
                    for key in change["added"])
            if self.previous is not None:
                for name, current in projection["interpretation_caches"].items():
                    previous = self.previous["interpretation_caches"][name]
                    record["changes"][name] = collection_changes(
                        resolve(previous, self.previous["snapshots"]), resolve(current, projection["snapshots"]))
                record["changes"]["graph_computed_memos"] = {
                    name: {"changed": trace.canonical(resolve(self.previous["graph_memos"][name], self.previous["snapshots"])) != trace.canonical(resolve(projection["graph_memos"][name], projection["snapshots"]))}
                    for name in GRAPH_MEMOS}
                record["changes"]["typed_interpretation_caches"] = {
                    name: {"before": self.previous["typed_cache_summary"][name], "after": value,
                           "changed": trace.canonical(self.previous["typed_cache_summary"][name]) != trace.canonical(value)}
                    for name, value in projection["typed_cache_summary"].items()}
                previous_caches = evidence_cache_summary(self.previous)
                record["changes"]["derived_evidence_caches"] = {
                    name: {"before": previous_caches[name], "after": value,
                           "changed": not _same_copied_value(previous_caches[name], value)}
                    for name, value in record["derived_cache_summary"].items()}
            record["checks"] = checks
            record["instrument_status"] = "COMPLETE" if all(checks.values()) else "INCOMPLETE"
            self.failed = record["instrument_status"] != "COMPLETE"
            self.previous = projection
        except BaseException as error:
            self.failed = True
            record["error"] = {"type": type(error).__name__, "scope": "Checkpoint copying or comparison failed"}
        return record
