#!/usr/bin/env python3
"""Build tables and interface coverage from the frozen evidence inputs."""
import argparse
import csv
import json
from collections import defaultdict
from audit_current import OUT, REPO, csv_text


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |'] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows]) + '\n'


def build():
    src = json.loads((OUT / 'source-totals.json').read_text())
    rows = src['rows']
    counts = {(r['system'], r['scope'], r['category']): r['sloc'] for r in rows}
    categories = [('user_computation', '用户读取计算切片'), ('kernel_computation', '普通内核读取实现（含原入口）'),
                  ('shared_computation', '共享读取计算与协议'), ('data_abi', '数据 ABI 与布局断言'),
                  ('user_adapter_provider', '用户适配、初始化及用户 provider/fallback'),
                  ('kernel_adapter', '内核适配及 syscall 边界'), ('publisher', '状态发布'),
                  ('mapping_namespace', '映射与 namespace'), ('provider_integration', 'provider 接入'),
                  ('integration', '其余运行接入声明'), ('build', '构建与链接'), ('getcpu', 'getcpu 专属实现与适配')]
    out = '# 工作 1、2：数值表\n\n所有主表值来自同目录 CSV/JSON；单位和范围见 README.md。\n\n## 同功能源码职责切片\n\n'
    values = [[label, counts.get(('Raw','feature',key),0), counts.get(('VKSO','feature',key),0)] for key,label in categories]
    total = src['totals']
    values += [['时间及共用接入小计（去除 getcpu 专属行）', *[total[s]['feature']-counts[s,'feature','getcpu'] for s in ['Raw','VKSO']]],
               ['功能切片合计', total['Raw']['feature'], total['VKSO']['feature']],
               ['保留读取/分派切片（另列）', total['Raw']['retained'], total['VKSO']['retained']],
               ['功能 + 上述保留切片', *[total[s]['feature']+total[s]['retained'] for s in ['Raw','VKSO']]],
               ['共同数学/provider 契约切片（另列）', total['Raw']['common'], total['VKSO']['common']],
               ['通用构建/注册设施（完整列入的文件，另列）', total['Raw']['infrastructure'], total['VKSO']['infrastructure']]]
    out += table(['职责（非空非注释物理源码行）','Raw','VKSO'],values)
    out += '\n普通 Raw 内核函数混合计算与返回 ABI，不能把第一至第三行直接换算成纯算法缩减率。功能合计以共同 Linux/libc 设施为边界；新增公开库、初始化和完整用户头文件均计入 VKSO。最后一行是实际复用设施的文件规模，不按本案例虚构摊销比例；不是整套工具链总量。\n'
    symbols=list(csv.DictReader((OUT/'binary-symbols.csv').open()))
    sections=list(csv.DictReader((OUT/'binary-sections.csv').open()))
    ordinary={'ktime_get_real_ts64','ktime_get','ktime_get_resolution_ns','ktime_get_with_offset','ktime_get_raw','ktime_get_ts64','ktime_get_seconds','ktime_get_real_seconds','ktime_get_raw_ts64','ktime_get_coarse_real_ts64','ktime_get_coarse_ts64'}
    binaries=[]
    def unique_size(rs):
        seen={}
        for r in rs:
            key=r['artifact'],r['address'];seen[key]=max(seen.get(key,0),int(r['bytes']))
        return sum(seen.values())
    for variant in ['normal','no-retpoline']:
        s=[r for r in symbols if r['variant']==variant]
        q=[r for r in sections if r['variant']==variant]
        def put(metric,system,rs,scope):binaries.append(dict(variant=variant,system=system,metric=metric,bytes=unique_size(rs),scope=scope))
        for system in ['Raw','VKSO']:
            put('11 ordinary kernel entry extents',system,[r for r in s if r['system']==system and r['artifact']=='kernel' and r['symbol'] in ordinary],'kallsyms extents including padding; shared callees separate')
        put('native time/getcpu vDSO symbols','Raw',[r for r in s if r['artifact']=='embedded-vdso' and r['scope']=='feature'],'ELF st_size; SGX excluded')
        put('shared time/getcpu function bodies','VKSO',[r for r in s if r['artifact']=='kernel-shared-core'],'ELF st_size; alignment and general thunk page separate')
        for artifact,section in [('embedded-vdso','.text'),('direct/libvkso_time.so','.text')]:
            for r in q:
                if r['artifact']==artifact and r['section']==section:
                    binaries.append(dict(variant=variant,system=r['system'],metric=artifact+' .text',bytes=int(r['bytes']),scope=r['scope']))
        for scope in ['shared backing: count once with kernel','user private']:
            group=[r for r in q if r['artifact']=='libkernel.so' and r['scope']==scope and r['section'].startswith('.text')]
            binaries.append(dict(variant=variant,system='VKSO',metric='carrier '+scope+' executable sections',bytes=sum(int(r['bytes']) for r in group),scope='reserved page bytes, not function body bytes'))
    out+='\n## 实际 clean 实验包二进制\n\n'+table(['配置','方案','项目','字节','口径'],[[r[k] for k in ['variant','system','metric','bytes','scope']] for r in binaries])
    out+='\n这些行是相互重叠的视图，不相加为总体内存：共享函数体属于共享代码页，carrier 的相应页与内核具有相同 backing。内核入口 extent 包含对齐，ELF symbol size 不含函数间对齐。完整段、符号和设施计量分别保存在 binary-sections.csv、binary-symbols.csv。\n'
    boots=list(csv.DictReader((OUT/'mechanism-boots.csv').open()))
    out+='\n## 正式裸机机制验证\n\n'+table(['配置','独立启动','每次 text 共享页','每次 data 共享页','API / 选定快路径 / ABI及namespace / PFN'],[[v,len([r for r in boots if r['variant']==v]),boots[[r['variant'] for r in boots].index(v)]['text_pages'],1,'全部通过'] for v in ['normal','no-retpoline']])
    resources=list(csv.DictReader((OUT/'resource-pages.csv').open()))
    groups=defaultdict(list)
    for r in resources:groups[r['variant'],r['system'],r['processes'],r['kind']].append(int(r['unique_recorded_pfns']))
    out+='\n## 多进程记录到的唯一物理页\n\n'+table(['配置','方案','进程数','映射类别','四次启动 min–max'],[[*k,f'{min(v)}–{max(v)}'] for k,v in sorted(groups.items(),key=lambda kv:(kv[0][0],kv[0][1],int(kv[0][2]),kv[0][3]))])
    out+='\n这是采集器在所列映射中记录到的 PFN，并非总内存。Raw vvar 记录为 0 个 present PFN，不能解释为没有状态页。Raw vDSO 在多进程间本来就共享；VKSO 的物理证据是额外跨用户/内核的页身份一致。\n'
    # Interface coverage distinguishes shared code execution from shared state reads.
    interfaces=[]
    def add(domain,interface,mode,path,namespace,evidence):
        interfaces.append(dict(domain=domain,interface=interface,mode=mode,path=path,namespace=namespace,evidence=evidence))
    for name in ['realtime','monotonic','monotonic_raw','boottime','tai','realtime_coarse','monotonic_coarse']:
        kind='coarse' if name.endswith('coarse') else 'hres'
        add('user','clock_gettime('+name+')','shared_code','clock_gettime -> __vkso_clock_gettime -> vkso_clock_gettime_'+kind,'MM_data; offset only for masked namespace clocks','8 boots: check.log + legacy-abi.log; actual carrier transfers in binary-user-transfers.csv')
    for name,path in [('clock_getres(shared clocks)','__vkso_clock_getres -> vkso_clock_getres_hres/coarse'),('gettimeofday','IFUNC -> __vkso_gettimeofday -> vkso_gettimeofday_core'),('time','IFUNC -> __vkso_time'),('getcpu','getcpu -> __vkso_getcpu')]:
        add('user',name,'shared_code',path,'ABI-specific; realtime/time not namespace-offset clocks','8 boots: public API and ABI checks; selected denial scope in check-fast.log')
    for name in sorted(ordinary):
        direct=name in ['ktime_get_resolution_ns','ktime_get_seconds','ktime_get_real_seconds']
        kind='coarse' if 'coarse' in name else 'hres'
        add('kernel',name,'shared_state_only' if direct else 'shared_code',
            'root scalar adapter -> shared state scalar' if direct else 'root adapter -> vkso_clock_gettime_'+kind,
            'root semantics; NULL MM_data', 'current source; exact compiled transfers for 4 representatives; host contract for tested callers')
    add('kernel syscall','clock_gettime/getres(shared clocks)','shared_code','POSIX dispatch -> shared hres/coarse entries','current MM_data','current source; 8-boot syscall/namespace ABI checks')
    add('both','native clock IDs / provider failure','domain_fallback','user syscall; kernel native k_clock or vkso_timekeeping_get_private','offset applied once by the completing path','8-boot native-ID checks; host contract for provider failure; no bare-metal PV/HV claim')
    for name in ['ktime_get_mono_fast_ns','ktime_get_raw_fast_ns','ktime_get_boot_fast_ns','ktime_get_real_fast_ns','ktime_get_coarse_with_offset','ktime_get_snapshot','ktime_get_update_offsets_now']:
        add('kernel',name,'private_retained','private timekeeper / fast-timekeeper path','original kernel contract','source-only classification; not claimed shared')
    return {'tables.md':out,'binary-summary.csv':csv_text(binaries,list(binaries[0])),
            'interfaces.csv':csv_text(interfaces,list(interfaces[0]))}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args()
    for name,data in build().items():
        path=OUT/name
        if args.check:assert path.read_text()==data,'stale report: '+name
        else:path.write_text(data)
    print('report_check=PASS' if args.check else 'report_written=PASS')


if __name__=='__main__':main()
