"""Independent ordinary-DOM pre/post evidence for one requested update.

Prepared separately from the learner. Execute only after the root freezes the
source and authorizes the relevant capture phase. No business write is made.
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
OUT = ROOT / 'runs/product_menu_linkding_evaluator_v2'
READER = ROOT / 'runs/product_evaluator_v3/check_effects.py'
spec = importlib.util.spec_from_file_location('independent_v3_reader', READER)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def source_hashes(expected_hashes):
    return {name:reader.sha(ROOT / name) for name in sorted(set(reader.SOURCE_PATHS) | set(expected_hashes))}


def prior_observed_values():
    prior_path = ROOT / 'runs/product_record_evaluator_v1/after/result.json'
    prior = json.loads(prior_path.read_text())
    expectations, provenance = {}, []
    assert prior['verdict'] == 'PASS' and len(prior['captures']) == 2
    for item in prior['captures']:
        snapshot_path = prior_path.parent / (item['snapshot_id'] + '.json')
        assert reader.sha(snapshot_path) == item['snapshot_sha256']
        snapshot = json.loads(snapshot_path.read_text())
        observed = {}
        for name, record in item['records'].items():
            assert record['exact_matching_record_count'] == len(record['selected_records']) == 1
            selected = record['selected_records'][0]
            root = selected['root']
            assert root == snapshot['nodes'][root['index']] and root['tag'] == 'li'
            for key in ('title_and_destination_nodes', 'tag_nodes', 'description_nodes'):
                assert len(selected[key]) == 1
                node = selected[key][0]
                assert node == snapshot['nodes'][node['index']]
                cursor = node['index']
                while cursor >= 0 and cursor != root['index']:
                    cursor = snapshot['nodes'][cursor]['parent']
                assert cursor == root['index'], 'Field must share the observed native record ancestor'
            title = selected['title_and_destination_nodes'][0]
            observed[name] = {'url':title['destination'], 'title':title['text'],
                'tags':selected['tag_nodes'][0]['text'],
                'description':selected['description_nodes'][0]['own_text']}
        if expectations:
            assert expectations == observed
        expectations = observed
        provenance.append({key:item[key] for key in ('snapshot_id','snapshot_sha256','stage','captured_at')})
    return expectations, {'result_path':str(prior_path.relative_to(ROOT)),
        'result_sha256':reader.sha(prior_path), 'captures':provenance,
        'derivation':'Actual captured title text/destination, tag text, description own_text; raw-node equality and shared native ancestor verified; both captures agree'}


def capture(expected_hashes):
    phase = 'read_check'
    source_before = source_hashes(expected_hashes)
    assert all(source_before[name] == expected for name, expected in expected_hashes.items())
    expectations, provenance = prior_observed_values()
    path = OUT / phase
    assert not (path / 'result.json').exists(), 'Capture phase already has a result; do not silently overwrite it'
    credentials = json.loads((ROOT / 'runs/product_apps_v1/linkding/private/credentials.json').read_text())
    credentials = {key:credentials[key] for key in ('username', 'password')}
    started, cpu_start, peak_rss = time.monotonic(), reader.cpu_seconds(), [0]
    stop_monitor = threading.Event()

    def monitor():
        while not stop_monitor.is_set():
            table = reader.process_table()
            owned = reader.descendants(table, os.getpid())
            peak_rss[0] = max(peak_rss[0], sum(table[pid]['rss_bytes'] for pid in owned if pid in table))
            stop_monitor.wait(0.05)

    monitoring = threading.Thread(target=monitor, daemon=True)
    monitoring.start()
    session, captures = None, []
    result = {'phase':phase, 'started_at':reader.now(), 'application':'linkding',
              'expectations':expectations, 'source_before':source_before,
              'reader_source':str(READER.relative_to(ROOT)), 'reader_sha256':reader.sha(READER),
              'capture_script_sha256':reader.sha(__file__),
              'expected_state_provenance':provenance,
              'method':'Unchanged independent v3 visible-DOM extraction and same-record matching; ordinary UI authentication only'}
    try:
        session = reader.MeteredSession('http://127.0.0.1:8851/')
        session.phase = 'navigation'
        session.goto()
        session.phase = 'authentication'
        result['authentication'] = session.authenticate(credentials)
        credentials.clear()
        assert result['authentication'] == {'status':'CONNECTED', 'authentication_actions':3}, 'Fresh authentication failed'
        for stage in ('before_reload', 'after_reload'):
            session.phase = stage
            if stage == 'after_reload':
                session.reload()
            else:
                session.read()
            snapshot = session._page.evaluate(reader.DOM_JS)
            snapshot.update(id='eval_dom_' + uuid.uuid4().hex, captured_at=reader.now())
            snapshot_path = path / (snapshot['id'] + '.json')
            reader.save(snapshot_path, snapshot)
            captures.append({'stage':stage, 'snapshot_id':snapshot['id'],
                'snapshot_sha256':reader.sha(snapshot_path), 'captured_at':snapshot['captured_at'],
                'url':snapshot['url'],
                'records':{name:reader.record_checks('linkding', snapshot, fields)
                           for name, fields in expectations.items()}})
        result['captures'] = captures
        result['verdict'] = ('PASS' if all(record['exact_matching_record_count'] == 1
                            for item in captures for record in item['records'].values()) else 'UNESTABLISHED')
    except Exception as exc:
        result.update(verdict='ERROR', error_type=type(exc).__name__)
    finally:
        if session is not None:
            table = reader.process_table()
            owned = [table[pid] for pid in sorted(reader.descendants(table, os.getpid()) - {os.getpid()})]
            result['metrics'] = {
                'authentication_primitives':len(session.primitives), 'primitive_kinds':session.primitives,
                'requested_navigations':1, 'requested_reloads':int(len(captures) == 2),
                'main_frame_navigation_events':session.main_frame_navigations,
                'business_write_primitives':0, 'conservative_possible_write_primitives':len(session.primitives),
                'interaction_total_including_auth_navigation_reload':len(session.primitives)+1+int(len(captures)==2),
                'browser_session_read_calls_by_phase':session.read_calls,
                'browser_session_raw_snapshot_reads_by_phase':session.raw_snapshot_calls,
                'independent_dom_reads':len(captures), 'model_calls':0, 'paid_cost':0,
                'retries':0, 'fresh_browser_sessions':1, 'setup_resets':0,
                'cpu_affinity':sorted(os.sched_getaffinity(0)),
            }
            close_started = reader.now()
            session.close()
            deadline = time.monotonic() + 5
            while True:
                after = reader.process_table()
                live = [proc for proc in owned if (proc['pid'] in after
                    and after[proc['pid']]['start_ticks'] == proc['start_ticks']
                    and after[proc['pid']]['state'] != 'Z')]
                if not live or time.monotonic() >= deadline:
                    break
                time.sleep(0.05)
            receipts = []
            for proc in owned:
                current = after.get(proc['pid'])
                state = ('absent' if current is None else 'pid_reused' if current['start_ticks'] != proc['start_ticks']
                         else 'zombie_terminated' if current['state'] == 'Z' else 'still_live')
                receipts.append({**{key:proc[key] for key in ('pid','ppid','name','start_ticks')}, 'after_close':state})
            result['termination'] = {'close_started_at':close_started, 'checked_at':reader.now(),
                'close_returned':True, 'owned_processes':receipts, 'live_owned_process_count':len(live)}
            if live:
                result['verdict'] = 'ERROR_BROWSER_STILL_LIVE'
        stop_monitor.set()
        monitoring.join()
        result.setdefault('metrics', {}).update(elapsed_seconds=round(time.monotonic()-started, 3),
            cpu_seconds=round(reader.cpu_seconds()-cpu_start, 3), peak_aggregate_rss_bytes=peak_rss[0])
        result['completed_at'] = reader.now()
        result['source_after'] = source_hashes(expected_hashes)
        result['source_unchanged'] = result['source_before'] == result['source_after']
        reader.save(path / 'result.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-hashes', type=Path, required=True)
    args = parser.parse_args()
    expected_hashes = json.loads(args.source_hashes.read_text())
    assert isinstance(expected_hashes, dict) and all(isinstance(value, str) for value in expected_hashes.values())
    assert set(reader.SOURCE_PATHS) <= set(expected_hashes)
    result = capture(expected_hashes)
    print(json.dumps({'phase':result['phase'], 'verdict':result['verdict'],
                      'source_unchanged':result['source_unchanged'],
                      'live_owned_processes':result.get('termination', {}).get('live_owned_process_count')}))
