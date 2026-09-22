#define _POSIX_C_SOURCE 200809L
#include <inttypes.h>
#include <stdio.h>
#include <time.h>
/* Shell-stage observer. Its process overhead is retained, not subtracted. */
int main(int argc, char **argv) {
    struct timespec t;
    if (argc != 4 || clock_gettime(CLOCK_MONOTONIC_RAW, &t)) return 2;
    uint64_t ns = (uint64_t)t.tv_sec * UINT64_C(1000000000) + t.tv_nsec;
    FILE *out = fopen(argv[1], "a");
    if (!out) { perror(argv[1]); return 2; }
    int fail = fprintf(out, "event\t%s\t%s\t%" PRIu64 "\n", argv[2], argv[3], ns) < 0;
    return fclose(out) || fail ? 2 : 0;
}
