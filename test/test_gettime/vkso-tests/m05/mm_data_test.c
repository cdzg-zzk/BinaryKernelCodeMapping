#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define AT_VKSO_MM_DATA 52
#define VKSO_MM_DATA_ABI_VERSION 1U

struct vkso_mm_data {
	uint32_t abi_version;
	uint32_t flags;
	struct {
		int64_t sec;
		uint64_t nsec;
	} monotonic_offset;
};

static void fail(const char *message)
{
	fprintf(stderr, "failure=%s errno=%d\n", message, errno);
	exit(1);
}

static void check_mapping(const void *address)
{
	char line[512], permissions[5], name[128] = "";
	unsigned long start, end;
	FILE *maps = fopen("/proc/self/maps", "r");

	if (!maps)
		fail("open maps");
	while (fgets(line, sizeof(line), maps)) {
		int fields = sscanf(line, "%lx-%lx %4s %*s %*s %*s %127s",
				    &start, &end, permissions, name);

		if (fields < 3 || (uintptr_t)address < start ||
		    (uintptr_t)address >= end)
			continue;
		fclose(maps);
		if (end - start != (unsigned long)sysconf(_SC_PAGESIZE) ||
		    strcmp(permissions, "r--p") || fields != 4 ||
		    strcmp(name, "[vkso_mm_data]"))
			fail("mapping permissions or name");
		return;
	}
	fclose(maps);
	fail("mapping not found");
}

static uint64_t mapping_pfn(const void *address)
{
	uint64_t entry;
	long page_size = sysconf(_SC_PAGESIZE);
	off_t offset = ((uintptr_t)address / (uintptr_t)page_size) *
		       (off_t)sizeof(entry);
	int fd = open("/proc/self/pagemap", O_RDONLY | O_CLOEXEC);

	if (fd < 0)
		fail("open pagemap");
	if (pread(fd, &entry, sizeof(entry), offset) != sizeof(entry))
		fail("read pagemap");
	close(fd);
	if (!(entry & (UINT64_C(1) << 63)))
		fail("mapping not present");
	return entry & ((UINT64_C(1) << 55) - 1);
}

int main(void)
{
	const struct vkso_mm_data *mm_data;
	uint64_t parent_pfn, child_pfn = 0;
	int pipefd[2], status;
	pid_t child;

	errno = 0;
	mm_data = (const void *)getauxval(AT_VKSO_MM_DATA);
	if (!mm_data || errno)
		fail("auxv address");
	if (getauxval(AT_SYSINFO_EHDR))
		fail("legacy vdso auxv present");
	if (mm_data->abi_version != VKSO_MM_DATA_ABI_VERSION || mm_data->flags ||
	    mm_data->monotonic_offset.sec || mm_data->monotonic_offset.nsec)
		fail("mm data contents");
	check_mapping(mm_data);
	parent_pfn = mapping_pfn(mm_data);
	if (!parent_pfn)
		fail("parent pfn hidden");

	if (pipe(pipefd))
		fail("pipe");
	child = fork();
	if (child < 0)
		fail("fork");
	if (!child) {
		close(pipefd[0]);
		if (mm_data->abi_version != VKSO_MM_DATA_ABI_VERSION)
			_exit(2);
		child_pfn = mapping_pfn(mm_data);
		if (write(pipefd[1], &child_pfn, sizeof(child_pfn)) !=
		    sizeof(child_pfn))
			_exit(3);
		close(pipefd[1]);
		*(volatile uint32_t *)&mm_data->flags = 1;
		_exit(4);
	}
	close(pipefd[1]);
	if (read(pipefd[0], &child_pfn, sizeof(child_pfn)) != sizeof(child_pfn))
		fail("child pfn");
	close(pipefd[0]);
	if (waitpid(child, &status, 0) != child)
		fail("waitpid");
	if (!WIFSIGNALED(status) || WTERMSIG(status) != SIGSEGV)
		fail("mapping was writable");
	if (!child_pfn || child_pfn == parent_pfn)
		fail("fork shared physical page");

	printf("auxv_mm_data=%p\n", (const void *)mm_data);
	puts("mm_data_layout=pass");
	puts("mm_data_mapping=r--/nx");
	printf("per_mm_pages=pass parent_pfn=%llu child_pfn=%llu\n",
	       (unsigned long long)parent_pfn,
	       (unsigned long long)child_pfn);
	puts("m05_status=pass");
	return 0;
}
