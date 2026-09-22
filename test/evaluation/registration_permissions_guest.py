#!/usr/bin/env python3
"""Use actual owner pages under normal and rodata=off guest boot policies."""
import csv
import io
import json
import os
from pathlib import Path
import re
import subprocess
from registration_transaction_guest import (Client, Request, BEGIN, STAGE, COMMIT,
    QUERY, RELEASE, FORGET, ACTIVE, ABORTED, TEXT, RODATA, SHARED_DATA)
import registration_completion_guest as G
ROOT, OUT, PAGE = G.ROOT, G.OUT, G.PAGE

def main():
    OUT.mkdir()
    record = dict(status='running', scope='source type and actual mapping admission; no timing comparison',
                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  cmdline=Path('/proc/cmdline').read_text().strip(), rows=[])
    def command(argv, name, expected=0):
        with (OUT/(name+'.log')).open('w') as stream:
            result = subprocess.run(list(map(str,argv)),stdout=stream,stderr=subprocess.STDOUT,timeout=20)
        if expected is not None: assert result.returncode == expected, (name,result.returncode)
        return result.returncode
    try:
        unprotected = 'rodata=off' in record['cmdline'].split()
        for name in ('vkso_lz4','vkso_kernel_reader','page_cache_replace'):
            command(['insmod',ROOT/(name+'.ko')],'load-'+name)
        owner = Path('/sys/module/vkso_lz4')
        version = (owner/'srcversion').read_text().strip()
        identity = json.loads((ROOT/'image-identities.json').read_text())
        (OUT/'owner_descriptors.txt').write_text(f"vkso_lz4_owner {version} vkso_lz4 {identity['owner_build_id']}\n")
        (OUT/'kernel_identity.txt').write_text(f"kernel {identity['kernel_build_id']}\n")
        probe = Path('/sys/kernel/debug/vkso_kernel_reader')
        client = Client()
        baseline = dict(owner=0,transport=1)
        def refs():
            return dict(owner=int((owner/'refcnt').read_text()),
                        transport=int(Path('/sys/module/page_cache_replace/refcnt').read_text()))
        assert refs()==baseline
        for section, intended in (('.text',TEXT),('.rodata',RODATA),('.vkso_owner',None)):
            section_address=int((owner/'sections'/section).read_text(),16)
            source=section_address & ~(PAGE-1)
            (probe/'page_addresses').write_text(hex(source)+'\n')
            raw=(probe/'pages').read_text();(OUT/(section[1:]+'-mapping.csv')).write_text(raw)
            mapping=list(csv.DictReader(io.StringIO(raw)))[0]
            assert int(mapping['kernel_vaddr'],16)==source and int(mapping['level'])==1
            assert int(mapping['user'])==0
            if intended in (TEXT,RODATA):
                assert int(mapping['writable'])==int(unprotected)
                assert int(mapping['executable'])==int(intended==TEXT)
            for kind,label in ((TEXT,'text'),(RODATA,'rodata'),(SHARED_DATA,'shared_data')):
                tid=800+len(record['rows']);name=section[1:]+'-'+label
                path=OUT/(name+'.bin');path.write_bytes(b'H'*PAGE+b'Z'*PAGE)
                with path.open('rb') as stream: os.fsync(stream.fileno())
                before=G.observe(path)
                r=Request();r.total=1;r.filepath=str(path).encode();st=path.stat()
                r.device=st.st_dev;r.inode=st.st_ino;r.owner_count=1
                r.owners[0].symbol=b'vkso_lz4_owner';r.owners[0].srcversion=version.encode()
                client.rpc(BEGIN,tid,request=r)
                r=Request();r.total=r.count=1;r.pages[0].offset=PAGE;r.pages[0].source=source;r.pages[0].kind=kind
                client.rpc(STAGE,tid,request=r)
                accepted=not unprotected and intended==kind
                reply=client.rpc(COMMIT,tid,0 if accepted else -13)
                observed=G.observe(path)
                if accepted:
                    assert reply['state']==ACTIVE and reply['applied']==1
                    assert observed['pfn']==int(mapping['pfn']) and not observed['original']
                else:
                    assert reply['state']==ABORTED and reply['applied']==0 and reply['failed_page']==0
                    assert observed==before and refs()==baseline
                release=client.rpc(RELEASE,tid);client.rpc(FORGET,tid)
                restored=G.observe(path);assert restored['original'] and restored['pfn']!=int(mapping['pfn'])
                assert refs()==baseline
                manager=None
                if not accepted:
                    plan=OUT/'page_mappings.txt';plan.write_text(f'0x1000,{hex(source)},{label},{section}\n')
                    rc=command([G.MANAGER,'replace',path,plan,'--hold'],'manager-'+name,None)
                    log=(OUT/('manager-'+name+'.log')).read_text()
                    assert rc!=0 and re.search(r'operation=3 .*status=-13 state=3 .*applied=0',log),log
                    assert G.observe(path)['original'] and refs()==baseline
                    assert not (ROOT/'runtime/manager.state').exists() and not (ROOT/'runtime/manager.pid').exists()
                    manager=dict(returncode=rc,log='manager-'+name+'.log')
                record['rows'].append(dict(section=section,section_address=section_address,kind=kind,mapping=mapping,accepted=accepted,
                    before=before,observed=observed,restored=restored,commit=reply,release=release,manager=manager))
        client.fd.close()
        for name in ('page_cache_replace','vkso_kernel_reader','vkso_lz4'):
            command(['rmmod',name],'unload-'+name)
        record.update(status='pass',modules_after=Path('/proc/modules').read_text())
    except BaseException as error:
        record.update(status='fail',error=repr(error));raise
    finally:
        (OUT/'status.json').write_text(json.dumps(record,indent=2)+'\n')
        (OUT/'dmesg.txt').write_text(subprocess.check_output(['dmesg'],text=True))

if __name__=='__main__':main()
