#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <getopt.h>
#include <linux/perf_event.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <unistd.h>

typedef uint32_t (*xxh32_func)(const void *input, size_t length, uint32_t seed);

enum target_kind {
    TARGET_STUB,
    TARGET_NATIVE,
};

enum condition_kind {
    COND_HOT,
    COND_PTE_COLD,
    COND_POST_DROP,
};

struct target_spec {
    enum target_kind kind;
    const char *name;
    const char *path_env;
    const char *default_path;
    const char *symbol;
};

struct perf_group_read {
    uint64_t nr;
    uint64_t values[6];
};

struct sample {
    uint64_t cycles_tsc;
    uint64_t perf_cycles;
    uint64_t instructions;
    uint64_t l1i_misses;
    uint64_t l1d_misses;
    uint64_t llc_misses;
    uint64_t itlb_misses;
    long minflt;
    long majflt;
};

static const struct target_spec targets[] = {
    {
        .kind = TARGET_STUB,
        .name = "stub",
        .path_env = "STUB_DSO",
        .default_path = "./zzk_xxh32_lkm.so",
        .symbol = "zzk_xxh32",
    },
    {
        .kind = TARGET_NATIVE,
        .name = "native",
        .path_env = "NATIVE_DSO",
        .default_path = "./libclone_xxh32.so",
        .symbol = "clone_xxh32",
    },
};

static volatile uint32_t result_sink;
static int perf_fds[6] = {-1, -1, -1, -1, -1, -1};

static long perf_event_open(struct perf_event_attr *attr, pid_t pid, int cpu,
                            int group_fd, unsigned long flags)
{
    return syscall(__NR_perf_event_open, attr, pid, cpu, group_fd, flags);
}

static inline uint64_t rdtsc_begin(void)
{
    uint32_t lo = 0;
    uint32_t hi = 0;
    __asm__ volatile("lfence\nrdtsc" : "=a"(lo), "=d"(hi) : : "memory");
    return ((uint64_t)hi << 32) | lo;
}

static inline uint64_t rdtsc_end(void)
{
    uint32_t lo = 0;
    uint32_t hi = 0;
    uint32_t aux = 0;
    __asm__ volatile("rdtscp\nlfence" : "=a"(lo), "=d"(hi), "=c"(aux) : : "memory");
    return ((uint64_t)hi << 32) | lo;
}

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s -t <stub|native> -s <hot|pte-cold|post-drop> [-n runs]\n"
            "\n"
            "This helper collects PMCs for mechanism analysis. Use\n"
            "benchmark_first_touch for the primary cycles/faults table.\n",
            prog);
}

static const struct target_spec *find_target(const char *name)
{
    for (size_t i = 0; i < sizeof(targets) / sizeof(targets[0]); i++) {
        if (strcmp(name, targets[i].name) == 0) {
            return &targets[i];
        }
    }
    return NULL;
}

static int parse_condition(const char *name, enum condition_kind *condition)
{
    if (strcmp(name, "hot") == 0) {
        *condition = COND_HOT;
        return 0;
    }
    if (strcmp(name, "pte-cold") == 0 || strcmp(name, "warm") == 0) {
        *condition = COND_PTE_COLD;
        return 0;
    }
    if (strcmp(name, "post-drop") == 0 || strcmp(name, "cold") == 0) {
        *condition = COND_POST_DROP;
        return 0;
    }
    return -1;
}

static const char *condition_name(enum condition_kind condition)
{
    switch (condition) {
    case COND_HOT:
        return "hot";
    case COND_PTE_COLD:
        return "pte-cold";
    case COND_POST_DROP:
        return "post-drop";
    }
    return "unknown";
}

static int sample_has_expected_faults(const struct target_spec *target,
                                      enum condition_kind condition,
                                      const struct sample *sample)
{
    switch (condition) {
    case COND_HOT:
        return sample->minflt == 0 && sample->majflt == 0;
    case COND_PTE_COLD:
        return sample->minflt == 1 && sample->majflt == 0;
    case COND_POST_DROP:
        if (target->kind == TARGET_NATIVE) {
            return sample->minflt == 0 && sample->majflt == 1;
        }
        return sample->minflt == 1 && sample->majflt == 0;
    }
    return 0;
}

static void configure_hw_event(struct perf_event_attr *attr, uint64_t config)
{
    memset(attr, 0, sizeof(*attr));
    attr->type = PERF_TYPE_HARDWARE;
    attr->size = sizeof(*attr);
    attr->config = config;
    attr->disabled = 1;
    attr->exclude_kernel = 0;
    attr->exclude_hv = 1;
    attr->read_format = PERF_FORMAT_GROUP;
}

static void configure_cache_event(struct perf_event_attr *attr, uint64_t cache,
                                  uint64_t op, uint64_t result)
{
    memset(attr, 0, sizeof(*attr));
    attr->type = PERF_TYPE_HW_CACHE;
    attr->size = sizeof(*attr);
    attr->config = cache | (op << 8) | (result << 16);
    attr->disabled = 1;
    attr->exclude_kernel = 0;
    attr->exclude_hv = 1;
    attr->read_format = PERF_FORMAT_GROUP;
}

static void open_perf_events(void)
{
    struct perf_event_attr attr;

    configure_hw_event(&attr, PERF_COUNT_HW_CPU_CYCLES);
    perf_fds[0] = perf_event_open(&attr, 0, -1, -1, 0);
    if (perf_fds[0] < 0) {
        perror("perf_event_open(cpu-cycles)");
        exit(EXIT_FAILURE);
    }

    configure_hw_event(&attr, PERF_COUNT_HW_INSTRUCTIONS);
    perf_fds[1] = perf_event_open(&attr, 0, -1, perf_fds[0], 0);

    configure_cache_event(&attr, PERF_COUNT_HW_CACHE_L1I,
                          PERF_COUNT_HW_CACHE_OP_READ,
                          PERF_COUNT_HW_CACHE_RESULT_MISS);
    perf_fds[2] = perf_event_open(&attr, 0, -1, perf_fds[0], 0);

    configure_cache_event(&attr, PERF_COUNT_HW_CACHE_L1D,
                          PERF_COUNT_HW_CACHE_OP_READ,
                          PERF_COUNT_HW_CACHE_RESULT_MISS);
    perf_fds[3] = perf_event_open(&attr, 0, -1, perf_fds[0], 0);

    configure_cache_event(&attr, PERF_COUNT_HW_CACHE_LL,
                          PERF_COUNT_HW_CACHE_OP_READ,
                          PERF_COUNT_HW_CACHE_RESULT_MISS);
    perf_fds[4] = perf_event_open(&attr, 0, -1, perf_fds[0], 0);

    configure_cache_event(&attr, PERF_COUNT_HW_CACHE_ITLB,
                          PERF_COUNT_HW_CACHE_OP_READ,
                          PERF_COUNT_HW_CACHE_RESULT_MISS);
    perf_fds[5] = perf_event_open(&attr, 0, -1, perf_fds[0], 0);

    for (int i = 1; i < 6; i++) {
        if (perf_fds[i] < 0) {
            perror("perf_event_open(group member)");
            fprintf(stderr, "This CPU/kernel may not support the requested PMC group.\n");
            exit(EXIT_FAILURE);
        }
    }
}

static void close_perf_events(void)
{
    for (int i = 0; i < 6; i++) {
        if (perf_fds[i] >= 0) {
            close(perf_fds[i]);
            perf_fds[i] = -1;
        }
    }
}

static void evict_func_page(void *func_ptr)
{
    long page_size = sysconf(_SC_PAGESIZE);
    void *aligned = (void *)((uintptr_t)func_ptr & ~((uintptr_t)page_size - 1));

    if (madvise(aligned, (size_t)page_size, MADV_DONTNEED) != 0) {
        perror("madvise(MADV_DONTNEED)");
    }
}

static int drop_page_cache(void)
{
    if (geteuid() != 0) {
        fprintf(stderr, "post-drop requires root because it writes /proc/sys/vm/drop_caches\n");
        return -1;
    }

    if (system("sync; echo 3 > /proc/sys/vm/drop_caches") != 0) {
        fprintf(stderr, "failed to execute sync + drop_caches\n");
        return -1;
    }
    return 0;
}

static int prepare_condition(enum condition_kind condition, xxh32_func func,
                             const void *input, size_t length, uint32_t seed)
{
    result_sink ^= func(input, length, seed);

    switch (condition) {
    case COND_HOT:
        return 0;
    case COND_PTE_COLD:
        evict_func_page((void *)func);
        return 0;
    case COND_POST_DROP:
        evict_func_page((void *)func);
        return drop_page_cache();
    }
    return -1;
}

static struct sample measure_once(enum condition_kind condition, xxh32_func func,
                                  const void *input, size_t length, uint32_t seed)
{
    struct sample s;
    struct rusage before;
    struct rusage after;
    struct perf_group_read counts;

    memset(&s, 0, sizeof(s));
    memset(&counts, 0, sizeof(counts));

    if (prepare_condition(condition, func, input, length, seed) != 0) {
        s.cycles_tsc = UINT64_MAX;
        return s;
    }

    ioctl(perf_fds[0], PERF_EVENT_IOC_RESET, PERF_IOC_FLAG_GROUP);
    getrusage(RUSAGE_SELF, &before);
    ioctl(perf_fds[0], PERF_EVENT_IOC_ENABLE, PERF_IOC_FLAG_GROUP);
    uint64_t start = rdtsc_begin();
    result_sink ^= func(input, length, seed);
    uint64_t end = rdtsc_end();
    ioctl(perf_fds[0], PERF_EVENT_IOC_DISABLE, PERF_IOC_FLAG_GROUP);
    getrusage(RUSAGE_SELF, &after);

    if (read(perf_fds[0], &counts, sizeof(counts)) != (ssize_t)sizeof(counts) || counts.nr != 6) {
        perror("read(perf group)");
        s.cycles_tsc = UINT64_MAX;
        return s;
    }

    s.cycles_tsc = end - start;
    s.perf_cycles = counts.values[0];
    s.instructions = counts.values[1];
    s.l1i_misses = counts.values[2];
    s.l1d_misses = counts.values[3];
    s.llc_misses = counts.values[4];
    s.itlb_misses = counts.values[5];
    s.minflt = after.ru_minflt - before.ru_minflt;
    s.majflt = after.ru_majflt - before.ru_majflt;
    return s;
}

static int compare_sample_cycles(const void *a, const void *b)
{
    const struct sample *sa = a;
    const struct sample *sb = b;

    if (sa->cycles_tsc < sb->cycles_tsc) {
        return -1;
    }
    if (sa->cycles_tsc > sb->cycles_tsc) {
        return 1;
    }
    return 0;
}

static double mean_u64(const struct sample *samples, int count, uint64_t (*get)(const struct sample *))
{
    double sum = 0.0;
    for (int i = 0; i < count; i++) {
        sum += (double)get(&samples[i]);
    }
    return sum / count;
}

static uint64_t get_perf_cycles(const struct sample *s) { return s->perf_cycles; }
static uint64_t get_instructions(const struct sample *s) { return s->instructions; }
static uint64_t get_l1i(const struct sample *s) { return s->l1i_misses; }
static uint64_t get_l1d(const struct sample *s) { return s->l1d_misses; }
static uint64_t get_llc(const struct sample *s) { return s->llc_misses; }
static uint64_t get_itlb(const struct sample *s) { return s->itlb_misses; }

static void print_statistics(const struct target_spec *target,
                             enum condition_kind condition,
                             struct sample *samples, int count)
{
    qsort(samples, (size_t)count, sizeof(samples[0]), compare_sample_cycles);

    struct sample *expected = calloc((size_t)count, sizeof(expected[0]));
    if (!expected) {
        perror("calloc");
        exit(EXIT_FAILURE);
    }

    int expected_count = 0;
    int fault_mismatch_count = 0;
    for (int i = 0; i < count; i++) {
        if (!sample_has_expected_faults(target, condition, &samples[i])) {
            fault_mismatch_count++;
            continue;
        }
        expected[expected_count++] = samples[i];
    }

    if (expected_count == 0) {
        fprintf(stderr, "all samples had unexpected fault counts\n");
        free(expected);
        exit(EXIT_FAILURE);
    }

    double q1 = (double)expected[expected_count / 4].cycles_tsc;
    double q3 = (double)expected[(expected_count * 3) / 4].cycles_tsc;
    double iqr = q3 - q1;
    double lower = q1 - 1.5 * iqr;
    double upper = q3 + 1.5 * iqr;

    struct sample *filtered = calloc((size_t)count, sizeof(filtered[0]));
    if (!filtered) {
        perror("calloc");
        exit(EXIT_FAILURE);
    }

    int filtered_count = 0;
    long total_minflt = 0;
    long total_majflt = 0;
    double sum_tsc = 0.0;

    for (int i = 0; i < expected_count; i++) {
        if ((double)expected[i].cycles_tsc < lower || (double)expected[i].cycles_tsc > upper) {
            continue;
        }
        filtered[filtered_count++] = expected[i];
        total_minflt += expected[i].minflt;
        total_majflt += expected[i].majflt;
        sum_tsc += (double)expected[i].cycles_tsc;
    }

    if (filtered_count == 0) {
        fprintf(stderr, "all samples were filtered out\n");
        free(expected);
        free(filtered);
        exit(EXIT_FAILURE);
    }

    double mean_tsc = sum_tsc / filtered_count;
    double variance_sum = 0.0;
    for (int i = 0; i < filtered_count; i++) {
        double delta = (double)filtered[i].cycles_tsc - mean_tsc;
        variance_sum += delta * delta;
    }

    printf("Target: %s\n", target->name);
    printf("Condition: %s\n", condition_name(condition));
    printf("Total Runs: %d\n", count);
    printf("Expected-Fault Runs: %d (%.1f%%)\n",
           expected_count, (double)expected_count * 100.0 / count);
    printf("Valid Runs (IQR): %d (%.1f%% retained)\n",
           filtered_count, (double)filtered_count * 100.0 / count);
    printf("Fault Mismatches: %d\n", fault_mismatch_count);
    printf("Avg Minor Faults: %.2f per run\n", (double)total_minflt / filtered_count);
    printf("Avg Major Faults: %.2f per run\n", (double)total_majflt / filtered_count);
    printf("Median TSC Cycles: %lu\n", filtered[filtered_count / 2].cycles_tsc);
    printf("Mean TSC Cycles: %.2f\n", mean_tsc);
    printf("Std Deviation: %.2f\n", sqrt(variance_sum / filtered_count));
    printf("Mean Perf Cycles: %.2f\n", mean_u64(filtered, filtered_count, get_perf_cycles));
    printf("Mean Instructions: %.2f\n", mean_u64(filtered, filtered_count, get_instructions));
    printf("Mean L1I Misses: %.2f\n", mean_u64(filtered, filtered_count, get_l1i));
    printf("Mean L1D Misses: %.2f\n", mean_u64(filtered, filtered_count, get_l1d));
    printf("Mean LLC Misses: %.2f\n", mean_u64(filtered, filtered_count, get_llc));
    printf("Mean iTLB Misses: %.2f\n", mean_u64(filtered, filtered_count, get_itlb));
    printf("Result Sink: %u\n", result_sink);

    free(expected);
    free(filtered);
}

int main(int argc, char **argv)
{
    const struct target_spec *target = NULL;
    enum condition_kind condition = COND_HOT;
    int have_condition = 0;
    int runs = 30;

    int opt;
    while ((opt = getopt(argc, argv, "t:s:n:h")) != -1) {
        switch (opt) {
        case 't':
            target = find_target(optarg);
            break;
        case 's':
            have_condition = parse_condition(optarg, &condition) == 0;
            break;
        case 'n':
            runs = atoi(optarg);
            break;
        case 'h':
        default:
            usage(argv[0]);
            return opt == 'h' ? 0 : 1;
        }
    }

    if (!target || !have_condition || runs <= 0) {
        usage(argv[0]);
        return 1;
    }

    const char *path = getenv(target->path_env);
    if (!path || path[0] == '\0') {
        path = target->default_path;
    }

    void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "dlopen(%s): %s\n", path, dlerror());
        return 1;
    }

    dlerror();
    xxh32_func func = (xxh32_func)dlsym(handle, target->symbol);
    const char *dlsym_error = dlerror();
    if (dlsym_error) {
        fprintf(stderr, "dlsym(%s): %s\n", target->symbol, dlsym_error);
        dlclose(handle);
        return 1;
    }

    open_perf_events();

    size_t length = 5;
    void *input = calloc(length, 1);
    struct sample *samples = calloc((size_t)runs, sizeof(samples[0]));
    if (!input || !samples) {
        perror("calloc");
        free(input);
        free(samples);
        close_perf_events();
        dlclose(handle);
        return 1;
    }

    uint32_t seed = 0x1234;
    for (int i = 0; i < runs; i++) {
        samples[i] = measure_once(condition, func, input, length, seed);
        if (samples[i].cycles_tsc == UINT64_MAX) {
            free(input);
            free(samples);
            close_perf_events();
            dlclose(handle);
            return 1;
        }
    }

    print_statistics(target, condition, samples, runs);

    free(input);
    free(samples);
    close_perf_events();
    dlclose(handle);
    return 0;
}
