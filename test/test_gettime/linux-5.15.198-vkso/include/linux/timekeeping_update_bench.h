/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_TIMEKEEPING_UPDATE_BENCH_H
#define _LINUX_TIMEKEEPING_UPDATE_BENCH_H

#include <linux/types.h>

struct timekeeper;

#define TIMEKEEPING_UPDATE_BENCH_STAGE_MARKS 7
#define TIMEKEEPING_UPDATE_BENCH_STAGE_PARTS 8

struct timekeeping_update_bench_stages {
	u64 marks[TIMEKEEPING_UPDATE_BENCH_STAGE_MARKS];
};

#ifdef CONFIG_TIMEKEEPING_UPDATE_BENCH
#include <linux/jump_label.h>
#include <asm/msr.h>

extern struct static_key_false timekeeping_update_bench_key;
void timekeeping_update_bench_record(u64 start, u64 end, unsigned int action,
				     const struct timekeeper *tk,
				     const struct timekeeping_update_bench_stages *stages);
#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
#include <linux/build_bug.h>
extern struct static_key_false timekeeping_update_bench_order_swap_key;
void timekeeping_update_bench_prepare(void *fast_raw);
#endif

#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
struct timekeeping_update_bench_pmu_snapshot {
	u64 hit;
	u64 miss;
	bool valid;
};
void timekeeping_update_bench_pmu_before(
		struct timekeeping_update_bench_pmu_snapshot *snapshot);
void timekeeping_update_bench_pmu_record(u64 start, u64 end,
		unsigned int action, const struct timekeeper *tk,
		const struct timekeeping_update_bench_stages *stages,
		const struct timekeeping_update_bench_pmu_snapshot *before);
#endif

#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
extern struct static_key_false timekeeping_update_bench_stage_key;
extern u32 timekeeping_update_bench_stage_mask;

static __always_inline void timekeeping_update_bench_stage_mark(
		struct timekeeping_update_bench_stages *stages, unsigned int part)
{
	if (static_branch_unlikely(&timekeeping_update_bench_stage_key) &&
	    (READ_ONCE(timekeeping_update_bench_stage_mask) & (1U << part)))
		stages->marks[part] = rdtsc_ordered();
}
#endif

static __always_inline u64 timekeeping_update_bench_start(void)
{
	if (!static_branch_unlikely(&timekeeping_update_bench_key))
		return 0;
	return rdtsc_ordered();
}

static __always_inline void
timekeeping_update_bench_finish(u64 start, unsigned int action,
				const struct timekeeper *tk,
				const struct timekeeping_update_bench_stages *stages)
{
	u64 end;

	if (!start)
		return;
	end = rdtsc_ordered();
	timekeeping_update_bench_record(start, end, action, tk, stages);
}
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
static __always_inline void
timekeeping_update_bench_pmu_finish(u64 start, unsigned int action,
				    const struct timekeeper *tk,
				    const struct timekeeping_update_bench_stages *stages,
				    const struct timekeeping_update_bench_pmu_snapshot *before)
{
	u64 end;

	if (!start)
		return;
	end = rdtsc_ordered();
	timekeeping_update_bench_pmu_record(start, end, action, tk, stages,
					   before);
}
#endif
#else
static inline u64 timekeeping_update_bench_start(void)
{
	return 0;
}

static inline void
timekeeping_update_bench_finish(u64 start, unsigned int action,
				const struct timekeeper *tk,
				const struct timekeeping_update_bench_stages *stages)
{
}
#endif

#endif /* _LINUX_TIMEKEEPING_UPDATE_BENCH_H */
