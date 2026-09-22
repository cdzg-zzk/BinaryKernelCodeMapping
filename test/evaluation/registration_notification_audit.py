#!/usr/bin/env python3
"""Check notification ownership, file/VMA observations and actual payloads."""
from pathlib import Path
import argparse,json

ROOT=Path(__file__).resolve().parents[2]

def audit(out):
    result=json.loads((out/'result.json').read_text());v=out/'evidence/validation'
    assert result['status']=='pass' and result['qemu_returncode']==0 and not result['kernel_failure']
    guest=result['guest_record'];checks=guest['checks'];new=checks['wrapper-and-file-boundaries']
    assert all(new[k] for k in ('active_competitor_preserved','stale_state_preserved','regular_notification_file_preserved','shell_exit_before_ready_restores'))
    assert new['sudo_background_path']['application_uid']==65534 and new['sudo_background_path']['manager_uid']==0
    operations=json.loads((v/'file-operations.stdout').read_text())
    assert operations==new['file_operations'] and operations['uid']==65534
    for op in ('open-rdwr','truncate','rename','unlink','hardlink','chmod','utime'):
        assert operations['operations'][op]=={'ordinary_file':'allowed','carrier.bin':1,'alias.bin':1}
    assert operations['operations']['shared-write-upgrade']==13
    pfns=json.loads((v/'file-operations-pfn.json').read_text())
    assert pfns['before']==pfns['after'] and not pfns['before']['original']
    assert 'Another manager owns this runtime directory' in (v/'wrapper-competing/page_replace.log').read_text()
    assert 'Existing manager state requires recovery' in (v/'wrapper-stale/page_replace.log').read_text()
    interrupted=(v/'wrapper-interrupted/page_replace.log').read_text()
    assert 'operation=3 ' in interrupted and 'operation=5 ' in interrupted
    assert 'Manager hold session restored and exiting.' in interrupted
    assert (v/'not-a-notification-fifo').read_text()=='retain these bytes'
    assert {x.split()[0] for x in guest['modules_after'].splitlines()}=={'virtio_blk'}
    for name in ('manager','page_cache_replace.ko'):
        assert (ROOT/'page_cache_replace'/name).read_bytes()==(out/'payload'/name).read_bytes()
    for name in ('manager.cpp','page_cache_replace.c','protocol.h','owner.h'):
        assert (ROOT/'page_cache_replace'/name).read_bytes()==(out/'source'/name).read_bytes()
    assert (ROOT/'vkso').read_bytes()==(out/'payload/vkso').read_bytes()
    product=(ROOT/'vkso').read_text();harness=(v/'wrapper-functions.sh').read_text()
    for name in ('as_root','setup_event','hold_state_owned','cleanup_session','exec_with_replacement'):
        start=product.index(name+'() {');function=product[start:product.index('\n}',start)+2]
        assert function in harness,name
    return dict(status='pass',boot_id=guest['boot_id'],checked_components='actual current manager, page module, vkso and extracted wrapper functions',
                sudo_background=new['sudo_background_path'],file_operations=operations,
                source_pfn=pfns['before']['pfn'],scope='root and sudo notification paths; full transaction and file/VMA validation; no setup performance estimate')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args()
    r=audit(a.directory.resolve());(a.directory/'independent-audit.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='file_operations'},indent=2))
