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

#include "../m27/vkso_abi.h"
#include "../m27/vkso_user_wrapper.h"

#ifndef CLOCK_REALTIME_ALARM
#define CLOCK_REALTIME_ALARM 8
#endif
#ifndef VKSO_SHARED_ST_VALUE
#error "VKSO_SHARED_ST_VALUE must match libkernel.so"
#endif

#define DEFAULT_ITERATIONS 500000U
#define DEFAULT_REPEATS 31U
#define DEFAULT_WARMUP 10000U
#define DEFAULT_SEQ_ITERATIONS 100000000U
#define DEFAULT_LAYOUT_ITERATIONS 200000U
#define PMU_EVENT_COUNT 4U
#define RAW_VVAR_DATA_OFFSET 128U
#define RAW_VDSO_BASES 12U
#define RAW_CS_RAW 1U

enum backend {
	BACKEND_RAW,
	BACKEND_VKSO,
};

enum mode {
	MODE_PERF,
	MODE_SEQ,
	MODE_LAYOUT,
};

enum path {
	PATH_SYSCALL,
	PATH_RAW_VDSO,
	PATH_VKSO_CORE,
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
	int core_supported;
};

static const struct operation_info operations[OP_COUNT] = {
	[OP_CGT_REALTIME] = {
		"clock_gettime_realtime", CLOCK_REALTIME, 1
	},
	[OP_CGT_MONOTONIC] = {
		"clock_gettime_monotonic", CLOCK_MONOTONIC, 1
	},
	[OP_CGT_MONOTONIC_RAW] = {
		"clock_gettime_monotonic_raw", CLOCK_MONOTONIC_RAW, 1
	},
	[OP_CGT_BOOTTIME] = {
		"clock_gettime_boottime", CLOCK_BOOTTIME, 1
	},
	[OP_CGT_TAI] = {
		"clock_gettime_tai", CLOCK_TAI, 1
	},
	[OP_CGT_REALTIME_COARSE] = {
		"clock_gettime_realtime_coarse", CLOCK_REALTIME_COARSE, 1
	},
	[OP_CGT_MONOTONIC_COARSE] = {
		"clock_gettime_monotonic_coarse",
		CLOCK_MONOTONIC_COARSE, 1
	},
	[OP_CGT_PROCESS_CPU] = {
		"clock_gettime_process_cpu_fallback",
		CLOCK_PROCESS_CPUTIME_ID, 0
	},
	[OP_CGT_REALTIME_ALARM] = {
		"clock_gettime_realtime_alarm_fallback",
		CLOCK_REALTIME_ALARM, 0
	},
	[OP_CGR_REALTIME] = {
		"clock_getres_realtime", CLOCK_REALTIME, 1
	},
	[OP_CGR_REALTIME_COARSE] = {
		"clock_getres_realtime_coarse", CLOCK_REALTIME_COARSE, 1
	},
	[OP_CGR_PROCESS_CPU] = {
		"clock_getres_process_cpu_fallback",
		CLOCK_PROCESS_CPUTIME_ID, 0
	},
	[OP_GTOD_TV] = { "gettimeofday_tv", 0, 1 },
	[OP_GTOD_TZ] = { "gettimeofday_timezone", 0, 1 },
	[OP_GTOD_BOTH] = { "gettimeofday_both", 0, 1 },
	[OP_GTOD_NULL] = { "gettimeofday_null", 0, 1 },
	[OP_TIME_NULL] = { "time_null", 0, 1 },
	[OP_TIME_POINTER] = { "time_pointer", 0, 1 },
	[OP_GETCPU_BOTH] = { "getcpu_both", 0, 1 },
	[OP_GETCPU_NULL] = { "getcpu_null", 0, 1 },
};

static const char *const path_names[] = {
	[PATH_SYSCALL] = "syscall",
	[PATH_RAW_VDSO] = "raw_vdso",
	[PATH_VKSO_CORE] = "vkso_core",
	[PATH_VKSO_WRAPPER] = "vkso_wrapper",
};

typedef int (*vdso_clock_fn)(clockid_t, struct timespec *);
typedef int (*vdso_gettimeofday_fn)(struct timeval *, struct timezone *);
typedef time_t (*vdso_time_fn)(time_t *);
typedef int (*vdso_getcpu_fn)(unsigned int *, unsigned int *, void *);

static vdso_clock_fn vdso_clock_gettime;
static vdso_clock_fn vdso_clock_getres;
static vdso_gettimeofday_fn vdso_gettimeofday;
static vdso_time_fn vdso_time;
static vdso_getcpu_fn vdso_getcpu;
static const struct vkso_mm_data *vkso_mm_data;
static const struct vkso_cycle_context cycle_context;
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
	uint32_t reserved;
	volatile uint64_t cycle_last;
	volatile uint32_t mult;
	volatile uint32_t shift;
};

struct vkso_hres_base_bench {
	volatile int64_t sec;
	volatile uint64_t shifted_nsec;
};

struct vkso_hres_data_bench {
	struct vkso_cycle_data_bench cycles;
	struct vkso_hres_base_bench realtime_base;
	struct vkso_hres_base_bench monotonic_base;
	struct vkso_hres_base_bench boottime_base;
	struct vkso_hres_base_bench tai_base;
};

struct vkso_raw_data_bench {
	struct vkso_cycle_data_bench cycles;
	struct vkso_hres_base_bench monotonic_raw_base;
};

struct vkso_shared_data_bench {
	volatile uint32_t seq;
	uint32_t abi_version;
	struct vkso_hres_data_bench hres;
	struct vkso_time_value realtime_coarse;
	struct vkso_time_value monotonic_coarse;
	struct vkso_raw_data_bench raw;
	uint32_t hrtimer_resolution;
	uint32_t reserved;
	struct vkso_timezone timezone;
};

_Static_assert(sizeof(struct raw_vdso_data) == 240,
	       "raw x86-64 vdso_data layout changed");
_Static_assert(__builtin_offsetof(struct vkso_shared_data_bench, raw) == 128,
	       "VKSO raw layout changed");

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
	vdso_clock_gettime =
		(vdso_clock_fn)vdso_lookup("__vdso_clock_gettime");
	vdso_clock_getres =
		(vdso_clock_fn)vdso_lookup("__vdso_clock_getres");
	vdso_gettimeofday =
		(vdso_gettimeofday_fn)vdso_lookup("__vdso_gettimeofday");
	vdso_time = (vdso_time_fn)vdso_lookup("__vdso_time");
	vdso_getcpu = (vdso_getcpu_fn)vdso_lookup("__vdso_getcpu");
	if (!vdso_clock_gettime || !vdso_clock_getres ||
	    !vdso_gettimeofday || !vdso_time || !vdso_getcpu)
		fail_message("raw vDSO is missing a required native symbol");
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

static uint64_t result_checksum(enum operation operation, long result,
				const struct timespec *ts,
				const struct timeval *tv,
				const struct timezone *tz,
				time_t stored, unsigned int cpu,
				unsigned int node)
{
	if (result < 0)
		return (uint64_t)-result;
	if (operation_is_clock_gettime(operation) ||
	    operation_is_clock_getres(operation))
		return (uint64_t)ts->tv_sec ^ (uint64_t)ts->tv_nsec;
	if (operation >= OP_GTOD_TV && operation <= OP_GTOD_NULL)
		return (uint64_t)tv->tv_sec ^ (uint64_t)tv->tv_usec ^
		       (uint32_t)tz->tz_minuteswest;
	if (operation == OP_TIME_NULL || operation == OP_TIME_POINTER)
		return (uint64_t)result ^ (uint64_t)stored;
	return cpu ^ node;
}

static __attribute__((noinline))
uint64_t invoke(enum operation operation, enum path path)
{
	struct timespec ts = { 0 };
	struct timeval tv = { 0 };
	struct timezone tz = { 0 };
	time_t stored = 0;
	unsigned int cpu = 0, node = 0;
	const struct operation_info *info = &operations[operation];
	long result;

	if (operation_is_clock_gettime(operation)) {
		if (path == PATH_SYSCALL)
			result = raw_syscall2(SYS_clock_gettime, info->clock_id,
					      (long)&ts);
		else if (path == PATH_RAW_VDSO)
			result = vdso_clock_gettime(info->clock_id, &ts);
		else if (path == PATH_VKSO_CORE)
			result = vkso_clock_gettime_core(
				vkso_mm_data, info->clock_id,
				(struct vkso_time_value *)&ts, &cycle_context);
		else
			result = vkso_user_clock_gettime(info->clock_id, &ts);
	} else if (operation_is_clock_getres(operation)) {
		if (path == PATH_SYSCALL)
			result = raw_syscall2(SYS_clock_getres, info->clock_id,
					      (long)&ts);
		else if (path == PATH_RAW_VDSO)
			result = vdso_clock_getres(info->clock_id, &ts);
		else if (path == PATH_VKSO_CORE)
			result = __vkso_clock_getres(
				info->clock_id, (struct vkso_time_value *)&ts);
		else
			result = vkso_user_clock_getres(info->clock_id, &ts);
	} else if (operation >= OP_GTOD_TV && operation <= OP_GTOD_NULL) {
		struct timeval *tv_pointer =
			operation == OP_GTOD_TZ || operation == OP_GTOD_NULL ?
			NULL : &tv;
		struct timezone *tz_pointer =
			operation == OP_GTOD_TV || operation == OP_GTOD_NULL ?
			NULL : &tz;

		if (path == PATH_SYSCALL)
			result = raw_syscall2(SYS_gettimeofday,
					      (long)tv_pointer,
					      (long)tz_pointer);
		else if (path == PATH_RAW_VDSO)
			result = vdso_gettimeofday(tv_pointer, tz_pointer);
		else if (path == PATH_VKSO_CORE)
			result = vkso_gettimeofday_core(
				(struct vkso_timeval *)tv_pointer,
				(struct vkso_timezone *)tz_pointer,
				&cycle_context);
		else
			result = vkso_user_gettimeofday(tv_pointer, tz_pointer);
	} else if (operation == OP_TIME_NULL ||
		   operation == OP_TIME_POINTER) {
		time_t *pointer =
			operation == OP_TIME_POINTER ? &stored : NULL;

		if (path == PATH_SYSCALL)
			result = raw_syscall1(SYS_time, (long)pointer);
		else if (path == PATH_RAW_VDSO)
			result = vdso_time(pointer);
		else if (path == PATH_VKSO_CORE)
			result = __vkso_time((int64_t *)pointer);
		else
			result = vkso_user_time(pointer);
	} else {
		unsigned int *cpu_pointer =
			operation == OP_GETCPU_BOTH ? &cpu : NULL;
		unsigned int *node_pointer =
			operation == OP_GETCPU_BOTH ? &node : NULL;

		if (path == PATH_SYSCALL)
			result = raw_syscall3(SYS_getcpu, (long)cpu_pointer,
					      (long)node_pointer, 0);
		else if (path == PATH_RAW_VDSO)
			result = vdso_getcpu(cpu_pointer, node_pointer, NULL);
		else if (path == PATH_VKSO_CORE)
			result = __vkso_getcpu(cpu_pointer, node_pointer, NULL);
		else
			result = vkso_user_getcpu(cpu_pointer, node_pointer,
						 NULL);
	}
	if (result < 0)
		fail_message("benchmark operation returned an error");
	return result_checksum(operation, result, &ts, &tv, &tz, stored,
			       cpu, node);
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

static void invoke_loop(enum operation operation, enum path path,
			unsigned int iterations)
{
	unsigned int index;
	uint64_t checksum = 0;

	for (index = 0; index < iterations; ++index)
		checksum += invoke(operation, path);
	sink = checksum;
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
		invoke_loop(operation, path, iterations);
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
		invoke_loop(operation, path, iterations);
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

static unsigned int available_paths(enum backend backend,
				    enum operation operation,
				    enum path *paths)
{
	if (backend == BACKEND_RAW) {
		paths[0] = PATH_SYSCALL;
		paths[1] = PATH_RAW_VDSO;
		return 2;
	}
	paths[0] = PATH_SYSCALL;
	if (operations[operation].core_supported) {
		paths[1] = PATH_VKSO_CORE;
		paths[2] = PATH_VKSO_WRAPPER;
		return 3;
	}
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
		enum path paths[3];
		unsigned int count = available_paths(backend, operation, paths);
		unsigned int index;

		for (index = 0; index < count; ++index)
			invoke_loop(operation, paths[index], warmup);
	}

	puts("backend,api,repeat,path,tsc_cycles_per_call,pmu_enabled,"
	     "pmu_cycles_per_call,instructions_per_call,branches_per_call,"
	     "branch_misses_per_call,cache_references_per_call,"
	     "cache_misses_per_call,l1d_load_misses_per_call,"
	     "llc_load_misses_per_call");
	for (operation = 0; operation < OP_COUNT; ++operation) {
		enum path paths[3];
		unsigned int count = available_paths(backend, operation, paths);

		for (repeat = 0; repeat < repeats; ++repeat) {
			unsigned int step;

			for (step = 0; step < count; ++step) {
				enum path path = paths[(step + repeat) % count];
				struct measurement value =
					measure(operation, path, iterations);

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
			raw ? &data->raw.cycles : &data->hres.cycles;
		const struct vkso_hres_base_bench *base =
			raw ? &data->raw.monotonic_raw_base :
			      &data->hres.monotonic_base;
		uint32_t seq = __atomic_load_n(&data->seq, __ATOMIC_ACQUIRE);

		if (seq & 1) {
			result.odd++;
			result.retries++;
			continue;
		}
		checksum ^= cycles->cycle_last;
		checksum ^= cycles->mult;
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
		Dl_info info;
		const struct vkso_shared_data_bench *data;
		struct seq_result hres, raw;

		if (!dladdr((const void *)vkso_clock_gettime_core, &info) ||
		    !info.dli_fbase)
			fail_message("cannot locate libkernel.so base");
		data = (const void *)((uintptr_t)info.dli_fbase +
				     (uintptr_t)VKSO_SHARED_ST_VALUE);
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

static void usage(const char *program)
{
	fprintf(stderr,
		"usage: %s --probe | --backend {raw|vkso} "
		"[--mode perf|seq|layout] [--cpu N] [--iterations N] "
		"[--repeats N] [--warmup N] [--pmu 0|1] "
		"[--seq-iterations N] [--layout-iterations N]\n",
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
	int backend_set = 0;
	int index;

	if (argc == 2 && !strcmp(argv[1], "--probe")) {
		enum backend detected = detect_backend();

		printf("backend=%s\n", backend_name(detected));
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
			else
				fail_message("mode must be perf, seq or layout");
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
	else
		run_layout(layout_iterations, repeats);
	return sink == UINT64_MAX;
}
