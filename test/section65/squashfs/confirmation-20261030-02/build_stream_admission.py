#!/usr/bin/env python3
"""Keep large-file streams from cycling through the small-file data cache."""
import difflib,json,shutil,subprocess,sys,hashlib
from pathlib import Path
from prerequisite import ROOT,RUNS,verify

verify()
base=RUNS/'builds/data-cache-controls-02/data-16'
out=RUNS/'builds/data-cache-stream-01';shutil.copytree(base,out)
p=out/'xz-user-source/user_bridge.c';before=p.read_text();text=before
old='    struct squashfs_cache_entry busy;';assert text.count(old)==1
text=text.replace(old,old+'\n    struct squashfs_cache *stream_data;')
old='    free(im->sb.s_root);';assert text.count(old)==1
text=text.replace(old,'    u_cache_delete(im->stream_data);\n'+old)
old='            e=squashfs_get_datablock(i->i_sb,block,length);';assert text.count(old)==1
text=text.replace(old,'''            /* Single-thread private reader: files larger than the bounded
             * data working set use one reusable streaming buffer. Keep the
             * same common get_datablock path and restore its private binding
             * before returning to the caller. Small files retain reuse. */
            if (i->i_size > (u64)s->read_page->entries * s->block_size) {
                struct sq_image *im=image_of(i->i_sb);
                struct squashfs_cache *retained=s->read_page;
                if (!im->stream_data) im->stream_data=u_cache_init("stream",1,s->block_size);
                if (!im->stream_data) return -ENOMEM;
                s->read_page=im->stream_data;
                e=squashfs_get_datablock(i->i_sb,block,length);
                s->read_page=retained;
            } else {
                e=squashfs_get_datablock(i->i_sb,block,length);
            }''')
p.write_text(text)
(out/'stream-admission.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='data16/user_bridge.c',tofile='stream-admission/user_bridge.c')))
args=[sys.executable,str(ROOT/'test/section65/squashfs/build_user.py'),'--build',str(out),'--source-dir',str(out/'xz-user-source'),'--directory-cache','--direct-decode','--shared-lz4','--shared-xz']
with (out/'stream-build.log').open('w') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
for n in ['vkso_sq_core.ko','vkso_squashfs.ko']:
    assert (out/n).read_bytes()==(base/n).read_bytes()
(out/'stream-admission.json').write_text(json.dumps(dict(status='built',predecessor=str(base),
    rationale='All stream candidates decode the same 1027 blocks and have 2052 cache misses. Larger retained buffer rotation adds work without hits in large sequential files. Use one scratch slot for files exceeding the fixed data budget, preserving bounded reuse for smaller files.',
    policy='16 lazy private data slots plus one lazy large-file stream slot; threshold is fixed cache byte capacity. Same core, codecs, frontend and immutable-image semantics.',
    source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='Candidate, not promoted; validate stream/Python tradeoff before formal confirmation.'),indent=2)+'\n')
print('Built stream-admission candidate with unchanged owner')
