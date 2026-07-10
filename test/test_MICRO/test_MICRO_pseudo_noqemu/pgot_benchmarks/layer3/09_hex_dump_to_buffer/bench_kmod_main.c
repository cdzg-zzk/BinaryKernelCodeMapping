#include <linux/cpumask.h>
#include <linux/errno.h>
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

#define SCALE 1000ULL
#define SRC_LEN 64
#define LINE_LEN 128

#ifndef noipa
#define noipa __attribute__((noipa))
#endif

#ifdef BENCH_NOTRACE
#define BENCH_NOTRACE_ATTR __attribute__((no_instrument_function))
#else
#define BENCH_NOTRACE_ATTR
#endif

#if defined(BENCH_ALIGN64) || !defined(BENCH_NO_ALIGN64)
#define BENCH_ALIGN_ATTR __attribute__((aligned(64)))
#else
#define BENCH_ALIGN_ATTR
#endif

typedef u64 (*body_fn_t)(u64 iters);
typedef int (*hex_fn_t)(const void *buf, size_t len, int rowsize,
			int groupsize, char *linebuf, size_t linebuflen,
			bool ascii);

int pgot_hex_dump_to_buffer_origin(const void *buf, size_t len, int rowsize,
				   int groupsize, char *linebuf,
				   size_t linebuflen, bool ascii);
int pgot_hex_dump_to_buffer_data_pgot(const void *buf, size_t len, int rowsize,
				      int groupsize, char *linebuf,
				      size_t linebuflen, bool ascii);
int pgot_hex_dump_to_buffer_func_pgot(const void *buf, size_t len, int rowsize,
				      int groupsize, char *linebuf,
				      size_t linebuflen, bool ascii);
int pgot_hex_dump_to_buffer_all_pgot(const void *buf, size_t len, int rowsize,
				     int groupsize, char *linebuf,
				     size_t linebuflen, bool ascii);

static unsigned long iterations = 10000;
static unsigned long warmup = 10000;
static unsigned int input_len = 32;
static int repeats = 31;
static int run_id;
static int cpu = -1;
static bool irq_off;
static char *build = "unknown";
static char *variants = "all_pgot";

module_param(iterations, ulong, 0444);
module_param(warmup, ulong, 0444);
module_param(input_len, uint, 0444);
module_param(repeats, int, 0444);
module_param(run_id, int, 0444);
module_param(cpu, int, 0444);
module_param(irq_off, bool, 0444);
module_param(build, charp, 0444);
module_param(variants, charp, 0444);

static u8 bench_src[SRC_LEN] __aligned(64);
static char line_origin[LINE_LEN] __aligned(64);
static char line_data[LINE_LEN] __aligned(64);
static char line_func[LINE_LEN] __aligned(64);
static char line_all[LINE_LEN] __aligned(64);
static volatile u64 sink_u64;

struct variant_desc {
	const char *name;
	hex_fn_t fn;
	char *line;
};

static struct variant_desc variant_descs[] = {
	{ "data_pgot", pgot_hex_dump_to_buffer_data_pgot, line_data },
	{ "func_pgot", pgot_hex_dump_to_buffer_func_pgot, line_func },
	{ "all_pgot", pgot_hex_dump_to_buffer_all_pgot, line_all },
};

static inline void compiler_barrier(void)
{
	asm volatile("" ::: "memory");
}

static inline u64 rdtsc_start(void)
{
	unsigned int lo, hi;

	asm volatile("lfence\n\trdtsc" : "=a"(lo), "=d"(hi) :: "memory");
	return ((u64)hi << 32) | lo;
}

static inline u64 rdtsc_end(void)
{
	unsigned int lo, hi;

	asm volatile("rdtscp\n\tlfence" : "=a"(lo), "=d"(hi) :: "rcx", "memory");
	return ((u64)hi << 32) | lo;
}

#define DEFINE_HEX_BODY(name, fn_sym, line_sym) \
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_##name(u64 iters) \
{ \
	u64 i, acc = 0; \
	size_t len = input_len; \
	for (i = 0; i < iters; i++) { \
		int ret = fn_sym(bench_src, len, 32, 1, line_sym, LINE_LEN, true); \
		acc += ret + line_sym[(i + ret) & (LINE_LEN - 1)]; \
		asm volatile("" : "+r"(acc), "+m"(line_sym) :: "memory"); \
	} \
	return acc; \
}

DEFINE_HEX_BODY(origin, pgot_hex_dump_to_buffer_origin, line_origin)
DEFINE_HEX_BODY(data_pgot, pgot_hex_dump_to_buffer_data_pgot, line_data)
DEFINE_HEX_BODY(func_pgot, pgot_hex_dump_to_buffer_func_pgot, line_func)
DEFINE_HEX_BODY(all_pgot, pgot_hex_dump_to_buffer_all_pgot, line_all)

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
	pr_info("PGOT_L3_RAW,layer3_hex_dump_to_buffer_kmod,%s,%d,%s,%d,%lu,%s,%s,%s\n",
		build, run_id, variant, repeat, iterations,
		origin_buf, variant_buf, delta_buf);
}

static void do_warmup(void)
{
	int i;

	if (!warmup)
		return;
	sink_u64 ^= body_origin(warmup);
	for (i = 0; i < ARRAY_SIZE(variant_descs); i++)
		sink_u64 ^= select_body(variant_descs[i].name)(warmup);
	compiler_barrier();
}

static int run_case(const char *variant)
{
	body_fn_t origin_body = select_body("origin");
	body_fn_t variant_body = select_body(variant);
	s64 *origin_samples, *variant_samples;
	int r;

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
			variant0 = measure_x1000(variant_body, iterations);
			origin0 = measure_x1000(origin_body, iterations);
			origin1 = measure_x1000(origin_body, iterations);
			variant1 = measure_x1000(variant_body, iterations);
		} else {
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

static int pin_current_thread(void)
{
	if (cpu < 0)
		return 0;
	if (cpu >= nr_cpu_ids || !cpu_online(cpu))
		return -EINVAL;
	return set_cpus_allowed_ptr(current, cpumask_of(cpu));
}

static int init_bench_state(void)
{
	int i;

	if (!input_len || input_len > 32)
		input_len = 32;
	for (i = 0; i < SRC_LEN; i++)
		bench_src[i] = (u8)(0x20 + ((i * 13) & 0x5f));
	memset(line_origin, 0, sizeof(line_origin));
	memset(line_data, 0, sizeof(line_data));
	memset(line_func, 0, sizeof(line_func));
	memset(line_all, 0, sizeof(line_all));
	compiler_barrier();
	return 0;
}

static int validate_one(struct variant_desc *variant)
{
	int ret_origin, ret_variant;

	memset(line_origin, 0, sizeof(line_origin));
	memset(variant->line, 0, LINE_LEN);
	ret_origin = pgot_hex_dump_to_buffer_origin(bench_src, input_len, 32, 1,
						    line_origin, LINE_LEN, true);
	ret_variant = variant->fn(bench_src, input_len, 32, 1, variant->line,
				  LINE_LEN, true);
	if (ret_origin != ret_variant || strcmp(line_origin, variant->line)) {
		pr_err("PGOT_L3_VALIDATE_FAIL,experiment=layer3_hex_dump_to_buffer_kmod,variant=%s,origin_ret=%d,variant_ret=%d\n",
		       variant->name, ret_origin, ret_variant);
		return -EINVAL;
	}
	return 0;
}

static int validate_variants(void)
{
	int i, ret;

	for (i = 0; i < ARRAY_SIZE(variant_descs); i++) {
		ret = validate_one(&variant_descs[i]);
		if (ret)
			return ret;
	}
	return 0;
}

static bool variant_enabled(const char *name)
{
	char *p = variants;
	size_t n = strlen(name);

	if (!variants || !strcmp(variants, "all"))
		return true;
	while (*p) {
		while (*p == ',' || *p == ' ')
			p++;
		if (!strncmp(p, name, n) && (p[n] == '\0' || p[n] == ',' || p[n] == ' '))
			return true;
		while (*p && *p != ',')
			p++;
	}
	return false;
}

static int run_all_cases(void)
{
	int i, ret;

	for (i = 0; i < ARRAY_SIZE(variant_descs); i++) {
		if (!variant_enabled(variant_descs[i].name))
			continue;
		ret = run_case(variant_descs[i].name);
		if (ret)
			return ret;
	}
	return 0;
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
	ret = validate_variants();
	if (ret)
		return ret;
	pr_info("PGOT_L3_START,experiment=layer3_hex_dump_to_buffer_kmod,build=%s,iterations=%lu,warmup=%lu,repeats=%d,run_id=%d,cpu=%d,irq_off=%d,input_len=%u,variants=%s\n",
		build, iterations, warmup, repeats, run_id, cpu, irq_off,
		input_len, variants);
	do_warmup();
	ret = run_all_cases();
	pr_info("PGOT_L3_DONE,experiment=layer3_hex_dump_to_buffer_kmod,ret=%d,sink=%llu\n",
		ret, (unsigned long long)sink_u64);
	return ret;
}

static void __exit bench_exit(void)
{
}

module_init(bench_init);
module_exit(bench_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("PGOT microbenchmark");
MODULE_DESCRIPTION("Layer3 hex_dump_to_buffer copied-closure PGOT benchmark");
