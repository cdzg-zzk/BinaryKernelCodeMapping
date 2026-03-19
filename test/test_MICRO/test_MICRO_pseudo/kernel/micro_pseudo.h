#ifndef MICRO_PSEUDO_H
#define MICRO_PSEUDO_H

#include <linux/types.h>

#define MICRO_PSEUDO_INPUT_BYTES 4096U
#define MICRO_PSEUDO_MAX_REPEATS 31U
#define MICRO_PSEUDO_MAX_WARMUP 64U
#define MICRO_PSEUDO_DEFAULT_INPUT_LEN 256U

enum micro_pseudo_variant_id {
	MICRO_VARIANT_KERNEL_NATIVE = 0,
	MICRO_VARIANT_KERNEL_MICRO,
	MICRO_VARIANT_COUNT,
};

struct micro_run_params {
	enum micro_pseudo_variant_id variant_id;
	u32 iters;
	u32 warmup;
	u32 repeat;
	u32 seed;
	u32 batch_iters;
	u32 input_len;
	int cpu;
};

struct micro_run_result {
	bool valid;
	int status;
	int requested_cpu;
	u32 actual_cpu;
	u32 iters;
	u32 warmup;
	u32 repeat;
	u32 batch_iters;
	u32 seed;
	u32 input_len;
	enum micro_pseudo_variant_id variant_id;
	u32 checksum;
	u64 total_bytes;
	u64 best_cycles;
	u64 median_cycles;
	u64 worst_cycles;
	u64 cycles_per_call_x1000;
	u64 cycles_per_byte_x1000;
	u64 samples[MICRO_PSEUDO_MAX_REPEATS];
	char message[128];
};

#endif
