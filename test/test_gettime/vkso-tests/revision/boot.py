#!/usr/bin/env python3
"""Stage, install and run the balanced bare-metal campaign across real reboots."""
import argparse
import json
import os
import re
import shutil
import subprocess
import time
import traceback
from pathlib import Path
from campaign import digest, pending

HERE = Path(__file__).resolve().parent
SERVICE = 'vkso-clocktime-revision.service'
GRUB_SCRIPT = Path('/etc/grub.d/43_vkso_clocktime_revision')


def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def entry_name(step, plan):
    return f"vkso-revision-{step['role']}-{step['backend']}-{plan['packages'][step['role']]['variant']}"


def stage(root, plan, multireader, module):
    grub = Path('/boot/grub/grub.cfg').read_text()
    entries = []
    seen = set()
    for step in plan['steps']:
        name = entry_name(step, plan)
        if name in seen:
            continue
        seen.add(name)
        prefix = 'vkso-final' if step['role'] == 'read' else 'vkso-update'
        variant = plan['packages'][step['role']]['variant']
        old = f"{prefix}-{step['backend']}-{variant}"
        match = re.search(r"^menuentry [^\n]+ --id " + re.escape(old) + r" \{\n(.*?)^\}",
                          grub, re.M | re.S)
        if not match:
            raise ValueError(f'existing boot entry missing: {old}')
        body = match[1]
        for key, value in [('isolcpus', 'domain,managed_irq,1-3'), ('nohz_full', '1-3'),
                           ('rcu_nocbs', '1-3'), ('irqaffinity', '0')]:
            if not re.search(r'\b' + key + r'=\S+', body):
                raise ValueError(f'existing boot entry missing {key}')
            body = re.sub(r'\b' + key + r'=\S+', f'{key}={value}', body)
        entries.append(f"menuentry 'Clocktime revision: {step['role']} {step['backend']} {variant}' --id {name} {{\n{body}}}\n")
        package = Path(plan['packages'][step['role']]['path'])
        image = Path('/boot') / f"{old}-5.15.198.bzImage"
        if digest(image) != digest(package / f"{step['backend']}-bzImage"):
            raise ValueError(f'installed image differs from package: {image}')
    # Return to the same ordinary kernel used to start the experiment.
    release = os.uname().release
    returned = re.search(r"menuentry '[^']+' [^\n]+ '(gnulinux-" + re.escape(release)
                         + r"-advanced-[^']+)'", grub)
    parent = re.search(r"^submenu '[^']+' [^\n]+ '(gnulinux-advanced-[^']+)'", grub, re.M)
    if not returned or not parent:
        raise ValueError('cannot identify the current kernel return entry')
    for path in [root, HERE, multireader, module]:
        if any(c.isspace() or c in '%"' for c in str(path)):
            raise ValueError('systemd staging requires paths without whitespace, percent or quotes')
    staged = root / 'boot-stage'
    staged.mkdir()
    (staged / 'grub-script').write_text("#!/bin/sh\ncat <<'VKSO_REVISION_EOF'\n" + '\n'.join(entries)
                                      + 'VKSO_REVISION_EOF\n')
    (staged / SERVICE).write_text(f'''[Unit]
Description=Clocktime revision independent-boot experiment
After=network-online.target
Wants=network-online.target
ConditionPathExists={root}/armed

[Service]
Type=simple
ExecStart=/usr/bin/python3 {HERE}/boot.py resume {root}
WorkingDirectory={HERE}
CPUAffinity=0
TimeoutStopSec=90

[Install]
WantedBy=multi-user.target
''')
    config = dict(multireader=str(multireader), kernel_module=str(module),
                  return_entry=parent[1] + '>' + returned[1], plan_sha256=digest(root / 'plan.json'))
    (staged / 'controller.json').write_text(json.dumps(config, indent=2) + '\n')
    print(f'staged boot entries and service: {staged}')


def install(root):
    staged = root / 'boot-stage'
    target = Path('/etc/systemd/system') / SERVICE
    if GRUB_SCRIPT.exists() or target.exists():
        raise ValueError('revision controller already installed; inspect it before replacing')
    shutil.copy2(staged / 'grub-script', GRUB_SCRIPT)
    GRUB_SCRIPT.chmod(0o755)
    run(['update-grub'])
    shutil.copy2(staged / SERVICE, target)
    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'enable', SERVICE])
    print('installed; no reboot requested yet')


def reboot(entry):
    run(['grub-reboot', entry])
    environment = run(['grub-editenv', '/boot/grub/grubenv', 'list'], capture_output=True, text=True).stdout
    if f'next_entry={entry}\n' not in environment:
        raise ValueError('GRUB did not retain the requested next entry')
    os.sync()
    run(['systemctl', 'reboot'])


def resume(root, plan, config):
    if (root / 'failed.json').exists():
        raise ValueError('a previous collection failed; retain and inspect its evidence before resuming')
    step = pending(root, plan)
    if step is None:
        raise ValueError('campaign is already complete')
    irqbalance = subprocess.run(['systemctl', 'is-active', '--quiet', 'irqbalance']).returncode == 0
    settings = {}
    try:
        if irqbalance:
            run(['systemctl', 'stop', 'irqbalance'])
        base = Path('/sys/devices/system/cpu')
        requested = [(base / 'intel_pstate' / name, value) for name, value in
                     [('no_turbo', '1'), ('min_perf_pct', '100'), ('max_perf_pct', '100')]]
        requested += [(p, 'performance') for p in base.glob('cpufreq/policy*/scaling_governor')]
        for path, value in requested:
            if path.exists():
                previous = path.read_text()
                # Firmware-disabled turbo already reports 1 and rejects even
                # an identical write. Preserve already satisfied settings.
                if previous.strip() != value:
                    path.write_text(value + '\n')
                    settings[path] = previous
                if path.read_text().strip() != value:
                    raise ValueError(f'frequency setting did not take effect: {path}')
        # Allow boot services to finish before the collector's per-method stabilization.
        time.sleep(60)
        with (root / f"step-{step['index']:03d}.log").open('x') as log:
            run(['python3', HERE / 'collect.py', root, '--multireader', config['multireader'],
                 '--kernel-module', config['kernel_module']], stdout=log, stderr=subprocess.STDOUT)
    except BaseException:
        (root / 'failed.json').write_text(json.dumps(dict(step=step, error=traceback.format_exc()), indent=2))
        (root / 'armed').unlink(missing_ok=True)
        raise
    finally:
        for path, value in reversed(list(settings.items())):
            path.write_text(value)
        if irqbalance:
            run(['systemctl', 'start', 'irqbalance'])
    next_step = pending(root, plan)
    if next_step is not None:
        reboot(entry_name(next_step, plan))
    else:
        run(['python3', HERE / 'analyze.py', *sorted(root.glob('step-*/measurements.csv')),
             '--output', root / 'summary.csv'])
        (root / 'armed').unlink()
        (root / 'campaign-complete.json').write_text(json.dumps(dict(plan_sha256=digest(root / 'plan.json'),
                                                                   summary_sha256=digest(root / 'summary.csv')), indent=2))
        run(['systemctl', 'disable', SERVICE])
        reboot(config['return_entry'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['stage', 'install', 'start', 'resume'])
    parser.add_argument('campaign', type=Path)
    parser.add_argument('--multireader', type=Path)
    parser.add_argument('--kernel-module', type=Path)
    args = parser.parse_args()
    root = args.campaign.resolve()
    plan = json.loads((root / 'plan.json').read_text())
    if args.command == 'stage':
        if not args.multireader or not args.kernel_module:
            parser.error('stage requires --multireader and --kernel-module')
        stage(root, plan, args.multireader.resolve(), args.kernel_module.resolve())
        return
    if os.geteuid() != 0:
        parser.error('install/start/resume require root')
    config = json.loads((root / 'boot-stage/controller.json').read_text())
    if config['plan_sha256'] != digest(root / 'plan.json'):
        raise ValueError('campaign changed after boot staging')
    if args.command == 'install':
        install(root)
    elif args.command == 'start':
        step = pending(root, plan)
        if step is None or (root / 'failed.json').exists():
            raise ValueError('campaign is complete or needs failure inspection')
        run(['systemctl', 'is-enabled', '--quiet', SERVICE])
        (root / 'armed').touch(exist_ok=False)
        reboot(entry_name(step, plan))
    else:
        resume(root, plan, config)


if __name__ == '__main__':
    main()
