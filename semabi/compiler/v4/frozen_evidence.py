"""Build a read-only EvidenceLog from retained bytes instead of from a run directory.

The shared ``semabi.compiler.evidence`` implementation stays byte-identical to the V2 tag;
this adapter sits beside it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

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

    @classmethod
    def from_bytes(
        cls,
        observations: bytes,
        steps: bytes,
        *,
        probes: bytes | None = None,
        acquired_probes: bytes | None = None,
        run_dir: Path,
    ) -> "RetainedEvidenceLog":
        """Construct a read-only parser from one retained byte object."""

        retained = from_bytes(observations, steps, probes=probes,
                              acquired_probes=acquired_probes, run_dir=run_dir)
        if not isinstance(retained, cls):
            raise TypeError("retained evidence class mismatch")
        return retained


def from_bytes(
    observations: bytes,
    steps: bytes,
    *,
    probes: bytes | None = None,
    acquired_probes: bytes | None = None,
    run_dir: Path,
) -> RetainedEvidenceLog:
    """Parse retained JSONL bytes without opening ``run_dir``.

    Every call builds a fresh object graph for the abstractor; the run path is provenance
    only. Acquired probes (``probes.acquired.jsonl``, run after the trace on a fresh instance
    for controls the explorer never probed) go into the same graph, marked ``acquired``.
    """

    if not isinstance(observations, bytes) or not isinstance(steps, bytes):
        raise TypeError("retained evidence requires immutable bytes inputs")
    log = RetainedEvidenceLog.__new__(RetainedEvidenceLog)
    log.dir = Path(run_dir)
    log.obs_path = log.dir / "observations.jsonl"
    log.steps_path = log.dir / "steps.jsonl"
    log.observations = {}
    log.steps = []
    log.typed_tokens = []
    log.probe_records = _parse_probe_records(probes) + [
        {**record, "acquired": True} for record in _parse_probe_records(acquired_probes)]

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


def _parse_probe_records(raw: bytes | None) -> list[dict[str, Any]]:
    """Parse the optional probe JSONL sidecar into fresh mutable records."""

    if raw is None:
        return []
    if not isinstance(raw, bytes):
        raise TypeError("retained probes require immutable bytes input")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("probes.jsonl is not valid UTF-8 JSONL") from exc

    records: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"probes.jsonl record {number} is malformed JSON") from exc
        if not isinstance(row, Mapping) or not isinstance(row.get("key"), list):
            raise ValueError(
                f"probes.jsonl record {number} must contain a list-valued key"
            )
        if any(isinstance(item, (dict, list, set)) for item in row["key"]):
            raise ValueError(f"probes.jsonl record {number} key values must be scalar")
        for field_name in ("sensing_steps", "sensing_actions"):
            value = row.get(field_name)
            if value is not None and not isinstance(value, list):
                raise ValueError(
                    f"probes.jsonl record {number} {field_name} must be a list"
                )
            if field_name == "sensing_actions" and value is not None:
                for action in value:
                    if not isinstance(action, Mapping) or not isinstance(action.get("key"), list):
                        raise ValueError(
                            f"probes.jsonl record {number} sensing action is malformed"
                        )
            if field_name == "sensing_steps" and value is not None:
                if any(isinstance(step, bool) or not isinstance(step, int) for step in value):
                    raise ValueError(
                        f"probes.jsonl record {number} sensing step numbers are malformed"
                    )
        # json.loads already builds a new graph; copying the outer mapping keeps ownership
        # explicit even for a decoder that returns a shared mapping.
        records.append(dict(row))
    return records
