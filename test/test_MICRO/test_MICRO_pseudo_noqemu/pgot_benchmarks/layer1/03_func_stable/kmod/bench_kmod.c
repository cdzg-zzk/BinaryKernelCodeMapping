#include <linux/cpumask.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/moduleparam.h>
#include <linux/preempt.h>
#include <linux/sched.h>
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

static unsigned long iterations = 1000000;
static int repeats = 31;
static int run_id;
static int cpu = -1;
static char *build = "unknown";

module_param(iterations, ulong, 0444);
MODULE_PARM_DESC(iterations, "inner-loop iterations per timed sample");
module_param(repeats, int, 0444);
MODULE_PARM_DESC(repeats, "paired empty/direct/pgot repetitions");
module_param(run_id, int, 0444);
MODULE_PARM_DESC(run_id, "raw sample run id");
module_param(cpu, int, 0444);
MODULE_PARM_DESC(cpu, "optional CPU affinity for the module init thread");
module_param(build, charp, 0444);
MODULE_PARM_DESC(build, "build label: no_retpoline or retpoline");

#ifdef BENCH_ASM_MATCHED
bench_fn_t pgot_func_table[1] __aligned(64);
#else
static bench_fn_t pgot_func_table[1] __aligned(64);
#endif
static volatile u64 sink_u64;

static inline void compiler_barrier(void)
{
	asm volatile("" ::: "memory");
}

static inline void event_fence(void)
{
#ifdef BENCH_EVENT_LFENCE
	asm volatile("lfence" ::: "memory");
#endif
}

static noinline noipa BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 target_0(u64 x)
{
#ifdef BENCH_TARGET_EMPTY
	asm volatile("" : "+r"(x) :: "memory");
	return x;
#else
	return (x * 3ULL) + 1ULL;
#endif
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

static void init_func_table(void)
{
	pgot_func_table[0] = target_0;
	compiler_barrier();
}

#define CALL_DIRECT() do { \
	event_fence(); \
	x = target_0(x); \
	event_fence(); \
} while (0)

#define CALL_CACHED_INDIRECT() do { \
	event_fence(); \
	x = f(x); \
	event_fence(); \
} while (0)

#define CALL_SLOT_DIRECT() do { \
	bench_fn_t volatile *slot__ = pgot_func_table; \
	bench_fn_t f__ = slot__[0]; \
	asm volatile("" : "+r"(f__) :: "memory"); \
	event_fence(); \
	x = target_0(x); \
	event_fence(); \
} while (0)

#define CALL_PGOT() do { \
	bench_fn_t volatile *slot__ = pgot_func_table; \
	bench_fn_t f__ = slot__[0]; \
	event_fence(); \
	x = f__(x); \
	event_fence(); \
} while (0)

#define EMPTY_BARRIER() do { \
	asm volatile("" : "+r"(x) :: "memory"); \
} while (0)

#define DEFINE_EMPTY_BODY(name, steps) \
static noinline BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_##name(u64 iters) \
{ \
	u64 x = 0x123456789abcdef0ULL; \
	u64 it; \
	for (it = 0; it < iters; it++) { \
		steps \
		asm volatile("" : "+r"(x) :: "memory"); \
	} \
	return x; \
}

#define DEFINE_BODY(kind, events, steps) \
static noinline BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_##kind##_##events(u64 iters) \
{ \
	u64 x = 0x123456789abcdef0ULL; \
	u64 it; \
	for (it = 0; it < iters; it++) { \
		steps \
		asm volatile("" : "+r"(x) :: "memory"); \
	} \
	return x; \
}

#define DEFINE_CACHED_BODY(events, steps) \
static noinline BENCH_NOTRACE_ATTR BENCH_ALIGN_ATTR u64 body_cached_##events(u64 iters) \
{ \
	bench_fn_t volatile *slot = pgot_func_table; \
	bench_fn_t f = slot[0]; \
	u64 x = 0x123456789abcdef0ULL; \
	u64 it; \
	compiler_barrier(); \
	for (it = 0; it < iters; it++) { \
		steps \
		asm volatile("" : "+r"(x) :: "memory"); \
	} \
	return x; \
}

#define CALLS_DIRECT_1  CALL_DIRECT();
#define CALLS_DIRECT_2  CALLS_DIRECT_1 CALL_DIRECT();
#define CALLS_DIRECT_4  CALLS_DIRECT_2 CALL_DIRECT(); CALL_DIRECT();
#define CALLS_DIRECT_8  CALLS_DIRECT_4 CALL_DIRECT(); CALL_DIRECT(); CALL_DIRECT(); CALL_DIRECT();
#define CALLS_DIRECT_16 CALLS_DIRECT_8 CALL_DIRECT(); CALL_DIRECT(); CALL_DIRECT(); CALL_DIRECT(); CALL_DIRECT(); CALL_DIRECT(); CALL_DIRECT(); CALL_DIRECT();

#define CALLS_CACHED_1  CALL_CACHED_INDIRECT();
#define CALLS_CACHED_2  CALLS_CACHED_1 CALL_CACHED_INDIRECT();
#define CALLS_CACHED_4  CALLS_CACHED_2 CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT();
#define CALLS_CACHED_8  CALLS_CACHED_4 CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT();
#define CALLS_CACHED_16 CALLS_CACHED_8 CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT(); CALL_CACHED_INDIRECT();

#define CALLS_SLOT_DIRECT_1  CALL_SLOT_DIRECT();
#define CALLS_SLOT_DIRECT_2  CALLS_SLOT_DIRECT_1 CALL_SLOT_DIRECT();
#define CALLS_SLOT_DIRECT_4  CALLS_SLOT_DIRECT_2 CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT();
#define CALLS_SLOT_DIRECT_8  CALLS_SLOT_DIRECT_4 CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT();
#define CALLS_SLOT_DIRECT_16 CALLS_SLOT_DIRECT_8 CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT(); CALL_SLOT_DIRECT();

#define CALLS_PGOT_1  CALL_PGOT();
#define CALLS_PGOT_2  CALLS_PGOT_1 CALL_PGOT();
#define CALLS_PGOT_4  CALLS_PGOT_2 CALL_PGOT(); CALL_PGOT();
#define CALLS_PGOT_8  CALLS_PGOT_4 CALL_PGOT(); CALL_PGOT(); CALL_PGOT(); CALL_PGOT();
#define CALLS_PGOT_16 CALLS_PGOT_8 CALL_PGOT(); CALL_PGOT(); CALL_PGOT(); CALL_PGOT(); CALL_PGOT(); CALL_PGOT(); CALL_PGOT(); CALL_PGOT();

#define CALLS_EMPTY_1  EMPTY_BARRIER();
#define CALLS_EMPTY_2  CALLS_EMPTY_1 EMPTY_BARRIER();
#define CALLS_EMPTY_4  CALLS_EMPTY_2 EMPTY_BARRIER(); EMPTY_BARRIER();
#define CALLS_EMPTY_8  CALLS_EMPTY_4 EMPTY_BARRIER(); EMPTY_BARRIER(); EMPTY_BARRIER(); EMPTY_BARRIER();
#define CALLS_EMPTY_16 CALLS_EMPTY_8 EMPTY_BARRIER(); EMPTY_BARRIER(); EMPTY_BARRIER(); EMPTY_BARRIER(); EMPTY_BARRIER(); EMPTY_BARRIER(); EMPTY_BARRIER(); EMPTY_BARRIER();

DEFINE_EMPTY_BODY(empty_1, CALLS_EMPTY_1)
DEFINE_EMPTY_BODY(empty_2, CALLS_EMPTY_2)
DEFINE_EMPTY_BODY(empty_4, CALLS_EMPTY_4)
DEFINE_EMPTY_BODY(empty_8, CALLS_EMPTY_8)
DEFINE_EMPTY_BODY(empty_16, CALLS_EMPTY_16)

#ifdef BENCH_PGOT_FIRST
DEFINE_BODY(pgot, 1, CALLS_PGOT_1)
DEFINE_BODY(pgot, 2, CALLS_PGOT_2)
DEFINE_BODY(pgot, 4, CALLS_PGOT_4)
DEFINE_BODY(pgot, 8, CALLS_PGOT_8)
DEFINE_BODY(pgot, 16, CALLS_PGOT_16)

DEFINE_CACHED_BODY(1, CALLS_CACHED_1)
DEFINE_CACHED_BODY(2, CALLS_CACHED_2)
DEFINE_CACHED_BODY(4, CALLS_CACHED_4)
DEFINE_CACHED_BODY(8, CALLS_CACHED_8)
DEFINE_CACHED_BODY(16, CALLS_CACHED_16)

DEFINE_BODY(slot_direct, 1, CALLS_SLOT_DIRECT_1)
DEFINE_BODY(slot_direct, 2, CALLS_SLOT_DIRECT_2)
DEFINE_BODY(slot_direct, 4, CALLS_SLOT_DIRECT_4)
DEFINE_BODY(slot_direct, 8, CALLS_SLOT_DIRECT_8)
DEFINE_BODY(slot_direct, 16, CALLS_SLOT_DIRECT_16)

DEFINE_BODY(direct, 1, CALLS_DIRECT_1)
DEFINE_BODY(direct, 2, CALLS_DIRECT_2)
DEFINE_BODY(direct, 4, CALLS_DIRECT_4)
DEFINE_BODY(direct, 8, CALLS_DIRECT_8)
DEFINE_BODY(direct, 16, CALLS_DIRECT_16)
#else
DEFINE_BODY(direct, 1, CALLS_DIRECT_1)
DEFINE_BODY(direct, 2, CALLS_DIRECT_2)
DEFINE_BODY(direct, 4, CALLS_DIRECT_4)
DEFINE_BODY(direct, 8, CALLS_DIRECT_8)
DEFINE_BODY(direct, 16, CALLS_DIRECT_16)

DEFINE_CACHED_BODY(1, CALLS_CACHED_1)
DEFINE_CACHED_BODY(2, CALLS_CACHED_2)
DEFINE_CACHED_BODY(4, CALLS_CACHED_4)
DEFINE_CACHED_BODY(8, CALLS_CACHED_8)
DEFINE_CACHED_BODY(16, CALLS_CACHED_16)

DEFINE_BODY(slot_direct, 1, CALLS_SLOT_DIRECT_1)
DEFINE_BODY(slot_direct, 2, CALLS_SLOT_DIRECT_2)
DEFINE_BODY(slot_direct, 4, CALLS_SLOT_DIRECT_4)
DEFINE_BODY(slot_direct, 8, CALLS_SLOT_DIRECT_8)
DEFINE_BODY(slot_direct, 16, CALLS_SLOT_DIRECT_16)

DEFINE_BODY(pgot, 1, CALLS_PGOT_1)
DEFINE_BODY(pgot, 2, CALLS_PGOT_2)
DEFINE_BODY(pgot, 4, CALLS_PGOT_4)
DEFINE_BODY(pgot, 8, CALLS_PGOT_8)
DEFINE_BODY(pgot, 16, CALLS_PGOT_16)
#endif

typedef u64 (*body_fn_t)(u64);

#ifdef BENCH_ASM_MATCHED
extern u64 body_asm_empty_1(u64 iters);
extern u64 body_asm_empty_2(u64 iters);
extern u64 body_asm_empty_4(u64 iters);
extern u64 body_asm_empty_8(u64 iters);
extern u64 body_asm_empty_16(u64 iters);
extern u64 body_asm_direct_1(u64 iters);
extern u64 body_asm_direct_2(u64 iters);
extern u64 body_asm_direct_4(u64 iters);
extern u64 body_asm_direct_8(u64 iters);
extern u64 body_asm_direct_16(u64 iters);
extern u64 body_asm_cached_1(u64 iters);
extern u64 body_asm_cached_2(u64 iters);
extern u64 body_asm_cached_4(u64 iters);
extern u64 body_asm_cached_8(u64 iters);
extern u64 body_asm_cached_16(u64 iters);
extern u64 body_asm_pgot_1(u64 iters);
extern u64 body_asm_pgot_2(u64 iters);
extern u64 body_asm_pgot_4(u64 iters);
extern u64 body_asm_pgot_8(u64 iters);
extern u64 body_asm_pgot_16(u64 iters);

#define ASM_EVENT_EMPTY \
	".byte 0x0f,0x1f,0x44,0x00,0x00\n\t" \
	".byte 0x0f,0x1f,0x44,0x00,0x00\n\t" \
	".byte 0x0f,0x1f,0x00\n\t"

#define ASM_EVENT_DIRECT \
	"call target_0\n\t" \
	".byte 0x0f,0x1f,0x44,0x00,0x00\n\t" \
	"mov %rax,%rdi\n\t"

#define ASM_EVENT_CACHED \
	".byte 0x0f,0x1f,0x80,0x00,0x00,0x00,0x00\n\t" \
	"call *%r13\n\t" \
	"mov %rax,%rdi\n\t"

#define ASM_EVENT_PGOT \
	"mov pgot_func_table(%rip),%r11\n\t" \
	"call *%r11\n\t" \
	"mov %rax,%rdi\n\t"

#define ASM_EVENTS_1(event) event
#define ASM_EVENTS_2(event) ASM_EVENTS_1(event) event
#define ASM_EVENTS_4(event) ASM_EVENTS_2(event) event event
#define ASM_EVENTS_8(event) ASM_EVENTS_4(event) event event event event
#define ASM_EVENTS_16(event) ASM_EVENTS_8(event) event event event event event event event event

#define DEFINE_ASM_BODY(kind, events, event_code) \
asm( \
	".text\n\t" \
	".align 64\n\t" \
	".globl body_asm_" #kind "_" #events "\n\t" \
	".type body_asm_" #kind "_" #events ", @function\n" \
	"body_asm_" #kind "_" #events ":\n\t" \
	"push %rbp\n\t" \
	"mov %rsp,%rbp\n\t" \
	"push %r12\n\t" \
	"push %rbx\n\t" \
	"mov %rdi,%r12\n\t" \
	"movabs $0x123456789abcdef0,%rdi\n\t" \
	"test %r12,%r12\n\t" \
	"je 2f\n\t" \
	"xor %ebx,%ebx\n\t" \
	".align 64\n" \
	"1:\n\t" \
	event_code \
	"add $1,%rbx\n\t" \
	"cmp %rbx,%r12\n\t" \
	"jne 1b\n" \
	"2:\n\t" \
	"mov %rdi,%rax\n\t" \
	"pop %rbx\n\t" \
	"pop %r12\n\t" \
	"pop %rbp\n\t" \
	"ret\n\t" \
	"int3\n\t" \
	".size body_asm_" #kind "_" #events ", .-body_asm_" #kind "_" #events "\n\t" \
)

#define DEFINE_ASM_CACHED_BODY(events, event_code) \
asm( \
	".text\n\t" \
	".align 64\n\t" \
	".globl body_asm_cached_" #events "\n\t" \
	".type body_asm_cached_" #events ", @function\n" \
	"body_asm_cached_" #events ":\n\t" \
	"push %rbp\n\t" \
	"mov %rsp,%rbp\n\t" \
	"push %r13\n\t" \
	"push %r12\n\t" \
	"push %rbx\n\t" \
	"mov %rdi,%r12\n\t" \
	"mov pgot_func_table(%rip),%r13\n\t" \
	"movabs $0x123456789abcdef0,%rdi\n\t" \
	"test %r12,%r12\n\t" \
	"je 2f\n\t" \
	"xor %ebx,%ebx\n\t" \
	".align 64\n" \
	"1:\n\t" \
	event_code \
	"add $1,%rbx\n\t" \
	"cmp %rbx,%r12\n\t" \
	"jne 1b\n" \
	"2:\n\t" \
	"mov %rdi,%rax\n\t" \
	"pop %rbx\n\t" \
	"pop %r12\n\t" \
	"pop %r13\n\t" \
	"pop %rbp\n\t" \
	"ret\n\t" \
	"int3\n\t" \
	".size body_asm_cached_" #events ", .-body_asm_cached_" #events "\n\t" \
)

DEFINE_ASM_BODY(empty, 1, ASM_EVENTS_1(ASM_EVENT_EMPTY));
DEFINE_ASM_BODY(empty, 2, ASM_EVENTS_2(ASM_EVENT_EMPTY));
DEFINE_ASM_BODY(empty, 4, ASM_EVENTS_4(ASM_EVENT_EMPTY));
DEFINE_ASM_BODY(empty, 8, ASM_EVENTS_8(ASM_EVENT_EMPTY));
DEFINE_ASM_BODY(empty, 16, ASM_EVENTS_16(ASM_EVENT_EMPTY));
DEFINE_ASM_BODY(direct, 1, ASM_EVENTS_1(ASM_EVENT_DIRECT));
DEFINE_ASM_BODY(direct, 2, ASM_EVENTS_2(ASM_EVENT_DIRECT));
DEFINE_ASM_BODY(direct, 4, ASM_EVENTS_4(ASM_EVENT_DIRECT));
DEFINE_ASM_BODY(direct, 8, ASM_EVENTS_8(ASM_EVENT_DIRECT));
DEFINE_ASM_BODY(direct, 16, ASM_EVENTS_16(ASM_EVENT_DIRECT));
DEFINE_ASM_CACHED_BODY(1, ASM_EVENTS_1(ASM_EVENT_CACHED));
DEFINE_ASM_CACHED_BODY(2, ASM_EVENTS_2(ASM_EVENT_CACHED));
DEFINE_ASM_CACHED_BODY(4, ASM_EVENTS_4(ASM_EVENT_CACHED));
DEFINE_ASM_CACHED_BODY(8, ASM_EVENTS_8(ASM_EVENT_CACHED));
DEFINE_ASM_CACHED_BODY(16, ASM_EVENTS_16(ASM_EVENT_CACHED));
DEFINE_ASM_BODY(pgot, 1, ASM_EVENTS_1(ASM_EVENT_PGOT));
DEFINE_ASM_BODY(pgot, 2, ASM_EVENTS_2(ASM_EVENT_PGOT));
DEFINE_ASM_BODY(pgot, 4, ASM_EVENTS_4(ASM_EVENT_PGOT));
DEFINE_ASM_BODY(pgot, 8, ASM_EVENTS_8(ASM_EVENT_PGOT));
DEFINE_ASM_BODY(pgot, 16, ASM_EVENTS_16(ASM_EVENT_PGOT));
#endif

static body_fn_t select_empty_body(int events)
{
	switch (events) {
	case 1: return body_empty_1;
	case 2: return body_empty_2;
	case 4: return body_empty_4;
	case 8: return body_empty_8;
	case 16: return body_empty_16;
	default: return NULL;
	}
}

static body_fn_t select_cached_body(int events)
{
	switch (events) {
	case 1: return body_cached_1;
	case 2: return body_cached_2;
	case 4: return body_cached_4;
	case 8: return body_cached_8;
	case 16: return body_cached_16;
	default: return NULL;
	}
}

static body_fn_t select_body(bool pgot, int events)
{
	if (!pgot) {
		switch (events) {
		case 1: return body_direct_1;
		case 2: return body_direct_2;
		case 4: return body_direct_4;
		case 8: return body_direct_8;
		case 16: return body_direct_16;
		default: return NULL;
		}
	}

	switch (events) {
	case 1: return body_pgot_1;
	case 2: return body_pgot_2;
	case 4: return body_pgot_4;
	case 8: return body_pgot_8;
	case 16: return body_pgot_16;
	default: return NULL;
	}
}

static body_fn_t select_slot_direct_body(int events)
{
	switch (events) {
	case 1: return body_slot_direct_1;
	case 2: return body_slot_direct_2;
	case 4: return body_slot_direct_4;
	case 8: return body_slot_direct_8;
	case 16: return body_slot_direct_16;
	default: return NULL;
	}
}

#ifdef BENCH_ASM_MATCHED
static body_fn_t select_asm_empty_body(int events)
{
	switch (events) {
	case 1: return body_asm_empty_1;
	case 2: return body_asm_empty_2;
	case 4: return body_asm_empty_4;
	case 8: return body_asm_empty_8;
	case 16: return body_asm_empty_16;
	default: return NULL;
	}
}

static body_fn_t select_asm_direct_body(int events)
{
	switch (events) {
	case 1: return body_asm_direct_1;
	case 2: return body_asm_direct_2;
	case 4: return body_asm_direct_4;
	case 8: return body_asm_direct_8;
	case 16: return body_asm_direct_16;
	default: return NULL;
	}
}

static body_fn_t select_asm_cached_body(int events)
{
	switch (events) {
	case 1: return body_asm_cached_1;
	case 2: return body_asm_cached_2;
	case 4: return body_asm_cached_4;
	case 8: return body_asm_cached_8;
	case 16: return body_asm_cached_16;
	default: return NULL;
	}
}

static body_fn_t select_asm_pgot_body(int events)
{
	switch (events) {
	case 1: return body_asm_pgot_1;
	case 2: return body_asm_pgot_2;
	case 4: return body_asm_pgot_4;
	case 8: return body_asm_pgot_8;
	case 16: return body_asm_pgot_16;
	default: return NULL;
	}
}
#endif

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

static void print_raw_line(int events, int repeat, s64 empty, s64 direct,
			   s64 cached, s64 slot_direct, s64 pgot)
{
	s64 delta_cached_direct = cached - direct;
	s64 delta_slot_direct = slot_direct - direct;
	s64 delta_pgot_cached = pgot - cached;
	s64 delta_pgot_direct = pgot - direct;
	char empty_buf[32];
	char direct_buf[32];
	char cached_buf[32];
	char slot_direct_buf[32];
	char pgot_buf[32];
	char delta_cached_direct_buf[32];
	char delta_slot_direct_buf[32];
	char delta_pgot_cached_buf[32];
	char delta_pgot_direct_buf[32];

	scaled_to_buf(empty_buf, sizeof(empty_buf), empty);
	scaled_to_buf(direct_buf, sizeof(direct_buf), direct);
	scaled_to_buf(cached_buf, sizeof(cached_buf), cached);
	scaled_to_buf(slot_direct_buf, sizeof(slot_direct_buf), slot_direct);
	scaled_to_buf(pgot_buf, sizeof(pgot_buf), pgot);
	scaled_to_buf(delta_cached_direct_buf, sizeof(delta_cached_direct_buf),
		      delta_cached_direct);
	scaled_to_buf(delta_slot_direct_buf, sizeof(delta_slot_direct_buf),
		      delta_slot_direct);
	scaled_to_buf(delta_pgot_cached_buf, sizeof(delta_pgot_cached_buf),
		      delta_pgot_cached);
	scaled_to_buf(delta_pgot_direct_buf, sizeof(delta_pgot_direct_buf),
		      delta_pgot_direct);

	pr_info("PGOT_L1FS_RAW,layer1_func_stable,%s,%d,%d,%d,%lu,%s,%s,%s,%s,%s,%s,%s,%s,%s\n",
		build, run_id, events, repeat, iterations, empty_buf, direct_buf,
		cached_buf, slot_direct_buf, pgot_buf, delta_cached_direct_buf,
		delta_slot_direct_buf, delta_pgot_cached_buf,
		delta_pgot_direct_buf);
}

#ifdef BENCH_ASM_MATCHED
static void print_asm_raw_line(int events, int repeat, s64 empty, s64 direct,
			       s64 cached, s64 pgot)
{
	s64 delta_cached_direct = cached - direct;
	s64 delta_pgot_cached = pgot - cached;
	s64 delta = pgot - direct;
	char empty_buf[32];
	char direct_buf[32];
	char cached_buf[32];
	char pgot_buf[32];
	char delta_cached_direct_buf[32];
	char delta_pgot_cached_buf[32];
	char delta_buf[32];

	scaled_to_buf(empty_buf, sizeof(empty_buf), empty);
	scaled_to_buf(direct_buf, sizeof(direct_buf), direct);
	scaled_to_buf(cached_buf, sizeof(cached_buf), cached);
	scaled_to_buf(pgot_buf, sizeof(pgot_buf), pgot);
	scaled_to_buf(delta_cached_direct_buf, sizeof(delta_cached_direct_buf),
		      delta_cached_direct);
	scaled_to_buf(delta_pgot_cached_buf, sizeof(delta_pgot_cached_buf),
		      delta_pgot_cached);
	scaled_to_buf(delta_buf, sizeof(delta_buf), delta);

	pr_info("PGOT_L1FS_ASM_RAW,layer1_func_stable_asm_matched,%s,%d,%d,%d,%lu,%s,%s,%s,%s,%s,%s,%s\n",
		build, run_id, events, repeat, iterations, empty_buf, direct_buf,
		cached_buf, pgot_buf, delta_cached_direct_buf,
		delta_pgot_cached_buf, delta_buf);
}
#endif

static int run_event(int events)
{
	body_fn_t empty_fn = select_empty_body(events);
	body_fn_t direct_fn = select_body(false, events);
	body_fn_t cached_fn = select_cached_body(events);
	body_fn_t slot_direct_fn = select_slot_direct_body(events);
	body_fn_t pgot_fn = select_body(true, events);
	int r;

	if (!empty_fn || !direct_fn || !cached_fn || !slot_direct_fn || !pgot_fn)
		return -EINVAL;

	(void)measure_x1000(empty_fn, iterations / 10 + 1);
	(void)measure_x1000(direct_fn, iterations / 10 + 1);
	(void)measure_x1000(cached_fn, iterations / 10 + 1);
	(void)measure_x1000(slot_direct_fn, iterations / 10 + 1);
	(void)measure_x1000(pgot_fn, iterations / 10 + 1);

	for (r = 0; r < repeats; r++) {
		s64 empty, direct, cached, slot_direct, pgot;

		switch (r % 5) {
		case 0:
			empty = measure_x1000(empty_fn, iterations);
			direct = measure_x1000(direct_fn, iterations);
			cached = measure_x1000(cached_fn, iterations);
			slot_direct = measure_x1000(slot_direct_fn, iterations);
			pgot = measure_x1000(pgot_fn, iterations);
			break;
		case 1:
			pgot = measure_x1000(pgot_fn, iterations);
			slot_direct = measure_x1000(slot_direct_fn, iterations);
			cached = measure_x1000(cached_fn, iterations);
			empty = measure_x1000(empty_fn, iterations);
			direct = measure_x1000(direct_fn, iterations);
			break;
		case 2:
			direct = measure_x1000(direct_fn, iterations);
			cached = measure_x1000(cached_fn, iterations);
			slot_direct = measure_x1000(slot_direct_fn, iterations);
			pgot = measure_x1000(pgot_fn, iterations);
			empty = measure_x1000(empty_fn, iterations);
			break;
		case 3:
			cached = measure_x1000(cached_fn, iterations);
			pgot = measure_x1000(pgot_fn, iterations);
			direct = measure_x1000(direct_fn, iterations);
			empty = measure_x1000(empty_fn, iterations);
			slot_direct = measure_x1000(slot_direct_fn, iterations);
			break;
		default:
			slot_direct = measure_x1000(slot_direct_fn, iterations);
			empty = measure_x1000(empty_fn, iterations);
			pgot = measure_x1000(pgot_fn, iterations);
			direct = measure_x1000(direct_fn, iterations);
			cached = measure_x1000(cached_fn, iterations);
			break;
		}
		print_raw_line(events, r, empty, direct, cached, slot_direct, pgot);
	}
	return 0;
}

static int run_all_events(void)
{
	static const int events[] = {1, 2, 4, 8, 16};
	int i, ret;

	for (i = 0; i < ARRAY_SIZE(events); i++) {
		ret = run_event(events[i]);
		if (ret)
			return ret;
	}
	return 0;
}

#ifdef BENCH_ASM_MATCHED
static int run_asm_event(int events)
{
	body_fn_t empty_fn = select_asm_empty_body(events);
	body_fn_t direct_fn = select_asm_direct_body(events);
	body_fn_t cached_fn = select_asm_cached_body(events);
	body_fn_t pgot_fn = select_asm_pgot_body(events);
	int r;

	if (!empty_fn || !direct_fn || !cached_fn || !pgot_fn)
		return -EINVAL;

	(void)measure_x1000(empty_fn, iterations / 10 + 1);
	(void)measure_x1000(direct_fn, iterations / 10 + 1);
	(void)measure_x1000(cached_fn, iterations / 10 + 1);
	(void)measure_x1000(pgot_fn, iterations / 10 + 1);

	for (r = 0; r < repeats; r++) {
		s64 empty, direct, cached, pgot;

		switch (r % 4) {
		case 0:
			empty = measure_x1000(empty_fn, iterations);
			direct = measure_x1000(direct_fn, iterations);
			cached = measure_x1000(cached_fn, iterations);
			pgot = measure_x1000(pgot_fn, iterations);
			break;
		case 1:
			pgot = measure_x1000(pgot_fn, iterations);
			cached = measure_x1000(cached_fn, iterations);
			empty = measure_x1000(empty_fn, iterations);
			direct = measure_x1000(direct_fn, iterations);
			break;
		case 2:
			direct = measure_x1000(direct_fn, iterations);
			cached = measure_x1000(cached_fn, iterations);
			pgot = measure_x1000(pgot_fn, iterations);
			empty = measure_x1000(empty_fn, iterations);
			break;
		default:
			cached = measure_x1000(cached_fn, iterations);
			empty = measure_x1000(empty_fn, iterations);
			pgot = measure_x1000(pgot_fn, iterations);
			direct = measure_x1000(direct_fn, iterations);
			break;
		}
		print_asm_raw_line(events, r, empty, direct, cached, pgot);
	}
	return 0;
}

static int run_all_asm_events(void)
{
	static const int events[] = {1, 2, 4, 8, 16};
	int i, ret;

	for (i = 0; i < ARRAY_SIZE(events); i++) {
		ret = run_asm_event(events[i]);
		if (ret)
			return ret;
	}
	return 0;
}
#endif

static int pin_current_cpu(void)
{
	if (cpu < 0)
		return 0;
	if (cpu >= nr_cpu_ids || !cpu_online(cpu))
		return -EINVAL;
	return set_cpus_allowed_ptr(current, cpumask_of(cpu));
}

static int __init pgot_l1fs_init(void)
{
	int ret;

	if (!iterations || repeats <= 0)
		return -EINVAL;

	ret = pin_current_cpu();
	if (ret) {
		pr_err("PGOT_L1FS_ERROR,cpu_pin_failed,cpu=%d,ret=%d\n", cpu, ret);
		return ret;
	}

	init_func_table();
	pr_info("PGOT_L1FS_BEGIN,build=%s,run_id=%d,iterations=%lu,repeats=%d,cpu=%d,sample_order=interleave,target_pattern=stable\n",
		build, run_id, iterations, repeats, cpu);

#ifndef BENCH_ASM_ONLY
	ret = run_all_events();
	if (ret)
		return ret;
#endif

#ifdef BENCH_ASM_MATCHED
	ret = run_all_asm_events();
	if (ret)
		return ret;
#endif

	pr_info("PGOT_L1FS_END,build=%s,run_id=%d\n", build, run_id);
	return 0;
}

static void __exit pgot_l1fs_exit(void)
{
	pr_info("PGOT_L1FS_EXIT,build=%s,run_id=%d\n", build, run_id);
}

module_init(pgot_l1fs_init);
module_exit(pgot_l1fs_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("pgot_benchmarks");
MODULE_DESCRIPTION("Layer1 func-pgot stable target benchmark in kernel mode");
