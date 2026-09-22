#!/usr/bin/env python3
"""Replay typed request validation and the unchanged full transaction matrix."""
from pathlib import Path
import argparse,json,re,subprocess
from registration_retirement_audit import audit as retirement_audit

def audit(out):
    retirement=retirement_audit(out)
    r=json.loads((out/'result.json').read_text());c=r['guest_record']['checks']
    assert c['protocol_layout']==dict(page=24,request=7216,result=88)
    assert c['protocol_v3_rejected']['status']==-93 and c['protocol_v4_short_rejected']['status']==-90
    for i in range(3):
        x=c[f'invalid-page-kind-{i}'];assert (x['status'],x['staged'],x['applied'])==(-22,0,0)
    for kind in range(2):
        for i in range(3):
            x=c[f'page-type-mismatch-{kind}-{i}']
            assert (x['status'],x['state'],x['applied'],x['failed_page'])==(-13,3,0,i)
    for fail in (0,150,255,256,299,None):
        x=c[f'cross_batch_{fail}'];assert x['total']==x['staged']==300
        assert (x['status'],x['applied'])==((0,300) if fail is None else (-5,0))
    layouts={}
    for name in ('transaction','binding','vkso_tx_request'):
        raw=subprocess.check_output(['pahole','-C',name,str(out/'payload/page_cache_replace.ko')],text=True)
        layouts[name]=int(re.search(r'/\* size: (\d+),',raw)[1])
        (out/(name+'-layout.txt')).write_text(raw)
    assert layouts==dict(transaction=688,binding=64,vkso_tx_request=7216)
    return dict(status='pass',boot_id=r['guest_record']['boot_id'],protocol=4,layout=c['protocol_layout'],
                compiled_layouts=layouts,malformed_type_cases=3,type_mismatch_preflight_cases=6,
                legacy_request_rejected=True,full_transaction_and_retirement_matrix=retirement)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args()
    report=audit(a.directory.resolve());(a.directory/'typed-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='full_transaction_and_retirement_matrix'},indent=2))
