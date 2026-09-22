#!/usr/bin/env python3
"""Build observers around the repository's complete algorithm benchmark helpers."""
from pathlib import Path
import argparse,json,subprocess
ROOT=Path(__file__).resolve().parents[3]
def build(output):
    output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=True)
    commands=[]
    for name in ('clock','lz4','bch','xz','lz4-plain'):
        source_name = 'lz4' if name == 'lz4-plain' else name
        argv=['gcc','-O2','-g','-std=gnu11','-Wall','-Wextra','-Wno-unused-function',
              '-I'+str(ROOT/'test/test_xz/kmod'),str(ROOT/'test/evaluation/setup'/f'{source_name}.c'),
              '-ldl','-o',str(output/f'setup-{name}')]
        if name == 'lz4-plain': argv.insert(1, '-DVKSO_SETUP_UNINSTRUMENTED')
        result=subprocess.run(argv,text=True,capture_output=True)
        commands.append(dict(argv=argv,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
        (output/'build.json').write_text(json.dumps(commands,indent=2)+'\n')
        if result.returncode: raise RuntimeError(result.stderr)
    return output
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);print(build(p.parse_args().output))
