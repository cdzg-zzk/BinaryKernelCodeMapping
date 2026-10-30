#!/usr/bin/env python3
"""Add SIF's sector-aligned partition offset to a separate lklfuse frontend.

The pinned filesystem and LKL library are unchanged. This wrapper uses their
existing synchronous POSIX block callbacks and retains the unmodified binary.
"""
import argparse
import difflib
import json
import os
from pathlib import Path
import subprocess

SECTION = Path(__file__).resolve().parents[1]
BOUNDARY = r'''
static int offset_capacity(struct lkl_disk disk, unsigned long long *bytes)
{
	int ret = lkl_dev_blk_ops.get_capacity(disk, bytes);
	if (ret || lklfuse.offset > *bytes || lklfuse.offset % 512)
		return -1;
	*bytes -= lklfuse.offset;
	return 0;
}

static int offset_request(struct lkl_disk disk, struct lkl_blk_req *request)
{
	struct lkl_blk_req adjusted = *request;
	if (request->type == LKL_DEV_BLK_TYPE_READ ||
	    request->type == LKL_DEV_BLK_TYPE_WRITE) {
		if (request->sector > (~0ULL / 512) - lklfuse.offset / 512)
			return LKL_DEV_BLK_STATUS_IOERR;
		adjusted.sector += lklfuse.offset / 512;
	}
	return lkl_dev_blk_ops.request(disk, &adjusted);
}

static struct lkl_dev_blk_ops offset_ops = {
	.get_capacity = offset_capacity,
	.request = offset_request,
};
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=Path, default=SECTION/'build/lkl/build-squash-only')
    args = p.parse_args(); build = args.build.resolve()
    provenance = json.loads((SECTION/'build/lkl/acquisition-03.json').read_text())
    source = Path(provenance['directory'])/'tools/lkl'
    original = (source/'lklfuse.c').read_text()
    changed = original.replace('\tint mb;\n', '\tint mb;\n\tunsigned long long offset;\n')
    changed = changed.replace('#define LKLFUSE_OPT', BOUNDARY+'\n#define LKLFUSE_OPT', 1)
    changed = changed.replace('LKLFUSE_OPT("mb=%d", mb, 0),',
                              'LKLFUSE_OPT("mb=%d", mb, 0),\n\tLKLFUSE_OPT("offset=%llu", offset, 0),')
    changed = changed.replace('\tlklfuse.disk.fd = ret;', '\tlklfuse.disk.fd = ret;\n\tlklfuse.disk.ops = &offset_ops;')
    out = build/'sif-frontend'; out.mkdir(exist_ok=False)
    (out/'lklfuse.c').write_text(changed)
    (out/'frontend.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),
         changed.splitlines(True), fromfile='a/tools/lkl/lklfuse.c', tofile='b/tools/lkl/lklfuse.c')))
    command = ['gcc', '-O2', '-g', '-Wall', '-Wextra', '-Wno-unused-parameter',
               '-Wno-missing-field-initializers', '-fno-strict-aliasing', '-fPIC', '-pthread',
               '-D_FILE_OFFSET_BITS=64', '-I'+str(build/'tools/lkl/include'),
               '-I'+str(source/'include'), '-I'+str(SECTION/'build/fuse-deps/usr/include'),
               str(out/'lklfuse.c'), str(build/'tools/lkl/liblkl.a'), '-pie', '-Wl,-z,noexecstack',
               '-lrt', '-lpthread', '-Wl,-l:libfuse3.so.3', '-o', str(out/'lklfuse')]
    subprocess.run(command, check=True)
    (out/'build.json').write_text(json.dumps(dict(status='built', commands=[command],
        source=provenance, added_lines=len(changed.splitlines())-len(original.splitlines()),
        boundary='512-byte-aligned offset through existing POSIX disk operations'), indent=2)+'\n')


if __name__ == '__main__':main()
