
/home/zzk/BinaryKernelCodeMapping/test/test_BCH/build/libbch-kernel-native.so:     file format elf64-x86-64


Disassembly of section .init:

Disassembly of section .plt:

Disassembly of section .plt.got:

Disassembly of section .plt.sec:

Disassembly of section .text:

0000000000002720 <bch_decode>:
    2720:	f3 0f 1e fa          	endbr64 
    2724:	41 57                	push   r15
    2726:	41 89 d2             	mov    r10d,edx
    2729:	41 56                	push   r14
    272b:	41 55                	push   r13
    272d:	41 54                	push   r12
    272f:	49 89 cc             	mov    r12,rcx
    2732:	8d 0c d5 00 00 00 00 	lea    ecx,[rdx*8+0x0]
    2739:	55                   	push   rbp
    273a:	53                   	push   rbx
    273b:	48 83 ec 48          	sub    rsp,0x48
    273f:	8b 47 04             	mov    eax,DWORD PTR [rdi+0x4]
    2742:	8b 2f                	mov    ebp,DWORD PTR [rdi]
    2744:	89 4c 24 2c          	mov    DWORD PTR [rsp+0x2c],ecx
    2748:	44 8b 7f 08          	mov    r15d,DWORD PTR [rdi+0x8]
    274c:	89 44 24 14          	mov    DWORD PTR [rsp+0x14],eax
    2750:	2b 47 0c             	sub    eax,DWORD PTR [rdi+0xc]
    2753:	39 c1                	cmp    ecx,eax
    2755:	0f 87 d5 04 00 00    	ja     2c30 <bch_decode+0x510>
    275b:	48 89 fb             	mov    rbx,rdi
    275e:	4d 89 ce             	mov    r14,r9
    2761:	4d 85 c9             	test   r9,r9
    2764:	0f 84 6a 02 00 00    	je     29d4 <bch_decode+0x2b4>
    276a:	48 8b 43 68          	mov    rax,QWORD PTR [rbx+0x68]
    276e:	4c 8b 5b 60          	mov    r11,QWORD PTR [rbx+0x60]
    2772:	31 f6                	xor    esi,esi
    2774:	48 8b 6b 58          	mov    rbp,QWORD PTR [rbx+0x58]
    2778:	45 8b 2e             	mov    r13d,DWORD PTR [r14]
    277b:	48 89 44 24 18       	mov    QWORD PTR [rsp+0x18],rax
    2780:	43 8d 44 3f 01       	lea    eax,[r15+r15*1+0x1]
    2785:	4c 89 df             	mov    rdi,r11
    2788:	4c 8d 24 85 04 00 00 00 	lea    r12,[rax*4+0x4]
    2790:	4c 89 5c 24 08       	mov    QWORD PTR [rsp+0x8],r11
    2795:	4c 89 e2             	mov    rdx,r12
    2798:	e8 13 e9 ff ff       	call   10b0 <memset@plt>
    279d:	4c 89 e2             	mov    rdx,r12
    27a0:	31 f6                	xor    esi,esi
    27a2:	48 89 ef             	mov    rdi,rbp
    27a5:	e8 06 e9 ff ff       	call   10b0 <memset@plt>
    27aa:	4c 8b 5c 24 08       	mov    r11,QWORD PTR [rsp+0x8]
    27af:	48 b8 00 00 00 00 01 00 00 00 	movabs rax,0x100000000
    27b9:	49 89 03             	mov    QWORD PTR [r11],rax
    27bc:	48 89 45 00          	mov    QWORD PTR [rbp+0x0],rax
    27c0:	45 85 ff             	test   r15d,r15d
    27c3:	0f 84 77 03 00 00    	je     2b40 <bch_decode+0x420>
    27c9:	41 8d 47 ff          	lea    eax,[r15-0x1]
    27cd:	c7 44 24 28 ff ff ff ff 	mov    DWORD PTR [rsp+0x28],0xffffffff
    27d5:	45 31 e4             	xor    r12d,r12d
    27d8:	31 c9                	xor    ecx,ecx
    27da:	89 44 24 08          	mov    DWORD PTR [rsp+0x8],eax
    27de:	c7 44 24 20 01 00 00 00 	mov    DWORD PTR [rsp+0x20],0x1
    27e6:	eb 15                	jmp    27fd <bch_decode+0xdd>
    27e8:	41 39 ff             	cmp    r15d,edi
    27eb:	0f 84 93 00 00 00    	je     2884 <bch_decode+0x164>
    27f1:	41 39 cf             	cmp    r15d,ecx
    27f4:	0f 82 cf 01 00 00    	jb     29c9 <bch_decode+0x2a9>
    27fa:	41 89 fc             	mov    r12d,edi
    27fd:	45 85 ed             	test   r13d,r13d
    2800:	0f 85 aa 00 00 00    	jne    28b0 <bch_decode+0x190>
    2806:	8b 4d 00             	mov    ecx,DWORD PTR [rbp+0x0]
    2809:	41 8d 7c 24 01       	lea    edi,[r12+0x1]
    280e:	44 3b 64 24 08       	cmp    r12d,DWORD PTR [rsp+0x8]
    2813:	73 d3                	jae    27e8 <bch_decode+0xc8>
    2815:	8d 04 3f             	lea    eax,[rdi+rdi*1]
    2818:	45 8b 2c 86          	mov    r13d,DWORD PTR [r14+rax*4]
    281c:	49 89 c0             	mov    r8,rax
    281f:	85 c9                	test   ecx,ecx
    2821:	0f 84 d0 03 00 00    	je     2bf7 <bch_decode+0x4d7>
    2827:	b8 01 00 00 00       	mov    eax,0x1
    282c:	44 89 c2             	mov    edx,r8d
    282f:	29 c2                	sub    edx,eax
    2831:	45 8b 0c 96          	mov    r9d,DWORD PTR [r14+rdx*4]
    2835:	89 c2                	mov    edx,eax
    2837:	8b 54 95 04          	mov    edx,DWORD PTR [rbp+rdx*4+0x4]
    283b:	85 d2                	test   edx,edx
    283d:	74 35                	je     2874 <bch_decode+0x154>
    283f:	45 85 c9             	test   r9d,r9d
    2842:	74 30                	je     2874 <bch_decode+0x154>
    2844:	4c 8b 53 20          	mov    r10,QWORD PTR [rbx+0x20]
    2848:	48 8b 73 18          	mov    rsi,QWORD PTR [rbx+0x18]
    284c:	47 0f b7 0c 4a       	movzx  r9d,WORD PTR [r10+r9*2]
    2851:	41 0f b7 14 52       	movzx  edx,WORD PTR [r10+rdx*2]
    2856:	44 01 ca             	add    edx,r9d
    2859:	44 8b 4b 04          	mov    r9d,DWORD PTR [rbx+0x4]
    285d:	41 89 d2             	mov    r10d,edx
    2860:	45 29 ca             	sub    r10d,r9d
    2863:	44 39 ca             	cmp    edx,r9d
    2866:	41 0f 43 d2          	cmovae edx,r10d
    286a:	48 63 d2             	movsxd rdx,edx
    286d:	0f b7 14 56          	movzx  edx,WORD PTR [rsi+rdx*2]
    2871:	41 31 d5             	xor    r13d,edx
    2874:	83 c0 01             	add    eax,0x1
    2877:	39 c8                	cmp    eax,ecx
    2879:	76 b1                	jbe    282c <bch_decode+0x10c>
    287b:	41 39 ff             	cmp    r15d,edi
    287e:	0f 85 6d ff ff ff    	jne    27f1 <bch_decode+0xd1>
    2884:	41 39 cf             	cmp    r15d,ecx
    2887:	0f 82 3c 01 00 00    	jb     29c9 <bch_decode+0x2a9>
    288d:	41 89 cc             	mov    r12d,ecx
    2890:	85 c9                	test   ecx,ecx
    2892:	0f 8f 0f 01 00 00    	jg     29a7 <bch_decode+0x287>
    2898:	0f 85 2b 01 00 00    	jne    29c9 <bch_decode+0x2a9>
    289e:	48 83 c4 48          	add    rsp,0x48
    28a2:	44 89 e0             	mov    eax,r12d
    28a5:	5b                   	pop    rbx
    28a6:	5d                   	pop    rbp
    28a7:	41 5c                	pop    r12
    28a9:	41 5d                	pop    r13
    28ab:	41 5e                	pop    r14
    28ad:	41 5f                	pop    r15
    28af:	c3                   	ret    
    28b0:	43 8d 04 24          	lea    eax,[r12+r12*1]
    28b4:	48 8b 7c 24 18       	mov    rdi,QWORD PTR [rsp+0x18]
    28b9:	48 89 ee             	mov    rsi,rbp
    28bc:	4c 89 5c 24 38       	mov    QWORD PTR [rsp+0x38],r11
    28c1:	89 44 24 34          	mov    DWORD PTR [rsp+0x34],eax
    28c5:	2b 44 24 28          	sub    eax,DWORD PTR [rsp+0x28]
    28c9:	89 44 24 24          	mov    DWORD PTR [rsp+0x24],eax
    28cd:	8d 41 01             	lea    eax,[rcx+0x1]
    28d0:	48 8d 14 85 04 00 00 00 	lea    rdx,[rax*4+0x4]
    28d8:	e8 03 e8 ff ff       	call   10e0 <memcpy@plt>
    28dd:	4c 8b 4b 20          	mov    r9,QWORD PTR [rbx+0x20]
    28e1:	8b 54 24 20          	mov    edx,DWORD PTR [rsp+0x20]
    28e5:	44 89 e8             	mov    eax,r13d
    28e8:	4c 8b 5c 24 38       	mov    r11,QWORD PTR [rsp+0x38]
    28ed:	31 ff                	xor    edi,edi
    28ef:	41 0f b7 14 51       	movzx  edx,WORD PTR [r9+rdx*2]
    28f4:	41 0f b7 04 41       	movzx  eax,WORD PTR [r9+rax*2]
    28f9:	03 44 24 14          	add    eax,DWORD PTR [rsp+0x14]
    28fd:	45 8b 03             	mov    r8d,DWORD PTR [r11]
    2900:	29 d0                	sub    eax,edx
    2902:	89 44 24 30          	mov    DWORD PTR [rsp+0x30],eax
    2906:	eb 08                	jmp    2910 <bch_decode+0x1f0>
    2908:	83 c7 01             	add    edi,0x1
    290b:	41 39 f8             	cmp    r8d,edi
    290e:	72 50                	jb     2960 <bch_decode+0x240>
    2910:	89 f8                	mov    eax,edi
    2912:	41 8b 44 83 04       	mov    eax,DWORD PTR [r11+rax*4+0x4]
    2917:	85 c0                	test   eax,eax
    2919:	74 ed                	je     2908 <bch_decode+0x1e8>
    291b:	8b 53 04             	mov    edx,DWORD PTR [rbx+0x4]
    291e:	41 0f b7 04 41       	movzx  eax,WORD PTR [r9+rax*2]
    2923:	03 44 24 30          	add    eax,DWORD PTR [rsp+0x30]
    2927:	8b 0b                	mov    ecx,DWORD PTR [rbx]
    2929:	4c 8b 53 18          	mov    r10,QWORD PTR [rbx+0x18]
    292d:	39 d0                	cmp    eax,edx
    292f:	72 15                	jb     2946 <bch_decode+0x226>
    2931:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    2938:	29 d0                	sub    eax,edx
    293a:	89 d6                	mov    esi,edx
    293c:	21 c6                	and    esi,eax
    293e:	d3 e8                	shr    eax,cl
    2940:	01 f0                	add    eax,esi
    2942:	39 c2                	cmp    edx,eax
    2944:	76 f2                	jbe    2938 <bch_decode+0x218>
    2946:	8b 4c 24 24          	mov    ecx,DWORD PTR [rsp+0x24]
    294a:	48 98                	cdqe   
    294c:	8d 14 39             	lea    edx,[rcx+rdi*1]
    294f:	83 c7 01             	add    edi,0x1
    2952:	41 0f b7 0c 42       	movzx  ecx,WORD PTR [r10+rax*2]
    2957:	31 4c 95 04          	xor    DWORD PTR [rbp+rdx*4+0x4],ecx
    295b:	41 39 f8             	cmp    r8d,edi
    295e:	73 b0                	jae    2910 <bch_decode+0x1f0>
    2960:	8b 4d 00             	mov    ecx,DWORD PTR [rbp+0x0]
    2963:	44 03 44 24 24       	add    r8d,DWORD PTR [rsp+0x24]
    2968:	41 39 c8             	cmp    r8d,ecx
    296b:	0f 86 98 fe ff ff    	jbe    2809 <bch_decode+0xe9>
    2971:	48 8b 74 24 18       	mov    rsi,QWORD PTR [rsp+0x18]
    2976:	44 89 45 00          	mov    DWORD PTR [rbp+0x0],r8d
    297a:	4c 89 df             	mov    rdi,r11
    297d:	8b 06                	mov    eax,DWORD PTR [rsi]
    297f:	83 c0 01             	add    eax,0x1
    2982:	48 8d 14 85 04 00 00 00 	lea    rdx,[rax*4+0x4]
    298a:	e8 51 e7 ff ff       	call   10e0 <memcpy@plt>
    298f:	44 89 6c 24 20       	mov    DWORD PTR [rsp+0x20],r13d
    2994:	8b 4d 00             	mov    ecx,DWORD PTR [rbp+0x0]
    2997:	49 89 c3             	mov    r11,rax
    299a:	8b 44 24 34          	mov    eax,DWORD PTR [rsp+0x34]
    299e:	89 44 24 28          	mov    DWORD PTR [rsp+0x28],eax
    29a2:	e9 62 fe ff ff       	jmp    2809 <bch_decode+0xe9>
    29a7:	48 8b 53 58          	mov    rdx,QWORD PTR [rbx+0x58]
    29ab:	48 8b 8c 24 80 00 00 00 	mov    rcx,QWORD PTR [rsp+0x80]
    29b3:	be 01 00 00 00       	mov    esi,0x1
    29b8:	48 89 df             	mov    rdi,rbx
    29bb:	e8 80 ef ff ff       	call   1940 <find_poly_roots>
    29c0:	44 39 e0             	cmp    eax,r12d
    29c3:	0f 84 e6 01 00 00    	je     2baf <bch_decode+0x48f>
    29c9:	41 bc b6 ff ff ff    	mov    r12d,0xffffffb6
    29cf:	e9 ca fe ff ff       	jmp    289e <bch_decode+0x17e>
    29d4:	4c 89 c2             	mov    rdx,r8
    29d7:	4d 85 c0             	test   r8,r8
    29da:	0f 84 f7 00 00 00    	je     2ad7 <bch_decode+0x3b7>
    29e0:	48 8b 47 30          	mov    rax,QWORD PTR [rdi+0x30]
    29e4:	48 89 c6             	mov    rsi,rax
    29e7:	48 89 44 24 08       	mov    QWORD PTR [rsp+0x8],rax
    29ec:	e8 4f ea ff ff       	call   1440 <load_ecc8>
    29f1:	4d 85 e4             	test   r12,r12
    29f4:	0f 85 f9 00 00 00    	jne    2af3 <bch_decode+0x3d3>
    29fa:	8b 6b 0c             	mov    ebp,DWORD PTR [rbx+0xc]
    29fd:	8b 43 08             	mov    eax,DWORD PTR [rbx+0x8]
    2a00:	4c 8b 5b 48          	mov    r11,QWORD PTR [rbx+0x48]
    2a04:	89 ea                	mov    edx,ebp
    2a06:	89 44 24 14          	mov    DWORD PTR [rsp+0x14],eax
    2a0a:	83 e2 1f             	and    edx,0x1f
    2a0d:	0f 85 f5 01 00 00    	jne    2c08 <bch_decode+0x4e8>
    2a13:	8b 44 24 14          	mov    eax,DWORD PTR [rsp+0x14]
    2a17:	4c 89 df             	mov    rdi,r11
    2a1a:	31 f6                	xor    esi,esi
    2a1c:	44 8d 24 00          	lea    r12d,[rax+rax*1]
    2a20:	49 63 d4             	movsxd rdx,r12d
    2a23:	48 c1 e2 02          	shl    rdx,0x2
    2a27:	e8 84 e6 ff ff       	call   10b0 <memset@plt>
    2a2c:	49 89 c3             	mov    r11,rax
    2a2f:	41 8d 44 24 ff       	lea    eax,[r12-0x1]
    2a34:	d1 e8                	shr    eax,1
    2a36:	4d 8d 6c c3 08       	lea    r13,[r11+rax*8+0x8]
    2a3b:	48 83 44 24 08 04    	add    QWORD PTR [rsp+0x8],0x4
    2a41:	48 8b 44 24 08       	mov    rax,QWORD PTR [rsp+0x8]
    2a46:	83 ed 20             	sub    ebp,0x20
    2a49:	44 8b 70 fc          	mov    r14d,DWORD PTR [rax-0x4]
    2a4d:	45 85 f6             	test   r14d,r14d
    2a50:	0f 84 fa 00 00 00    	je     2b50 <bch_decode+0x430>
    2a56:	66 2e 0f 1f 84 00 00 00 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    2a60:	41 0f bd c6          	bsr    eax,r14d
    2a64:	41 bf 1f 00 00 00    	mov    r15d,0x1f
    2a6a:	83 f0 1f             	xor    eax,0x1f
    2a6d:	41 29 c7             	sub    r15d,eax
    2a70:	45 85 e4             	test   r12d,r12d
    2a73:	7e 49                	jle    2abe <bch_decode+0x39e>
    2a75:	42 8d 74 3d 00       	lea    esi,[rbp+r15*1+0x0]
    2a7a:	4c 8b 53 18          	mov    r10,QWORD PTR [rbx+0x18]
    2a7e:	4c 89 df             	mov    rdi,r11
    2a81:	44 8d 0c 36          	lea    r9d,[rsi+rsi*1]
    2a85:	0f 1f 00             	nop    DWORD PTR [rax]
    2a88:	8b 53 04             	mov    edx,DWORD PTR [rbx+0x4]
    2a8b:	8b 0b                	mov    ecx,DWORD PTR [rbx]
    2a8d:	89 f0                	mov    eax,esi
    2a8f:	39 f2                	cmp    edx,esi
    2a91:	77 16                	ja     2aa9 <bch_decode+0x389>
    2a93:	0f 1f 44 00 00       	nop    DWORD PTR [rax+rax*1+0x0]
    2a98:	29 d0                	sub    eax,edx
    2a9a:	41 89 d0             	mov    r8d,edx
    2a9d:	41 21 c0             	and    r8d,eax
    2aa0:	d3 e8                	shr    eax,cl
    2aa2:	44 01 c0             	add    eax,r8d
    2aa5:	39 c2                	cmp    edx,eax
    2aa7:	76 ef                	jbe    2a98 <bch_decode+0x378>
    2aa9:	48 98                	cdqe   
    2aab:	44 01 ce             	add    esi,r9d
    2aae:	41 0f b7 04 42       	movzx  eax,WORD PTR [r10+rax*2]
    2ab3:	31 07                	xor    DWORD PTR [rdi],eax
    2ab5:	48 83 c7 08          	add    rdi,0x8
    2ab9:	49 39 fd             	cmp    r13,rdi
    2abc:	75 ca                	jne    2a88 <bch_decode+0x368>
    2abe:	b8 01 00 00 00       	mov    eax,0x1
    2ac3:	44 89 f9             	mov    ecx,r15d
    2ac6:	d3 e0                	shl    eax,cl
    2ac8:	89 c2                	mov    edx,eax
    2aca:	44 31 f2             	xor    edx,r14d
    2acd:	44 39 f0             	cmp    eax,r14d
    2ad0:	74 7e                	je     2b50 <bch_decode+0x430>
    2ad2:	41 89 d6             	mov    r14d,edx
    2ad5:	eb 89                	jmp    2a60 <bch_decode+0x340>
    2ad7:	48 85 f6             	test   rsi,rsi
    2ada:	0f 84 50 01 00 00    	je     2c30 <bch_decode+0x510>
    2ae0:	4d 85 e4             	test   r12,r12
    2ae3:	0f 84 47 01 00 00    	je     2c30 <bch_decode+0x510>
    2ae9:	31 c9                	xor    ecx,ecx
    2aeb:	44 89 d2             	mov    edx,r10d
    2aee:	e8 cd f7 ff ff       	call   22c0 <bch_encode>
    2af3:	4c 8b 6b 38          	mov    r13,QWORD PTR [rbx+0x38]
    2af7:	4c 89 e2             	mov    rdx,r12
    2afa:	48 89 df             	mov    rdi,rbx
    2afd:	4c 89 ee             	mov    rsi,r13
    2b00:	e8 3b e9 ff ff       	call   1440 <load_ecc8>
    2b05:	89 e8                	mov    eax,ebp
    2b07:	41 0f af c7          	imul   eax,r15d
    2b0b:	83 c0 1f             	add    eax,0x1f
    2b0e:	c1 e8 05             	shr    eax,0x5
    2b11:	74 2d                	je     2b40 <bch_decode+0x420>
    2b13:	48 8b 7b 30          	mov    rdi,QWORD PTR [rbx+0x30]
    2b17:	89 c0                	mov    eax,eax
    2b19:	31 d2                	xor    edx,edx
    2b1b:	31 f6                	xor    esi,esi
    2b1d:	48 89 7c 24 08       	mov    QWORD PTR [rsp+0x8],rdi
    2b22:	8b 0c 97             	mov    ecx,DWORD PTR [rdi+rdx*4]
    2b25:	41 33 4c 95 00       	xor    ecx,DWORD PTR [r13+rdx*4+0x0]
    2b2a:	89 0c 97             	mov    DWORD PTR [rdi+rdx*4],ecx
    2b2d:	48 83 c2 01          	add    rdx,0x1
    2b31:	09 ce                	or     esi,ecx
    2b33:	48 39 d0             	cmp    rax,rdx
    2b36:	75 ea                	jne    2b22 <bch_decode+0x402>
    2b38:	85 f6                	test   esi,esi
    2b3a:	0f 85 ba fe ff ff    	jne    29fa <bch_decode+0x2da>
    2b40:	45 31 e4             	xor    r12d,r12d
    2b43:	e9 56 fd ff ff       	jmp    289e <bch_decode+0x17e>
    2b48:	0f 1f 84 00 00 00 00 00 	nop    DWORD PTR [rax+rax*1+0x0]
    2b50:	85 ed                	test   ebp,ebp
    2b52:	0f 8f e3 fe ff ff    	jg     2a3b <bch_decode+0x31b>
    2b58:	8b 74 24 14          	mov    esi,DWORD PTR [rsp+0x14]
    2b5c:	31 d2                	xor    edx,edx
    2b5e:	85 f6                	test   esi,esi
    2b60:	7e 39                	jle    2b9b <bch_decode+0x47b>
    2b62:	41 8b 04 93          	mov    eax,DWORD PTR [r11+rdx*4]
    2b66:	85 c0                	test   eax,eax
    2b68:	74 23                	je     2b8d <bch_decode+0x46d>
    2b6a:	48 8b 4b 20          	mov    rcx,QWORD PTR [rbx+0x20]
    2b6e:	48 8b 7b 18          	mov    rdi,QWORD PTR [rbx+0x18]
    2b72:	0f b7 04 41          	movzx  eax,WORD PTR [rcx+rax*2]
    2b76:	8b 4b 04             	mov    ecx,DWORD PTR [rbx+0x4]
    2b79:	01 c0                	add    eax,eax
    2b7b:	41 89 c0             	mov    r8d,eax
    2b7e:	41 29 c8             	sub    r8d,ecx
    2b81:	39 c8                	cmp    eax,ecx
    2b83:	41 0f 43 c0          	cmovae eax,r8d
    2b87:	48 98                	cdqe   
    2b89:	0f b7 04 47          	movzx  eax,WORD PTR [rdi+rax*2]
    2b8d:	41 89 44 d3 04       	mov    DWORD PTR [r11+rdx*8+0x4],eax
    2b92:	48 83 c2 01          	add    rdx,0x1
    2b96:	48 39 d6             	cmp    rsi,rdx
    2b99:	75 c7                	jne    2b62 <bch_decode+0x442>
    2b9b:	8b 43 04             	mov    eax,DWORD PTR [rbx+0x4]
    2b9e:	4c 8b 73 48          	mov    r14,QWORD PTR [rbx+0x48]
    2ba2:	44 8b 7b 08          	mov    r15d,DWORD PTR [rbx+0x8]
    2ba6:	89 44 24 14          	mov    DWORD PTR [rsp+0x14],eax
    2baa:	e9 bb fb ff ff       	jmp    276a <bch_decode+0x4a>
    2baf:	48 8b 84 24 80 00 00 00 	mov    rax,QWORD PTR [rsp+0x80]
    2bb7:	8b 4c 24 2c          	mov    ecx,DWORD PTR [rsp+0x2c]
    2bbb:	41 8d 54 24 ff       	lea    edx,[r12-0x1]
    2bc0:	03 4b 0c             	add    ecx,DWORD PTR [rbx+0xc]
    2bc3:	4c 8d 44 90 04       	lea    r8,[rax+rdx*4+0x4]
    2bc8:	8d 79 ff             	lea    edi,[rcx-0x1]
    2bcb:	8b 30                	mov    esi,DWORD PTR [rax]
    2bcd:	39 ce                	cmp    esi,ecx
    2bcf:	0f 83 f4 fd ff ff    	jae    29c9 <bch_decode+0x2a9>
    2bd5:	89 fa                	mov    edx,edi
    2bd7:	29 f2                	sub    edx,esi
    2bd9:	80 bb 80 00 00 00 00 	cmp    BYTE PTR [rbx+0x80],0x0
    2be0:	89 10                	mov    DWORD PTR [rax],edx
    2be2:	75 05                	jne    2be9 <bch_decode+0x4c9>
    2be4:	83 f2 07             	xor    edx,0x7
    2be7:	89 10                	mov    DWORD PTR [rax],edx
    2be9:	48 83 c0 04          	add    rax,0x4
    2bed:	4c 39 c0             	cmp    rax,r8
    2bf0:	75 d9                	jne    2bcb <bch_decode+0x4ab>
    2bf2:	e9 a7 fc ff ff       	jmp    289e <bch_decode+0x17e>
    2bf7:	41 39 ff             	cmp    r15d,edi
    2bfa:	0f 85 fa fb ff ff    	jne    27fa <bch_decode+0xda>
    2c00:	e9 88 fc ff ff       	jmp    288d <bch_decode+0x16d>
    2c05:	0f 1f 00             	nop    DWORD PTR [rax]
    2c08:	85 ed                	test   ebp,ebp
    2c0a:	8d 45 1f             	lea    eax,[rbp+0x1f]
    2c0d:	b9 20 00 00 00       	mov    ecx,0x20
    2c12:	0f 49 c5             	cmovns eax,ebp
    2c15:	29 d1                	sub    ecx,edx
    2c17:	ba ff ff ff ff       	mov    edx,0xffffffff
    2c1c:	d3 e2                	shl    edx,cl
    2c1e:	48 8b 4c 24 08       	mov    rcx,QWORD PTR [rsp+0x8]
    2c23:	c1 f8 05             	sar    eax,0x5
    2c26:	48 98                	cdqe   
    2c28:	21 14 81             	and    DWORD PTR [rcx+rax*4],edx
    2c2b:	e9 e3 fd ff ff       	jmp    2a13 <bch_decode+0x2f3>
    2c30:	41 bc ea ff ff ff    	mov    r12d,0xffffffea
    2c36:	e9 63 fc ff ff       	jmp    289e <bch_decode+0x17e>

Disassembly of section .fini:
