#!/usr/bin/env python3
"""Measure the actual clean campaign packages, including embedded Raw vDSO.

Kernel symbol extents use the next distinct kallsyms address, including padding.
They are deliberately not called ELF st_size or executed-instruction counts.
"""
import argparse
import bisect
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from collections import Counter, defaultdict

from elftools.elf.elffile import ELFFile
from audit_current import REPO, OUT, csv_text

BARE = REPO / 'test/test_gettime/vkso-tests/baremetal'
CAMPAIGN = BARE / 'results/20260929T040650Z-clocktime-full'


def kallsyms(data, absolute_percpu=True):
    """Decode Linux 5.15 relative kallsyms, validating all marker offsets.

The digit tokens only locate candidates. Accept a candidate only when its
256-entry token index and every 256-symbol name marker agree exactly.
"""
    elf = ELFFile(io.BytesIO(data))
    sec = elf.get_section_by_name('.rodata')
    b = sec.data()
    needle = b'0\0' + b''.join(str(i).encode() + b'\0' for i in range(1, 10))
    scan = 0
    while True:
        digit = b.find(needle, scan)
        if digit < 0:
            raise ValueError('no validated kallsyms table')
        scan = digit + 1
        try:
            start = digit
            for _ in range(48):
                start = b.rfind(b'\0', 0, start - 1) + 1
            pos = start
            tokens, offsets = [], []
            for _ in range(256):
                end = b.index(0, pos)
                offsets.append(pos - start)
                tokens.append(b[pos:end].decode('ascii'))
                pos = end + 1
            index = struct.pack('<256H', *offsets)
            if b.find(index, pos, pos + 8 + len(index)) < 0:
                continue
            for padding in (0, 4):
                mend = start - padding
                mstart = mend - 4
                last = 2**32
                while mstart >= 0:
                    value = struct.unpack_from('<I', b, mstart)[0]
                    if value >= last or value > len(b):
                        break
                    if value == 0:
                        break
                    last = value
                    mstart -= 4
                count = (mend - mstart) // 4
                if count < 10 or count > 10000:
                    continue
                markers = list(struct.unpack_from('<' + 'I' * count, b, mstart))
                if markers[0] != 0:
                    continue
                near = mstart - markers[-1]
                for n in range((count - 1) * 256 + 1, count * 256 + 1):
                    at = b.find(struct.pack('<Q', n), max(0, near - 65536), near)
                    if at < 8 + n * 4:
                        continue
                    pos = at + 8
                    names, actual = [], []
                    for i in range(n):
                        if i % 256 == 0:
                            actual.append(pos - at - 8)
                        length = b[pos]
                        pos += 1
                        if not length:
                            break
                        names.append(''.join(tokens[x] for x in b[pos:pos + length]))
                        pos += length
                    if len(names) != n or actual != markers or (pos + 7) // 8 * 8 != mstart:
                        continue
                    base = struct.unpack_from('<Q', b, at - 8)[0]
                    # kallsyms_relative_base is pointer-aligned; an odd number
                    # of 32-bit offsets leaves four padding bytes before it.
                    offsets_start = (at - 8 - n * 4) & ~7
                    vals = struct.unpack_from('<' + 'i' * n, b, offsets_start)
                    addresses = [(v if v >= 0 else base - 1 - v) if absolute_percpu
                                 else base + (v & 0xffffffff) for v in vals]
                    result = {}
                    for name, address in zip(names, addresses):
                        key = name[1:]
                        if key in result:
                            previous = result[key]
                            result[key + '#' + hex(previous[0])] = previous
                        result[key] = (address, name[0])
                    if not (result['_text'][0] <= result['ktime_get'][0] < result['_etext'][0]):
                        continue
                    if result['_text'][0] != elf.get_section_by_name('.text')['sh_addr']:
                        continue
                    return result
        except (UnicodeDecodeError, ValueError, IndexError, struct.error, KeyError):
            continue


def extract_image(path):
    script = REPO / 'test/test_gettime/linux-5.15.198-vkso/scripts/extract-vmlinux'
    p = subprocess.run(['bash', str(script), str(path)], capture_output=True, check=True)
    data = p.stdout
    ELFFile(io.BytesIO(data))
    return data


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_id(elf):
    for section in elf.iter_sections():
        if section['sh_type'] == 'SHT_NOTE':
            for note in section.iter_notes():
                if note['n_type'] == 'NT_GNU_BUILD_ID' and note['n_name'] == 'GNU':
                    value = note['n_desc']
                    return value.hex() if isinstance(value, bytes) else value
    return ''


def embedded_vdso(data):
    pos = 1
    while True:
        pos = data.find(b'\x7fELF\x02', pos)
        if pos < 0:
            raise ValueError('native vDSO missing')
        try:
            elf = ELFFile(io.BytesIO(data[pos:]))
            ds = elf.get_section_by_name('.dynsym')
            if ds and any(s.name == '__vdso_clock_gettime' for s in ds.iter_symbols()):
                return elf, pos
        except Exception:
            pass
        pos += 1


def symbol_sizes(elf):
    symtab = elf.get_section_by_name('.symtab') or elf.get_section_by_name('.dynsym')
    return [(s.name, s['st_value'], s['st_size'], s['st_info']['type']) for s in symtab.iter_symbols()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((OUT / 'source-manifest.json').read_text())
    symbols, sections, identities, missing, branches = [], [], [], [], []
    wanted = {s: {} for s in ['Raw', 'VKSO']}
    for row in manifest['slices']:
        if row['origin'] != row['system']:
            continue
        for name in row['symbols'].split(';'):
            if name:
                wanted[row['system']][name.replace('sys:', '__x64_sys_')] = (row['scope'], row['category'])
    for s in wanted:
        for name in ['timekeeping_update', 'update_wall_time']:
            wanted[s][name] = ('host_container', 'publisher_with_common_timekeeping')
    for name in ['update_vsyscall', 'update_vsyscall_tz', 'vdso_fault', 'vvar_fault', 'vdso_join_timens', 'arch_setup_additional_pages']:
        wanted['Raw'][name] = ('feature', 'publication_or_mapping')
    for name in ['vkso_mm_fault', 'vkso_mm_mremap', 'vkso_dup_mmap', 'vkso_destroy_context', 'vkso_time_join_namespace', 'arch_setup_additional_pages', 'vkso_time_update_timezone']:
        wanted['VKSO'][name] = ('feature', 'publication_or_mapping')
    for variant in ['normal', 'no-retpoline']:
        pkg = BARE / ('artifacts/clocktime-auto-53f692884c64-clean-' + variant)
        sharing = json.loads((CAMPAIGN / f'block-01/read/vkso-{variant}/sharing.json').read_text())
        shared_sections = {p['section'] for p in sharing['pages']}
        for system, method in [('Raw', 'raw'), ('VKSO', 'vkso')]:
            run = json.loads((CAMPAIGN / f'block-01/read/{method}-{variant}/run.json').read_text())
            image = pkg / (method + '-bzImage')
            assert sha(image) == run['kernel_image_sha256']
            data = extract_image(image)
            elf = ELFFile(io.BytesIO(data))
            ksyms = kallsyms(data)
            addresses = sorted({a for a, kind in ksyms.values() if kind.lower() == 't'})
            # Raw images are stripped. Independently check their decoded code
            # addresses against the kernel's exported relative-pointer table.
            export_checks = 0
            for name in wanted[system]:
                export = ksyms.get('__ksymtab_' + name)
                if not export or name not in ksyms:
                    continue
                address = export[0]
                for section in elf.iter_sections():
                    if section['sh_addr'] <= address < section['sh_addr'] + section['sh_size']:
                        delta = struct.unpack_from('<i', section.data(), address - section['sh_addr'])[0]
                        assert address + delta == ksyms[name][0], name
                        export_checks += 1
                        break
            assert export_checks >= 11
            identities.append(dict(variant=variant, system=system, image=str(image.relative_to(REPO)),
                                   build_id=build_id(elf), campaign_image_identity='PASS',
                                   kallsyms_symbols=len(ksyms), exported_function_addresses_checked=export_checks))
            # Cross-validate the decoder against the actual matching VKSO ELF.
            if system == 'VKSO':
                full = BARE / f'artifacts/.kbuild-cache/read/{variant}/build/vkso/vmlinux'
                with full.open('rb') as stream:
                    full_elf = ELFFile(stream)
                    assert build_id(full_elf) == build_id(elf)
                    checked = 0
                    full_symbols = symbol_sizes(full_elf)
                    occurrences = Counter(n for n, a, size, k in full_symbols if k == 'STT_FUNC')
                    decoded_functions = defaultdict(set)
                    for n, (a, k) in ksyms.items():
                        if k.lower() == 't':
                            decoded_functions[n.split('#')[0]].add(a)
                    for name, address, size, kind in full_symbols:
                        if kind == 'STT_FUNC' and name in decoded_functions and occurrences[name] == 1:
                            assert address in decoded_functions[name], name
                            checked += 1
                    assert checked > 1000
                    identities[-1]['decoder_elf_function_addresses_checked'] = checked
                    starts = {n: a for n, a, z, k in full_symbols}
                    shared_start, shared_end = starts['__vkso_text_start'], starts['__vkso_text_end']
                    for name, address, size, kind in full_symbols:
                        if kind == 'STT_FUNC' and shared_start <= address < shared_end and size:
                            symbols.append(dict(variant=variant, system=system, artifact='kernel-shared-core',
                                                scope='feature', category='getcpu' if 'getcpu' in name else 'shared_time',
                                                symbol=name, address=hex(address), bytes=size, metric='ELF symbol st_size'))
                    identities[-1]['shared_core_reserved_bytes'] = shared_end - shared_start
                    # Record direct transfers in the actual kernel image, alongside
                    # the carrier's tail jumps, to tie both domains to one entry.
                    for caller in ['ktime_get', 'ktime_get_ts64', 'ktime_get_raw_ts64', 'ktime_get_coarse_ts64']:
                        dump = subprocess.check_output(['objdump', '-d', '--disassemble=' + caller, str(full)], text=True)
                        for line in dump.splitlines():
                            if ('call' in line or 'jmp' in line) and ('<vkso_clock_gettime_' in line):
                                branches.append(dict(variant=variant, artifact='kernel:' + caller, disassembly=line.strip()))
            for name, (scope, category) in wanted[system].items():
                matches = [n for n in ksyms if n == name or n.startswith(name + '.')]
                if not matches:
                    missing.append(dict(variant=variant, system=system, symbol=name,
                                        reason='inlined/absent as standalone symbol; not counted as zero implementation'))
                for actual in matches:
                    address, kind = ksyms[actual]
                    if kind.lower() != 't':
                        continue
                    end = addresses[bisect.bisect_right(addresses, address)]
                    symbols.append(dict(variant=variant, system=system, artifact='kernel', scope=scope,
                                        category=category, symbol=actual, address=hex(address), bytes=end-address,
                                        metric='kallsyms next distinct text address (includes padding)'))
            for sec in elf.iter_sections():
                if sec['sh_flags'] & 2:
                    sections.append(dict(variant=variant, system=system, artifact='kernel', section=sec.name,
                                         bytes=sec['sh_size'], scope='whole-kernel context'))
            if system == 'Raw':
                vdso, offset = embedded_vdso(data)
                for name, address, size, kind in symbol_sizes(vdso):
                    if name.startswith('__vdso_') and kind == 'STT_FUNC':
                        symbols.append(dict(variant=variant, system=system, artifact='embedded-vdso',
                                            scope='excluded_platform' if 'sgx' in name else 'feature',
                                            category='getcpu' if 'getcpu' in name else 'user_time', symbol=name,
                                            address=hex(address), bytes=size, metric='ELF symbol st_size'))
                for sec in vdso.iter_sections():
                    if sec['sh_flags'] & 2:
                        sections.append(dict(variant=variant, system=system, artifact='embedded-vdso',
                                             section=sec.name, bytes=sec['sh_size'], scope='native DSO including SGX'))
                identities[-1]['embedded_vdso_file_offset'] = offset
        # Carrier symbols, private public adapter and general runtime facilities.
        for filename in ['libkernel.so', 'direct/libvkso_time.so', 'manager', 'page_cache_replace.ko']:
            path = pkg / filename
            if filename == 'libkernel.so':
                assert sha(path) == run['carrier_sha256']
            if filename == 'direct/libvkso_time.so':
                assert sha(path) == run['public_library_sha256']
            with path.open('rb') as stream:
                elf = ELFFile(stream)
                for sec in elf.iter_sections():
                    if sec['sh_flags'] & 2:
                        scope = ('shared backing: count once with kernel' if filename == 'libkernel.so' and sec.name in shared_sections
                                 else 'general infrastructure' if filename in ['manager', 'page_cache_replace.ko'] else 'user private')
                        sections.append(dict(variant=variant, system='VKSO', artifact=filename,
                                             section=sec.name, bytes=sec['sh_size'], scope=scope))
                if filename in ['libkernel.so', 'direct/libvkso_time.so']:
                    for name, address, size, kind in symbol_sizes(elf):
                        if kind in ['STT_FUNC', 'STT_LOOS'] and size:
                            symbols.append(dict(variant=variant, system='VKSO', artifact=filename, scope='carrier/public symbol inventory',
                                                category='getcpu' if 'getcpu' in name else 'time_or_adapter', symbol=name,
                                                address=hex(address), bytes=size, metric='ELF symbol st_size; aliases not additive'))
                    dis = subprocess.check_output(['objdump', '-d', str(path)], text=True)
                    for line in dis.splitlines():
                        if any(word in line for word in ['<vkso_clock_gettime_hres>', '<vkso_clock_gettime_coarse>', '<__vkso_clock_gettime>', '<vkso_gettimeofday_core>']) and any(word in line for word in ['jmp', 'call']):
                            branches.append(dict(variant=variant, artifact=filename, disassembly=line.strip()))
    outputs = {
        'binary-symbols.csv': csv_text(symbols, list(symbols[0])),
        'binary-sections.csv': csv_text(sections, list(sections[0])),
        'binary-identities.json': json.dumps(identities, indent=2) + '\n',
        'binary-inline-or-absent.json': json.dumps(missing, indent=2) + '\n',
        'binary-user-transfers.csv': csv_text(branches, list(branches[0])),
    }
    for name, text in outputs.items():
        path = OUT / name
        if args.check:
            assert path.read_text() == text, 'stale output: ' + name
        else:
            path.write_text(text)
    print('binary_evidence_check=PASS' if args.check else 'binary_evidence_written=PASS')
    print(json.dumps(identities, indent=2))


if __name__ == '__main__':
    main()
