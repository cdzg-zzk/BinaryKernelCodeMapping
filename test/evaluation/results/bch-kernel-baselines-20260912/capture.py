#!/usr/bin/env python3
"""Capture installed BCH baseline evidence; reads inputs, writes only --output.

No module operations, compilation, package installation, or network access.
Requires pyelftools. Raw inputs and exact commands are listed in identity.json
and commands.json. DWARF extraction retains only CU attributes and four APIs.
"""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from elftools.elf.elffile import ELFFile


REPO = Path(__file__).resolve().parents[4]
STOCK = Path('/lib/modules/5.15.0-119-generic/kernel/lib/bch.ko')
DEBUG = Path('/usr/lib/debug/lib/modules/5.15.0-119-generic/kernel/lib/bch.ko')
HEADERS = Path('/usr/src/linux-headers-5.15.0-119')
BUILD = Path('/lib/modules/5.15.0-119-generic/build').resolve()
SOURCE = REPO / 'test/test_BCH'
OWNER_SOURCE = REPO / 'test/evaluation/results/bch_resource-qemu-20260912-attempt03/build-source'
OWNER = OWNER_SOURCE / 'kmod/vkso_bch.ko'
APIS = ['bch_encode', 'bch_init', 'bch_decode', 'bch_free']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decoded(value):
    return value.decode(errors='replace') if isinstance(value, bytes) else value


def elf_summary(path):
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        ids = []
        alloc = []
        for section in elf.iter_sections():
            if section['sh_type'] == 'SHT_NOTE':
                for note in section.iter_notes():
                    if note['n_name'] == 'GNU' and note['n_type'] == 'NT_GNU_BUILD_ID':
                        ids.append(note['n_desc'])
            if section['sh_flags'] & 2:
                alloc.append(dict(name=section.name, type=section['sh_type'],
                                  size=section['sh_size'], flags=section['sh_flags'],
                                  sha256=sha(section.data())))
        symtab = elf.get_section_by_name('.symtab')
        undefined = sorted({s.name for s in symtab.iter_symbols()
                            if s['st_shndx'] == 'SHN_UNDEF' and s.name})
        comment = elf.get_section_by_name('.comment')
        return dict(build_ids=ids, allocated_sections=alloc,
                    undefined_symbols=undefined,
                    compiler_comments=[decoded(c) for c in comment.data().split(b'\0') if c])


def dwarf_summary(path):
    rows = []
    with path.open('rb') as stream:
        dwarf = ELFFile(stream).get_dwarf_info()
        for cu in dwarf.iter_CUs():
            top = cu.get_top_DIE()
            row = {key: decoded(top.attributes[key].value)
                   for key in ['DW_AT_name', 'DW_AT_comp_dir', 'DW_AT_producer']
                   if key in top.attributes}
            line_program = dwarf.line_program_for_CU(cu)
            row['dwarf_version'] = cu.header.version
            row['line_file_fields'] = [dict(content_type=e.content_type, form=e.form)
                                      for e in line_program.header.file_name_entry_format]
            row['api_declarations'] = []
            if row['DW_AT_name'].endswith('/lib/bch.c'):
                for die in cu.iter_DIEs():
                    name = die.attributes.get('DW_AT_name')
                    if (die.tag == 'DW_TAG_subprogram' and name
                            and decoded(name.value) in APIS):
                        row['api_declarations'].append({
                            'name': decoded(name.value),
                            **{key: decoded(die.attributes[key].value)
                               for key in ['DW_AT_decl_line', 'DW_AT_decl_file', 'DW_AT_external']
                               if key in die.attributes}})
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    commands = []

    def write(name, value):
        path = args.output / name
        if not isinstance(value, (str, bytes)):
            value = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
        if isinstance(value, bytes):
            path.write_bytes(value)
        else:
            path.write_text(value)

    def run(name, argv, accepted=(0,)):
        result = subprocess.run(argv, cwd=REPO, text=True, capture_output=True)
        commands.append(dict(output=name, argv=argv, cwd=str(REPO),
                             returncode=result.returncode, stderr=result.stderr))
        write(name, result.stdout)
        if result.returncode not in accepted:
            raise RuntimeError(f'{argv[0]} returned {result.returncode}: {result.stderr}')

    inputs = dict(stock=STOCK, debug=DEBUG, owner=OWNER,
                  exact119_header=HEADERS / 'include/linux/bch.h',
                  vendored_header=SOURCE / 'vendor/linux-5.15/include/linux/bch.h',
                  stock_symvers=BUILD / 'Module.symvers',
                  owner_symvers=OWNER_SOURCE / 'kmod/Module.symvers',
                  exact119_config=BUILD / '.config',
                  vendor_c=SOURCE / 'vendor/linux-5.15/lib/bch.c',
                  adapted_c=SOURCE / 'adapted/bch.c',
                  owner_compile_command=OWNER_SOURCE / 'kmod/.bch_impl.o.cmd')
    for name in ['kmod/Makefile', 'kmod/bch_impl.c', 'kmod/module_meta.c', 'adapted/bch.c']:
        inputs['current_' + name] = SOURCE / name
        inputs['consumed_' + name] = OWNER_SOURCE / name
    identity = {name: dict(path=str(path), resolved=str(path.resolve()),
                          bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
                for name, path in inputs.items()}
    write('identity.json', dict(captured_utc=datetime.now(timezone.utc).isoformat(),
                               repo=str(REPO), artifacts=identity))
    run('package-owners.txt', ['dpkg-query', '-S', str(STOCK), str(DEBUG),
                            str(inputs['exact119_header']), str(inputs['stock_symvers'])])
    run('package-versions.txt', ['dpkg-query', '-W', '-f=${Package}\t${Version}\t${db:Status-Abbrev}\n',
                                'linux-modules-5.15.0-119-generic',
                                'linux-image-unsigned-5.15.0-119-generic-dbgsym',
                                'linux-headers-5.15.0-119', 'linux-headers-5.15.0-119-generic'])
    run('stock-modinfo.txt', ['modinfo', str(STOCK)])
    run('owner-modinfo.txt', ['modinfo', str(OWNER)])
    for label, path in [('stock', STOCK), ('debug', DEBUG), ('owner', OWNER)]:
        run(label + '-notes.txt', ['readelf', '-n', str(path)])
    stock = elf_summary(STOCK)
    debug = elf_summary(DEBUG)
    owner = elf_summary(OWNER)
    write('stock-elf.json', stock)
    write('debug-elf.json', debug)
    write('owner-elf.json', owner)
    sa = {s['name']: s for s in stock['allocated_sections']}
    da = {s['name']: s for s in debug['allocated_sections']}
    rows = []
    for name in sorted(set(sa) | set(da)):
        a, b = sa.get(name), da.get(name)
        rows.append(dict(name=name, stock=a, debug=b, identical=a == b))
    alloc_pass = len(rows) == 17 and all(r['identical'] for r in rows)
    write('allocated-section-comparison.json', dict(
        method='Every SHF_ALLOC section, including SHT_NOBITS zero contents; compare names, types, flags, sizes and bytes.',
        expected_sections=17, compared_sections=len(rows),
        build_ids_equal=stock['build_ids'] == debug['build_ids'],
        status='PASS' if alloc_pass else 'FAIL', sections=rows))
    write('stock-cu.json', dwarf_summary(DEBUG))
    for label, path, names in [('stock', inputs['stock_symvers'], APIS),
                               ('owner', inputs['owner_symvers'], ['vkso_' + s for s in APIS])]:
        selected = [line for line in path.read_text().splitlines()
                    if len(line.split()) > 1 and line.split()[1] in names]
        if len(selected) != 4:
            raise AssertionError(f'{label}: expected four public APIs, got {len(selected)}')
        write(label + '-public-symbols.tsv', '\n'.join(selected) + '\n')
    header_equal = inputs['exact119_header'].read_bytes() == inputs['vendored_header'].read_bytes()
    write('exact119-bch.h', inputs['exact119_header'].read_bytes())
    write('header-comparison.json', dict(status='PASS' if header_equal else 'FAIL',
                                        exact119=identity['exact119_header'],
                                        vendored=identity['vendored_header'], bytes_identical=header_equal))
    selected_config = [line for line in inputs['exact119_config'].read_text().splitlines()
                       if re.match(r'^(?:# )?CONFIG_(?:BCH|RETPOLINE|RETHUNK|X86_KERNEL_IBT|STACKPROTECTOR|FORTIFY_SOURCE|UBSAN|FUNCTION_TRACER)(?:_|=| )', line)]
    write('exact119-config-excerpt.txt', '\n'.join(selected_config) + '\n')
    command_lines = [line for line in inputs['owner_compile_command'].read_text().splitlines()
                     if line.startswith('cmd_')]
    if len(command_lines) != 1:
        raise AssertionError('expected one owner algorithm command')
    write('owner-bch_impl-command.txt', '\n'.join(command_lines) + '\n')
    for name in ['Makefile', 'bch_impl.c', 'module_meta.c']:
        write('owner-' + name, (OWNER_SOURCE / 'kmod' / name).read_bytes())
    write('owner-source-comparison.json', [dict(
        source=name, current=identity['current_' + name], consumed=identity['consumed_' + name],
        bytes_identical=identity['current_' + name]['sha256'] == identity['consumed_' + name]['sha256'])
        for name in ['kmod/Makefile', 'kmod/bch_impl.c', 'kmod/module_meta.c', 'adapted/bch.c']])
    run('vendor-to-adapted.diff', ['diff', '-u', str(inputs['vendor_c']), str(inputs['adapted_c'])], (1,))
    write('commands.json', commands)
    checks = dict(stock_debug_allocated_sections=alloc_pass,
                  stock_debug_build_id=stock['build_ids'] == debug['build_ids'],
                  public_header_identical=header_equal,
                  consumed_owner_source_matches_current=all(
                      identity['current_' + n]['sha256'] == identity['consumed_' + n]['sha256']
                      for n in ['kmod/Makefile', 'kmod/bch_impl.c', 'kmod/module_meta.c', 'adapted/bch.c']))
    write('result.json', dict(status='PASS' if all(checks.values()) else 'FAIL', checks=checks,
                             scope='Installed binary/interface/build provenance only; no new runtime or performance result.',
                             stock119_source_content_identity='Not established: DWARF source paths/lines have no content checksum.'))
    if not all(checks.values()):
        raise AssertionError(checks)
    print(json.dumps(dict(output=str(args.output), status='PASS', checks=checks), indent=2))


if __name__ == '__main__':
    main()
