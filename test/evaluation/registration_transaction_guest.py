#!/usr/bin/env python3
"""Exercise the full v4 module/manager; no performance samples."""
import ctypes as C
import json
import mmap
import fcntl
import os
import re
from pathlib import Path
import signal
import socket
import struct
import subprocess
import time
import registration_completion_guest as G

ROOT, OUT, PAGE = G.ROOT, G.OUT, G.PAGE
LIBC = G.LIBC
BEGIN, STAGE, COMMIT, QUERY, RELEASE, FORGET = range(1, 7)
UNKNOWN, STAGING, ACTIVE, ABORTED, RESTORED, RECOVERY = range(6)
TEXT, RODATA, SHARED_DATA = range(1, 4)

class Owner(C.Structure):
    _fields_ = [('symbol', C.c_char * 64), ('srcversion', C.c_char * 25), ('reserved', C.c_ubyte * 7)]
class Page(C.Structure):
    _fields_ = [('offset', C.c_uint64), ('source', C.c_uint64),
                ('kind', C.c_uint32), ('reserved', C.c_uint32)]
class Request(C.Structure):
    _fields_ = [('version', C.c_uint32), ('operation', C.c_uint32), ('transaction', C.c_uint64),
                ('total', C.c_uint32), ('start', C.c_uint32), ('count', C.c_uint32),
                ('owner_count', C.c_uint32), ('device', C.c_uint64), ('inode', C.c_uint64),
                ('filepath', C.c_char * 256), ('owners', Owner * 8), ('pages', Page * 256)]
class Result(C.Structure):
    _fields_ = [('version', C.c_uint32), ('operation', C.c_uint32), ('transaction', C.c_uint64),
                ('status', C.c_int32), ('state', C.c_uint32), ('total', C.c_uint32),
                ('staged', C.c_uint32), ('applied', C.c_uint32), ('failed_page', C.c_int32),
                ('last_operation', C.c_uint32), ('last_sequence', C.c_uint32),
                ('last_status', C.c_int32), ('reserved', C.c_uint32),
                ('operation_ns', C.c_uint64), ('prepare_ns', C.c_uint64),
                ('apply_ns', C.c_uint64), ('release_ns', C.c_uint64)]

class Client:
    def __init__(self):
        self.fd = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, 30)
        self.fd.bind((0, 0)); self.fd.settimeout(2); self.seq = 0
    def rpc(self, operation, tid, expected=0, request=None, lost=False, version=4, wire_size=None):
        r = request or Request(); r.version = version; r.operation = operation; r.transaction = tid
        self.seq += 1
        payload = bytes(r) if wire_size is None else bytes(r)[:wire_size]
        self.fd.sendto(struct.pack('IHHII', 16 + len(payload), 0x30, 1, self.seq, 0) + payload, (0, 0))
        if lost:
            try: self.fd.recv(8192)
            except TimeoutError: return self.seq
            raise AssertionError('expected dropped reply')
        data, sender = self.fd.recvfrom(8192)
        size, typ, flags, seq, pid = struct.unpack_from('IHHII', data)
        assert sender == (0, 0) and size == len(data) == 16 + C.sizeof(Result)
        assert typ == 0x31 and seq == self.seq
        result = Result.from_buffer_copy(data[16:])
        d = {name: getattr(result, name) for name, _ in Result._fields_}
        assert (d['version'], d['operation'], d['transaction'], d['status']) == (4, operation, tid, expected), d
        return d


def main():
    OUT.mkdir()
    record = dict(status='running', scope='v4 typed full-plan registration and recovery; no performance trials',
                  kernel=os.uname().release, boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), checks={})
    checks = record['checks']
    owner_name = 'vkso_lz4'
    descriptor_name = 'vkso_lz4_owner'
    def command(argv, name, expected=0):
        with (OUT / (name + '.log')).open('w') as f:
            p = subprocess.run(list(map(str, argv)), stdout=f, stderr=subprocess.STDOUT, timeout=20)
        if expected is not None: assert p.returncode == expected, (name, p.returncode)
        return p.returncode
    def refs():
        return {name: int(Path('/sys/module', name, 'refcnt').read_text())
                for name in (owner_name, 'page_cache_replace')}
    params = Path('/sys/module/page_cache_replace/parameters')
    def inject(name, value): (params / name).write_text(str(value))
    def fixture(name, count=3):
        path = OUT / name; path.write_bytes(b'H' * PAGE + b'Z' * PAGE * count)
        with path.open('rb') as f: os.fsync(f.fileno())
        return path
    def original(path): return path.read_bytes()[PAGE:] == b'Z' * (path.stat().st_size - PAGE)
    try:
        assert os.uname().release == '5.15.0-119-generic'
        for name in ('vkso_lz4', 'vkso_kernel_reader', 'page_cache_replace'):
            command(['insmod', ROOT / (name + '.ko')], 'load-' + name)
        if Path('/sys/module/vkso_tx_fixture').exists():
            owner_name, descriptor_name = 'vkso_tx_fixture', 'vkso_fixture_owner'
        record['owner'] = owner_name
        owner = Path('/sys/module', owner_name)
        source = int((owner / 'sections/.text').read_text(), 16)
        management = int((owner / 'sections/.vkso_owner').read_text(), 16)
        version = (owner / 'srcversion').read_text().strip()
        probe = Path('/sys/kernel/debug/vkso_kernel_reader')
        (probe / 'page_addresses').write_text(' '.join(hex(source + i*PAGE) for i in range(3))+'\n')
        (OUT / 'source-pages.csv').write_text((probe / 'pages').read_text())
        client = Client()
        def begin(path, tid, count=3, expected=0):
            r = Request(); r.total = count; r.filepath = str(path).encode()
            st = path.stat(); r.device = st.st_dev; r.inode = st.st_ino
            r.owner_count = 1; r.owners[0].symbol = descriptor_name.encode()
            r.owners[0].srcversion = version.encode()
            return client.rpc(BEGIN, tid, expected, r)
        def stage(tid, count=3, sources=None):
            r = Request(); r.total = count; r.count = count
            for i in range(count):
                r.pages[i].offset = (i+1)*PAGE
                r.pages[i].source = sources[i] if sources else source+i*PAGE
                r.pages[i].kind = TEXT
            return client.rpc(STAGE, tid, request=r)
        baseline = refs(); record['transport_open_baseline_refs'] = baseline; assert baseline == {owner_name: 0, 'page_cache_replace': 1}
        assert (C.sizeof(Page), C.sizeof(Request), C.sizeof(Result)) == (24, 7216, 88)
        checks['protocol_v3_rejected'] = client.rpc(QUERY, 700, -93, version=3, wire_size=5168)
        checks['protocol_v4_short_rejected'] = client.rpc(QUERY, 701, -90, wire_size=16)
        checks['protocol_layout'] = dict(page=C.sizeof(Page), request=C.sizeof(Request), result=C.sizeof(Result))
        for case, (kind, reserved) in enumerate(((0, 0), (4, 0), (TEXT, 1))):
            tid = 710 + case; typed_path = fixture(f'invalid-kind-{case}.bin', 1)
            begin(typed_path, tid, 1)
            r = Request(); r.total = r.count = 1
            r.pages[0].offset = PAGE; r.pages[0].source = source
            r.pages[0].kind = kind; r.pages[0].reserved = reserved
            reply = client.rpc(STAGE, tid, -22, r)
            assert reply['staged'] == reply['applied'] == 0 and original(typed_path)
            client.rpc(RELEASE, tid); client.rpc(FORGET, tid)
            assert refs() == baseline
            checks[f'invalid-page-kind-{case}'] = reply
        # All positions are checked before replacing any destination page.
        for case, kind in enumerate((RODATA, SHARED_DATA)):
            for bad in range(3):
                tid = 720 + case * 3 + bad; typed_path = fixture(f'type-mismatch-{case}-{bad}.bin')
                begin(typed_path, tid)
                r = Request(); r.total = r.count = 3
                for i in range(3):
                    r.pages[i].offset = (i+1)*PAGE; r.pages[i].source = source+i*PAGE
                    r.pages[i].kind = kind if i == bad else TEXT
                client.rpc(STAGE, tid, request=r)
                reply = client.rpc(COMMIT, tid, -13)
                assert reply['state'] == ABORTED and reply['applied'] == 0 and reply['failed_page'] == bad
                assert original(typed_path) and refs() == baseline
                client.rpc(FORGET, tid)
                checks[f'page-type-mismatch-{case}-{bad}'] = reply
        path = fixture('writer.bin')
        fd = os.open(path, os.O_RDWR)
        try: checks['existing_writer'] = begin(path, 1, expected=-26)
        finally: os.close(fd)
        assert original(path) and refs() == baseline
        fd = os.open(path, os.O_RDWR)
        writable = mmap.mmap(fd, PAGE, access=mmap.ACCESS_WRITE, offset=PAGE)
        os.close(fd)
        try:
            checks['existing_shared_writable_mapping'] = begin(path, 2, expected=-26)
        finally:
            writable.close()
        assert original(path) and refs() == baseline
        # An out-of-range source at each position is rejected before any apply.
        for bad in range(3):
            tid = 10 + bad; path = fixture(f'preflight-{bad}.bin')
            begin(path, tid); addresses = [source+i*PAGE for i in range(3)]; addresses[bad] = management
            stage(tid, sources=addresses)
            r = client.rpc(COMMIT, tid, -13)
            assert r['state'] == ABORTED and r['applied'] == 0 and r['failed_page'] == bad
            assert original(path) and refs() == baseline
            checks[f'preflight-{bad}'] = r
        for bad in range(3):
            tid = 20 + bad; path = fixture(f'apply-{bad}.bin')
            begin(path, tid); stage(tid); inject('test_fail_apply', bad)
            r = client.rpc(COMMIT, tid, -5)
            assert r['state'] == ABORTED and not r['applied'] and r['failed_page'] == bad
            assert original(path) and refs() == baseline
            assert client.rpc(RELEASE, tid)['state'] == ABORTED
            checks[f'apply-rollback-{bad}'] = r
        path = fixture('recovery.bin'); begin(path, 30); stage(30)
        r = client.rpc(COMMIT, 30); assert r['state'] == ACTIVE and r['applied'] == 3
        assert refs() == {owner_name: 1, 'page_cache_replace': 2}
        read_fd = os.open(path, os.O_RDONLY)
        read_map = mmap.mmap(read_fd, PAGE, access=mmap.ACCESS_READ, offset=PAGE)
        cow_map = mmap.mmap(read_fd, PAGE, access=mmap.ACCESS_COPY, offset=PAGE)
        os.close(read_fd)
        original_source = read_map[:]
        cow_map[0] = 81
        assert read_map[:] == original_source
        inject('test_fail_release', 1)
        r = client.rpc(RELEASE, 30, -5)
        assert r['state'] == RECOVERY and r['applied'] == 1 and r['failed_page'] == 1
        data = path.read_bytes()
        assert data[PAGE:2*PAGE] == b'Z'*PAGE and data[3*PAGE:] == b'Z'*PAGE and data[2*PAGE:3*PAGE] != b'Z'*PAGE
        assert refs() == {owner_name: 1, 'page_cache_replace': 2}
        checks['release_continues_after_error'] = r
        for name in (owner_name, 'page_cache_replace'):
            assert command(['rmmod', name], 'recovery-unload-'+name, None) != 0
        assert client.rpc(RELEASE, 30)['state'] == RESTORED and original(path) and refs() == baseline
        assert client.rpc(RELEASE, 30)['state'] == RESTORED
        assert read_map[:] == b'Z'*PAGE and cow_map[0] == 81
        read_map.close(); cow_map.close()
        checks['persistent_mapping_and_private_cow'] = True
        checks['release_retry_and_idempotence'] = True
        # Commit rollback itself can leave a recoverable page; all other pages
        # are still removed even when this first reverse-order release fails.
        path = fixture('rollback-recovery.bin'); begin(path, 31); stage(31)
        inject('test_fail_apply', 2); inject('test_fail_release', 1)
        r = client.rpc(COMMIT, 31, -5)
        assert r['state'] == RECOVERY and r['applied'] == 1
        checks['commit_rollback_recovery'] = r
        assert client.rpc(RELEASE, 31)['state'] == RESTORED and original(path) and refs() == baseline
        path = fixture('lost-ack.bin'); begin(path, 40); stage(40)
        inject('test_drop_reply', COMMIT)
        seq = client.rpc(COMMIT, 40, lost=True)
        r = client.rpc(QUERY, 40)
        assert r['state'] == ACTIVE and r['last_operation'] == COMMIT and r['last_sequence'] == seq and r['last_status'] == 0
        checks['lost_commit_ack_query'] = r
        client.rpc(RELEASE, 40); assert original(path) and refs() == baseline
        # Multiple transactions may use disjoint PFNs, never the same PFN.
        first, other, disjoint = fixture('first.bin', 1), fixture('other.bin', 1), fixture('disjoint.bin', 1)
        begin(first, 50, 1); stage(50, 1); client.rpc(COMMIT, 50)
        begin(other, 51, 1); stage(51, 1)
        r = client.rpc(COMMIT, 51, -16); assert r['state'] == ABORTED and original(other)
        begin(disjoint, 52, 1); stage(52, 1, [source+PAGE]); client.rpc(COMMIT, 52)
        assert refs() == {owner_name: 2, 'page_cache_replace': 3}
        client.rpc(RELEASE, 50); client.rpc(RELEASE, 52)
        assert original(first) and original(disjoint) and refs() == baseline
        checks['conflict_and_disjoint_transactions'] = r
        if owner_name == 'vkso_tx_fixture':
            for case, fail in enumerate((0, 150, 255, 256, 299, None)):
                tid = 100 + case; path = fixture(f'cross-batch-{case}.bin', 300)
                begin(path, tid, 300)
                for start in (0, 256):
                    r = Request(); r.total = 300; r.start = start; r.count = min(256, 300-start)
                    for i in range(r.count):
                        r.pages[i].offset = (start+i+1)*PAGE
                        r.pages[i].source = source+(start+i)*PAGE
                        r.pages[i].kind = TEXT
                    reply = client.rpc(STAGE, tid, request=r)
                    assert reply['staged'] == start+r.count and original(path)
                    assert client.rpc(STAGE, tid, request=r)['staged'] == start+r.count
                if fail is not None: inject('test_fail_apply', fail)
                reply = client.rpc(COMMIT, tid, -5 if fail is not None else 0)
                if fail is not None:
                    assert reply['state'] == ABORTED and reply['applied'] == 0 and reply['failed_page'] == fail
                else:
                    assert reply['state'] == ACTIVE and reply['applied'] == 300
                    assert path.read_bytes()[PAGE:] == b'\x90' * 300*PAGE
                    client.rpc(RELEASE, tid)
                assert original(path) and refs() == baseline
                checks[f'cross_batch_{fail}'] = reply
        # Occupied slots at several xarray depths: replacement must retain
        # their metadata even when each selected leaf has a single file page.
        sparse = OUT / 'sparse.bin'
        indices = (1, 64, 4096, 262144)
        with sparse.open('wb') as stream:
            stream.truncate((indices[-1]+1)*PAGE)
            for index in indices:
                stream.seek(index*PAGE); stream.write(b'Z'*PAGE)
            stream.flush(); os.fsync(stream.fileno())
        begin(sparse, 130, len(indices))
        r = Request(); r.total = r.count = len(indices)
        for i, index in enumerate(indices):
            r.pages[i].offset = index*PAGE; r.pages[i].source = source+i*PAGE; r.pages[i].kind = TEXT
        client.rpc(STAGE, 130, request=r)
        r = client.rpc(COMMIT, 130); assert r['applied'] == len(indices)
        client.rpc(RELEASE, 130)
        observed_pages = []
        with sparse.open('rb') as stream:
            for index in indices:
                stream.seek(index*PAGE); observed_pages.append(stream.read(PAGE))
                assert observed_pages[-1] == b'Z'*PAGE
        (OUT / 'sparse-restored-selected-pages.bin').write_bytes(b''.join(observed_pages))
        sparse.unlink() # Keep the selected observations without expanding the sparse file on extraction.
        assert refs() == baseline
        checks['sparse_xarray_slots'] = dict(indices=indices, commit=r)
        # Read-only mappings from three processes repeatedly fault while the
        # transaction is removed. Complete pages must be source or file bytes.
        path = fixture('concurrent.bin', 1); begin(path, 150, 1); stage(150, 1)
        client.rpc(COMMIT, 150)
        reader_code = r"""
import mmap, os, sys, time
from pathlib import Path
path, ready, done = map(Path, sys.argv[1:])
fd = os.open(path, os.O_RDONLY)
m = mmap.mmap(fd, 4096, access=mmap.ACCESS_READ, offset=4096)
source = m[:]; assert source != b'Z'*4096
ready.write_text('ready')
n = 0
while not done.exists():
    m.madvise(mmap.MADV_DONTNEED)
    b = m[:]
    assert all(v == source[i] or v == 90 for i, v in enumerate(b))
    n += 1
assert m[:] == b'Z'*4096
ready.write_text(str(n))
m.close(); os.close(fd)
"""
        readers = []
        done = OUT / 'readers.done'
        for i in range(3):
            ready = OUT / f'reader-{i}.ready'
            log = (OUT / f'reader-{i}.log').open('w')
            readers.append((subprocess.Popen(['python3', '-c', reader_code, str(path), str(ready), str(done)], stdout=log, stderr=subprocess.STDOUT), ready, log))
        try:
            deadline = time.monotonic()+10
            while not all(r.exists() for _, r, _ in readers):
                assert all(p.poll() is None for p, _, _ in readers) and time.monotonic() < deadline
                time.sleep(.01)
            time.sleep(.05)
            client.rpc(RELEASE, 150); done.touch()
            for p, ready, log in readers:
                assert p.wait(timeout=10) == 0
                assert int(ready.read_text()) > 0
                log.close()
            checks['three_process_fault_release'] = [int(r.read_text()) for _, r, _ in readers]
        finally:
            for p, _, log in readers:
                if p.poll() is None: p.kill(); p.wait()
                log.close()
        assert original(path) and refs() == baseline
        # The actual manager must recover its COMMIT ACK before publishing PID.
        path = fixture('manager.bin', 1)
        plan = OUT / 'page_mappings.txt'
        plan.write_text(f'# file_offset,kernel_vaddr,kind,section\n0x1000,{hex(source)},text,.fixture\n')
        identities = json.loads((ROOT / 'image-identities.json').read_text())
        assert (identities['owner_module'], identities['owner_srcversion']) == (owner_name, version)
        owner_manifest = f"{descriptor_name} {version} {owner_name} {identities['owner_build_id']}\n"
        kernel_manifest = f"kernel {identities['kernel_build_id']}\n"
        (OUT / 'owner_descriptors.txt').write_text(owner_manifest)
        (OUT / 'kernel_identity.txt').write_text(kernel_manifest)
        (OUT / 'image-identities.json').write_text(json.dumps(identities, indent=2)+'\n')
        # Source-version alone accepts this second real build; its linked-image
        # identity must fail while BEGIN holds a reference, before any STAGE.
        negative_manifests = {
            'wrong-module': (owner_manifest.replace(' '+owner_name+' ', ' nonexistent_owner '), kernel_manifest),
            'wrong-kernel': (owner_manifest, f"kernel {identities['owner_build_id']}\n"),
        }
        if 'variant_build_id' in identities:
            negative_manifests['same-source-different-build'] = (owner_manifest.replace(identities['owner_build_id'], identities['variant_build_id']), kernel_manifest)
        for name, (owner_text, kernel_text) in negative_manifests.items():
            (OUT / 'owner_descriptors.txt').write_text(owner_text)
            (OUT / 'kernel_identity.txt').write_text(kernel_text)
            rc = command([G.MANAGER, 'replace', path, plan, '--hold'], 'identity-'+name, None)
            log = (OUT / ('identity-'+name+'.log')).read_text()
            assert rc != 0 and 'mismatch' in log and 'phase=after-begin' in log
            assert 'operation=1 ' in log and 'operation=2 ' not in log and 'operation=3 ' not in log
            assert original(path) and refs() == baseline
            assert not (ROOT / 'runtime/manager.state').exists() and not (ROOT / 'runtime/manager.pid').exists()
            checks['image-identity-'+name] = True
        (OUT / 'owner_descriptors.txt').write_text(owner_manifest)
        (OUT / 'kernel_identity.txt').write_text(kernel_manifest)
        from registration_wrapper_guest import validate as validate_wrapper
        directory=OUT/'file-boundaries';directory.mkdir();os.chown(directory,65534,65534);directory.chmod(0o777)
        wrapper_path=fixture('file-boundaries/carrier.bin',1)
        os.chown(wrapper_path,65534,65534);wrapper_path.chmod(0o666)
        os.link(wrapper_path,directory/'alias.bin')
        checks['wrapper-and-file-boundaries']=validate_wrapper(wrapper_path,plan,refs,baseline,command)
        inject('test_drop_reply', COMMIT)
        with (OUT / 'manager-hold.log').open('w') as stream:
            manager = subprocess.Popen([str(G.MANAGER), 'replace', str(path), str(plan), '--hold'], stdout=stream, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic()+20
                while not (ROOT / 'runtime/manager.pid').exists():
                    assert manager.poll() is None and time.monotonic() < deadline
                    time.sleep(.02)
                assert not original(path) and refs() == {owner_name: 1, 'page_cache_replace': 2}
                inject('test_drop_reply', RELEASE)
                manager.send_signal(signal.SIGTERM)
                assert manager.wait(timeout=20) == 0
            finally:
                if manager.poll() is None: manager.kill(); manager.wait()
        assert original(path) and refs() == baseline
        assert not (ROOT / 'runtime/manager.state').exists()
        log = (OUT / 'manager-hold.log').read_text()
        assert log.count('recovered_reply') == 2
        checks['manager_lost_commit_and_release_ack'] = True
        with (OUT / 'manager-crash.log').open('w') as stream:
            manager = subprocess.Popen([str(G.MANAGER), 'replace', str(path), str(plan), '--hold'], stdout=stream, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic()+10
                while not (ROOT / 'runtime/manager.pid').exists():
                    assert manager.poll() is None and time.monotonic() < deadline
                    time.sleep(.01)
                (OUT / 'crashed-manager.state').write_text((ROOT / 'runtime/manager.state').read_text())
                manager.kill(); manager.wait()
                assert not original(path)
                command([G.MANAGER, 'restore', path, plan], 'manager-reconnect-release')
            finally:
                if manager.poll() is None: manager.kill(); manager.wait()
        assert original(path) and refs() == baseline and not (ROOT / 'runtime/manager.state').exists()
        checks['manager_crash_reconnect_release'] = True
        # Crash at real manager checkpoints spanning the initial write-ahead
        # record, immutable change, BEGIN, STAGE and successful COMMIT.
        for checkpoint in ('state-persisted', 'immutable-set', 'begin-confirmed', 'staged', 'committed'):
            with (OUT / f'manager-checkpoint-{checkpoint}.log').open('w') as stream:
                env = dict(os.environ, VKSO_TEST_STOP_AT=checkpoint)
                manager = subprocess.Popen([str(G.MANAGER), 'replace', str(path), str(plan), '--hold'],
                                           stdout=stream, stderr=subprocess.STDOUT, env=env)
                try:
                    deadline = time.monotonic()+10
                    while True:
                        assert manager.poll() is None and time.monotonic() < deadline
                        status = Path(f'/proc/{manager.pid}/status').read_text()
                        if any(line.startswith('State:') and 'T' in line for line in status.splitlines()): break
                        time.sleep(.01)
                    assert (ROOT / 'runtime/manager.state').exists()
                    assert not (ROOT / 'runtime/manager.pid').exists()
                    (OUT / f'checkpoint-{checkpoint}.state').write_text((ROOT / 'runtime/manager.state').read_text())
                    manager.kill(); manager.wait()
                    command([G.MANAGER, 'restore', path, plan], f'checkpoint-{checkpoint}-recovery')
                finally:
                    if manager.poll() is None: manager.kill(); manager.wait()
            assert original(path) and refs() == baseline and not (ROOT / 'runtime/manager.state').exists()
            fd = os.open(path, os.O_RDONLY)
            flags, = struct.unpack('I', fcntl.ioctl(fd, 0x80086601, struct.pack('I',0)))
            os.close(fd); assert not flags & 16
            checks['checkpoint_'+checkpoint] = True
        # Retirement has two recovery windows: RELEASE is confirmed but its
        # record remains, or FORGET succeeded but local flags/state remain.
        for checkpoint, expected_query in (('released-confirmed', 0), ('forgotten-confirmed', -2)):
            with (OUT / f'manager-checkpoint-{checkpoint}.log').open('w') as stream:
                manager = subprocess.Popen([str(G.MANAGER), 'replace', str(path), str(plan), '--hold'],
                    stdout=stream, stderr=subprocess.STDOUT, env=dict(os.environ, VKSO_TEST_STOP_AT=checkpoint))
                try:
                    deadline = time.monotonic()+10
                    while not (ROOT / 'runtime/manager.pid').exists():
                        assert manager.poll() is None and time.monotonic()<deadline
                        time.sleep(.01)
                    manager.send_signal(signal.SIGTERM)
                    while True:
                        assert manager.poll() is None and time.monotonic()<deadline
                        status = Path(f'/proc/{manager.pid}/status').read_text()
                        if any(line.startswith('State:') and 'T' in line for line in status.splitlines()): break
                        time.sleep(.01)
                    state = (ROOT / 'runtime/manager.state').read_text()
                    (OUT / f'checkpoint-{checkpoint}.state').write_text(state)
                    tid = int(re.search(r'^transaction_id=(\d+)$', state, re.M)[1])
                    observed = client.rpc(QUERY, tid, expected=expected_query)
                    if expected_query == 0:
                        assert observed['state']==RESTORED and observed['applied']==0
                    checkpoint_refs = refs()
                    # The paused manager still owns its netlink socket. That
                    # socket pins the transport module independently of the
                    # released transaction and owner references.
                    assert original(path) and checkpoint_refs=={
                        owner_name: baseline[owner_name],
                        'page_cache_replace': baseline['page_cache_replace']+1}, checkpoint_refs
                    manager.kill(); manager.wait()
                    command([G.MANAGER, 'restore', path, plan], f'checkpoint-{checkpoint}-recovery')
                    after = client.rpc(QUERY, tid, expected=-2)
                    checks['checkpoint_'+checkpoint] = dict(transaction=tid, before_recovery=observed,
                        refs_while_manager_socket_open=checkpoint_refs, after_recovery=after)
                finally:
                    if manager.poll() is None: manager.kill(); manager.wait()
            assert original(path) and refs()==baseline and not (ROOT / 'runtime/manager.state').exists()
        command([G.MANAGER, 'replace', path, plan], 'forget-lost-ack-replace')
        state = (ROOT / 'runtime/manager.state').read_text()
        tid = int(re.search(r'^transaction_id=(\d+)$', state, re.M)[1])
        inject('test_drop_reply', FORGET)
        command([G.MANAGER, 'restore', path, plan], 'forget-lost-ack-restore')
        assert 'recovered_absence' in (OUT / 'forget-lost-ack-restore.log').read_text()
        checks['manager_lost_forget_ack'] = client.rpc(QUERY, tid, expected=-2)
        assert original(path) and refs()==baseline and not (ROOT / 'runtime/manager.state').exists()
        # Rejected BEGIN retains its exact result for QUERY after a lost ACK.
        writer = os.open(path, os.O_RDWR)
        inject('test_drop_reply', BEGIN)
        try:
            rc = command([G.MANAGER, 'replace', path, plan, '--hold'], 'manager-lost-rejected-begin', None)
            assert rc != 0
        finally: os.close(writer)
        log = (OUT / 'manager-lost-rejected-begin.log').read_text()
        assert 'recovered_reply' in log and 'status=-26' in log
        assert original(path) and refs() == baseline and not (ROOT / 'runtime/manager.state').exists()
        checks['lost_rejected_begin_ack'] = True
        # Preserve immutable when it belongs to the original file, including
        # recovery after COMMIT but before the manager published ready.
        fd = os.open(path, os.O_RDONLY)
        flags, = struct.unpack('I', fcntl.ioctl(fd, 0x80086601, struct.pack('I',0)))
        fcntl.ioctl(fd, 0x40086602, struct.pack('I', flags | 16))
        os.close(fd)
        command([G.MANAGER, 'replace', path, plan], 'preexisting-immutable-replace')
        command([G.MANAGER, 'restore', path, plan], 'preexisting-immutable-restore')
        fd = os.open(path, os.O_RDONLY)
        observed, = struct.unpack('I', fcntl.ioctl(fd, 0x80086601, struct.pack('I',0)))
        assert observed & 16
        fcntl.ioctl(fd, 0x40086602, struct.pack('I', flags)); os.close(fd)
        checks['preexisting_immutable_preserved'] = True
        # A manager restore failure is a nonzero exit with recovery identity;
        # a new manager can then release the remaining page and clear flags.
        with (OUT / 'manager-recovery-error.log').open('w') as stream:
            manager = subprocess.Popen([str(G.MANAGER), 'replace', str(path), str(plan), '--hold'], stdout=stream, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic()+10
                while not (ROOT / 'runtime/manager.pid').exists():
                    assert manager.poll() is None and time.monotonic() < deadline
                    time.sleep(.01)
                assert command([G.MANAGER, 'replace', path, plan], 'manager-runtime-conflict', None) != 0
                inject('test_fail_release', 0)
                manager.send_signal(signal.SIGTERM)
                assert manager.wait(timeout=10) != 0
                assert (ROOT / 'runtime/manager.state').exists() and not original(path)
                (OUT / 'failed-release-manager.state').write_text((ROOT / 'runtime/manager.state').read_text())
                command([G.MANAGER, 'restore', path, plan], 'manager-recovery-retry')
            finally:
                if manager.poll() is None: manager.kill(); manager.wait()
        assert original(path) and refs() == baseline and not (ROOT / 'runtime/manager.state').exists()
        checks['manager_failure_retains_state_and_retries'] = True
        # Every manager-created transaction, including wrapper and recovery
        # cases, must be absent after its final successful cleanup.
        manager_ids = set()
        for log in OUT.rglob('*.log'):
            manager_ids.update(int(tid) for tid in re.findall(
                r'^VKSO_TRANSACTION id=(\d+) operation=1\b', log.read_text(), re.M))
        assert manager_ids
        checks['manager_terminal_records_absent'] = [client.rpc(QUERY, tid, expected=-2)
                                                     for tid in sorted(manager_ids)]
        client.fd.close()
        assert refs() == {owner_name: 0, 'page_cache_replace': 0}
        for name in (owner_name, 'vkso_kernel_reader', 'page_cache_replace'):
            command(['rmmod', name], 'unload-'+name)
        record.update(status='pass', protocol_sizes=dict(request=C.sizeof(Request), result=C.sizeof(Result)),
                      modules_after=Path('/proc/modules').read_text())
    except BaseException as error:
        record.update(status='fail', error=repr(error)); raise
    finally:
        (OUT / 'dmesg.txt').write_text(subprocess.check_output(['dmesg'], text=True))
        (OUT / 'status.json').write_text(json.dumps(record, indent=2)+'\n')

if __name__ == '__main__': main()
