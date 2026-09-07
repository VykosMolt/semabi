"""Synthetic normalization chronology audit; no application/fixture inputs.

Run from the repository root with the command in report.md. The only in-memory
ablation inserts ``probe.learning = False`` before non-source observations enter
the normalization probe. No learner source or fixture files are changed.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from semabi.compiler import compile_v4 as compiler
from semabi.compiler.browser import Primitive
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v4 import consequence
from semabi.compiler.v4.identity import family_key
from semabi.compiler.v4.pinned import FamilyReading, PinnedReading


ROOT = Path(__file__).resolve().parents[6]
SOURCE_PATHS = (
    "semabi/compiler/compile_v4.py",
    "semabi/compiler/v4/consequence.py",
    "semabi/compiler/v2/graph.py",
    "semabi/compiler/v2/sections.py",
    "semabi/compiler/v2/abstractor.py",
    "semabi/compiler/v4/abstractor.py",
    "semabi/compiler/v2/units.py",
    "semabi/compiler/evidence.py",
    "semabi/compiler/observation.py",
    "semabi/compiler/v4/search.py",
)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in SOURCE_PATHS}


def frozen_probe_control():
    """Build the exact helper with one inserted line, only inside this process."""
    original = inspect.getsource(compiler._normalise_sections)
    needle = "    for sig, obs in log.observations.items():\n"
    assert original.count(needle) == 1
    modified = original.replace(needle, "    probe.learning = False\n" + needle, 1)
    namespace = dict(compiler.__dict__)
    exec(compile(modified, "<diagnostic frozen-probe control>", "exec"), namespace)
    return namespace["_normalise_sections"]


def five_node_page(first: str, second: str) -> Observation:
    return Observation([
        Node(0, -1, "group", ""),
        Node(1, 0, "heading", first), Node(2, 0, "button", "Go"),
        Node(3, 0, "heading", second), Node(4, 0, "button", "Go"),
    ])


def numbered_page(first: str, second: str) -> Observation:
    return Observation([
        Node(0, -1, "group", ""),
        Node(1, 0, "heading", "Item"), Node(2, 0, "text", first),
        Node(3, 0, "button", "Go"),
        Node(4, 0, "heading", "Item"), Node(5, 0, "text", second),
        Node(6, 0, "button", "Go"),
    ])


def write_log(directory: Path, before: Observation, future: Observation,
              target: int = 2) -> EvidenceLog:
    log = EvidenceLog(directory)
    action = Primitive("click", target, target_desc={"role": "button", "name": "Go"})
    log.add_step(0, action, True, None, before, before)
    log.add_step(0, action, True, None, before, future)
    return log


def payload(log) -> dict:
    return {"observations": {sig: obs.to_json() for sig, obs in log.observations.items()},
            "steps": [step.to_json() for step in log.steps]}


def representation(log) -> dict:
    for sig, obs in log.observations.items():
        assert sig == obs.structural_signature()
    for step in log.steps:
        assert step.before in log.observations and step.after in log.observations
        assert log.obs(step.before).node(step.action.target).key()[:2] == ("button", "Go")
    return {
        "digest": digest(payload(log)),
        "observations": [
            {"signature": sig, "node_count": len(obs.nodes),
             "parents": [node.parent for node in obs.nodes]}
            for sig, obs in log.observations.items()
        ],
        "steps": [step.to_json() for step in log.steps],
        "signatures_resolve": True,
        "action_target_preserved": True,
    }


def graph_statistics(G) -> str:
    # Calling data_set first resolves its caches; added runtime structure is excluded.
    data = sorted(G.data_set())
    return digest({
        "data": data, "seen": sorted(G._seen),
        "templates": sorted((key, sorted(tt.strings.items()), tt.n)
                            for key, tt in G.templates.items()),
        "variation": sorted((repr(key), sorted(tt.strings.items()), tt.n)
                            for key, tt in G.templates_v.items()),
    })


def main(output: Path) -> None:
    hashes_before = source_hashes()
    control = frozen_probe_control()
    p = five_node_page("Alpha", "Beta Gamma")
    q = five_node_page("Delta", "Epsilon Zeta")
    report = {
        "source_hashes_at_start": hashes_before,
        "normalizer_source_sha256": hashlib.sha256(
            inspect.getsource(compiler._normalise_sections).encode()).hexdigest(),
        "synthetic_pages": {"P": p.to_json(), "Q": q.to_json()},
        "direct_normalization": {}, "fits": {}, "live_parity": {},
    }
    with tempfile.TemporaryDirectory(prefix="semabi-chronology-audit-") as temp:
        base = Path(temp)
        directories = {}
        for name, future in (("same_future", p), ("changed_future", q)):
            directories[name] = base / name
            write_log(directories[name], p, future)

        prefix_payloads = [payload(EvidenceLog(d).through(1)) for d in directories.values()]
        frontier_payloads = [payload(EvidenceLog(d).before_action(1)) for d in directories.values()]
        assert prefix_payloads[0] == prefix_payloads[1]
        assert frontier_payloads[0] == frontier_payloads[1]
        report["raw_prefix_digest"] = digest(prefix_payloads[0])
        report["raw_frontier_digest"] = digest(frontier_payloads[0])

        for name, directory in directories.items():
            row = report["direct_normalization"][name] = {}
            for mode, helper in (("current", compiler._normalise_sections),
                                 ("frozen_probe", control)):
                log = EvidenceLog(directory)
                helper(log, stats_from=log.through(1))
                row[mode] = representation(log)
                # The original indices retain the same complete node key, not only labels.
                normalized_p = log.obs(log.steps[0].before)
                assert [node.key() for node in normalized_p.nodes[:5]] == [
                    node.key() for node in p.nodes]
            full_current, full_control = EvidenceLog(directory), EvidenceLog(directory)
            compiler._normalise_sections(full_current)
            control(full_control)
            assert payload(full_current) == payload(full_control)
            row["stats_from_none_control_equals_current"] = True
            row["full_fit_representation"] = representation(full_current)

        for regime in (consequence.FROZEN_PREFIX, consequence.CAUSAL_PREQUENTIAL):
            regime_rows = report["fits"][regime] = {}
            for mode in ("current", "frozen_probe"):
                modes = regime_rows[mode] = {}
                for name, directory in directories.items():
                    context = (patch.object(compiler, "_normalise_sections", control)
                               if mode == "frozen_probe" else nullcontext())
                    with context:
                        fit = consequence.fit(directory, PinnedReading(), at=1,
                                              min_support=1, regime=regime,
                                              read_outputs=False)
                    modes[name] = {
                        "evidence": representation(fit.evidence),
                        "full_log": representation(fit.log),
                        "graph_statistics_digest": graph_statistics(fit.abstractor.G),
                        "graph_observation_nodes": [len(obs.nodes)
                                                   for obs in fit.abstractor.G.obs.values()],
                        "graph_is_hypothesis_graph": fit.abstractor.G is fit.abstractor.H.G,
                        "frozen": not fit.abstractor.G.learning,
                        "operator_count": len(fit.operators),
                        "entity_type_count": len(fit.abstractor.types),
                    }
                evidence = [row["evidence"] for row in modes.values()]
                assert (evidence[0] == evidence[1]) == (mode == "frozen_probe")
                assert all(row["operator_count"] == 0 for row in modes.values())

        # Independent parity witness with an ordinary recurring section template.
        numbered_p, numbered_q = numbered_page("1", "2"), numbered_page("3", "4")
        numbered_dir = base / "numbered"
        write_log(numbered_dir, numbered_p, numbered_q, target=3)
        H, _ = compiler.build_hypotheses(numbered_dir, EvidenceLog(numbered_dir).through(1))
        reading = PinnedReading({family_key(t): FamilyReading(family_key(t), unit.key_slot)
                                 for t, unit in H.units.items()}, name="prefix-only-numbered")
        report["live_parity"]["pinned_reading_from_prefix"] = reading.to_json()
        for mode in ("current", "frozen_probe"):
            context = (patch.object(compiler, "_normalise_sections", control)
                       if mode == "frozen_probe" else nullcontext())
            with context:
                fit = consequence.fit(numbered_dir, reading, at=1, min_support=1,
                                      read_outputs=False)
            A = fit.abstractor
            offline = fit.log.obs(fit.log.steps[1].after)
            statistics_before = graph_statistics(A.G)
            normalized_objects = sorted((tid, key) for tid, key in A.abstract(offline).objs)
            raw_sig = A.ensure(numbered_q)
            raw_objects = sorted((tid, key) for tid, key in A.abstract(numbered_q).objs)
            statistics_after = graph_statistics(A.G)
            assert len(offline.nodes) == 9 and len(A.G.obs[raw_sig].nodes) == 7
            assert len(normalized_objects) == 2 and not raw_objects
            assert statistics_before == statistics_after
            report["live_parity"][mode] = {
                "raw_page": numbered_q.to_json(),
                "offline_signature": offline.structural_signature(),
                "offline_nodes": len(offline.nodes),
                "offline_objects": normalized_objects,
                "live_signature": raw_sig, "live_nodes": len(A.G.obs[raw_sig].nodes),
                "live_objects": raw_objects,
                "graph_is_hypothesis_graph": A.G is A.H.G,
                "runtime_graph_statistics_unchanged": statistics_before == statistics_after,
            }

    report["source_hashes_at_end"] = source_hashes()
    assert hashes_before == report["source_hashes_at_end"], "Source changed during audit; rerun."
    report["assertions_passed"] = True
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"PASS: future evidence changes prefix sections in both regimes; report: {output}")
    print("PASS: frozen-probe control removes that dependence and preserves full normalization")
    print("PASS: live/offline object discrepancy is independent and remains with frozen probe")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results.json"))
    main(parser.parse_args().output)
