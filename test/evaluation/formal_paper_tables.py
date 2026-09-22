#!/usr/bin/env python3
"""Render evidence tables from complete deployment summaries, preserving pairing."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import median


def csv_rows(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))


def render(directory, output, allow_partial=False, algorithms_only=False, applications_only=False):
    directory=Path(directory);output=Path(output)
    analysis=json.loads((directory/'analysis.json').read_text())
    assert analysis['status']=='complete' or allow_partial, 'paper tables require all complete deployments'
    source=csv_rows(directory/'deployment-ratios.csv')
    groups=defaultdict(list)
    for row in source:groups[row['algorithm'],row['domain'],row['workload'],row['baseline']].append(row)
    def result(algorithm,domain,workload,baseline):
        group=groups[algorithm,domain,workload,baseline]
        assert group and len({r['deployment'] for r in group})==len(group)
        ratios=[float(r['median_cost_ratio']) for r in group]
        return dict(ratio=median(ratios),minimum=min(ratios),maximum=max(ratios),deployments=len(group),
            native=median(float(r['median_baseline_value']) for r in group),
            vkso=median(float(r['median_target_value']) for r in group))
    def ratio(r):return f"{r['ratio']:.3f} [{r['minimum']:.3f}, {r['maximum']:.3f}]"
    sections={}; facts={}
    def table(key,caption,columns,rows):
        sections[key]='\n'.join([caption,'','| '+' | '.join(columns)+' |',
                                 '| '+' | '.join(['---']*len(columns))+' |',
                                 *['| '+' | '.join(map(str,row))+' |' for row in rows]])+'\n'
    if not applications_only:
        rows=[]
        for op in ('compress','decompress'):
            for block,label in ((4096,'4 KiB'),(65536,'64 KiB'),(1048576,'1 MiB')):
                workload=f'{op}/block={block}'
                r=result('lz4','user',workload,'kernel-userspace-libc')
                u=result('lz4','user',workload,'user-default')
                n=result('lz4','user',workload,'kernel-userspace-native')
                rows.append([op,label,f"{r['native']:.2f}",f"{r['vkso']:.2f}",ratio(r),ratio(n),ratio(u)])
                facts['lz4-user/'+workload]=r
        table('table-09','**Table 9: LZ4 component throughput and relative execution cost.** Absolute values are MB/s. Cost ratios invert paired throughput ratios; values above 1 mean slower VKSO execution. Brackets give the minimum and maximum deployment medians.',
              ['Operation','Block size','Same-source MB/s','VKSO MB/s','Cost / same-source libc','Cost / same-source native','Cost / upstream native'],rows)
        for t,number in ((4,10),(8,11)):
            rows=[]
            cases=[('init',-1),('encode',0)]+[(op,e) for op in ('decode-full','decode-precomputed') for e in range(t+1)]
            for op,e in cases:
                workload=f'm=13/t={t}/bytes=512/errors={e}/{op}'
                r=result('bch','user',workload,'kernel-native');u=result('bch','user',workload,'author-standalone')
                rows.append([op,'—' if e<0 else e,f"{r['native']:.2f}",f"{r['vkso']:.2f}",ratio(r),ratio(u)])
                facts['bch-user/'+workload]=r
            table(f'table-{number}',f'**Table {number}: BCH costs with m=13, t={t}, and 512-byte data.** Absolute values are medians of deployment medians, in ns/op. Ratios preserve within-round pairing; brackets span deployment medians. Init includes control creation and free.',
                  ['Operation','Errors','Native ns/op','VKSO ns/op','Cost / same-source','Cost / author'],rows)
        rows=[]
        for case in ('bash','libc.so.6','python3'):
            r=result('xz','user',case,'native');facts['xz-user/'+case]=r
            rows.append([case,f"{r['native']:.2f}",f"{r['vkso']:.2f}",ratio(r)])
        table('table-12','**Table 12: XZ Embedded throughput and relative execution cost.** Absolute values are MiB/s; ratios use cost direction, so values above 1 mean slower VKSO execution. Brackets span deployment medians.',
              ['Input','Native MiB/s','VKSO MiB/s','Cost / native'],rows)
        # Sum full-file times within the same round before comparing corpus costs.
        corpus=defaultdict(float);coverage=defaultdict(set)
        for row in csv_rows(directory/'observations.csv'):
            if row['algorithm']=='lz4' and row['domain']=='kernel':
                case,op,block=row['workload'].split('/')
                key=(row['deployment'],row['round'],op,block,row['backend'])
                corpus[key]+=float(row['value']);coverage[key].add(case)
        assert all(len(v)==12 for v in coverage.values())
        rows=[]
        for op in ('compress','decompress'):
            for block in (65536,1048576):
                per_baseline={}
                for baseline in ('matched-direct-kernel','stock-kernel'):
                    by_deployment=defaultdict(list);absolute=defaultdict(list)
                    for (dep,repeat,operation,bs,backend),value in corpus.items():
                        if operation==op and bs==f'block={block}' and backend=='owner-kernel':
                            native=corpus[dep,repeat,operation,bs,baseline]
                            by_deployment[dep].append(value/native);absolute[dep].append(value)
                    values=[median(v) for v in by_deployment.values()]
                    assert values
                    per_baseline[baseline]=dict(ratio=median(values),minimum=min(values),maximum=max(values),
                        deployments=len(values),vkso=median(median(v) for v in absolute.values()))
                r=per_baseline['matched-direct-kernel'];facts[f'lz4-kernel/{op}/{block}']=per_baseline
                rows.append(['LZ4',f'{op}, {block//1024} KiB',f"{r['vkso']/1e6:.3f} ms/corpus",ratio(r),ratio(per_baseline['stock-kernel'])])
        for case in ('bash','libc.so.6','python3'):
            workload=f'{case}/decompress/block=0'
            baseline = 'matched-build-kernel' if ('xz','kernel',workload,'matched-build-kernel') in groups else 'matched-direct-kernel'
            r=result('xz','kernel',workload,baseline);s=result('xz','kernel',workload,'stock-kernel')
            facts['xz-kernel/'+case]=dict(matched=r,stock=s)
            rows.append(['XZ',case,f"{r['vkso']/1e6:.3f} ms/file",ratio(r),ratio(s)])
        for t in (4,8):
            for op,e in (('encode',0),('decode-precomputed',0),('decode-precomputed',2),('decode-full',2)):
                workload=f'm=13/t={t}/bytes=512/errors={e}/{op}'
                r=result('bch','kernel',workload,'matched-source-kernel');s=result('bch','kernel',workload,'stock-kernel')
                facts['bch-kernel/'+workload]=dict(matched=r,stock=s)
                rows.append(['BCH',f't={t}, {op}, errors={e}',f"{r['vkso']:.2f} ns/op",ratio(r),ratio(s)])
        table('table-13','**Table 13: Execution costs of the actual kernel export owners.** Stock is the distribution implementation. XZ Matched retains the original Ubuntu algorithm, kernel CRC32 and feature configuration under owner code-generation options. LZ4/BCH controls retain their previously defined source adaptations. LZ4 sums all twelve full-file costs within each round. Brackets span three deployment medians; complete results remain in the accompanying CSV.',
              ['Algorithm','Workload','Owner cost','Owner / stock','Owner / control'],
              [[*row[:3], row[4], row[3]] for row in rows])
    if algorithms_only:
        return write_tables(output, analysis, sections, facts)
    rows=[]
    for op in ('compress','decompress'):
        for block in (65536,1048576):
            workload=f'{op}/block={block}'
            r=result('lz4','cli',workload,'same-source');u=result('lz4','cli',workload,'upstream-dso');s=result('lz4','cli',workload,'stock-cli')
            facts['cli/'+workload]=dict(matched=r,upstream=u,stock=s)
            rows.append([op,f'{block//1024} KiB',f"{r['native']/1e6:.2f}",f"{r['vkso']/1e6:.2f}",ratio(r),ratio(s)])
    table('table-28','**Table 24: Complete LZ4 CLI file workflows.** Times sum twelve file commands, in ms. Commands include process startup, framing and buffered file I/O; output is closed without fsync. Inputs are pre-read. Cost ratios retain matching rounds; brackets span deployment medians.',
          ['Operation','Block size','Same-source ms','VKSO ms','Cost / same-source','Cost / stock CLI'],rows)
    rows=[]
    for phase in ('active','ready'):
        for passes in (1,3):
            workload=f'{phase}/traced=0/passes={passes}'
            r=result('lz4','setup',workload,'native');facts['setup/'+workload]=r
            rows.append([phase,passes,f"{r['native']/1e6:.2f}",f"{r['vkso']/1e6:.2f}",ratio(r)])
    table('table-29','**Table 25: Complete LZ4 task cost with and without registration in the command.** Trace-off elapsed times are in ms and include full input, compression, decompression and validation. Active starts a new process under an existing registration; ready additionally registers and releases a constructed carrier. Offline construction is separate.',
          ['Registration scope','Corpus passes','Native ms','VKSO ms','Cost / native'],rows)
    # Shell stages and observer controls are reported separately, never subtracted.
    exports=[json.loads((Path(d)/'setup-export-audit.json').read_text()) for d in analysis['included_directories']
             if (Path(d)/'setup-export-audit.json').exists()]
    rows=[]
    for stage in ('krg','checker','header','carrier','install'):
        values=[r['construction_ns'][stage]/1e9 for r in exports];assert values
        facts['export/'+stage]=dict(median_seconds=median(values),minimum=min(values),maximum=max(values))
        rows.append([stage,f'{median(values):.3f}',f'[{min(values):.3f}, {max(values):.3f}]'])
    table('table-30','**Table 26: Offline LZ4 export stages.** Seconds are medians and ranges across complete deployments. Timings retain shell observer overhead and exclude owner compilation/loading. The benchmark application interval is excluded.',
          ['Stage','Median seconds','Deployment range'],rows)
    observer=[]
    for phase in ('active','ready'):
        for backend in ('native','vkso'):
            for passes in (1,3):
                values=[]
                for d in analysis['included_directories']:
                    path=Path(d)/f'results/setup-comparison-{phase}/comparison.json'
                    if not path.exists():continue
                    record=json.loads(path.read_text());pairs=defaultdict(dict)
                    for r in record['rows']:
                        if r['backend']==backend and r['iterations']==passes:pairs[r['repeat']][r['traced']]=r['total_ns']
                    assert len(pairs)==3 and all(set(p)=={False,True} for p in pairs.values())
                    values.append(median(p[True]/p[False] for p in pairs.values()))
                observer.append(dict(phase=phase,backend=backend,passes=passes,median=median(values),minimum=min(values),maximum=max(values)))
    facts['observer_trace_on_over_off']=observer
    stage_deployments=defaultdict(list);calibrations=[]
    for d in analysis['included_directories']:
        for phase in ('active','ready'):
            path=Path(d)/f'results/setup-comparison-{phase}/comparison.json'
            if not path.exists():continue
            record=json.loads(path.read_text());local=defaultdict(list)
            for r in record['rows']:
                if not r['traced'] or r['iterations']!=1:continue
                key=phase+'/'+r['backend']
                local[key+'/first_valid'].append(r['to_first_valid_ns'])
                events={e['name']:e['ns'] for e in r['events']}
                for stage in ('load','input','task','unload'):
                    local[key+'/'+stage].append(events[stage+'.end']-events[stage+'.begin'])
                if r['shell_events']:
                    shell={e['name']:e['ns'] for e in r['shell_events']}
                    local[key+'/registration_wrapper'].append(shell['manager.ready']-shell['manager.begin'])
                    local[key+'/release_wrapper'].append(shell['cleanup.end']-shell['cleanup.begin'])
            for key,values in local.items():
                assert len(values)==3;stage_deployments[key].append(median(values))
            if phase=='ready':
                values=[r['total_ns'] for r in record['clock_calibration']]
                assert len(values)==30;calibrations.append(median(values))
    facts['instrumented_one_pass_stages_ms']={key:dict(median=median(v)/1e6,minimum=min(v)/1e6,maximum=max(v)/1e6)
                                            for key,v in stage_deployments.items()}
    facts['clock_helper_ms']=dict(median=median(calibrations)/1e6,minimum=min(calibrations)/1e6,maximum=max(calibrations)/1e6)
    return write_tables(output, analysis, sections, facts)


def write_tables(output, analysis, sections, facts):
    output.mkdir(parents=True,exist_ok=True)
    status='COMPLETE' if analysis['status']=='complete' else 'PARTIAL: provisional values, not manuscript replacements'
    document='# Algorithm, application and deployment evidence\n\n'+status+'\n\n'
    document+='Each absolute value is the median of deployment medians. Each ratio first pairs inner rounds, then summarizes complete deployments with equal weight. Ranges are descriptive, not confidence intervals.\n\n'
    document+='\n'.join(sections.values())
    (output/'tables.md').write_text(document)
    (output/'tables.json').write_text(json.dumps(dict(status=analysis['status'],tables=sections,facts=facts),indent=2)+'\n')
    return dict(status=analysis['status'],tables=len(sections),completed_deployments=analysis['completed_deployments'])


def render_section63(directory, output):
    """Compatibility entry; current tables use the six-version schema."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'section63/scripts'))
    from tables import build
    directory, output = Path(directory).resolve(), Path(output).resolve()
    base = directory.parent if directory.name == 'analysis' else directory
    assert output == base, 'use the campaign directory as --output'
    build(base)
    return dict(status='complete', output=str(base / 'paper-material'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--allow-partial',action='store_true')
    p.add_argument('--applications-only',action='store_true')
    p.add_argument('--section63', action='store_true', help='render the single current section 6.3 campaign')
    args = vars(p.parse_args())
    section63 = args.pop('section63')
    if section63:
        assert not args.pop('applications_only')
        assert not args.pop('allow_partial'), 'section 6.3 requires complete evidence'
    print(json.dumps((render_section63 if section63 else render)(**args),indent=2))
