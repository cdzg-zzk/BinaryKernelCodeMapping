/* SPDX-License-Identifier: GPL-2.0 */
#ifndef VKSO_TEST_ABI_H
#define VKSO_TEST_ABI_H

#include <stdint.h>

#define AT_VKSO_MM_DATA 52
#define VKSO_TIME_ABI_VERSION 11U
#define VKSO_MM_DATA_ABI_VERSION 3U
#define VKSO_TIME_OK 0
#define VKSO_TIME_UNSUPPORTED_MODE (-1)
#define VKSO_TIME_BACKEND_REQUIRED (-2)

struct vkso_time_value {
	int64_t sec;
	uint64_t nsec;
} __attribute__((__may_alias__));

struct vkso_timeval {
	int64_t sec;
	int64_t usec;
} __attribute__((__may_alias__));

struct vkso_timezone {
	int32_t minuteswest;
	int32_t dsttime;
} __attribute__((__may_alias__));

struct vkso_hres_base {
	int64_t sec;
	uint64_t shifted_nsec;
};

struct vkso_cycle_data {
	int32_t clock_mode;
	uint32_t shift;
	uint64_t cycle_last;
	uint64_t mask;
	uint32_t mono_mult;
	uint32_t raw_mult;
};

struct vkso_read_state {
	struct vkso_cycle_data cycles;
	struct vkso_hres_base realtime_base;
	struct vkso_hres_base monotonic_base;
	struct vkso_hres_base boottime_base;
	struct vkso_hres_base tai_base;
	struct vkso_time_value realtime_coarse;
	uint32_t hrtimer_resolution;
	uint32_t clocksource_resolution;
	struct vkso_hres_base monotonic_raw_base;
	struct vkso_time_value monotonic_coarse;
	struct vkso_timezone timezone;
};

struct vkso_shared_data {
	uint32_t seq;
	uint32_t abi_version;
	struct vkso_read_state state;
};

struct vkso_mm_data {
	uint32_t abi_version;
	uint32_t clock_mask;
	struct vkso_time_value monotonic_offset;
	struct vkso_time_value boottime_offset;
};

struct vkso_context {
	const void *pvclock_page;
	const void *hvclock_page;
};

int vkso_clock_gettime_core(
	int clock_id, struct vkso_time_value *value,
	const struct vkso_mm_data *mm_data,
	const struct vkso_context *context);
int vkso_clock_getres_core(int clock_id, struct vkso_time_value *value);
int vkso_clock_gettime_realtime(
	struct vkso_time_value *value, const struct vkso_context *context);
int vkso_clock_gettime_monotonic(
	struct vkso_time_value *value, const struct vkso_context *context);
int vkso_clock_gettime_monotonic_raw(
	struct vkso_time_value *value, const struct vkso_context *context);
int vkso_clock_gettime_boottime(
	struct vkso_time_value *value, const struct vkso_context *context);
int vkso_clock_gettime_tai(
	struct vkso_time_value *value, const struct vkso_context *context);
int vkso_clock_gettime_realtime_coarse(struct vkso_time_value *value);
int vkso_clock_gettime_monotonic_coarse(struct vkso_time_value *value);
int vkso_clock_gettime_boottime_coarse(struct vkso_time_value *value);
int vkso_clock_gettime_tai_coarse(struct vkso_time_value *value);
int vkso_clock_getres_hres(struct vkso_time_value *value);
int vkso_clock_getres_coarse(struct vkso_time_value *value);
int vkso_time_apply_offset(
	const struct vkso_time_value *offset,
	struct vkso_time_value *value);
int vkso_gettimeofday_core(
	struct vkso_timeval *tv, struct vkso_timezone *tz,
	const struct vkso_context *context);

/* Standard user ABI exported by the private libkernel.so entry page. */
int __vkso_clock_gettime(int clock_id, struct vkso_time_value *value);
int __vkso_clock_getres(int clock_id, struct vkso_time_value *value);
int __vkso_gettimeofday(struct vkso_timeval *tv,
			struct vkso_timezone *tz);
int __vkso_bind_context(const struct vkso_mm_data *mm_data,
			const void *pvclock_page, const void *hvclock_page);
const void *__vkso_shared_data(void);
int64_t __vkso_time(int64_t *tloc);
int __vkso_getcpu(unsigned int *cpu, unsigned int *node, void *unused);

#endif /* VKSO_TEST_ABI_H */
