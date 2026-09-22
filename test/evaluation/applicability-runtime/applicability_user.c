/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <sys/stat.h>
#include <limits.h>

static void *ar_allocate(size_t size) { return malloc(size); }
static void ar_release(void *pointer) { free(pointer); }
/* Driver-local explicit callback ABI. Actual119 sort callback entry is already
 * SysV-aligned; this attribute is not evidence of a target alignment failure. */
#define AR_CALLBACK __attribute__((noinline, force_align_arg_pointer))
#include "engine.h"

static void ar_json_string(struct ar_text *text, const char *value)
{
	const unsigned char *p = (const unsigned char *)(value ? value : "");
	ar_append(text, "\"");
	for (; *p; ++p) {
		if (*p == '"' || *p == '\\') ar_append(text, "\\%c", *p);
		else if (*p < 32 || *p >= 127) ar_append(text, "\\u%04x", *p);
		else ar_append(text, "%c", *p);
	}
	ar_append(text, "\"");
}

static int ar_write(const char *directory, const char *name, const struct ar_text *text)
{
	char path[PATH_MAX];
	FILE *stream;
	int result = 0;
	if (snprintf(path, sizeof(path), "%s/%s", directory, name) >= (int)sizeof(path)) return -ENAMETOOLONG;
	stream = fopen(path, "w");
	if (!stream) return -errno;
	if (fwrite(text->data, 1, text->length, stream) != text->length) result = -EIO;
	if (fclose(stream) && !result) result = -EIO;
	return result;
}

static void *ar_load(const char *path, const char *symbol, void **handle, Dl_info *info)
{
	void *address;
	*handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
	if (!*handle) { fprintf(stderr, "dlopen %s: %s\n", path, dlerror()); return NULL; }
	dlerror(); address = dlsym(*handle, symbol);
	if (!address || dlerror() || !dladdr(address, info)) {
		fprintf(stderr, "public symbol lookup failed: %s in %s\n", symbol, path);
		return NULL;
	}
	return address;
}

int main(int argc, char **argv)
{
	const char *hash_path = NULL, *sort_path = NULL, *output = NULL;
	struct ar_text hash = {0}, sort = {0}, status = {0};
	struct ar_stats stats = {0};
	void *hash_handle = NULL, *sort_handle = NULL;
	Dl_info hash_info = {0}, sort_info = {0};
	ar_hash_fn hash_function = NULL;
	ar_sort_fn sort_function = NULL;
	unsigned int roots;
	int i, result = 0, io_result = 0;
	for (i = 1; i < argc; ++i) {
		if (!strcmp(argv[i], "--xxh32") && i + 1 < argc) hash_path = argv[++i];
		else if (!strcmp(argv[i], "--sort") && i + 1 < argc) sort_path = argv[++i];
		else if (!strcmp(argv[i], "--output") && i + 1 < argc) output = argv[++i];
		else { fprintf(stderr, "unknown/incomplete option: %s\n", argv[i]); return 2; }
	}
	if (!output || (!hash_path && !sort_path)) {
		fprintf(stderr, "Usage: %s [--xxh32 DSO] [--sort DSO] --output DIRECTORY\n", argv[0]); return 2;
	}
	if (mkdir(output, 0755)) { perror("mkdir output (must be new)"); return 2; }
	roots = (hash_path ? 1 : 0) | (sort_path ? 2 : 0);
	hash.capacity = AR_HASH_CAPACITY; sort.capacity = AR_SORT_CAPACITY; status.capacity = 16384;
	hash.data = calloc(1, hash.capacity); sort.data = calloc(1, sort.capacity); status.data = calloc(1, status.capacity);
	if (!hash.data || !sort.data || !status.data) { result = -ENOMEM; goto done; }
	ar_headers(&hash, &sort);
	if (hash_path) { hash_function = (ar_hash_fn)ar_load(hash_path, "xxh32", &hash_handle, &hash_info); if (!hash_function) result = -ELIBBAD; }
	if (sort_path) { sort_function = (ar_sort_fn)ar_load(sort_path, "sort", &sort_handle, &sort_info); if (!sort_function) result = -ELIBBAD; }
	if (!result) result = ar_execute(roots, hash_function, sort_function, &hash, &sort, &stats);
	ar_append(&status,
		"{\"schema_version\":1,\"backend\":\"registered-user-api\",\"status\":\"%s\",\"errno\":%d,"
		"\"roots\":%u,\"xxh32_checks\":%u,\"xxh32_kats\":%u,\"sort_checks\":%u,\"failed_case\":%d,"
		"\"cmp_calls\":%llu,\"swap_calls\":%llu,\"api_addresses\":{\"xxh32\":%lu,\"sort\":%lu},"
		"\"callback_addresses\":{\"comparator\":%lu,\"swap\":%lu},"
		"\"callback_swap_size_bytes\":%zu,\"pointer_bytes\":%zu,\"size_t_bytes\":%zu,"
		"\"workload_buffers_released\":true,\"measurement\":false,\"xxh32_path\":",
		result ? "fail" : "pass", result, roots, stats.hash_checks, stats.hash_kats, stats.sort_checks,
		stats.failed_case, (unsigned long long)stats.cmp_calls, (unsigned long long)stats.swap_calls,
		(unsigned long)hash_function, (unsigned long)sort_function, (unsigned long)ar_comparator,
		(unsigned long)ar_swapper, sizeof(int), sizeof(void *), sizeof(size_t));
	ar_json_string(&status, hash_path); ar_append(&status, ",\"sort_path\":"); ar_json_string(&status, sort_path);
	ar_append(&status, ",\"xxh32_dladdr_path\":"); ar_json_string(&status, hash_info.dli_fname);
	ar_append(&status, ",\"sort_dladdr_path\":"); ar_json_string(&status, sort_info.dli_fname);
	ar_append(&status, ",\"xxh32_dladdr_fbase\":%lu,\"sort_dladdr_fbase\":%lu}\n",
		(unsigned long)hash_info.dli_fbase, (unsigned long)sort_info.dli_fbase);
	if (status.error) result = status.error;
	io_result = ar_write(output, "xxh32.csv", &hash);
	if (!io_result) io_result = ar_write(output, "sort.csv", &sort);
	if (!io_result) io_result = ar_write(output, "status.json", &status);
	if (io_result) result = io_result;
done:
	fprintf(stderr, "APPLICABILITY_USER status=%s errno=%d roots=%u xxh32_checks=%u sort_checks=%u\n",
		result ? "fail" : "pass", result, roots, stats.hash_checks, stats.sort_checks);
	if (hash_handle) dlclose(hash_handle);
	if (sort_handle) dlclose(sort_handle);
	free(hash.data); free(sort.data); free(status.data);
	return result ? 1 : 0;
}
