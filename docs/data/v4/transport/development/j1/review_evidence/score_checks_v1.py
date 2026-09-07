"""Independent saved-forecast scoring controls with invented public pages."""
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
SCORE = HERE.parent / 'score.py'
IO_SHA = '2cf44787526076337b53d8a67ef12796c7460d2dcb64cfbbbec7093c946a5327'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def require(condition, detail):
    if not condition: raise AssertionError(detail)

def imported(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); sys.modules[name] = value
    spec.loader.exec_module(value); return value


def page(text, *, names=('Alpha', 'Beta'), channel='status'):
    nodes = [{'i': 0, 'parent': -1, 'role': 'group', 'name': '', 'bbox': [0, 0, 100, 100]}]
    for name in names:
        nodes.append({'i': len(nodes), 'parent': 0, 'role': 'text', 'name': name, 'bbox': [0, 0, 10, 10]})
    if channel is not None:
        nodes.append({'i': len(nodes), 'parent': 0, 'role': channel, 'name': text, 'bbox': [0, 0, 50, 10]})
    return {'url': 'http://127.0.0.1/invented-score', 'nodes': nodes}


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--score-sha', required=True); parser.add_argument('--protocol-sha', required=True)
    parser.add_argument('--output', required=True, type=Path); args = parser.parse_args()
    require(not args.output.exists(), 'Exclusive result identity already exists')
    require(sha(SCORE) == args.score_sha and sha(HERE.parent / 'protocol_v1.md') == args.protocol_sha
            and sha(HERE.parent / 'live_io.py') == IO_SHA, 'Reviewed source changed')
    paths = [SCORE, HERE.parent / 'protocol_v1.md', HERE.parent / 'live_io.py', HERE.parent / 'live_contract_v1.md',
             HERE.parent / 'trace.py', Path(__file__)]
    paths += sorted((ROOT / 'semabi/compiler').rglob('*.py'))
    paths += [ROOT / 'semabi/__init__.py', ROOT / 'semabi/relmodel.py']
    sources = {str(path.relative_to(ROOT)): sha(path) for path in paths}
    scorer = imported('_reviewed_j1_score', SCORE)
    trace = imported('_reviewed_j1_score_trace', HERE.parent / 'trace.py')
    sys.path.insert(0, str(ROOT))
    from semabi.compiler.observation import Node, Observation
    from semabi.compiler.v4 import emission, outcome
    native = SimpleNamespace(Observation=Observation, emission=emission, outcome=outcome)
    bindings = trace.Bindings({}, {
        outcome.Vouch: trace.RecordSpec('semabi.compiler.v4.outcome.Vouch', tuple(outcome.Vouch.__dataclass_fields__)),
        outcome.ControlOutcome: trace.RecordSpec('semabi.compiler.v4.outcome.ControlOutcome', tuple(outcome.ControlOutcome.__dataclass_fields__)),
        Node: trace.RecordSpec('semabi.compiler.observation.Node', tuple(Node.__dataclass_fields__)),
        Observation: trace.RecordSpec('semabi.compiler.observation.Observation', tuple(Observation.__dataclass_fields__)),
    }, {'observation': Observation})
    def encoded(value):
        copier = trace.Copier(bindings); result = copier.copy(value)
        require(not copier.errors, 'Invented value could not be copied: ' + repr(copier.errors))
        return result, copier.snapshots
    def cp(value):
        result, snapshots = encoded(value); require(not snapshots, 'Unexpected snapshot in scalar/container helper'); return result
    control = 'invented-apply-control'; connected = 'Connected <> to <> .'; refused = 'Refused <> to <> .'
    def vouch(event, *, sole=False, preceded_by=()):
        return outcome.Vouch(event, (4, 9), (('present', 'source'),), 2, sole, preceded_by)
    got = outcome.ControlOutcome(control, events={connected: 2, refused: 1})
    checkpoint = {'schema': 'semabi.j1.live_checkpoint.v1', 'checkpoint_index': 0,
                  'instrument_status': 'COMPLETE', 'projection': {'snapshots': {}, 'common': {
                  'emission_vocabulary': {'values': cp({('Historic',)}), 'frozen': True},
                  'fit': {'outcomes': cp({control: got})}}}}
    vocab = scorer.vocabulary(checkpoint, emission); initial_vocab = copy.deepcopy(vocab.values)
    known = scorer.control_events(checkpoint)
    require(known == {control: {connected: 2, refused: 1}}, 'Saved event counts differ')
    before, after = page('Waiting.'), page('Connected Alpha to Beta.')
    rows = []; assessed = []
    def check(name, function, *, reject=False):
        try:
            value = function(); passed = not reject
            rows.append({'name': name, 'expected': 'reject' if reject else 'accept',
                         'status': 'PASS' if passed else 'FAIL', 'result': value})
        except Exception as error:
            rows.append({'name': name, 'expected': 'reject' if reject else 'accept',
                         'status': 'PASS' if reject else 'FAIL', 'exception': type(error).__name__, 'detail': str(error)})
    def response(event=connected, *, rule=None, listed=None, arguments=None, roles=None):
        rule = {event: vouch(event)} if rule is None else rule
        listed = {event: vouch(event)} if listed is None else listed
        events = list(dict.fromkeys([event, *rule, *listed]))
        if arguments is None:
            arguments = {key: ({0: 'Alpha', 1: 'Beta'} if key == connected else {}) for key in events}
        if roles is None: roles = {connected: {0: 'source', 1: 'target'}}
        values = {'control': control, 'state': None, 'parsed': None, 'owner': None, 'bound': {},
                  'binding_status': {}, 'literals': set(), 'roles': {}, 'arg_roles': roles,
                  'decision_list': event, 'rule': rule, 'list': listed, 'arguments': arguments}
        saved, snapshots = encoded(values)
        return {'schema': 'semabi.j1.forecast.v1', 'status': 'FORECAST', 'instrument_status': 'COMPLETE',
                'incomplete_reasons': [], 'snapshots': snapshots, 'values': saved}
    def assess(saved=None, pre=before, post=after, *, missing=False):
        saved = None if missing else response() if saved is None else saved
        before_bytes = scorer.io.json_bytes([saved, pre, post]); vocabulary_before = copy.deepcopy(vocab.values)
        result = scorer.assess(saved, pre, post, vocab, known, native)
        require(scorer.io.json_bytes([saved, pre, post]) == before_bytes, 'Scoring mutated saved forecasts or raw pages')
        require(vocab.values == vocabulary_before and vocab.frozen is True, 'Scoring changed frozen vocabulary')
        assessed.append(result); return result
    def categories(saved=None, pre=before, post=after, *, expected, details=None, missing=False):
        value = assess(saved, pre, post, missing=missing)
        actual = {name: item['category'] for name, item in value['channels'].items()}
        require(actual == expected, 'Wrong frame categories: ' + repr(actual))
        for name, detail in (details or {}).items(): require(value['channels'][name].get('detail') == detail, 'Wrong unavailable detail')
        return value
    expected_correct = {'decision_list': 'correct', 'rule': 'forced_correct', 'list': 'forced_correct'}
    expected_wrong = {'decision_list': 'wrong', 'rule': 'forced_wrong', 'list': 'forced_wrong'}
    expected_unavailable = dict.fromkeys(scorer.CHANNELS, 'unestablished')

    # The independent expected values preserve exact native types, insertion order and masks.
    def large_roundtrip():
        values = {'mask': 2 ** 240 + 17, ('type', 3): -(2 ** 120), 'edge': 2 ** 53,
                  'below': -(2 ** 53), 'small': 2 ** 53 - 1, 'counter': Counter({'a': 3}),
                  'defaults': defaultdict(list, {'x': ('y',)}), 'set': {('A',), ('B',)}, 'frozen': frozenset({1, 2})}
        raw = cp(values); decoded = scorer.decode(raw)
        require(list(decoded) == list(values) and decoded == dict(values), 'Lossless typed values differ')
        require(type(decoded['mask']) is int and decoded['mask'] == 2 ** 240 + 17, 'Large mask lost bits')
        require(type(decoded['set']) is set and type(decoded['frozen']) is frozenset, 'Set kind changed')
        return {'mask_decimal': str(decoded['mask']), 'mapping_key_order_preserved': True, 'native_copier': True}
    check('typed_large_integer_container_roundtrip', large_roundtrip)
    def snapshot_roundtrip():
        raw, snapshots = encoded(Observation.from_json(after)); decoded = scorer.decode(raw, snapshots)
        require(decoded['$record'] == 'semabi.compiler.observation.Observation', 'Snapshot type changed')
        require(decoded['fields']['nodes'][1]['fields']['name'] == 'Alpha', 'Snapshot content changed')
        return {'snapshot_count': len(snapshots), 'typed_record_preserved': True}
    check('actual_copier_snapshot_roundtrip', snapshot_roundtrip)
    for label, value in [('zero', '0'), ('leading_zero', '09007199254740992'), ('plus', '+9007199254740992'), ('space', ' 9007199254740992'), ('small', '9007199254740991'), ('float', '9007199254740992.0')]:
        check('noncanonical_decimal_' + label, lambda value=value: scorer.decode({'$integer_decimal': value}), reject=True)
    check('mapping_duplicate_key', lambda: scorer.decode({'$mapping': 'dict', 'items': [['x', 1], ['x', 2]]}), reject=True)
    check('mapping_boolean_integer_alias', lambda: scorer.decode({'$mapping': 'dict', 'items': [[True, 1], [1, 2]]}), reject=True)
    check('mapping_float_integer_alias', lambda: scorer.decode({'$mapping': 'dict', 'items': [[1.0, 1], [1, 2]]}), reject=True)
    check('mapping_unknown_kind', lambda: scorer.decode({'$mapping': 'OrderedDict', 'items': []}), reject=True)
    check('set_duplicate_encoded_member', lambda: scorer.decode({'$set': 'set', 'items': [1, 1]}), reject=True)
    check('set_boolean_integer_alias', lambda: scorer.decode({'$set': 'set', 'items': [1, True]}), reject=True)
    check('set_unsorted_members', lambda: scorer.decode({'$set': 'set', 'items': [2, 1]}), reject=True)
    check('unknown_copied_object', lambda: scorer.decode({'$unknown': {'reason': 'invented'}}), reject=True)
    check('missing_snapshot', lambda: scorer.decode({'$snapshot': 'a' * 64}, {}), reject=True)
    check('wrong_snapshot_hash', lambda: scorer.decode({'$snapshot': 'a' * 64}, {'a' * 64: {'$tuple': []}}), reject=True)
    def active_snapshot():
        value = {'$tuple': []}; address = trace.sha(value)
        return scorer.decode({'$snapshot': address}, {address: value}, (address,))
    check('cyclic_snapshot_reference', active_snapshot, reject=True)

    def vocabulary_frozen():
        result = scorer.vocabulary(checkpoint, emission)
        require(type(result) is emission.Vocabulary and result.values == {('Historic',)} and result.frozen is True, 'Saved Vocabulary changed')
        result.learn(Observation.from_json(page('Connected New to Name.', names=('New', 'Name'))))
        require(result.values == {('Historic',)}, 'Saved Vocabulary learned from held-out page')
        return {'native_type': True, 'values': sorted(result.values), 'frozen': result.frozen}
    check('saved_native_vocabulary_frozen', vocabulary_frozen)
    for name, mutation in [('not_frozen', lambda value: value['projection']['common']['emission_vocabulary'].update(frozen=False)),
                           ('bool_index', lambda value: value.update(checkpoint_index=False)),
                           ('later_checkpoint', lambda value: value.update(checkpoint_index=1)),
                           ('incomplete', lambda value: value.update(instrument_status='INCOMPLETE')),
                           ('wrong_values_type', lambda value: value['projection']['common']['emission_vocabulary'].update(values=cp([('Historic',)])))]:
        def changed_vocabulary(mutation=mutation):
            value = copy.deepcopy(checkpoint); mutation(value); return scorer.vocabulary(value, emission)
        check('vocabulary_' + name, changed_vocabulary, reject=True)
    check('saved_control_event_counts', lambda: {'counts': scorer.control_events(checkpoint)})
    def bad_count():
        value = copy.deepcopy(checkpoint); value['projection']['common']['fit']['outcomes']['items'][0][1]['fields']['events'] = cp({connected: True})
        return scorer.control_events(value)
    check('control_event_boolean_count', bad_count, reject=True)
    def vouch_roundtrip():
        expected = vouch(connected, preceded_by=(refused,)); raw, snapshots = encoded({connected: expected})
        result = scorer._vouches(raw, snapshots)[connected]
        require(result == vars(expected) and result['witnesses'] == (4, 9) and result['preceded_by'] == (refused,), 'Vouch was summarized or reordered')
        return result
    check('native_vouch_full_ordered_fields', vouch_roundtrip)
    for name, mutation in [('missing_field', lambda record: record['fields'].pop('preceded_by')),
                           ('extra_field', lambda record: record['fields'].update(extra=True)),
                           ('bool_covers', lambda record: record['fields'].update(covers=True)),
                           ('negative_witness', lambda record: record['fields'].update(witnesses=cp((-1,)))),
                           ('bool_witness', lambda record: record['fields'].update(witnesses=cp((True,)))),
                           ('wrong_event', lambda record: record['fields'].update(event='wrong')),
                           ('integer_sole', lambda record: record['fields'].update(sole=1)),
                           ('wrong_record_type', lambda record: record.update({'$record': 'invented.Vouch'}))]:
        def wrong_vouch(mutation=mutation):
            raw = cp({connected: vouch(connected)}); mutation(raw['items'][0][1]); return scorer._vouches(raw, {})
        check('vouch_' + name, wrong_vouch, reject=True)

    # Frame/SILENT truth table, including the shared observable unchanged case.
    check('changed_matching_standing_frame', lambda: categories(expected=expected_correct))
    check('changed_wrong_frame', lambda: categories(response(refused), expected=expected_wrong))
    check('unchanged_matching_standing_frame', lambda: categories(pre=after, expected=expected_correct))
    check('unchanged_arbitrary_frame_is_wrong', lambda: categories(response(refused), pre=after, expected=expected_wrong))
    check('unchanged_silent_is_correct', lambda: categories(response(outcome.SILENT), pre=after, expected=expected_correct))
    check('changed_silent_is_wrong', lambda: categories(response(outcome.SILENT), expected=expected_wrong))
    check('empty_unchanged_channel_silent', lambda: categories(response(outcome.SILENT), pre=page(''), post=page(''), expected=expected_correct))
    check('missing_channel_is_unavailable', lambda: categories(post=page('', channel=None), expected=expected_unavailable, details=dict.fromkeys(scorer.CHANNELS, 'NO_CHANNEL')))
    check('alert_is_not_native_emission_channel', lambda: categories(post=page('Connected Alpha to Beta.', channel='alert'), expected=expected_unavailable, details=dict.fromkeys(scorer.CHANNELS, 'NO_CHANNEL')))
    check('missing_poststate_is_unavailable', lambda: categories(post=None, expected=expected_unavailable, details=dict.fromkeys(scorer.CHANNELS, 'NO_CHANNEL')))
    for event, detail in [(outcome.UNDETERMINED, 'UNDETERMINED'), (outcome.UNNAMED, 'UNNAMED')]:
        def undetermined(event=event, detail=detail):
            saved = response(event, rule={connected: vouch(connected)}, listed={connected: vouch(connected)})
            return categories(saved, expected={'decision_list': 'unestablished', 'rule': 'forced_correct', 'list': 'forced_correct'}, details={'decision_list': detail})
        check('decision_list_' + detail.lower(), undetermined)
    def sole(correct):
        event = connected if correct else refused
        saved = response(event, rule={event: vouch(event, sole=True)}, listed={event: vouch(event, sole=True)})
        value = categories(saved, expected={'decision_list': 'correct' if correct else 'wrong', 'rule': 'unestablished', 'list': 'unestablished'})
        for name in ('rule', 'list'):
            require(value['channels'][name]['detail'] == 'SOLE_OBSERVED_VOCABULARY'
                    and value['channels'][name]['sole_correct'] is correct
                    and value['channels'][name]['sole_wrong'] is (not correct), 'Sole vocabulary became forced evidence')
        return value
    check('sole_observed_correct_stays_unestablished', lambda: sole(True))
    check('sole_observed_wrong_stays_unestablished', lambda: sole(False))
    def ambiguous(events, expect_among, pre=before):
        options = {event: vouch(event) for event in events}
        value = categories(response(rule=options, listed=options), pre=pre,
                           expected={'decision_list': 'correct', 'rule': 'ambiguous', 'list': 'ambiguous'})
        for name in ('rule', 'list'):
            require(value['channels'][name]['observed_among'] is expect_among, 'Ambiguous observed membership differs')
        return value
    check('ambiguous_among_retained', lambda: ambiguous([connected, refused], True))
    check('ambiguous_missing_retained', lambda: ambiguous([refused, 'Other event .'], False))
    check('unchanged_ambiguous_wrong_events_not_corroborated', lambda: ambiguous([refused, 'Other event .'], False, after))
    def both_observable():
        value = ambiguous([connected, outcome.SILENT], True, after)
        require(value['channels']['rule']['matching'] == [connected, outcome.SILENT], 'Unchanged standing frame and SILENT comparison differs')
        return value
    check('unchanged_frame_and_silent_both_match_without_forcing', both_observable)
    check('empty_admissible_sets_stay_unestablished', lambda: categories(response(rule={}, listed={}),
          expected={'decision_list': 'correct', 'rule': 'unestablished', 'list': 'unestablished'},
          details={'rule': 'NO_ADMISSIBLE_EVENT', 'list': 'NO_ADMISSIBLE_EVENT'}))
    for status in ['UNREACHABLE', 'NO_PRESTATE', 'NON_CLICK', 'NO_MODEL', 'ERROR']:
        saved = {'schema': 'semabi.j1.forecast.v1', 'status': status, 'instrument_status': 'COMPLETE'}
        check('nonforecast_' + status.lower(), lambda saved=saved, status=status: categories(saved, expected=expected_unavailable, details=dict.fromkeys(scorer.CHANNELS, status)))
    check('missing_forecast_retains_opportunity', lambda: categories(missing=True, expected=expected_unavailable, details=dict.fromkeys(scorer.CHANNELS, 'MISSING_FORECAST')))
    check('incomplete_forecast_retains_opportunity', lambda: categories({'schema': 'semabi.j1.forecast.v1', 'status': 'FORECAST', 'instrument_status': 'INCOMPLETE'},
          expected=expected_unavailable, details=dict.fromkeys(scorer.CHANNELS, 'INCOMPLETE_INSTRUMENT')))
    def novel():
        post = page('Novel Alpha meets Gamma.', names=('Alpha', 'Gamma'))
        value = assess(response('Novel <> meets <> .'), post=post)
        require(value['novel_observed_frame'] is True and value['observed']['frame'] == 'Novel <> meets <> .', 'New observed event was hidden by fitted labels')
        require(value['previously_observed_control_events'] == [connected, refused], 'Saved observed-label inventory changed')
        require(vocab.values == initial_vocab, 'New page values changed trained vocabulary')
        return value
    check('open_event_vocabulary_keeps_new_frame', novel)
    def known_frame():
        value = assess(); require(value['novel_observed_frame'] is False, 'Known observed event labeled novel'); return value
    check('previously_observed_frame_not_novel', known_frame)

    def argument_case(predicted, roles, *, expected_statuses, expected_reasons, post=after, event=connected):
        saved = response(event, arguments={event: predicted}, roles={event: roles})
        value = assess(saved, post=post); entry = value['literal_arguments'][event]
        require([row['status'] for row in entry['rows']] == expected_statuses, 'Literal argument statuses differ')
        require([row['reason'] for row in entry['rows']] == expected_reasons, 'Literal argument reasons differ')
        require(entry['denominator_positions'] == len(expected_statuses), 'Literal position denominator shrank')
        return value
    check('literal_arguments_both_match', lambda: argument_case({0: 'Alpha', 1: 'Beta'}, {0: 'source', 1: 'target'},
          expected_statuses=['matched', 'matched'], expected_reasons=['EXACT_LITERAL', 'EXACT_LITERAL']))
    def wrong_argument():
        value = argument_case({0: 'Alpha', 1: 'Wrong'}, {0: 'source', 1: 'target'}, expected_statuses=['matched', 'mismatched'], expected_reasons=['EXACT_LITERAL', 'EXACT_LITERAL'])
        require(value['channels']['decision_list']['category'] == 'correct', 'Argument mismatch changed frame verdict')
        return value
    check('frame_correct_literal_endpoint_wrong', wrong_argument)
    check('unbound_role_position_is_explicit', lambda: argument_case({0: 'Alpha'}, {0: 'source', 1: 'target'},
          expected_statuses=['matched', 'unavailable'], expected_reasons=['EXACT_LITERAL', 'NO_BOUND_LITERAL']))
    check('missing_role_and_literal_still_keeps_frame_arity', lambda: argument_case({}, {},
          expected_statuses=['unavailable', 'unavailable'], expected_reasons=['NO_BOUND_LITERAL', 'NO_BOUND_LITERAL']))
    check('fresh_requires_independent_creation_control', lambda: argument_case({0: 'Alpha', 1: outcome.FRESH}, {0: 'source', 1: 'created:T1'},
          expected_statuses=['matched', 'unavailable'], expected_reasons=['EXACT_LITERAL', 'FRESH_REQUIRES_SEPARATE_CREATION_CONTROL']))
    check('extra_predicted_position_has_no_observed_argument', lambda: argument_case({0: 'Alpha', 1: 'Beta', 2: 'Extra'}, {0: 'source', 1: 'target', 2: 'extra'},
          expected_statuses=['matched', 'matched', 'unavailable'], expected_reasons=['EXACT_LITERAL', 'EXACT_LITERAL', 'NO_OBSERVED_ARGUMENT_POSITION']))
    check('wrong_frame_does_not_grade_literals', lambda: argument_case({0: 'Alpha', 1: 'Beta'}, {0: 'source', 1: 'target'}, event=refused,
          expected_statuses=['unavailable', 'unavailable'], expected_reasons=['FRAME_NOT_CORROBORATED', 'FRAME_NOT_CORROBORATED']))
    check('no_channel_does_not_grade_literals', lambda: argument_case({0: 'Alpha', 1: 'Beta'}, {0: 'source', 1: 'target'}, post=page('', channel=None),
          expected_statuses=['unavailable', 'unavailable'], expected_reasons=['NO_CHANNEL', 'NO_CHANNEL']))
    def wrong_payload(name):
        value = response()
        if name == 'status': value['status'] = 'INVENTED_UNKNOWN'
        elif name == 'copy_failure': value['incomplete_reasons'] = [{'reason': 'invented'}]
        elif name == 'inventory': value['values']['items'].append(['unexpected', None])
        elif name == 'argument_opportunity':
            for key, item in value['values']['items']:
                if key == 'arguments': item['items'].append(['absent-event', cp({})])
        elif name == 'bool_argument_position':
            for key, item in value['values']['items']:
                if key == 'arguments': item['items'][0][1]['items'][0][0] = False
        elif name == 'missing_event_arguments':
            for key, item in value['values']['items']:
                if key == 'arguments': item['items'].clear()
        return scorer.payload(value)
    for name in ['status', 'copy_failure', 'inventory', 'argument_opportunity', 'bool_argument_position', 'missing_event_arguments']:
        check('payload_' + name, lambda name=name: wrong_payload(name), reject=True)
    def denominator_summary():
        result = scorer.summary(assessed)
        require(result['denominator_opportunities'] == len(assessed), 'Summary dropped an opportunity')
        for channel in scorer.CHANNELS:
            data = result['channels'][channel]
            require(sum(data['categories'].values()) == len(assessed), 'Channel denominator differs')
            require(data['unestablished_reasons'].get('MISSING_FORECAST') == 1
                    and data['unestablished_reasons'].get('INCOMPLETE_INSTRUMENT') == 1, 'Unavailable rows vanished')
        require(result['channels']['rule']['sole_correct'] == result['channels']['rule']['sole_wrong'] == 1, 'Sole-vocabulary counts disappeared')
        return result
    check('all_assessed_opportunity_denominators_preserved', denominator_summary)
    check('empty_summary_keeps_zero_denominator', lambda: scorer.summary([]))
    require(vocab.values == initial_vocab and vocab.frozen is True, 'Final vocabulary changed')
    require(all(sha(ROOT / name) == digest for name, digest in sources.items()), 'Reviewed source changed during controls')
    forbidden = [name for name in sys.modules if name.startswith(('semabi.hidden', 'semabi.env', 'semabi.eval'))]
    require(not forbidden, 'Evaluator modules imported')
    record = {'schema': 'semabi.j1.score_independent_checks.v1',
              'status': 'PASS' if all(row['status'] == 'PASS' for row in rows) else 'FAIL',
              'sources': sources, 'checks': rows, 'counts': dict(Counter(row['status'] for row in rows)),
              'pid': os.getpid(), 'affinity': sorted(os.sched_getaffinity(0)),
              'scope': 'Invented public pages/checkpoints/forecasts, actual native Observation/emission/outcome constants and dataclasses, actual trace Copier with minimal explicit native record bindings. No fit, retrospective query, browser, fixture/evaluator payload or custody CLI.'}
    with args.output.open('x') as stream: json.dump(record, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps({'path': str(args.output), 'sha256': sha(args.output), 'counts': record['counts'], 'failed': [row['name'] for row in rows if row['status'] == 'FAIL']}))
    return 0 if record['status'] == 'PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
