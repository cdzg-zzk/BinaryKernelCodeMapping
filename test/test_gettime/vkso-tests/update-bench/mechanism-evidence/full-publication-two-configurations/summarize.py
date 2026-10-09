#!/usr/bin/env python3
"""Combine the completed, separately verified full-publication matrices."""
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
SOURCES = {'Normal': HERE.parent / 'full-publication-recorder-normal/step-07-review',
           'no-retpoline': HERE.parent / 'full-publication-recorder-control/step-07-review'}
SCENARIOS = ('idle', 'monotonic', 'monotonic_raw', 'monotonic_coarse')
LABELS = dict(zip(SCENARIOS, ('idle', 'MONOTONIC', 'RAW', 'COARSE')))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_write(name, rows):
    with (HERE / name).open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    reports, binding, observations, effects = {}, {}, [], []
    cell_means, cell_peaks = defaultdict(list), defaultdict(list)
    boot_ids = []
    samples = 0
    for config, source in SOURCES.items():
        report = json.loads((source / 'report.json').read_text())
        verified = json.loads((source / 'matrix-verification.json').read_text())
        assert report['complete_matrix'] and report['completed_boots'] == 8
        assert verified['status'] == 'PASS' and verified['stop_decision'] == 'STOP_PLANNED_MATRIX'
        assert verified['report_sha256'] == sha(source / 'report.json')
        reports[config] = report
        binding[config] = dict(source=str(source.relative_to(HERE.parent)),
                               report_sha256=sha(source / 'report.json'),
                               verification_sha256=sha(source / 'matrix-verification.json'),
                               samples=verified['periodic_samples'])
        samples += verified['periodic_samples']
        lookup = {}
        for run in report['runs']:
            boot_ids.append(run['boot_id'])
            assert run['case'].endswith('-' + config.lower())
            step = run['step']
            for scenario in SCENARIOS:
                stats = run['summaries'][scenario]
                key = (config, step['backend'], step['recorder'], scenario)
                cell_means[key].append(stats['mean'])
                cell_peaks[key].append(run['distributions'][scenario]['3']['dominant_peak'])
                lookup[step['block'], step['backend'], step['recorder'], scenario] = stats['mean']
                observations.append(dict(config=config, backend=step['backend'], recorder=step['recorder'],
                    block=step['block'], boot_id=run['boot_id'], scenario=scenario,
                    **{k: stats[k] for k in ('count', 'mean', 'median', 'p95', 'p99', 'maximum')},
                    **{f'peak_sigma_{s}': run['distributions'][scenario][str(s)]['dominant_peak'] for s in (2, 3, 5)}))
        for row in report['block_comparisons']:
            block, scenario = row['block'], row['scenario']
            deltas = {rec: lookup[block, 'vkso', rec, scenario] - lookup[block, 'raw', rec, scenario]
                      for rec in ('current', 'legacy')}
            interaction = deltas['current'] - deltas['legacy']
            assert abs(interaction - row['current_minus_legacy_mean_delta']) < 1e-9
            effects.append(dict(config=config, block=block, scenario=scenario,
                                current_delta=deltas['current'], legacy_delta=deltas['legacy'],
                                recorder_interaction=interaction,
                                peak_interaction_sigma3=row['current_minus_legacy_peak_delta']))
    assert len(boot_ids) == len(set(boot_ids)) == 16 and samples == 511996
    assert len(observations) == 64 and len(effects) == 16
    config_changes = []
    for backend in ('raw', 'vkso'):
        for recorder in ('current', 'legacy'):
            for scenario in SCENARIOS:
                keys = [(config, backend, recorder, scenario) for config in SOURCES]
                normal, no_retpoline = [cell_means[k] for k in keys]
                assert len(normal) == len(no_retpoline) == 2
                all_pairs = [x - y for x in normal for y in no_retpoline]
                config_changes.append(dict(backend=backend, recorder=recorder, scenario=scenario,
                    normal_equal_boot_mean=mean(normal), no_retpoline_equal_boot_mean=mean(no_retpoline),
                    normal_minus_no_retpoline=mean(normal) - mean(no_retpoline),
                    observed_cross_boot_min=min(all_pairs), observed_cross_boot_max=max(all_pairs),
                    normal_peaks_sigma3=cell_peaks[keys[0]], no_retpoline_peaks_sigma3=cell_peaks[keys[1]]))
    csv_write('per-boot-costs.csv', observations)
    csv_write('backend-and-recorder-effects.csv', effects)
    csv_write('configuration-contrasts.csv', config_changes)
    result = dict(status='PASS', sources=binding, boots=16, samples=samples, boot_ids=boot_ids,
                  observations=observations, effects=effects, configuration_contrasts=config_changes,
                  script_sha256=sha(Path(__file__)),
                  scope='Two boots per backend/recorder/configuration; separate collection periods. '
                        'Configuration groups differ in multiple mitigation options. Cross-boot ranges '
                        'are observed combinations, not confidence intervals or causal retpoline effects.')
    (HERE / 'comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# 两配置完整软件发布：证据汇总', '',
        '两项固定矩阵均已完成并停止：16次不同启动、256窗、511,996周期样本，每后端/记录器/配置两次启动。'
        'Normal为255,999样本，no-retpoline为255,997样本；两项分别完成原CSV、归档与功能/恢复核验。'
        '本汇总不新增采集，不替代所要求的物理机制解释。', '',
        '## 记录器是否改变后端比较', '',
        'D=(VKSO−Raw)Current−(VKSO−Raw)Legacy，单位TSC ticks。分别显示两块，不能将块间符号翻转平均掉。', '',
        '| 配置 | 负载 | D第一块 | D第二块 | 两块等权D | σ=3峰位D：第一/第二块 |',
        '| --- | --- | ---: | ---: | ---: | --- |']
    for config in SOURCES:
        for scenario in SCENARIOS:
            rows = sorted((x for x in effects if x['config'] == config and x['scenario'] == scenario), key=lambda x: x['block'])
            values = [x['recorder_interaction'] for x in rows]
            lines.append(f'| {config} | {LABELS[scenario]} | ' + ' | '.join(f'{x:+.4f}' for x in values + [mean(values)])
                         + ' | ' + ' / '.join(f"{x['peak_interaction_sigma3']:+d}" for x in rows) + ' |')
    lines += ['',
        'Normal四负载D均在两块为负；no-retpoline的idle/RAW为负、MONOTONIC为正，COARSE则翻转。'
        '尤其MONOTONIC的记录器相对效应在两配置中方向相反，不能把记录器误差建模为跨配置通用常数。'
        'no-retpoline COARSE两块等权D接近零不能支持测量无影响。', '',
        'Normal COARSE第一块峰位D对带宽敏感（σ=2/3/5为+187/+186/+53），第二块为+53/+53/+51；'
        'no-retpoline默认峰位D为+82/+81。峰位、完整均值、占比和尾部必须分别报告，不能强行对应同一物理峰。', '',
        '## 实际发布成本', '',
        '下表为两次启动各自完整样本均值的等权平均，另列两次启动均值的观察范围，不是置信区间。'
        '逐启动样本数、中位数、p95/p99、最大值及三个带宽主峰见per-boot-costs.csv；全部尾部保留。', '',
        '| 配置 | 后端 | 记录器 | 负载 | 等权均值 | 两次启动均值范围 |',
        '| --- | --- | --- | --- | ---: | --- |']
    for config in SOURCES:
        for backend in ('raw', 'vkso'):
            for recorder in ('current', 'legacy'):
                for scenario in SCENARIOS:
                    values = cell_means[config, backend, recorder, scenario]
                    lines.append(f'| {config} | {backend.upper() if backend == "vkso" else "Raw"} | {recorder.title()} | '
                                 f'{LABELS[scenario]} | {mean(values):.3f} | {min(values):.3f}～{max(values):.3f} |')
    lines += ['', '## 跨配置变化的适用范围', '',
        'configuration-contrasts.csv逐后端/记录器/负载给出Normal−no-retpoline等权均值差、四种跨启动组合的观察范围和两次主峰。'
        '两个矩阵在不同时段采集，块编号相同不表示同一时刻配对；配置组涉及多个缓解选项，不能单独归因于retpoline。', '',
        '计时覆盖完整软件发布路径：序列开始、UPDATE、正式timekeeper复制和最终序列结束，记录追加位于终点后。'
        '沿用原RDTSCP计时约定，不等于存储全局可见或读者观察到发布的延迟；也不是旧函数内窗口与新窗口相减后的“复制成本”。', '',
        '现有证据已证明记录器改变相对比较，且该效应依赖配置与分布部分。两配置各自的条件成本、占比、分位秩尾部贡献和完整ECDF均已保存。'
        '自然多峰形成、VKSO/Raw占比差和缓解配置峰位差仍缺唯一物理机制证据；已停止的布局、节流及排序先导不因此自动追加。', '',
        '- [Normal完整证据](../full-publication-recorder-normal/step-07-review/interpretation.md)。',
        '- [no-retpoline完整证据](../full-publication-recorder-control/step-07-review/interpretation.md)。',
        '- [逐启动成本](per-boot-costs.csv)、[后端及记录器效应](backend-and-recorder-effects.csv)、[配置变化](configuration-contrasts.csv)。',
        '- [结构化汇总与来源绑定](comparison.json)，由本目录summarize.py复现。', '']
    (HERE / 'README.md').write_text('\n'.join(lines))
    print(json.dumps(dict(status='PASS', boots=16, samples=samples, cost_rows=len(observations), effect_rows=len(effects))))


if __name__ == '__main__':
    main()
