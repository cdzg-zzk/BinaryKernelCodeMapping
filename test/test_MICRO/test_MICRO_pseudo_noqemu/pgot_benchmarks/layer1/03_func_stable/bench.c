#include "bench_common.h"
#include "targets.h"

#define STEP_DIRECT() do { \
    x = target_0(x); \
} while (0)

#define STEP_PGOT() do { \
    bench_fn_t f__ = slot[0]; \
    x = f__(x); \
} while (0)

#define DEFINE_DIRECT_BODY(events, body_steps) \
NOINLINE static uint64_t body_direct_##events(uint64_t iterations) \
{ \
    uint64_t x = 0x123456789abcdef0ULL; \
    for (uint64_t it = 0; it < iterations; it++) { \
        body_steps \
        asm volatile("" : "+r"(x) :: "memory"); \
    } \
    return x; \
}

#define DEFINE_PGOT_BODY(events, body_steps) \
NOINLINE static uint64_t body_pgot_##events(uint64_t iterations) \
{ \
    uint64_t x = 0x123456789abcdef0ULL; \
    bench_fn_t volatile *slot = pgot_func_table; \
    for (uint64_t it = 0; it < iterations; it++) { \
        body_steps \
        asm volatile("" : "+r"(x) :: "memory"); \
    } \
    return x; \
}

DEFINE_DIRECT_BODY(1, STEP_DIRECT();)
DEFINE_DIRECT_BODY(2, STEP_DIRECT(); STEP_DIRECT();)
DEFINE_DIRECT_BODY(4, STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT();)
DEFINE_DIRECT_BODY(8, STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT();)
DEFINE_DIRECT_BODY(16, STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT(); STEP_DIRECT();)

DEFINE_PGOT_BODY(1, STEP_PGOT();)
DEFINE_PGOT_BODY(2, STEP_PGOT(); STEP_PGOT();)
DEFINE_PGOT_BODY(4, STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT();)
DEFINE_PGOT_BODY(8, STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT();)
DEFINE_PGOT_BODY(16, STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT(); STEP_PGOT();)

typedef uint64_t (*body_fn_t)(uint64_t);

struct sample_set {
    double *values;
    double median;
    double iqr;
};

static body_fn_t select_body(const char *variant, int events)
{
    if (!strcmp(variant, "direct")) {
        switch (events) {
        case 1: return body_direct_1;
        case 2: return body_direct_2;
        case 4: return body_direct_4;
        case 8: return body_direct_8;
        case 16: return body_direct_16;
        }
    } else {
        switch (events) {
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

static void run_pair(const struct bench_config *cfg, int events)
{
    body_fn_t dfn = select_body("direct", events);
    body_fn_t pfn = select_body("pgot", events);
    struct sample_set direct;
    struct sample_set pgot;
    struct sample_set delta;

    collect_pair(dfn, pfn, cfg, &direct, &pgot, &delta);
    printf("layer1_func_stable,%d,1,%" PRIu64 ",%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
           events, cfg->iterations, cfg->repeats, direct.median, pgot.median,
           delta.median, delta.median / (double)events, direct.median / (double)events,
           pgot.median / (double)events, delta.iqr, direct.iqr, pgot.iqr);
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
    init_pgot_func_table();
    bench_print_env_header("layer1_func_stable");
    bench_print_config_header(&cfg);
    printf("# target_pattern=stable\n");
    printf("# sample_order=interleave\n");
    printf("# delta=median_of_paired_delta\n");
    printf("experiment,pgot_events,target_count,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,delta_cycles_per_event,direct_cycles_per_event,pgot_cycles_per_event,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter\n");
    const char *only_events = getenv("PGOT_EVENTS");
    if (only_events) {
        int events = atoi(only_events);
        if (!(events == 1 || events == 2 || events == 4 || events == 8 || events == 16)) {
            fprintf(stderr, "PGOT_EVENTS must be one of 1,2,4,8,16\n");
            return 2;
        }
        run_pair(&cfg, events);
        return 0;
    }

    const int events[] = {1, 2, 4, 8, 16};
    for (size_t i = 0; i < sizeof(events) / sizeof(events[0]); i++)
        run_pair(&cfg, events[i]);
    return 0;
}
