#!/usr/bin/python3
"""Real cooperative-owner lifetime and mapping checks in an exact119 guest."""
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import registration_completion_guest as G

ROOT, OUT, PAGE, LIBC = G.ROOT, G.OUT, G.PAGE, G.LIBC
LIBC.mprotect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]


class Owner(ctypes.Structure):
    _fields_ = [('symbol', ctypes.c_char * 64), ('srcversion', ctypes.c_char * 25),
                ('reserved', ctypes.c_ubyte * 7)]


class Replace(G.Replace):
    _fields_ = [('owner_count', ctypes.c_uint), ('owners', Owner * 8)]


def rpc(protocol, request, seq):
    return G.rpc(protocol, request, seq, 0x20, version=2, result_type=0x21)


def map_page(carrier):
    fd = os.open(carrier, os.O_RDONLY)
    try:
        address = LIBC.mmap(None, PAGE, 1, 2, fd, PAGE)
        assert address != ctypes.c_void_p(-1).value
        return address
    finally:
        os.close(fd)


def main():
    OUT.mkdir()
    record = dict(status='running', scope='cooperative module lifetime and backing, no performance trials',
                  kernel=os.uname().release,
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), checks={})
    checks = record['checks']

    def command(argv, name, expected=0):
        with (OUT / (name + '.log')).open('w') as stream:
            proc = subprocess.run(list(map(str, argv)), stdout=stream, stderr=subprocess.STDOUT, timeout=15)
        if expected is not None:
            assert proc.returncode == expected, (name, proc.returncode)
        return proc.returncode

    def refs():
        return {name: int(Path('/sys/module', name, 'refcnt').read_text())
                for name in ('vkso_lz4', 'page_cache_replace')}

    try:
        assert os.uname().release == '5.15.0-119-generic'
        for name in ('vkso_lz4', 'vkso_kernel_reader', 'page_cache_replace'):
            command(['insmod', ROOT / (name + '.ko')], 'load-' + name)
        owner = Path('/sys/module/vkso_lz4')
        source = int((owner / 'sections/.text').read_text(), 16)
        management = int((owner / 'sections/.vkso_owner').read_text(), 16)
        version = (owner / 'srcversion').read_text().strip()
        probe = Path('/sys/kernel/debug/vkso_kernel_reader')
        (probe / 'page_addresses').write_text(f'{hex(source)} {hex(management)}\n')
        text = (probe / 'pages').read_text()
        (OUT / 'source-pages.csv').write_text(text)
        pfns = {int(row.split(',')[0], 16): int(row.split(',')[1]) for row in text.splitlines()[1:]}
        assert source in pfns and management in pfns and pfns[source] != pfns[management]
        record.update(source=source, management=management, source_pfn=pfns[source], srcversion=version,
                      protocol_sizes=dict(replace=ctypes.sizeof(Replace), owner=ctypes.sizeof(Owner)))
        carrier = OUT / 'fixture.bin'
        carrier.write_bytes(b'H' * PAGE + b'Z' * PAGE)
        other = OUT / 'other.bin'
        other.write_bytes(carrier.read_bytes())
        for path in (carrier, other):
            with path.open('rb') as f:
                os.fsync(f.fileno())
        plan = OUT / 'page_mappings.txt'
        plan.write_text(f'# file_offset,kernel_vaddr,kind,section\n0x1000,{hex(source)},text,.fixture\n')
        (OUT / 'owner_descriptors.txt').write_text(f'vkso_lz4_owner {version}\n')
        request = Replace()
        request.path = str(carrier).encode(); request.count = 1
        request.offsets[0] = PAGE; request.sources[0] = source
        request.owner_count = 1
        request.owners[0].symbol = b'vkso_lz4_owner'
        request.owners[0].srcversion = version.encode()
        baseline = refs()
        assert baseline == {'vkso_lz4': 0, 'page_cache_replace': 0}
        for name, change, expected in [
            ('missing_owner', lambda r: setattr(r, 'owner_count', 0), -13),
            ('stale_srcversion', lambda r: setattr(r.owners[0], 'srcversion', b'BAD'), -116),
            ('management_not_exportable', lambda r: r.sources.__setitem__(0, management), -13),
        ]:
            bad = Replace.from_buffer_copy(request)
            change(bad)
            result = rpc(30, bad, 100 + len(checks))
            assert result['status'] == expected and result['completed'] == 0
            assert refs() == baseline and G.observe(carrier)['original']
            checks[name] = dict(result=result, refs_after=refs())
        with (OUT / 'manager-hold.log').open('w') as stream:
            manager = subprocess.Popen(list(map(str, [G.MANAGER, 'replace', carrier, plan, '--hold'])),
                                       stdout=stream, stderr=subprocess.STDOUT)
            read_mapping = cow_mapping = None
            try:
                deadline = time.monotonic() + 10
                while not (ROOT / 'runtime/manager.pid').exists():
                    assert manager.poll() is None and time.monotonic() < deadline
                    time.sleep(.01)
                active_refs = refs()
                assert active_refs == {'vkso_lz4': 1, 'page_cache_replace': 1}
                assert G.observe(carrier)['pfn'] == pfns[source]
                checks['active'] = dict(refs=active_refs, source_pfn=pfns[source])
                for name in ('vkso_lz4', 'page_cache_replace'):
                    rc = command(['rmmod', name], 'active-unload-' + name, None)
                    assert rc != 0 and Path('/sys/module', name).exists()
                    checks['unload_rejected_' + name] = rc
                conflict = Replace.from_buffer_copy(request)
                conflict.path = str(other).encode()
                result = rpc(30, conflict, 200)
                assert result['status'] == -16 and G.observe(other)['original'] and refs() == active_refs
                checks['different_inode_conflict'] = result
                release = G.Restore()
                release.path = str(other).encode(); release.count = 1; release.offsets[0] = PAGE
                result = rpc(29, release, 201)
                assert result['status'] == -18 and refs() == active_refs
                checks['wrong_mapping_restore_retains_owners'] = result
                read_mapping = map_page(carrier)
                original_source = ctypes.string_at(read_mapping, PAGE)
                cow_mapping = map_page(carrier)
                assert LIBC.mprotect(cow_mapping, PAGE, 3) == 0
                ctypes.c_ubyte.from_address(cow_mapping).value = 0x51
                assert ctypes.string_at(read_mapping, PAGE) == original_source
                checks['private_cow_source_unchanged'] = True
                manager.send_signal(signal.SIGTERM)
                rc = manager.wait(timeout=10)
                assert rc == 0 and refs() == baseline
                assert ctypes.string_at(read_mapping, PAGE) == b'Z' * PAGE
                assert ctypes.c_ubyte.from_address(cow_mapping).value == 0x51
                assert G.observe(carrier)['pfn'] != pfns[source]
                checks['restored'] = dict(manager_exit=rc, refs=refs(), live_read_mapping_original=True,
                                         private_cow_preserved=True)
            finally:
                if manager.poll() is None:
                    manager.send_signal(signal.SIGTERM); manager.wait(timeout=10)
                for address in (read_mapping, cow_mapping):
                    if address is not None: LIBC.munmap(address, PAGE)
        command(['rmmod', 'vkso_lz4'], 'released-owner-unload')
        command(['rmmod', 'vkso_kernel_reader'], 'released-probe-unload')
        command(['rmmod', 'page_cache_replace'], 'released-page-module-unload')
        record['modules_after'] = Path('/proc/modules').read_text()
        record['status'] = 'pass'
    except BaseException as error:
        record.update(status='fail', error=repr(error))
        raise
    finally:
        (OUT / 'dmesg.txt').write_text(subprocess.check_output(['dmesg'], text=True))
        (OUT / 'status.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
