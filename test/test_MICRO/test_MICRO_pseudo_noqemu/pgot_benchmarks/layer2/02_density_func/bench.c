#include "bench_common.h"
#include "targets.h"

#ifdef RETPOLINE_BUILD
#define BUILD_NAME "retpoline"
#else
#define BUILD_NAME "no_retpoline"
#endif

#define WORK_1() do { \
    acc = (acc * 1664525ULL) + 1013904223ULL; \
    acc ^= acc >> 17; \
} while (0)

#define WORK_2() do { WORK_1(); WORK_1(); } while (0)
#define WORK_4() do { WORK_2(); WORK_2(); } while (0)
#define WORK_8() do { WORK_4(); WORK_4(); } while (0)
#define WORK_16() do { WORK_8(); WORK_8(); } while (0)
#define WORK_32() do { WORK_16(); WORK_16(); } while (0)
#define WORK_64() do { WORK_32(); WORK_32(); } while (0)

#define CALL_DIRECT() do { \
    acc = target_0(acc); \
} while (0)

#define CALL_PGOT() do { \
    bench_fn_t volatile *slot__ = pgot_func_table; \
    bench_fn_t f__ = slot__[0]; \
    acc = f__(acc); \
} while (0)

#define EVENTS_0(kind) do { } while (0)
#define EVENTS_1(kind) do { CALL_##kind(); } while (0)
#define EVENTS_2(kind) do { EVENTS_1(kind); EVENTS_1(kind); } while (0)
#define EVENTS_4(kind) do { EVENTS_2(kind); EVENTS_2(kind); } while (0)
#define EVENTS_8(kind) do { EVENTS_4(kind); EVENTS_4(kind); } while (0)
#define EVENTS_16(kind) do { EVENTS_8(kind); EVENTS_8(kind); } while (0)

#define LAYOUT_DIST1(kind, front, evs) do { \
    front(); \
    evs(kind); \
    front(); \
} while (0)

#define LAYOUT_DIST2(kind, front, middle, g0, g1) do { \
    front(); \
    g0(kind); \
    middle(); \
    g1(kind); \
    front(); \
} while (0)

#define LAYOUT_DIST4(kind, front, middle, g0, g1, g2, g3) do { \
    front(); \
    g0(kind); \
    middle(); \
    g1(kind); \
    middle(); \
    g2(kind); \
    middle(); \
    g3(kind); \
    front(); \
} while (0)

#define LAYOUT_DIST8(kind, front, middle, g0, g1, g2, g3, g4, g5, g6, g7) do { \
    front(); \
    g0(kind); \
    middle(); \
    g1(kind); \
    middle(); \
    g2(kind); \
    middle(); \
    g3(kind); \
    middle(); \
    g4(kind); \
    middle(); \
    g5(kind); \
    middle(); \
    g6(kind); \
    middle(); \
    g7(kind); \
    front(); \
} while (0)

#define DEFINE_MEASURE(kind, bw, placement, ev, layout, ...) \
NOINLINE static double measure_##kind##_bw##bw##_##placement##_ev##ev(uint64_t iterations) \
{ \
    uint64_t acc = 0x1020304050607080ULL; \
    uint64_t start = bench_rdtsc_start(); \
    for (uint64_t i = 0; i < iterations; i++) { \
        acc += i; \
        layout(kind, __VA_ARGS__); \
        asm volatile("" : "+r"(acc) :: "memory"); \
    } \
    uint64_t end = bench_rdtsc_end(); \
    bench_black_box_u64(acc); \
    return (double)(end - start) / (double)iterations; \
}

#define DEFINE_PAIR(bw, placement, ev, layout, ...) \
DEFINE_MEASURE(DIRECT, bw, placement, ev, layout, __VA_ARGS__) \
DEFINE_MEASURE(PGOT, bw, placement, ev, layout, __VA_ARGS__)

#define DEFINE_DIST1_CASES(bw, front) \
DEFINE_PAIR(bw, dist1, 0, LAYOUT_DIST1, front, EVENTS_0) \
DEFINE_PAIR(bw, dist1, 1, LAYOUT_DIST1, front, EVENTS_1) \
DEFINE_PAIR(bw, dist1, 2, LAYOUT_DIST1, front, EVENTS_2) \
DEFINE_PAIR(bw, dist1, 4, LAYOUT_DIST1, front, EVENTS_4) \
DEFINE_PAIR(bw, dist1, 8, LAYOUT_DIST1, front, EVENTS_8) \
DEFINE_PAIR(bw, dist1, 16, LAYOUT_DIST1, front, EVENTS_16)

#define DEFINE_DIST2_CASES(bw, front, middle) \
DEFINE_PAIR(bw, dist2, 0, LAYOUT_DIST2, front, middle, EVENTS_0, EVENTS_0) \
DEFINE_PAIR(bw, dist2, 1, LAYOUT_DIST2, front, middle, EVENTS_0, EVENTS_1) \
DEFINE_PAIR(bw, dist2, 2, LAYOUT_DIST2, front, middle, EVENTS_1, EVENTS_1) \
DEFINE_PAIR(bw, dist2, 4, LAYOUT_DIST2, front, middle, EVENTS_2, EVENTS_2) \
DEFINE_PAIR(bw, dist2, 8, LAYOUT_DIST2, front, middle, EVENTS_4, EVENTS_4) \
DEFINE_PAIR(bw, dist2, 16, LAYOUT_DIST2, front, middle, EVENTS_8, EVENTS_8)

#define DEFINE_DIST4_CASES(bw, front, middle) \
DEFINE_PAIR(bw, dist4, 0, LAYOUT_DIST4, front, middle, EVENTS_0, EVENTS_0, EVENTS_0, EVENTS_0) \
DEFINE_PAIR(bw, dist4, 1, LAYOUT_DIST4, front, middle, EVENTS_0, EVENTS_0, EVENTS_1, EVENTS_0) \
DEFINE_PAIR(bw, dist4, 2, LAYOUT_DIST4, front, middle, EVENTS_0, EVENTS_1, EVENTS_0, EVENTS_1) \
DEFINE_PAIR(bw, dist4, 4, LAYOUT_DIST4, front, middle, EVENTS_1, EVENTS_1, EVENTS_1, EVENTS_1) \
DEFINE_PAIR(bw, dist4, 8, LAYOUT_DIST4, front, middle, EVENTS_2, EVENTS_2, EVENTS_2, EVENTS_2) \
DEFINE_PAIR(bw, dist4, 16, LAYOUT_DIST4, front, middle, EVENTS_4, EVENTS_4, EVENTS_4, EVENTS_4)

#define DEFINE_DIST8_CASES(bw, front, middle) \
DEFINE_PAIR(bw, dist8, 0, LAYOUT_DIST8, front, middle, EVENTS_0, EVENTS_0, EVENTS_0, EVENTS_0, EVENTS_0, EVENTS_0, EVENTS_0, EVENTS_0) \
DEFINE_PAIR(bw, dist8, 1, LAYOUT_DIST8, front, middle, EVENTS_0, EVENTS_0, EVENTS_0, EVENTS_0, EVENTS_1, EVENTS_0, EVENTS_0, EVENTS_0) \
DEFINE_PAIR(bw, dist8, 2, LAYOUT_DIST8, front, middle, EVENTS_0, EVENTS_0, EVENTS_1, EVENTS_0, EVENTS_0, EVENTS_0, EVENTS_1, EVENTS_0) \
DEFINE_PAIR(bw, dist8, 4, LAYOUT_DIST8, front, middle, EVENTS_0, EVENTS_1, EVENTS_0, EVENTS_1, EVENTS_0, EVENTS_1, EVENTS_0, EVENTS_1) \
DEFINE_PAIR(bw, dist8, 8, LAYOUT_DIST8, front, middle, EVENTS_1, EVENTS_1, EVENTS_1, EVENTS_1, EVENTS_1, EVENTS_1, EVENTS_1, EVENTS_1) \
DEFINE_PAIR(bw, dist8, 16, LAYOUT_DIST8, front, middle, EVENTS_2, EVENTS_2, EVENTS_2, EVENTS_2, EVENTS_2, EVENTS_2, EVENTS_2, EVENTS_2)

#define DEFINE_WORKSET(bw, d1_front, d2_front, d2_middle, d4_front, d4_middle, d8_front, d8_middle) \
DEFINE_DIST1_CASES(bw, d1_front) \
DEFINE_DIST2_CASES(bw, d2_front, d2_middle) \
DEFINE_DIST4_CASES(bw, d4_front, d4_middle) \
DEFINE_DIST8_CASES(bw, d8_front, d8_middle)

DEFINE_WORKSET(32, WORK_16, WORK_8, WORK_16, WORK_4, WORK_8, WORK_2, WORK_4)
DEFINE_WORKSET(64, WORK_32, WORK_16, WORK_32, WORK_8, WORK_16, WORK_4, WORK_8)
DEFINE_WORKSET(128, WORK_64, WORK_32, WORK_64, WORK_16, WORK_32, WORK_8, WORK_16)

typedef double (*measure_fn_t)(uint64_t);

#define SELECT_CASE(kind, bw, placement, ev) case ev: return measure_##kind##_bw##bw##_##placement##_ev##ev
#define SELECT_PLACEMENT(kind, bw, placement) \
SELECT_CASE(kind, bw, placement, 0); SELECT_CASE(kind, bw, placement, 1); \
SELECT_CASE(kind, bw, placement, 2); SELECT_CASE(kind, bw, placement, 4); \
SELECT_CASE(kind, bw, placement, 8); SELECT_CASE(kind, bw, placement, 16)

struct sample_set {
    double *values;
    double median;
    double iqr;
};

struct layer2_config {
    struct bench_config bench;
    int base_work;
    const char *placement;
    int pgot_events;
    int single_case;
    int interleave;
};

struct placement_info {
    const char *name;
    int groups;
};

static const int base_works[] = {32, 64, 128};
static const int events[] = {0, 1, 2, 4, 8, 16};
static const struct placement_info placements[] = {
    {"dist1", 1},
    {"dist2", 2},
    {"dist4", 4},
    {"dist8", 8},
};

static int is_supported_base_work(int bw)
{
    return bw == 32 || bw == 64 || bw == 128;
}

static int is_supported_event(int ev)
{
    return ev == 0 || ev == 1 || ev == 2 || ev == 4 || ev == 8 || ev == 16;
}

static int placement_groups(const char *placement)
{
    for (size_t i = 0; i < sizeof(placements) / sizeof(placements[0]); i++) {
        if (!strcmp(placement, placements[i].name))
            return placements[i].groups;
    }
    return 0;
}

static int max_events_per_group(int events_count, int groups)
{
    if (events_count == 0)
        return 0;
    int counts[8] = {0};
    for (int k = 0; k < events_count; k++) {
        int g = ((2 * k + 1) * groups) / (2 * events_count);
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

static measure_fn_t select_measure(const char *kind, int bw, const char *placement, int ev)
{
    if (!is_supported_base_work(bw) || !placement_groups(placement) || !is_supported_event(ev))
        return NULL;

    if (!strcmp(kind, "direct")) {
        if (bw == 32) {
            if (!strcmp(placement, "dist1")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 32, dist1); } }
            if (!strcmp(placement, "dist2")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 32, dist2); } }
            if (!strcmp(placement, "dist4")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 32, dist4); } }
            if (!strcmp(placement, "dist8")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 32, dist8); } }
        } else if (bw == 64) {
            if (!strcmp(placement, "dist1")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 64, dist1); } }
            if (!strcmp(placement, "dist2")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 64, dist2); } }
            if (!strcmp(placement, "dist4")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 64, dist4); } }
            if (!strcmp(placement, "dist8")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 64, dist8); } }
        } else if (bw == 128) {
            if (!strcmp(placement, "dist1")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 128, dist1); } }
            if (!strcmp(placement, "dist2")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 128, dist2); } }
            if (!strcmp(placement, "dist4")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 128, dist4); } }
            if (!strcmp(placement, "dist8")) { switch (ev) { SELECT_PLACEMENT(DIRECT, 128, dist8); } }
        }
    } else {
        if (bw == 32) {
            if (!strcmp(placement, "dist1")) { switch (ev) { SELECT_PLACEMENT(PGOT, 32, dist1); } }
            if (!strcmp(placement, "dist2")) { switch (ev) { SELECT_PLACEMENT(PGOT, 32, dist2); } }
            if (!strcmp(placement, "dist4")) { switch (ev) { SELECT_PLACEMENT(PGOT, 32, dist4); } }
            if (!strcmp(placement, "dist8")) { switch (ev) { SELECT_PLACEMENT(PGOT, 32, dist8); } }
        } else if (bw == 64) {
            if (!strcmp(placement, "dist1")) { switch (ev) { SELECT_PLACEMENT(PGOT, 64, dist1); } }
            if (!strcmp(placement, "dist2")) { switch (ev) { SELECT_PLACEMENT(PGOT, 64, dist2); } }
            if (!strcmp(placement, "dist4")) { switch (ev) { SELECT_PLACEMENT(PGOT, 64, dist4); } }
            if (!strcmp(placement, "dist8")) { switch (ev) { SELECT_PLACEMENT(PGOT, 64, dist8); } }
        } else if (bw == 128) {
            if (!strcmp(placement, "dist1")) { switch (ev) { SELECT_PLACEMENT(PGOT, 128, dist1); } }
            if (!strcmp(placement, "dist2")) { switch (ev) { SELECT_PLACEMENT(PGOT, 128, dist2); } }
            if (!strcmp(placement, "dist4")) { switch (ev) { SELECT_PLACEMENT(PGOT, 128, dist4); } }
            if (!strcmp(placement, "dist8")) { switch (ev) { SELECT_PLACEMENT(PGOT, 128, dist8); } }
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

static void free_samples(struct sample_set *set)
{
    free(set->values);
    set->values = NULL;
}

static void write_raw_samples(int bw, const char *placement, int ev,
                              const struct sample_set *direct,
                              const struct sample_set *pgot, int repeats)
{
    const char *dir = getenv("PGOT_RAW_DIR");
    if (!dir || !dir[0])
        return;

    char path[512];
    int n = snprintf(path, sizeof(path), "%s/layer2_density_func_%s_bw%d_%s_ev%d.csv",
                     dir, BUILD_NAME, bw, placement, ev);
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

static void run_pair(const struct layer2_config *opts, int bw, const char *placement, int ev)
{
    const struct bench_config *cfg = &opts->bench;
    int groups = placement_groups(placement);
    measure_fn_t dfn = select_measure("direct", bw, placement, ev);
    measure_fn_t pfn = select_measure("pgot", bw, placement, ev);
    if (!groups || !dfn || !pfn) {
        fprintf(stderr, "unsupported case: base_work=%d placement=%s pgot_events=%d\n",
                bw, placement, ev);
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
    write_raw_samples(bw, placement, ev, &direct, &pgot, cfg->repeats);
    printf("layer2_func_pgot_placement,%s,stable,%d,%s,%d,%d,%.6f,%d,%" PRIu64 ",%d,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
           BUILD_NAME, bw, placement, groups, ev, avg_per_group, max_per_group,
           cfg->iterations, cfg->repeats, direct.median, pgot.median, delta.median,
           pct, per_event, delta.iqr, direct.iqr, pgot.iqr);
    free_samples(&delta);
    free_samples(&direct);
    free_samples(&pgot);
}

static void layer2_usage(const char *prog)
{
    bench_usage(prog);
    fprintf(stderr,
            "  --base-work n    run one base-work value: 32,64,128\n"
            "  --pgot-events n  run one event count: 0,1,2,4,8,16\n"
            "  --placement p    run one placement: dist1,dist2,dist4,dist8\n"
            "  --sample-order o sample order: interleave, separate; default interleave\n");
}

static int parse_layer2_args(int argc, char **argv, struct layer2_config *out)
{
    bench_default_config(&out->bench);
    out->base_work = -1;
    out->placement = NULL;
    out->pgot_events = -1;
    out->single_case = 0;
    out->interleave = 1;

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
            out->base_work = atoi(argv[i]);
            if (!is_supported_base_work(out->base_work))
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
            if (!strcmp(argv[i], "interleave")) {
                out->interleave = 1;
            } else if (!strcmp(argv[i], "separate")) {
                out->interleave = 0;
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
    if ((out->base_work >= 0) != (out->placement != NULL) ||
        (out->base_work >= 0) != (out->pgot_events >= 0))
        return -1;
    if (out->base_work >= 0) {
        if (!select_measure("direct", out->base_work, out->placement, out->pgot_events))
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
    init_pgot_func_table();
    bench_print_env_header("layer2_func_pgot_placement");
    bench_print_config_header(cfg);
    printf("# target_pattern=stable\n");
    printf("# sample_order=%s\n", opts.interleave ? "interleave" : "separate");
    printf("experiment,build,target_pattern,base_work,placement,placement_groups,pgot_events,avg_events_per_group,max_events_per_group,iterations,repeats,direct_cycles_per_iter,pgot_cycles_per_iter,delta_cycles_per_iter,overhead_percent,delta_cycles_per_event,delta_iqr_cycles_per_iter,direct_iqr_cycles_per_iter,pgot_iqr_cycles_per_iter\n");

    if (opts.single_case) {
        run_pair(&opts, opts.base_work, opts.placement, opts.pgot_events);
        return 0;
    }

    for (size_t b = 0; b < sizeof(base_works) / sizeof(base_works[0]); b++)
        for (size_t p = 0; p < sizeof(placements) / sizeof(placements[0]); p++)
            for (size_t e = 0; e < sizeof(events) / sizeof(events[0]); e++)
                run_pair(&opts, base_works[b], placements[p].name, events[e]);
    return 0;
}
