"""Parallel prefetch of pinned bases and their fits for conditional derivation.

A pinned base is a full search with the family's alternatives refuted; the
sequential conditional derive runs one per candidate per family, in series.  Here
they run in a process pool: each search in a private copy of the corpus (its own
sidecar, no races), the prep JSON written atomically into the shared cache under
the same state-hash key the drivers use; then the (base, family, key) fits in a
second pool via the production `_fit_rows`.  No semantics change; only when the
work happens.
"""
import hashlib
import json
import os
import shutil
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")
sys.path.insert(0, str(Path(__file__).resolve().parent))

SPLIT = 0.5


def state_hash(rows) -> str:
    return hashlib.sha256(json.dumps(
        sorted((r["family"], str(r["key_slot"])) for r in rows)).encode()).hexdigest()[:20]


def _pinned_prep(args) -> str:
    run_dir, cache, rows = args
    run_dir, cache = Path(run_dir), Path(cache)
    disk = cache / f"prep_{state_hash(rows)}.json"
    if disk.exists():
        return "cached"
    from semabi.compiler.compile_v4 import build_hypotheses
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import pinned as v4_pinned
    from semabi.compiler.v4 import search as v4_search
    from semabi.compiler.v4.identity import family_key
    tmp = Path(tempfile.mkdtemp(prefix="pin_", dir=str(run_dir.parent)))
    try:
        for name in ("steps.jsonl", "observations.jsonl", "probes.jsonl", "probes.acquired.jsonl",
                     "field_theories_v4.json", "hidden_domain.json"):
            if (run_dir / name).exists():
                shutil.copy(run_dir / name, tmp / name)
        (tmp / "identity_refutations_v4.json").write_text(json.dumps({"refuted": rows}, indent=1))
        log = EvidenceLog(tmp)
        H0, G = build_hypotheses(tmp, log)
        result = v4_search.search(H0, G, log, run_dir=tmp)
        H = result.hypotheses
        reading = {"name": "fixpoint", "families": {
            family_key(t): {"family": family_key(t), "key_slot": r.key_slot, "status": r.status}
            for t, r in result.chosen.items()}}
        base = v4_pinned.from_search(result, tmp, "retrospective",
                                     refuted=v4_search.read_refutations(tmp)).fingerprint()
        questions = [{"family": q.template, "left": q.left.key_slot, "right": q.right.key_slot}
                     for q in result.open_questions]
        held = {}
        for q in questions:
            for k in (q["left"], q["right"]):
                held[f"{q['family']}||{k}"] = sorted(v4_search.slot_values(H, q["family"], k))
        out = {"base": base, "questions": questions, "held": held, "reading": reading}
        part = disk.with_suffix(".tmp")
        part.write_text(json.dumps(out, default=str))
        os.replace(part, disk)
        return "searched"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def prefetch_pins(run_dir: Path, cache: Path, pinned_states: list, fits: list,
                  comparator: str, workers: int = 4) -> dict:
    """pinned_states: [rows...] to prep; fits: [(family, key, rows)] whose prep must
    exist afterwards -- the fit's base is read from the prep."""
    from semabi.eval.v4_identity_ties import _fit_rows, _rows_cache_path
    todo = [(str(run_dir), str(cache), rows) for rows in pinned_states
            if not (cache / f"prep_{state_hash(rows)}.json").exists()]
    done = {"searched": 0, "fitted": 0}
    if todo:
        with ProcessPoolExecutor(max_workers=min(workers, len(todo))) as ex:
            done["searched"] = list(ex.map(_pinned_prep, todo)).count("searched")
    jobs = []
    for family, key, rows in fits:
        pr = json.loads((cache / f"prep_{state_hash(rows)}.json").read_text())
        if not _rows_cache_path(cache, pr["base"], family, key, comparator).exists():
            jobs.append((str(run_dir), str(cache), pr["reading"], pr["base"], family, key,
                         SPLIT, comparator))
    if jobs:
        with ProcessPoolExecutor(max_workers=min(workers, len(jobs))) as ex:
            done["fitted"] = list(ex.map(_fit_rows, jobs)).count("fitted")
    return done
