"""Seal the reviewed B1 validation inventory without running native code."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
HEAD = '96b2d1f0efa573e675739f2d230b1e2245c088d5'
SOURCE_SHA = 'c40e565fb6f6fda6116a442a6291ba987e0d2e445ed8d63ec3f58082743b730d'
CORPUS_SHA = '09a2a3babd7b1337cd98affb8d71ea04e43ef48f5118bf5c7e96b62fd593b535'
G2_SHA = '481f879db351618431127a8f7a99db1a35ed06975c7f1f325347c9953a80d67e'
COMPARISON_SHA = 'ef415af9df5c4d48d658a29fb85209ef32e743e7107b9d62f0782fab516fc981'
CASES = ('allocation_positive', 'allocation_refusals', 'pilot', 'separating', 'separating_extended')
JOBS = {'full_pytest_v1': 'full_pytest_v1_v1.json',
        **{'corpus_' + case: case + '_v1.json' for case in CASES},
        'corpus_comparison_v1': 'corpus_comparison_v1.json'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    require(path.resolve(strict=True) == path and path.is_file(), 'Noncanonical artifact: ' + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path, expected=None):
    require(expected is None or sha(path) == expected, 'Changed authenticated artifact: ' + str(path))
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--proposal-sha', required=True)
    args = parser.parse_args()
    require(len(args.proposal_sha) == 64 and all(c in '0123456789abcdef' for c in args.proposal_sha), 'Expected approved proposal SHA-256')
    output = HERE / 'results_manifest_v1.json'
    require(not output.exists() and not output.is_symlink(), 'Final manifest identity already exists')
    proposal_path = HERE / 'artifact_manifest_proposal_v1.json'
    proposal = read(proposal_path, args.proposal_sha)
    require(proposal['schema'] == 'semabi.transport.b1_validation_artifact_proposal.v1'
            and proposal['source_head'] == HEAD, 'Wrong proposal')
    expected_names = set(proposal['files']) | {proposal_path.relative_to(ROOT).as_posix()}

    def verify_inventory():
        actual = set()
        for path in HERE.rglob('*'):
            require(not path.is_symlink(), 'Symlink in validation inventory')
            if path.is_dir():
                continue
            require(path.is_file(), 'Nonregular validation artifact')
            actual.add(path.relative_to(ROOT).as_posix())
        require(actual == expected_names, 'Validation artifact membership changed')
        for name, entry in proposal['files'].items():
            path = ROOT / name
            require(path.is_relative_to(HERE) and set(entry) == {'bytes', 'sha256'}, 'Invalid proposed artifact')
            require(path.stat().st_size == entry['bytes'] and sha(path) == entry['sha256'], 'Proposed artifact bytes changed: ' + name)
        require(sha(proposal_path) == args.proposal_sha, 'Proposal changed')

    verify_inventory()
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD, 'Worktree HEAD changed')
    require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--'], cwd=ROOT, text=True).strip(), 'Tracked worktree changed')
    source = read(HERE / 'source_freeze_v1.json', SOURCE_SHA)
    corpus = read(HERE / 'corpus_freeze_v1.json', CORPUS_SHA)
    require(source['source_head'] == corpus['source_head'] == HEAD, 'Freeze source differs')
    require(corpus['source_freeze']['sha256'] == SOURCE_SHA and corpus['files'] == source['files']
            and corpus['corpora'] == source['corpora'], 'Corpus/source link differs')
    frozen = {}
    for field in ('files', 'source_files', 'test_files', 'tracked_files', 'verification_files', 'suite_retained_run_files'):
        for name, expected in source[field].items():
            require(name not in frozen or frozen[name] == expected, 'Conflicting source inventory')
            frozen[name] = expected
    frozen.update(source['corpora']['files'])
    for name, expected in frozen.items():
        require(sha(ROOT / name) == expected, 'Frozen worktree bytes changed: ' + name)
    require(set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')[:-1]) == set(source['tracked_files']), 'Tracked inventory changed')
    for directory, field in (('semabi', 'source_files'), ('tests', 'test_files')):
        require({p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob('*.py')} == set(source[field]), 'Python source/test inventory changed')
    jobs = {}
    for name, receipt_name in JOBS.items():
        path = HERE / 'jobs' / name / 'process.json'
        job = read(path)
        receipt = read(HERE / 'terminal_receipts' / receipt_name)
        terminal = json.loads(receipt['output'])
        require(receipt['coordinator'] == '/root/baseline_verification' and receipt['exit_code'] == 0, 'Launcher receipt failed')
        require(job['status'] == terminal['status'] == 'FINISHED' and job['returncode'] == terminal['returncode'] == 0
                and job['child_terminated'] is terminal['child_terminated'] is True
                and job['child_pid'] == terminal['child_pid'] and job['end_utc'] == terminal['end_utc'], 'Job/terminal mismatch: ' + name)
        require(job['source_head'] == HEAD and job['source_hashes'] == source['source_files']
                and job['log_sha256'] == sha(path.parent / 'output.log'), 'Job source/log mismatch')
        jobs[name] = {'process': path.relative_to(ROOT).as_posix(),
                      'terminal_receipt': (HERE / 'terminal_receipts' / receipt_name).relative_to(ROOT).as_posix(),
                      'child_pid': job['child_pid'], 'tool_session_id': receipt['tool_session_id'],
                      'returncode': 0, 'child_terminated': True}
    suite = read(HERE / 'full_pytest_checks_v1.json')
    require(suite['status'] == 'VERIFIED' and suite['source_freeze_sha256'] == SOURCE_SHA
            and suite['testcases'] == 625 and suite['passed'] == 621, 'Suite verification differs')
    comparison = read(HERE / 'corpus_comparison_v1.json', COMPARISON_SHA)
    require(comparison['g2_results_manifest_sha256'] == G2_SHA
            and comparison['source_freeze_sha256'] == SOURCE_SHA
            and comparison['corpus_freeze_sha256'] == CORPUS_SHA
            and set(comparison['comparisons']) == set(CASES), 'Comparison association differs')
    for case in CASES:
        row = comparison['comparisons'][case]
        require(row['semantic_payloads_equal'] is True and row['differences'] == []
                and all(row['components_equal'].values()), 'Recorded regression differs')
    for phase, files in comparison['inputs'].items():
        root = Path(comparison['declared_roots'][phase])
        for name, expected in files.items():
            require(sha(root / name) == expected, 'Comparison input changed: ' + phase + ':' + name)
    verify_inventory()
    artifacts = dict(proposal['files'])
    artifacts[proposal_path.relative_to(ROOT).as_posix()] = {'bytes': proposal_path.stat().st_size, 'sha256': args.proposal_sha}
    record = {'schema': 'semabi.transport.b1_validation_results.v1', 'status': 'PRESERVED',
              'created_utc': datetime.now(timezone.utc).isoformat(), 'source_head': HEAD,
              'coordinator': '/root/baseline_verification', 'working_directory': str(ROOT),
              'source_freeze_sha256': SOURCE_SHA, 'corpus_freeze_sha256': CORPUS_SHA,
              'g2_results_manifest_sha256': G2_SHA, 'corpus_comparison_sha256': COMPARISON_SHA,
              'approved_proposal_sha256': args.proposal_sha, 'files': artifacts, 'jobs': jobs,
              'all_owned_jobs_terminated': True, 'unique_frozen_files_verified': len(frozen),
              'result': '621 passed, 3 skipped, 1 xfailed; five same-seed retained corpus payloads exactly equal preserved G2 under its six-component projection; all residual failures retained.',
              'scope': 'Isolated B1 development validation only; no fresh transport or semantic identification claim.'}
    with output.open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'path': output.relative_to(ROOT).as_posix(), 'sha256': sha(output), 'files': len(artifacts), 'jobs': len(jobs)}))


if __name__ == '__main__':
    main()
