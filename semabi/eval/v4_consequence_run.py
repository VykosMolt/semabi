"""Runs the scoped, outcome-masked consequence check over the retained development chains.
Compiles once per reading and split, then reuses that fit for every applicability mode
and control mutation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.v4 import manifests
from semabi.compiler.v4.pinned import PinnedReading


class _Candidate:
    """A named reading recovered from a manifest as data."""

    def __init__(self, name: str, reading):
        self.name = name
        self.reading = reading


def vessel_keyed(readings: dict):
    """Harbour's reading that makes the rows vessels: the overview and the board are
    both keyed by the vessel's name."""
    def carries_vessels(reading) -> bool:
        # The overview rows are vessels and the call buttons are objects (the
        # created-argument claim needs them). The board key is left unconstrained.
        fams = getattr(reading, "families", None) or {}
        overview = next((f for t, f in fams.items() if "cell@Calls logged" in t), None)
        buttons = fams.get("button[_]")
        return (overview is not None
                and getattr(overview, "key_slot", None) == "cell@Vessel#0"
                and buttons is not None
                and getattr(buttons, "key_slot", None) == "button#0")

    for name in ("joint discrimination x2", "source_choice"):
        reading = readings.get(name)
        if reading is not None and carries_vessels(reading):
            return reading
    raise KeyError("no retained harbour reading keys the overview and the board by "
                   "cell@Vessel#0 (docs/v4_retained.md)")


def _candidates(path: Path):
    """The candidate readings, from a chain manifest or a bare source manifest.

    A manifest pins the hash of the compiler that generated it; the authenticated loader
    refuses one whose compiler has since changed, which happens here on purpose since this
    project changes the inducer. When that happens the readings are still recovered from
    the file as data, but these results are not a claim the frozen compiler produced them.
    Any other mismatch is still an error.
    """
    path = Path(path)
    payload = json.loads(path.read_text())
    try:
        if "source_manifest" in payload:
            return manifests.load_chain_manifest(path).source_manifest.candidates
        return manifests.load_source_manifest(path).candidates
    except manifests.ManifestError as exc:
        # A compiler file changed or was added, or the import closure moved because of
        # one of those. All three mean the manifest was written by a different compiler.
        if not any(m in str(exc) for m in ("implementation hash mismatch",
                                           "implementation file set is not frozen",
                                           "implementation closure is not frozen")):
            raise
        if "source_manifest" in payload:
            path = (path.parent / payload["source_manifest"]["path"]).resolve()
            payload = json.loads(path.read_text())
        return [_Candidate(c["name"], PinnedReading.from_json(c["reading"]))
                for c in payload["candidates"]]
from semabi.compiler.v4.consequence import (ASSERTED, ATTESTED, GENERATIVE,
                                            IDENTITY, MASKED,
                                            NEAR_OPTIMAL, SAME_INDEX, UNMASKED, VALUE,
                                            fit, score)

MUTATIONS = {
    "none": None,
    "never_rendered_token": lambda v: "ZZ_NEVER_RENDERED_BY_THIS_APPLICATION",
    "impossible_ordinal": lambda v: f"{v.split('#')[0]}#9",
    "inverted_toggle": lambda v: (
        v.replace("open", "\x00").replace("closed", "open").replace("\x00", "closed")),
}


def run(chain_path: Path, run_dir: Path, splits, readings=None, mutations=("none",),
        modes=(ASSERTED,), rules=(MASKED,)):
    candidates = {c.name: c.reading for c in _candidates(chain_path)}
    rows = []
    for split in splits:
        for name in (readings or sorted(candidates)):
            model = fit(Path(run_dir), candidates[name], split=split)
            for mode in modes:
                for rule in rules:
                    for mutation in mutations:
                        result = score(model, mutate=MUTATIONS[mutation], applicability=mode,
                                       correspondence=rule)
                        rows.append({"name": name, "mutation": mutation, **result.to_json()})
    return rows


def _fmt(counts: dict) -> str:
    return "/".join(f"{counts.get(k, 0):4d}" for k in
                    ("SUPPORTED", "REFUTED", "POSSIBLE", "UNKNOWN", "NOT_APPLICABLE"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chain", required=True, type=Path,
                        help="a chain manifest, or a source manifest for an application that "
                             "has no frozen chain")
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--split", action="append", type=float, default=None)
    parser.add_argument("--reading", action="append", default=None)
    parser.add_argument("--mutation", action="append", default=None, choices=sorted(MUTATIONS))
    parser.add_argument("--applicability", action="append", default=None,
                        choices=[ASSERTED, ATTESTED, GENERATIVE])
    parser.add_argument("--correspondence", action="append", default=None,
                        choices=[MASKED, NEAR_OPTIMAL, UNMASKED, SAME_INDEX])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = run(args.chain, args.run, args.split or [0.4, 0.5, 0.6, 0.7, 0.8], args.reading,
               args.mutation or ["none"], args.applicability or [ASSERTED],
               args.correspondence or [MASKED])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    print(f"{'split':>5} {'reading':30} {'mode':9} {'match':11} {'mutation':20} "
          f"| {'VALUE  S/R/P/U/NA':^24} | {'EXISTENCE':^24} | {'IDENTITY':^24}")
    for row in rows:
        print(f"{row['split']:5.1f} {row['name'][:30]:30} {row['applicability']:9} "
              f"{row['correspondence_rule']:11} {row['mutation']:20} "
              f"| {_fmt(row['value'])} | {_fmt(row['existence'])} | {_fmt(row['identity'])}")
    print()
    for row in rows:
        b = row["binding"]
        print(f"  {row['name'][:28]:30} {row['applicability']:9} {row['mutation'][:14]:16} "
              f"bindings {b['status']} median={b['median_assignments']} max={b['largest']}")
    print()
    for row in rows:
        if row["value_landing"]:
            print(f"  {row['name'][:28]:30} {row['applicability']:9} {row['mutation']:16} "
                  f"landed: {row['value_landing']}")
    print()
    seen: dict[tuple, dict[str, tuple[str, int]]] = {}
    for row in rows:
        key = (row["split"], row["applicability"], row["correspondence_rule"],
               row["mutation"])
        seen.setdefault(key, {})[row["name"]] = (row["prediction_signature_digest"],
                                                 row["predictions_signed"])
    for key, digests in sorted(seen.items()):
        if len(digests) < 2:
            continue
        groups: dict[str, list[str]] = {}
        # A reading with no testable claim is untested, not its own class: an empty
        # signature would otherwise read as "distinguished from everything".
        untested = [n for n, (_, count) in sorted(digests.items()) if not count]
        for name, (digest, count) in sorted(digests.items()):
            if count:
                groups.setdefault(digest, []).append(name)
        line = " | ".join("{" + ", ".join(g) + "}" for g in groups.values()) or "(none tested)"
        if untested:
            line += "   untested: " + ", ".join(untested)
        print(f"  split {key[0]} {key[1]} {key[2]} {key[3]}: predictive classes: {line}")
    print()
    for row in rows:
        for p in row["refutations"][:2]:
            print(f"  {row['name'][:26]:28} {row['applicability']:9} step {p['step']:4d} "
                  f"{p['kind']:8s} {p['subject']!r} .{p['slot']} -> {p['expected']!r} "
                  f"node {p['feature_node']} {p['correspondence']} saw {p['observed']} "
                  f"{'(clicked row)' if p['action_local'] else '(another row)'}")


if __name__ == "__main__":
    main()
