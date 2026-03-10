#include <dlfcn.h>
#include <signal.h>
#include <stdio.h>
#include <setjmp.h>
#include <string.h>

#include "deflate_types.h"

#define LIB_PATH "/home/zzk/BinaryKernelCodeMapping/test/test_zlib/libmz_zlib_deflate.so"
#define Z_NO_FLUSH 0
#define Z_FINISH 5
#define INIT_STATE 42
#define BUSY_STATE 113

typedef int (*mz_zlib_deflate_fn)(z_streamp strm, int flush);

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

int main(void)
{
    void *handle = dlopen(LIB_PATH, RTLD_NOW);
    if (handle == NULL) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
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

    restore_fault_handlers(&old_segv, &old_bus);

    dlclose(handle);
    return 0;
}
