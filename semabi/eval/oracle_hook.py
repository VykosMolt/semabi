"""Evaluator-side recorder for the oracle ladder.

After every primitive it snapshots the settled page the same way the compiler
does and records, per observation node, the hidden entity id that the
instrumented app (experiments/oracle_apps) annotates on the nearest ancestor
(`data-eid`), the referenced entities (`data-erefs`) and, for comboboxes, the
entity id of every option (`data-oid`). It also records the hidden state, so
one record per hook call carries everything the oracle conditions need.

Records are keyed by (primitive kind, after-signature) so that hook calls the
compiler did not log (e.g. the reset inside `view_sweep`) can be skipped when
aligning with the evidence log (see `align_records`).

The compiler never reads these files (tests/test_boundary.py)."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

ORACLE_JS = r"""
() => {
  const hs = window.__semabi_nodes || [];
  const eid = hs.map(e => { const a = e.closest('[data-eid]'); return a ? a.getAttribute('data-eid') : null; });
  const erefs = hs.map(e => { const a = e.closest('[data-erefs]'); return a ? a.getAttribute('data-erefs') : null; });
  const opts = {};
  hs.forEach((e, i) => {
    if (e.tagName && e.tagName.toLowerCase() === 'select') {
      opts[i] = Array.from(e.options).map(o => o.getAttribute('data-oid') || o.getAttribute('data-eid') || null);
    }
  });
  return {eid, erefs, opts};
}
"""


class OracleHook:
    def __init__(self, run_dir: Path, evaluator_url: str):
        self.path = Path(run_dir) / "oracle.jsonl"
        self.url = evaluator_url
        self.n = 0
        if self.path.exists():
            self.n = sum(1 for _ in self.path.open())

    def __call__(self, browser, primitive, result) -> None:
        obs = browser.observe()  # settled snapshot; refreshes window.__semabi_nodes
        # apps that re-render after an async fetch may settle later than the compiler's
        # two-snapshot criterion: wait until the signature is stable for 150 ms
        for _ in range(10):
            time.sleep(0.15)
            again = browser.observe()
            if again.structural_signature() == obs.structural_signature():
                break
            obs = again
        ann = browser._page.evaluate(ORACLE_JS)
        snap = json.loads(urllib.request.urlopen(self.url, timeout=5).read())
        rec = {"n": self.n, "kind": primitive.kind, "sig": obs.structural_signature(),
               "episode": snap["episode"], "state": snap["state"], "log_len": len(snap["log"]),
               "last_op": snap["log"][-1] if snap["log"] else None, "log": snap["log"],
               "eid": ann["eid"], "erefs": ann["erefs"], "opts": {int(k): v for k, v in ann["opts"].items()}}
        assert len(rec["eid"]) == len(obs.nodes), (len(rec["eid"]), len(obs.nodes))
        with self.path.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        self.n += 1


def load_records(run_dir: Path) -> list[dict]:
    p = Path(run_dir) / "oracle.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def align_records(log, records: list[dict]) -> list[dict | None]:
    """One record per evidence-log step (None if missing): sequential match on
    (kind, after-signature); hook records without a logged step are skipped."""
    out: list[dict | None] = []
    j = 0
    for s in log.steps:
        hit = None
        k = j
        while k < len(records) and k < j + 3:
            r = records[k]
            if r["kind"] == s.action.kind and r["sig"] == s.after:
                hit = r
                j = k + 1
                break
            k += 1
        out.append(hit)
    return out
