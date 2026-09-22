// SPDX-License-Identifier: GPL-2.0
/* USER-SPACE TEST FIXTURE ONLY. No page grafting and no kernel execution.
 * The real assembly veneers are linked to these stub computations to test
 * calling conventions, context binding, errno and syscall exits. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdint.h>
#include <sys/syscall.h>
#include <unistd.h>
#include "vkso_abi.h"

const char vkso_fixture_marker[] = "NOT_A_KERNEL_CARRIER";
unsigned char vkso_shared_page[4096] __attribute__((aligned(4096)));
struct vkso_mm_data fixture_mm = { .abi_version = VKSO_MM_DATA_ABI_VERSION };
int fixture_aux_missing;
int fixture_failure;
int64_t fixture_seconds = 12345;

unsigned long getauxval(unsigned long tag)
{
    if (tag == AT_VKSO_MM_DATA && !fixture_aux_missing)
        return (unsigned long)&fixture_mm;
    errno = ENOENT;
    return 0;
}
int vkso_clock_gettime_hres(int32_t id, struct vkso_time_value *v,
                           const struct vkso_mm_data *mm,
                           const struct vkso_context *context)
{
    if (mm != &fixture_mm || !context || !context->clock_gettime_failure)
        return -EPROTO;
    if (fixture_failure) return context->clock_gettime_failure(id, v, mm);
    v->sec = fixture_seconds; v->nsec = 123;
    return 0;
}
int vkso_clock_gettime_coarse(int32_t id, struct vkso_time_value *v,
                             const struct vkso_mm_data *mm)
{
    (void)id;
    if (mm != &fixture_mm) return -EPROTO;
    v->sec = fixture_seconds; v->nsec = 456;
    return 0;
}
int vkso_clock_getres_hres(struct vkso_time_value *v)
{
    if (v) { v->sec = 0; v->nsec = 1; }
    return 0;
}
int vkso_clock_getres_coarse(struct vkso_time_value *v)
{
    if (v) { v->sec = 0; v->nsec = 1000000; }
    return 0;
}
int vkso_gettimeofday_core(struct vkso_timeval *tv, struct vkso_timezone *tz,
                          const struct vkso_context *context)
{
    if (!context || !context->gettimeofday_failure) return -EPROTO;
    if (fixture_failure) return context->gettimeofday_failure(tv, tz, -1);
    if (tv) { tv->sec = fixture_seconds; tv->usec = 123; }
    if (tz) { tz->minuteswest = 0; tz->dsttime = 0; }
    return 0;
}
int64_t __vkso_time(int64_t *value)
{
    if (value) *value = fixture_seconds;
    return fixture_seconds;
}
int __vkso_getcpu(unsigned int *cpu, unsigned int *node, void *unused)
{
    (void)unused;
    if (syscall(SYS_getcpu, cpu, node, NULL)) return -errno;
    return 0;
}
__attribute__((constructor)) static void initialize_fixture(void)
{
    ((struct vkso_shared_data *)vkso_shared_page)->abi_version = VKSO_TIME_ABI_VERSION;
}
