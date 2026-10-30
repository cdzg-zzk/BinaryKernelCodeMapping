#!/usr/bin/env python3
"""Independent ISO format implementation: libarchive's complete image traversal."""
import argparse
import ctypes as C
import hashlib
import json
import locale
from pathlib import Path
import stat

HERE=Path(__file__).resolve().parent
def library():
    a=C.CDLL('libarchive.so.13')
    signatures={
        'archive_read_new':([],C.c_void_p),
        'archive_read_support_format_iso9660':([C.c_void_p],C.c_int),
        'archive_read_set_options':([C.c_void_p,C.c_char_p],C.c_int),
        'archive_read_open_filename':([C.c_void_p,C.c_char_p,C.c_size_t],C.c_int),
        'archive_read_next_header':([C.c_void_p,C.POINTER(C.c_void_p)],C.c_int),
        'archive_read_data':([C.c_void_p,C.c_void_p,C.c_size_t],C.c_ssize_t),
        'archive_read_free':([C.c_void_p],C.c_int),
        'archive_error_string':([C.c_void_p],C.c_char_p),
        'archive_version_string':([],C.c_char_p),
    }
    for name in ('pathname_utf8','pathname','symlink_utf8','symlink','hardlink'):
        signatures['archive_entry_'+name]=([C.c_void_p],C.c_char_p)
    for name in ('size','uid','gid','mtime','mtime_nsec'):
        signatures['archive_entry_'+name]=([C.c_void_p],C.c_int64)
    for name in ('mode','nlink'):
        signatures['archive_entry_'+name]=([C.c_void_p],C.c_uint32)
    for name,(args,result) in signatures.items():
        f=getattr(a,name); f.argtypes=args; f.restype=result
    return a
def manifest(a,image,norock):
    reader=a.archive_read_new(); rows=[]; warnings=[]
    def ok(r):
        if r < -20: raise RuntimeError(a.archive_error_string(reader))
        if r < 0: warnings.append(a.archive_error_string(reader).decode())
    try:
        ok(a.archive_read_support_format_iso9660(reader))
        if norock: ok(a.archive_read_set_options(reader,b'iso9660:!rockridge'))
        ok(a.archive_read_open_filename(reader,str(image).encode(),65536))
        entry=C.c_void_p(); buf=C.create_string_buffer(65537)
        while True:
            status=a.archive_read_next_header(reader,C.byref(entry))
            if status==1: break
            ok(status)
            rawpath=a.archive_entry_pathname_utf8(entry) or a.archive_entry_pathname(entry)
            if rawpath is None:
                warnings.append('Header has no pathname; cannot compare this entry')
                continue
            path=rawpath.decode()
            if path in ('.','/'): continue
            path=path.removeprefix('./').rstrip('/')
            row=dict(path=path)
            for name in ('size','mode','uid','gid','nlink'): row[name]=getattr(a,'archive_entry_'+name)(entry)
            row['mtime_ns']=a.archive_entry_mtime(entry)*10**9+a.archive_entry_mtime_nsec(entry)
            if stat.S_ISREG(row['mode']):
                h=hashlib.sha256(); size=0
                while True:
                    n=a.archive_read_data(reader,buf,len(buf))
                    if n < 0: raise RuntimeError(a.archive_error_string(reader))
                    if not n: break
                    h.update(buf.raw[:n]); size+=n
                row['sha256']=h.hexdigest(); row['actual_bytes']=size
                link=a.archive_entry_hardlink(entry)
                if link: row['hardlink']=link.decode()
            elif stat.S_ISLNK(row['mode']):
                row['target']=(a.archive_entry_symlink_utf8(entry) or a.archive_entry_symlink(entry)).decode()
            rows.append(row)
    finally: a.archive_read_free(reader)
    return rows,warnings
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=False)
    locale.setlocale(locale.LC_ALL,'C.UTF-8'); a=library()
    results=dict(version=a.archive_version_string().decode(),cases=[])
    for c in json.loads((args.reference/'result.json').read_text())['cases']:
        rows,warnings=manifest(a,HERE/'build/images'/c['image'],c['mode']=='norock')
        (args.output/c['manifest']).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        expected={r['path']:r for r in json.loads((args.reference/c['manifest']).read_text())}
        actual={r['path']:r for r in rows}; differences=[]; metadata=[]
        for path in sorted(actual.keys()|expected.keys()):
            x,y=expected.get(path),actual.get(path)
            if x is None or y is None:
                differences.append(dict(path=path,kernel=x,libarchive=y)); continue
            # Directory byte size and default mode/link counts differ between implementations.
            fields=['sha256','target']
            if stat.S_ISREG(x['mode']): fields+=['size']
            diff={k:[x.get(k),y.get(k)] for k in fields if x.get(k)!=y.get(k)}
            if stat.S_IFMT(x['mode'])!=stat.S_IFMT(y['mode']): diff['type']=[x['mode'],y['mode']]
            if diff: differences.append(dict(path=path,fields=diff))
            meta={k:[x[k],y[k]] for k in ('mode','size','uid','gid','nlink','mtime_ns') if x[k]!=y[k]}
            if meta: metadata.append(dict(path=path,fields=meta))
        results['cases'].append(dict(**c,entries_libarchive=len(rows),content_differences=differences,
                                    metadata_differences=metadata,warnings=warnings))
        print(c['image'],c['mode'],len(rows),'content differences',len(differences))
    results['status']='pass' if not any(c['content_differences'] for c in results['cases']) else 'differences'
    (args.output/'result.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__': main()
