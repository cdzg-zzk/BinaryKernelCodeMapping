#!/usr/bin/env python3
"""Live shared-page census plus namespace switch and reference-lifetime checks."""
import ctypes
import json
import os
from pathlib import Path
import struct
import sys

from memory_probe import LIBC, group, page

TIME_NS = 0x80
LIBC.setns.argtypes = [ctypes.c_int, ctypes.c_int]


def drain_lazy_mm():
    # Idle CPUs may retain an exited task's active_mm until their next switch.
    allowed = os.sched_getaffinity(0)
    try:
        for cpu in sorted(allowed):
            os.sched_setaffinity(0, {cpu})
    finally:
        os.sched_setaffinity(0, allowed)


def join(fd):
    assert LIBC.setns(fd, TIME_NS) == 0, ctypes.get_errno()


def create(mono, boot):
    assert LIBC.unshare(TIME_NS) == 0, ctypes.get_errno()
    Path('/proc/self/timens_offsets').write_text(f'monotonic {mono} 456\nboottime {boot} 123\n')
    return os.open('/proc/self/ns/time_for_children', os.O_RDONLY)


def refs():
    pfn, count, maps = map(int, Path('/sys/kernel/debug/vkso_mm_refs').read_text().split())
    return dict(pfn=pfn, refs=count, maps=maps)


def backing_refs(pfn):
    control=Path('/sys/module/page_refs/parameters/pfn')
    control.write_text(str(pfn))
    try:return refs()
    finally:control.write_text('0')


def concurrent_first_join():
    fd=create(222,333)
    root=os.open('/proc/self/ns/time',os.O_RDONLY)
    join(root);os.close(root)  # Children start in root; first entry races at the gate.
    gate_r,gate_w=os.pipe();result_r,result_w=os.pipe();hold_r,hold_w=os.pipe()
    children=[]
    for i in range(16):
        pid=os.fork()
        if not pid:
            try:
                os.close(gate_w);os.close(result_r);os.close(hold_w)
                assert os.read(gate_r,1)==b'x'
                join(fd)
                observed=page(LIBC.getauxval(52))
                values=struct.unpack_from('<qQqQ',bytes.fromhex(observed['bytes']),8)
                assert values==(222,456,333,123)
                os.write(result_w,struct.pack('<Q',observed['pfn']))
                os.read(hold_r,1)
                os._exit(0)
            except BaseException:os._exit(1)
        children.append(pid)
    os.close(gate_r);os.close(result_w);os.close(hold_r)
    os.write(gate_w,b'x'*16);os.close(gate_w)
    result=b''
    while len(result)<128:
        chunk=os.read(result_r,128-len(result));assert chunk;result+=chunk
    pfns=list(struct.unpack('<16Q',result));assert len(set(pfns))==1
    live=backing_refs(pfns[0]);assert live['refs']==33 and live['maps']==16,live
    os.write(hold_w,b'x'*16);os.close(hold_w);os.close(result_r)
    for pid in children:assert os.waitpid(pid,0)[1]==0
    drain_lazy_mm()
    idle=backing_refs(pfns[0]);assert idle['refs']==1 and idle['maps']==0,idle
    root=os.open('/proc/self/ns/time',os.O_RDONLY)
    join(root);os.close(root);os.close(fd)
    return dict(children=16,pfns=pfns,live=live,after_exit=idle)


def lifecycle():
    address = LIBC.getauxval(52)
    root = os.open('/proc/self/ns/time', os.O_RDONLY)
    lib = ctypes.CDLL('/work/package/libkernel.so')
    bind = lib.__vkso_bind_context
    bind.argtypes = [ctypes.c_void_p]*3
    assert bind(address, None, None) == 0
    clock = lib.__vkso_clock_gettime
    output = (ctypes.c_int64*2)()
    base = page(address)
    a = create(123, 789)
    join(a)
    first = page(address)
    assert first['pfn'] != base['pfn']
    assert struct.unpack_from('<qQqQ', bytes.fromhex(first['bytes']), 8) == (123,456,789,123)
    before = refs()
    assert before['pfn'] == first['pfn'] and before['refs'] == 3 and before['maps'] == 1
    ask_r, ask_w = os.pipe()
    answer_r, answer_w = os.pipe()
    child = os.fork()
    if not child:
        os.close(ask_w); os.close(answer_r)
        try:
            while os.read(ask_r,1):
                observed = page(address)
                assert observed == first
                assert clock(1, output) == 0
                os.write(answer_w,b'y')
            os._exit(0)
        except BaseException:
            os._exit(1)
    os.close(ask_r); os.close(answer_w)
    b = create(-1, 999)
    join(b)
    second = page(address)
    assert second['pfn'] not in (base['pfn'], first['pfn'])
    observed = []
    for iteration in range(30):
        for fd, expected in [(root,base),(a,first),(b,second)]:
            join(fd)
            assert page(address) == expected  # same VA and new content/PFN
            for cid in (1,4,6,7):
                before_time, after_time = (ctypes.c_int64*2)(),(ctypes.c_int64*2)()
                assert LIBC.syscall(228,cid,ctypes.byref(before_time)) == 0
                assert clock(cid,output) == 0
                assert LIBC.syscall(228,cid,ctypes.byref(after_time)) == 0
                assert tuple(before_time) <= tuple(output) <= tuple(after_time)
            os.write(ask_w,b'x')
            assert os.read(answer_r,1) == b'y'
        observed.append(refs())
    os.close(ask_w); os.close(answer_r)
    assert os.waitpid(child,0)[1] == 0
    drain_lazy_mm()
    join(a)
    page(address)
    after = refs()
    assert before == after, (before,after)
    join(root)
    assert page(address) == base
    os.close(a);os.close(b)
    # Repeated namespace creation/destruction must not retain mm/PTE references.
    root_refs = refs()
    cycles=[]
    for i in range(100):
        fd = create(i, i+1)
        join(fd)
        page(address)
        record = refs()
        assert record['refs'] == 3 and record['maps'] == 1
        join(root)
        page(address)
        idle=backing_refs(record['pfn'])
        assert idle['refs']==1 and idle['maps']==0
        os.close(fd)
        assert refs() == root_refs
        cycles.append(dict(active=record,after_leave=idle))
    os.close(root)
    return dict(switches=90, sibling_checks=90, clocks_per_switch=4,
                address_unchanged=address, before=before, after=after,
                namespace_b_refs=observed, create_destroy_cycles=cycles,
                root_refs=root_refs)


def main():
    output=Path('/work/results')
    report={'groups':[]}
    report['groups'].append(group(32,'fork',False,1))
    for count in (1,8,32):
        report['groups'].append(group(count,'exec',True,1))
    drain_lazy_mm()
    report['lifecycle']=lifecycle()
    report['concurrent_join']=concurrent_first_join()
    root=os.open('/proc/self/ns/time',os.O_RDONLY)
    a=create(123,789)
    join(a)
    report['groups'].append(group(8,'exec',True,1))
    assert report['groups'][-1]['records'][0]['mm']['pfn'] != report['groups'][1]['records'][0]['mm']['pfn']
    join(root);os.close(a);os.close(root)
    (output/'sharing.json').write_text(json.dumps(report,indent=2)+'\n')
    print('namespace_sharing_probe=pass',flush=True)


if __name__=='__main__': main()
