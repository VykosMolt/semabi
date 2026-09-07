"""Freeze the unchanged isolated B1 checkout and exact retained input copies."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
MAIN = Path('/home/moloch/semabi')
HEAD = '96b2d1f0efa573e675739f2d230b1e2245c088d5'
G2_SHA = '3f88423e84622313263c097a289fb4c8fddb2a0d8d2d56176186229759848df6'
CHANGES = {
    'semabi/compiler/v4/binding.py': '0f905cae535aa975dffe517f1107884f37524fdc3cbcc781ec7f645cd0f9b0dc',
    'semabi/compiler/v4/consequence.py': 'c95bd040c8b066aaaac5bb5653b2ff20824ed3f2b59aba81c42b8a579ca8445e',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError('Expected an actual regular worktree file: ' + str(path))
    return path.relative_to(ROOT).as_posix()


def hashes(paths):
    return {relative(path): sha(path) for path in sorted(paths)}


def main():
    output = HERE / 'source_freeze_v1.json'
    if output.exists() or output.is_symlink():
        raise FileExistsError('Immutable B1 source freeze already exists')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if head != HEAD:
        raise ValueError('Not the reviewed B1 commit')
    tracked_names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')[:-1]
    tracked = hashes(ROOT / name for name in tracked_names)
    if subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--'], cwd=ROOT, text=True).strip():
        raise ValueError('Tracked worktree differs from the reviewed commit')
    prior_path = MAIN / 'docs/data/v4/transport/development/g2/freeze_v1.json'
    if sha(prior_path) != G2_SHA:
        raise ValueError('Authenticated G2 phase freeze changed')
    prior = json.loads(prior_path.read_text())
    runtime = {name: sha(ROOT / name) for name in prior['files']
               if not name.startswith('docs/data/v4/transport/first_pass/')}
    differences = {name: actual for name, actual in runtime.items() if actual != prior['files'][name]}
    if differences != CHANGES:
        raise ValueError('Runtime differs from G2 beyond the two reviewed B1 changes')
    compiler = {relative(path) for path in (ROOT / 'semabi/compiler').rglob('*.py')}
    if compiler != {name for name in runtime if name.startswith('semabi/compiler/')}:
        raise ValueError('Compiler inventory differs')
    manifest_path = ROOT / 'docs/data/v4/transport/development/g1/rebuild_v1/input_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    corpus_root = ROOT / manifest['root']
    if len(manifest['files']) != 45 or corpus_root != ROOT / 'runs/v4/transport_g1_corpora_v1':
        raise ValueError('Expected exact persistent G1/G2 corpus inventory')
    inputs = hashes(corpus_root / name for name in manifest['files'])
    if {name: sha(corpus_root / name) for name in manifest['files']} != manifest['files']:
        raise ValueError('Copied corpus bytes differ')
    if {path.relative_to(corpus_root).as_posix() for path in corpus_root.rglob('*') if path.is_file()} != set(manifest['files']):
        raise ValueError('Copied corpus membership differs')
    verification_paths = [HERE / name for name in ('plan_v1.md', 'freeze_validation_v1.py', 'input_copy_v1.json', 'import_check_v1.json')]
    verification_paths += [ROOT / name for name in ('docs/data/v4/transport/run_job.py', 'docs/data/v4/transport/baseline/check_corpora.py', 'docs/data/v4/prequential/instruments/link_probe.py', 'pyproject.toml', 'pytest.ini')]
    suite_runs = hashes(path for name in ('harbour_transfer', 'blend_book_transfer', 'harbour_dev')
                        for path in (ROOT / 'runs/v4' / name).rglob('*') if path.is_file())
    record = {
        'schema': 'semabi.transport.b1_validation_freeze.v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_head': head, 'working_directory': str(ROOT), 'coordinator': '/root/baseline_verification',
        'prior_g2': {'path': str(prior_path), 'sha256': G2_SHA, 'source_head': prior['source_head']},
        'reviewed_runtime_changes': CHANGES, 'files': runtime,
        'source_files': hashes((ROOT / 'semabi').rglob('*.py')),
        'test_files': hashes((ROOT / 'tests').rglob('*.py')),
        'tracked_files': tracked, 'verification_files': hashes(verification_paths),
        'suite_retained_run_files': suite_runs,
        'corpora': {'manifest': relative(manifest_path), 'manifest_sha256': sha(manifest_path), 'root': manifest['root'], 'files': inputs},
        'scope': 'B1 clean worktree validation preparation only. Runtime files exclude archived, fixture, oracle and evaluator paths. Whole tracked-file hashes are custody metadata, not learner input.',
    }
    with output.open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'path': relative(output), 'sha256': sha(output), 'runtime_files': len(runtime),
                      'source_files': len(record['source_files']), 'test_files': len(record['test_files']),
                      'tracked_files': len(tracked), 'corpus_files': len(inputs), 'suite_run_files': len(suite_runs)}))


if __name__ == '__main__':
    main()
