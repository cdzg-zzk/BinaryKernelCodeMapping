// SPDX-License-Identifier: GPL-2.0
/*
 * Micro-benchmark Experiment 2: Isolate D-Cache (Data Flow) Overhead.
 * Uses Xorshift to cause severe L1/L2/L3 D-Cache misses, but fills the
 * entire GOT with a single target to guarantee 100% BTB Prediction Hit.
 * Includes optimization barriers to prevent GCC devirtualization.
 */

 #include <linux/module.h>
 #include <linux/kernel.h>
 #include <linux/init.h>
 #include <linux/smp.h>
 #include <linux/preempt.h>
 #include <linux/irqflags.h>
 #include <linux/slab.h>
 #include <linux/sort.h>
 
 MODULE_LICENSE("GPL");
 MODULE_AUTHOR("System Researcher");
 MODULE_DESCRIPTION("Exp 2: Pure D-Cache Isolation Jitter Benchmark");
 
 static unsigned int cpu = 0;
 module_param(cpu, uint, 0644);
 
 static unsigned int repeats = 10;
 module_param(repeats, uint, 0644);
 
 static unsigned int iterations = 1000;
 module_param(iterations, uint, 0644);
 
 static unsigned int warmup_runs = 3;
 module_param(warmup_runs, uint, 0644);
 
 /* ---------------------------------------------------------
  * 1. Precision Timing Primitives
  * --------------------------------------------------------- */
static __always_inline u64 rdtsc_begin(void)
{
    unsigned int lo, hi;
    /*
    * 第1个 lfence：确保之前的循环控制等指令全部彻底执行完。
    * rdtsc：按下秒表开始计时。
    * 第2个 lfence：确保秒表按下去了，后面的访存指令 (mov) 才能开始执行。
    */
    asm volatile("lfence\n\trdtsc\n\tlfence" : "=a"(lo), "=d"(hi) :: "memory");
    return ((u64)hi << 32) | lo;
}

static __always_inline u64 rdtsc_end(void)
{
    unsigned int lo, hi;
    /*
    * 第1个 lfence：【极其关键】死死拦住，必须等前面的 mov 和 call 彻底退役(Retire)！
    * rdtsc：按下秒表停止计时。
    * 第2个 lfence：防止后面的指令提前跑上来干扰。
    */
    asm volatile("lfence\n\trdtsc\n\tlfence" : "=a"(lo), "=d"(hi) :: "memory");
    return ((u64)hi << 32) | lo;
}
 /* ---------------------------------------------------------
  * 2. Single Target Generation (Guarantees BTB Hit)
  * --------------------------------------------------------- */
 static noinline void notrace dummy_target(void) 
 { 
     asm volatile(""); 
 }
 
 /* ---------------------------------------------------------
  * 3. The Massive Pseudo-GOT Table (Up to 8 MB)
  * --------------------------------------------------------- */
 #define MAX_GOT_ENTRIES 1048576 
 static void (*pseudo_got[MAX_GOT_ENTRIES])(void) __read_mostly;
 
 static const u32 test_sizes[] = {
     8, 64, 512, 1024, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576
 };
 #define NUM_TEST_CASES (sizeof(test_sizes) / sizeof(test_sizes[0]))
 
 /* ---------------------------------------------------------
  * 4. Measurement Logic
  * --------------------------------------------------------- */
 static int cmp_u64(const void *a, const void *b)
 {
     u64 val_a = *(const u64 *)a;
     u64 val_b = *(const u64 *)b;
     return (val_a < val_b) ? -1 : ((val_a > val_b) ? 1 : 0);
 }
 
 static u64 measure_working_set(u32 got_entries, u64 *results_buf)
 {
     int i;
     unsigned long flags;
     void *target;
     void (*fn)(void);
     u32 mask = got_entries - 1;
     u32 state = 24601 + got_entries; 
 
     // 预热阶段：让 BTB 提前学会这个唯一的跳转目标，同时建立真实的缓存驱逐环境
     for (i = 0; i < got_entries; i++) {
         state ^= state << 13;
         state ^= state >> 17;
         state ^= state << 5;
         u32 idx = state & mask;
         
         target = READ_ONCE(pseudo_got[idx]);
         asm volatile("" : "+r" (target)); // 编译器黑盒屏障
         fn = target;
         fn();
     }
 
     preempt_disable();
     local_irq_save(flags);
 
     for (i = 0; i < iterations; i++) {
         state ^= state << 13;
         state ^= state >> 17;
         state ^= state << 5;
         u32 idx = state & mask;
 
         u64 start = rdtsc_begin();
         
         // 动作 A: 遭遇极其严重的 D-Cache Miss (真实主存读取)
         target = READ_ONCE(pseudo_got[idx]);  
         
         // 【核心修复】：粉碎编译器的“常量传播/去虚化”优化
         asm volatile("" : "+r" (target)); 
         
         // 动作 B: 遭遇完美的 BTB Hit (预测开销为 0)
         fn = target;
         fn();
         
         u64 end = rdtsc_end();
 
         results_buf[i] = end - start;
     }
 
     local_irq_restore(flags);
     preempt_enable();
 
     sort(results_buf, iterations, sizeof(u64), cmp_u64, NULL);
     return results_buf[iterations / 2];
 }
 
 static void run_bench_on_cpu(void *info)
 {
     int i, r;
     u64 *results_buf;
     u64 case_averages[NUM_TEST_CASES] = {0};
 
     results_buf = kmalloc_array(iterations, sizeof(u64), GFP_KERNEL);
     if (!results_buf) {
         pr_err("test_btb_exp2: failed to allocate memory\n");
         return;
     }
 
     pr_info("test_btb_exp2: CPU=%u repeats=%u iterations=%u warmup=%u (Pure D-Cache Isolation)\n", 
             cpu, repeats, iterations, warmup_runs);
 
     for (r = 0; r < warmup_runs; r++) {
         for (i = 0; i < NUM_TEST_CASES; i++) {
             measure_working_set(test_sizes[i], results_buf);
         }
     }
 
     for (r = 0; r < repeats; r++) {
         for (i = 0; i < NUM_TEST_CASES; i++) {
             u64 median = measure_working_set(test_sizes[i], results_buf);
             case_averages[i] += median;
         }
     }
 
     for (i = 0; i < NUM_TEST_CASES; i++) {
         case_averages[i] /= repeats;
     }
     
     u64 baseline_cycles = case_averages[0];
 
     pr_info("test_btb_exp2: --- Final Averaged Results (Baseline L1 Hit: ~%llu cycles) ---\n", baseline_cycles);
     for (i = 0; i < NUM_TEST_CASES; i++) {
         u64 raw = case_averages[i];
         s64 overhead = (s64)raw - (s64)baseline_cycles;
         u32 size_kb = (test_sizes[i] * 8) / 1024;
         
         if (i == 0) {
             pr_info("test_btb_exp2: GOT Entries = %-7u (%4u KB) : raw = %llu cycles (Baseline)\n", 
                     test_sizes[i], size_kb, raw);
         } else {
             pr_info("test_btb_exp2: GOT Entries = %-7u (%4u KB) : raw = %llu cycles, pure overhead = %+lld cycles\n", 
                     test_sizes[i], size_kb, raw, overhead);
         }
     }
     pr_info("test_btb_exp2: --- Test Complete ---\n");
 
     kfree(results_buf);
 }
 
 static int __init test_btb_init(void)
 {
     int i;
     // 【核心解耦点】：整个庞大的内存工作集里，装的全部是唯一的单跳目标
     for (i = 0; i < MAX_GOT_ENTRIES; i++) {
         pseudo_got[i] = dummy_target;
     }
 
     if (smp_call_function_single(cpu, run_bench_on_cpu, NULL, 1)) {
         pr_err("test_btb_exp2: failed to dispatch to CPU %d\n", cpu);
         return -EINVAL;
     }
     return 0; 
 }
 
 static void __exit test_btb_exit(void)
 {
     pr_info("test_btb_exp2: Unloaded.\n");
 }
 
 module_init(test_btb_init);
 module_exit(test_btb_exit);