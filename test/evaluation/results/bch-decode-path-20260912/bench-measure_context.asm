
/home/zzk/BinaryKernelCodeMapping/test/test_BCH/build/bch-bench:     file format elf64-x86-64


Disassembly of section .init:

Disassembly of section .plt:

Disassembly of section .plt.got:

Disassembly of section .plt.sec:

Disassembly of section .text:

0000000000002da0 <measure_context>:
    2da0:	41 54                	push   r12
    2da2:	49 89 f4             	mov    r12,rsi
    2da5:	55                   	push   rbp
    2da6:	48 89 fd             	mov    rbp,rdi
    2da9:	bf 02 00 00 00       	mov    edi,0x2
    2dae:	48 83 ec 38          	sub    rsp,0x38
    2db2:	64 48 8b 04 25 28 00 00 00 	mov    rax,QWORD PTR fs:0x28
    2dbb:	48 89 44 24 28       	mov    QWORD PTR [rsp+0x28],rax
    2dc0:	31 c0                	xor    eax,eax
    2dc2:	48 89 e6             	mov    rsi,rsp
    2dc5:	e8 16 e4 ff ff       	call   11e0 <clock_gettime@plt>
    2dca:	85 c0                	test   eax,eax
    2dcc:	75 50                	jne    2e1e <measure_context+0x7e>
    2dce:	4c 89 e6             	mov    rsi,r12
    2dd1:	48 89 ef             	mov    rdi,rbp
    2dd4:	e8 27 ff ff ff       	call   2d00 <run_context.isra.0>
    2dd9:	48 8d 74 24 10       	lea    rsi,[rsp+0x10]
    2dde:	bf 02 00 00 00       	mov    edi,0x2
    2de3:	e8 f8 e3 ff ff       	call   11e0 <clock_gettime@plt>
    2de8:	85 c0                	test   eax,eax
    2dea:	75 43                	jne    2e2f <measure_context+0x8f>
    2dec:	48 8b 44 24 10       	mov    rax,QWORD PTR [rsp+0x10]
    2df1:	48 2b 04 24          	sub    rax,QWORD PTR [rsp]
    2df5:	48 69 c0 00 ca 9a 3b 	imul   rax,rax,0x3b9aca00
    2dfc:	48 03 44 24 18       	add    rax,QWORD PTR [rsp+0x18]
    2e01:	48 2b 44 24 08       	sub    rax,QWORD PTR [rsp+0x8]
    2e06:	48 8b 54 24 28       	mov    rdx,QWORD PTR [rsp+0x28]
    2e0b:	64 48 2b 14 25 28 00 00 00 	sub    rdx,QWORD PTR fs:0x28
    2e14:	75 14                	jne    2e2a <measure_context+0x8a>
    2e16:	48 83 c4 38          	add    rsp,0x38
    2e1a:	5d                   	pop    rbp
    2e1b:	41 5c                	pop    r12
    2e1d:	c3                   	ret    
    2e1e:	48 8d 3d da 13 00 00 	lea    rdi,[rip+0x13da]        # 41ff <_IO_stdin_used+0x1ff>
    2e25:	e8 b6 fd ff ff       	call   2be0 <die>
    2e2a:	e8 d1 e3 ff ff       	call   1200 <__stack_chk_fail@plt>
    2e2f:	48 8d 3d e4 13 00 00 	lea    rdi,[rip+0x13e4]        # 421a <_IO_stdin_used+0x21a>
    2e36:	e8 a5 fd ff ff       	call   2be0 <die>

Disassembly of section .fini:
