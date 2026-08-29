"""Persistence probes for the controls the explorer never probed: click, reload, look.

The inducer treats a click as a domain action unless an executed probe has certified it as
sensing -- interface state that does not survive a reload -- and heuristics may not certify
it, because consistency under a collapsed abstraction once hid real domain actions.  That
policy is right, and it leaves a control whose status was never probed in the domain.  Vet's
navigation tabs (`Clients`, `Appointments`, `Vets`) and cellar's (`Cellar`, `Lots`, `Intake`)
were clicked hundreds of times in their traces and never followed by a reload, so their
status was unknown, and every object type rendered per view acquired create and delete
effects on navigation: an operator of support 68 that "deletes three cells" when `Vets` is
pressed, fifty-three contradictions in vet's durable ledger, and seventy actions the clean
reading could not bind (`docs/v4_frontier.md`).

This runs the explorer's own probe for named buttons on a fresh instance of the application:
click the button from a view other than its own, reload, and compare what the reload shows
with what the previous reload showed.  The same page means nothing persisted -- the click
was interface state, `VIEW`; a different page means something did, `DOMAIN`; a click that
changed no view is `UNDETERMINED`.  The records go to ``probes.acquired.jsonl`` beside the
run's own ``probes.jsonl``, labelled, so that the retained evidence stays as recorded and
`V2Abstractor.fit_view_controls` reads both.  A probe is a fact about a control, not about
any state of the history, and it is the same kind of evidence the explorer's probes are.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.v2.score import _same_view


def probe(base: str, seed: int, names: list[str], *, attempts: int = 3) -> list[dict]:
    browser = Browser(base + "/", base + "/reset")
    records: list[dict] = []
    try:
        browser.goto()
        browser.reset(seed)
        browser.act(Primitive("reload"))
        default_view = browser.observe()      # what a reload shows
        for name in names:
            for attempt in range(attempts):
                browser.act(Primitive("reload"))
                before = browser.observe()
                # from a view other than the button's own: from its own view a tab changes
                # nothing, which is not evidence either way
                others = [n.i for n in before.nodes
                          if n.role == "button" and n.name in names and n.name != name]
                if others:
                    browser.act(Primitive("click", target=others[attempt % len(others)]))
                    before = browser.observe()
                node = next((n for n in before.nodes
                             if n.role == "button" and (n.name or "") == name), None)
                if node is None:
                    continue
                browser.act(Primitive("click", target=node.i))
                after = browser.observe()
                browser.act(Primitive("reload"))
                back = browser.observe()
                changed = not _same_view(before, after)
                persisted = back.structural_signature() != default_view.structural_signature()
                status = "UNDETERMINED" if not changed else "DOMAIN" if persisted else "VIEW"
                records.append({"key": ["click", "button", name, None], "status": status,
                                "mixed": [], "persisted_default": persisted,
                                "changed_views": [name] if changed else [],
                                "acquired": True, "probe": "navigation reload persistence",
                                "seed": seed})
                break
    finally:
        browser.close()
    return records


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True, help="http://127.0.0.1:PORT")
    ap.add_argument("--seed", type=int, required=True, help="a seed no retained trace used")
    ap.add_argument("--buttons", required=True, help="comma-separated rendered names")
    ap.add_argument("--out", required=True, help="the run's probes.acquired.jsonl")
    a = ap.parse_args(argv)
    records = probe(a.base, a.seed, a.buttons.split(","))
    for r in records:
        print(f"  {r['key'][2]:20} {r['status']}")
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in records))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
