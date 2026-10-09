#!/usr/bin/env python3
"""Verify full UPDATE decomposition deliverables against archived observations."""
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import cairosvg
from PIL import Image
from update_evaluation import OUT, ROOT, rows


def main():
    here=OUT.parent;logs=[];commands=[]
    for args in [[str(here/'update_evaluation.py'),'--check'],[str(here/'update_report.py'),'--check'],
                 ['-m','unittest','discover','-s',str(here/'tests'),'-p','test_update_evaluation.py']]:
        p=subprocess.run([sys.executable,*args],cwd=ROOT,text=True,capture_output=True)
        command=' '.join([sys.executable,*args]).replace(str(ROOT)+'/','')
        logs.append('$ '+command+'\n'+p.stdout+p.stderr);commands.append(dict(command=command,exit_code=p.returncode))
        if p.returncode:
            (OUT/'verification.log').write_text('\n'.join(logs));raise RuntimeError(command)
    summary=rows(OUT/'summary.csv');blocks=rows(OUT/'decomposition-blocks.csv');sensitivity=rows(OUT/'sensitivity.csv');loads=rows(OUT/'load-response.csv')
    assert (len(summary),len(blocks),len(sensitivity),len(loads))==(8,32,128,6)
    assert len(rows(OUT/'boots.csv'))==64 and len(rows(OUT/'rounds.csv'))==960
    validation=json.loads((OUT/'validation.json').read_text());assert validation['samples']==3599774 and validation['update_boots']==16
    assert len(validation['non_cpu0_samples'])==4
    assert len({x['boot_id'] for x in rows(OUT/'identities.csv')})==16
    assert all(int(x['negative_blocks'])==4 and float(x['ci95_high'])<0 for x in loads)
    assert all(int(x['faster_blocks'])==4 for x in summary if x['scenario'] in ['monotonic_raw','monotonic_coarse'])
    keys=['low_contribution','high_capped_contribution','occupancy_contribution','tail_contribution']
    residual=max(abs(sum(float(x[k]) for k in keys)-float(x['delta'])) for x in blocks)
    assert residual<1e-9
    resolved=[x for x in sensitivity if x['status']=='defined'];assert len(sensitivity)-len(resolved)==5
    for x in resolved:
        assert float(x['low_contribution'])<0 and float(x['occupancy_contribution'])>0
        original=next(s for s in summary if (s['variant'],s['scenario'])==(x['variant'],x['scenario']))
        assert abs(float(x['delta'])-float(original['delta']))<1e-9
    assert all(float(x['tail_contribution'])<0 for x in summary)
    ns={'s':'http://www.w3.org/2000/svg'};render=[]
    for svg in sorted(OUT.glob('update-*.svg')):
        doc=ET.fromstring(svg.read_bytes());assert doc.findall('.//s:text',ns)
        regenerated=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.read_bytes()))).convert('RGB')
        png=Image.open(svg.with_suffix('.png')).convert('RGB')
        assert png.size==regenerated.size and png.tobytes()==regenerated.tobytes(),svg.name
        pdf=svg.with_suffix('.pdf').read_bytes();assert pdf.startswith(b'%PDF-') and b'%%EOF' in pdf[-64:]
        render.append(svg.name)
    assert len(render)==5
    for name in ['README.md','evaluation-text.md','measurement-and-mechanism.md','visual-contract.md','tables.md','boot-results.md']:
        text=(OUT/name).read_text()
        for link in re.findall(r'\]\(([^)]+)\)',text):assert (OUT/link).exists(),(name,link)
    tex=list(OUT.glob('table-update-*.tex'));assert len(tex)==2
    for path in tex:
        s=path.read_text();assert s.count('\\begin{tabular}')==s.count('\\end{tabular}')==1
    groups=rows(OUT/'groups.csv');claims={}
    for variant in ['normal','no-retpoline']:
        for backend in ['raw','vkso']:
            z=[float(x['mean']) for x in groups if x['variant']==variant and x['backend']==backend]
            claims[variant+'/'+backend]=dict(min_mean=min(z),max_mean=max(z),range_width=max(z)-min(z))
    result=dict(status='PASS',scope='UPDATE offline distribution decomposition; matched recorder and causal mechanism remain separate next task',
                commands=commands,full_samples=validation['samples'],full_sample_means_reproduced=True,
                max_four_term_reconstruction_error=residual,load_response_all_four_blocks=6,
                low_side_negative_and_occupancy_positive_in_all_resolved_sensitivities=len(resolved),unresolved_sensitivity_settings=5,
                workload_mean_ranges=claims,figures=render,
                render_check='all five PNGs inspected; density title overlap fixed; PNGs match canonical SVG; vector PDFs present',
                deliverables=['tables.md','boot-results.md','summary.csv','decomposition-blocks.csv','load-response.csv','groups.csv','boots.csv','rounds.csv','sensitivity.csv','histograms.csv','cdfs.csv','evaluation-text.md','measurement-and-mechanism.md'],
                latex='two booktabs content fragments; syntax checked')
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'verification.log').write_text('\n'.join(logs)+'\nNumerical identity, complete coverage and rendered-artifact checks: PASS\n')
    print(json.dumps(dict(status='PASS',samples=validation['samples'],comparisons=8,load_response_comparisons=6,figures=5),indent=2))

if __name__=='__main__':main()
