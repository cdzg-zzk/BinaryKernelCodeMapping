#!/usr/bin/env python3
"""Audit actual object instructions and Kbuild commands; compile a bounded probe."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[4]


def inspect(path, output):
    assembly = subprocess.check_output(['objdump', '-dr', path], text=True)
    output.write_text(assembly)
    functions = {}
    name = None
    for line in assembly.splitlines():
        match = re.match(r'^[0-9a-f]+ <([^>]+)>:', line)
        if match:
            name = match[1]
            functions[name] = []
        elif name:
            functions[name].append(line)
    rows = []
    for name, body in functions.items():
        text = '\n'.join(body)
        rows.append(dict(function=name,
            gs_canary_instructions=len(re.findall(r'%gs:0x28', text)),
            fs_canary_instructions=len(re.findall(r'%fs:0x28', text)),
            stack_fail_relocations=len(re.findall(r'R_X86_64_\S+\s+__stack_chk_fail', text)),
            return_thunk_relocations=len(re.findall(r'R_X86_64_\S+\s+__x86_return_thunk', text)),
            indirect_thunk_relocations=len(re.findall(r'R_X86_64_\S+\s+__x86_indirect_thunk_', text)),
            fentry_relocations=len(re.findall(r'R_X86_64_\S+\s+(__fentry__|mcount)', text))))
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                disassembly=str(output), functions=rows,
                undefined=subprocess.check_output(['nm', '-u', path], text=True).splitlines())


def command(path):
    raw = path.read_text().splitlines()[0].split(' := ', 1)[1]
    return shlex.split(raw)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    build = a.build.resolve()
    controls = ROOT/'test/evaluation-local/runs/iso9660/squash-bounded-controls-build-01'
    paths = {'prepared-filesystem': build/'shared_core.o',
             'prepared-xz': build/'xz_dec_stream.o',
             'prepared-lz4': build/'shared_lz4.o',
             'native-consumer': build/'dir.o',
             'optimized-native-normal': controls/'native-small-normal/dir.o',
             'optimized-native-relaxed': controls/'native-small-relaxed/dir.o'}
    rows = {}
    for label, path in paths.items():
        row = inspect(path, out/(label+'.asm'))
        args = command(path.with_name('.'+path.name+'.cmd'))
        row['compiler_argv'] = args
        row['ordered_relevant_flags'] = [x for x in args if x.startswith((
            '-O', '-mcmodel', '-fpie', '-fPIE', '-fno-PIE', '-fstack-protector',
            '-fno-stack-protector', '-mindirect-branch', '-mfunction-return',
            '-fsanitize', '-fno-sanitize', '-pg', '-mfentry', '-mrecord-mcount',
            '-mharden', '-D__NO_FORTIFY'))]
        rows[label] = row
    # Compile the exact same PIC source with its original kernel SSP/thunk flags.
    # Keep the output separate and never load/register this diagnostic object.
    args = command(build/'.shared_core.o.cmd')
    args = [x for x in args if x not in ['-fno-stack-protector',
            '-mfunction-return=keep', '-mindirect-branch=keep'] and not x.startswith('-Wp,-MMD,')]
    # GCC selects FS with the small code model, unlike the native kernel model.
    # Explicitly request the native canary segment for this ABI feasibility probe.
    args[1:1] = ['-fstack-protector-strong', '-mstack-protector-guard-reg=gs']
    args[args.index('-o')+1] = str(out/'pic-hardened-probe.o')
    with (out/'probe-build.log').open('w') as log:
        subprocess.run(args, cwd=ROOT/'test/section65/build/native/kernel',
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    rows['pic-hardened-build-only'] = inspect(out/'pic-hardened-probe.o', out/'pic-hardened-probe.asm')
    rows['pic-hardened-build-only']['compiler_argv'] = args
    assert any(r['gs_canary_instructions'] for r in rows['optimized-native-normal']['functions'])
    assert not any(r['gs_canary_instructions'] for r in rows['prepared-filesystem']['functions'])
    assert any(r['gs_canary_instructions'] for r in rows['pic-hardened-build-only']['functions'])
    config = ROOT/'test/section65/build/native/kernel/.config'
    selected = [line for line in config.read_text().splitlines() if re.search(
        r'CONFIG_(RETPOLINE|RETHUNK|STACKPROTECTOR|FTRACE|FUNCTION_TRACER|UBSAN|FORTIFY_SOURCE|XZ_DEC)', line)]
    result = dict(status='complete', objects=rows, config=selected,
        compiler=subprocess.check_output(['gcc', '--version'], text=True).splitlines()[0],
        scope='Object-level evidence. Retained thunk relocations do not by themselves certify runtime mitigation policy.',
        conclusion='PIC compilation can retain kernel SSP and external thunks. Current shared objects deliberately omit them: kernel GS canary storage and external thunk/failure targets are not bound by the current user ABI. The build-only probe is not a runnable hardened VKSO implementation. The prototype changes native hardening properties; prepared/native timing is the cost of that complete prototype configuration, not pure PGOT cost.')
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('audited', len(rows), 'object configurations')


if __name__ == '__main__':
    main()
