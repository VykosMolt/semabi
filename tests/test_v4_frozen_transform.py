"""Tests that a fitted model does not learn anything further from held-out pages.

A held-out evaluation is only prospective if the model reading a held-out page is the
one the prefix produced. Scoping the evidence log is not enough: the abstractor's
observation graph accumulates corpus statistics that decide which text is a value rather
than a label, so reading the suffix could quietly teach the model the vocabulary it is
about to be judged with.

A frozen model can read a new observation without being changed by it: a position the
prefix never established stays unknown rather than becoming known. These tests do not
establish that the prefix model is good, only that its held-out answers are ones it
could have given before seeing that evidence.
"""
from __future__ import annotations

import pytest

from semabi.compiler.observation import Node, Observation
from semabi.compiler.v2.graph import ObsGraph


def page(*rows: str, table: bool = True) -> Observation:
    """A one-table page whose single column carries ``rows`` as cell texts."""
    nodes = [Node(0, -1, "main", "")]
    if table:
        nodes.append(Node(1, 0, "table", ""))
        parent = 1
    else:
        parent = 0
    i = len(nodes)
    for text in rows:
        nodes.append(Node(i, parent, "row", ""))
        nodes.append(Node(i + 1, i, "cell", text))
        i += 2
    return Observation(nodes)


def fitted(*observations: Observation) -> ObsGraph:
    """A graph that has learned from ``observations`` and is then frozen."""
    G = ObsGraph()
    for k, obs in enumerate(observations):
        G.add(f"p{k}", obs)
    G.data_set()             # resolve the vocabulary the prefix justifies
    G.learning = False
    return G


def vocabulary(G: ObsGraph) -> dict:
    """Everything the graph would later consult as evidence about text."""
    return {"data": set(G.data_set()), "templates": set(G.templates),
            "templates_v": set(G.templates_v), "whole": set(G._whole),
            "nonwidget": set(G._in_nonwidget),
            "header_strings": {k: set(v) for k, v in G.header_strings.items()}}


# ------------------------------------------------------------------ the boundary itself

def test_a_frozen_graph_reads_a_new_observation_without_learning_its_vocabulary():
    """Reading a held-out page can add tokens to the data vocabulary that the prefix
    never saw, changing the model itself, independent of whether it changed any reading.
    """
    G = fitted(page("Berth 1", "Berth 2"), page("Berth 3", "Berth 4"))
    before = vocabulary(G)

    G.add("suffix", page("livestock", "130"))

    assert vocabulary(G) == before, "reading a held-out page changed what the model knows"
    assert "livestock" not in G.data_set()
    assert G.obs["suffix"] is not None                     # but it was read
    assert ("suffix", 3) in G.nodes                        # per-observation structure arrived
    assert ("suffix", 3) in G.position_of


def test_the_same_page_does_move_a_graph_that_is_still_learning():
    """Checks that the test above exercises the actual defect and not a no-op accessor.
    """
    G = fitted(page("Berth 1", "Berth 2"), page("Berth 3", "Berth 4"))
    before = vocabulary(G)
    G.learning = True                                      # the historical behaviour

    G.add("suffix", page("livestock", "130"))

    assert vocabulary(G) != before
    assert G._whole > before["whole"]


def test_reading_the_same_held_out_page_twice_learns_nothing_the_second_time():
    G = fitted(page("Berth 1", "Berth 2"), page("Berth 3", "Berth 4"))
    G.add("suffix", page("livestock", "130"))
    once = vocabulary(G)
    nodes_once = dict(G.nodes)

    G.add("suffix", page("livestock", "130"))

    assert vocabulary(G) == once
    assert G.nodes == nodes_once


# ------------------------------------------------------------------ unknown is not absence

def test_a_position_the_prefix_never_established_stays_unknown_rather_than_becoming_known():
    """Novelty in the suffix may reduce what the frozen model knows, never add to it.
    A frozen graph has no template for a position the prefix never saw, so ``is_prose``
    answers False rather than inventing evidence from the page being read.
    """
    def note(text):
        return Observation([Node(0, -1, "main", ""), Node(1, 0, "paragraph", text)])

    # Each note is two words, so the branch that judges a position from its own text alone
    # cannot fire; only accumulated variation at the position can make it prose.
    suffix = [("s0", note("berth closed")), ("s1", note("harbour busy")),
              ("s2", note("quay idle"))]
    prefix = page("Berth 1", "Berth 2")

    G = fitted(prefix)
    for sig, obs in suffix:
        G.add(sig, obs)
    assert G.position_of[("s0", 1)] not in G.templates      # unknown, not stocked from the suffix
    assert G.is_prose("s0", 1) is False

    learning = fitted(prefix)
    learning.learning = True
    for sig, obs in suffix:
        learning.add(sig, obs)
    assert learning.position_of[("s0", 1)] in learning.templates
    assert learning.is_prose("s0", 1) is True               # evidence invented from the suffix


def test_a_future_only_column_does_not_join_the_header_vocabulary():
    """A new *feature* may not enter the schema even though a new *value* is ordinary."""
    G = fitted(page("Berth 1"), page("Berth 2"))
    before = {k: set(v) for k, v in G.header_strings.items()}

    G.add("suffix", page("Berth 3"))                       # known column, new value: fine
    assert {k: set(v) for k, v in G.header_strings.items()} == before

    wide = Observation([Node(0, -1, "main", ""), Node(1, 0, "table", ""),
                        Node(2, 1, "row", ""), Node(3, 2, "cell", "Berth"),
                        Node(4, 2, "cell", "Tonnage")])
    G.add("wide", wide)
    assert {k: set(v) for k, v in G.header_strings.items()} == before
    assert ("wide", 4) in G.header                         # still readable as a header cell


# ------------------------------------------------------------------ what the future cannot do

def test_two_different_futures_leave_the_same_frozen_model():
    """Suffix replacement invariance, at the graph the schema is derived from."""
    prefix = [page("Berth 1", "Berth 2"), page("Berth 3", "Berth 4")]
    a, b = fitted(*prefix), fitted(*prefix)
    assert vocabulary(a) == vocabulary(b)

    a.add("f", page("livestock", "130"))
    b.add("f", page("Berth 5", "Berth 6"))
    b.add("g", Observation([Node(0, -1, "main", ""), Node(1, 0, "paragraph", "a wholly new view")]))

    assert vocabulary(a) == vocabulary(b), "the model depends on which future it was shown"


def test_reading_order_cannot_change_what_a_frozen_model_learned():
    prefix = [page("Berth 1", "Berth 2")]
    forward, backward = fitted(*prefix), fitted(*prefix)
    suffix = [("s0", page("livestock")), ("s1", page("130")), ("s2", page("Berth 9"))]
    for sig, obs in suffix:
        forward.add(sig, obs)
    for sig, obs in reversed(suffix):
        backward.add(sig, obs)
    assert vocabulary(forward) == vocabulary(backward)


# ------------------------------------------------------------------ the real pipeline

def _ownership_page(value="10", names=("Alpha", "Bravo"), header="Item", status=""):
    nodes = [Node(0, -1, "group", ""), Node(1, 0, "button", "Save"),
             Node(2, 0, "textbox", "Amount", value), Node(3, 0, "table", ""),
             Node(4, 3, "row", ""), Node(5, 4, "cell", header)]
    for name in names:
        i = len(nodes)
        nodes.extend([Node(i, 3, "row", ""), Node(i + 1, i, "cell", name)])
    nodes.append(Node(len(nodes), 0, "status", status))
    return Observation(nodes)


def _ownership_log(tmp_path):
    from semabi.compiler.browser import Primitive
    from semabi.compiler.evidence import EvidenceLog

    log = EvidenceLog(tmp_path / "ownership")
    first = _ownership_page()
    typed = _ownership_page("20")
    saved = _ownership_page("20", status="Saved Alpha.")
    for before, action, after in (
        (first, Primitive("reload"), first),
        (first, Primitive("type", 2, "20"), typed),
        (typed, Primitive("click", 1), saved),
        (saved, Primitive("reload"), typed),
    ):
        log.add_step(0, action, True, None, before, after)
    return log


def _promotion_page(names):
    return Observation([Node(0, -1, "group", ""), Node(1, 0, "button", "Add item"),
                        Node(2, 0, "group", "")] +
                       [Node(i + 3, 2, "text", name) for i, name in enumerate(names)])


def _promotion_log(tmp_path):
    from semabi.compiler.browser import Primitive
    from semabi.compiler.evidence import EvidenceLog

    log = EvidenceLog(tmp_path / "promotion")
    first = _promotion_page(("Larch", "Birch"))
    expanded = _promotion_page(("Larch", "Birch", "Cedar"))
    log.add_step(0, Primitive("reload"), True, None, first, first)
    log.add_step(0, Primitive("click", 1), True, None, first, expanded)
    return log


def _learned_reading(A):
    from copy import deepcopy

    return deepcopy((vocabulary(A.G), A.types, A.emissions.values, A.controls))


@pytest.mark.parametrize("branch", ["inferred", "pinned", "legacy"])
def test_v4_selected_graph_reads_unseen_pages_without_changing_the_reading(tmp_path, branch):
    from semabi.compiler.compile_v4 import compile_v4
    from semabi.compiler.v4.pinned import from_search

    log = _ownership_log(tmp_path)
    source = compile_v4(log.dir, write_diagnostics=False)
    assert source.v4.promoted == []
    kwargs = {}
    if branch == "pinned":
        kwargs["pinned"] = from_search(source.v4, log.dir)
    elif branch == "legacy":
        kwargs["identity"] = {t: u.key_slot for t, u in source.hypotheses.units.items()}
    compiled = source if branch == "inferred" else compile_v4(
        log.dir, write_diagnostics=False, **kwargs)
    A = compiled.abstractor.freeze()
    before = _learned_reading(A)
    assert A.G.header_strings and A.emissions.values
    known = [(A.abstract(obs), A.control_family(obs)) for obs in compiled.log.observations.values()]
    unseen = _ownership_page("fresh value", ("Cedar", "Dune"), header="Future column",
                             status="Saved Cedar.")
    sig = unseen.structural_signature()
    assert sig not in A.G.obs and sig not in A.H.G.obs

    A.parsed(unseen)                    # historically raised KeyError in H.parse_units
    assert 1 in A.control_family(unseen)
    A.abstract(unseen)

    assert A.G is A.H.G
    assert A.G.learning is False and A.emissions.frozen
    assert A.G.obs[sig] is unseen and (sig, 2) in A.G.nodes
    assert _learned_reading(A) == before
    assert [(A.abstract(obs), A.control_family(obs))
            for obs in compiled.log.observations.values()] == known


def test_v4_accepted_promotion_carries_the_selected_hypotheses_graph(tmp_path):
    from semabi.compiler.compile_v4 import compile_v4

    log = _promotion_log(tmp_path)
    compiled = compile_v4(log.dir, evidence_log=log, read_outputs=False)
    assert compiled.v4.promoted == ["text[_]"]
    assert any(move["move"] == "promote_leaf" for move in compiled.v4.moves)
    A = compiled.abstractor.freeze()
    learned = _learned_reading(A)
    unseen = _promotion_page(("Larch", "Birch", "Cedar", "Elm"))
    sig = unseen.structural_signature()
    assert sig not in A.G.obs and sig not in A.H.G.obs

    A.parsed(unseen)
    assert 1 in A.control_family(unseen)
    A.abstract(unseen)

    assert A.H is compiled.v4.hypotheses and A.G is A.H.G
    assert A.G.learning is False and A.emissions.frozen
    assert sig in A.G.obs and _learned_reading(A) == learned


def test_v4_inferred_fit_keeps_its_frozen_reading_in_either_unseen_page_order(tmp_path):
    from semabi.compiler.v4 import consequence as csq

    log = _ownership_log(tmp_path)
    forward = csq.fit(log.dir, None, at=len(log.steps), min_support=1).abstractor
    backward = csq.fit(log.dir, None, at=len(log.steps), min_support=1).abstractor
    learned = _learned_reading(forward)
    assert _learned_reading(backward) == learned
    pages = [_ownership_page("fresh value", ("Cedar", "Dune")),
             _ownership_page("another value", ("Elm", "Fir"), header="Future column")]
    readings = []
    for A, order in ((forward, pages), (backward, list(reversed(pages)))):
        for obs in order:
            A.parsed(obs)
            A.control_family(obs)
            A.abstract(obs)
        assert A.G is A.H.G and A.G.learning is False and A.emissions.frozen
        assert _learned_reading(A) == learned
        readings.append([(A.abstract(obs), A.control_family(obs)) for obs in pages])
    assert readings[0] == readings[1]


def test_v4_search_candidate_reads_only_its_own_graph(tmp_path):
    from copy import deepcopy

    from semabi.compiler.compile_v4 import build_hypotheses
    from semabi.compiler.v4.search import _build

    log = _ownership_log(tmp_path)
    source, G = build_hypotheses(log.dir, log)
    candidate, sibling = deepcopy(source), deepcopy(source)
    source_observations, sibling_observations = set(G.obs), set(sibling.G.obs)
    source_vocabulary, sibling_vocabulary = vocabulary(G), vocabulary(sibling.G)
    A = _build(candidate, G, log).freeze()
    unseen = _ownership_page("candidate value", ("Cedar", "Dune"))
    sig = unseen.structural_signature()

    A.parsed(unseen)
    assert 1 in A.control_family(unseen)
    A.abstract(unseen)

    assert A.G is candidate.G and A.H is candidate
    assert sig in candidate.G.obs
    assert set(G.obs) == source_observations and set(sibling.G.obs) == sibling_observations
    assert vocabulary(G) == source_vocabulary and vocabulary(sibling.G) == sibling_vocabulary
    assert G.learning is True and sibling.G.learning is True


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
HARBOUR_RUN = ROOT / "runs/v4/harbour_transfer"
HARBOUR_CHAIN = ROOT / "docs/data/v4/manifests/harbour_chain.json"


@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_fitting_a_reading_leaves_a_model_that_no_longer_learns():
    """The freezing boundary must hold for the whole pipeline, including lazily induced
    control families -- resolving them on first access could induce them over graph state
    that is no longer the prefix.
    """
    from semabi.compiler.v4 import consequence as csq
    from semabi.eval.v4_consequence_run import _candidates, vessel_keyed

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    model = csq.fit(HARBOUR_RUN, vessel_keyed(readings), split=0.5)
    A = model.abstractor
    assert A.G.learning is False
    assert A._controls is not None

    before = (set(A.G.data_set()), len(A.G.templates), len(A.G.templates_v), set(A.G._whole))
    for step in model.log.steps[model.cut:][:20]:
        A.abstract(model.log.obs(step.before))
        A.abstract(model.log.obs(step.after))
    assert (set(A.G.data_set()), len(A.G.templates), len(A.G.templates_v),
            set(A.G._whole)) == before


# ------------------------------------------------------------------ the causal frontier

def _section_chronology_log(tmp_path, changed_future):
    from semabi.compiler.browser import Primitive
    from semabi.compiler.evidence import EvidenceLog

    def section_page(first, second):
        return Observation([Node(0, -1, "group", ""), Node(1, 0, "heading", first),
                            Node(2, 0, "button", "Go"), Node(3, 0, "heading", second),
                            Node(4, 0, "button", "Go")])

    before = section_page("Alpha", "Beta Gamma")
    future = section_page("Delta", "Epsilon Zeta") if changed_future else before
    log = EvidenceLog(tmp_path / str(changed_future))
    action = Primitive("click", 2, target_desc={"role": "button", "name": "Go"})
    log.add_step(0, action, True, None, before, before)
    log.add_step(0, action, True, None, before, future)
    return log


def _section_payload(log):
    return {"observations": {sig: obs.to_json() for sig, obs in log.observations.items()},
            "steps": [step.to_json() for step in log.steps]}


def _assert_section_coordinates(log, raw):
    for sig, obs in log.observations.items():
        assert sig == obs.structural_signature()
    for step in log.steps:
        original = raw.steps[step.step]
        assert step.action.to_json() == original.action.to_json()
        assert step.action.target == 2
        for side in ("before", "after"):
            obs = log.obs(getattr(step, side))       # every remapped reference must resolve
            raw_obs = raw.obs(getattr(original, side))
            assert [(node.i, node.key()) for node in obs.nodes[:5]] == [
                (node.i, node.key()) for node in raw_obs.nodes]
        assert log.obs(step.before).node(2).key() == raw.obs(original.before).node(2).key()


@pytest.mark.parametrize("regime", ["FROZEN_PREFIX", "CAUSAL_PREQUENTIAL"])
def test_future_outcome_cannot_change_the_section_representation_of_a_prefix(tmp_path, regime):
    from semabi.compiler.v4 import consequence as csq

    raw = [_section_chronology_log(tmp_path, changed) for changed in (False, True)]
    assert _section_payload(raw[0].through(1)) == _section_payload(raw[1].through(1))
    assert _section_payload(raw[0].before_action(1)) == _section_payload(raw[1].before_action(1))
    models = [csq.fit(log.dir, None, at=1, regime=regime, min_support=1, read_outputs=False)
              for log in raw]
    for model, original in zip(models, raw):
        assert model.cut == 1
        _assert_section_coordinates(model.log, original)
        _assert_section_coordinates(model.evidence, original)
    assert _section_payload(models[0].evidence) == _section_payload(models[1].evidence)
    assert _section_payload(models[0].evidence) == _section_payload(raw[0].through(1))
    assert _learned_reading(models[0].abstractor) == _learned_reading(models[1].abstractor)


@pytest.mark.parametrize("changed_future", [False, True])
def test_section_normalization_with_all_evidence_preserves_its_exact_output(tmp_path, changed_future):
    from dataclasses import replace

    from semabi.compiler.compile_v4 import _normalise_sections
    from semabi.compiler.evidence import EvidenceLog

    raw = _section_chronology_log(tmp_path, changed_future)
    log = EvidenceLog(raw.dir)
    # With both pages allowed, the two heading/button spans are established sections.
    expected_pages = {}
    for sig, obs in raw.observations.items():
        nodes = [replace(node, parent=parent) for node, parent in
                 zip(obs.nodes, [-1, 5, 5, 6, 6])] + [Node(5, 0, "group", ""),
                                                   Node(6, 0, "group", "")]
        expected_pages[sig] = Observation(nodes) if changed_future else obs
    expected = _section_payload(raw)
    expected["observations"] = {obs.structural_signature(): obs.to_json()
                                for obs in expected_pages.values()}
    for step in expected["steps"]:
        for side in ("before", "after"):
            step[side] = expected_pages[step[side]].structural_signature()

    _normalise_sections(log, stats_from=None)

    assert _section_payload(log) == expected
    _assert_section_coordinates(log, raw)


def _run(tmp_path, rows, name="run"):
    """A run directory with ``rows`` continuous steps, each a distinct observation."""
    import json
    from semabi.compiler.evidence import EvidenceLog
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    obs = [{"sig": f"s{i}", "obs": {"nodes": [
        {"i": 0, "parent": None, "role": "text", "name": f"v{i}", "bbox": [0, 0, 1, 1]}]}}
        for i in range(rows + 1)]
    (d / "observations.jsonl").write_text("\n".join(json.dumps(o) for o in obs) + "\n")
    steps = [{"step": i, "episode": 0, "action": {"kind": "click", "target": 0},
              "ok": True, "error": None, "before": f"s{i}", "after": f"s{i+1}",
              "typed_tokens": []} for i in range(rows)]
    (d / "steps.jsonl").write_text("\n".join(json.dumps(s) for s in steps) + "\n")
    return EvidenceLog(d)


def test_the_pre_action_view_holds_the_page_the_agent_was_looking_at_and_not_the_outcome(tmp_path):
    """An agent choosing an action has seen every completed transition and the page in
    front of it, but not what the action does. This is a different, looser boundary than
    a held-out cut; conflating them would either deny the agent the page it acts on or
    hand it the answer.
    """
    log = _run(tmp_path, 8)
    view = log.before_action(4)

    assert [s.step for s in view.steps] == [0, 1, 2, 3]         # completed transitions only
    assert "s4" in view.observations                            # the page it is acting on
    assert "s5" not in view.observations                        # what the action did
    assert "s8" not in view.observations
    assert view.obs_path is None


def test_what_an_action_does_cannot_reach_the_model_that_predicted_it(tmp_path):
    """Two histories that agree up to and including the pre-state of an action must
    produce the same model, whatever follows.
    """
    import json
    a = _run(tmp_path, 9, "a")
    b = _run(tmp_path, 9, "b")
    d = tmp_path / "b"
    rows = [json.loads(l) for l in (d / "steps.jsonl").read_text().splitlines()]
    for r in rows[4:]:
        r["after"] = r["after"] + "x"                       # a wholly different future
        if r["step"] > 4:
            r["before"] = r["before"] + "x"
    (d / "steps.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    from semabi.compiler.evidence import EvidenceLog
    b = EvidenceLog(d)

    va, vb = a.before_action(4), b.before_action(4)
    assert set(va.observations) == set(vb.observations)
    assert [(s.before, s.after) for s in va.steps] == [(s.before, s.after) for s in vb.steps]


# ------------------------------------------------------------------ attacking the prequential evaluator

@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_a_prequential_model_is_not_built_from_the_outcome_it_is_about_to_predict():
    """Everything the model was fitted from must be an observation the agent had
    already seen when it chose the action. The post-state must never be among them, so
    the assertion checks the step list the model learned from, not merely which
    signatures are present (which can coincide when an action changes nothing).
    """
    from semabi.compiler.v4 import consequence as csq
    from semabi.eval.v4_consequence_run import _candidates, vessel_keyed

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    t = 200
    model = csq.fit(HARBOUR_RUN, vessel_keyed(readings), at=t,
                    regime=csq.CAUSAL_PREQUENTIAL)
    seen, whole = model.evidence, model.log
    assert model.cut == t
    assert seen is not whole, "the model must record the view it learned from"
    assert [s.step for s in seen.steps] == list(range(t))
    assert whole.steps[t].before in seen.observations

    after = whole.steps[t].after
    if after != whole.steps[t].before:          # a no-op action is looking at its own outcome
        assert after not in seen.observations
    reachable = {s.before for s in whole.steps[:t]} | {s.after for s in whole.steps[:t]} \
        | {whole.steps[t].before}
    assert set(seen.observations) <= reachable


@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_deleting_the_future_does_not_move_the_model_that_predicted_the_present(tmp_path):
    """Truncates the trace immediately after the action under test and rebuilds the
    model: if anything downstream of the prediction had reached it, the fingerprint
    would move.
    """
    import json
    import shutil

    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4.prequential import fingerprint
    from semabi.compiler.evidence import EvidenceLog
    from semabi.eval.v4_consequence_run import _candidates, vessel_keyed

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    reading = vessel_keyed(readings)
    t = 120

    whole = csq.fit(HARBOUR_RUN, reading, at=t, regime=csq.CAUSAL_PREQUENTIAL)

    truncated = tmp_path / "truncated"
    truncated.mkdir()
    src = EvidenceLog(HARBOUR_RUN)
    keep = {s.before for s in src.steps[:t]} | {s.after for s in src.steps[:t]} \
        | {src.steps[t].before}
    (truncated / "observations.jsonl").write_text("".join(
        line + "\n" for line in (HARBOUR_RUN / "observations.jsonl").read_text().splitlines()
        if json.loads(line)["sig"] in keep))
    (truncated / "steps.jsonl").write_text("".join(
        line + "\n" for line in (HARBOUR_RUN / "steps.jsonl").read_text().splitlines()[:t]))
    for extra in ("meta.json",):
        if (HARBOUR_RUN / extra).exists():
            shutil.copy(HARBOUR_RUN / extra, truncated / extra)

    cut = csq.fit(truncated, reading, at=t, regime=csq.CAUSAL_PREQUENTIAL)
    assert fingerprint(cut.abstractor) == fingerprint(whole.abstractor)
    assert len(cut.operators) == len(whole.operators)


# ------------------------------------------------------------------ abstaining is not denying

@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_a_rule_that_cannot_say_which_object_says_so_rather_than_guessing():
    """A rule whose referring expression names no single object in this state has not
    identified its subject. `NOT_APPLICABLE` is a claim about the page; `UNKNOWN` is a
    claim about the model. Falling through to enumeration answers a different question
    -- which objects the preconditions fail to exclude -- and wrongly reports the page
    as refusing the rule instead of the model failing to identify a subject.
    """
    from types import SimpleNamespace

    from semabi.compiler.abstract import AbsObj, AbstractState
    from semabi.compiler.v4 import binding, consequence as csq, referring

    tid = 1
    st = AbstractState.__new__(AbstractState)
    st.objs = {(tid, "N1"): AbsObj(tid, "N1", {}, refs={}, node=1)}
    st.view = {"combobox#0": "Nowhere (gone)"}
    st.types = {tid: SimpleNamespace(key_slot="id")}

    op = SimpleNamespace(name="op0", params={"?v": tid}, pre=[], effs=(),
                         acts=(SimpleNamespace(kind="click", loc=None, owner=None, arg=None),),
                         core=lambda: (SimpleNamespace(kind="click", loc=None, owner=None),))
    q = referring.Query(referring.SELECTION, "?v", "the object named by combobox#0",
                        form=("combobox#0",))

    bound, why = csq.bindings_for(None, None, st, op, 0, csq.ASSERTED, {"?v": q})
    assert why == ""
    assert bound.status == binding.UNNAMED
    assert bound.status not in (binding.NONE, binding.UNIQUE)
    assert "names no single object" in bound.detail
    assert bound.admissible == ()

    # and when it does resolve, the rule is bound and the enumeration proceeds
    st.view = {"combobox#0": "N1 (open)"}
    A = SimpleNamespace(types=st.types)
    bound, why = csq.bindings_for(A, None, st, op, 0, csq.ASSERTED, {"?v": q})
    assert bound.status != binding.UNNAMED
    assert bound.status == binding.UNIQUE
    assert bound.unique.get("?v").key == "N1"


# ------------------------------------------------------------------ what the model cannot see

@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_the_application_says_what_it_did_and_the_model_reads_it_as_an_outcome():
    """Three things are pinned: the parser does not place the status sentence as an
    ordinary leaf (doing so would turn it into an attribute slot and make a status-only
    change look like a domain change), the transition carries it instead, and a
    status-only diff is still not a domain change.
    """
    from semabi.compiler.abstract import Diff
    from semabi.compiler.parse import DATA_ROLES
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import emission as em
    from semabi.eval.v4_consequence_run import _candidates, vessel_keyed

    # A role is state or output, never both: read twice, a message would be a domain change.
    assert not (set(em.LIVE_ROLES) & DATA_ROLES)

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    model = csq.fit(HARBOUR_RUN, vessel_keyed(readings), split=0.5)
    A, log = model.abstractor, model.evidence

    checked = placed = in_view = 0
    for sig in list(log.observations)[:40]:
        obs = log.obs(sig)
        status = [n for n in obs.nodes if n.role == "status" and (n.name or "").strip()]
        if not status:
            continue
        checked += 1
        node = status[0]
        roots = [inst.root for inst in A.parsed(obs).instances]
        if any(node.i in obs.subtree(r) for r in roots):
            placed += 1
        state = A.abstract(obs)
        if node.name in (state.view or {}).values():
            in_view += 1

    assert checked, "harbour's observations carry a status line; this found none"
    assert placed == 0 and in_view == 0, (
        f"{placed} status nodes are inside a unit and {in_view} reach the view; the live "
        "region is a transition output and must not also be state"
    )

    # It is carried on the transitions instead, as a lifted event.
    emitted = [tr for tr in model.inducer.transitions if tr.emission is not None]
    assert emitted, "no transition carries an output"
    assert any(e.kind == "emit" for op in model.operators for e in op.effs)

    # And the gate is untouched: nothing about the world changed.
    only_view = Diff([], [], [], [], {"status": ("Ready.", "Berth N2 is already closed.")})
    assert only_view.domain_changed is False
