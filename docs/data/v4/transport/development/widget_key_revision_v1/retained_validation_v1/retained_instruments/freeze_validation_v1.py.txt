"""Freeze reviewed W1 validation instruments, candidate files and exact inputs."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
MAIN = Path('/home/moloch/semabi')
HEAD = '284d80c855ff37c42a509ae1dd88f83d4e04e3f4'
B1_SHA = 'c40e565fb6f6fda6116a442a6291ba987e0d2e445ed8d63ec3f58082743b730d'
CHANGES = {'semabi/compiler/v2/hypotheses.py': '637347222e7212fd04a9ce367c9972ed9cdbc96c5768d021793c8a9774eda344'}
TEST_CHANGES = {'tests/test_v2_collection_variation.py': 'a7beaca90e5dc50721d087edc726228bb605e3f59e54aea9d24299e7cf132c47'}
MANIFEST_SHA = '0a2fc2a9833f290fb23d9300e0547b53b83af2ec93ab3a92cde63b1f0ddc1dc1'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    require(path.resolve(strict=True) == path and path.is_file(), 'Expected actual worktree file: ' + str(path))
    return path.relative_to(ROOT).as_posix()


def hashes(paths):
    return {relative(path): sha(path) for path in sorted(paths)}


def write(path, record):
    with path.open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    source_path, corpus_path = HERE / 'source_freeze_v1.json', HERE / 'corpus_freeze_v1.json'
    require(all(not path.exists() and not path.is_symlink() for path in (source_path, corpus_path)),
            'W1 freeze identities are exclusive')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    require(head == HEAD, 'Not the reviewed focused W1 source checkpoint')
    require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--'], cwd=ROOT, text=True).strip(),
            'Tracked candidate worktree differs from reviewed commit')
    prior_path = MAIN / 'docs/data/v4/transport/development/b1_validation/source_freeze_v1.json'
    require(sha(prior_path) == B1_SHA, 'Authenticated B1 source freeze changed')
    prior = json.loads(prior_path.read_text())
    source_files = hashes((ROOT / 'semabi').rglob('*.py'))
    test_files = hashes((ROOT / 'tests').rglob('*.py'))
    for actual, baseline, expected in ((source_files, prior['source_files'], CHANGES),
                                       (test_files, prior['test_files'], TEST_CHANGES)):
        require(set(actual) == set(baseline), 'Native/test file inventory differs from B1')
        require({name: value for name, value in actual.items() if value != baseline[name]} == expected,
                'Changes exceed reviewed W1 native/test edits')
    runtime = hashes(ROOT / name for name in prior['files'])
    require({name: value for name, value in runtime.items() if value != prior['files'][name]} == CHANGES,
            'Runtime differs from B1 beyond the reviewed hypotheses change')
    manifest_path = ROOT / 'docs/data/v4/transport/development/g1/rebuild_v1/input_manifest.json'
    require(sha(manifest_path) == MANIFEST_SHA, 'Persistent input manifest changed')
    manifest = json.loads(manifest_path.read_text())
    require(manifest['root'] == 'runs/v4/transport_g1_corpora_v1' and len(manifest['files']) == 45,
            'Wrong persistent G1/G2 corpus inventory')
    corpus_root = ROOT / manifest['root']
    inputs = hashes(corpus_root / name for name in manifest['files'])
    require({name: sha(corpus_root / name) for name in manifest['files']} == manifest['files'], 'Copied corpus bytes differ')
    require({path.relative_to(corpus_root).as_posix() for path in corpus_root.rglob('*') if path.is_file()}
            == set(manifest['files']), 'Copied corpus membership differs')
    suite = hashes(path for name in ('harbour_transfer', 'blend_book_transfer', 'harbour_dev')
                   for path in (ROOT / 'runs/v4' / name).rglob('*') if path.is_file())
    require(suite == prior['suite_retained_run_files'] and len(suite) == 18, 'Retained full-suite inputs differ from B1')
    names = ('validation_plan_v1.md', 'freeze_validation_v1.py', 'validation_guard.py', 'run_corpus.py',
             'run_full_suite.py', 'compare_corpora.py', 'preserve_validation_v1.py', 'input_copy_v1.json')
    verification_paths = [HERE / name for name in names]
    verification_paths += list((HERE / 'verification_preparation').iterdir())
    verification_paths += list((HERE / 'instrument_revisions').iterdir())
    verification_paths += [ROOT / name for name in ('docs/data/v4/transport/run_job.py',
        'docs/data/v4/transport/baseline/check_corpora.py', 'docs/data/v4/prequential/instruments/link_probe.py',
        'scripts/v4_authority.py', 'scripts/v4_freeze_evaluator_inputs.py', 'pyproject.toml', 'pytest.ini')]
    plugins = [{'name': item.name, 'value': item.value, 'distribution': item.dist.name,
                'version': item.dist.version} for item in importlib.metadata.entry_points(group='pytest11')]
    require(plugins == [], 'Unexpected external pytest plugin entry points')
    pytest_environment = {name: os.environ.get(name) for name in
                          ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD')}
    require(all(value is None for value in pytest_environment.values()), 'Unexpected pytest environment override')
    tracked_names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')[:-1]
    source = {'schema': 'semabi.transport.w1_validation_freeze.v1',
        'created_utc': datetime.now(timezone.utc).isoformat(), 'source_head': head, 'working_directory': str(ROOT),
        'coordinator': '/root/baseline_verification',
        'prior_b1': {'path': str(prior_path), 'sha256': B1_SHA, 'source_head': prior['source_head'],
                     'qualification': 'Accepted retained-output baseline; historical loaded native origins were not recorded. Fresh B1 helper import order gives main precedence.'},
        'reviewed_runtime_changes': CHANGES, 'reviewed_test_changes': TEST_CHANGES,
        'files': runtime, 'source_files': source_files, 'test_files': test_files,
        'tracked_files': hashes(ROOT / name for name in tracked_names),
        'verification_files': hashes(verification_paths), 'suite_retained_run_files': suite,
        'corpora': {'manifest': relative(manifest_path), 'manifest_sha256': MANIFEST_SHA,
                    'root': manifest['root'], 'files': inputs},
        'pytest_entry_points': plugins,
        'pytest_environment': pytest_environment,
        'full_suite_origin_scope': {
            'primary': 'PRIMARY_PYTEST_INTERPRETER; canonical anchored SemABI package and before/after module table paths/hashes.',
            'python_children': 'CONTROLLED_SYNTHETIC_AUTHORITY_TESTS; test_v4_execution_authority.py intentionally executes synthetic temporary SemABI packages. These children are excluded from the parent origin ledger and remain unmodified.',
            'static_child_inventory': {'test_file': 'tests/test_v4_execution_authority.py',
                'sha256': test_files['tests/test_v4_execution_authority.py'],
                'authority_helper_calls': 27, 'plain_import_helper_calls': 4, 'direct_calls': 2,
                'total_expanded_python_launches': 33, 'count_basis': 'Static current test parametrization/loops; no runtime count claim.'},
            'private_script_execution': 'scripts/v4_authority.py and scripts/v4_freeze_evaluator_inputs.py execute under private names. Source custody binds their bytes; SemABI origin snapshots do not observe those executions.',
            'other_children': 'Playwright browser/driver descendants are not Python SemABI workers; third-party process behavior is outside the native origin ledger.'},
        'scope': 'Reviewed focused source checkpoint plus validation instruments and inputs. Metadata preparation only; no full-suite or corpus result is claimed. Whole tracked-file hashes are custody metadata, not learner input.'}
    write(source_path, source)
    source_sha = sha(source_path)
    corpus = {'schema': 'semabi.transport.w1_corpus_freeze.v1', 'source_head': head,
        'working_directory': str(ROOT), 'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_freeze': {'path': relative(source_path), 'sha256': source_sha},
        'files': runtime, 'corpora': source['corpora'],
        'verification_files': {**source['verification_files'], relative(source_path): source_sha}}
    write(corpus_path, corpus)
    print(json.dumps({'source_freeze_sha256': source_sha, 'corpus_freeze_sha256': sha(corpus_path),
        'source_head': head, 'runtime_files': len(runtime), 'source_files': len(source_files),
        'test_files': len(test_files), 'corpus_files': len(inputs), 'suite_run_files': len(suite)}))


if __name__ == '__main__':
    main()
