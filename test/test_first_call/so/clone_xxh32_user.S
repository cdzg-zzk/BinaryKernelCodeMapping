    .section .text.clone_xxh32, "ax", @progbits
    .p2align 12
    .globl clone_xxh32
    .type clone_xxh32, @function
clone_xxh32:
    push   %rbp
    mov    %rsi, %r8
    add    %rdi, %rsi
    mov    %rsp, %rbp
    push   %rbx
    cmp    $0xf, %r8
    jbe    .L330
    mov    %edx, %r9d
    lea    0x24234428(%rdx), %eax
    lea    -0x10(%rsi), %rbx
    lea    -0x7a143589(%rdx), %r11d
    lea    0x61c8864f(%rdx), %r10d
    mov    %rdi, %rdx
.L51:
    imul   $0x85ebca77, (%rdx), %ecx
    add    $0x10, %rdx
    add    %ecx, %eax
    imul   $0x85ebca77, -0xc(%rdx), %ecx
    rol    $0xd, %eax
    imul   $0x9e3779b1, %eax, %eax
    add    %r11d, %ecx
    rol    $0xd, %ecx
    imul   $0x9e3779b1, %ecx, %r11d
    imul   $0x85ebca77, -0x8(%rdx), %ecx
    add    %r9d, %ecx
    rol    $0xd, %ecx
    imul   $0x9e3779b1, %ecx, %r9d
    imul   $0x85ebca77, -0x4(%rdx), %ecx
    add    %r10d, %ecx
    rol    $0xd, %ecx
    imul   $0x9e3779b1, %ecx, %r10d
    cmp    %rdx, %rbx
    jae    .L51
    lea    -0x10(%r8), %rdx
    lea    0x1(%rdi), %rcx
    and    $0xfffffffffffffff0, %rdx
    lea    -0xf(%rsi), %rbx
    add    $0x10, %rdx
    cmp    %rcx, %rbx
    mov    $0x10, %ecx
    cmovb  %rcx, %rdx
    rol    %eax
    rol    $0x7, %r11d
    rol    $0xc, %r9d
    add    %rdx, %rdi
    lea    (%rax, %r11, 1), %edx
    ror    $0xe, %r10d
    add    %r9d, %edx
    add    %r10d, %edx
.L196:
    add    %r8d, %edx
    lea    0x4(%rdi), %r8
    cmp    %r8, %rsi
    jb     .L253
    mov    %r8, %rcx
.L211:
    imul   $0xc2b2ae3d, -0x4(%rcx), %eax
    add    $0x4, %rcx
    add    %edx, %eax
    ror    $0xf, %eax
    imul   $0x27d4eb2f, %eax, %edx
    cmp    %rsi, %rcx
    jbe    .L211
    lea    -0x4(%rsi), %rax
    sub    %rdi, %rax
    and    $0xfffffffffffffffc, %rax
    lea    (%r8, %rax, 1), %rdi
.L253:
    cmp    %rdi, %rsi
    jbe    .L287
.L258:
    movzbl (%rdi), %eax
    add    $0x1, %rdi
    imul   $0x165667b1, %eax, %eax
    add    %edx, %eax
    rol    $0xb, %eax
    imul   $0x9e3779b1, %eax, %edx
    cmp    %rdi, %rsi
    jne    .L258
.L287:
    mov    %edx, %eax
    mov    -0x8(%rbp), %rbx
    leave
    shr    $0xf, %eax
    xor    %edx, %eax
    imul   $0x85ebca77, %eax, %eax
    mov    %eax, %edx
    shr    $0xd, %edx
    xor    %eax, %edx
    imul   $0xc2b2ae3d, %edx, %edx
    mov    %edx, %eax
    shr    $0x10, %eax
    xor    %edx, %eax
    ret

.L330:
    add    $0x165667b1, %edx
    jmp    .L196
    .size clone_xxh32, .-clone_xxh32

    .section .note.GNU-stack,"",@progbits
