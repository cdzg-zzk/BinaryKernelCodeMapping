/* SPDX-License-Identifier: GPL-2.0 */
#ifndef VKSO_TEST_ABI_H
#define VKSO_TEST_ABI_H

#include <stdint.h>

#define AT_VKSO_MM_DATA 52
#include "vkso_time_abi.h"

/* Standard user ABI exported by the private libkernel.so entry page. */
int __vkso_clock_gettime(int clock_id, struct vkso_time_value *value);
int __vkso_clock_getres(int clock_id, struct vkso_time_value *value);
int __vkso_gettimeofday(struct vkso_timeval *tv,
			struct vkso_timezone *tz);
int __vkso_bind_context(const struct vkso_mm_data *mm_data,
			const void *pvclock_page, const void *hvclock_page);
int __vkso_bind_gettimeofday_failure(
	vkso_gettimeofday_failure_t failure);
const void *__vkso_shared_data(void);
int64_t __vkso_time(int64_t *tloc);
int __vkso_getcpu(unsigned int *cpu, unsigned int *node, void *unused);

#endif /* VKSO_TEST_ABI_H */
