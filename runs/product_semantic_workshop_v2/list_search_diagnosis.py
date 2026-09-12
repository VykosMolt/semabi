#!/usr/bin/env python3
"""Bounded offline search replay on exact fitted evidence and live query literals.

No application actions, ontology fitting, artifact mutation, or increased runtime
policy budget. Larger search budgets here are disclosed diagnostics only.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from time import monotonic

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--database', type=Path, required=True)
parser.add_argument('--report', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--budget', type=int, action='append', required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.source.resolve()))
from semabi.compiler.semantic import SemanticArtifact
from semabi.compiler.v4 import outcome

job = json.loads(args.report.read_text())['invocation_job']
request = job['request']
simulation = job['result'].get('counterfactual') or job['result']['prediction']
prediction = simulation['prediction']
with sqlite3.connect(f'file:{args.database}?mode=ro', uri=True) as db:
    stored = db.execute('SELECT artifact FROM operations WHERE connection_id=? AND id=? AND version=?',
        (job['connection_id'], request['operation_id'], request['version'])).fetchone()[0]
model = SemanticArtifact.from_json(json.loads(stored)['support']['semantic_artifact']).outcomes[prediction['control']]
literals = {tuple(literal) for literal in prediction['literals']}
results = []
for budget in args.budget:
    start = monotonic()
    answer = model.admissibility(literals, corroborated=True, hypothesis=outcome.LIST, search_budget=budget)
    results.append({'budget': budget, 'seconds': monotonic() - start, 'complete': answer.complete,
                    'alternatives': {event: asdict(vouch) for event, vouch in answer.options.items()},
                    'work': answer.work, 'witnesses': answer.witnesses})
    print(json.dumps({key: results[-1][key] for key in ('budget', 'seconds', 'complete', 'work')}
                     | {'alternatives': sorted(answer.options)}), flush=True)
output = {'boundary': __doc__.strip(), 'application_actions': 0, 'fits': 0,
          'source': str(args.source), 'outcome_sha256': hashlib.sha256(Path(outcome.__file__).read_bytes()).hexdigest(),
          'operation_version': request['version'], 'rows': len(model.evidence.events),
          'literal_count': len(literals), 'live_prediction': {key: prediction.get(key) for key in
              ('status', 'point', 'reason', 'search', 'alternatives_complete')},
          'results': results}
with args.output.open('x') as stream:
    json.dump(output, stream, indent=2, default=lambda value: sorted(value) if isinstance(value, (set, frozenset)) else str(value))
    stream.write('\n')
