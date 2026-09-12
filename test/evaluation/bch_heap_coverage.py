#!/usr/bin/env python3
"""Check BCH heap evidence layouts/identities against consumed real ELF/source files.

Read-only apart from the requested JSON report. Complements bch_heap_audit.py;
does not execute a benchmark, load an ELF, or decode allocator slots from pagemap.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
ROLES = ('native-before-owner', 'native-owner-loaded', 'registered-carrier')
PROBE_SHA = 'f9d12c973053a17c97a8d124cfebdf0e4441ce4210762fa197c2ae37d1009cf6'
TYPES = {0: 'SHT_NULL', 1: 'SHT_PROGBITS', 2: 'SHT_SYMTAB', 3: 'SHT_STRTAB',
         4: 'SHT_RELA', 5: 'SHT_HASH', 6: 'SHT_DYNAMIC', 7: 'SHT_NOTE',
         8: 'SHT_NOBITS', 9: 'SHT_REL', 11: 'SHT_DYNSYM', 14: 'SHT_INIT_ARRAY',
         15: 'SHT_FINI_ARRAY', 16: 'SHT_PREINIT_ARRAY', 0x6ffffff6: 'SHT_GNU_HASH',
         0x6fffffff: 'SHT_GNU_versym', 0x6ffffffe: 'SHT_GNU_verneed',
         0x6ffffffd: 'SHT_GNU_verdef'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Elf:
    """Small independent ELF64/LSB x86-64 reader, limited to archived small files."""
    def __init__(self, path):
        require(path.stat().st_size < 64 * 1024 * 1024, f'oversized ELF input: {path}')
        self.path, self.data = path, path.read_bytes()
        require(self.data[:7] == b'\x7fELF\x02\x01\x01', f'not ELF64 LSB: {path}')
        h = struct.unpack_from('<HHIQQQIHHHHHH', self.data, 16)
        require(h[1] == 62 and h[8] in (0, 56) and h[10] == 64,
                f'unsupported ELF machine/header: {path}')
        self.segments = []
        for i in range(h[9]):
            p = struct.unpack_from('<IIQQQQQQ', self.data, h[4] + i * h[8])
            if p[0] == 1:
                self.segments.append(dict(p_vaddr=p[3], p_offset=p[2],
                    p_filesz=p[5], p_memsz=p[6], p_flags=p[1]))
        headers = [struct.unpack_from('<IIQQQQIIQQ', self.data, h[5] + i * 64)
                   for i in range(h[11])]
        names = headers[h[12]]
        strings = self.data[names[4]:names[4] + names[5]]
        self.sections, self.symbols = [], {}
        for index, s in enumerate(headers):
            name = strings[s[0]:].split(b'\0', 1)[0].decode()
            self.sections.append(dict(name=name, address=s[3], size=s[5],
                flags=s[2], type=TYPES.get(s[1], s[1]), offset=s[4], index=index))
        for s in headers:
            if s[1] not in (2, 11):
                continue
            require(s[9] == 24, f'invalid symbol size: {path}')
            st = headers[s[6]]
            names = self.data[st[4]:st[4] + st[5]]
            for offset in range(s[4], s[4] + s[5], 24):
                sym = struct.unpack_from('<IBBHQQ', self.data, offset)
                if sym[3]:
                    name = names[sym[0]:].split(b'\0', 1)[0].decode()
                    self.symbols[name] = dict(value=sym[4], size=sym[5],
                                              section=sym[3], info=sym[1])

    def allocated(self):
        return [{key: s[key] for key in ('name', 'address', 'size', 'flags', 'type')}
                for s in self.sections if s['flags'] & 2]

    def section_identity(self, name):
        s = next(s for s in self.sections if s['name'] == name)
        return dict(size=s['size'], sha256=hashlib.sha256(
            self.data[s['offset']:s['offset'] + s['size']]).hexdigest())


def audit(output, preparation, repo, archived_inputs=False):
    def input_path(path):
        path = path.resolve()
        if archived_inputs:
            require(path.is_relative_to(output), f'archived replay escaped archive: {path}')
        return path

    def input_json(path):
        return read(input_path(path))

    def input_text(path):
        return input_path(path).read_text()

    require(input_json(output / 'result.json')['status'] == 'pass', 'guest is not terminal PASS')
    validation = output / 'evidence/validation'
    evidence = validation / 'bch_heap'
    components = input_json(output / 'components.json')
    by_target = {item['target']: item for item in components['components']}
    files = {}

    def record(path):
        path = input_path(path)
        key = str(path)
        if key not in files:
            files[key] = dict(path=key, bytes=path.stat().st_size, sha256=sha(path))
        return files[key]['sha256']

    mapped_paths = {}
    if archived_inputs:
        repo = output / 'coverage-inputs/reference-repo'
        preparation = output / 'observation-preparation'
        ledger_path = output / 'coverage-inputs/path-mapping.json'
        ledger = input_json(ledger_path)
        require(ledger['schema_version'] == 1, 'unknown archived path mapping schema')
        record(ledger_path)
        for item in ledger['entries']:
            original = item['original_path']
            require(original not in mapped_paths and Path(original).is_absolute(),
                    f'duplicate/nonabsolute original provenance path: {original}')
            relative = Path(item['archived_path'])
            require(not relative.is_absolute() and '..' not in relative.parts,
                    f'invalid archived reference path: {relative}')
            archived = (output / relative).resolve()
            require(record(archived) == item['sha256'] and
                    archived.stat().st_size == item['bytes'],
                    f'archived reference bytes differ from mapping ledger: {relative}')
            mapped_paths[original] = archived

    def provenance_path(original):
        if not archived_inputs:
            return Path(original)
        require(str(original) in mapped_paths,
                f'original provenance path has no explicit archived mapping: {original}')
        return mapped_paths[str(original)]

    # Verify all actual input source copies against the copy ledger and original
    # repository sources, excluding generated owner object files.
    preserved = []
    for target, item in by_target.items():
        if target.startswith('build-source/'):
            path = output / target
            original = repo / 'test/test_BCH' / Path(target).relative_to('build-source')
            require(record(path) == item['sha256'] == record(original),
                    f'original source was changed: {target}')
            preserved.append(target)
    require(len(preserved) == 23, 'missing original build inputs')
    require(all(item['returncode'] == 0 for item in components['host_commands']),
            'recorded build failure')

    source = output / 'payload/helpers/bch_heap_probe_source/test'
    identities = {
        'bench_sha256': record(source / 'test_BCH/src/bch_bench.c'),
        'adapted_sha256': record(source / 'test_BCH/adapted/bch.c'),
        'header_sha256': record(source / 'test_BCH/vendor/linux-5.15/include/linux/bch.h'),
        'shim_sha256': record(output / 'payload/repo/make_dll/shim.c'),
    }
    for key, relative in [('bench_sha256', 'src/bch_bench.c'),
                          ('adapted_sha256', 'adapted/bch.c'),
                          ('header_sha256', 'vendor/linux-5.15/include/linux/bch.h')]:
        require(identities[key] == record(output / 'build-source' / relative),
                f'probe and owner/native build input differs: {key}')
    require(record(source / 'evaluation/bch_heap_probe.c') == PROBE_SHA,
            'unexpected frozen C observer')
    owner_header = provenance_path('/lib/modules/5.15.0-119-generic/build/include/linux/bch.h')
    require(record(owner_header) == identities['header_sha256'],
            'actual owner kernel header differs from probe/native public header')
    owner_command = output / 'build-source/kmod/.bch_impl.o.cmd'
    owner_command_text = input_text(owner_command)
    require('include/linux/bch.h' in owner_command_text and
            'kmod/../adapted/bch.c' in owner_command_text,
            'owner compiler dependency record does not identify complete BCH/header')
    record(owner_command)
    require(identities['shim_sha256'] == record(repo / 'make_dll/shim.c'),
            'consumed shim source differs from original repository shim')
    for path in [output / 'userspace-build.log', output / 'owner-build.log',
                 output / 'build-source/Makefile', output / 'build-source/kmod/Makefile']:
        record(path)
    prepared_id = input_json(preparation / 'probe-source-identities.json')
    argv = input_json(preparation / 'probe-build-command.json')
    for macro, key in [('BENCH', 'bench_sha256'), ('ADAPTED', 'adapted_sha256'),
                       ('HEADER', 'header_sha256'), ('SHIM', 'shim_sha256')]:
        require(prepared_id[macro] == identities[key], f'preparation SHA differs: {macro}')
        require(f'-DPROBE_{macro}_SHA256="{identities[key]}"' in argv,
                f'compiled SHA macro differs: {macro}')
    require(record(provenance_path(argv[-1])) == record(output / 'payload/helpers/libbch_heap_probe.so'),
            'built probe differs from consumed probe')
    require(record(provenance_path(argv[-4])) == PROBE_SHA, 'compiler consumed a different observer')
    for path in [preparation / 'probe-source-identities.json',
                 preparation / 'probe-build-command.json', preparation / 'probe-build.log']:
        record(path)
    require(not input_text(preparation / 'probe-build.log').strip(), 'probe compiler diagnostics')

    def guest_file(path):
        path = Path(path)
        if path.is_relative_to('/work/validation'):
            return validation / path.relative_to('/work/validation')
        require(path.is_relative_to('/work'), f'unknown guest path: {path}')
        return output / 'payload' / path.relative_to('/work')

    elfs = {}
    def elf(path):
        path = path.resolve()
        if path not in elfs:
            record(path)
            elfs[path] = Elf(path)
        return elfs[path]

    source_checks, layout_checks, api_checks = 0, 0, 0
    role_summary = []
    for role in ROLES:
        role_path = evidence / role
        r = input_json(role_path / 'role.json')
        require(r['status'] == 'pass', f'non-pass role: {role}')
        count = 0
        for group in r['groups']:
            require(group['count'] == len(group['pids']), 'PID count differs')
            for pid in group['pids']:
                directory = role_path / f'n{group["count"]:02d}' / str(pid)
                loaded = input_json(directory / 'loaded/probe.json')
                expected_roles = {'carrier', 'shim', 'observer'} if role == 'registered-carrier' else {'native', 'observer'}
                require({item['role'] for item in loaded['layouts']} == expected_roles and
                        len(loaded['layouts']) == len(expected_roles), 'layout role coverage differs')
                for layout in loaded['layouts']:
                    artifact = elf(guest_file(layout['path']))
                    require(layout['segments'] == artifact.segments,
                            f'actual ELF PT_LOAD mismatch: {directory} {layout["role"]}')
                    require(layout['sections'] == artifact.allocated(),
                            f'actual ELF allocated sections mismatch: {directory} {layout["role"]}')
                    layout_checks += 1
                main_layout = next(x for x in loaded['layouts'] if x['role'] in ('native', 'carrier'))
                binary = elf(guest_file(main_layout['path']))
                prefix = 'vkso_' if role == 'registered-carrier' else ''
                for phase in group['phases']:
                    if phase == 'before':
                        continue
                    state = input_json(directory / phase / 'probe.json')['probe']
                    require(state['source_identity'] == identities,
                            f'reported SHA does not match consumed source: {directory} {phase}')
                    source_checks += 1
                    for api in ('init', 'free', 'encode', 'decode'):
                        name = prefix + 'bch_' + api
                        require(state['api_symbols'][api] == name and
                                state['api_addresses'][api] == main_layout['load_bias'] + binary.symbols[name]['value'],
                                f'API address does not match actual ELF symbol: {directory} {api}')
                        api_checks += 1
                count += 1
        role_summary.append(dict(role=role, loader_processes=count))
    require([r['loader_processes'] for r in role_summary] == [21, 21, 21], 'incomplete 1/4/16 loader coverage')
    require(source_checks == 504 and layout_checks == 147 and api_checks == 2016,
            'incomplete source/layout/API coverage')

    # Preserve direct binary evidence in addition to the complete-source chain.
    original_text = []
    for fresh, original in [
        (output / 'payload/owner/vkso_bch.ko', repo / 'test/test_BCH/kmod/vkso_bch.ko'),
        *[(output / 'payload/binaries' / name, repo / 'test/test_BCH/build' / name)
          for name in ('bch-bench', 'libbch-kernel-native.so', 'libbch-author-standalone.so')]]:
        actual, previous = elf(fresh), elf(original)
        a, b = actual.section_identity('.text'), previous.section_identity('.text')
        require(a == b, f'original .text differs: {fresh}')
        original_text.append(dict(fresh=str(fresh), original=str(original), text=a))
        key = str(fresh.relative_to(output))
        require(record(fresh) == by_target[key]['sha256'], f'payload ELF differs from copied build: {fresh}')

    owner = elf(output / 'payload/owner/vkso_bch.ko')
    owner_censuses = []
    for path in sorted(evidence.glob('*/**/system.json')):
        system = input_json(path)
        module = system['modules'].get('vkso_bch')
        if not module:
            continue
        require([{k: s[k] for k in ('name', 'address', 'size', 'flags', 'type')}
                 for s in module['elf_allocated_sections']] == owner.allocated(),
                f'owner ELF section list differs: {path}')
        attributes = module['attributes']
        base, size = module['core_base'], int(attributes['coresize'])
        expected = list(range(base, base + (size + 4095) // 4096 * 4096, 4096))
        require(attributes['initstate'] == 'live' and int(attributes['initsize']) == 0,
                f'owner is not post-init/live: {path}')
        require(int(module['proc_modules_fields'][1]) == size and
                int(module['proc_modules_fields'][5], 16) == base and
                module['requested_addresses'] == expected and
                sorted(row['address'] for row in module['observed_pages']) == expected and
                not module['missing_addresses'], f'incomplete owner core census: {path}')
        owner_censuses.append(dict(path=str(path), core_bytes=size, pages=len(expected),
            observed_pfns=sorted(row['pfn'] for row in module['observed_pages'])))
    require(owner_censuses, 'owner census missing')

    normalized = dict(roles=role_summary, actual_elf_layout_checks=layout_checks,
        source_identity_record_checks=source_checks, api_symbol_address_checks=api_checks,
        consumed_source_identity=identities, preserved_original_source_files=sorted(preserved),
        original_text={Path(item['fresh']).name: item['text'] for item in original_text},
        owner_core=[{key: row[key] for key in ('core_bytes', 'pages', 'observed_pfns')}
                    for row in owner_censuses])
    return dict(status='pass', scope='actual archived ELF/source identity coverage; complements raw-pagemap audit',
        input_mode='archived' if archived_inputs else 'original-external', normalized_findings=normalized,
        roles=role_summary, actual_elf_layout_checks=layout_checks,
        source_identity_record_checks=source_checks, api_symbol_address_checks=api_checks,
        consumed_source_identity=identities, preserved_original_source_files=preserved,
        exact119_owner_header=str(owner_header.resolve()), owner_dependency_command=str(owner_command),
        original_text_comparisons=original_text, owner_core_censuses=owner_censuses,
        files=list(files.values()), limitations=[
            'Runtime snapshots are not atomic; this audit checks recorded layouts against on-disk consumed ELF.',
            'Pagemap does not contain object bytes or allocator slot contents; C records the successful allocator binding checks.',
            'Owner core includes code/data/padding/support; freed init and external allocations are excluded.',
            'Compile-command and copy ledgers are local provenance records, not independently authenticated attestation.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--preparation', type=Path)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--archived-inputs', action='store_true',
                        help='use only reference bytes/mapped original paths inside the extracted attempt archive')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    preparation = args.preparation or args.output.with_name(args.output.name + '-preparation')
    result = audit(args.output.resolve(), preparation.resolve(), args.repo.resolve(), args.archived_inputs)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'actual_elf_layout_checks',
        'source_identity_record_checks', 'api_symbol_address_checks')}))


if __name__ == '__main__':
    main()
