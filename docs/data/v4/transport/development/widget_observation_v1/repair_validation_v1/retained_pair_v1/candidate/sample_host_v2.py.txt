"""Record post-exit host command matches for W2 namespace-local executions."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

ROOT = Path('/home/moloch/semabi')
TARGETS = {'BASELINE': ROOT / 'runs/.w2_scoring_baseline_worktree',
           'CANDIDATE': ROOT / 'runs/.w2_scoring_worktree'}


def main():
    expectations = {}
    for condition, root in TARGETS.items():
        directory = root / 'docs/data/v4/transport/development/widget_observation_repair_v1/root_focused_v1'
        process = json.loads((directory / 'job_v1/process.json').read_text())
        command = json.loads((directory / 'command_v1.json').read_text())
        terminal = json.loads((directory / 'root_reap_tool_v1.json').read_text())
        if terminal['result'].get('exit_code') != process['returncode'] or not process['child_terminated']:
            raise ValueError('Required owned completion is absent')
        argv = command['argv']
        start = argv.index(str(ROOT / '.venv/bin/python'))
        runner = argv[start:]
        if runner[runner.index('--') + 1:] != process['command']:
            raise ValueError('Recorded runner/child command link differs')
        expectations[condition] = (directory, process, runner, process['command'])
    matches = {name: {'runner': [], 'child': []} for name in expectations}
    inaccessible, vanished, scanned = [], [], []
    for path in sorted(Path('/proc').iterdir()):
        if not path.name.isdigit():
            continue
        try:
            status = (path / 'status').read_text()
            uid = int(next(line for line in status.splitlines() if line.startswith('Uid:')).split()[2])
            if uid != os.geteuid():
                continue
            raw = (path / 'cmdline').read_bytes()
            argv = [part.decode() for part in raw.split(b'\0') if part]
            scanned.append(int(path.name))
            for name, (_directory, _process, runner, child) in expectations.items():
                if argv == runner:
                    matches[name]['runner'].append(int(path.name))
                if argv == child:
                    matches[name]['child'].append(int(path.name))
        except FileNotFoundError:
            vanished.append(int(path.name))
        except (OSError, UnicodeError, StopIteration, ValueError) as error:
            inaccessible.append({'pid': int(path.name), 'error': str(error)})
    common = {'created_utc': datetime.now(timezone.utc).isoformat(), 'sampler_pid': os.getpid(),
              'sampler_effective_uid': os.geteuid(), 'sampler_pid_namespace': os.readlink('/proc/self/ns/pid'),
              'sampler_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scanned_effective_uid_pids': scanned, 'vanished_during_sample': vanished,
              'inaccessible_entries': inaccessible,
              'scope': 'Post-exit host scan for exact recorded argv arrays under the same effective UID. '
                       'Runner and child IDs in their process record are namespace-local; no mapping to host PIDs was captured. '
                       'No numeric host-PID or process-group absence is claimed. Reaping is established by the owned tool terminal receipt and runner child completion.'}
    for condition, (directory, process, runner, child) in expectations.items():
        record = {**common, 'schema': 'semabi.widget_observation.namespace_completion_sample.v2',
                  'condition': condition, 'namespace_local_pids': {
                      'runner_pid': process['runner_pid'], 'child_pid': process['child_pid'],
                      'owned_process_group': process['owned_process_group']},
                  'host_pid_mapping': 'NOT_CAPTURED', 'expected_runner_argv': runner,
                  'expected_child_argv': child, 'exact_command_matches': matches[condition]}
        path = directory / 'root_host_termination_v2.json'
        with path.open('x') as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(json.dumps({'condition': condition, 'record_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'exact_command_matches': matches[condition], 'inaccessible_entries': inaccessible,
                          'host_sampler_pid': os.getpid()}, sort_keys=True))


if __name__ == '__main__':
    main()
