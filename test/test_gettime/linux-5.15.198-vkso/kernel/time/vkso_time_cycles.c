// SPDX-License-Identifier: GPL-2.0

#include "vkso_time_internal.h"

#ifdef CONFIG_PARAVIRT_CLOCK
#include <asm/pvclock.h>
#endif
#ifdef CONFIG_HYPERV_TIMER
#include <clocksource/hyperv_timer.h>
#endif

#ifdef CONFIG_PARAVIRT_CLOCK
static __always_inline
s64 vkso_read_pvclock_cycles(const void *page)
{
	const struct pvclock_vcpu_time_info *pvti;
	u32 version;
	u64 value;

	if (unlikely(!page))
		return -1;
	pvti = &((const struct pvclock_vsyscall_time_info *)page)->pvti;
	do {
		version = pvclock_read_begin(pvti);
		if (unlikely(!(pvti->flags & PVCLOCK_TSC_STABLE_BIT)))
			return -1;
		value = __pvclock_read_cycles(pvti, rdtsc_ordered());
	} while (pvclock_read_retry(pvti, version));

	return value;
}
#endif

#ifdef CONFIG_HYPERV_TIMER
static __always_inline
s64 vkso_read_hvclock_cycles(const void *page)
{
	if (unlikely(!page))
		return -1;
	return hv_read_tsc_page(page);
}
#endif

noinline notrace __vkso_text
s64 vkso_read_cycles_cold(const struct vkso_context *context, s32 clock_mode)
{
	if (unlikely(!context))
		return -1;
#ifdef CONFIG_PARAVIRT_CLOCK
	if (clock_mode == VDSO_CLOCKMODE_PVCLOCK)
		return vkso_read_pvclock_cycles(context->pvclock_page);
#endif
#ifdef CONFIG_HYPERV_TIMER
	if (clock_mode == VDSO_CLOCKMODE_HVCLOCK)
		return vkso_read_hvclock_cycles(context->hvclock_page);
#endif
	return -1;
}
