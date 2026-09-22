#!/usr/bin/env python3
"""One fixed boot/collect interface, four cases, independently booted blocks."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
from bundle import PROTOCOL, sha256, kv_file, write_json
from package_check import check

HERE = Path(__file__).resolve().parent
BARE = HERE.parent / 'baremetal'
ORDERS = (
    ('raw-normal', 'vkso-normal', 'raw-no-retpoline', 'vkso-no-retpoline'),
    ('vkso-normal', 'vkso-no-retpoline', 'raw-normal', 'raw-no-retpoline'),
    ('vkso-no-retpoline', 'raw-no-retpoline', 'vkso-normal', 'raw-normal'),
    ('raw-no-retpoline', 'raw-normal', 'vkso-no-retpoline', 'vkso-normal'),
)


def plan(blocks):
    return [dict(block=b + 1, case=c) for b in range(blocks) for c in ORDERS[b % 4]]


def atomic(path, data):
    tmp = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    write_json(tmp, data)
    tmp.replace(path)


def frozen_inputs(packages):
    files = [BARE / 'experiment.conf', BARE / 'collect-case.sh', BARE / 'boot-once.sh',
             BARE / 'verify-packages.sh', BARE / 'experiment.sh']
    files += list(HERE.glob('*.py'))
    files += [p / 'SHA256SUMS' for p in packages.values()]
    return {str(p.resolve()): sha256(p) for p in files}


def archive(root):
    target = root.with_name(root.name + '.tar.gz')
    if target.exists():
        raise ValueError('archive exists; refusing overwrite: ' + str(target))
    tmp = target.with_name(target.name + '.partial-' + str(os.getpid()))
    with tarfile.open(tmp, 'w:gz') as stream:
        stream.add(root, arcname=root.name)
    tmp.replace(target)
    target.with_name(target.name + '.sha256').write_text(sha256(target) + '  ' + str(target) + '\n')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['begin', 'boot', 'collect', 'status', 'aggregate'])
    parser.add_argument('value', nargs='?')
    args = parser.parse_args()
    results = Path(os.environ.get('RESULTS_DIR', BARE / 'results')).resolve()
    state_file = Path(os.environ.get('STATE_FILE', BARE / '.direct-api-state.json')).resolve()
    results.mkdir(parents=True, exist_ok=True)
    with open(os.environ.get('LOCK_FILE', str(BARE / '.direct-api.lock')), 'a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads(state_file.read_text()) if state_file.exists() else None
        if args.action == 'begin':
            if state and state['status'] == 'active':
                raise ValueError('campaign already active; use status/boot/collect')
            packages = {v: Path(os.environ.get(e, BARE / 'artifacts' / ('direct-' + v))).resolve()
                        for v, e in [('normal', 'NORMAL_PACKAGE'), ('no-retpoline', 'NO_RETPOLINE_PACKAGE')]}
            subprocess.run([str(BARE / 'verify-packages.sh'), *map(str, packages.values())], check=True)
            for package in packages.values():
                for local in [BARE / n for n in ('collect-case.sh', 'experiment.sh', 'experiment.conf', 'boot-once.sh')]:
                    if sha256(local) != sha256(package / local.name):
                        raise ValueError('workflow changed since build; rebuild: ' + local.name)
                for local in HERE.glob('*.py'):
                    if sha256(local) != sha256(package / 'direct/src/direct-api' / local.name):
                        raise ValueError('direct API source changed since build; rebuild: ' + local.name)
            config = kv_file(BARE / 'experiment.conf')
            blocks = int(config['BLOCKS'])
            if not 1 <= int(config['PERF_PROCESSES']) <= int(config['REPEATS']) <= 1000:
                raise ValueError('invalid repetition counts')
            if not 0 < int(config['ITERATIONS']) <= 1000000 or not 0 <= int(config['WARMUP']) <= 1000000:
                raise ValueError('invalid batch/warmup counts')
            if not 1 <= blocks <= 100:
                raise ValueError('BLOCKS must be 1..100')
            run_id = args.value or time.strftime('%Y%m%dT%H%M%SZ-direct-api', time.gmtime())
            if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in run_id):
                raise ValueError('invalid run ID')
            root = results / run_id
            if root.exists() or root.with_name(root.name + '.tar.gz').exists():
                raise ValueError('run already exists')
            root.mkdir()
            manifest = dict(protocol=PROTOCOL, packages={k: str(v) for k, v in packages.items()},
                            config=config, plan=plan(blocks), identities=frozen_inputs(packages))
            write_json(root / 'campaign.json', manifest)
            state = dict(root=str(root), next_index=0, status='active', manifest_sha256=sha256(root / 'campaign.json'))
            atomic(state_file, state)
        if not state:
            if args.action == 'status':
                print('status=not-started'); return
            raise ValueError('run ./experiment.sh begin first')
        root = Path(state['root'])
        if sha256(root / 'campaign.json') != state['manifest_sha256']:
            raise ValueError('campaign manifest changed')
        manifest = json.loads((root / 'campaign.json').read_text())
        if args.action == 'aggregate':
            if state['status'] != 'complete':
                raise ValueError('campaign is incomplete')
            if not root.with_name(root.name + '.tar.gz').exists():
                archive(root)
            subprocess.run([sys.executable, str(HERE / 'results.py'),
                            *map(str, sorted(root.glob('block-*/*'))), '--out', str(root / 'summary.json')], check=True)
            print('summary=' + str(root / 'summary.json')); return
        if args.action in ('boot', 'collect'):
            if state['status'] != 'active':
                raise ValueError('campaign is complete; begin a new campaign explicitly')
            for name, digest in manifest['identities'].items():
                if sha256(name) != digest:
                    raise ValueError('frozen input changed: ' + name)
            entry = manifest['plan'][state['next_index']]
            case = entry['case']
            if args.value and args.value != case:
                raise ValueError('expected ' + case + ', requested ' + args.value)
            package = Path(manifest['packages'][case.split('-', 1)[1]])
            check(package)
            if args.action == 'boot':
                image = Path('/boot') / ('vkso-final-' + case + '-5.15.198.bzImage')
                if sha256(image) != sha256(package / (case.split('-')[0] + '-bzImage')):
                    raise ValueError('installed image mismatch')
                subprocess.run([str(BARE / 'boot-once.sh'), case], check=True)
            else:
                boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                for previous in root.glob('block-*/*/run.json'):
                    if json.loads(previous.read_text())['boot_id'] == boot:
                        raise ValueError('boot already collected; reboot for each independent observation')
                block = root / ('block-%02d' % entry['block'])
                block.mkdir(exist_ok=True)
                final = block / case
                if final.exists():
                    raise ValueError('result exists; refusing overwrite')
                partial = root / ('.partial-' + case + '-' + str(time.time_ns()))
                env = dict(os.environ, DIRECT_PACKAGE=str(package), DIRECT_OUT=str(partial),
                           DIRECT_CONFIG=json.dumps(manifest['config']), DIRECT_BLOCK=str(entry['block']))
                try:
                    subprocess.run([str(BARE / 'collect-case.sh'), case, root.name], env=env, check=True)
                    run = json.loads((partial / 'run.json').read_text())
                    if run['status'] != 'COMPLETE':
                        raise ValueError('collector did not finish')
                    partial.rename(final)
                except BaseException:
                    if partial.exists():
                        incomplete = root / 'incomplete'
                        incomplete.mkdir(exist_ok=True)
                        partial.rename(incomplete / partial.name)
                    raise
                state['next_index'] += 1
                if state['next_index'] == len(manifest['plan']):
                    state['status'] = 'complete'
                    atomic(state_file, state)
                    print('archive=' + str(archive(root)))
                else:
                    atomic(state_file, state)
        print('result_root=' + str(root))
        print('status=' + state['status'])
        print('completed_boots=' + str(state['next_index']))
        if state['status'] == 'active':
            entry = manifest['plan'][state['next_index']]
            print('next_block=%d next_case=%s' % (entry['block'], entry['case']))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        sys.exit('campaign refused/failed: ' + str(exc))
