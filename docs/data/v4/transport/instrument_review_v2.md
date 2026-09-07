# T1 instrument V2 review, before fresh evaluation

Reviewer: `/root/acquisition_audit`, 2026-09-07 15:41 UTC.
Repository HEAD: `0283151f42d39b7457041a4a1be01c4f647bbc6c`.

The bounded integration and failure-accounting checks below pass. V2 is ready
for initial collection and source preparation, then the final evidence freeze
before held-out evaluation. This acceptance concerns the instrument; the frozen
learner still has the independently reproduced graph failure below. No SemABI
production file differs from `9bc371ce9af65241426b77585aa79352bdd7f123`.

V1 remains preserved at `795d073`. Its review checked collection with a mocked
browser separately from synthetic learner fits. That did not exercise the actual
collector-produced empty bootstrap Observation through the learner, and therefore
missed the initialization failure. The first dispatch initial run had 32 charged
attempts and zero recorded action failures; preparation then failed at node zero
in `Hypotheses.parse_units`. This reviewer read that initial-only preparation
traceback. No fresh held-out outcome, fixture application implementation, oracle
script or reserved interface was inspected. The fixture author's separate audit
owns those semantics and exposure records.

This reviewer authored the earlier scorer; the scorer checks here are executable
verification, not an independent implementation review of their own code. Root
reviewed the scorer and authored the V2 changes. This reviewer independently
reviewed collector behavior, the V2 correction policy and the protocol.

## Exact reviewed artifacts

| File | SHA-256 |
| --- | --- |
| `scripts/transport_collect.py` | `022f80109a55b0ff86c06fa72ca3654a3b15ab3a66c187cace15b00b828fcc14` |
| `scripts/transport_score.py` | `9a4cd7cadc8646e031e54368de6a32b4f9628698de3b8c321a39219b19dee7cc` |
| `docs/data/v4/transport/protocol_v2.md` | `8afcfbd40b292f6be71763f1787a42a4a7fda63ad56c413f254a40cb7de80892` |

## Findings and acceptance limits

- V2 records the first reset as a charged event with `before=null`, actual
  observed after-state and no paired Step. A genuine charged reload follows.
  The executable browser double changes a visible render counter on reload,
  proving that the stored boundary is an actual before/after transition. Later
  observed case resets remain Steps. All observations passed to fitting have
  actual nodes. A new acquisition session advances the prior maximum episode.
- The actual collector output now passes the real source-candidate generator,
  initial fit, both acquisition arms, scheduled refits and terminal fits. Both
  arms preserve the initial raw files as byte prefixes. The first reset and
  reload consume two of the stated primitive budget, in both arms.
- The integrated contested preflight exposed a separate existing learner
  limitation: inferred `A.G` and `A.H.G` can differ. Reading an unseen signature
  adds it to `A.G`, then `H.parse_units` raises `KeyError` because `H.G` lacks it.
  The direct control below still reproduces this. A reading generated only from
  the same initial synthetic evidence shares its graph and succeeds. That
  pinned control is diagnostic evidence, not an oracle or a production repair.
- Per-button recognition exceptions retain the node, charged decision's raw
  before-state signature, error and full traceback. They supply no contested
  prediction. The existing Explorer fallback spends the same primitive budget.
  Failed scheduled fits record the training cut and traceback, set model
  availability to false, and retry only at the existing schedule. Computation
  failures remain distinct from failed world actions. The real contested
  synthetic run records 22 recognition failures and zero targeted actions;
  completing its budget does not establish acquisition success.
- Evaluation exceptions are accounted for separately by state, decision-list,
  RULE, LIST and query channel. A failed fit keeps its reading and all click
  opportunities. Failed state checks supply no fabricated claims; successful
  later checks survive. Empty surfaces from failed readings remain in the
  shared intersection. A runtime failure cannot establish H1, H2 or a removed
  rival outcome. The failed-attempt ledger must still be joined to the fixed
  evaluator task coordinates in the campaign analysis.
- The state wrapper changes batching to one click at a time, while retaining
  native per-step summaries and raw claim coordinates. On the positive control,
  all 16 state rows exactly match a single native full-trace scoring call.
  Independent RULE failure injection leaves LIST and decision-list rows
  unchanged. Existing complete-mask support reconstruction still passes all
  16 RULE/LIST checks. Model serialization and evidence/freeze violations remain
  fatal instrument errors; interrupts are not swallowed as learner failures.
- V1's runtime path allowlist, sealed metadata separation, candidate cap and
  disclosure of language omissions remain unchanged. Its scientific limits
  still apply: generated interfaces after demonstrations, bounded candidate
  language, fixed attempted-click scope, and no semantic identification from an
  empty or shrinking shared surface. This review does not certify future
  campaign results or H4's separate fixture proof.

All commands below run from `/home/moloch/semabi`; inputs are public synthetic
Observations created inside automatically removed temporary directories. Only
the browser is mocked in reproduction A: source generation, fitting, Explorer,
contested queries and scheduled refits use the unchanged learner. Reproduction C
injects named exceptions only at the boundary being tested. No real browser,
server or background process is started by these checks.

## Reproduction A: actual collection through actual learning and acquisition

```bash
PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .venv/bin/python -B - <<'PY'
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from scripts import transport_collect as c, transport_score as s
from semabi.compiler.browser import ActionResult
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Node, Observation

class FakeBrowser:
    instances = []
    def __init__(self, url, reset_url):
        self.url, self.reset_url, self.episode = url, reset_url, 0
        self.n_settle_timeouts = self.n_navigation_waits = 0
        self.calls = []; self.closed = False; self.generation = 0; self.value = ''
        self.__class__.instances.append(self)
    def act(self, primitive):
        self.calls.append((primitive.kind, self.reset_url, primitive.target))
        if primitive.kind == 'reset': self.episode += 1; self.generation = 0; self.value = ''
        elif primitive.kind == 'reload': self.generation += 1
        elif primitive.kind == 'type': self.value = primitive.text or ''
        ok = primitive.target != 2
        return ActionResult(ok, None if ok else 'synthetic browser failure')
    def observe(self):
        assert self.calls and self.calls[0][0] == 'reset', 'observed before reset'
        return Observation([Node(0,-1,'group',''), Node(1,0,'button','Go'), Node(2,0,'button','Fail'),
                            Node(3,0,'textbox','Amount',value=self.value),
                            Node(4,0,'text',f'Render {self.generation}')], self.url)
    def close(self): self.closed = True

spec = {'cases': [
 {'case':'one','family':'simple','reset_url':'/reset/a','target_action_index':1,
  'script':[{'kind':'snapshot'},{'kind':'click','role':'button','name':'Go'},
            {'kind':'snapshot'},{'kind':'click','role':'button','name':'Missing'}]},
 {'case':'two','family':'simple','reset_url':'/reset/b','target_action_index':1,
  'script':[{'kind':'snapshot'},{'kind':'type','role':'textbox','name':'Amount','value':'5'},
            {'kind':'click','role':'button','name':'Fail'}]}]}
with TemporaryDirectory(prefix='transport_review_v2_pipeline_') as tmp:
    root = Path(tmp); script = root/'public_synthetic.json'; script.write_text(json.dumps(spec))
    args = SimpleNamespace(script=script,fixture=None,url='http://127.0.0.1:1234/public',
                           reset_url='http://127.0.0.1:1234/reset',out=root/'initial',seed=7)
    with patch.object(c,'Browser',FakeBrowser): result = c.collect_script(args)
    log = EvidenceLog(args.out)
    decisions = [json.loads(line) for line in (args.out/'decisions.jsonl').read_text().splitlines()]
    assert result['charged_attempts'] == 7 and result['paired_steps_recorded'] == 6
    assert result['unpaired_attempts'] == 1 and result['failed_attempts'] == 2
    assert result['snapshot_calls'] == 9 and result['primitive_counts'] == {'reset':2,'reload':1,'click':3,'type':1}
    assert decisions[0]['before'] is None and decisions[0]['step'] is None
    assert decisions[0]['action']['kind'] == 'reset' and decisions[0]['episode'] == 1
    assert log.steps[0].action.kind == 'reload' and log.steps[0].before == decisions[0]['after']
    assert log.steps[0].before != log.steps[0].after, 'reload must change the visible render counter'
    assert [step.episode for step in log.steps] == [1,1,1,2,2,2]
    assert [step.action.kind for step in log.steps] == ['reload','click','click','reset','type','click']
    assert [row['step'] for row in decisions if row.get('task_target')] == [2,5]
    assert all(obs.nodes for obs in log.observations.values())
    assert FakeBrowser.instances[-1].closed and len(FakeBrowser.instances[-1].calls) == 6
    prepared = s.prepare(args.out,root/'candidates')
    fitted = s.fit_train(args.out)
    assert prepared['training_steps'] == fitted.cut == 6
    assert fitted.abstractor.H.step_kinds == ['reload','click','click','reset','type','click']
    print(json.dumps({'initial_charged':7,'initial_paired':6,'initial_unpaired':1,'initial_failures':2,
                      'source_candidates':prepared['retained_count'],'real_fit_cut':fitted.cut,
                      'real_H_step_kinds':fitted.abstractor.H.step_kinds},sort_keys=True))
    for policy in ('untargeted','contested'):
        output = root/policy; output.mkdir()
        arm = SimpleNamespace(initial=args.out,out=output,url=args.url,reset_url=args.reset_url,
                              seed=7,policy=policy,budget=17)
        with patch.object(c,'Browser',FakeBrowser): acquired = c.acquire(arm)
        combined = EvidenceLog(output)
        rows = [json.loads(line) for line in (output/'decisions.jsonl').read_text().splitlines()]
        boundary = combined.steps[6]
        assert acquired['charged_attempts'] == 17 and acquired['paired_steps_recorded'] == 16
        assert acquired['unpaired_attempts'] == 1 and len(combined.steps) == 22
        assert rows[0]['before'] is None and rows[0]['step'] is None and rows[0]['episode'] == 3
        assert rows[0]['action']['kind'] == 'reset' and rows[1]['action']['kind'] == 'reload'
        assert boundary.action.kind == 'reload' and boundary.episode == 3
        assert boundary.before == rows[0]['after'] and boundary.before != boundary.after
        assert all(step.episode == 3 for step in combined.steps[6:])
        assert all(obs.nodes for obs in combined.observations.values())
        assert acquired['refits'] == [{'after_charged_attempts':0,'training_steps':6,'status':'FITTED'},
                                     {'after_charged_attempts':15,'training_steps':20,'status':'FITTED'}]
        assert json.loads((output/'refits.json').read_text()) == acquired['refits']
        failed_queries = [item for row in rows for item in row.get('candidates',[])
                          if item.get('status') == 'RECOGNITION_RUNTIME_FAILURE']
        assert acquired['recognition_runtime_failures'] == len(failed_queries)
        if policy == 'contested':
            assert failed_queries and all(item['error'].startswith('KeyError:') and 'parse_units' in item['traceback'] for item in failed_queries)
            assert all(row['reason'] == 'untargeted_explorer' for row in rows[2:])
        else: assert not failed_queries
        for name in ('observations.jsonl','steps.jsonl'):
            assert (output/name).read_bytes().startswith((args.out/name).read_bytes())
        terminal = s.fit_train(output)
        assert terminal.cut == 22 and terminal.abstractor.H.step_kinds[6] == 'reload'
        assert FakeBrowser.instances[-1].closed
        print(json.dumps({'policy':policy,'charged':acquired['charged_attempts'],
                          'new_paired':acquired['paired_steps_recorded'],'combined_steps':len(combined.steps),
                          'new_episode':boundary.episode,'H_boundary_kind':terminal.abstractor.H.step_kinds[6],
                          'refit_training_steps':[row['training_steps'] for row in acquired['refits']],
                          'recognition_runtime_failures':len(failed_queries),'targeted_attempts':acquired['targeted_attempts']},sort_keys=True))
print('REAL collector -> source candidates -> fit, plus both REAL acquisition/refit pipelines: PASS')
PY
```

Observed exit 0:

```text
{"initial_charged": 7, "initial_failures": 2, "initial_paired": 6, "initial_unpaired": 1, "real_H_step_kinds": ["reload", "click", "click", "reset", "type", "click"], "real_fit_cut": 6, "source_candidates": 1}
{"H_boundary_kind": "reload", "charged": 17, "combined_steps": 22, "new_episode": 3, "new_paired": 16, "policy": "untargeted", "recognition_runtime_failures": 0, "refit_training_steps": [6, 20], "targeted_attempts": 0}
{"H_boundary_kind": "reload", "charged": 17, "combined_steps": 22, "new_episode": 3, "new_paired": 16, "policy": "contested", "recognition_runtime_failures": 22, "refit_training_steps": [6, 20], "targeted_attempts": 0}
REAL collector -> source candidates -> fit, plus both REAL acquisition/refit pipelines: PASS
```

## Reproduction B: retained frozen-learner graph failure and initial-only control

```bash
PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .venv/bin/python -B - <<'PY'
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Node, Observation
from semabi.compiler.browser import Primitive
from semabi.compiler.v4.pinned import PinnedReading
from scripts import transport_score as s

def page(value):
    return Observation([Node(0,-1,'group',''),Node(1,0,'button','Go'),Node(2,0,'textbox','Amount',value=value)])
with TemporaryDirectory(prefix='transport_review_v2_graph_') as tmp:
    root=Path(tmp); train=root/'initial'; log=EvidenceLog(train)
    a,b=page('1'),page('2')
    log.add_step(1,Primitive('reload'),True,None,a,a)
    log.add_step(1,Primitive('type',2,'2'),True,None,a,b)
    log.add_step(1,Primitive('click',1),True,None,b,b)
    prepared=s.prepare(train,root/'candidates')
    unseen=page('fresh value'); sig=unseen.structural_signature()
    for condition,reading in [('inferred',None),('pinned_initial_candidate',PinnedReading.from_json(prepared['candidates'][0]['reading']))]:
        model=s.fit_train(train,reading); A=model.abstractor
        same=A.G is A.H.G
        before={'A_has':sig in A.G.obs,'H_has':sig in A.H.G.obs}
        try:
            A.control_family(unseen)
            error=None
        except KeyError as exc:
            error=f'KeyError: {exc}'
        after={'A_has':sig in A.G.obs,'H_has':sig in A.H.G.obs}
        if condition=='inferred': assert not same and error and after=={'A_has':True,'H_has':False}
        else: assert same and error is None and after=={'A_has':True,'H_has':True}
        print(json.dumps({'condition':condition,'same_graph':same,'before':before,'after':after,'error':error},sort_keys=True))
PY
```

Observed exit 0:

```text
{"after": {"A_has": true, "H_has": false}, "before": {"A_has": false, "H_has": false}, "condition": "inferred", "error": "KeyError: '2fbb05330db3f0b0'", "same_graph": false}
{"after": {"A_has": true, "H_has": true}, "before": {"A_has": false, "H_has": false}, "condition": "pinned_initial_candidate", "error": null, "same_graph": true}
```

## Reproduction C: failures preserve opportunities, other channels and later successes

```bash
PYTHONHASHSEED=0 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .venv/bin/python -B - <<'PY'
import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from scripts import transport_collect as c, transport_score as s
from semabi.compiler.browser import ActionResult, Primitive
from semabi.compiler.evidence import EvidenceLog
from semabi.compiler.observation import Node, Observation
from semabi.compiler.v4 import consequence as csq, outcome as oc

def observation(value, reply):
    rows=[('group','',-1),('table','',0),('rowgroup','',1),('row','',2),('cell','Alpha',3),
          ('cell',value,3),('button','Flip',3),('row','',2),('cell','Beta',7),('cell','ready',7),
          ('button','Flip',7),('status',reply,0)]
    return Observation([Node(i,p,r,n) for i,(r,n,p) in enumerate(rows)])

def trace(path, missing=False):
    log=EvidenceLog(path); before=observation('cold','Waiting')
    for i in range(8):
        after=observation('warm' if i%2==0 else 'cold','Warmed Alpha' if i%2==0 else 'Cooled Alpha')
        log.add_step(1,Primitive('click',6,target_desc={'role':'button','name':'Flip'}),True,None,before,after)
        before=after
    if missing:
        log.add_step(1,Primitive('click',target_desc={'role':'button','name':'Missing'}),False,'unreachable',before,before)
    return log

class FakeBrowser:
    instances=[]
    def __init__(self,url,reset_url):
        self.url,self.reset_url,self.episode=url,reset_url,0
        self.n_settle_timeouts=self.n_navigation_waits=0
        self.calls=[]; self.closed=False
        self.__class__.instances.append(self)
    def act(self, primitive):
        self.calls.append(primitive.kind)
        if primitive.kind=='reset': self.episode+=1
        return ActionResult(True,None)
    def observe(self):
        assert self.calls and self.calls[0]=='reset'
        return Observation([Node(0,-1,'group',''),Node(1,0,'button','Go')],self.url)
    def close(self): self.closed=True

with TemporaryDirectory(prefix='transport_review_v2_failures_') as tmp:
    root=Path(tmp); train=root/'train'; trace(train); evaluation=trace(root/'eval',missing=True)
    model=s.fit_train(train)
    healthy,surface=s.score_model(model,evaluation)
    native=csq.score(replace(model,log=evaluation,cut=0))
    assert healthy['state']['rows'] == [s.jsonable(p) for p in native.predictions]
    assert healthy['state']['rows'], 'control must have actual state predictions'
    raw_score=csq.score; raw_admissible=oc.score_step_admissible; raw_query=s.query_record
    def state_failure(model, **kw):
        assert len(model.log.steps)==1
        if model.log.steps[0].step==1: raise ValueError('synthetic state failure at step 1')
        return raw_score(model,**kw)
    def channel_failure(model,step,**kw):
        if step.step==2 and kw['hypothesis']==oc.RULE: raise LookupError('synthetic RULE failure at step 2')
        return raw_admissible(model,step,**kw)
    def query_failure(model,step):
        if step.step==3: raise RuntimeError('synthetic query failure at step 3')
        return raw_query(model,step)
    with patch.object(csq,'score',state_failure), patch.object(oc,'score_step_admissible',channel_failure), patch.object(s,'query_record',query_failure):
        broken,broken_surface=s.score_model(s.fit_train(train),evaluation)
    assert broken['state']['summary']=={
        'evaluation_click_attempts':9,'scored_clicks':7,'runtime_failure_clicks':1,'unreachable_target_clicks':1,
        'prediction_counts':dict(__import__('collections').Counter(row['verdict'] for row in broken['state']['rows']))}
    assert broken['state']['rows']==[row for row in healthy['state']['rows'] if row['step']!=1]
    assert [row['step'] for row in broken['state']['per_step']]==[0,2,3,4,5,6,7]
    failure=next(row for row in broken['state']['failures'] if row['step']==1)
    assert failure['error']=='ValueError: synthetic state failure at step 1' and 'state_failure' in failure['traceback']
    for channel in ('decision_list',oc.RULE,oc.LIST):
        summary=broken['emission'][channel]['summary']
        assert summary['denominator_all_click_attempts']==9 and sum(summary['categories'].values())==9
        assert summary['unreachable_target']==1 and summary['runtime_failure']==(1 if channel==oc.RULE else 0)
        for row,reference in zip(broken['emission'][channel]['rows'],healthy['emission'][channel]['rows']):
            if row['step']==2 and channel==oc.RULE:
                assert row['verdict']==oc.NO_MODEL and row['unestablished_subtype']=='runtime_failure'
                assert row['error']=='LookupError: synthetic RULE failure at step 2' and 'channel_failure' in row['traceback']
                for key in ('before','after','action','episode','action_ok','action_error'): assert row[key]==reference[key]
            else: assert row==reference
    assert broken['queries'][3]['status']=='RUNTIME_FAILURE' and 'query_failure' in broken['queries'][3]['traceback']
    assert all(row==healthy['queries'][i] for i,row in enumerate(broken['queries']) if i!=3)
    assert '1|' not in ''.join(broken_surface['state']) and 2 not in broken_surface['emission']
    print(json.dumps({'fixed_click_denominator':9,'state_runtime_failures':1,'state_later_successes_retained':True,
                      'RULE_runtime_failures':1,'other_channels_unchanged':True,'query_runtime_failures':1,
                      'native_state_predictions':len(healthy['state']['rows'])},sort_keys=True))

    prepared=s.prepare(train,root/'candidates')
    real_fit=s.fit_train
    def failed_inferred(path,reading=None):
        if reading is None: raise RuntimeError('synthetic inferred fit failure')
        return real_fit(path,reading)
    with patch.object(s,'fit_train',failed_inferred):
        report=s.score(train,evaluation.dir,root/'candidates/candidates.json',root/'score.json')
    assert report['status']=='FINISHED' and report['pending_models']==[]
    assert set(report['models'])=={row['id'] for row in prepared['candidates']}|{'current_inferred'}
    failed=report['models']['current_inferred']
    assert failed['model'] is None and failed['fit_error']['error']=='RuntimeError: synthetic inferred fit failure'
    assert 'failed_inferred' in failed['fit_error']['traceback']
    assert failed['state']['rows']==[] and failed['state']['summary']['runtime_failure_clicks']==8
    for channel in ('decision_list',oc.RULE,oc.LIST):
        summary=failed['emission'][channel]['summary']
        assert summary['denominator_all_click_attempts']==9 and summary['runtime_failure']==8 and summary['unreachable_target']==1
        assert summary['categories']['unestablished']==9
    assert report['identity_frozen_candidates']['state_union_size']>0
    assert report['identity_including_current_inferred']['state_shared_size']==0
    assert 'current_inferred' in report['identity_including_current_inferred']['board']
    assert json.loads((root/'score.json').read_text())==s.jsonable(report)
    print(json.dumps({'fit_failure_all_opportunities_retained':9,'fit_failure_runtime_rows_per_channel':8,
                      'fit_failure_unreachable_rows_per_channel':1,'failed_model_in_scoreboard':True,
                      'shared_state_with_failed_model':0},sort_keys=True))

    for policy in ('untargeted','contested'):
        output=root/policy; output.mkdir()
        args=SimpleNamespace(initial=train,out=output,url='http://127.0.0.1:1234/public',
                             reset_url='http://127.0.0.1:1234/reset',seed=7,policy=policy,budget=17)
        with patch.object(c,'Browser',FakeBrowser),patch.object(c.csq,'fit',side_effect=RuntimeError('synthetic acquisition fit failure')):
            acquired=c.acquire(args)
        rows=[json.loads(line) for line in (output/'decisions.jsonl').read_text().splitlines()]
        assert acquired['charged_attempts']==17 and acquired['failed_attempts']==0 and acquired['fit_runtime_failures']==2
        assert acquired['paired_steps_recorded']==16 and acquired['unpaired_attempts']==1
        assert [(entry['after_charged_attempts'],entry['training_steps']) for entry in acquired['refits']]==[(0,8),(15,22)]
        assert all(entry['status']=='RUNTIME_FAILURE' and 'RuntimeError: synthetic acquisition fit failure' in entry['traceback'] for entry in acquired['refits'])
        assert json.loads((output/'refits.json').read_text())==acquired['refits']
        assert all(row['reason']=='untargeted_explorer' for row in rows[2:])
        if policy=='contested':
            assert all(item['status']=='FIT_RUNTIME_FAILURE' for row in rows[2:] for item in row['candidates'])
        assert FakeBrowser.instances[-1].closed and len(FakeBrowser.instances[-1].calls)==17
        print(json.dumps({'policy':policy,'charged_despite_fit_failure':17,'learner_fit_failures':2,
                          'world_failed_attempts':0,'fallback_unchanged':True},sort_keys=True))
print('Learner errors remain unestablished; full opportunities, traces and later successes preserved: PASS')
PY
```

Observed exit 0:

```text
{"RULE_runtime_failures": 1, "fixed_click_denominator": 9, "native_state_predictions": 16, "other_channels_unchanged": true, "query_runtime_failures": 1, "state_later_successes_retained": true, "state_runtime_failures": 1}
fit and score candidate_00
fit and score current_inferred
{"failed_model_in_scoreboard": true, "fit_failure_all_opportunities_retained": 9, "fit_failure_runtime_rows_per_channel": 8, "fit_failure_unreachable_rows_per_channel": 1, "shared_state_with_failed_model": 0}
{"charged_despite_fit_failure": 17, "fallback_unchanged": true, "learner_fit_failures": 2, "policy": "untargeted", "world_failed_attempts": 0}
{"charged_despite_fit_failure": 17, "fallback_unchanged": true, "learner_fit_failures": 2, "policy": "contested", "world_failed_attempts": 0}
Learner errors remain unestablished; full opportunities, traces and later successes preserved: PASS
```

## Reproduction D: unchanged complete-support reconstruction

The exact Reproduction D command in `instrument_review_v1.md` was rerun against
the V2 scorer with the same deterministic environment. It reconstructs the
complete available outcome evidence from serialized masks and compares all
RULE/LIST admissible outcome sets to the saved queries. Exit 0:

```json
{"all_click_attempts": 9, "empty_shared_size": 0, "empty_union_size": 2, "support_reconstructions": 16, "unreachable_target": 1}
```
