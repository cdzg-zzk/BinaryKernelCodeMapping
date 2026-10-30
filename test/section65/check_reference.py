#!/usr/bin/env python3
"""Compare kernel file bytes with GNU iso-read without treating CLI time as a benchmark."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    tools = HERE / 'build/tools/usr'
    env = dict(os.environ, LD_LIBRARY_PATH=str(tools / 'lib/x86_64-linux-gnu'))
    manifest = json.loads((args.reference / 'evidence/result.json').read_text())
    records = []
    for case in manifest['cases']:
        if case['mode'] != 'default':
            continue  # iso-read's CLI does not expose the kernel's norock option.
        rows = json.loads((args.reference / 'evidence' / case['manifest']).read_text())
        for row in rows:
            if 'sha256' not in row:
                continue
            output = out / 'extracted.tmp'
            if output.exists():
                output.unlink()
            command = [str(tools / 'bin/iso-read'), '--no-header', '-i',
                       str(HERE / 'build/images' / case['image']),
                       '-e', '/' + row['path'], '-o', str(output)]
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            data = output.read_bytes() if output.exists() else None
            digest = hashlib.sha256(data).hexdigest() if data is not None else None
            records.append(dict(image=case['image'], path=row['path'],
                                returncode=result.returncode, stderr=result.stderr,
                                stdout=result.stdout, bytes=len(data) if data is not None else None,
                                expected_bytes=row['size'], sha256=digest,
                                expected_sha256=row['sha256'],
                                equal=result.returncode == 0 and digest == row['sha256']))
    if (out / 'extracted.tmp').exists():
        (out / 'extracted.tmp').unlink()
    (out / 'files.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
    summary = dict(scope='GNU libiso9660 CLI byte oracle; no performance samples',
                   compared=len(records), equal=sum(r['equal'] for r in records),
                   mismatches=[{'image':r['image'],'path':r['path'],'returncode':r['returncode']}
                               for r in records if not r['equal']])
    (out / 'result.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
