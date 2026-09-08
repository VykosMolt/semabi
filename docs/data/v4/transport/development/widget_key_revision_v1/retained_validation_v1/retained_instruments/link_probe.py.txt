"""Judge each created-later link decision by evidence on the shared surface.

The hypothesis builder turns a key-overlapping template into a LINK type when its
key repeats within observations or its rows appear later for keys the other family
already showed -- a doctrine, never judged.  `Hypotheses.force_link` flips that
decision per template (V2 refinement's own toggle).  For each linked template on a
corpus: fit the default reading and the flipped one (union instead of link), collect
both readings' node-keyed state claims plus emission claims on the frozen-prefix
suffix, and compare on the shared surface with `retro_decision_shared`.

Usage: link_probe.py <run_dir> <doctrine_json> <out_json>
"""
import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, "/home/moloch/semabi")

SPLIT = 0.5


def settled_reading(run_dir: Path):
    """The search's own reading on the whole history, pinned: every retained
    instrument fits a PinnedReading; fitting with none runs the search inside the
    prefix view, which does not hold the full graph."""
    from semabi.compiler.compile_v4 import build_hypotheses
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import pinned as v4_pinned
    from semabi.compiler.v4 import search as v4_search
    log = EvidenceLog(run_dir)
    H0, G = build_hypotheses(run_dir, log)
    result = v4_search.search(H0, G, log, run_dir=run_dir)
    return v4_pinned.from_search(result, run_dir, "link-probe")


def rows_under(run_dir: Path, forced: set, reading) -> list:
    """Suffix rows (emission + node-keyed state claims) with force_link=forced."""
    import semabi.compiler.compile_v4 as c4
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.v4 import consequence as csq
    from semabi.compiler.v4 import outcome as oc
    original = c4.build_hypotheses

    def patched(run, log, promoted=None):
        H, G = original(run, log, promoted)
        H.force_link = set(forced)      # read when compile builds the entity types
        return H, G
    c4.build_hypotheses = patched
    try:
        log = EvidenceLog(run_dir)
        cut = int(len(log.steps) * SPLIT)
        model = csq.fit(run_dir, reading, split=SPLIT)
        m = replace(model, log=log, cut=0)
        state_by_step: dict = {}
        for p in csq.score(model).predictions:
            state_by_step.setdefault(p.step, []).append(
                {"operator": p.operator, "kind": p.kind, "slot": p.slot, "subject": p.subject,
                 "verdict": p.verdict, "expected": p.expected, "node": p.feature_node})
        rows = []
        for step in log.steps:
            if step.step < cut or step.action.kind != "click" or step.action.target is None:
                continue
            v = oc.score_step_admissible(m, step, corroborated=True, hypothesis=oc.RULE)
            rows.append({"step": step.step, "verdict": v["verdict"], "admissible": v.get("admissible"),
                         "level": v.get("level"), "arguments": v.get("arguments"),
                         "fresh": v.get("fresh"), "state": state_by_step.get(step.step, [])})
        return rows
    finally:
        c4.build_hypotheses = original


def main():
    run, doctrine, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    from semabi.eval.v4_identity_ties import retro_decision_shared
    links = json.loads(doctrine.read_text())["link_decisions"]
    templates = sorted({l["unit"] for l in links})
    # doctrine json truncates unit names at 70 chars; recover full templates from the builder
    from semabi.compiler.compile_v4 import build_hypotheses
    from semabi.compiler.evidence import EvidenceLog
    H, _ = build_hypotheses(run, EvidenceLog(run))
    full = {u.template for u in H.units.values()}
    templates = [next((f for f in full if f.startswith(t[:60])), t) for t in templates]
    reading = settled_reading(run)
    base_rows = rows_under(run, set(), reading)
    verdicts = []
    for t in templates:
        flipped = rows_under(run, {t}, reading)
        d = retro_decision_shared(base_rows, flipped)
        verdicts.append({"template": t[:80], "link_vs_union": d["outcome"],
                         "refuted": {"left": "link", "right": "union"}.get(d.get("refuted")),
                         "counts": d["counts"], "unshared": d["unshared"]})
        print(f"  {t[:60]:60s} -> {d['outcome']} refuted={verdicts[-1]['refuted']} counts={d['counts']}")
    out.write_text(json.dumps({"run": run.name, "links": verdicts}, indent=1, default=str))


if __name__ == "__main__":
    main()
