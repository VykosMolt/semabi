"""Synthetic checks of accounting and session isolation; no fixture outcomes.

Run: .venv/bin/python docs/data/v4/transport/recorder_selfcheck.py OUTPUT.json
"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from semabi.compiler.browser import Primitive, ActionResult
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Observation, Node

spec = importlib.util.spec_from_file_location("transport_collect", ROOT / "scripts/transport_collect.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
obs = Observation([Node(0, -1, "group", ""), Node(1, 0, "button", "Try")])


class SyntheticBrowser:
    def __init__(self, *args):
        self.episode = self.calls = 0
        self.n_settle_timeouts = self.n_navigation_waits = 0

    def goto(self):
        raise AssertionError("Previous session must never be observed")

    def observe(self):
        assert self.calls > 0, "Snapshot before reset would leak prior session"
        return obs

    def act(self, primitive):
        self.calls += 1
        if primitive.kind == "reset":
            self.episode += 1
        return ActionResult(self.calls % 2 == 1,
                            "synthetic failure" if self.calls % 2 == 0 else None)

    def close(self):
        pass


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        initial, out = root / "initial", root / "arm"
        out.mkdir()
        log = EvidenceLog(initial)
        log.add_step(9, Primitive("click", 1), True, None, obs, obs)
        args = SimpleNamespace(initial=initial, out=out, url="unused", reset_url="unused",
                               seed=1701, policy="untargeted", budget=16)
        with patch.object(module, "Browser", SyntheticBrowser), \
             patch.object(module.csq, "fit", return_value=object()) as fit, \
             patch.object(module, "context", side_effect=AssertionError("Control read model")):
            result = module.acquire(args)
        assert result["charged_attempts"] == 16 and result["failed_attempts"] == 8
        combined = EvidenceLog(out)
        assert len(combined.steps) == 16 and combined.steps[0].to_json() == log.steps[0].to_json()
        assert result["paired_steps_recorded"] == 15 and result["unpaired_attempts"] == 1
        assert {step.episode for step in combined.steps[1:]} == {10}
        assert fit.call_count == 2 and result["targeted_attempts"] == 0
        records = [json.loads(line) for line in (out / "decisions.jsonl").read_text().splitlines()]
        assert len(records) == 16 and records[0]["action"]["kind"] == "reset"
        assert records[0]["pre_state_unobserved"]
        assert records[0]["before"] is None and records[0]["step"] is None
        assert combined.steps[1].action.kind == "reload"
        assert combined.obs(combined.steps[1].before).nodes == obs.nodes
        assert all(not row.get("candidates") for row in records)
        missing, error = module.resolve(obs, {"kind": "click", "role": "button", "name": "absent"})
        assert missing.target is None and error
        rec = module.Recorder(SyntheticBrowser(), EvidenceLog(root / "missing"), root / "missing.jsonl")
        rec.act(obs, missing, {"reason": "missing target"}, error=error)
        assert rec.attempts == rec.failures == 1 and rec.browser.calls == 0
        duplicate = Observation(obs.nodes + [Node(2, 0, "button", "Try")])
        missing, error = module.resolve(duplicate, {"kind": "click", "role": "button", "name": "Try"})
        assert missing.target is None and error
        payload = {
            "schema": "transport.recorder.selfcheck.v3", "provenance": module.stamp(),
            "source_sha256": module.digest(ROOT / "scripts/transport_collect.py"),
            "selfcheck_sha256": module.digest(Path(__file__)), "passed": True,
            "checks": ["budget includes reset", "failed attempts retained", "initial prefix unchanged",
                       "untargeted selection cannot read model", "15-step refit schedule",
                       "missing targets charged without clicking", "ambiguous targets refused",
                       "no snapshot before reset", "appended episodes unique",
                       "unobserved reset retained outside paired steps", "real reload supplies boundary"],
            "result": result,
        }
        target = Path(sys.argv[1])
        if target.exists():
            raise FileExistsError("Preserve original results; choose another identity")
        module.write(target, payload)
        print(json.dumps({"checks_passed": len(payload["checks"]), "output": str(target)}))


if __name__ == "__main__":
    main()
