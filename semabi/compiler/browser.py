"""Playwright wrapper exposing only primitive actions and restricted observations.

The compiler sees: roles, accessible names/text, input values, checked state,
select options, placeholders, bounding boxes, and tree structure. It does not
see ids, classes, data attributes, network traffic, or JS state.
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import sync_playwright

from semabi.compiler.observation import Node, Observation

SNAPSHOT_JS = r"""
() => {
  const roleOf = (e) => {
    const r = e.getAttribute('role'); if (r) return r;
    const t = e.tagName.toLowerCase();
    if (t === 'button') return 'button';
    if (t === 'a') return 'link';
    if (t === 'input') { const ty = (e.getAttribute('type')||'text').toLowerCase(); if (ty==='checkbox') return 'checkbox'; if (ty==='radio') return 'radio'; return 'textbox'; }
    if (t === 'textarea') return 'textbox';
    if (t === 'select') return 'combobox';
    if (/^h[1-6]$/.test(t)) return 'heading';
    if (t === 'li') return 'listitem'; if (t === 'ul' || t === 'ol') return 'list';
    if (t === 'table') return 'table'; if (t === 'tr') return 'row'; if (t === 'td' || t === 'th') return 'cell';
    if (t === 'thead' || t === 'tbody' || t === 'tfoot') return 'rowgroup';
    if (['p','span','em','strong','b','i','label','small','code'].includes(t)) return 'text';
    return 'group';
  };
  const visible = (e) => { const cs = getComputedStyle(e); if (cs.display==='none'||cs.visibility==='hidden') return false; const r=e.getBoundingClientRect(); return r.width>0||r.height>0||e.childElementCount>0; };
  const ownText = (e) => { let s=''; for (const c of e.childNodes) if (c.nodeType===3) s+=c.textContent; return s.replace(/\s+/g,' ').trim(); };
  const nodes = []; const handles = [];
  const walk = (e, parent) => {
    if (['script','style','option','title','head'].includes(e.tagName.toLowerCase())) return;
    if (!visible(e)) return;
    const role = roleOf(e);
    const t = e.tagName.toLowerCase();
    let name = '';
    if (['button','link','heading','text','listitem','cell','alert'].includes(role) && e.childElementCount===0) name = (e.textContent||'').replace(/\s+/g,' ').trim();
    else name = ownText(e);
    if (e.getAttribute('aria-label')) name = e.getAttribute('aria-label');
    const n = { i: nodes.length, parent, role, name };
    const r = e.getBoundingClientRect(); n.bbox = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
    if (t === 'input' || t === 'textarea') { if (role==='checkbox'||role==='radio') n.checked = !!e.checked; else n.value = e.value; if (e.placeholder) n.placeholder = e.placeholder; }
    if (t === 'select') { n.options = Array.from(e.options).map(o=>o.textContent.trim()); n.value = e.selectedIndex>=0 ? e.options[e.selectedIndex].textContent.trim() : ''; }
    if (e.getAttribute('aria-current')) n.current = true;
    if (role==='group' && !name && e.childElementCount===0) return;
    nodes.push(n); handles.push(e);
    const idx = n.i;
    for (const c of e.children) walk(c, idx);
  };
  walk(document.body, -1);
  window.__semabi_nodes = handles;
  return nodes;
}
"""


@dataclass
class ActionResult:
    ok: bool
    error: str | None = None


@dataclass
class Primitive:
    kind: str  # click | type | press | select | reload | reset | noop
    target: int | None = None
    text: str | None = None
    # a descriptor of the target node at the time of the action, for logs
    target_desc: dict | None = None

    def to_json(self) -> dict:
        d = {"kind": self.kind}
        if self.target is not None:
            d["target"] = self.target
        if self.text is not None:
            d["text"] = self.text
        if self.target_desc is not None:
            d["target_desc"] = self.target_desc
        return d

    def __str__(self) -> str:
        td = self.target_desc or {}
        t = f"{td.get('role','?')}:{td.get('name','')!r}" if td else (str(self.target) if self.target is not None else "")
        if self.kind in ("type", "select"):
            return f"{self.kind}({t}, {self.text!r})"
        if self.kind == "press":
            return f"press({self.text!r})"
        return f"{self.kind}({t})" if t else f"{self.kind}()"


class Browser:
    """Primitive interface. `hooks` (evaluator-side) may be attached to observe
    step boundaries; the compiler never reads from them."""

    def __init__(self, url: str, reset_url: str, headless: bool = True, settle_ms: int = 40, max_settle_ms: int = 3000):
        self.url = url
        self.reset_url = reset_url
        self.settle_ms = settle_ms
        self.max_settle_ms = max_settle_ms
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=headless)
        self._page = self._browser.new_page(viewport={"width": 1400, "height": 1000})
        self.n_primitives = 0
        self.n_resets = 0
        self.episode = 0
        self.step_hooks: list = []
        self._last_obs: Observation | None = None

    def close(self):
        try:
            self._browser.close()
        finally:
            self._pw.stop()

    # -------------------------------------------------------------- observe
    def _raw_snapshot(self) -> Observation:
        raw = self._page.evaluate(SNAPSHOT_JS)
        nodes = [Node(d["i"], d["parent"], d["role"], d["name"], d.get("value"), d.get("checked"),
                      d.get("options"), d.get("placeholder"), d.get("current"), tuple(d["bbox"])) for d in raw]
        return Observation(nodes, self._page.url)

    def observe(self) -> Observation:
        """Snapshot after the page has settled (two identical consecutive snapshots)."""
        t0 = time.time()
        prev = self._raw_snapshot()
        while True:
            time.sleep(self.settle_ms / 1000)
            cur = self._raw_snapshot()
            if cur.structural_signature() == prev.structural_signature():
                break
            prev = cur
            if (time.time() - t0) * 1000 > self.max_settle_ms:
                break
        self._last_obs = cur
        return cur

    # -------------------------------------------------------------- act
    def _handle(self, i: int):
        h = self._page.evaluate_handle("(i) => window.__semabi_nodes[i]", i)
        el = h.as_element()
        if el is None:
            raise RuntimeError(f"node {i} is not an element")
        return el

    def act(self, p: Primitive) -> ActionResult:
        """Execute a primitive against the last observed snapshot indices."""
        if p.target is not None and self._last_obs is not None and p.target < len(self._last_obs.nodes):
            n = self._last_obs.nodes[p.target]
            p.target_desc = {"role": n.role, "name": n.name, "placeholder": n.placeholder}
        res = ActionResult(True)
        try:
            if p.kind == "click":
                self._handle(p.target).click(timeout=2000)
            elif p.kind == "type":
                el = self._handle(p.target)
                el.fill(p.text or "", timeout=2000)
            elif p.kind == "press":
                self._page.keyboard.press(p.text or "Enter")
            elif p.kind == "select":
                self._handle(p.target).select_option(label=p.text, timeout=2000)
            elif p.kind == "reload":
                self._page.reload(wait_until="networkidle")
            elif p.kind == "reset":
                self._do_reset(int(p.text) if p.text else 0)
            elif p.kind == "noop":
                pass
            else:
                raise ValueError(p.kind)
        except Exception as e:  # noqa: BLE001 - surfaced as failed primitive
            res = ActionResult(False, f"{type(e).__name__}: {str(e).splitlines()[0][:200]}")
        if p.kind != "reset":
            self.n_primitives += 1
        for h in self.step_hooks:
            h(self, p, res)
        return res

    def _do_reset(self, seed: int):
        req = urllib.request.Request(self.reset_url, data=json.dumps({"seed": seed}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5).read()
        self.n_resets += 1
        self.episode += 1
        self._page.goto(self.url, wait_until="networkidle")

    def reset(self, seed: int = 0) -> Observation:
        self.act(Primitive("reset", text=str(seed)))
        return self.observe()

    def goto(self):
        self._page.goto(self.url, wait_until="networkidle")
