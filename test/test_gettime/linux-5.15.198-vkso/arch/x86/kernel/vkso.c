// SPDX-License-Identifier: GPL-2.0

#include <linux/err.h>
#include <linux/binfmts.h>
#include <linux/mm.h>
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

static union vkso_mm_page vkso_root_mm_data __page_aligned_data = {
	.data.abi_version = VKSO_MM_DATA_ABI_VERSION,
};

static struct page *vkso_namespace_page(struct time_namespace *ns)
{
#ifdef CONFIG_TIME_NS
	if (ns != &init_time_ns)
		return ns->vkso_page;
#endif
	return virt_to_page(&vkso_root_mm_data);
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
	get_page(page);
	mm->context.vkso_mm_page = page;
	mm->context.vkso_mm_kdata = page_address(page);
	mm->context.vkso_mm_data = (void __user *)addr;
	return 0;
}

void vkso_init_context(struct mm_struct *mm)
{
	mm->context.vkso_mm_page = NULL;
	mm->context.vkso_mm_kdata = NULL;
	mm->context.vkso_mm_data = NULL;
}

int vkso_dup_mmap(struct mm_struct *oldmm, struct mm_struct *mm)
{
	if (!oldmm->context.vkso_mm_page)
		return 0;
	return vkso_install_mm_mapping(mm,
		(unsigned long)oldmm->context.vkso_mm_data,
		oldmm->context.vkso_mm_page);
}

void vkso_destroy_context(struct mm_struct *mm)
{
	struct page *page = mm->context.vkso_mm_page;

	mm->context.vkso_mm_page = NULL;
	mm->context.vkso_mm_kdata = NULL;
	mm->context.vkso_mm_data = NULL;
	if (page)
		put_page(page);
}

void vkso_time_join_namespace(struct task_struct *task,
			      struct time_namespace *ns)
{
	struct mm_struct *mm = task->mm;
	struct page *page = vkso_namespace_page(ns), *old;
	struct vm_area_struct *vma;
	unsigned long addr;

	if (!mm || !mm->context.vkso_mm_page)
		return;
	/* Serialize backing changes against faults, including remote mm readers. */
	mmap_write_lock(mm);
	old = mm->context.vkso_mm_page;
	get_page(page);
	mm->context.vkso_mm_page = page;
	mm->context.vkso_mm_kdata = page_address(page);
	addr = (unsigned long)mm->context.vkso_mm_data;
	vma = find_vma(mm, addr);
	if (vma && vma_is_special_mapping(vma, &vkso_mm_mapping))
		zap_page_range(vma, vma->vm_start, PAGE_SIZE);
	mmap_write_unlock(mm);
	put_page(old);
}

int arch_setup_additional_pages(struct linux_binprm *bprm, int uses_interp)
{
	struct mm_struct *mm = current->mm;
	struct page *page = vkso_namespace_page(current->nsproxy->time_ns);
	unsigned long addr;
	int ret;

	(void)bprm;
	(void)uses_interp;
	if (mmap_write_lock_killable(mm))
		return -EINTR;
	addr = get_unmapped_area(NULL, 0, PAGE_SIZE, 0, 0);
	if (IS_ERR_VALUE(addr)) {
		ret = addr;
		goto out;
	}
	ret = vkso_install_mm_mapping(mm, addr, page);
out:
	mmap_write_unlock(mm);
	return ret;
}
