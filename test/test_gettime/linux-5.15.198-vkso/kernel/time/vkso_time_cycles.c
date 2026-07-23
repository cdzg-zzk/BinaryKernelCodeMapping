// SPDX-License-Identifier: GPL-2.0

#include "vkso_time_internal.h"

#ifdef CONFIG_PARAVIRT_CLOCK
#include <asm/pvclock.h>
#endif
#ifdef CONFIG_HYPERV_TIMER
#include <clocksource/hyperv_timer.h>
#endif

#ifdef CONFIG_PARAVIRT_CLOCK
noinline notrace __vkso_text
bool vkso_read_pvclock_cycles(const void *page, u64 *cycles)
{
	const struct pvclock_vcpu_time_info *pvti;
	u32 version;
	u64 value;

	if (unlikely(!page))
		return false;
	pvti = &((const struct pvclock_vsyscall_time_info *)page)->pvti;
	do {
		version = pvclock_read_begin(pvti);
		if (unlikely(!(pvti->flags & PVCLOCK_TSC_STABLE_BIT)))
			return false;
		value = __pvclock_read_cycles(pvti, rdtsc_ordered());
	} while (pvclock_read_retry(pvti, version));

	*cycles = value;
	return (s64)value >= 0;
}
#endif

#ifdef CONFIG_HYPERV_TIMER
noinline notrace __vkso_text
bool vkso_read_hvclock_cycles(const void *page, u64 *cycles)
{
	u64 value;

	if (unlikely(!page))
		return false;
	value = hv_read_tsc_page(page);
	*cycles = value;
	return (s64)value >= 0;
}
#endif
