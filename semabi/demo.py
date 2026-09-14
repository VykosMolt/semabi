"""Learn an unfamiliar application's hidden rule by clicking on it, then check it.

Default mode replays a retained interaction trace and needs no browser. `--live`
starts the bundled fixture application and drives a real browser instead.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import fields as field_theory
from semabi.compiler.v4 import outcome as oc
from semabi.compiler.v4 import referring

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "docs/data/v4/transport/p43/falls2_1702"
HELD_OUT = ROOT / "docs/data/v4/transport/first_pass/dispatch/evaluation_v2"
CONTRACT = ROOT / "experiments/transport_v1/public_contract.json"
SERVER = ROOT / "experiments/transport_v1/server.py"
CONTROL = "button:Check dispatch"

# The evaluator knows this. The learner is never told any of it.
APPLICATION = [
    "A dispatch board lists three runs. Opening a run shows its packed weight in an",
    "editable field and lets you attach one of three vans, each with a payload limit.",
    "A 'Check dispatch' button answers with a status line. The rule behind that answer",
    "is hidden: there is no API, no schema, no documentation and no source to read.",
]

SHORT = {
    oc.FORCED_RIGHT: ("exact", "ok"),
    oc.FORCED_WRONG: ("WRONG", "bad"),
    oc.SEVERAL_AMONG: ("ambiguous", "warn"),
    oc.SEVERAL_MISSING: ("WRONG", "bad"),
    oc.SOLE_RIGHT: ("seen once", "warn"),
    oc.SOLE_WRONG: ("WRONG", "bad"),
    oc.NOT_ESTABLISHED: ("nothing established", "dim"),
    oc.NO_MODEL: ("no model", "dim"),
}


class Style:
    def __init__(self, enabled: bool):
        self.on = enabled

    def __call__(self, text: str, kind: str = "") -> str:
        codes = {"bold": "1", "dim": "2", "ok": "32", "warn": "33", "bad": "31", "key": "36"}
        return f"\033[{codes[kind]}m{text}\033[0m" if self.on and kind in codes else text


def rule(style: Style, title: str = "") -> None:
    line = "─" * 74
    print(f"\n{style(title, 'bold')}\n{style(line, 'dim')}" if title else style(line, "dim"))


def wrap(text: list[str], indent: str = "  ") -> None:
    for line in text:
        print(indent + line if line else "")


# ---------------------------------------------------------------- reading the model

def observed(model, log) -> tuple[dict, dict, dict]:
    """The keys, the fields ever filled, and the on-screen labels of each type."""
    keys: dict[int, list] = {}
    filled: dict[int, list] = {}
    labels: dict[tuple[int, str], str] = {}
    A = model.abstractor
    for signature in dict.fromkeys(step.before for step in log.steps):
        page = log.obs(signature)
        state = A.abstract(page)
        present = set()
        for obj in state.objs.values():
            present.add(obj.tid)
            row = keys.setdefault(obj.tid, [])
            if obj.key not in row:
                row.append(obj.key)
            seen = filled.setdefault(obj.tid, [])
            for slot, value in obj.attrs.items():
                if value is not None and slot not in seen:
                    seen.append(slot)
        for instance in A.H.parse_units(signature):
            for slot, node in instance.slot_nodes.items():
                rendered = page.node(node)
                name = rendered.name or rendered.placeholder
                if not name or name == rendered.value:
                    continue
                for tid in present:
                    labels.setdefault((tid, slot), name)
    return keys, filled, labels


def field_name(labels: dict, tid: int, slot: str) -> str:
    plain = slot[len("attr:"):] if slot.startswith("attr:") else slot
    plain = plain.split("#")[0].strip(": ")
    return labels.get((tid, slot[len("attr:"):] if slot.startswith("attr:") else slot), plain or slot)


def role_phrase(role) -> str:
    if role.name == oc.OWNER:
        return "the object the button sits in"
    if role.kind == referring.RELATION:
        direction = role.form[0]
        if direction == "backward":
            return "the object shown inside it"
        if direction == "parent":
            return "the object that contains it"
        return "the object it refers to"
    if role.kind == referring.SELECTION:
        return "the object chosen in the list"
    if role.kind == referring.SINGLETON:
        return "the only object of its type"
    return role.name


def rule_fields(got) -> set:
    """The (type, slot) fields the learned rules actually compare."""
    out = set()
    for row in getattr(got, "rules", ()):
        for literal in row.condition:
            for role, slot in field_theory.ordered_fields(literal):
                role = got.roles.get(role)
                if role is not None:
                    out.add((role.tid, slot))
    return out


def literal_text(literal, got, labels) -> str:
    head = literal[0]
    if head in (field_theory.CMP_GE, field_theory.CMP_LT):
        _, left, left_slot, right, right_slot = literal
        left_role, right_role = got.roles[left], got.roles[right]
        sign = ">=" if head == field_theory.CMP_GE else "<"
        return (f"{field_name(labels, left_role.tid, left_slot)} of {role_phrase(left_role)}"
                f"  {sign}  {field_name(labels, right_role.tid, right_slot)} of {role_phrase(right_role)}")
    if head in (field_theory.GE, field_theory.LT):
        _, role_name, slot, value = literal
        role = got.roles[role_name]
        sign = ">=" if head == field_theory.GE else "<"
        return f"{field_name(labels, role.tid, slot)} of {role_phrase(role)}  {sign}  {value}"
    if head == "attr":
        _, role_name, slot, value = literal
        role = got.roles[role_name]
        return f"{field_name(labels, role.tid, slot)} of {role_phrase(role)}  is  {value!r}"
    if head in ("named", "unnamed", "ambiguous"):
        return f"{role_phrase(got.roles[literal[1]])} is {head}"
    return repr(literal)


# ---------------------------------------------------------------- the report

def report(log, evaluation, style: Style, *, source: str) -> int:
    rule(style, "The application")
    wrap(APPLICATION)
    print()
    wrap([style("The learner is given none of that. It sees rendered accessibility trees", "dim"),
          style("and may click, type, select, reload and reset. Nothing else.", "dim")])

    rule(style, "What it did")
    kinds: dict[str, int] = {}
    for step in log.steps:
        kinds[step.action.kind] = kinds.get(step.action.kind, 0) + 1
    counted = ", ".join(f"{n} {kind}" for kind, n in sorted(kinds.items(), key=lambda row: -row[1]))
    wrap([f"{len(log.steps)} interactions with the live page ({counted})", source])

    print(f"\n  fitting a model on that evidence", end="", flush=True)
    started = time.monotonic()
    model = csq.fit(log.dir, None, at=len(log.steps), regime=csq.FROZEN_PREFIX)
    print(f" — {time.monotonic() - started:.1f}s")
    keys, filled, labels = observed(model, log)
    got = model.outcomes.get(CONTROL)

    rule(style, "What it inferred")
    wrap([style("No schema, field list or object type was supplied. These are its own.", "dim"), ""])
    for tid in sorted(keys):
        names = " · ".join(str(key) for key in keys[tid] if key)
        print(f"  {style(f'type {tid}', 'bold')}   identified by name: {style(names, 'key')}")
        slots = filled.get(tid, [])
        used = [slot for slot in slots if (tid, slot) in rule_fields(got)]
        names = list(dict.fromkeys(field_name(labels, tid, slot) for slot in used + slots))
        if names:
            shown = ", ".join(names[:3])
            rest = f", and {len(names) - 3} more" if len(names) > 3 else ""
            print(f"            fields it reads: {shown}{rest}")
        for slot, target in model.abstractor.types[tid].refs.items():
            relation = "appears inside" if slot.startswith("in:") else "refers to"
            print(f"            {relation} type {target}")
    if got is None:
        print(style("\n  No outcome model was learned for this control.", "bad"))
        return 1

    rule(style, "What it learned about the button")
    events = " and ".join(sorted(got.events))
    wrap([f"Clicking {style('Check dispatch', 'key')} answered {events}", ""])
    for row in got.rules:
        if row.condition:
            for i, literal in enumerate(row.condition):
                print(f"    {'if  ' if i == 0 else 'and '}{literal_text(literal, got, labels)}")
            print(f"    {style('then', 'bold')} the interface answers {style(repr(row.event), 'key')}"
                  f"   {style(f'({row.covered} occasions)', 'dim')}")
        else:
            print(f"    {style('otherwise', 'bold')} it answers {style(repr(row.event), 'key')}"
                  f"   {style(f'({row.covered} occasions)', 'dim')}")
    print()
    wrap([style("The comparison is between two different objects: a field of the van", "dim"),
          style("against a field of the run it is attached to. Neither was named for it.", "dim")])

    return held_out(model, evaluation, style)


def held_out(model, evaluation, style: Style) -> int:
    rule(style, "Tested on a session it never saw")
    scored = replace(model, log=evaluation, cut=0)
    rows, other = [], {}
    for step in evaluation.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        verdict = oc.score_step_admissible(scored, step, corroborated=True, hypothesis=oc.RULE)
        if verdict.get("control") != CONTROL:
            other[verdict["verdict"]] = other.get(verdict["verdict"], 0) + 1
            continue
        rows.append(verdict)

    print(f"  {'click':>6}  {'what the evidence allowed':38}  {'what happened':22}")
    print(style("  " + "─" * 72, "dim"))
    tally: dict[str, int] = {}
    for index, row in enumerate(rows, 1):
        admissible = " or ".join(row.get("admissible") or []) or "nothing established"
        label, kind = SHORT.get(row["verdict"], (row["verdict"][:18], "dim"))
        tally[label] = tally.get(label, 0) + 1
        print(f"  {index:>6}  {admissible:38}  {str(row.get('observed') or '-'):22}  {style(label, kind)}")

    order = ["exact", "ambiguous", "seen once", "nothing established", "WRONG"]
    summary = " · ".join(f"{tally[label]} {label}" for label in order if label in tally)
    print()
    wrap([f"{style(summary, 'bold')} out of {len(rows)} clicks on that button",
          style(f"{sum(other.values())} other clicks were navigation or controls with too little", "dim"),
          style("evidence; the model says so rather than guessing.", "dim")])

    rule(style, "What this shows, and what it does not")
    wrap(["The learner recovered an object model and a cross-object comparison from",
          "clicking alone, and used it on values and pairings it had never seen.",
          "",
          style("It does not show transfer to an application nobody prepared: this fixture", "dim"),
          style("is development evidence. docs/v4_retained.md carries the full record,", "dim"),
          style("including what failed.", "dim")])
    return 1 if any(key == "WRONG" for key in tally) else 0


# ---------------------------------------------------------------- live acquisition

def wait_for(url: str, seconds: float = 15) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1).read()
            return
        except (urllib.error.URLError, OSError):
            time.sleep(0.2)
    raise RuntimeError(f"fixture application did not start at {url}")


def resolve(page, action: dict) -> int | None:
    role, name = action["role"], action["name"]
    matches = [node for node in page.nodes if node.role == role and node.name == name]
    if not matches and role == "spinbutton":     # the snapshot renders number inputs as textboxes
        matches = [node for node in page.nodes if node.role == "textbox" and node.name == name]
    return matches[0].i if len(matches) == 1 else None


def seek_fall(model, page, asked: set):
    """Type the smallest value already seen into a field whose value has only risen.

    A field that only ever rose is a clock, and an order over a clock is an order
    over time, so the learner declines to read it as a size. Setting it lower is
    the observation that settles the question, and only the learner's own theory
    says which field to set.
    """
    from semabi.compiler.browser import Primitive

    theory = next((getattr(got, "field_theory", None) for got in model.outcomes.values()
                   if getattr(got, "field_theory", None)), None)
    if not theory or not theory.get("clocks"):
        return None
    signature = model.abstractor.ensure(page)     # a page the fit never saw is still parsable
    for tid, slot in theory["clocks"]:
        entity = model.abstractor.H.entity_types.get(tid)
        if entity is None:
            continue
        slot_id = slot[len("attr:"):] if slot.startswith("attr:") else slot
        candidates = theory.get("candidates") or {}
        witnessed = (candidates.get(tid) or candidates.get(str(tid)) or {}).get(slot, [])
        seen = [value for value in map(field_theory.numeric, witnessed) if value is not None]
        for instance in model.abstractor.H.parse_units(signature):
            if instance.template not in entity.units:
                continue
            node = instance.slot_nodes.get(slot_id)
            if node is None or node >= len(page.nodes):
                continue
            for candidate in [page.node(node)] + [page.node(child) for child in page.children(node)]:
                current = field_theory.numeric(candidate.value)
                if candidate.role != "textbox" or current is None:
                    continue
                lower = [value for value in seen if value < current]
                if not lower or (tid, slot, candidate.value) in asked:
                    continue
                asked.add((tid, slot, candidate.value))
                value = min(lower)
                text = str(int(value)) if value == int(value) else str(value)
                return Primitive("type", candidate.i, text), candidate.value
    return None


def reload_step(browser, log, episode: int, page):
    """A reload of its own: what survives one is what belongs to the object, not the view."""
    from semabi.compiler.browser import Primitive

    primitive = Primitive("reload")
    result = browser.act(primitive)
    after = browser.observe()
    log.add_step(episode, primitive, result.ok, result.error, page, after)
    return after


def acquire(directory: Path, port: int, seed: int, budget: int, style: Style) -> EvidenceLog:
    from semabi.compiler.browser import Browser, Primitive
    from semabi.compiler.explorer import Explorer, affordance_key

    contract = json.loads(CONTRACT.read_text())["fixtures"]["dispatch"]
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen([sys.executable, str(SERVER), "--port", str(port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log = EvidenceLog(directory)
    try:
        wait_for(base + "/health")
        print(f"  fixture application at {style(base + contract['route'], 'key')}")
        browser = Browser(base + contract["route"], base + contract["reset_url"])
        try:
            page = reload_step(browser, log, 1, browser.reset(seed))
            print("  replaying the supplied demonstration of the workflow", end="", flush=True)
            for action in contract["initial_script"]:
                if action["kind"] == "snapshot":
                    continue
                target = resolve(page, action)
                if target is None:
                    continue
                primitive = Primitive(action["kind"], target, action.get("value"))
                result = browser.act(primitive)
                after = browser.observe()
                log.add_step(1, primitive, result.ok, result.error, page, after)
                page = after
            print(f" — {len(log.steps)} steps")

            print("  fitting what it has seen so far", end="", flush=True)
            model = csq.fit(directory, None, at=len(log.steps))
            print(" — done")

            explorer = Explorer(browser, log, seed=seed)
            browser.reset_url = base + contract["acquisition_reset_url"]
            browser.episode = 2
            page = reload_step(browser, log, 2, browser.reset(seed))
            asked, falls, start = set(), 0, len(log.steps)
            while len(log.steps) - start < budget:
                chosen = seek_fall(model, page, asked) if model is not None else None
                if chosen is not None:
                    primitive, previous = chosen
                    falls += 1
                    print(f"  {style('the move that matters', 'bold')}: it types "
                          f"{style(primitive.text, 'key')} into a field showing {style(previous, 'key')}, "
                          f"a value it has only seen rise")
                else:
                    primitive = explorer.choose(page)
                key = affordance_key(page, primitive)
                result = browser.act(primitive)
                after = browser.observe()
                log.add_step(2, primitive, result.ok, result.error, page, after)
                explorer.counts[key] += 1
                explorer.last_typed_target = primitive.target if primitive.kind == "type" else None
                page = after
                if (len(log.steps) - start) % 15 == 0:
                    model = csq.fit(directory, None, at=len(log.steps))
            print(f"  {len(log.steps) - start} further interactions it chose itself "
                  f"({falls} of them a deliberate fall)")
        finally:
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
    return EvidenceLog(directory)


# ---------------------------------------------------------------- entry point

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true",
                        help="start the bundled application and drive a real browser")
    parser.add_argument("--port", type=int, default=8791, help="port for the live fixture")
    parser.add_argument("--seed", type=int, default=1702)
    parser.add_argument("--budget", type=int, default=60, help="live interactions after the demonstration")
    parser.add_argument("--run", type=Path, help="where a live run records its evidence")
    parser.add_argument("--no-colour", action="store_true")
    args = parser.parse_args(argv)

    style = Style(not args.no_colour and sys.stdout.isatty())
    print(style("\nSemABI — learning what an application does by operating it\n", "bold"))

    if args.live:
        directory = args.run or (ROOT / "runs" / f"demo_live_{int(time.time())}")
        rule(style, "Interacting")
        log = acquire(directory, args.port, args.seed, args.budget, style)
        source = f"recorded live into {directory.relative_to(ROOT) if directory.is_relative_to(ROOT) else directory}"
    else:
        if not TRACE.exists():
            print(style(f"missing retained trace {TRACE}", "bad"))
            return 2
        log = EvidenceLog(TRACE)
        source = ("replayed from a retained trace: a demonstration of the workflow, then\n  "
                  "interactions the learner chose for itself")

    return report(log, EvidenceLog(HELD_OUT), style, source=source)


if __name__ == "__main__":
    raise SystemExit(main())
