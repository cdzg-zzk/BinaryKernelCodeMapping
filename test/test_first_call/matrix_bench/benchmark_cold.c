/*
    1. 配置ftrace脚本：sudo bash ./setup_ftrace.sh
    2. 编译测试程序：gcc -O3 benchmark_cold.c xxh32_static.S -o benchmark_cold -ldl
    3. 执行测试程序：sudo ./benchmark_cold
    4. 获得ftrace输出：sudo cat /sys/kernel/tracing/trace > fault_trace.log
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

typedef uint32_t (*xxh32_func)(const void* input, size_t length, uint32_t seed);

// [修改处] 声明外部汇编函数
extern uint32_t xxh32_static(const void* input, size_t length, uint32_t seed);

/*
    ftrace功能函数
*/
// --- 新增的 ftrace 控制函数 ---
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
    // 将当前进程 PID 写入 ftrace 过滤列表
    ftrace_write("/sys/kernel/tracing/set_ftrace_pid", pid_str);
}
void ftrace_mark(const char *msg) {
    // 写入标记，方便在海量日志中一眼找到我们的测试起点
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

// 检查页驻留状态
// 返回 1: 驻留在物理内存
// 返回 0: 不在物理内存中 (被 swap 或 drop)
// 返回 -1: 页表映射已断开 (Unmapped)
int check_page_status(void* ptr) {
    unsigned char vec[1];
    long page_size = sysconf(_SC_PAGESIZE);
    void *aligned_addr = (void *)((uintptr_t)ptr & ~(page_size - 1));
    
    if (mincore(aligned_addr, page_size, vec) == 0) {
        return vec[0] & 1; 
    }
    return -1; 
}

// [关键修改 2] 外科手术式剔除：只剔除函数开头所在的这 1 个 4KB 页
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

void test_cold_target(const char* target_name, xxh32_func func, const void* input, size_t length, uint32_t seed) {
    printf("==================================================\n");
    printf("Evaluating [%s] in COLD state\n", target_name);
    
    // 1. 预热，拉起页表
    func(input, length, seed);
    
    int status_warm = check_page_status((void*)func);
    printf("[DEBUG] After warm-up, PTE Status: %s\n", status_warm == 1 ? "RESIDENT" : "UNKNOWN");

    // 2. 剔除目标函数的页表映射
    evict_func_page((void*)func);

    // 3. 清空文件系统缓存
    drop_page_cache();

    // 4. [关键修改 3] 在清理完毕后，查看页表和物理页的最终状态
    int status_ready = check_page_status((void*)func);
    if (status_ready == -1) {
        printf("[DEBUG] Ready for COLD test: PTE UNMAPPED (Success!)\n");
    } else if (status_ready == 0) {
        printf("[DEBUG] Ready for COLD test: PTE Exists, but Page Evicted\n");
    } else {
        printf("[DEBUG] Ready for COLD test: PAGE STILL RESIDENT (Expected for Target 1)\n");
    }

    
    // 准备好消息，不要在测量区间内格式化字符串
    char marker_msg[128];
    sprintf(marker_msg, "START_TEST: %s\n", target_name);

    // --- 提前执行一下 getrusage() 防止ftrace中多一次page fault ---
    struct rusage usage_start, usage_end;
    getrusage(RUSAGE_SELF, &usage_start);

    uint64_t start_tsc = rdtsc_begin();
    uint64_t end_tsc = rdtsc_end();

    ftrace_write("/sys/kernel/tracing/tracing_on", "0"); 
    // --- pre-run end ---

    // 1. 先打开 ftrace 开关并打上书签
    ftrace_mark(marker_msg);                           
    ftrace_write("/sys/kernel/tracing/tracing_on", "1"); 

    // --- 极度纯净的核心测量区间开始 ---
    getrusage(RUSAGE_SELF, &usage_start);

    start_tsc = rdtsc_begin();

    func(input, length, seed); // 仅仅测量这一行！

    end_tsc = rdtsc_end();
    getrusage(RUSAGE_SELF, &usage_end);
    // --- 极度纯净的核心测量区间结束 ---

    // 2. 核心执行完后，立刻关掉追踪并打上结束标签
    ftrace_write("/sys/kernel/tracing/tracing_on", "0"); 
    ftrace_mark("END_TEST\n");

    long minor_faults = usage_end.ru_minflt - usage_start.ru_minflt;
    long major_faults = usage_end.ru_majflt - usage_start.ru_majflt;

    printf("\n[RESULT]\n");
    printf("  -> Minor Page Faults       : %ld\n", minor_faults);
    printf("  -> Major Page Faults       : %ld\n", major_faults);
    printf("  -> COLD Cycles             : %lu\n", end_tsc - start_tsc);
    printf("==================================================\n\n");
}

// ... [现有的 test_cold_target 函数保持不变] ...

// ====================================================================
// 新增：WARM 状态测试逻辑
// 仅剔除页表映射 (PTE)，保留物理内存 (Page Cache)
// ====================================================================
void test_warm_target(const char* target_name, xxh32_func func, const void* input, size_t length, uint32_t seed) {
    printf("==================================================\n");
    printf("Evaluating [%s] in WARM state\n", target_name);
    
    // 1. 预热，拉起页表并将文件数据拉入 Page Cache (如果它是冷的话)
    func(input, length, seed);

    // 2. [关键差异] 仅仅剔除目标函数的页表映射
    evict_func_page((void*)func);

    // [注意：绝对不执行 drop_page_cache() !]

    // 3. 查看页表和物理页的状态
    int status_ready = check_page_status((void*)func);
    if (status_ready == -1) {
        printf("[DEBUG] Ready for WARM test: PTE UNMAPPED (Success! Page should be in cache)\n");
    } else {
        printf("[DEBUG] Ready for WARM test: UNEXPECTED STATUS (%d)\n", status_ready);
    }

    char marker_msg[128];
    sprintf(marker_msg, "START_WARM_TEST: %s\n", target_name);

    // 预跑清理环境
    struct rusage usage_start, usage_end;
    getrusage(RUSAGE_SELF, &usage_start);
    uint64_t start_tsc = rdtsc_begin();
    uint64_t end_tsc = rdtsc_end();
    ftrace_write("/sys/kernel/tracing/tracing_on", "0"); 

    // 1. 打开 ftrace 开关并打上书签
    ftrace_mark(marker_msg);                           
    ftrace_write("/sys/kernel/tracing/tracing_on", "1"); 

    // --- 纯净的核心测量区间开始 ---
    getrusage(RUSAGE_SELF, &usage_start);
    start_tsc = rdtsc_begin();

    func(input, length, seed); // 触发 Minor Page Fault

    end_tsc = rdtsc_end();
    getrusage(RUSAGE_SELF, &usage_end);
    // --- 纯净的核心测量区间结束 ---

    // 2. 关掉追踪
    ftrace_write("/sys/kernel/tracing/tracing_on", "0"); 
    ftrace_mark("END_WARM_TEST\n");

    long minor_faults = usage_end.ru_minflt - usage_start.ru_minflt;
    long major_faults = usage_end.ru_majflt - usage_start.ru_majflt;

    printf("\n[RESULT]\n");
    printf("  -> Minor Page Faults       : %ld\n", minor_faults);
    printf("  -> Major Page Faults       : %ld\n", major_faults);
    printf("  -> WARM Cycles             : %lu\n", end_tsc - start_tsc);
    printf("==================================================\n\n");
}

// ====================================================================
// 新增：HOT 状态测试逻辑
// 页表已建立 (PTE Exists)，物理内存也已命中 (Page Cache Hot)
// ====================================================================
void test_hot_target(const char* target_name, xxh32_func func, const void* input, size_t length, uint32_t seed) {
    printf("==================================================\n");
    printf("Evaluating [%s] in HOT state\n", target_name);
    
    // 1. 预热，拉起页表并将文件数据拉入 Page Cache
    func(input, length, seed);

    // [注意：不做任何剔除或清空操作！]

    // 2. 验证状态 (预期状态：完全驻留且已映射)
    int status_ready = check_page_status((void*)func);
    if (status_ready == 1) {
        printf("[DEBUG] Ready for HOT test: PAGE RESIDENT & MAPPED (Success!)\n");
    } else {
        printf("[DEBUG] Ready for HOT test: UNEXPECTED STATUS (%d)\n", status_ready);
    }

    char marker_msg[128];
    sprintf(marker_msg, "START_HOT_TEST: %s\n", target_name);

    // --- 提前执行一下 getrusage() 防止ftrace中多一次page fault ---
    struct rusage usage_start, usage_end;
    getrusage(RUSAGE_SELF, &usage_start);
    uint64_t start_tsc = rdtsc_begin();
    uint64_t end_tsc = rdtsc_end();
    ftrace_write("/sys/kernel/tracing/tracing_on", "0"); 
    // --- pre-run end ---

    ftrace_mark(marker_msg);                           
    ftrace_write("/sys/kernel/tracing/tracing_on", "1"); 

    // --- 极度纯净的核心测量区间开始 ---
    getrusage(RUSAGE_SELF, &usage_start);
    start_tsc = rdtsc_begin();

    func(input, length, seed); // 核心执行：此时不应触发任何缺页中断！

    end_tsc = rdtsc_end();
    getrusage(RUSAGE_SELF, &usage_end);
    // --- 极度纯净的核心测量区间结束 ---

    ftrace_write("/sys/kernel/tracing/tracing_on", "0"); 
    ftrace_mark("END_HOT_TEST\n");

    long minor_faults = usage_end.ru_minflt - usage_start.ru_minflt;
    long major_faults = usage_end.ru_majflt - usage_start.ru_majflt;

    printf("\n[RESULT]\n");
    printf("  -> Minor Page Faults       : %ld\n", minor_faults);
    printf("  -> Major Page Faults       : %ld\n", major_faults);
    printf("  -> HOT Cycles              : %lu\n", end_tsc - start_tsc);
    printf("==================================================\n\n");
}

int main() {
    if (geteuid() != 0) {
        fprintf(stderr, "ERROR: Run as root!\n");
        return 1;
    }
    ftrace_set_pid();
    size_t data_length = 5;
    void* input_data = malloc(data_length);
    memset(input_data, 0, data_length);
    uint32_t seed = 0x1234;

    test_hot_target("Target 3 (Static Embedded)", xxh32_static, input_data, data_length, seed);
    test_warm_target("Target 3 (Static Embedded)", xxh32_static, input_data, data_length, seed);
    test_cold_target("Target 3 (Static Embedded)", xxh32_static, input_data, data_length, seed);

    void* handle2 = dlopen("/home/zzk/BinaryKernelCodeMapping/test/test_first_call/matrix_bench/libclone_xxh32.so", RTLD_NOW | RTLD_LOCAL);
    if (handle2) {
        xxh32_func func2 = (xxh32_func)dlsym(handle2, "clone_xxh32");
        if (func2) {
            test_hot_target("Target 2 (Native SO)", func2, input_data, data_length, seed);
            test_warm_target("Target 2 (Native SO)", func2, input_data, data_length, seed);
            test_cold_target("Target 2 (Native SO)", func2, input_data, data_length, seed);
        }
        dlclose(handle2);
    }

    void* handle1 = dlopen("/home/zzk/BinaryKernelCodeMapping/test/test_first_call/matrix_bench/zzk_xxh32_lkm.ko.so", RTLD_NOW | RTLD_LOCAL);
    if (handle1) {
        xxh32_func func1 = (xxh32_func)dlsym(handle1, "zzk_xxh32");
        if (func1) {
            // 依次执行 HOT -> WARM -> COLD
            test_hot_target("Target 1 (Custom SO)", func1, input_data, data_length, seed);
            test_warm_target("Target 1 (Custom SO)", func1, input_data, data_length, seed);
            test_cold_target("Target 1 (Custom SO)", func1, input_data, data_length, seed);
        }
        dlclose(handle1);
    }

    free(input_data);
    return 0;
}