"""ABI coverage and PFN-record corruption tests; no live mappings are used."""
import copy
import unittest

from audit_support_records import (abi_contract, verify_abi, verify_footprint,
                                   verify_same_boot_sources)


def abi_fixture(backend='raw-vdso', threads=1):
    extras = {
        'semantics.multicpu_threads': f' threads={threads}',
        'security.mapping_permissions': ' code=R-X data=R-- context=R--',
        'path.fallback.single_syscall': ' cases=3',
        'namespace.fast_paths': ' clocks=5',
        'namespace.offsets_frozen': ' errno=EACCES',
    }
    lines = [f'backend={backend}']
    for (key, status), count in abi_contract().items():
        if key != 'abi_matrix_status':
            lines.extend([f'{key}={status}{extras.get(key, "")}'] * count)
    return '\n'.join(lines + ['abi_matrix_status=pass'])


class SupportAuditTests(unittest.TestCase):
    def setUp(self):
        self.plan = [(4096, 0x10000, 'text', '.text1'),
                     (8192, 0x20000, 'text', '.text2'),
                     (16384, 0x30000, 'shared_data', '.shared_data')]
        self.suffix = 'step-001/compact-split/package/libkernel.so'
        self.record = dict(
            method='compact-split',
            pages=[dict(file_offset=offset, kind=kind, section=section,
                        kernel_pfn=kernel, user_pfn=user, shared=shared)
                   for (offset, _, kind, section), kernel, user, shared in
                   zip(self.plan, (11, 22, 33), (201, 202, 33), (False, False, True))],
            carrier_smaps=[f'{start}-{end} {perm} {offset} 00:00 1 /archive/{self.suffix}'
                           for start, end, perm, offset in (
                               ('10000', '11000', 'r-xp', '00001000'),
                               ('11000', '20000', '---p', '00002000'),
                               ('20000', '21000', 'r-xp', '00002000'),
                               ('30000', '31000', 'r--p', '00004000'))],
            distinct_source_pfns=3, distinct_user_pfns=3, source_user_union_pfns=5,
            scope='declared closure pages; smaps adds carrier support, not whole-system net memory')

    def verify(self, record=None):
        return verify_footprint(self.record if record is None else record, self.plan,
                                'compact-split', self.suffix)

    def test_raw_backend_and_actual_thread_scope(self):
        for count in (1, 4):
            result = verify_abi(abi_fixture(threads=count), 'raw')
            self.assertEqual(result['thread_count'], count)
            self.assertEqual(result['multiple_cpus_exercised'], count > 1)
        with self.assertRaises(ValueError):
            verify_abi(abi_fixture(backend='vkso'), 'raw')

    def test_pass_marker_cannot_hide_missing_duplicate_or_failed_case(self):
        text = abi_fixture()
        case = 'semantics.clock_gettime.realtime=pass'
        for replacement in ('', case + '\n' + case, case.replace('pass', 'fail')):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                verify_abi(text.replace(case, replacement), 'raw')
        with self.assertRaises(ValueError):
            verify_abi(text.replace('path.clock_gettime.realtime=fast',
                                    'path.clock_gettime.realtime=fallback'), 'raw')

    def test_distinct_backing_and_overlapping_loader_reservation(self):
        report = self.verify()
        self.assertEqual(report['source_user_union_pfns'], 5)
        self.assertEqual(report['shared_pages'], 1)
        self.assertEqual(report['copied_pages'], 2)

    def test_invalid_page_records_are_rejected(self):
        for field, value in (('shared', True), ('user_pfn', 0), ('user_pfn', 22),
                             ('file_offset', 8192), ('kind', 'shared_data')):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                record = copy.deepcopy(self.record)
                record['pages'][0][field] = value
                self.verify(record)
        record = copy.deepcopy(self.record)
        record['source_user_union_pfns'] = 3
        with self.assertRaises(ValueError):
            self.verify(record)
        record = copy.deepcopy(self.record)
        record['pages'].pop()
        with self.assertRaises(ValueError):
            self.verify(record)

    def test_writable_code_executable_state_and_wrong_carrier_rejected(self):
        for before, after in (('r-xp', 'rwxp'), ('r--p', 'r-xp'),
                              ('step-001', 'step-999')):
            with self.subTest(after=after), self.assertRaises(ValueError):
                record = copy.deepcopy(self.record)
                record['carrier_smaps'] = [line.replace(before, after)
                                           for line in record['carrier_smaps']]
                self.verify(record)

    def test_sources_must_match_between_methods_in_same_boot(self):
        second = copy.deepcopy(self.record)
        verify_same_boot_sources([self.record, second])
        second['pages'][0]['kernel_pfn'] = 99
        with self.assertRaises(ValueError):
            verify_same_boot_sources([self.record, second])


if __name__ == '__main__':
    unittest.main()
