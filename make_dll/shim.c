#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>

/*
 * User-space shim implementations for kernel-only APIs.
 * Functions listed in shim.txt are provided here so that build_PIC_so.py
 * can link dependent modules against libshim.so instead of kernel space.
 * This is a pragmatic stand-in: semantics are matched approximately using
 * libc/syscall equivalents; avoid putting privileged-only or unshimmable
 * symbols here.
 */

typedef unsigned long gfp_t;

struct timespec64 {
    long tv_sec;
    long tv_nsec;
};

static uint64_t timespec_to_ns(const struct timespec* ts) {
    return ((uint64_t)ts->tv_sec * 1000000000ull) + (uint64_t)ts->tv_nsec;
}

void* kmalloc(size_t size, gfp_t flags) {
    (void)flags;
    return malloc(size);
}

void kfree(const void* ptr) {
    free((void*)ptr);
}

char* kstrdup(const char* s, gfp_t flags) {
    (void)flags;
    return s ? strdup(s) : NULL;
}

int printk(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    int n = vprintf(fmt, ap);
    va_end(ap);
    return n;
}

int64_t ktime_get(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)timespec_to_ns(&ts);
}

uint64_t ktime_get_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return timespec_to_ns(&ts);
}

int ktime_get_real_ts64(struct timespec64* ts64) {
    if (!ts64) return -1;
    struct timespec ts;
    if (clock_gettime(CLOCK_REALTIME, &ts) != 0) {
        return -1;
    }
    ts64->tv_sec = ts.tv_sec;
    ts64->tv_nsec = ts.tv_nsec;
    return 0;
}

int do_gettimeofday(struct timeval* tv) {
    return gettimeofday(tv, NULL);
}
