#include "bench_common.h"
#include "data_tables.h"

#define STEP_DIRECT() do { \
    volatile uint64_t *p__ = &chain_values[idx & (PGOT_CHAIN_SLOTS - 1)]; \
    idx = *p__; \
} while (0)

#define STEP_PGOT() do { \
    uint64_t * volatile *slot__ = pgot_chain_table; \
    volatile uint64_t *p__ = slot__[idx & (PGOT_CHAIN_SLOTS - 1)]; \
    idx = *p__; \
} while (0)

#define DEFINE_BODY(kind, steps, body_steps) \
NOINLINE static uint64_t body_##kind##_##steps(uint64_t iterations) \
{ \
    uint64_t idx = 0x123u; \
    for (uint64_t it = 0; it < iterations; it++) { \
        body_steps \
        asm volatile("" : "+r"(idx) :: "memory"); \
    } \
    return idx; \
}

DEFINE_BODY(direct, 1, STEP_DIRECT();)
DEFINE_BODY(direct, 2, STEP_DIRECT(); STEP_DIRECT();)
DEFINE_BODY(direct, 4, STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT();)
DEFINE_BODY(direct, 8, STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT();)
DEFINE_BODY(direct, 16, STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT();)

DEFINE_BODY(pgot, 1, STEP_PGOT();)
DEFINE_BODY(pgot, 2, STEP_PGOT(); STEP_PGOT();)
DEFINE_BODY(pgot, 4, STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT();)
DEFINE_BODY(pgot, 8, STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT();)
DEFINE_BODY(pgot, 16, STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT();)

typedef uint64_t (*body_fn_t)(uint64_t);

struct sample_set {
    double *values;
    double median;
    double iqr;
};

static body_fn_t select_body(const char *variant, int steps)
{
    if (!strcmp(variant, "direct")) {
        switch (steps) {
        case 1: return body_direct_1;
        case 2: return body_direct_2;
        case 4: return body_direct_4;
        case 8: return body_direct_8;
        case 16: return body_direct_16;
        }
    } else {
        switch (steps) {
        case 1: return body_pgot_1;
        case 2: return body_pgot_2;
        case 4: return body_pgot_4;
        case 8: return body_pgot_8;
        case 16: return body_pgot_16;
        }
    }
    return NULL;
}

static double measure(body_fn_t fn, uint64_t iterations)
{
    uint64_t start = bench_rdtsc_start();
    uint64_t v = fn(iterations);
    uint64_t end = bench_rdtsc_end();
    bench_black_box_u64(v);
    return (double)(end - start) / (double)iterations;
}

static void compute_stats(struct sample_set *set, int repeats)
{
    double *sorted = calloc((size_t)repeats, sizeof(sorted[0]));
    if (!sorted) {
        perror("calloc");
        exit(1);
    }
    memcpy(sorted, set->values, (size_t)repeats * sizeof(sorted[0]));
    set->median = bench_median(sorted, repeats);
    set->iqr = bench_iqr(sorted, repeats);
    free(sorted);
}

static void alloc_sample_set(struct sample_set *set, int repeats)
{
    set->values = calloc((size_t)repeats, sizeof(set->values[0]));
    if (!set->values) {
        perror("calloc");
        exit(1);
    }
    set->median = 0.0;
    set->iqr = 0.0;
}

static void free_samples(struct sample_set *set)
{
    free(set->values);
    set->values = NULL;
}

static void collect_pair(body_fn_t dfn, body_fn_t pfn, const struct bench_config *cfg,
                         struct sample_set *direct, struct sample_set *pgot,
                         struct sample_set *delta)
{
    alloc_sample_set(direct, cfg->repeats);
    alloc_sample_set(pgot, cfg->repeats);
    alloc_sample_set(delta, cfg->repeats);

    (void)measure(dfn, cfg->iterations / 10 + 1);
    (void)measure(pfn, cfg->iterations / 10 + 1);
    for (int r = 0; r < cfg->repeats; r++) {
        if (r & 1) {
            pgot->values[r] = measure(pfn, cfg->iterations);
            direct->values[r] = measure(dfn, cfg->iterations);
        } else {
            direct->values[r] = measure(dfn, cfg->iterations);
            pgot->values[r] = measure(pfn, cfg->iterations);
        }
        delta->values[r] = pgot->values[r] - direct->values[r];
    }
    compute_stats(direct, cfg->repeats);
    compute_stats(pgot, cfg->repeats);
    compute_stats(delta, cfg->repeats);
}

static void run_pair(const struct bench_config *cfg, int steps)
{
    body_fn_t dfn = select_body("direct", steps);
    body_fn_t pfn = select_body("pgot", steps);
    struct sample_set direct;
    struct sample_set pgot;
    struct sample_set delta;

    collect_pair(dfn, pfn, cfg, &direct, &pgot, &delta);
    printf("layer1_data_dependent,%d,%" PRIu64 ",%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
           steps, cfg->iterations, cfg->repeats, direct.median, pgot.median,
           delta.median, delta.median / (double)steps, direct.median / (double)steps,
           pgot.median / (double)steps, delta.iqr, direct.iqr, pgot.iqr);
    free_samples(&direct);
    free_samples(&pgot);
    free_samples(&delta);
}

int main(int argc, char **argv)
{
    struct bench_config cfg;
    if (bench_parse_args(argc, argv, &cfg) != 0) {
        bench_usage(argv[0]);
        return 2;
    }
    bench_pin_cpu(cfg.cpu);
    init_data_tables();
    bench_print_env_header("layer1_data_dependent");
    bench_print_config_header(&cfg);
    printf("# sample_order=interleave\n");
    printf("# delta=median_of_paired_delta\n");
    printf("experiment,chain_steps,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,delta_cycles_per_step,direct_cycles_per_step,pgot_cycles_per_step,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter\n");

    const int steps[] = {1, 2, 4, 8, 16};
    for (size_t i = 0; i < sizeof(steps) / sizeof(steps[0]); i++)
        run_pair(&cfg, steps[i]);
    return 0;
}
