#!/usr/bin/env python3
"""Separate demonstrated ISO reuse, preparation cost and unmeasured claims."""
import json
from pathlib import Path
import re
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUNS = ROOT / 'test/evaluation-local/runs/iso9660'
BUILD = HERE / 'build/native/modules/adapted'


def read(path):
    return json.loads(path.read_text())


def main():
    proof = RUNS / 'native-kernel-guest-01'
    run = read(proof / 'run.json')
    assert run['status'] == 'complete'
    evidence = proof / 'evidence'
    correctness = read(evidence / 'correctness.json')
    assert correctness['status'] == 'pass' and len(correctness['cases']) == 35
    shared = read(evidence / 'pfns-vkso-fuse.json')['pages']
    copied = read(evidence / 'pfns-copied-fuse.json')['pages']
    assert all(p['shared'] for p in shared) and all(not p['shared'] for p in copied)
    assert len(shared) == len({p['kernel_pfn'] for p in shared}) == len(copied)
    modules = {line.split()[0]: int(line.split()[1]) for line in
               (evidence / 'modules-loaded.txt').read_text().splitlines()}
    manager_rss = int(re.search(r'^Rss:\s+(\d+) kB',
                      (evidence / 'manager-smaps.txt').read_text(), re.M)[1]) * 1024
    old = read(RUNS / 'costs-01.json')
    adaptation = read(BUILD / 'adaptation.json')
    assert adaptation['functions'] == old['adaptation']['functions']
    assert (BUILD / 'shared_core.c').read_bytes() == (HERE / 'build/adapted/shared_core.c').read_bytes()
    line_count = lambda p: len(p.read_text().splitlines())
    source_lines = {name: line_count(BUILD / name) for name in
                    ('kernel_support.c', 'core_metadata.c', 'support_types.h', 'support_remap.h', 'user_bindings.c')}
    for name in ('user_bridge.c', 'fuse_frontend.c', 'adapt.py', 'build_user.py'):
        source_lines[name] = line_count(HERE / name)
    maintenance = []
    for name in ('maintenance-fuse-before-01', 'maintenance-fuse-after-01'):
        row = read(RUNS / name / 'result.json')
        assert row['status'] == 'pass'
        maintenance.append({k: row[k] for k in ('fixed', 'name_bytes', 'full_name_lookup', 'payload_bytes')})
    native = []
    for path in RUNS.glob('native-*'):
        result = path / 'result.json'
        if result.exists():
            row = read(result)
            if row.get('scope') == 'native performance':
                native.append(dict(path=str(path.relative_to(ROOT)), status=row['status']))
    repair = RUNS / 'maintenance-oneshot-01'
    repair_status = read(repair / 'run.json')
    assert repair_status['status'] == 'complete'
    lifecycle = read(repair / 'evidence/registration-lifecycle.json')
    assert lifecycle['registration_process_exited'] and not lifecycle['live_manager_pids']
    repair_cases = {}
    for label, name, fixed in [
        ('original_kernel', 'maintenance-kernel-original.json', False),
        ('fixed_kernel', 'maintenance-kernel-fixed.json', True),
        ('original_copy', 'maintenance-before/result.json', False),
        ('fixed_copy', 'maintenance-fixed-copy/result.json', True),
        ('fixed_vkso', 'maintenance-fixed-vkso/result.json', True),
    ]:
        row = read(repair / 'evidence' / name)
        assert row['status'] == 'pass' and row['fixed'] == fixed
        assert row['name_bytes'] == ([300] if fixed else [44])
        assert row['full_name_lookup'] == fixed
        repair_cases[label] = {k: row[k] for k in ('fixed', 'name_bytes', 'full_name_lookup', 'payload_bytes')}
    analysis_path = HERE / 'native-analysis.json'
    analysis = read(analysis_path)
    assert analysis['status'] == 'audited'
    lkl_path = HERE / 'lkl-analysis.json'
    lkl_analysis = read(lkl_path)
    assert lkl_analysis['status'] == 'audited'
    cached_path = HERE / 'lkl-namecache-analysis.json'
    cached = read(cached_path)
    assert cached['status'] == 'audited'
    squash_run = RUNS / 'squash-native-guest-03'
    squash = read(squash_run / 'evidence/result.json')
    squash_build = read(HERE / 'build/squashfs/reader-adapted/adaptation.json')
    assert read(squash_run / 'run.json')['status'] == 'complete'
    assert squash['status'] == 'complete' and squash['modules_unloaded']
    squash_export = RUNS / 'squash-export-04'
    squash_lifecycle = read(squash_export / 'evidence/result.json')
    assert read(squash_export / 'run.json')['status'] == 'complete'
    assert (squash_lifecycle['status'] == 'complete' and squash_lifecycle['restored']
            and squash_lifecycle['modules_unloaded'] and squash_lifecycle['registration_process_exited'])
    squash_paths = {}
    for label in ['shared', 'copied']:
        folder = squash_export / 'evidence' / label
        checked = read(folder / 'result.json')
        assert checked['status'] == 'pass' and len(checked['cases']) == 6
        observations = [read(p) for p in sorted(folder.glob('*-pfns.json'))]
        assert len(observations) == 5
        for observation in observations:
            assert observation['status'] == 'pass' and len(observation['pages']) == 6
            assert all(row['shared'] == (label == 'shared') for row in observation['pages'])
        squash_paths[label] = dict(functional_cases=len(checked['cases']),
            boundary_reads=sum(row['random_and_boundary_reads'] for row in checked['cases']),
            pfn_observations=len(observations), pages_per_mapping=len(observations[0]['pages']),
            kernel_shared_bytes=6*4096 if label == 'shared' else 0)
    squash_app_run = RUNS / 'squash-apptainer-shared-02'
    squash_app = read(squash_app_run/'result.json')
    assert squash_app['status'] == 'complete' and squash_app['restored'] and squash_app['modules_unloaded']
    squash_app_pages = read(squash_app_run/'application-pfns.json')
    assert squash_app_pages['status'] == 'pass' and all(r['shared'] for r in squash_app_pages['pages'])
    squash_app_task = read(squash_app_run/'application/result.json')
    assert squash_app_task['status'] == 'pass' and squash_app_task['entries'] == 5866
    squash_native_run = RUNS/'squash-native-cost-01'
    squash_native_cost = read(squash_native_run/'result.json')
    squash_app_analysis=read(HERE/'squashfs-application-analysis.json')
    assert squash_app_analysis['status']=='audited' and len(squash_app_analysis['campaigns'])==2
    squash_samples = [json.loads(line) for line in (squash_native_run/'samples.jsonl').read_text().splitlines()]
    assert squash_native_cost['status'] == 'complete' and squash_native_cost['modules_unloaded']
    assert len(squash_samples) == squash_native_cost['observations'] == 96
    for workload in ['archive', 'scan']:
        assert len({r['digest'] for r in squash_samples if r['workload'] == workload}) == 1
    record = dict(
        generated_unix_seconds=time.time(),
        native_performance_runs=native,
        native_performance_analysis=str(analysis_path.relative_to(ROOT)),
        native_performance_campaigns=[dict(label=r['label'], path=r['path'],
            formal_observations=r['formal_observations']) for r in analysis['campaigns']],
        functional=dict(evidence=str(proof.relative_to(ROOT)), kernel='5.15.198 raw-normal in TCG',
                        cases=35, paths=5, workloads=['GNU find directory index', 'GNU tar archive'],
                        timings_in_this_functional_run_are_native=False),
        preparation=dict(original_core_functions=len(adaptation['functions']),
                         original_function_lines=sum(f['original_lines'] for f in adaptation['functions']),
                         functions_with_body_edits=[f['function'] for f in adaptation['functions'] if f['edited_after_move']],
                         unicode_helper_lines=adaptation['unicode_lines'], explicit_services=adaptation['support_bindings'],
                         current_source_lines=source_lines,
                         accounting='Includes blanks/comments. Counts do not measure developer time. Generated wrappers and first user adapter must not be omitted.'),
        physical_reuse=dict(shared_pages=len(shared), page_bytes=4096, shared_bytes=len(shared)*4096,
                            copied_control_shared_pages=0,
                            scope='kernel-to-user duplication; ordinary DSOs already share pages between user processes'),
        resource_observations=dict(module_bytes=modules,
            original_driver_bytes=modules['iso_original'],
            prepared_driver_bytes=modules['vkso_isofs']+modules['vkso_iso_core'],
            prepared_driver_increment_bytes=modules['vkso_isofs']+modules['vkso_iso_core']-modules['iso_original'],
            registration_module_bytes=modules['page_cache_replace'],
            pfn_reader_is_measurement_only=True,
            hold_manager_observed_rss_bytes=manager_rss,
            hold_manager_is_mandatory=False,
            oneshot_basis='manager.cpp supports replace without --hold and later explicit restore; page_cache_replace.c permits privileged release from a reconnecting process',
            oneshot_functional_run=str(repair.relative_to(ROOT)),
            oneshot_lifecycle=lifecycle,
            net_memory_saving_proven=False,
            interpretation='The 20 KiB duplicated pages alone do not establish net memory savings. Module increments and registration infrastructure must be counted. The observed hold-process RSS is optional lifecycle scaffolding, not an inherent always-resident requirement.'),
        maintenance=dict(upstream_commit='b8253bcf92d6365b20eea6465f5a93c9fc4aa029',
                         copied_fuse_before_after=maintenance,
                         fixed_kernel_and_shared_fuse=repair_cases,
                         evidence=str(repair.relative_to(ROOT)),
                         unchanged_bridge_and_frontend=True,
                         live_replacement_tested=False,
                         scope='long-Joliet compatibility extension, not standard 64-unit names',
                         exclusive_vkso_advantage_proven=False),
        related_work=dict(lkl_runtime_comparison=str(lkl_path.relative_to(ROOT)),
                          lkl_formal_observations=lkl_analysis['observations'],
                          lkl_correctness_cases=lkl_analysis['correctness_cases'],
                          lkl_status='completed initial comparison and paired positive-name-cache ablation',
                          cached_analysis=str(cached_path.relative_to(ROOT)),
                          cached_formal_observations=cached['observations'],
                          cached_correctness_cases=cached['correctness_cases'],
                          ordinary_shared_source_single_fix_advantage='not exclusive to VKSO'),
        squashfs_preparation=dict(evidence=str(squash_run.relative_to(ROOT)),
            native_functional_cases=len(squash['cases']),
            common_functions=len(squash_build['functions']),
            original_function_lines=sum(r['original_lines'] for r in squash_build['functions']),
            services=squash_build['services'], operation_tables=squash_build['operation_tables'],
            native_performance_measured=True,
            native_performance_scope='initial single-boot, single gzip SIF; fresh mounts and warm VFS caches',
            native_performance_evidence=str(squash_native_run.relative_to(ROOT)),
            native_performance_summary=squash_native_cost['summary'], user_adapter_completed=True,
            user_adapter_scope='read-only single-threaded FUSE; user/security xattrs; per-mount caches',
            export_evidence=str(squash_export.relative_to(ROOT)), user_paths=squash_paths,
            adapter_source_lines={name:len((HERE/'squashfs'/name).read_text().splitlines())
                                  for name in ['user_bridge.c','posix_io.c','fuse_frontend.c','apptainer_helper.c']},
            apptainer_execution_completed=True,
            apptainer_evidence=str(squash_app_run.relative_to(ROOT)),
            apptainer_version=squash_app_task['apptainer_version'],
            apptainer_task='GNU tar archives the Linux include tree from a real SIF',
            apptainer_entries=squash_app_task['entries'],
            apptainer_stock_results_identical=True,
            apptainer_shared_bytes=len(squash_app_pages['pages'])*4096),
        squashfs_application_comparison=dict(analysis='test/section65/squashfs-application-analysis.json',
            observations=sum(c['observations'] for c in squash_app_analysis['campaigns']),
            final_campaign=squash_app_analysis['campaigns'][-1]['evidence'],
            scope=squash_app_analysis['scope'], memory_scope=squash_app_analysis['memory_scope'],
            first_use_development_cost_advantage_demonstrated=False),
        next_evidence=['Concrete SquashFS maintenance case; broader native overhead validation'])
    output = HERE / 'reassessment-evidence.json'
    output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(dict(output=str(output), shared_bytes=record['physical_reuse']['shared_bytes'],
                         driver_increment=record['resource_observations']['prepared_driver_increment_bytes'],
                         native_runs=native)))


if __name__ == '__main__':
    main()
