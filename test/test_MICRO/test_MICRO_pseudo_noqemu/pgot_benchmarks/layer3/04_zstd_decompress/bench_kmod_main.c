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
#include <linux/zstd.h>

#define SCALE 1000ULL
#define ZSTD_OUT_LEN 512

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

size_t pgot_ZSTD_DCtxWorkspaceBound_origin(void);
ZSTD_DCtx *pgot_ZSTD_initDCtx_origin(void *workspace, size_t workspaceSize);
size_t pgot_ZSTD_decompressBegin_origin(ZSTD_DCtx *dctx);
size_t pgot_ZSTD_decompressDCtx_origin(ZSTD_DCtx *dctx, void *dst,
				       size_t dstCapacity, const void *src,
				       size_t srcSize);

size_t pgot_ZSTD_DCtxWorkspaceBound_data_pgot(void);
ZSTD_DCtx *pgot_ZSTD_initDCtx_data_pgot(void *workspace, size_t workspaceSize);
size_t pgot_ZSTD_decompressBegin_data_pgot(ZSTD_DCtx *dctx);
size_t pgot_ZSTD_decompressDCtx_data_pgot(ZSTD_DCtx *dctx, void *dst,
					  size_t dstCapacity, const void *src,
					  size_t srcSize);

size_t pgot_ZSTD_DCtxWorkspaceBound_func_pgot(void);
ZSTD_DCtx *pgot_ZSTD_initDCtx_func_pgot(void *workspace, size_t workspaceSize);
size_t pgot_ZSTD_decompressBegin_func_pgot(ZSTD_DCtx *dctx);
size_t pgot_ZSTD_decompressDCtx_func_pgot(ZSTD_DCtx *dctx, void *dst,
					  size_t dstCapacity, const void *src,
					  size_t srcSize);

size_t pgot_ZSTD_DCtxWorkspaceBound_all_pgot(void);
ZSTD_DCtx *pgot_ZSTD_initDCtx_all_pgot(void *workspace, size_t workspaceSize);
size_t pgot_ZSTD_decompressBegin_all_pgot(ZSTD_DCtx *dctx);
size_t pgot_ZSTD_decompressDCtx_all_pgot(ZSTD_DCtx *dctx, void *dst,
					 size_t dstCapacity, const void *src,
					 size_t srcSize);

struct zstd_case_state {
	const char *name;
	size_t (*workspace_bound)(void);
	ZSTD_DCtx *(*init)(void *workspace, size_t workspaceSize);
	size_t (*begin)(ZSTD_DCtx *dctx);
	size_t (*decompress)(ZSTD_DCtx *dctx, void *dst, size_t dstCapacity,
			     const void *src, size_t srcSize);
	ZSTD_DCtx *dctx;
	void *workspace;
	u8 output[ZSTD_OUT_LEN] __aligned(64);
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
MODULE_PARM_DESC(iterations, "ZSTD decompressions per timed sample");
module_param(warmup, ulong, 0444);
MODULE_PARM_DESC(warmup, "warmup decompressions before raw sampling");
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

static struct zstd_case_state origin_state = {
	.name = "origin",
	.workspace_bound = pgot_ZSTD_DCtxWorkspaceBound_origin,
	.init = pgot_ZSTD_initDCtx_origin,
	.begin = pgot_ZSTD_decompressBegin_origin,
	.decompress = pgot_ZSTD_decompressDCtx_origin,
};

static struct zstd_case_state data_state = {
	.name = "data_pgot",
	.workspace_bound = pgot_ZSTD_DCtxWorkspaceBound_data_pgot,
	.init = pgot_ZSTD_initDCtx_data_pgot,
	.begin = pgot_ZSTD_decompressBegin_data_pgot,
	.decompress = pgot_ZSTD_decompressDCtx_data_pgot,
};

static struct zstd_case_state func_state = {
	.name = "func_pgot",
	.workspace_bound = pgot_ZSTD_DCtxWorkspaceBound_func_pgot,
	.init = pgot_ZSTD_initDCtx_func_pgot,
	.begin = pgot_ZSTD_decompressBegin_func_pgot,
	.decompress = pgot_ZSTD_decompressDCtx_func_pgot,
};

static struct zstd_case_state all_state = {
	.name = "all_pgot",
	.workspace_bound = pgot_ZSTD_DCtxWorkspaceBound_all_pgot,
	.init = pgot_ZSTD_initDCtx_all_pgot,
	.begin = pgot_ZSTD_decompressBegin_all_pgot,
	.decompress = pgot_ZSTD_decompressDCtx_all_pgot,
};

static volatile u64 sink_u64;

static const u8 bench_input[] __aligned(64) = {
	0x28, 0xb5, 0x2f, 0xfd, 0x04, 0x50, 0x75, 0x04,
	0x00, 0x42, 0x4b, 0x1e, 0x17, 0x90, 0x81, 0x31,
	0x00, 0xf2, 0x2f, 0xe4, 0x36, 0xc9, 0xef, 0x92,
	0x88, 0x32, 0xc9, 0xf2, 0x24, 0x94, 0xd8, 0x68,
	0x9a, 0x0f, 0x00, 0x0c, 0xc4, 0x31, 0x6f, 0x0d,
	0x0c, 0x38, 0xac, 0x5c, 0x48, 0x03, 0xcd, 0x63,
	0x67, 0xc0, 0xf3, 0xad, 0x4e, 0x90, 0xaa, 0x78,
	0xa0, 0xa4, 0xc5, 0x99, 0xda, 0x2f, 0xb6, 0x24,
	0x60, 0xe2, 0x79, 0x4b, 0xaa, 0xb6, 0x6b, 0x85,
	0x0b, 0xc9, 0xc6, 0x04, 0x66, 0x86, 0xe2, 0xcc,
	0xe2, 0x25, 0x3f, 0x4f, 0x09, 0xcd, 0xb8, 0x9d,
	0xdb, 0xc1, 0x90, 0xa9, 0x11, 0xbc, 0x35, 0x44,
	0x69, 0x2d, 0x9c, 0x64, 0x4f, 0x13, 0x31, 0x64,
	0xcc, 0xfb, 0x4d, 0x95, 0x93, 0x86, 0x7f, 0x33,
	0x7f, 0x1a, 0xef, 0xe9, 0x30, 0xf9, 0x67, 0xa1,
	0x94, 0x0a, 0x69, 0x0f, 0x60, 0xcd, 0xc3, 0xab,
	0x99, 0xdc, 0x42, 0xed, 0x97, 0x05, 0x00, 0x33,
	0xc3, 0x15, 0x95, 0x3a, 0x06, 0xa0, 0x0e, 0x20,
	0xa9, 0x0e, 0x82, 0xb9, 0x43, 0x45, 0x01, 0xaa,
	0x6d, 0xda, 0x0d,
};

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

static inline void prepare_context(struct zstd_case_state *state,
				   size_t (*begin)(ZSTD_DCtx *dctx))
{
	begin(state->dctx);
	asm volatile("" : "+m"(state->output) :: "memory");
}

static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64
body_origin(u64 iters)
{
	u64 i, acc = 0;

	for (i = 0; i < iters; i++) {
		size_t ret;

		prepare_context(&origin_state, pgot_ZSTD_decompressBegin_origin);
		ret = pgot_ZSTD_decompressDCtx_origin(origin_state.dctx,
						      origin_state.output,
						      sizeof(origin_state.output),
						      bench_input,
						      sizeof(bench_input));
		acc += ret + origin_state.output[i % ZSTD_OUT_LEN];
		asm volatile("" : "+r"(acc), "+m"(origin_state) :: "memory");
	}
	return acc;
}

#define DEFINE_VARIANT_BODY(name, state_name, begin_fn, decompress_fn)	\
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64		\
body_##name(u64 iters)							\
{									\
	u64 i, acc = 0;							\
									\
	for (i = 0; i < iters; i++) {					\
		size_t ret;						\
									\
		prepare_context(&state_name, begin_fn);			\
		ret = decompress_fn(state_name.dctx, state_name.output,	\
				    sizeof(state_name.output), bench_input,	\
				    sizeof(bench_input));			\
		acc += ret + state_name.output[i % ZSTD_OUT_LEN];	\
		asm volatile("" : "+r"(acc), "+m"(state_name) :: "memory"); \
	}								\
	return acc;							\
}

DEFINE_VARIANT_BODY(data_pgot, data_state,
		    pgot_ZSTD_decompressBegin_data_pgot,
		    pgot_ZSTD_decompressDCtx_data_pgot)
DEFINE_VARIANT_BODY(func_pgot, func_state,
		    pgot_ZSTD_decompressBegin_func_pgot,
		    pgot_ZSTD_decompressDCtx_func_pgot)
DEFINE_VARIANT_BODY(all_pgot, all_state,
		    pgot_ZSTD_decompressBegin_all_pgot,
		    pgot_ZSTD_decompressDCtx_all_pgot)

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

	pr_info("PGOT_L3_RAW,layer3_zstd_decompress_kmod,%s,%d,%s,%d,%lu,%s,%s,%s\n",
		build, run_id, variant, repeat, iterations,
		origin_buf, variant_buf, delta_buf);
}

static int validate_one(struct zstd_case_state *variant)
{
	size_t ret_origin, ret_variant;

	prepare_context(&origin_state, pgot_ZSTD_decompressBegin_origin);
	ret_origin = pgot_ZSTD_decompressDCtx_origin(origin_state.dctx,
						     origin_state.output,
						     sizeof(origin_state.output),
						     bench_input,
						     sizeof(bench_input));

	prepare_context(variant, variant->begin);
	ret_variant = variant->decompress(variant->dctx, variant->output,
					  sizeof(variant->output),
					  bench_input, sizeof(bench_input));

	if (ZSTD_isError(ret_origin) || ZSTD_isError(ret_variant) ||
	    ret_origin != ret_variant ||
	    memcmp(origin_state.output, variant->output, ret_origin) != 0) {
		pr_err("PGOT_L3_VALIDATE_FAIL,zstd,%s,origin_ret=%zu,variant_ret=%zu\n",
		       variant->name, ret_origin, ret_variant);
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

static int init_state(struct zstd_case_state *state)
{
	size_t workspace_size;
	size_t begin_ret;

	workspace_size = state->workspace_bound();
	state->workspace = vzalloc(workspace_size);
	if (!state->workspace)
		return -ENOMEM;

	state->dctx = state->init(state->workspace, workspace_size);
	if (!state->dctx) {
		vfree(state->workspace);
		state->workspace = NULL;
		return -EINVAL;
	}

	begin_ret = state->begin(state->dctx);
	if (ZSTD_isError(begin_ret)) {
		vfree(state->workspace);
		state->workspace = NULL;
		state->dctx = NULL;
		return -EINVAL;
	}

	return 0;
}

static void free_state(struct zstd_case_state *state)
{
	if (state->workspace) {
		vfree(state->workspace);
		state->workspace = NULL;
		state->dctx = NULL;
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

	pr_info("PGOT_L3_START,experiment=layer3_zstd_decompress_kmod,build=%s,iterations=%lu,warmup=%lu,repeats=%d,run_id=%d,cpu=%d,irq_off=%d,input_len=%zu,variants=%s\n",
		build, iterations, warmup, repeats, run_id, cpu,
		irq_off, sizeof(bench_input), variants);

	ret = run_all_cases();

	pr_info("PGOT_L3_DONE,experiment=layer3_zstd_decompress_kmod,ret=%d,sink=%llu\n",
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
	pr_info("PGOT_L3_EXIT,experiment=layer3_zstd_decompress_kmod\n");
}

module_init(bench_init);
module_exit(bench_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Layer3 ZSTD decompression copied-closure PGOT benchmark");
