
/home/zzk/BinaryKernelCodeMapping/test/test_BCH/build/libbch-kernel-native.so:     file format elf64-x86-64


Disassembly of section .init:

Disassembly of section .plt:

Disassembly of section .plt.got:

Disassembly of section .plt.sec:

Disassembly of section .text:

0000000000001440 <load_ecc8>:
    1440:	41 56                	push   r14
    1442:	41 55                	push   r13
    1444:	41 54                	push   r12
    1446:	49 89 f4             	mov    r12,rsi
    1449:	48 89 d6             	mov    rsi,rdx
    144c:	55                   	push   rbp
    144d:	53                   	push   rbx
    144e:	48 89 fb             	mov    rbx,rdi
    1451:	48 83 ec 10          	sub    rsp,0x10
    1455:	8b 07                	mov    eax,DWORD PTR [rdi]
    1457:	0f af 47 08          	imul   eax,DWORD PTR [rdi+0x8]
    145b:	c7 44 24 0c 00 00 00 00 	mov    DWORD PTR [rsp+0xc],0x0
    1463:	8d 50 1f             	lea    edx,[rax+0x1f]
    1466:	c1 ea 05             	shr    edx,0x5
    1469:	89 d5                	mov    ebp,edx
    146b:	83 ed 01             	sub    ebp,0x1
    146e:	0f 84 5c 01 00 00    	je     15d0 <load_ecc8+0x190>
    1474:	8d 42 fe             	lea    eax,[rdx-0x2]
    1477:	44 0f b6 8f 80 00 00 00 	movzx  r9d,BYTE PTR [rdi+0x80]
    147f:	4c 89 e7             	mov    rdi,r12
    1482:	4c 8d 44 86 04       	lea    r8,[rsi+rax*4+0x4]
    1487:	eb 55                	jmp    14de <load_ecc8+0x9e>
    1489:	0f 1f 80 00 00 00 00 	nop    DWORD PTR [rax+0x0]
    1490:	4c 8d 35 a9 2b 00 00 	lea    r14,[rip+0x2ba9]        # 4040 <swap_bits_table>
    1497:	48 8d 05 a2 2b 00 00 	lea    rax,[rip+0x2ba2]        # 4040 <swap_bits_table>
    149e:	4c 8d 2d 9b 2b 00 00 	lea    r13,[rip+0x2b9b]        # 4040 <swap_bits_table>
    14a5:	0f b6 04 10          	movzx  eax,BYTE PTR [rax+rdx*1]
    14a9:	43 0f b6 14 1e       	movzx  edx,BYTE PTR [r14+r11*1]
    14ae:	c1 e0 10             	shl    eax,0x10
    14b1:	c1 e2 18             	shl    edx,0x18
    14b4:	09 d0                	or     eax,edx
    14b6:	43 0f b6 54 15 00    	movzx  edx,BYTE PTR [r13+r10*1+0x0]
    14bc:	c1 e2 08             	shl    edx,0x8
    14bf:	09 d0                	or     eax,edx
    14c1:	48 8d 15 78 2b 00 00 	lea    rdx,[rip+0x2b78]        # 4040 <swap_bits_table>
    14c8:	0f b6 0c 0a          	movzx  ecx,BYTE PTR [rdx+rcx*1]
    14cc:	09 c1                	or     ecx,eax
    14ce:	48 83 c6 04          	add    rsi,0x4
    14d2:	48 83 c7 04          	add    rdi,0x4
    14d6:	89 4f fc             	mov    DWORD PTR [rdi-0x4],ecx
    14d9:	49 39 f0             	cmp    r8,rsi
    14dc:	74 32                	je     1510 <load_ecc8+0xd0>
    14de:	44 0f b6 1e          	movzx  r11d,BYTE PTR [rsi]
    14e2:	0f b6 4e 03          	movzx  ecx,BYTE PTR [rsi+0x3]
    14e6:	44 0f b6 56 02       	movzx  r10d,BYTE PTR [rsi+0x2]
    14eb:	0f b6 56 01          	movzx  edx,BYTE PTR [rsi+0x1]
    14ef:	45 84 c9             	test   r9b,r9b
    14f2:	75 9c                	jne    1490 <load_ecc8+0x50>
    14f4:	41 c1 e3 18          	shl    r11d,0x18
    14f8:	0f b6 c2             	movzx  eax,dl
    14fb:	41 c1 e2 08          	shl    r10d,0x8
    14ff:	c1 e0 10             	shl    eax,0x10
    1502:	44 09 d8             	or     eax,r11d
    1505:	44 09 d0             	or     eax,r10d
    1508:	eb c2                	jmp    14cc <load_ecc8+0x8c>
    150a:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    1510:	8b 43 08             	mov    eax,DWORD PTR [rbx+0x8]
    1513:	0f af 03             	imul   eax,DWORD PTR [rbx]
    1516:	8d 50 07             	lea    edx,[rax+0x7]
    1519:	48 8d 7c 24 0c       	lea    rdi,[rsp+0xc]
    151e:	b9 04 00 00 00       	mov    ecx,0x4
    1523:	4c 89 c6             	mov    rsi,r8
    1526:	c1 ea 03             	shr    edx,0x3
    1529:	8d 04 ad 00 00 00 00 	lea    eax,[rbp*4+0x0]
    1530:	29 c2                	sub    edx,eax
    1532:	e8 99 fb ff ff       	call   10d0 <__memcpy_chk@plt>
    1537:	80 bb 80 00 00 00 00 	cmp    BYTE PTR [rbx+0x80],0x0
    153e:	0f b6 54 24 0c       	movzx  edx,BYTE PTR [rsp+0xc]
    1543:	74 63                	je     15a8 <load_ecc8+0x168>
    1545:	48 8d 35 f4 2a 00 00 	lea    rsi,[rip+0x2af4]        # 4040 <swap_bits_table>
    154c:	48 8d 3d ed 2a 00 00 	lea    rdi,[rip+0x2aed]        # 4040 <swap_bits_table>
    1553:	48 8d 0d e6 2a 00 00 	lea    rcx,[rip+0x2ae6]        # 4040 <swap_bits_table>
    155a:	0f b6 44 24 0d       	movzx  eax,BYTE PTR [rsp+0xd]
    155f:	0f b6 14 16          	movzx  edx,BYTE PTR [rsi+rdx*1]
    1563:	0f b6 04 07          	movzx  eax,BYTE PTR [rdi+rax*1]
    1567:	c1 e2 18             	shl    edx,0x18
    156a:	c1 e0 10             	shl    eax,0x10
    156d:	09 d0                	or     eax,edx
    156f:	0f b6 54 24 0e       	movzx  edx,BYTE PTR [rsp+0xe]
    1574:	0f b6 14 11          	movzx  edx,BYTE PTR [rcx+rdx*1]
    1578:	c1 e2 08             	shl    edx,0x8
    157b:	09 d0                	or     eax,edx
    157d:	48 8d 0d bc 2a 00 00 	lea    rcx,[rip+0x2abc]        # 4040 <swap_bits_table>
    1584:	0f b6 54 24 0f       	movzx  edx,BYTE PTR [rsp+0xf]
    1589:	0f b6 14 11          	movzx  edx,BYTE PTR [rcx+rdx*1]
    158d:	89 ed                	mov    ebp,ebp
    158f:	09 d0                	or     eax,edx
    1591:	41 89 04 ac          	mov    DWORD PTR [r12+rbp*4],eax
    1595:	48 83 c4 10          	add    rsp,0x10
    1599:	5b                   	pop    rbx
    159a:	5d                   	pop    rbp
    159b:	41 5c                	pop    r12
    159d:	41 5d                	pop    r13
    159f:	41 5e                	pop    r14
    15a1:	c3                   	ret    
    15a2:	66 0f 1f 44 00 00    	nop    WORD PTR [rax+rax*1+0x0]
    15a8:	0f b6 44 24 0d       	movzx  eax,BYTE PTR [rsp+0xd]
    15ad:	c1 e2 18             	shl    edx,0x18
    15b0:	c1 e0 10             	shl    eax,0x10
    15b3:	09 d0                	or     eax,edx
    15b5:	0f b6 54 24 0e       	movzx  edx,BYTE PTR [rsp+0xe]
    15ba:	c1 e2 08             	shl    edx,0x8
    15bd:	09 d0                	or     eax,edx
    15bf:	0f b6 54 24 0f       	movzx  edx,BYTE PTR [rsp+0xf]
    15c4:	eb c7                	jmp    158d <load_ecc8+0x14d>
    15c6:	66 2e 0f 1f 84 00 00 00 00 00 	cs nop WORD PTR [rax+rax*1+0x0]
    15d0:	49 89 f0             	mov    r8,rsi
    15d3:	e9 3e ff ff ff       	jmp    1516 <load_ecc8+0xd6>

Disassembly of section .fini:
