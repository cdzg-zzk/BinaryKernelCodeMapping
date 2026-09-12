#!/usr/bin/python3
"""Observe one valid page followed by an unresolved page in a disposable guest."""
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from registration_guest import LIBC, OUT, PAGE, ROOT, mapping, observation


def main():
    OUT.mkdir()
    record = {'scope': 'KVM partial-registration observation; unchanged packaged implementation',
              'kernel': os.uname().release,
              'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
              'complete': False}

    def save():
        (OUT / 'observations.json').write_text(json.dumps(record, indent=2) + '\n')

    def run(args, name):
        with (OUT / (name + '.log')).open('w') as f:
            subprocess.run(list(map(str, args)), stdout=f, stderr=subprocess.STDOUT, check=True)

    for module in ['vkso_m09_clock', 'vkso_kernel_reader', 'page_cache_replace']:
        run(['insmod', ROOT / (module + '.ko')], 'load-' + module)
    owner = Path('/sys/module/vkso_m09_clock')
    source = int((owner / 'sections/.text').read_text().strip(), 16) & ~(PAGE - 1)
    # This canonical vmalloc-range address has no PTE in this guest. It is
    # checked below before submitting the plan; no bytes are read from it.
    missing = 0xffffe7fffffff000
    probe = Path('/sys/kernel/debug/vkso_kernel_reader')
    (probe / 'page_addresses').write_text(f'{hex(source)} {hex(missing)}\n')
    kernel_pages = (probe / 'pages').read_text()
    (OUT / 'source-pages.csv').write_text(kernel_pages)
    pages = {int(row.split(',')[0], 16): int(row.split(',')[1])
             for row in kernel_pages.splitlines()[1:]}
    assert source in pages and missing not in pages
    record.update(source_address=source, source_pfn=pages[source], unresolved_address=missing,
                  unresolved_has_present_pte=False,
                  owner_refcnt_before=int((owner / 'refcnt').read_text()))
    carrier = OUT / 'fixture.bin'
    carrier.write_bytes(b'H' * PAGE + b'Z' * PAGE + b'Q' * PAGE)
    with carrier.open('rb') as f:
        os.fsync(f.fileno())
    plan = OUT / 'page_mappings.txt'
    plan.write_text('# file_offset,kernel_vaddr,kind,section\n'
                    f'0x1000,{hex(source)},text,.fixture_text\n'
                    f'0x2000,{hex(missing)},text,.unresolved_fixture_page\n')
    run([ROOT / 'manager', 'validate', carrier, plan], 'validate')
    save()
    with (OUT / 'manager-hold.log').open('w') as log:
        manager = subprocess.Popen([str(ROOT / 'manager'), 'replace', str(carrier), str(plan), '--hold'],
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 15
            while not (ROOT / 'runtime/manager.pid').is_file():
                if manager.poll() is not None:
                    raise RuntimeError('manager exited before observation of its ready file')
                if time.monotonic() >= deadline:
                    raise RuntimeError('manager ready file timeout')
                time.sleep(.02)
            record['manager_ready_file'] = True
            record['manager_alive_at_ready'] = manager.poll() is None
            record['owner_refcnt_at_ready'] = int((owner / 'refcnt').read_text())
            kernel_log = subprocess.check_output(['dmesg'], text=True)
            (OUT / 'kernel-at-ready.log').write_text(kernel_log)
            error = f'Failed to get LKM code page for kernel_vaddr: {hex(missing)}'
            record['kernel_resolution_error_observed'] = error in kernel_log
            record['kernel_batch_error_minus12_observed'] = 'Failed to process pages: -12' in kernel_log
            assert record['kernel_resolution_error_observed'] and record['kernel_batch_error_minus12_observed']
            first = mapping(carrier)
            second = mapping(carrier, offset=2 * PAGE)
            try:
                record['first_mapping_at_ready'] = observation(first)
                record['second_mapping_at_ready'] = observation(second)
                record['first_binding_remains'] = record['first_mapping_at_ready']['pfn'] == pages[source]
                record['second_original_bytes'] = ctypes.string_at(second, PAGE) == b'Q' * PAGE
                assert record['second_original_bytes']
            finally:
                LIBC.munmap(first, PAGE)
                LIBC.munmap(second, PAGE)
            record['partial_carrier_exposed_at_ready'] = record['first_binding_remains']
            save()
        finally:
            if manager.poll() is None:
                manager.send_signal(signal.SIGTERM)
            record['manager_exit_code'] = manager.wait(timeout=15)
            save()
    for offset, byte in [(PAGE, b'Z'), (2 * PAGE, b'Q')]:
        address = mapping(carrier, offset=offset)
        try:
            item = observation(address)
            item.update(file_offset=offset, original_bytes=ctypes.string_at(address, PAGE) == byte * PAGE)
            record.setdefault('after_restore', []).append(item)
            assert item['original_bytes'] and item['pfn'] != pages[source]
        finally:
            LIBC.munmap(address, PAGE)
    run(['rmmod', 'vkso_m09_clock'], 'normal-owner-unload')
    record['owner_absent_after_ordered_unload'] = not owner.exists()
    assert record['manager_exit_code'] == 0 and record['owner_absent_after_ordered_unload']
    record['complete'] = True
    save()
    # Completion describes the observation, not a passing atomicity contract.
    print('registration_observation=complete', flush=True)


if __name__ == '__main__':
    main()
