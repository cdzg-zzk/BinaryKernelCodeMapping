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
#define VKSO_MM_CLOCK_MASK_OFFSET	4
#define VKSO_MM_MONOTONIC_OFFSET	8
#define VKSO_MM_BOOTTIME_OFFSET		24

	.macro VKSO_APPLY_MM clock, member
	movq	vkso_user_mm_data(%rip), %rax
	testl	$(1 << \clock), VKSO_MM_CLOCK_MASK_OFFSET(%rax)
	je	.Lclock_return
	leaq	\member(%rax), %rdi
	jmp	vkso_time_apply_offset
	.endm

/*
 * Private userspace entry veneers embedded directly in libkernel.so.
 *
 * Shared core text remains backed by kernel pages.  This page is ordinary
 * DSO-owned RX text so it can inject per-process addresses without changing
 * the shared kernel ABI.  The clock_gettime veneer preserves the two common
 * clocks as its first tests, then uses a shallow decision tree for the other
 * IDs before tail-jumping to the specialized readers.  This removes one
 * shared-core dispatch hop and only prepares dependencies used by the selected
 * reader. Coarse readers cannot fail and remain tail calls; high-resolution
 * readers return a pure-core status so this public page owns their cold
 * syscall exit. make_dll resolves every transfer locally, so no PLT/GOT
 * remains on the hot path.
 */

	.section .vkso.user.text, "ax", @progbits
	.p2align 4
	.globl __vkso_clock_gettime
	.type __vkso_clock_gettime, @function
__vkso_clock_gettime:
	testl	%edi, %edi
	jne	.Lclock_not_realtime
	pushq	%rsi
	movq	%rsi, %rdi
	leaq	vkso_user_context(%rip), %rsi
	call	vkso_clock_gettime_realtime
	popq	%rsi
	testl	%eax, %eax
	je	.Lclock_return
	xorl	%edi, %edi
	jmp	.Lclock_fallback

.Lclock_not_realtime:
	cmpl	$VKSO_CLOCK_MONOTONIC, %edi
	jne	.Lclock_not_monotonic
	pushq	%rsi
	movq	%rsi, %rdi
	leaq	vkso_user_context(%rip), %rsi
	call	vkso_clock_gettime_monotonic
	popq	%rsi
	testl	%eax, %eax
	je	.Lclock_apply_monotonic
	movl	$VKSO_CLOCK_MONOTONIC, %edi
	jmp	.Lclock_fallback

.Lclock_not_monotonic:
	cmpl	$VKSO_CLOCK_MONOTONIC_COARSE, %edi
	je	.Lclock_monotonic_coarse
	jg	.Lclock_after_coarse
	cmpl	$VKSO_CLOCK_REALTIME_COARSE, %edi
	je	.Lclock_realtime_coarse
	cmpl	$VKSO_CLOCK_MONOTONIC_RAW, %edi
	je	.Lclock_monotonic_raw

.Lclock_fallback:
	movslq	%edi, %rdi
	movl	$__NR_clock_gettime, %eax
	syscall
	ret

.Lclock_after_coarse:
	cmpl	$VKSO_CLOCK_BOOTTIME, %edi
	je	.Lclock_boottime
	cmpl	$VKSO_CLOCK_TAI, %edi
	jne	.Lclock_fallback
	pushq	%rsi
	movq	%rsi, %rdi
	leaq	vkso_user_context(%rip), %rsi
	call	vkso_clock_gettime_tai
	popq	%rsi
	testl	%eax, %eax
	je	.Lclock_return
	movl	$VKSO_CLOCK_TAI, %edi
	jmp	.Lclock_fallback

.Lclock_realtime_coarse:
	movq	%rsi, %rdi
	jmp	vkso_clock_gettime_realtime_coarse

.Lclock_monotonic_coarse:
	pushq	%rsi
	movq	%rsi, %rdi
	call	vkso_clock_gettime_monotonic_coarse
	popq	%rsi
	jmp	.Lclock_apply_monotonic_coarse

.Lclock_monotonic_raw:
	pushq	%rsi
	movq	%rsi, %rdi
	leaq	vkso_user_context(%rip), %rsi
	call	vkso_clock_gettime_monotonic_raw
	popq	%rsi
	testl	%eax, %eax
	je	.Lclock_apply_monotonic_raw
	movl	$VKSO_CLOCK_MONOTONIC_RAW, %edi
	jmp	.Lclock_fallback

.Lclock_boottime:
	pushq	%rsi
	movq	%rsi, %rdi
	leaq	vkso_user_context(%rip), %rsi
	call	vkso_clock_gettime_boottime
	popq	%rsi
	testl	%eax, %eax
	je	.Lclock_apply_boottime
	movl	$VKSO_CLOCK_BOOTTIME, %edi
	jmp	.Lclock_fallback

.Lclock_apply_monotonic:
	VKSO_APPLY_MM VKSO_CLOCK_MONOTONIC, VKSO_MM_MONOTONIC_OFFSET

.Lclock_apply_monotonic_coarse:
	VKSO_APPLY_MM VKSO_CLOCK_MONOTONIC_COARSE, VKSO_MM_MONOTONIC_OFFSET

.Lclock_apply_monotonic_raw:
	VKSO_APPLY_MM VKSO_CLOCK_MONOTONIC_RAW, VKSO_MM_MONOTONIC_OFFSET

.Lclock_apply_boottime:
	VKSO_APPLY_MM VKSO_CLOCK_BOOTTIME, VKSO_MM_BOOTTIME_OFFSET

.Lclock_return:
	xorl	%eax, %eax
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
	pushq	%rdi
	pushq	%rsi
	subq	$8, %rsp
	leaq	vkso_user_context(%rip), %rdx
	call	vkso_gettimeofday_core
	addq	$8, %rsp
	popq	%rsi
	popq	%rdi
	testl	%eax, %eax
	jne	.Lgettimeofday_fallback
	ret
.Lgettimeofday_fallback:
	movl	$__NR_gettimeofday, %eax
	syscall
	ret
	.size __vkso_gettimeofday, .-__vkso_gettimeofday

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
	.size vkso_user_context, .-vkso_user_context

	.section .note.GNU-stack, "", @progbits
