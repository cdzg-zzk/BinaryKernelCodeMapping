#!/usr/bin/env python3
"""Reconstruct complete-task setup comparisons from each raw command log."""
from pathlib import Path
import argparse
import itertools
import json
import statistics
import re
try:
    from .collect import events
except ImportError:
    from collect import events

def audit_export(path):
    """Report offline construction separately from the full benchmark session."""
    samples=events(Path(path).read_text())
    construction=('krg','checker','header','carrier','install')
    expected=['command.begin']
    for name in construction:expected.extend((name+'.begin',name+'.end'))
    expected+=['session.begin','manager.begin','manager.ready','application.begin',
               'application.end','cleanup.begin','cleanup.end']
    assert [x['name'] for x in samples]==expected
    assert len({x['pid'] for x in samples})==1
    assert all(a['ns']<=b['ns'] for a,b in zip(samples,samples[1:]))
    stamps={x['name']:x['ns'] for x in samples}
    return dict(status='pass',clock='CLOCK_MONOTONIC_RAW',
                construction_ns={name:stamps[name+'.end']-stamps[name+'.begin'] for name in construction},
                command_marker_to_application_ns=stamps['application.begin']-stamps['command.begin'],
                registration_wrapper_ns=stamps['manager.ready']-stamps['manager.begin'],
                scope='instrumented construction and registration stages; excludes owner build/load; application contains the complete benchmark campaign',
                observer_policy='shell helper launch/output/exit retained; do not subtract calibration or call the full session setup latency')

def audit(directory, manager_log=None):
    directory=Path(directory)
    data=json.loads((directory/'comparison.json').read_text())
    assert data['status']=='pass' and data['phase'] in ('active','ready')
    assert data['cpu_affinity'] and len(data['cpu_affinity'])==1
    assert len(data['rows'])==8*data['rounds'] and len(data['warmup'])==2
    expected=set(itertools.product(range(data['rounds']),('native','vkso'),(False,True),(1,3)))
    seen=set();transactions=set();groups={}
    manager_operations={}
    if data['phase']=='ready':
        manager_log=Path(manager_log) if manager_log else directory.parent/'export/vkso/metadata/page_replace.log'
        for line in manager_log.read_text().splitlines():
            if line.startswith('VKSO_TRANSACTION id='):
                fields={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
                manager_operations.setdefault(fields['id'],[]).append(fields)

    for row in data['warmup']+data['rows']:
        raw=(directory/row['log']).read_text()
        assert [x for x in raw.splitlines() if x.startswith('valid\tlz4\t')]==[
            f"valid\tlz4\t12\t211938580\t{row['iterations']}"]
        assert row['inputs']==12 and row['input_bytes']==211938580 and row['returncode']==0
        assert row['end_ns']>row['start_ns'] and row['total_ns']==row['end_ns']-row['start_ns']
        if row['traced']:
            samples=events(raw);assert samples==row['events']
            assert len({x['pid'] for x in samples})==1
            names=[x['name'] for x in samples]
            for key in ('process.main','load.begin','load.end','first.valid','task.begin','task.end','unload.end'):
                assert names.count(key)==1
            assert names.count('dlsym.begin')==names.count('dlsym.end')==2
            first=next(x['ns'] for x in samples if x['name']=='first.valid')
            assert first==row['first_valid_ns'] and row['to_first_valid_ns']==first-row['start_ns']
            assert row['start_ns']<=samples[0]['ns']<=first<=samples[-1]['ns']<=row['end_ns']
        else:
            assert not any(x.startswith('event\t') for x in raw.splitlines())
            assert row['events']==[] and row['first_valid_ns'] is row['to_first_valid_ns'] is None
        whole=data['phase']=='ready' and row['backend']=='vkso'
        if whole:
            assert row['argv'][1]=='exec-ready' and '--' in row['argv']
            operations=row['kernel_transactions'];assert [x['operation'] for x in operations]==[1,2,3,5,6]
            assert len({x['id'] for x in operations})==1 and all(x['status']==0 for x in operations)
            tid=operations[0]['id'];assert tid not in transactions;transactions.add(tid)
            assert manager_operations[tid]==operations
            assert operations[2]['applied']==5 and operations[3]['applied']==0
            if row['traced']:
                stages=events((directory/(Path(row['log']).stem+'-stages.tsv')).read_text())
                assert stages==row['shell_events']
                assert [e['name'] for e in stages]==['command.begin','session.begin','manager.begin','manager.ready','application.begin','application.end','cleanup.begin','cleanup.end']
                assert row['start_ns']<=stages[0]['ns']<=row['first_valid_ns']<=stages[-1]['ns']<=row['end_ns']
            else:assert row['shell_events']==[]
        else:assert row['kernel_transactions']==row['shell_events']==[]
        selected=data['libraries'][row['backend']]
        assert row['argv'][-4:]==[selected,row['argv'][-3],'65536',str(row['iterations'])]
        assert Path(row['argv'][-5]).name==('setup-lz4' if row['traced'] else 'setup-lz4-plain')
        if 'repeat' in row:
            key=(row['repeat'],row['backend'],row['traced'],row['iterations'])
            assert key in expected and key not in seen;seen.add(key)
            groups.setdefault((row['backend'],row['traced'],row['iterations']),[]).append(row['total_ns'])
    assert seen==expected
    # Verify planned rotation rather than treating the condition order as random.
    conditions=list(itertools.product(('native','vkso'),(False,True),(1,3)))
    for repeat in range(data['rounds']):
        order=conditions[repeat%8:]+conditions[:repeat%8]
        if repeat%2:order=list(reversed(order))
        rows=[r for r in data['rows'] if r['repeat']==repeat]
        assert [r['position'] for r in rows]==list(range(8))
        assert [(r['backend'],r['traced'],r['iterations']) for r in rows]==order
    calibration=data['clock_calibration']
    if data['phase']=='ready':
        assert len(transactions)==1+4*data['rounds'] and len(calibration)==30
        raw=events((directory/'clock-calibration.tsv').read_text());assert len(raw)==30
        for row,event in zip(calibration,raw):
            assert row['start_ns']<=event['ns']<=row['end_ns']
            assert row['total_ns']==row['end_ns']-row['start_ns']
    else:assert not transactions and not calibration
    return dict(status='pass',phase=data['phase'],boot_id=data['boot_id'],observations=len(data['rows']),
                warmups=2,full_input_bytes=211938580,registrations=len(transactions),transaction_ids=sorted(transactions),
                scope=data['scope'],clock_calibration_samples=len(calibration),
                median_command_ns=[dict(backend=k[0],traced=k[1],iterations=k[2],value=statistics.median(v)) for k,v in sorted(groups.items())])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();r=audit(a.directory)
    (a.directory/'independent-audit.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))
