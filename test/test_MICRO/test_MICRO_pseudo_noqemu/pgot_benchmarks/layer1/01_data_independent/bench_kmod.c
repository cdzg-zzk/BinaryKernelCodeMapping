#include <linux/cpumask.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/preempt.h>
#include <linux/sched.h>
#include <linux/slab.h>
#include <linux/math64.h>
#include <linux/types.h>

#define PGOT_DATA_SLOTS 32
#define SCALE 1000ULL

static unsigned long iterations = 1000000;
static int repeats = 31;
static int run_id;
static int cpu = -1;

module_param(iterations, ulong, 0444);
MODULE_PARM_DESC(iterations, "inner-loop iterations per timed sample");
module_param(repeats, int, 0444);
MODULE_PARM_DESC(repeats, "paired direct/pgot repetitions");
module_param(run_id, int, 0444);
MODULE_PARM_DESC(run_id, "raw sample run id");
module_param(cpu, int, 0444);
MODULE_PARM_DESC(cpu, "optional CPU affinity for the module init thread");

static u64 direct_values[PGOT_DATA_SLOTS] __aligned(64);
static u64 *pgot_data_table[PGOT_DATA_SLOTS] __aligned(64);
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

static inline void black_box_u64(u64 v)
{
	sink_u64 ^= v;
	compiler_barrier();
}

static void init_data_tables(void)
{
	int i;

	for (i = 0; i < PGOT_DATA_SLOTS; i++) {
		direct_values[i] = 0x100000001b3ULL + (u64)i * 97ULL;
		pgot_data_table[i] = &direct_values[i];
	}
	compiler_barrier();
}

#define LOAD_DIRECT(i) do { \
	volatile u64 *p__ = &direct_values[(i) & (PGOT_DATA_SLOTS - 1)]; \
	acc += *p__; \
} while (0)

#define LOAD_PGOT(i) do { \
	u64 * volatile *slot__ = pgot_data_table; \
	volatile u64 *p__ = slot__[(i) & (PGOT_DATA_SLOTS - 1)]; \
	acc += *p__; \
} while (0)

#define LOAD_DIRECT_BARRIERED(i) do { \
	volatile u64 *p__ = &direct_values[(i) & (PGOT_DATA_SLOTS - 1)]; \
	acc += *p__; \
	asm volatile("" : "+r"(acc) :: "memory"); \
} while (0)

#define LOAD_PGOT_BARRIERED(i) do { \
	u64 * volatile *slot__ = pgot_data_table; \
	volatile u64 *p__ = slot__[(i) & (PGOT_DATA_SLOTS - 1)]; \
	acc += *p__; \
	asm volatile("" : "+r"(acc) :: "memory"); \
} while (0)

#define EMPTY_BARRIER() do { \
	asm volatile("" : "+r"(acc) :: "memory"); \
} while (0)

#define DEFINE_EMPTY_BODY(name, loads) \
static noinline u64 body_##name(u64 iters) \
{ \
	u64 acc = 0xabcdef1234567890ULL; \
	u64 it; \
	for (it = 0; it < iters; it++) { \
		loads \
		asm volatile("" : "+r"(acc) :: "memory"); \
	} \
	return acc; \
}

#define DEFINE_BODY(kind, events, loads) \
static noinline u64 body_##kind##_##events(u64 iters) \
{ \
	u64 acc = 0xabcdef1234567890ULL; \
	u64 it; \
	for (it = 0; it < iters; it++) { \
		loads \
		asm volatile("" : "+r"(acc) :: "memory"); \
	} \
	return acc; \
}

#define LOADS_DIRECT_1  LOAD_DIRECT(0);
#define LOADS_DIRECT_2  LOADS_DIRECT_1 LOAD_DIRECT(1);
#define LOADS_DIRECT_4  LOADS_DIRECT_2 LOAD_DIRECT(2); LOAD_DIRECT(3);
#define LOADS_DIRECT_6  LOADS_DIRECT_4 LOAD_DIRECT(4); LOAD_DIRECT(5);
#define LOADS_DIRECT_8  LOADS_DIRECT_6 LOAD_DIRECT(6); LOAD_DIRECT(7);
#define LOADS_DIRECT_10 LOADS_DIRECT_8 LOAD_DIRECT(8); LOAD_DIRECT(9);
#define LOADS_DIRECT_12 LOADS_DIRECT_10 LOAD_DIRECT(10); LOAD_DIRECT(11);
#define LOADS_DIRECT_14 LOADS_DIRECT_12 LOAD_DIRECT(12); LOAD_DIRECT(13);
#define LOADS_DIRECT_16 LOADS_DIRECT_14 LOAD_DIRECT(14); LOAD_DIRECT(15);
#define LOADS_DIRECT_18 LOADS_DIRECT_16 LOAD_DIRECT(16); LOAD_DIRECT(17);

#define LOADS_PGOT_1  LOAD_PGOT(0);
#define LOADS_PGOT_2  LOADS_PGOT_1 LOAD_PGOT(1);
#define LOADS_PGOT_4  LOADS_PGOT_2 LOAD_PGOT(2); LOAD_PGOT(3);
#define LOADS_PGOT_6  LOADS_PGOT_4 LOAD_PGOT(4); LOAD_PGOT(5);
#define LOADS_PGOT_8  LOADS_PGOT_6 LOAD_PGOT(6); LOAD_PGOT(7);
#define LOADS_PGOT_10 LOADS_PGOT_8 LOAD_PGOT(8); LOAD_PGOT(9);
#define LOADS_PGOT_12 LOADS_PGOT_10 LOAD_PGOT(10); LOAD_PGOT(11);
#define LOADS_PGOT_14 LOADS_PGOT_12 LOAD_PGOT(12); LOAD_PGOT(13);
#define LOADS_PGOT_16 LOADS_PGOT_14 LOAD_PGOT(14); LOAD_PGOT(15);
#define LOADS_PGOT_18 LOADS_PGOT_16 LOAD_PGOT(16); LOAD_PGOT(17);

#define LOADS_DIRECT_BARRIERED_1  LOAD_DIRECT_BARRIERED(0);
#define LOADS_DIRECT_BARRIERED_2  LOADS_DIRECT_BARRIERED_1 LOAD_DIRECT_BARRIERED(1);
#define LOADS_DIRECT_BARRIERED_4  LOADS_DIRECT_BARRIERED_2 LOAD_DIRECT_BARRIERED(2); LOAD_DIRECT_BARRIERED(3);
#define LOADS_DIRECT_BARRIERED_6  LOADS_DIRECT_BARRIERED_4 LOAD_DIRECT_BARRIERED(4); LOAD_DIRECT_BARRIERED(5);
#define LOADS_DIRECT_BARRIERED_8  LOADS_DIRECT_BARRIERED_6 LOAD_DIRECT_BARRIERED(6); LOAD_DIRECT_BARRIERED(7);
#define LOADS_DIRECT_BARRIERED_10 LOADS_DIRECT_BARRIERED_8 LOAD_DIRECT_BARRIERED(8); LOAD_DIRECT_BARRIERED(9);
#define LOADS_DIRECT_BARRIERED_12 LOADS_DIRECT_BARRIERED_10 LOAD_DIRECT_BARRIERED(10); LOAD_DIRECT_BARRIERED(11);
#define LOADS_DIRECT_BARRIERED_14 LOADS_DIRECT_BARRIERED_12 LOAD_DIRECT_BARRIERED(12); LOAD_DIRECT_BARRIERED(13);
#define LOADS_DIRECT_BARRIERED_16 LOADS_DIRECT_BARRIERED_14 LOAD_DIRECT_BARRIERED(14); LOAD_DIRECT_BARRIERED(15);
#define LOADS_DIRECT_BARRIERED_18 LOADS_DIRECT_BARRIERED_16 LOAD_DIRECT_BARRIERED(16); LOAD_DIRECT_BARRIERED(17);

#define LOADS_PGOT_BARRIERED_1  LOAD_PGOT_BARRIERED(0);
#define LOADS_PGOT_BARRIERED_2  LOADS_PGOT_BARRIERED_1 LOAD_PGOT_BARRIERED(1);
#define LOADS_PGOT_BARRIERED_4  LOADS_PGOT_BARRIERED_2 LOAD_PGOT_BARRIERED(2); LOAD_PGOT_BARRIERED(3);
#define LOADS_PGOT_BARRIERED_6  LOADS_PGOT_BARRIERED_4 LOAD_PGOT_BARRIERED(4); LOAD_PGOT_BARRIERED(5);
#define LOADS_PGOT_BARRIERED_8  LOADS_PGOT_BARRIERED_6 LOAD_PGOT_BARRIERED(6); LOAD_PGOT_BARRIERED(7);
#define LOADS_PGOT_BARRIERED_10 LOADS_PGOT_BARRIERED_8 LOAD_PGOT_BARRIERED(8); LOAD_PGOT_BARRIERED(9);
#define LOADS_PGOT_BARRIERED_12 LOADS_PGOT_BARRIERED_10 LOAD_PGOT_BARRIERED(10); LOAD_PGOT_BARRIERED(11);
#define LOADS_PGOT_BARRIERED_14 LOADS_PGOT_BARRIERED_12 LOAD_PGOT_BARRIERED(12); LOAD_PGOT_BARRIERED(13);
#define LOADS_PGOT_BARRIERED_16 LOADS_PGOT_BARRIERED_14 LOAD_PGOT_BARRIERED(14); LOAD_PGOT_BARRIERED(15);
#define LOADS_PGOT_BARRIERED_18 LOADS_PGOT_BARRIERED_16 LOAD_PGOT_BARRIERED(16); LOAD_PGOT_BARRIERED(17);

#define LOADS_EMPTY_BARRIERED_1  EMPTY_BARRIER();
#define LOADS_EMPTY_BARRIERED_2  LOADS_EMPTY_BARRIERED_1 EMPTY_BARRIER();
#define LOADS_EMPTY_BARRIERED_4  LOADS_EMPTY_BARRIERED_2 EMPTY_BARRIER(); EMPTY_BARRIER();
#define LOADS_EMPTY_BARRIERED_6  LOADS_EMPTY_BARRIERED_4 EMPTY_BARRIER(); EMPTY_BARRIER();
#define LOADS_EMPTY_BARRIERED_8  LOADS_EMPTY_BARRIERED_6 EMPTY_BARRIER(); EMPTY_BARRIER();
#define LOADS_EMPTY_BARRIERED_10 LOADS_EMPTY_BARRIERED_8 EMPTY_BARRIER(); EMPTY_BARRIER();
#define LOADS_EMPTY_BARRIERED_12 LOADS_EMPTY_BARRIERED_10 EMPTY_BARRIER(); EMPTY_BARRIER();
#define LOADS_EMPTY_BARRIERED_14 LOADS_EMPTY_BARRIERED_12 EMPTY_BARRIER(); EMPTY_BARRIER();
#define LOADS_EMPTY_BARRIERED_16 LOADS_EMPTY_BARRIERED_14 EMPTY_BARRIER(); EMPTY_BARRIER();
#define LOADS_EMPTY_BARRIERED_18 LOADS_EMPTY_BARRIERED_16 EMPTY_BARRIER(); EMPTY_BARRIER();

DEFINE_EMPTY_BODY(empty_scheduled, )
DEFINE_EMPTY_BODY(empty_barriered_1, LOADS_EMPTY_BARRIERED_1)
DEFINE_EMPTY_BODY(empty_barriered_2, LOADS_EMPTY_BARRIERED_2)
DEFINE_EMPTY_BODY(empty_barriered_4, LOADS_EMPTY_BARRIERED_4)
DEFINE_EMPTY_BODY(empty_barriered_6, LOADS_EMPTY_BARRIERED_6)
DEFINE_EMPTY_BODY(empty_barriered_8, LOADS_EMPTY_BARRIERED_8)
DEFINE_EMPTY_BODY(empty_barriered_10, LOADS_EMPTY_BARRIERED_10)
DEFINE_EMPTY_BODY(empty_barriered_12, LOADS_EMPTY_BARRIERED_12)
DEFINE_EMPTY_BODY(empty_barriered_14, LOADS_EMPTY_BARRIERED_14)
DEFINE_EMPTY_BODY(empty_barriered_16, LOADS_EMPTY_BARRIERED_16)
DEFINE_EMPTY_BODY(empty_barriered_18, LOADS_EMPTY_BARRIERED_18)

DEFINE_BODY(direct, 1, LOADS_DIRECT_1)
DEFINE_BODY(direct, 2, LOADS_DIRECT_2)
DEFINE_BODY(direct, 4, LOADS_DIRECT_4)
DEFINE_BODY(direct, 6, LOADS_DIRECT_6)
DEFINE_BODY(direct, 8, LOADS_DIRECT_8)
DEFINE_BODY(direct, 10, LOADS_DIRECT_10)
DEFINE_BODY(direct, 12, LOADS_DIRECT_12)
DEFINE_BODY(direct, 14, LOADS_DIRECT_14)
DEFINE_BODY(direct, 16, LOADS_DIRECT_16)
DEFINE_BODY(direct, 18, LOADS_DIRECT_18)

DEFINE_BODY(pgot, 1, LOADS_PGOT_1)
DEFINE_BODY(pgot, 2, LOADS_PGOT_2)
DEFINE_BODY(pgot, 4, LOADS_PGOT_4)
DEFINE_BODY(pgot, 6, LOADS_PGOT_6)
DEFINE_BODY(pgot, 8, LOADS_PGOT_8)
DEFINE_BODY(pgot, 10, LOADS_PGOT_10)
DEFINE_BODY(pgot, 12, LOADS_PGOT_12)
DEFINE_BODY(pgot, 14, LOADS_PGOT_14)
DEFINE_BODY(pgot, 16, LOADS_PGOT_16)
DEFINE_BODY(pgot, 18, LOADS_PGOT_18)

DEFINE_BODY(direct_barriered, 1, LOADS_DIRECT_BARRIERED_1)
DEFINE_BODY(direct_barriered, 2, LOADS_DIRECT_BARRIERED_2)
DEFINE_BODY(direct_barriered, 4, LOADS_DIRECT_BARRIERED_4)
DEFINE_BODY(direct_barriered, 6, LOADS_DIRECT_BARRIERED_6)
DEFINE_BODY(direct_barriered, 8, LOADS_DIRECT_BARRIERED_8)
DEFINE_BODY(direct_barriered, 10, LOADS_DIRECT_BARRIERED_10)
DEFINE_BODY(direct_barriered, 12, LOADS_DIRECT_BARRIERED_12)
DEFINE_BODY(direct_barriered, 14, LOADS_DIRECT_BARRIERED_14)
DEFINE_BODY(direct_barriered, 16, LOADS_DIRECT_BARRIERED_16)
DEFINE_BODY(direct_barriered, 18, LOADS_DIRECT_BARRIERED_18)

DEFINE_BODY(pgot_barriered, 1, LOADS_PGOT_BARRIERED_1)
DEFINE_BODY(pgot_barriered, 2, LOADS_PGOT_BARRIERED_2)
DEFINE_BODY(pgot_barriered, 4, LOADS_PGOT_BARRIERED_4)
DEFINE_BODY(pgot_barriered, 6, LOADS_PGOT_BARRIERED_6)
DEFINE_BODY(pgot_barriered, 8, LOADS_PGOT_BARRIERED_8)
DEFINE_BODY(pgot_barriered, 10, LOADS_PGOT_BARRIERED_10)
DEFINE_BODY(pgot_barriered, 12, LOADS_PGOT_BARRIERED_12)
DEFINE_BODY(pgot_barriered, 14, LOADS_PGOT_BARRIERED_14)
DEFINE_BODY(pgot_barriered, 16, LOADS_PGOT_BARRIERED_16)
DEFINE_BODY(pgot_barriered, 18, LOADS_PGOT_BARRIERED_18)

typedef u64 (*body_fn_t)(u64);

static body_fn_t select_empty_body(bool barriered, int events)
{
	if (!barriered)
		return body_empty_scheduled;

	switch (events) {
	case 1: return body_empty_barriered_1;
	case 2: return body_empty_barriered_2;
	case 4: return body_empty_barriered_4;
	case 6: return body_empty_barriered_6;
	case 8: return body_empty_barriered_8;
	case 10: return body_empty_barriered_10;
	case 12: return body_empty_barriered_12;
	case 14: return body_empty_barriered_14;
	case 16: return body_empty_barriered_16;
	case 18: return body_empty_barriered_18;
	default: return NULL;
	}
}

static body_fn_t select_body(bool barriered, bool pgot, int events)
{
	if (!barriered && !pgot) {
		switch (events) {
		case 1: return body_direct_1;
		case 2: return body_direct_2;
		case 4: return body_direct_4;
		case 6: return body_direct_6;
		case 8: return body_direct_8;
		case 10: return body_direct_10;
		case 12: return body_direct_12;
		case 14: return body_direct_14;
		case 16: return body_direct_16;
		case 18: return body_direct_18;
		default: return NULL;
		}
	}

	if (!barriered && pgot) {
		switch (events) {
		case 1: return body_pgot_1;
		case 2: return body_pgot_2;
		case 4: return body_pgot_4;
		case 6: return body_pgot_6;
		case 8: return body_pgot_8;
		case 10: return body_pgot_10;
		case 12: return body_pgot_12;
		case 14: return body_pgot_14;
		case 16: return body_pgot_16;
		case 18: return body_pgot_18;
		default: return NULL;
		}
	}

	if (barriered && !pgot) {
		switch (events) {
		case 1: return body_direct_barriered_1;
		case 2: return body_direct_barriered_2;
		case 4: return body_direct_barriered_4;
		case 6: return body_direct_barriered_6;
		case 8: return body_direct_barriered_8;
		case 10: return body_direct_barriered_10;
		case 12: return body_direct_barriered_12;
		case 14: return body_direct_barriered_14;
		case 16: return body_direct_barriered_16;
		case 18: return body_direct_barriered_18;
		default: return NULL;
		}
	}

	switch (events) {
	case 1: return body_pgot_barriered_1;
	case 2: return body_pgot_barriered_2;
	case 4: return body_pgot_barriered_4;
	case 6: return body_pgot_barriered_6;
	case 8: return body_pgot_barriered_8;
	case 10: return body_pgot_barriered_10;
	case 12: return body_pgot_barriered_12;
	case 14: return body_pgot_barriered_14;
	case 16: return body_pgot_barriered_16;
	case 18: return body_pgot_barriered_18;
	default: return NULL;
	}
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

static void print_raw_line(const char *variant, int events, int repeat,
			   s64 empty, s64 direct, s64 pgot)
{
	s64 delta = pgot - direct;
	s64 delta_per_event = div_s64(delta, events);
	char empty_buf[32];
	char direct_buf[32];
	char pgot_buf[32];
	char delta_buf[32];
	char delta_per_event_buf[32];

	scaled_to_buf(empty_buf, sizeof(empty_buf), empty);
	scaled_to_buf(direct_buf, sizeof(direct_buf), direct);
	scaled_to_buf(pgot_buf, sizeof(pgot_buf), pgot);
	scaled_to_buf(delta_buf, sizeof(delta_buf), delta);
	scaled_to_buf(delta_per_event_buf, sizeof(delta_per_event_buf), delta_per_event);

	pr_info("PGOT_L1DI_RAW,layer1_data_independent,%s,%d,%d,%d,%lu,%s,%s,%s,%s,%s\n",
		variant, run_id, events, repeat, iterations, empty_buf, direct_buf,
		pgot_buf, delta_buf, delta_per_event_buf);
}

static int run_event(const char *variant, bool barriered, int events)
{
	body_fn_t empty_fn = select_empty_body(barriered, events);
	body_fn_t direct_fn = select_body(barriered, false, events);
	body_fn_t pgot_fn = select_body(barriered, true, events);
	int r;

	if (!empty_fn || !direct_fn || !pgot_fn)
		return -EINVAL;

	(void)measure_x1000(empty_fn, iterations / 10 + 1);
	(void)measure_x1000(direct_fn, iterations / 10 + 1);
	(void)measure_x1000(pgot_fn, iterations / 10 + 1);

	for (r = 0; r < repeats; r++) {
		s64 empty, direct, pgot;

		switch (r % 3) {
		case 0:
			empty = measure_x1000(empty_fn, iterations);
			direct = measure_x1000(direct_fn, iterations);
			pgot = measure_x1000(pgot_fn, iterations);
			break;
		case 1:
			pgot = measure_x1000(pgot_fn, iterations);
			empty = measure_x1000(empty_fn, iterations);
			direct = measure_x1000(direct_fn, iterations);
			break;
		default:
			direct = measure_x1000(direct_fn, iterations);
			pgot = measure_x1000(pgot_fn, iterations);
			empty = measure_x1000(empty_fn, iterations);
			break;
		}
		print_raw_line(variant, events, r, empty, direct, pgot);
	}
	return 0;
}

static int run_variant(const char *variant, bool barriered)
{
	static const int events[] = {1, 2, 4, 6, 8, 10, 12, 14, 16, 18};
	int i, ret;

	for (i = 0; i < ARRAY_SIZE(events); i++) {
		ret = run_event(variant, barriered, events[i]);
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

static int __init pgot_l1di_init(void)
{
	int ret;

	if (!iterations || repeats <= 0)
		return -EINVAL;

	ret = pin_current_cpu();
	if (ret) {
		pr_err("PGOT_L1DI_ERROR,cpu_pin_failed,cpu=%d,ret=%d\n", cpu, ret);
		return ret;
	}

	init_data_tables();
	pr_info("PGOT_L1DI_BEGIN,run_id=%d,iterations=%lu,repeats=%d,cpu=%d,sample_order=interleave,variants=scheduled|barriered\n",
		run_id, iterations, repeats, cpu);

	ret = run_variant("scheduled", false);
	if (ret)
		return ret;
	ret = run_variant("barriered", true);
	if (ret)
		return ret;

	pr_info("PGOT_L1DI_END,run_id=%d\n", run_id);
	return 0;
}

static void __exit pgot_l1di_exit(void)
{
	pr_info("PGOT_L1DI_EXIT,run_id=%d\n", run_id);
}

module_init(pgot_l1di_init);
module_exit(pgot_l1di_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("pgot_benchmarks");
MODULE_DESCRIPTION("Layer1 data-pgot independent primitive benchmark in kernel mode");
