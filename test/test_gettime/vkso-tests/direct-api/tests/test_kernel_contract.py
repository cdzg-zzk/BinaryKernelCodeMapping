#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Execute production reader code with deterministic host-only environment fixtures.

This does not emulate kernel memory ordering, boot, page grafting or performance.
The reader algorithm, root adapters, ordinary callers and failure callbacks are
compiled from the repository; only environmental primitives/private input are fake.
Temporary compiler products are removed. VKSO_TEST_ARTIFACTS optionally retains
code-generation evidence outside the source tree (CI uses this).
"""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[2]
KERNEL = HERE.parent / 'linux-5.15.198-vkso'
REPO = HERE.parents[2]
BASE = '09b9505667f1d1c3da71ac8aaaa7d6054255bc62'

COMPAT = r'''
#ifndef CLOCKTIME_HOST_COMPAT_H
#define CLOCKTIME_HOST_COMPAT_H
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <time.h>
#include <sys/time.h>
#include <errno.h>
typedef int64_t s64;
typedef int32_t s32;
typedef uint64_t u64;
typedef uint32_t u32;
typedef uint8_t u8;
typedef int64_t time64_t;
typedef int64_t ktime_t;
typedef long __kernel_old_time_t;
struct timespec64 { time64_t tv_sec; long tv_nsec; };
struct __kernel_old_timeval { long tv_sec, tv_usec; };
enum tk_offsets { TK_OFFS_REAL, TK_OFFS_BOOT, TK_OFFS_TAI };
#define NSEC_PER_SEC 1000000000L
#define NSEC_PER_USEC 1000L
#define LOW_RES_NSEC 1000000L
#define __visible
#define notrace
#define noinline __attribute__((noinline))
#define __noclone __attribute__((noclone))
#define __cold __attribute__((cold))
#define __section(x) __attribute__((section(x)))
#define static_assert _Static_assert
#define likely(x) __builtin_expect(!!(x), 1)
#define unlikely(x) __builtin_expect(!!(x), 0)
#define READ_ONCE(x) (*(volatile __typeof__(x) *)&(x))
#define WRITE_ONCE(x, v) (*(volatile __typeof__(x) *)&(x) = (v))
#define barrier() __asm__ volatile("" ::: "memory")
#define smp_rmb() barrier()
#define cpu_relax() barrier()
#define WARN_ON(x) ((void)(x))
extern int timekeeping_suspended;
extern struct timezone sys_tz;
static inline ktime_t timespec64_to_ktime(struct timespec64 ts)
{ return ts.tv_sec * NSEC_PER_SEC + ts.tv_nsec; }
static inline u64 __iter_div_u64_rem(u64 n, u32 d, u64 *r)
{ *r = n % d; return n / d; }
#endif
'''


def definition(text, name):
    """Extract one complete top-level C definition, not a second algorithm copy."""
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', lambda m: '\n' * m[0].count('\n'), text,
                   flags=re.S)
    pattern = re.compile(r'(?m)^[\w \t*]+\n?(?:' + re.escape(name) +
                         r')\s*\([^;{}]*\)\s*\{')
    matches = list(pattern.finditer(clean))
    if len(matches) != 1:
        raise ValueError(f'expected one definition of {name}, got {len(matches)}')
    m = matches[0]
    depth = 1
    end = m.end()
    while depth and end < len(clean):
        depth += (clean[end] == '{') - (clean[end] == '}')
        end += 1
    if depth:
        raise ValueError('unterminated definition: ' + name)
    return clean[m.start():end] + '\n'


def run(args, **kw):
    return subprocess.run(list(map(str, args)), check=True, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=60, **kw).stdout


class KernelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='clocktime-contract-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.out = Path(cls.temp.name)
        cls.cc = os.environ.get('CC', 'gcc')
        cls.headers = cls.out / 'include'
        stubs = ['linux/types.h', 'linux/compiler.h', 'linux/compiler_types.h',
                 'linux/time.h', 'linux/time64.h', 'linux/stddef.h', 'linux/build_bug.h',
                 'asm/clocksource.h', 'vdso/ktime.h', 'vdso/math64.h']
        cls.headers.mkdir()
        (cls.headers / 'host_compat.h').write_text(COMPAT)
        for name in stubs:
            path = cls.headers / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('#include "host_compat.h"\n')
        (cls.headers / 'vdso/clocksource.h').write_text(
            '#define VDSO_CLOCKMODE_NONE 0\n#define VDSO_CLOCKMODE_TSC 1\n'
            '#define VDSO_CLOCKMODE_PVCLOCK 2\n#define VDSO_CLOCKMODE_HVCLOCK 3\n')
        (cls.headers / 'asm/msr.h').write_text(
            '#include "host_compat.h"\nextern u64 host_counter(void);\n'
            '#define rdtsc_ordered() host_counter()\n')
        cls.flags = ['-O2', '-std=gnu11', '-D_GNU_SOURCE', '-Wall', '-Wextra', '-Werror',
                     '-Wno-unused-parameter', '-fno-strict-aliasing', '-fno-stack-protector',
                     '-fno-optimize-sibling-calls', '-I' + str(cls.headers),
                     '-I' + str(KERNEL / 'include')]
        callers = (KERNEL / 'kernel/time/timekeeping.c').read_text()
        names = ['ktime_get_real_ts64', 'ktime_get_ts64', 'ktime_get_raw_ts64',
                 'ktime_get', 'ktime_get_raw', 'ktime_get_with_offset']
        (cls.out / 'callers.inc').write_text(''.join(definition(callers, n) for n in names))
        (cls.out / 'callbacks.inc').write_text(
            definition((KERNEL / 'kernel/time/posix-timers.c').read_text(),
                       'vkso_posix_clock_gettime_failure') +
            definition((KERNEL / 'kernel/time/time.c').read_text(),
                       'vkso_kernel_gettimeofday_failure'))
        cls.binary = cls.out / 'contract'
        cls.build_log = run([cls.cc, *cls.flags, '-I' + str(cls.out), '-no-pie',
                            HERE / 'direct-api/tests/kernel_contract.c',
                            KERNEL / 'kernel/time/vkso_time_core.c',
                            KERNEL / 'kernel/time/vkso_time_cycles.c', '-o', cls.binary])

    def check_case(self, case):
        self.assertIn('PASS ' + case, run([self.binary, case]))

    def test_hres_against_integer_oracle(self):
        self.check_case('hres')

    def test_coarse_resolution_seconds(self):
        self.check_case('coarse')

    def test_user_failure_propagated_and_offset_not_reapplied(self):
        self.check_case('user-failure')

    def test_actual_kernel_callback_completes_once(self):
        self.check_case('kernel-failure')

    def test_ordinary_and_scalar_callers_on_success(self):
        self.check_case('callers')

    def test_root_rejects_native_clocks_without_touching_output(self):
        self.check_case('unsupported')

    def test_retry_rejects_mixed_generation(self):
        self.check_case('retry')

    def test_getcpu_kernel_completion_and_optional_outputs(self):
        self.check_case('getcpu')

    def test_root_codegen_removes_second_private_fallback(self):
        source = self.out / 'codegen.c'
        source.write_text('#include <linux/vkso_time.h>\n#include <linux/vkso_getcpu.h>\n'
                          '#include "callers.inc"\n'
                          'int cpu_adapter(unsigned *c, unsigned *n) { return vkso_getcpu(c,n); }\n')
        current = self.out / 'current.o'
        run([self.cc, *self.flags, '-I' + str(self.out), '-c', source, '-o', current])
        symbols = run(['nm', '-u', current])
        self.assertNotIn('vkso_timekeeping_get_private', symbols)
        self.assertIn('vkso_clock_gettime_hres', symbols)
        dump = run(['objdump', '-dr', current])
        artifacts = os.environ.get('VKSO_TEST_ARTIFACTS')
        if artifacts:
            target = Path(artifacts)
            target.mkdir(parents=True, exist_ok=True)
            (target / 'root-current.txt').write_text(dump)
            (target / 'root-current-symbols.txt').write_text(run(['nm', '-S', current]))
            (target / 'root-compiler.txt').write_text(run([self.cc, '--version']))
        # A fixed historical header demonstrates that this test catches the
        # original duplicate responsibility, not just a fake callee definition.
        base = run(['git', '-C', REPO, 'show', BASE + ':' +
                    str((KERNEL / 'include/linux/vkso_time.h').relative_to(REPO))])
        old = self.out / 'old/include/linux/vkso_time.h'
        old.parent.mkdir(parents=True)
        old.write_text(base)
        before = self.out / 'before.o'
        run([self.cc, '-I' + str(old.parents[1]), *self.flags, '-I' + str(self.out),
             '-c', source, '-o', before])
        self.assertIn('vkso_timekeeping_get_private', run(['nm', '-u', before]))
        if artifacts:
            (target / 'root-before.txt').write_text(run(['objdump', '-dr', before]))
            (target / 'root-before-symbols.txt').write_text(run(['nm', '-S', before]))
            (target / 'source.sha256').write_text(''.join(
                hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + str(p.relative_to(REPO)) + '\n'
                for p in [KERNEL / 'include/linux/vkso_time.h',
                          KERNEL / 'include/linux/vkso_getcpu.h',
                          KERNEL / 'kernel/time/vkso_time_core.c']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
