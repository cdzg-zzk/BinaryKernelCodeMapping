#!/usr/bin/env python3
"""Bounded resource observations around the unchanged full BCH guest workflow.

Only loader probes dlopen and fault pages. The existing BCH benchmark separately
executes its complete correctness-only path in the same registration session.
"""
from pathlib import Path
import ctypes
import csv
import io
import json
import os
import select
import struct
import subprocess
import sys
import time
import traceback

from elftools.elf.elffile import ELFFile

sys.path.insert(0, '/work/helpers')
import bch_functional as functional
from carrier import mappings

OUT = Path('/work/validation/bch_resources')
PAGE = 4096
MASK = (1 << 55) - 1
NATIVE = Path('/work/binaries/libbch-kernel-native.so')
RUNTIME = Path('/work/repo/page_cache_replace/runtime')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def identity():
    return {'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'kernel': os.uname().release, 'controller_pid': os.getpid(),
            'observed_unix': time.time()}


def map_rows(text):
    rows = []
    for line in text.splitlines():
        parts = line.split(maxsplit=5)
        start, end = (int(value, 16) for value in parts[0].split('-'))
        rows.append({'start': start, 'end': end, 'permissions': parts[1],
                     'file_offset': int(parts[2], 16), 'device': parts[3],
                     'inode': int(parts[4]), 'path': parts[5] if len(parts) == 6 else ''})
    return rows


def elf_layout(path):
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        segments = [{key: int(segment[key]) for key in
                     ('p_vaddr', 'p_offset', 'p_filesz', 'p_memsz', 'p_flags')}
                    for segment in elf.iter_segments() if segment['p_type'] == 'PT_LOAD']
        sections = [{'name': section.name, 'address': int(section['sh_addr']),
                     'size': int(section['sh_size']), 'flags': int(section['sh_flags']),
                     'type': section['sh_type']}
                    for section in elf.iter_sections() if section['sh_flags'] & 2]
    return {'path': str(path), 'segments': segments, 'sections': sections}


def base_address(layout):
    # Sparse carrier starts at p_vaddr=0x1000: dladdr's first mapped address is
    # not its ELF load bias. Reconstruct bias from an actual file-offset VMA.
    first = min(layout['segments'], key=lambda row: row['p_vaddr'])
    rows = [row for row in map_rows(Path('/proc/self/maps').read_text())
            if row['path'] == layout['path']
            and row['file_offset'] == first['p_offset'] // PAGE * PAGE]
    assert len(rows) == 1, (layout['path'], first, rows)
    return rows[0]['start'] - first['p_vaddr'] // PAGE * PAGE


def loaded_pages(layout, base, role, plan):
    rows = map_rows(Path('/proc/self/maps').read_text())
    pages = {}
    for segment in layout['segments']:
        begin = base + segment['p_vaddr']
        end = begin + segment['p_memsz']
        for address in range(begin // PAGE * PAGE, (end + PAGE - 1) // PAGE * PAGE, PAGE):
            valid = max(address, begin)
            region = next(row for row in rows if row['start'] <= valid < row['end'])
            if 'r' not in region['permissions']:
                raise RuntimeError(('unreadable PT_LOAD page', layout['path'], address, region))
            offset = (segment['p_offset'] + valid - begin) // PAGE * PAGE
            file_backed = valid - begin < segment['p_filesz']
            if file_backed:
                assert region['path'] == layout['path'], (layout, region)
                assert offset == region['file_offset'] + (address - region['start']), (offset, region)
            sections = [section['name'] for section in layout['sections']
                        if section['address'] < address + PAGE - base
                        and section['address'] + section['size'] > address - base]
            declared = plan.get(offset) if role == 'carrier' and file_backed else None
            item = pages.setdefault(address, {
                'address': address, 'fault_address': valid, 'library': layout['path'],
                'role': role, 'file_offset': offset if file_backed else None,
                'file_backed_segment': file_backed, 'permissions': region['permissions'],
                'vma': region, 'sections': [], 'segment_flags': [],
                'declared': declared})
            item['sections'] = sorted(set(item['sections'] + sections))
            item['segment_flags'] = sorted(set(item['segment_flags'] + [segment['p_flags']]))
    return list(pages.values())


def loader_main(library_path, role, plan_path):
    library_path = Path(library_path).resolve()
    plan = {int(row[0]): {'kernel_address': row[1], 'kind': row[2], 'section': row[3]}
            for row in mappings(Path(plan_path))} if plan_path != '-' else {}
    layout = elf_layout(library_path)
    print(json.dumps({'phase': 'before', 'pid': os.getpid()}), flush=True)
    assert sys.stdin.readline().strip() == 'load'
    library = ctypes.CDLL(str(library_path))
    base = base_address(layout)
    targets = loaded_pages(layout, base, role, plan)
    layouts = [layout]
    if role == 'carrier':
        shim = library_path.parent / 'libshim.so'
        shim_layout = elf_layout(shim)
        shim_base = base_address(shim_layout)
        targets += loaded_pages(shim_layout, shim_base, 'shim', {})
        layouts.append(shim_layout)
    print(json.dumps({'phase': 'loaded', 'pid': os.getpid(), 'targets': targets,
                      'layouts': layouts, 'load_base': base}), flush=True)
    assert sys.stdin.readline().strip() == 'fault'
    checksum = 0
    for row in targets:
        checksum ^= ctypes.c_ubyte.from_address(row['fault_address']).value
    print(json.dumps({'phase': 'faulted', 'pid': os.getpid(), 'checksum': checksum}), flush=True)
    assert sys.stdin.readline().strip() == 'release'


def snapshot(pid, destination, targets=None):
    destination.mkdir(parents=True, exist_ok=False)
    record = {'pid': pid, **identity(), 'pagemap_read': 'fresh os.pread; recorded VMA ranges only',
              'snapshot_atomic': False, 'pagemap_ranges': [], 'target_pages': []}
    proc = Path('/proc') / str(pid)
    maps = (proc / 'maps').read_text()
    (destination / 'maps.txt').write_text(maps)
    for name in ('smaps', 'smaps_rollup', 'status'):
        try:
            (destination / (name + '.txt')).write_text((proc / name).read_text())
        except OSError as error:
            record.setdefault('read_errors', {})[name] = str(error)
    descriptor = os.open(proc / 'pagemap', os.O_RDONLY)
    try:
        with (destination / 'pagemap.bin').open('wb') as stream:
            for row in map_rows(maps):
                item = dict(row, binary_offset=stream.tell(), requested_entries=(row['end'] - row['start']) // PAGE)
                try:
                    requested = item['requested_entries'] * 8
                    # Bounded chunks exclude virtual holes and prevent giant sparse-file reads.
                    total = 0
                    for offset in range(0, requested, 65536):
                        chunk = os.pread(descriptor, min(65536, requested - offset),
                                         row['start'] // PAGE * 8 + offset)
                        stream.write(chunk)
                        total += len(chunk)
                        if len(chunk) != min(65536, requested - offset):
                            item['short_read'] = True
                            break
                    item['bytes_read'] = total
                except (OSError, OverflowError) as error:
                    item['error'] = str(error)
                    item['bytes_read'] = stream.tell() - item['binary_offset']
                record['pagemap_ranges'].append(item)
        for target in targets or []:
            entry, = struct.unpack('<Q', os.pread(descriptor, 8, target['address'] // PAGE * 8))
            record['target_pages'].append(dict(target, pagemap_entry=hex(entry),
                present=bool(entry & (1 << 63)), pfn=entry & MASK,
                file_or_shared_anon=bool(entry & (1 << 61)), exclusive_bit=bool(entry & (1 << 56))))
    finally:
        os.close(descriptor)
    record['finished_unix'] = time.time()
    write(destination / 'record.json', record)
    return record


def kernel_pages(addresses, destination):
    destination.mkdir(parents=True, exist_ok=True)
    result = {}
    probe = Path('/sys/kernel/debug/vkso_kernel_reader')
    for index in range(0, len(addresses), 64):
        batch = addresses[index:index + 64]
        (probe / 'page_addresses').write_text(' '.join(hex(address) for address in batch))
        raw = (probe / 'pages').read_text()
        (destination / f'pages-{index // 64:03}.csv').write_text(raw)
        (destination / f'addresses-{index // 64:03}.txt').write_text(' '.join(map(hex, batch)) + '\n')
        for row in csv.DictReader(io.StringIO(raw)):
            result[int(row['kernel_vaddr'], 0)] = int(row['pfn'])
    return result


def system_snapshot(destination, observe_modules=False):
    destination.mkdir(parents=True, exist_ok=True)
    result = {'identity': identity(), 'modules': {}}
    for name in ('modules', 'meminfo', 'vmstat', 'slabinfo'):
        try:
            (destination / (name + '.txt')).write_text((Path('/proc') / name).read_text())
        except OSError as error:
            result.setdefault('read_errors', {})[name] = str(error)
    module_lines = {row.split()[0]: row.split() for row in Path('/proc/modules').read_text().splitlines()}
    if observe_modules:
        for name in ('vkso_bch', 'vkso_kernel_reader', 'page_cache_replace'):
            fields = module_lines[name]
            directory = Path('/sys/module') / name
            item = {'proc_modules_fields': fields, 'attributes': {}, 'sections': {}}
            for attr in ('coresize', 'initsize', 'refcnt', 'initstate', 'taint'):
                file = directory / attr
                if file.exists():
                    item['attributes'][attr] = file.read_text().strip()
            for section in (directory / 'sections').iterdir():
                item['sections'][section.name] = section.read_text().strip()
            base, size = int(fields[5], 16), int(item['attributes']['coresize'])
            init_size = int(item['attributes']['initsize'])
            assert base and base % PAGE == 0 and size + init_size == int(fields[1]), item
            assert item['attributes']['initstate'] == 'live' and init_size == 0, item
            module_paths = {'vkso_bch': '/work/owner/vkso_bch.ko',
                            'vkso_kernel_reader': '/work/helpers/vkso_kernel_reader.ko',
                            'page_cache_replace': '/work/repo/page_cache_replace/page_cache_replace.ko'}
            sections = elf_layout(Path(module_paths[name]))['sections']
            for section in sections:
                section['runtime_address'] = int(item['sections'].get(section['name'], '0'), 16)
            item['elf_allocated_sections'] = sections
            addresses = list(range(base, base + size, PAGE))
            pfns = kernel_pages(addresses, destination / name)
            item.update(core_base=base, core_bytes=size, rounded_core_bytes=len(addresses) * PAGE,
                        requested_addresses=addresses,
                        observed_pages=[{'address': address, 'pfn': pfns[address],
                                         'overlapping_sections': [section['name'] for section in sections
                                             if section['runtime_address'] < address + PAGE
                                             and section['runtime_address'] + section['size'] > address]}
                                        for address in addresses if address in pfns],
                        missing_addresses=[address for address in addresses if address not in pfns],
                        scope='core allocation interval from proc_modules base and sysfs coresize; includes code, data, padding and support; excludes freed init allocation and external allocations')
            result['modules'][name] = item
    write(destination / 'system.json', result)
    return result


def status_kb(path, field):
    for line in path.read_text().splitlines():
        if line.startswith(field + ':'):
            return int(line.split()[1])
    return None


def receive(process, expected):
    readable, _, _ = select.select([process.stdout], [], [], 60)
    if not readable:
        raise RuntimeError(('loader response timeout', process.pid, expected))
    line = process.stdout.readline()
    if not line:
        raise RuntimeError(('loader exited before phase', process.pid, expected, process.poll()))
    value = json.loads(line)
    assert value['phase'] == expected and value['pid'] == process.pid, value
    return value


def summarize(records, source, owner, group):
    categories = {}
    declared_rows = []
    for record in records:
        for row in record['target_pages']:
            assert row['present'] and row['pfn'], row
            if row['declared']:
                category = 'declared-' + row['declared']['kind']
                expected = source[row['declared']['kernel_address']]
                assert row['pfn'] == expected and 'w' not in row['permissions'], row
                declared_rows.append(row)
            elif row['role'] == 'shim':
                category = 'shim-' + ('writable' if 'w' in row['permissions'] else 'readonly')
            elif row['role'] == 'carrier':
                category = 'carrier-support-' + ('writable' if 'w' in row['permissions'] else 'readonly')
            else:
                category = 'native-' + ('executable' if 'x' in row['permissions'] else
                                        'writable' if 'w' in row['permissions'] else 'readonly')
            categories.setdefault(category, []).append((record['pid'], row))
    owner_pfns = set(owner)
    source_pfns = set(source.values())
    target_pfns = {row['pfn'] for record in records for row in record['target_pages']}
    summary = {'loader_count': len(records), 'loader_pids': [record['pid'] for record in records],
               'categories': {}, 'target_pfn_union': sorted(target_pfns),
               'declared_source_pfn_union': sorted(source_pfns),
               'target_and_declared_source_pfn_union': sorted(target_pfns | source_pfns),
               'owner_core_pfn_union': sorted(owner_pfns),
               'target_and_owner_core_pfn_union': sorted(target_pfns | owner_pfns),
               'declared_loader_mappings': len(declared_rows),
               'scope': 'faulted library PT_LOAD pages plus required shim; loader-only, no BCH control/heap objects; PFN set unions, not RSS multiplied by process count'}
    for category, rows in categories.items():
        pfns = sorted({row['pfn'] for _, row in rows})
        private = {row['pfn'] for _, row in rows
                   if row['permissions'].endswith('p') and not row['file_or_shared_anon']}
        summary['categories'][category] = {
            'mapping_count': len(rows), 'pfn_union': pfns, 'distinct_pfns': len(pfns),
            'pfn_distinct_process_count': {str(pfn): len({pid for pid, row in rows if row['pfn'] == pfn}) for pfn in pfns},
            'private_vma_nonfile_pfns': sorted(private),
            'owner_core_overlap_pfns': sorted(set(pfns) & owner_pfns)}
    summary['process_status_kb'] = []
    for record in records:
        pid = record['pid']
        item = {'pid': pid}
        for phase in ('before', 'loaded', 'faulted'):
            path = group / str(pid) / phase / 'status.txt'
            item[phase] = {name: status_kb(path, name) for name in ('VmRSS', 'VmHWM', 'VmPTE', 'RssAnon', 'RssFile', 'RssShmem')}
        item['VmPTE_delta_faulted_minus_before_kb'] = item['faulted']['VmPTE'] - item['before']['VmPTE']
        summary['process_status_kb'].append(item)
    return summary


def run_role(role, library, plan_path=None):
    destination = OUT / role
    destination.mkdir(parents=True, exist_ok=False)
    initial = system_snapshot(destination / 'initial-system', observe_modules=role != 'native-before-owner')
    owner = [row['pfn'] for row in initial['modules'].get('vkso_bch', {}).get('observed_pages', [])]
    source = {}
    plan = mappings(plan_path) if plan_path else []
    if plan:
        source = kernel_pages([row[1] for row in plan], destination / 'declared-source')
        assert set(source) == {row[1] for row in plan}
        assert set(source.values()).issubset(owner)
    role_record = {'role': role, 'library': str(library), 'identity': identity(),
                   'plan': plan, 'groups': [], 'status': 'running',
                   'owner_baseline_meaning': 'controlled dedicated-owner preload only; not evidence of original kernel demand'}
    write(destination / 'role.json', role_record)
    try:
        for count in (1, 4, 16):
            group = destination / f'n{count:02}'
            group.mkdir()
            processes, errors = [], []
            try:
                for index in range(count):
                    error = (group / f'loader-{index:02}.stderr').open('w')
                    errors.append(error)
                    process = subprocess.Popen([sys.executable, '/work/guest.py', '--resource-loader',
                        str(library), 'carrier' if plan else 'native', str(plan_path) if plan else '-'],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error, text=True, bufsize=1)
                    processes.append(process)
                for process in processes:
                    receive(process, 'before')
                for process in processes:
                    snapshot(process.pid, group / str(process.pid) / 'before')
                    process.stdin.write('load\n')
                    process.stdin.flush()
                targets = {}
                for process in processes:
                    reply = receive(process, 'loaded')
                    targets[process.pid] = reply['targets']
                    write(group / str(process.pid) / 'loader.json', reply)
                for process in processes:
                    snapshot(process.pid, group / str(process.pid) / 'loaded', targets[process.pid])
                    process.stdin.write('fault\n')
                    process.stdin.flush()
                for process in processes:
                    receive(process, 'faulted')
                records = [snapshot(process.pid, group / str(process.pid) / 'faulted', targets[process.pid])
                           for process in processes]
                manager = None
                if plan:
                    pid = int((RUNTIME / 'manager.pid').read_text())
                    manager = snapshot(pid, group / 'manager')
                    for name in ('manager.pid', 'manager.state'):
                        (group / name).write_text((RUNTIME / name).read_text())
                system_snapshot(group / 'active-system')
                summary = summarize(records, source, owner, group)
                summary.update(identity=identity(), role=role,
                               manager_pid=manager['pid'] if manager else None)
                if plan:
                    assert summary['declared_loader_mappings'] == count * len(plan), summary
                write(group / 'summary.json', summary)
                role_record['groups'].append(summary)
                print(f'bch_resource_role={role} loaders={count}:pass', flush=True)
            finally:
                for process in processes:
                    if process.poll() is None:
                        try:
                            process.stdin.write('release\n')
                            process.stdin.flush()
                            process.wait(timeout=10)
                        except (BrokenPipeError, subprocess.TimeoutExpired):
                            process.terminate()
                            process.wait(timeout=10)
                    if process.returncode:
                        role_record.setdefault('loader_exit_failures', []).append(
                            {'pid': process.pid, 'returncode': process.returncode})
                for error in errors:
                    error.close()
            assert not role_record.get('loader_exit_failures'), role_record
            write(destination / 'role.json', role_record)
        role_record['status'] = 'pass'
    except BaseException:
        role_record['status'] = 'fail'
        role_record['error'] = traceback.format_exc()
        raise
    finally:
        write(destination / 'role.json', role_record)


def main():
    original_execute = functional.execute
    before_done = False

    def execute_hook(command, log, environment=None):
        nonlocal before_done
        words = list(map(str, command))
        if words[:1] == ['insmod'] and words[1].endswith('/vkso_bch.ko'):
            run_role('native-before-owner', NATIVE)
        if len(words) > 1 and words[0] == '/work/repo/vkso' and words[1] == 'exec':
            run_role('native-owner-loaded', NATIVE)
        if words[:1] == ['rmmod'] and not before_done:
            before_done = True
            system_snapshot(OUT / 'restored-before-module-unload', observe_modules=True)
        return original_execute(command, log, environment)

    functional.execute = execute_hook
    result = functional.main()
    roles = [json.loads((OUT / role / 'role.json').read_text()) for role in
             ('native-before-owner', 'native-owner-loaded', 'registered-carrier')
             if (OUT / role / 'role.json').exists()]
    status = 'pass' if result == 0 and len(roles) == 3 and all(row['status'] == 'pass' for row in roles) else 'fail'
    write(OUT / 'result.json', {'status': status, 'identity': identity(),
          'roles': [row['role'] for row in roles], 'functional_status': result,
          'scope': 'same boot/session 1/4/16 loader PFN accounting plus unchanged complete BCH correctness; no performance samples',
          'limitations': ['controlled preloaded-owner baseline does not imply original kernel need',
                          'loader support excludes BCH control/heap objects used by separate correctness process',
                          'PTE values are per-process VmPTE, not independently enumerated page-table PFNs',
                          'whole owner core excludes external allocator/slab/vmalloc metadata and freed init allocation',
                          'snapshots are sequential and include generic Python/runtime instrumentation overhead',
                          'restoration check covers fresh file-offset mappings only']})
    print('bch_resource_validation=' + status, flush=True)
    return 0 if status == 'pass' else 1


if __name__ == '__main__':
    if sys.argv[1:2] == ['--resource-loader']:
        loader_main(*sys.argv[2:])
    elif sys.argv[1:] == ['--validate-bch']:
        fields = dict(line.split('=', 1) for line in
                      (functional.WORK / 'vkso/metadata/outputs.env').read_text().splitlines())
        run_role('registered-carrier', Path(fields['library']).resolve(), Path(fields['page_map']))
        functional.validate_bch()
    else:
        raise SystemExit(main())
