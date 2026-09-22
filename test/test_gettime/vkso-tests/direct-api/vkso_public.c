// SPDX-License-Identifier: GPL-2.0
/* Conventional dynamically linked API. The carrier's fallback uses raw syscalls,
 * never these public symbols. Initialization is explicit, before first use. */
#include "vkso_time.h"
int clock_gettime(clockid_t c, struct timespec *v) { return vkso_time_clock_gettime(c, v); }
int clock_getres(clockid_t c, struct timespec *v) { return vkso_time_clock_getres(c, v); }
int gettimeofday(struct timeval *v, void *tz) { (void)tz; return vkso_time_gettimeofday(v, NULL); }
time_t time(time_t *v) { return vkso_time_time(v); }
int getcpu(unsigned *cpu, unsigned *node) { return vkso_time_getcpu(cpu, node); }
