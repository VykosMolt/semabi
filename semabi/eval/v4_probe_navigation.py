"""Runs persistence probes for controls the explorer never probed: click, reload, look.

The inducer treats an unprobed click as a domain action by default, which is correct policy
but leaves navigation controls that were clicked often and never followed by a reload with
an unknown status, sometimes acquiring spurious create/delete effects.

This runs the explorer's own probe for named buttons on a fresh instance: click the button
from another view, reload, and compare with what the previous reload showed. Same page means
nothing persisted (`VIEW`); a different page means something did (`DOMAIN`); no view change
is `UNDETERMINED`. Records go to ``probes.acquired.jsonl`` beside the run's own
``probes.jsonl``, and `V2Abstractor.fit_view_controls` reads both.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.v2.score import _same_view


def probe(base: str, seed: int, names: list[str], *, attempts: int = 3,
          via: str | None = None) -> list[dict]:
    """``via`` names a button to click first, to reach a control that needs a prerequisite
    step (e.g. opening a detail panel). The verdict is still about what survives the reload,
    read against what a reload shows by default."""
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
                if via:
                    door = next((n for n in before.nodes
                                 if n.role == "button" and (n.name or "") == via), None)
                    if door is None:
                        continue
                    browser.act(Primitive("click", target=door.i))
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
                                "seed": seed, **({"via": via} if via else {})})
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
    ap.add_argument("--via", default=None, help="a button to click first, from the reloaded page")
    a = ap.parse_args(argv)
    records = probe(a.base, a.seed, a.buttons.split(","), via=a.via)
    for r in records:
        print(f"  {r['key'][2]:20} {r['status']}")
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in records))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
