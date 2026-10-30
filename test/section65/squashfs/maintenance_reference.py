#!/usr/bin/env python3
"""Same-version unadapted SquashFS with the negative-offset patch, guest only."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SECTION = HERE.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--maintenance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--relaxed', action='store_true',
        help='diagnostic: align mitigation/instrumentation flags, retain kernel addressing')
    args = parser.parse_args()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    source = SECTION/'build/native/linux-5.15.198/fs/squashfs'
    build = out/'build'; shutil.copytree(source, build)
    # Only registration identity and the upstream check change in the original driver.
    changes = []
    for name in ['cache.c', 'super.c', 'Makefile']:
        path = build/name; before = path.read_text(); after = before
        if name == 'cache.c':
            start = before.index('int squashfs_copy_data(')
            end = before.index('\n}', start)
            body = before[start:end]
            assert body.count('if (length == 0)') == 1
            after = before[:start]+body.replace('if (length == 0)', 'if (length == 0 || offset < 0)')+before[end:]
        elif name == 'super.c':
            after = before.replace('.name = "squashfs"', '.name = "sqreference"')
            assert after != before
        else:
            after = before.replace('obj-$(CONFIG_SQUASHFS) += squashfs.o', 'obj-m += sq_reference.o')
            after = after.replace('squashfs-y', 'sq_reference-y').replace('squashfs-$(', 'sq_reference-$(')
            if args.relaxed:
                after += ('\nccflags-remove-y += -pg -mfentry -mrecord-mcount -fstack-protector-strong\n'
                          'ccflags-y += -fno-stack-protector -mfunction-return=keep -mindirect-branch=keep -D__NO_FORTIFY\n'
                          'UBSAN_SANITIZE := n\n')
        path.write_text(after)
        changes.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                       fromfile='original/'+name, tofile='fixed-reference/'+name))
    (out/'reference.patch').write_text(''.join(changes))
    with (out/'build.log').open('w') as log:
        subprocess.run(['make', '-C', str(SECTION/'build/native/kernel'), f'M={build}', '-j2', 'modules'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    pkg = out/'package'; shutil.copytree(args.maintenance.resolve()/'fixed-package', pkg)
    shutil.copy2(build/'sq_reference.ko', pkg/'sq_reference.ko')
    (pkg/'reference_test.py').write_text('''import hashlib,json,subprocess
from pathlib import Path
from reference_guest import manifest
p=Path('/work/package'); o=Path('/work/evidence'); o.mkdir(); m=o/'mount'; m.mkdir()
result={'status':'running','scope':'unadapted 5.15.198 with same upstream patch; TCG functional only'}
def cmd(*args): subprocess.run(list(map(str,args)),check=True)
try:
 cmd('insmod',p/'sq_reference.ko')
 result['cases']=[]
 for image in [p/'case/valid.squashfs',p/'case/negative.squashfs',*sorted((p/'images').glob('*.squashfs'))]:
  cmd('mount','-t','sqreference','-o','ro,loop',image,m)
  try:
   row={'image':image.name}
   if image.parent.name=='case':
    try:
     data=(m/'payload').read_bytes()
     row.update(errno=0,bytes=len(data),zero_filled=not any(data),sha256=hashlib.sha256(data).hexdigest())
     if image.name=='valid.squashfs': assert data==(p/'case/source/payload').read_bytes()
    except OSError as e: row['errno']=e.errno
   else:
    rows=manifest(m); assert rows==json.loads((p/'reference'/(image.stem+'-squashfs.json')).read_text())
    row.update(entries=len(rows),status='pass')
   result['cases'].append(row)
  finally: cmd('umount',m)
 cmd('rmmod','sq_reference'); result.update(status='complete',modules_unloaded=True)
finally: (o/'result.json').write_text(json.dumps(result,indent=2)+'\\n')
''')
    (pkg/'run.sh').write_text('#!/bin/bash\nset -eu\ncd /work/package\nexec python3 reference_test.py\n')
    identity = dict(source=str(source),relaxed=args.relaxed,
                    interpretation='flag diagnostic, not additive causal decomposition; original kernel addressing retained',
                    module_sha256=hashlib.sha256((build/'sq_reference.ko').read_bytes()).hexdigest())
    (out/'identity.json').write_text(json.dumps(identity, indent=2)+'\n')
    subprocess.run([sys.executable, str(SECTION/'native/qemu.py'), '--package', str(pkg),
                    '--output', str(out/'guest'), '--native-ide', '--kernel',
                    '/boot/vkso-final-raw-normal-5.15.198.bzImage', '--timeout', '1200'], check=True)


if __name__ == '__main__':
    main()
