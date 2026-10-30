#!/usr/bin/env python3
"""Account requested live directory-list storage; diagnostic builds only."""
import argparse,json
from pathlib import Path
import shutil,subprocess,sys,traceback
ROOT=Path(__file__).resolve().parents[4];HERE=ROOT/'test/section65/squashfs'

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--core',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);result=dict(status='running',scope='Requested live bytes for directory lists and handles only; excludes allocator overhead, realloc overlap, other caches and process memory.',cases=[])
    write=lambda:(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');write()
    try:
        for label,flags in [('rebuild-each-request',[]),('retain-per-handle',['--directory-cache'])]:
            build=out/(label+'-build');shutil.copytree(a.build,build);source=build/'memory-source';source.mkdir()
            for n in ['user_bridge.c','posix_io.c','fuse_frontend.c','apptainer_helper.c','profile.h']:
                shutil.copy2(a.build/'codec-user-source'/n,source/n)
            path=source/'fuse_frontend.c';s=path.read_text()
            marker='static void *image_handle;';assert s.count(marker)==1
            s=s.replace(marker,marker+'''
static unsigned long long names_live, names_peak;
static void names_add(size_t n) { names_live+=n; if (names_live>names_peak) names_peak=names_live; }
static void names_sub(size_t n) { if (n>names_live) abort(); names_live-=n; }
''')
            s=s.replace('names->items=items; names->cap=cap;','names_add((cap-names->cap)*sizeof(*items)); names->items=items; names->cap=cap;')
            s=s.replace('names->items[names->n++]=copy;','names_add(strlen(copy)+1); names->items[names->n++]=copy;')
            s=s.replace('for (size_t i=0;i<names->n;i++) free(names->items[i]);','for (size_t i=0;i<names->n;i++) { names_sub(strlen(names->items[i])+1); free(names->items[i]); }\n    names_sub(names->cap*sizeof(*names->items));')
            s=s.replace('handle->inode=inode;fi->fh=', 'names_add(sizeof(*handle)); handle->inode=inode;fi->fh=')
            s=s.replace('free_names(&handle->names);free(handle);','free_names(&handle->names);names_sub(sizeof(*handle));free(handle);')
            marker='    api.close_image(image_handle);';assert marker in s
            s=s.replace(marker,'    fprintf(stderr,"SQ_MEMORY {\\"peak_requested_bytes\\":%llu,\\"final_requested_bytes\\":%llu}\\n",names_peak,names_live);\n'+marker)
            path.write_text(s)
            with (out/(label+'-build.log')).open('w') as f:subprocess.run([sys.executable,HERE/'build_user.py','--build',build,'--source-dir',source,'--bridge-only','--profile','--shared-lz4','--direct-decode',*flags],stdout=f,stderr=subprocess.STDOUT,check=True)
            run=out/(label+'-run')
            with (out/(label+'-run.log')).open('w') as f:subprocess.run([sys.executable,HERE/'improvement/profile_user.py','--build',build,'--baseline',a.build,'--core',a.core,'--codecs','gzip','--workloads','scan','archive','--output',run],stdout=f,stderr=subprocess.STDOUT,check=True)
            for task in ['scan','archive']:
                lines=(run/f'gzip-{task}-profile.log').read_text().splitlines();records=[json.loads(l[len('SQ_MEMORY '):]) for l in lines if l.startswith('SQ_MEMORY ')]
                assert len(records)==1 and records[0]['final_requested_bytes']==0
                result['cases'].append(dict(variant=label,workload=task,**records[0]));write()
        result['status']='complete'
    except BaseException:result.update(status='failed',error=traceback.format_exc());raise
    finally:write()
if __name__=='__main__':main()
