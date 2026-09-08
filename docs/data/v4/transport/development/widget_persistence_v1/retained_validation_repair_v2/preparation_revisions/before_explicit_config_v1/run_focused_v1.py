"""Run the five existing cache-fixture tests with retained candidate custody."""
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

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prefix_state(preparation):
    prefix = Path(preparation['ambient_prefix'])
    state = {'runtime_prefix': sys.pycache_prefix, 'ambient_prefix': str(prefix),
             'exists': prefix.exists(), 'is_symlink': prefix.is_symlink(),
             'dont_write_bytecode': sys.dont_write_bytecode}
    require(prefix.is_absolute() and prefix.resolve() == prefix
            and not state['exists'] and not state['is_symlink'],
            'The unused ambient bytecode prefix must remain absent')
    require(sys.pycache_prefix == str(prefix) and sys.dont_write_bytecode
            and os.environ.get('PYTHONPYCACHEPREFIX') == str(prefix),
            'The runtime bytecode prefix or write policy was not restored')
    return state


def verify(preparation, expected_sha):
    require(sha(HERE / 'focused_preparation_v1.json') == expected_sha,
            'Focused preparation changed')
    require(preparation['schema'] == 'semabi.transport.w1_cache_repair_focused_preparation.v1'
            and preparation['working_directory'] == str(ROOT) and Path.cwd() == ROOT,
            'Wrong focused preparation or candidate worktree')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
            == preparation['base_source_head'], 'Candidate base commit changed')
    require(subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--'],
            cwd=ROOT, text=True).splitlines() == preparation['changed_tracked_files'],
            'The test-only candidate diff changed scope')
    require(all(os.environ.get(name) == value for name, value in preparation['environment'].items()),
            'Frozen process or pytest environment changed')
    require(sorted(os.sched_getaffinity(0)) == preparation['cpu_affinity']
            and os.getpriority(os.PRIO_PROCESS, 0) == 0, 'CPU affinity or priority changed')
    require(sys.version == preparation['python_version']
            and sys.executable == preparation['python_executable'], 'Interpreter changed')
    require(sorted((entry.name, entry.value) for entry in importlib.metadata.entry_points(group='pytest11'))
            == [tuple(entry) for entry in preparation['pytest_entry_points']],
            'Installed pytest entry points changed')
    prefix_state(preparation)
    for name, expected in preparation['files'].items():
        path = ROOT / name
        require(not Path(name).is_absolute() and all(part not in ('', '.', '..') for part in name.split('/'))
                and path.resolve(strict=True) == path and path.is_file()
                and sha(path) == expected, 'Frozen candidate file changed: ' + name)
    for directory, key in (('semabi', 'native_files'), ('tests', 'test_files')):
        require({path.relative_to(ROOT).as_posix() for path in (ROOT / directory).rglob('*.py')}
                == set(preparation[key]), 'Candidate Python membership changed: ' + directory)


def origins(preparation, phase):
    modules, violations = {}, []
    for name, module in sorted(sys.modules.copy().items()):
        if name != 'semabi' and not name.startswith('semabi.'):
            continue
        try:
            path = Path(module.__file__)
            relative = path.relative_to(ROOT).as_posix()
            require(path.is_absolute() and path.resolve(strict=True) == path and path.suffix == '.py',
                    'Native module lacks canonical Python source')
            require(preparation['native_files'].get(relative) == sha(path),
                    'Native source bytes differ')
            require(module.__spec__ is not None and module.__spec__.origin == str(path),
                    'Native module spec differs')
            package_paths = list(getattr(module, '__path__', []))
            require(not package_paths or package_paths == [str(path.parent)], 'Native package path differs')
            modules[name] = {'path': str(path), 'relative_path': relative, 'sha256': sha(path),
                             'spec_origin': module.__spec__.origin, 'package_paths': package_paths}
        except Exception as error:
            violations.append({'module': name, 'error': f'{type(error).__name__}: {error}',
                               'reported_file': str(getattr(module, '__file__', None))})
    return {'phase': phase, 'modules': modules, 'violations': violations}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--preparation-sha256', required=True)
    args = parser.parse_args()
    path = HERE / 'focused_preparation_v1.json'
    require(sha(path) == args.preparation_sha256, 'Focused preparation digest differs')
    preparation = json.loads(path.read_text())
    require(preparation['files'].get(Path(__file__).resolve().relative_to(ROOT).as_posix())
            == sha(Path(__file__).resolve()), 'Focused entry point changed')
    verify(preparation, args.preparation_sha256)
    require(not any(name == 'semabi' or name.startswith('semabi.') for name in sys.modules),
            'SemABI was imported before candidate authentication')
    output = HERE / 'focused_v1'
    output.mkdir(exist_ok=False)
    record = {'schema': 'semabi.transport.w1_cache_repair_focused_execution.v1',
              'created_utc': datetime.now(timezone.utc).isoformat(), 'cwd': str(ROOT),
              'base_source_head': preparation['base_source_head'],
              'candidate_status': 'UNCOMMITTED_TEST_ONLY_REPAIR',
              'preparation_sha256': args.preparation_sha256,
              'actual_command': [sys.executable, *sys.argv], 'pid': os.getpid(),
              'cpu_affinity': sorted(os.sched_getaffinity(0)), 'environment': preparation['environment'],
              'pytest_args': preparation['pytest_args'], 'snapshots': [], 'test_cache_checks': {},
              'scope': 'PRIMARY_PYTEST_INTERPRETER; the five selected tests declare no child interpreters.',
              'limitation': 'Source/path snapshots do not observe code objects or modules removed between boundaries. Per-test cache observations are boundary checks, not continuous filesystem tracing.'}
    try:
        sys.path.insert(0, str(ROOT))
        package = importlib.import_module('semabi')
        require(package.__file__ == str(ROOT / 'semabi/__init__.py')
                and list(package.__path__) == [str(ROOT / 'semabi')], 'Candidate package anchor differs')
        record['snapshots'].append(origins(preparation, 'before_pytest'))
        require(not record['snapshots'][-1]['violations'], 'Initial native origins differ')
        record['prefix_before_pytest'] = prefix_state(preparation)
        import pytest

        class CacheChecks:
            def pytest_collection_finish(self, session):
                record['collected_nodeids'] = [item.nodeid for item in session.items]
                require(record['collected_nodeids'] == preparation['test_nodeids'],
                        'Focused test collection differs')

            @pytest.hookimpl(wrapper=True, tryfirst=True)
            def pytest_runtest_makereport(self, item, call):
                report = yield
                if call.when != 'call' or 'tmp_path' not in item.funcargs:
                    return report
                temporary = item.funcargs['tmp_path']
                private = temporary / 'bytecode'
                paths = list(private.rglob('*'))
                row = {'private_root': str(private), 'temporary_root': str(temporary),
                       'private_root_present_after_call': private.is_dir(),
                       'private_directories_after_call': sum(path.is_dir() for path in paths),
                       'private_files_after_call': [str(path) for path in paths if path.is_file()],
                       'private_symlinks_after_call': [str(path) for path in paths if path.is_symlink()],
                       'call_outcome': report.outcome,
                       'call_exception': str(call.excinfo.value) if call.excinfo is not None else None}
                record['test_cache_checks'][item.nodeid] = row
                row['prefix_after_call'] = prefix_state(preparation)
                if report.passed:
                    require(private.resolve(strict=True) == private and row['private_root_present_after_call']
                            and not row['private_files_after_call'] and not row['private_symlinks_after_call'],
                            'Test-owned cache was not created or restored cleanly')
                return report

            def pytest_runtest_logreport(self, report):
                if report.when != 'teardown':
                    return
                row = record['test_cache_checks'].setdefault(report.nodeid, {})
                row['teardown_outcome'] = report.outcome
                row['prefix_after_teardown'] = prefix_state(preparation)
                if 'temporary_root' in row:
                    temporary = Path(row['temporary_root'])
                    row['temporary_root_absent_after_teardown'] = not temporary.exists() and not temporary.is_symlink()
                    if report.passed:
                        require(row['temporary_root_absent_after_teardown'], 'Test-owned temporary tree remains')

        code = int(pytest.main(preparation['pytest_args'], plugins=[CacheChecks()]))
        record['pytest_returncode'] = code
        record['pytest_version'] = pytest.__version__
        if code == 0:
            checks = record['test_cache_checks']
            require(set(checks) == set(preparation['test_nodeids']) and all(
                row.get('call_outcome') == row.get('teardown_outcome') == 'passed'
                and row.get('private_root_present_after_call') is True
                and row.get('private_files_after_call') == row.get('private_symlinks_after_call') == []
                and 'prefix_after_call' in row and 'prefix_after_teardown' in row
                and row.get('temporary_root_absent_after_teardown') is True
                for row in checks.values()), 'Successful pytest lacks complete five-test cache evidence')
    except BaseException as error:
        record['execution_error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        record['snapshots'].append(origins(preparation, 'after_pytest_or_failure'))
        try:
            require(not record['snapshots'][-1]['violations'], 'Final native origins differ')
            record['prefix_after_pytest'] = prefix_state(preparation)
            verify(preparation, args.preparation_sha256)
            record['postflight_status'] = 'VERIFIED'
        except BaseException as error:
            record['postflight_status'] = 'FAILED'
            record['postflight_error'] = f'{type(error).__name__}: {error}'
            raise
        finally:
            with (output / 'execution_v1.json').open('x') as stream:
                json.dump(record, stream, indent=2, sort_keys=True)
                stream.write('\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
