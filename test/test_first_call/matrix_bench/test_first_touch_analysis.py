"""Known synthetic tails and corrupt archives test the independent analyzer."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from analyze_first_touch import audit, reconstruct
from test_batch_archiving import RUNNER, fixture_environment


class FirstTouchAnalysisTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.logs = self.root / 'records'
        self.environment = fixture_environment(self.root)

    def collect_fixture(self, **updates):
        return subprocess.run(['bash', str(RUNNER)], cwd=self.root,
                              env={**self.environment, **updates}, capture_output=True,
                              text=True, timeout=10)

    def test_rejected_batch_tail_remains_in_unfiltered_view(self):
        result = self.collect_fixture()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = audit(self.logs)
        self.assertTrue(report['complete'])
        for group in report['groups'].values():
            self.assertEqual(group['views']['all_prepared_calls']['calls'], 20)
            self.assertEqual(group['views']['all_prepared_calls']['mean'], 1018)
            self.assertEqual(group['views']['all_prepared_calls']['p95'], 10000)
            self.assertEqual(group['views']['iqr_retained_calls']['calls'], 18)
            self.assertEqual(group['views']['iqr_retained_calls']['p95'], 20)
            self.assertEqual(group['views']['accepted_batch_calls']['calls'], 10)
            self.assertEqual(group['mean_accepted_batch_statistics']['median'], 20)
            self.assertEqual(group['iqr_excluded'], 2)

    def test_failure_is_not_counted_as_zero_cycle_sample(self):
        self.assertEqual(self.collect_fixture(FIXTURE_FAIL='1').returncode, 7)
        report = audit(self.logs)
        self.assertFalse(report['complete'])
        group = report['groups']['native/hot']
        self.assertEqual(group['preparation_failures'], 1)
        self.assertEqual(group['views']['all_prepared_calls'], {'calls': 0})
        self.assertEqual(report['groups']['stub/hot']['attempts'], 0)

    def test_completion_marker_cannot_hide_insufficient_batches(self):
        self.assertEqual(self.collect_fixture(MAX_ATTEMPTS='1').returncode, 2)
        self.assertFalse(audit(self.logs)['complete'])
        (self.logs/'complete.txt').write_text('status=complete\n')
        with self.assertRaisesRegex(ValueError, 'completion marker'):
            audit(self.logs)

    def test_changed_raw_value_and_missing_rows_are_detected(self):
        self.assertEqual(self.collect_fixture().returncode, 0)
        path = self.logs/'native/hot/attempt-02.samples.csv'
        original = path.read_text()
        for change in (original.replace(',20,0,0', ',21,0,0', 1),
                       '\n'.join(original.splitlines()[:-1])+'\n'):
            with self.subTest(change=change):
                path.write_text(change)
                with self.assertRaises(ValueError):
                    audit(self.logs)
        path.write_text(original)
        stdout = self.logs/'native/hot/attempt-02.stdout'
        stdout.write_text(stdout.read_text().replace('Median Cycles: 20', 'Median Cycles: 30'))
        with self.assertRaisesRegex(ValueError, 'Median Cycles'):
            audit(self.logs)

    def test_fault_class_filter_keeps_unexpected_faults_visible(self):
        rows = [dict(sample=str(i), target='native', condition='pte-cold',
                     preparation_status='0', cycles=str(cycles), minflt=str(minor), majflt=str(major))
                for i, (cycles, minor, major) in enumerate(((50, 1, 0), (1000, 0, 1), (60, 1, 0)))]
        views = reconstruct(rows, 'native', 'pte-cold')
        self.assertEqual(views['all_prepared_calls'], [50, 1000, 60])
        self.assertEqual(views['expected_fault_calls'], [50, 60])
        self.assertEqual(views['fault_classes'], {'1/0': 2, '0/1': 1})

    def test_unlogged_raw_file_is_not_silently_omitted(self):
        self.assertEqual(self.collect_fixture().returncode, 0)
        source = self.logs/'native/hot/attempt-02.samples.csv'
        (self.logs/'native/hot/attempt-03.samples.csv').write_bytes(source.read_bytes())
        with self.assertRaisesRegex(ValueError, 'no attempt-ledger entry'):
            audit(self.logs)


if __name__ == '__main__':
    unittest.main()
