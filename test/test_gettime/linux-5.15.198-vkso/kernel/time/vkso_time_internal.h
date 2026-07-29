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

#ifdef CONFIG_VKSO_TIME_TEST
struct vkso_hres_snapshot {
	u32 seq;
	u32 retries;
	s32 clock_mode;
	struct vkso_hres_base base;
	u64 cycle_last;
	u32 mult;
	u32 shift;
	u64 cycles;
};

static __always_inline void
vkso_count_retry(struct vkso_hres_snapshot *snapshot)
{
	if (snapshot->retries != (u32)-1)
		snapshot->retries++;
}
#endif

s64 vkso_cycles_read_cold(const struct vkso_context *context,
			  s32 clock_mode);

static __always_inline u32
vkso_read_begin(const struct vkso_shared_data *shared)
{
	u32 seq;

	while (unlikely((seq = READ_ONCE(shared->seq)) & 1)) {
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
 * TSC stays inline and does not touch context. PV/HV are deliberately
 * out-of-line cold paths, reached by direct calls within .vkso.text.
 */
static __always_inline s64
vkso_cycles_read(const struct vkso_context *context, s32 clock_mode)
{
	if (likely(clock_mode == VDSO_CLOCKMODE_TSC))
		return rdtsc_ordered();
	barrier();
	return vkso_cycles_read_cold(context, clock_mode);
}

/*
 * All x86 clocks exported to userspace currently have a U64_MAX mask.  Clamp
 * their rare backward observation exactly as the native x86 vDSO does.  The
 * finite-mask case retains the generic clocksource wrap rule, which keeps the
 * canonical state expressive without charging the common x86 path an
 * unnecessary mask operation.
 */
static __always_inline u64
vkso_cycle_delta(u64 cycles, u64 cycle_last, u64 mask)
{
	if (likely(mask == U64_MAX)) {
		if (likely(cycles > cycle_last))
			return cycles - cycle_last;
		return 0;
	}
	return (cycles - cycle_last) & mask;
}

/*
 * Read and convert in one inlined operation.  Keeping an intermediate
 * snapshot forced the production build to spill every field to the stack
 * and reload it after the seq check.
 */
static __always_inline int
vkso_read_hres_time(const struct vkso_shared_data *shared,
		    const struct vkso_hres_base *base,
		    const struct vkso_cycle_data *cycle_data,
		    const u32 *multiplier,
		    const struct vkso_context *context,
		    struct vkso_time_value *value)
{
	u64 cycles, cycle_last, mask, ns;
	s64 sec;
	u32 mult, shift;
	u32 seq;
	s32 clock_mode;

	for (;;) {
		seq = vkso_read_begin(shared);
		clock_mode = READ_ONCE(cycle_data->clock_mode);
		cycles = vkso_cycles_read(context, clock_mode);
		if (unlikely((s64)cycles < 0))
			return VKSO_TIME_UNSUPPORTED_MODE;
		cycle_last = READ_ONCE(cycle_data->cycle_last);
		mask = READ_ONCE(cycle_data->mask);
		mult = READ_ONCE(*multiplier);
		ns = READ_ONCE(base->shifted_nsec);
		ns += vkso_cycle_delta(cycles, cycle_last, mask) * mult;
		shift = READ_ONCE(cycle_data->shift);
		sec = READ_ONCE(base->sec);
		if (!vkso_read_retry(shared, seq))
			break;
	}

	ns >>= shift;
	value->sec = sec + __iter_div_u64_rem(ns, NSEC_PER_SEC, &ns);
	value->nsec = ns;
	return VKSO_TIME_OK;
}

static __always_inline void
vkso_apply_offset(const struct vkso_time_value *offset,
		  struct vkso_time_value *value)
{
	u64 nsec = value->nsec + READ_ONCE(offset->nsec);
	s64 sec = value->sec + READ_ONCE(offset->sec);

	if (nsec >= NSEC_PER_SEC) {
		nsec -= NSEC_PER_SEC;
		sec++;
	}
	value->sec = sec;
	value->nsec = nsec;
}

#ifdef CONFIG_VKSO_TIME_TEST
static __always_inline int
vkso_read_hres_sample(const struct vkso_shared_data *shared,
		      size_t value_offset, size_t cycle_offset,
		      size_t mult_offset,
		      const struct vkso_context *context,
		      struct vkso_hres_snapshot *snapshot)
{
	const struct vkso_hres_base *base =
		(const void *)((const u8 *)shared + value_offset);
	const struct vkso_cycle_data *cycle_data =
		(const void *)((const u8 *)shared + cycle_offset);
	const u32 *multiplier =
		(const void *)((const u8 *)shared + mult_offset);
	struct vkso_hres_snapshot next = { .retries = 0 };
	u32 seq;

	for (;;) {
		while (unlikely((seq = READ_ONCE(shared->seq)) & 1)) {
			vkso_count_retry(&next);
			cpu_relax();
		}
		/* Keep payload loads between the two seq observations. */
		smp_rmb();
		next.clock_mode = READ_ONCE(cycle_data->clock_mode);
		next.cycles = vkso_cycles_read(context, next.clock_mode);
		if (unlikely((s64)next.cycles < 0))
			return VKSO_TIME_UNSUPPORTED_MODE;
		next.cycle_last = READ_ONCE(cycle_data->cycle_last);
		next.mult = READ_ONCE(*multiplier);
		next.shift = READ_ONCE(cycle_data->shift);
		next.base.sec = READ_ONCE(base->sec);
		next.base.shifted_nsec = READ_ONCE(base->shifted_nsec);
		if (!vkso_read_retry(shared, seq))
			break;
		vkso_count_retry(&next);
	}
	next.seq = seq;
	*snapshot = next;
	return VKSO_TIME_OK;
}
#endif

static __always_inline void
vkso_read_coarse(const struct vkso_shared_data *shared,
		 const struct vkso_time_value *base,
		 struct vkso_time_value *value)
{
	struct vkso_time_value next;
	u32 seq;

	for (;;) {
		seq = vkso_read_begin(shared);
		next.sec = READ_ONCE(base->sec);
		next.nsec = READ_ONCE(base->nsec);
		if (!vkso_read_retry(shared, seq))
			break;
	}
	*value = next;
}

static __always_inline const struct vkso_shared_data *vkso_shared_data(void)
{
	const struct vkso_shared_data *shared;

	asm("lea vkso_shared_page(%%rip), %0" : "=r" (shared));
	return shared;
}

#endif /* _KERNEL_TIME_VKSO_TIME_INTERNAL_H */
