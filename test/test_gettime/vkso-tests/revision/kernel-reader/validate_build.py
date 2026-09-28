#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Reconstruct and compile reviewed Clocktime objects; never boot or install.

Requires a pristine extracted Linux 5.15.198 tree, GCC/Kbuild prerequisites and
Git history. All reconstruction occurs in a temporary copy. Output retains logs,
configs, object disassembly, source identities and shared-text equality checks.
This is object/code-generation validation, NOT a linked-kernel or timing result.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[5]
PREFIX = 'test/test_gettime/linux-5.15.198-vkso'
READER = 'test/test_gettime/vkso-tests/revision/kernel-reader'
PLATFORM = 'test/test_gettime/vkso-tests/code-size/platform-baseline.json'
BASE = '09b9505667f1d1c3da71ac8aaaa7d6054255bc62'
OBJECTS = ['kernel/time/timekeeping.o', 'kernel/time/posix-timers.o',
           'kernel/time/time.o', 'kernel/sys.o', 'kernel/time/vkso_time_core.o',
           'kernel/time/vkso_time_cycles.o', 'kernel/time/vkso_time.o',
           'arch/x86/kernel/vkso_getcpu.o']
SHARED = ['kernel/time/vkso_time_core.o', 'kernel/time/vkso_time_cycles.o',
          'arch/x86/kernel/vkso_getcpu.o']


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--base', default=BASE)
    p.add_argument('--head', default='HEAD')
    p.add_argument('--cc', default='gcc')
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--variant', choices=['normal', 'no-retpoline'], default='normal')
    a = p.parse_args()
    if not 1 <= a.jobs <= 256:
        p.error('jobs must be in 1..256')
    version = (a.source / 'Makefile').read_text()
    for key, val in [('VERSION', '5'), ('PATCHLEVEL', '15'), ('SUBLEVEL', '198')]:
        import re
        if not re.search(r'^' + key + r'\s*=\s*' + val + r'\s*$', version, re.M):
            p.error('requires pristine Linux 5.15.198 source')
    out = a.out.resolve()
    if out == a.source.resolve() or a.source.resolve() in out.parents:
        p.error('output must be outside the pristine source tree')
    out.mkdir(parents=True, exist_ok=False)
    report = dict(status='FAIL', scope='Kbuild objects only; no boot or performance',
                  variant=a.variant, revisions={}, shared_text={})
    env = dict(os.environ, KBUILD_BUILD_TIMESTAMP='2026-09-28 00:00:00 UTC',
               KBUILD_BUILD_USER='clocktime', KBUILD_BUILD_HOST='validation')
    def run(args, log):
        with (out / log).open('a') as stream:
            stream.write('$ ' + ' '.join(map(str, args)) + '\n'); stream.flush()
            subprocess.run(list(map(str, args)), stdout=stream, stderr=subprocess.STDOUT,
                           env=env, check=True, timeout=600)
    try:
        report['compiler'] = subprocess.check_output([a.cc, '--version'], text=True)
        with tempfile.TemporaryDirectory(prefix='clocktime-kbuild-') as work:
            work = Path(work)
            source = work / 'linux'
            shutil.copytree(a.source, source, symlinks=True)
            edits = json.loads(git('show', a.base + ':' + PLATFORM))
            for item in edits:
                path = Path(item['path'])
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError('invalid platform path')
                target = source / path
                text = target.read_text().splitlines(True) if target.exists() else []
                for edit in reversed(item['edits']):
                    if not 0 <= edit['start'] <= edit['end'] <= len(text):
                        raise ValueError('invalid platform edit: ' + str(path))
                    text[edit['start']:edit['end']] = edit['lines']
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(''.join(text))
            for label, ref in [('base', a.base), ('candidate', a.head)]:
                rev = git('rev-parse', '--verify', ref + '^{commit}').decode().strip()
                report['revisions'][label] = rev
                paths = git('ls-tree', '-r', '--name-only', rev, '--', PREFIX).decode().splitlines()
                for name in paths:
                    target = source / Path(name).relative_to(PREFIX)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(git('show', rev + ':' + name))
                build = work / (label + '-build')
                build.mkdir()
                cmd = ['make', '-C', source, 'O=' + str(build), 'CC=' + a.cc, '-j' + str(a.jobs)]
                run([*cmd, 'defconfig'], label + '.log')
                flags = ['--enable', 'TIME_NS', '--enable', 'MODULES', '--enable', 'DEBUG_FS',
                         '--disable', 'IA32_EMULATION', '--disable', 'X86_X32',
                         '--disable', 'VKSO_TIME_TEST', '--disable', 'DEBUG_INFO',
                         '--disable', 'DEBUG_INFO_BTF', '--disable', 'FUNCTION_TRACER',
                         '--disable', 'STACKPROTECTOR', '--disable', 'STACKPROTECTOR_STRONG',
                         '--set-str', 'SYSTEM_TRUSTED_KEYS', '',
                         '--set-str', 'SYSTEM_REVOCATION_KEYS', '']
                if a.variant == 'no-retpoline':
                    for flag in ['RETPOLINE', 'RETHUNK', 'CPU_UNRET_ENTRY']:
                        flags += ['--disable', flag]
                run([source / 'scripts/config', '--file', build / '.config', *flags], label + '.log')
                run([*cmd, 'olddefconfig'], label + '.log')
                run([*cmd, 'modules_prepare'], label + '.log')
                shutil.copy2(build / '.config', out / (label + '.config'))
                run([*cmd, *OBJECTS], label + '.log')
                module = work / (label + '-module')
                module.mkdir()
                for name in ['Makefile', 'vkso_kernel_reader.c']:
                    (module / name).write_bytes(git('show', rev + ':' + READER + '/' + name))
                run([*cmd, 'M=' + str(module), 'vkso_kernel_reader.o'], label + '.log')
                for obj in OBJECTS + [str(module / 'vkso_kernel_reader.o')]:
                    path = Path(obj) if Path(obj).is_absolute() else build / obj
                    target = label + '-' + path.name
                    run(['objdump', '-dr', path], target + '.disassembly.txt')
                    run(['nm', '-S', '--size-sort', path], target + '.symbols.txt')
                    if obj in SHARED:
                        text = out / (target + '.shared-text')
                        run(['objcopy', '--dump-section', '.vkso.text=' + str(text), path], label + '.log')
                        report['shared_text'].setdefault(obj, {})[label] = digest(text)
            for obj, hashes in report['shared_text'].items():
                if hashes['base'] != hashes['candidate']:
                    raise ValueError('shared text changed: ' + obj)
            if (out / 'base.config').read_bytes() != (out / 'candidate.config').read_bytes():
                raise ValueError('configuration mismatch')
            report['status'] = 'PASS'
    except BaseException as e:
        report['error'] = str(e)
        raise
    finally:
        (out / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        (out / 'SHA256SUMS').write_text(''.join(digest(f) + '  ' + f.name + '\n'
            for f in sorted(out.iterdir()) if f.is_file() and f.name != 'SHA256SUMS'))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
