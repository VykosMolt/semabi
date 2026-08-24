"""Read-only EvidenceLog construction over descriptor-retained V4 bytes.

This adapter lives entirely on the V4 side of the frozen compiler boundary.  The shared
``semabi.compiler.evidence`` implementation remains byte-identical to the V2 tag.
"""
from __future__ import annotations

import json
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog, Step
from semabi.compiler.observation import Observation


class RetainedEvidenceLog(EvidenceLog):
    """An EvidenceLog object graph that cannot write to its descriptive run path."""

    def add_observation(self, obs: Observation) -> str:
        del obs
        raise RuntimeError("retained V4 evidence is read-only")

    def add_step(self, *args, **kwargs) -> Step:
        del args, kwargs
        raise RuntimeError("retained V4 evidence is read-only")

    def save_meta(self, **kwargs) -> None:
        del kwargs
        raise RuntimeError("retained V4 evidence is read-only")


def from_bytes(
    observations: bytes,
    steps: bytes,
    *,
    run_dir: Path,
) -> RetainedEvidenceLog:
    """Parse exact retained JSONL bytes without opening ``run_dir``."""

    if not isinstance(observations, bytes) or not isinstance(steps, bytes):
        raise TypeError("retained evidence requires immutable bytes inputs")
    log = RetainedEvidenceLog.__new__(RetainedEvidenceLog)
    log.dir = Path(run_dir)
    log.obs_path = log.dir / "observations.jsonl"
    log.steps_path = log.dir / "steps.jsonl"
    log.observations = {}
    log.steps = []
    log.typed_tokens = []

    def lines(raw: bytes, label: str) -> list[str]:
        try:
            return raw.decode("utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise ValueError(f"{label} is not valid UTF-8 JSONL") from exc

    for line in lines(observations, "observations.jsonl"):
        try:
            row = json.loads(line)
            log.observations[row["sig"]] = Observation.from_json(row["obs"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("invalid observations.jsonl record") from exc
    for line in lines(steps, "steps.jsonl"):
        try:
            log.steps.append(Step.from_json(json.loads(line)))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("invalid steps.jsonl record") from exc
    if log.steps:
        log.typed_tokens = list(log.steps[-1].typed_tokens)
    return log
