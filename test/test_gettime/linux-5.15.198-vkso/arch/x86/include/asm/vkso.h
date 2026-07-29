/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _ASM_X86_VKSO_H
#define _ASM_X86_VKSO_H

struct mm_struct;

void vkso_init_context(struct mm_struct *mm);
int vkso_dup_mmap(struct mm_struct *oldmm, struct mm_struct *mm);
void vkso_destroy_context(struct mm_struct *mm);

#endif /* _ASM_X86_VKSO_H */
