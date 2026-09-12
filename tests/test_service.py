"""HTTP/storage contract tests with a labeled fake Runtime, never browser acceptance."""
from __future__ import annotations

import json
import hashlib
import sqlite3
import stat
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest

from semabi.compiler.artifacts import ArtifactStore, StoreError
from semabi.service import Service, connection_request, make_server


def operation(version=1):
    return {"id": "create", "version": version, "name": "FAKE create item", "kind": "create_record", "status": "ACTIVE",
            "argument_schema": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]},
            "output_schema": {"type": "object"}, "prerequisites": [], "procedure": [{"fake": True}],
            "effect_checks": [{"fake": True}], "support": {"source": "FAKE_RUNTIME_HTTP_CONTRACT_ONLY"},
            "scope": {}, "evidence_sha256": "f" * 64, "supported_scope": "fake contract only"}


class FakeRuntime:
    """Supplies synthetic results solely to exercise the service contract."""

    def __init__(self, directory):
        self.directory = directory
        self.owner = threading.get_ident()
        self.calls = []
        self.sessions = {}
        self.settings = []
        self.invocations = []
        self.invocation_connections = []
        self.mode = "confirm"
        self.empty_learning = False
        self.invalidations = []
        self.entered = threading.Event()
        self.release = threading.Event()
        self.release.set()
        self.intent_was_committed = False

    def _record(self, name, connection=None):
        self.calls.append((name, connection, threading.get_ident()))
        assert threading.get_ident() == self.owner

    def connect(self, connection, credentials):
        self._record("connect", connection["id"])
        self.sessions[connection["id"]] = credentials
        return {"status": "CONNECTED", "credentials": credentials}

    def learn(self, connection, settings, emit):
        self._record("learn", connection["id"])
        self.settings.append(settings)
        credentials = self.sessions[connection["id"]]
        emit({"type": "progress", "message": " ".join(credentials.values()), "credentials": credentials})
        return {"status": "COMPLETE", "metrics": {"fake": True},
                "operations": [] if self.empty_learning else [operation(settings["_operation_versions"].get("create", 0) + 1)],
                "invalidations": self.invalidations}

    def invoke(self, connection, artifact, arguments, emit):
        self._record("invoke", connection["id"])
        self.invocations.append((connection["id"], artifact, arguments))
        self.invocation_connections.append(json.loads(json.dumps(connection)))
        self.entered.set()
        assert self.release.wait(5), "test did not release fake invocation"
        if self.mode == "stale":
            return {"outcome": "FAILED_BEFORE_EFFECT", "operation_status": "STALE",
                    "reason": "fake learned locator assumption failed"}
        if self.mode == "raise_before":
            raise RuntimeError("private-onboarding-password before write")
        emit("write_intent", target="fake-only")
        # A second SQLite connection must see the intent before the fake dispatch proceeds.
        with sqlite3.connect(self.directory.parent / "artifacts.sqlite3") as db:
            self.intent_was_committed = db.execute(
                "SELECT COUNT(*) FROM jobs WHERE kind='invoke' AND status='RUNNING' AND write_intent=1").fetchone()[0] == 1
        if self.mode == "raise_after":
            raise RuntimeError("private-onboarding-password after write")
        emit({"type": "effect_observed", "fake": True})
        return {"outcome": "APPLICATION_REFUSAL" if self.mode == "refuse" else "CONFIRMED",
                "effect": {"title": arguments.get("title"), "fake": True}, "metrics": {"writes": 1}}

    def inspect(self, connection):
        self._record("inspect", connection["id"])
        return {"status": "CONNECTED"}

    def close(self, connection_id=None):
        self._record("close", connection_id)
        if connection_id is None:
            self.sessions.clear()
        else:
            self.sessions.pop(connection_id, None)


class HTTPHarness:
    def __init__(self, directory):
        self.fake = None

        def factory(path):
            self.fake = FakeRuntime(path)
            return self.fake
        self.service = Service(directory, runtime_factory=factory)
        try:
            self.server = make_server(self.service, port=0)
        except BaseException:
            self.service.close(timeout=5)
            raise
        self.base = "http://127.0.0.1:" + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def close(self):
        self.fake.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)
        assert not self.thread.is_alive()
        assert self.service.close(timeout=5)

    def request(self, method, path, body=None, *, headers=None, authorized=True, raw=None):
        request_headers = {"Content-Type": "application/json"}
        if authorized:
            request_headers["Authorization"] = "Bearer " + self.service.token
        request_headers.update(headers or {})
        data = raw if raw is not None else None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data, headers=request_headers, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, json.load(response)

    def completed(self, accepted):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status, job = self.request("GET", "/v1/jobs/" + accepted["job_id"])
            assert status == 200
            if job["status"] not in ("QUEUED", "RUNNING"):
                return job
            time.sleep(0.005)
        pytest.fail("fake Runtime job did not complete")

    def connect(self, *, credentials=None, exploration=True):
        status, accepted = self.request("POST", "/v1/connections", {
            "url": "http://example.test/work", "credentials": credentials or {},
            "scope": {"exploration_enabled": exploration, "max_actions": 12, "max_writes": 3}})
        assert status == 202
        assert self.completed(accepted)["status"] == "COMPLETED"
        return accepted["id"]

    def learn(self, connection_id):
        status, accepted = self.request("POST", f"/v1/connections/{connection_id}/learn", {"settings": {"max_actions": 10, "max_writes": 2}})
        assert status == 202
        job = self.completed(accepted)
        assert job["status"] == "COMPLETED", job
        return job

    def invoke(self, connection_id, title="fresh", *, version=1, key=None, limits=None):
        body = {"version": version, "arguments": {"title": title}}
        if limits is not None:
            body["limits"] = limits
        return self.request("POST", f"/v1/connections/{connection_id}/operations/create/invoke",
                            body,
                            headers={"Idempotency-Key": key} if key else None)


@pytest.mark.parametrize('exit_reset', [False, True, 'stale_draft'],
                         ids=['repeated_same_and_different_targets', 'contradicted_next_exit', 'restored_stale_draft'])
def test_http_typed_updates_end_at_checked_state_and_guard_the_next_continuation(tmp_path, monkeypatch, exit_reset):
    """Ordinary induced artifact and real HTTP worker; application bits are independent.

    Store/connection plumbing is supplied test setup, not unfamiliar-app evidence.
    The final-exit reset is the evaluator's retained 7ffd0e1 counterexample.
    """
    from types import SimpleNamespace
    import test_operation_runtime as diagnostics

    controlled_browser = (diagnostics._CheckboxRestoredDraftBrowser() if exit_reset == 'stale_draft'
                          else diagnostics._CheckboxVerificationExitResetBrowser())
    with monkeypatch.context() as learning:
        runtime, learned_connection, browser, learned = diagnostics._learn_checkbox_records(
            tmp_path / 'fit', learning, browser=controlled_browser)
    operation = diagnostics._checkbox_kind(learned, 'update_visible_record')
    if exit_reset == 'stale_draft':
        browser.restore_stale_drafts = True
    else:
        browser.reset_on_verification_exit = exit_reset
    browser.close = lambda: None
    api = HTTPHarness.__new__(HTTPHarness)
    api.fake = SimpleNamespace(release=threading.Event())
    api.service = Service(tmp_path / 'service', runtime_factory=lambda directory: runtime)
    try:
        api.server = make_server(api.service, port=0)
    except BaseException:
        api.service.close(timeout=5)
        raise
    api.base = 'http://127.0.0.1:' + str(api.server.server_port)
    api.thread = threading.Thread(target=api.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
    api.thread.start()
    try:
        connection, connecting = api.service.store.create_connection(
            {key: value for key, value in learned_connection.items() if key != 'id'}, {})
        assert api.service.store.start_job(connecting)
        api.service.store.finish_job(connecting, {'status': 'CONNECTED'})
        runtime.sessions[connection['id']] = runtime.sessions.pop(learned_connection['id'])
        publishing = api.service.store.queue_job(connection['id'], 'learn', {})
        assert api.service.store.start_job(publishing)
        api.service.store.finish_job(publishing, {'status': 'COMPLETED'}, operations=[operation])
        path = f"/v1/connections/{connection['id']}/operations/{operation['id']}/invoke"

        def invoke(index, desired):
            status, accepted = api.request('POST', path, {'version': operation['version'],
                'arguments': {'target': browser.rows[index]['URL'], 'pinned': desired}})
            assert status == 202
            api.completed(accepted)
            status, execution = api.request('GET', '/v1/executions/' + accepted['execution_id'])
            assert status == 200
            return execution['result']

        first = invoke(0, True)
        if exit_reset == 'stale_draft':
            assert browser.persisted_resets == [0]
            assert [row['Pinned'] for row in browser.rows] == [False, False]
            assert first['outcome'] != 'CONFIRMED', first
            return
        assert first['outcome'] == 'CONFIRMED', first
        assert browser.rows[0]['Pinned'] is True and browser.rows[1]['Pinned'] is False
        assert browser.scene == 'editor' and browser.exit_resets == []
        assert first['effect']['witness']['checkbox_readback']['values']['pinned'] is True
        if exit_reset:
            second = invoke(0, True)
            assert second['outcome'] == 'UNCERTAIN' and second['operation_status'] == 'STALE'
            assert browser.rows[0]['Pinned'] is False and browser.exit_resets == [0]
            before = len(browser.actions), browser.navigation_count
            status, _ = api.request('POST', path, {'version': operation['version'],
                'arguments': {'target': browser.rows[0]['URL'], 'pinned': True}})
            assert status == 409
            assert (len(browser.actions), browser.navigation_count) == before
        else:
            second = invoke(0, False)
            third = invoke(1, True)
            assert second['outcome'] == third['outcome'] == 'CONFIRMED'
            assert [row['Pinned'] for row in browser.rows] == [False, True]
            assert browser.scene == 'editor' and browser.selected == 1
    finally:
        api.close()


@pytest.fixture
def api(tmp_path):
    harness = HTTPHarness(tmp_path / "service")
    try:
        yield harness
    finally:
        harness.close()


def test_http_connect_learn_schema_invoke_reconnect_and_private_storage(api, capsys):
    credentials = {"username": "onboard-user", "password": "private-onboarding-password"}
    connection_id = api.connect(credentials=credentials)
    learned = api.learn(connection_id)
    status, listing = api.request("GET", f"/v1/connections/{connection_id}/operations")
    assert status == 200 and listing["operations"][0]["id"] == "create"
    assert listing["operations"][0]["argument_schema"]["required"] == ["title"]
    status, accepted = api.invoke(connection_id, "unseen argument", key="first-call")
    assert status == 202
    job = api.completed(accepted)
    assert job["status"] == "COMPLETED" and job["result"]["outcome"] == "CONFIRMED"
    assert job["result"]["effect"]["title"] == "unseen argument"
    assert api.fake.intent_was_committed and job["write_intent"]
    assert [event["sequence"] for event in job["events"]] == list(range(1, len(job["events"]) + 1))
    assert [event["type"] for event in job["events"]] == ["job_started", "write_intent", "effect_observed", "job_finished"]
    status, execution = api.request("GET", "/v1/executions/" + accepted["execution_id"])
    assert status == 200 and execution == job
    status, reconnected = api.request("POST", f"/v1/connections/{connection_id}/reconnect", {})
    assert status == 202 and api.completed(reconnected)["status"] == "COMPLETED"
    calls = api.fake.calls
    assert [call[0] for call in calls][-2:] == ["close", "connect"]
    assert len({call[2] for call in calls}) == 1 and calls[0][2] != threading.get_ident()
    status, connections = api.request("GET", "/v1/connections")
    assert status == 200 and connections["connections"][0]["allowed_origin"] == "http://example.test"
    public = json.dumps([learned, listing, execution, connections]) + capsys.readouterr().out + capsys.readouterr().err
    for secret in [*credentials.values(), api.service.token]:
        assert secret not in public
    assert api.service.store.credentials(connection_id) == credentials
    assert learned["request"] == {"settings": {"max_actions": 10, "max_writes": 2}}
    directory = api.service.store.directory
    for path in (directory, directory / "connections", directory / "connections" / connection_id):
        assert stat.S_IMODE(path.stat().st_mode) == 0o700
    for path in (directory / "token", directory / "artifacts.sqlite3", directory / "artifacts.sqlite3-wal", directory / "artifacts.sqlite3-shm"):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.parametrize("url", ["file:///tmp/app", "http://user:secret@example.test/", "http://user@example.test/",
                                  "http://example.test:99999/", "not a URL", "http://example.test\\evil/"])
def test_connection_validation_rejects_invalid_or_credential_bearing_urls(api, url):
    status, _ = api.request("POST", "/v1/connections", {"url": url})
    assert status == 400
    assert api.service.store.connections() == [] and api.fake.calls == []


def test_url_origin_normalization_and_budgets():
    connection, _ = connection_request({"url": "HTTPS://Example.Test:443/work?q=1#tab"})
    assert connection["allowed_origin"] == "https://example.test"
    assert connection["url"] == "https://example.test/work?q=1#tab"
    assert connection["scope"]["exploration_enabled"] is False
    connection, _ = connection_request({"url": "http://[::1]:9000/"})
    assert connection["allowed_origin"] == "http://[::1]:9000"
    with pytest.raises(StoreError):
        connection_request({"url": "http://example.test/", "scope": {"max_actions": True}})


def test_authentication_openapi_and_body_validation(api):
    assert api.request("GET", "/openapi.json", authorized=False)[0] == 401
    assert api.request("POST", "/v1/connections", {"url": "http://example.test/"}, authorized=False)[0] == 401
    status, description = api.request("GET", "/openapi.json")
    assert status == 200 and description["security"] == [{"localBearer": []}]
    assert description["components"]["schemas"]["Invocation"]["required"] == ["arguments", "version"]
    limits = description["components"]["schemas"]["InvocationLimits"]
    assert limits["additionalProperties"] is False and limits["required"] == []
    assert limits["properties"]["max_actions"]["maximum"] == 40
    assert limits["properties"]["max_writes"]["maximum"] == 25
    assert limits["properties"]["max_seconds"]["exclusiveMinimum"] == 0
    assert limits["properties"]["max_seconds"]["maximum"] == 600
    assert set(description["components"]["schemas"]["InvocationResult"]["properties"]["outcome"]["enum"]) == {
        "CONFIRMED", "APPLICATION_REFUSAL", "FAILED_BEFORE_EFFECT", "UNCERTAIN",
        "PREDICTED_REFUSAL", "PREDICTION_UNAVAILABLE"}
    assert "/v1/executions/{execution_id}" in description["paths"]
    assert "/v1/connections/{connection_id}/operations/{operation_id}/invoke" in description["paths"]
    assert api.service.token not in json.dumps(description)
    for raw in (b'{"url":"http://example.test/","url":"http://other.test/"}', b'{"url":NaN}', b'{"url":1e999}', b'[]'):
        assert api.request("POST", "/v1/connections", raw=raw)[0] == 400
    assert api.service.store.connections() == []


def test_learning_requires_scope_and_cannot_inject_versions_or_expand_budgets(api):
    disabled = api.connect(exploration=False)
    assert api.request("POST", f"/v1/connections/{disabled}/learn", {})[0] == 409
    connection_id = api.connect()
    for settings in ({"_operation_versions": {"create": 100}}, {"_existing_operations": [operation()]},
                     {"_semantic_training_operations": [operation()]},
                     {"max_actions": 13}, {"max_writes": 4}, {"credentials": {}}):
        assert api.request("POST", f"/v1/connections/{connection_id}/learn", {"settings": settings})[0] == 400
    assert api.fake.settings == []


def test_learning_supplies_only_the_current_connections_active_artifacts_internally(api):
    first, second = api.connect(), api.connect()
    api.learn(first)
    assert api.fake.settings[-1]['_existing_operations'] == []
    api.learn(first)
    assert [(item['id'], item['version']) for item in api.fake.settings[-1]['_existing_operations']] == [('create', 1)]
    api.fake.empty_learning = True
    api.learn(first)
    supplied = api.fake.settings[-1]['_existing_operations']
    assert [(item['id'], item['version'], item['status']) for item in supplied] == [('create', 2, 'ACTIVE')]
    assert supplied == api.service.store.operations(first)
    api.learn(second)
    assert api.fake.settings[-1]['_existing_operations'] == []


def test_invocations_bind_connection_and_require_explicit_active_version(api):
    first, second = api.connect(), api.connect()
    api.learn(first)
    assert api.invoke(second)[0] == 404
    assert api.request("GET", f"/v1/connections/{second}/operations/create")[0] == 404
    for body in ({"arguments": {}}, {"arguments": {}, "version": True}, {"arguments": [], "version": 1}):
        assert api.request("POST", f"/v1/connections/{first}/operations/create/invoke", body)[0] == 400
    assert api.invoke(first, version=2)[0] == 404
    assert api.fake.invocations == []


def test_concurrent_idempotency_returns_one_job_and_changed_request_conflicts(api):
    connection_id = api.connect()
    api.learn(connection_id)
    api.fake.release.clear()
    path = f"/v1/connections/{connection_id}/operations/create/invoke"
    requests = [{"arguments": {"title": "fresh", "tag": "value"}, "version": 1},
                {"version": 1, "arguments": {"tag": "value", "title": "fresh"}}]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda body: api.request("POST", path, body, headers={"Idempotency-Key": "once"}), requests))
    assert all(status == 202 for status, _ in responses)
    assert len({body["job_id"] for _, body in responses}) == 1
    assert sorted(body["deduplicated"] for _, body in responses) == [False, True]
    assert api.invoke(connection_id, "different", key="once")[0] == 409
    assert api.fake.entered.wait(3)
    api.fake.release.set()
    job = api.completed(responses[0][1])
    assert job["result"]["outcome"] == "CONFIRMED" and len(api.fake.invocations) == 1


def test_invocation_limit_validation_rejects_expansion_and_nonexact_types(api):
    connection_id = api.connect()
    api.learn(connection_id)
    path = f"/v1/connections/{connection_id}/operations/create/invoke"
    bad_limits = [None, [], False, {"unexpected": 1}]
    bad_limits += [{"max_actions": value} for value in (True, 2.0, "2", 0, -1, 13)]
    bad_limits += [{"max_writes": value} for value in (False, 1.0, "1", -1, 4)]
    bad_limits += [{"max_seconds": value} for value in (True, "1", None, 0, -1, 600.01, float("nan"), float("inf"))]
    bad_limits += [{"max_actions": 2, "max_writes": 3}]
    for limits in bad_limits:
        code, _ = api.request("POST", path, {"version": 1, "arguments": {"title": "fresh"}, "limits": limits})
        assert code == 400, limits
    assert api.fake.invocations == []
    with api.service.store._lock:
        assert api.service.store.db.execute("SELECT COUNT(*) FROM jobs WHERE kind='invoke'").fetchone()[0] == 0


def test_invocation_limits_normalize_for_idempotency_and_do_not_leak_scope(api):
    connection_id = api.connect()
    api.learn(connection_id)
    original = api.service.store.connection(connection_id)
    first_limits = {"max_actions": 6, "max_seconds": 10}
    code, accepted = api.invoke(connection_id, key="limited", limits=first_limits)
    assert code == 202
    job = api.completed(accepted)
    normalized = {"max_actions": 6, "max_writes": 3, "max_seconds": 10.0}
    assert job["request"]["limits"] == normalized
    assert type(job["request"]["limits"]["max_seconds"]) is float
    code, repeated = api.invoke(connection_id, key="limited", limits=normalized)
    assert code == 202 and repeated["deduplicated"] and repeated["id"] == accepted["id"]
    for changed in ({**normalized, "max_actions": 5}, {**normalized, "max_writes": 2},
                    {**normalized, "max_seconds": 9}):
        assert api.invoke(connection_id, key="limited", limits=changed)[0] == 409
    assert api.invoke(connection_id, key="limited")[0] == 409
    code, following = api.invoke(connection_id, "following", key="following")
    assert code == 202 and api.completed(following)["result"]["outcome"] == "CONFIRMED"
    assert api.fake.invocation_connections[0]["scope"] == {**original["scope"], **normalized}
    assert api.fake.invocation_connections[1] == original
    assert api.service.store.connection(connection_id) == original
    assert len(api.fake.invocations) == 2
    assert first_limits == {"max_actions": 6, "max_seconds": 10}


def test_invocation_limits_apply_runtime_hard_caps_and_default_writes_to_actions(api):
    code, connected = api.request("POST", "/v1/connections", {
        "url": "http://example.test/work", "scope": {"exploration_enabled": True, "max_actions": 100, "max_writes": 80}})
    assert code == 202 and api.completed(connected)["status"] == "COMPLETED"
    connection_id = connected["id"]
    api.learn(connection_id)
    for limits in ({"max_actions": 41}, {"max_writes": 26}, {"max_actions": 2, "max_writes": 3}):
        assert api.invoke(connection_id, limits=limits)[0] == 400
    for limits, expected in (({}, {"max_actions": 40, "max_writes": 25}),
                             ({"max_actions": 2}, {"max_actions": 2, "max_writes": 2}),
                             ({"max_writes": 0, "max_seconds": 600},
                              {"max_actions": 40, "max_writes": 0, "max_seconds": 600.0})):
        code, accepted = api.invoke(connection_id, limits=limits)
        assert code == 202 and api.completed(accepted)["request"]["limits"] == expected
    assert api.service.store.connection(connection_id)["scope"] == {
        "exploration_enabled": True, "max_actions": 100, "max_writes": 80}


def test_omitted_invocation_limits_preserve_legacy_request_and_fingerprint(api):
    connection_id = api.connect()
    api.learn(connection_id)
    code, accepted = api.invoke(connection_id, key="legacy")
    assert code == 202
    assert api.completed(accepted)["request"] == {
        "operation_id": "create", "version": 1, "arguments": {"title": "fresh"}}
    with api.service.store._lock:
        row = api.service.store.db.execute(
            "SELECT fingerprint FROM idempotency WHERE connection_id=? AND key='legacy'", (connection_id,)).fetchone()
    legacy_bytes = b'{"arguments":{"title":"fresh"},"operation_id":"create","version":1}'
    assert row["fingerprint"] == hashlib.sha256(legacy_bytes).hexdigest()
    assert api.invoke(connection_id, key="legacy", limits={})[0] == 409


def test_missing_rediscovery_preserves_operations_and_new_support_versions_them(api):
    connection_id = api.connect()
    api.learn(connection_id)
    api.fake.empty_learning = True
    api.learn(connection_id)
    assert api.service.store.operation(connection_id, "create")["status"] == "ACTIVE"
    assert api.service.store.operation(connection_id, "create")["version"] == 1
    api.fake.empty_learning = False
    api.learn(connection_id)
    assert api.fake.settings[-1]["_operation_versions"] == {"create": 1}
    status, active = api.request("GET", f"/v1/connections/{connection_id}/operations")
    assert status == 200 and [item["version"] for item in active["operations"]] == [2]
    status, history = api.request("GET", f"/v1/connections/{connection_id}/operations?include_history=true")
    assert status == 200 and [(item["version"], item["status"]) for item in history["operations"]] == [(2, "ACTIVE"), (1, "SUPERSEDED")]
    assert api.request("GET", f"/v1/connections/{connection_id}/operations/create?version=1")[1]["status"] == "SUPERSEDED"
    assert api.invoke(connection_id, version=1)[0] == 409


def test_explicit_invalidation_preserves_failed_assumption(api):
    connection_id = api.connect()
    api.learn(connection_id)
    api.fake.empty_learning = True
    api.fake.invalidations = [{"id": "create", "version": 1, "status": "WITHDRAWN", "reason": "fake supported assumption was refuted"}]
    api.learn(connection_id)
    retained = api.service.store.operation(connection_id, "create", 1)
    assert retained["status"] == "WITHDRAWN"
    assert retained["status_reason"] == "fake supported assumption was refuted"
    assert api.invoke(connection_id)[0] == 409


def test_stale_result_atomically_blocks_already_queued_invocation(api):
    connection_id = api.connect()
    api.learn(connection_id)
    api.fake.mode = "stale"
    api.fake.release.clear()
    status, first = api.invoke(connection_id, key="stale-first")
    assert status == 202 and api.fake.entered.wait(3)
    status, second = api.invoke(connection_id, "second", key="stale-second")
    assert status == 202
    api.fake.release.set()
    first_job, second_job = api.completed(first), api.completed(second)
    assert first_job["status"] == "COMPLETED" and first_job["result"]["operation_status"] == "STALE"
    assert second_job["status"] == "FAILED" and second_job["result"]["outcome"] == "FAILED_BEFORE_EFFECT"
    assert not second_job["write_intent"] and len(api.fake.invocations) == 1
    assert api.service.store.operation(connection_id, "create", 1)["status"] == "STALE"
    status, retried = api.invoke(connection_id, key="stale-first")
    assert status == 202 and retried["job_id"] == first["job_id"] and retried["deduplicated"]
    assert api.invoke(connection_id, key="new-call")[0] == 409


@pytest.mark.parametrize("mode,outcome,status", [("refuse", "APPLICATION_REFUSAL", "COMPLETED"),
                                               ("raise_before", "FAILED_BEFORE_EFFECT", "FAILED"),
                                               ("raise_after", "UNCERTAIN", "FAILED")])
def test_job_completion_never_invents_confirmed_effect(api, mode, outcome, status):
    connection_id = api.connect(credentials={"username": "onboard-user", "password": "private-onboarding-password"})
    api.learn(connection_id)
    api.fake.mode = mode
    code, accepted = api.invoke(connection_id)
    assert code == 202
    job = api.completed(accepted)
    assert (job["status"], job["result"]["outcome"]) == (status, outcome)
    assert "private-onboarding-password" not in json.dumps(job)


@pytest.mark.parametrize("limits", [None, {"max_actions": 3, "max_writes": 2, "max_seconds": 15}])
def test_restart_fails_queued_work_and_preserves_write_uncertainty_without_replay(tmp_path, limits):
    directory = tmp_path / "service"
    store = ArtifactStore(directory)
    configuration, credentials = connection_request({"url": "http://example.test/", "credentials": {"username": "private-user", "password": "private-password"}})
    connection, connect_job = store.create_connection(configuration, credentials)
    store.start_job(connect_job)
    store.finish_job(connect_job, {"status": "CONNECTED"})
    learn_job = store.queue_job(connection["id"], "learn", {"settings": {}})
    store.start_job(learn_job)
    store.finish_job(learn_job, {"status": "COMPLETE"}, operations=[operation()])
    jobs = {}
    for label in ("queued", "running_no_write", "running_write"):
        job_id, _ = store.queue_invocation(connection["id"], "create", 1, {"title": label}, label, limits)
        jobs[label] = job_id
        if label != "queued":
            store.start_job(job_id)
        if label == "running_write":
            store.add_event(job_id, {"type": "write_intent"})
    store.close()
    api = HTTPHarness(directory)
    try:
        for label, job_id in jobs.items():
            code, job = api.request("GET", "/v1/executions/" + job_id)
            assert code == 200 and job["status"] == "FAILED"
            assert job["result"]["outcome"] == ("UNCERTAIN" if label == "running_write" else "FAILED_BEFORE_EFFECT")
            assert job["request"].get("limits") == limits
        assert api.fake.calls == []
        assert api.service.store.connection(connection["id"])["status"] == "DISCONNECTED"
        code, old = api.invoke(connection["id"], "running_write", key="running_write", limits=limits)
        assert code == 202 and old["job_id"] == jobs["running_write"] and old["deduplicated"]
        if limits is not None:
            assert api.invoke(connection["id"], "running_write", key="running_write",
                              limits={**limits, "max_seconds": 14})[0] == 409
        assert api.fake.invocations == []
        assert api.service.store.operation(connection["id"], "create")["status"] == "ACTIVE"
        code, fresh = api.request("POST", f"/v1/connections/{connection['id']}/reconnect", {})
        assert code == 202 and api.completed(fresh)["status"] == "COMPLETED"
        assert api.fake.sessions[connection["id"]] == credentials
    finally:
        api.close()


@pytest.mark.parametrize('fault', [None, 'new_outcome', 'no_rivals', 'unrepresented',
                                  'actual_no_rivals', 'rejected_edit', 'sibling_changed',
                                  'no_write_budget', 'setup_only_budget', 'no_response_budget',
                                  'terminal_reset', 'terminal_ambiguity'])
def test_authorized_semantic_repair_orchestration_checks_actual_rivals_and_effects(tmp_path, monkeypatch, fault):
    """Diagnostic artifact; real acquisition routing, budgets and observed persistence.

    Opportunity answers are supplied to isolate orchestration, not to claim that
    fitting discovers rivals. HTTP provenance authorization is tested separately.
    """
    import test_operation_runtime as diagnostics
    from semabi.compiler.runtime import Budget, Runtime, StopOperation, Trace
    from semabi.compiler.semantic import SemanticArtifact
    from semabi.compiler.semantic_runtime import acquire_repair

    if fault == 'terminal_reset':
        monkeypatch.setattr(diagnostics._DetailOnlyGuardedSemanticDiagnosticBrowser,
                            'reset_on_final_return', True)
        monkeypatch.setattr(diagnostics, '_GuardedSemanticDiagnosticBrowser',
                            diagnostics._DetailOnlyGuardedSemanticDiagnosticBrowser)

    captured = {}

    def capture(runtime, connection, operation, arguments, emit):
        captured.update(runtime=runtime, operation=operation, arguments=arguments)
        return {'outcome': 'DIAGNOSTIC_SETUP_ONLY'}

    with monkeypatch.context() as setup:
        setup.setattr(Runtime, 'invoke', capture)
        _, browser = diagnostics._semantic_diagnostic(
            tmp_path / 'setup', monkeypatch, guarded=True,
            fault='sibling_changed' if fault == 'sibling_changed' else None,
            response=('Unseen completion',) if fault == 'new_outcome' else ('Recorded',))
    artifact = SemanticArtifact.from_json({})
    opportunities = []
    if fault == 'terminal_ambiguity':
        original_predict = artifact.predict

        def ambiguous_terminal_prediction(*args, **kwargs):
            prediction = original_predict(*args, **kwargs)
            if browser.reloads >= 2:
                prediction.update(status='ambiguous', alternatives={'Recorded': {}, 'Declined': {}})
            return prediction

        artifact.predict = ambiguous_terminal_prediction

    def opportunity(obs, node, *, editable_node=None, value=None):
        proposed = editable_node is not None
        opportunities.append('proposed' if proposed else 'actual')
        blocked = ((proposed and fault in {'no_rivals', 'unrepresented'}) or
                   (not proposed and fault == 'actual_no_rivals'))
        prediction = artifact.predict(obs, node)
        prediction.update(status='ambiguous' if not blocked else 'unestablished',
                          alternatives={'Recorded': {}, 'Declined': {}} if not blocked else {})
        return {'eligible': not blocked,
                'kind': 'unrepresented_edit' if fault == 'unrepresented' else
                        'no_complete_outcome_rivals' if blocked else 'complete_outcome_rivals',
                'prediction': prediction}

    artifact.acquisition_opportunity = opportunity
    if fault == 'rejected_edit':
        original_act = browser.act

        def reject_edit(action):
            result = original_act(action)
            if action.kind == 'type':
                browser.values['A'] = '3'
                browser.draft = None
                browser.surface = browser.detail()
            return result

        browser.act = reject_edit
    max_writes = {'no_write_budget': 0, 'setup_only_budget': 1,
                  'no_response_budget': 2}.get(fault, 20)
    events, trials, edits = [], [], []
    trace = Trace(tmp_path / 'repair', events.append, Budget(30, max_writes))
    report = {'field_write_attempted': False}
    repair = {key: captured[key] for key in ('operation', 'arguments')}
    stopped = fault in {'actual_no_rivals', 'rejected_edit', 'sibling_changed',
                        'no_write_budget', 'setup_only_budget', 'no_response_budget', 'terminal_reset'}
    if stopped:
        with pytest.raises(StopOperation):
            acquire_repair(captured['runtime'], browser, trace, repair, trials, edits, report)
    else:
        witness = acquire_repair(captured['runtime'], browser, trace, repair, trials, edits, report)
        if fault in {'no_rivals', 'unrepresented'}:
            assert witness is None
            assert report['status'] == 'NOT_ENGAGED'
        else:
            assert witness is not None
            assert report['status'] == 'OBSERVED_EXPERIMENT'
            assert browser.values == {'A': '7', 'B': '9'}
            assert len(trials) == len(edits) == 1 and edits[0].get('persisted')
            assert edits[0]['persisted'] == browser.surface.observation.structural_signature()
            if fault == 'terminal_ambiguity':
                terminal = [event for event in events if event['type'] == 'semantic_terminal_target_witness']
                assert terminal[-1]['prediction']['status'] == 'ambiguous'
            if fault == 'new_outcome':
                assert 'Unseen completion' in json.dumps(report['observation'])
                assert trials[0]['after'] != trials[0]['before']
    if fault == 'terminal_reset':
        assert browser.final_return_resets[0] == {'A': '7', 'B': '9'}
        assert browser.values == {'A': '3', 'B': '9'}
        assert browser.reloads == 2
        assert len(edits) == 1 and not edits[0].get('persisted')
        assert report.get('status') != 'OBSERVED_EXPERIMENT'
    if fault in {'no_write_budget', 'setup_only_budget', 'no_rivals', 'unrepresented'}:
        assert browser.fills == browser.final_actions == 0
        assert report['field_write_attempted'] is False
        assert not trials and not edits
    if fault in {'actual_no_rivals', 'rejected_edit', 'no_response_budget'}:
        assert browser.fills == 1 and browser.final_actions == 0
        assert report['field_write_attempted'] is True
        assert not trials and not edits
    if fault == 'rejected_edit':
        assert opportunities == ['proposed']
        assert browser.values['A'] == '3'
    if fault == 'actual_no_rivals':
        assert opportunities == ['proposed', 'actual']
    if fault == 'sibling_changed':
        assert browser.values == {'A': '7', 'B': '7'}
        assert browser.final_actions == 1
        assert edits and not any(edit.get('persisted') for edit in edits)
        assert not any(event['type'] == 'semantic_repair_observed' for event in events)
    # Navigation/selection, failed attempts, and verification are charged too.
    assert trace.budget.writes == len(browser.actions)
    assert trace.budget.actions >= trace.budget.writes
    assert trace.budget.writes <= max_writes
    assert sum(event['type'] == 'write_intent' for event in events) == len(browser.actions)


def _semantic_repair_operation(version=1, *, kind='semantic_guarded_update'):
    """Supplied operation for repair-authorization tests, not learned competence."""
    artifact = operation(version)
    artifact.update(id='guarded', kind=kind,
                    argument_schema={'type': 'object', 'additionalProperties': False,
                                     'properties': {'target': {'type': 'string'}, 'value': {'type': 'string'},
                                                    'expect': {'type': 'string', 'enum': ['Recorded', 'Declined']}},
                                     'required': ['target', 'value', 'expect']})
    return artifact


def _publish_repair_fixture_operation(api, connection_id, artifact):
    job = api.service.store.queue_job(connection_id, 'learn', {})
    assert api.service.store.start_job(job)
    api.service.store.finish_job(job, {'status': 'COMPLETED'}, operations=[artifact])


def _semantic_repair_source(api, connection_id, *, state='COMPLETED', outcome='PREDICTION_UNAVAILABLE',
                            field_witness=False, omit_field_witness=False, kind='semantic_guarded_update',
                            job_kind='invoke'):
    _publish_repair_fixture_operation(api, connection_id, _semantic_repair_operation(kind=kind))
    arguments = {'target': 'A', 'value': '12', 'expect': 'Recorded'}
    if job_kind == 'invoke':
        job, _ = api.service.store.queue_invocation(connection_id, 'guarded', 1, arguments, None)
    else:
        job = api.service.store.queue_job(connection_id, job_kind, {})
    if state != 'QUEUED':
        assert api.service.store.start_job(job)
    if state not in {'QUEUED', 'RUNNING'}:
        result = {'outcome': outcome, 'effect': {} if omit_field_witness else {'field_write_attempted': field_witness}}
        api.service.store.finish_job(job, result, failed=state == 'FAILED')
    return job, arguments


@pytest.mark.parametrize('fault', ['missing', 'foreign', 'queued', 'running', 'failed', 'uncertain',
                                 'wrong_job_kind', 'wrong_operation_kind', 'missing_field_witness',
                                 'numeric_false_witness', 'written_field', 'predicted_refusal',
                                 'no_active_operation', 'changed_argument_schema'])
def test_semantic_repair_rejects_ineligible_execution_provenance(api, fault):
    """HTTP authorization/plumbing only; FakeRuntime never fits or executes here."""
    connection = api.connect()
    source_connection = api.connect() if fault == 'foreign' else connection
    state = {'queued': 'QUEUED', 'running': 'RUNNING', 'failed': 'FAILED'}.get(fault, 'COMPLETED')
    source, _ = _semantic_repair_source(
        api, source_connection, state=state,
        outcome={'uncertain': 'UNCERTAIN', 'predicted_refusal': 'PREDICTED_REFUSAL'}.get(fault, 'PREDICTION_UNAVAILABLE'),
        field_witness=0 if fault == 'numeric_false_witness' else fault == 'written_field',
        omit_field_witness=fault == 'missing_field_witness',
        kind='semantic_action' if fault == 'wrong_operation_kind' else 'semantic_guarded_update',
        job_kind='learn' if fault == 'wrong_job_kind' else 'invoke')
    if fault == 'missing':
        source = 'job_missing'
    if fault in {'no_active_operation', 'changed_argument_schema'}:
        current = _semantic_repair_operation(2)
        if fault == 'no_active_operation':
            job = api.service.store.queue_job(connection, 'learn', {})
            assert api.service.store.start_job(job)
            api.service.store.finish_job(job, {'status': 'COMPLETED'}, invalidations=[
                {'id': 'guarded', 'version': 1, 'status': 'STALE', 'reason': 'diagnostic withdrawal'}])
        else:
            current['argument_schema']['properties']['new_required'] = {'type': 'string'}
            current['argument_schema']['required'].append('new_required')
            _publish_repair_fixture_operation(api, connection, current)
    before = len(api.fake.settings)
    status, _ = api.request('POST', f'/v1/connections/{connection}/learn', {'repair_execution_id': source})
    assert status in {400, 404, 409}, (fault, status)
    assert len(api.fake.settings) == before
    assert api.fake.invocations == []


@pytest.mark.parametrize('max_writes', [0, 1])
def test_semantic_repair_binds_original_objective_to_latest_active_operation_and_limits(api, max_writes):
    """An old result is an objective; explicit republication supplies current authority."""
    connection = api.connect()
    source, arguments = _semantic_repair_source(api, connection)
    latest = _semantic_repair_operation(2)
    _publish_repair_fixture_operation(api, connection, latest)
    status, accepted = api.request('POST', f'/v1/connections/{connection}/learn', {
        'repair_execution_id': source, 'settings': {'max_actions': 6, 'max_writes': max_writes}})
    assert status == 202
    job = api.completed(accepted)
    assert job['status'] == 'COMPLETED', job
    settings = api.fake.settings[-1]
    repair = settings['_semantic_repair']
    assert repair['execution_id'] == source
    assert repair['source_version'] == 1
    assert repair['operation'] == latest
    assert repair['arguments'] == arguments
    assert settings['max_actions'] == 6 and settings['max_writes'] == max_writes
    assert api.fake.invocations == [], 'requesting repair does not dispatch an ordinary invocation'
    assert not job['write_intent'], 'fake learning produced no observations or application writes'


@pytest.mark.parametrize('injection', [
    {'arguments': {'value': '1'}}, {'_semantic_repair': {'arguments': {'value': '1'}}},
    {'settings': {'_semantic_repair': {}}}, {'settings': {'repair_execution_id': 'job_other'}},
    {'settings': {'max_actions': 13}}, {'settings': {'max_writes': 4}},
])
def test_semantic_repair_does_not_accept_injected_objectives_or_expand_scope(api, injection):
    connection = api.connect()
    source, _ = _semantic_repair_source(api, connection)
    status, _ = api.request('POST', f'/v1/connections/{connection}/learn',
                            {'repair_execution_id': source, **injection})
    assert status == 400
    assert api.fake.settings == []


@pytest.mark.parametrize('change', ['republished', 'withdrawn'])
def test_semantic_repair_revalidates_queued_operation_revision_before_learning(api, monkeypatch, change):
    connection = api.connect()
    source, _ = _semantic_repair_source(api, connection)
    queued = []
    enqueue = api.service._enqueue
    monkeypatch.setattr(api.service, '_enqueue', queued.append)
    status, accepted = api.request('POST', f'/v1/connections/{connection}/learn', {'repair_execution_id': source})
    assert status == 202 and queued == [accepted['job_id']]
    if change == 'republished':
        _publish_repair_fixture_operation(api, connection, _semantic_repair_operation(2))
    else:
        job = api.service.store.queue_job(connection, 'learn', {})
        assert api.service.store.start_job(job)
        api.service.store.finish_job(job, {'status': 'COMPLETED'}, invalidations=[
            {'id': 'guarded', 'version': 1, 'status': 'STALE', 'reason': 'diagnostic queued withdrawal'}])
    enqueue(accepted['job_id'])
    job = api.completed(accepted)
    assert job['status'] == 'FAILED', job
    assert job['result']['outcome'] == 'FAILED_BEFORE_EFFECT'
    assert not job['write_intent']
    assert api.fake.settings == []


@pytest.mark.parametrize('prior_state', ['QUEUED', 'RUNNING', 'FAILED_WRITE', 'UNCERTAIN',
                                       'FAILED_BEFORE_EFFECT', 'OBSERVED_EXPERIMENT'])
def test_semantic_repair_fences_pending_and_uncertain_prior_experiments(api, prior_state):
    """Persisted attempts, not client retries, govern duplicate experiment admission."""
    connection = api.connect()
    source, _ = _semantic_repair_source(api, connection)
    prior = api.service.store.queue_job(connection, 'learn', {
        'repair_execution_id': source, 'repair_operation_version': 1,
        'settings': {'max_actions': 6, 'max_writes': 3}})
    if prior_state != 'QUEUED':
        assert api.service.store.start_job(prior)
    if prior_state == 'FAILED_WRITE':
        api.service.store.add_event(prior, {'type': 'write_intent'})
    if prior_state not in {'QUEUED', 'RUNNING'}:
        api.service.store.finish_job(prior, {'repair': {'status': prior_state}},
                                     failed=prior_state in {'FAILED_WRITE', 'FAILED_BEFORE_EFFECT'})
    status, accepted = api.request('POST', f'/v1/connections/{connection}/learn',
                                    {'repair_execution_id': source})
    if prior_state in {'QUEUED', 'RUNNING', 'FAILED_WRITE', 'UNCERTAIN'}:
        assert status == 409
        assert api.fake.settings == []
    else:
        assert status == 202
        assert api.completed(accepted)['status'] == 'COMPLETED'
        assert len(api.fake.settings) == 1


@pytest.mark.parametrize('earlier_failed', [True, False])
def test_semantic_repair_worker_orders_concurrent_admissions_without_repeating_uncertain_write(api, earlier_failed):
    connection = api.connect()
    source, _ = _semantic_repair_source(api, connection)
    request = {'repair_execution_id': source, 'repair_operation_version': 1,
               'settings': {'max_actions': 6, 'max_writes': 3}}
    # Seed the two queued rows that concurrent admission can produce. The real
    # worker must inspect only earlier attempts, never block on later requests.
    first = api.service.store.queue_job(connection, 'learn', request)
    second = api.service.store.queue_job(connection, 'learn', request)
    if earlier_failed:
        assert api.service.store.start_job(first)
        api.service.store.add_event(first, {'type': 'write_intent'})
        api.service.store.finish_job(first, {'outcome': 'UNCERTAIN'}, failed=True)
        selected = second
    else:
        selected = first
    api.service._enqueue(selected)
    completed = api.completed({'job_id': selected})
    if earlier_failed:
        assert completed['status'] == 'FAILED'
        assert completed['result']['outcome'] == 'FAILED_BEFORE_EFFECT'
        assert not completed['write_intent']
        assert api.fake.settings == []
    else:
        assert completed['status'] == 'COMPLETED'
        assert len(api.fake.settings) == 1
        assert api.service.store.job(second)['status'] == 'QUEUED'


@pytest.mark.parametrize('later_log', ['none', 'identical', 'changed_trial', 'ambiguous_unrecorded_step'])
def test_http_relearning_uses_stale_semantic_training_without_replaying_old_procedures(
        tmp_path, monkeypatch, later_log):
    """Real service/runtime recovery; supplied fit result isolates evidence selection.

    Historical artifacts are training provenance only. This test does not induce a
    model or claim browser learning; any browser action during reuse is an error.
    """
    from copy import deepcopy
    from types import SimpleNamespace
    import test_operation_runtime as diagnostics
    from semabi.compiler.browser import Primitive
    from semabi.compiler.evidence import EvidenceLog
    from semabi.compiler.runtime import Runtime
    from semabi.compiler import semantic, semantic_runtime

    browser_calls, captured_settings, fitted_steps, runtimes, acquisition_attempts = [], [], [], [], []

    class NoExplorationBrowser:
        allowed_origin = 'https://synthetic.invalid'

        def __getattr__(self, name):
            if name == 'close':
                return lambda: None
            def prohibited(*args, **kwargs):
                browser_calls.append(name)
                raise AssertionError('historical procedure must not be executed during pure refit')
            return prohibited

    def factory(directory):
        runtime = Runtime(directory)
        original_learn = runtime.learn
        def learn(connection, settings, emit):
            captured_settings.append(deepcopy(settings))
            return original_learn(connection, settings, emit)
        runtime.learn = learn
        runtimes.append(runtime)
        return runtime

    def fit(directory):
        fitted_steps.extend(step.to_json() for step in EvidenceLog(directory).steps)
        return SimpleNamespace(metadata={'fit_seconds': 0}, operations=lambda: [], to_json=lambda: {})

    monkeypatch.setattr(semantic, 'fit_semantics', fit)
    # A scheduling spy isolates ambiguity handling; it supplies no trials or actions.
    monkeypatch.setattr(semantic_runtime, 'acquire', lambda *args: acquisition_attempts.append(True))
    api = HTTPHarness.__new__(HTTPHarness)
    api.fake = SimpleNamespace(release=threading.Event())
    api.service = Service(tmp_path / 'service', runtime_factory=factory)
    try:
        api.server = make_server(api.service, port=0)
    except BaseException:
        api.service.close(timeout=5)
        raise
    api.base = 'http://127.0.0.1:' + str(api.server.server_port)
    api.thread = threading.Thread(target=api.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
    api.thread.start()
    try:
        connections = []
        for _ in range(2):
            connection, job = api.service.store.create_connection({
                'url': NoExplorationBrowser.allowed_origin + '/',
                'scope': {'exploration_enabled': True, 'max_actions': 20, 'max_writes': 10}}, {})
            assert api.service.store.start_job(job)
            api.service.store.finish_job(job, {'status': 'CONNECTED'})
            runtimes[0].sessions[connection['id']] = NoExplorationBrowser()
            connections.append(connection)
        current, foreign = connections
        log = EvidenceLog(runtimes[0].data_dir / current['id'] / 'evidence' / 'prior-onboarding')
        trials = []
        for owner in ('A', 'B'):
            before = diagnostics._semantic_diagnostic_detail(owner, ('Waiting',)).observation
            after = diagnostics._semantic_diagnostic_detail(owner, ('Recorded',)).observation
            step = log.add_step(0, Primitive('click', 2), True, None, before, after)
            trials.append({'before': step.before, 'after': step.after, 'node': 2, 'route': [],
                           'action': {'kind': 'click', 'descriptor': {'role': 'button', 'label': 'Check'}}})
        if later_log == 'ambiguous_unrecorded_step':
            after = log.observations[trials[-1]['after']]
            log.add_step(0, Primitive('reload'), True, None, after, after)
        if later_log != 'none':
            decoy = EvidenceLog(log.dir.parent / 'zz-unrelated-invocation')
            for step in log.steps:
                action = (Primitive('reload') if later_log == 'changed_trial' else
                          Primitive('noop') if later_log == 'ambiguous_unrecorded_step' and step.step == len(log.steps) - 1
                          else deepcopy(step.action))
                decoy.add_step(0, action, True, None,
                               log.observations[step.before], log.observations[step.after])

        def historical(version, status, revision, count, support_trials):
            artifact = operation(version)
            artifact.update(id='semantic-history', kind='semantic_action', status=status,
                            procedure={'return_context': {'entry_shape': 'retained', 'returns': []},
                                       'navigation': [{'must_not_execute': True}]},
                            support={'semantic_artifact': {'metadata': {
                                'representation_revision': revision, 'fitted_steps': count}},
                                     'trials': support_trials, 'edits': []})
            return artifact

        unrelated = operation()
        unrelated['status'] = 'STALE'
        for connection, artifacts in ((current, [unrelated,
                historical(1, 'SUPERSEDED', 'older-reading', 1, trials[:1]),
                historical(2, 'STALE', 'current-reading', len(log.steps), trials)]),
                (foreign, [historical(99, 'ACTIVE', 'foreign-reading', 2, trials)])):
            job = api.service.store.queue_job(connection['id'], 'learn', {})
            assert api.service.store.start_job(job)
            api.service.store.finish_job(job, {'status': 'COMPLETED'}, operations=artifacts)
        assert api.service.store.operations(current['id']) == []
        status, accepted = api.request('POST', f"/v1/connections/{current['id']}/learn",
                                       {'settings': {'max_actions': 20, 'max_writes': 10}})
        assert status == 202
        job = api.completed(accepted)
        assert job['status'] == 'COMPLETED', job
        assert captured_settings[-1]['_existing_operations'] == []
        history = captured_settings[-1].get('_semantic_training_operations', [])
        assert [(item['version'], item['status']) for item in history] == [(2, 'STALE'), (1, 'SUPERSEDED')]
        assert browser_calls == [], 'neither a fresh scan nor an old live procedure is authorized by artifact reuse'
        if later_log == 'ambiguous_unrecorded_step':
            assert fitted_steps == [], 'matching trial rows do not identify the rest of an ambiguous raw history'
            assert acquisition_attempts == [True], 'ambiguous legacy evidence requires authorized acquisition'
            assert job['result']['metrics'].get('reused_training_steps', 0) == 0
        else:
            assert fitted_steps == [step.to_json() for step in log.steps]
            assert acquisition_attempts == []
            assert job['result']['metrics']['reused_training_steps'] == 2
        assert job['result']['metrics']['actions'] == 0
        assert job['result']['operations'] == []
        assert api.service.store.operations(current['id']) == [], 'refit did not reactivate stale procedures'
    finally:
        api.close()


def test_store_has_one_owner_and_operation_publication_is_transactional(tmp_path):
    store = ArtifactStore(tmp_path / "service")
    try:
        with pytest.raises(StoreError, match="already has a service owner"):
            ArtifactStore(tmp_path / "service")
        configuration, credentials = connection_request({"url": "http://example.test/"})
        connection, connect_job = store.create_connection(configuration, credentials)
        store.start_job(connect_job)
        store.finish_job(connect_job, {"status": "CONNECTED"})
        job_id = store.queue_job(connection["id"], "learn", {})
        store.start_job(job_id)
        with pytest.raises(StoreError, match="invalidation"):
            store.finish_job(job_id, {}, operations=[operation()],
                             invalidations=[{"id": "missing", "version": 1, "status": "STALE", "reason": "failed assumption"}])
        assert store.operations(connection["id"], True) == []
        assert store.job(job_id)["status"] == "RUNNING"
        store.finish_job(job_id, {}, operations=[operation()])
        job_id = store.queue_job(connection["id"], "learn", {})
        store.start_job(job_id)
        changed = {**operation(), "name": "changed same version"}
        with pytest.raises(StoreError, match="immutable"):
            store.finish_job(job_id, {}, operations=[changed])
        assert store.operation(connection["id"], "create")["name"] == "FAKE create item"
    finally:
        store.close()


@pytest.mark.parametrize("supplied", [False, True])
def test_example_client_sends_optional_invocation_limits_only_when_requested(tmp_path, monkeypatch, supplied):
    from io import BytesIO
    from pathlib import Path
    import runpy
    import sys

    token_file = tmp_path / "token"
    token_file.write_text("synthetic-client-token")
    requests = []

    def respond(request, **_kwargs):
        body = json.loads(request.data) if request.data is not None else None
        requests.append((request.method, request.full_url, body))
        if request.full_url.endswith("/operations"):
            value = {"operations": [operation()]}
        elif request.full_url.endswith("/invoke"):
            value = {"job_id": "synthetic", "execution_id": "synthetic"}
        else:
            value = {"id": "synthetic", "status": "COMPLETED", "events": [], "result": {"outcome": "CONFIRMED"}}
        return BytesIO(json.dumps(value).encode())

    argv = ["client.py", "--connection", "synthetic", "--reuse-session", "--token-file", str(token_file),
            "--arguments", '{"title":"fresh"}', "--idempotency-key", "synthetic-client"]
    if supplied:
        argv += ["--invoke-max-actions", "4", "--invoke-max-writes", "0", "--invoke-max-seconds", "1.5"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(urllib.request, "urlopen", respond)
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples/client.py"), run_name="__main__")
    invoked = [body for method, url, body in requests if method == "POST" and url.endswith("/invoke")]
    expected = {"version": 1, "arguments": {"title": "fresh"}}
    if supplied:
        expected["limits"] = {"max_actions": 4, "max_writes": 0, "max_seconds": 1.5}
    assert invoked == [expected]


@pytest.mark.parametrize('patch', [{'description': 'Changed through HTTP'}, {}, {'unknown': 'Rejected field'},
                                  {'pinned': False}])
def test_http_partial_text_patch_preserves_schema_and_uses_real_runtime(tmp_path, monkeypatch, patch):
    """Fake connection setup only; the learned artifact and invocation are real Runtime work."""
    import test_operation_runtime as diagnostics
    helper = diagnostics._learn_checkbox_records if 'pinned' in patch else diagnostics._learn_editable_records
    runtime, original_connection, browser, learned = helper(tmp_path / 'runtime', monkeypatch)
    artifact = (diagnostics._checkbox_kind if 'pinned' in patch else diagnostics._learned_kind)(
        learned, 'update_visible_record')
    if 'pinned' in patch:
        browser.rows[0]['Pinned'] = True
    before = deepcopy(browser.rows)
    actions_before = len(browser.actions)
    api = HTTPHarness(tmp_path / 'http')
    try:
        connection, job = api.service.store.create_connection(
            {key: value for key, value in original_connection.items() if key != 'id'}, {})
        assert api.service.store.start_job(job)
        api.service.store.finish_job(job, {'status': 'CONNECTED'})
        runtime.sessions[connection['id']] = browser
        # Delegate the HTTP worker's execution to the actual runtime, rather
        # than the harness's canned effect. No browser onboarding is claimed.
        api.fake.invoke = runtime.invoke
        job = api.service.store.queue_job(connection['id'], 'learn', {})
        assert api.service.store.start_job(job)
        validated = Service._operations({'operations': [artifact]})
        api.service.store.finish_job(job, {'status': 'COMPLETED'}, operations=validated)
        status, catalog = api.request('GET', f"/v1/connections/{connection['id']}/operations")
        assert status == 200
        exposed = next(op for op in catalog['operations'] if op['id'] == artifact['id'])
        assert exposed['argument_schema'] == artifact['argument_schema']
        assert exposed['argument_schema']['required'] == ['target']
        assert exposed['argument_schema']['minProperties'] == 2
        status, accepted = api.request('POST', f"/v1/connections/{connection['id']}/operations/{artifact['id']}/invoke",
                                       {'version': artifact['version'], 'arguments': {'target': before[0]['URL'], **patch}})
        assert status == 202
        result = api.completed(accepted)['result']
        if 'description' in patch or 'pinned' in patch:
            assert result['outcome'] == 'CONFIRMED', result
            assert browser.rows == [{**before[0], **{name.title(): value for name, value in patch.items()}}, before[1]]
            assert result['effect']['requested_changes'] == patch
            assert result['effect']['preserved_values']['title'] == before[0]['Title']
            if 'pinned' in patch:
                assert exposed['argument_schema']['properties']['pinned']['type'] == 'boolean'
                assert result['effect']['witness']['checkbox_readback']['values']['pinned'] is False
        else:
            assert result['outcome'] == 'FAILED_BEFORE_EFFECT', result
            assert browser.rows == before and len(browser.actions) == actions_before
    finally:
        api.close()


@pytest.mark.parametrize('fault', [None, 'wrong_owner', 'sibling_changed', 'stale_operation',
                                 'postaction_owner_changed', 'verification_reload_sibling_changed',
                                 'transient_draft', 'detail_only_final_return_reset', 'incomplete_search'])
def test_http_semantic_invocation_uses_real_runtime_and_independent_application_state(tmp_path, monkeypatch, fault):
    """Supplied artifact setup; actual HTTP queue, Runtime invocation and verification.

    This does not claim browser onboarding or fitting. Unlike FakeRuntime, the
    controlled browser owns mutable application state and never supplies an outcome.
    """
    from types import SimpleNamespace
    import test_operation_runtime as diagnostics
    from semabi.compiler.runtime import Runtime, bind_contract

    if fault == 'detail_only_final_return_reset':
        monkeypatch.setattr(diagnostics._DetailOnlyGuardedSemanticDiagnosticBrowser,
                            'reset_on_final_return', True)
        monkeypatch.setattr(diagnostics, '_GuardedSemanticDiagnosticBrowser',
                            diagnostics._DetailOnlyGuardedSemanticDiagnosticBrowser)

    captured = {}

    def capture_artifact(runtime, connection, artifact, arguments, emit):
        captured.update(connection=connection, artifact=artifact, arguments=arguments)
        return {'outcome': 'ARTIFACT_SETUP_ONLY'}

    # Reuse the existing diagnostic artifact builder without invoking it locally.
    # Restore Runtime.invoke before the service worker is created.
    with monkeypatch.context() as setup:
        setup.setattr(Runtime, 'invoke', capture_artifact)
        _, browser = diagnostics._semantic_diagnostic(
            tmp_path / 'artifact_setup', monkeypatch, guarded=True,
            owner='B' if fault == 'wrong_owner' else None,
            fault=fault if fault in {'sibling_changed', 'transient_draft'} else None)
    browser.close = lambda: None
    if fault == 'incomplete_search':
        from semabi.compiler.semantic import SemanticArtifact
        from semabi.compiler.v4 import consequence, outcome
        import test_v4_outcome as finite
        # Actual finite evidence search; supplied grounding isolates its HTTP
        # preflight consequence, not discovery or a learned relational task.
        model = finite._acquisition_artifact([({'p'}, 'Recorded')] * 3 + [({'q'}, 'Declined')] * 3)
        owner = SimpleNamespace(id=(1, 'A'), tid=1, key='A', node=0,
                                positional=False, attrs={}, refs={})
        state = SimpleNamespace(objs={owner.id: owner}, view={})
        model.prepare = lambda obs: obs
        model.abstract = lambda obs: state
        model.abstractor.parsed = lambda obs: None
        with monkeypatch.context() as grounding:
            grounding.setattr(consequence, '_owner_object', lambda *args: owner)
            grounding.setattr(outcome, 'query_literals', lambda *args: {('feature', 'p')})
            prediction = SemanticArtifact.predict(model, finite._acquisition_page({'p'}), 2, search_budget=0)
        assert prediction['status'] == 'unavailable'
        assert set(prediction['alternatives']) == {'Recorded'}
        assert prediction['alternatives_complete'] is False
        fitted = SemanticArtifact.from_json({})  # Existing diagnostic loader supplies this instance.
        simulate = fitted.simulate_edit

        def exhausted_counterfactual(*args):
            proposed = simulate(*args)
            proposed['prediction'].update({key: prediction[key] for key in
                ('status', 'alternatives', 'alternatives_complete', 'search', 'reason')})
            return proposed

        fitted.simulate_edit = exhausted_counterfactual
    if fault == 'postaction_owner_changed':
        original_act = browser.act

        def switch_postaction_owner(action):
            name = browser.surface.observation.node(action.target).name
            result = original_act(action)
            if name == 'Check':
                browser.selected = 'B'
                browser.surface = browser.detail(('Recorded',))
            return result

        browser.act = switch_postaction_owner
    if fault == 'verification_reload_sibling_changed':
        original_reload = browser.reload

        def reload_with_sibling_effect():
            surface = original_reload()
            browser.values['B'] = '7'
            return surface

        browser.reload = reload_with_sibling_effect
    artifact = captured['artifact']
    if fault == 'stale_operation':
        artifact['support']['policy_version'] = 'obsolete-diagnostic-policy'
        bind_contract(artifact)

    runtimes = []

    def factory(directory):
        runtime = Runtime(directory)
        runtimes.append(runtime)
        return runtime

    api = HTTPHarness.__new__(HTTPHarness)
    api.fake = SimpleNamespace(release=threading.Event())  # close() coordination only
    api.service = Service(tmp_path / 'http_service', runtime_factory=factory)
    try:
        api.server = make_server(api.service, port=0)
    except BaseException:
        api.service.close(timeout=5)
        raise
    api.base = 'http://127.0.0.1:' + str(api.server.server_port)
    api.thread = threading.Thread(target=api.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
    api.thread.start()
    try:
        connection, connect_job = api.service.store.create_connection(
            {key: value for key, value in captured['connection'].items() if key != 'id'}, {})
        assert api.service.store.start_job(connect_job)
        api.service.store.finish_job(connect_job, {'status': 'CONNECTED'})
        runtimes[0].sessions[connection['id']] = browser
        learn_job = api.service.store.queue_job(connection['id'], 'learn', {})
        assert api.service.store.start_job(learn_job)
        unrelated = deepcopy(artifact)
        unrelated['id'] = 'unrelated-supported-operation'
        bind_contract(unrelated)
        api.service.store.finish_job(learn_job, {'status': 'COMPLETED'}, operations=[artifact, unrelated])
        status, accepted = api.request('POST', f"/v1/connections/{connection['id']}/operations/{artifact['id']}/invoke",
                                       {'version': artifact['version'], 'arguments': captured['arguments']},
                                       headers={'Idempotency-Key': 'real-semantic-diagnostic'})
        assert status == 202
        job = api.completed(accepted)
        assert job['status'] == 'COMPLETED', job
        status, execution = api.request('GET', '/v1/executions/' + accepted['execution_id'])
        assert status == 200
        result = execution['result']
        if fault is None:
            assert result['outcome'] == 'CONFIRMED', result
            assert browser.values == {'A': '7', 'B': '9'}
            assert browser.fills == browser.final_actions == 1
        elif fault == 'incomplete_search':
            assert result['outcome'] == 'PREDICTION_UNAVAILABLE', result
            proposed = result['prediction']['prediction']
            assert set(proposed['alternatives']) == {'Recorded'} and not proposed['alternatives_complete']
            assert proposed['search']['checks'] == 0
            assert browser.values == {'A': '3', 'B': '9'}
            assert browser.fills == browser.final_actions == 0
            assert api.service.store.operation(connection['id'], artifact['id'])['status'] == 'ACTIVE'
        elif fault in {'sibling_changed', 'verification_reload_sibling_changed'}:
            assert result['outcome'] == 'UNCERTAIN', result
            assert browser.values == {'A': '7', 'B': '7'}
            assert browser.fills == 1
            assert api.service.store.operation(connection['id'], artifact['id'])['status'] == 'ACTIVE'
        elif fault == 'detail_only_final_return_reset':
            assert browser.final_return_resets[0] == {'A': '7', 'B': '9'}
            assert browser.values == {'A': '3', 'B': '9'}, 'actual terminal target refutes the HTTP update result'
            assert browser.fills == browser.final_actions == 1
            assert browser.reloads == 2
            assert result['outcome'] != 'CONFIRMED', result
        elif fault == 'transient_draft':
            assert result['outcome'] == 'UNCERTAIN', result
            assert browser.values == {'A': '3', 'B': '9'}, 'independent application state refutes persistence'
            assert browser.fills == browser.final_actions == 1
            assert result['operation_status'] == 'STALE'
            assert api.service.store.operation(connection['id'], artifact['id'])['status'] == 'STALE'
            assert api.service.store.operation(connection['id'], unrelated['id'])['status'] == 'ACTIVE'
            writes_before = browser.fills, browser.final_actions
            status, _ = api.request('POST', f"/v1/connections/{connection['id']}/operations/{artifact['id']}/invoke",
                                    {'version': artifact['version'], 'arguments': captured['arguments']},
                                    headers={'Idempotency-Key': 'new-request-after-persistence-refutation'})
            assert status == 409 and (browser.fills, browser.final_actions) == writes_before
        elif fault == 'postaction_owner_changed':
            assert result['outcome'] == 'UNCERTAIN', result
            assert browser.values == {'A': '7', 'B': '9'}
            assert browser.selected == 'B'
            assert browser.fills == browser.final_actions == 1
            assert result['operation_status'] == 'STALE'
        else:
            assert result['outcome'] != 'CONFIRMED', result
            assert browser.values == {'A': '3', 'B': '9'}
            assert browser.fills == browser.final_actions == 0
            assert result['operation_status'] == 'STALE'
            status, _ = api.request('POST', f"/v1/connections/{connection['id']}/operations/{artifact['id']}/invoke",
                                    {'version': artifact['version'], 'arguments': captured['arguments']},
                                    headers={'Idempotency-Key': 'new-request-after-suspension'})
            assert status == 409
    finally:
        api.close()
