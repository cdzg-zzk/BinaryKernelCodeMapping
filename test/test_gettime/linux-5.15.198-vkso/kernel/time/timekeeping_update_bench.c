// SPDX-License-Identifier: GPL-2.0
/* Test-only recorder for complete timekeeping_update() latency. */
#include <linux/debugfs.h>
#include <linux/cache.h>
#include <linux/fs.h>
#include <linux/init.h>
#include <linux/jump_label.h>
#include <linux/mutex.h>
#include <linux/perf_event.h>
#include <linux/preempt.h>
#include <linux/rcupdate.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <linux/timekeeper_internal.h>
#include <linux/timekeeping_update_bench.h>
#include <linux/uaccess.h>
#include <linux/vmalloc.h>

#include <asm/msr.h>
#include <asm/perf_event.h>
#include <asm/processor.h>

#define TK_UPDATE_BENCH_MAX_SAMPLES	65536U
#define TK_UPDATE_BENCH_CALIBRATION	4096U

struct tk_update_bench_sample {
	u64 cycles;
	u32 action;
	u32 cpu;
};

/* Allocated only for diagnose, leaving the formal recorder at 16 B/sample. */
struct tk_update_bench_diag_state {
	u64 start_tsc;
	u32 phase_nsec;
	u8 ktime_carry;
	u8 realtime_carry;
	u8 monotonic_carry;
	u8 leap_pending;
	u32 clock_mode;
	u32 shift;
};

DEFINE_STATIC_KEY_FALSE(timekeeping_update_bench_key);
static u64 tk_update_bench_seen;
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
DEFINE_STATIC_KEY_FALSE(timekeeping_update_bench_pmu_key);
#define TK_UPDATE_BENCH_RFO_HIT	0xc224ULL
#define TK_UPDATE_BENCH_RFO_MISS	0x2224ULL
struct tk_update_bench_pmu_sample {
	u32 hit;
	u32 miss;
	u8 valid;
};
static struct tk_update_bench_pmu_sample *tk_update_bench_pmu_samples;
static struct perf_event *tk_update_bench_pmu_hit;
static struct perf_event *tk_update_bench_pmu_miss;
static int tk_update_bench_pmu_hit_index = -1;
static int tk_update_bench_pmu_miss_index = -1;
static u64 tk_update_bench_pmu_mask;
static bool tk_update_bench_pmu_active;
static bool tk_update_bench_pmu_window_valid;
static u64 tk_update_bench_pmu_hit_running;
static u64 tk_update_bench_pmu_miss_running;

void timekeeping_update_bench_pmu_before(
		struct timekeeping_update_bench_pmu_snapshot *snapshot)
{
	snapshot->valid = false;
	if (!static_branch_unlikely(&timekeeping_update_bench_pmu_key) ||
	    raw_smp_processor_id() != 0)
		return;
	lockdep_assert_irqs_disabled();
	rdpmcl(tk_update_bench_pmu_hit_index, snapshot->hit);
	rdpmcl(tk_update_bench_pmu_miss_index, snapshot->miss);
	rmb();
	snapshot->valid = true;
}

void timekeeping_update_bench_pmu_record(u64 start, u64 end,
		unsigned int action, const struct timekeeper *tk,
		const struct timekeeping_update_bench_stages *stages,
		const struct timekeeping_update_bench_pmu_snapshot *before)
{
	u64 index = tk_update_bench_seen;
	u64 hit = 0, miss = 0;
	bool valid = before->valid;

	if (valid) {
		rmb();
		rdpmcl(tk_update_bench_pmu_hit_index, hit);
		rdpmcl(tk_update_bench_pmu_miss_index, miss);
		rmb();
		hit = (hit - before->hit) & tk_update_bench_pmu_mask;
		miss = (miss - before->miss) & tk_update_bench_pmu_mask;
		valid = hit <= 1024 && miss <= 1024;
	}
	timekeeping_update_bench_record(start, end, action, tk, stages);
	if (tk_update_bench_pmu_active && index < TK_UPDATE_BENCH_MAX_SAMPLES) {
		struct tk_update_bench_pmu_sample *sample =
			&tk_update_bench_pmu_samples[index];

		sample->hit = valid ? hit : 0;
		sample->miss = valid ? miss : 0;
		sample->valid = valid;
	}
}

static void tk_update_bench_pmu_release(void)
{
	if (tk_update_bench_pmu_hit) {
		perf_event_release_kernel(tk_update_bench_pmu_hit);
		tk_update_bench_pmu_hit = NULL;
	}
	if (tk_update_bench_pmu_miss) {
		perf_event_release_kernel(tk_update_bench_pmu_miss);
		tk_update_bench_pmu_miss = NULL;
	}
}

static void tk_update_bench_pmu_validate(void)
{
	unsigned long flags;
	u64 value, hit_enabled, miss_enabled;
	int hit_ret, miss_ret;

	tk_update_bench_pmu_window_valid = false;
	if (get_cpu() != 0) {
		put_cpu();
		return;
	}
	local_irq_save(flags);
	hit_ret = perf_event_read_local(tk_update_bench_pmu_hit, &value,
			&hit_enabled, &tk_update_bench_pmu_hit_running);
	miss_ret = perf_event_read_local(tk_update_bench_pmu_miss, &value,
			&miss_enabled, &tk_update_bench_pmu_miss_running);
	local_irq_restore(flags);
	put_cpu();
	if (!hit_ret && !miss_ret && hit_enabled && miss_enabled &&
	    tk_update_bench_pmu_hit_running >= hit_enabled - hit_enabled / 100 &&
	    tk_update_bench_pmu_miss_running >= miss_enabled - miss_enabled / 100)
		tk_update_bench_pmu_window_valid = true;
}

static int tk_update_bench_pmu_open(void)
{
	struct perf_event_attr attr = {
		.type = PERF_TYPE_RAW,
		.size = sizeof(attr),
		.pinned = 1,
		.exclude_user = 1,
		.exclude_hv = 1,
	};
	unsigned long flags;
	u32 width;
	u64 value;
	int ret;

	if (boot_cpu_data.x86 != 6 || boot_cpu_data.x86_model != 140)
		return -EOPNOTSUPP;
	width = (cpuid_eax(0x0a) >> 16) & 0xff;
	if (width < 32 || width > 63)
		return -EOPNOTSUPP;
	tk_update_bench_pmu_mask = (1ULL << width) - 1;
	attr.config = TK_UPDATE_BENCH_RFO_HIT;
	tk_update_bench_pmu_hit = perf_event_create_kernel_counter(
		&attr, 0, NULL, NULL, NULL);
	if (IS_ERR(tk_update_bench_pmu_hit)) {
		ret = PTR_ERR(tk_update_bench_pmu_hit);
		tk_update_bench_pmu_hit = NULL;
		return ret;
	}
	attr.config = TK_UPDATE_BENCH_RFO_MISS;
	tk_update_bench_pmu_miss = perf_event_create_kernel_counter(
		&attr, 0, NULL, NULL, NULL);
	if (IS_ERR(tk_update_bench_pmu_miss)) {
		ret = PTR_ERR(tk_update_bench_pmu_miss);
		tk_update_bench_pmu_miss = NULL;
		goto fail;
	}
	if (get_cpu() != 0) {
		put_cpu();
		ret = -EINVAL;
		goto fail;
	}
	local_irq_save(flags);
	ret = perf_event_read_local(tk_update_bench_pmu_hit, &value,
				    NULL, NULL);
	if (!ret)
		ret = perf_event_read_local(tk_update_bench_pmu_miss, &value,
					    NULL, NULL);
	if (!ret) {
		tk_update_bench_pmu_hit_index =
			x86_perf_rdpmc_index(tk_update_bench_pmu_hit);
		tk_update_bench_pmu_miss_index =
			x86_perf_rdpmc_index(tk_update_bench_pmu_miss);
		if (tk_update_bench_pmu_hit_index < 0 ||
		    tk_update_bench_pmu_miss_index < 0)
			ret = -EBUSY;
	}
	local_irq_restore(flags);
	put_cpu();
	if (ret)
		goto fail;
	return 0;
fail:
	tk_update_bench_pmu_release();
	return ret;
}
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
DEFINE_STATIC_KEY_FALSE(timekeeping_update_bench_stage_key);
u32 timekeeping_update_bench_stage_mask;
#endif

static DEFINE_MUTEX(tk_update_bench_control_lock);
static struct tk_update_bench_sample *tk_update_bench_samples;
static struct tk_update_bench_diag_state *tk_update_bench_diag_samples;
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
struct tk_update_bench_stage_sample {
	u64 ticks[TIMEKEEPING_UPDATE_BENCH_STAGE_PARTS];
};
static struct tk_update_bench_stage_sample *tk_update_bench_stage_samples;
struct tk_update_bench_split_sample {
	u64 prefix;
	u64 suffix;
};
static struct tk_update_bench_split_sample *tk_update_bench_split_samples;
static u64 tk_update_bench_invalid_stages;
static u64 tk_update_bench_invalid_splits;
static bool tk_update_bench_staged;
static int tk_update_bench_split_part = -1;
#endif
static u64 tk_update_bench_dropped;
static u64 tk_update_bench_tsc_overhead;
static u64 tk_update_bench_tsc_pairs[TK_UPDATE_BENCH_CALIBRATION];
static unsigned int tk_update_bench_calibration_cpu;
static bool tk_update_bench_enabled;
static bool tk_update_bench_diagnostic;
#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
/* Only the standalone cache-preparation diagnosis selects these modes. */
DEFINE_STATIC_KEY_FALSE(timekeeping_update_bench_order_swap_key);
static bool tk_update_bench_order_swapped;
static u32 tk_update_bench_prep_mode;
static u32 tk_update_bench_control_lines[32] ____cacheline_aligned;

void timekeeping_update_bench_prepare(void *fast_raw)
{
	void *target;
	u32 mode;

	if (!static_branch_unlikely(&timekeeping_update_bench_key))
		return;
	mode = READ_ONCE(tk_update_bench_prep_mode);
	if (!mode)
		return;
	target = mode == 2 || mode == 4 || mode == 6 ? fast_raw :
		tk_update_bench_control_lines;
	if (mode == 3 || mode == 4) {
		/* A non-locking ownership hint. The control issues identical
		 * instructions against an unrelated pair of cache lines.
		 */
		asm volatile("prefetchw %0\n\tprefetchw %1"
			     : : "m" (*(u32 *)target),
				 "m" (*(u32 *)((u8 *)target + 64)) : "memory");
		return;
	}
	if (mode == 5 || mode == 6) {
		/* Read-intent counterpart to PREFETCHW, with the same target
		 * and control cache lines and no memory modification.
		 */
		asm volatile("prefetcht0 %0\n\tprefetcht0 %1"
			     : : "m" (*(u32 *)target),
				 "m" (*(u32 *)((u8 *)target + 64)) : "memory");
		return;
	}
	/* Same locked RMWs in both modes; neither changes the stored values.
	 * The target differs only in whether these two lines are tk_fast_raw.
	 * Both operations complete before the timed UPDATE window begins.
	 */
	asm volatile("lock; orl $0, %0\n\tlock; orl $0, %1"
		     : "+m" (*(u32 *)target),
		       "+m" (*(u32 *)((u8 *)target + 64))
		     : : "cc", "memory");
}
#endif

void timekeeping_update_bench_record(u64 start, u64 end, unsigned int action,
				     const struct timekeeper *tk,
				     const struct timekeeping_update_bench_stages *stages)
{
	/* Every caller holds the global timekeeper_lock, so writers serialize. */
	u64 index = tk_update_bench_seen++;
	struct tk_update_bench_sample *sample;

	if (unlikely(index >= TK_UPDATE_BENCH_MAX_SAMPLES)) {
		tk_update_bench_dropped++;
		return;
	}

	sample = &tk_update_bench_samples[index];
	sample->cycles = end - start;
	sample->action = action;
	sample->cpu = raw_smp_processor_id();
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
	if (unlikely(tk_update_bench_staged)) {
		struct tk_update_bench_stage_sample *parts =
			&tk_update_bench_stage_samples[index];
		u64 previous = start;
		unsigned int part;

		for (part = 0; part < TIMEKEEPING_UPDATE_BENCH_STAGE_MARKS;
		     part++) {
			u64 mark = stages->marks[part];

			if (unlikely(mark <= previous))
				tk_update_bench_invalid_stages++;
			parts->ticks[part] = mark - previous;
			previous = mark;
		}
		if (unlikely(end <= previous))
			tk_update_bench_invalid_stages++;
		parts->ticks[part] = end - previous;
	}
	if (unlikely(tk_update_bench_split_part >= 0)) {
		int part = tk_update_bench_split_part;
		u64 mark = stages->marks[part];

		if (unlikely(mark <= start || mark >= end))
			tk_update_bench_invalid_splits++;
		tk_update_bench_split_samples[index].prefix = mark - start;
		tk_update_bench_split_samples[index].suffix = end - mark;
	}
#endif
	if (unlikely(tk_update_bench_diagnostic)) {
		struct tk_update_bench_diag_state *diag =
			&tk_update_bench_diag_samples[index];
		u32 shift = tk->tkr_mono.shift;
		u64 shifted_second = (u64)NSEC_PER_SEC << shift;
		u64 mono_nsec = tk->tkr_mono.xtime_nsec >> shift;

		diag->start_tsc = start;
		diag->phase_nsec = mono_nsec % NSEC_PER_SEC;
		diag->ktime_carry =
			(u32)tk->wall_to_monotonic.tv_nsec +
			mono_nsec >= NSEC_PER_SEC;
		diag->realtime_carry =
			tk->tkr_mono.xtime_nsec >= shifted_second;
		diag->monotonic_carry =
			tk->tkr_mono.xtime_nsec +
			((u64)tk->wall_to_monotonic.tv_nsec << shift) >=
			shifted_second;
		diag->leap_pending = tk->next_leap_ktime != KTIME_MAX;
		diag->clock_mode = tk->tkr_mono.clock->vdso_clock_mode;
		diag->shift = shift;
	}
}

static u64 tk_update_bench_calibrate(void)
{
	u64 minimum = U64_MAX;
	unsigned int index;
	int cpu = get_cpu();

	tk_update_bench_calibration_cpu = cpu;

	for (index = 0; index < TK_UPDATE_BENCH_CALIBRATION; index++) {
		u64 start = rdtsc_ordered();
		u64 end = rdtsc_ordered();

		tk_update_bench_tsc_pairs[index] = end - start;
		if (tk_update_bench_tsc_pairs[index] < minimum)
			minimum = tk_update_bench_tsc_pairs[index];
	}
	put_cpu();
	return minimum;
}

static void tk_update_bench_stop(void)
{
	if (!tk_update_bench_enabled)
		return;
	tk_update_bench_enabled = false;
	static_branch_disable(&timekeeping_update_bench_key);
#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
	if (tk_update_bench_order_swapped)
		static_branch_disable(&timekeeping_update_bench_order_swap_key);
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
	if (tk_update_bench_pmu_active)
		static_branch_disable(&timekeeping_update_bench_pmu_key);
#endif
	/* Drain an update which observed the enabled branch before it changed. */
	synchronize_rcu();
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
	if (tk_update_bench_pmu_active) {
		tk_update_bench_pmu_validate();
		tk_update_bench_pmu_release();
	}
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
	if (tk_update_bench_staged || tk_update_bench_split_part >= 0)
		static_branch_disable(&timekeeping_update_bench_stage_key);
#endif
}

static void tk_update_bench_reset(void)
{
	vfree(tk_update_bench_diag_samples);
	tk_update_bench_diag_samples = NULL;
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
	vfree(tk_update_bench_pmu_samples);
	tk_update_bench_pmu_samples = NULL;
	tk_update_bench_pmu_active = false;
	tk_update_bench_pmu_window_valid = false;
	tk_update_bench_pmu_hit_running = 0;
	tk_update_bench_pmu_miss_running = 0;
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
	vfree(tk_update_bench_stage_samples);
	tk_update_bench_stage_samples = NULL;
	vfree(tk_update_bench_split_samples);
	tk_update_bench_split_samples = NULL;
	tk_update_bench_invalid_stages = 0;
	tk_update_bench_invalid_splits = 0;
	tk_update_bench_staged = false;
	tk_update_bench_split_part = -1;
	timekeeping_update_bench_stage_mask = 0;
#endif
	tk_update_bench_seen = 0;
	tk_update_bench_dropped = 0;
	tk_update_bench_diagnostic = false;
#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
	tk_update_bench_prep_mode = 0;
	tk_update_bench_order_swapped = false;
#endif
	tk_update_bench_tsc_overhead = tk_update_bench_calibrate();
}

static int tk_update_bench_status_show(struct seq_file *file, void *unused)
{
	seq_printf(file, "enabled=%u\n", tk_update_bench_enabled);
	seq_printf(file, "capacity=%u\n", TK_UPDATE_BENCH_MAX_SAMPLES);
	seq_printf(file, "samples=%llu\n",
		   min_t(u64, tk_update_bench_seen,
			 TK_UPDATE_BENCH_MAX_SAMPLES));
	seq_printf(file, "seen=%llu\n", tk_update_bench_seen);
	seq_printf(file, "dropped=%llu\n", tk_update_bench_dropped);
	seq_printf(file, "tsc_pair_min=%llu\n", tk_update_bench_tsc_overhead);
	seq_printf(file, "diagnostic_schema=%u\n", 1);
	seq_printf(file, "stage_schema=%u\n", IS_ENABLED(CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG));
	seq_printf(file, "split_schema=%u\n", IS_ENABLED(CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG));
	seq_printf(file, "diagnostic=%u\n", tk_update_bench_diagnostic);
	seq_printf(file, "prep_schema=%u\n",
		   IS_ENABLED(CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG));
	seq_printf(file, "percall_pmu_schema=%u\n",
		   IS_ENABLED(CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG));
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
	seq_printf(file, "percall_pmu_active=%u\n", tk_update_bench_pmu_active);
	seq_printf(file, "percall_pmu_validation=%s\n",
		   tk_update_bench_pmu_window_valid ? "PASS" : "NOT_RUN_OR_FAIL");
	seq_printf(file, "percall_pmu_hit_running_ns=%llu\n",
		   tk_update_bench_pmu_hit_running);
	seq_printf(file, "percall_pmu_miss_running_ns=%llu\n",
		   tk_update_bench_pmu_miss_running);
	seq_printf(file, "percall_pmu_hit_index=%d\n", tk_update_bench_pmu_hit_index);
	seq_printf(file, "percall_pmu_miss_index=%d\n", tk_update_bench_pmu_miss_index);
	seq_printf(file, "percall_pmu_mask=0x%llx\n", tk_update_bench_pmu_mask);
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
	seq_printf(file, "prep_mode=%u\n", tk_update_bench_prep_mode);
	seq_printf(file, "order_schema=1\norder_swapped=%u\n",
		   tk_update_bench_order_swapped);
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
	seq_printf(file, "staged=%u\n", tk_update_bench_staged);
	seq_printf(file, "invalid_stages=%llu\n", tk_update_bench_invalid_stages);
	seq_printf(file, "split_part=%d\n", tk_update_bench_split_part);
	seq_printf(file, "invalid_splits=%llu\n", tk_update_bench_invalid_splits);
#endif
	seq_printf(file, "calibration_cpu=%u\n", tk_update_bench_calibration_cpu);
	return 0;
}

static int tk_update_bench_status_open(struct inode *inode, struct file *file)
{
	return single_open(file, tk_update_bench_status_show, NULL);
}

static ssize_t tk_update_bench_control_write(struct file *file,
		const char __user *user_buffer, size_t count, loff_t *position)
{
	char command[16];
	size_t length = min(count, sizeof(command) - 1);
	int ret = count;

	if (copy_from_user(command, user_buffer, length))
		return -EFAULT;
	command[length] = '\0';
	strim(command);

	mutex_lock(&tk_update_bench_control_lock);
	if (!strcmp(command, "start") || !strcmp(command, "diagnose") ||
	    !strcmp(command, "pmurfo") ||
	    !strcmp(command, "prepctl") || !strcmp(command, "prepraw") ||
	    !strcmp(command, "preftctl") || !strcmp(command, "preftraw") ||
	    !strcmp(command, "prefct0") || !strcmp(command, "prefrawt0") ||
	    !strcmp(command, "ordernormal") || !strcmp(command, "orderswap") ||
	    !strcmp(command, "stage") || !strncmp(command, "split", 5)) {
		if (!tk_update_bench_enabled) {
			bool staged = !strcmp(command, "stage");
			bool split = !strncmp(command, "split", 5);
			int split_part = -1;

			if (split) {
				if (strlen(command) != 6 || command[5] < '0' ||
				    command[5] >= '0' + TIMEKEEPING_UPDATE_BENCH_STAGE_MARKS) {
					ret = -EINVAL;
					goto unlock;
				}
				split_part = command[5] - '0';
			}
			if ((staged || split) &&
			    !IS_ENABLED(CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG)) {
				ret = -EOPNOTSUPP;
				goto unlock;
			}
		if ((!strcmp(command, "prepctl") || !strcmp(command, "prepraw") ||
		     !strcmp(command, "preftctl") || !strcmp(command, "preftraw") ||
		     !strcmp(command, "prefct0") || !strcmp(command, "prefrawt0") ||
		     !strcmp(command, "ordernormal") || !strcmp(command, "orderswap")) &&
			    !IS_ENABLED(CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG)) {
				ret = -EOPNOTSUPP;
				goto unlock;
			}
			if (!strcmp(command, "pmurfo") &&
			    !IS_ENABLED(CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG)) {
				ret = -EOPNOTSUPP;
				goto unlock;
			}
			tk_update_bench_reset();
			if (staged || split || !strcmp(command, "diagnose") ||
			    !strcmp(command, "prepctl") || !strcmp(command, "prepraw") ||
		    !strcmp(command, "preftctl") || !strcmp(command, "preftraw") ||
		    !strcmp(command, "prefct0") || !strcmp(command, "prefrawt0") ||
		    !strcmp(command, "ordernormal") || !strcmp(command, "orderswap") ||
		    !strcmp(command, "pmurfo")) {
				tk_update_bench_diag_samples = vzalloc(array_size(
					TK_UPDATE_BENCH_MAX_SAMPLES,
					sizeof(*tk_update_bench_diag_samples)));
				if (!tk_update_bench_diag_samples) {
					ret = -ENOMEM;
					goto unlock;
				}
				tk_update_bench_diagnostic = true;
			}
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
			if (!strcmp(command, "pmurfo")) {
				tk_update_bench_pmu_samples = vzalloc(array_size(
					TK_UPDATE_BENCH_MAX_SAMPLES,
					sizeof(*tk_update_bench_pmu_samples)));
				if (!tk_update_bench_pmu_samples) {
					vfree(tk_update_bench_diag_samples);
					tk_update_bench_diag_samples = NULL;
					tk_update_bench_diagnostic = false;
					ret = -ENOMEM;
					goto unlock;
				}
				ret = tk_update_bench_pmu_open();
				if (ret < 0) {
					vfree(tk_update_bench_pmu_samples);
					tk_update_bench_pmu_samples = NULL;
					vfree(tk_update_bench_diag_samples);
					tk_update_bench_diag_samples = NULL;
					tk_update_bench_diagnostic = false;
					goto unlock;
				}
				tk_update_bench_pmu_active = true;
				static_branch_enable(&timekeeping_update_bench_pmu_key);
			}
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
			if (!strcmp(command, "prepctl"))
				tk_update_bench_prep_mode = 1;
			else if (!strcmp(command, "prepraw"))
				tk_update_bench_prep_mode = 2;
			else if (!strcmp(command, "preftctl"))
				tk_update_bench_prep_mode = 3;
			else if (!strcmp(command, "preftraw"))
				tk_update_bench_prep_mode = 4;
			else if (!strcmp(command, "prefct0"))
				tk_update_bench_prep_mode = 5;
			else if (!strcmp(command, "prefrawt0"))
				tk_update_bench_prep_mode = 6;
			if (!strcmp(command, "orderswap")) {
				tk_update_bench_order_swapped = true;
				static_branch_enable(&timekeeping_update_bench_order_swap_key);
			}
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
			if (staged) {
				tk_update_bench_stage_samples = vzalloc(array_size(
					TK_UPDATE_BENCH_MAX_SAMPLES,
					sizeof(*tk_update_bench_stage_samples)));
				if (!tk_update_bench_stage_samples) {
					vfree(tk_update_bench_diag_samples);
					tk_update_bench_diag_samples = NULL;
					tk_update_bench_diagnostic = false;
					ret = -ENOMEM;
					goto unlock;
				}
				tk_update_bench_staged = true;
				timekeeping_update_bench_stage_mask =
					(1U << TIMEKEEPING_UPDATE_BENCH_STAGE_MARKS) - 1;
				static_branch_enable(&timekeeping_update_bench_stage_key);
			}
			if (split) {
				tk_update_bench_split_samples = vzalloc(array_size(
					TK_UPDATE_BENCH_MAX_SAMPLES,
					sizeof(*tk_update_bench_split_samples)));
				if (!tk_update_bench_split_samples) {
					vfree(tk_update_bench_diag_samples);
					tk_update_bench_diag_samples = NULL;
					tk_update_bench_diagnostic = false;
					ret = -ENOMEM;
					goto unlock;
				}
				tk_update_bench_split_part = split_part;
				timekeeping_update_bench_stage_mask = 1U << split_part;
				static_branch_enable(&timekeeping_update_bench_stage_key);
			}
#endif
			tk_update_bench_enabled = true;
			static_branch_enable(&timekeeping_update_bench_key);
		}
	} else if (!strcmp(command, "stop")) {
		tk_update_bench_stop();
	} else if (!strcmp(command, "reset")) {
		tk_update_bench_stop();
		tk_update_bench_reset();
	} else {
		ret = -EINVAL;
	}
unlock:
	mutex_unlock(&tk_update_bench_control_lock);
	return ret;
}

static const struct file_operations tk_update_bench_control_fops = {
	.owner = THIS_MODULE,
	.open = tk_update_bench_status_open,
	.read = seq_read,
	.write = tk_update_bench_control_write,
	.llseek = seq_lseek,
	.release = single_release,
};

static int tk_update_bench_samples_show(struct seq_file *file, void *unused)
{
	u64 count, index;

	if (READ_ONCE(tk_update_bench_enabled)) {
		seq_puts(file, "error=recorder_is_running\n");
		return 0;
	}

	count = min_t(u64, READ_ONCE(tk_update_bench_seen),
		      TK_UPDATE_BENCH_MAX_SAMPLES);
	seq_printf(file, "# tsc_pair_min=%llu seen=%llu dropped=%llu\n",
		   tk_update_bench_tsc_overhead, tk_update_bench_seen,
		   tk_update_bench_dropped);
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
	seq_printf(file, "# percall_pmu_active=%u rfo_hit_config=0x%llx rfo_miss_config=0x%llx\n",
		   tk_update_bench_pmu_active,
		   TK_UPDATE_BENCH_RFO_HIT, TK_UPDATE_BENCH_RFO_MISS);
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_CACHE_PREP_DIAG
	seq_printf(file, "# prep_mode=%u\n", tk_update_bench_prep_mode);
	seq_printf(file, "# order_swapped=%u\n",
		   tk_update_bench_order_swapped);
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
	seq_printf(file, "# stage_schema=%u invalid_stages=%llu\n",
		   tk_update_bench_staged ? 1 : 0,
		   tk_update_bench_invalid_stages);
	if (tk_update_bench_split_part >= 0)
		seq_printf(file, "# split_schema=1 split_part=%d invalid_splits=%llu\n",
			   tk_update_bench_split_part,
			   tk_update_bench_invalid_splits);
#endif
	if (tk_update_bench_diagnostic) {
		seq_puts(file, "sample,cycles,action,cpu,phase_nsec,ktime_carry,realtime_carry,monotonic_carry,leap_pending,clock_mode,shift,start_tsc");
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
		if (tk_update_bench_staged)
			seq_puts(file, ",prep_ticks,ktime_ticks,first_publish_ticks,second_publish_ticks,base_real_ticks,fast_mono_ticks,fast_raw_ticks,tail_ticks");
		if (tk_update_bench_split_part >= 0)
			seq_puts(file, ",prefix_ticks,suffix_ticks");
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
		if (tk_update_bench_pmu_active)
			seq_puts(file, ",rfo_hit,rfo_miss,pmu_valid");
#endif
		seq_putc(file, '\n');
	} else {
		seq_puts(file, "sample,cycles,action,cpu\n");
	}
	for (index = 0; index < count; index++) {
		const struct tk_update_bench_sample *sample =
			&tk_update_bench_samples[index];

		seq_printf(file, "%llu,%llu,%u,%u", index,
			   sample->cycles, sample->action, sample->cpu);
		if (tk_update_bench_diagnostic) {
			const struct tk_update_bench_diag_state *diag =
				&tk_update_bench_diag_samples[index];

			seq_printf(file, ",%u,%u,%u,%u,%u,%u,%u,%llu",
				   diag->phase_nsec, diag->ktime_carry,
				   diag->realtime_carry,
				   diag->monotonic_carry,
				   diag->leap_pending, diag->clock_mode,
				   diag->shift, diag->start_tsc);
		}
#ifdef CONFIG_TIMEKEEPING_UPDATE_STAGE_DIAG
		if (tk_update_bench_staged) {
			const struct tk_update_bench_stage_sample *parts =
				&tk_update_bench_stage_samples[index];
			unsigned int part;

			for (part = 0; part < TIMEKEEPING_UPDATE_BENCH_STAGE_PARTS;
			     part++)
				seq_printf(file, ",%llu", parts->ticks[part]);
		}
		if (tk_update_bench_split_part >= 0) {
			const struct tk_update_bench_split_sample *parts =
				&tk_update_bench_split_samples[index];

			seq_printf(file, ",%llu,%llu", parts->prefix,
				   parts->suffix);
		}
#endif
#ifdef CONFIG_TIMEKEEPING_UPDATE_PERCALL_PMU_DIAG
		if (tk_update_bench_pmu_active) {
			const struct tk_update_bench_pmu_sample *pmu =
				&tk_update_bench_pmu_samples[index];

			seq_printf(file, ",%u,%u,%u", pmu->hit,
				   pmu->miss, pmu->valid);
		}
#endif
		seq_putc(file, '\n');
	}
	return 0;
}

static int tk_update_bench_calibration_show(struct seq_file *file, void *unused)
{
	unsigned int index;

	if (READ_ONCE(tk_update_bench_enabled)) {
		seq_puts(file, "error=recorder_is_running\n");
		return 0;
	}
	seq_printf(file, "# cpu=%u unit=TSC_ticks\n",
		   tk_update_bench_calibration_cpu);
	seq_puts(file, "sample,ticks\n");
	for (index = 0; index < TK_UPDATE_BENCH_CALIBRATION; index++)
		seq_printf(file, "%u,%llu\n", index,
			   tk_update_bench_tsc_pairs[index]);
	return 0;
}

static int tk_update_bench_calibration_open(struct inode *inode,
					    struct file *file)
{
	return single_open(file, tk_update_bench_calibration_show, NULL);
}

static const struct file_operations tk_update_bench_calibration_fops = {
	.owner = THIS_MODULE,
	.open = tk_update_bench_calibration_open,
	.read = seq_read,
	.llseek = seq_lseek,
	.release = single_release,
};

static int tk_update_bench_samples_open(struct inode *inode, struct file *file)
{
	return single_open(file, tk_update_bench_samples_show, NULL);
}

static const struct file_operations tk_update_bench_samples_fops = {
	.owner = THIS_MODULE,
	.open = tk_update_bench_samples_open,
	.read = seq_read,
	.llseek = seq_lseek,
	.release = single_release,
};

static int __init tk_update_bench_init(void)
{
	struct dentry *directory;

	tk_update_bench_samples = vzalloc(array_size(
		TK_UPDATE_BENCH_MAX_SAMPLES,
		sizeof(*tk_update_bench_samples)));
	if (!tk_update_bench_samples)
		return -ENOMEM;
	tk_update_bench_reset();
	directory = debugfs_create_dir("timekeeping_update_bench", NULL);
	debugfs_create_file("control", 0600, directory, NULL,
			    &tk_update_bench_control_fops);
	debugfs_create_file("samples", 0400, directory, NULL,
			    &tk_update_bench_samples_fops);
	debugfs_create_file("calibration", 0400, directory, NULL,
			    &tk_update_bench_calibration_fops);
	return 0;
}
late_initcall(tk_update_bench_init);
