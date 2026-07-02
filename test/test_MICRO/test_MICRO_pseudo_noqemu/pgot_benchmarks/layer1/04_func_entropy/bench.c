#include "bench_common.h"
#include "targets.h"

#define TRACE_LEN 65536u

static uint8_t target_trace[TRACE_LEN] ALIGNED64;

static void init_high_entropy_trace(unsigned target_count)
{
    uint32_t x = 0x12345678u ^ (target_count * 0x9e3779b9u);
    for (size_t i = 0; i < TRACE_LEN; i++) {
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        target_trace[i] = (uint8_t)(x & (target_count - 1));
    }
    compiler_barrier();
}

NOINLINE static uint64_t body_pgot_entropy(uint64_t iterations)
{
    uint64_t x = 0xabcdef9876543210ULL;
    bench_fn_t volatile *slot = pgot_func_table;
    for (uint64_t it = 0; it < iterations; it++) {
        uint8_t idx = target_trace[it & (TRACE_LEN - 1)];
        bench_fn_t f = slot[idx];
        x = f(x + it);
        asm volatile("" : "+r"(x) :: "memory");
    }
    return x;
}

static double measure(uint64_t iterations)
{
    uint64_t start = bench_rdtsc_start();
    uint64_t v = body_pgot_entropy(iterations);
    uint64_t end = bench_rdtsc_end();
    bench_black_box_u64(v);
    return (double)(end - start) / (double)iterations;
}

static void run_case(const struct bench_config *cfg, unsigned target_count)
{
    init_high_entropy_trace(target_count);

    double *samples = calloc((size_t)cfg->repeats, sizeof(samples[0]));
    if (!samples) {
        perror("calloc");
        exit(1);
    }

    (void)measure(cfg->iterations / 10 + 1);
    for (int r = 0; r < cfg->repeats; r++)
        samples[r] = measure(cfg->iterations);

    double med = bench_median(samples, cfg->repeats);
    double iqr = bench_iqr(samples, cfg->repeats);
    printf("layer1_func_entropy,pgot_high_entropy,%u,%" PRIu64 ",%d,%u,%.6f,%.6f\n",
           target_count, cfg->iterations, cfg->repeats, TRACE_LEN, med, iqr);
    free(samples);
}

int main(int argc, char **argv)
{
    struct bench_config cfg;
    if (bench_parse_args(argc, argv, &cfg) != 0) {
        bench_usage(argv[0]);
        return 2;
    }
    bench_pin_cpu(cfg.cpu);
    init_pgot_func_table();
    bench_print_env_header("layer1_func_entropy");
    bench_print_config_header(&cfg);
    printf("experiment,variant,target_count,iterations,repeats,trace_len,cycles_per_call,iqr_cycles_per_call\n");

    const char *only_k = getenv("PGOT_TARGET_COUNT");
    if (only_k) {
        unsigned k = (unsigned)strtoul(only_k, NULL, 0);
        if (!(k == 1 || k == 2 || k == 4 || k == 8 || k == 16)) {
            fprintf(stderr, "PGOT_TARGET_COUNT must be one of 1,2,4,8,16\n");
            return 2;
        }
        run_case(&cfg, k);
        return 0;
    }

    const unsigned counts[] = {1, 2, 4, 8, 16};
    for (size_t i = 0; i < sizeof(counts) / sizeof(counts[0]); i++)
        run_case(&cfg, counts[i]);
    return 0;
}
