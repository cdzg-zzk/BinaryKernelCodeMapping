#include <dlfcn.h>
#include <signal.h>
#include <stdio.h>
#include <setjmp.h>
#include <stdlib.h>
#include <string.h>

#include "deflate_types.h"

#define LIB_PATH "/home/zzk/BinaryKernelCodeMapping/test/test_zlib/libmz_zlib_deflate.so"
#define Z_NO_FLUSH 0
#define Z_PARTIAL_FLUSH 1
#define Z_PACKET_FLUSH 2
#define Z_SYNC_FLUSH 3
#define Z_FULL_FLUSH 4
#define Z_FINISH 5
#define Z_OK 0
#define Z_STREAM_END 1
#define Z_STREAM_ERROR (-2)
#define Z_BUF_ERROR (-5)
#define Z_DEFLATED 8
#define Z_FILTERED 1
#define Z_HUFFMAN_ONLY 2
#define Z_DEFAULT_STRATEGY 0
#define Z_DEFAULT_COMPRESSION (-1)
#define INIT_STATE 42
#define BUSY_STATE 113
#define TEST_WINDOW_BITS 15
#define TEST_MEM_LEVEL 8
#define TEST_WORKSPACE_SIZE (1U << 20)

typedef int (*mz_zlib_deflate_fn)(z_streamp strm, int flush);
typedef int (*mz_zlib_deflateInit2_fn)(z_streamp strm, int level, int method,
                                       int windowBits, int memLevel, int strategy);
typedef unsigned long (*zlib_compress_bound_fn)(unsigned long source_len);
typedef int (*zlib_uncompress_fn)(Byte *dest, unsigned long *dest_len,
                                  const Byte *source, unsigned long source_len);

struct fake_deflate_state {
    z_streamp strm;
    int status;
    unsigned char *pending_buf;
    unsigned long pending_buf_size;
    unsigned char *pending_out;
    int pending;
    int noheader;
    unsigned char data_type;
    unsigned char method;
    int last_flush;
    unsigned int w_size;
    unsigned int w_bits;
    unsigned int w_mask;
    unsigned char *window;
    unsigned long window_size;
    unsigned short *prev;
    unsigned short *head;
    unsigned int ins_h;
    unsigned int hash_size;
    unsigned int hash_bits;
    unsigned int hash_mask;
    unsigned int hash_shift;
    long block_start;
    unsigned int match_length;
    unsigned int prev_match;
    int match_available;
    unsigned int strstart;
    unsigned int match_start;
    unsigned int lookahead;
    unsigned int prev_length;
    unsigned int max_chain_length;
    unsigned int max_lazy_match;
    int level;
    int strategy;
    unsigned char padding[8192];
};

static sigjmp_buf jump_env;
static volatile sig_atomic_t caught_signal;

static void fault_handler(int signo)
{
    caught_signal = signo;
    siglongjmp(jump_env, 1);
}

static void install_fault_handlers(struct sigaction *old_segv, struct sigaction *old_bus)
{
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = fault_handler;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, old_segv);
    sigaction(SIGBUS, &sa, old_bus);
}

static void restore_fault_handlers(const struct sigaction *old_segv, const struct sigaction *old_bus)
{
    sigaction(SIGSEGV, old_segv, NULL);
    sigaction(SIGBUS, old_bus, NULL);
}

static void fill_repetitive_payload(unsigned char *buf, size_t len)
{
    static const unsigned char pattern[] =
        "BinaryKernelCodeMapping::mz_zlib::repeatable-payload::";
    size_t i;

    for (i = 0; i < len; i++) {
        buf[i] = pattern[i % (sizeof(pattern) - 1)];
    }
}

static void fill_mixed_payload(unsigned char *buf, size_t len)
{
    size_t i;

    for (i = 0; i < len; i++) {
        buf[i] = (unsigned char)(((i * 131U) + (i >> 3) + 17U) & 0xffU);
    }
}

static int verify_roundtrip(const char *label, zlib_uncompress_fn uncompress_fn,
                            const unsigned char *input, size_t input_len,
                            const unsigned char *compressed, size_t compressed_len)
{
    unsigned char *decoded;
    unsigned long decoded_len = (unsigned long)input_len;
    int rc;

    decoded = malloc(input_len == 0 ? 1 : input_len);
    if (decoded == NULL) {
        printf("%s roundtrip: malloc failed\n", label);
        return 0;
    }

    rc = uncompress_fn(decoded, &decoded_len, compressed, (unsigned long)compressed_len);
    if (rc != Z_OK) {
        printf("%s roundtrip: uncompress rc=%d compressed_len=%zu\n",
               label, rc, compressed_len);
        free(decoded);
        return 0;
    }

    if (decoded_len != input_len || memcmp(decoded, input, input_len) != 0) {
        printf("%s roundtrip: mismatch decoded_len=%lu expected=%zu\n",
               label, decoded_len, input_len);
        free(decoded);
        return 0;
    }

    printf("%s roundtrip: OK compressed_len=%zu decoded_len=%lu\n",
           label, compressed_len, decoded_len);
    free(decoded);
    return 1;
}

static void run_finish_roundtrip_case(const char *label,
                                      mz_zlib_deflate_fn deflate_fn,
                                      mz_zlib_deflateInit2_fn init2_fn,
                                      zlib_compress_bound_fn compress_bound_fn,
                                      zlib_uncompress_fn uncompress_fn,
                                      int level,
                                      int strategy,
                                      const unsigned char *input,
                                      size_t input_len)
{
    z_stream stream;
    unsigned char *workspace = NULL;
    unsigned char *output = NULL;
    unsigned long output_cap;
    struct fake_deflate_state *state;
    int init_rc;
    int deflate_rc;

    memset(&stream, 0, sizeof(stream));
    output_cap = compress_bound_fn != NULL ? compress_bound_fn((unsigned long)input_len)
                                           : (unsigned long)(input_len * 2U + 1024U);
    workspace = malloc(TEST_WORKSPACE_SIZE);
    output = calloc(1, output_cap == 0 ? 1 : output_cap);
    if (workspace == NULL || output == NULL) {
        printf("%s: allocation failed\n", label);
        free(workspace);
        free(output);
        return;
    }

    memset(workspace, 0, TEST_WORKSPACE_SIZE);
    stream.workspace = workspace;

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) != 0) {
        printf("%s: faulted with signal %d\n", label, (int)caught_signal);
        free(workspace);
        free(output);
        return;
    }

    init_rc = init2_fn(&stream, level, Z_DEFLATED, TEST_WINDOW_BITS,
                       TEST_MEM_LEVEL, strategy);
    if (init_rc != Z_OK || stream.state == NULL) {
        printf("%s: init2 rc=%d state=%p\n", label, init_rc, (void *)stream.state);
        free(workspace);
        free(output);
        return;
    }

    state = (struct fake_deflate_state *)stream.state;
    stream.next_in = input;
    stream.avail_in = (uLong)input_len;
    stream.next_out = output;
    stream.avail_out = output_cap;
    stream.adler = 1;

    deflate_rc = deflate_fn(&stream, Z_FINISH);
    printf("%s: init2=%d deflate=%d total_in=%lu total_out=%lu pending=%d status=%d strategy=%d\n",
           label, init_rc, deflate_rc, stream.total_in, stream.total_out,
           state->pending, state->status, strategy);

    if (deflate_rc == Z_STREAM_END) {
        verify_roundtrip(label, uncompress_fn, input, input_len, output, stream.total_out);
    }

    free(workspace);
    free(output);
}

static void run_chunked_roundtrip_case(const char *label,
                                       mz_zlib_deflate_fn deflate_fn,
                                       mz_zlib_deflateInit2_fn init2_fn,
                                       zlib_compress_bound_fn compress_bound_fn,
                                       zlib_uncompress_fn uncompress_fn,
                                       int level,
                                       int strategy,
                                       int mid_flush,
                                       const unsigned char *input,
                                       size_t input_len)
{
    z_stream stream;
    unsigned char *workspace = NULL;
    unsigned char *output = NULL;
    unsigned long output_cap;
    size_t split = input_len / 2;
    struct fake_deflate_state *state;
    int init_rc;
    int rc1;
    int rc2;
    int rc3;

    memset(&stream, 0, sizeof(stream));
    output_cap = compress_bound_fn != NULL ? compress_bound_fn((unsigned long)input_len)
                                           : (unsigned long)(input_len * 2U + 1024U);
    output_cap += 8192;
    workspace = malloc(TEST_WORKSPACE_SIZE);
    output = calloc(1, output_cap == 0 ? 1 : output_cap);
    if (workspace == NULL || output == NULL) {
        printf("%s: allocation failed\n", label);
        free(workspace);
        free(output);
        return;
    }

    memset(workspace, 0, TEST_WORKSPACE_SIZE);
    stream.workspace = workspace;

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) != 0) {
        printf("%s: faulted with signal %d\n", label, (int)caught_signal);
        free(workspace);
        free(output);
        return;
    }

    init_rc = init2_fn(&stream, level, Z_DEFLATED, TEST_WINDOW_BITS,
                       TEST_MEM_LEVEL, strategy);
    if (init_rc != Z_OK || stream.state == NULL) {
        printf("%s: init2 rc=%d state=%p\n", label, init_rc, (void *)stream.state);
        free(workspace);
        free(output);
        return;
    }

    state = (struct fake_deflate_state *)stream.state;
    stream.next_out = output;
    stream.avail_out = output_cap;
    stream.adler = 1;

    stream.next_in = input;
    stream.avail_in = (uLong)split;
    rc1 = deflate_fn(&stream, Z_NO_FLUSH);

    stream.next_in = input + split;
    stream.avail_in = (uLong)(input_len - split);
    rc2 = deflate_fn(&stream, mid_flush);

    stream.next_in = NULL;
    stream.avail_in = 0;
    rc3 = deflate_fn(&stream, Z_FINISH);

    printf("%s: init2=%d rc1=%d rc2=%d rc3=%d total_in=%lu total_out=%lu pending=%d status=%d strategy=%d mid_flush=%d\n",
           label, init_rc, rc1, rc2, rc3, stream.total_in, stream.total_out,
           state->pending, state->status, strategy, mid_flush);

    if (rc3 == Z_STREAM_END) {
        verify_roundtrip(label, uncompress_fn, input, input_len, output, stream.total_out);
    }

    free(workspace);
    free(output);
}

static void run_tiny_out_roundtrip_case(const char *label,
                                        mz_zlib_deflate_fn deflate_fn,
                                        mz_zlib_deflateInit2_fn init2_fn,
                                        zlib_uncompress_fn uncompress_fn,
                                        int level,
                                        int strategy,
                                        const unsigned char *input,
                                        size_t input_len,
                                        size_t out_chunk)
{
    z_stream stream;
    unsigned char *workspace = NULL;
    unsigned char *output = NULL;
    unsigned char chunk_buf[32];
    size_t output_cap = input_len * 2U + 16384U;
    size_t produced = 0;
    struct fake_deflate_state *state;
    int init_rc;
    int rc = Z_OK;

    memset(&stream, 0, sizeof(stream));
    workspace = malloc(TEST_WORKSPACE_SIZE);
    output = calloc(1, output_cap == 0 ? 1 : output_cap);
    if (workspace == NULL || output == NULL) {
        printf("%s: allocation failed\n", label);
        free(workspace);
        free(output);
        return;
    }

    memset(workspace, 0, TEST_WORKSPACE_SIZE);
    stream.workspace = workspace;

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) != 0) {
        printf("%s: faulted with signal %d\n", label, (int)caught_signal);
        free(workspace);
        free(output);
        return;
    }

    init_rc = init2_fn(&stream, level, Z_DEFLATED, TEST_WINDOW_BITS,
                       TEST_MEM_LEVEL, strategy);
    if (init_rc != Z_OK || stream.state == NULL) {
        printf("%s: init2 rc=%d state=%p\n", label, init_rc, (void *)stream.state);
        free(workspace);
        free(output);
        return;
    }

    state = (struct fake_deflate_state *)stream.state;
    stream.next_in = input;
    stream.avail_in = (uLong)input_len;
    stream.adler = 1;

    while (produced < output_cap) {
        memset(chunk_buf, 0, sizeof(chunk_buf));
        stream.next_out = chunk_buf;
        stream.avail_out = (uLong)out_chunk;
        rc = deflate_fn(&stream, stream.avail_in == 0 ? Z_FINISH : Z_NO_FLUSH);

        if (produced + out_chunk > output_cap) {
            printf("%s: output buffer exhausted\n", label);
            break;
        }
        memcpy(output + produced, chunk_buf, out_chunk - stream.avail_out);
        produced += out_chunk - stream.avail_out;

        if (rc == Z_STREAM_END) {
            break;
        }
        if (rc != Z_OK) {
            break;
        }
    }

    printf("%s: init2=%d final_rc=%d total_in=%lu total_out=%lu produced=%zu pending=%d status=%d chunk=%zu strategy=%d\n",
           label, init_rc, rc, stream.total_in, stream.total_out, produced,
           state->pending, state->status, out_chunk, strategy);

    if (rc == Z_STREAM_END) {
        verify_roundtrip(label, uncompress_fn, input, input_len, output, produced);
    }

    free(workspace);
    free(output);
}

int main(void)
{
    void *handle = dlopen(LIB_PATH, RTLD_NOW);
    void *zlib_handle;
    zlib_compress_bound_fn compress_bound_fn;
    zlib_uncompress_fn uncompress_fn;
    unsigned char *large_repetitive = NULL;
    unsigned char *large_mixed = NULL;
    size_t large_repetitive_len = 65536;
    size_t large_mixed_len = 49152;
    if (handle == NULL) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }

    zlib_handle = dlopen("libz.so.1", RTLD_NOW);
    if (zlib_handle == NULL) {
        fprintf(stderr, "dlopen libz failed: %s\n", dlerror());
        dlclose(handle);
        return 1;
    }

    compress_bound_fn = (zlib_compress_bound_fn)dlsym(zlib_handle, "compressBound");
    uncompress_fn = (zlib_uncompress_fn)dlsym(zlib_handle, "uncompress");
    if (compress_bound_fn == NULL || uncompress_fn == NULL) {
        fprintf(stderr, "dlsym libz helpers failed\n");
        dlclose(zlib_handle);
        dlclose(handle);
        return 1;
    }

    dlerror();
    mz_zlib_deflate_fn fn = (mz_zlib_deflate_fn)dlsym(handle, "mz_zlib_deflate");
    const char *err = dlerror();
    if (err != NULL) {
        fprintf(stderr, "dlsym failed: %s\n", err);
        dlclose(handle);
        return 1;
    }

    dlerror();
    mz_zlib_deflateInit2_fn init2_fn =
        (mz_zlib_deflateInit2_fn)dlsym(handle, "mz_zlib_deflateInit2");
    err = dlerror();
    if (err != NULL) {
        fprintf(stderr, "dlsym failed: %s\n", err);
        dlclose(handle);
        return 1;
    }

    z_stream stream;
    memset(&stream, 0, sizeof(stream));

    z_stream guarded_stream;
    memset(&guarded_stream, 0, sizeof(guarded_stream));
    struct fake_deflate_state guarded_state;
    memset(&guarded_state, 0, sizeof(guarded_state));
    guarded_stream.state = (struct internal_state *)&guarded_state;
    guarded_stream.avail_out = 0;

    z_stream buffered_stream;
    unsigned char pending_byte = 0xab;
    unsigned char copied_byte = 0x00;
    struct fake_deflate_state buffered_state;
    memset(&buffered_stream, 0, sizeof(buffered_stream));
    memset(&buffered_state, 0, sizeof(buffered_state));
    buffered_state.status = BUSY_STATE;
    buffered_state.pending_buf = &pending_byte;
    buffered_state.pending_out = &pending_byte;
    buffered_state.pending = 1;
    buffered_state.last_flush = Z_NO_FLUSH;
    buffered_stream.state = (struct internal_state *)&buffered_state;
    buffered_stream.next_out = &copied_byte;
    buffered_stream.avail_out = 1;

    z_stream header_stream;
    unsigned char header_pending[8] = {0};
    unsigned char header_out[8] = {0};
    struct fake_deflate_state header_state;
    memset(&header_stream, 0, sizeof(header_stream));
    memset(&header_state, 0, sizeof(header_state));
    header_state.status = INIT_STATE;
    header_state.pending_buf = header_pending;
    header_state.pending_out = header_pending;
    header_state.pending_buf_size = sizeof(header_pending);
    header_state.last_flush = -1;
    header_state.w_bits = 15;
    header_state.level = 1;
    header_stream.state = (struct internal_state *)&header_state;
    header_stream.next_out = header_out;
    header_stream.avail_out = sizeof(header_out);
    header_stream.adler = 1;

    z_stream empty_busy_stream;
    struct fake_deflate_state empty_busy_state;
    memset(&empty_busy_stream, 0, sizeof(empty_busy_stream));
    memset(&empty_busy_state, 0, sizeof(empty_busy_state));
    empty_busy_state.status = BUSY_STATE;
    empty_busy_state.last_flush = Z_NO_FLUSH;
    empty_busy_stream.state = (struct internal_state *)&empty_busy_state;
    empty_busy_stream.avail_out = 1;

    z_stream fast_stream;
    struct fake_deflate_state fast_state;
    memset(&fast_stream, 0, sizeof(fast_stream));
    memset(&fast_state, 0, sizeof(fast_state));
    fast_state.status = BUSY_STATE;
    fast_state.last_flush = -1;
    fast_state.level = 1;
    fast_state.lookahead = 1;
    fast_state.w_size = 1;
    fast_state.window_size = 2;
    fast_stream.state = (struct internal_state *)&fast_state;
    fast_stream.avail_out = 16;

    z_stream slow_stream;
    struct fake_deflate_state slow_state;
    memset(&slow_stream, 0, sizeof(slow_stream));
    memset(&slow_state, 0, sizeof(slow_state));
    slow_state.status = BUSY_STATE;
    slow_state.last_flush = -1;
    slow_state.level = 4;
    slow_state.lookahead = 1;
    slow_state.w_size = 1;
    slow_state.window_size = 2;
    slow_stream.state = (struct internal_state *)&slow_state;
    slow_stream.avail_out = 16;

    z_stream stored_stream;
    struct fake_deflate_state stored_state;
    unsigned char stored_window[4] = {0x11, 0x22, 0x33, 0x44};
    unsigned char stored_pending[32] = {0};
    unsigned char stored_out[32] = {0};
    memset(&stored_stream, 0, sizeof(stored_stream));
    memset(&stored_state, 0, sizeof(stored_state));
    stored_state.status = BUSY_STATE;
    stored_state.last_flush = -1;
    stored_state.level = 0;
    stored_state.pending_buf = stored_pending;
    stored_state.pending_out = stored_pending;
    stored_state.pending_buf_size = sizeof(stored_pending);
    stored_state.window = stored_window;
    stored_state.w_size = 1;
    stored_state.window_size = 2;
    stored_state.block_start = 0;
    stored_state.strstart = 1;
    stored_stream.state = (struct internal_state *)&stored_state;
    stored_stream.next_out = stored_out;
    stored_stream.avail_out = sizeof(stored_out);
    stored_stream.adler = 1;

    z_stream init2_bad_method_stream;
    unsigned char init2_bad_method_workspace[TEST_WORKSPACE_SIZE];
    memset(&init2_bad_method_stream, 0, sizeof(init2_bad_method_stream));
    memset(init2_bad_method_workspace, 0, sizeof(init2_bad_method_workspace));
    init2_bad_method_stream.workspace = init2_bad_method_workspace;

    z_stream init2_bad_window_stream;
    unsigned char init2_bad_window_workspace[TEST_WORKSPACE_SIZE];
    memset(&init2_bad_window_stream, 0, sizeof(init2_bad_window_stream));
    memset(init2_bad_window_workspace, 0, sizeof(init2_bad_window_workspace));
    init2_bad_window_stream.workspace = init2_bad_window_workspace;

    z_stream init2_ok_stream;
    unsigned char *init2_ok_workspace = malloc(TEST_WORKSPACE_SIZE);
    unsigned char init2_ok_output[128] = {0};
    const unsigned char init2_ok_input[] = "stub dso init2 smoke test payload";
    struct fake_deflate_state *init2_ok_state;
    int init2_ok_rc = Z_STREAM_ERROR;

    z_stream init2_data_stream;
    unsigned char *init2_data_workspace = malloc(TEST_WORKSPACE_SIZE);
    unsigned char init2_data_output[128] = {0};
    struct fake_deflate_state *init2_data_state;
    int init2_data_rc = Z_STREAM_ERROR;

    z_stream init2_stored_stream;
    unsigned char *init2_stored_workspace = malloc(TEST_WORKSPACE_SIZE);
    unsigned char init2_stored_output[128] = {0};
    struct fake_deflate_state *init2_stored_state;
    int init2_stored_rc = Z_STREAM_ERROR;

    memset(&init2_ok_stream, 0, sizeof(init2_ok_stream));
    memset(&init2_data_stream, 0, sizeof(init2_data_stream));
    memset(&init2_stored_stream, 0, sizeof(init2_stored_stream));
    if (init2_ok_workspace == NULL || init2_data_workspace == NULL ||
        init2_stored_workspace == NULL) {
        fprintf(stderr, "malloc failed for init2 workspace\n");
        free(init2_ok_workspace);
        free(init2_data_workspace);
        free(init2_stored_workspace);
        dlclose(handle);
        return 1;
    }
    memset(init2_ok_workspace, 0, TEST_WORKSPACE_SIZE);
    init2_ok_stream.workspace = init2_ok_workspace;
    memset(init2_data_workspace, 0, TEST_WORKSPACE_SIZE);
    init2_data_stream.workspace = init2_data_workspace;
    memset(init2_stored_workspace, 0, TEST_WORKSPACE_SIZE);
    init2_stored_stream.workspace = init2_stored_workspace;

    struct sigaction old_segv, old_bus;
    install_fault_handlers(&old_segv, &old_bus);

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        printf("mz_zlib_deflate(NULL, 0) = %d\n", fn(NULL, 0));
    } else {
        printf("mz_zlib_deflate(NULL, 0) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        printf("mz_zlib_deflate(&zero_stream, 0) = %d\n", fn(&stream, 0));
    } else {
        printf("mz_zlib_deflate(&zero_stream, 0) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        printf("mz_zlib_deflate(&guarded_stream, 0) = %d\n", fn(&guarded_stream, 0));
    } else {
        printf("mz_zlib_deflate(&guarded_stream, 0) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        int rc = fn(&buffered_stream, 0);
        printf("mz_zlib_deflate(&buffered_stream, 0) = %d, copied_byte=0x%02x, pending=%d, avail_out=%lu\n",
               rc, copied_byte, buffered_state.pending, buffered_stream.avail_out);
    } else {
        printf("mz_zlib_deflate(&buffered_stream, 0) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        int rc = fn(&header_stream, 0);
        printf("mz_zlib_deflate(&header_stream, 0) = %d, header=%02x %02x, total_out=%lu, status=%d\n",
               rc, header_out[0], header_out[1], header_stream.total_out, header_state.status);
    } else {
        printf("mz_zlib_deflate(&header_stream, 0) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        printf("mz_zlib_deflate(&empty_busy_stream, 0) = %d\n", fn(&empty_busy_stream, 0));
    } else {
        printf("mz_zlib_deflate(&empty_busy_stream, 0) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        int rc = fn(&fast_stream, 0);
        printf("mz_zlib_deflate(&fast_stream, 0) = %d, lookahead=%u, status=%d\n",
               rc, fast_state.lookahead, fast_state.status);
    } else {
        printf("mz_zlib_deflate(&fast_stream, 0) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        int rc = fn(&slow_stream, 0);
        printf("mz_zlib_deflate(&slow_stream, 0) = %d, lookahead=%u, status=%d\n",
               rc, slow_state.lookahead, slow_state.status);
    } else {
        printf("mz_zlib_deflate(&slow_stream, 0) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        int rc = fn(&stored_stream, Z_FINISH);
        printf("mz_zlib_deflate(&stored_stream, Z_FINISH) = %d, total_out=%lu, status=%d, out0=%02x out1=%02x out2=%02x\n",
               rc, stored_stream.total_out, stored_state.status,
               stored_out[0], stored_out[1], stored_out[2]);
    } else {
        printf("mz_zlib_deflate(&stored_stream, Z_FINISH) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        printf("mz_zlib_deflateInit2(NULL, %d, %d, %d, %d, %d) = %d\n",
               Z_DEFAULT_COMPRESSION, Z_DEFLATED, TEST_WINDOW_BITS,
               TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY,
               init2_fn(NULL, Z_DEFAULT_COMPRESSION, Z_DEFLATED,
                        TEST_WINDOW_BITS, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY));
    } else {
        printf("mz_zlib_deflateInit2(NULL, ...) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        int rc = init2_fn(&init2_bad_method_stream, Z_DEFAULT_COMPRESSION, 0,
                          TEST_WINDOW_BITS, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY);
        printf("mz_zlib_deflateInit2(&bad_method_stream, default, 0, %d, %d, %d) = %d\n",
               TEST_WINDOW_BITS, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY, rc);
    } else {
        printf("mz_zlib_deflateInit2(&bad_method_stream, ...) faulted with signal %d\n",
               (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        int rc = init2_fn(&init2_bad_window_stream, Z_DEFAULT_COMPRESSION,
                          Z_DEFLATED, 8, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY);
        printf("mz_zlib_deflateInit2(&bad_window_stream, default, %d, 8, %d, %d) = %d\n",
               Z_DEFLATED, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY, rc);
    } else {
        printf("mz_zlib_deflateInit2(&bad_window_stream, ...) faulted with signal %d\n",
               (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        init2_ok_rc = init2_fn(&init2_ok_stream, Z_DEFAULT_COMPRESSION, Z_DEFLATED,
                               TEST_WINDOW_BITS, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY);
        init2_ok_state = (struct fake_deflate_state *)init2_ok_stream.state;
        printf("mz_zlib_deflateInit2(&ok_stream, default, %d, %d, %d, %d) = %d, state=%p, status=%d, w_bits=%u, hash_bits=%u, level=%d\n",
               Z_DEFLATED, TEST_WINDOW_BITS, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY,
               init2_ok_rc, (void *)init2_ok_stream.state,
               init2_ok_state ? init2_ok_state->status : -1,
               init2_ok_state ? init2_ok_state->w_bits : 0,
               init2_ok_state ? init2_ok_state->hash_bits : 0,
               init2_ok_state ? init2_ok_state->level : -1);
    } else {
        printf("mz_zlib_deflateInit2(&ok_stream, ...) faulted with signal %d\n",
               (int)caught_signal);
    }

    if (init2_ok_rc == Z_OK && init2_ok_stream.state != NULL) {
        caught_signal = 0;
        if (sigsetjmp(jump_env, 1) == 0) {
            init2_ok_state = (struct fake_deflate_state *)init2_ok_stream.state;
            init2_ok_stream.next_in = NULL;
            init2_ok_stream.avail_in = 0;
            init2_ok_stream.next_out = init2_ok_output;
            init2_ok_stream.avail_out = sizeof(init2_ok_output);
            init2_ok_stream.adler = 1;

            {
                int deflate_rc = fn(&init2_ok_stream, Z_NO_FLUSH);
                printf("mz_zlib_deflate(&ok_stream_after_init2, Z_NO_FLUSH) = %d, total_in=%lu, total_out=%lu, pending=%d, status=%d, out0=%02x out1=%02x\n",
                       deflate_rc, init2_ok_stream.total_in, init2_ok_stream.total_out,
                       init2_ok_state->pending, init2_ok_state->status,
                       init2_ok_output[0], init2_ok_output[1]);
            }
        } else {
            printf("mz_zlib_deflate(&ok_stream_after_init2, Z_NO_FLUSH) faulted with signal %d\n",
                   (int)caught_signal);
        }
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        init2_data_rc = init2_fn(&init2_data_stream, Z_DEFAULT_COMPRESSION, Z_DEFLATED,
                                 TEST_WINDOW_BITS, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY);
        init2_data_state = (struct fake_deflate_state *)init2_data_stream.state;
        printf("mz_zlib_deflateInit2(&data_stream, default, %d, %d, %d, %d) = %d, state=%p\n",
               Z_DEFLATED, TEST_WINDOW_BITS, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY,
               init2_data_rc, (void *)init2_data_stream.state);
        if (init2_data_state != NULL) {
            printf("data_stream state after init2: status=%d, w_bits=%u, hash_bits=%u, level=%d\n",
                   init2_data_state->status, init2_data_state->w_bits,
                   init2_data_state->hash_bits, init2_data_state->level);
        }
    } else {
        printf("mz_zlib_deflateInit2(&data_stream, ...) faulted with signal %d\n",
               (int)caught_signal);
    }

    if (init2_data_rc == Z_OK && init2_data_stream.state != NULL) {
        caught_signal = 0;
        if (sigsetjmp(jump_env, 1) == 0) {
            init2_data_state = (struct fake_deflate_state *)init2_data_stream.state;
            init2_data_stream.next_in = init2_ok_input;
            init2_data_stream.avail_in = sizeof(init2_ok_input) - 1;
            init2_data_stream.next_out = init2_data_output;
            init2_data_stream.avail_out = sizeof(init2_data_output);
            init2_data_stream.adler = 1;

            {
                int deflate_rc = fn(&init2_data_stream, Z_FINISH);
                printf("mz_zlib_deflate(&data_stream_after_init2, Z_FINISH) = %d, total_in=%lu, total_out=%lu, pending=%d, status=%d, out0=%02x out1=%02x\n",
                       deflate_rc, init2_data_stream.total_in, init2_data_stream.total_out,
                       init2_data_state->pending, init2_data_state->status,
                       init2_data_output[0], init2_data_output[1]);
            }
        } else {
            printf("mz_zlib_deflate(&data_stream_after_init2, Z_FINISH) faulted with signal %d\n",
                   (int)caught_signal);
        }
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        init2_stored_rc = init2_fn(&init2_stored_stream, 0, Z_DEFLATED,
                                   TEST_WINDOW_BITS, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY);
        init2_stored_state = (struct fake_deflate_state *)init2_stored_stream.state;
        printf("mz_zlib_deflateInit2(&stored_data_stream, 0, %d, %d, %d, %d) = %d, state=%p\n",
               Z_DEFLATED, TEST_WINDOW_BITS, TEST_MEM_LEVEL, Z_DEFAULT_STRATEGY,
               init2_stored_rc, (void *)init2_stored_stream.state);
        if (init2_stored_state != NULL) {
            printf("stored_data_stream state after init2: status=%d, w_bits=%u, hash_bits=%u, level=%d\n",
                   init2_stored_state->status, init2_stored_state->w_bits,
                   init2_stored_state->hash_bits, init2_stored_state->level);
        }
    } else {
        printf("mz_zlib_deflateInit2(&stored_data_stream, ...) faulted with signal %d\n",
               (int)caught_signal);
    }

    if (init2_stored_rc == Z_OK && init2_stored_stream.state != NULL) {
        caught_signal = 0;
        if (sigsetjmp(jump_env, 1) == 0) {
            init2_stored_state = (struct fake_deflate_state *)init2_stored_stream.state;
            init2_stored_stream.next_in = init2_ok_input;
            init2_stored_stream.avail_in = sizeof(init2_ok_input) - 1;
            init2_stored_stream.next_out = init2_stored_output;
            init2_stored_stream.avail_out = sizeof(init2_stored_output);
            init2_stored_stream.adler = 1;

            {
                int deflate_rc = fn(&init2_stored_stream, Z_FINISH);
                printf("mz_zlib_deflate(&stored_data_stream_after_init2, Z_FINISH) = %d, total_in=%lu, total_out=%lu, pending=%d, status=%d, out0=%02x out1=%02x\n",
                       deflate_rc, init2_stored_stream.total_in, init2_stored_stream.total_out,
                       init2_stored_state->pending, init2_stored_state->status,
                       init2_stored_output[0], init2_stored_output[1]);
            }
        } else {
            printf("mz_zlib_deflate(&stored_data_stream_after_init2, Z_FINISH) faulted with signal %d\n",
                   (int)caught_signal);
        }
    }

    large_repetitive = malloc(large_repetitive_len);
    large_mixed = malloc(large_mixed_len);
    if (large_repetitive == NULL || large_mixed == NULL) {
        fprintf(stderr, "malloc failed for extended payloads\n");
        free(large_repetitive);
        free(large_mixed);
        restore_fault_handlers(&old_segv, &old_bus);
        free(init2_ok_workspace);
        free(init2_data_workspace);
        free(init2_stored_workspace);
        dlclose(zlib_handle);
        dlclose(handle);
        return 1;
    }

    fill_repetitive_payload(large_repetitive, large_repetitive_len);
    fill_mixed_payload(large_mixed, large_mixed_len);

    run_finish_roundtrip_case("level0-finish-small", fn, init2_fn,
                              compress_bound_fn, uncompress_fn, 0,
                              Z_DEFAULT_STRATEGY,
                              init2_ok_input, sizeof(init2_ok_input) - 1);
    run_finish_roundtrip_case("level1-finish-large-mixed", fn, init2_fn,
                              compress_bound_fn, uncompress_fn, 1,
                              Z_DEFAULT_STRATEGY,
                              large_mixed, large_mixed_len);
    run_finish_roundtrip_case("level6-finish-large-repeat", fn, init2_fn,
                              compress_bound_fn, uncompress_fn, 6,
                              Z_DEFAULT_STRATEGY,
                              large_repetitive, large_repetitive_len);
    run_finish_roundtrip_case("level6-finish-large-mixed", fn, init2_fn,
                              compress_bound_fn, uncompress_fn, 6,
                              Z_DEFAULT_STRATEGY,
                              large_mixed, large_mixed_len);
    run_finish_roundtrip_case("level6-finish-filtered", fn, init2_fn,
                              compress_bound_fn, uncompress_fn, 6,
                              Z_FILTERED,
                              large_mixed, large_mixed_len);
    run_finish_roundtrip_case("level6-finish-huffman-only", fn, init2_fn,
                              compress_bound_fn, uncompress_fn, 6,
                              Z_HUFFMAN_ONLY,
                              large_mixed, large_mixed_len);

    run_chunked_roundtrip_case("level1-chunked-no-flush", fn, init2_fn,
                               compress_bound_fn, uncompress_fn, 1,
                               Z_DEFAULT_STRATEGY,
                               Z_NO_FLUSH, large_mixed, large_mixed_len);
    run_chunked_roundtrip_case("level6-chunked-full-flush", fn, init2_fn,
                               compress_bound_fn, uncompress_fn, 6,
                               Z_DEFAULT_STRATEGY,
                               Z_FULL_FLUSH, large_repetitive, large_repetitive_len);
    run_chunked_roundtrip_case("level6-chunked-sync-flush", fn, init2_fn,
                               compress_bound_fn, uncompress_fn, 6,
                               Z_DEFAULT_STRATEGY,
                               Z_SYNC_FLUSH, large_mixed, large_mixed_len);
    run_chunked_roundtrip_case("level6-chunked-partial-flush", fn, init2_fn,
                               compress_bound_fn, uncompress_fn, 6,
                               Z_DEFAULT_STRATEGY,
                               Z_PARTIAL_FLUSH, large_repetitive, large_repetitive_len);
    run_tiny_out_roundtrip_case("level6-tiny-out", fn, init2_fn,
                                uncompress_fn, 6, Z_DEFAULT_STRATEGY,
                                large_repetitive, large_repetitive_len, 7);
    run_tiny_out_roundtrip_case("level1-tiny-out-huffman", fn, init2_fn,
                                uncompress_fn, 1, Z_HUFFMAN_ONLY,
                                large_mixed, large_mixed_len, 5);

    restore_fault_handlers(&old_segv, &old_bus);

    free(large_repetitive);
    free(large_mixed);
    free(init2_ok_workspace);
    free(init2_data_workspace);
    free(init2_stored_workspace);
    dlclose(zlib_handle);
    dlclose(handle);
    return 0;
}
