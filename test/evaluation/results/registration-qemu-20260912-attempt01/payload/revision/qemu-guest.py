#!/usr/bin/python3
"""Disposable-guest observations of the existing page-grafting implementation."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import struct
import subprocess
import sys
import time

PAGE = 4096
ROOT = Path('/work')
OUT = ROOT / 'validation'
LIBC = ctypes.CDLL(None, use_errno=True)
LIBC.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int,
                      ctypes.c_int, ctypes.c_int, ctypes.c_long]
LIBC.mmap.restype = ctypes.c_void_p
LIBC.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
LIBC.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]


def mapping(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        address = LIBC.mmap(None, PAGE, 1, 2, fd, PAGE)
    finally:
        os.close(fd)
    if address == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_errno(), 'mmap')
    return address


def pfn(address):
    ctypes.c_ubyte.from_address(address).value  # fault in the observation
    with open('/proc/self/pagemap', 'rb') as f:
        f.seek((address // PAGE) * 8)
        entry, = struct.unpack('Q', f.read(8))
    assert entry >> 63 and entry & ((1 << 55) - 1)
    return entry & ((1 << 55) - 1)


def observation(address):
    return {'pid': os.getpid(), 'address': address, 'pfn': pfn(address),
            'bytes_sha256': hashlib.sha256(ctypes.string_at(address, PAGE)).hexdigest()}


def reader(path):
    address = mapping(path)
    print(json.dumps(observation(address)), flush=True)
    sys.stdin.readline()
    assert LIBC.munmap(address, PAGE) == 0


def main():
    OUT.mkdir()
    record = {'scope': 'KVM functional mechanism fixture; synthetic file backing, no API performance',
              'kernel': os.uname().release, 'guest_uid': os.getuid(),
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'phases': []}

    def save():
        (OUT / 'observations.json').write_text(json.dumps(record, indent=2) + '\n')

    def run(args, name):
        with (OUT / (name + '.log')).open('w') as f:
            return subprocess.run(list(map(str, args)), stdout=f, stderr=subprocess.STDOUT, check=True)

    for module in ['vkso_m09_clock', 'vkso_kernel_reader', 'page_cache_replace']:
        run(['insmod', ROOT / (module + '.ko')], 'load-' + module)
    owner = Path('/sys/module/vkso_m09_clock')
    source = int((owner / 'sections/.text').read_text().strip(), 16) & ~(PAGE - 1)
    probe = Path('/sys/kernel/debug/vkso_kernel_reader')
    (probe / 'page_addresses').write_text(hex(source) + '\n')
    kernel_pages = (probe / 'pages').read_text()
    (OUT / 'source-pages.csv').write_text(kernel_pages)
    source_pfn = int(kernel_pages.splitlines()[1].split(',')[1])
    record.update(source_address=source, source_pfn=source_pfn)

    def phase(name):
        record['phases'].append({'phase': name, 'owner_refcnt': int((owner / 'refcnt').read_text())})
        save()

    carrier = OUT / 'fixture.bin'
    carrier.write_bytes(b'H' * PAGE + b'Z' * PAGE)
    with carrier.open('rb') as f:
        os.fsync(f.fileno())
    plan = OUT / 'page_mappings.txt'
    plan.write_text(f'# file_offset,kernel_vaddr,kind,section\n0x1000,{hex(source)},text,.fixture_text\n')
    phase('before_registration')
    run([ROOT / 'manager', 'validate', carrier, plan], 'validate')
    manager_log = (OUT / 'manager-hold.log').open('w')
    manager = subprocess.Popen([str(ROOT / 'manager'), 'replace', str(carrier), str(plan), '--hold'],
                               stdout=manager_log, stderr=subprocess.STDOUT)
    children = []
    address = None
    try:
        deadline = time.monotonic() + 15
        while not (ROOT / 'runtime/manager.pid').is_file():
            if manager.poll() is not None:
                raise RuntimeError('manager exited before its ready file')
            if time.monotonic() >= deadline:
                raise RuntimeError('manager ready file timeout')
            time.sleep(.02)
        phase('manager_ready_file')
        address = mapping(carrier)
        record['parent_mapping'] = observation(address)
        assert record['parent_mapping']['pfn'] == source_pfn
        for _ in range(2):
            child = subprocess.Popen([sys.executable, __file__, '--reader', str(carrier)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            children.append(child)
            child_record = json.loads(child.stdout.readline())
            assert child_record['pfn'] == source_pfn
            assert child_record['bytes_sha256'] == record['parent_mapping']['bytes_sha256']
            record.setdefault('child_mappings', []).append(child_record)
        phase('three_reader_processes_mapped')

        # A normal user-mode store through the existing read-only PTE must fault.
        pid = os.fork()
        if pid == 0:
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            ctypes.c_ubyte.from_address(address).value ^= 1
            os._exit(0)
        _, status = os.waitpid(pid, 0)
        record['readonly_store_signal'] = os.WTERMSIG(status) if os.WIFSIGNALED(status) else None
        assert record['readonly_store_signal'] == signal.SIGSEGV

        # MAP_PRIVATE may become writable through COW; observe backing after a store.
        result = LIBC.mprotect(address, PAGE, 1 | 2)
        record['private_mprotect_result'] = result
        record['private_mprotect_errno'] = ctypes.get_errno() if result else 0
        if result == 0:
            ctypes.c_ubyte.from_address(address).value ^= 1
            record['private_after_store'] = observation(address)
            assert record['private_after_store']['pfn'] != source_pfn
            fresh = mapping(carrier)
            try:
                record['source_after_private_store'] = observation(fresh)
                assert record['source_after_private_store']['pfn'] == source_pfn
                assert record['source_after_private_store']['bytes_sha256'] == record['parent_mapping']['bytes_sha256']
            finally:
                LIBC.munmap(fresh, PAGE)
        phase('after_permission_observations')
    finally:
        if address is not None:
            LIBC.munmap(address, PAGE)
        for child in children:
            child.communicate('\n', timeout=5)
            assert child.returncode == 0
        phase('readers_closed_before_restore')
        if manager.poll() is None:
            manager.send_signal(signal.SIGTERM)
        record['manager_exit_code'] = manager.wait(timeout=15)
        manager_log.close()
        save()
    assert record['manager_exit_code'] == 0
    phase('after_restore')
    restored = mapping(carrier)
    try:
        record['restored_mapping'] = observation(restored)
        assert record['restored_mapping']['pfn'] != source_pfn
        assert ctypes.string_at(restored, PAGE) == b'Z' * PAGE
    finally:
        LIBC.munmap(restored, PAGE)
    run(['rmmod', 'vkso_m09_clock'], 'normal-owner-unload')
    record['owner_absent_after_ordered_unload'] = not owner.exists()
    assert record['owner_absent_after_ordered_unload']
    record['complete'] = True
    save()
    print('registration_fixture=pass', flush=True)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--reader':
        reader(sys.argv[2])
    else:
        main()
