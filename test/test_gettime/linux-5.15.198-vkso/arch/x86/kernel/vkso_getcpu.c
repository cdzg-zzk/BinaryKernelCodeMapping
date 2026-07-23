// SPDX-License-Identifier: GPL-2.0

#include <asm/processor.h>

#include <linux/compiler.h>
#include <linux/vkso.h>

#include <vkso/getcpu.h>

/*
 * Keep the x86 CPU/node reader separate from the generic time core, just as
 * the native x86 vDSO keeps vgetcpu.c separate from vclock_gettime.c.
 */
__visible noinline notrace __vkso_text
int __vkso_getcpu(unsigned int *cpu, unsigned int *node, void *unused)
{
	unsigned long cpu_node;

	/*
	 * The alternatives pass selects RDPID when available and otherwise uses
	 * the per-CPU GDT descriptor prepared by setup_getcpu().
	 */
	alternative_io("lsl %[segment],%k[value]",
		       "rdpid %[value]",
		       X86_FEATURE_RDPID,
		       [value] "=r" (cpu_node),
		       [segment] "r" (__CPUNODE_SEG));
	if (cpu)
		*cpu = cpu_node & CPUNODE_MASK;
	if (node)
		*node = cpu_node >> CPUNODE_BITS;
	return VKSO_GETCPU_OK;
}
