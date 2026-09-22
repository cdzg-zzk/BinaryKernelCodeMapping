/* Diagnostic companion: reuse the complete target and timestamp primitives. */
#define main original_first_touch_main
#include "benchmark_first_touch.c"
#undef main
#include <sched.h>

static uint64_t page_entry(int fd, void *address)
{
    uint64_t value;
    if (pread(fd, &value, sizeof(value), (uintptr_t)address / 4096 * 8) != sizeof(value)) {
        perror("pagemap"); exit(1);
    }
    return value;
}

int main(int argc, char **argv)
{
    if (argc != 3) return 2;
    cpu_set_t cpus; CPU_ZERO(&cpus); CPU_SET(1, &cpus);
    if (sched_setaffinity(0, sizeof(cpus), &cpus)) return 1;
    const struct target_spec *target = find_target(argv[1]);
    if (!target) return 2;
    void *handle = dlopen(getenv(target->path_env), RTLD_NOW | RTLD_LOCAL);
    if (!handle) { fprintf(stderr, "%s\n", dlerror()); return 1; }
    xxh32_func func = (xxh32_func)dlsym(handle, target->symbol);
    if (!func) return 1;
    const uint32_t expected = strtoul(argv[2], NULL, 0);
    const char input[] = "hello";
    void *page = (void *)((uintptr_t)func & ~(uintptr_t)4095);
    int fd = open("/proc/self/pagemap", O_RDONLY);
    if (fd < 0 || sysconf(_SC_PAGESIZE) != 4096) return 1;
    struct rusage before, after;
    getrusage(RUSAGE_SELF, &before); getrusage(RUSAGE_SELF, &after);
    setvbuf(stdout, NULL, _IOLBF, 0);
    printf("{\"event\":\"ready\",\"pid\":%d,\"cpu\":%d,\"address\":%llu}\n",
           getpid(), sched_getcpu(), (unsigned long long)(uintptr_t)func);
    char command[64]; int prepared = 0;
    while (fgets(command, sizeof(command), stdin)) {
        if (!strcmp(command, "PREP\n")) {
            if (func(input, 5, 0x1234) != expected || evict_func_page((void *)func)) return 1;
            prepared = 1;
            printf("{\"event\":\"prepared\",\"pte\":%llu}\n",
                   (unsigned long long)page_entry(fd, page));
        } else if (!strcmp(command, "CALL\n") && prepared) {
            unsigned char resident;
            if (mincore(page, 4096, &resident)) return 1;
            uint64_t pte_before = page_entry(fd, page);
            getrusage(RUSAGE_SELF, &before);
            uint64_t start = rdtsc_begin();
            uint32_t answer = func(input, 5, 0x1234);
            uint64_t end = rdtsc_end();
            getrusage(RUSAGE_SELF, &after);
            uint64_t pte_after = page_entry(fd, page);
            printf("{\"event\":\"call\",\"resident_before\":%u,\"pte_before\":%llu,"
                   "\"pte_after\":%llu,\"cycles\":%llu,\"minflt\":%ld,\"majflt\":%ld,"
                   "\"answer\":%u,\"expected\":%u,\"cpu\":%d}\n",
                   resident & 1, (unsigned long long)pte_before, (unsigned long long)pte_after,
                   (unsigned long long)(end-start), after.ru_minflt-before.ru_minflt,
                   after.ru_majflt-before.ru_majflt, answer, expected, sched_getcpu());
            if (answer != expected) return 1;
            prepared = 0;
        } else if (!strcmp(command, "QUIT\n")) break;
        else return 2;
    }
    close(fd); dlclose(handle); return 0;
}
