/* SPDX-License-Identifier: GPL-2.0
 * Shared control layout (u64): ready, stop, batches. No control syscalls occur
 * between batches. Writer's recorded interval is nested inside this load run.
 * Batch samples are retained in memory and emitted only after stop.
 */
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#ifdef USE_VKSO
#include "vkso_time.h"
#endif
#define CAPACITY 262144
struct sample { uint64_t ticks; unsigned start, end; };
static struct sample samples[CAPACITY];
static uint64_t stamp(unsigned *aux)
{
    unsigned lo, hi, cpu;
    __asm__ __volatile__("lfence; rdtscp; lfence" : "=a"(lo), "=d"(hi), "=c"(cpu) :: "memory");
    *aux = cpu;
    return ((uint64_t)hi << 32) | lo;
}
static unsigned number(const char *s)
{
    char *end; errno = 0;
    unsigned long n = strtoul(s, &end, 10);
    if (errno || !*s || *end || n > 1000000) { fprintf(stderr,"invalid number\n"); exit(2); }
    return n;
}
int main(int argc, char **argv)
{
    if (argc != 6) { fprintf(stderr,"usage: load CONTROL CPU OP BATCH WARMUP\n"); return 2; }
    unsigned cpu = number(argv[2]), batch = number(argv[4]), warm = number(argv[5]);
    if (cpu >= CPU_SETSIZE || !batch) return 2;
    clockid_t clock;
    if (!strcmp(argv[3], "monotonic")) clock = CLOCK_MONOTONIC;
    else if (!strcmp(argv[3], "monotonic_raw")) clock = CLOCK_MONOTONIC_RAW;
    else if (!strcmp(argv[3], "monotonic_coarse")) clock = CLOCK_MONOTONIC_COARSE;
    else return 2;
    cpu_set_t set; CPU_ZERO(&set); CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof(set), &set)) { perror("affinity"); return 1; }
    int fd = open(argv[1], O_RDWR);
    if (fd < 0) return 1;
    uint64_t *control = mmap(NULL, 4096, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    if (control == MAP_FAILED) return 1;
#ifdef USE_VKSO
    if (vkso_time_init()) { perror("vkso_time_init"); return 1; }
#endif
    /* First touch all storage before READY. */
    memset(samples, 0xff, sizeof(samples));
    struct timespec ts;
    for (unsigned i = 0; i < warm + 1; ++i)
        if (clock_gettime(clock, &ts)) return 1;
    __atomic_store_n(&control[0], 1, __ATOMIC_RELEASE);
    size_t count = 0;
    while (!__atomic_load_n(&control[1], __ATOMIC_ACQUIRE)) {
        if (count == CAPACITY) { fprintf(stderr,"sample capacity exhausted\n"); return 1; }
        unsigned a, b;
        uint64_t start = stamp(&a);
        for (unsigned i = 0; i < batch; ++i)
            if (clock_gettime(clock, &ts)) return 1;
        uint64_t end = stamp(&b);
        if (a != b || end <= start) { fprintf(stderr,"migration/counter reversal\n"); return 1; }
        samples[count++] = (struct sample){end-start, a, b};
        __atomic_store_n(&control[2], count, __ATOMIC_RELEASE);
    }
    puts("batch,calls,tsc_ticks,aux_start,aux_end");
    for (size_t i = 0; i < count; ++i)
        printf("%zu,%u,%"PRIu64",%u,%u\n",i,batch,samples[i].ticks,samples[i].start,samples[i].end);
    munmap(control,4096);
    return count ? 0 : 1;
}
