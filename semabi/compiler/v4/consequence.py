"""Did the thing this action touched do what the reading predicted?

`prospective` checks a prediction against the whole later page, which is too weak: a
value that appears in an untouched row confirms a claim about a row that never changed.
Here a prediction names one raw node and the check asks what that node became.

Where the node went comes from `correspondence`, which reads the raw page, knows nothing
about any reading, and is computed with the predicted field hidden, so the property being
tested cannot be what finds the thing it is tested on. The rules are fitted on a strict
earlier prefix, and the value is compared against the raw later page.

The reading is used only for the earlier state: which object the rule is about, and
whether its precondition held. IDENTITY is the one verdict that consults the reading
afterwards, because that claim is about the reading's own naming; it is reported apart
from VALUE so a conclusion can be read without it.

Verdicts carry the uncertainty of the correspondence: SUPPORTED where every possible
continuation shows the predicted result, REFUTED where none does, POSSIBLE where they
differ, UNKNOWN where the correspondence settled nothing. Nothing is tie-broken.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from semabi.compiler.induce import VARIES
from semabi.compiler.parse import leaf_value
from semabi.compiler.v4 import binding
from semabi.compiler.v4 import correspondence as corr
from semabi.compiler.v4 import emission as emit_mod
from semabi.compiler.v4 import outcome
from semabi.compiler.v4.prospective import action_control, control_of, split_literal

VALUE = "VALUE"
IDENTITY = "IDENTITY"
EXISTENCE = "EXISTENCE"
OUTPUT = "OUTPUT"        # what the interaction returned, checked against the live region
CREATION = "CREATION"    # an object the interaction brings into being, checked on the page

CHANGES = "\x00CHANGES"    # the claim of an effect whose value the action does not determine

MASKED = "masked"          # the instrument: candidate-independent, predicted field hidden
NEAR_OPTIMAL = "masked_near_optimal"   # the same, admitting alignments one match off the best
UNMASKED = "unmasked"      # control: the same matcher allowed to use the tested property
SAME_INDEX = "same_index"  # control: the node kept its position in the tree

SUPPORTED = "SUPPORTED"
REFUTED = "REFUTED"
POSSIBLE = "POSSIBLE"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass
class ScopedPrediction:
    """One rule's claim about one held-out step, checked where the action landed."""
    step: int
    control: str
    operator: str
    kind: str
    support: int
    slot: str
    predicted: str
    expected: str = ""             # the predicted value as the page check actually tests it
    subject: str = ""              # the object the rule was bound to, by the reading's key
    feature_node: int | None = None
    correspondence: str = ""       # UNIQUE | AMBIGUOUS | NONE | ""
    admissible: tuple[int, ...] = ()
    observed: tuple[str, ...] = ()
    held_before: str = ""
    bindings: int = 0                           # assignments the pre-state left open
    binding_status: str = ""                    # UNIQUE | AMBIGUOUS | NONE | UNOBSERVED
    binding_evidence: str = ""                  # supported | possible, over those assignments
    binding_truncated: bool = False              # the enumeration hit its resource bound
    identity: Any = None                        # the reading's own naming check, when it applies
    verdict: str = NOT_APPLICABLE
    detail: str = ""
    layers: tuple[str, ...] = ()
    action_local: bool | None = None            # is the predicted node where the click landed?
    context: tuple[tuple[str, Any], ...] = ()   # what the reading saw of the bound objects

    def to_json(self) -> dict[str, Any]:
        return {"step": self.step, "control": self.control, "operator": self.operator,
                "kind": self.kind, "support": self.support, "slot": self.slot,
                "predicted": self.predicted, "expected": self.expected,
                "subject": self.subject,
                "feature_node": self.feature_node, "correspondence": self.correspondence,
                "admissible": list(self.admissible), "observed": list(self.observed),
                "verdict": self.verdict, "detail": self.detail, "layers": list(self.layers),
                "action_local": self.action_local, "bindings": self.bindings,
                "binding_status": self.binding_status,
                "binding_evidence": self.binding_evidence}


# Which information boundary produced a result.  These are not styles of the same
# experiment; they answer different questions and a report that mixes them says nothing.
TRANSDUCTIVE = "TRANSDUCTIVE"      # schema from the whole retained trace: diagnostic only
FROZEN_PREFIX = "FROZEN_PREFIX"    # schema, action model and queries from the prefix alone
CAUSAL_PREQUENTIAL = "CAUSAL_PREQUENTIAL"   # everything observed before this action, and no more
REGIMES = (FROZEN_PREFIX, TRANSDUCTIVE, CAUSAL_PREQUENTIAL)


@dataclass
class ScopedResult:
    reading: str
    split: float
    applicability: str
    correspondence_rule: str
    fitted_on_steps: int
    evaluated_steps: int
    operators: int
    single_act_operators: int
    regime: str = FROZEN_PREFIX
    model: dict[str, Any] = field(default_factory=dict)
    predictions: list[ScopedPrediction] = field(default_factory=list)
    skipped: Counter = field(default_factory=Counter)
    schema_evidence: dict[str, Any] = field(default_factory=dict)

    def counts(self, kind: str) -> dict[str, int]:
        return dict(sorted(Counter(p.verdict for p in self.predictions
                                   if p.kind == kind).items()))

    def correspondence_counts(self, kind: str) -> dict[str, int]:
        return dict(sorted(Counter(p.correspondence for p in self.predictions
                                   if p.kind == kind and p.correspondence).items()))

    def coverage(self, kind: str) -> dict[str, Any]:
        rows = [p for p in self.predictions if p.kind == kind]
        decided = (SUPPORTED, REFUTED, POSSIBLE)
        tested = sum(1 for p in rows if p.verdict in decided)
        untested = Counter(p.detail for p in rows if p.verdict not in decided)
        return {"predictions": len(rows), "tested": tested,
                "coverage": round(tested / len(rows), 3) if rows else 0.0,
                "reasons": dict(untested.most_common(6)),
                "instrument_reached_this_application": tested > 0}

    @property
    def refutations(self) -> list[ScopedPrediction]:
        return [p for p in self.predictions if p.verdict == REFUTED]

    # Every claim checked against the raw page.  ``OUTPUT`` belongs here for the same reason
    # the other two do: it is decided by what the application rendered, not by anything the
    # reading computes about the later page.
    PAGE_CHECKS = (VALUE, EXISTENCE, OUTPUT, CREATION)

    def signature(self, kind: str | tuple[str, ...] = PAGE_CHECKS) -> list[tuple]:
        """What this reading predicted, where, and how it came out, in raw page terms.

        (step, raw node, expected text, verdict). Every part is either an index into the
        recorded page or a string the page does or does not show, so two readings can be
        compared without translating one vocabulary into the other. Readings with equal
        signatures made the same claims in the same places.

        Only decided predictions are signed: a rule that never fired made no claim.
        """
        kinds = (kind,) if isinstance(kind, str) else tuple(kind)
        # A prediction the pre-state could not bind has no node to name; -1 keeps the
        # signature total without pretending it landed somewhere.
        return sorted((p.kind, p.step, -1 if p.feature_node is None else p.feature_node,
                       str(p.expected), p.verdict)
                      for p in self.predictions
                      if p.kind in kinds and p.verdict != NOT_APPLICABLE)

    def signature_digest(self, kind: str | tuple[str, ...] = PAGE_CHECKS) -> str:
        import hashlib
        import json as _json
        payload = _json.dumps(self.signature(kind), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def binding_summary(self) -> dict[str, Any]:
        """How well each reading's own rules pin down the object the action affected.

        Not a score: the count of assignments its preconditions fail to exclude. A reading
        that cannot relate the control to the object it changes leaves every object of the
        type open, and that shows up here rather than in a verdict."""
        rows = [p for p in self.predictions if p.kind in (VALUE, EXISTENCE)]
        status = Counter(p.binding_status for p in rows if p.binding_status)
        sizes = [p.bindings for p in rows if p.bindings]
        return {"status": dict(sorted(status.items())),
                "median_assignments": sorted(sizes)[len(sizes) // 2] if sizes else 0,
                "largest": max(sizes) if sizes else 0,
                # A count that stopped at the bound is not a measurement of how open the rule
                # was, so it is reported rather than read as one.
                "hit_the_enumeration_bound": sum(1 for p in rows if p.binding_truncated),
                "evidence": dict(sorted(Counter(
                    p.binding_evidence for p in rows if p.binding_evidence).items()))}

    def landing(self, kind: str = VALUE) -> dict[str, dict[str, int]]:
        """Where each decided prediction landed relative to the click, by verdict."""
        out: dict[str, dict[str, int]] = {}
        for p in self.predictions:
            if p.kind != kind or p.verdict == NOT_APPLICABLE or p.action_local is None:
                continue
            key = "in the clicked row" if p.action_local else "in another row"
            out.setdefault(p.verdict, {}).setdefault(key, 0)
            out[p.verdict][key] += 1
        return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}

    def schema(self) -> dict[str, Any]:
        """Are the operators well-formed action schemas, in the STRIPS+ sense?

        A schema's variables are either carried by the action, determined by its
        preconditions, or merely satisfiable. The first two may appear in effects; the
        third may not, because an effect on an object the state does not pin down does
        not say which object changes.

        This reports what was actually learned: a parameter counts as determined when
        every occasion the rule fired left it pinned, and an operator is ill-formed when
        an undetermined parameter appears in one of its effects."""
        operators, ill = {}, []
        for name, row in sorted(self.schema_evidence.items()):
            params = {}
            for param in sorted(row["derived"]):
                seen, pinned = row["seen"][param], row["pinned"][param]
                params[param] = ("determined" if seen and pinned == seen
                                 else f"open on {seen - pinned} of {seen} occasions")
            bad = sorted(p for p in row["derived"] & row["effect_params"]
                         if row["seen"][p] and row["pinned"][p] != row["seen"][p])
            # An output argument the state does not pin down is a message the model cannot
            # instantiate, not an effect on nothing in particular.  Reported apart for that
            # reason: only the second is an ill-formed schema.
            loose_output = sorted(p for p in row["derived"] & row.get("output_params", set())
                                  if p not in row["effect_params"]
                                  and row["seen"][p] and row["pinned"][p] != row["seen"][p])
            kind = ("an effect on an object the state does not pin down" if bad
                    else "every parameter explicit in the action" if not params
                    else "the preconditions determine the rest")
            operators[name] = {"derived": params, "undetermined_effect_params": bad,
                               "undetermined_output_params": loose_output, "kind": kind}
            if bad:
                ill.append(name)
        return {"operators": operators, "ill_formed": sorted(ill),
                "kinds": dict(sorted(Counter(o["kind"] for o in operators.values()).items()))}

    def to_json(self) -> dict[str, Any]:
        return {"reading": self.reading, "split": self.split,
                "applicability": self.applicability,
                "correspondence_rule": self.correspondence_rule,
                "fitted_on_steps": self.fitted_on_steps,
                "evaluated_steps": self.evaluated_steps, "operators": self.operators,
                "single_act_operators": self.single_act_operators, "model": self.model,
                "value": self.counts(VALUE), "identity": self.counts(IDENTITY),
                "existence": self.counts(EXISTENCE),
                "output": self.counts(OUTPUT), "output_coverage": self.coverage(OUTPUT),
                "creation": self.counts(CREATION),
                "creation_coverage": self.coverage(CREATION),
                "existence_coverage": self.coverage(EXISTENCE),
                "value_correspondence": self.correspondence_counts(VALUE),
                "value_coverage": self.coverage(VALUE), "value_landing": self.landing(VALUE),
                "existence_landing": self.landing(EXISTENCE),
                "identity_coverage": self.coverage(IDENTITY),
                "binding": self.binding_summary(), "schema": self.schema(),
                "prediction_signature_digest": self.signature_digest(),
                "predictions_signed": len(self.signature()),
                "skipped": dict(sorted(self.skipped.items())),
                # Enough refutations to inspect a pattern, not enough to make the artifact
                # mostly witnesses; the full set is a rerun away.
                "refutations": [p.to_json() for p in self.refutations[:8]]}


# ---------------------------------------------------------------- the reading bridge

def slot_nodes(A, obs) -> dict[tuple[int, str], int]:
    """(instance root, slot name) -> the raw node the slot's value is read from.

    The abstractor already records this while parsing, which is what makes an effect on a
    slot resolvable to one cell rather than to a page-wide text search."""
    sig = A.ensure(obs)
    out: dict[tuple[int, str], int] = {}
    for ui in A.H.parse_units(sig):
        et_id = A.H.tid_of_template.get(ui.template)
        if et_id is None:
            continue
        unit = A.H.units.get(ui.template)
        if unit is not None and unit.key_slot and unit.key_slot in ui.slot_nodes:
            out[(ui.root, "id")] = ui.slot_nodes[unit.key_slot]
        et = A.H.entity_types[et_id]
        for sid in et.attr_slots.get(ui.template, ()):
            node = ui.slot_nodes.get(sid)
            if node is not None:
                out[(ui.root, A.attr_name(et, ui.template, sid))] = node
    return out


def action_local(obs, clicked: int, node: int) -> bool:
    """Is the node this rule is about in the same table row as the control that was clicked?

    A diagnosis, not a verdict. It separates "the rule was wrong about this object" from
    "the rule was about a different object entirely"; only the second is about the
    reading. Where the click has no enclosing row the answer is trivially true."""
    def scope(index: int) -> int:
        for ancestor in obs.ancestors(index):
            if obs.node(ancestor).role == "row":
                return ancestor
        return -1
    return scope(clicked) == scope(node)


def _single_click_operators(operators) -> dict[str, list]:
    """Operators whose core is one click, indexed by the control that click names.

    A macro's claim is about a sequence, and a held-out single step is not an instance of it.
    Testing one anyway would report refutations for rules that were never asserted about it.
    """
    out: dict[str, list] = {}
    for op in operators:
        core = op.core()
        if len(core) != 1 or core[0].kind != "click" or core[0].loc is None:
            continue
        out.setdefault(control_of(core[0].loc.slot), []).append(op)
    return out


def clicked_control(A, obs, step) -> str:
    """Which control family a rule's locator names, for the control this step clicked.

    A locator names a family, which is the rendered label where controls are keyed by
    label and a learned family key where they are not. Comparing the slot against the
    clicked node's label alone matches nothing on an application whose buttons are
    grouped, so ask the abstractor which family the node belongs to."""
    target = step.action.target
    if target is not None:
        family = A.control_family(obs).get(target)
        if family:
            return control_of(family)
    return action_control(step)


def _owner_object(A, po, state, node: int):
    """The object the clicked control sits in, as the inducer names it.

    Resolved by (type, key) as well as by node: a button that is itself a mention of an
    entity has a key that names the row's object while its node does not, and matching
    nodes alone left such clicks with no owner at all."""
    idx = po.node_instance.get(node)
    by_node = {o.node: o for o in state.objs.values()}
    while idx is not None:
        inst = po.instances[idx]
        if inst.root in by_node:
            return by_node[inst.root]
        key = inst.slots.get("id")
        if key is not None and key[1] not in (None, ""):
            found = state.objs.get((inst.tid, key[1]))
            if found is not None:
                return found
        idx = inst.parent
    return None


def action_binding(A, po, state, op, clicked: int) -> tuple[dict[str, Any], str]:
    """The parameters the concrete action supplies, and nothing else.

    A reading whose objects contain the clicked control can say which object the action is
    about; one whose objects do not supplies nothing here. A typed or selected string was
    also carried by the action, but it lives on the step rather than on the rule and is not
    passed in, so it counts as never supplied rather than as refuting a rule."""
    binding: dict[str, Any] = {}
    core = op.core()[0]
    if core.owner and core.loc is not None and core.loc.owner_tid is not None:
        owner = _owner_object(A, po, state, clicked)
        if owner is None:
            return {}, "the reading does not read the clicked control as part of any object"
        binding[core.owner] = owner
    return binding, ""


def bindings_for(A, po, state, op, clicked: int, applicability: str,
                 queries: dict | None = None) -> tuple[Any, str]:
    """Every assignment of the rule's parameters this pre-action state leaves open.

    An assignment is admissible exactly when it satisfies what decides whether the rule
    applies, so binding and applicability are one question asked once.

    A learned referring query is asked first, which is what it was learned for. If it names
    exactly one object that object is used; if it names none or several, the enumeration
    proceeds. The query never decides whether the rule applies, only what it is about."""
    supplied, why = action_binding(A, po, state, op, clicked)
    if why:
        return None, why
    named = _named_by_query(op, state, supplied, queries)
    unnamed = [v for v in (queries or ()) if v not in named and v not in supplied]
    if unnamed:
        # The rule learned a way to say which object it is about, and it does not resolve
        # here. Enumerating instead would answer a different question -- which objects the
        # preconditions fail to exclude -- so abstain. UNNAMED rather than NONE: "I cannot
        # tell which object" is not "the rule does not apply".
        return binding.Bindings(
            binding.UNNAMED, (),
            "the rule's referring expression names no single object here: "
            + ", ".join(sorted(unnamed))), ""
    return binding.solve(op, applicable_literals(op, applicability), state,
                         {**supplied, **named}, types=A.types), ""


def _named_by_query(op, state, supplied: dict, queries: dict | None) -> dict:
    """Objects the rule's own referring queries determine in this state.

    Asked in dependency order, so a variable a query has already determined can anchor the
    next, and never the other way round.
    """
    if not queries:
        return {}
    # `action_binding` hands the solver objects, not identifiers, so a query-determined
    # variable has to arrive in the same currency.
    known = {p: (state.objs.get(v) if isinstance(v, tuple) else v)
             for p, v in supplied.items()}
    out: dict[str, Any] = {}
    pending = dict(queries)
    progress = True
    while progress and pending:
        progress = False
        for var, q in list(pending.items()):
            if q.given and any(g not in known for g in q.given):
                continue
            del pending[var]
            progress = True
            hits = q.denotation(op, state, known)
            if len(hits) == 1:
                known[var] = out[var] = hits[0]
    return out


_UNCHECKABLE = ("nonempty_str", "str_ne_attr")

ASSERTED = "asserted"      # the rule's own learned precondition, and nothing more
ATTESTED = "attested"      # RETIRED -- see applicable_literals; kept to replay old artifacts
GENERATIVE = "generative"  # RETIRED for the same reason, more so: op.common without op.pre

AUTHORITATIVE = (ASSERTED,)
"""The modes that measure a property of the reading rather than of its fitting transitions.

``attested`` and ``generative`` are not among them.  Both feed ``op.common`` to the binder, and
``op.common`` contains the literals ``learn_pre`` refuses -- so both re-admit, through a second
code path, exactly the memorised training identities the learner threw out.  Measured on two
applications: adding only the ``op.common`` literals that pass those refusals changes not one
verdict on any firing of either, while every verdict change the full mode produces is caused by
a key-slot identity constant.  They remain callable so retained artifacts can be reproduced.
"""


def applicable_literals(op, mode: str) -> list[tuple]:
    """The conditions a rule's antecedent is taken to require.

    `learn_pre` keeps a minimal precondition, just enough to exclude the negatives it saw,
    so a rule asserts less than the conditions it was observed under. Firing it outside
    them is extrapolation. Whether that counts against the reading or against the
    precondition learner cannot be read off the verdict, so both are available:
    `asserted` is the rule as stated, `attested` also requires the attribute values that
    held in every positive.

    Only attribute conditions are added. Structural ones cannot be checked for every
    binding, and dropping an unverifiable restriction makes a rule fire more often, which
    is the direction that invents refutations.

    `attested` and `generative` are no longer authoritative. Both re-admit conditions the
    precondition learner deliberately refuses (equalities on a key, constants of an object
    seen once), and an ablation showed every verdict they change comes from one of those:
    in effect they say "this rule applies to the object that had this name during
    training"."""
    if mode == GENERATIVE:
        return [literal for literal in sorted(getattr(op, "common", ()) or (), key=str)
                if len(literal) == 4 and literal[0] in ("attr", "attr_ne")]
    out = list(op.pre)
    if mode == ATTESTED:
        chosen = {(lit[1], lit[2]) for lit in out if lit[0] in ("attr", "attr_ne")}
        for literal in sorted(getattr(op, "common", ()) or (), key=str):
            if (len(literal) == 4 and literal[0] in ("attr", "attr_ne")
                    and (literal[1], literal[2]) not in chosen):
                out.append(literal)
    return out


def preconditions_hold(A, state, op, values, mode: str = ASSERTED) -> tuple[bool, str]:
    """Does the rule's antecedent hold, exactly, for one complete assignment?

    The same semantics the binder uses, applied to an assignment that is already complete.
    A condition this state cannot decide leaves the rule un-fired: over-firing invents
    refutations, under-firing only costs coverage.

    Nothing on the prediction path calls this, since the binder has already satisfied the
    preconditions. It exists for a caller holding a binding nobody derived, and delegates
    rather than reimplementing so the two cannot disagree."""
    state.types = getattr(state, "types", None) or A.types
    for literal in applicable_literals(op, mode):
        missing = [x for x in literal[1:]
                   if isinstance(x, str) and x.startswith("?") and x not in values]
        if missing:
            return False, f"the rule constrains {missing[0]}, which this step does not bind"
        verdict = binding.holds(literal, values, state)
        if verdict is None:
            return False, (f"the rule's {literal[0]} precondition is about a typed value, "
                           f"not tested here")
        if verdict is False:
            return False, _why_not(literal)
    return True, ""


def _why_not(literal: tuple) -> str:
    head = literal[0]
    if head in ("attr", "attr_ne", "attr_ge", "attr_lt"):
        _, p, slot, value = literal
        sign = {"attr": "=", "attr_ne": "!=", "attr_ge": ">=", "attr_lt": "<"}[head]
        return f"the rule requires {p}.{slot} {sign} {value!r}, which is not so here"
    if head in ("ref_null", "ref_set"):
        _, p, slot = literal
        want = "nothing" if head == "ref_null" else "something"
        return f"the rule requires {slot} to point at {want}, which is not so here"
    if head in ("ref", "ref_ne"):
        return f"the rule's {literal[2]} reference does not hold here"
    if head in ("parent", "parent_ne", "parent_null", "parent_set"):
        return "the rule's containment precondition does not hold here"
    if head == "empty":
        return "the rule requires an object nothing points at"
    return f"the rule's {head} precondition does not hold here"


# ---------------------------------------------------------------- evaluation

def binding_context(binding) -> tuple[tuple[str, Any], ...]:
    """Everything the reading says about the objects the rule was bound to.

    This is what a conditional refinement may be drawn from, and it comes from the
    reading's own vocabulary, so a reading that cannot see the distinguishing state cannot
    be rescued by one. References belong here as much as attributes: a cell that resolves
    to another object is often the one thing that separates success from failure."""
    out: list[tuple[str, Any]] = []
    for param, obj in sorted(binding.items()):
        out.append((f"{param}.id", obj.key))
        for slot, value in sorted(obj.attrs.items()):
            out.append((f"{param}.{slot}", value))
        for slot, target in sorted(obj.refs.items()):
            out.append((f"{param}.{slot}", None if target is None else str(target[1])))
    return tuple(out)


@dataclass
class Fit:
    """One compiled reading on one prefix, reused across scorings.

    Compiling is the whole cost of this instrument, so the applicability modes, the
    controls and both halves of the trace score the same fit rather than repeating it."""
    reading: Any
    abstractor: Any
    operators: list
    log: Any
    cut: int
    split: float
    inducer: Any = None
    regime: str = FROZEN_PREFIX
    evidence: Any = None   # the scoped view the model was actually built from
    queries: dict = field(default_factory=dict)   # operator -> variable -> referring query
    read_outputs: bool = True                    # were live regions read as transition outputs?
    outcomes: dict = field(default_factory=dict)  # control -> ordered outcome model


def fit(run_dir: Path, reading, *, split: float = 0.6, at: int | None = None,
        min_support: int = 2, regime: str = FROZEN_PREFIX, read_outputs: bool = True,
        permute_outcomes: int | None = None, subject_restricted: bool = False) -> Fit:
    """Compile one reading on the evidence a regime says was available, and freeze it.

    The regime is the information boundary, and there is one place that turns it into a
    view of the trace, so no result can be produced under a boundary nobody named.

    FROZEN_PREFIX fits the observation model on prefix pages only and never updates.
    TRANSDUCTIVE lets the whole trace build it, which measures how much of a result the
    later pages were responsible for and is never prospective evidence.
    CAUSAL_PREQUENTIAL is what an agent actually faces: every completed transition and
    the page in front of it, and nothing about how the action turns out.

    `at` names the cut in steps, `split` as a fraction."""
    from semabi.compiler.compile_v4 import compile_v4
    from semabi.compiler.evidence import EvidenceLog

    if regime not in REGIMES:
        raise ValueError(f"unknown information regime {regime!r}")
    run_dir = Path(run_dir)
    full = EvidenceLog(run_dir)
    cut = int(len(full.steps) * split) if at is None else at
    split = cut / len(full.steps) if full.steps else split
    slice_at = {FROZEN_PREFIX: full.through,
                TRANSDUCTIVE: full.transductively_through,
                CAUSAL_PREQUENTIAL: full.before_action}[regime]
    # Sections are decided from this regime's own pages and then applied to every page, so a
    # held-out page is read under a frozen ontology. Slicing happens afterwards because the
    # rewrite re-keys signatures.
    from semabi.compiler.compile_v4 import _normalise_sections
    _normalise_sections(full, stats_from=slice_at(cut))
    prefix = slice_at(cut)
    compiled = compile_v4(run_dir, min_support=min_support, write_diagnostics=False,
                          pinned=reading, evidence_log=prefix, read_outputs=read_outputs)
    # Fitting is over.  Everything after this reads observations the model must not learn from,
    # whichever regime built it: a transductive schema is a diagnostic, not a licence to keep
    # learning while it scores.
    compiled.inducer.A.freeze()
    # The referring queries are part of the model: a rule that names an object the action
    # does not supply has to say which object before it can predict anything. The inducer
    # learns them before its preconditions; this fallback covers a caller without them.
    queries = compiled.inducer.queries or _learn_queries(compiled.inducer,
                                                        compiled.inducer.operators)
    # `log` is the whole trace because scoring has to reach the steps being predicted;
    # `evidence` is what the model was allowed to learn from, kept so a caller can check the
    # boundary rather than trust it. The outcome layer sits over the operators: what a click
    # returns is one of a set of alternatives, learned as an ordered list.
    outcomes = (outcome.learn(compiled.inducer, permute=permute_outcomes,
                              subject_restricted=subject_restricted)
                if read_outputs else {})
    return Fit(reading, compiled.inducer.A, compiled.inducer.operators, full, cut, split,
               compiled.inducer, regime, prefix, queries, read_outputs, outcomes)


def _learn_queries(inducer, operators) -> dict:
    """Per operator, a referring query for each object its effects act on that it must find."""
    from semabi.compiler.v4 import referring

    out: dict[str, dict] = {}
    for op in operators:
        # What a prediction will actually have in hand: the owner of the clicked control and
        # nothing else. Treating a typed string as supplied told this search there was
        # nothing to look for.
        core = op.core()
        bound = {core[-1].owner} if core and core[-1].owner else set()
        enabling = {a.owner for a in core[:-1] if a.owner} - bound
        evidence = [(tr.before,
                     {q: tr.before.objs.get(v) for q, v in tr.binding.items()
                      if isinstance(v, tuple)})
                    for tr in op.positives]
        got = referring.ground(op, evidence, bound,
                               inducer.memorises_the_fitting_instance,
                               referring.collection_types(inducer.A), enabling=enabling)
        if got.queries:
            out[op.name] = dict(got.queries)
    return out


def evaluate(run_dir: Path, reading, *, split: float = 0.6, min_support: int = 2,
             mutate: Callable[[str], str] | None = None,
             evaluate_on: str = "suffix", applicability: str = ASSERTED,
             correspondence: str = MASKED) -> ScopedResult:
    """Fit on the first ``split`` of the history; predict the rest; check where it landed."""
    return score(fit(run_dir, reading, split=split, min_support=min_support),
                 mutate=mutate, evaluate_on=evaluate_on, applicability=applicability,
                 correspondence=correspondence)


def score(model: Fit, *, mutate: Callable[[str], str] | None = None,
          evaluate_on: str = "suffix", applicability: str = ASSERTED,
          correspondence: str = MASKED) -> ScopedResult:
    """Check a fitted reading's rules against the raw page, where each one lands.

    `evaluate_on` lets the conditional search ask for the same verdicts over the prefix.
    It never changes what the rules were fitted on."""
    A, operators, full, cut = model.abstractor, model.operators, model.log, model.cut
    reading, split = model.reading, model.split
    by_control = _single_click_operators(operators)

    result = ScopedResult(
        reading=getattr(reading, "name", "?"), split=split, applicability=applicability,
        correspondence_rule=correspondence, fitted_on_steps=cut,
        evaluated_steps=len(full.steps) - cut, operators=len(operators),
        single_act_operators=sum(len(v) for v in by_control.values()),
        regime=model.regime, model=_model_summary(operators))
    relocate = matcher(correspondence, corr.Corresponder())
    # Survival is asked with the content layers only.  Letting the descent fall through to
    # role and position would answer "still there" for a panel replaced by a different panel
    # of the same shape, which is the one answer a removal check must never give for free.
    gone = corr.Corresponder(ladder=(corr.DEEP, corr.LOCAL))
    bridges: dict[int, dict[tuple[int, str], int]] = {}
    states: dict[int, Any] = {}

    # "next" is the prequential evaluation point: the one action standing immediately after
    # everything the model was allowed to learn from.
    evaluated = {"suffix": full.steps[cut:], "prefix": full.steps[:cut],
                 "next": full.steps[cut:cut + 1], "all": full.steps}[evaluate_on]
    result.evaluated_steps = len(evaluated)
    for step in evaluated:
        if step.action.kind != "click" or step.action.target is None:
            continue
        pre, post = full.obs(step.before), full.obs(step.after)
        control = clicked_control(A, pre, step)
        rules = by_control.get(control) or by_control.get(action_control(step))
        if not rules:
            result.skipped["no rule fitted for this control"] += 1
            continue
        state = states.get(id(pre))
        if state is None:
            state = states[id(pre)] = A.abstract(pre)
        po = A.parsed(pre)
        bridge = bridges.get(id(pre))
        if bridge is None:
            bridge = bridges[id(pre)] = slot_nodes(A, pre)
        # Within one step every assignment of every rule asks about the same pair of pages,
        # so relocation depends only on the node. That recomputation is the whole cost of
        # scoring. The cache lives for one step so no page outlives it.
        step_relocate = _for_one_step(relocate)
        step_gone = _for_one_step(gone)
        for op in rules:
            bound, why = bindings_for(A, po, state, op, step.action.target, applicability,
                                      model.queries.get(op.name))
            _record_schema(result, op, bound)
            for eff in op.effs:
                claim = _claim(op, eff, mutate)
                if claim is None:
                    continue
                kind, slot, predicted = claim
                base = ScopedPrediction(
                    step=step.step, control=control, operator=op.name, kind=kind,
                    support=len(op.positives), slot=slot, predicted=predicted)
                if why:
                    base.verdict, base.detail = NOT_APPLICABLE, why
                    result.predictions.append(base)
                    continue
                base.bindings = len(bound.admissible)
                base.binding_status = bound.status
                base.binding_truncated = bound.truncated
                if bound.status in (binding.UNOBSERVED, binding.UNSETTLED, binding.UNNAMED):
                    # Three different ways of not knowing -- nothing of that type was
                    # rendered, the search could not finish, or the rule cannot say which
                    # object it is about here -- and none is evidence about the rule.
                    base.verdict, base.detail = UNKNOWN, bound.detail
                    result.predictions.append(base)
                    continue
                if bound.status == binding.NONE:
                    base.verdict, base.detail = NOT_APPLICABLE, bound.detail
                    result.predictions.append(base)
                    continue
                assignments = bound.admissible
                if kind is CREATION:
                    # A creation claim is about the values the new object will carry, so two
                    # assignments that resolve them the same way are one claim. Evaluating
                    # them separately asked the same question a hundred times.
                    assignments = _distinct_by(assignments,
                                               lambda a: _creation_values(eff, a))
                parts = [_under_one_binding(base, A, bridge, pre, post, step, op, eff,
                                            assignment, step_relocate, step_gone, states,
                                            predicted)
                         for assignment in assignments]
                aggregated = _aggregate(base, parts, bound)
                result.predictions.append(aggregated)
                if aggregated.identity is not None:
                    result.predictions.append(aggregated.identity)
    return result


def _for_one_step(match):
    """`match` memoised for the one transition it is about.

    Correspondence depends only on the two pages and the node, and within a step the pages
    do not change. Keying on the node alone keeps no page alive past its own step."""
    seen: dict[int, Any] = {}

    def once(pre, post, node):
        found = seen.get(node)
        if found is None:
            found = seen[node] = match(pre, post, node)
        return found

    return once


def _record_schema(result: ScopedResult, op, bound) -> None:
    """Note, for this firing, which derived parameters the pre-state pinned.

    A firing that produced no binding at all says nothing either way about whether the
    parameter can be determined, so it is not counted rather than counted as open.
    """
    if bound is None or not bound.admissible:
        return
    row = result.schema_evidence.get(op.name)
    if row is None:
        row = result.schema_evidence[op.name] = {
            "derived": set(),
            "effect_params": {e.obj for e in op.effs if e.kind != "emit"},
            "output_params": {v for e in op.effs if e.kind == "emit"
                              for v in [e.obj] + [x for _, x in e.attrs]
                              if isinstance(v, str) and v.startswith("?")},
            "seen": Counter(), "pinned": Counter()}
    pinned = bound.pinned()
    for param, origin in bound.admissible[0].provenance.items():
        if origin != binding.DERIVED:
            continue
        row["derived"].add(param)
        row["seen"][param] += 1
        row["pinned"][param] += param in pinned


def _claim(op, eff, mutate):
    """What this effect asserts about the page, or ``None`` if it asserts nothing testable."""
    if eff.kind == "emit":
        # The claim is about the live region after the action: which event it reads, and
        # about which objects. No correspondence needed: the region is one stable node.
        return OUTPUT, eff.slot, (mutate(eff.slot) if mutate else eff.slot)
    if eff.kind == "add":
        # The claim is that the page will render a structure it did not render before, carrying
        # these values together.  What "these values" are depends on the binding, so the
        # predicted text is filled in where the binding is known.
        return CREATION, "id", "new"
    if eff.kind == "remove":
        return EXISTENCE, "id", "gone"
    if eff.kind != "set" or eff.slot is None:
        return None
    if eff.new is VARIES:
        # The learner has said this slot changes without saying to what, because the action
        # does not determine the value.  That is still a claim the page can refute -- the slot
        # may not change at all -- and dropping it would turn a generalisation into silence.
        return VALUE, eff.slot, CHANGES
    if isinstance(eff.new, str):
        return VALUE, eff.slot, (mutate(eff.new) if mutate else eff.new)
    return None


def _under_one_binding(base, A, bridge, pre, post, step, op, eff, assignment, relocate, gone,
                       states, predicted) -> ScopedPrediction:
    """The verdict this effect gets if *this* assignment is the one that happened."""
    pred = ScopedPrediction(
        step=base.step, control=base.control, operator=base.operator, kind=base.kind,
        support=base.support, slot=base.slot, predicted=base.predicted,
        binding_evidence=assignment.evidence)
    if base.kind is OUTPUT:
        return _output_prediction(pred, A, post, eff, assignment, predicted)
    if base.kind is CREATION:
        return _creation_prediction(pred, pre, post, eff, assignment)
    subject = assignment.get(eff.obj)
    if subject is None or getattr(subject, "node", None) is None:
        pred.verdict = NOT_APPLICABLE
        pred.detail = "the effect is about an object this assignment does not bind"
        return pred
    pred.subject = str(subject.key)
    pred.context = binding_context(assignment.values)
    if base.kind is EXISTENCE or eff.kind == "remove":
        survives = _existence_prediction(A, bridge, pre, post, step, base.control, op,
                                         assignment.values, eff, gone)
        if survives is None:
            return pred
        survives.binding_evidence = assignment.evidence
        return survives
    node = bridge.get((subject.node, eff.slot))
    if node is None:
        pred.verdict = NOT_APPLICABLE
        pred.detail = f"the reading does not render {eff.slot} anywhere in this object"
        return pred
    held = (subject.key if _is_key_slot(A, subject, eff.slot) else subject.attrs.get(eff.slot))
    rendered = leaf_value(pre.node(node))
    pred.held_before = str(rendered)
    if _rendered_as(held) != _rendered_as(rendered):
        # ``attr:col`` is the clear case: it is the column label *about* a cell, and the cell
        # renders its own contents instead.  Checking a predicted value against the node's text
        # would compare two different things, and did.
        pred.verdict = NOT_APPLICABLE
        pred.detail = (f"{eff.slot} holds {held!r} but the node it was read from renders "
                       f"{rendered!r}, so this slot is not that node's text and a page check "
                       f"cannot stand in for it")
        return pred
    pred.feature_node = node
    pred.action_local = action_local(pre, step.action.target, node)
    match = relocate(pre, post, node)
    pred.correspondence, pred.admissible, pred.layers = (match.status, match.admissible,
                                                         match.layers)
    _value_verdict(pred, post, match, subject, A, eff, predicted)
    if _is_key_slot(A, subject, eff.slot):
        after = states.get(id(post))
        if after is None:
            after = states[id(post)] = A.abstract(post)
        pred.identity = _identity_prediction(pred, after, match, predicted)
    return pred


def _aggregate(base: ScopedPrediction, parts: list[ScopedPrediction], bound
               ) -> ScopedPrediction:
    """One verdict for the rule at this step, over every assignment still open.

    The rule fired once. Several open assignments are competing guesses about which one it
    was, not a claim about each, so one assignment whose consequence holds stops a
    refutation. Refuting requires every open assignment to be contradicted, and an
    assignment that could not be tested counts against refuting."""
    decided = [p for p in parts if p.verdict in (SUPPORTED, REFUTED, POSSIBLE)]
    verdicts = {p.verdict for p in parts}
    # The witness quoted stands for the aggregate, not for its best case: a supported
    # assignment where the verdict is supported, otherwise the first one decided at all.
    winner = (next((p for p in parts if p.verdict == SUPPORTED), None)
              if verdicts == {SUPPORTED} else None)
    winner = winner or (decided[0] if decided else (parts[0] if parts else base))
    for field_name in ("subject", "context", "held_before", "feature_node", "action_local",
                       "correspondence", "admissible", "layers", "observed", "expected"):
        setattr(base, field_name, getattr(winner, field_name, getattr(base, field_name)))
    base.identity = _aggregate_identity(base, parts, bound)
    base.binding_evidence = ("/".join(sorted({p.binding_evidence for p in parts}))
                            if parts else "")
    if bound.truncated:
        # Deduplicating assignments can leave one representative consequence, but it
        # cannot make an incomplete binding search exhaustive in either direction.
        counts = Counter(p.verdict for p in parts)
        observed = ", ".join(f"{verdict}={counts[verdict]}" for verdict in
                             (SUPPORTED, REFUTED, POSSIBLE, UNKNOWN, NOT_APPLICABLE))
        base.binding_truncated = True
        base.verdict = POSSIBLE if decided else UNKNOWN
        base.detail = (f"the binding search is incomplete: {len(bound.admissible)} assignments "
                       f"retained; {len(parts)} representative consequences evaluated; "
                       f"observed consequence verdicts: {observed}")
        if parts:
            base.detail += f"; representative evidence: {winner.detail}"
        return base
    if not decided:
        base.verdict = parts[0].verdict if parts else NOT_APPLICABLE
        base.detail = (parts[0].detail if parts else "no assignment binds this effect")
        return base
    if verdicts == {SUPPORTED}:
        base.verdict, base.detail = SUPPORTED, winner.detail
    elif verdicts == {REFUTED} and not bound.truncated:
        base.verdict = REFUTED
        base.detail = (winner.detail if len(parts) == 1 else
                       f"every one of the {len(parts)} assignments the pre-state leaves open "
                       f"is contradicted: {winner.detail}")
    elif SUPPORTED in verdicts and len(parts) > 1:
        base.verdict = POSSIBLE
        base.detail = (f"{sum(1 for p in parts if p.verdict == SUPPORTED)} of {len(parts)} "
                       f"assignments the pre-state leaves open support this and the evidence "
                       f"does not say which one happened")
    else:
        base.verdict = POSSIBLE if len(parts) > 1 else decided[0].verdict
        base.detail = (decided[0].detail if len(parts) == 1 else
                       f"the {len(parts)} assignments the pre-state leaves open disagree, "
                       f"so this step does not settle the rule")
    return base


def _aggregate_identity(base: ScopedPrediction, parts: list[ScopedPrediction], bound):
    """The naming check, over the same assignments and by the same rule.

    Reporting it for one chosen assignment would let a reading be judged on whichever of its
    candidate objects it named correctly, which is the leak this whole layer exists to close.
    """
    named = [p.identity for p in parts if p.identity is not None]
    if not named:
        return None
    carrier = ScopedPrediction(
        step=base.step, control=base.control, operator=base.operator, kind=IDENTITY,
        support=base.support, slot=base.slot, predicted=base.predicted,
        expected=base.predicted, bindings=base.bindings,
        binding_status=base.binding_status)
    return _aggregate(carrier, named, bound)


def matcher(kind: str, corresponder):
    """Which correspondence rule to check predictions against, including the broken ones.

    A conclusion that survives all of them is not an artefact of the instrument; one that
    appears under only one of them is. `unmasked` lets the correspondence use the very
    property being predicted; `same_index` assumes the page re-renders in place."""
    if kind == NEAR_OPTIMAL:
        wider = corr.Corresponder(corresponder.descriptors, tolerance=1)
        return lambda pre, post, node: wider(pre, post, node, corr.mask_outcome(pre, node))
    if kind == UNMASKED:
        return lambda pre, post, node: corresponder(pre, post, node, {})
    if kind == SAME_INDEX:
        def by_index(pre, post, node):
            if node < len(post.nodes) and post.node(node).role == pre.node(node).role:
                return corr.Correspondence(node, (node,), corr.UNIQUE, ("SAME_INDEX",),
                                           "the node kept its position in the tree")
            return corr.Correspondence(node, (), corr.NONE, ("SAME_INDEX",),
                                       "no node of that role at that position")
        return by_index
    return lambda pre, post, node: corresponder(pre, post, node, corr.mask_outcome(pre, node))


def _rendered_as(value) -> str | None:
    """The comparable form of a slot value: what it would look like as rendered text."""
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value)
    return str(split_literal(value)[0]) if isinstance(value, str) else str(value)


def _model_summary(operators) -> dict[str, Any]:
    """What the fit itself looks like, carried alongside the verdicts.

    A refutation count says nothing about whether the learner was given the repairs it can
    make. These are the facts that do: counterexamples left unexplained, the forms of
    condition used, and how many effect values the action does not fix."""
    vocabulary: Counter = Counter()
    undetermined = 0
    for op in operators:
        for literal in op.pre:
            vocabulary[literal[0]] += 1
        for eff in op.effs:
            values = ([eff.new] if eff.kind in ("set", "rel", "forall_set", "forall_rel")
                      else [v for _, v in eff.attrs] + [v for _, v in eff.refs])
            undetermined += sum(1 for v in values if v is VARIES)
    return {"operators": len(operators),
            "unexplained_counterexamples": sum(op.unexplained_negatives for op in operators),
            "learned_precondition_vocabulary": dict(sorted(vocabulary.items())),
            "effect_values_the_action_does_not_determine": undetermined,
            "rules_supported_by_one_transition": sum(1 for op in operators
                                                     if len(op.positives) == 1)}


def _existence_prediction(A, bridge, pre, post, step, control, op, binding, eff, gone):
    """A rule that says an object goes away, checked where that object was rendered.

    Some readings are entirely about existence: every fitted rule makes objects appear or
    disappear and none predicts what anything will say. A value check reports nothing
    there, so the same correspondence answers the other question instead, by relocating
    the node that rendered the object's name and asking whether it still says it.

    Nothing is masked here: the claim is that the object is gone, so its rendered name is
    evidence rather than the answer."""
    subject = binding.get(eff.obj)
    if subject is None or subject.node is None or subject.node < 0:
        return None
    node = bridge.get((subject.node, "id"), subject.node)
    if node >= len(pre.nodes):
        return None
    pred = ScopedPrediction(
        step=step.step, control=control, operator=op.name, kind=EXISTENCE,
        support=len(op.positives), slot="id", predicted="gone", expected="gone",
        subject=str(subject.key), feature_node=node,
        action_local=action_local(pre, step.action.target, node),
        context=binding_context(binding))
    match = gone(pre, post, node)
    pred.correspondence, pred.admissible, pred.layers = (match.status, match.admissible,
                                                         match.layers)
    if match.status == corr.NONE:
        pred.verdict = SUPPORTED
        pred.detail = "nothing in the later observation continues the structure that rendered it"
        return pred
    rendered = str(leaf_value(pre.node(node)))
    seen = [str(leaf_value(post.node(j))) for j in match.admissible]
    pred.observed = tuple(seen)
    still = sum(1 for x in seen if x == rendered)
    if still == len(seen):
        pred.verdict = REFUTED
        pred.detail = f"the continuation still renders {rendered!r}, so the object did not go"
    elif still == 0:
        pred.verdict = SUPPORTED
        pred.detail = f"no admissible continuation still renders {rendered!r}"
    else:
        pred.verdict = POSSIBLE
        pred.detail = "some admissible continuations still render it and some do not"
    return pred


def _output_prediction(pred: ScopedPrediction, A, post, eff, assignment, predicted: str
                       ) -> ScopedPrediction:
    """Did the live region say the event this rule predicted, about these objects?

    Checked against the raw later page, lifted by the same frozen vocabulary the model was
    fitted with. The reading supplies only which objects it thinks the click was about, so
    this asks two things at once on purpose: an event predicted about the wrong object is
    not a correct prediction.

    No correspondence layer: a live region is one stable node and the claim is about what
    it says, not about following a node across a change."""
    observed = emit_mod.live_text(post)
    if observed is None:
        pred.verdict = NOT_APPLICABLE
        pred.detail = "this application renders no live region, so it returns nothing to check"
        return pred
    args = []
    for _, value in eff.attrs:
        if value is VARIES:
            args.append(None)     # the action does not determine this argument: not checked
            continue
        if isinstance(value, tuple) and len(value) == 3 and value[0] in ("attr", "ref"):
            # a determinable argument: what the bound object's own attribute or reference
            # renders on the pre-action page (`induce`: the lifted dereference), read at
            # prediction time exactly as a relation query re-follows its slot
            obj = assignment.get(value[1])
            if obj is None:
                held = None
            elif value[0] == "attr":
                held = obj.attrs.get(value[2])
            else:
                ref = obj.refs.get(value[2])
                held = None if ref is None else ref[1]
            if held is None:
                args.append(None)          # the page does not determine it here: unchecked
            else:
                args.append(str(held))
            continue
        if isinstance(value, str) and value.startswith("?"):
            obj = assignment.get(value)
            if obj is None:
                pred.verdict = UNKNOWN
                pred.detail = f"the rule does not say which object {value} is here"
                return pred
            args.append(str(obj.key))
        else:
            args.append(str(value))
    subject = assignment.get(eff.obj) if eff.obj else None
    pred.subject = str(subject.key) if subject is not None else ""
    pred.context = binding_context(assignment.values)
    event = emit_mod.lift_event(observed, post, vocabulary=getattr(A, "emissions", None))
    pred.expected = emit_mod.render(predicted, ["*" if a is None else a for a in args])
    pred.observed = (event.frame,) + tuple(event.args)
    pred.held_before = observed
    if event.frame != predicted:
        pred.verdict = REFUTED
        pred.detail = (f"predicted the interface to return {pred.expected!r}; it returned "
                       f"{observed!r}, which is a different event")
        return pred
    if any(a is not None and (i >= len(event.args) or event.args[i] != a)
           for i, a in enumerate(args)):
        pred.verdict = REFUTED
        pred.detail = (f"predicted {pred.expected!r}; the interface returned the same event "
                       f"about {list(event.args)} rather than {args}")
        return pred
    pred.verdict = SUPPORTED
    pred.detail = f"the interface returned {observed!r}"
    return pred


def _nodes_rendering(obs, value: str) -> frozenset:
    """Nodes whose subtree renders `value`, memoised per page.

    One pass per distinct value per page. Doing it per claim instead is the difference
    between a test that runs and one that does not."""
    from semabi.compiler.v4.emission import tokens as _tokens

    index = getattr(obs, "_rendering_index", None)
    if index is None:
        index = obs._rendering_index = {}
    hit = index.get(value)
    if hit is not None:
        return hit
    under = getattr(obs, "_subtree_texts", None)
    if under is None:
        under = {}
        for n in reversed(obs.nodes):
            got = set()
            for text in (n.name, n.value):
                if text:
                    got.add(text)
                    got.update(_tokens(text))
            for child in obs.children(n.i):
                got |= under.get(child, set())
            under[n.i] = got
        obs._subtree_texts = under
    want = _tokens(value)
    hit = frozenset(i for i, got in under.items()
                    if value in got or (want and all(t in got for t in want)))
    index[value] = hit
    return hit


def _creation_witnesses(obs, values: list[str]) -> int:
    """Minimal subtrees rendering all of ``values``.

    Minimal so that a witness is not counted again for every ancestor of it, and counted rather
    than sought so that the check is a *change*: blend's draw form renders the vat, the blend
    and the amount before the click as well as after, and asking only whether the page shows
    them somewhere would be answered by the form the click was made from.
    """
    if not values:
        return 0
    holds = _nodes_rendering(obs, values[0])
    for value in values[1:]:
        holds &= _nodes_rendering(obs, value)
        if not holds:
            return 0
    return sum(1 for i in holds if not any(c in holds for c in obs.children(i)))


def _distinct_by(items, key):
    seen, out = set(), []
    for item in items:
        k = key(item)
        if k in seen:
            continue
        seen.add(k)
        out.append(item)
    return tuple(out)


def _creation_values(eff, assignment) -> tuple:
    """The values a creation claim is about, under one assignment."""
    out = []
    for _slot, value in tuple(eff.attrs) + tuple(eff.refs):
        if value is VARIES or value is None or (
                isinstance(value, tuple) and len(value) == 3 and value[0] in ("attr", "ref")):
            out.append(None)
        elif isinstance(value, str) and value.startswith("?"):
            obj = assignment.get(value)
            out.append(None if obj is None else str(obj.key))
        elif isinstance(value, str) and value:
            out.append(split_literal(value)[0])
        else:
            out.append(None)
    return tuple(out)


def _creation_prediction(pred: ScopedPrediction, pre, post, eff, assignment
                         ) -> ScopedPrediction:
    """Did the page gain a structure rendering, together, what the new object is said to carry?

    Creation was the one effect kind nothing scored.  A ``remove`` claim is checked by
    relocating the node that rendered the object; a created object has no node in the earlier
    page to relocate, so the check is the other way round -- the values the rule says the new
    object carries, sought as a *minimal* subtree of the later page and counted against the
    earlier one.  The reading supplies which objects the rule is about and what it says they
    are called; the page decides.

    A value the action does not determine is not part of the claim.  A rule that determines
    none of them is not making a checkable one.
    """
    values: list[str] = []
    undetermined = 0
    for _slot, value in tuple(eff.attrs) + tuple(eff.refs):
        if value is VARIES or value is None or (
                isinstance(value, tuple) and len(value) == 3 and value[0] in ("attr", "ref")):
            undetermined += 1
            continue
        if isinstance(value, str) and value.startswith("?"):
            obj = assignment.get(value)
            if obj is None:
                undetermined += 1
                continue
            values.append(str(obj.key))
        elif isinstance(value, str) and value:
            values.append(split_literal(value)[0])
    pred.context = binding_context(assignment.values)
    if not values:
        pred.verdict = UNKNOWN
        pred.detail = (f"the rule determines none of the {undetermined} values it says the new "
                       f"object carries, so it does not say what would appear")
        return pred
    pred.expected = " + ".join(values)
    before = _creation_witnesses(pre, values)
    after = _creation_witnesses(post, values)
    pred.held_before = f"{before} structures carried these values before"
    pred.observed = (f"{after} after",)
    if after > before:
        pred.verdict = SUPPORTED
        pred.detail = (f"the page gained a structure carrying {values}: {before} -> {after}")
    else:
        pred.verdict = REFUTED
        pred.detail = (f"no structure carrying {values} appeared: {before} -> {after}")
    return pred


def _is_key_slot(A, subject, slot: str) -> bool:
    ti = A.types.get(subject.tid)
    return ti is not None and slot == ti.key_slot


def _value_verdict(pred: ScopedPrediction, post, match, subject, A, eff, predicted: str) -> None:
    """Did the continuation of the node this effect is about take the predicted text?"""
    if predicted is CHANGES:
        expected = CHANGES
    else:
        expected = (split_literal(predicted)[0] if _is_key_slot(A, subject, eff.slot)
                    else predicted)
    pred.expected = expected
    if match.status == corr.NONE:
        pred.verdict, pred.detail = UNKNOWN, match.detail
        return
    seen = [leaf_value(post.node(j)) for j in match.admissible]
    pred.observed = tuple(str(x) for x in seen)
    hits = (sum(1 for x in seen if str(x) != pred.held_before) if expected is CHANGES
            else sum(1 for x in seen if x == expected))
    if hits == len(seen):
        pred.verdict = SUPPORTED
        shown = "a different value" if expected is CHANGES else repr(expected)
        pred.detail = (f"every admissible continuation renders {shown}"
                       if len(seen) > 1 else f"the continuation renders {shown}")
    elif hits == 0:
        pred.verdict = REFUTED
        shown = "a different value" if expected is CHANGES else repr(expected)
        pred.detail = (f"no admissible continuation renders {shown}; "
                       f"they render {sorted(set(map(str, seen)))}")
    else:
        pred.verdict = POSSIBLE
        pred.detail = (f"{hits} of {len(seen)} admissible continuations render {expected!r}, "
                       f"so the correspondence does not settle this")


def _identity_prediction(base: ScopedPrediction, after, match, predicted: str
                         ) -> ScopedPrediction:
    """The reading's own name for the continuation, against the name it predicted.

    Only a reading whose entity names collide makes this claim, because only such a reading
    has to say which copy an object becomes.  It is the reading's key function applied to an
    unmodified later page, so the page still arbitrates; it is kept apart from ``VALUE``
    because it is the one check that reads the later observation through the reading.
    """
    pred = ScopedPrediction(
        step=base.step, control=base.control, operator=base.operator, kind=IDENTITY,
        support=base.support, slot=base.slot, predicted=predicted, subject=base.subject,
        expected=predicted, feature_node=base.feature_node,
        correspondence=base.correspondence, admissible=base.admissible, layers=base.layers)
    if match.status == corr.NONE:
        pred.verdict, pred.detail = UNKNOWN, match.detail
        return pred
    by_node = {o.node: o for o in after.objs.values()}
    keys = [by_node[j].key if j in by_node else None for j in match.admissible]
    pred.observed = tuple("-" if k is None else str(k) for k in keys)
    if all(k is None for k in keys):
        pred.verdict = UNKNOWN
        pred.detail = "the reading reads no object at the continuation, so it names nothing"
        return pred
    hits = sum(1 for k in keys if k == predicted)
    if hits == len(keys):
        pred.verdict, pred.detail = SUPPORTED, f"the reading names the continuation {predicted!r}"
    elif hits == 0:
        pred.verdict = REFUTED
        pred.detail = (f"the reading predicted the name {predicted!r} and names the "
                       f"continuation {sorted({str(k) for k in keys})}")
    else:
        pred.verdict = POSSIBLE
        pred.detail = f"{hits} of {len(keys)} admissible continuations are named {predicted!r}"
    return pred
