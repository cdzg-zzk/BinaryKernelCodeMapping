// SPDX-License-Identifier: GPL-2.0
/* Test-only module. Measures ordinary exported APIs on either complete kernel. */
#include <linux/cpu.h>
#include <linux/debugfs.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <linux/timekeeping.h>
#include <linux/uaccess.h>
#include <asm/msr.h>
#include <asm/pgtable.h>

#define MAX_ROUNDS 1000
static struct dentry *directory;
static DEFINE_MUTEX(bench_lock);
static const char *const names[] = {"monotonic", "monotonic_raw", "monotonic_coarse"};
/* Separate controls keep the historical three-API campaign matrix unchanged. */
static const char *const scalar_names[] = {
	"ktime_get", "ktime_get_raw", "ktime_get_real",
	"ktime_get_boottime", "ktime_get_tai",
};
struct sample { u64 cycles, checksum; unsigned int cpu; };
struct request {
	unsigned int cpu, iterations, rounds, warmup;
	struct sample *samples;
	bool scalar;
};
static struct request recorded, scalar_recorded = { .scalar = true };
static unsigned long page_addresses[64];
static unsigned int page_count;

/* Dispatch once per batch, not an extra indirect call for every clock read. */
static noinline u64 run_batch(unsigned int operation, unsigned int iterations)
{
	struct timespec64 value;
	u64 sum = 0;
	unsigned int i;
#define LOOP(api) do { \
	for (i = 0; i < iterations; ++i) { \
		api(&value); \
		sum += (u64)value.tv_sec ^ value.tv_nsec; \
	} \
} while (0)
	switch (operation) {
	case 0: LOOP(ktime_get_ts64); break;
	case 1: LOOP(ktime_get_raw_ts64); break;
	case 2: LOOP(ktime_get_coarse_ts64); break;
	}
#undef LOOP
	return sum;
}

/* The scalar suite uses direct calls and no sec/nsec checksum conversion. */
static noinline u64 run_scalar_batch(unsigned int operation, unsigned int iterations)
{
	u64 sum = 0;
	unsigned int i;
#define LOOP(expr) do { \
	for (i = 0; i < iterations; ++i) \
		sum += (u64)ktime_to_ns(expr); \
} while (0)
	switch (operation) {
	case 0: LOOP(ktime_get()); break;
	case 1: LOOP(ktime_get_raw()); break;
	case 2: LOOP(ktime_get_with_offset(TK_OFFS_REAL)); break;
	case 3: LOOP(ktime_get_with_offset(TK_OFFS_BOOT)); break;
	case 4: LOOP(ktime_get_with_offset(TK_OFFS_TAI)); break;
	}
#undef LOOP
	return sum;
}

/* Same clock, different output ABI; outside every timing window. A wall-clock
 * discontinuity can reject this diagnostic rather than certify bad samples. */
static int scalar_check(void)
{
	struct timespec64 before, after;
	ktime_t value;
	unsigned int op;

	for (op = 0; op < ARRAY_SIZE(scalar_names); ++op) {
#define CHECK(ts_api, expression) do { \
	ts_api(&before); \
	value = (expression); \
	ts_api(&after); \
} while (0)
		switch (op) {
		case 0: CHECK(ktime_get_ts64, ktime_get()); break;
		case 1: CHECK(ktime_get_raw_ts64, ktime_get_raw()); break;
		case 2: CHECK(ktime_get_real_ts64, ktime_get_with_offset(TK_OFFS_REAL)); break;
		case 3: CHECK(ktime_get_boottime_ts64, ktime_get_with_offset(TK_OFFS_BOOT)); break;
		default: CHECK(ktime_get_clocktai_ts64, ktime_get_with_offset(TK_OFFS_TAI)); break;
		}
#undef CHECK
		if (ktime_before(value, timespec64_to_ktime(before)) ||
		    ktime_after(value, timespec64_to_ktime(after)))
			return -ERANGE;
	}
	return 0;
}

static long measure_on_cpu(void *data)
{
	struct request *r = data;
	unsigned int count = r->scalar ? ARRAY_SIZE(scalar_names) : ARRAY_SIZE(names);
	unsigned int round, step;
	int error;

	if (r->scalar) {
		error = scalar_check();
		if (error)
			return error;
	}
	for (round = 0; round < r->rounds; ++round) {
		for (step = 0; step < count; ++step) {
			unsigned int op = (step + round) % count;
			struct sample *s = &r->samples[round * count + op];
			u64 start, end;

			/* Select outside the measured window, never per API call. */
			if (r->scalar) {
				s->checksum = run_scalar_batch(op, r->warmup);
				barrier();
				start = rdtsc_ordered();
				s->checksum ^= run_scalar_batch(op, r->iterations);
				end = rdtsc_ordered();
				barrier();
			} else {
				s->checksum = run_batch(op, r->warmup);
				barrier();
				start = rdtsc_ordered();
				s->checksum ^= run_batch(op, r->iterations);
				end = rdtsc_ordered();
				barrier();
			}
			s->cycles = end - start;
			s->cpu = smp_processor_id();
		}
		cond_resched();
	}
	return 0;
}

static ssize_t control_write(struct file *file, const char __user *buffer,
			     size_t length, loff_t *position)
{
	char input[96], extra;
	struct request *saved = file->private_data;
	struct request r = { .scalar = saved->scalar };
	unsigned int count = r.scalar ? ARRAY_SIZE(scalar_names) : ARRAY_SIZE(names);
	int error;
	if (!length || length >= sizeof(input)) return -EINVAL;
	if (copy_from_user(input, buffer, length)) return -EFAULT;
	input[length] = 0;
	if (sscanf(input, "%u %u %u %u %c", &r.cpu, &r.iterations,
		   &r.rounds, &r.warmup, &extra) != 4 || !r.iterations ||
	    r.iterations > 1000000 || !r.rounds || r.rounds > MAX_ROUNDS ||
	    r.warmup > 1000000 || r.cpu >= nr_cpu_ids) return -EINVAL;
	if (!mutex_trylock(&bench_lock)) return -EBUSY;
	r.samples = kcalloc(r.rounds * count, sizeof(*r.samples), GFP_KERNEL);
	if (!r.samples) { error = -ENOMEM; goto unlock; }
	cpus_read_lock();
	if (!cpu_online(r.cpu)) error = -ENODEV;
	else error = work_on_cpu(r.cpu, measure_on_cpu, &r);
	cpus_read_unlock();
	if (error) { kfree(r.samples); goto unlock; }
	kfree(saved->samples);
	*saved = r;
unlock:
	mutex_unlock(&bench_lock);
	return error ? error : length;
}

static int samples_show(struct seq_file *stream, void *unused)
{
	struct request *r = stream->private;
	const char *const *labels = r->scalar ? scalar_names : names;
	unsigned int count = r->scalar ? ARRAY_SIZE(scalar_names) : ARRAY_SIZE(names);
	unsigned int round, op;

	mutex_lock(&bench_lock);
	seq_puts(stream, "api,round,cpu,iterations,total_tsc_cycles,checksum\n");
	if (r->samples)
		for (round = 0; round < r->rounds; ++round)
			for (op = 0; op < count; ++op) {
				struct sample *s = &r->samples[round * count + op];
				seq_printf(stream, "%s,%u,%u,%u,%llu,%llu\n", labels[op],
					round, s->cpu, r->iterations, s->cycles, s->checksum);
			}
	mutex_unlock(&bench_lock);
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(samples);
/* Read-only evidence for the explicitly supplied test closure's kernel aliases. */
static ssize_t pages_write(struct file *file, const char __user *buffer,
			  size_t length, loff_t *position)
{
	char *input, *cursor, *token;
	unsigned long addresses[ARRAY_SIZE(page_addresses)];
	unsigned int count = 0;
	int error = 0;
	if (!length || length > 2048) return -EINVAL;
	input = memdup_user_nul(buffer, length);
	if (IS_ERR(input)) return PTR_ERR(input);
	cursor = input;
	while ((token = strsep(&cursor, " \n\t")) != NULL) {
		unsigned long address;
		if (!*token) continue;
		if (count == ARRAY_SIZE(addresses) || kstrtoul(token, 0, &address) ||
		    address < PAGE_OFFSET || (address & (PAGE_SIZE - 1))) {
			error = -EINVAL; break;
		}
		addresses[count++] = address;
	}
	if (!error && count) {
		mutex_lock(&bench_lock);
		memcpy(page_addresses, addresses, count * sizeof(*addresses));
		page_count = count;
		mutex_unlock(&bench_lock);
	} else if (!error) error = -EINVAL;
	kfree(input);
	return error ? error : length;
}

static int pages_show(struct seq_file *stream, void *unused)
{
	unsigned int i;
	mutex_lock(&bench_lock);
	seq_puts(stream, "kernel_vaddr,pfn,level\n");
	for (i = 0; i < page_count; ++i) {
		unsigned int level;
		unsigned long address = page_addresses[i], pfn;
		pte_t *entry = lookup_address(address, &level);
		if (!entry || !pte_present(*entry)) continue;
		if (level == PG_LEVEL_4K) pfn = pte_pfn(*entry);
		else if (level == PG_LEVEL_2M)
			pfn = pmd_pfn(*(pmd_t *)entry) + ((address & ~PMD_MASK) >> PAGE_SHIFT);
		else if (level == PG_LEVEL_1G)
			pfn = pud_pfn(*(pud_t *)entry) + ((address & ~PUD_MASK) >> PAGE_SHIFT);
		else continue;
		seq_printf(stream, "0x%lx,%lu,%u\n", address, pfn, level);
	}
	mutex_unlock(&bench_lock);
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(pages);
static const struct file_operations page_control_ops = {
	.owner = THIS_MODULE, .write = pages_write, .llseek = no_llseek,
};
static const struct file_operations control_ops = {
	.owner = THIS_MODULE, .open = simple_open,
	.write = control_write, .llseek = no_llseek,
};
static int __init reader_init(void)
{
	directory = debugfs_create_dir("vkso_kernel_reader", NULL);
	if (IS_ERR(directory)) return PTR_ERR(directory);
	debugfs_create_file("control", 0200, directory, &recorded, &control_ops);
	debugfs_create_file("samples", 0400, directory, &recorded, &samples_fops);
	debugfs_create_file("scalar_control", 0200, directory, &scalar_recorded, &control_ops);
	debugfs_create_file("scalar_samples", 0400, directory, &scalar_recorded, &samples_fops);
	debugfs_create_file("page_addresses", 0200, directory, NULL, &page_control_ops);
	debugfs_create_file("pages", 0400, directory, NULL, &pages_fops);
	return 0;
}
static void __exit reader_exit(void)
{
	debugfs_remove_recursive(directory);
	kfree(recorded.samples);
	kfree(scalar_recorded.samples);
}
module_init(reader_init);
module_exit(reader_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Ordinary kernel clock reader evaluation (no VKSO core changes)");
