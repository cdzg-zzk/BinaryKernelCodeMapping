#!/usr/bin/env python3
"""Expose the existing LKL heap-size pilot instead of treating 512 MiB as a minimum."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

ROOT=Path(__file__).resolve().parents[4]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    rows=[];inputs=[]
    for codec in ['gzip','xz','lz4']:
        run=ROOT/f'test/evaluation-local/runs/iso9660/squash-application-{codec}-pilot-02/benchmark'
        state=json.loads((run/'result.json').read_text());assert state['status']=='complete' and state['pilot']
        samples=[json.loads(l) for l in (run/'samples.jsonl').read_text().splitlines()]
        resources=json.loads((run/'resources.json').read_text())
        inputs.append(dict(run=str(run),samples_sha256=hashlib.sha256((run/'samples.jsonl').read_bytes()).hexdigest()))
        for heap in [16,64,256,512]:
            variant=f'lkl-{heap}'
            selected=[r for r in samples if r['variant']==variant]
            assert {r['workload'] for r in selected}=={'startup','scan','archive','stream'}
            memory=resources[variant]['after']['helper']['memory']
            rows.append(dict(codec=codec,heap_mib=heap,all_tasks_passed=True,
                blocks=state['blocks'],repeats=state['repeats'],
                task_median_seconds={w:statistics.median(r['wall_seconds'] for r in selected if r['workload']==w) for w in state['workloads']},
                helper_after_include_archive_rss_kib=memory['Rss'],
                helper_after_include_archive_pss_kib=memory['Pss'],threads=memory['Threads']))
    stock=ROOT/'test/section65/build/squashfs/apptainer/jammy/usr/libexec/apptainer/bin/squashfuse_ll'
    help_text=subprocess.run([stock,'--help'],capture_output=True,text=True).stderr
    if not help_text:help_text=subprocess.run([stock,'--help'],capture_output=True,text=True).stdout
    (out/'squashfuse-help.txt').write_text(help_text)
    result=dict(status='complete',inputs=inputs,lkl_heap_pilot=rows,
        interpretation='All four tested heaps complete all tasks. 512 MiB is a performance-oriented evaluation configuration, not a minimum memory requirement. These exploratory pilots have only one campaign per codec (gzip four blocks, xz/lz4 one); report descriptive timings, not confirmatory confidence intervals. Memory snapshots follow include archive, not the sequential workload peak.',
        stock=dict(path=str(stock),sha256=hashlib.sha256(stock.read_bytes()).hexdigest(),
            single_thread_option='-s',default='multithreaded low-level FUSE frontend',
            diagnostic='Retain default deployment and add the same executable with -s; record actual helper thread counts in resource snapshots.'))
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Existing LKL heap-size pilot','',result['interpretation'],'',
           '| Codec | Heap MiB | Startup s | Scan s | Archive s | Stream s | PSS MiB after include archive |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        t=r['task_median_seconds']
        lines.append(f"| {r['codec']} | {r['heap_mib']} | {t['startup']:.4f} | {t['scan']:.4f} | {t['archive']:.4f} | {t['stream']:.4f} | {r['helper_after_include_archive_pss_kib']/1024:.2f} |")
    (out/'heap-pilot.md').write_text('\n'.join(lines)+'\n')
    tex=[r'\begin{table}[h]\centering\small',
        r'\caption{Exploratory LKL heap pilot: all settings complete all four tasks. Gzip has four blocks; xz/lz4 have one. Times are descriptive medians. PSS follows the include archive, not a sequential-task peak.}',
        r'\begin{tabular}{lrrrrrr}\toprule Codec & Heap MiB & Startup s & Scan s & Archive s & Stream s & PSS MiB \\ \midrule']
    for r in rows:
        t=r['task_median_seconds']
        tex.append(f"{r['codec']} & {r['heap_mib']} & {t['startup']:.3f} & {t['scan']:.3f} & {t['archive']:.3f} & {t['stream']:.3f} & {r['helper_after_include_archive_pss_kib']/1024:.2f}"+r' \\')
    tex += [r'\bottomrule\end{tabular}\end{table}']
    (out/'heap-pilot.tex').write_text('\n'.join(tex)+'\n')
    print('audited',len(rows),'heap/codec pilot cells')


if __name__=='__main__':main()
