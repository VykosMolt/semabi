"""Read-only evaluator setup preflight; never pulls, starts or seeds an app."""
import json
from pathlib import Path
import socket
import subprocess

HERE = Path(__file__).resolve().parent
IMAGE = 'freshrss/freshrss:1.30.0'
CONTAINER = 'semabi-freshrss-reserved-v1'


def main():
    plan = json.loads((HERE / 'task_plan.json').read_text())
    assert plan['denominator'] == len(plan['tasks']) == 16
    assert len({task['id'] for task in plan['tasks']}) == 16
    image = subprocess.run(['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}'],
                           capture_output=True, text=True)
    container = subprocess.run(['docker', 'container', 'inspect', CONTAINER, '--format', '{{.Id}}'],
                               capture_output=True, text=True)
    with socket.socket() as check:
        occupied = check.connect_ex(('127.0.0.1', 8882)) == 0
    print(json.dumps({'application': 'FreshRSS', 'version': plan['version'],
                     'requested_tasks': 16, 'image_cached': image.returncode == 0,
                     'named_container_exists': container.returncode == 0,
                     'port_8882_occupied': occupied,
                     'setup_actions': 0, 'learner_attempts': 0,
                     'next': 'Read the retained setup/assessment receipts; do not repeat a frozen assessment or reseed its baseline'}))


if __name__ == '__main__':
    main()
