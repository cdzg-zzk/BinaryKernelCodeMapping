#!/usr/bin/env python3
"""Regenerate all numeric tables, plots and static evidence, without kernel execution."""
import argparse
import subprocess
import sys
from pathlib import Path
from layer3_v2 import ROOT, sha
import json

p=argparse.ArgumentParser();p.add_argument('--fixed',type=Path,default=ROOT/'results/layer3-fixed-batch-v2');p.add_argument('--campaign',type=Path,default=ROOT/'results/layer3-confirmatory-v2');a=p.parse_args()
def run(script,*args):subprocess.run([sys.executable,str(ROOT/'scripts'/script),*map(str,args)],check=True)
archive=ROOT/'results/layer3'
for rel,h in json.loads((a.fixed/'historical-hashes.json').read_text()).items():
    # Hash list is relative to the benchmark root.
    assert sha(ROOT/rel)==h,rel
run('layer3_v2.py','reanalyze','--archive',archive,'--calibration',a.fixed/'calibration/calibration.json','--output',a.fixed)
run('layer3_v2.py','summarize','--campaign',a.campaign,'--config',a.fixed/'fixed-batches.json','--output',a.campaign)
run('static_layer3_v2.py','--campaign',a.campaign)
for folder in [a.fixed,a.campaign]:run('plot_layer3_v2.py','--analysis',folder)
run('report_layer3_v2.py','--fixed',a.fixed,'--campaign',a.campaign)
print('Reproduced all Layer-3 v2 analyses, tables, diagnostic inventories and figures; historical hashes intact.')
