// SPDX-License-Identifier: GPL-2.0

#include <linux/compiler.h>
#include <linux/hrtimer.h>
#include <linux/sched.h>
#include <linux/stddef.h>
#include <linux/string.h>
#include <linux/time.h>
#include <linux/time64.h>
#include <linux/timekeeper_internal.h>
#include <linux/vkso_time.h>

#include <vdso/clocksource.h>

static_assert(sizeof(struct timespec64) == sizeof(struct vkso_time_value) &&
	      offsetof(struct timespec64, tv_sec) ==
	      offsetof(struct vkso_time_value, sec) &&
	      offsetof(struct timespec64, tv_nsec) ==
	      offsetof(struct vkso_time_value, nsec));

union vkso_shared_page vkso_shared_page
	__aligned(VKSO_SHARED_PAGE_SIZE) __vkso_shared_data;

static __always_inline void vkso_time_prepare_cycles(
	struct vkso_cycle_data *next, const struct tk_read_base *tkr,
	s32 clock_mode)
{
	next->clock_mode = clock_mode;
	if (clock_mode == VDSO_CLOCKMODE_NONE)
		return;
	next->cycle_last = tkr->cycle_last;
	next->mask = tkr->mask;
	next->mult = tkr->mult;
	next->shift = tkr->shift;
}

static void vkso_time_prepare(struct vkso_shared_data *next,
			      const struct timekeeper *tk)
{
	s64 monotonic_sec = tk->xtime_sec + tk->wall_to_monotonic.tv_sec;
	u64 monotonic_shifted_nsec = tk->tkr_mono.xtime_nsec +
		((u64)tk->wall_to_monotonic.tv_nsec << tk->tkr_mono.shift);
	s64 boottime_sec;
	u64 boottime_shifted_nsec;
	u64 shifted_second = (u64)NSEC_PER_SEC << tk->tkr_mono.shift;
	s32 clock_mode = tk->tkr_mono.clock->vdso_clock_mode;

	if (monotonic_shifted_nsec >= shifted_second) {
		monotonic_shifted_nsec -= shifted_second;
		monotonic_sec++;
	}
	boottime_sec = monotonic_sec + tk->monotonic_to_boot.tv_sec;
	boottime_shifted_nsec = monotonic_shifted_nsec +
		((u64)tk->monotonic_to_boot.tv_nsec << tk->tkr_mono.shift);
	if (boottime_shifted_nsec >= shifted_second) {
		boottime_shifted_nsec -= shifted_second;
		boottime_sec++;
	}
	next->abi_version = VKSO_TIME_ABI_VERSION;
	next->hrtimer_resolution = hrtimer_resolution;
	next->realtime_coarse.sec = tk->xtime_sec;
	next->realtime_coarse.nsec =
		tk->tkr_mono.xtime_nsec >> tk->tkr_mono.shift;
	next->monotonic_coarse.sec = monotonic_sec;
	next->monotonic_coarse.nsec =
		monotonic_shifted_nsec >> tk->tkr_mono.shift;
	vkso_time_prepare_cycles(&next->hres.cycles, &tk->tkr_mono,
				 clock_mode);
	vkso_time_prepare_cycles(&next->raw.cycles, &tk->tkr_raw,
				 clock_mode);
	if (clock_mode == VDSO_CLOCKMODE_NONE)
		return;
	next->hres.realtime_base.sec = tk->xtime_sec;
	next->hres.realtime_base.shifted_nsec = tk->tkr_mono.xtime_nsec;
	next->hres.monotonic_base.sec = monotonic_sec;
	next->hres.monotonic_base.shifted_nsec = monotonic_shifted_nsec;
	next->hres.boottime_base.sec = boottime_sec;
	next->hres.boottime_base.shifted_nsec = boottime_shifted_nsec;
	next->hres.tai_base.sec = tk->xtime_sec + tk->tai_offset;
	next->hres.tai_base.shifted_nsec = tk->tkr_mono.xtime_nsec;
	next->raw.monotonic_raw_base.sec = tk->raw_sec;
	next->raw.monotonic_raw_base.shifted_nsec = tk->tkr_raw.xtime_nsec;
}

void vkso_time_publish(struct timekeeper *tk)
{
	struct vkso_shared_data next = { 0 };
	struct vkso_shared_data *shared = &vkso_shared_page.data;
	size_t payload_offset = offsetof(struct vkso_shared_data, abi_version);
	u32 seq;

	/* Derive first so the reader-visible odd interval only copies data. */
	vkso_time_prepare(&next, tk);
	seq = READ_ONCE(shared->seq);
	WRITE_ONCE(shared->seq, seq + 1);
	smp_wmb();
	memcpy((u8 *)shared + payload_offset, (u8 *)&next + payload_offset,
	       sizeof(*shared) - payload_offset);
	smp_wmb();
	WRITE_ONCE(shared->seq, seq + 2);
}

int vkso_time_get_global(clockid_t clock_id, struct timespec64 *tp)
{
	return __vkso_clock_gettime(NULL, clock_id,
				   (struct vkso_time_value *)tp);
}

int vkso_time_get_context(clockid_t clock_id, struct timespec64 *tp)
{
	const struct vkso_mm_data *mm_data =
		READ_ONCE(current->mm->context.vkso_mm_kdata);

	return __vkso_clock_gettime(mm_data, clock_id,
				   (struct vkso_time_value *)tp);
}

int vkso_time_getres(clockid_t clock_id, struct timespec64 *tp)
{
	return __vkso_clock_getres(clock_id, (struct vkso_time_value *)tp);
}
