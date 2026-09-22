// SPDX-License-Identifier: GPL-2.0
/* Read-only mapping observer for the controlled source-admission experiment. */
#include <linux/module.h>
#include <linux/debugfs.h>
#include <linux/seq_file.h>
#include <linux/uaccess.h>
#include <asm/pgtable.h>
static struct dentry *directory;
static unsigned long address;
static ssize_t set_address(struct file *f, const char __user *buffer,
                           size_t length, loff_t *offset)
{
    unsigned long value;
    int error = kstrtoul_from_user(buffer, length, 0, &value);
    if (error) return error;
    WRITE_ONCE(address, value);
    return length;
}
static int pages_show(struct seq_file *stream, void *unused)
{
    unsigned long target = READ_ONCE(address), pfn;
    unsigned int level;
    pte_t *entry = lookup_address(target, &level);
    u64 flags;
    if (!entry) return -EFAULT;
    flags = pte_val(READ_ONCE(*entry));
    if (!(flags & _PAGE_PRESENT)) return -EFAULT;
    if (level == PG_LEVEL_4K) pfn = pte_pfn(*entry);
    else if (level == PG_LEVEL_2M)
        pfn = pmd_pfn(*(pmd_t *)entry) + ((target & ~PMD_MASK) >> PAGE_SHIFT);
    else if (level == PG_LEVEL_1G)
        pfn = pud_pfn(*(pud_t *)entry) + ((target & ~PUD_MASK) >> PAGE_SHIFT);
    else return -EINVAL;
    seq_puts(stream, "kernel_vaddr,pfn,level,leaf_flags,writable,executable,user\n");
    seq_printf(stream, "0x%lx,%lu,%u,0x%llx,%u,%u,%u\n", target, pfn, level,
               flags, !!(flags & _PAGE_RW), !(flags & _PAGE_NX), !!(flags & _PAGE_USER));
    return 0;
}
DEFINE_SHOW_ATTRIBUTE(pages);
static const struct file_operations control_ops = {
    .owner = THIS_MODULE, .write = set_address, .llseek = no_llseek,
};
static int __init observer_init(void)
{
    directory = debugfs_create_dir("vkso_kernel_reader", NULL);
    if (IS_ERR(directory)) return PTR_ERR(directory);
    debugfs_create_file("page_addresses", 0200, directory, NULL, &control_ops);
    debugfs_create_file("pages", 0400, directory, NULL, &pages_fops);
    return 0;
}
static void __exit observer_exit(void) { debugfs_remove_recursive(directory); }
module_init(observer_init);
module_exit(observer_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Read-only source mapping permission observer");
