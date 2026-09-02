"""Every reachable tournament fixpoint, exhaustively, within a bound.

The production tournament loop (semabi.eval.v4_identity_ties.tournament_fixpoint)
is nondeterministic at exactly two points: which stale family is re-run first, and
which open family is taken next.  The authoritative closure is defined as the
intersection over reachable fixpoints; the production schedule family {fwd, rev}
is a sample of that set.  This enumerates the set (DFS over the choice points,
memoised on canonical state) and reports whether the sample's intersection is the
true one.  Cycles along a path are reported, not resolved: the harbour prefixes
never cycled and a cycle here would be a finding of its own.

Usage: enumerate_fixpoints.py <run_dir> <name> <out_json> [max_states]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from attack import make_prep_derive, stamp
from fitcache import prefetching
from semabi.eval.v4_identity_ties import tournament


def enumerate_fixpoints(prep_fn, derive_fn, raw_rows, max_states=5000):
    """Returns {"endpoints": {frozenset rows: n_paths}, "states": n, "cycles": n}."""

    def rows_of(derived, excluding=None):
        return list(raw_rows) + [
            {"family": f, "key_slot": k, "held": None, "premises": {"base": b}, "why": ""}
            for (f, k, b) in sorted(derived, key=str) if f != excluding]

    def candidates_of(pr, family):
        out = []
        for q in pr["questions"]:
            if q["family"] == family:
                for k in (q["left"], q["right"]):
                    if k not in out:
                        out.append(k)
        return out

    def run_family(derived, family, neutral):
        """The production run_family, functional: returns the family's new rows."""
        others = {r for r in derived if r[0] != family}
        seen = list(candidates_of(neutral, family))
        while True:
            t = tournament(derive_fn, neutral, family, seen)
            mine = {(family, str(c), neutral["base"]) for c in t["dominated"]}
            later = prep_fn(rows_of(others | mine))
            grown = [c for c in candidates_of(later, family) if c not in seen]
            if not grown:
                return others | mine
            seen.extend(grown)

    endpoints: dict = {}
    seen_states: set = set()
    cycles = 0
    visited = 0

    def canon(derived, attempted, closed):
        return (frozenset(derived), frozenset(attempted), frozenset(closed))

    def dfs(derived, attempted, closed, path):
        nonlocal cycles, visited
        key = canon(derived, attempted, closed)
        if key in path:
            cycles += 1
            return
        if key in seen_states:
            return
        seen_states.add(key)
        visited += 1
        if visited > max_states:
            raise RuntimeError(f"state bound {max_states} exceeded")
        # invalidation first: branch over every stale family
        stale = []
        for fam in sorted({f for f, _, _ in derived}):
            own = prep_fn(rows_of(derived, excluding=fam))
            if any(b != own["base"] for f, _, b in derived if f == fam):
                stale.append((fam, own))
        if stale:
            for fam, own in stale:
                new = run_family(derived, fam, own)
                dfs(frozenset(new), attempted, closed, path | {key})
            return
        pr = prep_fn(rows_of(derived))
        active = {f for f, _, _ in derived}
        fams = []
        for q in pr["questions"]:
            f = q["family"]
            if f in fams or f in active or f in closed:
                continue
            neutral = prep_fn(rows_of(derived, excluding=f))
            if (f, neutral["base"]) in attempted:
                continue
            fams.append((f, neutral))
        if not fams:
            ep = frozenset((f, k) for f, k, _ in derived)
            endpoints[ep] = endpoints.get(ep, 0) + 1
            return
        for f, neutral in fams:
            new = run_family(derived, f, neutral)
            dfs(frozenset(new), attempted | {(f, neutral["base"])}, closed, path | {key})

    dfs(frozenset(), frozenset(), frozenset(), frozenset())
    return {"endpoints": endpoints, "states": visited, "cycles": cycles}


def main():
    run_dir, name, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    bound = int(sys.argv[4]) if len(sys.argv) > 4 else 5000
    sidecar = run_dir / "identity_refutations_v4.json"
    original = json.loads(sidecar.read_text()) if sidecar.exists() else {"refuted": []}
    raw = [r for r in original.get("refuted", []) if "premises" not in r]
    sidecar.write_text(json.dumps({"refuted": raw}, indent=1))
    prep, derive = make_prep_derive(run_dir)
    prep = prefetching(prep, run_dir, "v2", workers=6)
    r = enumerate_fixpoints(prep, derive, raw, bound)
    eps = list(r["endpoints"].items())
    inter_all = set.intersection(*[set(e) for e, _ in eps]) if eps else set()
    union_all = set.union(*[set(e) for e, _ in eps]) if eps else set()
    rec = {"stamp": stamp(), "run": str(run_dir), "name": name,
           "reachable_fixpoints": len(eps), "states_visited": r["states"], "cycles": r["cycles"],
           "endpoints": [{"rows": sorted(map(list, e)), "paths": n} for e, n in eps],
           "intersection_all": sorted(map(list, inter_all)),
           "disputed_all": sorted(map(list, union_all - inter_all))}
    out.write_text(json.dumps(rec, indent=1, default=str))
    print(name, "reachable fixpoints:", len(eps), "| states:", r["states"], "| cycles:", r["cycles"])
    print("  intersection over all:", len(inter_all), "rows | disputed:", len(union_all - inter_all))


if __name__ == "__main__":
    main()
