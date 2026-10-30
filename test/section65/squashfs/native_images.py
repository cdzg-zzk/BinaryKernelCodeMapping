#!/usr/bin/env python3
"""Compress the existing Apptainer root tree identically with five codecs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'test/evaluation-local/runs/iso9660/squash-apptainer-copied-02/rootfs')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    source = args.source.resolve()
    assert (source/'opt/linux-headers/linux/fs.h').is_file()
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    result = dict(status='running', source=str(source), workload_subtree='opt/linux-headers', cases=[])
    for compressor in ['gzip', 'xz', 'zstd', 'lz4', 'lzo']:
        image = out/(compressor+'.squashfs')
        command = ['mksquashfs', str(source), str(image), '-noappend', '-processors', '1',
                   '-comp', compressor, '-b', '131072', '-all-time', '1700000000',
                   '-mkfs-time', '1700000000', '-no-progress']
        with (out/(compressor+'.log')).open('w') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        result['cases'].append(dict(compressor=compressor, image=str(image), offset=0,
            bytes=image.stat().st_size, sha256=hashlib.sha256(image.read_bytes()).hexdigest(), command=command))
        (out/'images.json').write_text(json.dumps(result, indent=2)+'\n')
        print('built '+compressor, flush=True)
    result['status'] = 'complete'
    (out/'images.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__': main()
