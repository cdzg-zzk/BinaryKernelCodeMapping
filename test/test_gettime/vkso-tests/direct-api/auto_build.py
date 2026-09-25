#!/usr/bin/env python3
"""Build the four Clocktime packages with one resumable incremental command."""
import hashlib
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

from bundle import kv_file, sha256
from package_check import check as check_read

HERE = Path(__file__).resolve().parent
BARE = HERE.parent / 'baremetal'
UPDATE = HERE.parent / 'update-bench'
ROOT = BARE.parents[3]
ART = BARE / 'artifacts'
KERNEL = ROOT / 'test/test_gettime/linux-5.15.198-vkso'
MODES = ('read', 'update')
VARIANTS = ('normal', 'no-retpoline')
INDEPENDENT_INPUTS = (
    'test/test_gettime/vkso-tests/functional/vkso_user_entry.S',
    'test/test_gettime/vkso-tests/baremetal/symbols.txt',
    'test/test_gettime/vkso-tests/baremetal/shared_data.txt',
    'test/test_gettime/vkso-tests/baremetal/reusable_text.txt',
    'make_dll/shim.txt', 'make_dll/build_PIC_so.py',
)
KERNEL_PACKAGE_INPUTS = (
    'test/test_gettime/vkso-tests/baremetal/base.config',
    'test/test_gettime/vkso-tests/baremetal/baremetal.config',
    'test/test_gettime/vkso-tests/baremetal/path.config',
    'test/test_gettime/vkso-tests/baremetal/vkso_time_bench.c',
    'test/test_gettime/vkso-tests/functional/abi_matrix.c',
    'test/test_gettime/vkso-tests/revision/kernel-reader/vkso_kernel_reader.c',
)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def patch_sections(data):
    parts = data.split(b'diff --git ')
    return {part.split(b' b/', 1)[1].split(b'\n', 1)[0].decode(): part
            for part in parts[1:] if b' b/' in part.split(b'\n', 1)[0]}


def package_check(mode, package):
    if mode == 'read':
        check_read(package)
    else:
        sys.path.insert(0, str(UPDATE))
        from stateful import check
        check(package)


def compiled_inputs_changed(package):
    build = json.loads((package / 'direct/build.json').read_text())
    for name, digest in build['source_hashes'].items():
        current = HERE.parent / name
        if current.suffix in ('.c', '.h') or current.name == 'Makefile':
            if not current.is_file() or sha256(current) != digest:
                return True
    return False


def measured_fingerprint():
    files = sorted(p for p in HERE.rglob('*') if p.is_file() and
                   (p.suffix in ('.c', '.h') or p.name == 'Makefile') and
                   not {'build', '__pycache__'}.intersection(p.relative_to(HERE).parts))
    files += [HERE.parent/'functional'/n for n in
              ('vkso_abi.h', 'vkso_user_wrapper.c', 'vkso_user_wrapper.h', 'vkso_user_entry.S')]
    return hashlib.sha256(''.join(str(p.relative_to(HERE.parent)) + sha256(p)
                                   for p in files).encode()).hexdigest()


def parent_for(mode, variant):
    label = 'clean' if mode == 'read' else 'update'
    choices = [ART / f'clocktime-auto-current-{mode}-{variant}',
               ART / f'ifunc-{label}-{variant}',
               ART / f'clocktime-ifunc-{label}-{variant}',
               ART / f'clocktime-full-v1-{label}-{variant}']
    for path in choices:
        if (path / 'SHA256SUMS').is_file():
            try:
                package_check(mode, path)
            except (OSError, ValueError, KeyError):
                continue
            return path.resolve()
    raise ValueError(f'no valid parent package for {mode}/{variant}')


def run_rebuild(target, mode, parent, output):
    cmd = [sys.executable, str(HERE / 'rebuild.py'), target,
           '--scope', mode, '--package', str(parent), '--out', str(output)]
    subprocess.run(cmd, check=True)


def free_output(base):
    for attempt in range(100):
        path = base if attempt == 0 else base.with_name(base.name + f'-retry{attempt}')
        if not any(p.exists() for p in (path, path.with_name(path.name+'.work'),
                                        path.with_name(path.name+'.building'))):
            return path
    raise ValueError('too many preserved failed attempts for ' + str(base))


def main():
    if sys.argv[1:] not in ([], ['--plan']):
        raise ValueError('usage: build-all.sh [auto|auto --plan]')
    plan = sys.argv[1:] == ['--plan']
    commit = git('rev-parse', 'HEAD').decode().strip()
    patch = git('diff', '--binary', '--no-ext-diff', 'HEAD', '--')
    patch_sha = hashlib.sha256(patch).hexdigest()
    kernel_sha = subprocess.check_output([BARE / 'source-tree-hash.sh', KERNEL], text=True).strip()
    measured_sha = measured_fingerprint()
    run_id = hashlib.sha256((commit + patch_sha + kernel_sha + measured_sha).encode()).hexdigest()[:12]
    current_sections = patch_sections(patch)
    selected = {}
    for mode in MODES:
        selected[mode] = {}
        for variant in VARIANTS:
            parent = parent_for(mode, variant)
            manifest = kv_file(parent / 'boot-manifest.txt')
            old_sections = patch_sections((parent / 'source.patch').read_bytes())
            changed = {name for name in set(old_sections) | set(current_sections)
                       if old_sections.get(name) != current_sections.get(name)}
            label = 'clean' if mode == 'read' else 'update'
            final = ART / f'clocktime-auto-{run_id}-{label}-{variant}'
            stage = ART / f'clocktime-auto-{run_id}-{label}-{variant}-stage'
            if final.exists():
                package_check(mode, final)
                chosen = final
                action = 'REUSE_COMPLETE'
            else:
                if manifest['vkso_source_tree_sha256'] != kernel_sha or \
                        manifest['git_commit'] != commit or changed.intersection(KERNEL_PACKAGE_INPUTS):
                    action = 'vkso'
                elif changed.intersection(INDEPENDENT_INPUTS):
                    cached = ART / '.kbuild-cache' / mode / variant / 'build/vkso/arch/x86/boot/bzImage'
                    action = 'carrier' if cached.is_file() and sha256(cached) == sha256(parent / 'vkso-bzImage') else 'vkso'
                else:
                    direct_changed = compiled_inputs_changed(parent)
                    action = 'bench' if direct_changed else \
                        'metadata' if manifest['candidate_patch_sha256'] != patch_sha else 'REUSE'
                if plan:
                    chosen = parent
                elif action in ('vkso', 'carrier'):
                    if stage.exists():
                        package_check(mode, stage)
                    else:
                        stage = free_output(stage)
                        run_rebuild(f'{action}-{variant}', mode, parent, stage)
                    final = free_output(final)
                    run_rebuild(f'bench-{variant}', mode, stage, final)
                    chosen = final
                elif action in ('bench', 'metadata'):
                    final = free_output(final)
                    run_rebuild(f'{action}-{variant}', mode, parent, final)
                    chosen = final
                else:
                    chosen = parent
            selected[mode][variant] = chosen.resolve()
            print(f'auto_case={mode}:{variant} action={action} package={chosen}', flush=True)
    if plan:
        return
    sys.path.insert(0, str(UPDATE))
    from stateful import check_all_packages
    check_all_packages(selected)
    if git('rev-parse', 'HEAD').decode().strip() != commit or \
            hashlib.sha256(git('diff', '--binary', '--no-ext-diff', 'HEAD', '--')).hexdigest() != patch_sha or \
            subprocess.check_output([BARE / 'source-tree-hash.sh', KERNEL], text=True).strip() != kernel_sha or \
            measured_fingerprint() != measured_sha:
        raise ValueError('source changed during build; packages preserved, current links not advanced')
    for mode in MODES:
        for variant in VARIANTS:
            link = ART / f'clocktime-auto-current-{mode}-{variant}'
            temporary = ART / (link.name + '.new')
            if temporary.exists() or temporary.is_symlink():
                raise ValueError('stale temporary link: ' + str(temporary))
            temporary.symlink_to(selected[mode][variant])
            temporary.replace(link)
    env = ART / 'clocktime-auto-current.env'
    values = {'NORMAL_PACKAGE': selected['read']['normal'],
              'NO_RETPOLINE_PACKAGE': selected['read']['no-retpoline'],
              'UPDATE_NORMAL_PACKAGE': selected['update']['normal'],
              'UPDATE_NO_RETPOLINE_PACKAGE': selected['update']['no-retpoline']}
    temporary = env.with_suffix('.env.new')
    temporary.write_text(''.join(f'export {key}={value}\n' for key, value in values.items()))
    temporary.replace(env)
    print('four_package_validation=PASS')
    print('package_env=' + str(env))


if __name__ == '__main__':
    try:
        ART.mkdir(parents=True, exist_ok=True)
        with (ART / '.auto-build.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            main()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        sys.exit('automatic build failed: ' + str(exc))
