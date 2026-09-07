"""Independent custody/control checks using complete invented native records."""
from collections import Counter
from pathlib import Path
from types import ModuleType, SimpleNamespace
import argparse
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io as stdio
import json
import os
import socket
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
J1 = HERE.parent
IO_SHA = '2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327'
ACTOR_SHA = '26a91ec96deb9c381dcc28c4e0277c6a349c0d940f7693e7bb9e6d3e55b267b7'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def require(condition, detail):
    if not condition: raise AssertionError(detail)
def imported(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); sys.modules[name] = value
    spec.loader.exec_module(value); return value

def functions(path, names, namespace):
    tree = ast.parse(path.read_text())
    selected = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names]
    require({node.name for node in selected} == set(names), 'Native function AST inventory differs')
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)

def plain(path): return json.loads(path.read_text())
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, sort_keys=True) + '\n')


def invented_script():
    scope = {'role': 'group', 'name': 'Panel', 'exact': True}
    return {'fixtures': {'invented': {'cases': [
        {'case': 'invented-first', 'family': 'invented-pair', 'target_action_index': 1,
         'script': [{'kind': 'snapshot'}, {'kind': 'select', 'role': 'combobox', 'name': 'Choice', 'value': 'Beta', 'exact': True, 'scope': scope},
                    {'kind': 'click', 'role': 'button', 'name': 'Apply', 'exact': True, 'scope': scope}]},
        {'case': 'invented-second', 'family': 'invented-failure', 'target_action_index': 0, 'reset_url': '/invented-second-reset',
         'script': [{'kind': 'click', 'role': 'button', 'name': 'Missing', 'exact': True, 'scope': scope},
                    {'kind': 'type', 'role': 'textbox', 'name': 'Entry', 'value': True, 'exact': True, 'scope': scope}, {'kind': 'snapshot'}]},
    ]}}}


def make_baseline(root, actor, scoped, native):
    root.mkdir(); directory = root / 'run'; directory.mkdir(); predictor = root / 'predictor'; predictor.mkdir()
    script = invented_script(); script_path = root / 'invented_script.json'; write(script_path, script)
    phase = {'fixture': 'invented', 'url': 'http://127.0.0.1/invented', 'reset_url': '/invented-reset', 'seed': 7}
    events, browsers = [], []
    raw_page = {'url': phase['url'], 'nodes': [
        {'i': 0, 'parent': -1, 'role': 'group', 'name': 'Panel', 'bbox': [0, 0, 100, 100]},
        {'i': 1, 'parent': 0, 'role': 'button', 'name': 'Apply', 'bbox': [1, 1, 10, 10]},
        {'i': 2, 'parent': 0, 'role': 'textbox', 'name': 'Entry', 'value': '', 'bbox': [1, 15, 10, 10]},
        {'i': 3, 'parent': 0, 'role': 'combobox', 'name': 'Choice', 'value': 'Alpha', 'options': ['Alpha', 'Beta'], 'bbox': [1, 30, 10, 10]}]}
    class Browser:
        def __init__(self, url, reset_url):
            self.url, self.reset_url = url, reset_url; self.current = copy.deepcopy(raw_page); self.episode = 0
            self.n_settle_timeouts = self.n_navigation_waits = 0; self.closed = False; self.observations = 0
            self._last_obs = native.Observation.from_json(self.current); browsers.append(self)
        def observe(self):
            self.observations += 1; raw = copy.deepcopy(self.current)
            raw['url'] = self.url + '?invented_view=' + str(self.observations)
            raw['nodes'][1]['bbox'][0] = self.observations
            self._last_obs = native.Observation.from_json(raw); return self._last_obs
        def act(self, primitive):
            events.append({'kind': primitive.kind, 'episode_before': self.episode})
            if primitive.target is not None:
                primitive.target_desc = actor.io.public_descriptor(self._last_obs.nodes[primitive.target].to_json())
            if primitive.kind == 'reset':
                self.episode += 1; self.current = copy.deepcopy(raw_page)
            elif primitive.kind == 'select': self.current['nodes'][primitive.target]['value'] = primitive.text
            elif primitive.kind == 'type' and type(primitive.text) is not str:
                return native.ActionResult(False, 'invented native scalar rejection')
            return native.ActionResult(True, None)
        def close(self): self.closed = True
    base = ModuleType('_invented_retained_custody_collector')
    base.__dict__.update(json=json, Path=Path, Counter=Counter, hashlib=hashlib,
                         Primitive=native.Primitive, Browser=Browser, EvidenceLog=native.EvidenceLog)
    functions(ROOT / 'scripts/transport_collect.py', {'Recorder', 'resolve', 'collect_script', 'digest'}, base.__dict__)
    base.resolve = scoped.scoped_resolver(base.resolve, native.Primitive)
    provenance = {'pid': 731, 'fit_id': 'same-invented-resident-fit', 'source_head': 'invented-source-head', 'training': 'invented-raw-training'}
    ledger = actor.io.Ledger(predictor / 'forecasts.jsonl')
    class Client:
        ledger_path = ledger.path
        def request(self, request):
            ledger.validate_next(request)
            status = ('UNREACHABLE' if request['primitive'] is None else 'NO_PRESTATE' if request['observation'] is None
                      else 'NON_CLICK' if request['primitive']['kind'] != 'click' else 'NO_MODEL')
            response = {'schema': 'semabi.j1.forecast.v1', 'instrument_status': 'COMPLETE', 'status': status}
            ack = ledger.append(request, response, provenance)
            return ack, actor.io.verify_receipt(ledger.path, ack, request)
    state = actor.ActorState(Client(), provenance); original = base.Recorder; state.instrument(base)
    try:
        summary = base.collect_script(SimpleNamespace(script=script_path, fixture=phase['fixture'], url=phase['url'],
                   reset_url=phase['reset_url'], seed=phase['seed'], out=directory))
    finally:
        state.close(); ledger.close()
    require(base.Recorder is original and all(browser.closed for browser in browsers), 'Baseline construction leaked resources')
    require(summary['charged_attempts'] == 7 and summary['failed_attempts'] == 2 and summary['paired_steps_recorded'] == 6
            and summary['snapshot_calls'] == 8 and summary['complete'] is False, 'Independent native script accounting differs')
    require(all(intent['state'] == 'MATCHED' for intent in state.recorders[0].intents), 'Baseline actor is incomplete')
    ready = root / 'invented_ready.json'; write(ready, {'scope': 'Opaque invented ready binding for custody; real ready gates tested separately'})
    ready_ref = {'path': str(ready), 'sha256': sha(ready)}
    expected_actor = {'manifest_sha256': 'a' * 64, 'source_head': provenance['source_head']}
    expected_collector = {'manifest_sha256': 'b' * 64, 'verification_files': {'public.py': 'c' * 64}}
    run = {'status': 'FINISHED', **summary, 'start': {'git_head': provenance['source_head']},
           'end': {'git_head': provenance['source_head']}, 'freeze_sha256': expected_collector['manifest_sha256'],
           'raw_hashes': {name: sha(directory / name) for name in ('observations.jsonl', 'steps.jsonl', 'decisions.jsonl')}}
    completion = {'status': 'PASS', 'collection_error': None, 'verification_error': None}
    actor_record = {'schema': 'semabi.j1.actor_verification.v1', **completion, 'before': expected_actor, 'after': expected_actor,
                    'ready': ready_ref, 'provenance': provenance, 'predictor_pid': provenance['pid'], 'cleanup_errors': [], 'accounting': state.accounting()}
    collector_record = {'schema': 'semabi.j1.collector_instrument_verification.v1', **completion,
                        'before': expected_collector, 'after': expected_collector}
    for name, value in [('run.json', run), ('actor_verification.json', actor_record), ('collector_verification.json', collector_record)]: write(directory / name, value)
    names = ['observations.jsonl', 'steps.jsonl', 'decisions.jsonl', 'forecast_receipts.jsonl', 'forecast_reconciliation.jsonl',
             'run.json', 'actor_verification.json', 'collector_verification.json']
    data = {name: [json.loads(line) for line in (directory / name).read_text().splitlines()] if name.endswith('.jsonl') else plain(directory / name) for name in names}
    data['ledger'] = [json.loads(line) for line in ledger.path.read_text().splitlines()]
    return SimpleNamespace(root=root, data=data, script=script, phase=phase, provenance=provenance,
                           expected_actor=expected_actor, expected_collector=expected_collector, ready_reference=ready_ref,
                           ready=plain(ready), events=events)


class Capsule:
    def __init__(self, source, root, custody):
        self.root, self.custody = root, custody; self.directory = root / 'run'; self.ledger_path = root / 'predictor/forecasts.jsonl'
        self.data = copy.deepcopy(source.data)
        def relocate(value):
            if type(value) is str: return str(root) + value[len(str(source.root)):] if value.startswith(str(source.root)) else value
            if type(value) is list: return [relocate(item) for item in value]
            if type(value) is dict: return {key: relocate(item) for key, item in value.items()}
            return value
        self.data = relocate(self.data); self.ready_reference = relocate(source.ready_reference)
        self.provenance = copy.deepcopy(source.provenance); self.expected_actor = copy.deepcopy(source.expected_actor)
        self.expected_collector = copy.deepcopy(source.expected_collector); self.script = copy.deepcopy(source.script); self.phase = dict(source.phase)
        self.directory.mkdir(parents=True); self.ledger_path.parent.mkdir(); write(root / 'invented_ready.json', source.ready)
        self.post_refresh = None; self.phase_offset = 0
    def dump(self, *, resign=False):
        io = self.custody.io
        ledger_raw = b''.join(io.json_bytes(row) for row in self.data['ledger']); self.ledger_path.write_bytes(ledger_raw)
        if resign:
            offset = 0
            for index, record in enumerate(self.data['ledger']):
                raw = io.json_bytes(record)
                ack = {'schema': io.ACK_SCHEMA, 'request_id': record['request']['request_id'], 'receipt_index': index + 1,
                       'offset': offset, 'length': len(raw), 'record_sha256': io.digest(raw), 'instrument_status': record['response']['instrument_status']}
                offset += len(raw)
                target = index - self.phase_offset
                if 0 <= target < len(self.data['forecast_receipts.jsonl']):
                    self.data['forecast_receipts.jsonl'][target]['acknowledgement'] = copy.deepcopy(ack)
                    self.data['decisions.jsonl'][target]['forecast_receipt'] = copy.deepcopy(self.data['forecast_receipts.jsonl'][target])
                    self.data['actor_verification.json']['accounting'][0]['intents'][target]['acknowledgement'] = copy.deepcopy(ack)
                    self.data['actor_verification.json']['accounting'][0]['intents'][target]['receipt_index'] = index + 1
                    self.data['forecast_reconciliation.jsonl'][target]['receipt_index'] = index + 1
        for name, value in self.data.items():
            if name.endswith('.jsonl'): (self.directory / name).write_bytes(b''.join(io.json_bytes(row) for row in value))
        self.data['run.json']['raw_hashes'] = {name: sha(self.directory / name) for name in ('observations.jsonl', 'steps.jsonl', 'decisions.jsonl')}
        accounting = self.data['actor_verification.json']['accounting'][0]
        for label, name in [('receipts', 'forecast_receipts.jsonl'), ('reconciliations', 'forecast_reconciliation.jsonl')]:
            accounting[label] = {'path': str(self.directory / name), 'sha256': sha(self.directory / name), 'error': None}
        if self.post_refresh is not None: self.post_refresh(self)
        for name, value in self.data.items():
            if name.endswith('.json'): write(self.directory / name, value)
    def reconcile(self, native, validate_step):
        raw = self.custody.raw_history(self.directory, validate_step, native.signature)
        ledger = self.custody.read_ledger(self.ledger_path, self.provenance)[self.phase_offset:]
        context = SimpleNamespace(**vars(native), ledger_path=self.ledger_path)
        planned = self.custody.allocation(self.script, self.phase)
        return self.custody.reconcile_phase(self.directory, planned, ledger, self.provenance, native=context, raw=raw,
                  expected_actor=self.expected_actor, expected_collector=self.expected_collector,
                  ready_reference=self.ready_reference, source_head=self.provenance['source_head'])


def checkpoint_fixture(custody, model, training, path, *, index=0, learned=None):
    checks = {name: True for name in ['complete_projection', 'no_prior_checkpoint_failure', 'learned_commitment_unchanged',
              'old_memo_entries_unchanged_since_startup', 'old_memo_entries_unchanged_since_previous_checkpoint',
              'new_memo_entries_belong_to_interpreted_observations']}
    for name in model.GRAPH_LOOKUPS:
        checks.update({f'old_graph_{name}_entries_unchanged_since_startup': True,
                       f'old_graph_{name}_entries_unchanged_since_previous_checkpoint': True,
                       f'new_graph_{name}_entries_belong_to_interpreted_observations': True})
    ownership = dict.fromkeys(['same_pid', 'fit_inducer', 'fit_abstractor', 'fit_log', 'fit_evidence', 'fit_operators',
               'inducer_abstractor', 'inducer_evidence', 'abstractor_hypotheses', 'shared_graph', 'abstractor_vocabulary',
               'parser_is_none', 'graph_frozen', 'emission_frozen'], True)
    object_names = ('fit', 'inducer', 'abstractor', 'hypotheses', 'graph', 'vocabulary', 'log', 'evidence')
    common = {'schema': 'semabi.transport.j1_fit_projection.v1', 'status': 'COMPLETE', 'incomplete_reasons': [],
              'raw_mapping': {'raw_records': copy.deepcopy(training), 'raw_records_sha256': custody.io.digest(custody.io.json_bytes(training)[:-1])},
              'primary_step_associations': [], 'fit': {'cut': len(training['steps']), 'reading': 'invented-normal-reading'},
              'permitted_evidence_step_ids': list(range(len(training['steps']))),
              'abstractor': {'_cache': {}, '_assigned': {}, 'learned_value': 'stable'},
              'hypotheses': {'_page_instances': {}, 'learned_value': 'stable'}}
    inventory = {'fit': sorted(model.FIT_FIELDS),
                 'inducer': sorted(set(model.trace.INDUCER_FIELDS) | {'A', 'log', 'transitions', 'noops', 'operators'}),
                 'abstractor': sorted(set(model.trace.ABSTRACTOR_FIELDS) | {'G', 'H', 'parser', 'emissions'}),
                 'hypotheses': sorted(set(model.trace.HYPOTHESIS_FIELDS) | {'G', 'memo'}),
                 'graph': sorted(set(model.GRAPH_FROZEN + model.GRAPH_LOOKUPS + model.GRAPH_MEMOS)),
                 'vocabulary': ['frozen', 'values'],
                 'log': sorted(['steps', 'observations', 'typed_tokens', 'dir', 'obs_path', 'steps_path']),
                 'evidence': sorted(['steps', 'observations', 'typed_tokens', 'dir', 'obs_path', 'steps_path'])}
    projection = {'schema': 'semabi.j1.live_projection.v1', 'status': 'COMPLETE', 'incomplete_reasons': [],
                  'common': common, 'ownership': ownership,
                  'identity_attestation': {'pid': 731, 'objects': {name: 1000 + i for i, name in enumerate(object_names)},
                                          'scope': 'Strong references and identity checks within this resident process'},
                  'stored_key_inventory': inventory,
                  'snapshots': {}, 'graph_frozen': {'learning': False}, 'graph_policy': {'invented': 'stable'},
                  'execution_handles': {'abstractor': {'parser': None, 'cat': 'absent'}}}
    learned = model.learned_view(projection) if learned is None else copy.deepcopy(learned)
    saved = {'schema': 'semabi.j1.live_checkpoint.v1', 'checkpoint_index': index, 'instrument_status': 'COMPLETE',
             'checks': checks, 'changes': {}, 'projection': projection, 'learned_commitment': learned,
             'learned_commitment_sha256': custody.io.digest(custody.io.json_bytes(learned)[:-1])}
    write(path, saved)
    receipt = {'schema': 'semabi.j1.checkpoint_receipt.v1', 'instrument_status': 'COMPLETE', 'checkpoint_index': index,
               'path': str(path), 'sha256': sha(path), 'learned_commitment_sha256': saved['learned_commitment_sha256']}
    return saved, receipt


def control_case(control, boundary, root, *, operation='checkpoint', behavior=None):
    root.mkdir(); actor, io = control.actor, control.io
    previous = actor.ROOT, actor.HERE, actor.subprocess, io.Client, list(sys.argv)
    connection = ledger = None
    try:
        item = boundary.tree(actor, root / 'source')
        directory = root / 'predictor'; directory.mkdir()
        ledger = io.Ledger(directory / 'forecasts.jsonl')
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); socket_path = root / 'owned.sock'; connection.bind(str(socket_path))
        provenance = {'source_head': 'invented-head', 'runtime_freeze_sha256': sha(item.predictor), 'pid': 731, 'fit': 'same-invented-fit'}
        ready = {'schema': 'semabi.j1.predictor_ready.v1', 'status': 'READY', 'pid': 731, 'ledger_path': str(ledger.path),
                 'socket_path': str(socket_path), 'provenance': provenance}
        write(directory / 'ready.json', ready)
        output = root / 'control.json'; calls = []; original = b'immutable existing control identity\n'
        if behavior == 'exists': output.write_bytes(original)
        if behavior == 'source_before': (item.root / 'scripts/transport_collect.py').write_text('invented source alteration')
        if behavior == 'ready_before': ready['pid'] = True; write(directory / 'ready.json', ready)
        class Client:
            def __init__(self, socket_name, ledger_name):
                require(socket_name == str(socket_path) and ledger_name == str(ledger.path), 'Control client routing differs')
            def request(self, request):
                ledger.validate_next(request); calls.append(copy.deepcopy(request))
                if behavior == 'request_error': raise io.ProtocolError('invented request error')
                response = {'schema': 'semabi.j1.checkpoint_receipt.v1', 'instrument_status': 'INCOMPLETE' if behavior == 'incomplete' else 'COMPLETE',
                            'checkpoint_index': 1, 'path': str(root / 'invented-checkpoint.json'), 'sha256': 'a' * 64, 'learned_commitment_sha256': 'b' * 64}
                used_provenance = {'wrong': 'different-fit'} if behavior == 'wrong_provenance' else provenance
                ack = ledger.append(request, response, used_provenance)
                if behavior == 'lost_ack': raise io.ProtocolError('invented lost acknowledgement')
                if behavior == 'source_after': (item.root / 'scripts/transport_collect.py').write_text('invented later source alteration')
                if behavior == 'ready_after': ready['extra'] = 'changed after receipt'; write(directory / 'ready.json', ready)
                return ack, io.verify_receipt(ledger.path, ack, request)
        io.Client = Client
        sys.argv = [str(J1 / 'control.py'), '--actor-freeze', str(item.path), '--collector-freeze', str(item.collection),
                    '--predictor-dir', str(directory), '--operation', operation, '--out', str(output)]
        error = None; stdout = stdio.StringIO()
        try:
            with contextlib.redirect_stdout(stdout): control.main()
        except Exception as caught: error = {'type': type(caught).__name__, 'detail': str(caught)}
        result = {'error': error, 'request_count': len(calls), 'ledger_records': ledger.index, 'stdout': stdout.getvalue()}
        if behavior in ('exists', 'source_before', 'ready_before'):
            require(error is not None and not calls, 'Pre-request control gate failed')
            require(output.read_bytes() == original if behavior == 'exists' else not output.exists(), 'Early control gate altered an output')
        else:
            saved = plain(output); result['saved'] = saved
            require(saved['request']['op'] == operation and set(saved['request']) == {'schema', 'op', 'request_id'}, 'Control semantic payload differs')
            require(len(calls) == 1, 'Control request retried or disappeared')
            if behavior is None:
                require(error is None and saved['status'] == 'PASS' and ledger.index == 1, 'Valid control did not pass')
                require(saved['record'] == io.verify_receipt(ledger.path, saved['acknowledgement'], saved['request']), 'Saved control receipt bytes differ')
            else:
                require(error is not None and saved['status'] == 'ERROR', 'Control failure was not preserved as ERROR')
                require(ledger.index == (0 if behavior == 'request_error' else 1), 'Lost/failed control ledger accounting differs')
        return result
    finally:
        actor.ROOT, actor.HERE, actor.subprocess, io.Client, sys.argv = previous
        if connection is not None: connection.close()
        if ledger is not None: ledger.close()


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--custody-sha', required=True); parser.add_argument('--control-sha', required=True)
    parser.add_argument('--output', required=True, type=Path); args = parser.parse_args()
    require(not args.output.exists(), 'Exclusive output already exists')
    require(sha(J1 / 'custody.py') == args.custody_sha and sha(J1 / 'control.py') == args.control_sha
            and sha(J1 / 'live_io.py') == IO_SHA and sha(J1 / 'act.py') == ACTOR_SHA, 'Held source changed')
    paths = [J1 / name for name in ['custody.py', 'control.py', 'act.py', 'collect.py', 'live_io.py', 'predictor.py', 'live_model.py', 'trace.py', 'live_contract_v1.md', 'protocol_v1.md']]
    paths += [Path(__file__), HERE / 'actor_boundary_checks_v1.py', ROOT / 'scripts/transport_collect.py']
    paths += sorted((ROOT / 'semabi/compiler').rglob('*.py')) + [ROOT / 'semabi/__init__.py', ROOT / 'semabi/relmodel.py']
    sources = {str(path.relative_to(ROOT)): sha(path) for path in paths}
    custody = imported('_reviewed_j1_custody', J1 / 'custody.py'); control = imported('_reviewed_j1_control', J1 / 'control.py')
    actor = imported('_reviewed_actor_for_custody', J1 / 'act.py'); scoped = imported('_reviewed_scoped_for_custody', J1 / 'collect.py')
    model = imported('_reviewed_model_custody_helpers', J1 / 'live_model.py')
    boundary = imported('_reviewed_boundary_source_tree_helper', HERE / 'actor_boundary_checks_v1.py')
    sys.path.insert(0, str(ROOT))
    from semabi.compiler.observation import Observation
    from semabi.compiler.browser import Primitive, ActionResult
    from semabi.compiler.evidence import EvidenceLog
    native = SimpleNamespace(Observation=Observation, Primitive=Primitive, ActionResult=ActionResult, EvidenceLog=EvidenceLog)
    ns = {'io': custody.io}; functions(J1 / 'predictor.py', {'public_scalar', 'validate_training_step'}, ns)
    validate_step = ns['validate_training_step']
    resolver_ns = {'Primitive': Primitive}; functions(ROOT / 'scripts/transport_collect.py', {'resolve'}, resolver_ns)
    native.resolve = scoped.scoped_resolver(resolver_ns['resolve'], Primitive)
    native.signature = lambda public: Observation.from_json(public).structural_signature()
    rows = []
    def check(name, function, *, reject=False):
        try:
            result = function(); passed = not reject
            rows.append({'name': name, 'expected': 'reject' if reject else 'accept', 'status': 'PASS' if passed else 'FAIL', 'result': result})
        except Exception as error:
            rows.append({'name': name, 'expected': 'reject' if reject else 'accept', 'status': 'PASS' if reject else 'FAIL',
                         'exception': type(error).__name__, 'detail': str(error)})
    with tempfile.TemporaryDirectory(prefix='j1cc_') as temporary:
        root = Path(temporary); baseline = make_baseline(root / 'baseline', actor, scoped, native)
        def phase_case(name, mutation=None, *, resign=False, after_dump=None):
            capsule = Capsule(baseline, root / ('p_' + name), custody)
            if mutation is not None: mutation(capsule)
            capsule.dump(resign=resign)
            if after_dump is not None: after_dump(capsule)
            value = capsule.reconcile(native, validate_step)
            return {'accounting': value['accounting'], 'raw_representative_equalities': [row['prestate_raw_equals_native_representative'] for row in value['rows']]}
        def valid_phase():
            value = phase_case('valid')
            require(value['accounting']['charged_attempts'] == 7 and value['accounting']['failed_attempts'] == 2
                    and value['accounting']['paired_steps_recorded'] == 6 and value['accounting']['designated_targets'] == 2
                    and value['accounting']['unresolved_attempts'] == 1, 'Valid failed/unresolved fixed accounting differs')
            require(False in value['raw_representative_equalities'], 'Native geometry/URL deduplication was concealed')
            return value
        check('complete_native_actor_failed_unresolved_phase', valid_phase)
        def global_receipt_indices():
            capsule = Capsule(baseline, root / 'p_global_indices', custody)
            record = {'schema': custody.io.RECORD_SCHEMA, 'receipt_index': 1, 'recorded_utc': custody.io.now(),
                      'request': custody.io.control_request('checkpoint'),
                      'response': {'schema': 'semabi.j1.checkpoint_receipt.v1', 'instrument_status': 'COMPLETE'},
                      'provenance': capsule.provenance}
            capsule.data['ledger'].insert(0, record); capsule.phase_offset = 1
            for index, value in enumerate(capsule.data['ledger'], 1): value['receipt_index'] = index
            capsule.dump(resign=True); result = capsule.reconcile(native, validate_step)
            require([row['receipt_index'] for row in result['rows']] == list(range(2, 9)), 'Global receipt indices were confused with local charged indices')
            return {'receipt_indices': list(range(2, 9)), 'charged_attempts': result['accounting']['charged_attempts'], 'preceding_control_left_to_global_caller': True}
        check('global_ledger_indices_distinct_from_phase_charges', global_receipt_indices)
        def full_allocation():
            script = {'fixtures': {'invented': {'cases': [{'case': 'invented-' + str(i), 'family': 'invented', 'target_action_index': 11,
                      'script': [{'kind': 'click', 'role': 'button', 'name': 'Apply'} for _ in range(12)]} for i in range(24)]}}}
            script['fixtures']['invented']['cases'][0]['script'].insert(0, {'kind': 'snapshot'})
            result = custody.allocation(script, baseline.phase)
            require(len(result['rows']) == 313 and result['targets'] == result['case_count'] == 24 and result['snapshot_requests'] == 1, 'Full fixed allocation denominator differs')
            require([row['charged_attempt'] for row in result['rows'] if row['target']] == [14 + 13 * i for i in range(24)], 'Designated target charged positions differ')
            require([row['charged_attempt'] for row in result['rows'] if row['action']['kind'] == 'reload'] == [2], 'Observed reload boundary differs')
            require(sum(row['action']['kind'] == 'reset' for row in result['rows']) == 24, 'A reset charge disappeared')
            return {'charged_attempts': 313, 'targets': 24, 'snapshot_requests': 1, 'target_charges': [14 + 13 * i for i in range(24)]}
        check('full_24_target_313_charged_allocation', full_allocation)
        for name, mutation in [('duplicate_case', lambda s: s['fixtures']['invented']['cases'][1].update(case='invented-first')),
                              ('boolean_target', lambda s: s['fixtures']['invented']['cases'][0].update(target_action_index=True)),
                              ('negative_target', lambda s: s['fixtures']['invented']['cases'][0].update(target_action_index=-1)),
                              ('absent_target', lambda s: s['fixtures']['invented']['cases'][0].update(target_action_index=8))]:
            def allocation_bad(mutation=mutation):
                script = copy.deepcopy(baseline.script); mutation(script); return custody.allocation(script, baseline.phase)
            check('allocation_' + name, allocation_bad, reject=True)
        def set_receipt(c, key, value):
            c.data['forecast_receipts.jsonl'][0][key] = value
            c.data['decisions.jsonl'][0]['forecast_receipt'] = copy.deepcopy(c.data['forecast_receipts.jsonl'][0])
        def sidecar_hash(c):
            c.post_refresh = lambda value: value.data['actor_verification.json']['accounting'][0]['receipts'].update(sha256='0' * 64)
        def raw_hash(c): c.post_refresh = lambda value: value.data['run.json']['raw_hashes'].update({'steps.jsonl': '0' * 64})
        def request_control(c): c.data['ledger'][1]['request'] = custody.io.control_request('checkpoint')
        def wrong_public_key(c): c.data['ledger'][2]['request']['observation']['nodes'][1]['name'] = 'Altered visible key'
        def wrong_descriptor(c): c.data['ledger'][3]['request']['primitive']['target_desc']['name'] = 'Wrong public descriptor'
        def wrong_resolved_action(c): c.data['ledger'][3]['request']['primitive']['text'] = 'Changed action argument'
        def raw_geometry(c):
            for row in c.data['observations.jsonl']:
                row['obs']['url'] += '/other-representative'
                row['obs']['nodes'][0]['bbox'][0] = 73
        phase_specs = [
            ('missing_decision', lambda c: c.data['decisions.jsonl'].pop(), False),
            ('extra_decision', lambda c: c.data['decisions.jsonl'].append(copy.deepcopy(c.data['decisions.jsonl'][-1])), False),
            ('duplicate_decision', lambda c: c.data['decisions.jsonl'].__setitem__(2, copy.deepcopy(c.data['decisions.jsonl'][1])), False),
            ('missing_receipt', lambda c: c.data['forecast_receipts.jsonl'].pop(), False),
            ('extra_receipt', lambda c: c.data['forecast_receipts.jsonl'].append(copy.deepcopy(c.data['forecast_receipts.jsonl'][-1])), False),
            ('missing_reconciliation', lambda c: c.data['forecast_reconciliation.jsonl'].pop(), False),
            ('missing_step', lambda c: c.data['steps.jsonl'].pop(), False),
            ('extra_step', lambda c: c.data['steps.jsonl'].append({**copy.deepcopy(c.data['steps.jsonl'][-1]), 'step': 6}), False),
            ('duplicate_step', lambda c: c.data['steps.jsonl'].__setitem__(1, copy.deepcopy(c.data['steps.jsonl'][0])), False),
            ('duplicate_observation', lambda c: c.data['observations.jsonl'].append(copy.deepcopy(c.data['observations.jsonl'][0])), False),
            ('missing_ledger_forecast', lambda c: c.data['ledger'].pop(), False),
            ('extra_ledger_forecast', lambda c: c.data['ledger'].append(copy.deepcopy(c.data['ledger'][-1])), False),
            ('duplicate_ledger_id', lambda c: c.data['ledger'][1]['request'].update(request_id=c.data['ledger'][0]['request']['request_id']), True),
            ('ledger_bool_index', lambda c: c.data['ledger'][0].update(receipt_index=True), False),
            ('ledger_float_index', lambda c: c.data['ledger'][0].update(receipt_index=1.0), False),
            ('ledger_wrong_provenance', lambda c: c.data['ledger'][0]['provenance'].update(fit_id='another-fit'), True),
            ('ledger_incomplete', lambda c: c.data['ledger'][0]['response'].update(instrument_status='INCOMPLETE'), True),
            ('ledger_control_in_action_position', request_control, True),
            ('decision_bool_charge', lambda c: c.data['decisions.jsonl'][0].update(charged_attempt=True), False),
            ('decision_float_charge', lambda c: c.data['decisions.jsonl'][0].update(charged_attempt=1.0), False),
            ('decision_bool_episode', lambda c: c.data['decisions.jsonl'][0].update(episode=True), False),
            ('decision_float_step', lambda c: c.data['decisions.jsonl'][1].update(step=0.0), False),
            ('decision_bool_ok', lambda c: c.data['decisions.jsonl'][0].update(ok=1), False),
            ('raw_step_bool_index', lambda c: c.data['steps.jsonl'][0].update(step=False), False),
            ('raw_step_float_episode', lambda c: c.data['steps.jsonl'][0].update(episode=1.0), False),
            ('raw_step_forecast_metadata', lambda c: c.data['steps.jsonl'][0].update(forecast_receipt={'bad': True}), False),
            ('unknown_native_decision_key', lambda c: c.data['decisions.jsonl'][1].update(unrequested='extra'), False),
            ('wrong_case_metadata', lambda c: c.data['decisions.jsonl'][3].update(case='another-case'), False),
            ('wrong_target_metadata', lambda c: c.data['decisions.jsonl'][3].update(task_target=False), False),
            ('changed_fixed_scope', lambda c: c.script['fixtures']['invented']['cases'][0]['script'][2]['scope'].update(name='Other panel'), False),
            ('hidden_public_key_drift', wrong_public_key, True),
            ('conflicting_resolved_descriptor', wrong_descriptor, True),
            ('changed_forecast_argument', wrong_resolved_action, True),
            ('receipt_bool_charge', lambda c: set_receipt(c, 'charged_attempt', True), False),
            ('receipt_wrong_ledger', lambda c: set_receipt(c, 'ledger_path', '/tmp/another-ledger'), False),
            ('receipt_wrong_ack_offset', lambda c: c.data['forecast_receipts.jsonl'][0]['acknowledgement'].update(offset=1), False),
            ('intent_missing', lambda c: c.data['actor_verification.json']['accounting'][0]['intents'].pop(), False),
            ('intent_unmatched', lambda c: c.data['actor_verification.json']['accounting'][0]['intents'][0].update(state='ACKNOWLEDGED'), False),
            ('intent_bool_receipt_index', lambda c: c.data['actor_verification.json']['accounting'][0]['intents'][0].update(receipt_index=True), False),
            ('intent_float_episode', lambda c: c.data['actor_verification.json']['accounting'][0]['intents'][0].update(episode=1.0), False),
            ('intent_wrong_expected_action', lambda c: c.data['actor_verification.json']['accounting'][0]['intents'][1]['expected_action'].update(text='wrong'), False),
            ('reconciliation_bool_charge', lambda c: c.data['forecast_reconciliation.jsonl'][0].update(charged_attempt=True), False),
            ('reconciliation_float_receipt_index', lambda c: c.data['forecast_reconciliation.jsonl'][0].update(receipt_index=1.0), False),
            ('reconciliation_wrong_outcome', lambda c: c.data['forecast_reconciliation.jsonl'][0].update(ok=False), False),
            ('missing_poststate', lambda c: c.data['decisions.jsonl'][1].update(after='missing'), False),
            ('unpaired_reset_as_step', lambda c: c.data['decisions.jsonl'][0].update(step=0), False),
            ('unresolved_failure_erased', lambda c: c.data['decisions.jsonl'][5].update(ok=True, error=None), False),
            ('unresolved_diagnostic_changed', lambda c: c.data['decisions.jsonl'][5].update(error='changed unresolved error'), False),
            ('native_not_finished', lambda c: c.data['run.json'].update(status='RUNNING'), False),
            ('native_wrong_head', lambda c: c.data['run.json']['end'].update(git_head='another-head'), False),
            ('native_wrong_freeze', lambda c: c.data['run.json'].update(freeze_sha256='0' * 64), False),
            ('native_wrong_complete', lambda c: c.data['run.json'].update(complete=True), False),
            ('native_bool_count', lambda c: c.data['run.json'].update(unpaired_attempts=True), False),
            ('native_wrong_snapshot_count', lambda c: c.data['run.json'].update(snapshot_calls=7), False),
            ('native_wrong_raw_hash', raw_hash, False),
            ('collector_not_pass', lambda c: c.data['collector_verification.json'].update(status='ERROR'), False),
            ('collector_changed_verification', lambda c: c.data['collector_verification.json']['after'].update(manifest_sha256='0' * 64), False),
            ('actor_not_pass', lambda c: c.data['actor_verification.json'].update(status='ERROR'), False),
            ('actor_wrong_ready', lambda c: c.data['actor_verification.json']['ready'].update(sha256='0' * 64), False),
            ('actor_bool_pid', lambda c: c.data['actor_verification.json'].update(predictor_pid=True), False),
            ('actor_cleanup_error', lambda c: c.data['actor_verification.json'].update(cleanup_errors=['invented']), False),
            ('actor_extra_recorder', lambda c: c.data['actor_verification.json']['accounting'].append(copy.deepcopy(c.data['actor_verification.json']['accounting'][0])), False),
            ('actor_initialization_error', lambda c: c.data['actor_verification.json']['accounting'][0].update(initialization_error='invented'), False),
            ('actor_wrong_count', lambda c: c.data['actor_verification.json']['accounting'][0].update(charged_attempts=6), False),
            ('actor_sidecar_hash', sidecar_hash, False),
        ]
        for name, mutation, resign in phase_specs:
            check('phase_' + name, lambda name=name, mutation=mutation, resign=resign: phase_case(name, mutation, resign=resign), reject=True)
        check('native_representative_url_geometry_inequality_allowed', lambda: phase_case('representative_geometry', raw_geometry))
        for name in ('decisions.jsonl', 'observations.jsonl', 'steps.jsonl', 'forecast_receipts.jsonl', 'forecast_reconciliation.jsonl'):
            def truncate(capsule, name=name):
                path = capsule.directory / name; path.write_bytes(path.read_bytes()[:-1])
            check('truncated_' + name, lambda name=name, truncate=truncate: phase_case('truncated_' + name, after_dump=truncate), reject=True)
        for label, change in [('noncanonical', lambda raw: raw.replace(b'"schema":', b'"schema": ', 1)),
                              ('truncated', lambda raw: raw[:-1]), ('blank_line', lambda raw: raw + b'\n')]:
            def bad_ledger(label=label, change=change):
                path = root / ('ledger_' + label + '.jsonl')
                path.write_bytes(change(b''.join(custody.io.json_bytes(row) for row in baseline.data['ledger'])))
                return custody.read_ledger(path, baseline.provenance)
            check('ledger_' + label, bad_ledger, reject=True)
        def ledger_symlink():
            original = root / 'ledger_actual.jsonl'; original.write_bytes(b''.join(custody.io.json_bytes(row) for row in baseline.data['ledger']))
            alias = root / 'ledger_alias.jsonl'; alias.symlink_to(original)
            return custody.read_ledger(alias, baseline.provenance)
        check('ledger_symlink_rejected', ledger_symlink, reject=True)
        for label, change in [('unknown_observation', lambda raw: raw.update(extra='invented')),
                              ('unknown_node', lambda raw: raw['nodes'][0].update(extra='invented')),
                              ('boolean_node_index', lambda raw: raw['nodes'][0].update(i=False)),
                              ('cyclic_parent', lambda raw: raw['nodes'][0].update(parent=0))]:
            def raw_gate(label=label, change=change):
                capsule = Capsule(baseline, root / ('raw_' + label), custody); change(capsule.data['observations.jsonl'][0]['obs']); capsule.dump()
                calls = []
                def signature(public): calls.append('native_signature_constructor'); return native.signature(public)
                try: custody.raw_history(capsule.directory, validate_step, signature)
                except Exception as error:
                    require(not calls, 'Malformed raw schema reached native constructor')
                    return {'rejected_before_native': True, 'error': type(error).__name__}
                raise AssertionError('Malformed raw schema accepted')
            check('raw_schema_gate_' + label, raw_gate)

        # Exact checkpoint inventories, the same process/objects, raw training and learned commitment.
        training = {name: copy.deepcopy(baseline.data[name + '.jsonl']) for name in ('observations', 'steps')}
        checkpoint_root = root / 'checkpoints'; checkpoint_root.mkdir()
        initial_path = checkpoint_root / 'initial.json'; initial_saved, initial_receipt = checkpoint_fixture(custody, model, training, initial_path)
        initial = custody.checkpoint(initial_path, initial_receipt, index=0, training_records=training, pid=731)
        check('startup_checkpoint_raw_cut_native_objects', lambda: {'cut': initial['projection']['common']['fit']['cut'], 'objects': initial['projection']['identity_attestation']['objects'], 'checks': list(initial['checks'])})
        def checkpoint_case(name, mutation=None, *, startup=False, receipt_mutation=None):
            path = checkpoint_root / (name + '.json'); index = 0 if startup else 1
            saved, receipt = checkpoint_fixture(custody, model, training, path, index=index)
            if mutation is not None: mutation(saved)
            write(path, saved); receipt['sha256'] = sha(path)
            if receipt_mutation is not None: receipt_mutation(receipt)
            result = custody.checkpoint(path, receipt, index=index, initial=None if startup else initial,
                                        training_records=training, pid=731)
            return {'checks': list(result['checks']), 'ownership': list(result['projection']['ownership']),
                    'learned_commitment_sha256': result['learned_commitment_sha256']}
        check('later_checkpoint_same_native_fit', lambda: checkpoint_case('later_valid'))
        checkpoint_specs = [
            ('receipt_bool_index', None, False, lambda r: r.update(checkpoint_index=True)),
            ('receipt_wrong_hash', None, False, lambda r: r.update(sha256='0' * 64)),
            ('saved_bool_index', lambda r: r.update(checkpoint_index=True), False, None),
            ('saved_incomplete', lambda r: r.update(instrument_status='INCOMPLETE'), False, None),
            ('failed_check', lambda r: r['checks'].update(learned_commitment_unchanged=False), False, None),
            ('integer_check_alias', lambda r: r['checks'].update(complete_projection=1), False, None),
            ('missing_required_check', lambda r: r['checks'].pop('old_memo_entries_unchanged_since_startup'), True, None),
            ('extra_check', lambda r: r['checks'].update(unreviewed_gate=True), True, None),
            ('failed_ownership', lambda r: r['projection']['ownership'].update(shared_graph=False), False, None),
            ('missing_required_ownership', lambda r: r['projection']['ownership'].pop('fit_inducer'), True, None),
            ('extra_ownership', lambda r: r['projection']['ownership'].update(unreviewed_relationship=True), True, None),
            ('projection_incomplete', lambda r: r['projection'].update(status='INCOMPLETE'), False, None),
            ('common_incomplete', lambda r: r['projection']['common'].update(status='INCOMPLETE'), False, None),
            ('copy_failure', lambda r: r['projection']['common']['incomplete_reasons'].append({'invented': True}), False, None),
            ('wrong_pid', lambda r: r['projection']['identity_attestation'].update(pid=732), False, None),
            ('bool_pid', lambda r: r['projection']['identity_attestation'].update(pid=True), False, None),
            ('different_native_object', lambda r: r['projection']['identity_attestation']['objects'].update(graph=9001), False, None),
            ('missing_native_object', lambda r: r['projection']['identity_attestation']['objects'].pop('graph'), True, None),
            ('bool_native_object_id', lambda r: r['projection']['identity_attestation']['objects'].update(graph=True), True, None),
            ('missing_stored_object_inventory', lambda r: r['projection']['stored_key_inventory'].pop('graph'), True, None),
            ('different_stored_keys', lambda r: r['projection']['stored_key_inventory']['fit'].append('new-field'), False, None),
            ('wrong_learned_hash', lambda r: r.update(learned_commitment_sha256='0' * 64), False, None),
            ('changed_learned_value', lambda r: r['learned_commitment'].update(invented_change=True), False, None),
            ('changed_raw_training', lambda r: r['projection']['common']['raw_mapping']['raw_records']['steps'].pop(), False, None),
            ('wrong_raw_training_hash', lambda r: r['projection']['common']['raw_mapping'].update(raw_records_sha256='0' * 64), False, None),
            ('task_labels_enter_learner', lambda r: r['projection']['common']['primary_step_associations'].append({'step': 0}), False, None),
            ('bool_training_cut', lambda r: r['projection']['common']['fit'].update(cut=True), False, None),
            ('different_training_cut', lambda r: r['projection']['common']['fit'].update(cut=5), False, None),
            ('different_permitted_steps', lambda r: r['projection']['common']['permitted_evidence_step_ids'].pop(), False, None),
        ]
        for name, mutation, startup, receipt_mutation in checkpoint_specs:
            check('checkpoint_' + name, lambda name=name, mutation=mutation, startup=startup, receipt_mutation=receipt_mutation:
                  checkpoint_case(name, mutation, startup=startup, receipt_mutation=receipt_mutation), reject=True)
        def projection_binding_is_caller_gate():
            path = checkpoint_root / 'caller_projection_binding.json'
            saved, receipt = checkpoint_fixture(custody, model, training, path, index=1)
            saved['projection']['common']['abstractor']['learned_value'] = 'changed projected learned value'
            write(path, saved); receipt['sha256'] = sha(path)
            custody.checkpoint(path, receipt, index=1, initial=initial, training_records=training, pid=731)
            require(not custody.same(model.learned_view(saved['projection']), saved['learned_commitment']), 'Independent projected learned mismatch disappeared')
            return {'core_verifies_saved_commitment': True, 'caller_must_recompute_learned_view': True,
                    'scope': 'Explicit root-assigned caller obligation; the evaluate CLI is not executed or accepted here'}
        check('projection_to_learned_view_is_explicit_caller_gate', projection_binding_is_caller_gate)
        for operation in ('checkpoint', 'shutdown'):
            check('control_valid_' + operation, lambda operation=operation: control_case(control, boundary, root / ('c_' + operation), operation=operation))
        for behavior in ('exists', 'source_before', 'ready_before', 'request_error', 'lost_ack', 'wrong_provenance', 'incomplete', 'source_after', 'ready_after'):
            check('control_' + behavior, lambda behavior=behavior: control_case(control, boundary, root / ('c_' + behavior), behavior=behavior))
    require(all(sha(ROOT / name) == digest for name, digest in sources.items()), 'Source changed during custody/control checks')
    record = {'schema': 'semabi.j1.custody_control_independent_checks.v1', 'status': 'PASS' if all(row['status'] == 'PASS' for row in rows) else 'FAIL',
              'sources': sources, 'checks': rows, 'counts': dict(Counter(row['status'] for row in rows)),
              'pid': os.getpid(), 'affinity': sorted(os.sched_getaffinity(0)),
              'scope': 'Invented records only; actual native public data and EvidenceLog, retained collect_script/Recorder/resolver AST, accepted actor and real ledger. Fake Browser, in-process invented predictor, bound temporary local Unix sockets for actual control ready gates. No fit, prediction, browser service, J1/R1 payload or evaluate/preserve CLI.'}
    with args.output.open('x') as stream: json.dump(record, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps({'path': str(args.output), 'sha256': sha(args.output), 'counts': record['counts'], 'failed': [row['name'] for row in rows if row['status'] == 'FAIL']}))
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
