/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_TIME_H
#define _LINUX_VKSO_TIME_H

#include <linux/compiler_types.h>
#include <linux/time64.h>
#include <vkso/time.h>

struct mm_struct;
struct task_struct;
struct timekeeper;
struct timens_offsets;

#define VKSO_TEXT_SECTION		".vkso.text"
#define VKSO_SHARED_DATA_SECTION	".vkso.shared_data"

#define __vkso_text		__section(VKSO_TEXT_SECTION)
#define __vkso_shared_data	__section(VKSO_SHARED_DATA_SECTION)

extern char __vkso_text_start[];
extern char __vkso_text_end[];
extern char __vkso_shared_data_start[];
extern char __vkso_shared_data_end[];

#ifdef CONFIG_VKSO_TIME
extern union vkso_shared_page vkso_shared_page;

void vkso_time_publish(struct timekeeper *tk);
void vkso_time_update_timezone(void);
void vkso_time_update_mm_data(struct task_struct *task,
			      const struct timens_offsets *offsets);

static __always_inline int
vkso_time_get(const struct vkso_mm_data *mm_data, clockid_t clock_id,
	      struct timespec64 *tp)
{
	return __vkso_clock_gettime(mm_data, clock_id,
				   (struct vkso_time_value *)tp);
}

static __always_inline int
vkso_time_getres(clockid_t clock_id, struct timespec64 *tp)
{
	return __vkso_clock_getres(clock_id, (struct vkso_time_value *)tp);
}

static __always_inline int
vkso_time_gettimeofday(struct __kernel_old_timeval *tv, struct timezone *tz)
{
	return __vkso_gettimeofday((struct vkso_timeval *)tv,
				   (struct vkso_timezone *)tz);
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
