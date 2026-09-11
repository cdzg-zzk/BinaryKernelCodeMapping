"""Exercise shell archival decisions with synthetic output, never a real DSO."""
import csv
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

RUNNER = Path(__file__).resolve().with_name('run_benchmarks.sh')
FIXTURE = '''#!/usr/bin/env python3
# Synthetic orchestration fixture. No timing or DSO loading occurs.
import argparse,csv,os
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('-t');p.add_argument('-s');p.add_argument('-n',type=int);p.add_argument('-o',type=Path)
a=p.parse_args()
attempt=int(a.o.name.split('.')[0].split('-')[-1])
failed=os.environ.get('FIXTURE_FAIL')=='1'
with a.o.open('x',newline='') as f:
 w=csv.writer(f);w.writerow(['sample','target','condition','preparation_status','cycles','minflt','majflt'])
 if failed: w.writerow([0,a.t,a.s,-1,'','',''])
 else:
  for i in range(a.n): w.writerow([i,a.t,a.s,0,10000 if attempt==1 and i<2 else 20,0,0])
if failed:
 print('synthetic preparation failure',file=__import__('sys').stderr)
 raise SystemExit(7)
retained=a.n-2 if attempt==1 else a.n
print(f'Target: {a.t}\\nCondition: {a.s}\\nTotal Runs: {a.n}')
print(f'Expected-Fault Runs: {a.n} (100.0%)')
print(f'Valid Runs (IQR): {retained} ({retained*100/a.n:.1f}% retained)')
print('Fault Mismatches: 0\\nAvg Minor Faults: 0.00 per run\\nAvg Major Faults: 0.00 per run')
print('Median Cycles: 20\\nMean Cycles: 20.00\\nStd Deviation: 0.00')
print('P25 Cycles: 20\\nP75 Cycles: 20\\nP95 Cycles: 20')
'''


def fixture_environment(root):
    binary = root / 'benchmark_first_touch'
    binary.write_text(FIXTURE)
    binary.chmod(0o755)
    environment = dict(os.environ, STUB_DSO='/synthetic/stub',
                                NATIVE_DSO='/synthetic/native', CONDITIONS_OVERRIDE='hot',
                                NUM_RUNS='10', TARGET_SUCCESSES='1', MAX_ATTEMPTS='2',
                                THRESHOLD_PCT='90', CPU=str(min(os.sched_getaffinity(0))),
                                CSV_FILE=str(root / 'result.csv'), LOG_DIR=str(root / 'records'))
    environment.pop('FIXTURE_FAIL', None)
    return environment


class BatchArchivingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.logs = self.root / 'records'
        self.output = self.root / 'result.csv'
        self.environment = fixture_environment(self.root)

    def run_fixture(self, **updates):
        return subprocess.run(['bash', str(RUNNER)], cwd=self.root,
                              env={**self.environment, **updates}, capture_output=True,
                              text=True, timeout=10)

    def decisions(self):
        with (self.logs / 'attempts.csv').open() as stream:
            return list(csv.DictReader(stream))

    def test_rejected_and_accepted_attempts_preserve_raw_records(self):
        result = self.run_fixture()
        self.assertEqual(result.returncode, 0, result.stderr)
        decisions = self.decisions()
        self.assertEqual([r['decision'] for r in decisions],
                         ['rejected', 'accepted', 'rejected', 'accepted'])
        self.assertEqual([r['iqr_retained'] for r in decisions], ['8', '10', '8', '10'])
        files = list(self.logs.glob('*/*/*.samples.csv'))
        self.assertEqual(len(files), 4)
        for file in files:
            with file.open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 10)
        self.assertTrue((self.logs / 'complete.txt').exists())
        before = self.output.read_bytes()
        second = self.run_fixture()
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(self.output.read_bytes(), before)

    def test_exhausted_attempts_are_incomplete(self):
        result = self.run_fixture(MAX_ATTEMPTS='1')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual([r['decision'] for r in self.decisions()], ['rejected', 'rejected'])
        self.assertFalse((self.logs / 'complete.txt').exists())

    def test_benchmark_failure_is_retained_and_stops_batch(self):
        result = self.run_fixture(FIXTURE_FAIL='1')
        self.assertEqual(result.returncode, 7, result.stderr)
        decisions = self.decisions()
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]['decision'], 'failed')
        self.assertEqual(decisions[0]['exit_status'], '7')
        stderr = self.logs / 'native/hot/attempt-01.stderr'
        self.assertIn('synthetic preparation failure', stderr.read_text())
        self.assertFalse((self.logs / 'complete.txt').exists())


if __name__ == '__main__':
    unittest.main()
