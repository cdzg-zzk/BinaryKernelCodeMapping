/* SPDX-License-Identifier: GPL-2.0 */
#ifndef VKSO_USER_WRAPPER_H
#define VKSO_USER_WRAPPER_H

#include <sys/time.h>
#include <time.h>

/*
 * Hand-written user adapter used until make_dll grows wrapper generation.
 * These signatures, return values and fallback rules match the native vDSO
 * ABI; internal MM/counter context is deliberately not exposed.
 */
int vkso_user_wrapper_init(void);
int vkso_user_clock_gettime(clockid_t clock_id, struct timespec *value);
int vkso_user_clock_getres(clockid_t clock_id, struct timespec *value);
int vkso_user_gettimeofday(struct timeval *tv, struct timezone *tz);
time_t vkso_user_time(time_t *tloc);
int vkso_user_getcpu(unsigned int *cpu, unsigned int *node, void *unused);

#endif /* VKSO_USER_WRAPPER_H */
