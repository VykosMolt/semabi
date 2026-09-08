"""Bind corpus inputs from preserved six-job W3/W2 phases without native execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
W3_ROOT = Path('/home/moloch/semabi/runs/.w3_repair_worktree')
W3 = W3_ROOT / 'docs/data/v4/transport/development/widget_key_revision_repair_v1/validation_gate_v1'
W3_HEAD = 'aaa9b5df915464754341794179b5297cf22f6140'
CASES = ('allocation_positive', 'allocation_refusals', 'pilot', 'separating', 'separating_extended')
OWNED_JOBS = sorted(['full_pytest_v1', *('corpus_' + case for case in CASES)])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(path, expected=None):
    require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file(),
            'Expected canonical regular metadata or preserved artifact')
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    require(expected is None or digest == expected, 'Frozen or preserved bytes changed: ' + str(path))
    return content, {'bytes': len(content), 'sha256': digest}


def read(path, expected=None):
    content, binding = raw(path, expected)
    return json.loads(content), binding


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--w3-manifest', type=Path, required=True)
    parser.add_argument('--w3-manifest-sha256', required=True)
    parser.add_argument('--w2-manifest', type=Path, required=True)
    parser.add_argument('--w2-manifest-sha256', required=True)
    parser.add_argument('--source-freeze-sha256', required=True)
    parser.add_argument('--corpus-freeze-sha256', required=True)
    args = parser.parse_args()
    require(Path.cwd() == ROOT, 'Run from the W2 worktree')
    output = HERE / 'comparison_inputs_v1.json'
    require(not output.exists() and not output.is_symlink(), 'Comparison binding identity is exclusive')
    source, _ = read(HERE / 'source_freeze_v1.json', args.source_freeze_sha256)
    corpus, _ = read(HERE / 'corpus_freeze_v1.json', args.corpus_freeze_sha256)
    require(source['schema'] == 'semabi.transport.w2_validation_freeze.v1'
            and corpus['schema'] == 'semabi.transport.w2_corpus_freeze.v1'
            and source['source_head'] == corpus['source_head']
            and source['working_directory'] == corpus['working_directory'] == str(ROOT),
            'Wrong candidate source/corpus commitment')
    policy_path = HERE / 'comparison_policy_v1.json'
    for path in (Path(__file__).resolve(), policy_path):
        raw(path, source['verification_files'][path.relative_to(ROOT).as_posix()])
    policy, policy_binding = read(policy_path)
    require(policy['schema'] == 'semabi.transport.w2_comparison_policy.v1'
            and policy['predecessor']['source_head'] == W3_HEAD
            and policy['predecessor']['working_directory'] == str(W3_ROOT)
            and policy['predecessor']['gate_directory'] == str(W3)
            and policy['candidate']['source_head'] == source['source_head']
            and policy['candidate']['working_directory'] == str(ROOT)
            and policy['candidate']['gate_directory'] == str(HERE)
            and set(policy['cases']) == set(CASES), 'Prepared comparison identity differs')
    phases = {}
    authenticated = {}
    for phase, root, base, path, expected, head, source_sha, corpus_sha in (
            ('W3', W3_ROOT, W3, args.w3_manifest, args.w3_manifest_sha256, W3_HEAD,
             policy['predecessor']['source_freeze_sha256'], policy['predecessor']['corpus_freeze_sha256']),
            ('W2', ROOT, HERE, args.w2_manifest, args.w2_manifest_sha256, source['source_head'],
             args.source_freeze_sha256, args.corpus_freeze_sha256)):
        require(path.is_absolute() and path.is_relative_to(base), 'Use a preserved manifest inside its declared gate')
        manifest, manifest_binding = read(path, expected)
        require(manifest['status'] == 'PRESERVED' and manifest['all_owned_jobs_terminated'] is True
                and manifest['owned_job_names'] == OWNED_JOBS
                and manifest['source_head'] == head and manifest['working_directory'] == str(root)
                and manifest['source_freeze_sha256'] == source_sha
                and manifest['corpus_freeze_sha256'] == corpus_sha,
                'Corpus phase has no matching completed preservation manifest')
        required = [base / 'source_freeze_v1.json', base / 'corpus_freeze_v1.json',
                    base / 'full_suite_source_freeze_v1.json']
        result_files = {}
        for case in CASES:
            directory = base / 'corpora' / case
            required += [directory / name for name in (
                case + '.json', case + '_fit.json', case + '_partial.json', case + '_process.json',
                'source_snapshot.json', 'adapter.json', 'adapter_postflight.json', 'import_origins_v1.json')]
            required += [base / 'jobs' / ('corpus_' + case) / name for name in ('process.json', 'output.log')]
        for artifact in required:
            name = artifact.relative_to(root).as_posix()
            entry = manifest['files'][name]
            require(set(entry) == {'bytes', 'sha256'}, 'Preservation file record differs')
            _, actual = raw(artifact, entry['sha256'])
            require(actual == entry, 'Preserved artifact size differs')
            authenticated[str(artifact)] = actual
        for case in CASES:
            directory = base / 'corpora' / case
            inner, _ = read(directory / (case + '_process.json'))
            job, _ = read(base / 'jobs' / ('corpus_' + case) / 'process.json')
            postflight, _ = read(directory / 'adapter_postflight.json')
            require(inner['state'] == 'completed' and inner['case'] == case and inner['changed_inputs'] == []
                    and job['status'] == 'FINISHED' and job['returncode'] == 0 and job['child_terminated'] is True
                    and postflight['status'] == 'VERIFIED', 'Corpus case is incomplete')
            artifact = directory / (case + '.json')
            entry = authenticated[str(artifact)]
            require(inner['result_sha256'] == entry['sha256'], 'Completed result digest differs')
            result_files[artifact.relative_to(root).as_posix()] = entry
        require(authenticated[str(base / 'source_freeze_v1.json')]['sha256'] == source_sha
                and authenticated[str(base / 'corpus_freeze_v1.json')]['sha256'] == corpus_sha
                and authenticated[str(base / 'full_suite_source_freeze_v1.json')]['sha256']
                    == manifest['full_suite_source_freeze_sha256'],
                'Preservation inventory binds different freezes')
        phases[phase] = {'working_directory': str(root), 'gate_directory': str(base), 'source_head': head,
                         'source_freeze_sha256': source_sha, 'corpus_freeze_sha256': corpus_sha,
                         'full_suite_source_freeze_sha256': manifest['full_suite_source_freeze_sha256'],
                         'owned_job_names': OWNED_JOBS,
                         'preservation_manifest': {'path': str(path), 'schema': manifest['schema'], **manifest_binding},
                         'result_files': result_files}
        authenticated[str(path)] = manifest_binding
    for path, expected in authenticated.items():
        _, actual = raw(Path(path), expected['sha256'])
        require(actual == expected, 'Preserved input changed during comparison preparation')
    raw(policy_path, policy_binding['sha256'])
    record = {'schema': 'semabi.transport.w2_comparison_inputs.v1',
              'created_utc': datetime.now(timezone.utc).isoformat(), 'policy_sha256': policy_binding['sha256'],
              'predecessor_source_head': W3_HEAD, 'candidate_source_head': source['source_head'],
              'phases': phases, 'authenticated_inputs': authenticated,
              'preparer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'native_executed': False, 'semantic_comparison_executed': False,
              'scope': 'Late binding of complete corpus outputs from preserved six-native-job phases. No W3 acceptance/equality claim, '
                       'new native baseline, projection change, source change or GO is introduced.'}
    with output.open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    _, binding = raw(output)
    print(json.dumps({'output': str(output), **binding, 'phases': list(phases)}, sort_keys=True))


if __name__ == '__main__':
    main()
