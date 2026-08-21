"""Evaluator-side hook: record the hidden state after every primitive action.

Written to <run>/hidden.jsonl, keyed by step index. The compiler never reads it."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path


class HiddenRecorder:
    def __init__(self, run_dir: Path, evaluator_url: str):
        self.path = Path(run_dir) / "hidden.jsonl"
        self.url = evaluator_url
        self.n = 0
        if self.path.exists():
            self.n = sum(1 for _ in self.path.open())

    def __call__(self, browser, primitive, result) -> None:
        snap = json.loads(urllib.request.urlopen(self.url, timeout=5).read())
        rec = {"step": self.n, "episode": snap["episode"], "state": snap["state"], "log_len": len(snap["log"]),
               "last_op": snap["log"][-1] if snap["log"] else None}
        with self.path.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        self.n += 1


def load_hidden(run_dir: Path) -> list[dict]:
    p = Path(run_dir) / "hidden.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
