"""Retained-corpus regression diagnostic, never a fresh-transfer evaluation.

Uses the settled-reading and fit/scoring path of join_inspect.py and
score_override.py. Adds checks against the raw visible selector and sheet fields,
without passing those checks or oracle files into the learner. A wrong prediction
is retained as a result; it is not an assertion to make green.
"""
from collections import Counter
from dataclasses import asdict, replace
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
PREQ = Path("/home/moloch/semabi-scratch/preq")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs/data/v4/prequential/instruments"))

from link_probe import settled_reading
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4 import outcome as oc

CASES = {
    "allocation_positive": ("harbour_join_dev", "harbour_join_hold", "Allocate berth"),
    "allocation_refusals": ("harbour_ref_dev", "harbour_ref_hold", "Allocate berth"),
    "pilot": ("harbour_pil_dev", "harbour_pil_hold", "Book pilot"),
    "separating": ("harbour_sep_dev", "harbour_sep_hold", "Book pilot"),
    "separating_extended": ("harbour_sep2_dev", "harbour_sep_hold", "Book pilot"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc():
    return datetime.datetime.now(datetime.UTC).isoformat()


def write(path, record):
    path.write_text(json.dumps(record, indent=2, default=str) + "\n")


def visible_check(obs, target, bound, roles):
    """Harbour-specific measurement only: selector identity and sheet length.

    The selector is the raw combobox sibling of the clicked control. The vessel
    and length are two-column rows in the nearest ancestor group. These are
    independent of the learner's abstractor, chosen identity and predicted event.
    Numeric meters are normalized by removing the visible trailing ' m'.
    """
    button = obs.node(target)
    siblings = [obs.node(i) for i in obs.children(button.parent)]
    selectors = [n for n in siblings if n.role == "combobox"]
    selected_roles = [name for name, role in roles.items() if role.kind == "selection"]
    selected_keys = [str(bound[name].key) for name in selected_roles if name in bound]
    checks = []
    if len(selectors) == 1:
        raw = selectors[0].value or ""
        chosen = raw.split(" - ", 1)[0]
        empty = chosen in {"no pilot chosen", "no berth chosen"}
        matched = not selected_keys if empty else chosen in selected_keys
        checks.append({"question": "selected object retained", "raw_node": selectors[0].i,
                       "visible": raw, "expected_key": None if empty else chosen,
                       "bound_selection_keys": selected_keys,
                       "selection_role_count": len(selected_roles),
                       "status": "match" if matched and selected_roles else "mismatch"})
    else:
        checks.append({"question": "selected object retained", "status": "unmeasured",
                       "reason": f"{len(selectors)} raw sibling comboboxes"})
    sheet = {}
    for ancestor in obs.ancestors(target):
        if obs.node(ancestor).role != "group":
            continue
        for idx in obs.subtree(ancestor):
            if obs.node(idx).role != "row":
                continue
            cells = [obs.node(i) for i in obs.children(idx) if obs.node(i).role == "cell"]
            if len(cells) == 2 and cells[0].name in {"Vessel", "Length overall"}:
                sheet[cells[0].name] = {"value": cells[1].name, "node": cells[1].i}
        if sheet:
            break
    owner = bound.get("owner")
    if "Vessel" in sheet:
        raw = sheet["Vessel"]
        expected = raw["value"]
        actual = None if owner is None else str(owner.key)
        checks.append({"question": "sheet vessel is action owner", "raw_node": raw["node"],
                       "visible": expected, "bound_owner_key": actual,
                       "status": "match" if actual == expected else "mismatch"})
    else:
        checks.append({"question": "sheet vessel is action owner", "status": "unmeasured",
                       "reason": "visible sheet vessel row absent"})
    if "Length overall" in sheet:
        raw = sheet["Length overall"]
        expected = raw["value"].removesuffix(" m")
        actual = None if owner is None else owner.attrs.get("attr:Length overall#0")
        checks.append({"question": "owner length survives representation", "raw_node": raw["node"],
                       "visible": raw["value"], "expected_scalar": expected,
                       "bound_scalar": actual, "status": "match" if actual == expected else "mismatch"})
    else:
        checks.append({"question": "owner length survives representation", "status": "unmeasured",
                       "reason": "visible sheet length row absent"})
    return checks


def score(model, log, control, *, predictions):
    fit = replace(model, log=log, cut=0)
    rows = []
    for step in log.steps:
        if step.action.kind != "click" or step.action.target is None:
            continue
        pre = log.obs(step.before)
        # Raw button name selects the denominator independently of recognition.
        if pre.node(step.action.target).name != control.split(":", 1)[1]:
            continue
        recognized = csq.clicked_control(fit.abstractor, pre, step)
        row = {"step": step.step, "episode": step.episode, "ok": step.ok,
               "error": step.error, "before": step.before, "after": step.after,
               "raw_target": step.action.target, "recognized_control": recognized}
        m = fit.outcomes.get(control)
        if m is None:
            row["recognition_failure"] = "no outcome model"
        else:
            state = fit.abstractor.abstract(pre)
            owner = oc._owner(fit.abstractor, pre, step)
            bound, statuses = m.bind(state, owner)
            row["roles"] = statuses
            row["bound"] = {r: {"key": obj.key, "tid": obj.tid, "attrs": obj.attrs}
                            for r, obj in bound.items()}
            row["visible_checks"] = visible_check(pre, step.action.target, bound, m.roles)
            if predictions:
                query = oc.query_literals(fit, m, state, bound, statuses)
                row["version_space"] = oc.score_step_admissible(fit, step, corroborated=True,
                                                               hypothesis=oc.RULE)
                row["decision_list"] = oc.score_step(fit, step)
                row["vouches"] = {event: asdict(vouch) for event, vouch in
                                  m.admissible(query, corroborated=True, hypothesis=oc.RULE).items()}
        rows.append(row)
    return {"target_clicks": len(rows), "failed_attempts": sum(not r["ok"] for r in rows),
            "recognition_mismatches": sum(r["recognized_control"] != control for r in rows),
            "visible_check_ledger": dict(Counter(c["status"] for r in rows
                                                 for c in r.get("visible_checks", []))),
            "visible_check_scope": {q: dict(Counter(c["status"] for r in rows
                                       for c in r.get("visible_checks", []) if c["question"] == q))
                                    for q in sorted({c["question"] for r in rows
                                                     for c in r.get("visible_checks", [])})},
            "version_space_ledger": dict(Counter(r["version_space"]["verdict"]
                                                  for r in rows if "version_space" in r)),
            "decision_list_ledger": dict(Counter(r["decision_list"]["verdict"]
                                                  for r in rows if "decision_list" in r)),
            "rows": rows}


def main(name):
    dev_name, hold_name, label = CASES[name]
    dev, hold, control = PREQ / dev_name, PREQ / hold_name, "button:" + label
    provenance = {"case": name, "owner": "/root/baseline_verification", "pid": os.getpid(),
                  "started_utc": utc(), "state": "running", "dev": str(dev), "hold": str(hold),
                  "control": control, "command": [sys.executable, str(Path(__file__).resolve()), name],
                  "working_directory": str(ROOT), "instrument_sha256": digest(Path(__file__)),
                  "source_snapshot_sha256": digest(OUT / "source_snapshot.json"),
                  "scope": "disclosed retained development regression; no fresh-generalization claim",
                  "fit_boundary": "existing instrument: search on all dev; outcome split 0.999; hold scoring only",
                  "input_files": {str(p): digest(p) for d in (dev, hold)
                                  for p in sorted(d.iterdir()) if p.is_file()}}
    write(OUT / (name + "_process.json"), provenance)
    start = time.monotonic()
    print(f"{utc()} {name}: settled reading", flush=True)
    reading = settled_reading(dev)
    print(f"{utc()} {name}: fitting", flush=True)
    model = csq.fit(dev, reading, split=0.999)
    m = model.outcomes.get(control)
    record = {"provenance": provenance, "reading": reading.to_json(),
              "fit": None if m is None else {"roles": {r: asdict(role) for r, role in m.roles.items()},
                   "rules": [str(rule) for rule in m.rules], "ordered": m.ordered,
                   "pairs": m.pairs, "events": m.events, "default": m.default,
                   "arg_roles": m.arg_roles, "fitted": m.fitted},
              "dev_steps": len(model.log.steps), "outcome_cut": model.cut}
    print(f"{utc()} {name}: scoring and visible binding checks", flush=True)
    record["development"] = score(model, model.log, control, predictions=False)
    record["holdout"] = score(model, EvidenceLog(hold), control, predictions=True)
    write(OUT / (name + ".json"), record)
    provenance.update(state="completed", ended_utc=utc(), elapsed_seconds=time.monotonic() - start,
                      result_sha256=digest(OUT / (name + ".json")),
                      changed_inputs=[p for p, before in provenance["input_files"].items()
                                      if digest(Path(p)) != before])
    write(OUT / (name + "_process.json"), provenance)
    print(json.dumps({part: {k: v for k, v in record[part].items() if k != "rows"}
                      for part in ("development", "holdout")}, indent=2), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
