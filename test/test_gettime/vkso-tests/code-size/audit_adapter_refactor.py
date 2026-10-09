#!/usr/bin/env python3
"""Verify the ABI/init refactor against the measured source, without a boot.

Counts keep the original functional scope, including required retained readers.
Compiler checks establish layout and selected code-generation equivalence, not
new performance measurements. Kernel compilation uses the local configured tree.
"""
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

from elftools.elf.elffile import ELFFile
from audit_changes import lexical_lines
from audit_current import OUT as MEASURED, REPO, sources, inventory

HERE = Path(__file__).resolve().parent
BASE = json.loads((MEASURED / 'source-manifest.json').read_text())
KERNEL = REPO / BASE['kernel_root']
TESTS = HERE.parent
HEADER = KERNEL / 'include/vkso/time_abi.h'
FILES = [KERNEL / 'include/vkso/time.h', HEADER,
         TESTS / 'functional/vkso_abi.h', TESTS / 'functional/vkso_user_wrapper.c',
         TESTS / 'direct-api/vkso_time_init.c', TESTS / 'direct-api/Makefile']
OUTPUT = HERE / 'adapter-evidence'


def run(argv, **kwargs):
    return subprocess.check_output(list(map(str, argv)), stderr=subprocess.STDOUT,
                                   text=True, **kwargs)


def original(path):
    return run(['git', 'show', BASE['revision'] + ':' + str(path.relative_to(REPO))], cwd=REPO)


def code(path, text):
    return len(lexical_lines(str(path), text))


def code_image(path):
    """Executable bytes plus their relocation targets; debug locations excluded."""
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        executable = {i: s for i, s in enumerate(elf.iter_sections()) if s['sh_flags'] & 4}
        image = {s.name: {'bytes': s.data().hex(), 'relocations': []} for s in executable.values()}
        for section in elf.iter_sections():
            if section['sh_type'] not in ('SHT_REL', 'SHT_RELA') or section['sh_info'] not in executable:
                continue
            symbols = elf.get_section(section['sh_link'])
            target = image[executable[section['sh_info']].name]['relocations']
            for relocation in section.iter_relocations():
                symbol = symbols.get_symbol(relocation['r_info_sym'])
                name = symbol.name
                if not name and isinstance(symbol['st_shndx'], int):
                    name = elf.get_section(symbol['st_shndx']).name
                target.append((relocation['r_offset'], relocation['r_info_type'], name,
                               relocation.entry.get('r_addend', 0)))
        return image


def source_counts():
    texts = sources(BASE, check_worktree=False)
    recreated = inventory(BASE, texts)
    for name, data in recreated.items():
        assert (MEASURED / name).read_text() == data, name
    changed = set(FILES)
    # Existing measured sources outside the reviewed patch must still match.
    for (origin, path), text in texts.items():
        if origin not in ('VKSO', 'Project', 'Platform'):
            continue
        current = KERNEL / path if origin in ('VKSO', 'Platform') else REPO / path
        if current not in changed:
            assert current.read_text() == text, current
    rows = []
    for path in FILES:
        before = original(path) if path != HEADER else ''
        after = path.read_text()
        rows.append(dict(path=str(path.relative_to(REPO)), before=code(path, before),
                         after=code(path, after), delta=code(path, after)-code(path, before)))
    # The header's test-only block stays unchanged and remains outside feature counts.
    old = original(KERNEL / 'include/vkso/time.h')
    new = (KERNEL / 'include/vkso/time.h').read_text()
    pattern = r'#ifdef CONFIG_VKSO_TIME_TEST.*?#endif'
    assert re.findall(pattern, old, re.S) == re.findall(pattern, new, re.S)
    assert (TESTS / 'functional/vkso_time_abi.h').is_symlink()
    assert (TESTS / 'functional/vkso_time_abi.h').resolve() == HEADER.resolve()
    delta = sum(r['delta'] for r in rows)
    totals = json.loads(recreated['source-totals.json'])['totals']
    result = {}
    for system in ('Raw', 'VKSO'):
        t = totals[system]
        result[system] = dict(feature=t['feature'], retained=t['retained'],
                              including_retained=t['feature']+t['retained'])
    result['VKSO_refactored'] = dict(feature=result['VKSO']['feature']+delta,
                                     retained=result['VKSO']['retained'],
                                     including_retained=result['VKSO']['including_retained']+delta)
    assert delta == -63
    return dict(unit='nonblank noncomment physical source lines', files=rows, delta=delta,
                totals=result, link_counting='canonical ABI source counted once; symbolic include alias has no second source body',
                boundary='same declared time/getcpu inventory and retained reader roots; general facilities and common dependencies remain separate')


def compiler_checks(work):
    old = work / 'before'; old.mkdir()
    new = work / 'after'; new.mkdir()
    for name in ['vkso_abi.h', 'vkso_user_wrapper.h', 'vkso_user_wrapper.c']:
        (old / name).write_text(original(TESTS / 'functional' / name))
    for name in ['vkso_public.c', 'vkso_time.h', 'vkso_time_init.c']:
        (old / name).write_text(original(TESTS / 'direct-api' / name))
    (old / 'vkso_user_entry.S').write_text(original(TESTS / 'functional/vkso_user_entry.S'))
    (old / 'include/vkso').mkdir(parents=True)
    old_kernel = old / 'include/vkso/time.h'
    old_kernel.write_text(original(KERNEL / 'include/vkso/time.h'))
    flags = ['gcc', '-D_GNU_SOURCE', '-O2', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
             '-fno-lto', '-fno-builtin', '-fPIC', '-fno-plt']
    objects = {}
    for directory, includes, source in [(old, [old], old / 'vkso_public.c'),
                                        (new, [TESTS/'functional', TESTS/'direct-api'], TESTS/'direct-api/vkso_public.c')]:
        output = directory / 'public.o'
        run(flags + ['-I'+str(p) for p in includes] + ['-c', source, '-o', output])
        objects[directory.name] = output
    assert objects['before'].read_bytes() == objects['after'].read_bytes()
    for directory, include, source in [(old, old/'include', old/'vkso_user_entry.S'),
                                       (new, KERNEL/'include', TESTS/'functional/vkso_user_entry.S')]:
        run(['gcc', '-I'+str(include), '-c', '-fPIC', source, '-o', directory/'entry.o'])
    assert (old/'entry.o').read_bytes() == (new/'entry.o').read_bytes()
    # Compare every field of each shared structure to the old independent user ABI.
    structs = re.findall(r'struct (vkso_\w+) \{(.*?)\}', (old/'vkso_abi.h').read_text(), re.S)
    assert len(structs) == 9
    for name, _ in structs:
        definition = 'struct ' + name + ' {'
        assert old_kernel.read_text().count(definition) == 1
        assert HEADER.read_text().count(definition) == 1
        assert definition not in (TESTS/'functional/vkso_abi.h').read_text()
        assert definition not in (KERNEL/'include/vkso/time.h').read_text()
    statements = []
    for name, body in structs:
        statements.append(f'printf("{name} %zu %zu\\n", sizeof(struct {name}), _Alignof(struct {name}));')
        for line in body.splitlines():
            match = re.search(r'(\w+)\s*;', line)
            if match:
                field = match[1]
                statements.append(f'printf("{name}.{field} %zu %zu\\n", offsetof(struct {name}, {field}), sizeof(((struct {name} *)0)->{field}));')
    source = '#include <stdio.h>\n#include <stddef.h>\n#include "vkso_abi.h"\nint main(void) {\n'+'\n'.join(statements)+'\n}\n'
    (work/'layout.c').write_text(source)
    layouts = []
    for directory, include in [(old, old), (new, TESTS/'functional')]:
        run(flags + ['-I'+str(include), work/'layout.c', '-o', directory/'layout'])
        layouts.append(run([directory/'layout']))
    assert layouts[0] == layouts[1]
    (OUTPUT/'abi-layout.txt').write_text(layouts[1])
    # Compile real kernel translation units with the same Kbuild command, changing
    # only the forced old header. Both objects are unprocessed compiler products.
    targets = ['kernel/time/vkso_time_core', 'kernel/time/vkso_time_cycles',
               'kernel/time/vkso_time', 'kernel/time/timekeeping',
               'kernel/time/posix-timers', 'kernel/time/time', 'arch/x86/kernel/vkso']
    reports = []
    for target in targets:
        path = Path(target)
        cmd = (KERNEL/path.parent/('.'+path.name+'.o.cmd')).read_text().splitlines()[0].split(' := ', 1)[1]
        argv = shlex.split(cmd)
        assert all(x not in (';', '&&', '||') for x in argv), 'unexpected compound Kbuild command'
        argv = [x for x in argv if not x.startswith('-Wp,-MMD,')]
        out_index = argv.index('-o') + 1
        for directory in (old, new):
            invocation = list(argv)
            invocation[out_index] = str(directory/(path.name+'.o'))
            if directory == old:
                invocation += ['-include', str(old_kernel)]
            run(invocation, cwd=KERNEL)
        before = code_image(old/(path.name+'.o')); after = code_image(new/(path.name+'.o'))
        assert before == after, 'executable code/relocations differ: '+target
        reports.append(dict(unit=target+'.c', executable_sections=list(after),
                            executable_bytes=sum(len(s['bytes'])//2 for s in after.values()),
                            compiler_command=argv,
                            comparison='identical executable sections and relocation targets'))
    return dict(compiler=run(['gcc','-dumpfullversion']).strip(), abi_structures=len(structs),
                abi_layout_entries=len(statements), public_object='byte-identical',
                carrier_object='byte-identical', kernel_translation_units=reports,
                kernel_config=[line for line in (KERNEL/'.config').read_text().splitlines()
                               if re.match(r'(?:# )?CONFIG_(?:RETPOLINE|VKSO_TIME_TEST|TIMEKEEPING_UPDATE_BENCH|PREEMPT|HZ_)[=A-Z_ ]', line)],
                scope='local configured kernel compiler commands; no new latency measurements or boot claims')


def main():
    OUTPUT.mkdir(exist_ok=True)
    counts = source_counts()
    with tempfile.TemporaryDirectory(prefix='clocktime-adapter-audit-') as tmp:
        compilation = compiler_checks(Path(tmp))
    tests = {}
    for label, command in [('public-api', ['python3', TESTS/'direct-api/tests/test_direct.py', 'RuntimeTests']),
                           ('kernel-contract', ['python3', TESTS/'direct-api/tests/test_kernel_contract.py'])]:
        log = run(command)
        (OUTPUT/(label+'.log')).write_text(log)
        tests[label] = log.strip().splitlines()[-1]
    report = dict(status='PASS', measured_revision=BASE['revision'], candidate='current worktree ABI/init refactor',
                  source_counts=counts, compilation=compilation, tests=tests,
                  review=[
                      dict(area='ABI structures/version constants', action='consolidated', reason='one canonical header; user include alias; package exports header contents'),
                      dict(area='auxv discovery', action='consolidated', reason='wrapper validates before carrier access; public once initializer delegates'),
                      dict(area='public error conversion and carrier dispatch', action='retained', reason='distinct errno and context responsibilities; measured fast-path instructions unchanged'),
                      dict(area='kernel return conversion and root/current namespace', action='retained', reason='preserves public kernel interfaces and domain semantics'),
                      dict(area='provider/native fallback', action='retained and included in cost', reason='required behavior, not removable duplication'),
                      dict(area='libc layout checks and core layout checks', action='retained', reason='cover separate interface boundaries; compile-time only')],
                  performance='existing READ/UPDATE results remain attached to measured revision; refactor has no new timing result')
    (OUTPUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
