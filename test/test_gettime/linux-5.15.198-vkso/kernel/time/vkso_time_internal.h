/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _KERNEL_TIME_VKSO_TIME_INTERNAL_H
#define _KERNEL_TIME_VKSO_TIME_INTERNAL_H

#include <linux/compiler.h>
#include <linux/time.h>
#include <linux/vkso_time.h>

#include <asm/clocksource.h>
#include <asm/msr.h>

#include <vdso/clocksource.h>
#include <vdso/ktime.h>
#include <vdso/math64.h>

struct vkso_hres_snapshot {
#ifdef CONFIG_VKSO_TIME_TEST
	u32 seq;
	u32 retries;
	s32 clock_mode;
#endif
	struct vkso_hres_base base;
	u64 cycle_last;
	u32 mult;
	u32 shift;
	u64 cycles;
};

#ifdef CONFIG_PARAVIRT_CLOCK
bool vkso_read_pvclock_cycles(const void *page, u64 *cycles);
#endif
#ifdef CONFIG_HYPERV_TIMER
bool vkso_read_hvclock_cycles(const void *page, u64 *cycles);
#endif

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
 * TSC stays inline and does not touch cycle_context. PV/HV are deliberately
 * out-of-line cold paths, reached by direct calls within .vkso.text.
 */
static __always_inline bool
vkso_read_cycles(const struct vkso_cycle_context *cycle_context,
		 s32 clock_mode, u64 *cycles)
{
	if (likely(clock_mode == VDSO_CLOCKMODE_TSC)) {
		*cycles = rdtsc_ordered();
		return (s64)*cycles >= 0;
	}
#ifdef CONFIG_PARAVIRT_CLOCK
	if (clock_mode == VDSO_CLOCKMODE_PVCLOCK) {
		barrier();
		return cycle_context &&
			vkso_read_pvclock_cycles(cycle_context->pvclock_page,
						cycles);
	}
#endif
#ifdef CONFIG_HYPERV_TIMER
	if (clock_mode == VDSO_CLOCKMODE_HVCLOCK) {
		barrier();
		return cycle_context &&
			vkso_read_hvclock_cycles(cycle_context->hvclock_page,
						cycles);
	}
#endif
	return false;
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
	size_t cycle_offset, const struct vkso_cycle_context *cycle_context,
	struct vkso_hres_snapshot *snapshot)
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
		clock_mode = READ_ONCE(cycle_data->clock_mode);
		if (unlikely(!vkso_read_cycles(cycle_context, clock_mode,
					      &next.cycles)))
			return VKSO_TIME_FALLBACK;
		next.cycle_last = READ_ONCE(cycle_data->cycle_last);
#ifdef CONFIG_VKSO_TIME_TEST
		next.clock_mode = clock_mode;
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

#endif /* _KERNEL_TIME_VKSO_TIME_INTERNAL_H */
