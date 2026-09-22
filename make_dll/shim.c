#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>

/*
 * User-space shim implementations for kernel-only APIs.
 * Most functions listed in shim.txt are provided here so build_PIC_so.py can
 * link dependent modules against libshim.so instead of kernel space.  The
 * __x86_indirect_thunk_* entries are special: the builder emits those direct-
 * jump thunks inside libkernel.so at their original relative addresses.
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
void* kvmalloc(size_t size, gfp_t flags) {
    (void)flags;
    return malloc(size);
}

__attribute__((force_align_arg_pointer))
void kfree(const void* ptr) {
    free((void*)ptr);
}

__attribute__((force_align_arg_pointer))
void kvfree(const void* ptr) {
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

__attribute__((force_align_arg_pointer))
void* memcpy(void* dst, const void* src, size_t n) {
    return __builtin_memcpy(dst, src, n);
}

__attribute__((force_align_arg_pointer))
void* memmove(void* dst, const void* src, size_t n) {
    return __builtin_memmove(dst, src, n);
}

__attribute__((force_align_arg_pointer))
void* memset(void* dst, int c, size_t n) {
    return __builtin_memset(dst, c, n);
}

void kernel_fpu_begin_mask(unsigned int kfpu_mask);
void kernel_fpu_end(void);

__asm__(
    ".globl kernel_fpu_begin_mask\n"
    ".type kernel_fpu_begin_mask, @function\n"
    "kernel_fpu_begin_mask:\n"
    "endbr64\n"
    "ret\n"
    ".size kernel_fpu_begin_mask, .-kernel_fpu_begin_mask\n"
    ".globl kernel_fpu_end\n"
    ".type kernel_fpu_end, @function\n"
    "kernel_fpu_end:\n"
    "endbr64\n"
    "ret\n"
    ".size kernel_fpu_end, .-kernel_fpu_end\n"
);

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

/* Explicit data-slot targets with kernel-to-user stack realignment. */
#include <dlfcn.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

typedef void *(*vkso_copy_fn)(void *, const void *, size_t);
typedef void *(*vkso_set_fn)(void *, int, size_t);
static void *vkso_memory_libc_handle;
static vkso_copy_fn vkso_memory_libc_copy;
static vkso_copy_fn vkso_memory_libc_move;
static vkso_set_fn vkso_memory_libc_set;

static void *vkso_memory_libc_symbol(const char *name)
{
    dlerror();
    void *symbol = dlsym(vkso_memory_libc_handle, name);
    const char *error = dlerror();
    if (error || !symbol) {
        fprintf(stderr, "vkso memory ABI bridge: libc %s: %s\n", name,
                error ? error : "null entry");
        abort();
    }
    return symbol;
}

__attribute__((constructor))
static void vkso_memory_libc_open(void)
{
    vkso_memory_libc_handle = dlopen("libc.so.6", RTLD_NOW | RTLD_LOCAL);
    if (!vkso_memory_libc_handle) {
        fprintf(stderr, "vkso memory ABI bridge: %s\n", dlerror());
        abort();
    }
    /* POSIX dlsym function-pointer conversions on the selected Linux/x86 ABI. */
    vkso_memory_libc_copy = (vkso_copy_fn)vkso_memory_libc_symbol("memcpy");
    vkso_memory_libc_move = (vkso_copy_fn)vkso_memory_libc_symbol("memmove");
    vkso_memory_libc_set = (vkso_set_fn)vkso_memory_libc_symbol("memset");
}

__attribute__((destructor))
static void vkso_memory_libc_close(void)
{
    if (vkso_memory_libc_handle)
        dlclose(vkso_memory_libc_handle);
}

__attribute__((force_align_arg_pointer))
void *vkso_abi_memcpy(void *destination, const void *source, size_t size)
{
    return vkso_memory_libc_copy(destination, source, size);
}

__attribute__((force_align_arg_pointer))
void *vkso_abi_memmove(void *destination, const void *source, size_t size)
{
    return vkso_memory_libc_move(destination, source, size);
}

__attribute__((force_align_arg_pointer))
void *vkso_abi_memset(void *destination, int value, size_t size)
{
    return vkso_memory_libc_set(destination, value, size);
}

/* Observation-only accessor; the three call paths above do not collect data. */
void *vkso_abi_memory_target(unsigned int index)
{
    if (index == 0) return (void *)vkso_memory_libc_copy;
    if (index == 1) return (void *)vkso_memory_libc_move;
    if (index == 2) return (void *)vkso_memory_libc_set;
    return NULL;
}
