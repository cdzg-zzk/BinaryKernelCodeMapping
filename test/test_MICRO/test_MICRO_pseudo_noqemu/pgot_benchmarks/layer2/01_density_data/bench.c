#include "bench_common.h"
#include "data_tables.h"

#define BASE_WORK_UNITS 64

#define WORK_1() do { \
    acc = (acc * 1664525ULL) + 1013904223ULL; \
    acc ^= acc >> 17; \
} while (0)

#define WORK_4() do { WORK_1(); WORK_1(); WORK_1(); WORK_1(); } while (0)
#define WORK_8() do { WORK_4(); WORK_4(); } while (0)
#define WORK_16() do { WORK_8(); WORK_8(); } while (0)
#define WORK_32() do { WORK_16(); WORK_16(); } while (0)

#define EVENT_DIRECT(idx) do { \
    volatile uint64_t *p__ = &direct_values[(idx) & (PGOT_DATA_SLOTS - 1)]; \
    acc += *p__; \
} while (0)

#define EVENT_PGOT(idx) do { \
    uint64_t * volatile *slot__ = pgot_data_table; \
    volatile uint64_t *p__ = slot__[(idx) & (PGOT_DATA_SLOTS - 1)]; \
    acc += *p__; \
} while (0)

#define EVENTS_0(kind) do { } while (0)
#define EVENTS_1(kind) do { EVENT_##kind(0); } while (0)
#define EVENTS_2(kind) do { EVENTS_1(kind); EVENT_##kind(1); } while (0)
#define EVENTS_4(kind) do { EVENTS_2(kind); EVENT_##kind(2); EVENT_##kind(3); } while (0)
#define EVENTS_8(kind) do { \
    EVENTS_4(kind); EVENT_##kind(4); EVENT_##kind(5); EVENT_##kind(6); EVENT_##kind(7); \
} while (0)
#define EVENTS_16(kind) do { \
    EVENTS_8(kind); \
    EVENT_##kind(8); EVENT_##kind(9); EVENT_##kind(10); EVENT_##kind(11); \
    EVENT_##kind(12); EVENT_##kind(13); EVENT_##kind(14); EVENT_##kind(15); \
} while (0)
#define EVENTS_32(kind) do { \
    EVENTS_16(kind); \
    EVENT_##kind(16); EVENT_##kind(17); EVENT_##kind(18); EVENT_##kind(19); \
    EVENT_##kind(20); EVENT_##kind(21); EVENT_##kind(22); EVENT_##kind(23); \
    EVENT_##kind(24); EVENT_##kind(25); EVENT_##kind(26); EVENT_##kind(27); \
    EVENT_##kind(28); EVENT_##kind(29); EVENT_##kind(30); EVENT_##kind(31); \
} while (0)

#define LAYOUT_DIST1(kind, events) do { \
    WORK_32(); \
    events(kind); \
    WORK_32(); \
} while (0)

#define LAYOUT_DIST1_0(kind) LAYOUT_DIST1(kind, EVENTS_0)
#define LAYOUT_DIST1_1(kind) LAYOUT_DIST1(kind, EVENTS_1)
#define LAYOUT_DIST1_2(kind) LAYOUT_DIST1(kind, EVENTS_2)
#define LAYOUT_DIST1_4(kind) LAYOUT_DIST1(kind, EVENTS_4)
#define LAYOUT_DIST1_8(kind) LAYOUT_DIST1(kind, EVENTS_8)
#define LAYOUT_DIST1_16(kind) LAYOUT_DIST1(kind, EVENTS_16)
#define LAYOUT_DIST1_32(kind) LAYOUT_DIST1(kind, EVENTS_32)

#define LAYOUT_DIST2_0(kind) do { WORK_16(); WORK_32(); WORK_16(); } while (0)
#define LAYOUT_DIST2_1(kind) do { WORK_16(); WORK_32(); EVENTS_1(kind); WORK_16(); } while (0)
#define LAYOUT_DIST2_2(kind) do { WORK_16(); EVENTS_1(kind); WORK_32(); EVENTS_1(kind); WORK_16(); } while (0)
#define LAYOUT_DIST2_4(kind) do { WORK_16(); EVENTS_2(kind); WORK_32(); EVENTS_2(kind); WORK_16(); } while (0)
#define LAYOUT_DIST2_8(kind) do { WORK_16(); EVENTS_4(kind); WORK_32(); EVENTS_4(kind); WORK_16(); } while (0)
#define LAYOUT_DIST2_16(kind) do { WORK_16(); EVENTS_8(kind); WORK_32(); EVENTS_8(kind); WORK_16(); } while (0)
#define LAYOUT_DIST2_32(kind) do { WORK_16(); EVENTS_16(kind); WORK_32(); EVENTS_16(kind); WORK_16(); } while (0)

#define LAYOUT_DIST4_0(kind) do { \
    WORK_8(); WORK_16(); WORK_16(); WORK_16(); WORK_8(); \
} while (0)
#define LAYOUT_DIST4_1(kind) do { \
    WORK_8(); WORK_16(); WORK_16(); EVENTS_1(kind); WORK_16(); WORK_8(); \
} while (0)
#define LAYOUT_DIST4_2(kind) do { \
    WORK_8(); WORK_16(); EVENTS_1(kind); WORK_16(); WORK_16(); EVENTS_1(kind); WORK_8(); \
} while (0)
#define LAYOUT_DIST4_4(kind) do { \
    WORK_8(); EVENTS_1(kind); WORK_16(); EVENTS_1(kind); \
    WORK_16(); EVENTS_1(kind); WORK_16(); EVENTS_1(kind); WORK_8(); \
} while (0)
#define LAYOUT_DIST4_8(kind) do { \
    WORK_8(); EVENTS_2(kind); WORK_16(); EVENTS_2(kind); \
    WORK_16(); EVENTS_2(kind); WORK_16(); EVENTS_2(kind); WORK_8(); \
} while (0)
#define LAYOUT_DIST4_16(kind) do { \
    WORK_8(); EVENTS_4(kind); WORK_16(); EVENTS_4(kind); \
    WORK_16(); EVENTS_4(kind); WORK_16(); EVENTS_4(kind); WORK_8(); \
} while (0)
#define LAYOUT_DIST4_32(kind) do { \
    WORK_8(); EVENTS_8(kind); WORK_16(); EVENTS_8(kind); \
    WORK_16(); EVENTS_8(kind); WORK_16(); EVENTS_8(kind); WORK_8(); \
} while (0)

#define LAYOUT_DIST8_0(kind) do { \
    WORK_4(); WORK_8(); WORK_8(); WORK_8(); WORK_8(); WORK_8(); WORK_8(); WORK_8(); WORK_4(); \
} while (0)
#define LAYOUT_DIST8_1(kind) do { \
    WORK_4(); WORK_8(); WORK_8(); WORK_8(); WORK_8(); EVENTS_1(kind); \
    WORK_8(); WORK_8(); WORK_8(); WORK_4(); \
} while (0)
#define LAYOUT_DIST8_2(kind) do { \
    WORK_4(); WORK_8(); WORK_8(); EVENTS_1(kind); WORK_8(); WORK_8(); \
    WORK_8(); WORK_8(); EVENTS_1(kind); WORK_8(); WORK_4(); \
} while (0)
#define LAYOUT_DIST8_4(kind) do { \
    WORK_4(); WORK_8(); EVENTS_1(kind); WORK_8(); WORK_8(); EVENTS_1(kind); \
    WORK_8(); WORK_8(); EVENTS_1(kind); WORK_8(); WORK_8(); EVENTS_1(kind); WORK_4(); \
} while (0)
#define LAYOUT_DIST8_8(kind) do { \
    WORK_4(); EVENTS_1(kind); WORK_8(); EVENTS_1(kind); WORK_8(); EVENTS_1(kind); \
    WORK_8(); EVENTS_1(kind); WORK_8(); EVENTS_1(kind); WORK_8(); EVENTS_1(kind); \
    WORK_8(); EVENTS_1(kind); WORK_8(); EVENTS_1(kind); WORK_4(); \
} while (0)
#define LAYOUT_DIST8_16(kind) do { \
    WORK_4(); EVENTS_2(kind); WORK_8(); EVENTS_2(kind); WORK_8(); EVENTS_2(kind); \
    WORK_8(); EVENTS_2(kind); WORK_8(); EVENTS_2(kind); WORK_8(); EVENTS_2(kind); \
    WORK_8(); EVENTS_2(kind); WORK_8(); EVENTS_2(kind); WORK_4(); \
} while (0)
#define LAYOUT_DIST8_32(kind) do { \
    WORK_4(); EVENTS_4(kind); WORK_8(); EVENTS_4(kind); WORK_8(); EVENTS_4(kind); \
    WORK_8(); EVENTS_4(kind); WORK_8(); EVENTS_4(kind); WORK_8(); EVENTS_4(kind); \
    WORK_8(); EVENTS_4(kind); WORK_8(); EVENTS_4(kind); WORK_4(); \
} while (0)

#define DEFINE_MEASURE(kind, placement, ev, layout) \
NOINLINE static double measure_##kind##_##placement##_ev##ev(uint64_t iterations) \
{ \
    uint64_t acc = 0xfeedfacecafebeefULL; \
    uint64_t start = bench_rdtsc_start(); \
    for (uint64_t i = 0; i < iterations; i++) { \
        acc += i; \
        layout(kind); \
        asm volatile("" : "+r"(acc) :: "memory"); \
    } \
    uint64_t end = bench_rdtsc_end(); \
    bench_black_box_u64(acc); \
    return (double)(end - start) / (double)iterations; \
}

#define DEFINE_PAIR(placement, ev, layout) \
DEFINE_MEASURE(DIRECT, placement, ev, layout) \
DEFINE_MEASURE(PGOT, placement, ev, layout)

DEFINE_PAIR(dist1, 0, LAYOUT_DIST1_0)
DEFINE_PAIR(dist1, 1, LAYOUT_DIST1_1)
DEFINE_PAIR(dist1, 2, LAYOUT_DIST1_2)
DEFINE_PAIR(dist1, 4, LAYOUT_DIST1_4)
DEFINE_PAIR(dist1, 8, LAYOUT_DIST1_8)
DEFINE_PAIR(dist1, 16, LAYOUT_DIST1_16)
DEFINE_PAIR(dist1, 32, LAYOUT_DIST1_32)

DEFINE_PAIR(dist2, 0, LAYOUT_DIST2_0)
DEFINE_PAIR(dist2, 1, LAYOUT_DIST2_1)
DEFINE_PAIR(dist2, 2, LAYOUT_DIST2_2)
DEFINE_PAIR(dist2, 4, LAYOUT_DIST2_4)
DEFINE_PAIR(dist2, 8, LAYOUT_DIST2_8)
DEFINE_PAIR(dist2, 16, LAYOUT_DIST2_16)
DEFINE_PAIR(dist2, 32, LAYOUT_DIST2_32)

DEFINE_PAIR(dist4, 0, LAYOUT_DIST4_0)
DEFINE_PAIR(dist4, 1, LAYOUT_DIST4_1)
DEFINE_PAIR(dist4, 2, LAYOUT_DIST4_2)
DEFINE_PAIR(dist4, 4, LAYOUT_DIST4_4)
DEFINE_PAIR(dist4, 8, LAYOUT_DIST4_8)
DEFINE_PAIR(dist4, 16, LAYOUT_DIST4_16)
DEFINE_PAIR(dist4, 32, LAYOUT_DIST4_32)

DEFINE_PAIR(dist8, 0, LAYOUT_DIST8_0)
DEFINE_PAIR(dist8, 1, LAYOUT_DIST8_1)
DEFINE_PAIR(dist8, 2, LAYOUT_DIST8_2)
DEFINE_PAIR(dist8, 4, LAYOUT_DIST8_4)
DEFINE_PAIR(dist8, 8, LAYOUT_DIST8_8)
DEFINE_PAIR(dist8, 16, LAYOUT_DIST8_16)
DEFINE_PAIR(dist8, 32, LAYOUT_DIST8_32)

typedef double (*measure_fn_t)(uint64_t);

#define SELECT_CASE(kind, placement, ev) case ev: return measure_##kind##_##placement##_ev##ev
#define SELECT_PLACEMENT(kind, placement) \
SELECT_CASE(kind, placement, 0); SELECT_CASE(kind, placement, 1); SELECT_CASE(kind, placement, 2); \
SELECT_CASE(kind, placement, 4); SELECT_CASE(kind, placement, 8); SELECT_CASE(kind, placement, 16); \
SELECT_CASE(kind, placement, 32)

struct sample_set {
    double *values;
    double median;
    double iqr;
};

struct layer2_config {
    struct bench_config bench;
    const char *placement;
    int pgot_events;
    int single_case;
    int interleave;
};

struct placement_info {
    const char *name;
    int groups;
};

static const struct placement_info placements[] = {
    {"dist1", 1},
    {"dist2", 2},
    {"dist4", 4},
    {"dist8", 8},
};

static int is_supported_event(int ev)
{
    return ev == 0 || ev == 1 || ev == 2 || ev == 4 || ev == 8 || ev == 16 || ev == 32;
}

static int placement_groups(const char *placement)
{
    for (size_t i = 0; i < sizeof(placements) / sizeof(placements[0]); i++) {
        if (!strcmp(placement, placements[i].name))
            return placements[i].groups;
    }
    return 0;
}

static int max_events_per_group(int events, int groups)
{
    if (events == 0)
        return 0;
    int counts[8] = {0};
    for (int k = 0; k < events; k++) {
        int g = ((2 * k + 1) * groups) / (2 * events);
        if (g >= groups)
            g = groups - 1;
        counts[g]++;
    }
    int max = 0;
    for (int i = 0; i < groups; i++) {
        if (counts[i] > max)
            max = counts[i];
    }
    return max;
}

static measure_fn_t select_measure(const char *kind, const char *placement, int ev)
{
    if (!is_supported_event(ev))
        return NULL;
    if (!strcmp(kind, "direct")) {
        if (!strcmp(placement, "dist1")) {
            switch (ev) { SELECT_PLACEMENT(DIRECT, dist1); }
        } else if (!strcmp(placement, "dist2")) {
            switch (ev) { SELECT_PLACEMENT(DIRECT, dist2); }
        } else if (!strcmp(placement, "dist4")) {
            switch (ev) { SELECT_PLACEMENT(DIRECT, dist4); }
        } else if (!strcmp(placement, "dist8")) {
            switch (ev) { SELECT_PLACEMENT(DIRECT, dist8); }
        }
    } else {
        if (!strcmp(placement, "dist1")) {
            switch (ev) { SELECT_PLACEMENT(PGOT, dist1); }
        } else if (!strcmp(placement, "dist2")) {
            switch (ev) { SELECT_PLACEMENT(PGOT, dist2); }
        } else if (!strcmp(placement, "dist4")) {
            switch (ev) { SELECT_PLACEMENT(PGOT, dist4); }
        } else if (!strcmp(placement, "dist8")) {
            switch (ev) { SELECT_PLACEMENT(PGOT, dist8); }
        }
    }
    return NULL;
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

static struct sample_set collect_samples(measure_fn_t fn, const struct bench_config *cfg)
{
    struct sample_set set;
    alloc_sample_set(&set, cfg->repeats);
    (void)fn(cfg->iterations / 10 + 1);
    for (int r = 0; r < cfg->repeats; r++)
        set.values[r] = fn(cfg->iterations);
    compute_stats(&set, cfg->repeats);
    return set;
}

static void collect_samples_interleaved(measure_fn_t dfn, measure_fn_t pfn,
                                        const struct bench_config *cfg,
                                        struct sample_set *direct,
                                        struct sample_set *pgot)
{
    alloc_sample_set(direct, cfg->repeats);
    alloc_sample_set(pgot, cfg->repeats);
    (void)dfn(cfg->iterations / 10 + 1);
    (void)pfn(cfg->iterations / 10 + 1);
    for (int r = 0; r < cfg->repeats; r++) {
        if (r & 1) {
            pgot->values[r] = pfn(cfg->iterations);
            direct->values[r] = dfn(cfg->iterations);
        } else {
            direct->values[r] = dfn(cfg->iterations);
            pgot->values[r] = pfn(cfg->iterations);
        }
    }
    compute_stats(direct, cfg->repeats);
    compute_stats(pgot, cfg->repeats);
}

static void free_samples(struct sample_set *set)
{
    free(set->values);
    set->values = NULL;
}

static void write_raw_samples(const char *placement, int ev, const struct sample_set *direct,
                              const struct sample_set *pgot, int repeats)
{
    const char *dir = getenv("PGOT_RAW_DIR");
    if (!dir || !dir[0])
        return;

    char path[512];
    int n = snprintf(path, sizeof(path), "%s/layer2_density_data_%s_ev%d.csv", dir, placement, ev);
    if (n < 0 || (size_t)n >= sizeof(path)) {
        fprintf(stderr, "raw sample path too long\n");
        exit(1);
    }

    FILE *f = fopen(path, "w");
    if (!f) {
        perror(path);
        exit(1);
    }
    fprintf(f, "repeat,direct_cycles,pgot_cycles,delta_cycles\n");
    for (int r = 0; r < repeats; r++)
        fprintf(f, "%d,%.6f,%.6f,%.6f\n", r, direct->values[r],
                pgot->values[r], pgot->values[r] - direct->values[r]);
    fclose(f);
}

static struct sample_set compute_delta_samples(const struct sample_set *direct,
                                               const struct sample_set *pgot,
                                               int repeats)
{
    struct sample_set delta;
    alloc_sample_set(&delta, repeats);
    for (int r = 0; r < repeats; r++)
        delta.values[r] = pgot->values[r] - direct->values[r];
    compute_stats(&delta, repeats);
    return delta;
}

static void run_pair(const struct layer2_config *opts, const char *placement, int ev)
{
    const struct bench_config *cfg = &opts->bench;
    int groups = placement_groups(placement);
    measure_fn_t dfn = select_measure("direct", placement, ev);
    measure_fn_t pfn = select_measure("pgot", placement, ev);
    if (!groups || !dfn || !pfn) {
        fprintf(stderr, "unsupported case: placement=%s pgot_events=%d\n", placement, ev);
        exit(2);
    }

    struct sample_set direct;
    struct sample_set pgot;
    if (opts->interleave) {
        collect_samples_interleaved(dfn, pfn, cfg, &direct, &pgot);
    } else {
        direct = collect_samples(dfn, cfg);
        pgot = collect_samples(pfn, cfg);
    }

    struct sample_set delta = compute_delta_samples(&direct, &pgot, cfg->repeats);
    double pct = direct.median != 0.0 ? (delta.median / direct.median) * 100.0 : 0.0;
    double per_event = ev > 0 ? delta.median / (double)ev : 0.0;
    double avg_per_group = groups > 0 ? (double)ev / (double)groups : 0.0;
    int max_per_group = max_events_per_group(ev, groups);
    write_raw_samples(placement, ev, &direct, &pgot, cfg->repeats);
    printf("layer2_density_data_placement,independent,%d,%s,%d,%d,%.6f,%d,%" PRIu64 ",%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
           BASE_WORK_UNITS, placement, groups, ev, avg_per_group, max_per_group,
           cfg->iterations, cfg->repeats, direct.median, pgot.median, delta.median, pct,
           per_event, delta.iqr, direct.iqr, pgot.iqr);
    free_samples(&delta);
    free_samples(&direct);
    free_samples(&pgot);
}

static void layer2_usage(const char *prog)
{
    bench_usage(prog);
    fprintf(stderr,
            "  --base-work n    only 64 is supported for this placement-density experiment\n"
            "  --pgot-events n  run one event count: 0,1,2,4,8,16,32\n"
            "  --placement p    run one placement: dist1,dist2,dist4,dist8\n"
            "  --sample-order o sample order: separate, interleave; default separate\n");
}

static int parse_layer2_args(int argc, char **argv, struct layer2_config *out)
{
    bench_default_config(&out->bench);
    out->placement = NULL;
    out->pgot_events = -1;
    out->single_case = 0;
    out->interleave = 0;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-n") || !strcmp(argv[i], "--iterations")) {
            if (++i >= argc)
                return -1;
            out->bench.iterations = strtoull(argv[i], NULL, 0);
        } else if (!strcmp(argv[i], "-r") || !strcmp(argv[i], "--repeats")) {
            if (++i >= argc)
                return -1;
            out->bench.repeats = atoi(argv[i]);
        } else if (!strcmp(argv[i], "-c") || !strcmp(argv[i], "--cpu")) {
            if (++i >= argc)
                return -1;
            out->bench.cpu = atoi(argv[i]);
        } else if (!strcmp(argv[i], "--base-work")) {
            if (++i >= argc)
                return -1;
            if (atoi(argv[i]) != BASE_WORK_UNITS)
                return -1;
        } else if (!strcmp(argv[i], "--placement")) {
            if (++i >= argc)
                return -1;
            out->placement = argv[i];
            if (!placement_groups(out->placement))
                return -1;
        } else if (!strcmp(argv[i], "--pgot-events")) {
            if (++i >= argc)
                return -1;
            out->pgot_events = atoi(argv[i]);
            if (!is_supported_event(out->pgot_events))
                return -1;
        } else if (!strcmp(argv[i], "--sample-order")) {
            if (++i >= argc)
                return -1;
            if (!strcmp(argv[i], "separate")) {
                out->interleave = 0;
            } else if (!strcmp(argv[i], "interleave")) {
                out->interleave = 1;
            } else {
                return -1;
            }
        } else if (!strcmp(argv[i], "-h") || !strcmp(argv[i], "--help")) {
            layer2_usage(argv[0]);
            exit(0);
        } else {
            return -1;
        }
    }

    if (out->bench.iterations == 0 || out->bench.repeats <= 0)
        return -1;
    if ((out->placement == NULL) != (out->pgot_events < 0))
        return -1;
    if (out->placement != NULL) {
        if (!select_measure("direct", out->placement, out->pgot_events))
            return -1;
        out->single_case = 1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    struct layer2_config opts;
    if (parse_layer2_args(argc, argv, &opts) != 0) {
        layer2_usage(argv[0]);
        return 2;
    }

    const struct bench_config *cfg = &opts.bench;
    bench_pin_cpu(cfg->cpu);
    init_data_tables();
    bench_print_env_header("layer2_density_data_placement");
    bench_print_config_header(cfg);
    printf("# base_work=%d\n", BASE_WORK_UNITS);
    printf("# access_pattern=independent\n");
    printf("# sample_order=%s\n", opts.interleave ? "interleave" : "separate");
    printf("experiment,access_pattern,base_work,placement,placement_groups,pgot_events,avg_events_per_group,max_events_per_group,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,overhead_percent,delta_cycles_per_event,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter\n");

    if (opts.single_case) {
        run_pair(&opts, opts.placement, opts.pgot_events);
        return 0;
    }

    const int evs[] = {0, 1, 2, 4, 8, 16, 32};
    for (size_t i = 0; i < sizeof(placements) / sizeof(placements[0]); i++)
        for (size_t j = 0; j < sizeof(evs) / sizeof(evs[0]); j++)
            run_pair(&opts, placements[i].name, evs[j]);
    return 0;
}
