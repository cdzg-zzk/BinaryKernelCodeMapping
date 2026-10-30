#!/usr/bin/env python3
"""Original-scale direct-adapter retention diagnostic, not FUSE/application data."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65';HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    runs=(SECTION/'build/squashfs/optimization-runs-01').resolve();out=runs/'cache-scale-direct-01';out.mkdir()
    bridge=runs/'builds/optimization-cache-01/libsq-copy.so'
    subprocess.run(['gcc','-O2','-Wall','-Wextra',str(HERE/'cache_scale.c'),'-ldl','-o',str(out/'bench')],check=True)
    result=dict(status='running',scope='Direct private adapter on unchanged original scale SIFs. Excludes FUSE and application startup; not subtracted from process results as a calibrated component cost. malloc_trim is diagnostic-only.',cases=[],bridge_sha256=sha(bridge))
    for scale in [1,4,16]:
        image=SECTION/'build/squashfs/refine-scale-images-01'/f'scale-{scale}.sif'
        raw=subprocess.check_output([str(out/'bench'),str(bridge),str(image),'36864'],text=True)
        (out/f'scale-{scale}.jsonl').write_text(raw)
        rows=[json.loads(line) for line in raw.splitlines()];assert len(rows)==5
        assert all(r['entries']==scale*5866+1 for r in rows if r['phase'].startswith('scan-'))
        result['cases'].append(dict(scale=scale,image_sha256=sha(image),snapshots=rows))
    result['status']='complete';(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
