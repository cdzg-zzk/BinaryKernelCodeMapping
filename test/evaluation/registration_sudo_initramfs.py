#!/usr/bin/env python3
"""Add the real sudo/PAM binaries to an isolated, network-free test initramfs."""
import argparse,gzip,json,os,re,shutil,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    root=a.output/'root';root.mkdir()
    raw=gzip.decompress(a.base.read_bytes())
    names=subprocess.check_output(['cpio','-it'],input=raw,stderr=subprocess.DEVNULL).decode().splitlines()
    assert all(not n.startswith('/') and '..' not in Path(n).parts for n in names)
    subprocess.run(['cpio','-id','--no-absolute-filenames','--no-preserve-owner'],cwd=root,input=raw,check=True,capture_output=True)
    copied=[]
    def copy(path):
        path=Path(path);target=root/str(path).lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
        if target.is_symlink():target.unlink()
        shutil.copy2(path,target);copied.append(str(path))
    for path in [Path('/usr/bin/sudo'),Path('/lib/x86_64-linux-gnu/security/pam_permit.so'),*Path('/usr/libexec/sudo').glob('*')]:
        if not path.is_file():continue
        copy(path)
        result=subprocess.run(['ldd',path],capture_output=True,text=True)
        for dependency in re.findall(r'(/[^\s()]+)',result.stdout):copy(dependency)
    (root/'usr/bin/sudo').chmod(0o4755)
    for d in ('etc/pam.d','run/sudo','var/lib/sudo'):(root/d).mkdir(parents=True,exist_ok=True)
    (root/'etc/passwd').write_text('root:x:0:0:root:/root:/bin/bash\nnobody:x:65534:65534:guest test:/tmp:/bin/bash\n')
    (root/'etc/group').write_text('root:x:0:\nnogroup:x:65534:\n')
    (root/'etc/sudoers').write_text('Defaults !requiretty\nnobody ALL=(ALL) NOPASSWD: ALL\n')
    (root/'etc/sudoers').chmod(0o440)
    (root/'etc/pam.d/sudo').write_text('auth required pam_permit.so\naccount required pam_permit.so\nsession required pam_permit.so\n')
    entries=b'\0'.join(str(x.relative_to(root)).encode() for x in root.rglob('*'))+b'\0'
    archive=subprocess.check_output(['cpio','--null','-o','--format=newc','--owner=0:0'],cwd=root,input=entries,stderr=subprocess.DEVNULL)
    (a.output/'initramfs.cpio.gz').write_bytes(gzip.compress(archive,compresslevel=1))
    (a.output/'preparation.json').write_text(json.dumps({'scope':'private KVM sudo-path validation only; no host accounts or permissions changed','base':str(a.base),'copied':copied,'test_uid':65534},indent=2)+'\n')
    shutil.copy2(__file__,a.output/Path(__file__).name)
if __name__=='__main__':main()
