// SPDX-License-Identifier: GPL-2.0
/* Test driver: calls the original stock and actual export-owner public APIs. */
#include <linux/bch.h>
#include <linux/cpu.h>
#include <linux/cpumask.h>
#include <linux/debugfs.h>
#include <linux/err.h>
#include <linux/ktime.h>
#include <linux/math64.h>
#include <linux/mm.h>
#include <linux/module.h>
#include <linux/sched.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <linux/vmalloc.h>

extern struct bch_control *vkso_bch_init(int m, int t, unsigned int poly,
				       bool swap_bits);
extern void vkso_bch_free(struct bch_control *bch);
extern void vkso_bch_encode(struct bch_control *bch, const u8 *data,
			    unsigned int len, u8 *ecc);
extern int vkso_bch_decode(struct bch_control *bch, const u8 *data,
	unsigned int len, const u8 *recv_ecc, const u8 *calc_ecc,
	const unsigned int *syn, unsigned int *errloc);
extern struct bch_control *matched_bch_init(int m, int t, unsigned int poly,
					  bool swap_bits);
extern void matched_bch_free(struct bch_control *bch);
extern void matched_bch_encode(struct bch_control *bch, const u8 *data,
			       unsigned int len, u8 *ecc);
extern int matched_bch_decode(struct bch_control *bch, const u8 *data,
	unsigned int len, const u8 *recv_ecc, const u8 *calc_ecc,
	const unsigned int *syn, unsigned int *errloc);

#define BACKENDS 3
#define CASES 2
#define MAX_T 8
#define DATA_BYTES 512
#define VECTOR_TRIALS 128
#define ERROR_GROUPS 14 /* (t4 + 1) + (t8 + 1) */
#define EXPECTED_DECODE_CHECKS (VECTOR_TRIALS * ERROR_GROUPS * BACKENDS * 2)
#define ROWS_PER_ROUND (BACKENDS * (2 * CASES + 2 * ERROR_GROUPS))
#define MAX_ITERATIONS 10000000ULL
#define PREFIX "BCH_KERNEL_BENCH "

static bool measure;
static unsigned int correctness_vectors = VECTOR_TRIALS;
static unsigned int outer_runs = 11;
static unsigned int sample_ms = 10;
module_param(measure, bool, 0444);
module_param(correctness_vectors, uint, 0444);
module_param(outer_runs, uint, 0444);
module_param(sample_ms, uint, 0444);
MODULE_PARM_DESC(measure, "0: full correctness only; 1: also collect wall-time samples");
MODULE_PARM_DESC(correctness_vectors, "Must be 128; complete correctness coverage");
MODULE_PARM_DESC(outer_runs, "Timing rounds, default 11, range 1..128");
MODULE_PARM_DESC(sample_ms, "Calibration target in milliseconds, default 10, range 1..100");

enum operation { OP_INIT, OP_ENCODE, OP_PRECOMPUTED, OP_FULL, OPERATIONS };
static const char * const operation_names[] = {
	"init", "encode", "decode-precomputed", "decode-full"
};

struct backend {
	const char *name;
	struct bch_control *(*init)(int, int, unsigned int, bool);
	void (*free)(struct bch_control *);
	void (*encode)(struct bch_control *, const u8 *, unsigned int, u8 *);
	int (*decode)(struct bch_control *, const u8 *, unsigned int,
		      const u8 *, const u8 *, const unsigned int *, unsigned int *);
};

static const struct backend backends[BACKENDS] = {
	{ "stock-kernel", bch_init, bch_free, bch_encode, bch_decode },
	{ "matched-source-kernel", matched_bch_init, matched_bch_free,
	  matched_bch_encode, matched_bch_decode },
	{ "owner-kernel", vkso_bch_init, vkso_bch_free,
	  vkso_bch_encode, vkso_bch_decode },
};

struct context {
	struct bch_control *control;
	u8 *work;
	u8 *difference;
	unsigned int errloc[MAX_T];
};

struct bench_case {
	unsigned int t, ecc_bits, ecc_bytes;
	u8 *codeword;
	struct context context[BACKENDS];
};

struct decode_evidence {
	int found;
	bool checked, locations_equal, restored_codeword_equal;
	unsigned int returned_positions[MAX_T];
};

struct vector_record {
	const char *phase;
	int round;
	unsigned int t, errors;
	u64 seed;
	unsigned int positions[MAX_T];
	bool ecc_equal[BACKENDS];
	struct decode_evidence checks[BACKENDS][2];
};

struct measurement {
	int round, errors, vector_id, error;
	unsigned int backend, t, operation, cpu_start, cpu_end;
	u64 iterations, ns, seed;
};

static struct bench_case cases[CASES];
static struct vector_record *vectors;
static struct measurement *results;
static unsigned int vector_count, vector_capacity, result_count, result_capacity;
static u64 calibrated[BACKENDS][CASES][OPERATIONS][MAX_T + 1];
static u64 decode_checks[CASES][BACKENDS][2];
static u64 parity_checks, geometry_checks;
static volatile u64 result_sink;
static int bound_cpu = -1, terminal_errno;
static const char *stage = "not-started";
static bool passed;
static struct dentry *debug_directory;

static u64 total_decode_checks(void)
{
	unsigned int c, b, m;
	u64 count = 0;

	for (c = 0; c < CASES; c++)
		for (b = 0; b < BACKENDS; b++)
			for (m = 0; m < 2; m++)
				count += decode_checks[c][b][m];
	return count;
}

static unsigned int exported_vector_rows(void)
{
	unsigned int i, rows = total_decode_checks();

	for (i = 0; i < vector_count; i++)
		if (strcmp(vectors[i].phase, "correctness"))
			rows++;
	return rows;
}

static u64 prng_next(u64 *state)
{
	u64 value = *state;

	value ^= value >> 12;
	value ^= value << 25;
	value ^= value >> 27;
	*state = value;
	return value * 2685821657736338717ULL;
}

static void error_vector(unsigned int *positions, unsigned int count,
			 unsigned int nbits, u64 seed)
{
	unsigned int i, j, candidate;
	bool duplicate;

	for (i = 0; i < count; i++) {
		do {
			candidate = prng_next(&seed) % nbits;
			candidate = (candidate & ~7U) | (7U - (candidate & 7U));
			duplicate = candidate >= nbits;
			for (j = 0; !duplicate && j < i; j++)
				duplicate = positions[j] == candidate;
		} while (duplicate);
		positions[i] = candidate;
	}
}

static int save_vector(const char *phase, int round, struct bench_case *test,
		       unsigned int errors, u64 seed, unsigned int *positions)
{
	struct vector_record *record;
	int index = vector_count;

	if (vector_count == vector_capacity)
		return -EOVERFLOW;
	error_vector(positions, errors, 8 * DATA_BYTES + test->ecc_bits, seed);
	record = &vectors[vector_count++];
	record->phase = phase;
	record->round = round;
	record->t = test->t;
	record->errors = errors;
	record->seed = seed;
	memcpy(record->positions, positions, errors * sizeof(*positions));
	return index;
}

static void flip_bits(u8 *data, const unsigned int *positions, unsigned int count)
{
	unsigned int i;

	for (i = 0; i < count; i++)
		data[positions[i] / 8] ^= 1U << (positions[i] & 7);
}

static void free_cases(void)
{
	unsigned int c, b;

	for (c = 0; c < CASES; c++) {
		for (b = 0; b < BACKENDS; b++) {
			struct context *context = &cases[c].context[b];

			if (context->control)
				backends[b].free(context->control);
			kfree(context->work);
			kfree(context->difference);
			memset(context, 0, sizeof(*context));
		}
		kfree(cases[c].codeword);
		cases[c].codeword = NULL;
	}
}

static int initialize_cases(void)
{
	unsigned int c, b, i;

	for (c = 0; c < CASES; c++) {
		struct bench_case *test = &cases[c];
		u64 seed = 0xb4c00000ULL + c;

		test->t = c ? 8 : 4;
		for (b = 0; b < BACKENDS; b++) {
			struct context *context = &test->context[b];
			struct bch_control *control;

			control = backends[b].init(13, test->t, 0, false);
			if (!control)
				return -ENOMEM;
			context->control = control;
			if (control->m != 13 || control->t != test->t ||
			    !control->ecc_bytes || control->ecc_bits > 13 * test->t ||
			    control->ecc_bytes != DIV_ROUND_UP(13 * test->t, 8))
				return -EPROTO;
			if (!b) {
				test->ecc_bits = control->ecc_bits;
				test->ecc_bytes = control->ecc_bytes;
				test->codeword = kzalloc(DATA_BYTES + test->ecc_bytes, GFP_KERNEL);
				if (!test->codeword)
					return -ENOMEM;
				for (i = 0; i < DATA_BYTES; i++)
					test->codeword[i] = prng_next(&seed);
			} else if (control->ecc_bits != test->ecc_bits ||
				   control->ecc_bytes != test->ecc_bytes) {
				return -EPROTO;
			}
			geometry_checks++;
			context->work = kmalloc(DATA_BYTES + test->ecc_bytes, GFP_KERNEL);
			context->difference = kzalloc(test->ecc_bytes, GFP_KERNEL);
			if (!context->work || !context->difference)
				return -ENOMEM;
			backends[b].encode(control, test->codeword, DATA_BYTES, context->difference);
			if (!b)
				memcpy(test->codeword + DATA_BYTES, context->difference, test->ecc_bytes);
			else if (memcmp(test->codeword + DATA_BYTES, context->difference, test->ecc_bytes))
				return -EBADMSG;
			else
				parity_checks++;
		}
	}
	return 0;
}

static void prepare(struct bench_case *test, unsigned int backend,
		    const unsigned int *positions, unsigned int errors, bool precomputed)
{
	struct context *context = &test->context[backend];
	unsigned int i;

	memcpy(context->work, test->codeword, DATA_BYTES + test->ecc_bytes);
	flip_bits(context->work, positions, errors);
	memset(context->errloc, 0xff, sizeof(context->errloc));
	if (precomputed) {
		memset(context->difference, 0, test->ecc_bytes);
		backends[backend].encode(context->control, context->work,
					DATA_BYTES, context->difference);
		for (i = 0; i < test->ecc_bytes; i++)
			context->difference[i] ^= context->work[DATA_BYTES + i];
	}
}

static int decode_once(struct bench_case *test, unsigned int backend, enum operation op)
{
	struct context *context = &test->context[backend];

	if (op == OP_PRECOMPUTED)
		return backends[backend].decode(context->control, NULL, DATA_BYTES,
			NULL, context->difference, NULL, context->errloc);
	return backends[backend].decode(context->control, context->work, DATA_BYTES,
		context->work + DATA_BYTES, NULL, NULL, context->errloc);
}

static int check_decode(unsigned int case_index, unsigned int backend,
			enum operation op, unsigned int *positions, unsigned int errors,
			struct decode_evidence *evidence)
{
	struct bench_case *test = &cases[case_index];
	struct context *context = &test->context[backend];
	unsigned int i, j;
	int found;

	/* A previous mode's output must not satisfy the current location check. */
	memset(context->errloc, 0xff, sizeof(context->errloc));
	found = decode_once(test, backend, op);
	evidence->found = found;
	memcpy(evidence->returned_positions, context->errloc, sizeof(context->errloc));
	if (found != errors)
		goto mismatch;
	for (i = 0; i < errors; i++) {
		bool present = false;

		for (j = 0; j < errors; j++)
			if (positions[i] == context->errloc[j])
				present = true;
		if (!present)
			goto mismatch;
	}
	evidence->locations_equal = true;
	/* Equal count + every distinct expected location implies the exact set. */
	flip_bits(context->work, context->errloc, errors);
	if (memcmp(context->work, test->codeword, DATA_BYTES + test->ecc_bytes))
		goto mismatch;
	evidence->restored_codeword_equal = true;
	flip_bits(context->work, context->errloc, errors);
	evidence->checked = true;
	decode_checks[case_index][backend][op - OP_PRECOMPUTED]++;
	return 0;
mismatch:
	pr_err(PREFIX "decode-mismatch backend=%s m=13 t=%u errors=%u mode=%s found=%d vector_id=%u\n",
		backends[backend].name, test->t, errors, operation_names[op], found,
		vector_count ? vector_count - 1 : 0);
	return -EBADMSG;
}

static int correctness(void)
{
	unsigned int c, trial, errors, b, op, positions[MAX_T] = {0};
	int error;

	for (c = 0; c < CASES; c++) {
		struct bench_case *test = &cases[c];

		for (trial = 0; trial < correctness_vectors; trial++) {
			for (errors = 0; errors <= test->t; errors++) {
				struct vector_record *record;
				u64 seed = 0x63c5a17e9bULL ^ ((u64)c << 48) ^
					((u64)trial << 16) ^ errors;

				error = save_vector("correctness", trial, test, errors, seed, positions);
				if (error < 0)
					return error;
				record = &vectors[error];
				for (b = 0; b < BACKENDS; b++)
					prepare(test, b, positions, errors, true);
				record->ecc_equal[0] = true;
				for (b = 1; b < BACKENDS; b++) {
					if (memcmp(test->context[0].difference, test->context[b].difference,
						   test->ecc_bytes))
						return -EBADMSG;
					record->ecc_equal[b] = true;
					parity_checks++;
				}
				for (b = 0; b < BACKENDS; b++)
					for (op = OP_PRECOMPUTED; op <= OP_FULL; op++) {
						error = check_decode(c, b, op, positions, errors,
							&record->checks[b][op - OP_PRECOMPUTED]);
						if (error)
							return error;
					}
			}
			cond_resched();
		}
		pr_info(PREFIX "correctness m=13 t=%u trials=%u backends=3 status=pass decode_checks=%llu\n",
			test->t, correctness_vectors,
			decode_checks[c][0][0] + decode_checks[c][0][1] +
			decode_checks[c][1][0] + decode_checks[c][1][1] +
			decode_checks[c][2][0] + decode_checks[c][2][1]);
	}
	return total_decode_checks() == EXPECTED_DECODE_CHECKS ? 0 : -EPROTO;
}

static int check_cpu(void)
{
	if (cpumask_weight(current->cpus_ptr) != 1 ||
	    cpumask_first(current->cpus_ptr) != bound_cpu ||
	    raw_smp_processor_id() != bound_cpu)
		return -EXDEV;
	return 0;
}

static int time_batch(struct bench_case *test, unsigned int backend,
		enum operation op, unsigned int errors, u64 iterations,
		struct measurement *record)
{
	u64 start, end, i;
	s64 decoded = 0;
	int error;

	error = check_cpu();
	if (error)
		return error;
	record->cpu_start = raw_smp_processor_id();
	start = ktime_get_ns();
	for (i = 0; i < iterations; i++) {
		if (op == OP_INIT) {
			struct bch_control *control = backends[backend].init(13, test->t, 0, false);

			if (!control)
				break;
			backends[backend].free(control);
		} else if (op == OP_ENCODE) {
			backends[backend].encode(test->context[backend].control,
					test->codeword, DATA_BYTES, NULL);
		} else {
			decoded += decode_once(test, backend, op);
		}
	}
	end = ktime_get_ns();
	record->cpu_end = raw_smp_processor_id();
	record->iterations = i;
	record->ns = end - start;
	result_sink += decoded + i;
	error = check_cpu();
	if (!error && i != iterations)
		error = -ENOMEM;
	if (!error && op >= OP_PRECOMPUTED && decoded != (s64)(iterations * errors))
		error = -EBADMSG;
	if (!error && !record->ns)
		error = -ERANGE;
	record->error = error;
	return error;
}

static int calibrate(struct bench_case *test, unsigned int backend,
		enum operation op, unsigned int errors, u64 *iterations)
{
	struct measurement sample = {0};
	u64 count = 1, target_ns = (u64)sample_ms * NSEC_PER_MSEC;
	int error;

	do {
		error = time_batch(test, backend, op, errors, count, &sample);
		if (error)
			return error;
		if (sample.ns >= target_ns / 8 || count >= 1000000)
			break;
		count *= 2;
		cond_resched();
	} while (true);
	*iterations = clamp_t(u64, div64_u64(count * target_ns, sample.ns), 1, MAX_ITERATIONS);
	return 0;
}

static int calibrate_all(void)
{
	unsigned int c, b, op, errors, positions[MAX_T] = {0};
	int error;

	for (c = 0; c < CASES; c++) {
		struct bench_case *test = &cases[c];

		for (b = 0; b < BACKENDS; b++)
			for (op = OP_INIT; op <= OP_ENCODE; op++) {
				error = calibrate(test, b, op, 0, &calibrated[b][c][op][0]);
				if (error)
					return error;
			}
		for (errors = 0; errors <= test->t; errors++) {
			u64 seed = 0xca11b4a7ULL ^ ((u64)c << 32) ^ errors;

			error = save_vector("calibration", -1, test, errors, seed, positions);
			if (error < 0)
				return error;
			for (op = OP_PRECOMPUTED; op <= OP_FULL; op++)
				for (b = 0; b < BACKENDS; b++) {
					prepare(test, b, positions, errors, op == OP_PRECOMPUTED);
					error = calibrate(test, b, op, errors, &calibrated[b][c][op][errors]);
					if (error)
						return error;
				}
		}
	}
	return 0;
}

static int sample_backends(unsigned int round, unsigned int case_index,
		enum operation op, unsigned int errors, u64 seed,
		int vector_id, unsigned int *positions)
{
	struct bench_case *test = &cases[case_index];
	unsigned int position, backend;
	int error;

	for (position = 0; position < BACKENDS; position++) {
		struct measurement warmup = {0};
		struct measurement *sample;
		u64 count;

		if (result_count == result_capacity)
			return -EOVERFLOW;
		backend = (position + round + case_index + op + errors) % BACKENDS;
		count = calibrated[backend][case_index][op][errors];
		if (op >= OP_PRECOMPUTED)
			prepare(test, backend, positions, errors, op == OP_PRECOMPUTED);
		/* Warmup and all preparation precede the recorded interval. */
		error = time_batch(test, backend, op, errors, min_t(u64, count, 32), &warmup);
		if (error)
			return error;
		sample = &results[result_count++];
		sample->round = round;
		sample->backend = backend;
		sample->t = test->t;
		sample->operation = op;
		sample->errors = op == OP_INIT ? -1 : errors;
		sample->seed = seed;
		sample->vector_id = vector_id;
		error = time_batch(test, backend, op, errors, count, sample);
		if (error) {
			pr_err(PREFIX "sample-fail round=%u backend=%s t=%u errors=%u mode=%s errno=%d\n",
				round, backends[backend].name, test->t, errors, operation_names[op], error);
			return error;
		}
		cond_resched();
	}
	return 0;
}

static int benchmark(void)
{
	unsigned int round, c, op, errors, positions[MAX_T] = {0};
	int error, vector_id;

	error = calibrate_all();
	if (error)
		return error;
	stage = "measurement";
	for (round = 0; round < outer_runs; round++)
		for (c = 0; c < CASES; c++) {
			for (op = OP_INIT; op <= OP_ENCODE; op++) {
				error = sample_backends(round, c, op, 0, 0, -1, positions);
				if (error)
					return error;
			}
			for (errors = 0; errors <= cases[c].t; errors++) {
				/* One vector shared by both decode modes and all three backends. */
				u64 seed = 0x9e3779b97f4a7c15ULL ^ ((u64)round << 40) ^
					((u64)c << 32) ^ errors;

				vector_id = save_vector("measurement", round, &cases[c], errors, seed, positions);
				if (vector_id < 0)
					return vector_id;
				for (op = OP_PRECOMPUTED; op <= OP_FULL; op++) {
					error = sample_backends(round, c, op, errors, seed, vector_id, positions);
					if (error)
						return error;
				}
			}
		}
	return result_count == outer_runs * ROWS_PER_ROUND ? 0 : -EPROTO;
}

static int status_show(struct seq_file *stream, void *unused)
{
	unsigned int c, b, m;

	seq_printf(stream, "status=%s\nerrno=%d\nstage=%s\nmeasure=%u\nbackends=3\n",
		passed ? "pass" : "fail", terminal_errno, stage, measure);
	seq_printf(stream, "correctness_vectors=%u\ndecode_checks=%llu\nexpected_decode_checks=10752\nparity_checks=%llu\ngeometry_checks=%llu\n",
		correctness_vectors, total_decode_checks(), parity_checks, geometry_checks);
	seq_printf(stream, "outer_runs=%u\nsample_ms=%u\nresult_rows=%u\nvector_rows=%u\nunique_input_vectors=%u\naffinity_cpu=%d\ntimebase=ktime_get_ns_wall\n",
		outer_runs, sample_ms, result_count, exported_vector_rows(), vector_count, bound_cpu);
	seq_puts(stream, "codeword_seed_t4=0xb4c00000\ncodeword_seed_t8=0xb4c00001\ninit_includes_free=1\ndriver_disables_irq_or_preempt=0\nhelper_scope=native-kernel-imports\n");
	for (c = 0; c < CASES; c++) {
		seq_printf(stream, "m13_t%u_ecc_bits=%u\nm13_t%u_ecc_bytes=%u\n",
			cases[c].t, cases[c].ecc_bits, cases[c].t, cases[c].ecc_bytes);
		for (b = 0; b < BACKENDS; b++)
			for (m = 0; m < 2; m++)
				seq_printf(stream, "m13_t%u_%s_%s_checks=%llu\n", cases[c].t,
					backends[b].name, operation_names[OP_PRECOMPUTED + m], decode_checks[c][b][m]);
	}
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(status);

static int results_show(struct seq_file *stream, void *unused)
{
	unsigned int i;

	seq_puts(stream, "round,backend,m,t,len,errors,mode,iterations,ns,timebase,cpu_start,cpu_end,seed,vector_id,errno\n");
	for (i = 0; i < result_count; i++) {
		const struct measurement *r = &results[i];

		seq_printf(stream, "%d,%s,13,%u,512,%d,%s,%llu,%llu,ktime_get_ns_wall,%u,%u,0x%llx,%d,%d\n",
			r->round, backends[r->backend].name, r->t, r->errors,
			operation_names[r->operation], r->iterations, r->ns,
			r->cpu_start, r->cpu_end, r->seed, r->vector_id, r->error);
	}
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(results);

static int vectors_show(struct seq_file *stream, void *unused)
{
	unsigned int i, j, b, mode;

	seq_puts(stream, "vector_id,phase,round,backend,m,t,len,errors,mode,seed,positions,found,returned_positions,locations_equal,restored_codeword_equal,ecc_equal\n");
	for (i = 0; i < vector_count; i++) {
		const struct vector_record *r = &vectors[i];

		if (strcmp(r->phase, "correctness")) {
			seq_printf(stream, "%u,%s,%d,all,13,%u,512,%u,both,0x%llx,", i,
				r->phase, r->round, r->t, r->errors, r->seed);
			for (j = 0; j < r->errors; j++)
				seq_printf(stream, "%s%u", j ? ":" : "", r->positions[j]);
			seq_puts(stream, ",,,,,\n");
			continue;
		}
		for (b = 0; b < BACKENDS; b++)
			for (mode = 0; mode < 2; mode++) {
				const struct decode_evidence *check = &r->checks[b][mode];

				if (!check->checked)
					continue;
				seq_printf(stream, "%u,%s,%d,%s,13,%u,512,%u,%s,0x%llx,",
					i, r->phase, r->round, backends[b].name, r->t, r->errors,
					operation_names[OP_PRECOMPUTED + mode], r->seed);
				for (j = 0; j < r->errors; j++)
					seq_printf(stream, "%s%u", j ? ":" : "", r->positions[j]);
				seq_printf(stream, ",%d,", check->found);
				for (j = 0; j < check->found && j < MAX_T; j++)
					seq_printf(stream, "%s%u", j ? ":" : "", check->returned_positions[j]);
				seq_printf(stream, ",%u,%u,%u\n", check->locations_equal,
					check->restored_codeword_equal, r->ecc_equal[b]);
			}
	}
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(vectors);

static int create_outputs(void)
{
	struct dentry *entry;

	debug_directory = debugfs_create_dir("bch_kernel_bench", NULL);
	if (IS_ERR_OR_NULL(debug_directory))
		return debug_directory ? PTR_ERR(debug_directory) : -ENOMEM;
	entry = debugfs_create_file("status", 0400, debug_directory, NULL, &status_fops);
	if (IS_ERR_OR_NULL(entry))
		return entry ? PTR_ERR(entry) : -ENOMEM;
	entry = debugfs_create_file("results", 0400, debug_directory, NULL, &results_fops);
	if (IS_ERR_OR_NULL(entry))
		return entry ? PTR_ERR(entry) : -ENOMEM;
	entry = debugfs_create_file("vectors", 0400, debug_directory, NULL, &vectors_fops);
	return IS_ERR_OR_NULL(entry) ? (entry ? PTR_ERR(entry) : -ENOMEM) : 0;
}

static void release_outputs(void)
{
	if (!IS_ERR_OR_NULL(debug_directory))
		debugfs_remove_recursive(debug_directory);
	debug_directory = NULL;
	kvfree(results);
	kvfree(vectors);
	results = NULL;
	vectors = NULL;
}

static int __init bch_kernel_bench_init(void)
{
	unsigned int b;
	int error;

	stage = "parameters";
	if (correctness_vectors != VECTOR_TRIALS || !outer_runs || outer_runs > 128 ||
	    !sample_ms || sample_ms > 100) {
		error = -EINVAL;
		goto fail;
	}
	stage = "affinity";
	if (cpumask_weight(current->cpus_ptr) != 1) {
		error = -EINVAL;
		goto fail;
	}
	bound_cpu = cpumask_first(current->cpus_ptr);
	error = check_cpu();
	if (error)
		goto fail;
	pr_info(PREFIX "start measure=%u cpu=%d correctness_vectors=%u outer_runs=%u sample_ms=%u timebase=ktime_get_ns_wall\n",
		measure, bound_cpu, correctness_vectors, outer_runs, sample_ms);
	pr_info(PREFIX "api backend=stock-kernel bch_init=%px bch_free=%px bch_encode=%px bch_decode=%px\n",
		bch_init, bch_free, bch_encode, bch_decode);
	pr_info(PREFIX "api backend=owner-kernel vkso_bch_init=%px vkso_bch_free=%px vkso_bch_encode=%px vkso_bch_decode=%px\n",
		vkso_bch_init, vkso_bch_free, vkso_bch_encode, vkso_bch_decode);
	pr_info(PREFIX "api backend=matched-source-kernel matched_bch_init=%px matched_bch_free=%px matched_bch_encode=%px matched_bch_decode=%px\n",
		matched_bch_init, matched_bch_free, matched_bch_encode, matched_bch_decode);
	stage = "allocation";
	vector_capacity = ERROR_GROUPS * (correctness_vectors + (measure ? outer_runs + 1 : 0));
	result_capacity = measure ? outer_runs * ROWS_PER_ROUND : 0;
	vectors = kvcalloc(vector_capacity, sizeof(*vectors), GFP_KERNEL);
	if (result_capacity)
		results = kvcalloc(result_capacity, sizeof(*results), GFP_KERNEL);
	if (!vectors || (result_capacity && !results)) {
		error = -ENOMEM;
		goto fail;
	}
	stage = "initialization";
	error = initialize_cases();
	if (error)
		goto fail;
	stage = "correctness";
	error = correctness();
	if (error)
		goto fail;
	if (measure) {
		stage = "calibration";
		error = benchmark();
		if (error)
			goto fail;
	}
	error = check_cpu();
	if (error)
		goto fail;
	free_cases();
	stage = "outputs";
	error = create_outputs();
	if (error)
		goto fail;
	passed = true;
	stage = "complete";
	pr_info(PREFIX "status=pass errno=0 decode_checks=%llu parity_checks=%llu vector_rows=%u result_rows=%u cpu=%d\n",
		total_decode_checks(), parity_checks, exported_vector_rows(), result_count, bound_cpu);
	/* Import dependencies keep each original provider referenced for driver life. */
	for (b = 0; b < BACKENDS; b++)
		pr_info(PREFIX "backend=%s complete=1\n", backends[b].name);
	return 0;
fail:
	terminal_errno = error;
	pr_err(PREFIX "status=fail errno=%d stage=%s decode_checks=%llu parity_checks=%llu vector_rows=%u result_rows=%u cpu=%d\n",
		error, stage, total_decode_checks(), parity_checks, exported_vector_rows(), result_count, bound_cpu);
	free_cases();
	release_outputs();
	return error;
}

static void __exit bch_kernel_bench_exit(void)
{
	release_outputs();
}

module_init(bch_kernel_bench_init);
module_exit(bch_kernel_bench_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Full stock/matched-source/actual-owner BCH correctness and optional wall-time benchmark");
