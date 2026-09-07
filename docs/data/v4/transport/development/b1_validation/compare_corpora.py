"""Compare preserved G2 and completed B1 corpus outputs under the G2 projection."""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
MAIN = Path('/home/moloch/semabi')
G2 = MAIN / 'docs/data/v4/transport/development/g2'
HEAD = '96b2d1f0efa573e675739f2d230b1e2245c088d5'
SOURCE_SHA = 'c40e565fb6f6fda6116a442a6291ba987e0d2e445ed8d63ec3f58082743b730d'
CORPUS_SHA = '09a2a3babd7b1337cd98affb8d71ea04e43ef48f5118bf5c7e96b62fd593b535'
G2_SHA = '3f88423e84622313263c097a289fb4c8fddb2a0d8d2d56176186229759848df6'
COMPARATOR_SHA = '6a4c7eedcfd6143581a8cd75e47c0459b48ac8614657fcf0e0a615d1558ad001'
CASES = {
    'allocation_positive': ('harbour_join_dev', 'harbour_join_hold'),
    'allocation_refusals': ('harbour_ref_dev', 'harbour_ref_hold'),
    'pilot': ('harbour_pil_dev', 'harbour_pil_hold'),
    'separating': ('harbour_sep_dev', 'harbour_sep_hold'),
    'separating_extended': ('harbour_sep2_dev', 'harbour_sep_hold'),
}
COMPONENTS = ('reading', 'fit', 'dev_steps', 'outcome_cut', 'development', 'holdout')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--g2-manifest-sha', required=True)
    args = parser.parse_args()
    require(len(args.g2_manifest_sha) == 64 and all(c in '0123456789abcdef' for c in args.g2_manifest_sha), 'Expected the approved G2 preservation SHA-256')
    output = HERE / 'corpus_comparison_v1.json'
    require(not output.exists() and not output.is_symlink(), 'Comparison identities are exclusive')
    require(subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == HEAD, 'B1 source HEAD changed')
    roots = {'G2': MAIN, 'B1': ROOT}
    inputs = {phase: {} for phase in roots}

    def data(phase, path, expected=None):
        require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file(), 'Expected an actual input file')
        name = path.relative_to(roots[phase]).as_posix()
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        require(expected is None or actual == expected, 'Changed authenticated input: ' + phase + ':' + name)
        require(name not in inputs[phase] or inputs[phase][name] == actual, 'Input changed while comparing: ' + name)
        inputs[phase][name] = actual
        return raw

    def read(phase, path, expected=None):
        return json.loads(data(phase, path, expected))

    comparison_source_sha = hashlib.sha256(data('B1', Path(__file__).resolve())).hexdigest()
    source = read('B1', HERE / 'source_freeze_v1.json', SOURCE_SHA)
    b1_freeze = read('B1', HERE / 'corpus_freeze_v1.json', CORPUS_SHA)
    g2_freeze = read('G2', G2 / 'freeze_v1.json', G2_SHA)
    g2_manifest = read('G2', G2 / 'results_manifest_v1.json', args.g2_manifest_sha)
    require(source['schema'] == 'semabi.transport.b1_validation_freeze.v1'
            and b1_freeze['schema'] == 'semabi.transport.b1_corpus_freeze.v1'
            and source['source_head'] == b1_freeze['source_head'] == HEAD, 'Wrong B1 freeze')
    require(b1_freeze['source_freeze'] == {'path': (HERE / 'source_freeze_v1.json').relative_to(ROOT).as_posix(), 'sha256': SOURCE_SHA}
            and b1_freeze['files'] == source['files'] and b1_freeze['corpora'] == source['corpora'], 'B1 source/corpus extension changed')
    require(g2_freeze['schema'] == 'semabi.transport.g2_development_freeze.v1'
            and g2_manifest['schema'] == 'semabi.transport.g2_results.v1'
            and g2_manifest['status'] == 'PRESERVED'
            and g2_manifest['source_head'] == g2_freeze['source_head']
            and g2_manifest['freeze_sha256'] == G2_SHA
            and g2_manifest['all_owned_jobs_terminated'] is True, 'G2 result is not an authenticated completed preservation')
    for name, expected in source['source_files'].items():
        data('B1', ROOT / name, expected)
    require({path.relative_to(ROOT).as_posix() for path in (ROOT / 'semabi').rglob('*.py')} == set(source['source_files']), 'B1 source inventory differs')
    for name, expected in b1_freeze['verification_files'].items():
        data('B1', ROOT / name, expected)

    def preserved_g2(path):
        name = path.relative_to(MAIN).as_posix()
        entry = g2_manifest['files'][name]
        require(set(entry) == {'sha256', 'bytes'} and path.stat().st_size == entry['bytes'], 'G2 preserved artifact size differs')
        return data('G2', path, entry['sha256'])

    comparator_path = G2 / 'compare_corpora.py'
    comparator = preserved_g2(comparator_path)
    require(hashlib.sha256(comparator).hexdigest() == COMPARATOR_SHA, 'Retained comparison algorithm changed')
    tree = ast.parse(comparator)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'differences')
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(comparator_path), 'exec'), namespace)
    differences = namespace['differences']
    retained_components = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                               and any(isinstance(target, ast.Name) and target.id == 'COMPONENTS' for target in node.targets))
    require(retained_components == COMPONENTS, 'Retained semantic projection changed')
    manifests = {}
    corpus_roots = {}
    for phase, freeze in (('G2', g2_freeze), ('B1', b1_freeze)):
        metadata = freeze['corpora']
        require(metadata['root'] == 'runs/v4/transport_g1_corpora_v1', 'Unexpected phase input root')
        path = roots[phase] / metadata['manifest']
        manifests[phase] = read(phase, path, metadata['manifest_sha256'])
        corpus_roots[phase] = roots[phase] / metadata['root']
        require(manifests[phase]['root'] == metadata['root'] and len(manifests[phase]['files']) == 45, 'Wrong persistent input inventory')
    require(manifests['G2'] == manifests['B1'], 'Persistent corpus manifests differ')
    for phase in roots:
        for name, expected in manifests[phase]['files'].items():
            data(phase, corpus_roots[phase] / name, expected)

    results = {}
    for case, pair in CASES.items():
        values, consumed, mapped, excluded = {}, {}, {}, {}
        for phase, base, freeze, freeze_name in (
            ('G2', G2, g2_freeze, 'freeze_v1.json'),
            ('B1', HERE, b1_freeze, 'corpus_freeze_v1.json')):
            directory = base / 'corpora' / case
            artifact_names = (case + '.json', case + '_process.json', 'source_snapshot.json', 'adapter.json')
            if phase == 'G2':
                for name in artifact_names:
                    preserved_g2(directory / name)
            result = read(phase, directory / (case + '.json'))
            inner = read(phase, directory / (case + '_process.json'))
            snapshot = read(phase, directory / 'source_snapshot.json')
            adapter = read(phase, directory / 'adapter.json')
            require(snapshot == freeze and result['provenance']['source_snapshot_sha256'] == inner['source_snapshot_sha256']
                    == sha(directory / 'source_snapshot.json') == sha(base / freeze_name), 'Result/snapshot/freeze link differs')
            require(inner['state'] == 'completed' and inner['case'] == case and inner['changed_inputs'] == []
                    and inner['result_sha256'] == sha(directory / (case + '.json')), 'Corpus result is incomplete or changed')
            measurement = 'docs/data/v4/transport/baseline/check_corpora.py'
            require(inner['instrument_sha256'] == adapter['instrument_sha256'] == freeze['verification_files'][measurement], 'Measurement source differs')
            require(adapter['adapter_sha256'] == freeze['verification_files'][(base / 'run_corpus.py').relative_to(roots[phase]).as_posix()], 'Adapter source differs')
            require(adapter['corpus_root'] == str(corpus_roots[phase]), 'Adapter input routing differs')
            if phase == 'B1':
                postflight = read(phase, directory / 'adapter_postflight.json')
                require(postflight['status'] == 'VERIFIED' and postflight['all_frozen_source_and_inputs_unchanged'] is True
                        and postflight['source_freeze_sha256'] == SOURCE_SHA and postflight['source_snapshot_sha256'] == CORPUS_SHA,
                        'B1 postflight is absent or invalid')
            consumed[phase] = result['provenance']['input_files']
            require(inner['input_files'] == consumed[phase], 'Inner/result consumed maps differ')
            require(result['provenance']['dev'] == str(corpus_roots[phase] / pair[0])
                    and result['provenance']['hold'] == str(corpus_roots[phase] / pair[1]), 'Development/holdout routing differs')
            mapped[phase] = {}
            for name, expected in consumed[phase].items():
                path = Path(name)
                relative = path.relative_to(corpus_roots[phase]).as_posix()
                require(path == corpus_roots[phase] / relative and manifests[phase]['files'][relative] == expected, 'Unexpected consumed corpus path/hash')
                data(phase, path, expected)
                mapped[phase][relative] = expected
            expected_consumed = {name: expected for name, expected in manifests[phase]['files'].items() if name.split('/')[0] in pair}
            require(mapped[phase] == expected_consumed, 'Consumed inventory omitted or added a case input')
            job_path = base / 'jobs' / ('corpus_' + case) / 'process.json'
            if phase == 'G2':
                preserved_g2(job_path)
                preserved_g2(job_path.parent / 'output.log')
            job = read(phase, job_path)
            require(job['status'] == 'FINISHED' and job['returncode'] == 0 and job['child_terminated'] is True
                    and job['source_head'] == freeze['source_head'] and job['cwd'] == str(roots[phase]), 'Owned job is incomplete or belongs to another source')
            command = ['.venv/bin/python'] + (['-B'] if phase == 'G2' else []) + [str((base / 'run_corpus.py').relative_to(roots[phase])),
                       case, str(directory.relative_to(roots[phase])), str((base / freeze_name).relative_to(roots[phase]))]
            require(job['command'] == command, 'Owned corpus command differs')
            require(job['python_hash_seed'] == '0' and job['thread_limits'] == {name: '1' for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}, 'Corpus seed/thread settings differ')
            data(phase, job_path.parent / 'output.log', job['log_sha256'])
            for name, expected in freeze['files'].items():
                if name.startswith('semabi/'):
                    require(job['source_hashes'][name] == expected, 'Owned job used a different native source')
            require(set(result) == {'provenance', *COMPONENTS}, 'Unreviewed semantic component inventory')
            source_run = result['reading']['provenance'].get('source_run')
            require(source_run == str(corpus_roots[phase] / pair[0]), 'Reading source-run routing differs')
            excluded[phase] = {'top_level_execution_provenance': copy.deepcopy(result['provenance']),
                               'reading_provenance_source_run': source_run}
            values[phase] = copy.deepcopy({key: result[key] for key in COMPONENTS})
            values[phase]['reading']['provenance'].pop('source_run', None)
        require(mapped['G2'] == mapped['B1'], 'Consumed bytes differ across explicitly routed worktrees')
        rows = differences(values['G2'], values['B1'])
        rows = [{({'G1': 'G2', 'G2': 'B1'}.get(key, key)): value for key, value in row.items()} for row in rows]
        results[case] = {'components_equal': {key: values['G2'][key] == values['B1'][key] for key in COMPONENTS},
                         'differences': rows, 'semantic_payloads_equal': values['G2'] == values['B1'],
                         'consumed_absolute_paths': consumed, 'consumed_relative_to_declared_roots': mapped,
                         'excluded_execution_and_source_run_provenance': excluded}
    for phase, files in inputs.items():
        for name, expected in files.copy().items():
            data(phase, roots[phase] / name, expected)
    record = {'schema': 'semabi.transport.b1_g2_corpus_comparison.v1', 'inputs': inputs,
              'source_sha256': comparison_source_sha, 'source_freeze_sha256': SOURCE_SHA,
              'corpus_freeze_sha256': CORPUS_SHA, 'g2_results_manifest_sha256': args.g2_manifest_sha,
              'retained_comparator_sha256': COMPARATOR_SHA, 'comparisons': results,
              'declared_roots': {phase: str(root) for phase, root in roots.items()},
              'projection': 'Exactly the G2 projection: all reading/fit/dev_steps/outcome_cut/development/holdout fields; only top-level execution provenance and reading.provenance.source_run excluded.',
              'routing': 'Absolute consumed paths are retained and mapped only by their explicitly declared phase corpus root to the same45 manifest-relative paths/hashes. No semantic value or row normalization.',
              'difference_algorithm': 'Unchanged G2 differences() AST; only top-level report labels G1/G2 are relabeled G2/B1.',
              'scope': 'Same-seed retained development regression. Every difference retained; no fresh-transfer or equivalence hypothesis is automatically established.'}
    with output.open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'output': str(output.relative_to(ROOT)), 'sha256': sha(output),
                      'differences': {name: len(row['differences']) for name, row in results.items()}}))


if __name__ == '__main__':
    main()
