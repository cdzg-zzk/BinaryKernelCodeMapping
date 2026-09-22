#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define BACKEND_COUNT 3
#define CASE_COUNT 2
#define MAX_T 8
#define MODE_COUNT 3

/* Opt-in diagnostic: share the historical user precomputed vectors across
 * both decode interfaces and the kernel driver. Legacy measurements retain
 * their original seed rule and timing protocol. */
static bool aligned_inputs;
static FILE *input_evidence;

enum operation_mode {
	MODE_ENCODE = 0,
	MODE_DECODE_PRECOMPUTED = 1,
	MODE_DECODE_FULL = 2,
};

/* Public prefix shared by the 2017 standalone and Linux 5.15 structures. */
struct bch_public {
	unsigned int m;
	unsigned int n;
	unsigned int t;
	unsigned int ecc_bits;
	unsigned int ecc_bytes;
};

typedef void *(*init4_fn)(int, int, unsigned int, bool);
typedef void *(*init3_fn)(int, int, unsigned int);
typedef void (*free_fn)(void *);
typedef void (*encode_fn)(void *, const uint8_t *, unsigned int, uint8_t *);
typedef int (*decode_fn)(void *, const uint8_t *, unsigned int,
			 const uint8_t *, const uint8_t *,
			 const unsigned int *, unsigned int *);

struct backend {
	const char *name;
	const char *path;
	bool standalone_api;
	void *handle;
	init4_fn init4;
	init3_fn init3;
	free_fn free_control;
	encode_fn encode;
	decode_fn decode;
};

struct bench_case {
	int m;
	int t;
	int len;
	unsigned int ecc_bits;
	unsigned int ecc_bytes;
	uint8_t *codeword;
	void *controls[BACKEND_COUNT];
};

struct op_context {
	struct backend *backend;
	void *control;
	struct bench_case *test;
	enum operation_mode mode;
	int errors;
	uint8_t *work;
	uint8_t *difference;
	unsigned int *errloc;
};

static volatile uint64_t result_sink;

static void die(const char *message)
{
	fprintf(stderr, "error: %s\n", message);
	exit(EXIT_FAILURE);
}

static void *xcalloc(size_t count, size_t size)
{
	void *ptr = calloc(count, size);

	if (!ptr)
		die("out of memory");
	return ptr;
}

static void *load_symbol(void *handle, const char *name)
{
	void *symbol;
	const char *error;

	dlerror();
	symbol = dlsym(handle, name);
	error = dlerror();
	if (error) {
		fprintf(stderr, "dlsym(%s): %s\n", name, error);
		exit(EXIT_FAILURE);
	}
	return symbol;
}

static void load_backend(struct backend *backend)
{
	backend->handle = dlopen(backend->path, RTLD_NOW | RTLD_LOCAL);
	if (!backend->handle) {
		fprintf(stderr, "dlopen(%s): %s\n", backend->path, dlerror());
		exit(EXIT_FAILURE);
	}

	if (backend->standalone_api) {
		backend->init3 = (init3_fn)load_symbol(backend->handle, "init_bch");
		backend->free_control =
			(free_fn)load_symbol(backend->handle, "free_bch");
		backend->encode =
			(encode_fn)load_symbol(backend->handle, "encode_bch");
		backend->decode =
			(decode_fn)load_symbol(backend->handle, "decode_bch");
	} else {
		const bool vkso = strcmp(backend->name, "kernel-vkso") == 0;
		const char *init_name = vkso ? "vkso_bch_init" : "bch_init";
		const char *free_name = vkso ? "vkso_bch_free" : "bch_free";
		const char *encode_name = vkso ? "vkso_bch_encode" : "bch_encode";
		const char *decode_name = vkso ? "vkso_bch_decode" : "bch_decode";

		backend->init4 = (init4_fn)load_symbol(backend->handle, init_name);
		backend->free_control =
			(free_fn)load_symbol(backend->handle, free_name);
		backend->encode =
			(encode_fn)load_symbol(backend->handle, encode_name);
		backend->decode =
			(decode_fn)load_symbol(backend->handle, decode_name);
	}
}

static void *new_control(struct backend *backend, int m, int t)
{
	void *control;

	if (backend->standalone_api)
		control = backend->init3(m, t, 0);
	else
		control = backend->init4(m, t, 0, false);
	if (!control) {
		fprintf(stderr, "%s: initialization failed for m=%d t=%d\n",
			backend->name, m, t);
		exit(EXIT_FAILURE);
	}
	return control;
}

static uint64_t prng_next(uint64_t *state)
{
	uint64_t value = *state;

	value ^= value >> 12;
	value ^= value << 25;
	value ^= value >> 27;
	*state = value;
	return value * UINT64_C(2685821657736338717);
}

static unsigned int reverse_bit_in_byte(unsigned int bit)
{
	return (bit & ~7U) | (7U - (bit & 7U));
}

static void generate_error_vector(unsigned int *vector, int count,
				  unsigned int nbits, uint64_t seed)
{
	int i;

	for (i = 0; i < count; ++i) {
		unsigned int candidate;
		bool duplicate;
		int j;

		do {
			candidate = (unsigned int)(prng_next(&seed) % nbits);
			candidate = reverse_bit_in_byte(candidate);
			duplicate = candidate >= nbits;
			for (j = 0; !duplicate && j < i; ++j)
				duplicate = vector[j] == candidate;
		} while (duplicate);
		vector[i] = candidate;
	}
}

static void flip_bits(uint8_t *buffer, const unsigned int *vector, int count)
{
	int i;

	for (i = 0; i < count; ++i)
		buffer[vector[i] / 8] ^= (uint8_t)(1U << (vector[i] & 7));
}

static bool same_locations(const unsigned int *expected, int expected_count,
			   const unsigned int *actual, int actual_count)
{
	int i;

	if (expected_count != actual_count)
		return false;
	for (i = 0; i < expected_count; ++i) {
		int j;
		bool found = false;

		for (j = 0; j < actual_count; ++j) {
			if (expected[i] == actual[j]) {
				found = true;
				break;
			}
		}
		if (!found)
			return false;
	}
	return true;
}

static void prepare_decode_context(struct op_context *context,
				   const unsigned int *vector)
{
	struct bench_case *test = context->test;
	size_t codeword_bytes = (size_t)test->len + test->ecc_bytes;
	unsigned int i;

	context->work = xcalloc(codeword_bytes, 1);
	context->difference = xcalloc(test->ecc_bytes, 1);
	context->errloc = xcalloc((size_t)test->t, sizeof(*context->errloc));
	memcpy(context->work, test->codeword, codeword_bytes);
	flip_bits(context->work, vector, context->errors);

	if (context->mode == MODE_DECODE_PRECOMPUTED) {
		context->backend->encode(context->control, context->work,
					 test->len, context->difference);
		for (i = 0; i < test->ecc_bytes; ++i)
			context->difference[i] ^= context->work[test->len + i];
	}
}

static void free_decode_context(struct op_context *context)
{
	free(context->work);
	free(context->difference);
	free(context->errloc);
	context->work = NULL;
	context->difference = NULL;
	context->errloc = NULL;
}

static void record_input(int outer, struct op_context *context,
			 const unsigned int *positions)
{
	unsigned int i;
	if (!input_evidence || context->mode != MODE_DECODE_PRECOMPUTED)
		return;
	fprintf(input_evidence, "%d,%d,%d,%s,", outer, context->test->t,
		context->errors, context->backend->name);
	for (i = 0; i < (unsigned int)context->errors; i++)
		fprintf(input_evidence, "%s%u", i ? ":" : "", positions[i]);
	fputc(',', input_evidence);
	for (i = 0; i < (unsigned int)context->test->len + context->test->ecc_bytes; i++)
		fprintf(input_evidence, "%02x", context->work[i]);
	fputc(',', input_evidence);
	for (i = 0; i < context->test->ecc_bytes; i++)
		fprintf(input_evidence, "%02x", context->difference[i]);
	fputc('\n', input_evidence);
}

static int decode_once(struct op_context *context)
{
	if (context->mode == MODE_DECODE_PRECOMPUTED) {
		return context->backend->decode(context->control, NULL,
			context->test->len, NULL, context->difference, NULL,
			context->errloc);
	}
	return context->backend->decode(context->control, context->work,
		context->test->len, context->work + context->test->len,
		NULL, NULL, context->errloc);
}

static void verify_decode(struct op_context *context,
			  const unsigned int *vector)
{
	int found = decode_once(context);

	if (!same_locations(vector, context->errors, context->errloc, found)) {
		int i;

		fprintf(stderr, "%s m=%d t=%d mode=%d errors=%d returned=%d\n",
			context->backend->name, context->test->m, context->test->t,
			context->mode, context->errors, found);
		fprintf(stderr, "expected:");
		for (i = 0; i < context->errors; ++i)
			fprintf(stderr, " %u", vector[i]);
		fprintf(stderr, "\nactual:");
		for (i = 0; i < found && i < context->test->t; ++i)
			fprintf(stderr, " %u", context->errloc[i]);
		fprintf(stderr, "\n");
		die("BCH error-location correctness failure");
	}

	flip_bits(context->work, context->errloc, found);
	if (memcmp(context->work, context->test->codeword,
		   (size_t)context->test->len + context->test->ecc_bytes) != 0)
		die("BCH returned locations do not restore the codeword");
	flip_bits(context->work, context->errloc, found);
}

static uint64_t elapsed_ns(const struct timespec *start,
			   const struct timespec *end)
{
	return (uint64_t)(end->tv_sec - start->tv_sec) * UINT64_C(1000000000) +
		(uint64_t)(end->tv_nsec - start->tv_nsec);
}

static uint64_t run_context(struct op_context *context, uint64_t iterations)
{
	uint64_t i;
	int value = 0;

	if (context->mode == MODE_ENCODE) {
		for (i = 0; i < iterations; ++i)
			context->backend->encode(context->control,
				context->test->codeword, context->test->len, NULL);
	} else {
		for (i = 0; i < iterations; ++i)
			value += decode_once(context);
	}
	result_sink += (uint64_t)value + iterations;
	return iterations;
}

static uint64_t measure_context(struct op_context *context, uint64_t iterations)
{
	struct timespec start;
	struct timespec end;

	if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &start) != 0)
		die("clock_gettime start failed");
	run_context(context, iterations);
	if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &end) != 0)
		die("clock_gettime end failed");
	return elapsed_ns(&start, &end);
}

static uint64_t calibrate_context(struct op_context *context,
				  uint64_t target_ns)
{
	uint64_t iterations = 1;
	uint64_t duration;

	do {
		duration = measure_context(context, iterations);
		if (duration >= target_ns / 8 || iterations >= UINT64_C(1000000))
			break;
		iterations *= 2;
	} while (true);

	if (duration == 0)
		return iterations;
	iterations = (uint64_t)((long double)iterations * target_ns / duration);
	if (iterations < 1)
		iterations = 1;
	if (iterations > UINT64_C(10000000))
		iterations = UINT64_C(10000000);
	return iterations;
}

static uint64_t measure_init(struct backend *backend, int m, int t,
			     uint64_t iterations)
{
	struct timespec start;
	struct timespec end;
	uint64_t i;

	clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &start);
	for (i = 0; i < iterations; ++i) {
		void *control = new_control(backend, m, t);
		backend->free_control(control);
	}
	clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &end);
	result_sink += iterations;
	return elapsed_ns(&start, &end);
}

static uint64_t calibrate_init(struct backend *backend, int m, int t,
			       uint64_t target_ns)
{
	uint64_t iterations = 1;
	uint64_t duration;

	do {
		duration = measure_init(backend, m, t, iterations);
		if (duration >= target_ns / 4 || iterations >= 1024)
			break;
		iterations *= 2;
	} while (true);
	if (duration == 0)
		return iterations;
	iterations = (uint64_t)((long double)iterations * target_ns / duration);
	return iterations ? iterations : 1;
}

static const char *mode_name(enum operation_mode mode)
{
	switch (mode) {
	case MODE_ENCODE:
		return "encode";
	case MODE_DECODE_PRECOMPUTED:
		return "decode-precomputed";
	case MODE_DECODE_FULL:
		return "decode-full";
	}
	return "unknown";
}

static void initialize_cases(struct backend *backends,
			     struct bench_case *cases)
{
	const int parameters[CASE_COUNT][2] = {{13, 4}, {13, 8}};
	int case_index;

	for (case_index = 0; case_index < CASE_COUNT; ++case_index) {
		struct bench_case *test = &cases[case_index];
		uint64_t seed = UINT64_C(0xb4c00000) + (uint64_t)case_index;
		uint8_t *reference_ecc = NULL;
		int backend_index;
		int i;

		test->m = parameters[case_index][0];
		test->t = parameters[case_index][1];
		/* This is the exact length rule used by the author's tu_bench.c. */
		test->len = (1 << (test->m - 1)) / 8;

		for (backend_index = 0; backend_index < BACKEND_COUNT;
		     ++backend_index) {
			struct bch_public *public;

			test->controls[backend_index] =
				new_control(&backends[backend_index], test->m, test->t);
			public = (struct bch_public *)test->controls[backend_index];
			if (backend_index == 0) {
				test->ecc_bits = public->ecc_bits;
				test->ecc_bytes = public->ecc_bytes;
				test->codeword = xcalloc((size_t)test->len +
							 test->ecc_bytes, 1);
				reference_ecc = test->codeword + test->len;
				for (i = 0; i < test->len; ++i)
					test->codeword[i] = (uint8_t)prng_next(&seed);
			} else if (public->ecc_bits != test->ecc_bits ||
				   public->ecc_bytes != test->ecc_bytes) {
				die("backend BCH geometry differs");
			}

			if (backend_index == 0) {
				backends[backend_index].encode(test->controls[backend_index],
					test->codeword, test->len, reference_ecc);
			} else {
				uint8_t *ecc = xcalloc(test->ecc_bytes, 1);

				backends[backend_index].encode(test->controls[backend_index],
					test->codeword, test->len, ecc);
				if (memcmp(reference_ecc, ecc, test->ecc_bytes) != 0)
					die("backend parity bytes differ");
				free(ecc);
			}
		}
	}
}

static void run_correctness(struct backend *backends,
			    struct bench_case *cases, int vectors)
{
	int case_index;

	for (case_index = 0; case_index < CASE_COUNT; ++case_index) {
		struct bench_case *test = &cases[case_index];
		int trial;

		for (trial = 0; trial < vectors; ++trial) {
			int errors;

			for (errors = 0; errors <= test->t; ++errors) {
				unsigned int vector[MAX_T];
				uint64_t seed = UINT64_C(0x63c5a17e9b) ^
					((uint64_t)case_index << 48) ^
					((uint64_t)trial << 16) ^ (uint64_t)errors;
				int backend_index;

				generate_error_vector(vector, errors,
					8U * (unsigned int)test->len + test->ecc_bits,
					seed);
				for (backend_index = 0; backend_index < BACKEND_COUNT;
				     ++backend_index) {
					enum operation_mode mode;

					for (mode = MODE_DECODE_PRECOMPUTED;
					     mode <= MODE_DECODE_FULL; ++mode) {
						struct op_context context = {
							.backend = &backends[backend_index],
							.control = test->controls[backend_index],
							.test = test,
							.mode = mode,
							.errors = errors,
						};

						prepare_decode_context(&context, vector);
						verify_decode(&context, vector);
						free_decode_context(&context);
					}
				}
			}
		}
		fprintf(stderr, "correctness: m=%d t=%d vectors=%d backends=3 ok\n",
			test->m, test->t, vectors);
	}
}

static void write_row(FILE *output, int outer, const struct bench_case *test,
		      int errors, const char *mode, const struct backend *backend,
		      uint64_t iterations, uint64_t duration)
{
	double ns_per_op = (double)duration / (double)iterations;
	double mbps = test->len ? (double)test->len * 8000.0 / ns_per_op : 0.0;

	fprintf(output,
		"%d,%d,%d,%d,%d,%s,%s,%" PRIu64 ",%" PRIu64
		",%.6f,%.6f\n",
		outer, test->m, test->t, test->len, errors, mode, backend->name,
		iterations, duration, ns_per_op, mbps);
	fflush(output);
}

static void run_benchmark(FILE *output, struct backend *backends,
			  struct bench_case *cases, int outer_runs,
			  uint64_t target_ns)
{
	uint64_t iterations[BACKEND_COUNT][CASE_COUNT][MODE_COUNT][MAX_T + 1] = {0};
	uint64_t init_iterations[BACKEND_COUNT][CASE_COUNT] = {0};
	int case_index;

	for (case_index = 0; case_index < CASE_COUNT; ++case_index) {
		struct bench_case *test = &cases[case_index];
		int backend_index;

		for (backend_index = 0; backend_index < BACKEND_COUNT; ++backend_index) {
			struct op_context encode_context = {
				.backend = &backends[backend_index],
				.control = test->controls[backend_index],
				.test = test,
				.mode = MODE_ENCODE,
			};
			int errors;

			iterations[backend_index][case_index][MODE_ENCODE][0] =
				calibrate_context(&encode_context, target_ns);
			init_iterations[backend_index][case_index] =
				calibrate_init(&backends[backend_index], test->m,
					       test->t, target_ns);

			for (errors = 0; errors <= test->t; ++errors) {
				unsigned int vector[MAX_T];
				enum operation_mode mode;

				generate_error_vector(vector, errors,
					8U * (unsigned int)test->len + test->ecc_bits,
					UINT64_C(0xca11b4a7) ^
					((uint64_t)case_index << 32) ^
					(uint64_t)errors);
				for (mode = MODE_DECODE_PRECOMPUTED;
				     mode <= MODE_DECODE_FULL; ++mode) {
					struct op_context context = {
						.backend = &backends[backend_index],
						.control = test->controls[backend_index],
						.test = test,
						.mode = mode,
						.errors = errors,
					};

					prepare_decode_context(&context, vector);
					iterations[backend_index][case_index][mode][errors] =
						calibrate_context(&context, target_ns);
					free_decode_context(&context);
				}
			}
		}
	}

	fprintf(output,
		"outer,m,t,len,errors,operation,backend,iterations,total_ns,ns_per_op,mbit_per_second\n");

	for (int outer = 0; outer < outer_runs; ++outer) {
		for (case_index = 0; case_index < CASE_COUNT; ++case_index) {
			struct bench_case *test = &cases[case_index];
			int position;

			for (position = 0; position < BACKEND_COUNT; ++position) {
				int backend_index = (position + outer + case_index) % BACKEND_COUNT;
				uint64_t count = init_iterations[backend_index][case_index];
				uint64_t duration = measure_init(&backends[backend_index],
					test->m, test->t, count);

				write_row(output, outer, test, -1, "init",
					  &backends[backend_index], count, duration);
			}

			for (int mode_value = MODE_ENCODE;
			     mode_value <= MODE_DECODE_FULL; ++mode_value) {
				enum operation_mode mode = (enum operation_mode)mode_value;
				int error_limit = mode == MODE_ENCODE ? 0 : test->t;

				for (int errors = 0; errors <= error_limit; ++errors) {
					unsigned int vector[MAX_T];
					uint64_t seed = UINT64_C(0x9e3779b97f4a7c15) ^
						((uint64_t)outer << 40) ^
						((uint64_t)case_index << 32) ^
						((uint64_t)(aligned_inputs ? MODE_DECODE_PRECOMPUTED : mode) << 24) ^
						(uint64_t)errors;

					generate_error_vector(vector, errors,
						8U * (unsigned int)test->len + test->ecc_bits,
						seed);
					for (position = 0; position < BACKEND_COUNT; ++position) {
						int backend_index = (position + outer + case_index +
							mode + errors) % BACKEND_COUNT;
						struct op_context context = {
							.backend = &backends[backend_index],
							.control = test->controls[backend_index],
							.test = test,
							.mode = mode,
							.errors = errors,
						};
						uint64_t count = iterations[backend_index][case_index]
							[mode][errors];
						uint64_t duration;

						if (mode != MODE_ENCODE)
							prepare_decode_context(&context, vector);
						record_input(outer, &context, vector);
						run_context(&context, count < 32 ? count : 32);
						duration = measure_context(&context, count);
						write_row(output, outer, test, errors,
							  mode_name(mode), &backends[backend_index],
							  count, duration);
						if (mode != MODE_ENCODE)
							free_decode_context(&context);
					}
				}
			}
		}
	}
}

static void cleanup(struct backend *backends, struct bench_case *cases)
{
	int case_index;

	for (case_index = 0; case_index < CASE_COUNT; ++case_index) {
		int backend_index;

		for (backend_index = 0; backend_index < BACKEND_COUNT; ++backend_index)
			backends[backend_index].free_control(
				cases[case_index].controls[backend_index]);
		free(cases[case_index].codeword);
	}
	for (int i = 0; i < BACKEND_COUNT; ++i)
		dlclose(backends[i].handle);
}

static const char *next_argument(int argc, char **argv, int *index)
{
	if (++(*index) >= argc)
		die("missing option value");
	return argv[*index];
}

int main(int argc, char **argv)
{
	struct backend backends[BACKEND_COUNT] = {
		{.name = "kernel-vkso"},
		{.name = "kernel-native"},
		{.name = "author-standalone", .standalone_api = true},
	};
	struct bench_case cases[CASE_COUNT] = {0};
	const char *output_path = NULL;
	int outer_runs = 9;
	int correctness_vectors = 128;
	double sample_ms = 5.0;
	bool correctness_only = false;
	FILE *output;
	int i;

	for (i = 1; i < argc; ++i) {
		if (strcmp(argv[i], "--kernel") == 0)
			backends[0].path = next_argument(argc, argv, &i);
		else if (strcmp(argv[i], "--kernel-native") == 0)
			backends[1].path = next_argument(argc, argv, &i);
		else if (strcmp(argv[i], "--standalone") == 0)
			backends[2].path = next_argument(argc, argv, &i);
		else if (strcmp(argv[i], "--adapted") == 0) {
			backends[1].name = "adapted-dso";
			backends[1].path = next_argument(argc, argv, &i);
		} else if (strcmp(argv[i], "--native") == 0) {
			backends[2].name = "native-dso";
			backends[2].standalone_api = false;
			backends[2].path = next_argument(argc, argv, &i);
		}
		else if (strcmp(argv[i], "--output") == 0)
			output_path = next_argument(argc, argv, &i);
		else if (strcmp(argv[i], "--outer") == 0)
			outer_runs = atoi(next_argument(argc, argv, &i));
		else if (strcmp(argv[i], "--sample-ms") == 0)
			sample_ms = atof(next_argument(argc, argv, &i));
		else if (strcmp(argv[i], "--correctness-vectors") == 0)
			correctness_vectors = atoi(next_argument(argc, argv, &i));
		else if (strcmp(argv[i], "--correctness-only") == 0)
			correctness_only = true;
		else if (strcmp(argv[i], "--aligned-inputs") == 0)
			aligned_inputs = true;
		else
			die("unknown command-line option");
	}

	for (i = 0; i < BACKEND_COUNT; ++i) {
		if (!backends[i].path)
			die("all three backend paths are required");
		load_backend(&backends[i]);
	}
	initialize_cases(backends, cases);
	run_correctness(backends, cases, correctness_vectors);

	if (!correctness_only) {
		if (!output_path)
			die("--output is required for benchmark mode");
		output = fopen(output_path, "w");
		if (!output) {
			fprintf(stderr, "fopen(%s): %s\n", output_path,
				strerror(errno));
			return EXIT_FAILURE;
		}
		if (aligned_inputs) {
			char *path;
			if (asprintf(&path, "%s.inputs.csv", output_path) < 0)
				die("input evidence path allocation failed");
			input_evidence = fopen(path, "w");
			free(path);
			if (!input_evidence)
				die("input evidence open failed");
			fputs("round,t,errors,backend,positions,work_hex,ecc_difference_hex\n", input_evidence);
		}
		run_benchmark(output, backends, cases, outer_runs,
			      (uint64_t)(sample_ms * 1000000.0));
		if (input_evidence)
			fclose(input_evidence);
		fclose(output);
	}

	cleanup(backends, cases);
	fprintf(stderr, "BCH evaluation completed; sink=%" PRIu64 "\n",
		result_sink);
	return EXIT_SUCCESS;
}
