// SPDX-License-Identifier: GPL-2.0
/* Test-only observation of the calling process's current MM_data page. */
#include <linux/debugfs.h>
#include <linux/mm.h>
#include <linux/module.h>
#include <linux/sched.h>
#include <linux/seq_file.h>

static struct dentry *entry;
static unsigned long pfn;
module_param(pfn, ulong, 0600);

static int refs_show(struct seq_file *out, void *unused)
{
	struct mm_struct *mm = current->mm;
	struct page *page;

	mmap_read_lock(mm);
	page = pfn && pfn_valid(pfn) ? pfn_to_page(pfn) :
		mm->context.vkso_mm_page;
	if (page)
		seq_printf(out, "%lu %d %d\n", page_to_pfn(page),
			   page_count(page), page_mapcount(page));
	mmap_read_unlock(mm);
	return 0;
}
DEFINE_SHOW_ATTRIBUTE(refs);

static int __init refs_init(void)
{
	entry = debugfs_create_file("vkso_mm_refs", 0400, NULL, NULL, &refs_fops);
	return PTR_ERR_OR_ZERO(entry);
}

static void __exit refs_exit(void)
{
	debugfs_remove(entry);
}
module_init(refs_init);
module_exit(refs_exit);
MODULE_LICENSE("GPL");
