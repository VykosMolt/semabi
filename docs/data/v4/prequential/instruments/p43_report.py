"""Report one P43 arm: decisions, refits, terminal field theory and the held-out verdicts."""
import json, subprocess, sys
from collections import Counter
from pathlib import Path
arm = Path(sys.argv[1]); out = Path(sys.argv[2])
I = "/home/moloch/semabi/docs/data/v4/prequential/instruments"
EV = "/home/moloch/semabi/docs/data/v4/transport/first_pass/dispatch/evaluation_v2"
run = json.loads((arm / "run.json").read_text())
print("run:", {k: run.get(k) for k in ("status", "charged_attempts", "failed_attempts", "fall_attempts", "paired_steps_recorded", "source_head", "source_dirty")})
for e in run.get("refits", []):
    print("refit @", e["after_charged_attempts"], e["status"], "clocks", e.get("clocks"), "pairs", e.get("adopted_pairs"))
seq = []
for l in (arm / "decisions.jsonl").read_text().splitlines():
    d = json.loads(l); a = d["action"]; td = a.get("target_desc") or {}
    tag = "" if d["ok"] else " FAIL"
    if d["reason"] == "fall_seeking":
        seq.append(f"FALL:type({td.get('name')} {d.get('current')!r}->{a.get('text')!r}){tag}")
    elif a["kind"] == "type":
        seq.append(f"type({a.get('text')!r}){tag}")
    elif a["kind"] == "click":
        seq.append(f"{td.get('name')}{tag}")
    else:
        seq.append(a["kind"].upper() + tag)
print("acquired:", " | ".join(seq))
env = {"PYTHONHASHSEED": "0"}
import os; env = {**os.environ, **env}
subprocess.run(["/home/moloch/semabi/.venv/bin/python", f"{I}/p42_score.py", str(arm), EV, str(out)], env=env, check=True, capture_output=True, cwd="/home/moloch/semabi")
r = json.loads(out.read_text())["results"]
for cls, row in r["emission"].items():
    s = row.get("summary", {})
    print(cls, s.get("categories"), "raw", s.get("raw_verdicts"))
rows = r["emission"].get("rule", {}).get("rows") or []
print("rule per control:", dict(Counter((x.get("control"), x.get("verdict")) for x in rows)))
th = subprocess.run(["/home/moloch/semabi/.venv/bin/python", f"{I}/p42_theory.py", str(arm), "Check dispatch"], env=env, capture_output=True, text=True, cwd="/home/moloch/semabi")
print("\n".join(l[:700] for l in th.stdout.splitlines()[:6]))
