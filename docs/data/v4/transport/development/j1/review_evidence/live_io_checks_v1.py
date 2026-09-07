"""Independent invented-record checks of the exact reviewed live_io source."""
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
import socket
import sys
import tempfile
import threading
import uuid

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'docs/data/v4/transport/development/j1/live_io.py'
CONTRACT = ROOT / 'docs/data/v4/transport/development/j1/live_contract_v1.md'
CONTRACT_SHA = 'f9642c36b3581323eaa8206d5117dd7831c2d57cf6142b39877fd0e2fbc17d90'
rows = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name, function, reject=False):
    try:
        detail = function()
        rows.append({'name': name, 'status': 'FAIL' if reject else 'PASS',
                     'expected': 'reject' if reject else 'accept', 'detail': detail})
    except Exception as error:
        rows.append({'name': name, 'status': 'PASS' if reject else 'FAIL',
                     'expected': 'reject' if reject else 'accept',
                     'exception': type(error).__name__, 'detail': str(error)})


def assert_true(condition, detail):
    if not condition:
        raise AssertionError(detail)


def clone(value):
    return copy.deepcopy(value)


def changed(value, path, replacement):
    value = clone(value)
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement
    return value


class Stream:
    def __init__(self, stream, events, failure=None):
        self.stream, self.events, self.failure = stream, events, failure

    def tell(self):
        return self.stream.tell()

    def write(self, raw):
        self.events.append('write')
        return self.stream.write(raw[:len(raw) // 2] if self.failure == 'partial_write' else raw)

    def flush(self):
        self.events.append('flush')
        if self.failure == 'flush':
            raise OSError('invented flush failure')
        return self.stream.flush()

    def fileno(self):
        return self.stream.fileno()

    def close(self):
        return self.stream.close()


def native_symbols(path, names, namespace):
    tree = ast.parse(path.read_text())
    selected = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names]
    assert_true({node.name for node in selected} == set(names), 'Native AST inventory differs')
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert_true(not args.output.exists(), 'Exclusive review output exists')
    assert_true(sha(SOURCE) == args.source_sha and sha(CONTRACT) == CONTRACT_SHA, 'Reviewed source/contract changed')
    spec = importlib.util.spec_from_file_location('_independent_j1_live_io', SOURCE)
    io = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(io)
    native_paths = [ROOT / 'semabi/compiler/observation.py', ROOT / 'semabi/compiler/browser.py', ROOT / 'scripts/transport_collect.py']
    source_hashes = {str(path.relative_to(ROOT)): sha(path) for path in [SOURCE, CONTRACT, Path(__file__), *native_paths]}
    obs = {'url': 'http://127.0.0.1/invented', 'nodes': [
        {'i': 0, 'parent': -1, 'role': 'group', 'name': 'Panel', 'bbox': [0, 0, 80, 60]},
        {'i': 1, 'parent': 0, 'role': 'button', 'name': 'Apply', 'placeholder': None, 'bbox': [1, 1, 20, 10]}]}
    primitive = {'kind': 'click', 'target': 1, 'text': None, 'target_desc': None}
    request = io.forecast_request(obs, primitive)
    response = {'instrument_status': 'COMPLETE', 'category': 'INVENTED_FORECAST', 'value': ['unused']}
    provenance = {'source': args.source_sha, 'training': 'invented-only'}
    check('public_descriptor_matches_browser', lambda: assert_true(request['primitive']['target_desc'] == {'role': 'button', 'name': 'Apply', 'placeholder': None}, 'Descriptor differs'))
    check('request_copy_does_not_mutate_inputs', lambda: assert_true(primitive['target_desc'] is None and request['observation'] == obs and request['observation'] is not obs, 'Input mutation or alias'))
    for kind in sorted(io.KINDS):
        p = clone(primitive); p['kind'] = kind
        if kind not in {'click', 'type', 'select'}:
            p['target'] = None
        check('kind_' + kind, lambda p=p: io.validate_request(io.forecast_request(obs, p)))
    for value in (None, '', 'visible value', True, False, 0, 7, -2, 1.25):
        p = changed(primitive, ['text'], value)
        check('attempted_text_' + repr(value), lambda p=p: assert_true(io.forecast_request(obs, p)['primitive']['text'] == p['text'] and type(io.forecast_request(obs, p)['primitive']['text']) is type(p['text']), 'Scalar changed'))
    for name, pre, p in [('unresolved_target', obs, None), ('initial_unobserved_reset', None, {'kind': 'reset', 'target': None, 'text': '0', 'target_desc': None}), ('null_prestate_null_primitive', None, None)]:
        check(name, lambda pre=pre, p=p: io.validate_request(io.forecast_request(pre, p)))
    for operation in ('checkpoint', 'shutdown'):
        check(operation, lambda operation=operation: io.validate_request(io.control_request(operation)))
    mutations = [
        ('forbidden_case', ['case'], 'sealed-case'), ('forbidden_profile', ['profile'], 'permuted'),
        ('forbidden_observation_key', ['observation', 'expected'], 'answer'),
        ('forbidden_node_key', ['observation', 'nodes', 1, 'oracle'], 1),
        ('forbidden_primitive_key', ['primitive', 'scope'], {'name': 'hidden'}),
        ('unknown_operation', ['op'], 'score'), ('uuid_not_opaque', ['request_id'], 'case-one'),
        ('uuid_wrong_version', ['request_id'], str(uuid.uuid1())),
        ('negative_target', ['primitive', 'target'], -1), ('bool_target', ['primitive', 'target'], True),
        ('float_target', ['primitive', 'target'], 1.0), ('target_out_of_range', ['primitive', 'target'], 2),
        ('node_index_mismatch', ['observation', 'nodes', 1, 'i'], 0),
        ('bool_node_index', ['observation', 'nodes', 1, 'i'], True),
        ('invalid_parent', ['observation', 'nodes', 1, 'parent'], 7),
        ('negative_parent', ['observation', 'nodes', 1, 'parent'], -2),
        ('bool_parent', ['observation', 'nodes', 1, 'parent'], False),
        ('self_parent_cycle', ['observation', 'nodes', 1, 'parent'], 1),
        ('two_node_cycle', ['observation', 'nodes', 0, 'parent'], 1),
        ('bool_bbox', ['observation', 'nodes', 1, 'bbox', 0], True),
        ('short_bbox', ['observation', 'nodes', 1, 'bbox'], [1, 2, 3]),
        ('nonfinite_bbox', ['observation', 'nodes', 1, 'bbox', 0], float('inf')),
        ('nested_options', ['observation', 'nodes', 1, 'options'], [['secret']]),
        ('nonboolean_checked', ['observation', 'nodes', 1, 'checked'], 1),
        ('nontext_node', ['observation', 'nodes', 1, 'name'], 7),
        ('descriptor_disagrees', ['primitive', 'target_desc', 'name'], 'Elsewhere'),
        ('descriptor_extra_key', ['primitive', 'target_desc', 'scope'], 'hidden'),
        ('nonscalar_text', ['primitive', 'text'], ['formula']),
        ('nonfinite_text', ['primitive', 'text'], float('nan')),
        ('target_without_observation', ['observation'], None),
    ]
    for name, path, value in mutations:
        check(name, lambda path=path, value=value: io.validate_request(changed(request, path, value)), reject=True)
    check('unresolved_descriptor_not_forwarded', lambda: io.forecast_request(obs, {'kind': 'click', 'target': None, 'text': 'unseen', 'target_desc': {'role': 'button', 'name': 'Unseen'}}), reject=True)
    check('conflicting_descriptor_not_overwritten', lambda: io.forecast_request(obs, changed(primitive, ['target_desc'], {'role': 'button', 'name': 'Wrong', 'placeholder': None})), reject=True)
    check('targeted_null_index_requires_null_primitive', lambda: io.forecast_request(obs, changed(primitive, ['target'], None)), reject=True)
    for name, raw in [('duplicate_top_key', b'{"op":1,"op":2}'), ('duplicate_nested_key', b'{"node":{"name":"a","name":"b"}}'), ('nan_literal', b'{"x":NaN}'), ('infinity_literal', b'{"x":Infinity}'), ('trailing_json', b'{}{}')]:
        check(name, lambda raw=raw: io.parse_json(raw), reject=True)
    check('overflow_number_rejected_by_schema', lambda: io.validate_request(io.parse_json(io.json_bytes(request).replace(b'"bbox":[0,0,80,60]', b'"bbox":[0,0,1e999,60]'))), reject=True)
    check('control_message_cannot_carry_semantics', lambda: io.validate_request({**io.control_request('checkpoint'), 'observation': obs}), reject=True)

    with tempfile.TemporaryDirectory(prefix='j1_live_io_review_') as temporary:
        directory = Path(temporary)
        ledger = io.Ledger(directory / 'ledger.jsonl')
        events = []
        ledger.stream = Stream(ledger.stream, events)
        original_fsync = io.os.fsync
        def observed_fsync(fd):
            events.append('fsync')
            return original_fsync(fd)
        io.os.fsync = observed_fsync
        try:
            ack = ledger.append(request, response, provenance)
            events.append('ack_returned')
        finally:
            io.os.fsync = original_fsync
        check('ledger_flush_fsync_before_ack', lambda: assert_true(events == ['write', 'flush', 'fsync', 'ack_returned'], 'Ordering differs: ' + repr(events)))
        check('receipt_roundtrip', lambda: assert_true(io.verify_receipt(ledger.path, ack, request)['request'] == request, 'Request differs'))
        before = ledger.path.read_bytes()
        check('duplicate_append_rejected_without_write', lambda: ledger.append(request, response, provenance), reject=True)
        check('duplicate_did_not_append', lambda: assert_true(ledger.index == 1 and ledger.path.read_bytes() == before, 'Duplicate wrote data'))
        callback_count = 0
        def duplicate_before_callback():
            nonlocal callback_count
            ledger.validate_next(request)
            callback_count += 1
        check('caller_validate_next_rejects_duplicate_before_callback', duplicate_before_callback, reject=True)
        check('duplicate_callback_count_zero', lambda: assert_true(callback_count == 0, 'Duplicate reached callback'))
        for name, key, value in [('ack_wrong_id', 'request_id', str(uuid.uuid4())), ('ack_bool_index', 'receipt_index', True), ('ack_zero_index', 'receipt_index', 0), ('ack_wrong_index', 'receipt_index', 2), ('ack_wrong_offset', 'offset', 1), ('ack_short_length', 'length', ack['length'] - 1), ('ack_large_length', 'length', ack['length'] + 1), ('ack_bad_hash', 'record_sha256', '0' * 64), ('ack_bad_status', 'instrument_status', 'PASS'), ('ack_extra_key', 'case', 'hidden')]:
            check(name, lambda key=key, value=value: io.verify_receipt(ledger.path, {**ack, key: value}, request), reject=True)
        original_record = io.parse_json(before)
        for name, record_index in [('record_bool_index_must_reject', True), ('record_float_index_must_reject', 1.0), ('record_wrong_integer_index', 2)]:
            altered = {**original_record, 'receipt_index': record_index}
            raw = io.json_bytes(altered); path = directory / (name + '.jsonl'); path.write_bytes(raw)
            altered_ack = {**ack, 'offset': 0, 'length': len(raw), 'record_sha256': io.digest(raw)}
            check(name, lambda path=path, altered_ack=altered_ack: io.verify_receipt(path, altered_ack, request), reject=True)
        for name, raw in [('partial_record', before[:-1]), ('noncanonical_record', b' ' + before)]:
            path = directory / (name + '.jsonl'); path.write_bytes(raw)
            altered_ack = {**ack, 'length': len(raw), 'record_sha256': io.digest(raw)}
            check(name, lambda path=path, altered_ack=altered_ack: io.verify_receipt(path, altered_ack, request), reject=True)
        other = io.forecast_request(obs, primitive)
        check('ack_cannot_authenticate_other_request', lambda: io.verify_receipt(ledger.path, {**ack, 'request_id': other['request_id']}, other), reject=True)
        ledger.close()

        for failure in ('partial_write', 'flush', 'fsync'):
            failed = io.Ledger(directory / (failure + '.jsonl')); failure_events = []
            failed.stream = Stream(failed.stream, failure_events, failure)
            if failure == 'fsync':
                io.os.fsync = lambda _fd: (_ for _ in ()).throw(OSError('invented fsync failure'))
            try:
                check(failure + '_prevents_ack', lambda failed=failed: failed.append(request, response, provenance), reject=True)
            finally:
                io.os.fsync = original_fsync
            check(failure + '_breaks_ledger', lambda failed=failed: assert_true(failed.broken and failed.index == 0 and not failed.seen, 'Failure continued as success'))
            check(failure + '_prevents_next_callback_obligation', lambda failed=failed: failed.validate_next(other), reject=True)
            failed.close()

        def ipc(lost_ack=False):
            ipc_name = 'lost_ack' if lost_ack else 'real_ipc'
            path = directory / (ipc_name + '.sock'); log = io.Ledger(directory / (ipc_name + '.jsonl'))
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); listener.bind(str(path)); listener.listen(1); listener.settimeout(2)
            server_errors = []; chronology = []
            def serve():
                try:
                    connection, _ = listener.accept()
                    with connection:
                        wire = connection.makefile('rb').readline(); given = io.parse_json(wire)
                        log.validate_next(given); chronology.append('validated_before_callback')
                        receipt = log.append(given, response, provenance); chronology.append('durable_append_returned')
                        if not lost_ack:
                            connection.sendall(io.json_bytes(receipt)); chronology.append('ack_sent')
                except Exception as error:
                    server_errors.append(type(error).__name__ + ': ' + str(error))
                finally:
                    listener.close()
            thread = threading.Thread(target=serve); thread.start()
            client_error = None; result = None
            try:
                result = io.Client(path, log.path, timeout=2).request(io.forecast_request(obs, primitive))
            except Exception as error:
                client_error = type(error).__name__ + ': ' + str(error)
            finally:
                thread.join(3); log.close()
            assert_true(not thread.is_alive() and not server_errors, 'Owned IPC server failed or not reaped: ' + repr(server_errors))
            assert_true(log.index == 1 and log.path.read_bytes().endswith(b'\n'), 'Durable opportunity missing')
            if lost_ack:
                assert_true(result is None and client_error is not None, 'Lost ACK was treated as success')
            else:
                assert_true(result is not None and client_error is None and chronology == ['validated_before_callback', 'durable_append_returned', 'ack_sent'], 'IPC ordering failed')
            return {'chronology': chronology, 'client_error': client_error, 'durable_records': log.index}
        check('actual_local_unix_ipc', ipc)
        check('lost_ack_preserves_opportunity_without_client_success', lambda: ipc(True))

        namespace = {'dataclass': dataclass, 'field': field, 'hashlib': hashlib, 'json': json, 'Path': Path, 'Counter': Counter}
        native_symbols(native_paths[0], {'Node', 'Observation'}, namespace)
        native_symbols(native_paths[1], {'Primitive', 'ActionResult'}, namespace)
        native_symbols(native_paths[2], {'Recorder'}, namespace)
        browser_tree = ast.parse(native_paths[1].read_text())
        browser_class = next(n for n in browser_tree.body if isinstance(n, ast.ClassDef) and n.name == 'Browser')
        browser_act = next(n for n in browser_class.body if isinstance(n, ast.FunctionDef) and n.name == 'act')
        exec(compile(ast.Module(body=[browser_act], type_ignores=[]), str(native_paths[1]), 'exec'), namespace)
        observation = namespace['Observation'].from_json(obs)
        class FakeLog:
            def __init__(self): self.steps = []
            def add_observation(self, page): return page.structural_signature()
            def add_step(self, episode, primitive, ok, error, before, after):
                step = SimpleNamespace(step=len(self.steps), before=self.add_observation(before), after=self.add_observation(after))
                self.steps.append(step); return step
        class FakeBrowser:
            def __init__(self): self._last_obs = observation; self.n_primitives = 0; self.step_hooks = []; self.episode = 1
            def observe(self): return observation
            def _handle(self, _target):
                def fill(text, **_kwargs):
                    if type(text) is not str: raise TypeError('invented browser requires text')
                return SimpleNamespace(fill=fill, click=lambda **_kwargs: None)
            def act(self, primitive): return namespace['act'](self, primitive)
        def native_scalar_failure():
            browser = FakeBrowser(); recorder = namespace['Recorder'](browser, FakeLog(), directory / 'native_decisions.jsonl')
            p = namespace['Primitive']('type', 1, True)
            sent = io.forecast_request(obs, {'kind': p.kind, 'target': p.target, 'text': p.text, 'target_desc': p.target_desc})
            recorder.act(observation, p, {'receipt': 'invented-durable-prior-receipt'})
            decision = json.loads(recorder.decisions_path.read_text())
            assert_true(decision['charged_attempt'] == 1 and decision['ok'] is False and decision['action']['text'] is True and recorder.failures == 1, 'Native charged scalar failure changed')
            assert_true(p.target_desc == sent['primitive']['target_desc'], 'Native Browser descriptor differs from pre-action payload')
            return {'charged_attempt': decision['charged_attempt'], 'ok': decision['ok'], 'attempted_text': decision['action']['text'], 'error': decision['error']}
        check('unchanged_native_recorder_preserves_browser_scalar_rejection', native_scalar_failure)
    assert_true(all(sha(ROOT / name) == digest for name, digest in source_hashes.items()), 'A reviewed source changed during checks')
    result = {'schema': 'semabi.j1.live_io_independent_checks.v1', 'status': 'PASS' if all(row['status'] == 'PASS' for row in rows) else 'FAIL',
              'source_sha256': args.source_sha, 'sources': source_hashes, 'checks': rows,
              'counts': dict(Counter(row['status'] for row in rows)),
              'scope': 'Invented plain JSON, temporary local files, fake native Browser/Recorder AST and two owned local Unix socket exchanges only. No fit, browser, fixture or sealed payload.'}
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps({'path': str(args.output), 'sha256': sha(args.output), 'status': result['status'], 'counts': result['counts'], 'failed': [row['name'] for row in rows if row['status'] == 'FAIL']}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
