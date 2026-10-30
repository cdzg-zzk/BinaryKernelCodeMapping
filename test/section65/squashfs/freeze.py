#!/usr/bin/env python3
"""Freeze the evaluated filesystem implementation, build identity and scripts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

SECTION = Path(__file__).resolve().parents[1]
ROOT = SECTION.parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    records = []
    def save(source, target):
        dest = out/target; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        records.append(dict(source=str(source), snapshot=str(target), bytes=dest.stat().st_size,
                            sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
    for path in a.build.resolve().iterdir():
        if path.is_file() and (path.suffix in ('.c','.h','.ko','.so','.json','.txt','.cmd') or
                path.name in ('Makefile','vkso-squashfuse','vkso-squash-helper','Module.symvers')):
            save(path, Path('build')/path.name)
        elif path.is_dir() and (path.name.endswith('source') or path.name=='source'):
            for item in path.rglob('*'):
                if item.is_file() and item.suffix in ('.c','.h','.json'):
                    save(item,Path('build')/item.relative_to(a.build.resolve()))
    for directory in [SECTION, SECTION/'squashfs', SECTION/'native', SECTION/'lkl']:
        for path in directory.iterdir():
            if path.is_file() and (path.suffix in ('.py','.c','.h') or path.name.endswith('-queue.json')):
                save(path, Path('source')/path.relative_to(SECTION))
    for directory in ['improvement','refinement']:
        for path in (SECTION/'squashfs'/directory).iterdir():
            if path.is_file() and path.suffix in ('.py','.c','.h','.json','.md','.tex'):
                save(path,Path('source')/path.relative_to(SECTION))
    for path in [ROOT/'make_dll/build_PIC_so.py', SECTION/'build/native/kernel/.config']:
        save(path, Path('inputs')/path.name)
    for name in ['README.md','STATUS.md','research-protocol.md','improvement-protocol.md','claim-experiment-map.md','related-work-comparison.md','reproduce.md','backend-conditions.md',
                 'claim-verdicts.json','squashfs/README.md','native/README.md','lkl/README.md']:
        save(SECTION/name,Path('documentation')/name)
    for name in ['plot_filesystem.py','plot_filesystem_improved.py','plot_filesystem_refined.py','build_filesystem_section.py','evaluation-requirements.txt',
                 'paper_content/sections/06-evaluation.tex','paper_content/references.bib','tables/filesystem-business.tex',
                 'paper_content/Paper Draft.md','design/chapter3_general_os_design.md','design/chapter4_linux_state_binding.md']:
        save(ROOT/'paper'/name,Path('paper')/name)
    save(ROOT/'paper/notes/section65-alignment.md',Path('paper/notes/section65-alignment.md'))
    diff = subprocess.check_output(['git','diff','HEAD','--','make_dll','test/section65'], cwd=ROOT)
    (out/'tracked.patch').write_bytes(diff)
    identity = dict(created=time.time(), revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    files=records, note='Untracked section65 sources are captured explicitly; tracked.patch alone is not the implementation.',
                    copied_control='Formal runs materialize copied bytes from the registered owner. The retained old libsq-copy.so is an unused earlier build artifact, not the formal copied control.',
                    compiler=subprocess.check_output(['gcc','--version'],text=True),
                    kernel=subprocess.check_output(['uname','-a'],text=True))
    (out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
    print(json.dumps(dict(snapshot=str(out),files=len(records))))


if __name__ == '__main__':
    main()
