/* Unapplied addition to make_dll/shim.c, compiled only during proposal review.
 * Unique entries prevent an ordinary global memcpy symbol from bypassing the
 * stack-ABI bridge. The explicit libc handle identifies the provider called
 * behind that bridge; no REP-equivalence claim is made.
 */
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
