#include <linux/bch.h>
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
#include <asm/byteorder.h>

#define SCALE 1000ULL
#define BCH_DATA_LEN 512
#define BCH_ECC_MAX 128
#define BCH_MAX_M 15
#define BCH_MAX_T 64
#define BCH_ECC_WORDS(_p) DIV_ROUND_UP((_p)->m * (_p)->t, 32)
#define BCH_ECC_BYTES(_p) DIV_ROUND_UP((_p)->m * (_p)->t, 8)
#define BCH_ECC_MAX_WORDS DIV_ROUND_UP(BCH_MAX_M * BCH_MAX_T, 32)

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
typedef void *(*memcpy_fn_t)(void *dst, const void *src, size_t n);

static unsigned long iterations = 10000;
static unsigned long warmup = 10000;
static int repeats = 31;
static int run_id;
static int cpu = -1;
static bool irq_off;
static char *build = "unknown";
static char *variants = "all_pgot";

module_param(iterations, ulong, 0444);
MODULE_PARM_DESC(iterations, "BCH encode operations per timed sample");
module_param(warmup, ulong, 0444);
MODULE_PARM_DESC(warmup, "warmup BCH encode operations before raw sampling");
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

static u8 swap_bits_table_origin[] __aligned(64) = {
	0x00, 0x80, 0x40, 0xc0, 0x20, 0xa0, 0x60, 0xe0,
	0x10, 0x90, 0x50, 0xd0, 0x30, 0xb0, 0x70, 0xf0,
	0x08, 0x88, 0x48, 0xc8, 0x28, 0xa8, 0x68, 0xe8,
	0x18, 0x98, 0x58, 0xd8, 0x38, 0xb8, 0x78, 0xf8,
	0x04, 0x84, 0x44, 0xc4, 0x24, 0xa4, 0x64, 0xe4,
	0x14, 0x94, 0x54, 0xd4, 0x34, 0xb4, 0x74, 0xf4,
	0x0c, 0x8c, 0x4c, 0xcc, 0x2c, 0xac, 0x6c, 0xec,
	0x1c, 0x9c, 0x5c, 0xdc, 0x3c, 0xbc, 0x7c, 0xfc,
	0x02, 0x82, 0x42, 0xc2, 0x22, 0xa2, 0x62, 0xe2,
	0x12, 0x92, 0x52, 0xd2, 0x32, 0xb2, 0x72, 0xf2,
	0x0a, 0x8a, 0x4a, 0xca, 0x2a, 0xaa, 0x6a, 0xea,
	0x1a, 0x9a, 0x5a, 0xda, 0x3a, 0xba, 0x7a, 0xfa,
	0x06, 0x86, 0x46, 0xc6, 0x26, 0xa6, 0x66, 0xe6,
	0x16, 0x96, 0x56, 0xd6, 0x36, 0xb6, 0x76, 0xf6,
	0x0e, 0x8e, 0x4e, 0xce, 0x2e, 0xae, 0x6e, 0xee,
	0x1e, 0x9e, 0x5e, 0xde, 0x3e, 0xbe, 0x7e, 0xfe,
	0x01, 0x81, 0x41, 0xc1, 0x21, 0xa1, 0x61, 0xe1,
	0x11, 0x91, 0x51, 0xd1, 0x31, 0xb1, 0x71, 0xf1,
	0x09, 0x89, 0x49, 0xc9, 0x29, 0xa9, 0x69, 0xe9,
	0x19, 0x99, 0x59, 0xd9, 0x39, 0xb9, 0x79, 0xf9,
	0x05, 0x85, 0x45, 0xc5, 0x25, 0xa5, 0x65, 0xe5,
	0x15, 0x95, 0x55, 0xd5, 0x35, 0xb5, 0x75, 0xf5,
	0x0d, 0x8d, 0x4d, 0xcd, 0x2d, 0xad, 0x6d, 0xed,
	0x1d, 0x9d, 0x5d, 0xdd, 0x3d, 0xbd, 0x7d, 0xfd,
	0x03, 0x83, 0x43, 0xc3, 0x23, 0xa3, 0x63, 0xe3,
	0x13, 0x93, 0x53, 0xd3, 0x33, 0xb3, 0x73, 0xf3,
	0x0b, 0x8b, 0x4b, 0xcb, 0x2b, 0xab, 0x6b, 0xeb,
	0x1b, 0x9b, 0x5b, 0xdb, 0x3b, 0xbb, 0x7b, 0xfb,
	0x07, 0x87, 0x47, 0xc7, 0x27, 0xa7, 0x67, 0xe7,
	0x17, 0x97, 0x57, 0xd7, 0x37, 0xb7, 0x77, 0xf7,
	0x0f, 0x8f, 0x4f, 0xcf, 0x2f, 0xaf, 0x6f, 0xef,
	0x1f, 0x9f, 0x5f, 0xdf, 0x3f, 0xbf, 0x7f, 0xff,
};

u8 *pgot_swap_bits_table[1] __aligned(64);
memcpy_fn_t pgot_memcpy_table[1] __aligned(64);

static struct bch_control *bench_bch;
static u8 bench_data[BCH_DATA_LEN] __aligned(64);
static u8 bench_ecc[BCH_ECC_MAX] __aligned(64);
static u8 check_origin[BCH_ECC_MAX] __aligned(64);
static u8 check_variant[BCH_ECC_MAX] __aligned(64);
static volatile u64 sink_u64;

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

/*
 * Keep direct and pgot table setup symmetric: both return a runtime register
 * value with the same compiler barrier. The pgot path still adds the slot load.
 */
static inline u8 *table_direct(void)
{
	u8 *table = swap_bits_table_origin;

	asm volatile("" : "+r"(table) :: "memory");
	return table;
}

static inline u8 *table_pgot(void)
{
	u8 * volatile *slot = pgot_swap_bits_table;
	u8 *table = slot[0];

	asm volatile("" : "+r"(table) :: "memory");
	return table;
}

static inline void memcpy_direct(void *dst, const void *src, size_t n)
{
	memcpy(dst, src, n);
}

static inline void memcpy_pgot(void *dst, const void *src, size_t n)
{
	memcpy_fn_t volatile *slot = pgot_memcpy_table;
	memcpy_fn_t fn = slot[0];

	asm volatile("" : "+r"(fn) :: "memory");
	fn(dst, src, n);
}

#define DEFINE_BCH_CLOSURE(name, TABLE_EXPR, MEMCPY_OP) \
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR \
u8 swap_bits_##name(struct bch_control *bch, u8 in) \
{ \
	u8 *table__; \
	if (!bch->swap_bits) \
		return in; \
	table__ = TABLE_EXPR(); \
	return table__[in]; \
} \
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR \
void bch_encode_unaligned_##name(struct bch_control *bch, \
				 const unsigned char *data, unsigned int len, \
				 u32 *ecc) \
{ \
	int i; \
	const u32 *p; \
	const int l = BCH_ECC_WORDS(bch) - 1; \
	while (len--) { \
		u8 tmp = swap_bits_##name(bch, *data++); \
		p = bch->mod8_tab + (l + 1) * (((ecc[0] >> 24) ^ tmp) & 0xff); \
		for (i = 0; i < l; i++) \
			ecc[i] = ((ecc[i] << 8) | (ecc[i + 1] >> 24)) ^ (*p++); \
		ecc[l] = (ecc[l] << 8) ^ (*p); \
	} \
} \
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR \
void load_ecc8_##name(struct bch_control *bch, u32 *dst, const u8 *src) \
{ \
	u8 pad[4] = {0, 0, 0, 0}; \
	unsigned int i, nwords = BCH_ECC_WORDS(bch) - 1; \
	for (i = 0; i < nwords; i++, src += 4) \
		dst[i] = ((u32)swap_bits_##name(bch, src[0]) << 24) | \
			 ((u32)swap_bits_##name(bch, src[1]) << 16) | \
			 ((u32)swap_bits_##name(bch, src[2]) << 8) | \
			 swap_bits_##name(bch, src[3]); \
	MEMCPY_OP(pad, src, BCH_ECC_BYTES(bch) - 4 * nwords); \
	dst[nwords] = ((u32)swap_bits_##name(bch, pad[0]) << 24) | \
		      ((u32)swap_bits_##name(bch, pad[1]) << 16) | \
		      ((u32)swap_bits_##name(bch, pad[2]) << 8) | \
		      swap_bits_##name(bch, pad[3]); \
} \
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR \
void store_ecc8_##name(struct bch_control *bch, u8 *dst, const u32 *src) \
{ \
	u8 pad[4]; \
	unsigned int i, nwords = BCH_ECC_WORDS(bch) - 1; \
	for (i = 0; i < nwords; i++) { \
		*dst++ = swap_bits_##name(bch, src[i] >> 24); \
		*dst++ = swap_bits_##name(bch, src[i] >> 16); \
		*dst++ = swap_bits_##name(bch, src[i] >> 8); \
		*dst++ = swap_bits_##name(bch, src[i]); \
	} \
	pad[0] = swap_bits_##name(bch, src[nwords] >> 24); \
	pad[1] = swap_bits_##name(bch, src[nwords] >> 16); \
	pad[2] = swap_bits_##name(bch, src[nwords] >> 8); \
	pad[3] = swap_bits_##name(bch, src[nwords]); \
	MEMCPY_OP(dst, pad, BCH_ECC_BYTES(bch) - 4 * nwords); \
} \
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR \
void bch_encode_##name(struct bch_control *bch, const u8 *data, \
		       unsigned int len, u8 *ecc) \
{ \
	const unsigned int l = BCH_ECC_WORDS(bch) - 1; \
	unsigned int i, mlen; \
	unsigned long m; \
	u32 w, r[BCH_ECC_MAX_WORDS]; \
	const size_t r_bytes = BCH_ECC_WORDS(bch) * sizeof(*r); \
	const u32 * const tab0 = bch->mod8_tab; \
	const u32 * const tab1 = tab0 + 256 * (l + 1); \
	const u32 * const tab2 = tab1 + 256 * (l + 1); \
	const u32 * const tab3 = tab2 + 256 * (l + 1); \
	const u32 *pdata, *p0, *p1, *p2, *p3; \
	if (WARN_ON(r_bytes > sizeof(r))) \
		return; \
	if (ecc) \
		load_ecc8_##name(bch, bch->ecc_buf, ecc); \
	else \
		memset(bch->ecc_buf, 0, r_bytes); \
	m = ((unsigned long)data) & 3; \
	if (m) { \
		mlen = (len < (4 - m)) ? len : 4 - m; \
		bch_encode_unaligned_##name(bch, data, mlen, bch->ecc_buf); \
		data += mlen; \
		len -= mlen; \
	} \
	pdata = (u32 *)data; \
	mlen = len / 4; \
	data += 4 * mlen; \
	len -= 4 * mlen; \
	MEMCPY_OP(r, bch->ecc_buf, r_bytes); \
	while (mlen--) { \
		w = cpu_to_be32(*pdata++); \
		if (bch->swap_bits) \
			w = (u32)swap_bits_##name(bch, w) | \
			    ((u32)swap_bits_##name(bch, w >> 8) << 8) | \
			    ((u32)swap_bits_##name(bch, w >> 16) << 16) | \
			    ((u32)swap_bits_##name(bch, w >> 24) << 24); \
		w ^= r[0]; \
		p0 = tab0 + (l + 1) * ((w >> 0) & 0xff); \
		p1 = tab1 + (l + 1) * ((w >> 8) & 0xff); \
		p2 = tab2 + (l + 1) * ((w >> 16) & 0xff); \
		p3 = tab3 + (l + 1) * ((w >> 24) & 0xff); \
		for (i = 0; i < l; i++) \
			r[i] = r[i + 1] ^ p0[i] ^ p1[i] ^ p2[i] ^ p3[i]; \
		r[l] = p0[l] ^ p1[l] ^ p2[l] ^ p3[l]; \
	} \
	MEMCPY_OP(bch->ecc_buf, r, r_bytes); \
	if (len) \
		bch_encode_unaligned_##name(bch, data, len, bch->ecc_buf); \
	if (ecc) \
		store_ecc8_##name(bch, ecc, bch->ecc_buf); \
}

DEFINE_BCH_CLOSURE(origin, table_direct, memcpy_direct)
DEFINE_BCH_CLOSURE(data_pgot, table_pgot, memcpy_direct)
DEFINE_BCH_CLOSURE(func_pgot, table_direct, memcpy_pgot)
DEFINE_BCH_CLOSURE(all_pgot, table_pgot, memcpy_pgot)

#define DEFINE_BODY(name) \
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_##name(u64 iters) \
{ \
	u64 i, acc = 0; \
	for (i = 0; i < iters; i++) { \
		memset(bench_ecc, 0, bench_bch->ecc_bytes); \
		bch_encode_##name(bench_bch, bench_data, BCH_DATA_LEN, bench_ecc); \
		acc += bench_ecc[i % bench_bch->ecc_bytes]; \
		asm volatile("" : "+r"(acc), "+m"(bench_ecc) :: "memory"); \
	} \
	return acc; \
}

DEFINE_BODY(origin)
DEFINE_BODY(data_pgot)
DEFINE_BODY(func_pgot)
DEFINE_BODY(all_pgot)

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

static void emit_raw(const char *variant, int repeat, s64 origin, s64 variant_cycles)
{
	char origin_buf[32], variant_buf[32], delta_buf[32];

	scaled_to_buf(origin_buf, sizeof(origin_buf), origin);
	scaled_to_buf(variant_buf, sizeof(variant_buf), variant_cycles);
	scaled_to_buf(delta_buf, sizeof(delta_buf), variant_cycles - origin);

	pr_info("PGOT_L3_RAW,layer3_bch_encode_kmod,%s,%d,%s,%d,%lu,%s,%s,%s\n",
		build, run_id, variant, repeat, iterations,
		origin_buf, variant_buf, delta_buf);
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
 * This prevents printk/pr_info from perturbing the next timed sample.
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

static int init_bench_state(void)
{
	int i;

	bench_bch = bch_init(13, 8, 0, true);
	if (!bench_bch)
		return -ENOMEM;
	if (bench_bch->ecc_bytes > BCH_ECC_MAX)
		return -EINVAL;

	for (i = 0; i < BCH_DATA_LEN; i++)
		bench_data[i] = (u8)(0x31 + i * 13 + (i >> 2));

	memset(bench_ecc, 0, sizeof(bench_ecc));
	pgot_swap_bits_table[0] = swap_bits_table_origin;
	pgot_memcpy_table[0] = memcpy;
	compiler_barrier();
	return 0;
}

static int validate_variant(void (*fn)(struct bch_control *, const u8 *,
				       unsigned int, u8 *),
			    const char *name)
{
	memset(check_origin, 0, bench_bch->ecc_bytes);
	memset(check_variant, 0, bench_bch->ecc_bytes);

	bch_encode_origin(bench_bch, bench_data, BCH_DATA_LEN, check_origin);
	fn(bench_bch, bench_data, BCH_DATA_LEN, check_variant);

	if (memcmp(check_origin, check_variant, bench_bch->ecc_bytes)) {
		pr_err("PGOT_L3_VALIDATE_FAIL,experiment=layer3_bch_encode_kmod,variant=%s\n",
		       name);
		return -EINVAL;
	}
	return 0;
}

static int validate_all_variants(void)
{
	int ret;

	ret = validate_variant(bch_encode_data_pgot, "data_pgot");
	if (ret)
		return ret;
	ret = validate_variant(bch_encode_func_pgot, "func_pgot");
	if (ret)
		return ret;
	return validate_variant(bch_encode_all_pgot, "all_pgot");
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
		goto out_free;

	ret = validate_all_variants();
	if (ret)
		goto out_free;

	pr_info("PGOT_L3_START,experiment=layer3_bch_encode_kmod,build=%s,iterations=%lu,warmup=%lu,repeats=%d,run_id=%d,cpu=%d,irq_off=%d,ecc_bytes=%u,variants=%s\n",
		build, iterations, warmup, repeats, run_id, cpu, irq_off,
		bench_bch->ecc_bytes, variants);

	ret = run_all_cases();

	pr_info("PGOT_L3_DONE,experiment=layer3_bch_encode_kmod,ret=%d,sink=%llu\n",
		ret, (unsigned long long)sink_u64);

out_free:
	if (ret && bench_bch) {
		bch_free(bench_bch);
		bench_bch = NULL;
	}
	return ret;
}

static void __exit bench_exit(void)
{
	if (bench_bch)
		bch_free(bench_bch);
	pr_info("PGOT_L3_EXIT,experiment=layer3_bch_encode_kmod\n");
}

module_init(bench_init);
module_exit(bench_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Layer3 BCH encode copied-closure PGOT benchmark");
