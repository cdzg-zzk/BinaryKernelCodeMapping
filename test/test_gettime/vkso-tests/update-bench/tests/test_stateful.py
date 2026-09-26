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
    def test_order_report_binds_mode_absolute_tsc_and_pt_coverage(self):
        sequence=(('normal-before',False),('swapped-before',True),
                  ('swapped-after',True),('normal-after',False))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,swapped in sequence:
                directory=root/name; directory.mkdir()
                path=directory/'round-00.csv'
                path.write_text(
                    '# tsc_pair_min=30 seen=1000 dropped=0\n'
                    f'# order_swapped={int(swapped)}\n'
                    'sample,cycles,action,cpu,phase_nsec,ktime_carry,realtime_carry,monotonic_carry,leap_pending,clock_mode,shift,start_tsc\n'+
                    ''.join(f'{i},{100 if i%2 else 140},0,0,500000000,0,0,0,0,1,24,{100000+i*10000}\n'
                            for i in range(1000)))
                (directory/'round-00-calibration.csv').write_text(
                    '# cpu=0 unit=TSC_ticks\nsample,ticks\n'+
                    ''.join(f'{i},30\n' for i in range(4096)))
                (directory/'pt-shape.json').write_text(json.dumps(
                    {'groups':{'traced':{'distribution_sufficient':True,
                                          'histogram':{'100':500,'140':500}}}}))
                (directory/'pt-validation.json').write_text(json.dumps(
                    {'validation':'PASS'}))
            report=s.order_shape(root,sequence)
            self.assertEqual(report['interpretation'],'READY_FOR_PT_ORDER_ANALYSIS')
            self.assertEqual(report['groups']['swapped-after']['quarter_high_fraction'],[.5]*4)
            path=root/'normal-before'/'round-00.csv'
            path.write_text(path.read_text().replace('# order_swapped=0','# order_swapped=1'))
            with self.assertRaisesRegex(ValueError,'publisher order mode mismatch'):
                s.order_shape(root,sequence)

    def test_percall_pmu_report_requires_real_per_update_counters(self):
        sequence=(('baseline-before',False),('percall-before',True),
                  ('baseline-middle',False),('percall-after',True),
                  ('baseline-after',False))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,armed in sequence:
                directory=root/name; directory.mkdir()
                path=directory/'round-00.csv'
                header=('sample,cycles,action,cpu,phase_nsec,ktime_carry,'
                        'realtime_carry,monotonic_carry,leap_pending,clock_mode,shift')
                if armed: header+=',rfo_hit,rfo_miss,pmu_valid'
                rows=[]
                for i in range(1000):
                    row=f'{i},{100 if i%2 else 150},0,0,500000000,0,0,0,0,1,24'
                    if armed: row+=',0,'+str(i%2)+',1'
                    rows.append(row)
                path.write_text('# tsc_pair_min=30 seen=1000 dropped=0\n'+
                                f'# percall_pmu_active={int(armed)} rfo_hit_config=0xc224 rfo_miss_config=0x2224\n'+
                                header+'\n'+'\n'.join(rows)+'\n')
                (directory/'round-00-calibration.csv').write_text(
                    '# cpu=0 unit=TSC_ticks\nsample,ticks\n'+
                    ''.join(f'{i},30\n' for i in range(4096)))
            report=s.percall_pmu_shape(root,sequence)
            self.assertEqual(report['groups']['percall-before']['event_groups']
                             ['hit=0,miss=0']['high_fraction'],1)
            self.assertEqual(report['groups']['percall-before']['event_groups']
                             ['hit=0,miss=1']['high_fraction'],0)
            path=root/'percall-before'/'round-00.csv'
            path.write_text(path.read_text().replace(',0,1,1\n',',0,1,0\n',1))
            with self.assertRaisesRegex(ValueError,'missing/invalid per-call PMU'):
                s.percall_pmu_shape(root,sequence)

    def test_cacheprep_report_checks_recorded_modes_and_keeps_distributions(self):
        sequence=(('baseline-before',None),('control-before',1),
                  ('fast-raw',2),('control-after',1),('baseline-after',None))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,mode in sequence:
                directory=root/name; directory.mkdir()
                path=directory/'round-00.csv'
                path.write_text(
                    '# tsc_pair_min=30 seen=1000 dropped=0\n'
                    f'# prep_mode={mode or 0}\n'
                    'sample,cycles,action,cpu,phase_nsec,ktime_carry,realtime_carry,monotonic_carry,leap_pending,clock_mode,shift\n'+
                    ''.join(f'{i},{100 if i%2 else 140},0,0,500000000,0,0,0,0,1,24\n'
                            for i in range(1000)))
                (directory/'round-00-calibration.csv').write_text(
                    '# cpu=0 unit=TSC_ticks\nsample,ticks\n'+
                    ''.join(f'{i},30\n' for i in range(4096)))
            report=s.cacheprep_shape(root,sequence)
            self.assertEqual(report['groups']['fast-raw']['samples'],1000)
            self.assertEqual(report['groups']['control-before']['high_fraction'],.5)
            self.assertEqual(report['modes']['fast-raw'],2)
            path=root/'fast-raw'/'round-00.csv'
            path.write_text(path.read_text().replace('# prep_mode=2','# prep_mode=1'))
            with self.assertRaisesRegex(ValueError,'writer mode mismatch'):
                s.cacheprep_shape(root,sequence)

    def test_prefetch_report_requires_target_and_control_modes(self):
        sequence=(('baseline-before',None),
                  ('read-control-before',5),('read-raw-before',6),
                  ('write-control-before',3),('write-raw-before',4),
                  ('baseline-middle',None),
                  ('write-raw-after',4),('write-control-after',3),
                  ('read-raw-after',6),('read-control-after',5),
                  ('baseline-after',None))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,mode in sequence:
                directory=root/name; directory.mkdir()
                (directory/'round-00.csv').write_text(
                    '# tsc_pair_min=30 seen=1000 dropped=0\n'
                    f'# prep_mode={mode or 0}\n'
                    'sample,cycles,action,cpu,phase_nsec,ktime_carry,realtime_carry,monotonic_carry,leap_pending,clock_mode,shift\n'+
                    ''.join(f'{i},{100 if i%2 else 140},0,0,500000000,0,0,0,0,1,24\n'
                            for i in range(1000)))
                (directory/'round-00-calibration.csv').write_text(
                    '# cpu=0 unit=TSC_ticks\nsample,ticks\n'+
                    ''.join(f'{i},30\n' for i in range(4096)))
            report=s.prefetch_shape(root,sequence)
            self.assertEqual(report['groups']['write-raw-after']['samples'],1000)
            self.assertEqual(report['modes']['read-control-after'],5)
            path=root/'read-raw-after'/'round-00.csv'
            path.write_text(path.read_text().replace('# prep_mode=6','# prep_mode=5'))
            with self.assertRaisesRegex(ValueError,'prefetch writer mode mismatch'):
                s.prefetch_shape(root,sequence)

    def test_cacheline_reader_evidence_keeps_writer_interval_immutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'run'/'static-read'/'round-00.csv'
            dest.parent.mkdir(parents=True)
            interval=dest.with_suffix('.json')
            interval.write_text('{"writer_start_ns":100,"writer_end_ns":1000}\n')
            original=interval.read_bytes()
            tail=''.join(f'PROGRESS monotonic_ns={t} reads={1000*i}\n'
                         for i,t in enumerate((200,400,600),1))+'DONE reads=5000\n'
            result=s.record_cacheline_reader(dest,
                {'symbol':'linux_banner','address':'0x1000','offset':4096},
                'READY {}\n',tail,0)
            self.assertEqual(interval.read_bytes(),original)
            self.assertEqual(result['progress_reports_inside_writer'],3)
            self.assertEqual(json.loads(dest.with_name('round-00-cacheline-reader.json').read_text())['reads'],5000)
            with self.assertRaises(FileExistsError):
                s.record_cacheline_reader(dest,
                    {'symbol':'linux_banner','address':'0x1000','offset':4096},
                    'READY {}\n',tail,0)

    def test_kcore_target_uses_elf_load_mapping_and_rejects_ambiguous_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); symbols=root/'kallsyms'; core=root/'kcore'
            symbols.write_text('0000000000100080 d tk_fast_raw\n')
            elf=bytearray(0x2000)
            elf[:6]=b'\x7fELF\x02\x01'
            s.struct.pack_into('<H',elf,16,4)
            s.struct.pack_into('<Q',elf,32,64)
            s.struct.pack_into('<HH',elf,54,56,1)
            s.struct.pack_into('<IIQQQQQQ',elf,64,1,0,0x1000,0x100000,0,0x1000,0x1000,0)
            elf[0x1080:0x1100]=bytes(range(128))
            core.write_bytes(elf)
            target=s.kcore_target('tk_fast_raw',symbols,core)
            self.assertEqual(target['offset'],0x1080)
            self.assertEqual(target['address'],'0x100080')
            symbols.write_text('0000000000100080 d tk_fast_raw\n0000000000100080 d tk_fast_raw\n')
            with self.assertRaisesRegex(ValueError,'symbol unavailable'):
                s.kcore_target('tk_fast_raw',symbols,core)
            symbols.write_text('0000000000100081 d tk_fast_raw\n')
            with self.assertRaisesRegex(ValueError,'not cacheline aligned'):
                s.kcore_target('tk_fast_raw',symbols,core)

    def test_diagnostic_rows_require_state_and_full_calibration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'round-00.csv'
            path.write_text('# tsc_pair_min=33 seen=1 dropped=0\n'
                'sample,cycles,action,cpu,phase_nsec,ktime_carry,realtime_carry,monotonic_carry,leap_pending,clock_mode,shift\n'
                '0,140,0,0,500000000,1,0,1,0,1,24\n')
            calibration=path.with_name('round-00-calibration.csv')
            calibration.write_text('# cpu=0 unit=TSC_ticks\nsample,ticks\n'+
                ''.join(f'{i},33\n' for i in range(4096)))
            rows,pairs=s.diagnostic_rows(path)
            self.assertEqual(rows[0]['ktime_carry'],'1')
            self.assertEqual(len(pairs),4096)
            path.write_text(path.read_text().replace('500000000','1000000000'))
            with self.assertRaises(ValueError):s.diagnostic_rows(path)
            path.write_text(path.read_text().replace('1000000000','500000000'))
            calibration.write_text(calibration.read_text().replace('# cpu=0','# cpu=2'))
            with self.assertRaises(ValueError):s.diagnostic_rows(path)

    def test_diagnosis_report_keeps_boots_and_state_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); package=root/'package'; package.mkdir()
            (package/'SHA256SUMS').write_text('package\n')
            paths=[]
            for boot in range(2):
                path=root/f'boot{boot}'; path.mkdir(); paths.append(path)
                run=dict(status='COMPLETE',scope='diagnostic',environment_cleanup='PASS',
                         boot_id=str(boot),case='raw-normal',package=str(package),
                         package_sha256=s.sha256(package/'SHA256SUMS'),
                         config={'REPEATS':1})
                (path/'run.json').write_text(json.dumps(run))
                for name in ('start.json','abi.log','check.log','check-fast.log'):
                    (path/name).write_text('ok\n')
                for scenario in s.SCENARIOS:
                    directory=path/scenario; directory.mkdir()
                    rows=['# tsc_pair_min=33 seen=1000 dropped=0',
                          'sample,cycles,action,cpu,phase_nsec,ktime_carry,realtime_carry,monotonic_carry,leap_pending,clock_mode,shift']
                    for i in range(1000):
                        state=i%2
                        rows.append(f'{i},{100 if state==0 else 150},0,0,{i%10*100000000},{state},0,{state},0,1,24')
                    (directory/'round-00.csv').write_text('\n'.join(rows)+'\n')
                    (directory/'round-00-calibration.csv').write_text(
                        '# cpu=0 unit=TSC_ticks\nsample,ticks\n'+
                        ''.join(f'{i},33\n' for i in range(4096)))
                s.seal(path)
            report=s.diagnosis_report(paths)
            self.assertEqual(report['boots'],2)
            self.assertEqual(len(report['boot_scenarios']),8)
            idle=report['boot_scenarios'][0]
            self.assertEqual(idle['high_fraction'],.5)
            self.assertEqual(idle['flag_groups']['ktime_carry']['1']['high_fraction'],1)
            state=s.no_marker_state_report(paths)
            self.assertEqual(state['protocol'],'clocktime-update-no-marker-state-v1')
            self.assertEqual(state['boots'],2)
            self.assertEqual(len(state['boot_scenarios']),4)
            idle=state['boot_scenarios'][0]
            self.assertEqual(idle['carry']['ktime_carry']['fraction_of_all_high'],1)
            self.assertEqual(idle['carry']['ktime_carry']['high_fraction_without'],0)
            self.assertEqual(idle['phase_clock'],'realtime')
            self.assertEqual(idle['phase_bands'][1]['count'],800)
            self.assertEqual(idle['middle_second_transitions']['high_after_high'],0)
            self.assertEqual(idle['middle_second_transitions']['high_after_low'],1)
            with self.assertRaises(ValueError):s.diagnosis_report([paths[0],paths[0]])
            with self.assertRaisesRegex(ValueError,'duplicate diagnostic boot'):
                s.no_marker_state_report([paths[0],paths[0]])

    def test_stage_report_locates_changed_raw_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); package=root/'package'; package.mkdir()
            (package/'SHA256SUMS').write_text('package\n')
            run=root/'run';run.mkdir()
            (run/'run.json').write_text(json.dumps(dict(
                status='COMPLETE',scope='diagnostic',stage_diagnostic=True,
                environment_cleanup='PASS',boot_id='stage-boot',case='raw-normal',
                package=str(package),package_sha256=s.sha256(package/'SHA256SUMS'),
                config={'REPEATS':1})))
            for name in ('start.json','abi.log','check.log','check-fast.log'):
                (run/name).write_text('ok\n')
            columns=','.join(s.STAGE_FIELDS)
            for scenario in s.SCENARIOS:
                directory=run/scenario;directory.mkdir()
                lines=['# tsc_pair_min=33 seen=1000 dropped=0',
                       '# stage_schema=1 invalid_stages=0',
                       'sample,cycles,action,cpu,phase_nsec,ktime_carry,realtime_carry,monotonic_carry,leap_pending,clock_mode,shift,'+columns]
                for i in range(1000):
                    parts=[10,10,60 if i%2 else 10,10,10,10,10,30]
                    lines.append(f'{i},{sum(parts)},0,0,500000000,0,0,0,0,1,24,'+
                                 ','.join(map(str,parts)))
                (directory/'round-00.csv').write_text('\n'.join(lines)+'\n')
                (directory/'round-00-calibration.csv').write_text(
                    '# cpu=0 unit=TSC_ticks\nsample,ticks\n'+
                    ''.join(f'{i},33\n' for i in range(4096)))
            s.seal(run)
            result=s.diagnosis_report([run])
            self.assertEqual(result['protocol'],'clocktime-update-stage-diagnosis-v1')
            idle=result['boot_scenarios'][0]
            self.assertEqual(idle['partition'],'outer-quartiles-of-instrumented-total')
            self.assertEqual(idle['stage_segments']['update_vsyscall']['high_minus_low_ticks'],50)
            self.assertEqual(idle['total_high_minus_low_median_ticks'],50)
            sample=run/'idle/round-00.csv'
            sample.write_text(sample.read_text().replace('0,100,0,0,','0,101,0,0,',1))
            with self.assertRaisesRegex(ValueError,'stage intervals'):
                s.diagnostic_rows(sample,staged=True)

    def test_split_report_validates_boundaries_and_preserves_boots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);package=root/'package';package.mkdir()
            (package/'SHA256SUMS').write_text('package\n')
            paths=[]
            for backend in ('raw','vkso'):
                run=root/backend;run.mkdir();paths.append(run)
                (run/'run.json').write_text(json.dumps(dict(
                    status='COMPLETE',scope='diagnostic',split_diagnostic=True,
                    stage_diagnostic=False,environment_cleanup='PASS',
                    boot_id=backend,case=backend+'-normal',package=str(package),
                    package_sha256=s.sha256(package/'SHA256SUMS'),
                    split_parts=s.SPLIT_PARTS[backend],config={'REPEATS':1})))
                for name in ('start.json','abi.log','check.log','check-fast.log'):
                    (run/name).write_text('ok\n')
                for scenario in s.SPLIT_SCENARIOS:
                    for part in s.SPLIT_PARTS[backend]:
                        directory=run/f'split-{part}'/scenario;directory.mkdir(parents=True)
                        lines=['# tsc_pair_min=33 seen=1000 dropped=0',
                               '# stage_schema=0 invalid_stages=0',
                               f'# split_schema=1 split_part={part} invalid_splits=0',
                               'sample,cycles,action,cpu,phase_nsec,ktime_carry,realtime_carry,monotonic_carry,leap_pending,clock_mode,shift,prefix_ticks,suffix_ticks']
                        for i in range(1000):
                            total=100 if i%2==0 else 140
                            prefix=40 if part==s.SPLIT_PARTS[backend][0] else 50+(total-100)
                            lines.append(f'{i},{total},0,0,500000000,0,0,0,0,1,24,{prefix},{total-prefix}')
                        (directory/'round-00.csv').write_text('\n'.join(lines)+'\n')
                        (directory/'round-00-calibration.csv').write_text(
                            '# cpu=0 unit=TSC_ticks\nsample,ticks\n'+
                            ''.join(f'{i},33\n' for i in range(4096)))
                s.seal(run)
            report=s.diagnosis_report(paths)
            self.assertEqual(report['protocol'],'clocktime-update-split-diagnosis-v1')
            self.assertEqual(report['boots'],2)
            self.assertEqual(len(report['boot_boundaries']),8)
            self.assertEqual(report['boot_boundaries'][0]['boundary'],'before_update_vsyscall')
            self.assertEqual(report['boot_boundaries'][1]['boundary'],'after_update_vsyscall')
            with self.assertRaisesRegex(ValueError,'not a complete no-marker'):
                s.no_marker_state_report(paths)
            sample=paths[0]/'split-1/idle/round-00.csv'
            sample.write_text(sample.read_text().replace('0,100,0,0,','0,101,0,0,',1))
            with self.assertRaisesRegex(ValueError,'split intervals'):
                s.diagnostic_rows(sample,split_part=1)

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
            self.assertFalse((d/'update-bench/compare-update.py').exists())
            self.assertFalse((d/'baremetal/build-all.sh').exists())
            self.assertTrue((d/'direct-api/sharing.py').exists())
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
             patch.object(s,'summarize_read',return_value={}),patch.object(s,'summarize_kernel',return_value={}), \
             patch.object(s,'mapping_footprint',return_value={}),patch.object(s,'static_footprint',return_value={}):
            root=Path(tmp);m=self.fixture(root);r=s.aggregate(root,m)
            self.assertEqual(len(r['stateful']['boot_summaries']),16)
            self.assertEqual(r['stateful']['comparisons'][0]['delta_ticks'],0)

    def test_aggregate_missing_tampered_mixed_boot(self):
        for kind in ('missing','tampered','duplicate-boot','mixed-package','incomplete'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as tmp, \
                 patch.object(s,'validate_sharing'),patch.object(s,'summarize_read',return_value={}), \
                 patch.object(s,'summarize_kernel',return_value={}), \
                 patch.object(s,'mapping_footprint',return_value={}),patch.object(s,'static_footprint',return_value={}):
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
    def test_verify_reports_unfinished_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'finish the build before verify/install'):
                s.check(Path(tmp)/'unfinished')

    def test_diagnostic_config_tolerates_only_new_optional_kconfig_lines(self):
        import rebuild
        parent='CONFIG_PERF_EVENTS=y\nCONFIG_TIMEKEEPING_UPDATE_BENCH=y\n'
        result=parent+('# CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG is not set\n'
                       'CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG=y\n')
        self.assertEqual(rebuild.ordinary_config_symbols(parent),
                         rebuild.ordinary_config_symbols(result))
        self.assertNotEqual(rebuild.ordinary_config_symbols(parent),
                            rebuild.ordinary_config_symbols(result+'CONFIG_OTHER=y\n'))

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

class FootprintTests(unittest.TestCase):
    def record(self,pid,backend):
        def mapping(kind,pfn):
            return dict(kind=kind,permissions='r--p',file_offset=0,
                        virtual_bytes=4096,present_pages=1,
                        unresolved_present_pages=0,pfns=[pfn])
        kinds=([mapping('vdso',10),mapping('vvar',11)] if backend=='raw' else
               [mapping('mm_data',20),mapping('carrier',21),mapping('public',30+pid)])
        return dict(pid=pid,time_namespace='time:[1]',mappings=kinds)

    def test_mapping_census_counts_shared_pfns(self):
        raw=s.census_summarize([self.record(1,'raw'),self.record(2,'raw')],'raw',2)
        vkso=s.census_summarize([self.record(1,'vkso'),self.record(2,'vkso')],'vkso',2)
        self.assertEqual(raw['union_unique_pfns'],2)
        self.assertEqual(vkso['unique_pfns']['mm_data'],1)
        self.assertEqual(vkso['union_unique_pfns'],4)
        bad=self.record(3,'vkso');bad['mappings'][0]['pfns']=[99]
        with self.assertRaisesRegex(ValueError,'MM_data'):
            s.census_summarize([self.record(1,'vkso'),bad],'vkso',2)
        hidden=self.record(1,'raw')
        hidden['mappings'][1].update(pfns=[],unresolved_present_pages=1)
        with self.assertRaisesRegex(ValueError,'PFNs are unavailable'):
            s.census_summarize([hidden],'raw',1)

    def test_section_parser_rejects_missing_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'sections'
            path.write_text('name size addr\n.text 123 0\n.rodata 9 0\nTotal 132\n')
            self.assertEqual(s.section_sizes(path)['.text'],123)
            path.write_text('.rodata 9 0\n')
            with self.assertRaisesRegex(ValueError,'missing .text'):
                s.section_sizes(path)

    def test_static_footprint_keeps_carrier_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            package=Path(tmp)
            (package/'direct').mkdir()
            for name,size in [('raw-vmlinux-sections.txt',1000),
                              ('vkso-vmlinux-sections.txt',1100),
                              ('raw-vdso-sections.txt',90),
                              ('vkso-carrier-sections.txt',80)]:
                (package/name).write_text(f'.text {size} 0\n')
            (package/'direct/libvkso_time.so.sections.txt').write_text('.text 70 0\n')
            (package/'raw-bzImage').write_bytes(b'r'*5)
            (package/'vkso-bzImage').write_bytes(b'v'*6)
            (package/'SHA256SUMS').write_text(''.join(
                s.sha256(p)+'  '+str(p.relative_to(package))+'\n'
                for p in sorted(package.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
            manifest={'packages':{'read':{'normal':{'path':str(package)}}}}
            row=s.static_footprint(manifest)['rows'][0]
            self.assertEqual(row['kernel_text_delta_bytes'],100)
            self.assertEqual(row['vkso_carrier_text_bytes'],80)
            self.assertEqual(row['vkso_public_library_text_bytes'],70)

    def test_mapping_footprint_validates_process_records_and_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);directories=[]
            for block in range(1,4):
                for case in ('raw-normal','vkso-normal','raw-no-retpoline','vkso-no-retpoline'):
                    directory=root/f'block-{block:02d}'/case;directory.mkdir(parents=True)
                    backend=case.split('-')[0]
                    groups=[s.census_summarize([self.record(i+1,backend) for i in range(count)],backend,count)
                            for count in s.CENSUS_COUNTS]
                    (directory/'run.json').write_text(json.dumps({'block':block,'case':case,'boot_id':str(block)+case}))
                    (directory/'resource.json').write_text(json.dumps({'protocol':s.CENSUS_PROTOCOL,
                        'backend':backend,'counts':list(s.CENSUS_COUNTS),'groups':groups,
                        'page_bytes':s.os.sysconf('SC_PAGE_SIZE'),
                        'kernel_release':'5.15.198'}))
                    s.seal(directory);directories.append(directory)
            report=s.mapping_footprint(directories)
            self.assertEqual(len(report['comparisons']),6)
            self.assertEqual(report['comparisons'][0]['boots_per_case'],3)
            target=directories[-1]/'resource.json'
            target.write_text(target.read_text()+' ')
            with self.assertRaises(ValueError):s.mapping_footprint(directories)

class ControlTests(unittest.TestCase):
    def test_pmu_parser_requires_complete_unmultiplexed_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'perf.csv'
            lines=['# started on test','']
            lines += [f'123,,{event},8000000000,100.00,,' for event in s.PMU_EVENTS]
            path.write_text('\n'.join(lines)+'\n')
            result=s.parse_perf_stat(path)
            self.assertEqual(set(result),set(s.PMU_EVENTS))
            self.assertTrue(all(row['count']==123 for row in result.values()))
            path.write_text(path.read_text().replace('100.00','50.00',1))
            with self.assertRaisesRegex(ValueError,'multiplexed'):
                s.parse_perf_stat(path)
            path.write_text('\n'.join(lines[:-1])+'\n')
            with self.assertRaisesRegex(ValueError,'missing or unsupported'):
                s.parse_perf_stat(path)

    def test_valid_pmu_counts_survive_perf_interrupt_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'raw-share'/'round-00.csv'
            dest.parent.mkdir()
            dest.with_suffix('.json').write_text(json.dumps(dict(
                writer_start_ns=10_000_000,writer_end_ns=8_010_000_000)))
            stat=dest.with_name('round-00-pmu.csv')
            stat.write_text('\n'.join(
                f'123,,{event},8020000000,100.00,,' for event in s.PMU_EVENTS)+'\n')
            result=s.record_pmu_window(dest,8,
                dict(enable_ns=1_000_000,disable_ns=8_020_000_000),130)
            self.assertEqual(result['validation'],'PASS')
            self.assertEqual(result['perf_exit_code'],130)
            self.assertTrue(dest.with_name('round-00-pmu.json').is_file())
            stat.write_text(stat.read_text().replace('8020000000','1000000000',1))
            with self.assertRaisesRegex(ValueError,'did not run'):
                s.record_pmu_window(dest,8,
                    dict(enable_ns=1_000_000,disable_ns=8_020_000_000),130)

    def test_pt_recording_accepts_valid_trace_after_nonzero_stop(self):
        header=('name = intel_pt/tsc=1,cyc=1/k\n'
                'contains AUX area data\n'
                'time of first sample : 100.000000\n'
                'time of last sample : 105.000000\n')
        trace=''.join('100.1: ffffffff timekeeping_update ([kernel.kallsyms])\n'
                      for _ in range(6))
        completed=s.subprocess.CompletedProcess
        with patch.object(s.subprocess,'run',side_effect=[
                completed([],0,header,''),completed([],0,trace,'')]):
            result=s.validate_pt_recording(Path('/mock/perf'),
                {'data':'/mock/trace/data','perf_exit_code':1})
        self.assertEqual(result['validation'],'PASS')
        self.assertEqual(result['perf_exit_code'],1)
        self.assertEqual(result['decoded_target_calls_in_100ms'],6)
        with patch.object(s.subprocess,'run',side_effect=[
                completed([],0,header,''),completed([],0,'','')]):
            with self.assertRaisesRegex(ValueError,'cannot decode'):
                s.validate_pt_recording(Path('/mock/perf'),
                    {'data':'/mock/trace/data','perf_exit_code':1})

    def test_business_pt_requires_branch_events_in_target_function(self):
        header=('name = intel_pt/tsc=1,cyc=1/k\n'
                'contains AUX area data\n'
                'time of first sample : 100.000000\n'
                'time of last sample : 110.000000\n')
        trace=''.join(f'100.1: ffffffff update_vsyscall+0x{i:x} ([kernel.kallsyms])\n'
                      for i in range(6))
        completed=s.subprocess.CompletedProcess
        interval={'data':'/mock/trace/data','perf_exit_code':0,
                  'filter':'filter update_vsyscall','requested_seconds':10}
        with patch.object(s.subprocess,'run',side_effect=[
                completed([],0,header,''),completed([],0,trace,'')]) as run:
            result=s.validate_pt_recording(Path('/mock/perf'),interval)
        self.assertEqual(result['target'],'update_vsyscall')
        self.assertEqual(result['itrace'],'b')
        self.assertEqual(result['decoded_target_events_in_100ms'],6)
        self.assertNotIn('decoded_target_calls_in_100ms',result)
        self.assertIn('--itrace=b',run.call_args_list[1].args[0])
        with patch.object(s.subprocess,'run',side_effect=[
                completed([],0,header,''),completed([],0,'','')]):
            with self.assertRaisesRegex(ValueError,'cannot decode update_vsyscall'):
                s.validate_pt_recording(Path('/mock/perf'),interval)

    def test_outer_business_trace_validates_branches_not_nested_call_count(self):
        header=('name = intel_pt/tsc=1,cyc=1/k\n'
                'contains AUX area data\n'
                'time of first sample : 100.000000\n'
                'time of last sample : 110.000000\n')
        trace=''.join(f'100.1: ffffffff timekeeping_advance+0x{i:x} ([kernel.kallsyms])\n'
                      for i in range(6))
        completed=s.subprocess.CompletedProcess
        interval={'data':'/mock/trace/data','perf_exit_code':0,
                  'filter':'filter timekeeping_advance','requested_seconds':10}
        with patch.object(s.subprocess,'run',side_effect=[
                completed([],0,header,''),completed([],0,trace,'')]) as run:
            result=s.validate_pt_recording(Path('/mock/perf'),interval)
        self.assertEqual(result['target'],'timekeeping_advance')
        self.assertEqual(result['itrace'],'b')
        self.assertNotIn('decoded_target_calls_in_100ms',result)
        self.assertIn('--itrace=b',run.call_args_list[1].args[0])
        # Seeing the old inner target does not validate the new outer scope.
        with patch.object(s.subprocess,'run',side_effect=[
                completed([],0,header,''),
                completed([],0,trace.replace('timekeeping_advance','update_vsyscall'),'')]):
            with self.assertRaisesRegex(ValueError,'cannot decode timekeeping_advance'):
                s.validate_pt_recording(Path('/mock/perf'),interval)

    def test_pt_shape_separates_traced_samples_without_boundary_leakage(self):
        with tempfile.TemporaryDirectory() as tmp:
            samples=Path(tmp)/'samples.csv'
            samples.write_text('sample,cycles,action,cpu\n'+''.join(
                f'{i},{84 if i<1000 else 140 if i<2200 else 100},0,0\n'
                for i in range(3000)))
            report=s.pt_shape(samples,dict(traced_sample_start=1000,
                                           traced_sample_end=2200),'vkso')
            groups=report['groups']
            self.assertEqual(groups['before']['samples'],950)
            self.assertEqual(groups['traced']['samples'],1100)
            self.assertEqual(groups['after']['samples'],750)
            self.assertEqual(groups['before']['high_fraction_at_historical_valley'],0)
            self.assertEqual(groups['traced']['high_fraction_at_historical_valley'],1)
            self.assertEqual(groups['after']['high_fraction_at_historical_valley'],0)

    def test_business_shape_uses_only_pt_covered_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            samples=Path(tmp)/'samples.csv'
            rows=['sample,cycles,action,cpu,phase_nsec,ktime_carry']
            for i in range(1200):
                boundary=i%25==0
                rows.append(f'{i},{150 if boundary else 100},0,0,'
                            f'{10000000 if boundary else 500000000},{int(boundary)}')
            samples.write_text('\n'.join(rows)+'\n')
            result=s.business_shape(samples,dict(traced_sample_start=50,
                                                 traced_sample_end=1150))
            self.assertEqual(result['phase']['second_start_0_40ms']['samples'],40)
            self.assertEqual(result['phase']['second_start_0_40ms']
                             ['high_fraction_at_historical_valley'],1)
            self.assertEqual(result['phase']['interior_40_900ms']
                             ['high_fraction_at_historical_valley'],0)

    def test_intel_pt_control_acknowledges_before_collection(self):
        for acknowledgement in (b'ack\n',b'ack\n\x00'):
            with self.subTest(acknowledgement=acknowledgement):
                command_read,command_write=os.pipe()
                ack_read,ack_write=os.pipe()
                try:
                    os.write(ack_write,acknowledgement)
                    with patch.object(s.subprocess,'Popen') as process:
                        process.return_value.poll.return_value=None
                        s.perf_control(command_write,ack_read,process.return_value,'enable')
                    self.assertEqual(os.read(command_read,32),b'enable\n')
                finally:
                    for fd in (command_read,command_write,ack_read,ack_write):os.close(fd)

    def test_package_validation_uses_variant_order_after_json_reload(self):
        # JSON manifests sort keys alphabetically, putting no-retpoline first.
        root=Path('/mock')
        packages={mode:{'no-retpoline':root/(mode+'-no-retpoline'),
                        'normal':root/(mode+'-normal')}
                  for mode in ('read','update')}
        identity={'git_commit':'commit','candidate_patch_sha256':'patch',
                  'vkso_source_tree_sha256':'source'}
        with patch.object(s.subprocess,'run') as run, \
             patch.object(s,'check_read_package',return_value={'source_fingerprint':'same'}), \
             patch.object(s,'compatible',return_value={'source_fingerprint':'same'}), \
             patch.object(s.workflow,'compatible'), \
             patch.object(s,'kv_file',side_effect=lambda path: dict(
                 identity,build_variant=('no-retpoline' if 'no-retpoline' in str(path)
                                         else 'normal'))), \
             patch.object(s,'sha256',return_value='same'):
            s.check_all_packages(packages)
        self.assertEqual([str(x) for x in run.call_args_list[0].args[0][-2:]],
                         ['/mock/read-normal','/mock/read-no-retpoline'])
        self.assertEqual([str(x) for x in run.call_args_list[1].args[0][-2:]],
                         ['/mock/update-normal','/mock/update-no-retpoline'])

    def test_full_campaign_begin_freezes_eight_image_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bare=root/'baremetal';bare.mkdir()
            (bare/'.clocktime-full.lock').touch()
            environment={'RESULTS_DIR':str(bare/'results'),
                         'STATE_FILE':str(bare/'.clocktime-full-state.json')}
            with patch.dict(os.environ,environment),patch.object(s,'BARE',bare), \
                 patch.object(s,'config',return_value={'BLOCKS':4}), \
                 patch.object(s,'check_all_packages') as checked, \
                 patch.object(s,'tools_snapshot',return_value='tools/mock'), \
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

    def test_sudo_collector_keeps_terminal_and_waits_for_cleanup(self):
        from unittest.mock import Mock
        process=Mock(pid=1234)
        process.wait.side_effect=[KeyboardInterrupt(),0]
        process.poll.return_value=None
        with patch.object(s.subprocess,'Popen',return_value=process) as popen, \
             patch.object(s.os,'killpg') as kill:
            with self.assertRaises(KeyboardInterrupt):
                s.run_collector(['sudo','collector'],needs_sudo=True)
            self.assertFalse(popen.call_args.kwargs['start_new_session'])
            process.terminate.assert_called_once_with()
            self.assertEqual(process.wait.call_count,2)
            kill.assert_not_called()

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
