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
#include <vdso/ktime.h>
#include <vdso/math64.h>

/* Keep the binary contract explicit before executable interfaces are added. */
static_assert(sizeof(struct vkso_time_value) == 16);
static_assert(offsetof(struct vkso_time_value, sec) == 0);
static_assert(offsetof(struct vkso_time_value, nsec) == 8);
static_assert(offsetof(struct vkso_shared_data, realtime_coarse) == 8);
static_assert(offsetof(struct vkso_shared_data, monotonic_coarse) == 24);
static_assert(offsetof(struct vkso_shared_data, hres) == 40);
static_assert(offsetof(struct vkso_shared_data, raw) == 136);
static_assert(offsetof(struct vkso_shared_data, hrtimer_resolution) == 184);
static_assert(offsetof(struct vkso_cycle_data, cycle_last) == 8);
static_assert(offsetof(struct vkso_cycle_data, mask) == 16);
static_assert(offsetof(struct vkso_cycle_data, mult) == 24);
static_assert(offsetof(struct vkso_cycle_data, shift) == 28);
static_assert(offsetof(struct vkso_hres_data, realtime_base) == 32);
static_assert(offsetof(struct vkso_hres_data, monotonic_base) == 48);
static_assert(offsetof(struct vkso_hres_data, boottime_base) == 64);
static_assert(offsetof(struct vkso_hres_data, tai_base) == 80);
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
static_assert(offsetof(struct vkso_mm_data, boottime_offset) == 24);
static_assert(sizeof(union vkso_shared_page) == VKSO_SHARED_PAGE_SIZE);
static_assert(sizeof(union vkso_mm_page) == VKSO_SHARED_PAGE_SIZE);

struct vkso_hres_snapshot {
#ifdef CONFIG_VKSO_TIME_TEST
	u32 seq;
	u32 retries;
	s32 clock_mode;
	u64 mask;
#endif
	struct vkso_hres_base base;
	u64 cycle_last;
	u32 mult;
	u32 shift;
	u64 cycles;
};

#ifdef CONFIG_VKSO_TIME_TEST
static __always_inline void
vkso_count_retry(struct vkso_hres_snapshot *snapshot)
{
	if (snapshot->retries != (u32)-1)
		snapshot->retries++;
}
#else
#define vkso_count_retry(snapshot) do { } while (0)
#endif

static __always_inline u32 vkso_read_begin(
	const struct vkso_shared_data *shared,
	struct vkso_hres_snapshot *snapshot)
{
	u32 seq;

	while (unlikely((seq = READ_ONCE(shared->seq)) & 1)) {
		if (snapshot)
			vkso_count_retry(snapshot);
		cpu_relax();
	}
	/* Keep payload loads between the two seq observations. */
	smp_rmb();
	return seq;
}

static __always_inline bool vkso_read_retry(
	const struct vkso_shared_data *shared, u32 seq)
{
	/* Complete payload loads before validating seq. */
	smp_rmb();
	return unlikely(seq != READ_ONCE(shared->seq));
}

/*
 * The native counter backend is deliberately inlined into the common reader:
 * there is no callback or indirect branch between the two seq observations.
 */
static __always_inline bool vkso_read_cycles(s32 clock_mode, u64 *cycles)
{
	if (unlikely(clock_mode != VDSO_CLOCKMODE_TSC))
		return false;
	*cycles = rdtsc_ordered();
	return (s64)*cycles >= 0;
}

static __always_inline void vkso_hres_from_snapshot(
	const struct vkso_hres_snapshot *snapshot, s64 offset_sec,
	u64 offset_nsec, struct vkso_time_value *value)
{
	u64 cycles = snapshot->cycles;
	u64 last = snapshot->cycle_last;
	u64 ns = snapshot->base.shifted_nsec;

	/* Match the x86 vDSO rule: clamp a slightly backward TSC to the base. */
	if (cycles > last)
		ns += (cycles - last) * snapshot->mult;
	ns >>= snapshot->shift;
	ns += offset_nsec;
	value->sec = snapshot->base.sec + offset_sec +
		__iter_div_u64_rem(ns, NSEC_PER_SEC, &ns);
	value->nsec = ns;
}

static __always_inline int vkso_read_hres(
	const struct vkso_shared_data *shared, size_t value_offset,
	size_t cycle_offset, struct vkso_hres_snapshot *snapshot)
{
	const struct vkso_hres_base *base =
		(const void *)((const u8 *)shared + value_offset);
	const struct vkso_cycle_data *cycle_data =
		(const void *)((const u8 *)shared + cycle_offset);
	struct vkso_hres_snapshot next;
	u32 seq;
	s32 clock_mode;

#ifdef CONFIG_VKSO_TIME_TEST
	next.retries = 0;
#endif
	for (;;) {
		seq = vkso_read_begin(shared, &next);
		if (unlikely(READ_ONCE(shared->abi_version) !=
			     VKSO_TIME_ABI_VERSION))
			return VKSO_TIME_FALLBACK;
		clock_mode = READ_ONCE(cycle_data->clock_mode);
		if (unlikely(!vkso_read_cycles(clock_mode, &next.cycles)))
			return VKSO_TIME_FALLBACK;
		next.cycle_last = READ_ONCE(cycle_data->cycle_last);
#ifdef CONFIG_VKSO_TIME_TEST
		next.clock_mode = clock_mode;
		next.mask = READ_ONCE(cycle_data->mask);
#endif
		next.mult = READ_ONCE(cycle_data->mult);
		next.shift = READ_ONCE(cycle_data->shift);
		next.base.sec = READ_ONCE(base->sec);
		next.base.shifted_nsec = READ_ONCE(base->shifted_nsec);
		if (!vkso_read_retry(shared, seq))
			break;
		vkso_count_retry(&next);
	}

#ifdef CONFIG_VKSO_TIME_TEST
	next.seq = seq;
#endif
	*snapshot = next;
	return VKSO_TIME_OK;
}

static __always_inline int vkso_read_coarse(
	const struct vkso_shared_data *shared, size_t value_offset,
	struct vkso_time_value *value)
{
	const struct vkso_time_value *base =
		(const void *)((const u8 *)shared + value_offset);
	struct vkso_time_value next;
	u32 seq;

	for (;;) {
		seq = vkso_read_begin(shared, NULL);
		if (unlikely(READ_ONCE(shared->abi_version) !=
			     VKSO_TIME_ABI_VERSION))
			return VKSO_TIME_FALLBACK;
		next.sec = READ_ONCE(base->sec);
		next.nsec = READ_ONCE(base->nsec);
		if (!vkso_read_retry(shared, seq))
			break;
	}
	*value = next;
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
	struct vkso_hres_snapshot snapshot;
	int status;

	if (!shared || !sample)
		return VKSO_TIME_FALLBACK;
	status = vkso_read_hres(shared,
		offsetof(struct vkso_shared_data, hres.realtime_base),
		offsetof(struct vkso_shared_data, hres.cycles),
		&snapshot);
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
	sample->realtime_base = snapshot.base;
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
	const struct vkso_shared_data *shared;
	struct vkso_hres_snapshot snapshot;
	struct vkso_time_value coarse;
	size_t value_offset;
	size_t cycle_offset = 0;
	size_t mm_offset = 0;
	u32 id = clock_id;
	s64 offset_sec = 0;
	u64 offset_nsec = 0;
	bool high_resolution;

	if (likely(id <= CLOCK_MONOTONIC)) {
		value_offset = offsetof(struct vkso_shared_data,
					 hres.realtime_base) +
			id * sizeof(struct vkso_hres_base);
		cycle_offset = offsetof(struct vkso_shared_data, hres.cycles);
		high_resolution = true;
		if (id == CLOCK_MONOTONIC)
			mm_offset = offsetof(struct vkso_mm_data,
					     monotonic_offset);
	} else if (id == CLOCK_MONOTONIC_RAW) {
		value_offset = offsetof(struct vkso_shared_data,
					 raw.monotonic_raw_base);
		cycle_offset = offsetof(struct vkso_shared_data, raw.cycles);
		high_resolution = true;
		mm_offset = offsetof(struct vkso_mm_data, monotonic_offset);
	} else if (id == CLOCK_BOOTTIME) {
		value_offset = offsetof(struct vkso_shared_data,
					hres.boottime_base);
		cycle_offset = offsetof(struct vkso_shared_data, hres.cycles);
		high_resolution = true;
		mm_offset = offsetof(struct vkso_mm_data, boottime_offset);
	} else if (id == CLOCK_TAI) {
		value_offset = offsetof(struct vkso_shared_data, hres.tai_base);
		cycle_offset = offsetof(struct vkso_shared_data, hres.cycles);
		high_resolution = true;
	} else {
		u32 coarse_index = id - CLOCK_REALTIME_COARSE;

		if (coarse_index >
		    CLOCK_MONOTONIC_COARSE - CLOCK_REALTIME_COARSE)
			return VKSO_TIME_FALLBACK;
		value_offset = offsetof(struct vkso_shared_data,
					 realtime_coarse) +
			coarse_index * sizeof(struct vkso_time_value);
		high_resolution = false;
		if (coarse_index)
			mm_offset = offsetof(struct vkso_mm_data,
					     monotonic_offset);
	}
	if (mm_offset) {
		const struct vkso_time_value *offset;

		if (unlikely(!mm_data ||
			     READ_ONCE(mm_data->abi_version) !=
			     VKSO_MM_DATA_ABI_VERSION))
			return VKSO_TIME_FALLBACK;
		offset = (const void *)((const u8 *)mm_data + mm_offset);
		offset_sec = READ_ONCE(offset->sec);
		offset_nsec = READ_ONCE(offset->nsec);
	}
	shared = vkso_shared_data();
	if (high_resolution) {
		if (vkso_read_hres(shared, value_offset, cycle_offset,
				   &snapshot) != VKSO_TIME_OK)
			return VKSO_TIME_FALLBACK;
		vkso_hres_from_snapshot(&snapshot, offset_sec, offset_nsec,
					value);
		return VKSO_TIME_OK;
	}
	if (vkso_read_coarse(shared, value_offset, &coarse) != VKSO_TIME_OK)
		return VKSO_TIME_FALLBACK;
	coarse.nsec += offset_nsec;
	coarse.sec += offset_sec;
	if (coarse.nsec >= NSEC_PER_SEC) {
		coarse.nsec -= NSEC_PER_SEC;
		coarse.sec++;
	}
	*value = coarse;
	return VKSO_TIME_OK;
}

__visible noinline notrace __vkso_text
int __vkso_clock_getres(int clock_id, struct vkso_time_value *value)
{
	const u32 hres_clocks = (1U << CLOCK_REALTIME) |
		(1U << CLOCK_MONOTONIC) | (1U << CLOCK_MONOTONIC_RAW) |
		(1U << CLOCK_BOOTTIME) | (1U << CLOCK_TAI);
	const u32 coarse_clocks = (1U << CLOCK_REALTIME_COARSE) |
		(1U << CLOCK_MONOTONIC_COARSE);
	const struct vkso_shared_data *shared;
	u32 id = clock_id;
	u32 mask;
	u32 resolution;

	if (id > CLOCK_TAI)
		return VKSO_TIME_FALLBACK;
	mask = 1U << id;
	if (mask & hres_clocks) {
		shared = vkso_shared_data();
		if (unlikely(READ_ONCE(shared->abi_version) !=
			     VKSO_TIME_ABI_VERSION))
			return VKSO_TIME_FALLBACK;
		resolution = READ_ONCE(shared->hrtimer_resolution);
	} else if (mask & coarse_clocks) {
		resolution = LOW_RES_NSEC;
	} else {
		return VKSO_TIME_FALLBACK;
	}
	if (value) {
		value->sec = 0;
		value->nsec = resolution;
	}
	return VKSO_TIME_OK;
}
