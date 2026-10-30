#!/usr/bin/env python3
"""Compile the domain adapter against the pinned kernel's private layout ABI."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import adapt

HERE = Path(__file__).resolve().parent
OUT = HERE / 'build/adapted'
KDIR = Path('/usr/src/linux-headers-5.15.0-119-generic')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=OUT)
    p.add_argument('--kdir',type=Path,default=KDIR)
    p.add_argument('--lookup-cache',action='store_true',help='cache successful names within each read-only image handle')
    args=p.parse_args()
    build=args.build.resolve()
    kdir=args.kdir.resolve()
    # Reuse the actual compiler/header/config command that built the shared core.
    flags = shlex.split((build/'.shared_core.o.cmd').read_text().splitlines()[0].split(' := ',1)[1])
    flags = flags[:flags.index('-c')]
    flags = [f for f in flags if not f.startswith(('-Wp,-MMD', '-DKBUILD_', '-D__KBUILD_', '-mpreferred-stack-boundary'))]
    flags += ['-fPIC', '-mpreferred-stack-boundary=4', '-I'+str(build), '-Wno-declaration-after-statement']
    if args.lookup_cache: flags += ['-DISO_LOOKUP_CACHE=1']
    bindings = '#include <linux/slab.h>\n#include <linux/blkdev.h>\n#include "isofs.h"\n'
    for field, ret, params, target in adapt.SUPPORT:
        bindings += f'extern {ret} {target}({params});\n'
    bindings += 'struct iso_support iso_support;\nstatic const struct iso_support user_bindings = {\n'
    bindings += ''.join(f'.{f}={t},\n' for f,_,_,t in adapt.SUPPORT) + '};\n'
    bindings += 'void __attribute__((constructor)) iso_user_init(void) { iso_bind_support(&user_bindings); }\n'
    (build/'user_bindings.c').write_text(bindings)
    commands = []
    for source in [HERE/'user_bridge.c', build/'user_bindings.c']:
        command = flags + ['-c',str(source),'-o',str(build/(source.stem+'.o'))]
        commands.append(command)
        subprocess.run(command,cwd=kdir,check=True)
    command = ['gcc','-shared','-Wl,-Bsymbolic','-Wl,-z,defs','-o',str(build/'libisofs-copy.so'),
               str(build/'shared_core.o'),str(build/'user_bridge.o'),str(build/'user_bindings.o')]
    commands.append(command)
    subprocess.run(command,check=True)
    # Bridge-only DSO resolves its seven core calls from the registered carrier.
    # Its private initializer supplies the process's dependency table once.
    command = ['gcc','-shared','-Wl,-Bsymbolic','-o',str(build/'libiso-bridge.so'),
               str(build/'user_bridge.o'),str(build/'user_bindings.o')]
    commands.append(command)
    subprocess.run(command,check=True)
    (build/'user-build.json').write_text(json.dumps(commands,indent=2)+'\n')

if __name__ == '__main__': main()
