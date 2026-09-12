"""P43: fall-seeking acquisition on a live fixture.

A clock the learner can set is a clock it can test.  Where the fitted field theory calls a
field a clock (it only ever rose in the history) and the page in view carries that field
in a textbox, the driver types a value below the current one -- the smallest value the
history witnessed for the field -- so that the history holds a fall.  Everywhere else the
T1 untargeted Explorer chooses, exactly as in the control arms; refits on the T1 schedule.

Usage: p43_acquire_falls.py --url U --reset-url R --initial DIR --out DIR --seed N [--budget 60]
"""
import argparse, hashlib, json, shutil, subprocess, sys, traceback
from pathlib import Path

ROOT = Path("/home/moloch/semabi")
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.explorer import Explorer, affordance_key
from semabi.compiler.v4 import consequence as csq
from semabi.compiler.v4.fields import numeric
import transport_collect as tc

EDITABLE = ("textbox",)


def theory(model) -> dict:
    for got in model.outcomes.values():
        ft = getattr(got, "field_theory", None)
        if ft:
            return ft
    return {}


def seek_fall(model, obs, asked: set):
    """A type primitive that lowers a clock field in view, with its record, or None."""
    ft = theory(model)
    A = model.abstractor
    if not ft.get("clocks"):
        return None
    sig = A.ensure(obs)
    instances = A.H.parse_units(sig)
    for tid, slot in ft["clocks"]:
        et = A.H.entity_types.get(tid)
        if et is None:
            continue
        slot_id = slot[len("attr:"):] if slot.startswith("attr:") else slot
        witnessed = [numeric(v) for v in ft.get("candidates", {}).get(tid, {}).get(slot, [])]
        witnessed = [v for v in witnessed if v is not None]
        for inst in instances:
            if inst.template not in et.units:
                continue
            node_index = inst.slot_nodes.get(slot_id)
            if node_index is None or node_index >= len(obs.nodes):
                continue
            node = obs.node(node_index)
            for cand in [node] + [obs.node(c) for c in obs.children(node_index)]:
                if cand.role not in EDITABLE:
                    continue
                current = numeric(cand.value)
                if current is None:
                    continue
                lower = [v for v in witnessed if v < current]
                if not lower:
                    continue
                value = min(lower)
                text = str(int(value)) if value == int(value) else str(value)
                key = (tid, slot, cand.value)
                if key in asked:
                    continue
                asked.add(key)
                return Primitive("type", cand.i, text), {
                    "reason": "fall_seeking", "field": [tid, slot], "template": inst.template,
                    "current": cand.value, "typed": text, "clocks": ft["clocks"]}
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True); ap.add_argument("--reset-url", required=True)
    ap.add_argument("--initial", type=Path, required=True); ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, required=True); ap.add_argument("--budget", type=int, default=60)
    args = ap.parse_args()
    if args.out.exists():
        ap.error("Output already exists; choose a new run identity")
    args.out.mkdir(parents=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--", "semabi"], cwd=ROOT, text=True).strip()
    record = {"start": tc.stamp(), "policy": "falls", "seed": args.seed, "budget": args.budget,
              "source_head": head, "source_dirty": bool(dirty),
              "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "initial_sha256": {n: tc.digest(args.initial / n) for n in ("observations.jsonl", "steps.jsonl")},
              "status": "RUNNING"}
    tc.write(args.out / "run.json", record)
    for name in ("observations.jsonl", "steps.jsonl"):
        shutil.copyfile(args.initial / name, args.out / name)
    log = EvidenceLog(args.out)
    browser = Browser(args.url, args.reset_url)
    browser.episode = max((step.episode for step in log.steps), default=0)
    explorer = Explorer(browser, log, seed=args.seed)
    rec = tc.Recorder(browser, log, args.out / "decisions.jsonl")
    refits, asked, falls = [], set(), 0

    def refit():
        entry = {"after_charged_attempts": rec.attempts, "training_steps": len(log.steps)}
        try:
            fitted = csq.fit(args.out, None, at=len(log.steps))
            entry.update(status="FITTED", clocks=theory(fitted).get("clocks", []),
                         adopted_pairs=theory(fitted).get("adopted_pairs", []))
        except Exception as error:
            fitted = None
            entry.update(status="RUNTIME_FAILURE", error=f"{type(error).__name__}: {error}",
                         traceback=traceback.format_exc())
        refits.append(entry)
        tc.write(args.out / "refits.json", refits)
        return fitted

    model = refit()
    try:
        obs = rec.act(None, Primitive("reset", text=str(args.seed)),
                      {"reason": "acquisition_setup_reset", "policy": "falls", "pre_state_unobserved": True})
        obs = rec.act(obs, Primitive("reload"), {"reason": "observed_session_boundary", "policy": "falls"})
        while rec.attempts < args.budget:
            if rec.attempts % 15 == 0 and rec.attempts:
                model = refit()
            chosen = seek_fall(model, obs, asked) if model is not None else None
            if chosen is not None:
                primitive, decision = chosen
                falls += 1
            else:
                primitive, decision = explorer.choose(obs), {"reason": "untargeted_explorer"}
            affinity = affordance_key(obs, primitive)
            obs = rec.act(obs, primitive, {"policy": "falls", **decision})
            explorer.counts[affinity] += 1
            explorer.last_typed_target = primitive.target if primitive.kind == "type" else None
        record.update(rec.summary(), refits=refits, fall_attempts=falls, status="FINISHED",
                      complete=rec.attempts == args.budget)
    except BaseException as error:
        record.update(status="ERROR", error=f"{type(error).__name__}: {error}", traceback=traceback.format_exc())
        raise
    finally:
        browser.close()
        record["end"] = tc.stamp()
        record["raw_hashes"] = {p.name: tc.digest(p) for p in args.out.iterdir()
                                if p.name in ("observations.jsonl", "steps.jsonl", "decisions.jsonl")}
        tc.write(args.out / "run.json", record)
        print(json.dumps({k: record.get(k) for k in ("status", "charged_attempts", "failed_attempts", "fall_attempts", "end")}))


if __name__ == "__main__":
    main()
