"""Baseline 1: raw screen-transition graph.

Nodes are observation signatures, edges are (screen, affordance) -> screen.
It is scored on held-out episodes by whether it can predict the next screen:
this shows how little a screen graph generalises (new strings = new screens).
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import affordance_key


def build(log: EvidenceLog, episodes: set[int]):
    edges: dict[tuple, set] = defaultdict(set)
    nodes = set()
    for s in log.steps:
        if s.episode not in episodes or s.action.kind == "reset":
            continue
        k = affordance_key(log.obs(s.before), s.action)
        edges[(s.before, k)].add(s.after)
        nodes |= {s.before, s.after}
    return nodes, edges


def evaluate(log: EvidenceLog) -> dict:
    eps = sorted(set(s.episode for s in log.steps))
    if len(eps) < 2:
        return {"error": "need >= 2 episodes"}
    train, test = set(eps[:-1]), {eps[-1]}
    nodes, edges = build(log, train)
    n = hit = known_state = 0
    for s in log.steps:
        if s.episode not in test or s.action.kind == "reset":
            continue
        n += 1
        k = affordance_key(log.obs(s.before), s.action)
        if s.before in nodes:
            known_state += 1
        if (s.before, k) in edges and s.after in edges[(s.before, k)]:
            hit += 1
    # screen-level abstraction: ignore typed values by hashing roles+names only
    return {"train_nodes": len(nodes), "train_edges": sum(len(v) for v in edges.values()), "test_steps": n,
            "test_state_seen_in_train": known_state / n if n else 0.0, "next_screen_predicted": hit / n if n else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    log = EvidenceLog(Path(a.run))
    r = evaluate(log)
    print(json.dumps(r, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
