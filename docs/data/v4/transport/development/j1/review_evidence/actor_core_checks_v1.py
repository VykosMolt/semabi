"""Independent actor/unchanged-Recorder controls with invented public data."""
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
ACTOR = HERE.parent / 'act.py'
IO_SHA = '2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327'
CONTRACT_SHA = 'f9642c36b3581323eaa8206d5117dd7831c2d57cf6142b39877fd0e2fbc17d90'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, detail):
    if not condition: raise AssertionError(detail)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); sys.modules[name] = value
    spec.loader.exec_module(value); return value


def native_symbols(path, names, namespace):
    tree = ast.parse(path.read_text())
    selected = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names]
    require({node.name for node in selected} == set(names), 'Native AST inventory differs')
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)


def build_native(events, *, row_mutator=None, step_mutator=None, primitive_mutator=None, observe_error=False):
    ns = {'dataclass': dataclass, 'field': field, 'hashlib': hashlib, 'json': json, 'Path': Path, 'Counter': Counter}
    native_symbols(ROOT / 'semabi/compiler/observation.py', {'Node', 'Observation'}, ns)
    native_symbols(ROOT / 'semabi/compiler/browser.py', {'Primitive', 'ActionResult'}, ns)
    native_symbols(ROOT / 'semabi/compiler/evidence.py', {'Step'}, ns)
    native_symbols(ROOT / 'scripts/transport_collect.py', {'Recorder'}, ns)
    tree = ast.parse((ROOT / 'semabi/compiler/browser.py').read_text())
    browser = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Browser')
    act = next(node for node in browser.body if isinstance(node, ast.FunctionDef) and node.name == 'act')
    exec(compile(ast.Module(body=[act], type_ignores=[]), str(ROOT / 'semabi/compiler/browser.py'), 'exec'), ns)
    raw = {'url': 'http://127.0.0.1/invented', 'nodes': [
        {'i': 0, 'parent': -1, 'role': 'group', 'name': 'Panel', 'bbox': [0, 0, 80, 60]},
        {'i': 1, 'parent': 0, 'role': 'button', 'name': 'Apply', 'bbox': [1, 1, 20, 10]},
        {'i': 2, 'parent': 0, 'role': 'textbox', 'name': 'Entry', 'value': '', 'bbox': [1, 15, 20, 10]},
        {'i': 3, 'parent': 0, 'role': 'combobox', 'name': 'Choice', 'value': 'A', 'options': ['A', 'B'], 'bbox': [1, 30, 20, 10]}]}
    page = ns['Observation'].from_json(raw)
    if row_mutator is not None:
        def dumps(value, **kwargs):
            if type(value) is dict and 'charged_attempt' in value:
                value = copy.deepcopy(value); row_mutator(value)
            return json.dumps(value, **kwargs)
        ns['json'] = SimpleNamespace(dumps=dumps)
    class Log:
        def __init__(self, _directory=None): self.steps = []; self.observations = {}; self.typed_tokens = []
        def add_observation(self, observation):
            signature = observation.structural_signature(); self.observations.setdefault(signature, observation); return signature
        def add_step(self, episode, primitive, ok, error, before, after):
            if primitive.kind == 'type' and primitive.text and primitive.text not in self.typed_tokens:
                self.typed_tokens.append(primitive.text)
            step = ns['Step'](len(self.steps), episode, primitive, ok, error,
                              self.add_observation(before), self.add_observation(after), list(self.typed_tokens))
            if step_mutator is not None: step_mutator(step)
            self.steps.append(step); return step
    class Browser:
        def __init__(self, url='', reset_url=''):
            self.url, self.reset_url = url, reset_url; self._last_obs = page
            self.episode = 0; self.n_primitives = 0; self.n_resets = 0; self.step_hooks = []
            self.n_settle_timeouts = self.n_navigation_waits = 0
            self.closed = False; self.fail_click = False
            self._page = SimpleNamespace(reload=lambda **_kwargs: None, keyboard=SimpleNamespace(press=lambda _text: None))
        def observe(self):
            if observe_error: raise OSError('invented observation failure after action')
            return page
        def _handle(self, _target):
            def click(**_kwargs):
                if self.fail_click: raise RuntimeError('invented native browser rejection')
            def text(value, **_kwargs):
                if type(value) is not str: raise TypeError('invented browser requires scalar text string')
            return SimpleNamespace(click=click, fill=text, select_option=lambda label, **kwargs: text(label, **kwargs))
        def _do_reset(self, _seed): self.episode += 1; self.n_resets += 1
        def act(self, primitive):
            events.append('native_act')
            result = ns['act'](self, primitive)
            if primitive_mutator is not None: primitive_mutator(primitive)
            return result
        def close(self): self.closed = True
    return SimpleNamespace(**ns), Browser, Log, page


class LocalClient:
    """Real ledger/receipt verification; the predictor callback is invented."""
    def __init__(self, io, directory, provenance, events, *, lost_ack=False, incomplete=False, wrong_provenance=False):
        self.io, self.events, self.provenance = io, events, provenance
        self.ledger = io.Ledger(directory / 'forecasts.jsonl'); self.ledger_path = self.ledger.path
        self.requests = []; self.lost_ack = lost_ack; self.incomplete = incomplete; self.wrong_provenance = wrong_provenance
    def request(self, request):
        self.ledger.validate_next(request); self.events.append('validated_request'); self.requests.append(copy.deepcopy(request))
        response = {'instrument_status': 'INCOMPLETE' if self.incomplete else 'COMPLETE', 'category': 'INVENTED'}
        provenance = {'wrong': True} if self.wrong_provenance else self.provenance
        ack = self.ledger.append(request, response, provenance); self.events.append('durable_predictor_return')
        if self.lost_ack: raise self.io.ProtocolError('invented lost acknowledgement')
        return ack, self.io.verify_receipt(self.ledger_path, ack, request)


def case(actor, directory, *, row_mutator=None, step_mutator=None, primitive_mutator=None,
         observe_error=False, lost_ack=False, incomplete=False, wrong_provenance=False,
         failure_fsync=None, initial_counter=None, unpaired=False, sequence=False):
    directory.mkdir(); events = []; ns, Browser, Log, page = build_native(events,
        row_mutator=row_mutator, step_mutator=step_mutator, primitive_mutator=primitive_mutator, observe_error=observe_error)
    client = LocalClient(actor.io, directory, {'source': 'invented-source', 'fit': 'same-invented-fit'}, events,
                         lost_ack=lost_ack, incomplete=incomplete, wrong_provenance=wrong_provenance)
    state = actor.ActorState(client, client.provenance); collector = SimpleNamespace(Recorder=ns.Recorder)
    original = collector.Recorder; state.instrument(collector)
    browser = Browser(); log = Log(); recorder = collector.Recorder(browser, log, directory / 'decisions.jsonl')
    if initial_counter is not None: recorder.attempts = initial_counter
    actual_fsync = actor.os.fsync
    fds = {client.ledger.stream.fileno(): 'predictor_fsync', recorder.receipts.fileno(): 'actor_receipt_fsync', recorder.reconciliations.fileno(): 'actor_reconciliation_fsync'}
    def fsync(fd):
        label = fds.get(fd, 'other_fsync'); events.append(label)
        if failure_fsync == label: raise OSError('invented ' + label + ' failure')
        return actual_fsync(fd)
    actor.os.fsync = fsync
    outcome = {'events': events}
    try:
        if sequence:
            before = recorder.act(None, ns.Primitive('reset', text='0'), {'reason': 'invented_reset'})
            before = recorder.act(before, ns.Primitive('reload'), {'reason': 'invented_reload'})
            before = recorder.act(before, ns.Primitive('click', 1), {'case': 'evaluator-only-case'})
            before = recorder.act(before, ns.Primitive('select', 3, 'B'), {'reason': 'invented_nonclick'})
            before = recorder.act(before, ns.Primitive('click', text='unseen argument', target_desc={'role': 'button', 'name': 'Unseen'}), {'requested': {'scope': 'evaluator-only'}}, error='Unreachable invented target')
            browser.fail_click = True
            before = recorder.act(before, ns.Primitive('click', 1), {'reason': 'invented_browser_failure'})
            browser.fail_click = False
            recorder.act(before, ns.Primitive('type', 2, True), {'reason': 'invented_scalar_failure'})
            require(recorder.attempts == 7 and recorder.failures == 3 and recorder.paired_steps == 6, 'Native accounting differs')
            require(len(client.requests) == 7 and client.requests[0]['observation'] is None and client.requests[4]['primitive'] is None, 'Reset/unreachable request differs')
            require(all(set(r) == {'schema', 'op', 'request_id', 'observation', 'primitive'} for r in client.requests), 'Evaluator metadata crossed request boundary')
            require(all(intent['state'] == 'MATCHED' for intent in recorder.intents), 'Completed path has an orphan')
            for index, event in enumerate(events):
                if event == 'native_act': require(events[index-1] == 'actor_receipt_fsync', 'Native action preceded durable actor receipt')
            outcome.update(charged_attempts=recorder.attempts, failures=recorder.failures, paired_steps=recorder.paired_steps,
                           intents=[dict(v) for v in recorder.intents])
        else:
            recorder.act(None if unpaired else page, ns.Primitive('reset', text='0') if unpaired else ns.Primitive('click', 1), {'reason': 'invented'})
            outcome.update(intents=[dict(v) for v in recorder.intents], charged_attempts=recorder.attempts)
    except Exception as error:
        outcome.update(exception=type(error).__name__, detail=str(error), intents=[dict(v) for v in recorder.intents],
                       charged_attempts=recorder.attempts, native_calls=events.count('native_act'))
    finally:
        actor.os.fsync = actual_fsync
        state.close(); client.ledger.close()
        require(collector.Recorder is original, 'Recorder class was not restored')
    return outcome


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False); parser.add_argument('--actor-sha', required=True); parser.add_argument('--output', required=True, type=Path); args = parser.parse_args()
    require(not args.output.exists(), 'Exclusive output exists')
    require(sha(ACTOR) == args.actor_sha and sha(ACTOR.parent / 'live_io.py') == IO_SHA and sha(ACTOR.parent / 'live_contract_v1.md') == CONTRACT_SHA, 'Reviewed source changed')
    actor = module('_reviewed_j1_actor', ACTOR)
    sources = {str(p.relative_to(ROOT)): sha(p) for p in [ACTOR, ACTOR.parent / 'live_io.py', ACTOR.parent / 'live_contract_v1.md', Path(__file__), ROOT / 'semabi/compiler/observation.py', ROOT / 'semabi/compiler/browser.py', ROOT / 'semabi/compiler/evidence.py', ROOT / 'scripts/transport_collect.py']}
    rows = []
    with tempfile.TemporaryDirectory(prefix='j1_actor_core_') as temporary:
        root = Path(temporary)
        specifications = [
            ('complete_native_sequence', {'sequence': True}, 'accept'),
            ('unpaired_reset', {'unpaired': True}, 'accept'),
            ('lost_ack_before_act', {'lost_ack': True}, 'before'),
            ('incomplete_before_act', {'incomplete': True}, 'before'),
            ('wrong_fit_before_act', {'wrong_provenance': True}, 'before'),
            ('predictor_fsync_before_act', {'failure_fsync': 'predictor_fsync'}, 'before'),
            ('actor_fsync_before_act', {'failure_fsync': 'actor_receipt_fsync'}, 'before'),
            ('reconciliation_fsync_orphan', {'failure_fsync': 'actor_reconciliation_fsync'}, 'after'),
            ('native_observe_error_orphan', {'observe_error': True}, 'after'),
            ('bool_counter_before_act', {'initial_counter': True}, 'before'),
            ('negative_counter_before_act', {'initial_counter': -1}, 'before'),
            ('row_bool_charge', {'row_mutator': lambda row: row.update(charged_attempt=True)}, 'after'),
            ('row_bool_episode', {'row_mutator': lambda row: row.update(episode=False)}, 'after'),
            ('row_float_step', {'row_mutator': lambda row: row.update(step=0.0)}, 'after'),
            ('step_bool_index', {'step_mutator': lambda step: setattr(step, 'step', False)}, 'after'),
            ('step_float_episode', {'step_mutator': lambda step: setattr(step, 'episode', 0.0)}, 'after'),
            ('row_wrong_receipt', {'row_mutator': lambda row: row['forecast_receipt'].update(request_id='wrong')}, 'after'),
            ('row_wrong_action', {'row_mutator': lambda row: row['action'].update(kind='reload')}, 'after'),
            ('row_wrong_before', {'row_mutator': lambda row: row.update(before='wrong')}, 'after'),
            ('row_wrong_after', {'row_mutator': lambda row: row.update(after='wrong')}, 'after'),
            ('row_wrong_ok', {'row_mutator': lambda row: row.update(ok=False)}, 'after'),
            ('row_integer_ok', {'row_mutator': lambda row: row.update(ok=1)}, 'after'),
            ('row_wrong_error', {'row_mutator': lambda row: row.update(error='invented corruption')}, 'after'),
            ('step_wrong_ok', {'step_mutator': lambda step: setattr(step, 'ok', False)}, 'after'),
            ('step_wrong_error', {'step_mutator': lambda step: setattr(step, 'error', 'invented corruption')}, 'after'),
            ('post_action_primitive_mutation', {'primitive_mutator': lambda primitive: setattr(primitive, 'text', 'changed after receipt')}, 'after'),
            ('unpaired_wrong_after', {'unpaired': True, 'row_mutator': lambda row: row.update(after='wrong')}, 'after'),
        ]
        for name, options, expected in specifications:
            value = case(actor, root / name, **options)
            passed = ('exception' not in value) if expected == 'accept' else ('exception' in value and value['native_calls'] == (0 if expected == 'before' else 1))
            rows.append({'name': name, 'expected': expected, 'status': 'PASS' if passed else 'FAIL', 'result': value})
    require(all(sha(ROOT / name) == digest for name, digest in sources.items()), 'Reviewed source changed during controls')
    record = {'schema': 'semabi.j1.actor_core_independent_checks.v1', 'status': 'PASS' if all(row['status'] == 'PASS' for row in rows) else 'FAIL',
              'sources': sources, 'checks': rows, 'counts': dict(Counter(row['status'] for row in rows)),
              'scope': 'Invented data, real live_io ledger and receipts, exact native class/method AST with fake Browser/EvidenceLog and explicit serializer/log corruption. No fit, browser launch, fixture or sealed payload.'}
    with args.output.open('x') as stream: json.dump(record, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps({'path': str(args.output), 'sha256': sha(args.output), 'counts': record['counts'], 'failed': [row['name'] for row in rows if row['status'] == 'FAIL']}))
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
