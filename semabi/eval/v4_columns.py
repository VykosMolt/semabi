"""Is the model invariant under a permutation of a table's columns?

`semabi.eval.v4_metamorphic` reverses the members of every collection and
`semabi.eval.v4_renaming` renames every name; both are presentation coordinates the frozen
model must not read.  A table's column order is a third: the header row declares what
each column means, and a vet's appointment keyed by its patient and its reason is the same
appointment when the reason column is rendered first.  The hypotheses name a slot by the
node's offset within its unit (`cell#0@3`), which is a position, not a column
(`docs/v4_frontier.md`), so this is the attack that finds out whether that matters.

The transform reverses the cells of every row of every table -- header and body rows alike,
each cell with its whole subtree, so header and field stay aligned -- renumbers the tree in
document order and remaps every click.  Two comparisons:

* **frozen**: the model fitted on the untouched history, scored on the column-reversed
  held-out history -- the version space, the chosen list and the durable ledger at every
  click, as the reversal instrument does.  A difference here is the model reading a column
  position.
* **refit**: the identity search run on the column-reversed run's prefix, its reading and
  entity types compared with the search on the untouched run *by column header*, and the
  two readings' suffix ledgers compared.  A difference here is the learner reading one.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import consequence as csq
from semabi.eval.v4_metamorphic import _rows_of, transform_run
from semabi.eval.v4_renaming import _ledger, _verdicts

REVERSE_COLUMNS = "reverse columns"


def _column_reversed_children(nodes: list[dict]) -> dict[int, list[int]]:
    """Children of every node, with the cells of every table row reversed."""
    children: dict[int, list[int]] = {}
    for n in nodes:
        children.setdefault(n["parent"], []).append(n["i"])
    role = {n["i"]: n["role"] for n in nodes}
    for t in [n["i"] for n in nodes if n["role"] == "table"]:
        for r in _rows_of(t, children, role):
            kids = children.get(r, [])
            if all(role.get(k) == "cell" for k in kids):
                children[r] = kids[::-1]
    return children


def transform(src: Path, dst: Path) -> None:
    transform_run(src, dst, _column_reversed_children)


def frozen(run_dir: Path, chain: Path, reading_name: str, score_on: Path, *,
           split: float = 1.0, workdir: Path | None = None) -> dict:
    """The frozen model on a column-reversed held-out history."""
    if reading_name == "search":
        # the search's own reading of the run (the manifests' pinned readings name families
        # and slots by the scheme in force when they were frozen)
        _, reading, _ = _search_reading(Path(run_dir), split)
    else:
        from semabi.eval.v4_consequence_run import _candidates

        reading = {c.name: c.reading for c in _candidates(chain)}[reading_name]
    model = csq.fit(Path(run_dir), reading, split=split)
    log = EvidenceLog(Path(score_on))
    workdir = Path(workdir or (Path(score_on).parent / f"{Path(score_on).name}_columns_reversed"))
    transform(Path(score_on), workdir)
    moved = EvidenceLog(workdir)
    before, after = _verdicts(model, log), _verdicts(model, moved)
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
                          "list": (b["list"], a["list"])})
    ledger_before, ledger_after = _ledger(model, log), _ledger(model, moved)
    ledger_diffs = [{"step": s, "before": ledger_before.get(s), "after": ledger_after.get(s)}
                    for s in sorted(set(ledger_before) | set(ledger_after))
                    if ledger_before.get(s) != ledger_after.get(s)]
    return {"run": Path(run_dir).name, "reading": reading_name, "scored_on": Path(score_on).name,
            "transform": REVERSE_COLUMNS, "comparison": "frozen", "clicks": len(before),
            "same": dict(same), "verdicts_before": dict(Counter(b["verdict"] for b in before)),
            "verdicts_after": dict(Counter(a["verdict"] for a in after)),
            "differences": diffs[:60], "n_differences": len(diffs),
            "ledger_steps": len(set(ledger_before) | set(ledger_after)),
            "ledger_same": len(set(ledger_before) | set(ledger_after)) - len(ledger_diffs),
            "ledger_differences": ledger_diffs[:40], "n_ledger_differences": len(ledger_diffs)}


def _search_reading(run_dir: Path, split: float):
    from semabi.compiler.compile_v4 import _normalise_sections, build_hypotheses
    from semabi.compiler.v4 import pinned as pn
    from semabi.compiler.v4 import search as v4_search

    full = EvidenceLog(run_dir)
    cut = int(len(full.steps) * split)
    _normalise_sections(full, stats_from=full.through(cut))
    prefix = full.through(cut)
    H, G = build_hypotheses(run_dir, prefix)
    result = v4_search.search(H, G, prefix, run_dir=run_dir)
    return result, pn.from_search(result, run_dir, name="search"), prefix


def _slot_columns(result, log) -> dict[str, dict[str, str]]:
    """For each family, the header text under each key slot component, read off the page:
    the slot's node is a cell; the header row's cell at the same column names it."""
    out: dict[str, dict[str, str]] = {}
    H = result.hypotheses
    for template, unit in H.units.items():
        if not unit.key_slot:
            continue
        fam = next((f for f, ts in result.families.items() if template in ts), template)
        for part in unit.key_slot.split("|"):
            if part in out.get(fam, {}):
                continue
            for inst in unit.instances:
                node = inst.slot_nodes.get(part)
                if node is None or inst.sig not in log.observations:
                    continue
                obs = log.obs(inst.sig)
                header = _header_of(obs, node)
                if header is not None:
                    out.setdefault(fam, {})[part] = header
                    break
            out.setdefault(fam, {}).setdefault(part, "?")
    return out


def _header_of(obs, node: int) -> str | None:
    """The header cell's text for the column a node stands in, if it is in a table."""
    x = node
    cell = None
    while x >= 0:
        n = obs.node(x)
        if n.role == "cell":
            cell = x
        if n.role == "row":
            row = x
            break
        x = n.parent
    else:
        return None
    if cell is None:
        return None
    col = obs.children(row).index(cell)
    t = row
    while t >= 0 and obs.node(t).role != "table":
        t = obs.node(t).parent
    if t < 0:
        return None
    rows = []
    stack = [t]
    while stack:
        y = stack.pop()
        for c in obs.children(y):
            if obs.node(c).role == "row":
                rows.append(c)
            stack.append(c)
    header = min(rows) if rows else None
    if header is None:
        return None
    cells = obs.children(header)
    return (obs.node(cells[col]).name or "") if col < len(cells) else None


def refit(run_dir: Path, *, split: float = 0.5, workdir: Path | None = None) -> dict:
    """The learner on a column-reversed run against the learner on the untouched run."""
    from semabi.eval.v4_reading_selection import _ledger as suffix_ledger

    run_dir = Path(run_dir)
    workdir = Path(workdir or (run_dir.parent / f"{run_dir.name}_columns_reversed"))
    transform(run_dir, workdir)
    a_res, a_reading, a_prefix = _search_reading(run_dir, split)
    b_res, b_reading, b_prefix = _search_reading(workdir, split)
    a_cols, b_cols = _slot_columns(a_res, a_prefix), _slot_columns(b_res, b_prefix)
    families = sorted(set(a_reading.families) | set(b_reading.families))
    rows = []
    for fam in families:
        ka = a_reading.families[fam].key_slot if fam in a_reading.families else None
        kb = b_reading.families[fam].key_slot if fam in b_reading.families else None
        ha = sorted(a_cols.get(fam, {}).values()) if ka else []
        hb = sorted(b_cols.get(fam, {}).values()) if kb else []
        rows.append({"family": fam, "key_original": ka, "key_reversed": kb,
                     "columns_original": ha, "columns_reversed": hb, "same_columns": ha == hb})
    a_led = suffix_ledger(csq.score(csq.fit(run_dir, a_reading, split=split)))
    b_led = suffix_ledger(csq.score(csq.fit(workdir, b_reading, split=split)))
    return {"run": run_dir.name, "transform": REVERSE_COLUMNS, "comparison": "refit", "split": split,
            "families": rows, "n_families_differing": sum(1 for r in rows if not r["same_columns"]),
            "withheld_original": [list(p) for p in a_res.withheld_unions],
            "withheld_reversed": [list(p) for p in b_res.withheld_unions],
            "final_original": a_res.final.to_json(), "final_reversed": b_res.final.to_json(),
            "suffix_ledger": {"original": a_led, "reversed": b_led}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain")
    ap.add_argument("--reading")
    ap.add_argument("--score-on", help="frozen comparison: the held-out history to reverse")
    ap.add_argument("--refit", action="store_true", help="refit comparison on the run's own prefix")
    ap.add_argument("--split", type=float, default=None)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.refit:
        r = refit(Path(a.run), split=a.split if a.split is not None else 0.5,
                  workdir=Path(a.workdir) if a.workdir else None)
        print(f"\n{r['run']}  columns reversed, refit  split={r['split']}")
        for row in r["families"]:
            flag = "" if row["same_columns"] else "   <- differs"
            print(f"  {row['family'][:50]:50} {row['key_original']!s:20} {row['columns_original']}  |  "
                  f"{row['key_reversed']!s:20} {row['columns_reversed']}{flag}")
        print(f"  withheld: {r['withheld_original']} | {r['withheld_reversed']}")
        print(f"  suffix ledger original {r['suffix_ledger']['original']}  reversed {r['suffix_ledger']['reversed']}")
    else:
        if not (a.reading and a.score_on) or (a.reading != "search" and not a.chain):
            ap.error("frozen comparison needs --reading (a chain reading, or 'search') and --score-on")
        r = frozen(Path(a.run), Path(a.chain) if a.chain else None, a.reading, Path(a.score_on),
                   split=a.split if a.split is not None else 1.0,
                   workdir=Path(a.workdir) if a.workdir else None)
        print(f"\n{r['run']}  {r['reading']!r}  scored on {r['scored_on']}  columns reversed")
        print(f"  {r['clicks']} clicks; identical: {r['same']}")
        print(f"  version space before: {r['verdicts_before']}")
        print(f"  version space after:  {r['verdicts_after']}")
        print(f"  durable ledger: {r['ledger_same']} of {r['ledger_steps']} steps identical")
        for d in r["differences"][:12]:
            print(f"    step {d['step']}: control {d['control']}  verdict {d['verdict']}  list {d['list']}")
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1, default=str))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
