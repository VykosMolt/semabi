"""Invented Python hook/copy controls only; no SemABI module or native fit runs."""
from dataclasses import make_dataclass, replace
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import weakref

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[1] / "trace.py"
spec = importlib.util.spec_from_file_location("j1_invented_trace", SOURCE)
t = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = t
spec.loader.exec_module(t)

State = make_dataclass("State", [("objects", dict)])
Observation = make_dataclass("Observation", [("nodes", list)])
ParsedObs = make_dataclass("ParsedObs", [("node_key", dict)])
Primitive = make_dataclass("Primitive", [("kind", str), ("target", object), ("text", object), ("target_desc", object)])
Step = make_dataclass("Step", [("step", int), ("episode", int), ("action", Primitive), ("ok", bool), ("error", object), ("before", str), ("after", str), ("typed_tokens", list)])
Transition = make_dataclass("Transition", [("steps", list), ("macro", list), ("before", State), ("after", State), ("binding", dict)])
Operator = make_dataclass("Operator", [("name", str), ("params", dict), ("positives", list), ("negatives", list)])
Grounding = make_dataclass("Grounding", [("queries", dict), ("basis", dict), ("unreachable", tuple)])
Role = make_dataclass("Role", [("name", str), ("form", tuple)])
Control = make_dataclass("Control", [("roles", dict), ("field_theory", dict)])

class Fit:
    pass

class Abstractor:
    pass

class Hypotheses:
    pass

class Vocabulary:
    pass

class Log:
    pass

class Inducer:
    def __init__(self):
        self.__dict__.update({name: {} for name in t.INDUCER_FIELDS})
        state = State({"item": {"value": 1}})
        self.transition = Transition([0], [0], state, state, {})
        self.transitions = [self.transition]
        self.noops = []
        self.operators = [Operator("op", {"?object": 1}, [self.transition], [])]
        self.view_transitions = [(self.transition, "view", 1, "item")]
        self.view_ops = []
        self.read_outputs = True

    def lift(self, tr):
        obj_param = {("T", "item"): "?object"}
        str_param = {}
        view_sources = {}
        ren = {"?object": "?canonical"}
        tr.binding = {"?canonical": (1, "item")}

    def learn_queries(self):
        op = self.operators[0]
        evidence = [(self.transition.before, {"?canonical": (1, "item")})]
        return ground(op, evidence, {"?canonical"}, None, frozenset({1}), enabling=frozenset())

    def _cluster_view_ops(self):
        self.lift(self.transition)

    def run(self):
        self.lift(self.transition)
        self.transition.binding = {"?later": (1, "item")}
        self.learn_queries()
        self._cluster_view_ops()
        self.transition.binding = {"?final": (1, "item")}
        return self.operators


def ground(op, evidence, action_bound, refuses, collections=frozenset(), enabling=frozenset()):
    wanted = []
    return Grounding({}, {"counts": 1}, ())


def fallback(inducer, operators):
    op = operators[0]
    return ground(op, [], set(), None)


def roles(inducer, operators):
    return {"role": Role("role", ("relation", "field"))}


def controls(inducer, A, log, by_control, ops_by_control, first_view, out, ordered, pairs, *,
             permute, subject_restricted, structural, touched, about, simplest):
    for control, rows in by_control.items():
        got = roles(inducer, ops_by_control.get(control, []))
        out[control] = Control(got, {})


def nonselected_caller():
    trial = Inducer()
    trial.run()


def compile_fit():
    inducer = Inducer()
    inducer.run()
    return inducer


def fit_once():
    nonselected_caller()
    inducer = compile_fit()
    abstractor = Abstractor()
    abstractor.__dict__.update({name: {} for name in t.ABSTRACTOR_FIELDS})
    hypotheses = Hypotheses()
    hypotheses.__dict__.update({name: {} for name in t.HYPOTHESIS_FIELDS})
    vocabulary = Vocabulary()
    vocabulary.values, vocabulary.frozen = set(), True
    abstractor.H, abstractor.emissions = hypotheses, vocabulary
    step = Step(0, 1, Primitive("click", 0, None, None), True, None, "page", "page", [])
    observation = Observation([])
    log = Log()
    log.steps, log.observations, log.typed_tokens = [step], {"page": observation}, []
    inducer.A, inducer.log = abstractor, log
    by_control = {"control": [(inducer.transition, step, observation, "event")]}
    outputs = []
    for ordered in ({"candidate": 1}, {}):
        out = {}
        controls(inducer, abstractor, log, by_control, {"control": inducer.operators}, {}, out, ordered, None,
                 permute=None, subject_restricted=False, structural=False, touched=False, about=False, simplest=False)
        outputs.append(out)
    out["control"].field_theory = {"adopted": []}
    result = Fit()
    result.__dict__.update(reading=None, cut=1, split=1.0, regime="frozen_prefix", read_outputs=True,
                           queries={}, outcomes=out, operators=inducer.operators, inducer=inducer,
                           abstractor=abstractor, log=log, evidence=log)
    return result


records = {cls: t.RecordSpec("invented." + cls.__name__, tuple(cls.__dataclass_fields__),
                           ("_member_positioned_cache",) if cls is ParsedObs else ())
           for cls in (State, Observation, ParsedObs, Primitive, Step, Transition, Operator, Grounding, Role, Control)}
bindings = t.Bindings({"fit": fit_once.__code__, "compile": compile_fit.__code__, "run": Inducer.run.__code__,
    "lift": Inducer.lift.__code__, "ground": ground.__code__, "inducer_queries": Inducer.learn_queries.__code__,
    "consequence_queries": fallback.__code__, "view_cluster": Inducer._cluster_view_ops.__code__,
    "controls": controls.__code__, "roles": roles.__code__}, records,
    {"fit": Fit, "inducer": Inducer, "transition": Transition, "operator": Operator, "state": State,
     "observation": Observation, "abstractor": Abstractor, "hypotheses": Hypotheses, "vocabulary": Vocabulary,
     "log": Log})
raw = {"steps": [{"step": 0, "episode": 1, "action": {"kind": "click", "target": 0}, "ok": True,
                   "error": None, "before": "page", "after": "page"}],
       "observations": [{"sig": "page", "obs": {"nodes": []}}]}
checks = []

baseline = t.project_fit(fit_once(), raw_records=raw, primary_steps=[0, 99], bindings=bindings)
with t.FitObserver(raw_records=raw, primary_steps=[0, 99], bindings=bindings) as observer:
    fitted = fit_once()
trace = observer.export(fitted)
assert baseline["status"] == trace["projection"]["status"] == trace["status"] == "COMPLETE", trace["incomplete_reasons"]
assert baseline == trace["projection"]
checks.append("invented_complete_baseline_and_profiled_projections_identical")
assert trace["profiler_restored"] and sys.getprofile() is None
assert trace["fit_calls"] == trace["selected_final_run_calls"] == 1
assert len(trace["omitted_inducer_run_calls"]) == 1
assert trace["omitted_inducer_run_calls"][0]["caller"]["function"] == "nonselected_caller"
checks.append("exact_caller_selection_and_unclassified_omitted_run")
lifts = [row for row in trace["events"] if row["kind"] == "lift_return"]
assert len(lifts) == 2 and lifts[0]["first_observed_lift"] and not lifts[1]["first_observed_lift"]
assert not lifts[0]["view_cluster_lift"] and lifts[1]["view_cluster_lift"]
assert all(row["normal_return"] for row in lifts)
assert lifts[0]["transition"]["snapshot"]["fields"]["binding"]["items"][0][0] == "?canonical"
assert trace["observed_transition_membership"][0]["current_snapshot"]["fields"]["binding"]["items"][0][0] == "?final"
assert trace["observed_transition_membership"][0]["membership"]["view_transitions"] == [0]
checks.append("first_and_repeated_view_lift_are_distinct_and_copies_survive_native_mutation")
passes = trace["outcome_pass_adoption"]
assert len(passes) == 2 and [row["is_final_fit_outcomes"] for row in passes] == [False, True]
assert len([row for row in trace["events"] if row["kind"] == "roles_return"]) == 2
assert all(row["control_pass"] is not None for row in trace["events"] if row["kind"] == "roles_return")
checks.append("repeated_control_dictionaries_and_roles_bound_by_identity")
assert baseline["primary_step_associations"][1]["status"] == "NO_FITTING_ASSOCIATION"
assert not baseline["primary_step_associations"][1]["permitted_fitting_step"]
checks.append("reporting_selector_retains_unassociated_nonfitting_step")

copier = t.Copier(bindings)
value = {1: [1], "1": (1,)}
copied = copier.copy(value)
value[1].append(2)
assert copied["items"] == [[1, [1]], ["1", {"$tuple": [1]}]]
assert copier.copy(2 ** 80) == {"$integer_decimal": format(2 ** 80, "d")}
assert copier.copy({3, 1, 2})["items"] == [1, 2, 3]
checks.append("copied_containers_preserve_key_types_order_and_large_integers")
cycle = []
cycle.append(cycle)
assert "$unknown" in copier.copy(cycle)[0]
checks.append("cycles_mark_copy_incomplete")

class Hostile:
    def __repr__(self):
        raise AssertionError("repr called")
    def __str__(self):
        raise AssertionError("str called")
    def to_json(self):
        raise AssertionError("to_json called")
    @property
    def clean(self):
        raise AssertionError("property called")

assert "$unknown" in copier.copy(Hostile())
checks.append("unsupported_native_like_object_not_rendered_or_queried")
identity = t.IdentityTable("object_")
owned = Hostile()
ref = weakref.ref(owned)
label = identity.add(owned)
del owned
gc.collect()
assert ref() is not None and identity.add(ref()) == label and identity.add(Hostile()) != label
checks.append("identity_table_keeps_original_alive")

def prior_profiler(frame, event, argument):
    return None

sys.setprofile(prior_profiler)
try:
    try:
        with t.FitObserver(bindings=bindings):
            raise AssertionError("active profiler was replaced")
    except RuntimeError:
        assert sys.getprofile() is prior_profiler
finally:
    sys.setprofile(None)
checks.append("already_active_profiler_refused_without_replacement")

def failed_fit():
    compile_fit()
    raise ValueError("invented native failure")

failed_bindings = replace(bindings, codes={**bindings.codes, "fit": failed_fit.__code__})
try:
    with t.FitObserver(raw_records=raw, bindings=failed_bindings) as failed:
        failed_fit()
except ValueError:
    pass
else:
    raise AssertionError("native exception was swallowed")
failed_record = failed.export()
assert failed_record["status"] == "INCOMPLETE" and failed_record["profiler_restored"] and failed_record["events"]
checks.append("native_exception_propagates_with_restored_profiler_and_partial_trace")

class BrokenObserver(t.FitObserver):
    def _transition(self, transition, path):
        raise ValueError("invented callback failure")

with BrokenObserver(raw_records=raw, bindings=bindings) as broken:
    result = fit_once()
assert type(result) is Fit and broken.closed and broken.restored
assert any(row["reason"] == "callback_exception:ValueError" for row in broken.copier.errors)
checks.append("callback_exception_does_not_enter_running_fit")

missing = t.project_fit(fitted, primary_steps=[0], bindings=bindings)
assert missing["status"] == "INCOMPLETE"
different = json.loads(json.dumps(raw))
different["steps"][0]["episode"] = 2
mismatch = t.project_fit(fitted, raw_records=different, bindings=bindings)
assert mismatch["status"] == "INCOMPLETE"
checks.append("missing_or_mismatched_raw_mapping_prevents_complete_projection")
consumed = []
def unexpected_iterator():
    consumed.append(True)
    yield fitted.inducer.transition

operator = Operator("op", {}, unexpected_iterator(), [])
guarded = t.FitObserver(bindings=bindings)
try:
    guarded._operator(operator, "invented_iterator")
except TypeError:
    pass
else:
    raise AssertionError("unsupported native iterator was accepted")
assert consumed == []
checks.append("unsupported_native_iterator_is_rejected_without_consumption")
altered_projection = json.loads(json.dumps(baseline))
altered_projection["fit"]["cut"] += 1
assert altered_projection["status"] == baseline["status"] == "COMPLETE"
assert altered_projection != baseline
checks.append("complete_common_projection_comparison_rejects_a_changed_measurement_field")
cache_callbacks = []
def forbidden_cache_property(instance):
    cache_callbacks.append(True)
    raise AssertionError("cache property or computation called")

ParsedObs._member_positioned_cache = property(forbidden_cache_property)
parsed = ParsedObs({0: "view_slot"})
cache_copier = t.Copier(bindings)
absent = cache_copier.copy(parsed)
assert absent["fields"]["_member_positioned_cache"]["$unknown"]["reason"] == "not_stored"
assert cache_copier.errors == []
parsed.__dict__["_member_positioned_cache"] = {"view_slot": True}
present = cache_copier.copy(parsed)
parsed.__dict__["_member_positioned_cache"]["view_slot"] = False
assert present["fields"]["_member_positioned_cache"]["items"] == [["view_slot", True]]
assert cache_callbacks == [] and cache_copier.errors == []
checks.append("optional_parsed_cache_absence_presence_isolation_and_no_callback")
assert not any(name == "semabi" or name.startswith("semabi.") for name in sys.modules)
print(json.dumps({"schema": "semabi.transport.j1_invented_trace_checks.v1", "status": "PASS",
                  "trace_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "checks": checks,
                  "scope": "Invented Python objects/calls only; no native transparency claim"}, indent=2))
