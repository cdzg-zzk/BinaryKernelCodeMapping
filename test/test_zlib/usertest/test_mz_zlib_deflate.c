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
#define TEST_WINDOW_BITS 15
#define TEST_MEM_LEVEL 8

typedef int (*mz_zlib_deflate_fn)(z_streamp strm, int flush);
typedef int (*mz_zlib_deflateInit2_fn)(z_streamp strm, int level, int method,
                                       int windowBits, int memLevel, int strategy);
typedef int (*mz_zlib_deflate_workspacesize_fn)(int windowBits, int memLevel);
typedef int (*mz_zlib_deflateReset_fn)(z_streamp strm);
typedef int (*mz_zlib_deflateEnd_fn)(z_streamp strm);
typedef void (*mz_crc32init_le_fn)(void);
typedef u32 (*mz_crc32_fn)(u32 crc, const unsigned char *p, size_t len);
typedef const u32 *(*mz_get_crc_table_fn)(void);
typedef unsigned long (*zlib_compress_bound_fn)(unsigned long source_len);
typedef int (*zlib_uncompress_fn)(Byte *dest, unsigned long *dest_len,
                                  const Byte *source, unsigned long source_len);

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

static unsigned char *allocate_workspace(mz_zlib_deflate_workspacesize_fn workspacesize_fn,
                                         int window_bits, int mem_level,
                                         int *workspace_size_out)
{
    int workspace_size = workspacesize_fn(window_bits, mem_level);
    unsigned char *workspace;

    if (workspace_size <= 0) {
        return NULL;
    }

    workspace = malloc((size_t)workspace_size);
    if (workspace == NULL) {
        return NULL;
    }

    memset(workspace, 0, (size_t)workspace_size);
    if (workspace_size_out != NULL) {
        *workspace_size_out = workspace_size;
    }
    return workspace;
}

static void run_crc_cases(mz_crc32init_le_fn init_fn,
                          mz_crc32_fn crc_fn,
                          mz_get_crc_table_fn get_table_fn)
{
    static const unsigned char crc_msg[] = "123456789";
    const u32 *table = NULL;
    u32 raw_crc = 0;
    u32 zlib_crc = 0;
    u32 zlib_crc_inc = 0;

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) != 0) {
        printf("crc-suite: faulted with signal %d\n", (int)caught_signal);
        return;
    }

    init_fn();
    table = get_table_fn();
    raw_crc = crc_fn(0, crc_msg, sizeof(crc_msg) - 1);
    zlib_crc = crc_fn(0xffffffffU, crc_msg, sizeof(crc_msg) - 1) ^ 0xffffffffU;
    zlib_crc_inc =
        crc_fn(crc_fn(0xffffffffU, crc_msg, 4), crc_msg + 4, (sizeof(crc_msg) - 1) - 4) ^
        0xffffffffU;

    if (table == NULL) {
        printf("crc-suite: mz_get_crc_table returned NULL\n");
        return;
    }

    printf("crc-suite: table=%p table[0]=0x%08x table[1]=0x%08x table[2]=0x%08x table[3]=0x%08x\n",
           (const void *)table, table[0], table[1], table[2], table[3]);
    printf("crc-suite: raw_crc=0x%08x zlib_crc=0x%08x incremental=0x%08x\n",
           raw_crc, zlib_crc, zlib_crc_inc);

    if (table[0] != 0x00000000U || table[1] != 0x77073096U) {
        printf("crc-suite: table verification FAILED\n");
        return;
    }
    if (zlib_crc != 0xcbf43926U || zlib_crc_inc != 0xcbf43926U) {
        printf("crc-suite: crc verification FAILED\n");
        return;
    }

    printf("crc-suite: OK\n");
}

static void run_finish_roundtrip_case(const char *label,
                                      mz_zlib_deflate_fn deflate_fn,
                                      mz_zlib_deflateInit2_fn init2_fn,
                                      mz_zlib_deflate_workspacesize_fn workspacesize_fn,
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
    int init_rc;
    int deflate_rc;

    memset(&stream, 0, sizeof(stream));
    output_cap = compress_bound_fn != NULL ? compress_bound_fn((unsigned long)input_len)
                                           : (unsigned long)(input_len * 2U + 1024U);
    workspace = allocate_workspace(workspacesize_fn, TEST_WINDOW_BITS, TEST_MEM_LEVEL, NULL);
    output = calloc(1, output_cap == 0 ? 1 : output_cap);
    if (workspace == NULL || output == NULL) {
        printf("%s: allocation failed\n", label);
        free(workspace);
        free(output);
        return;
    }

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

    stream.next_in = input;
    stream.avail_in = (uLong)input_len;
    stream.next_out = output;
    stream.avail_out = output_cap;
    stream.adler = 1;

    deflate_rc = deflate_fn(&stream, Z_FINISH);
    printf("%s: init2=%d deflate=%d total_in=%lu total_out=%lu state=%p strategy=%d\n",
           label, init_rc, deflate_rc, stream.total_in, stream.total_out,
           (void *)stream.state, strategy);

    if (deflate_rc == Z_STREAM_END) {
        verify_roundtrip(label, uncompress_fn, input, input_len, output, stream.total_out);
    }

    free(workspace);
    free(output);
}

static void run_chunked_roundtrip_case(const char *label,
                                       mz_zlib_deflate_fn deflate_fn,
                                       mz_zlib_deflateInit2_fn init2_fn,
                                       mz_zlib_deflate_workspacesize_fn workspacesize_fn,
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
    int init_rc;
    int rc1;
    int rc2;
    int rc3;

    memset(&stream, 0, sizeof(stream));
    output_cap = compress_bound_fn != NULL ? compress_bound_fn((unsigned long)input_len)
                                           : (unsigned long)(input_len * 2U + 1024U);
    output_cap += 8192;
    workspace = allocate_workspace(workspacesize_fn, TEST_WINDOW_BITS, TEST_MEM_LEVEL, NULL);
    output = calloc(1, output_cap == 0 ? 1 : output_cap);
    if (workspace == NULL || output == NULL) {
        printf("%s: allocation failed\n", label);
        free(workspace);
        free(output);
        return;
    }

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

    printf("%s: init2=%d rc1=%d rc2=%d rc3=%d total_in=%lu total_out=%lu state=%p strategy=%d mid_flush=%d\n",
           label, init_rc, rc1, rc2, rc3, stream.total_in, stream.total_out,
           (void *)stream.state, strategy, mid_flush);

    if (rc3 == Z_STREAM_END) {
        verify_roundtrip(label, uncompress_fn, input, input_len, output, stream.total_out);
    }

    free(workspace);
    free(output);
}

static void run_tiny_out_roundtrip_case(const char *label,
                                        mz_zlib_deflate_fn deflate_fn,
                                        mz_zlib_deflateInit2_fn init2_fn,
                                        mz_zlib_deflate_workspacesize_fn workspacesize_fn,
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
    int init_rc;
    int rc = Z_OK;

    memset(&stream, 0, sizeof(stream));
    workspace = allocate_workspace(workspacesize_fn, TEST_WINDOW_BITS, TEST_MEM_LEVEL, NULL);
    output = calloc(1, output_cap == 0 ? 1 : output_cap);
    if (workspace == NULL || output == NULL) {
        printf("%s: allocation failed\n", label);
        free(workspace);
        free(output);
        return;
    }

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

    printf("%s: init2=%d final_rc=%d total_in=%lu total_out=%lu produced=%zu state=%p chunk=%zu strategy=%d\n",
           label, init_rc, rc, stream.total_in, stream.total_out, produced,
           (void *)stream.state, out_chunk, strategy);

    if (rc == Z_STREAM_END) {
        verify_roundtrip(label, uncompress_fn, input, input_len, output, produced);
    }

    free(workspace);
    free(output);
}

static void run_workspacesize_case(const char *label,
                                   mz_zlib_deflate_fn deflate_fn,
                                   mz_zlib_deflateInit2_fn init2_fn,
                                   mz_zlib_deflate_workspacesize_fn workspacesize_fn,
                                   zlib_uncompress_fn uncompress_fn,
                                   int level,
                                   int method,
                                   int window_bits,
                                   int mem_level,
                                   int strategy,
                                   const unsigned char *input,
                                   size_t input_len)
{
    z_stream stream;
    int workspace_size;
    int neg_workspace_size;
    unsigned char *workspace = NULL;
    unsigned char *output = NULL;
    size_t output_cap = input_len * 2U + 16384U;
    int init_rc;
    int deflate_rc;

    memset(&stream, 0, sizeof(stream));
    workspace_size = workspacesize_fn(window_bits, mem_level);
    neg_workspace_size = workspacesize_fn(-window_bits, mem_level);
    printf("%s: workspacesize(%d,%d)=%d workspacesize(%d,%d)=%d\n",
           label, window_bits, mem_level, workspace_size,
           -window_bits, mem_level, neg_workspace_size);

    if (workspace_size <= 0 || workspace_size != neg_workspace_size) {
        printf("%s: invalid workspace size result\n", label);
        return;
    }

    workspace = malloc((size_t)workspace_size);
    output = calloc(1, output_cap == 0 ? 1 : output_cap);
    if (workspace == NULL || output == NULL) {
        printf("%s: allocation failed\n", label);
        free(workspace);
        free(output);
        return;
    }

    memset(workspace, 0, (size_t)workspace_size);
    stream.workspace = workspace;

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) != 0) {
        printf("%s: faulted with signal %d\n", label, (int)caught_signal);
        free(workspace);
        free(output);
        return;
    }

    init_rc = init2_fn(&stream, level, method, window_bits, mem_level, strategy);
    if (init_rc != Z_OK || stream.state == NULL) {
        printf("%s: init2 rc=%d state=%p\n", label, init_rc, (void *)stream.state);
        free(workspace);
        free(output);
        return;
    }

    stream.next_in = input;
    stream.avail_in = (uLong)input_len;
    stream.next_out = output;
    stream.avail_out = (uLong)output_cap;
    stream.adler = 1;

    deflate_rc = deflate_fn(&stream, Z_FINISH);
    printf("%s: init2=%d deflate=%d total_in=%lu total_out=%lu state=%p exact_workspace=%d\n",
           label, init_rc, deflate_rc, stream.total_in, stream.total_out,
           (void *)stream.state, workspace_size);

    if (deflate_rc == Z_STREAM_END) {
        verify_roundtrip(label, uncompress_fn, input, input_len, output, stream.total_out);
    }

    free(workspace);
    free(output);
}

static void run_reset_reuse_case(const char *label,
                                 mz_zlib_deflate_fn deflate_fn,
                                 mz_zlib_deflateInit2_fn init2_fn,
                                 mz_zlib_deflateReset_fn reset_fn,
                                 mz_zlib_deflate_workspacesize_fn workspacesize_fn,
                                 zlib_uncompress_fn uncompress_fn,
                                 int level,
                                 int strategy,
                                 const unsigned char *input1,
                                 size_t input1_len,
                                 const unsigned char *input2,
                                 size_t input2_len)
{
    z_stream stream;
    unsigned char *workspace = NULL;
    unsigned char *output1 = NULL;
    unsigned char *output2 = NULL;
    int workspace_size;
    size_t output_cap1 = input1_len * 2U + 16384U;
    size_t output_cap2 = input2_len * 2U + 16384U;
    int init_rc;
    int deflate1_rc;
    int reset_rc;
    int deflate2_rc;

    memset(&stream, 0, sizeof(stream));
    workspace_size = workspacesize_fn(TEST_WINDOW_BITS, TEST_MEM_LEVEL);
    workspace = malloc((size_t)workspace_size);
    output1 = calloc(1, output_cap1 == 0 ? 1 : output_cap1);
    output2 = calloc(1, output_cap2 == 0 ? 1 : output_cap2);
    if (workspace == NULL || output1 == NULL || output2 == NULL) {
        printf("%s: allocation failed\n", label);
        free(workspace);
        free(output1);
        free(output2);
        return;
    }

    memset(workspace, 0, (size_t)workspace_size);
    stream.workspace = workspace;

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) != 0) {
        printf("%s: faulted with signal %d\n", label, (int)caught_signal);
        free(workspace);
        free(output1);
        free(output2);
        return;
    }

    init_rc = init2_fn(&stream, level, Z_DEFLATED, TEST_WINDOW_BITS,
                       TEST_MEM_LEVEL, strategy);
    if (init_rc != Z_OK || stream.state == NULL) {
        printf("%s: init2 rc=%d state=%p\n", label, init_rc, (void *)stream.state);
        free(workspace);
        free(output1);
        free(output2);
        return;
    }

    stream.next_in = input1;
    stream.avail_in = (uLong)input1_len;
    stream.next_out = output1;
    stream.avail_out = (uLong)output_cap1;
    stream.adler = 1;
    deflate1_rc = deflate_fn(&stream, Z_FINISH);

    printf("%s:first-pass init2=%d deflate=%d total_in=%lu total_out=%lu state=%p\n",
           label, init_rc, deflate1_rc, stream.total_in, stream.total_out,
           (void *)stream.state);
    if (deflate1_rc == Z_STREAM_END) {
        verify_roundtrip(label, uncompress_fn, input1, input1_len, output1, stream.total_out);
    }

    reset_rc = reset_fn(&stream);
    printf("%s:reset rc=%d total_in=%lu total_out=%lu adler=%lu state=%p\n",
           label, reset_rc, stream.total_in, stream.total_out, stream.adler,
           (void *)stream.state);

    memset(output2, 0, output_cap2);
    stream.next_in = input2;
    stream.avail_in = (uLong)input2_len;
    stream.next_out = output2;
    stream.avail_out = (uLong)output_cap2;
    deflate2_rc = deflate_fn(&stream, Z_FINISH);
    printf("%s:second-pass deflate=%d total_in=%lu total_out=%lu state=%p\n",
           label, deflate2_rc, stream.total_in, stream.total_out,
           (void *)stream.state);
    if (deflate2_rc == Z_STREAM_END) {
        verify_roundtrip(label, uncompress_fn, input2, input2_len, output2, stream.total_out);
    }

    free(workspace);
    free(output1);
    free(output2);
}

static void run_end_case(const char *label,
                         mz_zlib_deflate_fn deflate_fn,
                         mz_zlib_deflateInit2_fn init2_fn,
                         mz_zlib_deflateEnd_fn end_fn,
                         mz_zlib_deflate_workspacesize_fn workspacesize_fn,
                         int level,
                         int strategy,
                         const unsigned char *input,
                         size_t input_len,
                         int do_finish)
{
    z_stream stream;
    unsigned char *workspace = NULL;
    unsigned char *output = NULL;
    size_t output_cap = input_len * 2U + 16384U;
    int init_rc;
    int deflate_rc = Z_OK;
    int end1_rc;
    int end2_rc;

    memset(&stream, 0, sizeof(stream));
    workspace = allocate_workspace(workspacesize_fn, TEST_WINDOW_BITS, TEST_MEM_LEVEL, NULL);
    output = calloc(1, output_cap == 0 ? 1 : output_cap);
    if (workspace == NULL || output == NULL) {
        printf("%s: allocation failed\n", label);
        free(workspace);
        free(output);
        return;
    }

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

    if (do_finish) {
        stream.next_in = input;
        stream.avail_in = (uLong)input_len;
        stream.next_out = output;
        stream.avail_out = (uLong)output_cap;
        stream.adler = 1;
        deflate_rc = deflate_fn(&stream, Z_FINISH);
    }

    end1_rc = end_fn(&stream);
    end2_rc = end_fn(&stream);
    printf("%s: init2=%d deflate=%d end1=%d end2=%d state_after_end=%p do_finish=%d\n",
           label, init_rc, deflate_rc, end1_rc, end2_rc, (void *)stream.state, do_finish);

    free(workspace);
    free(output);
}

static void run_end_busy_case(const char *label,
                              mz_zlib_deflate_fn deflate_fn,
                              mz_zlib_deflateInit2_fn init2_fn,
                              mz_zlib_deflateEnd_fn end_fn,
                              mz_zlib_deflate_workspacesize_fn workspacesize_fn,
                              int level,
                              int strategy,
                              const unsigned char *input,
                              size_t input_len)
{
    z_stream stream;
    unsigned char *workspace = NULL;
    unsigned char *output = NULL;
    size_t output_cap = input_len * 2U + 16384U;
    int init_rc;
    int deflate_rc;
    int end1_rc;

    memset(&stream, 0, sizeof(stream));
    workspace = allocate_workspace(workspacesize_fn, TEST_WINDOW_BITS, TEST_MEM_LEVEL, NULL);
    output = calloc(1, output_cap == 0 ? 1 : output_cap);
    if (workspace == NULL || output == NULL) {
        printf("%s: allocation failed\n", label);
        free(workspace);
        free(output);
        return;
    }

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
    stream.next_in = input;
    stream.avail_in = (uLong)input_len;
    stream.next_out = output;
    stream.avail_out = (uLong)output_cap;
    stream.adler = 1;
    deflate_rc = deflate_fn(&stream, Z_NO_FLUSH);
    end1_rc = end_fn(&stream);

    printf("%s: init2=%d deflate=%d end1=%d state_after_end=%p\n",
           label, init_rc, deflate_rc, end1_rc, (void *)stream.state);

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

    dlerror();
    mz_zlib_deflate_workspacesize_fn workspacesize_fn =
        (mz_zlib_deflate_workspacesize_fn)dlsym(handle, "mz_zlib_deflate_workspacesize");
    err = dlerror();
    if (err != NULL) {
        fprintf(stderr, "dlsym failed: %s\n", err);
        dlclose(zlib_handle);
        dlclose(handle);
        return 1;
    }

    dlerror();
    mz_zlib_deflateReset_fn reset_fn =
        (mz_zlib_deflateReset_fn)dlsym(handle, "mz_zlib_deflateReset");
    err = dlerror();
    if (err != NULL) {
        fprintf(stderr, "dlsym failed: %s\n", err);
        dlclose(zlib_handle);
        dlclose(handle);
        return 1;
    }

    dlerror();
    mz_zlib_deflateEnd_fn end_fn =
        (mz_zlib_deflateEnd_fn)dlsym(handle, "mz_zlib_deflateEnd");
    err = dlerror();
    if (err != NULL) {
        fprintf(stderr, "dlsym failed: %s\n", err);
        dlclose(zlib_handle);
        dlclose(handle);
        return 1;
    }

    dlerror();
    mz_crc32init_le_fn crc_init_fn =
        (mz_crc32init_le_fn)dlsym(handle, "mz_crc32init_le");
    err = dlerror();
    if (err != NULL) {
        fprintf(stderr, "dlsym failed: %s\n", err);
        dlclose(zlib_handle);
        dlclose(handle);
        return 1;
    }

    dlerror();
    mz_crc32_fn crc_fn = (mz_crc32_fn)dlsym(handle, "mz_crc32");
    err = dlerror();
    if (err != NULL) {
        fprintf(stderr, "dlsym failed: %s\n", err);
        dlclose(zlib_handle);
        dlclose(handle);
        return 1;
    }

    dlerror();
    mz_get_crc_table_fn get_crc_table_fn =
        (mz_get_crc_table_fn)dlsym(handle, "mz_get_crc_table");
    err = dlerror();
    if (err != NULL) {
        fprintf(stderr, "dlsym failed: %s\n", err);
        dlclose(zlib_handle);
        dlclose(handle);
        return 1;
    }

    z_stream stream;
    memset(&stream, 0, sizeof(stream));

    z_stream init2_bad_method_stream;
    unsigned char *init2_bad_method_workspace;
    memset(&init2_bad_method_stream, 0, sizeof(init2_bad_method_stream));

    z_stream init2_bad_window_stream;
    unsigned char *init2_bad_window_workspace;
    memset(&init2_bad_window_stream, 0, sizeof(init2_bad_window_stream));
    const unsigned char init2_ok_input[] = "stub dso init2 smoke test payload";

    init2_bad_method_workspace = allocate_workspace(workspacesize_fn, TEST_WINDOW_BITS,
                                                    TEST_MEM_LEVEL, NULL);
    init2_bad_window_workspace = allocate_workspace(workspacesize_fn, TEST_WINDOW_BITS,
                                                    TEST_MEM_LEVEL, NULL);
    if (init2_bad_method_workspace == NULL || init2_bad_window_workspace == NULL) {
        fprintf(stderr, "malloc failed for init2 workspace\n");
        free(init2_bad_method_workspace);
        free(init2_bad_window_workspace);
        dlclose(zlib_handle);
        dlclose(handle);
        return 1;
    }
    init2_bad_method_stream.workspace = init2_bad_method_workspace;
    init2_bad_window_stream.workspace = init2_bad_window_workspace;

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
        printf("mz_zlib_deflateReset(NULL) = %d\n", reset_fn(NULL));
    } else {
        printf("mz_zlib_deflateReset(NULL) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        printf("mz_zlib_deflateReset(&zero_stream) = %d\n", reset_fn(&stream));
    } else {
        printf("mz_zlib_deflateReset(&zero_stream) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        printf("mz_zlib_deflateEnd(NULL) = %d\n", end_fn(NULL));
    } else {
        printf("mz_zlib_deflateEnd(NULL) faulted with signal %d\n", (int)caught_signal);
    }

    caught_signal = 0;
    if (sigsetjmp(jump_env, 1) == 0) {
        printf("mz_zlib_deflateEnd(&zero_stream) = %d\n", end_fn(&stream));
    } else {
        printf("mz_zlib_deflateEnd(&zero_stream) faulted with signal %d\n", (int)caught_signal);
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

    large_repetitive = malloc(large_repetitive_len);
    large_mixed = malloc(large_mixed_len);
    if (large_repetitive == NULL || large_mixed == NULL) {
        fprintf(stderr, "malloc failed for extended payloads\n");
        free(large_repetitive);
        free(large_mixed);
        restore_fault_handlers(&old_segv, &old_bus);
        free(init2_bad_method_workspace);
        free(init2_bad_window_workspace);
        dlclose(zlib_handle);
        dlclose(handle);
        return 1;
    }

    fill_repetitive_payload(large_repetitive, large_repetitive_len);
    fill_mixed_payload(large_mixed, large_mixed_len);

    run_finish_roundtrip_case("level0-finish-small", fn, init2_fn,
                              workspacesize_fn,
                              compress_bound_fn, uncompress_fn, 0,
                              Z_DEFAULT_STRATEGY,
                              init2_ok_input, sizeof(init2_ok_input) - 1);
    run_finish_roundtrip_case("level1-finish-large-mixed", fn, init2_fn,
                              workspacesize_fn,
                              compress_bound_fn, uncompress_fn, 1,
                              Z_DEFAULT_STRATEGY,
                              large_mixed, large_mixed_len);
    run_finish_roundtrip_case("level6-finish-large-repeat", fn, init2_fn,
                              workspacesize_fn,
                              compress_bound_fn, uncompress_fn, 6,
                              Z_DEFAULT_STRATEGY,
                              large_repetitive, large_repetitive_len);
    run_finish_roundtrip_case("level6-finish-large-mixed", fn, init2_fn,
                              workspacesize_fn,
                              compress_bound_fn, uncompress_fn, 6,
                              Z_DEFAULT_STRATEGY,
                              large_mixed, large_mixed_len);
    run_finish_roundtrip_case("level6-finish-filtered", fn, init2_fn,
                              workspacesize_fn,
                              compress_bound_fn, uncompress_fn, 6,
                              Z_FILTERED,
                              large_mixed, large_mixed_len);
    run_finish_roundtrip_case("level6-finish-huffman-only", fn, init2_fn,
                              workspacesize_fn,
                              compress_bound_fn, uncompress_fn, 6,
                              Z_HUFFMAN_ONLY,
                              large_mixed, large_mixed_len);

    run_chunked_roundtrip_case("level1-chunked-no-flush", fn, init2_fn,
                               workspacesize_fn,
                               compress_bound_fn, uncompress_fn, 1,
                               Z_DEFAULT_STRATEGY,
                               Z_NO_FLUSH, large_mixed, large_mixed_len);
    run_chunked_roundtrip_case("level6-chunked-full-flush", fn, init2_fn,
                               workspacesize_fn,
                               compress_bound_fn, uncompress_fn, 6,
                               Z_DEFAULT_STRATEGY,
                               Z_FULL_FLUSH, large_repetitive, large_repetitive_len);
    run_chunked_roundtrip_case("level6-chunked-sync-flush", fn, init2_fn,
                               workspacesize_fn,
                               compress_bound_fn, uncompress_fn, 6,
                               Z_DEFAULT_STRATEGY,
                               Z_SYNC_FLUSH, large_mixed, large_mixed_len);
    run_chunked_roundtrip_case("level6-chunked-partial-flush", fn, init2_fn,
                               workspacesize_fn,
                               compress_bound_fn, uncompress_fn, 6,
                               Z_DEFAULT_STRATEGY,
                               Z_PARTIAL_FLUSH, large_repetitive, large_repetitive_len);
    run_tiny_out_roundtrip_case("level6-tiny-out", fn, init2_fn,
                                workspacesize_fn,
                                uncompress_fn, 6, Z_DEFAULT_STRATEGY,
                                large_repetitive, large_repetitive_len, 7);
    run_tiny_out_roundtrip_case("level1-tiny-out-huffman", fn, init2_fn,
                                workspacesize_fn,
                                uncompress_fn, 1, Z_HUFFMAN_ONLY,
                                large_mixed, large_mixed_len, 5);
    run_workspacesize_case("workspacesize-level6-exact", fn, init2_fn,
                           workspacesize_fn, uncompress_fn,
                           6, Z_DEFLATED, TEST_WINDOW_BITS, TEST_MEM_LEVEL,
                           Z_DEFAULT_STRATEGY,
                           large_repetitive, large_repetitive_len);
    run_workspacesize_case("workspacesize-level1-filtered-exact", fn, init2_fn,
                           workspacesize_fn, uncompress_fn,
                           1, Z_DEFLATED, TEST_WINDOW_BITS, TEST_MEM_LEVEL,
                           Z_FILTERED,
                           large_mixed, large_mixed_len);
    run_reset_reuse_case("reset-level6-reuse", fn, init2_fn, reset_fn,
                         workspacesize_fn, uncompress_fn,
                         6, Z_DEFAULT_STRATEGY,
                         large_repetitive, large_repetitive_len,
                         large_mixed, large_mixed_len);
    run_reset_reuse_case("reset-level1-huffman-reuse", fn, init2_fn, reset_fn,
                         workspacesize_fn, uncompress_fn,
                         1, Z_HUFFMAN_ONLY,
                         large_mixed, large_mixed_len,
                         init2_ok_input, sizeof(init2_ok_input) - 1);
    run_end_case("end-after-init", fn, init2_fn, end_fn, workspacesize_fn,
                 6, Z_DEFAULT_STRATEGY, large_repetitive, large_repetitive_len, 0);
    run_end_busy_case("end-after-busy", fn, init2_fn, end_fn, workspacesize_fn,
                      6, Z_DEFAULT_STRATEGY, large_repetitive, large_repetitive_len);
    run_end_case("end-after-finish", fn, init2_fn, end_fn, workspacesize_fn,
                 6, Z_DEFAULT_STRATEGY, large_repetitive, large_repetitive_len, 1);
    run_end_case("end-after-finish-huffman", fn, init2_fn, end_fn, workspacesize_fn,
                 1, Z_HUFFMAN_ONLY, large_mixed, large_mixed_len, 1);
    run_crc_cases(crc_init_fn, crc_fn, get_crc_table_fn);

    restore_fault_handlers(&old_segv, &old_bus);

    free(large_repetitive);
    free(large_mixed);
    free(init2_bad_method_workspace);
    free(init2_bad_window_workspace);
    dlclose(zlib_handle);
    dlclose(handle);
    return 0;
}
