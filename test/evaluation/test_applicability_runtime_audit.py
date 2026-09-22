#!/usr/bin/env python3
"""Mutation checks of the auditor using a real completed guest archive."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from applicability_runtime_audit import audit


class EvidenceAuditTests(unittest.TestCase):
    evidence = None

    @classmethod
    def setUpClass(cls):
        if cls.evidence is None:
            raise unittest.SkipTest('pass --evidence with a completed real guest archive')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='applicability-audit-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / 'validation'
        shutil.copytree(self.evidence, self.directory)

    def change_json(self, path, change):
        target = self.directory / path
        value = json.loads(target.read_text())
        change(value)
        target.write_text(json.dumps(value))

    def change_csv(self, path, change):
        target = self.directory / path
        with target.open(newline='') as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        change(rows)
        with target.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_real_archive_passes(self):
        report = audit(self.directory)
        self.assertEqual(report['status'], 'pass')
        self.assertEqual([r['checks'] for r in report['cases']], [247, 1152])
        self.assertEqual([r['generated_thunk_pages'] for r in report['cases']], [0, 1])

    def test_missing_or_duplicate_input_cannot_pass(self):
        self.change_csv('xxh32/user/xxh32.csv', lambda rows: rows.__setitem__(1, dict(rows[0])))
        with self.assertRaisesRegex(ValueError, 'duplicate/missing/reordered'):
            audit(self.directory)

    def test_agreeing_kernel_and_user_wrong_hash_cannot_pass(self):
        for path in ('kernel/xxh32.csv', 'xxh32/user/xxh32.csv'):
            self.change_csv(path, lambda rows: rows[10].update(expected='0', actual='0'))
        with self.assertRaisesRegex(ValueError, 'expected differs'):
            audit(self.directory)

    def test_sorted_wrong_permutation_cannot_pass(self):
        self.change_csv('sort/user/sort.csv', lambda rows: rows[500].update(actual_hex='00'))
        with self.assertRaisesRegex(ValueError, 'actual_hex differs'):
            audit(self.directory)

    def test_wrong_callback_binding_cannot_pass(self):
        self.change_csv('sort/user/sort.csv', lambda rows: rows[500].update(cmp_address='1'))
        with self.assertRaisesRegex(ValueError, 'comparator binding'):
            audit(self.directory)

    def test_raw_pfn_disagreement_cannot_pass(self):
        self.change_json('sort/registered-pfns.json', lambda obj: obj['pages'][0].update(pagemap_entry='0'))
        with self.assertRaisesRegex(ValueError, 'PFN mismatch'):
            audit(self.directory)

    def test_forged_api_location_cannot_pass(self):
        self.change_json('sort/user/status.json', lambda obj: obj['api_addresses'].update(
            sort=obj['api_addresses']['sort'] + 16))
        with self.assertRaisesRegex(ValueError, 'actual carrier ELF symbol'):
            audit(self.directory)

    def test_missing_user_records_remain_partial(self):
        (self.directory / 'sort/user/status.json').unlink()
        report = audit(self.directory)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['cases'][1]['functional_status'], 'unvalidated')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    EvidenceAuditTests.evidence = args.evidence.resolve()
    unittest.main(argv=[__file__, *remaining])
