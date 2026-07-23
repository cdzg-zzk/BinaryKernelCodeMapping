#define _GNU_SOURCE

#include <dlfcn.h>
#include <elf.h>
#include <fcntl.h>
#include <link.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define SAMPLES 10000U
#define VKSO_TIME_ABI_VERSION 1U
#define VKSO_MM_DATA_ABI_VERSION 1U
#define VKSO_TIME_FALLBACK (-1)
#define AT_VKSO_MM_DATA 52
#define READ_ONCE(value) __atomic_load_n(&(value), __ATOMIC_RELAXED)
#ifndef CLONE_NEWTIME
#define CLONE_NEWTIME 0x00000080
#endif
#define MONOTONIC_OFFSET_SEC 7
#define MONOTONIC_OFFSET_NSEC 123456789U

struct vkso_time_value {
	int64_t sec;
	uint64_t nsec;
};

struct vkso_hres_base {
	int64_t sec;
	uint64_t shifted_nsec;
};

struct vkso_hres_data {
	int32_t clock_mode;
	uint32_t reserved;
	uint64_t cycle_last;
	uint64_t mask;
	uint32_t mult;
	uint32_t shift;
	struct vkso_hres_base realtime_base;
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
};

struct vkso_mm_data {
	uint32_t abi_version;
	uint32_t flags;
	struct vkso_time_value monotonic_offset;
};

typedef int (*vkso_clock_gettime_fn)(const struct vkso_mm_data *, int,
				    struct vkso_time_value *);
typedef int (*vkso_hres_cycle_probe_fn)(struct vkso_hres_cycle_sample *);
typedef int (*vkso_hres_cycle_probe_at_fn)(
	const struct vkso_shared_data *, struct vkso_hres_cycle_sample *);

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

static uint64_t read_tsc_ordered(void)
{
	uint32_t low, high;

	__asm__ volatile("lfence\n\trdtsc"
			 : "=a" (low), "=d" (high) : : "memory");
	return ((uint64_t)high << 32) | low;
}

static void fail(const char *message)
{
	fprintf(stderr, "failure=%s\n", message);
	exit(1);
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

static void check_hres_snapshot(const struct vkso_shared_data *shared)
{
	struct timespec previous = { 0 };
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		uint64_t cycle_last, mask, shifted_nsec, cycles, delta, ns;
		uint32_t seq, mult, shift;
		int32_t clock_mode;
		int64_t base_sec;
		struct timespec before, after, current;

		if (syscall(SYS_clock_gettime, CLOCK_REALTIME, &before))
			fail("hres before oracle");
		do {
			do {
				seq = READ_ONCE(shared->seq);
			} while (seq & 1U);
			__atomic_thread_fence(__ATOMIC_ACQUIRE);
			clock_mode = READ_ONCE(shared->hres.clock_mode);
			cycles = read_tsc_ordered();
			cycle_last = READ_ONCE(shared->hres.cycle_last);
			mask = READ_ONCE(shared->hres.mask);
			mult = READ_ONCE(shared->hres.mult);
			shift = READ_ONCE(shared->hres.shift);
			base_sec = READ_ONCE(shared->hres.realtime_base.sec);
			shifted_nsec =
				READ_ONCE(shared->hres.realtime_base.shifted_nsec);
			__atomic_thread_fence(__ATOMIC_ACQUIRE);
		} while (seq != READ_ONCE(shared->seq));
		if (clock_mode != 1 || !cycle_last || mask != UINT64_MAX ||
		    !mult || shift >= 32)
			fail("hres conversion metadata");
		delta = cycles > cycle_last ? cycles - cycle_last : 0;
		ns = (shifted_nsec + delta * mult) >> shift;
		current.tv_sec = base_sec + (int64_t)(ns / UINT64_C(1000000000));
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
		__atomic_store_n(&test->shared.hres.clock_mode, 1,
				 __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.cycle_last, generation,
				 __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.mask, ~generation,
				 __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.mult,
				 (uint32_t)generation | 1U, __ATOMIC_RELAXED);
		__atomic_store_n(&test->shared.hres.shift,
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

static void check_tsc_cycles_shim(vkso_hres_cycle_probe_fn probe)
{
	struct vkso_hres_cycle_sample sample;
	unsigned int i;

	for (i = 0; i < SAMPLES; ++i) {
		if (probe(&sample) != 0 || sample.clock_mode != 1 ||
		    !sample.cycles || !sample.cycle_last || !sample.mult ||
		    sample.mask != UINT64_MAX || sample.shift >= 32 ||
		    (sample.seq & 1U))
			fail("TSC cycles shim");
	}
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

static void check_monotonic_namespace(vkso_clock_gettime_fn clock_gettime)
{
	static const char offset[] = "monotonic 7 123456789\n";
	int fd, status;
	pid_t child;

	if (unshare(CLONE_NEWTIME))
		fail("unshare time namespace");
	fd = open("/proc/self/timens_offsets", O_WRONLY | O_CLOEXEC);
	if (fd < 0 || write(fd, offset, sizeof(offset) - 1) != sizeof(offset) - 1)
		fail("set monotonic namespace offset");
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
		    mm_data->monotonic_offset.nsec != MONOTONIC_OFFSET_NSEC)
			_exit(2);
		check_monotonic_coarse(clock_gettime, mm_data);
		puts("monotonic_namespace_offset=pass");
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
	vkso_hres_cycle_probe_fn vkso_hres_cycle_probe;
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
	mm_data = (const void *)getauxval(AT_VKSO_MM_DATA);
	if (!mm_data || mm_data->abi_version != VKSO_MM_DATA_ABI_VERSION)
		fail("resolve mm data");
	if (mm_data->monotonic_offset.sec || mm_data->monotonic_offset.nsec)
		fail("root namespace offset");
	lookup.text_symbol = (uintptr_t)symbol;
	dl_iterate_phdr(find_shared_load, &lookup);
	shared = lookup.shared;
	if (!shared)
		fail("resolve shared load");
	symbol = dlsym(RTLD_DEFAULT, "__vkso_hres_cycle_probe");
	memcpy(&vkso_hres_cycle_probe, &symbol,
	       sizeof(vkso_hres_cycle_probe));
	symbol = dlsym(RTLD_DEFAULT, "__vkso_test_hres_cycle_probe_at");
	memcpy(&vkso_hres_cycle_probe_at, &symbol,
	       sizeof(vkso_hres_cycle_probe_at));
	if (!vkso_hres_cycle_probe || !vkso_hres_cycle_probe_at)
		fail("resolve M08 symbols");

	require_mapping(symbol, 1);
	require_mapping(shared, 0);
	if (shared->abi_version != VKSO_TIME_ABI_VERSION ||
	    (shared->seq & 1) ||
	    shared->realtime_coarse.nsec >= UINT64_C(1000000000) ||
	    shared->monotonic_coarse.nsec >= UINT64_C(1000000000))
		fail("shared data layout");
	check_hres_snapshot(shared);
	check_tsc_cycles_shim(vkso_hres_cycle_probe);
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

	{
		struct vkso_time_value value;

		if (vkso_clock_gettime(mm_data, CLOCK_MONOTONIC, &value) !=
		    VKSO_TIME_FALLBACK)
			fail("unsupported clock did not fallback");
	}

	printf("user_realtime_coarse=pass samples=%u\n", SAMPLES);
	printf("user_monotonic_coarse=pass samples=%u\n", SAMPLES);
	check_monotonic_namespace(vkso_clock_gettime);
	printf("text=%p shared_data=%p delta=%td\n", symbol, shared,
	       (char *)shared - (char *)symbol);
	puts("mapping_permissions=pass");
	puts("rip_relative_shared_read=pass");
	return 0;
}
