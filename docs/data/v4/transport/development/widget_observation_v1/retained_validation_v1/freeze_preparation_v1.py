"""Create the exclusive W2 gate freezes and commands; standard-library metadata only."""
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
PREDECESSOR = MAIN / 'runs/.w3_repair_worktree/docs/data/v4/transport/development/widget_key_revision_repair_v1/validation_gate_v1'
ACCEPTANCE = MAIN / 'docs/data/v4/transport/development/widget_observation_v1/repair_validation_v1'
HEAD = 'b15e6b0a4c2736fabfcb48fbab19981d82b575e8'
PARENT = 'e8f33c9056cc51135b7f9553fad3a7ad829def04'
NATIVE_CHANGES = {'semabi/compiler/v4/objective.py': 'c63ff4e6408c08d976fdfb4a9153d67e6cb1935ca231ee51b32a861648d78fca'}
TEST_CHANGES = {'tests/test_v4_objective.py': '93ebc7c829c8686765d535887f21a7f85c9e27c6fa03df029ea769644a307722'}
OUTPUTS = ('source_freeze_v1.json', 'corpus_freeze_v1.json', 'full_suite_source_freeze_v1.json',
           'commands_v1.json', 'freeze_creation_receipt_v1.json')


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
    prior = read(PREDECESSOR / 'source_freeze_v1.json', '49d0888546223dc90aef70212a80018dabbc68e92bf16dcf394b17ef698c8eac')
    full_prior = read(PREDECESSOR / 'full_suite_source_freeze_v1.json', 'e34af04a2fe44fdef0d1e541c3f4592b994b534efd9aa1710be0314cf838671b')
    copy_path = HERE / 'root_input_copy_v1.json'
    read(copy_path, '6a0642f8ae870c9eb3245024a8620b5b6214d0f9aa9719d4205c4d8c949c683a')
    input_identities = json.loads((HERE / 'input_identities_v1.json').read_text())
    preparation = read(HERE / 'preparation_manifest_v1.json', '0ed3f2e67e3af2227d459b984a025aac5613d3a472833e7e9028d1a8216f296e')
    for name, row in preparation['files'].items():
        require(sha(HERE / name) == row['sha256'] and (HERE / name).stat().st_size == row['bytes'], 'Held preparation changed')
    require(input_identities['comparison_predecessor']['source_head'] == prior['source_head'], 'Comparison predecessor differs')
    commands = json.loads((HERE / 'command_templates_v1.json').read_text())
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
    verification_paths += [path for folder in ('candidate_source_v3', 'baseline_v2') for path in (HERE.parent / folder).rglob('*') if path.is_file()]
    focused = HERE.parent / 'root_focused_v1'
    require(sha(focused / 'artifact_manifest_v2.json') == '8f69ae178aacb0b6f33627e9f7fa647b62e782aa798251cea74d1d4ae0e54098',
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
    for path in (PREDECESSOR / 'source_freeze_v1.json', PREDECESSOR / 'corpus_freeze_v1.json',
                 PREDECESSOR / 'full_suite_source_freeze_v1.json',
                 ACCEPTANCE / 'paired_result_v1.json', ACCEPTANCE / 'root_source_checkpoint_acceptance_v1.json',
                 ACCEPTANCE / 'independent_paired_review_v1.md', ACCEPTANCE / 'root_source_commit_tool_v1.json',
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
    discovery.update(schema='semabi.transport.w2_pytest_discovery_bindings.v1', source_head=HEAD,
                     working_directory=str(ROOT), default_conftest_cutoff=str(ROOT),
                     created_utc=datetime.now(timezone.utc).isoformat(),
                     prior_independent_collector=discovery['independent_collector'],
                     independent_collector='Reused W3 discovery binding; W2 preparation rechecked its exact inputs')
    for name, row in discovery['files'].items():
        path = ROOT / name
        require(sha(path) == row['sha256'] if row['present'] else not path.exists() and not path.is_symlink(),
                'Canonical discovery input changed')
    members = list((ROOT / 'tests').iterdir())
    require({path.name for path in members} == set(discovery['test_directory_members'])
            and all(path.is_file() and not path.is_symlink() for path in members), 'Canonical flat test inventory changed')
    now = datetime.now(timezone.utc).isoformat()
    source = {'schema': 'semabi.transport.w2_validation_freeze.v1', 'created_utc': now,
        'source_head': HEAD, 'base_source_head': PARENT, 'working_directory': str(ROOT), 'coordinator': '/root',
        'change_basis_w3_full_suite_sha256': sha(PREDECESSOR / 'full_suite_source_freeze_v1.json'),
        'reviewed_runtime_changes': NATIVE_CHANGES, 'reviewed_test_changes': TEST_CHANGES,
        'predecessor_full_vs_corpus_test_changes': changes(full_prior['test_files'], prior['test_files']),
        'files': runtime, 'source_files': native, 'test_files': tests, 'tracked_files': tracked,
        'verification_files': verification, 'suite_retained_run_files': suite, 'corpora': corpus_metadata,
        'retained_external_files': external, 'pytest_environment': pytest_environment, 'pytest_entry_points': plugins,
        'python_version': sys.version, 'python_executable': sys.executable,
        'allowed_cpu_affinities': [[cpu] for cpu in sorted({job['cpu'] for name, job in commands['jobs'].items()
                                                         if name != 'full_pytest_v1'})],
        'full_suite_origin_scope': full_prior['subprocess_scope'],
        'root_input_copy': {'path': copy_path.relative_to(ROOT).as_posix(), 'sha256': sha(copy_path)},
        'prior_w3_corpus_source': {'path': str(PREDECESSOR / 'source_freeze_v1.json'), 'sha256': sha(PREDECESSOR / 'source_freeze_v1.json')},
        'scope': 'Committed reviewed W2 source, rendered gate instruments and exact retained inputs. Metadata freeze only; no native execution, GO or acceptance is claimed.'}
    source_path = HERE / 'source_freeze_v1.json'
    write(source_path, source)
    source_sha = sha(source_path)
    corpus = {'schema': 'semabi.transport.w2_corpus_freeze.v1', 'created_utc': now, 'source_head': HEAD,
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
    full = {'schema': 'semabi.transport.w2_full_suite_freeze.v1', 'created_utc': now,
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
        'focused_results_manifest': {'path': str(focused / 'artifact_manifest_v2.json'), 'sha256': sha(focused / 'artifact_manifest_v2.json')},
        'prior_full_suite_source': {'path': str(PREDECESSOR / 'full_suite_source_freeze_v1.json'), 'sha256': sha(PREDECESSOR / 'full_suite_source_freeze_v1.json')},
        'verification_membership_scope': 'Every regular preparation/rendered file in this gate before freeze, accepted v3 objective and v2 test snapshots and focused evidence excluding its exact pytest scratch, plus unchanged dependencies. Final exact commands, GO and results are later records.',
        'scope': 'One canonical full-suite attempt under reviewed W2 source, separately authorized after freeze review. Five new corpus runs remain required; actual preserved W3 corpus results become comparison inputs through later separately hashed metadata.'}
    full_path = HERE / 'full_suite_source_freeze_v1.json'
    write(full_path, full)
    full_sha = sha(full_path)
    replacements = {'<W2_SOURCE_FREEZE_SHA256>': source_sha, '<W2_CORPUS_FREEZE_SHA256>': corpus_sha,
                    '<W2_FULL_SUITE_SOURCE_FREEZE_SHA256>': full_sha}
    commands['schema'] = 'semabi.transport.w2_validation_commands.v1'
    commands['status'] = 'NATIVE_COMMANDS_CONCRETE_COMPARISON_AWAITS_PRESERVED_INPUTS_NO_GO'
    commands['created_utc'] = now
    commands['freezes'] = {path.name: {'path': str(path), 'sha256': sha(path)} for path in (source_path, corpus_path, full_path)}
    commands['rendered_instruments'] = rendering['rendered_files']
    for name, job in commands['jobs'].items():
        job['status'] = 'CONCRETE_PREPARED_NOT_EXECUTED_ROOT_GO_REQUIRED'
        for field in ('inner_argv', 'outer_argv'):
            job[field] = [replacements.get(value, value) for value in job[field]]
        unresolved = [value for value in job['outer_argv'] if '<' in value or '>' in value]
        if name == 'corpus_comparison_v1':
            require(unresolved == ['<LATE_COMPARISON_INPUTS_SHA256>'], 'Unexpected late comparison placeholder')
            job['status'] = 'NOT_LAUNCHABLE_UNTIL_LATE_BINDING_AND_SEPARATE_GO'
        else:
            require(not unresolved, 'Unresolved native launch argv')
    for field in ('inner_argv', 'outer_argv'):
        row = commands['late_comparison_preparation']
        row[field] = [replacements.get(value, value) for value in row[field]]
    command_path = HERE / 'commands_v1.json'
    write(command_path, commands)
    receipt = {'schema': 'semabi.transport.w2_validation_freeze_creation.v1', 'created_utc': now,
        'status': 'FROZEN_NATIVE_COMMANDS_PREPARED_COMPARISON_PENDING_NO_GO', 'source_head': HEAD,
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
