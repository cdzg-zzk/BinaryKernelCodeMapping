#!/usr/bin/env python3
"""Reconstruct the two-boot source-admission matrix and raw permission records."""
from pathlib import Path
import argparse
import csv
import json
import re
ROOT=Path(__file__).resolve().parents[2]

def audit(normal, unprotected):
    boots=[];accepted_total=0;manager_rejections=0
    for out, off in ((Path(normal),False),(Path(unprotected),True)):
        result=json.loads((out/'result.json').read_text());v=out/'evidence/validation'
        assert result['status']=='pass' and result['qemu_returncode']==0 and not result['kernel_failure']
        data=json.loads((v/'status.json').read_text());assert data==result['guest_record']
        assert ('rodata=off' in data['cmdline'].split())==off
        assert len(data['rows'])==9
        seen=set();accepted=0;rejected=0
        for row in data['rows']:
            section,kind=row['section'],row['kind'];key=(section,kind)
            assert key not in seen;seen.add(key)
            raw=list(csv.DictReader((v/(section[1:]+'-mapping.csv')).open()))
            assert len(raw)==1 and raw[0]==row['mapping'];mapping=raw[0]
            flags=int(mapping['leaf_flags'],16)
            assert flags&1 and int(mapping['user'])==int(bool(flags&4))==0
            assert int(mapping['writable'])==int(bool(flags&2))
            assert int(mapping['executable'])==int(not bool(flags&(1<<63)))
            assert int(mapping['kernel_vaddr'],16)==row['section_address']&~4095
            assert int(mapping['level'])==1
            intended={'.text':1,'.rodata':2,'.vkso_owner':None}[section]
            if intended is not None:
                assert int(mapping['writable'])==int(off)
                assert int(mapping['executable'])==int(intended==1)
            expected=not off and intended==kind
            assert row['accepted']==expected
            commit=row['commit'];assert commit['version']==4 and commit['operation']==3
            assert (commit['status'],commit['state'],commit['applied'])==((0,2,1) if expected else (-13,3,0))
            source_pfn=int(mapping['pfn'])
            assert row['before']['original'] and row['before']['pfn']!=source_pfn
            if expected:
                assert row['observed']==dict(pfn=source_pfn,original=False)
                assert row['manager'] is None
                accepted+=1
            else:
                assert row['observed']==row['before'] and commit['failed_page']==0
                manager=row['manager'];assert manager['returncode']!=0
                text=(v/manager['log']).read_text()
                operations=[{k:int(val) for k,val in re.findall(r'(\w+)=(-?\d+)',line)}
                            for line in text.splitlines() if line.startswith('VKSO_TRANSACTION id=')]
                assert [r['operation'] for r in operations][:3]==[1,2,3]
                assert operations[2]['status']==-13 and operations[2]['applied']==0
                assert 'phase=after-begin' in text
                rejected+=1
            assert row['restored']['original'] and row['restored']['pfn']!=source_pfn
            assert (row['release']['status'],row['release']['applied'])==(0,0)
        assert seen=={(s,k) for s in ('.text','.rodata','.vkso_owner') for k in (1,2,3)}
        assert (accepted,rejected)==((0,9) if off else (2,7))
        assert {line.split()[0] for line in data['modules_after'].splitlines()}=={'virtio_blk'}
        for name in ('manager','page_cache_replace.ko'):
            assert (out/'payload'/name).read_bytes()==(ROOT/'page_cache_replace'/name).read_bytes()
        for name in ('manager.cpp','page_cache_replace.c','protocol.h','owner.h'):
            assert (out/'source'/name).read_bytes()==(ROOT/'page_cache_replace'/name).read_bytes()
        for name in ('manager','page_cache_replace.ko','vkso_lz4.ko','vkso_kernel_reader.ko'):
            assert (out/'payload'/name).read_bytes()==(Path(normal)/'payload'/name).read_bytes()
        boots.append(dict(boot_id=data['boot_id'],directory=str(out),rodata_off=off,accepted=accepted,
                          direct_rejections=rejected,manager_rejections=rejected))
        accepted_total+=accepted;manager_rejections+=rejected
    assert boots[0]['boot_id']!=boots[1]['boot_id']
    return dict(status='pass',boots=boots,direct_cases=18,accepted=accepted_total,
                manager_rejections=manager_rejections,identical_product_and_owner_binaries=True,
                scope='typed module admission and kernel mapping RW checks at registration; leaf observer; no publicness or later rewriting guarantee')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('normal',type=Path);p.add_argument('unprotected',type=Path)
    a=p.parse_args();report=audit(a.normal.resolve(),a.unprotected.resolve())
    (a.normal/'permission-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
