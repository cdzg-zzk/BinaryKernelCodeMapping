/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_TIMEKEEPING_UPDATE_BENCH_H
#define _LINUX_TIMEKEEPING_UPDATE_BENCH_H

#include <linux/types.h>

#ifdef CONFIG_TIMEKEEPING_UPDATE_BENCH
#include <linux/jump_label.h>
#include <asm/msr.h>

extern struct static_key_false timekeeping_update_bench_key;
void timekeeping_update_bench_record(u64 start, u64 end, unsigned int action);

static __always_inline u64 timekeeping_update_bench_start(void)
{
	if (!static_branch_unlikely(&timekeeping_update_bench_key))
		return 0;
	return rdtsc_ordered();
}

static __always_inline void
timekeeping_update_bench_finish(u64 start, unsigned int action)
{
	u64 end;

	if (!start)
		return;
	end = rdtsc_ordered();
	timekeeping_update_bench_record(start, end, action);
}
#else
static inline u64 timekeeping_update_bench_start(void)
{
	return 0;
}

static inline void
timekeeping_update_bench_finish(u64 start, unsigned int action)
{
}
#endif

#endif /* _LINUX_TIMEKEEPING_UPDATE_BENCH_H */
