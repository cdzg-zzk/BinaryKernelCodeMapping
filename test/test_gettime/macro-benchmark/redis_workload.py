#!/usr/bin/env python3
"""Unmodified Redis server and redis-benchmark, with server-only time bridge."""
import argparse
import csv
import io
import json
import os
import resource
import signal
from pathlib import Path
import socket
import subprocess
import time


def run(args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    p = argparse.ArgumentParser()
    p.add_argument('build', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--method', choices=['native', 'vdso', 'vkso', 'compact-split'], required=True)
    p.add_argument('--carrier', type=Path)
    p.add_argument('--audit', action='store_true')
    p.add_argument('--requests', type=int, default=3000000)
    p.add_argument('--rounds', type=int, default=7)
    p.add_argument('--warmup', type=int, default=200000)
    p.add_argument('--server-cpu', type=int, default=1)
    p.add_argument('--client-cpus', default='2,3')
    a = p.parse_args()
    build = a.build.resolve(); out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    server_cpu = a.server_cpu
    client_cpus = set(map(int, a.client_cpus.split(',')))
    online = set(range(os.cpu_count()))
    assert server_cpu in online and client_cpus <= online
    assert server_cpu not in client_cpus and len(client_cpus) == 2
    os.sched_setaffinity(0, {0})
    port = 16379
    with socket.socket() as available:
        available.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        available.bind(('127.0.0.1', port))  # Refuse an already occupied service port.
    env = dict(os.environ)
    env.pop('LD_PRELOAD', None)
    client_env = {**env, 'LD_PRELOAD': str(build / 'adapter.so'),
                  'CLOCKTIME_BACKEND': 'syscall'}
    if a.method != 'native':
        env.update(LD_PRELOAD=str(build / ('adapter-audit.so' if a.audit else 'adapter.so')),
                   CLOCKTIME_BACKEND='vkso' if a.method == 'compact-split' else a.method,
                   CLOCKTIME_AUDIT_FILE=str(out / 'calls.json'))
        if a.carrier: env['CLOCKTIME_CARRIER'] = str(a.carrier.resolve())
    server = [build / 'redis-server', '--bind', '127.0.0.1', '--port', str(port),
              '--save', '', '--appendonly', 'no', '--protected-mode', 'yes',
              '--daemonize', 'no', '--loglevel', 'notice', '--dir', out]
    if a.audit:
        # Functional run: a hidden syscall substitution cannot pass this filter.
        server.insert(0, build / 'check-adapter')
    server = ['setarch', os.uname().machine, '-R', *server]
    log = (out / 'server.log').open('w')
    proc = subprocess.Popen(list(map(str, server)), env=env, stdout=log, stderr=subprocess.STDOUT,
                            preexec_fn=lambda: os.sched_setaffinity(0, {server_cpu}))
    cli = [build / 'redis-cli', '-p', str(port)]
    (out / 'execution.json').write_text(json.dumps(dict(
        server=list(map(str, server)), method=a.method, client_timing='syscall on all kernels',
        server_cpu=server_cpu, client_cpus=sorted(client_cpus),
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()), indent=2))
    rows = []
    try:
        for attempt in range(100):
            if proc.poll() is not None: raise RuntimeError('Redis failed to start; see server.log')
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=.2) as s:
                    s.sendall(b'*1\r\n$4\r\nPING\r\n'); assert s.recv(64) == b'+PONG\r\n'
                break
            except OSError: time.sleep(.05)
        else: raise RuntimeError('Redis startup timeout')
        (out / 'server.maps').write_text(Path(f'/proc/{proc.pid}/maps').read_text())
        (out / 'server.smaps').write_text(Path(f'/proc/{proc.pid}/smaps').read_text())
        run(cli + ['INFO'], stdout=(out / 'info-before.txt').open('w'))
        # redis-benchmark substitutes __rand_int__ with a 12-digit decimal key.
        payload = bytearray()
        for i in range(10000):
            key = f'key:{i:012d}'.encode(); value = b'x' * 64
            payload += b'*3\r\n$3\r\nSET\r\n$' + str(len(key)).encode() + b'\r\n' + key
            payload += b'\r\n$64\r\n' + value + b'\r\n'
        run(cli + ['--pipe'], input=payload, stdout=(out / 'populate.log').open('w'))
        assert run(cli + ['DBSIZE'], capture_output=True, text=True).stdout.strip() == '10000'
        cases = [('get', 1), ('set', 1), ('get', 16), ('set', 16)]
        for round_number in range(a.rounds):
            # Rotate order without discarding difficult or slower cases.
            for command, pipeline in cases[round_number % 4:] + cases[:round_number % 4]:
                base = ['setarch', os.uname().machine, '-R', build / 'redis-benchmark', '-h', '127.0.0.1', '-p', port,
                        '-c', 50, '--threads', 2, '-P', pipeline, '-d', 64, '-r', 10000,
                        '-t', command, '--csv']
                def bench(count):
                    return run(base + ['-n', count], capture_output=True, text=True,
                               env=client_env,
                               preexec_fn=lambda: os.sched_setaffinity(0, client_cpus))
                warm = bench(a.warmup)
                name = f'{round_number:02d}-{command}-p{pipeline}'
                (out / (name + '-warmup.csv')).write_text(warm.stdout)
                def server_ticks():
                    fields = Path(f'/proc/{proc.pid}/stat').read_text().rsplit(')', 1)[1].split()
                    return int(fields[11]) + int(fields[12])
                ticks_before = server_ticks()
                client_before = resource.getrusage(resource.RUSAGE_CHILDREN)
                started = time.monotonic()
                result = bench(a.requests)
                elapsed = time.monotonic() - started
                client_after = resource.getrusage(resource.RUSAGE_CHILDREN)
                server_seconds = (server_ticks() - ticks_before) / os.sysconf('SC_CLK_TCK')
                (out / (name + '.csv')).write_text(result.stdout)
                (out / (name + '.stderr')).write_text(result.stderr)
                records = list(csv.DictReader(io.StringIO(result.stdout)))
                assert len(records) == 1, result.stdout
                rows.append(dict(method=a.method, round=round_number, command=command,
                    pipeline=pipeline, requests=a.requests, wall_seconds=elapsed,
                    server_cpu_seconds=server_seconds,
                    client_cpu_seconds=(client_after.ru_utime + client_after.ru_stime -
                                        client_before.ru_utime - client_before.ru_stime), **records[0]))
        final_info = run(cli + ['INFO'], capture_output=True, text=True).stdout
        (out / 'info-after.txt').write_text(final_info)
        info = dict(line.split(':', 1) for line in final_info.splitlines() if ':' in line)
        assert info['monotonic_clock'] == 'POSIX clock_gettime'
        assert int(info['keyspace_misses']) == 0
        assert int(info['keyspace_hits']) >= 2 * a.rounds * (a.requests + a.warmup)
    finally:
        if proc.poll() is None:
            proc.terminate()  # Redis handles SIGTERM; only signal the process we own.
            try: proc.wait(timeout=15)
            except subprocess.TimeoutExpired: proc.terminate(); proc.wait(timeout=5)
        log.close()
    assert proc.returncode == 0, proc.returncode
    if a.audit and a.method != 'native':
        calls = json.loads((out / 'calls.json').read_text())
        assert calls['clock_gettime'] > 0 and calls['gettimeofday'] > 0
        assert calls['clock_ids'][1] > 0
    with (out / 'measurements.csv').open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (out / 'complete.json').write_text(json.dumps(dict(status='pass', method=a.method,
        scope='functional syscall-denial' if a.audit else 'application timing',
        rounds=a.rounds, requests=a.requests, warmup=a.warmup, server_cpu=server_cpu,
        client_cpus=sorted(client_cpus), cases=cases), indent=2) + '\n')
    print('redis_workload=pass', flush=True)


if __name__ == '__main__': main()
