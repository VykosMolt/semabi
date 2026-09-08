"""Count saved training units, typed objects and parsed fields without a Fit."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
J1 = HERE.parent.parent
ROOT = J1.parents[5]
PATCH = 'group[_](heading[_],group[](text[_](combobox[_])))'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def size(value):
    if type(value) is list:
        return len(value)
    assert type(value) is dict
    if '$mapping' in value or '$set' in value:
        return len(value['items'])
    assert set(value) == {'$tuple'}
    return len(value['$tuple'])


def main():
    seal = J1 / 'analysis/identity_search_replay_v1/artifact_manifest_v1.json'
    assert sha(seal) == 'c6ecb59ea29510161e56d243bf48fc19cd598e90f1579f00f581d5a6ebbff0ae'
    bindings = {str(seal.relative_to(ROOT)): sha(seal), **read(seal)['files']}
    first_pass = J1 / 'first_pass_manifest_v2.json'
    assert sha(first_pass) == '51b77f306b0c1a79c9db8192226af0743dd91c8a0025123ae73ba3666eadb256'
    original = read(first_pass)['files']
    raw_path = ROOT / 'docs/data/v4/transport/first_pass/join/j1_training_v1/observations.jsonl'
    bindings[str(raw_path.relative_to(ROOT))] = original[str(raw_path.relative_to(ROOT))]
    helper_seal = J1 / 'analysis/saved_training_model_v2/artifact_manifest_v1.json'
    assert sha(helper_seal) == 'd595eb931e6a04fa238b2cd8e9660a678edb3c08f0bffc1b34d48bb774370c78'
    helper_path = helper_seal.with_name('inspect_operators_v1.py')
    bindings[str(helper_path.relative_to(ROOT))] = read(helper_seal)['files'][str(helper_path.relative_to(ROOT))]

    def authenticate():
        for name, digest in bindings.items():
            p = ROOT / name
            assert p.resolve(strict=True) == p and not p.is_symlink() and sha(p) == digest, name
    authenticate()
    spec = importlib.util.spec_from_file_location('_j1_saved_field_reader', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    fields, mapping = helper.fields, helper.mapping
    projection = read(J1 / 'analysis/identity_search_replay_v1/projection_v1.json')
    hypothesis, abstractor = projection['hypotheses'], projection['abstractor']
    raw = [json.loads(line) for line in raw_path.read_bytes().splitlines()]
    by_sig = {row['sig']: row['obs'] for row in raw}
    assert len(raw) == len(by_sig) == 45
    units = []
    patch_nodes = {sig: set() for sig in by_sig}
    for template, encoded in mapping(hypothesis['units']).items():
        unit = fields(encoded, 'v2.hypotheses.UnitHyp')
        instances = [fields(item, 'v2.hypotheses.UnitInstance') for item in unit['instances']]
        units.append({'template': template, 'instances': len(instances), 'key_slot': unit['key_slot'],
                      'key_score': unit['key_score'], 'max_per_obs': unit['max_per_obs'],
                      'slot_names': sorted(mapping(unit['slots'])), 'evidence': unit['evidence']})
        if template == PATCH:
            for instance in instances:
                nodes = by_sig[instance['sig']]['nodes']
                assert next(node for node in nodes if node['i'] == instance['root'])['role'] == 'group'
                descendants = {instance['root']}
                while True:
                    expanded = descendants | {node['i'] for node in nodes if node['parent'] in descendants}
                    if expanded == descendants:
                        break
                    descendants = expanded
                patch_nodes[instance['sig']].update(descendants)
    parsed_counts, radio_counts = [], Counter()
    for sig, encoded in mapping(abstractor['_cache']).items():
        parsed = fields(encoded, 'parse.ParsedObs')
        member_nodes = {key for key, value in parsed['node_instance']['items']}
        parsed_counts.append({'sig': sig, 'instances': len(parsed['instances']), 'statics': size(parsed['statics']),
                              'patch_node_memberships': len(patch_nodes[sig] & member_nodes)})
        for encoded_instance in parsed['instances']:
            instance = fields(encoded_instance, 'parse.Instance')
            for name, value in mapping(instance['slots']).items():
                if name == 'radio:Select receiver':
                    label, checked = helper.sequence(value)
                    assert label == 'Select receiver' and type(checked) is bool
                    radio_counts[str(checked).lower()] += 1
    states, kinds = [], Counter()
    for encoded in projection['snapshots'].values():
        kinds[encoded['$record']] += 1
        if encoded['$record'] != 'semabi.compiler.abstract.AbstractState':
            continue
        state = fields(encoded, 'abstract.AbstractState')
        parsed = fields(state['parsed'], 'parse.ParsedObs')
        objects = [fields(value, 'abstract.AbsObj') for key, value in state['objs']['items']]
        states.append({'objects': len(objects), 'references': sum(size(obj['refs']) for obj in objects),
                       'instances': len(parsed['instances']), 'statics': size(parsed['statics']),
                       'view': size(state['view']), 'partial': state['partial'],
                       'unidentified': size(state['unidentified']), 'provisional': size(state['provisional'])})
    state_distributions = {key: dict(Counter(str(row[key]) for row in states)) for key in states[0]}
    result = {'schema': 'semabi.j1.saved_training_representation_summary.v1',
              'status': 'SAVED_FIELDS_COUNTED', 'source_sha256': sha(Path(__file__)), 'inputs': bindings,
              'raw_observations': len(raw),
              'raw_comboboxes': sum(node['role'] == 'combobox' for row in raw for node in row['obs']['nodes']),
              'unit_types': size(hypothesis['unit_types']), 'units': units,
              'entity_types': size(hypothesis['entity_types']), 'typed_templates': size(hypothesis['tid_of_template']),
              'allowed_templates': size(hypothesis['allowed']), 'reload_pairs': hypothesis['reload_pairs'],
              'persistent_widgets': hypothesis['persistent_widgets'], 'record_splits': size(hypothesis['record_splits']),
              'slot_attachments': size(hypothesis['slot_attachments']), 'parsed_observations': parsed_counts,
              'parsed_radio_values': dict(radio_counts), 'snapshot_kinds': dict(kinds),
              'state_count': len(states), 'state_field_distributions': state_distributions,
              'scope': 'Read-only counts from the exactly matched training projection and original raw observations. No reconstruction of native classes, fitting, prediction, evaluation payload or oracle input.'}
    assert not any(name == 'semabi' or name.startswith('semabi.') for name in sys.modules)
    authenticate()
    out = HERE / 'summary_v1.json'
    with out.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps({'path': str(out), 'sha256': sha(out), 'status': result['status'],
                      'raw_observations': len(raw), 'states': len(states), 'parsed_observations': len(parsed_counts)}))


if __name__ == '__main__':
    main()
