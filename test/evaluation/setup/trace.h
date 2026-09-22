#ifndef VKSO_SETUP_TRACE_H
#define VKSO_SETUP_TRACE_H
#define _GNU_SOURCE
#include <dlfcn.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
#ifndef VKSO_SETUP_UNINSTRUMENTED
/* Buffer timestamps: no output, allocation or helper process in task timing. */
static struct { const char *name; uint64_t ns; } setup_events[128];
static unsigned setup_count;
static uint64_t setup_now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &t)) { perror("clock_gettime"); exit(2); }
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}
static void setup_mark(const char *name) {
    if (setup_count == 128) { fputs("setup event overflow\n", stderr); exit(2); }
    setup_events[setup_count].name = name;
    setup_events[setup_count++].ns = setup_now();
}
static void setup_flush(void) {
    for (unsigned i = 0; i < setup_count; ++i)
        printf("event\t%ld\t%s\t%" PRIu64 "\n", (long)getpid(), setup_events[i].name, setup_events[i].ns);
}
#else
static inline void setup_mark(const char *name) { (void)name; }
static inline void setup_flush(void) { }
#endif
static void *setup_dlopen(const char *path, int flags) {
    setup_mark("dlopen.begin");
    void *handle = dlopen(path, flags);
    setup_mark("dlopen.end");
    return handle;
}
static void *setup_dlsym(void *handle, const char *name) {
    setup_mark("dlsym.begin");
    void *symbol = dlsym(handle, name);
    setup_mark("dlsym.end");
    return symbol;
}
#endif
