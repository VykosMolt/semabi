"""CLI: run phase-1 exploration against a UI and write an evidence log."""
from __future__ import annotations

import argparse
from pathlib import Path

from semabi.compiler.browser import Browser
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import Explorer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--reset-url", required=True)
    ap.add_argument("--run", required=True, type=Path)
    ap.add_argument("--episodes", type=int, default=4)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--record-hidden", default=None, help="evaluator URL (e.g. http://127.0.0.1:8765/_evaluator/state); evaluator side only")
    a = ap.parse_args()
    log = EvidenceLog(a.run)
    b = Browser(a.url, a.reset_url)
    if a.record_hidden:
        from semabi.eval.recorder import HiddenRecorder  # evaluator side; the compiler never sees this
        b.step_hooks.append(HiddenRecorder(a.run, a.record_hidden))
    try:
        Explorer(b, log, seed=a.seed).run(a.episodes, a.steps)
    finally:
        b.close()
    log.save_meta(url=a.url, primitives=b.n_primitives, resets=b.n_resets)
    print(f"{len(log.steps)} steps, {len(log.observations)} distinct observations, {b.n_primitives} primitives")


if __name__ == "__main__":
    main()
