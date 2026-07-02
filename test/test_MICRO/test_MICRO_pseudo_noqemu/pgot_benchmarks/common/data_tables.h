#ifndef PGOT_BENCH_DATA_TABLES_H
#define PGOT_BENCH_DATA_TABLES_H

#include "bench_common.h"

#define PGOT_DATA_SLOTS 16
#define PGOT_CHAIN_SLOTS 4096

static uint64_t direct_values[PGOT_DATA_SLOTS] ALIGNED64;
static uint64_t *pgot_data_table[PGOT_DATA_SLOTS] ALIGNED64;

static uint64_t chain_values[PGOT_CHAIN_SLOTS] ALIGNED64;
static uint64_t *pgot_chain_table[PGOT_CHAIN_SLOTS] ALIGNED64;

static inline void init_data_tables(void)
{
    for (size_t i = 0; i < PGOT_DATA_SLOTS; i++) {
        direct_values[i] = 0x100000001b3ULL + i * 97u;
        pgot_data_table[i] = &direct_values[i];
    }

    uint32_t x = 0x13579bdfu;
    for (size_t i = 0; i < PGOT_CHAIN_SLOTS; i++) {
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        chain_values[i] = x & (PGOT_CHAIN_SLOTS - 1);
    }
    for (size_t i = 0; i < PGOT_CHAIN_SLOTS; i++)
        pgot_chain_table[i] = &chain_values[i];

    compiler_barrier();
}

#endif
