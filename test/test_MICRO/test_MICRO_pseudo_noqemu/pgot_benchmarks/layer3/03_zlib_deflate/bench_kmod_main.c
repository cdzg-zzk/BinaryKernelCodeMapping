#include <linux/cpumask.h>
#include <linux/init.h>
#include <linux/irqflags.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/preempt.h>
#include <linux/sched.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/types.h>
#include <linux/vmalloc.h>
#include <linux/zlib.h>

#define SCALE 1000ULL
#define ZLIB_OUT_LEN 1024
#define ZLIB_LEVEL 3

#ifndef noipa
#define noipa __attribute__((noipa))
#endif

#ifdef BENCH_NOTRACE
#define BENCH_NOTRACE_ATTR __attribute__((no_instrument_function))
#else
#define BENCH_NOTRACE_ATTR
#endif

/*
 * Align benchmark bodies by default to reduce accidental origin/variant layout
 * differences. BENCH_ALIGN64 is accepted for compatibility with older run.sh.
 * Define BENCH_NO_ALIGN64 to disable.
 */
#if defined(BENCH_ALIGN64) || !defined(BENCH_NO_ALIGN64)
#define BENCH_ALIGN_ATTR __attribute__((aligned(64)))
#else
#define BENCH_ALIGN_ATTR
#endif

typedef u64 (*body_fn_t)(u64 iters);

int pgot_zlib_deflateInit_origin(z_streamp strm, int level);
int pgot_zlib_deflateReset_origin(z_streamp strm);
int pgot_zlib_deflate_origin(z_streamp strm, int flush);
int pgot_zlib_deflateEnd_origin(z_streamp strm);
int pgot_zlib_deflate_workspacesize_origin(int windowBits, int memLevel);

int pgot_zlib_deflateInit_data_pgot(z_streamp strm, int level);
int pgot_zlib_deflateReset_data_pgot(z_streamp strm);
int pgot_zlib_deflate_data_pgot(z_streamp strm, int flush);
int pgot_zlib_deflateEnd_data_pgot(z_streamp strm);
int pgot_zlib_deflate_workspacesize_data_pgot(int windowBits, int memLevel);

int pgot_zlib_deflateInit_func_pgot(z_streamp strm, int level);
int pgot_zlib_deflateReset_func_pgot(z_streamp strm);
int pgot_zlib_deflate_func_pgot(z_streamp strm, int flush);
int pgot_zlib_deflateEnd_func_pgot(z_streamp strm);
int pgot_zlib_deflate_workspacesize_func_pgot(int windowBits, int memLevel);

int pgot_zlib_deflateInit_all_pgot(z_streamp strm, int level);
int pgot_zlib_deflateReset_all_pgot(z_streamp strm);
int pgot_zlib_deflate_all_pgot(z_streamp strm, int flush);
int pgot_zlib_deflateEnd_all_pgot(z_streamp strm);
int pgot_zlib_deflate_workspacesize_all_pgot(int windowBits, int memLevel);

struct zlib_variant_ops {
	const char *name;
	int (*init)(z_streamp strm, int level);
	int (*reset)(z_streamp strm);
	int (*deflate)(z_streamp strm, int flush);
	int (*end)(z_streamp strm);
	int (*workspacesize)(int windowBits, int memLevel);
};

struct zlib_case_state {
	z_stream stream;
	void *workspace;
	u8 output[ZLIB_OUT_LEN] __aligned(64);
	const struct zlib_variant_ops *ops;
};

static unsigned long iterations = 1000;
static unsigned long warmup = 1000;
static int repeats = 31;
static int run_id;
static int cpu = -1;
static bool irq_off;
static char *build = "unknown";
static char *variants = "all_pgot";

module_param(iterations, ulong, 0444);
MODULE_PARM_DESC(iterations, "zlib deflate operations per timed sample");
module_param(warmup, ulong, 0444);
MODULE_PARM_DESC(warmup, "warmup deflate operations before raw sampling");
module_param(repeats, int, 0444);
MODULE_PARM_DESC(repeats, "paired origin/variant repetitions");
module_param(run_id, int, 0444);
MODULE_PARM_DESC(run_id, "raw sample run id");
module_param(cpu, int, 0444);
MODULE_PARM_DESC(cpu, "optional CPU affinity for module init thread");
module_param(irq_off, bool, 0444);
MODULE_PARM_DESC(irq_off, "disable local IRQs during each timed sample; use only for short samples");
module_param(build, charp, 0444);
MODULE_PARM_DESC(build, "build label: no_retpoline or retpoline");
module_param(variants, charp, 0444);
MODULE_PARM_DESC(variants, "comma-separated variants to run: data_pgot,func_pgot,all_pgot or all");

static const struct zlib_variant_ops origin_ops = {
	.name = "origin",
	.init = pgot_zlib_deflateInit_origin,
	.reset = pgot_zlib_deflateReset_origin,
	.deflate = pgot_zlib_deflate_origin,
	.end = pgot_zlib_deflateEnd_origin,
	.workspacesize = pgot_zlib_deflate_workspacesize_origin,
};

static const struct zlib_variant_ops data_ops = {
	.name = "data_pgot",
	.init = pgot_zlib_deflateInit_data_pgot,
	.reset = pgot_zlib_deflateReset_data_pgot,
	.deflate = pgot_zlib_deflate_data_pgot,
	.end = pgot_zlib_deflateEnd_data_pgot,
	.workspacesize = pgot_zlib_deflate_workspacesize_data_pgot,
};

static const struct zlib_variant_ops func_ops = {
	.name = "func_pgot",
	.init = pgot_zlib_deflateInit_func_pgot,
	.reset = pgot_zlib_deflateReset_func_pgot,
	.deflate = pgot_zlib_deflate_func_pgot,
	.end = pgot_zlib_deflateEnd_func_pgot,
	.workspacesize = pgot_zlib_deflate_workspacesize_func_pgot,
};

static const struct zlib_variant_ops all_ops = {
	.name = "all_pgot",
	.init = pgot_zlib_deflateInit_all_pgot,
	.reset = pgot_zlib_deflateReset_all_pgot,
	.deflate = pgot_zlib_deflate_all_pgot,
	.end = pgot_zlib_deflateEnd_all_pgot,
	.workspacesize = pgot_zlib_deflate_workspacesize_all_pgot,
};

static struct zlib_case_state origin_state = { .ops = &origin_ops };
static struct zlib_case_state data_state = { .ops = &data_ops };
static struct zlib_case_state func_state = { .ops = &func_ops };
static struct zlib_case_state all_state = { .ops = &all_ops };
static volatile u64 sink_u64;

static const u8 bench_input[] __aligned(64) =
	"This document describes a compression method based on the DEFLATE "
	"compression algorithm. This document defines the application of the "
	"DEFLATE algorithm to the IP Payload Compression Protocol. The input is "
	"kept intentionally small so each benchmark iteration executes the full "
	"deflate closure and exposes table accesses inside the copied code.";

static inline void compiler_barrier(void)
{
	asm volatile("" ::: "memory");
}

static inline u64 rdtsc_start(void)
{
	u32 lo, hi, aux;

	asm volatile("lfence\n\t"
		     "rdtscp"
		     : "=a"(lo), "=d"(hi), "=c"(aux)
		     :
		     : "memory");
	return ((u64)hi << 32) | lo;
}

static inline u64 rdtsc_end(void)
{
	u32 lo, hi, aux;

	asm volatile("rdtscp\n\t"
		     "lfence"
		     : "=a"(lo), "=d"(hi), "=c"(aux)
		     :
		     : "memory");
	return ((u64)hi << 32) | lo;
}

static inline void prepare_stream_with_reset(struct zlib_case_state *state,
					     int (*reset)(z_streamp strm))
{
	reset(&state->stream);
	state->stream.next_in = (u8 *)bench_input;
	state->stream.avail_in = sizeof(bench_input) - 1;
	state->stream.next_out = state->output;
	state->stream.avail_out = sizeof(state->output);
	asm volatile("" : "+m"(state->stream), "+m"(state->output) :: "memory");
}

static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64
body_origin(u64 iters)
{
	u64 i, acc = 0;

	for (i = 0; i < iters; i++) {
		int ret;

		prepare_stream_with_reset(&origin_state,
					  pgot_zlib_deflateReset_origin);
		ret = pgot_zlib_deflate_origin(&origin_state.stream, Z_FINISH);
		acc += origin_state.stream.total_out;
		acc += origin_state.output[i % ZLIB_OUT_LEN] + ret;
		asm volatile("" : "+r"(acc), "+m"(origin_state) :: "memory");
	}
	return acc;
}

#define DEFINE_VARIANT_BODY(name, state_name, reset_fn, deflate_fn)	\
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64		\
body_##name(u64 iters)							\
{									\
	u64 i, acc = 0;							\
									\
	for (i = 0; i < iters; i++) {					\
		int ret;						\
									\
		prepare_stream_with_reset(&state_name, reset_fn);	\
		ret = deflate_fn(&state_name.stream, Z_FINISH);		\
		acc += state_name.stream.total_out;			\
		acc += state_name.output[i % ZLIB_OUT_LEN] + ret;	\
		asm volatile("" : "+r"(acc), "+m"(state_name) :: "memory"); \
	}								\
	return acc;							\
}

DEFINE_VARIANT_BODY(data_pgot, data_state,
		    pgot_zlib_deflateReset_data_pgot,
		    pgot_zlib_deflate_data_pgot)
DEFINE_VARIANT_BODY(func_pgot, func_state,
		    pgot_zlib_deflateReset_func_pgot,
		    pgot_zlib_deflate_func_pgot)
DEFINE_VARIANT_BODY(all_pgot, all_state,
		    pgot_zlib_deflateReset_all_pgot,
		    pgot_zlib_deflate_all_pgot)

static body_fn_t select_body(const char *variant)
{
	if (!strcmp(variant, "origin"))
		return body_origin;
	if (!strcmp(variant, "data_pgot"))
		return body_data_pgot;
	if (!strcmp(variant, "func_pgot"))
		return body_func_pgot;
	if (!strcmp(variant, "all_pgot"))
		return body_all_pgot;
	return NULL;
}

static s64 measure_x1000(body_fn_t fn, u64 iters)
{
	u64 start, end, v;
	unsigned long flags = 0;

	preempt_disable();
	if (irq_off)
		local_irq_save(flags);

	start = rdtsc_start();
	v = fn(iters);
	end = rdtsc_end();

	if (irq_off)
		local_irq_restore(flags);
	preempt_enable();

	sink_u64 ^= v;
	compiler_barrier();
	return div64_u64((end - start) * SCALE, iters);
}

static void scaled_to_buf(char *buf, size_t size, s64 value)
{
	u64 abs_value;

	if (value < 0) {
		abs_value = (u64)(-value);
		scnprintf(buf, size, "-%llu.%03llu",
			  div64_u64(abs_value, SCALE), abs_value % SCALE);
	} else {
		abs_value = (u64)value;
		scnprintf(buf, size, "%llu.%03llu",
			  div64_u64(abs_value, SCALE), abs_value % SCALE);
	}
}

static void emit_raw(const char *variant, int repeat, s64 origin,
		     s64 variant_cycles)
{
	char origin_buf[32], variant_buf[32], delta_buf[32];

	scaled_to_buf(origin_buf, sizeof(origin_buf), origin);
	scaled_to_buf(variant_buf, sizeof(variant_buf), variant_cycles);
	scaled_to_buf(delta_buf, sizeof(delta_buf), variant_cycles - origin);

	pr_info("PGOT_L3_RAW,layer3_zlib_deflate_kmod,%s,%d,%s,%d,%lu,%s,%s,%s\n",
		build, run_id, variant, repeat, iterations,
		origin_buf, variant_buf, delta_buf);
}

static int validate_one(struct zlib_case_state *variant)
{
	int ret_origin, ret_variant;

	prepare_stream_with_reset(&origin_state, pgot_zlib_deflateReset_origin);
	ret_origin = origin_state.ops->deflate(&origin_state.stream, Z_FINISH);

	prepare_stream_with_reset(variant, variant->ops->reset);
	ret_variant = variant->ops->deflate(&variant->stream, Z_FINISH);

	if (ret_origin != ret_variant ||
	    origin_state.stream.total_out != variant->stream.total_out ||
	    memcmp(origin_state.output, variant->output,
		   origin_state.stream.total_out) != 0) {
		pr_err("PGOT_L3_VALIDATE_FAIL,zlib,%s,origin_ret=%d,variant_ret=%d,origin_out=%lu,variant_out=%lu\n",
		       variant->ops->name, ret_origin, ret_variant,
		       origin_state.stream.total_out, variant->stream.total_out);
		return -EINVAL;
	}
	return 0;
}

static int validate_variants(void)
{
	int ret;

	ret = validate_one(&data_state);
	if (ret)
		return ret;
	ret = validate_one(&func_state);
	if (ret)
		return ret;
	return validate_one(&all_state);
}

static void do_warmup(void)
{
	if (!warmup)
		return;

	sink_u64 ^= body_origin(warmup);
	sink_u64 ^= body_data_pgot(warmup);
	sink_u64 ^= body_func_pgot(warmup);
	sink_u64 ^= body_all_pgot(warmup);
	compiler_barrier();
}

/*
 * Measure all raw samples for one variant first, then print them.
 * This avoids printk/pr_info perturbing the next timed sample.
 */
static int run_case(const char *variant)
{
	body_fn_t origin_body = select_body("origin");
	body_fn_t variant_body = select_body(variant);
	s64 *origin_samples;
	s64 *variant_samples;
	int r;

	if (!origin_body || !variant_body)
		return -EINVAL;

	origin_samples = kcalloc(repeats, sizeof(*origin_samples), GFP_KERNEL);
	if (!origin_samples)
		return -ENOMEM;

	variant_samples = kcalloc(repeats, sizeof(*variant_samples), GFP_KERNEL);
	if (!variant_samples) {
		kfree(origin_samples);
		return -ENOMEM;
	}

	for (r = 0; r < repeats; r++) {
		s64 origin0, origin1, variant0, variant1;

		if (r & 1) {
			/* BAAB order */
			variant0 = measure_x1000(variant_body, iterations);
			origin0 = measure_x1000(origin_body, iterations);
			origin1 = measure_x1000(origin_body, iterations);
			variant1 = measure_x1000(variant_body, iterations);
		} else {
			/* ABBA order */
			origin0 = measure_x1000(origin_body, iterations);
			variant0 = measure_x1000(variant_body, iterations);
			variant1 = measure_x1000(variant_body, iterations);
			origin1 = measure_x1000(origin_body, iterations);
		}

		origin_samples[r] = div_s64(origin0 + origin1, 2);
		variant_samples[r] = div_s64(variant0 + variant1, 2);
	}

	for (r = 0; r < repeats; r++)
		emit_raw(variant, r, origin_samples[r], variant_samples[r]);

	kfree(variant_samples);
	kfree(origin_samples);
	return 0;
}

static bool variant_enabled(const char *name)
{
	const char *p = variants;
	size_t n = strlen(name);

	if (!variants || !strcmp(variants, "all"))
		return true;

	while (*p) {
		while (*p == ',' || *p == ' ')
			p++;
		if (!strncmp(p, name, n) &&
		    (p[n] == '\0' || p[n] == ',' || p[n] == ' '))
			return true;
		while (*p && *p != ',')
			p++;
	}
	return false;
}

static int run_all_cases(void)
{
	static const char *all_variants[] = {"data_pgot", "func_pgot", "all_pgot"};
	int v, ret;

	do_warmup();

	for (v = 0; v < ARRAY_SIZE(all_variants); v++) {
		if (!variant_enabled(all_variants[v]))
			continue;
		ret = run_case(all_variants[v]);
		if (ret)
			return ret;
	}
	return 0;
}

static int pin_current_thread(void)
{
	if (cpu < 0)
		return 0;
	if (cpu >= nr_cpu_ids || !cpu_online(cpu))
		return -EINVAL;
	return set_cpus_allowed_ptr(current, cpumask_of(cpu));
}

static int init_state(struct zlib_case_state *state)
{
	size_t workspace_size;
	int ret;

	workspace_size = state->ops->workspacesize(MAX_WBITS, MAX_MEM_LEVEL);
	state->workspace = vzalloc(workspace_size);
	if (!state->workspace)
		return -ENOMEM;

	memset(&state->stream, 0, sizeof(state->stream));
	state->stream.workspace = state->workspace;

	ret = state->ops->init(&state->stream, ZLIB_LEVEL);
	if (ret != Z_OK) {
		vfree(state->workspace);
		state->workspace = NULL;
		return -EINVAL;
	}
	return 0;
}

static void free_state(struct zlib_case_state *state)
{
	if (state->workspace) {
		state->ops->end(&state->stream);
		vfree(state->workspace);
		state->workspace = NULL;
	}
}

static void cleanup_bench_state(void)
{
	free_state(&all_state);
	free_state(&func_state);
	free_state(&data_state);
	free_state(&origin_state);
}

static int init_bench_state(void)
{
	int ret;

	ret = init_state(&origin_state);
	if (ret)
		goto out_cleanup;
	ret = init_state(&data_state);
	if (ret)
		goto out_cleanup;
	ret = init_state(&func_state);
	if (ret)
		goto out_cleanup;
	ret = init_state(&all_state);
	if (ret)
		goto out_cleanup;

	ret = validate_variants();
	if (ret)
		goto out_cleanup;

	return 0;

out_cleanup:
	cleanup_bench_state();
	return ret;
}

static int __init bench_init(void)
{
	int ret;

	if (!iterations || repeats <= 0)
		return -EINVAL;

	ret = pin_current_thread();
	if (ret)
		return ret;

	ret = init_bench_state();
	if (ret)
		return ret;

	pr_info("PGOT_L3_START,experiment=layer3_zlib_deflate_kmod,build=%s,iterations=%lu,warmup=%lu,repeats=%d,run_id=%d,cpu=%d,irq_off=%d,variants=%s\n",
		build, iterations, warmup, repeats, run_id, cpu, irq_off,
		variants);

	ret = run_all_cases();

	pr_info("PGOT_L3_DONE,experiment=layer3_zlib_deflate_kmod,ret=%d,sink=%llu\n",
		ret, (unsigned long long)sink_u64);

	if (ret) {
		cleanup_bench_state();
		return ret;
	}
	return 0;
}

static void __exit bench_exit(void)
{
	cleanup_bench_state();
	pr_info("PGOT_L3_EXIT,experiment=layer3_zlib_deflate_kmod\n");
}

module_init(bench_init);
module_exit(bench_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("PGOT layer3 copied zlib deflate closure benchmark");
