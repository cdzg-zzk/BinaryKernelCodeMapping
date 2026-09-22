#!/usr/bin/env python3
"""Write the repetition/PMU findings directly from their retained summaries."""
import csv,json,statistics as st
from pathlib import Path
import argparse

def rows(p):return list(csv.DictReader(p.open()))
def build(base):
    data=rows(base/'analysis/summary.csv');lookup={(r['algorithm'],r['domain'],r['workload'],r['target'],r['baseline']):r for r in data}
    def record(domain,t,e,mode='decode-precomputed',middle=False):
        return lookup['bch',domain,f'm=13/t={t}/bytes=512/errors={e}/{mode}',
            'kernel-vkso' if domain=='user' else 'owner-kernel',
            ('adapted-dso' if middle else 'native-dso') if domain=='user' else ('matched-kernel' if middle else 'stock-kernel')]
    def cell(r):return ' / '.join(f"{100*(float(r[k])-1):+.2f}%" for k in ('median_cost_ratio','minimum_deployment_ratio','maximum_deployment_ratio'))
    user=rows(base/'repeat-bch/user-pmu/load-summary.csv');kernel=rows(base/'repeat-bch/pmu/phase-summary.csv')
    def metrics(domain,t,e,backend):
        g=[r for r in (user if domain=='user' else kernel) if r['t']==str(t) and r['errors']==str(e) and r['mode']=='decode-precomputed' and r['backend']==backend]
        assert len(g)==(3 if domain=='user' else 9)
        return {k:st.median(float(r[k]) for r in g) for k in ('ns','cycles','instructions','branch_misses','l1d_read_misses')}
    facts={domain:{f't{t}-e{e}':{backend:metrics(domain,t,e,backend) for backend in backends} for t,e in ((4,0),(4,2),(8,2),(8,8))}
        for domain,backends in [('user',('native-dso','adapted-dso','kernel-vkso')),('kernel',('stock-kernel','matched-source-kernel','owner-kernel'))]}
    (base/'repeat-bch/pmu-facts.json').write_text(json.dumps(facts,indent=2)+'\n')
    text='''# BCH 重复测量与原因分析

状态：采集和分析完成。新增九次完整两端部署，连同原三次，共十二次。
Owner、Matched、Native/Adapted DSO、正式 benchmark 二进制及输入协议均未改变。
所有完整部署保留，原始三次与新增九次还在 [cohort-summary.csv](cohort-summary.csv)
中分别统计。LZ4/XZ 保留各三次部署。

## 重测后的主要结论

以下依次为十二次部署的配对中位变化、最小值、最大值；不是置信区间。

| 执行域 / 比较 | 路径 | 中位 / 最小 / 最大 |
| --- | --- | --- |
'''
    for domain,t,e,middle in [('user',4,2,False),('user',8,2,False),('user',8,8,False),('kernel',4,0,True),('kernel',4,2,True),('kernel',8,2,True),('kernel',4,2,False),('kernel',8,2,False),('kernel',8,8,False)]:
        comparison='VKSO/Native' if domain=='user' else 'Owner/Matched' if middle else 'Owner/Stock'
        text+=f'| {domain}，{comparison} | t={t}，{e} 错误 precomputed | {cell(record(domain,t,e,middle=middle))} |\n'
    text+='''
两错误用户收益与八错误用户退化都在新增重复中保留。零错误内核路径的
Owner/Matched 中位数改变方向，但完整范围仍跨零，不能将原三次的负中位数
解读成固定收益。新增重复提高了对分布的认识，没有使所有路径“变稳定”。

原三次与新增九次的 t=4 两错误用户中位变化分别约为 −8.02% 和 −8.64%；
t=8 分别为 −10.23% 和 −9.94%。这支持主结果的方向。原三次的波动样本仍在
十二次范围内，没有按速度删掉或重采。

## 性能差异：已有因果对照与新增执行证据

BCH 已采用的 syndrome 循环显式缓存 `a_pow_tab` 并推进输出指针。原始内核
构建在内循环重新读取表指针，原始普通用户构建将其提升到循环外；单独关闭
用户编译的 strict-alias 分析重现了循环内读取。已有 loop-only 对照给出
2.36%（t=4）和 4.10%（t=8）的两错误内核收益。这是源码表达与编译条件交互的
直接证据，但不是 Owner 全部收益的分解。已有 helper-only 对照同样保留。

新增用户 PMU 使用真实 carrier 和不变的三种算法二进制，只给 benchmark 增加
批次外计数器读取。三个诊断部署均完成 128 向量/参数的正确性矩阵和全部
0..t 错误数测量，输入与正式数据逐项相同。以下指令数和分支失误是各诊断
部署内中位数再取中位数，均按完整操作归一化：

| 路径 | Native 指令 | Adapted 指令 | VKSO 指令 | Native 分支失误 | VKSO 分支失误 |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
    for t,e in ((4,2),(8,2),(8,8)):
        g=facts['user'][f't{t}-e{e}'];n,a,v=(g[b] for b in ('native-dso','adapted-dso','kernel-vkso'))
        text+=f"| t={t}，{e} 错误 | {n['instructions']:,.0f} | {a['instructions']:,.0f} | {v['instructions']:,.0f} | {n['branch_misses']:.2f} | {v['branch_misses']:.2f} |\n"
    text+='''
两错误时，源码缓存和不同生成代码共同减少实际执行指令；这与用户端主要收益
方向一致。八错误时，VKSO 相对 Native 反而执行更多指令并发生更多分支失误。
Linux `find_poly_roots()` 对 1–4 阶使用专门求根程序，更高阶进入多项式分解
及递归求根。因此错误数改变了工作在代码路径之间的分布，局部 syndrome
优化不能保证完整解码始终更快。这里的 PMU 支持执行工作量与控制流解释，
不把指令数和分支失误乘固定单价来声称精确分解全部耗时。

内核的分母不同。八错误时，诊断阶段的 Stock/Matched/Owner 指令数约为
40,577 / 39,248 / 38,038。Owner 相对 Stock 执行更少指令，用户 VKSO 相对
Native 则执行更多指令；两端相反的性能方向有实际执行证据支持，并非同一个
固定 PGOT 成本发生正负翻转。Matched 与 Stock 的差异还包含机制所需代码生成
条件、模块构建与布局，不能全部归为源码缓存收益。

### 控制上下文与不稳定性

三次独立内核诊断各保留六个已分配上下文。在同一次装载内，Stock/Matched/Owner
循环交换这些上下文，完成三个全量正确性与计时阶段。检查确认每个控制对象及
其 pow/log 表、ECC、syndrome、elp、输入和差值缓冲区地址保持不变，并恰好被
三个实现各使用一次。每次装载的初始轮换位置不同，平衡阶段顺序。

对相同上下文和错误位置配对后，两错误 Owner/Matched 的 cycles 变化在三个
装载中分别为 t=4：−2.93%、−3.36%、−3.42%；t=8：−13.54%、−12.08%、−12.67%。
因此两错误收益在同一批数据对象上仍存在，不能解释成 Owner 恰巧分到了更快的
上下文。这是独立诊断的 cycles 比较，不替换正式时间表。

零错误短路径仍没有得到唯一的微架构归因。十二次正式部署的十二个 BCH API
入口地址分别始终相同，排除了入口虚拟地址变化的解释。PMU/上下文轮换中，
Matched 的指令数约 378/次、分支失误约 1/次，L1D read misses 约 0.001/次，
cycles/ref-cycles 比率约 0.99656，均较稳定；阶段时延仍在约 81.5–87.8 ns
之间变化。这些计数器没有支持“执行更多工作”“L1D 容量失效”或频率变化的
归因。代码地址相同也不代表全部缓存或前端状态相同，后者本轮没有被独立测定。

论文不将零错误的某个负中位数作为加速主张，而是保留十二次范围，并解释
有稳定方向且具备执行证据的两错误/八错误结果。此处停止追查，不追加试验
直到出现想要的中位数。

## 证据位置与处理记录

- [完整当前统计](../analysis/summary.csv)，[逐部署统计](../analysis/deployment-ratios.csv)。
- [原三次/新增九次](cohort-summary.csv)，[全部 API 地址](entry-addresses.csv)。
- [内核 PMU 阶段统计](pmu/phase-summary.csv)、[同上下文配对](pmu/same-context-pairs.csv)、[地址交叉核验](pmu/context-addresses.csv)。
- [用户 PMU 统计](user-pmu/load-summary.csv)、[机器可读解释数值](pmu-facts.json)。
- 各诊断子目录保留源文件、编译产物、计数器运行时间、完整向量、输入与载入/卸载日志。

内核 PMU 共 9,504 个完整操作记录、47,520 个事件记录，来自三次装载的九个
阶段；用户 PMU 共 3,168 个操作记录、15,840 个事件记录，来自三次注册部署。
所有硬件事件检查 enabled/running，未使用 multiplex 后估算的值。插桩计时
不加入正式的十二次 BCH 样本。

首个新增尝试在完成用户测量后，内核收集器因继承 CPU 0 亲和性而在计时前
拒绝运行。映射已恢复，记录保存在 `pre-kernel-affinity-failure/`，修正启动器
亲和性后完成固定的九次完整部署。这不是因性能不利而剔除样本。
'''
    (base/'repeat-bch/findings.md').write_text(text)
    print('Repetition and cause report generated.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();build(a.directory.resolve())
