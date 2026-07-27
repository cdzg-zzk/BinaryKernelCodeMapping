/* SPDX-License-Identifier: GPL-2.0 */

/*
 * Private userspace entry veneers embedded directly in libkernel.so.
 *
 * Shared core text remains backed by kernel pages.  This page is ordinary
 * DSO-owned RX text so it can inject per-process addresses without changing
 * the shared kernel ABI.  The clock_gettime veneer mirrors the core's branch
 * order and tail-jumps to its existing specialized readers.  This removes one
 * shared-core dispatch hop and only prepares dependencies used by the selected
 * reader.  make_dll resolves every transfer locally, so no PLT/GOT remains on
 * the hot path.
 */

	.section .vkso.user.text, "ax", @progbits
	.p2align 4
	.globl __vkso_clock_gettime
	.type __vkso_clock_gettime, @function
__vkso_clock_gettime:
	movq	%rsi, %rdx
	movl	%edi, %esi
	testl	%esi, %esi
	jne	.Lclock_not_realtime
	leaq	vkso_user_context(%rip), %rcx
	jmp	vkso_clock_gettime_realtime

.Lclock_not_realtime:
	movq	vkso_user_mm_data(%rip), %rdi
	cmpl	$1, %esi
	jne	.Lclock_not_monotonic
	leaq	vkso_user_context(%rip), %rcx
	jmp	vkso_clock_gettime_monotonic

.Lclock_not_monotonic:
	leal	-5(%rsi), %eax
	cmpl	$1, %eax
	jbe	.Lclock_coarse
	leaq	vkso_user_context(%rip), %rcx
	jmp	vkso_clock_gettime_other

.Lclock_coarse:
	jmp	vkso_clock_gettime_coarse
	.size __vkso_clock_gettime, .-__vkso_clock_gettime

	.p2align 4
	.globl __vkso_clock_getres
	.type __vkso_clock_getres, @function
__vkso_clock_getres:
	leaq	vkso_user_context(%rip), %rdx
	jmp	vkso_clock_getres_core
	.size __vkso_clock_getres, .-__vkso_clock_getres

	.p2align 4
	.globl __vkso_gettimeofday
	.type __vkso_gettimeofday, @function
__vkso_gettimeofday:
	leaq	vkso_user_context(%rip), %rdx
	jmp	vkso_gettimeofday_core
	.size __vkso_gettimeofday, .-__vkso_gettimeofday

	/*
	 * Bind once after reading AT_VKSO_MM_DATA.  A NULL first argument is the
	 * optimized root-time-namespace representation.  The other arguments
	 * are address-space-correct PVClock/Hyper-V aliases when available.
	 */
	.p2align 4
	.globl __vkso_bind_context
	.type __vkso_bind_context, @function
__vkso_bind_context:
	movq	%rdi, vkso_user_mm_data(%rip)
	movq	%rsi, vkso_user_context(%rip)
	movq	%rdx, vkso_user_context+8(%rip)
	xorl	%eax, %eax
	ret
	.size __vkso_bind_context, .-__vkso_bind_context

	.section .vkso.user.data, "aw", @progbits
	.p2align 3
	.type vkso_user_mm_data, @object
vkso_user_mm_data:
	.quad 0
	.size vkso_user_mm_data, .-vkso_user_mm_data

	.p2align 3
	.type vkso_user_context, @object
vkso_user_context:
	.quad 0			/* pvclock_page */
	.quad 0			/* hvclock_page */
	.long 1		/* VKSO_FALLBACK_SYSCALL */
	.long 0
	.size vkso_user_context, .-vkso_user_context

	.section .note.GNU-stack, "", @progbits
