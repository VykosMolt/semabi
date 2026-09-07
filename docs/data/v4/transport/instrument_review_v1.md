# T1 instrument review, before fresh evaluation

Reviewer: `/root/acquisition_audit`, 2026-09-07 15:14 UTC.
Repository HEAD: `9bc371ce9af65241426b77585aa79352bdd7f123`.

The bounded instrument checks below pass. They validate collection, evidence
boundaries, serialization and measurement accounting, not the fixture semantics
or the campaign's scientific hypotheses. No fresh evaluation was run or read.

The reviewer previously implemented `transport_score.py`; its executable checks
are therefore not an independent implementation review. The collector and
protocol were authored by root and reviewed separately here. Root also reviewed
the scorer and requested the missing-target and runtime-freeze checks. This
reviewer saw existing SemABI source/tests and disclosed retained notes, plus the
public workflow descriptions in the protocol. No fresh application source,
oracle script, reserved interface, evaluation values or outcomes were inspected.

## Exact reviewed artifacts

| File | SHA-256 |
| --- | --- |
| `scripts/transport_collect.py` | `193231330e0e1cf898768f98e9f91649d4ae13920c45a4cbfe00cccbed4bc63c` |
| `scripts/transport_score.py` | `0f4d272e1267485af86740b6a27fdd239864836aa4642475260e200a6008bc77` |
| `docs/data/v4/transport/protocol_v1.md` | `02a29daf097dedf5a7cee490055e1b25abbe8e0cdec079adc0fce2d971559d57` |
| `docs/data/v4/transport/baseline/check_corpora.py` | `ecfb411df3cc80c00642b6166874a705f4135f8bbf6224d71c45234ee7c0ce0d` |

All commands below ran in `/home/moloch/semabi`, using `.venv/bin/python -B`,
`PYTHONHASHSEED=0`, and numeric-library thread counts set to one, with synthetic
inputs under automatically removed temporary directories. No browser, server or
background process remained after the checks. The five embedded commands were
also re-extracted from this review and rerun against the final reviewed code.

## Findings resolved before the freeze

1. Acquisition initially reused episode numbers from copied initial evidence.
   Initializing the new browser episode at the existing maximum separates the
   histories used by the clock policy.
2. The collector initially observed the server before resetting it. That could
   expose a previous arm's terminal state. Reset now precedes every session's
   first observation, and its empty pre-state is explicitly marked unobserved.
3. Unresolved scripted click targets initially disappeared from scorer click
   denominators. They now remain as an unestablished `unreachable_target`
   subtype, including their failed attempt and action descriptor.
4. A runtime manifest containing sealed fixture/oracle paths initially caused
   both runtime verifiers to open those files just to hash them. A harmless
   synthetic sentinel reproduced this. Runtime `files` now has an explicit
   learner/evidence allowlist, while `sealed_evaluator_files` is metadata only
   and is verified in the separate evaluator/orchestrator. Canonical path
   checks reject traversal, absolute paths and symlink redirects, including
   redirects to another location within the repository.
5. The scorer originally hashed every `semabi/**/*.py` file for source
   provenance. Pre-freeze synthetic helper calls therefore hashed existing
   `semabi/hidden` and `semabi/env` implementation bytes. They did not display
   those contents to the reviewer or provide them to fitting/policy functions;
   no fresh `experiments/transport_v1` or fresh oracle files were read. The
   source-version function now hashes only 66 permitted learner implementation
   files. This correction precedes any campaign result.
6. The retained-corpus diagnostic accessed `role.kind` on an `outcome.Alias`,
   which has no such member. Its owner was notified after a synthetic crash
   reproduced. The corrected diagnostic recursively inspects alias parts while
   retaining one semantic role. It also allows the visible vessel to be supplied
   by a bound relation instead of requiring the action owner itself to be keyed
   by the vessel. Positive and discriminating negative checks pass below.

## Scientific limits that remain explicit

- This is generated-interface transfer after supplied demonstrations. It does
  not establish direct Harbour-reading transport, independently authored
  application transfer, or a statistical treatment effect from two seeds.
- The treatment is the existing contested predicate plus existing Explorer,
  with the documented snapshot-order preference and literal-set deduplication.
  It is not the old target-parameterized acquisition function unchanged.
- `Explorer.choose()` does not propose reload/reset: after the charged setup
  reset this wrapper has no special persistence-probe or replay policy. A
  missed discriminator may be a policy limitation. It is not evidence of
  observational equivalence.
- Source preparation preserves the first eight candidates in the existing
  generator's order and discloses later candidates from that same neighborhood.
  It does not enumerate every identity, union, link choice or joint partition.
- The scorer uses the frozen raw live observation transform, matching the
  collector. It does not normalize evaluation observations using their own
  statistics. Any mismatch between training normalization and live reading is
  a measured limitation of the frozen system, not silently repaired here.
- Complete masks/index/events and query literals reproduce surviving outcome
  support within the frozen language. Representative vouches alone are not a
  complete set of explanations. Changes in representation/language across refits
  still require explicit comparison before claiming elimination of a rival.
- Raw scorer click totals include navigation and setup. The final campaign
  report must join `decisions.jsonl`'s `case`, `task_family`, `task_target` and
  `step` fields with scorer rows to retain task-specific denominators, including
  unreachable designated targets. These labels are evaluator metadata and do
  not enter fitting or acquisition.
- The shared scoreboard is descriptive. Empty/shared/shrinking surfaces,
  slot-fallback coordinates, contradictions and unshared material remain visible;
  a candidate merely unrefuted on that surface is not independently identified.
- Fixture expressibility, held-out negative cases, hidden observational
  equivalence, independent state/argument controls and final failure attribution
  remain for the separate fixture audit and post-preservation analysis. This
  source review does not certify them without seeing their evidence.
- The final protocol explicitly records the author's rejected v1 ambiguity
  design, the sealed v2 transition argument, and dispatch-only raw eligibility
  for the monotone-quantity attack. The reviewer saw these design-level
  disclosures, not the withheld values or audit histories. Rejection of a
  resolvable case and retaining its source is the correct evidence treatment;
  the v2 proof remains the fixture author's separately audited responsibility.

## Reproduction A: multiple cases, resets, target indices and failed attempts

```bash
.venv/bin/python -B - <<'PY'
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from scripts import transport_collect as c
from semabi.compiler.browser import ActionResult
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Node, Observation

class FakeBrowser:
    instances = []
    def __init__(self, url, reset_url):
        self.url, self.reset_url, self.episode = url, reset_url, 0
        self.n_settle_timeouts = self.n_navigation_waits = 0
        self.calls, self.closed = [], False
        self.__class__.instances.append(self)
    def act(self, primitive):
        self.calls.append((primitive.kind, self.reset_url, primitive.target))
        if primitive.kind == 'reset': self.episode += 1
        return ActionResult(primitive.target != 2, 'synthetic browser failure' if primitive.target == 2 else None)
    def observe(self):
        assert self.calls and self.calls[0][0] == 'reset', 'observed before reset'
        return Observation([Node(0,-1,'group',''),Node(1,0,'button','Go'),
                            Node(2,0,'button','Fail'),Node(3,0,'textbox','Amount')], self.url)
    def close(self): self.closed = True

spec = {'cases': [
    {'case':'one','family':'simple','reset_url':'/reset/a','target_action_index':1,
     'script':[{'kind':'snapshot'},{'kind':'click','role':'button','name':'Go'},
               {'kind':'snapshot'},{'kind':'click','role':'button','name':'Missing'}]},
    {'case':'two','family':'simple','reset_url':'/reset/b','target_action_index':1,
     'script':[{'kind':'snapshot'},{'kind':'type','role':'textbox','name':'Amount','value':'5'},
               {'kind':'click','role':'button','name':'Fail'}]}]}
with TemporaryDirectory(prefix='transport_review_multicase_') as tmp:
    root=Path(tmp); script=root/'public_synthetic.json'; script.write_text(json.dumps(spec))
    args=SimpleNamespace(script=script, fixture=None, url='http://127.0.0.1:1234/public',
                         reset_url='http://127.0.0.1:1234/reset', out=root/'run', seed=7)
    with patch.object(c,'Browser',FakeBrowser): result=c.collect_script(args)
    log=EvidenceLog(args.out)
    rows=[json.loads(line) for line in (args.out/'decisions.jsonl').read_text().splitlines()]
    browser=FakeBrowser.instances[-1]
    resets=[row for row in rows if row['action']['kind']=='reset']
    targets=[row for row in rows if row.get('task_target')]
    assert result['charged_attempts']==6 and result['failed_attempts']==2
    assert result['primitive_counts']=={'reset':2,'click':3,'type':1}
    assert result['snapshot_calls']==8 and result['case_count']==2 and not result['complete']
    assert [step.episode for step in log.steps]==[1,1,1,2,2,2]
    assert [row['reset_url'] for row in resets]==['http://127.0.0.1:1234/reset/a','http://127.0.0.1:1234/reset/b']
    assert [row['script_index'] for row in targets]==[3,2]
    assert [row['step'] for row in targets]==[2,5]
    assert targets[0]['action'].get('target') is None and not targets[0]['ok']
    assert targets[1]['action']['target']==2 and not targets[1]['ok']
    assert not log.obs(log.steps[0].before).nodes
    assert browser.closed and len(browser.calls)==5
    print(json.dumps({'charged_attempts':result['charged_attempts'],'resets':len(resets),
                      'failed_attempts':result['failed_attempts'],'episodes':[step.episode for step in log.steps],
                      'target_steps':[row['step'] for row in targets],'snapshot_calls':result['snapshot_calls'],
                      'browser_calls':len(browser.calls),'closed':browser.closed},sort_keys=True))
PY
```

Observed exit 0:

```json
{"browser_calls": 5, "charged_attempts": 6, "closed": true, "episodes": [1, 1, 1, 2, 2, 2], "failed_attempts": 2, "resets": 2, "snapshot_calls": 8, "target_steps": [2, 5]}
```

## Reproduction B: sealed metadata and runtime pathname boundary

All application/oracle paths below are temporary synthetic sentinels. No actual
sealed application or evaluation file is opened by this test.

```bash
.venv/bin/python -B - <<'PY'
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from scripts import transport_collect as c, transport_score as s
with TemporaryDirectory(prefix='transport_review_allowlist_') as tmp:
    root=Path(tmp); runtime=root/'semabi/compiler/runtime.py'; runtime.parent.mkdir(parents=True)
    runtime.write_text('RUNTIME = 1\n')
    secret=root/'experiments/oracle/private.py'; secret.parent.mkdir(parents=True); secret.write_text('SEALED = 17\n')
    redirected=root/'semabi/compiler/redirect.py'; redirected.symlink_to(secret)
    data=root/'docs/data/v4/transport/first_pass/initial/steps.jsonl'; data.parent.mkdir(parents=True); data.write_text('{}\n')
    manifest=root/'freeze.json'
    runtime_hash=s.file_digest(runtime); secret_hash=s.file_digest(secret); data_hash=s.file_digest(data)
    original=Path.read_bytes; opened=[]
    def watched(path):
        opened.append(path.resolve())
        if path.resolve()==secret.resolve(): raise AssertionError('sealed source opened')
        return original(path)
    checked=0
    with patch.object(c,'ROOT',root),patch.object(s,'ROOT',root),patch.object(Path,'read_bytes',watched):
        manifest.write_text(json.dumps({'files':{'semabi/compiler/runtime.py':runtime_hash,
            'docs/data/v4/transport/first_pass/initial/steps.jsonl':data_hash},
            'sealed_evaluator_files':{'experiments/oracle/private.py':secret_hash}}))
        for verify in (c.verify_freeze,s.verify_freeze): verify(manifest)
        for bad in ('experiments/oracle/private.py','semabi/compiler/../../experiments/oracle/private.py',
                    'semabi/compiler/redirect.py',str(secret),'semabi/compiler/../env/private.py',
                    'docs/data/v4/transport/first_pass/oracle/steps.jsonl'):
            manifest.write_text(json.dumps({'files':{bad:secret_hash}}))
            for verify in (c.verify_freeze,s.verify_freeze):
                try: verify(manifest)
                except RuntimeError as exc: assert 'learner paths' in str(exc).lower(),str(exc)
                else: raise AssertionError('forbidden path accepted: '+bad)
                checked+=1
    assert secret.resolve() not in opened
    print(json.dumps({'valid_runtime_verifiers':2,'forbidden_path_rejections':checked,'sealed_content_reads':0},sort_keys=True))
version=s.source_version()
assert len(version['implementation_files'])==66
assert all(s.permitted_runtime_path(path) for path in version['implementation_files'])
print('source_version: 66 allowed learner implementation files; no hidden/env/application files')
PY
```

Observed exit 0:

```text
{"forbidden_path_rejections": 12, "sealed_content_reads": 0, "valid_runtime_verifiers": 2}
source_version: 66 allowed learner implementation files; no hidden/env/application files
```

## Reproduction C: candidate cap and exact omission inventory

This injects twelve synthetic results into the wrapper's generator boundary;
it tests wrapper selection/accounting, not the scientific completeness of the
existing source generator.

```bash
.venv/bin/python -B - <<'PY'
import json,sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from scripts import transport_score as s
from tests.test_v4_probe_adapter import _valid_run
from semabi.compiler.v4.pinned import PinnedReading
class Search:
    def to_json(self): return {'synthetic':True}
with TemporaryDirectory(prefix='transport_review_candidates_') as tmp:
    root=Path(tmp); train=_valid_run(root/'train')
    secret=root/'sealed_do_not_load.py'; secret.write_text('SYNTHETIC = 17\n')
    original=Path.read_bytes; opened=[]
    def watched(path):
        opened.append(path.resolve()); return original(path)
    choices=[PinnedReading(name=f'reading_{i}') for i in range(12)]
    def generator(path,log,**kw):
        assert path==train and log.dir==train
        assert kw=={'max_candidates':sys.maxsize,'refuted':{},'records':[]}
        return Search(),choices,[],None,None
    with patch.object(s.source_candidates,'source_candidates',generator),patch.object(Path,'read_bytes',watched):
        result=s.prepare(train,root/'prepared')
    assert result['cap']==8 and result['retained_count']==8
    assert [row['name'] for row in result['candidates']]==[f'reading_{i}' for i in range(8)]
    assert [row['name'] for row in result['omitted_due_to_cap']]==[f'reading_{i}' for i in range(8,12)]
    assert secret.resolve() not in opened
    print(json.dumps({'retained':result['retained_count'],'omitted':len(result['omitted_due_to_cap']),
                      'sealed_sentinel_reads':0},sort_keys=True))
PY
```

Observed exit 0:

```json
{"omitted": 4, "retained": 8, "sealed_sentinel_reads": 0}
```

## Reproduction D: reconstruct support and preserve missing target denominators

```bash
.venv/bin/python -B - <<'PY'
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from scripts import transport_score as s
from semabi.compiler.observation import Node, Observation
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.browser import Primitive
from semabi.compiler.v4 import outcome as oc

def observation(value,reply):
    rows=[('group','',-1),('table','',0),('rowgroup','',1),('row','',2),('cell','Alpha',3),
          ('cell',value,3),('button','Flip',3),('row','',2),('cell','Beta',7),('cell','ready',7),
          ('button','Flip',7),('status',reply,0)]
    return Observation([Node(i,p,r,n) for i,(r,n,p) in enumerate(rows)])
def trace(path,missing=False):
    log=EvidenceLog(path); before=observation('cold','Waiting')
    for i in range(8):
        after=observation('warm' if i%2==0 else 'cold','Warmed Alpha' if i%2==0 else 'Cooled Alpha')
        log.add_step(1,Primitive('click',6,target_desc={'role':'button','name':'Flip'}),True,None,before,after)
        before=after
    if missing: log.add_step(1,Primitive('click',target_desc={'role':'button','name':'Missing'}),False,'unreachable',before,before)
    return log
with TemporaryDirectory(prefix='transport_review_support_') as tmp:
    root=Path(tmp); trace(root/'train'); evaluation=trace(root/'eval',missing=True)
    record,surface=s.score_model(s.fit_train(root/'train'),evaluation)
    json.dumps(s.jsonable(record),allow_nan=False)
    reconstructions={}
    for control,model in record['model']['outcomes'].items():
        evidence=model['evidence']; index={entry['bit']:tuple(entry['literal']) for entry in evidence['index']}
        rows=[({literal for bit,literal in index.items() if int(mask)&(1<<bit)},event,frozenset())
              for mask,event in zip(evidence['masks_decimal'],evidence['events'])]
        reconstructions[control]=oc.Evidence(rows)
    checks=0
    for query in record['queries']:
        if 'representative_support' not in query: continue
        literals={tuple(literal) for literal in query['query_literals']}
        for hypothesis in (oc.RULE,oc.LIST):
            rebuilt=reconstructions[query['control']].admissible(literals,corroborated=True,hypothesis=hypothesis)
            assert sorted(rebuilt)==sorted(query['representative_support'][hypothesis])
            checks+=1
    for channel in ('decision_list',oc.RULE,oc.LIST):
        summary=record['emission'][channel]['summary']
        assert summary['denominator_all_click_attempts']==9 and summary['unreachable_target']==1
        assert sum(summary['categories'].values())==9
    empty=s.shared_report({'a':{'state':{'1|VALUE|4':['SUPPORTED','x']},'emission':{}},
                           'b':{'state':{'2|VALUE|5':['SUPPORTED','y']},'emission':{}}},{})
    assert empty['state_shared_size']==0 and empty['state_union_size']==2
    print(json.dumps({'support_reconstructions':checks,'all_click_attempts':9,'unreachable_target':1,
                      'empty_shared_size':empty['state_shared_size'],'empty_union_size':empty['state_union_size']},sort_keys=True))
PY
```

Observed exit 0:

```json
{"all_click_attempts": 9, "empty_shared_size": 0, "empty_union_size": 2, "support_reconstructions": 16, "unreachable_target": 1}
```

## Reproduction E: retained diagnostic alias and related-vessel control

The function is extracted from source to avoid importing or running the retained
corpus instrument. The call-key owner and its related vessel deliberately differ.

```bash
.venv/bin/python -B - <<'PY'
import ast, json
from pathlib import Path
from semabi.compiler.observation import Node, Observation
from semabi.compiler.abstract import AbsObj
from semabi.compiler.v4.outcome import Alias, Role
path=Path('docs/data/v4/transport/baseline/check_corpora.py')
node=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='visible_check')
ns={}; exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),ns)
rows=[('group','',-1),('combobox','',0),('button','Book',0),('table','',0),('row','',3),
      ('cell','Vessel',4),('cell','VesselA',4),('row','',3),('cell','Length overall',7),('cell','85 m',7)]
obs=Observation([Node(i,p,r,n,value='A' if i==1 else None) for i,(r,n,p) in enumerate(rows)])
roles={'resource':Alias('resource',(Role('selected','selection',('combobox#0',),1),),1)}
bound={'owner':AbsObj(2,'C1',{}),'vessel':AbsObj(3,'VesselA',{'attr:Length overall#0':'85'}),'resource':AbsObj(1,'A',{})}
checks=ns['visible_check'](obs,2,bound,roles)
assert [row['status'] for row in checks]==['match','match','match']
bound['vessel'].attrs['attr:Length overall#0']='90'
negative=ns['visible_check'](obs,2,bound,roles)
assert [row['status'] for row in negative]==['match','match','mismatch']
print(json.dumps({'alias_and_related_vessel':[row['status'] for row in checks],
                  'wrong_related_length':[row['status'] for row in negative]},sort_keys=True))
PY
```

Observed exit 0:

```json
{"alias_and_related_vessel": ["match", "match", "match"], "wrong_related_length": ["match", "match", "mismatch"]}
```
