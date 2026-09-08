"""Independently authenticate and seal the completed offline controls."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/home/moloch/semabi')
HERE = Path(__file__).resolve().parent
J1 = HERE.parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def main():
    manifest_path = HERE / 'source_manifest_v1.json'
    assert sha(manifest_path) == '4167af43a763f6d3ee38bded0ae78a02e10fb497c57fc285a94cf304518ed920'
    source = read(manifest_path)
    bindings = dict(source['files'])
    inputs = source['inputs']
    for reference in inputs.values():
        bindings[reference['path']] = reference['sha256']
    parents = {
        str(manifest_path.relative_to(ROOT)): sha(manifest_path),
        str((HERE / 'artifact_manifest_v1.json').relative_to(ROOT)): '607f28e74c94fabfd04b5d0ecb97f894dc080801226eff84cf642dc2c514a5ff',
        str((HERE / 'independent_review/artifact_manifest_v1.json').relative_to(ROOT)): '3555d4590444ffc76a888b81b9e52c663aadf3ad315a1ec936592f07f8d66fe3',
    }
    bindings.update(parents)
    for name in parents:
        assert sha(ROOT / name) == parents[name]
        if name != str(manifest_path.relative_to(ROOT)):
            bindings.update(read(ROOT / name)['files'])
    values = {label: read(ROOT / reference['path']) for label, reference in inputs.items()}
    for label in ('preservation', 'sidecar_preparation', 'sidecar_review', 'corrected_score', 'controls_source', 'sidecar_source'):
        bindings.update(values[label]['files'])
    bindings.update(values['controls_source']['dependency_files'])
    for name, value in values['controls_preparation']['files'].items():
        p = HERE.parent / 'post_controls_v1' / name
        bindings[str(p.relative_to(ROOT))] = value['sha256']
        assert p.stat().st_size == value['bytes']
    for label, reference in values['sidecar_source']['inputs'].items():
        bindings[reference['path']] = reference['sha256']
        if label == 'failed_score_seal':
            bindings.update(read(ROOT / reference['path'])['files'])
    for name, digest in bindings.items():
        p = ROOT / name
        assert not Path(name).is_absolute() and p.resolve(strict=True) == p
        assert p.is_file() and not p.is_symlink() and sha(p) == digest, name
    frozen, preserved = values['freeze'], values['preservation']
    assert len(preserved['files']) == 705 and preserved['status'] == 'PRESERVED'
    assert preserved['freeze_sha256'] == inputs['freeze']['sha256']
    for name, digest in {**frozen['source_files'], **frozen['fixed_inputs']}.items():
        assert preserved['files'][name] == digest
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == frozen['source_head'] == '6aea64baac1678cbce8ba4b1a41ab04756225c7d'
    native = {str(p.relative_to(ROOT)) for p in (ROOT / 'semabi').rglob('*.py')}
    assert native == {n for n in frozen['source_files'] if n.startswith('semabi/')}
    job = read(HERE / 'jobs/controls_v1/process.json')
    assert job['runner_pid'] == 1208901 and job['child_pid'] == job['owned_process_group'] == 1208903
    assert job['status'] == 'FINISHED' and job['returncode'] == 0 and job['child_terminated'] is True
    assert job['cwd'] == str(ROOT) and job['source_head'] == head and job['owner'] == '/root'
    assert job['command'] == ['.venv/bin/python', '-B', str((HERE / 'run.py').relative_to(ROOT)),
                              '--manifest', str(manifest_path), '--manifest-sha256', sha(manifest_path)]
    assert job['source_hashes'] == {n: frozen['source_files'][n] for n in native}
    assert job['python_hash_seed'] == '0' and set(job['thread_limits'].values()) == {'1'}
    assert job['log_sha256'] == sha(HERE / 'jobs/controls_v1/output.log')
    for name, digest in job['instrument_hashes'].items():
        assert sha(ROOT / name) == digest == preserved['files'][name]
    reap = read(HERE / 'root_reap_tool_v1.json')
    assert reap['args']['session_id'] == 67617 and reap['result']['exit_code'] == 0
    sample = json.loads(read(HERE / 'root_host_sample_v1.json')['result']['output'])
    assert sample['job_status'] == 'RUNNING' and not sample['bytecode_prefix_present']
    for row in sample['processes']:
        assert row['present'] and row['affinity'] == [20] and row['nice'] == 0
        env = row['environment']
        assert all(env[n] == '1' for n in ('BLIS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS',
                                          'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'))
        assert env['PYTHONHASHSEED'] == '0' and env['PYTHONDONTWRITEBYTECODE'] == '1'
        assert env['PYTHONPYCACHEPREFIX'] == '/tmp/semabi_j1_post_controls_v1_no_pyc'
    assert not Path('/tmp/semabi_j1_post_controls_v1_no_pyc').exists()
    assert Path('/proc/1/stat').is_file()
    assert all(not Path('/proc', str(pid)).exists() for pid in (1208901, 1208903))
    for p in Path('/proc').glob('[0-9]*/stat'):
        try:
            pgrp = int(p.read_text().rsplit(') ', 1)[1].split()[2])
        except (FileNotFoundError, ProcessLookupError):
            continue
        assert pgrp not in (1208901, 1208903)
    audit = read(HERE / 'attempt_v1/adapter_audit.json')
    assert audit['status'] == 'CONTROLS_COMPLETE' and audit['original_main_invoked'] is True
    assert audit['original_main_returncode'] == 0 and audit['error'] is None and audit['postflight_error'] is None
    assert audit['loader_restored'] is True and audit['argv_restored'] is True
    assert len(audit['evaluators']) == 2
    assert [len(row['normalization']['reads']) for row in audit['evaluators']] == [4, 0]
    for row in audit['evaluators']:
        assert row['original_preservation_calls'] == 2 and row['reader_restored'] is True
        assert row['preservation_guard_restored'] is True and row['normalization']['reader_restored'] is True
        for record in row['normalization']['reads']:
            assert record['normalized'] is True
            assert record['actor_sha256'] == preserved['files'][record['actor_path']]
            assert record['sidecar_sha256'] == preserved['files'][record['sidecar_path']]
            assert record['original'] == record['sidecar_path']
            assert record['canonical'] == str(ROOT / record['sidecar_path'])
    result_path = ROOT / source['outputs']['result']
    assert audit['result'] == {'path': str(result_path.relative_to(ROOT)), 'sha256': sha(result_path)}
    result = read(result_path)
    assert result['schema'] == 'semabi.j1.post_preservation_diagnostics.v1' and result['status'] == 'DIAGNOSTIC_ONLY'
    assert result['custody_error'] is None and result['first_pass_status'] == 'PRESERVED'
    assert result['freeze_sha256'] == inputs['freeze']['sha256'] and result['first_pass_sha256'] == inputs['preservation']['sha256']
    assert result['control_manifest_sha256'] == inputs['controls_source']['sha256']
    assert result['source_files'] == values['controls_source']['files']
    new_files = [result_path, HERE / 'attempt_v1/adapter_audit.json', HERE / 'jobs/controls_v1/process.json',
                 HERE / 'jobs/controls_v1/output.log', HERE / 'root_acceptance_v1.json', HERE / 'root_launch_tool_v1.json',
                 HERE / 'root_host_sample_v1.json', HERE / 'root_reap_tool_v1.json', Path(__file__).resolve()]
    assert all(str(p.relative_to(ROOT)) not in bindings for p in new_files)
    sealed = {'schema': 'semabi.j1.post_controls_adapter_result_artifacts.v1', 'status': 'OFFLINE_CONTROLS_PRESERVED',
              'verified_utc': datetime.now(timezone.utc).isoformat(), 'source_head': head, 'parents': parents,
              'input_manifests': inputs, 'unique_held_bindings_rehashed': len(bindings),
              'preserved_files_rehashed': 705, 'native_source_files_rehashed': len(native),
              'owned_pids_and_groups_absent': [1208901, 1208903], 'root_session_reaped': 67617,
              'live_cpu_affinity': [20], 'live_nice': 0, 'normalization_counts': [4, 0],
              'original_preservation_call_counts': [2, 2], 'all_hooks_restored': True,
              'file_count': len(new_files), 'files': {str(p.relative_to(ROOT)): sha(p) for p in new_files},
              'scope': 'Unchanged post-preservation controls completed with original custody; diagnostic semantics are not assessed by this seal.'}
    out = HERE / 'result_manifest_v1.json'
    with out.open('x') as stream:
        json.dump(sealed, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'path': str(out), 'sha256': sha(out), 'files': len(new_files),
                      'held_bindings_rehashed': len(bindings), 'status': sealed['status']}))


if __name__ == '__main__':
    main()
