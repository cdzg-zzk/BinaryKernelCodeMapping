#!/usr/bin/env python3
"""Final requirement checks for the complete READ evidence deliverable."""
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import cairosvg
from PIL import Image
from read_evaluation import HERE, ROOT, OUT, CASE_NAMES, KERNEL_APIS, VARIANTS, rows


def main():
    logs=[];commands=[]
    for args in [[str(HERE/'read_evaluation.py'),'--check'],[str(HERE/'read_paths.py'),'--check'],
                 [str(HERE/'read_report.py'),'--check'],['-m','unittest','discover','-s',str(HERE/'tests'),'-p','test_read_evaluation.py']]:
        p=subprocess.run([sys.executable,*args],capture_output=True,text=True,cwd=ROOT)
        label=' '.join([sys.executable,*args]).replace(str(ROOT)+'/', '')
        logs.append('$ '+label+'\n'+p.stdout+p.stderr);commands.append(dict(command=label,exit_code=p.returncode))
        if p.returncode:
            (OUT/'verification.log').write_text('\n'.join(logs));raise RuntimeError(label)
    table=rows(OUT/'summary.csv'); boot=rows(OUT/'boot-statistics.csv'); block=rows(OUT/'block-deltas.csv')
    assert len(table)==38 and len(boot)==304 and len(block)==152
    assert len({(x['variant'],x['domain'],x['api']) for x in table})==38
    assert len(rows(OUT/'call-paths.csv'))==19
    f=lambda x,k:float(x[k])
    claims={}
    for cat in ['clock_gettime_fast','kernel_read','other_time_fast','getcpu','fallback']:
        selected=[x for x in table if x['category']==cat]
        claims[cat]=dict(comparisons=len(selected),min_delta=min(f(x,'delta_ticks') for x in selected),
                         max_delta=max(f(x,'delta_ticks') for x in selected),
                         min_mean_delta=min(f(x,'mean_delta') for x in selected),
                         max_mean_delta=max(f(x,'mean_delta') for x in selected),
                         all_four_blocks_faster=sum(int(x['faster_blocks'])==4 for x in selected))
    assert round(claims['clock_gettime_fast']['min_delta'],3)==-1.006
    assert round(claims['clock_gettime_fast']['max_delta'],3)==1.006
    assert round(claims['kernel_read']['min_delta'],3)==-2.728
    assert round(claims['kernel_read']['max_delta'],3)==1.087
    assert claims['other_time_fast']['all_four_blocks_faster']==10
    assert claims['getcpu']['all_four_blocks_faster']==2
    assert claims['other_time_fast']['max_mean_delta']<0 and claims['getcpu']['max_mean_delta']<0
    assert claims['fallback']['max_delta']<0
    for x in table:
        assert round(f(x,'vkso_ticks')-f(x,'raw_ticks'),9)==round(f(x,'delta_ticks'),9)
        assert abs(100*(f(x,'vkso_ticks')/f(x,'raw_ticks')-1)-f(x,'delta_percent'))<1e-10
    render=[]
    ns={'s':'http://www.w3.org/2000/svg'}
    for name,count in [('main',100),('other',60),('fallback',30)]:
        svg=OUT/f'read-{name}.svg';doc=ET.fromstring(svg.read_bytes())
        # Circle + square data markers (5 per row/config) plus 2 legend markers.
        markers=len(doc.findall('.//s:circle',ns))+len([x for x in doc.findall('.//s:rect',ns) if x.get('stroke')])
        assert markers==count+2,(name,markers)
        texts=[x.text for x in doc.findall('.//s:text',ns)]
        assert 'VKSO − Raw (TSC ticks/call)' in texts
        reconstructed=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.read_bytes()))).convert('RGB')
        png=Image.open(svg.with_suffix('.png')).convert('RGB')
        assert png.size==reconstructed.size and png.tobytes()==reconstructed.tobytes()
        pdf=svg.with_suffix('.pdf').read_bytes()
        assert pdf.startswith(b'%PDF-') and b'%%EOF' in pdf[-64:]
        render.append(dict(figure=name,data_markers=count,png_matches_svg=True,pdf_present=True))
    for name in ['README.md','tables.md','boot-results.md','evaluation-text.md','visual-contract.md']:
        text=(OUT/name).read_text()
        for link in re.findall(r'\]\(([^)]+)\)',text):assert (OUT/link).exists(),(name,link)
    tex=list(OUT.glob('table-*.tex'));assert len(tex)==6
    for p in tex:
        s=p.read_text();assert s.count('\\begin{tabular}')==s.count('\\end{tabular}')==1
    result=dict(status='PASS',scope='complete clean READ evidence; all 38 comparisons',commands=commands,
                required_deliverables=dict(data_matrix='16 distinct READ boots; archived inputs and actual packages verified',
                                           statistics='boot-level delta CI + block/leave-one-out/mean sensitivity',
                                           paths='19 workloads; actual carrier/public/kernel module instructions',
                                           presentation='38 rows; six LaTeX fragments; three SVG/PDF/PNG figures; Chinese evaluation prose'),
                claims=claims,render=render,
                visual_review='Three actual PNGs inspected: labels, intervals, axes and legend clear; full ranges retained',
                latex='booktabs fragments; syntax checked, no full manuscript compilation requested')
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'verification.log').write_text('\n'.join(logs)+'\nRequirement, numerical and render checks: PASS\n')
    print(json.dumps(dict(status='PASS',comparisons=len(table),boot_api_units=len(boot),figures=len(render)),indent=2))

if __name__=='__main__':main()
