#include <linux/module.h>
#include <linux/sched.h>
#include <linux/cpumask.h>
#include <linux/irqflags.h>
#include <linux/preempt.h>

static int cpu = 2;
module_param(cpu, int, 0444);
static u64 samples[1001];

/* Same timestamp sequence and empty interval as the Layer-3 timers. */
static __always_inline u64 start(void)
{
	u32 lo, hi, aux;
	asm volatile("lfence\n\trdtscp" : "=a"(lo), "=d"(hi), "=c"(aux) :: "memory");
	return ((u64)hi << 32) | lo;
}
static __always_inline u64 end(void)
{
	u32 lo, hi, aux;
	asm volatile("rdtscp\n\tlfence" : "=a"(lo), "=d"(hi), "=c"(aux) :: "memory");
	return ((u64)hi << 32) | lo;
}
static int __init calibrate(void)
{
	unsigned long flags;
	u64 a, b;
	int i, ret;
	if (cpu < 0 || cpu >= nr_cpu_ids || !cpu_online(cpu)) return -EINVAL;
	ret = set_cpus_allowed_ptr(current, cpumask_of(cpu));
	if (ret) return ret;
	preempt_disable();
	local_irq_save(flags);
	for (i = 0; i < 100; i++) { a = start(); b = end(); asm volatile("" :: "r"(a), "r"(b) : "memory"); }
	for (i = 0; i < ARRAY_SIZE(samples); i++) { a = start(); b = end(); samples[i] = b - a; }
	local_irq_restore(flags);
	preempt_enable();
	for (i = 0; i < ARRAY_SIZE(samples); i++)
		pr_info("PGOT_TIMESTAMP,%d,%llu\n", i, samples[i]);
	return 0;
}
static void __exit finish(void) {}
module_init(calibrate);
module_exit(finish);
MODULE_LICENSE("GPL");
