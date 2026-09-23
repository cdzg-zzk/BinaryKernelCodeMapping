// SPDX-License-Identifier: GPL-2.0
/* Reuse namespace lifecycle/oracles, but bind to the real PUBLIC clock API.
 * Diagnostic executable only; never included in formal READ timing. */
#define VKSO_BACKEND
#define main private_matrix_main_unused
#include "../../functional/abi_matrix.c"
#undef main
#include "../vkso_time.h"
#include <limits.h>
#include <inttypes.h>

struct diagnostic_stamp { uint64_t ticks; unsigned aux; };
static struct diagnostic_stamp diagnostic_stamp(void)
{
    unsigned lo, hi, aux;
    __asm__ volatile("lfence\n\trdtscp\n\tlfence"
                     : "=a"(lo), "=d"(hi), "=c"(aux) : : "memory");
    return (struct diagnostic_stamp){((uint64_t)hi << 32) | lo, aux};
}
static void error_samples(void)
{
    const clockid_t ids[] = {-1, INT_MAX};
    const unsigned iterations = 100000;
    puts("api,clock_id,round,iterations,tsc_ticks,ticks_per_call,aux_start,aux_end");
    for (unsigned api = 0; api < 2; ++api)
        for (unsigned id = 0; id < 2; ++id)
            for (int round = -1; round < 11; ++round) {
                struct timespec value;
                unsigned bad = 0;
                struct diagnostic_stamp start = diagnostic_stamp();
                for (unsigned i = 0; i < iterations; ++i) {
                    errno = EBUSY;
                    int ret = api ? clock_getres(ids[id], &value) : clock_gettime(ids[id], &value);
                    bad |= ret != -1 || errno != EINVAL;
                }
                struct diagnostic_stamp end = diagnostic_stamp();
                if (bad || start.aux != end.aux) fail("error diagnostic semantics/migration");
                if (round >= 0)
                    printf("%s,%d,%d,%u,%" PRIu64 ",%.9f,%u,%u\n",
                           api ? "clock_getres" : "clock_gettime", ids[id], round,
                           iterations, end.ticks-start.ticks,
                           (double)(end.ticks-start.ticks)/iterations, start.aux, end.aux);
            }
}
/* Called in root, exec-child and setns paths, including syscall-denial children.
 * The namespace oracle still obtains clock_gettime through the public symbol.
 */
static int public_namespace_clock(clockid_t clock, struct timespec *value)
{
    struct timespec resolution, expected;
    struct timeval before, actual, after;
    time_t lo, stored, now, hi;
    unsigned cpu, node, expected_cpu, expected_node;
    if (syscall(SYS_clock_getres, clock, &expected)) fail("namespace getres oracle");
    errno = EBUSY;
    if (clock_getres(clock, &resolution) || errno != EBUSY ||
        resolution.tv_sec != expected.tv_sec || resolution.tv_nsec != expected.tv_nsec)
        fail("namespace public getres");
    if (syscall(SYS_gettimeofday, &before, NULL) || gettimeofday(&actual, NULL) ||
        syscall(SYS_gettimeofday, &after, NULL) ||
        actual.tv_sec * INT64_C(1000000) + actual.tv_usec < before.tv_sec * INT64_C(1000000) + before.tv_usec ||
        actual.tv_sec * INT64_C(1000000) + actual.tv_usec > after.tv_sec * INT64_C(1000000) + after.tv_usec)
        fail("namespace public gettimeofday");
    lo = syscall(SYS_time, NULL); now = time(&stored); hi = syscall(SYS_time, NULL);
    if (now != stored || now < lo || now > hi) fail("namespace public time");
    if (getcpu(&cpu, &node) || syscall(SYS_getcpu, &expected_cpu, &expected_node, NULL) ||
        cpu != expected_cpu || node != expected_node) fail("namespace public getcpu");
    errno = EBUSY;
    int result = clock_gettime(clock, value);
    if (result || errno != EBUSY) fail("namespace public clock_gettime/errno");
    return result;
}
static void public_init(void)
{
    if (!getauxval(AT_VKSO_MM_DATA) || getauxval(AT_SYSINFO_EHDR))
        fail("requires VKSO target environment");
    if (vkso_time_init()) fail("public API initialization");
    backend.name = "public-vkso";
    backend.clock_gettime = public_namespace_clock;
    backend.clock_getres = clock_getres;
}
int main(int argc, char **argv)
{
    public_init();
    if (argc == 3 && !strcmp(argv[1], "--namespace-exec-child")) {
        char *end;
        errno = 0;
        long fd = strtol(argv[2], &end, 10);
        if (errno || *end || fd < 0 || fd > INT_MAX) fail("namespace child fd");
        return namespace_exec_child((int)fd);
    }
    if (argc == 2 && !strcmp(argv[1], "--namespace")) {
        check_namespace_lifecycle();
        puts("public_namespace=PASS (public clock_gettime; exec/setns/offset/frozen/fast-path)");
        return 0;
    }
    if (argc == 2 && !strcmp(argv[1], "--errors")) { error_samples(); return 0; }
    fail("usage: public-target --namespace|--errors");
    return 1;
}
