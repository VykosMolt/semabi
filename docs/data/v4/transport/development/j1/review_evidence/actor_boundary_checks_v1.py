"""Independent actor lifecycle and authentic entrypoint routing controls."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
import argparse
import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import traceback

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
ACTOR = HERE.parent / 'act.py'
CORE_SHA = 'f14ba9073873c99ff24b889e89805fda0b862cb87e11124e0047cf71c0330006'
IO_SHA = '2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327'
CONTRACT_SHA = 'f9642c36b3581323eaa8206d5117dd7831c2d57cf6142b39877fd0e2fbc17d90'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def require(condition, detail):
    if not condition: raise AssertionError(detail)
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + '\n')


def imported(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); sys.modules[name] = value
    spec.loader.exec_module(value); return value


def construct(actor, core, root, conflict, close_failure=False):
    root.mkdir(); events = []; ns, Browser, Log, page = core.build_native(events)
    browser = Browser(); original_close = browser.close
    if close_failure:
        def close():
            original_close(); raise OSError('invented browser close failure')
        browser.close = close
    state = actor.ActorState(None, {}); collector = SimpleNamespace(Recorder=ns.Recorder)
    original = collector.Recorder; state.instrument(collector)
    (root / conflict).write_bytes(b'preexisting immutable bytes\n')
    try:
        collector.Recorder(browser, Log(), root / 'decisions.jsonl')
        raise AssertionError('Recorder constructor accepted occupied artifact')
    except FileExistsError:
        pass
    require(browser.closed, 'Constructor failure did not close browser')
    recorder = state.recorders[0]
    require(recorder.initialization_error.startswith('FileExistsError:'), 'Original construction error lost')
    require(all(stream is None or stream.closed for stream in (recorder.receipts, recorder.reconciliations)), 'Constructor leaked owned stream')
    require((root / conflict).read_bytes() == b'preexisting immutable bytes\n', 'Existing artifact changed')
    if close_failure: require(any('invented browser close failure' in e for e in state.cleanup_errors), 'Cleanup error omitted')
    state.close(); require(collector.Recorder is original, 'Constructor class not restored')
    return {'browser_closed': browser.closed, 'initialization_error': recorder.initialization_error,
            'cleanup_errors': state.cleanup_errors}


def closing(actor, nested=False, loader=False):
    events = []
    class Native: pass
    collector = SimpleNamespace(Recorder=Native)
    state = actor.ActorState(None, {})
    class Stream:
        def __init__(self, name, fail=False): self.name, self.fail = name, fail
        def close(self):
            events.append(self.name)
            if self.fail: raise OSError('invented stream close failure')
    if nested:
        state.instrument(collector); state.instrument(collector); state.close()
        require(collector.Recorder is Native, 'Repeated instrumentation left wrapper installed')
    else:
        original_loader = lambda: collector
        scoped = SimpleNamespace(_load_collector=original_loader)
        def prepare():
            state.recorders.append(SimpleNamespace(receipts=Stream('first', True), reconciliations=Stream('second')))
        try:
            if loader:
                with actor.recorder_loader(scoped, state):
                    scoped._load_collector(); prepare()
            else:
                state.instrument(collector); prepare(); state.close()
            raise AssertionError('Close failure did not propagate')
        except OSError as error:
            require(str(error) == 'invented stream close failure', 'Wrong close error')
        require(events == ['first', 'second'], 'Close failure prevented later cleanup')
        require(collector.Recorder is Native, 'Close failure left wrapper installed')
        require(scoped._load_collector is original_loader, 'Loader hook leaked after close failure')
    return {'events': events, 'cleanup_errors': state.cleanup_errors, 'original_class_restored': True}


def tree(actor, root):
    actor.ROOT = root; actor.HERE = root / 'docs/data/v4/transport/development/j1'
    actor.subprocess = SimpleNamespace(check_output=lambda *a, **k: 'invented-head\n')
    for name in actor.VERIFICATION_FILES:
        target = root / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((ROOT / name).read_bytes())
    collection = actor.HERE / 'invented_collection.json'; predictor = actor.HERE / 'invented_predictor.json'
    write(collection, {'files': {'semabi/compiler/browser.py': sha(root / 'semabi/compiler/browser.py')}})
    write(predictor, {'source_head': 'invented-head'})
    manifest = {'schema': 'semabi.j1.actor_freeze.v1', 'source_head': 'invented-head',
                'verification_files': {name: sha(root / name) for name in actor.VERIFICATION_FILES},
                'collector_freeze': {'path': str(collection.relative_to(root)), 'sha256': sha(collection)},
                'predictor_freeze': {'path': str(predictor.relative_to(root)), 'sha256': sha(predictor)}}
    path = actor.HERE / 'invented_actor.json'; write(path, manifest)
    return SimpleNamespace(root=root, manifest=manifest, path=path, collection=collection, predictor=predictor)


def manifest_case(actor, root, mutation):
    saved = actor.ROOT, actor.HERE, actor.subprocess
    try:
        item = tree(actor, root)
        if mutation is not None: mutation(item)
        write(item.path, item.manifest)
        return actor.verify_actor(item.path, item.collection)
    finally:
        actor.ROOT, actor.HERE, actor.subprocess = saved


def alter_reference(item, value): item.manifest['predictor_freeze']['path'] = value


def ready_case(actor, root, mutation):
    root.mkdir(); ledger = root / 'forecasts.jsonl'; ledger.touch(); connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock = root / 'owned.sock'; connection.bind(str(sock))
    verification = {'source_head': 'invented-head', 'predictor_freeze': {'sha256': 'a' * 64}}
    value = {'schema': 'semabi.j1.predictor_ready.v1', 'status': 'READY', 'pid': 1,
             'ledger_path': str(ledger), 'socket_path': str(sock),
             'provenance': {'source_head': 'invented-head', 'runtime_freeze_sha256': 'a' * 64,
                            'fit': 'invented-resident-fit', 'training': 'invented-training'}}
    item = SimpleNamespace(root=root, ledger=ledger, socket=sock, ready=value)
    try:
        if mutation is not None: mutation(item)
        write(root / 'ready.json', value)
        ready, binding = actor.read_ready(root, verification)
        require(ready == value and binding['sha256'] == sha(root / 'ready.json'), 'Ready binding changed')
        return {'ready_bound': True}
    finally: connection.close()


def integrated(actor, core, root):
    root.mkdir(); events = []; ns, Browser, Log, page = core.build_native(events)
    browsers = []
    class TrackedBrowser(Browser):
        def __init__(self, *args): super().__init__(*args); browsers.append(self)
    base = ModuleType('_invented_native_collector')
    base.__dict__.update(vars(ns)); base.__dict__.update(
        argparse=argparse, datetime=datetime, timezone=timezone, os=os, subprocess=subprocess,
        sys=sys, traceback=traceback, ROOT=ROOT, Browser=TrackedBrowser, EvidenceLog=Log,
        __doc__='Exact native entrypoint functions over invented public input and fake browser/log')
    core.native_symbols(ROOT / 'scripts/transport_collect.py',
        {'Recorder', 'resolve', 'stamp', 'digest', 'write', 'verify_freeze', 'collect_script', 'main'}, base.__dict__)
    scoped = imported('_reviewed_j1_scoped_for_actor', HERE.parent / 'collect.py')
    original_loader = lambda: base
    scoped._load_collector = original_loader; original_recorder, original_resolve = base.Recorder, base.resolve
    actual_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    fake_root = root / 'public_source_copy'; saved = actor.ROOT, actor.HERE, actor.subprocess, actor._module, actor.io.Client
    connection = None; client = None
    try:
        item = tree(actor, fake_root)
        actor.subprocess = SimpleNamespace(check_output=lambda *a, **k: actual_head + '\n')
        item.manifest['source_head'] = actual_head
        write(item.predictor, {'source_head': actual_head})
        item.manifest['predictor_freeze']['sha256'] = sha(item.predictor)
        collection = {'files': {'semabi/compiler/browser.py': sha(ROOT / 'semabi/compiler/browser.py')},
                      'verification_files': {name: sha(ROOT / name) for name in scoped.VERIFICATION_FILES}}
        write(item.collection, collection); item.manifest['collector_freeze']['sha256'] = sha(item.collection)
        write(item.path, item.manifest)
        predictor = root / 'resident'; predictor.mkdir()
        provenance = {'source_head': actual_head, 'runtime_freeze_sha256': sha(item.predictor),
                      'fit': 'same-invented-fit', 'training': 'invented-training'}
        client = core.LocalClient(actor.io, predictor, provenance, events)
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        socket_path = root / 'owned.sock'; connection.bind(str(socket_path))
        write(predictor / 'ready.json', {'schema': 'semabi.j1.predictor_ready.v1', 'status': 'READY', 'pid': os.getpid(),
              'socket_path': str(socket_path), 'ledger_path': str(client.ledger_path), 'provenance': provenance})
        actor.io.Client = lambda socket_name, ledger_name: client
        actor._module = lambda name, path: scoped
        script = root / 'invented_script.json'
        scope = {'role': 'group', 'name': 'Panel', 'exact': True}
        write(script, {'cases': [{'case': 'invented-evaluator-case', 'family': 'invented-evaluator-family',
               'target_action_index': 0, 'script': [
               {'kind': 'snapshot'}, {'kind': 'click', 'role': 'button', 'name': 'Apply', 'exact': True, 'scope': scope},
               {'kind': 'click', 'role': 'button', 'name': 'Missing', 'exact': True, 'scope': scope}]}]})
        output = root / 'run'
        result = actor.main(['--actor-freeze', str(item.path), '--predictor-dir', str(predictor), 'script',
                             '--freeze', str(item.collection), '--out', str(output), '--script', str(script),
                             '--url', 'http://127.0.0.1/invented', '--reset-url', '/invented-reset'])
        run = json.loads((output / 'run.json').read_text()); verification = json.loads((output / 'actor_verification.json').read_text())
        collection_result = json.loads((output / 'collector_verification.json').read_text())
        decisions = [json.loads(line) for line in (output / 'decisions.jsonl').read_text().splitlines()]
        require(result is None and run['status'] == 'FINISHED' and run['complete'] is False, 'Native failed completion was hidden')
        require(run['charged_attempts'] == 4 and run['failed_attempts'] == 1 and run['paired_steps_recorded'] == 3, 'Native full-script accounting differs')
        require(verification['status'] == collection_result['status'] == 'PASS', 'Actual actor/scoped entrypoints did not complete')
        require(len(verification['accounting']) == 1 and len(verification['accounting'][0]['intents']) == 4, 'One retained Recorder not used')
        require(all(v['state'] == 'MATCHED' for v in verification['accounting'][0]['intents']), 'Integrated invocation left orphan')
        require(len(client.requests) == 4 and client.requests[-1]['primitive'] is None, 'Unresolved scoped target did not use null primitive')
        require(all(set(v) == {'schema', 'op', 'request_id', 'observation', 'primitive'} for v in client.requests), 'Evaluator metadata crossed predictor boundary')
        require(decisions[2]['requested']['scope_resolution']['status'] == 'resolved' and decisions[3]['requested']['scope_resolution']['status'] == 'failed', 'Scoped resolver bypassed')
        require(all(browser.closed for browser in browsers), 'Retained collector browser not closed')
        require(base.Recorder is original_recorder and base.resolve is original_resolve and scoped._load_collector is original_loader, 'Scoped/actor hooks leaked')
        return {'native_run': {key: run[key] for key in ('status', 'complete', 'charged_attempts', 'failed_attempts', 'paired_steps_recorded')},
                'actor_status': verification['status'], 'collector_status': collection_result['status'],
                'request_count': len(client.requests), 'browser_closed': True, 'hooks_restored': True,
                'raw_decisions': decisions, 'requests': client.requests}
    finally:
        actor.ROOT, actor.HERE, actor.subprocess, actor._module, actor.io.Client = saved
        if connection is not None: connection.close()
        if client is not None: client.ledger.close()


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False); parser.add_argument('--actor-sha', required=True); parser.add_argument('--output', required=True, type=Path); args = parser.parse_args()
    require(not args.output.exists(), 'Exclusive output exists')
    require(sha(ACTOR) == args.actor_sha and sha(HERE / 'actor_core_checks_v1.py') == CORE_SHA and sha(ACTOR.parent / 'live_io.py') == IO_SHA and sha(ACTOR.parent / 'live_contract_v1.md') == CONTRACT_SHA, 'Reviewed source changed')
    actor = imported('_reviewed_j1_actor_boundary', ACTOR); core = imported('_reviewed_actor_core_helpers', HERE / 'actor_core_checks_v1.py')
    sources = {str(p.relative_to(ROOT)): sha(p) for p in [ACTOR, HERE / 'actor_core_checks_v1.py', Path(__file__), HERE.parent / 'collect.py', HERE.parent / 'live_io.py', HERE.parent / 'live_contract_v1.md', ROOT / 'scripts/transport_collect.py', ROOT / 'semabi/compiler/browser.py', ROOT / 'semabi/compiler/observation.py', ROOT / 'semabi/compiler/evidence.py']}
    rows = []
    def check(name, function, reject=False):
        try:
            value = function(); passed = not reject
            rows.append({'name': name, 'expected': 'reject' if reject else 'accept', 'status': 'PASS' if passed else 'FAIL', 'result': value})
        except Exception as error:
            rows.append({'name': name, 'expected': 'reject' if reject else 'accept', 'status': 'PASS' if reject else 'FAIL', 'exception': type(error).__name__, 'detail': str(error)})
    with tempfile.TemporaryDirectory(prefix='j1ab_') as temp:
        root = Path(temp)
        check('constructor_receipt_collision', lambda: construct(actor, core, root / 'construct1', 'forecast_receipts.jsonl'))
        check('constructor_reconciliation_collision', lambda: construct(actor, core, root / 'construct2', 'forecast_reconciliation.jsonl'))
        check('constructor_close_error_preserves_original', lambda: construct(actor, core, root / 'construct3', 'forecast_reconciliation.jsonl', True))
        check('close_failure_restores_all', lambda: closing(actor))
        check('loader_close_failure_restores_all', lambda: closing(actor, loader=True))
        check('repeated_instrumentation_restores_original', lambda: closing(actor, nested=True))
        for attribute in ('before', 'after'):
            def coherent(attribute=attribute):
                result = core.case(actor, root / ('coherent_' + attribute), step_mutator=lambda step: setattr(step, attribute, 'wrong'))
                require('exception' in result and result['native_calls'] == 1, 'Coherent Step/decision corruption accepted as MATCHED')
                return result
            check('coherent_step_raw_' + attribute, coherent)
        def mutate_runtime(item, kind):
            value = json.loads(item.collection.read_text())
            value['files'] = {} if kind == 'empty' else {'semabi/compiler/missing.py': 'a' * 64}
            write(item.collection, value); item.manifest['collector_freeze']['sha256'] = sha(item.collection)
        def relocated(item, part):
            path = item.root / part / 'invented.json'; write(path, {'source_head': 'invented-head'})
            item.manifest['predictor_freeze'] = {'path': str(path.relative_to(item.root)), 'sha256': sha(path)}
        def symlink_source(item):
            path = item.root / 'semabi/compiler/browser.py'; saved = path.read_bytes(); path.unlink()
            original = item.root / 'original.py'; original.write_bytes(saved); path.symlink_to(original)
        def symlink_ref(item):
            path = item.predictor; saved = path.read_bytes(); path.unlink()
            original = item.predictor.parent / 'original.json'; original.write_bytes(saved); path.symlink_to(original)
        manifest_specs = [
            ('valid', None),
            ('missing_inventory', lambda x: x.manifest['verification_files'].pop('scripts/transport_collect.py')),
            ('extra_inventory', lambda x: x.manifest['verification_files'].update({'extra.py': 'a' * 64})),
            ('wrong_source_hash', lambda x: x.manifest['verification_files'].update({'scripts/transport_collect.py': 'a' * 64})),
            ('wrong_head', lambda x: x.manifest.update(source_head='wrong')),
            ('absolute_reference', lambda x: alter_reference(x, str(x.predictor))),
            ('traversal_reference', lambda x: alter_reference(x, 'docs/../docs/data/v4/transport/development/j1/invented_predictor.json')),
            ('foreign_reference', lambda x: relocated(x, 'outside')),
            ('evaluator_reference', lambda x: relocated(x, 'docs/data/v4/transport/development/j1/evaluator')),
            ('symlink_source', symlink_source), ('symlink_reference', symlink_ref),
            ('wrong_reference_hash', lambda x: x.manifest['predictor_freeze'].update(sha256='a' * 64)),
            ('collector_routing', lambda x: setattr(x, 'collection', x.predictor)),
            ('empty_runtime', lambda x: mutate_runtime(x, 'empty')),
            ('missing_runtime', lambda x: mutate_runtime(x, 'missing')),
            ('predictor_wrong_head', lambda x: (write(x.predictor, {'source_head': 'wrong'}), x.manifest['predictor_freeze'].update(sha256=sha(x.predictor)))),
        ]
        for name, mutation in manifest_specs:
            check('manifest_' + name, lambda name=name, mutation=mutation: manifest_case(actor, root / ('m_' + name), mutation), name != 'valid')
        def ledger_symlink(item):
            item.ledger.unlink(); other = item.root / 'other'; other.touch(); item.ledger.symlink_to(other)
        ready_specs = [
            ('valid', None), ('pid_bool', lambda x: x.ready.update(pid=True)), ('pid_zero', lambda x: x.ready.update(pid=0)),
            ('wrong_status', lambda x: x.ready.update(status='ERROR')),
            ('wrong_ledger', lambda x: x.ready.update(ledger_path=str(x.root / 'other'))),
            ('symlink_ledger', ledger_symlink), ('missing_socket', lambda x: x.socket.unlink()),
            ('regular_socket', lambda x: (x.socket.unlink(), x.socket.touch())),
            ('wrong_head', lambda x: x.ready['provenance'].update(source_head='wrong')),
            ('wrong_freeze', lambda x: x.ready['provenance'].update(runtime_freeze_sha256='wrong')),
        ]
        for number, (name, mutation) in enumerate(ready_specs):
            check('ready_' + name, lambda number=number, mutation=mutation: ready_case(actor, root / ('r' + str(number)), mutation), name != 'valid')
        check('actual_actor_scoped_native_main_failed_script_retained', lambda: integrated(actor, core, root / 'integration'))
    require(all(sha(ROOT / name) == digest for name, digest in sources.items()), 'Reviewed source changed during controls')
    record = {'schema': 'semabi.j1.actor_boundary_independent_checks.v1', 'status': 'PASS' if all(row['status'] == 'PASS' for row in rows) else 'FAIL',
              'sources': sources, 'checks': rows, 'counts': dict(Counter(row['status'] for row in rows)),
              'scope': 'Invented data only. Actual actor/scoped main and exact retained function AST; fake Browser/EvidenceLog, copied public source routing, real ledger/receipt writes, bound local Unix socket and in-process invented predictor. No native import, fit, real browser, real fixture or sealed payload.'}
    with args.output.open('x') as stream: json.dump(record, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps({'path': str(args.output), 'sha256': sha(args.output), 'counts': record['counts'], 'failed': [r['name'] for r in rows if r['status'] == 'FAIL']}))
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
