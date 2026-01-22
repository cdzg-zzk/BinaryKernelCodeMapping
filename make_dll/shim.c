#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>

/*
 * User-space shim implementations for kernel-only APIs.
 * Functions listed in shim.txt are provided here so that build_PIC_so.py
 * can link dependent modules against libshim.so instead of kernel space.
 * This is a pragmatic stand-in: semantics are matched approximately using
 * libc/syscall equivalents; avoid putting privileged-only or unshimmable
 * symbols here.
 */

 /*
    __attribute__((force_align_arg_pointer))很重要，因为：
    - SysV 用户态 ABI 要求函数入口栈 16 字节对齐；调用指令会先减 8 字节，把 %rsp 从 16 变成 8，再进入
      被调函数。被调函数必须再减去 8 mod 16 的空间，让栈重新到 16 对齐。
    - 内核/模块代码常用 8 字节对齐（不保证 16），所以从模块函数调用用户态 ABI 的代码时，栈只剩 8 字节
      对齐。
    - libshim.so 的 _printk 按用户态 ABI 编译，序言用 movaps 保存 XMM 寄存器，要求 16 字节对齐；若调用
      者只给 8 字节对齐就会触发对齐异常。
    - 解决办法是让被调用方宽容（入口重对齐，比如 force_align_arg_pointer 或 -mstackrealign），或让调用
      方遵守 16 字节对齐。
 */
// gcc -shared -fPIC shim.c -o libshim.so
typedef unsigned long gfp_t;

struct timespec64 {
    long tv_sec;
    long tv_nsec;
};

__attribute__((force_align_arg_pointer))
static uint64_t timespec_to_ns(const struct timespec* ts) {
    return ((uint64_t)ts->tv_sec * 1000000000ull) + (uint64_t)ts->tv_nsec;
}

__attribute__((force_align_arg_pointer))
void* kmalloc(size_t size, gfp_t flags) {
    (void)flags;
    return malloc(size);
}

__attribute__((force_align_arg_pointer))
void* __kmalloc(size_t size, gfp_t flags) {
    (void)flags;
    return malloc(size);
}

__attribute__((force_align_arg_pointer))
void kfree(const void* ptr) {
    free((void*)ptr);
}

__attribute__((force_align_arg_pointer))
char* kstrdup(const char* s, gfp_t flags) {
    (void)flags;
    return s ? strdup(s) : NULL;
}

__attribute__((force_align_arg_pointer))
int printk(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    int n = vprintf(fmt, ap);
    va_end(ap);
    return n;
}

__attribute__((force_align_arg_pointer))
int _printk(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    int n = vprintf(fmt, ap);
    va_end(ap);
    return n;
}

__attribute__((force_align_arg_pointer))
int vprintk(const char* fmt, va_list ap) {
    return vprintf(fmt, ap);
}

void* memcpy(void* dst, const void* src, size_t n) {
    return __builtin_memcpy(dst, src, n);
}

__attribute__((force_align_arg_pointer))
int64_t ktime_get(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)timespec_to_ns(&ts);
}

__attribute__((force_align_arg_pointer))
uint64_t ktime_get_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return timespec_to_ns(&ts);
}

__attribute__((force_align_arg_pointer))
int ktime_get_real_ts64(struct timespec64* ts64) {
    if (!ts64) return -1;
    struct timespec ts;
    if (clock_gettime(CLOCK_REALTIME, &ts) != 0) {
        return -1;
    }
    ts64->tv_sec = ts.tv_sec;
    ts64->tv_nsec = ts.tv_nsec;
    return 0;
}

__attribute__((force_align_arg_pointer))
int do_gettimeofday(struct timeval* tv) {
    return gettimeofday(tv, NULL);
}
