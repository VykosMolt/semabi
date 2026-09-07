"""Generated fixture implementation. This is never a learner input."""
from copy import deepcopy
import json
from pathlib import Path


BASE_CONNECTIONS = ((0, 0), (0, 1), (1, 0), (1, 1),
                    (2, 2), (2, 3), (3, 2), (3, 3))


def load_catalog(path):
    catalog = json.loads(Path(path).read_text())
    all_names = []
    for collection, size in (("transmitters", 4), ("receivers", 4), ("patches", 8)):
        names, order = catalog[collection], catalog[collection + "_order"]
        if (len(names) != size or len(set(names)) != size
                or sorted(order) != list(range(size))):
            raise ValueError("Invalid presentation catalog")
        if not all(isinstance(name, str) and name.strip() == name and name for name in names):
            raise ValueError("Invalid visible identity")
        all_names.extend(names)
    if len(set(all_names)) != len(all_names):
        raise ValueError("Visible identity alphabets must be disjoint")
    return catalog


def fresh():
    """One fixed public reset state; there is no case-dependent state installer."""
    return {"connections": [{"transmitter": left, "receiver": right}
                             for left, right in BASE_CONNECTIONS],
            "received": [False] * 4, "selected_receiver": None, "notice": None}


def public(state, catalog):
    selected = state["selected_receiver"]
    notice = state["notice"]
    return {
        "transmitters": [{"name": catalog["transmitters"][i]}
                         for i in catalog["transmitters_order"]],
        "receivers": [{"name": catalog["receivers"][i], "received": state["received"][i]}
                      for i in catalog["receivers_order"]],
        "patches": [{"name": catalog["patches"][i],
                     "transmitter": catalog["transmitters"][state["connections"][i]["transmitter"]],
                     "receiver": catalog["receivers"][state["connections"][i]["receiver"]]}
                    for i in catalog["patches_order"]],
        "selected_receiver": None if selected is None else catalog["receivers"][selected],
        "notice": None if notice is None else {
            "delivered": notice["delivered"],
            "transmitter": catalog["transmitters"][notice["transmitter"]],
            "receiver": catalog["receivers"][notice["receiver"]]},
    }


def act(state, action, catalog):
    """Apply only public control operations, using visible identity arguments."""
    fields = {
        "set_endpoint": {"op", "patch", "endpoint", "value"},
        "select_receiver": {"op", "receiver"},
        "clear_receipt": {"op", "receiver"},
        "clear_message": {"op"},
        "transmit": {"op", "transmitter"},
    }
    if (not isinstance(action, dict) or not isinstance(action.get("op"), str)
            or action["op"] not in fields or set(action) != fields[action["op"]]):
        raise ValueError("Unknown public operation fields")
    op = action["op"]
    if op == "set_endpoint":
        patch = catalog["patches"].index(action["patch"])
        endpoint = action["endpoint"]
        if endpoint not in ("transmitter", "receiver"):
            raise ValueError("Unknown endpoint")
        collection = "transmitters" if endpoint == "transmitter" else "receivers"
        state["connections"][patch][endpoint] = catalog[collection].index(action["value"])
    elif op == "select_receiver":
        state["selected_receiver"] = catalog["receivers"].index(action["receiver"])
    elif op == "clear_receipt":
        state["received"][catalog["receivers"].index(action["receiver"])] = False
    elif op == "clear_message":
        state["notice"] = None
    elif op == "transmit":
        transmitter = catalog["transmitters"].index(action["transmitter"])
        receiver = state["selected_receiver"]
        if receiver is None:
            raise ValueError("Select a receiver first")
        outgoing = {i for i, edge in enumerate(state["connections"])
                    if edge["transmitter"] == transmitter}
        incoming = {i for i, edge in enumerate(state["connections"])
                    if edge["receiver"] == receiver}
        delivered = bool(outgoing.intersection(incoming))
        if delivered:
            state["received"][receiver] = True
        state["notice"] = {"delivered": delivered, "transmitter": transmitter, "receiver": receiver}
    else:
        raise ValueError("Unknown public operation")
    return public(state, catalog)


def clone(state):
    return deepcopy(state)
