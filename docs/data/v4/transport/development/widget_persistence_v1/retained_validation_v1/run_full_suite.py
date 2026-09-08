"""Run canonical full pytest selection with W1 primary-interpreter origins."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent


def load_guard(source_sha):
    path = HERE / 'source_freeze_v1.json'
    raw = path.read_bytes()
    if path.resolve(strict=True) != path or hashlib.sha256(raw).hexdigest() != source_sha:
        raise ValueError('Source freeze authentication failed')
    source = json.loads(raw)
    for path in (Path(__file__).resolve(), HERE / 'validation_guard.py'):
        raw = path.read_bytes()
        if path.resolve(strict=True) != path or source['verification_files'].get(path.relative_to(ROOT).as_posix()) != hashlib.sha256(raw).hexdigest():
            raise ValueError('Entry point or shared guard changed')
    guard = types.ModuleType('w1_validation_guard')
    guard.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), guard.__dict__)
    return guard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-freeze-sha256', required=True)
    parser.add_argument('--corpus-freeze-sha256', required=True)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('pytest_args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    guard = load_guard(args.source_freeze_sha256)
    source, _, _ = guard.verify(args.source_freeze_sha256, args.corpus_freeze_sha256)
    relative = HERE.relative_to(ROOT).as_posix()
    expected = ['--', '-q', 'tests', '--junitxml=' + relative + '/full_pytest_v1.xml',
                '--basetemp=' + relative + '/pytest_tmp_v1']
    guard.require(args.pytest_args == expected, 'Use the exact frozen full-suite pytest arguments')
    out = HERE / 'full_suite_v1'
    for path in (out, HERE / 'full_pytest_v1.xml', HERE / 'pytest_tmp_v1'):
        guard.require(not path.exists() and not path.is_symlink(), 'Full-suite identities are exclusive')
    plugins = [{'name': item.name, 'value': item.value, 'distribution': item.dist.name,
                'version': item.dist.version} for item in importlib.metadata.entry_points(group='pytest11')]
    guard.require(plugins == source['pytest_entry_points'] == [], 'Unfrozen external pytest plugin inventory')
    pytest_environment = {name: os.environ.get(name) for name in source['pytest_environment']}
    guard.require(pytest_environment == source['pytest_environment'], 'Unfrozen pytest environment override')
    if args.verify_only:
        print(json.dumps({'status': 'VERIFIED_WITHOUT_NATIVE_OR_PYTEST_IMPORT',
                          'source_freeze_sha256': args.source_freeze_sha256,
                          'corpus_freeze_sha256': args.corpus_freeze_sha256, 'pytest_args': expected[1:]}))
        return 0
    out.mkdir(exist_ok=False)
    record = guard.execution_record(args.source_freeze_sha256, args.corpus_freeze_sha256, 'PRIMARY_PYTEST_INTERPRETER')
    record['pytest_args'] = expected[1:]
    record['pytest_entry_points'] = plugins
    record['pytest_environment'] = pytest_environment
    record['subprocess_scope'] = source['full_suite_origin_scope']
    record['project_local_non_semabi_exec'] = {name: source['verification_files'][name] for name in
        ('scripts/v4_authority.py', 'scripts/v4_freeze_evaluator_inputs.py')}
    try:
        record['snapshots'].append(guard.anchor(source))
        import pytest
        before = guard.origins(source, 'before_pytest')
        record['snapshots'].append(before)
        guard.require(not before['violations'], 'Pre-pytest native origin violation')
        code = int(pytest.main(expected[1:]))
        record['pytest_returncode'] = code
        return code
    except BaseException as error:
        record['execution_error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        after = guard.origins(source, 'after_pytest_or_failure')
        record['snapshots'].append(after)
        try:
            guard.verify(args.source_freeze_sha256, args.corpus_freeze_sha256)
            guard.require(not after['violations'], 'Post-pytest native origin violation')
            record['postflight_status'] = 'VERIFIED'
        except BaseException as error:
            record['postflight_status'] = 'FAILED'
            record['postflight_error'] = f'{type(error).__name__}: {error}'
            raise
        finally:
            guard.write_json(out / 'import_origins_v1.json', record)


if __name__ == '__main__':
    raise SystemExit(main())
