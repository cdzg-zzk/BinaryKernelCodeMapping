/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_TIME_H
#define _LINUX_VKSO_TIME_H

#include <linux/time64.h>
#include <linux/vkso.h>
#include <vkso/time.h>

struct mm_struct;
struct task_struct;
struct timens_offsets;

void vkso_timekeeping_get_private(clockid_t clock_id, struct timespec64 *ts);

extern union vkso_shared_page vkso_shared_page;
extern struct vkso_context vkso_kernel_context;

void vkso_time_update_timezone(void);
void vkso_time_update_mm_data(struct task_struct *task,
			      const struct timens_offsets *offsets);
void vkso_time_set_pvclock_page(const void *page);
void vkso_time_set_hvclock_page(const void *page);
#ifdef CONFIG_VKSO_TIME_TEST
int vkso_timekeeping_writer_context_selftest(void);
#endif

/*
 * Ordinary kernel readers use the same global-clock dispatcher as userspace,
 * but select root-namespace semantics with a NULL MM_data pointer.  Special
 * NMI, writer-locked and early-boot readers remain on their private paths.
 */
#define vkso_time_get_root(clock_id, tp)				\
	vkso_clock_gettime_common((clock_id),				\
		(struct vkso_time_value *)(tp), NULL,			\
		&vkso_kernel_context)

static __always_inline u32 vkso_time_get_root_resolution(void)
{
	return READ_ONCE(
		vkso_shared_page.data.state.clocksource_resolution);
}

static __always_inline time64_t vkso_time_get_root_monotonic_seconds(void)
{
	return READ_ONCE(vkso_shared_page.data.state.monotonic_coarse.sec);
}

static __always_inline time64_t vkso_time_get_root_realtime_seconds(void)
{
	return READ_ONCE(vkso_shared_page.data.state.realtime_base.sec);
}

static __always_inline int
vkso_time_gettimeofday(struct __kernel_old_timeval *tv, struct timezone *tz)
{
	return vkso_gettimeofday_core((struct vkso_timeval *)tv,
				      (struct vkso_timezone *)tz,
				      &vkso_kernel_context);
}

#endif /* _LINUX_VKSO_TIME_H */
