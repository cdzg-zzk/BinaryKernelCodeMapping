
/home/zzk/BinaryKernelCodeMapping/test/test_BCH/build/bch-bench:     file format elf64-x86-64


Disassembly of section .init:

Disassembly of section .plt:

Disassembly of section .plt.got:

Disassembly of section .plt.sec:

Disassembly of section .text:

0000000000002f70 <prepare_decode_context>:
    2f70:	41 57                	push   r15
    2f72:	41 56                	push   r14
    2f74:	41 55                	push   r13
    2f76:	49 89 fd             	mov    r13,rdi
    2f79:	41 54                	push   r12
    2f7b:	55                   	push   rbp
    2f7c:	53                   	push   rbx
    2f7d:	48 89 f3             	mov    rbx,rsi
    2f80:	be 01 00 00 00       	mov    esi,0x1
    2f85:	48 83 ec 08          	sub    rsp,0x8
    2f89:	4c 8b 77 10          	mov    r14,QWORD PTR [rdi+0x10]
    2f8d:	45 8b 66 10          	mov    r12d,DWORD PTR [r14+0x10]
    2f91:	4d 63 7e 08          	movsxd r15,DWORD PTR [r14+0x8]
    2f95:	4d 01 e7             	add    r15,r12
    2f98:	4c 89 ff             	mov    rdi,r15
    2f9b:	e8 90 e2 ff ff       	call   1230 <calloc@plt>
    2fa0:	48 85 c0             	test   rax,rax
    2fa3:	0f 84 f5 00 00 00    	je     309e <prepare_decode_context+0x12e>
    2fa9:	49 89 45 20          	mov    QWORD PTR [r13+0x20],rax
    2fad:	4c 89 e7             	mov    rdi,r12
    2fb0:	be 01 00 00 00       	mov    esi,0x1
    2fb5:	48 89 c5             	mov    rbp,rax
    2fb8:	e8 73 e2 ff ff       	call   1230 <calloc@plt>
    2fbd:	49 89 c4             	mov    r12,rax
    2fc0:	48 85 c0             	test   rax,rax
    2fc3:	0f 84 d5 00 00 00    	je     309e <prepare_decode_context+0x12e>
    2fc9:	49 89 45 28          	mov    QWORD PTR [r13+0x28],rax
    2fcd:	49 63 7e 04          	movsxd rdi,DWORD PTR [r14+0x4]
    2fd1:	be 04 00 00 00       	mov    esi,0x4
    2fd6:	e8 55 e2 ff ff       	call   1230 <calloc@plt>
    2fdb:	48 85 c0             	test   rax,rax
    2fde:	0f 84 ba 00 00 00    	je     309e <prepare_decode_context+0x12e>
    2fe4:	49 89 45 30          	mov    QWORD PTR [r13+0x30],rax
    2fe8:	49 8b 76 18          	mov    rsi,QWORD PTR [r14+0x18]
    2fec:	4c 89 fa             	mov    rdx,r15
    2fef:	48 89 ef             	mov    rdi,rbp
    2ff2:	e8 79 e2 ff ff       	call   1270 <memcpy@plt>
    2ff7:	41 8b 45 1c          	mov    eax,DWORD PTR [r13+0x1c]
    2ffb:	85 c0                	test   eax,eax
    2ffd:	7e 2c                	jle    302b <prepare_decode_context+0xbb>
    2fff:	83 e8 01             	sub    eax,0x1
    3002:	48 89 da             	mov    rdx,rbx
    3005:	be 01 00 00 00       	mov    esi,0x1
    300a:	48 8d 7c 83 04       	lea    rdi,[rbx+rax*4+0x4]
    300f:	90                   	nop
    3010:	8b 0a                	mov    ecx,DWORD PTR [rdx]
    3012:	89 f3                	mov    ebx,esi
    3014:	48 83 c2 04          	add    rdx,0x4
    3018:	89 c8                	mov    eax,ecx
    301a:	83 e1 07             	and    ecx,0x7
    301d:	c1 e8 03             	shr    eax,0x3
    3020:	d3 e3                	shl    ebx,cl
    3022:	30 5c 05 00          	xor    BYTE PTR [rbp+rax*1+0x0],bl
    3026:	48 39 fa             	cmp    rdx,rdi
    3029:	75 e5                	jne    3010 <prepare_decode_context+0xa0>
    302b:	41 83 7d 18 01       	cmp    DWORD PTR [r13+0x18],0x1
    3030:	74 16                	je     3048 <prepare_decode_context+0xd8>
    3032:	48 83 c4 08          	add    rsp,0x8
    3036:	5b                   	pop    rbx
    3037:	5d                   	pop    rbp
    3038:	41 5c                	pop    r12
    303a:	41 5d                	pop    r13
    303c:	41 5e                	pop    r14
    303e:	41 5f                	pop    r15
    3040:	c3                   	ret    
    3041:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    3048:	49 8b 45 00          	mov    rax,QWORD PTR [r13+0x0]
    304c:	41 8b 56 08          	mov    edx,DWORD PTR [r14+0x8]
    3050:	4c 89 e1             	mov    rcx,r12
    3053:	48 89 ee             	mov    rsi,rbp
    3056:	49 8b 7d 08          	mov    rdi,QWORD PTR [r13+0x8]
    305a:	ff 50 38             	call   QWORD PTR [rax+0x38]
    305d:	41 8b 46 10          	mov    eax,DWORD PTR [r14+0x10]
    3061:	85 c0                	test   eax,eax
    3063:	74 cd                	je     3032 <prepare_decode_context+0xc2>
    3065:	31 c0                	xor    eax,eax
    3067:	66 0f 1f 84 00 00 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    3070:	49 8b 75 20          	mov    rsi,QWORD PTR [r13+0x20]
    3074:	89 c2                	mov    edx,eax
    3076:	89 c1                	mov    ecx,eax
    3078:	49 03 55 28          	add    rdx,QWORD PTR [r13+0x28]
    307c:	41 03 4e 08          	add    ecx,DWORD PTR [r14+0x8]
    3080:	83 c0 01             	add    eax,0x1
    3083:	0f b6 0c 0e          	movzx  ecx,BYTE PTR [rsi+rcx*1]
    3087:	30 0a                	xor    BYTE PTR [rdx],cl
    3089:	41 39 46 10          	cmp    DWORD PTR [r14+0x10],eax
    308d:	77 e1                	ja     3070 <prepare_decode_context+0x100>
    308f:	48 83 c4 08          	add    rsp,0x8
    3093:	5b                   	pop    rbx
    3094:	5d                   	pop    rbp
    3095:	41 5c                	pop    r12
    3097:	41 5d                	pop    r13
    3099:	41 5e                	pop    r14
    309b:	41 5f                	pop    r15
    309d:	c3                   	ret    
    309e:	48 8d 3d 8e 11 00 00 	lea    rdi,[rip+0x118e]        # 4233 <_IO_stdin_used+0x233>
    30a5:	e8 36 fb ff ff       	call   2be0 <die>

Disassembly of section .fini:
