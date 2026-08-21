"""Append-only interaction evidence log.

steps.jsonl        one record per primitive action (before/after observation sigs)
observations.jsonl every distinct observation, keyed by structural signature
Raw evidence is never discarded; all induction re-reads it.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from semabi.compiler.browser import Primitive
from semabi.compiler.observation import Observation


@dataclass
class Step:
    step: int
    episode: int
    action: Primitive
    ok: bool
    error: str | None
    before: str
    after: str
    typed_tokens: list[str]  # all agent-generated strings so far (for identity anchoring)

    def to_json(self) -> dict:
        return {"step": self.step, "episode": self.episode, "action": self.action.to_json(), "ok": self.ok,
                "error": self.error, "before": self.before, "after": self.after, "typed_tokens": self.typed_tokens}

    @classmethod
    def from_json(cls, d: dict) -> "Step":
        a = d["action"]
        p = Primitive(a["kind"], a.get("target"), a.get("text"), a.get("target_desc"))
        return cls(d["step"], d["episode"], p, d["ok"], d.get("error"), d["before"], d["after"], d.get("typed_tokens", []))


class EvidenceLog:
    def __init__(self, run_dir: Path):
        self.dir = Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.obs_path = self.dir / "observations.jsonl"
        self.steps_path = self.dir / "steps.jsonl"
        self.observations: dict[str, Observation] = {}
        self.steps: list[Step] = []
        self.typed_tokens: list[str] = []
        if self.obs_path.exists():
            for line in self.obs_path.read_text().splitlines():
                d = json.loads(line)
                self.observations[d["sig"]] = Observation.from_json(d["obs"])
        if self.steps_path.exists():
            for line in self.steps_path.read_text().splitlines():
                self.steps.append(Step.from_json(json.loads(line)))
            if self.steps:
                self.typed_tokens = list(self.steps[-1].typed_tokens)

    def add_observation(self, obs: Observation) -> str:
        sig = obs.structural_signature()
        if sig not in self.observations:
            self.observations[sig] = obs
            with self.obs_path.open("a") as f:
                f.write(json.dumps({"sig": sig, "obs": obs.to_json()}) + "\n")
        return sig

    def add_step(self, episode: int, action: Primitive, ok: bool, error: str | None, before: Observation, after: Observation) -> Step:
        if action.kind == "type" and action.text and action.text not in self.typed_tokens:
            self.typed_tokens.append(action.text)
        s = Step(len(self.steps), episode, action, ok, error, self.add_observation(before), self.add_observation(after), list(self.typed_tokens))
        self.steps.append(s)
        with self.steps_path.open("a") as f:
            f.write(json.dumps(s.to_json()) + "\n")
        return s

    def obs(self, sig: str) -> Observation:
        return self.observations[sig]

    def save_meta(self, **kw):
        p = self.dir / "meta.json"
        d = json.loads(p.read_text()) if p.exists() else {}
        d.update(kw)
        d["updated"] = time.time()
        p.write_text(json.dumps(d, indent=1))
