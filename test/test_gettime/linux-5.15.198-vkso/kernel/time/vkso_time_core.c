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
#include <vdso/math64.h>

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
#ifdef CONFIG_VKSO_TIME_TEST
static_assert(sizeof(struct vkso_hres_cycle_sample) == 64);
#endif
static_assert(offsetof(struct vkso_mm_data, monotonic_offset) == 8);
static_assert(sizeof(union vkso_shared_page) == VKSO_SHARED_PAGE_SIZE);
static_assert(sizeof(union vkso_mm_page) == VKSO_SHARED_PAGE_SIZE);

#define VKSO_READ_HRES	1U

struct vkso_read_snapshot {
	u32 seq;
	u32 retries;
	u32 abi_version;
	struct vkso_time_value coarse;
	struct vkso_hres_data hres;
	u64 cycles;
};

static __always_inline void vkso_count_retry(u32 *retries)
{
	if (*retries != (u32)-1)
		(*retries)++;
}

/*
 * The native counter backend is deliberately inlined into the common reader:
 * there is no callback or indirect branch between the two seq observations.
 */
static __always_inline bool vkso_read_cycles(s32 clock_mode, u64 *cycles)
{
	if (clock_mode != VDSO_CLOCKMODE_TSC)
		return false;
	*cycles = rdtsc_ordered();
	return (s64)*cycles >= 0;
}

static __always_inline void
vkso_realtime_from_snapshot(const struct vkso_read_snapshot *snapshot,
			    struct vkso_time_value *value)
{
	u64 cycles = snapshot->cycles;
	u64 last = snapshot->hres.cycle_last;
	u64 ns = snapshot->hres.realtime_base.shifted_nsec;

	/* Match the x86 vDSO rule: clamp a slightly backward TSC to the base. */
	if (cycles > last)
		ns += (cycles - last) * snapshot->hres.mult;
	ns >>= snapshot->hres.shift;
	value->sec = snapshot->hres.realtime_base.sec +
		__iter_div_u64_rem(ns, NSEC_PER_SEC, &ns);
	value->nsec = ns;
}

/*
 * This is the only shared-data transaction.  Callers select either one
 * coarse value by offset or the high-resolution conversion snapshot.
 */
static __always_inline int vkso_read_snapshot(
	const struct vkso_shared_data *shared, size_t coarse_offset, u32 flags,
	struct vkso_read_snapshot *snapshot)
{
	const struct vkso_time_value *coarse =
		(const void *)((const u8 *)shared + coarse_offset);
	struct vkso_read_snapshot next;
	u32 retries = 0;
	bool have_cycles = true;

	for (;;) {
		next.seq = READ_ONCE(shared->seq);
		if (next.seq & 1) {
			vkso_count_retry(&retries);
			cpu_relax();
			continue;
		}
		smp_rmb();
		next.abi_version = READ_ONCE(shared->abi_version);
		if (flags & VKSO_READ_HRES) {
			next.hres.clock_mode =
				READ_ONCE(shared->hres.clock_mode);
			have_cycles = vkso_read_cycles(next.hres.clock_mode,
						       &next.cycles);
			next.hres.cycle_last =
				READ_ONCE(shared->hres.cycle_last);
			next.hres.mask = READ_ONCE(shared->hres.mask);
			next.hres.mult = READ_ONCE(shared->hres.mult);
			next.hres.shift = READ_ONCE(shared->hres.shift);
			next.hres.realtime_base.sec =
				READ_ONCE(shared->hres.realtime_base.sec);
			next.hres.realtime_base.shifted_nsec =
				READ_ONCE(
					shared->hres.realtime_base.shifted_nsec);
		} else {
			next.coarse.sec = READ_ONCE(coarse->sec);
			next.coarse.nsec = READ_ONCE(coarse->nsec);
		}
		smp_rmb();
		if (next.seq == READ_ONCE(shared->seq))
			break;
		vkso_count_retry(&retries);
	}

	if (next.abi_version != VKSO_TIME_ABI_VERSION || !have_cycles ||
	    (!(flags & VKSO_READ_HRES) && next.coarse.nsec >= NSEC_PER_SEC))
		return VKSO_TIME_FALLBACK;
	next.retries = retries;
	*snapshot = next;
	return VKSO_TIME_OK;
}

static __always_inline const struct vkso_shared_data *vkso_shared_data(void)
{
	const struct vkso_shared_data *shared;

	asm("lea vkso_shared_page(%%rip), %0" : "=r" (shared));
	return shared;
}

#ifdef CONFIG_VKSO_TIME_TEST
static __always_inline int vkso_hres_sample(
	const struct vkso_shared_data *shared,
	struct vkso_hres_cycle_sample *sample)
{
	struct vkso_read_snapshot snapshot;
	int status;

	if (!shared || !sample)
		return VKSO_TIME_FALLBACK;
	status = vkso_read_snapshot(shared, 0, VKSO_READ_HRES, &snapshot);
	if (status != VKSO_TIME_OK)
		return status;
	sample->seq = snapshot.seq;
	sample->retries = snapshot.retries;
	sample->clock_mode = snapshot.hres.clock_mode;
	sample->shift = snapshot.hres.shift;
	sample->cycles = snapshot.cycles;
	sample->cycle_last = snapshot.hres.cycle_last;
	sample->mask = snapshot.hres.mask;
	sample->mult = snapshot.hres.mult;
	sample->reserved = 0;
	sample->realtime_base = snapshot.hres.realtime_base;
	return VKSO_TIME_OK;
}

__visible noinline notrace __vkso_text
int __vkso_test_hres_cycle_probe_at(
	const struct vkso_shared_data *shared,
	struct vkso_hres_cycle_sample *sample)
{
	return vkso_hres_sample(shared, sample);
}
#endif

__visible noinline notrace __vkso_text
int __vkso_clock_gettime(const struct vkso_mm_data *mm_data, int clock_id,
			 struct vkso_time_value *value)
{
	struct vkso_read_snapshot snapshot;
	size_t coarse_offset;
	u32 read_flags;
	s64 offset_sec = 0;
	u64 offset_nsec = 0;
	bool use_mm_data;

	if (!value)
		return VKSO_TIME_FALLBACK;
	switch (clock_id) {
	case CLOCK_REALTIME:
		coarse_offset = 0;
		read_flags = VKSO_READ_HRES;
		use_mm_data = false;
		break;
	case CLOCK_REALTIME_COARSE:
		coarse_offset = offsetof(struct vkso_shared_data,
					 realtime_coarse);
		read_flags = 0;
		use_mm_data = false;
		break;
	case CLOCK_MONOTONIC_COARSE:
		coarse_offset = offsetof(struct vkso_shared_data,
					 monotonic_coarse);
		read_flags = 0;
		use_mm_data = true;
		break;
	default:
		return VKSO_TIME_FALLBACK;
	}
	if (use_mm_data) {
		if (!mm_data ||
		    READ_ONCE(mm_data->abi_version) !=
			    VKSO_MM_DATA_ABI_VERSION)
			return VKSO_TIME_FALLBACK;
		offset_sec = READ_ONCE(mm_data->monotonic_offset.sec);
		offset_nsec = READ_ONCE(mm_data->monotonic_offset.nsec);
		if (offset_nsec >= NSEC_PER_SEC)
			return VKSO_TIME_FALLBACK;
	}
	if (vkso_read_snapshot(vkso_shared_data(), coarse_offset, read_flags,
			       &snapshot) != VKSO_TIME_OK)
		return VKSO_TIME_FALLBACK;
	if (read_flags & VKSO_READ_HRES) {
		vkso_realtime_from_snapshot(&snapshot, value);
		return VKSO_TIME_OK;
	}
	snapshot.coarse.nsec += offset_nsec;
	snapshot.coarse.sec += offset_sec;
	if (snapshot.coarse.nsec >= NSEC_PER_SEC) {
		snapshot.coarse.nsec -= NSEC_PER_SEC;
		snapshot.coarse.sec++;
	}
	*value = snapshot.coarse;
	return VKSO_TIME_OK;
}
