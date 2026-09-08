"""Held callable draft. No loader, native imports, fitting, outcomes, or file writes.

A separately reviewed root driver must supply a real admitted Fit, the unchanged
native referring module, and a fresh authenticated trace.Copier(native_bindings).
The setup receipt is an external trust boundary, not self-authentication.
"""
from copy import copy, deepcopy
import hashlib
import json

SOURCE_HEAD = "b15e6b0a4c2736fabfcb48fbab19981d82b575e8"
INPUT_SHA256 = {
    "observations.jsonl": "c271d8d73229326d558a3790365cd5743d227da5e0ebd93e66b1928848d9c4b9",
    "steps.jsonl": "53ac19a56ed58a852f1bd84468f3b7907f0765252b8501e8a990176325b15452",
}
COHORT = (("06f4a3dad59b9656", 0), ("3821550301c5b69f", 36),
          ("de1da1d18aed05e3", 75), ("5c64d2b807fd478e", 101),
          ("b85b3b735272a749", 153))
RECEIVER_VAR, ACTION_VAR, ACTION_NODE = "?o0", "?o1", 17


class SetupLimit(Exception):
    pass


def need(condition, reason):
    if not condition:
        raise SetupLimit(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def raw_observation(obs):
    """Read stored fields using the existing Observation.to_json field convention."""
    nodes = []
    for node in obs.nodes:
        fields = vars(node)
        row = {key: fields[key] for key in ("i", "parent", "role", "name")}
        row.update({key: fields[key] for key in
                    ("value", "checked", "options", "placeholder", "current")
                    if fields[key] is not None})
        row["bbox"] = list(fields["bbox"])
        nodes.append(row)
    return {"nodes": nodes, "url": obs.url}


def ancestors(nodes, index):
    found = []
    while index >= 0:
        need(index < len(nodes) and index not in found, "invalid_raw_ancestry")
        found.append(index)
        index = nodes[index]["parent"]
    return found


def admitted_owner(state, node_index, tid, raw):
    po = state.parsed
    instance_index = po.node_instance.get(node_index)
    need(type(instance_index) is int and 0 <= instance_index < len(po.instances),
         "missing_or_invalid_parsed_owner")
    instance = po.instances[instance_index]
    need(instance.tid == tid and not instance.positional, "wrong_or_positional_owner_type")
    need(instance.root in ancestors(raw["nodes"], node_index), "owner_is_not_raw_ancestor")
    candidates = [obj for obj in state.objs.values() if obj.node == instance.root]
    need(len(candidates) == 1, "missing_or_ambiguous_native_owner")
    obj = candidates[0]
    identity = (obj.tid, obj.key)
    need(obj.tid == tid and type(obj.key) is str and bool(obj.key) and
         not obj.positional and identity not in state.provisional and
         state.objs.get(identity) is obj, "unusable_native_owner_identity")
    need(sum((other.tid, other.key) == identity for other in state.objs.values()) == 1,
         "ambiguous_native_owner_identity")
    need(not any(row[0] == tid and row[1] == instance.root for row in state.unidentified),
         "unidentified_owner_conflict")
    root = raw["nodes"][instance.root]
    headings = [node for node in raw["nodes"] if node["role"] == "heading" and
                node["parent"] == instance.root and node["name"] == obj.key]
    need(root["name"] == obj.key and len(headings) == 1, "owner_key_not_uniquely_visible_locally")
    return obj, instance


def admit_state(state, raw, op):
    need(state.parsed is not None and raw_observation(state.parsed.obs) == raw,
         "native_state_does_not_match_exact_raw_observation")
    nodes = raw["nodes"]
    need([node["i"] for node in nodes] == list(range(len(nodes))), "noncanonical_node_indices")
    radios = [node for node in nodes if node["role"] == "radio"]
    need(len(radios) == 4, "radio_cohort_membership_changed")
    owners, families, rows = [], set(), []
    for node in radios:
        need(type(node.get("checked")) is bool, "unknown_radio_checked_value")
        obj, instance = admitted_owner(state, node["i"], op.params[RECEIVER_VAR], raw)
        family = state.parsed.node_key.get(node["i"])
        slot_value = instance.slots.get(family)
        need(type(family) is str and bool(family) and
             type(slot_value) is tuple and len(slot_value) == 2 and
             type(slot_value[1]) is bool and slot_value == (node["name"], node["checked"]),
             "radio_family_or_native_slot_disagrees")
        families.add(family)
        if node["checked"]:
            owners.append(obj)
        rows.append({"radio_node": node["i"], "checked": node["checked"],
                     "parsed_family": family, "owner_root": obj.node,
                     "owner_id": [obj.tid, obj.key]})
    need(len(families) == 1, "ambiguous_parsed_radio_family")
    need(len({tuple(row["owner_id"]) for row in rows}) == len(rows), "duplicate_radio_owner")
    need(len(owners) <= 1, "multiple_checked_radios")
    family = next(iter(families))
    need(family not in state.view, "base_source_already_present_no_overwrite")
    need(nodes[ACTION_NODE]["role"] == "button" and
         nodes[ACTION_NODE]["name"] == "Transmit" and
         state.parsed.node_key.get(ACTION_NODE) == "button:Transmit", "action_selector_changed")
    actor, _ = admitted_owner(state, ACTION_NODE, op.params[ACTION_VAR], raw)
    return family, (owners[0] if owners else None), actor, rows


def run_control(*, fit, referring, copier, setup_receipt, training_bytes):
    """Return raw diagnostic data only; root owns subsequent custody and assessment.

    copier must start error-free and use the retained complete record schema.
    Its transition table may be pre-registered by the driver; the admitted
    operator_record_sha256 must use that same registration and canonical codec.
    """
    result = {"schema": "semabi.j1.receiver_view_control.v1", "status": "SETUP_LIMIT",
              "setup_receipt": deepcopy(setup_receipt), "findings": [], "calls": [],
              "binding_scope": "identity-assisted raw-owner diagnostic; not native training positives",
              "assessment": "PENDING_SEPARATE_POST_PRESERVATION_REVIEW"}
    originals, arms, admitted = {}, {"A": {}, "B": {}}, {}
    op = None

    def snap(value, path):
        value = copier.copy(value, path)
        need(not copier.errors, "typed_copy_incomplete")
        return value

    def capture():
        original = {sig: snap(state, "original." + sig) for sig, state in originals.items()}
        identities = {sig: {"state": id(state), "parsed": id(state.parsed), "objs": id(state.objs),
                            "members": [[obj.tid, obj.key, id(obj), id(obj.attrs), id(obj.refs)]
                                        for obj in state.objs.values()]}
                      for sig, state in originals.items()}
        copied = {}
        for arm, states in arms.items():
            copied[arm] = {}
            for sig, state in states.items():
                need(state.objs is originals[sig].objs, "arm_objects_container_replaced")
                masked = copy(state)
                masked.view = {}
                copied[arm][sig] = {"nonview": snap(masked, "masked." + sig),
                                    "view": snap(state.view, "view." + sig)}
        return {"operator": snap(op, "operator"), "operator_identity": id(op),
                "originals": original, "original_identity_tokens": identities, "arms": copied}

    try:
        need(not copier.errors, "incoming_typed_copy_errors")
        need(setup_receipt.get("status") == "ROOT_ADMITTED" and
             setup_receipt.get("source_head") == SOURCE_HEAD, "native_setup_not_admitted")
        for key in ("source_freeze_sha256", "fit_provenance_sha256", "runtime_origin_receipt_sha256",
                    "operator_record_sha256"):
            value = setup_receipt.get(key)
            need(type(value) is str and len(value) == 64 and
                 all(char in "0123456789abcdef" for char in value), "missing_setup_binding:" + key)
        need(set(training_bytes) == set(INPUT_SHA256), "training_file_membership_changed")
        for name, expected in INPUT_SHA256.items():
            need(type(training_bytes[name]) is bytes and
                 hashlib.sha256(training_bytes[name]).hexdigest() == expected, "training_hash:" + name)
        observations = [json.loads(line) for line in training_bytes["observations.jsonl"].splitlines()]
        steps = [json.loads(line) for line in training_bytes["steps.jsonl"].splitlines()]
        by_sig = {row["sig"]: row["obs"] for row in observations}
        need(len(by_sig) == len(observations) == 45 and len(steps) == 312, "training_count_changed")
        need(fit.cut == 312 and len(fit.log.steps) == 312 and fit.inducer is not None,
             "resident_fit_prefix_changed")
        need(bool(fit.operators), "missing_operator")
        op = fit.operators[0]
        core = [act for act in op.acts if act.kind not in ("type", "select", "context")]
        need(op.name == "op0" and op.params == {RECEIVER_VAR: 1, ACTION_VAR: 0} and
             len(core) == 1 and core[0].kind == "click" and core[0].owner == ACTION_VAR and
             core[0].loc.slot == "button:Transmit" and core[0].loc.owner_tid == 0,
             "operator_or_receiver_parameter_changed")
        need(digest(snap(op, "operator")) == setup_receipt["operator_record_sha256"],
             "operator_record_not_admitted")
        cohort_raw, basis = [], []
        for sig, step in COHORT:
            need(steps[step]["step"] == step and steps[step]["before"] == sig and
                 fit.log.steps[step].before == sig and
                 setup_receipt.get("raw_to_normalized_associations", {}).get(sig) == sig,
                 "raw_to_native_association_changed:" + sig)
            need(step in fit.inducer._tracked_before, "missing_stored_native_state:" + sig)
            state, raw = fit.inducer._tracked_before[step], by_sig[sig]
            originals[sig] = state
            try:
                admitted[sig] = admit_state(state, raw, op)
            except SetupLimit as error:
                result["findings"].append({"sig": sig, "reason": str(error)})
            masked_raw = deepcopy(raw)
            for node in masked_raw["nodes"]:
                if node["role"] == "radio":
                    node.pop("checked", None)
            cohort_raw.append(digest(masked_raw))
            basis.append(snap({key: value for key, value in vars(state).items() if key != "parsed"}, "basis"))
        need(not result["findings"], "inadmissible_owner_setup_no_injection")
        need(len(set(cohort_raw)) == 1 and all(value == basis[0] for value in basis),
             "cohort_differs_beyond_raw_checked_fields")
        need(len({item[0] for item in admitted.values()}) == 1 and
             sum(item[1] is not None for item in admitted.values()) == 4 and
             admitted[COHORT[0][0]][1] is None, "checked_cohort_or_family_changed")
        need(len({(item[2].tid, item[2].key) for item in admitted.values()}) == 1,
             "action_owner_differs_across_cohort")
        original_before = capture()["originals"]
        result["observations"] = []
        for sig, _ in COHORT:
            state, (family, owner, actor, rows) = originals[sig], admitted[sig]
            guards = {}
            need(all(type(slot) is str for slot in state.view), "nonstring_view_key")
            for arm in arms:
                cloned = copy(state)
                cloned.parsed, cloned.view = copy(state.parsed), dict(state.view)
                cloned.parsed._member_positioned_cache = {}
                arms[arm][sig] = cloned
                guards[arm] = {slot: referring._member_positioned(cloned, slot)
                               for slot in sorted(set(state.view) | {family})}
            need(guards["A"] == guards["B"], "guard_disagrees_between_identical_copies")
            if owner is not None:
                arms["B"][sig].view[family] = owner.key
            result["observations"].append({"sig": sig, "radios": rows, "guard_results": guards,
                "action_owner_id": [actor.tid, actor.key], "family": family,
                "added_B_field": None if owner is None else {"slot": family, "value": owner.key}})
        before = capture()
        need(before["originals"] == original_before, "guard_mutated_original_state")
        need(all(before["arms"]["A"][sig]["nonview"] == before["arms"]["B"][sig]["nonview"]
                 for sig, _ in COHORT), "arm_metadata_inequivalence")
        result["before"] = before
        candidates = {}
        for arm in arms:
            evidence = [(arms[arm][sig], {RECEIVER_VAR: admitted[sig][1]})
                        for sig, _ in COHORT if admitted[sig][1] is not None]
            candidates[arm] = referring._selection_queries(op, RECEIVER_VAR, evidence)
            result["calls"].append({"kind": "_selection_queries", "arm": arm, "returned": candidates[arm]})
            need(capture() == before, "native_selection_call_mutated_inputs:" + arm)
        for slot in sorted(set(candidates["A"]) | set(candidates["B"])):
            query = referring.Query(referring.SELECTION, RECEIVER_VAR, "control view selection", form=(slot,))
            for arm in arms:
                for sig, _ in COHORT:
                    hits = query.denotation(op, arms[arm][sig], {ACTION_VAR: admitted[sig][2]})
                    result["calls"].append({"kind": "Query.denotation", "arm": arm, "sig": sig,
                        "query": snap(query, "query"), "candidate_origins": [key for key in arms if slot in candidates[key]],
                        "returned": snap(hits, "denotation"), "object_ids": [[obj.tid, obj.key] for obj in hits]})
                    need(capture() == before, "native_denotation_call_mutated_inputs")
        result["after"] = capture()
        result["status"] = "CONTROL_CAPTURED"
    except SetupLimit as error:
        result["findings"].append({"reason": str(error)})
        if result["calls"] or arms["A"]:
            result["status"] = "CONTROL_INCOMPLETE"
    except Exception as error:
        result["status"] = "CONTROL_INCOMPLETE"
        result["findings"].append({"exception_type": type(error).__name__, "message": str(error)})
    if op is not None and originals:
        try:
            result["final_state"] = capture()
        except Exception as error:
            result["findings"].append({"final_copy_error": type(error).__name__ + ":" + str(error)})
    result["typed_copy_errors"] = deepcopy(copier.errors)
    result["typed_snapshots"] = deepcopy(copier.snapshots)
    return result
