"""Independent declarative reference, used only by audits and final evaluator."""

from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

SPEC = json.loads(Path(__file__).with_name("specification.json").read_text())


def outcome(state, operation):
    if operation == "review":
        accepted = state["_clearance"] is True
        family = "ambiguity"
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
