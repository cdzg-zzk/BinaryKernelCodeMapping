/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_TIME_H
#define _LINUX_VKSO_TIME_H

#include <linux/time64.h>
#include <linux/vkso.h>
#include <vkso/time.h>

struct mm_struct;
struct task_struct;
struct timens_offsets;

void vkso_timekeeping_get_private(clockid_t clock_id, bool coarse,
				   struct timespec64 *ts);

#ifdef CONFIG_VKSO_TIME
extern union vkso_shared_page vkso_shared_page;
extern struct vkso_context vkso_kernel_context;

void vkso_time_publish(const struct vkso_read_state *state);
void vkso_time_update_timezone(void);
void vkso_time_update_mm_data(struct task_struct *task,
			      const struct timens_offsets *offsets);
void vkso_time_set_pvclock_page(const void *page);
void vkso_time_set_hvclock_page(const void *page);
#ifdef CONFIG_VKSO_TIME_TEST
int vkso_timekeeping_writer_context_selftest(void);
#endif

static __always_inline int
vkso_time_get(const struct vkso_mm_data *mm_data, clockid_t clock_id,
	      struct timespec64 *tp)
{
	return vkso_clock_gettime_core(clock_id,
				      (struct vkso_time_value *)tp, mm_data,
				      &vkso_kernel_context);
}

/*
 * A typed root reader names the clock at the call site. These two adapters
 * only bridge the kernel result type and environment; they compile to a
 * direct call and never inspect MM_data or a generic clock ID.
 */
#define vkso_time_get_root_hres(reader, tp)				\
	(reader)((struct vkso_time_value *)(tp), &vkso_kernel_context)
#define vkso_time_get_root_coarse(reader, tp)				\
	(reader)((struct vkso_time_value *)(tp))

static __always_inline int vkso_time_get_root_resolution(u32 *nsec)
{
	struct vkso_time_value value;
	int status;

	status = vkso_clock_getres_hres(&value);
	if (likely(status == VKSO_TIME_OK))
		*nsec = value.nsec;
	return status;
}

static __always_inline int
vkso_time_get_root_monotonic_seconds(time64_t *seconds)
{
	*seconds = READ_ONCE(
		vkso_shared_page.data.state.monotonic_coarse.sec);
	return VKSO_TIME_OK;
}

static __always_inline int
vkso_time_get_root_realtime_seconds(time64_t *seconds)
{
	*seconds = READ_ONCE(vkso_shared_page.data.state.realtime_base.sec);
	return VKSO_TIME_OK;
}

static __always_inline int
vkso_time_getres(clockid_t clock_id, struct timespec64 *tp)
{
	return vkso_clock_getres_core(clock_id,
				      (struct vkso_time_value *)tp);
}

static __always_inline int
vkso_time_gettimeofday(struct __kernel_old_timeval *tv, struct timezone *tz)
{
	return vkso_gettimeofday_core((struct vkso_timeval *)tv,
				      (struct vkso_timezone *)tz,
				      &vkso_kernel_context);
}

static __always_inline int vkso_time_get_seconds(__kernel_old_time_t *value)
{
	*value = (__kernel_old_time_t)__vkso_time(NULL);
	return VKSO_TIME_OK;
}
#else
static inline void vkso_time_publish(const struct vkso_read_state *state)
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
	return VKSO_TIME_BACKEND_REQUIRED;
}

static inline int
vkso_time_getres(clockid_t clock_id, struct timespec64 *tp)
{
	return VKSO_TIME_BACKEND_REQUIRED;
}

#define vkso_time_get_root_hres(reader, tp) VKSO_TIME_BACKEND_REQUIRED
#define vkso_time_get_root_coarse(reader, tp) VKSO_TIME_BACKEND_REQUIRED

static inline int vkso_time_get_root_resolution(u32 *nsec)
{
	return VKSO_TIME_BACKEND_REQUIRED;
}

static inline int
vkso_time_get_root_monotonic_seconds(time64_t *seconds)
{
	return VKSO_TIME_BACKEND_REQUIRED;
}

static inline int
vkso_time_get_root_realtime_seconds(time64_t *seconds)
{
	return VKSO_TIME_BACKEND_REQUIRED;
}

static inline int
vkso_time_gettimeofday(struct __kernel_old_timeval *tv, struct timezone *tz)
{
	return VKSO_TIME_BACKEND_REQUIRED;
}

static inline int vkso_time_get_seconds(__kernel_old_time_t *value)
{
	return VKSO_TIME_BACKEND_REQUIRED;
}

static inline void
vkso_time_update_mm_data(struct task_struct *task,
			 const struct timens_offsets *offsets)
{
}
#endif

#endif /* _LINUX_VKSO_TIME_H */
