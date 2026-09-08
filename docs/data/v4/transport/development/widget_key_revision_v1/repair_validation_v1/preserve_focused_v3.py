"""Seal one finished W3 focused attempt before inspecting test outcomes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve(strict=True)
    manifest = directory / 'artifact_manifest_v3.json'
    completion = directory / 'root_completion_checks_v3.json'
    if manifest.exists() or completion.exists():
        raise ValueError('This attempt already has preservation outputs')
    checks = []

    def check(name, ok):
        checks.append({'name': name, 'pass': bool(ok)})

    def read(name):
        return json.loads((directory / name).read_text())

    freeze = read('source_freeze_v1.json')
    command = read('command_v1.json')
    go = read('root_go_v1.json')
    launch = read('root_launch_tool_v1.json')
    reap = read('root_reap_tool_v1.json')
    host = read('root_host_termination_v1.json')
    process = read('job_v1/process.json')
    execution = read('execution_v1.json')
    root = Path(freeze['working_directory'])
    check('source head', subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root,
          text=True).strip() == freeze['source_head'] == process['source_head'] == execution['source_head'])
    check('tracked differences', sorted(subprocess.check_output(
        ['git', 'diff', '--name-only', 'HEAD', '--'], cwd=root, text=True).splitlines())
        == freeze['expected_tracked_changes'])
    for collection, base in [('files', root), ('external_files', Path('/'))]:
        for name, digest in freeze[collection].items():
            path = base / name
            check(collection + ':' + name, path.is_file() and not path.is_symlink()
                  and path.resolve(strict=True) == path and sha(path) == digest)
    check('native membership', {p.relative_to(root).as_posix() for p in (root / 'semabi').rglob('*.py')}
          == set(freeze['native_files']))
    check('job native hashes', process['source_hashes'] == freeze['native_files'])
    check('freeze binding', sha(directory / 'source_freeze_v1.json')
          == command['source_freeze_sha256'] == go['source_freeze_sha256']
          == execution['source_freeze_sha256'])
    check('command binding', sha(directory / 'command_v1.json') == go['command_sha256'])
    check('launch binding', launch['args'] == go['exec_command_args'])
    check('launched command', all(launch['args'].get(k) == v for k, v in command['exec_command_args'].items()))
    if 'session_id' in launch['result']:
        check('session ownership', launch['result']['session_id'] == reap['args'].get('session_id'))
    else:
        check('actual direct completion', launch == reap and 'exit_code' in launch['result'])
    terminal = json.loads(reap['result']['output'])
    check('exit continuity', reap['result']['exit_code'] == terminal['returncode']
          == process['returncode'] == execution['pytest_returncode'])
    check('process continuity', execution['pid'] == terminal['child_pid'] == process['child_pid']
          == process['owned_process_group'] == host['child_pid'])
    check('termination continuity', terminal['child_terminated'] and process['child_terminated']
          and terminal['end_utc'] == process['end_utc'])
    check('host post-exit sample', host['created_utc'] >= process['end_utc']
          and host['runner_pid'] == process['runner_pid'] and not host['runner_present']
          and not host['child_present'] and host['child_process_group_members'] == [])
    check('log binding', sha(directory / 'job_v1/output.log') == process['log_sha256'])
    check('child command', command['argv'][command['argv'].index('--') + 1:]
          == process['command'] == execution['argv'])
    check('working directory', execution['working_directory'] == process['cwd'] == str(root))
    check('frozen runtime settings', execution['environment'] == freeze['environment']
          and execution['cpu_affinity'] == freeze['cpu_affinity'] and execution['priority'] == 0
          and execution['interpreter_flags'] == {'safe_path': True, 'optimize': 0, 'dont_write_bytecode': True}
          and execution['pytest_args'] == freeze['pytest_args'])
    boundary = {'verified_files': len(freeze['files']), 'verified_external_files': len(freeze['external_files']),
                'ambient_prefix_absent': True}
    check('pre/postflight', execution['postflight_status'] == 'VERIFIED'
          and execution['preflight'] == execution['postflight'] == boundary
          and 'execution_error' not in execution and 'postflight_error' not in execution)
    prefix = Path(freeze['environment']['PYTHONPYCACHEPREFIX'])
    check('ambient prefix remains absent', not prefix.exists() and not prefix.is_symlink())
    check('two origin boundaries', len(execution['snapshots']) == 2)
    for index, snapshot in enumerate(execution['snapshots']):
        check('recorded origin violations ' + str(index), snapshot['violations'] == [])
        for name, row in snapshot['modules'].items():
            path = Path(row['file'])
            relative = path.relative_to(root).as_posix()
            paths = [str(path.parent)] if path.name == '__init__.py' else []
            check('origin ' + str(index) + ':' + name,
                  path.resolve(strict=True) == path and relative in freeze['native_files']
                  and sha(path) == freeze['native_files'][relative] and row['spec_origin'] == str(path)
                  and row['package_paths'] == row['spec_package_paths'] == paths)
    record = {'schema': 'semabi.widget_key_revision.focused_preservation.v3',
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'preserver_path': str(Path(__file__).resolve()), 'preserver_sha256': sha(Path(__file__)),
              'scope': 'Custody checks only. Exit continuity does not require test success. Host evidence is post-exit. '
                       'All regular attempt files and the targets of pytest scratch symlinks are recorded; no native execution.',
              'checks': checks, 'findings': [c['name'] for c in checks if not c['pass']]}
    with completion.open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    files = {}
    symlinks = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            path.resolve(strict=True).relative_to(directory / 'pytest_tmp_v1')
            symlinks[path.relative_to(directory).as_posix()] = str(path.readlink())
            continue
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = {'sha256': sha(path), 'bytes': path.stat().st_size}
    seal = {'schema': 'semabi.widget_key_revision.focused_artifacts.v3',
            'created_utc': datetime.now(timezone.utc).isoformat(), 'condition': freeze['condition'],
            'files': files, 'scratch_symlinks': symlinks, 'custody_findings': record['findings'],
            'scope': 'Sealed before semantic inspection of JUnit/log. Native assertions may fail. '
                     'Malformed required metadata can abort preservation before this seal; this is not a universal recovery tool.'}
    with manifest.open('x') as stream:
        json.dump(seal, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'manifest': str(manifest), 'sha256': sha(manifest), 'files': len(files),
                      'checks': len(checks), 'scratch_symlinks': len(symlinks), 'custody_findings': record['findings']}, sort_keys=True))


if __name__ == '__main__':
    main()
