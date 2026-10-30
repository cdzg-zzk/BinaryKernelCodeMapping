#!/usr/bin/env python3
"""Same-inode pathname perturbation; mounted-work diagnostic, not app timing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
from check_fuse import mounted


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def ticks(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return int(fields[11]) + int(fields[12])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--blocks', type=int, default=8)
    p.add_argument('--seed', type=int, default=66501)
    a = p.parse_args()
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(__file__, out/'runner.py')
    build = ROOT/'test/section65/build/squashfs/evaluation-improved-01/build'
    source = {'core.so': ROOT/'test/evaluation-local/runs/iso9660/squash-minimal-deployment-01/libsq-materialized.so',
              'bridge.so': build/'libsq-bridge.so', 'frontend': build/'vkso-squashfuse'}
    image = ROOT/'test/section65/build/squashfs/application-images-01/xz.sif'
    target = out/'mount'; target.mkdir()
    levels = [0, 8, 16, 24, 32]
    paths = {}
    for level in levels:
        d = out/('p'+'x'*level); d.mkdir(); paths[level] = d
        for name, src in source.items():
            os.link(src, d/name)
            assert (d/name).stat().st_ino == src.stat().st_ino
    state = dict(status='running', scope=__doc__, seed=a.seed, blocks=a.blocks,
                 sources={k: dict(path=str(v), sha256=digest(v), inode=v.stat().st_ino) for k,v in source.items()},
                 image=dict(path=str(image), sha256=digest(image)), rows=[],
                 timing='Fresh mounted helper; image backing warmed; tar task only; observer after timing.',
                 affinity='helper and tar CPUs 1,2; driver CPU 0',
                 environment=dict(uname=list(os.uname()), clock_ticks=os.sysconf('SC_CLK_TCK'),
                                  boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))
    def save(): (out/'result.json').write_text(json.dumps(state, indent=2)+'\n')
    save(); expected = None; rng = random.Random(a.seed)
    try:
        with tempfile.TemporaryDirectory(prefix='sq-path-', dir='/dev/shm') as scratch:
            payload = Path(scratch)/'output.tar'
            for block in range(a.blocks):
                order = levels.copy(); rng.shuffle(order)
                for level in order:
                    name = f'b{block:02d}-p{level:02d}'
                    d = paths[level]
                    with image.open('rb') as f:
                        while f.read(1 << 20): pass
                    command = ['taskset','-c','1,2', str(d/'frontend'), str(d/'core.so'),
                               str(d/'bridge.so'), str(image), '36864', str(target)]
                    with mounted(command, target, out/(name+'.log')) as child:
                        cpu0 = ticks(child.pid); start = time.perf_counter()
                        task = subprocess.run(['taskset','-c','1,2','tar','-cf',str(payload),
                                               '-C',str(target/'opt/stream-data'),'.'],
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
                        elapsed = time.perf_counter()-start; cpu1 = ticks(child.pid)
                        assert task.returncode == 0, task.stderr
                        observed = digest(payload)
                        if expected is None: expected = observed
                        assert observed == expected
                        (out/(name+'-maps.txt')).write_text(Path(f'/proc/{child.pid}/maps').read_text())
                        script = out/(name+'-gdb.py')
                        snapshot = out/(name+'-addresses.json')
                        script.write_text('''import gdb, json
im=gdb.parse_and_eval('(struct sq_image *)image_handle')
sb=im.dereference()['sb']['s_fs_info'].cast(gdb.lookup_type('struct squashfs_sb_info').pointer())
st=sb.dereference()['stream'].cast(gdb.lookup_type('struct user_stream').pointer())
r={'image':int(im),'filesystem':int(sb),'stream':int(st),'codec':int(st.dereference()['codec']),'output':int(st.dereference()['output'])}
for field in ['block_cache','fragment_cache','read_page']:
 c=sb.dereference()[field]
 if int(c):
  r[field]=int(c)
  r[field+'_buffers']=[int(c.dereference()['entry'][i]['data'][0]) for i in range(int(c.dereference()['entries']))]
open('''+repr(str(snapshot))+''','w').write(json.dumps(r,indent=2)+'\\n')
''')
                        with (out/(name+'-gdb.log')).open('w') as log:
                            subprocess.run(['taskset','-c','0','gdb','-q','-nx','-batch','-p',str(child.pid),
                                            '-ex','add-symbol-file '+str(HERE.parent/'build/squashfs/debug-types-01/types.o')+' 0',
                                            '-ex','source '+str(script),'-ex','detach'],
                                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30)
                        addresses = json.loads(snapshot.read_text())
                    row = dict(block=block,padding=level,order=order,wall_seconds=elapsed,
                               helper_cpu_seconds=(cpu1-cpu0)/os.sysconf('SC_CLK_TCK'),
                               output_sha256=observed,output_bytes=payload.stat().st_size,
                               command=command,addresses=addresses)
                    state['rows'].append(row); save(); payload.unlink()
                    print(block, level, round(elapsed,6), flush=True)
        state['summary'] = {str(level): dict(wall_median=statistics.median(r['wall_seconds'] for r in state['rows'] if r['padding']==level),
                                            cpu_median=statistics.median(r['helper_cpu_seconds'] for r in state['rows'] if r['padding']==level))
                            for level in levels}
        state.update(status='complete', finished=time.time())
    except BaseException:
        state.update(status='failed', error=traceback.format_exc()); raise
    finally: save()


if __name__ == '__main__': main()
