
/home/zzk/BinaryKernelCodeMapping/test/test_BCH/build/bch-bench:     file format elf64-x86-64


Disassembly of section .init:

Disassembly of section .plt:

Disassembly of section .plt.got:

Disassembly of section .plt.sec:

Disassembly of section .text:

0000000000002a40 <decode_once>:
    2a40:	48 83 ec 08          	sub    rsp,0x8
    2a44:	48 8b 07             	mov    rax,QWORD PTR [rdi]
    2a47:	83 7f 18 01          	cmp    DWORD PTR [rdi+0x18],0x1
    2a4b:	4c 8b 47 30          	mov    r8,QWORD PTR [rdi+0x30]
    2a4f:	4c 8b 5f 08          	mov    r11,QWORD PTR [rdi+0x8]
    2a53:	4c 8b 50 40          	mov    r10,QWORD PTR [rax+0x40]
    2a57:	48 8b 47 10          	mov    rax,QWORD PTR [rdi+0x10]
    2a5b:	8b 50 08             	mov    edx,DWORD PTR [rax+0x8]
    2a5e:	74 28                	je     2a88 <decode_once+0x48>
    2a60:	48 83 ec 08          	sub    rsp,0x8
    2a64:	48 8b 77 20          	mov    rsi,QWORD PTR [rdi+0x20]
    2a68:	48 63 ca             	movsxd rcx,edx
    2a6b:	45 31 c9             	xor    r9d,r9d
    2a6e:	41 50                	push   r8
    2a70:	4c 89 df             	mov    rdi,r11
    2a73:	45 31 c0             	xor    r8d,r8d
    2a76:	48 01 f1             	add    rcx,rsi
    2a79:	41 ff d2             	call   r10
    2a7c:	5a                   	pop    rdx
    2a7d:	59                   	pop    rcx
    2a7e:	48 83 c4 08          	add    rsp,0x8
    2a82:	c3                   	ret    
    2a83:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    2a88:	48 83 ec 08          	sub    rsp,0x8
    2a8c:	31 f6                	xor    esi,esi
    2a8e:	45 31 c9             	xor    r9d,r9d
    2a91:	31 c9                	xor    ecx,ecx
    2a93:	41 50                	push   r8
    2a95:	4c 8b 47 28          	mov    r8,QWORD PTR [rdi+0x28]
    2a99:	4c 89 df             	mov    rdi,r11
    2a9c:	41 ff d2             	call   r10
    2a9f:	5e                   	pop    rsi
    2aa0:	5f                   	pop    rdi
    2aa1:	48 83 c4 08          	add    rsp,0x8
    2aa5:	c3                   	ret    

Disassembly of section .fini:
