// SPDX-License-Identifier: GPL-2.0

#include <asm/clocksource.h>
#include <asm/msr.h>
#include <asm/processor.h>

#include <linux/build_bug.h>
#include <linux/compiler.h>
#include <linux/stddef.h>
#include <linux/time.h>
#include <linux/vkso_time.h>

#include <vdso/clocksource.h>

/* Keep the binary contract explicit before executable interfaces are added. */
static_assert(sizeof(struct vkso_time_value) == 16);
static_assert(offsetof(struct vkso_time_value, sec) == 0);
static_assert(offsetof(struct vkso_time_value, nsec) == 8);
static_assert(offsetof(struct vkso_shared_data, realtime_coarse) == 8);
static_assert(offsetof(struct vkso_shared_data, monotonic_coarse) == 24);
static_assert(offsetof(struct vkso_shared_data, hres) == 40);
static_assert(offsetof(struct vkso_hres_data, cycle_last) == 8);
static_assert(offsetof(struct vkso_hres_data, mask) == 16);
static_assert(offsetof(struct vkso_hres_data, mult) == 24);
static_assert(offsetof(struct vkso_hres_data, shift) == 28);
static_assert(offsetof(struct vkso_hres_data, realtime_base) == 32);
static_assert(sizeof(struct vkso_hres_cycle_sample) == 64);
static_assert(offsetof(struct vkso_mm_data, monotonic_offset) == 8);
static_assert(sizeof(union vkso_shared_page) == VKSO_SHARED_PAGE_SIZE);
static_assert(sizeof(union vkso_mm_page) == VKSO_SHARED_PAGE_SIZE);

static __always_inline void vkso_count_retry(u32 *retries)
{
	if (*retries != (u32)-1)
		(*retries)++;
}

/*
 * The native counter backend is deliberately inlined into the common reader:
 * there is no callback or indirect branch between the two seq observations.
 */
static __always_inline bool vkso_read_tsc_cycles(s32 clock_mode, u64 *cycles)
{
	if (clock_mode != VDSO_CLOCKMODE_TSC)
		return false;
	*cycles = rdtsc_ordered();
	return true;
}

static __always_inline int
vkso_hres_cycle_snapshot(const struct vkso_shared_data *shared,
			 struct vkso_hres_cycle_sample *sample)
{
	struct vkso_hres_cycle_sample next;
	u32 abi_version;
	u32 retries = 0;
	bool have_cycles;

	if (!shared || !sample)
		return VKSO_TIME_FALLBACK;
	for (;;) {
		next.seq = READ_ONCE(shared->seq);
		if (next.seq & 1) {
			vkso_count_retry(&retries);
			cpu_relax();
			continue;
		}
		smp_rmb();
		abi_version = READ_ONCE(shared->abi_version);
		next.clock_mode = READ_ONCE(shared->hres.clock_mode);
		have_cycles = vkso_read_tsc_cycles(next.clock_mode,
						   &next.cycles);
		next.cycle_last = READ_ONCE(shared->hres.cycle_last);
		next.mask = READ_ONCE(shared->hres.mask);
		next.mult = READ_ONCE(shared->hres.mult);
		next.shift = READ_ONCE(shared->hres.shift);
		next.realtime_base.sec =
		READ_ONCE(shared->hres.realtime_base.sec);
		next.realtime_base.shifted_nsec =
		READ_ONCE(shared->hres.realtime_base.shifted_nsec);
		smp_rmb();
		if (next.seq == READ_ONCE(shared->seq))
			break;
		vkso_count_retry(&retries);
	}

	if (abi_version != VKSO_TIME_ABI_VERSION || !have_cycles)
		return VKSO_TIME_FALLBACK;
	next.retries = retries;
	next.reserved = 0;
	*sample = next;
	return VKSO_TIME_OK;
}

__visible noinline notrace __vkso_text
int __vkso_hres_cycle_probe(struct vkso_hres_cycle_sample *sample)
{
	const struct vkso_shared_data *shared;

	/* Keep the exported shared page reachable from a position-independent DSO. */
	asm("lea vkso_shared_page(%%rip), %0" : "=r" (shared));
	return vkso_hres_cycle_snapshot(shared, sample);
}

/* M08-only entry used to drive the same reader against a concurrent writer. */
__visible noinline notrace __vkso_text
int __vkso_test_hres_cycle_probe_at(
	const struct vkso_shared_data *shared,
	struct vkso_hres_cycle_sample *sample)
{
	return vkso_hres_cycle_snapshot(shared, sample);
}

__visible noinline notrace __vkso_text
int __vkso_clock_gettime(const struct vkso_mm_data *mm_data, int clock_id,
			 struct vkso_time_value *value)
{
	const struct vkso_shared_data *shared = &vkso_shared_page.data;
	u32 seq, abi_version;
	s64 offset_sec = 0;
	u64 offset_nsec = 0;
	s64 sec;
	u64 nsec;
	bool monotonic;

	if (!value)
		return VKSO_TIME_FALLBACK;
	switch (clock_id) {
	case CLOCK_REALTIME_COARSE:
		monotonic = false;
		break;
	case CLOCK_MONOTONIC_COARSE:
		if (!mm_data ||
		    READ_ONCE(mm_data->abi_version) !=
			    VKSO_MM_DATA_ABI_VERSION)
			return VKSO_TIME_FALLBACK;
		offset_sec = READ_ONCE(mm_data->monotonic_offset.sec);
		offset_nsec = READ_ONCE(mm_data->monotonic_offset.nsec);
		if (offset_nsec >= NSEC_PER_SEC)
			return VKSO_TIME_FALLBACK;
		monotonic = true;
		break;
	default:
		return VKSO_TIME_FALLBACK;
	}
	do {
		seq = READ_ONCE(shared->seq);
		if (seq & 1)
			continue;
		smp_rmb();
		abi_version = READ_ONCE(shared->abi_version);
		if (monotonic) {
			sec = READ_ONCE(shared->monotonic_coarse.sec);
			nsec = READ_ONCE(shared->monotonic_coarse.nsec);
		} else {
			sec = READ_ONCE(shared->realtime_coarse.sec);
			nsec = READ_ONCE(shared->realtime_coarse.nsec);
		}
		smp_rmb();
	} while ((seq & 1) || seq != READ_ONCE(shared->seq));

	if (abi_version != VKSO_TIME_ABI_VERSION || nsec >= NSEC_PER_SEC)
		return VKSO_TIME_FALLBACK;
	nsec += offset_nsec;
	sec += offset_sec;
	if (nsec >= NSEC_PER_SEC) {
		nsec -= NSEC_PER_SEC;
		sec++;
	}

	value->sec = sec;
	value->nsec = nsec;
	return VKSO_TIME_OK;
}
