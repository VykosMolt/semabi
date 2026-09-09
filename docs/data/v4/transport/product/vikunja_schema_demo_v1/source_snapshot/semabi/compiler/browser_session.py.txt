"""Account-scoped browser sessions using only rendered interface evidence.

The richer product snapshot keeps local form/row information independently of
V4's persistent identity choices. DOM IDs are not business identities. No page
application source, network payload, private JS store or hidden endpoint is read.
"""
from __future__ import annotations

import time
from urllib.parse import urlsplit

from semabi.compiler.browser import Browser, Primitive
from semabi.compiler.observation import Node, Observation
from semabi.compiler.surface import Surface, digest


SURFACE_JS = r"""() => {
  const nodes = [], handles = [], controls = {}, forms = {}, text_boundaries = {};
  const text = s => (s || '').replace(/\s+/g, ' ').trim();
  const visible = e => {
    const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && s.visibility !== 'collapse'
      && e.checkVisibility({checkOpacity:true, checkVisibilityCSS:true})
      && (r.width > 0 || r.height > 0);
  };
  const ownText = e => text(Array.from(e.childNodes).filter(c => c.nodeType === 3).map(c => c.textContent).join(' '));
  const editableText = e => {
    const parts = [];
    const walk = n => {
      if (n.nodeType === 3) { parts.push(n.textContent); return; }
      if (n.nodeType !== 1 || n.getAttribute('aria-hidden') === 'true' || !visible(n)) return;
      for (const child of n.childNodes) walk(child);
    };
    walk(e);
    return text(parts.join(' '));
  };
  const paragraphText = e => {
    // A paragraph/preformatted block is one rendered text boundary. Preserve
    // its inline text order without joining unrelated record fields. Decline
    // aggregation when hidden content, widgets, or another block is present.
    if (!['P', 'PRE'].includes(e.tagName) || e.isContentEditable) return null;
    const inline = new Set(['SPAN', 'EM', 'STRONG', 'B', 'I', 'SMALL', 'CODE',
      'S', 'DEL', 'INS', 'U', 'MARK', 'ABBR', 'SUB', 'SUP', 'A']);
    for (const child of e.querySelectorAll('*')) {
      if (!inline.has(child.tagName) || !visible(child) || child.isContentEditable
          || !['inline', 'inline-block', 'inline-flex', 'inline-grid', 'contents']
              .includes(getComputedStyle(child).display)
          || child.getAttribute('aria-hidden') === 'true'
          || child.getAttribute('aria-haspopup')
          || (child.hasAttribute('role') && !['none', 'presentation', 'text', 'link']
              .includes(child.getAttribute('role')))) return null;
    }
    return text(e.innerText);
  };
  const label = e => {
    if (e.getAttribute('aria-label')) return text(e.getAttribute('aria-label'));
    const refs = (e.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean)
      .map(id => document.getElementById(id)).filter(n => n && visible(n));
    if (refs.length) return text(refs.map(n => n.innerText).join(' '));
    const labels = Array.from(e.labels || []).filter(visible);
    if (labels.length) return text(labels.map(n => n.innerText).join(' '));
    if (e.placeholder) return text(e.placeholder);
    // Some visual editors omit the HTML label association. Use a local label
    // only when the nearest small scope contains this single visible editor.
    if (['INPUT','TEXTAREA','SELECT'].includes(e.tagName) || e.isContentEditable) {
      let scope = e.parentElement;
      for (let depth = 0; scope && depth < 3; depth++, scope = scope.parentElement) {
        const editors = Array.from(scope.querySelectorAll('input,textarea,select,[contenteditable="true"]'))
          .filter(n => visible(n) && !(n.tagName === 'INPUT' && n.type === 'hidden'));
        if (editors.length !== 1 || editors[0] !== e) break;
        const names = [...new Set(Array.from(scope.querySelectorAll('label')).filter(visible)
          .map(n => text(n.innerText)).filter(Boolean))];
        if (names.length === 1) return names[0];
        if (names.length > 1) break;
        const branch = Array.from(scope.children).find(n => n === e || n.contains(e));
        const preceding = Array.from(scope.children).slice(0, Array.from(scope.children).indexOf(branch))
          .filter(n => visible(n) && !n.querySelector('button,a,input,textarea,select'))
          .map(n => text(n.innerText)).filter(n => n && n.length <= 80);
        const nearbyNames = [...new Set(preceding)];
        if (nearbyNames.length === 1) return nearbyNames[0];
      }
    }
    return '';
  };
  const roleOf = e => {
    const explicit = e.getAttribute('role');
    if (explicit && !['none', 'presentation'].includes(explicit)) return explicit;
    const tag = e.tagName.toLowerCase();
    if (e.isContentEditable && !e.parentElement?.isContentEditable) return 'textbox';
    if (tag === 'button') return 'button';
    if (tag === 'summary') return 'button';
    if (tag === 'a') return 'link';
    if (tag === 'input') {
      const type = (e.type || 'text').toLowerCase();
      if (['submit', 'button', 'reset', 'image'].includes(type)) return 'button';
      if (['checkbox', 'radio'].includes(type)) return type;
      return 'textbox';
    }
    if (tag === 'textarea') return 'textbox';
    if (tag === 'select') return 'combobox';
    if (/^h[1-6]$/.test(tag)) return 'heading';
    return ({li:'listitem', ul:'list', ol:'list', table:'table', tr:'row', td:'cell', th:'cell',
      thead:'rowgroup', tbody:'rowgroup', tfoot:'rowgroup', article:'article',
      p:'text', span:'text', em:'text', strong:'text', b:'text', i:'text', label:'text',
      small:'text', code:'text', pre:'text'})[tag] || 'group';
  };
  const walk = (e, parent) => {
    const tag = e.tagName.toLowerCase();
    if (['script','style','option','title','head','noscript','template'].includes(tag) || !visible(e)) return;
    if (tag === 'input' && e.type === 'hidden') return;
    const role = roleOf(e), interactive = ['button','link','textbox','combobox','checkbox','radio','menu','menuitem'].includes(role);
    const paragraph = ['p', 'pre'].includes(tag) && !e.isContentEditable;
    const completeText = paragraph ? paragraphText(e) : null;
    let name = interactive ? label(e) : completeText ?? ownText(e);
    if (!name && !paragraph && ['button','link','menuitem','heading','text','cell','alert','status','listitem'].includes(role))
      name = text(e.innerText);
    if (!name && role === 'button' && tag === 'input') name = text(e.value);
    const i = nodes.length, r = e.getBoundingClientRect();
    if (paragraph) text_boundaries[i] = completeText;
    const n = {i, parent, role, name, bbox:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]};
    const type = tag === 'input' ? (e.type || 'text') : role === 'textbox' && e.isContentEditable ? 'contenteditable' : tag === 'textarea' ? 'textarea' : '';
    if (role === 'textbox') {
      n.value = type === 'password' ? '[REDACTED]' : e.isContentEditable ? editableText(e) : (e.value || '');
      if (e.placeholder) n.placeholder = e.placeholder;
    }
    if (['checkbox','radio'].includes(role)) n.checked = !!e.checked || e.getAttribute('aria-checked') === 'true';
    if (role === 'combobox' && tag === 'select') {
      n.options = Array.from(e.options).map(o => text(o.textContent));
      n.value = e.selectedIndex >= 0 ? text(e.options[e.selectedIndex].textContent) : '';
    }
    if (e.getAttribute('aria-current')) n.current = true;
    nodes.push(n); handles.push(e);
    if (interactive) controls[i] = {role, label:name, input_type:type, required:!!e.required,
      disabled:!!e.disabled || e.getAttribute('aria-disabled') === 'true', readonly:!!e.readOnly,
      min:e.min || null, max:e.max || null, max_length:e.maxLength >= 0 ? e.maxLength : null,
      options:n.options || [], submit:role === 'button' && e.type === 'submit', form:null,
      has_popup:e.getAttribute('aria-haspopup') || null};
    // The destination a user can inspect/copy from a rendered link. Reading
    // this affordance never follows it or retrieves an endpoint response.
    if (role === 'link' && tag === 'a' && e.hasAttribute('href')) controls[i].destination = e.href;
    if (tag === 'form') forms[i] = {role:'form'};
    for (const child of e.children) walk(child, i);
  };
  walk(document.body, -1);
  for (const [index, control] of Object.entries(controls)) {
    const form = handles[index].form || handles[index].closest('form');
    const formIndex = handles.indexOf(form);
    if (formIndex >= 0) control.form = formIndex;
  }
  window.__semabi_nodes = handles;
  return {nodes, controls, forms, text_boundaries};
}"""


def origin_of(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("An HTTP(S) URL without embedded credentials is required")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    default = port == (443 if parsed.scheme == "https" else 80)
    return f"{parsed.scheme}://{host}" + ("" if default else f":{port}")


class BrowserSession(Browser):
    def __init__(self, url: str, *, headless: bool = True, playwright=None):
        self.allowed_origin = origin_of(url)
        self.surface: Surface | None = None
        self.blocked_requests = 0
        super().__init__(url, reset_url="", headless=headless, settle_ms=100,
                         max_settle_ms=2000, navigation_ms=3000, max_navigations=2,
                         playwright=playwright)
        try:
            self._page.context.route("**/*", self._route)
            self._page.context.on("page", lambda page: page.close() if page is not self._page else None)
        except BaseException:
            try:
                self.close()
            except BaseException:
                pass
            raise

    def _route(self, route) -> None:
        url = route.request.url
        try:
            allowed = origin_of(url) == self.allowed_origin
        except ValueError:
            allowed = url.startswith(("data:", "blob:"))
        if allowed:
            route.continue_()
        else:
            self.blocked_requests += 1
            route.abort("blockedbyclient")

    def _raw_snapshot(self) -> Observation:
        raw = self._page.evaluate(SURFACE_JS)
        obs = Observation([Node.from_json(node) for node in raw["nodes"]], self._page.url)
        self.surface = Surface(obs, {int(key): value for key, value in raw["controls"].items()},
                               {int(key): value for key, value in raw["forms"].items()},
                               text_boundaries={int(key): value for key, value in raw["text_boundaries"].items()})
        return obs

    def read(self) -> Surface:
        # Long-lived event streams need not prevent a stable rendered read.
        # Stability is local snapshot agreement, not network or business quiescence.
        deadline = time.monotonic() + self.max_settle_ms / 1000
        previous, agreements = None, 0
        while True:
            obs = self._snapshot(time.time() + self.navigation_ms / 1000)
            signature = digest([obs.structural_signature(), self.surface.controls, self.surface.forms,
                                self.surface.text_boundaries])
            agreements = agreements + 1 if signature == previous else 0
            if agreements >= 2 or time.monotonic() >= deadline:
                break
            previous = signature
            time.sleep(self.settle_ms / 1000)
        if self.surface is None:
            raise RuntimeError("No rendered observation is available")
        self.surface.settled = agreements >= 2
        self._last_obs = self.surface.observation
        return self.surface

    def goto(self, url: str | None = None):
        destination = url or self.url
        if origin_of(destination) != self.allowed_origin:
            raise ValueError("Navigation is outside the connection origin")
        self._page.goto(destination, wait_until="domcontentloaded", timeout=10000)
        return self.read().observation

    def reload(self) -> Surface:
        self._page.reload(wait_until="domcontentloaded", timeout=10000)
        return self.read()

    def retain_nodes(self, nodes: list[int]):
        """Keep temporary observed DOM elements, never a persistent record key."""
        return self._page.evaluate_handle("indices => indices.map(i => window.__semabi_nodes[i])", nodes)

    def nodes_retained(self, retained, nodes: list[int]) -> bool:
        return retained.evaluate("""(elements, indices) => elements.length === indices.length &&
          elements.every((element, i) => element && element.isConnected &&
            element === window.__semabi_nodes[indices[i]] && elements[0].contains(element))""", nodes)

    @staticmethod
    def release_nodes(retained) -> None:
        retained.dispose()

    def act(self, primitive: Primitive):
        if primitive.kind == "reset":
            raise ValueError("A product connection has no implicit reset endpoint")
        return super().act(primitive)

    @staticmethod
    def _login_controls(surface: Surface) -> dict | None:
        """Select one supported login scope from rendered controls only.

        Native submits take priority, including disabled competitors. The
        fallback is an explicit English authentication-label prior, not a
        general inference that a nearby button submits a password form.
        """
        passwords = [node for node, control in surface.controls.items()
                     if control["input_type"] == "password"]
        if len(passwords) != 1:
            return None

        def normalized_label(control: dict) -> str:
            return " ".join(control["label"].split()).casefold()

        auth_labels = {"login", "log in", "sign in"}
        password = passwords[0]
        root = surface.controls[password].get("form")
        native = root is not None
        if native:
            if root not in surface.forms:
                return None
            members = set(surface.observation.subtree(root))
            if password not in members:
                return None
            owned = {node: control for node, control in surface.controls.items()
                     if control.get("form") == root}
            # Native form ownership may reach outside the form subtree. Such
            # competing credentials/actions cannot disappear from selection,
            # but this supported scope does not authorize acting outside it.
            if any(node not in members and (
                    control["role"] == "textbox" and control["input_type"] in {"text", "email", "", "password"}
                    or control["role"] == "button" and (
                        control.get("submit") or normalized_label(control) in auth_labels))
                   for node, control in owned.items()):
                return None
            controls = {node: control for node, control in owned.items() if node in members}
        else:
            # Preserve the existing form-less requirement of globally unique
            # username and button controls. Do not discover a new smaller form.
            controls = surface.controls
        users = [node for node, control in controls.items()
                 if control["role"] == "textbox" and node != password
                 and control["input_type"] in {"text", "email", ""}]
        buttons = [node for node, control in controls.items() if control["role"] == "button"]
        if len(users) != 1:
            return None
        user = users[0]
        if any(surface.controls[node]["role"] != "textbox" or surface.controls[node]["disabled"]
               or surface.controls[node]["readonly"] for node in (user, password)):
            return None
        if native:
            submits = [node for node in buttons if controls[node].get("submit")]
            if submits:
                if len(submits) != 1:
                    return None
                button, basis = submits[0], "unique_native_submit"
            else:
                candidates = [node for node in buttons if not controls[node]["disabled"]
                              and normalized_label(controls[node]) in auth_labels]
                if len(candidates) != 1:
                    return None
                button, basis = candidates[0], "exact_english_login_label_prior"
        else:
            if len(buttons) != 1 or surface.controls[user].get("form") is not None:
                return None
            button = buttons[0]
            if controls[button].get("form") is not None:
                return None
            basis = "unique_native_submit" if controls[button].get("submit") else "exact_english_login_label_prior"
            if not controls[button].get("submit") and normalized_label(controls[button]) not in auth_labels:
                return None
            root = next((ancestor for ancestor in surface.observation.ancestors(password)
                         if {user, password, button} <= set(surface.observation.subtree(ancestor))), None)
            if root is None:
                return None
        # These English labels advertise cancellation or password visibility,
        # even if a page marks that button as its only native submit.
        if controls[button]["disabled"] or normalized_label(controls[button]) in {
                "cancel", "show password", "hide password", "show the password", "hide the password"}:
            return None
        return {"root": root, "user": user, "password": password, "button": button,
                "contract": {"native_form": native, "root_role": surface.observation.node(root).role,
                             "selection_basis": basis,
                             "descriptors": {name: surface.descriptor(node) for name, node in
                                             (("user", user), ("password", password), ("button", button))}}}

    def authenticate(self, credentials: dict) -> dict:
        """Use ordinary password-form UI. No credential values enter evidence."""
        actions = 0
        retained, selection_basis = None, None

        def outcome(status: str, reason: str | None = None) -> dict:
            result = {"status": status, "authentication_actions": actions}
            if reason:
                result["reason"] = reason
            if selection_basis is not None:
                result["login_selection_basis"] = selection_basis
            if selection_basis == "exact_english_login_label_prior":
                result["authentication_prior"] = "Whole normalized English label: Login, Log in, Sign in"
            if status == "CONNECTED":
                result["authentication_evidence"] = "same_origin_settled_password_form_absence"
            return result

        def supported_view(surface: Surface) -> bool:
            return surface.settled and origin_of(surface.observation.url) == self.allowed_origin

        try:
            surface = self.read()
            if not supported_view(surface):
                return outcome("AUTH_REQUIRED", "Authentication requires a settled same-origin view")
            if not any(control["input_type"] == "password" for control in surface.controls.values()):
                return outcome("CONNECTED")
            if not all(isinstance(credentials.get(name), str) and credentials[name]
                       for name in ("username", "password")):
                return outcome("AUTH_REQUIRED", "A unique supported login form and credentials are required")
            selected = self._login_controls(surface)
            if selected is None:
                return outcome("AUTH_REQUIRED", "Login controls are unsupported or ambiguous")
            selection_basis = selected["contract"]["selection_basis"]
            retained = self.retain_nodes([selected[name] for name in ("root", "user", "password", "button")])
            for kind, field, value in [("type", "user", credentials["username"]),
                                       ("type", "password", credentials["password"]),
                                       ("click", "button", None)]:
                current = self.read()
                if not supported_view(current):
                    return outcome("AUTH_REQUIRED", "Authentication requires a settled same-origin view")
                fresh = self._login_controls(current)
                if (fresh is None or fresh["contract"] != selected["contract"]
                        or not self.nodes_retained(retained, [fresh[name] for name in
                                                            ("root", "user", "password", "button")])):
                    return outcome("AUTH_REQUIRED", "Login controls changed before interaction")
                # Login actions bypass the public evidence recorder, including errors.
                actions += 1
                result = self.act(Primitive(kind, fresh[field], value))
                if not result.ok:
                    return outcome("AUTH_REQUIRED", "Login interaction did not complete")
            deadline = time.monotonic() + self.max_settle_ms / 1000
            while True:
                after = self.read()
                if not supported_view(after):
                    return outcome("AUTH_REQUIRED", "Authentication requires a settled same-origin view")
                still_password = any(control["input_type"] == "password" for control in after.controls.values())
                if not still_password or time.monotonic() >= deadline:
                    break
            return outcome("AUTH_REQUIRED" if still_password else "CONNECTED")
        except Exception:
            return outcome("AUTH_REQUIRED", "Login could not be confirmed")
        finally:
            if retained is not None:
                try:
                    self.release_nodes(retained)
                except Exception:
                    pass  # Handle cleanup must not expose credential-bearing errors.
