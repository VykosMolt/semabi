"""Root's independent postflight for the completed, training-only replay."""
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


def verify_map(mapping):
    for name, digest in mapping.items():
        path = ROOT / name
        assert not Path(name).is_absolute() and path.resolve(strict=True) == path
        assert path.is_file() and not path.is_symlink() and sha(path) == digest, name


def main():
    source = HERE / 'source_manifest_v2.json'
    assert sha(source) == '9a034671ba155b5a5ebfd2ee81cda49d362219f067079342b993399c94f21757'
    manifest = read(source)
    verify_map(manifest['files'])
    verify_map(manifest['inputs'])
    freeze = read(J1 / 'evaluation_freeze_v2.json')
    preservation = read(J1 / 'first_pass_manifest_v2.json')
    assert preservation['status'] == 'PRESERVED' and len(preservation['files']) == 705
    verify_map(preservation['files'])
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == freeze['source_head'] == '6aea64baac1678cbce8ba4b1a41ab04756225c7d'
    native = {str(p.relative_to(ROOT)) for p in (ROOT / 'semabi').rglob('*.py')}
    assert native == {n for n in freeze['source_files'] if n.startswith('semabi/')}
    job = read(HERE / 'jobs/replay_v1/process.json')
    assert job['runner_pid'] == 1187307 and job['child_pid'] == job['owned_process_group'] == 1187309
    assert job['status'] == 'FINISHED' and job['returncode'] == 0 and job['child_terminated'] is True
    assert job['source_head'] == head and job['cwd'] == str(ROOT) and job['owner'] == '/root'
    assert job['command'] == ['.venv/bin/python', '-B', str((HERE / 'diagnose.py').relative_to(ROOT)),
                              '--manifest', str(source), '--manifest-sha256', sha(source)]
    assert job['python_hash_seed'] == '0' and set(job['thread_limits'].values()) == {'1'}
    assert job['log_sha256'] == sha(HERE / 'jobs/replay_v1/output.log')
    assert job['source_hashes'] == {n: freeze['source_files'][n] for n in native}
    verify_map(job['source_hashes'])
    verify_map(job['instrument_hashes'])
    reaped = read(HERE / 'root_reap_tool_v1.json')
    assert reaped['args']['session_id'] == 5981 and reaped['result']['exit_code'] == 0
    assert not (HERE / 'unused_bytecode_prefix_v2').exists()
    assert not (HERE / 'unused_bytecode_prefix_v2').is_symlink()
    assert not Path('/proc/1187307').exists() and not Path('/proc/1187309').exists()
    assert Path('/proc/1/stat').is_file()
    groups = []
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(') ', 1)[1].split()
        except (FileNotFoundError, ProcessLookupError):
            continue
        if int(fields[2]) == 1187309:
            groups.append(str(path.parent))
    assert groups == []
    result = read(HERE / 'diagnosis_v1.json')
    assert sha(HERE / 'diagnosis_v1.json') == '67694dc901390b23736875281a911b4cb34cf7db8b7739cf54c598e2d4b7415f'
    assert result['status'] == 'MATCHED_TRAINING_REPLAY' and result['projection_exactly_matches'] is True
    assert result['error'] is None and result['postflight_error'] is None
    assert result['fit_invocations_in_this_script'] == 1 and len(result['compile_calls']) == 1
    assert result['pid'] == 1187309 and result['cpu_affinity'] == [19]
    assert result['entry_point_restored'] is True and result['bytecode_prefix_absent_after_fit'] is True
    assert result['different_projection_fields'] == [] and result['source_manifest_sha256'] == sha(source)
    verify_map({result['projection']['path']: result['projection']['sha256']})
    for field in ('native_module_origins_before_fit', 'native_module_origins_after_fit'):
        origins = result[field]
        assert origins
        for record in origins.values():
            assert record['path'] in native and record['sha256'] == preservation['files'][record['path']]
    projection = read(HERE / 'projection_v1.json')
    original = read(J1 / 'evaluation_execution_v2/predictor_v2/fit_trace.json')
    assert projection == original['projection'] and projection['status'] == 'COMPLETE'
    paths = sorted(p for p in HERE.rglob('*') if p.is_file())
    assert all(p.resolve(strict=True) == p and not p.is_symlink() for p in paths)
    output = HERE / 'artifact_manifest_v1.json'
    assert output not in paths
    sealed = {
        'schema': 'semabi.j1.identity_search_diagnostic_artifacts.v1',
        'status': 'VERIFIED_MATCHED_TRAINING_REPLAY',
        'verified_utc': datetime.now(timezone.utc).isoformat(),
        'source_head': head,
        'source_manifest_sha256': sha(source),
        'first_pass_manifest_sha256': sha(J1 / 'first_pass_manifest_v2.json'),
        'preserved_files_rehashed': len(preservation['files']),
        'native_source_files_rehashed': len(native),
        'full_projection_independently_equal': True,
        'owned_pids_absent': [1187307, 1187309],
        'owned_process_group_absent': 1187309,
        'root_session_reaped': 5981,
        'bytecode_prefix_absent': True,
        'scope': 'Training replay only; native search data retained but not evaluated by this seal. No fresh-interface or JOIN success claim.',
        'files': {str(p.relative_to(ROOT)): sha(p) for p in paths},
    }
    with output.open('x') as stream:
        json.dump(sealed, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'path': str(output), 'sha256': sha(output), 'files': len(paths),
                      'status': sealed['status'], 'owned_pids_absent': sealed['owned_pids_absent']}))


if __name__ == '__main__':
    main()
