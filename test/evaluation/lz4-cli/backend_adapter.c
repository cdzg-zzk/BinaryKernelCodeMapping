#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* The application uses ordinary independent LZ4 frames, level 1, no dictionary.
 * Frame parsing, checksums, file I/O and CLI behavior stay in upstream code.
 */
typedef int (*kernel_compress_fn)(const char *, char *, int, int, void *);
typedef int (*user_compress_fn)(void *, const char *, char *, int, int, int);
typedef int (*decompress_fn)(const char *, char *, int, int);
static kernel_compress_fn kernel_compress;
static user_compress_fn user_compress;
static decompress_fn decode;
static void *handle, *workmem, *compress_address, *decode_address;
static const char *trace_path;
static int kernel_api, backend_ready;
static uint64_t compress_calls, decompress_calls;

static void fail(const char *message)
{
    fprintf(stderr, "LZ4 application adapter: %s\n", message);
    exit(2);
}

static void *symbol(const char *name)
{
    dlerror();
    void *value = dlsym(handle, name);
    const char *error = dlerror();
    if (!value || error)
        fail(error ? error : "missing symbol");
    return value;
}

__attribute__((constructor)) static void open_backend(void)
{
    const char *path = getenv("VKSO_LZ4_LIBRARY");
    const char *api = getenv("VKSO_LZ4_API");
    if (!path || !api || (strcmp(api, "kernel") && strcmp(api, "user")))
        fail("VKSO_LZ4_LIBRARY and VKSO_LZ4_API=kernel|user are required");
    kernel_api = !strcmp(api, "kernel");
    trace_path = getenv("VKSO_LZ4_TRACE");
    handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!handle)
        fail(dlerror());
    compress_address = symbol(kernel_api ? "vkso_LZ4_compress_default"
                                         : "LZ4_compress_fast_extState");
    decode_address = symbol(kernel_api ? "vkso_LZ4_decompress_safe"
                                       : "LZ4_decompress_safe");
    _Static_assert(sizeof(decode) == sizeof(decode_address), "function pointer size");
    memcpy(&decode, &decode_address, sizeof(decode));
    if (kernel_api) {
        memcpy(&kernel_compress, &compress_address, sizeof(kernel_compress));
        if (posix_memalign(&workmem, 64, 64 * 1024))
            fail("cannot allocate kernel-API work memory");
        memset(workmem, 0, 64 * 1024);
    } else {
        memcpy(&user_compress, &compress_address, sizeof(user_compress));
    }
    backend_ready = 1;
}

__attribute__((destructor)) static void close_backend(void)
{
    if (trace_path && backend_ready) {
        Dl_info compress_info = {0}, decode_info = {0};
        if (!dladdr(compress_address, &compress_info) || !dladdr(decode_address, &decode_info))
            fail("cannot identify selected code addresses");
        FILE *stream = fopen(trace_path, "w");
        if (!stream)
            fail("cannot write call-path diagnostic");
        fprintf(stream, "compress_calls=%llu\ndecompress_calls=%llu\n"
                "compress_address=%p\ndecompress_address=%p\n"
                "compress_dso=%s\ndecompress_dso=%s\n",
                (unsigned long long)compress_calls, (unsigned long long)decompress_calls,
                compress_address, decode_address, compress_info.dli_fname, decode_info.dli_fname);
        fclose(stream);
    }
    free(workmem);
    if (handle)
        dlclose(handle);
}

int __wrap_LZ4_compress_fast_extState_fastReset(void *state, const char *src,
        char *dst, int size, int capacity, int acceleration)
{
    if (acceleration != 1)
        fail("this workflow requires compression level 1");
    if (trace_path)
        ++compress_calls;
    if (kernel_api)
        return kernel_compress(src, dst, size, capacity, workmem);
    return user_compress(state, src, dst, size, capacity, acceleration);
}

int __wrap_LZ4_decompress_safe_usingDict(const char *src, char *dst,
        int compressed, int capacity, const char *dictionary, int dictionary_size)
{
    (void)dictionary;
    if (dictionary_size)
        fail("this workflow requires independent blocks without a dictionary");
    if (trace_path)
        ++decompress_calls;
    return decode(src, dst, compressed, capacity);
}

int __wrap_LZ4_decompress_safe(const char *src, char *dst, int compressed, int capacity)
{
    if (trace_path)
        ++decompress_calls;
    return decode(src, dst, compressed, capacity);
}
