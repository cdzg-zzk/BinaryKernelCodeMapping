// SPDX-License-Identifier: GPL-2.0

#include <linux/compiler.h>
#include <linux/cpu.h>
#include <linux/crc32.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/minmax.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/preempt.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/sort.h>
#include <linux/string.h>
#include <linux/uaccess.h>

#include "micro.h"
#include "micro_pseudo.h"

#define PROC_DIR_NAME "micro_pseudo"
#define PROC_RUN_NAME "run"
#define PROC_RESULT_NAME "last_result"
#define MAX_CMD_LEN 256

static u8 input_buf[MICRO_PSEUDO_INPUT_BYTES] __aligned(64);
static u32 bench_sink;

static struct proc_dir_entry *proc_dir;
static struct proc_dir_entry *proc_run;
static struct proc_dir_entry *proc_result;
static DEFINE_MUTEX(run_lock);

static struct micro_run_result last_result = {
	.valid = false,
	.status = 0,
	.message = "no run yet",
};

static const char *const variant_names[MICRO_VARIANT_COUNT] = {
	[MICRO_VARIANT_KERNEL_NATIVE] = "kernel_native",
	[MICRO_VARIANT_KERNEL_MICRO] = "kernel_micro",
};

static __always_inline u64 rdtsc_begin(void)
{
	u32 lo, hi;

	asm volatile("lfence\n\trdtsc" : "=a"(lo), "=d"(hi) :: "memory");
	return ((u64)hi << 32) | lo;
}

static __always_inline u64 rdtsc_end(void)
{
	u32 lo, hi;

	asm volatile("rdtsc\n\tlfence" : "=a"(lo), "=d"(hi) :: "memory");
	return ((u64)hi << 32) | lo;
}

static int cmp_u64(const void *lhs, const void *rhs)
{
	const u64 *a = lhs;
	const u64 *b = rhs;

	if (*a < *b)
		return -1;
	if (*a > *b)
		return 1;
	return 0;
}

static const char *variant_name(enum micro_pseudo_variant_id variant_id)
{
	if (variant_id >= MICRO_VARIANT_COUNT)
		return "unknown";
	return variant_names[variant_id];
}

static u32 prng_step(u32 *state)
{
	*state = *state * 1664525U + 1013904223U;
	return *state;
}

static void init_input_data(void)
{
	u32 state = 0x12345678U;
	u32 i;

	for (i = 0; i < MICRO_PSEUDO_INPUT_BYTES; i++)
		input_buf[i] = (u8)(prng_step(&state) >> 24);
}

static noinline u32 run_native_crc32(u32 iters, u32 seed, u32 input_len)
{
	u32 state = seed;
	u32 i;

	for (i = 0; i < iters; i++)
		state = crc32_le(state, input_buf, input_len);

	return state;
}

static noinline u32 run_micro_crc32(u32 iters, u32 seed, u32 input_len)
{
	u32 state = seed;
	u32 i;

	for (i = 0; i < iters; i++)
		state = crc32_le_micro(state, input_buf, input_len);

	return state;
}

static u32 run_variant(enum micro_pseudo_variant_id variant_id, u32 iters,
		       u32 seed, u32 input_len)
{
	switch (variant_id) {
	case MICRO_VARIANT_KERNEL_MICRO:
		return run_micro_crc32(iters, seed, input_len);
	case MICRO_VARIANT_KERNEL_NATIVE:
	default:
		return run_native_crc32(iters, seed, input_len);
	}
}

static void run_warmup(const struct micro_run_params *params)
{
	u32 i;
	u32 state = params->seed;

	for (i = 0; i < params->warmup; i++)
		state = run_variant(params->variant_id,
				    min(params->batch_iters, params->iters),
				    state + i, params->input_len);

	WRITE_ONCE(bench_sink, state);
}

static u64 run_timed_once(const struct micro_run_params *params, u32 *checksum)
{
	u32 remaining = params->iters;
	u32 state = params->seed;
	u64 total_cycles = 0;

	while (remaining) {
		u32 n = min(remaining, params->batch_iters);
		unsigned long flags;
		u64 start, end;

		preempt_disable();
		local_irq_save(flags);
		start = rdtsc_begin();
		state = run_variant(params->variant_id, n, state,
				    params->input_len);
		end = rdtsc_end();
		local_irq_restore(flags);
		preempt_enable();

		total_cycles += end - start;
		remaining -= n;
	}

	*checksum = state;
	WRITE_ONCE(bench_sink, state);
	return total_cycles;
}

static void do_run_benchmark(void *info)
{
	struct micro_run_result *result = info;
	struct micro_run_params params;
	u64 sorted[MICRO_PSEUDO_MAX_REPEATS];
	u32 i;

	params.variant_id = result->variant_id;
	params.iters = result->iters;
	params.warmup = result->warmup;
	params.repeat = result->repeat;
	params.seed = result->seed;
	params.batch_iters = result->batch_iters;
	params.input_len = result->input_len;
	params.cpu = result->requested_cpu;

	result->actual_cpu = raw_smp_processor_id();
	run_warmup(&params);

	for (i = 0; i < params.repeat; i++) {
		u32 checksum;

		result->samples[i] = run_timed_once(&params, &checksum);
		result->checksum = checksum;
		sorted[i] = result->samples[i];
	}

	sort(sorted, params.repeat, sizeof(sorted[0]), cmp_u64, NULL);
	result->best_cycles = sorted[0];
	result->median_cycles = sorted[params.repeat / 2];
	result->worst_cycles = sorted[params.repeat - 1];
	result->total_bytes = (u64)params.iters * params.input_len;
	result->cycles_per_call_x1000 =
		div64_u64(result->median_cycles * 1000ULL, params.iters);
	result->cycles_per_byte_x1000 =
		div64_u64(result->median_cycles * 1000ULL, result->total_bytes);
	result->status = 0;
	result->valid = true;
	strscpy(result->message, "ok", sizeof(result->message));
}

static int parse_variant_id(const char *value,
			    enum micro_pseudo_variant_id *variant_id)
{
	if (!strcmp(value, "kernel_native") || !strcmp(value, "native")) {
		*variant_id = MICRO_VARIANT_KERNEL_NATIVE;
		return 0;
	}

	if (!strcmp(value, "kernel_micro") || !strcmp(value, "micro")) {
		*variant_id = MICRO_VARIANT_KERNEL_MICRO;
		return 0;
	}

	return -EINVAL;
}

static void init_default_params(struct micro_run_params *params)
{
	params->variant_id = MICRO_VARIANT_KERNEL_NATIVE;
	params->iters = 200000U;
	params->warmup = 3U;
	params->repeat = 9U;
	params->seed = 0x1234U;
	params->batch_iters = 8192U;
	params->input_len = MICRO_PSEUDO_DEFAULT_INPUT_LEN;
	params->cpu = -1;
}

static int parse_run_command(char *buf, struct micro_run_params *params)
{
	char *cursor = buf;
	char *token;
	int ret;

	init_default_params(params);

	while ((token = strsep(&cursor, " \t\r\n")) != NULL) {
		char *key = token;
		char *value = strchr(token, '=');

		if (!*token)
			continue;
		if (!value)
			return -EINVAL;

		*value++ = '\0';

		if (!strcmp(key, "variant")) {
			ret = parse_variant_id(value, &params->variant_id);
			if (ret)
				return ret;
			continue;
		}

		if (!strcmp(key, "iters")) {
			ret = kstrtou32(value, 0, &params->iters);
			if (ret)
				return ret;
			continue;
		}

		if (!strcmp(key, "warmup")) {
			ret = kstrtou32(value, 0, &params->warmup);
			if (ret)
				return ret;
			continue;
		}

		if (!strcmp(key, "repeat")) {
			ret = kstrtou32(value, 0, &params->repeat);
			if (ret)
				return ret;
			continue;
		}

		if (!strcmp(key, "seed")) {
			ret = kstrtou32(value, 0, &params->seed);
			if (ret)
				return ret;
			continue;
		}

		if (!strcmp(key, "batch_iters")) {
			ret = kstrtou32(value, 0, &params->batch_iters);
			if (ret)
				return ret;
			continue;
		}

		if (!strcmp(key, "input_len")) {
			ret = kstrtou32(value, 0, &params->input_len);
			if (ret)
				return ret;
			continue;
		}

		if (!strcmp(key, "cpu")) {
			ret = kstrtoint(value, 0, &params->cpu);
			if (ret)
				return ret;
			continue;
		}

		return -EINVAL;
	}

	if (!params->iters || !params->batch_iters || !params->input_len)
		return -EINVAL;
	if (params->input_len > MICRO_PSEUDO_INPUT_BYTES)
		return -EINVAL;

	params->warmup = min(params->warmup, MICRO_PSEUDO_MAX_WARMUP);
	params->repeat = clamp_t(u32, params->repeat, 1, MICRO_PSEUDO_MAX_REPEATS);

	return 0;
}

static void store_error_result(const struct micro_run_params *params, int status,
			       const char *message)
{
	memset(&last_result, 0, sizeof(last_result));
	last_result.valid = false;
	last_result.status = status;
	last_result.variant_id = params->variant_id;
	last_result.iters = params->iters;
	last_result.warmup = params->warmup;
	last_result.repeat = params->repeat;
	last_result.seed = params->seed;
	last_result.batch_iters = params->batch_iters;
	last_result.input_len = params->input_len;
	last_result.requested_cpu = params->cpu;
	strscpy(last_result.message, message, sizeof(last_result.message));
}

static int execute_run(const struct micro_run_params *params)
{
	struct micro_run_result result;
	int cpu = params->cpu;

	memset(&result, 0, sizeof(result));
	result.variant_id = params->variant_id;
	result.iters = params->iters;
	result.warmup = params->warmup;
	result.repeat = params->repeat;
	result.seed = params->seed;
	result.batch_iters = params->batch_iters;
	result.input_len = params->input_len;
	result.requested_cpu = cpu;

	if (cpu >= 0) {
		if (!cpu_possible(cpu) || !cpu_online(cpu)) {
			store_error_result(params, -EINVAL,
					   "requested cpu is offline");
			return -EINVAL;
		}

		if (raw_smp_processor_id() != cpu) {
			store_error_result(params, -EINVAL,
					   "caller is not running on requested cpu");
			return -EINVAL;
		}
	}

	do_run_benchmark(&result);
	last_result = result;
	return 0;
}

static int result_show(struct seq_file *m, void *v)
{
	u32 i;

	mutex_lock(&run_lock);
	seq_printf(m, "valid=%u\n", last_result.valid ? 1 : 0);
	seq_printf(m, "status=%d\n", last_result.status);
	seq_printf(m, "message=%s\n", last_result.message);
	seq_printf(m, "benchmark=crc32_le\n");
	seq_printf(m, "variant=%s\n", variant_name(last_result.variant_id));
	seq_printf(m, "requested_cpu=%d\n", last_result.requested_cpu);
	seq_printf(m, "actual_cpu=%u\n", last_result.actual_cpu);
	seq_printf(m, "iters=%u\n", last_result.iters);
	seq_printf(m, "warmup=%u\n", last_result.warmup);
	seq_printf(m, "repeat=%u\n", last_result.repeat);
	seq_printf(m, "batch_iters=%u\n", last_result.batch_iters);
	seq_printf(m, "input_len=%u\n", last_result.input_len);
	seq_printf(m, "seed=0x%08x\n", last_result.seed);
	seq_printf(m, "checksum=0x%08x\n", last_result.checksum);
	seq_printf(m, "total_bytes=%llu\n", last_result.total_bytes);
	seq_printf(m, "best_cycles=%llu\n", last_result.best_cycles);
	seq_printf(m, "median_cycles=%llu\n", last_result.median_cycles);
	seq_printf(m, "worst_cycles=%llu\n", last_result.worst_cycles);
	seq_printf(m, "cycles_per_call_x1000=%llu\n",
		   last_result.cycles_per_call_x1000);
	seq_printf(m, "cycles_per_byte_x1000=%llu\n",
		   last_result.cycles_per_byte_x1000);
	for (i = 0; i < last_result.repeat; i++)
		seq_printf(m, "sample_%u=%llu\n", i, last_result.samples[i]);
	mutex_unlock(&run_lock);

	return 0;
}

static int result_open(struct inode *inode, struct file *file)
{
	return single_open(file, result_show, NULL);
}

static ssize_t run_write(struct file *file, const char __user *ubuf,
			 size_t len, loff_t *ppos)
{
	char buf[MAX_CMD_LEN];
	struct micro_run_params params;
	ssize_t ret = len;
	int err;

	if (*ppos != 0)
		return -EINVAL;
	if (len == 0 || len >= sizeof(buf))
		return -EINVAL;

	if (copy_from_user(buf, ubuf, len))
		return -EFAULT;
	buf[len] = '\0';

	err = parse_run_command(buf, &params);
	if (err)
		return err;

	mutex_lock(&run_lock);
	err = execute_run(&params);
	mutex_unlock(&run_lock);
	if (err)
		return err;

	*ppos += len;
	return ret;
}

static const struct proc_ops run_ops = {
	.proc_write = run_write,
};

static const struct proc_ops result_ops = {
	.proc_open = result_open,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};

static int __init micro_pseudo_init(void)
{
	init_input_data();

	proc_dir = proc_mkdir(PROC_DIR_NAME, NULL);
	if (!proc_dir)
		return -ENOMEM;

	proc_run = proc_create(PROC_RUN_NAME, 0220, proc_dir, &run_ops);
	if (!proc_run)
		goto err_remove_dir;

	proc_result = proc_create(PROC_RESULT_NAME, 0444, proc_dir, &result_ops);
	if (!proc_result)
		goto err_remove_run;

	pr_info("micro_pseudo: loaded, benchmark=crc32_le, use /proc/%s/%s\n",
		PROC_DIR_NAME, PROC_RUN_NAME);
	return 0;

err_remove_run:
	proc_remove(proc_run);
err_remove_dir:
	proc_remove(proc_dir);
	return -ENOMEM;
}

static void __exit micro_pseudo_exit(void)
{
	proc_remove(proc_result);
	proc_remove(proc_run);
	proc_remove(proc_dir);
	pr_info("micro_pseudo: unloaded\n");
}

module_init(micro_pseudo_init);
module_exit(micro_pseudo_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("OpenAI Codex");
MODULE_DESCRIPTION("crc32_le benchmark harness comparing kernel native and crc32_le_micro");
