#!/usr/bin/env python3
"""Count resident PFNs in the time-related user mappings of live exec processes.

This is a mapping census, not a whole-system RAM measurement. It runs before
READ timing and keeps each cohort alive while pagemap is inspected.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import sys

PAGE = os.sysconf('SC_PAGE_SIZE')
PROTOCOL = 'clocktime-mapping-census-v1'
COUNTS = (1, 8, 32)


class Timespec(ctypes.Structure):
    _fields_ = [('tv_sec', ctypes.c_long), ('tv_nsec', ctypes.c_long)]


class Timeval(ctypes.Structure):
    _fields_ = [('tv_sec', ctypes.c_long), ('tv_usec', ctypes.c_long)]


def first_touch(backend, library):
    lib = ctypes.CDLL(None if backend == 'raw' else str(library), use_errno=True)
    if backend == 'vkso':
        init = lib.vkso_time_init
        init.restype = ctypes.c_int
        if init() != 0:
            raise OSError(ctypes.get_errno(), 'vkso_time_init failed')
    lib.clock_gettime.argtypes = [ctypes.c_int, ctypes.POINTER(Timespec)]
    lib.clock_gettime.restype = ctypes.c_int
    stamp = Timespec()
    for clock in (0, 1, 4, 7, 11, 5, 6):
        if lib.clock_gettime(clock, ctypes.byref(stamp)) != 0:
            raise OSError(ctypes.get_errno(), 'clock_gettime first touch')
    lib.clock_getres.argtypes = [ctypes.c_int, ctypes.POINTER(Timespec)]
    lib.clock_getres.restype = ctypes.c_int
    if lib.clock_getres(0, ctypes.byref(stamp)) != 0:
        raise OSError(ctypes.get_errno(), 'clock_getres first touch')
    lib.gettimeofday.argtypes = [ctypes.POINTER(Timeval), ctypes.c_void_p]
    lib.gettimeofday.restype = ctypes.c_int
    tv = Timeval()
    if lib.gettimeofday(ctypes.byref(tv), None) != 0:
        raise OSError(ctypes.get_errno(), 'gettimeofday first touch')
    lib.time.argtypes = [ctypes.c_void_p]
    lib.time.restype = ctypes.c_long
    if lib.time(None) == -1:
        raise OSError(ctypes.get_errno(), 'time first touch')
    lib.getcpu.argtypes = [ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
    lib.getcpu.restype = ctypes.c_int
    cpu, node = ctypes.c_uint(), ctypes.c_uint()
    if lib.getcpu(ctypes.byref(cpu), ctypes.byref(node)) != 0:
        raise OSError(ctypes.get_errno(), 'getcpu first touch')


def classify(path, carrier, public):
    if path == '[vdso]':
        return 'vdso'
    if path == '[vvar]' or path.startswith('[vvar_'):
        return 'vvar'
    if path == '[vkso_mm_data]':
        return 'mm_data'
    if path == str(carrier):
        return 'carrier'
    if path == str(public):
        return 'public'
    return None


def read_process(pid, carrier, public):
    maps = Path(f'/proc/{pid}/maps').read_text().splitlines()
    mappings = []
    with Path(f'/proc/{pid}/pagemap').open('rb') as pagemap:
        for line in maps:
            fields = line.split(maxsplit=5)
            if len(fields) < 6:
                continue
            kind = classify(fields[5], carrier, public)
            if not kind:
                continue
            first, last = (int(x, 16) for x in fields[0].split('-'))
            permissions = fields[1]
            if 'r' not in permissions:
                continue
            if 'w' in permissions and 'x' in permissions:
                raise ValueError('writable executable time mapping')
            pfns = []
            present = unresolved = 0
            for address in range(first, last, PAGE):
                pagemap.seek((address // PAGE) * 8)
                data = pagemap.read(8)
                if len(data) != 8:
                    raise ValueError('short pagemap read')
                entry, = struct.unpack('<Q', data)
                if entry & (1 << 63):
                    present += 1
                    pfn = entry & ((1 << 55) - 1)
                    if pfn:
                        pfns.append(pfn)
                    else:
                        unresolved += 1
            mappings.append(dict(kind=kind, permissions=permissions,
                                 file_offset=int(fields[2], 16),
                                 virtual_bytes=last-first, present_pages=present,
                                 unresolved_present_pages=unresolved, pfns=pfns))
    return dict(pid=pid, time_namespace=os.readlink(f'/proc/{pid}/ns/time'), mappings=mappings)


def summarize(records, backend, count):
    if len(records) != count or len({r['pid'] for r in records}) != count:
        raise ValueError('cohort process count mismatch')
    if len({r['time_namespace'] for r in records}) != 1:
        raise ValueError('cohort spans time namespaces')
    required = ('vdso', 'vvar') if backend == 'raw' else ('mm_data', 'carrier', 'public')
    excluded = ('mm_data', 'carrier', 'public') if backend == 'raw' else ('vdso', 'vvar')
    categories = {name: set() for name in required}
    counts = {name: 0 for name in required}
    unresolved = {name: 0 for name in required}
    for record in records:
        seen = {m['kind'] for m in record['mappings']}
        if not set(required).issubset(seen) or set(excluded) & seen:
            raise ValueError('wrong or missing time mapping: '+str(record['pid']))
        for mapping in record['mappings']:
            kind = mapping['kind']
            if kind not in categories:
                raise ValueError('unexpected time mapping category: '+kind)
            if (mapping['present_pages'] !=
                    len(mapping['pfns'])+mapping['unresolved_present_pages'] or
                    any(type(pfn) is not int or pfn <= 0 for pfn in mapping['pfns']) or
                    ('w' in mapping['permissions'] and 'x' in mapping['permissions'])):
                raise ValueError('invalid mapping page record')
            categories[kind].update(mapping['pfns'])
            counts[kind] += mapping['present_pages']
            unresolved[kind] += mapping['unresolved_present_pages']
    if not categories['vdso' if backend == 'raw' else 'carrier']:
        raise ValueError('time code PFNs are unavailable')
    if backend == 'vkso' and not categories['public']:
        raise ValueError('public library PFNs are unavailable')
    if any(unresolved.values()):
        raise ValueError('present time mapping PFNs are unavailable')
    if backend == 'vkso' and len(categories['mm_data']) != 1:
        raise ValueError('same-namespace MM_data is not one physical page')
    union = set().union(*categories.values())
    return dict(processes=count, namespace=records[0]['time_namespace'],
                unique_pfns={name:len(pfns) for name,pfns in categories.items()},
                union_unique_pfns=len(union), union_bytes=len(union)*PAGE,
                mapped_present_pages=counts, unresolved_present_pages=unresolved,
                records=records)


def cohort(count, backend, package):
    children = []
    library = package/'direct/libvkso_time.so'
    try:
        for _ in range(count):
            child = subprocess.Popen([sys.executable, '-B', __file__, 'worker',
                                      backend, str(library)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
            children.append(child)
            ready, _, _ = select.select([child.stdout], [], [], 30)
            line = child.stdout.readline() if ready else b''
            if line != b'READY\n':
                details = child.stderr.read(4096).decode(errors='replace') if child.poll() is not None else ''
                raise RuntimeError('resource worker did not initialize; pid='+str(child.pid)+' '+details)
        records = [read_process(child.pid, (package/'libkernel.so').resolve(),
                                library.resolve()) for child in children]
        return summarize(records, backend, count)
    finally:
        for child in children:
            if child.poll() is None:
                try:
                    child.stdin.write(b'x')
                    child.stdin.flush()
                except BrokenPipeError:
                    pass
            child.stdin.close()
        for child in children:
            try:
                code = child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                code = child.wait()
            if code and sys.exc_info()[0] is None:
                raise RuntimeError('resource worker exited with status '+str(code))
            child.stdout.close()
            child.stderr.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('collect', 'worker'))
    parser.add_argument('backend', choices=('raw', 'vkso'))
    parser.add_argument('package', type=Path)
    args = parser.parse_args()
    if args.mode == 'worker':
        first_touch(args.backend, args.package)
        print('READY', flush=True)
        sys.stdin.buffer.read(1)
        return
    if os.geteuid() != 0:
        raise ValueError('root pagemap access required')
    package = args.package.resolve()
    groups = [cohort(count,args.backend,package) for count in COUNTS]
    print(json.dumps(dict(protocol=PROTOCOL, backend=args.backend,
                          scope='resident PFNs in named user time mappings; not net system RAM',
                          page_bytes=PAGE, kernel_release=os.uname().release,
                          counts=list(COUNTS), groups=groups), sort_keys=True))


if __name__ == '__main__':
    main()
