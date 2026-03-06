/*
    编译测试程序：gcc -O3 benchmark_single.c xxh32_static.S -o benchmark_single -ldl -lm
    执行测试程序示例：
      sudo ./benchmark_single -t 1 -s cold -n 100
      (测试 Target 1, COLD 状态. 将自动执行 2次Ftrace + 100次性能测试 + 2次Ftrace)
*/

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <dlfcn.h>
#include <sys/mman.h>
#include <unistd.h>
#include <sys/resource.h>
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <math.h>

typedef uint32_t (*xxh32_func)(const void* input, size_t length, uint32_t seed);

extern uint32_t xxh32_static(const void* input, size_t length, uint32_t seed);

// --- ftrace 控制函数 ---
void ftrace_write(const char *path, const char *val) {
    int fd = open(path, O_WRONLY);
    if (fd >= 0) {
        if(write(fd, val, strlen(val)) == -1) {
            perror("write");
        }
        close(fd);
    }
}

void ftrace_set_pid() {
    char pid_str[32];
    sprintf(pid_str, "%d", getpid());
    ftrace_write("/sys/kernel/tracing/set_ftrace_pid", pid_str);
}

void ftrace_mark(const char *msg) {
    return;
    ftrace_write("/sys/kernel/tracing/trace_marker", msg);
}

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
// 测试核心逻辑 (新增 enable_ftrace 开关与阶段前缀 marker_prefix)
// ====================================================================

uint64_t test_target(int state, const char* target_name, xxh32_func func, const void* input, size_t length, uint32_t seed, const char* marker_prefix, int iter, long* min_flt, long* maj_flt, int enable_ftrace) {
    
    // 1. 预热
    func(input, length, seed);
    
    // 2. 根据状态执行剥离操作
    if (state == 2) { // WARM
        evict_func_page((void*)func);
    } else if (state == 3) { // COLD
        evict_func_page((void*)func);
        drop_page_cache();
    }

    char marker_msg[128];
    sprintf(marker_msg, "START_%s_ITER_%d: %s\n", marker_prefix, iter, target_name);

    struct rusage usage_start, usage_end;
    getrusage(RUSAGE_SELF, &usage_start); // 预执行防止缺页
    uint64_t start_tsc = rdtsc_begin();
    uint64_t end_tsc = rdtsc_end();

    if (enable_ftrace) {
        ftrace_write("/sys/kernel/tracing/tracing_on", "0"); 
        ftrace_mark(marker_msg);                           
        ftrace_write("/sys/kernel/tracing/tracing_on", "1"); 
    }

    // --- 极度纯净的核心测量区间开始 ---
    getrusage(RUSAGE_SELF, &usage_start);
    start_tsc = rdtsc_begin();

    func(input, length, seed); 

    end_tsc = rdtsc_end();
    getrusage(RUSAGE_SELF, &usage_end);
    // --- 极度纯净的核心测量区间结束 ---

    if (enable_ftrace) {
        ftrace_write("/sys/kernel/tracing/tracing_on", "0"); 
        char end_msg[64];
        sprintf(end_msg, "END_%s_ITER_%d\n", marker_prefix, iter);
        ftrace_mark(end_msg);
    }

    *min_flt = usage_end.ru_minflt - usage_start.ru_minflt;
    *maj_flt = usage_end.ru_majflt - usage_start.ru_majflt;

    return end_tsc - start_tsc;
}

// ====================================================================
// 统计学处理逻辑 (保持不变)
// ====================================================================
int compare_uint64(const void *a, const void *b) {
    uint64_t arg1 = *(const uint64_t *)a;
    uint64_t arg2 = *(const uint64_t *)b;
    if (arg1 < arg2) return -1;
    if (arg1 > arg2) return 1;
    return 0;
}

void print_statistics(uint64_t* cycles, int count, long total_min_flt, long total_maj_flt) {
    qsort(cycles, count, sizeof(uint64_t), compare_uint64);

    double q1 = cycles[count / 4];
    double q3 = cycles[(count * 3) / 4];
    double iqr = q3 - q1;
    double lower_bound = q1 - 1.5 * iqr;
    double upper_bound = q3 + 1.5 * iqr;

    uint64_t filtered[count];
    int filtered_count = 0;
    for (int i = 0; i < count; i++) {
        if (cycles[i] >= lower_bound && cycles[i] <= upper_bound) {
            filtered[filtered_count++] = cycles[i];
        }
    }

    if (filtered_count == 0) {
        printf("Error: All data filtered out!\n");
        return;
    }

    double sum = 0;
    for (int i = 0; i < filtered_count; i++) sum += filtered[i];
    double mean = sum / filtered_count;

    double variance_sum = 0;
    for (int i = 0; i < filtered_count; i++) variance_sum += pow(filtered[i] - mean, 2);
    double stddev = sqrt(variance_sum / filtered_count);
    
    uint64_t median = filtered[filtered_count / 2];

    printf("\n================ [ STATISTICAL RESULTS ] ================\n");
    printf("Total Runs      : %d\n", count);
    printf("Valid Runs (IQR): %d (%.1f%% retained)\n", filtered_count, (float)filtered_count/count*100);
    printf("Avg Minor Faults: %.2f per run\n", (float)total_min_flt / count);
    printf("Avg Major Faults: %.2f per run\n", (float)total_maj_flt / count);
    printf("---------------------------------------------------------\n");
    printf("Median Cycles   : %lu\n", median);
    printf("Mean Cycles     : %.2f\n", mean);
    printf("Std Deviation   : %.2f\n", stddev);
    printf("=========================================================\n");
}

int main(int argc, char *argv[]) {
    if (geteuid() != 0) {
        fprintf(stderr, "ERROR: Run as root!\n");
        return 1;
    }

    int target_id = 0; // 1: Custom, 2: Native, 3: Static
    int state_id = 0;  // 1: Hot, 2: Warm, 3: Cold
    int num_runs = 100;

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
            default:
                fprintf(stderr, "Usage: %s -t <1|2|3> -s <hot|warm|cold> [-n iterations]\n", argv[0]);
                return 1;
        }
    }

    if (target_id < 1 || target_id > 3 || state_id < 1 || state_id > 3) {
        fprintf(stderr, "Invalid target or state. Example: -t 1 -s cold -n 100\n");
        return 1;
    }

    const char* state_names[] = {"", "HOT", "WARM", "COLD"};
    
    // --- 【关键】在开始前清空旧的 Ftrace 缓冲区 ---
    ftrace_write("/sys/kernel/tracing/trace", "");
    ftrace_set_pid();

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

    if (!target_func) {
        fprintf(stderr, "Failed to load target function.\n");
        if (handle) dlclose(handle);
        free(input_data);
        return 1;
    }

    printf("Starting 2+N+2 evaluation of [%s] in [%s] state (N=%d)...\n", target_name, state_names[state_id], num_runs);

    uint64_t* cycles_arr = malloc(num_runs * sizeof(uint64_t));
    long total_min_flt = 0, total_maj_flt = 0;
    long dummy_min, dummy_maj;

    // ================== 第 1 阶段：前置 2 次 Ftrace 抓取 ==================
    printf("[Phase 1/3] Running 2 Pre-Ftrace Iterations...\n");
    for (int i = 1; i <= 1; i++) {
        test_target(state_id, target_name, target_func, input_data, data_length, seed, "PRE_FTRACE", i, &dummy_min, &dummy_maj, 1);
    }

    // ================== 第 2 阶段：N 次核心性能循环 ==================
    printf("[Phase 2/3] Running %d Pure Performance Iterations...\n", num_runs);
    for (int i = 0; i < num_runs; i++) {
        long min_flt = 0, maj_flt = 0;
        // 注意：此处开启 Ftrace 参数为 0
        cycles_arr[i] = test_target(state_id, target_name, target_func, input_data, data_length, seed, "PERF", i, &min_flt, &maj_flt, 0);
        total_min_flt += min_flt;
        total_maj_flt += maj_flt;
    }

    // // ================== 第 3 阶段：后置 2 次 Ftrace 抓取 ==================
    // printf("[Phase 3/3] Running 2 Post-Ftrace Iterations...\n");
    // for (int i = 1; i <= 2; i++) {
    //     test_target(state_id, target_name, target_func, input_data, data_length, seed, "POST_FTRACE", i, &dummy_min, &dummy_maj, 1);
    // }

    // 打印性能统计结果
    print_statistics(cycles_arr, num_runs, total_min_flt, total_maj_flt);

    // ================== 自动导出日志文件 ==================
    char dump_cmd[256];
    char log_filename[128];
    sprintf(log_filename, "ftrace_T%d_%s.log", target_id, state_names[state_id]);
    sprintf(dump_cmd, "cat /sys/kernel/tracing/trace > %s", log_filename);
    printf("Exporting ftrace log to: %s\n", log_filename);
    if (system(dump_cmd) != 0) {
         fprintf(stderr, "Failed to export ftrace log.\n");
    }
    if (system("echo > /sys/kernel/tracing/trace") != 0) {
        fprintf(stderr, "Failed to clear ftrace log.\n");
    }
    if (handle) dlclose(handle);
    free(input_data);
    free(cycles_arr);
    return 0;
}