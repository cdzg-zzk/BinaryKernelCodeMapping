#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/preempt.h>
#include <linux/irqflags.h>

static __always_inline u64 rdtsc_begin(void) {
    unsigned int lo, hi;
    asm volatile("rdtsc" : "=a"(lo), "=d"(hi) :: "memory");
    return ((u64)hi << 32) | lo;
}

static __always_inline u64 rdtsc_end(void) {
    unsigned int lo, hi;
    asm volatile("rdtsc" : "=a"(lo), "=d"(hi) :: "memory");
    return ((u64)hi << 32) | lo;
}

// 引入庞大的机器生成代码（包含数组声明和乱序逻辑）
#include "generated_calls.h"

static int __init test_macro_init(void) {
    INIT_GOT_TABLE();
    run_all_sizes();
    return 0;
}

static void __exit test_macro_exit(void) {
    pr_info("Macro-benchmark Unloaded.\n");
}

module_init(test_macro_init);
module_exit(test_macro_exit);
MODULE_LICENSE("GPL");