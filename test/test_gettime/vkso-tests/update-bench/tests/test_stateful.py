#!/usr/bin/env python3
"""No target kernels, module loads, sudo, or performance measurement."""
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import stateful as s

WRITER='# tsc_pair_min=8 seen=3 dropped=0\nsample,cycles,action,cpu\n0,30,0,0\n1,40,0,1\n2,99,1,0\n'
class StatefulTests(unittest.TestCase):
    def test_balanced_boots(self):
        p=s.full_plan(4)
        self.assertEqual(len(p),32)
        for b in range(4):
            entries=p[8*b:8*b+8]
            self.assertEqual({(x['mode'],x['case']) for x in entries},
                             {(mode,case) for mode in ('read','update')
                              for case in ('raw-normal','vkso-normal','raw-no-retpoline','vkso-no-retpoline')})
            self.assertTrue(all(entries[i]['case']==entries[i+1]['case'] and
                                entries[i]['mode']=='read' and entries[i+1]['mode']=='update'
                                for i in range(0,8,2)))

    def test_raw_writer_ticks_not_corrected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'w';p.write_text(WRITER);r=s.writer_rows(p)
            self.assertEqual(r['median_ticks'],35);self.assertEqual(r['other_actions'],1)
            self.assertEqual(r['cpu_counts'],{'0':2,'1':1})

    def test_writer_bad_samples(self):
        for contents in (WRITER.replace('dropped=0','dropped=1'),WRITER.replace('1,40','0,40'),WRITER.replace('0,30','0,-1'),''):
            with self.subTest(contents=contents), tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'w';p.write_text(contents)
                with self.assertRaises(ValueError):s.writer_rows(p)

    def test_reader_migration_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'r';p.write_text('batch,calls,tsc_ticks,aux_start,aux_end\n0,100,5000,2,3\n')
            with self.assertRaises(ValueError):s.reader_rows(p,100)

    def test_reader_between_batch_migration_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'r';p.write_text('batch,calls,tsc_ticks,aux_start,aux_end\n0,100,5000,2,2\n1,100,5000,3,3\n')
            with self.assertRaises(ValueError):s.reader_rows(p,100)

    def test_snapshot_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); revision=s.tools_snapshot(root);d=root/revision
            s.verify_sums(d);(d/'update-bench/stateful.py').write_text('changed')
            with self.assertRaises(ValueError):s.verify_sums(d)

    def cleanup_case(self, fail_restore):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'result'; calls=[]
            (root/'SHA256SUMS').write_text('mock')
            (root/'direct').mkdir();(root/'direct/SHA256SUMS').write_text('mock')
            def run(argv,destination,env,**kw):
                calls.append([str(x) for x in argv]);Path(destination).write_text('mock\n')
                if 'replace' in argv:raise RuntimeError('partial replace failure')
                if fail_restore and 'restore' in argv:raise RuntimeError('restore failed')
            real_is_file=Path.is_file
            def is_file(p):return True if str(p).endswith('timekeeping_update_bench/control') else real_is_file(p)
            with patch.object(s,'preflight',return_value={}),patch.object(s,'tune',return_value=nullcontext()), \
                 patch.object(s,'logged',side_effect=run),patch.object(s.os,'sched_setaffinity'), \
                 patch.object(Path,'is_file',is_file),patch.object(Path,'is_char_device',return_value=True), \
                 patch.object(s,'kv_file',return_value={'enabled':'0'}):
                with self.assertRaises(ValueError):s.collect(root,'vkso-normal',{},out,1,'tools/1')
            r=json.loads((out/'run.json').read_text());self.assertEqual(r['status'],'FAIL')
            self.assertTrue(any('restore' in x for x in calls))
            self.assertEqual(['rmmod','page_cache_replace'] in calls,not fail_restore)
            s.verify_sums(out)
    def test_partial_replace_restored(self):self.cleanup_case(False)
    def test_restore_failure_keeps_module(self):self.cleanup_case(True)

    def fixture(self,root):
        c={'BLOCKS':1,'REPEATS':1,'UPDATE_SECONDS':1,'READER_ITERATIONS':10000}
        (root/'direct').mkdir(exist_ok=True)
        (root/'SHA256SUMS').write_text('package\n')
        (root/'direct/SHA256SUMS').write_text('direct\n')
        package_hash=s.sha256(root/'SHA256SUMS')
        direct_hash=s.sha256(root/'direct/SHA256SUMS')
        m={'plan':s.full_plan(1),'config':c,
           'packages':{mode:{v:{'sha256':package_hash,'direct_sha256':direct_hash,'path':str(root)}
                             for v in ('normal','no-retpoline')}
                       for mode in ('read','update')}}
        (root/'direct/build.json').write_text('{}')
        revision=s.tools_snapshot(root)
        for n,e in enumerate(m['plan']):
            d=root/'block-01'/e['mode']/e['case'];d.mkdir(parents=True)
            r=dict(protocol=s.PROTOCOL,case=e['case'],block=1,config=c,scope='all',boot_id=str(n),package_sha256=package_hash,bundle_sha256=direct_hash,tool_revision=revision,status='COMPLETE',cleanup_errors=[],environment_cleanup='PASS',package_checksums_sha256=package_hash,bundle_build_sha256=s.sha256(root/'direct/build.json'))
            (d/'run.json').write_text(json.dumps(r));(d/'start.json').write_text('{}')
            if e['mode']=='read':
                s.seal(d)
                continue
            (d/'abi.log').write_text('abi_matrix_status=pass');(d/'check.log').write_text('public_api_check=PASS scope=full');(d/'check-fast.log').write_text('time_syscall_denial_check=PASS')
            (d/'sharing.log').write_text('{}')
            for scenario in s.SCENARIOS:
                directory=d/scenario;directory.mkdir()
                (directory/'round-00.csv').write_text(WRITER)
                interval={'writer_start_ns':0,'writer_end_ns':1000000000}
                if scenario!='idle':
                    interval.update(load_batch_before_start=1,load_batch_after_stop=2)
                    (directory/'round-00-reader.csv').write_text('batch,calls,tsc_ticks,aux_start,aux_end\n0,10000,500000,2,2\n1,10000,500000,2,2\n')
                (directory/'round-00.json').write_text(json.dumps(interval))
            s.seal(d)
        return m

    def test_aggregate_boot_unit(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(s,'validate_sharing'), \
             patch.object(s,'summarize_read',return_value={}),patch.object(s,'summarize_kernel',return_value={}):
            root=Path(tmp);m=self.fixture(root);r=s.aggregate(root,m)
            self.assertEqual(len(r['stateful']['boot_summaries']),16)
            self.assertEqual(r['stateful']['comparisons'][0]['delta_ticks'],0)

    def test_aggregate_missing_tampered_mixed_boot(self):
        for kind in ('missing','tampered','duplicate-boot','mixed-package','incomplete'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp, \
                 patch.object(s,'validate_sharing'),patch.object(s,'summarize_read',return_value={}), \
                 patch.object(s,'summarize_kernel',return_value={}):
                root=Path(tmp);m=self.fixture(root);d=root/'block-01/update/vkso-normal'
                if kind=='missing':(d/'idle/round-00.csv').unlink()
                elif kind=='tampered':(d/'idle/round-00.csv').write_text('corrupt')
                else:
                    p=d/'run.json';r=json.loads(p.read_text())
                    if kind=='duplicate-boot':r['boot_id']='0'
                    if kind=='mixed-package':r['package_sha256']='other'
                    if kind=='incomplete':r['status']='FAIL'
                    p.write_text(json.dumps(r));s.seal(d)
                with self.assertRaises(ValueError):s.aggregate(root,m)

    def test_failed_reader_never_starts_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rec=root/'rec';rec.mkdir();(rec/'control').write_text('stop\n')
            with self.assertRaises(ValueError):s.window(rec,.01,root/'round.csv',['/bin/false'])
            self.assertEqual((rec/'control').read_text(),'stop\n')

class BuildTests(unittest.TestCase):
    def test_update_selective_plans_do_not_build(self):
        import rebuild
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);package=root/'parent';package.mkdir()
            for variant in ('normal','no-retpoline'):
                (package/'boot-manifest.txt').write_text('build_variant='+variant+'\ncc_version=11.4.0\n')
                for backend in ('raw','vkso','bench'):
                    target=backend+'-'+variant
                    with patch.object(s,'check',return_value={}), \
                         patch.object(rebuild.subprocess,'check_output',return_value='11.4.0'), \
                         patch.object(rebuild,'run') as run, \
                         patch.object(sys,'argv',['rebuild',target,'--scope','update','--package',str(package),'--out',str(root/target),'--plan']):
                        rebuild.main();run.assert_not_called()
                    self.assertFalse((root/target).exists())

class ControlTests(unittest.TestCase):
    def test_full_campaign_begin_freezes_eight_image_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bare=root/'baremetal';bare.mkdir()
            (bare/'.clocktime-full.lock').touch()
            environment={'RESULTS_DIR':str(bare/'results'),
                         'STATE_FILE':str(bare/'.clocktime-full-state.json')}
            with patch.dict(os.environ,environment),patch.object(s,'BARE',bare), \
                 patch.object(s,'config',return_value={'BLOCKS':4}), \
                 patch.object(s,'check_all_packages') as checked, \
                 patch.object(s,'package_identity',return_value={'path':'/mock','sha256':'p','direct_sha256':'d'}):
                s.campaign('begin','fixture')
                state=json.loads((bare/'.clocktime-full-state.json').read_text())
                manifest=json.loads((bare/'results/fixture/campaign.json').read_text())
                self.assertEqual(state['next_index'],0)
                self.assertEqual(manifest['plan'],s.full_plan(4))
                self.assertEqual(len(manifest['packages']['read']),2)
                self.assertEqual(len(manifest['packages']['update']),2)
                checked.assert_called_once()
                with self.assertRaisesRegex(ValueError,'campaign already active'):
                    s.campaign('begin','other')

    def test_cancel_waits_for_collector_cleanup(self):
        from unittest.mock import Mock
        process=Mock(pid=1234)
        process.wait.side_effect=[KeyboardInterrupt(),0]
        process.poll.return_value=None
        with patch.object(s.subprocess,'Popen',return_value=process),patch.object(s.os,'killpg') as kill:
            with self.assertRaises(KeyboardInterrupt):s.run_collector(['mock'])
            self.assertEqual(process.wait.call_count,2)
            kill.assert_called_once_with(1234,s.signal.SIGTERM)

    def test_wrong_kernel_rejected_before_config_or_tuning(self):
        with patch.object(s,'check',return_value={}),patch.object(s,'kv_file',return_value={'build_variant':'normal','raw_uts_version':'target'}), \
             patch.object(s.platform,'release',return_value='wrong'),patch.object(s.gzip,'open') as config:
            with self.assertRaisesRegex(ValueError,'wrong kernel'):
                s.preflight(Path('/mock'),'raw-normal',{'CPU':2})
            config.assert_not_called()

    def test_steady_reader_handshake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rec=root/'rec';rec.mkdir();(rec/'control').write_text('stop\n');(rec/'samples').write_text(WRITER)
            reader=root/'mock-reader'
            reader.write_text("""#!/usr/bin/env python3
import mmap,struct,sys,time
with open(sys.argv[1],'r+b') as f: c=mmap.mmap(f.fileno(),4096)
struct.pack_into('Q',c,0,1)
n=0
while not struct.unpack_from('Q',c,8)[0]:
 n+=1;struct.pack_into('Q',c,16,n);time.sleep(.001)
print('batch,calls,tsc_ticks,aux_start,aux_end')
for i in range(n): print(str(i)+',10000,500000,2,2')
""")
            reader.chmod(0o700)
            s.window(rec,.03,root/'round.csv',[str(reader)])
            self.assertEqual((rec/'control').read_text(),'stop\n')
            r=json.loads((root/'round.json').read_text())
            self.assertGreater(r['load_batch_after_stop'],r['load_batch_before_start'])
            s.writer_rows(root/'round.csv');s.reader_rows(root/'round-reader.csv',10000)

    def tuning(self,initial,fail_restore=False):
        values={str(Path('/sys/devices/system/cpu/intel_pstate')/k):v for k,v in initial.items()}
        governor=Path('/sys/devices/system/cpu/cpufreq/policy0/scaling_governor');values[str(governor)]='performance'
        writes=[]; record={}
        def read(p,*a,**kw):return values[str(p)]
        def write(p,v,*a,**kw):
            writes.append((str(p),v.strip()))
            if fail_restore and str(p).endswith('no_turbo') and v.strip()=='0':raise OSError('locked')
            values[str(p)]=v.strip()
        import subprocess
        with patch.object(Path,'read_text',read),patch.object(Path,'write_text',write), \
             patch.object(Path,'glob',return_value=[governor]), \
             patch.object(s.subprocess,'run',return_value=subprocess.CompletedProcess([],3)):
            if fail_restore:
                with self.assertRaises(RuntimeError):
                    with s.tune(record):pass
            else:
                with s.tune(record):pass
        return record,writes,values

    def test_unchanged_tuning_not_written(self):
        r,w,v=self.tuning({'no_turbo':'1','max_perf_pct':'100','min_perf_pct':'100'})
        self.assertEqual(w,[]);self.assertEqual(r['environment_cleanup'],'PASS')

    def test_tuning_restored(self):
        r,w,v=self.tuning({'no_turbo':'0','max_perf_pct':'80','min_perf_pct':'20'})
        self.assertEqual(r['tuning_before'],r['tuning_after']);self.assertEqual(len(w),6)

    def test_tuning_restore_failure_reported(self):
        r,w,v=self.tuning({'no_turbo':'0','max_perf_pct':'100','min_perf_pct':'100'},True)
        self.assertEqual(r['environment_cleanup'],'FAIL')

if __name__=='__main__':unittest.main(verbosity=2)
