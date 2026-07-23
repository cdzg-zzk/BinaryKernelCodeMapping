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
static_assert(offsetof(struct vkso_shared_data, raw) == 104);
static_assert(offsetof(struct vkso_cycle_data, cycle_last) == 8);
static_assert(offsetof(struct vkso_cycle_data, mask) == 16);
static_assert(offsetof(struct vkso_cycle_data, mult) == 24);
static_assert(offsetof(struct vkso_cycle_data, shift) == 28);
static_assert(offsetof(struct vkso_hres_data, realtime_base) == 32);
static_assert(offsetof(struct vkso_hres_data, monotonic_base) == 48);
static_assert(offsetof(struct vkso_raw_data, monotonic_raw_base) == 32);
static_assert(CLOCK_REALTIME == 0);
static_assert(CLOCK_MONOTONIC == CLOCK_REALTIME + 1);
static_assert(CLOCK_MONOTONIC_COARSE == CLOCK_REALTIME_COARSE + 1);
static_assert(offsetof(struct vkso_hres_data, monotonic_base) ==
	      offsetof(struct vkso_hres_data, realtime_base) +
	      sizeof(struct vkso_hres_base));
static_assert(offsetof(struct vkso_shared_data, monotonic_coarse) ==
	      offsetof(struct vkso_shared_data, realtime_coarse) +
	      sizeof(struct vkso_time_value));
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
	s32 clock_mode;
	u64 cycle_last;
	u64 mask;
	u32 mult;
	u32 shift;
	struct vkso_hres_base hres_base;
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

static __always_inline void vkso_hres_from_snapshot(
	const struct vkso_read_snapshot *snapshot, s64 offset_sec,
	u64 offset_nsec, struct vkso_time_value *value)
{
	u64 cycles = snapshot->cycles;
	u64 last = snapshot->cycle_last;
	u64 ns = snapshot->hres_base.shifted_nsec;

	/* Match the x86 vDSO rule: clamp a slightly backward TSC to the base. */
	if (cycles > last)
		ns += (cycles - last) * snapshot->mult;
	ns >>= snapshot->shift;
	ns += offset_nsec;
	value->sec = snapshot->hres_base.sec + offset_sec +
		__iter_div_u64_rem(ns, NSEC_PER_SEC, &ns);
	value->nsec = ns;
}

/*
 * This is the only shared-data transaction.  Callers select either one
 * coarse value by offset or the high-resolution conversion snapshot.
 */
static __always_inline int vkso_read_snapshot(
	const struct vkso_shared_data *shared, size_t value_offset,
	size_t cycle_offset, u32 flags, struct vkso_read_snapshot *snapshot)
{
	const void *selected = (const u8 *)shared + value_offset;
	const struct vkso_time_value *coarse = selected;
	const struct vkso_hres_base *hres_base = selected;
	const struct vkso_cycle_data *cycle_data =
		(const void *)((const u8 *)shared + cycle_offset);
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
			next.clock_mode = READ_ONCE(cycle_data->clock_mode);
			have_cycles = vkso_read_cycles(next.clock_mode,
						       &next.cycles);
			next.cycle_last = READ_ONCE(cycle_data->cycle_last);
			next.mask = READ_ONCE(cycle_data->mask);
			next.mult = READ_ONCE(cycle_data->mult);
			next.shift = READ_ONCE(cycle_data->shift);
			next.hres_base.sec = READ_ONCE(hres_base->sec);
			next.hres_base.shifted_nsec =
				READ_ONCE(hres_base->shifted_nsec);
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
	status = vkso_read_snapshot(shared,
		offsetof(struct vkso_shared_data, hres.realtime_base),
		offsetof(struct vkso_shared_data, hres.cycles),
		VKSO_READ_HRES, &snapshot);
	if (status != VKSO_TIME_OK)
		return status;
	sample->seq = snapshot.seq;
	sample->retries = snapshot.retries;
	sample->clock_mode = snapshot.clock_mode;
	sample->shift = snapshot.shift;
	sample->cycles = snapshot.cycles;
	sample->cycle_last = snapshot.cycle_last;
	sample->mask = snapshot.mask;
	sample->mult = snapshot.mult;
	sample->reserved = 0;
	sample->realtime_base = snapshot.hres_base;
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
	size_t value_offset;
	size_t cycle_offset = 0;
	u32 read_flags;
	u32 id = clock_id;
	s64 offset_sec = 0;
	u64 offset_nsec = 0;
	bool use_mm_data;

	if (!value)
		return VKSO_TIME_FALLBACK;
	if (id <= CLOCK_MONOTONIC) {
		value_offset = offsetof(struct vkso_shared_data,
					 hres.realtime_base) +
			id * sizeof(struct vkso_hres_base);
		cycle_offset = offsetof(struct vkso_shared_data, hres.cycles);
		read_flags = VKSO_READ_HRES;
		use_mm_data = id == CLOCK_MONOTONIC;
	} else if (id == CLOCK_MONOTONIC_RAW) {
		value_offset = offsetof(struct vkso_shared_data,
					 raw.monotonic_raw_base);
		cycle_offset = offsetof(struct vkso_shared_data, raw.cycles);
		read_flags = VKSO_READ_HRES;
		use_mm_data = true;
	} else {
		u32 coarse_index = id - CLOCK_REALTIME_COARSE;

		if (coarse_index >
		    CLOCK_MONOTONIC_COARSE - CLOCK_REALTIME_COARSE)
			return VKSO_TIME_FALLBACK;
		value_offset = offsetof(struct vkso_shared_data,
					 realtime_coarse) +
			coarse_index * sizeof(struct vkso_time_value);
		read_flags = 0;
		use_mm_data = coarse_index != 0;
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
	if (vkso_read_snapshot(vkso_shared_data(), value_offset, cycle_offset,
			       read_flags, &snapshot) != VKSO_TIME_OK)
		return VKSO_TIME_FALLBACK;
	if (read_flags & VKSO_READ_HRES) {
		vkso_hres_from_snapshot(&snapshot, offset_sec, offset_nsec,
					value);
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
