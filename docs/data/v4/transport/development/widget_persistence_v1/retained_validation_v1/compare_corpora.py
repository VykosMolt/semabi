"""Compare W1 to retained B1 outputs and authenticate B1's accepted G2 equality."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
MAIN = Path('/home/moloch/semabi')
B1 = MAIN / 'docs/data/v4/transport/development/b1_validation'
G2 = MAIN / 'docs/data/v4/transport/development/g2'
B1_MANIFEST_SHA = 'af3c7131375798bbf0cc0f4050617cc8ebea901a6313d7be7879f23409597e8d'
B1_SOURCE_SHA = 'c40e565fb6f6fda6116a442a6291ba987e0d2e445ed8d63ec3f58082743b730d'
B1_CORPUS_SHA = '09a2a3babd7b1337cd98affb8d71ea04e43ef48f5118bf5c7e96b62fd593b535'
B1_COMPARISON_SHA = 'ef415af9df5c4d48d658a29fb85209ef32e743e7107b9d62f0782fab516fc981'
G2_MANIFEST_SHA = '481f879db351618431127a8f7a99db1a35ed06975c7f1f325347c9953a80d67e'
COMPARATOR_SHA = '6a4c7eedcfd6143581a8cd75e47c0459b48ac8614657fcf0e0a615d1558ad001'
CASES = {'allocation_positive': ('harbour_join_dev', 'harbour_join_hold'),
         'allocation_refusals': ('harbour_ref_dev', 'harbour_ref_hold'),
         'pilot': ('harbour_pil_dev', 'harbour_pil_hold'),
         'separating': ('harbour_sep_dev', 'harbour_sep_hold'),
         'separating_extended': ('harbour_sep2_dev', 'harbour_sep_hold')}
COMPONENTS = ('reading', 'fit', 'dev_steps', 'outcome_cut', 'development', 'holdout')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_guard(source_sha):
    path = HERE / 'source_freeze_v1.json'
    raw = path.read_bytes()
    require(path.resolve(strict=True) == path and hashlib.sha256(raw).hexdigest() == source_sha,
            'Source freeze authentication failed')
    source = json.loads(raw)
    for path in (Path(__file__).resolve(), HERE / 'validation_guard.py'):
        raw = path.read_bytes()
        require(path.resolve(strict=True) == path and source['verification_files'].get(path.relative_to(ROOT).as_posix())
                == hashlib.sha256(raw).hexdigest(), 'Entry point or shared guard changed')
    guard = types.ModuleType('w1_validation_guard')
    guard.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), guard.__dict__)
    return guard


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--b1-manifest-sha', required=True)
    parser.add_argument('--source-freeze-sha256', required=True)
    parser.add_argument('--corpus-freeze-sha256', required=True)
    args = parser.parse_args()
    require(args.b1_manifest_sha == B1_MANIFEST_SHA, 'Use the accepted B1 preservation manifest')
    guard = load_guard(args.source_freeze_sha256)
    source, w1_freeze, w1_corpus_root = guard.verify(args.source_freeze_sha256, args.corpus_freeze_sha256)
    output = HERE / 'corpus_comparison_v1.json'
    require(not output.exists() and not output.is_symlink(), 'Comparison identity is exclusive')
    roots = {'B1': MAIN, 'G2': MAIN, 'W1': ROOT}
    inputs = {phase: {} for phase in roots}

    def data(phase, path, expected=None):
        require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file(), 'Expected actual input file')
        name = path.relative_to(roots[phase]).as_posix()
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(expected is None or digest == expected, 'Authenticated input changed: ' + phase + ':' + name)
        require(name not in inputs[phase] or inputs[phase][name] == digest, 'Input changed while comparing: ' + name)
        inputs[phase][name] = digest
        return raw

    def read(phase, path, expected=None):
        return json.loads(data(phase, path, expected))

    b1_manifest = read('B1', B1 / 'results_manifest_v1.json', B1_MANIFEST_SHA)
    g2_manifest = read('G2', G2 / 'results_manifest_v1.json', G2_MANIFEST_SHA)
    require(b1_manifest['schema'] == 'semabi.transport.b1_validation_results.v1'
            and b1_manifest['status'] == g2_manifest['status'] == 'PRESERVED'
            and b1_manifest['all_owned_jobs_terminated'] is True
            and g2_manifest['schema'] == 'semabi.transport.g2_results.v1'
            and g2_manifest['all_owned_jobs_terminated'] is True
            and b1_manifest['source_freeze_sha256'] == B1_SOURCE_SHA
            and b1_manifest['corpus_freeze_sha256'] == B1_CORPUS_SHA
            and b1_manifest['corpus_comparison_sha256'] == B1_COMPARISON_SHA
            and b1_manifest['g2_results_manifest_sha256'] == G2_MANIFEST_SHA, 'Invalid accepted baseline preservation chain')

    def preserved(phase, path):
        manifest = b1_manifest if phase == 'B1' else g2_manifest
        entry = manifest['files'][path.relative_to(MAIN).as_posix()]
        require(set(entry) == {'bytes', 'sha256'} and path.stat().st_size == entry['bytes'], 'Preserved artifact size differs')
        return data(phase, path, entry['sha256'])

    b1_source = json.loads(preserved('B1', B1 / 'source_freeze_v1.json'))
    b1_freeze = json.loads(preserved('B1', B1 / 'corpus_freeze_v1.json'))
    chain = json.loads(preserved('B1', B1 / 'corpus_comparison_v1.json'))
    require(sha(B1 / 'source_freeze_v1.json') == B1_SOURCE_SHA and sha(B1 / 'corpus_freeze_v1.json') == B1_CORPUS_SHA
            and sha(B1 / 'corpus_comparison_v1.json') == B1_COMPARISON_SHA, 'Accepted B1 freeze/comparison link differs')
    require(b1_source['source_head'] == b1_freeze['source_head'] == b1_manifest['source_head']
            and b1_source['working_directory'] == b1_manifest['working_directory']
            and chain['schema'] == 'semabi.transport.b1_g2_corpus_comparison.v1'
            and chain['source_freeze_sha256'] == B1_SOURCE_SHA and chain['corpus_freeze_sha256'] == B1_CORPUS_SHA
            and chain['g2_results_manifest_sha256'] == G2_MANIFEST_SHA
            and chain['retained_comparator_sha256'] == COMPARATOR_SHA
            and set(chain['comparisons']) == set(CASES), 'Accepted B1/G2 comparison identity differs')
    for row in chain['comparisons'].values():
        require(row['semantic_payloads_equal'] is True and row['differences'] == []
                and row['components_equal'] == {name: True for name in COMPONENTS}, 'Accepted B1/G2 equality chain differs')
    comparator_path = G2 / 'compare_corpora.py'
    comparator = preserved('G2', comparator_path)
    require(hashlib.sha256(comparator).hexdigest() == COMPARATOR_SHA, 'Retained G2 comparison algorithm changed')
    tree = ast.parse(comparator)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'differences')
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(comparator_path), 'exec'), namespace)
    differences = namespace['differences']
    components = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == 'COMPONENTS' for target in node.targets))
    require(components == COMPONENTS, 'Retained semantic projection changed')
    declared = {'B1': Path(b1_manifest['working_directory']), 'W1': ROOT}
    require(declared['B1'] == Path('/home/moloch/semabi/runs/.b1_validation_worktree')
            and chain['declared_roots'] == {'B1': str(declared['B1']), 'G2': str(MAIN)}, 'Historical baseline roots differ')
    corpus_roots = {phase: root / 'runs/v4/transport_g1_corpora_v1' for phase, root in declared.items()}
    require(corpus_roots['W1'] == w1_corpus_root, 'Candidate corpus routing differs')
    manifest = read('W1', ROOT / source['corpora']['manifest'], source['corpora']['manifest_sha256'])
    require(b1_freeze['corpora'] == source['corpora'], 'B1/W1 persistent input commitments differ')
    for name, digest in manifest['files'].items():
        data('W1', w1_corpus_root / name, digest)
    for path, digest in ((HERE / 'source_freeze_v1.json', args.source_freeze_sha256),
                         (HERE / 'corpus_freeze_v1.json', args.corpus_freeze_sha256)):
        data('W1', path, digest)
    for name, digest in w1_freeze['verification_files'].items():
        data('W1', ROOT / name, digest)
    results = {}
    for case, pair in CASES.items():
        values, consumed, mapped, excluded = {}, {}, {}, {}
        for phase, base, freeze, phase_source, source_sha, corpus_sha in (
            ('B1', B1, b1_freeze, b1_source, B1_SOURCE_SHA, B1_CORPUS_SHA),
            ('W1', HERE, w1_freeze, source, args.source_freeze_sha256, args.corpus_freeze_sha256)):
            directory = base / 'corpora' / case

            def artifact(path):
                return json.loads(preserved(phase, path)) if phase == 'B1' else read(phase, path)

            result = artifact(directory / (case + '.json'))
            fit = artifact(directory / (case + '_fit.json'))
            partial = artifact(directory / (case + '_partial.json'))
            require(fit == {name: result[name] for name in ('provenance', 'reading', 'fit', 'dev_steps', 'outcome_cut')}
                    and partial == {name: result[name] for name in ('provenance', 'reading', 'fit', 'dev_steps', 'outcome_cut', 'development')},
                    'Fit/partial prefixes differ from completed corpus result')
            inner = artifact(directory / (case + '_process.json'))
            snapshot = artifact(directory / 'source_snapshot.json')
            adapter = artifact(directory / 'adapter.json')
            postflight = artifact(directory / 'adapter_postflight.json')
            require(snapshot == freeze and result['provenance']['source_snapshot_sha256']
                    == inner['source_snapshot_sha256'] == sha(directory / 'source_snapshot.json') == corpus_sha,
                    'Result/snapshot/freeze link differs')
            require(inner['state'] == 'completed' and inner['case'] == case and inner['changed_inputs'] == []
                    and inner['result_sha256'] == sha(directory / (case + '.json')), 'Incomplete or changed corpus result')
            measurement = 'docs/data/v4/transport/baseline/check_corpora.py'
            adapter_name = (base / 'run_corpus.py').relative_to(roots[phase]).as_posix()
            require(inner['instrument_sha256'] == adapter['instrument_sha256'] == freeze['verification_files'][measurement]
                    and adapter['adapter_sha256'] == freeze['verification_files'][adapter_name], 'Measurement/adapter source differs')
            require(adapter['source_head'] == freeze['source_head'] and adapter['source_freeze_sha256'] == source_sha
                    and adapter['source_snapshot_sha256'] == corpus_sha
                    and adapter['cwd'] == inner['working_directory'] == str(declared[phase])
                    and adapter['corpus_root'] == str(corpus_roots[phase]), 'Adapter source/input routing differs')
            require(postflight['status'] == 'VERIFIED' and postflight['all_frozen_source_and_inputs_unchanged'] is True
                    and postflight['source_freeze_sha256'] == source_sha
                    and postflight['source_snapshot_sha256'] == corpus_sha, 'Postflight is invalid')
            consumed[phase] = result['provenance']['input_files']
            require(inner['input_files'] == consumed[phase], 'Inner/result consumed maps differ')
            require(result['provenance']['dev'] == inner['dev'] == str(corpus_roots[phase] / pair[0])
                    and result['provenance']['hold'] == inner['hold'] == str(corpus_roots[phase] / pair[1]), 'Case routing differs')
            mapped[phase] = {}
            for name, expected in consumed[phase].items():
                path = Path(name)
                relative = path.relative_to(corpus_roots[phase]).as_posix()
                require(path == corpus_roots[phase] / relative and all(part not in ('', '.', '..') for part in relative.split('/'))
                        and manifest['files'][relative] == expected, 'Unexpected consumed corpus path/hash')
                data('W1', w1_corpus_root / relative, expected)
                mapped[phase][relative] = expected
            require(mapped[phase] == {name: value for name, value in manifest['files'].items() if name.split('/')[0] in pair},
                    'Consumed inventory omitted or added a case input')
            job_path = base / 'jobs' / ('corpus_' + case) / 'process.json'
            job = artifact(job_path)
            require(job['status'] == 'FINISHED' and job['returncode'] == 0 and job['child_terminated'] is True
                    and job['source_head'] == freeze['source_head'] and job['cwd'] == str(declared[phase])
                    and job['child_pid'] == inner['pid'] == adapter['pid'], 'Owned job is incomplete or belongs to another execution')
            script_relative = (base / 'run_corpus.py').relative_to(roots[phase]).as_posix()
            tail = [script_relative, case, str(directory.relative_to(roots[phase])), str((base / 'corpus_freeze_v1.json').relative_to(roots[phase]))]
            command = ['.venv/bin/python', *tail] if phase == 'B1' else [str(MAIN / '.venv/bin/python'), '-B', *tail,
                '--source-freeze-sha256', source_sha, '--corpus-freeze-sha256', corpus_sha]
            require(job['command'] == command, 'Owned corpus command differs')
            require(job['python_hash_seed'] == '0' and job['thread_limits'] == {name: '1' for name in
                ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}, 'Corpus seed/thread settings differ')
            if phase == 'B1':
                preserved(phase, job_path.parent / 'output.log')
            data(phase, job_path.parent / 'output.log', job['log_sha256'])
            require(job['source_hashes'] == phase_source['source_files'], 'Owned source-file hashes differ')
            if phase == 'W1':
                audit_path = directory / 'import_origins_v1.json'
                audit = read(phase, audit_path, postflight['import_origins_sha256'])
                require(audit['scope'] == 'PRIMARY_CORPUS_INTERPRETER' and audit['postflight_status'] == 'VERIFIED'
                        and audit['measurement_returned'] is True and 'execution_error' not in audit
                        and audit['source_head'] == guard.HEAD and audit['source_freeze_sha256'] == source_sha
                        and audit['corpus_freeze_sha256'] == corpus_sha and audit['pid'] == job['child_pid']
                        and audit['cwd'] == str(ROOT) and audit['required_environment'] == adapter['required_environment'] == guard.ENV
                        and audit['dont_write_bytecode'] is True and audit['bytecode_prefix'] == adapter['bytecode_prefix']
                        and audit['affinity'] == adapter['affinity'] and len(audit['affinity']) == 1, 'Candidate origin/execution receipt differs')
                require([row['phase'] for row in audit['snapshots']] == ['candidate_package_anchor', 'before_measurement', 'after_measurement_or_failure'],
                        'Candidate origin boundaries differ')
                for boundary in audit['snapshots']:
                    require(boundary['violations'] == [] and 'semabi' in boundary['modules'], 'Native origin violation or absent package anchor')
                    for name, row in boundary['modules'].items():
                        path = ROOT / row['relative_path']
                        require((name == 'semabi' or name.startswith('semabi.')) and row['path'] == row['spec_origin'] == str(path)
                                and source['source_files'][row['relative_path']] == row['sha256']
                                and row['package_paths'] in ([], [str(path.parent)]), 'Native origin row differs')
                require('semabi.compiler.v2.hypotheses' in audit['snapshots'][-1]['modules'],
                        'Candidate hypotheses origin was not recorded after measurement')
            require(set(result) == {'provenance', *COMPONENTS}, 'Unreviewed semantic component inventory')
            source_run = result['reading']['provenance'].get('source_run')
            require(source_run == str(corpus_roots[phase] / pair[0]), 'Reading source-run routing differs')
            excluded[phase] = {'top_level_execution_provenance': copy.deepcopy(result['provenance']),
                               'reading_provenance_source_run': source_run}
            values[phase] = copy.deepcopy({name: result[name] for name in COMPONENTS})
            values[phase]['reading']['provenance'].pop('source_run', None)
        b1_result_name = (B1 / 'corpora' / case / (case + '.json')).relative_to(MAIN).as_posix()
        g2_result_path = G2 / 'corpora' / case / (case + '.json')
        preserved('G2', g2_result_path)
        require(chain['inputs']['B1'][b1_result_name] == inputs['B1'][b1_result_name]
                and chain['inputs']['G2'][g2_result_path.relative_to(MAIN).as_posix()] == sha(g2_result_path),
                'Accepted equality chain references different B1/G2 result bytes')
        require(mapped['B1'] == mapped['W1'], 'Consumed bytes differ across declared roots')
        rows = differences(values['B1'], values['W1'])
        rows = [{({'G1': 'B1', 'G2': 'W1'}.get(key, key)): value for key, value in row.items()} for row in rows]
        results[case] = {'components_equal': {name: values['B1'][name] == values['W1'][name] for name in COMPONENTS},
            'differences': rows, 'semantic_payloads_equal': values['B1'] == values['W1'],
            'consumed_absolute_paths': consumed, 'consumed_relative_to_declared_roots': mapped,
            'excluded_execution_and_source_run_provenance': excluded}
    guard.verify(args.source_freeze_sha256, args.corpus_freeze_sha256)
    for phase, files in inputs.items():
        for name, digest in files.copy().items():
            data(phase, roots[phase] / name, digest)
    record = {'schema': 'semabi.transport.w1_b1_corpus_comparison.v1', 'inputs': inputs,
        'source_sha256': sha(Path(__file__)), 'source_freeze_sha256': args.source_freeze_sha256,
        'corpus_freeze_sha256': args.corpus_freeze_sha256, 'b1_results_manifest_sha256': B1_MANIFEST_SHA,
        'accepted_b1_g2_chain': {'comparison_sha256': B1_COMPARISON_SHA, 'g2_results_manifest_sha256': G2_MANIFEST_SHA,
            'all_five_semantic_payloads_equal': True, 'qualification': 'Accepted retained-output baseline; B1 historical loaded origins were not recorded and fresh-process helper import gives main precedence. G2 intended source root was main.'},
        'retained_comparator_sha256': COMPARATOR_SHA, 'comparisons': results,
        'artifact_roots': {phase: str(root) for phase, root in roots.items()},
        'declared_original_worktree_roots': {phase: str(root) for phase, root in declared.items()},
        'declared_corpus_roots': {phase: str(root) for phase, root in corpus_roots.items()},
        'projection': 'Exactly the G2 projection: all reading/fit/dev_steps/outcome_cut/development/holdout fields; only top-level execution provenance and reading.provenance.source_run excluded.',
        'routing': 'Historical B1 absolute input paths remain declared provenance. Maps are authenticated against the same45 manifest-relative paths/hashes and byte-identical W1 input copies; original baseline roots are not treated as current artifact locations.',
        'difference_algorithm': 'Unchanged G2 differences() AST; only top-level report labels G1/G2 relabeled B1/W1.',
        'scope': 'Same-seed retained development regression. Every difference retained; no fresh-transfer or equivalence hypothesis is automatically established.'}
    guard.write_json(output, record)
    print(json.dumps({'output': str(output.relative_to(ROOT)), 'sha256': sha(output),
                      'differences': {name: len(row['differences']) for name, row in results.items()}}))


if __name__ == '__main__':
    main()
