/* SPDX-License-Identifier: GPL-2.0 */
/* No entry point: these distinct physical pages are never executed. */
.section .text,"ax",@progbits
.balign 4096
.globl vkso_fixture_pages
.type vkso_fixture_pages,@object
vkso_fixture_pages:
.fill 300*4096,1,0x90
.size vkso_fixture_pages, .-vkso_fixture_pages
.section .note.GNU-stack,"",@progbits
