import ast
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
sys.dont_write_bytecode = True
base = Path('docs/data/v4/transport/reserved_v1').resolve()
def load(name):
    spec = importlib.util.spec_from_file_location('check_' + name, base / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
p = load('preserve_first_pass')
s = load('summarize')
helper_tree = ast.parse(p.HELPER.read_bytes())
namespace = {'Counter': Counter, 'EXPECTED_BUDGET': 60}
selected = [node for node in helper_tree.body if isinstance(node, ast.FunctionDef) and node.name in {'require', 'accounting'}]
exec(compile(ast.Module(body=selected, type_ignores=[]), 'retained-accounting', 'exec'), namespace)
accounting = namespace['accounting']
checks = 0
with tempfile.TemporaryDirectory(prefix='r1-custody-author-') as temporary:
    root = Path(temporary)
    p.ROOT = root
    p.HERE = root / 'reserved'
    p.RAW = root / 'raw'
    p.COLLECTOR = root / 'scripts/transport_collect.py'
    freeze = p.HERE / 'implementation_freeze_v1.json'
    freeze.parent.mkdir()
    freeze.write_text('{}')
    scripted = root / p.SCRIPTS[p.INITIAL]
    scripted.parent.mkdir(parents=True)
    scripted.write_text('opaque synthetic bytes')
    directory = p.RAW / p.INITIAL
    directory.mkdir(parents=True)
    observations = [{'sig': 'synthetic-sig', 'obs': {}}]
    decisions = []
    steps = []
    for index in range(37):
        kind = 'reset' if index == 0 else 'reload' if index == 1 else 'click'
        decision = {'step': None if index == 0 else index - 1, 'episode': 1,
                    'charged_attempt': index + 1, 'action': {'kind': kind},
                    'ok': index != 5, 'error': 'synthetic failure' if index == 5 else None,
                    'before': None if index == 0 else 'synthetic-sig', 'after': 'synthetic-sig'}
        decisions.append(decision)
        if index:
            steps.append({key: value for key, value in decision.items() if key != 'charged_attempt'})
    for name, rows in [('observations.jsonl', observations), ('steps.jsonl', steps), ('decisions.jsonl', decisions)]:
        (directory / name).write_text(''.join(json.dumps(row) + '\n' for row in rows))
    command = ['.venv/bin/python', 'scripts/transport_collect.py', 'script', '--url', p.URL,
               '--reset-url', p.RESET + 'initial', '--out', str(directory), '--freeze', str(freeze),
               '--seed', '1701', '--script', str(scripted), '--fixture', 'reservoir']
    stamp = {'utc': '2026-01-01T00:00:01+00:00', 'pid': 123, 'cwd': str(root), 'argv': command[1:], 'git_head': 'synthetic-head'}
    run = {'status': 'FINISHED', 'complete': False, 'charged_attempts': 37, 'failed_attempts': 1,
           'paired_steps_recorded': 36, 'unpaired_attempts': 1,
           'primitive_counts': dict(Counter(row['action']['kind'] for row in decisions)),
           'snapshot_calls': 36, 'settle_timeouts': 0, 'navigation_waits': 0, 'bootstrap_goto': 0,
           'raw_hashes': {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in (*p.RAW_NAMES, 'decisions.jsonl')},
           'script_file': str(scripted), 'script_sha256': hashlib.sha256(scripted.read_bytes()).hexdigest(),
           'case_count': 1, 'freeze_sha256': hashlib.sha256(freeze.read_bytes()).hexdigest(), 'start': stamp, 'end': stamp}
    (directory / 'run.json').write_text(json.dumps(run))
    job = {'command': command, 'child_pid': 123, 'start_utc': '2026-01-01T00:00:00+00:00', 'end_utc': '2026-01-01T00:00:02+00:00'}
    record = p.collection(p.Inventory(), p.INITIAL, job, freeze, 'synthetic-head', accounting)
    assert record['accounting']['failed_attempts'] == 1 and record['accounting']['complete'] is False
    checks += 1
    steps[4]['ok'] = True
    (directory / 'steps.jsonl').write_text(''.join(json.dumps(row) + '\n' for row in steps))
    run['raw_hashes']['steps.jsonl'] = hashlib.sha256((directory / 'steps.jsonl').read_bytes()).hexdigest()
    (directory / 'run.json').write_text(json.dumps(run))
    try:
        p.collection(p.Inventory(), p.INITIAL, job, freeze, 'synthetic-head', accounting)
    except ValueError as error:
        assert 'Decision/raw step binding' in str(error)
        checks += 1
    else:
        raise AssertionError('mutated paired transition accepted')
    s.ROOT = root
    s.HERE = root / 'reserved'
    s.RAW = root / 'raw'
    s.MANIFEST = s.HERE / 'first_pass_manifest_v1.json'
    mapping = {}
    for logical, actual in s.STAGES.items():
        for name in ('run.json', 'decisions.jsonl'):
            mapping[f'reservoir/{logical}/{name}'] = s.RAW / actual / name
        if logical not in ('initial_v2', 'evaluation_v2'):
            mapping[f'reservoir/{logical}/refits.json'] = s.RAW / actual / 'refits.json'
        if logical != 'evaluation_v2':
            mapping[f'reservoir/scores/{logical}.json'] = s.HERE / 'scores' / (actual + '.json')
    mapping['reservoir/candidates_v2/candidates.json'] = s.RAW / 'r1_candidates_v1/candidates.json'
    files = {}
    for path in mapping.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{}\n')
        files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    s.MANIFEST.write_text(json.dumps({'schema': 'semabi.transport.reserved_first_pass.v1', 'status': 'PRESERVED', 'all_owned_jobs_terminated': True, 'files': files}))
    inputs = s.PreservedInputs()
    assert inputs.aliases == mapping and len(mapping) == 22
    for alias in mapping:
        assert inputs.read(alias) == {}
    inputs.verify_unchanged()
    checks += 1
    for bad in ('dispatch/initial_v2/run.json', 'reservoir/../initial_v2/run.json', 'reservoir/r1_initial_v1/run.json'):
        try:
            inputs.read(bad)
        except ValueError:
            checks += 1
        else:
            raise AssertionError('unrecognized alias accepted')
    next(iter(mapping.values())).write_text('{"changed":true}')
    try:
        inputs.verify_unchanged()
    except ValueError:
        checks += 1
    else:
        raise AssertionError('input mutation accepted')
print(json.dumps({'synthetic_checks_passed': checks, 'r1_raw_read': False, 'learner_imported': False}))
