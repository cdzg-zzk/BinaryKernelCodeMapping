#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

typedef uint32_t (*xxh32_func)(const void *input, size_t length, uint32_t seed);

struct target_spec {
    const char *name;
    const char *path_env;
    const char *default_path;
    const char *symbol;
};

static const struct target_spec targets[] = {
    {
        .name = "stub",
        .path_env = "STUB_DSO",
        .default_path = "../tmp/libzzk_xxh32_lkm.so",
        .symbol = "zzk_xxh32",
    },
    {
        .name = "native",
        .path_env = "NATIVE_DSO",
        .default_path = "../so/libclone_xxh32.so",
        .symbol = "clone_xxh32",
    },
};

static volatile uint32_t result_sink;

static void usage(const char *prog)
{
    fprintf(stderr,
            "Usage: %s -t <stub|native> [-s pte-cold] -o <trace.log>\n"
            "\n"
            "This tool captures one controlled PTE-cold minor fault:\n"
            "  warm up once -> madvise target function page -> trace one call.\n",
            prog);
}

static const struct target_spec *find_target(const char *name)
{
    for (size_t i = 0; i < sizeof(targets) / sizeof(targets[0]); i++) {
        if (strcmp(name, targets[i].name) == 0) {
            return &targets[i];
        }
    }
    return NULL;
}

static int write_file(const char *path, const char *value)
{
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        fprintf(stderr, "open(%s): %s\n", path, strerror(errno));
        return -1;
    }
    ssize_t len = (ssize_t)strlen(value);
    if (write(fd, value, (size_t)len) != len) {
        fprintf(stderr, "write(%s): %s\n", path, strerror(errno));
        close(fd);
        return -1;
    }
    close(fd);
    return 0;
}

static int append_file_to_output(const char *src, const char *dst)
{
    int in = open(src, O_RDONLY | O_CLOEXEC);
    if (in < 0) {
        fprintf(stderr, "open(%s): %s\n", src, strerror(errno));
        return -1;
    }
    int out = open(dst, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    if (out < 0) {
        fprintf(stderr, "open(%s): %s\n", dst, strerror(errno));
        close(in);
        return -1;
    }

    char buf[8192];
    for (;;) {
        ssize_t n = read(in, buf, sizeof(buf));
        if (n < 0) {
            fprintf(stderr, "read(%s): %s\n", src, strerror(errno));
            close(in);
            close(out);
            return -1;
        }
        if (n == 0) {
            break;
        }
        if (write(out, buf, (size_t)n) != n) {
            fprintf(stderr, "write(%s): %s\n", dst, strerror(errno));
            close(in);
            close(out);
            return -1;
        }
    }

    close(in);
    close(out);
    return 0;
}

static void evict_func_page(void *func_ptr)
{
    long page_size = sysconf(_SC_PAGESIZE);
    void *aligned = (void *)((uintptr_t)func_ptr & ~((uintptr_t)page_size - 1));

    if (madvise(aligned, (size_t)page_size, MADV_DONTNEED) != 0) {
        perror("madvise(MADV_DONTNEED)");
    }
}

static void prepare_pte_cold(xxh32_func func, const void *input, size_t length,
                             uint32_t seed)
{
    result_sink ^= func(input, length, seed);
    evict_func_page((void *)func);
}

static int configure_ftrace(void)
{
    char pid[32];

    snprintf(pid, sizeof(pid), "%d", getpid());
    if (write_file("/sys/kernel/tracing/tracing_on", "0") != 0) {
        return -1;
    }
    write_file("/sys/kernel/tracing/set_ftrace_pid", "\n");
    write_file("/sys/kernel/tracing/set_graph_function", "\n");
    if (write_file("/sys/kernel/tracing/current_tracer", "nop") != 0) {
        return -1;
    }
    if (write_file("/sys/kernel/tracing/trace", "\n") != 0) {
        return -1;
    }
    if (write_file("/sys/kernel/tracing/current_tracer", "function_graph") != 0) {
        return -1;
    }
    if (write_file("/sys/kernel/tracing/set_ftrace_pid", pid) != 0) {
        return -1;
    }
    if (write_file("/sys/kernel/tracing/set_graph_function", "handle_mm_fault") != 0) {
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const struct target_spec *target = NULL;
    const char *output_path = NULL;

    int opt;
    while ((opt = getopt(argc, argv, "t:s:o:h")) != -1) {
        switch (opt) {
        case 't':
            target = find_target(optarg);
            break;
        case 's':
            if (strcmp(optarg, "pte-cold") != 0 && strcmp(optarg, "warm") != 0) {
                fprintf(stderr, "benchmark_ftrace only supports -s pte-cold\n");
                return 1;
            }
            break;
        case 'o':
            output_path = optarg;
            break;
        case 'h':
        default:
            usage(argv[0]);
            return opt == 'h' ? 0 : 1;
        }
    }

    if (!target || !output_path) {
        usage(argv[0]);
        return 1;
    }

    const char *path = getenv(target->path_env);
    if (!path || path[0] == '\0') {
        path = target->default_path;
    }

    void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "dlopen(%s): %s\n", path, dlerror());
        return 1;
    }

    dlerror();
    xxh32_func func = (xxh32_func)dlsym(handle, target->symbol);
    const char *dlsym_error = dlerror();
    if (dlsym_error) {
        fprintf(stderr, "dlsym(%s): %s\n", target->symbol, dlsym_error);
        dlclose(handle);
        return 1;
    }

    unsigned char input[5] = {0};
    uint32_t seed = 0x1234;

    prepare_pte_cold(func, input, sizeof(input), seed);

    if (configure_ftrace() != 0) {
        dlclose(handle);
        return 1;
    }

    if (write_file("/sys/kernel/tracing/tracing_on", "1") != 0) {
        dlclose(handle);
        return 1;
    }
    result_sink ^= func(input, sizeof(input), seed);
    write_file("/sys/kernel/tracing/tracing_on", "0");

    if (append_file_to_output("/sys/kernel/tracing/trace", output_path) != 0) {
        dlclose(handle);
        return 1;
    }

    write_file("/sys/kernel/tracing/set_graph_function", "\n");
    write_file("/sys/kernel/tracing/set_ftrace_pid", "\n");
    write_file("/sys/kernel/tracing/current_tracer", "nop");
    dlclose(handle);
    return 0;
}
