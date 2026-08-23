"""End-to-end smoke test on the kanban UI (requires Playwright/Chromium)."""
import tempfile
from pathlib import Path

import pytest

from semabi import relmodel as rm
from semabi.compiler.browser import Browser
from semabi.compiler.compile import compile_log
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import Explorer
from semabi.env.server import World, serve
from semabi.eval.matching import evaluate
from semabi.eval.recorder import HiddenRecorder, load_hidden


@pytest.mark.slow
def test_kanban_random_phase_recovers_types():
    # an ephemeral port: a fixed range collides with a leftover server or with the
    # instrumented gauntlet-v2 apps on 8800-8807 and fails the run for no reason
    world = World("standard", 0)
    srv = serve(world, 0)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    with tempfile.TemporaryDirectory() as d:
        run = Path(d)
        try:
            log = EvidenceLog(run)
            b = Browser(f"{base}/ui/kanban", f"{base}/reset")
            b.step_hooks.append(HiddenRecorder(run, f"{base}/_evaluator/state"))
            try:
                Explorer(b, log, seed=0).run(2, 25)
            finally:
                b.close()
            C = compile_log(run)
            hidden = load_hidden(run)
            pairs = [(rm.State.from_json(r["state"]), C.learned_state_after(i)) for i, r in enumerate(hidden)]
            res = evaluate(world.domain, C.model, pairs, [p[0] for p in pairs][:20])
            assert res["types"]["recovered"] == 2
            assert res["operators"]["recovered"] >= 3
        finally:
            srv.shutdown()
