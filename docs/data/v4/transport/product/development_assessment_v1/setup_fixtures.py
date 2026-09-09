"""Evaluator-only ordinary UI fixture construction; run only in coordinated phases.

This runner must never be supplied to an evaluated arm. It uses intended fixture
values as UI input, then separately extracts ordinary visible DOM for read-back.
It does not read learned operations, runtime matching output, databases, network
responses, hidden app state, or supplied record IDs. All app mutations are visible
form fills/checks/saves. Link destinations are taken from current visible links.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
READER = ROOT / 'runs/product_evaluator_v3/check_effects.py'
spec = importlib.util.spec_from_file_location('independent_reader', READER)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

# Ordinary rendered UI properties only. Password values are never captured.
DOM_JS = reader.DOM_JS.replace("nodes.push(node);", """
    if (e.labels) node.labels = Array.from(e.labels).filter(visible).map(x => norm(x.innerText));
    for (const attr of ['aria-label','aria-haspopup','aria-checked','title','placeholder']) {
      if (e.hasAttribute(attr)) node[attr] = e.getAttribute(attr);
    }
    if (e.tagName === 'INPUT') {
      node.input_type = e.type;
      if (e.type !== 'password') node.value = e.value;
      if (['checkbox','radio'].includes(e.type)) node.checked = e.checked;
    }
    if (e.tagName === 'TEXTAREA' || e.tagName === 'SELECT') node.value = e.value;
    if (e.isContentEditable) node.editable = true;
    nodes.push(node);
""")


def descendants(snapshot, root):
    indices = {root['index']}
    for node in snapshot['nodes']:
        if node['parent'] in indices:
            indices.add(node['index'])
    return [node for node in snapshot['nodes'] if node['index'] in indices]


def fixture_records(app, snapshot, fixtures):
    answer = {}
    for name, fields in fixtures.items():
        if app == 'linkding':
            args = {**fields, 'tags':' '.join(fields['tags'])}
            check = reader.record_checks(app, snapshot, args)
            selected = check['selected_records']
        else:
            # Markdown tag spans may split paragraph text, but rendered text is
            # the expected content. Preserve complete paragraph and tag nodes.
            check = reader.record_checks(app, snapshot, {'value':fields['content']})
            selected = check['selected_records']
            for record in selected:
                local = descendants(snapshot, record['root'])
                record['tag_nodes'] = [node for node in local if node['text'] in fields['tags'] or node['text'] in ['#' + tag for tag in fields['tags']]]
                record['all_expected_tags_visible'] = all(any(node['text'] in (tag, '#' + tag) for node in local) for tag in fields['tags'])
        answer[name] = check
    return answer


class Setup:
    def __init__(self, app, phase, hashes):
        self.app, self.phase, self.hashes = app, phase, hashes
        self.started, self.cpu_started = time.monotonic(), reader.cpu_seconds()
        self.path = OUT / 'fixture_setup' / app / (phase + '_' + uuid.uuid4().hex)
        self.path.mkdir(parents=True, mode=0o700)
        plan_path, expected_path = OUT / 'request_plan.json', OUT / 'expected_results.json'
        self.plan, self.expected = json.loads(plan_path.read_text()), json.loads(expected_path.read_text())
        self.limit = self.plan['budgets']['fixture_setup']
        self.fixtures = self.expected['proposed_visible_fixtures'][app]
        incomplete = [p for p in self.path.parent.glob('*/started.json') if not (p.parent / 'result.json').exists()]
        assert not incomplete, 'Prior interrupted setup requires accounting reconciliation before another attempt'
        previous = [json.loads(p.read_text()) for p in self.path.parent.glob('*/result.json')]
        self.previous = {'actions':sum(r['metrics']['actions'] for r in previous),
            'possible_writes':sum(r['metrics']['possible_writes'] for r in previous),
            'elapsed_seconds':sum(r['metrics']['elapsed_seconds'] for r in previous)}
        self.events, self.captures, self.form_checks = [], [], []
        self.session, self.peak, self.stop = None, [0], threading.Event()
        self.result = {'application':app,'phase':phase,'started_at':reader.now(),
            'classification':'Evaluator-only fixture setup, outside evaluated arms',
            'fixture_status':'PROPOSED_NOT_YET_OBSERVED','source_before':self.source_hashes(),
            'source_hashes_required':hashes,'setup_script_sha256':reader.sha(__file__),
            'reader_sha256':reader.sha(READER),
            'inputs':{str(p.relative_to(ROOT)):reader.sha(p) for p in (plan_path,expected_path)},
            'cumulative_previous':self.previous,'limits':self.limit,
            'authorization':'Execute only after root explicitly coordinates this exact app/phase and idle opaque lifecycle state.',
            'manual_assistance':'App-specific ordinary UI fixture runner prepared by evaluator; no model calls inside runner.'}
        assert all(self.result['source_before'][name] == digest for name,digest in hashes.items())
        assert all(value >= 0 for value in self.previous.values())
        (self.path / 'setup_script.py').write_bytes(Path(__file__).read_bytes())
        reader.save(self.path / 'started.json', self.result)
        self.thread = threading.Thread(target=self.monitor,daemon=True)
        self.thread.start()

    def source_hashes(self):
        return {name:reader.sha(ROOT / name) for name in sorted(self.hashes)}

    def monitor(self):
        while not self.stop.is_set():
            table = reader.process_table()
            owned = reader.descendants(table, os.getpid())
            self.peak[0] = max(self.peak[0],sum(table[p]['rss_bytes'] for p in owned if p in table))
            self.stop.wait(0.05)

    def meter(self, kind, possible_write=False, **details):
        actions = len(self.events) + self.previous['actions']
        writes = sum(e['possible_write'] for e in self.events) + self.previous['possible_writes']
        elapsed = time.monotonic()-self.started+self.previous['elapsed_seconds']
        assert actions + 1 <= self.limit['max_actions'], 'Cumulative setup action budget exhausted'
        assert writes + int(possible_write) <= self.limit['max_possible_writes'], 'Cumulative setup possible-write budget exhausted'
        assert elapsed < self.limit['max_seconds'], 'Cumulative setup time budget exhausted'
        event = {'sequence':len(self.events)+1,'at':reader.now(),'kind':kind,'possible_write':int(possible_write),**details}
        self.events.append(event)
        reader.save(self.path / 'events.json', self.events)

    def capture(self, stage):
        assert time.monotonic()-self.started+self.previous['elapsed_seconds'] < self.limit['max_seconds']
        self.session.phase = stage
        self.session.read()
        snapshot = self.session._page.evaluate(DOM_JS)
        snapshot.update(id='fixture_dom_'+uuid.uuid4().hex,captured_at=reader.now())
        path = self.path / (snapshot['id']+'.json')
        reader.save(path,snapshot)
        self.captures.append({'stage':stage,'snapshot_id':snapshot['id'],'snapshot_sha256':reader.sha(path),'url':snapshot['url'],'captured_at':snapshot['captured_at']})
        return snapshot

    def go(self, url, evidence=None):
        self.meter('navigation',url=url,observed_link=evidence)
        self.session._page.goto(url)

    def reload(self):
        self.meter('reload')
        self.session._page.reload()

    def act(self, kind, locator, value=None, **detail):
        assert locator.count() == 1 and locator.is_visible(), 'UI target must be uniquely visible'
        self.meter(kind,True,**detail)
        if kind == 'fill': locator.fill(value)
        elif kind == 'check': locator.set_checked(value)
        elif kind == 'click': locator.click()
        else: raise AssertionError('Unsupported setup action')

    def field(self, label):
        locator = self.session._page.get_by_label(label,exact=True)
        assert locator.count()==1 and locator.is_visible(), 'Expected visible label is unavailable'
        return locator

    def editable(self, expected_content=None):
        locator = self.session._page.locator('textarea:visible, [contenteditable="true"]:visible')
        if expected_content is None:
            assert locator.count()==1, 'Expected one ordinary visible editor'
            return locator
        selected=[]
        for i in range(locator.count()):
            candidate=locator.nth(i)
            value=candidate.input_value() if candidate.evaluate('(e)=>e.tagName')=='TEXTAREA' else candidate.inner_text()
            if value==expected_content: selected.append(candidate)
        assert len(selected)==1, 'Expected one visible populated editor with the observed old content'
        return selected[0]

    def editor_save(self, editor):
        parent=editor
        for _ in range(12):
            parent=parent.locator('xpath=..')
            saves=parent.get_by_role('button',name='Save',exact=True)
            if saves.count()==1 and saves.is_visible(): return saves
        raise AssertionError('No unique Save control in the populated editor ancestry')

    def observed_link(self,snapshot,label,root=None):
        nodes = descendants(snapshot,root) if root else snapshot['nodes']
        candidates = [n for n in nodes if n['tag']=='a' and n['text']==label and n.get('destination')]
        assert len(candidates)==1, 'Expected one currently observed visible link'
        self.go(candidates[0]['destination'],{'snapshot_id':snapshot['id'],'node':candidates[0]})

    def linkding_form(self, stage, expected):
        snapshot = self.capture(stage)
        found = {}
        for label,key in [('URL','url'),('Title','title'),('Description','description'),('Tags','tags')]:
            nodes=[n for n in snapshot['nodes'] if label in n.get('labels',[]) and 'value' in n]
            assert len(nodes)==1, f'Expected one visible {label} field'
            found[key]=nodes[0]
            assert nodes[0]['value']==(' '.join(expected[key]) if key=='tags' else expected[key])
        boxes = [n for n in snapshot['nodes'] if n.get('input_type')=='checkbox' and any('unread' in x.lower() for x in n.get('labels',[]))]
        assert len(boxes)==1 and boxes[0]['checked']==expected['unread'],'Expected unread state unavailable'
        self.form_checks.append({'stage':stage,'snapshot_id':snapshot['id'],'actual_field_nodes':found,'unread_node':boxes[0]})
        return snapshot

    def unread_checkbox(self):
        page=self.session._page
        boxes=page.get_by_role('checkbox')
        selected=[]
        for i in range(boxes.count()):
            box=boxes.nth(i)
            if box.is_visible():
                labels=box.evaluate('(e)=>Array.from(e.labels||[]).map(x=>x.innerText).join(" ")')
                if 'unread' in labels.lower(): selected.append(box)
        assert len(selected)==1, 'Expected exactly one visible unread checkbox'
        return selected[0]

    def create_linkding(self,fields,name):
        current=self.capture('before_create_'+name)
        self.observed_link(current,'Add bookmark')
        self.capture('new_form_'+name)
        for label,key in [('URL','url'),('Title','title'),('Description','description'),('Tags','tags')]:
            self.act('fill',self.field(label),' '.join(fields[key]) if key=='tags' else fields[key],field=label)
        checkbox=self.unread_checkbox()
        if checkbox.is_checked()!=fields['unread']:
            self.act('check',checkbox,fields['unread'],field='Unread')
        self.linkding_form('populated_form_'+name,fields)
        self.act('click',self.session._page.get_by_role('button',name='Save',exact=True),button='Save',business_save=True)
        self.capture('saved_'+name)

    def create_memos(self,fields,name):
        self.capture('before_create_'+name)
        self.act('fill',self.editable(),fields['content'],field='visible memo editor')
        self.capture('populated_editor_'+name)
        self.act('click',self.session._page.get_by_role('button',name='Save',exact=True),button='Save',business_save=True)
        self.capture('saved_'+name)

    def check_records(self,stage,variant):
        snapshot=self.capture(stage)
        checks=fixture_records(self.app,snapshot,self.fixtures[variant])
        self.captures[-1]['fixture_records']=checks
        assert all(r['exact_matching_record_count']==1 for r in checks.values()), 'Fixture values are not each visible once'
        if self.app=='memos':
            assert all(r['selected_records'][0]['all_expected_tags_visible'] for r in checks.values()), 'Fixture tag nodes are not visible'
        if variant=='b_changed':
            old=self.fixtures['base']['B']
            absence=fixture_records(self.app,snapshot,{'old_B':old})['old_B']
            self.captures[-1]['old_B_absence']=absence
            assert absence['exact_matching_record_count']==0, 'Old B record is still visible'
            old_token=self.plan['run_token']+'betafind'
            assert not any(old_token in n['text'] for n in snapshot['nodes']), 'Old B token is still visible'
            if self.app=='linkding':
                assert not any(n.get('destination')==old['url'] for n in snapshot['nodes']), 'Old B URL is still visible'
            self.captures[-1]['old_B_token_absent']=old_token
        return snapshot,checks

    def edit_b(self):
        snapshot,records=self.check_records('before_B_edit','base')
        old,new=self.fixtures['base']['B'],self.fixtures['b_changed']['B']
        if self.app=='linkding':
            self.observed_link(snapshot,'Edit',records['B']['selected_records'][0]['root'])
            self.linkding_form('B_edit_pre_state',old)
            for label,key in [('URL','url'),('Description','description')]:
                self.act('fill',self.field(label),new[key],field=label)
            self.linkding_form('B_edit_populated',new)
        else:
            page=self.session._page
            article=page.locator('article').filter(has=page.get_by_text(old['content'],exact=True))
            assert article.count()==1,'Expected exactly one visible B article'
            menu=article.locator('button[aria-haspopup="menu"]')
            self.act('click',menu,button='B record menu')
            self.capture('B_menu_open')
            self.act('click',page.get_by_role('menuitem',name='Edit',exact=True),button='Edit')
            self.capture('B_editor_pre_state')
            editor=self.editable(old['content'])
            value=editor.input_value() if editor.evaluate('(e)=>e.tagName')=='TEXTAREA' else editor.inner_text()
            assert value==old['content'],'Visible editor pre-state differs'
            self.act('fill',editor,new['content'],field='visible memo editor')
            self.capture('B_editor_populated')
        save=self.editor_save(editor) if self.app=='memos' else self.session._page.get_by_role('button',name='Save',exact=True)
        self.act('click',save,button='Save',business_save=True)

    def run(self):
        own=self
        class Session(reader.MeteredSession):
            def act(self,primitive):
                own.meter('authentication_'+primitive.kind,True)
                return super().act(primitive)
        try:
            url={'linkding':'http://127.0.0.1:8851/','memos':'http://127.0.0.1:8852/'}[self.app]
            self.session=Session(url)
            self.session._page.set_default_timeout(5000)
            self.meter('set_viewport',width=1280,height=900)
            self.session._page.set_viewport_size({'width':1280,'height':900})
            self.go(url)
            self.session.phase='authentication'
            credentials=json.loads((ROOT/f'runs/product_apps_v1/{self.app}/private/credentials.json').read_text())
            self.result['authentication']=self.session.authenticate({k:credentials[k] for k in ('username','password')})
            credentials.clear()
            assert self.result['authentication']=={'status':'CONNECTED','authentication_actions':3}
            initial=self.capture('initial')
            if self.phase=='base':
                assert not any(self.plan['run_token'] in n['text'] for n in initial['nodes']), 'Proposed fixture token already visible'
                for name,fields in self.fixtures['base'].items():
                    (self.create_linkding if self.app=='linkding' else self.create_memos)(fields,name)
            else: self.edit_b()
            snapshot,records=self.check_records('before_reload',self.phase)
            self.reload()
            snapshot,records=self.check_records('after_reload',self.phase)
            if self.app=='linkding':
                # Inspect actual persisted unread checkbox state through each
                # currently observed Edit link; navigation performs no save.
                listing=snapshot['url']
                for name,fields in self.fixtures[self.phase].items():
                    self.observed_link(snapshot,'Edit',records[name]['selected_records'][0]['root'])
                    self.linkding_form('persisted_'+name,fields)
                    self.go(listing,{'snapshot_id':snapshot['id'],'basis':'previously observed rendered listing URL'})
                    snapshot,records=self.check_records('return_from_persisted_'+name,self.phase)
            self.result.update(verdict='PASS',fixture_status='OBSERVED_IN_ORDINARY_UI')
        except Exception as exc:
            self.result.update(verdict='ERROR',error_type=type(exc).__name__)
            if isinstance(exc,AssertionError): self.result['error']=str(exc)[:300]
            if self.session is not None:
                try: self.capture('error_diagnostic')
                except Exception: pass
        finally:
            self.finish()
        return self.result

    def finish(self):
        if self.session is not None:
            table=reader.process_table()
            owned=[table[p] for p in sorted(reader.descendants(table,os.getpid())-{os.getpid()})]
            self.result['session_counts']={'authentication_primitives':self.session.primitives,'read_calls':self.session.read_calls,'raw_snapshot_reads':self.session.raw_snapshot_calls,'main_frame_navigation_events':self.session.main_frame_navigations}
            self.session.close()
            deadline=time.monotonic()+5
            while True:
                after=reader.process_table()
                live=[p for p in owned if p['pid'] in after and p['start_ticks']==after[p['pid']]['start_ticks'] and after[p['pid']]['state']!='Z']
                if not live or time.monotonic()>=deadline:break
                time.sleep(0.05)
            receipts=[]
            for p in owned:
                current=after.get(p['pid'])
                state='absent' if current is None else 'pid_reused' if current['start_ticks']!=p['start_ticks'] else 'zombie_terminated' if current['state']=='Z' else 'still_live'
                receipts.append({**{k:p[k] for k in ('pid','ppid','name','start_ticks')},'after_close':state})
            self.result['termination']={'close_returned':True,'checked_at':reader.now(),'owned_processes':receipts,'live_owned_process_count':len(live)}
            if live:self.result['verdict']='ERROR_BROWSER_STILL_LIVE'
        self.stop.set();self.thread.join()
        metrics={'actions':len(self.events),'possible_writes':sum(e['possible_write'] for e in self.events),
            'business_save_clicks':sum(e.get('business_save',False) for e in self.events),
            'elapsed_seconds':round(time.monotonic()-self.started,3),'cpu_seconds':round(reader.cpu_seconds()-self.cpu_started,3),
            'peak_aggregate_rss_bytes':self.peak[0],'cpu_affinity':sorted(os.sched_getaffinity(0)),
            'independent_dom_reads':len(self.captures),'fresh_browser_sessions':1,'model_calls':0,'paid_cost':0,'retries':0,'setup_resets':0,
            'viewport':{'width':1280,'height':900}}
        cumulative={k:self.previous[k]+metrics[k] for k in self.previous}
        self.result.update(metrics=metrics,cumulative_after=cumulative,events=self.events,captures=self.captures,
            form_checks=self.form_checks,source_after=self.source_hashes(),completed_at=reader.now())
        self.result['source_unchanged']=self.result['source_before']==self.result['source_after']
        if not self.result['source_unchanged']: self.result['verdict']='ERROR_SOURCE_CHANGED'
        if cumulative['actions']>self.limit['max_actions'] or cumulative['possible_writes']>self.limit['max_possible_writes'] or cumulative['elapsed_seconds']>self.limit['max_seconds']:
            self.result['verdict']='ERROR_CUMULATIVE_BUDGET_EXCEEDED'
        reader.save(self.path/'result.json',self.result)
        print(json.dumps({'application':self.app,'phase':self.phase,'verdict':self.result['verdict'],'result_path':str((self.path/'result.json').relative_to(ROOT)),'cumulative_after':cumulative,'live_owned_processes':self.result.get('termination',{}).get('live_owned_process_count')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--application',choices=('memos','linkding'),required=True)
    parser.add_argument('--phase',choices=('base','b_changed'),required=True)
    parser.add_argument('--source-hashes',type=Path,required=True)
    args=parser.parse_args()
    Setup(args.application,args.phase,json.loads(args.source_hashes.read_text())).run()
