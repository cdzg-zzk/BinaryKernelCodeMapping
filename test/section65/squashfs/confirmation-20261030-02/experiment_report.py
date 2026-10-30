#!/usr/bin/env python3
"""Generate a traceable experiment report without changing the manuscript."""
import argparse,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
RUNS=Path('/var/tmp/vkso-section65-optimization-20261030-hBcg9Y')
def read(p):return json.loads(p.read_text())
def one(rows,**keys):
    a=[r for r in rows if all(r.get(k)==v for k,v in keys.items())];assert len(a)==1,(keys,len(a));return a[0]
def pct(v):return f'{100*(v-1):+.2f}%'
def effect(r):return pct(r['time_ratio'])+' ['+', '.join(pct(v) for v in r['ratio_ci95'])+']'
def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);a=p.parse_args();out=a.analysis.resolve()
    data=read(out/'analysis.json');audit=read(out/'audit.json');mem=read(out/'resource-ledger/resources.json');cost=read(out/'costs.json');reuse=read(out/'reuse-audit/result.json')
    assert data['status']==audit['status']==mem['status']=='complete'
    assert data['observations']==audit['observations']==8172 and len(data['inputs'])==30
    assert audit['interrupted_partial_observations']==790
    rows=data['results'];absolute=data['absolute'];lines=[]
    def add(s=''):lines.append(s)
    def table(selected):
        add('| 场景 / 格式 / 任务 / 状态 | 对照 → 测试 | 对照秒 | 测试秒 | 配对耗时变化 [95% CI] | 配对数 / campaign 数 |')
        add('| --- | --- | ---: | ---: | ---: | ---: |')
        for r in selected:
            k={key:r[key] for key in ['kind','codec','workload','phase']}
            b=one(absolute,**k,variant=r['baseline']);t=one(absolute,**k,variant=r['treatment'])
            add('| '+ ' / '.join(k.values())+' | '+r['baseline']+' → '+r['treatment']+f" | {b['mean_campaign_median_seconds']:.4f} | {t['mean_campaign_median_seconds']:.4f} | {effect(r)} | {r['pairs']} / 3 |")
        add()
    add('# Section 6.5 优化与完整实验报告');add()
    add('本报告交付实验、分析和原始证据。按用户最新要求，不更新论文正文、不生成图片。现有论文/PDF仍是先前版本，不代表本轮结果。');add()
    add('## 1. 研究问题与版本');add()
    add('验证复杂 SquashFS 公共核心能否同时服务真实 native 与 Apptainer/SIF 用户消费者，保持私有对象/缓存，并以合理的适配、执行和部署成本实现跨域物理复用。三类对照分别回答：原生准备成本、同代码 copied/shared 的共享增量、相对 SquashFUSE/LKL 的完整应用表现。');add()
    add('公共核心不仅是解码器：还包含 SquashFS 的 superblock、目录、inode、block list、元数据及数据访问逻辑，以及公共 LZ4/XZ。native consumer 保留 VFS、内核 page cache、同步和 BIO 环境；用户桥提供私有对象、缓存、分配和用户 I/O，并经 FUSE helper 接入真实 Apptainer/SIF。其余 codec 由两侧服务绑定提供。这是声明的复用边界，并非把完整 VFS 或整个内核带入用户域。');add()
    add('选定版本为现有标量字典 word-copy XZ 核心，加 2048/4096 inode/name LRU 和 48 槽惰性数据缓存（128 KiB 块时最多请求 6 MiB 数据缓冲）。metadata/fragment 缓存仍为 8/3 槽。owner 与 native consumer 字节不变；前端/translator 的运行段内容和地址不变，重建后的 build ID 和调试信息不同。copied/shared 使用完全相同的最终前端、桥和核心指令。');add()
    add('16 槽候选的 Python 改善伴随 LZ4 stream 回退；按文件大小使用单个缓冲区的候选未保住 Python 收益，也未消除 LZ4 回退，因此均未采用。48 槽候选经过预先限定的 16/48 比较后选定，额外内存成本计入结果。bit-tree 解码候选仅完成诊断/构建，未进入正式版本。详见 SELECTION.md、CACHE_PROTOCOL.md 和保留的全部 pilot。');add()
    add('本轮关键数值（全部对照详见后续表和 summary.csv）：');add()
    for label,query in [
        ('Python/XZ：VKSO 对 stock',dict(kind='heldout',codec='xz',workload='compile',baseline='stock',treatment='vkso')),
        ('Python/XZ：48 槽 copied 对旧一槽 copied',dict(kind='heldout',codec='xz',workload='compile',baseline='copied-small',treatment='copied')),
        ('XZ 顺序任务：VKSO 对 stock',dict(kind='application-final',codec='xz',workload='stream',baseline='stock',treatment='vkso')),
        ('LZ4 顺序任务：48 槽 copied 对旧一槽 copied',dict(kind='application-final',codec='lz4',workload='stream',baseline='copied-small',treatment='copied')),
        ('LZ4 顺序任务：VKSO 对同代码 copied',dict(kind='application-final',codec='lz4',workload='stream',baseline='copied',treatment='vkso')),
        ('原生 XZ fresh 顺序：word-copy 对优化前 prepared',dict(kind='native-stream',codec='xz',workload='archive',phase='fresh-mount',baseline='prepared-xz',treatment='prepared-optimized'))]:
        r=one(rows,**query);add('- '+label+'：'+effect(r)+'。')
    add()
    add('这次优化显著缩小了 Python/XZ 的旧差距，但仍慢于 stock；LZ4 顺序任务相对旧缓存存在小幅回退，且 48 槽增加私有缓冲区容量。因此结果是有成本的优化，不支持所有任务均无回退或普遍更省内存。');add()
    add('## 2. 覆盖、执行和统计');add()
    add(f"完整分析为 30 个 campaign / 8,172 条观测，独立重算 {len(rows)} 项配对比较。2,688 条来自四个二进制及 runner 身份匹配的原生 campaign；5,484 条为本轮新观测。用户应用全部重测。被交互中断的原生组 790 条部分记录完整保留、全部排除，并使用原种子/条件重跑整组。更早 14 组 / 4,580 条缩减收尾及其中 127 条中断记录仍独立保留。未按性能筛选观测。")
    add();add('| 矩阵 | campaign | 观测 | 作用 |');add('| --- | ---: | ---: | --- |')
    kinds=[('native-final',3,3360,'五格式，scan/archive，fresh/warm，七种 native 条件'),('native-stream',3,672,'XZ/LZ4 大文件 archive，fresh/warm'),('application-final',9,3456,'gzip/XZ/LZ4 四任务，含 stock 单线程/translator、LKL 两配置、旧缓存 copied'),('heldout',6,336,'固定 gzip/XZ Python 编译，647 个相同产物'),('decoder-diagnostic',6,240,'XZ/LZ4 等长路径、解码器与动态依赖对照'),('sharing-singlecpu',3,108,'gzip stream 单 CPU stock/copied/shared')]
    for kind,c,n,scope in kinds:
        assert sum(x['samples'] for x in data['inputs'] if x['kind']==kind)==n
        add(f'| {kind} | {c} | {n:,} | {scope} |')
    add();add('每格三个 campaign；先在 campaign 内对配对 log ratio 求均值，再对 campaign 等权，95% 区间使用 campaign 层级 Student-t（df=2）。绝对时间为各 campaign 中位数的均值，不能直接相除代替配对比率。表中百分比为测试/对照−1，负值表示耗时降低。所有比较的 CPU 比率、逐 campaign 估计及次级重采样结果保存在 analysis.json。');add()
    add('同一 i7-1165G7 主机、同一次启动；原生 CPU 1，普通应用 CPU 1–2，单 CPU 对照单列。SMT/turbo 已关闭，powersave 策略保持原状。新进程/挂载/加载周期、交错配对和实际顺序均保留。压缩镜像页缓存预热；fresh-mount 不等于冷存储，warm native 可能绕过公共核心。正式计时无本任务并行编译、QEMU 或 profiler。TCG 仅用于功能。');add()
    add('## 3. 原生准备及公共 XZ 优化');add()
    table([r for r in rows if r['kind'] in ['native-final','native-stream'] and r['phase']=='fresh-mount' and r['baseline']=='native-word-normal' and r['treatment']=='prepared-optimized'])
    table([r for r in rows if r['kind']=='native-stream' and r['codec']=='xz' and r['baseline']=='prepared-xz' and r['treatment']=='prepared-optimized'])
    add('完整原生表同时保留 original、相同算法优化的 normal/relaxed native，以及先前 prepared 对照。prepared 的 PIC、stack protector、indirect/return thunk 差异未消除；结果属于完整准备方案，不能解释为纯 PGOT 成本或加固等价。匹配 word-copy 的 native 模块捆绑 XZ，和调用宿主 XZ 的旧参考具有不同驻留边界。');add()
    add('## 4. 完整应用表现');add()
    table([r for r in rows if r['kind'] in ['application-final','heldout'] and r['baseline'] in ['stock','stock-single','lkl-512','lkl-cache-512'] and r['treatment']=='vkso'])
    add('stock 为实际 squashfuse_ll 0.6.2；默认和 -s 使用同一可执行体，编译时 data/fragment 容量均为 48。LKL 使用 Linux 6.12、512 MiB heap，并保留默认和匹配 positive timeout 的配置；512 MiB 是偏性能的选择，不是完成任务的最低内存。不同核心/缓存/FUSE API/线程/库的完整方案差异不等于物理共享效果。Python 已参与本次优化，不能再称为未见过的 holdout。');add()
    add('## 5. 共享增量与缓存优化归因');add()
    table([r for r in rows if r['baseline']=='copied' and r['treatment']=='vkso'])
    table([r for r in rows if r['baseline']=='copied-small' and r['treatment']=='copied'])
    add('缓存对照保持公共 owner 指令不变；这项收益同样惠及 copied。默认路径、等长路径及单 CPU 条件分别报告；小点估计或包含零的区间不能证明严格等价或普遍零开销。');add()
    stream=one(rows,kind='application-final',codec='lz4',workload='stream',baseline='copied',treatment='vkso')
    add('LZ4 stream 的 shared/copied 三轮耗时变化依次为 '+', '.join(pct(v) for v in stream['campaign_ratios'].values())+'；合并 CPU 时间比变化为 '+pct(stream['cpu_ratio'])+' ['+', '.join(pct(v) for v in stream['cpu_ratio_ci95'])+']。耗时区间仍宽，不能把此前单轮 +6.22% 或本轮负点估计认定为固定共享机制成本；未删除任何一轮。');add()
    add('三轮完整 Python 解码器诊断在旧一槽桥上观察到：common-retained/library +2.60%，library/stock +13.01%。完整 Python 的解码次数从旧桥 352 次下降到 48 槽的 282 次；stock 为 243 次，产物一致。最终 metadata 扫描三次重放均为公共解析器 76 次 / 558,231 解压字节，stock 两种线程模式均为 137 次 / 1,106,363 字节。计数支持减少重复解压工作，但不能把所有时间差精确分配给一个原因。仪器化时间不进入正式统计。');add()
    add('## 6. 内存、物理页与部署');add()
    add('| 后端 | 1× PSS KiB | 4× | 16× |');add('| --- | ---: | ---: | ---: |')
    for v in ['stock','stock-single','copied','vkso','copied-small','copied-unbounded','lkl-cache-512']:
        vals=[one(mem['scale'],scale=n,variant=v)['pss_kib'] for n in [1,4,16]];add('| '+v+' | '+' | '.join(str(x) for x in vals)+' |')
    add();add('这些是完成任务后的单次未计时 helper 快照，不是峰值、区间或整机净内存。完整三 codec × 三 campaign 的 RSS/PSS/USS/VmHWM/线程和前后快照见 resource-ledger/resources.json。48 槽比旧一槽桥多保留约 6 MiB 数据；新缓存策略在小规模也可能高于旧无界桥。libfuse 16× 活对象诊断测到 14,786,560 B node slabs 和 2,097,152 B hash arrays；第二遍节点数稳定，说明桥的缓存上限并不等于整个进程内存上限。');add()
    small=one(mem['scale'],scale=16,variant='copied')['pss_kib'];large=one(mem['scale'],scale=16,variant='copied-unbounded')['pss_kib'];shared=one(mem['scale'],scale=16,variant='vkso')['pss_kib'];single=one(mem['scale'],scale=16,variant='stock-single')['pss_kib']
    add(f'16× 规模最终 copied 对旧无界 copied 的 PSS 变化为 {pct(small/large)}；最终 VKSO 为 {shared:,} KiB，高于 stock-single 的 {single:,} KiB。这是缓存策略的空间/时间折中，不是代码页共享造成的 PSS 降幅。');add()
    b=mem['business'];add(f"实际共享 9 页 / 36 KiB，逐页 PFN 和映射字节一致，copied PFN 不共享。owner/consumer 为 {b['owner_resident_bytes']//1024}/{b['native_consumer_resident_bytes']//1024} KiB；捆绑相同 XZ 的 normal native 参考为 {b['native_reference_resident_bytes']//1024} KiB；注册请求 {b['registration_requested_bytes']:,} B。通用平台 32 KiB 按用户指定作为一次性基础设施单列，不计入业务小计。")
    add();add('| 业务部署情景 | 文件实际分配 KiB |');add('| --- | ---: |')
    for n,v in mem['disk_scenarios'].items():add(f"| {n} | {v['allocated_bytes']//1024} |")
    add();add('磁盘采用未剥离文件的 st_blocks，按 inode 去重，共同依赖/镜像/平台同口径排除。已有 prepared native 与纯用户部署分别解释；普通 DSO 也可在用户进程间共享，不能按进程数乘以代码去重收益。模块驻留、helper PSS、注册请求与磁盘分配不能直接相加成整机净收益。')
    d=mem['deployment_summary']['core_export_registration'];add(f"构造/导出/注册在 9 个应用 campaign 中的中位耗时 {d['median']:.3f} s，范围 [{d['minimum']:.3f}, {d['maximum']:.3f}]；逐次阶段见 ledger。这个值不含编译、模块加载和验证，也不能假设 copied 构造免费。owner 重载或版本变化需要重新部署，已驻留后才可摊销到后续应用调用。")
    add();add('## 7. 正确性、适配和维护');add()
    counts={Path(x['path']).name:x['physical_lines'] for x in cost['source_lines'] if x['category']=='first_user_integration'}
    add(f"复用 34 个文件系统函数 / 2,103 原始物理行，16 个 native 源/头文件发生准备修改，3 个文件系统函数体改变。XZ 原始算法范围 2,604 行，当前 2,637 行，仅 dict_repeat 算法体编辑；公共 LZ4 同时保留。桥/POSIX/frontend 为 {counts['user_bridge.c']}/{counts['posix_io.c']}/{counts['fuse_frontend.c']} 行。生成支持、生成器、服务槽、机械移动、应用 translator、通用 exporter 修正及脚本分别核算。LKL 应用扩展 30 行只与已有平台上的应用接入比较，不能与首次内核准备混比。代码量没有转换为开发工时。")
    add();add('最终桥通过 25 个五格式挂载和 5 个 BCJ 挂载；客体中 copied/shared 各 22,032 次边界/随机读取。ASAN/UBSAN 检查私有适配器，覆盖 8192 文件、三轮 churn 和超过缓存预算的活跃句柄；未插桩公共核心，未证明全进程无泄漏。真实 FUSE FD/游标生命周期、native A 与真实 SIF B/C 的独立对象和退出次序、共享页及 XZ 断点、后续 native 回归、最小部署均通过。')
    add();add('已知上游负偏移缺陷的 old/fixed × native/copied/shared 维护记录保留。旧错误由客户端、daemon 信号及目标函数内核故障共同判断；并非将任意失败算作复现。当前最终桥客体回归三端 EIO、daemon 存活、五格式回归/restore/unload 通过。原维护实验中桥和前端保持不变；后来的字典与缓存优化单独计账。共同修复惠及 copied，仍需重建、导出/注册和重新部署，未证明热更新。')
    add();add('## 8. 主张判断和边界');add()
    add('| 主张 | 当前判断 | 对应证据/边界 |');add('| --- | --- | --- |')
    claims=[('复杂公共核心进入真实 native/user 应用','在明确范围内支持','真实 SIF/FD/offset、功能、PFN、私有对象与生命周期'),('保留原生功能并量化准备成本','在明确范围内支持','五格式、直接匹配优化参考；加固差异仍存在'),('物理共享的增量执行成本可量化','在测量范围内支持','同代码 copied/shared；不从不显著推出等价'),('相对现有后端的实际效率','在明确任务/配置范围内支持','上表所有任务、stock 两线程与 LKL 两缓存配置'),('格式代码复用与共同维护点','支持','源范围/修改面/真实上游修复；并非全部零改动'),('物理资源去重','条件性支持','36 KiB identity；已有 owner 与纯用户部署不同'),('减少开发/调试工时','未证明','无可靠历史人时或受控人工任务'),('整机净内存必然下降','不支持该一般结论','组件账本不足以替代完整整机增量测量'),('热更新、并发吞吐扩展、跨启动/机器推广','未验证','生命周期重叠及同 boot 三轮不能替代这些实验'),('shared 普遍优于同代码 copied','不支持','copied 享有核心/适配/维护收益且可独立部署')]
    for c in claims:add('| '+' | '.join(c)+' |')
    add();add('## 9. 复现和证据入口');add()
    add('本目录 analysis.json、summary.csv、audit.json、costs.json、reuse-audit/ 和 resource-ledger/ 是统一分析入口。源码协议与原/恢复注册在 test/section65/squashfs/confirmation-20261030-02/；recovered-formal-queue.json 指向最终 30 组原始记录。各目录保存 samples.jsonl、environment.json、实际顺序、阶段日志、资源和 PFN 检查。790 条部分记录由 data48-recovery-01/recovery.json 单独登记；旧 running 字段不表示仍有进程。')
    add();add('正式停止条件为固定矩阵完成，不以显著优势停止。未运行的 stream-resource 队列、bit-tree 构建和全部失败/拒绝候选均保留其真实状态。论文与图片另行处理，本报告不将旧 PDF 标为新结果。')
    (out/'EXPERIMENT_REPORT.md').write_text('\n'.join(lines)+'\n')
    (out/'report-provenance.json').write_text(json.dumps(dict(status='complete',scope='Experiment report only',inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [out/'analysis.json',out/'audit.json',out/'costs.json',out/'resource-ledger/resources.json',Path(__file__)]}),indent=2)+'\n')
    print('Wrote experiment report; no manuscript or images changed')
if __name__=='__main__':main()
