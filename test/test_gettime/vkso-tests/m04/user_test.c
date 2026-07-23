#define _GNU_SOURCE

#include <dlfcn.h>
#include <elf.h>
#include <fcntl.h>
#include <link.h>
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
#ifndef CLONE_NEWTIME
#define CLONE_NEWTIME 0x00000080
#endif
#define MONOTONIC_OFFSET_SEC 7
#define MONOTONIC_OFFSET_NSEC 123456789U

struct vkso_time_value {
	int64_t sec;
	uint64_t nsec;
};

struct vkso_shared_data {
	uint32_t seq;
	uint32_t abi_version;
	struct vkso_time_value realtime_coarse;
	struct vkso_time_value monotonic_coarse;
};

struct vkso_mm_data {
	uint32_t abi_version;
	uint32_t flags;
	struct vkso_time_value monotonic_offset;
};

typedef int (*vkso_clock_gettime_fn)(const struct vkso_mm_data *, int,
				    struct vkso_time_value *);

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

	require_mapping(symbol, 1);
	require_mapping(shared, 0);
	if (shared->abi_version != VKSO_TIME_ABI_VERSION ||
	    (shared->seq & 1) ||
	    shared->realtime_coarse.nsec >= UINT64_C(1000000000) ||
	    shared->monotonic_coarse.nsec >= UINT64_C(1000000000))
		fail("shared data layout");

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
