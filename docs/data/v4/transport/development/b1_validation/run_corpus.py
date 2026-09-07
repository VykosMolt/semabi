"""Route the unchanged baseline measurement through frozen B1 worktree inputs."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'docs/data/v4/transport/baseline'
SOURCE = HERE / 'source_freeze_v1.json'
SOURCE_SHA = 'c40e565fb6f6fda6116a442a6291ba987e0d2e445ed8d63ec3f58082743b730d'
HEAD = '96b2d1f0efa573e675739f2d230b1e2245c088d5'
CASES = ('allocation_positive', 'allocation_refusals', 'pilot', 'separating', 'separating_extended')
ENV = {name: '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                             'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS')}
ENV['PYTHONHASHSEED'] = '0'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(name):
    if not isinstance(name, str) or not name or Path(name).is_absolute() or any(part in ('', '.', '..') for part in name.split('/')):
        raise ValueError('Expected canonical worktree-relative file')
    path = ROOT / name
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError('Expected actual worktree file: ' + name)
    return path


def verify_files(files):
    if not isinstance(files, dict) or not files:
        raise ValueError('Expected nonempty frozen inventory')
    for name, expected in files.items():
        if sha(checked(name)) != expected:
            raise ValueError('Frozen bytes changed: ' + name)


def verify(case, destination, snapshot):
    if any(os.environ.get(name) != expected for name, expected in ENV.items()):
        raise ValueError('Use the frozen one-thread and hash-seed environment')
    if case not in CASES or destination != HERE / 'corpora' / case:
        raise ValueError('Use the canonical new output for this B1 corpus case')
    if snapshot != HERE / 'corpus_freeze_v1.json' or snapshot.resolve(strict=True) != snapshot:
        raise ValueError('Use the exact B1 corpus freeze')
    if SOURCE.resolve(strict=True) != SOURCE or sha(SOURCE) != SOURCE_SHA:
        raise ValueError('The reviewed isolated B1 source freeze changed')
    source, record = json.loads(SOURCE.read_text()), json.loads(snapshot.read_text())
    if (source['schema'] != 'semabi.transport.b1_validation_freeze.v1'
            or record['schema'] != 'semabi.transport.b1_corpus_freeze.v1'
            or record['source_head'] != HEAD or source['source_head'] != HEAD
            or subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != HEAD):
        raise ValueError('Wrong B1 phase or source commit')
    if record['source_freeze'] != {'path': SOURCE.relative_to(ROOT).as_posix(), 'sha256': SOURCE_SHA}:
        raise ValueError('Corpus extension belongs to a different source freeze')
    if record['files'] != source['files'] or record['corpora'] != source['corpora']:
        raise ValueError('Corpus extension changed runtime or input commitments')
    expected_verification = {**source['verification_files'],
        SOURCE.relative_to(ROOT).as_posix(): SOURCE_SHA,
        (HERE / 'run_corpus.py').relative_to(ROOT).as_posix(): sha(HERE / 'run_corpus.py'),
        (HERE / 'corpus_plan_v1.md').relative_to(ROOT).as_posix(): sha(HERE / 'corpus_plan_v1.md')}
    if record['verification_files'] != expected_verification:
        raise ValueError('Corpus extension verification inventory differs')
    verify_files(source['source_files'])
    actual_source = {path.relative_to(ROOT).as_posix() for path in (ROOT / 'semabi').rglob('*.py')}
    if actual_source != set(source['source_files']):
        raise ValueError('SemABI source file inventory differs')
    verify_files(record['files'])
    verify_files(record['verification_files'])
    metadata = record['corpora']
    manifest_path = checked(metadata['manifest'])
    if sha(manifest_path) != metadata['manifest_sha256']:
        raise ValueError('Persistent input manifest changed')
    manifest = json.loads(manifest_path.read_text())
    corpus_root = ROOT / manifest['root']
    if (corpus_root != ROOT / 'runs/v4/transport_g1_corpora_v1'
            or metadata['root'] != manifest['root'] or len(manifest['files']) != 45):
        raise ValueError('Expected the exact persistent G1/G2 input root')
    expected_inputs = {(corpus_root / name).relative_to(ROOT).as_posix(): digest for name, digest in manifest['files'].items()}
    if metadata['files'] != expected_inputs:
        raise ValueError('Corpus file commitment differs from the retained manifest')
    verify_files(expected_inputs)
    actual_inputs = {path.relative_to(corpus_root).as_posix() for path in corpus_root.rglob('*') if path.is_file()}
    if actual_inputs != set(manifest['files']):
        raise ValueError('Unexpected or missing persistent input')
    return record, corpus_root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=CASES)
    parser.add_argument('destination', type=Path)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    out, snapshot = args.destination.absolute(), args.snapshot.absolute()
    source, corpus_root = verify(args.case, out, snapshot)
    if out.exists() or out.is_symlink():
        raise FileExistsError('Corpus result identities are exclusive')
    if args.verify_only:
        print(json.dumps({'status': 'VERIFIED_WITHOUT_MEASUREMENT_IMPORT', 'case': args.case,
                          'source_freeze_sha256': SOURCE_SHA, 'corpus_freeze_sha256': sha(snapshot),
                          'input_files': len(source['corpora']['files']), 'output': str(out)}))
        return
    os.environ['SEMABI_BASELINE_CORPORA'] = str(corpus_root)
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location('b1_retained_baseline_measurement', BASE / 'check_corpora.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if args.case not in module.CASES or module.PREQ != corpus_root or module.ROOT != ROOT:
        raise ValueError('Retained measurement uses another source or input root')
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(snapshot, out / 'source_snapshot.json')
    adapter = {'schema': 'semabi.transport.b1_corpus_adapter.v1', 'owner': '/root/baseline_verification',
               'actual_command': [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
               'cwd': str(ROOT), 'pid': os.getpid(), 'started_utc': datetime.now(timezone.utc).isoformat(),
               'source_head': HEAD, 'source_freeze_sha256': SOURCE_SHA,
               'source_snapshot': str(snapshot), 'source_snapshot_sha256': sha(snapshot),
               'instrument': str(BASE / 'check_corpora.py'), 'instrument_sha256': sha(BASE / 'check_corpora.py'),
               'adapter_sha256': sha(Path(__file__)), 'corpus_root': str(corpus_root),
               'input_manifest_sha256': source['corpora']['manifest_sha256'], 'required_environment': ENV,
               'affinity': sorted(os.sched_getaffinity(0)),
               'inherited_provenance': 'Unchanged baseline helper retains its nominal owner and command; this adapter and outer owned runner identify the actual invocation.',
               'override': 'Only module.OUT and SEMABI_BASELINE_CORPORA route authenticated input/output. Baseline measurement and fit functions are unchanged.'}
    (out / 'adapter.json').write_text(json.dumps(adapter, indent=2, sort_keys=True) + '\n')
    module.OUT = out
    module.main(args.case)
    verify(args.case, out, snapshot)
    (out / 'adapter_postflight.json').write_text(json.dumps({'status': 'VERIFIED', 'ended_utc': datetime.now(timezone.utc).isoformat(),
        'source_freeze_sha256': SOURCE_SHA, 'source_snapshot_sha256': sha(snapshot),
        'all_frozen_source_and_inputs_unchanged': True}, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
