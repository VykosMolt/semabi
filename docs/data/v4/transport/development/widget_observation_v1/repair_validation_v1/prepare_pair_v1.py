"""Freeze one matched W2 scoring pair without importing native code or tests."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

MAIN = Path('/home/moloch/semabi')
HERE = Path(__file__).resolve().parent
HEAD = 'e8f33c9056cc51135b7f9553fad3a7ad829def04'
TEST = 'tests/test_v4_objective.py'
OBJECTIVE = 'semabi/compiler/v4/objective.py'
CANDIDATE_SHA = 'c63ff4e6408c08d976fdfb4a9153d67e6cb1935ca231ee51b32a861648d78fca'
BASELINE_SHA = 'a62d6907b0aa1f643a2e2cb96038cbedab8ac40b55c0e95e67d5f2452f1bdfef'
RUNNER_SHA = '8c789085eff8a235555d37b6013fdd142285a16a6568e19e768722b205e95015'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--test-sha256', required=True)
    parser.add_argument('--test-manifest', required=True, type=Path)
    parser.add_argument('--test-manifest-sha256', required=True)
    args = parser.parse_args()
    candidate = MAIN / 'runs/.w2_scoring_worktree'
    baseline = MAIN / 'runs/.w2_scoring_baseline_worktree'
    proposal = candidate / 'docs/data/v4/transport/development/widget_observation_repair_v1'
    manifest = args.test_manifest
    require(manifest.resolve(strict=True) == manifest and sha(manifest) == args.test_manifest_sha256,
            'The reviewed test manifest changed')
    require(sha(candidate / TEST) == args.test_sha256, 'The reviewed test source changed')
    require(sha(candidate / OBJECTIVE) == CANDIDATE_SHA and sha(baseline / OBJECTIVE) == BASELINE_SHA,
            'Candidate or baseline objective changed')
    require(sys.executable == str(MAIN / '.venv/bin/python') and sys.flags.safe_path
            and sys.dont_write_bytecode and sys.flags.optimize == 0, 'Preparation runtime changed')
    for root in (baseline, candidate):
        require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip() == HEAD,
                'W2 arms must use the exact same integrated W3 HEAD')
    require(not subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--'], cwd=baseline, text=True).strip(),
            'Baseline source is already dirty')
    require(sorted(subprocess.check_output(['git', 'diff', '--name-only', 'HEAD', '--'], cwd=candidate,
                                          text=True).splitlines()) == sorted([TEST, OBJECTIVE]),
            'Unexpected candidate changes')
    native = {p.relative_to(candidate).as_posix(): sha(p) for p in (candidate / 'semabi').rglob('*.py')}
    base_native = {p.relative_to(baseline).as_posix(): sha(p) for p in (baseline / 'semabi').rglob('*.py')}
    require(set(native) == set(base_native) and len(native) == 156
            and {name for name in native if native[name] != base_native[name]} == {OBJECTIVE},
            'The native comparison must isolate objective.py')
    runner = HERE / 'run_focused_v1.py'
    require(sha(runner) == RUNNER_SHA, 'Focused runner changed')
    external_paths = [runner, Path(sys.executable).resolve(strict=True), manifest,
                      proposal / 'candidate_source_v3/objective.py', proposal / 'w3_integration_v1.json',
                      proposal / 'independent_source_review_v1.md', Path(__file__).resolve()]
    external = {str(p): sha(p) for p in external_paths}
    require(all(p.resolve(strict=True) == p and p.is_file() for p in external_paths),
            'External dependency path is not canonical')
    environments = {}
    destinations = {}
    for condition, root in [('BASELINE', baseline), ('CANDIDATE', candidate)]:
        prefix = Path('/tmp/semabi_w2_scoring_' + condition.lower() + '_v1_no_pyc')
        require(not prefix.exists() and not prefix.is_symlink(), 'Bytecode identity already exists')
        directory = root / 'docs/data/v4/transport/development/widget_observation_repair_v1/root_focused_v1'
        require(not directory.exists() and not directory.is_symlink(), 'Attempt identity already exists')
        destinations[condition] = directory
        env = {name: '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                                      'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'BLIS_NUM_THREADS')}
        env.update(PYTHONHASHSEED='0', PYTHONDONTWRITEBYTECODE='1', PYTHONOPTIMIZE='0',
                   PYTHONPATH='', PYTHONPYCACHEPREFIX=str(prefix))
        for name in ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD'):
            require(os.environ.get(name) is None, 'Unexpected pytest environment: ' + name)
            env[name] = None
        environments[condition] = env
    # The baseline receives precisely the reviewed test bytes, after both output
    # identities and the original baseline source have been authenticated.
    (baseline / TEST).write_bytes((candidate / TEST).read_bytes())
    results, maps = {}, {}
    for condition, root in [('BASELINE', baseline), ('CANDIDATE', candidate)]:
        directory = destinations[condition]
        directory.mkdir(parents=True, exist_ok=False)
        members = [*sorted((root / 'semabi').rglob('*.py')), *sorted((root / 'tests').rglob('*.py')),
                   root / 'pytest.ini', root / 'pyproject.toml', root / 'docs/data/v4/transport/run_job.py']
        require(all(p.resolve(strict=True) == p and p.is_file() for p in members), 'Noncanonical source file')
        files = {p.relative_to(root).as_posix(): sha(p) for p in members}
        require(len(files) == 229 and files[TEST] == args.test_sha256, 'Source/test membership changed')
        maps[condition] = files
        pytest_args = ['-q', '-c', 'pytest.ini', '--noconftest', TEST,
                       '--junitxml=' + str(directory / 'pytest_v1.xml'),
                       '--basetemp=' + str(directory / 'pytest_tmp_v1')]
        freeze = {'schema': 'semabi.widget_observation.focused_freeze.v1',
                  'created_utc': datetime.now(timezone.utc).isoformat(), 'condition': condition,
                  'source_head': HEAD, 'working_directory': str(root), 'files': files,
                  'native_files': {n: h for n, h in files.items() if n.startswith('semabi/')},
                  'external_files': external, 'expected_tracked_changes': sorted([TEST] + ([OBJECTIVE] if condition == 'CANDIDATE' else [])),
                  'python_executable': sys.executable, 'python_realpath': str(Path(sys.executable).resolve()),
                  'python_version': sys.version, 'pytest_version': importlib.metadata.version('pytest'),
                  'pytest_entry_points': sorted((e.name, e.value) for e in importlib.metadata.entry_points(group='pytest11')),
                  'cpu_affinity': [9], 'environment': environments[condition], 'pytest_args': pytest_args,
                  'result': str(directory / 'execution_v1.json'), 'junit': str(directory / 'pytest_v1.xml'),
                  'basetemp': str(directory / 'pytest_tmp_v1'),
                  'scope': 'Disclosed W2 version-2 development tests; same accepted W3 source in both arms, only objective.py differs. '
                           'Explicit focused config and no conftest; normal plugins. Root .pytest_cache and named basetemp are runtime scratch. '
                           'Primary-interpreter source/path snapshots, not executed-code-object or child coverage.'}
        path = directory / 'source_freeze_v1.json'
        write(path, freeze)
        env = environments[condition]
        argv = ['taskset', '-c', '9', 'env', *[n + '=' + v for n, v in sorted(env.items()) if v is not None],
                sys.executable, '-P', '-B', 'docs/data/v4/transport/run_job.py',
                (directory / 'job_v1').relative_to(root).as_posix(), '--', sys.executable, '-P', '-B',
                str(runner), '--freeze', str(path), '--sha256', sha(path)]
        command = {'schema': 'semabi.widget_observation.focused_command.v1', 'condition': condition,
                   'source_freeze_sha256': sha(path), 'argv': argv, 'status': 'PREPARED_PENDING_ROOT_GO',
                   'exec_command_args': {'cmd': shlex.join(argv), 'workdir': str(root),
                                         'yield_time_ms': 1000, 'max_output_tokens': 4500}}
        write(directory / 'command_v1.json', command)
        results[condition] = {'directory': str(directory), 'source_freeze_sha256': sha(path),
                              'command_sha256': sha(directory / 'command_v1.json')}
    require(maps['BASELINE'].keys() == maps['CANDIDATE'].keys()
            and {n for n in maps['BASELINE'] if maps['BASELINE'][n] != maps['CANDIDATE'][n]} == {OBJECTIVE},
            'Prepared arms differ outside objective.py')
    print(json.dumps({'schema': 'semabi.widget_observation.paired_preparation.v1', 'conditions': results,
                      'files_per_arm': 229, 'external_files_per_arm': len(external),
                      'only_different_file': OBJECTIVE, 'native_executed': False}, sort_keys=True))


if __name__ == '__main__':
    main()
