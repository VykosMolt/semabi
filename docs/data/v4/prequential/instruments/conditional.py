"""Conditional bases: judge F=a and F=b each in the world its own key implies.

Finding 7: a pairwise comparison judged inside a third world -- the neutral base,
where F is unkeyed -- confounds the keys with the cross-family structure each key
triggers (on harbour the Vessel override overlaps a Vessel-keyed board and the
builder unions them; in the Vessel world proper the board is None and nothing
collides).  Here each side is fitted under the reading the search settles on with
F pinned to that side's key: pinning = lifting F's own rows and refuting F's other
posed candidates.  Other families are free to re-settle.  The tournament's
invalidation still keys on the neutral base (cross-family staleness); the verdict's
premises additionally record the two conditional bases.

Pure core (`conditional_derive`) for scripted attack; `make_conditional` wires it to
the production prep/fit path with the same caches.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")
sys.path.insert(0, str(Path(__file__).resolve().parent))


def candidates_of(pr, family):
    out = []
    for q in pr["questions"]:
        if q["family"] == family:
            for k in (q["left"], q["right"]):
                if k not in out:
                    out.append(k)
    return out


def pin_rows(current_rows, family, key, candidates):
    """The sidecar state in which F's own rows are lifted and every other posed
    candidate of F is refuted: the world F=key implies, other families free."""
    others = [r for r in current_rows if r["family"] != family]
    pins = [{"family": family, "key_slot": c, "held": [], "why": "conditional pin",
             "evidence": {"instrument": "conditional base"}}
            for c in candidates if str(c) != str(key)]
    return others + pins


def conditional_derive(prep_fn, rows_for_fn, decide, current_rows_fn, prefetch=None):
    """derive_fn: (pr, family, left, right) -> decision, each side on its own base.
    ``prefetch(family, cands, cur)`` may warm every pinned base and fit for the
    family at once (cond_prefetch); the sequential path below then hits caches."""
    warmed: set = set()
    def derive(pr, family, left, right):
        cands = candidates_of(pr, family)
        for k in (left, right):
            if k not in cands:
                cands.append(k)
        cur = current_rows_fn()
        if prefetch is not None:
            token = (family, tuple(sorted(map(str, cands))),
                     tuple(sorted((r["family"], str(r["key_slot"])) for r in cur if r["family"] != family)))
            if token not in warmed:
                warmed.add(token)
                prefetch(family, cands, cur)
        pa = prep_fn(pin_rows(cur, family, left, cands))
        pb = prep_fn(pin_rows(cur, family, right, cands))
        d = decide(rows_for_fn(pa, family, left), rows_for_fn(pb, family, right))
        d["conditional"] = {"left_base": pa["base"], "right_base": pb["base"]}
        d.pop("details", None)
        return d
    return derive


def make_conditional(run_dir: Path, comparator: str, split: float = 0.5):
    """Production wiring: prep from attack.make_prep_derive (state-hash cached),
    fits via the production _fit_rows into the same cache."""
    from attack import make_prep_derive
    from semabi.eval.v4_identity_ties import (_rows_cache_path, _fit_rows, retro_decision,
                                              retro_decision_shared, EMISSION_COMPARATOR)
    prep0, _ = make_prep_derive(run_dir)
    cache = run_dir / "fixpoint_fits"
    state = {"rows": []}

    def prep(rows):
        state["rows"] = list(rows)
        return prep0(rows)

    def rows_for(pr_side, family, key):
        path = _rows_cache_path(cache, pr_side["base"], family, key, comparator)
        if not path.exists():
            _fit_rows((str(run_dir), str(cache), pr_side["reading"], pr_side["base"],
                       family, key, split, comparator))
        return json.loads(path.read_text())

    decide = retro_decision if comparator == EMISSION_COMPARATOR else retro_decision_shared

    def prefetch(family, cands, cur):
        from cond_prefetch import prefetch_pins
        states = [pin_rows(cur, family, k, cands) for k in cands]
        fits = [(family, k, pin_rows(cur, family, k, cands)) for k in cands]
        n = prefetch_pins(run_dir, cache, states, fits, comparator, workers=6)
        print(f"prefetch pins {family[:40]}: {n}", flush=True)

    return prep, conditional_derive(prep0, rows_for, decide, lambda: state["rows"], prefetch)
