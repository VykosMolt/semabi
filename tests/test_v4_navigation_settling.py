"""Tests that the observation layer survives an action that replaces the document
(e.g. a full-page navigation), rather than crashing.

Checks the four things the fix has to get right: the observation survives, it is the
new page, a permanent browser error is still raised, and primitive accounting is
untouched by the retries."""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from semabi.compiler.browser import Browser, Primitive, _is_navigation_error
from semabi.compiler import browser as browser_module
from semabi.compiler.runtime import Runtime
from semabi.compiler.browser_session import BrowserSession

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
def test_stalled_rendering_is_unsettled_and_requires_a_fresh_observation():
    browser = BrowserSession('https://synthetic.invalid/')
    browser.render_ready_ms = 80
    try:
        browser._page.set_content('''<button onclick="this.textContent='Changed'">Apply</button>
          <script>
            window.savedRAF = requestAnimationFrame;
            window.requestAnimationFrame = () => 1;
            window.__semabi_render_ready = true;
            document.__semabi_render_ready = true;
          </script>''')
        surface = browser.read()
        button = next(n for n in surface.observation.nodes if n.role == 'button')
        assert not surface.settled
        assert browser._last_obs is None and browser._render_root is None
        assert browser.n_primitives == 0

        # Frame delivery returning does not license a retry with the unsettled IDs.
        browser._page.evaluate('() => { requestAnimationFrame = savedRAF; }')
        result = browser.act(Primitive('click', target=button.i))
        assert not result.ok and 'unsettled' in result.error
        assert browser._page.locator('button').inner_text() == 'Apply'
        assert browser.n_primitives == 1

        # This arm tests recovery, not a three-second browser startup guarantee.
        # The production default still refuses safely when its budget expires.
        browser.render_ready_ms = 10000
        fresh = browser.read()
        assert fresh.settled
        button = next(n for n in fresh.observation.nodes if n.role == 'button')
        result = browser.act(Primitive('click', target=button.i))
        assert result.ok, result.error
        assert browser._page.locator('button').inner_text() == 'Changed'
    finally:
        browser.close()


@pytest.mark.slow
def test_render_readiness_is_document_local_and_warm_reads_do_not_wait_for_frames(monkeypatch):
    browser = BrowserSession('https://synthetic.invalid/')
    try:
        browser._page.set_content('<button>First</button>')
        assert browser.read().settled
        root = browser._render_root
        disposed = []
        dispose = root.dispose
        monkeypatch.setattr(root, 'dispose', lambda: (disposed.append(True), dispose())[1])
        # Startup readiness is cached, not a substitute for per-action actionability.
        browser._page.evaluate('() => { window.frameCalls = 0; requestAnimationFrame = () => ++frameCalls; }')
        assert browser.read().settled
        assert browser._page.evaluate('frameCalls') == 0
        assert browser._render_root is root

        browser._page.set_content('<button>Replacement</button>')
        browser.render_ready_ms = 80
        assert not browser.read().settled
        assert disposed == [True]
        assert browser._render_root is None
    finally:
        browser.close()


@pytest.mark.slow
def test_research_observation_explicitly_rejects_stalled_rendering():
    browser = Browser('https://synthetic.invalid/', '', render_ready_ms=80)
    try:
        browser._page.set_content('<button>Apply</button><script>requestAnimationFrame = () => 1</script>')
        with pytest.raises(RuntimeError, match='Observation unsettled'):
            browser.observe()
        assert browser.n_settle_timeouts == 1
        assert browser.n_primitives == 0
        assert browser._last_obs is None and browser._render_root is None
        assert not browser.act(Primitive('click', target=1)).ok
    finally:
        browser.close()


class _Driver:
    def __init__(self, failure=None):
        self.failure = failure
        self.browsers = []
        self.stop_calls = 0
        self.chromium = SimpleNamespace(launch=self.launch)

    def launch(self, **options):
        if self.failure == 'launch':
            raise RuntimeError('synthetic launch failure')
        browser = _DriverBrowser(self)
        self.browsers.append(browser)
        return browser

    def stop(self):
        self.stop_calls += 1


class _DriverBrowser:
    def __init__(self, driver):
        self.driver = driver
        self.close_calls = 0

    def new_page(self, **options):
        if self.driver.failure in {'new_page', 'new_page_and_close'}:
            raise RuntimeError('synthetic new_page failure')
        return SimpleNamespace(on=lambda *args: None, evaluate=self.evaluate,
                               url='https://synthetic.invalid/')

    def evaluate(self, _script):
        if self.close_calls or self.driver.stop_calls:
            raise RuntimeError('synthetic closed browser')
        return []

    def close(self):
        self.close_calls += 1
        if self.driver.failure == 'new_page_and_close':
            raise RuntimeError('synthetic cleanup failure')


def test_native_browser_owns_and_stops_its_default_driver_once(monkeypatch):
    driver = _Driver()
    starts = []
    monkeypatch.setattr(browser_module, 'sync_playwright',
                        lambda: SimpleNamespace(start=lambda: starts.append(driver) or driver))

    browser = Browser('https://synthetic.invalid/', '')
    released = []
    browser._render_root = SimpleNamespace(dispose=lambda: released.append(True))
    browser.close()
    browser.close()

    assert starts == [driver]
    assert driver.browsers[0].close_calls == 1
    assert driver.stop_calls == 1
    assert released == [True] and browser._render_root is None


def test_failed_readiness_disposes_handle_without_masking_primary_failure():
    browser = Browser.__new__(Browser)
    browser._render_root = None
    disposed = []

    def dispose():
        disposed.append(True)
        raise RuntimeError('synthetic destroyed document cleanup')

    def fail(*args):
        raise RuntimeError('synthetic permanent browser failure')

    root = SimpleNamespace(dispose=dispose)
    browser._page = SimpleNamespace(evaluate_handle=lambda script: root, evaluate=fail)
    with pytest.raises(RuntimeError, match='synthetic permanent browser failure'):
        browser._wait_for_render(80)
    assert disposed == [True] and browser._render_root is None


def test_borrowed_driver_keeps_another_browser_usable_after_one_closes(monkeypatch):
    driver = _Driver()

    def unexpected_start():
        raise AssertionError('a borrowed driver must not start another event loop')

    monkeypatch.setattr(browser_module, 'sync_playwright', unexpected_start)
    first = Browser('https://synthetic.invalid/', '', playwright=driver)
    second = Browser('https://synthetic.invalid/', '', playwright=driver)
    first.close()

    assert second._raw_snapshot().url == 'https://synthetic.invalid/'
    assert driver.stop_calls == 0
    assert driver.browsers[0].close_calls == 1
    assert driver.browsers[1].close_calls == 0
    second.close()
    assert driver.browsers[1].close_calls == 1
    assert driver.stop_calls == 0


@pytest.mark.parametrize('borrowed', [False, True], ids=['owned_driver', 'borrowed_driver'])
@pytest.mark.parametrize('failure', ['launch', 'new_page', 'new_page_and_close'])
def test_browser_startup_failure_cleans_acquired_resources(monkeypatch, borrowed, failure):
    driver = _Driver(failure)
    monkeypatch.setattr(browser_module, 'sync_playwright', lambda: SimpleNamespace(start=lambda: driver))
    expected = 'synthetic launch failure' if failure == 'launch' else 'synthetic new_page failure'

    with pytest.raises(RuntimeError, match=expected):
        Browser('https://synthetic.invalid/', '', playwright=driver if borrowed else None)

    assert driver.stop_calls == (0 if borrowed else 1)
    assert [browser.close_calls for browser in driver.browsers] == ([] if failure == 'launch' else [1])


@pytest.mark.slow
def test_runtime_two_real_browsers_survive_reconnect_and_individual_close(tmp_path):
    srv = _serve()
    base = f'http://127.0.0.1:{srv.server_address[1]}'
    runtime = Runtime(tmp_path)
    first = {'id': 'first', 'url': base + '/first'}
    second = {'id': 'second', 'url': base + '/second'}
    try:
        assert runtime.connect(first, {})['status'] == 'CONNECTED'
        assert runtime.connect(second, {})['status'] == 'CONNECTED'
        first_browser, second_browser = runtime.sessions['first'], runtime.sessions['second']
        assert first_browser._pw is second_browser._pw is runtime._playwright
        assert first_browser._browser is not second_browser._browser
        assert first_browser._page.context is not second_browser._page.context
        assert runtime.inspect(second)['settled']

        assert runtime.connect(first, {})['status'] == 'CONNECTED'
        assert runtime.sessions['first'] is not first_browser
        assert first_browser._page.is_closed()
        assert runtime.sessions['second'] is second_browser
        assert runtime.inspect(second)['settled']
        runtime.close('first')
        assert runtime.inspect(second)['settled']
    finally:
        try:
            runtime.close()
        finally:
            srv.shutdown()
            srv.server_close()
    assert runtime.sessions == {}
    assert runtime._playwright is None


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
