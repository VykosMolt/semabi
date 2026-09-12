"""Evaluator-only setup for the preselected FreshRSS assessment; never learner input."""
import argparse
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import time
import urllib.request
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from preflight import CONTAINER, IMAGE

HERE = Path(__file__).resolve().parent
PRIVATE = HERE / 'private'
FEEDS = HERE / 'feeds'
URL = 'http://127.0.0.1:8882/'
VOLUME = 'semabi_freshrss_reserved_v1_data'
USER = 'semabi'


def docker(*args, **kwargs):
    result = subprocess.run(['docker', *args], capture_output=True, **kwargs)
    if result.returncode:
        # Never print command output containing native data or secret values.
        raise RuntimeError('Evaluator Docker action failed: ' + str(args[0]))
    return result.stdout


def save_new(path, value):
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as out:
        json.dump(value, out, indent=2)
        out.write('\n')


def owned():
    info = json.loads(docker('inspect', CONTAINER))[0]
    identity = json.loads((PRIVATE / 'container.json').read_text())
    assert info['Id'] == identity['id']
    assert info['Config']['Labels']['semabi.owner'] == 'semantic_bridge'
    assert info['HostConfig']['PortBindings']['8882/tcp'] == [{'HostIp': '127.0.0.1', 'HostPort': '8882'}]
    assert info['HostConfig']['NanoCpus'] == 2_000_000_000
    assert info['HostConfig']['Memory'] == 1_073_741_824
    return info


def generate_data():
    plan = json.loads((HERE / 'task_plan.json').read_text())
    assert plan['denominator'] == len(plan['tasks']) == 16
    FEEDS.mkdir(exist_ok=False)
    now = datetime.now(timezone.utc)
    for feed in plan['setup']['feeds'] + plan['setup']['unsubscribed_feeds']:
        root = ET.Element('rss', version='2.0')
        channel = ET.SubElement(root, 'channel')
        for tag, value in [('title', feed['title']), ('link', URL), ('description', 'Static evaluator RSS data')]:
            ET.SubElement(channel, tag).text = value
        for index in range(feed['articles']):
            item = ET.SubElement(channel, 'item')
            title = (feed['special_titles'][index] if index < len(feed['special_titles'])
                     else feed['content_prefix'] + ' ' + str(index + 1))
            ET.SubElement(item, 'title').text = title
            ET.SubElement(item, 'guid', isPermaLink='false').text = feed['file'] + ':' + str(index + 1)
            ET.SubElement(item, 'link').text = URL + 'evaluator-feeds/' + feed['file'] + '#article-' + str(index + 1)
            ET.SubElement(item, 'description').text = feed['content_prefix'] + ' content ' + str(index + 1)
            ET.SubElement(item, 'pubDate').text = format_datetime(now - timedelta(minutes=index + 1))
        ET.ElementTree(root).write(FEEDS / feed['file'], encoding='utf-8', xml_declaration=True)
    root = ET.Element('opml', version='2.0')
    head = ET.SubElement(root, 'head')
    ET.SubElement(head, 'title').text = 'Prospectively selected assessment data'
    body = ET.SubElement(root, 'body')
    for name in plan['setup']['categories']:
        category = ET.SubElement(body, 'outline', text=name, title=name)
        for feed in plan['setup']['feeds']:
            if feed['category'] == name:
                ET.SubElement(category, 'outline', type='rss', text=feed['title'], title=feed['title'],
                              xmlUrl=plan['setup']['feed_base_url'] + feed['file'], htmlUrl=URL)
    ET.ElementTree(root).write(PRIVATE / 'seed.opml', encoding='utf-8', xml_declaration=True)


def start():
    assert not (PRIVATE / 'container.json').exists(), 'Already provisioned; inspect owned instance instead'
    with socket.socket() as probe:
        assert probe.connect_ex(('127.0.0.1', 8882)) != 0, 'Port is owned by another service'
    for kind, name in [('container', CONTAINER), ('volume', VOLUME)]:
        assert subprocess.run(['docker', kind, 'inspect', name], capture_output=True).returncode != 0
    image = json.loads(docker('image', 'inspect', IMAGE))[0]
    PRIVATE.mkdir(mode=0o700, exist_ok=True)
    save_new(PRIVATE / 'credentials.json', {'username': USER, 'password': secrets.token_urlsafe(24)})
    generate_data()
    docker('volume', 'create', '--label', 'semabi.owner=semantic_bridge', VOLUME)
    identity = docker('run', '-d', '--name', CONTAINER, '--cpus', '2', '--cpuset-cpus', '10,11',
        '--memory', '1g', '--pids-limit', '256', '--restart', 'no', '--label', 'semabi.owner=semantic_bridge',
        '--log-opt', 'max-size=10m', '-p', '127.0.0.1:8882:8882',
        '-v', VOLUME + ':/var/www/FreshRSS/data',
        '--mount', 'type=bind,src=' + str(FEEDS) + ',dst=/var/www/FreshRSS/p/evaluator-feeds,readonly',
        '-e', 'LISTEN=0.0.0.0:8882', '-e', 'INTERNAL_HOST_ALLOWLIST=127.0.0.1:8882',
        '-e', 'TZ=UTC', '-e', 'CRON_MIN=', '-e', 'ENABLE_ACCESS_LOG=0',
        '-e', 'FRESHRSS_INSTALL=--default-user ' + USER + ' --base-url ' + URL + ' --language en --db-type sqlite', IMAGE).decode().strip()
    save_new(PRIVATE / 'container.json', {'id': identity, 'image_id': image['Id'], 'digests': image['RepoDigests']})
    for attempt in range(60):
        try:
            with urllib.request.urlopen(URL, timeout=2) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.5)
    else:
        raise RuntimeError('FreshRSS did not become reachable in the setup window')
    owned()
    print('Owned bounded FreshRSS container started; no learner call.')


def cli(command, *arguments, input=None):
    owned()
    return docker('exec', '-i', '--user', 'www-data', '-w', '/var/www/FreshRSS', CONTAINER,
                  'cli/' + command + '.php', *arguments, input=input)


def seed():
    owned()
    assert not (PRIVATE / 'seed_receipt.json').exists(), 'Never reseed completed baseline'
    credentials = json.loads((PRIVATE / 'credentials.json').read_text())
    cli('create-user', '--user', USER, '--no-default-feeds', '--language', 'en')
    # Hash and set via stdin. Password and hash never occur in command argv,
    # Docker environment, public receipts or native-output logging.
    password_hash = docker('exec', '-i', '--user', 'www-data', CONTAINER, 'php', '-r',
                          'echo password_hash(stream_get_contents(STDIN), PASSWORD_DEFAULT);',
                          input=credentials['password'].encode())
    cli('reconfigure-user', '--user', USER, '--key', 'passwordHash', '--set', '--value-stdin', input=password_hash)
    docker('cp', str(PRIVATE / 'seed.opml'), CONTAINER + ':/tmp/semabi-seed.opml')
    cli('import-for-user', '--user', USER, '--filename', '/tmp/semabi-seed.opml')
    cli('actualize-user', '--user', USER)
    info = json.loads(cli('user-info', '--user', USER, '--json'))
    save_new(PRIVATE / 'seed_receipt.json', {'user_info': info, 'learner_calls': 0})
    print('Evaluator account and preselected RSS data seeded; native verification pending.')


def verify():
    owned()
    assert not (HERE / 'setup_receipt.json').exists()
    info = json.loads(cli('user-info', '--user', USER, '--json'))
    opml = cli('export-opml-for-user', '--user', USER)
    save_new(PRIVATE / 'native_verification.json', {'user_info': info, 'opml': opml.decode(),
                                                   'boundary': 'Evaluator native evidence, never learner inputs'})
    cli('export-sqlite-for-user', '--user', USER, '--filename', '/tmp/semabi-baseline.sqlite')
    docker('cp', CONTAINER + ':/tmp/semabi-baseline.sqlite', str(PRIVATE / 'baseline.sqlite'))
    os.chmod(PRIVATE / 'baseline.sqlite', 0o600)
    print('Native OPML, counts and SQLite baseline captured privately; inspect before readiness claim.')


def complete_seed():
    """Finish empty categories omitted by native OPML import, using evaluator UI."""
    from playwright.sync_api import sync_playwright
    owned()
    assert not (HERE / 'setup_receipt.json').exists()
    plan = json.loads((HERE / 'task_plan.json').read_text())
    prior = json.loads((PRIVATE / 'native_verification.json').read_text())
    categories = {item.attrib['text'] for item in ET.fromstring(prior['opml']).find('body')}
    missing = [name for name in plan['setup']['categories'] if name not in categories]
    credentials = json.loads((PRIVATE / 'credentials.json').read_text())
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until='networkidle')
        page.get_by_label('Username', exact=True).fill(credentials['username'])
        password = page.get_by_label('Password', exact=True)
        password.fill(credentials['password'])
        page.get_by_role('button', name='Login', exact=True).click()
        password.wait_for(state='hidden', timeout=10000)
        page.get_by_role('link', name='Subscription management', exact=True).click()
        for name in missing:
            page.get_by_text('Add a category', exact=True).click()
            field = page.locator('input[name="new-category"]').first
            field.fill(name)
            field.locator('xpath=ancestor::form').get_by_role('button', name='Add', exact=True).click()
            # The native readback is independent of the submitted text.
            updated = ET.fromstring(cli('export-opml-for-user', '--user', USER))
            assert name in {item.attrib['text'] for item in updated.find('body')}
        display = page.get_by_role('link', name='Display', exact=True, include_hidden=True).get_attribute('href')
        assert display
        page.goto(urljoin(page.url, display), wait_until='networkidle')
        themes = page.locator('select[name="theme"]')
        assert themes.count() == 1
        current = themes.input_value()
        choices = themes.locator('option').evaluate_all('(xs)=>xs.map(x=>({value:x.value,label:x.textContent}))')
        alternatives = sorted(item['value'] for item in choices if item['value'] and item['value'] != current)
        assert alternatives, 'Preselected presentation challenge remains setup-unestablished without another theme'
        save_new(PRIVATE / 'theme_challenge.json', {'initial': current, 'alternative': alternatives[0],
                 'choices': choices, 'policy': 'Lexicographically first built-in alternative, before any learner attempt'})
        browser.close()
    cli('export-sqlite-for-user', '--user', USER, '--filename', '/tmp/semabi-baseline-verified.sqlite')
    target = PRIVATE / 'baseline_verified.sqlite'
    assert not target.exists()
    docker('cp', CONTAINER + ':/tmp/semabi-baseline-verified.sqlite', str(target))
    os.chmod(target, 0o600)
    with sqlite3.connect('file:' + str(target) + '?mode=ro', uri=True) as database:
        actual_categories = {row[0] for row in database.execute('SELECT name FROM category')}
        assert set(plan['setup']['categories']) <= actual_categories
        feeds = database.execute('SELECT f.id,c.name,f.name,f.url FROM feed f JOIN category c ON f.category=c.id').fetchall()
        expected = {(item['category'], item['title'], plan['setup']['feed_base_url'] + item['file']): item
                    for item in plan['setup']['feeds']}
        assert {(category, title, url) for _, category, title, url in feeds} == set(expected)
        for identity, category, title, url in feeds:
            definition = expected[(category, title, url)]
            entries = database.execute('SELECT guid,title,content,is_read,is_favorite FROM entry WHERE id_feed=?', (identity,)).fetchall()
            source = ET.parse(FEEDS / definition['file'])
            expected_entries = {item.findtext('guid'): (item.findtext('title'), item.findtext('description'))
                                for item in source.findall('./channel/item')}
            assert len(entries) == definition['articles'] == len(expected_entries)
            assert {row[0] for row in entries} == set(expected_entries)
            for guid, entry_title, content, read, favourite in entries:
                assert (entry_title, content) == expected_entries[guid]
                assert read == favourite == 0
    identity = json.loads((PRIVATE / 'container.json').read_text())
    save_new(HERE / 'setup_receipt.json', {'application': 'FreshRSS', 'version': '1.30.0',
        'url': URL, 'container': CONTAINER, 'container_id': identity['id'],
        'image_id': identity['image_id'], 'image_digests': identity['digests'],
        'limits': {'cpus': 2, 'cpuset': '10,11', 'memory_bytes': 1073741824},
        'credential_path': str(PRIVATE / 'credentials.json'), 'task_plan': str(HERE / 'task_plan.json'),
        'setup_verified': True, 'requested_tasks': 16, 'learner_runs': 0, 'reserved_assessment_started': False,
        'baseline': str(target), 'presentation_challenge_preselected': True,
        'setup_failures_retained': ['Native OPML import omitted an empty planned category; evaluator UI completed it',
            'Evaluator login wait returned before asynchronous navigation; explicit password disappearance succeeded',
            'Evaluator Add a category role-link locator failed; rendered heading was the observed affordance'],
        'exposure': 'Evaluator read official setup docs, rendered login/subscription/display UI, exported OPML and SQLite schema/data. Native identifiers, selectors, theme and expected data remain evaluator-only; no application source or learner outcomes inspected. Shared context is not blind.',
        'official_sources': ['https://github.com/FreshRSS/FreshRSS/releases/tag/1.30.0',
            'https://github.com/FreshRSS/FreshRSS/blob/1.30.0/Docker/README.md',
            'https://github.com/FreshRSS/FreshRSS/blob/1.30.0/cli/README.md']})
    print('Preselected baseline, authentication and theme availability independently verified; no learner run.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'seed', 'verify', 'complete-seed', 'status'])
    action = parser.parse_args().action
    if action == 'status':
        print(json.dumps({'running': owned()['State']['Running'], 'learner_calls': 0}))
    else:
        globals()[action.replace('-', '_')]()
