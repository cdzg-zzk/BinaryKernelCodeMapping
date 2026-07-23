// SPDX-License-Identifier: GPL-2.0

#include <linux/err.h>
#include <linux/binfmts.h>
#include <linux/gfp.h>
#include <linux/mm.h>
#include <linux/string.h>
#include <linux/time_namespace.h>
#include <linux/vkso_time.h>

#include <asm/mmu.h>
#include <asm/vkso.h>

static vm_fault_t vkso_mm_fault(const struct vm_special_mapping *sm,
				struct vm_area_struct *vma,
				struct vm_fault *vmf)
{
	struct page *page = READ_ONCE(vma->vm_mm->context.vkso_mm_page);

	if (vmf->pgoff || !page)
		return VM_FAULT_SIGBUS;
	get_page(page);
	vmf->page = page;
	return 0;
}

static int vkso_mm_mremap(const struct vm_special_mapping *sm,
			  struct vm_area_struct *new_vma)
{
	return -EINVAL;
}

static const struct vm_special_mapping vkso_mm_mapping = {
	.name = "[vkso_mm_data]",
	.fault = vkso_mm_fault,
	.mremap = vkso_mm_mremap,
};

static struct page *vkso_alloc_mm_page(const struct page *source)
{
	struct page *page = alloc_page(GFP_KERNEL | __GFP_ZERO);
	union vkso_mm_page *data;

	if (!page)
		return NULL;
	data = page_address(page);
	if (source)
		memcpy(data, page_address(source), PAGE_SIZE);
	else
		data->data.abi_version = VKSO_MM_DATA_ABI_VERSION;
	return page;
}

static int vkso_install_mm_mapping(struct mm_struct *mm, unsigned long addr,
				   struct page *page)
{
	struct vm_area_struct *vma;

	vma = _install_special_mapping(mm, addr, PAGE_SIZE,
			VM_READ | VM_MAYREAD | VM_DONTDUMP | VM_DONTCOPY,
			&vkso_mm_mapping);
	if (IS_ERR(vma))
		return PTR_ERR(vma);
	mm->context.vkso_mm_page = page;
	mm->context.vkso_mm_data = (void __user *)addr;
	return 0;
}

void vkso_init_context(struct mm_struct *mm)
{
	mm->context.vkso_mm_page = NULL;
	mm->context.vkso_mm_data = NULL;
}

int vkso_dup_mmap(struct mm_struct *oldmm, struct mm_struct *mm)
{
	struct page *page;
	unsigned long addr;
	int ret;

	if (!oldmm->context.vkso_mm_page)
		return 0;
	addr = (unsigned long)oldmm->context.vkso_mm_data;
	page = vkso_alloc_mm_page(oldmm->context.vkso_mm_page);
	if (!page)
		return -ENOMEM;
	ret = vkso_install_mm_mapping(mm, addr, page);
	if (ret)
		put_page(page);
	return ret;
}

void vkso_destroy_context(struct mm_struct *mm)
{
	struct page *page = mm->context.vkso_mm_page;

	mm->context.vkso_mm_page = NULL;
	mm->context.vkso_mm_data = NULL;
	if (page)
		put_page(page);
}

const struct vkso_mm_data *vkso_time_mm_data(struct mm_struct *mm)
{
	struct page *page;

	if (!mm)
		return NULL;
	page = READ_ONCE(mm->context.vkso_mm_page);
	return page ? page_address(page) : NULL;
}

void vkso_time_update_mm_data(struct task_struct *task,
			      const struct timespec64 *monotonic_offset)
{
	struct mm_struct *mm = task->mm;
	union vkso_mm_page *data;
	struct page *page;

	if (!mm)
		return;
	page = READ_ONCE(mm->context.vkso_mm_page);
	if (!page)
		return;
	data = page_address(page);
	WRITE_ONCE(data->data.monotonic_offset.sec, monotonic_offset->tv_sec);
	WRITE_ONCE(data->data.monotonic_offset.nsec, monotonic_offset->tv_nsec);
}

int arch_setup_additional_pages(struct linux_binprm *bprm, int uses_interp)
{
	struct mm_struct *mm = current->mm;
	struct page *page;
	unsigned long addr;
	int ret;

	(void)bprm;
	(void)uses_interp;
	page = vkso_alloc_mm_page(NULL);
	if (!page)
		return -ENOMEM;
	if (mmap_write_lock_killable(mm)) {
		put_page(page);
		return -EINTR;
	}
	addr = get_unmapped_area(NULL, 0, PAGE_SIZE, 0, 0);
	if (IS_ERR_VALUE(addr)) {
		ret = addr;
		goto out;
	}
	ret = vkso_install_mm_mapping(mm, addr, page);
out:
	mmap_write_unlock(mm);
	if (ret) {
		put_page(page);
		return ret;
	}
#ifdef CONFIG_TIME_NS
	vkso_time_update_mm_data(current,
		&current->nsproxy->time_ns->offsets.monotonic);
#endif
	return 0;
}
