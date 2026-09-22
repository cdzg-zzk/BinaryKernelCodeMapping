#!/usr/bin/python3
"""Exercise completion/error propagation in a private exact119 guest.

The full page module and manager are used. A failed batch's surviving prefix
is observed and explicitly restored; this is not a transactional rollback test.
"""
import ctypes
import errno
import json
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import time

ROOT = Path('/work')
OUT = ROOT / 'validation'
PAGE = 4096
MANAGER = ROOT / 'manager'
LIBC = ctypes.CDLL(None, use_errno=True)
LIBC.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int,
                      ctypes.c_int, ctypes.c_int, ctypes.c_long]
LIBC.mmap.restype = ctypes.c_void_p
LIBC.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]


class Replace(ctypes.Structure):
    _fields_ = [('path', ctypes.c_char * 256), ('offset', ctypes.c_longlong),
                ('address', ctypes.c_ulong), ('count', ctypes.c_int),
                ('offsets', ctypes.c_longlong * 256), ('sources', ctypes.c_ulong * 256)]


class Restore(ctypes.Structure):
    _fields_ = [('path', ctypes.c_char * 256), ('offset', ctypes.c_longlong),
                ('count', ctypes.c_int), ('offsets', ctypes.c_longlong * 256)]


def rpc(protocol, request, seq, message_type=0x10, version=1, result_type=0x11):
    payload = bytes(request)
    packet = struct.pack('IHHII', 16 + len(payload), message_type, 1, seq, 0) + payload
    with socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, protocol) as sock:
        sock.bind((0, 0))
        sock.settimeout(6)
        sock.sendto(packet, (0, 0))
        data, sender = sock.recvfrom(4096)
    length, kind, flags, sequence, port = struct.unpack_from('IHHII', data)
    assert sender == (0, 0) and sequence == seq and kind == result_type and length == len(data) == 48
    actual_version, operation, status, completed, failed, reserved, ns = struct.unpack_from('IIiIiIQ', data, 16)
    assert actual_version == version and operation == protocol and reserved == 0 and ns > 0
    return dict(sequence=sequence, status=status, completed=completed, failed_page=failed,
                kernel_operation_ns=ns)


def observe(path, offset=PAGE):
    fd = os.open(path, os.O_RDONLY)
    try:
        address = LIBC.mmap(None, PAGE, 1, 2, fd, offset)
    finally:
        os.close(fd)
    assert address != ctypes.c_void_p(-1).value
    try:
        content = ctypes.string_at(address, PAGE)
        fd = os.open('/proc/self/pagemap', os.O_RDONLY)
        try:
            entry, = struct.unpack('Q', os.pread(fd, 8, address // PAGE * 8))
        finally:
            os.close(fd)
        assert entry >> 63 and entry & ((1 << 55) - 1)
        return dict(pfn=entry & ((1 << 55) - 1), original=content == b'Z' * PAGE)
    finally:
        LIBC.munmap(address, PAGE)


def main():
    OUT.mkdir()
    record = dict(status='running', scope='completion protocol and manager errors; no performance trials',
                  kernel=os.uname().release,
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), checks={})
    checks = record['checks']

    def save():
        (OUT / 'status.json').write_text(json.dumps(record, indent=2) + '\n')

    def command(argv, name, expected=0):
        with (OUT / (name + '.log')).open('w') as log:
            result = subprocess.run(list(map(str, argv)), stdout=log, stderr=subprocess.STDOUT, timeout=20)
        if expected is not None:
            assert result.returncode == expected, (name, result.returncode)
        return result.returncode

    try:
        assert os.uname().release == '5.15.0-119-generic'
        for name in ('vkso_lz4', 'vkso_kernel_reader', 'page_cache_replace'):
            command(['insmod', ROOT / (name + '.ko')], 'load-' + name)
        owner = Path('/sys/module/vkso_lz4')
        source = int((owner / 'sections/.text').read_text(), 16) & ~(PAGE - 1)
        missing = 0xffffe7fffffff000
        probe = Path('/sys/kernel/debug/vkso_kernel_reader')
        (probe / 'page_addresses').write_text(f'{hex(source)} {hex(missing)}\n')
        source_text = (probe / 'pages').read_text()
        (OUT / 'source-pages.csv').write_text(source_text)
        pfns = {int(row.split(',')[0], 16): int(row.split(',')[1])
                for row in source_text.splitlines()[1:]}
        assert source in pfns and missing not in pfns
        record.update(source=source, source_pfn=pfns[source], owner_refcnt=int((owner / 'refcnt').read_text()))
        carrier = OUT / 'fixture.bin'
        carrier.write_bytes(b'H' * PAGE + b'Z' * (2 * PAGE))
        with carrier.open('rb') as f:
            os.fsync(f.fileno())
        plan = OUT / 'one-page.txt'
        plan.write_text(f'# file_offset,kernel_vaddr,kind,section\n0x1000,{hex(source)},text,.fixture\n')
        partial = OUT / 'partial.txt'
        partial.write_text(plan.read_text() + f'0x2000,{hex(missing)},text,.missing\n')
        request = Replace()
        request.path = str(carrier).encode()
        request.count = 1
        request.offsets[0] = PAGE
        request.sources[0] = source
        for name, data, kind, expected in [
            ('short_payload', b'1234', 0x10, -errno.EMSGSIZE),
            ('legacy_type', Replace(), 0, -errno.EPROTONOSUPPORT),
            ('empty_batch', Replace(), 0x10, -errno.EINVAL),
            ('hello', Replace(), 0x12, 0),
        ]:
            result = rpc(30, data, 100 + len(checks), kind)
            assert result['status'] == expected and result['completed'] == 0
            checks[name] = result
        invalid = Replace.from_buffer_copy(request)
        invalid.offsets[0] = 1
        result = rpc(30, invalid, 110)
        assert result['status'] == -errno.EINVAL and result['failed_page'] == 0
        checks['unaligned'] = result
        invalid = Replace.from_buffer_copy(request)
        invalid.offsets[0] = 3 * PAGE
        result = rpc(30, invalid, 111)
        assert result['status'] == -errno.ERANGE and result['completed'] == 0
        checks['outside_file'] = result
        # Kernel credentials, not the userspace nlmsg_pid field, authorize work.
        child = os.fork()
        if child == 0:
            try:
                os.setgroups([]); os.setgid(65534); os.setuid(65534)
                try:
                    result = rpc(30, request, 112)
                    ok = result['status'] == -errno.EPERM
                except OSError as error:
                    ok = error.errno == errno.EPERM
                os._exit(0 if ok else 1)
            except BaseException:
                os._exit(2)
        assert os.waitpid(child, 0)[1] == 0
        checks['unprivileged_rejected'] = True
        assert observe(carrier)['original']
        # A real mid-batch source-resolution error must not publish ready.
        rc = command([MANAGER, 'replace', carrier, partial, '--hold'], 'partial-manager', None)
        log = (OUT / 'partial-manager.log').read_text()
        assert rc != 0 and not (ROOT / 'runtime/manager.pid').exists()
        assert 'status=-12 completed=1 failed_page=1' in log
        current = observe(carrier)
        assert current['pfn'] == pfns[source]
        checks['partial_failure'] = dict(manager_exit=rc, ready=False, first_binding_remains=current,
                                        recovery_state=(ROOT / 'runtime/manager.state').exists())
        assert checks['partial_failure']['recovery_state']
        command([MANAGER, 'restore', carrier, plan], 'explicit-prefix-recovery')
        assert observe(carrier)['original'] and observe(carrier)['pfn'] != pfns[source]
        assert not (ROOT / 'runtime/manager.state').exists()
        # Successful requests report all pages and allow subsequent sessions.
        for run in range(2):
            command([MANAGER, 'replace', carrier, plan], f'normal-{run}-replace')
            assert observe(carrier)['pfn'] == pfns[source]
            command([MANAGER, 'restore', carrier, plan], f'normal-{run}-restore')
            assert observe(carrier)['original']
        checks['normal_repeated_sessions'] = 2
        # Trigger an actual kernel restore error while the hold manager exists.
        with (OUT / 'hold-restore-error.log').open('w') as log:
            manager = subprocess.Popen(list(map(str, [MANAGER, 'replace', carrier, plan, '--hold'])),
                                       stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 10
                while not (ROOT / 'runtime/manager.pid').exists():
                    assert manager.poll() is None and time.monotonic() < deadline
                    time.sleep(.01)
                assert observe(carrier)['pfn'] == pfns[source]
                release = Restore()
                release.path = str(carrier).encode(); release.count = 1; release.offsets[0] = PAGE
                result = rpc(29, release, 200)
                assert result['status'] == 0 and result['completed'] == 1
                checks['external_restore'] = result
            finally:
                manager.send_signal(signal.SIGTERM)
                rc = manager.wait(timeout=10)
        log = (OUT / 'hold-restore-error.log').read_text()
        assert rc != 0 and 'status=-2 completed=0' in log
        assert 'Manager hold session restored and exiting.' not in log
        assert (ROOT / 'runtime/manager.state').exists() and observe(carrier)['original']
        checks['hold_restore_error'] = dict(manager_exit=rc, state_retained=True)
        # Test fixture owns this state and has independently observed recovery.
        for name in ('manager.pid', 'manager.state'):
            (ROOT / 'runtime' / name).unlink(missing_ok=True)
        command(['rmmod', 'page_cache_replace'], 'unload-new-module')
        command(['insmod', ROOT / 'legacy-page_cache_replace.ko'], 'load-legacy-module')
        rc = command([MANAGER, 'replace', carrier, plan, '--hold'], 'mixed-version', None)
        assert rc != 0 and not (ROOT / 'runtime/manager.pid').exists()
        assert observe(carrier)['original'] and observe(carrier)['pfn'] != pfns[source]
        checks['new_manager_old_module'] = dict(manager_exit=rc, unchanged_backing=True)
        command(['rmmod', 'page_cache_replace'], 'unload-legacy-module')
        command(['rmmod', 'vkso_kernel_reader'], 'unload-probe')
        command(['rmmod', 'vkso_lz4'], 'unload-owner')
        record['modules_after'] = Path('/proc/modules').read_text()
        record['status'] = 'pass'
    except BaseException as error:
        record.update(status='fail', error=repr(error))
        raise
    finally:
        (OUT / 'dmesg.txt').write_text(subprocess.check_output(['dmesg'], text=True))
        save()


if __name__ == '__main__':
    main()
