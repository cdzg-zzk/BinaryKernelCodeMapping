/* Diagnostic only: complete archived carrier code, controlled stable state. */
#define _GNU_SOURCE
#include <assert.h>
#include <dlfcn.h>
#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <x86intrin.h>
#include "../vkso-tests/functional/vkso_abi.h"

static uint64_t stamp(unsigned *aux)
{
    uint64_t value = __rdtscp(aux);
    _mm_lfence();
    return value;
}

int main(int argc, char **argv)
{
    assert(argc == 5);
    const char *path = argv[1];
    unsigned cpu = strtoul(argv[2], NULL, 0), rounds = strtoul(argv[3], NULL, 0);
    unsigned count = strtoul(argv[4], NULL, 0);
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    assert(sched_setaffinity(0, sizeof(set), &set) == 0);
    void *lib = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!lib) { fprintf(stderr, "%s\n", dlerror()); return 2; }
    struct vkso_shared_data *(*get_shared)(void) = dlsym(lib, "__vkso_shared_data");
    int (*bind)(const struct vkso_mm_data *, void *, void *) = dlsym(lib, "__vkso_bind_context");
    int (*coarse)(int, struct vkso_time_value *) = dlsym(lib, "__vkso_clock_gettime");
    int (*gtod)(struct vkso_timeval *, struct vkso_timezone *) = dlsym(lib, "__vkso_gettimeofday");
    assert(get_shared && bind && coarse && gtod);
    struct vkso_shared_data *shared = get_shared();
    assert(mprotect(shared, 4096, PROT_READ | PROT_WRITE) == 0);
    memset(shared, 0, 4096);
    shared->abi_version = 11;
    shared->state.cycles.clock_mode = 1;
    shared->state.realtime_base.sec = 1000;
    shared->state.timezone.minuteswest = 123;
    shared->state.timezone.dsttime = 4;
    struct vkso_mm_data mm = {.abi_version = 3};
    assert(bind(&mm, NULL, NULL) == 0);
    unsigned checks = 0;
    for (unsigned i = 0; i < 10000; i++) {
        shared->state.realtime_coarse.sec = i;
        shared->state.realtime_coarse.nsec = (i * 372193UL) % 1000000000;
        shared->state.monotonic_coarse.sec = i + 13;
        shared->state.monotonic_coarse.nsec = (i * 1271237UL) % 1000000000;
        mm.monotonic_offset.sec = (int)(i % 301) - 150;
        mm.monotonic_offset.nsec = (i * 891121UL) % 1000000000;
        for (unsigned mode = 0; mode < 3; mode++) {
            mm.clock_mask = mode == 2 ? 1U << 6 : 0;
            assert(bind(mode ? &mm : NULL, NULL, NULL) == 0);
            for (int clock = 5; clock <= 6; clock++) {
                struct vkso_time_value value;
                struct vkso_time_value expected = clock == 5 ? shared->state.realtime_coarse : shared->state.monotonic_coarse;
                if (clock == 6 && mode == 2) {
                    expected.sec += mm.monotonic_offset.sec;
                    expected.nsec += mm.monotonic_offset.nsec;
                    if (expected.nsec >= 1000000000) { expected.nsec -= 1000000000; expected.sec++; }
                }
                assert(coarse(clock, &value) == 0);
                assert(value.sec == expected.sec && value.nsec == expected.nsec);
                checks++;
            }
        }
    }
    assert(gtod(NULL, NULL) == 0);
    struct vkso_timezone tz;
    assert(gtod(NULL, &tz) == 0 && tz.minuteswest == 123 && tz.dsttime == 4);
    assert(mprotect(shared, 4096, PROT_READ) == 0);
    fprintf(stderr, "checks=%u coarse_address=%p gtod_address=%p shared=%p\n", checks + 2, coarse, gtod, shared);
    puts("round,scenario,iterations,tsc_ticks,cpu_start,cpu_end");
    const char *names[] = {"gettimeofday_null", "gettimeofday_timezone", "gettimeofday_tv",
                          "gettimeofday_both", "realtime_coarse", "monotonic_coarse_root", "monotonic_coarse_namespace"};
    for (unsigned round = 0; round < rounds; round++) {
        for (unsigned scenario = 0; scenario < 7; scenario++) {
            struct vkso_time_value value;
            struct vkso_timeval tv;
            mm.clock_mask = scenario == 6 ? 1U << 6 : 0;
            assert(bind(&mm, NULL, NULL) == 0);
            unsigned a = 0, b = 0;
            uint64_t start, stop;
            for (unsigned warm = 0; warm < 2; warm++) {
                unsigned n = warm ? count : 10000;
                /* Dispatch outside each timed body, as in the public benchmark. */
                switch (scenario) {
                case 0:
                    start = stamp(&a);
                    for (unsigned j = 0; j < n; j++) gtod(NULL, NULL);
                    stop = stamp(&b); break;
                case 1:
                    start = stamp(&a);
                    for (unsigned j = 0; j < n; j++) gtod(NULL, &tz);
                    stop = stamp(&b); break;
                case 2:
                    start = stamp(&a);
                    for (unsigned j = 0; j < n; j++) gtod(&tv, NULL);
                    stop = stamp(&b); break;
                case 3:
                    start = stamp(&a);
                    for (unsigned j = 0; j < n; j++) gtod(&tv, &tz);
                    stop = stamp(&b); break;
                case 4:
                    start = stamp(&a);
                    for (unsigned j = 0; j < n; j++) coarse(5, &value);
                    stop = stamp(&b); break;
                default:
                    start = stamp(&a);
                    for (unsigned j = 0; j < n; j++) coarse(6, &value);
                    stop = stamp(&b); break;
                }
                assert(a == b);
                if (warm) printf("%u,%s,%u,%" PRIu64 ",%u,%u\n", round, names[scenario], n, stop-start, a, b);
            }
        }
    }
    assert(dlclose(lib) == 0);
    return 0;
}
