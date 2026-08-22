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
from semabi.compiler.schema_llm import propose


def compile_v1(run_dir: Path, min_support: int = 1, model: str = "opus", reuse_schema: bool = True) -> Compiled:
    run_dir = Path(run_dir)
    log = EvidenceLog(run_dir)
    cat = Catalog()
    cat.fit_log(log)
    sp = run_dir / "schema.json"
    if reuse_schema and sp.exists():
        schema = json.loads(sp.read_text())
    else:
        schema, cat = propose(run_dir, model=model)
    G = SchemaGrounder(cat, schema)
    G.fit(log)
    I = Inducer(G, log)
    I.run()
    M = build_model(G, I.operators, min_support=min_support, view_ops=I.view_ops)
    # readable type names in the exported model
    M.meta = {"v1": True, "types": {f"T{t}": n for n, t in G.tid_of.items()}, "n_steps": len(log.steps),
              "n_transitions": len(I.transitions), "n_operators": len(I.operators)}
    M.save(run_dir / "model_v1.json")
    (run_dir / "model_v1.txt").write_text(str(M) + "\n\n" + I.report())
    return Compiled(log, cat.parser, G, I, M)
