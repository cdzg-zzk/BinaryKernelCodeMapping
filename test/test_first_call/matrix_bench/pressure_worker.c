#define _GNU_SOURCE
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sched.h>
#include <unistd.h>

#define BLOCK (1024UL * 1024)
#define FILE_BYTES (1024UL * BLOCK)

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    cpu_set_t cpus; CPU_ZERO(&cpus); CPU_SET(0, &cpus);
    if (sched_setaffinity(0, sizeof(cpus), &cpus)) return 1;
    int fd = open(argv[1], O_CREAT | O_EXCL | O_RDWR, 0600);
    if (fd < 0) { perror("working set"); return 1; }
    unsigned char *buffer = malloc(BLOCK), *reservation = NULL;
    size_t reserved = 0;
    if (!buffer) return 1;
    for (size_t i = 0; i < BLOCK; i++) buffer[i] = (i * 17 + 31) % 251;
    for (size_t offset = 0; offset < FILE_BYTES; offset += BLOCK)
        if (write(fd, buffer, BLOCK) != BLOCK) { perror("write"); return 1; }
    if (fsync(fd)) return 1;
    setvbuf(stdout, NULL, _IOLBF, 0);
    printf("{\"event\":\"ready\",\"pid\":%d,\"cpu\":%d,\"file_bytes\":%lu}\n",
           getpid(), sched_getcpu(), FILE_BYTES);
    char command[128];
    while (fgets(command, sizeof(command), stdin)) {
        if (!strncmp(command, "ALLOC ", 6) && !reservation) {
            reserved = strtoull(command + 6, NULL, 10);
            reservation = mmap(NULL, reserved, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
            if (reservation == MAP_FAILED) { perror("mmap"); return 1; }
            if (madvise(reservation, reserved, MADV_NOHUGEPAGE)) return 1;
            memset(reservation, 0xa5, reserved);
            printf("{\"event\":\"allocated\",\"anonymous_bytes\":%zu}\n", reserved);
        } else if (!strcmp(command, "SCAN\n")) {
            uint64_t sum = 0;
            for (int pass = 0; pass < 2; pass++)
                for (size_t offset = 0; offset < FILE_BYTES; offset += BLOCK) {
                    if (pread(fd, buffer, BLOCK, offset) != BLOCK) { perror("pread"); return 1; }
                    for (size_t i = 0; i < BLOCK; i += 4096) sum += buffer[i];
                }
            struct rusage usage;
            if (getrusage(RUSAGE_SELF, &usage)) return 1;
            printf("{\"event\":\"scanned\",\"read_bytes\":%lu,\"checksum\":%llu,"
                   "\"inblock_total\":%ld,\"anonymous_bytes\":%zu}\n",
                   2 * FILE_BYTES, (unsigned long long)sum, usage.ru_inblock, reserved);
        } else if (!strcmp(command, "FREE\n") && reservation) {
            if (munmap(reservation, reserved)) return 1;
            reservation = NULL; reserved = 0;
            puts("{\"event\":\"freed\",\"anonymous_bytes\":0}");
        } else if (!strcmp(command, "QUIT\n")) break;
        else return 2;
    }
    if (reservation) munmap(reservation, reserved);
    free(buffer); close(fd); return 0;
}
