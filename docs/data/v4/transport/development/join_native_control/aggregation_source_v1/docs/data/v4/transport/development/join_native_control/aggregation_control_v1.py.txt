"""Prepared native supplied-state diagnosis of incomplete consequence aggregation."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from semabi.compiler.abstract import AbsObj, AbstractState
from semabi.compiler.induce import ActT, EffT, OperatorHyp
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v4 import binding
from semabi.compiler.v4 import consequence as csq


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(freeze):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    files = {name: digest(ROOT / name) for name in freeze["files"]}
    if head != freeze["source_head"] or files != freeze["files"]:
        raise AssertionError("frozen source, head, or instrument changed")
    return {"source_head": head, "files": files}


def page(values):
    return Observation([Node(0, -1, "group", "")]
                       + [Node(i + 1, 0, "text", value) for i, value in enumerate(values)])


def prediction(bound, kind=csq.CREATION, verdict=csq.NOT_APPLICABLE):
    return csq.ScopedPrediction(
        step=0, control="supplied", operator="supplied_creation", kind=kind,
        support=0, slot="value", predicted="?z", bindings=len(bound.admissible),
        binding_status=bound.status, binding_truncated=bound.truncated,
        verdict=verdict, detail="supplied direct verdict" if kind == csq.VALUE else "")


def binding_record(found):
    return {"native": found.to_json(), "typed_assignments": [
        {param: obj.id for param, obj in row.values.items()} for row in found.admissible],
        "pinned": sorted(found.pinned()), "target_status": found.effect_target(["?z"]),
        "target_denotations": found.denotations(["?z"])}


def run_creation(op, eff, bounds):
    before = page([])
    cases = []
    expected = {
        "neither": ([], [csq.REFUTED, csq.REFUTED], csq.REFUTED),
        "alpha_only": (["Alpha"], [csq.SUPPORTED, csq.REFUTED], csq.POSSIBLE),
        "beta_only": (["Beta"], [csq.REFUTED, csq.SUPPORTED], csq.POSSIBLE),
        "both": (["Alpha", "Beta"], [csq.SUPPORTED, csq.SUPPORTED], csq.SUPPORTED),
    }
    checks = []
    for label, (values, complete_parts, complete_verdict) in expected.items():
        after = page(values)
        for budget, bound in bounds.items():
            assignments = csq._distinct_by(
                bound.admissible, lambda assignment: csq._creation_values(eff, assignment))
            base = prediction(bound)
            parts = [csq._under_one_binding(
                base, None, {}, before, after, None, op, eff, assignment,
                None, None, {}, base.predicted) for assignment in assignments]
            # Preserve the parts before aggregation can copy representative metadata.
            part_records = [asdict(part) for part in parts]
            result = csq._aggregate(base, parts, bound)
            target_parts = complete_parts if budget == "default" else complete_parts[:1]
            good = ([part.verdict for part in parts] == target_parts
                    and len(assignments) == (2 if budget == "default" else 1)
                    and (budget != "default" or result.verdict == complete_verdict))
            checks.append(good)
            cases.append({
                "post_case": label, "budget": budget, "before": before.to_json(),
                "after": after.to_json(), "binding": binding_record(bound),
                "all_creation_keys": [csq._creation_values(eff, b) for b in bound.admissible],
                "representatives": [
                    {param: obj.id for param, obj in b.values.items()} for b in assignments],
                "parts": part_records, "aggregate": asdict(result),
                "protocol_case_passed": good,
            })
    return cases, all(checks)


def direct_matrix(bounds):
    supplied = [[], [csq.SUPPORTED], [csq.REFUTED], [csq.POSSIBLE], [csq.UNKNOWN],
                [csq.NOT_APPLICABLE], [csq.SUPPORTED, csq.SUPPORTED],
                [csq.REFUTED, csq.REFUTED], [csq.SUPPORTED, csq.REFUTED],
                [csq.REFUTED, csq.UNKNOWN], [csq.SUPPORTED, csq.UNKNOWN],
                [csq.NOT_APPLICABLE, csq.NOT_APPLICABLE]]
    records = []
    for budget in ("default", "limit_two"):
        bound = bounds[budget]
        for verdicts in supplied:
            parts = [prediction(bound, csq.VALUE, verdict) for verdict in verdicts]
            before = [asdict(part) for part in parts]
            result = csq._aggregate(prediction(bound, csq.VALUE), parts, bound)
            records.append({"budget": budget, "supplied_parts": before,
                            "aggregate": asdict(result), "identity_case": False})
        for verdict in (csq.SUPPORTED, csq.REFUTED, csq.UNKNOWN):
            part = prediction(bound, csq.VALUE, verdict)
            part.identity = prediction(bound, csq.IDENTITY, verdict)
            before = asdict(part)
            result = csq._aggregate(prediction(bound, csq.VALUE), [part], bound)
            records.append({"budget": budget, "supplied_parts": [before],
                            "aggregate": asdict(result), "identity_case": True})
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("diagnostic output must be a new path")
    freeze = json.loads((HERE / "aggregation_freeze_v1.json").read_text())
    before = verify(freeze)
    objects = [AbsObj(1, key, {}) for key in ("Alpha", "Beta")]
    objects += [AbsObj(2, key, {}) for key in ("w0", "w1")]
    state = AbstractState({obj.id: obj for obj in objects}, {})
    eff = EffT("add", 3, "?new0", attrs=(("value", "?z"),))
    op = OperatorHyp("supplied_creation", (ActT("click", None, None),), (eff,),
                     {"?z": 1, "?w": 2, "?new0": 3})
    bounds = {
        "default": binding.solve(op, [], state, {}),
        "limit_two": binding.solve(op, [], state, {}, limit=2),
        "nodes_four": binding.solve(op, [], state, {}, nodes=4),
    }
    expected = [(z, w) for z in ("Alpha", "Beta") for w in ("w0", "w1")]
    assignments = lambda b: [(x.get("?z").key, x.get("?w").key) for x in b.admissible]
    space_ok = (assignments(bounds["default"]) == expected
                and bounds["default"].status == binding.AMBIGUOUS
                and not bounds["default"].truncated
                and bounds["default"].effect_target(["?z"]) == (binding.UNDERDETERMINED, 2))
    for name in ("limit_two", "nodes_four"):
        space_ok &= (assignments(bounds[name]) == expected[:2]
                     and bounds[name].status == binding.AMBIGUOUS and bounds[name].truncated
                     and bounds[name].effect_target(["?z"])
                     == (binding.UNDETERMINED_INCOMPLETE, 1))
    creation, creation_ok = run_creation(op, eff, bounds)
    lookup = {(c["post_case"], c["budget"]): c for c in creation}
    flags = {}
    for name in ("limit_two", "nodes_four"):
        flags[name] = {
            "false_refutation_reproduced": (
                lookup["beta_only", name]["aggregate"]["verdict"] == csq.REFUTED
                and lookup["beta_only", "default"]["aggregate"]["verdict"] == csq.POSSIBLE),
            "false_exhaustive_support_reproduced": (
                lookup["alpha_only", name]["aggregate"]["verdict"] == csq.SUPPORTED
                and lookup["alpha_only", "default"]["aggregate"]["verdict"] == csq.POSSIBLE),
        }
    result = {
        "schema": "incomplete-aggregation-native-diagnostic-v1",
        "scope": "supplied state, operator, and raw pages; native binding/dedup/creation/aggregation",
        "learner_fits": 0, "browser_actions": 0, "observational_learning_claim": False,
        "state": {"objects": [asdict(obj) for obj in objects]},
        "operator": {"name": op.name, "params": op.params, "effects": [asdict(eff)], "pre": []},
        "known_complete_assignments": expected,
        "solver_results": {name: binding_record(bound) for name, bound in bounds.items()},
        "creation_cases": creation, "direct_supplied_verdict_matrix": direct_matrix(bounds),
        "defect_flags": flags, "protocol_checks_passed": bool(space_ok and creation_ok),
        "before": before, "after": verify(freeze),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"protocol_checks_passed": result["protocol_checks_passed"],
                      "creation_cases": len(creation), "direct_cases": len(result["direct_supplied_verdict_matrix"]),
                      "defect_flags": flags, "result_sha256": digest(args.out)}, sort_keys=True))
    return 0 if result["protocol_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
