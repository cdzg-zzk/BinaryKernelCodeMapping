/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_TIME_H
#define _LINUX_VKSO_TIME_H

#include <linux/compiler_types.h>
#include <linux/time64.h>
#include <vkso/time.h>

struct mm_struct;
struct task_struct;
struct timekeeper;

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
bool vkso_time_get_realtime_coarse(struct timespec64 *tp);
bool vkso_time_get_monotonic_coarse(struct timespec64 *tp);
const struct vkso_mm_data *vkso_time_mm_data(struct mm_struct *mm);
void vkso_time_update_mm_data(struct task_struct *task,
			      const struct timespec64 *monotonic_offset);
#else
static inline void vkso_time_publish(struct timekeeper *tk)
{
}

static inline bool vkso_time_get_realtime_coarse(struct timespec64 *tp)
{
	return false;
}

static inline bool vkso_time_get_monotonic_coarse(struct timespec64 *tp)
{
	return false;
}

static inline void
vkso_time_update_mm_data(struct task_struct *task,
			 const struct timespec64 *monotonic_offset)
{
}
#endif

#endif /* _LINUX_VKSO_TIME_H */
