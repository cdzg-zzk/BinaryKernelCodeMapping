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

#define SCALE 1000ULL

#ifndef noipa
#define noipa __attribute__((noipa))
#endif

#ifdef BENCH_NOTRACE
#define BENCH_NOTRACE_ATTR __attribute__((no_instrument_function))
#else
#define BENCH_NOTRACE_ATTR
#endif

/*
 * Keep the benchmark bodies aligned by default to reduce accidental
 * origin/variant layout differences. Define BENCH_NO_ALIGN64 to disable.
 * BENCH_ALIGN64 is accepted for compatibility with older run.sh flags.
 */
#if defined(BENCH_ALIGN64) || !defined(BENCH_NO_ALIGN64)
#define BENCH_ALIGN_ATTR __attribute__((aligned(64)))
#else
#define BENCH_ALIGN_ATTR
#endif

typedef u64 (*body_fn_t)(u64 iters);

static unsigned long iterations = 100000;
static int repeats = 31;
static int warmups = 5;
static int run_id;
static int cpu = -1;
static bool irq_off;
static char *build = "unknown";

module_param(iterations, ulong, 0444);
MODULE_PARM_DESC(iterations, "SHA-256 block transforms per timed sample");
module_param(repeats, int, 0444);
MODULE_PARM_DESC(repeats, "paired origin/variant repetitions");
module_param(warmups, int, 0444);
MODULE_PARM_DESC(warmups, "warmup measurements per function before raw sampling");
module_param(run_id, int, 0444);
MODULE_PARM_DESC(run_id, "raw sample run id");
module_param(cpu, int, 0444);
MODULE_PARM_DESC(cpu, "optional CPU affinity for module init thread");
module_param(irq_off, bool, 0444);
MODULE_PARM_DESC(irq_off, "disable local IRQs during each timed sample; use only for short samples");
module_param(build, charp, 0444);
MODULE_PARM_DESC(build, "build label: no_retpoline or retpoline");

static const u32 sha256_k_origin[64] __aligned(64) = {
	0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U,
	0x3956c25bU, 0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U,
	0xd807aa98U, 0x12835b01U, 0x243185beU, 0x550c7dc3U,
	0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U, 0xc19bf174U,
	0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
	0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU,
	0x983e5152U, 0xa831c66dU, 0xb00327c8U, 0xbf597fc7U,
	0xc6e00bf3U, 0xd5a79147U, 0x06ca6351U, 0x14292967U,
	0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU, 0x53380d13U,
	0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
	0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U,
	0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
	0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U,
	0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U,
	0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
	0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U,
};

const u32 *pgot_k_table[1] __aligned(64);
static volatile u64 sink_u64;
static u8 bench_block[64] __aligned(64);

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

static inline u32 ror32_local(u32 x, unsigned int n)
{
	return (x >> n) | (x << (32 - n));
}

static inline u32 ch(u32 x, u32 y, u32 z)
{
	return z ^ (x & (y ^ z));
}

static inline u32 maj(u32 x, u32 y, u32 z)
{
	return (x & y) | (z & (x | y));
}

static inline u32 big_sigma0(u32 x)
{
	return ror32_local(x, 2) ^ ror32_local(x, 13) ^ ror32_local(x, 22);
}

static inline u32 big_sigma1(u32 x)
{
	return ror32_local(x, 6) ^ ror32_local(x, 11) ^ ror32_local(x, 25);
}

static inline u32 small_sigma0(u32 x)
{
	return ror32_local(x, 7) ^ ror32_local(x, 18) ^ (x >> 3);
}

static inline u32 small_sigma1(u32 x)
{
	return ror32_local(x, 17) ^ ror32_local(x, 19) ^ (x >> 10);
}

static inline u32 sha256_load_be32_word(const u8 *p)
{
	u32 v;

	v = ((u32)p[0] << 24) | ((u32)p[1] << 16) |
	    ((u32)p[2] << 8) | (u32)p[3];
	asm volatile("" : "+r"(v) :: "memory");
	return v;
}

/*
 * Symmetric initialization:
 * - origin also materializes k__ as a register value.
 * - origin and data_pgot use the same compiler barrier on k__.
 *
 * This avoids comparing a highly optimized constant-address direct form
 * against a constrained pgot form.
 */
#define DATA_DIRECT_INIT() \
	const u32 *k__ = sha256_k_origin; \
	asm volatile("" : "+r"(k__) :: "memory")

#define DATA_PGOT_INIT() \
	const u32 * volatile *slot__ = (const u32 * volatile *)pgot_k_table; \
	const u32 *k__ = slot__[0]; \
	asm volatile("" : "+r"(k__) :: "memory")

#define LOAD_DIRECT(p) \
	sha256_load_be32_word(p)

#define DEFINE_SHA256_TRANSFORM(name, DATA_INIT, LOAD_WORD) \
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR \
void sha256_transform_##name(u32 state[8], const u8 block[64]) \
{ \
	u32 W[64]; \
	u32 a, b, c, d, e, f, g, h; \
	u32 t1, t2; \
	int i; \
	DATA_INIT(); \
	for (i = 0; i < 16; i++) \
		W[i] = LOAD_WORD(block + i * 4); \
	for (i = 16; i < 64; i++) \
		W[i] = small_sigma1(W[i - 2]) + W[i - 7] + \
		       small_sigma0(W[i - 15]) + W[i - 16]; \
	a = state[0]; b = state[1]; c = state[2]; d = state[3]; \
	e = state[4]; f = state[5]; g = state[6]; h = state[7]; \
	for (i = 0; i < 64; i++) { \
		t1 = h + big_sigma1(e) + ch(e, f, g) + k__[i] + W[i]; \
		t2 = big_sigma0(a) + maj(a, b, c); \
		h = g; \
		g = f; \
		f = e; \
		e = d + t1; \
		d = c; \
		c = b; \
		b = a; \
		a = t1 + t2; \
	} \
	state[0] += a; state[1] += b; state[2] += c; state[3] += d; \
	state[4] += e; state[5] += f; state[6] += g; state[7] += h; \
	asm volatile("" : "+m"(*state) :: "memory"); \
}

DEFINE_SHA256_TRANSFORM(origin, DATA_DIRECT_INIT, LOAD_DIRECT)
DEFINE_SHA256_TRANSFORM(data_pgot, DATA_PGOT_INIT, LOAD_DIRECT)

static void init_tables(void)
{
	int i;

	for (i = 0; i < ARRAY_SIZE(bench_block); i++)
		bench_block[i] = (u8)(0x40 + i * 17 + (i >> 1));
	pgot_k_table[0] = sha256_k_origin;
	compiler_barrier();
}

static inline void init_state(u32 state[8])
{
	state[0] = 0x6a09e667U;
	state[1] = 0xbb67ae85U;
	state[2] = 0x3c6ef372U;
	state[3] = 0xa54ff53aU;
	state[4] = 0x510e527fU;
	state[5] = 0x9b05688cU;
	state[6] = 0x1f83d9abU;
	state[7] = 0x5be0cd19U;
}

#define DEFINE_BODY(name) \
static noinline BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_##name(u64 iters) \
{ \
	u32 state[8]; \
	u64 it; \
	init_state(state); \
	for (it = 0; it < iters; it++) { \
		sha256_transform_##name(state, bench_block); \
		state[0] += (u32)it; \
		asm volatile("" : "+m"(state), "+m"(bench_block) :: "memory"); \
	} \
	return ((u64)state[0] << 32) ^ state[1] ^ state[7]; \
}

DEFINE_BODY(origin)
DEFINE_BODY(data_pgot)

static body_fn_t select_body(const char *variant)
{
	if (!strcmp(variant, "origin"))
		return body_origin;
	if (!strcmp(variant, "data_pgot") || !strcmp(variant, "all_pgot"))
		return body_data_pgot;
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
		abs_value = (u64)-value;
		scnprintf(buf, size, "-%llu.%03llu",
			  div64_u64(abs_value, SCALE), abs_value % SCALE);
	} else {
		abs_value = (u64)value;
		scnprintf(buf, size, "%llu.%03llu",
			  div64_u64(abs_value, SCALE), abs_value % SCALE);
	}
}

static void print_raw_line(const char *variant, int repeat, s64 origin, s64 pgot)
{
	char origin_buf[32];
	char pgot_buf[32];
	char delta_buf[32];

	scaled_to_buf(origin_buf, sizeof(origin_buf), origin);
	scaled_to_buf(pgot_buf, sizeof(pgot_buf), pgot);
	scaled_to_buf(delta_buf, sizeof(delta_buf), pgot - origin);

	pr_info("PGOT_L3SHA_RAW,layer3_sha256_transform,%s,%d,%s,%d,%lu,%s,%s,%s\n",
		build, run_id, variant, repeat, iterations,
		origin_buf, pgot_buf, delta_buf);
}

static void do_warmups(body_fn_t origin_fn, body_fn_t variant_fn)
{
	u64 warm_iters;
	int w;

	if (warmups <= 0)
		return;

	warm_iters = iterations / 10;
	if (!warm_iters)
		warm_iters = 1;

	for (w = 0; w < warmups; w++) {
		(void)measure_x1000(origin_fn, warm_iters);
		(void)measure_x1000(variant_fn, warm_iters);
	}
}

/*
 * Measure raw samples first and print after the timed loop.
 * This avoids printk/pr_info perturbing cache/logging state before the next
 * sample.
 */
static int run_case(const char *variant)
{
	body_fn_t origin_fn = select_body("origin");
	body_fn_t variant_fn = select_body(variant);
	s64 *origin_samples;
	s64 *pgot_samples;
	int r;

	if (!origin_fn || !variant_fn)
		return -EINVAL;
	if (repeats <= 0)
		return -EINVAL;

	origin_samples = kcalloc(repeats, sizeof(*origin_samples), GFP_KERNEL);
	if (!origin_samples)
		return -ENOMEM;

	pgot_samples = kcalloc(repeats, sizeof(*pgot_samples), GFP_KERNEL);
	if (!pgot_samples) {
		kfree(origin_samples);
		return -ENOMEM;
	}

	do_warmups(origin_fn, variant_fn);

	for (r = 0; r < repeats; r++) {
		s64 origin0, origin1, pgot0, pgot1;

		if (r & 1) {
			/* BAAB order */
			pgot0 = measure_x1000(variant_fn, iterations);
			origin0 = measure_x1000(origin_fn, iterations);
			origin1 = measure_x1000(origin_fn, iterations);
			pgot1 = measure_x1000(variant_fn, iterations);
		} else {
			/* ABBA order */
			origin0 = measure_x1000(origin_fn, iterations);
			pgot0 = measure_x1000(variant_fn, iterations);
			pgot1 = measure_x1000(variant_fn, iterations);
			origin1 = measure_x1000(origin_fn, iterations);
		}

		origin_samples[r] = div_s64(origin0 + origin1, 2);
		pgot_samples[r] = div_s64(pgot0 + pgot1, 2);
	}

	for (r = 0; r < repeats; r++)
		print_raw_line(variant, r, origin_samples[r], pgot_samples[r]);

	kfree(pgot_samples);
	kfree(origin_samples);
	return 0;
}

static int run_all_cases(void)
{
	static const char *variants[] = {"all_pgot"};
	int i, ret;

	for (i = 0; i < ARRAY_SIZE(variants); i++) {
		ret = run_case(variants[i]);
		if (ret)
			return ret;
	}
	return 0;
}

static int pin_current_cpu(void)
{
	if (cpu < 0)
		return 0;
	if (cpu >= nr_cpu_ids || !cpu_online(cpu))
		return -EINVAL;
	return set_cpus_allowed_ptr(current, cpumask_of(cpu));
}

static int __init pgot_l3sha_init(void)
{
	int ret;

	if (!iterations || repeats <= 0)
		return -EINVAL;

	init_tables();
	ret = pin_current_cpu();
	if (ret) {
		pr_err("PGOT_L3SHA_ERROR,cpu_pin_failed,cpu=%d,ret=%d\n", cpu, ret);
		return ret;
	}

	pr_info("PGOT_L3SHA_START,build=%s,iterations=%lu,repeats=%d,warmups=%d,run_id=%d,cpu=%d,irq_off=%d\n",
		build, iterations, repeats, warmups, run_id, cpu, irq_off);
	ret = run_all_cases();
	pr_info("PGOT_L3SHA_DONE,ret=%d,sink=%llu\n", ret, (u64)sink_u64);
	return ret;
}

static void __exit pgot_l3sha_exit(void)
{
	pr_info("PGOT_L3SHA_EXIT\n");
}

module_init(pgot_l3sha_init);
module_exit(pgot_l3sha_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("pgot_benchmarks");
MODULE_DESCRIPTION("Layer3 SHA-256 transform origin/data-pgot benchmark");
