// SPDX-License-Identifier: GPL-2.0
#define _GNU_SOURCE
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <sys/mman.h>
#include "vkso_time.h"

extern unsigned char vkso_shared_page[4096];
extern struct vkso_mm_data fixture_mm;
extern int fixture_aux_missing, fixture_failure;
extern int64_t fixture_seconds;
static unsigned checks;
#define CHECK(condition) do { assert(condition); ++checks; } while (0)

static void *thread_error(void *unused)
{
    (void)unused;
    struct timespec v;
    errno = EBUSY;
    assert(vkso_clock_gettime(-1, &v) == -1 && errno == EINVAL);
    errno = ERANGE;
    assert(vkso_clock_gettime(CLOCK_MONOTONIC, &v) == 0 && errno == ERANGE);
    return NULL;
}
int main(void)
{
    struct vkso_shared_data *shared = (void *)vkso_shared_page;
    fixture_aux_missing = 1;
    CHECK(mprotect(vkso_shared_page, 4096, PROT_NONE) == 0);
    CHECK(vkso_time_init() == -1 && errno == ENOSYS);
    CHECK(mprotect(vkso_shared_page, 4096, PROT_READ | PROT_WRITE) == 0);
    fixture_aux_missing = 0;
    shared->abi_version = 0;
    CHECK(vkso_time_init() == -1 && errno == EPROTO);
    shared->abi_version = VKSO_TIME_ABI_VERSION;
    fixture_mm.abi_version = 0;
    CHECK(vkso_time_init() == -1 && errno == EPROTO);
    fixture_mm.abi_version = VKSO_MM_DATA_ABI_VERSION;
    fixture_mm.clock_mask = 1U << 31;
    CHECK(vkso_time_init() == -1 && errno == EPROTO);
    fixture_mm.clock_mask = 0;
    errno = EBUSY;
    CHECK(vkso_time_init() == 0 && errno == EBUSY);
    struct timespec v;
    const clockid_t clocks[] = {CLOCK_REALTIME, CLOCK_MONOTONIC, CLOCK_MONOTONIC_RAW,
        CLOCK_BOOTTIME, CLOCK_TAI, CLOCK_REALTIME_COARSE, CLOCK_MONOTONIC_COARSE};
    for (unsigned i = 0; i < sizeof(clocks) / sizeof(clocks[0]); ++i) {
        errno = EBUSY;
        CHECK(vkso_clock_gettime(clocks[i], &v) == 0 && errno == EBUSY);
        CHECK(v.tv_sec == fixture_seconds && v.tv_nsec >= 0 && v.tv_nsec < 1000000000);
    }
    CHECK(vkso_clock_gettime(-1, &v) == -1 && errno == EINVAL);
    CHECK(vkso_clock_gettime(1000, &v) == -1 && errno == EINVAL);
    CHECK(vkso_clock_getres(-1, &v) == -1 && errno == EINVAL);
    CHECK(vkso_clock_getres(CLOCK_REALTIME, NULL) == 0);
    CHECK(vkso_clock_getres(CLOCK_REALTIME_COARSE, &v) == 0 && v.tv_nsec == 1000000);
    CHECK(vkso_clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &v) == 0);
    CHECK(vkso_clock_getres(CLOCK_PROCESS_CPUTIME_ID, &v) == 0);
    struct timeval tv;
    struct vkso_timezone tz;
    CHECK(vkso_gettimeofday(&tv, &tz) == 0 && tv.tv_sec == fixture_seconds);
    fixture_failure = 1;
    CHECK(vkso_clock_gettime(CLOCK_MONOTONIC, &v) == 0 && v.tv_sec != fixture_seconds);
    CHECK(vkso_gettimeofday(&tv, NULL) == 0 && tv.tv_sec != fixture_seconds);
    fixture_failure = 0;
    fixture_seconds = -2;
    time_t seconds;
    errno = EBUSY;
    CHECK(vkso_time(&seconds) == -2 && seconds == -2 && errno == EBUSY);
    CHECK(vkso_time(NULL) == -2 && errno == EBUSY);
    unsigned int cpu, node;
    CHECK(vkso_getcpu(&cpu, &node) == 0);
    CHECK(vkso_getcpu(NULL, NULL) == 0);
    pthread_t thread;
    errno = EDOM;
    CHECK(pthread_create(&thread, NULL, thread_error, NULL) == 0);
    CHECK(pthread_join(thread, NULL) == 0 && errno == EDOM);
    printf("mock_assembly_api_checks=%u PASS (not kernel validation)\n", checks);
    return 0;
}
