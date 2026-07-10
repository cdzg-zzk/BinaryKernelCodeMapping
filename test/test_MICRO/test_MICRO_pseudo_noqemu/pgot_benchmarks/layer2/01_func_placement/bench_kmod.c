#include <linux/cpumask.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/preempt.h>
#include <linux/sched.h>
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

#ifdef BENCH_ALIGN64
#define BENCH_ALIGN_ATTR __attribute__((aligned(64)))
#else
#define BENCH_ALIGN_ATTR
#endif

typedef u64 (*bench_fn_t)(u64);
typedef u64 (*body_fn_t)(u64);

static unsigned long iterations = 1000000;
static int repeats = 31;
static int run_id;
static int cpu = -1;
static char *build = "unknown";
static char *fence_mode = "unknown";

module_param(iterations, ulong, 0444);
MODULE_PARM_DESC(iterations, "inner-loop iterations per timed sample");
module_param(repeats, int, 0444);
MODULE_PARM_DESC(repeats, "paired direct/pgot repetitions");
module_param(run_id, int, 0444);
MODULE_PARM_DESC(run_id, "raw sample run id");
module_param(cpu, int, 0444);
MODULE_PARM_DESC(cpu, "optional CPU affinity for module init thread");
module_param(build, charp, 0444);
MODULE_PARM_DESC(build, "build label: no_retpoline or retpoline");
module_param(fence_mode, charp, 0444);
MODULE_PARM_DESC(fence_mode, "fence label: unfenced or fenced");

static bench_fn_t pgot_func_table[11] __aligned(64);
static volatile u64 sink_u64;

static inline void compiler_barrier(void)
{
	asm volatile("" ::: "memory");
}

static inline u64 rol64_local(u64 x, unsigned int n)
{
	return (x << n) | (x >> (64 - n));
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

#ifdef BENCH_FENCE_AFTER_CALL
static inline void post_call_serialize(void)
{
	asm volatile("lfence" ::: "memory");
}
#else
static inline void post_call_serialize(void)
{
	compiler_barrier();
}
#endif

#ifdef BENCH_FENCE_BEFORE_CALL
static inline void pre_call_serialize(void)
{
	asm volatile("lfence" ::: "memory");
}
#else
static inline void pre_call_serialize(void)
{
	compiler_barrier();
}
#endif

static inline void iteration_serialize(void)
{
#ifdef BENCH_FENCE_ITERATION
	asm volatile("lfence" ::: "memory");
#else
	compiler_barrier();
#endif
}

static inline void black_box_u64(u64 v)
{
	sink_u64 ^= v;
	compiler_barrier();
}

#define WORK_UNIT() do { \
	x = x * 0x9e3779b185ebca87ULL + 0x165667b19e3779f9ULL; \
	x ^= rol64_local(x, 13); \
	x += 0xd6e8feb86659fd93ULL; \
	x ^= x >> 17; \
} while (0)

#define W0()
#define W1() WORK_UNIT()
#define W2() W1(); W1()
#define W3() W2(); W1()
#define W4() W2(); W2()
#define W5() W4(); W1()
#define W6() W4(); W2()
#define W8() W4(); W4()
#define W16() W8(); W8()
#define W32() W16(); W16()
#define W64() W32(); W32()

#define DEFINE_TARGET(work, steps) \
static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 target_work_##work(u64 x) \
{ \
	steps; \
	asm volatile("" : "+r"(x) :: "memory"); \
	return x; \
}

DEFINE_TARGET(0, W0())
DEFINE_TARGET(1, W1())
DEFINE_TARGET(2, W2())
DEFINE_TARGET(3, W3())
DEFINE_TARGET(4, W4())
DEFINE_TARGET(5, W5())
DEFINE_TARGET(6, W6())
DEFINE_TARGET(8, W8())
DEFINE_TARGET(16, W16())
DEFINE_TARGET(32, W32())
DEFINE_TARGET(64, W64())

static void init_func_table(void)
{
	pgot_func_table[0] = target_work_0;
	pgot_func_table[1] = target_work_1;
	pgot_func_table[2] = target_work_2;
	pgot_func_table[3] = target_work_3;
	pgot_func_table[4] = target_work_4;
	pgot_func_table[5] = target_work_5;
	pgot_func_table[6] = target_work_6;
	pgot_func_table[7] = target_work_8;
	pgot_func_table[8] = target_work_16;
	pgot_func_table[9] = target_work_32;
	pgot_func_table[10] = target_work_64;
	compiler_barrier();
}

#define CALL_DIRECT(work) do { \
	x = target_work_##work(x); \
} while (0)

#define CALL_PGOT(idx) do { \
	bench_fn_t volatile *slot__ = pgot_func_table; \
	bench_fn_t f__ = slot__[idx]; \
	x = f__(x); \
} while (0)

#define END_ITER() do { \
	asm volatile("" : "+r"(x) :: "memory"); \
	iteration_serialize(); \
} while (0)

#define DEFINE_NONE_BODY(kind) \
static noinline BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_##kind##_none_0(u64 iters) \
{ \
	u64 x = 0x123456789abcdef0ULL; \
	u64 it; \
	for (it = 0; it < iters; it++) { \
		pre_call_serialize(); \
		CALL_##kind(0); \
		post_call_serialize(); \
		END_ITER(); \
	} \
	return x; \
}

#define DEFINE_BEFORE_BODY(kind, work, idx, steps) \
static noinline BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_##kind##_before_##work(u64 iters) \
{ \
	u64 x = 0x123456789abcdef0ULL; \
	u64 it; \
	for (it = 0; it < iters; it++) { \
		steps; \
		pre_call_serialize(); \
		CALL_##kind(0); \
		post_call_serialize(); \
		END_ITER(); \
	} \
	return x; \
}

#define DEFINE_AFTER_BODY(kind, work, idx, steps) \
static noinline BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_##kind##_after_##work(u64 iters) \
{ \
	u64 x = 0x123456789abcdef0ULL; \
	u64 it; \
	for (it = 0; it < iters; it++) { \
		pre_call_serialize(); \
		CALL_##kind(0); \
		post_call_serialize(); \
		steps; \
		END_ITER(); \
	} \
	return x; \
}

#define DEFINE_INSIDE_DIRECT_BODY(work) \
static noinline BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_DIRECT_inside_##work(u64 iters) \
{ \
	u64 x = 0x123456789abcdef0ULL; \
	u64 it; \
	for (it = 0; it < iters; it++) { \
		pre_call_serialize(); \
		CALL_DIRECT(work); \
		post_call_serialize(); \
		END_ITER(); \
	} \
	return x; \
}

#define DEFINE_INSIDE_PGOT_BODY(work, idx) \
static noinline BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_PGOT_inside_##work(u64 iters) \
{ \
	u64 x = 0x123456789abcdef0ULL; \
	u64 it; \
	for (it = 0; it < iters; it++) { \
		pre_call_serialize(); \
		CALL_PGOT(idx); \
		post_call_serialize(); \
		END_ITER(); \
	} \
	return x; \
}

DEFINE_NONE_BODY(DIRECT)
DEFINE_NONE_BODY(PGOT)

#define DEFINE_WORK_ONLY_BODY(work, steps) \
static noinline BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_WORK_only_##work(u64 iters) \
{ \
	u64 x = 0x123456789abcdef0ULL; \
	u64 it; \
	for (it = 0; it < iters; it++) { \
		steps; \
		END_ITER(); \
	} \
	return x; \
}

#define DEFINE_PLACEMENT_WORK(work, idx, steps) \
	DEFINE_WORK_ONLY_BODY(work, steps) \
	DEFINE_BEFORE_BODY(DIRECT, work, idx, steps) \
	DEFINE_BEFORE_BODY(PGOT, work, idx, steps) \
	DEFINE_AFTER_BODY(DIRECT, work, idx, steps) \
	DEFINE_AFTER_BODY(PGOT, work, idx, steps) \
	DEFINE_INSIDE_DIRECT_BODY(work) \
	DEFINE_INSIDE_PGOT_BODY(work, idx)

DEFINE_PLACEMENT_WORK(0, 0, W0())
DEFINE_PLACEMENT_WORK(1, 1, W1())
DEFINE_PLACEMENT_WORK(2, 2, W2())
DEFINE_PLACEMENT_WORK(3, 3, W3())
DEFINE_PLACEMENT_WORK(4, 4, W4())
DEFINE_PLACEMENT_WORK(5, 5, W5())
DEFINE_PLACEMENT_WORK(6, 6, W6())
DEFINE_PLACEMENT_WORK(8, 7, W8())
DEFINE_PLACEMENT_WORK(16, 8, W16())
DEFINE_PLACEMENT_WORK(32, 9, W32())
DEFINE_PLACEMENT_WORK(64, 10, W64())

static body_fn_t select_body(const char *kind, const char *placement, int workload)
{
	bool pgot = !strcmp(kind, "pgot");

	if (!strcmp(placement, "none") && workload == 0)
		return pgot ? body_PGOT_none_0 : body_DIRECT_none_0;

	if (!strcmp(placement, "work_only")) {
		switch (workload) {
		case 0: return body_WORK_only_0;
		case 1: return body_WORK_only_1;
		case 2: return body_WORK_only_2;
		case 3: return body_WORK_only_3;
		case 4: return body_WORK_only_4;
		case 5: return body_WORK_only_5;
		case 6: return body_WORK_only_6;
		case 8: return body_WORK_only_8;
		case 16: return body_WORK_only_16;
		case 32: return body_WORK_only_32;
		case 64: return body_WORK_only_64;
		default: return NULL;
		}
	}

#define CASE_PLACE(place, work) \
	if (!strcmp(placement, #place) && workload == work) \
		return pgot ? body_PGOT_##place##_##work : body_DIRECT_##place##_##work

	CASE_PLACE(before, 0);
	CASE_PLACE(before, 1);
	CASE_PLACE(before, 2);
	CASE_PLACE(before, 3);
	CASE_PLACE(before, 4);
	CASE_PLACE(before, 5);
	CASE_PLACE(before, 6);
	CASE_PLACE(before, 8);
	CASE_PLACE(before, 16);
	CASE_PLACE(before, 32);
	CASE_PLACE(before, 64);
	CASE_PLACE(after, 0);
	CASE_PLACE(after, 1);
	CASE_PLACE(after, 2);
	CASE_PLACE(after, 3);
	CASE_PLACE(after, 4);
	CASE_PLACE(after, 5);
	CASE_PLACE(after, 6);
	CASE_PLACE(after, 8);
	CASE_PLACE(after, 16);
	CASE_PLACE(after, 32);
	CASE_PLACE(after, 64);
	CASE_PLACE(inside, 0);
	CASE_PLACE(inside, 1);
	CASE_PLACE(inside, 2);
	CASE_PLACE(inside, 3);
	CASE_PLACE(inside, 4);
	CASE_PLACE(inside, 5);
	CASE_PLACE(inside, 6);
	CASE_PLACE(inside, 8);
	CASE_PLACE(inside, 16);
	CASE_PLACE(inside, 32);
	CASE_PLACE(inside, 64);

#undef CASE_PLACE
	return NULL;
}

static s64 measure_x1000(body_fn_t fn, u64 iters)
{
	u64 start, end, v;

	preempt_disable();
	start = rdtsc_start();
	v = fn(iters);
	end = rdtsc_end();
	preempt_enable();

	black_box_u64(v);
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

static void print_raw_line(const char *placement, int workload, int repeat,
			   s64 direct, s64 pgot)
{
	char direct_buf[32];
	char pgot_buf[32];
	char delta_buf[32];

	scaled_to_buf(direct_buf, sizeof(direct_buf), direct);
	scaled_to_buf(pgot_buf, sizeof(pgot_buf), pgot);
	scaled_to_buf(delta_buf, sizeof(delta_buf), pgot - direct);

	pr_info("PGOT_L2FP_RAW,layer2_func_placement,%s,%s,%d,%s,%d,%d,%lu,%s,%s,%s\n",
		build, fence_mode, run_id, placement, workload, repeat,
		iterations, direct_buf, pgot_buf, delta_buf);
}

static int run_case(const char *placement, int workload)
{
	body_fn_t direct_fn = select_body("direct", placement, workload);
	body_fn_t pgot_fn = select_body("pgot", placement, workload);
	int r;

	if (!direct_fn || !pgot_fn)
		return -EINVAL;

	(void)measure_x1000(direct_fn, iterations / 10 + 1);
	(void)measure_x1000(pgot_fn, iterations / 10 + 1);

	for (r = 0; r < repeats; r++) {
		s64 direct, pgot;

		if (r & 1) {
			pgot = measure_x1000(pgot_fn, iterations);
			direct = measure_x1000(direct_fn, iterations);
		} else {
			direct = measure_x1000(direct_fn, iterations);
			pgot = measure_x1000(pgot_fn, iterations);
		}
		print_raw_line(placement, workload, r, direct, pgot);
	}
	return 0;
}

static int run_all_cases(void)
{
	static const int workloads[] = {0, 1, 2, 3, 4, 5, 6, 8, 16, 32, 64};
	static const char *placements[] = {"work_only", "before", "inside", "after"};
	int p, w, ret;

	ret = run_case("none", 0);
	if (ret)
		return ret;

	for (p = 0; p < ARRAY_SIZE(placements); p++) {
		for (w = 0; w < ARRAY_SIZE(workloads); w++) {
			ret = run_case(placements[p], workloads[w]);
			if (ret)
				return ret;
		}
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

static int __init pgot_l2fp_init(void)
{
	int ret;

	if (!iterations || repeats <= 0)
		return -EINVAL;

	ret = pin_current_cpu();
	if (ret) {
		pr_err("PGOT_L2FP_ERROR,cpu_pin_failed,cpu=%d,ret=%d\n", cpu, ret);
		return ret;
	}

	init_func_table();
	pr_info("PGOT_L2FP_BEGIN,build=%s,fence=%s,run_id=%d,iterations=%lu,repeats=%d,cpu=%d,event=1\n",
		build, fence_mode, run_id, iterations, repeats, cpu);
	ret = run_all_cases();
	pr_info("PGOT_L2FP_DONE,build=%s,fence=%s,run_id=%d,ret=%d\n",
		build, fence_mode, run_id, ret);
	return ret;
}

static void __exit pgot_l2fp_exit(void)
{
	pr_info("PGOT_L2FP_EXIT\n");
}

module_init(pgot_l2fp_init);
module_exit(pgot_l2fp_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("pgot microbench");
MODULE_DESCRIPTION("Layer2 func-pgot placement sensitivity benchmark");
