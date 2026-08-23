"""Execute one discriminating probe and let behaviour decide between two identity readings.

Compiler side: it reads rendered evidence and drives the browser, and never reads hidden
state.  The loop is the whole point of V4 -- an undecided reading of what the objects are
becomes an experiment, the experiment becomes evidence, and the evidence decides -- so the
before and after scores of *both* readings are recorded whatever they turn out to be.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.compile_v4 import build_hypotheses, compile_v4
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.v4 import objective, probe as probe_mod, search as v4_search


def _score(run_dir: Path, identity: dict[str, str | None] | None, max_steps: int | None):
    compiled = compile_v4(run_dir, min_support=2, write_diagnostics=False, identity=identity)
    return objective.evaluate(compiled.abstractor, compiled.log, max_steps), compiled


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-probes", type=int, default=2)
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--output", required=True)
    a = ap.parse_args()
    run_dir = Path(a.run)
    log = EvidenceLog(run_dir)
    H, G = build_hypotheses(run_dir, log)
    result = v4_search.search(H, G, log, max_steps=a.max_steps)
    report: dict = {"run": str(run_dir), "open_questions": [q.to_json() for q in result.open_questions],
                    "probes": [], "primitives_spent": 0}

    if not result.open_questions:
        report["outcome"] = "NOTHING_UNDECIDED"
        Path(a.output).write_text(json.dumps(report, indent=1))
        print(json.dumps(report, indent=1)[:1500])
        return

    browser = Browser(a.base.rstrip("/") + "/", a.base.rstrip("/") + "/reset")
    spent_before = browser.n_primitives
    try:
        for question in result.open_questions[:a.max_probes]:
            plan = probe_mod.derive(question, H, G, log.typed_tokens)
            entry: dict = {"question": question.to_json(),
                           "probe": plan.to_json() if plan else None}
            if plan is None:
                entry["outcome"] = "NO_EXECUTABLE_PROBE"
                report["probes"].append(entry)
                continue

            # both readings, scored on the trace as it stands
            def identity_for(reading):
                chosen = {t: r.key_slot for t, r in result.chosen.items()}
                for template in result.families.get(question.template, []):
                    chosen[template] = reading.key_slot
                return chosen

            left_before, _ = _score(run_dir, identity_for(question.left), a.max_steps)
            right_before, _ = _score(run_dir, identity_for(question.right), a.max_steps)

            # reach a situation in which the contested control is rendered
            browser.reset(a.seed)
            before = browser.observe()
            here = probe_mod.locate(question, H, G, before, before.structural_signature(),
                                    log.typed_tokens)
            visited: set[str] = set()
            for _ in range(12):
                if here is not None:
                    break
                visited.add(before.structural_signature())
                targets = [n for n in before.nodes if n.role in ("button", "link")]
                if not targets:
                    break
                nxt = next((n for n in targets if n.i not in visited), targets[0])
                browser.act(Primitive("click", target=nxt.i))
                before = browser.observe()
                here = probe_mod.locate(question, H, G, before, before.structural_signature(),
                                        log.typed_tokens)
            entry["reached_observation"] = here is not None
            if here is None:
                entry["outcome"] = "OBSERVATION_NOT_REACHED"
                report["probes"].append(entry)
                continue
            plan = here
            entry["probe"] = plan.to_json()

            log.add_observation(before)
            primitive = Primitive(plan.kind, target=plan.node, text=plan.text)
            res = browser.act(primitive)
            after = browser.observe()
            log.add_step(browser.episode, primitive, res.ok, res.error, before, after)
            # and then ask the application whether what just changed was a fact about the
            # world or about the screen: a reload keeps the one and forgets the other.  Two
            # primitives, and the second is the one that decides.
            reload_primitive = Primitive("reload")
            reload_res = browser.act(reload_primitive)
            settled = browser.observe()
            log.add_step(browser.episode, reload_primitive, reload_res.ok, reload_res.error, after, settled)
            entry["executed"] = {"ok": res.ok, "error": res.error,
                                 "page_changed": before.structural_signature() != after.structural_signature(),
                                 "survived_reload": after.structural_signature() == settled.structural_signature()}

            log2 = EvidenceLog(run_dir)
            left_after, _ = _score(run_dir, identity_for(question.left), a.max_steps)
            right_after, _ = _score(run_dir, identity_for(question.right), a.max_steps)
            entry["scores"] = {
                "left": {"key_slot": question.left.key_slot, "before": left_before.to_json(),
                         "after": left_after.to_json()},
                "right": {"key_slot": question.right.key_slot, "before": right_before.to_json(),
                          "after": right_after.to_json()},
            }
            # a probe is an experiment about one prediction, so it is settled on its own
            # evidence: whichever reading the two new steps newly contradict is the one the
            # application has just refuted.  Global dominance is the wrong question here --
            # two readings can stay Pareto-incomparable over a whole trace while one of them
            # has just been shown to claim a domain fact that a reload forgot.
            def hurt(before_score, after_score) -> dict:
                return {"contradictions": after_score.contradictions - before_score.contradictions,
                        "churn": after_score.churn - before_score.churn,
                        "visibility": after_score.visibility - before_score.visibility,
                        "explained": after_score.explained - before_score.explained}

            left_delta, right_delta = hurt(left_before, left_after), hurt(right_before, right_after)
            entry["probe_evidence"] = {"left": left_delta, "right": right_delta}
            left_refuted = left_delta["contradictions"] > 0 or left_delta["churn"] > 0
            right_refuted = right_delta["contradictions"] > 0 or right_delta["churn"] > 0
            if left_refuted and not right_refuted:
                entry["outcome"] = "RIGHT_SURVIVES"
                entry["eliminated"] = question.left.key_slot
                entry["why"] = ("the probe made the chosen reading claim a domain change that "
                                "the reload did not keep")
                v4_search.write_refutation(run_dir, question.template, question.left.key_slot,
                                           entry["why"], left_delta)
            elif right_refuted and not left_refuted:
                entry["outcome"] = "LEFT_SURVIVES"
                entry["eliminated"] = question.right.key_slot
                entry["why"] = ("the probe made the alternative reading claim a domain change "
                                "that the reload did not keep")
                v4_search.write_refutation(run_dir, question.template, question.right.key_slot,
                                           entry["why"], right_delta)
            elif left_after.better_than(right_after):
                entry["outcome"] = "LEFT_SURVIVES"
                entry["eliminated"] = question.right.key_slot
            elif right_after.better_than(left_after):
                entry["outcome"] = "RIGHT_SURVIVES"
                entry["eliminated"] = question.left.key_slot
            else:
                entry["outcome"] = "STILL_UNDECIDED"
            entry["steps_now"] = len(log2.steps)
            report["probes"].append(entry)
    finally:
        report["primitives_spent"] = browser.n_primitives - spent_before
        browser.close()

    outcomes = [p.get("outcome") for p in report["probes"]]
    report["outcome"] = ("RESOLVED" if any(o in ("LEFT_SURVIVES", "RIGHT_SURVIVES") for o in outcomes)
                         else "UNRESOLVED")
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(report, indent=1))
    print(json.dumps({"outcome": report["outcome"], "primitives": report["primitives_spent"],
                      "probes": [{k: p.get(k) for k in ("outcome", "eliminated")} for p in report["probes"]]},
                     indent=1))


if __name__ == "__main__":
    main()
