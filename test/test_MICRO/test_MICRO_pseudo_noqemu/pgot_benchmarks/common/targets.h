#ifndef PGOT_BENCH_TARGETS_H
#define PGOT_BENCH_TARGETS_H

#include "bench_common.h"

typedef uint64_t (*bench_fn_t)(uint64_t);

NOINLINE USED NOIPA static uint64_t target_0(uint64_t x) { return (x * 3u) + 1u; }
NOINLINE USED NOIPA static uint64_t target_1(uint64_t x) { return (x * 5u) ^ 0x11u; }
NOINLINE USED NOIPA static uint64_t target_2(uint64_t x) { return (x + 0x1234u) ^ (x >> 7); }
NOINLINE USED NOIPA static uint64_t target_3(uint64_t x) { return (x ^ 0x55aa55aaULL) + (x << 1); }
NOINLINE USED NOIPA static uint64_t target_4(uint64_t x) { return (x * 7u) - 3u; }
NOINLINE USED NOIPA static uint64_t target_5(uint64_t x) { return (x + 0x9e37u) ^ (x << 3); }
NOINLINE USED NOIPA static uint64_t target_6(uint64_t x) { return (x - 0x42u) * 11u; }
NOINLINE USED NOIPA static uint64_t target_7(uint64_t x) { return (x ^ (x >> 11)) + 17u; }
NOINLINE USED NOIPA static uint64_t target_8(uint64_t x) { return (x * 13u) ^ 0x3333u; }
NOINLINE USED NOIPA static uint64_t target_9(uint64_t x) { return (x + (x << 5)) ^ 0x7777u; }
NOINLINE USED NOIPA static uint64_t target_10(uint64_t x) { return (x - (x >> 3)) + 101u; }
NOINLINE USED NOIPA static uint64_t target_11(uint64_t x) { return (x ^ 0xff00ff00ULL) * 3u; }
NOINLINE USED NOIPA static uint64_t target_12(uint64_t x) { return (x + 19u) ^ (x << 9); }
NOINLINE USED NOIPA static uint64_t target_13(uint64_t x) { return (x * 17u) + (x >> 5); }
NOINLINE USED NOIPA static uint64_t target_14(uint64_t x) { return (x ^ (x << 13)) - 29u; }
NOINLINE USED NOIPA static uint64_t target_15(uint64_t x) { return (x + 31u) * 19u; }

static bench_fn_t target_table[16] ALIGNED64 = {
    target_0, target_1, target_2, target_3,
    target_4, target_5, target_6, target_7,
    target_8, target_9, target_10, target_11,
    target_12, target_13, target_14, target_15,
};

static bench_fn_t pgot_func_table[16] ALIGNED64;

static inline void init_pgot_func_table(void)
{
    for (size_t i = 0; i < 16; i++)
        pgot_func_table[i] = target_table[i];
    compiler_barrier();
}

#endif
