"""Compare the regenerated retained state with a committed one: frontiers, the
metamorphic invariants, and the outcome ledgers per application.

Usage: battery_compare.py <git rev>
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/moloch/semabi")
rev = sys.argv[1]


def committed(path):
    out = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{path}"], capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 else None


def current(path):
    p = ROOT / path
    return json.loads(p.read_text()) if p.exists() else None


def line(label, old, new):
    flag = "" if old == new else "   <-- CHANGED"
    print(f"  {label:44s} {str(old)[:38]:38s} -> {str(new)[:38]}{flag}")


for app in ("harbour", "vet_clinic", "blend_book"):
    o, n = committed(f"docs/data/v4/frontier_{app}.json"), current(f"docs/data/v4/frontier_{app}.json")
    print(f"frontier {app}")
    for k in ("identification", "holdout_outcome"):
        line(k, (o or {}).get(k), (n or {}).get(k))
    line("selected", ((o or {}).get("selected") or {}).get("name"), ((n or {}).get("selected") or {}).get("name"))
    line("survivor classes", ((o or {}).get("indistinguishable_classes") or {}).get("survivor_classes"),
         ((n or {}).get("indistinguishable_classes") or {}).get("survivor_classes"))
print("invariants (n_differences)")
for f in sorted((ROOT / "docs/data/v4").glob("*.json")):
    name = f.name
    if not any(name.startswith(x) for x in ("reversal_", "columns_frozen_", "renaming_", "columns_refit_")):
        continue
    o, n = committed(f"docs/data/v4/{name}"), current(f"docs/data/v4/{name}")
    line(name, (o or {}).get("n_differences"), (n or {}).get("n_differences"))
print("outcome ledgers")
for f in sorted((ROOT / "docs/data/v4").glob("outcome_*.json")):
    o, n = committed(f"docs/data/v4/{f.name}"), current(f"docs/data/v4/{f.name}")
    for src in (o, n):
        pass
    def ledger(d):
        m = (d or {}).get("outcome_model") or {}
        return m.get("ledger") or (d or {}).get("ledger")
    line(f.name, ledger(o), ledger(n))
