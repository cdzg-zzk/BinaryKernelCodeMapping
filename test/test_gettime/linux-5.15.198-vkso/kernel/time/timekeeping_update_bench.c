// SPDX-License-Identifier: GPL-2.0
/* Test-only recorder for complete timekeeping_update() latency. */
#include <linux/debugfs.h>
#include <linux/fs.h>
#include <linux/init.h>
#include <linux/jump_label.h>
#include <linux/mutex.h>
#include <linux/preempt.h>
#include <linux/rcupdate.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <linux/timekeeper_internal.h>
#include <linux/timekeeping_update_bench.h>
#include <linux/uaccess.h>
#include <linux/vmalloc.h>

#include <asm/msr.h>

#define TK_UPDATE_BENCH_MAX_SAMPLES	65536U
#define TK_UPDATE_BENCH_CALIBRATION	4096U

struct tk_update_bench_sample {
	u64 cycles;
	u32 action;
	u32 cpu;
};

/* Allocated only for diagnose, leaving the formal recorder at 16 B/sample. */
struct tk_update_bench_diag_state {
	u32 phase_nsec;
	u8 ktime_carry;
	u8 realtime_carry;
	u8 monotonic_carry;
	u8 leap_pending;
	u32 clock_mode;
	u32 shift;
};

DEFINE_STATIC_KEY_FALSE(timekeeping_update_bench_key);

static DEFINE_MUTEX(tk_update_bench_control_lock);
static struct tk_update_bench_sample *tk_update_bench_samples;
static struct tk_update_bench_diag_state *tk_update_bench_diag_samples;
static u64 tk_update_bench_seen;
static u64 tk_update_bench_dropped;
static u64 tk_update_bench_tsc_overhead;
static u64 tk_update_bench_tsc_pairs[TK_UPDATE_BENCH_CALIBRATION];
static unsigned int tk_update_bench_calibration_cpu;
static bool tk_update_bench_enabled;
static bool tk_update_bench_diagnostic;

void timekeeping_update_bench_record(u64 start, u64 end, unsigned int action,
				     const struct timekeeper *tk)
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
	if (unlikely(tk_update_bench_diagnostic)) {
		struct tk_update_bench_diag_state *diag =
			&tk_update_bench_diag_samples[index];
		u32 shift = tk->tkr_mono.shift;
		u64 shifted_second = (u64)NSEC_PER_SEC << shift;
		u64 mono_nsec = tk->tkr_mono.xtime_nsec >> shift;

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
	/* Drain an update which observed the enabled branch before it changed. */
	synchronize_rcu();
}

static void tk_update_bench_reset(void)
{
	vfree(tk_update_bench_diag_samples);
	tk_update_bench_diag_samples = NULL;
	tk_update_bench_seen = 0;
	tk_update_bench_dropped = 0;
	tk_update_bench_diagnostic = false;
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
	seq_printf(file, "diagnostic=%u\n", tk_update_bench_diagnostic);
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
	if (!strcmp(command, "start") || !strcmp(command, "diagnose")) {
		if (!tk_update_bench_enabled) {
			tk_update_bench_reset();
			if (!strcmp(command, "diagnose")) {
				tk_update_bench_diag_samples = vzalloc(array_size(
					TK_UPDATE_BENCH_MAX_SAMPLES,
					sizeof(*tk_update_bench_diag_samples)));
				if (!tk_update_bench_diag_samples) {
					ret = -ENOMEM;
					goto unlock;
				}
				tk_update_bench_diagnostic = true;
			}
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
	if (tk_update_bench_diagnostic)
		seq_puts(file, "sample,cycles,action,cpu,phase_nsec,ktime_carry,realtime_carry,monotonic_carry,leap_pending,clock_mode,shift\n");
	else
		seq_puts(file, "sample,cycles,action,cpu\n");
	for (index = 0; index < count; index++) {
		const struct tk_update_bench_sample *sample =
			&tk_update_bench_samples[index];

		seq_printf(file, "%llu,%llu,%u,%u", index,
			   sample->cycles, sample->action, sample->cpu);
		if (tk_update_bench_diagnostic) {
			const struct tk_update_bench_diag_state *diag =
				&tk_update_bench_diag_samples[index];

			seq_printf(file, ",%u,%u,%u,%u,%u,%u,%u",
				   diag->phase_nsec, diag->ktime_carry,
				   diag->realtime_carry,
				   diag->monotonic_carry,
				   diag->leap_pending, diag->clock_mode,
				   diag->shift);
		}
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
