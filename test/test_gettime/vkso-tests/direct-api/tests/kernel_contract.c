// SPDX-License-Identifier: GPL-2.0
/* Host fixture for the actual shared algorithm and kernel domain adapters.
 * No hardware, MM, scheduler, or memory-ordering claim is made by this test. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <linux/vkso_time.h>
#include <linux/vkso_getcpu.h>
#include <vdso/clocksource.h>

union vkso_shared_page vkso_shared_page;
struct vkso_context vkso_kernel_context;
struct timezone sys_tz = { 12, 3 };
int timekeeping_suspended;
static u64 cycles;
static unsigned counter_calls, private_calls, user_calls, cpu_calls;
static int rewrite_generation;

u64 host_counter(void)
{
	counter_calls++;
	if (rewrite_generation) {
		rewrite_generation = 0;
		vkso_shared_page.data.seq += 2;
		vkso_shared_page.data.state.monotonic_base.sec = 123;
	}
	return cycles;
}

/* Only the environment-specific private reader is replaced with a fixture. */
void vkso_timekeeping_get_private(clockid_t id, struct timespec64 *ts)
{
	private_calls++;
	ts->tv_sec = 100 + id;
	ts->tv_nsec = 900000000;
}
int __vkso_getcpu(unsigned *cpu, unsigned *node, void *unused)
{
	cpu_calls++;
	if (cpu) *cpu = 2;
	if (node) *node = 0;
	return VKSO_GETCPU_OK;
}
#include "callbacks.inc"
#include "callers.inc"

static int user_clock_failure(s32 id, struct vkso_time_value *v,
			      const struct vkso_mm_data *mm)
{
	user_calls++;
	/* Model a syscall result which ALREADY includes namespace offsets. */
	v->sec = 777;
	v->nsec = 123;
	return -EIO;
}
static int user_gtod_failure(struct vkso_timeval *tv,
			     struct vkso_timezone *tz, int status)
{
	assert(status == VKSO_TIME_UNSUPPORTED_MODE);
	user_calls++;
	return -EIO;
}

static void reset(void)
{
	struct vkso_read_state *s;
	memset(&vkso_shared_page, 0, sizeof(vkso_shared_page));
	vkso_shared_page.data.seq = 2;
	vkso_shared_page.data.abi_version = VKSO_TIME_ABI_VERSION;
	s = &vkso_shared_page.data.state;
	s->cycles.clock_mode = VDSO_CLOCKMODE_TSC;
	s->cycles.cycle_last = 100;
	s->cycles.mono_mult = 3;
	s->cycles.raw_mult = 2;
	s->cycles.shift = 1;
	s->cycles.mask = UINT64_MAX;
	s->realtime_base.sec = 10;
	s->monotonic_base.sec = 20;
	s->monotonic_raw_base.sec = 30;
	s->boottime_base.sec = 40;
	s->tai_base.sec = 50;
	s->realtime_coarse = (struct vkso_time_value){10, 12};
	s->monotonic_coarse = (struct vkso_time_value){20, 34};
	s->hrtimer_resolution = 1;
	s->clocksource_resolution = 2;
	s->timezone = (struct vkso_timezone){12, 3};
	vkso_kernel_context = (struct vkso_context){
		.clock_gettime_failure = vkso_posix_clock_gettime_failure,
		.gettimeofday_failure = vkso_kernel_gettimeofday_failure,
	};
	cycles = 110;
	counter_calls = private_calls = user_calls = cpu_calls = 0;
	rewrite_generation = 0;
}

static void hres(void)
{
	const int ids[] = {CLOCK_REALTIME, CLOCK_MONOTONIC, CLOCK_MONOTONIC_RAW,
			   CLOCK_BOOTTIME, CLOCK_TAI};
	struct vkso_read_state *s = &vkso_shared_page.data.state;
	struct vkso_hres_base *bases[] = {&s->realtime_base, &s->monotonic_base,
		&s->monotonic_raw_base, &s->boottime_base, &s->tai_base};
	struct vkso_mm_data mm = {.clock_mask = UINT32_MAX,
		.monotonic_offset = {-3, 800000000}, .boottime_offset = {4, 600000000}};
	for (unsigned i = 0; i < 10000; ++i) {
		cycles = 90 + i * 97;
		for (unsigned j = 0; j < 5; ++j) {
			struct vkso_time_value out;
			u64 ns;
			s64 sec = bases[j]->sec;
			bases[j]->shifted_nsec = (u64)(i % 9) * NSEC_PER_SEC;
			ns = (bases[j]->shifted_nsec + (cycles > 100 ? cycles - 100 : 0) *
				(j == 2 ? 2 : 3)) >> 1;
			sec += ns / NSEC_PER_SEC;
			ns %= NSEC_PER_SEC;
			if (j == 1 || j == 2) { sec -= 3; ns += 800000000; }
			if (j == 3) { sec += 4; ns += 600000000; }
			sec += ns / NSEC_PER_SEC;
			ns %= NSEC_PER_SEC;
			assert(!vkso_clock_gettime_hres(ids[j], &out, &mm, &vkso_kernel_context));
			assert(out.sec == sec && out.nsec == ns);
		}
	}
	assert(private_calls == 0 && counter_calls == 50000);
}

static void coarse(void)
{
	struct vkso_mm_data mm = {.clock_mask = 1U << CLOCK_MONOTONIC_COARSE,
		.monotonic_offset = {-2, 999999980}};
	struct vkso_time_value out;
	struct vkso_timeval tv;
	struct vkso_timezone tz;
	s64 stored;
	assert(!vkso_clock_gettime_coarse(CLOCK_MONOTONIC_COARSE, &out, &mm));
	assert(out.sec == 19 && out.nsec == 14);
	assert(!vkso_clock_getres_hres(&out) && out.sec == 0 && out.nsec == 1);
	assert(!vkso_clock_getres_hres(NULL));
	assert(!vkso_clock_getres_coarse(&out) && out.nsec == LOW_RES_NSEC);
	assert(!vkso_clock_getres_coarse(NULL));
	assert(__vkso_time(&stored) == 10 && stored == 10);
	assert(__vkso_time(NULL) == 10);
	assert(!counter_calls);
	assert(!vkso_gettimeofday_core(&tv, &tz, &vkso_kernel_context));
	assert(tv.sec == 10 && tv.usec == 0 && tz.minuteswest == 12 && tz.dsttime == 3);
}

static void user_failure(void)
{
	struct vkso_context context = {.clock_gettime_failure = user_clock_failure,
		.gettimeofday_failure = user_gtod_failure};
	struct vkso_mm_data mm = {.clock_mask = UINT32_MAX,
		.monotonic_offset = {500, 800000000}};
	struct vkso_time_value out;
	struct vkso_timeval tv;
	vkso_shared_page.data.state.cycles.clock_mode = VDSO_CLOCKMODE_NONE;
	assert(vkso_clock_gettime_hres(CLOCK_MONOTONIC, &out, &mm, &context) == -EIO);
	assert(user_calls == 1 && private_calls == 0);
	assert(out.sec == 777 && out.nsec == 123);
	assert(vkso_gettimeofday_core(&tv, NULL, &context) == -EIO);
	assert(user_calls == 2);
}

static void kernel_failure(void)
{
	struct timespec64 ts;
	struct vkso_time_value out;
	struct vkso_timeval tv;
	struct vkso_mm_data mm = {.clock_mask = UINT32_MAX,
		.monotonic_offset = {-3, 800000000}, .boottime_offset = {4, 600000000}};
	vkso_shared_page.data.state.cycles.clock_mode = VDSO_CLOCKMODE_NONE;
	ktime_get_ts64(&ts);
	assert(private_calls == 1 && ts.tv_sec == 101 && ts.tv_nsec == 900000000);
	assert(!vkso_clock_gettime_hres(CLOCK_MONOTONIC, &out, &mm, &vkso_kernel_context));
	assert(private_calls == 2 && out.sec == 99 && out.nsec == 700000000);
	assert(!vkso_clock_gettime_hres(CLOCK_BOOTTIME, &out, &mm, &vkso_kernel_context));
	assert(private_calls == 3 && out.sec == 112 && out.nsec == 500000000);
	assert(!vkso_gettimeofday_core(&tv, NULL, &vkso_kernel_context));
	assert(private_calls == 4 && tv.sec == 100 && tv.usec == 900000);
	assert(ktime_get_raw() == INT64_C(104900000000));
	assert(private_calls == 5);
}

static void callers(void)
{
	struct timespec64 ts;
	ktime_get_ts64(&ts);
	assert(ts.tv_sec == 20 && ts.tv_nsec == 15);
	ktime_get_raw_ts64(&ts);
	assert(ts.tv_sec == 30 && ts.tv_nsec == 10);
	ktime_get_real_ts64(&ts);
	assert(ts.tv_sec == 10 && ts.tv_nsec == 15);
	assert(ktime_get() == INT64_C(20000000015));
	assert(ktime_get_raw() == INT64_C(30000000010));
	assert(ktime_get_with_offset(TK_OFFS_REAL) == INT64_C(10000000015));
	assert(ktime_get_with_offset(TK_OFFS_BOOT) == INT64_C(40000000015));
	assert(ktime_get_with_offset(TK_OFFS_TAI) == INT64_C(50000000015));
	assert(!private_calls);
}

static void unsupported(void)
{
	const int ids[] = {-1, CLOCK_PROCESS_CPUTIME_ID, CLOCK_REALTIME_ALARM, INT32_MAX};
	for (unsigned i = 0; i < sizeof(ids)/sizeof(ids[0]); ++i) {
		struct timespec64 ts = {88, 99};
		assert(vkso_time_get_root(ids[i], &ts) == VKSO_TIME_NOT_SHARED);
		assert(ts.tv_sec == 88 && ts.tv_nsec == 99);
	}
	assert(!private_calls && !counter_calls);
}

static void retry(void)
{
	struct timespec64 ts;
	rewrite_generation = 1;
	ktime_get_ts64(&ts);
	assert(ts.tv_sec == 123 && ts.tv_nsec == 15 && counter_calls == 2);
}
static void getcpu_test(void)
{
	unsigned cpu = 9, node = 9;
	assert(!vkso_getcpu(&cpu, &node) && cpu == 2 && node == 0);
	assert(!vkso_getcpu(NULL, NULL) && cpu_calls == 2);
}

int main(int argc, char **argv)
{
	if (argc != 2) return 2;
	reset();
	if (!strcmp(argv[1], "hres")) hres();
	else if (!strcmp(argv[1], "coarse")) coarse();
	else if (!strcmp(argv[1], "user-failure")) user_failure();
	else if (!strcmp(argv[1], "kernel-failure")) kernel_failure();
	else if (!strcmp(argv[1], "callers")) callers();
	else if (!strcmp(argv[1], "unsupported")) unsupported();
	else if (!strcmp(argv[1], "retry")) retry();
	else if (!strcmp(argv[1], "getcpu")) getcpu_test();
	else return 2;
	printf("HOST_FIXTURE PASS %s\n", argv[1]);
	return 0;
}
