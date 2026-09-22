#define _POSIX_C_SOURCE 200809L
#include <dlfcn.h>
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#include "xz.h"

struct backend {
	const char *name;
	void *handle;
	void (*crc32_init)(void);
	struct xz_dec *(*dec_init)(enum xz_mode, uint32_t);
	enum xz_ret (*dec_run)(struct xz_dec *, struct xz_buf *);
	void (*dec_reset)(struct xz_dec *);
	void (*dec_end)(struct xz_dec *);
};

struct input {
	const char *label;
	uint8_t *plain;
	size_t plain_size;
	uint8_t *compressed;
	size_t compressed_size;
};

static void die(const char *message)
{
	fprintf(stderr, "%s\n", message);
	exit(1);
}

static void *lookup(void *handle, const char *name)
{
	void *symbol;
	const char *error;

	dlerror();
	symbol = dlsym(handle, name);
	error = dlerror();
	if (error != NULL) {
		fprintf(stderr, "missing symbol %s: %s\n", name, error);
		exit(1);
	}
	return symbol;
}

static void load_backend(struct backend *backend, const char *path,
		const char *prefix)
{
	char name[128];

	backend->handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
	if (backend->handle == NULL) {
		fprintf(stderr, "dlopen(%s): %s\n", path, dlerror());
		exit(1);
	}
#define LOAD(member, suffix) do { \
	snprintf(name, sizeof(name), "%s%s", prefix, suffix); \
	*(void **)(&backend->member) = lookup(backend->handle, name); \
} while (0)
	LOAD(crc32_init, "crc32_init");
	LOAD(dec_init, "dec_init");
	LOAD(dec_run, "dec_run");
	LOAD(dec_reset, "dec_reset");
	LOAD(dec_end, "dec_end");
#undef LOAD
	backend->crc32_init();
}

static uint8_t *read_file(const char *path, size_t *size)
{
	struct stat st;
	FILE *file;
	uint8_t *data;

	if (stat(path, &st) != 0 || st.st_size < 0)
		return NULL;
	data = malloc((size_t)st.st_size + 1);
	if (data == NULL)
		return NULL;
	file = fopen(path, "rb");
	if (file == NULL || fread(data, 1, (size_t)st.st_size, file)
			!= (size_t)st.st_size) {
		if (file != NULL)
			fclose(file);
		free(data);
		return NULL;
	}
	fclose(file);
	*size = (size_t)st.st_size;
	return data;
}

static uint64_t elapsed_ns(const struct timespec *start,
		const struct timespec *end)
{
	return (uint64_t)(end->tv_sec - start->tv_sec) * UINT64_C(1000000000)
		+ (uint64_t)(end->tv_nsec - start->tv_nsec);
}

static void decode_once(const struct backend *backend, struct xz_dec *decoder,
		const struct input *input, uint8_t *output, int reset)
{
	struct xz_buf buffer = {
		.in = input->compressed,
		.in_pos = 0,
		.in_size = input->compressed_size,
		.out = output,
		.out_pos = 0,
		.out_size = input->plain_size,
	};
	enum xz_ret result;

	if (reset)
		backend->dec_reset(decoder);
	result = backend->dec_run(decoder, &buffer);
	if (result != XZ_STREAM_END || buffer.in_pos != input->compressed_size
			|| buffer.out_pos != input->plain_size) {
		fprintf(stderr, "%s/%s: decode failed ret=%d in=%zu/%zu out=%zu/%zu\n",
			backend->name, input->label, result,
			buffer.in_pos, input->compressed_size,
			buffer.out_pos, input->plain_size);
		exit(1);
	}
}

static int guard_is_intact(const uint8_t *guard, size_t size)
{
	size_t i;

	for (i = 0; i < size; ++i)
		if (guard[i] != 0xA5)
			return 0;
	return 1;
}

static void run_case(const struct backend *backend, const struct input *input,
		unsigned int outer_run, unsigned int repeats)
{
	static const size_t guard_size = 64;
	struct xz_dec *decoder;
	uint8_t *allocation;
	uint8_t *output;
	struct timespec start;
	struct timespec end;
	uint64_t ns;
	unsigned int i;

	allocation = malloc(input->plain_size + guard_size * 2);
	if (allocation == NULL)
		die("output allocation failed");
	memset(allocation, 0xA5, input->plain_size + guard_size * 2);
	output = allocation + guard_size;
	decoder = backend->dec_init(XZ_SINGLE, 0);
	if (decoder == NULL)
		die("xz_dec_init failed");

	/* Untimed correctness pass and warm-up. */
	decode_once(backend, decoder, input, output, 0);
	if (memcmp(output, input->plain, input->plain_size) != 0)
		die("warm-up output mismatch");

	clock_gettime(CLOCK_MONOTONIC_RAW, &start);
	for (i = 0; i < repeats; ++i)
		decode_once(backend, decoder, input, output, 1);
	clock_gettime(CLOCK_MONOTONIC_RAW, &end);
	ns = elapsed_ns(&start, &end);

	if (memcmp(output, input->plain, input->plain_size) != 0
			|| !guard_is_intact(allocation, guard_size)
			|| !guard_is_intact(output + input->plain_size, guard_size))
		die("timed output or guard mismatch");

	printf("%s,%s,%u,%zu,%zu,%u,%" PRIu64 ",%.6f,%.6f\n",
		backend->name, input->label, outer_run,
		input->plain_size, input->compressed_size, repeats, ns,
		(double)ns / repeats / 1.0e6,
		((double)input->plain_size * repeats / (1024.0 * 1024.0))
			/ ((double)ns / 1.0e9));
	backend->dec_end(decoder);
	free(allocation);
}

int main(int argc, char **argv)
{
	const char *native_path = NULL;
	const char *adapted_path = NULL;
	const char *kernel_path = NULL;
	unsigned int repeats = 20;
	unsigned int outer_runs = 5;
	struct backend backends[3] = {
		{.name = "native"},
		{.name = "kernel-vkso"},
		{.name = "adapted-dso"},
	};
	struct input *inputs;
	int first_pair = 0;
	int pair_count;
	unsigned int run;
	int i;
	unsigned int backend_count = 2;

	for (i = 1; i < argc; ++i) {
		if (strcmp(argv[i], "--native") == 0 && i + 1 < argc)
			native_path = argv[++i];
		else if (strcmp(argv[i], "--adapted") == 0 && i + 1 < argc)
			adapted_path = argv[++i];
		else if (strcmp(argv[i], "--kernel") == 0 && i + 1 < argc)
			kernel_path = argv[++i];
		else if (strcmp(argv[i], "--repeats") == 0 && i + 1 < argc)
			repeats = (unsigned int)strtoul(argv[++i], NULL, 10);
		else if (strcmp(argv[i], "--outer-runs") == 0 && i + 1 < argc)
			outer_runs = (unsigned int)strtoul(argv[++i], NULL, 10);
		else if (strcmp(argv[i], "--") == 0) {
			first_pair = i + 1;
			break;
		} else
			die("invalid arguments");
	}
	if (native_path == NULL || kernel_path == NULL || first_pair == 0
			|| repeats == 0 || outer_runs == 0
			|| (argc - first_pair) == 0 || (argc - first_pair) % 3 != 0)
		die("usage: xz-bench --native DSO --kernel DSO [--repeats N] "
			"[--outer-runs N] -- LABEL ORIGINAL INPUT.xz [...]");

	pair_count = (argc - first_pair) / 3;
	inputs = calloc((size_t)pair_count, sizeof(*inputs));
	if (inputs == NULL)
		die("input metadata allocation failed");
	for (i = 0; i < pair_count; ++i) {
		inputs[i].label = argv[first_pair + i * 3];
		inputs[i].plain = read_file(argv[first_pair + i * 3 + 1],
			&inputs[i].plain_size);
		inputs[i].compressed = read_file(argv[first_pair + i * 3 + 2],
			&inputs[i].compressed_size);
		if (inputs[i].plain == NULL || inputs[i].compressed == NULL) {
			fprintf(stderr, "cannot read input %s: %s\n",
				inputs[i].label, strerror(errno));
			return 1;
		}
	}

	load_backend(&backends[0], native_path, "xz_");
	load_backend(&backends[1], kernel_path, "vkso_xz_");
	if (adapted_path) {
		backends[0].name = "native-dso";
		load_backend(&backends[2], adapted_path, "xz_");
		backend_count = 3;
	}
	puts("backend,case,outer_run,bytes,compressed_bytes,repeats,elapsed_ns,mean_ms,throughput_mib_s");
	for (run = 0; run < outer_runs; ++run) {
		int input_index;
		for (input_index = 0; input_index < pair_count; ++input_index) {
			unsigned int position;
			for (position = 0; position < backend_count; ++position) {
				unsigned int backend_index = (position + run) % backend_count;
				run_case(&backends[backend_index], &inputs[input_index],
					run, repeats);
			}
		}
	}
	for (i = 0; i < pair_count; ++i) {
		free(inputs[i].compressed);
		free(inputs[i].plain);
	}
	free(inputs);
	dlclose(backends[1].handle);
	dlclose(backends[0].handle);
	if (adapted_path)
		dlclose(backends[2].handle);
	return 0;
}
