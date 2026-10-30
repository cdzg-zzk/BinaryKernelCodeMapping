#!/usr/bin/env python3
"""Paired native ISO9660 experiments in a private mount namespace."""
import argparse
import contextlib
import csv
import io
import json
import math
import os
from pathlib import Path
import random
import resource
import select
import signal
import statistics
import struct
import subprocess
import sys
import tarfile
import time
import traceback

PACKAGE = Path(__file__).resolve().parent
VARIANTS = ('original', 'compat', 'prepared', 'copied-fuse', 'vkso-fuse')
MODULES = ('iso_original', 'iso_compat', 'vkso_iso_core', 'vkso_isofs',
           'vkso_kernel_reader', 'page_cache_replace')


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def kernel_id():
    data = Path('/sys/kernel/notes').read_bytes()
    pos = 0
    while pos + 12 <= len(data):
        namesz, descsz, kind = struct.unpack_from('III', data, pos)
        pos += 12
        name = data[pos:pos + namesz]
        pos += (namesz + 3) & ~3
        desc = data[pos:pos + descsz]
        pos += (descsz + 3) & ~3
        if name.rstrip(b'\0') == b'GNU' and kind == 3:
            return desc.hex()
    raise RuntimeError('running kernel build ID unavailable')


def cpu_ticks(pid):
    text = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return (int(text[11]) + int(text[12])) / os.sysconf('SC_CLK_TCK')


def process_memory(pid):
    return Path(f'/proc/{pid}/smaps_rollup').read_text()


def summary(rows):
    # Each block contributes one ratio; repeated mounts are not independent blocks.
    groups = {}
    for row in rows:
        groups.setdefault((row['image'], row['workload'], row['block'], row['variant']), []).append(row['wall_seconds'])
    result = []
    for image, workload in sorted({(r['image'], r['workload']) for r in rows}):
        for base, treatment in [('original', 'prepared'), ('original', 'compat'),
                                ('compat', 'prepared'), ('copied-fuse', 'vkso-fuse')]:
            ratios = []
            for block in sorted({r['block'] for r in rows}):
                b = groups.get((image, workload, block, base))
                t = groups.get((image, workload, block, treatment))
                if b and t:
                    ratios.append(statistics.median(t) / statistics.median(b))
            if not ratios:
                continue
            logs = [math.log(x) for x in ratios]
            rng = random.Random(20261029)
            boots = sorted(math.exp(statistics.mean(rng.choices(logs, k=len(logs)))) for _ in range(10000))
            result.append(dict(image=image, workload=workload, baseline=base, treatment=treatment,
                               blocks=len(ratios), paired_ratios=ratios,
                               geometric_mean_time_ratio=math.exp(statistics.mean(logs)),
                               bootstrap_95_percent=[boots[250], boots[9749]] if len(ratios) >= 4 else None,
                               direction='ratio > 1 means treatment takes longer'))
    return result


class Campaign:
    def __init__(self, args):
        self.args = args
        self.out = args.output.resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        self.mount = self.out / 'mount'
        self.mount.mkdir()
        self.scratch = self.out / 'scratch'
        self.scratch.mkdir()
        self.carrier = self.out / 'carrier'
        self.carrier.mkdir()
        self.loaded = []
        self.manager = None
        self.manager_log = None
        self.fifo_fd = None
        self.rows = []
        self.output_sizes = {}
        self.status = dict(status='running', stage='preflight', scope='native performance' if not args.functional else 'guest functional validation only')

    def command(self, argv, name, cwd=None):
        with (self.out / (name + '.log')).open('w') as stream:
            child = subprocess.run(list(map(str, argv)), cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        if child.returncode:
            raise RuntimeError(f'{name} failed ({child.returncode}); see {name}.log')

    def stage(self, name):
        self.status['stage'] = name
        write(self.out / 'result.json', self.status)
        print(name, flush=True)

    def preflight(self):
        assert os.geteuid() == 0, 'run through sudo bash run.sh'
        identity = json.loads((PACKAGE / 'package.json').read_text())
        assert kernel_id() == identity['kernel_build_id'], 'kernel differs from package: boot the recorded raw-normal image first'
        assert Path('/proc/self/ns/mnt').readlink() != Path('/proc/1/ns/mnt').readlink(), 'run.sh must create a private mount namespace'
        existing = {l.split()[0] for l in Path('/proc/modules').read_text().splitlines()}
        assert not existing.intersection(MODULES), 'test modules already loaded; inspect the previous session before rerunning'
        cpus = os.sched_getaffinity(0)
        assert self.args.client_cpu in cpus and self.args.server_cpu in cpus, f'CPUs unavailable: {cpus}'
        write(self.out / 'environment.json', dict(kernel=os.uname().release, build_id=kernel_id(),
              cmdline=Path('/proc/cmdline').read_text(), cpuinfo=Path('/proc/cpuinfo').read_text(),
              client_cpu=self.args.client_cpu, server_cpu=self.args.server_cpu,
              blocks=self.args.blocks, repeats=self.args.repeats, functional=self.args.functional,
              cache_policy='fresh filesystem mount / FUSE process for each pass; warm backing image; no global cache drop',
              package=identity))
        self.command(['mount', '-t', 'tmpfs', '-o', 'size=512m,mode=0700', 'iso-bench-output', self.scratch], 'mount-output')
        if not Path('/sys/kernel/debug/vkso_kernel_reader').parent.exists():
            raise RuntimeError('/sys/kernel/debug is unavailable')
        # Mount debugfs only inside this private namespace if necessary.
        if not os.path.ismount('/sys/kernel/debug'):
            self.command(['mount', '-t', 'debugfs', 'none', '/sys/kernel/debug'], 'mount-debugfs')
        for module in MODULES:
            self.command(['insmod', PACKAGE / 'modules' / (module + '.ko')], 'load-' + module)
            self.loaded.append(module)
        (self.out / 'modules-loaded.txt').write_text(Path('/proc/modules').read_text())

    def register(self):
        self.command([PACKAGE / 'krg', 'build', PACKAGE / 'vmlinux', '--module',
                      PACKAGE / 'modules/vkso_iso_core.ko', '-o', self.carrier / 'out.krg'], 'krg')
        self.command([sys.executable, PACKAGE / 'build_PIC_so.py', '--symbols', PACKAGE / 'symbols.txt',
                      '--krg', self.carrier / 'out.krg', '--ko', PACKAGE / 'modules/vkso_iso_core.ko',
                      '--shim-list', PACKAGE / 'shim.txt', '--vmlinux', PACKAGE / 'vmlinux'], 'carrier', cwd=self.carrier)
        self.library = next(self.carrier.glob('lib*.so')).resolve()
        fifo = self.out / 'notify'
        os.mkfifo(fifo)
        self.fifo_fd = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
        self.manager_log = (self.out / 'manager.log').open('w')
        self.manager = subprocess.Popen([str(PACKAGE / 'manager'), 'replace', str(self.library),
                                        str(self.carrier / 'page_mappings.txt'),
                                        '--hold', '--notify-fifo', str(fifo)],
                                       stdout=self.manager_log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 30
        events = b''
        while b'READY 0 ' not in events:
            assert self.manager.poll() is None, 'registration failed; see manager.log'
            assert time.monotonic() < deadline, 'registration timeout'
            if select.select([self.fifo_fd], [], [], .2)[0]:
                events += os.read(self.fifo_fd, 4096)
        (self.out / 'manager-events.txt').write_bytes(events)
        (self.out / 'manager-smaps.txt').write_text(process_memory(self.manager.pid))
        self.copied = self.out / 'libiso-copied.so'
        self.copied.write_bytes(self.library.read_bytes())

    def pfns(self, pid, library, shared, label):
        plan = [(int(o, 0), int(a, 0), k, s) for line in (self.carrier / 'page_mappings.txt').read_text().splitlines()
                if line and not line.startswith('#') for o, a, k, s in [line.split(',')]]
        reader = Path('/sys/kernel/debug/vkso_kernel_reader')
        (reader / 'page_addresses').write_text(' '.join(hex(a) for _, a, _, _ in plan))
        kernel = {int(r['kernel_vaddr'], 0): int(r['pfn']) for r in csv.DictReader(io.StringIO((reader / 'pages').read_text()))}
        rows = []
        with open(f'/proc/{pid}/mem', 'rb', buffering=0) as mem, open(f'/proc/{pid}/pagemap', 'rb', buffering=0) as pm:
            for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
                fields = line.split(maxsplit=5)
                if len(fields) != 6 or fields[5] != str(library):
                    continue
                start, end = (int(x, 16) for x in fields[0].split('-'))
                off = int(fields[2], 16)
                for offset, address, kind, _ in plan:
                    if off <= offset < off + end - start:
                        user = start + offset - off
                        assert len(os.pread(mem.fileno(), 1, user)) == 1
                        entry = int.from_bytes(os.pread(pm.fileno(), 8, user // 4096 * 8), 'little')
                        pfn = entry & ((1 << 55) - 1)
                        assert entry & (1 << 63) and pfn
                        rows.append(dict(offset=offset, user_pfn=pfn, kernel_pfn=kernel[address],
                                         shared=pfn == kernel[address], permissions=fields[1], kind=kind))
        assert len(rows) == len(plan)
        assert all(r['shared'] == shared and 'w' not in r['permissions'] for r in rows)
        write(self.out / (label + '.json'), dict(status='pass', pages=rows))
        (self.out / (label + '-smaps.txt')).write_text(process_memory(pid))

    @contextlib.contextmanager
    def mounted(self, variant, image, norock=False):
        child = None
        log = None
        try:
            if variant in ('original', 'compat', 'prepared'):
                fstype = dict(original='iso_original', compat='iso_compat', prepared='vksoiso')[variant]
                self.command(['mount', '-t', fstype, '-o', 'ro,loop' + (',norock' if norock else ''), image, self.mount], 'mount')
            else:
                library = self.library if variant == 'vkso-fuse' else self.copied
                log = (self.out / 'fuse-last.log').open('w')
                child = subprocess.Popen(['taskset', '-c', str(self.args.server_cpu), str(PACKAGE / 'vkso-isofuse'),
                                          str(library), str(PACKAGE / 'libiso-bridge.so'), str(image),
                                          str(int(norock)), str(self.mount)], stdout=log, stderr=subprocess.STDOUT,
                                         env=dict(os.environ, LD_LIBRARY_PATH=str(PACKAGE)))
                deadline = time.monotonic() + 30
                while not os.path.ismount(self.mount):
                    assert child.poll() is None, 'FUSE exited; see fuse-last.log'
                    assert time.monotonic() < deadline, 'FUSE mount timeout'
                    time.sleep(.01)
            yield child
        finally:
            if os.path.ismount(self.mount):
                self.command(['umount', self.mount], 'unmount')
            if child is not None and child.poll() is None:
                child.terminate()
                child.wait(timeout=10)
            if log:
                log.close()

    def correctness(self):
        from reference_guest import manifest
        cases = json.loads((PACKAGE / 'reference/result.json').read_text())['cases']
        proof = []
        for variant in VARIANTS:
            for case in cases:
                self.stage(f'verify: {variant} {case["image"]} {case["mode"]}')
                with self.mounted(variant, PACKAGE / 'images' / case['image'], case['mode'] == 'norock') as child:
                    rows = manifest(self.mount)
                    expected = json.loads((PACKAGE / 'reference' / case['manifest']).read_text())
                    assert rows == expected, (variant, case, 'reference mismatch')
                    if child and case == cases[0]:
                        self.pfns(child.pid, self.library if variant == 'vkso-fuse' else self.copied,
                                  variant == 'vkso-fuse', 'pfns-' + variant)
                proof.append(dict(variant=variant, image=case['image'], mode=case['mode'], entries=len(rows)))
        # The larger real source tree is checked against the original kernel too.
        image = PACKAGE / 'images/kernel-include.iso'
        oracle = None
        for variant in VARIANTS:
            self.stage(f'verify: {variant} {image.name}')
            with self.mounted(variant, image):
                rows = manifest(self.mount)
                if oracle is None:
                    oracle = rows
                    write(self.out / 'kernel-include-reference.json', rows)
                assert rows == oracle, (variant, 'kernel include tree mismatch')
            proof.append(dict(variant=variant, image=image.name, entries=len(rows)))
        write(self.out / 'correctness.json', dict(status='pass', cases=proof))

    def measure(self, variant, image, workload, block, repeat, phase):
        # Bring the image file into cache without modifying global cache state.
        with image.open('rb') as stream:
            while stream.read(1 << 20):
                pass
        destination = self.scratch / ('scan.txt' if workload == 'scan' else 'archive.tar')
        with self.mounted(variant, image) as daemon:
            if workload == 'scan':
                argv = ['find', str(self.mount), '-printf', '%y %s %m %p %l\n']
            else:
                argv = ['tar', '-cf', str(destination), '-C', str(self.mount), '.']
            server_before = cpu_ticks(daemon.pid) if daemon else 0
            with destination.open('wb') if workload == 'scan' else open(os.devnull, 'wb') as output:
                start = time.perf_counter()
                child = subprocess.Popen(['taskset', '-c', str(self.args.client_cpu)] + argv,
                                          stdout=output, stderr=subprocess.PIPE)
                # Workloads are read-only and expected to emit no stderr; communicate
                # bounds the run while resource accounting covers just this client.
                before = resource.getrusage(resource.RUSAGE_CHILDREN)
                try:
                    _, stderr = child.communicate(timeout=180)
                except BaseException:
                    child.kill()
                    child.communicate()
                    raise
                elapsed = time.perf_counter() - start
                after = resource.getrusage(resource.RUSAGE_CHILDREN)
            assert child.returncode == 0 and not stderr, (argv, child.returncode, stderr.decode(errors='replace'))
            server_cpu = (cpu_ticks(daemon.pid) - server_before) if daemon else 0
            row = dict(phase=phase, block=block, repeat=repeat, variant=variant, image=image.name, workload=workload,
                       wall_seconds=elapsed, client_user_seconds=after.ru_utime-before.ru_utime,
                       client_system_seconds=after.ru_stime-before.ru_stime, server_cpu_seconds=server_cpu,
                       output_bytes=destination.stat().st_size)
            key = (image.name, workload)
            expected_size = self.output_sizes.setdefault(key, row['output_bytes'])
            assert row['output_bytes'] == expected_size, (variant, key, 'workload output size differs')
        destination.unlink()
        with (self.out / 'observations.jsonl').open('a') as stream:
            stream.write(json.dumps(row) + '\n')
        if phase == 'formal':
            self.rows.append(row)

    def timings(self):
        images = [PACKAGE / 'images' / name for name in json.loads((PACKAGE / 'package.json').read_text())['benchmark_images']]
        for image in images:
            for workload in ('scan', 'archive'):
                for variant in VARIANTS:
                    self.stage(f'warmup: {image.name} {workload} {variant}')
                    self.measure(variant, image, workload, -1, 0, 'warmup')
        rng = random.Random(20261029)
        for block in range(self.args.blocks):
            tasks = [(image, workload) for image in images for workload in ('scan', 'archive')]
            rng.shuffle(tasks)
            for image, workload in tasks:
                order = list(VARIANTS)
                rng.shuffle(order)
                for variant in order:
                    self.stage(f'block {block+1}/{self.args.blocks}: {image.name} {workload} {variant}')
                    for repeat in range(self.args.repeats):
                        self.measure(variant, image, workload, block, repeat, 'formal')
        write(self.out / 'summary.json', dict(status='complete', functional_only=self.args.functional,
                                             comparisons=summary(self.rows)))
        with (self.out / 'observations.csv').open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.rows[0]))
            writer.writeheader()
            writer.writerows(self.rows)

    def cleanup(self):
        errors = []
        if self.manager and self.manager.poll() is None:
            try:
                self.manager.send_signal(signal.SIGTERM)
                assert self.manager.wait(timeout=30) == 0
            except BaseException as exc:
                errors.append('registration cleanup: ' + repr(exc))
        if self.manager_log:
            self.manager_log.close()
        if self.fifo_fd is not None:
            os.close(self.fifo_fd)
        for target in [self.mount, self.scratch]:
            if os.path.ismount(target):
                try:
                    self.command(['umount', target], 'cleanup-' + target.name)
                except BaseException as exc:
                    errors.append(repr(exc))
        for module in reversed(self.loaded):
            try:
                self.command(['rmmod', module], 'unload-' + module)
            except BaseException as exc:
                errors.append(repr(exc))
        return errors

    def run(self):
        try:
            self.preflight()
            self.stage('register shared core')
            self.register()
            self.stage('verify all five paths against original kernel')
            self.correctness()
            self.timings()
            self.status.update(status='complete', stage='complete', observations=len(self.rows))
        except BaseException:
            self.status.update(status='failed', error=traceback.format_exc())
            print(self.status['error'], flush=True)
        finally:
            errors = self.cleanup()
            if errors:
                self.status.update(status='failed', cleanup_errors=errors)
            write(self.out / 'result.json', self.status)
            # Omit the transient carrier (its registered zero pages are restored).
            archive = self.out.with_suffix('.tar.gz')
            with tarfile.open(archive, 'w:gz') as tar:
                for path in self.out.iterdir():
                    if path.name not in ('carrier', 'scratch', 'mount', 'notify', 'libiso-copied.so'):
                        tar.add(path, arcname=self.out.name + '/' + path.name)
            print(json.dumps(dict(**self.status, output=str(self.out), archive=str(archive))), flush=True)
        return 0 if self.status['status'] == 'complete' else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--blocks', type=int, default=8)
    p.add_argument('--repeats', type=int, default=3)
    p.add_argument('--client-cpu', type=int, default=1)
    p.add_argument('--server-cpu', type=int, default=2)
    p.add_argument('--functional', action='store_true')
    a = p.parse_args()
    assert a.blocks >= 1 and a.repeats >= 1
    raise SystemExit(Campaign(a).run())


if __name__ == '__main__':
    main()
