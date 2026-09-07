"""Summarize preserved R1 records through the unchanged T1 measurement helper.

Only fixed logical path aliases change. Every consumed record and repository code
dependency is authenticated before parsing/import; no fit or evaluator control runs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
TRANSPORT = HERE.parent
RAW = TRANSPORT / "first_pass/reservoir"
MANIFEST = HERE / "first_pass_manifest_v1.json"
HELPER = TRANSPORT / "acquisition_summary.py"
STAGES = {"initial_v2": "r1_initial_v1", "evaluation_v2": "r1_evaluation_v1",
          **{f"{policy}_{seed}": f"r1_{policy}_{seed}"
             for seed in (1701, 1702) for policy in ("contested", "untargeted")}}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError("Nonfinite JSON number: " + value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


def relative(path):
    name = path.relative_to(ROOT).as_posix()
    require(path.resolve(strict=True) == path and path.is_file(),
            "Input must be an actual regular repository file: " + name)
    return name


class PreservedInputs:
    """Exact allowlist adapter; unrecognized logical names have no fallback."""
    def __init__(self):
        self.manifest_bytes = MANIFEST.read_bytes()
        relative(MANIFEST)
        self.manifest = parse(self.manifest_bytes)
        require(self.manifest["schema"] == "semabi.transport.reserved_first_pass.v1"
                and self.manifest["status"] == "PRESERVED"
                and self.manifest["all_owned_jobs_terminated"] is True,
                "A complete R1 first-pass preservation is required")
        self.inventory = self.manifest["files"]
        require(isinstance(self.inventory, dict) and self.inventory, "Missing preserved inventory")
        for name, expected in self.inventory.items():
            require(isinstance(name, str) and name and not Path(name).is_absolute()
                    and all(part not in ("", ".", "..") for part in name.split("/"))
                    and isinstance(expected, str) and len(expected) == 64
                    and all(c in "0123456789abcdef" for c in expected), "Malformed preservation inventory")
        self.aliases = {}
        for logical, actual in STAGES.items():
            for name in ("run.json", "decisions.jsonl"):
                self.aliases[f"reservoir/{logical}/{name}"] = RAW / actual / name
            if logical not in ("initial_v2", "evaluation_v2"):
                self.aliases[f"reservoir/{logical}/refits.json"] = RAW / actual / "refits.json"
            if logical != "evaluation_v2":
                self.aliases[f"reservoir/scores/{logical}.json"] = HERE / "scores" / (actual + ".json")
        self.aliases["reservoir/candidates_v2/candidates.json"] = RAW / "r1_candidates_v1/candidates.json"
        self.files = {}
        self.authenticated = {}

    def data(self, path):
        name = relative(path)
        require(name in self.inventory, "Input absent from first-pass preservation: " + name)
        data = path.read_bytes()
        require(sha(data) == self.inventory[name], "Preserved input changed: " + name)
        self.authenticated[name] = self.inventory[name]
        return data

    def read(self, logical, *, lines=False):
        require(logical in self.aliases, "Unsupported R1 logical input: " + logical)
        path = self.aliases[logical]
        data = self.data(path)
        self.files[logical] = {"path": str(path), "sha256": sha(data), "bytes": len(data),
                               "actual_repository_path": relative(path), "logical_alias": logical}
        return [parse(line) for line in data.splitlines() if line.strip()] if lines else parse(data)

    def verify_unchanged(self):
        require(MANIFEST.read_bytes() == self.manifest_bytes, "Preservation manifest changed during summary")
        for name in self.authenticated.copy():
            self.data(ROOT / name)


def summarize():
    inputs = PreservedInputs()
    # Authenticate imports before executing any repository module, including the
    # unchanged scorer imported by the retained helper. No imported fit is called.
    dependencies = {relative(p) for p in (ROOT / "semabi").rglob("*.py")}
    dependencies.update(relative(p) for p in (Path(__file__).resolve(), HELPER,
                                               ROOT / "scripts/transport_score.py"))
    scripts_init = ROOT / "scripts/__init__.py"
    if scripts_init.exists():
        dependencies.add(relative(scripts_init))
    for name in sorted(dependencies):
        inputs.data(ROOT / name)
    for phase in ("implementation", "campaign"):
        path = HERE / (phase + "_freeze_v1.json")
        record = parse(inputs.data(path))
        association = inputs.manifest[phase + "_freeze"]
        require(association == {"path": relative(path), "sha256": inputs.inventory[relative(path)]}
                and record["schema"] == "semabi.transport.reserved_freeze.v1"
                and record["stage"] == phase and record["source_head"] == inputs.manifest["source_head"],
                "Preservation/freeze source association differs")
        for instrument in (Path(__file__).resolve(), HELPER):
            name = relative(instrument)
            require(record["verification_files"].get(name) == inputs.inventory[name],
                    "Summary dependency was not committed before R1")
    for stage in STAGES.values():
        for name in ("observations.jsonl", "steps.jsonl"):
            inputs.data(RAW / stage / name)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("r1_retained_acquisition_summary", HELPER)
    require(spec is not None and spec.loader is not None, "Cannot load retained summary helper")
    retained = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(retained)
    result = {
        "schema": "semabi.transport.reserved_acquisition_summary.v1",
        "retained_summary_schema": retained.SCHEMA,
        "preservation": {"path": relative(MANIFEST), "sha256": sha(inputs.manifest_bytes)},
        "source_head": inputs.manifest["source_head"], "source": inputs.manifest["source"],
        "implementation_freeze": inputs.manifest["implementation_freeze"],
        "campaign_freeze": inputs.manifest["campaign_freeze"],
        "analysis_dependencies": {name: inputs.inventory[name] for name in sorted(dependencies)},
        "stage_aliases": STAGES,
        "path_aliases": {logical: relative(path) for logical, path in sorted(inputs.aliases.items())},
        "alias_scope": "Legacy stage and score names inside retained measurements are logical aliases only; path_aliases identify every actual R1 input.",
        "scope": "Post-preservation analysis of saved R1 observations and scores using unchanged acquisition_summary.py functions; no fitting or oracle input.",
        "hypotheses": "NOT_AUTOMATICALLY_ESTABLISHED; representation, binding, language and runtime failures require diagnosis",
        "support_reconstruction": "Saved score model.outcomes[control].evidence retains complete masks/index/events/about policy; saved query representative_support retains vouches. A vouch is representative, not every supporting conjunction.",
        "fixtures": {"reservoir": retained.summarize_fixture(inputs, "reservoir")},
    }
    require(set(inputs.files) == set(inputs.aliases), "Retained summary did not consume its exact fixed input set")
    inputs.verify_unchanged()
    result["inputs"] = inputs.files
    result["authenticated_inputs"] = dict(sorted(inputs.authenticated.items()))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "acquisition_summary_v1.json")
    args = parser.parse_args()
    output = args.out.absolute()
    require(output.parent.resolve(strict=True) == HERE and output.suffix == ".json"
            and not output.exists() and not output.is_symlink(), "Choose a new R1 summary JSON identity")
    result = summarize()
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"path": relative(output), "sha256": sha(output.read_bytes()),
                      "status": "SUMMARIZED", "preservation_sha256": result["preservation"]["sha256"]}))


if __name__ == "__main__":
    main()
