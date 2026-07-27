/* SPDX-License-Identifier: GPL-2.0 */

#include <asm/unistd_64.h>

/* x86-64 UAPI clock IDs; the shared C core has matching static assertions. */
#define VKSO_CLOCK_REALTIME		0
#define VKSO_CLOCK_MONOTONIC		1
#define VKSO_CLOCK_MONOTONIC_RAW	4
#define VKSO_CLOCK_REALTIME_COARSE	5
#define VKSO_CLOCK_MONOTONIC_COARSE	6
#define VKSO_CLOCK_BOOTTIME		7
#define VKSO_CLOCK_TAI			11
#define VKSO_HRES_CLOCK_MASK \
	((1 << VKSO_CLOCK_REALTIME) | (1 << VKSO_CLOCK_MONOTONIC) | \
	 (1 << VKSO_CLOCK_MONOTONIC_RAW) | (1 << VKSO_CLOCK_BOOTTIME) | \
	 (1 << VKSO_CLOCK_TAI))
#define VKSO_COARSE_CLOCK_MASK \
	((1 << VKSO_CLOCK_REALTIME_COARSE) | \
	 (1 << VKSO_CLOCK_MONOTONIC_COARSE))

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
	cmpl	$VKSO_CLOCK_MONOTONIC, %esi
	jne	.Lclock_not_monotonic
	movq	vkso_user_mm_data(%rip), %rdi
	leaq	vkso_user_context(%rip), %rcx
	jmp	vkso_clock_gettime_monotonic

.Lclock_not_monotonic:
	cmpl	$VKSO_CLOCK_REALTIME_COARSE, %esi
	je	.Lclock_realtime_coarse
	cmpl	$VKSO_CLOCK_MONOTONIC_COARSE, %esi
	je	.Lclock_monotonic_coarse
	cmpl	$VKSO_CLOCK_MONOTONIC_RAW, %esi
	je	.Lclock_monotonic_raw
	cmpl	$VKSO_CLOCK_BOOTTIME, %esi
	je	.Lclock_boottime
	cmpl	$VKSO_CLOCK_TAI, %esi
	jne	.Lclock_fallback
	leaq	vkso_user_context(%rip), %rcx
	jmp	vkso_clock_gettime_tai

.Lclock_realtime_coarse:
	jmp	vkso_clock_gettime_realtime_coarse

.Lclock_monotonic_coarse:
	movq	vkso_user_mm_data(%rip), %rdi
	jmp	vkso_clock_gettime_monotonic_coarse

.Lclock_monotonic_raw:
	movq	vkso_user_mm_data(%rip), %rdi
	leaq	vkso_user_context(%rip), %rcx
	jmp	vkso_clock_gettime_monotonic_raw

.Lclock_boottime:
	movq	vkso_user_mm_data(%rip), %rdi
	leaq	vkso_user_context(%rip), %rcx
	jmp	vkso_clock_gettime_boottime

.Lclock_fallback:
	movslq	%esi, %rdi
	movq	%rdx, %rsi
	movl	$__NR_clock_gettime, %eax
	syscall
	ret
	.size __vkso_clock_gettime, .-__vkso_clock_gettime

	.p2align 4
	.globl __vkso_clock_getres
	.type __vkso_clock_getres, @function
__vkso_clock_getres:
	cmpl	$VKSO_CLOCK_TAI, %edi
	ja	.Lclock_getres_fallback
	movl	$1, %eax
	movl	%edi, %ecx
	shll	%cl, %eax
	testl	$VKSO_HRES_CLOCK_MASK, %eax
	jne	.Lclock_getres_hres
	testl	$VKSO_COARSE_CLOCK_MASK, %eax
	jne	.Lclock_getres_coarse
.Lclock_getres_fallback:
	movslq	%edi, %rdi
	movl	$__NR_clock_getres, %eax
	syscall
	ret

.Lclock_getres_hres:
	jmp	vkso_clock_getres_hres

.Lclock_getres_coarse:
	jmp	vkso_clock_getres_coarse
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
	.long 1		/* VKSO_FALLBACK_SYSCALL */
	.long 0
	.size vkso_user_context, .-vkso_user_context

	.section .note.GNU-stack, "", @progbits
