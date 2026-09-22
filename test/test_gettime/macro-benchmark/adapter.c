/* Experiment-only x86-64 libc bridge. Both providers use the same bridge. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>
#include "vkso_abi.h"

static long raw_result(long r) { return r == -1 ? -errno : r; }
static int early_clock(clockid_t c, struct timespec *t)
{ return raw_result(syscall(SYS_clock_gettime, c, t)); }
static int early_res(clockid_t c, struct timespec *t)
{ return raw_result(syscall(SYS_clock_getres, c, t)); }
static int early_gtod(struct timeval *t, void *z)
{ return raw_result(syscall(SYS_gettimeofday, t, z)); }
static time_t early_time(time_t *t)
{ return raw_result(syscall(SYS_time, t)); }
static int (*provider_clock)(clockid_t, struct timespec *) = early_clock;
static int (*provider_res)(clockid_t, struct timespec *) = early_res;
static int (*provider_gtod)(struct timeval *, void *) = early_gtod;
static time_t (*provider_time)(time_t *) = early_time;

#ifdef CLOCKTIME_AUDIT
static unsigned long counts[4], clocks[16];
#define COUNT(i) __atomic_fetch_add(&counts[i], 1, __ATOMIC_RELAXED)
static void __attribute__((destructor)) report(void)
{
    const char *path = getenv("CLOCKTIME_AUDIT_FILE");
    FILE *f = path ? fopen(path, "w") : NULL;
    if (!f) _exit(120);
    fprintf(f, "{\"backend\":\"%s\",\"clock_gettime\":%lu,\"clock_getres\":%lu,"
            "\"gettimeofday\":%lu,\"time\":%lu,\"clock_ids\":[",
            getenv("CLOCKTIME_BACKEND"), counts[0], counts[1], counts[2], counts[3]);
    for (int i = 0; i < 16; i++) fprintf(f, "%s%lu", i ? "," : "", clocks[i]);
    fputs("]}\n", f); fclose(f);
}
#else
#define COUNT(i) ((void)0)
#endif

static long libc_result(long r)
{
    if ((unsigned long)r >= (unsigned long)-4095) { errno = -r; return -1; }
    return r;
}
int clock_gettime(clockid_t c, struct timespec *t)
{
    COUNT(0);
#ifdef CLOCKTIME_AUDIT
    if ((unsigned)c < 16) __atomic_fetch_add(&clocks[c], 1, __ATOMIC_RELAXED);
#endif
    return libc_result(provider_clock(c, t));
}
int clock_getres(clockid_t c, struct timespec *t)
{ COUNT(1); return libc_result(provider_res(c, t)); }
int gettimeofday(struct timeval *t, void *z)
{ COUNT(2); return libc_result(provider_gtod(t, z)); }
time_t time(time_t *t)
{ COUNT(3); return libc_result(provider_time(t)); }

static void *symbol(void *handle, const char *name)
{
    void *p = dlsym(handle, name);
    if (!p) { fprintf(stderr, "clocktime: missing %s\n", name); _exit(121); }
    return p;
}
static void __attribute__((constructor)) initialize(void)
{
    const char *backend = getenv("CLOCKTIME_BACKEND");
    /* Identical client timing on both kernels, including those without vDSO. */
    if (backend && !strcmp(backend, "syscall")) return;
    int vkso = backend && !strcmp(backend, "vkso");
    if (!backend || (!vkso && strcmp(backend, "vdso"))) _exit(122);
    const char *path = vkso ? getenv("CLOCKTIME_CARRIER") : "linux-vdso.so.1";
    void *h = path ? dlopen(path, RTLD_NOW | RTLD_LOCAL) : NULL;
    if (!h) { fprintf(stderr, "clocktime: provider unavailable\n"); _exit(123); }
    if (vkso) {
        const struct vkso_mm_data *mm = (void *)getauxval(AT_VKSO_MM_DATA);
        const struct vkso_shared_data *(*shared)(void) = symbol(h, "__vkso_shared_data");
        int (*bind)(const void *, const void *, const void *) = symbol(h, "__vkso_bind_context");
        if (!mm || mm->abi_version != VKSO_MM_DATA_ABI_VERSION ||
            shared()->abi_version != VKSO_TIME_ABI_VERSION || bind(mm, NULL, NULL)) _exit(124);
    }
    provider_clock = symbol(h, vkso ? "__vkso_clock_gettime" : "__vdso_clock_gettime");
    provider_res = symbol(h, vkso ? "__vkso_clock_getres" : "__vdso_clock_getres");
    provider_gtod = symbol(h, vkso ? "__vkso_gettimeofday" : "__vdso_gettimeofday");
    provider_time = symbol(h, vkso ? "__vkso_time" : "__vdso_time");
}
