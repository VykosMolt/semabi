"""Is the frozen model invariant under a permutation of the members of a collection?

`docs/v4_open_world.md` found that the observation model had been reading the *position* of
a row -- second in its table -- as part of what the row's cells mean, and that removing
that coordinate collapsed eleven harbour types to five.  A vessel does not become a
different thing by being rendered third instead of first; where the interface declares a
listing, the order of its members is presentation, and nothing the model says about a click
should depend on it.  Renaming (`semabi.eval.v4_renaming`) is the same test for the
spelling of a name.  This is the test for the coordinate.

The transform reverses the members of every declared collection on every page of a held-out
history -- the rows of each body row group, the items of each list -- renumbers the tree
in document order, and remaps every click to the node it landed on.  Header rows stay where
they are: a table's first row is the interface's own declaration and not a member.  Reversal
rather than a random shuffle so that consecutive pages are transformed alike and the
history stays a history.  Every verdict of the version space and the chosen list at every
click is then compared against the untouched history.

Not every rearrangement of a page is neutral, and this one is applied only where the
accessibility tree says a container is a collection.  A difference it reports is a place
where the model read a coordinate.
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v2.graph import COLLECTIONS
from semabi.compiler.v4 import consequence as csq
from semabi.eval.v4_renaming import _verdicts

REVERSE = "reverse"


def _reordered_children(nodes: list[dict]) -> dict[int, list[int]]:
    """Children of every node, with the members of each collection reversed."""
    children: dict[int, list[int]] = {}
    for n in nodes:
        children.setdefault(n["parent"], []).append(n["i"])
    role = {n["i"]: n["role"] for n in nodes}
    parent = {n["i"]: n["parent"] for n in nodes}
    for p, kids in children.items():
        if p < 0 or role.get(p) not in COLLECTIONS or role[p] == "table":
            continue          # row groups within a table keep their order (head, body)
        if role[p] == "rowgroup":
            # the first row of the table is its header, wherever the row groups start
            table = parent.get(p, -1)
            first_row = min((r for r in _rows_of(table, children, role)), default=None)
            keep = [k for k in kids if k == first_row]
            rest = [k for k in kids if k != first_row]
            children[p] = keep + rest[::-1]
        else:
            children[p] = kids[::-1]
    return children


def _rows_of(table: int, children: dict[int, list[int]], role: dict[int, str]) -> list[int]:
    out = []
    stack = [table]
    while stack:
        x = stack.pop()
        for c in children.get(x, []):
            if role.get(c) == "row":
                out.append(c)
            stack.append(c)
    return out


def transform_page(obs: dict, children_of=_reordered_children) -> tuple[dict, dict[int, int]]:
    """The page with its collections reversed, and old node index -> new.

    `children_of` is the rearrangement: the members of each collection reversed here, the
    columns of each table reversed in `semabi.eval.v4_columns`."""
    nodes = obs["nodes"]
    children = children_of(nodes)
    order: list[int] = []
    stack = [n["i"] for n in nodes if n["parent"] < 0][::-1]
    while stack:
        x = stack.pop()
        order.append(x)
        stack.extend(reversed(children.get(x, [])))
    for n in nodes:                          # nodes unreachable from a root, if any
        if n["i"] not in set(order):
            order.append(n["i"])
    new_of = {old: k for k, old in enumerate(order)}
    by_old = {n["i"]: n for n in nodes}
    out_nodes = []
    for old in order:
        n = dict(by_old[old])
        n["i"] = new_of[old]
        n["parent"] = new_of[n["parent"]] if n["parent"] >= 0 else -1
        out_nodes.append(n)
    return {**obs, "nodes": out_nodes}, new_of


def transform_run(src: Path, dst: Path, children_of=_reordered_children) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in src.iterdir():
        if f.name not in ("observations.jsonl", "steps.jsonl") and f.is_file():
            shutil.copy(f, dst / f.name)
    from semabi.compiler.observation import Observation

    maps: dict[str, dict[int, int]] = {}
    sig_of: dict[str, str] = {}
    with (src / "observations.jsonl").open() as fin, (dst / "observations.jsonl").open("w") as fout:
        for line in fin:
            d = json.loads(line)
            page, new_of = transform_page(d["obs"], children_of)
            maps[d["sig"]] = new_of
            # a transformed page is a different page: it carries its own structural
            # signature, so that a fresh fit on the transformed run is self-consistent
            sig_of[d["sig"]] = Observation.from_json(page).structural_signature()
            fout.write(json.dumps({**d, "sig": sig_of[d["sig"]], "obs": page}) + "\n")
    with (src / "steps.jsonl").open() as fin, (dst / "steps.jsonl").open("w") as fout:
        for line in fin:
            d = json.loads(line)
            act = d.get("action") or {}
            if act.get("target") is not None:
                act["target"] = maps[d["before"]][act["target"]]
            for k in ("before", "after"):
                if d.get(k) in sig_of:
                    d[k] = sig_of[d[k]]
            fout.write(json.dumps(d) + "\n")


def compare(run_dir: Path, chain: Path, reading_name: str, score_on: Path, *,
            split: float = 1.0, workdir: Path | None = None) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(Path(run_dir), readings[reading_name], split=split)
    log = EvidenceLog(Path(score_on))
    workdir = Path(workdir or (Path(score_on).parent / f"{Path(score_on).name}_reversed"))
    transform_run(Path(score_on), workdir)
    moved = EvidenceLog(workdir)
    before = _verdicts(model, log)
    after = _verdicts(model, moved)
    assert [b["step"] for b in before] == [a["step"] for a in after]
    same: Counter = Counter()
    diffs = []
    for b, a in zip(before, after):
        control_same = b["control"] == a["control"]
        space_same = b["verdict"] == a["verdict"] and b["admissible"] == a["admissible"]
        list_same = b["list"] == a["list"] and b["predicted"] == a["predicted"]
        same["controls"] += control_same
        same["version space"] += space_same
        same["decision list"] += list_same
        if not (control_same and space_same and list_same):
            diffs.append({"step": b["step"], "control": (b["control"], a["control"]),
                          "verdict": (b["verdict"], a["verdict"]),
                          "admissible": (b["admissible"], a["admissible"]),
                          "list": (b["list"], a["list"]),
                          "observed": (b["observed"], a["observed"])})
    return {"run": Path(run_dir).name, "reading": reading_name, "scored_on": Path(score_on).name,
            "transform": REVERSE, "clicks": len(before), "same": dict(same),
            "verdicts_before": dict(Counter(b["verdict"] for b in before)),
            "verdicts_after": dict(Counter(a["verdict"] for a in after)),
            "differences": diffs[:80], "n_differences": len(diffs)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--score-on", required=True)
    ap.add_argument("--split", type=float, default=1.0)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    r = compare(Path(a.run), Path(a.chain), a.reading, Path(a.score_on), split=a.split,
                workdir=Path(a.workdir) if a.workdir else None)
    print(f"\n{r['run']}  {r['reading']!r}  scored on {r['scored_on']}  members {r['transform']}d")
    print(f"  {r['clicks']} clicks; identical: {r['same']}")
    print(f"  version space before: {r['verdicts_before']}")
    print(f"  version space after:  {r['verdicts_after']}")
    for d in r["differences"][:25]:
        print(f"    step {d['step']}: control {d['control']}  verdict {d['verdict']}  "
              f"admissible {d['admissible']}  list {d['list']}")
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1, default=str))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
