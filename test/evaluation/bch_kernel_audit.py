#!/usr/bin/env python3
"""Replay the complete BCH kernel-driver records; no kernel access is required."""
from pathlib import Path
import argparse
from collections import Counter
import csv
import io
import json


BACKENDS = ('stock-kernel', 'matched-source-kernel', 'owner-kernel')
MODES = ('init', 'encode', 'decode-precomputed', 'decode-full')
VECTOR_FIELDS = ('vector_id', 'phase', 'round', 'backend', 'm', 't', 'len', 'errors',
                 'mode', 'seed', 'positions', 'found', 'returned_positions',
                 'locations_equal', 'restored_codeword_equal', 'ecc_equal')
RESULT_FIELDS = ('round', 'backend', 'm', 't', 'len', 'errors', 'mode', 'iterations',
                 'ns', 'timebase', 'cpu_start', 'cpu_end', 'seed', 'vector_id', 'errno')
MASK64 = (1 << 64) - 1


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, label):
    try:
        require(isinstance(value, str) and value.strip() == value and value != '',
                f'{label}: missing or padded integer')
        return int(value, 16 if value.lower().startswith('0x') else 10)
    except (ValueError, TypeError) as error:
        raise ValueError(f'{label}: invalid integer {value!r}') from error


def read_status(path):
    result = {}
    for line in path.read_text().splitlines():
        require('=' in line, f'{path.name}: invalid status line')
        key, value = line.split('=', 1)
        require(key and key not in result, f'{path.name}: duplicate/empty status key {key!r}')
        result[key] = value
    require(result, f'{path.name}: empty status')
    return result


def read_csv(path, fields):
    reader = csv.DictReader(io.StringIO(path.read_text()))
    require(tuple(reader.fieldnames or ()) == fields, f'{path.name}: unexpected CSV header')
    rows = list(reader)
    for index, row in enumerate(rows):
        require(set(row) == set(fields) and all(value is not None for value in row.values()),
                f'{path.name}: incomplete or extra columns at row {index}')
    return rows


def positions(value, label):
    values = [] if value == '' else [integer(x, label) for x in value.split(':')]
    require(len(set(values)) == len(values), f'{label}: duplicate bit location')
    return values


def expected_positions(seed, errors, nbits):
    result = []
    state = seed
    while len(result) < errors:
        state ^= state >> 12
        state ^= (state << 25) & MASK64
        state ^= state >> 27
        candidate = ((state * 2685821657736338717) & MASK64) % nbits
        candidate = (candidate & ~7) | (7 - (candidate & 7))
        if candidate < nbits and candidate not in result:
            result.append(candidate)
    return result


def vector_plan(measure, correctness_vectors, outer_runs):
    plan = []
    for case, t in enumerate((4, 8)):
        for trial in range(correctness_vectors):
            for errors in range(t + 1):
                seed = 0x63c5a17e9b ^ (case << 48) ^ (trial << 16) ^ errors
                plan.append(('correctness', trial, t, errors, seed))
    if measure:
        for case, t in enumerate((4, 8)):
            for errors in range(t + 1):
                plan.append(('calibration', -1, t, errors,
                             0xca11b4a7 ^ (case << 32) ^ errors))
        for round_number in range(outer_runs):
            for case, t in enumerate((4, 8)):
                for errors in range(t + 1):
                    plan.append(('measurement', round_number, t, errors,
                        0x9e3779b97f4a7c15 ^ (round_number << 40) ^ (case << 32) ^ errors))
    return plan


def audit(directory: Path, *, measure: bool, expected_cpu: int = 1,
          correctness_vectors: int = 128, outer_runs: int = 11, sample_ms: int = 10) -> dict:
    directory = Path(directory)
    require(correctness_vectors == 128 and 1 <= outer_runs <= 128 and 1 <= sample_ms <= 100,
            'requested audit parameters do not match the driver contract')
    status = read_status(directory / 'driver-status.txt')
    vector_rows = read_csv(directory / 'driver-vectors.txt', VECTOR_FIELDS)
    result_rows = read_csv(directory / 'driver-results.txt', RESULT_FIELDS)
    expected_checks = correctness_vectors * (5 + 9) * len(BACKENDS) * 2
    expected_result_rows = outer_runs * len(BACKENDS) * ((2 + 2 * 5) + (2 + 2 * 9)) if measure else 0
    text_status = {'status': 'pass', 'stage': 'complete', 'timebase': 'ktime_get_ns_wall',
                   'helper_scope': 'native-kernel-imports'}
    for key, expected in text_status.items():
        require(status.get(key) == expected, f'status {key}: expected {expected!r}')
    numeric_status = {'errno': 0, 'measure': int(measure), 'backends': len(BACKENDS),
        'correctness_vectors': correctness_vectors, 'decode_checks': expected_checks,
        'expected_decode_checks': expected_checks, 'outer_runs': outer_runs,
        'sample_ms': sample_ms, 'result_rows': expected_result_rows, 'affinity_cpu': expected_cpu,
        'init_includes_free': 1, 'driver_disables_irq_or_preempt': 0,
        'geometry_checks': 2 * len(BACKENDS),
        'codeword_seed_t4': 0xb4c00000, 'codeword_seed_t8': 0xb4c00001}
    for t in (4, 8):
        numeric_status[f'm13_t{t}_ecc_bits'] = 13 * t
        numeric_status[f'm13_t{t}_ecc_bytes'] = (13 * t + 7) // 8
        for backend in BACKENDS:
            for mode in MODES[2:]:
                numeric_status[f'm13_t{t}_{backend}_{mode}_checks'] = correctness_vectors * (t + 1)
    for key, expected in numeric_status.items():
        require(integer(status.get(key), f'status {key}') == expected,
                f'status {key}: expected {expected}')

    plan = vector_plan(measure, correctness_vectors, outer_runs)
    expected_keys = []
    for vector_id, (phase, _round, _t, _errors, _seed) in enumerate(plan):
        if phase == 'correctness':
            expected_keys.extend((vector_id, backend, mode) for backend in BACKENDS for mode in MODES[2:])
        else:
            expected_keys.append((vector_id, 'all', 'both'))
    seen = set()
    actual_keys = []
    actual_checks = Counter()
    measurement_vectors = {}
    for row in vector_rows:
        vector_id = integer(row['vector_id'], 'vector_id')
        require(0 <= vector_id < len(plan), f'vector_id {vector_id}: outside plan')
        phase, round_number, t, errors, seed = plan[vector_id]
        key = (vector_id, row['backend'], row['mode'])
        require(key not in seen, f'vectors: duplicate record {key}')
        seen.add(key)
        actual_keys.append(key)
        require(row['phase'] == phase, f'vector {vector_id}: wrong phase')
        for field, expected in {'round': round_number, 'm': 13, 't': t, 'len': 512,
                                'errors': errors, 'seed': seed}.items():
            require(integer(row[field], f'vector {vector_id} {field}') == expected,
                    f'vector {vector_id}: wrong {field}')
        expected = expected_positions(seed, errors, 4096 + 13 * t)
        supplied = positions(row['positions'], f'vector {vector_id} positions')
        require(supplied == expected, f'vector {vector_id}: incorrect seeded input positions')
        if phase == 'correctness':
            require(row['backend'] in BACKENDS and row['mode'] in MODES[2:],
                    f'vector {vector_id}: missing backend/mode identity')
            found = integer(row['found'], f'vector {vector_id} found')
            returned = positions(row['returned_positions'], f'vector {vector_id} returned positions')
            require(found == errors and len(returned) == errors and set(returned) == set(expected),
                    f'vector {vector_id}: decoder locations differ from injected locations')
            for field in ('locations_equal', 'restored_codeword_equal', 'ecc_equal'):
                require(integer(row[field], f'vector {vector_id} {field}') == 1,
                        f'vector {vector_id}: {field} failed')
            actual_checks[(t, row['backend'], row['mode'])] += 1
        else:
            require((row['backend'], row['mode']) == ('all', 'both'),
                    f'vector {vector_id}: non-correctness pairing differs')
            require(all(row[field] == '' for field in ('found', 'returned_positions',
                        'locations_equal', 'restored_codeword_equal', 'ecc_equal')),
                    f'vector {vector_id}: unmeasured correctness fields must be empty')
            if phase == 'measurement':
                measurement_vectors[(round_number, t, errors)] = (vector_id, seed)
    require(actual_keys == expected_keys, 'vectors: missing records or incorrect backend/mode ordering')
    require(sum(actual_checks.values()) == expected_checks, 'vectors: incomplete actual decode checks')

    expected_results = []
    if measure:
        for round_number in range(outer_runs):
            for case, t in enumerate((4, 8)):
                cells = [(0, -1), (1, 0)]
                cells += [(op, errors) for errors in range(t + 1) for op in (2, 3)]
                for op, errors in cells:
                    for position in range(len(BACKENDS)):
                        backend = BACKENDS[(position + round_number + case + op + max(errors, 0)) % len(BACKENDS)]
                        expected_results.append((round_number, backend, t, errors, MODES[op]))
    require(len(result_rows) == len(expected_results), 'results: missing or extra timing rows')
    seen_results = set()
    iteration_series = {}
    ns_values = []
    for index, (row, expected) in enumerate(zip(result_rows, expected_results)):
        round_number, backend, t, errors, mode = expected
        key = (integer(row['round'], 'result round'), row['backend'],
               integer(row['t'], 'result t'), integer(row['errors'], 'result errors'), row['mode'])
        require(key not in seen_results, f'results: duplicate timing cell {key}')
        seen_results.add(key)
        require(key == expected, f'result {index}: incorrect timing cell or rotation order')
        for field, value in {'m': 13, 'len': 512, 'cpu_start': expected_cpu,
                             'cpu_end': expected_cpu, 'errno': 0}.items():
            require(integer(row[field], f'result {index} {field}') == value,
                    f'result {index}: incorrect {field}')
        require(row['timebase'] == 'ktime_get_ns_wall', f'result {index}: incorrect timebase')
        iterations = integer(row['iterations'], f'result {index} iterations')
        ns = integer(row['ns'], f'result {index} ns')
        require(1 <= iterations <= 10000000 and 0 < ns <= MASK64,
                f'result {index}: invalid iteration count or elapsed ns')
        series = (backend, t, errors, mode)
        require(iteration_series.setdefault(series, iterations) == iterations,
                f'result {index}: iterations changed after per-cell calibration')
        expected_vector, expected_seed = measurement_vectors[(round_number, t, errors)] if mode in MODES[2:] else (-1, 0)
        require(integer(row['vector_id'], f'result {index} vector_id') == expected_vector and
                integer(row['seed'], f'result {index} seed') == expected_seed,
                f'result {index}: input vector identity or mode pairing differs')
        ns_values.append(ns)

    require(integer(status.get('vector_rows'), 'status vector_rows') == len(vector_rows),
            'status vector_rows does not match emitted vector CSV')
    require(integer(status.get('unique_input_vectors'), 'status unique_input_vectors') == len(plan),
            'status unique_input_vectors does not match distinct vector identities')
    expected_parity_checks = (2 + correctness_vectors * (5 + 9)) * (len(BACKENDS) - 1)
    require(integer(status.get('parity_checks'), 'status parity_checks') == expected_parity_checks,
            'status parity_checks does not match per-backend parity comparisons')
    return {'status': 'pass', 'scope': 'complete kernel-driver record replay; guest timings do not '
            'establish a paper performance result', 'measure': int(measure), 'backends': list(BACKENDS),
            'correctness_vectors': correctness_vectors, 'decode_checks': sum(actual_checks.values()),
            'parity_checks': expected_parity_checks, 'vector_rows': len(vector_rows),
            'unique_input_vectors': len(plan), 'timing_rows': len(result_rows),
            'expected_cpu': expected_cpu, 'outer_runs': outer_runs, 'sample_ms': sample_ms,
            'timing_ns_min': min(ns_values) if ns_values else None,
            'timing_ns_max': max(ns_values) if ns_values else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--measure', type=int, choices=(0, 1), required=True)
    parser.add_argument('--expected-cpu', type=int, default=1)
    parser.add_argument('--correctness-vectors', type=int, default=128)
    parser.add_argument('--outer-runs', type=int, default=11)
    parser.add_argument('--sample-ms', type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(audit(args.directory, measure=bool(args.measure), expected_cpu=args.expected_cpu,
        correctness_vectors=args.correctness_vectors, outer_runs=args.outer_runs,
        sample_ms=args.sample_ms), indent=2))


if __name__ == '__main__':
    main()
