#!/usr/bin/env python3
"""Extract actual READ-package entry instructions and map every measured API."""
import argparse
import csv
import json
import re
import subprocess
from pathlib import Path
from read_evaluation import BARE, OUT, ROOT, VARIANTS, CASE_NAMES, KERNEL_APIS, csv_text


def disassemble(path, names):
    full=subprocess.check_output(['objdump','-drwC',str(path)],text=True)
    found={}
    for m in re.finditer(r'^([0-9a-f]+) <([^>]+)>:\n(.*?)(?=\n[0-9a-f]+ <|\Z)',full,re.M|re.S):
        if m[2] in names: found[m[2]]=m.group(0).strip()
    if set(names)-found.keys():raise ValueError((path,set(names)-found.keys()))
    return found


def produce():
    chunks=[]
    for variant in VARIANTS:
        package=BARE/'artifacts'/('clocktime-auto-53f692884c64-clean-'+variant)
        sets=[('direct/libvkso_time.so',['clock_gettime','clock_getres','getcpu','resolve_time','resolve_gettimeofday']),
              ('libkernel.so',['__vkso_clock_gettime','__vkso_clock_getres','__vkso_gettimeofday','__vkso_time','__vkso_getcpu','vkso_clock_gettime_hres','vkso_clock_gettime_coarse']),
              ('raw-kernel-reader.ko',['run_batch','measure_on_cpu']),('vkso-kernel-reader.ko',['run_batch','measure_on_cpu'])]
        for artifact,names in sets:
            ds=disassemble(package/artifact,names)
            if 'kernel-reader' in artifact:
                for target in ['ktime_get_ts64','ktime_get_raw_ts64','ktime_get_coarse_ts64']:
                    assert target in ds['run_batch'],target
            if artifact=='libkernel.so':
                assert 'syscall' in ds['__vkso_clock_gettime']
                assert 'vkso_clock_gettime_hres' in ds['__vkso_clock_gettime']
                assert 'vkso_clock_gettime_coarse' in ds['__vkso_clock_gettime']
                assert 'vkso_gettimeofday_core' in ds['__vkso_gettimeofday']
            for symbol,body in ds.items():
                chunks.append(f'## {variant}: {artifact}: {symbol}\n\n```asm\n{body}\n```\n')
        syms=subprocess.check_output(['readelf','-Ws',str(package/'direct/libvkso_time.so')],text=True)
        for name in ['time','gettimeofday']:
            assert re.search(r'IFUNC\s+GLOBAL[^\n]*\s'+name+r'\s*$',syms,re.M)
        chunks.append('## '+variant+': public IFUNC binding\n\n```text\n'+'\n'.join(x for x in syms.splitlines() if 'IFUNC' in x)+'\n```\n')
    paths=[]
    for api in CASE_NAMES:
        if api in CASE_NAMES[:5]:
            raw='libc clock_gettime -> native vDSO do_hres -> vvar/cycle conversion'
            vkso='public clock_gettime -> carrier clock-ID classification + MM_data/context -> shared vkso_clock_gettime_hres'
            reason='同一共享转换核心；clock ID 的基址选择与 namespace 分支不同，逐时钟报告实测成本。'
        elif api in CASE_NAMES[5:7]:
            raw='libc clock_gettime -> native vDSO do_coarse -> vvar snapshot'
            vkso='public clock_gettime -> carrier classification + MM_data -> shared vkso_clock_gettime_coarse'
            reason='两侧均读取 coarse 快照；VKSO 保留入口分类与 MM_data 注入，短路径需同时报告绝对差和百分比。'
        elif api in CASE_NAMES[7:9]:
            raw='libc clock_getres -> native vDSO clock_getres'
            vkso='public clock_getres -> carrier classification -> shared vkso_clock_getres_hres/coarse'
            reason='hres 读取已发布分辨率，coarse 返回 LOW_RES_NSEC；不执行周期转换。'
        elif api=='gettimeofday_tv':
            raw='libc gettimeofday -> native vDSO gettimeofday'
            vkso='public IFUNC resolved before timing -> carrier __vkso_gettimeofday -> shared vkso_gettimeofday_core'
            reason='IFUNC 将稳定调用直接绑定 carrier；共享核心完成时间读取和微秒转换。'
        elif api.startswith('time_'):
            raw='libc time -> native vDSO time'
            vkso='public IFUNC resolved before timing -> shared __vkso_time'
            reason='直接读取共享秒值，time_pointer 另写输出指针；两个工作负载分别计量。'
        elif api=='getcpu_both':
            raw='libc getcpu -> native vDSO getcpu'
            vkso='public getcpu -> shared __vkso_getcpu'
            reason='属于 getcpu 共享功能，读取 CPU/node；不属于时间周期换算。'
        else:
            call='clock_getres' if api.startswith('clock_getres') else 'clock_gettime'
            raw=f'libc {call} -> native fallback -> syscall'
            vkso=f'public {call} -> carrier native-clock branch -> syscall'
            reason='这些 clock ID 在入口分类后直接进入 syscall，测得完整 fallback 路径，不能归为共享读取核心加速。'
        paths.append(dict(domain='user',api=api,raw_path=raw,vkso_path=vkso,interpretation=reason,
                          evidence='entry-disassembly.md; direct-api/vkso_public.c; functional/vkso_user_entry.S; code-size/current-evidence/source-lines.csv'))
    for api,func,core in zip(KERNEL_APIS,['ktime_get_ts64','ktime_get_raw_ts64','ktime_get_coarse_ts64'],['vkso_clock_gettime_hres','vkso_clock_gettime_hres','vkso_clock_gettime_coarse']):
        paths.append(dict(domain='kernel',api=api,raw_path=f'run_batch -> {func} -> native timekeeper reader',
                          vkso_path=f'run_batch -> {func} -> root adapter (NULL MM_data) -> {core}',
                          interpretation='普通内核导出接口直接调用，输出 timespec64；两侧均包含循环和校验累加成本。配置组内分别比较。',
                          evidence='entry-disassembly.md; code-size/current-evidence/binary-user-transfers.csv; revision/kernel-reader/vkso_kernel_reader.c'))
    return {'entry-disassembly.md':'# Actual clean READ package instructions\n\n'+ '\n'.join(chunks), 'call-paths.csv':csv_text(paths)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    for name,s in produce().items():
        if a.check:assert (OUT/name).read_bytes()==s.encode(),name
        else:(OUT/name).write_bytes(s.encode())
    print('READ paths: PASS; 19 API workloads and two actual package variants')
