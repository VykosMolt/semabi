"""Run one experiment that decides a surviving identity tie, with both readings frozen first.

A tie between two keys of a family (`semabi.eval.v4_identity_ties`) is decided by an
interaction on which the readings predict differently: make a second instance that shares
the contested value with an existing one (a *collision*), or change the contested value of
an instance (a *mutation*).  Under the reading keyed by that value the instance is one
object -- a conflict between two mentions, a replacement -- and under the other it is two.

The plan names the history the readings were fitted on, the application, the two readings
as ``family -> key`` maps, the actions to perform, and each reading's prediction, and it is
written *before* the first action.  The actions are performed on a fresh instance of the
application, appended to a copy of the history (the retained history is not touched), and
both readings are scored by the causal objective on the extended history.  What decides is
the change in the terms the experiment was about: a reading whose objects the new steps
force into a conflict, a churn or a contradiction has been refuted by the application; a
reading the new steps merely explain has survived.  Both scores are reported whatever they
say (`docs/v4_ties.md`).
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.compile_v4 import compile_v4
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import objective

TERMS = ("explained", "conflicts", "churn", "contradictions", "visibility", "spurious", "named", "positional")


def _find(obs, spec: dict) -> int | None:
    """A node by role and name (or a name prefix), optionally the n-th such."""
    role, name, nth = spec.get("role"), spec.get("name"), spec.get("nth", 0)
    hits = [n.i for n in obs.nodes
            if (role is None or n.role == role)
            and (name is None or n.name == name or (spec.get("prefix") and str(n.name or "").startswith(name)))]
    return hits[nth] if len(hits) > nth else None


def _score(run_dir: Path, identity: dict) -> objective.Behaviour:
    compiled = compile_v4(run_dir, min_support=2, write_diagnostics=False, identity=identity)
    return objective.evaluate(compiled.abstractor, compiled.log)


def run(plan: dict, workdir: Path) -> dict:
    source = Path(plan["run"])
    if workdir.exists():
        shutil.rmtree(workdir)
    shutil.copytree(source, workdir)
    readings = plan["readings"]                  # name -> {family: key_slot}
    report = {"plan": plan, "before": {}, "after": {}, "delta": {}, "steps": []}
    for name, identity in readings.items():
        report["before"][name] = _score(workdir, identity).to_json()
    log = EvidenceLog(workdir)
    browser = Browser(plan["base"].rstrip("/") + "/", plan["base"].rstrip("/") + "/reset")
    try:
        browser.goto()
        browser.reset(int(plan.get("seed", 4247)))
        browser.act(Primitive("reload"))
        obs = browser.observe()
        log.add_observation(obs)
        episode = browser.episode
        for action in plan["actions"]:
            target = _find(obs, action["target"]) if "target" in action else None
            if "target" in action and target is None:
                report["outcome"] = f"TARGET_NOT_FOUND: {action['target']}"
                return report
            text = action.get("text")
            if "option" in action and target is not None:
                # the k-th option of a select, resolved on the live page rather than spelled
                # in the plan: what matters is which choice, not the label's exact text
                options = list(obs.node(target).options or [])
                text = options[action["option"]] if action["option"] < len(options) else None
                if text is None:
                    report["outcome"] = f"OPTION_NOT_FOUND: {action}"
                    return report
            primitive = Primitive(action["kind"], target=target, text=text)
            res = browser.act(primitive)
            after = browser.observe()
            log.add_observation(after)
            step = log.add_step(episode, primitive, res.ok, res.error, obs, after)
            report["steps"].append({"step": step.step, "action": action, "ok": res.ok, "error": res.error,
                                    "status": next((n.name for n in after.nodes if n.role == "status"), None)})
            obs = after
        reload = Primitive("reload")
        res = browser.act(reload)
        settled = browser.observe()
        log.add_observation(settled)
        step = log.add_step(episode, reload, res.ok, res.error, obs, settled)
        report["steps"].append({"step": step.step, "action": {"kind": "reload"}, "ok": res.ok,
                                "survived_reload": obs.structural_signature() == settled.structural_signature()})
    finally:
        browser.close()
    return verdict(plan, workdir, report)


# what each kind of experiment is about: the terms in which its readings' predictions differ
DECISIVE = {"collision": ("positional", "conflicts"), "mutation": ("churn", "contradictions")}


def verdict(plan: dict, workdir: Path, report: dict) -> dict:
    """Score both readings on the extended history and decide on the experiment's own terms.

    An experiment is about one difference between two readings -- a collision shows as a
    key that has to fall back on position or as two mentions in conflict, a mutation as a
    churn or a contradiction -- and only that difference is evidence between them.  A change
    both readings suffer alike (the reload, a count that moved) says nothing about which is
    right, and counting it once made every experiment refute both sides."""
    readings = plan["readings"]
    kind = plan.get("test", "collision")
    terms = DECISIVE.get(kind, DECISIVE["collision"])
    for name, identity in readings.items():
        after_score = _score(workdir, identity)
        report["after"][name] = after_score.to_json()
        before = report["before"][name]
        report["delta"][name] = {t: after_score.to_json().get(t, 0) - before.get(t, 0) for t in TERMS}
    harm = {name: sum(d[t] for t in terms) for name, d in report["delta"].items()}
    report["decisive_terms"] = list(terms)
    report["harm"] = harm
    least = min(harm.values())
    survivors = [name for name, h in harm.items() if h == least]
    refuted = [name for name, h in harm.items() if h > least]
    if refuted:
        report["outcome"] = "DECIDED"
        report["refuted"], report["survivors"] = refuted, survivors
    elif least > 0:
        report["outcome"] = "BOTH_HURT_ALIKE"
        report["survivors"] = survivors
    else:
        report["outcome"] = "UNDECIDED"
        report["survivors"] = survivors
    return report


def rescore(plan: dict, workdir: Path) -> dict:
    """The verdict on an experiment already performed: the extended history in `workdir`
    against the untouched history, without touching the application again."""
    source = Path(plan["run"])
    report = {"plan": plan, "before": {}, "after": {}, "delta": {}, "steps": [], "rescored": True}
    for name, identity in plan["readings"].items():
        report["before"][name] = _score(source, identity).to_json()
    return verdict(plan, workdir, report)


def propagate(result: dict, run_dir: Path | None = None) -> list[dict]:
    """Feed a decided experiment back to the SOURCE history as retained refutations.

    The search reads `identity_refutations_v4.json` beside a history and does not consider
    a refuted key for that family again (`semabi.compiler.v4.search.read_refutations`), and
    the freeze refuses a candidate that activates one.  A reading the experiment refuted is
    written there for every family the plan keyed by it, with the experiment as provenance
    -- which history, which actions, which terms decided -- so that the SOURCE learner's next
    manifest carries what the application said, and nothing from the transfer histories."""
    from semabi.compiler.v4 import search as v4_search

    plan = result["plan"]
    run_dir = Path(run_dir or plan["run"])
    tie = plan["tie"]
    families = tie.get("families") or [tie["family"]]
    written = []
    if result.get("outcome") != "DECIDED":
        return written
    for name in result.get("refuted", []):
        reading = plan["readings"][name]
        for family in families:
            key = reading.get(family)
            why = (f"refuted by an executed experiment ({plan.get('name', 'tie experiment')}): "
                   f"harm {result['harm'][name]} on {result['decisive_terms']} against "
                   f"{min(result['harm'].values())} for {', '.join(result['survivors'])}")
            evidence = {"experiment": plan.get("name"), "actions": plan["actions"],
                        "delta": result["delta"][name], "decisive_terms": result["decisive_terms"],
                        "predicted": plan.get("predictions", {}).get(name)}
            v4_search.write_refutation(run_dir, family, key, why, evidence)
            written.append({"family": family, "key_slot": key})
    return written


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, help="JSON: run, base, readings, actions, predictions")
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rescore", action="store_true",
                    help="decide an experiment already performed in --workdir; no new steps")
    ap.add_argument("--propagate", action="store_true",
                    help="write the decided result at --out back to the SOURCE history as refutations")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    if a.propagate:
        result = json.loads(Path(a.out).read_text())
        written = propagate(result)
        print(json.dumps({"propagated": written, "to": plan["run"]}, indent=1))
        return 0
    if not a.workdir:
        ap.error("--workdir is required unless --propagate")
    report = rescore(plan, Path(a.workdir)) if a.rescore else run(plan, Path(a.workdir))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=1, default=str))
    print(json.dumps({"outcome": report.get("outcome"), "harm": report.get("harm"),
                      "survivors": report.get("survivors"), "delta": report.get("delta"),
                      "steps": [(s["step"], s.get("status")) for s in report["steps"]]}, indent=1)[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
