
/home/zzk/BinaryKernelCodeMapping/test/test_BCH/build/bch-bench:     file format elf64-x86-64


Disassembly of section .text:

000000000000222e <main+0xf2e>:
    222e:	48 8b 44 24 10       	mov    rax,QWORD PTR [rsp+0x10]
    2233:	4c 8b 7c 24 70       	mov    r15,QWORD PTR [rsp+0x70]
    2238:	48 c7 44 24 18 00 00 00 00 	mov    QWORD PTR [rsp+0x18],0x0
    2241:	89 44 24 28          	mov    DWORD PTR [rsp+0x28],eax
    2245:	89 44 24 20          	mov    DWORD PTR [rsp+0x20],eax
    2249:	48 c1 e0 28          	shl    rax,0x28
    224d:	48 89 44 24 58       	mov    QWORD PTR [rsp+0x58],rax
    2252:	8b 44 24 28          	mov    eax,DWORD PTR [rsp+0x28]
    2256:	48 8b 6c 24 18       	mov    rbp,QWORD PTR [rsp+0x18]
    225b:	41 89 c4             	mov    r12d,eax
    225e:	8d 58 03             	lea    ebx,[rax+0x3]
    2261:	44 89 e0             	mov    eax,r12d
    2264:	be ab aa aa aa       	mov    esi,0xaaaaaaab
    2269:	48 0f af c6          	imul   rax,rsi
    226d:	48 8b 74 24 40       	mov    rsi,QWORD PTR [rsp+0x40]
    2272:	48 c1 e8 21          	shr    rax,0x21
    2276:	8d 14 40             	lea    edx,[rax+rax*2]
    2279:	44 89 e0             	mov    eax,r12d
    227c:	41 83 c4 01          	add    r12d,0x1
    2280:	29 d0                	sub    eax,edx
    2282:	48 98                	cdqe   
    2284:	48 8d 54 45 00       	lea    rdx,[rbp+rax*2+0x0]
    2289:	48 8d 04 c0          	lea    rax,[rax+rax*8]
    228d:	4c 8b b4 d4 60 01 00 00 	mov    r14,QWORD PTR [rsp+rdx*8+0x160]
    2295:	4c 8d 2c c6          	lea    r13,[rsi+rax*8]
    2299:	41 8b 57 04          	mov    edx,DWORD PTR [r15+0x4]
    229d:	41 8b 37             	mov    esi,DWORD PTR [r15]
    22a0:	4c 89 ef             	mov    rdi,r13
    22a3:	4c 89 f1             	mov    rcx,r14
    22a6:	e8 75 08 00 00       	call   2b20 <measure_init>
    22ab:	41 8b 4f 04          	mov    ecx,DWORD PTR [r15+0x4]
    22af:	45 8b 47 08          	mov    r8d,DWORD PTR [r15+0x8]
    22b3:	41 b9 ff ff ff ff    	mov    r9d,0xffffffff
    22b9:	50                   	push   rax
    22ba:	48 8d 05 a7 1f 00 00 	lea    rax,[rip+0x1fa7]        # 4268 <_IO_stdin_used+0x268>
    22c1:	41 8b 17             	mov    edx,DWORD PTR [r15]
    22c4:	41 56                	push   r14
    22c6:	41 ff 75 00          	push   QWORD PTR [r13+0x0]
    22ca:	50                   	push   rax
    22cb:	8b 74 24 40          	mov    esi,DWORD PTR [rsp+0x40]
    22cf:	48 8b 7c 24 28       	mov    rdi,QWORD PTR [rsp+0x28]
    22d4:	e8 37 09 00 00       	call   2c10 <write_row.isra.0>
    22d9:	48 83 c4 20          	add    rsp,0x20
    22dd:	44 39 e3             	cmp    ebx,r12d
    22e0:	0f 85 7b ff ff ff    	jne    2261 <main+0xf61>
    22e6:	48 8b 44 24 18       	mov    rax,QWORD PTR [rsp+0x18]
    22eb:	45 31 f6             	xor    r14d,r14d
    22ee:	48 c1 e0 20          	shl    rax,0x20
    22f2:	48 89 44 24 60       	mov    QWORD PTR [rsp+0x60],rax
    22f7:	48 8d 44 6d 00       	lea    rax,[rbp+rbp*2+0x0]
    22fc:	48 8d 04 c0          	lea    rax,[rax+rax*8]
    2300:	48 89 84 24 a0 00 00 00 	mov    QWORD PTR [rsp+0xa0],rax
    2308:	44 89 74 24 78       	mov    DWORD PTR [rsp+0x78],r14d
    230d:	44 89 b4 24 80 00 00 00 	mov    DWORD PTR [rsp+0x80],r14d
    2315:	4d 85 f6             	test   r14,r14
    2318:	0f 84 31 04 00 00    	je     274f <main+0x144f>
    231e:	41 8b 47 04          	mov    eax,DWORD PTR [r15+0x4]
    2322:	89 44 24 38          	mov    DWORD PTR [rsp+0x38],eax
    2326:	85 c0                	test   eax,eax
    2328:	0f 88 d1 01 00 00    	js     24ff <main+0x11ff>
    232e:	4c 89 f0             	mov    rax,r14
    2331:	4c 89 74 24 30       	mov    QWORD PTR [rsp+0x30],r14
    2336:	45 31 ed             	xor    r13d,r13d
    2339:	48 8d ac 24 00 01 00 00 	lea    rbp,[rsp+0x100]
    2341:	48 c1 e0 18          	shl    rax,0x18
    2345:	48 89 44 24 68       	mov    QWORD PTR [rsp+0x68],rax
    234a:	8b 44 24 28          	mov    eax,DWORD PTR [rsp+0x28]
    234e:	44 01 f0             	add    eax,r14d
    2351:	89 44 24 48          	mov    DWORD PTR [rsp+0x48],eax
    2355:	48 8d 84 24 40 01 00 00 	lea    rax,[rsp+0x140]
    235d:	48 89 44 24 50       	mov    QWORD PTR [rsp+0x50],rax
    2362:	44 89 f0             	mov    eax,r14d
    2365:	48 8d 04 c0          	lea    rax,[rax+rax*8]
    2369:	48 89 84 24 90 00 00 00 	mov    QWORD PTR [rsp+0x90],rax
    2371:	48 8b 4c 24 58       	mov    rcx,QWORD PTR [rsp+0x58]
    2376:	41 8b 57 08          	mov    edx,DWORD PTR [r15+0x8]
    237a:	44 89 ee             	mov    esi,r13d
    237d:	44 89 eb             	mov    ebx,r13d
    2380:	48 b8 15 7c 4a 7f b9 79 37 9e 	movabs rax,0x9e3779b97f4a7c15
    238a:	48 8b 7c 24 50       	mov    rdi,QWORD PTR [rsp+0x50]
    238f:	4c 31 e9             	xor    rcx,r13
    2392:	48 33 4c 24 60       	xor    rcx,QWORD PTR [rsp+0x60]
    2397:	48 33 4c 24 68       	xor    rcx,QWORD PTR [rsp+0x68]
    239c:	48 31 c1             	xor    rcx,rax
    239f:	41 8b 47 0c          	mov    eax,DWORD PTR [r15+0xc]
    23a3:	8d 14 d0             	lea    edx,[rax+rdx*8]
    23a6:	e8 c5 05 00 00       	call   2970 <generate_error_vector>
