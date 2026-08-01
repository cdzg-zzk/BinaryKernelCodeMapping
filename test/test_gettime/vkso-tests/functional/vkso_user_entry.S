/* SPDX-License-Identifier: GPL-2.0 */

#include <asm/unistd_64.h>
#include <vkso/time.h>

/*
 * Private userspace entry veneers embedded directly in libkernel.so.
 *
 * Shared core text remains backed by kernel pages.  This page is ordinary
 * DSO-owned RX text so it can inject per-process addresses without changing
 * the shared kernel ABI. Clock IDs are classified once at this environment
 * boundary: native clocks go directly to the syscall failure adapter, while
 * hres/coarse clocks tail-jump into their shared reader. Only a provider
 * failure returns through vkso_user_context. make_dll resolves every transfer
 * locally, so no PLT/GOT remains on the hot path.
 */

	.section .vkso.user.text, "ax", @progbits
	.macro vkso_dispatch_clock hres, coarse, native
	cmpl	$VKSO_CLOCK_ID_MAX, %edi
	ja	\native
	movl	$VKSO_HRES_CLOCK_MASK, %eax
	btl	%edi, %eax
	jc	\hres
	movl	$VKSO_COARSE_CLOCK_MASK, %eax
	btl	%edi, %eax
	jc	\coarse
	/* Unclassified in-range clock IDs fall through to the native label. */
	.endm

	.p2align 4
	.globl __vkso_clock_gettime
	.type __vkso_clock_gettime, @function
__vkso_clock_gettime:
	vkso_dispatch_clock .Lclock_gettime_hres, \
		.Lclock_gettime_coarse, .Lclock_gettime_native
.Lclock_gettime_native:
	/* Also entered indirectly when a shared provider rejects its mode. */
vkso_user_clock_gettime_failure:
	movslq	%edi, %rdi
	movl	$__NR_clock_gettime, %eax
	syscall
	ret

.Lclock_gettime_hres:
	movq	vkso_user_mm_data(%rip), %rdx
	leaq	vkso_user_context(%rip), %rcx
	jmp	vkso_clock_gettime_hres

.Lclock_gettime_coarse:
	movq	vkso_user_mm_data(%rip), %rdx
	jmp	vkso_clock_gettime_coarse
	.size __vkso_clock_gettime, .-__vkso_clock_gettime
	.type vkso_user_clock_gettime_failure, @function
	.size vkso_user_clock_gettime_failure, \
		.Lclock_gettime_hres-vkso_user_clock_gettime_failure

	.p2align 4
	.globl __vkso_clock_getres
	.type __vkso_clock_getres, @function
__vkso_clock_getres:
	vkso_dispatch_clock .Lclock_getres_hres, \
		.Lclock_getres_coarse, .Lclock_getres_fallback
.Lclock_getres_fallback:
	movslq	%edi, %rdi
	movl	$__NR_clock_getres, %eax
	syscall
	ret

.Lclock_getres_hres:
	movq	%rsi, %rdi
	jmp	vkso_clock_getres_hres

.Lclock_getres_coarse:
	movq	%rsi, %rdi
	jmp	vkso_clock_getres_coarse
	.size __vkso_clock_getres, .-__vkso_clock_getres

	.p2align 4
	.globl __vkso_gettimeofday
	.type __vkso_gettimeofday, @function
__vkso_gettimeofday:
	leaq	vkso_user_context(%rip), %rdx
	jmp	vkso_gettimeofday_core
	.size __vkso_gettimeofday, .-__vkso_gettimeofday

	.type vkso_user_gettimeofday_failure, @function
vkso_user_gettimeofday_failure:
	movl	$__NR_gettimeofday, %eax
	syscall
	ret
	.size vkso_user_gettimeofday_failure, \
		.-vkso_user_gettimeofday_failure

	/*
	 * Bind once after reading AT_VKSO_MM_DATA.  The per-MM page remains
	 * valid across time-namespace changes; root namespace offsets are
	 * represented by its zero clock mask.  The other arguments are
	 * address-space-correct PVClock/Hyper-V aliases when available.
	 */
	.p2align 4
	.globl __vkso_bind_context
	.type __vkso_bind_context, @function
__vkso_bind_context:
	movq	%rdi, vkso_user_mm_data(%rip)
	movq	%rsi, vkso_user_context(%rip)
	movq	%rdx, vkso_user_context+8(%rip)
	leaq	vkso_user_clock_gettime_failure(%rip), %rax
	movq	%rax, vkso_user_context+16(%rip)
	leaq	vkso_user_gettimeofday_failure(%rip), %rax
	movq	%rax, vkso_user_context+24(%rip)
	xorl	%eax, %eax
	ret
	.size __vkso_bind_context, .-__vkso_bind_context

	.p2align 4
	.globl __vkso_shared_data
	.type __vkso_shared_data, @function
__vkso_shared_data:
	leaq	vkso_shared_page(%rip), %rax
	ret
	.size __vkso_shared_data, .-__vkso_shared_data

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
	.quad 0			/* clock_gettime_failure */
	.quad 0			/* gettimeofday_failure */
	.size vkso_user_context, .-vkso_user_context

	.section .note.GNU-stack, "", @progbits
