/* SPDX-License-Identifier: GPL-2.0 */
#ifndef VKSO_USER_WRAPPER_H
#define VKSO_USER_WRAPPER_H

#include <sys/time.h>
#include <time.h>

/* Bind auxv-provided per-MM state to libkernel.so once per process image. */
int vkso_user_wrapper_init(void);

/* Compatibility names for tests that predate the standard DSO exports. */
int vkso_user_clock_gettime(clockid_t clock_id, struct timespec *value);
int vkso_user_clock_getres(clockid_t clock_id, struct timespec *value);
int vkso_user_gettimeofday(struct timeval *tv, struct timezone *tz);
time_t vkso_user_time(time_t *tloc);
int vkso_user_getcpu(unsigned int *cpu, unsigned int *node, void *unused);

#endif /* VKSO_USER_WRAPPER_H */
