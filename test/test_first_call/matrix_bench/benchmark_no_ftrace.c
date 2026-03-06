/*
    编译测试程序：gcc -O3 benchmark_no_ftrace.c xxh32_static.S -o benchmark_no_ftrace -ldl -lm
    执行测试程序示例：
      sudo taskset -c 1 ./benchmark_no_ftrace -t 1 -s cold -n 50
*/

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <dlfcn.h>
#include <sys/mman.h>
#include <unistd.h>
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <math.h>

// --- perf_event 必要的头文件 ---
#include <linux/perf_event.h>
#include <linux/hw_breakpoint.h>
#include <sys/syscall.h>
#include <sys/ioctl.h>

typedef uint32_t (*xxh32_func)(const void* input, size_t length, uint32_t seed);
extern uint32_t xxh32_static(const void* input, size_t length, uint32_t seed);

// ====================================================================
// Perf Event 控制逻辑
// ====================================================================
static long perf_event_open(struct perf_event_attr *hw_event, pid_t pid,
                            int cpu, int group_fd, unsigned long flags) {
    return syscall(__NR_perf_event_open, hw_event, pid, cpu, group_fd, flags);
}

int fd_llc  = -1;   // LLC Miss (作为 Group Leader)
int fd_l1d  = -1;   // L1 Data Cache Miss
int fd_l1i  = -1;   // L1 Instruction Cache Miss
int fd_itlb = -1;   // iTLB Miss

void setup_perf_events() {
    struct perf_event_attr pe;

    // 1. 设置 Leader: LLC Load Misses
    memset(&pe, 0, sizeof(struct perf_event_attr));
    pe.type = PERF_TYPE_HW_CACHE;
    pe.size = sizeof(struct perf_event_attr);
    pe.config = (PERF_COUNT_HW_CACHE_LL) | 
                (PERF_COUNT_HW_CACHE_OP_READ << 8) | 
                (PERF_COUNT_HW_CACHE_RESULT_MISS << 16);
    pe.disabled = 1;       // Leader 初始必须关闭
    pe.exclude_kernel = 0; // 监控内核缺页
    pe.exclude_hv = 1;
    pe.read_format = PERF_FORMAT_GROUP;
    
    fd_llc = perf_event_open(&pe, 0, -1, -1, 0);
    if (fd_llc == -1) {
        perror("Failed to open perf_event leader (LLC)");
        exit(EXIT_FAILURE);
    }

    // 2. 兄弟成员: L1 Data Cache Load Misses
    memset(&pe, 0, sizeof(struct perf_event_attr));
    pe.type = PERF_TYPE_HW_CACHE;
    pe.size = sizeof(struct perf_event_attr);
    pe.config = (PERF_COUNT_HW_CACHE_L1D) | 
                (PERF_COUNT_HW_CACHE_OP_READ << 8) | 
                (PERF_COUNT_HW_CACHE_RESULT_MISS << 16);
    pe.exclude_kernel = 0;
    pe.exclude_hv = 1;
    pe.read_format = PERF_FORMAT_GROUP;
    fd_l1d = perf_event_open(&pe, 0, -1, fd_llc, 0);

    // 3. 兄弟成员: L1 Instruction Cache Load Misses
    memset(&pe, 0, sizeof(struct perf_event_attr));
    pe.type = PERF_TYPE_HW_CACHE;
    pe.size = sizeof(struct perf_event_attr);
    pe.config = (PERF_COUNT_HW_CACHE_L1I) | 
                (PERF_COUNT_HW_CACHE_OP_READ << 8) | 
                (PERF_COUNT_HW_CACHE_RESULT_MISS << 16);
    pe.exclude_kernel = 0;
    pe.exclude_hv = 1;
    pe.read_format = PERF_FORMAT_GROUP;
    fd_l1i = perf_event_open(&pe, 0, -1, fd_llc, 0);

    // 4. 兄弟成员: iTLB Load Misses
    memset(&pe, 0, sizeof(struct perf_event_attr));
    pe.type = PERF_TYPE_HW_CACHE;
    pe.size = sizeof(struct perf_event_attr);
    pe.config = (PERF_COUNT_HW_CACHE_ITLB) | 
                (PERF_COUNT_HW_CACHE_OP_READ << 8) | 
                (PERF_COUNT_HW_CACHE_RESULT_MISS << 16);
    pe.exclude_kernel = 0;
    pe.exclude_hv = 1;
    pe.read_format = PERF_FORMAT_GROUP;
    fd_itlb = perf_event_open(&pe, 0, -1, fd_llc, 0);
}

// 对应 PERF_FORMAT_GROUP 的读取结构 (1个Leader + 3个兄弟 = 4个值)
struct perf_read_format {
    uint64_t nr;           // 返回的事件数量 (应为 4)
    uint64_t values[4];    // {llc, l1d, l1i, itlb}
};

// 测量结果数据结构
typedef struct {
    uint64_t cycles;
    uint64_t llc_misses;
    uint64_t l1d_misses;
    uint64_t l1i_misses;
    uint64_t itlb_misses;
} TestResult;

// ====================================================================

static inline uint64_t rdtsc_begin(void) {
    uint32_t lo = 0, hi = 0;
    __asm__ volatile("lfence\nrdtsc" : "=a"(lo), "=d"(hi) : : "memory");
    return ((uint64_t)hi << 32) | lo;
}

static inline uint64_t rdtsc_end(void) {
    uint32_t lo = 0, hi = 0;
    uint32_t aux = 0;
    __asm__ volatile("rdtscp\nlfence" : "=a"(lo), "=d"(hi), "=c"(aux) : : "memory");
    (void)aux;
    return ((uint64_t)hi << 32) | lo;
}

void evict_func_page(void* func_ptr) {
    long page_size = sysconf(_SC_PAGESIZE);
    void *aligned_addr = (void *)((uintptr_t)func_ptr & ~(page_size - 1));
    if (madvise(aligned_addr, page_size, MADV_DONTNEED) != 0) {
        perror("madvise MADV_DONTNEED failed");
    }
}

void drop_page_cache() {
    if (system("sync; echo 3 > /proc/sys/vm/drop_caches") != 0) {
        fprintf(stderr, "Warning: Failed to drop caches.\n");
    }
}

// ====================================================================
// 测试核心逻辑
// ====================================================================

TestResult test_target(int state, const char* target_name, xxh32_func func, const void* input, size_t length, uint32_t seed, int iter) {
    
    TestResult res;
    memset(&res, 0, sizeof(TestResult));

    func(input, length, seed); // 预热
    
    if (state == 2) { 
        evict_func_page((void*)func);
    } else if (state == 3) { 
        evict_func_page((void*)func);
        drop_page_cache(); 
    }

    // --- 极度纯净的测量区间开始 ---
    ioctl(fd_llc, PERF_EVENT_IOC_RESET, PERF_IOC_FLAG_GROUP);
    ioctl(fd_llc, PERF_EVENT_IOC_ENABLE, PERF_IOC_FLAG_GROUP);
    
    uint64_t start_tsc = rdtsc_begin();

    func(input, length, seed); 

    uint64_t end_tsc = rdtsc_end();
    
    ioctl(fd_llc, PERF_EVENT_IOC_DISABLE, PERF_IOC_FLAG_GROUP);
    // --- 测量区间结束 ---

    struct perf_read_format read_group;
    if (read(fd_llc, &read_group, sizeof(struct perf_read_format)) > 0) {
        res.llc_misses   = read_group.values[0];
        res.l1d_misses   = read_group.values[1];
        res.l1i_misses   = read_group.values[2];
        res.itlb_misses  = read_group.values[3];
    }

    res.cycles = end_tsc - start_tsc;

    return res;
}

// ====================================================================
// 统计算法
// ====================================================================
int compare_result(const void *a, const void *b) {
    TestResult *r1 = (TestResult *)a;
    TestResult *r2 = (TestResult *)b;
    if (r1->cycles < r2->cycles) return -1;
    if (r1->cycles > r2->cycles) return 1;
    return 0;
}

void print_statistics(TestResult* results, int count) {
    qsort(results, count, sizeof(TestResult), compare_result);

    double q1 = results[count / 4].cycles;
    double q3 = results[(count * 3) / 4].cycles;
    double iqr = q3 - q1;
    double lower_bound = q1 - 1.5 * iqr;
    double upper_bound = q3 + 1.5 * iqr;

    TestResult filtered[count];
    int filtered_count = 0;
    for (int i = 0; i < count; i++) {
        if (results[i].cycles >= lower_bound && results[i].cycles <= upper_bound) {
            filtered[filtered_count++] = results[i];
        }
    }

    if (filtered_count == 0) {
        printf("Error: All data filtered out!\n");
        return;
    }

    double sum_cyc = 0, sum_llc = 0, sum_l1d = 0, sum_l1i = 0, sum_itlb = 0;
    
    for (int i = 0; i < filtered_count; i++) {
        sum_cyc += filtered[i].cycles;
        sum_llc += filtered[i].llc_misses;
        sum_l1d += filtered[i].l1d_misses;
        sum_l1i += filtered[i].l1i_misses;
        sum_itlb += filtered[i].itlb_misses;
    }

    double mean_cyc = sum_cyc / filtered_count;
    double variance_sum = 0;
    for (int i = 0; i < filtered_count; i++) {
        variance_sum += pow(filtered[i].cycles - mean_cyc, 2);
    }
    
    printf("\n================ [ STATISTICAL RESULTS ] ================\n");
    printf("Valid Runs (IQR) : %d (%.1f%% retained)\n", filtered_count, (float)filtered_count/count*100);
    printf("---------------------------------------------------------\n");
    printf("Median Cycles    : %lu\n", filtered[filtered_count / 2].cycles);
    printf("Mean Cycles      : %.2f (StdDev: %.2f)\n", mean_cyc, sqrt(variance_sum / filtered_count));
    printf("---------------------------------------------------------\n");
    printf("[ Micro-Arch PMC Stats (Absolute Pure Faulting Region) ]\n");
    printf("Mean L1-I Misses : %.2f\n", sum_l1i / filtered_count);
    printf("Mean L1-D Misses : %.2f\n", sum_l1d / filtered_count);
    printf("Mean LLC Misses  : %.2f\n", sum_llc / filtered_count);
    printf("Mean iTLB Misses : %.2f\n", sum_itlb / filtered_count);
    printf("=========================================================\n");
}

int main(int argc, char *argv[]) {
    if (geteuid() != 0) {
        fprintf(stderr, "ERROR: Run as root!\n");
        return 1;
    }

    int target_id = 0; 
    int state_id = 0;  
    int num_runs = 10; 

    int opt;
    while ((opt = getopt(argc, argv, "t:s:n:")) != -1) {
        switch (opt) {
            case 't': target_id = atoi(optarg); break;
            case 's': 
                if (strcmp(optarg, "hot") == 0) state_id = 1;
                else if (strcmp(optarg, "warm") == 0) state_id = 2;
                else if (strcmp(optarg, "cold") == 0) state_id = 3;
                break;
            case 'n': num_runs = atoi(optarg); break;
        }
    }

    setup_perf_events();

    size_t data_length = 5;
    void* input_data = malloc(data_length);
    memset(input_data, 0, data_length);
    uint32_t seed = 0x1234;

    xxh32_func target_func = NULL;
    const char* target_name = "";
    void* handle = NULL;

    if (target_id == 1) {
        handle = dlopen("/home/zzk/BinaryKernelCodeMapping/test/test_first_call/matrix_bench/zzk_xxh32_lkm.so", RTLD_NOW | RTLD_LOCAL);
        if (handle) target_func = (xxh32_func)dlsym(handle, "zzk_xxh32");
        target_name = "Target 1 (Custom SO)";
    } else if (target_id == 2) {
        handle = dlopen("/home/zzk/BinaryKernelCodeMapping/test/test_first_call/matrix_bench/libclone_xxh32.so", RTLD_NOW | RTLD_LOCAL);
        if (handle) target_func = (xxh32_func)dlsym(handle, "clone_xxh32");
        target_name = "Target 2 (Native SO)";
    } else if (target_id == 3) {
        target_func = xxh32_static;
        target_name = "Target 3 (Static Embedded)";
    }

    if (!target_func) return 1;

    const char* state_names[] = {"", "HOT", "WARM", "COLD"};
    printf("Starting Precise PMC evaluation of [%s] in [%s] state (N=%d)...\n", target_name, state_names[state_id], num_runs);

    TestResult* results_arr = malloc(num_runs * sizeof(TestResult));

    for (int i = 0; i < num_runs; i++) {
        results_arr[i] = test_target(state_id, target_name, target_func, input_data, data_length, seed, i);
    }

    print_statistics(results_arr, num_runs);

    if (handle) dlclose(handle);
    free(input_data);
    free(results_arr);
    return 0;
}