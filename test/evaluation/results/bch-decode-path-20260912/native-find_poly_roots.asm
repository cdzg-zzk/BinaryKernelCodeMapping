
/home/zzk/BinaryKernelCodeMapping/test/test_BCH/build/libbch-kernel-native.so:     file format elf64-x86-64


Disassembly of section .init:

Disassembly of section .plt:

Disassembly of section .plt.got:

Disassembly of section .plt.sec:

Disassembly of section .text:

0000000000001940 <find_poly_roots>:
    1940:	41 57                	push   r15
    1942:	41 56                	push   r14
    1944:	49 89 d6             	mov    r14,rdx
    1947:	41 55                	push   r13
    1949:	41 54                	push   r12
    194b:	49 89 fc             	mov    r12,rdi
    194e:	55                   	push   rbp
    194f:	53                   	push   rbx
    1950:	48 83 ec 58          	sub    rsp,0x58
    1954:	8b 02                	mov    eax,DWORD PTR [rdx]
    1956:	89 74 24 10          	mov    DWORD PTR [rsp+0x10],esi
    195a:	48 89 4c 24 08       	mov    QWORD PTR [rsp+0x8],rcx
    195f:	c7 44 24 28 00 00 00 00 	mov    DWORD PTR [rsp+0x28],0x0
    1967:	45 31 ed             	xor    r13d,r13d
    196a:	4c 89 f7             	mov    rdi,r14
    196d:	45 89 ee             	mov    r14d,r13d
    1970:	49 89 fd             	mov    r13,rdi
    1973:	83 f8 03             	cmp    eax,0x3
    1976:	0f 84 74 01 00 00    	je     1af0 <find_poly_roots+0x1b0>
    197c:	77 42                	ja     19c0 <find_poly_roots+0x80>
    197e:	83 f8 01             	cmp    eax,0x1
    1981:	0f 84 e9 02 00 00    	je     1c70 <find_poly_roots+0x330>
    1987:	83 f8 02             	cmp    eax,0x2
    198a:	0f 85 1f 03 00 00    	jne    1caf <find_poly_roots+0x36f>
    1990:	41 8b 45 04          	mov    eax,DWORD PTR [r13+0x4]
    1994:	4d 89 ef             	mov    r15,r13
    1997:	85 c0                	test   eax,eax
    1999:	74 0c                	je     19a7 <find_poly_roots+0x67>
    199b:	41 8b 4d 08          	mov    ecx,DWORD PTR [r13+0x8]
    199f:	85 c9                	test   ecx,ecx
    19a1:	0f 85 73 07 00 00    	jne    211a <find_poly_roots+0x7da>
    19a7:	8b 44 24 28          	mov    eax,DWORD PTR [rsp+0x28]
    19ab:	48 83 c4 58          	add    rsp,0x58
    19af:	5b                   	pop    rbx
    19b0:	5d                   	pop    rbp
    19b1:	44 01 f0             	add    eax,r14d
    19b4:	41 5c                	pop    r12
    19b6:	41 5d                	pop    r13
    19b8:	41 5e                	pop    r14
    19ba:	41 5f                	pop    r15
    19bc:	c3                   	ret    
    19bd:	0f 1f 00             	nop    DWORD PTR [rax]
    19c0:	83 f8 04             	cmp    eax,0x4
    19c3:	0f 85 f7 02 00 00    	jne    1cc0 <find_poly_roots+0x380>
    19c9:	41 8b 55 04          	mov    edx,DWORD PTR [r13+0x4]
    19cd:	4d 89 ef             	mov    r15,r13
    19d0:	85 d2                	test   edx,edx
    19d2:	74 d3                	je     19a7 <find_poly_roots+0x67>
    19d4:	49 8b 5c 24 20       	mov    rbx,QWORD PTR [r12+0x20]
    19d9:	41 8b 4f 14          	mov    ecx,DWORD PTR [r15+0x14]
    19dd:	41 8b 44 24 04       	mov    eax,DWORD PTR [r12+0x4]
    19e2:	4d 8b 6c 24 18       	mov    r13,QWORD PTR [r12+0x18]
    19e7:	0f b7 14 53          	movzx  edx,WORD PTR [rbx+rdx*2]
    19eb:	44 0f b7 04 4b       	movzx  r8d,WORD PTR [rbx+rcx*2]
    19f0:	01 c2                	add    edx,eax
    19f2:	44 29 c2             	sub    edx,r8d
    19f5:	89 d1                	mov    ecx,edx
    19f7:	29 c1                	sub    ecx,eax
    19f9:	39 d0                	cmp    eax,edx
    19fb:	0f 46 d1             	cmovbe edx,ecx
    19fe:	48 63 d2             	movsxd rdx,edx
    1a01:	41 0f b7 4c 55 00    	movzx  ecx,WORD PTR [r13+rdx*2+0x0]
    1a07:	41 8b 57 08          	mov    edx,DWORD PTR [r15+0x8]
    1a0b:	89 cf                	mov    edi,ecx
    1a0d:	85 d2                	test   edx,edx
    1a0f:	74 1b                	je     1a2c <find_poly_roots+0xec>
    1a11:	0f b7 14 53          	movzx  edx,WORD PTR [rbx+rdx*2]
    1a15:	01 c2                	add    edx,eax
    1a17:	44 29 c2             	sub    edx,r8d
    1a1a:	89 d6                	mov    esi,edx
    1a1c:	29 c6                	sub    esi,eax
    1a1e:	39 d0                	cmp    eax,edx
    1a20:	0f 46 d6             	cmovbe edx,esi
    1a23:	48 63 d2             	movsxd rdx,edx
    1a26:	41 0f b7 54 55 00    	movzx  edx,WORD PTR [r13+rdx*2+0x0]
    1a2c:	41 8b 77 0c          	mov    esi,DWORD PTR [r15+0xc]
    1a30:	85 f6                	test   esi,esi
    1a32:	74 1e                	je     1a52 <find_poly_roots+0x112>
    1a34:	0f b7 34 73          	movzx  esi,WORD PTR [rbx+rsi*2]
    1a38:	01 c6                	add    esi,eax
    1a3a:	44 29 c6             	sub    esi,r8d
    1a3d:	41 89 f1             	mov    r9d,esi
    1a40:	41 29 c1             	sub    r9d,eax
    1a43:	39 f0                	cmp    eax,esi
    1a45:	41 0f 46 f1          	cmovbe esi,r9d
    1a49:	48 63 f6             	movsxd rsi,esi
    1a4c:	41 0f b7 74 75 00    	movzx  esi,WORD PTR [r13+rsi*2+0x0]
    1a52:	41 8b 6f 10          	mov    ebp,DWORD PTR [r15+0x10]
    1a56:	85 ed                	test   ebp,ebp
    1a58:	0f 84 4a 05 00 00    	je     1fa8 <find_poly_roots+0x668>
    1a5e:	44 0f b7 0c 6b       	movzx  r9d,WORD PTR [rbx+rbp*2]
    1a63:	41 01 c1             	add    r9d,eax
    1a66:	45 29 c1             	sub    r9d,r8d
    1a69:	45 89 c8             	mov    r8d,r9d
    1a6c:	41 29 c0             	sub    r8d,eax
    1a6f:	44 39 c8             	cmp    eax,r9d
    1a72:	45 0f 47 c1          	cmova  r8d,r9d
    1a76:	31 ed                	xor    ebp,ebp
    1a78:	4d 63 c0             	movsxd r8,r8d
    1a7b:	47 0f b7 7c 45 00    	movzx  r15d,WORD PTR [r13+r8*2+0x0]
    1a81:	4d 89 f8             	mov    r8,r15
    1a84:	45 85 ff             	test   r15d,r15d
    1a87:	0f 85 23 05 00 00    	jne    1fb0 <find_poly_roots+0x670>
    1a8d:	4c 8b 44 24 08       	mov    r8,QWORD PTR [rsp+0x8]
    1a92:	4c 89 e7             	mov    rdi,r12
    1a95:	e8 46 fb ff ff       	call   15e0 <find_affine4_roots>
    1a9a:	83 f8 04             	cmp    eax,0x4
    1a9d:	0f 85 04 ff ff ff    	jne    19a7 <find_poly_roots+0x67>
    1aa3:	48 8b 54 24 08       	mov    rdx,QWORD PTR [rsp+0x8]
    1aa8:	48 8d 7a 10          	lea    rdi,[rdx+0x10]
    1aac:	41 8b 74 24 04       	mov    esi,DWORD PTR [r12+0x4]
    1ab1:	8b 02                	mov    eax,DWORD PTR [rdx]
    1ab3:	45 85 ff             	test   r15d,r15d
    1ab6:	74 0e                	je     1ac6 <find_poly_roots+0x186>
    1ab8:	0f b7 0c 43          	movzx  ecx,WORD PTR [rbx+rax*2]
    1abc:	89 f0                	mov    eax,esi
    1abe:	29 c8                	sub    eax,ecx
    1ac0:	41 0f b7 44 45 00    	movzx  eax,WORD PTR [r13+rax*2+0x0]
    1ac6:	31 e8                	xor    eax,ebp
    1ac8:	0f b7 0c 43          	movzx  ecx,WORD PTR [rbx+rax*2]
    1acc:	89 f0                	mov    eax,esi
    1ace:	29 c8                	sub    eax,ecx
    1ad0:	f7 d9                	neg    ecx
    1ad2:	39 f0                	cmp    eax,esi
    1ad4:	0f 43 c1             	cmovae eax,ecx
    1ad7:	48 83 c2 04          	add    rdx,0x4
    1adb:	89 42 fc             	mov    DWORD PTR [rdx-0x4],eax
    1ade:	48 39 d7             	cmp    rdi,rdx
    1ae1:	75 c9                	jne    1aac <find_poly_roots+0x16c>
    1ae3:	41 83 c6 04          	add    r14d,0x4
    1ae7:	e9 bb fe ff ff       	jmp    19a7 <find_poly_roots+0x67>
    1aec:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    1af0:	41 8b 55 04          	mov    edx,DWORD PTR [r13+0x4]
    1af4:	4d 89 ef             	mov    r15,r13
    1af7:	85 d2                	test   edx,edx
    1af9:	0f 84 a8 fe ff ff    	je     19a7 <find_poly_roots+0x67>
    1aff:	49 8b 5c 24 20       	mov    rbx,QWORD PTR [r12+0x20]
    1b04:	41 8b 75 10          	mov    esi,DWORD PTR [r13+0x10]
    1b08:	41 8b 44 24 04       	mov    eax,DWORD PTR [r12+0x4]
    1b0d:	49 8b 4c 24 18       	mov    rcx,QWORD PTR [r12+0x18]
    1b12:	0f b7 14 53          	movzx  edx,WORD PTR [rbx+rdx*2]
    1b16:	0f b7 34 73          	movzx  esi,WORD PTR [rbx+rsi*2]
    1b1a:	45 8b 4d 08          	mov    r9d,DWORD PTR [r13+0x8]
    1b1e:	01 c2                	add    edx,eax
    1b20:	29 f2                	sub    edx,esi
    1b22:	89 d7                	mov    edi,edx
    1b24:	29 c7                	sub    edi,eax
    1b26:	39 d0                	cmp    eax,edx
    1b28:	0f 46 d7             	cmovbe edx,edi
    1b2b:	48 63 d2             	movsxd rdx,edx
    1b2e:	0f b7 14 51          	movzx  edx,WORD PTR [rcx+rdx*2]
    1b32:	89 d7                	mov    edi,edx
    1b34:	45 85 c9             	test   r9d,r9d
    1b37:	74 20                	je     1b59 <find_poly_roots+0x219>
    1b39:	46 0f b7 04 4b       	movzx  r8d,WORD PTR [rbx+r9*2]
    1b3e:	41 01 c0             	add    r8d,eax
    1b41:	41 29 f0             	sub    r8d,esi
    1b44:	45 89 c1             	mov    r9d,r8d
    1b47:	41 29 c1             	sub    r9d,eax
    1b4a:	44 39 c0             	cmp    eax,r8d
    1b4d:	45 0f 46 c1          	cmovbe r8d,r9d
    1b51:	4d 63 c0             	movsxd r8,r8d
    1b54:	46 0f b7 0c 41       	movzx  r9d,WORD PTR [rcx+r8*2]
    1b59:	41 8b 6f 0c          	mov    ebp,DWORD PTR [r15+0xc]
    1b5d:	45 31 d2             	xor    r10d,r10d
    1b60:	85 ed                	test   ebp,ebp
    1b62:	0f 84 9e 00 00 00    	je     1c06 <find_poly_roots+0x2c6>
    1b68:	44 0f b7 04 6b       	movzx  r8d,WORD PTR [rbx+rbp*2]
    1b6d:	41 01 c0             	add    r8d,eax
    1b70:	41 29 f0             	sub    r8d,esi
    1b73:	44 89 c6             	mov    esi,r8d
    1b76:	29 c6                	sub    esi,eax
    1b78:	44 39 c0             	cmp    eax,r8d
    1b7b:	41 0f 47 f0          	cmova  esi,r8d
    1b7f:	48 63 f6             	movsxd rsi,esi
    1b82:	0f b7 2c 71          	movzx  ebp,WORD PTR [rcx+rsi*2]
    1b86:	85 ed                	test   ebp,ebp
    1b88:	49 89 e8             	mov    r8,rbp
    1b8b:	40 0f 95 c6          	setne  sil
    1b8f:	85 d2                	test   edx,edx
    1b91:	0f 84 01 07 00 00    	je     2298 <find_poly_roots+0x958>
    1b97:	40 84 f6             	test   sil,sil
    1b9a:	0f 84 f8 06 00 00    	je     2298 <find_poly_roots+0x958>
    1ba0:	44 0f b7 d7          	movzx  r10d,di
    1ba4:	0f b7 34 6b          	movzx  esi,WORD PTR [rbx+rbp*2]
    1ba8:	46 0f b7 14 53       	movzx  r10d,WORD PTR [rbx+r10*2]
    1bad:	44 01 d6             	add    esi,r10d
    1bb0:	41 89 f2             	mov    r10d,esi
    1bb3:	41 29 c2             	sub    r10d,eax
    1bb6:	39 f0                	cmp    eax,esi
    1bb8:	41 0f 46 f2          	cmovbe esi,r10d
    1bbc:	48 63 f6             	movsxd rsi,esi
    1bbf:	44 0f b7 14 71       	movzx  r10d,WORD PTR [rcx+rsi*2]
    1bc4:	45 85 c9             	test   r9d,r9d
    1bc7:	0f 84 e4 06 00 00    	je     22b1 <find_poly_roots+0x971>
    1bcd:	44 89 ca             	mov    edx,r9d
    1bd0:	42 0f b7 34 43       	movzx  esi,WORD PTR [rbx+r8*2]
    1bd5:	0f b7 14 53          	movzx  edx,WORD PTR [rbx+rdx*2]
    1bd9:	01 f2                	add    edx,esi
    1bdb:	41 89 d0             	mov    r8d,edx
    1bde:	41 29 c0             	sub    r8d,eax
    1be1:	39 d0                	cmp    eax,edx
    1be3:	41 0f 46 d0          	cmovbe edx,r8d
    1be7:	48 63 d2             	movsxd rdx,edx
    1bea:	66 33 3c 51          	xor    di,WORD PTR [rcx+rdx*2]
    1bee:	0f b7 d7             	movzx  edx,di
    1bf1:	01 f6                	add    esi,esi
    1bf3:	89 f7                	mov    edi,esi
    1bf5:	29 c7                	sub    edi,eax
    1bf7:	39 f0                	cmp    eax,esi
    1bf9:	0f 46 f7             	cmovbe esi,edi
    1bfc:	48 63 f6             	movsxd rsi,esi
    1bff:	0f b7 04 71          	movzx  eax,WORD PTR [rcx+rsi*2]
    1c03:	41 31 c1             	xor    r9d,eax
    1c06:	4c 8d 6c 24 40       	lea    r13,[rsp+0x40]
    1c0b:	44 89 d1             	mov    ecx,r10d
    1c0e:	44 89 ce             	mov    esi,r9d
    1c11:	4c 89 e7             	mov    rdi,r12
    1c14:	4d 89 e8             	mov    r8,r13
    1c17:	e8 c4 f9 ff ff       	call   15e0 <find_affine4_roots>
    1c1c:	83 f8 04             	cmp    eax,0x4
    1c1f:	0f 85 82 fd ff ff    	jne    19a7 <find_poly_roots+0x67>
    1c25:	4c 8b 4c 24 08       	mov    r9,QWORD PTR [rsp+0x8]
    1c2a:	4c 89 e8             	mov    rax,r13
    1c2d:	4c 8d 44 24 50       	lea    r8,[rsp+0x50]
    1c32:	31 f6                	xor    esi,esi
    1c34:	8b 10                	mov    edx,DWORD PTR [rax]
    1c36:	39 d5                	cmp    ebp,edx
    1c38:	74 1e                	je     1c58 <find_poly_roots+0x318>
    1c3a:	41 8b 7c 24 04       	mov    edi,DWORD PTR [r12+0x4]
    1c3f:	0f b7 0c 53          	movzx  ecx,WORD PTR [rbx+rdx*2]
    1c43:	89 fa                	mov    edx,edi
    1c45:	29 ca                	sub    edx,ecx
    1c47:	f7 d9                	neg    ecx
    1c49:	39 d7                	cmp    edi,edx
    1c4b:	0f 46 d1             	cmovbe edx,ecx
    1c4e:	48 63 ce             	movsxd rcx,esi
    1c51:	83 c6 01             	add    esi,0x1
    1c54:	41 89 14 89          	mov    DWORD PTR [r9+rcx*4],edx
    1c58:	48 83 c0 04          	add    rax,0x4
    1c5c:	49 39 c0             	cmp    r8,rax
    1c5f:	75 d3                	jne    1c34 <find_poly_roots+0x2f4>
    1c61:	41 01 f6             	add    r14d,esi
    1c64:	e9 3e fd ff ff       	jmp    19a7 <find_poly_roots+0x67>
    1c69:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    1c70:	41 8b 55 04          	mov    edx,DWORD PTR [r13+0x4]
    1c74:	85 d2                	test   edx,edx
    1c76:	0f 84 2b fd ff ff    	je     19a7 <find_poly_roots+0x67>
    1c7c:	49 8b 74 24 20       	mov    rsi,QWORD PTR [r12+0x20]
    1c81:	41 8b 45 08          	mov    eax,DWORD PTR [r13+0x8]
    1c85:	41 8b 4c 24 04       	mov    ecx,DWORD PTR [r12+0x4]
    1c8a:	0f b7 04 46          	movzx  eax,WORD PTR [rsi+rax*2]
    1c8e:	0f b7 14 56          	movzx  edx,WORD PTR [rsi+rdx*2]
    1c92:	01 c8                	add    eax,ecx
    1c94:	29 d0                	sub    eax,edx
    1c96:	89 c2                	mov    edx,eax
    1c98:	29 ca                	sub    edx,ecx
    1c9a:	39 c1                	cmp    ecx,eax
    1c9c:	48 8b 4c 24 08       	mov    rcx,QWORD PTR [rsp+0x8]
    1ca1:	0f 46 c2             	cmovbe eax,edx
    1ca4:	41 83 c6 01          	add    r14d,0x1
    1ca8:	89 01                	mov    DWORD PTR [rcx],eax
    1caa:	e9 f8 fc ff ff       	jmp    19a7 <find_poly_roots+0x67>
    1caf:	85 c0                	test   eax,eax
    1cb1:	0f 84 f0 fc ff ff    	je     19a7 <find_poly_roots+0x67>
    1cb7:	66 0f 1f 84 00 00 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    1cc0:	45 8b 0c 24          	mov    r9d,DWORD PTR [r12]
    1cc4:	48 63 44 24 10       	movsxd rax,DWORD PTR [rsp+0x10]
    1cc9:	41 39 c1             	cmp    r9d,eax
    1ccc:	44 89 4c 24 2c       	mov    DWORD PTR [rsp+0x2c],r9d
    1cd1:	0f 82 d0 fc ff ff    	jb     19a7 <find_poly_roots+0x67>
    1cd7:	49 8b 54 24 18       	mov    rdx,QWORD PTR [r12+0x18]
    1cdc:	49 8b 6c 24 70       	mov    rbp,QWORD PTR [r12+0x70]
    1ce1:	31 f6                	xor    esi,esi
    1ce3:	45 31 ff             	xor    r15d,r15d
    1ce6:	49 8b 5c 24 78       	mov    rbx,QWORD PTR [r12+0x78]
    1ceb:	4d 8b 44 24 60       	mov    r8,QWORD PTR [r12+0x60]
    1cf0:	0f b7 04 42          	movzx  eax,WORD PTR [rdx+rax*2]
    1cf4:	49 8b 7c 24 68       	mov    rdi,QWORD PTR [r12+0x68]
    1cf9:	48 c7 03 01 00 00 00 	mov    QWORD PTR [rbx],0x1
    1d00:	89 43 08             	mov    DWORD PTR [rbx+0x8],eax
    1d03:	c7 45 00 00 00 00 00 	mov    DWORD PTR [rbp+0x0],0x0
    1d0a:	41 8b 45 00          	mov    eax,DWORD PTR [r13+0x0]
    1d0e:	48 89 7c 24 30       	mov    QWORD PTR [rsp+0x30],rdi
    1d13:	48 89 ef             	mov    rdi,rbp
    1d16:	83 c0 01             	add    eax,0x1
    1d19:	4c 89 44 24 18       	mov    QWORD PTR [rsp+0x18],r8
    1d1e:	48 8d 14 85 04 00 00 00 	lea    rdx,[rax*4+0x4]
    1d26:	e8 85 f3 ff ff       	call   10b0 <memset@plt>
    1d2b:	49 8b 44 24 50       	mov    rax,QWORD PTR [r12+0x50]
    1d30:	4c 89 ee             	mov    rsi,r13
    1d33:	4c 89 e7             	mov    rdi,r12
    1d36:	48 89 c2             	mov    rdx,rax
    1d39:	48 89 44 24 20       	mov    QWORD PTR [rsp+0x20],rax
    1d3e:	e8 5d f5 ff ff       	call   12a0 <gf_poly_logrep>
    1d43:	44 8b 4c 24 2c       	mov    r9d,DWORD PTR [rsp+0x2c]
    1d48:	4c 8b 44 24 18       	mov    r8,QWORD PTR [rsp+0x18]
    1d4d:	45 85 c9             	test   r9d,r9d
    1d50:	45 8d 59 ff          	lea    r11d,[r9-0x1]
    1d54:	0f 8e ab 00 00 00    	jle    1e05 <find_poly_roots+0x4c5>
    1d5a:	4c 89 44 24 38       	mov    QWORD PTR [rsp+0x38],r8
    1d5f:	4d 89 ea             	mov    r10,r13
    1d62:	4d 89 e5             	mov    r13,r12
    1d65:	49 89 ec             	mov    r12,rbp
    1d68:	44 89 74 24 2c       	mov    DWORD PTR [rsp+0x2c],r14d
    1d6d:	44 89 cd             	mov    ebp,r9d
    1d70:	45 89 fe             	mov    r14d,r15d
    1d73:	45 89 df             	mov    r15d,r11d
    1d76:	66 2e 0f 1f 84 00 00 00 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    1d80:	48 63 03             	movsxd rax,DWORD PTR [rbx]
    1d83:	48 89 c7             	mov    rdi,rax
    1d86:	85 c0                	test   eax,eax
    1d88:	78 50                	js     1dda <find_poly_roots+0x49a>
    1d8a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    1d90:	8b 54 83 04          	mov    edx,DWORD PTR [rbx+rax*4+0x4]
    1d94:	41 31 54 84 04       	xor    DWORD PTR [r12+rax*4+0x4],edx
    1d99:	8b 54 83 04          	mov    edx,DWORD PTR [rbx+rax*4+0x4]
    1d9d:	85 d2                	test   edx,edx
    1d9f:	74 25                	je     1dc6 <find_poly_roots+0x486>
    1da1:	49 8b 75 20          	mov    rsi,QWORD PTR [r13+0x20]
    1da5:	49 8b 4d 18          	mov    rcx,QWORD PTR [r13+0x18]
    1da9:	0f b7 14 56          	movzx  edx,WORD PTR [rsi+rdx*2]
    1dad:	41 8b 75 04          	mov    esi,DWORD PTR [r13+0x4]
    1db1:	01 d2                	add    edx,edx
    1db3:	41 89 d0             	mov    r8d,edx
    1db6:	41 29 f0             	sub    r8d,esi
    1db9:	39 f2                	cmp    edx,esi
    1dbb:	41 0f 43 d0          	cmovae edx,r8d
    1dbf:	48 63 d2             	movsxd rdx,edx
    1dc2:	0f b7 14 51          	movzx  edx,WORD PTR [rcx+rdx*2]
    1dc6:	89 54 c3 04          	mov    DWORD PTR [rbx+rax*8+0x4],edx
    1dca:	c7 44 c3 08 00 00 00 00 	mov    DWORD PTR [rbx+rax*8+0x8],0x0
    1dd2:	48 83 e8 01          	sub    rax,0x1
    1dd6:	85 c0                	test   eax,eax
    1dd8:	79 b6                	jns    1d90 <find_poly_roots+0x450>
    1dda:	41 3b 3c 24          	cmp    edi,DWORD PTR [r12]
    1dde:	76 04                	jbe    1de4 <find_poly_roots+0x4a4>
    1de0:	41 89 3c 24          	mov    DWORD PTR [r12],edi
    1de4:	45 39 fe             	cmp    r14d,r15d
    1de7:	7c 67                	jl     1e50 <find_poly_roots+0x510>
    1de9:	41 83 c6 01          	add    r14d,0x1
    1ded:	44 39 f5             	cmp    ebp,r14d
    1df0:	75 8e                	jne    1d80 <find_poly_roots+0x440>
    1df2:	44 8b 74 24 2c       	mov    r14d,DWORD PTR [rsp+0x2c]
    1df7:	4c 8b 44 24 38       	mov    r8,QWORD PTR [rsp+0x38]
    1dfc:	4c 89 e5             	mov    rbp,r12
    1dff:	4d 89 ec             	mov    r12,r13
    1e02:	4d 89 d5             	mov    r13,r10
    1e05:	8b 55 00             	mov    edx,DWORD PTR [rbp+0x0]
    1e08:	8b 4c 95 04          	mov    ecx,DWORD PTR [rbp+rdx*4+0x4]
    1e0c:	48 89 d0             	mov    rax,rdx
    1e0f:	85 c9                	test   ecx,ecx
    1e11:	74 16                	je     1e29 <find_poly_roots+0x4e9>
    1e13:	eb 5f                	jmp    1e74 <find_poly_roots+0x534>
    1e15:	0f 1f 00             	nop    DWORD PTR [rax]
    1e18:	8d 50 ff             	lea    edx,[rax-0x1]
    1e1b:	89 55 00             	mov    DWORD PTR [rbp+0x0],edx
    1e1e:	48 89 d0             	mov    rax,rdx
    1e21:	8b 54 95 04          	mov    edx,DWORD PTR [rbp+rdx*4+0x4]
    1e25:	85 d2                	test   edx,edx
    1e27:	75 4b                	jne    1e74 <find_poly_roots+0x534>
    1e29:	85 c0                	test   eax,eax
    1e2b:	75 eb                	jne    1e18 <find_poly_roots+0x4d8>
    1e2d:	4c 89 e8             	mov    rax,r13
    1e30:	83 44 24 10 01       	add    DWORD PTR [rsp+0x10],0x1
    1e35:	45 89 f5             	mov    r13d,r14d
    1e38:	49 89 c6             	mov    r14,rax
    1e3b:	44 01 6c 24 28       	add    DWORD PTR [rsp+0x28],r13d
    1e40:	8b 00                	mov    eax,DWORD PTR [rax]
    1e42:	e9 20 fb ff ff       	jmp    1967 <find_poly_roots+0x27>
    1e47:	66 0f 1f 84 00 00 00 00 00 	nop    WORD PTR [rax+rax*1+0x0]
    1e50:	48 8b 4c 24 20       	mov    rcx,QWORD PTR [rsp+0x20]
    1e55:	4c 89 d2             	mov    rdx,r10
    1e58:	d1 23                	shl    DWORD PTR [rbx],1
    1e5a:	48 89 de             	mov    rsi,rbx
    1e5d:	4c 89 ef             	mov    rdi,r13
    1e60:	4c 89 54 24 18       	mov    QWORD PTR [rsp+0x18],r10
    1e65:	e8 a6 f4 ff ff       	call   1310 <gf_poly_mod>
    1e6a:	4c 8b 54 24 18       	mov    r10,QWORD PTR [rsp+0x18]
    1e6f:	e9 75 ff ff ff       	jmp    1de9 <find_poly_roots+0x4a9>
    1e74:	85 c0                	test   eax,eax
    1e76:	74 b5                	je     1e2d <find_poly_roots+0x4ed>
    1e78:	41 8b 45 00          	mov    eax,DWORD PTR [r13+0x0]
    1e7c:	4c 89 c7             	mov    rdi,r8
    1e7f:	4c 89 ee             	mov    rsi,r13
    1e82:	83 c0 01             	add    eax,0x1
    1e85:	48 8d 14 85 04 00 00 00 	lea    rdx,[rax*4+0x4]
    1e8d:	e8 4e f2 ff ff       	call   10e0 <memcpy@plt>
    1e92:	8b 55 00             	mov    edx,DWORD PTR [rbp+0x0]
    1e95:	49 89 c0             	mov    r8,rax
    1e98:	8b 00                	mov    eax,DWORD PTR [rax]
    1e9a:	39 d0                	cmp    eax,edx
    1e9c:	0f 83 c8 03 00 00    	jae    226a <find_poly_roots+0x92a>
    1ea2:	4c 89 c3             	mov    rbx,r8
    1ea5:	85 c0                	test   eax,eax
    1ea7:	75 10                	jne    1eb9 <find_poly_roots+0x579>
    1ea9:	e9 d3 03 00 00       	jmp    2281 <find_poly_roots+0x941>
    1eae:	66 90                	xchg   ax,ax
    1eb0:	48 89 e8             	mov    rax,rbp
    1eb3:	48 89 dd             	mov    rbp,rbx
    1eb6:	48 89 c3             	mov    rbx,rax
    1eb9:	31 c9                	xor    ecx,ecx
    1ebb:	48 89 da             	mov    rdx,rbx
    1ebe:	48 89 ee             	mov    rsi,rbp
    1ec1:	4c 89 e7             	mov    rdi,r12
    1ec4:	e8 47 f4 ff ff       	call   1310 <gf_poly_mod>
    1ec9:	8b 45 00             	mov    eax,DWORD PTR [rbp+0x0]
    1ecc:	85 c0                	test   eax,eax
    1ece:	75 e0                	jne    1eb0 <find_poly_roots+0x570>
    1ed0:	49 89 d8             	mov    r8,rbx
    1ed3:	41 8b 10             	mov    edx,DWORD PTR [r8]
    1ed6:	41 8b 45 00          	mov    eax,DWORD PTR [r13+0x0]
    1eda:	83 44 24 10 01       	add    DWORD PTR [rsp+0x10],0x1
    1edf:	39 c2                	cmp    edx,eax
    1ee1:	72 13                	jb     1ef6 <find_poly_roots+0x5b6>
    1ee3:	4c 89 e9             	mov    rcx,r13
    1ee6:	45 89 f5             	mov    r13d,r14d
    1ee9:	44 01 6c 24 28       	add    DWORD PTR [rsp+0x28],r13d
    1eee:	49 89 ce             	mov    r14,rcx
    1ef1:	e9 71 fa ff ff       	jmp    1967 <find_poly_roots+0x27>
    1ef6:	4c 8b 7c 24 30       	mov    r15,QWORD PTR [rsp+0x30]
    1efb:	29 d0                	sub    eax,edx
    1efd:	31 c9                	xor    ecx,ecx
    1eff:	4c 89 c2             	mov    rdx,r8
    1f02:	4c 89 ee             	mov    rsi,r13
    1f05:	4c 89 e7             	mov    rdi,r12
    1f08:	4c 89 44 24 18       	mov    QWORD PTR [rsp+0x18],r8
    1f0d:	41 89 07             	mov    DWORD PTR [r15],eax
    1f10:	e8 fb f3 ff ff       	call   1310 <gf_poly_mod>
    1f15:	41 8b 07             	mov    eax,DWORD PTR [r15]
    1f18:	4c 8b 44 24 18       	mov    r8,QWORD PTR [rsp+0x18]
    1f1d:	49 8d 7f 04          	lea    rdi,[r15+0x4]
    1f21:	8d 50 01             	lea    edx,[rax+0x1]
    1f24:	41 8b 00             	mov    eax,DWORD PTR [r8]
    1f27:	48 c1 e2 02          	shl    rdx,0x2
    1f2b:	49 8d 74 85 04       	lea    rsi,[r13+rax*4+0x4]
    1f30:	e8 ab f1 ff ff       	call   10e0 <memcpy@plt>
    1f35:	4c 8b 44 24 18       	mov    r8,QWORD PTR [rsp+0x18]
    1f3a:	4c 89 ef             	mov    rdi,r13
    1f3d:	41 8b 10             	mov    edx,DWORD PTR [r8]
    1f40:	4c 89 c6             	mov    rsi,r8
    1f43:	48 89 d0             	mov    rax,rdx
    1f46:	48 8d 14 52          	lea    rdx,[rdx+rdx*2]
    1f4a:	83 c0 01             	add    eax,0x1
    1f4d:	49 8d 5c 95 00       	lea    rbx,[r13+rdx*4+0x0]
    1f52:	48 8d 14 85 04 00 00 00 	lea    rdx,[rax*4+0x4]
    1f5a:	e8 81 f1 ff ff       	call   10e0 <memcpy@plt>
    1f5f:	41 8b 07             	mov    eax,DWORD PTR [r15]
    1f62:	4c 89 fe             	mov    rsi,r15
    1f65:	48 89 df             	mov    rdi,rbx
    1f68:	83 c0 01             	add    eax,0x1
    1f6b:	48 8d 14 85 04 00 00 00 	lea    rdx,[rax*4+0x4]
    1f73:	e8 68 f1 ff ff       	call   10e0 <memcpy@plt>
    1f78:	4c 8b 7c 24 08       	mov    r15,QWORD PTR [rsp+0x8]
    1f7d:	4c 89 ea             	mov    rdx,r13
    1f80:	4c 89 e7             	mov    rdi,r12
    1f83:	8b 74 24 10          	mov    esi,DWORD PTR [rsp+0x10]
    1f87:	49 89 dd             	mov    r13,rbx
    1f8a:	4c 89 f9             	mov    rcx,r15
    1f8d:	e8 ae f9 ff ff       	call   1940 <find_poly_roots>
    1f92:	48 63 d0             	movsxd rdx,eax
    1f95:	41 01 c6             	add    r14d,eax
    1f98:	8b 03                	mov    eax,DWORD PTR [rbx]
    1f9a:	49 8d 3c 97          	lea    rdi,[r15+rdx*4]
    1f9e:	48 89 7c 24 08       	mov    QWORD PTR [rsp+0x8],rdi
    1fa3:	e9 cb f9 ff ff       	jmp    1973 <find_poly_roots+0x33>
    1fa8:	45 31 ff             	xor    r15d,r15d
    1fab:	e9 dd fa ff ff       	jmp    1a8d <find_poly_roots+0x14d>
    1fb0:	85 d2                	test   edx,edx
    1fb2:	0f 84 04 01 00 00    	je     20bc <find_poly_roots+0x77c>
    1fb8:	0f b7 0c 53          	movzx  ecx,WORD PTR [rbx+rdx*2]
    1fbc:	45 0f b7 cf          	movzx  r9d,r15w
    1fc0:	42 0f b7 14 4b       	movzx  edx,WORD PTR [rbx+r9*2]
    1fc5:	41 89 e9             	mov    r9d,ebp
    1fc8:	01 c1                	add    ecx,eax
    1fca:	29 d1                	sub    ecx,edx
    1fcc:	89 54 24 10          	mov    DWORD PTR [rsp+0x10],edx
    1fd0:	89 ca                	mov    edx,ecx
    1fd2:	29 c2                	sub    edx,eax
    1fd4:	39 c8                	cmp    eax,ecx
    1fd6:	0f 47 d1             	cmova  edx,ecx
    1fd9:	48 63 d2             	movsxd rdx,edx
    1fdc:	41 0f b7 54 55 00    	movzx  edx,WORD PTR [r13+rdx*2+0x0]
    1fe2:	0f b7 0c 53          	movzx  ecx,WORD PTR [rbx+rdx*2]
    1fe6:	49 89 d3             	mov    r11,rdx
    1fe9:	89 ca                	mov    edx,ecx
    1feb:	89 4c 24 18          	mov    DWORD PTR [rsp+0x18],ecx
    1fef:	83 e2 01             	and    edx,0x1
    1ff2:	44 0f 45 c8          	cmovne r9d,eax
    1ff6:	41 01 c9             	add    r9d,ecx
    1ff9:	41 8b 0c 24          	mov    ecx,DWORD PTR [r12]
    1ffd:	45 89 ca             	mov    r10d,r9d
    2000:	41 c1 ea 1f          	shr    r10d,0x1f
    2004:	45 01 ca             	add    r10d,r9d
    2007:	41 d1 fa             	sar    r10d,1
    200a:	44 89 d2             	mov    edx,r10d
    200d:	44 39 d0             	cmp    eax,r10d
    2010:	77 1a                	ja     202c <find_poly_roots+0x6ec>
    2012:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    2018:	29 c2                	sub    edx,eax
    201a:	41 89 c2             	mov    r10d,eax
    201d:	41 21 d2             	and    r10d,edx
    2020:	d3 ea                	shr    edx,cl
    2022:	44 01 d2             	add    edx,r10d
    2025:	39 d0                	cmp    eax,edx
    2027:	76 ef                	jbe    2018 <find_poly_roots+0x6d8>
    2029:	41 89 d2             	mov    r10d,edx
    202c:	4d 63 d2             	movsxd r10,r10d
    202f:	45 01 c9             	add    r9d,r9d
    2032:	43 0f b7 6c 55 00    	movzx  ebp,WORD PTR [r13+r10*2+0x0]
    2038:	44 89 ca             	mov    edx,r9d
    203b:	49 89 ea             	mov    r10,rbp
    203e:	44 39 c8             	cmp    eax,r9d
    2041:	77 19                	ja     205c <find_poly_roots+0x71c>
    2043:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    2048:	29 c2                	sub    edx,eax
    204a:	41 89 c1             	mov    r9d,eax
    204d:	41 21 d1             	and    r9d,edx
    2050:	d3 ea                	shr    edx,cl
    2052:	44 01 ca             	add    edx,r9d
    2055:	39 d0                	cmp    eax,edx
    2057:	76 ef                	jbe    2048 <find_poly_roots+0x708>
    2059:	41 89 d1             	mov    r9d,edx
    205c:	4d 63 c9             	movsxd r9,r9d
    205f:	47 0f b7 4c 4d 00    	movzx  r9d,WORD PTR [r13+r9*2+0x0]
    2065:	85 f6                	test   esi,esi
    2067:	0f 84 0d 02 00 00    	je     227a <find_poly_roots+0x93a>
    206d:	66 45 85 db          	test   r11w,r11w
    2071:	0f 84 03 02 00 00    	je     227a <find_poly_roots+0x93a>
    2077:	89 f2                	mov    edx,esi
    2079:	0f b7 14 53          	movzx  edx,WORD PTR [rbx+rdx*2]
    207d:	03 54 24 18          	add    edx,DWORD PTR [rsp+0x18]
    2081:	89 d1                	mov    ecx,edx
    2083:	29 c1                	sub    ecx,eax
    2085:	39 d0                	cmp    eax,edx
    2087:	0f 46 d1             	cmovbe edx,ecx
    208a:	48 63 d2             	movsxd rdx,edx
    208d:	41 0f b7 54 55 00    	movzx  edx,WORD PTR [r13+rdx*2+0x0]
    2093:	44 31 cf             	xor    edi,r9d
    2096:	0f b7 cf             	movzx  ecx,di
    2099:	31 d1                	xor    ecx,edx
    209b:	85 ed                	test   ebp,ebp
    209d:	74 1d                	je     20bc <find_poly_roots+0x77c>
    209f:	42 0f b7 14 53       	movzx  edx,WORD PTR [rbx+r10*2]
    20a4:	03 54 24 10          	add    edx,DWORD PTR [rsp+0x10]
    20a8:	89 d7                	mov    edi,edx
    20aa:	29 c7                	sub    edi,eax
    20ac:	39 d0                	cmp    eax,edx
    20ae:	0f 46 d7             	cmovbe edx,edi
    20b1:	48 63 d2             	movsxd rdx,edx
    20b4:	41 0f b7 54 55 00    	movzx  edx,WORD PTR [r13+rdx*2+0x0]
    20ba:	31 d6                	xor    esi,edx
    20bc:	85 c9                	test   ecx,ecx
    20be:	0f 84 e3 f8 ff ff    	je     19a7 <find_poly_roots+0x67>
    20c4:	89 ca                	mov    edx,ecx
    20c6:	0f b7 3c 53          	movzx  edi,WORD PTR [rbx+rdx*2]
    20ca:	89 c2                	mov    edx,eax
    20cc:	29 fa                	sub    edx,edi
    20ce:	41 0f b7 4c 55 00    	movzx  ecx,WORD PTR [r13+rdx*2+0x0]
    20d4:	42 0f b7 14 43       	movzx  edx,WORD PTR [rbx+r8*2]
    20d9:	01 c2                	add    edx,eax
    20db:	29 fa                	sub    edx,edi
    20dd:	41 89 d0             	mov    r8d,edx
    20e0:	41 29 c0             	sub    r8d,eax
    20e3:	39 d0                	cmp    eax,edx
    20e5:	41 0f 46 d0          	cmovbe edx,r8d
    20e9:	48 63 d2             	movsxd rdx,edx
    20ec:	41 0f b7 54 55 00    	movzx  edx,WORD PTR [r13+rdx*2+0x0]
    20f2:	85 f6                	test   esi,esi
    20f4:	0f 84 93 f9 ff ff    	je     1a8d <find_poly_roots+0x14d>
    20fa:	0f b7 34 73          	movzx  esi,WORD PTR [rbx+rsi*2]
    20fe:	01 c6                	add    esi,eax
    2100:	29 fe                	sub    esi,edi
    2102:	89 f7                	mov    edi,esi
    2104:	29 c7                	sub    edi,eax
    2106:	39 f0                	cmp    eax,esi
    2108:	89 f0                	mov    eax,esi
    210a:	0f 46 c7             	cmovbe eax,edi
    210d:	48 98                	cdqe   
    210f:	41 0f b7 74 45 00    	movzx  esi,WORD PTR [r13+rax*2+0x0]
    2115:	e9 73 f9 ff ff       	jmp    1a8d <find_poly_roots+0x14d>
    211a:	4d 8b 6c 24 20       	mov    r13,QWORD PTR [r12+0x20]
    211f:	41 8b 77 0c          	mov    esi,DWORD PTR [r15+0xc]
    2123:	41 8b 54 24 04       	mov    edx,DWORD PTR [r12+0x4]
    2128:	45 8b 04 24          	mov    r8d,DWORD PTR [r12]
    212c:	41 0f b7 7c 4d 00    	movzx  edi,WORD PTR [r13+rcx*2+0x0]
    2132:	41 0f b7 44 45 00    	movzx  eax,WORD PTR [r13+rax*2+0x0]
    2138:	41 0f b7 4c 75 00    	movzx  ecx,WORD PTR [r13+rsi*2+0x0]
    213e:	89 7c 24 18          	mov    DWORD PTR [rsp+0x18],edi
    2142:	01 c8                	add    eax,ecx
    2144:	89 4c 24 20          	mov    DWORD PTR [rsp+0x20],ecx
    2148:	89 d1                	mov    ecx,edx
    214a:	29 f9                	sub    ecx,edi
    214c:	49 8b 7c 24 18       	mov    rdi,QWORD PTR [r12+0x18]
    2151:	8d 04 48             	lea    eax,[rax+rcx*2]
    2154:	48 89 7c 24 10       	mov    QWORD PTR [rsp+0x10],rdi
    2159:	39 c2                	cmp    edx,eax
    215b:	77 14                	ja     2171 <find_poly_roots+0x831>
    215d:	44 89 c1             	mov    ecx,r8d
    2160:	29 d0                	sub    eax,edx
    2162:	89 d6                	mov    esi,edx
    2164:	21 c6                	and    esi,eax
    2166:	d3 e8                	shr    eax,cl
    2168:	01 f0                	add    eax,esi
    216a:	39 c2                	cmp    edx,eax
    216c:	76 f2                	jbe    2160 <find_poly_roots+0x820>
    216e:	41 89 c8             	mov    r8d,ecx
    2171:	48 8b 4c 24 10       	mov    rcx,QWORD PTR [rsp+0x10]
    2176:	48 98                	cdqe   
    2178:	44 0f b7 3c 41       	movzx  r15d,WORD PTR [rcx+rax*2]
    217d:	45 85 ff             	test   r15d,r15d
    2180:	0f 84 03 01 00 00    	je     2289 <find_poly_roots+0x949>
    2186:	49 8b 5c 24 40       	mov    rbx,QWORD PTR [r12+0x40]
    218b:	44 89 f8             	mov    eax,r15d
    218e:	31 f6                	xor    esi,esi
    2190:	41 bb 1f 00 00 00    	mov    r11d,0x1f
    2196:	41 ba 01 00 00 00    	mov    r10d,0x1
    219c:	0f 1f 40 00          	nop    DWORD PTR [rax+0x0]
    21a0:	0f bd f8             	bsr    edi,eax
    21a3:	44 89 d9             	mov    ecx,r11d
    21a6:	44 89 d5             	mov    ebp,r10d
    21a9:	41 89 f1             	mov    r9d,esi
    21ac:	83 f7 1f             	xor    edi,0x1f
    21af:	29 f9                	sub    ecx,edi
    21b1:	48 63 f9             	movsxd rdi,ecx
    21b4:	d3 e5                	shl    ebp,cl
    21b6:	8b 3c bb             	mov    edi,DWORD PTR [rbx+rdi*4]
    21b9:	89 e9                	mov    ecx,ebp
    21bb:	89 c5                	mov    ebp,eax
    21bd:	31 c8                	xor    eax,ecx
    21bf:	31 fe                	xor    esi,edi
    21c1:	39 e9                	cmp    ecx,ebp
    21c3:	75 db                	jne    21a0 <find_poly_roots+0x860>
    21c5:	44 39 cf             	cmp    edi,r9d
    21c8:	0f 84 d9 f7 ff ff    	je     19a7 <find_poly_roots+0x67>
    21ce:	89 f0                	mov    eax,esi
    21d0:	41 0f b7 4c 45 00    	movzx  ecx,WORD PTR [r13+rax*2+0x0]
    21d6:	8d 04 09             	lea    eax,[rcx+rcx*1]
    21d9:	89 c7                	mov    edi,eax
    21db:	29 d7                	sub    edi,edx
    21dd:	39 c2                	cmp    edx,eax
    21df:	0f 46 c7             	cmovbe eax,edi
    21e2:	48 8b 7c 24 10       	mov    rdi,QWORD PTR [rsp+0x10]
    21e7:	48 98                	cdqe   
    21e9:	0f b7 04 47          	movzx  eax,WORD PTR [rdi+rax*2]
    21ed:	31 f0                	xor    eax,esi
    21ef:	44 39 f8             	cmp    eax,r15d
    21f2:	0f 85 af f7 ff ff    	jne    19a7 <find_poly_roots+0x67>
    21f8:	89 f0                	mov    eax,esi
    21fa:	83 f0 01             	xor    eax,0x1
    21fd:	48 01 c0             	add    rax,rax
    2200:	8b 7c 24 20          	mov    edi,DWORD PTR [rsp+0x20]
    2204:	8d 34 57             	lea    esi,[rdi+rdx*2]
    2207:	2b 74 24 18          	sub    esi,DWORD PTR [rsp+0x18]
    220b:	29 ce                	sub    esi,ecx
    220d:	39 f2                	cmp    edx,esi
    220f:	77 11                	ja     2222 <find_poly_roots+0x8e2>
    2211:	44 89 c1             	mov    ecx,r8d
    2214:	29 d6                	sub    esi,edx
    2216:	89 d7                	mov    edi,edx
    2218:	21 f7                	and    edi,esi
    221a:	d3 ee                	shr    esi,cl
    221c:	01 fe                	add    esi,edi
    221e:	39 f2                	cmp    edx,esi
    2220:	76 f2                	jbe    2214 <find_poly_roots+0x8d4>
    2222:	48 8b 4c 24 08       	mov    rcx,QWORD PTR [rsp+0x8]
    2227:	89 31                	mov    DWORD PTR [rcx],esi
    2229:	8b 4c 24 20          	mov    ecx,DWORD PTR [rsp+0x20]
    222d:	41 8b 74 24 04       	mov    esi,DWORD PTR [r12+0x4]
    2232:	8d 14 71             	lea    edx,[rcx+rsi*2]
    2235:	41 0f b7 4c 05 00    	movzx  ecx,WORD PTR [r13+rax*1+0x0]
    223b:	2b 54 24 18          	sub    edx,DWORD PTR [rsp+0x18]
    223f:	89 d0                	mov    eax,edx
    2241:	29 c8                	sub    eax,ecx
    2243:	39 c6                	cmp    esi,eax
    2245:	77 12                	ja     2259 <find_poly_roots+0x919>
    2247:	41 8b 0c 24          	mov    ecx,DWORD PTR [r12]
    224b:	29 f0                	sub    eax,esi
    224d:	89 f2                	mov    edx,esi
    224f:	21 c2                	and    edx,eax
    2251:	d3 e8                	shr    eax,cl
    2253:	01 d0                	add    eax,edx
    2255:	39 c6                	cmp    esi,eax
    2257:	76 f2                	jbe    224b <find_poly_roots+0x90b>
    2259:	48 8b 4c 24 08       	mov    rcx,QWORD PTR [rsp+0x8]
    225e:	41 83 c6 02          	add    r14d,0x2
    2262:	89 41 04             	mov    DWORD PTR [rcx+0x4],eax
    2265:	e9 3d f7 ff ff       	jmp    19a7 <find_poly_roots+0x67>
    226a:	89 d0                	mov    eax,edx
    226c:	48 89 ea             	mov    rdx,rbp
    226f:	4c 89 c5             	mov    rbp,r8
    2272:	49 89 d0             	mov    r8,rdx
    2275:	e9 28 fc ff ff       	jmp    1ea2 <find_poly_roots+0x562>
    227a:	31 d2                	xor    edx,edx
    227c:	e9 12 fe ff ff       	jmp    2093 <find_poly_roots+0x753>
    2281:	49 89 e8             	mov    r8,rbp
    2284:	e9 4a fc ff ff       	jmp    1ed3 <find_poly_roots+0x593>
    2289:	41 0f b7 4d 00       	movzx  ecx,WORD PTR [r13+0x0]
    228e:	b8 02 00 00 00       	mov    eax,0x2
    2293:	e9 68 ff ff ff       	jmp    2200 <find_poly_roots+0x8c0>
    2298:	45 31 d2             	xor    r10d,r10d
    229b:	45 85 c9             	test   r9d,r9d
    229e:	74 09                	je     22a9 <find_poly_roots+0x969>
    22a0:	40 84 f6             	test   sil,sil
    22a3:	0f 85 24 f9 ff ff    	jne    1bcd <find_poly_roots+0x28d>
    22a9:	85 ed                	test   ebp,ebp
    22ab:	0f 84 55 f9 ff ff    	je     1c06 <find_poly_roots+0x2c6>
    22b1:	42 0f b7 34 43       	movzx  esi,WORD PTR [rbx+r8*2]
    22b6:	e9 36 f9 ff ff       	jmp    1bf1 <find_poly_roots+0x2b1>

Disassembly of section .fini:
