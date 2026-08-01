// SPDX-License-Identifier: GPL-2.0
#define _GNU_SOURCE

#include <dlfcn.h>
#include <elf.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <linux/perf_event.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#include "../functional/vkso_abi.h"
#include "../functional/vkso_user_wrapper.h"

#ifndef CLOCK_REALTIME_ALARM
#define CLOCK_REALTIME_ALARM 8
#endif
#define DEFAULT_ITERATIONS 500000U
#define DEFAULT_REPEATS 31U
#define DEFAULT_WARMUP 10000U
#define DEFAULT_SEQ_ITERATIONS 100000000U
#define DEFAULT_LAYOUT_ITERATIONS 200000U
#define DEFAULT_LOAD_SECONDS 10U
#define PMU_EVENT_COUNT 4U
#define RAW_VVAR_DATA_OFFSET 128U
#define RAW_VDSO_BASES 12U
#define RAW_CS_RAW 1U
#define READER_MEASUREMENT_WINDOW "direct-user-api-steady-batch-v3"
#define LOAD_MEASUREMENT_WINDOW "direct-user-api-conditioned-load-v4"

enum backend {
	BACKEND_RAW,
	BACKEND_VKSO,
};

enum mode {
	MODE_PERF,
	MODE_SEQ,
	MODE_LAYOUT,
	MODE_LOAD,
};

enum path {
	PATH_SYSCALL,
	PATH_RAW_VDSO,
	PATH_VKSO_WRAPPER,
};

enum operation {
	OP_CGT_REALTIME,
	OP_CGT_MONOTONIC,
	OP_CGT_MONOTONIC_RAW,
	OP_CGT_BOOTTIME,
	OP_CGT_TAI,
	OP_CGT_REALTIME_COARSE,
	OP_CGT_MONOTONIC_COARSE,
	OP_CGT_PROCESS_CPU,
	OP_CGT_REALTIME_ALARM,
	OP_CGR_REALTIME,
	OP_CGR_REALTIME_COARSE,
	OP_CGR_PROCESS_CPU,
	OP_GTOD_TV,
	OP_GTOD_TZ,
	OP_GTOD_BOTH,
	OP_GTOD_NULL,
	OP_TIME_NULL,
	OP_TIME_POINTER,
	OP_GETCPU_BOTH,
	OP_GETCPU_NULL,
	OP_COUNT,
};

struct operation_info {
	const char *name;
	clockid_t clock_id;
};

static const struct operation_info operations[OP_COUNT] = {
	[OP_CGT_REALTIME] = {
		"clock_gettime_realtime", CLOCK_REALTIME
	},
	[OP_CGT_MONOTONIC] = {
		"clock_gettime_monotonic", CLOCK_MONOTONIC
	},
	[OP_CGT_MONOTONIC_RAW] = {
		"clock_gettime_monotonic_raw", CLOCK_MONOTONIC_RAW
	},
	[OP_CGT_BOOTTIME] = {
		"clock_gettime_boottime", CLOCK_BOOTTIME
	},
	[OP_CGT_TAI] = {
		"clock_gettime_tai", CLOCK_TAI
	},
	[OP_CGT_REALTIME_COARSE] = {
		"clock_gettime_realtime_coarse", CLOCK_REALTIME_COARSE
	},
	[OP_CGT_MONOTONIC_COARSE] = {
		"clock_gettime_monotonic_coarse",
		CLOCK_MONOTONIC_COARSE
	},
	[OP_CGT_PROCESS_CPU] = {
		"clock_gettime_process_cpu_fallback",
		CLOCK_PROCESS_CPUTIME_ID
	},
	[OP_CGT_REALTIME_ALARM] = {
		"clock_gettime_realtime_alarm_fallback",
		CLOCK_REALTIME_ALARM
	},
	[OP_CGR_REALTIME] = {
		"clock_getres_realtime", CLOCK_REALTIME
	},
	[OP_CGR_REALTIME_COARSE] = {
		"clock_getres_realtime_coarse", CLOCK_REALTIME_COARSE
	},
	[OP_CGR_PROCESS_CPU] = {
		"clock_getres_process_cpu_fallback",
		CLOCK_PROCESS_CPUTIME_ID
	},
	[OP_GTOD_TV] = { "gettimeofday_tv", 0 },
	[OP_GTOD_TZ] = { "gettimeofday_timezone", 0 },
	[OP_GTOD_BOTH] = { "gettimeofday_both", 0 },
	[OP_GTOD_NULL] = { "gettimeofday_null", 0 },
	[OP_TIME_NULL] = { "time_null", 0 },
	[OP_TIME_POINTER] = { "time_pointer", 0 },
	[OP_GETCPU_BOTH] = { "getcpu_both", 0 },
	[OP_GETCPU_NULL] = { "getcpu_null", 0 },
};

static const char *const path_names[] = {
	[PATH_SYSCALL] = "syscall",
	[PATH_RAW_VDSO] = "raw_vdso",
	[PATH_VKSO_WRAPPER] = "vkso_wrapper",
};

typedef int (*vdso_clock_fn)(clockid_t, struct timespec *);
typedef int (*vdso_gettimeofday_fn)(struct timeval *, struct timezone *);
typedef time_t (*vdso_time_fn)(time_t *);
typedef int (*vdso_getcpu_fn)(unsigned int *, unsigned int *, void *);

struct user_time_functions {
	vdso_clock_fn clock_gettime;
	vdso_clock_fn clock_getres;
	vdso_gettimeofday_fn gettimeofday;
	vdso_time_fn time;
	vdso_getcpu_fn getcpu;
};

static struct user_time_functions user_time;
static const struct vkso_mm_data *vkso_mm_data;
static volatile uint64_t sink;

struct pmu_group {
	int leader;
	int descriptors[PMU_EVENT_COUNT];
};

struct pmu_reading {
	uint64_t nr;
	uint64_t time_enabled;
	uint64_t time_running;
	uint64_t values[PMU_EVENT_COUNT];
};

struct measurement {
	double tsc_cycles_per_call;
	double pmu_cycles_per_call;
	double instructions_per_call;
	double branches_per_call;
	double branch_misses_per_call;
	double cache_references_per_call;
	double cache_misses_per_call;
	double l1d_load_misses_per_call;
	double llc_load_misses_per_call;
};

struct raw_vdso_timestamp {
	uint64_t sec;
	uint64_t nsec;
};

struct raw_vdso_data {
	volatile uint32_t seq;
	int32_t clock_mode;
	volatile uint64_t cycle_last;
	uint64_t mask;
	volatile uint32_t mult;
	volatile uint32_t shift;
	struct raw_vdso_timestamp basetime[RAW_VDSO_BASES];
	int32_t tz_minuteswest;
	int32_t tz_dsttime;
	uint32_t hrtimer_res;
	uint32_t unused;
};

struct vkso_cycle_data_bench {
	int32_t clock_mode;
	volatile uint32_t shift;
	volatile uint64_t cycle_last;
	volatile uint64_t mask;
	volatile uint32_t mono_mult;
	volatile uint32_t raw_mult;
};

struct vkso_hres_base_bench {
	volatile int64_t sec;
	volatile uint64_t shifted_nsec;
};

struct vkso_read_state_bench {
	struct vkso_cycle_data_bench cycles;
	struct vkso_hres_base_bench realtime_base;
	struct vkso_hres_base_bench monotonic_base;
	struct vkso_hres_base_bench boottime_base;
	struct vkso_hres_base_bench tai_base;
	struct vkso_time_value realtime_coarse;
	uint32_t hrtimer_resolution;
	uint32_t clocksource_resolution;
	struct vkso_hres_base_bench monotonic_raw_base;
	struct vkso_time_value monotonic_coarse;
	struct vkso_timezone timezone;
};

struct vkso_shared_data_bench {
	volatile uint32_t seq;
	uint32_t abi_version;
	struct vkso_read_state_bench state;
};

_Static_assert(sizeof(struct raw_vdso_data) == 240,
	       "raw x86-64 vdso_data layout changed");
_Static_assert(sizeof(struct vkso_shared_data_bench) == 168,
	       "VKSO shared-data size changed");
_Static_assert(__builtin_offsetof(struct vkso_shared_data_bench,
				  state.monotonic_raw_base) == 128,
	       "VKSO raw layout changed");
_Static_assert(__builtin_offsetof(struct vkso_shared_data_bench,
				  state.realtime_base.sec) == 40,
	       "VKSO time seconds layout changed");

static struct pmu_group core_group = { .leader = -1 };
static struct pmu_group cache_group = { .leader = -1 };
static int pmu_enabled;

static void fail_message(const char *message)
{
	fprintf(stderr, "%s\n", message);
	exit(1);
}

static void die(const char *message)
{
	fprintf(stderr, "%s: %s\n", message, strerror(errno));
	exit(1);
}

static uint64_t parse_number(const char *value, const char *name,
			     int allow_zero)
{
	char *end;
	unsigned long long parsed;

	errno = 0;
	parsed = strtoull(value, &end, 10);
	if (errno || !*value || *end || (!allow_zero && !parsed) ||
	    parsed > UINT_MAX) {
		fprintf(stderr, "invalid %s: %s\n", name, value);
		exit(2);
	}
	return parsed;
}

static void pin_cpu(unsigned int cpu)
{
	cpu_set_t set;

	CPU_ZERO(&set);
	CPU_SET(cpu, &set);
	if (sched_setaffinity(0, sizeof(set), &set))
		die("sched_setaffinity");
}

static inline uint64_t tsc_begin(unsigned int *aux)
{
	uint32_t lo, hi;

	__asm__ volatile("lfence\n\trdtscp\n\tlfence"
			 : "=a"(lo), "=d"(hi), "=c"(*aux) :: "memory");
	return ((uint64_t)hi << 32) | lo;
}

static inline uint64_t tsc_end(unsigned int *aux)
{
	uint32_t lo, hi;

	__asm__ volatile("rdtscp\n\tlfence"
			 : "=a"(lo), "=d"(hi), "=c"(*aux) :: "memory");
	return ((uint64_t)hi << 32) | lo;
}

static inline uint64_t ordered_tsc(void)
{
	uint32_t lo, hi;

	__asm__ volatile("lfence\n\trdtsc"
			 : "=a"(lo), "=d"(hi) :: "memory");
	return ((uint64_t)hi << 32) | lo;
}

static inline long raw_syscall1(long number, long first)
{
	register long rax asm("rax") = number;
	register long rdi asm("rdi") = first;

	asm volatile("syscall"
		     : "+a"(rax)
		     : "D"(rdi)
		     : "rcx", "r11", "memory");
	return rax;
}

static inline long raw_syscall2(long number, long first, long second)
{
	register long rax asm("rax") = number;
	register long rdi asm("rdi") = first;
	register long rsi asm("rsi") = second;

	asm volatile("syscall"
		     : "+a"(rax)
		     : "D"(rdi), "S"(rsi)
		     : "rcx", "r11", "memory");
	return rax;
}

static inline long raw_syscall3(long number, long first, long second,
				long third)
{
	register long rax asm("rax") = number;
	register long rdi asm("rdi") = first;
	register long rsi asm("rsi") = second;
	register long rdx asm("rdx") = third;

	asm volatile("syscall"
		     : "+a"(rax)
		     : "D"(rdi), "S"(rsi), "d"(rdx)
		     : "rcx", "r11", "memory");
	return rax;
}

static void *vdso_lookup(const char *name)
{
	uintptr_t base = getauxval(AT_SYSINFO_EHDR);
	const Elf64_Ehdr *ehdr = (const Elf64_Ehdr *)base;
	const Elf64_Phdr *phdr;
	const Elf64_Dyn *dynamic = NULL;
	const Elf64_Sym *symtab = NULL;
	const char *strtab = NULL;
	const uint32_t *hash = NULL;
	size_t index;

	if (!base || memcmp(ehdr->e_ident, ELFMAG, SELFMAG) ||
	    ehdr->e_ident[EI_CLASS] != ELFCLASS64)
		return NULL;
	phdr = (const Elf64_Phdr *)(base + ehdr->e_phoff);
	for (index = 0; index < ehdr->e_phnum; ++index) {
		if (phdr[index].p_type == PT_DYNAMIC) {
			dynamic = (const Elf64_Dyn *)(base +
						    phdr[index].p_vaddr);
			break;
		}
	}
	if (!dynamic)
		return NULL;
	for (; dynamic->d_tag != DT_NULL; ++dynamic) {
		switch (dynamic->d_tag) {
		case DT_SYMTAB:
			symtab = (const Elf64_Sym *)(base + dynamic->d_un.d_ptr);
			break;
		case DT_STRTAB:
			strtab = (const char *)(base + dynamic->d_un.d_ptr);
			break;
		case DT_HASH:
			hash = (const uint32_t *)(base + dynamic->d_un.d_ptr);
			break;
		default:
			break;
		}
	}
	if (!symtab || !strtab || !hash)
		return NULL;
	for (index = 1; index < hash[1]; ++index) {
		if (symtab[index].st_shndx != SHN_UNDEF &&
		    !strcmp(strtab + symtab[index].st_name, name))
			return (void *)(base + symtab[index].st_value);
	}
	return NULL;
}

static void resolve_raw_vdso(void)
{
	user_time.clock_gettime =
		(vdso_clock_fn)vdso_lookup("__vdso_clock_gettime");
	user_time.clock_getres =
		(vdso_clock_fn)vdso_lookup("__vdso_clock_getres");
	user_time.gettimeofday =
		(vdso_gettimeofday_fn)vdso_lookup("__vdso_gettimeofday");
	user_time.time = (vdso_time_fn)vdso_lookup("__vdso_time");
	user_time.getcpu = (vdso_getcpu_fn)vdso_lookup("__vdso_getcpu");
	if (!user_time.clock_gettime || !user_time.clock_getres ||
	    !user_time.gettimeofday || !user_time.time ||
	    !user_time.getcpu)
		fail_message("raw vDSO is missing a required native symbol");
}

static void *lookup_vkso_symbol(const char *name)
{
	const char *error;
	void *symbol;

	dlerror();
	symbol = dlsym(RTLD_DEFAULT, name);
	error = dlerror();
	if (error || !symbol) {
		fprintf(stderr, "cannot resolve %s: %s\n", name,
			error ? error : "symbol is NULL");
		exit(1);
	}
	return symbol;
}

static void resolve_vkso(void)
{
	user_time.clock_gettime =
		(vdso_clock_fn)lookup_vkso_symbol("__vkso_clock_gettime");
	user_time.clock_getres =
		(vdso_clock_fn)lookup_vkso_symbol("__vkso_clock_getres");
	user_time.gettimeofday =
		(vdso_gettimeofday_fn)lookup_vkso_symbol(
			"__vkso_gettimeofday");
	user_time.time =
		(vdso_time_fn)lookup_vkso_symbol("__vkso_time");
	user_time.getcpu =
		(vdso_getcpu_fn)lookup_vkso_symbol("__vkso_getcpu");
}

static enum backend detect_backend(void)
{
	unsigned long vdso = getauxval(AT_SYSINFO_EHDR);
	unsigned long mm_data;

	errno = 0;
	mm_data = getauxval(AT_VKSO_MM_DATA);
	if (vdso && !mm_data)
		return BACKEND_RAW;
	if (!vdso && mm_data && !errno)
		return BACKEND_VKSO;
	fail_message("cannot identify raw vDSO or VKSO auxv contract");
	return BACKEND_RAW;
}

static const char *backend_name(enum backend backend)
{
	return backend == BACKEND_RAW ? "raw" : "vkso";
}

static void initialize_backend(enum backend backend)
{
	if (detect_backend() != backend)
		fail_message("requested backend does not match the booted kernel");
	if (backend == BACKEND_RAW) {
		resolve_raw_vdso();
		return;
	}
	if (vkso_user_wrapper_init())
		die("vkso_user_wrapper_init");
	resolve_vkso();
	vkso_mm_data = (const void *)getauxval(AT_VKSO_MM_DATA);
}

static int operation_is_clock_gettime(enum operation operation)
{
	return operation <= OP_CGT_REALTIME_ALARM;
}

static int operation_is_clock_getres(enum operation operation)
{
	return operation >= OP_CGR_REALTIME &&
	       operation <= OP_CGR_PROCESS_CPU;
}

static uint64_t user_clock_gettime_loop(clockid_t clock_id,
					uint64_t iterations)
{
	struct timespec value = { 0 };
	uint64_t index, checksum = 0;

	for (index = 0; index < iterations; ++index) {
		if (user_time.clock_gettime(clock_id, &value) < 0)
			fail_message("benchmark operation returned an error");
		checksum += (uint64_t)value.tv_sec ^ (uint64_t)value.tv_nsec;
	}
	return checksum;
}

static uint64_t syscall_clock_gettime_loop(clockid_t clock_id,
					   uint64_t iterations)
{
	struct timespec value = { 0 };
	uint64_t index, checksum = 0;

	for (index = 0; index < iterations; ++index) {
		long result = raw_syscall2(SYS_clock_gettime, clock_id,
					   (long)&value);

		if (result < 0)
			fail_message("benchmark operation returned an error");
		checksum += (uint64_t)value.tv_sec ^ (uint64_t)value.tv_nsec;
	}
	return checksum;
}

static uint64_t clock_getres_loop(clockid_t clock_id, enum path path,
				  uint64_t iterations)
{
	struct timespec value = { 0 };
	uint64_t index, checksum = 0;

	if (path == PATH_SYSCALL) {
		for (index = 0; index < iterations; ++index) {
			long result = raw_syscall2(SYS_clock_getres, clock_id,
						   (long)&value);

			if (result < 0)
				fail_message("benchmark operation returned an error");
			checksum += (uint64_t)value.tv_sec ^
				    (uint64_t)value.tv_nsec;
		}
	} else {
		for (index = 0; index < iterations; ++index) {
			if (user_time.clock_getres(clock_id, &value) < 0)
				fail_message("benchmark operation returned an error");
			checksum += (uint64_t)value.tv_sec ^
				    (uint64_t)value.tv_nsec;
		}
	}
	return checksum;
}

static uint64_t gettimeofday_loop(enum operation operation, enum path path,
				  uint64_t iterations)
{
	struct timeval value = { 0 };
	struct timezone timezone = { 0 };
	struct timeval *value_pointer =
		operation == OP_GTOD_TZ || operation == OP_GTOD_NULL ?
		NULL : &value;
	struct timezone *timezone_pointer =
		operation == OP_GTOD_TV || operation == OP_GTOD_NULL ?
		NULL : &timezone;
	uint64_t index, checksum = 0;

	if (path == PATH_SYSCALL) {
		for (index = 0; index < iterations; ++index) {
			long result = raw_syscall2(SYS_gettimeofday,
						   (long)value_pointer,
						   (long)timezone_pointer);

			if (result < 0)
				fail_message("benchmark operation returned an error");
			checksum += (uint64_t)value.tv_sec ^
				    (uint64_t)value.tv_usec ^
				    (uint32_t)timezone.tz_minuteswest;
		}
	} else {
		for (index = 0; index < iterations; ++index) {
			if (user_time.gettimeofday(value_pointer,
						    timezone_pointer) < 0)
				fail_message("benchmark operation returned an error");
			checksum += (uint64_t)value.tv_sec ^
				    (uint64_t)value.tv_usec ^
				    (uint32_t)timezone.tz_minuteswest;
		}
	}
	return checksum;
}

static uint64_t time_loop(enum operation operation, enum path path,
			  uint64_t iterations)
{
	time_t stored = 0;
	time_t *pointer = operation == OP_TIME_POINTER ? &stored : NULL;
	uint64_t index, checksum = 0;

	if (path == PATH_SYSCALL) {
		for (index = 0; index < iterations; ++index) {
			long result = raw_syscall1(SYS_time, (long)pointer);

			if (result < 0)
				fail_message("benchmark operation returned an error");
			checksum += (uint64_t)result ^ (uint64_t)stored;
		}
	} else {
		for (index = 0; index < iterations; ++index) {
			time_t result = user_time.time(pointer);

			if (result < 0)
				fail_message("benchmark operation returned an error");
			checksum += (uint64_t)result ^ (uint64_t)stored;
		}
	}
	return checksum;
}

static uint64_t getcpu_loop(enum operation operation, enum path path,
			    uint64_t iterations)
{
	unsigned int cpu = 0, node = 0;
	unsigned int *cpu_pointer = operation == OP_GETCPU_BOTH ? &cpu : NULL;
	unsigned int *node_pointer =
		operation == OP_GETCPU_BOTH ? &node : NULL;
	uint64_t index, checksum = 0;

	if (path == PATH_SYSCALL) {
		for (index = 0; index < iterations; ++index) {
			long result = raw_syscall3(SYS_getcpu, (long)cpu_pointer,
						   (long)node_pointer, 0);

			if (result < 0)
				fail_message("benchmark operation returned an error");
			checksum += cpu ^ node;
		}
	} else {
		for (index = 0; index < iterations; ++index) {
			if (user_time.getcpu(cpu_pointer, node_pointer, NULL) < 0)
				fail_message("benchmark operation returned an error");
			checksum += cpu ^ node;
		}
	}
	return checksum;
}

static uint64_t direct_operation_loop(enum operation operation,
				      enum path path, uint64_t iterations)
{
	const struct operation_info *info = &operations[operation];

	if (operation_is_clock_gettime(operation)) {
		if (path == PATH_SYSCALL)
			return syscall_clock_gettime_loop(info->clock_id,
						   iterations);
		return user_clock_gettime_loop(info->clock_id, iterations);
	}
	if (operation_is_clock_getres(operation))
		return clock_getres_loop(info->clock_id, path, iterations);
	if (operation >= OP_GTOD_TV && operation <= OP_GTOD_NULL)
		return gettimeofday_loop(operation, path, iterations);
	if (operation == OP_TIME_NULL || operation == OP_TIME_POINTER)
		return time_loop(operation, path, iterations);
	return getcpu_loop(operation, path, iterations);
}

static int perf_event_open(struct perf_event_attr *attribute, int group_fd)
{
	return syscall(SYS_perf_event_open, attribute, 0, -1, group_fd, 0);
}

static uint64_t cache_event_config(uint64_t cache, uint64_t operation,
				   uint64_t result)
{
	return cache | operation << 8 | result << 16;
}

static void open_pmu_group(struct pmu_group *group, const uint32_t *types,
			   const uint64_t *configs, const char *const *names)
{
	unsigned int index;

	for (index = 0; index < PMU_EVENT_COUNT; ++index) {
		struct perf_event_attr attribute = {
			.type = types[index],
			.size = sizeof(attribute),
			.config = configs[index],
			.disabled = index == 0,
			.pinned = index == 0,
			.read_format = PERF_FORMAT_GROUP |
				       PERF_FORMAT_TOTAL_TIME_ENABLED |
				       PERF_FORMAT_TOTAL_TIME_RUNNING,
		};
		int descriptor = perf_event_open(&attribute,
						 index ? group->leader : -1);

		if (descriptor < 0)
			die(names[index]);
		group->descriptors[index] = descriptor;
		if (!index)
			group->leader = descriptor;
	}
}

static void initialize_pmu(void)
{
	static const uint32_t hardware_types[PMU_EVENT_COUNT] = {
		PERF_TYPE_HARDWARE, PERF_TYPE_HARDWARE,
		PERF_TYPE_HARDWARE, PERF_TYPE_HARDWARE,
	};
	static const uint64_t core_configs[PMU_EVENT_COUNT] = {
		PERF_COUNT_HW_CPU_CYCLES,
		PERF_COUNT_HW_INSTRUCTIONS,
		PERF_COUNT_HW_BRANCH_INSTRUCTIONS,
		PERF_COUNT_HW_BRANCH_MISSES,
	};
	static const char *const core_names[PMU_EVENT_COUNT] = {
		"open PMU cycles", "open PMU instructions",
		"open PMU branches", "open PMU branch misses",
	};
	static const uint32_t cache_types[PMU_EVENT_COUNT] = {
		PERF_TYPE_HARDWARE, PERF_TYPE_HARDWARE,
		PERF_TYPE_HW_CACHE, PERF_TYPE_HW_CACHE,
	};
	uint64_t cache_configs[PMU_EVENT_COUNT] = {
		PERF_COUNT_HW_CACHE_REFERENCES,
		PERF_COUNT_HW_CACHE_MISSES,
		cache_event_config(PERF_COUNT_HW_CACHE_L1D,
				   PERF_COUNT_HW_CACHE_OP_READ,
				   PERF_COUNT_HW_CACHE_RESULT_MISS),
		cache_event_config(PERF_COUNT_HW_CACHE_LL,
				   PERF_COUNT_HW_CACHE_OP_READ,
				   PERF_COUNT_HW_CACHE_RESULT_MISS),
	};
	static const char *const cache_names[PMU_EVENT_COUNT] = {
		"open PMU cache references", "open PMU cache misses",
		"open PMU L1D load misses", "open PMU LLC load misses",
	};

	open_pmu_group(&core_group, hardware_types, core_configs, core_names);
	open_pmu_group(&cache_group, cache_types, cache_configs, cache_names);
}

static void close_pmu_group(struct pmu_group *group)
{
	unsigned int index;

	if (group->leader < 0)
		return;
	for (index = 0; index < PMU_EVENT_COUNT; ++index)
		close(group->descriptors[index]);
	group->leader = -1;
}

static void start_pmu_group(const struct pmu_group *group)
{
	if (ioctl(group->leader, PERF_EVENT_IOC_RESET, PERF_IOC_FLAG_GROUP) ||
	    ioctl(group->leader, PERF_EVENT_IOC_ENABLE, PERF_IOC_FLAG_GROUP))
		die("start PMU group");
}

static void stop_pmu_group(const struct pmu_group *group,
			   struct pmu_reading *reading)
{
	if (ioctl(group->leader, PERF_EVENT_IOC_DISABLE, PERF_IOC_FLAG_GROUP))
		die("stop PMU group");
	if (read(group->leader, reading, sizeof(*reading)) !=
	    (ssize_t)sizeof(*reading))
		die("read PMU group");
	if (reading->nr != PMU_EVENT_COUNT || !reading->time_running)
		fail_message("PMU group was not scheduled");
}

static double pmu_per_call(const struct pmu_reading *reading,
			   unsigned int event, unsigned int iterations)
{
	long double scaled = reading->values[event];

	scaled *= reading->time_enabled;
	scaled /= reading->time_running;
	scaled /= iterations;
	return scaled;
}

static void direct_call_loop(enum operation operation, enum path path,
			     unsigned int iterations)
{
	sink = direct_operation_loop(operation, path, iterations);
}

static struct measurement measure(enum operation operation, enum path path,
				  unsigned int iterations)
{
	struct measurement measurement = { 0 };
	unsigned int start_aux, end_aux, attempt;
	uint64_t start, end;

	for (attempt = 0; attempt < 10; ++attempt) {
		struct pmu_reading reading;

		if (pmu_enabled)
			start_pmu_group(&core_group);
		start = tsc_begin(&start_aux);
		direct_call_loop(operation, path, iterations);
		end = tsc_end(&end_aux);
		if (pmu_enabled) {
			stop_pmu_group(&core_group, &reading);
			measurement.pmu_cycles_per_call =
				pmu_per_call(&reading, 0, iterations);
			measurement.instructions_per_call =
				pmu_per_call(&reading, 1, iterations);
			measurement.branches_per_call =
				pmu_per_call(&reading, 2, iterations);
			measurement.branch_misses_per_call =
				pmu_per_call(&reading, 3, iterations);
		}
		if (start_aux != end_aux)
			continue;
		measurement.tsc_cycles_per_call =
			(double)(end - start) / iterations;
		break;
	}
	if (attempt == 10)
		fail_message("CPU migration during every timing attempt");

	if (pmu_enabled) {
		struct pmu_reading reading;

		start_pmu_group(&cache_group);
		direct_call_loop(operation, path, iterations);
		stop_pmu_group(&cache_group, &reading);
		measurement.cache_references_per_call =
			pmu_per_call(&reading, 0, iterations);
		measurement.cache_misses_per_call =
			pmu_per_call(&reading, 1, iterations);
		measurement.l1d_load_misses_per_call =
			pmu_per_call(&reading, 2, iterations);
		measurement.llc_load_misses_per_call =
			pmu_per_call(&reading, 3, iterations);
	}
	return measurement;
}

static unsigned int available_paths(enum backend backend, enum path *paths)
{
	if (backend == BACKEND_RAW) {
		paths[0] = PATH_SYSCALL;
		paths[1] = PATH_RAW_VDSO;
		return 2;
	}
	paths[0] = PATH_SYSCALL;
	paths[1] = PATH_VKSO_WRAPPER;
	return 2;
}

static void run_perf(enum backend backend, unsigned int iterations,
		     unsigned int repeats, unsigned int warmup)
{
	unsigned int operation, repeat;

	if (pmu_enabled)
		initialize_pmu();
	for (operation = 0; operation < OP_COUNT; ++operation) {
		enum path paths[2];
		unsigned int count = available_paths(backend, paths);
		unsigned int index;

		for (index = 0; index < count; ++index)
			direct_call_loop(operation, paths[index], warmup);
	}

	puts("backend,api,repeat,path,tsc_cycles_per_call,pmu_enabled,"
	     "pmu_cycles_per_call,instructions_per_call,branches_per_call,"
	     "branch_misses_per_call,cache_references_per_call,"
	     "cache_misses_per_call,l1d_load_misses_per_call,"
	     "llc_load_misses_per_call");
	for (operation = 0; operation < OP_COUNT; ++operation) {
		enum path paths[2];
		unsigned int count = available_paths(backend, paths);

		for (repeat = 0; repeat < repeats; ++repeat) {
			unsigned int step;

			for (step = 0; step < count; ++step) {
				enum path path = paths[(step + repeat) % count];
				struct measurement value;

				/*
				 * Re-prime the exact path after alternating with its
				 * peer.  In particular, do not let the preceding syscall
				 * sample define the indirect-branch state of the user
				 * sample.
				 */
				direct_call_loop(operation, path, warmup);
				value = measure(operation, path, iterations);

				printf("%s,%s,%u,%s,%.6f,%d,%.6f,%.6f,"
				       "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
				       backend_name(backend),
				       operations[operation].name, repeat,
				       path_names[path],
				       value.tsc_cycles_per_call, pmu_enabled,
				       value.pmu_cycles_per_call,
				       value.instructions_per_call,
				       value.branches_per_call,
				       value.branch_misses_per_call,
				       value.cache_references_per_call,
				       value.cache_misses_per_call,
				       value.l1d_load_misses_per_call,
				       value.llc_load_misses_per_call);
			}
		}
	}
	close_pmu_group(&cache_group);
	close_pmu_group(&core_group);
}

static uintptr_t find_mapping(const char *name)
{
	FILE *stream = fopen("/proc/self/maps", "r");
	char line[512];
	unsigned long start;

	if (!stream)
		die("open /proc/self/maps");
	while (fgets(line, sizeof(line), stream)) {
		if (!strstr(line, name))
			continue;
		if (sscanf(line, "%lx-", &start) != 1)
			fail_message("cannot parse mapping");
		fclose(stream);
		return start;
	}
	fclose(stream);
	fail_message("required mapping is unavailable");
	return 0;
}

struct seq_result {
	uint64_t completed;
	uint64_t retries;
	uint64_t odd;
	uint64_t changed;
	double cycles_per_read;
};

static struct seq_result observe_raw_seq(const struct raw_vdso_data *data,
					 uint64_t iterations)
{
	struct seq_result result = { 0 };
	unsigned int start_aux, end_aux;
	uint64_t start = tsc_begin(&start_aux);
	uint64_t checksum = 0;

	while (result.completed < iterations) {
		uint32_t seq = __atomic_load_n(&data->seq, __ATOMIC_ACQUIRE);

		if (seq & 1) {
			result.odd++;
			result.retries++;
			continue;
		}
		checksum ^= data->cycle_last;
		checksum ^= data->mult;
		checksum ^= data->shift;
		checksum ^= data->basetime[CLOCK_MONOTONIC].sec;
		checksum ^= data->basetime[CLOCK_MONOTONIC].nsec;
		checksum ^= ordered_tsc();
		__atomic_thread_fence(__ATOMIC_ACQUIRE);
		if (seq != __atomic_load_n(&data->seq, __ATOMIC_RELAXED)) {
			result.changed++;
			result.retries++;
			continue;
		}
		result.completed++;
	}
	result.cycles_per_read =
		(double)(tsc_end(&end_aux) - start) / result.completed;
	if (start_aux != end_aux)
		fail_message("CPU migrated during raw seq observation");
	sink = checksum;
	return result;
}

static struct seq_result
observe_vkso_seq(const struct vkso_shared_data_bench *data, int raw,
		 uint64_t iterations)
{
	struct seq_result result = { 0 };
	unsigned int start_aux, end_aux;
	uint64_t start = tsc_begin(&start_aux);
	uint64_t checksum = 0;

	while (result.completed < iterations) {
		const struct vkso_cycle_data_bench *cycles =
			&data->state.cycles;
		const struct vkso_hres_base_bench *base =
			raw ? &data->state.monotonic_raw_base :
			      &data->state.monotonic_base;
		uint32_t mult = raw ? cycles->raw_mult : cycles->mono_mult;
		uint32_t seq = __atomic_load_n(&data->seq, __ATOMIC_ACQUIRE);

		if (seq & 1) {
			result.odd++;
			result.retries++;
			continue;
		}
		checksum ^= cycles->cycle_last;
		checksum ^= mult;
		checksum ^= cycles->shift;
		checksum ^= base->sec;
		checksum ^= base->shifted_nsec;
		checksum ^= ordered_tsc();
		__atomic_thread_fence(__ATOMIC_ACQUIRE);
		if (seq != __atomic_load_n(&data->seq, __ATOMIC_RELAXED)) {
			result.changed++;
			result.retries++;
			continue;
		}
		result.completed++;
	}
	result.cycles_per_read =
		(double)(tsc_end(&end_aux) - start) / result.completed;
	if (start_aux != end_aux)
		fail_message("CPU migrated during VKSO seq observation");
	sink = checksum;
	return result;
}

static void print_seq_result(enum backend backend, const char *reader,
			     const struct seq_result *result)
{
	printf("%s,%s,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64
	       ",%.9f,%.6f\n",
	       backend_name(backend), reader, result->completed,
	       result->retries, result->odd, result->changed,
	       1000000.0 * result->retries / result->completed,
	       result->cycles_per_read);
}

static void run_seq(enum backend backend, uint64_t iterations)
{
	puts("backend,reader,completed,retries,odd_seq,changed_seq,"
	     "retries_per_million,cycles_per_read");
	if (backend == BACKEND_RAW) {
		uintptr_t mapping = find_mapping("[vvar]");
		const struct raw_vdso_data *data =
			(const void *)(mapping + RAW_VVAR_DATA_OFFSET);
		struct seq_result hres = observe_raw_seq(data, iterations);
		struct seq_result raw =
			observe_raw_seq(data + RAW_CS_RAW, iterations);

		print_seq_result(backend, "hres_protocol", &hres);
		print_seq_result(backend, "raw_protocol", &raw);
	} else {
		const struct vkso_shared_data_bench *data =
			__vkso_shared_data();
		struct seq_result hres, raw;

		if (data->abi_version != VKSO_TIME_ABI_VERSION)
			fail_message("VKSO shared-data address/ABI mismatch");
		hres = observe_vkso_seq(data, 0, iterations);
		raw = observe_vkso_seq(data, 1, iterations);
		print_seq_result(backend, "hres_protocol", &hres);
		print_seq_result(backend, "raw_protocol", &raw);
	}
}

static inline void flush_line(const void *address)
{
	__asm__ volatile("clflush (%0)" :: "r"(address) : "memory");
}

static double layout_batch(volatile unsigned char *data, int new_layout,
			   unsigned int iterations)
{
	unsigned int index;
	uint64_t cycles = 0, checksum = 0;
	size_t cycle_offset = new_layout ? 136 : 104;
	size_t mult_offset = new_layout ? 144 : 112;
	size_t shift_offset = new_layout ? 148 : 116;
	size_t sec_offset = new_layout ? 152 : 120;
	size_t nsec_offset = new_layout ? 160 : 128;

	for (index = 0; index < iterations; ++index) {
		unsigned int start_aux, end_aux;
		uint64_t start, end;

		flush_line((const void *)(data + 0));
		flush_line((const void *)(data + 64));
		flush_line((const void *)(data + 128));
		__asm__ volatile("mfence" ::: "memory");
		start = tsc_begin(&start_aux);
		checksum ^= *(volatile uint32_t *)(data + 0);
		checksum ^= *(volatile uint64_t *)(data + cycle_offset);
		checksum ^= *(volatile uint32_t *)(data + mult_offset);
		checksum ^= *(volatile uint32_t *)(data + shift_offset);
		checksum ^= *(volatile uint64_t *)(data + sec_offset);
		checksum ^= *(volatile uint64_t *)(data + nsec_offset);
		end = tsc_end(&end_aux);
		if (start_aux != end_aux)
			fail_message("CPU migrated during layout measurement");
		cycles += end - start;
	}
	sink = checksum;
	return (double)cycles / iterations;
}

static void run_layout(unsigned int iterations, unsigned int repeats)
{
	volatile unsigned char *data;
	unsigned int repeat;

	if (posix_memalign((void **)&data, 64, 192))
		die("posix_memalign");
	memset((void *)data, 0x5a, 192);
	puts("layout,repeat,iterations,cold_cycles_per_read,cache_lines_read");
	for (repeat = 0; repeat < repeats; ++repeat) {
		int first_new = repeat & 1;
		int step;

		for (step = 0; step < 2; ++step) {
			int new_layout = first_new ^ step;
			double cycles =
				layout_batch(data, new_layout, iterations);

			printf("%s,%u,%u,%.6f,%d\n",
			       new_layout ? "new_aligned_raw" :
					    "old_straddled_raw",
			       repeat, iterations, cycles,
			       new_layout ? 2 : 3);
		}
	}
	free((void *)data);
}

static int public_clock_gettime(clockid_t clock_id, struct timespec *value)
{
	return user_time.clock_gettime(clock_id, value);
}

static uint64_t timespec_to_ns(const struct timespec *value)
{
	return (uint64_t)value->tv_sec * UINT64_C(1000000000) +
	       (uint64_t)value->tv_nsec;
}

static void run_load(enum backend backend, enum operation operation,
		     unsigned int iterations, unsigned int seconds,
		     unsigned int warmup)
{
	const struct operation_info *info = &operations[operation];
	enum path path = backend == BACKEND_RAW ?
		PATH_RAW_VDSO : PATH_VKSO_WRAPPER;
	struct timespec previous = { 0 }, current, wall_start, wall_now;
	uint64_t measured_batches = 0, measured_calls = 0;
	uint64_t conditioning_calls = 0, checksum = 0;
	uint64_t measured_cycles = 0, wall_ns;
	unsigned int index;

	/* Validate ordering separately so it is not charged to the load loop. */
	for (index = 0; index < warmup; index++) {
		if (public_clock_gettime(info->clock_id, &current))
			fail_message("concurrent reader returned an error");
		if (index && (current.tv_sec < previous.tv_sec ||
		    (current.tv_sec == previous.tv_sec &&
		     current.tv_nsec < previous.tv_nsec)))
			fail_message("concurrent reader observed time reversal");
		previous = current;
	}
	if (raw_syscall2(SYS_clock_gettime, CLOCK_MONOTONIC,
			 (long)&wall_start))
		fail_message("cannot read load-test start time");
	do {
		unsigned int start_aux, end_aux;
		uint64_t start, end;

		/* Remove predictor state left by the duration-control syscall. */
		checksum += direct_operation_loop(operation, path, warmup);
		conditioning_calls += warmup;
		start = tsc_begin(&start_aux);
		checksum += direct_operation_loop(operation, path, iterations);
		end = tsc_end(&end_aux);
		if (start_aux != end_aux)
			fail_message("CPU migrated during concurrent reader load");
		measured_cycles += end - start;
		measured_batches++;
		measured_calls += iterations;

		/* Keep duration control outside the reader measurement window. */
		if (raw_syscall2(SYS_clock_gettime, CLOCK_MONOTONIC,
				 (long)&wall_now))
			fail_message("cannot read load-test current time");
		wall_ns = timespec_to_ns(&wall_now) - timespec_to_ns(&wall_start);
	} while (wall_ns < (uint64_t)seconds * UINT64_C(1000000000));
	sink = checksum;
	puts("backend,api,seconds,batch_iterations,warmup_per_batch,"
	     "measured_batches,measured_calls,conditioning_calls,total_calls,"
	     "wall_ns,tsc_cycles_per_call,total_calls_per_second,"
	     "cpu_migration,time_reversal,measurement_window");
	printf("%s,%s,%u,%u,%u,%" PRIu64 ",%" PRIu64 ",%" PRIu64
	       ",%" PRIu64 ",%" PRIu64 ",%.9f,%.3f,0,0,%s\n",
	       backend_name(backend), info->name, seconds, iterations, warmup,
	       measured_batches, measured_calls, conditioning_calls,
	       measured_calls + conditioning_calls, wall_ns,
	       (double)measured_cycles / measured_calls,
	       (double)(measured_calls + conditioning_calls) * 1000000000.0 /
	       wall_ns, LOAD_MEASUREMENT_WINDOW);
}

static void usage(const char *program)
{
	fprintf(stderr,
		"usage: %s --probe | --backend {raw|vkso} "
		"[--mode perf|seq|layout|load] [--cpu N] [--iterations N] "
		"[--repeats N] [--warmup N] [--pmu 0|1] "
		"[--seq-iterations N] [--layout-iterations N] "
		"[--operation monotonic|monotonic_raw|monotonic_coarse] "
		"[--seconds N]\n",
		program);
}

int main(int argc, char **argv)
{
	enum backend backend = BACKEND_RAW;
	enum mode mode = MODE_PERF;
	unsigned int cpu = 2;
	unsigned int iterations = DEFAULT_ITERATIONS;
	unsigned int repeats = DEFAULT_REPEATS;
	unsigned int warmup = DEFAULT_WARMUP;
	uint64_t seq_iterations = DEFAULT_SEQ_ITERATIONS;
	unsigned int layout_iterations = DEFAULT_LAYOUT_ITERATIONS;
	unsigned int load_seconds = DEFAULT_LOAD_SECONDS;
	enum operation load_operation = OP_CGT_MONOTONIC;
	int backend_set = 0;
	int index;

	if (argc == 2 && !strcmp(argv[1], "--probe")) {
		enum backend detected = detect_backend();

		printf("backend=%s\n", backend_name(detected));
		printf("reader_measurement_window=%s\n",
		       READER_MEASUREMENT_WINDOW);
		printf("load_measurement_window=%s\n",
		       LOAD_MEASUREMENT_WINDOW);
		printf("at_sysinfo_ehdr=%#lx\n", getauxval(AT_SYSINFO_EHDR));
		printf("at_vkso_mm_data=%#lx\n", getauxval(AT_VKSO_MM_DATA));
		return 0;
	}

	for (index = 1; index < argc; index += 2) {
		if (index + 1 == argc) {
			usage(argv[0]);
			return 2;
		}
		if (!strcmp(argv[index], "--backend")) {
			if (!strcmp(argv[index + 1], "raw"))
				backend = BACKEND_RAW;
			else if (!strcmp(argv[index + 1], "vkso"))
				backend = BACKEND_VKSO;
			else
				fail_message("backend must be raw or vkso");
			backend_set = 1;
		} else if (!strcmp(argv[index], "--mode")) {
			if (!strcmp(argv[index + 1], "perf"))
				mode = MODE_PERF;
			else if (!strcmp(argv[index + 1], "seq"))
				mode = MODE_SEQ;
			else if (!strcmp(argv[index + 1], "layout"))
				mode = MODE_LAYOUT;
			else if (!strcmp(argv[index + 1], "load"))
				mode = MODE_LOAD;
			else
				fail_message("mode must be perf, seq, layout or load");
		} else if (!strcmp(argv[index], "--cpu")) {
			cpu = parse_number(argv[index + 1], "CPU", 1);
		} else if (!strcmp(argv[index], "--iterations")) {
			iterations =
				parse_number(argv[index + 1], "iterations", 0);
		} else if (!strcmp(argv[index], "--repeats")) {
			repeats =
				parse_number(argv[index + 1], "repeats", 0);
		} else if (!strcmp(argv[index], "--warmup")) {
			warmup =
				parse_number(argv[index + 1], "warmup", 1);
		} else if (!strcmp(argv[index], "--pmu")) {
			pmu_enabled =
				parse_number(argv[index + 1], "PMU", 1);
		} else if (!strcmp(argv[index], "--seq-iterations")) {
			seq_iterations = parse_number(argv[index + 1],
						      "seq iterations", 0);
		} else if (!strcmp(argv[index], "--layout-iterations")) {
			layout_iterations =
				parse_number(argv[index + 1],
					     "layout iterations", 0);
		} else if (!strcmp(argv[index], "--seconds")) {
			load_seconds =
				parse_number(argv[index + 1], "seconds", 0);
		} else if (!strcmp(argv[index], "--operation")) {
			if (!strcmp(argv[index + 1], "monotonic")) {
				load_operation = OP_CGT_MONOTONIC;
			} else if (!strcmp(argv[index + 1], "monotonic_raw")) {
				load_operation = OP_CGT_MONOTONIC_RAW;
			} else if (!strcmp(argv[index + 1], "monotonic_coarse")) {
				load_operation = OP_CGT_MONOTONIC_COARSE;
			} else {
				fail_message("unsupported load operation");
			}
		} else {
			usage(argv[0]);
			return 2;
		}
	}
	if (!backend_set) {
		usage(argv[0]);
		return 2;
	}
	if (pmu_enabled > 1)
		fail_message("PMU must be 0 or 1");

	pin_cpu(cpu);
	initialize_backend(backend);
	if (mode == MODE_PERF)
		run_perf(backend, iterations, repeats, warmup);
	else if (mode == MODE_SEQ)
		run_seq(backend, seq_iterations);
	else if (mode == MODE_LAYOUT)
		run_layout(layout_iterations, repeats);
	else
		run_load(backend, load_operation, iterations, load_seconds,
			 warmup);
	return sink == UINT64_MAX;
}
