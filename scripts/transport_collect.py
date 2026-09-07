"""Frozen black-box collection instrument; no fixture semantics in the learner.

Script collection is an evaluator/initial-evidence operation. Acquisition accepts
only public URLs, the initial EvidenceLog, seed and budget, never scripts/oracles.
The treatment composes the retained contested predicate with retained Explorer.
Every attempted primitive, including failed setup, is charged and retained.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import Explorer
from semabi.compiler.observation import Observation
from semabi.compiler.v4 import consequence as csq, outcome as oc
from semabi.eval.v4_acquire import contested


def stamp():
    return {"utc": datetime.now(timezone.utc).isoformat(), "pid": os.getpid(),
            "cwd": str(Path.cwd()), "argv": sys.argv,
            "git_head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def verify_freeze(path):
    manifest = json.loads(Path(path).read_text())
    explicit = {"semabi/__init__.py", "semabi/relmodel.py",
                "semabi/eval/__init__.py", "semabi/eval/v4_acquire.py",
                "semabi/eval/v4_identity_scoreboard.py", "semabi/eval/v4_consequence_run.py",
                "scripts/transport_collect.py", "scripts/transport_score.py"}
    def permitted(relative):
        file = ROOT / relative
        if {"experiments", "hidden", "env", "oracle"} & set(Path(relative).parts):
            return False
        if not file.resolve().is_relative_to(ROOT):
            return False
        if file.resolve().relative_to(ROOT).as_posix() != relative:
            return False
        return (relative in explicit or
                (relative.startswith("semabi/compiler/") and file.suffix == ".py") or
                (relative.startswith("docs/data/v4/transport/first_pass/") and
                 file.name in {"observations.jsonl", "steps.jsonl", "candidates.json"}))
    refused = [p for p in manifest["files"] if not permitted(p)]
    if refused:
        raise RuntimeError(f"Non-learner paths in runtime freeze section: {refused}")
    # The evaluator separately verifies sealed_evaluator_files. Never open those
    # files in a collection/learning process, even just to recompute their hash.
    changed = [p for p, sha in manifest["files"].items()
               if not (ROOT / p).is_file() or digest(ROOT / p) != sha]
    if changed:
        raise RuntimeError(f"Frozen inputs changed: {changed}")
    return digest(path)


class Recorder:
    def __init__(self, browser, log, decisions_path):
        self.browser, self.log = browser, log
        self.decisions_path = Path(decisions_path)
        self.attempts = 0
        self.failures = 0
        self.observations = 0
        self.kinds = Counter()

    def observe(self):
        obs = self.browser.observe()
        self.observations += 1
        self.log.add_observation(obs)
        return obs

    def act(self, before, primitive, decision, error=None):
        # Missing scripted targets are attempts too; never click a guessed node.
        self.attempts += 1
        self.kinds[primitive.kind] += 1
        if error is None:
            result = self.browser.act(primitive)
            ok, error = result.ok, result.error
            after = self.observe()
        else:
            ok, after = False, before
        self.failures += not ok
        step = self.log.add_step(self.browser.episode, primitive, ok, error, before, after)
        record = {"step": step.step, "charged_attempt": self.attempts,
                  "action": primitive.to_json(), "ok": ok, "error": error,
                  "before": step.before, "after": step.after, **decision}
        with self.decisions_path.open("a") as stream:
            stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        return after

    def summary(self):
        return {"charged_attempts": self.attempts, "failed_attempts": self.failures,
                "primitive_counts": dict(self.kinds), "snapshot_calls": self.observations,
                "bootstrap_goto": 0,
                "settle_timeouts": self.browser.n_settle_timeouts,
                "navigation_waits": self.browser.n_navigation_waits}


def resolve(obs, action):
    kind = action["kind"]
    if kind in ("reset", "reload", "press"):
        return Primitive(kind, text=action.get("text", action.get("value"))), None
    role, name = action["role"], action["name"]
    matches = [n for n in obs.nodes if n.role == role and n.name == name]
    # Browser's public schema maps a native input[type=number] to textbox.
    # This translation belongs to scripted setup, never to the acquisition policy.
    alias = False
    if not matches and role == "spinbutton":
        matches = [n for n in obs.nodes if n.role == "textbox" and n.name == name]
        alias = bool(matches)
    if len(matches) != 1:
        return Primitive(kind, text=action.get("value"),
                         target_desc={"role": role, "name": name}), (
            f"Script target must resolve uniquely; found {len(matches)}")
    primitive = Primitive(kind, matches[0].i, action.get("value", action.get("text")))
    if alias:
        action["observation_role_translation"] = "spinbutton -> textbox"
    return primitive, None


def context(model, obs, node):
    A = model.abstractor
    control = csq.control_of(A.control_family(obs).get(node, ""))
    got = model.outcomes.get(control)
    if got is None:
        return {"node": node, "control": control, "model": False}
    state = A.abstract(obs)
    owner = csq._owner_object(A, A.parsed(obs), state, node)
    bound, status = got.bind(state, owner)
    literals = oc.query_literals(model, got, state, bound, status)
    options = got.admissible(literals, corroborated=True, hypothesis=oc.RULE)
    return {"node": node, "control": control, "model": True,
            "contested": contested(got, literals, options),
            "literals": sorted(literals, key=repr),
            "list_prediction": got.predict(literals),
            "admissible": sorted(options),
            "vouches": {event: asdict(vouch) for event, vouch in options.items()},
            "status": status,
            "owner": None if owner is None else asdict(owner),
            "bound": {role: None if obj is None else asdict(obj)
                      for role, obj in bound.items()}}


def collect_script(args):
    spec = json.loads(Path(args.script).read_text())
    if args.fixture is not None:
        spec = spec["fixtures"][args.fixture]
    if "cases" in spec:
        cases = spec["cases"]
    else:
        script = spec.get("initial_script", spec.get("script"))
        if script is None:
            raise ValueError("Script file must provide cases, initial_script or script")
        cases = [{"case": "initial", "script": script, "reset_url": args.reset_url}]
    browser = Browser(args.url, args.reset_url)
    log = EvidenceLog(args.out)
    rec = Recorder(browser, log, args.out / "decisions.jsonl")
    try:
        # No prior server state may become evidence for the next session. The
        # empty pre-state records that nothing was observed before its first reset.
        obs = Observation([], args.url)
        for case_index, case in enumerate(cases):
            reset_url = case.get("reset_url", args.reset_url)
            if reset_url.startswith("/"):
                from urllib.parse import urlsplit
                url = urlsplit(args.url)
                reset_url = f"{url.scheme}://{url.netloc}{reset_url}"
            browser.reset_url = reset_url
            obs = rec.act(obs, Primitive("reset", text=str(args.seed)),
                          {"reason": "script_setup_reset", "pre_state_unobserved": case_index == 0,
                           "case": case.get("case"), "reset_url": reset_url})
            charged_index = 0
            for index, action in enumerate(case["script"]):
                if action["kind"] == "snapshot":
                    obs = rec.observe()
                    continue
                primitive, error = resolve(obs, action)
                obs = rec.act(obs, primitive, {
                    "reason": "script", "script_index": index, "requested": action,
                    "case": case.get("case"), "task_family": case.get("family"),
                    "task_target": charged_index == case.get("target_action_index")}, error=error)
                charged_index += 1
        return {**rec.summary(), "script_sha256": digest(args.script),
                "script_file": str(args.script), "case_count": len(cases),
                "complete": rec.failures == 0}
    finally:
        browser.close()


def acquire(args):
    # Copy only raw permitted evidence, never sidecars, scripts, or cached models.
    for name in ("observations.jsonl", "steps.jsonl"):
        shutil.copyfile(args.initial / name, args.out / name)
    log = EvidenceLog(args.out)
    initial_steps = len(log.steps)
    model = csq.fit(args.out, None, at=initial_steps)
    browser = Browser(args.url, args.reset_url)
    # Appending a fresh browser session must not merge it with an initial episode;
    # the frozen clock policy deliberately measures rises/falls within episodes.
    browser.episode = max((step.episode for step in log.steps), default=0)
    explorer = Explorer(browser, log, seed=args.seed)
    rec = Recorder(browser, log, args.out / "decisions.jsonl")
    asked = set()
    refits = [{"after_charged_attempts": 0, "training_steps": initial_steps}]
    targeted = 0
    try:
        obs = rec.act(Observation([], args.url), Primitive("reset", text=str(args.seed)),
                      {"reason": "acquisition_setup_reset", "policy": args.policy,
                       "pre_state_unobserved": True})
        while rec.attempts < args.budget:
            if rec.attempts % 15 == 0:
                model = csq.fit(args.out, None, at=len(log.steps))
                refits.append({"after_charged_attempts": rec.attempts,
                               "training_steps": len(log.steps)})
            candidates = []
            chosen = None
            if args.policy == "contested":
                for node in obs.nodes:
                    if node.role != "button":
                        continue
                    item = context(model, obs, node.i)
                    candidates.append(item)
                    key = (item["control"], repr(item.get("literals")))
                    if (chosen is None and item.get("contested") and key not in asked):
                        chosen = (item, key)
            if chosen is not None:
                item, key = chosen
                primitive = Primitive("click", target=item["node"])
                asked.add(key)
                reason = "existing_contested_predicate"
                targeted += 1
            else:
                primitive = explorer.choose(obs)
                reason = "untargeted_explorer"
            # Update Explorer's own novelty history for every policy's action.
            from semabi.compiler.explorer import affordance_key
            affinity = affordance_key(obs, primitive)
            obs = rec.act(obs, primitive, {"reason": reason, "policy": args.policy,
                                           "candidates": candidates})
            explorer.counts[affinity] += 1
            explorer.last_typed_target = primitive.target if primitive.kind == "type" else None
        return {**rec.summary(), "initial_steps": initial_steps,
                "initial_sha256": {name: digest(args.initial / name)
                                   for name in ("observations.jsonl", "steps.jsonl")},
                "seed": args.seed, "budget": args.budget, "policy": args.policy,
                "targeted_attempts": targeted, "refits": refits,
                "terminal_refit": "performed by scoring process using all acquired history",
                "complete": rec.attempts == args.budget}
    finally:
        browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("script", "acquire"))
    parser.add_argument("--url", required=True)
    parser.add_argument("--reset-url", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--script", type=Path)
    parser.add_argument("--fixture")
    parser.add_argument("--initial", type=Path)
    parser.add_argument("--policy", choices=("contested", "untargeted"))
    parser.add_argument("--budget", type=int, default=60)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output already exists; choose a new immutable run identity")
    if args.mode == "script" and not args.script:
        parser.error("script requires --script")
    if args.mode == "acquire" and (not args.initial or not args.policy or args.script):
        parser.error("acquire requires --initial/--policy and prohibits --script")
    if args.budget < 1:
        parser.error("budget must include at least the reset")
    frozen_hash = verify_freeze(args.freeze)
    args.out.mkdir(parents=True)
    record = {"start": stamp(), "freeze_sha256": frozen_hash, "status": "RUNNING"}
    write(args.out / "run.json", record)
    try:
        result = collect_script(args) if args.mode == "script" else acquire(args)
        record.update(result)
        if verify_freeze(args.freeze) != frozen_hash:
            raise RuntimeError("Freeze manifest changed during collection")
        record["status"] = "FINISHED"
    except BaseException as error:
        record.update(status="ERROR", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        record["end"] = stamp()
        record["raw_hashes"] = {p.name: digest(p) for p in args.out.iterdir()
                                if p.name in ("observations.jsonl", "steps.jsonl", "decisions.jsonl")}
        write(args.out / "run.json", record)
        print(json.dumps(record, default=str), flush=True)


if __name__ == "__main__":
    main()
