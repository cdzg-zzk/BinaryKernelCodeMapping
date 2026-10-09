#!/usr/bin/env python3
"""Read-only transcription and scope audit of the canonical Clocktime section.

Uses the previously audited evidence tables, not a new benchmark run. Prints JSON;
redirect it to clocktime-manuscript-check.json to retain the check result.
"""
import csv
import json
import re
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
B = ROOT / 'test/test_gettime/vkso-tests'
E = B / 'update-bench/mechanism-evidence'
DOC = ROOT / 'paper/paper_content/Paper Draft.md'
text = DOC.read_text()
section = text.split('## Stateful System Case: Consolidating Kernel and vDSO Time Reads\n', 1)[1].split('## Registration and Mapping Behavior', 1)[0]
appendix = text.split('# Appendix C: Clocktime Implementation and Performance Details\n', 1)[1]
checks = {}

def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))

# Resolve tables by scientific role/title, independent of main/appendix numbering.
TABLE_TITLES = {
    '10(a)': 'Matched Clocktime source slices',
    '10(b)': 'Binary components in the measured READ images',
    '12(a)': 'Normal user clock_gettime and kernel READ',
    '12(b)': 'no-retpoline user clock_gettime and kernel READ',
    '13(a)': 'Normal other public paths and fallback',
    '13(b)': 'no-retpoline other public paths and fallback',
    '14': 'Complete software publication cost',
    '15': 'Backend publication cost differences',
    '16': 'Publication tail cost with the Current recorder',
    '17': 'Increase in publication cost under continuous reads',
    'recorder': 'Backend differences and recorder interaction',
    'main_source': 'Shared implementation and maintenance responsibilities',
    'main_update': 'Complete publication cost with the Current recorder',
}

def mdtable(label):
    title = re.escape(TABLE_TITLES[label])
    matches = list(re.finditer(r'\*\*Table [^:]+: ' + title + r'\.\*\*', text))
    assert len(matches) == 1, (label, len(matches))
    after = text[matches[0].end():]
    block = re.search(r'(?m)^\| .*\n(?:\|.*\n)+', after).group()
    return [[c.strip().replace('**', '') for c in line.strip().strip('|').split('|')] for line in block.splitlines()][2:]

def number(value):
    return float(value.replace(',', ''))

def close(shown, expected):
    assert abs(number(shown) - float(expected)) <= 0.00050001, (shown, expected)

# Reconstruct SLOC from the individual counted source locations.
source = rows(B / 'code-size/current-evidence/source-lines.csv')
counts = Counter((r['system'], r['scope'], r['category']) for r in source)
category_order = ['user_computation', 'kernel_computation', 'shared_computation', 'data_abi', 'user_adapter_provider', 'kernel_adapter', 'publisher', 'mapping_namespace', 'provider_integration', 'integration', 'build', 'getcpu']
t = mdtable('10(a)')
for row, category in zip(t[:12], category_order):
    for col, system in enumerate(['Raw', 'VKSO'], 1):
        assert number(row[col]) == counts[system, 'feature', category]
for col, system in enumerate(['Raw', 'VKSO'], 1):
    feature = sum(v for (s, scope, _), v in counts.items() if s == system and scope == 'feature')
    retained = sum(v for (s, scope, _), v in counts.items() if s == system and scope == 'retained')
    expected = [feature, retained, feature + retained, sum(v for (s, scope, _), v in counts.items() if s == system and scope == 'common'), sum(v for (s, scope, _), v in counts.items() if s == system and scope == 'infrastructure')]
    assert [number(r[col]) for r in t[12:]] == expected
checks['source_table'] = '17 rows checked against individual source-line ownership'

# The main table reports maintenance responsibilities. Full costs include retained
# readers and keep measured/refactored source identities separate in Appendix C2.
main_source = mdtable('main_source')
assert len(main_source) == 3
assert '同一份9个结构定义' in main_source[1][1]
refactor = json.loads((B / 'code-size/adapter-evidence/report.json').read_text())
assert refactor['status'] == 'PASS'
assert refactor['source_counts']['delta'] == -63
assert sum(r['delta'] for r in refactor['source_counts']['files']) == -63
expected_candidate = [int(number(r[2])) for r in t]
expected_candidate[3] += 5
expected_candidate[4] -= 68
expected_candidate[12] -= 63
expected_candidate[14] -= 63
assert [number(r[3]) for r in t] == expected_candidate
assert expected_candidate[14] == refactor['source_counts']['totals']['VKSO_refactored']['including_retained'] == 1708
assert refactor['compilation']['abi_structures'] == 9
assert refactor['compilation']['abi_layout_entries'] == 45
assert len(refactor['compilation']['kernel_translation_units']) == 7
assert '以下READ与发布性能对应ABI合并前的实验产物' in section
assert '增加137行' not in text
checks['maintenance_and_refactor'] = 'main responsibility table and all 17 refactored-source cells checked; required fallback included; performance revision separate'

# Binary table uses two distinct size conventions, retained in its caption.
binary = rows(B / 'code-size/current-evidence/binary-summary.csv')
sections = rows(B / 'code-size/current-evidence/binary-sections.csv')
t = mdtable('10(b)')
metrics = ['11 ordinary kernel entry extents', 'native time/getcpu vDSO symbols', 'shared time/getcpu function bodies', None, 'direct/libvkso_time.so .text', 'carrier shared backing: count once with kernel executable sections', 'carrier user private executable sections']
for i, metric in enumerate(metrics):
    for col, (variant, system) in enumerate([('normal', 'Raw'), ('normal', 'VKSO'), ('no-retpoline', 'Raw'), ('no-retpoline', 'VKSO')], 1):
        if t[i][col] == '—':
            continue
        if metric is None:
            found = [r for r in sections if r['variant'] == variant and r['system'] == system and r['section'] == '.text' and r['artifact'] != 'kernel' and int(r['bytes']) == 1853]
        else:
            found = [r for r in binary if r['variant'] == variant and r['system'] == system and r['metric'] == metric]
        assert len(found) == 1, (variant, system, metric, found)
        assert number(t[i][col]) == int(found[0]['bytes'])
checks['binary_table'] = 'all populated cells bound to measured artifact summaries'

# Exhaustive READ rows, including uncertainty and complete mean (no selected rows).
summary = rows(B / 'direct-api/read-evidence/summary.csv')
boots = rows(B / 'direct-api/read-evidence/boot-statistics.csv')
assert len(summary) == 38 and len(boots) == 304
assert sum(int(r['batches']) for r in boots) == 9424
assert len({r['boot_id'] for r in boots}) == 16
for variant, suffix in [('normal', 'a'), ('no-retpoline', 'b')]:
    for main, table_id in [(True, '12'), (False, '13')]:
        expected = [r for r in summary if r['variant'] == variant and (r['domain'] == 'kernel' or r['category'] == 'clock_gettime_fast') == main]
        printed = mdtable(f'{table_id}({suffix})')
        assert len(printed) == len(expected)
        for line, r in zip(printed, expected):
            for col, key in [(1, 'raw_ticks'), (2, 'vkso_ticks'), (3, 'delta_ticks'), (5, 'mean_delta')]:
                close(line[col], r[key])
            ci = line[4].strip('[]').split(', ')
            close(ci[0], r['delta_ci95_low']); close(ci[1], r['delta_ci95_high'])
            samples = [x for x in boots if x['variant'] == variant and x['api'] == r['api'] and x['domain'] == r['domain']]
            for method, key in [('raw', 'raw_ticks'), ('vkso', 'vkso_ticks')]:
                selected = [x for x in samples if x['method'] == method]
                assert len(selected) == 4
                assert abs(statistics.median(float(x['median']) for x in selected) - float(r[key])) < 1e-9
checks['read'] = '38 rows / 228 numbers; medians reconstructed from 304 boot-interface summaries'

# Complete publication and recorder contrasts; independent boots remain the unit.
publication = rows(E / 'full-publication-two-configurations/per-boot-costs.csv')
assert len(publication) == 64 and len({r['boot_id'] for r in publication}) == 16
assert sum(int(r['count']) for r in publication) == 511996
assert not ({r['boot_id'] for r in publication} & {r['boot_id'] for r in boots})
scenarios = ['idle', 'monotonic', 'monotonic_raw', 'monotonic_coarse']
for line in mdtable('14'):
    config, backend, recorder = line[:3]
    for i, scenario in enumerate(scenarios, 3):
        samples = [r for r in publication if r['config'] == config and r['backend'] == backend.lower() and r['recorder'] == recorder.lower() and r['scenario'] == scenario]
        assert len(samples) == 2
        close(line[i], statistics.mean(float(r['mean']) for r in samples))
name_map = dict(zip(['idle', 'MONOTONIC', 'RAW', 'COARSE'], scenarios))
for line in mdtable('15'):
    config, name = line[:2]
    expected = []
    for block in ['0', '1']:
        cells = {(r['backend'], r['recorder']): float(r['mean']) for r in publication if r['config'] == config and r['scenario'] == name_map[name] and r['block'] == block}
        current = cells['vkso', 'current'] - cells['raw', 'current']
        legacy = cells['vkso', 'legacy'] - cells['raw', 'legacy']
        if name != 'idle':
            assert current < 0 and legacy < 0
        expected.append([current, legacy, current - legacy])
    for column in range(2):
        for block, value in enumerate(line[column + 2].split(' / ')):
            close(value, expected[block][column])
checks['publication'] = '32 appendix means and 32 backend contrasts recalculated from 64 boot-load summaries'

# Main headline table: complete Current means, including idle, plus exact ratios.
main_update = mdtable('main_update')
assert len(main_update) == 8
full_names = {'idle':'idle','MONOTONIC':'monotonic','MONOTONIC_RAW':'monotonic_raw','MONOTONIC_COARSE':'monotonic_coarse'}
reductions=[]
for line in main_update:
    config, name = line[:2]
    costs = {}
    for col, backend in [(2,'raw'),(3,'vkso')]:
        selected=[r for r in publication if r['config']==config and r['scenario']==full_names[name] and r['backend']==backend and r['recorder']=='current']
        assert len(selected)==2
        costs[backend]=statistics.mean(float(r['mean']) for r in selected)
        close(line[col],costs[backend])
    delta=(costs['vkso']/costs['raw']-1)*100
    assert abs(float(line[4].strip('%'))-delta)<0.0050001
    if name!='idle': reductions.append(-delta)
assert f'{min(reductions):.2f}%～{max(reductions):.2f}%' in text
checks['main_update'] = 'all eight Current cells and percentages verified; loaded range from unrounded means'

# Tail distributions and load response, reconstructed from each boot.
for line in mdtable('16'):
    config, name = line[:2]
    for column, (key, backend) in enumerate([('p95','raw'),('p95','vkso'),('p99','raw'),('p99','vkso')], 2):
        expected = sorted([r for r in publication if r['config'] == config and r['backend'] == backend and r['recorder'] == 'current' and r['scenario'] == name_map[name]], key=lambda r: int(r['block']))
        assert len(expected) == 2
        for shown, r in zip(line[column].split(' / '), expected):
            close(shown, r[key])
for line in mdtable('17'):
    config, recorder = line[:2]
    for col, scenario in enumerate(scenarios[1:], 2):
        for shown, backend in zip(line[col].split(' / '), ['raw', 'vkso']):
            selected = [r for r in publication if r['config'] == config and r['backend'] == backend and r['recorder'] == recorder.lower()]
            increments = []
            for block in ['0','1']:
                cells = {r['scenario']:float(r['mean']) for r in selected if r['block'] == block}
                increments.append(cells[scenario] - cells['idle'])
            close(shown, statistics.mean(increments))
        raw, vkso = map(float, line[col].split(' / '))
        assert vkso < raw
checks['tail_and_load'] = '64 per-boot p95/p99 values and 24 load increments reconstructed'
# Appendix retains every recorder interaction that materially affects comparison.
app_rows = mdtable('recorder')
assert len(app_rows) == 8
for line in app_rows:
    config, name = line[:2]
    for block, shown in enumerate(line[4].split(' / ')):
        cells = {(r['backend'],r['recorder']):float(r['mean']) for r in publication if r['config']==config and r['scenario']==name_map[name] and int(r['block'])==block}
        close(shown,(cells['vkso','current']-cells['raw','current'])-(cells['vkso','legacy']-cells['raw','legacy']))
checks['recorder_appendix'] = 'all 16 recorder interactions preserved and checked'

mechanism = rows(B / 'code-size/current-evidence/mechanism-boots.csv')
pfns = rows(B / 'code-size/current-evidence/shared-pages.csv')
interfaces = rows(B / 'code-size/current-evidence/interfaces.csv')
assert len(mechanism) == 8 and len(pfns) == 20
assert all(r['user_pfn'] == r['kernel_pfn'] and r['result'] == 'PASS' for r in pfns)
assert all(all(r[k] == 'PASS' for k in ['public_api', 'selected_fast_path_denial', 'abi_namespace_lifecycle', 'pfn_identity']) for r in mechanism)
assert Counter(r['mode'] for r in interfaces if r['domain'] == 'kernel')['shared_code'] == 8
assert Counter(r['mode'] for r in interfaces if r['domain'] == 'kernel')['shared_state_only'] == 3
maintenance = json.loads((B / 'code-size/current-evidence/maintenance-validation.json').read_text())
assert maintenance['cases'] == 100100 and len(maintenance['production_functions_changed']) == 2
assert all(maintenance[k] == [] for k in ['user_adapter_functions_changed', 'kernel_adapter_functions_changed', 'publisher_functions_changed', 'mapping_functions_changed'])
checks['mechanism_and_maintenance'] = '8 shared-compute / 3 shared-state kernel entries; 8 boot records; 20 PFNs; actual 2-function maintenance case'

link_count = 0
for target in re.findall(r'\]\(([^)]+)\)', section + appendix):
    if '://' in target or target.startswith('#'):
        continue
    assert (DOC.parent / target.split('#')[0]).exists(), target
    link_count += 1
assert '3.87%' not in text and '2.57%' not in text
assert text.count('## Stateful System Case:') == 1 and text.count('# Appendix C:') == 1
assert '### A Stateful Case for Cross-domain Reuse' in section and '### From Separate Readers to a Shared Execution Body' in section
assert all(term not in section + appendix for term in ['尚未分别识别', 'STOP_', '机制先导', '双峰根因'])
assert '功能切片合计' in appendix and '记录器' in appendix and 'x86-64 LP64' in section
assert json.loads((E / 'context-backend-followup/reboot-readiness.json').read_text())['requires_user_reboot'] is False
checks['links_and_scope'] = f'{link_count} local targets exist; old headline percentages removed; scope/design/sharing/performance present; material recorder comparison retained; reboot remains withdrawn'
print(json.dumps({'status':'PASS_MANUSCRIPT_TRANSCRIPTION_AND_SCOPE', 'manuscript':str(DOC.relative_to(ROOT)), 'checks':checks, 'scope':'Document and existing evidence tables only. No new experiment; no claim that unresolved physical mechanisms were identified. Scope, design rationale and performance interpretation receive a separate editorial review.'},ensure_ascii=False,indent=2))
