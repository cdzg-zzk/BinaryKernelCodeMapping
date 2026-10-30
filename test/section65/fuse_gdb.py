"""Run by GDB's Python interpreter inside the isolated guest."""
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import gdb

sys.path.insert(0,'/work')
from check_fuse import observe_process

out=Path('/work/evidence/debug')
out.mkdir()
result=dict(status='running',scope='hardware breakpoint in shared core serving a FUSE read')
client=None
try:
    gdb.execute('set pagination off')
    gdb.execute('set confirm off')
    gdb.execute('set debuginfod enabled off')
    gdb.execute('set startup-with-shell off')
    gdb.execute('break debug_ready')
    gdb.execute('run')
    entry=int(gdb.parse_and_eval('debug_entry'))
    layout=json.loads(Path('/work/debug-layout.json').read_text())
    textbase=entry-layout['isofs_get_blocks']
    gdb.execute(f'add-symbol-file /work/vkso_iso_core.ko {textbase:#x}')
    for old in layout['source_prefixes']:
        gdb.execute(f'set substitute-path {old} /work/debug-source')
    bp=gdb.Breakpoint(f'*{entry:#x}',type=gdb.BP_HARDWARE_BREAKPOINT)
    bp.condition='inode->i_size == 65537'
    result['hardware_breakpoint']=bp.type==gdb.BP_HARDWARE_BREAKPOINT
    script='''import json,os,time
from pathlib import Path
p=Path('/work/debug-mount');deadline=time.monotonic()+60
while not os.path.ismount(p):
 assert time.monotonic()<deadline,'debug mount timeout'
 time.sleep(.1)
data=(p/'cross-block.bin').read_bytes()
assert len(data)==65537
Path('/work/evidence/debug/client.json').write_text(json.dumps(dict(bytes=len(data),status='pass')))
'''
    client=subprocess.Popen(['python3','-c',script])
    gdb.execute('continue')
    frame=gdb.newest_frame()
    result['function']=frame.name()
    result['inode_size']=int(gdb.parse_and_eval('inode->i_size'))
    result['block']=int(gdb.parse_and_eval('iblock'))
    sal=frame.find_sal()
    result['source']=sal.symtab.filename if sal.symtab else None
    result['line']=sal.line
    result['backtrace']=gdb.execute('bt',to_string=True)
    (out/'backtrace.txt').write_text(result['backtrace'])
    assert result['function']=='isofs_get_blocks',result
    assert 'iso_read_inode_data' in result['backtrace'],result['backtrace']
    assert result['inode_size']==65537 and result['line']>0
    library=next(Path('/work/carrier').glob('lib*.so')).resolve()
    pid=gdb.selected_inferior().pid
    observe_process(pid,library,out/'pfns-before-step.json')
    before=int(gdb.parse_and_eval('$pc'))
    gdb.execute('stepi')
    after=int(gdb.parse_and_eval('$pc'))
    assert before!=after
    result['single_step']={'before':hex(before),'after':hex(after)}
    observe_process(pid,library,out/'pfns-after-step.json')
    bp.delete()
    # Detach resumes the FUSE daemon, allowing the blocked client read to finish.
    gdb.execute('detach')
    assert client.wait(timeout=60)==0
    result['client']=json.loads((out/'client.json').read_text())
    subprocess.run(['umount','/work/debug-mount'],check=True,timeout=30)
    result['status']='pass'
except BaseException:
    result['status']='failed';result['error']=traceback.format_exc()
    raise
finally:
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    if client and client.poll() is None:
        client.terminate();client.wait(timeout=10)
