// SPDX-License-Identifier: GPL-2.0
/*
 * lkm_locate: verify LKM relocation/addressing rules with an internal ctx
 * wrapper while keeping exported API unchanged.
 */

 #include <linux/errno.h>
 #include <linux/init.h>
 #include <linux/kernel.h>
 #include <linux/module.h>
 #include <linux/slab.h>
 #include <linux/string.h>
 
 /* [2] Global initialized variable (.data) */
 int ext_global_data = 0x1111;
 
 /* [3] Global uninitialized variable (.bss) */
 int ext_global_bss;
 
 extern int _printk(const char *fmt, ...);
 
 /* Keep these TU-local symbols static and pinned as distinct rodata objects. */
 static const int static_rodata = 0x2222;
 static const int static_array[4] = {
     0x10, 0x20, 0x30, 0x40
 };
 static const char my_fmt_str[] =
     "GOT Test -> BSS:%d, DATA:0x%x, RODATA:0x%x, ARR[%d]:0x%x\n";
 static const short dmin_data[] = {
     1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,
     385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577
 };
 
 struct lkm_locate_table_entry {
     int bias;
     int (*func)(int x);
 };

static noinline int lkm_locate_table_func_add(int x)
{
    return x + static_array[0];
}

static noinline int lkm_locate_table_func_sub(int x)
{
    return x - static_array[1];
}


 struct lkm_locate_ctx {
     void *(*kmalloc_fn)(size_t size, gfp_t flags);
     void (*kfree_fn)(const void *objp);
     int (*kprint_fn)(const char *fmt, ...);
 
     int *p_data;
     int *p_bss;
     const int *p_rodata;
     const int *p_array;
     const char *p_fmt;
     const short *p_dmin;
 };
 
 static volatile int lkm_locate_sink;
 
 /*
  * Keep ctx in .data with explicit pointer initializers so builder can
  * collect stable data relocations (including shim targets) at -O2.
  */
 static volatile struct lkm_locate_ctx lkm_locate_ctx_default = {
// static struct lkm_locate_ctx lkm_locate_ctx_default = {
     .kmalloc_fn = __kmalloc,
     .kfree_fn = kfree,
     .kprint_fn = _printk,
     .p_data = &ext_global_data,
     .p_bss = &ext_global_bss,
     .p_rodata = &static_rodata,
     .p_array = static_array,
     .p_fmt = my_fmt_str,
     .p_dmin = dmin_data,
 };

noinline int lkm_locate_test_all_pseudo_got(int x)
{
    int sum = 0;
    int arr_idx;
    char *dst;

    /* 直接通过结构体变量调用内存分配函数 */
    dst = lkm_locate_ctx_default.kmalloc_fn(32, GFP_KERNEL);
    if (!dst)
        return -ENOMEM;

    /* 直接通过结构体变量访问数据指针 */
    *lkm_locate_ctx_default.p_bss = x;
    *lkm_locate_ctx_default.p_data += 1;

    arr_idx = x % 4;

    sum += *lkm_locate_ctx_default.p_bss;
    sum += *lkm_locate_ctx_default.p_data;
    sum += *lkm_locate_ctx_default.p_rodata;
    sum += lkm_locate_ctx_default.p_array[arr_idx];
    sum += lkm_locate_ctx_default.p_dmin[arr_idx % 30];

    /* 直接通过结构体变量调用打印函数并传入对应格式和参数 */
    lkm_locate_ctx_default.kprint_fn(
            lkm_locate_ctx_default.p_fmt,
            *lkm_locate_ctx_default.p_bss,
            *lkm_locate_ctx_default.p_data,
            *lkm_locate_ctx_default.p_rodata,
            arr_idx,
            lkm_locate_ctx_default.p_array[arr_idx]);

    /* 直接通过结构体变量调用释放函数 */
    lkm_locate_ctx_default.kfree_fn(dst);

    return sum;
}
EXPORT_SYMBOL(lkm_locate_test_all_pseudo_got);

/*
 * Keep the table separate from ctx and force an explicit RIP-relative LEA
 * before indexed field access.
 */
static struct lkm_locate_table_entry lkm_locate_config_table[] __used = {
// static const struct lkm_locate_table_entry lkm_locate_config_table[] __used = {
    { .bias = 0x10, .func = lkm_locate_table_func_add },
    { .bias = 0x20, .func = lkm_locate_table_func_sub },
};

noinline int lkm_locate_test_table(int selector)
{
    volatile struct lkm_locate_table_entry *base;
    const volatile struct lkm_locate_table_entry *entry;
    int index;

    index = selector & 1;

    asm volatile(
        "lea lkm_locate_config_table(%%rip), %0"
        : "=r"(base)
    );

    entry = &base[index];

    return entry->func(selector + entry->bias);

}
EXPORT_SYMBOL(lkm_locate_test_table);
 static int __init lkm_locate_init(void)
 {
     lkm_locate_sink = lkm_locate_test_all_pseudo_got(42);
     lkm_locate_sink += lkm_locate_test_table(1);
     return 0;
 }
 
 static void __exit lkm_locate_exit(void)
 {
     lkm_locate_sink = 0;
 }
 
 module_init(lkm_locate_init);
 module_exit(lkm_locate_exit);
 
 MODULE_LICENSE("GPL");
 MODULE_DESCRIPTION("LKM relocation/addressing probe with direct variable access");
