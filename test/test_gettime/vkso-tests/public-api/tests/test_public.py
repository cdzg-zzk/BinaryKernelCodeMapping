#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Unprivileged source tests. Mock carrier/commands are NOT kernel evidence."""
import csv
import hashlib
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
import build
import collect
import summarize
CPU = min(os.sched_getaffinity(0))


def execute(command, **kwargs):
    return subprocess.run([str(x) for x in command], text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def rows(repeats=3, offset=0, implementation='native-libc'):
    return [dict(zip(collect.FIELDS, [collect.PROTOCOL, implementation, api,
            str(r), '500', '5000', '10.000000000', '2', '2', 'OK']))
            for r in range(offset, repeats + offset) for api in sorted(collect.APIS)]


def checksums(root):
    (root / 'SHA256SUMS').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + str(p.relative_to(root)) + '\n'
        for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS'))


class NativeAndAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='vkso-public-TEST-ONLY-')
        cls.out = Path(cls.temp.name)
        cc = os.environ.get('CC', 'gcc')
        flags = ['-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fno-lto']
        inc = ['-I' + str(HERE), '-I' + str(HERE.parent / 'functional')]
        commands = [
            [cc, *flags, *inc, '-fPIC', '-shared', '-Wl,-Bsymbolic', '-Wl,-soname,libkernel.so',
             '-I' + str(HERE.parents[1] / 'linux-5.15.198-vkso/include'),
             HERE.parent / 'functional/vkso_user_entry.S', HERE / 'tests/mock_core.c',
             '-o', cls.out / 'libkernel.so'],
            [cc, *flags, *inc, '-fPIC', '-pie', HERE / 'tests/test_api.c',
             HERE.parent / 'functional/vkso_user_wrapper.c', '-L' + str(cls.out),
             '-Wl,--no-as-needed', '-lkernel', '-Wl,-rpath,' + str(cls.out),
             '-pthread', '-o', cls.out / 'test-api'],
            [cc, *flags, HERE / 'public_time_bench.c', '-o', cls.out / 'raw'],
            [cc, *flags, *inc, '-DVKSO_BACKEND', HERE / 'public_time_bench.c',
             HERE.parent / 'functional/vkso_user_wrapper.c', '-L' + str(cls.out),
             '-Wl,--no-as-needed', '-lkernel', '-Wl,-rpath,' + str(cls.out), '-o', cls.out / 'vkso'],
        ]
        for command in commands:
            result = execute(command)
            if result.returncode:
                raise RuntimeError(result.stderr)
        cls.env = os.environ.copy()
        cls.env.pop('LD_PRELOAD', None)
        cls.env.pop('LD_AUDIT', None)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def bench(self, name, *args, env=None):
        return execute([self.out / name, '--cpu', CPU, *args], env=env or self.env)

    def test_real_assembly_with_mock_core(self):
        result = execute([self.out / 'test-api'], env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('mock_assembly_api_checks=37 PASS', result.stdout)

    def test_native_supported_api_smoke(self):
        for api in sorted(collect.APIS - {'clock_gettime_realtime_alarm_fallback'}):
            with self.subTest(api=api):
                result = self.bench('raw', '--api', api, '--iterations', 1000, '--repeats', 2, '--warmup', 10)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = list(csv.DictReader(result.stdout.splitlines()))
                self.assertEqual(len(data), 2)
                self.assertTrue(all(r['api'] == api and r['status'] == 'OK' for r in data))

    def test_host_alarm_support_is_explicit(self):
        result = self.bench('raw', '--api', 'clock_gettime_realtime_alarm_fallback', '--check')
        if result.returncode and 'errno=22' in result.stderr:
            self.skipTest('host alarm clock returns EINVAL; target matrix still requires it')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_fastpath_syscall_denial(self):
        result = self.bench('raw', '--api', 'clock_gettime_monotonic', '--check-fastpath')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('syscall_denial_fastpath=PASS', result.stderr)

    def test_mock_cannot_pass_fastpath_denial(self):
        result = self.bench('vkso', '--api', 'clock_gettime_monotonic', '--check-fastpath')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('syscall-denial failure: getcpu_both', result.stderr)

    def test_mock_direct_caller_smoke(self):
        result = self.bench('vkso', '--api', 'clock_gettime_monotonic', '--iterations', 1000,
                            '--repeats', 2, '--warmup', 10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('vkso-direct', result.stdout)

    def test_linkage_has_no_adapter_or_resolver(self):
        for name in ('raw', 'vkso'):
            dynamic = execute(['readelf', '-dW', self.out / name]).stdout
            symbols = execute(['nm', '-u', self.out / name]).stdout
            self.assertEqual('Shared library: [libkernel.so]' in dynamic, name == 'vkso')
            self.assertNotIn('adapter.so', dynamic)
            self.assertNotIn('dlsym', symbols)
            self.assertNotIn('dlopen', symbols)
            if name == 'raw':
                self.assertNotIn('__vkso_', symbols)

    def test_invalid_arguments_refused(self):
        for args in (('--iterations', '0'), ('--repeats', '0'), ('--cpu', '-1'),
                     ('--warmup', '-1'), ('--api', 'unknown'), ('--bad', '1'),
                     ('--iterations', 'nan'), ('--iterations', '99999999999999999999')):
            with self.subTest(args=args):
                self.assertEqual(self.bench('raw', *args).returncode, 2)

    def test_preload_refused(self):
        env = self.env.copy()
        env['LD_PRELOAD'] = ''
        result = self.bench('raw', '--check', env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn('forbidden', result.stderr)

    def test_builder_refuses_fixture(self):
        package = self.out / 'mock.building-1'
        package.mkdir()
        shutil.copy2(self.out / 'libkernel.so', package / 'libkernel.so')
        checksums(package)
        with self.assertRaisesRegex(ValueError, 'fixture'):
            build.build(package, os.environ.get('CC', 'gcc'))
        self.assertFalse((package / 'public-api').exists())

    def test_packaging_pipeline_with_mocked_admission(self):
        # Real compiler/ELF/archive/checksum operations, but not a deployable package.
        package = self.out / 'pipeline.building-2'
        package.mkdir()
        shutil.copy2(self.out / 'libkernel.so', package / 'libkernel.so')
        checksums(package)
        real_run = build.run
        def admitted(command, **kwargs):
            result = real_run(command, **kwargs)
            if list(command[:2]) == ['readelf', '-Ws']:
                result.stdout = result.stdout.replace('vkso_fixture_marker', 'admission_stub')
            return result
        with patch.object(build, 'run', admitted):
            meta = build.build(package, os.environ.get('CC', 'gcc'))
        self.assertEqual(meta['runtime_validation'], 'NOT_RUN')
        self.assertTrue((package / 'public-api/source/vkso_user_wrapper.c').is_file())
        self.assertEqual(execute(['sha256sum', '-c', 'SHA256SUMS'], cwd=package).returncode, 0)


class DataAndOrchestrationTests(unittest.TestCase):
    def test_complete_matrix(self):
        collect.validate_rows(rows(), 'native-libc', 3, 500)

    def test_missing_duplicate_empty_rejected(self):
        data = rows()
        for changed in (data[:-1], data + [data[0]], []):
            with self.assertRaises(ValueError):
                collect.validate_rows(changed, 'native-libc', 3, 500)
        with self.assertRaises(ValueError):
            collect.validate_rows([], 'native-libc', 0, 500)

    def test_corrupt_fields_rejected(self):
        for field, value in [('protocol', 'old-vdso'), ('implementation', 'vkso-direct'),
                             ('status', 'MIGRATED'), ('aux_end', '3'),
                             ('tsc_cycles_per_call', 'nan'), ('tsc_cycles_per_call', 'inf'),
                             ('tsc_cycles_per_call', '11'), ('tsc_cycles_total', '0'),
                             ('iterations', '501'), ('api', 'unknown'), ('repeat', '100')]:
            with self.subTest(field=field):
                data = rows()
                data[0][field] = value
                with self.assertRaises(ValueError):
                    collect.validate_rows(data, 'native-libc', 3, 500)

    def test_process_offsets(self):
        data = rows(2) + rows(1, 2)
        collect.validate_rows(data, 'native-libc', 3, 500)
        with self.assertRaises(ValueError):
            collect.validate_rows(data, 'native-libc', 3, 500, 1)

    def test_boot_estimator_and_four_groups(self):
        data = []
        for variant in ('normal', 'no-retpoline'):
            for backend, costs in [('raw', [10, 20]), ('vkso', [30])]:
                data += [dict(case=backend + '-' + variant, api='a', tsc_cycles_per_call=x) for x in costs]
        result = summarize.comparisons(data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['raw_boots'], 2)
        self.assertEqual(result[0]['cost_ratio'], 2)
        with self.assertRaisesRegex(ValueError, 'four'):
            summarize.comparisons(data[:3])

    def test_result_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('manifest.json', 'build-manifest.json', 'public.csv'):
                (root / name).write_text('fixture')
            checksums(root)
            summarize.verify_result_files(root)
            (root / 'public.csv').write_text('corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                summarize.verify_result_files(root)

    def test_duplicate_boot_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for index in range(2):
                directory = Path(tmp) / str(index) / 'raw-normal/public'
                directory.mkdir(parents=True)
                (directory.parent / 'complete').write_text('case=raw-normal\nstatus=complete\n')
                (directory / 'manifest.json').write_text(json.dumps(dict(
                    protocol=collect.PROTOCOL, status='complete', boot_id='same-boot',
                    case='raw-normal', backend='raw', implementation='native-libc',
                    repeats=3, iterations=500, warmup=10, cpu=2, processes=2, libc=['fixture', '1'])))
                (directory / 'build-manifest.json').write_text(json.dumps(dict(
                    cc_version='fixture', flags=[], sources={}, libc_version='fixture')))
                with (directory / 'public.csv').open('w', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=collect.FIELDS)
                    writer.writeheader(); writer.writerows(rows())
                checksums(directory)
            with self.assertRaisesRegex(ValueError, 'reused boot_id'):
                summarize.load_boots([tmp])

    def test_balanced_order(self):
        script = (HERE.parent / 'baremetal/experiment.sh').read_text()
        prefix = script[script.index('# Preplanned'):script.index('\nmanifest_value()')]
        orders = []
        for block in range(4):
            env = dict(os.environ, PUBLIC_BLOCK=str(block))
            result = execute(['bash', '-eu', '-c', prefix + '\nprintf "%s\\n" "${FULL_CASES[*]}"'], env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            orders.append(result.stdout.split())
        expected = {'raw-normal', 'vkso-normal', 'raw-no-retpoline', 'vkso-no-retpoline'}
        self.assertTrue(all(set(order) == expected for order in orders))
        self.assertTrue(all(len({o[i] for o in orders}) == 4 for i in range(4)))
        self.assertEqual(len({(o[i], o[i + 1]) for o in orders for i in range(3)}), 12)
        env['PUBLIC_BLOCK'] = '$(false)'
        self.assertEqual(execute(['bash', '-eu', '-c', prefix], env=env).returncode, 2)

    def test_shell_syntax_and_defaults(self):
        for name in ('build-all.sh', 'collect-case.sh', 'experiment.sh'):
            result = execute(['bash', '-n', HERE.parent / 'baremetal' / name])
            self.assertEqual(result.returncode, 0, result.stderr)
        conf = (HERE.parent / 'baremetal/experiment.conf').read_text()
        self.assertIn('MACRO_ENABLED=0', conf)
        self.assertIn('PMU=0', conf)
        self.assertIn('EXPERIMENT_SCHEMA=5', conf)

    def test_completed_package_cannot_be_modified(self):
        with self.assertRaisesRegex(ValueError, 'new build-all'):
            build.build('/tmp/final-normal', 'gcc')

    def test_simulated_collector_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / 'package'
            tools = package / 'public-api'
            (tools / 'source').mkdir(parents=True)
            (tools / 'source/fixture.txt').write_text('simulation, not runtime evidence')
            (tools / 'raw-public-bench').write_text('never executed')
            (tools / 'manifest.json').write_text(json.dumps(dict(
                protocol=collect.PROTOCOL, api_count=17, carrier_sha256='fixture')))
            for name in ('boot-manifest.txt', 'source.patch', 'SHA256SUMS'):
                (package / name).write_text('simulation')
            args = SimpleNamespace(package=package, output=Path(tmp) / 'public', backend='raw',
                case='raw-normal', run_id='simulation', cpu=CPU, repeats=3,
                iterations=500, processes=2, warmup=10)
            actual_run = subprocess.run
            def child(command, **kwargs):
                if command[0] != 'setarch':
                    return actual_run(command, **kwargs)
                if '--repeats' in command:
                    repeat = int(command[command.index('--repeats') + 1])
                    offset = int(command[command.index('--offset') + 1])
                    writer = csv.DictWriter(kwargs['stdout'], fieldnames=collect.FIELDS)
                    writer.writeheader(); writer.writerows(rows(repeat, offset))
                else:
                    kwargs['stdout'].write('simulated diagnostic\n')
                return subprocess.CompletedProcess(command, 0)
            with patch.object(collect.subprocess, 'run', child):
                collect.collect(args)
            summarize.verify_result_files(args.output)
            args.output = Path(tmp) / 'failure'
            with patch.object(collect.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'fixture')):
                with self.assertRaises(subprocess.CalledProcessError):
                    collect.collect(args)
            self.assertFalse((args.output / 'manifest.json').exists())

    def mock_release(self, restore_status=0, active=0, unload_status=0):
        script = (HERE.parent / 'baremetal/collect-case.sh').read_text()
        function = script[script.index('release_resources()'):script.index('\ncleanup()')]
        guarded = script[script.index('run_guarded()'):script.index('# Kept as a separate')]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = root / 'manager'
            manager.write_text('#!/bin/sh\nprintf "restore\\n" >>"$LOG"\nexit "$RESTORE_STATUS"\n')
            manager.chmod(0o755)
            program = guarded + function + '''
rmmod() { echo "unload:$1" >>"$LOG"; return "$UNLOAD_STATUS"; }
systemctl() { echo "irqbalance" >>"$LOG"; }
module_loaded=1; clock_module_loaded=1; replaced=1; irqbalance_was_active=1
release_resources
status=$?
echo "result:$status:$module_loaded:$replaced"
'''
            env = dict(os.environ, PACKAGE=tmp, PARTIAL=tmp, LOG=str(root / 'calls'),
                       RESTORE_STATUS=str(restore_status), UNLOAD_STATUS=str(unload_status),
                       operation_active=str(active))
            result = execute(['bash', '-u', '-c', program], env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            log = (root / 'calls').read_text() if (root / 'calls').exists() else ''
            return result.stdout, log

    def test_mock_restore_failure_keeps_backing(self):
        output, log = self.mock_release(restore_status=1)
        self.assertIn('result:1:1:1', output)
        self.assertIn('restore', log)
        self.assertNotIn('unload:page_cache_replace', log)

    def test_mock_successful_release(self):
        output, log = self.mock_release()
        self.assertIn('result:0:0:0', output)
        self.assertIn('unload:page_cache_replace', log)

    def test_mock_active_child_prevents_restore(self):
        output, log = self.mock_release(active=1)
        self.assertIn('result:1:1:1', output)
        self.assertEqual(log, '')

    def test_partial_replace_and_signal_guards(self):
        script = (HERE.parent / 'baremetal/collect-case.sh').read_text()
        self.assertLess(script.index('replaced=1\n\trun_guarded'), script.index('run_guarded "$PACKAGE/manager" replace'))
        self.assertIn("trap 'exit 143' TERM", script)
        self.assertLess(script.index('release_resources || exit 1'), script.index("printf 'case=%s\\nstatus=complete"))


if __name__ == '__main__':
    unittest.main(verbosity=2)
