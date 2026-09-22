#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <stddef.h>
#include <stdio.h>
#include <sys/prctl.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

static void forbid_time_syscalls(void)
{
    struct sock_filter code[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, SYS_clock_gettime, 4, 0),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, SYS_clock_getres, 3, 0),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, SYS_gettimeofday, 2, 0),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, SYS_time, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
    };
    struct sock_fprog p = { .len = sizeof(code) / sizeof(code[0]), .filter = code };
    assert(prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) == 0);
    assert(prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &p) == 0);
}
static long long ns(struct timespec t) { return t.tv_sec * 1000000000LL + t.tv_nsec; }
int main(int argc, char **argv)
{
    if (argc > 1) {
        forbid_time_syscalls();
        execv(argv[1], argv + 1);
        return 125;
    }
    int clocks[] = {0, 1, 4, 5, 6, 7, 11};
    struct timespec a, t, b;
    for (unsigned i = 0; i < sizeof(clocks) / sizeof(clocks[0]); i++) {
        assert(syscall(SYS_clock_gettime, clocks[i], &a) == 0);
        errno = EDOM;
        assert(clock_gettime(clocks[i], &t) == 0 && errno == EDOM);
        assert(syscall(SYS_clock_gettime, clocks[i], &b) == 0);
        assert(ns(a) <= ns(t) && ns(t) <= ns(b));
    }
    errno = 0;
    assert(clock_gettime(-123, &t) == -1 && errno == EINVAL);
    errno = 0;
    assert(clock_getres(-123, &t) == -1 && errno == EINVAL);
    assert(clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &t) == 0);
    forbid_time_syscalls();
    assert(syscall(SYS_clock_gettime, CLOCK_MONOTONIC, &t) == -1 && errno == EPERM);
    for (unsigned i = 0; i < sizeof(clocks) / sizeof(clocks[0]); i++) {
        assert(clock_gettime(clocks[i], &t) == 0);
        assert(clock_getres(clocks[i], &t) == 0);
    }
    struct timeval tv;
    assert(gettimeofday(&tv, NULL) == 0);
    time_t now;
    assert(time(&now) == now && now > 0);
    puts("adapter_check=pass errno,fallback,brackets,syscall-denied-fast-paths");
    return 0;
}
