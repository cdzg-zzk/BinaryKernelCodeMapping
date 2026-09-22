#!/usr/bin/env python3
"""Guest-only census of live Clocktime MM_data and complete carrier mappings."""
import ctypes
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import threading

LIBC = ctypes.CDLL(None, use_errno=True)
LIBC.getauxval.argtypes = [ctypes.c_ulong]
LIBC.getauxval.restype = ctypes.c_ulong
PAGE = 4096
CARRIER = '/work/package/libkernel.so'


def page(address):
    payload = ctypes.string_at(address, PAGE)
    with open('/proc/self/pagemap', 'rb') as stream:
        stream.seek(address // PAGE * 8)
        entry, = struct.unpack('<Q', stream.read(8))
    assert entry >> 63 and entry & ((1 << 55) - 1)
    return dict(address=address, pfn=entry & ((1 << 55) - 1), bytes=payload.hex())


def observe(load):
    address = LIBC.getauxval(52)
    assert address
    result = dict(pid=os.getpid(), namespace=os.readlink('/proc/self/ns/time'),
                  mm=page(address))
    result['mm']['abi'], result['mm']['mask'] = struct.unpack_from('<II', bytes.fromhex(result['mm']['bytes']))
    assert result['mm']['abi'] == 3
    threads = []
    if load:
        lib = ctypes.CDLL(CARRIER)
        bind = lib.__vkso_bind_context
        bind.argtypes = [ctypes.c_void_p] * 3
        assert bind(address, None, None) == 0
        value = (ctypes.c_int64 * 2)()
        assert lib.__vkso_clock_gettime(0, value) == 0
        assert value[0] > 0
        cpu, node = ctypes.c_uint(), ctypes.c_uint()
        assert lib.__vkso_getcpu(ctypes.byref(cpu), ctypes.byref(node), None) == 0
        assert lib.__vkso_gettimeofday(value, None) == 0
        mappings = []
        for line in Path('/proc/self/maps').read_text().splitlines():
            fields = line.split()
            if fields[-1] != CARRIER or 'r' not in fields[1]:
                continue
            begin, end = (int(v, 16) for v in fields[0].split('-'))
            for virtual in range(begin, end, PAGE):
                item = page(virtual)
                item.pop('bytes')
                item.update(offset=int(fields[2], 16) + virtual - begin, permissions=fields[1])
                mappings.append(item)
        result['carrier'] = mappings
        assert len(mappings) == 5
        for _ in range(4):
            worker = threading.Thread(target=lambda: threads.append(page(address)['pfn']))
            worker.start()
            worker.join()
        result['thread_mm_pfns'] = threads
        assert threads == [result['mm']['pfn']] * 4
    result['VmPTE'] = next(line for line in Path('/proc/self/status').read_text().splitlines()
                           if line.startswith('VmPTE:'))
    return result


def group(count, mode, load, expected_pages=None):
    children, records = [], []
    try:
        for _ in range(count):
            if mode == 'exec':
                process = subprocess.Popen([sys.executable, __file__, 'child', str(int(load))],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                children.append(process)
                records.append(json.loads(process.stdout.readline()))
            else:
                read_result, write_result = os.pipe()
                read_wait, write_wait = os.pipe()
                pid = os.fork()
                if not pid:
                    os.close(read_result)
                    os.close(write_wait)
                    with os.fdopen(write_result, 'w') as stream:
                        stream.write(json.dumps(observe(False)) + '\n')
                    os.read(read_wait, 1)
                    os._exit(0)
                os.close(write_result)
                os.close(read_wait)
                children.append((pid, write_wait))
                with os.fdopen(read_result) as stream:
                    records.append(json.loads(stream.readline()))
        # All children remain alive until this census is complete.
        unique_pages = len({r['mm']['pfn'] for r in records})
        assert unique_pages == (count if expected_pages is None else expected_pages)
        assert len({r['mm']['bytes'] for r in records}) == 1
        assert len({r['namespace'] for r in records}) == 1
        return dict(count=count, mode=mode, carrier_loaded=load, records=records,
                    unique_mm_pages=unique_pages, identical_mm_bytes=True,
                    mm_payload_bytes=40, mm_allocated_bytes=unique_pages * PAGE)
    finally:
        for process in children:
            if isinstance(process, tuple):
                os.write(process[1], b'x')
                os.close(process[1])
                pid, status = os.waitpid(process[0], 0)
                assert os.waitstatus_to_exitcode(status) == 0
            else:
                process.stdin.close()
                assert process.wait() == 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'child':
        print(json.dumps(observe(bool(int(sys.argv[2])))), flush=True)
        sys.stdin.read(1)
        return
    output = Path('/work/results')
    output.mkdir(exist_ok=True)
    report = dict(scope='live PFNs in the original packaged VKSO kernel; no performance claims',
                  kernel=os.uname().release, groups=[])
    report['groups'].append(group(32, 'fork', False))
    for count in (1, 8, 32):
        report['groups'].append(group(count, 'exec', True))
    assert LIBC.unshare(0x80) == 0, ctypes.get_errno()  # CLONE_NEWTIME
    Path('/proc/self/timens_offsets').write_text('monotonic 123 456\nboottime 789 123\n')
    report['groups'].append(group(8, 'exec', True))
    assert report['groups'][-1]['records'][0]['namespace'] != report['groups'][1]['records'][0]['namespace']
    assert report['groups'][-1]['records'][0]['mm']['mask'] != 0
    (output / 'memory.json').write_text(json.dumps(report, indent=2) + '\n')
    print('memory_probe=pass', flush=True)


if __name__ == '__main__':
    main()
