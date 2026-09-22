// SPDX-License-Identifier: GPL-2.0
/* TEST ONLY. Not kernel-backed; never use these values as performance data. */
#include <errno.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>
#include "vkso_abi.h"

const int vkso_test_only_mock_carrier = 1;
static struct vkso_shared_data shared = {.abi_version = VKSO_TIME_ABI_VERSION};
static struct vkso_mm_data mm = {.abi_version = VKSO_MM_DATA_ABI_VERSION};
static atomic_int binds, reads;
static _Thread_local int forced_error;
static _Thread_local int64_t seconds = 1700000000;
static int mode(const char *name)
{
	const char *value = getenv("VKSO_TEST_MODE");
	return value && strcmp(name, value) == 0;
}
unsigned long getauxval(unsigned long tag)
{
	if (tag != AT_VKSO_MM_DATA || mode("missing")) { errno = ENOENT; return 0; }
	if (mode("mm-version")) mm.abi_version = 0;
	if (mode("mask")) mm.clock_mask = 1U << 31;
	return (unsigned long)&mm;
}
const void *__vkso_shared_data(void)
{
	atomic_fetch_add(&reads, 1);
	if (mode("shared-version")) shared.abi_version = 0;
	return &shared;
}
int __vkso_bind_context(const struct vkso_mm_data *data, const void *pv, const void *hv)
{
	atomic_fetch_add(&binds, 1);
	if (mode("bind")) { errno = EIO; return -1; }
	if (data != &mm || pv || hv) { errno = EPROTO; return -1; }
	return 0;
}
int __vkso_clock_gettime(int clock, struct vkso_time_value *value)
{
	if (forced_error) return -forced_error;
	if (clock == -1) return -EINVAL;
	*value = (struct vkso_time_value){42, 123};
	return 0;
}
int __vkso_clock_getres(int clock, struct vkso_time_value *value)
{
	if (forced_error) return -forced_error;
	if (clock == -1) return -EINVAL;
	if (value) *value = (struct vkso_time_value){0, 1};
	return 0;
}
int __vkso_gettimeofday(struct vkso_timeval *tv, struct vkso_timezone *tz)
{
	if (forced_error) return -forced_error;
	if (tv) *tv = (struct vkso_timeval){42, 1234};
	if (tz) *tz = (struct vkso_timezone){0, 0};
	return 0;
}
int64_t __vkso_time(int64_t *ptr) { if (ptr) *ptr = seconds; return seconds; }
int __vkso_getcpu(unsigned *cpu, unsigned *node, void *unused)
{
	if (forced_error) return -forced_error;
	if (unused) return -EINVAL;
	if (cpu) *cpu = 7;
	if (node) *node = 0;
	return 0;
}
int mock_binds(void) { return atomic_load(&binds); }
int mock_reads(void) { return atomic_load(&reads); }
void mock_error(int error) { forced_error = error; }
void mock_seconds(int64_t value) { seconds = value; }
