#!/usr/bin/env python3
"""Compile complete candidate functions using the actual kernel Kbuild flags."""
import argparse
import difflib
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'linux-5.15.198-vkso/kernel/time/vkso_time_core.c'


def run(args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('kernel', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    kernel = args.kernel.resolve()
    if kernel == SOURCE.parents[2].resolve():
        raise ValueError('Use a separate full source copy, not the maintained kernel tree')
    original = SOURCE.read_text()
    internal_path = SOURCE.with_name('vkso_time_internal.h')
    internal = internal_path.read_text()
    cycles = SOURCE.with_name('vkso_time_cycles.c').read_text()
    coarse = '''__visible noinline __noclone notrace __vkso_text
int vkso_clock_gettime_coarse(s32 clock_id, struct vkso_time_value *value,
                              const struct vkso_mm_data *mm_data)
{
    const struct vkso_shared_data *shared = vkso_shared_data();
    const struct vkso_time_value *coarse = clock_id == CLOCK_REALTIME_COARSE ?
        &shared->state.realtime_coarse : &shared->state.monotonic_coarse;

    vkso_read_coarse(shared, coarse, value);
    if (clock_id == CLOCK_MONOTONIC_COARSE && mm_data &&
        (READ_ONCE(mm_data->clock_mask) & (1U << CLOCK_MONOTONIC_COARSE)))
        vkso_apply_offset(&mm_data->monotonic_offset, value);
    return VKSO_TIME_OK;
}
'''
    begin = original.index('__visible noinline __noclone notrace __vkso_text\nint vkso_clock_gettime_coarse')
    end = original.index('\n__visible', begin + 1)
    early = original.replace('''	if (likely(tv)) {
		int status = vkso_read_hres_time(''', '''	if (unlikely(!tv)) {
		if (tz) {
			tz->minuteswest = READ_ONCE(shared->state.timezone.minuteswest);
			tz->dsttime = READ_ONCE(shared->state.timezone.dsttime);
		}
		return VKSO_TIME_OK;
	}
	{
		int status = vkso_read_hres_time(''')
    assert early != original
    outlined = original.replace('static __always_inline int\nvkso_read_hres_time(',
                                'static noinline __noclone notrace __vkso_text\nint vkso_read_hres_time(')
    assert outlined != original
    variants = {'baseline': original, 'coarse-late-offset': original[:begin] + coarse + original[end:],
                'gettimeofday-early-null': early, 'hres-single-body': outlined,
                'cold-preserve': original.replace('static noinline notrace __vkso_text\nint vkso_finish_hres_cold',
                    'static noinline notrace __vkso_text __attribute__((no_caller_saved_registers))\nint vkso_finish_hres_cold')}
    records = []
    for name, source in variants.items():
        dest = out / name
        dest.mkdir()
        (dest / 'vkso_time_core.c').write_text(source)
        (dest / 'candidate.patch').write_text(''.join(difflib.unified_diff(
            original.splitlines(True), source.splitlines(True),
            fromfile='a/kernel/time/vkso_time_core.c', tofile='b/kernel/time/vkso_time_core.c')))
        (kernel / 'kernel/time/vkso_time_core.c').write_text(source)
        header = internal.replace('s64 vkso_cycles_read_cold(',
            '__attribute__((no_caller_saved_registers))\ns64 vkso_cycles_read_cold(') if name == 'cold-preserve' else internal
        (kernel / 'kernel/time/vkso_time_internal.h').write_text(header)
        (dest / 'vkso_time_internal.h').write_text(header)
        (dest / 'internal.patch').write_text(''.join(difflib.unified_diff(internal.splitlines(True), header.splitlines(True),
            fromfile='a/kernel/time/vkso_time_internal.h', tofile='b/kernel/time/vkso_time_internal.h')))
        with (dest / 'build.log').open('w') as log:
            run(['make', '-C', kernel, '-j4', 'V=1', 'kernel/time/vkso_time_core.o', 'kernel/time/vkso_time_cycles.o'],
                stdout=log, stderr=subprocess.STDOUT)
        obj = dest / 'core.o'
        shutil.copy2(kernel / 'kernel/time/vkso_time_core.o', obj)
        shutil.copy2(kernel / 'kernel/time/vkso_time_cycles.o', dest / 'cycles.o')
        (dest / 'cycles.asm').write_text(run(['objdump', '-dr', dest / 'cycles.o'], capture_output=True, text=True).stdout)
        (dest / 'vkso_time_cycles.c').write_text(cycles)
        assembly = run(['objdump', '-dr', obj], capture_output=True, text=True).stdout
        (dest / 'core.asm').write_text(assembly)
        symbols = run(['nm', '-S', '--defined-only', obj], capture_output=True, text=True).stdout
        (dest / 'symbols.txt').write_text(symbols)
        sizes = {fields[3]: int(fields[1], 16) for line in symbols.splitlines()
                 if len(fields := line.split()) == 4 and fields[2].lower() == 't'}
        records.append(dict(variant=name, function_bytes=sizes, sum_function_bytes=sum(sizes.values())))
    (kernel / 'kernel/time/vkso_time_core.c').write_text(original)
    (kernel / 'kernel/time/vkso_time_internal.h').write_text(internal)
    (out / 'summary.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
