"""Capture public HTTP artifacts for the disclosed record-operation development run."""
import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path('/home/moloch/semabi')
BASE = ROOT / 'runs/product_record_v1'
TOKEN = (ROOT / 'runs/product_service_v1/token').read_text().strip()
SECRETS = [TOKEN]
for app in ('memos', 'linkding'):
    credentials = json.loads((ROOT / f'runs/product_apps_v1/{app}/private/credentials.json').read_text())
    SECRETS.extend(credentials[key] for key in ('username', 'password'))


def get(path):
    with urlopen(Request('http://127.0.0.1:8860' + path,
                         headers={'Authorization': 'Bearer ' + TOKEN}), timeout=10) as response:
        return json.load(response)


def redact(value):
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        for secret in sorted(SECRETS, key=len, reverse=True):
            value = value.replace(secret, '[REDACTED]')
    return value


result = {'classification': 'Disclosed development HTTP calls, not a fixed task assessment',
          'source_sha256': json.loads((BASE / 'source_sha256.json').read_text()),
          'client_logs': [], 'jobs': {}, 'operations': []}
for path in sorted(BASE.glob('*.log')):
    ids = list(dict.fromkeys(re.findall(r'"job_id":\s*"([^"]+)"', path.read_text())))
    if not ids:
        continue
    result['client_logs'].append({'path': str(path.relative_to(ROOT)),
                                 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'job_ids': ids})
    for job_id in ids:
        job = get('/v1/jobs/' + job_id)
        assert job['status'] in ('COMPLETED', 'FAILED'), 'Do not archive an unfinished job as complete'
        result['jobs'][job_id] = job
connection = 'conn_69dde230fe564df8899a808d6cfd5d20'
result['connection'] = get('/v1/connections/' + connection)
result['operations'] = get('/v1/connections/' + connection + '/operations')['operations']
for operation in result['operations']:
    for name, expected in operation['support']['source_sha256'].items():
        assert hashlib.sha256((ROOT / 'semabi/compiler' / name).read_bytes()).hexdigest() == expected
result = redact(result)
(BASE / 'service_snapshot.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'operations': [{key: op[key] for key in ('id', 'version', 'kind')} for op in result['operations']],
                  'jobs': [{key: job[key] for key in ('id', 'kind', 'status')} |
                           {key: job['result'].get(key) for key in ('metrics', 'invalidations', 'attempts', 'outcome')}
                           for job in result['jobs'].values()]}, indent=2))
