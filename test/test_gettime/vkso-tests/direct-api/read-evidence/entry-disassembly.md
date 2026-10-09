# Actual clean READ package instructions

## normal: direct/libvkso_time.so: clock_gettime

```asm
0000000000001200 <clock_gettime>:
    1200:	f3 0f 1e fa          	endbr64 
    1204:	48 83 ec 08          	sub    $0x8,%rsp
    1208:	ff 15 aa 2d 00 00    	call   *0x2daa(%rip)        # 3fb8 <__vkso_clock_gettime@Base>
    120e:	85 c0                	test   %eax,%eax
    1210:	0f 88 0c ff ff ff    	js     1122 <clock_gettime.cold>
    1216:	48 83 c4 08          	add    $0x8,%rsp
    121a:	c3                   	ret    
    121b:	0f 1f 44 00 00       	nopl   0x0(%rax,%rax,1)
```

## normal: direct/libvkso_time.so: clock_getres

```asm
0000000000001220 <clock_getres>:
    1220:	f3 0f 1e fa          	endbr64 
    1224:	48 83 ec 08          	sub    $0x8,%rsp
    1228:	ff 15 b2 2d 00 00    	call   *0x2db2(%rip)        # 3fe0 <__vkso_clock_getres@Base>
    122e:	85 c0                	test   %eax,%eax
    1230:	0f 88 f1 fe ff ff    	js     1127 <clock_getres.cold>
    1236:	48 83 c4 08          	add    $0x8,%rsp
    123a:	c3                   	ret    
    123b:	0f 1f 44 00 00       	nopl   0x0(%rax,%rax,1)
```

## normal: direct/libvkso_time.so: resolve_gettimeofday

```asm
0000000000001270 <resolve_gettimeofday>:
    1270:	f3 0f 1e fa          	endbr64 
    1274:	48 8b 05 55 2d 00 00 	mov    0x2d55(%rip),%rax        # 3fd0 <__vkso_gettimeofday@Base>
    127b:	c3                   	ret    
    127c:	0f 1f 40 00          	nopl   0x0(%rax)
```

## normal: direct/libvkso_time.so: resolve_time

```asm
0000000000001280 <resolve_time>:
    1280:	f3 0f 1e fa          	endbr64 
    1284:	48 8b 05 4d 2d 00 00 	mov    0x2d4d(%rip),%rax        # 3fd8 <__vkso_time@Base>
    128b:	c3                   	ret    
    128c:	0f 1f 40 00          	nopl   0x0(%rax)
```

## normal: direct/libvkso_time.so: getcpu

```asm
0000000000001290 <getcpu>:
    1290:	f3 0f 1e fa          	endbr64 
    1294:	48 83 ec 08          	sub    $0x8,%rsp
    1298:	31 d2                	xor    %edx,%edx
    129a:	ff 15 58 2d 00 00    	call   *0x2d58(%rip)        # 3ff8 <__vkso_getcpu@Base>
    12a0:	85 c0                	test   %eax,%eax
    12a2:	0f 88 88 fe ff ff    	js     1130 <getcpu.cold>
    12a8:	48 83 c4 08          	add    $0x8,%rsp
    12ac:	c3                   	ret    
    12ad:	0f 1f 00             	nopl   (%rax)
```

## normal: libkernel.so: __vkso_getcpu

```asm
0000000000001000 <__vkso_getcpu>:
	...
```

## normal: libkernel.so: vkso_clock_gettime_hres

```asm
0000000000001060 <vkso_clock_gettime_hres>:
	...
```

## normal: libkernel.so: vkso_clock_gettime_coarse

```asm
0000000000001220 <vkso_clock_gettime_coarse>:
	...
```

## normal: libkernel.so: __vkso_time

```asm
0000000000001450 <__vkso_time>:
	...
```

## normal: libkernel.so: __vkso_clock_gettime

```asm
0000000001601000 <__vkso_clock_gettime>:
 1601000:	83 ff 0b             	cmp    $0xb,%edi
 1601003:	77 14                	ja     1601019 <__vkso_clock_gettime+0x19>
 1601005:	b8 93 08 00 00       	mov    $0x893,%eax
 160100a:	0f a3 f8             	bt     %edi,%eax
 160100d:	72 15                	jb     1601024 <__vkso_clock_gettime+0x24>
 160100f:	b8 60 00 00 00       	mov    $0x60,%eax
 1601014:	0f a3 f8             	bt     %edi,%eax
 1601017:	72 1e                	jb     1601037 <__vkso_clock_gettime+0x37>
 1601019:	48 63 ff             	movslq %edi,%rdi
 160101c:	b8 e4 00 00 00       	mov    $0xe4,%eax
 1601021:	0f 05                	syscall 
 1601023:	c3                   	ret    
 1601024:	48 8b 15 d5 0f 00 00 	mov    0xfd5(%rip),%rdx        # 1602000 <__vkso_shared_data+0xf00>
 160102b:	48 8d 0d d6 0f 00 00 	lea    0xfd6(%rip),%rcx        # 1602008 <__vkso_shared_data+0xf08>
 1601032:	e9 29 00 a0 fe       	jmp    1060 <vkso_clock_gettime_hres>
 1601037:	48 8b 15 c2 0f 00 00 	mov    0xfc2(%rip),%rdx        # 1602000 <__vkso_shared_data+0xf00>
 160103e:	e9 dd 01 a0 fe       	jmp    1220 <vkso_clock_gettime_coarse>
 1601043:	66 66 2e 0f 1f 84 00 00 00 00 00 	data16 cs nopw 0x0(%rax,%rax,1)
 160104e:	66 90                	xchg   %ax,%ax
```

## normal: libkernel.so: __vkso_clock_getres

```asm
0000000001601050 <__vkso_clock_getres>:
 1601050:	83 ff 0b             	cmp    $0xb,%edi
 1601053:	77 14                	ja     1601069 <__vkso_clock_getres+0x19>
 1601055:	b8 93 08 00 00       	mov    $0x893,%eax
 160105a:	0f a3 f8             	bt     %edi,%eax
 160105d:	72 15                	jb     1601074 <__vkso_clock_getres+0x24>
 160105f:	b8 60 00 00 00       	mov    $0x60,%eax
 1601064:	0f a3 f8             	bt     %edi,%eax
 1601067:	72 13                	jb     160107c <__vkso_clock_getres+0x2c>
 1601069:	48 63 ff             	movslq %edi,%rdi
 160106c:	b8 e5 00 00 00       	mov    $0xe5,%eax
 1601071:	0f 05                	syscall 
 1601073:	c3                   	ret    
 1601074:	48 89 f7             	mov    %rsi,%rdi
 1601077:	e9 64 02 a0 fe       	jmp    12e0 <vkso_clock_getres_hres>
 160107c:	48 89 f7             	mov    %rsi,%rdi
 160107f:	e9 8c 02 a0 fe       	jmp    1310 <vkso_clock_getres_coarse>
 1601084:	66 66 2e 0f 1f 84 00 00 00 00 00 	data16 cs nopw 0x0(%rax,%rax,1)
 160108f:	90                   	nop
```

## normal: libkernel.so: __vkso_gettimeofday

```asm
0000000001601090 <__vkso_gettimeofday>:
 1601090:	48 8d 15 71 0f 00 00 	lea    0xf71(%rip),%rdx        # 1602008 <__vkso_shared_data+0xf08>
 1601097:	e9 94 02 a0 fe       	jmp    1330 <vkso_gettimeofday_core>
 160109c:	b8 60 00 00 00       	mov    $0x60,%eax
 16010a1:	0f 05                	syscall 
 16010a3:	c3                   	ret    
 16010a4:	66 66 2e 0f 1f 84 00 00 00 00 00 	data16 cs nopw 0x0(%rax,%rax,1)
 16010af:	90                   	nop
```

## normal: raw-kernel-reader.ko: run_batch

```asm
0000000000000310 <run_batch>:
 310:	55                   	push   %rbp
 311:	48 89 e5             	mov    %rsp,%rbp
 314:	41 56                	push   %r14
 316:	41 55                	push   %r13
 318:	41 54                	push   %r12
 31a:	53                   	push   %rbx
 31b:	89 f3                	mov    %esi,%ebx
 31d:	48 83 ec 18          	sub    $0x18,%rsp
 321:	65 48 8b 04 25 28 00 00 00 	mov    %gs:0x28,%rax
 32a:	48 89 45 d8          	mov    %rax,-0x28(%rbp)
 32e:	31 c0                	xor    %eax,%eax
 330:	83 ff 01             	cmp    $0x1,%edi
 333:	74 52                	je     387 <run_batch+0x77>
 335:	83 ff 02             	cmp    $0x2,%edi
 338:	75 79                	jne    3b3 <run_batch+0xa3>
 33a:	45 31 f6             	xor    %r14d,%r14d
 33d:	45 31 e4             	xor    %r12d,%r12d
 340:	4c 8d 6d c8          	lea    -0x38(%rbp),%r13
 344:	85 f6                	test   %esi,%esi
 346:	74 1c                	je     364 <run_batch+0x54>
 348:	4c 89 ef             	mov    %r13,%rdi
 34b:	41 83 c6 01          	add    $0x1,%r14d
 34f:	e8 00 00 00 00       	call   354 <run_batch+0x44>	350: R_X86_64_PLT32	ktime_get_coarse_ts64-0x4
 354:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 358:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 35c:	49 01 c4             	add    %rax,%r12
 35f:	44 39 f3             	cmp    %r14d,%ebx
 362:	75 e4                	jne    348 <run_batch+0x38>
 364:	48 8b 45 d8          	mov    -0x28(%rbp),%rax
 368:	65 48 2b 04 25 28 00 00 00 	sub    %gs:0x28,%rax
 371:	75 6c                	jne    3df <run_batch+0xcf>
 373:	48 83 c4 18          	add    $0x18,%rsp
 377:	4c 89 e0             	mov    %r12,%rax
 37a:	5b                   	pop    %rbx
 37b:	41 5c                	pop    %r12
 37d:	41 5d                	pop    %r13
 37f:	41 5e                	pop    %r14
 381:	5d                   	pop    %rbp
 382:	e9 00 00 00 00       	jmp    387 <run_batch+0x77>	383: R_X86_64_PLT32	__x86_return_thunk-0x4
 387:	45 31 f6             	xor    %r14d,%r14d
 38a:	45 31 e4             	xor    %r12d,%r12d
 38d:	4c 8d 6d c8          	lea    -0x38(%rbp),%r13
 391:	85 f6                	test   %esi,%esi
 393:	74 cf                	je     364 <run_batch+0x54>
 395:	4c 89 ef             	mov    %r13,%rdi
 398:	41 83 c6 01          	add    $0x1,%r14d
 39c:	e8 00 00 00 00       	call   3a1 <run_batch+0x91>	39d: R_X86_64_PLT32	ktime_get_raw_ts64-0x4
 3a1:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 3a5:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 3a9:	49 01 c4             	add    %rax,%r12
 3ac:	44 39 f3             	cmp    %r14d,%ebx
 3af:	75 e4                	jne    395 <run_batch+0x85>
 3b1:	eb b1                	jmp    364 <run_batch+0x54>
 3b3:	45 31 f6             	xor    %r14d,%r14d
 3b6:	45 31 e4             	xor    %r12d,%r12d
 3b9:	4c 8d 6d c8          	lea    -0x38(%rbp),%r13
 3bd:	85 f6                	test   %esi,%esi
 3bf:	74 a3                	je     364 <run_batch+0x54>
 3c1:	4c 89 ef             	mov    %r13,%rdi
 3c4:	41 83 c6 01          	add    $0x1,%r14d
 3c8:	e8 00 00 00 00       	call   3cd <run_batch+0xbd>	3c9: R_X86_64_PLT32	ktime_get_ts64-0x4
 3cd:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 3d1:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 3d5:	49 01 c4             	add    %rax,%r12
 3d8:	44 39 f3             	cmp    %r14d,%ebx
 3db:	75 e4                	jne    3c1 <run_batch+0xb1>
 3dd:	eb 85                	jmp    364 <run_batch+0x54>
 3df:	e8 00 00 00 00       	call   3e4 <run_batch+0xd4>	3e0: R_X86_64_PLT32	__stack_chk_fail-0x4
 3e4:	66 66 2e 0f 1f 84 00 00 00 00 00 	data16 cs nopw 0x0(%rax,%rax,1)
 3ef:	90                   	nop
```

## normal: raw-kernel-reader.ko: measure_on_cpu

```asm
00000000000003f0 <measure_on_cpu>:
 3f0:	8b 47 08             	mov    0x8(%rdi),%eax
 3f3:	85 c0                	test   %eax,%eax
 3f5:	0f 84 e1 00 00 00    	je     4dc <measure_on_cpu+0xec>
 3fb:	55                   	push   %rbp
 3fc:	48 89 e5             	mov    %rsp,%rbp
 3ff:	41 57                	push   %r15
 401:	49 89 ff             	mov    %rdi,%r15
 404:	41 56                	push   %r14
 406:	41 55                	push   %r13
 408:	41 bd 03 00 00 00    	mov    $0x3,%r13d
 40e:	41 54                	push   %r12
 410:	53                   	push   %rbx
 411:	48 83 ec 10          	sub    $0x10,%rsp
 415:	45 8d 65 fd          	lea    -0x3(%r13),%r12d
 419:	4b 8d 04 64          	lea    (%r12,%r12,2),%rax
 41d:	4d 89 e6             	mov    %r12,%r14
 420:	48 89 45 c8          	mov    %rax,-0x38(%rbp)
 424:	b8 ab aa aa aa       	mov    $0xaaaaaaab,%eax
 429:	41 8b 77 0c          	mov    0xc(%r15),%esi
 42d:	4c 0f af e0          	imul   %rax,%r12
 431:	49 c1 ec 21          	shr    $0x21,%r12
 435:	43 8d 04 64          	lea    (%r12,%r12,2),%eax
 439:	45 89 f4             	mov    %r14d,%r12d
 43c:	41 29 c4             	sub    %eax,%r12d
 43f:	44 89 e0             	mov    %r12d,%eax
 442:	48 03 45 c8          	add    -0x38(%rbp),%rax
 446:	44 89 e7             	mov    %r12d,%edi
 449:	48 8d 14 40          	lea    (%rax,%rax,2),%rdx
 44d:	49 8b 47 10          	mov    0x10(%r15),%rax
 451:	48 8d 1c d0          	lea    (%rax,%rdx,8),%rbx
 455:	e8 b6 fe ff ff       	call   310 <run_batch>
 45a:	48 89 43 08          	mov    %rax,0x8(%rbx)
 45e:	0f 31                	rdtsc  
 460:	90                   	nop
 461:	90                   	nop
 462:	90                   	nop
 463:	41 8b 77 04          	mov    0x4(%r15),%esi
 467:	48 c1 e2 20          	shl    $0x20,%rdx
 46b:	44 89 e7             	mov    %r12d,%edi
 46e:	48 09 c2             	or     %rax,%rdx
 471:	48 89 55 d0          	mov    %rdx,-0x30(%rbp)
 475:	e8 96 fe ff ff       	call   310 <run_batch>
 47a:	48 31 43 08          	xor    %rax,0x8(%rbx)
 47e:	0f 31                	rdtsc  
 480:	90                   	nop
 481:	90                   	nop
 482:	90                   	nop
 483:	48 c1 e2 20          	shl    $0x20,%rdx
 487:	41 83 c6 01          	add    $0x1,%r14d
 48b:	48 09 c2             	or     %rax,%rdx
 48e:	48 2b 55 d0          	sub    -0x30(%rbp),%rdx
 492:	48 89 13             	mov    %rdx,(%rbx)
 495:	65 8b 05 00 00 00 00 	mov    %gs:0x0(%rip),%eax        # 49c <measure_on_cpu+0xac>	498: R_X86_64_PC32	cpu_number-0x4
 49c:	89 43 10             	mov    %eax,0x10(%rbx)
 49f:	45 39 f5             	cmp    %r14d,%r13d
 4a2:	74 08                	je     4ac <measure_on_cpu+0xbc>
 4a4:	45 89 f4             	mov    %r14d,%r12d
 4a7:	e9 78 ff ff ff       	jmp    424 <measure_on_cpu+0x34>
 4ac:	e8 00 00 00 00       	call   4b1 <measure_on_cpu+0xc1>	4ad: R_X86_64_PLT32	__cond_resched-0x4
 4b1:	41 8d 45 01          	lea    0x1(%r13),%eax
 4b5:	41 83 ed 02          	sub    $0x2,%r13d
 4b9:	45 39 6f 08          	cmp    %r13d,0x8(%r15)
 4bd:	76 08                	jbe    4c7 <measure_on_cpu+0xd7>
 4bf:	41 89 c5             	mov    %eax,%r13d
 4c2:	e9 4e ff ff ff       	jmp    415 <measure_on_cpu+0x25>
 4c7:	48 83 c4 10          	add    $0x10,%rsp
 4cb:	31 c0                	xor    %eax,%eax
 4cd:	5b                   	pop    %rbx
 4ce:	41 5c                	pop    %r12
 4d0:	41 5d                	pop    %r13
 4d2:	41 5e                	pop    %r14
 4d4:	41 5f                	pop    %r15
 4d6:	5d                   	pop    %rbp
 4d7:	e9 00 00 00 00       	jmp    4dc <measure_on_cpu+0xec>	4d8: R_X86_64_PLT32	__x86_return_thunk-0x4
 4dc:	31 c0                	xor    %eax,%eax
 4de:	e9 00 00 00 00       	jmp    4e3 <measure_on_cpu+0xf3>	4df: R_X86_64_PLT32	__x86_return_thunk-0x4
 4e3:	66 66 2e 0f 1f 84 00 00 00 00 00 	data16 cs nopw 0x0(%rax,%rax,1)
 4ee:	66 90                	xchg   %ax,%ax
```

## normal: vkso-kernel-reader.ko: run_batch

```asm
00000000000005a0 <run_batch>:
 5a0:	55                   	push   %rbp
 5a1:	48 89 e5             	mov    %rsp,%rbp
 5a4:	41 56                	push   %r14
 5a6:	41 55                	push   %r13
 5a8:	41 89 f5             	mov    %esi,%r13d
 5ab:	41 54                	push   %r12
 5ad:	53                   	push   %rbx
 5ae:	48 83 ec 18          	sub    $0x18,%rsp
 5b2:	65 48 8b 04 25 28 00 00 00 	mov    %gs:0x28,%rax
 5bb:	48 89 45 d8          	mov    %rax,-0x28(%rbp)
 5bf:	31 c0                	xor    %eax,%eax
 5c1:	83 ff 01             	cmp    $0x1,%edi
 5c4:	74 35                	je     5fb <run_batch+0x5b>
 5c6:	89 fb                	mov    %edi,%ebx
 5c8:	83 ff 02             	cmp    $0x2,%edi
 5cb:	74 7d                	je     64a <run_batch+0xaa>
 5cd:	45 31 e4             	xor    %r12d,%r12d
 5d0:	85 ff                	test   %edi,%edi
 5d2:	74 51                	je     625 <run_batch+0x85>
 5d4:	48 8b 45 d8          	mov    -0x28(%rbp),%rax
 5d8:	65 48 2b 04 25 28 00 00 00 	sub    %gs:0x28,%rax
 5e1:	0f 85 94 00 00 00    	jne    67b <run_batch+0xdb>
 5e7:	48 83 c4 18          	add    $0x18,%rsp
 5eb:	4c 89 e0             	mov    %r12,%rax
 5ee:	5b                   	pop    %rbx
 5ef:	41 5c                	pop    %r12
 5f1:	41 5d                	pop    %r13
 5f3:	41 5e                	pop    %r14
 5f5:	5d                   	pop    %rbp
 5f6:	e9 00 00 00 00       	jmp    5fb <run_batch+0x5b>	5f7: R_X86_64_PLT32	__x86_return_thunk-0x4
 5fb:	31 db                	xor    %ebx,%ebx
 5fd:	45 31 e4             	xor    %r12d,%r12d
 600:	4c 8d 75 c8          	lea    -0x38(%rbp),%r14
 604:	85 f6                	test   %esi,%esi
 606:	74 cc                	je     5d4 <run_batch+0x34>
 608:	4c 89 f7             	mov    %r14,%rdi
 60b:	83 c3 01             	add    $0x1,%ebx
 60e:	e8 00 00 00 00       	call   613 <run_batch+0x73>	60f: R_X86_64_PLT32	ktime_get_raw_ts64-0x4
 613:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 617:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 61b:	49 01 c4             	add    %rax,%r12
 61e:	41 39 dd             	cmp    %ebx,%r13d
 621:	75 e5                	jne    608 <run_batch+0x68>
 623:	eb af                	jmp    5d4 <run_batch+0x34>
 625:	85 f6                	test   %esi,%esi
 627:	74 ab                	je     5d4 <run_batch+0x34>
 629:	4c 8d 75 c8          	lea    -0x38(%rbp),%r14
 62d:	4c 89 f7             	mov    %r14,%rdi
 630:	83 c3 01             	add    $0x1,%ebx
 633:	e8 00 00 00 00       	call   638 <run_batch+0x98>	634: R_X86_64_PLT32	ktime_get_ts64-0x4
 638:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 63c:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 640:	49 01 c4             	add    %rax,%r12
 643:	41 39 dd             	cmp    %ebx,%r13d
 646:	75 e5                	jne    62d <run_batch+0x8d>
 648:	eb 8a                	jmp    5d4 <run_batch+0x34>
 64a:	31 db                	xor    %ebx,%ebx
 64c:	45 31 e4             	xor    %r12d,%r12d
 64f:	4c 8d 75 c8          	lea    -0x38(%rbp),%r14
 653:	85 f6                	test   %esi,%esi
 655:	0f 84 79 ff ff ff    	je     5d4 <run_batch+0x34>
 65b:	4c 89 f7             	mov    %r14,%rdi
 65e:	83 c3 01             	add    $0x1,%ebx
 661:	e8 00 00 00 00       	call   666 <run_batch+0xc6>	662: R_X86_64_PLT32	ktime_get_coarse_ts64-0x4
 666:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 66a:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 66e:	49 01 c4             	add    %rax,%r12
 671:	41 39 dd             	cmp    %ebx,%r13d
 674:	75 e5                	jne    65b <run_batch+0xbb>
 676:	e9 59 ff ff ff       	jmp    5d4 <run_batch+0x34>
 67b:	e8 00 00 00 00       	call   680 <control_write>	67c: R_X86_64_PLT32	__stack_chk_fail-0x4
```

## normal: vkso-kernel-reader.ko: measure_on_cpu

```asm
0000000000000930 <measure_on_cpu>:
 930:	55                   	push   %rbp
 931:	48 89 e5             	mov    %rsp,%rbp
 934:	41 57                	push   %r15
 936:	49 89 ff             	mov    %rdi,%r15
 939:	41 56                	push   %r14
 93b:	41 55                	push   %r13
 93d:	41 54                	push   %r12
 93f:	53                   	push   %rbx
 940:	48 83 ec 38          	sub    $0x38,%rsp
 944:	65 48 8b 04 25 28 00 00 00 	mov    %gs:0x28,%rax
 94d:	48 89 44 24 30       	mov    %rax,0x30(%rsp)
 952:	31 c0                	xor    %eax,%eax
 954:	80 7f 18 00          	cmpb   $0x0,0x18(%rdi)
 958:	0f 85 2a 01 00 00    	jne    a88 <measure_on_cpu+0x158>
 95e:	c7 44 24 0c 03 00 00 00 	movl   $0x3,0xc(%rsp)
 966:	8b 44 24 0c          	mov    0xc(%rsp),%eax
 96a:	c7 44 24 08 00 00 00 00 	movl   $0x0,0x8(%rsp)
 972:	c7 04 24 00 00 00 00 	movl   $0x0,(%rsp)
 979:	89 44 24 04          	mov    %eax,0x4(%rsp)
 97d:	41 8b 47 08          	mov    0x8(%r15),%eax
 981:	85 c0                	test   %eax,%eax
 983:	0f 84 ad 00 00 00    	je     a36 <measure_on_cpu+0x106>
 989:	44 8b 24 24          	mov    (%rsp),%r12d
 98d:	31 d2                	xor    %edx,%edx
 98f:	44 89 e0             	mov    %r12d,%eax
 992:	41 8b 77 0c          	mov    0xc(%r15),%esi
 996:	f7 74 24 0c          	divl   0xc(%rsp)
 99a:	8b 44 24 08          	mov    0x8(%rsp),%eax
 99e:	01 d0                	add    %edx,%eax
 9a0:	41 89 d5             	mov    %edx,%r13d
 9a3:	41 80 7f 18 00       	cmpb   $0x0,0x18(%r15)
 9a8:	89 c0                	mov    %eax,%eax
 9aa:	44 89 ef             	mov    %r13d,%edi
 9ad:	48 8d 14 40          	lea    (%rax,%rax,2),%rdx
 9b1:	49 8b 47 10          	mov    0x10(%r15),%rax
 9b5:	4c 8d 34 d0          	lea    (%rax,%rdx,8),%r14
 9b9:	0f 84 a0 00 00 00    	je     a5f <measure_on_cpu+0x12f>
 9bf:	e8 6c f9 ff ff       	call   330 <run_scalar_batch>
 9c4:	49 89 46 08          	mov    %rax,0x8(%r14)
 9c8:	0f 31                	rdtsc  
 9ca:	90                   	nop
 9cb:	90                   	nop
 9cc:	90                   	nop
 9cd:	48 c1 e2 20          	shl    $0x20,%rdx
 9d1:	41 8b 77 04          	mov    0x4(%r15),%esi
 9d5:	44 89 ef             	mov    %r13d,%edi
 9d8:	48 89 d3             	mov    %rdx,%rbx
 9db:	48 09 c3             	or     %rax,%rbx
 9de:	e8 4d f9 ff ff       	call   330 <run_scalar_batch>
 9e3:	49 31 46 08          	xor    %rax,0x8(%r14)
 9e7:	0f 31                	rdtsc  
 9e9:	90                   	nop
 9ea:	90                   	nop
 9eb:	90                   	nop
 9ec:	48 c1 e2 20          	shl    $0x20,%rdx
 9f0:	48 09 d0             	or     %rdx,%rax
 9f3:	48 29 d8             	sub    %rbx,%rax
 9f6:	41 83 c4 01          	add    $0x1,%r12d
 9fa:	49 89 06             	mov    %rax,(%r14)
 9fd:	65 8b 05 00 00 00 00 	mov    %gs:0x0(%rip),%eax        # a04 <measure_on_cpu+0xd4>	a00: R_X86_64_PC32	cpu_number-0x4
 a04:	41 89 46 10          	mov    %eax,0x10(%r14)
 a08:	44 39 64 24 04       	cmp    %r12d,0x4(%rsp)
 a0d:	0f 85 7a ff ff ff    	jne    98d <measure_on_cpu+0x5d>
 a13:	e8 00 00 00 00       	call   a18 <measure_on_cpu+0xe8>	a14: R_X86_64_PLT32	__cond_resched-0x4
 a18:	83 04 24 01          	addl   $0x1,(%rsp)
 a1c:	8b 4c 24 0c          	mov    0xc(%rsp),%ecx
 a20:	83 44 24 04 01       	addl   $0x1,0x4(%rsp)
 a25:	8b 04 24             	mov    (%rsp),%eax
 a28:	01 4c 24 08          	add    %ecx,0x8(%rsp)
 a2c:	41 39 47 08          	cmp    %eax,0x8(%r15)
 a30:	0f 87 53 ff ff ff    	ja     989 <measure_on_cpu+0x59>
 a36:	31 c0                	xor    %eax,%eax
 a38:	48 8b 54 24 30       	mov    0x30(%rsp),%rdx
 a3d:	65 48 2b 14 25 28 00 00 00 	sub    %gs:0x28,%rdx
 a46:	0f 85 c8 01 00 00    	jne    c14 <measure_on_cpu+0x2e4>
 a4c:	48 83 c4 38          	add    $0x38,%rsp
 a50:	5b                   	pop    %rbx
 a51:	41 5c                	pop    %r12
 a53:	41 5d                	pop    %r13
 a55:	41 5e                	pop    %r14
 a57:	41 5f                	pop    %r15
 a59:	5d                   	pop    %rbp
 a5a:	e9 00 00 00 00       	jmp    a5f <measure_on_cpu+0x12f>	a5b: R_X86_64_PLT32	__x86_return_thunk-0x4
 a5f:	e8 3c fb ff ff       	call   5a0 <run_batch>
 a64:	49 89 46 08          	mov    %rax,0x8(%r14)
 a68:	0f 31                	rdtsc  
 a6a:	90                   	nop
 a6b:	90                   	nop
 a6c:	90                   	nop
 a6d:	48 c1 e2 20          	shl    $0x20,%rdx
 a71:	41 8b 77 04          	mov    0x4(%r15),%esi
 a75:	44 89 ef             	mov    %r13d,%edi
 a78:	48 89 d3             	mov    %rdx,%rbx
 a7b:	48 09 c3             	or     %rax,%rbx
 a7e:	e8 1d fb ff ff       	call   5a0 <run_batch>
 a83:	e9 5b ff ff ff       	jmp    9e3 <measure_on_cpu+0xb3>
 a88:	c7 44 24 0c 00 00 00 00 	movl   $0x0,0xc(%rsp)
 a90:	49 bd 03 7d c1 25 02 00 00 00 	movabs $0x225c17d03,%r13
 a9a:	49 be ff ff ff ff ff ff ff 7f 	movabs $0x7fffffffffffffff,%r14
 aa4:	8b 44 24 0c          	mov    0xc(%rsp),%eax
 aa8:	83 f8 02             	cmp    $0x2,%eax
 aab:	0f 84 e3 00 00 00    	je     b94 <measure_on_cpu+0x264>
 ab1:	0f 87 8c 00 00 00    	ja     b43 <measure_on_cpu+0x213>
 ab7:	85 c0                	test   %eax,%eax
 ab9:	0f 84 34 01 00 00    	je     bf3 <measure_on_cpu+0x2c3>
 abf:	83 f8 01             	cmp    $0x1,%eax
 ac2:	0f 85 fb 00 00 00    	jne    bc3 <measure_on_cpu+0x293>
 ac8:	48 8d 7c 24 10       	lea    0x10(%rsp),%rdi
 acd:	e8 00 00 00 00       	call   ad2 <measure_on_cpu+0x1a2>	ace: R_X86_64_PLT32	ktime_get_raw_ts64-0x4
 ad2:	e8 00 00 00 00       	call   ad7 <measure_on_cpu+0x1a7>	ad3: R_X86_64_PLT32	ktime_get_raw-0x4
 ad7:	48 8d 7c 24 20       	lea    0x20(%rsp),%rdi
 adc:	48 89 c3             	mov    %rax,%rbx
 adf:	e8 00 00 00 00       	call   ae4 <measure_on_cpu+0x1b4>	ae0: R_X86_64_PLT32	ktime_get_raw_ts64-0x4
 ae4:	48 8b 44 24 10       	mov    0x10(%rsp),%rax
 ae9:	48 8b 4c 24 18       	mov    0x18(%rsp),%rcx
 aee:	4c 89 f2             	mov    %r14,%rdx
 af1:	4c 39 e8             	cmp    %r13,%rax
 af4:	7f 0b                	jg     b01 <measure_on_cpu+0x1d1>
 af6:	48 69 c0 00 ca 9a 3b 	imul   $0x3b9aca00,%rax,%rax
 afd:	48 8d 14 08          	lea    (%rax,%rcx,1),%rdx
 b01:	48 39 d3             	cmp    %rdx,%rbx
 b04:	0f 8c ad 00 00 00    	jl     bb7 <measure_on_cpu+0x287>
 b0a:	48 8b 44 24 20       	mov    0x20(%rsp),%rax
 b0f:	48 8b 54 24 28       	mov    0x28(%rsp),%rdx
 b14:	4c 39 e8             	cmp    %r13,%rax
 b17:	7f 13                	jg     b2c <measure_on_cpu+0x1fc>
 b19:	48 69 c0 00 ca 9a 3b 	imul   $0x3b9aca00,%rax,%rax
 b20:	48 01 d0             	add    %rdx,%rax
 b23:	48 39 c3             	cmp    %rax,%rbx
 b26:	0f 8f 8b 00 00 00    	jg     bb7 <measure_on_cpu+0x287>
 b2c:	83 44 24 0c 01       	addl   $0x1,0xc(%rsp)
 b31:	8b 44 24 0c          	mov    0xc(%rsp),%eax
 b35:	83 f8 05             	cmp    $0x5,%eax
 b38:	0f 85 66 ff ff ff    	jne    aa4 <measure_on_cpu+0x174>
 b3e:	e9 23 fe ff ff       	jmp    966 <measure_on_cpu+0x36>
 b43:	83 7c 24 0c 03       	cmpl   $0x3,0xc(%rsp)
 b48:	75 79                	jne    bc3 <measure_on_cpu+0x293>
 b4a:	bf 01 00 00 00       	mov    $0x1,%edi
 b4f:	e8 00 00 00 00       	call   b54 <measure_on_cpu+0x224>	b50: R_X86_64_PLT32	ktime_get_with_offset-0x4
 b54:	48 89 c7             	mov    %rax,%rdi
 b57:	e8 00 00 00 00       	call   b5c <measure_on_cpu+0x22c>	b58: R_X86_64_PLT32	ns_to_timespec64-0x4
 b5c:	bf 01 00 00 00       	mov    $0x1,%edi
 b61:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
 b66:	48 89 54 24 18       	mov    %rdx,0x18(%rsp)
 b6b:	e8 00 00 00 00       	call   b70 <measure_on_cpu+0x240>	b6c: R_X86_64_PLT32	ktime_get_with_offset-0x4
 b70:	bf 01 00 00 00       	mov    $0x1,%edi
 b75:	48 89 c3             	mov    %rax,%rbx
 b78:	e8 00 00 00 00       	call   b7d <measure_on_cpu+0x24d>	b79: R_X86_64_PLT32	ktime_get_with_offset-0x4
 b7d:	48 89 c7             	mov    %rax,%rdi
 b80:	e8 00 00 00 00       	call   b85 <measure_on_cpu+0x255>	b81: R_X86_64_PLT32	ns_to_timespec64-0x4
 b85:	48 89 44 24 20       	mov    %rax,0x20(%rsp)
 b8a:	48 89 54 24 28       	mov    %rdx,0x28(%rsp)
 b8f:	e9 50 ff ff ff       	jmp    ae4 <measure_on_cpu+0x1b4>
 b94:	48 8d 7c 24 10       	lea    0x10(%rsp),%rdi
 b99:	e8 00 00 00 00       	call   b9e <measure_on_cpu+0x26e>	b9a: R_X86_64_PLT32	ktime_get_real_ts64-0x4
 b9e:	31 ff                	xor    %edi,%edi
 ba0:	e8 00 00 00 00       	call   ba5 <measure_on_cpu+0x275>	ba1: R_X86_64_PLT32	ktime_get_with_offset-0x4
 ba5:	48 8d 7c 24 20       	lea    0x20(%rsp),%rdi
 baa:	48 89 c3             	mov    %rax,%rbx
 bad:	e8 00 00 00 00       	call   bb2 <measure_on_cpu+0x282>	bae: R_X86_64_PLT32	ktime_get_real_ts64-0x4
 bb2:	e9 2d ff ff ff       	jmp    ae4 <measure_on_cpu+0x1b4>
 bb7:	48 c7 c0 de ff ff ff 	mov    $0xffffffffffffffde,%rax
 bbe:	e9 75 fe ff ff       	jmp    a38 <measure_on_cpu+0x108>
 bc3:	bf 02 00 00 00       	mov    $0x2,%edi
 bc8:	e8 00 00 00 00       	call   bcd <measure_on_cpu+0x29d>	bc9: R_X86_64_PLT32	ktime_get_with_offset-0x4
 bcd:	48 89 c7             	mov    %rax,%rdi
 bd0:	e8 00 00 00 00       	call   bd5 <measure_on_cpu+0x2a5>	bd1: R_X86_64_PLT32	ns_to_timespec64-0x4
 bd5:	bf 02 00 00 00       	mov    $0x2,%edi
 bda:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
 bdf:	48 89 54 24 18       	mov    %rdx,0x18(%rsp)
 be4:	e8 00 00 00 00       	call   be9 <measure_on_cpu+0x2b9>	be5: R_X86_64_PLT32	ktime_get_with_offset-0x4
 be9:	bf 02 00 00 00       	mov    $0x2,%edi
 bee:	48 89 c3             	mov    %rax,%rbx
 bf1:	eb 85                	jmp    b78 <measure_on_cpu+0x248>
 bf3:	48 8d 7c 24 10       	lea    0x10(%rsp),%rdi
 bf8:	e8 00 00 00 00       	call   bfd <measure_on_cpu+0x2cd>	bf9: R_X86_64_PLT32	ktime_get_ts64-0x4
 bfd:	e8 00 00 00 00       	call   c02 <measure_on_cpu+0x2d2>	bfe: R_X86_64_PLT32	ktime_get-0x4
 c02:	48 8d 7c 24 20       	lea    0x20(%rsp),%rdi
 c07:	48 89 c3             	mov    %rax,%rbx
 c0a:	e8 00 00 00 00       	call   c0f <measure_on_cpu+0x2df>	c0b: R_X86_64_PLT32	ktime_get_ts64-0x4
 c0f:	e9 d0 fe ff ff       	jmp    ae4 <measure_on_cpu+0x1b4>
 c14:	e8 00 00 00 00       	call   c19 <measure_on_cpu+0x2e9>	c15: R_X86_64_PLT32	__stack_chk_fail-0x4

Disassembly of section .altinstr_replacement:
```

## normal: public IFUNC binding

```text
    19: 0000000000001270    12 IFUNC   GLOBAL DEFAULT   14 vkso_time_gettimeofday
    21: 0000000000001270    12 IFUNC   GLOBAL DEFAULT   14 gettimeofday
    22: 0000000000001280    12 IFUNC   GLOBAL DEFAULT   14 time
    39: 0000000000001270    12 IFUNC   GLOBAL DEFAULT   14 vkso_time_gettimeofday
    48: 0000000000001270    12 IFUNC   GLOBAL DEFAULT   14 gettimeofday
    49: 0000000000001280    12 IFUNC   GLOBAL DEFAULT   14 time
```

## no-retpoline: direct/libvkso_time.so: clock_gettime

```asm
0000000000001200 <clock_gettime>:
    1200:	f3 0f 1e fa          	endbr64 
    1204:	48 83 ec 08          	sub    $0x8,%rsp
    1208:	ff 15 aa 2d 00 00    	call   *0x2daa(%rip)        # 3fb8 <__vkso_clock_gettime@Base>
    120e:	85 c0                	test   %eax,%eax
    1210:	0f 88 0c ff ff ff    	js     1122 <clock_gettime.cold>
    1216:	48 83 c4 08          	add    $0x8,%rsp
    121a:	c3                   	ret    
    121b:	0f 1f 44 00 00       	nopl   0x0(%rax,%rax,1)
```

## no-retpoline: direct/libvkso_time.so: clock_getres

```asm
0000000000001220 <clock_getres>:
    1220:	f3 0f 1e fa          	endbr64 
    1224:	48 83 ec 08          	sub    $0x8,%rsp
    1228:	ff 15 b2 2d 00 00    	call   *0x2db2(%rip)        # 3fe0 <__vkso_clock_getres@Base>
    122e:	85 c0                	test   %eax,%eax
    1230:	0f 88 f1 fe ff ff    	js     1127 <clock_getres.cold>
    1236:	48 83 c4 08          	add    $0x8,%rsp
    123a:	c3                   	ret    
    123b:	0f 1f 44 00 00       	nopl   0x0(%rax,%rax,1)
```

## no-retpoline: direct/libvkso_time.so: resolve_gettimeofday

```asm
0000000000001270 <resolve_gettimeofday>:
    1270:	f3 0f 1e fa          	endbr64 
    1274:	48 8b 05 55 2d 00 00 	mov    0x2d55(%rip),%rax        # 3fd0 <__vkso_gettimeofday@Base>
    127b:	c3                   	ret    
    127c:	0f 1f 40 00          	nopl   0x0(%rax)
```

## no-retpoline: direct/libvkso_time.so: resolve_time

```asm
0000000000001280 <resolve_time>:
    1280:	f3 0f 1e fa          	endbr64 
    1284:	48 8b 05 4d 2d 00 00 	mov    0x2d4d(%rip),%rax        # 3fd8 <__vkso_time@Base>
    128b:	c3                   	ret    
    128c:	0f 1f 40 00          	nopl   0x0(%rax)
```

## no-retpoline: direct/libvkso_time.so: getcpu

```asm
0000000000001290 <getcpu>:
    1290:	f3 0f 1e fa          	endbr64 
    1294:	48 83 ec 08          	sub    $0x8,%rsp
    1298:	31 d2                	xor    %edx,%edx
    129a:	ff 15 58 2d 00 00    	call   *0x2d58(%rip)        # 3ff8 <__vkso_getcpu@Base>
    12a0:	85 c0                	test   %eax,%eax
    12a2:	0f 88 88 fe ff ff    	js     1130 <getcpu.cold>
    12a8:	48 83 c4 08          	add    $0x8,%rsp
    12ac:	c3                   	ret    
    12ad:	0f 1f 00             	nopl   (%rax)
```

## no-retpoline: libkernel.so: __vkso_getcpu

```asm
0000000000001000 <__vkso_getcpu>:
	...
```

## no-retpoline: libkernel.so: vkso_clock_gettime_hres

```asm
0000000000001060 <vkso_clock_gettime_hres>:
	...
```

## no-retpoline: libkernel.so: vkso_clock_gettime_coarse

```asm
0000000000001220 <vkso_clock_gettime_coarse>:
	...
```

## no-retpoline: libkernel.so: __vkso_time

```asm
0000000000001440 <__vkso_time>:
	...
```

## no-retpoline: libkernel.so: __vkso_clock_gettime

```asm
0000000001601000 <__vkso_clock_gettime>:
 1601000:	83 ff 0b             	cmp    $0xb,%edi
 1601003:	77 14                	ja     1601019 <__vkso_clock_gettime+0x19>
 1601005:	b8 93 08 00 00       	mov    $0x893,%eax
 160100a:	0f a3 f8             	bt     %edi,%eax
 160100d:	72 15                	jb     1601024 <__vkso_clock_gettime+0x24>
 160100f:	b8 60 00 00 00       	mov    $0x60,%eax
 1601014:	0f a3 f8             	bt     %edi,%eax
 1601017:	72 1e                	jb     1601037 <__vkso_clock_gettime+0x37>
 1601019:	48 63 ff             	movslq %edi,%rdi
 160101c:	b8 e4 00 00 00       	mov    $0xe4,%eax
 1601021:	0f 05                	syscall 
 1601023:	c3                   	ret    
 1601024:	48 8b 15 d5 0f 00 00 	mov    0xfd5(%rip),%rdx        # 1602000 <__vkso_shared_data+0xf00>
 160102b:	48 8d 0d d6 0f 00 00 	lea    0xfd6(%rip),%rcx        # 1602008 <__vkso_shared_data+0xf08>
 1601032:	e9 29 00 a0 fe       	jmp    1060 <vkso_clock_gettime_hres>
 1601037:	48 8b 15 c2 0f 00 00 	mov    0xfc2(%rip),%rdx        # 1602000 <__vkso_shared_data+0xf00>
 160103e:	e9 dd 01 a0 fe       	jmp    1220 <vkso_clock_gettime_coarse>
 1601043:	66 66 2e 0f 1f 84 00 00 00 00 00 	data16 cs nopw 0x0(%rax,%rax,1)
 160104e:	66 90                	xchg   %ax,%ax
```

## no-retpoline: libkernel.so: __vkso_clock_getres

```asm
0000000001601050 <__vkso_clock_getres>:
 1601050:	83 ff 0b             	cmp    $0xb,%edi
 1601053:	77 14                	ja     1601069 <__vkso_clock_getres+0x19>
 1601055:	b8 93 08 00 00       	mov    $0x893,%eax
 160105a:	0f a3 f8             	bt     %edi,%eax
 160105d:	72 15                	jb     1601074 <__vkso_clock_getres+0x24>
 160105f:	b8 60 00 00 00       	mov    $0x60,%eax
 1601064:	0f a3 f8             	bt     %edi,%eax
 1601067:	72 13                	jb     160107c <__vkso_clock_getres+0x2c>
 1601069:	48 63 ff             	movslq %edi,%rdi
 160106c:	b8 e5 00 00 00       	mov    $0xe5,%eax
 1601071:	0f 05                	syscall 
 1601073:	c3                   	ret    
 1601074:	48 89 f7             	mov    %rsi,%rdi
 1601077:	e9 64 02 a0 fe       	jmp    12e0 <vkso_clock_getres_hres>
 160107c:	48 89 f7             	mov    %rsi,%rdi
 160107f:	e9 7c 02 a0 fe       	jmp    1300 <vkso_clock_getres_coarse>
 1601084:	66 66 2e 0f 1f 84 00 00 00 00 00 	data16 cs nopw 0x0(%rax,%rax,1)
 160108f:	90                   	nop
```

## no-retpoline: libkernel.so: __vkso_gettimeofday

```asm
0000000001601090 <__vkso_gettimeofday>:
 1601090:	48 8d 15 71 0f 00 00 	lea    0xf71(%rip),%rdx        # 1602008 <__vkso_shared_data+0xf08>
 1601097:	e9 84 02 a0 fe       	jmp    1320 <vkso_gettimeofday_core>
 160109c:	b8 60 00 00 00       	mov    $0x60,%eax
 16010a1:	0f 05                	syscall 
 16010a3:	c3                   	ret    
 16010a4:	66 66 2e 0f 1f 84 00 00 00 00 00 	data16 cs nopw 0x0(%rax,%rax,1)
 16010af:	90                   	nop
```

## no-retpoline: raw-kernel-reader.ko: run_batch

```asm
00000000000002f0 <run_batch>:
 2f0:	55                   	push   %rbp
 2f1:	48 89 e5             	mov    %rsp,%rbp
 2f4:	41 56                	push   %r14
 2f6:	41 55                	push   %r13
 2f8:	41 54                	push   %r12
 2fa:	53                   	push   %rbx
 2fb:	89 f3                	mov    %esi,%ebx
 2fd:	48 83 ec 18          	sub    $0x18,%rsp
 301:	65 48 8b 04 25 28 00 00 00 	mov    %gs:0x28,%rax
 30a:	48 89 45 d8          	mov    %rax,-0x28(%rbp)
 30e:	31 c0                	xor    %eax,%eax
 310:	83 ff 01             	cmp    $0x1,%edi
 313:	74 4f                	je     364 <run_batch+0x74>
 315:	83 ff 02             	cmp    $0x2,%edi
 318:	75 76                	jne    390 <run_batch+0xa0>
 31a:	45 31 f6             	xor    %r14d,%r14d
 31d:	45 31 e4             	xor    %r12d,%r12d
 320:	4c 8d 6d c8          	lea    -0x38(%rbp),%r13
 324:	85 f6                	test   %esi,%esi
 326:	74 1c                	je     344 <run_batch+0x54>
 328:	4c 89 ef             	mov    %r13,%rdi
 32b:	41 83 c6 01          	add    $0x1,%r14d
 32f:	e8 00 00 00 00       	call   334 <run_batch+0x44>	330: R_X86_64_PLT32	ktime_get_coarse_ts64-0x4
 334:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 338:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 33c:	49 01 c4             	add    %rax,%r12
 33f:	44 39 f3             	cmp    %r14d,%ebx
 342:	75 e4                	jne    328 <run_batch+0x38>
 344:	48 8b 45 d8          	mov    -0x28(%rbp),%rax
 348:	65 48 2b 04 25 28 00 00 00 	sub    %gs:0x28,%rax
 351:	75 69                	jne    3bc <run_batch+0xcc>
 353:	48 83 c4 18          	add    $0x18,%rsp
 357:	4c 89 e0             	mov    %r12,%rax
 35a:	5b                   	pop    %rbx
 35b:	41 5c                	pop    %r12
 35d:	41 5d                	pop    %r13
 35f:	41 5e                	pop    %r14
 361:	5d                   	pop    %rbp
 362:	c3                   	ret    
 363:	cc                   	int3   
 364:	45 31 f6             	xor    %r14d,%r14d
 367:	45 31 e4             	xor    %r12d,%r12d
 36a:	4c 8d 6d c8          	lea    -0x38(%rbp),%r13
 36e:	85 f6                	test   %esi,%esi
 370:	74 d2                	je     344 <run_batch+0x54>
 372:	4c 89 ef             	mov    %r13,%rdi
 375:	41 83 c6 01          	add    $0x1,%r14d
 379:	e8 00 00 00 00       	call   37e <run_batch+0x8e>	37a: R_X86_64_PLT32	ktime_get_raw_ts64-0x4
 37e:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 382:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 386:	49 01 c4             	add    %rax,%r12
 389:	44 39 f3             	cmp    %r14d,%ebx
 38c:	75 e4                	jne    372 <run_batch+0x82>
 38e:	eb b4                	jmp    344 <run_batch+0x54>
 390:	45 31 f6             	xor    %r14d,%r14d
 393:	45 31 e4             	xor    %r12d,%r12d
 396:	4c 8d 6d c8          	lea    -0x38(%rbp),%r13
 39a:	85 f6                	test   %esi,%esi
 39c:	74 a6                	je     344 <run_batch+0x54>
 39e:	4c 89 ef             	mov    %r13,%rdi
 3a1:	41 83 c6 01          	add    $0x1,%r14d
 3a5:	e8 00 00 00 00       	call   3aa <run_batch+0xba>	3a6: R_X86_64_PLT32	ktime_get_ts64-0x4
 3aa:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 3ae:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 3b2:	49 01 c4             	add    %rax,%r12
 3b5:	44 39 f3             	cmp    %r14d,%ebx
 3b8:	75 e4                	jne    39e <run_batch+0xae>
 3ba:	eb 88                	jmp    344 <run_batch+0x54>
 3bc:	e8 00 00 00 00       	call   3c1 <run_batch+0xd1>	3bd: R_X86_64_PLT32	__stack_chk_fail-0x4
 3c1:	66 66 2e 0f 1f 84 00 00 00 00 00 	data16 cs nopw 0x0(%rax,%rax,1)
 3cc:	0f 1f 40 00          	nopl   0x0(%rax)
```

## no-retpoline: raw-kernel-reader.ko: measure_on_cpu

```asm
00000000000003d0 <measure_on_cpu>:
 3d0:	8b 47 08             	mov    0x8(%rdi),%eax
 3d3:	85 c0                	test   %eax,%eax
 3d5:	0f 84 de 00 00 00    	je     4b9 <measure_on_cpu+0xe9>
 3db:	55                   	push   %rbp
 3dc:	48 89 e5             	mov    %rsp,%rbp
 3df:	41 57                	push   %r15
 3e1:	49 89 ff             	mov    %rdi,%r15
 3e4:	41 56                	push   %r14
 3e6:	41 55                	push   %r13
 3e8:	41 bd 03 00 00 00    	mov    $0x3,%r13d
 3ee:	41 54                	push   %r12
 3f0:	53                   	push   %rbx
 3f1:	48 83 ec 10          	sub    $0x10,%rsp
 3f5:	45 8d 65 fd          	lea    -0x3(%r13),%r12d
 3f9:	4b 8d 04 64          	lea    (%r12,%r12,2),%rax
 3fd:	4d 89 e6             	mov    %r12,%r14
 400:	48 89 45 c8          	mov    %rax,-0x38(%rbp)
 404:	b8 ab aa aa aa       	mov    $0xaaaaaaab,%eax
 409:	41 8b 77 0c          	mov    0xc(%r15),%esi
 40d:	4c 0f af e0          	imul   %rax,%r12
 411:	49 c1 ec 21          	shr    $0x21,%r12
 415:	43 8d 04 64          	lea    (%r12,%r12,2),%eax
 419:	45 89 f4             	mov    %r14d,%r12d
 41c:	41 29 c4             	sub    %eax,%r12d
 41f:	44 89 e0             	mov    %r12d,%eax
 422:	48 03 45 c8          	add    -0x38(%rbp),%rax
 426:	44 89 e7             	mov    %r12d,%edi
 429:	48 8d 14 40          	lea    (%rax,%rax,2),%rdx
 42d:	49 8b 47 10          	mov    0x10(%r15),%rax
 431:	48 8d 1c d0          	lea    (%rax,%rdx,8),%rbx
 435:	e8 b6 fe ff ff       	call   2f0 <run_batch>
 43a:	48 89 43 08          	mov    %rax,0x8(%rbx)
 43e:	0f 31                	rdtsc  
 440:	90                   	nop
 441:	90                   	nop
 442:	90                   	nop
 443:	41 8b 77 04          	mov    0x4(%r15),%esi
 447:	48 c1 e2 20          	shl    $0x20,%rdx
 44b:	44 89 e7             	mov    %r12d,%edi
 44e:	48 09 c2             	or     %rax,%rdx
 451:	48 89 55 d0          	mov    %rdx,-0x30(%rbp)
 455:	e8 96 fe ff ff       	call   2f0 <run_batch>
 45a:	48 31 43 08          	xor    %rax,0x8(%rbx)
 45e:	0f 31                	rdtsc  
 460:	90                   	nop
 461:	90                   	nop
 462:	90                   	nop
 463:	48 c1 e2 20          	shl    $0x20,%rdx
 467:	41 83 c6 01          	add    $0x1,%r14d
 46b:	48 09 c2             	or     %rax,%rdx
 46e:	48 2b 55 d0          	sub    -0x30(%rbp),%rdx
 472:	48 89 13             	mov    %rdx,(%rbx)
 475:	65 8b 05 00 00 00 00 	mov    %gs:0x0(%rip),%eax        # 47c <measure_on_cpu+0xac>	478: R_X86_64_PC32	cpu_number-0x4
 47c:	89 43 10             	mov    %eax,0x10(%rbx)
 47f:	45 39 f5             	cmp    %r14d,%r13d
 482:	74 08                	je     48c <measure_on_cpu+0xbc>
 484:	45 89 f4             	mov    %r14d,%r12d
 487:	e9 78 ff ff ff       	jmp    404 <measure_on_cpu+0x34>
 48c:	e8 00 00 00 00       	call   491 <measure_on_cpu+0xc1>	48d: R_X86_64_PLT32	__cond_resched-0x4
 491:	41 8d 45 01          	lea    0x1(%r13),%eax
 495:	41 83 ed 02          	sub    $0x2,%r13d
 499:	45 39 6f 08          	cmp    %r13d,0x8(%r15)
 49d:	76 08                	jbe    4a7 <measure_on_cpu+0xd7>
 49f:	41 89 c5             	mov    %eax,%r13d
 4a2:	e9 4e ff ff ff       	jmp    3f5 <measure_on_cpu+0x25>
 4a7:	48 83 c4 10          	add    $0x10,%rsp
 4ab:	31 c0                	xor    %eax,%eax
 4ad:	5b                   	pop    %rbx
 4ae:	41 5c                	pop    %r12
 4b0:	41 5d                	pop    %r13
 4b2:	41 5e                	pop    %r14
 4b4:	41 5f                	pop    %r15
 4b6:	5d                   	pop    %rbp
 4b7:	c3                   	ret    
 4b8:	cc                   	int3   
 4b9:	31 c0                	xor    %eax,%eax
 4bb:	c3                   	ret    
 4bc:	cc                   	int3   
 4bd:	0f 1f 00             	nopl   (%rax)
```

## no-retpoline: vkso-kernel-reader.ko: run_batch

```asm
0000000000000560 <run_batch>:
 560:	55                   	push   %rbp
 561:	48 89 e5             	mov    %rsp,%rbp
 564:	41 56                	push   %r14
 566:	41 55                	push   %r13
 568:	41 89 f5             	mov    %esi,%r13d
 56b:	41 54                	push   %r12
 56d:	53                   	push   %rbx
 56e:	48 83 ec 18          	sub    $0x18,%rsp
 572:	65 48 8b 04 25 28 00 00 00 	mov    %gs:0x28,%rax
 57b:	48 89 45 d8          	mov    %rax,-0x28(%rbp)
 57f:	31 c0                	xor    %eax,%eax
 581:	83 ff 01             	cmp    $0x1,%edi
 584:	74 32                	je     5b8 <run_batch+0x58>
 586:	89 fb                	mov    %edi,%ebx
 588:	83 ff 02             	cmp    $0x2,%edi
 58b:	74 7a                	je     607 <run_batch+0xa7>
 58d:	45 31 e4             	xor    %r12d,%r12d
 590:	85 ff                	test   %edi,%edi
 592:	74 4e                	je     5e2 <run_batch+0x82>
 594:	48 8b 45 d8          	mov    -0x28(%rbp),%rax
 598:	65 48 2b 04 25 28 00 00 00 	sub    %gs:0x28,%rax
 5a1:	0f 85 8d 00 00 00    	jne    634 <run_batch+0xd4>
 5a7:	48 83 c4 18          	add    $0x18,%rsp
 5ab:	4c 89 e0             	mov    %r12,%rax
 5ae:	5b                   	pop    %rbx
 5af:	41 5c                	pop    %r12
 5b1:	41 5d                	pop    %r13
 5b3:	41 5e                	pop    %r14
 5b5:	5d                   	pop    %rbp
 5b6:	c3                   	ret    
 5b7:	cc                   	int3   
 5b8:	31 db                	xor    %ebx,%ebx
 5ba:	45 31 e4             	xor    %r12d,%r12d
 5bd:	4c 8d 75 c8          	lea    -0x38(%rbp),%r14
 5c1:	85 f6                	test   %esi,%esi
 5c3:	74 cf                	je     594 <run_batch+0x34>
 5c5:	4c 89 f7             	mov    %r14,%rdi
 5c8:	83 c3 01             	add    $0x1,%ebx
 5cb:	e8 00 00 00 00       	call   5d0 <run_batch+0x70>	5cc: R_X86_64_PLT32	ktime_get_raw_ts64-0x4
 5d0:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 5d4:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 5d8:	49 01 c4             	add    %rax,%r12
 5db:	41 39 dd             	cmp    %ebx,%r13d
 5de:	75 e5                	jne    5c5 <run_batch+0x65>
 5e0:	eb b2                	jmp    594 <run_batch+0x34>
 5e2:	85 f6                	test   %esi,%esi
 5e4:	74 ae                	je     594 <run_batch+0x34>
 5e6:	4c 8d 75 c8          	lea    -0x38(%rbp),%r14
 5ea:	4c 89 f7             	mov    %r14,%rdi
 5ed:	83 c3 01             	add    $0x1,%ebx
 5f0:	e8 00 00 00 00       	call   5f5 <run_batch+0x95>	5f1: R_X86_64_PLT32	ktime_get_ts64-0x4
 5f5:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 5f9:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 5fd:	49 01 c4             	add    %rax,%r12
 600:	41 39 dd             	cmp    %ebx,%r13d
 603:	75 e5                	jne    5ea <run_batch+0x8a>
 605:	eb 8d                	jmp    594 <run_batch+0x34>
 607:	31 db                	xor    %ebx,%ebx
 609:	45 31 e4             	xor    %r12d,%r12d
 60c:	4c 8d 75 c8          	lea    -0x38(%rbp),%r14
 610:	85 f6                	test   %esi,%esi
 612:	74 80                	je     594 <run_batch+0x34>
 614:	4c 89 f7             	mov    %r14,%rdi
 617:	83 c3 01             	add    $0x1,%ebx
 61a:	e8 00 00 00 00       	call   61f <run_batch+0xbf>	61b: R_X86_64_PLT32	ktime_get_coarse_ts64-0x4
 61f:	48 8b 45 c8          	mov    -0x38(%rbp),%rax
 623:	48 33 45 d0          	xor    -0x30(%rbp),%rax
 627:	49 01 c4             	add    %rax,%r12
 62a:	41 39 dd             	cmp    %ebx,%r13d
 62d:	75 e5                	jne    614 <run_batch+0xb4>
 62f:	e9 60 ff ff ff       	jmp    594 <run_batch+0x34>
 634:	e8 00 00 00 00       	call   639 <run_batch+0xd9>	635: R_X86_64_PLT32	__stack_chk_fail-0x4
 639:	0f 1f 80 00 00 00 00 	nopl   0x0(%rax)
```

## no-retpoline: vkso-kernel-reader.ko: measure_on_cpu

```asm
00000000000008f0 <measure_on_cpu>:
 8f0:	55                   	push   %rbp
 8f1:	48 89 e5             	mov    %rsp,%rbp
 8f4:	41 57                	push   %r15
 8f6:	49 89 ff             	mov    %rdi,%r15
 8f9:	41 56                	push   %r14
 8fb:	41 55                	push   %r13
 8fd:	41 54                	push   %r12
 8ff:	53                   	push   %rbx
 900:	48 83 ec 38          	sub    $0x38,%rsp
 904:	65 48 8b 04 25 28 00 00 00 	mov    %gs:0x28,%rax
 90d:	48 89 44 24 30       	mov    %rax,0x30(%rsp)
 912:	31 c0                	xor    %eax,%eax
 914:	80 7f 18 00          	cmpb   $0x0,0x18(%rdi)
 918:	0f 85 27 01 00 00    	jne    a45 <measure_on_cpu+0x155>
 91e:	c7 44 24 0c 03 00 00 00 	movl   $0x3,0xc(%rsp)
 926:	8b 44 24 0c          	mov    0xc(%rsp),%eax
 92a:	c7 44 24 08 00 00 00 00 	movl   $0x0,0x8(%rsp)
 932:	c7 04 24 00 00 00 00 	movl   $0x0,(%rsp)
 939:	89 44 24 04          	mov    %eax,0x4(%rsp)
 93d:	41 8b 47 08          	mov    0x8(%r15),%eax
 941:	85 c0                	test   %eax,%eax
 943:	0f 84 ad 00 00 00    	je     9f6 <measure_on_cpu+0x106>
 949:	44 8b 24 24          	mov    (%rsp),%r12d
 94d:	31 d2                	xor    %edx,%edx
 94f:	44 89 e0             	mov    %r12d,%eax
 952:	41 8b 77 0c          	mov    0xc(%r15),%esi
 956:	f7 74 24 0c          	divl   0xc(%rsp)
 95a:	8b 44 24 08          	mov    0x8(%rsp),%eax
 95e:	01 d0                	add    %edx,%eax
 960:	41 89 d5             	mov    %edx,%r13d
 963:	41 80 7f 18 00       	cmpb   $0x0,0x18(%r15)
 968:	89 c0                	mov    %eax,%eax
 96a:	44 89 ef             	mov    %r13d,%edi
 96d:	48 8d 14 40          	lea    (%rax,%rax,2),%rdx
 971:	49 8b 47 10          	mov    0x10(%r15),%rax
 975:	4c 8d 34 d0          	lea    (%rax,%rdx,8),%r14
 979:	0f 84 9d 00 00 00    	je     a1c <measure_on_cpu+0x12c>
 97f:	e8 8c f9 ff ff       	call   310 <run_scalar_batch>
 984:	49 89 46 08          	mov    %rax,0x8(%r14)
 988:	0f 31                	rdtsc  
 98a:	90                   	nop
 98b:	90                   	nop
 98c:	90                   	nop
 98d:	48 c1 e2 20          	shl    $0x20,%rdx
 991:	41 8b 77 04          	mov    0x4(%r15),%esi
 995:	44 89 ef             	mov    %r13d,%edi
 998:	48 89 d3             	mov    %rdx,%rbx
 99b:	48 09 c3             	or     %rax,%rbx
 99e:	e8 6d f9 ff ff       	call   310 <run_scalar_batch>
 9a3:	49 31 46 08          	xor    %rax,0x8(%r14)
 9a7:	0f 31                	rdtsc  
 9a9:	90                   	nop
 9aa:	90                   	nop
 9ab:	90                   	nop
 9ac:	48 c1 e2 20          	shl    $0x20,%rdx
 9b0:	48 09 d0             	or     %rdx,%rax
 9b3:	48 29 d8             	sub    %rbx,%rax
 9b6:	41 83 c4 01          	add    $0x1,%r12d
 9ba:	49 89 06             	mov    %rax,(%r14)
 9bd:	65 8b 05 00 00 00 00 	mov    %gs:0x0(%rip),%eax        # 9c4 <measure_on_cpu+0xd4>	9c0: R_X86_64_PC32	cpu_number-0x4
 9c4:	41 89 46 10          	mov    %eax,0x10(%r14)
 9c8:	44 39 64 24 04       	cmp    %r12d,0x4(%rsp)
 9cd:	0f 85 7a ff ff ff    	jne    94d <measure_on_cpu+0x5d>
 9d3:	e8 00 00 00 00       	call   9d8 <measure_on_cpu+0xe8>	9d4: R_X86_64_PLT32	__cond_resched-0x4
 9d8:	83 04 24 01          	addl   $0x1,(%rsp)
 9dc:	8b 4c 24 0c          	mov    0xc(%rsp),%ecx
 9e0:	83 44 24 04 01       	addl   $0x1,0x4(%rsp)
 9e5:	8b 04 24             	mov    (%rsp),%eax
 9e8:	01 4c 24 08          	add    %ecx,0x8(%rsp)
 9ec:	41 39 47 08          	cmp    %eax,0x8(%r15)
 9f0:	0f 87 53 ff ff ff    	ja     949 <measure_on_cpu+0x59>
 9f6:	31 c0                	xor    %eax,%eax
 9f8:	48 8b 54 24 30       	mov    0x30(%rsp),%rdx
 9fd:	65 48 2b 14 25 28 00 00 00 	sub    %gs:0x28,%rdx
 a06:	0f 85 c5 01 00 00    	jne    bd1 <measure_on_cpu+0x2e1>
 a0c:	48 83 c4 38          	add    $0x38,%rsp
 a10:	5b                   	pop    %rbx
 a11:	41 5c                	pop    %r12
 a13:	41 5d                	pop    %r13
 a15:	41 5e                	pop    %r14
 a17:	41 5f                	pop    %r15
 a19:	5d                   	pop    %rbp
 a1a:	c3                   	ret    
 a1b:	cc                   	int3   
 a1c:	e8 3f fb ff ff       	call   560 <run_batch>
 a21:	49 89 46 08          	mov    %rax,0x8(%r14)
 a25:	0f 31                	rdtsc  
 a27:	90                   	nop
 a28:	90                   	nop
 a29:	90                   	nop
 a2a:	48 c1 e2 20          	shl    $0x20,%rdx
 a2e:	41 8b 77 04          	mov    0x4(%r15),%esi
 a32:	44 89 ef             	mov    %r13d,%edi
 a35:	48 89 d3             	mov    %rdx,%rbx
 a38:	48 09 c3             	or     %rax,%rbx
 a3b:	e8 20 fb ff ff       	call   560 <run_batch>
 a40:	e9 5e ff ff ff       	jmp    9a3 <measure_on_cpu+0xb3>
 a45:	c7 44 24 0c 00 00 00 00 	movl   $0x0,0xc(%rsp)
 a4d:	49 bd 03 7d c1 25 02 00 00 00 	movabs $0x225c17d03,%r13
 a57:	49 be ff ff ff ff ff ff ff 7f 	movabs $0x7fffffffffffffff,%r14
 a61:	8b 44 24 0c          	mov    0xc(%rsp),%eax
 a65:	83 f8 02             	cmp    $0x2,%eax
 a68:	0f 84 e3 00 00 00    	je     b51 <measure_on_cpu+0x261>
 a6e:	0f 87 8c 00 00 00    	ja     b00 <measure_on_cpu+0x210>
 a74:	85 c0                	test   %eax,%eax
 a76:	0f 84 34 01 00 00    	je     bb0 <measure_on_cpu+0x2c0>
 a7c:	83 f8 01             	cmp    $0x1,%eax
 a7f:	0f 85 fb 00 00 00    	jne    b80 <measure_on_cpu+0x290>
 a85:	48 8d 7c 24 10       	lea    0x10(%rsp),%rdi
 a8a:	e8 00 00 00 00       	call   a8f <measure_on_cpu+0x19f>	a8b: R_X86_64_PLT32	ktime_get_raw_ts64-0x4
 a8f:	e8 00 00 00 00       	call   a94 <measure_on_cpu+0x1a4>	a90: R_X86_64_PLT32	ktime_get_raw-0x4
 a94:	48 8d 7c 24 20       	lea    0x20(%rsp),%rdi
 a99:	48 89 c3             	mov    %rax,%rbx
 a9c:	e8 00 00 00 00       	call   aa1 <measure_on_cpu+0x1b1>	a9d: R_X86_64_PLT32	ktime_get_raw_ts64-0x4
 aa1:	48 8b 44 24 10       	mov    0x10(%rsp),%rax
 aa6:	48 8b 4c 24 18       	mov    0x18(%rsp),%rcx
 aab:	4c 89 f2             	mov    %r14,%rdx
 aae:	4c 39 e8             	cmp    %r13,%rax
 ab1:	7f 0b                	jg     abe <measure_on_cpu+0x1ce>
 ab3:	48 69 c0 00 ca 9a 3b 	imul   $0x3b9aca00,%rax,%rax
 aba:	48 8d 14 08          	lea    (%rax,%rcx,1),%rdx
 abe:	48 39 d3             	cmp    %rdx,%rbx
 ac1:	0f 8c ad 00 00 00    	jl     b74 <measure_on_cpu+0x284>
 ac7:	48 8b 44 24 20       	mov    0x20(%rsp),%rax
 acc:	48 8b 54 24 28       	mov    0x28(%rsp),%rdx
 ad1:	4c 39 e8             	cmp    %r13,%rax
 ad4:	7f 13                	jg     ae9 <measure_on_cpu+0x1f9>
 ad6:	48 69 c0 00 ca 9a 3b 	imul   $0x3b9aca00,%rax,%rax
 add:	48 01 d0             	add    %rdx,%rax
 ae0:	48 39 c3             	cmp    %rax,%rbx
 ae3:	0f 8f 8b 00 00 00    	jg     b74 <measure_on_cpu+0x284>
 ae9:	83 44 24 0c 01       	addl   $0x1,0xc(%rsp)
 aee:	8b 44 24 0c          	mov    0xc(%rsp),%eax
 af2:	83 f8 05             	cmp    $0x5,%eax
 af5:	0f 85 66 ff ff ff    	jne    a61 <measure_on_cpu+0x171>
 afb:	e9 26 fe ff ff       	jmp    926 <measure_on_cpu+0x36>
 b00:	83 7c 24 0c 03       	cmpl   $0x3,0xc(%rsp)
 b05:	75 79                	jne    b80 <measure_on_cpu+0x290>
 b07:	bf 01 00 00 00       	mov    $0x1,%edi
 b0c:	e8 00 00 00 00       	call   b11 <measure_on_cpu+0x221>	b0d: R_X86_64_PLT32	ktime_get_with_offset-0x4
 b11:	48 89 c7             	mov    %rax,%rdi
 b14:	e8 00 00 00 00       	call   b19 <measure_on_cpu+0x229>	b15: R_X86_64_PLT32	ns_to_timespec64-0x4
 b19:	bf 01 00 00 00       	mov    $0x1,%edi
 b1e:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
 b23:	48 89 54 24 18       	mov    %rdx,0x18(%rsp)
 b28:	e8 00 00 00 00       	call   b2d <measure_on_cpu+0x23d>	b29: R_X86_64_PLT32	ktime_get_with_offset-0x4
 b2d:	bf 01 00 00 00       	mov    $0x1,%edi
 b32:	48 89 c3             	mov    %rax,%rbx
 b35:	e8 00 00 00 00       	call   b3a <measure_on_cpu+0x24a>	b36: R_X86_64_PLT32	ktime_get_with_offset-0x4
 b3a:	48 89 c7             	mov    %rax,%rdi
 b3d:	e8 00 00 00 00       	call   b42 <measure_on_cpu+0x252>	b3e: R_X86_64_PLT32	ns_to_timespec64-0x4
 b42:	48 89 44 24 20       	mov    %rax,0x20(%rsp)
 b47:	48 89 54 24 28       	mov    %rdx,0x28(%rsp)
 b4c:	e9 50 ff ff ff       	jmp    aa1 <measure_on_cpu+0x1b1>
 b51:	48 8d 7c 24 10       	lea    0x10(%rsp),%rdi
 b56:	e8 00 00 00 00       	call   b5b <measure_on_cpu+0x26b>	b57: R_X86_64_PLT32	ktime_get_real_ts64-0x4
 b5b:	31 ff                	xor    %edi,%edi
 b5d:	e8 00 00 00 00       	call   b62 <measure_on_cpu+0x272>	b5e: R_X86_64_PLT32	ktime_get_with_offset-0x4
 b62:	48 8d 7c 24 20       	lea    0x20(%rsp),%rdi
 b67:	48 89 c3             	mov    %rax,%rbx
 b6a:	e8 00 00 00 00       	call   b6f <measure_on_cpu+0x27f>	b6b: R_X86_64_PLT32	ktime_get_real_ts64-0x4
 b6f:	e9 2d ff ff ff       	jmp    aa1 <measure_on_cpu+0x1b1>
 b74:	48 c7 c0 de ff ff ff 	mov    $0xffffffffffffffde,%rax
 b7b:	e9 78 fe ff ff       	jmp    9f8 <measure_on_cpu+0x108>
 b80:	bf 02 00 00 00       	mov    $0x2,%edi
 b85:	e8 00 00 00 00       	call   b8a <measure_on_cpu+0x29a>	b86: R_X86_64_PLT32	ktime_get_with_offset-0x4
 b8a:	48 89 c7             	mov    %rax,%rdi
 b8d:	e8 00 00 00 00       	call   b92 <measure_on_cpu+0x2a2>	b8e: R_X86_64_PLT32	ns_to_timespec64-0x4
 b92:	bf 02 00 00 00       	mov    $0x2,%edi
 b97:	48 89 44 24 10       	mov    %rax,0x10(%rsp)
 b9c:	48 89 54 24 18       	mov    %rdx,0x18(%rsp)
 ba1:	e8 00 00 00 00       	call   ba6 <measure_on_cpu+0x2b6>	ba2: R_X86_64_PLT32	ktime_get_with_offset-0x4
 ba6:	bf 02 00 00 00       	mov    $0x2,%edi
 bab:	48 89 c3             	mov    %rax,%rbx
 bae:	eb 85                	jmp    b35 <measure_on_cpu+0x245>
 bb0:	48 8d 7c 24 10       	lea    0x10(%rsp),%rdi
 bb5:	e8 00 00 00 00       	call   bba <measure_on_cpu+0x2ca>	bb6: R_X86_64_PLT32	ktime_get_ts64-0x4
 bba:	e8 00 00 00 00       	call   bbf <measure_on_cpu+0x2cf>	bbb: R_X86_64_PLT32	ktime_get-0x4
 bbf:	48 8d 7c 24 20       	lea    0x20(%rsp),%rdi
 bc4:	48 89 c3             	mov    %rax,%rbx
 bc7:	e8 00 00 00 00       	call   bcc <measure_on_cpu+0x2dc>	bc8: R_X86_64_PLT32	ktime_get_ts64-0x4
 bcc:	e9 d0 fe ff ff       	jmp    aa1 <measure_on_cpu+0x1b1>
 bd1:	e8 00 00 00 00       	call   bd6 <measure_on_cpu+0x2e6>	bd2: R_X86_64_PLT32	__stack_chk_fail-0x4

Disassembly of section .altinstr_replacement:
```

## no-retpoline: public IFUNC binding

```text
    19: 0000000000001270    12 IFUNC   GLOBAL DEFAULT   14 vkso_time_gettimeofday
    21: 0000000000001270    12 IFUNC   GLOBAL DEFAULT   14 gettimeofday
    22: 0000000000001280    12 IFUNC   GLOBAL DEFAULT   14 time
    39: 0000000000001270    12 IFUNC   GLOBAL DEFAULT   14 vkso_time_gettimeofday
    48: 0000000000001270    12 IFUNC   GLOBAL DEFAULT   14 gettimeofday
    49: 0000000000001280    12 IFUNC   GLOBAL DEFAULT   14 time
```
