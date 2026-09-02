"""Parallel prefetch of the fits a base's questions will need.

The fixpoint is sequential by nature (a verdict can invalidate the next), but
the fits are not: every candidate key a base poses needs one frozen-prefix
fit, independent of the others.  This fills the same on-disk caches the
drivers read, in a process pool, so the sequential loop then hits cache.
No semantics are touched -- only when the work happens.
"""
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")

SPLIT = 0.5


def _token_and_path(run_dir: Path, base: str, family: str, key, variant: str, comparator: str):
    if variant == "v2":
        token = (base, family, str(key))
        return run_dir / "fixpoint_fits" / (hashlib.sha256(repr(token).encode()).hexdigest()[:20] + ".json")
    token = (base, family, str(key), comparator, "node")
    return run_dir / f"fixpoint_fits_{variant}" / (hashlib.sha256(repr(token).encode()).hexdigest()[:20] + ".json")


def fit_rows(args) -> str:
    """One fit, written atomically to the driver's cache path.  Top-level for the pool."""
    run_dir, reading_json, base, family, key, variant, comparator = args
    run_dir = Path(run_dir)
    path = _token_and_path(run_dir, base, family, key, variant, comparator)
    if path.exists():
        return "cached"
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    from semabi.compiler.v4 import pinned as v4_pinned
    from semabi.eval.v4_identity_ties import _override
    log = EvidenceLog(run_dir)
    cut = int(len(log.steps) * SPLIT)
    reading = v4_pinned.PinnedReading.from_json(_override(reading_json, family, key))
    model = csq.fit(run_dir, reading, split=SPLIT)
    m = replace(model, log=log, cut=0)
    state_by_step: dict = {}
    if variant != "v2":
        for p in csq.score(model).predictions:
            state_by_step.setdefault(p.step, []).append(
                {"operator": p.operator, "kind": p.kind, "slot": p.slot,
                 "subject": p.subject, "verdict": p.verdict, "expected": p.expected,
                 "node": p.feature_node, "predicted": p.predicted})
    rows = []
    for step in log.steps:
        if step.step < cut or step.action.kind != "click" or step.action.target is None:
            continue
        v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
        row = {"step": step.step, "verdict": v["verdict"], "admissible": v.get("admissible"),
               "level": v.get("level"), "arguments": v.get("arguments"), "fresh": v.get("fresh")}
        if variant != "v2":
            row["state"] = state_by_step.get(step.step, [])
        rows.append(row)
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows, default=str))
    os.replace(tmp, path)
    return "fitted"


def prefetch(run_dir: Path, pr: dict, variant: str = "v2", comparator: str = "",
             workers: int = 6, families=None) -> dict:
    """Fit, in parallel, every (family, key) the base's questions pose."""
    keys = []
    for q in pr["questions"]:
        if families is not None and q["family"] not in families:
            continue
        for k in (q["left"], q["right"]):
            if (q["family"], str(k)) not in {(f, str(kk)) for f, kk in keys}:
                keys.append((q["family"], k))
    jobs = [(str(run_dir), pr["reading"], pr["base"], f, k, variant, comparator) for f, k in keys]
    todo = [j for j in jobs if not _token_and_path(Path(j[0]), j[2], j[3], j[4], variant, comparator).exists()]
    if not todo:
        return {"keys": len(keys), "fitted": 0}
    with ProcessPoolExecutor(max_workers=min(workers, len(todo))) as ex:
        results = list(ex.map(fit_rows, todo))
    return {"keys": len(keys), "fitted": results.count("fitted")}


def prefetching(prep_fn, run_dir: Path, variant: str = "v2", comparator: str = "",
                workers: int = 6):
    """Wrap a prep_fn so every base it returns has its fits prefetched."""
    def prep(rows):
        pr = prep_fn(rows)
        n = prefetch(run_dir, pr, variant, comparator, workers)
        if n["fitted"]:
            print(f"prefetch: {n['fitted']} fits for {n['keys']} keys on base {pr['base']}", flush=True)
        return pr
    return prep
