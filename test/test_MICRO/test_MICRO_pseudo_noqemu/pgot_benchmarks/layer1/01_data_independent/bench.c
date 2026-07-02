#include "bench_common.h"
#include "data_tables.h"

#define LOAD_DIRECT(i) do { \
    volatile uint64_t *p__ = &direct_values[(i) & (PGOT_DATA_SLOTS - 1)]; \
    acc += *p__; \
} while (0)

#define LOAD_PGOT(i) do { \
    uint64_t * volatile *slot__ = pgot_data_table; \
    volatile uint64_t *p__ = slot__[(i) & (PGOT_DATA_SLOTS - 1)]; \
    acc += *p__; \
} while (0)

#define DEFINE_BODY(kind, events, loads) \
NOINLINE static uint64_t body_##kind##_##events(uint64_t iterations) \
{ \
    uint64_t acc = 0xabcdef1234567890ULL; \
    for (uint64_t it = 0; it < iterations; it++) { \
        loads \
        asm volatile("" : "+r"(acc) :: "memory"); \
    } \
    return acc; \
}

DEFINE_BODY(direct, 1, LOAD_DIRECT(0);)
DEFINE_BODY(direct, 2, LOAD_DIRECT(0); LOAD_DIRECT(1);)
DEFINE_BODY(direct, 4, LOAD_DIRECT(0); LOAD_DIRECT(1); LOAD_DIRECT(2); LOAD_DIRECT(3);)
DEFINE_BODY(direct, 8, LOAD_DIRECT(0); LOAD_DIRECT(1); LOAD_DIRECT(2); LOAD_DIRECT(3); LOAD_DIRECT(4); LOAD_DIRECT(5); LOAD_DIRECT(6); LOAD_DIRECT(7);)
DEFINE_BODY(direct, 16, LOAD_DIRECT(0); LOAD_DIRECT(1); LOAD_DIRECT(2); LOAD_DIRECT(3); LOAD_DIRECT(4); LOAD_DIRECT(5); LOAD_DIRECT(6); LOAD_DIRECT(7); LOAD_DIRECT(8); LOAD_DIRECT(9); LOAD_DIRECT(10); LOAD_DIRECT(11); LOAD_DIRECT(12); LOAD_DIRECT(13); LOAD_DIRECT(14); LOAD_DIRECT(15);)

DEFINE_BODY(pgot, 1, LOAD_PGOT(0);)
DEFINE_BODY(pgot, 2, LOAD_PGOT(0); LOAD_PGOT(1);)
DEFINE_BODY(pgot, 4, LOAD_PGOT(0); LOAD_PGOT(1); LOAD_PGOT(2); LOAD_PGOT(3);)
DEFINE_BODY(pgot, 8, LOAD_PGOT(0); LOAD_PGOT(1); LOAD_PGOT(2); LOAD_PGOT(3); LOAD_PGOT(4); LOAD_PGOT(5); LOAD_PGOT(6); LOAD_PGOT(7);)
DEFINE_BODY(pgot, 16, LOAD_PGOT(0); LOAD_PGOT(1); LOAD_PGOT(2); LOAD_PGOT(3); LOAD_PGOT(4); LOAD_PGOT(5); LOAD_PGOT(6); LOAD_PGOT(7); LOAD_PGOT(8); LOAD_PGOT(9); LOAD_PGOT(10); LOAD_PGOT(11); LOAD_PGOT(12); LOAD_PGOT(13); LOAD_PGOT(14); LOAD_PGOT(15);)

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

static int current_run_id(void)
{
    const char *s = getenv("PGOT_RUN_ID");
    if (!s || !s[0])
        return 0;
    return atoi(s);
}

static void write_raw_samples(int events, const struct bench_config *cfg,
                              const struct sample_set *direct,
                              const struct sample_set *pgot,
                              const struct sample_set *delta)
{
    const char *path = getenv("PGOT_RAW_FILE");
    if (!path || !path[0])
        return;

    FILE *f = fopen(path, "a");
    if (!f) {
        perror(path);
        exit(1);
    }

    if (ftell(f) == 0) {
        fprintf(f, "experiment,run_id,event,repeat,iterations,direct_cycles,pgot_cycles,delta_cycles,delta_cycles_per_event\n");
    }

    int run_id = current_run_id();
    for (int r = 0; r < cfg->repeats; r++) {
        fprintf(f, "layer1_data_independent,%d,%d,%d,%" PRIu64 ",%.9f,%.9f,%.9f,%.9f\n",
                run_id, events, r, cfg->iterations, direct->values[r],
                pgot->values[r], delta->values[r], delta->values[r] / (double)events);
    }
    fclose(f);
}

static void run_pair(const struct bench_config *cfg, int events)
{
    body_fn_t dfn = select_body("direct", events);
    body_fn_t pfn = select_body("pgot", events);
    struct sample_set direct;
    struct sample_set pgot;
    struct sample_set delta;

    collect_pair(dfn, pfn, cfg, &direct, &pgot, &delta);
    write_raw_samples(events, cfg, &direct, &pgot, &delta);
    printf("layer1_data_independent,%d,%" PRIu64 ",%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
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
    init_data_tables();
    bench_print_env_header("layer1_data_independent");
    bench_print_config_header(&cfg);
    printf("# sample_order=interleave\n");
    printf("# delta=median_of_paired_delta\n");
    printf("experiment,events,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,delta_cycles_per_event,direct_cycles_per_event,pgot_cycles_per_event,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter\n");

    const int events[] = {1, 2, 4, 8, 16};
    for (size_t i = 0; i < sizeof(events) / sizeof(events[0]); i++)
        run_pair(&cfg, events[i]);
    return 0;
}
