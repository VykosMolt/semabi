"""Run the W2 objective development test file with a frozen native source boundary."""
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
import traceback


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(freeze):
    root = Path(freeze['working_directory'])
    require(root.resolve(strict=True) == root and Path.cwd() == root, 'Wrong native worktree')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
            == freeze['source_head'], 'Source HEAD changed')
    dirty = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--'], cwd=root, text=True).splitlines()
    require(sorted(dirty) == freeze['expected_tracked_changes'], 'Unexpected tracked source change')
    require(sys.executable == freeze['python_executable'] and sys.version == freeze['python_version'],
            'Python runtime changed')
    require(sys.flags.safe_path and sys.dont_write_bytecode and sys.flags.optimize == 0,
            'Safe path, disabled bytecode and normal optimization are required')
    require(sorted(os.sched_getaffinity(0)) == freeze['cpu_affinity']
            and os.getpriority(os.PRIO_PROCESS, 0) == 0, 'CPU or priority changed')
    require({name: os.environ.get(name) for name in freeze['environment']} == freeze['environment'],
            'Frozen environment changed')
    require(importlib.metadata.version('pytest') == freeze['pytest_version']
            and sorted((entry.name, entry.value) for entry in importlib.metadata.entry_points(group='pytest11'))
            == [tuple(entry) for entry in freeze['pytest_entry_points']], 'Pytest or plugin metadata changed')
    prefix = Path(freeze['environment']['PYTHONPYCACHEPREFIX'])
    require(sys.pycache_prefix == str(prefix) and not prefix.exists() and not prefix.is_symlink(),
            'Ambient bytecode prefix changed or acquired files')
    for collection, base in (('files', root), ('external_files', Path('/'))):
        for name, digest in freeze[collection].items():
            path = base / name
            require(path.resolve(strict=True) == path and path.is_file() and sha(path) == digest,
                    'Frozen source changed: ' + str(path))
    require({p.relative_to(root).as_posix() for p in (root / 'semabi').rglob('*.py')}
            == set(freeze['native_files']), 'Native Python membership changed')
    return {'verified_files': len(freeze['files']), 'verified_external_files': len(freeze['external_files']),
            'ambient_prefix_absent': True}


def origins(freeze):
    root = Path(freeze['working_directory'])
    modules, violations = {}, []
    for name, module in sorted(sys.modules.items()):
        if name != 'semabi' and not name.startswith('semabi.'):
            continue
        filename = getattr(module, '__file__', None)
        spec = getattr(module, '__spec__', None)
        row = {'file': filename, 'spec_origin': getattr(spec, 'origin', None),
               'package_paths': list(getattr(module, '__path__', [])),
               'spec_package_paths': list(getattr(spec, 'submodule_search_locations', None) or [])}
        modules[name] = row
        try:
            path = Path(filename)
            relative = path.relative_to(root).as_posix()
            expected_paths = [str(path.parent)] if path.name == '__init__.py' else []
            require(path.resolve(strict=True) == path and relative in freeze['native_files']
                    and sha(path) == freeze['native_files'][relative]
                    and row['spec_origin'] == filename and row['package_paths'] == expected_paths
                    and row['spec_package_paths'] == expected_paths, 'origin mismatch')
        except (ValueError, TypeError, OSError) as error:
            violations.append({'module': name, 'error': str(error)})
    return {'modules': modules, 'violations': violations}


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--freeze', required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    freeze_path = Path(args.freeze)
    require(sha(freeze_path) == args.sha256, 'Source-freeze digest changed')
    freeze = json.loads(freeze_path.read_text())
    require(freeze['schema'] == 'semabi.widget_observation.focused_freeze.v1', 'Wrong focused schema')
    require(freeze['external_files'].get(str(Path(__file__).resolve())) == sha(Path(__file__)),
            'Focused entrypoint changed')
    preflight = verify(freeze)
    require(not any(n == 'semabi' or n.startswith('semabi.') for n in sys.modules),
            'SemABI imported before source authentication')
    require(freeze['pytest_args'] == ['-q', '-c', 'pytest.ini', '--noconftest',
            'tests/test_v4_objective.py',
            '--junitxml=' + freeze['junit'], '--basetemp=' + freeze['basetemp']], 'Focused pytest selection changed')
    for name in ('result', 'junit', 'basetemp'):
        path = Path(freeze[name])
        require(not path.exists() and not path.is_symlink(), 'Focused output identity already exists: ' + name)
    record = {'schema': 'semabi.widget_observation.focused_execution.v1',
              'created_utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
              'source_head': freeze['source_head'], 'source_freeze_sha256': args.sha256,
              'working_directory': str(Path.cwd()), 'argv': sys.orig_argv,
              'environment': {name: os.environ.get(name) for name in freeze['environment']},
              'cpu_affinity': sorted(os.sched_getaffinity(0)), 'priority': os.getpriority(os.PRIO_PROCESS, 0),
              'interpreter_flags': {'safe_path': sys.flags.safe_path, 'optimize': sys.flags.optimize,
                                    'dont_write_bytecode': sys.dont_write_bytecode},
              'preflight': preflight, 'pytest_args': freeze['pytest_args'], 'snapshots': [],
              'scope': 'Primary pytest interpreter source/path snapshots, not executed-code-object or child-module coverage.'}
    code = None
    try:
        root = Path(freeze['working_directory'])
        sys.path.insert(0, str(root))
        package = importlib.import_module('semabi')
        require(package.__file__ == str(root / 'semabi/__init__.py')
                and list(package.__path__) == [str(root / 'semabi')], 'Candidate package anchor differs')
        record['snapshots'].append(origins(freeze))
        require(not record['snapshots'][-1]['violations'], 'Initial native origins differ')
        import pytest
        code = int(pytest.main(freeze['pytest_args']))
        record['pytest_returncode'] = code
    except BaseException:
        record['execution_error'] = traceback.format_exc()
        raise
    finally:
        try:
            record['snapshots'].append(origins(freeze))
            require(not record['snapshots'][-1]['violations'], 'Final native origins differ')
            require(sha(freeze_path) == args.sha256, 'Source freeze changed during execution')
            record['postflight'] = verify(freeze)
            record['postflight_status'] = 'VERIFIED'
        except BaseException:
            record['postflight_status'] = 'FAILED'
            record['postflight_error'] = traceback.format_exc()
            raise
        finally:
            with Path(freeze['result']).open('x') as stream:
                json.dump(record, stream, indent=2, sort_keys=True)
                stream.write('\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
