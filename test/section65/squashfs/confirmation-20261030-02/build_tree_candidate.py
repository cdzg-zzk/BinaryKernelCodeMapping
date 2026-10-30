#!/usr/bin/env python3
"""Build the finite bit-tree hypothesis under unchanged production flags."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from prerequisite import ROOT, RUNS, verify

SECTION = ROOT / 'test/section65'
OLD = SECTION / 'squashfs/optimization-20261030-01'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    verify()
    diagnostic = RUNS / 'bittree-diagnostic-03'
    assert json.loads((diagnostic/'result.json').read_text())['status'] == 'complete'
    assert json.loads((RUNS/'python-attribution-queue-02/result.json').read_text())['status'] == 'complete'
    out = a.output.resolve()
    base = RUNS/'builds/optimization-cache-01'
    shutil.copytree(base, out)
    before = (base/'xz_dec_lzma2.c').read_text()
    after = (diagnostic/'tree-unrolled/xz_dec_lzma2.c').read_text()
    (out/'xz_dec_lzma2.c').write_text(after)
    (out/'tree-unrolling.patch').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile='word/xz_dec_lzma2.c', tofile='tree/xz_dec_lzma2.c')))
    for old in [str(base), str(SECTION/'build/squashfs/optimization-cache-01')]:
        path = out/'Makefile'
        path.write_text(path.read_text().replace(old, str(out)))
    state = dict(status='building', predecessor=str(base),
        edited_algorithm_bodies=['dict_repeat', 'rc_bittree'],
        scope='Candidate only. Same word-copy, private LRU and compiler policies; fixed-depth tree unrolling adds code size. No timing claim until complete-task pilot.',
        commands=[])
    def save():
        (out/'tree-candidate.json').write_text(json.dumps(state,indent=2)+'\n')
    save()
    try:
        with (out/'tree-build.log').open('w') as log:
            def run(cmd):
                cmd=list(map(str,cmd)); state['commands'].append(cmd)
                subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
            run(['make','-C',SECTION/'build/native/kernel','M='+str(out),'-j2','modules'])
            run([sys.executable,SECTION/'squashfs/build_user.py','--build',out,
                 '--source-dir',out/'xz-user-source','--directory-cache','--direct-decode','--shared-lz4','--shared-xz'])
        # Distinguish unchanged integration from the changed common algorithm.
        for name in ['shared_core.c','shared_lz4.c','xz-user-source/user_bridge.c',
                     'xz-user-source/posix_io.c','xz-user-source/fuse_frontend.c']:
            assert sha(out/name) == sha(base/name), name
        state.update(status='built', hashes={n:sha(out/n) for n in [
            'xz_dec_lzma2.c','vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse']},
            size=subprocess.check_output(['size',out/'vkso_sq_core.ko'],text=True))
    except BaseException as exc:
        state.update(status='failed',error=repr(exc)); raise
    finally:
        save()
    print(json.dumps(state,indent=2))

if __name__ == '__main__':
    main()
