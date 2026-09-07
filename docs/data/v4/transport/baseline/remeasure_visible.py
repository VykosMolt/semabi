"""Correct only raw visible-binding measurements of a completed retained fit.

This reuses the original recorded role and bound-object rows; it neither fits
the learner nor changes any original decision-list or version-space result.
"""
from collections import Counter
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from check_corpora import visible_check
from semabi.compiler.evidence import EvidenceLog

OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def role(data):
    fields = dict(data)
    if "parts" in fields:
        fields["parts"] = [role(part) for part in fields["parts"]]
    return SimpleNamespace(**fields)


def main(case):
    original = OUT / (case + ".json")
    record = json.loads(original.read_text())
    roles = {name: role(data) for name, data in (record.get("fit") or {}).get("roles", {}).items()}
    result = {"case": case, "recorded_utc": datetime.datetime.now(datetime.UTC).isoformat(),
              "original_result": original.name, "original_result_sha256": digest(original),
              "measurement_instrument_sha256": digest(OUT / "check_corpora.py"),
              "remeasurement_instrument_sha256": digest(Path(__file__)),
              "scope": "Existing bound-object rows against raw visible observations only; no learner refit or prediction change."}
    for part, key in (("development", "dev"), ("holdout", "hold")):
        directory = Path(record["provenance"][key])
        if os.environ.get("SEMABI_BASELINE_CORPORA"):
            directory = Path(os.environ["SEMABI_BASELINE_CORPORA"]) / directory.name
        log = EvidenceLog(directory)
        steps = {step.step: step for step in log.steps}
        rows = []
        for before in record[part]["rows"]:
            step = steps[before["step"]]
            bound = {name: SimpleNamespace(**obj) for name, obj in before.get("bound", {}).items()}
            checks = visible_check(log.obs(step.before), step.action.target, bound, roles)
            rows.append({"step": step.step, "before": step.before, "raw_target": step.action.target,
                         "visible_checks": checks})
        questions = sorted({c["question"] for row in rows for c in row["visible_checks"]})
        result[part] = {"target_clicks": len(rows),
                        "visible_check_ledger": dict(Counter(c["status"] for r in rows
                                                            for c in r["visible_checks"])),
                        "visible_check_scope": {question: dict(Counter(c["status"] for r in rows
                            for c in r["visible_checks"] if c["question"] == question))
                            for question in questions}, "rows": rows}
    (OUT / (case + "_visible_v3.json")).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({part: {key: value for key, value in result[part].items() if key != "rows"}
                      for part in ("development", "holdout")}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
