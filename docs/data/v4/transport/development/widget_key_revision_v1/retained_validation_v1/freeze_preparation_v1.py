"""Create the exclusive W3 gate freezes and commands; standard-library metadata only."""
import ast
import copy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
MAIN = Path('/home/moloch/semabi')
W1 = MAIN / 'runs/.w1_worktree/docs/data/v4/transport/development/widget_persistence_v1'
W1_FULL = MAIN / 'runs/.w1_validation_worktree/docs/data/v4/transport/development/widget_persistence_v1/validation_repair_v2'
HEAD = 'aaa9b5df915464754341794179b5297cf22f6140'
PARENT = 'a1c0bc96d6a9725a3f23e18dbc96f97b0bd38f08'
NATIVE_CHANGES = {
    'semabi/compiler/v2/hypotheses.py': '8dab56a4b4d7a56424e5e91648b49f60f9ba576502ad0d9832ccce57ba50d235',
    'semabi/compiler/v2/refinement.py': '592029f46ed70f37198386535e5a45c7330cb98189bbda3b20663df28afa335a',
}
TEST_CHANGES = {
    'tests/test_v2_collection_variation.py': 'b66dc6caf0bc68a2694e5129d514efca415833ef2d879adf5ba086bbad6cd26c',
    'tests/test_v2_refinement.py': '60faa0ecaa61e2a11dbc382baeff971f7acc313f95887d39330ffc6ddcf7c748',
}
OUTPUTS = ('source_freeze_v1.json', 'corpus_freeze_v1.json', 'full_suite_source_freeze_v1.json',
           'commands_v2.json', 'freeze_creation_receipt_v1.json')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    require(path.resolve(strict=True) == path and path.is_file(), 'Expected canonical file: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path, expected):
    require(sha(path) == expected, 'Retained dependency changed: ' + str(path))
    return json.loads(path.read_text())


def hashes(paths):
    return {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(paths)}


def write(path, record):
    with path.open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')


def changes(actual, previous):
    require(set(actual) == set(previous), 'Source inventory differs from the accepted predecessor')
    return {name: value for name, value in actual.items() if value != previous[name]}


def main():
    require(Path.cwd() == ROOT and sys.flags.safe_path and sys.flags.optimize == 0
            and sys.dont_write_bytecode and os.environ.get('PYTHONPATH') == '', 'Use safe metadata-only startup')
    require(not any(name == 'semabi' or name.startswith('semabi.') for name in sys.modules), 'Unexpected native import')
    require(all(not (HERE / name).exists() and not (HERE / name).is_symlink() for name in OUTPUTS),
            'Final preparation identities are exclusive')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == HEAD
            and subprocess.check_output(['git', 'rev-parse', 'HEAD^'], text=True).strip() == PARENT,
            'Reviewed checkpoint changed')
    require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--'], text=True).strip(),
            'Tracked candidate worktree changed')
    require(set(subprocess.check_output(['git', 'diff', '--name-only', PARENT, HEAD, '--'], text=True).splitlines())
            == set(NATIVE_CHANGES) | set(TEST_CHANGES), 'Checkpoint scope changed')
    prior = read(W1 / 'source_freeze_v1.json', '583d17e7a1d6170b58205e07145b683456490aec44d36718bfc227319bf78a62')
    full_prior = read(W1_FULL / 'full_suite_source_freeze_v2.json', 'a1b4242f0cf11a885822e693e0412d6e3c451543ed8417eefe1aed4890f2afc1')
    copy_path = HERE / 'root_input_copy_v1.json'
    read(copy_path, '72bfcd5a62c9b7878cf476aa0a01f8f10c7ab44f350d0d696b384fdfa4d86620')
    input_identities = json.loads((HERE / 'input_identities_v1.json').read_text())
    for identity in input_identities['retained_authority'].values():
        require(sha(Path(identity['path'])) == identity['sha256'], 'Accepted predecessor identity changed')
    commands = json.loads((HERE / 'command_templates_v2.json').read_text())
    require(commands['source_checkpoint'] == HEAD and len(commands['jobs']) == 7, 'Wrong command proposal')
    for job in commands['jobs'].values():
        prefix = Path(job['fresh_bytecode_prefix'])
        require(prefix.is_absolute() and prefix.resolve() == prefix
                and not prefix.exists() and not prefix.is_symlink(), 'Prefix is no longer absent')
        require(not (ROOT / job['job_directory']).exists(), 'Job identity already exists')
        require(all(not (ROOT / name).exists() for name in job.get('outputs', [])), 'Result identity already exists')
    native = hashes((ROOT / 'semabi').rglob('*.py'))
    tests = hashes((ROOT / 'tests').rglob('*.py'))
    require(changes(native, full_prior['native_files']) == NATIVE_CHANGES, 'Native delta changed')
    require(changes(tests, full_prior['test_files']) == TEST_CHANGES, 'Test delta changed')
    runtime = hashes(ROOT / name for name in full_prior['runtime_files'])
    require(changes(runtime, full_prior['runtime_files']) == NATIVE_CHANGES, 'Runtime delta changed')
    dependencies = hashes(ROOT / name for name in full_prior['dependency_files'])
    require(dependencies == full_prior['dependency_files'], 'Measurement/runtime dependency changed')
    corpus_metadata = copy.deepcopy(prior['corpora'])
    corpus_manifest_path = ROOT / corpus_metadata['manifest']
    corpus_manifest = read(corpus_manifest_path, corpus_metadata['manifest_sha256'])
    corpus_root = ROOT / corpus_metadata['root']
    require(corpus_manifest['root'] == corpus_metadata['root'] and len(corpus_manifest['files']) == 45,
            'Wrong corpus input inventory')
    inputs = hashes(corpus_root / name for name in corpus_manifest['files'])
    require(inputs == corpus_metadata['files'] and {path.relative_to(corpus_root).as_posix()
            for path in corpus_root.rglob('*') if path.is_file()} == set(corpus_manifest['files']),
            'Copied corpus membership or bytes differ')
    suite = hashes(path for name in ('harbour_transfer', 'blend_book_transfer', 'harbour_dev')
                   for path in (ROOT / 'runs/v4' / name).rglob('*') if path.is_file())
    require(suite == full_prior['suite_retained_run_files'] and len(suite) == 18, 'Suite inputs differ')
    tracked = hashes(ROOT / name for name in subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0') if name)
    rendering = json.loads((HERE / 'rendering_receipt_v1.json').read_text())
    for name, row in rendering['rendered_files'].items():
        require(sha(ROOT / name) == row['sha256'], 'Rendered instrument changed')
        ast.parse((ROOT / name).read_text(), filename=name)
    verification_paths = [path for path in HERE.rglob('*') if path.is_file()]
    verification_paths += [ROOT / name for name in dependencies]
    verification_paths += [ROOT / 'pytest.ini', corpus_manifest_path]
    verification_paths += [path for path in (HERE.parent / 'candidate_v4').rglob('*') if path.is_file()]
    focused = HERE.parent / 'root_focused_candidate_v2'
    require(sha(focused / 'artifact_manifest_v3.json') == 'bee301848e116ee6c942fcd84d8a452f0bc09c882467b0f0fcebb91b00586749',
            'Accepted focused candidate seal changed')
    verification_paths += [path for path in focused.rglob('*')
                           if not path.is_relative_to(focused / 'pytest_tmp_v1') and path.is_file()]
    verification = hashes(set(verification_paths))
    require(sys.executable == full_prior['python_executable'] and sys.version == full_prior['python_version'],
            'Shared interpreter changed')
    plugins = sorted((entry.name, entry.value) for entry in importlib.metadata.entry_points(group='pytest11'))
    require(plugins == [] and importlib.metadata.version('pytest') == full_prior['pytest_version'],
            'Installed pytest or plugin metadata changed')
    pytest_environment = {name: os.environ.get(name) for name in
                          ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD')}
    require(all(value is None for value in pytest_environment.values()), 'Unexpected pytest override')
    external = dict(full_prior['retained_external_files'])
    for path in (W1 / 'source_freeze_v1.json', W1 / 'corpus_freeze_v1.json', W1 / 'results_manifest_v1.json',
                 W1 / 'corpus_comparison_v1.json', W1_FULL / 'full_suite_source_freeze_v2.json',
                 W1_FULL / 'full_suite_results_manifest_v2.json', W1_FULL / 'root_full_gate_acceptance_v2.json',
                 MAIN / 'docs/data/v4/transport/development/g2/results_manifest_v1.json',
                 MAIN / 'docs/data/v4/transport/development/g2/compare_corpora.py'):
        external.setdefault(str(path), sha(path))
    for name, expected in external.items():
        require(sha(Path(name)) == expected, 'Retained external dependency changed')
    require(sha(MAIN / 'docs/data/v4/transport/development/g2/results_manifest_v1.json')
            == '481f879db351618431127a8f7a99db1a35ed06975c7f1f325347c9953a80d67e'
            and sha(MAIN / 'docs/data/v4/transport/development/g2/compare_corpora.py')
            == '6a4c7eedcfd6143581a8cd75e47c0459b48ac8614657fcf0e0a615d1558ad001',
            'Accepted comparison algorithm or G2 preservation identity changed')
    discovery = copy.deepcopy(full_prior['pytest_discovery'])
    discovery.update(schema='semabi.transport.w3_pytest_discovery_bindings.v1', source_head=HEAD,
                     working_directory=str(ROOT), default_conftest_cutoff=str(ROOT),
                     created_utc=datetime.now(timezone.utc).isoformat(),
                     prior_independent_collector=discovery['independent_collector'],
                     independent_collector='Reused accepted W1 binding; W3 preparation rechecked its exact inputs')
    for name, row in discovery['files'].items():
        path = ROOT / name
        require(sha(path) == row['sha256'] if row['present'] else not path.exists() and not path.is_symlink(),
                'Canonical discovery input changed')
    members = list((ROOT / 'tests').iterdir())
    require({path.name for path in members} == set(discovery['test_directory_members'])
            and all(path.is_file() and not path.is_symlink() for path in members), 'Canonical flat test inventory changed')
    now = datetime.now(timezone.utc).isoformat()
    source = {'schema': 'semabi.transport.w3_validation_freeze.v1', 'created_utc': now,
        'source_head': HEAD, 'base_source_head': PARENT, 'working_directory': str(ROOT), 'coordinator': '/root',
        'change_basis_w1_full_suite_sha256': sha(W1_FULL / 'full_suite_source_freeze_v2.json'),
        'reviewed_runtime_changes': NATIVE_CHANGES, 'reviewed_test_changes': TEST_CHANGES,
        'inherited_test_changes_from_original_w1': changes(full_prior['test_files'], prior['test_files']),
        'files': runtime, 'source_files': native, 'test_files': tests, 'tracked_files': tracked,
        'verification_files': verification, 'suite_retained_run_files': suite, 'corpora': corpus_metadata,
        'retained_external_files': external, 'pytest_environment': pytest_environment, 'pytest_entry_points': plugins,
        'python_version': sys.version, 'python_executable': sys.executable,
        'allowed_cpu_affinities': [[cpu] for cpu in sorted({job['cpu'] for name, job in commands['jobs'].items()
                                                         if name != 'full_pytest_v1'})],
        'full_suite_origin_scope': full_prior['subprocess_scope'],
        'root_input_copy': {'path': copy_path.relative_to(ROOT).as_posix(), 'sha256': sha(copy_path)},
        'prior_w1_corpus_source': {'path': str(W1 / 'source_freeze_v1.json'), 'sha256': sha(W1 / 'source_freeze_v1.json')},
        'scope': 'Committed reviewed W3 source, rendered gate instruments and exact retained inputs. Metadata freeze only; no native execution, GO or acceptance is claimed.'}
    source_path = HERE / 'source_freeze_v1.json'
    write(source_path, source)
    source_sha = sha(source_path)
    corpus = {'schema': 'semabi.transport.w3_corpus_freeze.v1', 'created_utc': now, 'source_head': HEAD,
        'working_directory': str(ROOT), 'source_freeze': {'path': source_path.relative_to(ROOT).as_posix(), 'sha256': source_sha},
        'files': runtime, 'corpora': corpus_metadata,
        'verification_files': {**verification, source_path.relative_to(ROOT).as_posix(): source_sha}}
    corpus_path = HERE / 'corpus_freeze_v1.json'
    write(corpus_path, corpus)
    corpus_sha = sha(corpus_path)
    full_verification = {**verification, source_path.relative_to(ROOT).as_posix(): source_sha,
                         corpus_path.relative_to(ROOT).as_posix(): corpus_sha}
    full_job = commands['jobs']['full_pytest_v1']
    full_environment = {**full_job['environment'], **pytest_environment}
    full = {'schema': 'semabi.transport.w3_full_suite_freeze.v1', 'created_utc': now,
        'source_head': HEAD, 'base_source_head': PARENT, 'working_directory': str(ROOT), 'coordinator': '/root',
        'tracked_source_delta': {**NATIVE_CHANGES, **TEST_CHANGES}, 'native_files': native, 'test_files': tests,
        'tracked_files': tracked, 'runtime_files': runtime, 'dependency_files': dependencies,
        'verification_files': full_verification, 'files': {**tracked, **native, **tests, **runtime, **suite, **inputs, **full_verification},
        'retained_external_files': external, 'suite_retained_run_files': suite,
        'environment': full_environment, 'cpu_affinity': [full_job['cpu']], 'priority': 0,
        'ambient_prefix': full_job['fresh_bytecode_prefix'], 'python_version': sys.version,
        'python_executable': sys.executable, 'python_required_flags': {'-P': True, '-B': True, 'optimize': 0},
        'pytest_version': full_prior['pytest_version'], 'pytest_entry_points': plugins, 'pytest_args': full_job['pytest_args'],
        'pytest_discovery': discovery, 'subprocess_scope': full_prior['subprocess_scope'],
        'project_local_non_semabi_exec': full_prior['project_local_non_semabi_exec'],
        'source_corpus_freezes': {'source': source_sha, 'corpus': corpus_sha},
        'root_input_copy': source['root_input_copy'],
        'focused_results_manifest': {'path': str(focused / 'artifact_manifest_v3.json'), 'sha256': sha(focused / 'artifact_manifest_v3.json')},
        'prior_accepted_full_suite': {'path': str(W1_FULL / 'full_suite_source_freeze_v2.json'), 'sha256': sha(W1_FULL / 'full_suite_source_freeze_v2.json')},
        'verification_membership_scope': 'Every regular preparation/rendered file in this gate before freeze, accepted v4 candidate snapshot and focused evidence excluding its exact pytest scratch, plus unchanged dependencies. Final exact commands, GO and results are later records.',
        'scope': 'One canonical full-suite attempt under reviewed W3 source, separately authorized after freeze review. Five new corpus runs remain required; retained W1 corpus results are comparison inputs, not reused W3 results.'}
    full_path = HERE / 'full_suite_source_freeze_v1.json'
    write(full_path, full)
    full_sha = sha(full_path)
    replacements = {'<W3_SOURCE_FREEZE_SHA256>': source_sha, '<W3_CORPUS_FREEZE_SHA256>': corpus_sha,
                    '<W3_FULL_SUITE_SOURCE_FREEZE_SHA256>': full_sha}
    commands['schema'] = 'semabi.transport.w3_validation_commands.v2'
    commands['status'] = 'CONCRETE_PREPARED_NOT_EXECUTED_ROOT_REVIEW_AND_GO_REQUIRED'
    commands['created_utc'] = now
    commands['freezes'] = {path.name: {'path': str(path), 'sha256': sha(path)} for path in (source_path, corpus_path, full_path)}
    commands['rendered_instruments'] = rendering['rendered_files']
    for job in commands['jobs'].values():
        job['status'] = 'CONCRETE_PREPARED_NOT_EXECUTED_ROOT_GO_REQUIRED'
        for field in ('inner_argv', 'outer_argv'):
            job[field] = [replacements.get(value, value) for value in job[field]]
        require(not any('<' in value or '>' in value for value in job['outer_argv']), 'Unresolved launch argv')
    command_path = HERE / 'commands_v2.json'
    write(command_path, commands)
    receipt = {'schema': 'semabi.transport.w3_validation_freeze_creation.v1', 'created_utc': now,
        'status': 'FROZEN_AND_PREPARED_NOT_EXECUTED_NO_GO', 'source_head': HEAD,
        'preparer_source_sha256': sha(Path(__file__).resolve()), 'python_executable': sys.executable,
        'native_files': len(native), 'test_files': len(tests), 'tracked_files': len(tracked),
        'runtime_files': len(runtime), 'dependency_files': len(dependencies), 'verification_files': len(verification),
        'retained_external_files': len(external), 'corpus_files': len(inputs), 'suite_files': len(suite),
        'files': {str(path): sha(path) for path in (source_path, corpus_path, full_path, command_path)},
        'native_modules_imported': [name for name in sys.modules if name == 'semabi' or name.startswith('semabi.')],
        'launch_authority': 'Root independently reviews/rechecks these freezes and commands, then issues separate GO and owns launch.'}
    require(not receipt['native_modules_imported'], 'Native module imported during preparation')
    write(HERE / 'freeze_creation_receipt_v1.json', receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
