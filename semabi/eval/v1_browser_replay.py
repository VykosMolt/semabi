"""Prospective corrected-browser replay of the frozen V1 interaction evidence.

This does not repair stored observations.  It re-executes the historical primitive action
sequence against fresh deterministic app resets using the corrected browser, then compiles
with the exact retained final V1 schema.  It therefore isolates observation settling while
pinning both interaction choices and LLM output.  Any target relocation or action-result
divergence is retained and affects the run status.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from semabi.compiler.browser import Browser
from semabi.compiler.compile_v1 import compile_v1
from semabi.compiler.evidence import EvidenceLog
from semabi.eval import external as ext
from semabi.eval.external import (
    check_failures, domain_from_description, explain_transitions, state_from_json, summarize,
)
from semabi.eval.matching import align
from semabi.eval.recorder import HiddenRecorder, load_hidden

from semabi.eval.v1_corrected_rerun import APPS, compact, delta, sha256, wait_ready


def resolve_target(obs, primitive) -> tuple[object, str | None]:
    p = copy.copy(primitive)
    if p.target is None:
        return p, None
    desc = p.target_desc or {}

    def matches(node):
        return (not desc.get("role") or node.role == desc["role"]) \
            and (not desc.get("name") or node.name == desc["name"]) \
            and (desc.get("placeholder") is None or node.placeholder == desc["placeholder"])

    if p.target < len(obs.nodes) and matches(obs.node(p.target)):
        return p, None
    candidates = [n.i for n in obs.nodes if matches(n)]
    if len(candidates) == 1:
        old = p.target
        p.target = candidates[0]
        return p, f"relocated target {old}->{p.target} by retained role/name/placeholder"
    return p, f"target descriptor had {len(candidates)} matches; retained historical index {p.target}"


def replay(root: Path, historical: Path, run_dir: Path, app_path: Path, port: int) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(historical / "schema.json", run_dir / "schema.json")
    base = f"http://127.0.0.1:{port}"
    server_log_path = run_dir / "server.log"
    divergences = []
    with server_log_path.open("a") as server_log:
        server = subprocess.Popen(
            [sys.executable, str(app_path), "--port", str(port)],
            stdout=server_log, stderr=subprocess.STDOUT, cwd=app_path.parent,
        )
        try:
            wait_ready(base + "/_evaluator/domain", server)
            desc = json.loads(urllib.request.urlopen(base + "/_evaluator/domain", timeout=5).read())
            (run_dir / "hidden_domain.json").write_text(json.dumps(desc, indent=1))
            source = EvidenceLog(historical)
            target = EvidenceLog(run_dir)
            browser = Browser(base + "/", base + "/reset")
            browser.step_hooks.append(HiddenRecorder(run_dir, base + "/_evaluator/state"))
            try:
                browser.goto()
                browser.observe()
                obs = browser.reset(99)  # historical view_sweep reset: recorded by evaluator, not evidence log
                for source_step in source.steps:
                    primitive, relocation = resolve_target(obs, source_step.action)
                    before_sig = obs.structural_signature()
                    result = browser.act(primitive)
                    after = browser.observe()
                    logged_primitive = copy.copy(primitive)
                    if logged_primitive.target is not None and logged_primitive.target >= len(obs.nodes):
                        # The historical browser sometimes acted through a detached element
                        # after its snapshot had gone stale.  Replaying that invalid index can
                        # correctly fail, but V1's catalog assumes every retained target index
                        # belongs to the recorded before-observation.  Preserve the execution
                        # divergence below and omit only this ungroundable target from compiler
                        # input; never substitute another visible control.
                        logged_primitive.target = None
                        logged_primitive.target_desc = None
                        if relocation:
                            relocation += "; compiler-facing invalid target omitted"
                        else:
                            relocation = "compiler-facing invalid target omitted"
                    target.add_step(source_step.episode, logged_primitive, result.ok, result.error, obs, after)
                    event = {}
                    if relocation:
                        event["target_resolution"] = relocation
                    if before_sig != source_step.before:
                        event["before_signature"] = {"historical": source_step.before, "corrected": before_sig}
                    if after.structural_signature() != source_step.after:
                        event["after_signature"] = {"historical": source_step.after,
                                                    "corrected": after.structural_signature()}
                    if result.ok != source_step.ok:
                        event["action_result"] = {"historical": source_step.ok, "corrected": result.ok,
                                                  "error": result.error}
                    if event:
                        event.update({"step": source_step.step, "action": str(primitive)})
                        divergences.append(event)
                    obs = after
            finally:
                browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)

    (run_dir / "replay_provenance.json").write_text(json.dumps({
        "version": 1, "historical_run": str(historical),
        "historical_steps": len(EvidenceLog(historical).steps),
        "corrected_steps": len(EvidenceLog(run_dir).steps),
        "target_resolution_events": sum("target_resolution" in x for x in divergences),
        "action_result_divergences": sum("action_result" in x for x in divergences),
        "observation_signature_divergences": sum(
            "before_signature" in x or "after_signature" in x for x in divergences
        ),
        "events": divergences,
    }, indent=1))

    ext.LINK_DERIVED.clear()
    ext.LINK_FLAGS.clear()
    hidden_dom = domain_from_description(json.loads((run_dir / "hidden_domain.json").read_text()))
    compiled = compile_v1(run_dir, min_support=2)
    hidden = load_hidden(run_dir)
    n = min(len(hidden) - 1, len(compiled.log.steps))
    pairs = [(state_from_json(hidden[i + 1]["state"]), compiled.visible_state_after(i)) for i in range(n)]
    mapping = align(hidden_dom, compiled.model, pairs, attr_agree=0.85, rel_agree=0.8)
    scores, used = explain_transitions(hidden_dom, compiled.model, mapping, hidden)
    check_failures(hidden_dom, compiled.model, mapping, hidden, scores)
    result = summarize(hidden_dom, compiled.model, mapping, scores, used)
    result["cost"] = {"primitives": sum(1 for s in compiled.log.steps if s.action.kind != "reset")}
    (run_dir / "eval.json").write_text(json.dumps(result, indent=1, default=str))
    return result


def write_report(output: Path, root: Path, runs_root: Path, records: dict) -> None:
    statuses = {x.get("status") for x in records.values()}
    if len(records) == len(APPS) and statuses == {"COMPLETE"}:
        campaign_status = "COMPLETE"
    elif len(records) == len(APPS) and statuses <= {"COMPLETE", "EXECUTION_DIVERGENCE"}:
        campaign_status = "COMPLETE_WITH_EXECUTION_DIVERGENCES"
    else:
        campaign_status = "IN_PROGRESS"
    report = {
        "version": 1,
        "status": campaign_status,
        "protocol": {
            "kind": "prospective corrected-browser action/schema-pinned replay",
            "not_claimed": "not a regenerated active-learning run; exact regeneration is blocked when corrected prompts miss the retained LLM cache",
            "browser": "150 ms interval, three identical consecutive snapshots, 3000 ms maximum",
            "actions": "historical primitive sequence replayed under the same reset seeds",
            "schema": "exact retained final schema.json from the historical frozen V1 run",
            "pairing": "hidden evaluator record offset +1 for the unlogged view-sweep reset",
            "compiler": "V1 compiler sources byte-identical to v1.0-grounding",
            "runs_root": str(runs_root),
        },
        "source_sha256": {
            "semabi/compiler/browser.py": sha256(root / "semabi/compiler/browser.py"),
            "semabi/compiler/compile_v1.py": sha256(root / "semabi/compiler/compile_v1.py"),
            "semabi/eval/v1_browser_replay.py": sha256(root / "semabi/eval/v1_browser_replay.py"),
        },
        "apps": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=1, default=str))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", default="runs/v1_corrected_browser_replay_20260823")
    parser.add_argument("--historical-root", default="runs")
    parser.add_argument("--output", default="docs/data/v1_corrected_browser_replay_2026-08-23.json")
    parser.add_argument("--port", type=int, default=8940)
    parser.add_argument("--app", action="append")
    args = parser.parse_args()
    root = Path.cwd()
    runs_root = Path(args.runs_root)
    historical_root = Path(args.historical_root)
    output = Path(args.output)
    records = json.loads(output.read_text()).get("apps", {}) if output.exists() else {}
    selected = [x for x in APPS if not args.app or x[0] in set(args.app)]
    for offset, (canonical, app_dir) in enumerate(selected):
        historical = historical_root / canonical
        run_dir = runs_root / canonical
        corrected_eval = run_dir / "eval.json"
        if corrected_eval.exists():
            corrected = json.loads(corrected_eval.read_text())
            print(f"== {canonical}: completed replay exists", flush=True)
        elif (run_dir / "steps.jsonl").exists() and (run_dir / "steps.jsonl").stat().st_size:
            records[canonical] = {"status": "PARTIAL_REQUIRES_CUSTODY", "run": str(run_dir)}
            write_report(output, root, runs_root, records)
            raise RuntimeError(f"refusing to overwrite incomplete replay: {run_dir}")
        else:
            print(f"== {canonical}: replaying {len(EvidenceLog(historical).steps)} primitives", flush=True)
            corrected = replay(
                root, historical, run_dir,
                root / "experiments/oracle_apps" / app_dir / "app.py",
                args.port + offset,
            )
        historical_result = json.loads((historical / "eval.json").read_text())
        before, after = compact(historical_result), compact(corrected)
        provenance = json.loads((run_dir / "replay_provenance.json").read_text())
        diverged = provenance["action_result_divergences"] or provenance["target_resolution_events"]
        records[canonical] = {
            "status": "EXECUTION_DIVERGENCE" if diverged else "COMPLETE",
            "historical_run": str(historical), "corrected_run": str(run_dir),
            "historical_frozen_v1": before, "corrected_browser_replay": after,
            "delta": delta(before, after),
            "historical_schema_sha256": sha256(historical / "schema.json"),
            "replayed_schema_sha256": sha256(run_dir / "schema.json"),
            "target_resolution_events": provenance["target_resolution_events"],
            "action_result_divergences": provenance["action_result_divergences"],
            "observation_signature_divergences": provenance["observation_signature_divergences"],
        }
        write_report(output, root, runs_root, records)
        print(
            f"   types {after['types_recovered']} attrs {after['attributes_recovered']} "
            f"rels {after['relations_recovered']} ops {after['operators_recovered']} "
            f"target-relocations {provenance['target_resolution_events']} "
            f"action-divergences {provenance['action_result_divergences']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
