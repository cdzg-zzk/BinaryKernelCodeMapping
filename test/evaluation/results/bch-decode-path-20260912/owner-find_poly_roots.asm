
/home/zzk/BinaryKernelCodeMapping/test/test_BCH/kmod/vkso_bch.ko:     file format elf64-x86-64


Disassembly of section .text:

0000000000001530 <find_poly_roots>:
    1530:	55                   	push   rbp	64: R_X86_64_PC32	.rodata+0x3c
	118: R_X86_64_PC32	.rodata+0x3c
	11f: R_X86_64_PC32	.rodata+0x3c
	126: R_X86_64_PC32	.rodata+0x3c
	148: R_X86_64_PC32	.rodata+0x3c
	1b2: R_X86_64_PC32	vkso_bch_memcpy_slot-0x4
	1c8: R_X86_64_PC32	.rodata+0x3c
	1cf: R_X86_64_PC32	.rodata+0x3c
	1d6: R_X86_64_PC32	.rodata+0x3c
	1fe: R_X86_64_PC32	.rodata+0x3c
	3bd: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	3e7: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	3f5: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	403: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	411: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	41f: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	42d: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	43b: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	449: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	459: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	46a: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	553: R_X86_64_PC32	vkso_bch_memcpy_slot-0x4
	5cc: R_X86_64_PC32	.rodata+0x3c
	5d3: R_X86_64_PC32	.rodata+0x3c
	5da: R_X86_64_PC32	.rodata+0x3c
	60a: R_X86_64_PC32	.rodata+0x3c
	6cf: R_X86_64_PC32	vkso_bch_memcpy_slot-0x4
	727: R_X86_64_PC32	.rodata+0x3c
	749: R_X86_64_PC32	.rodata+0x3c
	76f: R_X86_64_PC32	.rodata+0x3c
	796: R_X86_64_PC32	.rodata+0x3c
	7e9: R_X86_64_PC32	.rodata+0x3c
	7fc: R_X86_64_PC32	.rodata+0x3c
	813: R_X86_64_PC32	.rodata+0x3c
	82a: R_X86_64_PC32	.rodata+0x3c
	846: R_X86_64_PC32	vkso_bch_memcpy_slot-0x4
	875: R_X86_64_PC32	vkso_bch_memset_slot-0x4
	d0f: R_X86_64_PC32	.rodata-0x4
	d1e: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	d47: R_X86_64_PC32	vkso_bch_memset_slot-0x4
	d83: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	d9f: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	dc4: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	de6: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	e09: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	e25: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	e4d: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	e73: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	e9c: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	ed5: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	f80: R_X86_64_PLT32	vkso_bch_free-0x4
	fd5: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	fed: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	100a: R_X86_64_PC32	vkso_bch_kmalloc_slot-0x4
	1041: R_X86_64_PC32	vkso_bch_memset_slot-0x4
	1235: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	1241: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	124a: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	126c: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	127b: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	12c1: R_X86_64_PC32	vkso_bch_memset_slot-0x4
	13bb: R_X86_64_PC32	vkso_bch_kfree_slot-0x4
	143d: R_X86_64_PC32	vkso_bch_memset_slot-0x4
	150c: R_X86_64_PC32	vkso_bch_memset_slot-0x4
    1531:	48 89 e5             	mov    rbp,rsp
    1534:	41 57                	push   r15
    1536:	49 89 cf             	mov    r15,rcx
    1539:	41 56                	push   r14
    153b:	41 55                	push   r13
    153d:	49 89 d5             	mov    r13,rdx
    1540:	41 54                	push   r12
    1542:	49 89 fc             	mov    r12,rdi
    1545:	53                   	push   rbx
    1546:	48 83 ec 38          	sub    rsp,0x38
    154a:	8b 02                	mov    eax,DWORD PTR [rdx]
    154c:	83 f8 03             	cmp    eax,0x3
    154f:	0f 84 9a 02 00 00    	je     17ef <find_poly_roots+0x2bf>
    1555:	41 89 f0             	mov    r8d,esi
    1558:	77 33                	ja     158d <find_poly_roots+0x5d>
    155a:	83 f8 01             	cmp    eax,0x1
    155d:	0f 84 53 02 00 00    	je     17b6 <find_poly_roots+0x286>
    1563:	83 f8 02             	cmp    eax,0x2
    1566:	0f 85 34 05 00 00    	jne    1aa0 <find_poly_roots+0x570>
    156c:	8b 52 04             	mov    edx,DWORD PTR [rdx+0x4]
    156f:	85 d2                	test   edx,edx
    1571:	0f 85 e2 03 00 00    	jne    1959 <find_poly_roots+0x429>
    1577:	45 31 f6             	xor    r14d,r14d
    157a:	48 83 c4 38          	add    rsp,0x38
    157e:	44 89 f0             	mov    eax,r14d
    1581:	5b                   	pop    rbx
    1582:	41 5c                	pop    r12
    1584:	41 5d                	pop    r13
    1586:	41 5e                	pop    r14
    1588:	41 5f                	pop    r15
    158a:	5d                   	pop    rbp
    158b:	c3                   	ret    
    158c:	cc                   	int3   
    158d:	83 f8 04             	cmp    eax,0x4
    1590:	0f 85 12 05 00 00    	jne    1aa8 <find_poly_roots+0x578>
    1596:	8b 52 04             	mov    edx,DWORD PTR [rdx+0x4]
    1599:	85 d2                	test   edx,edx
    159b:	74 da                	je     1577 <find_poly_roots+0x47>
    159d:	4c 8b 47 18          	mov    r8,QWORD PTR [rdi+0x18]
    15a1:	48 8b 7f 20          	mov    rdi,QWORD PTR [rdi+0x20]
    15a5:	41 8b 4d 14          	mov    ecx,DWORD PTR [r13+0x14]
    15a9:	41 8b 44 24 04       	mov    eax,DWORD PTR [r12+0x4]
    15ae:	0f b7 14 57          	movzx  edx,WORD PTR [rdi+rdx*2]
    15b2:	45 8b 4d 08          	mov    r9d,DWORD PTR [r13+0x8]
    15b6:	44 0f b7 1c 4f       	movzx  r11d,WORD PTR [rdi+rcx*2]
    15bb:	01 c2                	add    edx,eax
    15bd:	44 29 da             	sub    edx,r11d
    15c0:	89 d1                	mov    ecx,edx
    15c2:	29 c1                	sub    ecx,eax
    15c4:	39 d0                	cmp    eax,edx
    15c6:	0f 46 d1             	cmovbe edx,ecx
    15c9:	48 63 d2             	movsxd rdx,edx
    15cc:	41 0f b7 0c 50       	movzx  ecx,WORD PTR [r8+rdx*2]
    15d1:	41 89 ca             	mov    r10d,ecx
    15d4:	45 85 c9             	test   r9d,r9d
    15d7:	74 1b                	je     15f4 <find_poly_roots+0xc4>
    15d9:	42 0f b7 14 4f       	movzx  edx,WORD PTR [rdi+r9*2]
    15de:	01 c2                	add    edx,eax
    15e0:	44 29 da             	sub    edx,r11d
    15e3:	89 d6                	mov    esi,edx
    15e5:	29 c6                	sub    esi,eax
    15e7:	39 d0                	cmp    eax,edx
    15e9:	0f 46 d6             	cmovbe edx,esi
    15ec:	48 63 d2             	movsxd rdx,edx
    15ef:	45 0f b7 0c 50       	movzx  r9d,WORD PTR [r8+rdx*2]
    15f4:	41 8b 75 0c          	mov    esi,DWORD PTR [r13+0xc]
    15f8:	85 f6                	test   esi,esi
    15fa:	74 1a                	je     1616 <find_poly_roots+0xe6>
    15fc:	0f b7 14 77          	movzx  edx,WORD PTR [rdi+rsi*2]
    1600:	01 c2                	add    edx,eax
    1602:	44 29 da             	sub    edx,r11d
    1605:	89 d6                	mov    esi,edx
    1607:	29 c6                	sub    esi,eax
    1609:	39 d0                	cmp    eax,edx
    160b:	0f 46 d6             	cmovbe edx,esi
    160e:	48 63 d2             	movsxd rdx,edx
    1611:	41 0f b7 34 50       	movzx  esi,WORD PTR [r8+rdx*2]
    1616:	45 8b 6d 10          	mov    r13d,DWORD PTR [r13+0x10]
    161a:	45 85 ed             	test   r13d,r13d
    161d:	0f 84 4a 06 00 00    	je     1c6d <find_poly_roots+0x73d>
    1623:	42 0f b7 14 6f       	movzx  edx,WORD PTR [rdi+r13*2]
    1628:	01 c2                	add    edx,eax
    162a:	44 29 da             	sub    edx,r11d
    162d:	41 89 d3             	mov    r11d,edx
    1630:	41 29 c3             	sub    r11d,eax
    1633:	39 d0                	cmp    eax,edx
    1635:	41 0f 46 d3          	cmovbe edx,r11d
    1639:	48 63 d2             	movsxd rdx,edx
    163c:	41 0f b7 1c 50       	movzx  ebx,WORD PTR [r8+rdx*2]
    1641:	49 89 db             	mov    r11,rbx
    1644:	85 db                	test   ebx,ebx
    1646:	0f 84 87 06 00 00    	je     1cd3 <find_poly_roots+0x7a3>
    164c:	45 85 c9             	test   r9d,r9d
    164f:	0f 84 fc 00 00 00    	je     1751 <find_poly_roots+0x221>
    1655:	42 0f b7 14 4f       	movzx  edx,WORD PTR [rdi+r9*2]
    165a:	0f b7 cb             	movzx  ecx,bx
    165d:	0f b7 0c 4f          	movzx  ecx,WORD PTR [rdi+rcx*2]
    1661:	01 c2                	add    edx,eax
    1663:	29 ca                	sub    edx,ecx
    1665:	89 4d bc             	mov    DWORD PTR [rbp-0x44],ecx
    1668:	89 d1                	mov    ecx,edx
    166a:	29 c1                	sub    ecx,eax
    166c:	39 d0                	cmp    eax,edx
    166e:	0f 46 d1             	cmovbe edx,ecx
    1671:	45 31 f6             	xor    r14d,r14d
    1674:	48 63 d2             	movsxd rdx,edx
    1677:	41 0f b7 14 50       	movzx  edx,WORD PTR [r8+rdx*2]
    167c:	0f b7 0c 57          	movzx  ecx,WORD PTR [rdi+rdx*2]
    1680:	49 89 d5             	mov    r13,rdx
    1683:	89 ca                	mov    edx,ecx
    1685:	89 4d b0             	mov    DWORD PTR [rbp-0x50],ecx
    1688:	83 e2 01             	and    edx,0x1
    168b:	44 0f 45 f0          	cmovne r14d,eax
    168f:	41 01 ce             	add    r14d,ecx
    1692:	41 8b 0c 24          	mov    ecx,DWORD PTR [r12]
    1696:	45 89 f1             	mov    r9d,r14d
    1699:	41 c1 e9 1f          	shr    r9d,0x1f
    169d:	45 01 f1             	add    r9d,r14d
    16a0:	41 d1 f9             	sar    r9d,1
    16a3:	44 89 ca             	mov    edx,r9d
    16a6:	44 39 c8             	cmp    eax,r9d
    16a9:	77 14                	ja     16bf <find_poly_roots+0x18f>
    16ab:	29 c2                	sub    edx,eax
    16ad:	41 89 c1             	mov    r9d,eax
    16b0:	41 21 d1             	and    r9d,edx
    16b3:	d3 ea                	shr    edx,cl
    16b5:	44 01 ca             	add    edx,r9d
    16b8:	39 d0                	cmp    eax,edx
    16ba:	76 ef                	jbe    16ab <find_poly_roots+0x17b>
    16bc:	41 89 d1             	mov    r9d,edx
    16bf:	4d 63 c9             	movsxd r9,r9d
    16c2:	45 01 f6             	add    r14d,r14d
    16c5:	47 0f b7 0c 48       	movzx  r9d,WORD PTR [r8+r9*2]
    16ca:	44 89 f2             	mov    edx,r14d
    16cd:	66 44 89 4d c0       	mov    WORD PTR [rbp-0x40],r9w
    16d2:	44 39 f0             	cmp    eax,r14d
    16d5:	77 14                	ja     16eb <find_poly_roots+0x1bb>
    16d7:	29 c2                	sub    edx,eax
    16d9:	41 89 c6             	mov    r14d,eax
    16dc:	41 21 d6             	and    r14d,edx
    16df:	d3 ea                	shr    edx,cl
    16e1:	44 01 f2             	add    edx,r14d
    16e4:	39 d0                	cmp    eax,edx
    16e6:	76 ef                	jbe    16d7 <find_poly_roots+0x1a7>
    16e8:	41 89 d6             	mov    r14d,edx
    16eb:	4d 63 f6             	movsxd r14,r14d
    16ee:	43 0f b7 14 70       	movzx  edx,WORD PTR [r8+r14*2]
    16f3:	85 f6                	test   esi,esi
    16f5:	0f 84 3e 07 00 00    	je     1e39 <find_poly_roots+0x909>
    16fb:	66 45 85 ed          	test   r13w,r13w
    16ff:	0f 84 34 07 00 00    	je     1e39 <find_poly_roots+0x909>
    1705:	89 f1                	mov    ecx,esi
    1707:	0f b7 0c 4f          	movzx  ecx,WORD PTR [rdi+rcx*2]
    170b:	03 4d b0             	add    ecx,DWORD PTR [rbp-0x50]
    170e:	41 89 cd             	mov    r13d,ecx
    1711:	41 29 c5             	sub    r13d,eax
    1714:	39 c8                	cmp    eax,ecx
    1716:	41 0f 46 cd          	cmovbe ecx,r13d
    171a:	48 63 c9             	movsxd rcx,ecx
    171d:	41 0f b7 0c 48       	movzx  ecx,WORD PTR [r8+rcx*2]
    1722:	41 31 d2             	xor    r10d,edx
    1725:	41 0f b7 d2          	movzx  edx,r10w
    1729:	31 d1                	xor    ecx,edx
    172b:	45 85 c9             	test   r9d,r9d
    172e:	74 21                	je     1751 <find_poly_roots+0x221>
    1730:	0f b7 55 c0          	movzx  edx,WORD PTR [rbp-0x40]
    1734:	0f b7 14 57          	movzx  edx,WORD PTR [rdi+rdx*2]
    1738:	03 55 bc             	add    edx,DWORD PTR [rbp-0x44]
    173b:	41 89 d2             	mov    r10d,edx
    173e:	41 29 c2             	sub    r10d,eax
    1741:	39 d0                	cmp    eax,edx
    1743:	41 0f 46 d2          	cmovbe edx,r10d
    1747:	48 63 d2             	movsxd rdx,edx
    174a:	41 0f b7 14 50       	movzx  edx,WORD PTR [r8+rdx*2]
    174f:	31 d6                	xor    esi,edx
    1751:	85 c9                	test   ecx,ecx
    1753:	0f 84 1e fe ff ff    	je     1577 <find_poly_roots+0x47>
    1759:	89 c9                	mov    ecx,ecx
    175b:	89 c2                	mov    edx,eax
    175d:	44 0f b7 14 4f       	movzx  r10d,WORD PTR [rdi+rcx*2]
    1762:	44 29 d2             	sub    edx,r10d
    1765:	41 0f b7 0c 50       	movzx  ecx,WORD PTR [r8+rdx*2]
    176a:	42 0f b7 14 5f       	movzx  edx,WORD PTR [rdi+r11*2]
    176f:	01 c2                	add    edx,eax
    1771:	44 29 d2             	sub    edx,r10d
    1774:	41 89 d3             	mov    r11d,edx
    1777:	41 29 c3             	sub    r11d,eax
    177a:	39 d0                	cmp    eax,edx
    177c:	41 0f 46 d3          	cmovbe edx,r11d
    1780:	48 63 d2             	movsxd rdx,edx
    1783:	45 0f b7 1c 50       	movzx  r11d,WORD PTR [r8+rdx*2]
    1788:	85 f6                	test   esi,esi
    178a:	0f 84 9e 06 00 00    	je     1e2e <find_poly_roots+0x8fe>
    1790:	0f b7 14 77          	movzx  edx,WORD PTR [rdi+rsi*2]
    1794:	45 89 cd             	mov    r13d,r9d
    1797:	45 89 d9             	mov    r9d,r11d
    179a:	01 c2                	add    edx,eax
    179c:	44 29 d2             	sub    edx,r10d
    179f:	89 d6                	mov    esi,edx
    17a1:	29 c6                	sub    esi,eax
    17a3:	39 d0                	cmp    eax,edx
    17a5:	89 d0                	mov    eax,edx
    17a7:	0f 46 c6             	cmovbe eax,esi
    17aa:	48 98                	cdqe   
    17ac:	41 0f b7 34 40       	movzx  esi,WORD PTR [r8+rax*2]
    17b1:	e9 b9 04 00 00       	jmp    1c6f <find_poly_roots+0x73f>
    17b6:	8b 52 04             	mov    edx,DWORD PTR [rdx+0x4]
    17b9:	85 d2                	test   edx,edx
    17bb:	0f 84 b6 fd ff ff    	je     1577 <find_poly_roots+0x47>
    17c1:	48 8b 77 20          	mov    rsi,QWORD PTR [rdi+0x20]
    17c5:	41 8b 45 08          	mov    eax,DWORD PTR [r13+0x8]
    17c9:	41 be 01 00 00 00    	mov    r14d,0x1
    17cf:	8b 4f 04             	mov    ecx,DWORD PTR [rdi+0x4]
    17d2:	0f b7 04 46          	movzx  eax,WORD PTR [rsi+rax*2]
    17d6:	0f b7 14 56          	movzx  edx,WORD PTR [rsi+rdx*2]
    17da:	01 c8                	add    eax,ecx
    17dc:	29 d0                	sub    eax,edx
    17de:	89 c2                	mov    edx,eax
    17e0:	29 ca                	sub    edx,ecx
    17e2:	39 c1                	cmp    ecx,eax
    17e4:	0f 46 c2             	cmovbe eax,edx
    17e7:	41 89 07             	mov    DWORD PTR [r15],eax
    17ea:	e9 8b fd ff ff       	jmp    157a <find_poly_roots+0x4a>
    17ef:	8b 52 04             	mov    edx,DWORD PTR [rdx+0x4]
    17f2:	85 d2                	test   edx,edx
    17f4:	0f 84 7d fd ff ff    	je     1577 <find_poly_roots+0x47>
    17fa:	49 8b 4c 24 20       	mov    rcx,QWORD PTR [r12+0x20]
    17ff:	41 8b 75 10          	mov    esi,DWORD PTR [r13+0x10]
    1803:	41 8b 44 24 04       	mov    eax,DWORD PTR [r12+0x4]
    1808:	48 8b 7f 18          	mov    rdi,QWORD PTR [rdi+0x18]
    180c:	0f b7 14 51          	movzx  edx,WORD PTR [rcx+rdx*2]
    1810:	44 0f b7 04 71       	movzx  r8d,WORD PTR [rcx+rsi*2]
    1815:	01 c2                	add    edx,eax
    1817:	44 29 c2             	sub    edx,r8d
    181a:	89 d6                	mov    esi,edx
    181c:	29 c6                	sub    esi,eax
    181e:	39 d0                	cmp    eax,edx
    1820:	0f 46 d6             	cmovbe edx,esi
    1823:	41 8b 75 08          	mov    esi,DWORD PTR [r13+0x8]
    1827:	48 63 d2             	movsxd rdx,edx
    182a:	44 0f b7 0c 57       	movzx  r9d,WORD PTR [rdi+rdx*2]
    182f:	45 89 cb             	mov    r11d,r9d
    1832:	85 f6                	test   esi,esi
    1834:	74 19                	je     184f <find_poly_roots+0x31f>
    1836:	0f b7 14 71          	movzx  edx,WORD PTR [rcx+rsi*2]
    183a:	01 c2                	add    edx,eax
    183c:	44 29 c2             	sub    edx,r8d
    183f:	89 d6                	mov    esi,edx
    1841:	29 c6                	sub    esi,eax
    1843:	39 d0                	cmp    eax,edx
    1845:	0f 46 d6             	cmovbe edx,esi
    1848:	48 63 d2             	movsxd rdx,edx
    184b:	0f b7 34 57          	movzx  esi,WORD PTR [rdi+rdx*2]
    184f:	45 8b 55 0c          	mov    r10d,DWORD PTR [r13+0xc]
    1853:	31 db                	xor    ebx,ebx
    1855:	45 85 d2             	test   r10d,r10d
    1858:	0f 84 9d 00 00 00    	je     18fb <find_poly_roots+0x3cb>
    185e:	42 0f b7 14 51       	movzx  edx,WORD PTR [rcx+r10*2]
    1863:	01 c2                	add    edx,eax
    1865:	44 29 c2             	sub    edx,r8d
    1868:	41 89 d0             	mov    r8d,edx
    186b:	41 29 c0             	sub    r8d,eax
    186e:	39 d0                	cmp    eax,edx
    1870:	41 0f 46 d0          	cmovbe edx,r8d
    1874:	48 63 d2             	movsxd rdx,edx
    1877:	0f b7 1c 57          	movzx  ebx,WORD PTR [rdi+rdx*2]
    187b:	85 db                	test   ebx,ebx
    187d:	49 89 d8             	mov    r8,rbx
    1880:	0f 95 c2             	setne  dl
    1883:	45 85 c9             	test   r9d,r9d
    1886:	0f 84 ca 05 00 00    	je     1e56 <find_poly_roots+0x926>
    188c:	84 d2                	test   dl,dl
    188e:	0f 84 c2 05 00 00    	je     1e56 <find_poly_roots+0x926>
    1894:	45 0f b7 d3          	movzx  r10d,r11w
    1898:	0f b7 14 59          	movzx  edx,WORD PTR [rcx+rbx*2]
    189c:	46 0f b7 14 51       	movzx  r10d,WORD PTR [rcx+r10*2]
    18a1:	44 01 d2             	add    edx,r10d
    18a4:	41 89 d2             	mov    r10d,edx
    18a7:	41 29 c2             	sub    r10d,eax
    18aa:	39 d0                	cmp    eax,edx
    18ac:	41 0f 46 d2          	cmovbe edx,r10d
    18b0:	48 63 d2             	movsxd rdx,edx
    18b3:	44 0f b7 14 57       	movzx  r10d,WORD PTR [rdi+rdx*2]
    18b8:	85 f6                	test   esi,esi
    18ba:	0f 84 ad 05 00 00    	je     1e6d <find_poly_roots+0x93d>
    18c0:	42 0f b7 14 41       	movzx  edx,WORD PTR [rcx+r8*2]
    18c5:	41 89 f0             	mov    r8d,esi
    18c8:	42 0f b7 0c 41       	movzx  ecx,WORD PTR [rcx+r8*2]
    18cd:	01 d1                	add    ecx,edx
    18cf:	41 89 c8             	mov    r8d,ecx
    18d2:	41 29 c0             	sub    r8d,eax
    18d5:	39 c8                	cmp    eax,ecx
    18d7:	41 0f 46 c8          	cmovbe ecx,r8d
    18db:	48 63 c9             	movsxd rcx,ecx
    18de:	66 44 33 1c 4f       	xor    r11w,WORD PTR [rdi+rcx*2]
    18e3:	45 0f b7 cb          	movzx  r9d,r11w
    18e7:	01 d2                	add    edx,edx
    18e9:	89 d1                	mov    ecx,edx
    18eb:	29 c1                	sub    ecx,eax
    18ed:	39 d0                	cmp    eax,edx
    18ef:	0f 46 d1             	cmovbe edx,ecx
    18f2:	48 63 d2             	movsxd rdx,edx
    18f5:	0f b7 04 57          	movzx  eax,WORD PTR [rdi+rdx*2]
    18f9:	31 c6                	xor    esi,eax
    18fb:	4c 8d 45 c8          	lea    r8,[rbp-0x38]
    18ff:	44 89 d1             	mov    ecx,r10d
    1902:	44 89 ca             	mov    edx,r9d
    1905:	4c 89 e7             	mov    rdi,r12
    1908:	e8 43 f2 ff ff       	call   b50 <find_affine4_roots>
    190d:	83 f8 04             	cmp    eax,0x4
    1910:	0f 85 61 fc ff ff    	jne    1577 <find_poly_roots+0x47>
    1916:	48 8d 45 c8          	lea    rax,[rbp-0x38]
    191a:	48 8d 7d d8          	lea    rdi,[rbp-0x28]
    191e:	45 31 f6             	xor    r14d,r14d
    1921:	8b 10                	mov    edx,DWORD PTR [rax]
    1923:	39 da                	cmp    edx,ebx
    1925:	74 24                	je     194b <find_poly_roots+0x41b>
    1927:	49 8b 4c 24 20       	mov    rcx,QWORD PTR [r12+0x20]
    192c:	41 8b 74 24 04       	mov    esi,DWORD PTR [r12+0x4]
    1931:	0f b7 0c 51          	movzx  ecx,WORD PTR [rcx+rdx*2]
    1935:	89 f2                	mov    edx,esi
    1937:	29 ca                	sub    edx,ecx
    1939:	f7 d9                	neg    ecx
    193b:	39 d6                	cmp    esi,edx
    193d:	0f 46 d1             	cmovbe edx,ecx
    1940:	49 63 ce             	movsxd rcx,r14d
    1943:	41 83 c6 01          	add    r14d,0x1
    1947:	41 89 14 8f          	mov    DWORD PTR [r15+rcx*4],edx
    194b:	48 83 c0 04          	add    rax,0x4
    194f:	48 39 c7             	cmp    rdi,rax
    1952:	75 cd                	jne    1921 <find_poly_roots+0x3f1>
    1954:	e9 21 fc ff ff       	jmp    157a <find_poly_roots+0x4a>
    1959:	41 8b 4d 08          	mov    ecx,DWORD PTR [r13+0x8]
    195d:	85 c9                	test   ecx,ecx
    195f:	0f 84 12 fc ff ff    	je     1577 <find_poly_roots+0x47>
    1965:	48 8b 5f 20          	mov    rbx,QWORD PTR [rdi+0x20]
    1969:	41 8b 75 0c          	mov    esi,DWORD PTR [r13+0xc]
    196d:	8b 47 04             	mov    eax,DWORD PTR [rdi+0x4]
    1970:	45 8b 04 24          	mov    r8d,DWORD PTR [r12]
    1974:	0f b7 3c 4b          	movzx  edi,WORD PTR [rbx+rcx*2]
    1978:	0f b7 34 73          	movzx  esi,WORD PTR [rbx+rsi*2]
    197c:	0f b7 14 53          	movzx  edx,WORD PTR [rbx+rdx*2]
    1980:	89 c1                	mov    ecx,eax
    1982:	29 f9                	sub    ecx,edi
    1984:	89 7d b0             	mov    DWORD PTR [rbp-0x50],edi
    1987:	49 8b 7c 24 18       	mov    rdi,QWORD PTR [r12+0x18]
    198c:	01 f2                	add    edx,esi
    198e:	89 75 b8             	mov    DWORD PTR [rbp-0x48],esi
    1991:	8d 14 4a             	lea    edx,[rdx+rcx*2]
    1994:	48 89 7d c0          	mov    QWORD PTR [rbp-0x40],rdi
    1998:	39 d0                	cmp    eax,edx
    199a:	77 14                	ja     19b0 <find_poly_roots+0x480>
    199c:	44 89 c1             	mov    ecx,r8d
    199f:	29 c2                	sub    edx,eax
    19a1:	89 c6                	mov    esi,eax
    19a3:	21 d6                	and    esi,edx
    19a5:	d3 ea                	shr    edx,cl
    19a7:	01 f2                	add    edx,esi
    19a9:	39 d0                	cmp    eax,edx
    19ab:	76 f2                	jbe    199f <find_poly_roots+0x46f>
    19ad:	41 89 c8             	mov    r8d,ecx
    19b0:	48 8b 7d c0          	mov    rdi,QWORD PTR [rbp-0x40]
    19b4:	48 63 d2             	movsxd rdx,edx
    19b7:	0f b7 3c 57          	movzx  edi,WORD PTR [rdi+rdx*2]
    19bb:	89 7d bc             	mov    DWORD PTR [rbp-0x44],edi
    19be:	85 ff                	test   edi,edi
    19c0:	0f 84 7a 04 00 00    	je     1e40 <find_poly_roots+0x910>
    19c6:	4d 8b 6c 24 40       	mov    r13,QWORD PTR [r12+0x40]
    19cb:	8b 55 bc             	mov    edx,DWORD PTR [rbp-0x44]
    19ce:	31 f6                	xor    esi,esi
    19d0:	41 bb ff ff ff ff    	mov    r11d,0xffffffff
    19d6:	41 ba 01 00 00 00    	mov    r10d,0x1
    19dc:	44 89 d9             	mov    ecx,r11d
    19df:	45 89 d6             	mov    r14d,r10d
    19e2:	41 89 f1             	mov    r9d,esi
    19e5:	0f bd ca             	bsr    ecx,edx
    19e8:	48 63 f9             	movsxd rdi,ecx
    19eb:	41 d3 e6             	shl    r14d,cl
    19ee:	41 8b 7c bd 00       	mov    edi,DWORD PTR [r13+rdi*4+0x0]
    19f3:	44 89 f1             	mov    ecx,r14d
    19f6:	41 89 d6             	mov    r14d,edx
    19f9:	31 ca                	xor    edx,ecx
    19fb:	31 fe                	xor    esi,edi
    19fd:	44 39 f1             	cmp    ecx,r14d
    1a00:	75 da                	jne    19dc <find_poly_roots+0x4ac>
    1a02:	44 39 cf             	cmp    edi,r9d
    1a05:	0f 84 6c fb ff ff    	je     1577 <find_poly_roots+0x47>
    1a0b:	89 f2                	mov    edx,esi
    1a0d:	0f b7 3c 53          	movzx  edi,WORD PTR [rbx+rdx*2]
    1a11:	48 8b 5d c0          	mov    rbx,QWORD PTR [rbp-0x40]
    1a15:	8d 14 3f             	lea    edx,[rdi+rdi*1]
    1a18:	89 d1                	mov    ecx,edx
    1a1a:	29 c1                	sub    ecx,eax
    1a1c:	39 d0                	cmp    eax,edx
    1a1e:	0f 46 d1             	cmovbe edx,ecx
    1a21:	48 63 d2             	movsxd rdx,edx
    1a24:	0f b7 14 53          	movzx  edx,WORD PTR [rbx+rdx*2]
    1a28:	31 f2                	xor    edx,esi
    1a2a:	3b 55 bc             	cmp    edx,DWORD PTR [rbp-0x44]
    1a2d:	0f 85 44 fb ff ff    	jne    1577 <find_poly_roots+0x47>
    1a33:	89 f2                	mov    edx,esi
    1a35:	83 f2 01             	xor    edx,0x1
    1a38:	48 01 d2             	add    rdx,rdx
    1a3b:	8b 5d b8             	mov    ebx,DWORD PTR [rbp-0x48]
    1a3e:	8d 0c 43             	lea    ecx,[rbx+rax*2]
    1a41:	2b 4d b0             	sub    ecx,DWORD PTR [rbp-0x50]
    1a44:	29 f9                	sub    ecx,edi
    1a46:	39 c8                	cmp    eax,ecx
    1a48:	77 15                	ja     1a5f <find_poly_roots+0x52f>
    1a4a:	89 ce                	mov    esi,ecx
    1a4c:	44 89 c1             	mov    ecx,r8d
    1a4f:	29 c6                	sub    esi,eax
    1a51:	89 c7                	mov    edi,eax
    1a53:	21 f7                	and    edi,esi
    1a55:	d3 ee                	shr    esi,cl
    1a57:	01 fe                	add    esi,edi
    1a59:	39 f0                	cmp    eax,esi
    1a5b:	76 f2                	jbe    1a4f <find_poly_roots+0x51f>
    1a5d:	89 f1                	mov    ecx,esi
    1a5f:	41 89 0f             	mov    DWORD PTR [r15],ecx
    1a62:	49 8b 4c 24 20       	mov    rcx,QWORD PTR [r12+0x20]
    1a67:	41 8b 74 24 04       	mov    esi,DWORD PTR [r12+0x4]
    1a6c:	8b 45 b8             	mov    eax,DWORD PTR [rbp-0x48]
    1a6f:	0f b7 14 11          	movzx  edx,WORD PTR [rcx+rdx*1]
    1a73:	8d 04 70             	lea    eax,[rax+rsi*2]
    1a76:	2b 45 b0             	sub    eax,DWORD PTR [rbp-0x50]
    1a79:	29 d0                	sub    eax,edx
    1a7b:	39 c6                	cmp    esi,eax
    1a7d:	77 12                	ja     1a91 <find_poly_roots+0x561>
    1a7f:	41 8b 0c 24          	mov    ecx,DWORD PTR [r12]
    1a83:	29 f0                	sub    eax,esi
    1a85:	89 f2                	mov    edx,esi
    1a87:	21 c2                	and    edx,eax
    1a89:	d3 e8                	shr    eax,cl
    1a8b:	01 d0                	add    eax,edx
    1a8d:	39 c6                	cmp    esi,eax
    1a8f:	76 f2                	jbe    1a83 <find_poly_roots+0x553>
    1a91:	41 89 47 04          	mov    DWORD PTR [r15+0x4],eax
    1a95:	41 be 02 00 00 00    	mov    r14d,0x2
    1a9b:	e9 da fa ff ff       	jmp    157a <find_poly_roots+0x4a>
    1aa0:	85 c0                	test   eax,eax
    1aa2:	0f 84 cf fa ff ff    	je     1577 <find_poly_roots+0x47>
    1aa8:	45 8b 0c 24          	mov    r9d,DWORD PTR [r12]
    1aac:	45 39 c1             	cmp    r9d,r8d
    1aaf:	0f 82 c2 fa ff ff    	jb     1577 <find_poly_roots+0x47>
    1ab5:	49 8b 44 24 60       	mov    rax,QWORD PTR [r12+0x60]
    1aba:	49 8b 5c 24 78       	mov    rbx,QWORD PTR [r12+0x78]
    1abf:	44 89 4d bc          	mov    DWORD PTR [rbp-0x44],r9d
    1ac3:	31 f6                	xor    esi,esi
    1ac5:	4d 8b 74 24 70       	mov    r14,QWORD PTR [r12+0x70]
    1aca:	44 89 45 c0          	mov    DWORD PTR [rbp-0x40],r8d
    1ace:	48 89 45 b0          	mov    QWORD PTR [rbp-0x50],rax
    1ad2:	49 8b 44 24 68       	mov    rax,QWORD PTR [r12+0x68]
    1ad7:	48 c7 03 01 00 00 00 	mov    QWORD PTR [rbx],0x1
    1ade:	49 8b 54 24 18       	mov    rdx,QWORD PTR [r12+0x18]
    1ae3:	4c 89 f7             	mov    rdi,r14
    1ae6:	48 89 45 a0          	mov    QWORD PTR [rbp-0x60],rax
    1aea:	49 63 c0             	movsxd rax,r8d
    1aed:	0f b7 04 42          	movzx  eax,WORD PTR [rdx+rax*2]
    1af1:	89 43 08             	mov    DWORD PTR [rbx+0x8],eax
    1af4:	41 c7 06 00 00 00 00 	mov    DWORD PTR [r14],0x0
    1afb:	41 8b 45 00          	mov    eax,DWORD PTR [r13+0x0]
    1aff:	83 c0 01             	add    eax,0x1
    1b02:	48 8d 14 85 04 00 00 00 	lea    rdx,[rax*4+0x4]
    1b0a:	48 8b 05 00 00 00 00 	mov    rax,QWORD PTR [rip+0x0]        # 1b11 <find_poly_roots+0x5e1>	1b0d: R_X86_64_PC32	vkso_bch_memset_slot-0x4
    1b11:	ff d0                	call   rax
    1b13:	49 8b 54 24 50       	mov    rdx,QWORD PTR [r12+0x50]
    1b18:	4c 89 ee             	mov    rsi,r13
    1b1b:	4c 89 e7             	mov    rdi,r12
    1b1e:	e8 2d e7 ff ff       	call   250 <gf_poly_logrep>
    1b23:	44 8b 4d bc          	mov    r9d,DWORD PTR [rbp-0x44]
    1b27:	45 31 d2             	xor    r10d,r10d
    1b2a:	44 8b 45 c0          	mov    r8d,DWORD PTR [rbp-0x40]
    1b2e:	45 85 c9             	test   r9d,r9d
    1b31:	41 8d 41 ff          	lea    eax,[r9-0x1]
    1b35:	0f 8e b5 00 00 00    	jle    1bf0 <find_poly_roots+0x6c0>
    1b3b:	44 89 45 b8          	mov    DWORD PTR [rbp-0x48],r8d
    1b3f:	45 89 d5             	mov    r13d,r10d
    1b42:	41 89 c0             	mov    r8d,eax
    1b45:	49 89 f2             	mov    r10,rsi
    1b48:	4c 89 7d a8          	mov    QWORD PTR [rbp-0x58],r15
    1b4c:	45 89 cf             	mov    r15d,r9d
    1b4f:	8b 13                	mov    edx,DWORD PTR [rbx]
    1b51:	85 d2                	test   edx,edx
    1b53:	78 72                	js     1bc7 <find_poly_roots+0x697>
    1b55:	48 63 f2             	movsxd rsi,edx
    1b58:	8d 0c 12             	lea    ecx,[rdx+rdx*1]
    1b5b:	89 d2                	mov    edx,edx
    1b5d:	48 8d 04 b5 04 00 00 00 	lea    rax,[rsi*4+0x4]
    1b65:	48 29 d6             	sub    rsi,rdx
    1b68:	48 c1 e6 02          	shl    rsi,0x2
    1b6c:	8b 14 03             	mov    edx,DWORD PTR [rbx+rax*1]
    1b6f:	41 31 14 06          	xor    DWORD PTR [r14+rax*1],edx
    1b73:	8b 14 03             	mov    edx,DWORD PTR [rbx+rax*1]
    1b76:	85 d2                	test   edx,edx
    1b78:	74 2a                	je     1ba4 <find_poly_roots+0x674>
    1b7a:	4d 8b 4c 24 20       	mov    r9,QWORD PTR [r12+0x20]
    1b7f:	49 8b 7c 24 18       	mov    rdi,QWORD PTR [r12+0x18]
    1b84:	41 0f b7 14 51       	movzx  edx,WORD PTR [r9+rdx*2]
    1b89:	45 8b 4c 24 04       	mov    r9d,DWORD PTR [r12+0x4]
    1b8e:	01 d2                	add    edx,edx
    1b90:	41 89 d3             	mov    r11d,edx
    1b93:	45 29 cb             	sub    r11d,r9d
    1b96:	44 39 ca             	cmp    edx,r9d
    1b99:	41 0f 43 d3          	cmovae edx,r11d
    1b9d:	48 63 d2             	movsxd rdx,edx
    1ba0:	0f b7 14 57          	movzx  edx,WORD PTR [rdi+rdx*2]
    1ba4:	48 63 f9             	movsxd rdi,ecx
    1ba7:	48 83 e8 04          	sub    rax,0x4
    1bab:	89 54 bb 04          	mov    DWORD PTR [rbx+rdi*4+0x4],edx
    1baf:	8d 51 01             	lea    edx,[rcx+0x1]
    1bb2:	83 e9 02             	sub    ecx,0x2
    1bb5:	48 63 d2             	movsxd rdx,edx
    1bb8:	c7 44 93 04 00 00 00 00 	mov    DWORD PTR [rbx+rdx*4+0x4],0x0
    1bc0:	48 39 f0             	cmp    rax,rsi
    1bc3:	75 a7                	jne    1b6c <find_poly_roots+0x63c>
    1bc5:	8b 13                	mov    edx,DWORD PTR [rbx]
    1bc7:	41 39 16             	cmp    DWORD PTR [r14],edx
    1bca:	73 03                	jae    1bcf <find_poly_roots+0x69f>
    1bcc:	41 89 16             	mov    DWORD PTR [r14],edx
    1bcf:	45 39 c5             	cmp    r13d,r8d
    1bd2:	0f 8c 00 01 00 00    	jl     1cd8 <find_poly_roots+0x7a8>
    1bd8:	41 83 c5 01          	add    r13d,0x1
    1bdc:	45 39 ef             	cmp    r15d,r13d
    1bdf:	0f 85 6a ff ff ff    	jne    1b4f <find_poly_roots+0x61f>
    1be5:	44 8b 45 b8          	mov    r8d,DWORD PTR [rbp-0x48]
    1be9:	4c 8b 7d a8          	mov    r15,QWORD PTR [rbp-0x58]
    1bed:	4d 89 d5             	mov    r13,r10
    1bf0:	41 8b 16             	mov    edx,DWORD PTR [r14]
    1bf3:	41 8b 4c 96 04       	mov    ecx,DWORD PTR [r14+rdx*4+0x4]
    1bf8:	48 89 d0             	mov    rax,rdx
    1bfb:	85 c9                	test   ecx,ecx
    1bfd:	74 1b                	je     1c1a <find_poly_roots+0x6ea>
    1bff:	e9 fe 00 00 00       	jmp    1d02 <find_poly_roots+0x7d2>
    1c04:	8d 50 ff             	lea    edx,[rax-0x1]
    1c07:	41 89 16             	mov    DWORD PTR [r14],edx
    1c0a:	48 89 d0             	mov    rax,rdx
    1c0d:	41 8b 54 96 04       	mov    edx,DWORD PTR [r14+rdx*4+0x4]
    1c12:	85 d2                	test   edx,edx
    1c14:	0f 85 e8 00 00 00    	jne    1d02 <find_poly_roots+0x7d2>
    1c1a:	85 c0                	test   eax,eax
    1c1c:	75 e6                	jne    1c04 <find_poly_roots+0x6d4>
    1c1e:	31 db                	xor    ebx,ebx
    1c20:	4d 85 ed             	test   r13,r13
    1c23:	0f 84 4e f9 ff ff    	je     1577 <find_poly_roots+0x47>
    1c29:	41 8d 70 01          	lea    esi,[r8+0x1]
    1c2d:	4c 89 f9             	mov    rcx,r15
    1c30:	4c 89 ea             	mov    rdx,r13
    1c33:	4c 89 e7             	mov    rdi,r12
    1c36:	44 89 45 c0          	mov    DWORD PTR [rbp-0x40],r8d
    1c3a:	e8 f1 f8 ff ff       	call   1530 <find_poly_roots>
    1c3f:	44 8b 45 c0          	mov    r8d,DWORD PTR [rbp-0x40]
    1c43:	41 89 c6             	mov    r14d,eax
    1c46:	48 85 db             	test   rbx,rbx
    1c49:	0f 84 2b f9 ff ff    	je     157a <find_poly_roots+0x4a>
    1c4f:	49 63 c6             	movsxd rax,r14d
    1c52:	41 8d 70 01          	lea    esi,[r8+0x1]
    1c56:	48 89 da             	mov    rdx,rbx
    1c59:	4c 89 e7             	mov    rdi,r12
    1c5c:	49 8d 0c 87          	lea    rcx,[r15+rax*4]
    1c60:	e8 cb f8 ff ff       	call   1530 <find_poly_roots>
    1c65:	41 01 c6             	add    r14d,eax
    1c68:	e9 0d f9 ff ff       	jmp    157a <find_poly_roots+0x4a>
    1c6d:	31 db                	xor    ebx,ebx
    1c6f:	4d 89 f8             	mov    r8,r15
    1c72:	44 89 ca             	mov    edx,r9d
    1c75:	4c 89 e7             	mov    rdi,r12
    1c78:	e8 d3 ee ff ff       	call   b50 <find_affine4_roots>
    1c7d:	41 89 c6             	mov    r14d,eax
    1c80:	83 f8 04             	cmp    eax,0x4
    1c83:	0f 85 ee f8 ff ff    	jne    1577 <find_poly_roots+0x47>
    1c89:	49 8d 77 10          	lea    rsi,[r15+0x10]
    1c8d:	41 8b 4c 24 04       	mov    ecx,DWORD PTR [r12+0x4]
    1c92:	49 8b 54 24 20       	mov    rdx,QWORD PTR [r12+0x20]
    1c97:	41 8b 07             	mov    eax,DWORD PTR [r15]
    1c9a:	85 db                	test   ebx,ebx
    1c9c:	74 11                	je     1caf <find_poly_roots+0x77f>
    1c9e:	0f b7 04 42          	movzx  eax,WORD PTR [rdx+rax*2]
    1ca2:	89 cf                	mov    edi,ecx
    1ca4:	29 c7                	sub    edi,eax
    1ca6:	49 8b 44 24 18       	mov    rax,QWORD PTR [r12+0x18]
    1cab:	0f b7 04 78          	movzx  eax,WORD PTR [rax+rdi*2]
    1caf:	44 31 e8             	xor    eax,r13d
    1cb2:	0f b7 14 42          	movzx  edx,WORD PTR [rdx+rax*2]
    1cb6:	89 c8                	mov    eax,ecx
    1cb8:	29 d0                	sub    eax,edx
    1cba:	f7 da                	neg    edx
    1cbc:	39 c8                	cmp    eax,ecx
    1cbe:	0f 43 c2             	cmovae eax,edx
    1cc1:	49 83 c7 04          	add    r15,0x4
    1cc5:	41 89 47 fc          	mov    DWORD PTR [r15-0x4],eax
    1cc9:	4c 39 fe             	cmp    rsi,r15
    1ccc:	75 bf                	jne    1c8d <find_poly_roots+0x75d>
    1cce:	e9 a7 f8 ff ff       	jmp    157a <find_poly_roots+0x4a>
    1cd3:	45 31 ed             	xor    r13d,r13d
    1cd6:	eb 97                	jmp    1c6f <find_poly_roots+0x73f>
    1cd8:	d1 23                	shl    DWORD PTR [rbx],1
    1cda:	49 8b 4c 24 50       	mov    rcx,QWORD PTR [r12+0x50]
    1cdf:	4c 89 d2             	mov    rdx,r10
    1ce2:	48 89 de             	mov    rsi,rbx
    1ce5:	4c 89 e7             	mov    rdi,r12
    1ce8:	44 89 45 bc          	mov    DWORD PTR [rbp-0x44],r8d
    1cec:	4c 89 55 c0          	mov    QWORD PTR [rbp-0x40],r10
    1cf0:	e8 bb e5 ff ff       	call   2b0 <gf_poly_mod>
    1cf5:	44 8b 45 bc          	mov    r8d,DWORD PTR [rbp-0x44]
    1cf9:	4c 8b 55 c0          	mov    r10,QWORD PTR [rbp-0x40]
    1cfd:	e9 d6 fe ff ff       	jmp    1bd8 <find_poly_roots+0x6a8>
    1d02:	85 c0                	test   eax,eax
    1d04:	0f 84 14 ff ff ff    	je     1c1e <find_poly_roots+0x6ee>
    1d0a:	41 8b 45 00          	mov    eax,DWORD PTR [r13+0x0]
    1d0e:	48 8b 5d b0          	mov    rbx,QWORD PTR [rbp-0x50]
    1d12:	44 89 45 c0          	mov    DWORD PTR [rbp-0x40],r8d
    1d16:	4c 89 ee             	mov    rsi,r13
    1d19:	83 c0 01             	add    eax,0x1
    1d1c:	48 89 df             	mov    rdi,rbx
    1d1f:	48 8d 14 85 04 00 00 00 	lea    rdx,[rax*4+0x4]
    1d27:	48 8b 05 00 00 00 00 	mov    rax,QWORD PTR [rip+0x0]        # 1d2e <find_poly_roots+0x7fe>	1d2a: R_X86_64_PC32	vkso_bch_memcpy_slot-0x4
    1d2e:	ff d0                	call   rax
    1d30:	8b 03                	mov    eax,DWORD PTR [rbx]
    1d32:	41 8b 16             	mov    edx,DWORD PTR [r14]
    1d35:	44 8b 45 c0          	mov    r8d,DWORD PTR [rbp-0x40]
    1d39:	39 d0                	cmp    eax,edx
    1d3b:	72 0c                	jb     1d49 <find_poly_roots+0x819>
    1d3d:	89 d0                	mov    eax,edx
    1d3f:	4c 89 f2             	mov    rdx,r14
    1d42:	49 89 de             	mov    r14,rbx
    1d45:	48 89 55 b0          	mov    QWORD PTR [rbp-0x50],rdx
    1d49:	85 c0                	test   eax,eax
    1d4b:	0f 84 fc 00 00 00    	je     1e4d <find_poly_roots+0x91d>
    1d51:	44 89 45 c0          	mov    DWORD PTR [rbp-0x40],r8d
    1d55:	48 8b 5d b0          	mov    rbx,QWORD PTR [rbp-0x50]
    1d59:	eb 09                	jmp    1d64 <find_poly_roots+0x834>
    1d5b:	4c 89 f2             	mov    rdx,r14
    1d5e:	49 89 de             	mov    r14,rbx
    1d61:	48 89 d3             	mov    rbx,rdx
    1d64:	31 c9                	xor    ecx,ecx
    1d66:	48 89 da             	mov    rdx,rbx
    1d69:	4c 89 f6             	mov    rsi,r14
    1d6c:	4c 89 e7             	mov    rdi,r12
    1d6f:	e8 3c e5 ff ff       	call   2b0 <gf_poly_mod>
    1d74:	41 8b 06             	mov    eax,DWORD PTR [r14]
    1d77:	85 c0                	test   eax,eax
    1d79:	75 e0                	jne    1d5b <find_poly_roots+0x82b>
    1d7b:	48 89 5d b0          	mov    QWORD PTR [rbp-0x50],rbx
    1d7f:	44 8b 45 c0          	mov    r8d,DWORD PTR [rbp-0x40]
    1d83:	48 8b 45 b0          	mov    rax,QWORD PTR [rbp-0x50]
    1d87:	8b 10                	mov    edx,DWORD PTR [rax]
    1d89:	41 8b 45 00          	mov    eax,DWORD PTR [r13+0x0]
    1d8d:	39 c2                	cmp    edx,eax
    1d8f:	0f 83 89 fe ff ff    	jae    1c1e <find_poly_roots+0x6ee>
    1d95:	4c 8b 75 a0          	mov    r14,QWORD PTR [rbp-0x60]
    1d99:	29 d0                	sub    eax,edx
    1d9b:	48 8b 5d b0          	mov    rbx,QWORD PTR [rbp-0x50]
    1d9f:	31 c9                	xor    ecx,ecx
    1da1:	4c 89 ee             	mov    rsi,r13
    1da4:	4c 89 e7             	mov    rdi,r12
    1da7:	44 89 45 c0          	mov    DWORD PTR [rbp-0x40],r8d
    1dab:	41 89 06             	mov    DWORD PTR [r14],eax
    1dae:	48 89 da             	mov    rdx,rbx
    1db1:	e8 fa e4 ff ff       	call   2b0 <gf_poly_mod>
    1db6:	41 8b 06             	mov    eax,DWORD PTR [r14]
    1db9:	49 8d 7e 04          	lea    rdi,[r14+0x4]
    1dbd:	8d 50 01             	lea    edx,[rax+0x1]
    1dc0:	8b 03                	mov    eax,DWORD PTR [rbx]
    1dc2:	48 c1 e2 02          	shl    rdx,0x2
    1dc6:	49 8d 74 85 04       	lea    rsi,[r13+rax*4+0x4]
    1dcb:	48 8b 05 00 00 00 00 	mov    rax,QWORD PTR [rip+0x0]        # 1dd2 <find_poly_roots+0x8a2>	1dce: R_X86_64_PC32	vkso_bch_memcpy_slot-0x4
    1dd2:	ff d0                	call   rax
    1dd4:	8b 13                	mov    edx,DWORD PTR [rbx]
    1dd6:	48 89 de             	mov    rsi,rbx
    1dd9:	4c 89 ef             	mov    rdi,r13
    1ddc:	48 89 d0             	mov    rax,rdx
    1ddf:	48 8d 14 52          	lea    rdx,[rdx+rdx*2]
    1de3:	83 c0 01             	add    eax,0x1
    1de6:	49 8d 5c 95 00       	lea    rbx,[r13+rdx*4+0x0]
    1deb:	48 8d 14 85 04 00 00 00 	lea    rdx,[rax*4+0x4]
    1df3:	48 8b 05 00 00 00 00 	mov    rax,QWORD PTR [rip+0x0]        # 1dfa <find_poly_roots+0x8ca>	1df6: R_X86_64_PC32	vkso_bch_memcpy_slot-0x4
    1dfa:	ff d0                	call   rax
    1dfc:	41 8b 06             	mov    eax,DWORD PTR [r14]
    1dff:	4c 89 f6             	mov    rsi,r14
    1e02:	48 89 df             	mov    rdi,rbx
    1e05:	45 31 f6             	xor    r14d,r14d
    1e08:	83 c0 01             	add    eax,0x1
    1e0b:	48 8d 14 85 04 00 00 00 	lea    rdx,[rax*4+0x4]
    1e13:	48 8b 05 00 00 00 00 	mov    rax,QWORD PTR [rip+0x0]        # 1e1a <find_poly_roots+0x8ea>	1e16: R_X86_64_PC32	vkso_bch_memcpy_slot-0x4
    1e1a:	ff d0                	call   rax
    1e1c:	4d 85 ed             	test   r13,r13
    1e1f:	44 8b 45 c0          	mov    r8d,DWORD PTR [rbp-0x40]
    1e23:	0f 85 00 fe ff ff    	jne    1c29 <find_poly_roots+0x6f9>
    1e29:	e9 18 fe ff ff       	jmp    1c46 <find_poly_roots+0x716>
    1e2e:	45 89 cd             	mov    r13d,r9d
    1e31:	45 89 d9             	mov    r9d,r11d
    1e34:	e9 36 fe ff ff       	jmp    1c6f <find_poly_roots+0x73f>
    1e39:	31 c9                	xor    ecx,ecx
    1e3b:	e9 e2 f8 ff ff       	jmp    1722 <find_poly_roots+0x1f2>
    1e40:	0f b7 3b             	movzx  edi,WORD PTR [rbx]
    1e43:	ba 02 00 00 00       	mov    edx,0x2
    1e48:	e9 ee fb ff ff       	jmp    1a3b <find_poly_roots+0x50b>
    1e4d:	4c 89 75 b0          	mov    QWORD PTR [rbp-0x50],r14
    1e51:	e9 2d ff ff ff       	jmp    1d83 <find_poly_roots+0x853>
    1e56:	45 31 d2             	xor    r10d,r10d
    1e59:	85 f6                	test   esi,esi
    1e5b:	74 08                	je     1e65 <find_poly_roots+0x935>
    1e5d:	84 d2                	test   dl,dl
    1e5f:	0f 85 5b fa ff ff    	jne    18c0 <find_poly_roots+0x390>
    1e65:	85 db                	test   ebx,ebx
    1e67:	0f 84 8e fa ff ff    	je     18fb <find_poly_roots+0x3cb>
    1e6d:	42 0f b7 14 41       	movzx  edx,WORD PTR [rcx+r8*2]
    1e72:	e9 70 fa ff ff       	jmp    18e7 <find_poly_roots+0x3b7>

Disassembly of section .init.text:

Disassembly of section .exit.text:
