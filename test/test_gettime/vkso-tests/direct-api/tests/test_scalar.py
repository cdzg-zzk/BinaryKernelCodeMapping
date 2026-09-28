#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Scalar diagnostics cannot be mistaken for formal READ data."""
import copy
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import scalar
import supplemental
from test_kernel_contract import definition, run, REPO, BASE


def samples():
    text = io.StringIO()
    w = csv.writer(text, lineterminator='\n')
    w.writerow(scalar.COLUMNS)
    for round_index in range(3):
        for api in scalar.APIS:
            w.writerow([api, round_index, 2, 100, 5000 + 100 * round_index, 0])
    return text.getvalue()


class ScalarTests(unittest.TestCase):
    def test_full_matrix_and_mean(self):
        self.assertEqual(scalar.validate(samples(), 2, 100, 3),
                         dict.fromkeys(scalar.APIS, 51.0))

    def test_missing_duplicate_unexpected_and_malformed_rows(self):
        rows = samples().splitlines()
        for text in ['\n'.join(rows[:-1]), samples() + rows[1] + '\n',
                     samples().replace('ktime_get_raw', 'monotonic_raw'),
                     samples().replace('5000,0', '5000'),
                     samples().replace('5000,0', '5000,0,9'),
                     samples().replace('5000,0', '-1,0')]:
            with self.subTest(text=text[:100]), self.assertRaises((ValueError, TypeError)):
                scalar.validate(text, 2, 100, 3)

    def test_cpu_iterations_and_schema_checked(self):
        for text, cpu, iterations in [(samples(), 3, 100), (samples(), 2, 101),
                                      (samples().replace('api,round', 'case,round'), 2, 100)]:
            with self.assertRaises(ValueError):
                scalar.validate(text, cpu, iterations, 3)

    def fixture(self, root, name, boot):
        out = root / name
        out.mkdir()
        record = dict(protocol=scalar.PROTOCOL, status='COMPLETE', label='candidate',
                      case='vkso-normal', cpu=2, iterations=100, rounds=3, warmup=10,
                      module_sha256='module', environment=dict(boot_id=boot,
                      compiler_version='11.4.0', cpu_info={'model name': 'test'},
                      tuning={'test': 'controlled'}, kernel_image_sha256='image'))
        (out / 'scalar.json').write_text(json.dumps(record))
        (out / 'samples.csv').write_text(samples())
        scalar.inventory(out)
        return out

    def test_summary_independent_boots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self.fixture(root, 'a', 'boot-1')
            b = self.fixture(root, 'b', 'boot-2')
            r = scalar.summarize([a, b])['groups']['candidate:vkso-normal']
            self.assertEqual(r['boots'], 2)
            self.assertEqual(r['apis']['ktime_get']['mean'], 51.0)

    def test_same_boot_and_modified_samples_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self.fixture(root, 'a', 'boot-1')
            b = self.fixture(root, 'b', 'boot-1')
            with self.assertRaisesRegex(ValueError, 'same boot'):
                scalar.summarize([a, b])
            (a / 'samples.csv').write_text(samples() + '\n')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                scalar.summarize([a])

    def test_failed_and_mixed_kernel_runs_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = self.fixture(root, 'a', 'boot-1')
            b = self.fixture(root, 'b', 'boot-2')
            r = json.loads((b / 'scalar.json').read_text())
            for key, value in [('status', 'FAIL'), ('module_sha256', 'other')]:
                changed = copy.deepcopy(r)
                changed[key] = value
                (b / 'scalar.json').write_text(json.dumps(changed))
                scalar.inventory(b)
                with self.assertRaises(ValueError):
                    scalar.summarize([a, b])

    def test_tuning_rejects_bad_backend_before_any_operation(self):
        with patch.object(supplemental, 'kv_file') as metadata:
            with self.assertRaisesRegex(ValueError, 'backend'):
                with supplemental.controlled_tuning(Path('/not-used'), 'unknown'):
                    self.fail('tuning was entered')
            metadata.assert_not_called()

    def test_legacy_inner_measurement_loop_unchanged(self):
        name = 'test/test_gettime/vkso-tests/revision/kernel-reader/vkso_kernel_reader.c'
        old = run(['git', '-C', REPO, 'show', BASE + ':' + name])
        new = (REPO / name).read_text()
        self.assertEqual(definition(old, 'run_batch'), definition(new, 'run_batch'))
        self.assertIn('"scalar_control"', new)
        self.assertIn('"scalar_samples"', new)


if __name__ == '__main__':
    unittest.main(verbosity=2)
