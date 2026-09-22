#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Source/caller tests plus native-host smoke. Never claim target-kernel PASS."""
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import bundle
import results
import collect


def run(argv, **kwargs):
    return subprocess.run([str(x) for x in argv], check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs).stdout


def samples():
    record = dict(repeats=3, processes=2, cpu=2, backend='native-libc', iterations=100)
    rows = []
    for process, count in ((0, 2), (1, 1)):
        for repeat in range(count):
            for name in results.CASE_NAMES:
                rows.append(dict(protocol=bundle.PROTOCOL, backend='native-libc', case=name,
                                 process_index=str(process), round=str(repeat), iterations='100',
                                 tsc_ticks='5000', ticks_per_call='50.000000000', cpu='2',
                                 aux_start='2', aux_end='2', checksum='0'))
    return rows, record


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='vkso-direct-TEST-ONLY-')
        cls.out = Path(cls.temp.name)
        cls.cc = os.environ.get('CC', 'gcc')
        cls.cpu = min(os.sched_getaffinity(0))
        (cls.out / 'carrier').mkdir()
        flags = ['-D_GNU_SOURCE', '-O2', '-g', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                 '-fno-lto', '-fno-builtin', '-I' + str(HERE), '-I' + str(HERE.parent / 'functional')]
        cls.flags = flags
        run([cls.cc, *flags, '-fPIC', '-shared', HERE / 'tests/mock_carrier.c',
             '-Wl,-soname,libkernel.so', '-o', cls.out / 'carrier/libkernel.so'])
        cls.build_log = run(['make', '-C', HERE, 'native', 'vkso', 'OUT=' + str(cls.out), 'CC=' + cls.cc])
        cls.native_probe = run([cls.out / 'native-bench', '--probe'])
        cls.native_probe_fields = dict(
            line.split('=', 1) for line in cls.native_probe.splitlines() if '=' in line)
        cls.raw_host = (cls.native_probe_fields.get('native_vdso') == '1' and
                        cls.native_probe_fields.get('vkso_mm_auxv') == '0')
        run([cls.cc, *flags, HERE / 'tests/test_api.c', cls.out / 'libvkso_time_init.a', '-pthread',
             '-L' + str(cls.out / 'carrier'), '-lkernel', '-Wl,-rpath,' + str(cls.out / 'carrier'),
             '-o', cls.out / 'test-api'])

    def require_raw_host(self):
        if not self.raw_host:
            self.skipTest(
                'native runtime smoke requires a Raw boot '
                f"(native_vdso={self.native_probe_fields.get('native_vdso', 'missing')}, "
                f"vkso_mm_auxv={self.native_probe_fields.get('vkso_mm_auxv', 'missing')})")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_mock_direct_link_api_errno_threads_once(self):
        output = run([self.out / 'test-api'], env=dict(os.environ, VKSO_TEST_MODE='success'))
        self.assertIn('MOCK direct-link', output)

    def test_mock_initialization_failure_paths(self):
        for mode in ('missing', 'shared-version', 'mm-version', 'mask', 'bind'):
            with self.subTest(mode=mode):
                output = run([self.out / 'test-api'], env=dict(os.environ, VKSO_TEST_MODE=mode))
                self.assertIn('MOCK initializer failure', output)

    def test_real_functional_inputs_match_pinned_git_blobs(self):
        for name, expected in bundle.FUNCTIONAL_BLOBS.items():
            data = (HERE.parent / 'functional' / name).read_bytes()
            self.assertEqual(hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(), expected)

    def test_native_and_vkso_link_disassembly_audit(self):
        for name in ('native', 'vkso'):
            dynamic, undefined, assembly = bundle.audit_binary(self.out / (name + '-bench'), name)
            self.assertNotIn('adapter.so', dynamic)
            self.assertNotIn('dlopen', undefined)
            self.assertGreaterEqual(assembly.count('rdtscp'), 2 * len(results.CASE_NAMES))

    def test_native_fast_api_check(self):
        self.require_raw_host()
        output = run([self.out / 'native-bench', '--check', '--fast-only', '--cpu', self.cpu])
        self.assertIn('public_api_check=PASS scope=fast-only', output)

    def test_native_no_time_syscall_diagnostic(self):
        self.require_raw_host()
        output = run([self.out / 'native-bench', '--check-fast', '--cpu', self.cpu])
        self.assertIn('time_syscall_denial_check=PASS', output)

    def test_native_smoke_csv_not_accepted_as_formal_full_matrix(self):
        self.require_raw_host()
        output = run([self.out / 'native-bench', '--bench', '--fast-only', '--cpu', self.cpu,
                      '--iterations', 1000, '--warmup', 100, '--repeats', 2])
        rows = list(csv.DictReader(io.StringIO(output)))
        self.assertEqual(len(rows), 26)
        for row in rows:
            self.assertEqual(row['protocol'], bundle.PROTOCOL)
            self.assertGreater(float(row['ticks_per_call']), 0)
        with self.assertRaises(ValueError):
            results.validate_rows(rows, dict(repeats=2, processes=1, cpu=self.cpu,
                                             iterations=1000, backend='native-libc'))

    def test_native_probe_not_kernel_evidence(self):
        fields = self.native_probe_fields
        self.assertEqual(fields.get('protocol'), bundle.PROTOCOL)
        self.assertEqual(fields.get('backend'), 'native-libc')
        self.assertIn(fields.get('native_vdso'), ('0', '1'))
        self.assertIn(fields.get('vkso_mm_auxv'), ('0', '1'))
        self.assertEqual(fields.get('measurement_unit'), 'tsc_ticks_per_call')

    def test_bad_benchmark_arguments_refused(self):
        for args in ([], ['--bench'], ['--bench', '--cpu', '-1'],
                     ['--bench', '--cpu', str(self.cpu), '--iterations', '0'],
                     ['--probe', '--check']):
            with self.subTest(args=args):
                proc = subprocess.run([str(self.out / 'native-bench'), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertNotEqual(proc.returncode, 0)

    def test_header_cpp_compatibility(self):
        source = self.out / 'header.cc'
        source.write_text('#include "vkso_time.h"\nint f(timespec *p) { return vkso_time_clock_gettime(CLOCK_MONOTONIC, p); }\n')
        run(['g++', '-D_GNU_SOURCE', '-std=c++17', '-Wall', '-Wextra', '-Werror',
             '-I' + str(HERE), '-I' + str(HERE.parent / 'functional'), '-c', source, '-o', self.out / 'header.o'])


class DataTests(unittest.TestCase):
    def test_full_matrix_accepts(self):
        rows, record = samples()
        results.validate_rows(rows, record)

    def test_missing_duplicate_and_extra_refused(self):
        rows, record = samples()
        for invalid in (rows[:-1], rows + [rows[0]], rows + [dict(rows[0], case='invented')]):
            with self.assertRaises(ValueError):
                results.validate_rows(invalid, record)

    def test_metadata_corruption_refused(self):
        for key, value in (('backend', 'bridge-vdso'), ('protocol', 'old'), ('cpu', '1'),
                           ('aux_end', '99'), ('iterations', '200'), ('ticks_per_call', 'NaN'),
                           ('ticks_per_call', '1'), ('tsc_ticks', '0')):
            with self.subTest(key=key, value=value):
                rows, record = samples()
                rows[0][key] = value
                with self.assertRaises(ValueError):
                    results.validate_rows(rows, record)

    def test_insufficient_boots_no_confidence_interval(self):
        import random
        self.assertIsNone(results.ratio_interval([1], [1], random.Random(1)))
        self.assertIsNone(results.ratio_interval([1, 2], [1, 2], random.Random(1)))
        self.assertEqual(results.ratio_interval([10] * 3, [20] * 3, random.Random(1), 100), [2, 2])

    def test_cpu_ranges(self):
        self.assertEqual(collect.cpu_list('1-3,5,8-9'), {1, 2, 3, 5, 8, 9})
        with self.assertRaises(ValueError):
            collect.cpu_list('3-1')

    def test_checksum_missing_and_modified_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'payload').write_text('original')
            digest = bundle.sha256(root / 'payload')
            (root / 'SHA256SUMS').write_text(digest + '  payload\n')
            self.assertEqual(bundle.verify_sums(root, {'payload'})['payload'], digest)
            with self.assertRaises(ValueError):
                bundle.verify_sums(root, {'not-there'})
            (root / 'payload').write_text('changed')
            with self.assertRaises(ValueError):
                bundle.verify_sums(root)

    def test_checksum_escape_and_duplicates_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in ('../secret', '/absolute'):
                with self.assertRaises(ValueError):
                    bundle.checked_path(root, path)
            (root / 'x').write_text('x')
            line = bundle.sha256(root / 'x') + '  x\n'
            (root / 'SHA256SUMS').write_text(line + line)
            with self.assertRaises(ValueError):
                bundle.verify_sums(root)

    def test_write_json_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'file.json'
            bundle.write_json(path, {'original': True})
            with self.assertRaises(FileExistsError):
                bundle.write_json(path, {'original': False})
            self.assertTrue(json.loads(path.read_text())['original'])



def synthetic_run(root, case, boot_id):
    """TEST DATA, not an observation of any machine."""
    root.mkdir()
    rows, record = samples()
    backend = 'native-libc' if case.startswith('raw-') else 'vkso-direct'
    record.update(status='COMPLETE', protocol=bundle.PROTOCOL, case=case, boot_id=boot_id,
                  backend=backend, warmup=10, compiler_version='TEST-ONLY',
                  benchmark_source_sha256='TEST-SOURCE', header_sha256='TEST-HEADER',
                  source_fingerprint='TEST-CODE', base_cflags='TEST-FLAGS',
                  package_manifest_sha256='TEST-PACKAGE', binary_sha256='TEST-BINARY',
                  cpu_info={'model name': 'SYNTHETIC', 'microcode': 'TEST'}, tuning={})
    for row in rows:
        row['backend'] = backend
        if backend == 'vkso-direct':
            row['tsc_ticks'] = '10000'
            row['ticks_per_call'] = '100.0'
    (root / 'run.json').write_text(json.dumps(record))
    with (root / 'samples.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=results.COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    for name in ('check.log', 'check-fast.log', 'legacy-abi.log'):
        (root / name).write_text('SYNTHETIC TEST FIXTURE; NOT runtime evidence\n')
    sums(root)
    return root


def sums(root):
    (root / 'SHA256SUMS').write_text(''.join(bundle.sha256(p) + '  ' + p.name + '\n'
                                           for p in sorted(root.iterdir())
                                           if p.is_file() and p.name != 'SHA256SUMS'))


class WorkflowTests(unittest.TestCase):
    def test_synthetic_four_group_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [synthetic_run(Path(tmp) / case, case, 'TEST-' + case) for case in results.GROUPS]
            data = results.summarize(paths)
            self.assertEqual(len(data['comparisons']), 32)
            for result in data['comparisons']:
                self.assertEqual(result['vkso_over_raw'], 2)
                self.assertIsNone(result['pointwise_bootstrap_95pct'])

    def test_same_boot_and_missing_groups_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = synthetic_run(Path(tmp) / 'a', 'raw-normal', 'TEST-SAME-BOOT')
            b = synthetic_run(Path(tmp) / 'b', 'vkso-normal', 'TEST-SAME-BOOT')
            with self.assertRaisesRegex(ValueError, 'same boot'):
                results.summarize([a, b])
            with self.assertRaisesRegex(ValueError, 'all four'):
                results.summarize([a])

    def test_mixed_sources_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = synthetic_run(Path(tmp) / 'a', 'raw-normal', 'TEST-A')
            b = synthetic_run(Path(tmp) / 'b', 'vkso-normal', 'TEST-B')
            record = json.loads((b / 'run.json').read_text())
            record['header_sha256'] = 'DIFFERENT'
            (b / 'run.json').write_text(json.dumps(record))
            sums(b)
            with self.assertRaisesRegex(ValueError, 'mixed workload'):
                results.summarize([a, b])

    def check_mock_cleanup(self, restore_fails):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package, sidecar, out = root / 'package', root / 'bundle', root / 'result'
            package.mkdir(); sidecar.mkdir()
            (package / 'boot-manifest.txt').write_text('TEST ONLY')
            (sidecar / 'build.json').write_text('{}')
            options = SimpleNamespace(out=out, bundle=sidecar, case='vkso-normal', cpu=2,
                                      iterations=100, warmup=10, repeats=3, processes=2)
            commands = []
            def fake_command(argv, destination, env, timeout=600):
                commands.append(list(argv))
                Path(destination).write_text('MOCKED command; no kernel operation executed\n')
                if len(argv) > 1 and argv[1] == 'replace':
                    raise RuntimeError('injected partial replacement failure')
                if len(argv) > 1 and argv[1] == 'restore' and restore_fails:
                    raise RuntimeError('injected restore failure')
            with patch.object(collect, 'logged', side_effect=fake_command), \
                 patch.object(collect.os, 'sched_setaffinity'), \
                 patch.object(collect.os, 'geteuid', return_value=0), \
                 patch.object(Path, 'is_char_device', return_value=True):
                with self.assertRaises(RuntimeError):
                    collect.collect(options, package, {}, [], {})
            self.assertTrue(any(len(cmd) > 1 and cmd[1] == 'restore' for cmd in commands))
            unloaded = ['rmmod', 'page_cache_replace'] in commands
            self.assertEqual(unloaded, not restore_fails)
            record = json.loads((out / 'run.json').read_text())
            self.assertEqual(record['status'], 'FAIL')
            self.assertEqual(bool(record['cleanup_errors']), restore_fails)
            self.assertIn(['rmmod', 'vkso_m09_clock'], commands)

    def test_mock_partial_replace_attempts_restore(self):
        self.check_mock_cleanup(False)

    def test_mock_failed_restore_does_not_unload_backing(self):
        self.check_mock_cleanup(True)

    def test_logged_command_timeout_kills_own_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'timeout.log'
            with self.assertRaises(subprocess.TimeoutExpired):
                collect.logged([sys.executable, '-c', 'import time; time.sleep(30)'], path,
                               dict(os.environ), timeout=0.05)
            self.assertTrue(path.exists())

    def test_logged_command_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'failure.log'
            with self.assertRaises(RuntimeError):
                collect.logged([sys.executable, '-c', 'print("failure fixture"); exit(3)'], path,
                               dict(os.environ))
            self.assertIn('failure fixture', path.read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
