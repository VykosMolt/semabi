"""Does the candidate-independent matcher include the continuation the application intended?

The correspondence in :mod:`semabi.compiler.v4.correspondence` is built from the accessibility
tree alone, which is the only thing SemABI is allowed to see.  Whether it is *right* is a
different question, and these applications can answer it: every retained run carries an
``oracle.jsonl`` of the application's own hidden state, one record per observation, with each
domain entity under a stable identifier that persists across re-renders.

That is a diagnostic sidecar and nothing more.  It is never given to the compiler, to a
reading, or to the consequence check; it exists so that a claim like "the matcher relocated
the berth's condition cell" can be checked against what the application says the berth is,
rather than against the matcher's own reasoning.

Two restricted tallies keep the headline number from being a statement about easy inputs: the
same counts over transitions that add or remove nodes, and over the nodes whose index actually
moved -- the only cases a matcher that answered "the same position" could not get right.

The check is deliberately run in the matcher's hardest mode -- the anchoring text masked, as a
prediction about that text would mask it -- and reports the number that matters:
``unique_but_wrong``, a confident correspondence onto the wrong structure, which is the only
failure mode that manufactures a false semantic verdict.  ``ambiguous`` costs coverage and
``none`` costs coverage; neither invents evidence.

Steps that reset the application are excluded: a reset regenerates the scenario and reuses
the entity identifiers, so there is no continuation for the oracle to be right about.  Leaving
them in reported seven confident mismatches that were entirely an artefact of that reuse.

A caveat the numbers cannot carry: an entity whose identifying string is rendered once is
located here *by that string*, so the oracle's realisation and the matcher's evidence overlap
wherever the surrounding structure is thin.  The masking is what keeps the two apart at the
node under test; it does not make the oracle independent of the DOM in general.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Observation
from semabi.compiler.v4.correspondence import AMBIGUOUS, NONE, UNIQUE, Corresponder, mask_outcome


def key_attrs(states: list[dict]) -> dict[str, str]:
    """Per entity type, the string attribute whose value is distinct across its entities."""
    values: dict[tuple[str, str], list[str]] = {}
    for state in states:
        for obj in state["objects"]:
            for attr, value in obj["attrs"].items():
                if isinstance(value, str):
                    values.setdefault((obj["type"], attr), []).append(value)
    out: dict[str, str] = {}
    # Prefer the conventional identifier names.  Taking whichever qualifying attribute came
    # first alphabetically picked ``cargo`` for harbour's vessels, and two vessels can carry
    # the same cargo, so the anchor was lost in exactly the states the check needed it.
    preferred = ("code", "ref", "name", "id", "label", "title")
    def rank(item):
        (etype, attr) = item[0]
        return (etype, preferred.index(attr) if attr in preferred else len(preferred), attr)
    for (etype, attr), seen in sorted(values.items(), key=rank):
        if etype in out:
            continue
        per_state = all(
            len({o["attrs"][attr] for o in state["objects"]
                 if o["type"] == etype and isinstance(o["attrs"].get(attr), str)})
            == len([o for o in state["objects"] if o["type"] == etype])
            for state in states)
        if per_state:
            out[etype] = attr
    return out


def anchors(state: dict, obs: Observation, keys: dict[str, str]) -> dict[str, int]:
    """Entity id -> the one node whose rendered text is that entity's identifying string."""
    by_name: dict[str, list[int]] = {}
    for node in obs.nodes:
        if node.name:
            by_name.setdefault(node.name, []).append(node.i)
    out: dict[str, int] = {}
    for obj in state["objects"]:
        attr = keys.get(obj["type"])
        value = obj["attrs"].get(attr) if attr else None
        if not isinstance(value, str):
            continue
        hits = by_name.get(value, [])
        if len(hits) == 1:
            out[obj["id"]] = hits[0]
    return out


def audit(run_dir: Path, limit: int | None = None) -> dict[str, Any]:
    log = EvidenceLog(run_dir)
    records = [json.loads(line) for line in
               (run_dir / "oracle.jsonl").read_text().splitlines()]
    states = [r["state"] for r in records]
    keys = key_attrs(states)
    corresponder = Corresponder()

    tally: Counter = Counter()
    cells: Counter = Counter()
    vanished: Counter = Counter()
    hard: Counter = Counter()      # the same tally restricted to structural transitions
    shifted: Counter = Counter()   # ... and to cases where the node's index itself moved
    wrong: list[dict[str, Any]] = []
    steps = log.steps[:limit] if limit else log.steps
    for k, step in enumerate(steps):
        if k + 1 >= len(records):
            break
        pre, post = log.obs(step.before), log.obs(step.after)
        if records[k]["sig"] != step.before or records[k + 1]["sig"] != step.after:
            tally["misaligned_oracle_record"] += 1
            continue
        if records[k + 1]["kind"] == "reset":
            # A reset regenerates the scenario and reuses the entity identifiers, so ``b3``
            # before and ``b3`` after are different berths.  There is no continuation to
            # check across one, and treating the oracle as if there were reported the
            # matcher wrong for relocating a row that genuinely ceased to exist.
            tally["reset_no_continuation_exists"] += 1
            continue
        before = anchors(states[k], pre, keys)
        after = anchors(states[k + 1], post, keys)
        # A transition that only rewrites one cell is easy for any matcher; one that adds or
        # removes nodes is where a positional or content-exact rule breaks.  Reporting the
        # restricted tally is what keeps "0 wrong" from being a statement about easy inputs.
        structural = len(pre.nodes) != len(post.nodes)
        for eid, pre_node in sorted(before.items()):
            obj_id = eid
            truth = after.get(eid)
            match = corresponder(pre, post, pre_node, mask_outcome(pre, pre_node))
            if truth is None:
                # Two different situations, and only one of them is about the matcher: the
                # entity is gone from the application's state, or it is still there and its
                # identifying text is no longer rendered exactly once so the oracle has no
                # node to name.  Counting them together made 44 unremarkable relocations look
                # like confident matches onto deleted structure.
                gone = obj_id not in {o["id"] for o in states[k + 1]["objects"]}
                vanished[f"{'removed_from_state' if gone else 'anchor_not_unique_after'}"
                          f"/{match.status}"] += 1
                continue
            outcome = (NONE if match.status == NONE else
                       ("unique_and_correct" if match.unique == truth else "unique_but_wrong")
                       if match.status == UNIQUE else
                       "ambiguous_containing_truth" if truth in match.admissible
                       else "ambiguous_missing_truth")
            if structural:
                hard[outcome] += 1
            if truth != pre_node:
                # The decisive subset.  Most nodes keep their index across a re-render, so a
                # matcher that simply answered "the same index" would score well on the totals
                # above; it cannot score at all here.
                shifted[outcome] += 1
            if match.status == NONE:
                tally["none"] += 1
            elif match.status == UNIQUE:
                tally["unique_and_correct" if match.unique == truth else "unique_but_wrong"] += 1
                if match.unique != truth:
                    wrong.append({"step": step.step, "entity": eid, "pre": pre_node,
                                  "matcher": match.unique, "oracle": truth,
                                  "layers": list(match.layers)})
            else:
                tally["ambiguous_containing_truth" if truth in match.admissible
                      else "ambiguous_missing_truth"] += 1
            _cells(corresponder, pre, post, pre_node, truth, cells, wrong, step.step, eid,
                   hard if structural else None, shifted)
    total = sum(v for k, v in tally.items() if k not in
                ("reset_no_continuation_exists", "misaligned_oracle_record"))
    return {"run": str(run_dir), "key_attributes": keys, "steps": len(steps),
            "anchor_correspondences": total, "anchor": dict(sorted(tally.items())),
            "attribute_cells": dict(sorted(cells.items())),
            "transitions_that_add_or_remove_nodes": dict(sorted(hard.items())),
            "nodes_whose_index_moved": dict(sorted(shifted.items())),
            "no_oracle_truth_available": dict(sorted(vanished.items())),
            "unique_but_wrong": tally["unique_but_wrong"] + cells["unique_but_wrong"],
            "witnesses": wrong[:20]}


def _cells(corresponder, pre, post, pre_anchor: int, truth_anchor: int, cells: Counter,
           wrong: list, step: int, eid: str, hard: Counter | None = None,
           shifted: Counter | None = None) -> None:
    """The same check for every sibling cell of the entity's row, which is where the readings'
    predictions actually land."""
    pre_row = next((a for a in pre.ancestors(pre_anchor) if pre.node(a).role == "row"), None)
    post_row = next((a for a in post.ancestors(truth_anchor) if post.node(a).role == "row"), None)
    if pre_row is None or post_row is None:
        return
    pre_cells = [c for c in pre.children(pre_row) if pre.node(c).role == "cell"]
    post_cells = [c for c in post.children(post_row) if post.node(c).role == "cell"]
    if len(pre_cells) != len(post_cells):
        cells["row_shape_changed_no_truth"] += 1
        return
    for column, (a, b) in enumerate(zip(pre_cells, post_cells)):
        match = corresponder(pre, post, a, mask_outcome(pre, a))
        outcome = (NONE if match.status == NONE else
                   ("unique_and_correct" if match.unique == b else "unique_but_wrong")
                   if match.status == UNIQUE else
                   "ambiguous_containing_truth" if b in match.admissible
                   else "ambiguous_missing_truth")
        if shifted is not None and b != a:
            shifted[outcome] += 1
        if hard is not None:
            hard[NONE if match.status == NONE else
                 ("unique_and_correct" if match.unique == b else "unique_but_wrong")
                 if match.status == UNIQUE else
                 "ambiguous_containing_truth" if b in match.admissible
                 else "ambiguous_missing_truth"] += 1
        if match.status == NONE:
            cells["none"] += 1
        elif match.status == UNIQUE:
            cells["unique_and_correct" if match.unique == b else "unique_but_wrong"] += 1
            if match.unique != b:
                wrong.append({"step": step, "entity": eid, "column": column, "pre": a,
                              "matcher": match.unique, "oracle": b,
                              "layers": list(match.layers)})
        else:
            cells["ambiguous_containing_truth" if b in match.admissible
                  else "ambiguous_missing_truth"] += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path, action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = [audit(run, args.limit) for run in args.run]
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
    for row in rows:
        print(f"== {row['run']}  keys={row['key_attributes']}")
        print(f"   anchors      {row['anchor']}")
        print(f"   row cells    {row['attribute_cells']}")
        print(f"   structural   {row['transitions_that_add_or_remove_nodes']}")
        print(f"   index moved  {row['nodes_whose_index_moved']}")
        print(f"   no oracle truth  {row['no_oracle_truth_available']}")
        print(f"   UNIQUE BUT WRONG: {row['unique_but_wrong']}")
        for w in row["witnesses"][:5]:
            print(f"      step {w['step']} {w['entity']} col {w.get('column')} "
                  f"matcher {w['matcher']} oracle {w['oracle']} layers {w['layers']}")


if __name__ == "__main__":
    main()
