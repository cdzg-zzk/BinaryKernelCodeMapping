#include <crypto/aes.h>
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
#define AES_BLOCK 16

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
typedef void (*aes_enc_fn_t)(const struct crypto_aes_ctx *ctx, u8 *out,
			     const u8 *in);

int pgot_aes_expandkey_origin(struct crypto_aes_ctx *ctx, const u8 *in_key,
			      unsigned int key_len);
int pgot_aes_expandkey_data_pgot(struct crypto_aes_ctx *ctx, const u8 *in_key,
				 unsigned int key_len);
int pgot_aes_expandkey_func_pgot(struct crypto_aes_ctx *ctx, const u8 *in_key,
				 unsigned int key_len);
int pgot_aes_expandkey_all_pgot(struct crypto_aes_ctx *ctx, const u8 *in_key,
				unsigned int key_len);
void pgot_aes_encrypt_origin(const struct crypto_aes_ctx *ctx, u8 *out,
			     const u8 *in);
void pgot_aes_encrypt_data_pgot(const struct crypto_aes_ctx *ctx, u8 *out,
				const u8 *in);
void pgot_aes_encrypt_func_pgot(const struct crypto_aes_ctx *ctx, u8 *out,
				const u8 *in);
void pgot_aes_encrypt_all_pgot(const struct crypto_aes_ctx *ctx, u8 *out,
			       const u8 *in);

static unsigned long iterations = 10000;
static unsigned long warmup = 10000;
static unsigned int input_len = AES_BLOCK;
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

static u8 bench_key[AES_KEYSIZE_128] __aligned(64);
static u8 bench_in[AES_BLOCK] __aligned(64);
static u8 out_origin[AES_BLOCK] __aligned(64);
static u8 out_data[AES_BLOCK] __aligned(64);
static u8 out_func[AES_BLOCK] __aligned(64);
static u8 out_all[AES_BLOCK] __aligned(64);
static struct crypto_aes_ctx ctx_origin __aligned(64);
static struct crypto_aes_ctx ctx_data __aligned(64);
static struct crypto_aes_ctx ctx_func __aligned(64);
static struct crypto_aes_ctx ctx_all __aligned(64);
static volatile u64 sink_u64;

struct variant_desc {
	const char *name;
	aes_enc_fn_t fn;
	struct crypto_aes_ctx *ctx;
	u8 *out;
};

static struct variant_desc variant_descs[] = {
	{ "data_pgot", pgot_aes_encrypt_data_pgot, &ctx_data, out_data },
	{ "func_pgot", pgot_aes_encrypt_func_pgot, &ctx_func, out_func },
	{ "all_pgot", pgot_aes_encrypt_all_pgot, &ctx_all, out_all },
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

#define DEFINE_AES_BODY(name, fn_sym, ctx_sym, out_sym) \
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_##name(u64 iters) \
{ \
	u64 i, acc = 0; \
	for (i = 0; i < iters; i++) { \
		bench_in[0] ^= (u8)i; \
		fn_sym(ctx_sym, out_sym, bench_in); \
		acc += out_sym[(i + out_sym[0]) & (AES_BLOCK - 1)]; \
		asm volatile("" : "+r"(acc), "+m"(out_sym), "+m"(bench_in) :: "memory"); \
	} \
	return acc; \
}

DEFINE_AES_BODY(origin, pgot_aes_encrypt_origin, &ctx_origin, out_origin)
DEFINE_AES_BODY(data_pgot, pgot_aes_encrypt_data_pgot, &ctx_data, out_data)
DEFINE_AES_BODY(func_pgot, pgot_aes_encrypt_func_pgot, &ctx_func, out_func)
DEFINE_AES_BODY(all_pgot, pgot_aes_encrypt_all_pgot, &ctx_all, out_all)

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
	pr_info("PGOT_L3_RAW,layer3_aes_encrypt_kmod,%s,%d,%s,%d,%lu,%s,%s,%s\n",
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
	int i, ret;

	for (i = 0; i < AES_KEYSIZE_128; i++)
		bench_key[i] = (u8)(0x11 + i * 7);
	for (i = 0; i < AES_BLOCK; i++)
		bench_in[i] = (u8)(0x31 + i * 13);

	ret = pgot_aes_expandkey_origin(&ctx_origin, bench_key, AES_KEYSIZE_128);
	if (ret)
		return ret;
	ret = pgot_aes_expandkey_data_pgot(&ctx_data, bench_key, AES_KEYSIZE_128);
	if (ret)
		return ret;
	ret = pgot_aes_expandkey_func_pgot(&ctx_func, bench_key, AES_KEYSIZE_128);
	if (ret)
		return ret;
	ret = pgot_aes_expandkey_all_pgot(&ctx_all, bench_key, AES_KEYSIZE_128);
	if (ret)
		return ret;
	memset(out_origin, 0, sizeof(out_origin));
	memset(out_data, 0, sizeof(out_data));
	memset(out_func, 0, sizeof(out_func));
	memset(out_all, 0, sizeof(out_all));
	compiler_barrier();
	return 0;
}

static int validate_one(struct variant_desc *variant)
{
	u8 in[AES_BLOCK] __aligned(16);

	memcpy(in, bench_in, AES_BLOCK);
	memset(out_origin, 0, sizeof(out_origin));
	memset(variant->out, 0, AES_BLOCK);
	pgot_aes_encrypt_origin(&ctx_origin, out_origin, in);
	variant->fn(variant->ctx, variant->out, in);
	if (memcmp(out_origin, variant->out, AES_BLOCK)) {
		pr_err("PGOT_L3_VALIDATE_FAIL,experiment=layer3_aes_encrypt_kmod,variant=%s\n",
		       variant->name);
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
	pr_info("PGOT_L3_START,experiment=layer3_aes_encrypt_kmod,build=%s,iterations=%lu,warmup=%lu,repeats=%d,run_id=%d,cpu=%d,irq_off=%d,input_len=%u,variants=%s\n",
		build, iterations, warmup, repeats, run_id, cpu, irq_off,
		input_len, variants);
	do_warmup();
	ret = run_all_cases();
	pr_info("PGOT_L3_DONE,experiment=layer3_aes_encrypt_kmod,ret=%d,sink=%llu\n",
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
MODULE_DESCRIPTION("Layer3 aes_encrypt copied-closure PGOT benchmark");
