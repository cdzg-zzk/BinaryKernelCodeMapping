#!/usr/bin/env python3
"""Reconstruct setup observations from raw guest logs without executing workloads."""
from pathlib import Path
import argparse,json,re
from collect import events

def one(samples,name):
    values=[x['ns'] for x in samples if x['name']==name]
    assert len(values)==1,(name,values)
    return values[0]

def check_processes(directory,algorithm):
    data=json.loads((directory/'processes.json').read_text())
    assert data['status']=='pass' and data['algorithm']==algorithm
    rows=data['rows'];assert len(rows)==6
    assert [(r['backend'],r['iterations']) for r in rows]==[
        ('kernel-vkso',1),('native',1),('native',3),('kernel-vkso',3),('kernel-vkso',1),('native',1)]
    for row in rows:
        raw=(directory/row['log']).read_text();observed=events(raw)
        assert observed==row['events']
        assert len({e['pid'] for e in observed})==1
        assert row['returncode']==0 and row['start_ns']<=observed[0]['ns']<=observed[-1]['ns']<=row['end_ns']
        assert row['external_total_ns']==row['end_ns']-row['start_ns']
        assert row['first_valid_ns']==one(observed,'first.valid')
        assert row['external_to_first_valid_ns']==row['first_valid_ns']-row['start_ns']
        assert row['load_to_first_valid_ns']==row['first_valid_ns']-one(observed,'load.begin')
        for stage in ('load','task','unload','dlopen'):
            assert row['stage_ns'][stage]==one(observed,stage+'.end')-one(observed,stage+'.begin')
        assert one(observed,'load.begin')<=one(observed,'dlopen.begin')<=one(observed,'dlopen.end')<=one(observed,'load.end')
        assert one(observed,'load.end')<=one(observed,'task.begin')<=row['first_valid_ns']<=one(observed,'task.end')
        lookup=[e for e in observed if e['name'].startswith('dlsym.')]
        assert len(lookup)=={'lz4':4,'bch':8,'xz':10}[algorithm]
        assert row['stage_ns']['dlsym_sum']==sum(b['ns']-a['ns'] for a,b in zip(lookup[::2],lookup[1::2]))
        expected=f"valid\t{algorithm}\t{row['inputs']}\t{row['bytes']}\t{row['iterations']}"
        assert raw.splitlines().count(expected)==1
        assert row['inputs']=={'lz4':12,'bch':2,'xz':3}[algorithm] and row['bytes']>0
    assert len({r['events'][0]['pid'] for r in rows})==6
    assert len({r['bytes'] for r in rows})==1
    return rows

def audit(directory,algorithm):
    result=json.loads((directory/'result.json').read_text())
    assert result['status']=='pass' and not result['kernel_failure'] and result['qemu_returncode']==0
    v=directory/'evidence/validation'
    full=check_processes(v/'setup-full',algorithm);ready=check_processes(v/'setup-ready',algorithm)
    stages=events((v/'setup-stages.tsv').read_text())
    assert len({x['pid'] for x in stages})==1
    expected=['command.begin','krg.begin','krg.end','checker.begin','checker.end','header.begin','header.end',
        'carrier.begin','carrier.end','install.begin','install.end','session.begin','manager.begin','manager.ready',
        'application.begin','application.end','cleanup.begin','cleanup.end']
    assert [x['name'] for x in stages]==expected
    commands=[json.loads(line) for line in (v/'commands.jsonl').read_text().splitlines()]
    command=[r for r in commands if len(r['argv'])>1 and r['argv'][0]=='/work/repo/vkso' and r['argv'][1]=='exec']
    assert len(command)==1;command=command[0]
    assert command['start_ns']<=stages[0]['ns']<one(stages,'application.begin')<=full[0]['first_valid_ns']<one(stages,'application.end')<=stages[-1]['ns']<=command['end_ns']
    session=json.loads((v/'setup-ready/session.json').read_text())
    actual=events((v/'setup-ready-stages.tsv').read_text());assert session['stages']==actual
    assert [x['name'] for x in actual]==[x for x in expected if not any(x.startswith(s+'.') for s in ('krg','checker','header','carrier','install'))]
    assert session['start_ns']<=actual[0]['ns']<one(actual,'application.begin')<=ready[0]['first_valid_ns']<one(actual,'application.end')<=actual[-1]['ns']<=session['end_ns']
    assert session['external_to_first_valid_ns']==ready[0]['first_valid_ns']-session['start_ns']
    assert session['external_total_ns']==session['end_ns']-session['start_ns']
    # Kernel fields are cumulative within a transaction. Keep one COMMIT and
    # one RELEASE per session; never sum prepare/apply fields from both replies.
    log=(v/'export/vkso/metadata/page_replace.log').read_text()
    transactions={}
    for line in log.splitlines():
        if line.startswith('VKSO_TRANSACTION '):
            fields={key:int(value) for key,value in re.findall(r'(\w+)=(-?\d+)',line)}
            transactions.setdefault(fields['id'],[]).append(fields)
    # Optional matched comparisons add separate sessions to this same raw log.
    # Independently validate those sessions before separating the original two.
    comparisons={}
    if (v/'setup-comparison-ready').exists():
        from compare_audit import audit as audit_comparison
        for phase in ('active','ready'):
            comparisons[phase]=audit_comparison(v/f'setup-comparison-{phase}')
        for tid in comparisons['ready']['transaction_ids']:
            assert tid in transactions
            del transactions[tid]
    assert len(transactions)==2
    manager_source=(directory/'payload/repo/page_cache_replace/manager.cpp').read_text()
    manager_retires='r.operation = VKSO_FORGET;' in manager_source
    kernel=[]
    for rows in transactions.values():
        assert [r['operation'] for r in rows]==([1,2,3,5,6] if manager_retires else [1,2,3,5])
        assert all(r['status']==0 for r in rows)
        commit=rows[2];release=rows[3]
        assert commit['applied']=={'lz4':5,'bch':4,'xz':4}[algorithm]
        assert release['applied']==0 and release['state']==4
        kernel.append(dict(commit=commit,release=release,forget=rows[4] if manager_retires else None))
    pfns=json.loads((v/'registered-pfns.json').read_text())
    assert pfns['status']=='pass' and all(row['shared'] for row in pfns['pages'])
    guest=result.get('guest_record',{})
    modules=guest.get('modules_after',json.loads((v/'status.json').read_text()).get('modules_after',''))
    assert not any(name in modules for name in ('page_cache_replace','vkso_lz4','vkso_bch','vkso_xz','vkso_kernel_reader'))
    report=dict(status='pass',algorithm=algorithm,clock='CLOCK_MONOTONIC_RAW',
        full_deployment_to_first_valid_ns=full[0]['first_valid_ns']-command['start_ns'],
        ready_carrier_to_first_valid_ns=session['external_to_first_valid_ns'],
        full_stage_ns={s:one(stages,s+'.end')-one(stages,s+'.begin') for s in ('krg','checker','header','carrier','install','application','cleanup')},
        registration_wrapper_ns=one(stages,'manager.ready')-one(stages,'manager.begin'),
        kernel_transactions=kernel,processes=12,matched_comparisons=comparisons,
        inputs_per_task=full[0]['inputs'],bytes_per_task=full[0]['bytes'],
        scope='two functional registration sessions; virtualized instrumented timings, not formal physical-host samples',
        nesting='dlopen/dlsym are inside load; kernel prepare/apply inside COMMIT; first-valid includes complete task and validation; phases are not all additive')
    (directory/'setup-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('algorithm',choices=['lz4','bch','xz'])
    a=p.parse_args();print(json.dumps(audit(a.directory,a.algorithm),indent=2))
