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
 * A typed root reader names the clock at the call site. These two adapters
 * only bridge the kernel result type and environment; they compile to a
 * direct call and never inspect MM_data or a generic clock ID.
 */
#define vkso_time_get_root_hres(reader, tp)				\
	(reader)((struct vkso_time_value *)(tp), &vkso_kernel_context)
#define vkso_time_get_root_coarse(reader, tp)				\
	do {								\
		(void)(reader)((struct vkso_time_value *)(tp));		\
	} while (0)

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
