#!/usr/bin/env python3
"""Synthetic record-corruption tests, never experiment or performance evidence."""
import csv
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location('bch_kernel_audit',
    Path(__file__).with_name('bch_kernel_audit.py'))
AUDITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDITOR)
BACKENDS = ('stock-kernel', 'matched-source-kernel', 'owner-kernel')
DECODE = ('decode-precomputed', 'decode-full')


def fixture_positions(seed, count, t):
    """Independent unsigned-arithmetic transcription of the driver's PRNG."""
    state, output = seed, []
    while len(output) < count:
        state = (state ^ (state // 4096)) % (2 ** 64)
        state = (state ^ (state * (2 ** 25))) % (2 ** 64)
        state = (state ^ (state // (2 ** 27))) % (2 ** 64)
        bit = ((state * 2685821657736338717) % (2 ** 64)) % (4096 + 13 * t)
        bit = 8 * (bit // 8) + 7 - (bit % 8)
        if bit < 4096 + 13 * t and bit not in output:
            output.append(bit)
    return output


def write_csv(path, fields, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def write_fixture(directory, measure):
    """Construct complete but explicitly synthetic observations for parser tests."""
    directory.mkdir()
    vectors, measurement_ids = [], {}
    unique = 0

    def add_vector(phase, round_number, t, errors, seed):
        nonlocal unique
        vector_id = unique
        unique += 1
        injected = fixture_positions(seed, errors, t)
        pairs = [(b, m) for b in BACKENDS for m in DECODE] if phase == 'correctness' else [('all', 'both')]
        for backend, mode in pairs:
            row = dict(zip(AUDITOR.VECTOR_FIELDS, (vector_id, phase, round_number,
                backend, 13, t, 512, errors, mode, hex(seed), ':'.join(map(str, injected)),
                errors if phase == 'correctness' else '',
                ':'.join(map(str, reversed(injected))) if phase == 'correctness' else '',
                1 if phase == 'correctness' else '', 1 if phase == 'correctness' else '',
                1 if phase == 'correctness' else '')))
            vectors.append(row)
        if phase == 'measurement':
            measurement_ids[(round_number, t, errors)] = (vector_id, seed)

    for case, t in enumerate((4, 8)):
        for trial in range(128):
            for errors in range(t + 1):
                add_vector('correctness', trial, t, errors,
                           0x63c5a17e9b ^ (case << 48) ^ (trial << 16) ^ errors)
    if measure:
        for case, t in enumerate((4, 8)):
            for errors in range(t + 1):
                add_vector('calibration', -1, t, errors, 0xca11b4a7 ^ (case << 32) ^ errors)
        for round_number in range(11):
            for case, t in enumerate((4, 8)):
                for errors in range(t + 1):
                    add_vector('measurement', round_number, t, errors,
                        0x9e3779b97f4a7c15 ^ (round_number << 40) ^ (case << 32) ^ errors)

    results = []
    if measure:
        for round_number in range(11):
            for case, t in enumerate((4, 8)):
                for op, mode in enumerate(('init', 'encode') + DECODE):
                    # Accumulate, then sort by the driver's cell/rotation schedule.
                    for errors in ([-1] if op == 0 else [0] if op == 1 else range(t + 1)):
                        for b, backend in enumerate(BACKENDS):
                            vector_id, seed = measurement_ids[(round_number, t, errors)] if op >= 2 else (-1, 0)
                            results.append(dict(zip(AUDITOR.RESULT_FIELDS, (round_number, backend,
                                13, t, 512, errors, mode, 100 + b + op, 10000000,
                                'ktime_get_ns_wall', 1, 1, hex(seed), vector_id, 0))))

        def order(row):
            op = ('init', 'encode') + DECODE
            op = op.index(row['mode'])
            case = (4, 8).index(row['t'])
            cell = op if op < 2 else 2 + row['errors'] * 2 + op - 2
            first = (row['round'] + case + op + max(row['errors'], 0)) % 3
            position = (BACKENDS.index(row['backend']) - first) % 3
            return row['round'], case, cell, position
        results.sort(key=order)

    status = dict(status='pass', errno=0, stage='complete', measure=int(measure),
        backends=3, correctness_vectors=128, decode_checks=10752,
        expected_decode_checks=10752, parity_checks=3588, geometry_checks=6,
        outer_runs=11, sample_ms=10, result_rows=len(results), vector_rows=len(vectors),
        unique_input_vectors=unique, affinity_cpu=1, timebase='ktime_get_ns_wall',
        codeword_seed_t4='0xb4c00000', codeword_seed_t8='0xb4c00001',
        init_includes_free=1, driver_disables_irq_or_preempt=0,
        helper_scope='native-kernel-imports')
    for t in (4, 8):
        status[f'm13_t{t}_ecc_bits'] = 13 * t
        status[f'm13_t{t}_ecc_bytes'] = (13 * t + 7) // 8
        for backend in BACKENDS:
            for mode in DECODE:
                status[f'm13_t{t}_{backend}_{mode}_checks'] = 128 * (t + 1)
    (directory / 'driver-status.txt').write_text(''.join(f'{k}={v}\n' for k, v in status.items()))
    write_csv(directory / 'driver-vectors.txt', AUDITOR.VECTOR_FIELDS, vectors)
    write_csv(directory / 'driver-results.txt', AUDITOR.RESULT_FIELDS, results)


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = tempfile.TemporaryDirectory(prefix='bch-audit-synthetic-')
        cls.fixture_root = Path(cls.fixtures.name)
        for measure in (False, True):
            write_fixture(cls.fixture_root / str(int(measure)), measure)

    @classmethod
    def tearDownClass(cls):
        cls.fixtures.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='bch-audit-corruption-')
        self.directory = Path(self.temporary.name)
        self.reset()

    def tearDown(self):
        self.temporary.cleanup()

    def reset(self, measure=True):
        for path in (self.fixture_root / str(int(measure))).iterdir():
            shutil.copyfile(path, self.directory / path.name)

    def rows(self, name):
        with (self.directory / f'driver-{name}.txt').open(newline='') as stream:
            return list(csv.DictReader(stream))

    def save(self, name, rows):
        fields = AUDITOR.VECTOR_FIELDS if name == 'vectors' else AUDITOR.RESULT_FIELDS
        write_csv(self.directory / f'driver-{name}.txt', fields, rows)

    def reject(self, message):
        with self.assertRaisesRegex(ValueError, message):
            AUDITOR.audit(self.directory, measure=True)

    def test_complete_correctness_and_full_measurement_accept(self):
        for measure, vector_rows, unique, timing in ((False, 10752, 1792, 0), (True, 10920, 1960, 1056)):
            self.reset(measure)
            report = AUDITOR.audit(self.directory, measure=measure)
            self.assertEqual(report['decode_checks'], 10752)
            self.assertEqual(report['vector_rows'], vector_rows)
            self.assertEqual(report['unique_input_vectors'], unique)
            self.assertEqual(report['timing_rows'], timing)
        # Fixture deliberately reverses returned positions: location order is immaterial.

    def test_missing_vector_rejected_even_if_status_count_adjusted(self):
        vectors = self.rows('vectors')
        self.save('vectors', vectors[:-1])
        path = self.directory / 'driver-status.txt'
        path.write_text(path.read_text().replace('vector_rows=10920', 'vector_rows=10919'))
        self.reject('missing records')

    def test_duplicate_vector_with_preserved_row_count(self):
        vectors = self.rows('vectors')
        vectors[1] = dict(vectors[0])
        self.save('vectors', vectors)
        self.reject('duplicate record')

    def test_missing_backend_or_mode_pair(self):
        for field in ('backend', 'mode'):
            self.reset()
            vectors = self.rows('vectors')
            vectors[0][field] = 'unrecorded'
            self.save('vectors', vectors)
            self.reject('backend/mode identity')

    def test_changed_input_rejected_even_if_all_six_observations_agree(self):
        vectors = self.rows('vectors')
        for row in vectors:
            if row['vector_id'] == '1':
                row['positions'] = row['returned_positions'] = '123'
        self.save('vectors', vectors)
        self.reject('incorrect seeded input positions')

    def test_wrong_seed_or_geometry(self):
        for field, value in (('seed', '0x123'), ('t', '8'), ('round', '1'), ('len', '511')):
            self.reset()
            vectors = self.rows('vectors')
            vectors[0][field] = value
            self.save('vectors', vectors)
            self.reject(f'wrong {field}')

    def test_duplicate_or_wrong_returned_locations(self):
        for value, message in (('123:123', 'duplicate bit location'),
                               ('123:124', 'decoder locations differ')):
            self.reset()
            vectors = self.rows('vectors')
            vectors[12]['returned_positions'] = value  # vector_id 2 has two errors.
            self.save('vectors', vectors)
            self.reject(message)

    def test_reported_failure_cannot_hide_behind_pass_status(self):
        for field in ('locations_equal', 'restored_codeword_equal', 'ecc_equal'):
            self.reset()
            vectors = self.rows('vectors')
            vectors[0][field] = '0'
            self.save('vectors', vectors)
            self.reject(f'{field} failed')

    def test_unobserved_calibration_cannot_claim_correctness(self):
        vectors = self.rows('vectors')
        vectors[10752]['found'] = '0'
        self.save('vectors', vectors)
        self.reject('unmeasured correctness fields must be empty')

    def test_status_disagreement(self):
        for key in ('errno', 'measure', 'sample_ms', 'affinity_cpu', 'parity_checks',
                    'm13_t4_stock-kernel_decode-precomputed_checks', 'unique_input_vectors'):
            self.reset()
            path = self.directory / 'driver-status.txt'
            lines = path.read_text().splitlines()
            path.write_text('\n'.join(key + '=-1' if line.startswith(key + '=') else line for line in lines) + '\n')
            self.reject('status ' + key)

    def test_duplicate_status_key(self):
        path = self.directory / 'driver-status.txt'
        path.write_text(path.read_text() + 'errno=0\n')
        self.reject('duplicate/empty status key')

    def test_missing_timing_row(self):
        results = self.rows('results')
        self.save('results', results[:-1])
        self.reject('missing or extra timing rows')

    def test_duplicate_timing_cell_without_count_change(self):
        results = self.rows('results')
        results[1] = dict(results[0])
        self.save('results', results)
        self.reject('duplicate timing cell')

    def test_wrong_timing_rotation(self):
        results = self.rows('results')
        results[0], results[1] = results[1], results[0]
        self.save('results', results)
        self.reject('rotation order')

    def test_cpu_errno_or_timebase_mismatch(self):
        for field, value in (('cpu_start', '0'), ('cpu_end', '0'), ('errno', '-1'),
                             ('timebase', 'CLOCK_PROCESS_CPUTIME_ID')):
            self.reset()
            results = self.rows('results')
            results[0][field] = value
            self.save('results', results)
            self.reject('incorrect ' + field)

    def test_invalid_duration_or_iteration(self):
        for field, value in (('ns', '0'), ('ns', '-1'), ('ns', '1.5'),
                             ('iterations', '0'), ('iterations', '10000001')):
            self.reset()
            results = self.rows('results')
            results[0][field] = value
            self.save('results', results)
            self.reject('invalid iteration count|invalid integer')

    def test_later_round_cannot_change_calibrated_iterations(self):
        results = self.rows('results')
        results[96]['iterations'] = str(int(results[96]['iterations']) + 1)
        self.save('results', results)
        self.reject('iterations changed')

    def test_decode_modes_must_share_input_vector(self):
        results = self.rows('results')
        full = next(row for row in results if row['mode'] == 'decode-full')
        full['vector_id'] = str(int(full['vector_id']) + 1)
        self.save('results', results)
        self.reject('input vector identity or mode pairing differs')

    def test_large_positive_wall_time_is_not_silently_filtered(self):
        results = self.rows('results')
        results[0]['ns'] = '60000000000'
        self.save('results', results)
        report = AUDITOR.audit(self.directory, measure=True)
        self.assertEqual(report['timing_ns_max'], 60000000000)

    def test_bad_header_and_missing_column(self):
        path = self.directory / 'driver-results.txt'
        path.write_text(path.read_text().replace('cpu_end', 'cpu_stop', 1))
        self.reject('unexpected CSV header')
        self.reset()
        lines = path.read_text().splitlines()
        lines[1] = lines[1].rsplit(',', 1)[0]
        path.write_text('\n'.join(lines) + '\n')
        self.reject('incomplete or extra columns')


if __name__ == '__main__':
    unittest.main()
