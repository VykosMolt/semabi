"""Application implementation. Not an input to the learner."""

from copy import deepcopy
from math import isfinite


BASES = {
    "dispatch": {
        "jobs": [
            {"name": "Cedar run", "quantity": 7, "note": "North depot"},
            {"name": "Rowan run", "quantity": 11, "note": "River depot"},
            {"name": "Alder run", "quantity": 20, "note": "Hill depot"},
        ],
        "resources": [
            {"name": "Swift van", "capacity": 8},
            {"name": "Panel van", "capacity": 14},
            {"name": "Box van", "capacity": 23},
        ],
    },
    "workshop": {
        "jobs": [
            {"name": "Reed frame", "quantity": 12, "note": "Frames"},
            {"name": "Elm frame", "quantity": 25, "note": "Frames"},
            {"name": "Moss shelf", "quantity": 16, "note": "Shelves"},
        ],
        "resources": [
            {"name": "Compact station", "capacity": 10},
            {"name": "Standard station", "capacity": 18},
            {"name": "Extended station", "capacity": 27},
        ],
    },
    "reservoir": {
        "jobs": [{"name": "Orchard watering", "quantity": 13, "note": "West orchard"}],
        "resources": [
            {"name": "Copper cistern", "capacity": 11},
            {"name": "Slate cistern", "capacity": 20},
            {"name": "Stone cistern", "capacity": 31},
        ],
    },
}


def fresh(fixture, case=None):
    state = deepcopy(BASES[fixture])
    state.update(
        fixture=fixture, view="board" if fixture == "dispatch" else "registry" if fixture == "workshop" else "amount",
        selected_job="Orchard watering" if fixture == "reservoir" else None,
        selected_resource=None, pending_resource=None, expanded=[], result=None,
        review_result=None, review_done=False, _clearance=True,
    )
    if case:
        for job, quantity in case.get("quantities", {}).items():
            next(item for item in state["jobs"] if item["name"] == job)["quantity"] = quantity
        for resource, capacity in case.get("capacities", {}).items():
            next(item for item in state["resources"] if item["name"] == resource)["capacity"] = capacity
        state["_clearance"] = case.get("clearance", True)
    return state


def public(state):
    return {key: deepcopy(value) for key, value in state.items() if not key.startswith("_")}


def item(state, collection, name):
    return next(value for value in state[collection] if value["name"] == name)


def act(state, action):
    """Apply a public operation; authorization uses the current UI state."""
    op = action["op"]
    fixture = state["fixture"]
    if op == "expand" and state["view"] == "registry":
        category = action["name"]
        if category not in {job["note"] for job in state["jobs"]}:
            raise ValueError("Unknown category")
        if category in state["expanded"]:
            state["expanded"].remove(category)
        else:
            state["expanded"].append(category)
    elif op == "open" and state["view"] in {"board", "registry"}:
        job = item(state, "jobs", action["name"])
        if state["view"] == "registry" and job["note"] not in state["expanded"]:
            raise ValueError("Job category is closed")
        state.update(view="detail", selected_job=job["name"], selected_resource=None, result=None)
    elif op == "quantity" and state["view"] in {"detail", "amount"}:
        value = action["value"]
        try:
            numeric = float(value)
            if not isfinite(numeric) or numeric < 0:
                raise ValueError("Invalid quantity")
            value = int(numeric) if numeric.is_integer() else numeric
        except (ValueError, TypeError):
            value = ""
        item(state, "jobs", state["selected_job"])["quantity"] = value
        state["result"] = None
    elif op == "choose" and state["view"] == "detail":
        state.update(view="chooser", pending_resource=state["selected_resource"])
    elif op == "select" and state["view"] in {"chooser", "source"}:
        resource = item(state, "resources", action["name"])
        if fixture == "dispatch":
            state.update(view="detail", selected_resource=resource["name"], result=None)
        else:
            state["pending_resource"] = resource["name"]
    elif op == "attach" and state["view"] == "chooser" and state["pending_resource"]:
        state.update(view="detail", selected_resource=state["pending_resource"], result=None)
    elif op == "back" and state["view"] == "detail":
        state.update(view="board" if fixture == "dispatch" else "registry", result=None)
    elif op == "continue" and state["view"] == "amount":
        state.update(view="source", result=None)
    elif op == "continue" and state["view"] == "source" and state["pending_resource"]:
        state.update(view="review", selected_resource=state["pending_resource"], result=None)
    elif op == "edit" and state["view"] == "review":
        state.update(view="amount", result=None)
    elif op == "attempt" and state["view"] in {"detail", "review"}:
        quantity = item(state, "jobs", state["selected_job"])["quantity"]
        selected = state["selected_resource"]
        accepted = isinstance(quantity, (int, float)) and selected is not None
        if accepted:
            accepted = quantity <= item(state, "resources", selected)["capacity"]
        texts = {
            "dispatch": ("Dispatch unavailable", "Dispatch ready"),
            "workshop": ("Job cannot start", "Job accepted"),
            "reservoir": ("Watering cannot start", "Watering scheduled"),
        }
        state["result"] = texts[fixture][bool(accepted)]
    elif op == "review" and state["view"] in {"detail", "review"} and not state["review_done"]:
        state["review_done"] = True
        texts = {
            "dispatch": ("Seal held", "Seal approved"),
            "workshop": ("Release held", "Release approved"),
            "reservoir": ("Water access held", "Water access approved"),
        }
        state["review_result"] = texts[fixture][state["_clearance"]]
    else:
        raise ValueError("Operation is not available in the current view")
    return public(state)
