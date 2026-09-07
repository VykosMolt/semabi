"""Independent declarative reference, used only by audits and final evaluator."""

from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

SPEC = json.loads(Path(__file__).with_name("specification.json").read_text())


def outcome(state, operation):
    if operation == "review":
        family = "ambiguity"
        fixture = state["fixture"]
        records = state["resources"] if fixture == "reservoir" else state["jobs"]
        selected = state["selected_resource"] if fixture == "reservoir" else state["selected_job"]
        record = next(record for record in records if record["name"] == selected)
        accepted = review_accepts(fixture, record["review_load"], record["review_limit"], state["_review_rule"])
    else:
        family = "relation"
        jobs = {j["name"]: j["quantity"] for j in state["jobs"]}
        capacities = {r["name"]: r["capacity"] for r in state["resources"]}
        try:
            need = Decimal(str(jobs[state["selected_job"]]))
            room = Decimal(str(capacities[state["selected_resource"]]))
            accepted = need.is_finite() and room.is_finite() and not need.is_signed() and not (room - need).is_signed()
        except (KeyError, InvalidOperation):
            accepted = False
    return SPEC[family]["labels"][state["fixture"]][int(accepted)]


def review_accepts(fixture, load, limit, rule):
    need, room = Decimal(str(load)), Decimal(str(limit))
    if rule == "relation":
        return not (room - need).is_signed()
    bounds = SPEC["ambiguity"]["bounds"][fixture]
    return all((need <= Decimal(str(bounds["load_bound"])), room >= Decimal(str(bounds["limit_bound"]))))
