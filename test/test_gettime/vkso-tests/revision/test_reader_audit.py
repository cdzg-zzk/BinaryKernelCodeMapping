"""Arithmetic and corruption fixtures; these are not performance results."""
import copy
import unittest

from audit_reader_records import LOAD_PROTOCOL, compare_values, reconstruct_window


class ReaderAuditTests(unittest.TestCase):
    def setUp(self):
        self.parameters = dict(reader_cpus='1,2,3', seconds=15,
                               iterations=500000, warmup=10000,
                               paced_iterations=10000, paced_warmup=0)
        self.items = [dict(
            backend='vkso', api='clock_gettime_monotonic', reader=str(reader),
            cpu=str(reader + 1), readers='2', scheduled_start_ns='1000',
            scheduled_end_ns='15000001000', start_ns='1000', end_ns='15000001000',
            measured_calls=str(calls), conditioning_calls='0', measured_batches=str(batches),
            tsc_cycles_per_call='50', target_total_calls_per_second='1000000',
            late_batches='1', writer_start_ns='1000001000', writer_end_ns='14000001000',
            measurement_window=LOAD_PROTOCOL)
            for reader, calls, batches in ((0, 15000000, 1500), (1, 7500000, 750))]

    def reconstruct(self, items=None):
        return reconstruct_window(self.items if items is None else items,
                                  'monotonic', 2, 1000000, self.parameters, 'vkso')

    def test_unequal_rates_and_lateness_are_retained(self):
        observed, total, fairness, window = self.reconstruct()
        self.assertEqual([r['rate'] for r in observed], [1000000, 500000])
        self.assertEqual([r['late'] for r in observed], [1, 1])
        self.assertEqual(total, 1500000)
        self.assertAlmostEqual(fairness, .9)
        self.assertEqual(window['writer_envelope_seconds'], 13)
        self.assertEqual(window['leading_margin_seconds'], 1)
        self.assertEqual(window['trailing_margin_seconds'], 1)

    def test_control_envelope_need_not_equal_nominal_recording_duration(self):
        for row in self.items:
            row['writer_end_ns'] = '14020001000'
        self.assertAlmostEqual(self.reconstruct()[3]['writer_envelope_seconds'], 13.02)

    def test_corrupt_counter_identity_and_window_are_rejected(self):
        corruptions = {
            'reader': '1', 'cpu': '2', 'readers': '3', 'backend': 'raw',
            'api': 'clock_gettime_monotonic_raw', 'measured_calls': '15000001',
            'conditioning_calls': '10', 'late_batches': '1501',
            'target_total_calls_per_second': '0', 'measurement_window': 'unknown',
            'start_ns': '1000001000', 'end_ns': '14000001000',
            'scheduled_end_ns': '16000001000', 'writer_start_ns': '2000001000',
            'tsc_cycles_per_call': 'nan',
        }
        for field, value in corruptions.items():
            with self.subTest(field=field):
                items = copy.deepcopy(self.items)
                items[0][field] = value
                with self.assertRaises(ValueError):
                    self.reconstruct(items)

    def test_missing_reader_rejected(self):
        with self.assertRaises(ValueError):
            self.reconstruct(self.items[:1])

    def test_normalized_value_change_and_missing_row_rejected(self):
        raw = {('example', 'total_rate', 'calls/s', LOAD_PROTOCOL, '3'): 1500000.0}
        row = dict(method='vkso', scenario='example', metric='total_rate', unit='calls/s',
                   protocol=LOAD_PROTOCOL, round='3', value='1500000.0')
        compare_values([row], 'vkso', raw)
        for value in ('1500010', 'nan', 'inf'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                compare_values([{**row, 'value': value}], 'vkso', raw)
        with self.assertRaises(ValueError):
            compare_values([], 'vkso', raw)


if __name__ == '__main__':
    unittest.main()
