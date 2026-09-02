"""What the current harbour compile learned for the berth allocation, and what its
refusals look like: the JOIN-shaped precondition (berth capacity vs vessel length)
that the precondition grammar cannot state."""
import json, sys
sys.path.insert(0, "/home/moloch/semabi")
from pathlib import Path
from semabi.compiler.compile_v4 import compile_v4
run = Path(sys.argv[1]); out = Path(sys.argv[2])
c = compile_v4(run, min_support=2, write_diagnostics=False)
rows = []
for op in c.inducer.operators:
    how = " ".join(str(a) for a in op.acts)
    if "Allocate berth" in how or "berth" in how.lower():
        rows.append({"name": op.name, "how": how[:160], "support": op.support,
                     "pre": [str(l) for l in getattr(op, "pre", [])][:8],
                     "effs": [str(e) for e in op.effs][:6],
                     "neg": getattr(op, "neg", None),
                     "unexplained_failures": getattr(op, "unexplained", None)})
print(json.dumps(rows, indent=1, default=str)[:3000])
print("total operators:", len(c.inducer.operators))
out.write_text(json.dumps({"berth_operators": rows, "total": len(c.inducer.operators)}, indent=1, default=str))
