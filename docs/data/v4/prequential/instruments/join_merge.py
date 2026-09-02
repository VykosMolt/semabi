"""Merge retained tie-experiment extensions onto one copy of their source history.

Each result json holds the steps and pages its experiment appended to its plan's history
(`v4_tie_experiment.extension`).  Each extension starts from a reset, so several can be
appended in sequence to one copy of any history: steps renumbered to their position, each
extension its own episode, pages written once by signature.

Usage: join_merge.py <out_dir> <base_run> <result.json>...
"""
import json
import shutil
import sys
from pathlib import Path


def merge(out: Path, source: Path, results: list[Path]) -> int:
    exts = [json.loads(p.read_text()) for p in results]
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(source, out)
    steps = [json.loads(l) for l in (out / "steps.jsonl").read_text().splitlines()]
    seen = {json.loads(l)["sig"] for l in (out / "observations.jsonl").read_text().splitlines()}
    n, episode = len(steps), max((s["episode"] for s in steps), default=-1) + 1
    with (out / "observations.jsonl").open("a") as obs, (out / "steps.jsonl").open("a") as st:
        for e in exts:
            for row in e["extension"]["observations"]:
                if row["sig"] not in seen:
                    seen.add(row["sig"])
                    obs.write(json.dumps(row) + "\n")
            for row in e["extension"]["steps"]:
                st.write(json.dumps({**row, "step": n, "episode": episode}) + "\n")
                n += 1
            episode += 1
    (out / "join_merge.json").write_text(json.dumps(
        {"source": str(source), "results": [str(p) for p in results], "steps": n}, indent=1))
    return n


if __name__ == "__main__":
    print("steps:", merge(Path(sys.argv[1]), Path(sys.argv[2]), [Path(p) for p in sys.argv[3:]]))
