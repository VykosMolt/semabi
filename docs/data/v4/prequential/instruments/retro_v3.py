"""claim-content-v3-delta: the retrospective comparator with the state channel.

Scratch implementation, for attack; production adoption only after the
scripted cases here, the harbour regression, the twin decision and a
schedule-attack re-run all pass.

Row shape: the v2 emission row plus a "state" list of that step's
ScopedPrediction claims under the fitted reading:
    {"step": int, <v2 emission fields>, "state": [claim, ...]}
    claim = {"operator","kind","slot","subject","verdict","expected"}

Units: emission units exactly as v2 (`_units`); plus one right unit per
SUPPORTED state claim with a non-empty checked expected value, one wrong
unit per REFUTED claim.  POSSIBLE and NOT_APPLICABLE contribute nothing --
projection silence is neither equivalence nor defeat -- and unchecked
support (no expected value) earns nothing.  Channels are disjoint by
construction; no atom counts twice.  The dominance rule is unchanged:
refuted exactly when the other side predicts strictly more of what the
application returned while getting nothing more wrong.
"""
import sys

sys.path.insert(0, "/home/moloch/semabi")

from semabi.eval.v4_identity_ties import _claim_signature, _units  # v2 emission channel

SUPPORTED, REFUTED = "SUPPORTED", "REFUTED"
COMPARATOR = "claim-content-v3-delta"


def _state_sig(row) -> tuple:
    return tuple(sorted((c["operator"], c["kind"], c["slot"], str(c.get("subject")),
                         c["verdict"], str(c.get("expected")))
                        for c in row.get("state") or []))


def _state_units(row) -> tuple[int, int]:
    right = sum(1 for c in row.get("state") or []
                if c["verdict"] == SUPPORTED and str(c.get("expected") or "") != "")
    wrong = sum(1 for c in row.get("state") or [] if c["verdict"] == REFUTED)
    return right, wrong


def sig_v3(row) -> tuple:
    return (_claim_signature(row), _state_sig(row))


def units_v3(row) -> tuple[int, int]:
    er, ew = _units(row)
    sr, sw = _state_units(row)
    return er + sr, ew + sw


COMPARATOR_SHARED = "claim-content-v3s-shared"


def _atoms(row) -> dict:
    """State claims keyed by an ontology-neutral coordinate: (kind, page node),
    falling back to the slot when no node was recorded."""
    out = {}
    for c in row.get("state") or []:
        out[(c["kind"], c.get("node") if c.get("node") is not None else c["slot"])] = c
    return out


def _shared_units(l_atoms: dict, r_atoms: dict) -> tuple:
    """(left right/wrong, right right/wrong) over atoms both readings claim."""
    shared = set(l_atoms) & set(r_atoms)
    def units(atoms):
        r = sum(1 for k in shared if atoms[k]["verdict"] == SUPPORTED
                and str(atoms[k].get("expected") or "") != "")
        w = sum(1 for k in shared if atoms[k]["verdict"] == REFUTED)
        return r, w
    return units(l_atoms), units(r_atoms), len(l_atoms) - len(shared), len(r_atoms) - len(shared)


def retro_decision_v3s(left_rows: list, right_rows: list) -> dict:
    """R1': dominance over the shared claim surface only.  A finer ontology's
    extra vocabulary (creation claims for objects the other reading does not
    have) is provenance, never evidence."""
    by_left = {r["step"]: r for r in left_rows}
    counts = {"left": {"right": 0, "wrong": 0}, "right": {"right": 0, "wrong": 0}}
    unshared = {"left": 0, "right": 0}
    diffs = 0
    for r in right_rows:
        l = by_left.get(r["step"])
        if l is None:
            continue
        la, ra = _atoms(l), _atoms(r)
        shared = set(la) & set(ra)
        shared_sig = lambda a: tuple(sorted((k, a[k]["verdict"], str(a[k].get("expected")))
                                            for k in shared))
        if _claim_signature(l) == _claim_signature(r) and shared_sig(la) == shared_sig(ra):
            unshared["left"] += len(la) - len(shared)
            unshared["right"] += len(ra) - len(shared)
            continue
        diffs += 1
        (lr, lw), (rr, rw), ul, ur = _shared_units(la, ra)
        er_l, ew_l = _units(l)
        er_r, ew_r = _units(r)
        counts["left"]["right"] += er_l + lr
        counts["left"]["wrong"] += ew_l + lw
        counts["right"]["right"] += er_r + rr
        counts["right"]["wrong"] += ew_r + rw
        unshared["left"] += ul
        unshared["right"] += ur
    out = {"comparator": COMPARATOR_SHARED, "disagreements": diffs, "counts": counts,
           "unshared": unshared, "outcome": "UNDECIDED"}
    lc, rc = counts["left"], counts["right"]
    if diffs and lc["right"] > rc["right"] and lc["wrong"] <= rc["wrong"]:
        out.update(outcome="DECIDED", refuted="right", survivor="left")
    elif diffs and rc["right"] > lc["right"] and rc["wrong"] <= lc["wrong"]:
        out.update(outcome="DECIDED", refuted="left", survivor="right")
    return out


def retro_decision_v3(left_rows: list, right_rows: list) -> dict:
    by_left = {r["step"]: r for r in left_rows}
    diffs = []
    for r in right_rows:
        l = by_left.get(r["step"])
        if l is not None and sig_v3(l) != sig_v3(r):
            diffs.append((l, r))
    counts = {"left": {"right": 0, "wrong": 0}, "right": {"right": 0, "wrong": 0}}
    for l, r in diffs:
        lr, lw = units_v3(l)
        rr, rw = units_v3(r)
        counts["left"]["right"] += lr
        counts["left"]["wrong"] += lw
        counts["right"]["right"] += rr
        counts["right"]["wrong"] += rw
    out = {"comparator": COMPARATOR, "disagreements": len(diffs),
           "counts": counts, "outcome": "UNDECIDED"}
    lc, rc = counts["left"], counts["right"]
    if diffs and lc["right"] > rc["right"] and lc["wrong"] <= rc["wrong"]:
        out.update(outcome="DECIDED", refuted="right", survivor="left")
    elif diffs and rc["right"] > lc["right"] and rc["wrong"] <= lc["wrong"]:
        out.update(outcome="DECIDED", refuted="left", survivor="right")
    return out
