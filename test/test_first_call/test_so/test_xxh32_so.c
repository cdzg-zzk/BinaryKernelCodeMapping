#include <dlfcn.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint32_t (*xxh32_fn_t)(const void *input, size_t length, uint32_t seed);

static inline uint32_t rotl32(uint32_t x, int r) {
    return (x << r) | (x >> (32 - r));
}

static inline uint32_t read32le(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static inline uint32_t xxh32_round(uint32_t acc, uint32_t input) {
    const uint32_t PRIME2 = 0x85EBCA77U;
    const uint32_t PRIME1 = 0x9E3779B1U;
    acc += input * PRIME2;
    acc = rotl32(acc, 13);
    acc *= PRIME1;
    return acc;
}

static uint32_t xxh32_ref(const void *input, size_t length, uint32_t seed) {
    const uint32_t PRIME1 = 0x9E3779B1U;
    const uint32_t PRIME2 = 0x85EBCA77U;
    const uint32_t PRIME3 = 0xC2B2AE3DU;
    const uint32_t PRIME4 = 0x27D4EB2FU;
    const uint32_t PRIME5 = 0x165667B1U;

    const uint8_t *p = (const uint8_t *)input;
    const uint8_t *const bEnd = p + length;
    uint32_t h32;

    if (length >= 16) {
        const uint8_t *const limit = bEnd - 16;
        uint32_t v1 = seed + PRIME1 + PRIME2;
        uint32_t v2 = seed + PRIME2;
        uint32_t v3 = seed + 0;
        uint32_t v4 = seed - PRIME1;

        do {
            v1 = xxh32_round(v1, read32le(p)); p += 4;
            v2 = xxh32_round(v2, read32le(p)); p += 4;
            v3 = xxh32_round(v3, read32le(p)); p += 4;
            v4 = xxh32_round(v4, read32le(p)); p += 4;
        } while (p <= limit);

        h32 = rotl32(v1, 1) + rotl32(v2, 7) + rotl32(v3, 12) + rotl32(v4, 18);
    } else {
        h32 = seed + PRIME5;
    }

    h32 += (uint32_t)length;

    while ((size_t)(bEnd - p) >= 4) {
        h32 += read32le(p) * PRIME3;
        h32 = rotl32(h32, 17) * PRIME4;
        p += 4;
    }

    while (p < bEnd) {
        h32 += (*p) * PRIME5;
        h32 = rotl32(h32, 11) * PRIME1;
        ++p;
    }

    h32 ^= h32 >> 15;
    h32 *= PRIME2;
    h32 ^= h32 >> 13;
    h32 *= PRIME3;
    h32 ^= h32 >> 16;
    return h32;
}

struct test_case {
    const char *name;
    const uint8_t *data;
    size_t len;
    uint32_t seed;
};

int main(void) {
    const char *so_kernel = "/home/zzk/BinaryKernelCodeMapping/test/test_first_call/matrix_bench/zzk_xxh32_lkm.so";
    const char *so_clone = "/home/zzk/BinaryKernelCodeMapping/test/test_first_call/matrix_bench/libclone_xxh32.so";

    void *h_kernel = dlopen(so_kernel, RTLD_NOW | RTLD_LOCAL);
    if (!h_kernel) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", so_kernel, dlerror());
        return 1;
    }
    void *h_clone = dlopen(so_clone, RTLD_NOW | RTLD_LOCAL);
    if (!h_clone) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", so_clone, dlerror());
        dlclose(h_kernel);
        return 1;
    }

    dlerror();
    xxh32_fn_t zzk_xxh32 = (xxh32_fn_t)dlsym(h_kernel, "zzk_xxh32");
    const char *e1 = dlerror();
    xxh32_fn_t clone_xxh32 = (xxh32_fn_t)dlsym(h_clone, "clone_xxh32");
    const char *e2 = dlerror();

    if (e1 || !zzk_xxh32) {
        fprintf(stderr, "dlsym zzk_xxh32 failed: %s\n", e1 ? e1 : "unknown");
        dlclose(h_clone);
        dlclose(h_kernel);
        return 1;
    }
    if (e2 || !clone_xxh32) {
        fprintf(stderr, "dlsym clone_xxh32 failed: %s\n", e2 ? e2 : "unknown");
        dlclose(h_clone);
        dlclose(h_kernel);
        return 1;
    }

    static const uint8_t empty_data[] = "";
    static const uint8_t a_data[] = "a";
    static const uint8_t hello_data[] = "hello";
    static const uint8_t phrase_data[] = "The quick brown fox jumps over the lazy dog";
    static const uint8_t long_data[] =
        "0123456789abcdef"
        "fedcba9876543210"
        "kernel-user-clone-check";
    static const uint8_t bin_data[] = {0x00, 0x01, 0x02, 0x7f, 0x80, 0xfe, 0xff, 0x11, 0x22, 0x33, 0x44, 0x55, 0xaa, 0xbb, 0xcc, 0xdd, 0xee};

    const struct test_case cases[] = {
        {"empty_seed0", empty_data, 0, 0},
        {"a_seed0", a_data, 1, 0},
        {"hello_seed0", hello_data, 5, 0},
        {"hello_seed12345678", hello_data, 5, 0x12345678U},
        {"phrase_seed0", phrase_data, sizeof(phrase_data) - 1, 0},
        {"long_seeddeadbeef", long_data, sizeof(long_data) - 1, 0xdeadbeefU},
        {"binary_seedcafebabe", bin_data, sizeof(bin_data), 0xcafebabeU},
    };

    int failed = 0;
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        const struct test_case *tc = &cases[i];
        uint32_t expected = xxh32_ref(tc->data, tc->len, tc->seed);
        uint32_t r1 = zzk_xxh32(tc->data, tc->len, tc->seed);
        uint32_t r2 = clone_xxh32(tc->data, tc->len, tc->seed);

        if (r1 != expected || r2 != expected) {
            ++failed;
            printf("[FAIL] %s len=%zu seed=0x%08" PRIx32 " expected=0x%08" PRIx32 " zzk=0x%08" PRIx32 " clone=0x%08" PRIx32 "\n",
                   tc->name, tc->len, tc->seed, expected, r1, r2);
        } else {
            printf("[ OK ] %s => 0x%08" PRIx32 "\n", tc->name, expected);
        }
    }

    dlclose(h_clone);
    dlclose(h_kernel);

    if (failed) {
        printf("\nResult: %d case(s) failed.\n", failed);
        return 2;
    }

    printf("\nResult: all test cases passed.\n");
    return 0;
}
