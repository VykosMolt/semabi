"""Seal W3 raw artifacts after root reaping; never interpret scored payloads."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

SELF = Path(__file__).absolute()
ROOT, HERE = SELF.parents[8], SELF.parents[1]
BINDINGS = {
    'commands_v2.json': '13053e60aa5105e9780d4a7459ff7589f2ca561d067b08ef3593a5bf61cf16eb',
    'source_freeze_v1.json': '49d0888546223dc90aef70212a80018dabbc68e92bf16dcf394b17ef698c8eac',
    'corpus_freeze_v1.json': 'e28cdcb3483ae6edce0cd931bcf70c0913dde554eeffcdd0a5685cd20a9b73ae',
    'full_suite_source_freeze_v1.json': 'e34af04a2fe44fdef0d1e541c3f4592b994b534efd9aa1710be0314cf838671b',
}
CHECKS, FINDINGS = [], []


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(name, condition, detail=None):
    CHECKS.append({'name': name, 'pass': bool(condition), 'detail': detail})
    if not condition:
        FINDINGS.append({'name': name, 'detail': detail})
    return bool(condition)


def attempt(name, action, default=None):
    try:
        return action()
    except Exception as error:
        check(name, False, f'{type(error).__name__}: {error}')
        return default


def fingerprint(path):
    require(path.resolve(strict=True) == path and path.is_file(), 'Noncanonical regular file: ' + str(path))
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes': path.stat().st_size, 'sha256': digest}


def metadata(path):
    def parse():
        value = json.loads(path.read_text())
        require(isinstance(value, dict), 'Expected a metadata object')
        return value
    return attempt('metadata:' + str(path), parse, {})


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def inventory():
    scratch, files = HERE / 'full_pytest_tmp_v1', {}
    require(not scratch.is_symlink() and (not scratch.exists() or
            (scratch.is_dir() and scratch.resolve(strict=True) == scratch)), 'Invalid scratch root')
    for directory, dirs, names in os.walk(HERE, followlinks=False):
        for name in [*dirs, *names]:
            path = Path(directory) / name
            if path == scratch:
                dirs.remove(name)
                continue
            require(not path.is_symlink(), 'Symlink in raw inventory: ' + str(path))
            if not path.is_dir():
                files[path.relative_to(ROOT).as_posix()] = fingerprint(path)
    return files


def sample_host(jobs):
    targets = {pid: argv for row in jobs.values() for pid, argv in row['pid_argv'] if type(pid) is int and pid > 0}
    groups = {row['group'] for row in jobs.values() if type(row['group']) is int and row['group'] > 0}
    sample = {'pid_namespace': os.readlink('/proc/self/ns/pid'), 'pid': os.getpid(),
              'effective_uid': os.geteuid(), 'source': str(SELF), 'source_sha256': fingerprint(SELF)['sha256'],
              'recorded_pids': sorted(targets), 'recorded_groups': sorted(groups), 'present': [], 'unknown': []}
    live = []
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            pid, group, state = int(path.name), int(fields[2]), fields[0]
            if pid not in targets and group not in groups:
                continue
            raw = (path / 'cmdline').read_bytes()
            argv = [part.decode(errors='surrogateescape') for part in (raw[:-1] if raw.endswith(b'\0') else raw).split(b'\0')] if raw else []
            row = {'pid': pid, 'group': group, 'state': state, 'argv': argv, 'start_ticks': fields[19]}
            sample['present'].append(row)
            if state != 'Z' and pid in targets and argv != targets[pid]:
                sample['unknown'].append(row)
            elif state != 'Z' and (argv == targets.get(pid) or group in groups):
                live.append(row)
        except FileNotFoundError:
            continue
        except Exception as error:
            sample['unknown'].append({'pid': int(path.name), 'error': f'{type(error).__name__}: {error}'})
    sample['live_owned'] = live
    check('host scan complete without unknown entries', not sample['unknown'], sample['unknown'])
    require(not live, 'Live recorded process or owned group blocks sealing: ' + json.dumps(live))
    return sample


def inspect_job(name, command, contract, launches, source):
    process = metadata(ROOT / contract['process'])
    launch, terminal = launches.get(name, {}), metadata(ROOT / contract['terminal_receipt'])
    result = {'process': contract['process'], 'terminal_receipt': contract['terminal_receipt'],
              'outer_returncode': process.get('returncode'), 'group': process.get('owned_process_group'),
              'pid_argv': [(process.get('runner_pid'), command['outer_argv'][command['outer_argv'].index(sys.executable):]),
                           (process.get('child_pid'), command['inner_argv'])], 'terminated': False}
    def continuity():
        lp, tp = launch['result'], terminal['result']
        session = lp.get('session_id')
        session_ok = (type(session) is int and terminal['args'].get('session_id') == session) if session is not None else terminal == launch
        actual = json.loads(tp['output'])
        launch_ok = check(name + ': actual launch', shlex.split(launch['args']['cmd']) == command['outer_argv']
                          and launch['args']['workdir'] == str(ROOT) and launch['args']['sandbox_permissions'] == 'require_escalated')
        terminal_ok = check(name + ': actual terminal continuity', session_ok and type(tp.get('exit_code')) is int
            and 'session_id' not in tp and all(process.get(k) == actual.get(k) for k in
            ('status', 'returncode', 'child_pid', 'child_terminated', 'end_utc'))
            and process.get('status') in ('FINISHED', 'FAILED', 'INTERRUPTED') and process.get('child_terminated') is True
            and type(process.get('returncode')) is int and isinstance(process.get('end_utc'), str) and bool(process['end_utc']))
        pid_ok = check(name + ': runner/child/group', all(type(pid) is int and pid > 0 for pid, _ in result['pid_argv'])
                       and process['runner_pid'] != process['child_pid'] == result['group'])
        provenance_ok = check(name + ': source/command/cwd/log', process.get('source_head') == source['source_head']
              and process.get('source_hashes') == source['source_files'] and process.get('command') == command['inner_argv']
              and process.get('cwd') == str(ROOT) and process.get('log_sha256') == fingerprint(ROOT / contract['log'])['sha256']
              and process.get('instrument_hashes') == {p: {**source['files'], **source['verification_files']}[p] for p in
                  ('scripts/transport_collect.py', 'scripts/transport_score.py', 'docs/data/v4/transport/run_job.py')})
        exit_ok = check(name + ': wrapper exit continuity', type(process.get('returncode')) is int and
            (tp.get('exit_code') != 0 if process.get('status') == 'INTERRUPTED' else tp.get('exit_code') == process['returncode'] % 256))
        result.update(terminated=launch_ok and terminal_ok and pid_ok and provenance_ok and exit_ok,
                      tool_returncode=tp.get('exit_code'), tool_session_id=session)
    attempt(name + ': continuity metadata', continuity)
    check(name + ': outer outcome is zero', result['outer_returncode'] == 0, result['outer_returncode'])
    for path in contract['outputs']:
        check(name + ': declared output present:' + path, (ROOT / path).is_file())
    audit_path = HERE / ('full_suite_v1/import_origins_v1.json' if name == 'full_pytest_v1' else
                         'corpora/' + name.removeprefix('corpus_') + '/import_origins_v1.json')
    audit = metadata(audit_path)
    expected_freeze = BINDINGS['full_suite_source_freeze_v1.json' if name == 'full_pytest_v1' else 'source_freeze_v1.json']
    check(name + ': inner source/process association', audit.get('source_head') == source['source_head']
          and audit.get('source_freeze_sha256') == expected_freeze and audit.get('pid') == process.get('child_pid')
          and audit.get('working_directory', audit.get('cwd')) == str(ROOT)
          and audit.get('actual_command') == [command['inner_argv'][0], *command['inner_argv'][3:]])
    check(name + ': inner postflight', audit.get('postflight_status') == 'VERIFIED'
          and not audit.get('execution_error') and not audit.get('postflight_error'), {k: audit.get(k) for k in ('postflight_status', 'execution_error', 'postflight_error')})
    if name == 'full_pytest_v1':
        result['pytest_returncode'] = audit.get('pytest_returncode')
        check(name + ': inner pytest outcome', type(result['pytest_returncode']) is int and result['pytest_returncode'] == 0, result['pytest_returncode'])
        if audit.get('postflight_status') == 'VERIFIED' and not audit.get('execution_error'):
            check(name + ': pytest/wrapper exit continuity', result['pytest_returncode'] == result['outer_returncode'])
    else:
        check(name + ': measurement returned', audit.get('measurement_returned') is True
              and audit.get('corpus_freeze_sha256') == BINDINGS['corpus_freeze_v1.json'])
        case = name.removeprefix('corpus_')
        inner = metadata(audit_path.parent / (case + '_process.json'))
        result['measurement_state'] = inner.get('state')
        check(name + ': inner process completion', inner.get('state') == 'completed' and inner.get('case') == case
              and inner.get('pid') == process.get('child_pid') and inner.get('changed_inputs') == []
              and inner.get('source_snapshot_sha256') == BINDINGS['corpus_freeze_v1.json'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for option in ('commands', 'source-freeze', 'corpus-freeze', 'full-suite-freeze', 'self'):
        parser.add_argument('--' + option + '-sha256', required=True)
    args = parser.parse_args()
    require(Path.cwd() == ROOT and SELF.resolve(strict=True) == SELF, 'Use the canonical W3 worktree')
    require(sys.flags.safe_path and sys.dont_write_bytecode and sys.flags.optimize == 0, 'Require safe startup, no bytecode, optimization zero')
    require(fingerprint(SELF)['sha256'] == args.self_sha256, 'Preserver source digest differs')
    supplied = (args.commands_sha256, args.source_freeze_sha256, args.corpus_freeze_sha256, args.full_suite_freeze_sha256)
    for (name, expected), actual in zip(BINDINGS.items(), supplied, strict=True):
        require(actual == expected == fingerprint(HERE / name)['sha256'], 'Frozen binding differs: ' + name)
    output, proposal, checks_path = [HERE / name for name in ('native_artifact_manifest_v1.json',
        'native_artifact_manifest_proposal_v1.json', 'root_completion_checks_v1.json')]
    require(all(not p.exists() and not p.is_symlink() for p in (output, proposal, checks_path)), 'Output identities are exclusive')
    original = inventory()
    commands, source, corpus, full = [metadata(HERE / name) for name in BINDINGS]
    host = metadata(HERE / 'root_host_before_v1.json')
    require(os.readlink('/proc/self/ns/pid') == host.get('sampler_pid_namespace') and os.geteuid() == host.get('effective_uid'), 'Require the recorded host PID namespace and UID')
    check('freeze links', all(f['working_directory'] == str(ROOT) and f['source_head'] == source['source_head'] for f in (corpus, full))
          and corpus['source_freeze'] == {'path': (HERE / 'source_freeze_v1.json').relative_to(ROOT).as_posix(), 'sha256': supplied[1]}
          and full['source_corpus_freezes'] == {'source': supplied[1], 'corpus': supplied[2]} and corpus['corpora'] == source['corpora']
          and corpus['files'] == source['files'] and full['native_files'] == source['source_files'] and full['test_files'] == source['test_files']
          and corpus['verification_files'] == {**source['verification_files'], (HERE / 'source_freeze_v1.json').relative_to(ROOT).as_posix(): supplied[1]}
          and full['verification_files'] == {**corpus['verification_files'], (HERE / 'corpus_freeze_v1.json').relative_to(ROOT).as_posix(): supplied[2]})
    check('complete frozen coverage', len(full['files']) == 2949 and len(full['retained_external_files']) == 175
          and all(full['files'].get(p) == h for mapping in (source['tracked_files'], source['source_files'], source['test_files'],
              source['files'], source['verification_files'], source['suite_retained_run_files'], source['corpora']['files']) for p, h in mapping.items()))
    for label, base, files in (('full frozen files', ROOT, full['files']), ('retained external files', Path('/'), full['retained_external_files'])):
        bad = [name for name, expected in files.items() if attempt(label + ':' + name, lambda n=name: fingerprint(base / n), {}).get('sha256') != expected]
        check(label, not bad, {'count': len(files), 'mismatches': bad})
    git = lambda *argv: subprocess.check_output(['git', *argv], cwd=ROOT, text=True)
    check('clean frozen HEAD', git('rev-parse', 'HEAD').strip() == source['source_head'] and not git('diff', '--name-only', 'HEAD', '--').strip())
    check('tracked membership', set(git('ls-files', '-z').split('\0')) - {''} == set(full['tracked_files']))
    for directory, expected, pattern in [('semabi', full['native_files'], '*.py'), ('tests', full['test_files'], '*.py'),
            (source['corpora']['root'], source['corpora']['files'], '*')]:
        actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob(pattern) if p.is_file()}
        check('membership:' + directory, actual == set(expected))
    actual = {p.relative_to(ROOT).as_posix() for name in ('harbour_transfer', 'blend_book_transfer', 'harbour_dev') for p in (ROOT / 'runs/v4' / name).rglob('*') if p.is_file()}
    check('retained suite input membership', actual == set(full['suite_retained_run_files']))
    contract, launches = metadata(HERE / 'result_contract_v1.json'), metadata(HERE / 'root_launch_receipts_v1.json')
    jobs = {name: inspect_job(name, row, contract['jobs'][name], launches, source) for name, row in commands['jobs'].items() if name != 'corpus_comparison_v1'}
    check('six native launch receipts', len(jobs) == 6 and set(launches) == set(jobs))
    host_after = sample_host(jobs)
    record = {'schema': 'semabi.transport.w3_raw_completion_checks.v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
              'bindings': BINDINGS, 'preserver': {'path': str(SELF), **fingerprint(SELF)}, 'host_after': host_after,
              'checks': CHECKS, 'findings': FINDINGS, 'jobs': jobs,
              'all_owned_jobs_terminated': all(row['terminated'] for row in jobs.values()) and not host_after['unknown'],
              'scope': 'Raw custody only; no JUnit, fit, partial, scored corpus or comparator payload was parsed.'}
    write(checks_path, record)
    original[checks_path.relative_to(ROOT).as_posix()] = fingerprint(checks_path)
    require(inventory() == original, 'Raw inventory changed during preservation')
    common = {'source_head': source['source_head'], 'working_directory': str(ROOT), 'bindings': BINDINGS,
              'source_freeze_sha256': supplied[1], 'corpus_freeze_sha256': supplied[2],
              'full_suite_source_freeze_sha256': supplied[3], 'owned_job_names': sorted(jobs),
              'excluded_runtime_scratch': str(HERE / 'full_pytest_tmp_v1'), 'semantic_acceptance': 'NOT_ASSESSED',
              'all_owned_jobs_terminated': record['all_owned_jobs_terminated'], 'custody_findings': FINDINGS}
    write(proposal, {'schema': 'semabi.transport.w3_native_artifact_proposal.v1', **common, 'files': original})
    original[proposal.relative_to(ROOT).as_posix()] = fingerprint(proposal)
    require(inventory() == original, 'Raw inventory changed after exclusive proposal')
    write(output, {'schema': 'semabi.transport.w3_native_artifacts.v1', **common, 'files': original,
                   'status': 'PRESERVED_WITH_FINDINGS' if FINDINGS else 'PRESERVED', 'proposal_sha256': fingerprint(proposal)['sha256']})
    print(json.dumps({'path': str(output), **fingerprint(output), 'findings': len(FINDINGS)}))


if __name__ == '__main__':
    main()
