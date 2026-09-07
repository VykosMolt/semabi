"""Prepared O-REP/oracle-formula micro-control; execute only after contract review.

The only semantic calls are native supplied-state binding, reference-query
grounding/evaluation, and state differencing. No learner fitting or trace occurs.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from semabi.compiler.abstract import AbsObj, AbstractState, diff
from semabi.compiler.induce import ActT, EffT, OperatorHyp
from semabi.compiler.v4 import binding, referring
from semabi.compiler.v4.consequence import _named_by_query


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def verify_freeze(freeze):
    found = {name: digest_file(ROOT / name) for name in freeze["files"]}
    if found != freeze["files"] or source_head() != freeze["source_head"]:
        raise AssertionError("frozen source/head/instrument changed")
    return {"source_head": source_head(), "files": found}


def state_json(state):
    return {"objects": [asdict(obj) for _, obj in sorted(state.objs.items())],
            "view": state.view, "partial": state.partial}


def operator_json(op):
    return {"name": op.name, "params": op.params, "acts": [asdict(act) for act in op.acts],
            "effects": [asdict(eff) for eff in op.effs], "pre": op.pre}


def make_cell(spec, label):
    X, M, Z = (spec["types"][kind] for kind in ("X", "M", "Z"))
    objects = [AbsObj(X, key, {}) for key in spec["sources"]]
    objects += [AbsObj(Z, key, {"flag": False}) for key in spec["targets"]]
    objects += [AbsObj(M, key, {}, refs={"left": (X, left), "right": (Z, right)})
                for key, left, right in zip(spec["bridges"], spec["left"], spec["right"][label])]
    state = AbstractState({obj.id: obj for obj in objects}, {})
    assert len(state.objs) == 8
    assert Counter(obj.tid for obj in objects) == {X: 2, M: 4, Z: 2}
    assert Counter(obj.refs["left"] for obj in objects if obj.tid == M) == {
        (X, key): 2 for key in spec["sources"]}
    assert Counter(obj.refs["right"] for obj in objects if obj.tid == M) == {
        (Z, key): 2 for key in spec["targets"]}
    return state


def make_operator(spec, name, chain=False):
    X, M, Z = (spec["types"][kind] for kind in ("X", "M", "Z"))
    effects = [EffT("set", Z, "?z", "flag", False, True)]
    if chain:
        effects.insert(0, EffT("set", M, "?m", "flag", False, True))
    return OperatorHyp(name, (ActT("click", None, "?x"),), tuple(effects),
                       {"?x": X, "?m": M, "?z": Z})


def solve_record(op, formula, state, seeds, *, limit=None):
    kwargs = {} if limit is None else {"limit": limit}
    found = binding.solve(op, formula, state, seeds, **kwargs)
    return {
        "supplied_query_arguments": {var: obj.id for var, obj in seeds.items()},
        "native_seed_provenance_note": "ACTION labels supplied solver arguments, not observed click provenance",
        "native": found.to_json(),
        "assignments": [{"typed_values": {var: obj.id for var, obj in row.values.items()},
                         "native": row.to_json(),
                         "holds": [binding.holds(literal, row.values, state) for literal in formula]}
                        for row in found.admissible],
        "assignment_count": len(found.admissible), "truncated": found.truncated,
        "projected_targets": [values[0] for values in found.denotations(("?z",))],
        "effect_target": found.effect_target(("?z",)),
        "answer_limit": binding.MAX_ADMISSIBLE if limit is None else limit,
        "search_node_limit": binding.MAX_SEARCH_NODES,
    }


def primary_control(spec):
    op = make_operator(spec, "supplied_join_formula")
    formula = [tuple(literal) for literal in spec["formula"]]
    states, cases = {}, []
    X, M, Z = (spec["types"][kind] for kind in ("X", "M", "Z"))
    for label in spec["state_order"]:
        state = make_cell(spec, label)
        states[label] = state_json(state)
        for i, (x, z) in enumerate(spec["endpoint_order"]):
            seeds = {"?x": state.objs[X, x], "?z": state.objs[Z, z]}
            candidates = []
            for m in spec["bridges"]:
                values = {**seeds, "?m": state.objs[M, m]}
                holds = [binding.holds(literal, values, state) for literal in formula]
                candidates.append({"witness": (M, m), "holds": holds,
                                   "conjunction": all(value is True for value in holds)})
            solved = solve_record(op, formula, state, seeds)
            expected = spec["expected_assignment_counts"][label][i]
            expected_status = {0: binding.NONE, 1: binding.UNIQUE, 2: binding.AMBIGUOUS}[expected]
            checks = {"assignment_count": solved["assignment_count"] == expected,
                      "holds_count": sum(row["conjunction"] for row in candidates) == expected,
                      "holds_decided": all(value is not None for row in candidates for value in row["holds"]),
                      "assignment_status": solved["native"]["status"] == expected_status,
                      "complete": not solved["truncated"],
                      "effect_projection": solved["effect_target"] == (
                          (binding.DETERMINED, 1) if expected else (binding.INAPPLICABLE, 0)),
                      "target_identity": solved["projected_targets"] == ([(Z, z)] if expected else [])}
            cases.append({"state": label, "source": x, "target": z, "expected_count": expected,
                          "candidate_witnesses": candidates, "solver": solved, "checks": checks})
    return {"intervention": spec["intervention"], "formula": formula, "operator": operator_json(op),
            "states": states, "planned_cases": 12, "cases": cases,
            "checks_passed": len(cases) == 12 and all(all(row["checks"].values()) for row in cases)}


def chain_control(spec):
    X, M, Z = (spec["types"][kind] for kind in ("X", "M", "Z"))
    objects = []
    for x, m, z in spec["chain"]["edges"]:
        objects += [AbsObj(X, x, {}, refs={"next": (M, m)}),
                    AbsObj(M, m, {"flag": False}, refs={"next": (Z, z)}),
                    AbsObj(Z, z, {"flag": False})]
    state = AbstractState({obj.id: obj for obj in objects}, {})
    assert len(state.objs) == 6 and Counter(obj.tid for obj in objects) == {X: 2, M: 2, Z: 2}
    op = make_operator(spec, "supplied_forward_chain_with_intermediate_effect", chain=True)
    formula = [tuple(literal) for literal in spec["chain"]["formula"]]
    evidence, supervised = [], []
    for x, m, z in spec["chain"]["edges"]:
        values = {"?x": state.objs[X, x], "?m": state.objs[M, m], "?z": state.objs[Z, z]}
        after = copy.deepcopy(state)
        after.objs[M, m].attrs["flag"] = True
        after.objs[Z, z].attrs["flag"] = True
        delta = diff(state, after)
        evidence.append((state, values))
        supervised.append({"binding": {var: obj.id for var, obj in values.items()},
                           "supplied_after": state_json(after), "native_attribute_changes": delta.attr_changes,
                           "both_effects_present": set(delta.attr_changes) == {
                               ((M, m), "flag", False, True), ((Z, z), "flag", False, True)}})
    filter_calls = []

    def allow_property(_op, literal):
        filter_calls.append(literal)
        return False

    grounded = referring.ground(op, evidence, {"?x"}, allow_property)
    queries = {var: asdict(query) for var, query in grounded.queries.items()}
    evaluations = []
    for x, m, z in spec["chain"]["edges"]:
        seeds = {"?x": state.objs[X, x]}
        named = _named_by_query(op, state, seeds, grounded.queries)
        denotations = {var: [obj.id for obj in query.denotation(op, state, {**seeds, **named})]
                       for var, query in grounded.queries.items()}
        solved = solve_record(op, formula, state, {**seeds, **named})
        evaluations.append({"source": x, "named_by_native_queries": {var: obj.id for var, obj in named.items()},
                            "query_denotations": denotations, "solver": solved,
                            "correct_chain": {var: obj.id for var, obj in named.items()} == {
                                "?m": (M, m), "?z": (Z, z)}
                                and solved["assignment_count"] == 1 and not solved["truncated"]
                                and solved["projected_targets"] == [(Z, z)]})
    expected_queries = {"?m": (("?x",), ("forward", "next")),
                        "?z": (("?m",), ("forward", "next"))}
    query_check = set(grounded.queries) == set(expected_queries) and all(
        query.kind == referring.RELATION and (query.given, query.form) == expected_queries[var]
        for var, query in grounded.queries.items())
    return {"intervention": "supplied six-object graph and two-effect supervision; native query production",
            "state": state_json(state), "operator": operator_json(op), "oracle_formula_for_scoring_only": formula,
            "supervision": supervised, "native_grounding": grounded.to_json(), "query_forms": queries,
            "property_filter": "all property candidates allowed; no memorisation-policy competence claim",
            "property_filter_calls": filter_calls, "evaluations": evaluations,
            "checks_passed": query_check and all(row["both_effects_present"] for row in supervised)
                and all(row["correct_chain"] for row in evaluations)}


def bounded_search_control(spec):
    control = spec["bounded_search"]
    state = make_cell(spec, control["state"])
    op = make_operator(spec, "separate_source_only_truncation_diagnostic")
    formula = [tuple(literal) for literal in spec["formula"]]
    seeds = {"?x": state.objs[spec["types"]["X"], control["source"]]}
    complete = solve_record(op, formula, state, seeds)
    limited = solve_record(op, formula, state, seeds, limit=control["limited_answers"])
    actual = sorted([row["typed_values"][var][1] for var in ("?x", "?m", "?z")]
                    for row in complete["assignments"])
    known = sorted(control["expected_complete_assignments"])
    missing = limited["assignment_count"] < complete["assignment_count"]
    return {"scope": "separate computational diagnostic, excluded from 12 primary cases",
            "source_only_query": seeds["?x"].id, "known_complete_assignments": known,
            "default_result": complete, "limit_one_result": limited,
            "known_space_confirmed": actual == known and not complete["truncated"],
            "known_assignments_omitted": missing,
            "lost_truncation_flag_reproduced": missing and not limited["truncated"],
            "false_unique_assignment_reproduced": missing and limited["native"]["status"] == binding.UNIQUE,
            "false_target_determinacy_reproduced": complete["effect_target"][0] == binding.UNDERDETERMINED
                and limited["effect_target"][0] == binding.DETERMINED}


def main(output):
    if output.exists():
        raise FileExistsError(output)
    freeze = json.loads((HERE / "freeze.json").read_text())
    before = verify_freeze(freeze)
    spec = json.loads((HERE / "contract.json").read_text())
    result = {"schema": "semabi.join_native_control.result.v1", "before": before,
              "primary": primary_control(spec), "forward_chain": chain_control(spec),
              "bounded_search": bounded_search_control(spec),
              "learner_fits": 0, "browser_actions": 0, "observational_learning_claim": False}
    result["after"] = verify_freeze(freeze)
    result["protocol_checks_passed"] = result["primary"]["checks_passed"] \
        and result["forward_chain"]["checks_passed"] and result["bounded_search"]["known_space_confirmed"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"protocol_checks_passed": result["protocol_checks_passed"],
                      "primary_cases": len(result["primary"]["cases"]),
                      "bounded_search": {key: value for key, value in result["bounded_search"].items()
                                         if key.endswith("reproduced")},
                      "result_sha256": digest_file(output)}, sort_keys=True), flush=True)
    return 0 if result["protocol_checks_passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    raise SystemExit(main(parser.parse_args().out.resolve()))
