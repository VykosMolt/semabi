"""V1 compile: catalog -> (cached) LLM schema -> grounder -> V0 inducer/model."""
from __future__ import annotations

import json
from pathlib import Path

from semabi.compiler.compile import Compiled
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.grounder import SchemaGrounder
from semabi.compiler.induce import Inducer
from semabi.compiler.mentions import Catalog
from semabi.compiler.model import build_model
from semabi.compiler.schema_llm import propose, propose_candidates


def coherence(I: Inducer) -> float:
    """Retrospective coherence of a grounding: supported operators with few parameters are
    good; domain changes attributed to view switches/reloads and one-off transitions are bad."""
    good = sum(min(op.support, 6) / (1 + max(0, len(op.params) - 2)) for op in I.operators if op.support >= 2)
    singles = sum(1 for op in I.operators if op.support == 1)
    return good - 0.3 * singles - 0.2 * I.reattributed


def compile_v1(run_dir: Path, min_support: int = 1, model: str = "opus", reuse_schema: bool = True) -> Compiled:
    run_dir = Path(run_dir)
    log = EvidenceLog(run_dir)
    cat = Catalog()
    cat.fit_log(log)
    sp = run_dir / "schema.json"
    if reuse_schema and sp.exists():
        schema = json.loads(sp.read_text())
        G = SchemaGrounder(cat, schema)
        G.fit(log)
        I = Inducer(G, log)
        I.run()
    else:
        best = None
        for cand in propose_candidates(run_dir, model=model, k=2):
            Gc = SchemaGrounder(cat, cand)
            Gc.fit(log)
            Ic = Inducer(Gc, log)
            Ic.run()
            score = coherence(Ic)
            (run_dir / "schema_candidates.log").open("a").write(json.dumps({"score": score, "types": [t["name"] for t in cand.get("types", [])]}) + "\n")
            if best is None or score > best[0]:
                best = (score, cand, Gc, Ic)
        score, schema, G, I = best
        sp.write_text(json.dumps(schema, indent=1))
    M = build_model(G, I.operators, min_support=min_support, view_ops=I.view_ops)
    # readable type names in the exported model
    M.meta = {"v1": True, "types": {f"T{t}": n for n, t in G.tid_of.items()}, "n_steps": len(log.steps),
              "n_transitions": len(I.transitions), "n_operators": len(I.operators)}
    M.save(run_dir / "model_v1.json")
    (run_dir / "model_v1.txt").write_text(str(M) + "\n\n" + I.report())
    return Compiled(log, cat.parser, G, I, M)
