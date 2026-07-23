#define _GNU_SOURCE

#include <errno.h>
#include <dlfcn.h>
#include <elf.h>
#include <fcntl.h>
#include <link.h>
#include <pthread.h>
#include <sched.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <sys/timex.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define SAMPLES 10000U
#define VKSO_TIME_ABI_VERSION 6U
#define VKSO_MM_DATA_ABI_VERSION 2U
#define VKSO_TIME_OK 0
#define VKSO_TIME_FALLBACK (-1)
#define AT_VKSO_MM_DATA 52
#define READ_ONCE(value) __atomic_load_n(&(value), __ATOMIC_RELAXED)
#ifndef CLONE_NEWTIME
#define CLONE_NEWTIME 0x00000080
#endif
#define MONOTONIC_OFFSET_SEC 7
#define MONOTONIC_OFFSET_NSEC 123456789U
#define BOOTTIME_OFFSET_SEC 11
#define BOOTTIME_OFFSET_NSEC 234567890U
#define TAI_OFFSET_SEC 37

struct vkso_time_value {
	int64_t sec;
	uint64_t nsec;
} __attribute__((__may_alias__));

struct vkso_timeval {
	int64_t sec;
	int64_t usec;
} __attribute__((__may_alias__));

struct vkso_timezone {
	int32_t minuteswest;
	int32_t dsttime;
} __attribute__((__may_alias__));

struct vkso_hres_base {
	int64_t sec;
	uint64_t shifted_nsec;
};

struct vkso_cycle_data {
	int32_t clock_mode;
	uint32_t reserved;
	uint64_t cycle_last;
	uint64_t mask;
	uint32_t mult;
	uint32_t shift;
};

struct vkso_hres_data {
	struct vkso_cycle_data cycles;
	struct vkso_hres_base realtime_base;
	struct vkso_hres_base monotonic_base;
	struct vkso_hres_base boottime_base;
	struct vkso_hres_base tai_base;
};

struct vkso_raw_data {
	struct vkso_cycle_data cycles;
	struct vkso_hres_base monotonic_raw_base;
};

struct vkso_hres_cycle_sample {
	uint32_t seq;
	uint32_t retries;
	int32_t clock_mode;
	uint32_t shift;
	uint64_t cycles;
	uint64_t cycle_last;
	uint64_t mask;
	uint32_t mult;
	uint32_t reserved;
	struct vkso_hres_base realtime_base;
};

struct vkso_shared_data {
	uint32_t seq;
	uint32_t abi_version;
	struct vkso_time_value realtime_coarse;
	struct vkso_time_value monotonic_coarse;
	struct vkso_hres_data hres;
	struct vkso_raw_data raw;
	uint32_t hrtimer_resolution;
	uint32_t reserved;
};

struct vkso_mm_data {
	uint32_t abi_version;
	uint32_t reserved;
	struct vkso_time_value monotonic_offset;
	struct vkso_time_value boottime_offset;
};

typedef int (*vkso_clock_gettime_fn)(const struct vkso_mm_data *, int,
				    struct vkso_time_value *);
typedef int (*vkso_clock_getres_fn)(int, struct vkso_time_value *);
typedef int (*vkso_gettimeofday_fn)(struct vkso_timeval *,
				    struct vkso_timezone *);
typedef int (*vkso_hres_cycle_probe_at_fn)(
	const struct vkso_shared_data *, struct vkso_hres_cycle_sample *);

_Static_assert(sizeof(struct timespec) == sizeof(struct vkso_time_value) &&
	       offsetof(struct timespec, tv_sec) ==
	       offsetof(struct vkso_time_value, sec) &&
	       offsetof(struct timespec, tv_nsec) ==
	       offsetof(struct vkso_time_value, nsec),
	       "timespec and VKSO result layouts differ");

struct retry_test {
	struct vkso_shared_data shared;
	int ready;
	int stop;
};

struct shared_lookup {
	uintptr_t text_symbol;
	struct vkso_shared_data *shared;
};

static int find_shared_load(struct dl_phdr_info *info, size_t size, void *data)
{
	struct shared_lookup *lookup = data;
	int contains_text = 0;
	unsigned int i;

	(void)size;
	for (i = 0; i < info->dlpi_phnum; ++i) {
		const ElfW(Phdr) *phdr = &info->dlpi_phdr[i];
		uintptr_t start = info->dlpi_addr + phdr->p_vaddr;

		if (phdr->p_type == PT_LOAD && (phdr->p_flags & PF_X) &&
		    lookup->text_symbol >= start &&
		    lookup->text_symbol < start + phdr->p_memsz) {
			contains_text = 1;
			break;
		}
	}
	if (!contains_text)
		return 0;
	for (i = 0; i < info->dlpi_phnum; ++i) {
		const ElfW(Phdr) *phdr = &info->dlpi_phdr[i];

		if (phdr->p_type == PT_LOAD && phdr->p_flags == PF_R &&
		    phdr->p_memsz == 4096) {
			lookup->shared = (void *)(info->dlpi_addr + phdr->p_vaddr);
			return 1;
		}
	}
	return 0;
}

static int64_t to_ns(const struct timespec *ts)
{
	return (int64_t)ts->tv_sec * INT64_C(1000000000) + ts->tv_nsec;
}

static int64_t timeval_to_us(const struct timeval *tv)
{
	return (int64_t)tv->tv_sec * INT64_C(1000000) + tv->tv_usec;
}

static void fail(const char *message)
{
	fprintf(stderr, "failure=%s\n", message);
	exit(1);
}

static void check_gettimeofday_timeval(vkso_gettimeofday_fn gettimeofday)
{
	int64_t previous = 0;
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		struct timeval before, after;
		struct vkso_timeval current;
		int64_t current_us;

		if (syscall(SYS_gettimeofday, &before, NULL) ||
		    gettimeofday(&current, NULL) ||
		    syscall(SYS_gettimeofday, &after, NULL))
			fail("gettimeofday timeval");
		current_us = current.sec * INT64_C(1000000) + current.usec;
		if (current.usec < 0 || current.usec >= 1000000 ||
		    current_us < timeval_to_us(&before) ||
		    current_us > timeval_to_us(&after) ||
		    (i && current_us < previous))
			fail("gettimeofday timeval value");
		previous = current_us;
	}
	printf("user_gettimeofday_timeval=pass samples=%u\n", SAMPLES);
}

static void check_hres_resolution(vkso_clock_getres_fn clock_getres)
{
	static const clockid_t clocks[] = {
		CLOCK_REALTIME, CLOCK_MONOTONIC, CLOCK_MONOTONIC_RAW,
		CLOCK_BOOTTIME, CLOCK_TAI,
	};
	unsigned int i, clock;

	for (clock = 0; clock < sizeof(clocks) / sizeof(clocks[0]); ++clock) {
		for (i = 0; i < SAMPLES; ++i) {
			struct vkso_time_value value;
			struct timespec expected;

			if (syscall(SYS_clock_getres, clocks[clock], &expected) ||
			    clock_getres(clocks[clock], &value) ||
			    value.sec != expected.tv_sec ||
			    value.nsec != (uint64_t)expected.tv_nsec)
				fail("high-resolution clock_getres");
		}
	}
	printf("user_clock_getres_hres=pass clocks=%zu samples=%u\n",
	       sizeof(clocks) / sizeof(clocks[0]), SAMPLES);
}

static int vkso_clock_getres_with_fallback(
	vkso_clock_getres_fn clock_getres, clockid_t clock_id,
	struct timespec *tp)
{
	long ret;

	if (clock_getres(clock_id, (struct vkso_time_value *)tp) ==
	    VKSO_TIME_OK)
		return 0;
	asm("syscall" : "=a" (ret), "=m" (*tp) :
	    "0" (SYS_clock_getres), "D" (clock_id), "S" (tp) :
	    "rcx", "r11");
	return ret;
}

static void check_coarse_resolution(vkso_clock_getres_fn clock_getres)
{
	static const clockid_t clocks[] = {
		CLOCK_REALTIME_COARSE, CLOCK_MONOTONIC_COARSE,
	};
	unsigned int i, clock;

	for (clock = 0; clock < sizeof(clocks) / sizeof(clocks[0]); ++clock) {
		for (i = 0; i < SAMPLES; ++i) {
			struct vkso_time_value value;
			struct timespec expected;

			if (syscall(SYS_clock_getres, clocks[clock], &expected) ||
			    clock_getres(clocks[clock], &value) ||
			    value.sec != expected.tv_sec ||
			    value.nsec != (uint64_t)expected.tv_nsec)
				fail("coarse clock_getres");
		}
	}
	printf("user_clock_getres_coarse=pass clocks=%zu samples=%u\n",
	       sizeof(clocks) / sizeof(clocks[0]), SAMPLES);
}

static void check_clock_getres_null(vkso_clock_getres_fn clock_getres)
{
	static const clockid_t clocks[] = {
		CLOCK_REALTIME, CLOCK_MONOTONIC, CLOCK_MONOTONIC_RAW,
		CLOCK_REALTIME_COARSE, CLOCK_MONOTONIC_COARSE,
		CLOCK_BOOTTIME, CLOCK_TAI,
	};
	unsigned int clock;

	for (clock = 0; clock < sizeof(clocks) / sizeof(clocks[0]); ++clock) {
		if (clock_getres(clocks[clock], NULL) ||
		    vkso_clock_getres_with_fallback(clock_getres,
						    clocks[clock], NULL))
			fail("clock_getres NULL");
	}
	if (vkso_clock_getres_with_fallback(clock_getres,
					    CLOCK_PROCESS_CPUTIME_ID, NULL))
		fail("clock_getres fallback NULL");
	puts("user_clock_getres_null=pass");
}

static void check_clock_getres_fallback(
	vkso_clock_getres_fn clock_getres, clockid_t clock_id)
{
	struct vkso_time_value core_value;
	struct timespec expected, value;

	if (clock_getres(clock_id, &core_value) != VKSO_TIME_FALLBACK)
		fail("unsupported clock_getres accepted by core");
	errno = 0;
	if (!syscall(SYS_clock_getres, clock_id, &expected)) {
		if (vkso_clock_getres_with_fallback(clock_getres, clock_id,
						    &value) ||
		    value.tv_sec != expected.tv_sec ||
		    value.tv_nsec != expected.tv_nsec)
			fail("clock_getres fallback value");
		return;
	}
	{
		int expected_errno = errno;

		errno = 0;
		if (vkso_clock_getres_with_fallback(clock_getres, clock_id,
						    &value) !=
		    -expected_errno || errno)
			fail("clock_getres fallback error");
	}
}

static void check_invalid_clock_getres(
	vkso_clock_getres_fn clock_getres, clockid_t clock_id)
{
	struct vkso_time_value core_value;
	struct timespec value;

	if (clock_getres(clock_id, &core_value) != VKSO_TIME_FALLBACK)
		fail("invalid clock_getres accepted by core");
	errno = 0;
	if (vkso_clock_getres_with_fallback(clock_getres, clock_id,
					    &value) != -EINVAL ||
	    errno)
		fail("invalid clock_getres fallback");
}

static int vkso_clock_gettime_with_fallback(
	vkso_clock_gettime_fn clock_gettime,
	const struct vkso_mm_data *mm_data, clockid_t clock_id,
	struct timespec *tp)
{
	long ret;

	if (clock_gettime(mm_data, clock_id,
			  (struct vkso_time_value *)tp) == VKSO_TIME_OK)
		return 0;
	/* Match the x86 vDSO ABI: return the raw negative syscall error. */
	asm("syscall" : "=a" (ret), "=m" (*tp) :
	    "0" (SYS_clock_gettime), "D" (clock_id), "S" (tp) :
	    "rcx", "r11");
	return ret;
}

static void check_fallback_clock(vkso_clock_gettime_fn clock_gettime,
				 const struct vkso_mm_data *mm_data,
				 clockid_t clock_id, const char *marker)
{
	struct vkso_time_value core_value;
	struct timespec probe;
	unsigned int i;

	if (clock_gettime(mm_data, clock_id, &core_value) !=
	    VKSO_TIME_FALLBACK)
		fail("unsupported clock accepted by core");
	errno = 0;
	if (syscall(SYS_clock_gettime, clock_id, &probe)) {
		int expected_errno = errno;

		errno = 0;
		if (vkso_clock_gettime_with_fallback(clock_gettime, mm_data,
						     clock_id, &probe) !=
		    -expected_errno || errno)
			fail("fallback error mismatch");
		printf("%s=pass errno=%d\n", marker, expected_errno);
		return;
	}
	for (i = 0; i < SAMPLES; ++i) {
		struct timespec before, current, after;

		if (syscall(SYS_clock_gettime, clock_id, &before) ||
		    vkso_clock_gettime_with_fallback(clock_gettime, mm_data,
						     clock_id, &current) ||
		    syscall(SYS_clock_gettime, clock_id, &after))
			fail("fallback clock call");
		if (current.tv_nsec < 0 || current.tv_nsec >= 1000000000L ||
		    to_ns(&current) < to_ns(&before) ||
		    to_ns(&current) > to_ns(&after))
			fail("fallback clock bracket");
	}
	printf("%s=pass samples=%u\n", marker, SAMPLES);
}

static void check_invalid_clock_fallback(
	vkso_clock_gettime_fn clock_gettime,
	const struct vkso_mm_data *mm_data, clockid_t clock_id)
{
	struct vkso_time_value core_value;
	struct timespec value;

	if (clock_gettime(mm_data, clock_id, &core_value) !=
	    VKSO_TIME_FALLBACK)
		fail("invalid clock accepted by core");
	errno = 0;
	if (syscall(SYS_clock_gettime, clock_id, &value) != -1 ||
	    errno != EINVAL)
		fail("invalid clock syscall semantics");
	errno = 0;
	if (vkso_clock_gettime_with_fallback(clock_gettime, mm_data,
					     clock_id, &value) != -EINVAL ||
	    errno)
		fail("invalid clock fallback semantics");
}

static void require_mapping(const void *address, int executable)
{
	char line[512], permissions[5];
	unsigned long start, end;
	FILE *maps = fopen("/proc/self/maps", "r");

	if (!maps)
		fail("open maps");
	while (fgets(line, sizeof(line), maps)) {
		if (sscanf(line, "%lx-%lx %4s", &start, &end, permissions) != 3)
			continue;
		if ((uintptr_t)address < start || (uintptr_t)address >= end)
			continue;
		fclose(maps);
		if (permissions[0] != 'r' || permissions[1] == 'w' ||
		    (permissions[2] == 'x') != executable)
			fail(executable ? "text permissions" : "data permissions");
		return;
	}
	fclose(maps);
	fail("mapping not found");
}

static void check_monotonic_coarse(vkso_clock_gettime_fn clock_gettime,
				   const struct vkso_mm_data *mm_data)
{
	struct timespec previous = { 0 };
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		struct timespec before, after, current;
		struct vkso_time_value value;

		if (syscall(SYS_clock_gettime, CLOCK_MONOTONIC_COARSE, &before) ||
		    clock_gettime(mm_data, CLOCK_MONOTONIC_COARSE, &value) ||
		    syscall(SYS_clock_gettime, CLOCK_MONOTONIC_COARSE, &after))
			fail("monotonic coarse call");
		current.tv_sec = value.sec;
		current.tv_nsec = (long)value.nsec;
		if (to_ns(&current) < to_ns(&before) ||
		    to_ns(&current) > to_ns(&after) ||
		    (i && to_ns(&current) < to_ns(&previous)))
			fail("monotonic coarse bracket");
		previous = current;
	}
}

static void check_realtime(vkso_clock_gettime_fn clock_gettime)
{
	struct timespec previous = { 0 };
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		struct timespec before, after, current;
		struct vkso_time_value value;

		if (syscall(SYS_clock_gettime, CLOCK_REALTIME, &before) ||
		    clock_gettime(NULL, CLOCK_REALTIME, &value) ||
		    syscall(SYS_clock_gettime, CLOCK_REALTIME, &after))
			fail("realtime call");
		current.tv_sec = value.sec;
		current.tv_nsec = (long)value.nsec;
		if (current.tv_nsec < 0 || current.tv_nsec >= 1000000000L ||
		    to_ns(&current) < to_ns(&before) ||
		    to_ns(&current) > to_ns(&after) ||
		    (i && to_ns(&current) < to_ns(&previous)))
			fail("realtime bracket");
		previous = current;
	}
	printf("user_realtime=pass samples=%u\n", SAMPLES);
}

static void set_tai_offset(void)
{
	struct timex tx = {
		.modes = ADJ_TAI,
		.constant = TAI_OFFSET_SEC,
	};

	if (syscall(SYS_adjtimex, &tx) < 0)
		fail("set TAI offset");
	memset(&tx, 0, sizeof(tx));
	if (syscall(SYS_adjtimex, &tx) < 0 || tx.tai != TAI_OFFSET_SEC)
		fail("read TAI offset");
}

static void check_tai_offset(vkso_clock_gettime_fn clock_gettime,
			     const struct vkso_mm_data *mm_data)
{
	struct timespec previous = { 0 };
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		struct vkso_time_value before_value, tai_value, after_value;
		struct timespec before, tai, after;

		if (clock_gettime(NULL, CLOCK_REALTIME, &before_value) ||
		    clock_gettime(mm_data, CLOCK_TAI, &tai_value) ||
		    clock_gettime(NULL, CLOCK_REALTIME, &after_value))
			fail("TAI offset clock call");
		before.tv_sec = before_value.sec;
		before.tv_nsec = (long)before_value.nsec;
		tai.tv_sec = tai_value.sec - TAI_OFFSET_SEC;
		tai.tv_nsec = (long)tai_value.nsec;
		after.tv_sec = after_value.sec;
		after.tv_nsec = (long)after_value.nsec;
		if (to_ns(&tai) < to_ns(&before) ||
		    to_ns(&tai) > to_ns(&after) ||
		    (i && to_ns(&tai) < to_ns(&previous)))
			fail("TAI offset relation");
		previous = tai;
	}
	printf("tai_offset=pass seconds=%d samples=%u\n",
	       TAI_OFFSET_SEC, SAMPLES);
}

static void check_hres_clock(vkso_clock_gettime_fn clock_gettime,
			     const struct vkso_mm_data *mm_data,
			     clockid_t clock_id)
{
	struct timespec previous = { 0 };
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		struct timespec before, after, current;
		struct vkso_time_value value;

		if (syscall(SYS_clock_gettime, clock_id, &before) ||
		    clock_gettime(mm_data, clock_id, &value) ||
		    syscall(SYS_clock_gettime, clock_id, &after))
			fail("high-resolution clock call");
		current.tv_sec = value.sec;
		current.tv_nsec = (long)value.nsec;
		if (current.tv_nsec < 0 || current.tv_nsec >= 1000000000L ||
		    to_ns(&current) < to_ns(&before) ||
		    to_ns(&current) > to_ns(&after) ||
		    (i && to_ns(&current) < to_ns(&previous)))
			fail("high-resolution clock bracket");
		previous = current;
	}
}

static void check_namespace_application(
	vkso_clock_gettime_fn clock_gettime,
	const struct vkso_mm_data *mm_data, clockid_t clock_id)
{
	struct vkso_mm_data root_mm = *mm_data;
	struct vkso_time_value *root_offset;
	const struct vkso_time_value *offset;
	struct vkso_time_value before_value, after_value;
	struct timespec before, current, after;
	int64_t offset_ns;

	if (clock_id == CLOCK_BOOTTIME) {
		root_offset = &root_mm.boottime_offset;
		offset = &mm_data->boottime_offset;
	} else {
		root_offset = &root_mm.monotonic_offset;
		offset = &mm_data->monotonic_offset;
	}
	offset_ns = offset->sec * INT64_C(1000000000) + offset->nsec;
	root_offset->sec = 0;
	root_offset->nsec = 0;
	if (clock_gettime(&root_mm, clock_id, &before_value))
		fail("root clock before namespace oracle");
	before.tv_sec = before_value.sec;
	before.tv_nsec = (long)before_value.nsec;
	if (syscall(SYS_clock_gettime, clock_id, &current))
		fail("namespace clock syscall");
	if (clock_gettime(&root_mm, clock_id, &after_value))
		fail("root clock after namespace oracle");
	after.tv_sec = after_value.sec;
	after.tv_nsec = (long)after_value.nsec;
	if (to_ns(&current) < to_ns(&before) + offset_ns ||
	    to_ns(&current) > to_ns(&after) + offset_ns)
		fail("namespace offset application");
}

static void check_tai_namespace_independence(
	vkso_clock_gettime_fn clock_gettime,
	const struct vkso_mm_data *mm_data)
{
	struct vkso_mm_data root_mm = *mm_data;

	root_mm.monotonic_offset.sec = 0;
	root_mm.monotonic_offset.nsec = 0;
	root_mm.boottime_offset.sec = 0;
	root_mm.boottime_offset.nsec = 0;
	check_hres_clock(clock_gettime, &root_mm, CLOCK_TAI);
	check_hres_clock(clock_gettime, mm_data, CLOCK_TAI);
}

static void *seq_writer(void *argument)
{
	struct retry_test *test = argument;
	uint64_t generation = 1;

	while (!__atomic_load_n(&test->stop, __ATOMIC_ACQUIRE)) {
		uint32_t seq = READ_ONCE(test->shared.seq);
		unsigned int spin;

		__atomic_store_n(&test->shared.seq, seq + 1, __ATOMIC_RELEASE);
		if (generation == 1) {
			/* Hand the single QEMU CPU to a reader while seq is odd. */
			__atomic_store_n(&test->ready, 1, __ATOMIC_RELEASE);
			sched_yield();
		}
		__atomic_store_n(&test->shared.abi_version,
				 VKSO_TIME_ABI_VERSION, __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.cycles.clock_mode, 1,
				 __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.cycles.cycle_last, generation,
				 __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.cycles.mask, ~generation,
				 __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.cycles.mult,
				 (uint32_t)generation | 1U, __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.cycles.shift,
				 (uint32_t)(generation % 31), __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.realtime_base.sec,
				 (int64_t)generation, __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.realtime_base.shifted_nsec,
				 generation * 17, __ATOMIC_RELAXED);
		for (spin = 0; spin < 256; ++spin)
			__asm__ volatile("pause");
		__atomic_store_n(&test->shared.seq, seq + 2, __ATOMIC_RELEASE);
		generation++;
		sched_yield();
	}
	return NULL;
}

static void check_tsc_cycles_shim(vkso_hres_cycle_probe_at_fn probe_at,
				  const struct vkso_shared_data *shared)
{
	struct timespec previous = { 0 };
	struct vkso_hres_cycle_sample sample;
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		uint64_t delta, ns;
		struct timespec before, after, current;

		if (syscall(SYS_clock_gettime, CLOCK_REALTIME, &before))
			fail("hres before oracle");
		if (probe_at(shared, &sample) != 0 || sample.clock_mode != 1 ||
		    !sample.cycles || !sample.cycle_last || !sample.mult ||
		    sample.mask != UINT64_MAX || sample.shift >= 32 ||
		    (sample.seq & 1U))
			fail("TSC cycles shim");
		delta = sample.cycles > sample.cycle_last ?
			sample.cycles - sample.cycle_last : 0;
		ns = (sample.realtime_base.shifted_nsec + delta * sample.mult) >>
		     sample.shift;
		current.tv_sec = sample.realtime_base.sec +
			(int64_t)(ns / UINT64_C(1000000000));
		current.tv_nsec = (long)(ns % UINT64_C(1000000000));
		if (syscall(SYS_clock_gettime, CLOCK_REALTIME, &after))
			fail("hres after oracle");
		if (to_ns(&current) < to_ns(&before) ||
		    to_ns(&current) > to_ns(&after) ||
		    (i && to_ns(&current) < to_ns(&previous)))
			fail("hres snapshot bracket");
		previous = current;
	}
	printf("hres_snapshot=pass samples=%u\n", SAMPLES);
	printf("tsc_cycles_shim=pass samples=%u\n", SAMPLES);
}

static void check_seq_retry(vkso_hres_cycle_probe_at_fn probe_at)
{
	struct retry_test test = { 0 };
	pthread_t writer;
	uint64_t total_retries = 0;
	uint64_t previous_generation = 0;
	unsigned int i;

	if (pthread_create(&writer, NULL, seq_writer, &test))
		fail("create seq writer");
	while (!__atomic_load_n(&test.ready, __ATOMIC_ACQUIRE))
		sched_yield();
	for (i = 0; i < SAMPLES; ++i) {
		struct vkso_hres_cycle_sample sample;
		uint64_t generation;

		if (probe_at(&test.shared, &sample) != 0)
			fail("concurrent seq probe");
		generation = (uint64_t)sample.realtime_base.sec;
		if (!generation || sample.clock_mode != 1 || !sample.cycles ||
		    sample.cycle_last != generation ||
		    sample.mask != ~generation ||
		    sample.mult != ((uint32_t)generation | 1U) ||
		    sample.shift != generation % 31 ||
		    sample.realtime_base.shifted_nsec != generation * 17 ||
		    generation < previous_generation || (sample.seq & 1U))
			fail("mixed seq generation");
		previous_generation = generation;
		total_retries += sample.retries;
	}
	__atomic_store_n(&test.stop, 1, __ATOMIC_RELEASE);
	if (pthread_join(writer, NULL))
		fail("join seq writer");
	if (!total_retries)
		fail("seq retry not observed");
	printf("seq_retry_concurrency=pass samples=%u retries=%llu\n",
	       SAMPLES, (unsigned long long)total_retries);
}

static void check_time_namespace(vkso_clock_gettime_fn clock_gettime)
{
	static const char offsets[] =
		"monotonic 7 123456789\n"
		"boottime 11 234567890\n";
	int fd, status;
	pid_t child;

	if (unshare(CLONE_NEWTIME))
		fail("unshare time namespace");
	fd = open("/proc/self/timens_offsets", O_WRONLY | O_CLOEXEC);
	if (fd < 0 ||
	    write(fd, offsets, sizeof(offsets) - 1) != sizeof(offsets) - 1)
		fail("set time namespace offsets");
	close(fd);
	fflush(NULL);
	child = fork();
	if (child < 0)
		fail("fork time namespace child");
	if (!child) {
		const struct vkso_mm_data *mm_data =
			(const void *)getauxval(AT_VKSO_MM_DATA);

		if (!mm_data ||
		    mm_data->monotonic_offset.sec != MONOTONIC_OFFSET_SEC ||
		    mm_data->monotonic_offset.nsec != MONOTONIC_OFFSET_NSEC ||
		    mm_data->boottime_offset.sec != BOOTTIME_OFFSET_SEC ||
		    mm_data->boottime_offset.nsec != BOOTTIME_OFFSET_NSEC)
			_exit(2);
		check_hres_clock(clock_gettime, mm_data, CLOCK_MONOTONIC);
		check_namespace_application(clock_gettime, mm_data,
					    CLOCK_MONOTONIC);
		check_hres_clock(clock_gettime, mm_data, CLOCK_MONOTONIC_RAW);
		check_namespace_application(clock_gettime, mm_data,
					    CLOCK_MONOTONIC_RAW);
		check_monotonic_coarse(clock_gettime, mm_data);
		check_hres_clock(clock_gettime, mm_data, CLOCK_BOOTTIME);
		check_namespace_application(clock_gettime, mm_data,
					    CLOCK_BOOTTIME);
		check_tai_namespace_independence(clock_gettime, mm_data);
		puts("monotonic_raw_hres_namespace_offset=pass");
		puts("monotonic_hres_namespace_offset=pass");
		puts("monotonic_namespace_offset=pass");
		puts("boottime_namespace_offset=pass");
		puts("tai_namespace_independent=pass");
		fflush(stdout);
		_exit(0);
	}
	if (waitpid(child, &status, 0) != child || !WIFEXITED(status) ||
	    WEXITSTATUS(status))
		fail("time namespace child");
}

int main(void)
{
	vkso_clock_gettime_fn vkso_clock_gettime;
	vkso_clock_getres_fn vkso_clock_getres;
	vkso_gettimeofday_fn vkso_gettimeofday;
	vkso_hres_cycle_probe_at_fn vkso_hres_cycle_probe_at;
	struct shared_lookup lookup = { 0 };
	struct vkso_shared_data *shared;
	const struct vkso_mm_data *mm_data;
	struct timespec previous = { 0 };
	Dl_info info;
	void *symbol;
	unsigned int i;

	symbol = dlsym(RTLD_DEFAULT, "__vkso_clock_gettime");
	memcpy(&vkso_clock_gettime, &symbol, sizeof(vkso_clock_gettime));
	if (!vkso_clock_gettime || !dladdr(symbol, &info))
		fail("resolve symbols");
	symbol = dlsym(RTLD_DEFAULT, "__vkso_clock_getres");
	memcpy(&vkso_clock_getres, &symbol, sizeof(vkso_clock_getres));
	if (!vkso_clock_getres)
		fail("resolve clock_getres");
	symbol = dlsym(RTLD_DEFAULT, "__vkso_gettimeofday");
	memcpy(&vkso_gettimeofday, &symbol, sizeof(vkso_gettimeofday));
	if (!vkso_gettimeofday)
		fail("resolve gettimeofday");
	mm_data = (const void *)getauxval(AT_VKSO_MM_DATA);
	if (!mm_data || mm_data->abi_version != VKSO_MM_DATA_ABI_VERSION)
		fail("resolve mm data");
	if (mm_data->monotonic_offset.sec || mm_data->monotonic_offset.nsec ||
	    mm_data->boottime_offset.sec || mm_data->boottime_offset.nsec)
		fail("root namespace offset");
	lookup.text_symbol = (uintptr_t)symbol;
	dl_iterate_phdr(find_shared_load, &lookup);
	shared = lookup.shared;
	if (!shared)
		fail("resolve shared load");
	symbol = dlsym(RTLD_DEFAULT, "__vkso_test_hres_cycle_probe_at");
	memcpy(&vkso_hres_cycle_probe_at, &symbol,
	       sizeof(vkso_hres_cycle_probe_at));
	if (!vkso_hres_cycle_probe_at)
		fail("resolve M08 symbols");

	require_mapping(symbol, 1);
	require_mapping(shared, 0);
	if (shared->abi_version != VKSO_TIME_ABI_VERSION ||
	    (shared->seq & 1) ||
	    !shared->hrtimer_resolution ||
	    shared->realtime_coarse.nsec >= UINT64_C(1000000000) ||
	    shared->monotonic_coarse.nsec >= UINT64_C(1000000000))
		fail("shared data layout");
	check_hres_resolution(vkso_clock_getres);
	check_gettimeofday_timeval(vkso_gettimeofday);
	check_coarse_resolution(vkso_clock_getres);
	check_clock_getres_null(vkso_clock_getres);
	check_clock_getres_fallback(vkso_clock_getres,
				    CLOCK_PROCESS_CPUTIME_ID);
	check_clock_getres_fallback(vkso_clock_getres,
				    CLOCK_THREAD_CPUTIME_ID);
	check_clock_getres_fallback(vkso_clock_getres, CLOCK_REALTIME_ALARM);
	check_clock_getres_fallback(vkso_clock_getres, CLOCK_BOOTTIME_ALARM);
	check_invalid_clock_getres(vkso_clock_getres, 12345);
	check_invalid_clock_getres(vkso_clock_getres, -1);
	puts("user_clock_getres_fallback=pass");
	puts("user_clock_getres_invalid=pass errno=EINVAL");
	set_tai_offset();
	check_realtime(vkso_clock_gettime);
	check_hres_clock(vkso_clock_gettime, mm_data, CLOCK_MONOTONIC);
	printf("user_monotonic=pass samples=%u\n", SAMPLES);
	check_hres_clock(vkso_clock_gettime, mm_data, CLOCK_MONOTONIC_RAW);
	printf("user_monotonic_raw=pass samples=%u\n", SAMPLES);
	check_hres_clock(vkso_clock_gettime, mm_data, CLOCK_BOOTTIME);
	printf("user_boottime=pass samples=%u\n", SAMPLES);
	check_hres_clock(vkso_clock_gettime, mm_data, CLOCK_TAI);
	printf("user_tai=pass samples=%u\n", SAMPLES);
	check_tai_offset(vkso_clock_gettime, mm_data);
	check_tsc_cycles_shim(vkso_hres_cycle_probe_at, shared);
	check_seq_retry(vkso_hres_cycle_probe_at);

	for (i = 0; i < SAMPLES; ++i) {
		struct timespec before, after, current, realtime;
		struct vkso_time_value value;

		if (syscall(SYS_clock_gettime, CLOCK_REALTIME_COARSE, &before) ||
		    vkso_clock_gettime(mm_data, CLOCK_REALTIME_COARSE, &value) ||
		    syscall(SYS_clock_gettime, CLOCK_REALTIME_COARSE, &after))
			fail("clock call");
		current.tv_sec = value.sec;
		current.tv_nsec = (long)value.nsec;
		if (syscall(SYS_clock_gettime, CLOCK_REALTIME, &realtime))
			fail("realtime oracle");
		if (to_ns(&current) < to_ns(&before) ||
		    to_ns(&current) > to_ns(&after) ||
		    llabs(to_ns(&realtime) - to_ns(&current)) >
			    INT64_C(1000000000) ||
		    (i && to_ns(&current) < to_ns(&previous)))
			fail("clock bracket");
		previous = current;
	}
	check_monotonic_coarse(vkso_clock_gettime, mm_data);

	check_fallback_clock(vkso_clock_gettime, mm_data,
			     CLOCK_PROCESS_CPUTIME_ID,
			     "user_process_cputime_fallback");
	check_fallback_clock(vkso_clock_gettime, mm_data,
			     CLOCK_THREAD_CPUTIME_ID,
			     "user_thread_cputime_fallback");
	check_fallback_clock(vkso_clock_gettime, mm_data,
			     CLOCK_REALTIME_ALARM,
			     "user_realtime_alarm_fallback");
	check_fallback_clock(vkso_clock_gettime, mm_data,
			     CLOCK_BOOTTIME_ALARM,
			     "user_boottime_alarm_fallback");
	check_invalid_clock_fallback(vkso_clock_gettime, mm_data, 12345);
	check_invalid_clock_fallback(vkso_clock_gettime, mm_data, -1);

	printf("user_realtime_coarse=pass samples=%u\n", SAMPLES);
	printf("user_monotonic_coarse=pass samples=%u\n", SAMPLES);
	puts("unsupported_clock_fallback=pass");
	puts("user_invalid_clock_fallback=pass errno=EINVAL");
	check_time_namespace(vkso_clock_gettime);
	printf("text=%p shared_data=%p delta=%td\n", symbol, shared,
	       (char *)shared - (char *)symbol);
	puts("mapping_permissions=pass");
	puts("rip_relative_shared_read=pass");
	return 0;
}
