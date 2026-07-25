/* SPDX-License-Identifier: GPL-2.0 */
#ifndef VKSO_TEST_ABI_H
#define VKSO_TEST_ABI_H

#include <stdint.h>

#define AT_VKSO_MM_DATA 52
#define VKSO_MM_DATA_ABI_VERSION 3U
#define VKSO_TIME_OK 0

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

enum vkso_fallback_mode {
	VKSO_FALLBACK_RETURN,
	VKSO_FALLBACK_SYSCALL,
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
	uint32_t fallback_mode;
	uint32_t reserved;
};

int vkso_clock_gettime_core(
	const struct vkso_mm_data *mm_data, int clock_id,
	struct vkso_time_value *value,
	const struct vkso_context *context);
int vkso_clock_getres_core(int clock_id, struct vkso_time_value *value,
			   const struct vkso_context *context);
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
int64_t __vkso_time(int64_t *tloc);
int __vkso_getcpu(unsigned int *cpu, unsigned int *node, void *unused);

#endif /* VKSO_TEST_ABI_H */
