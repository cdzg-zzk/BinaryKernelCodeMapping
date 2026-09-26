#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Offline distributions from validated full campaigns; never collects or boots."""
from array import array
from collections import defaultdict
import csv
import itertools
import json
import math
from pathlib import Path
import random
import statistics as st

from bundle import sha256, write_json
from results import CASE_NAMES, KERNEL_APIS, percentile

SCENARIOS = ('idle', 'monotonic', 'monotonic_raw', 'monotonic_coarse')
VARIANTS = ('normal', 'no-retpoline')


def csv_rows(path):
    with path.open() as stream:
        yield from csv.DictReader(line for line in stream if not line.startswith('#'))


def delta_summary(raw, vkso):
    """Matched blocks, not matched inner rounds. Four blocks -> 256 resamples."""
    if len(raw) != len(vkso) or len(raw) < 3:
        raise ValueError('at least three complete block pairs required')
    delta = [v-r for r, v in zip(raw, vkso)]
    n = len(delta)
    if n <= 6:
        replicates = [st.fmean(delta[i] for i in ix)
                      for ix in itertools.product(range(n), repeat=n)]
    else:
        rng = random.Random(20260926)
        replicates = [st.fmean(rng.choices(delta, k=n)) for _ in range(20000)]
    return dict(raw_mean=st.fmean(raw), vkso_mean=st.fmean(vkso),
                delta=st.fmean(delta), raw_boot_means=raw, vkso_boot_means=vkso,
                block_deltas=delta, block_delta_range=[min(delta), max(delta)],
                delta_bootstrap95=[percentile(replicates, .025), percentile(replicates, .975)],
                negative_blocks=sum(x < 0 for x in delta), positive_blocks=sum(x > 0 for x in delta))


def band_stats(values, cut, cap=None):
    low = [min(x, cap) if cap is not None else x for x in values if x <= cut]
    high = [min(x, cap) if cap is not None else x for x in values if x > cut]
    if not low or not high:
        raise ValueError('empty band: cannot decompose conditional means')
    return dict(n=len(values), high_fraction=len(high)/len(values),
                low_mean=st.fmean(low), high_mean=st.fmean(high),
                low_median=st.median(low), high_median=st.median(high))


def decompose(raw, vkso, raw_cut, vkso_cut, cap=None):
    """Exact symmetric algebra, NOT causal attribution or matched latent states."""
    r, v = band_stats(raw, raw_cut, cap), band_stats(vkso, vkso_cut, cap)
    pr, pv = r['high_fraction'], v['high_fraction']
    p = (pr+pv)/2
    location = (1-p)*(v['low_mean']-r['low_mean']) + p*(v['high_mean']-r['high_mean'])
    mixture = (pv-pr)*((v['high_mean']+r['high_mean'])/2-(v['low_mean']+r['low_mean'])/2)
    delta = ((1-pv)*v['low_mean']+pv*v['high_mean']) - ((1-pr)*r['low_mean']+pr*r['high_mean'])
    if not math.isclose(location+mixture, delta, abs_tol=1e-9):
        raise ValueError('decomposition does not reconstruct total mean difference')
    return dict(raw=r, vkso=v, location=location, mixture=mixture, delta=delta)


def observe(root, manifest):
    data = defaultdict(lambda: array('d'))
    rounds, identities, inputs, other_cpus = [], [], [], []
    for entry in manifest['plan']:
        mode, case, block = entry['mode'], entry['case'], entry['block']
        directory = root / ('block-%02d' % block) / mode / case
        run = json.loads((directory/'run.json').read_text())
        backend = case.split('-', 1)[0]
        build = run if mode == 'read' else run['build']
        checks = build.get('kernel_checksums', {})
        identities.append(dict(mode=mode, case=case, block=block, boot_id=run['boot_id'],
            kernel_image_sha256=run.get('kernel_image_sha256', checks.get(backend+'-bzImage')),
            kernel_config_sha256=run.get('kernel_config_sha256', checks.get(backend+'.config')),
            benchmark_sha256=run.get('binary_sha256', build.get('binary_sha256')),
            public_library_sha256=build.get('public_library_sha256'),
            carrier_sha256=build.get('carrier_sha256'),
            git_commit=build.get('git_commit'), dirty_patch_sha256=build.get('dirty_patch_sha256'),
            source_fingerprint=build.get('source_fingerprint'),
            package_sha256=run.get('package_checksums_sha256', run.get('package_sha256'))))
        inputs.append(dict(path=str((directory/'SHA256SUMS').relative_to(root)), sha256=sha256(directory/'SHA256SUMS')))
        if mode == 'read':
            for r in csv_rows(directory/'samples.csv'):
                data['read_user', r['case'], case, block].append(int(r['tsc_ticks'])/int(r['iterations']))
            for r in csv_rows(directory/'kernel-reader.csv'):
                data['read_kernel', r['api'], case, block].append(int(r['total_tsc_cycles'])/int(r['iterations']))
        else:
            for scenario in SCENARIOS:
                for i in range(manifest['config']['REPEATS']):
                    f = directory/scenario/('round-%02d.csv' % i)
                    rows = list(csv_rows(f))
                    values = [int(r['cycles']) for r in rows if int(r['action']) == 0]
                    for r in rows:
                        if int(r['cpu']) != 0 and int(r['action']) == 0:
                            other_cpus.append(dict(case=case,block=block,scenario=scenario,round=i,
                                                   sample=int(r['sample']),cpu=int(r['cpu']),ticks=int(r['cycles'])))
                    data['update', scenario, case, block].extend(values)
                    rounds.append(dict(case=case, block=block, scenario=scenario, round=i,
                        n=len(values), other_actions=len(rows)-len(values),
                        mean=st.fmean(values), median=st.median(values)))
                    if scenario != 'idle':
                        # Complete enclosing load, same population as original aggregate.
                        for r in csv_rows(f.with_name(f.stem+'-reader.csv')):
                            data['concurrent_reader', scenario, case, block].append(int(r['tsc_ticks'])/int(r['calls']))
    return data, rounds, identities, inputs, other_cpus


def summarize(data, blocks):
    boots, comparisons, bands = [], [], []
    for (scope, metric, case, block), values in sorted(data.items()):
        ordered = sorted(values)
        q99 = percentile(ordered, .99)
        boots.append(dict(scope=scope, metric=metric, case=case, block=block, n=len(values),
            mean=st.fmean(values), median=st.median(values), q01=percentile(ordered, .01),
            q99=percentile(ordered, .99), minimum=ordered[0], maximum=ordered[-1],
            cap300_mean=st.fmean(min(x, 300) for x in values),
            tail300_fraction=sum(x > 300 for x in values)/len(values),
            tail300_excess=st.fmean(max(x-300, 0) for x in values),
            winsor99_mean=st.fmean(min(x, q99) for x in values)))
    for scope, metric in sorted({(k[0], k[1]) for k in data}):
        for variant in VARIANTS:
            r = [data[scope, metric, 'raw-'+variant, b] for b in blocks]
            v = [data[scope, metric, 'vkso-'+variant, b] for b in blocks]
            result = dict(scope=scope, metric=metric, variant=variant,
                **delta_summary([st.fmean(x) for x in r], [st.fmean(x) for x in v]))
            result['median_of_boot_medians_delta'] = st.median(st.median(x) for x in v)-st.median(st.median(x) for x in r)
            result['winsor99_delta'] = (
                st.fmean(b['winsor99_mean'] for b in boots if b['scope']==scope and b['metric']==metric and b['case']=='vkso-'+variant)-
                st.fmean(b['winsor99_mean'] for b in boots if b['scope']==scope and b['metric']==metric and b['case']=='raw-'+variant))
            if scope == 'update':
                result['cap300_delta'] = st.fmean(st.fmean(min(t, 300) for t in x) for x in v)-st.fmean(st.fmean(min(t, 300) for t in x) for x in r)
                result['tail300_excess_delta'] = result['delta']-result['cap300_delta']
                for rc, vc, name in [(120,110,'historical-valleys')]+[(c,c,'common-'+str(c)) for c in (100,110,120,130,140)]:
                    for cap in (None, 300):
                        paired=[]
                        try:
                            for block, raw, vkso in zip(blocks,r,v):
                                paired.append(dict(block=block, **decompose(raw,vkso,rc,vc,cap)))
                        except ValueError as exc:
                            bands.append(dict(variant=variant, scenario=metric, threshold=name,
                                              cap=cap, status='UNDEFINED', reason=str(exc)))
                            continue
                        bands.append(dict(variant=variant, scenario=metric, threshold=name,
                            raw_cut=rc, vkso_cut=vc, cap=cap, status='DEFINED', blocks=paired,
                            **{key:st.fmean(p[key] for p in paired) for key in ('location','mixture','delta')},
                            raw={key:st.fmean(p['raw'][key] for p in paired) for key in paired[0]['raw']},
                            vkso={key:st.fmean(p['vkso'][key] for p in paired) for key in paired[0]['vkso']}))
            comparisons.append(result)
    return boots, comparisons, bands


def write_csv(path, rows):
    with path.open('x') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def render(data, blocks, out):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':9, 'svg.fonttype':'none', 'pdf.fonttype':42})
    colors={'raw':'#0072B2','vkso':'#D55E00'}
    styles={'raw':'-','vkso':'--'}

    def draw(ax, arrays, backend, hist=False):
        if hist:
            edges=np.arange(40,244,4)
            ys=[np.histogram(a,bins=edges)[0]/len(a)*100 for a in arrays]
            x=(edges[1:]+edges[:-1])/2
        else:
            full=np.concatenate(arrays)
            x=np.unique(np.concatenate([np.quantile(full,np.linspace(0,.995,450)),
                np.quantile(full,[.999,.9995,.9999,1])]))
            ys=[np.searchsorted(np.sort(a),x,side='right')/len(a) for a in arrays]
        for y in ys: ax.plot(x,y,color=colors[backend],alpha=.18,lw=.6)
        ax.plot(x,np.mean(ys,axis=0),styles[backend],color=colors[backend],lw=1.5,label=backend.upper())

    def save(fig,name):
        fig.tight_layout(rect=(0,0,1,.965))
        for ext in ('png','pdf'):fig.savefig(out/(name+'.'+ext),dpi=160)
        plt.close(fig)

    for variant in VARIANTS:
        fig,axes=plt.subplots(4,2,figsize=(10,10))
        for i,scenario in enumerate(SCENARIOS):
            tails=[]
            for backend in colors:
                a=[np.array(data['update',scenario,backend+'-'+variant,b]) for b in blocks]
                draw(axes[i,0],a,backend,True);draw(axes[i,1],a,backend)
                tails.append('%s >240: %.2f%%'%(backend,np.mean([np.mean(x>240) for x in a])*100))
            axes[i,0].set(xlim=(40,240),ylabel='Calls / 4 ticks (%)',title=scenario+' | central distribution')
            axes[i,0].text(.98,.94,'; '.join(tails),ha='right',va='top',transform=axes[i,0].transAxes,fontsize=7)
            axes[i,1].set(xscale='log',ylim=(0,1.01),ylabel='CDF',title=scenario+' | full range')
            for ax in axes[i]:ax.set_xlabel('TSC ticks / UPDATE');ax.legend(fontsize=7);ax.spines[['top','right']].set_visible(False)
        fig.suptitle(variant+': UPDATE (all samples; thin lines = boots; thick = equal-boot average)')
        save(fig,'update-'+variant)
        for scope,metrics in [('read_user',CASE_NAMES),('read_kernel',KERNEL_APIS),('concurrent_reader',SCENARIOS[1:])]:
            cols=4 if scope=='read_user' else 3;nr=(len(metrics)+cols-1)//cols
            fig,axes=plt.subplots(nr,cols,figsize=(12,2.6*nr),squeeze=False)
            for ax,metric in zip(axes.flat,metrics):
                all_values=[]
                for backend in colors:
                    a=[np.array(data[scope,metric,backend+'-'+variant,b]) for b in blocks]
                    draw(ax,a,backend);all_values.extend(a)
                label=metric.replace('clock_gettime_','cgt: ').replace('clock_getres_','cgr: ').replace('_',' ')
                ax.set(title=label,ylim=(0,1.01),xlabel='TSC ticks / call (batch average)',ylabel='CDF')
                full=np.concatenate(all_values)
                if full.max()/full.min()>2:ax.set_xscale('log')
                ax.legend(fontsize=6);ax.tick_params(axis='x',labelsize=7);ax.spines[['top','right']].set_visible(False)
            for ax in list(axes.flat)[len(metrics):]:ax.set_visible(False)
            fig.suptitle(variant+': '+scope+' (full range; thin = boots; thick = equal-boot average)')
            save(fig,scope+'-'+variant)


def markdown_report(out, root, report):
    lines=['# Clocktime 全分布比较', '', '数据：`'+root.name+'`。', '',
        'Δ = VKSO − Raw；负值表示 VKSO 成本更低。单位均为 TSC ticks，不能写作 core cycles。', '',
        '主指标先对每个 boot 的全部原始观测取均值，再等权平均各 boot；不删除离群值，不扣计时常数。'
        'READ/kernel reader/concurrent reader 的观测是完整调用批次平均，UPDATE 是逐次 action=0 发布成本。'
        '并发 reader 使用包围 writer 的完整负载窗口，不将其误写为逐次时间对齐。', '',
        '区间为同 block 的 Raw/VKSO boot 均值差的 percentile bootstrap 95% 区间。'
        '4 个 block 枚举 4⁴=256 次有放回重采样；轮次不是独立实验。'
        '区间仅作逐项不确定性描述：boot 数少、无多重比较修正，不作等价性声明。', '']
    for scope in ('read_user','read_kernel','update','concurrent_reader'):
        lines.extend(['## '+scope,'','| 配置 | 接口/负载 | Raw | VKSO | Δ | 95% 区间 | 四个 block 的 Δ |',
                      '| --- | --- | ---: | ---: | ---: | --- | --- |'])
        for c in report['comparisons']:
            if c['scope']!=scope:continue
            ci=c['delta_bootstrap95']
            lines.append('| %s | %s | %.3f | %.3f | %+.3f | [%+.3f, %+.3f] | %s |'%(
                c['variant'],c['metric'],c['raw_mean'],c['vkso_mean'],c['delta'],*ci,
                ', '.join('%+.3f'%x for x in c['block_deltas'])))
        lines.append('')
    lines.extend(['## UPDATE 的区间位置与占比','',
        '以下沿用历史谷值：Raw ≤120 / >120，VKSO ≤110 / >110。'
        '这是两套分布的描述性划分，不是相同业务状态的配对。位置为各 boot 条件均值的等权均值。', '',
        '| 配置 | 负载 | Raw 低/高均值 | VKSO 低/高均值 | Raw/VKSO 高侧占比 | 位置项 | 占比项 |',
        '| --- | --- | ---: | ---: | ---: | ---: | ---: |'])
    for b in report['bands']:
        if b['threshold']!='historical-valleys' or b['cap'] is not None or b['status']!='DEFINED':continue
        r,v=b['raw'],b['vkso']
        lines.append('| %s | %s | %.2f / %.2f | %.2f / %.2f | %.1f%% / %.1f%% | %+.2f | %+.2f |'%(
            b['variant'],b['scenario'],r['low_mean'],r['high_mean'],v['low_mean'],v['high_mean'],
            100*r['high_fraction'],100*v['high_fraction'],b['location'],b['mixture']))
    lines.extend(['', '分解在每个 block 内计算后等权平均。记 p 为高侧占比，L/H 为低/高侧均值：', '',
        '`位置项 = (1−p̄)(L_V−L_R) + p̄(H_V−H_R)`', '',
        '`占比项 = (p_V−p_R)(H̄−L̄)`', '',
        '两项之和精确等于完整均值差；这是代数分解，不是因果归因。'
        '主分解保留长尾；report.json 另包含共同阈值 100/110/120/130/140 及 300 ticks 截顶敏感性结果。'
        '划分改变时两项可以改变，不能挑选有利阈值声称某种业务状态导致性能变化。', '',
        '## UPDATE 长尾敏感性', '',
        '截顶只用于解释敏感性：`min(x,300)` 不替换主结果。尾部超额项是 `max(x−300,0)` 的均值差。', '',
        '| 配置 | 负载 | 完整 Δ | 截顶 300 后 Δ | 尾部超额 Δ |',
        '| --- | --- | ---: | ---: | ---: |'])
    for c in report['comparisons']:
        if c['scope']=='update':lines.append('| %s | %s | %+.3f | %+.3f | %+.3f |'%(
            c['variant'],c['metric'],c['delta'],c['cap300_delta'],c['tail300_excess_delta']))
    lines.extend(['','## 文件与图示','',
        '- `boot-statistics.csv`：各独立启动的完整均值、分位数、长尾及 winsor99 敏感性。',
        '- `update-rounds.csv`：每轮均值和中位数，供观察同一启动内的占比变化。',
        '- `report.json`：主比较、区间、所有阈值敏感性、版本身份与输入记录。',
        '- `update-*.png/.pdf`：每种负载的中央直方图和全范围 CDF；尾部比例标在图内。',
        '- `read_user-*`、`read_kernel-*`、`concurrent_reader-*`：每个接口的全范围批次成本 CDF。',
        '', '粗曲线对 boot 等权，细曲线显示单个 boot；图上大量采样点不增加独立实验数。'
        '未执行新性能采集；全部结果由已验证的原始记录重算。'])
    (out/'report.md').write_text('\n'.join(lines)+'\n')


def generate(roots, out, validator):
    """Called by the fixed experiment.sh interface, separate from old aggregate."""
    if out.exists():raise ValueError('output already exists: '+str(out))
    roots=[p.resolve() for p in roots]
    if len(set(p.name for p in roots))!=len(roots):raise ValueError('duplicate campaign names')
    if any(out.resolve()==p or p in out.resolve().parents for p in roots):
        raise ValueError('analysis output must be outside immutable input campaigns')
    import matplotlib  # Fail before validation/output if plotting dependencies are missing.
    import numpy
    out.mkdir(parents=True,exist_ok=False)
    history=[]
    for root in roots:
        print('validating_distribution_input='+str(root),flush=True)
        manifest=json.loads((root/'campaign.json').read_text())
        validator(root,manifest)
        data, rounds, identities, inputs, other_cpus=observe(root,manifest)
        blocks=sorted({e['block'] for e in manifest['plan']})
        boots,comparisons,bands=summarize(data,blocks)
        report=dict(protocol='clocktime-distribution-v1',campaign=str(root),validation='PASS',
            independent_unit='boot',blocks=blocks,unit='TSC ticks',
            estimator='mean of complete within-boot means; equal weight per boot',
            interval='pointwise block-paired percentile bootstrap; n=4 has limited coverage; not equivalence',
            boot_statistics=boots,comparisons=comparisons,bands=bands,identities=identities,
            non_cpu0_action0_samples=other_cpus,
            inputs=inputs,campaign_manifest_sha256=sha256(root/'campaign.json'),analysis_sha256=sha256(Path(__file__)))
        dest=out/root.name;dest.mkdir()
        write_json(dest/'report.json',report);write_csv(dest/'boot-statistics.csv',boots)
        write_csv(dest/'update-rounds.csv',rounds)
        markdown_report(dest,root,report);render(data,blocks,dest)
        history.append(report)
        print('distribution_report='+str(dest/'report.md'),flush=True)
    # Cross-campaign values remain separated; source changes and boot drift coexist.
    rows=[]
    for report in history:
        for c in report['comparisons']:
            rows.append(dict(campaign=Path(report['campaign']).name,scope=c['scope'],metric=c['metric'],
                             variant=c['variant'],raw=c['raw_mean'],vkso=c['vkso_mean'],delta=c['delta']))
    write_csv(out/'campaign-comparison.csv',rows)
    write_json(out/'analysis.json',dict(status='COMPLETE',campaigns=[str(r) for r in roots],
        analysis_sha256=sha256(Path(__file__)),numpy_version=numpy.__version__,matplotlib_version=matplotlib.__version__,
        note='Campaigns are not pooled. Diagnostics are excluded. Raw/VKSO bands are not identified business states.'))
    with (out/'SHA256SUMS').open('x') as f:
        for p in sorted(out.rglob('*')):
            if p.is_file() and p!=out/'SHA256SUMS':f.write(sha256(p)+'  '+str(p.relative_to(out))+'\n')
