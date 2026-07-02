#ifndef PGOT_BENCH_COMMON_H
#define PGOT_BENCH_COMMON_H

#define _GNU_SOURCE

#include <errno.h>
#include <inttypes.h>
#include <sched.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <x86intrin.h>

#ifndef CACHELINE
#define CACHELINE 64
#endif

#define NOINLINE __attribute__((noinline))
#define USED __attribute__((used))
#define NOIPA __attribute__((noipa))
#define ALIGNED64 __attribute__((aligned(64)))

static volatile uint64_t g_sink_u64;

struct bench_config {
    uint64_t iterations;
    int repeats;
    int cpu;
};

static inline void compiler_barrier(void)
{
    asm volatile("" ::: "memory");
}

static inline uint64_t bench_rdtsc_start(void)
{
    unsigned aux;
    _mm_lfence();
    return __rdtscp(&aux);
}

static inline uint64_t bench_rdtsc_end(void)
{
    unsigned aux;
    uint64_t t = __rdtscp(&aux);
    _mm_lfence();
    return t;
}

static inline void bench_black_box_u64(uint64_t v)
{
    g_sink_u64 ^= v;
    compiler_barrier();
}

static inline int bench_pin_cpu(int cpu)
{
    if (cpu < 0)
        return 0;

    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0) {
        fprintf(stderr, "warning: failed to pin cpu %d: %s\n", cpu, strerror(errno));
        return -1;
    }
    return 0;
}

static int cmp_double(const void *a, const void *b)
{
    double da = *(const double *)a;
    double db = *(const double *)b;
    return (da > db) - (da < db);
}

static inline double bench_median(double *values, int n)
{
    qsort(values, (size_t)n, sizeof(values[0]), cmp_double);
    if (n & 1)
        return values[n / 2];
    return (values[n / 2 - 1] + values[n / 2]) / 2.0;
}

static inline double bench_iqr(double *sorted_values, int n)
{
    if (n < 4)
        return 0.0;
    double q1 = sorted_values[n / 4];
    double q3 = sorted_values[(3 * n) / 4];
    return q3 - q1;
}

static inline void bench_default_config(struct bench_config *cfg)
{
    cfg->iterations = 1000000ULL;
    cfg->repeats = 31;
    cfg->cpu = -1;
}

static inline void bench_usage(const char *prog)
{
    fprintf(stderr,
            "usage: %s [-n iterations] [-r repeats] [-c cpu]\n"
            "  -n iterations  inner-loop iterations, default 1000000\n"
            "  -r repeats     independent repetitions, default 31\n"
            "  -c cpu         pin process to one CPU, default disabled\n",
            prog);
}

static inline int bench_parse_args(int argc, char **argv, struct bench_config *cfg)
{
    bench_default_config(cfg);

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-n") || !strcmp(argv[i], "--iterations")) {
            if (++i >= argc)
                return -1;
            cfg->iterations = strtoull(argv[i], NULL, 0);
        } else if (!strcmp(argv[i], "-r") || !strcmp(argv[i], "--repeats")) {
            if (++i >= argc)
                return -1;
            cfg->repeats = atoi(argv[i]);
        } else if (!strcmp(argv[i], "-c") || !strcmp(argv[i], "--cpu")) {
            if (++i >= argc)
                return -1;
            cfg->cpu = atoi(argv[i]);
        } else if (!strcmp(argv[i], "-h") || !strcmp(argv[i], "--help")) {
            bench_usage(argv[0]);
            exit(0);
        } else {
            return -1;
        }
    }

    if (cfg->iterations == 0 || cfg->repeats <= 0)
        return -1;
    return 0;
}

static inline void bench_print_env_header(const char *experiment)
{
    printf("# experiment=%s\n", experiment);
#ifdef RETPOLINE_BUILD
    printf("# build=retpoline\n");
#else
    printf("# build=no_retpoline\n");
#endif
    printf("# timing=rdtscp_lfence_median\n");
}

static inline void bench_print_config_header(const struct bench_config *cfg)
{
    printf("# iterations=%" PRIu64 "\n", cfg->iterations);
    printf("# repeats=%d\n", cfg->repeats);
    if (cfg->cpu >= 0)
        printf("# cpu=%d\n", cfg->cpu);
    else
        printf("# cpu=unpinned\n");
}

static inline double bench_run_u64(uint64_t (*fn)(uint64_t), uint64_t iterations)
{
    uint64_t x = 0x9e3779b97f4a7c15ULL;
    uint64_t start = bench_rdtsc_start();
    for (uint64_t i = 0; i < iterations; i++) {
        x = fn(x + i);
    }
    uint64_t end = bench_rdtsc_end();
    bench_black_box_u64(x);
    return (double)(end - start) / (double)iterations;
}

#endif
