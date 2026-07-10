#include <linux/cpumask.h>
#include <linux/crc32poly.h>
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
#include <asm/byteorder.h>

#define SCALE 1000ULL
#define CRC_DATA_LEN 512
#define CRC_TABLE_SIZE 256

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
typedef const u32 *crc_table_t;

static unsigned long iterations = 10000;
static unsigned long warmup = 10000;
static int repeats = 31;
static int run_id;
static int cpu = -1;
static bool irq_off;
static char *build = "unknown";

module_param(iterations, ulong, 0444);
MODULE_PARM_DESC(iterations, "crc32_le operations per timed sample");
module_param(warmup, ulong, 0444);
MODULE_PARM_DESC(warmup, "warmup crc32_le operations before raw sampling");
module_param(repeats, int, 0444);
MODULE_PARM_DESC(repeats, "paired origin/variant repetitions");
module_param(run_id, int, 0444);
MODULE_PARM_DESC(run_id, "raw sample run id");
module_param(cpu, int, 0444);
MODULE_PARM_DESC(cpu, "optional CPU affinity for module init thread");
module_param(irq_off, bool, 0444);
MODULE_PARM_DESC(irq_off, "disable local IRQs during each timed sample");
module_param(build, charp, 0444);
MODULE_PARM_DESC(build, "build label: no_retpoline or retpoline");

static crc_table_t pgot_crc32table_le[1] __aligned(64);
static u32 crc32table_le_local[CRC_TABLE_SIZE] __aligned(64);
static u8 bench_data[CRC_DATA_LEN] __aligned(64);
static volatile u64 sink_u64;

static inline void compiler_barrier(void)
{
	asm volatile("" ::: "memory");
}

static inline u64 rdtsc_start(void)
{
	unsigned int lo, hi;

	asm volatile("lfence\n\trdtsc"
		     : "=a"(lo), "=d"(hi)
		     :
		     : "memory");
	return ((u64)hi << 32) | lo;
}

static inline u64 rdtsc_end(void)
{
	unsigned int lo, hi;

	asm volatile("rdtscp\n\tlfence"
		     : "=a"(lo), "=d"(hi)
		     :
		     : "rcx", "memory");
	return ((u64)hi << 32) | lo;
}

static void init_crc32table_le(void)
{
	int i, bit;

	for (i = 0; i < CRC_TABLE_SIZE; i++) {
		u32 crc = i;

		for (bit = 0; bit < 8; bit++)
			crc = (crc >> 1) ^ ((crc & 1) ? CRC32_POLY_LE : 0);
		crc32table_le_local[i] = crc;
	}
}

static inline u32 crc32_le_generic_local(u32 crc, const unsigned char *p,
					 size_t len, const u32 *tab)
{
	while (len--) {
		crc ^= *p++;
		crc = (crc >> 8) ^ tab[crc & 255];
	}
	return crc;
}

static noinline noipa BENCH_NOTRACE_ATTR u32
crc32_le_origin_local(u32 crc, const unsigned char *p, size_t len)
{
	return crc32_le_generic_local(crc, p, len, crc32table_le_local);
}

static noinline noipa BENCH_NOTRACE_ATTR u32
crc32_le_all_pgot_local(u32 crc, const unsigned char *p, size_t len)
{
	crc_table_t volatile *slot = pgot_crc32table_le;
	crc_table_t tab = slot[0];

	asm volatile("" : "+r"(tab) :: "memory");
	return crc32_le_generic_local(crc, p, len, tab);
}

static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64
body_origin(u64 iters)
{
	u64 i;
	u32 crc = 0xffffffffU;

	for (i = 0; i < iters; i++) {
		crc = crc32_le_origin_local(crc + (u32)i, bench_data,
					    CRC_DATA_LEN);
		asm volatile("" : "+r"(crc) :: "memory");
	}
	return crc;
}

static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64
body_all_pgot(u64 iters)
{
	u64 i;
	u32 crc = 0xffffffffU;

	for (i = 0; i < iters; i++) {
		crc = crc32_le_all_pgot_local(crc + (u32)i, bench_data,
					      CRC_DATA_LEN);
		asm volatile("" : "+r"(crc) :: "memory");
	}
	return crc;
}

static body_fn_t select_body(const char *variant)
{
	if (!strcmp(variant, "origin"))
		return body_origin;
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

	pr_info("PGOT_L3_RAW,layer3_crc32_le_kmod,%s,%d,%s,%d,%lu,%s,%s,%s\n",
		build, run_id, variant, repeat, iterations,
		origin_buf, variant_buf, delta_buf);
}

static void do_warmup(void)
{
	if (!warmup)
		return;

	sink_u64 ^= body_origin(warmup);
	sink_u64 ^= body_all_pgot(warmup);
	compiler_barrier();
}

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

	for (i = 0; i < CRC_DATA_LEN; i++)
		bench_data[i] = (u8)(0x5a + i * 17 + (i >> 1));

	init_crc32table_le();
	pgot_crc32table_le[0] = crc32table_le_local;
	compiler_barrier();
	return 0;
}

static int validate_variant(void)
{
	u32 origin, variant;

	origin = crc32_le_origin_local(0xffffffffU, bench_data, CRC_DATA_LEN);
	variant = crc32_le_all_pgot_local(0xffffffffU, bench_data, CRC_DATA_LEN);
	if (origin != variant) {
		pr_err("PGOT_L3_VALIDATE_FAIL,experiment=layer3_crc32_le_kmod,origin=%x,variant=%x\n",
		       origin, variant);
		return -EINVAL;
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

	ret = validate_variant();
	if (ret)
		return ret;

	pr_info("PGOT_L3_START,experiment=layer3_crc32_le_kmod,build=%s,iterations=%lu,warmup=%lu,repeats=%d,run_id=%d,cpu=%d,irq_off=%d,data_len=%d,variants=all_pgot\n",
		build, iterations, warmup, repeats, run_id, cpu, irq_off,
		CRC_DATA_LEN);

	do_warmup();
	ret = run_case("all_pgot");

	pr_info("PGOT_L3_DONE,experiment=layer3_crc32_le_kmod,ret=%d,sink=%llu\n",
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
MODULE_DESCRIPTION("Layer3 crc32_le copied-closure all-pgot benchmark");
