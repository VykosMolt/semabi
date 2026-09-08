"""Add comparison custody to the immutable W3 raw seal without interpreting results."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import types

SELF = Path(__file__).absolute()
ROOT, HERE = SELF.parents[8], SELF.parents[1]
RAW_SHA = 'b59eb2b89f45889242484ba342aa44b1f1dedfec4e52ef43e85ec4ef5304f8db'
HELPER_SHA = '5ac0b3e71d917510f26ed2332dcfa3dcd72af5b6e9c3914551b5c68aa2d56150'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def authenticated(path, expected):
    require(path.resolve(strict=True) == path and path.is_file(), 'Noncanonical artifact: ' + str(path))
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, 'Authenticated bytes changed: ' + str(path))
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--raw-manifest-sha256', required=True)
    parser.add_argument('--self-sha256', required=True)
    args = parser.parse_args()
    require(Path.cwd() == ROOT and sys.flags.safe_path and sys.dont_write_bytecode
            and sys.flags.optimize == 0, 'Require canonical W3 worktree and safe startup')
    authenticated(SELF, args.self_sha256)
    raw_path = HERE / 'native_artifact_manifest_v1.json'
    require(args.raw_manifest_sha256 == RAW_SHA, 'Wrong raw seal identity')
    raw = json.loads(authenticated(raw_path, RAW_SHA))
    require(raw['schema'] == 'semabi.transport.w3_native_artifacts.v1' and raw['status'] == 'PRESERVED'
            and raw['all_owned_jobs_terminated'] is True and raw['working_directory'] == str(ROOT), 'Invalid raw seal')
    helper_path = HERE / 'preservation_v1/preserve_native_v2.py'
    helper_bytes = authenticated(helper_path, HELPER_SHA)
    require(raw['files'][helper_path.relative_to(ROOT).as_posix()]
            == {'bytes': len(helper_bytes), 'sha256': HELPER_SHA}, 'Raw seal binds another helper')
    h = types.ModuleType('w3_retained_raw_preserver')
    h.__file__ = str(helper_path)
    exec(compile(helper_bytes, str(helper_path), 'exec'), h.__dict__)
    proposal, output = HERE / 'artifact_manifest_proposal_v1.json', HERE / 'results_manifest_v1.json'
    require(all(not p.exists() and not p.is_symlink() for p in (proposal, output)), 'Final outputs are exclusive')
    original = h.inventory()
    require(all(original.get(name) == entry for name, entry in raw['files'].items()), 'Original raw file changed or disappeared')
    require(original[raw_path.relative_to(ROOT).as_posix()]['sha256'] == RAW_SHA
            and original[SELF.relative_to(ROOT).as_posix()]['sha256'] == args.self_sha256, 'Raw manifest or preserver changed')
    commands, source = [h.metadata(HERE / name) for name in ('commands_v2.json', 'source_freeze_v1.json')]
    require(all(h.fingerprint(HERE / name)['sha256'] == digest for name, digest in raw['bindings'].items()), 'Raw binding changed')
    host = h.metadata(HERE / 'root_host_before_v1.json')
    require(os.readlink('/proc/self/ns/pid') == host.get('sampler_pid_namespace')
            and os.geteuid() == host.get('effective_uid'), 'Require the recorded host PID namespace and UID')
    name = 'corpus_comparison_v1'
    command = commands['jobs'][name]
    contract = h.metadata(HERE / 'result_contract_v1.json')['jobs'][name]
    process = h.metadata(ROOT / contract['process'])
    launch = h.metadata(HERE / 'root_comparison_launch_tool_v1.json')
    terminal = h.metadata(ROOT / contract['terminal_receipt'])
    job = {'process': contract['process'], 'terminal_receipt': contract['terminal_receipt'],
           'group': process.get('owned_process_group'), 'outer_returncode': process.get('returncode'),
           'pid_argv': [(process.get('runner_pid'), command['outer_argv'][command['outer_argv'].index(sys.executable):]),
                        (process.get('child_pid'), command['inner_argv'])], 'terminated': False}

    def continuity():
        lp, tp = launch['result'], terminal['result']
        session = lp.get('session_id')
        session_ok = (type(session) is int and terminal['args'].get('session_id') == session) if session is not None else terminal == launch
        actual = json.loads(tp['output'])
        launch_ok = h.check('comparison actual launch', shlex.split(launch['args']['cmd']) == command['outer_argv']
                           and launch['args']['workdir'] == str(ROOT) and launch['args']['sandbox_permissions'] == 'require_escalated')
        terminal_ok = h.check('comparison actual terminal continuity', session_ok and type(tp.get('exit_code')) is int
            and 'session_id' not in tp and all(process.get(k) == actual.get(k) for k in
                ('status', 'returncode', 'child_pid', 'child_terminated', 'end_utc'))
            and process.get('status') in ('FINISHED', 'FAILED', 'INTERRUPTED') and process.get('child_terminated') is True
            and type(process.get('returncode')) is int and isinstance(process.get('end_utc'), str) and bool(process['end_utc']))
        pid_ok = h.check('comparison runner/child/group', all(type(pid) is int and pid > 0 for pid, _ in job['pid_argv'])
                         and process['runner_pid'] != process['child_pid'] == job['group'])
        provenance_ok = h.check('comparison source/command/cwd/log', process.get('source_head') == source['source_head'] == raw['source_head']
            and process.get('source_hashes') == source['source_files'] and process.get('command') == command['inner_argv']
            and process.get('cwd') == command['cwd'] == str(ROOT) and process.get('log_sha256') == h.fingerprint(ROOT / contract['log'])['sha256']
            and process.get('instrument_hashes') == {p: {**source['files'], **source['verification_files']}[p] for p in
                ('scripts/transport_collect.py', 'scripts/transport_score.py', 'docs/data/v4/transport/run_job.py')})
        exit_ok = h.check('comparison wrapper exit continuity', type(process.get('returncode')) is int and
            (tp.get('exit_code') != 0 if process.get('status') == 'INTERRUPTED' else tp.get('exit_code') == process['returncode'] % 256))
        job.update(terminated=launch_ok and terminal_ok and pid_ok and provenance_ok and exit_ok,
                   tool_returncode=tp.get('exit_code'), tool_session_id=session)

    h.attempt('comparison continuity metadata', continuity)
    h.check('comparison outer outcome is zero', type(job['outer_returncode']) is int and job['outer_returncode'] == 0, job['outer_returncode'])
    for path in contract['outputs']:
        h.check('comparison declared output present:' + path, (ROOT / path).is_file())
    host_after = h.sample_host({name: job})
    terminated = job['terminated'] and not host_after['unknown'] and not host_after['present']
    common = {'created_utc': datetime.now(timezone.utc).isoformat(), 'source_head': raw['source_head'],
        'working_directory': str(ROOT), 'raw_manifest': {'path': str(raw_path), **h.fingerprint(raw_path)},
        'source_freeze_sha256': raw['source_freeze_sha256'], 'corpus_freeze_sha256': raw['corpus_freeze_sha256'],
        'full_suite_source_freeze_sha256': raw['full_suite_source_freeze_sha256'],
        'preserver': {'path': str(SELF), **h.fingerprint(SELF)}, 'retained_helper_sha256': HELPER_SHA,
        'owned_job_names': sorted([*raw['owned_job_names'], name]), 'comparison_job': job,
        'checks': h.CHECKS, 'custody_findings': h.FINDINGS, 'host_after': host_after,
        'all_owned_jobs_terminated': raw['all_owned_jobs_terminated'] and terminated,
        'termination_scope': h.TERMINATION_SCOPE, 'native_termination_basis': 'Authenticated raw seal; this final host sample covers the comparator only.',
        'excluded_runtime_scratch': raw['excluded_runtime_scratch'], 'semantic_acceptance': 'NOT_ASSESSED',
        'scope': 'Additive artifact custody only. Original raw bytes are unchanged; comparison payload and semantic acceptance are not interpreted.'}
    require(h.inventory() == original, 'Gate inventory changed during final preservation')
    h.write(proposal, {'schema': 'semabi.transport.w3_validation_artifact_proposal.v1', **common, 'files': original})
    original[proposal.relative_to(ROOT).as_posix()] = h.fingerprint(proposal)
    require(h.inventory() == original, 'Gate inventory changed after exclusive proposal')
    h.write(output, {'schema': 'semabi.transport.w3_validation_results.v1', **common, 'files': original,
                    'status': 'PRESERVED_WITH_FINDINGS' if h.FINDINGS else 'PRESERVED', 'proposal_sha256': h.fingerprint(proposal)['sha256']})
    print(json.dumps({'path': str(output), **h.fingerprint(output), 'findings': len(h.FINDINGS)}))


if __name__ == '__main__':
    main()
