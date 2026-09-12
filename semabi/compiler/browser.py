"""Playwright wrapper exposing only primitive actions and restricted observations.

The compiler sees: roles, accessible names/text, input values, checked state,
select options, placeholders, bounding boxes, and tree structure. It does not
see ids, classes, data attributes, network traffic, or JS state.

Observation settling (V4).  An action may answer by replacing the document rather than
mutating it -- ``fetch(...).then(() => location.href = ...)`` is an ordinary page pattern --
and the snapshot script runs inside the document it is about to lose.  Two of the six
gauntlet-v3 applications do exactly this and ended every V2 run with
``Execution context was destroyed`` (docs/v3_result.md).  Settling is therefore stated in
terms of two observable conditions rather than a delay: the request count the page has
outstanding must be zero, and three consecutive snapshots must agree.  A context destroyed
by a document swap is a transient failure with a definite end, so it is waited out under a
bounded budget and restarts the agreement count; every other browser error is raised
unchanged.  Only the *number* of outstanding requests is used, never their addresses or
contents -- the same idleness signal playwright's own ``networkidle`` load state is built
on, which this wrapper already used for navigation and reload.
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import sync_playwright

from semabi.compiler.observation import Node, Observation

SCOPE_STATE_JS = r"""
    for (const [attribute, key] of [['aria-expanded','expanded'], ['aria-busy','busy'],
                                   ['aria-selected','selected'], ['aria-pressed','pressed']]) {
      const value = e.getAttribute(attribute);
      if (value === 'true' || value === 'false') n[key] = value === 'true';
    }
    if (e.getAttribute('aria-pressed') === 'mixed') n.pressed = 'mixed';
    if (e.tagName.toLowerCase() === 'details') n.expanded = e.open;
    for (const [attribute, key] of [['aria-rowcount','row_count'], ['aria-rowindex','row_index'],
                                   ['aria-setsize','set_size'], ['aria-posinset','pos_in_set']]) {
      const value = e.getAttribute(attribute);
      if (value !== null && /^-?\d+$/.test(value)) n[key] = Number(value);
    }
"""

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
    else {
      const refs = (e.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean)
        .map(id => document.getElementById(id)).filter(n => n && visible(n));
      if (refs.length) name = refs.map(n => n.innerText || '').join(' ').replace(/\s+/g, ' ').trim();
    }
    const n = { i: nodes.length, parent, role, name };
    const r = e.getBoundingClientRect(); n.bbox = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
    if (t === 'input' || t === 'textarea') { if (role==='checkbox'||role==='radio') n.checked = !!e.checked; else n.value = e.value; if (e.placeholder) n.placeholder = e.placeholder; }
    if (t === 'select') { n.options = Array.from(e.options).map(o=>o.textContent.trim()); n.value = e.selectedIndex>=0 ? e.options[e.selectedIndex].textContent.trim() : ''; }
    if (e.getAttribute('aria-current')) n.current = true;
    /* OBSERVATION_SCOPE */
    if (role==='group' && !name && e.childElementCount===0) return;
    nodes.push(n); handles.push(e);
    const idx = n.i;
    for (const c of e.children) walk(c, idx);
  };
  walk(document.body, -1);
  window.__semabi_nodes = handles;
  return nodes;
}
""".replace('/* OBSERVATION_SCOPE */', SCOPE_STATE_JS)


_NAVIGATION_SIGNATURES = (
    "execution context was destroyed",
    "cannot find context with specified id",
    "execution context is not available",
    "frame was detached",
    "navigating and changing the document",
)


def _is_navigation_error(exc: BaseException) -> bool:
    """True only for a context lost to a document swap, never for a permanent failure."""
    text = str(exc).lower()
    return any(signature in text for signature in _NAVIGATION_SIGNATURES)


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

    def __init__(self, url: str, reset_url: str, headless: bool = True, settle_ms: int = 150,
                 max_settle_ms: int = 3000, navigation_ms: int = 5000, max_navigations: int = 4,
                 *, playwright=None):
        self.url = url
        self.reset_url = reset_url
        self.settle_ms = settle_ms
        self.max_settle_ms = max_settle_ms
        self.navigation_ms = navigation_ms
        self.max_navigations = max_navigations
        self._owns_playwright = playwright is None
        self._pw = playwright
        self._browser = None
        self._closed = False
        self.n_primitives = 0
        self.n_resets = 0
        self.episode = 0
        self.step_hooks: list = []
        self._last_obs: Observation | None = None
        # settling telemetry; provenance only, never an input to induction
        self.n_navigations = 0          # document swaps waited out during an observation
        self.n_navigation_waits = 0     # snapshot attempts lost to a destroyed context
        self.n_settle_timeouts = 0      # observations that hit their budget unsettled
        self._inflight = 0              # requests the page has outstanding (count only)
        try:
            if self._pw is None:
                self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=headless)
            self._page = self._browser.new_page(viewport={"width": 1400, "height": 1000})
            self._page.on("request", self._on_request)
            self._page.on("requestfinished", self._on_request_done)
            self._page.on("requestfailed", self._on_request_done)
        except BaseException:
            try:
                self.close()
            except BaseException:
                pass  # Preserve the startup failure after attempting resource cleanup.
            raise

    # ------------------------------------------------------- settling signals
    def _on_request(self, _request) -> None:
        self._inflight += 1

    def _on_request_done(self, _request) -> None:
        self._inflight = max(0, self._inflight - 1)

    @property
    def quiet(self) -> bool:
        """No request outstanding, so a fetch-then-navigate answer cannot still be coming."""
        return self._inflight == 0

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            if self._browser is not None:
                self._browser.close()
        finally:
            if self._owns_playwright and self._pw is not None:
                self._pw.stop()

    # -------------------------------------------------------------- observe
    def _raw_snapshot(self) -> Observation:
        raw = self._page.evaluate(SNAPSHOT_JS)
        nodes = [Node(d["i"], d["parent"], d["role"], d["name"], d.get("value"), d.get("checked"),
                      d.get("options"), d.get("placeholder"), d.get("current"), tuple(d["bbox"])) for d in raw]
        return Observation(nodes, self._page.url)

    def _snapshot(self, deadline: float) -> Observation:
        """One raw snapshot, waiting out a document swap that happens underneath it.

        A navigation destroys the execution context the snapshot script runs in.  That is a
        transient condition with a definite end -- the next document -- so it is waited out
        until `deadline`, and only for errors that name a context or frame swap.  Anything
        else (a closed target, a crashed browser, a script error) is raised unchanged, so a
        permanent failure is never silently turned into an observation."""
        while True:
            try:
                return self._raw_snapshot()
            except Exception as exc:  # noqa: BLE001 - re-raised unless it is a document swap
                if not _is_navigation_error(exc) or time.time() >= deadline:
                    raise
                self.n_navigation_waits += 1
                remaining = deadline - time.time()
                try:
                    self._page.wait_for_load_state("domcontentloaded",
                                                   timeout=max(50.0, remaining * 1000))
                except Exception:  # noqa: BLE001 - the budget, not this wait, is the bound
                    pass
                time.sleep(min(self.settle_ms / 1000, max(0.01, deadline - time.time())))

    def observe(self) -> Observation:
        """Snapshot after the page has settled.

        Settled means two things at once: the page has no request outstanding, so an answer
        that arrives as `fetch(...).then(() => location.href = ...)` cannot still be in
        flight; and three consecutive snapshots `settle_ms` apart agree.  A document swap
        observed while snapshotting restarts the agreement count and extends the budget once,
        up to `max_navigations` times, because the page that has to settle is a new one."""
        t0 = time.time()
        hard_deadline = t0 + (self.max_settle_ms + self.navigation_ms * self.max_navigations) / 1000
        settle_deadline = t0 + self.max_settle_ms / 1000
        waits = self.n_navigation_waits
        grants = 0
        prev = self._snapshot(hard_deadline)
        stable = 0
        while True:
            time.sleep(self.settle_ms / 1000)
            cur = self._snapshot(hard_deadline)
            if self.n_navigation_waits > waits:
                # the document was replaced under the snapshot: a different page now has to
                # settle, so agreement restarts and the budget is extended once per swap
                waits = self.n_navigation_waits
                stable = 0
                if grants < self.max_navigations:
                    grants += 1
                    self.n_navigations += 1
                    settle_deadline = time.time() + (self.max_settle_ms + self.navigation_ms) / 1000
            elif not self.quiet:
                # a request is outstanding; whatever it answers has not been rendered yet
                stable = 0
            elif cur.structural_signature() == prev.structural_signature():
                stable += 1
                if stable >= 2:
                    break
            else:
                stable = 0
            prev = cur
            now = time.time()
            if now > settle_deadline or now > hard_deadline:
                self.n_settle_timeouts += 1
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
