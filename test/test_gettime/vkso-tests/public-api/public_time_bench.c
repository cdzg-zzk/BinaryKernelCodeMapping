// SPDX-License-Identifier: GPL-2.0
#define _GNU_SOURCE
#include <cpuid.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <sys/prctl.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#define PROTOCOL "public-direct-v1"
#ifdef VKSO_BACKEND
#include "vkso_time.h"
#define API(name) vkso_##name
#define IMPLEMENTATION "vkso-direct"
#else
#define API(name) name
#define IMPLEMENTATION "native-libc"
#endif

static volatile uint64_t sink;
/* A batch invokes a dedicated loop: no per-call backend dispatch, timer,
 * output, PMU counter read, or dynamic symbol lookup. Return-status OR and
 * loop control are included symmetrically; no empty-loop subtraction. */
#define CLOCK_LOOP(name, operation, id) \
static int name(uint64_t n) { \
    struct timespec v = {0}; int error = 0; \
    for (uint64_t i = 0; i < n; ++i) error |= API(operation)(id, &v); \
    sink = (uint64_t)v.tv_sec ^ (uint64_t)v.tv_nsec; return error; \
}
CLOCK_LOOP(cgt_realtime, clock_gettime, CLOCK_REALTIME)
CLOCK_LOOP(cgt_monotonic, clock_gettime, CLOCK_MONOTONIC)
CLOCK_LOOP(cgt_raw, clock_gettime, CLOCK_MONOTONIC_RAW)
CLOCK_LOOP(cgt_boottime, clock_gettime, CLOCK_BOOTTIME)
CLOCK_LOOP(cgt_tai, clock_gettime, CLOCK_TAI)
CLOCK_LOOP(cgt_rt_coarse, clock_gettime, CLOCK_REALTIME_COARSE)
CLOCK_LOOP(cgt_mono_coarse, clock_gettime, CLOCK_MONOTONIC_COARSE)
CLOCK_LOOP(cgt_cpu, clock_gettime, CLOCK_PROCESS_CPUTIME_ID)
CLOCK_LOOP(cgt_alarm, clock_gettime, CLOCK_REALTIME_ALARM)
CLOCK_LOOP(cgr_realtime, clock_getres, CLOCK_REALTIME)
CLOCK_LOOP(cgr_coarse, clock_getres, CLOCK_REALTIME_COARSE)
CLOCK_LOOP(cgr_cpu, clock_getres, CLOCK_PROCESS_CPUTIME_ID)

static int gtod(uint64_t n)
{
    struct timeval v = {0}; int error = 0;
    for (uint64_t i = 0; i < n; ++i) error |= API(gettimeofday)(&v, NULL);
    sink = (uint64_t)v.tv_sec ^ (uint64_t)v.tv_usec;
    return error;
}
static int time_null(uint64_t n)
{
    time_t value = 0; int error = 0;
    for (uint64_t i = 0; i < n; ++i) {
        value = API(time)(NULL); error |= value == (time_t)-1;
    }
    sink = (uint64_t)value;
    return error;
}
static int time_pointer(uint64_t n)
{
    time_t value = 0, result = 0; int error = 0;
    for (uint64_t i = 0; i < n; ++i) {
        result = API(time)(&value); error |= result == (time_t)-1;
    }
    sink = (uint64_t)value ^ (uint64_t)result;
    return error;
}
static int cpu_both(uint64_t n)
{
    unsigned int cpu = 0, node = 0; int error = 0;
    for (uint64_t i = 0; i < n; ++i) error |= API(getcpu)(&cpu, &node);
    sink = cpu ^ node; return error;
}
static int cpu_null(uint64_t n)
{
    int error = 0;
    for (uint64_t i = 0; i < n; ++i) error |= API(getcpu)(NULL, NULL);
    return error;
}
struct operation { const char *name; int (*loop)(uint64_t); };
static const struct operation operations[] = {
    {"clock_gettime_realtime", cgt_realtime},
    {"clock_gettime_monotonic", cgt_monotonic},
    {"clock_gettime_monotonic_raw", cgt_raw},
    {"clock_gettime_boottime", cgt_boottime},
    {"clock_gettime_tai", cgt_tai},
    {"clock_gettime_realtime_coarse", cgt_rt_coarse},
    {"clock_gettime_monotonic_coarse", cgt_mono_coarse},
    {"clock_gettime_process_cpu_fallback", cgt_cpu},
    {"clock_gettime_realtime_alarm_fallback", cgt_alarm},
    {"clock_getres_realtime", cgr_realtime},
    {"clock_getres_realtime_coarse", cgr_coarse},
    {"clock_getres_process_cpu_fallback", cgr_cpu},
    {"gettimeofday_tv", gtod}, {"time_null", time_null},
    {"time_pointer", time_pointer}, {"getcpu_both", cpu_both},
    {"getcpu_null", cpu_null},
};
#define NOPS (sizeof(operations) / sizeof(operations[0]))

static uint64_t number(const char *s, uint64_t maximum)
{
    char *end = NULL;
    errno = 0;
    if (!*s || *s == '-' || *s == '+') goto invalid;
    unsigned long long value = strtoull(s, &end, 10);
    if (errno || *end || value > maximum) goto invalid;
    return value;
invalid:
    fprintf(stderr, "invalid numeric argument: %s\n", s); exit(2);
}
/* Target platform: x86-64 Intel with invariant TSC and RDTSCP.
 * LFENCE prevents following execution passing RDTSCP. The memory clobber
 * prevents compiler motion. AUX is recorded at BOTH ends, not sampled only
 * after the batch. This is elapsed TSC ticks, not retired core cycles. */
static inline uint64_t stamp(unsigned int *aux)
{
    unsigned int lo, hi, cpu;
    __asm__ volatile("rdtscp\n\tlfence" : "=a"(lo), "=d"(hi), "=c"(cpu)
                     : : "memory");
    *aux = cpu;
    return ((uint64_t)hi << 32) | lo;
}
static void require_tsc(void)
{
    unsigned int a, b, c, d;
    if (!__get_cpuid(0x80000001, &a, &b, &c, &d) || !(d & (1U << 27)) ||
        !__get_cpuid(0x80000007, &a, &b, &c, &d) || !(d & (1U << 8))) {
        fputs("RDTSCP and invariant TSC required; no timing fallback\n", stderr);
        exit(2);
    }
}
static int check_public_api(const char *selected)
{
    struct timespec ts;
    for (size_t i = 0; i < NOPS; ++i) {
        if (selected && strcmp(selected, operations[i].name)) continue;
        if (operations[i].loop(1)) {
            fprintf(stderr, "API failed: %s errno=%d\n", operations[i].name, errno);
            return -1;
        }
    }
    errno = 0;
    if (API(clock_gettime)((clockid_t)-1, &ts) != -1 || errno != EINVAL)
        return -1;
    errno = 0;
    if (API(clock_getres)((clockid_t)-1, &ts) != -1 || errno != EINVAL)
        return -1;
    if (API(clock_getres)(CLOCK_REALTIME, NULL)) return -1;
    if (API(clock_gettime)(CLOCK_MONOTONIC, &ts) ||
        ts.tv_nsec < 0 || ts.tv_nsec >= 1000000000L) return -1;
    struct timeval tv;
    if (API(gettimeofday)(&tv, NULL) || tv.tv_usec < 0 || tv.tv_usec >= 1000000L)
        return -1;
    time_t seconds;
    time_t result = API(time)(&seconds);
    if (result != seconds) return -1;
    return 0;
}
/* Diagnostic ONLY: deny time syscalls, then exercise the expected fast APIs.
 * This is a separate process from every timed process. A syscall mock cannot
 * pass this check and thus cannot masquerade as target fast-path evidence. */
static int check_fastpath(void)
{
#define DENY(nr) BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, nr, 0, 1), \
                 BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)
    struct sock_filter code[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        DENY(__NR_clock_gettime), DENY(__NR_clock_getres),
        DENY(__NR_gettimeofday), DENY(__NR_time), DENY(__NR_getcpu),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    };
#undef DENY
    struct sock_fprog program = { .len = sizeof(code) / sizeof(code[0]), .filter = code };
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) ||
        prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &program)) {
        perror("fastpath seccomp installation"); return -1;
    }
    struct timespec forbidden;
    errno = 0;
    if (syscall(SYS_clock_gettime, CLOCK_MONOTONIC, &forbidden) != -1 || errno != EPERM) {
        fputs("syscall-denial positive control failed\n", stderr);
        return -1;
    }
    for (size_t i = 0; i < NOPS; ++i) {
        if (strstr(operations[i].name, "fallback")) continue;
        if (operations[i].loop(1)) {
            fprintf(stderr, "syscall-denial failure: %s\n", operations[i].name);
            return -1;
        }
    }
    fputs("syscall_denial_fastpath=PASS\n", stderr);
    return 0;
}

int main(int argc, char **argv)
{
    uint64_t iterations = 500000, warmup = 10000, repeats = 31, offset = 0;
    int cpu = -1, check_only = 0, fastpath = 0;
    const char *selected = NULL;
    for (int i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--check-fastpath")) { fastpath = 1; continue; }
        if (!strcmp(argv[i], "--check")) { check_only = 1; continue; }
        if (!strcmp(argv[i], "--help")) {
            puts("--cpu N --iterations N --warmup N --repeats N --offset N [--check] [--api NAME]");
            return 0;
        }
        if (i + 1 == argc) { fputs("missing option value\n", stderr); return 2; }
        const char *option = argv[i], *value = argv[++i];
        if (!strcmp(option, "--api")) selected = value;
        else if (!strcmp(option, "--cpu")) cpu = (int)number(value, CPU_SETSIZE - 1);
        else if (!strcmp(option, "--iterations")) iterations = number(value, 1000000000);
        else if (!strcmp(option, "--warmup")) warmup = number(value, 1000000000);
        else if (!strcmp(option, "--repeats")) repeats = number(value, 100000);
        else if (!strcmp(option, "--offset")) offset = number(value, 1000000);
        else { fprintf(stderr, "unknown option: %s\n", option); return 2; }
    }
    if (!iterations || !repeats || cpu < 0) {
        fputs("positive iterations/repeats and explicit --cpu are required\n", stderr);
        return 2;
    }
    if (selected) {
        int found = 0;
        for (size_t i = 0; i < NOPS; ++i)
            if (!strcmp(selected, operations[i].name)) found = 1;
        if (!found) { fputs("unknown API name\n", stderr); return 2; }
    }
    cpu_set_t mask;
    CPU_ZERO(&mask); CPU_SET(cpu, &mask);
    if (sched_setaffinity(0, sizeof(mask), &mask)) { perror("affinity"); return 2; }
    if (getenv("LD_PRELOAD") || getenv("LD_AUDIT")) {
        fputs("LD_PRELOAD/LD_AUDIT are forbidden in the public benchmark\n", stderr);
        return 2;
    }
#ifdef VKSO_BACKEND
    if (vkso_time_init()) { perror("vkso_time_init"); return 2; }
#else
    if (!getauxval(AT_SYSINFO_EHDR)) {
        fputs("native baseline requires a kernel-provided vDSO\n", stderr); return 2;
    }
#endif
    if (check_public_api(selected)) { fputs("public_api_check=FAIL\n", stderr); return 1; }
    fprintf(stderr, "protocol=%s\nimplementation=%s\npublic_api_check=PASS\n",
            PROTOCOL, IMPLEMENTATION);
    if (fastpath) return check_fastpath() ? 1 : 0;
    if (check_only) return 0;
    require_tsc();
    puts("protocol,implementation,api,repeat,iterations,tsc_cycles_total,tsc_cycles_per_call,aux_start,aux_end,status");
    for (uint64_t r = 0; r < repeats; ++r) {
        for (size_t j = 0; j < NOPS; ++j) {
            size_t index = (j + r + offset) % NOPS;
            if (selected && strcmp(selected, operations[index].name)) continue;
            if (warmup && operations[index].loop(warmup)) {
                fputs("warmup failure\n", stderr); return 1;
            }
            unsigned int first, last;
            uint64_t start = stamp(&first);
            int error = operations[index].loop(iterations);
            uint64_t end = stamp(&last);
            const char *status = error ? "API_ERROR" :
                first != last ? "MIGRATED" : end <= start ? "BAD_TSC" : "OK";
            uint64_t elapsed = end > start ? end - start : 0;
            printf("%s,%s,%s,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%.9f,%u,%u,%s\n",
                   PROTOCOL, IMPLEMENTATION, operations[index].name, r + offset,
                   iterations, elapsed, (double)elapsed / iterations, first, last, status);
            /* Preserve the rejected sample and fail the collection. No resampling
             * until a favorable batch happens to appear. */
            if (strcmp(status, "OK")) return 1;
        }
    }
    return ferror(stdout) ? 1 : 0;
}
