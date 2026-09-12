
/home/zzk/BinaryKernelCodeMapping/test/test_BCH/build/bch-bench:     file format elf64-x86-64


Disassembly of section .init:

Disassembly of section .plt:

Disassembly of section .plt.got:

Disassembly of section .plt.sec:

Disassembly of section .text:

0000000000002d00 <run_context.isra.0>:
    2d00:	41 55                	push   r13
    2d02:	41 54                	push   r12
    2d04:	55                   	push   rbp
    2d05:	48 89 f5             	mov    rbp,rsi
    2d08:	53                   	push   rbx
    2d09:	48 89 fb             	mov    rbx,rdi
    2d0c:	48 83 ec 08          	sub    rsp,0x8
    2d10:	8b 47 18             	mov    eax,DWORD PTR [rdi+0x18]
    2d13:	85 c0                	test   eax,eax
    2d15:	74 31                	je     2d48 <run_context.isra.0+0x48>
    2d17:	45 31 e4             	xor    r12d,r12d
    2d1a:	45 31 ed             	xor    r13d,r13d
    2d1d:	48 85 f6             	test   rsi,rsi
    2d20:	74 4e                	je     2d70 <run_context.isra.0+0x70>
    2d22:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    2d28:	48 89 df             	mov    rdi,rbx
    2d2b:	49 83 c4 01          	add    r12,0x1
    2d2f:	e8 0c fd ff ff       	call   2a40 <decode_once>
    2d34:	41 01 c5             	add    r13d,eax
    2d37:	4c 39 e5             	cmp    rbp,r12
    2d3a:	75 ec                	jne    2d28 <run_context.isra.0+0x28>
    2d3c:	4d 63 ed             	movsxd r13,r13d
    2d3f:	eb 32                	jmp    2d73 <run_context.isra.0+0x73>
    2d41:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    2d48:	48 85 f6             	test   rsi,rsi
    2d4b:	74 23                	je     2d70 <run_context.isra.0+0x70>
    2d4d:	45 31 e4             	xor    r12d,r12d
    2d50:	48 8b 43 10          	mov    rax,QWORD PTR [rbx+0x10]
    2d54:	49 83 c4 01          	add    r12,0x1
    2d58:	48 8b 7b 08          	mov    rdi,QWORD PTR [rbx+0x8]
    2d5c:	31 c9                	xor    ecx,ecx
    2d5e:	8b 50 08             	mov    edx,DWORD PTR [rax+0x8]
    2d61:	48 8b 70 18          	mov    rsi,QWORD PTR [rax+0x18]
    2d65:	48 8b 03             	mov    rax,QWORD PTR [rbx]
    2d68:	ff 50 38             	call   QWORD PTR [rax+0x38]
    2d6b:	49 39 ec             	cmp    r12,rbp
    2d6e:	75 e0                	jne    2d50 <run_context.isra.0+0x50>
    2d70:	45 31 ed             	xor    r13d,r13d
    2d73:	48 8b 05 b6 32 00 00 	mov    rax,QWORD PTR [rip+0x32b6]        # 6030 <result_sink>
    2d7a:	48 01 c5             	add    rbp,rax
    2d7d:	4c 01 ed             	add    rbp,r13
    2d80:	48 89 2d a9 32 00 00 	mov    QWORD PTR [rip+0x32a9],rbp        # 6030 <result_sink>
    2d87:	48 83 c4 08          	add    rsp,0x8
    2d8b:	5b                   	pop    rbx
    2d8c:	5d                   	pop    rbp
    2d8d:	41 5c                	pop    r12
    2d8f:	41 5d                	pop    r13
    2d91:	c3                   	ret    

Disassembly of section .fini:
