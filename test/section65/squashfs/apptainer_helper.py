#!/usr/bin/env python3
"""Translate Apptainer's squashfuse helper arguments to the reader frontend."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    own, helper = sys.argv[1:].index('--'), None
    configuration, helper = sys.argv[1:1+own], sys.argv[2+own:]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--frontend', required=True)
    p.add_argument('--core', default='-')
    p.add_argument('--bridge', default='-')
    p.add_argument('--trace', type=Path, required=True)
    p.add_argument('--kind', choices=['reader', 'stock', 'lkl'], default='reader')
    p.add_argument('--memory', type=int, default=16)
    args = p.parse_args(configuration)
    if not helper:
        print('usage: squashfuse_ll -f [-o uid=N,gid=N,offset=N,ro,allow_other] IMAGE MOUNT')
        return
    p = argparse.ArgumentParser(prog='squashfuse_ll')
    p.add_argument('-f', action='store_true')
    p.add_argument('-o', action='append', default=[])
    p.add_argument('image')
    p.add_argument('mount')
    mount = p.parse_args(helper)
    if not mount.f:
        p.error('the Apptainer adapter expects foreground mode (-f)')
    options, offset = [], 0
    for option in ','.join(mount.o).split(','):
        if option.startswith('offset='):
            offset = int(option.split('=', 1)[1])
            if not 0 <= offset < 1 << 64:
                p.error('partition offset is outside uint64')
        elif option:
            options.append(option)
    if args.kind == 'reader':
        command = [args.frontend, args.core, args.bridge, mount.image, str(offset), mount.mount]
        if options:
            command.append(','.join(options))
    elif args.kind == 'stock':
        command = [args.frontend, *helper]
    else:
        command = [args.frontend, mount.image, mount.mount, '-f', '-s', '-o',
                   ','.join(options+[f'type=squashfs',f'mb={args.memory}',f'offset={offset}'])]
    with args.trace.open('a') as log:
        log.write(json.dumps(dict(pid=os.getpid(), source=mount.image, target=mount.mount,
                                  offset=offset, options=options, command=command))+'\n')
    os.execv(command[0], command)


if __name__ == '__main__':
    main()
