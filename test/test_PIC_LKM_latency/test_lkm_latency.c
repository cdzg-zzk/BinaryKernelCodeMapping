// SPDX-License-Identifier: GPL-2.0
/*
 * Micro-benchmark for indirect call overhead using RDTSC.
 * Compares direct calls vs function-pointer (pseudo-GOT-style) calls, and
 * evaluates how target predictability affects the indirect-call cost.
 */

#include <linux/errno.h>
#include <linux/init.h>
#include <linux/irqflags.h>
#include <linux/kernel.h>
#include <linux/log2.h>
#include <linux/math64.h>
#include <linux/minmax.h>
#include <linux/module.h>
#include <linux/preempt.h>
#include <linux/slab.h>
#include <linux/smp.h>
#include <linux/types.h>
#include <linux/compiler.h>
#include <linux/cpu.h>

#define MAX_TARGETS 32
#define MAX_PATTERN_LEN (64 * 1024)
#define MAX_RANDOM_SWEEP 4

enum random_mode {
	RANDOM_MODE_FN_PATTERN = 0,
};

static unsigned int iterations = 1000000;
module_param(iterations, uint, 0644);
MODULE_PARM_DESC(iterations, "Loop iterations per run");

static unsigned int repeats = 10;
module_param(repeats, uint, 0644);
MODULE_PARM_DESC(repeats, "Number of repeated runs");

static unsigned int warmup_runs = 3;
module_param(warmup_runs, uint, 0644);
MODULE_PARM_DESC(warmup_runs, "Warm-up runs before measurement");

static unsigned int warmup_iterations = 100000;
module_param(warmup_iterations, uint, 0644);
MODULE_PARM_DESC(warmup_iterations, "Iterations per warm-up run");

static bool enable_alt2 = true;
module_param(enable_alt2, bool, 0644);
MODULE_PARM_DESC(enable_alt2, "Enable 2-target alternating indirect calls");

static bool enable_random = true;
module_param(enable_random, bool, 0644);
MODULE_PARM_DESC(enable_random, "Enable random multi-target indirect calls");

static unsigned int random_targets = 16;
module_param(random_targets, uint, 0644);
MODULE_PARM_DESC(random_targets, "Number of targets for random mode (<= 32)");

static bool random_sweep = true;
module_param(random_sweep, bool, 0644);
MODULE_PARM_DESC(random_sweep, "Sweep random targets: 4/8/16/32 (ignores random_targets)");

static unsigned int pattern_len = 4096;
module_param(pattern_len, uint, 0644);
MODULE_PARM_DESC(pattern_len, "Random pattern length (power of two, <= 65536)");

static unsigned int seed = 1;
module_param(seed, uint, 0644);
MODULE_PARM_DESC(seed, "Seed for random target pattern generation");

static unsigned int cpu = 0;
module_param(cpu, uint, 0644);
MODULE_PARM_DESC(cpu, "CPU to run the benchmark on");

static __always_inline u64 rdtsc_begin(void)
{
	unsigned int lo, hi;

	asm volatile("lfence\n\trdtsc" : "=a"(lo), "=d"(hi) :: "memory");
	return ((u64)hi << 32) | lo;
}

static __always_inline u64 rdtsc_end(void)
{
	unsigned int lo, hi;

	asm volatile("rdtsc\n\tlfence" : "=a"(lo), "=d"(hi) :: "memory");
	return ((u64)hi << 32) | lo;
}

static noinline void bench_stub_0(void)
{
	asm volatile("movl %0, %%eax" :: "i"(0) : "eax", "memory");
}

static noinline void bench_stub_1(void)
{
	asm volatile("movl %0, %%eax" :: "i"(1) : "eax", "memory");
}

static noinline void bench_stub_2(void)
{
	asm volatile("movl %0, %%eax" :: "i"(2) : "eax", "memory");
}

static noinline void bench_stub_3(void)
{
	asm volatile("movl %0, %%eax" :: "i"(3) : "eax", "memory");
}

static noinline void bench_stub_4(void)
{
	asm volatile("movl %0, %%eax" :: "i"(4) : "eax", "memory");
}

static noinline void bench_stub_5(void)
{
	asm volatile("movl %0, %%eax" :: "i"(5) : "eax", "memory");
}

static noinline void bench_stub_6(void)
{
	asm volatile("movl %0, %%eax" :: "i"(6) : "eax", "memory");
}

static noinline void bench_stub_7(void)
{
	asm volatile("movl %0, %%eax" :: "i"(7) : "eax", "memory");
}

static noinline void bench_stub_8(void)
{
	asm volatile("movl %0, %%eax" :: "i"(8) : "eax", "memory");
}

static noinline void bench_stub_9(void)
{
	asm volatile("movl %0, %%eax" :: "i"(9) : "eax", "memory");
}

static noinline void bench_stub_10(void)
{
	asm volatile("movl %0, %%eax" :: "i"(10) : "eax", "memory");
}

static noinline void bench_stub_11(void)
{
	asm volatile("movl %0, %%eax" :: "i"(11) : "eax", "memory");
}

static noinline void bench_stub_12(void)
{
	asm volatile("movl %0, %%eax" :: "i"(12) : "eax", "memory");
}

static noinline void bench_stub_13(void)
{
	asm volatile("movl %0, %%eax" :: "i"(13) : "eax", "memory");
}

static noinline void bench_stub_14(void)
{
	asm volatile("movl %0, %%eax" :: "i"(14) : "eax", "memory");
}

static noinline void bench_stub_15(void)
{
	asm volatile("movl %0, %%eax" :: "i"(15) : "eax", "memory");
}

static noinline void bench_stub_16(void)
{
	asm volatile("movl %0, %%eax" :: "i"(16) : "eax", "memory");
}

static noinline void bench_stub_17(void)
{
	asm volatile("movl %0, %%eax" :: "i"(17) : "eax", "memory");
}

static noinline void bench_stub_18(void)
{
	asm volatile("movl %0, %%eax" :: "i"(18) : "eax", "memory");
}

static noinline void bench_stub_19(void)
{
	asm volatile("movl %0, %%eax" :: "i"(19) : "eax", "memory");
}

static noinline void bench_stub_20(void)
{
	asm volatile("movl %0, %%eax" :: "i"(20) : "eax", "memory");
}

static noinline void bench_stub_21(void)
{
	asm volatile("movl %0, %%eax" :: "i"(21) : "eax", "memory");
}

static noinline void bench_stub_22(void)
{
	asm volatile("movl %0, %%eax" :: "i"(22) : "eax", "memory");
}

static noinline void bench_stub_23(void)
{
	asm volatile("movl %0, %%eax" :: "i"(23) : "eax", "memory");
}

static noinline void bench_stub_24(void)
{
	asm volatile("movl %0, %%eax" :: "i"(24) : "eax", "memory");
}

static noinline void bench_stub_25(void)
{
	asm volatile("movl %0, %%eax" :: "i"(25) : "eax", "memory");
}

static noinline void bench_stub_26(void)
{
	asm volatile("movl %0, %%eax" :: "i"(26) : "eax", "memory");
}

static noinline void bench_stub_27(void)
{
	asm volatile("movl %0, %%eax" :: "i"(27) : "eax", "memory");
}

static noinline void bench_stub_28(void)
{
	asm volatile("movl %0, %%eax" :: "i"(28) : "eax", "memory");
}

static noinline void bench_stub_29(void)
{
	asm volatile("movl %0, %%eax" :: "i"(29) : "eax", "memory");
}

static noinline void bench_stub_30(void)
{
	asm volatile("movl %0, %%eax" :: "i"(30) : "eax", "memory");
}

static noinline void bench_stub_31(void)
{
	asm volatile("movl %0, %%eax" :: "i"(31) : "eax", "memory");
}

static void (*got_fns[MAX_TARGETS])(void);

static u64 bench_direct(unsigned int iters, unsigned int batch_iters)
{
	unsigned int done = 0;
	u64 total = 0;

	while (done < iters) {
		unsigned int i;
		unsigned int n = iters - done;
		unsigned long flags;
		u64 start, end;

		if (n > batch_iters)
			n = batch_iters;

		preempt_disable();
		local_irq_save(flags);
		start = rdtsc_begin();
		for (i = 0; i < n; i++)
			bench_stub_0();
		end = rdtsc_end();
		local_irq_restore(flags);
		preempt_enable();

		total += end - start;
		done += n;
	}

	return total;
}

static u64 bench_indirect_stable(unsigned int iters, unsigned int batch_iters)
{
	unsigned int done = 0;
	u64 total = 0;

	while (done < iters) {
		unsigned int i;
		unsigned int n = iters - done;
		unsigned long flags;
		u64 start, end;

		if (n > batch_iters)
			n = batch_iters;

		preempt_disable();
		local_irq_save(flags);
		start = rdtsc_begin();
		for (i = 0; i < n; i++) {
			void (*fn)(void) = READ_ONCE(got_fns[0]);

			fn();
		}
		end = rdtsc_end();
		local_irq_restore(flags);
		preempt_enable();

		total += end - start;
		done += n;
	}

	return total;
}

static u64 bench_indirect_alt2(unsigned int iters, unsigned int batch_iters)
{
	unsigned int done = 0;
	u64 total = 0;

	while (done < iters) {
		unsigned int i;
		unsigned int n = iters - done;
		unsigned long flags;
		u64 start, end;

		if (n > batch_iters)
			n = batch_iters;

		preempt_disable();
		local_irq_save(flags);
		start = rdtsc_begin();
		for (i = 0; i < n; i++) {
			void (*fn)(void) = READ_ONCE(got_fns[i & 1]);

			fn();
		}
		end = rdtsc_end();
		local_irq_restore(flags);
		preempt_enable();

		total += end - start;
		done += n;
	}

	return total;
}

static u64 bench_indirect_random(unsigned int iters, unsigned int batch_iters,
				 void (**pattern)(void), unsigned int pattern_mask)
{
	unsigned int done = 0;
	u64 total = 0;

	while (done < iters) {
		unsigned int i;
		unsigned int n = iters - done;
		unsigned long flags;
		u64 start, end;

		if (n > batch_iters)
			n = batch_iters;

		preempt_disable();
		local_irq_save(flags);
		start = rdtsc_begin();
		for (i = 0; i < n; i++) {
			void (*fn)(void) =
				READ_ONCE(pattern[(done + i) & pattern_mask]);

			fn();
		}
		end = rdtsc_end();
		local_irq_restore(flags);
		preempt_enable();

		total += end - start;
		done += n;
	}

	return total;
}

struct bench_args {
	unsigned int iterations;
	unsigned int repeats;
	unsigned int batch_iters;
	unsigned int warmup_runs;
	unsigned int warmup_iters;
	u64 *direct_runs;
	u64 *stable_runs;
	u64 *alt2_runs;
	unsigned int random_mode;
	unsigned int random_count;
	unsigned int random_targets[MAX_RANDOM_SWEEP];
	unsigned int random_pattern_mask;
	void (**random_patterns)(void);
	u64 *random_runs;
};

static void run_bench_on_cpu(void *info)
{
	struct bench_args *args = info;
	unsigned int r;
	unsigned int pattern_len = args->random_pattern_mask + 1;

	if (args->warmup_runs && args->warmup_iters) {
		for (r = 0; r < args->warmup_runs; r++) {
			unsigned int k;

			bench_direct(args->warmup_iters, args->batch_iters);
			bench_indirect_stable(args->warmup_iters, args->batch_iters);
			if (args->alt2_runs)
				bench_indirect_alt2(args->warmup_iters,
						    args->batch_iters);
			if (args->random_runs) {
				for (k = 0; k < args->random_count; k++) {
					void (**pattern)(void) = args->random_patterns +
						(k * pattern_len);

					bench_indirect_random(args->warmup_iters,
							      args->batch_iters,
							      pattern,
							      args->random_pattern_mask);
				}
			}
		}
	}

	for (r = 0; r < args->repeats; r++) {
		unsigned int k;

		args->direct_runs[r] = bench_direct(args->iterations,
						    args->batch_iters);
		args->stable_runs[r] = bench_indirect_stable(args->iterations,
							     args->batch_iters);
		if (args->alt2_runs)
			args->alt2_runs[r] = bench_indirect_alt2(args->iterations,
								 args->batch_iters);
		if (args->random_runs) {
			for (k = 0; k < args->random_count; k++) {
				void (**pattern)(void) = args->random_patterns +
					(k * pattern_len);

				args->random_runs[r * args->random_count + k] =
					bench_indirect_random(args->iterations,
							      args->batch_iters,
							      pattern,
							      args->random_pattern_mask);
			}
		}
	}
}

static u32 xorshift32(u32 *state)
{
	u32 x = *state;

	x ^= x << 13;
	x ^= x >> 17;
	x ^= x << 5;
	*state = x;
	return x;
}

static void print_avg_overhead(const char *label, u64 direct_per_1e6, u64 mode_per_1e6)
{
	s64 diff_per_1e6 = (s64)mode_per_1e6 - (s64)direct_per_1e6;
	u64 diff_abs_1e6 = diff_per_1e6 < 0 ? -diff_per_1e6 : diff_per_1e6;
	const char *diff_sign = diff_per_1e6 < 0 ? "-" : "";

	pr_info("test_lkm_latency: avg %s=%llu.%06llu cycles/call, overhead=%s%llu.%06llu cycles/call\n",
		label,
		mode_per_1e6 / 1000000, mode_per_1e6 % 1000000,
		diff_sign, diff_abs_1e6 / 1000000, diff_abs_1e6 % 1000000);
}

static int __init test_lkm_latency_init(void)
{
	unsigned int r;
	unsigned int batch_iters;
	struct bench_args args;
	u64 *direct_runs;
	u64 *stable_runs;
	u64 *alt2_runs = NULL;
	u64 *random_runs = NULL;
	u64 direct_total = 0;
	u64 stable_total = 0;
	u64 alt2_total = 0;
	u64 random_total[MAX_RANDOM_SWEEP] = {};
	u64 total_iters;
	u64 direct_per_1e6;
	u64 stable_per_1e6;
	u64 alt2_per_1e6;
	int ret;
	unsigned int warmup_iters;
	unsigned int rand_targets_list[MAX_RANDOM_SWEEP];
	unsigned int rand_targets_count = 0;
	unsigned int rand_pat_len = 0;
	unsigned int rand_pat_mask = 0;
	u32 effective_seed;
	void (**random_patterns)(void) = NULL;
	unsigned int i;
	char random_targets_str[64] = "n/a";

	static void (*const stub_fns[MAX_TARGETS])(void) = {
		bench_stub_0,  bench_stub_1,  bench_stub_2,  bench_stub_3,
		bench_stub_4,  bench_stub_5,  bench_stub_6,  bench_stub_7,
		bench_stub_8,  bench_stub_9,  bench_stub_10, bench_stub_11,
		bench_stub_12, bench_stub_13, bench_stub_14, bench_stub_15,
		bench_stub_16, bench_stub_17, bench_stub_18, bench_stub_19,
		bench_stub_20, bench_stub_21, bench_stub_22, bench_stub_23,
		bench_stub_24, bench_stub_25, bench_stub_26, bench_stub_27,
		bench_stub_28, bench_stub_29, bench_stub_30, bench_stub_31,
	};

	if (!iterations || !repeats) {
		pr_err("test_lkm_latency: iterations and repeats must be > 0\n");
		return -EINVAL;
	}

	effective_seed = seed ? seed : 1;

	for (i = 0; i < MAX_TARGETS; i++)
		WRITE_ONCE(got_fns[i], stub_fns[i]);

	batch_iters = iterations > 10000 ? 10000 : iterations;
	if (!batch_iters)
		batch_iters = 1;

	warmup_iters = min_t(unsigned int, iterations, warmup_iterations);

	direct_runs = kmalloc_array(repeats, sizeof(*direct_runs), GFP_KERNEL);
	if (!direct_runs)
		return -ENOMEM;

	stable_runs = kmalloc_array(repeats, sizeof(*stable_runs), GFP_KERNEL);
	if (!stable_runs) {
		kfree(direct_runs);
		return -ENOMEM;
	}

	if (enable_alt2) {
		alt2_runs = kmalloc_array(repeats, sizeof(*alt2_runs), GFP_KERNEL);
		if (!alt2_runs) {
			kfree(stable_runs);
			kfree(direct_runs);
			return -ENOMEM;
		}
	}

	if (enable_random) {
		if (random_sweep) {
			static const unsigned int sweep[MAX_RANDOM_SWEEP] = { 4, 8, 16, 32 };

			for (i = 0; i < MAX_RANDOM_SWEEP; i++)
				rand_targets_list[rand_targets_count++] =
					min_t(unsigned int, sweep[i], MAX_TARGETS);
		} else {
			unsigned int t = min_t(unsigned int, random_targets, MAX_TARGETS);

			if (t >= 2) {
				if (!is_power_of_2(t))
					t = rounddown_pow_of_two(t);
				if (t >= 2)
					rand_targets_list[rand_targets_count++] = t;
			}
		}
	}

	if (rand_targets_count) {
		int len = 0;

		rand_pat_len = clamp_t(unsigned int, pattern_len, 2, MAX_PATTERN_LEN);
		rand_pat_len = rounddown_pow_of_two(rand_pat_len);
		if (rand_pat_len < 2)
			rand_pat_len = 2;
		rand_pat_mask = rand_pat_len - 1;

		random_patterns = kmalloc_array((size_t)rand_pat_len * rand_targets_count,
						sizeof(*random_patterns), GFP_KERNEL);
		if (!random_patterns) {
			kfree(alt2_runs);
			kfree(stable_runs);
			kfree(direct_runs);
			return -ENOMEM;
		}

		for (i = 0; i < rand_targets_count; i++) {
			unsigned int targets = rand_targets_list[i];
			unsigned int tmask = targets - 1;
			u32 state = effective_seed ^ (targets * 0x9e3779b9u);
			unsigned int j;

			if (!state)
				state = 1;

			for (j = 0; j < rand_pat_len; j++) {
				u32 v = xorshift32(&state);
				unsigned int idx = v & tmask;

				random_patterns[i * rand_pat_len + j] = stub_fns[idx];
			}
		}

		random_runs = kmalloc_array((size_t)repeats * rand_targets_count,
					    sizeof(*random_runs), GFP_KERNEL);
		if (!random_runs) {
			kfree(random_patterns);
			kfree(alt2_runs);
			kfree(stable_runs);
			kfree(direct_runs);
			return -ENOMEM;
		}

		for (i = 0; i < rand_targets_count && len < sizeof(random_targets_str); i++) {
			len += scnprintf(random_targets_str + len,
					 sizeof(random_targets_str) - len,
					 "%s%u", i ? "," : "", rand_targets_list[i]);
		}
	}

	args.iterations = iterations;
	args.repeats = repeats;
	args.batch_iters = batch_iters;
	args.warmup_runs = warmup_runs;
	args.warmup_iters = warmup_iters;
	args.direct_runs = direct_runs;
	args.stable_runs = stable_runs;
	args.alt2_runs = alt2_runs;
	args.random_runs = random_runs;
	args.random_mode = RANDOM_MODE_FN_PATTERN;
	args.random_count = rand_targets_count;
	for (i = 0; i < rand_targets_count; i++)
		args.random_targets[i] = rand_targets_list[i];
	args.random_pattern_mask = rand_pat_mask;
	args.random_patterns = random_patterns;

	if (!cpu_online(cpu)) {
		pr_err("test_lkm_latency: cpu=%u is not online\n", cpu);
		kfree(random_runs);
		kfree(random_patterns);
		kfree(alt2_runs);
		kfree(stable_runs);
		kfree(direct_runs);
		return -EINVAL;
	}

	pr_info("test_lkm_latency: cpu=%u iterations=%u repeats=%u batch=%u warmup_runs=%u warmup_iters=%u alt2=%u random=%u random_sweep=%u rand_targets=%s pattern_len=%u seed=%u\n",
		cpu, iterations, repeats, batch_iters, warmup_runs, warmup_iters,
		enable_alt2 ? 1 : 0,
		rand_targets_count ? 1 : 0,
		random_sweep ? 1 : 0,
		random_targets_str,
		rand_pat_len,
		effective_seed);

	ret = smp_call_function_single(cpu, run_bench_on_cpu, &args, 1);
	if (ret) {
		pr_err("test_lkm_latency: smp_call_function_single failed: %d\n",
		       ret);
		kfree(random_runs);
		kfree(random_patterns);
		kfree(alt2_runs);
		kfree(stable_runs);
		kfree(direct_runs);
		return ret;
	}

	for (r = 0; r < repeats; r++) {
		unsigned int k;
		u64 direct_cycles = direct_runs[r];
		u64 stable_cycles = stable_runs[r];
		u64 alt2_cycles = alt2_runs ? alt2_runs[r] : 0;
		u64 direct_per_1000 = div_u64(direct_cycles * 1000, iterations);
		u64 stable_per_1000 = div_u64(stable_cycles * 1000, iterations);
		u64 alt2_per_1000 = alt2_runs ? div_u64(alt2_cycles * 1000, iterations) : 0;
		char line[512];
		int len;

		direct_total += direct_cycles;
		stable_total += stable_cycles;
		if (alt2_runs)
			alt2_total += alt2_cycles;
		if (random_runs) {
			for (k = 0; k < rand_targets_count; k++)
				random_total[k] += random_runs[r * rand_targets_count + k];
		}

		len = scnprintf(line, sizeof(line),
				"run=%u direct=%llu.%03llu stable=%llu.%03llu",
				r + 1,
				direct_per_1000 / 1000, direct_per_1000 % 1000,
				stable_per_1000 / 1000, stable_per_1000 % 1000);
		if (alt2_runs) {
			len += scnprintf(line + len, sizeof(line) - len,
					 " alt2=%llu.%03llu",
					 alt2_per_1000 / 1000, alt2_per_1000 % 1000);
		}
		if (random_runs) {
			for (k = 0; k < rand_targets_count; k++) {
				u64 random_cycles = random_runs[r * rand_targets_count + k];
				u64 random_per_1000 =
					div_u64(random_cycles * 1000, iterations);

				len += scnprintf(line + len, sizeof(line) - len,
						 " random%u=%llu.%03llu",
						 rand_targets_list[k],
						 random_per_1000 / 1000,
						 random_per_1000 % 1000);
			}
		}
		pr_info("test_lkm_latency: %s cycles/call\n", line);
	}

	total_iters = (u64)iterations * repeats;
	direct_per_1e6 = div_u64(direct_total * 1000000, total_iters);
	stable_per_1e6 = div_u64(stable_total * 1000000, total_iters);
	pr_info("test_lkm_latency: avg direct=%llu.%06llu cycles/call\n",
		direct_per_1e6 / 1000000, direct_per_1e6 % 1000000);
	print_avg_overhead("stable", direct_per_1e6, stable_per_1e6);

	if (alt2_runs) {
		alt2_per_1e6 = div_u64(alt2_total * 1000000, total_iters);
		print_avg_overhead("alt2", direct_per_1e6, alt2_per_1e6);
	}

	if (random_runs) {
		unsigned int k;

		for (k = 0; k < rand_targets_count; k++) {
			char label[32];
			u64 random_per_1e6 = div_u64(random_total[k] * 1000000,
						     total_iters);

			scnprintf(label, sizeof(label), "random%u",
				  rand_targets_list[k]);
			print_avg_overhead(label, direct_per_1e6, random_per_1e6);
		}
	}

	kfree(random_runs);
	kfree(random_patterns);
	kfree(alt2_runs);
	kfree(stable_runs);
	kfree(direct_runs);

	return 0;
}

static void __exit test_lkm_latency_exit(void)
{
	pr_info("test_lkm_latency: exit\n");
}

module_init(test_lkm_latency_init);
module_exit(test_lkm_latency_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Micro-benchmark for indirect call overhead vs predictability using RDTSC");
