"""Focused controls for the corrected checkpoint cat-handle and identity gates."""
from collections import Counter
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[7]
HERE = Path(__file__).resolve().parent
J1 = HERE.parent
HELPER_SHA = '8d22a5d1af9d3d63f8038e0de27d724399521ed71b45f663b50d495273e9e98a'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def require(condition, detail):
    if not condition: raise AssertionError(detail)
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); sys.modules[name] = value
    spec.loader.exec_module(value); return value


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False); parser.add_argument('--custody-sha', required=True); parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(); require(not args.output.exists(), 'Exclusive output already exists')
    require(sha(J1 / 'custody.py') == args.custody_sha and sha(HERE / 'custody_control_checks_v1.py') == HELPER_SHA, 'Reviewed source changed')
    paths = [J1 / name for name in ['custody.py', 'live_io.py', 'live_model.py', 'trace.py']]
    paths += [Path(__file__), HERE / 'custody_control_checks_v1.py']
    paths += sorted((ROOT / 'semabi/compiler').rglob('*.py')) + [ROOT / 'semabi/__init__.py', ROOT / 'semabi/relmodel.py']
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    custody = module('_reviewed_custody_boundary', J1 / 'custody.py')
    model = module('_reviewed_model_boundary', J1 / 'live_model.py')
    helper = module('_immutable_custody_fixture_helpers', HERE / 'custody_control_checks_v1.py')
    sys.path.insert(0, str(ROOT))
    from semabi.compiler.observation import Observation
    from semabi.compiler.browser import Primitive
    from semabi.compiler.evidence import Step
    def observation(name):
        return Observation.from_json({'url': 'http://127.0.0.1/invented', 'nodes': [
            {'i': 0, 'parent': -1, 'role': 'text', 'name': name, 'bbox': [0, 0, 1, 1]}]})
    before, after = observation('Alpha'), observation('Beta')
    training = {'observations': [{'sig': value.structural_signature(), 'obs': value.to_json()} for value in (before, after)],
                'steps': [Step(0, 1, Primitive('reload'), True, None, before.structural_signature(), after.structural_signature(), []).to_json()]}
    rows = []
    with tempfile.TemporaryDirectory(prefix='j1cb_') as temporary:
        root = Path(temporary)
        def case(name, *, cat=False, mutation=None, pid=731, initial=None):
            path = root / (name + '.json'); index = 0 if initial is None else 1
            saved, receipt = helper.checkpoint_fixture(custody, model, training, path, index=index)
            projection = saved['projection']
            if cat:
                projection['stored_key_inventory']['abstractor'] = sorted([*projection['stored_key_inventory']['abstractor'], 'cat'])
                projection['execution_handles']['abstractor']['cat'] = 'derived view_controls handle'
                projection['ownership'].update(cat_has_no_instance_fields=True, cat_view_controls=True)
            if mutation is not None: mutation(saved)
            # Rebind every hash deliberately, so a schema rejection cannot be an incidental stale hash.
            saved['learned_commitment'] = copy.deepcopy(model.learned_view(projection))
            saved['learned_commitment_sha256'] = custody.io.digest(custody.io.json_bytes(saved['learned_commitment'])[:-1])
            helper.write(path, saved); receipt.update(sha256=sha(path), learned_commitment_sha256=saved['learned_commitment_sha256'])
            return custody.checkpoint(path, receipt, index=index, initial=initial, training_records=training, pid=pid)
        def check(name, function, *, reject=False):
            try:
                result = function()
                rows.append({'name': name, 'expected': 'reject' if reject else 'accept', 'status': 'FAIL' if reject else 'PASS',
                             'result': {'ownership': result['projection']['ownership'], 'objects': result['projection']['identity_attestation']['objects']}})
                return result
            except Exception as error:
                rows.append({'name': name, 'expected': 'reject' if reject else 'accept', 'status': 'PASS' if reject else 'FAIL',
                             'exception': type(error).__name__, 'detail': str(error)})
                return None
        initial_cat = check('declared_cat_with_both_native_relationships', lambda: case('valid_cat', cat=True))
        check('same_cat_handle_and_native_objects_later', lambda: case('later_cat', cat=True, initial=initial_cat))
        specifications = [
            ('cat_missing_one_relationship', True, lambda r: r['projection']['ownership'].pop('cat_view_controls'), 731),
            ('cat_false_relationship', True, lambda r: r['projection']['ownership'].update(cat_has_no_instance_fields=False), 731),
            ('cat_extra_relationship', True, lambda r: r['projection']['ownership'].update(unreviewed=True), 731),
            ('cat_declared_but_handle_absent', True, lambda r: r['projection']['execution_handles']['abstractor'].update(cat='absent'), 731),
            ('cat_absent_but_handle_declared', False, lambda r: r['projection']['execution_handles']['abstractor'].update(cat='derived view_controls handle'), 731),
            ('cat_absent_but_relationships_present', False, lambda r: r['projection']['ownership'].update(cat_has_no_instance_fields=True, cat_view_controls=True), 731),
            ('parser_handle_not_none', True, lambda r: r['projection']['execution_handles']['abstractor'].update(parser='unexpected callback'), 731),
            ('object_id_float_alias', False, lambda r: r['projection']['identity_attestation']['objects'].update(graph=1004.0), 731),
            ('object_id_zero', False, lambda r: r['projection']['identity_attestation']['objects'].update(graph=0), 731),
            ('object_id_negative', False, lambda r: r['projection']['identity_attestation']['objects'].update(graph=-1), 731),
            ('caller_pid_bool_alias', False, lambda r: r['projection']['identity_attestation'].update(pid=1), True),
            ('caller_pid_float_alias', False, None, 731.0),
            ('caller_pid_zero', False, lambda r: r['projection']['identity_attestation'].update(pid=0), 0),
            ('caller_pid_negative', False, lambda r: r['projection']['identity_attestation'].update(pid=-1), -1),
            ('stored_field_duplicate', False, lambda r: r['projection']['stored_key_inventory']['fit'].append('reading'), 731),
            ('stored_fields_unsorted', False, lambda r: r['projection']['stored_key_inventory']['fit'].reverse(), 731),
            ('stored_field_nonstring', False, lambda r: r['projection']['stored_key_inventory']['fit'].append(True), 731),
            ('extra_attested_native_object', False, lambda r: r['projection']['identity_attestation']['objects'].update(unreviewed=42), 731),
            ('missing_stored_inventory_with_rebound_hash', False, lambda r: r['projection']['stored_key_inventory'].pop('graph'), 731),
        ]
        for name, cat, mutation, pid in specifications:
            check(name, lambda name=name, cat=cat, mutation=mutation, pid=pid: case(name, cat=cat, mutation=mutation, pid=pid), reject=True)
    require(all(sha(ROOT / name) == digest for name, digest in sources.items()), 'Source changed during focused controls')
    result = {'schema': 'semabi.j1.custody_checkpoint_boundary_checks.v1', 'status': 'PASS' if all(row['status'] == 'PASS' for row in rows) else 'FAIL',
              'sources': sources, 'checks': rows, 'counts': dict(Counter(row['status'] for row in rows)),
              'scope': 'Invented native public raw training objects and checkpoint data only. Every mutated checkpoint commitment/hash is coherently rebound before its rejection check. No fit, prediction, browser, socket service, evaluator payload or custody CLI.'}
    with args.output.open('x') as stream: json.dump(result, stream, indent=2, sort_keys=True); stream.write('\n')
    print(json.dumps({'path': str(args.output), 'sha256': sha(args.output), 'counts': result['counts'], 'failed': [row['name'] for row in rows if row['status'] == 'FAIL']}))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
