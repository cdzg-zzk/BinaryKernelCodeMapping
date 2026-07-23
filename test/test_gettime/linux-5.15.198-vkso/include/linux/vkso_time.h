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
int vkso_time_get_context(clockid_t clock_id, struct timespec64 *tp);
void vkso_time_update_mm_data(struct task_struct *task,
			      const struct timens_offsets *offsets);

static __always_inline int
vkso_time_get_global(clockid_t clock_id, struct timespec64 *tp)
{
	return __vkso_clock_gettime(NULL, clock_id,
				   (struct vkso_time_value *)tp);
}

static __always_inline int
vkso_time_getres(clockid_t clock_id, struct timespec64 *tp)
{
	return __vkso_clock_getres(clock_id, (struct vkso_time_value *)tp);
}
#else
static inline void vkso_time_publish(struct timekeeper *tk)
{
}

static inline int
vkso_time_get_global(clockid_t clock_id, struct timespec64 *tp)
{
	return VKSO_TIME_FALLBACK;
}

static inline int
vkso_time_get_context(clockid_t clock_id, struct timespec64 *tp)
{
	return VKSO_TIME_FALLBACK;
}

static inline int
vkso_time_getres(clockid_t clock_id, struct timespec64 *tp)
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
