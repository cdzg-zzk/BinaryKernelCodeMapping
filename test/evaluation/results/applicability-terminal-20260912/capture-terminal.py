#!/usr/bin/env python3
"""Capture and cross-check terminal records from the original static campaign.

This reads existing logs and process metadata only. It never imports or starts
the checker. Large terminal logs remain at their original location; selected
numbered lines and input identity are preserved instead of a full copy.
"""
import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


FIELDS = {
    'visited_functions': '已访问函数',
    'shim_hits': 'Shim 命中数',
    'static_references': '静态数据/地址引用数',
    'indirect_control_flow_sites': '间接控制流命中数',
    'instrumentation_sites': '编译器插桩命中数',
    'hard_failures': '致命失败数',
    'missing_symbols': '丢失符号数',
    'unanalyzable_functions': '不可分析函数数',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent.parent / 'applicability-static-20260912')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    def save(name, value):
        path = args.output / name
        if not isinstance(value, (bytes, str)):
            value = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
        path.write_bytes(value if isinstance(value, bytes) else value.encode())

    def identity(path, data):
        stat = path.stat()
        return dict(path=str(path.resolve()), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                    mtime_ns=stat.st_mtime_ns)

    captured = datetime.now(timezone.utc).isoformat()
    campaign_bytes = (args.source / 'results.json').read_bytes()
    campaign = json.loads(campaign_bytes)
    save('campaign-results.json', campaign_bytes)
    for name in ('identity.json', 'candidate-manifest.json'):
        save('campaign-' + name, (args.source / name).read_bytes())
    children = subprocess.run(['pgrep', '-P', '14474'], capture_output=True, text=True)
    assert children.returncode in (0, 1), children.stderr
    child_pids = [int(value) for value in children.stdout.split()]
    process = subprocess.run(['ps', '-p', ','.join(map(str, [14474, 15248, *child_pids])),
                              '-o', 'pid,ppid,stat,lstart,etime,args'], capture_output=True, text=True)
    assert process.returncode in (0, 1), process.stderr
    save('process-at-capture.txt', process.stdout)
    audit = []
    for item in campaign:
        name = item['id']
        result_path = args.source / name / 'result.json'
        result_bytes = result_path.read_bytes()
        assert json.loads(result_bytes) == item, name
        save(name + '-result.json', result_bytes)
        assert len(item['checks']) == 1, name
        check = item['checks'][0]
        log_path = args.source / name / f'checker-{name}.log'
        raw = log_path.read_bytes()
        lines = raw.decode().splitlines()
        clean = [re.sub(r'\x1b\[[0-9;]*m', '', line) for line in lines]
        text = '\n'.join(clean)
        counts = {}
        for field, label in FIELDS.items():
            found = re.findall(r'^  - ' + re.escape(label) + r': (\d+)$', text, re.M)
            assert len(found) == 1, (name, field, found)
            counts[field] = int(found[0])
            assert counts[field] == check[field], (name, field, counts[field], check[field])
        verdicts = re.findall(r'^\[最终结论\] (PASS|FAIL|INCOMPLETE) \(exit code: (\d+)\)$', text, re.M)
        assert len(verdicts) == 1, (name, verdicts)
        verdict, exit_code = verdicts[0]
        assert int(exit_code) == check['exit_code'], name
        expected_verdict = 'FAIL' if counts['hard_failures'] else (
            'INCOMPLETE' if counts['missing_symbols'] or counts['unanalyzable_functions'] else 'PASS')
        assert verdict == expected_verdict, (name, verdict, expected_verdict)
        assert check['status'] == {'PASS': 'checker_pass', 'FAIL': 'checker_fail',
                                   'INCOMPLETE': 'checker_incomplete'}[verdict], check
        summary_start = clean.index('[摘要]')
        selected = set(range(summary_start - 3, summary_start + 10))
        selected.update(range(max(0, len(lines) - 3), len(lines)))
        hard_types = Counter()
        hard_examples = {}
        unresolved = []
        for index, line in enumerate(clean):
            if '崩溃类型: ' in line:
                full_type = line.split('崩溃类型: ', 1)[1]
                kind = full_type.split(' (', 1)[0]
                hard_types[kind] += 1
                examples = hard_examples.setdefault(kind, [])
                if len(examples) < 2:
                    examples.append(dict(line=index + 1, text=line))
                    selected.update(range(index, min(len(lines), index + 3)))
            match = re.match(r'    \* \[([^]]+)\] ([^:]+): (.*?) \((.*)\)$', line)
            if match:
                owner, function, reason, detail = match.groups()
                unresolved.append(dict(line=index + 1, owner=owner, function=function,
                                       reason=reason, detail=detail))
                if len(unresolved) <= 3:
                    selected.add(index)
        assert sum(hard_types.values()) == counts['hard_failures'], name
        assert len(unresolved) == counts['unanalyzable_functions'], name
        if len(raw) <= 100000:
            save(name + '-checker.log', raw)
            archived_log = name + '-checker.log'
        else:
            archived_log = name + '-selected-log-lines.txt'
            save(archived_log, ''.join(f'{n + 1}: {lines[n]}\n' for n in sorted(selected) if 0 <= n < len(lines)))
        save(name + '-effective-shim.txt', (args.source / name / 'effective-shim.txt').read_bytes())
        audit.append(dict(id=name, log_identity=identity(log_path, raw), original_log_lines=len(lines),
                          archived_log=archived_log, summary_matches_result=True,
                          candidate_matches_campaign=True, verdict=verdict, exit_code=int(exit_code),
                          counts=counts, hard_failure_kinds=dict(hard_types), hard_failure_examples=hard_examples,
                          unanalyzable_records=len(unresolved),
                          unanalyzable_distinct_functions=len({(row['owner'], row['function']) for row in unresolved}),
                          unanalyzable_reasons=dict(Counter(row['reason'] for row in unresolved)),
                          scope='Static checker result only; diagnostic record counts are not unique-function counts or runtime outcomes.'))
    manifest = json.loads((args.output / 'campaign-candidate-manifest.json').read_text())
    completed = {row['id']: row for row in audit}
    children_commands = []
    active_targets = set()
    for pid in child_pids:
        try:
            argv = Path('/proc', str(pid), 'cmdline').read_bytes().decode().rstrip('\0').split('\0')
            children_commands.append(dict(pid=pid, argv=argv))
            if '-t' in argv:
                active_targets.add(argv[argv.index('-t') + 1])
        except FileNotFoundError:
            children_commands.append(dict(pid=pid, state='exited during read-only capture'))
    matrix = []
    for candidate in manifest['cases']:
        if candidate['cohort'] != 'prospective':
            continue
        name = candidate['id']
        log_path = args.source / name / f'checker-{name}.log'
        result_exists = (args.source / name / 'result.json').exists()
        if name in completed:
            state = 'checker_' + completed[name]['verdict'].lower()
        elif name in active_targets:
            state = 'running'
        elif log_path.exists():
            state = 'started_without_captured_terminal_result'
        else:
            state = 'not_started'
        matrix.append(dict(id=name, state=state, terminal_result_file_exists=result_exists,
                           log_exists=log_path.exists(), runtime='not_attempted',
                           allow_carrier_attempt=candidate['allow_carrier_attempt']))
    save('matrix-at-capture.json', dict(captured_utc=captured, atomic_snapshot=False,
                                      child_commands=children_commands, cases=matrix))
    checker = Path(__file__).resolve().parents[4] / 'kernel_cgd/function_checker/functions_checker.py'
    checker_bytes = checker.read_bytes()
    checker_lines = checker_bytes.decode().splitlines()
    ranges = [(218, 227), (710, 723), (801, 813)]
    save('checker-verdict-source.txt', ''.join(f'{n}: {checker_lines[n - 1]}\n'
                                             for start, end in ranges for n in range(start, end + 1)))
    save('checker-source-identity.json', dict(**identity(checker, checker_bytes), ranges=ranges))
    save('terminal-audit.json', dict(status='PASS', captured_utc=captured,
                                   campaign_result_identity=identity(args.source / 'results.json', campaign_bytes),
                                   terminal_candidates=len(campaign), observed_child_pids=child_pids,
                                   whole_eight_terminal=len(campaign) == 8, candidates=audit))
    print(json.dumps(dict(captured_utc=captured, terminal_candidates=len(campaign),
                          observed_child_pids=child_pids, verdicts={row['id']: row['verdict'] for row in audit}), indent=2))


if __name__ == '__main__':
    main()
