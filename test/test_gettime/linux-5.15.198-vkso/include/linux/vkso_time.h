/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_TIME_H
#define _LINUX_VKSO_TIME_H

#include <linux/time64.h>
#include <linux/vkso.h>
#include <vkso/time.h>

struct mm_struct;
struct task_struct;
struct timekeeper;
struct timens_offsets;

#ifdef CONFIG_VKSO_TIME
extern union vkso_shared_page vkso_shared_page;
extern struct vkso_cycle_context vkso_kernel_cycle_context;

void vkso_time_publish(struct timekeeper *tk);
void vkso_time_update_timezone(void);
void vkso_time_update_mm_data(struct task_struct *task,
			      const struct timens_offsets *offsets);
void vkso_time_set_pvclock_page(const void *page);
void vkso_time_set_hvclock_page(const void *page);

static __always_inline int
vkso_time_get(const struct vkso_mm_data *mm_data, clockid_t clock_id,
	      struct timespec64 *tp)
{
	return vkso_clock_gettime_core(mm_data, clock_id,
				      (struct vkso_time_value *)tp,
				      &vkso_kernel_cycle_context);
}

static __always_inline int
vkso_time_getres(clockid_t clock_id, struct timespec64 *tp)
{
	return __vkso_clock_getres(clock_id, (struct vkso_time_value *)tp);
}

static __always_inline int
vkso_time_gettimeofday(struct __kernel_old_timeval *tv, struct timezone *tz)
{
	return vkso_gettimeofday_core((struct vkso_timeval *)tv,
				      (struct vkso_timezone *)tz,
				      &vkso_kernel_cycle_context);
}

static __always_inline int vkso_time_get_seconds(__kernel_old_time_t *value)
{
	*value = (__kernel_old_time_t)__vkso_time(NULL);
	return VKSO_TIME_OK;
}
#else
static inline void vkso_time_publish(struct timekeeper *tk)
{
}

static inline void vkso_time_update_timezone(void)
{
}

static inline void vkso_time_set_pvclock_page(const void *page)
{
}

static inline void vkso_time_set_hvclock_page(const void *page)
{
}

static inline int
vkso_time_get(const struct vkso_mm_data *mm_data, clockid_t clock_id,
	      struct timespec64 *tp)
{
	return VKSO_TIME_FALLBACK;
}

static inline int
vkso_time_getres(clockid_t clock_id, struct timespec64 *tp)
{
	return VKSO_TIME_FALLBACK;
}

static inline int
vkso_time_gettimeofday(struct __kernel_old_timeval *tv, struct timezone *tz)
{
	return VKSO_TIME_FALLBACK;
}

static inline int vkso_time_get_seconds(__kernel_old_time_t *value)
{
	return VKSO_TIME_FALLBACK;
}

static inline void
vkso_time_update_mm_data(struct task_struct *task,
			 const struct timens_offsets *offsets)
{
}
#endif

#endif /* _LINUX_VKSO_TIME_H */
