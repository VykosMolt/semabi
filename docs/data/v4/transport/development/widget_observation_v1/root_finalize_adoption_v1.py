import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/moloch/semabi')
TESTED = ROOT / 'runs/.w2_scoring_worktree'
DEST = ROOT / 'docs/data/v4/transport/development/widget_observation_v1'
RETAINED = DEST / 'retained_validation_v1'

def git(*args, root=ROOT):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def facts(path):
    return {'bytes': path.stat().st_size, 'sha256': sha(path)}

def write_new(path, data):
    with path.open('x') as handle:
        handle.write(json.dumps(data, indent=2, sort_keys=True) + '\n')

head = git('rev-parse', 'HEAD')
parent = git('rev-parse', 'HEAD^')
assert head == '2887ec8e9a9e6b1304d68588bbc46f1fe3cb76d9'
assert parent == 'fec67da9b7c22f4bc9942d13673a457f482126df'
assert git('rev-parse', 'HEAD', root=TESTED) == 'b15e6b0a4c2736fabfcb48fbab19981d82b575e8'
changed = git('diff-tree', '--no-commit-id', '--name-only', '-r', head).splitlines()
assert changed == ['semabi/compiler/v4/objective.py', 'tests/test_v4_objective.py']
assert not git('diff', '--cached', '--name-only')
assert not git('diff', '--name-only', 'HEAD', '--', 'semabi', 'tests')
source = json.loads((RETAINED / 'source_freeze_v1.json').read_text())
full = json.loads((RETAINED / 'full_suite_source_freeze_v1.json').read_text())
maps = {
    'native': source['source_files'], 'tests': source['test_files'],
    'runtime': source['files'], 'dependencies': full['dependency_files'],
    'suite_inputs': source['suite_retained_run_files'],
    'corpus_inputs': source['corpora']['files'],
}
counts = {}
for label, entries in maps.items():
    for name, expected in entries.items():
        assert sha(ROOT / name) == expected, (label, name, 'main')
        assert sha(TESTED / name) == expected, (label, name, 'tested')
    counts[label] = len(entries)
for prefix, label in [('semabi', 'native'), ('tests', 'tests')]:
    actual = {str(path.relative_to(ROOT)) for path in (ROOT / prefix).rglob('*.py')}
    assert actual == set(maps[label]), (prefix, sorted(actual ^ set(maps[label])))
assert counts == {'native': 156, 'tests': 70, 'runtime': 67, 'dependencies': 6, 'suite_inputs': 18, 'corpus_inputs': 45}
assert sha(RETAINED / 'results_manifest_v1.json') == 'cb8992e869a1c3cf680e864ff65f55cb5e0cb220acef0d695aa965bd0ec8c26d'
assert sha(RETAINED / 'copy_manifest_v1.json') == 'cb928445d48752d0c5b676e2e682541359d7692c8c225c9ac94bd75b14feb64c'
evidence_names = [
    'retained_validation_v1/results_manifest_v1.json',
    'retained_validation_v1/copy_manifest_v1.json',
    'retained_validation_v1/full_suite_summary_v1.json',
    'retained_validation_v1/corpus_comparison_v1.json',
    'retained_validation_v1/root_result_acceptance_v1.json',
    'retained_validation_v1/independent_broad_review_v1.md',
    'independent_final_custody_review_v1.md',
    'root_exact_adoption_check_v1.json', 'root_main_commit_tool_v1.json',
]
receipt = {
    'schema': 'semabi.transport.w2_main_adoption.v1',
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'decision': 'ADOPTED_REVIEWED_W2_SOURCE',
    'main_source_commit': head, 'parent_main_commit': parent,
    'tested_source_commit': source['source_head'],
    'exact_changed_paths': changed, 'checked_counts': counts,
    'source_bytes_equal_after_commit': True,
    'complete_native_test_membership_equal': True,
    'source_adoption_main_index_clean': True,
    'full_suite': {'passed': 697, 'skipped': 3, 'xfail': 1, 'failed': 0, 'errors': 0},
    'corpora': {'cases': 5, 'components_per_case': 6, 'differences': 0, 'known_residuals': 'RETAINED'},
    'evidence': {name: facts(DEST / name) for name in evidence_names},
    'scope': 'Exact two-file source/test adoption, with canonical full suite and dedicated corpus evidence inherited from identical verified bytes. No unchanged passing native jobs rerun, fresh transfer, identity-truth or JOIN claim.',
}
write_new(DEST / 'main_adoption_v1.json', receipt)
print(json.dumps({'decision': receipt['decision'], 'head': head, 'checked_counts': counts, 'artifact': facts(DEST / 'main_adoption_v1.json')}, sort_keys=True))
