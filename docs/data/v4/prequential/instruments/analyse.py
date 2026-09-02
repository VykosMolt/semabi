"""Explain every boundary where retrospective and prequential scoring differ.

Two totals are not an explanation.  For each boundary this reads the retained
cell record and says WHY the closure's verdict state differs from the settled
one, row by row, in the campaign's provenance categories:

- later-intervention refutation: a raw experiment row that did not exist at t;
- family absent from the prefix ontology: ontology drift;
- question not yet posed: the prefix search never opened this question;
- undecided at the prefix base: opened, derived, no dominance yet;
- opened but never derived: question stood at the fixpoint;
- closure-only refutation: the prefix refuted a candidate the settled
  ontology no longer poses (a retired question).
"""
import json
import sys
from pathlib import Path

PREQ = Path(__file__).resolve().parent
FINAL_SIDECAR = Path("/home/moloch/semabi/runs/v4/harbour_dev/identity_refutations_v4.json")


def _match(fam: str, candidates: set) -> str | None:
    """The prefix ontology names families under its own headers (t188 renders
    the final cell@Call... family as cell@Calls...), so cross-prefix rows are
    matched by best token similarity, never by exact spelling; an unmatched
    family is reported as ontology drift, not silently bucketed."""
    import difflib
    best = difflib.get_close_matches(fam, list(candidates), n=1, cutoff=0.72)
    return best[0] if best else None


def classify(rec: dict, final_rows: list) -> dict:
    t = rec["t"]
    closure = rec["closure"]
    cfams = {r["family"] for r in closure["sidecar"]}
    ffams = {r["family"] for r in final_rows}
    fam_map = {f: _match(f, cfams) for f in ffams}          # final -> closure family
    crows = {(r["family"], str(r["key_slot"])) for r in closure["sidecar"]}
    frows = {(r["family"], str(r["key_slot"])): r for r in final_rows}
    open_by_fam = {}
    for q in (closure.get("questions") or []):
        open_by_fam.setdefault(q["family"], []).append((str(q["left"]), str(q["right"])))
    events_by_fam = {}
    for e in closure.get("events", []):
        if e["e"] in ("DERIVE", "REDERIVE"):
            events_by_fam.setdefault(e["family"], []).append(
                ((str(e["q"]["left"]), str(e["q"]["right"])), e["out"]))
    missing, matched_closure = [], set()
    for key, row in frows.items():
        fam, k = key
        cfam = fam_map.get(fam)
        if cfam is not None and (cfam, k) in crows:
            matched_closure.add((cfam, k))
            continue
        if "premises" not in row:
            missing.append({"row": key, "cause": "later-intervention refutation",
                            "note": "executed experiment postdates the trace"})
            continue
        if cfam is None:
            missing.append({"row": key, "cause": "family absent from the prefix ontology",
                            "note": "no similarly-named family in the closure"})
            continue
        q = row["premises"]["question"]
        sides = {str(q["left"]), str(q["right"])}
        ev = [(pair, out) for pair, out in events_by_fam.get(cfam, [])
              if sides & set(pair)]
        if any(out == "UNDECIDED" for _, out in ev):
            missing.append({"row": key, "cause": "undecided at the prefix base",
                            "note": f"derived under {cfam[:40]!r}, no dominance yet"})
        elif any(sides & set(pair) for pair in open_by_fam.get(cfam, [])):
            missing.append({"row": key, "cause": "opened but never derived",
                            "note": "question stood at the fixpoint"})
        elif ev:
            missing.append({"row": key, "cause": "derived differently at the prefix",
                            "note": f"{ev[:2]}"})
        else:
            missing.append({"row": key, "cause": "question not yet posed",
                            "note": "the prefix search never opened it"})
    inv_map = {v: k for k, v in fam_map.items() if v is not None}
    extra = []
    for ck in crows:
        if ck in matched_closure:
            continue
        cfam, k = ck
        ffam = inv_map.get(cfam) or _match(cfam, ffams)
        if ffam is not None and (ffam, k) in frows:
            continue            # same verdict, drifted family spelling
        extra.append({"row": list(ck), "cause": "closure-only refutation",
                      "note": ("final ontology lacks this key"
                               if ffam is None else f"final family {ffam[:40]!r} lacks it")})
    return {"t": t, "differs": rec.get("differs"),
            "cell_final": rec.get("cell_final", {}).get("verdict"),
            "cell_prefix": rec.get("cell_prefix", {}).get("verdict"),
            "closure_outcome": closure["outcome"],
            "closure_rows": sorted([r["family"], str(r["key_slot"])]
                                   for r in closure["sidecar"]),
            "missing_vs_final": missing, "closure_only": extra}


def main():
    final_rows = json.loads(FINAL_SIDECAR.read_text())["refuted"]
    out = []
    for f in sorted((PREQ / "cells").glob("t*.json")):
        rec = json.loads(f.read_text())
        out.append(classify(rec, final_rows))
    diffs = [r for r in out if r["differs"]]
    print(f"{len(out)} boundaries, {len(diffs)} with differing claim scores")
    for r in out:
        mark = "DIFF" if r["differs"] else ("same" if r["differs"] is False else "?")
        print(f"\n t={r['t']:3d} [{mark}] closure={r['closure_outcome']} "
              f"rows={len(r['closure_rows'])}")
        print(f"   final:  {r['cell_final']}")
        print(f"   prefix: {r['cell_prefix']}")
        for m in r["missing_vs_final"]:
            print(f"   - missing {m['row'][0][:34]}|{m['row'][1]}: {m['cause']} ({m['note']})")
        for m in r["closure_only"]:
            print(f"   + closure-only {m['row'][0][:34]}|{m['row'][1]}: {m['note']}")
    (PREQ / "provenance.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {PREQ/'provenance.json'}")


if __name__ == "__main__":
    main()
