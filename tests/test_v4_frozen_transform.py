"""The information boundary between fitting a semantic model and reading with it.

A held-out evaluation is only prospective if the model that reads the held-out page is the
model the prefix produced.  Scoping the evidence log was necessary and not sufficient: the
abstractor puts every observation it is asked to read into the observation graph, and the graph
accumulates the corpus statistics -- the text-variation templates and the data-token vocabulary
-- that decide which text on a page is a value rather than a label.  So transforming the suffix
was teaching the model the vocabulary it was about to be judged with.

What a pass establishes, and what it does not:

* a frozen model can read an observation it has never seen and is not changed by having read
  it.  Per-observation structure still arrives, because otherwise the page cannot be read at
  all; what does not arrive is anything the model would later consult as evidence.
* a position the prefix never established stays unknown rather than becoming known.  The frozen
  model answers with less, never with a claim about the application.
* nothing here establishes that the prefix model is *good*.  It establishes that its answers on
  held-out evidence are answers it could have given before seeing that evidence.
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
    """The defect, at the level it actually occurred.

    On harbour this added three tokens to the data vocabulary, one of them a word the prefix
    had never seen used as data.  Whether that changed a reading was a property of the trace;
    that the model moved was a property of the code.
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
    """Proof that the test above exercises the defect rather than an accessor.

    If freezing were a no-op, or if the corpus statistics were not really what the model
    consults, this assertion would not hold and the guarantee above would be vacuous.
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
    """Novelty in the suffix may reduce what the frozen model knows; it may not add to it.

    ``is_prose`` decides whether a text position is a sentence.  A frozen graph has no template
    for a position the prefix never saw, so it answers False -- *no evidence that this is
    prose*.  A graph that is still learning invents the evidence from the page it is reading.
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

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
HARBOUR_RUN = ROOT / "runs/v4/harbour_transfer"
HARBOUR_CHAIN = ROOT / "docs/data/v4/manifests/harbour_chain.json"


@pytest.mark.skipif(not (HARBOUR_RUN / "steps.jsonl").exists(), reason="retained trace absent")
def test_fitting_a_reading_leaves_a_model_that_no_longer_learns():
    """The boundary reaches the pipeline, not only the graph it is implemented in.

    Also pins the lazily induced control families: resolving them on first access would have
    induced them over whatever was in the graph at that moment, which after a few held-out
    transforms is not the prefix.
    """
    from semabi.compiler.v4 import consequence as csq
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    model = csq.fit(HARBOUR_RUN, readings["joint discrimination x2"], split=0.5)
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
    """The information frontier of an agent that is still learning.

    An agent choosing action ``t`` has seen every completed transition and the page in front of
    it.  It has not seen what the action did.  A held-out cut is a different and stricter
    boundary; conflating them would either deny the agent the page it is acting on or hand it
    the answer.
    """
    log = _run(tmp_path, 8)
    view = log.before_action(4)

    assert [s.step for s in view.steps] == [0, 1, 2, 3]         # completed transitions only
    assert "s4" in view.observations                            # the page it is acting on
    assert "s5" not in view.observations                        # what the action did
    assert "s8" not in view.observations
    assert view.obs_path is None


def test_what_an_action_does_cannot_reach_the_model_that_predicted_it(tmp_path):
    """Two histories agreeing up to and including the pre-state of action ``t``.

    Whatever follows -- a different outcome, a different future -- the evidence available when
    the action was chosen is the same, so a model built from it is the same.  This is the
    strongest chronology regression available at the level of the evidence view.
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
    """The frontier, on the real pipeline rather than on a fixture.

    Everything the model was fitted from must be an observation the agent had already seen when
    it chose the action: a completed transition, or the page in front of it.  The post-state is
    the one thing that must not be there, and where an action changes nothing the two coincide
    -- so the assertion is about the *step list* the model learned transitions from, not merely
    about which signatures are present.
    """
    from semabi.compiler.v4 import consequence as csq
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    t = 200
    model = csq.fit(HARBOUR_RUN, readings["joint discrimination x2"], at=t,
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
    """Future deletion invariance, on the real trace.

    The trace is truncated immediately after the action under test and the model rebuilt.  If
    anything downstream of the prediction had reached the model, the fingerprint would move.
    This is the strongest available chronology regression because it changes the data rather
    than the code, so no accessor or flag can satisfy it by accident.
    """
    import json
    import shutil

    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4.prequential import fingerprint
    from semabi.compiler.evidence import EvidenceLog
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    reading = readings["joint discrimination x2"]
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
    """The difference between "I cannot tell" and "it does not apply here".

    A rule that learned a referring expression and whose expression names no single object in
    this state has not identified its subject.  Falling through to enumeration answers a
    different question -- which objects the preconditions fail to exclude -- and that is where
    the wrong firing happens: on blend, abstaining instead cuts contradictions by 74%, takes
    precision from 21% to 37%, and stops the model being wrong at all on the steps where the
    application performs the action.

    What this pins is the *verdict*, not the improvement.  `NOT_APPLICABLE` is a claim about the
    page; `UNKNOWN` is a claim about the model, and only the second one is true here.  An
    earlier version of this returned the first, and 1090 predictions on one application would
    have been reported as the application refusing the rule.
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
def test_the_application_says_what_it_did_and_the_model_still_cannot_learn_from_it():
    """Half a gap, pinned at the half that remains.

    The status node is now read.  `status` joined the parser's leaf roles beside `alert`, which
    is the same kind of live region and was already in the graph's and the hypotheses' leaf
    sets; only `parse.DATA_ROLES` omitted it.  Harbour's status line now reaches the view on
    every observation it appears in.

    Nothing downstream moved.  Types, slots, operators and control families are identical with
    and without it on harbour and blend, and the regenerated claim ledgers are byte-identical --
    because reading a fact is not the same as being able to learn from it.

    What remains is the gate.  A transition whose only difference is the status line is still
    not a domain change, so a refusal is still set aside as a counterexample rather than lifted
    as an outcome, and all 69 of blend's held-out refusals are still counterexamples.  Closing
    that needs a category this model does not have: an observable outcome that is not a state
    change.  Making a status-only diff count as a domain change is *not* the repair -- nothing
    about the world changed, and that distinction is what stops view navigation looking causal.

    These assertions are written to fail when the second half closes, for the same reason the
    first version was: a silent improvement would leave the numbers in
    `docs/v4_chronology.md` describing a model that no longer exists.
    """
    from semabi.compiler.v4 import consequence as csq
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(HARBOUR_CHAIN)}
    model = csq.fit(HARBOUR_RUN, readings["joint discrimination x2"], split=0.5)
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
    assert in_view == checked, (
        f"only {in_view} of {checked} status lines reach the view -- the parser has stopped "
        "reading them, which undoes the first half of the repair"
    )
    assert placed == 0, (
        f"{placed} status nodes are now inside a unit; they are meant to be statics, and a "
        "status line that belongs to one row of a table is a different claim"
    )

    # The gate that still stops any of it being learned.
    from semabi.compiler.abstract import Diff
    only_view = Diff([], [], [], [], {"status": ("Ready.", "Berth N2 is already closed.")})
    assert only_view.domain_changed is False, (
        "a status-only change now counts as a domain change; that is the wrong repair -- "
        "nothing about the world changed, and this distinction is what stops view navigation "
        "looking causal.  If the second half has been closed properly, it was closed with a "
        "third category and this test needs rewriting around it"
    )
