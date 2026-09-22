"""Exercise the actual vkso handoff/cleanup functions with the full manager."""
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import time
import registration_completion_guest as G


def function(source,name):
    start=source.index(name+'() {')
    return source[start:source.index('\n}',start)+2]


def validate(path,plan,refs,baseline,command):
    out=G.OUT
    source=(G.ROOT/'vkso').read_text()
    script=out/'wrapper-functions.sh'
    code='\n'.join(function(source,n) for n in ('as_root','setup_event','hold_state_owned','cleanup_session','exec_with_replacement'))
    script.write_text('''#!/bin/bash
set -Eeuo pipefail
HOLD_ACTIVE=0
HOLD_WRAPPER_PID=""
HOLD_PID_FILE=""
HOLD_STATE_FILE=""
HOLD_NOTIFY_DIR=""
HOLD_NOTIFY_PATH=""
HOLD_NOTIFY_FD=""
HOLD_SESSION_PID=""
HOLD_SESSION_ID=""
HOLD_NOTIFY_DONE=0
PAGE_MODULE_LOADED_BY_US=0
CURRENT_SCRATCH=""
MANAGER_BIN=/work/manager
WORK_DIR=/work/validation
LIB_DIR=/work/validation
METADATA_DIR="$3"
mkdir -p "$METADATA_DIR"
library_arg="$1"
map_arg="$2"
shift 3
EXEC_CMD=("$@")
require_build_outputs() { :; }
compile_manager() { :; }
ensure_page_module() { :; }
metadata_value() { if [[ "$1" == library ]]; then echo "$library_arg"; else echo "$map_arg"; fi; }
require_cmd() { command -v "$1" >/dev/null; }
log() { echo "$*"; }
die() { echo "$*" >&2; exit 1; }
'''+code+'\ntrap \'cleanup_session $?\' EXIT\nexec_with_replacement\n')
    started=out/'wrapper-app-started'; finish=out/'wrapper-app-finish'; rejected=out/'rejected-app-started'
    application=out/'wrapper-application.py'
    application.write_text('''import sys,time
from pathlib import Path
path,started,finish=map(Path,sys.argv[1:])
assert path.read_bytes()[4096:] != b'Z'*4096
started.write_text('ready')
deadline=time.monotonic()+60
while not finish.exists():
 assert time.monotonic()<deadline
 time.sleep(.01)
''')
    with (out/'wrapper-first.log').open('w') as log:
        first=subprocess.Popen(['bash',str(script),str(path),str(plan),str(out/'wrapper-first'),
                                'python3',str(application),str(path),str(started),str(finish)],stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+20
            while not started.exists():
                assert first.poll() is None and time.monotonic()<deadline
                time.sleep(.01)
            state=G.ROOT/'runtime/manager.state'; saved=state.read_bytes()
            assert b'notify_fifo=' in saved
            manager_pid=int(next(x.split('=',1)[1] for x in saved.decode().splitlines() if x.startswith('process_pid=')))
            wrong=['bash',script,path,plan,out/'wrapper-competing','python3','-c',f"from pathlib import Path;Path({str(rejected)!r}).touch()"]
            assert command(wrong,'wrapper-competing',None)!=0
            assert state.read_bytes()==saved and not rejected.exists()
            os.kill(manager_pid,0)
            (out/'active-wrapper.state').write_bytes(saved)
            before=G.observe(path,4096)
            def ordinary_owner(): os.setgroups([]);os.setgid(65534);os.setuid(65534)
            operations=subprocess.run(['python3',str(G.ROOT/'registration_file_ops_guest.py'),str(path)],
                text=True,capture_output=True,preexec_fn=ordinary_owner,timeout=20)
            (out/'file-operations.stdout').write_text(operations.stdout)
            (out/'file-operations.stderr').write_text(operations.stderr)
            assert operations.returncode==0,operations.stderr
            after=G.observe(path,4096)
            assert before==after and not before['original']
            (out/'file-operations-pfn.json').write_text(json.dumps({'before':before,'after':after},indent=2)+'\n')
            finish.touch()
            assert first.wait(timeout=20)==0
        finally:
            if first.poll() is None: first.kill();first.wait()
    assert G.observe(path,4096)['original'] and refs()==baseline
    assert not (G.ROOT/'runtime/manager.state').exists()
    regular=out/'not-a-notification-fifo'; regular.write_text('retain these bytes')
    assert command([G.MANAGER,'replace',path,plan,'--hold','--notify-fifo',regular], 'reject-regular-notify',None)!=0
    assert regular.read_text()=='retain these bytes' and refs()==baseline
    # Kill the actual shell after START, before READY. Its inherited read end
    # must not keep the FIFO alive in the manager; failed READY triggers release.
    with (out/'wrapper-interrupted.log').open('w') as log:
        interrupted=subprocess.Popen(['bash',str(script),str(path),str(plan),str(out/'wrapper-interrupted'),
            'python3','-c',f"from pathlib import Path;Path({str(rejected)!r}).touch()"],
            stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,VKSO_TEST_STOP_AT='state-persisted'))
        manager_pid=None
        try:
            deadline=time.monotonic()+10
            while True:
                assert interrupted.poll() is None and time.monotonic()<deadline
                state=G.ROOT/'runtime/manager.state'
                if state.exists():
                    fields=dict(x.split('=',1) for x in state.read_text().splitlines())
                    if 'process_pid' in fields:
                        manager_pid=int(fields['process_pid'])
                        status=Path(f'/proc/{manager_pid}/status').read_text()
                        if any(x.startswith('State:') and 'T' in x for x in status.splitlines()): break
                time.sleep(.01)
            (out/'interrupted-wrapper.state').write_bytes(state.read_bytes())
            interrupted.kill();interrupted.wait()
            os.kill(manager_pid,signal.SIGCONT)
            while state.exists():
                assert time.monotonic()<deadline
                time.sleep(.01)
            assert not rejected.exists() and G.observe(path,4096)['original'] and refs()==baseline
        finally:
            if interrupted.poll() is None: interrupted.kill();interrupted.wait()
            if manager_pid and (G.ROOT/'runtime/manager.state').exists():
                os.kill(manager_pid,signal.SIGCONT);os.kill(manager_pid,signal.SIGTERM)
    # A dead manager's recovery record must also survive a rejected new vkso.
    with (out/'wrapper-stale-owner.log').open('w') as log:
        owner=subprocess.Popen([str(G.MANAGER),'replace',str(path),str(plan),'--hold'],stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+10
            while not (G.ROOT/'runtime/manager.pid').exists():
                assert owner.poll() is None and time.monotonic()<deadline
                time.sleep(.01)
            saved=(G.ROOT/'runtime/manager.state').read_bytes();owner.kill();owner.wait()
            assert command(['bash',script,path,plan,out/'wrapper-stale','true'],'wrapper-stale',None)!=0
            assert (G.ROOT/'runtime/manager.state').read_bytes()==saved
            (out/'stale-wrapper.state').write_bytes(saved)
            command([G.MANAGER,'restore',path,plan],'wrapper-stale-recovery')
        finally:
            if owner.poll() is None: owner.kill();owner.wait()
    assert G.observe(path,4096)['original'] and refs()==baseline
    sudo_record=None
    if shutil.which('sudo'):
        directory=out/'ordinary-launcher';directory.mkdir();os.chown(directory,65534,65534)
        observed=directory/'application.json'
        program='''import json,os,sys
from pathlib import Path
carrier,output=map(Path,sys.argv[1:])
assert carrier.read_bytes()[4096:] != b'Z'*4096
state=dict(x.split('=',1) for x in Path('/work/runtime/manager.state').read_text().splitlines())
status=Path('/proc/'+state['process_pid']+'/status').read_text()
assert any(x.startswith('Uid:') and x.split()[1:] == ['0']*4 for x in status.splitlines())
assert os.geteuid()==65534
output.write_text(json.dumps({'application_uid':os.geteuid(),'manager_uid':0,'transaction_id':state['transaction_id']}))
'''
        def ordinary_user():os.setgroups([]);os.setgid(65534);os.setuid(65534)
        with (out/'ordinary-launcher.log').open('w') as stream:
            completed=subprocess.run(['bash',str(script),str(path),str(plan),str(directory),
                'python3','-c',program,str(path),str(observed)],stdout=stream,stderr=subprocess.STDOUT,
                preexec_fn=ordinary_user,timeout=30)
        assert completed.returncode==0,(out/'ordinary-launcher.log').read_text()
        sudo_record=json.loads(observed.read_text())
        assert G.observe(path,4096)['original'] and refs()==baseline
        assert not (G.ROOT/'runtime/manager.state').exists()
    return {'status':'pass','sudo_background_path':sudo_record,'active_competitor_preserved':True,'stale_state_preserved':True,'regular_notification_file_preserved':True,'shell_exit_before_ready_restores':True,
            'file_operations':json.loads((out/'file-operations.stdout').read_text()),
            'scope':'actual vkso handoff/cleanup functions with prebuilt fixture; full build path checked separately'}
