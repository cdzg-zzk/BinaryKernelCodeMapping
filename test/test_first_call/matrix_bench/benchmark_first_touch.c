#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
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

struct sample {
    uint64_t cycles;
    long minflt;
    long majflt;
};

static volatile uint32_t result_sink;

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
            "Conditions:\n"
            "  hot        PTE is present before the measured call.\n"
            "  pte-cold   Function PTE is removed with madvise; backing page remains resident.\n"
            "  post-drop  Function PTE is removed, then sync+drop_caches is executed.\n"
            "\n"
            "DSO paths can be overridden with STUB_DSO and NATIVE_DSO.\n",
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
    struct sample s = {0};
    struct rusage before;
    struct rusage after;

    if (prepare_condition(condition, func, input, length, seed) != 0) {
        s.cycles = UINT64_MAX;
        return s;
    }

    getrusage(RUSAGE_SELF, &before);
    uint64_t start = rdtsc_begin();
    result_sink ^= func(input, length, seed);
    uint64_t end = rdtsc_end();
    getrusage(RUSAGE_SELF, &after);

    s.cycles = end - start;
    s.minflt = after.ru_minflt - before.ru_minflt;
    s.majflt = after.ru_majflt - before.ru_majflt;
    return s;
}

static int compare_sample_cycles(const void *a, const void *b)
{
    const struct sample *sa = a;
    const struct sample *sb = b;

    if (sa->cycles < sb->cycles) {
        return -1;
    }
    if (sa->cycles > sb->cycles) {
        return 1;
    }
    return 0;
}

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

    double q1 = (double)expected[expected_count / 4].cycles;
    double q3 = (double)expected[(expected_count * 3) / 4].cycles;
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
    double sum = 0.0;

    for (int i = 0; i < expected_count; i++) {
        if ((double)expected[i].cycles < lower || (double)expected[i].cycles > upper) {
            continue;
        }
        filtered[filtered_count++] = expected[i];
        total_minflt += expected[i].minflt;
        total_majflt += expected[i].majflt;
        sum += (double)expected[i].cycles;
    }

    if (filtered_count == 0) {
        fprintf(stderr, "all samples were filtered out\n");
        free(expected);
        free(filtered);
        exit(EXIT_FAILURE);
    }

    double mean = sum / filtered_count;
    double variance_sum = 0.0;
    for (int i = 0; i < filtered_count; i++) {
        double delta = (double)filtered[i].cycles - mean;
        variance_sum += delta * delta;
    }

    uint64_t median = filtered[filtered_count / 2].cycles;
    uint64_t p25 = filtered[filtered_count / 4].cycles;
    uint64_t p75 = filtered[(filtered_count * 3) / 4].cycles;
    uint64_t p95 = filtered[(filtered_count * 95) / 100].cycles;

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
    printf("Median Cycles: %lu\n", median);
    printf("Mean Cycles: %.2f\n", mean);
    printf("Std Deviation: %.2f\n", sqrt(variance_sum / filtered_count));
    printf("P25 Cycles: %lu\n", p25);
    printf("P75 Cycles: %lu\n", p75);
    printf("P95 Cycles: %lu\n", p95);
    printf("Result Sink: %u\n", result_sink);

    free(expected);
    free(filtered);
}

int main(int argc, char **argv)
{
    const struct target_spec *target = NULL;
    enum condition_kind condition = COND_HOT;
    int have_condition = 0;
    int runs = 100;

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

    size_t length = 5;
    void *input = calloc(length, 1);
    struct sample *samples = calloc((size_t)runs, sizeof(samples[0]));
    if (!input || !samples) {
        perror("calloc");
        free(input);
        free(samples);
        dlclose(handle);
        return 1;
    }

    uint32_t seed = 0x1234;
    for (int i = 0; i < runs; i++) {
        samples[i] = measure_once(condition, func, input, length, seed);
        if (samples[i].cycles == UINT64_MAX) {
            free(input);
            free(samples);
            dlclose(handle);
            return 1;
        }
    }

    print_statistics(target, condition, samples, runs);

    free(input);
    free(samples);
    dlclose(handle);
    return 0;
}
