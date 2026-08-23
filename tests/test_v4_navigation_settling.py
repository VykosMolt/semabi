"""The observation layer must survive an action that replaces the document.

Two of the six gauntlet-v3 applications answer every action with
``fetch(...).then(() => location.href = ...)``.  Under V2 that ended the run on the first
such action with ``Execution context was destroyed`` and no trace was produced at all
(docs/v3_result.md, docs/data/v3/crash_navigation.json).  These tests use a minimal
fixture that reproduces the pattern generically -- no gauntlet-v3 code, no application
specific waiting -- and check the four things the fix has to get right: the observation
survives, it is the *new* page, a permanent browser error is still raised, and primitive
accounting is untouched by the retries.
"""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from semabi.compiler.browser import Browser, Primitive, _is_navigation_error

PAGE = """<!doctype html><html><body>
<h1>step %d</h1>
<button id="go" type="button">advance</button>
<script>
document.getElementById('go').addEventListener('click', function () {
  fetch('/bump', {method: 'POST'}).then(function (r) { return r.json(); }).then(function (j) {
    location.href = '/?n=' + j.n;
  });
});
</script>
</body></html>"""


class _Handler(BaseHTTPRequestHandler):
    n = 0

    def log_message(self, *a):
        pass

    def _send(self, body, ctype):
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(PAGE % _Handler.n, "text/html; charset=utf-8")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.path == "/reset":
            _Handler.n = 0
        else:
            _Handler.n += 1
        self._send('{"n": %d}' % _Handler.n, "application/json")


def _serve():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_navigation_error_recognised_but_permanent_errors_are_not():
    assert _is_navigation_error(RuntimeError("Execution context was destroyed, most likely because of a navigation"))
    assert _is_navigation_error(RuntimeError("Cannot find context with specified id"))
    assert not _is_navigation_error(RuntimeError("Target page, context or browser has been closed"))
    assert not _is_navigation_error(RuntimeError("TypeError: e.getAttribute is not a function"))


@pytest.mark.slow
def test_fetch_then_navigate_action_yields_the_settled_new_page():
    _Handler.n = 0
    srv = _serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        browser = Browser(f"{base}/", f"{base}/reset")
        try:
            browser.goto()
            before = browser.observe()
            assert any("step 0" in n.name for n in before.nodes)
            button = next(n for n in before.nodes if n.role == "button")
            primitives_before = browser.n_primitives
            result = browser.act(Primitive("click", target=button.i))
            after = browser.observe()

            assert result.ok, result.error
            # the observation is the page the action produced, not the one it destroyed
            assert any("step 1" in n.name for n in after.nodes), [n.name for n in after.nodes]
            assert before.structural_signature() != after.structural_signature()
            # one primitive, whatever the settling had to do to see its result
            assert browser.n_primitives == primitives_before + 1
            assert browser.quiet

            # and it keeps working: the pattern repeats on every action
            button = next(n for n in after.nodes if n.role == "button")
            browser.act(Primitive("click", target=button.i))
            third = browser.observe()
            assert any("step 2" in n.name for n in third.nodes)
            assert browser.n_primitives == primitives_before + 2
        finally:
            browser.close()
    finally:
        srv.shutdown()


@pytest.mark.slow
def test_a_permanent_browser_failure_is_raised_not_waited_out():
    _Handler.n = 0
    srv = _serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        browser = Browser(f"{base}/", f"{base}/reset")
        browser.goto()
        browser.observe()
        browser.close()
        with pytest.raises(Exception) as excinfo:
            browser.observe()
        assert not _is_navigation_error(excinfo.value)
    finally:
        srv.shutdown()
