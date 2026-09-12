"""Frozen reserved assessment using the existing literal caller, without task rescues."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'runs/.freshrss-assessment-411189b'
COMMIT = '411189b9fd42e622fd9f7e792ad75394ae3098f1'
SERVER = 'http://127.0.0.1:8866'
DIRECTORY = HERE / 'assessment_411189b'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def save(path, value):
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    sys.path.insert(0, str(SOURCE))
    from semabi.compiler import runtime
    assert Path(runtime.__file__).resolve().parent == SOURCE / 'semabi/compiler'
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, text=True).strip() == COMMIT
    hashes = runtime.source_hashes()
    http = module('frozen_external_client', SOURCE / 'scripts/product_semantic_http.py')
    binder = module('frozen_literal_caller', ROOT / 'runs/product_assessment_development_v1/binding/binding.py')
    setup = module('freshrss_evaluator_setup', HERE / 'setup.py')
    plan = json.loads((HERE / 'task_plan.json').read_text())
    assert plan['denominator'] == len(plan['tasks']) == 16
    DIRECTORY.mkdir(mode=0o700, exist_ok=False)
    freeze = {'source_commit': COMMIT, 'runtime_source_sha256': hashes,
        'frozen_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'caller': {'path': 'runs/product_assessment_development_v1/binding/binding.py',
                   'policy_version': binder.POLICY_VERSION, 'source_sha256': binder.SOURCE_SHA256,
                   'policy_sha256': binder.POLICY_SHA256,
                   'scope': 'Existing literal single-payload CREATE/exact-value REPLACE; no new grammar or schema rescue'},
        'onboarding': {'jobs': 1, 'max_actions': 600, 'max_writes': 400, 'max_seconds': 1800,
                       'frontier_contexts': 48, 'depth': 6, 'context_visits': 2,
                       'automatic_second_job_or_repair': False},
        'invocation': {'max_actions': 64, 'max_writes': 48, 'max_seconds': 180},
        'task_plan': str(HERE / 'task_plan.json'), 'denominator': 16,
        'resources': {'service_port': 8866, 'cpuset': '8,9', 'application_memory_bytes': 1073741824},
        'exposure': 'Evaluator read official setup docs, rendered login/subscription/display UI and native OPML/SQLite schema/data. Learner gets only URL, private credentials, authorized UI actions and rendered observations. No FreshRSS source, native identity, expected answer or field mapping reaches learner. Shared context is not blind.',
        'known_limit': 'Frozen411 includes a disclosed Workshop fitted/live feature mismatch; later unaccepted research candidates are excluded. This run measures the frozen whole stack, including the limited caller, not a claim that every unrouted task is impossible through API operations.',
        'baseline_comparison': 'NOT_RUN; no competence or speed superiority claim'}
    save(HERE / 'assessment_freeze_411189b.json', freeze)
    rows = [{**task, 'status': 'NOT_RUN', 'invoked': False, 'completed': False} for task in plan['tasks']]
    result = {'status': 'STARTED', 'denominator': 16, 'rows': rows, 'source_commit': COMMIT,
              'native_checks': [], 'baseline_comparison': freeze['baseline_comparison'],
              'wrong_task_effects': 'UNMEASURED_NO_TASK_INVOCATIONS',
              'false_confirmations': 'UNDEFINED_WITHOUT_TASK_CONFIRMATIONS',
              'exposure': freeze['exposure'], 'resets': 0}
    client = http.Client(SERVER, HERE / 'private/service_411189b/token', 1800)

    def native_snapshot(phase):
        began = time.monotonic()
        native = '/tmp/semabi-assessment-' + phase + '.sqlite'
        setup.cli('export-sqlite-for-user', '--user', setup.USER, '--filename', native)
        path = HERE / 'private' / ('assessment_' + phase + '.sqlite')
        assert not path.exists()
        setup.docker('cp', setup.CONTAINER + ':' + native, str(path))
        os.chmod(path, 0o600)
        fields = {'category': 'id,name,kind', 'feed': 'id,category,name,url,priority,error',
                  'entry': 'id,guid,title,content,is_read,is_favorite,id_feed'}
        with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as database:
            state = {table: database.execute('SELECT ' + columns + ' FROM ' + table + ' ORDER BY id').fetchall()
                     for table, columns in fields.items()}
        receipt = {'phase': phase, 'elapsed_seconds': time.monotonic() - began,
                   'counts': {table: len(values) for table, values in state.items()},
                   'scope': 'Complete native category/feed/article inventory on named fields; evaluator-only',
                   'native_export_calls': 1, 'application_semantic_writes': 0}
        result['native_checks'].append(receipt)
        save(DIRECTORY / ('native_' + phase + '.json'), receipt)
        return state

    began = time.monotonic()
    try:
        before = native_snapshot('before')
        credential = json.loads((HERE / 'private/credentials.json').read_text())
        auth_start = time.monotonic()
        accepted = client.request('POST', '/v1/connections', {'url': setup.URL,
            'credentials': {name: credential[name] for name in ('username', 'password')},
            'scope': {'exploration_enabled': True, 'max_actions': 600, 'max_writes': 400}})
        credential.clear()
        connected = client.wait(accepted)
        save(DIRECTORY / 'connection.json', connected)
        result['connection'] = accepted['id']
        result['authentication'] = {'wall_seconds': time.monotonic() - auth_start, 'result': connected.get('result')}
        print('Frozen ordinary authentication completed; starting the one authorized onboarding job.', flush=True)
        prefix = '/v1/connections/' + accepted['id']
        learning_start = time.monotonic()
        queued = client.request('POST', prefix + '/learn', {'settings': {'max_actions': 600, 'max_writes': 400}})
        save(DIRECTORY / 'learning_accepted.json', queued)
        learned = client.wait(queued)
        save(DIRECTORY / 'onboarding.json', learned)
        result['onboarding'] = {'status': learned['status'], 'wall_seconds': time.monotonic() - learning_start,
                                'result': http.evidence_summary(learned.get('result'))}
        catalog = client.request('GET', prefix + '/operations')['operations']
        save(DIRECTORY / 'published_catalog.json', http.evidence_summary(catalog))
        for row in rows:
            bound = binder.bind_request(row['request'], row['arguments'], catalog)
            save(DIRECTORY / (row['id'] + '_binding.json'), bound)
            if bound['status'] == 'ELIGIBLE':
                # This frozen grammar does not cover the preselected requests.
                # Any unexpected acceptance requires review, not new execution logic.
                row['status'] = 'UNEXPECTED_BINDER_ACCEPTANCE_REQUIRES_ADJUDICATION'
                continue
            parsed, _ = binder._goal(row['request'], row['arguments'])
            row['status'] = 'UNSUPPORTED_BY_FROZEN_CALLER'
            row['failure_stage'] = 'caller_goal_grammar' if parsed is None else 'published_operation_binding'
            row['reasons'] = bound['reasons']
        after = native_snapshot('after')
        changes = {}
        for table in before:
            old = {row[0]: row for row in before[table]}
            new = {row[0]: row for row in after[table]}
            changes[table] = {'added': len(new.keys() - old.keys()), 'removed': len(old.keys() - new.keys()),
                              'changed': sum(old[key] != new[key] for key in old.keys() & new.keys())}
        result['onboarding_native_changes'] = changes
        result['status'] = 'TERMINAL_ALL16_RETAINED'
    except Exception as error:
        result['status'] = 'FAILED_ALL16_RETAINED'
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
        for row in rows:
            if row['status'] == 'NOT_RUN':
                row['status'] = 'SETUP_OR_ONBOARDING_UNESTABLISHED'
        raise
    finally:
        result['source_unchanged'] = runtime.source_hashes() == hashes
        result['wall_seconds'] = time.monotonic() - began
        result['requests'] = client.requests
        result['completed'] = sum(row['completed'] for row in rows)
        result['invocations'] = sum(row['invoked'] for row in rows)
        save(DIRECTORY / 'results.json', result)
        print(json.dumps({key: result[key] for key in ('status', 'completed', 'denominator', 'invocations')}))


if __name__ == '__main__':
    main()
