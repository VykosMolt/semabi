"""Offline independent READ comparison and selected-evidence packaging."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / 'runs/product_menu_linkding_evaluator_v2'
INPUT = ROOT / 'runs/product_menu_linkding_v2'
PUBLIC = ROOT / 'docs/data/v4/transport/product/menu_linkding_v2'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
def load(path): return json.loads(path.read_text())

spec = importlib.util.spec_from_file_location('capture', PRIVATE / 'capture_linkding.py')
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
expected, provenance = capture.prior_observed_values()
result = load(PRIVATE / 'read_check/result.json')
assert result['verdict'] == 'PASS' and result['source_unchanged']
assert result['expectations'] == expected and result['expected_state_provenance'] == provenance
frozen = load(INPUT / 'source_sha256.json')
assert result['source_before'] == result['source_after'] == frozen
for name, digest in frozen.items():
    assert sha(ROOT / name) == digest
    assert sha(ROOT / 'runs/product_menu_v2/source_snapshot' / name) == digest
actuals = []
for item in result['captures']:
    raw = PRIVATE / 'read_check' / (item['snapshot_id'] + '.json')
    assert sha(raw) == item['snapshot_sha256']
    snapshot = load(raw)
    values = {}
    for name, record in item['records'].items():
        independently_matched = capture.reader.record_checks('linkding', snapshot, expected[name])
        assert record == independently_matched and record['exact_matching_record_count'] == 1
        selected = record['selected_records'][0]
        title = selected['title_and_destination_nodes'][0]
        values[name] = {'url':title['destination'], 'title':title['text'],
            'tags':selected['tag_nodes'][0]['text'], 'description':selected['description_nodes'][0]['own_text']}
    assert values == expected
    actuals.append({'stage':item['stage'], 'snapshot_id':item['snapshot_id'], 'actual_observed_values':values})
service = load(INPUT / 'service_snapshot.json')
jobs = [job for job in service['jobs'].values() if job['kind'] == 'invoke']
assert len(jobs) == 1
job = jobs[0]
assert job['status'] == 'COMPLETED' and job['result']['outcome'] == 'CONFIRMED'
assert job['request']['arguments'] == {'target':expected['target']['url']}
assert job['result']['effect']['values'] == expected['target']
assert result['termination']['live_owned_process_count'] == 0
assert all(p['after_close'] == 'absent' for p in result['termination']['owned_processes'])
comparison = {'classification':'Disclosed development exact-known-URL READ, not paired assessment',
    'verdict':'PASS', 'job_id':job['id'], 'operation_id':job['request']['operation_id'],
    'version':job['request']['version'], 'request':job['request'],
    'runtime_reported_values':job['result']['effect']['values'],
    'runtime_reported_metrics':job['result']['metrics'],
    'expected_state_provenance':provenance, 'independent_current_values':actuals,
    'source_sha256':frozen,
    'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [INPUT / 'read.log', INPUT / 'service_snapshot.json', PRIVATE / 'read_check/result.json']},
    'claim':'All four returned fields equal prior actual DOM fields and both fresh ordinary-DOM observations; sampled non-target fields agree before and after reload.',
    'limitations':['Exact known URL only; no search or filter request evaluated.',
        'No new UPDATE effect check in this checkpoint.',
        'Visible local record context does not establish persistent identity, global uniqueness, or unobserved side effects.']}
save(PRIVATE / 'comparison.json', comparison)
PUBLIC.mkdir(parents=True, exist_ok=True)
for src, dest in [(INPUT / 'read.log','linkding_read.log'), (INPUT / 'learn.log','linkding_learn.log'),
    (INPUT / 'service_snapshot.json','service_snapshot.json'), (INPUT / 'source_sha256.json','source_sha256.json'),
    (INPUT / 'validation.json','validation.json'), (INPUT / 'capture_service.py','capture_service.py'),
    (PRIVATE / 'read_check/result.json','independent_read_check.json'), (PRIVATE / 'comparison.json','comparison.json'),
    (PRIVATE / 'capture_linkding.py','capture_linkding.py'), (Path(__file__),'seal.py')]:
    shutil.copyfile(src, PUBLIC / dest)
files = [p for p in PUBLIC.rglob('*') if p.is_file() and p.name != 'manifest.json']
for app in ('linkding','memos'):
    private = load(ROOT / f'runs/product_apps_v1/{app}/private/credentials.json')
    forbidden = [v.encode() for k,v in private.items() if isinstance(v,str) and ('password' in k or 'token' in k) and v]
    for p in files:
        assert not any(secret in p.read_bytes() for secret in forbidden), f'Credential spill in {p.name}'
manifest = {'classification':comparison['classification'], 'files':{str(p.relative_to(PUBLIC)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(files)},
    'private_full_dom_policy':'Full ordinary-DOM snapshots remain private; selected record nodes and snapshot hashes are public.',
    'checker_execution':{'launch_and_terminal_chunk':'390858','exit_code':0,'cpu_affinity':[4]},
    'shared_validation':'../menu_record_operations_v2/validation.json'}
save(PUBLIC / 'manifest.json',manifest)
print(json.dumps({'verdict':comparison['verdict'],'files':len(files),'bytes':sum(p.stat().st_size for p in files),'all_ten_source_hashes_match':True,'credential_scan':'PASS'}))
