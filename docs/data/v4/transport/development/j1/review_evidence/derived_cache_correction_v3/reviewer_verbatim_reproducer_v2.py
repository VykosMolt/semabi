from __future__ import annotations
import copy, hashlib, importlib.util, json
from pathlib import Path
SOURCE = Path('docs/data/v4/transport/development/j1/live_model.py')
EXPECTED = 'b83ff047ad79350774c142817789c75708f6b3f025d7b46b83f4744233a4bc96'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
spec = importlib.util.spec_from_file_location('_independent_cache_swap', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
fields = {'events':['A','A'], 'masks':[1,1], 'by_event':{'$mapping':'dict','items':[['A',[0,1]]]}, '_blocks':None}
empty = {'$record':m.EVIDENCE_RECORD, 'fields':fields}
populated = copy.deepcopy(empty)
populated['fields']['_blocks'] = [{'$tuple':[1,3,'A']}]
inline_before = {'common':{}, 'snapshots':{}, 'records':[empty,populated]}
inline_after = {'common':{}, 'snapshots':{}, 'records':[populated,empty]}
inline_summaries = [m.evidence_cache_summary(x) for x in (inline_before,inline_after)]
empty_address, populated_address = m.trace.sha(empty), m.trace.sha(populated)
def common(refs):
    return {'abstractor':{'_cache':{},'_assigned':{}}, 'hypotheses':{'_page_instances':{}}, 'logical_outcomes':refs}
base = {'stored_key_inventory':{}, 'graph_frozen':{}, 'graph_policy':{}, 'execution_handles':{}, 'snapshots':{empty_address:empty,populated_address:populated}}
ref_before = {**base, 'common':common([{'$snapshot':empty_address},{'$snapshot':populated_address}])}
ref_after = {**base, 'common':common([{'$snapshot':populated_address},{'$snapshot':empty_address}])}
ref_summaries = [m.evidence_cache_summary(x) for x in (ref_before,ref_after)]
learned_equal = m.trace.canonical(m.learned_view(ref_before)) == m.trace.canonical(m.learned_view(ref_after))
assert inline_before != inline_after and inline_summaries[0] == inline_summaries[1]
assert ref_before != ref_after and learned_equal and ref_summaries[0] == ref_summaries[1]
print(json.dumps({'schema':'semabi.j1.independent_cache_swap_reproducer.v1','source_sha256':EXPECTED,'inline_summary_equal':True,'referenced_summary_equal':True,'referenced_learned_equal':learned_equal,'empty_address':empty_address,'populated_address':populated_address,'summary':ref_summaries[0]},sort_keys=True))
