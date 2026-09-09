"""V4's abstractor boundary for retained compiler evidence.

The V2 abstractor remains frozen.  Ordinary live ``EvidenceLog`` objects retain the V2
implementation, while a retained V4 log supplies already parsed probe records so this
adapter never reopens ``probes.jsonl`` (or any other path) during compilation.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from semabi.compiler.abstract import AbstractState
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import affordance_key
from semabi.compiler.observation import Observation
from semabi.compiler.parse import Instance
from semabi.compiler.v2.abstractor import V2Abstractor


class V4Abstractor(V2Abstractor):
    """V2 domain semantics with V4 view evidence and retained probe inputs."""

    def abstract(self, obs: Observation) -> AbstractState:
        state = super().abstract(obs)
        po = state.parsed
        groups: dict[str, list] = defaultdict(list)
        for node in obs.nodes:
            key = po.node_key.get(node.i)
            if node.role == "radio" and isinstance(key, str) and key:
                groups[key].append(node)
        by_root: dict[tuple[int, int], list] = defaultdict(list)
        for obj in state.objs.values():
            by_root[obj.tid, obj.node].append(obj)
        unidentified = {(tid, root) for tid, root, *_ in state.unidentified}
        for key, members in groups.items():
            if (key in state.view or len(members) < 2
                    or any(type(node.checked) is not bool for node in members)
                    or sum(node.checked for node in members) != 1):
                continue
            owners = []
            for node in members:
                index = po.node_instance.get(node.i)
                if type(index) is not int or not 0 <= index < len(po.instances):
                    break
                inst = po.instances[index]
                if (not isinstance(inst, Instance) or type(inst.root) is not int
                        or not 0 <= inst.root < len(obs.nodes)
                        or inst.root not in [node.i, *obs.ancestors(node.i)]
                        or inst.positional or (inst.tid, inst.root) in unidentified):
                    break
                matches = by_root.get((inst.tid, inst.root), [])
                if len(matches) != 1:
                    break
                owner = matches[0]
                identity = inst.slots.get("id")
                if (not isinstance(identity, tuple) or len(identity) != 2
                        or not isinstance(identity[1], str) or not identity[1]
                        or identity[1] != owner.key or owner.positional
                        or owner.id in state.provisional
                        or state.objs.get(owner.id) is not owner):
                    break
                # Selection queries match by key prefix.  Validate every owner against
                # all objects of its type, including objects outside this radio group.
                if any(other is not owner and other.tid == owner.tid
                       and (owner.key.startswith(other.key)
                            or other.key.startswith(owner.key))
                       for other in state.objs.values()):
                    break
                owners.append(owner)
            if (len(owners) != len(members)
                    or len({owner.id for owner in owners}) != len(owners)):
                continue
            state.view[key] = next(owner.key for node, owner in zip(members, owners)
                                   if node.checked)
        return state

    def fit_view_controls(self, log: EvidenceLog) -> None:
        # Live/development logs have no retained record graph and keep the exact V2 path.
        probe_records = getattr(log, "probe_records", None)
        if probe_records is None:
            super().fit_view_controls(log)
            return

        # This is the frozen V2 implementation below.  The only input difference is that
        # retained probe JSONL was parsed by frozen_evidence.from_bytes before this method
        # was called; no pathname or filesystem operation is permitted on this branch.
        probe_status: dict[str, set[str]] = defaultdict(set)
        probe_by_step: dict[int, dict] = {}
        probe_by_key: dict[tuple, list[dict]] = defaultdict(list)
        for j in probe_records:
            if "step" in j:
                probe_by_step[int(j["step"])] = j
            for sensing_step in j.get("sensing_steps", []):
                probe_by_step[int(sensing_step)] = {
                    "status": "VIEW",
                    "controlled": True,
                    "kind": "DIAGNOSTIC_SURVEY_SENSING_STEP",
                    "originating_probe_step": j.get("step"),
                    "component_id": j.get("component_id"),
                }
            k = tuple(j["key"])
            probe_by_key[k].append(j)
            if len(k) >= 3 and k[0] == "click" and k[1] == "button":
                probe_status[k[2]].add(j["status"])
            for sensing in j.get("sensing_actions", []):
                sensing_key = tuple(sensing["key"])
                sensing_record = {
                    **sensing,
                    "controlled": True,
                    "kind": "DIAGNOSTIC_SURVEY_SENSING_STEP",
                    "originating_probe_step": j.get("step"),
                    "component_id": j.get("component_id"),
                }
                probe_by_step[int(sensing["step"])] = sensing_record
                probe_by_key[sensing_key].append(sensing_record)
                if (len(sensing_key) >= 3 and sensing_key[0] == "click"
                        and sensing_key[1] == "button"):
                    probe_status[sensing_key[2]].add("VIEW")
        # A controlled persistence result also supplies evidence for earlier occurrences of
        # the exact same compiler-visible affordance key.  Keep the originating probe step
        # and scope explicit; DOMAIN dominates, while VIEW is generalized only when every
        # matching probe is VIEW.
        for step in log.steps:
            if step.step in probe_by_step or step.action.target is None:
                continue
            try:
                key = affordance_key(log.obs(step.before), step.action)
            except (IndexError, KeyError):
                continue
            candidates = probe_by_key.get(key, [])
            if not candidates:
                continue
            scoped = []
            for candidate in candidates:
                identity = candidate.get("identity") or {}
                source_template = identity.get("source_template")
                source_slot = identity.get("source_slot")
                if not source_template or not source_slot:
                    scoped.append(candidate)
                    continue
                applies = any(
                    ui.template == source_template and any(
                        sid.rstrip("~") == source_slot and node == step.action.target
                        for sid, node in ui.slot_nodes.items()
                    )
                    for ui in self.H.parse_units(step.before)
                )
                if applies:
                    scoped.append(candidate)
            candidates = scoped
            if not candidates:
                continue
            selected = next((x for x in candidates if x.get("status") == "DOMAIN"), None)
            if selected is None and all(x.get("status") == "VIEW" for x in candidates):
                selected = candidates[-1]
            if selected is None:
                selected = candidates[-1]
            inherited = dict(selected)
            inherited["evidence_scope"] = "matching_local_affordance"
            inherited["originating_probe_step"] = selected.get("step")
            inherited["applies_to_step"] = step.step
            probe_by_step[step.step] = inherited
        self.probe_status = probe_status
        self.probe_by_step = probe_by_step
        domain_names = {n for n, st in probe_status.items() if "DOMAIN" in st}
        view_names = {n for n, st in probe_status.items() if st == {"VIEW"}}
        changed: Counter = Counter()
        clicked: Counter = Counter()
        in_unit: Counter = Counter()  # button label -> occurrences inside a unit instance
        total: Counter = Counter()
        for sig, obs in list(log.observations.items())[:300]:
            po = self.parsed(obs)
            for n in obs.nodes:
                if n.role == "button" and n.name:
                    total[n.name] += 1
                    if n.i in po.node_instance:
                        in_unit[n.name] += 1
        mostly_in_unit = {n for n, c in in_unit.items() if c > 0.5 * total[n]}
        for s in log.steps:
            if s.action.kind != "click" or not s.action.target_desc or s.action.target is None:
                continue
            name = s.action.target_desc.get("name")
            before = log.obs(s.before)
            po = self.parsed(before)
            if not name or s.action.target in po.node_instance or name in mostly_in_unit:
                continue
            a, b = self.abstract(before), self.abstract(log.obs(s.after))
            clicked[name] += 1
            common = set(a.objs) & set(b.objs)
            diff = any(
                a.objs[k].attrs.get(x) != b.objs[k].attrs.get(x)
                and a.objs[k].attrs.get(x) is not None
                and b.objs[k].attrs.get(x) is not None
                for k in common for x in a.objs[k].attrs
            ) or any(
                a.objs[k].refs.get(x) != b.objs[k].refs.get(x)
                and x in a.objs[k].refs and x in b.objs[k].refs
                for k in common for x in a.objs[k].refs
            )
            changed[name] += diff
        heuristic = {n for n, c in clicked.items() if changed[n] <= 0.1 * c}
        self.verified_view_controls = view_names - domain_names
        self.verified_domain_controls = domain_names
        self.heuristic_view_controls = heuristic - domain_names
        # Consistency under a collapsed abstraction is not evidence that an action is
        # sensing-only: that exact fallback hid successful domain actions on blind apps.
        # Only executed reload/survey probes can certify the control used by the inducer.
        # Heuristic candidates remain available for intervention selection and provenance.
        self.view_controls = set(self.verified_view_controls)
        self.cat = type("Cat", (), {"view_controls": self.view_controls})()
