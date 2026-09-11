"""Run the identity search on a history and print families, moves and open questions."""
import json, os, sys
from pathlib import Path
sys.path.insert(0, os.environ.get("SEMABI_ROOT", "/home/moloch/semabi"))
from semabi.compiler.compile_v4 import build_hypotheses
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import search as s4
run = Path(sys.argv[1]); needle = sys.argv[2] if len(sys.argv) > 2 else ""
log = EvidenceLog(run); H, G = build_hypotheses(run, log)
result = s4.search(H, G, log, run_dir=run, log_fn=lambda m: None)
print("== families")
for name, ts in result.families.items():
    print(f"  {name[:60]}  <- {len(ts)} templates; chosen={result.chosen[ts[0]].key_slot!r} {result.chosen[ts[0]].status}")
print("== moves")
for m in result.moves:
    if needle and needle not in m.get("family", ""):
        continue
    sc = m.get("score", {})
    print(f"  r{m.get('round')} {m['move']:9s} {m.get('family','')[:40]:40s} key={m.get('key_slot')!r:14s} against={m.get('against')!r:12s} by={m.get('decided_by')}  "
          f"expl={sc.get('explained')} unex={sc.get('unexplained')} atoms={sc.get('delta_atoms')} err={sum(sc.get(k,0) for k in ('churn','spurious','visibility','contradictions','conflicts','positional'))} cx={sc.get('complexity')}")
print("== open questions")
for q in result.open_questions:
    print("  ", q.template[:60], "|", q.left.key_slot, "vs", q.right.key_slot, "|", q.reason)
