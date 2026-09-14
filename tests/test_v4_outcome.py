"""The outcome model: an ordered list of guarded answers, and what it refuses to say."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from semabi.compiler.v4 import outcome as oc


@dataclass
class Obj:
    tid: int
    key: str
    attrs: dict = field(default_factory=dict)
    refs: dict = field(default_factory=dict)
    parent: Any = None

    @property
    def id(self):
        return (self.tid, self.key)


@dataclass
class State:
    objs: dict
    view: dict = field(default_factory=dict)


class FakeInducer:
    """Just enough of the inducer for the learner: a literal language and a type table."""

    class A:
        types = {}

    def _literals(self, _op, tr):
        lits = set()
        for role, oid in tr.binding.items():
            o = tr.before.objs.get(oid)
            if o is None:
                continue
            for slot, value in o.attrs.items():
                lits.add(("attr", role, slot, value))
        return lits


@pytest.mark.parametrize("silent", [False, True])
def test_response_fitting_uses_the_observed_state_without_revising_effect_beliefs(monkeypatch, silent):
    """Checks a fresh query updates local fields correctly while leaving prior belief
    and delayed-effect records intact, using an object with different local and
    maintained values."""
    from copy import deepcopy
    from types import SimpleNamespace
    from semabi.compiler.abstract import Diff, TypeInfo

    inducer = FakeInducer()
    inducer.A = SimpleNamespace(types={0: TypeInfo(0, key_slot="id"),
                                      1: TypeInfo(1, key_slot="id", refs={"in:0": 0})})
    rows, local = [], {}
    for index, (quantity, capacity, event) in enumerate([
            (3, 5, "accepted"), (4, 6, "accepted"),
            (8, 5, "refused"), (9, 6, "refused")]):
        owner = Obj(0, "same target", {"quantity": str(quantity), "response": None})
        related = Obj(1, "same resource", {"capacity": str(capacity)}, {"in:0": owner.id})
        state = State({owner.id: owner, related.id: related})
        local[index] = state
        belief = deepcopy(state)
        belief.objs[owner.id].attrs["response"] = "old response" if event == "accepted" else None
        belief.objs[related.id].attrs["capacity"] = "100"
        effect = Diff([], [], [(owner.id, "quantity", "2", "3")], [], {},
                      attr_revisions=[(owner.id, "response", "old", None)])
        transition = SimpleNamespace(before=belief, d=effect, emission=SimpleNamespace(args=()))
        step = SimpleNamespace(before=index, action=SimpleNamespace(target=0))
        rows.append((transition, step, state, None if silent else event))
    original_beliefs = deepcopy([row[0].before for row in rows])
    original_effects = deepcopy([row[0].d for row in rows])
    inducer.state = local.__getitem__
    monkeypatch.setattr(oc, "_owner", lambda _a, obs, _step: obs.objs[(0, "same target")])
    monkeypatch.setattr(oc, "roles_of", lambda *_: {oc.OWNER: oc.Role(oc.OWNER, "action", (), 0)})
    models = {}
    oc._learn_controls(inducer, inducer.A, None, {"button:Act": rows}, {}, {}, models,
                       {0: {"quantity": ["3", "4", "8", "9"]},
                        1: {"capacity": ["5", "6"]}}, None,
                       permute=None, subject_restricted=False, structural=False,
                       touched=False, about=False, simplest=False)
    got = models["button:Act"]
    for index, state in local.items():
        owner = state.objs[(0, "same target")]
        bound, status = got.bind(state, owner)
        query = oc.query_literals(SimpleNamespace(inducer=inducer), got, state, bound, status)
        fitted = {literal for literal, bit in got.evidence.index.items()
                  if got.evidence.masks[index] & (1 << bit)}
        assert fitted == {literal for literal in query
                          if got.evidence.refuse is None or not got.evidence.refuse(literal)}
        assert ("attr", oc.OWNER, "response", None) in query
        assert not any("old response" in literal or "100" in literal for literal in query)
    assert [row[0].before for row in rows] == original_beliefs
    assert [row[0].d for row in rows] == original_effects
    if not silent:
        assert all(set(shapes) == {(("set", "quantity"),)} for shapes in got.deltas.values())


@pytest.mark.parametrize("partial", [False, True])
def test_response_language_distinguishes_global_emptiness_from_observed_null_reference(partial):
    from types import SimpleNamespace
    from semabi.compiler.abstract import AbstractState, AbsObj, TypeInfo
    from semabi.compiler.induce import Inducer

    owner = AbsObj(0, "target", {"state": "available"}, refs={"resource": None})
    state = AbstractState({owner.id: owner}, {}, partial=partial)
    inducer = Inducer(SimpleNamespace(types={0: TypeInfo(0, key_slot="id")}), None)
    literals = oc._literals(inducer, state, {oc.OWNER: owner}, {oc.OWNER: "named"})
    assert (("empty", oc.OWNER) in literals) is not partial
    assert ("ref_null", oc.OWNER, "resource") in literals
    assert ("attr", oc.OWNER, "state", "available") in literals


def test_semantic_training_input_digest_rejects_same_length_evidence_substitution():
    from copy import deepcopy
    from types import SimpleNamespace
    from semabi.compiler.browser import Primitive
    from semabi.compiler.evidence import Step
    from semabi.compiler.observation import Node, Observation
    from semabi.compiler.semantic import training_evidence_digest

    before = Observation([Node(0, -1, 'group', ''), Node(1, 0, 'textbox', 'Quantity', value='1')])
    after = Observation([Node(0, -1, 'group', ''), Node(1, 0, 'textbox', 'Quantity', value='2')])
    log = SimpleNamespace(steps=[Step(0, 0, Primitive('type', 1, '2'), True, None, 'a', 'b', ['2'])],
                          observations={'a': before, 'b': after})
    digest = training_evidence_digest(log)
    assert training_evidence_digest(deepcopy(log)) == digest
    changed_action = deepcopy(log)
    changed_action.steps[0].action = Primitive('type', 1, '3')
    changed_observation = deepcopy(log)
    changed_observation.observations['b'].node(1).value = '3'
    standalone_read = deepcopy(log)
    standalone_read.observations['c'] = Observation([Node(0, -1, 'heading', 'Another record')])
    for different in (changed_action, changed_observation, standalone_read):
        assert len(different.steps) == len(log.steps)
        assert training_evidence_digest(different) != digest

def _fit_cache_log(tmp_path):
    from semabi.compiler.browser import Primitive
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.observation import Node, Observation
    log = EvidenceLog(tmp_path / 'training')
    before = Observation([Node(0, -1, 'group', ''), Node(1, 0, 'button', 'Inspect')])
    log.add_step(0, Primitive('click', 1), True, None, before, before)
    return log


def test_semantic_fit_cache_roundtrip_uses_exact_inputs_and_keeps_original_cost(tmp_path, monkeypatch):
    import json
    from semabi.compiler import semantic
    log = _fit_cache_log(tmp_path)
    original = semantic.fit_semantics(log.dir)
    frozen = json.loads(json.dumps(original.to_json()))
    monkeypatch.setattr(semantic.consequence, 'fit', lambda *args, **kwargs:
                        pytest.fail('exact cache hit must not fit'))
    restored = semantic.reuse_semantics(log.dir, frozen)
    assert restored is not None
    assert restored.operations() == original.operations()
    assert restored.metadata['fit_seconds'] == original.metadata['fit_seconds']
    assert restored.metadata['fit_provenance'] == original.metadata['fit_provenance']
    assert restored.metadata['fit_reuse_seconds'] >= 0
    assert 'fit_reuse_seconds' not in original.metadata
    assert semantic.reuse_semantics(log.dir, {**frozen, 'metadata': {
        key: value for key, value in frozen['metadata'].items() if key != 'fit_provenance'}}) is None
    assert semantic.reuse_semantics(log.dir, frozen, recipe={**semantic.FIT_RECIPE, 'min_support': 3}) is None
    # A new standalone observation is input even if actions and their count agree.
    from semabi.compiler.observation import Node, Observation
    log.add_observation(Observation([Node(0, -1, 'heading', 'New evidence')]))
    assert semantic.reuse_semantics(log.dir, frozen) is None


def test_archived_sampling_observation_does_not_become_a_fitted_transition_view(tmp_path):
    """Checks an unready sample gets archived without being used as a fitting
    endpoint."""
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.observation import Node, Observation
    from semabi.compiler.semantic import fit_semantics

    log = _fit_cache_log(tmp_path)
    baseline = fit_semantics(log.dir)
    sample = Observation([Node(0, -1, "group", ""),
                          Node(1, 0, "heading", "Unready-only schema"),
                          Node(2, 0, "textbox", "Unready-only field", value="Unready-only value")])
    signature = log.add_observation(sample)
    fitted = fit_semantics(log.dir)
    assert signature in EvidenceLog(log.dir).observations
    assert signature not in fitted.abstractor.G.obs
    assert fitted.metadata["representation_revision"] == baseline.metadata["representation_revision"]
    assert fitted.operations() == baseline.operations()
    assert fitted.metadata["fit_provenance"] != baseline.metadata["fit_provenance"]


@pytest.mark.parametrize('sidecar', ['probes.jsonl', 'probes.acquired.jsonl', 'field_theories_v4.json'])
def test_semantic_fit_cache_sidecar_content_and_absence_are_inputs(tmp_path, sidecar):
    import json
    from semabi.compiler import semantic
    log = _fit_cache_log(tmp_path)
    original = semantic.fit_semantics(log.dir).to_json()
    path = log.dir / sidecar
    path.write_text('{}\n' if sidecar.endswith('jsonl') else '{"theories": []}')
    assert semantic.reuse_semantics(log.dir, original) is None
    present = semantic.fit_semantics(log.dir).to_json()
    assert semantic.reuse_semantics(log.dir, json.loads(json.dumps(present))) is not None
    path.write_text(path.read_text() + '\n')
    assert semantic.reuse_semantics(log.dir, present) is None
    path.unlink()
    assert semantic.reuse_semantics(log.dir, present) is None
    assert semantic.reuse_semantics(log.dir, original) is not None


@pytest.mark.parametrize('mutated', ['steps.jsonl', 'observations.jsonl', 'probes.jsonl',
                                    'probes.acquired.jsonl', 'field_theories_v4.json'])
def test_semantic_fit_uses_private_snapshot_and_rejects_changed_origin(tmp_path, monkeypatch, mutated):
    from pathlib import Path
    from semabi.compiler import semantic
    log = _fit_cache_log(tmp_path)
    for name in semantic.FIT_INPUT_FILES[2:]:
        (log.dir / name).write_text('{}\n')
    captured = semantic.capture_fit_inputs(log.dir)
    actual_fit = semantic.consequence.fit
    bundles = []

    def change_origin(directory, *args, **kwargs):
        bundles.append(Path(directory))
        assert Path(directory) != log.dir
        assert semantic.capture_fit_inputs(directory) == captured
        (log.dir / mutated).write_bytes((captured[mutated] or b'') + b'\n')
        assert semantic.capture_fit_inputs(directory) == captured
        return actual_fit(directory, *args, **kwargs)

    monkeypatch.setattr(semantic.consequence, 'fit', change_origin)
    with pytest.raises(ValueError, match='inputs changed'):
        semantic.fit_semantics(log.dir)
    assert bundles and all(not directory.exists() for directory in bundles)


def test_semantic_fit_code_boundary_excludes_only_workflow_and_includes_relmodel(tmp_path, monkeypatch):
    from semabi.compiler import semantic
    root = tmp_path / 'semabi' / 'compiler'
    root.mkdir(parents=True)
    for name in ['runtime.py', 'semantic_runtime.py', 'surface.py', 'browser_session.py',
                 'semantic.py', 'browser.py', 'observation.py', 'evidence.py']:
        (root / name).write_text('original')
    (root / 'v4').mkdir()
    for name in ['fields.py', 'binding.py']:
        (root / 'v4' / name).write_text('original')
    (root.parent / 'relmodel.py').write_text('original')
    original = semantic.fit_source_hashes(root)
    for name in ['runtime.py', 'semantic_runtime.py', 'surface.py', 'browser_session.py']:
        (root / name).write_text('changed procedure')
        assert semantic.fit_source_hashes(root) == original
    for path in [root / 'v4' / 'fields.py', root / 'v4' / 'binding.py',
                 root / 'semantic.py', root.parent / 'relmodel.py']:
        path.write_text('changed semantics')
        assert semantic.fit_source_hashes(root) != original
        path.write_text('original')
    log = _fit_cache_log(tmp_path)
    artifact = semantic.fit_semantics(log.dir).to_json()
    changed = {**semantic.LOADED_FIT_SOURCE, 'compiler/v4/fields.py': 'new process source'}
    monkeypatch.setattr(semantic, 'LOADED_FIT_SOURCE', changed)
    monkeypatch.setattr(semantic, 'fit_source_hashes', lambda: changed)
    assert semantic.reuse_semantics(log.dir, artifact) is None
    monkeypatch.setattr(semantic, 'fit_source_hashes', lambda: {})
    with pytest.raises(ValueError, match='source changed'):
        semantic.reuse_semantics(log.dir, artifact)


def _state(**vats):
    return State({(1, k): Obj(1, k, dict(a)) for k, a in vats.items()})


ROLE = oc.Role("source", oc.referring.SINGLETON, (), 1)


def _occasions(rows):
    """rows: (attrs, event, args)."""
    return [(_state(v=attrs), None, event, args) for attrs, event, args in rows]


def test_it_learns_a_guard_and_puts_the_rest_in_the_default():
    rows = [({"gate": "open"}, "drew", ("v",)) for _ in range(4)]
    rows += [({"gate": "closed"}, "refused", ("v",)) for _ in range(4)]
    got = oc.learn_control(FakeInducer(), "c", _occasions(rows), {"source": ROLE})
    assert got.fitted == 8
    state = _state(v={"gate": "closed"})
    bound, status = got.bind(state, None)
    assert got.predict(oc._literals(FakeInducer(), state, bound, status)) == "refused"
    state = _state(v={"gate": "open"})
    bound, status = got.bind(state, None)
    assert got.predict(oc._literals(FakeInducer(), state, bound, status)) == "drew"


def test_an_ordered_list_expresses_a_guard_chain_that_a_rule_set_cannot():
    """Checks the first failing guard wins, so a later rule never needs to restate
    the first condition, since the evidence never shows the combination that would
    require it."""
    rows = [({"gate": "closed", "dest": "bottled"}, "closed", ())] * 3
    rows += [({"gate": "closed", "dest": "open"}, "closed", ())] * 3
    rows += [({"gate": "open", "dest": "bottled"}, "bottled", ())] * 3
    rows += [({"gate": "open", "dest": "open"}, "drew", ())] * 3
    got = oc.learn_control(FakeInducer(), "c", _occasions(rows), {"source": ROLE})
    for attrs, expected in (({"gate": "closed", "dest": "bottled"}, "closed"),
                            ({"gate": "closed", "dest": "open"}, "closed"),
                            ({"gate": "open", "dest": "bottled"}, "bottled"),
                            ({"gate": "open", "dest": "open"}, "drew")):
        state = _state(v=attrs)
        bound, status = got.bind(state, None)
        assert got.predict(oc._literals(FakeInducer(), state, bound, status)) == expected


def test_it_says_it_does_not_know_rather_than_answering_with_the_commonest():
    """Two events that nothing in the state separates: the list ends undetermined."""
    rows = [({"gate": "open"}, "drew", ())] * 5 + [({"gate": "open"}, "refused", ())] * 3
    got = oc.learn_control(FakeInducer(), "c", _occasions(rows), {"source": ROLE})
    state = _state(v={"gate": "open"})
    bound, status = got.bind(state, None)
    assert got.predict(oc._literals(FakeInducer(), state, bound, status)) == oc.UNDETERMINED


def test_a_condition_fitted_to_one_occasion_is_not_a_rule():
    rows = [({"gate": "open"}, "drew", ())] * 6 + [({"gate": "sealed"}, "odd", ())]
    got = oc.learn_control(FakeInducer(), "c", _occasions(rows), {"source": ROLE})
    assert all(r.event != "odd" for r in got.rules)


def test_whether_a_role_names_anything_is_itself_a_condition():
    """Cellar's commonest refusal is that a selection names no object."""
    rows = [(_state(v={"gate": "open"}), None, "drew", ()) for _ in range(4)]
    rows += [(State({}), None, "nothing chosen", ()) for _ in range(4)]
    got = oc.learn_control(FakeInducer(), "c", rows, {"source": ROLE})
    bound, status = got.bind(State({}), None)
    assert got.predict(oc._literals(FakeInducer(), State({}), bound, status)) == "nothing chosen"


def test_arguments_are_roles_and_not_the_values_they_took_while_fitting():
    rows = [(_state(v={"gate": "closed"}), None, "refused <>", ("v",)) for _ in range(3)]
    got = oc.learn_control(FakeInducer(), "c", rows, {"source": ROLE})
    assert got.arg_roles == {"refused <>": {0: "source"}}
    state = State({(1, "w"): Obj(1, "w", {"gate": "closed"})})
    bound, _ = got.bind(state, None)
    assert got.arguments("refused <>", bound) == {0: "w"}


def test_the_owners_own_relations_are_roles_even_where_no_effect_named_them():
    # A run page contains its carrier and refers to a depot; a control whose only
    # answer is a message has no operator variable for either, so the reading's own
    # relations supply them, anchored on the owner.
    from collections import Counter
    from semabi.compiler.abstract import TypeInfo
    types = {0: TypeInfo(0, refs={"rel:5": 5}), 2: TypeInfo(2, refs={"in:0": 0}),
             5: TypeInfo(5), 7: TypeInfo(7, refs={"in:2": 2}), 8: TypeInfo(8, parent_tids=Counter({0: 2}))}
    A = type("A", (), {"types": types})()
    roles = oc.relation_roles(A, 0)
    assert sorted(roles) == ["relation['backward', 'in:0']:2<owner", "relation['forward', 'rel:5']:5<owner",
                             "relation['parent', '']:8<owner"]
    assert all(r.anchor == oc.OWNER and r.kind == "relation" and r.path for r in roles.values())
    assert roles["relation['backward', 'in:0']:2<owner"].form == ("backward", "in:0")
    assert oc.relation_roles(A, None) == {}


def test_a_path_role_enters_the_language_only_through_comparisons():
    from semabi.compiler.abstract import AbsObj, AbstractState
    owner = AbsObj(0, "Cedar", {"attr:weight#0": "10"}, node=1)
    van = AbsObj(2, "Panel", {"attr:limit#0": "14", "attr:colour#0": "white"}, refs={"in:0": owner.id}, node=4)
    state = AbstractState({owner.id: owner, van.id: van}, {})

    class Inducer:
        A = type("A", (), {"types": {}})()

        def _literals(self, op, tr):
            return {("attr", "owner", "attr:weight#0", "10"), ("attr", "van", "attr:colour#0", "white"),
                    ("ref", "van", "in:0", "owner"), ("ref_set", "van", "in:0")}

    binding, status = {"owner": owner, "van": van}, {"owner": "named", "van": "named"}
    ordered = {0: {"attr:weight#0": ["7", "10"]}, 2: {"attr:limit#0": ["8", "14"]}}
    every = oc._literals(Inducer(), state, binding, status, None, ordered, None)
    paths = oc._literals(Inducer(), state, binding, status, None, ordered, None, frozenset({"van"}))
    assert ("attr", "van", "attr:colour#0", "white") in every and ("named", "van") in every
    assert not any("van" in lit[1:] and lit[0] not in ("attr_cmp_ge", "attr_cmp_lt", "attr") for lit in paths)
    assert {lit for lit in paths if lit[0] == "attr" and lit[1] == "van"} == {("attr", "van", "attr:limit#0", "14")}
    assert ("attr_cmp_ge", "van", "attr:limit#0", "owner", "attr:weight#0") in paths
    assert ("attr", "owner", "attr:weight#0", "10") in paths and ("named", "owner") in paths


def test_categorical_path_limit_survives_duplicate_aliases_without_new_evidence():
    """Checks adding a second path to the same resource doesn't let a categorical
    distinction become representable without new evidence."""
    from dataclasses import replace
    from semabi.compiler.abstract import AbsObj, AbstractState
    roles = {oc.OWNER: oc.Role(oc.OWNER, 'action', (), 0),
             'resource': oc.Role('resource', oc.referring.RELATION, ('forward', 'assigned'),
                                 1, oc.OWNER, path=True)}
    occasions = []
    for i in range(8):
        available = i % 2 == 0
        owner = AbsObj(0, f'owner{i}', {}, node=0)
        resource = AbsObj(1, f'resource{i % 3}', {'availability': 'ready' if available else 'busy'},
                          refs={'in:0': owner.id}, node=1)
        owner.refs['assigned'] = resource.id
        state = AbstractState({o.id: o for o in (owner, resource)}, {})
        occasions.append((state, owner, 'Allowed <>' if available else 'Blocked <>', (resource.key,)))
    ordinary = oc.learn_control(FakeInducer(), 'Check', occasions, roles)
    aliased = oc.learn_control(FakeInducer(), 'Check', occasions,
                              {**roles, 'duplicate': oc.Role('duplicate', oc.referring.RELATION,
                                                           ('backward', 'in:0'), 1, oc.OWNER, path=True)})

    def answer(model):
        state, owner = occasions[0][:2]
        bound, status = model.bind(state, owner)
        literals = oc._literals(FakeInducer(), state, bound, status, paths=oc._paths(model.roles))
        return model.predict(literals), set(model.admissible(literals, corroborated=True, hypothesis=oc.LIST))

    assert answer(ordinary) == (oc.UNDETERMINED, set())
    assert isinstance(aliased.roles['duplicate'], oc.Alias)
    assert answer(aliased) == (oc.UNDETERMINED, set())
    assert ordinary.fitted == aliased.fitted == len(occasions)
    # A full-capability role can still learn this task; this is a supplied-language
    # control, not evidence that comparison-only paths learn it.
    full_roles = {name: replace(role, path=False) for name, role in roles.items()}
    full = oc.learn_control(FakeInducer(), 'Check', occasions, full_roles)
    full_alias = oc.learn_control(FakeInducer(), 'Check', occasions,
                                 {**full_roles, 'duplicate': oc.Role('duplicate', oc.referring.RELATION,
                                                                   ('backward', 'in:0'), 1, oc.OWNER)})
    assert answer(full) == answer(full_alias) == ('Allowed <>', {'Allowed <>'})


def test_local_relationship_witness_does_not_require_global_membership_absence():
    from dataclasses import replace
    from semabi.compiler.abstract import AbsObj, AbstractState

    owner = AbsObj(0, "record", {}, node=1)
    old = AbsObj(1, "old", {"capacity": "4"}, refs={"in:0": owner.id}, node=None)
    current = AbsObj(1, "current", {"capacity": "4"}, refs={"in:0": owner.id}, node=5)
    state = AbstractState({o.id: o for o in (owner, old, current)}, {})
    path = oc.Role("resource", oc.referring.RELATION, ("backward", "in:0"), 1,
                   anchor=oc.OWNER, path=True)
    model = oc.ControlOutcome("check", roles={oc.OWNER: oc.Role(oc.OWNER, "action", (), 0), "resource": path})
    bound, status = model.bind(state, owner)
    assert bound["resource"] is current and status["resource"] == "named"
    assert state.objs[old.id].refs["in:0"] == owner.id, "local reading must not erase a belief"

    # Two visible members with equal values are two possible targets, not one witness.
    old.node = 6
    assert model.bind(state, owner)[1]["resource"] == "ambiguous"
    old.node = current.node = None
    assert model.bind(state, owner)[1]["resource"] == "unnamed"
    # An ordinary persistent relation query still sees the unresolved alternatives.
    assert len(replace(path, path=False).denotation(state, {oc.OWNER: owner})) == 2


def test_raw_categorical_relationship_is_observed_but_not_in_current_path_language():
    """Checks structure/fields/containment are fitted normally, while the
    categorical distinction needs the full-role language, supplied here rather than
    learned."""
    from dataclasses import replace
    from semabi.compiler.observation import Node, Observation
    from semabi.compiler.v2.graph import ObsGraph
    from semabi.compiler.v2.hypotheses import Hypotheses
    from semabi.compiler.v4.abstractor import V4Abstractor

    def page(owner, resources):
        nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'group', ''),
                 Node(2, 1, 'heading', 'Task ' + owner), Node(3, 1, 'button', 'Check')]
        for name, state in resources:
            root = len(nodes)
            nodes.extend([Node(root, 1, 'group', ''), Node(root + 1, root, 'heading', 'Resource ' + name),
                          Node(root + 2, root, 'text', 'Availability'), Node(root + 3, root, 'text', state)])
        return Observation(nodes)

    # Every owner and related name occurs under both outcomes; no spelling, ordering,
    # or constant numeric threshold can supply the categorical distinction.
    rows = [(owner, [(resource, category)]) for owner in ('Alpha', 'Beta', 'Gamma')
            for resource in ('Cedar', 'Elm', 'Oak') for category in ('Ready', 'Busy')]
    coverage = [(owner, []) for owner in ('Alpha', 'Beta', 'Gamma')]
    coverage += [(owner, [('Cedar', 'Ready'), ('Elm', 'Ready')]) for owner in ('Alpha', 'Beta', 'Gamma')]
    graph = ObsGraph()
    for owner, resources in [*rows, *coverage]:
        obs = page(owner, resources)
        graph.add(obs.structural_signature(), obs)
    hypothesis = Hypotheses(graph)
    hypothesis.fit()
    abstractor = V4Abstractor(graph, hypothesis)
    occasions = []
    for owner_name, resources in rows:
        state = abstractor.abstract(page(owner_name, resources))
        owner = next(obj for obj in state.objs.values() if obj.node == 1)
        resource = next(obj for obj in state.objs.values() if obj.node == 4)
        assert resource.refs == {'in:' + str(owner.tid): owner.id}
        assert resources[0][1] in resource.attrs.values()
        occasions.append((state, owner, 'Allowed <>' if resources[0][1] == 'Ready' else 'Blocked <>',
                          (resource.key,)))
    roles = {oc.OWNER: oc.Role(oc.OWNER, 'action', (), owner.tid),
             **oc.relation_roles(abstractor, owner.tid)}
    path_name, path = next((name, role) for name, role in roles.items() if name != oc.OWNER)
    assert len(roles) == 2 and path.path
    supplied = {name: replace(role, path=False) for name, role in roles.items()}
    variants = {
        'no_relation': {oc.OWNER: roles[oc.OWNER]},
        'one_path': roles,
        'duplicate_path': {**roles, 'alias': replace(path, name='alias')},
        'supplied_categories': supplied,
        'supplied_categories_alias': {**supplied, 'alias': replace(path, name='alias', path=False)},
    }
    models = {name: oc.learn_control(FakeInducer(), 'Check', occasions, language)
              for name, language in variants.items()}
    assert isinstance(models['duplicate_path'].roles['alias'], oc.Alias)
    assert {model.fitted for model in models.values()} == {18}, 'aliases do not add independent occasions'
    for category, expected in [('Ready', 'Allowed <>'), ('Busy', 'Blocked <>')]:
        state = abstractor.abstract(page('New', [('Fresh', category)]))
        owner = next(obj for obj in state.objs.values() if obj.node == 1)
        for name, model in models.items():
            bound, status = model.bind(state, owner)
            literals = oc._literals(FakeInducer(), state, bound, status, paths=oc._paths(model.roles))
            answer = model.predict(literals)
            assert answer == (expected if name.startswith('supplied_categories') else oc.UNDETERMINED)
    # Equal projected categories do not make two displayed objects a unique witness.
    for resources, expected in [([], 'unnamed'), ([('Fresh', 'Ready')], 'named'),
                                ([('Fresh', 'Ready'), ('Other', 'Ready')], 'ambiguous'),
                                ([('Fresh', 'Ready'), ('Other', 'Busy')], 'ambiguous')]:
        state = abstractor.abstract(page('New', resources))
        owner = next(obj for obj in state.objs.values() if obj.node == 1)
        assert models['one_path'].bind(state, owner)[1][path_name] == expected


def test_response_verification_checks_actual_known_branch_not_the_point_prediction():
    from types import SimpleNamespace
    from semabi.compiler.observation import Node, Observation
    from semabi.compiler.semantic import SemanticArtifact
    from semabi.compiler.v4.emission import Vocabulary

    def page(text):
        return Observation([Node(0, -1, "group", ""), Node(1, 0, "text", "A"),
                            Node(2, 0, "text", "B"), Node(3, 0, "button", "Commit"),
                            Node(4, 0, "status", text)])

    before = page("Waiting")
    model = oc.ControlOutcome("commit", events={"Accepted <>": 3, "Declined <>": 3},
                              arg_roles={"Accepted <>": {0: oc.OWNER}, "Declined <>": {0: oc.OWNER}})
    artifact = SemanticArtifact(SimpleNamespace(emissions=Vocabulary([before])), {"commit": model}, {})
    prediction = {"control": "commit", "point": "Accepted <>",
                  "bindings": {oc.OWNER: {"type": 1, "key": "A"}}}
    observed = artifact.verify_response(before, page("Declined A"), 3, "commit", prediction=prediction)
    assert observed["verified"], "a surprising known application refusal is still an observable result"
    wrong = artifact.verify_response(before, page("Declined B"), 3, "commit", prediction=prediction)
    assert wrong["recognized"] and not wrong["verified"]
    assert wrong["argument_disagreements"]["0"] == {"expected": "A", "observed": "B"}
    assert not artifact.verify_response(before, page("Novel A"), 3, "commit", prediction=prediction)["verified"]
    assert not artifact.verify_response(before, before, 3, "commit", prediction=prediction)["verified"]


def test_product_semantic_artifact_roundtrip_keeps_live_relational_language(monkeypatch):
    """Checks fitting raw observations, carrying semantics, and querying fresh pages
    keeps the relational language intact. This is a persistence check, not
    application evidence."""
    import copy
    import json
    from pathlib import Path
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.semantic import SemanticArtifact, fit_semantics, reuse_semantics
    from semabi.compiler.v4 import consequence

    root = Path(__file__).resolve().parents[1]
    training = root / "docs/data/v4/transport/p43/falls2_1702"
    evaluation = root / "docs/data/v4/transport/first_pass/dispatch/evaluation_v2"
    original = fit_semantics(training)

    def forbidden(*args, **kwargs):
        raise AssertionError("loading/invocation must not refit")

    monkeypatch.setattr(consequence, "fit", forbidden)
    reused = reuse_semantics(training, json.loads(json.dumps(original.to_json())))
    assert reused is not None, "ordinary cache reuse must preserve the fitted relational language"
    assert reused.metadata['fit_provenance'] == original.metadata['fit_provenance']
    restored = SemanticArtifact.from_json(json.loads(json.dumps(reused.to_json())))
    operation = next(op for op in restored.operations() if op["comparison"])
    control = operation["control"]
    training_model = original.outcomes[control]
    evidence = training_model.evidence
    assert len(evidence.occasion_obs) == len(evidence.events) == 15
    for index, page in evidence.occasion_obs.items():
        controls = [node.i for node in page.nodes if original.control_at(page, node.i) == control]
        assert len(controls) == 1
        prepared = original.prepare(page)
        state = original.abstract(prepared)
        owner = consequence._owner_object(original.abstractor, original.abstractor.parsed(prepared),
                                          state, controls[0])
        bound, status = training_model.bind(state, owner)
        query = oc.query_literals(original, training_model, state, bound, status)
        allowed = {literal for literal in query if evidence.refuse is None or not evidence.refuse(literal)}
        fitted = {literal for literal, bit in evidence.index.items()
                  if evidence.masks[index] & (1 << bit)}
        assert fitted == allowed, f"occasion {index} used features unavailable in its own raw observation"
    log = EvidenceLog(evaluation)
    calls, supported, changed = 0, 0, 0
    ambiguous_steps = []
    simulated = False
    for step in log.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        page = log.obs(step.before)
        if original.control_at(page, step.action.target) != control:
            continue
        calls += 1
        expected = original.predict(page, step.action.target)
        actual = restored.predict(page, step.action.target)
        assert actual == expected
        supported += actual["status"] == "supported"
        if actual["status"] == "supported":
            observed = original.observe(page, log.obs(step.after), control)["event"]
            assert observed is not None and set(actual["alternatives"]) == {observed["frame"]}
        elif actual["status"] == "ambiguous":
            ambiguous_steps.append(step.step)
        if not simulated:
            editables = restored.relevant_editables(page, step.action.target)
            assert editables, "the learned comparison must expose its actual editable source"
            editable = editables[0]
            assert editable["value"] == page.node(editable["node"]).value
            assert editable["provenance"][0]["field_node"] == editable["node"]
            before_signature = page.structural_signature()
            hypothetical = restored.simulate_edit(page, step.action.target, editable["node"], "999")
            assert hypothetical["status"] == "represented"
            assert hypothetical["owner_preserved"]
            assert hypothetical["application_effect"] == "not executed"
            assert hypothetical["prediction"]["point"] != actual["point"]
            assert page.structural_signature() == before_signature
            assert restored.predict(page, step.action.target) == actual
            assert restored.owner_at(page, step.action.target)["key"] == actual["owner"]["key"]
            # The response region is never an editable source, even if it says the
            # same value as a learned field.
            from semabi.compiler.v4 import emission
            for status_node in emission.live_nodes(page):
                assert restored.simulate_edit(page, step.action.target, status_node, "999")["status"] == "unavailable"
            simulated = True
        model = restored.outcomes[control]
        ablated = copy.copy(model)
        ablated.pairs = frozenset()
        restored.outcomes[control] = ablated
        missing_comparison = restored.predict(page, step.action.target)
        restored.outcomes[control] = model
        changed += (missing_comparison["point"], missing_comparison["alternatives"]) != (
            actual["point"], actual["alternatives"])
        # Repeated notices are not fresh evidence of a response, even if predicted.
        assert restored.observe(page, page, control)["changed"] is False
    # Local-feature parity removes carried list-only attributes from all training rows.
    # Two additional rival outcomes survive; that's an expected coverage regression,
    # not restored certainty from unseen prior beliefs.
    assert calls == 8 and supported == 5
    assert ambiguous_steps == [14, 24, 29]
    assert changed > 0, "the learned comparison must change an operational prediction"
    assert simulated
    assert {key: value for key, value in restored.metadata.items() if key != 'fit_reuse_seconds'} == original.metadata
    assert restored.metadata['fit_reuse_seconds'] >= 0


def _acquisition_page(features, response=None):
    from semabi.compiler.observation import Node, Observation
    nodes = [Node(0, -1, 'group', ''), Node(1, 0, 'text', ' '.join(sorted(features))),
             Node(2, 0, 'button', 'Act')]
    if response is not None:
        nodes.append(Node(3, 0, 'status', response))
    return Observation(nodes)


def _acquisition_artifact(rows):
    """Supplies a finite feature language; the actual acquisition bookkeeping engine
    is tested, not ontology fitting."""
    from collections import Counter
    from types import SimpleNamespace
    from semabi.compiler.semantic import SemanticArtifact
    from semabi.compiler.v4.emission import Vocabulary
    artifact = SemanticArtifact.__new__(SemanticArtifact)
    got = oc.ControlOutcome('act', events=dict(Counter(event for _, event in rows)))
    got.evidence = oc.Evidence([({('feature', feature) for feature in features}, event, frozenset())
                                for features, event in rows])
    artifact.outcomes = {'act': got}
    artifact.metadata = {'representation_revision': 'finite-test-language'}
    artifact.abstractor = SimpleNamespace(emissions=Vocabulary())
    artifact.control_at = lambda obs, node: 'act'
    artifact.queries = []

    def predict(obs, node):
        artifact.queries.append(obs.structural_signature())
        literals = {('feature', feature) for feature in obs.node(1).name.split()}
        options = got.admissible(literals, corroborated=True, hypothesis=oc.LIST)
        return {'control': 'act', 'owner': {'node': 1, 'key': 'Target'},
                'status': 'supported' if len(options) == 1 and not next(iter(options.values())).sole
                          else 'ambiguous' if options else 'unavailable',
                'alternatives': {event: {'condition': list(witness.condition), 'sole': witness.sole}
                                 for event, witness in options.items()}}

    artifact.predict = predict
    return artifact


def test_acquisition_distinguishes_competing_outcomes_from_other_barriers():
    rows = [({'p'}, 'Ready')] * 3 + [({'q', 'r'}, 'Unavailable')] * 3
    artifact = _acquisition_artifact(rows)
    page = _acquisition_page({'p', 'q', 'r'})
    assert artifact.acquisition_opportunity(page, 2)['kind'] == 'RIVAL_OUTCOMES'
    assert artifact.acquisition_opportunity(page, 2)['eligible']
    empty = _acquisition_artifact([])
    assert empty.acquisition_opportunity(page, 2)['kind'] == 'NO_ADMISSIBLE_INTERPRETATION'
    assert not empty.acquisition_opportunity(page, 2)['eligible']

    prediction = artifact.predict(page, 2)
    artifact.predict = lambda obs, node: {**prediction, 'owner': None}
    assert artifact.acquisition_opportunity(page, 2)['kind'] == 'UNBOUND_TARGET'
    artifact.predict = lambda obs, node: prediction
    artifact.simulate_edit = lambda *args: {'status': 'unavailable', 'reason': 'field not represented'}
    assert artifact.acquisition_opportunity(page, 2, editable_node=1, value='12')['kind'] == 'UNREPRESENTED_INTERVENTION'
    artifact.predict = lambda obs, node: {**prediction, 'alternatives': {'Ready': {'sole': True}}}
    assert artifact.acquisition_opportunity(page, 2)['kind'] == 'INSUFFICIENT_CORROBORATION'
    artifact.predict = lambda obs, node: {**prediction, 'status': 'supported', 'alternatives': {'Ready': {'sole': False}}}
    assert artifact.acquisition_opportunity(page, 2)['kind'] == 'AGREED_OUTCOME'


@pytest.mark.parametrize('features,expected', [({'p'}, {'Ready'}), ({'fresh'}, set())])
def test_incomplete_search_propagates_through_actual_prediction_answer_and_offline_score(monkeypatch, features, expected):
    from types import SimpleNamespace
    from semabi.compiler.semantic import SemanticArtifact
    from semabi.compiler.v4 import consequence
    artifact = _acquisition_artifact([({'p'}, 'Ready')] * 3 + [({'q'}, 'Unavailable')] * 3)
    page, after = _acquisition_page(features), _acquisition_page(features, 'Ready')
    owner = SimpleNamespace(id=(1, 'Target'), tid=1, key='Target', node=0,
                            positional=False, attrs={}, refs={})
    state = SimpleNamespace(objs={owner.id: owner}, view={})
    artifact.prepare = lambda obs: obs
    artifact.abstract = lambda obs: state
    artifact.abstractor.parsed = lambda obs: None
    artifact.abstractor.abstract = lambda obs: state
    artifact.predict = SemanticArtifact.predict.__get__(artifact)
    monkeypatch.setattr(consequence, '_owner_object', lambda *args: owner)
    monkeypatch.setattr(consequence, 'clicked_control', lambda *args: 'act')
    query = {('feature', feature) for feature in features}
    monkeypatch.setattr(oc, 'query_literals', lambda *args: query)
    monkeypatch.setattr(oc, '_pending_literals', lambda *args: query)
    monkeypatch.setattr(oc, 'LIST_SEARCH_BUDGET', 0)
    predicted = artifact.predict(page, 2)
    assert predicted['status'] == 'unavailable'
    assert predicted['alternatives_complete'] is False
    assert set(predicted['alternatives']) == expected
    got = artifact.outcomes['act']
    answered = got.answer(state, owner)
    assert answered.status == oc.SEARCH_INCOMPLETE and set(answered.outcomes) == expected
    assert not answered.search.complete
    opportunity = artifact.acquisition_opportunity(page, 2)
    assert opportunity['kind'] == 'SEARCH_INCOMPLETE' and not opportunity['eligible']
    model = SimpleNamespace(abstractor=artifact.abstractor, outcomes=artifact.outcomes,
                            log=SimpleNamespace(obs=lambda key: page if key == 'pre' else after))
    step = SimpleNamespace(step=0, before='pre', after='post', action=SimpleNamespace(target=2))
    score = oc.score_step_admissible(model, step, corroborated=True, hypothesis=oc.LIST)
    assert score['verdict'] == oc.SEARCH_INCOMPLETE
    assert set(score['admissible']) == expected and score['alternatives_complete'] is False
    model.log.obs = lambda key: after
    repeated = oc.score_step_admissible(model, step, corroborated=True, hypothesis=oc.LIST)
    assert repeated['verdict'] == oc.SEARCH_INCOMPLETE
    assert repeated['response_changed'] is False
    assert 'no distinguishable response effect' in repeated['response_observation']


def test_incomplete_acquisition_comparison_reports_found_sets_not_eliminated_rivals(monkeypatch):
    from copy import deepcopy
    page, after = _acquisition_page({'p', 'q'}), _acquisition_page({'p', 'q'}, 'Ready')
    old = _acquisition_artifact([({'p'}, 'Ready')] * 3 + [({'q'}, 'Unavailable')] * 3)
    new = _acquisition_artifact([({'p'}, 'Ready')] * 3)
    previous_prediction = old.predict(page, 2)
    previous_prediction['alternatives_complete'] = True
    current_prediction = deepcopy(previous_prediction)
    current_prediction.update(status='unavailable', alternatives_complete=False)
    current_prediction['alternatives'].pop('Unavailable')
    old.predict = lambda *args: previous_prediction
    new.predict = lambda *args: current_prediction
    changed = new.acquisition_change(old, page, after, 2)
    assert not changed['searches_complete'] and not changed['rival_outcome_elimination']
    assert changed['removed_outcomes'] is None and changed['added_outcomes'] is None
    assert changed['found_set_differences']['missing_after'] == ['Unavailable']
    assert changed['no_admissible_interpretation'] is None
    assert changed['remaining_ambiguity'] is None
    assert not changed['predictive_alternatives_reduced'] and not changed['false_certainty']


def test_inadequacy_does_not_call_an_unsearched_ordered_outcome_inseparable():
    from semabi.eval.v4_inadequacy import classify
    g, h, j, c = [('attr', 'r', key, 'yes') for key in 'ghjc']
    facts = [({g, j}, 'X', frozenset()), ({g, h}, 'X', frozenset()),
             ({h, c}, 'X', frozenset()), ({j}, 'X', frozenset())] + [({c}, 'Y', frozenset())] * 3
    got = oc.ControlOutcome('act', evidence=oc.Evidence(facts))
    kind, detail = classify(got, got.evidence._mask({c}), 'Y', search_budget=0)
    assert kind == oc.SEARCH_INCOMPLETE and detail['search']['checks'] == 0


def test_acquisition_does_not_count_a_changed_short_clause_as_rival_elimination():
    rows = [({'p'}, 'Ready')] * 3 + [({'q', 'r'}, 'Unavailable')] * 3
    previous = _acquisition_artifact(rows)
    question = _acquisition_page({'p', 'q', 'r'})
    short = previous.predict(question, 2)['alternatives']['Unavailable']['condition']
    attempted = {'p'} | {literal[1] for literal in short}
    assert attempted < {'p', 'q', 'r'}
    before, after = _acquisition_page(attempted), _acquisition_page(attempted, 'Ready')
    current = _acquisition_artifact(rows + [(attempted, 'Ready')])
    change = current.acquisition_change(previous, before, after, 2, question=question)
    assert change['before']['outcomes'] == change['after']['outcomes'] == ['Ready', 'Unavailable']
    assert current.predict(question, 2)['alternatives']['Unavailable']['condition'] != short
    assert change['remaining_ambiguity'] and not change['rival_outcome_elimination']
    assert not change['removed_outcomes']
    assert change['observation_consistent_with_current_prediction'] is None
    assert previous.queries[-1] == current.queries[-1] == question.structural_signature()


def test_acquisition_tracks_exact_question_resolution_novelty_and_unconfirmed_responses():
    rows = [({'p'}, 'Ready')] * 3 + [({'q', 'r'}, 'Unavailable')] * 3
    features = {'p', 'q', 'r'}
    before, after = _acquisition_page(features), _acquisition_page(features, 'Ready')
    previous = _acquisition_artifact(rows)
    current = _acquisition_artifact(rows + [(features, 'Ready')])
    change = current.acquisition_change(previous, before, after, 2)
    assert change['rival_outcome_elimination'] and not change['remaining_ambiguity']
    assert change['removed_outcomes'] == ['Unavailable']
    assert change['observation_consistent_with_current_prediction'] is True
    unchanged = current.acquisition_change(previous, after, after, 2)
    assert unchanged['observation_consistent_with_current_prediction'] is None
    assert not unchanged['observed']['current_model']['changed']

    novel = _acquisition_artifact(rows + [(features, 'Queued')])
    discovery = novel.acquisition_change(previous, before, _acquisition_page(features, 'Queued'), 2)
    assert discovery['additional_observed_frame']
    assert discovery['observed']['previous_model']['event']['frame'] == 'Queued'
    assert discovery['no_admissible_interpretation']
    assert not discovery['remaining_ambiguity'] and not discovery['false_certainty']


def test_acquisition_qualifies_changed_control_or_response_interpretation():
    from copy import deepcopy
    rows = [({'p'}, 'Ready')] * 3 + [({'q', 'r'}, 'Unavailable')] * 3
    features = {'p', 'q', 'r'}
    before, after = _acquisition_page(features), _acquisition_page(features, 'Ready')
    previous = _acquisition_artifact(rows)
    current = _acquisition_artifact(rows + [(features, 'Ready')])
    original_prediction = current.predict
    current.predict = lambda obs, node: {**original_prediction(obs, node), 'control': 'other-act'}
    current.control_at = lambda obs, node: 'other-act'
    current.outcomes['other-act'] = current.outcomes.pop('act')
    change = current.acquisition_change(previous, before, after, 2)
    assert change['question_matches_action'], 'both models still interpret the same raw occurrence'
    assert not change['same_control'] and not change['rival_outcome_elimination']
    assert change['removed_outcomes'] == ['Unavailable'], 'raw set changes remain visible'

    current = _acquisition_artifact(rows + [(features, 'Ready')])
    observe = current.observe

    def reinterpret(*args):
        observed = deepcopy(observe(*args))
        observed['event'].update(frame='<>', args=['Ready'])
        return observed

    current.observe = reinterpret
    change = current.acquisition_change(previous, before, after, 2)
    assert change['same_control'] and change['response_interpretation_changed']
    assert not change['rival_outcome_elimination']


@pytest.mark.parametrize('component', ['roles', 'ordered', 'pairs', 'defaults'])
def test_acquisition_qualifies_fitted_primitive_changes_separately_from_reduced_predictions(component):
    rows = [({'p'}, 'Ready')] * 3 + [({'q', 'r'}, 'Unavailable')] * 3
    features = {'p', 'q', 'r'}
    before, after = _acquisition_page(features), _acquisition_page(features, 'Ready')
    previous = _acquisition_artifact(rows)
    current = _acquisition_artifact(rows + [(features, 'Ready')])
    changes = {'roles': {'related': oc.Role('related', 'singleton', (), 1)},
               'ordered': {0: {'attr:load': ('1', '2', '3')}},
               'pairs': frozenset(), 'defaults': {'selection': 'Initial'}}
    setattr(current.outcomes['act'], component, changes[component])
    # Tests bookkeeping at the artifact boundary using finite feature observations,
    # not discovery of the supplied extra primitives.
    change = current.acquisition_change(previous, before, after, 2)
    assert change['before']['outcomes'] == ['Ready', 'Unavailable']
    assert change['after']['outcomes'] == ['Ready']
    assert change['predictive_alternatives_reduced']
    assert change['fitted_language_changes'] == [component]
    assert not change['rival_outcome_elimination']
    assert change['observation_consistent_with_current_prediction'] is True
