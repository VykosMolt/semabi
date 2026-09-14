"""Checks whether the frozen documents, the machine artifacts and the stored run records
agree, since a freeze is only meaningful if the prose, the JSON and the per-run provenance
say the same thing. Checks which decisions are canonical, how many traces each was tested
on and with what verdict, differential counts, collision before/after, hash-seed
determinism, and the operator ledger, each read from an artifact and compared against the
run records that produced it and the headline claims in `docs/v2_status.md`.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DATA = Path("docs/data/v2")


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text())


def check() -> list[tuple[str, bool, str]]:
    out: list[tuple[str, bool, str]] = []

    def ok(name: str, condition: bool, detail: str = "") -> None:
        out.append((name, bool(condition), detail))

    status = Path("docs/v2_status.md").read_text()
    legacy = _load("control_collision_legacy_2026-08-23.json")["summary"]
    current = _load("control_collision_2026-08-23.json")["summary"]
    determinism = _load("action_alphabet_determinism_2026-08-23.json")
    ledger = _load("operator_eligibility_2026-08-23.json")["summary"]
    prospective = _load("prospective_validation_2026-08-23.json")
    falsification = _load("falsification_2026-08-23.json")

    ok("collision: the rewrite removed every incompatible symbol",
       legacy["total_incompatible_symbols"] > 0 and current["total_incompatible_symbols"] == 0,
       f"{legacy['total_incompatible_symbols']} -> {current['total_incompatible_symbols']}")
    ok("collision: both arms cover the same runs",
       set(_load("control_collision_legacy_2026-08-23.json")["runs"])
       == set(_load("control_collision_2026-08-23.json")["runs"]))
    ok("determinism: identical across every tested hash seed",
       determinism["identical_across_hash_seeds"] and not determinism["differing_compiles"],
       ",".join(determinism["hash_seeds"]))
    ok("ledger: no known-vocabulary miss is unaccounted for",
       not ledger["known_vocabulary_gap"]["unaccounted_after_language_and_support"])
    ok("ledger: the clean denominator is fully recovered",
       ledger["eligible_clean_80pct"] == ledger["eligible_clean_80pct_recovered"],
       f"{ledger['eligible_clean_80pct_recovered']}/{ledger['eligible_clean_80pct']}")

    # every case: artifact statuses must match the decisions stored in the run
    for name, case in prospective["cases"].items():  # noqa: F402
        decisions = json.loads((Path(case["source_run"]) / "refinements_v2.json").read_text())["decisions"]
        stored = {d["id"]: d["status"] for d in decisions}
        ok(f"{name}: decision statuses match the run record", stored == case["decision_statuses"],
           str(stored))
        canonical = sorted(i for i, s in stored.items() if s == "VALIDATED")
        ok(f"{name}: canonical set matches", canonical == sorted(case["canonical_decision_ids"]))
        traces = case.get("held_out_traces", [])
        ok(f"{name}: a contradiction on any trace leaves nothing canonical",
           not (any(t["status"] == "MISPREDICTED" for t in traces) and canonical))

    for name, case in falsification["cases"].items():
        ok(f"{name}: non-canonical cases carry a machine-readable reason",
           bool(case["canonical_decision_ids"]) != bool(case["noncanonical_reason"]),
           str(case["noncanonical_reason"]))

    # the two headline claims of the frozen document
    observatory = prospective["summary"]["differential_by_case"].get("observatory_loop_001", {})
    ok("observatory: differential wins with no reverse case",
       observatory.get("candidate_wins", 0) > 0 and observatory.get("baseline_wins", 1) == 0,
       f"{observatory.get('candidate_wins')}/{observatory.get('baseline_wins')}")
    ok("status document quotes the collision result",
       f"| **{legacy['total_incompatible_symbols']}** | **{current['total_incompatible_symbols']}** |" in status)
    ok("status document names every artifact it relies on",
       all(f"{p.name}`" in status for p in sorted(DATA.glob("*.json"))),
       ", ".join(p.name for p in sorted(DATA.glob("*.json")) if f"{p.name}`" not in status))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    rows = check()
    for name, passed, detail in rows:
        print(f"{'PASS' if passed else 'FAIL'} {name}" + (f"  [{detail}]" if detail else ""))
    report = {"version": 1, "checks": [{"check": n, "passed": p, "detail": d} for n, p, d in rows],
              "all_consistent": all(p for _, p, _ in rows)}
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=1))
    print(("ALL CONSISTENT" if report["all_consistent"] else "INCONSISTENT"))
    raise SystemExit(0 if report["all_consistent"] else 1)


if __name__ == "__main__":
    main()
