// SPDX-License-Identifier: GPL-2.0

#include <linux/build_bug.h>
#include <linux/init.h>
#include <linux/irqflags.h>
#include <linux/ktime.h>
#include <linux/printk.h>
#include <linux/stddef.h>

#include "vkso_time_internal.h"

static_assert(sizeof(struct vkso_hres_cycle_sample) == 56);

static __always_inline int vkso_hres_sample(
	const struct vkso_shared_data *shared,
	struct vkso_hres_cycle_sample *sample)
{
	struct vkso_hres_snapshot snapshot;
	const size_t base_offset =
		offsetof(struct vkso_shared_data, state.realtime_base);
	const size_t cycle_offset =
		offsetof(struct vkso_shared_data, state.cycles);
	const size_t mult_offset =
		offsetof(struct vkso_shared_data, state.cycles.mono_mult);
	int status;

	if (!shared || !sample)
		return VKSO_TIME_BACKEND_REQUIRED;
	status = vkso_read_hres_sample(shared, base_offset, cycle_offset,
				       mult_offset, NULL, &snapshot);
	if (status != VKSO_TIME_OK)
		return status;
	sample->seq = snapshot.seq;
	sample->retries = snapshot.retries;
	sample->clock_mode = snapshot.clock_mode;
	sample->shift = snapshot.shift;
	sample->cycles = snapshot.cycles;
	sample->cycle_last = snapshot.cycle_last;
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

static int __init vkso_cycle_delta_selftest(void)
{
	if (vkso_cycle_delta(105, 100, U64_MAX) != 5 ||
	    vkso_cycle_delta(95, 100, U64_MAX) != 0 ||
	    vkso_cycle_delta(3, 0xfe, 0xff) != 5) {
		pr_err("VKSO cycle-delta selftest failed\n");
		return -EINVAL;
	}
	pr_info("VKSO cycle-delta selftest passed\n");
	return 0;
}
late_initcall(vkso_cycle_delta_selftest);

static __always_inline bool
vkso_test_normalized(const struct timespec64 *value)
{
	return value->tv_nsec >= 0 && value->tv_nsec < NSEC_PER_SEC;
}

static int __init vkso_kernel_reader_selftest(void)
{
	struct timespec64 real, monotonic, raw, boot, tai;
	struct timespec64 coarse_real, coarse_monotonic;
	unsigned long flags;
	u64 irq_first, irq_second, fast;
	time64_t seconds;

	ktime_get_real_ts64(&real);
	ktime_get_ts64(&monotonic);
	ktime_get_raw_ts64(&raw);
	ktime_get_boottime_ts64(&boot);
	ktime_get_clocktai_ts64(&tai);
	ktime_get_coarse_real_ts64(&coarse_real);
	ktime_get_coarse_ts64(&coarse_monotonic);
	seconds = ktime_get_seconds();

	if (!vkso_test_normalized(&real) ||
	    !vkso_test_normalized(&monotonic) ||
	    !vkso_test_normalized(&raw) ||
	    !vkso_test_normalized(&boot) ||
	    !vkso_test_normalized(&tai) ||
	    !vkso_test_normalized(&coarse_real) ||
	    !vkso_test_normalized(&coarse_monotonic) ||
	    boot.tv_sec < monotonic.tv_sec ||
	    seconds < coarse_monotonic.tv_sec ||
	    seconds > coarse_monotonic.tv_sec + 1 ||
	    !ktime_get_resolution_ns()) {
		pr_err("VKSO kernel-reader selftest failed\n");
		return -EINVAL;
	}

	local_irq_save(flags);
	irq_first = ktime_get_ns();
	irq_second = ktime_get_ns();
	local_irq_restore(flags);
	fast = ktime_get_mono_fast_ns();
	if (irq_second < irq_first || !fast) {
		pr_err("VKSO kernel-reader IRQ/fast selftest failed\n");
		return -EINVAL;
	}

	pr_info("VKSO kernel-reader selftest passed\n");
	return 0;
}
late_initcall(vkso_kernel_reader_selftest);
