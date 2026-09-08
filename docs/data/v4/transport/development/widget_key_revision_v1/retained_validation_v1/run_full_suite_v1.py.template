"""Run the canonical full suite at the independently reviewed W3 source checkpoint."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
CONFIG_NAMES = ('pytest.toml', '.pytest.toml', 'pytest.ini', '.pytest.ini',
                'pyproject.toml', 'tox.ini', 'setup.cfg', 'conftest.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_files(files, root):
    for name, expected in files.items():
        path = root / name
        require(not Path(name).is_absolute() and all(part not in ('', '.', '..') for part in name.split('/'))
                and path.resolve(strict=True) == path and path.is_file()
                and sha(path) == expected, 'Frozen file changed: ' + str(path))


def discovery(freeze):
    expected = freeze['pytest_discovery']
    require(set(expected['files']) == {name for name in CONFIG_NAMES}
            | {'tests/' + name for name in CONFIG_NAMES}, 'Incomplete pytest discovery binding')
    for name, entry in expected['files'].items():
        path = ROOT / name
        if entry['present']:
            require(path.resolve(strict=True) == path and path.is_file()
                    and sha(path) == entry['sha256'], 'Pytest discovery file changed: ' + name)
        else:
            require(not path.exists() and not path.is_symlink(), 'Unexpected pytest discovery input: ' + name)
    members = list((ROOT / 'tests').iterdir())
    require({path.name for path in members} == set(expected['test_directory_members'])
            and all(path.is_file() and not path.is_symlink() for path in members),
            'The flat canonical test discovery inventory changed')
    return {'files': expected['files'], 'test_directory_member_count': len(members),
            'expected_selected_config': expected['expected_selected_config'],
            'selection_basis': expected['selection_basis']}


def verify(freeze, expected_sha, helpers):
    require(Path.cwd() == ROOT and freeze['working_directory'] == str(ROOT)
            and freeze['schema'] == 'semabi.transport.w3_full_suite_freeze.v1',
            'Wrong full-suite source or worktree')
    require(sha(HERE / 'full_suite_source_freeze_v1.json') == expected_sha, 'Full-suite source freeze changed')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
            == freeze['source_head'], 'Committed candidate source changed')
    require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--'], cwd=ROOT, text=True).strip(),
            'Committed candidate has tracked changes')
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')) - {''}
    require(tracked == set(freeze['tracked_files']), 'Tracked source membership changed')
    require(all(os.environ.get(name) == expected for name, expected in freeze['environment'].items()),
            'Frozen process or pytest environment changed')
    require(sorted(os.sched_getaffinity(0)) == freeze['cpu_affinity']
            and os.getpriority(os.PRIO_PROCESS, 0) == 0, 'CPU affinity or priority changed')
    require(sys.version == freeze['python_version'] and sys.executable == freeze['python_executable'],
            'Interpreter changed')
    require(sys.flags.safe_path, 'Interpreter must suppress the implicit startup path')
    require(sys.flags.optimize == 0, 'Interpreter optimization would change exercised semantics')
    require(importlib.metadata.version('pytest') == freeze['pytest_version']
            and sorted((entry.name, entry.value) for entry in importlib.metadata.entry_points(group='pytest11'))
            == [tuple(entry) for entry in freeze['pytest_entry_points']], 'Installed pytest/plugin metadata changed')
    helpers.prefix_state(freeze)
    verify_files(freeze['files'], ROOT)
    for directory, key in (('semabi', 'native_files'), ('tests', 'test_files')):
        require({path.relative_to(ROOT).as_posix() for path in (ROOT / directory).rglob('*.py')}
                == set(freeze[key]), 'Candidate Python membership changed: ' + directory)
    for absolute, expected in freeze['retained_external_files'].items():
        path = Path(absolute)
        require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file()
                and sha(path) == expected, 'Retained dependency changed: ' + absolute)
    for name in ('harbour_transfer', 'blend_book_transfer', 'harbour_dev'):
        actual = {path.relative_to(ROOT).as_posix() for path in (ROOT / 'runs/v4' / name).rglob('*') if path.is_file()}
        expected = {path for path in freeze['suite_retained_run_files'] if path.startswith('runs/v4/' + name + '/')}
        require(actual == expected, 'Retained suite data membership changed: ' + name)
    return discovery(freeze)


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--source-freeze-sha256', required=True)
    args = parser.parse_args()
    path = HERE / 'full_suite_source_freeze_v1.json'
    require(sha(path) == args.source_freeze_sha256, 'Full-suite source-freeze digest differs')
    freeze = json.loads(path.read_text())
    for entry in (Path(__file__).resolve(), HERE / 'retained_full_suite_helpers.py'):
        require(freeze['verification_files'].get(entry.relative_to(ROOT).as_posix()) == sha(entry),
                'Full-suite entry point or retained helper source changed')
    helper_path = HERE / 'retained_full_suite_helpers.py'
    helpers = types.ModuleType('w1_cache_repair_boundary_helpers')
    helpers.__file__ = str(helper_path)
    exec(compile(helper_path.read_bytes(), str(helper_path), 'exec'), helpers.__dict__)
    before_discovery = verify(freeze, args.source_freeze_sha256, helpers)
    require(not any(name == 'semabi' or name.startswith('semabi.') for name in sys.modules),
            'SemABI was imported before candidate authentication')
    require(freeze['pytest_args'] == ['-q', 'tests',
            '--junitxml=' + (HERE / 'full_pytest_v1.xml').relative_to(ROOT).as_posix(),
            '--basetemp=' + (HERE / 'full_pytest_tmp_v1').relative_to(ROOT).as_posix()],
            'Canonical pytest arguments changed')
    for output in (HERE / 'full_suite_v1', HERE / 'full_pytest_v1.xml', HERE / 'full_pytest_tmp_v1'):
        require(not output.exists() and not output.is_symlink(), 'Full-suite output identity already exists')
    output = HERE / 'full_suite_v1'
    output.mkdir()
    record = {'schema': 'semabi.transport.w3_full_suite_execution.v1',
              'created_utc': datetime.now(timezone.utc).isoformat(), 'source_head': freeze['source_head'],
              'source_freeze_sha256': args.source_freeze_sha256, 'working_directory': str(ROOT),
              'actual_command': [sys.executable, *sys.argv], 'pid': os.getpid(),
              'cpu_affinity': sorted(os.sched_getaffinity(0)), 'environment': freeze['environment'],
              'interpreter_flags': {'safe_path': sys.flags.safe_path,
                                    'dont_write_bytecode': sys.dont_write_bytecode,
                                    'optimize': sys.flags.optimize},
              'pytest_args': freeze['pytest_args'], 'pytest_version': freeze['pytest_version'],
              'pytest_entry_points': freeze['pytest_entry_points'],
              'discovery_before_pytest': before_discovery,
              'scope': 'PRIMARY_PYTEST_INTERPRETER', 'subprocess_scope': freeze['subprocess_scope'],
              'project_local_non_semabi_exec': freeze['project_local_non_semabi_exec'],
              'snapshots': [], 'limitation': 'Native source/path snapshots cover modules present at the two boundaries; they do not observe removed modules, child module tables or executed code objects. Configuration selection is source-derived from frozen discovery inputs and installed pytest discovery code.'}
    try:
        sys.path.insert(0, str(ROOT))
        package = importlib.import_module('semabi')
        require(package.__file__ == str(ROOT / 'semabi/__init__.py')
                and list(package.__path__) == [str(ROOT / 'semabi')], 'Candidate package anchor differs')
        record['snapshots'].append(helpers.origins(freeze, 'before_pytest'))
        require(not record['snapshots'][-1]['violations'], 'Initial native origins differ')
        record['prefix_before_pytest'] = helpers.prefix_state(freeze)
        import pytest
        code = int(pytest.main(freeze['pytest_args']))
        record['pytest_returncode'] = code
    except BaseException as error:
        record['execution_error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        record['snapshots'].append(helpers.origins(freeze, 'after_pytest_or_failure'))
        try:
            require(not record['snapshots'][-1]['violations'], 'Final native origins differ')
            record['prefix_after_pytest'] = helpers.prefix_state(freeze)
            record['discovery_after_pytest'] = verify(freeze, args.source_freeze_sha256, helpers)
            record['postflight_status'] = 'VERIFIED'
        except BaseException as error:
            record['postflight_status'] = 'FAILED'
            record['postflight_error'] = f'{type(error).__name__}: {error}'
            raise
        finally:
            with (output / 'import_origins_v1.json').open('x') as stream:
                json.dump(record, stream, indent=2, sort_keys=True)
                stream.write('\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
