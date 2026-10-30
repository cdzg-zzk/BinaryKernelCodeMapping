#!/usr/bin/env python3
"""Build the private reader and FUSE application against the prepared core ABI."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
SECTION = HERE.parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,default=SECTION/'build/squashfs/reader-adapted')
    p.add_argument('--kdir',type=Path,default=SECTION/'build/native/kernel')
    p.add_argument('--source-dir',type=Path,default=HERE)
    p.add_argument('--profile',action='store_true',help='diagnostic counters; not formal timing')
    p.add_argument('--bridge-only',action='store_true',help='use a separately materialized identical core')
    p.add_argument('--directory-cache',action='store_true',help='candidate: retain one list per open directory')
    p.add_argument('--direct-decode',action='store_true',help='candidate: decode into contiguous actor storage')
    p.add_argument('--shared-lz4',action='store_true',help='candidate: same-owner safe LZ4 decoder, no user liblz4')
    p.add_argument('--bind-lz4',action='store_true',help='diagnostic: bind composed owner but retain user-library decoding')
    p.add_argument('--shared-xz',action='store_true',help='use the common native XZ decoder and remove liblzma')
    p.add_argument('--bind-xz',action='store_true',help='bind XZ services while using the library decoder control')
    p.add_argument('--retain-lz4-dependency',action='store_true',help='diagnostic: retain liblz4 even when decoding with the common body')
    p.add_argument('--retain-xz-dependency',action='store_true',help='diagnostic: retain liblzma even when decoding with the common body')
    args=p.parse_args(); out=args.build.resolve(); kdir=args.kdir.resolve()
    source=args.source_dir.resolve()
    diagnostic=['-DVKSO_SQ_PROFILE'] if args.profile else []
    if args.directory_cache:diagnostic+=['-DVKSO_SQ_DIRECTORY_CACHE']
    if args.direct_decode:diagnostic+=['-DVKSO_SQ_DIRECT_DECODE']
    if args.shared_lz4:diagnostic+=['-DVKSO_SQ_SHARED_LZ4']
    if args.bind_lz4:diagnostic+=['-DVKSO_SQ_BIND_LZ4']
    if args.shared_xz:diagnostic+=['-DVKSO_SQ_SHARED_XZ']
    if args.bind_xz:diagnostic+=['-DVKSO_SQ_BIND_XZ']
    flags=shlex.split((out/'.shared_core.o.cmd').read_text().splitlines()[0].split(' := ',1)[1])
    flags=flags[:flags.index('-c')]
    flags=[f for f in flags if not f.startswith(('-Wp,-MMD','-DKBUILD_','-D__KBUILD_','-mpreferred-stack-boundary'))]
    flags+=['-fPIC','-mpreferred-stack-boundary=4','-I'+str(out),'-Wno-declaration-after-statement']
    commands=[]
    def run(command,cwd=None):
        commands.append(command);subprocess.run(command,cwd=cwd,check=True)
    run(flags+diagnostic+['-c',str(source/'user_bridge.c'),'-o',str(out/'user_bridge.o')],kdir)
    run(['gcc','-O2','-g','-Wall','-Wextra','-Werror','-fPIC',*diagnostic,
         '-I'+str(out),
         '-I'+str(SECTION/'build/squashfs/deps/usr/include'),'-c',str(source/'posix_io.c'),'-o',str(out/'posix_io.o')])
    libs=['-lz','-Wl,-l:liblzma.so.5','-Wl,-l:libzstd.so.1','-Wl,-l:liblz4.so.1','-Wl,-l:liblzo2.so.2']
    if args.shared_lz4:libs.remove('-Wl,-l:liblz4.so.1')
    if args.shared_xz:libs.remove('-Wl,-l:liblzma.so.5')
    if args.retain_lz4_dependency:libs+=['-Wl,--no-as-needed','-Wl,-l:liblz4.so.1','-Wl,--as-needed']
    if args.retain_xz_dependency:libs+=['-Wl,--no-as-needed','-Wl,-l:liblzma.so.5','-Wl,--as-needed']
    for name,core in [('libsq-copy.so',['shared_core.o']),('libsq-bridge.so',[])]:
        if core and args.shared_lz4:core+=['shared_lz4.o']
        if core and (args.shared_xz or args.bind_xz):core+=['xz_dec_stream.o','xz_dec_lzma2.o','xz_dec_bcj.o','xz_support.o']
        if args.bridge_only and core:continue
        run(['gcc','-shared','-Wl,-Bsymbolic',*(['-Wl,-z,defs'] if core else []),'-o',str(out/name)]+
            [str(out/f) for f in core+['user_bridge.o','posix_io.o']]+libs)
    run(['gcc','-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror',*diagnostic,
         '-I'+str(SECTION/'build/fuse-deps/usr/include/fuse3'),str(source/'fuse_frontend.c'),
         '-Wl,-l:libfuse3.so.3','-ldl','-o',str(out/'vkso-squashfuse')])
    run(['gcc','-std=gnu11','-O2','-g','-Wall','-Wextra','-Werror',
         str(source/'apptainer_helper.c'),'-o',str(out/'vkso-squash-helper')])
    (out/'user-build.json').write_text(json.dumps(dict(status='built',commands=commands),indent=2)+'\n')
    print(json.dumps(dict(status='built',output=str(out))))


if __name__=='__main__':main()
