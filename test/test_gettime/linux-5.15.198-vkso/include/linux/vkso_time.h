/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_TIME_H
#define _LINUX_VKSO_TIME_H

#include <linux/time64.h>
#include <linux/vkso.h>
#include <vkso/time.h>

struct mm_struct;
struct task_struct;
struct time_namespace;

void vkso_timekeeping_get_private(clockid_t clock_id, struct timespec64 *ts);

extern union vkso_shared_page vkso_shared_page;
extern struct vkso_context vkso_kernel_context;

int vkso_posix_clock_gettime_failure(
	s32 clock_id, struct vkso_time_value *value,
	const struct vkso_mm_data *mm_data);
int vkso_kernel_gettimeofday_failure(
	struct vkso_timeval *tv, struct vkso_timezone *tz, int status);
void vkso_time_update_timezone(void);
void vkso_time_join_namespace(struct task_struct *task,
			      struct time_namespace *ns);
void vkso_time_set_pvclock_page(const void *page);
void vkso_time_set_hvclock_page(const void *page);
#ifdef CONFIG_VKSO_TIME_TEST
int vkso_timekeeping_writer_context_selftest(void);
#endif

/*
 * Ordinary kernel readers use only known shared clocks and select root-
 * namespace semantics with a NULL MM_data pointer. Dynamic clock IDs are
 * classified by the POSIX dispatcher. Special NMI, writer-locked and
 * early-boot readers remain on their private paths.
 *
 * This is a completing kernel adapter, not a provider probe. The fixed kernel
 * failure callback completes a private read when the shared provider fails.
 * Thus callers do not retry the same fallback. User adapters still propagate
 * their own syscall/errno results.
 */
static __always_inline void
vkso_time_get_root_hres(s32 clock_id, struct timespec64 *tp)
{
	struct vkso_time_value *value = (struct vkso_time_value *)tp;

	(void)vkso_clock_gettime_hres(clock_id, value, NULL,
				      &vkso_kernel_context);
}

static __always_inline void
vkso_time_get_root_coarse(s32 clock_id, struct timespec64 *tp)
{
	(void)vkso_clock_gettime_coarse(
		clock_id, (struct vkso_time_value *)tp, NULL);
}

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
