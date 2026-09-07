"""Score saved J1 pre-action forecasts against raw pages, without a fitted model.

The caller authenticates the complete run/receipt custody first. Native emission
helpers and Observation are injected after that source gate; this module imports
no learner, fixture, browser or evaluator configuration at load time.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("_j1_score_io", HERE / "live_io.py")
io = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = io
spec.loader.exec_module(io)

CHANNELS = ("decision_list", "rule", "list")
STATUSES = {"UNREACHABLE", "NO_PRESTATE", "NON_CLICK", "NO_MODEL", "FORECAST", "ERROR"}
VALUE_FIELDS = {"control", "state", "parsed", "owner", "bound", "binding_status", "literals",
                "roles", "arg_roles", "decision_list", "rule", "list", "arguments"}
VOUCH_FIELDS = {"event", "witnesses", "condition", "covers", "sole", "preceded_by"}


def _canonical(value):
    return io.json_bytes(value)[:-1]


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def decode(value, snapshots=None, active=()):
    """Decode only typed stored data; no native objects or callbacks are created."""
    snapshots = {} if snapshots is None else snapshots
    if value is None or type(value) in (str, bool, int, float):
        return value
    if type(value) is list:
        return [decode(item, snapshots, active) for item in value]
    io.require(type(value) is dict, "Unsupported copied value")
    keys = set(value)
    if keys == {"$snapshot"}:
        key = value["$snapshot"]
        io.require(type(key) is str and key not in active and key in snapshots,
                   "Missing or cyclic stored snapshot")
        io.require(hashlib.sha256(_canonical(snapshots[key])).hexdigest() == key,
                   "Stored snapshot hash differs")
        return decode(snapshots[key], snapshots, active + (key,))
    if keys == {"$integer_decimal"}:
        text = value["$integer_decimal"]
        io.require(type(text) is str, "Copied large integer is not decimal text")
        number = int(text)
        io.require(str(number) == text and abs(number) >= 2 ** 53, "Noncanonical copied large integer")
        return number
    if keys == {"$tuple"}:
        io.require(type(value["$tuple"]) is list, "Copied tuple items differ")
        return tuple(decode(item, snapshots, active) for item in value["$tuple"])
    if keys == {"$set", "items"}:
        io.require(value["$set"] in {"set", "frozenset"} and type(value["items"]) is list,
                   "Copied set schema differs")
        encoded = [_canonical(item) for item in value["items"]]
        io.require(encoded == sorted(set(encoded)), "Copied set ordering or membership differs")
        items = [decode(item, snapshots, active) for item in value["items"]]
        result = set(items)
        io.require(len(result) == len(items), "Copied set has aliased members")
        return result if value["$set"] == "set" else frozenset(result)
    if keys == {"$mapping", "items"}:
        return {key: decode(item, snapshots, active) for key, item in mapping(value, snapshots, active).items()}
    if keys == {"$record", "fields"}:
        io.require(type(value["$record"]) is str and type(value["fields"]) is dict,
                   "Copied record schema differs")
        return {"$record": value["$record"],
                "fields": {key: decode(item, snapshots, active) for key, item in value["fields"].items()}}
    raise io.ProtocolError("Unsupported or incomplete copied data")


def mapping(value, snapshots=None, active=()):
    """Decode mapping keys, retaining values for selective typed inspection."""
    io.require(type(value) is dict and set(value) == {"$mapping", "items"}
               and value["$mapping"] in {"dict", "Counter", "defaultdict"}
               and type(value["items"]) is list, "Copied mapping schema differs")
    out, encoded = {}, set()
    for pair in value["items"]:
        io.require(type(pair) is list and len(pair) == 2, "Copied mapping entry differs")
        key = decode(pair[0], snapshots, active)
        token = _canonical(pair[0])
        io.require(token not in encoded and key not in out, "Duplicate or aliased copied mapping key")
        encoded.add(token)
        out[key] = pair[1]
    return out


def vocabulary(checkpoint, emission):
    io.require(checkpoint.get("schema") == "semabi.j1.live_checkpoint.v1"
               and checkpoint.get("checkpoint_index") == 0
               and type(checkpoint["checkpoint_index"]) is int
               and checkpoint.get("instrument_status") == "COMPLETE",
               "Expected a complete startup model checkpoint")
    projection = checkpoint["projection"]
    common = projection["common"]
    raw = common["emission_vocabulary"]
    io.require(set(raw) == {"values", "frozen"} and raw["frozen"] is True,
               "Saved emission vocabulary was not frozen")
    values = decode(raw["values"], projection["snapshots"])
    io.require(type(values) is set and all(type(item) is tuple and item
               and all(type(token) is str for token in item) for item in values),
               "Saved emission vocabulary values differ")
    result = emission.Vocabulary()
    result.values = set(values)
    result.freeze()
    return result


def control_events(checkpoint):
    """Retain per-control observed labels, without assuming the set is complete."""
    projection = checkpoint["projection"]
    outcomes = mapping(projection["common"]["fit"]["outcomes"], projection["snapshots"])
    result = {}
    for name, raw in outcomes.items():
        io.require(type(name) is str and type(raw) is dict
                   and raw.get("$record") == "semabi.compiler.v4.outcome.ControlOutcome",
                   "Saved control record differs")
        events = decode(raw["fields"]["events"], projection["snapshots"])
        io.require(type(events) is dict and all(type(event) is str and _integer(count)
                   for event, count in events.items()), "Saved control event counts differ")
        result[name] = events
    return result


def _vouches(raw, snapshots):
    result = {}
    for event, value in mapping(raw, snapshots).items():
        record = decode(value, snapshots)
        io.require(type(event) is str and type(record) is dict
                   and set(record) == {"$record", "fields"}
                   and record["$record"] == "semabi.compiler.v4.outcome.Vouch"
                   and set(record["fields"]) == VOUCH_FIELDS, "Saved Vouch schema differs")
        fields = record["fields"]
        io.require(fields["event"] == event and type(fields["sole"]) is bool
                   and _integer(fields["covers"]) and type(fields["witnesses"]) is tuple
                   and all(_integer(witness) for witness in fields["witnesses"])
                   and type(fields["condition"]) is tuple and type(fields["preceded_by"]) is tuple
                   and all(type(prior) is str for prior in fields["preceded_by"]),
                   "Saved Vouch content differs")
        result[event] = fields
    return result


def payload(response):
    io.require(type(response) is dict and response.get("schema") == "semabi.j1.forecast.v1"
               and type(response.get("status")) is str and response["status"] in STATUSES
               and response.get("instrument_status") in {"COMPLETE", "INCOMPLETE"},
               "Saved forecast envelope differs")
    if response["instrument_status"] != "COMPLETE" or response["status"] != "FORECAST":
        return None
    io.require(response.get("incomplete_reasons") == [] and type(response.get("snapshots")) is dict,
               "Complete forecast contains a copying failure")
    snapshots = response["snapshots"]
    raw = mapping(response["values"], snapshots)
    io.require(set(raw) == VALUE_FIELDS, "Complete forecast value inventory differs")
    result = {key: decode(raw[key], snapshots) for key in
              ("control", "decision_list", "arg_roles", "arguments")}
    io.require(type(result["control"]) is str and type(result["decision_list"]) is str,
               "Saved control or decision-list event differs")
    for name in ("arg_roles", "arguments"):
        records = result[name]
        io.require(type(records) is dict and all(type(event) is str and type(positions) is dict
                   and all(_integer(index) and type(value) is str for index, value in positions.items())
                   for event, positions in records.items()), "Saved argument map differs")
    result.update(rule=_vouches(raw["rule"], snapshots), list=_vouches(raw["list"], snapshots))
    expected = dict.fromkeys([result["decision_list"], *result["rule"], *result["list"]])
    io.require(list(result["arguments"]) == list(expected), "Saved argument/event opportunities differ")
    return result


def measure(before, after, saved_vocabulary, native):
    """Use only native emission reading, with no learner/query/evidence mutation."""
    emission = native.emission
    pre = None if before is None else native.Observation.from_json(before)
    post = None if after is None else native.Observation.from_json(after)
    before_text = None if pre is None else emission.live_text(pre)
    channel = post is not None and bool(emission.live_nodes(post))
    after_text = None if post is None else emission.live_text(post)
    observed = None if after_text is None else emission.lift_event(
        after_text, post, pre, vocabulary=saved_vocabulary)
    return {"channel": channel, "before_live_text": before_text, "after_live_text": after_text,
            "unchanged_live_text": pre is not None and after_text == before_text,
            "frame": None if observed is None else observed.frame,
            "arguments": None if observed is None else list(observed.args)}


def _matches(event, observed, outcome):
    if event == outcome.SILENT:
        return observed["unchanged_live_text"]
    return event == observed["frame"]


def _unestablished(detail):
    return {"category": "unestablished", "detail": detail}


def _argument_checks(event, values, observed, native):
    predicted = values["arguments"][event]
    roles = values["arg_roles"].get(event, {})
    arity = event.split(" ").count(native.emission.PLACEHOLDER)
    positions = sorted(set(range(arity)) | set(predicted) | set(roles))
    rows = []
    for position in positions:
        row = {"position": position, "role": roles.get(position),
               "predicted_present": position in predicted, "predicted": predicted.get(position),
               "observed": (observed["arguments"][position]
                            if observed["arguments"] is not None and position < len(observed["arguments"]) else None)}
        if not observed["channel"]:
            row.update(status="unavailable", reason="NO_CHANNEL")
        elif not _matches(event, observed, native.outcome):
            row.update(status="unavailable", reason="FRAME_NOT_CORROBORATED")
        elif position not in predicted:
            row.update(status="unavailable", reason="NO_BOUND_LITERAL")
        elif predicted[position] == native.outcome.FRESH:
            row.update(status="unavailable", reason="FRESH_REQUIRES_SEPARATE_CREATION_CONTROL")
        elif row["observed"] is None:
            row.update(status="unavailable", reason="NO_OBSERVED_ARGUMENT_POSITION")
        else:
            row.update(status="matched" if predicted[position] == row["observed"] else "mismatched",
                       reason="EXACT_LITERAL")
        rows.append(row)
    return {"denominator_positions": len(positions), "rows": rows,
            "counts": dict(Counter(row["status"] for row in rows)),
            "scope": "Literal output arguments, separate from frame correctness and raw primitive arguments"}


def assess(response, before, after, saved_vocabulary, known_events, native):
    """One saved forecast opportunity; the custody caller supplies its raw pages."""
    observed = measure(before, after, saved_vocabulary, native)
    values = None if response is None else payload(response)
    status = "MISSING_FORECAST" if response is None else response["status"]
    result = {"forecast_status": status, "observed": observed,
              "channels": {}, "literal_arguments": {}, "novel_observed_frame": None}
    if values is None:
        reason = ("INCOMPLETE_INSTRUMENT" if response is not None
                  and response["instrument_status"] != "COMPLETE" else status)
        result["channels"] = {name: _unestablished(reason) for name in CHANNELS}
        return result
    result["control"] = values["control"]
    labels = known_events.get(values["control"])
    result["novel_observed_frame"] = (observed["frame"] not in labels
                                      if observed["frame"] is not None and labels is not None else None)
    result["previously_observed_control_events"] = None if labels is None else list(labels)
    if not observed["channel"]:
        result["channels"] = {name: _unestablished("NO_CHANNEL") for name in CHANNELS}
    else:
        event = values["decision_list"]
        if event in (native.outcome.UNDETERMINED, native.outcome.UNNAMED):
            chosen = _unestablished("UNDETERMINED" if event == native.outcome.UNDETERMINED else "UNNAMED")
        else:
            chosen = {"category": "correct" if _matches(event, observed, native.outcome) else "wrong"}
        result["channels"]["decision_list"] = {**chosen, "predicted": event}
        for name in ("rule", "list"):
            options = values[name]
            matching = [event for event in options if _matches(event, observed, native.outcome)]
            if not options:
                decision = _unestablished("NO_ADMISSIBLE_EVENT")
            elif len(options) > 1:
                decision = {"category": "ambiguous", "observed_among": bool(matching)}
            else:
                event, vouch = next(iter(options.items()))
                if vouch["sole"]:
                    decision = {**_unestablished("SOLE_OBSERVED_VOCABULARY"),
                                "sole_correct": bool(matching), "sole_wrong": not bool(matching)}
                else:
                    decision = {"category": "forced_correct" if matching else "forced_wrong"}
            result["channels"][name] = {**decision, "admissible": list(options), "matching": matching}
    result["literal_arguments"] = {event: _argument_checks(event, values, observed, native)
                                    for event in values["arguments"]
                                    if event not in (native.outcome.UNDETERMINED, native.outcome.UNNAMED)}
    return result


def summary(rows):
    result = {"denominator_opportunities": len(rows), "channels": {}}
    for name in CHANNELS:
        entries = [row["channels"][name] for row in rows]
        categories = (("correct", "wrong", "ambiguous", "unestablished") if name == "decision_list"
                      else ("forced_correct", "forced_wrong", "ambiguous", "unestablished"))
        result["channels"][name] = {
            "categories": {category: sum(entry["category"] == category for entry in entries)
                           for category in categories},
            "unestablished_reasons": dict(Counter(entry.get("detail", "UNSPECIFIED")
                 for entry in entries if entry["category"] == "unestablished")),
            "ambiguous_among": sum(entry.get("observed_among") is True for entry in entries),
            "ambiguous_missing": sum(entry.get("observed_among") is False for entry in entries),
            "sole_correct": sum(entry.get("sole_correct") is True for entry in entries),
            "sole_wrong": sum(entry.get("sole_wrong") is True for entry in entries),
        }
        io.require(sum(result["channels"][name]["categories"].values()) == len(rows),
                   "Outcome category denominator differs")
    return result
