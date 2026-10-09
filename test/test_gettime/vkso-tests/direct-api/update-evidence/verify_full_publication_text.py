#!/usr/bin/env python3
"""Check complete-publication manuscript tables against the verified matrices."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parents[1] / 'update-bench/mechanism-evidence'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    text_path = HERE / 'evaluation-text.md'
    text = text_path.read_text()
    source = EVIDENCE / 'full-publication-two-configurations/comparison.json'
    data = json.loads(source.read_text())
    assert data['status'] == 'PASS' and data['samples'] == 511996
    scenarios = ('idle', 'monotonic', 'monotonic_raw', 'monotonic_coarse')
    labels = dict(zip(scenarios, ('idle', 'MONOTONIC', 'MONOTONIC_RAW', 'MONOTONIC_COARSE')))
    expected_costs, expected_effects = [], []
    for config in ('Normal', 'no-retpoline'):
        for recorder in ('current', 'legacy'):
            for backend in ('raw', 'vkso'):
                values = []
                for scenario in scenarios:
                    rows = [x for x in data['observations'] if (x['config'], x['recorder'], x['backend'], x['scenario'])
                            == (config, recorder, backend, scenario)]
                    assert len(rows) == 2 and len({x['boot_id'] for x in rows}) == 2
                    values.append(sum(x['mean'] for x in rows) / 2)
                expected_costs.append('| ' + ' | '.join([config, 'Raw' if backend == 'raw' else 'VKSO', recorder.title()]
                                                      + [f'{v:.3f}' for v in values]) + ' |')
        for scenario in scenarios:
            rows = sorted([x for x in data['effects'] if x['config'] == config and x['scenario'] == scenario],
                          key=lambda x: x['block'])
            assert len(rows) == 2
            expected_effects.append('| ' + ' | '.join([config, labels[scenario]] +
                [' / '.join(f'{row[key]:+.3f}' for row in rows)
                 for key in ('current_delta', 'legacy_delta', 'recorder_interaction')]) + ' |')
    cost_start = text.index('| 配置 | 后端 | 记录器 |')
    effect_start = text.index('| 配置 | 读取负载 |')
    def rows_from(start):
        return [line for line in text[start:].split('\n\n', 1)[0].splitlines()[2:] if line.startswith('|')]
    assert rows_from(cost_start) == expected_costs
    assert rows_from(effect_start) == expected_effects
    assert all(x['current_delta'] < 0 and x['legacy_delta'] < 0
               for x in data['effects'] if x['scenario'] != 'idle')
    assert all(x['recorder_interaction'] < 0 for x in data['effects'] if x['config'] == 'Normal')
    assert all(x['recorder_interaction'] > 0 for x in data['effects']
               if x['config'] == 'no-retpoline' and x['scenario'] == 'monotonic')
    normal = EVIDENCE / 'full-publication-recorder-normal/step-07-review'
    bindings = {}
    for block in (0, 1):
        path = normal / f'block-{block}-audit.json'
        audit = json.loads(path.read_text())
        assert audit['status'] == 'PASS'
        for row in audit['comparisons']:
            if row['scenario'] in ('monotonic_raw', 'monotonic_coarse'):
                assert row['rank_contributions'][0] < 0 < row['rank_contributions'][2]
                for value in (row['rank_contributions'][0], row['rank_contributions'][2]):
                    assert f'{value:+.3f}'.replace('-', '−') in text
        bindings[path.name] = sha(path)
    report = json.loads((normal / 'report.json').read_text())
    runs = {x['step']['index']: x for x in report['runs']}
    peaks = [[runs[i]['distributions']['monotonic_coarse'][str(s)]['dominant_peak'] for s in (2, 3, 5)]
             for i in (3, 4)]
    assert peaks == [[641, 641, 775], [772, 773, 774]]
    delta = runs[4]['summaries']['monotonic_coarse']['mean'] - runs[3]['summaries']['monotonic_coarse']['mean']
    assert f'{delta:.3f}' == '3.086' and '3.086 ticks' in text
    assert '完整发布矩阵覆盖no-retpoline配置' not in text
    result = dict(status='PASS', cost_table_rows=8, absolute_cost_values=32,
                  contrast_table_rows=8, contrast_values=48,
                  checked_claims=['all loaded backend deltas negative', 'Normal recorder effects negative in both blocks',
                                  'MONOTONIC recorder effects positive in no-retpoline',
                                  'Normal RAW/COARSE negative body and opposing top-1% contributions',
                                  'Normal Current Raw COARSE bandwidth-dependent dominant peaks and +3.086 mean change'],
                  text_sha256=sha(text_path), comparison_sha256=sha(source), normal_audits=bindings,
                  verifier_sha256=sha(Path(__file__)),
                  scope='Two added tables and listed new Normal/cross-configuration claims; not a re-audit of historical prose.')
    (HERE / 'full-publication-prose-binding.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
