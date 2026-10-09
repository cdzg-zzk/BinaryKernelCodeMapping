#!/usr/bin/env python3
"""Offline UPDATE peak/occupancy analysis; immutable campaign inputs."""
import argparse
import base64
import csv
import hashlib
import html
import itertools
import json
import re
from pathlib import Path

import numpy as np

SCENARIOS = ('idle', 'monotonic', 'monotonic_raw', 'monotonic_coarse')
VARIANTS = ('normal', 'no-retpoline')
BACKENDS = ('raw', 'vkso')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checksums(directory):
    return {name: checksum for checksum, name in
            (line.split(None, 1) for line in (directory/'SHA256SUMS').read_text().splitlines())}


def verify(path, directory, sums):
    assert digest(path) == sums[str(path.relative_to(directory))], str(path)


def load(root):
    manifest = json.loads((root/'campaign.json').read_text())
    assert manifest['protocol'] == 'clocktime-full-v1'
    reference = json.loads(root.with_name(root.name+'-summary.json').read_text())
    expected = {(r['case'], r['scenario'], r['block'], r['round']): r['writer']
                for r in reference['stateful']['round_summaries']}
    data, rounds, identities, other_cpus = {}, {}, [], []
    boot_ids = set()
    for entry in manifest['plan']:
        if entry['mode'] != 'update':
            continue
        case, block = entry['case'], entry['block']
        directory = root/f'block-{block:02d}'/'update'/case
        sums = checksums(directory)
        verify(directory/'run.json', directory, sums)
        run = json.loads((directory/'run.json').read_text())
        assert run['status'] == 'COMPLETE' and run['environment_cleanup'] == 'PASS'
        assert not run['cleanup_errors'] and run['scope'] == 'all'
        assert run['config'] == manifest['config']
        assert run['case'] == case and run['block'] == block
        assert run['boot_id'] not in boot_ids
        boot_ids.add(run['boot_id'])
        package = manifest['packages']['update'][case.split('-', 1)[1]]
        assert run['package_sha256'] == package['sha256']
        assert run['bundle_sha256'] == package['direct_sha256']
        identities.append(dict(case=case, block=block, boot_id=run['boot_id'],
                               package_sha256=run['package_sha256'],
                               tool_revision=run['tool_revision']))
        for scenario in SCENARIOS:
            chunks = []
            for i in range(manifest['config']['REPEATS']):
                path = directory/scenario/f'round-{i:02d}.csv'
                verify(path, directory, sums)
                with path.open() as stream:
                    header = next(stream).strip()
                    rows = list(csv.DictReader(stream))
                meta = dict(re.findall(r'(\w+)=(\d+)', header))
                assert int(meta['dropped']) == 0 and int(meta['seen']) == len(rows)
                assert all(int(r['sample']) == j and int(r['cycles']) > 0
                           for j, r in enumerate(rows))
                assert all(int(r['action']) == 0 and int(r['cpu']) >= 0 for r in rows)
                for r in rows:
                    if int(r['cpu']) != 0:
                        other_cpus.append(dict(case=case, scenario=scenario, block=block,
                                               round=i, **{k:int(v) for k,v in r.items()}))
                values = np.array([int(r['cycles']) for r in rows], dtype=np.int64)
                prior = expected[case, scenario, block, i]
                assert len(values) == prior['count']
                assert np.isclose(values.mean(), prior['mean_ticks'], atol=1e-10, rtol=0)
                chunks.append(values)
            data[case, scenario, block] = np.concatenate(chunks)
            rounds[case, scenario, block] = chunks
    assert len(boot_ids) == manifest['config']['BLOCKS']*4
    return manifest, data, rounds, identities, other_cpus


def histogram(arrays):
    return np.mean([np.bincount(a[a <= 300], minlength=301)/len(a) for a in arrays], axis=0)


def smoothed(hist, sigma=3):
    grid = np.arange(-int(4*sigma), int(4*sigma)+1)
    kernel = np.exp(-0.5*(grid/sigma)**2)
    return np.convolve(hist, kernel/kernel.sum(), mode='same')


def peaks(hist, sigma=3):
    smooth = smoothed(hist, sigma)
    # Search windows cover the two main regions observed in this campaign.
    # This is a descriptive mode finder, not a latent-state mixture model.
    maxima = [i for i in range(65, 161)
              if smooth[i] > smooth[i-1] and smooth[i] >= smooth[i+1]]
    lower, upper = [i for i in maxima if i <= 125], [i for i in maxima if i >= 126]
    if not lower or not upper:
        raise ValueError('two local maxima unresolved at this smoothing width')
    low = max(lower, key=lambda i:smooth[i])
    high = max(upper, key=lambda i:smooth[i])
    if high-low < 16:
        raise ValueError('two main regions unresolved at this smoothing width')
    cut = int(low+8+np.argmin(smooth[low+8:high-7]))
    return dict(low_mode=low, high_mode=high, cut=cut,
                valley_depth=float(smooth[cut]/min(smooth[low], smooth[high]))), smooth


def stats(values, cut):
    low = values[values <= cut]
    high = values[values > cut]
    central = high[high <= 300]
    assert len(low) and len(central)
    result = dict(n=len(values), cut=cut, mean=float(values.mean()),
                  low_fraction=len(low)/len(values), high_fraction=len(high)/len(values),
                  tail300_fraction=float(np.mean(values > 300)),
                  tail300_excess=float(np.maximum(values-300, 0).mean()),
                  cap300_mean=float(np.minimum(values, 300).mean()))
    for name, a in (('low', low), ('high', high), ('high_central', central)):
        result[name+'_mean'] = float(a.mean())
        result[name+'_median'] = float(np.median(a))
        for q in (10, 90):
            result[name+f'_q{q}'] = float(np.percentile(a, q))
    for q in (10, 25, 50, 75, 90, 95, 99):
        result[f'q{q}'] = float(np.percentile(values, q))
    for limit in (180, 200, 240):
        result[f'tail{limit}_fraction'] = float(np.mean(values > limit))
        result[f'tail{limit}_excess'] = float(np.maximum(values-limit, 0).mean())
    reconstructed = result['low_fraction']*result['low_mean']+result['high_fraction']*result['high_mean']
    assert np.isclose(reconstructed, result['mean'], atol=1e-10, rtol=0)
    return result


def decompose(raw, vkso):
    p = (raw['high_fraction']+vkso['high_fraction'])/2
    low_delta = vkso['low_mean']-raw['low_mean']
    high_delta = vkso['high_mean']-raw['high_mean']
    low_term = (1-p)*low_delta
    high_term = p*high_delta
    occupancy = (vkso['high_fraction']-raw['high_fraction'])*(
        (vkso['high_mean']+raw['high_mean']-vkso['low_mean']-raw['low_mean'])/2)
    delta = vkso['mean']-raw['mean']
    assert np.isclose(low_term+high_term+occupancy, delta, atol=1e-10, rtol=0)
    return dict(low_delta=low_delta, high_delta=high_delta, low_term=low_term,
                high_term=high_term, location=low_term+high_term,
                occupancy=occupancy, delta=delta)


def average(rows):
    return {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}


def bootstrap(values):
    n = len(values)
    samples = [np.mean([values[i] for i in ix]) for ix in itertools.product(range(n), repeat=n)]
    return [float(x) for x in np.percentile(samples, [2.5, 97.5])]


def write_csv(path, rows):
    with path.open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyze(root, out, plot):
    assert not out.exists(), 'choose a new output directory'
    assert root not in out.parents, 'keep analyses outside immutable campaign'
    manifest, data, rounds, identities, other_cpus = load(root)
    blocks = list(range(1, manifest['config']['BLOCKS']+1))
    group_rows, boot_rows, round_rows, comparisons, sensitivity, smooth_rows = [], [], [], [], [], []
    group_map, thresholds = {}, {}
    for variant in VARIANTS:
        for scenario in SCENARIOS:
            groups = {}
            for backend in BACKENDS:
                case = backend+'-'+variant
                arrays = [data[case, scenario, b] for b in blocks]
                h = histogram(arrays)
                mode, smooth = peaks(h)
                cut = mode['cut']
                thresholds[case, scenario] = cut
                boot_stats = [stats(a, cut) for a in arrays]
                boot_peaks = []
                for a in arrays:
                    try:
                        boot_peaks.append(peaks(histogram([a]))[0])
                    except ValueError:
                        boot_peaks.append(dict(low_mode=None, high_mode=None, cut=None, valley_depth=None))
                group = dict(variant=variant, scenario=scenario, backend=backend,
                             **{**mode, **average(boot_stats)})
                for key in ('low_mode', 'high_mode', 'cut'):
                    group[key] = mode[key]
                    resolved = [x[key] for x in boot_peaks if x[key] is not None]
                    group[key+'_boot_range'] = [min(resolved), max(resolved)] if resolved else None
                group['resolved_boots'] = sum(x['cut'] is not None for x in boot_peaks)
                group['high_fraction_boot_range'] = [min(r['high_fraction'] for r in boot_stats), max(r['high_fraction'] for r in boot_stats)]
                group['total_samples'] = sum(len(a) for a in arrays)
                groups[backend] = boot_stats
                group_map[case, scenario] = group
                group_rows.append(group)
                for b, bs, bp in zip(blocks, boot_stats, boot_peaks):
                    boot_rows.append(dict(case=case, scenario=scenario, block=b,
                                          own_low_mode=bp['low_mode'], own_high_mode=bp['high_mode'],
                                          own_cut=bp['cut'], valley_depth=bp['valley_depth'], **bs))
                    for i, a in enumerate(rounds[case, scenario, b]):
                        round_rows.append(dict(case=case, scenario=scenario, block=b, round=i, **stats(a, cut)))
                for t in range(301):
                    smooth_rows.append(dict(case=case, scenario=scenario, ticks=t,
                                            fraction=float(h[t]), smooth_fraction=float(smooth[t])))
            per_block = [dict(block=b, **decompose(r, v))
                         for b, r, v in zip(blocks, groups['raw'], groups['vkso'])]
            summary = dict(variant=variant, scenario=scenario, **average(per_block), blocks=per_block)
            for metric in ('low_delta', 'high_delta', 'location', 'occupancy', 'delta'):
                values = [p[metric] for p in per_block]
                summary[metric+'_block_range'] = [min(values), max(values)]
                summary[metric+'_bootstrap95'] = bootstrap(values)
            for q in (10, 25, 50, 75, 90, 95, 99):
                summary[f'q{q}_delta'] = float(np.mean([v[f'q{q}']-r[f'q{q}'] for r, v in zip(groups['raw'], groups['vkso'])]))
            summary['tail_excess_delta'] = float(np.mean([v['tail300_excess']-r['tail300_excess'] for r, v in zip(groups['raw'], groups['vkso'])]))
            comparisons.append(summary)
            # Independent +/-5 tick shifts; retain all 9 outcomes.
            for rs, vs in itertools.product((-5, 0, 5), repeat=2):
                pairs = [decompose(stats(data['raw-'+variant, scenario, b], thresholds['raw-'+variant, scenario]+rs),
                                   stats(data['vkso-'+variant, scenario, b], thresholds['vkso-'+variant, scenario]+vs)) for b in blocks]
                sensitivity.append(dict(variant=variant, scenario=scenario, raw_shift=rs, vkso_shift=vs, status='defined', **average(pairs)))
            for sigma in (1.5, 2, 4, 6):
                try:
                    cuts = {backend: peaks(histogram([data[backend+'-'+variant, scenario, b] for b in blocks]), sigma)[0] for backend in BACKENDS}
                    pairs = [decompose(stats(data['raw-'+variant, scenario, b], cuts['raw']['cut']),
                                       stats(data['vkso-'+variant, scenario, b], cuts['vkso']['cut'])) for b in blocks]
                    result = dict(status='defined', **average(pairs))
                except ValueError:
                    result = dict(status='unresolved-peaks', **{k:None for k in per_block[0] if k!='block'})
                sensitivity.append(dict(variant=variant, scenario=scenario, raw_shift='sigma='+str(sigma),
                                        vkso_shift='sigma='+str(sigma), **result))
    report = dict(protocol='clocktime-update-peaks-v1', campaign=str(root),
                  campaign_manifest_sha256=digest(root/'campaign.json'), script_sha256=digest(Path(__file__)),
                  validation='raw writer files and run checksums PASS; all periodic action0 samples retained including non-CPU0; no dropped rows; existing round means/counts reproduced',
                  unit='TSC ticks/update', independent_unit='boot',
                  method='equal boot weighting; Gaussian smoothing sigma=3 ticks for descriptive local maxima; low window 65..125, high window 126..160; minimum between mode+8 and mode-8 sets population-specific valley; no observation removed',
                  limitations='low/high are distribution strata, not identified matching business states; Raw loaded peaks overlap; high band includes shoulders and tails; bootstrap is descriptive with only four block pairs; sensitivity conditional on fitted cuts',
                  groups=group_rows, comparisons=comparisons, identities=identities, non_cpu0_samples=other_cpus,
                  threshold_sensitivity=sensitivity)
    out.mkdir(parents=True)
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    write_csv(out/'groups.csv', [{k:v for k,v in r.items() if not isinstance(v, list)} for r in group_rows])
    write_csv(out/'boots.csv', boot_rows)
    write_csv(out/'rounds.csv', round_rows)
    write_csv(out/'threshold-sensitivity.csv', sensitivity)
    write_csv(out/'histograms.csv', smooth_rows)
    if plot:
        render(data, blocks, group_map, comparisons, out)
        write_html(report, out)
    print(json.dumps(dict(output=str(out), samples=sum(len(a) for a in data.values()), writer_boots=len(identities)), indent=2))


def render(data, blocks, groups, comparisons, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 9, 'pdf.fonttype': 42, 'svg.fonttype': 'none'})
    colors = {'raw': '#0072B2', 'vkso': '#D55E00'}
    for variant in VARIANTS:
        fig, axes = plt.subplots(4, 2, figsize=(12, 12))
        for i, scenario in enumerate(SCENARIOS):
            for backend in BACKENDS:
                case = backend+'-'+variant
                arrays = [data[case, scenario, b] for b in blocks]
                group = groups[case, scenario]
                for a in arrays:
                    sm = smoothed(histogram([a]))
                    axes[i, 0].plot(np.arange(301), sm*100, color=colors[backend], alpha=.2, lw=.7)
                sm = smoothed(histogram(arrays))
                axes[i, 0].plot(np.arange(301), sm*100, color=colors[backend], lw=1.7,
                                label=f"{backend}: modes {group['low_mode']}/{group['high_mode']}, cut {group['cut']}")
                axes[i, 0].axvline(group['cut'], color=colors[backend], lw=.7, ls=':')
                maximum = max(int(a.max()) for a in arrays)
                x = np.unique(np.concatenate((np.arange(50, 301), np.geomspace(301, max(302, maximum), 350)))).astype(int)
                cdfs = [np.searchsorted(np.sort(a), x, side='right')/len(a) for a in arrays]
                for cdf in cdfs:
                    axes[i, 1].plot(x, cdf, color=colors[backend], alpha=.2, lw=.7)
                axes[i, 1].plot(x, np.mean(cdfs, axis=0), color=colors[backend], lw=1.7, label=backend)
            axes[i, 0].set(xlim=(60, 280), xlabel='TSC ticks / UPDATE', ylabel='Probability / tick (%)', title=scenario+' | smoothed density')
            axes[i, 1].set(xscale='log', ylim=(0, 1.005), xlabel='TSC ticks / UPDATE (log scale)', ylabel='CDF', title=scenario+' | full-range CDF')
            for ax in axes[i]:
                ax.legend(fontsize=8)
                ax.spines[['top', 'right']].set_visible(False)
        fig.suptitle(variant+': four boots, thin = individual boots, thick = equal-boot average\nAll samples in denominators; density smoothing sigma=3 ticks; CDF covers long tails')
        fig.tight_layout(rect=(0, 0, 1, .955))
        for extension in ('png', 'pdf', 'svg'):
            fig.savefig(out/('distribution-'+variant+'.'+extension), dpi=160)
        plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for i, variant in enumerate(VARIANTS):
        for j, scenario in enumerate(SCENARIOS):
            for backend, shift in (('raw', -.15), ('vkso', .15)):
                case = backend+'-'+variant
                cut = groups[case, scenario]['cut']
                fractions = [stats(data[case, scenario, b], cut)['high_fraction']*100 for b in blocks]
                axes[i, 0].bar(j+shift, np.mean(fractions), width=.28, color=colors[backend], alpha=.65, label=backend if j==0 else None)
                axes[i, 0].scatter(j+shift+np.linspace(-.06, .06, len(blocks)), fractions, color=colors[backend], s=22)
            result = next(c for c in comparisons if c['variant']==variant and c['scenario']==scenario)
            for shift, key, color in ((-.22, 'low_term', '#009E73'), (0, 'high_term', '#CC79A7'), (.22, 'occupancy', '#E69F00')):
                axes[i, 1].bar(j+shift, result[key], width=.2, color=color, label=key if j==0 else None)
            axes[i, 1].scatter(j, result['delta'], color='black', marker='D', s=28, label='full mean delta' if j==0 else None)
        axes[i, 0].set(title=variant+' | high-band occupancy', ylabel='High-band observations (%)', ylim=(0, 100))
        axes[i, 1].set(title=variant+' | exact mean decomposition', ylabel='VKSO - Raw (TSC ticks / UPDATE)')
        axes[i, 1].axhline(0, color='gray', lw=.6)
        for ax in axes[i]:
            ax.set_xticks(range(4), ('idle', 'mono', 'raw', 'coarse'))
            ax.legend(fontsize=8)
            ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Population-specific valley bands; points = independent boots\nDecomposition is algebraic, not causal; includes every long-tail observation')
    fig.tight_layout(rect=(0, 0, 1, .92))
    for extension in ('png', 'pdf', 'svg'):
        fig.savefig(out/('occupancy-decomposition.'+extension), dpi=160)
    plt.close(fig)


def write_html(report, out):
    def table(headers, rows):
        return '<table><thead><tr>'+''.join('<th>'+html.escape(str(h))+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join(
            '<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table>'

    groups = {(g['variant'], g['scenario'], g['backend']):g for g in report['groups']}
    panels = []
    for variant in VARIANTS:
        peak_rows, band_rows, decomposition_rows, tail_rows = [], [], [], []
        for c in report['comparisons']:
            if c['variant'] != variant:
                continue
            scenario = c['scenario']
            r, v = groups[variant, scenario, 'raw'], groups[variant, scenario, 'vkso']
            peak_rows.append([scenario, f"{r['low_mode']} → {v['low_mode']} ({v['low_mode']-r['low_mode']:+d})",
                              f"{r['high_mode']} → {v['high_mode']} ({v['high_mode']-r['high_mode']:+d})",
                              f"{100*r['high_fraction']:.1f}% → {100*v['high_fraction']:.1f}%",
                              f"{r['cut']} / {v['cut']}"])
            band_rows.append([scenario, f"{r['low_median']:.2f} / {v['low_median']:.2f}",
                              f"{r['high_median']:.2f} / {v['high_median']:.2f}",
                              f"{r['low_mean']:.2f} / {v['low_mean']:.2f}",
                              f"{r['high_mean']:.2f} / {v['high_mean']:.2f}",
                              f"{100*r['high_fraction_boot_range'][0]:.1f}–{100*r['high_fraction_boot_range'][1]:.1f}% / {100*v['high_fraction_boot_range'][0]:.1f}–{100*v['high_fraction_boot_range'][1]:.1f}%"])
            decomposition_rows.append([scenario, f"{c['low_term']:+.2f}", f"{c['high_term']:+.2f}",
                                       f"{c['occupancy']:+.2f}", f"{c['delta']:+.2f}"])
            tail_rows.append([scenario]+[f"{100*r[f'tail{t}_fraction']:.2f}% / {100*v[f'tail{t}_fraction']:.2f}%" for t in (180, 200, 240, 300)]+
                             [f"{r['q95']:.2f} / {v['q95']:.2f}", f"{r['q99']:.2f} / {v['q99']:.2f}"])
        picture = base64.b64encode((out/('distribution-'+variant+'.png')).read_bytes()).decode()
        panels.append('<section data-variant="'+variant+'"><h2>'+variant+'</h2><h3>主峰位置与高侧占比</h3>'+table(
            ['负载', '低峰 Raw → VKSO (Δ)', '高峰 Raw → VKSO (Δ)', '高侧占比 Raw → VKSO', '分界 Raw / VKSO'], peak_rows)+
            '<p>峰位置：等权启动密度，经 σ=3 ticks 高斯平滑后的局部极大值。占比按各自谷值划分，高侧包含肩峰和长尾。主峰搜索区间为低侧 65–125、高侧 126–160；分布类别没有被识别为相同业务状态。</p>'+
            '<img alt="UPDATE density and full CDF" src="data:image/png;base64,'+picture+'">'+
            '<h3>条件统计（Raw / VKSO）</h3>'+table(['负载', '低侧中位数', '高侧中位数', '低侧均值', '高侧均值', '高侧占比四启动范围'], band_rows)+
            '<p>先计算每次启动的条件统计，再等权平均四次启动。高侧均值保留全部长尾，不能将它直接当作主峰位置。</p>'+
            '<h3>完整均值差的精确分解</h3>'+table(['负载', '低侧成本贡献', '高侧成本贡献', '占比贡献', '合计 Δ'], decomposition_rows)+
            '<p>每块分别计算：低侧贡献=(1−p̄)(Lᵥ−Lᵣ)，高侧贡献=p̄(Hᵥ−Hᵣ)，占比贡献=(pᵥ−pᵣ)(H̄−L̄)，再等权平均。三项之和逐块精确重建完整均值差。这是描述性代数分解，不能作因果归因。</p>'+
            '<h3>较慢样本与尾部（Raw / VKSO）</h3>'+table(['负载', '>180', '>200', '>240', '>300', 'P95', 'P99'], tail_rows)+
            '<p>180/200/240/300 为描述性成本阈值；未删除、截断或扣除任何正式样本。尾部分位数为逐次 UPDATE 观测的启动内分位数，再等权平均。</p></section>')
    sensitivity = []
    for c in report['comparisons']:
        rows = [r for r in report['threshold_sensitivity'] if r['variant']==c['variant'] and r['scenario']==c['scenario'] and r['status']=='defined']
        sensitivity.append([c['variant'], c['scenario']]+[f"{min(r[k] for r in rows):+.2f}…{max(r[k] for r in rows):+.2f}" for k in ('low_delta', 'high_delta', 'location', 'occupancy')])
    text = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>UPDATE 主峰与占比分析</title>
<style>body{font:16px/1.6 system-ui,sans-serif;max-width:1150px;margin:30px auto;padding:0 20px;color:#202932}table{border-collapse:collapse;width:100%;font-size:14px;margin:20px 0}th,td{border-bottom:1px solid #dce2e8;padding:8px;text-align:right}th:first-child,td:first-child{text-align:left}th{background:#eef3f7}img{width:100%;height:auto}button{padding:8px 16px;margin:8px;font-size:16px}p{max-width:1000px}h2{margin-top:35px}</style>
<h1>当前 Clocktime UPDATE：主峰、占比与长尾</h1><p>数据：20260929T040650Z-clocktime-full；16 次独立 UPDATE 启动，3,599,774 个 periodic action=0 样本。960 个原始 CSV、运行记录校验通过；逐轮样本数和均值与原 summary 一致，无丢样。4 个 CPU2 样本与原汇总一致保留。</p>
<p>单位为 TSC ticks/update；Δ=VKSO−Raw，负值表示更低成本。VKSO 低峰均比 Raw 低，高侧占比更大；no-retpoline 高主峰明显更高。Raw 的加载分布主峰重叠且有肩峰，高侧均值也包含主峰以外的慢样本。</p>
<button onclick="choose('all')">全部</button><button onclick="choose('normal')">Normal</button><button onclick="choose('no-retpoline')">no-retpoline</button>
'''+''.join(panels)+'<h2>阈值与平滑敏感性</h2>'+table(['配置', '负载', '低侧均值 Δ 范围', '高侧均值 Δ 范围', '成本位置贡献范围', '占比贡献范围'], sensitivity)+'''
<p>范围涵盖 Raw/VKSO 分界各独立移动 ±5 ticks 的九种组合，以及 σ=1.5/2/4/6 可辨双峰时的结果。未辨出两个主峰的宽度在 JSON 标为 unresolved-peaks。低侧条件均值差始终为负，占比贡献始终为正；部分高侧条件均值差会变号。范围为敏感性范围，不是置信区间。</p>
<p>峰占比受谷值选择影响，不能解读为已知代码路径的发生率。Normal coarse 的谷底较浅，分峰最不确定。主结论来自密度峰位置及四次启动的重复表现。只有四块，逐块 bootstrap 区间仅作描述；峰分类在全部样本上选择，未重新 bootstrap 拟合谷值。</p>
<h2>复算文件</h2><p><a href="report.json">完整 JSON</a> · <a href="groups.csv">分组统计</a> · <a href="boots.csv">逐启动</a> · <a href="rounds.csv">逐轮</a> · <a href="threshold-sensitivity.csv">敏感性</a> · <a href="histograms.csv">密度数据</a></p>
<script>function choose(v){document.querySelectorAll('section[data-variant]').forEach(s=>s.hidden=v!=='all'&&s.dataset.variant!==v)}</script></html>'''
    (out/'report.html').write_text(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('campaign', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--plots', action='store_true')
    args = parser.parse_args()
    analyze(args.campaign.resolve(), args.out.resolve(), args.plots)
