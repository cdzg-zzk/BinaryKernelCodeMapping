#!/usr/bin/env python3
"""Freeze mechanism evidence from the completed clean campaign; no target run."""
import argparse
import json
from pathlib import Path
import subprocess

from audit_current import REPO, OUT, csv_text
from audit_binary_current import CAMPAIGN


def collect():
    boot_rows, page_rows, resource_rows = [], [], []
    for block in range(1, 5):
        for variant in ['normal', 'no-retpoline']:
            directory = CAMPAIGN / f'block-{block:02}/read/vkso-{variant}'
            run = json.loads((directory / 'run.json').read_text())
            sharing = json.loads((directory / 'sharing.json').read_text())
            checks = {n: (directory / n).read_text() for n in ['check.log', 'check-fast.log', 'legacy-abi.log']}
            assert 'public_api_check=PASS scope=full' in checks['check.log']
            assert 'time_syscall_denial_check=PASS' in checks['check-fast.log']
            assert 'abi_matrix_status=pass' in checks['legacy-abi.log']
            for word in ['security.mapping_permissions=pass', 'namespace.exec.lifecycle=pass', 'namespace.setns.commit=pass']:
                assert word in checks['legacy-abi.log'], (directory, word)
            assert run['git_commit'] == 'cf9dc817f29f9c8d6f88dde0c58c4ccb75347aeb'
            for p in sharing['pages']:
                assert p['shared'] and p['user_pfn'] == p['kernel_pfn']
                page_rows.append(dict(block=block, variant=variant, kind=p['kind'], section=p['section'],
                                      user_pfn=p['user_pfn'], kernel_pfn=p['kernel_pfn'], result='PASS',
                                      evidence=str((directory / 'sharing.json').relative_to(REPO))))
            boot_rows.append(dict(block=block, variant=variant, boot_id=run['boot_id'],
                                  source_revision=run['git_commit'], public_api='PASS', selected_fast_path_denial='PASS',
                                  abi_namespace_lifecycle='PASS', pfn_identity='PASS',
                                  text_pages=sum(p['kind'] == 'text' for p in sharing['pages']),
                                  data_pages=sum(p['kind'] == 'shared_data' for p in sharing['pages']),
                                  evidence=str(directory.relative_to(REPO))))
    for block in range(1, 5):
        for variant in ['normal', 'no-retpoline']:
            for system in ['raw', 'vkso']:
                path = CAMPAIGN / f'block-{block:02}/read/{system}-{variant}/resource.json'
                d = json.loads(path.read_text())
                for group in d['groups']:
                    kinds = {}
                    for record in group['records']:
                        for mapping in record['mappings']:
                            item = kinds.setdefault(mapping['kind'], dict(pfns=set(), mapped=0, unresolved=0))
                            item['pfns'].update(x for x in mapping['pfns'] if x is not None)
                            item['mapped'] += mapping['present_pages']
                            item['unresolved'] += mapping['unresolved_present_pages']
                    for kind, item in kinds.items():
                        resource_rows.append(dict(block=block, variant=variant, system=system, processes=group['processes'],
                                                  kind=kind, summed_present_mappings=item['mapped'],
                                                  unique_recorded_pfns=len(item['pfns']), unresolved_present_pages=item['unresolved'],
                                                  page_bytes=d['page_bytes'], evidence=str(path.relative_to(REPO))))
    commit = 'aa1855e812107757f57ef68fc537f91c48c8034c'
    patch = subprocess.check_output(['git', 'show', '--format=fuller', commit, '--',
                                     'test/test_gettime/linux-5.15.198-vkso/kernel/time/vkso_time_core.c',
                                     'test/test_gettime/linux-5.15.198-vkso/kernel/time/vkso_time_internal.h',
                                     'test/test_gettime/linux-5.15.198-vkso/kernel/time/vkso_time_test.c'], cwd=REPO, text=True)
    return {'mechanism-boots.csv': csv_text(boot_rows, list(boot_rows[0])),
            'shared-pages.csv': csv_text(page_rows, list(page_rows[0])),
            'resource-pages.csv': csv_text(resource_rows, list(resource_rows[0])),
            'maintenance-aa1855e.patch': patch}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    for name, data in collect().items():
        path = OUT / name
        if args.check:
            assert path.read_text() == data, 'stale evidence: ' + name
        else:
            path.write_text(data)
    print('mechanism_evidence_check=PASS' if args.check else 'mechanism_evidence_written=PASS')


if __name__ == '__main__':
    main()
