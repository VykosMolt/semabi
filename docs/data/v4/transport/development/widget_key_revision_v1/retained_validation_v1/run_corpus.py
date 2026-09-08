"""Run the unchanged baseline measurement with authenticated W3 imports."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import types

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
CASES = ('allocation_positive', 'allocation_refusals', 'pilot', 'separating', 'separating_extended')


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
    guard = types.ModuleType('w3_validation_guard')
    guard.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), guard.__dict__)
    return guard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=CASES)
    parser.add_argument('destination', type=Path)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--source-freeze-sha256', required=True)
    parser.add_argument('--corpus-freeze-sha256', required=True)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    guard = load_guard(args.source_freeze_sha256)
    source, corpus, corpus_root = guard.verify(args.source_freeze_sha256, args.corpus_freeze_sha256)
    out, snapshot = args.destination.absolute(), args.snapshot.absolute()
    guard.require(out == HERE / 'corpora' / args.case and snapshot == HERE / 'corpus_freeze_v1.json',
                  'Use canonical W3 corpus output and snapshot')
    guard.require(out.resolve() == out, 'Corpus output ancestry must be canonical')
    guard.require(not out.exists() and not out.is_symlink(), 'Corpus identities are exclusive')
    if args.verify_only:
        print(json.dumps({'status': 'VERIFIED_WITHOUT_NATIVE_OR_MEASUREMENT_IMPORT', 'case': args.case,
                          'source_freeze_sha256': args.source_freeze_sha256,
                          'corpus_freeze_sha256': args.corpus_freeze_sha256, 'input_files': 45, 'output': str(out)}))
        return
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(snapshot, out / 'source_snapshot.json')
    record = guard.execution_record(args.source_freeze_sha256, args.corpus_freeze_sha256, 'PRIMARY_CORPUS_INTERPRETER')
    measurement = ROOT / 'docs/data/v4/transport/baseline/check_corpora.py'
    adapter = {'schema': 'semabi.transport.w3_corpus_adapter.v1', 'owner': '/root',
               'actual_command': [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
               'cwd': str(ROOT), 'pid': os.getpid(), 'started_utc': datetime.now(timezone.utc).isoformat(),
               'source_head': guard.HEAD, 'source_freeze_sha256': args.source_freeze_sha256,
               'source_snapshot': str(snapshot), 'source_snapshot_sha256': args.corpus_freeze_sha256,
               'instrument': str(measurement), 'instrument_sha256': guard.sha(measurement),
               'adapter_sha256': guard.sha(Path(__file__)), 'corpus_root': str(corpus_root),
               'input_manifest_sha256': source['corpora']['manifest_sha256'], 'required_environment': guard.ENV,
               'bytecode_prefix': sys.pycache_prefix, 'affinity': sorted(os.sched_getaffinity(0)),
               'inherited_provenance': 'Unchanged baseline helper retains nominal owner and command; adapter and outer owned runner record the actual invocation.',
               'override': 'Only module.OUT and SEMABI_BASELINE_CORPORA route input/output. Candidate package anchoring precedes unchanged helper imports. Measurement and fit functions are unchanged.'}
    guard.write_json(out / 'adapter.json', adapter)
    completed = False
    try:
        record['snapshots'].append(guard.anchor(source))
        os.environ['SEMABI_BASELINE_CORPORA'] = str(corpus_root)
        guard.require('link_probe' not in sys.modules, 'Legacy helper was preloaded before authentication')
        spec = importlib.util.spec_from_file_location('w3_retained_baseline_measurement', measurement)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        guard.require(args.case in module.CASES and module.PREQ == corpus_root and module.ROOT == ROOT,
                      'Retained measurement resolved another source or input root')
        helper = ROOT / 'docs/data/v4/prequential/instruments/link_probe.py'
        guard.require(Path(sys.modules['link_probe'].__file__) == helper
                      and guard.sha(helper) == source['verification_files'][helper.relative_to(ROOT).as_posix()],
                      'Retained helper import origin differs')
        record['measurement_helper_origin'] = {'path': str(helper), 'sha256': guard.sha(helper)}
        before = guard.origins(source, 'before_measurement')
        record['snapshots'].append(before)
        guard.require(not before['violations'], 'Pre-measurement native origin violation')
        module.OUT = out
        module.main(args.case)
        completed = True
    except BaseException as error:
        record['execution_error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        after = guard.origins(source, 'after_measurement_or_failure')
        record['snapshots'].append(after)
        record['measurement_returned'] = completed
        try:
            guard.verify(args.source_freeze_sha256, args.corpus_freeze_sha256)
            guard.require(not after['violations'], 'Post-measurement native origin violation')
            record['postflight_status'] = 'VERIFIED'
        except BaseException as error:
            record['postflight_status'] = 'FAILED'
            record['postflight_error'] = f'{type(error).__name__}: {error}'
            raise
        finally:
            guard.write_json(out / 'import_origins_v1.json', record)
        if completed:
            guard.write_json(out / 'adapter_postflight.json', {'status': 'VERIFIED',
                'ended_utc': datetime.now(timezone.utc).isoformat(),
                'source_freeze_sha256': args.source_freeze_sha256, 'source_snapshot_sha256': args.corpus_freeze_sha256,
                'all_frozen_source_and_inputs_unchanged': True,
                'import_origins_sha256': guard.sha(out / 'import_origins_v1.json')})


if __name__ == '__main__':
    main()
