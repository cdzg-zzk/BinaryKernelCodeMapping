#define _GNU_SOURCE

#include "official_backend_adapter.h"

#include <dlfcn.h>
#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define KERNEL_WORKMEM_SIZE (64u * 1024u)

typedef int (*user_compress_fn)(void *, const char *, char *, int, int, int);
typedef int (*kernel_compress_fn)(const char *, char *, int, int, void *);
typedef int (*decompress_fn)(const char *, char *, int, int);
typedef int (*state_size_fn)(void);

static void *backend_handle;
static void *backend_workmem;
static user_compress_fn user_compress;
static kernel_compress_fn kernel_compress;
static decompress_fn backend_decompress;
static int backend_uses_kernel_api;

static int
load_symbol(const char *name, void *target, size_t target_size)
{
	void *symbol;
	const char *error;

	dlerror();
	symbol = dlsym(backend_handle, name);
	error = dlerror();
	if (symbol == NULL || error != NULL) {
		fprintf(stderr, "dlsym(%s): %s\n", name,
			error != NULL ? error : "null symbol");
		return -1;
	}
	if (target_size != sizeof(symbol)) {
		fprintf(stderr, "incompatible function pointer size for %s\n", name);
		return -1;
	}
	memcpy(target, &symbol, sizeof(symbol));
	return 0;
}

int
official_backend_open(const char *path, int kernel_api)
{
	state_size_fn state_size = NULL;
	size_t workmem_size;
	int error;

	backend_uses_kernel_api = kernel_api;
	backend_handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
	if (backend_handle == NULL) {
		fprintf(stderr, "dlopen(%s): %s\n", path, dlerror());
		return -1;
	}

	if (kernel_api) {
		if (load_symbol("vkso_LZ4_compress_default", &kernel_compress,
				sizeof(kernel_compress)) != 0
			|| load_symbol("vkso_LZ4_decompress_safe", &backend_decompress,
				sizeof(backend_decompress)) != 0)
			goto fail;
		workmem_size = KERNEL_WORKMEM_SIZE;
	} else {
		if (load_symbol("LZ4_compress_fast_extState", &user_compress,
				sizeof(user_compress)) != 0
			|| load_symbol("LZ4_decompress_safe", &backend_decompress,
				sizeof(backend_decompress)) != 0
			|| load_symbol("LZ4_sizeofState", &state_size,
				sizeof(state_size)) != 0)
			goto fail;
		workmem_size = (size_t)state_size();
	}

	error = posix_memalign(&backend_workmem, 64, workmem_size);
	if (error != 0) {
		errno = error;
		perror("posix_memalign backend state");
		goto fail;
	}
	memset(backend_workmem, 0, workmem_size);
	return 0;

fail:
	dlclose(backend_handle);
	backend_handle = NULL;
	return -1;
}

void
official_backend_close(void)
{
	free(backend_workmem);
	backend_workmem = NULL;
	if (backend_handle != NULL)
		dlclose(backend_handle);
	backend_handle = NULL;
}

int
__wrap_LZ4_compress_fast(const char *source, char *destination,
		int source_size, int destination_capacity, int acceleration)
{
	if (backend_uses_kernel_api) {
		if (acceleration != 1)
			return 0;
		return kernel_compress(source, destination, source_size,
			destination_capacity, backend_workmem);
	}
	return user_compress(backend_workmem, source, destination, source_size,
		destination_capacity, acceleration);
}

int
__wrap_LZ4_decompress_safe_usingDict(const char *source, char *destination,
		int compressed_size, int destination_capacity,
		const char *dictionary, int dictionary_size)
{
	if (dictionary != NULL || dictionary_size != 0)
		return -1;
	return backend_decompress(source, destination, compressed_size,
		destination_capacity);
}
