"""Compares what a control's label says against what the control does. A rendered label
can carry a word that is also a value elsewhere on the page, and whether that matters is a
question about behaviour: for every control family, this reports the tokens masked as data
in its labels, the values its learned effects write, and which masked tokens are also
values the family writes, meaning the token is really the action's argument. Nothing here
changes a reading; it reports what the history says a word in a label is for.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from semabi.compiler.v2.graph import tokens
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4.consequence import control_of


def roles(run_dir: Path, chain: Path, reading_name: str, *, split: float = 0.5) -> dict:
    from semabi.eval.v4_consequence_run import _candidates

    readings = {c.name: c.reading for c in _candidates(chain)}
    model = csq.fit(Path(run_dir), readings[reading_name], split=split)
    A, log = model.abstractor, model.log
    written: dict[str, Counter] = defaultdict(Counter)
    for op in model.operators:
        core = op.core()
        if len(core) != 1 or core[0].loc is None:
            continue
        fam = control_of(core[0].loc.slot)
        for e in op.effs:
            v = getattr(e, "new", None)
            if isinstance(v, str) and v and not v.startswith("?") and v != "*":
                written[fam][v] += op.support
    masked: dict[str, Counter] = defaultdict(Counter)
    labelled: dict[str, Counter] = defaultdict(Counter)
    for s in log.steps[:model.cut]:
        if s.action.kind != "click" or s.action.target is None:
            continue
        obs = log.obs(s.before)
        sig = A.ensure(obs)
        fam = control_of(A.control_family(obs).get(s.action.target, ""))
        for t in tokens(obs.node(s.action.target).name or ""):
            if not t[0].isalnum():
                continue
            (masked if A.G.is_data_at(sig, s.action.target, t) else labelled)[fam][t] += 1
    out = {}
    for fam in sorted(set(written) | set(masked) | set(labelled)):
        out[fam] = {"writes": dict(written[fam].most_common()),
                    "masked": dict(masked[fam].most_common(8)),
                    "label": dict(labelled[fam].most_common(8)),
                    "arguments": sorted(t for t in masked[fam] if t in written[fam]),
                    "label_words_it_writes": sorted(t for t in labelled[fam] if t in written[fam])}
    return {"run": Path(run_dir).name, "reading": reading_name, "cut": model.cut, "families": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", required=True)
    ap.add_argument("--chain", required=True)
    ap.add_argument("--reading", required=True)
    ap.add_argument("--split", type=float, default=0.5)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    r = roles(Path(a.run), Path(a.chain), a.reading, split=a.split)
    print(f"\n{r['run']}  {r['reading']!r}  cut={r['cut']}")
    for fam, d in r["families"].items():
        print(f"  {fam:45} writes {d['writes']}  masked {d['masked']}  label {d['label']}")
        if d["arguments"] or d["label_words_it_writes"]:
            print(f"      arguments (masked, and written): {d['arguments']}   "
                  f"label words it writes: {d['label_words_it_writes']}")
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
