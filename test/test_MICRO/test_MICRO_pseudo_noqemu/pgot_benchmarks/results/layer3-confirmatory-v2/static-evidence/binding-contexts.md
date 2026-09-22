# Binding instruction contexts

Static sites, not execution counts. Full disassembly is adjacent.

## 01_sha256_transform/no_retpoline/data_pgot: sha256_transform_data_pgot, 3ae, pgot_k_table

```asm
 3a7:	mov    %rax,-0x30(%rbp)
 3ab:	mov    0x0(%rip),%rax        # 3b2 <sha256_transform_data_pgot+0x32>
			3ae: R_X86_64_PC32	pgot_k_table-0x4
 3b2:	mov    %rax,-0x138(%rbp)
 3b9:	xor    %ebx,%ebx
 3bb:	movslq %ebx,%rsi
 3be:	cmp    $0x3f,%rsi
 3c2:	ja     6d2 <sha256_transform_data_pgot+0x352>
 3c8:	mov    (%r12,%rbx,4),%eax
 3cc:	bswap  %eax
 3ce:	mov    %eax,-0x130(%rbp,%rbx,4)
 3d5:	add    $0x1,%rbx
 3d9:	cmp    $0x10,%rbx
 3dd:	jne    3bb <sha256_transform_data_pgot+0x3b>
 3df:	lea    -0x130(%rbp),%r13
 3e6:	lea    -0x2(%rbx),%esi
 3e9:	movslq %esi,%rsi
 3ec:	cmp    $0x3f,%rsi
 3f0:	ja     6c1 <sha256_transform_data_pgot+0x341>
```

## 01_sha256_transform/retpoline/data_pgot: sha256_transform_data_pgot, 3ae, pgot_k_table

```asm
 3a7:	mov    %rax,-0x30(%rbp)
 3ab:	mov    0x0(%rip),%rax        # 3b2 <sha256_transform_data_pgot+0x32>
			3ae: R_X86_64_PC32	pgot_k_table-0x4
 3b2:	mov    %rax,-0x138(%rbp)
 3b9:	xor    %ebx,%ebx
 3bb:	movslq %ebx,%rsi
 3be:	cmp    $0x3f,%rsi
 3c2:	ja     6d2 <sha256_transform_data_pgot+0x352>
 3c8:	mov    (%r12,%rbx,4),%eax
 3cc:	bswap  %eax
 3ce:	mov    %eax,-0x130(%rbp,%rbx,4)
 3d5:	add    $0x1,%rbx
 3d9:	cmp    $0x10,%rbx
 3dd:	jne    3bb <sha256_transform_data_pgot+0x3b>
 3df:	lea    -0x130(%rbp),%r13
 3e6:	lea    -0x2(%rbx),%esi
 3e9:	movslq %esi,%rsi
 3ec:	cmp    $0x3f,%rsi
 3f0:	ja     6c1 <sha256_transform_data_pgot+0x341>
```

## 02_bch_encode/no_retpoline/data_pgot: swap_bits_data_pgot, 166, pgot_swap_bits_table

```asm
     161:	je     171 <swap_bits_data_pgot+0x31>
     163:	mov    0x0(%rip),%rax        # 16a <swap_bits_data_pgot+0x2a>
			166: R_X86_64_PC32	pgot_swap_bits_table-0x4
     16a:	movzbl %bl,%ebx
     16d:	movzbl (%rax,%rbx,1),%eax
     171:	pop    %rbx
     172:	pop    %r12
     174:	pop    %rbp
     175:	ret    
     176:	int3   
     177:	nopw   0x0(%rax,%rax,1)

```

## 02_bch_encode/no_retpoline/func_pgot: load_ecc8_func_pgot, 489, pgot_memcpy_table

```asm
     481:	imul   0x8(%r15),%eax
     486:	mov    0x0(%rip),%rcx        # 48d <load_ecc8_func_pgot+0xcd>
			489: R_X86_64_PC32	pgot_memcpy_table-0x4
     48d:	mov    -0x44(%rbp),%r14d
     491:	lea    0x7(%rax),%edx
     494:	mov    -0x40(%rbp),%rsi
     498:	lea    -0x34(%rbp),%rdi
     49c:	shr    $0x3,%edx
     49f:	lea    0x0(,%r14,4),%eax
     4a7:	sub    %eax,%edx
     4a9:	call   *%rcx
     4ab:	movzbl -0x34(%rbp),%esi
     4af:	mov    %r15,%rdi
     4b2:	call   280 <swap_bits_func_pgot>
     4b7:	movzbl -0x33(%rbp),%esi
     4bb:	mov    %r15,%rdi
     4be:	mov    %eax,%r12d
     4c1:	call   280 <swap_bits_func_pgot>
     4c6:	movzbl -0x32(%rbp),%esi
```

## 02_bch_encode/no_retpoline/func_pgot: store_ecc8_func_pgot, 63f, pgot_memcpy_table

```asm
     63a:	sub    %eax,%edx
     63c:	mov    0x0(%rip),%rax        # 643 <store_ecc8_func_pgot+0x103>
			63f: R_X86_64_PC32	pgot_memcpy_table-0x4
     643:	lea    -0x34(%rbp),%rsi
     647:	mov    %r12,%rdi
     64a:	call   *%rax
     64c:	mov    -0x30(%rbp),%rax
     650:	sub    %gs:0x28,%rax
     659:	jne    66b <store_ecc8_func_pgot+0x12b>
     65b:	add    $0x18,%rsp
     65f:	pop    %rbx
     660:	pop    %r12
     662:	pop    %r13
     664:	pop    %r14
     666:	pop    %r15
     668:	pop    %rbp
     669:	ret    
     66a:	int3   
     66b:	call   670 <store_ecc8_func_pgot+0x130>
```

## 02_bch_encode/no_retpoline/all_pgot: swap_bits_all_pgot, 6a6, pgot_swap_bits_table

```asm
     6a1:	je     6b1 <swap_bits_all_pgot+0x31>
     6a3:	mov    0x0(%rip),%rax        # 6aa <swap_bits_all_pgot+0x2a>
			6a6: R_X86_64_PC32	pgot_swap_bits_table-0x4
     6aa:	movzbl %bl,%ebx
     6ad:	movzbl (%rax,%rbx,1),%eax
     6b1:	pop    %rbx
     6b2:	pop    %r12
     6b4:	pop    %rbp
     6b5:	ret    
     6b6:	int3   
     6b7:	nopw   0x0(%rax,%rax,1)

```

## 02_bch_encode/no_retpoline/all_pgot: load_ecc8_all_pgot, 889, pgot_memcpy_table

```asm
     881:	imul   0x8(%r15),%eax
     886:	mov    0x0(%rip),%rcx        # 88d <load_ecc8_all_pgot+0xcd>
			889: R_X86_64_PC32	pgot_memcpy_table-0x4
     88d:	mov    -0x44(%rbp),%r14d
     891:	lea    0x7(%rax),%edx
     894:	mov    -0x40(%rbp),%rsi
     898:	lea    -0x34(%rbp),%rdi
     89c:	shr    $0x3,%edx
     89f:	lea    0x0(,%r14,4),%eax
     8a7:	sub    %eax,%edx
     8a9:	call   *%rcx
     8ab:	movzbl -0x34(%rbp),%esi
     8af:	mov    %r15,%rdi
     8b2:	call   680 <swap_bits_all_pgot>
     8b7:	movzbl -0x33(%rbp),%esi
     8bb:	mov    %r15,%rdi
     8be:	mov    %eax,%r12d
     8c1:	call   680 <swap_bits_all_pgot>
     8c6:	movzbl -0x32(%rbp),%esi
```

## 02_bch_encode/no_retpoline/all_pgot: store_ecc8_all_pgot, a3f, pgot_memcpy_table

```asm
     a3a:	sub    %eax,%edx
     a3c:	mov    0x0(%rip),%rax        # a43 <store_ecc8_all_pgot+0x103>
			a3f: R_X86_64_PC32	pgot_memcpy_table-0x4
     a43:	lea    -0x34(%rbp),%rsi
     a47:	mov    %r12,%rdi
     a4a:	call   *%rax
     a4c:	mov    -0x30(%rbp),%rax
     a50:	sub    %gs:0x28,%rax
     a59:	jne    a6b <store_ecc8_all_pgot+0x12b>
     a5b:	add    $0x18,%rsp
     a5f:	pop    %rbx
     a60:	pop    %r12
     a62:	pop    %r13
     a64:	pop    %r14
     a66:	pop    %r15
     a68:	pop    %rbp
     a69:	ret    
     a6a:	int3   
     a6b:	call   a70 <store_ecc8_all_pgot+0x130>
```

## 02_bch_encode/no_retpoline/all_pgot: bch_encode_all_pgot, b92, pgot_memcpy_table

```asm
     b8b:	mov    0x30(%rax),%rsi
     b8f:	mov    0x0(%rip),%rax        # b96 <bch_encode_all_pgot+0x116>
			b92: R_X86_64_PC32	pgot_memcpy_table-0x4
     b96:	mov    -0x110(%rbp),%rdx
     b9d:	lea    -0xa8(%rbp),%rdi
     ba4:	call   *%rax
     ba6:	test   %ebx,%ebx
     ba8:	mov    -0xb0(%rbp),%r8d
     baf:	je     cfb <bch_encode_all_pgot+0x27b>
     bb5:	mov    -0xbc(%rbp),%eax
     bbb:	mov    -0x108(%rbp),%rcx
     bc2:	lea    -0x2(%r8),%edx
     bc6:	mov    %rax,-0xb0(%rbp)
     bcd:	lea    0x0(,%rax,4),%r9
     bd5:	lea    (%rcx,%rbx,4),%rax
     bd9:	mov    %rax,-0xe8(%rbp)
     be0:	mov    -0xb8(%rbp),%rax
     be7:	mov    (%rcx),%r13d
     bea:	add    $0x4,%rcx
```

## 02_bch_encode/no_retpoline/all_pgot: bch_encode_all_pgot, d09, pgot_memcpy_table

```asm
     d02:	mov    0x30(%rax),%rdi
     d06:	mov    0x0(%rip),%rax        # d0d <bch_encode_all_pgot+0x28d>
			d09: R_X86_64_PC32	pgot_memcpy_table-0x4
     d0d:	mov    -0x110(%rbp),%rdx
     d14:	lea    -0xa8(%rbp),%rsi
     d1b:	call   *%rax
     d1d:	mov    -0x120(%rbp),%edi
     d23:	test   %edi,%edi
     d25:	jne    e8d <bch_encode_all_pgot+0x40d>
     d2b:	mov    -0x118(%rbp),%rsi
     d32:	test   %rsi,%rsi
     d35:	je     d47 <bch_encode_all_pgot+0x2c7>
     d37:	mov    -0xb8(%rbp),%rdi
     d3e:	mov    0x30(%rdi),%rdx
     d42:	call   940 <store_ecc8_all_pgot>
     d47:	mov    -0x30(%rbp),%rax
     d4b:	sub    %gs:0x28,%rax
     d54:	jne    ff8 <bch_encode_all_pgot+0x578>
     d5a:	add    $0x110,%rsp
```

## 02_bch_encode/no_retpoline/all_pgot: bch_encode_all_pgot, d77, memset

```asm
     d74:	xor    %esi,%esi
     d76:	call   d7b <bch_encode_all_pgot+0x2fb>
			d77: R_X86_64_PLT32	memset-0x4
     d7b:	mov    -0x108(%rbp),%rax
     d82:	mov    -0xb0(%rbp),%r8d
     d89:	and    $0x3,%eax
     d8c:	je     b69 <bch_encode_all_pgot+0xe9>
     d92:	mov    $0x4,%ebx
     d97:	mov    -0xb8(%rbp),%rdi
     d9e:	mov    -0x108(%rbp),%r15
     da5:	mov    %r8d,-0xb0(%rbp)
     dac:	sub    %rax,%rbx
     daf:	mov    -0x11c(%rbp),%eax
     db5:	mov    0x30(%rdi),%rcx
     db9:	mov    %r15,%rsi
     dbc:	cmp    %rax,%rbx
     dbf:	mov    %rax,%r14
     dc2:	cmova  %rax,%rbx
     dc6:	mov    %ebx,%edx
```

## 02_bch_encode/no_retpoline/func_pgot: bch_encode_func_pgot, 1212, pgot_memcpy_table

```asm
    120b:	mov    0x30(%rax),%rsi
    120f:	mov    0x0(%rip),%rax        # 1216 <bch_encode_func_pgot+0x116>
			1212: R_X86_64_PC32	pgot_memcpy_table-0x4
    1216:	mov    -0x110(%rbp),%rdx
    121d:	lea    -0xa8(%rbp),%rdi
    1224:	call   *%rax
    1226:	test   %ebx,%ebx
    1228:	mov    -0xb0(%rbp),%r8d
    122f:	je     137b <bch_encode_func_pgot+0x27b>
    1235:	mov    -0xbc(%rbp),%eax
    123b:	mov    -0x108(%rbp),%rcx
    1242:	lea    -0x2(%r8),%edx
    1246:	mov    %rax,-0xb0(%rbp)
    124d:	lea    0x0(,%rax,4),%r9
    1255:	lea    (%rcx,%rbx,4),%rax
    1259:	mov    %rax,-0xe8(%rbp)
    1260:	mov    -0xb8(%rbp),%rax
    1267:	mov    (%rcx),%r13d
    126a:	add    $0x4,%rcx
```

## 02_bch_encode/no_retpoline/func_pgot: bch_encode_func_pgot, 1389, pgot_memcpy_table

```asm
    1382:	mov    0x30(%rax),%rdi
    1386:	mov    0x0(%rip),%rax        # 138d <bch_encode_func_pgot+0x28d>
			1389: R_X86_64_PC32	pgot_memcpy_table-0x4
    138d:	mov    -0x110(%rbp),%rdx
    1394:	lea    -0xa8(%rbp),%rsi
    139b:	call   *%rax
    139d:	mov    -0x120(%rbp),%edi
    13a3:	test   %edi,%edi
    13a5:	jne    150d <bch_encode_func_pgot+0x40d>
    13ab:	mov    -0x118(%rbp),%rsi
    13b2:	test   %rsi,%rsi
    13b5:	je     13c7 <bch_encode_func_pgot+0x2c7>
    13b7:	mov    -0xb8(%rbp),%rdi
    13be:	mov    0x30(%rdi),%rdx
    13c2:	call   540 <store_ecc8_func_pgot>
    13c7:	mov    -0x30(%rbp),%rax
    13cb:	sub    %gs:0x28,%rax
    13d4:	jne    1678 <bch_encode_func_pgot+0x578>
    13da:	add    $0x110,%rsp
```

## 02_bch_encode/no_retpoline/func_pgot: bch_encode_func_pgot, 13f7, memset

```asm
    13f4:	xor    %esi,%esi
    13f6:	call   13fb <bch_encode_func_pgot+0x2fb>
			13f7: R_X86_64_PLT32	memset-0x4
    13fb:	mov    -0x108(%rbp),%rax
    1402:	mov    -0xb0(%rbp),%r8d
    1409:	and    $0x3,%eax
    140c:	je     11e9 <bch_encode_func_pgot+0xe9>
    1412:	mov    $0x4,%ebx
    1417:	mov    -0xb8(%rbp),%rdi
    141e:	mov    -0x108(%rbp),%r15
    1425:	mov    %r8d,-0xb0(%rbp)
    142c:	sub    %rax,%rbx
    142f:	mov    -0x11c(%rbp),%eax
    1435:	mov    0x30(%rdi),%rcx
    1439:	mov    %r15,%rsi
    143c:	cmp    %rax,%rbx
    143f:	mov    %rax,%r14
    1442:	cmova  %rax,%rbx
    1446:	mov    %ebx,%edx
```

## 02_bch_encode/no_retpoline/origin: load_ecc8_origin, 1867, memcpy

```asm
    1862:	lea    -0x34(%rbp),%rdi
    1866:	call   186b <load_ecc8_origin+0xeb>
			1867: R_X86_64_PLT32	memcpy-0x4
    186b:	movzbl -0x34(%rbp),%esi
    186f:	mov    %r15,%rdi
    1872:	call   0 <swap_bits_origin>
    1877:	movzbl -0x33(%rbp),%esi
    187b:	mov    %r15,%rdi
    187e:	mov    %eax,%r12d
    1881:	call   0 <swap_bits_origin>
    1886:	movzbl -0x32(%rbp),%esi
    188a:	mov    %r15,%rdi
    188d:	shl    $0x18,%r12d
    1891:	movzbl %al,%eax
    1894:	shl    $0x10,%eax
    1897:	or     %eax,%r12d
    189a:	call   0 <swap_bits_origin>
    189f:	movzbl -0x31(%rbp),%esi
    18a3:	mov    %r15,%rdi
```

## 02_bch_encode/no_retpoline/data_pgot: load_ecc8_data_pgot, 19e7, memcpy

```asm
    19e2:	lea    -0x34(%rbp),%rdi
    19e6:	call   19eb <load_ecc8_data_pgot+0xeb>
			19e7: R_X86_64_PLT32	memcpy-0x4
    19eb:	movzbl -0x34(%rbp),%esi
    19ef:	mov    %r15,%rdi
    19f2:	call   140 <swap_bits_data_pgot>
    19f7:	movzbl -0x33(%rbp),%esi
    19fb:	mov    %r15,%rdi
    19fe:	mov    %eax,%r12d
    1a01:	call   140 <swap_bits_data_pgot>
    1a06:	movzbl -0x32(%rbp),%esi
    1a0a:	mov    %r15,%rdi
    1a0d:	shl    $0x18,%r12d
    1a11:	movzbl %al,%eax
    1a14:	shl    $0x10,%eax
    1a17:	or     %eax,%r12d
    1a1a:	call   140 <swap_bits_data_pgot>
    1a1f:	movzbl -0x31(%rbp),%esi
    1a23:	mov    %r15,%rdi
```

## 02_bch_encode/no_retpoline/origin: store_ecc8_origin, 1b8e, memcpy

```asm
    1b8a:	mov    %r12,%rdi
    1b8d:	call   1b92 <store_ecc8_origin+0x112>
			1b8e: R_X86_64_PLT32	memcpy-0x4
    1b92:	mov    -0x30(%rbp),%rax
    1b96:	sub    %gs:0x28,%rax
    1b9f:	jne    1bb1 <store_ecc8_origin+0x131>
    1ba1:	add    $0x18,%rsp
    1ba5:	pop    %rbx
    1ba6:	pop    %r12
    1ba8:	pop    %r13
    1baa:	pop    %r14
    1bac:	pop    %r15
    1bae:	pop    %rbp
    1baf:	ret    
    1bb0:	int3   
    1bb1:	call   1bb6 <store_ecc8_origin+0x136>
			1bb2: R_X86_64_PLT32	__stack_chk_fail-0x4
    1bb6:	cs nopw 0x0(%rax,%rax,1)

```

## 02_bch_encode/no_retpoline/data_pgot: store_ecc8_data_pgot, 1cce, memcpy

```asm
    1cca:	mov    %r12,%rdi
    1ccd:	call   1cd2 <store_ecc8_data_pgot+0x112>
			1cce: R_X86_64_PLT32	memcpy-0x4
    1cd2:	mov    -0x30(%rbp),%rax
    1cd6:	sub    %gs:0x28,%rax
    1cdf:	jne    1cf1 <store_ecc8_data_pgot+0x131>
    1ce1:	add    $0x18,%rsp
    1ce5:	pop    %rbx
    1ce6:	pop    %r12
    1ce8:	pop    %r13
    1cea:	pop    %r14
    1cec:	pop    %r15
    1cee:	pop    %rbp
    1cef:	ret    
    1cf0:	int3   
    1cf1:	call   1cf6 <store_ecc8_data_pgot+0x136>
			1cf2: R_X86_64_PLT32	__stack_chk_fail-0x4
    1cf6:	cs nopw 0x0(%rax,%rax,1)

```

## 02_bch_encode/no_retpoline/data_pgot: bch_encode_data_pgot, 1e21, memcpy

```asm
    1e1d:	mov    %r12,%rsi
    1e20:	call   1e25 <bch_encode_data_pgot+0x125>
			1e21: R_X86_64_PLT32	memcpy-0x4
    1e25:	test   %ebx,%ebx
    1e27:	mov    -0xb0(%rbp),%r8d
    1e2e:	je     1f85 <bch_encode_data_pgot+0x285>
    1e34:	mov    -0xbc(%rbp),%eax
    1e3a:	mov    -0x108(%rbp),%rcx
    1e41:	lea    -0x2(%r8),%edx
    1e45:	mov    %rax,-0xb0(%rbp)
    1e4c:	lea    0x0(,%rax,4),%r9
    1e54:	lea    (%rcx,%rbx,4),%rax
    1e58:	mov    %rax,-0xe8(%rbp)
    1e5f:	mov    -0xb8(%rbp),%rax
    1e66:	mov    (%rcx),%r13d
    1e69:	add    $0x4,%rcx
    1e6d:	movzbl 0x80(%rax),%ebx
    1e74:	bswap  %r13d
    1e77:	cmp    $0x1,%bl
```

## 02_bch_encode/no_retpoline/data_pgot: bch_encode_data_pgot, 1f97, memcpy

```asm
    1f93:	mov    %r12,%rdi
    1f96:	call   1f9b <bch_encode_data_pgot+0x29b>
			1f97: R_X86_64_PLT32	memcpy-0x4
    1f9b:	mov    -0x120(%rbp),%eax
    1fa1:	test   %eax,%eax
    1fa3:	jne    210b <bch_encode_data_pgot+0x40b>
    1fa9:	mov    -0x118(%rbp),%rsi
    1fb0:	test   %rsi,%rsi
    1fb3:	je     1fc5 <bch_encode_data_pgot+0x2c5>
    1fb5:	mov    -0xb8(%rbp),%rdi
    1fbc:	mov    0x30(%rdi),%rdx
    1fc0:	call   1bc0 <store_ecc8_data_pgot>
    1fc5:	mov    -0x30(%rbp),%rax
    1fc9:	sub    %gs:0x28,%rax
    1fd2:	jne    2273 <bch_encode_data_pgot+0x573>
    1fd8:	add    $0x110,%rsp
    1fdf:	pop    %rbx
    1fe0:	pop    %r12
    1fe2:	pop    %r13
```

## 02_bch_encode/no_retpoline/data_pgot: bch_encode_data_pgot, 1ff5, memset

```asm
    1ff2:	xor    %esi,%esi
    1ff4:	call   1ff9 <bch_encode_data_pgot+0x2f9>
			1ff5: R_X86_64_PLT32	memset-0x4
    1ff9:	mov    -0x108(%rbp),%rax
    2000:	mov    -0xb0(%rbp),%r8d
    2007:	and    $0x3,%eax
    200a:	je     1de9 <bch_encode_data_pgot+0xe9>
    2010:	mov    $0x4,%ebx
    2015:	mov    -0xb8(%rbp),%rdi
    201c:	mov    -0x108(%rbp),%r15
    2023:	mov    %r8d,-0xb0(%rbp)
    202a:	sub    %rax,%rbx
    202d:	mov    -0x11c(%rbp),%eax
    2033:	mov    0x30(%rdi),%rcx
    2037:	mov    %r15,%rsi
    203a:	cmp    %rax,%rbx
    203d:	mov    %rax,%r14
    2040:	cmova  %rax,%rbx
    2044:	mov    %ebx,%edx
```

## 02_bch_encode/no_retpoline/origin: bch_encode_origin, 24a1, memcpy

```asm
    249d:	mov    %r12,%rsi
    24a0:	call   24a5 <bch_encode_origin+0x125>
			24a1: R_X86_64_PLT32	memcpy-0x4
    24a5:	test   %ebx,%ebx
    24a7:	mov    -0xb0(%rbp),%r8d
    24ae:	je     2605 <bch_encode_origin+0x285>
    24b4:	mov    -0xbc(%rbp),%eax
    24ba:	mov    -0x108(%rbp),%rcx
    24c1:	lea    -0x2(%r8),%edx
    24c5:	mov    %rax,-0xb0(%rbp)
    24cc:	lea    0x0(,%rax,4),%r9
    24d4:	lea    (%rcx,%rbx,4),%rax
    24d8:	mov    %rax,-0xe8(%rbp)
    24df:	mov    -0xb8(%rbp),%rax
    24e6:	mov    (%rcx),%r13d
    24e9:	add    $0x4,%rcx
    24ed:	movzbl 0x80(%rax),%ebx
    24f4:	bswap  %r13d
    24f7:	cmp    $0x1,%bl
```

## 02_bch_encode/no_retpoline/origin: bch_encode_origin, 2617, memcpy

```asm
    2613:	mov    %r12,%rdi
    2616:	call   261b <bch_encode_origin+0x29b>
			2617: R_X86_64_PLT32	memcpy-0x4
    261b:	mov    -0x120(%rbp),%eax
    2621:	test   %eax,%eax
    2623:	jne    278b <bch_encode_origin+0x40b>
    2629:	mov    -0x118(%rbp),%rsi
    2630:	test   %rsi,%rsi
    2633:	je     2645 <bch_encode_origin+0x2c5>
    2635:	mov    -0xb8(%rbp),%rdi
    263c:	mov    0x30(%rdi),%rdx
    2640:	call   1a80 <store_ecc8_origin>
    2645:	mov    -0x30(%rbp),%rax
    2649:	sub    %gs:0x28,%rax
    2652:	jne    28f3 <bch_encode_origin+0x573>
    2658:	add    $0x110,%rsp
    265f:	pop    %rbx
    2660:	pop    %r12
    2662:	pop    %r13
```

## 02_bch_encode/no_retpoline/origin: bch_encode_origin, 2675, memset

```asm
    2672:	xor    %esi,%esi
    2674:	call   2679 <bch_encode_origin+0x2f9>
			2675: R_X86_64_PLT32	memset-0x4
    2679:	mov    -0x108(%rbp),%rax
    2680:	mov    -0xb0(%rbp),%r8d
    2687:	and    $0x3,%eax
    268a:	je     2469 <bch_encode_origin+0xe9>
    2690:	mov    $0x4,%ebx
    2695:	mov    -0xb8(%rbp),%rdi
    269c:	mov    -0x108(%rbp),%r15
    26a3:	mov    %r8d,-0xb0(%rbp)
    26aa:	sub    %rax,%rbx
    26ad:	mov    -0x11c(%rbp),%eax
    26b3:	mov    0x30(%rdi),%rcx
    26b7:	mov    %r15,%rsi
    26ba:	cmp    %rax,%rbx
    26bd:	mov    %rax,%r14
    26c0:	cmova  %rax,%rbx
    26c4:	mov    %ebx,%edx
```

## 02_bch_encode/retpoline/data_pgot: swap_bits_data_pgot, 166, pgot_swap_bits_table

```asm
     161:	je     171 <swap_bits_data_pgot+0x31>
     163:	mov    0x0(%rip),%rax        # 16a <swap_bits_data_pgot+0x2a>
			166: R_X86_64_PC32	pgot_swap_bits_table-0x4
     16a:	movzbl %bl,%ebx
     16d:	movzbl (%rax,%rbx,1),%eax
     171:	pop    %rbx
     172:	pop    %r12
     174:	pop    %rbp
     175:	ret    
     176:	int3   
     177:	nopw   0x0(%rax,%rax,1)

```

## 02_bch_encode/retpoline/func_pgot: load_ecc8_func_pgot, 489, pgot_memcpy_table

```asm
     481:	imul   0x8(%r15),%eax
     486:	mov    0x0(%rip),%rcx        # 48d <load_ecc8_func_pgot+0xcd>
			489: R_X86_64_PC32	pgot_memcpy_table-0x4
     48d:	mov    -0x44(%rbp),%r14d
     491:	lea    0x7(%rax),%edx
     494:	mov    -0x40(%rbp),%rsi
     498:	lea    -0x34(%rbp),%rdi
     49c:	shr    $0x3,%edx
     49f:	lea    0x0(,%r14,4),%eax
     4a7:	sub    %eax,%edx
     4a9:	jmp    4bd <load_ecc8_func_pgot+0xfd>
     4ab:	call   4b7 <load_ecc8_func_pgot+0xf7>
     4b0:	pause  
     4b2:	lfence 
     4b5:	jmp    4b0 <load_ecc8_func_pgot+0xf0>
     4b7:	mov    %rcx,(%rsp)
     4bb:	ret    
     4bc:	int3   
     4bd:	call   4ab <load_ecc8_func_pgot+0xeb>
```

## 02_bch_encode/retpoline/func_pgot: store_ecc8_func_pgot, 67f, pgot_memcpy_table

```asm
     67a:	sub    %eax,%edx
     67c:	mov    0x0(%rip),%rax        # 683 <store_ecc8_func_pgot+0x103>
			67f: R_X86_64_PC32	pgot_memcpy_table-0x4
     683:	lea    -0x34(%rbp),%rsi
     687:	mov    %r12,%rdi
     68a:	jmp    69e <store_ecc8_func_pgot+0x11e>
     68c:	call   698 <store_ecc8_func_pgot+0x118>
     691:	pause  
     693:	lfence 
     696:	jmp    691 <store_ecc8_func_pgot+0x111>
     698:	mov    %rax,(%rsp)
     69c:	ret    
     69d:	int3   
     69e:	call   68c <store_ecc8_func_pgot+0x10c>
     6a3:	mov    -0x30(%rbp),%rax
     6a7:	sub    %gs:0x28,%rax
     6b0:	jne    6c2 <store_ecc8_func_pgot+0x142>
     6b2:	add    $0x18,%rsp
     6b6:	pop    %rbx
```

## 02_bch_encode/retpoline/all_pgot: swap_bits_all_pgot, 726, pgot_swap_bits_table

```asm
     721:	je     731 <swap_bits_all_pgot+0x31>
     723:	mov    0x0(%rip),%rax        # 72a <swap_bits_all_pgot+0x2a>
			726: R_X86_64_PC32	pgot_swap_bits_table-0x4
     72a:	movzbl %bl,%ebx
     72d:	movzbl (%rax,%rbx,1),%eax
     731:	pop    %rbx
     732:	pop    %r12
     734:	pop    %rbp
     735:	ret    
     736:	int3   
     737:	nopw   0x0(%rax,%rax,1)

```

## 02_bch_encode/retpoline/all_pgot: load_ecc8_all_pgot, 909, pgot_memcpy_table

```asm
     901:	imul   0x8(%r15),%eax
     906:	mov    0x0(%rip),%rcx        # 90d <load_ecc8_all_pgot+0xcd>
			909: R_X86_64_PC32	pgot_memcpy_table-0x4
     90d:	mov    -0x44(%rbp),%r14d
     911:	lea    0x7(%rax),%edx
     914:	mov    -0x40(%rbp),%rsi
     918:	lea    -0x34(%rbp),%rdi
     91c:	shr    $0x3,%edx
     91f:	lea    0x0(,%r14,4),%eax
     927:	sub    %eax,%edx
     929:	jmp    93d <load_ecc8_all_pgot+0xfd>
     92b:	call   937 <load_ecc8_all_pgot+0xf7>
     930:	pause  
     932:	lfence 
     935:	jmp    930 <load_ecc8_all_pgot+0xf0>
     937:	mov    %rcx,(%rsp)
     93b:	ret    
     93c:	int3   
     93d:	call   92b <load_ecc8_all_pgot+0xeb>
```

## 02_bch_encode/retpoline/all_pgot: store_ecc8_all_pgot, aff, pgot_memcpy_table

```asm
     afa:	sub    %eax,%edx
     afc:	mov    0x0(%rip),%rax        # b03 <store_ecc8_all_pgot+0x103>
			aff: R_X86_64_PC32	pgot_memcpy_table-0x4
     b03:	lea    -0x34(%rbp),%rsi
     b07:	mov    %r12,%rdi
     b0a:	jmp    b1e <store_ecc8_all_pgot+0x11e>
     b0c:	call   b18 <store_ecc8_all_pgot+0x118>
     b11:	pause  
     b13:	lfence 
     b16:	jmp    b11 <store_ecc8_all_pgot+0x111>
     b18:	mov    %rax,(%rsp)
     b1c:	ret    
     b1d:	int3   
     b1e:	call   b0c <store_ecc8_all_pgot+0x10c>
     b23:	mov    -0x30(%rbp),%rax
     b27:	sub    %gs:0x28,%rax
     b30:	jne    b42 <store_ecc8_all_pgot+0x142>
     b32:	add    $0x18,%rsp
     b36:	pop    %rbx
```

## 02_bch_encode/retpoline/all_pgot: bch_encode_all_pgot, c92, pgot_memcpy_table

```asm
     c8b:	mov    0x30(%rax),%rsi
     c8f:	mov    0x0(%rip),%rax        # c96 <bch_encode_all_pgot+0x116>
			c92: R_X86_64_PC32	pgot_memcpy_table-0x4
     c96:	mov    -0x110(%rbp),%rdx
     c9d:	lea    -0xa8(%rbp),%rdi
     ca4:	jmp    cb8 <bch_encode_all_pgot+0x138>
     ca6:	call   cb2 <bch_encode_all_pgot+0x132>
     cab:	pause  
     cad:	lfence 
     cb0:	jmp    cab <bch_encode_all_pgot+0x12b>
     cb2:	mov    %rax,(%rsp)
     cb6:	ret    
     cb7:	int3   
     cb8:	call   ca6 <bch_encode_all_pgot+0x126>
     cbd:	test   %ebx,%ebx
     cbf:	mov    -0xb0(%rbp),%r8d
     cc6:	je     e12 <bch_encode_all_pgot+0x292>
     ccc:	mov    -0xbc(%rbp),%eax
     cd2:	mov    -0x108(%rbp),%rcx
```

## 02_bch_encode/retpoline/all_pgot: bch_encode_all_pgot, e20, pgot_memcpy_table

```asm
     e19:	mov    0x30(%rax),%rdi
     e1d:	mov    0x0(%rip),%rax        # e24 <bch_encode_all_pgot+0x2a4>
			e20: R_X86_64_PC32	pgot_memcpy_table-0x4
     e24:	mov    -0x110(%rbp),%rdx
     e2b:	lea    -0xa8(%rbp),%rsi
     e32:	jmp    e46 <bch_encode_all_pgot+0x2c6>
     e34:	call   e40 <bch_encode_all_pgot+0x2c0>
     e39:	pause  
     e3b:	lfence 
     e3e:	jmp    e39 <bch_encode_all_pgot+0x2b9>
     e40:	mov    %rax,(%rsp)
     e44:	ret    
     e45:	int3   
     e46:	call   e34 <bch_encode_all_pgot+0x2b4>
     e4b:	mov    -0x120(%rbp),%edi
     e51:	test   %edi,%edi
     e53:	jne    fbb <bch_encode_all_pgot+0x43b>
     e59:	mov    -0x118(%rbp),%rsi
     e60:	test   %rsi,%rsi
```

## 02_bch_encode/retpoline/all_pgot: bch_encode_all_pgot, ea5, memset

```asm
     ea2:	xor    %esi,%esi
     ea4:	call   ea9 <bch_encode_all_pgot+0x329>
			ea5: R_X86_64_PLT32	memset-0x4
     ea9:	mov    -0x108(%rbp),%rax
     eb0:	mov    -0xb0(%rbp),%r8d
     eb7:	and    $0x3,%eax
     eba:	je     c69 <bch_encode_all_pgot+0xe9>
     ec0:	mov    $0x4,%ebx
     ec5:	mov    -0xb8(%rbp),%rdi
     ecc:	mov    -0x108(%rbp),%r15
     ed3:	mov    %r8d,-0xb0(%rbp)
     eda:	sub    %rax,%rbx
     edd:	mov    -0x11c(%rbp),%eax
     ee3:	mov    0x30(%rdi),%rcx
     ee7:	mov    %r15,%rsi
     eea:	cmp    %rax,%rbx
     eed:	mov    %rax,%r14
     ef0:	cmova  %rax,%rbx
     ef4:	mov    %ebx,%edx
```

## 02_bch_encode/retpoline/func_pgot: bch_encode_func_pgot, 1352, pgot_memcpy_table

```asm
    134b:	mov    0x30(%rax),%rsi
    134f:	mov    0x0(%rip),%rax        # 1356 <bch_encode_func_pgot+0x116>
			1352: R_X86_64_PC32	pgot_memcpy_table-0x4
    1356:	mov    -0x110(%rbp),%rdx
    135d:	lea    -0xa8(%rbp),%rdi
    1364:	jmp    1378 <bch_encode_func_pgot+0x138>
    1366:	call   1372 <bch_encode_func_pgot+0x132>
    136b:	pause  
    136d:	lfence 
    1370:	jmp    136b <bch_encode_func_pgot+0x12b>
    1372:	mov    %rax,(%rsp)
    1376:	ret    
    1377:	int3   
    1378:	call   1366 <bch_encode_func_pgot+0x126>
    137d:	test   %ebx,%ebx
    137f:	mov    -0xb0(%rbp),%r8d
    1386:	je     14d2 <bch_encode_func_pgot+0x292>
    138c:	mov    -0xbc(%rbp),%eax
    1392:	mov    -0x108(%rbp),%rcx
```

## 02_bch_encode/retpoline/func_pgot: bch_encode_func_pgot, 14e0, pgot_memcpy_table

```asm
    14d9:	mov    0x30(%rax),%rdi
    14dd:	mov    0x0(%rip),%rax        # 14e4 <bch_encode_func_pgot+0x2a4>
			14e0: R_X86_64_PC32	pgot_memcpy_table-0x4
    14e4:	mov    -0x110(%rbp),%rdx
    14eb:	lea    -0xa8(%rbp),%rsi
    14f2:	jmp    1506 <bch_encode_func_pgot+0x2c6>
    14f4:	call   1500 <bch_encode_func_pgot+0x2c0>
    14f9:	pause  
    14fb:	lfence 
    14fe:	jmp    14f9 <bch_encode_func_pgot+0x2b9>
    1500:	mov    %rax,(%rsp)
    1504:	ret    
    1505:	int3   
    1506:	call   14f4 <bch_encode_func_pgot+0x2b4>
    150b:	mov    -0x120(%rbp),%edi
    1511:	test   %edi,%edi
    1513:	jne    167b <bch_encode_func_pgot+0x43b>
    1519:	mov    -0x118(%rbp),%rsi
    1520:	test   %rsi,%rsi
```

## 02_bch_encode/retpoline/func_pgot: bch_encode_func_pgot, 1565, memset

```asm
    1562:	xor    %esi,%esi
    1564:	call   1569 <bch_encode_func_pgot+0x329>
			1565: R_X86_64_PLT32	memset-0x4
    1569:	mov    -0x108(%rbp),%rax
    1570:	mov    -0xb0(%rbp),%r8d
    1577:	and    $0x3,%eax
    157a:	je     1329 <bch_encode_func_pgot+0xe9>
    1580:	mov    $0x4,%ebx
    1585:	mov    -0xb8(%rbp),%rdi
    158c:	mov    -0x108(%rbp),%r15
    1593:	mov    %r8d,-0xb0(%rbp)
    159a:	sub    %rax,%rbx
    159d:	mov    -0x11c(%rbp),%eax
    15a3:	mov    0x30(%rdi),%rcx
    15a7:	mov    %r15,%rsi
    15aa:	cmp    %rax,%rbx
    15ad:	mov    %rax,%r14
    15b0:	cmova  %rax,%rbx
    15b4:	mov    %ebx,%edx
```

## 02_bch_encode/retpoline/origin: load_ecc8_origin, 19e7, memcpy

```asm
    19e2:	lea    -0x34(%rbp),%rdi
    19e6:	call   19eb <load_ecc8_origin+0xeb>
			19e7: R_X86_64_PLT32	memcpy-0x4
    19eb:	movzbl -0x34(%rbp),%esi
    19ef:	mov    %r15,%rdi
    19f2:	call   0 <swap_bits_origin>
    19f7:	movzbl -0x33(%rbp),%esi
    19fb:	mov    %r15,%rdi
    19fe:	mov    %eax,%r12d
    1a01:	call   0 <swap_bits_origin>
    1a06:	movzbl -0x32(%rbp),%esi
    1a0a:	mov    %r15,%rdi
    1a0d:	shl    $0x18,%r12d
    1a11:	movzbl %al,%eax
    1a14:	shl    $0x10,%eax
    1a17:	or     %eax,%r12d
    1a1a:	call   0 <swap_bits_origin>
    1a1f:	movzbl -0x31(%rbp),%esi
    1a23:	mov    %r15,%rdi
```

## 02_bch_encode/retpoline/data_pgot: load_ecc8_data_pgot, 1b67, memcpy

```asm
    1b62:	lea    -0x34(%rbp),%rdi
    1b66:	call   1b6b <load_ecc8_data_pgot+0xeb>
			1b67: R_X86_64_PLT32	memcpy-0x4
    1b6b:	movzbl -0x34(%rbp),%esi
    1b6f:	mov    %r15,%rdi
    1b72:	call   140 <swap_bits_data_pgot>
    1b77:	movzbl -0x33(%rbp),%esi
    1b7b:	mov    %r15,%rdi
    1b7e:	mov    %eax,%r12d
    1b81:	call   140 <swap_bits_data_pgot>
    1b86:	movzbl -0x32(%rbp),%esi
    1b8a:	mov    %r15,%rdi
    1b8d:	shl    $0x18,%r12d
    1b91:	movzbl %al,%eax
    1b94:	shl    $0x10,%eax
    1b97:	or     %eax,%r12d
    1b9a:	call   140 <swap_bits_data_pgot>
    1b9f:	movzbl -0x31(%rbp),%esi
    1ba3:	mov    %r15,%rdi
```

## 02_bch_encode/retpoline/origin: store_ecc8_origin, 1d0e, memcpy

```asm
    1d0a:	mov    %r12,%rdi
    1d0d:	call   1d12 <store_ecc8_origin+0x112>
			1d0e: R_X86_64_PLT32	memcpy-0x4
    1d12:	mov    -0x30(%rbp),%rax
    1d16:	sub    %gs:0x28,%rax
    1d1f:	jne    1d31 <store_ecc8_origin+0x131>
    1d21:	add    $0x18,%rsp
    1d25:	pop    %rbx
    1d26:	pop    %r12
    1d28:	pop    %r13
    1d2a:	pop    %r14
    1d2c:	pop    %r15
    1d2e:	pop    %rbp
    1d2f:	ret    
    1d30:	int3   
    1d31:	call   1d36 <store_ecc8_origin+0x136>
			1d32: R_X86_64_PLT32	__stack_chk_fail-0x4
    1d36:	cs nopw 0x0(%rax,%rax,1)

```

## 02_bch_encode/retpoline/data_pgot: store_ecc8_data_pgot, 1e4e, memcpy

```asm
    1e4a:	mov    %r12,%rdi
    1e4d:	call   1e52 <store_ecc8_data_pgot+0x112>
			1e4e: R_X86_64_PLT32	memcpy-0x4
    1e52:	mov    -0x30(%rbp),%rax
    1e56:	sub    %gs:0x28,%rax
    1e5f:	jne    1e71 <store_ecc8_data_pgot+0x131>
    1e61:	add    $0x18,%rsp
    1e65:	pop    %rbx
    1e66:	pop    %r12
    1e68:	pop    %r13
    1e6a:	pop    %r14
    1e6c:	pop    %r15
    1e6e:	pop    %rbp
    1e6f:	ret    
    1e70:	int3   
    1e71:	call   1e76 <store_ecc8_data_pgot+0x136>
			1e72: R_X86_64_PLT32	__stack_chk_fail-0x4
    1e76:	cs nopw 0x0(%rax,%rax,1)

```

## 02_bch_encode/retpoline/data_pgot: bch_encode_data_pgot, 1fa1, memcpy

```asm
    1f9d:	mov    %r12,%rsi
    1fa0:	call   1fa5 <bch_encode_data_pgot+0x125>
			1fa1: R_X86_64_PLT32	memcpy-0x4
    1fa5:	test   %ebx,%ebx
    1fa7:	mov    -0xb0(%rbp),%r8d
    1fae:	je     2105 <bch_encode_data_pgot+0x285>
    1fb4:	mov    -0xbc(%rbp),%eax
    1fba:	mov    -0x108(%rbp),%rcx
    1fc1:	lea    -0x2(%r8),%edx
    1fc5:	mov    %rax,-0xb0(%rbp)
    1fcc:	lea    0x0(,%rax,4),%r9
    1fd4:	lea    (%rcx,%rbx,4),%rax
    1fd8:	mov    %rax,-0xe8(%rbp)
    1fdf:	mov    -0xb8(%rbp),%rax
    1fe6:	mov    (%rcx),%r13d
    1fe9:	add    $0x4,%rcx
    1fed:	movzbl 0x80(%rax),%ebx
    1ff4:	bswap  %r13d
    1ff7:	cmp    $0x1,%bl
```

## 02_bch_encode/retpoline/data_pgot: bch_encode_data_pgot, 2117, memcpy

```asm
    2113:	mov    %r12,%rdi
    2116:	call   211b <bch_encode_data_pgot+0x29b>
			2117: R_X86_64_PLT32	memcpy-0x4
    211b:	mov    -0x120(%rbp),%eax
    2121:	test   %eax,%eax
    2123:	jne    228b <bch_encode_data_pgot+0x40b>
    2129:	mov    -0x118(%rbp),%rsi
    2130:	test   %rsi,%rsi
    2133:	je     2145 <bch_encode_data_pgot+0x2c5>
    2135:	mov    -0xb8(%rbp),%rdi
    213c:	mov    0x30(%rdi),%rdx
    2140:	call   1d40 <store_ecc8_data_pgot>
    2145:	mov    -0x30(%rbp),%rax
    2149:	sub    %gs:0x28,%rax
    2152:	jne    23f3 <bch_encode_data_pgot+0x573>
    2158:	add    $0x110,%rsp
    215f:	pop    %rbx
    2160:	pop    %r12
    2162:	pop    %r13
```

## 02_bch_encode/retpoline/data_pgot: bch_encode_data_pgot, 2175, memset

```asm
    2172:	xor    %esi,%esi
    2174:	call   2179 <bch_encode_data_pgot+0x2f9>
			2175: R_X86_64_PLT32	memset-0x4
    2179:	mov    -0x108(%rbp),%rax
    2180:	mov    -0xb0(%rbp),%r8d
    2187:	and    $0x3,%eax
    218a:	je     1f69 <bch_encode_data_pgot+0xe9>
    2190:	mov    $0x4,%ebx
    2195:	mov    -0xb8(%rbp),%rdi
    219c:	mov    -0x108(%rbp),%r15
    21a3:	mov    %r8d,-0xb0(%rbp)
    21aa:	sub    %rax,%rbx
    21ad:	mov    -0x11c(%rbp),%eax
    21b3:	mov    0x30(%rdi),%rcx
    21b7:	mov    %r15,%rsi
    21ba:	cmp    %rax,%rbx
    21bd:	mov    %rax,%r14
    21c0:	cmova  %rax,%rbx
    21c4:	mov    %ebx,%edx
```

## 02_bch_encode/retpoline/origin: bch_encode_origin, 2621, memcpy

```asm
    261d:	mov    %r12,%rsi
    2620:	call   2625 <bch_encode_origin+0x125>
			2621: R_X86_64_PLT32	memcpy-0x4
    2625:	test   %ebx,%ebx
    2627:	mov    -0xb0(%rbp),%r8d
    262e:	je     2785 <bch_encode_origin+0x285>
    2634:	mov    -0xbc(%rbp),%eax
    263a:	mov    -0x108(%rbp),%rcx
    2641:	lea    -0x2(%r8),%edx
    2645:	mov    %rax,-0xb0(%rbp)
    264c:	lea    0x0(,%rax,4),%r9
    2654:	lea    (%rcx,%rbx,4),%rax
    2658:	mov    %rax,-0xe8(%rbp)
    265f:	mov    -0xb8(%rbp),%rax
    2666:	mov    (%rcx),%r13d
    2669:	add    $0x4,%rcx
    266d:	movzbl 0x80(%rax),%ebx
    2674:	bswap  %r13d
    2677:	cmp    $0x1,%bl
```

## 02_bch_encode/retpoline/origin: bch_encode_origin, 2797, memcpy

```asm
    2793:	mov    %r12,%rdi
    2796:	call   279b <bch_encode_origin+0x29b>
			2797: R_X86_64_PLT32	memcpy-0x4
    279b:	mov    -0x120(%rbp),%eax
    27a1:	test   %eax,%eax
    27a3:	jne    290b <bch_encode_origin+0x40b>
    27a9:	mov    -0x118(%rbp),%rsi
    27b0:	test   %rsi,%rsi
    27b3:	je     27c5 <bch_encode_origin+0x2c5>
    27b5:	mov    -0xb8(%rbp),%rdi
    27bc:	mov    0x30(%rdi),%rdx
    27c0:	call   1c00 <store_ecc8_origin>
    27c5:	mov    -0x30(%rbp),%rax
    27c9:	sub    %gs:0x28,%rax
    27d2:	jne    2a73 <bch_encode_origin+0x573>
    27d8:	add    $0x110,%rsp
    27df:	pop    %rbx
    27e0:	pop    %r12
    27e2:	pop    %r13
```

## 02_bch_encode/retpoline/origin: bch_encode_origin, 27f5, memset

```asm
    27f2:	xor    %esi,%esi
    27f4:	call   27f9 <bch_encode_origin+0x2f9>
			27f5: R_X86_64_PLT32	memset-0x4
    27f9:	mov    -0x108(%rbp),%rax
    2800:	mov    -0xb0(%rbp),%r8d
    2807:	and    $0x3,%eax
    280a:	je     25e9 <bch_encode_origin+0xe9>
    2810:	mov    $0x4,%ebx
    2815:	mov    -0xb8(%rbp),%rdi
    281c:	mov    -0x108(%rbp),%r15
    2823:	mov    %r8d,-0xb0(%rbp)
    282a:	sub    %rax,%rbx
    282d:	mov    -0x11c(%rbp),%eax
    2833:	mov    0x30(%rdi),%rcx
    2837:	mov    %r15,%rsi
    283a:	cmp    %rax,%rbx
    283d:	mov    %rax,%r14
    2840:	cmova  %rax,%rbx
    2844:	mov    %ebx,%edx
```

## 03_zlib_deflate/no_retpoline/all_pgot: fill_window, a78, pgot_memcpy_table_all_pgot

```asm
     a72:	mov    %rbx,%rdx
     a75:	mov    0x0(%rip),%rax        # a7c <fill_window+0x10c>
			a78: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     a7c:	call   *%rax
     a7e:	mov    -0x70(%rbp),%rax
     a82:	mov    -0x58(%rbp),%rcx
     a86:	add    %rbx,(%rax)
     a89:	add    %rbx,0x10(%rax)
     a8d:	mov    -0x74(%rbp),%eax
     a90:	add    0x9c(%rcx),%eax
     a96:	mov    %eax,-0x5c(%rbp)
     a99:	mov    -0x58(%rbp),%rdi
     a9d:	mov    -0x5c(%rbp),%eax
     aa0:	mov    %eax,0x9c(%rdi)
     aa6:	cmp    $0x2,%eax
     aa9:	jbe    af0 <fill_window+0x180>
     aab:	mov    0x94(%rdi),%ecx
     ab1:	mov    0x48(%rdi),%rax
     ab5:	mov    %rcx,%rdx
```

## 03_zlib_deflate/no_retpoline/all_pgot: fill_window, d20, pgot_memcpy_table_all_pgot

```asm
     d1a:	mov    %rcx,%r14
     d1d:	mov    0x0(%rip),%rax        # d24 <fill_window+0x3b4>
			d20: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     d24:	lea    (%rdi,%r15,1),%rsi
     d28:	mov    %r15,%rdx
     d2b:	call   *%rax
     d2d:	mov    0x6c(%r14),%ecx
     d31:	mov    -0x94(%rbp),%r8d
     d38:	xor    %esi,%esi
     d3a:	mov    0x60(%r14),%rax
     d3e:	sub    %r8d,0x98(%r14)
     d45:	mov    %rcx,%rdx
     d48:	sub    %r8d,0x94(%r14)
     d4f:	sub    %r15,0x80(%r14)
     d56:	sub    $0x1,%edx
     d59:	lea    (%rax,%rcx,2),%rax
     d5d:	not    %rdx
     d60:	lea    (%rax,%rdx,2),%rdi
     d64:	movzwl -0x2(%rax),%ecx
```

## 03_zlib_deflate/no_retpoline/all_pgot: compress_block, 2353, pgot_length_code_all_pgot

```asm
    234a:	je     2282 <compress_block+0x42>
    2350:	mov    0x0(%rip),%rdx        # 2357 <compress_block+0x117>
			2353: R_X86_64_PC32	pgot_length_code_all_pgot-0x4
    2357:	movzbl (%rdx,%rax,1),%eax
    235b:	mov    %r9d,%edx
    235e:	mov    %rax,%r15
    2361:	lea    0x404(%r8,%rax,4),%rax
    2369:	movzwl 0x2(%rax),%r10d
    236e:	movzwl (%rax),%eax
    2371:	sub    %r10d,%edx
    2374:	mov    %eax,%r11d
    2377:	cmp    %ecx,%edx
    2379:	jge    26cd <compress_block+0x48d>
    237f:	cmp    $0x1f,%ecx
    2382:	ja     2388 <compress_block+0x148>
			2384: R_X86_64_PC32	.text.unlikely+0x964
    2388:	movslq 0x28(%rbx),%rdx
    238c:	mov    %eax,%edi
    238e:	mov    0x10(%rbx),%rsi
```

## 03_zlib_deflate/no_retpoline/all_pgot: compress_block, 23f5, pgot_extra_lbits_all_pgot

```asm
    23eb:	mov    %ax,0x1720(%rbx)
    23f2:	mov    0x0(%rip),%rax        # 23f9 <compress_block+0x1b9>
			23f5: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
    23f9:	mov    %ecx,0x1724(%rbx)
    23ff:	mov    (%rax,%r15,4),%eax
    2403:	test   %eax,%eax
    2405:	je     24a2 <compress_block+0x262>
    240b:	mov    0x0(%rip),%rsi        # 2412 <compress_block+0x1d2>
			240e: R_X86_64_PC32	pgot_base_length_all_pgot-0x4
    2412:	sub    (%rsi,%r15,4),%r13d
    2416:	mov    %r9d,%esi
    2419:	sub    %eax,%esi
    241b:	cmp    %ecx,%esi
    241d:	jge    2770 <compress_block+0x530>
    2423:	cmp    $0x1f,%edx
    2426:	ja     242c <compress_block+0x1ec>
			2428: R_X86_64_PC32	.text.unlikely+0x8f1
    242c:	movslq 0x28(%rbx),%rdx
    2430:	mov    %r13d,%edi
```

## 03_zlib_deflate/no_retpoline/all_pgot: compress_block, 240e, pgot_base_length_all_pgot

```asm
    2405:	je     24a2 <compress_block+0x262>
    240b:	mov    0x0(%rip),%rsi        # 2412 <compress_block+0x1d2>
			240e: R_X86_64_PC32	pgot_base_length_all_pgot-0x4
    2412:	sub    (%rsi,%r15,4),%r13d
    2416:	mov    %r9d,%esi
    2419:	sub    %eax,%esi
    241b:	cmp    %ecx,%esi
    241d:	jge    2770 <compress_block+0x530>
    2423:	cmp    $0x1f,%edx
    2426:	ja     242c <compress_block+0x1ec>
			2428: R_X86_64_PC32	.text.unlikely+0x8f1
    242c:	movslq 0x28(%rbx),%rdx
    2430:	mov    %r13d,%edi
    2433:	mov    0x10(%rbx),%rsi
    2437:	movzwl %r13w,%r13d
    243b:	shl    %cl,%edi
    243d:	mov    %edi,%ecx
    243f:	lea    0x1(%rdx),%edi
    2442:	or     0x1720(%rbx),%cx
```

## 03_zlib_deflate/no_retpoline/all_pgot: compress_block, 24a9, pgot_dist_code_all_pgot

```asm
    24a2:	sub    $0x1,%r12d
    24a6:	mov    0x0(%rip),%rsi        # 24ad <compress_block+0x26d>
			24a9: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    24ad:	cmp    $0xff,%r12d
    24b4:	ja     270c <compress_block+0x4cc>
    24ba:	mov    %r12d,%eax
    24bd:	movzbl (%rsi,%rax,1),%r13d
    24c2:	mov    -0x30(%rbp),%rax
    24c6:	lea    (%rax,%r13,4),%rsi
    24ca:	movzwl 0x2(%rsi),%eax
    24ce:	movzwl (%rsi),%r15d
    24d2:	mov    %r9d,%esi
    24d5:	sub    %eax,%esi
    24d7:	mov    %r15d,%r10d
    24da:	cmp    %ecx,%esi
    24dc:	jge    26ec <compress_block+0x4ac>
    24e2:	cmp    $0x1f,%edx
    24e5:	ja     24eb <compress_block+0x2ab>
			24e7: R_X86_64_PC32	.text.unlikely+0x87e
```

## 03_zlib_deflate/no_retpoline/all_pgot: compress_block, 2552, pgot_extra_dbits_all_pgot

```asm
    254d:	mov    %eax,%ecx
    254f:	mov    0x0(%rip),%rdx        # 2556 <compress_block+0x316>
			2552: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    2556:	mov    %r15w,0x1720(%rbx)
    255e:	mov    %ecx,0x1724(%rbx)
    2564:	mov    (%rdx,%r13,4),%r15d
    2568:	test   %r15d,%r15d
    256b:	je     2319 <compress_block+0xd9>
    2571:	mov    0x0(%rip),%rdx        # 2578 <compress_block+0x338>
			2574: R_X86_64_PC32	pgot_base_dist_all_pgot-0x4
    2578:	sub    (%rdx,%r13,4),%r12d
    257c:	mov    %r9d,%edx
    257f:	sub    %r15d,%edx
    2582:	cmp    %ecx,%edx
    2584:	jge    2749 <compress_block+0x509>
    258a:	cmp    $0x1f,%eax
    258d:	ja     2593 <compress_block+0x353>
			258f: R_X86_64_PC32	.text.unlikely+0x816
    2593:	movslq 0x28(%rbx),%rax
```

## 03_zlib_deflate/no_retpoline/all_pgot: compress_block, 2574, pgot_base_dist_all_pgot

```asm
    256b:	je     2319 <compress_block+0xd9>
    2571:	mov    0x0(%rip),%rdx        # 2578 <compress_block+0x338>
			2574: R_X86_64_PC32	pgot_base_dist_all_pgot-0x4
    2578:	sub    (%rdx,%r13,4),%r12d
    257c:	mov    %r9d,%edx
    257f:	sub    %r15d,%edx
    2582:	cmp    %ecx,%edx
    2584:	jge    2749 <compress_block+0x509>
    258a:	cmp    $0x1f,%eax
    258d:	ja     2593 <compress_block+0x353>
			258f: R_X86_64_PC32	.text.unlikely+0x816
    2593:	movslq 0x28(%rbx),%rax
    2597:	mov    %r12d,%edx
    259a:	movzwl %r12w,%r12d
    259e:	shl    %cl,%edx
    25a0:	mov    0x10(%rbx),%rcx
    25a4:	or     0x1720(%rbx),%dx
    25ab:	lea    0x1(%rax),%esi
    25ae:	mov    %dx,0x1720(%rbx)
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 28d7, pgot_base_length_all_pgot

```asm
    28ce:	mov    $0x1,%r9d
    28d4:	mov    0x0(%rip),%rax        # 28db <pgot_zlib_tr_init_all_pgot+0x4b>
			28d7: R_X86_64_PC32	pgot_base_length_all_pgot-0x4
    28db:	lea    0x0(,%r14,4),%r8
    28e3:	xor    %ebx,%ebx
    28e5:	mov    %r15d,(%rax,%r14,4)
    28e9:	jmp    28fc <pgot_zlib_tr_init_all_pgot+0x6c>
    28eb:	mov    0x0(%rip),%rax        # 28f2 <pgot_zlib_tr_init_all_pgot+0x62>
			28ee: R_X86_64_PC32	pgot_length_code_all_pgot-0x4
    28f2:	movslq %r12d,%r12
    28f5:	add    $0x1,%ebx
    28f8:	mov    %r14b,(%rax,%r12,1)
    28fc:	mov    0x0(%rip),%rax        # 2903 <pgot_zlib_tr_init_all_pgot+0x73>
			28ff: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
    2903:	lea    (%rbx,%r15,1),%r12d
    2907:	mov    (%rax,%r8,1),%ecx
    290b:	cmp    $0x1f,%ecx
    290e:	ja     2914 <pgot_zlib_tr_init_all_pgot+0x84>
			2910: R_X86_64_PC32	.text.unlikely+0xa0a
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 28ee, pgot_length_code_all_pgot

```asm
    28e9:	jmp    28fc <pgot_zlib_tr_init_all_pgot+0x6c>
    28eb:	mov    0x0(%rip),%rax        # 28f2 <pgot_zlib_tr_init_all_pgot+0x62>
			28ee: R_X86_64_PC32	pgot_length_code_all_pgot-0x4
    28f2:	movslq %r12d,%r12
    28f5:	add    $0x1,%ebx
    28f8:	mov    %r14b,(%rax,%r12,1)
    28fc:	mov    0x0(%rip),%rax        # 2903 <pgot_zlib_tr_init_all_pgot+0x73>
			28ff: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
    2903:	lea    (%rbx,%r15,1),%r12d
    2907:	mov    (%rax,%r8,1),%ecx
    290b:	cmp    $0x1f,%ecx
    290e:	ja     2914 <pgot_zlib_tr_init_all_pgot+0x84>
			2910: R_X86_64_PC32	.text.unlikely+0xa0a
    2914:	mov    %r9d,%eax
    2917:	shl    %cl,%eax
    2919:	cmp    %eax,%ebx
    291b:	jl     28eb <pgot_zlib_tr_init_all_pgot+0x5b>
    291d:	add    $0x1,%r14
    2921:	cmp    $0x1c,%r14
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 28ff, pgot_extra_lbits_all_pgot

```asm
    28f8:	mov    %r14b,(%rax,%r12,1)
    28fc:	mov    0x0(%rip),%rax        # 2903 <pgot_zlib_tr_init_all_pgot+0x73>
			28ff: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
    2903:	lea    (%rbx,%r15,1),%r12d
    2907:	mov    (%rax,%r8,1),%ecx
    290b:	cmp    $0x1f,%ecx
    290e:	ja     2914 <pgot_zlib_tr_init_all_pgot+0x84>
			2910: R_X86_64_PC32	.text.unlikely+0xa0a
    2914:	mov    %r9d,%eax
    2917:	shl    %cl,%eax
    2919:	cmp    %eax,%ebx
    291b:	jl     28eb <pgot_zlib_tr_init_all_pgot+0x5b>
    291d:	add    $0x1,%r14
    2921:	cmp    $0x1c,%r14
    2925:	je     2c1f <pgot_zlib_tr_init_all_pgot+0x38f>
    292b:	mov    %r12d,%r15d
    292e:	jmp    28d4 <pgot_zlib_tr_init_all_pgot+0x44>
    2930:	sar    $0x7,%r12d
    2934:	mov    $0x40,%r14d
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2949, pgot_base_dist_all_pgot

```asm
    2940:	mov    $0x1,%r8d
    2946:	mov    0x0(%rip),%rax        # 294d <pgot_zlib_tr_init_all_pgot+0xbd>
			2949: R_X86_64_PC32	pgot_base_dist_all_pgot-0x4
    294d:	mov    %r12d,%edx
    2950:	mov    %r12d,%ebx
    2953:	shl    $0x7,%edx
    2956:	mov    %edx,(%rax,%r14,1)
    295a:	mov    %r12d,%eax
    295d:	jmp    2975 <pgot_zlib_tr_init_all_pgot+0xe5>
    295f:	mov    0x0(%rip),%rdx        # 2966 <pgot_zlib_tr_init_all_pgot+0xd6>
			2962: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    2966:	add    $0x100,%ebx
    296c:	movslq %ebx,%rbx
    296f:	mov    %r15b,(%rdx,%rbx,1)
    2973:	mov    %esi,%ebx
    2975:	mov    0x0(%rip),%rdx        # 297c <pgot_zlib_tr_init_all_pgot+0xec>
			2978: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    297c:	mov    %ebx,%r12d
    297f:	mov    (%rdx,%r14,1),%ecx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2962, pgot_dist_code_all_pgot

```asm
    295d:	jmp    2975 <pgot_zlib_tr_init_all_pgot+0xe5>
    295f:	mov    0x0(%rip),%rdx        # 2966 <pgot_zlib_tr_init_all_pgot+0xd6>
			2962: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    2966:	add    $0x100,%ebx
    296c:	movslq %ebx,%rbx
    296f:	mov    %r15b,(%rdx,%rbx,1)
    2973:	mov    %esi,%ebx
    2975:	mov    0x0(%rip),%rdx        # 297c <pgot_zlib_tr_init_all_pgot+0xec>
			2978: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    297c:	mov    %ebx,%r12d
    297f:	mov    (%rdx,%r14,1),%ecx
    2983:	sub    $0x7,%ecx
    2986:	cmp    $0x1f,%ecx
    2989:	ja     298f <pgot_zlib_tr_init_all_pgot+0xff>
			298b: R_X86_64_PC32	.text.unlikely+0xa3c
    298f:	mov    %r8d,%edi
    2992:	mov    %ebx,%edx
    2994:	lea    0x1(%rbx),%esi
    2997:	shl    %cl,%edi
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2978, pgot_extra_dbits_all_pgot

```asm
    2973:	mov    %esi,%ebx
    2975:	mov    0x0(%rip),%rdx        # 297c <pgot_zlib_tr_init_all_pgot+0xec>
			2978: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    297c:	mov    %ebx,%r12d
    297f:	mov    (%rdx,%r14,1),%ecx
    2983:	sub    $0x7,%ecx
    2986:	cmp    $0x1f,%ecx
    2989:	ja     298f <pgot_zlib_tr_init_all_pgot+0xff>
			298b: R_X86_64_PC32	.text.unlikely+0xa3c
    298f:	mov    %r8d,%edi
    2992:	mov    %ebx,%edx
    2994:	lea    0x1(%rbx),%esi
    2997:	shl    %cl,%edi
    2999:	sub    %eax,%edx
    299b:	cmp    %edx,%edi
    299d:	jg     295f <pgot_zlib_tr_init_all_pgot+0xcf>
    299f:	add    $0x1,%r15d
    29a3:	add    $0x4,%r14
    29a7:	cmp    $0x1e,%r15d
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 29d8, pgot_static_ltree_all_pgot

```asm
    29d3:	xor    %eax,%eax
    29d5:	mov    0x0(%rip),%rdx        # 29dc <pgot_zlib_tr_init_all_pgot+0x14c>
			29d8: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    29dc:	mov    $0x8,%ebx
    29e1:	mov    %bx,0x2(%rdx,%rax,1)
    29e6:	add    $0x4,%rax
    29ea:	cmp    $0x240,%rax
    29f0:	jne    29d5 <pgot_zlib_tr_init_all_pgot+0x145>
    29f2:	movzwl -0x3e(%rbp),%esi
    29f6:	mov    0x0(%rip),%rdx        # 29fd <pgot_zlib_tr_init_all_pgot+0x16d>
			29f9: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    29fd:	mov    $0x9,%r11d
    2a03:	mov    %r11w,0x2(%rdx,%rax,1)
    2a09:	add    $0x4,%rax
    2a0d:	cmp    $0x400,%rax
    2a13:	jne    29f6 <pgot_zlib_tr_init_all_pgot+0x166>
    2a15:	lea    0x70(%rsi),%edx
    2a18:	movzwl -0x42(%rbp),%esi
    2a1c:	mov    %dx,-0x3e(%rbp)
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 29f9, pgot_static_ltree_all_pgot

```asm
    29f2:	movzwl -0x3e(%rbp),%esi
    29f6:	mov    0x0(%rip),%rdx        # 29fd <pgot_zlib_tr_init_all_pgot+0x16d>
			29f9: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    29fd:	mov    $0x9,%r11d
    2a03:	mov    %r11w,0x2(%rdx,%rax,1)
    2a09:	add    $0x4,%rax
    2a0d:	cmp    $0x400,%rax
    2a13:	jne    29f6 <pgot_zlib_tr_init_all_pgot+0x166>
    2a15:	lea    0x70(%rsi),%edx
    2a18:	movzwl -0x42(%rbp),%esi
    2a1c:	mov    %dx,-0x3e(%rbp)
    2a20:	mov    0x0(%rip),%rdx        # 2a27 <pgot_zlib_tr_init_all_pgot+0x197>
			2a23: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a27:	mov    $0x7,%r10d
    2a2d:	mov    %r10w,0x2(%rdx,%rax,1)
    2a33:	add    $0x4,%rax
    2a37:	cmp    $0x460,%rax
    2a3d:	jne    2a20 <pgot_zlib_tr_init_all_pgot+0x190>
    2a3f:	lea    0x18(%rsi),%edx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2a23, pgot_static_ltree_all_pgot

```asm
    2a1c:	mov    %dx,-0x3e(%rbp)
    2a20:	mov    0x0(%rip),%rdx        # 2a27 <pgot_zlib_tr_init_all_pgot+0x197>
			2a23: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a27:	mov    $0x7,%r10d
    2a2d:	mov    %r10w,0x2(%rdx,%rax,1)
    2a33:	add    $0x4,%rax
    2a37:	cmp    $0x460,%rax
    2a3d:	jne    2a20 <pgot_zlib_tr_init_all_pgot+0x190>
    2a3f:	lea    0x18(%rsi),%edx
    2a42:	mov    %dx,-0x42(%rbp)
    2a46:	mov    0x0(%rip),%rdx        # 2a4d <pgot_zlib_tr_init_all_pgot+0x1bd>
			2a49: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a4d:	mov    $0x8,%r9d
    2a53:	mov    %r9w,0x2(%rdx,%rax,1)
    2a59:	add    $0x4,%rax
    2a5d:	cmp    $0x480,%rax
    2a63:	jne    2a46 <pgot_zlib_tr_init_all_pgot+0x1b6>
    2a65:	mov    0x0(%rip),%rdi        # 2a6c <pgot_zlib_tr_init_all_pgot+0x1dc>
			2a68: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2a49, pgot_static_ltree_all_pgot

```asm
    2a42:	mov    %dx,-0x42(%rbp)
    2a46:	mov    0x0(%rip),%rdx        # 2a4d <pgot_zlib_tr_init_all_pgot+0x1bd>
			2a49: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a4d:	mov    $0x8,%r9d
    2a53:	mov    %r9w,0x2(%rdx,%rax,1)
    2a59:	add    $0x4,%rax
    2a5d:	cmp    $0x480,%rax
    2a63:	jne    2a46 <pgot_zlib_tr_init_all_pgot+0x1b6>
    2a65:	mov    0x0(%rip),%rdi        # 2a6c <pgot_zlib_tr_init_all_pgot+0x1dc>
			2a68: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a6c:	lea    -0x50(%rbp),%rdx
    2a70:	mov    $0x11f,%esi
    2a75:	xor    %ebx,%ebx
    2a77:	lea    0x98(%rcx),%eax
    2a7d:	mov    %ax,-0x40(%rbp)
    2a81:	call   df0 <gen_codes>
    2a86:	mov    0x0(%rip),%rax        # 2a8d <pgot_zlib_tr_init_all_pgot+0x1fd>
			2a89: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    2a8d:	lea    0x0(,%rbx,4),%r12
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2a68, pgot_static_ltree_all_pgot

```asm
    2a63:	jne    2a46 <pgot_zlib_tr_init_all_pgot+0x1b6>
    2a65:	mov    0x0(%rip),%rdi        # 2a6c <pgot_zlib_tr_init_all_pgot+0x1dc>
			2a68: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a6c:	lea    -0x50(%rbp),%rdx
    2a70:	mov    $0x11f,%esi
    2a75:	xor    %ebx,%ebx
    2a77:	lea    0x98(%rcx),%eax
    2a7d:	mov    %ax,-0x40(%rbp)
    2a81:	call   df0 <gen_codes>
    2a86:	mov    0x0(%rip),%rax        # 2a8d <pgot_zlib_tr_init_all_pgot+0x1fd>
			2a89: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    2a8d:	lea    0x0(,%rbx,4),%r12
    2a95:	mov    $0x5,%r8d
    2a9b:	movslq %ebx,%rsi
    2a9e:	mov    %r8w,0x2(%rax,%r12,1)
    2aa4:	cmp    $0xff,%rsi
    2aab:	ja     2caa <pgot_zlib_tr_init_all_pgot+0x41a>
    2ab1:	movzbl 0x0(%rbx),%eax
			2ab4: R_X86_64_32S	byte_rev_table
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2a89, pgot_static_dtree_all_pgot

```asm
    2a81:	call   df0 <gen_codes>
    2a86:	mov    0x0(%rip),%rax        # 2a8d <pgot_zlib_tr_init_all_pgot+0x1fd>
			2a89: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    2a8d:	lea    0x0(,%rbx,4),%r12
    2a95:	mov    $0x5,%r8d
    2a9b:	movslq %ebx,%rsi
    2a9e:	mov    %r8w,0x2(%rax,%r12,1)
    2aa4:	cmp    $0xff,%rsi
    2aab:	ja     2caa <pgot_zlib_tr_init_all_pgot+0x41a>
    2ab1:	movzbl 0x0(%rbx),%eax
			2ab4: R_X86_64_32S	byte_rev_table
    2ab8:	mov    0x0(%rip),%rdx        # 2abf <pgot_zlib_tr_init_all_pgot+0x22f>
			2abb: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    2abf:	add    $0x1,%rbx
    2ac3:	shr    $0x3,%eax
    2ac6:	mov    %ax,(%rdx,%r12,1)
    2acb:	cmp    $0x1e,%rbx
    2acf:	jne    2a86 <pgot_zlib_tr_init_all_pgot+0x1f6>
    2ad1:	movl   $0x1,0x0(%rip)        # 2adb <pgot_zlib_tr_init_all_pgot+0x24b>
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2abb, pgot_static_dtree_all_pgot

```asm
			2ab4: R_X86_64_32S	byte_rev_table
    2ab8:	mov    0x0(%rip),%rdx        # 2abf <pgot_zlib_tr_init_all_pgot+0x22f>
			2abb: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    2abf:	add    $0x1,%rbx
    2ac3:	shr    $0x3,%eax
    2ac6:	mov    %ax,(%rdx,%r12,1)
    2acb:	cmp    $0x1e,%rbx
    2acf:	jne    2a86 <pgot_zlib_tr_init_all_pgot+0x1f6>
    2ad1:	movl   $0x1,0x0(%rip)        # 2adb <pgot_zlib_tr_init_all_pgot+0x24b>
			2ad3: R_X86_64_PC32	.bss-0x8
    2adb:	lea    0xbc(%r13),%rax
    2ae2:	xor    %edi,%edi
    2ae4:	xor    %ebx,%ebx
    2ae6:	movq   $0x0,0x1710(%r13)
    2af1:	mov    %rax,0xb40(%r13)
    2af8:	lea    0x9b0(%r13),%rax
    2aff:	mov    %rax,0xb58(%r13)
    2b06:	lea    0xaa4(%r13),%rax
    2b0d:	movq   $0x0,0xb50(%r13)
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2c22, pgot_length_code_all_pgot

```asm
    2c1e:	int3   
    2c1f:	mov    0x0(%rip),%rdx        # 2c26 <pgot_zlib_tr_init_all_pgot+0x396>
			2c22: R_X86_64_PC32	pgot_length_code_all_pgot-0x4
    2c26:	lea    -0x1(%r12),%eax
    2c2b:	xor    %r15d,%r15d
    2c2e:	xor    %r14d,%r14d
    2c31:	cltq   
    2c33:	mov    $0x1,%r9d
    2c39:	movb   $0x1c,(%rdx,%rax,1)
    2c3d:	mov    0x0(%rip),%rax        # 2c44 <pgot_zlib_tr_init_all_pgot+0x3b4>
			2c40: R_X86_64_PC32	pgot_base_dist_all_pgot-0x4
    2c44:	lea    0x0(,%r14,4),%r8
    2c4c:	xor    %ebx,%ebx
    2c4e:	mov    %r15d,(%rax,%r14,4)
    2c52:	jmp    2c65 <pgot_zlib_tr_init_all_pgot+0x3d5>
    2c54:	mov    0x0(%rip),%rax        # 2c5b <pgot_zlib_tr_init_all_pgot+0x3cb>
			2c57: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    2c5b:	movslq %r12d,%r12
    2c5e:	add    $0x1,%ebx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2c40, pgot_base_dist_all_pgot

```asm
    2c39:	movb   $0x1c,(%rdx,%rax,1)
    2c3d:	mov    0x0(%rip),%rax        # 2c44 <pgot_zlib_tr_init_all_pgot+0x3b4>
			2c40: R_X86_64_PC32	pgot_base_dist_all_pgot-0x4
    2c44:	lea    0x0(,%r14,4),%r8
    2c4c:	xor    %ebx,%ebx
    2c4e:	mov    %r15d,(%rax,%r14,4)
    2c52:	jmp    2c65 <pgot_zlib_tr_init_all_pgot+0x3d5>
    2c54:	mov    0x0(%rip),%rax        # 2c5b <pgot_zlib_tr_init_all_pgot+0x3cb>
			2c57: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    2c5b:	movslq %r12d,%r12
    2c5e:	add    $0x1,%ebx
    2c61:	mov    %r14b,(%rax,%r12,1)
    2c65:	mov    0x0(%rip),%rax        # 2c6c <pgot_zlib_tr_init_all_pgot+0x3dc>
			2c68: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    2c6c:	lea    (%rbx,%r15,1),%r12d
    2c70:	mov    (%rax,%r8,1),%ecx
    2c74:	cmp    $0x1f,%ecx
    2c77:	ja     2c7d <pgot_zlib_tr_init_all_pgot+0x3ed>
			2c79: R_X86_64_PC32	.text.unlikely+0x9d8
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2c57, pgot_dist_code_all_pgot

```asm
    2c52:	jmp    2c65 <pgot_zlib_tr_init_all_pgot+0x3d5>
    2c54:	mov    0x0(%rip),%rax        # 2c5b <pgot_zlib_tr_init_all_pgot+0x3cb>
			2c57: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    2c5b:	movslq %r12d,%r12
    2c5e:	add    $0x1,%ebx
    2c61:	mov    %r14b,(%rax,%r12,1)
    2c65:	mov    0x0(%rip),%rax        # 2c6c <pgot_zlib_tr_init_all_pgot+0x3dc>
			2c68: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    2c6c:	lea    (%rbx,%r15,1),%r12d
    2c70:	mov    (%rax,%r8,1),%ecx
    2c74:	cmp    $0x1f,%ecx
    2c77:	ja     2c7d <pgot_zlib_tr_init_all_pgot+0x3ed>
			2c79: R_X86_64_PC32	.text.unlikely+0x9d8
    2c7d:	mov    %r9d,%eax
    2c80:	shl    %cl,%eax
    2c82:	cmp    %eax,%ebx
    2c84:	jl     2c54 <pgot_zlib_tr_init_all_pgot+0x3c4>
    2c86:	add    $0x1,%r14
    2c8a:	cmp    $0x10,%r14
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2c68, pgot_extra_dbits_all_pgot

```asm
    2c61:	mov    %r14b,(%rax,%r12,1)
    2c65:	mov    0x0(%rip),%rax        # 2c6c <pgot_zlib_tr_init_all_pgot+0x3dc>
			2c68: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    2c6c:	lea    (%rbx,%r15,1),%r12d
    2c70:	mov    (%rax,%r8,1),%ecx
    2c74:	cmp    $0x1f,%ecx
    2c77:	ja     2c7d <pgot_zlib_tr_init_all_pgot+0x3ed>
			2c79: R_X86_64_PC32	.text.unlikely+0x9d8
    2c7d:	mov    %r9d,%eax
    2c80:	shl    %cl,%eax
    2c82:	cmp    %eax,%ebx
    2c84:	jl     2c54 <pgot_zlib_tr_init_all_pgot+0x3c4>
    2c86:	add    $0x1,%r14
    2c8a:	cmp    $0x10,%r14
    2c8e:	je     2930 <pgot_zlib_tr_init_all_pgot+0xa0>
    2c94:	mov    %r12d,%r15d
    2c97:	jmp    2c3d <pgot_zlib_tr_init_all_pgot+0x3ad>
    2c99:	mov    $0x0,%rdi
			2c9c: R_X86_64_32S	.data+0x200
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_deflateReset_all_pgot, 2da7, pgot_memset_table_all_pgot

```asm
    2da1:	lea    -0x1(%rax),%edx
    2da4:	mov    0x0(%rip),%rax        # 2dab <pgot_zlib_deflateReset_all_pgot+0xab>
			2da7: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    2dab:	add    %rdx,%rdx
    2dae:	call   *%rax
    2db0:	movslq 0xac(%rbx),%rax
    2db7:	shl    $0x4,%rax
    2dbb:	add    0x0(%rip),%rax        # 2dc2 <pgot_zlib_deflateReset_all_pgot+0xc2>
			2dbe: R_X86_64_PC32	pgot_configuration_table_all_pgot-0x4
    2dc2:	movzwl 0x2(%rax),%edx
    2dc6:	mov    %edx,0xa8(%rbx)
    2dcc:	movzwl (%rax),%edx
    2dcf:	mov    %edx,0xb4(%rbx)
    2dd5:	movzwl 0x4(%rax),%edx
    2dd9:	mov    %edx,0xb8(%rbx)
    2ddf:	movzwl 0x6(%rax),%eax
    2de3:	movq   $0x0,0x80(%rbx)
    2dee:	movl   $0x2,0x88(%rbx)
    2df8:	movq   $0x0,0x90(%rbx)
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_deflateReset_all_pgot, 2dbe, pgot_configuration_table_all_pgot

```asm
    2db7:	shl    $0x4,%rax
    2dbb:	add    0x0(%rip),%rax        # 2dc2 <pgot_zlib_deflateReset_all_pgot+0xc2>
			2dbe: R_X86_64_PC32	pgot_configuration_table_all_pgot-0x4
    2dc2:	movzwl 0x2(%rax),%edx
    2dc6:	mov    %edx,0xa8(%rbx)
    2dcc:	movzwl (%rax),%edx
    2dcf:	mov    %edx,0xb4(%rbx)
    2dd5:	movzwl 0x4(%rax),%edx
    2dd9:	mov    %edx,0xb8(%rbx)
    2ddf:	movzwl 0x6(%rax),%eax
    2de3:	movq   $0x0,0x80(%rbx)
    2dee:	movl   $0x2,0x88(%rbx)
    2df8:	movq   $0x0,0x90(%rbx)
    2e03:	movl   $0x0,0x68(%rbx)
    2e0a:	mov    %eax,0xa4(%rbx)
    2e10:	movabs $0x200000000,%rax
    2e1a:	mov    %rax,0x9c(%rbx)
    2e21:	xor    %eax,%eax
    2e23:	mov    -0x8(%rbp),%rbx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_stored_block_all_pgot, 316a, pgot_memcpy_table_all_pgot

```asm
    3163:	movslq 0x28(%rbx),%rdi
    3167:	mov    0x0(%rip),%rax        # 316e <pgot_zlib_tr_stored_block_all_pgot+0x17e>
			316a: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    316e:	add    0x10(%rbx),%rdi
    3172:	call   *%rax
    3174:	add    %r12d,0x28(%rbx)
    3178:	add    $0x8,%rsp
    317c:	pop    %rbx
    317d:	pop    %r12
    317f:	pop    %r13
    3181:	pop    %r14
    3183:	pop    %rbp
    3184:	ret    
    3185:	int3   
    3186:	cmp    $0x1f,%ecx
    3189:	ja     318f <pgot_zlib_tr_stored_block_all_pgot+0x19f>
			318b: R_X86_64_PC32	.text.unlikely+0xa6f
    318f:	mov    %ecx,%eax
    3191:	mov    %r13d,%edx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_align_all_pgot, 336d, pgot_static_ltree_all_pgot

```asm
    3363:	mov    %ax,0x1720(%rbx)
    336a:	mov    0x0(%rip),%rax        # 3371 <pgot_zlib_tr_align_all_pgot+0xa1>
			336d: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    3371:	mov    $0x10,%esi
    3376:	mov    %ecx,0x1724(%rbx)
    337c:	movzwl 0x402(%rax),%r12d
    3384:	movzwl 0x400(%rax),%eax
    338b:	sub    %r12d,%esi
    338e:	mov    %eax,%r13d
    3391:	cmp    %ecx,%esi
    3393:	jge    35de <pgot_zlib_tr_align_all_pgot+0x30e>
    3399:	cmp    $0x1f,%edx
    339c:	ja     33a2 <pgot_zlib_tr_align_all_pgot+0xd2>
			339e: R_X86_64_PC32	.text.unlikely+0xb94
    33a2:	movslq 0x28(%rbx),%rdx
    33a6:	mov    %eax,%edi
    33a8:	mov    0x10(%rbx),%rsi
    33ac:	shl    %cl,%edi
    33ae:	mov    %edi,%ecx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_align_all_pgot, 34ec, pgot_static_ltree_all_pgot

```asm
    34e2:	mov    %ax,0x1720(%rbx)
    34e9:	mov    0x0(%rip),%rsi        # 34f0 <pgot_zlib_tr_align_all_pgot+0x220>
			34ec: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    34f0:	mov    %ecx,0x1724(%rbx)
    34f6:	movzwl 0x402(%rsi),%eax
    34fd:	movzwl 0x400(%rsi),%r12d
    3505:	mov    $0x10,%esi
    350a:	sub    %eax,%esi
    350c:	mov    %r12d,%r13d
    350f:	cmp    %ecx,%esi
    3511:	jge    368a <pgot_zlib_tr_align_all_pgot+0x3ba>
    3517:	cmp    $0x1f,%edx
    351a:	ja     3520 <pgot_zlib_tr_align_all_pgot+0x250>
			351c: R_X86_64_PC32	.text.unlikely+0xc1e
    3520:	movslq 0x28(%rbx),%rdx
    3524:	mov    %r12d,%edi
    3527:	mov    0x10(%rbx),%rsi
    352b:	shl    %cl,%edi
    352d:	mov    %edi,%ecx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_deflate_all_pgot, 37cd, pgot_configuration_table_all_pgot

```asm
    37c6:	shl    $0x4,%rax
    37ca:	add    0x0(%rip),%rax        # 37d1 <pgot_zlib_deflate_all_pgot+0xd1>
			37cd: R_X86_64_PC32	pgot_configuration_table_all_pgot-0x4
    37d1:	mov    0x8(%rax),%rax
    37d5:	call   *%rax
    37d7:	lea    -0x2(%rax),%edx
    37da:	cmp    $0x1,%edx
    37dd:	jbe    390e <pgot_zlib_deflate_all_pgot+0x20e>
    37e3:	test   $0xfffffffd,%eax
    37e8:	je     391e <pgot_zlib_deflate_all_pgot+0x21e>
    37ee:	cmp    $0x1,%eax
    37f1:	jne    38b2 <pgot_zlib_deflate_all_pgot+0x1b2>
    37f7:	cmp    $0x1,%r13d
    37fb:	je     3c1b <pgot_zlib_deflate_all_pgot+0x51b>
    3801:	cmp    $0x2,%r13d
    3805:	je     3c0d <pgot_zlib_deflate_all_pgot+0x50d>
    380b:	mov    -0x30(%rbp),%rdi
    380f:	xor    %ecx,%ecx
    3811:	xor    %edx,%edx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_deflate_all_pgot, 3843, pgot_memset_table_all_pgot

```asm
    383d:	lea    -0x1(%rax),%edx
    3840:	mov    0x0(%rip),%rax        # 3847 <pgot_zlib_deflate_all_pgot+0x147>
			3843: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    3847:	add    %rdx,%rdx
    384a:	call   *%rax
    384c:	mov    0x38(%r12),%r15
    3851:	mov    0x20(%r12),%rax
    3856:	mov    0x28(%r15),%edx
    385a:	mov    %rdx,%r14
    385d:	cmp    %rax,%rdx
    3860:	cmova  %eax,%r14d
    3864:	test   %r14d,%r14d
    3867:	je     38ad <pgot_zlib_deflate_all_pgot+0x1ad>
    3869:	mov    0x18(%r12),%rdi
    386e:	mov    %r14d,%edx
    3871:	test   %rdi,%rdi
    3874:	je     388c <pgot_zlib_deflate_all_pgot+0x18c>
    3876:	mov    0x20(%r15),%rsi
    387a:	mov    %rdx,-0x38(%rbp)
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_deflate_all_pgot, 387f, memcpy

```asm
    387a:	mov    %rdx,-0x38(%rbp)
    387e:	call   3883 <pgot_zlib_deflate_all_pgot+0x183>
			387f: R_X86_64_PLT32	memcpy-0x4
    3883:	mov    -0x38(%rbp),%rdx
    3887:	add    %rdx,0x18(%r12)
    388c:	add    %rdx,0x20(%r15)
    3890:	add    %rdx,0x28(%r12)
    3895:	sub    %rdx,0x20(%r12)
    389a:	sub    %r14d,0x28(%r15)
    389e:	jne    38a8 <pgot_zlib_deflate_all_pgot+0x1a8>
    38a0:	mov    0x10(%r15),%rax
    38a4:	mov    %rax,0x20(%r15)
    38a8:	mov    0x20(%r12),%rax
    38ad:	test   %rax,%rax
    38b0:	je     3926 <pgot_zlib_deflate_all_pgot+0x226>
    38b2:	cmp    $0x5,%r13d
    38b6:	jne    3931 <pgot_zlib_deflate_all_pgot+0x231>
    38b8:	mov    -0x30(%rbp),%rdi
    38bc:	mov    $0x1,%eax
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_deflate_all_pgot, 3a28, memcpy

```asm
    3a23:	mov    %rdx,-0x38(%rbp)
    3a27:	call   3a2c <pgot_zlib_deflate_all_pgot+0x32c>
			3a28: R_X86_64_PLT32	memcpy-0x4
    3a2c:	mov    -0x38(%rbp),%rdx
    3a30:	add    %rdx,0x18(%r12)
    3a35:	add    %rdx,0x20(%r15)
    3a39:	add    %rdx,0x28(%r12)
    3a3e:	sub    %rdx,0x20(%r12)
    3a43:	sub    %r14d,0x28(%r15)
    3a47:	je     3b99 <pgot_zlib_deflate_all_pgot+0x499>
    3a4d:	mov    0x20(%r12),%rax
    3a52:	test   %rax,%rax
    3a55:	je     3926 <pgot_zlib_deflate_all_pgot+0x226>
    3a5b:	mov    -0x30(%rbp),%rdx
    3a5f:	mov    0x8(%r12),%rax
    3a64:	cmpl   $0x29a,0x8(%rdx)
    3a6b:	jne    3a9d <pgot_zlib_deflate_all_pgot+0x39d>
    3a6d:	test   %rax,%rax
    3a70:	je     38fa <pgot_zlib_deflate_all_pgot+0x1fa>
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_deflate_all_pgot, 3b4f, memcpy

```asm
    3b4b:	mov    %r15,%rdx
    3b4e:	call   3b53 <pgot_zlib_deflate_all_pgot+0x453>
			3b4f: R_X86_64_PLT32	memcpy-0x4
    3b53:	add    %r15,0x18(%r12)
    3b58:	add    %r15,0x20(%r14)
    3b5c:	add    %r15,0x28(%r12)
    3b61:	sub    %r15,0x20(%r12)
    3b66:	sub    %r13d,0x28(%r14)
    3b6a:	jne    3b74 <pgot_zlib_deflate_all_pgot+0x474>
    3b6c:	mov    0x10(%r14),%rax
    3b70:	mov    %rax,0x20(%r14)
    3b74:	mov    -0x30(%rbp),%rax
    3b78:	mov    0x28(%rax),%edx
    3b7b:	movl   $0xffffffff,0x2c(%rax)
    3b82:	xor    %eax,%eax
    3b84:	test   %edx,%edx
    3b86:	sete   %al
    3b89:	add    $0x10,%rsp
    3b8d:	pop    %rbx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_flush_block_all_pgot, 3ced, pgot_bl_order_all_pgot

```asm
    3ce5:	call   f50 <build_tree>
    3cea:	mov    0x0(%rip),%rcx        # 3cf1 <pgot_zlib_tr_flush_block_all_pgot+0xc1>
			3ced: R_X86_64_PC32	pgot_bl_order_all_pgot-0x4
    3cf1:	movzbl (%rcx,%rbx,1),%edx
    3cf5:	mov    %ebx,%eax
    3cf7:	cmp    $0x26,%rdx
    3cfb:	ja     45df <pgot_zlib_tr_flush_block_all_pgot+0x9af>
    3d01:	cmpw   $0x0,0xaa6(%r12,%rdx,4)
    3d0b:	jne    4356 <pgot_zlib_tr_flush_block_all_pgot+0x726>
    3d11:	sub    $0x1,%rbx
    3d15:	cmp    $0x2,%rbx
    3d19:	jne    3cf1 <pgot_zlib_tr_flush_block_all_pgot+0xc1>
    3d1b:	mov    $0x17,%edx
    3d20:	mov    $0x3,%ebx
    3d25:	mov    $0x2,%eax
    3d2a:	mov    0x1708(%r12),%rdi
    3d32:	add    0x1700(%r12),%rdx
    3d3a:	mov    %rdx,0x1700(%r12)
    3d42:	add    $0xa,%rdx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_flush_block_all_pgot, 40e3, pgot_bl_order_all_pgot

```asm
    40de:	je     4127 <pgot_zlib_tr_flush_block_all_pgot+0x4f7>
    40e0:	mov    0x0(%rip),%rdx        # 40e7 <pgot_zlib_tr_flush_block_all_pgot+0x4b7>
			40e3: R_X86_64_PC32	pgot_bl_order_all_pgot-0x4
    40e7:	movzbl (%rdx,%rbx,1),%edx
    40eb:	movslq %edx,%r15
    40ee:	cmp    $0xd,%ecx
    40f1:	jg     4037 <pgot_zlib_tr_flush_block_all_pgot+0x407>
    40f7:	cmp    $0x26,%dl
    40fa:	ja     45bf <pgot_zlib_tr_flush_block_all_pgot+0x98f>
    4100:	movzwl 0xaa6(%r12,%r15,4),%r15d
    4109:	cmp    $0x1f,%ecx
    410c:	ja     4112 <pgot_zlib_tr_flush_block_all_pgot+0x4e2>
			410e: R_X86_64_PC32	.text.unlikely+0xec6
    4112:	mov    %ecx,%esi
    4114:	mov    %r15d,%edx
    4117:	shl    %cl,%edx
    4119:	lea    0x3(%rsi),%ecx
    411c:	or     0x1720(%r12),%dx
    4125:	jmp    40c6 <pgot_zlib_tr_flush_block_all_pgot+0x496>
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_flush_block_all_pgot, 42b7, pgot_static_ltree_all_pgot

```asm
    42ab:	mov    %ax,0x1720(%r12)
    42b4:	mov    0x0(%rip),%rsi        # 42bb <pgot_zlib_tr_flush_block_all_pgot+0x68b>
			42b7: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    42bb:	mov    %r12,%rdi
    42be:	mov    %edx,0x1724(%r12)
    42c6:	mov    0x0(%rip),%rdx        # 42cd <pgot_zlib_tr_flush_block_all_pgot+0x69d>
			42c9: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    42cd:	call   2240 <compress_block>
    42d2:	mov    0x1708(%r12),%rax
    42da:	add    0x1710(%r12),%rax
    42e2:	add    $0x3,%rax
    42e6:	mov    %rax,0x1710(%r12)
    42ee:	jmp    4175 <pgot_zlib_tr_flush_block_all_pgot+0x545>
    42f3:	mov    0x1724(%r12),%eax
    42fb:	cmp    $0x8,%eax
    42fe:	jg     43f9 <pgot_zlib_tr_flush_block_all_pgot+0x7c9>
    4304:	test   %eax,%eax
    4306:	jle    4326 <pgot_zlib_tr_flush_block_all_pgot+0x6f6>
    4308:	movzwl 0x1720(%r12),%ecx
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_flush_block_all_pgot, 42c9, pgot_static_dtree_all_pgot

```asm
    42be:	mov    %edx,0x1724(%r12)
    42c6:	mov    0x0(%rip),%rdx        # 42cd <pgot_zlib_tr_flush_block_all_pgot+0x69d>
			42c9: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    42cd:	call   2240 <compress_block>
    42d2:	mov    0x1708(%r12),%rax
    42da:	add    0x1710(%r12),%rax
    42e2:	add    $0x3,%rax
    42e6:	mov    %rax,0x1710(%r12)
    42ee:	jmp    4175 <pgot_zlib_tr_flush_block_all_pgot+0x545>
    42f3:	mov    0x1724(%r12),%eax
    42fb:	cmp    $0x8,%eax
    42fe:	jg     43f9 <pgot_zlib_tr_flush_block_all_pgot+0x7c9>
    4304:	test   %eax,%eax
    4306:	jle    4326 <pgot_zlib_tr_flush_block_all_pgot+0x6f6>
    4308:	movzwl 0x1720(%r12),%ecx
    4311:	movslq 0x28(%r12),%rax
    4316:	mov    0x10(%r12),%rdx
    431b:	lea    0x1(%rax),%esi
    431e:	mov    %esi,0x28(%r12)
```

## 03_zlib_deflate/no_retpoline/all_pgot: deflate_stored, 46ed, memcpy

```asm
    46e8:	mov    %rdx,-0x30(%rbp)
    46ec:	call   46f1 <deflate_stored+0xd1>
			46ed: R_X86_64_PLT32	memcpy-0x4
    46f1:	mov    -0x30(%rbp),%rdx
    46f5:	add    %rdx,0x18(%r14)
    46f9:	add    %rdx,0x20(%r13)
    46fd:	add    %rdx,0x28(%r14)
    4701:	sub    %rdx,0x20(%r14)
    4705:	sub    %r15d,0x28(%r13)
    4709:	jne    4713 <deflate_stored+0xf3>
    470b:	mov    0x10(%r13),%rax
    470f:	mov    %rax,0x20(%r13)
    4713:	mov    (%rbx),%rax
    4716:	mov    0x20(%rax),%rax
    471a:	test   %rax,%rax
    471d:	je     48d3 <deflate_stored+0x2b3>
    4723:	mov    0x94(%rbx),%eax
    4729:	mov    0x80(%rbx),%rcx
    4730:	mov    0x38(%rbx),%edi
```

## 03_zlib_deflate/no_retpoline/all_pgot: deflate_stored, 47eb, memcpy

```asm
    47e6:	mov    %rdx,-0x30(%rbp)
    47ea:	call   47ef <deflate_stored+0x1cf>
			47eb: R_X86_64_PLT32	memcpy-0x4
    47ef:	mov    -0x30(%rbp),%rdx
    47f3:	add    %rdx,0x18(%r14)
    47f7:	mov    -0x40(%rbp),%rcx
    47fb:	add    %rdx,0x20(%rcx)
    47ff:	add    %rdx,0x28(%r14)
    4803:	sub    %rdx,0x20(%r14)
    4807:	sub    %r15d,0x28(%rcx)
    480b:	jne    4815 <deflate_stored+0x1f5>
    480d:	mov    0x10(%rcx),%rax
    4811:	mov    %rax,0x20(%rcx)
    4815:	mov    (%rbx),%rax
    4818:	mov    0x20(%rax),%rax
    481c:	test   %rax,%rax
    481f:	je     48ef <deflate_stored+0x2cf>
    4825:	xor    %eax,%eax
    4827:	cmpl   $0x5,-0x34(%rbp)
```

## 03_zlib_deflate/no_retpoline/all_pgot: deflate_stored, 48a1, memcpy

```asm
    489c:	mov    %rdx,-0x30(%rbp)
    48a0:	call   48a5 <deflate_stored+0x285>
			48a1: R_X86_64_PLT32	memcpy-0x4
    48a5:	mov    -0x30(%rbp),%rdx
    48a9:	add    %rdx,0x18(%r14)
    48ad:	mov    -0x40(%rbp),%rcx
    48b1:	add    %rdx,0x20(%rcx)
    48b5:	add    %rdx,0x28(%r14)
    48b9:	sub    %rdx,0x20(%r14)
    48bd:	sub    %r15d,0x28(%rcx)
    48c1:	je     48e5 <deflate_stored+0x2c5>
    48c3:	mov    (%rbx),%rax
    48c6:	mov    0x20(%rax),%rax
    48ca:	test   %rax,%rax
    48cd:	jne    4745 <deflate_stored+0x125>
    48d3:	xor    %eax,%eax
    48d5:	add    $0x18,%rsp
    48d9:	pop    %rbx
    48da:	pop    %r12
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_tally_all_pgot, 4987, pgot_extra_dbits_all_pgot

```asm
    4981:	mov    %r15d,%r13d
    4984:	mov    0x0(%rip),%r14        # 498b <pgot_zlib_tr_tally_all_pgot+0x8b>
			4987: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    498b:	xor    %ebx,%ebx
    498d:	mov    0x94(%r12),%ecx
    4995:	mov    0x80(%r12),%r8
    499d:	shl    $0x3,%r13
    49a1:	movslq %ebx,%rsi
    49a4:	cmp    $0x3c,%rsi
    49a8:	ja     4a97 <pgot_zlib_tr_tally_all_pgot+0x197>
    49ae:	movzwl 0x9b0(%r12,%rbx,4),%edx
    49b7:	movslq (%r14,%rbx,4),%rax
    49bb:	add    $0x1,%rbx
    49bf:	add    $0x5,%rax
    49c3:	imul   %rdx,%rax
    49c7:	add    %rax,%r13
    49ca:	cmp    $0x1e,%rbx
    49ce:	jne    49a1 <pgot_zlib_tr_tally_all_pgot+0xa1>
    49d0:	mov    %r15d,%eax
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_tally_all_pgot, 4a0a, pgot_length_code_all_pgot

```asm
    4a06:	int3   
    4a07:	mov    0x0(%rip),%rax        # 4a0e <pgot_zlib_tr_tally_all_pgot+0x10e>
			4a0a: R_X86_64_PC32	pgot_length_code_all_pgot-0x4
    4a0e:	mov    %edx,%edx
    4a10:	lea    -0x1(%rsi),%ebx
    4a13:	addl   $0x1,0x1718(%r12)
    4a1c:	movzbl (%rax,%rdx,1),%eax
    4a20:	lea    0x101(%rax),%r13
    4a27:	cmp    $0x23c,%r13
    4a2e:	ja     4ac7 <pgot_zlib_tr_tally_all_pgot+0x1c7>
    4a34:	addw   $0x1,0xbc(%r12,%r13,4)
    4a3e:	mov    0x0(%rip),%rdx        # 4a45 <pgot_zlib_tr_tally_all_pgot+0x145>
			4a41: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    4a45:	cmp    $0xff,%ebx
    4a4b:	jbe    4a72 <pgot_zlib_tr_tally_all_pgot+0x172>
    4a4d:	mov    %ebx,%esi
    4a4f:	shr    $0x7,%esi
    4a52:	lea    0x100(%rsi),%eax
    4a58:	movzbl (%rdx,%rax,1),%eax
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_tally_all_pgot, 4a41, pgot_dist_code_all_pgot

```asm
    4a34:	addw   $0x1,0xbc(%r12,%r13,4)
    4a3e:	mov    0x0(%rip),%rdx        # 4a45 <pgot_zlib_tr_tally_all_pgot+0x145>
			4a41: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    4a45:	cmp    $0xff,%ebx
    4a4b:	jbe    4a72 <pgot_zlib_tr_tally_all_pgot+0x172>
    4a4d:	mov    %ebx,%esi
    4a4f:	shr    $0x7,%esi
    4a52:	lea    0x100(%rsi),%eax
    4a58:	movzbl (%rdx,%rax,1),%eax
    4a5c:	movslq %eax,%rbx
    4a5f:	cmp    $0x3c,%al
    4a61:	ja     4ab6 <pgot_zlib_tr_tally_all_pgot+0x1b6>
    4a63:	addw   $0x1,0x9b0(%r12,%rbx,4)
    4a6d:	jmp    4965 <pgot_zlib_tr_tally_all_pgot+0x65>
    4a72:	mov    %ebx,%esi
    4a74:	movzbl (%rdx,%rsi,1),%eax
    4a78:	jmp    4a5c <pgot_zlib_tr_tally_all_pgot+0x15c>
    4a7a:	sub    %r8,%rcx
    4a7d:	shr    $0x3,%r13
```

## 03_zlib_deflate/no_retpoline/all_pgot: deflate_slow, 4d32, memcpy

```asm
    4d2d:	mov    %rdx,-0x30(%rbp)
    4d31:	call   4d36 <deflate_slow+0x246>
			4d32: R_X86_64_PLT32	memcpy-0x4
    4d36:	mov    -0x30(%rbp),%rdx
    4d3a:	add    %rdx,0x18(%r13)
    4d3e:	mov    -0x38(%rbp),%rcx
    4d42:	add    %rdx,0x20(%rcx)
    4d46:	add    %rdx,0x28(%r13)
    4d4a:	sub    %rdx,0x20(%r13)
    4d4e:	sub    %r15d,0x28(%rcx)
    4d52:	jne    4d5c <deflate_slow+0x26c>
    4d54:	mov    0x10(%rcx),%rax
    4d58:	mov    %rax,0x20(%rcx)
    4d5c:	mov    (%rbx),%rax
    4d5f:	mov    0x20(%rax),%rax
    4d63:	test   %rax,%rax
    4d66:	je     4ee6 <deflate_slow+0x3f6>
    4d6c:	mov    0x9c(%rbx),%eax
    4d72:	cmp    $0x105,%eax
```

## 03_zlib_deflate/no_retpoline/all_pgot: deflate_slow, 4e91, memcpy

```asm
    4e8c:	mov    %r8,-0x30(%rbp)
    4e90:	call   4e95 <deflate_slow+0x3a5>
			4e91: R_X86_64_PLT32	memcpy-0x4
    4e95:	add    %r13,0x18(%r15)
    4e99:	mov    -0x38(%rbp),%ecx
    4e9c:	mov    -0x30(%rbp),%r8
    4ea0:	add    %r13,0x20(%r8)
    4ea4:	add    %r13,0x28(%r15)
    4ea8:	sub    %r13,0x20(%r15)
    4eac:	sub    %ecx,0x28(%r8)
    4eb0:	jne    4eba <deflate_slow+0x3ca>
    4eb2:	mov    0x10(%r8),%rax
    4eb6:	mov    %rax,0x20(%r8)
    4eba:	mov    0x94(%rbx),%eax
    4ec0:	mov    (%rbx),%r15
    4ec3:	add    $0x1,%eax
    4ec6:	mov    %eax,0x94(%rbx)
    4ecc:	mov    0x9c(%rbx),%eax
    4ed2:	sub    $0x1,%eax
```

## 03_zlib_deflate/no_retpoline/all_pgot: deflate_slow, 4fd5, memcpy

```asm
    4fd0:	mov    %rdx,-0x30(%rbp)
    4fd4:	call   4fd9 <deflate_slow+0x4e9>
			4fd5: R_X86_64_PLT32	memcpy-0x4
    4fd9:	mov    -0x30(%rbp),%rdx
    4fdd:	add    %rdx,0x18(%r14)
    4fe1:	mov    -0x38(%rbp),%rcx
    4fe5:	add    %rdx,0x20(%rcx)
    4fe9:	add    %rdx,0x28(%r14)
    4fed:	sub    %rdx,0x20(%r14)
    4ff1:	sub    %r15d,0x28(%rcx)
    4ff5:	je     5020 <deflate_slow+0x530>
    4ff7:	mov    (%rbx),%rax
    4ffa:	mov    0x20(%rax),%rax
    4ffe:	test   %rax,%rax
    5001:	je     5054 <deflate_slow+0x564>
    5003:	xor    %eax,%eax
    5005:	cmp    $0x5,%r12d
    5009:	sete   %al
    500c:	add    $0x10,%rsp
```

## 03_zlib_deflate/no_retpoline/all_pgot: deflate_fast, 5234, memcpy

```asm
    522f:	mov    %rdx,-0x30(%rbp)
    5233:	call   5238 <deflate_fast+0x1c8>
			5234: R_X86_64_PLT32	memcpy-0x4
    5238:	mov    -0x30(%rbp),%rdx
    523c:	add    %rdx,0x18(%r13)
    5240:	add    %rdx,0x20(%r12)
    5245:	add    %rdx,0x28(%r13)
    5249:	sub    %rdx,0x20(%r13)
    524d:	sub    %r15d,0x28(%r12)
    5252:	jne    525e <deflate_fast+0x1ee>
    5254:	mov    0x10(%r12),%rax
    5259:	mov    %rax,0x20(%r12)
    525e:	mov    (%rbx),%rax
    5261:	mov    0x20(%rax),%rax
    5265:	test   %rax,%rax
    5268:	jne    508f <deflate_fast+0x1f>
    526e:	add    $0x18,%rsp
    5272:	xor    %eax,%eax
    5274:	pop    %rbx
```

## 03_zlib_deflate/no_retpoline/all_pgot: deflate_fast, 53d9, memcpy

```asm
    53d4:	mov    %rdx,-0x30(%rbp)
    53d8:	call   53dd <deflate_fast+0x36d>
			53d9: R_X86_64_PLT32	memcpy-0x4
    53dd:	mov    -0x30(%rbp),%rdx
    53e1:	add    %rdx,0x18(%r14)
    53e5:	mov    -0x40(%rbp),%rcx
    53e9:	add    %rdx,0x20(%rcx)
    53ed:	add    %rdx,0x28(%r14)
    53f1:	sub    %rdx,0x20(%r14)
    53f5:	sub    %r15d,0x28(%rcx)
    53f9:	je     5424 <deflate_fast+0x3b4>
    53fb:	mov    (%rbx),%rax
    53fe:	mov    0x20(%rax),%rax
    5402:	test   %rax,%rax
    5405:	je     542e <deflate_fast+0x3be>
    5407:	xor    %eax,%eax
    5409:	cmpl   $0x5,-0x34(%rbp)
    540d:	sete   %al
    5410:	add    $0x18,%rsp
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot.cold, 9f7, pgot_extra_dbits_all_pgot

```asm
			9f0: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     9f4:	mov    0x0(%rip),%rax        # 9fb <pgot_zlib_tr_init_all_pgot.cold+0x1f>
			9f7: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
     9fb:	mov    -0x58(%rbp),%r8
     9ff:	mov    $0x1,%r9d
     a05:	mov    (%rax,%r8,1),%ecx
     a09:	jmp    a0e <pgot_zlib_tr_init_all_pgot.cold+0x32>
			a0a: R_X86_64_PC32	.text+0x2c79
     a0e:	movslq %ecx,%rdx
     a11:	mov    $0x1,%esi
     a16:	mov    $0x0,%rdi
			a19: R_X86_64_32S	.data+0x13c0
     a1d:	mov    %r8,-0x58(%rbp)
     a21:	call   a26 <pgot_zlib_tr_init_all_pgot.cold+0x4a>
			a22: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a26:	mov    0x0(%rip),%rax        # a2d <pgot_zlib_tr_init_all_pgot.cold+0x51>
			a29: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
     a2d:	mov    -0x58(%rbp),%r8
     a31:	mov    $0x1,%r9d
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot.cold, a29, pgot_extra_lbits_all_pgot

```asm
			a22: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a26:	mov    0x0(%rip),%rax        # a2d <pgot_zlib_tr_init_all_pgot.cold+0x51>
			a29: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
     a2d:	mov    -0x58(%rbp),%r8
     a31:	mov    $0x1,%r9d
     a37:	mov    (%rax,%r8,1),%ecx
     a3b:	jmp    a40 <pgot_zlib_tr_init_all_pgot.cold+0x64>
			a3c: R_X86_64_PC32	.text+0x2910
     a40:	movslq %ecx,%rdx
     a43:	mov    $0x1,%esi
     a48:	mov    $0x0,%rdi
			a4b: R_X86_64_32S	.data+0x1380
     a4f:	mov    %eax,-0x58(%rbp)
     a52:	call   a57 <pgot_zlib_tr_init_all_pgot.cold+0x7b>
			a53: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a57:	mov    0x0(%rip),%rdx        # a5e <pgot_zlib_tr_init_all_pgot.cold+0x82>
			a5a: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
     a5e:	mov    -0x58(%rbp),%eax
     a61:	mov    $0x1,%r8d
```

## 03_zlib_deflate/no_retpoline/all_pgot: pgot_zlib_tr_init_all_pgot.cold, a5a, pgot_extra_dbits_all_pgot

```asm
			a53: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a57:	mov    0x0(%rip),%rdx        # a5e <pgot_zlib_tr_init_all_pgot.cold+0x82>
			a5a: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
     a5e:	mov    -0x58(%rbp),%eax
     a61:	mov    $0x1,%r8d
     a67:	mov    (%rdx,%r14,1),%ecx
     a6b:	sub    $0x7,%ecx
     a6e:	jmp    a73 <pgot_zlib_tr_stored_block_all_pgot.cold>
			a6f: R_X86_64_PC32	.text+0x298b

```

## 03_zlib_deflate/no_retpoline/data_pgot: compress_block, 1333, pgot_length_code_data_pgot

```asm
    132a:	je     1262 <compress_block+0x42>
    1330:	mov    0x0(%rip),%rdx        # 1337 <compress_block+0x117>
			1333: R_X86_64_PC32	pgot_length_code_data_pgot-0x4
    1337:	movzbl (%rdx,%rax,1),%eax
    133b:	mov    %r9d,%edx
    133e:	mov    %rax,%r15
    1341:	lea    0x404(%r8,%rax,4),%rax
    1349:	movzwl 0x2(%rax),%r10d
    134e:	movzwl (%rax),%eax
    1351:	sub    %r10d,%edx
    1354:	mov    %eax,%r11d
    1357:	cmp    %ecx,%edx
    1359:	jge    16ad <compress_block+0x48d>
    135f:	cmp    $0x1f,%ecx
    1362:	ja     1368 <compress_block+0x148>
			1364: R_X86_64_PC32	.text.unlikely+0x8ff
    1368:	movslq 0x28(%rbx),%rdx
    136c:	mov    %eax,%edi
    136e:	mov    0x10(%rbx),%rsi
```

## 03_zlib_deflate/no_retpoline/data_pgot: compress_block, 13d5, pgot_extra_lbits_data_pgot

```asm
    13cb:	mov    %ax,0x1720(%rbx)
    13d2:	mov    0x0(%rip),%rax        # 13d9 <compress_block+0x1b9>
			13d5: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
    13d9:	mov    %ecx,0x1724(%rbx)
    13df:	mov    (%rax,%r15,4),%eax
    13e3:	test   %eax,%eax
    13e5:	je     1482 <compress_block+0x262>
    13eb:	mov    0x0(%rip),%rsi        # 13f2 <compress_block+0x1d2>
			13ee: R_X86_64_PC32	pgot_base_length_data_pgot-0x4
    13f2:	sub    (%rsi,%r15,4),%r13d
    13f6:	mov    %r9d,%esi
    13f9:	sub    %eax,%esi
    13fb:	cmp    %ecx,%esi
    13fd:	jge    1750 <compress_block+0x530>
    1403:	cmp    $0x1f,%edx
    1406:	ja     140c <compress_block+0x1ec>
			1408: R_X86_64_PC32	.text.unlikely+0x88c
    140c:	movslq 0x28(%rbx),%rdx
    1410:	mov    %r13d,%edi
```

## 03_zlib_deflate/no_retpoline/data_pgot: compress_block, 13ee, pgot_base_length_data_pgot

```asm
    13e5:	je     1482 <compress_block+0x262>
    13eb:	mov    0x0(%rip),%rsi        # 13f2 <compress_block+0x1d2>
			13ee: R_X86_64_PC32	pgot_base_length_data_pgot-0x4
    13f2:	sub    (%rsi,%r15,4),%r13d
    13f6:	mov    %r9d,%esi
    13f9:	sub    %eax,%esi
    13fb:	cmp    %ecx,%esi
    13fd:	jge    1750 <compress_block+0x530>
    1403:	cmp    $0x1f,%edx
    1406:	ja     140c <compress_block+0x1ec>
			1408: R_X86_64_PC32	.text.unlikely+0x88c
    140c:	movslq 0x28(%rbx),%rdx
    1410:	mov    %r13d,%edi
    1413:	mov    0x10(%rbx),%rsi
    1417:	movzwl %r13w,%r13d
    141b:	shl    %cl,%edi
    141d:	mov    %edi,%ecx
    141f:	lea    0x1(%rdx),%edi
    1422:	or     0x1720(%rbx),%cx
```

## 03_zlib_deflate/no_retpoline/data_pgot: compress_block, 1489, pgot_dist_code_data_pgot

```asm
    1482:	sub    $0x1,%r12d
    1486:	mov    0x0(%rip),%rsi        # 148d <compress_block+0x26d>
			1489: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    148d:	cmp    $0xff,%r12d
    1494:	ja     16ec <compress_block+0x4cc>
    149a:	mov    %r12d,%eax
    149d:	movzbl (%rsi,%rax,1),%r13d
    14a2:	mov    -0x30(%rbp),%rax
    14a6:	lea    (%rax,%r13,4),%rsi
    14aa:	movzwl 0x2(%rsi),%eax
    14ae:	movzwl (%rsi),%r15d
    14b2:	mov    %r9d,%esi
    14b5:	sub    %eax,%esi
    14b7:	mov    %r15d,%r10d
    14ba:	cmp    %ecx,%esi
    14bc:	jge    16cc <compress_block+0x4ac>
    14c2:	cmp    $0x1f,%edx
    14c5:	ja     14cb <compress_block+0x2ab>
			14c7: R_X86_64_PC32	.text.unlikely+0x819
```

## 03_zlib_deflate/no_retpoline/data_pgot: compress_block, 1532, pgot_extra_dbits_data_pgot

```asm
    152d:	mov    %eax,%ecx
    152f:	mov    0x0(%rip),%rdx        # 1536 <compress_block+0x316>
			1532: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    1536:	mov    %r15w,0x1720(%rbx)
    153e:	mov    %ecx,0x1724(%rbx)
    1544:	mov    (%rdx,%r13,4),%r15d
    1548:	test   %r15d,%r15d
    154b:	je     12f9 <compress_block+0xd9>
    1551:	mov    0x0(%rip),%rdx        # 1558 <compress_block+0x338>
			1554: R_X86_64_PC32	pgot_base_dist_data_pgot-0x4
    1558:	sub    (%rdx,%r13,4),%r12d
    155c:	mov    %r9d,%edx
    155f:	sub    %r15d,%edx
    1562:	cmp    %ecx,%edx
    1564:	jge    1729 <compress_block+0x509>
    156a:	cmp    $0x1f,%eax
    156d:	ja     1573 <compress_block+0x353>
			156f: R_X86_64_PC32	.text.unlikely+0x7b1
    1573:	movslq 0x28(%rbx),%rax
```

## 03_zlib_deflate/no_retpoline/data_pgot: compress_block, 1554, pgot_base_dist_data_pgot

```asm
    154b:	je     12f9 <compress_block+0xd9>
    1551:	mov    0x0(%rip),%rdx        # 1558 <compress_block+0x338>
			1554: R_X86_64_PC32	pgot_base_dist_data_pgot-0x4
    1558:	sub    (%rdx,%r13,4),%r12d
    155c:	mov    %r9d,%edx
    155f:	sub    %r15d,%edx
    1562:	cmp    %ecx,%edx
    1564:	jge    1729 <compress_block+0x509>
    156a:	cmp    $0x1f,%eax
    156d:	ja     1573 <compress_block+0x353>
			156f: R_X86_64_PC32	.text.unlikely+0x7b1
    1573:	movslq 0x28(%rbx),%rax
    1577:	mov    %r12d,%edx
    157a:	movzwl %r12w,%r12d
    157e:	shl    %cl,%edx
    1580:	mov    0x10(%rbx),%rcx
    1584:	or     0x1720(%rbx),%dx
    158b:	lea    0x1(%rax),%esi
    158e:	mov    %dx,0x1720(%rbx)
```

## 03_zlib_deflate/no_retpoline/data_pgot: fill_window, 2446, memcpy

```asm
    2442:	add    %rax,%rdi
    2445:	call   244a <fill_window+0x10a>
			2446: R_X86_64_PLT32	memcpy-0x4
    244a:	mov    -0x70(%rbp),%rcx
    244e:	mov    -0x74(%rbp),%eax
    2451:	add    %rbx,(%rcx)
    2454:	add    %rbx,0x10(%rcx)
    2458:	mov    -0x58(%rbp),%rbx
    245c:	add    0x9c(%rbx),%eax
    2462:	mov    %eax,-0x5c(%rbp)
    2465:	mov    -0x58(%rbp),%rdi
    2469:	mov    -0x5c(%rbp),%eax
    246c:	mov    %eax,0x9c(%rdi)
    2472:	cmp    $0x2,%eax
    2475:	jbe    24bc <fill_window+0x17c>
    2477:	mov    0x94(%rdi),%ecx
    247d:	mov    0x48(%rdi),%rax
    2481:	mov    %rcx,%rdx
    2484:	movzbl (%rax,%rcx,1),%ebx
```

## 03_zlib_deflate/no_retpoline/data_pgot: fill_window, 26f1, memcpy

```asm
    26ed:	mov    %r15,%rdx
    26f0:	call   26f5 <fill_window+0x3b5>
			26f1: R_X86_64_PLT32	memcpy-0x4
    26f5:	mov    0x6c(%r14),%ecx
    26f9:	mov    0x60(%r14),%rax
    26fd:	xor    %esi,%esi
    26ff:	mov    -0x94(%rbp),%r8d
    2706:	sub    %r15,0x80(%r14)
    270d:	mov    %rcx,%rdx
    2710:	sub    %r8d,0x98(%r14)
    2717:	lea    (%rax,%rcx,2),%rax
    271b:	sub    %r8d,0x94(%r14)
    2722:	sub    $0x1,%edx
    2725:	not    %rdx
    2728:	lea    (%rax,%rdx,2),%rdi
    272c:	movzwl -0x2(%rax),%ecx
    2730:	sub    $0x2,%rax
    2734:	mov    %ecx,%edx
    2736:	sub    %r8d,%edx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 28d7, pgot_base_length_data_pgot

```asm
    28ce:	mov    $0x1,%r9d
    28d4:	mov    0x0(%rip),%rax        # 28db <pgot_zlib_tr_init_data_pgot+0x4b>
			28d7: R_X86_64_PC32	pgot_base_length_data_pgot-0x4
    28db:	lea    0x0(,%r14,4),%r8
    28e3:	xor    %ebx,%ebx
    28e5:	mov    %r15d,(%rax,%r14,4)
    28e9:	jmp    28fc <pgot_zlib_tr_init_data_pgot+0x6c>
    28eb:	mov    0x0(%rip),%rax        # 28f2 <pgot_zlib_tr_init_data_pgot+0x62>
			28ee: R_X86_64_PC32	pgot_length_code_data_pgot-0x4
    28f2:	movslq %r12d,%r12
    28f5:	add    $0x1,%ebx
    28f8:	mov    %r14b,(%rax,%r12,1)
    28fc:	mov    0x0(%rip),%rax        # 2903 <pgot_zlib_tr_init_data_pgot+0x73>
			28ff: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
    2903:	lea    (%rbx,%r15,1),%r12d
    2907:	mov    (%rax,%r8,1),%ecx
    290b:	cmp    $0x1f,%ecx
    290e:	ja     2914 <pgot_zlib_tr_init_data_pgot+0x84>
			2910: R_X86_64_PC32	.text.unlikely+0xa0a
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 28ee, pgot_length_code_data_pgot

```asm
    28e9:	jmp    28fc <pgot_zlib_tr_init_data_pgot+0x6c>
    28eb:	mov    0x0(%rip),%rax        # 28f2 <pgot_zlib_tr_init_data_pgot+0x62>
			28ee: R_X86_64_PC32	pgot_length_code_data_pgot-0x4
    28f2:	movslq %r12d,%r12
    28f5:	add    $0x1,%ebx
    28f8:	mov    %r14b,(%rax,%r12,1)
    28fc:	mov    0x0(%rip),%rax        # 2903 <pgot_zlib_tr_init_data_pgot+0x73>
			28ff: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
    2903:	lea    (%rbx,%r15,1),%r12d
    2907:	mov    (%rax,%r8,1),%ecx
    290b:	cmp    $0x1f,%ecx
    290e:	ja     2914 <pgot_zlib_tr_init_data_pgot+0x84>
			2910: R_X86_64_PC32	.text.unlikely+0xa0a
    2914:	mov    %r9d,%eax
    2917:	shl    %cl,%eax
    2919:	cmp    %eax,%ebx
    291b:	jl     28eb <pgot_zlib_tr_init_data_pgot+0x5b>
    291d:	add    $0x1,%r14
    2921:	cmp    $0x1c,%r14
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 28ff, pgot_extra_lbits_data_pgot

```asm
    28f8:	mov    %r14b,(%rax,%r12,1)
    28fc:	mov    0x0(%rip),%rax        # 2903 <pgot_zlib_tr_init_data_pgot+0x73>
			28ff: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
    2903:	lea    (%rbx,%r15,1),%r12d
    2907:	mov    (%rax,%r8,1),%ecx
    290b:	cmp    $0x1f,%ecx
    290e:	ja     2914 <pgot_zlib_tr_init_data_pgot+0x84>
			2910: R_X86_64_PC32	.text.unlikely+0xa0a
    2914:	mov    %r9d,%eax
    2917:	shl    %cl,%eax
    2919:	cmp    %eax,%ebx
    291b:	jl     28eb <pgot_zlib_tr_init_data_pgot+0x5b>
    291d:	add    $0x1,%r14
    2921:	cmp    $0x1c,%r14
    2925:	je     2c1f <pgot_zlib_tr_init_data_pgot+0x38f>
    292b:	mov    %r12d,%r15d
    292e:	jmp    28d4 <pgot_zlib_tr_init_data_pgot+0x44>
    2930:	sar    $0x7,%r12d
    2934:	mov    $0x40,%r14d
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2949, pgot_base_dist_data_pgot

```asm
    2940:	mov    $0x1,%r8d
    2946:	mov    0x0(%rip),%rax        # 294d <pgot_zlib_tr_init_data_pgot+0xbd>
			2949: R_X86_64_PC32	pgot_base_dist_data_pgot-0x4
    294d:	mov    %r12d,%edx
    2950:	mov    %r12d,%ebx
    2953:	shl    $0x7,%edx
    2956:	mov    %edx,(%rax,%r14,1)
    295a:	mov    %r12d,%eax
    295d:	jmp    2975 <pgot_zlib_tr_init_data_pgot+0xe5>
    295f:	mov    0x0(%rip),%rdx        # 2966 <pgot_zlib_tr_init_data_pgot+0xd6>
			2962: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    2966:	add    $0x100,%ebx
    296c:	movslq %ebx,%rbx
    296f:	mov    %r15b,(%rdx,%rbx,1)
    2973:	mov    %esi,%ebx
    2975:	mov    0x0(%rip),%rdx        # 297c <pgot_zlib_tr_init_data_pgot+0xec>
			2978: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    297c:	mov    %ebx,%r12d
    297f:	mov    (%rdx,%r14,1),%ecx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2962, pgot_dist_code_data_pgot

```asm
    295d:	jmp    2975 <pgot_zlib_tr_init_data_pgot+0xe5>
    295f:	mov    0x0(%rip),%rdx        # 2966 <pgot_zlib_tr_init_data_pgot+0xd6>
			2962: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    2966:	add    $0x100,%ebx
    296c:	movslq %ebx,%rbx
    296f:	mov    %r15b,(%rdx,%rbx,1)
    2973:	mov    %esi,%ebx
    2975:	mov    0x0(%rip),%rdx        # 297c <pgot_zlib_tr_init_data_pgot+0xec>
			2978: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    297c:	mov    %ebx,%r12d
    297f:	mov    (%rdx,%r14,1),%ecx
    2983:	sub    $0x7,%ecx
    2986:	cmp    $0x1f,%ecx
    2989:	ja     298f <pgot_zlib_tr_init_data_pgot+0xff>
			298b: R_X86_64_PC32	.text.unlikely+0xa3c
    298f:	mov    %r8d,%edi
    2992:	mov    %ebx,%edx
    2994:	lea    0x1(%rbx),%esi
    2997:	shl    %cl,%edi
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2978, pgot_extra_dbits_data_pgot

```asm
    2973:	mov    %esi,%ebx
    2975:	mov    0x0(%rip),%rdx        # 297c <pgot_zlib_tr_init_data_pgot+0xec>
			2978: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    297c:	mov    %ebx,%r12d
    297f:	mov    (%rdx,%r14,1),%ecx
    2983:	sub    $0x7,%ecx
    2986:	cmp    $0x1f,%ecx
    2989:	ja     298f <pgot_zlib_tr_init_data_pgot+0xff>
			298b: R_X86_64_PC32	.text.unlikely+0xa3c
    298f:	mov    %r8d,%edi
    2992:	mov    %ebx,%edx
    2994:	lea    0x1(%rbx),%esi
    2997:	shl    %cl,%edi
    2999:	sub    %eax,%edx
    299b:	cmp    %edx,%edi
    299d:	jg     295f <pgot_zlib_tr_init_data_pgot+0xcf>
    299f:	add    $0x1,%r15d
    29a3:	add    $0x4,%r14
    29a7:	cmp    $0x1e,%r15d
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 29d8, pgot_static_ltree_data_pgot

```asm
    29d3:	xor    %eax,%eax
    29d5:	mov    0x0(%rip),%rdx        # 29dc <pgot_zlib_tr_init_data_pgot+0x14c>
			29d8: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    29dc:	mov    $0x8,%ebx
    29e1:	mov    %bx,0x2(%rdx,%rax,1)
    29e6:	add    $0x4,%rax
    29ea:	cmp    $0x240,%rax
    29f0:	jne    29d5 <pgot_zlib_tr_init_data_pgot+0x145>
    29f2:	movzwl -0x3e(%rbp),%esi
    29f6:	mov    0x0(%rip),%rdx        # 29fd <pgot_zlib_tr_init_data_pgot+0x16d>
			29f9: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    29fd:	mov    $0x9,%r11d
    2a03:	mov    %r11w,0x2(%rdx,%rax,1)
    2a09:	add    $0x4,%rax
    2a0d:	cmp    $0x400,%rax
    2a13:	jne    29f6 <pgot_zlib_tr_init_data_pgot+0x166>
    2a15:	lea    0x70(%rsi),%edx
    2a18:	movzwl -0x42(%rbp),%esi
    2a1c:	mov    %dx,-0x3e(%rbp)
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 29f9, pgot_static_ltree_data_pgot

```asm
    29f2:	movzwl -0x3e(%rbp),%esi
    29f6:	mov    0x0(%rip),%rdx        # 29fd <pgot_zlib_tr_init_data_pgot+0x16d>
			29f9: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    29fd:	mov    $0x9,%r11d
    2a03:	mov    %r11w,0x2(%rdx,%rax,1)
    2a09:	add    $0x4,%rax
    2a0d:	cmp    $0x400,%rax
    2a13:	jne    29f6 <pgot_zlib_tr_init_data_pgot+0x166>
    2a15:	lea    0x70(%rsi),%edx
    2a18:	movzwl -0x42(%rbp),%esi
    2a1c:	mov    %dx,-0x3e(%rbp)
    2a20:	mov    0x0(%rip),%rdx        # 2a27 <pgot_zlib_tr_init_data_pgot+0x197>
			2a23: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a27:	mov    $0x7,%r10d
    2a2d:	mov    %r10w,0x2(%rdx,%rax,1)
    2a33:	add    $0x4,%rax
    2a37:	cmp    $0x460,%rax
    2a3d:	jne    2a20 <pgot_zlib_tr_init_data_pgot+0x190>
    2a3f:	lea    0x18(%rsi),%edx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2a23, pgot_static_ltree_data_pgot

```asm
    2a1c:	mov    %dx,-0x3e(%rbp)
    2a20:	mov    0x0(%rip),%rdx        # 2a27 <pgot_zlib_tr_init_data_pgot+0x197>
			2a23: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a27:	mov    $0x7,%r10d
    2a2d:	mov    %r10w,0x2(%rdx,%rax,1)
    2a33:	add    $0x4,%rax
    2a37:	cmp    $0x460,%rax
    2a3d:	jne    2a20 <pgot_zlib_tr_init_data_pgot+0x190>
    2a3f:	lea    0x18(%rsi),%edx
    2a42:	mov    %dx,-0x42(%rbp)
    2a46:	mov    0x0(%rip),%rdx        # 2a4d <pgot_zlib_tr_init_data_pgot+0x1bd>
			2a49: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a4d:	mov    $0x8,%r9d
    2a53:	mov    %r9w,0x2(%rdx,%rax,1)
    2a59:	add    $0x4,%rax
    2a5d:	cmp    $0x480,%rax
    2a63:	jne    2a46 <pgot_zlib_tr_init_data_pgot+0x1b6>
    2a65:	mov    0x0(%rip),%rdi        # 2a6c <pgot_zlib_tr_init_data_pgot+0x1dc>
			2a68: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2a49, pgot_static_ltree_data_pgot

```asm
    2a42:	mov    %dx,-0x42(%rbp)
    2a46:	mov    0x0(%rip),%rdx        # 2a4d <pgot_zlib_tr_init_data_pgot+0x1bd>
			2a49: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a4d:	mov    $0x8,%r9d
    2a53:	mov    %r9w,0x2(%rdx,%rax,1)
    2a59:	add    $0x4,%rax
    2a5d:	cmp    $0x480,%rax
    2a63:	jne    2a46 <pgot_zlib_tr_init_data_pgot+0x1b6>
    2a65:	mov    0x0(%rip),%rdi        # 2a6c <pgot_zlib_tr_init_data_pgot+0x1dc>
			2a68: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a6c:	lea    -0x50(%rbp),%rdx
    2a70:	mov    $0x11f,%esi
    2a75:	xor    %ebx,%ebx
    2a77:	lea    0x98(%rcx),%eax
    2a7d:	mov    %ax,-0x40(%rbp)
    2a81:	call   17a0 <gen_codes>
    2a86:	mov    0x0(%rip),%rax        # 2a8d <pgot_zlib_tr_init_data_pgot+0x1fd>
			2a89: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    2a8d:	lea    0x0(,%rbx,4),%r12
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2a68, pgot_static_ltree_data_pgot

```asm
    2a63:	jne    2a46 <pgot_zlib_tr_init_data_pgot+0x1b6>
    2a65:	mov    0x0(%rip),%rdi        # 2a6c <pgot_zlib_tr_init_data_pgot+0x1dc>
			2a68: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a6c:	lea    -0x50(%rbp),%rdx
    2a70:	mov    $0x11f,%esi
    2a75:	xor    %ebx,%ebx
    2a77:	lea    0x98(%rcx),%eax
    2a7d:	mov    %ax,-0x40(%rbp)
    2a81:	call   17a0 <gen_codes>
    2a86:	mov    0x0(%rip),%rax        # 2a8d <pgot_zlib_tr_init_data_pgot+0x1fd>
			2a89: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    2a8d:	lea    0x0(,%rbx,4),%r12
    2a95:	mov    $0x5,%r8d
    2a9b:	movslq %ebx,%rsi
    2a9e:	mov    %r8w,0x2(%rax,%r12,1)
    2aa4:	cmp    $0xff,%rsi
    2aab:	ja     2caa <pgot_zlib_tr_init_data_pgot+0x41a>
    2ab1:	movzbl 0x0(%rbx),%eax
			2ab4: R_X86_64_32S	byte_rev_table
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2a89, pgot_static_dtree_data_pgot

```asm
    2a81:	call   17a0 <gen_codes>
    2a86:	mov    0x0(%rip),%rax        # 2a8d <pgot_zlib_tr_init_data_pgot+0x1fd>
			2a89: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    2a8d:	lea    0x0(,%rbx,4),%r12
    2a95:	mov    $0x5,%r8d
    2a9b:	movslq %ebx,%rsi
    2a9e:	mov    %r8w,0x2(%rax,%r12,1)
    2aa4:	cmp    $0xff,%rsi
    2aab:	ja     2caa <pgot_zlib_tr_init_data_pgot+0x41a>
    2ab1:	movzbl 0x0(%rbx),%eax
			2ab4: R_X86_64_32S	byte_rev_table
    2ab8:	mov    0x0(%rip),%rdx        # 2abf <pgot_zlib_tr_init_data_pgot+0x22f>
			2abb: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    2abf:	add    $0x1,%rbx
    2ac3:	shr    $0x3,%eax
    2ac6:	mov    %ax,(%rdx,%r12,1)
    2acb:	cmp    $0x1e,%rbx
    2acf:	jne    2a86 <pgot_zlib_tr_init_data_pgot+0x1f6>
    2ad1:	movl   $0x1,0x0(%rip)        # 2adb <pgot_zlib_tr_init_data_pgot+0x24b>
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2abb, pgot_static_dtree_data_pgot

```asm
			2ab4: R_X86_64_32S	byte_rev_table
    2ab8:	mov    0x0(%rip),%rdx        # 2abf <pgot_zlib_tr_init_data_pgot+0x22f>
			2abb: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    2abf:	add    $0x1,%rbx
    2ac3:	shr    $0x3,%eax
    2ac6:	mov    %ax,(%rdx,%r12,1)
    2acb:	cmp    $0x1e,%rbx
    2acf:	jne    2a86 <pgot_zlib_tr_init_data_pgot+0x1f6>
    2ad1:	movl   $0x1,0x0(%rip)        # 2adb <pgot_zlib_tr_init_data_pgot+0x24b>
			2ad3: R_X86_64_PC32	.bss-0x8
    2adb:	lea    0xbc(%r13),%rax
    2ae2:	xor    %edi,%edi
    2ae4:	xor    %ebx,%ebx
    2ae6:	movq   $0x0,0x1710(%r13)
    2af1:	mov    %rax,0xb40(%r13)
    2af8:	lea    0x9b0(%r13),%rax
    2aff:	mov    %rax,0xb58(%r13)
    2b06:	lea    0xaa4(%r13),%rax
    2b0d:	movq   $0x0,0xb50(%r13)
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2c22, pgot_length_code_data_pgot

```asm
    2c1e:	int3   
    2c1f:	mov    0x0(%rip),%rdx        # 2c26 <pgot_zlib_tr_init_data_pgot+0x396>
			2c22: R_X86_64_PC32	pgot_length_code_data_pgot-0x4
    2c26:	lea    -0x1(%r12),%eax
    2c2b:	xor    %r15d,%r15d
    2c2e:	xor    %r14d,%r14d
    2c31:	cltq   
    2c33:	mov    $0x1,%r9d
    2c39:	movb   $0x1c,(%rdx,%rax,1)
    2c3d:	mov    0x0(%rip),%rax        # 2c44 <pgot_zlib_tr_init_data_pgot+0x3b4>
			2c40: R_X86_64_PC32	pgot_base_dist_data_pgot-0x4
    2c44:	lea    0x0(,%r14,4),%r8
    2c4c:	xor    %ebx,%ebx
    2c4e:	mov    %r15d,(%rax,%r14,4)
    2c52:	jmp    2c65 <pgot_zlib_tr_init_data_pgot+0x3d5>
    2c54:	mov    0x0(%rip),%rax        # 2c5b <pgot_zlib_tr_init_data_pgot+0x3cb>
			2c57: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    2c5b:	movslq %r12d,%r12
    2c5e:	add    $0x1,%ebx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2c40, pgot_base_dist_data_pgot

```asm
    2c39:	movb   $0x1c,(%rdx,%rax,1)
    2c3d:	mov    0x0(%rip),%rax        # 2c44 <pgot_zlib_tr_init_data_pgot+0x3b4>
			2c40: R_X86_64_PC32	pgot_base_dist_data_pgot-0x4
    2c44:	lea    0x0(,%r14,4),%r8
    2c4c:	xor    %ebx,%ebx
    2c4e:	mov    %r15d,(%rax,%r14,4)
    2c52:	jmp    2c65 <pgot_zlib_tr_init_data_pgot+0x3d5>
    2c54:	mov    0x0(%rip),%rax        # 2c5b <pgot_zlib_tr_init_data_pgot+0x3cb>
			2c57: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    2c5b:	movslq %r12d,%r12
    2c5e:	add    $0x1,%ebx
    2c61:	mov    %r14b,(%rax,%r12,1)
    2c65:	mov    0x0(%rip),%rax        # 2c6c <pgot_zlib_tr_init_data_pgot+0x3dc>
			2c68: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    2c6c:	lea    (%rbx,%r15,1),%r12d
    2c70:	mov    (%rax,%r8,1),%ecx
    2c74:	cmp    $0x1f,%ecx
    2c77:	ja     2c7d <pgot_zlib_tr_init_data_pgot+0x3ed>
			2c79: R_X86_64_PC32	.text.unlikely+0x9d8
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2c57, pgot_dist_code_data_pgot

```asm
    2c52:	jmp    2c65 <pgot_zlib_tr_init_data_pgot+0x3d5>
    2c54:	mov    0x0(%rip),%rax        # 2c5b <pgot_zlib_tr_init_data_pgot+0x3cb>
			2c57: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    2c5b:	movslq %r12d,%r12
    2c5e:	add    $0x1,%ebx
    2c61:	mov    %r14b,(%rax,%r12,1)
    2c65:	mov    0x0(%rip),%rax        # 2c6c <pgot_zlib_tr_init_data_pgot+0x3dc>
			2c68: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    2c6c:	lea    (%rbx,%r15,1),%r12d
    2c70:	mov    (%rax,%r8,1),%ecx
    2c74:	cmp    $0x1f,%ecx
    2c77:	ja     2c7d <pgot_zlib_tr_init_data_pgot+0x3ed>
			2c79: R_X86_64_PC32	.text.unlikely+0x9d8
    2c7d:	mov    %r9d,%eax
    2c80:	shl    %cl,%eax
    2c82:	cmp    %eax,%ebx
    2c84:	jl     2c54 <pgot_zlib_tr_init_data_pgot+0x3c4>
    2c86:	add    $0x1,%r14
    2c8a:	cmp    $0x10,%r14
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2c68, pgot_extra_dbits_data_pgot

```asm
    2c61:	mov    %r14b,(%rax,%r12,1)
    2c65:	mov    0x0(%rip),%rax        # 2c6c <pgot_zlib_tr_init_data_pgot+0x3dc>
			2c68: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    2c6c:	lea    (%rbx,%r15,1),%r12d
    2c70:	mov    (%rax,%r8,1),%ecx
    2c74:	cmp    $0x1f,%ecx
    2c77:	ja     2c7d <pgot_zlib_tr_init_data_pgot+0x3ed>
			2c79: R_X86_64_PC32	.text.unlikely+0x9d8
    2c7d:	mov    %r9d,%eax
    2c80:	shl    %cl,%eax
    2c82:	cmp    %eax,%ebx
    2c84:	jl     2c54 <pgot_zlib_tr_init_data_pgot+0x3c4>
    2c86:	add    $0x1,%r14
    2c8a:	cmp    $0x10,%r14
    2c8e:	je     2930 <pgot_zlib_tr_init_data_pgot+0xa0>
    2c94:	mov    %r12d,%r15d
    2c97:	jmp    2c3d <pgot_zlib_tr_init_data_pgot+0x3ad>
    2c99:	mov    $0x0,%rdi
			2c9c: R_X86_64_32S	.data+0x200
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_deflateReset_data_pgot, 2da8, memset

```asm
    2da4:	add    %rdx,%rdx
    2da7:	call   2dac <pgot_zlib_deflateReset_data_pgot+0xac>
			2da8: R_X86_64_PLT32	memset-0x4
    2dac:	movslq 0xac(%rbx),%rax
    2db3:	shl    $0x4,%rax
    2db7:	add    0x0(%rip),%rax        # 2dbe <pgot_zlib_deflateReset_data_pgot+0xbe>
			2dba: R_X86_64_PC32	pgot_configuration_table_data_pgot-0x4
    2dbe:	movzwl 0x2(%rax),%edx
    2dc2:	mov    %edx,0xa8(%rbx)
    2dc8:	movzwl (%rax),%edx
    2dcb:	mov    %edx,0xb4(%rbx)
    2dd1:	movzwl 0x4(%rax),%edx
    2dd5:	mov    %edx,0xb8(%rbx)
    2ddb:	movzwl 0x6(%rax),%eax
    2ddf:	movq   $0x0,0x80(%rbx)
    2dea:	movl   $0x2,0x88(%rbx)
    2df4:	movq   $0x0,0x90(%rbx)
    2dff:	movl   $0x0,0x68(%rbx)
    2e06:	mov    %eax,0xa4(%rbx)
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_deflateReset_data_pgot, 2dba, pgot_configuration_table_data_pgot

```asm
    2db3:	shl    $0x4,%rax
    2db7:	add    0x0(%rip),%rax        # 2dbe <pgot_zlib_deflateReset_data_pgot+0xbe>
			2dba: R_X86_64_PC32	pgot_configuration_table_data_pgot-0x4
    2dbe:	movzwl 0x2(%rax),%edx
    2dc2:	mov    %edx,0xa8(%rbx)
    2dc8:	movzwl (%rax),%edx
    2dcb:	mov    %edx,0xb4(%rbx)
    2dd1:	movzwl 0x4(%rax),%edx
    2dd5:	mov    %edx,0xb8(%rbx)
    2ddb:	movzwl 0x6(%rax),%eax
    2ddf:	movq   $0x0,0x80(%rbx)
    2dea:	movl   $0x2,0x88(%rbx)
    2df4:	movq   $0x0,0x90(%rbx)
    2dff:	movl   $0x0,0x68(%rbx)
    2e06:	mov    %eax,0xa4(%rbx)
    2e0c:	movabs $0x200000000,%rax
    2e16:	mov    %rax,0x9c(%rbx)
    2e1d:	xor    %eax,%eax
    2e1f:	mov    -0x8(%rbp),%rbx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_stored_block_data_pgot, 316c, memcpy

```asm
    3167:	add    0x10(%rbx),%rdi
    316b:	call   3170 <pgot_zlib_tr_stored_block_data_pgot+0x180>
			316c: R_X86_64_PLT32	memcpy-0x4
    3170:	add    %r12d,0x28(%rbx)
    3174:	add    $0x8,%rsp
    3178:	pop    %rbx
    3179:	pop    %r12
    317b:	pop    %r13
    317d:	pop    %r14
    317f:	pop    %rbp
    3180:	ret    
    3181:	int3   
    3182:	cmp    $0x1f,%ecx
    3185:	ja     318b <pgot_zlib_tr_stored_block_data_pgot+0x19b>
			3187: R_X86_64_PC32	.text.unlikely+0xa6f
    318b:	mov    %ecx,%eax
    318d:	mov    %r13d,%edx
    3190:	shl    %cl,%edx
    3192:	lea    0x3(%rax),%ecx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_align_data_pgot, 336d, pgot_static_ltree_data_pgot

```asm
    3363:	mov    %ax,0x1720(%rbx)
    336a:	mov    0x0(%rip),%rax        # 3371 <pgot_zlib_tr_align_data_pgot+0xa1>
			336d: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    3371:	mov    $0x10,%esi
    3376:	mov    %ecx,0x1724(%rbx)
    337c:	movzwl 0x402(%rax),%r12d
    3384:	movzwl 0x400(%rax),%eax
    338b:	sub    %r12d,%esi
    338e:	mov    %eax,%r13d
    3391:	cmp    %ecx,%esi
    3393:	jge    35de <pgot_zlib_tr_align_data_pgot+0x30e>
    3399:	cmp    $0x1f,%edx
    339c:	ja     33a2 <pgot_zlib_tr_align_data_pgot+0xd2>
			339e: R_X86_64_PC32	.text.unlikely+0xb94
    33a2:	movslq 0x28(%rbx),%rdx
    33a6:	mov    %eax,%edi
    33a8:	mov    0x10(%rbx),%rsi
    33ac:	shl    %cl,%edi
    33ae:	mov    %edi,%ecx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_align_data_pgot, 34ec, pgot_static_ltree_data_pgot

```asm
    34e2:	mov    %ax,0x1720(%rbx)
    34e9:	mov    0x0(%rip),%rsi        # 34f0 <pgot_zlib_tr_align_data_pgot+0x220>
			34ec: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    34f0:	mov    %ecx,0x1724(%rbx)
    34f6:	movzwl 0x402(%rsi),%eax
    34fd:	movzwl 0x400(%rsi),%r12d
    3505:	mov    $0x10,%esi
    350a:	sub    %eax,%esi
    350c:	mov    %r12d,%r13d
    350f:	cmp    %ecx,%esi
    3511:	jge    368a <pgot_zlib_tr_align_data_pgot+0x3ba>
    3517:	cmp    $0x1f,%edx
    351a:	ja     3520 <pgot_zlib_tr_align_data_pgot+0x250>
			351c: R_X86_64_PC32	.text.unlikely+0xc1e
    3520:	movslq 0x28(%rbx),%rdx
    3524:	mov    %r12d,%edi
    3527:	mov    0x10(%rbx),%rsi
    352b:	shl    %cl,%edi
    352d:	mov    %edi,%ecx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_deflate_data_pgot, 37cd, pgot_configuration_table_data_pgot

```asm
    37c6:	shl    $0x4,%rax
    37ca:	add    0x0(%rip),%rax        # 37d1 <pgot_zlib_deflate_data_pgot+0xd1>
			37cd: R_X86_64_PC32	pgot_configuration_table_data_pgot-0x4
    37d1:	mov    0x8(%rax),%rax
    37d5:	call   *%rax
    37d7:	lea    -0x2(%rax),%edx
    37da:	cmp    $0x1,%edx
    37dd:	jbe    390a <pgot_zlib_deflate_data_pgot+0x20a>
    37e3:	test   $0xfffffffd,%eax
    37e8:	je     391a <pgot_zlib_deflate_data_pgot+0x21a>
    37ee:	cmp    $0x1,%eax
    37f1:	jne    38ae <pgot_zlib_deflate_data_pgot+0x1ae>
    37f7:	cmp    $0x1,%r13d
    37fb:	je     3c17 <pgot_zlib_deflate_data_pgot+0x517>
    3801:	cmp    $0x2,%r13d
    3805:	je     3c09 <pgot_zlib_deflate_data_pgot+0x509>
    380b:	mov    -0x30(%rbp),%rdi
    380f:	xor    %ecx,%ecx
    3811:	xor    %edx,%edx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_deflate_data_pgot, 3844, memset

```asm
    3840:	add    %rdx,%rdx
    3843:	call   3848 <pgot_zlib_deflate_data_pgot+0x148>
			3844: R_X86_64_PLT32	memset-0x4
    3848:	mov    0x38(%r12),%r15
    384d:	mov    0x20(%r12),%rax
    3852:	mov    0x28(%r15),%edx
    3856:	mov    %rdx,%r14
    3859:	cmp    %rax,%rdx
    385c:	cmova  %eax,%r14d
    3860:	test   %r14d,%r14d
    3863:	je     38a9 <pgot_zlib_deflate_data_pgot+0x1a9>
    3865:	mov    0x18(%r12),%rdi
    386a:	mov    %r14d,%edx
    386d:	test   %rdi,%rdi
    3870:	je     3888 <pgot_zlib_deflate_data_pgot+0x188>
    3872:	mov    0x20(%r15),%rsi
    3876:	mov    %rdx,-0x38(%rbp)
    387a:	call   387f <pgot_zlib_deflate_data_pgot+0x17f>
			387b: R_X86_64_PLT32	memcpy-0x4
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_deflate_data_pgot, 387b, memcpy

```asm
    3876:	mov    %rdx,-0x38(%rbp)
    387a:	call   387f <pgot_zlib_deflate_data_pgot+0x17f>
			387b: R_X86_64_PLT32	memcpy-0x4
    387f:	mov    -0x38(%rbp),%rdx
    3883:	add    %rdx,0x18(%r12)
    3888:	add    %rdx,0x20(%r15)
    388c:	add    %rdx,0x28(%r12)
    3891:	sub    %rdx,0x20(%r12)
    3896:	sub    %r14d,0x28(%r15)
    389a:	jne    38a4 <pgot_zlib_deflate_data_pgot+0x1a4>
    389c:	mov    0x10(%r15),%rax
    38a0:	mov    %rax,0x20(%r15)
    38a4:	mov    0x20(%r12),%rax
    38a9:	test   %rax,%rax
    38ac:	je     3922 <pgot_zlib_deflate_data_pgot+0x222>
    38ae:	cmp    $0x5,%r13d
    38b2:	jne    392d <pgot_zlib_deflate_data_pgot+0x22d>
    38b4:	mov    -0x30(%rbp),%rdi
    38b8:	mov    $0x1,%eax
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_deflate_data_pgot, 3a24, memcpy

```asm
    3a1f:	mov    %rdx,-0x38(%rbp)
    3a23:	call   3a28 <pgot_zlib_deflate_data_pgot+0x328>
			3a24: R_X86_64_PLT32	memcpy-0x4
    3a28:	mov    -0x38(%rbp),%rdx
    3a2c:	add    %rdx,0x18(%r12)
    3a31:	add    %rdx,0x20(%r15)
    3a35:	add    %rdx,0x28(%r12)
    3a3a:	sub    %rdx,0x20(%r12)
    3a3f:	sub    %r14d,0x28(%r15)
    3a43:	je     3b95 <pgot_zlib_deflate_data_pgot+0x495>
    3a49:	mov    0x20(%r12),%rax
    3a4e:	test   %rax,%rax
    3a51:	je     3922 <pgot_zlib_deflate_data_pgot+0x222>
    3a57:	mov    -0x30(%rbp),%rdx
    3a5b:	mov    0x8(%r12),%rax
    3a60:	cmpl   $0x29a,0x8(%rdx)
    3a67:	jne    3a99 <pgot_zlib_deflate_data_pgot+0x399>
    3a69:	test   %rax,%rax
    3a6c:	je     38f6 <pgot_zlib_deflate_data_pgot+0x1f6>
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_deflate_data_pgot, 3b4b, memcpy

```asm
    3b47:	mov    %r15,%rdx
    3b4a:	call   3b4f <pgot_zlib_deflate_data_pgot+0x44f>
			3b4b: R_X86_64_PLT32	memcpy-0x4
    3b4f:	add    %r15,0x18(%r12)
    3b54:	add    %r15,0x20(%r14)
    3b58:	add    %r15,0x28(%r12)
    3b5d:	sub    %r15,0x20(%r12)
    3b62:	sub    %r13d,0x28(%r14)
    3b66:	jne    3b70 <pgot_zlib_deflate_data_pgot+0x470>
    3b68:	mov    0x10(%r14),%rax
    3b6c:	mov    %rax,0x20(%r14)
    3b70:	mov    -0x30(%rbp),%rax
    3b74:	mov    0x28(%rax),%edx
    3b77:	movl   $0xffffffff,0x2c(%rax)
    3b7e:	xor    %eax,%eax
    3b80:	test   %edx,%edx
    3b82:	sete   %al
    3b85:	add    $0x10,%rsp
    3b89:	pop    %rbx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_flush_block_data_pgot, 3ced, pgot_bl_order_data_pgot

```asm
    3ce5:	call   1900 <build_tree>
    3cea:	mov    0x0(%rip),%rcx        # 3cf1 <pgot_zlib_tr_flush_block_data_pgot+0xc1>
			3ced: R_X86_64_PC32	pgot_bl_order_data_pgot-0x4
    3cf1:	movzbl (%rcx,%rbx,1),%edx
    3cf5:	mov    %ebx,%eax
    3cf7:	cmp    $0x26,%rdx
    3cfb:	ja     45df <pgot_zlib_tr_flush_block_data_pgot+0x9af>
    3d01:	cmpw   $0x0,0xaa6(%r12,%rdx,4)
    3d0b:	jne    4356 <pgot_zlib_tr_flush_block_data_pgot+0x726>
    3d11:	sub    $0x1,%rbx
    3d15:	cmp    $0x2,%rbx
    3d19:	jne    3cf1 <pgot_zlib_tr_flush_block_data_pgot+0xc1>
    3d1b:	mov    $0x17,%edx
    3d20:	mov    $0x3,%ebx
    3d25:	mov    $0x2,%eax
    3d2a:	mov    0x1708(%r12),%rdi
    3d32:	add    0x1700(%r12),%rdx
    3d3a:	mov    %rdx,0x1700(%r12)
    3d42:	add    $0xa,%rdx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_flush_block_data_pgot, 40e3, pgot_bl_order_data_pgot

```asm
    40de:	je     4127 <pgot_zlib_tr_flush_block_data_pgot+0x4f7>
    40e0:	mov    0x0(%rip),%rdx        # 40e7 <pgot_zlib_tr_flush_block_data_pgot+0x4b7>
			40e3: R_X86_64_PC32	pgot_bl_order_data_pgot-0x4
    40e7:	movzbl (%rdx,%rbx,1),%edx
    40eb:	movslq %edx,%r15
    40ee:	cmp    $0xd,%ecx
    40f1:	jg     4037 <pgot_zlib_tr_flush_block_data_pgot+0x407>
    40f7:	cmp    $0x26,%dl
    40fa:	ja     45bf <pgot_zlib_tr_flush_block_data_pgot+0x98f>
    4100:	movzwl 0xaa6(%r12,%r15,4),%r15d
    4109:	cmp    $0x1f,%ecx
    410c:	ja     4112 <pgot_zlib_tr_flush_block_data_pgot+0x4e2>
			410e: R_X86_64_PC32	.text.unlikely+0xec6
    4112:	mov    %ecx,%esi
    4114:	mov    %r15d,%edx
    4117:	shl    %cl,%edx
    4119:	lea    0x3(%rsi),%ecx
    411c:	or     0x1720(%r12),%dx
    4125:	jmp    40c6 <pgot_zlib_tr_flush_block_data_pgot+0x496>
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_flush_block_data_pgot, 42b7, pgot_static_ltree_data_pgot

```asm
    42ab:	mov    %ax,0x1720(%r12)
    42b4:	mov    0x0(%rip),%rsi        # 42bb <pgot_zlib_tr_flush_block_data_pgot+0x68b>
			42b7: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    42bb:	mov    %r12,%rdi
    42be:	mov    %edx,0x1724(%r12)
    42c6:	mov    0x0(%rip),%rdx        # 42cd <pgot_zlib_tr_flush_block_data_pgot+0x69d>
			42c9: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    42cd:	call   1220 <compress_block>
    42d2:	mov    0x1708(%r12),%rax
    42da:	add    0x1710(%r12),%rax
    42e2:	add    $0x3,%rax
    42e6:	mov    %rax,0x1710(%r12)
    42ee:	jmp    4175 <pgot_zlib_tr_flush_block_data_pgot+0x545>
    42f3:	mov    0x1724(%r12),%eax
    42fb:	cmp    $0x8,%eax
    42fe:	jg     43f9 <pgot_zlib_tr_flush_block_data_pgot+0x7c9>
    4304:	test   %eax,%eax
    4306:	jle    4326 <pgot_zlib_tr_flush_block_data_pgot+0x6f6>
    4308:	movzwl 0x1720(%r12),%ecx
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_flush_block_data_pgot, 42c9, pgot_static_dtree_data_pgot

```asm
    42be:	mov    %edx,0x1724(%r12)
    42c6:	mov    0x0(%rip),%rdx        # 42cd <pgot_zlib_tr_flush_block_data_pgot+0x69d>
			42c9: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    42cd:	call   1220 <compress_block>
    42d2:	mov    0x1708(%r12),%rax
    42da:	add    0x1710(%r12),%rax
    42e2:	add    $0x3,%rax
    42e6:	mov    %rax,0x1710(%r12)
    42ee:	jmp    4175 <pgot_zlib_tr_flush_block_data_pgot+0x545>
    42f3:	mov    0x1724(%r12),%eax
    42fb:	cmp    $0x8,%eax
    42fe:	jg     43f9 <pgot_zlib_tr_flush_block_data_pgot+0x7c9>
    4304:	test   %eax,%eax
    4306:	jle    4326 <pgot_zlib_tr_flush_block_data_pgot+0x6f6>
    4308:	movzwl 0x1720(%r12),%ecx
    4311:	movslq 0x28(%r12),%rax
    4316:	mov    0x10(%r12),%rdx
    431b:	lea    0x1(%rax),%esi
    431e:	mov    %esi,0x28(%r12)
```

## 03_zlib_deflate/no_retpoline/data_pgot: deflate_stored, 46ed, memcpy

```asm
    46e8:	mov    %rdx,-0x30(%rbp)
    46ec:	call   46f1 <deflate_stored+0xd1>
			46ed: R_X86_64_PLT32	memcpy-0x4
    46f1:	mov    -0x30(%rbp),%rdx
    46f5:	add    %rdx,0x18(%r14)
    46f9:	add    %rdx,0x20(%r13)
    46fd:	add    %rdx,0x28(%r14)
    4701:	sub    %rdx,0x20(%r14)
    4705:	sub    %r15d,0x28(%r13)
    4709:	jne    4713 <deflate_stored+0xf3>
    470b:	mov    0x10(%r13),%rax
    470f:	mov    %rax,0x20(%r13)
    4713:	mov    (%rbx),%rax
    4716:	mov    0x20(%rax),%rax
    471a:	test   %rax,%rax
    471d:	je     48d3 <deflate_stored+0x2b3>
    4723:	mov    0x94(%rbx),%eax
    4729:	mov    0x80(%rbx),%rcx
    4730:	mov    0x38(%rbx),%edi
```

## 03_zlib_deflate/no_retpoline/data_pgot: deflate_stored, 47eb, memcpy

```asm
    47e6:	mov    %rdx,-0x30(%rbp)
    47ea:	call   47ef <deflate_stored+0x1cf>
			47eb: R_X86_64_PLT32	memcpy-0x4
    47ef:	mov    -0x30(%rbp),%rdx
    47f3:	add    %rdx,0x18(%r14)
    47f7:	mov    -0x40(%rbp),%rcx
    47fb:	add    %rdx,0x20(%rcx)
    47ff:	add    %rdx,0x28(%r14)
    4803:	sub    %rdx,0x20(%r14)
    4807:	sub    %r15d,0x28(%rcx)
    480b:	jne    4815 <deflate_stored+0x1f5>
    480d:	mov    0x10(%rcx),%rax
    4811:	mov    %rax,0x20(%rcx)
    4815:	mov    (%rbx),%rax
    4818:	mov    0x20(%rax),%rax
    481c:	test   %rax,%rax
    481f:	je     48ef <deflate_stored+0x2cf>
    4825:	xor    %eax,%eax
    4827:	cmpl   $0x5,-0x34(%rbp)
```

## 03_zlib_deflate/no_retpoline/data_pgot: deflate_stored, 48a1, memcpy

```asm
    489c:	mov    %rdx,-0x30(%rbp)
    48a0:	call   48a5 <deflate_stored+0x285>
			48a1: R_X86_64_PLT32	memcpy-0x4
    48a5:	mov    -0x30(%rbp),%rdx
    48a9:	add    %rdx,0x18(%r14)
    48ad:	mov    -0x40(%rbp),%rcx
    48b1:	add    %rdx,0x20(%rcx)
    48b5:	add    %rdx,0x28(%r14)
    48b9:	sub    %rdx,0x20(%r14)
    48bd:	sub    %r15d,0x28(%rcx)
    48c1:	je     48e5 <deflate_stored+0x2c5>
    48c3:	mov    (%rbx),%rax
    48c6:	mov    0x20(%rax),%rax
    48ca:	test   %rax,%rax
    48cd:	jne    4745 <deflate_stored+0x125>
    48d3:	xor    %eax,%eax
    48d5:	add    $0x18,%rsp
    48d9:	pop    %rbx
    48da:	pop    %r12
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_tally_data_pgot, 4987, pgot_extra_dbits_data_pgot

```asm
    4981:	mov    %r15d,%r13d
    4984:	mov    0x0(%rip),%r14        # 498b <pgot_zlib_tr_tally_data_pgot+0x8b>
			4987: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    498b:	xor    %ebx,%ebx
    498d:	mov    0x94(%r12),%ecx
    4995:	mov    0x80(%r12),%r8
    499d:	shl    $0x3,%r13
    49a1:	movslq %ebx,%rsi
    49a4:	cmp    $0x3c,%rsi
    49a8:	ja     4a97 <pgot_zlib_tr_tally_data_pgot+0x197>
    49ae:	movzwl 0x9b0(%r12,%rbx,4),%edx
    49b7:	movslq (%r14,%rbx,4),%rax
    49bb:	add    $0x1,%rbx
    49bf:	add    $0x5,%rax
    49c3:	imul   %rdx,%rax
    49c7:	add    %rax,%r13
    49ca:	cmp    $0x1e,%rbx
    49ce:	jne    49a1 <pgot_zlib_tr_tally_data_pgot+0xa1>
    49d0:	mov    %r15d,%eax
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_tally_data_pgot, 4a0a, pgot_length_code_data_pgot

```asm
    4a06:	int3   
    4a07:	mov    0x0(%rip),%rax        # 4a0e <pgot_zlib_tr_tally_data_pgot+0x10e>
			4a0a: R_X86_64_PC32	pgot_length_code_data_pgot-0x4
    4a0e:	mov    %edx,%edx
    4a10:	lea    -0x1(%rsi),%ebx
    4a13:	addl   $0x1,0x1718(%r12)
    4a1c:	movzbl (%rax,%rdx,1),%eax
    4a20:	lea    0x101(%rax),%r13
    4a27:	cmp    $0x23c,%r13
    4a2e:	ja     4ac7 <pgot_zlib_tr_tally_data_pgot+0x1c7>
    4a34:	addw   $0x1,0xbc(%r12,%r13,4)
    4a3e:	mov    0x0(%rip),%rdx        # 4a45 <pgot_zlib_tr_tally_data_pgot+0x145>
			4a41: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    4a45:	cmp    $0xff,%ebx
    4a4b:	jbe    4a72 <pgot_zlib_tr_tally_data_pgot+0x172>
    4a4d:	mov    %ebx,%esi
    4a4f:	shr    $0x7,%esi
    4a52:	lea    0x100(%rsi),%eax
    4a58:	movzbl (%rdx,%rax,1),%eax
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_tally_data_pgot, 4a41, pgot_dist_code_data_pgot

```asm
    4a34:	addw   $0x1,0xbc(%r12,%r13,4)
    4a3e:	mov    0x0(%rip),%rdx        # 4a45 <pgot_zlib_tr_tally_data_pgot+0x145>
			4a41: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    4a45:	cmp    $0xff,%ebx
    4a4b:	jbe    4a72 <pgot_zlib_tr_tally_data_pgot+0x172>
    4a4d:	mov    %ebx,%esi
    4a4f:	shr    $0x7,%esi
    4a52:	lea    0x100(%rsi),%eax
    4a58:	movzbl (%rdx,%rax,1),%eax
    4a5c:	movslq %eax,%rbx
    4a5f:	cmp    $0x3c,%al
    4a61:	ja     4ab6 <pgot_zlib_tr_tally_data_pgot+0x1b6>
    4a63:	addw   $0x1,0x9b0(%r12,%rbx,4)
    4a6d:	jmp    4965 <pgot_zlib_tr_tally_data_pgot+0x65>
    4a72:	mov    %ebx,%esi
    4a74:	movzbl (%rdx,%rsi,1),%eax
    4a78:	jmp    4a5c <pgot_zlib_tr_tally_data_pgot+0x15c>
    4a7a:	sub    %r8,%rcx
    4a7d:	shr    $0x3,%r13
```

## 03_zlib_deflate/no_retpoline/data_pgot: deflate_slow, 4d32, memcpy

```asm
    4d2d:	mov    %rdx,-0x30(%rbp)
    4d31:	call   4d36 <deflate_slow+0x246>
			4d32: R_X86_64_PLT32	memcpy-0x4
    4d36:	mov    -0x30(%rbp),%rdx
    4d3a:	add    %rdx,0x18(%r13)
    4d3e:	mov    -0x38(%rbp),%rcx
    4d42:	add    %rdx,0x20(%rcx)
    4d46:	add    %rdx,0x28(%r13)
    4d4a:	sub    %rdx,0x20(%r13)
    4d4e:	sub    %r15d,0x28(%rcx)
    4d52:	jne    4d5c <deflate_slow+0x26c>
    4d54:	mov    0x10(%rcx),%rax
    4d58:	mov    %rax,0x20(%rcx)
    4d5c:	mov    (%rbx),%rax
    4d5f:	mov    0x20(%rax),%rax
    4d63:	test   %rax,%rax
    4d66:	je     4ee6 <deflate_slow+0x3f6>
    4d6c:	mov    0x9c(%rbx),%eax
    4d72:	cmp    $0x105,%eax
```

## 03_zlib_deflate/no_retpoline/data_pgot: deflate_slow, 4e91, memcpy

```asm
    4e8c:	mov    %r8,-0x30(%rbp)
    4e90:	call   4e95 <deflate_slow+0x3a5>
			4e91: R_X86_64_PLT32	memcpy-0x4
    4e95:	add    %r13,0x18(%r15)
    4e99:	mov    -0x38(%rbp),%ecx
    4e9c:	mov    -0x30(%rbp),%r8
    4ea0:	add    %r13,0x20(%r8)
    4ea4:	add    %r13,0x28(%r15)
    4ea8:	sub    %r13,0x20(%r15)
    4eac:	sub    %ecx,0x28(%r8)
    4eb0:	jne    4eba <deflate_slow+0x3ca>
    4eb2:	mov    0x10(%r8),%rax
    4eb6:	mov    %rax,0x20(%r8)
    4eba:	mov    0x94(%rbx),%eax
    4ec0:	mov    (%rbx),%r15
    4ec3:	add    $0x1,%eax
    4ec6:	mov    %eax,0x94(%rbx)
    4ecc:	mov    0x9c(%rbx),%eax
    4ed2:	sub    $0x1,%eax
```

## 03_zlib_deflate/no_retpoline/data_pgot: deflate_slow, 4fd5, memcpy

```asm
    4fd0:	mov    %rdx,-0x30(%rbp)
    4fd4:	call   4fd9 <deflate_slow+0x4e9>
			4fd5: R_X86_64_PLT32	memcpy-0x4
    4fd9:	mov    -0x30(%rbp),%rdx
    4fdd:	add    %rdx,0x18(%r14)
    4fe1:	mov    -0x38(%rbp),%rcx
    4fe5:	add    %rdx,0x20(%rcx)
    4fe9:	add    %rdx,0x28(%r14)
    4fed:	sub    %rdx,0x20(%r14)
    4ff1:	sub    %r15d,0x28(%rcx)
    4ff5:	je     5020 <deflate_slow+0x530>
    4ff7:	mov    (%rbx),%rax
    4ffa:	mov    0x20(%rax),%rax
    4ffe:	test   %rax,%rax
    5001:	je     5054 <deflate_slow+0x564>
    5003:	xor    %eax,%eax
    5005:	cmp    $0x5,%r12d
    5009:	sete   %al
    500c:	add    $0x10,%rsp
```

## 03_zlib_deflate/no_retpoline/data_pgot: deflate_fast, 5234, memcpy

```asm
    522f:	mov    %rdx,-0x30(%rbp)
    5233:	call   5238 <deflate_fast+0x1c8>
			5234: R_X86_64_PLT32	memcpy-0x4
    5238:	mov    -0x30(%rbp),%rdx
    523c:	add    %rdx,0x18(%r13)
    5240:	add    %rdx,0x20(%r12)
    5245:	add    %rdx,0x28(%r13)
    5249:	sub    %rdx,0x20(%r13)
    524d:	sub    %r15d,0x28(%r12)
    5252:	jne    525e <deflate_fast+0x1ee>
    5254:	mov    0x10(%r12),%rax
    5259:	mov    %rax,0x20(%r12)
    525e:	mov    (%rbx),%rax
    5261:	mov    0x20(%rax),%rax
    5265:	test   %rax,%rax
    5268:	jne    508f <deflate_fast+0x1f>
    526e:	add    $0x18,%rsp
    5272:	xor    %eax,%eax
    5274:	pop    %rbx
```

## 03_zlib_deflate/no_retpoline/data_pgot: deflate_fast, 53d9, memcpy

```asm
    53d4:	mov    %rdx,-0x30(%rbp)
    53d8:	call   53dd <deflate_fast+0x36d>
			53d9: R_X86_64_PLT32	memcpy-0x4
    53dd:	mov    -0x30(%rbp),%rdx
    53e1:	add    %rdx,0x18(%r14)
    53e5:	mov    -0x40(%rbp),%rcx
    53e9:	add    %rdx,0x20(%rcx)
    53ed:	add    %rdx,0x28(%r14)
    53f1:	sub    %rdx,0x20(%r14)
    53f5:	sub    %r15d,0x28(%rcx)
    53f9:	je     5424 <deflate_fast+0x3b4>
    53fb:	mov    (%rbx),%rax
    53fe:	mov    0x20(%rax),%rax
    5402:	test   %rax,%rax
    5405:	je     542e <deflate_fast+0x3be>
    5407:	xor    %eax,%eax
    5409:	cmpl   $0x5,-0x34(%rbp)
    540d:	sete   %al
    5410:	add    $0x18,%rsp
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot.cold, 9f7, pgot_extra_dbits_data_pgot

```asm
			9f0: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     9f4:	mov    0x0(%rip),%rax        # 9fb <pgot_zlib_tr_init_data_pgot.cold+0x1f>
			9f7: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
     9fb:	mov    -0x58(%rbp),%r8
     9ff:	mov    $0x1,%r9d
     a05:	mov    (%rax,%r8,1),%ecx
     a09:	jmp    a0e <pgot_zlib_tr_init_data_pgot.cold+0x32>
			a0a: R_X86_64_PC32	.text+0x2c79
     a0e:	movslq %ecx,%rdx
     a11:	mov    $0x1,%esi
     a16:	mov    $0x0,%rdi
			a19: R_X86_64_32S	.data+0x13c0
     a1d:	mov    %r8,-0x58(%rbp)
     a21:	call   a26 <pgot_zlib_tr_init_data_pgot.cold+0x4a>
			a22: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a26:	mov    0x0(%rip),%rax        # a2d <pgot_zlib_tr_init_data_pgot.cold+0x51>
			a29: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
     a2d:	mov    -0x58(%rbp),%r8
     a31:	mov    $0x1,%r9d
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot.cold, a29, pgot_extra_lbits_data_pgot

```asm
			a22: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a26:	mov    0x0(%rip),%rax        # a2d <pgot_zlib_tr_init_data_pgot.cold+0x51>
			a29: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
     a2d:	mov    -0x58(%rbp),%r8
     a31:	mov    $0x1,%r9d
     a37:	mov    (%rax,%r8,1),%ecx
     a3b:	jmp    a40 <pgot_zlib_tr_init_data_pgot.cold+0x64>
			a3c: R_X86_64_PC32	.text+0x2910
     a40:	movslq %ecx,%rdx
     a43:	mov    $0x1,%esi
     a48:	mov    $0x0,%rdi
			a4b: R_X86_64_32S	.data+0x1380
     a4f:	mov    %eax,-0x58(%rbp)
     a52:	call   a57 <pgot_zlib_tr_init_data_pgot.cold+0x7b>
			a53: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a57:	mov    0x0(%rip),%rdx        # a5e <pgot_zlib_tr_init_data_pgot.cold+0x82>
			a5a: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
     a5e:	mov    -0x58(%rbp),%eax
     a61:	mov    $0x1,%r8d
```

## 03_zlib_deflate/no_retpoline/data_pgot: pgot_zlib_tr_init_data_pgot.cold, a5a, pgot_extra_dbits_data_pgot

```asm
			a53: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a57:	mov    0x0(%rip),%rdx        # a5e <pgot_zlib_tr_init_data_pgot.cold+0x82>
			a5a: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
     a5e:	mov    -0x58(%rbp),%eax
     a61:	mov    $0x1,%r8d
     a67:	mov    (%rdx,%r14,1),%ecx
     a6b:	sub    $0x7,%ecx
     a6e:	jmp    a73 <pgot_zlib_tr_stored_block_data_pgot.cold>
			a6f: R_X86_64_PC32	.text+0x298b

```

## 03_zlib_deflate/no_retpoline/func_pgot: fill_window, a78, pgot_memcpy_table_func_pgot

```asm
     a72:	mov    %rbx,%rdx
     a75:	mov    0x0(%rip),%rax        # a7c <fill_window+0x10c>
			a78: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     a7c:	call   *%rax
     a7e:	mov    -0x70(%rbp),%rax
     a82:	mov    -0x58(%rbp),%rcx
     a86:	add    %rbx,(%rax)
     a89:	add    %rbx,0x10(%rax)
     a8d:	mov    -0x74(%rbp),%eax
     a90:	add    0x9c(%rcx),%eax
     a96:	mov    %eax,-0x5c(%rbp)
     a99:	mov    -0x58(%rbp),%rdi
     a9d:	mov    -0x5c(%rbp),%eax
     aa0:	mov    %eax,0x9c(%rdi)
     aa6:	cmp    $0x2,%eax
     aa9:	jbe    af0 <fill_window+0x180>
     aab:	mov    0x94(%rdi),%ecx
     ab1:	mov    0x48(%rdi),%rax
     ab5:	mov    %rcx,%rdx
```

## 03_zlib_deflate/no_retpoline/func_pgot: fill_window, d20, pgot_memcpy_table_func_pgot

```asm
     d1a:	mov    %rcx,%r14
     d1d:	mov    0x0(%rip),%rax        # d24 <fill_window+0x3b4>
			d20: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     d24:	lea    (%rdi,%r15,1),%rsi
     d28:	mov    %r15,%rdx
     d2b:	call   *%rax
     d2d:	mov    0x6c(%r14),%ecx
     d31:	mov    -0x94(%rbp),%r8d
     d38:	xor    %esi,%esi
     d3a:	mov    0x60(%r14),%rax
     d3e:	sub    %r8d,0x98(%r14)
     d45:	mov    %rcx,%rdx
     d48:	sub    %r8d,0x94(%r14)
     d4f:	sub    %r15,0x80(%r14)
     d56:	sub    $0x1,%edx
     d59:	lea    (%rax,%rcx,2),%rax
     d5d:	not    %rdx
     d60:	lea    (%rax,%rdx,2),%rdi
     d64:	movzwl -0x2(%rax),%ecx
```

## 03_zlib_deflate/no_retpoline/func_pgot: pgot_zlib_deflateReset_func_pgot, 3339, pgot_memset_table_func_pgot

```asm
    3333:	lea    -0x1(%rax),%edx
    3336:	mov    0x0(%rip),%rax        # 333d <pgot_zlib_deflateReset_func_pgot+0xad>
			3339: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    333d:	add    %rdx,%rdx
    3340:	call   *%rax
    3342:	movslq 0xac(%rbx),%r12
    3349:	cmp    $0x9,%r12
    334d:	ja     3433 <pgot_zlib_deflateReset_func_pgot+0x1a3>
    3353:	mov    %r12,%rax
    3356:	shl    $0x4,%rax
    335a:	movzwl 0x0(%rax),%eax
			335d: R_X86_64_32S	.rodata+0x182
    3361:	mov    %eax,0xa8(%rbx)
    3367:	cmp    $0x9,%r12
    336b:	ja     3447 <pgot_zlib_deflateReset_func_pgot+0x1b7>
    3371:	mov    %r12,%rax
    3374:	shl    $0x4,%rax
    3378:	movzwl 0x0(%rax),%eax
			337b: R_X86_64_32S	.rodata+0x180
```

## 03_zlib_deflate/no_retpoline/func_pgot: pgot_zlib_tr_stored_block_func_pgot, 378a, pgot_memcpy_table_func_pgot

```asm
    3783:	movslq 0x28(%rbx),%rdi
    3787:	mov    0x0(%rip),%rax        # 378e <pgot_zlib_tr_stored_block_func_pgot+0x17e>
			378a: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    378e:	add    0x10(%rbx),%rdi
    3792:	call   *%rax
    3794:	add    %r12d,0x28(%rbx)
    3798:	add    $0x8,%rsp
    379c:	pop    %rbx
    379d:	pop    %r12
    379f:	pop    %r13
    37a1:	pop    %r14
    37a3:	pop    %rbp
    37a4:	ret    
    37a5:	int3   
    37a6:	cmp    $0x1f,%ecx
    37a9:	ja     37af <pgot_zlib_tr_stored_block_func_pgot+0x19f>
			37ab: R_X86_64_PC32	.text.unlikely+0xa06
    37af:	mov    %ecx,%eax
    37b1:	mov    %r13d,%edx
```

## 03_zlib_deflate/no_retpoline/func_pgot: pgot_zlib_deflate_func_pgot, 3e5d, pgot_memset_table_func_pgot

```asm
    3e57:	lea    -0x1(%rax),%edx
    3e5a:	mov    0x0(%rip),%rax        # 3e61 <pgot_zlib_deflate_func_pgot+0x151>
			3e5d: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    3e61:	add    %rdx,%rdx
    3e64:	call   *%rax
    3e66:	mov    0x38(%r12),%r15
    3e6b:	mov    0x20(%r12),%rax
    3e70:	mov    0x28(%r15),%edx
    3e74:	mov    %rdx,%r14
    3e77:	cmp    %rax,%rdx
    3e7a:	cmova  %eax,%r14d
    3e7e:	test   %r14d,%r14d
    3e81:	je     3ec7 <pgot_zlib_deflate_func_pgot+0x1b7>
    3e83:	mov    0x18(%r12),%rdi
    3e88:	mov    %r14d,%edx
    3e8b:	test   %rdi,%rdi
    3e8e:	je     3ea6 <pgot_zlib_deflate_func_pgot+0x196>
    3e90:	mov    0x20(%r15),%rsi
    3e94:	mov    %rdx,-0x38(%rbp)
```

## 03_zlib_deflate/no_retpoline/func_pgot: pgot_zlib_deflate_func_pgot, 3e99, memcpy

```asm
    3e94:	mov    %rdx,-0x38(%rbp)
    3e98:	call   3e9d <pgot_zlib_deflate_func_pgot+0x18d>
			3e99: R_X86_64_PLT32	memcpy-0x4
    3e9d:	mov    -0x38(%rbp),%rdx
    3ea1:	add    %rdx,0x18(%r12)
    3ea6:	add    %rdx,0x20(%r15)
    3eaa:	add    %rdx,0x28(%r12)
    3eaf:	sub    %rdx,0x20(%r12)
    3eb4:	sub    %r14d,0x28(%r15)
    3eb8:	jne    3ec2 <pgot_zlib_deflate_func_pgot+0x1b2>
    3eba:	mov    0x10(%r15),%rax
    3ebe:	mov    %rax,0x20(%r15)
    3ec2:	mov    0x20(%r12),%rax
    3ec7:	test   %rax,%rax
    3eca:	je     40b0 <pgot_zlib_deflate_func_pgot+0x3a0>
    3ed0:	cmp    $0x5,%r13d
    3ed4:	jne    3f30 <pgot_zlib_deflate_func_pgot+0x220>
    3ed6:	mov    -0x30(%rbp),%rdi
    3eda:	mov    $0x1,%eax
```

## 03_zlib_deflate/no_retpoline/func_pgot: pgot_zlib_deflate_func_pgot, 4027, memcpy

```asm
    4022:	mov    %rdx,-0x38(%rbp)
    4026:	call   402b <pgot_zlib_deflate_func_pgot+0x31b>
			4027: R_X86_64_PLT32	memcpy-0x4
    402b:	mov    -0x38(%rbp),%rdx
    402f:	add    %rdx,0x18(%r12)
    4034:	add    %rdx,0x20(%r15)
    4038:	add    %rdx,0x28(%r12)
    403d:	sub    %rdx,0x20(%r12)
    4042:	sub    %r14d,0x28(%r15)
    4046:	je     41c6 <pgot_zlib_deflate_func_pgot+0x4b6>
    404c:	mov    0x20(%r12),%rax
    4051:	test   %rax,%rax
    4054:	je     40b0 <pgot_zlib_deflate_func_pgot+0x3a0>
    4056:	mov    -0x30(%rbp),%rdx
    405a:	mov    0x8(%r12),%rax
    405f:	cmpl   $0x29a,0x8(%rdx)
    4066:	jne    40ca <pgot_zlib_deflate_func_pgot+0x3ba>
    4068:	test   %rax,%rax
    406b:	je     3f18 <pgot_zlib_deflate_func_pgot+0x208>
```

## 03_zlib_deflate/no_retpoline/func_pgot: pgot_zlib_deflate_func_pgot, 417c, memcpy

```asm
    4178:	mov    %r15,%rdx
    417b:	call   4180 <pgot_zlib_deflate_func_pgot+0x470>
			417c: R_X86_64_PLT32	memcpy-0x4
    4180:	add    %r15,0x18(%r12)
    4185:	add    %r15,0x20(%r14)
    4189:	add    %r15,0x28(%r12)
    418e:	sub    %r15,0x20(%r12)
    4193:	sub    %r13d,0x28(%r14)
    4197:	jne    41a1 <pgot_zlib_deflate_func_pgot+0x491>
    4199:	mov    0x10(%r14),%rax
    419d:	mov    %rax,0x20(%r14)
    41a1:	mov    -0x30(%rbp),%rax
    41a5:	mov    0x28(%rax),%edx
    41a8:	movl   $0xffffffff,0x2c(%rax)
    41af:	xor    %eax,%eax
    41b1:	test   %edx,%edx
    41b3:	sete   %al
    41b6:	add    $0x10,%rsp
    41ba:	pop    %rbx
```

## 03_zlib_deflate/no_retpoline/func_pgot: deflate_stored, 4e6d, memcpy

```asm
    4e68:	mov    %rdx,-0x30(%rbp)
    4e6c:	call   4e71 <deflate_stored+0xd1>
			4e6d: R_X86_64_PLT32	memcpy-0x4
    4e71:	mov    -0x30(%rbp),%rdx
    4e75:	add    %rdx,0x18(%r14)
    4e79:	add    %rdx,0x20(%r13)
    4e7d:	add    %rdx,0x28(%r14)
    4e81:	sub    %rdx,0x20(%r14)
    4e85:	sub    %r15d,0x28(%r13)
    4e89:	jne    4e93 <deflate_stored+0xf3>
    4e8b:	mov    0x10(%r13),%rax
    4e8f:	mov    %rax,0x20(%r13)
    4e93:	mov    (%rbx),%rax
    4e96:	mov    0x20(%rax),%rax
    4e9a:	test   %rax,%rax
    4e9d:	je     5053 <deflate_stored+0x2b3>
    4ea3:	mov    0x94(%rbx),%eax
    4ea9:	mov    0x80(%rbx),%rcx
    4eb0:	mov    0x38(%rbx),%edi
```

## 03_zlib_deflate/no_retpoline/func_pgot: deflate_stored, 4f6b, memcpy

```asm
    4f66:	mov    %rdx,-0x30(%rbp)
    4f6a:	call   4f6f <deflate_stored+0x1cf>
			4f6b: R_X86_64_PLT32	memcpy-0x4
    4f6f:	mov    -0x30(%rbp),%rdx
    4f73:	add    %rdx,0x18(%r14)
    4f77:	mov    -0x40(%rbp),%rcx
    4f7b:	add    %rdx,0x20(%rcx)
    4f7f:	add    %rdx,0x28(%r14)
    4f83:	sub    %rdx,0x20(%r14)
    4f87:	sub    %r15d,0x28(%rcx)
    4f8b:	jne    4f95 <deflate_stored+0x1f5>
    4f8d:	mov    0x10(%rcx),%rax
    4f91:	mov    %rax,0x20(%rcx)
    4f95:	mov    (%rbx),%rax
    4f98:	mov    0x20(%rax),%rax
    4f9c:	test   %rax,%rax
    4f9f:	je     506f <deflate_stored+0x2cf>
    4fa5:	xor    %eax,%eax
    4fa7:	cmpl   $0x5,-0x34(%rbp)
```

## 03_zlib_deflate/no_retpoline/func_pgot: deflate_stored, 5021, memcpy

```asm
    501c:	mov    %rdx,-0x30(%rbp)
    5020:	call   5025 <deflate_stored+0x285>
			5021: R_X86_64_PLT32	memcpy-0x4
    5025:	mov    -0x30(%rbp),%rdx
    5029:	add    %rdx,0x18(%r14)
    502d:	mov    -0x40(%rbp),%rcx
    5031:	add    %rdx,0x20(%rcx)
    5035:	add    %rdx,0x28(%r14)
    5039:	sub    %rdx,0x20(%r14)
    503d:	sub    %r15d,0x28(%rcx)
    5041:	je     5065 <deflate_stored+0x2c5>
    5043:	mov    (%rbx),%rax
    5046:	mov    0x20(%rax),%rax
    504a:	test   %rax,%rax
    504d:	jne    4ec5 <deflate_stored+0x125>
    5053:	xor    %eax,%eax
    5055:	add    $0x18,%rsp
    5059:	pop    %rbx
    505a:	pop    %r12
```

## 03_zlib_deflate/no_retpoline/func_pgot: deflate_slow, 5552, memcpy

```asm
    554d:	mov    %rdx,-0x30(%rbp)
    5551:	call   5556 <deflate_slow+0x246>
			5552: R_X86_64_PLT32	memcpy-0x4
    5556:	mov    -0x30(%rbp),%rdx
    555a:	add    %rdx,0x18(%r13)
    555e:	mov    -0x38(%rbp),%rcx
    5562:	add    %rdx,0x20(%rcx)
    5566:	add    %rdx,0x28(%r13)
    556a:	sub    %rdx,0x20(%r13)
    556e:	sub    %r15d,0x28(%rcx)
    5572:	jne    557c <deflate_slow+0x26c>
    5574:	mov    0x10(%rcx),%rax
    5578:	mov    %rax,0x20(%rcx)
    557c:	mov    (%rbx),%rax
    557f:	mov    0x20(%rax),%rax
    5583:	test   %rax,%rax
    5586:	je     5706 <deflate_slow+0x3f6>
    558c:	mov    0x9c(%rbx),%eax
    5592:	cmp    $0x105,%eax
```

## 03_zlib_deflate/no_retpoline/func_pgot: deflate_slow, 56b1, memcpy

```asm
    56ac:	mov    %r8,-0x30(%rbp)
    56b0:	call   56b5 <deflate_slow+0x3a5>
			56b1: R_X86_64_PLT32	memcpy-0x4
    56b5:	add    %r13,0x18(%r15)
    56b9:	mov    -0x38(%rbp),%ecx
    56bc:	mov    -0x30(%rbp),%r8
    56c0:	add    %r13,0x20(%r8)
    56c4:	add    %r13,0x28(%r15)
    56c8:	sub    %r13,0x20(%r15)
    56cc:	sub    %ecx,0x28(%r8)
    56d0:	jne    56da <deflate_slow+0x3ca>
    56d2:	mov    0x10(%r8),%rax
    56d6:	mov    %rax,0x20(%r8)
    56da:	mov    0x94(%rbx),%eax
    56e0:	mov    (%rbx),%r15
    56e3:	add    $0x1,%eax
    56e6:	mov    %eax,0x94(%rbx)
    56ec:	mov    0x9c(%rbx),%eax
    56f2:	sub    $0x1,%eax
```

## 03_zlib_deflate/no_retpoline/func_pgot: deflate_slow, 57f5, memcpy

```asm
    57f0:	mov    %rdx,-0x30(%rbp)
    57f4:	call   57f9 <deflate_slow+0x4e9>
			57f5: R_X86_64_PLT32	memcpy-0x4
    57f9:	mov    -0x30(%rbp),%rdx
    57fd:	add    %rdx,0x18(%r14)
    5801:	mov    -0x38(%rbp),%rcx
    5805:	add    %rdx,0x20(%rcx)
    5809:	add    %rdx,0x28(%r14)
    580d:	sub    %rdx,0x20(%r14)
    5811:	sub    %r15d,0x28(%rcx)
    5815:	je     5840 <deflate_slow+0x530>
    5817:	mov    (%rbx),%rax
    581a:	mov    0x20(%rax),%rax
    581e:	test   %rax,%rax
    5821:	je     5874 <deflate_slow+0x564>
    5823:	xor    %eax,%eax
    5825:	cmp    $0x5,%r12d
    5829:	sete   %al
    582c:	add    $0x10,%rsp
```

## 03_zlib_deflate/no_retpoline/func_pgot: deflate_fast, 5a54, memcpy

```asm
    5a4f:	mov    %rdx,-0x30(%rbp)
    5a53:	call   5a58 <deflate_fast+0x1c8>
			5a54: R_X86_64_PLT32	memcpy-0x4
    5a58:	mov    -0x30(%rbp),%rdx
    5a5c:	add    %rdx,0x18(%r13)
    5a60:	add    %rdx,0x20(%r12)
    5a65:	add    %rdx,0x28(%r13)
    5a69:	sub    %rdx,0x20(%r13)
    5a6d:	sub    %r15d,0x28(%r12)
    5a72:	jne    5a7e <deflate_fast+0x1ee>
    5a74:	mov    0x10(%r12),%rax
    5a79:	mov    %rax,0x20(%r12)
    5a7e:	mov    (%rbx),%rax
    5a81:	mov    0x20(%rax),%rax
    5a85:	test   %rax,%rax
    5a88:	jne    58af <deflate_fast+0x1f>
    5a8e:	add    $0x18,%rsp
    5a92:	xor    %eax,%eax
    5a94:	pop    %rbx
```

## 03_zlib_deflate/no_retpoline/func_pgot: deflate_fast, 5bf9, memcpy

```asm
    5bf4:	mov    %rdx,-0x30(%rbp)
    5bf8:	call   5bfd <deflate_fast+0x36d>
			5bf9: R_X86_64_PLT32	memcpy-0x4
    5bfd:	mov    -0x30(%rbp),%rdx
    5c01:	add    %rdx,0x18(%r14)
    5c05:	mov    -0x40(%rbp),%rcx
    5c09:	add    %rdx,0x20(%rcx)
    5c0d:	add    %rdx,0x28(%r14)
    5c11:	sub    %rdx,0x20(%r14)
    5c15:	sub    %r15d,0x28(%rcx)
    5c19:	je     5c44 <deflate_fast+0x3b4>
    5c1b:	mov    (%rbx),%rax
    5c1e:	mov    0x20(%rax),%rax
    5c22:	test   %rax,%rax
    5c25:	je     5c4e <deflate_fast+0x3be>
    5c27:	xor    %eax,%eax
    5c29:	cmpl   $0x5,-0x34(%rbp)
    5c2d:	sete   %al
    5c30:	add    $0x18,%rsp
```

## 03_zlib_deflate/no_retpoline/origin: fill_window, 2546, memcpy

```asm
    2542:	add    %rax,%rdi
    2545:	call   254a <fill_window+0x10a>
			2546: R_X86_64_PLT32	memcpy-0x4
    254a:	mov    -0x70(%rbp),%rcx
    254e:	mov    -0x74(%rbp),%eax
    2551:	add    %rbx,(%rcx)
    2554:	add    %rbx,0x10(%rcx)
    2558:	mov    -0x58(%rbp),%rbx
    255c:	add    0x9c(%rbx),%eax
    2562:	mov    %eax,-0x5c(%rbp)
    2565:	mov    -0x58(%rbp),%rdi
    2569:	mov    -0x5c(%rbp),%eax
    256c:	mov    %eax,0x9c(%rdi)
    2572:	cmp    $0x2,%eax
    2575:	jbe    25bc <fill_window+0x17c>
    2577:	mov    0x94(%rdi),%ecx
    257d:	mov    0x48(%rdi),%rax
    2581:	mov    %rcx,%rdx
    2584:	movzbl (%rax,%rcx,1),%ebx
```

## 03_zlib_deflate/no_retpoline/origin: fill_window, 27f1, memcpy

```asm
    27ed:	mov    %r15,%rdx
    27f0:	call   27f5 <fill_window+0x3b5>
			27f1: R_X86_64_PLT32	memcpy-0x4
    27f5:	mov    0x6c(%r14),%ecx
    27f9:	mov    0x60(%r14),%rax
    27fd:	xor    %esi,%esi
    27ff:	mov    -0x94(%rbp),%r8d
    2806:	sub    %r15,0x80(%r14)
    280d:	mov    %rcx,%rdx
    2810:	sub    %r8d,0x98(%r14)
    2817:	lea    (%rax,%rcx,2),%rax
    281b:	sub    %r8d,0x94(%r14)
    2822:	sub    $0x1,%edx
    2825:	not    %rdx
    2828:	lea    (%rax,%rdx,2),%rdi
    282c:	movzwl -0x2(%rax),%ecx
    2830:	sub    $0x2,%rax
    2834:	mov    %ecx,%edx
    2836:	sub    %r8d,%edx
```

## 03_zlib_deflate/no_retpoline/origin: pgot_zlib_deflateReset_origin, 333a, memset

```asm
    3336:	add    %rdx,%rdx
    3339:	call   333e <pgot_zlib_deflateReset_origin+0xae>
			333a: R_X86_64_PLT32	memset-0x4
    333e:	movslq 0xac(%rbx),%r12
    3345:	cmp    $0x9,%r12
    3349:	ja     342f <pgot_zlib_deflateReset_origin+0x19f>
    334f:	mov    %r12,%rax
    3352:	shl    $0x4,%rax
    3356:	movzwl 0x0(%rax),%eax
			3359: R_X86_64_32S	.rodata+0x182
    335d:	mov    %eax,0xa8(%rbx)
    3363:	cmp    $0x9,%r12
    3367:	ja     3443 <pgot_zlib_deflateReset_origin+0x1b3>
    336d:	mov    %r12,%rax
    3370:	shl    $0x4,%rax
    3374:	movzwl 0x0(%rax),%eax
			3377: R_X86_64_32S	.rodata+0x180
    337b:	mov    %eax,0xb4(%rbx)
    3381:	cmp    $0x9,%r12
```

## 03_zlib_deflate/no_retpoline/origin: pgot_zlib_tr_stored_block_origin, 378c, memcpy

```asm
    3787:	add    0x10(%rbx),%rdi
    378b:	call   3790 <pgot_zlib_tr_stored_block_origin+0x180>
			378c: R_X86_64_PLT32	memcpy-0x4
    3790:	add    %r12d,0x28(%rbx)
    3794:	add    $0x8,%rsp
    3798:	pop    %rbx
    3799:	pop    %r12
    379b:	pop    %r13
    379d:	pop    %r14
    379f:	pop    %rbp
    37a0:	ret    
    37a1:	int3   
    37a2:	cmp    $0x1f,%ecx
    37a5:	ja     37ab <pgot_zlib_tr_stored_block_origin+0x19b>
			37a7: R_X86_64_PC32	.text.unlikely+0xa06
    37ab:	mov    %ecx,%eax
    37ad:	mov    %r13d,%edx
    37b0:	shl    %cl,%edx
    37b2:	lea    0x3(%rax),%ecx
```

## 03_zlib_deflate/no_retpoline/origin: pgot_zlib_deflate_origin, 3e5e, memset

```asm
    3e5a:	add    %rdx,%rdx
    3e5d:	call   3e62 <pgot_zlib_deflate_origin+0x152>
			3e5e: R_X86_64_PLT32	memset-0x4
    3e62:	mov    0x38(%r12),%r15
    3e67:	mov    0x20(%r12),%rax
    3e6c:	mov    0x28(%r15),%edx
    3e70:	mov    %rdx,%r14
    3e73:	cmp    %rax,%rdx
    3e76:	cmova  %eax,%r14d
    3e7a:	test   %r14d,%r14d
    3e7d:	je     3ec3 <pgot_zlib_deflate_origin+0x1b3>
    3e7f:	mov    0x18(%r12),%rdi
    3e84:	mov    %r14d,%edx
    3e87:	test   %rdi,%rdi
    3e8a:	je     3ea2 <pgot_zlib_deflate_origin+0x192>
    3e8c:	mov    0x20(%r15),%rsi
    3e90:	mov    %rdx,-0x38(%rbp)
    3e94:	call   3e99 <pgot_zlib_deflate_origin+0x189>
			3e95: R_X86_64_PLT32	memcpy-0x4
```

## 03_zlib_deflate/no_retpoline/origin: pgot_zlib_deflate_origin, 3e95, memcpy

```asm
    3e90:	mov    %rdx,-0x38(%rbp)
    3e94:	call   3e99 <pgot_zlib_deflate_origin+0x189>
			3e95: R_X86_64_PLT32	memcpy-0x4
    3e99:	mov    -0x38(%rbp),%rdx
    3e9d:	add    %rdx,0x18(%r12)
    3ea2:	add    %rdx,0x20(%r15)
    3ea6:	add    %rdx,0x28(%r12)
    3eab:	sub    %rdx,0x20(%r12)
    3eb0:	sub    %r14d,0x28(%r15)
    3eb4:	jne    3ebe <pgot_zlib_deflate_origin+0x1ae>
    3eb6:	mov    0x10(%r15),%rax
    3eba:	mov    %rax,0x20(%r15)
    3ebe:	mov    0x20(%r12),%rax
    3ec3:	test   %rax,%rax
    3ec6:	je     40ac <pgot_zlib_deflate_origin+0x39c>
    3ecc:	cmp    $0x5,%r13d
    3ed0:	jne    3f2c <pgot_zlib_deflate_origin+0x21c>
    3ed2:	mov    -0x30(%rbp),%rdi
    3ed6:	mov    $0x1,%eax
```

## 03_zlib_deflate/no_retpoline/origin: pgot_zlib_deflate_origin, 4023, memcpy

```asm
    401e:	mov    %rdx,-0x38(%rbp)
    4022:	call   4027 <pgot_zlib_deflate_origin+0x317>
			4023: R_X86_64_PLT32	memcpy-0x4
    4027:	mov    -0x38(%rbp),%rdx
    402b:	add    %rdx,0x18(%r12)
    4030:	add    %rdx,0x20(%r15)
    4034:	add    %rdx,0x28(%r12)
    4039:	sub    %rdx,0x20(%r12)
    403e:	sub    %r14d,0x28(%r15)
    4042:	je     41c2 <pgot_zlib_deflate_origin+0x4b2>
    4048:	mov    0x20(%r12),%rax
    404d:	test   %rax,%rax
    4050:	je     40ac <pgot_zlib_deflate_origin+0x39c>
    4052:	mov    -0x30(%rbp),%rdx
    4056:	mov    0x8(%r12),%rax
    405b:	cmpl   $0x29a,0x8(%rdx)
    4062:	jne    40c6 <pgot_zlib_deflate_origin+0x3b6>
    4064:	test   %rax,%rax
    4067:	je     3f14 <pgot_zlib_deflate_origin+0x204>
```

## 03_zlib_deflate/no_retpoline/origin: pgot_zlib_deflate_origin, 4178, memcpy

```asm
    4174:	mov    %r15,%rdx
    4177:	call   417c <pgot_zlib_deflate_origin+0x46c>
			4178: R_X86_64_PLT32	memcpy-0x4
    417c:	add    %r15,0x18(%r12)
    4181:	add    %r15,0x20(%r14)
    4185:	add    %r15,0x28(%r12)
    418a:	sub    %r15,0x20(%r12)
    418f:	sub    %r13d,0x28(%r14)
    4193:	jne    419d <pgot_zlib_deflate_origin+0x48d>
    4195:	mov    0x10(%r14),%rax
    4199:	mov    %rax,0x20(%r14)
    419d:	mov    -0x30(%rbp),%rax
    41a1:	mov    0x28(%rax),%edx
    41a4:	movl   $0xffffffff,0x2c(%rax)
    41ab:	xor    %eax,%eax
    41ad:	test   %edx,%edx
    41af:	sete   %al
    41b2:	add    $0x10,%rsp
    41b6:	pop    %rbx
```

## 03_zlib_deflate/no_retpoline/origin: deflate_stored, 4e5d, memcpy

```asm
    4e58:	mov    %rdx,-0x30(%rbp)
    4e5c:	call   4e61 <deflate_stored+0xd1>
			4e5d: R_X86_64_PLT32	memcpy-0x4
    4e61:	mov    -0x30(%rbp),%rdx
    4e65:	add    %rdx,0x18(%r14)
    4e69:	add    %rdx,0x20(%r13)
    4e6d:	add    %rdx,0x28(%r14)
    4e71:	sub    %rdx,0x20(%r14)
    4e75:	sub    %r15d,0x28(%r13)
    4e79:	jne    4e83 <deflate_stored+0xf3>
    4e7b:	mov    0x10(%r13),%rax
    4e7f:	mov    %rax,0x20(%r13)
    4e83:	mov    (%rbx),%rax
    4e86:	mov    0x20(%rax),%rax
    4e8a:	test   %rax,%rax
    4e8d:	je     5043 <deflate_stored+0x2b3>
    4e93:	mov    0x94(%rbx),%eax
    4e99:	mov    0x80(%rbx),%rcx
    4ea0:	mov    0x38(%rbx),%edi
```

## 03_zlib_deflate/no_retpoline/origin: deflate_stored, 4f5b, memcpy

```asm
    4f56:	mov    %rdx,-0x30(%rbp)
    4f5a:	call   4f5f <deflate_stored+0x1cf>
			4f5b: R_X86_64_PLT32	memcpy-0x4
    4f5f:	mov    -0x30(%rbp),%rdx
    4f63:	add    %rdx,0x18(%r14)
    4f67:	mov    -0x40(%rbp),%rcx
    4f6b:	add    %rdx,0x20(%rcx)
    4f6f:	add    %rdx,0x28(%r14)
    4f73:	sub    %rdx,0x20(%r14)
    4f77:	sub    %r15d,0x28(%rcx)
    4f7b:	jne    4f85 <deflate_stored+0x1f5>
    4f7d:	mov    0x10(%rcx),%rax
    4f81:	mov    %rax,0x20(%rcx)
    4f85:	mov    (%rbx),%rax
    4f88:	mov    0x20(%rax),%rax
    4f8c:	test   %rax,%rax
    4f8f:	je     505f <deflate_stored+0x2cf>
    4f95:	xor    %eax,%eax
    4f97:	cmpl   $0x5,-0x34(%rbp)
```

## 03_zlib_deflate/no_retpoline/origin: deflate_stored, 5011, memcpy

```asm
    500c:	mov    %rdx,-0x30(%rbp)
    5010:	call   5015 <deflate_stored+0x285>
			5011: R_X86_64_PLT32	memcpy-0x4
    5015:	mov    -0x30(%rbp),%rdx
    5019:	add    %rdx,0x18(%r14)
    501d:	mov    -0x40(%rbp),%rcx
    5021:	add    %rdx,0x20(%rcx)
    5025:	add    %rdx,0x28(%r14)
    5029:	sub    %rdx,0x20(%r14)
    502d:	sub    %r15d,0x28(%rcx)
    5031:	je     5055 <deflate_stored+0x2c5>
    5033:	mov    (%rbx),%rax
    5036:	mov    0x20(%rax),%rax
    503a:	test   %rax,%rax
    503d:	jne    4eb5 <deflate_stored+0x125>
    5043:	xor    %eax,%eax
    5045:	add    $0x18,%rsp
    5049:	pop    %rbx
    504a:	pop    %r12
```

## 03_zlib_deflate/no_retpoline/origin: deflate_slow, 5542, memcpy

```asm
    553d:	mov    %rdx,-0x30(%rbp)
    5541:	call   5546 <deflate_slow+0x246>
			5542: R_X86_64_PLT32	memcpy-0x4
    5546:	mov    -0x30(%rbp),%rdx
    554a:	add    %rdx,0x18(%r13)
    554e:	mov    -0x38(%rbp),%rcx
    5552:	add    %rdx,0x20(%rcx)
    5556:	add    %rdx,0x28(%r13)
    555a:	sub    %rdx,0x20(%r13)
    555e:	sub    %r15d,0x28(%rcx)
    5562:	jne    556c <deflate_slow+0x26c>
    5564:	mov    0x10(%rcx),%rax
    5568:	mov    %rax,0x20(%rcx)
    556c:	mov    (%rbx),%rax
    556f:	mov    0x20(%rax),%rax
    5573:	test   %rax,%rax
    5576:	je     56f6 <deflate_slow+0x3f6>
    557c:	mov    0x9c(%rbx),%eax
    5582:	cmp    $0x105,%eax
```

## 03_zlib_deflate/no_retpoline/origin: deflate_slow, 56a1, memcpy

```asm
    569c:	mov    %r8,-0x30(%rbp)
    56a0:	call   56a5 <deflate_slow+0x3a5>
			56a1: R_X86_64_PLT32	memcpy-0x4
    56a5:	add    %r13,0x18(%r15)
    56a9:	mov    -0x38(%rbp),%ecx
    56ac:	mov    -0x30(%rbp),%r8
    56b0:	add    %r13,0x20(%r8)
    56b4:	add    %r13,0x28(%r15)
    56b8:	sub    %r13,0x20(%r15)
    56bc:	sub    %ecx,0x28(%r8)
    56c0:	jne    56ca <deflate_slow+0x3ca>
    56c2:	mov    0x10(%r8),%rax
    56c6:	mov    %rax,0x20(%r8)
    56ca:	mov    0x94(%rbx),%eax
    56d0:	mov    (%rbx),%r15
    56d3:	add    $0x1,%eax
    56d6:	mov    %eax,0x94(%rbx)
    56dc:	mov    0x9c(%rbx),%eax
    56e2:	sub    $0x1,%eax
```

## 03_zlib_deflate/no_retpoline/origin: deflate_slow, 57e5, memcpy

```asm
    57e0:	mov    %rdx,-0x30(%rbp)
    57e4:	call   57e9 <deflate_slow+0x4e9>
			57e5: R_X86_64_PLT32	memcpy-0x4
    57e9:	mov    -0x30(%rbp),%rdx
    57ed:	add    %rdx,0x18(%r14)
    57f1:	mov    -0x38(%rbp),%rcx
    57f5:	add    %rdx,0x20(%rcx)
    57f9:	add    %rdx,0x28(%r14)
    57fd:	sub    %rdx,0x20(%r14)
    5801:	sub    %r15d,0x28(%rcx)
    5805:	je     5830 <deflate_slow+0x530>
    5807:	mov    (%rbx),%rax
    580a:	mov    0x20(%rax),%rax
    580e:	test   %rax,%rax
    5811:	je     5864 <deflate_slow+0x564>
    5813:	xor    %eax,%eax
    5815:	cmp    $0x5,%r12d
    5819:	sete   %al
    581c:	add    $0x10,%rsp
```

## 03_zlib_deflate/no_retpoline/origin: deflate_fast, 5a44, memcpy

```asm
    5a3f:	mov    %rdx,-0x30(%rbp)
    5a43:	call   5a48 <deflate_fast+0x1c8>
			5a44: R_X86_64_PLT32	memcpy-0x4
    5a48:	mov    -0x30(%rbp),%rdx
    5a4c:	add    %rdx,0x18(%r13)
    5a50:	add    %rdx,0x20(%r12)
    5a55:	add    %rdx,0x28(%r13)
    5a59:	sub    %rdx,0x20(%r13)
    5a5d:	sub    %r15d,0x28(%r12)
    5a62:	jne    5a6e <deflate_fast+0x1ee>
    5a64:	mov    0x10(%r12),%rax
    5a69:	mov    %rax,0x20(%r12)
    5a6e:	mov    (%rbx),%rax
    5a71:	mov    0x20(%rax),%rax
    5a75:	test   %rax,%rax
    5a78:	jne    589f <deflate_fast+0x1f>
    5a7e:	add    $0x18,%rsp
    5a82:	xor    %eax,%eax
    5a84:	pop    %rbx
```

## 03_zlib_deflate/no_retpoline/origin: deflate_fast, 5be9, memcpy

```asm
    5be4:	mov    %rdx,-0x30(%rbp)
    5be8:	call   5bed <deflate_fast+0x36d>
			5be9: R_X86_64_PLT32	memcpy-0x4
    5bed:	mov    -0x30(%rbp),%rdx
    5bf1:	add    %rdx,0x18(%r14)
    5bf5:	mov    -0x40(%rbp),%rcx
    5bf9:	add    %rdx,0x20(%rcx)
    5bfd:	add    %rdx,0x28(%r14)
    5c01:	sub    %rdx,0x20(%r14)
    5c05:	sub    %r15d,0x28(%rcx)
    5c09:	je     5c34 <deflate_fast+0x3b4>
    5c0b:	mov    (%rbx),%rax
    5c0e:	mov    0x20(%rax),%rax
    5c12:	test   %rax,%rax
    5c15:	je     5c3e <deflate_fast+0x3be>
    5c17:	xor    %eax,%eax
    5c19:	cmpl   $0x5,-0x34(%rbp)
    5c1d:	sete   %al
    5c20:	add    $0x18,%rsp
```

## 03_zlib_deflate/retpoline/all_pgot: fill_window, a7c, pgot_memcpy_table_all_pgot

```asm
     a76:	mov    %rbx,%rdx
     a79:	mov    0x0(%rip),%rax        # a80 <fill_window+0x110>
			a7c: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     a80:	jmp    a94 <fill_window+0x124>
     a82:	call   a8e <fill_window+0x11e>
     a87:	pause  
     a89:	lfence 
     a8c:	jmp    a87 <fill_window+0x117>
     a8e:	mov    %rax,(%rsp)
     a92:	ret    
     a93:	int3   
     a94:	call   a82 <fill_window+0x112>
     a99:	mov    -0x70(%rbp),%rax
     a9d:	mov    -0x58(%rbp),%rcx
     aa1:	add    %rbx,(%rax)
     aa4:	add    %rbx,0x10(%rax)
     aa8:	mov    -0x74(%rbp),%eax
     aab:	add    0x9c(%rcx),%eax
     ab1:	mov    %eax,-0x5c(%rbp)
```

## 03_zlib_deflate/retpoline/all_pgot: fill_window, d3b, pgot_memcpy_table_all_pgot

```asm
     d35:	mov    %rcx,%r14
     d38:	mov    0x0(%rip),%rax        # d3f <fill_window+0x3cf>
			d3b: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     d3f:	lea    (%rdi,%r15,1),%rsi
     d43:	mov    %r15,%rdx
     d46:	jmp    d5a <fill_window+0x3ea>
     d48:	call   d54 <fill_window+0x3e4>
     d4d:	pause  
     d4f:	lfence 
     d52:	jmp    d4d <fill_window+0x3dd>
     d54:	mov    %rax,(%rsp)
     d58:	ret    
     d59:	int3   
     d5a:	call   d48 <fill_window+0x3d8>
     d5f:	mov    0x6c(%r14),%ecx
     d63:	mov    -0x94(%rbp),%r8d
     d6a:	xor    %esi,%esi
     d6c:	mov    0x60(%r14),%rax
     d70:	sub    %r8d,0x98(%r14)
```

## 03_zlib_deflate/retpoline/all_pgot: compress_block, 2393, pgot_length_code_all_pgot

```asm
    238a:	je     22c2 <compress_block+0x42>
    2390:	mov    0x0(%rip),%rdx        # 2397 <compress_block+0x117>
			2393: R_X86_64_PC32	pgot_length_code_all_pgot-0x4
    2397:	movzbl (%rdx,%rax,1),%eax
    239b:	mov    %r9d,%edx
    239e:	mov    %rax,%r15
    23a1:	lea    0x404(%r8,%rax,4),%rax
    23a9:	movzwl 0x2(%rax),%r10d
    23ae:	movzwl (%rax),%eax
    23b1:	sub    %r10d,%edx
    23b4:	mov    %eax,%r11d
    23b7:	cmp    %ecx,%edx
    23b9:	jge    270d <compress_block+0x48d>
    23bf:	cmp    $0x1f,%ecx
    23c2:	ja     23c8 <compress_block+0x148>
			23c4: R_X86_64_PC32	.text.unlikely+0x964
    23c8:	movslq 0x28(%rbx),%rdx
    23cc:	mov    %eax,%edi
    23ce:	mov    0x10(%rbx),%rsi
```

## 03_zlib_deflate/retpoline/all_pgot: compress_block, 2435, pgot_extra_lbits_all_pgot

```asm
    242b:	mov    %ax,0x1720(%rbx)
    2432:	mov    0x0(%rip),%rax        # 2439 <compress_block+0x1b9>
			2435: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
    2439:	mov    %ecx,0x1724(%rbx)
    243f:	mov    (%rax,%r15,4),%eax
    2443:	test   %eax,%eax
    2445:	je     24e2 <compress_block+0x262>
    244b:	mov    0x0(%rip),%rsi        # 2452 <compress_block+0x1d2>
			244e: R_X86_64_PC32	pgot_base_length_all_pgot-0x4
    2452:	sub    (%rsi,%r15,4),%r13d
    2456:	mov    %r9d,%esi
    2459:	sub    %eax,%esi
    245b:	cmp    %ecx,%esi
    245d:	jge    27b0 <compress_block+0x530>
    2463:	cmp    $0x1f,%edx
    2466:	ja     246c <compress_block+0x1ec>
			2468: R_X86_64_PC32	.text.unlikely+0x8f1
    246c:	movslq 0x28(%rbx),%rdx
    2470:	mov    %r13d,%edi
```

## 03_zlib_deflate/retpoline/all_pgot: compress_block, 244e, pgot_base_length_all_pgot

```asm
    2445:	je     24e2 <compress_block+0x262>
    244b:	mov    0x0(%rip),%rsi        # 2452 <compress_block+0x1d2>
			244e: R_X86_64_PC32	pgot_base_length_all_pgot-0x4
    2452:	sub    (%rsi,%r15,4),%r13d
    2456:	mov    %r9d,%esi
    2459:	sub    %eax,%esi
    245b:	cmp    %ecx,%esi
    245d:	jge    27b0 <compress_block+0x530>
    2463:	cmp    $0x1f,%edx
    2466:	ja     246c <compress_block+0x1ec>
			2468: R_X86_64_PC32	.text.unlikely+0x8f1
    246c:	movslq 0x28(%rbx),%rdx
    2470:	mov    %r13d,%edi
    2473:	mov    0x10(%rbx),%rsi
    2477:	movzwl %r13w,%r13d
    247b:	shl    %cl,%edi
    247d:	mov    %edi,%ecx
    247f:	lea    0x1(%rdx),%edi
    2482:	or     0x1720(%rbx),%cx
```

## 03_zlib_deflate/retpoline/all_pgot: compress_block, 24e9, pgot_dist_code_all_pgot

```asm
    24e2:	sub    $0x1,%r12d
    24e6:	mov    0x0(%rip),%rsi        # 24ed <compress_block+0x26d>
			24e9: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    24ed:	cmp    $0xff,%r12d
    24f4:	ja     274c <compress_block+0x4cc>
    24fa:	mov    %r12d,%eax
    24fd:	movzbl (%rsi,%rax,1),%r13d
    2502:	mov    -0x30(%rbp),%rax
    2506:	lea    (%rax,%r13,4),%rsi
    250a:	movzwl 0x2(%rsi),%eax
    250e:	movzwl (%rsi),%r15d
    2512:	mov    %r9d,%esi
    2515:	sub    %eax,%esi
    2517:	mov    %r15d,%r10d
    251a:	cmp    %ecx,%esi
    251c:	jge    272c <compress_block+0x4ac>
    2522:	cmp    $0x1f,%edx
    2525:	ja     252b <compress_block+0x2ab>
			2527: R_X86_64_PC32	.text.unlikely+0x87e
```

## 03_zlib_deflate/retpoline/all_pgot: compress_block, 2592, pgot_extra_dbits_all_pgot

```asm
    258d:	mov    %eax,%ecx
    258f:	mov    0x0(%rip),%rdx        # 2596 <compress_block+0x316>
			2592: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    2596:	mov    %r15w,0x1720(%rbx)
    259e:	mov    %ecx,0x1724(%rbx)
    25a4:	mov    (%rdx,%r13,4),%r15d
    25a8:	test   %r15d,%r15d
    25ab:	je     2359 <compress_block+0xd9>
    25b1:	mov    0x0(%rip),%rdx        # 25b8 <compress_block+0x338>
			25b4: R_X86_64_PC32	pgot_base_dist_all_pgot-0x4
    25b8:	sub    (%rdx,%r13,4),%r12d
    25bc:	mov    %r9d,%edx
    25bf:	sub    %r15d,%edx
    25c2:	cmp    %ecx,%edx
    25c4:	jge    2789 <compress_block+0x509>
    25ca:	cmp    $0x1f,%eax
    25cd:	ja     25d3 <compress_block+0x353>
			25cf: R_X86_64_PC32	.text.unlikely+0x816
    25d3:	movslq 0x28(%rbx),%rax
```

## 03_zlib_deflate/retpoline/all_pgot: compress_block, 25b4, pgot_base_dist_all_pgot

```asm
    25ab:	je     2359 <compress_block+0xd9>
    25b1:	mov    0x0(%rip),%rdx        # 25b8 <compress_block+0x338>
			25b4: R_X86_64_PC32	pgot_base_dist_all_pgot-0x4
    25b8:	sub    (%rdx,%r13,4),%r12d
    25bc:	mov    %r9d,%edx
    25bf:	sub    %r15d,%edx
    25c2:	cmp    %ecx,%edx
    25c4:	jge    2789 <compress_block+0x509>
    25ca:	cmp    $0x1f,%eax
    25cd:	ja     25d3 <compress_block+0x353>
			25cf: R_X86_64_PC32	.text.unlikely+0x816
    25d3:	movslq 0x28(%rbx),%rax
    25d7:	mov    %r12d,%edx
    25da:	movzwl %r12w,%r12d
    25de:	shl    %cl,%edx
    25e0:	mov    0x10(%rbx),%rcx
    25e4:	or     0x1720(%rbx),%dx
    25eb:	lea    0x1(%rax),%esi
    25ee:	mov    %dx,0x1720(%rbx)
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2917, pgot_base_length_all_pgot

```asm
    290e:	mov    $0x1,%r9d
    2914:	mov    0x0(%rip),%rax        # 291b <pgot_zlib_tr_init_all_pgot+0x4b>
			2917: R_X86_64_PC32	pgot_base_length_all_pgot-0x4
    291b:	lea    0x0(,%r14,4),%r8
    2923:	xor    %ebx,%ebx
    2925:	mov    %r15d,(%rax,%r14,4)
    2929:	jmp    293c <pgot_zlib_tr_init_all_pgot+0x6c>
    292b:	mov    0x0(%rip),%rax        # 2932 <pgot_zlib_tr_init_all_pgot+0x62>
			292e: R_X86_64_PC32	pgot_length_code_all_pgot-0x4
    2932:	movslq %r12d,%r12
    2935:	add    $0x1,%ebx
    2938:	mov    %r14b,(%rax,%r12,1)
    293c:	mov    0x0(%rip),%rax        # 2943 <pgot_zlib_tr_init_all_pgot+0x73>
			293f: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
    2943:	lea    (%rbx,%r15,1),%r12d
    2947:	mov    (%rax,%r8,1),%ecx
    294b:	cmp    $0x1f,%ecx
    294e:	ja     2954 <pgot_zlib_tr_init_all_pgot+0x84>
			2950: R_X86_64_PC32	.text.unlikely+0xa0a
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 292e, pgot_length_code_all_pgot

```asm
    2929:	jmp    293c <pgot_zlib_tr_init_all_pgot+0x6c>
    292b:	mov    0x0(%rip),%rax        # 2932 <pgot_zlib_tr_init_all_pgot+0x62>
			292e: R_X86_64_PC32	pgot_length_code_all_pgot-0x4
    2932:	movslq %r12d,%r12
    2935:	add    $0x1,%ebx
    2938:	mov    %r14b,(%rax,%r12,1)
    293c:	mov    0x0(%rip),%rax        # 2943 <pgot_zlib_tr_init_all_pgot+0x73>
			293f: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
    2943:	lea    (%rbx,%r15,1),%r12d
    2947:	mov    (%rax,%r8,1),%ecx
    294b:	cmp    $0x1f,%ecx
    294e:	ja     2954 <pgot_zlib_tr_init_all_pgot+0x84>
			2950: R_X86_64_PC32	.text.unlikely+0xa0a
    2954:	mov    %r9d,%eax
    2957:	shl    %cl,%eax
    2959:	cmp    %eax,%ebx
    295b:	jl     292b <pgot_zlib_tr_init_all_pgot+0x5b>
    295d:	add    $0x1,%r14
    2961:	cmp    $0x1c,%r14
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 293f, pgot_extra_lbits_all_pgot

```asm
    2938:	mov    %r14b,(%rax,%r12,1)
    293c:	mov    0x0(%rip),%rax        # 2943 <pgot_zlib_tr_init_all_pgot+0x73>
			293f: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
    2943:	lea    (%rbx,%r15,1),%r12d
    2947:	mov    (%rax,%r8,1),%ecx
    294b:	cmp    $0x1f,%ecx
    294e:	ja     2954 <pgot_zlib_tr_init_all_pgot+0x84>
			2950: R_X86_64_PC32	.text.unlikely+0xa0a
    2954:	mov    %r9d,%eax
    2957:	shl    %cl,%eax
    2959:	cmp    %eax,%ebx
    295b:	jl     292b <pgot_zlib_tr_init_all_pgot+0x5b>
    295d:	add    $0x1,%r14
    2961:	cmp    $0x1c,%r14
    2965:	je     2c5f <pgot_zlib_tr_init_all_pgot+0x38f>
    296b:	mov    %r12d,%r15d
    296e:	jmp    2914 <pgot_zlib_tr_init_all_pgot+0x44>
    2970:	sar    $0x7,%r12d
    2974:	mov    $0x40,%r14d
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2989, pgot_base_dist_all_pgot

```asm
    2980:	mov    $0x1,%r8d
    2986:	mov    0x0(%rip),%rax        # 298d <pgot_zlib_tr_init_all_pgot+0xbd>
			2989: R_X86_64_PC32	pgot_base_dist_all_pgot-0x4
    298d:	mov    %r12d,%edx
    2990:	mov    %r12d,%ebx
    2993:	shl    $0x7,%edx
    2996:	mov    %edx,(%rax,%r14,1)
    299a:	mov    %r12d,%eax
    299d:	jmp    29b5 <pgot_zlib_tr_init_all_pgot+0xe5>
    299f:	mov    0x0(%rip),%rdx        # 29a6 <pgot_zlib_tr_init_all_pgot+0xd6>
			29a2: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    29a6:	add    $0x100,%ebx
    29ac:	movslq %ebx,%rbx
    29af:	mov    %r15b,(%rdx,%rbx,1)
    29b3:	mov    %esi,%ebx
    29b5:	mov    0x0(%rip),%rdx        # 29bc <pgot_zlib_tr_init_all_pgot+0xec>
			29b8: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    29bc:	mov    %ebx,%r12d
    29bf:	mov    (%rdx,%r14,1),%ecx
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 29a2, pgot_dist_code_all_pgot

```asm
    299d:	jmp    29b5 <pgot_zlib_tr_init_all_pgot+0xe5>
    299f:	mov    0x0(%rip),%rdx        # 29a6 <pgot_zlib_tr_init_all_pgot+0xd6>
			29a2: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    29a6:	add    $0x100,%ebx
    29ac:	movslq %ebx,%rbx
    29af:	mov    %r15b,(%rdx,%rbx,1)
    29b3:	mov    %esi,%ebx
    29b5:	mov    0x0(%rip),%rdx        # 29bc <pgot_zlib_tr_init_all_pgot+0xec>
			29b8: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    29bc:	mov    %ebx,%r12d
    29bf:	mov    (%rdx,%r14,1),%ecx
    29c3:	sub    $0x7,%ecx
    29c6:	cmp    $0x1f,%ecx
    29c9:	ja     29cf <pgot_zlib_tr_init_all_pgot+0xff>
			29cb: R_X86_64_PC32	.text.unlikely+0xa3c
    29cf:	mov    %r8d,%edi
    29d2:	mov    %ebx,%edx
    29d4:	lea    0x1(%rbx),%esi
    29d7:	shl    %cl,%edi
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 29b8, pgot_extra_dbits_all_pgot

```asm
    29b3:	mov    %esi,%ebx
    29b5:	mov    0x0(%rip),%rdx        # 29bc <pgot_zlib_tr_init_all_pgot+0xec>
			29b8: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    29bc:	mov    %ebx,%r12d
    29bf:	mov    (%rdx,%r14,1),%ecx
    29c3:	sub    $0x7,%ecx
    29c6:	cmp    $0x1f,%ecx
    29c9:	ja     29cf <pgot_zlib_tr_init_all_pgot+0xff>
			29cb: R_X86_64_PC32	.text.unlikely+0xa3c
    29cf:	mov    %r8d,%edi
    29d2:	mov    %ebx,%edx
    29d4:	lea    0x1(%rbx),%esi
    29d7:	shl    %cl,%edi
    29d9:	sub    %eax,%edx
    29db:	cmp    %edx,%edi
    29dd:	jg     299f <pgot_zlib_tr_init_all_pgot+0xcf>
    29df:	add    $0x1,%r15d
    29e3:	add    $0x4,%r14
    29e7:	cmp    $0x1e,%r15d
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2a18, pgot_static_ltree_all_pgot

```asm
    2a13:	xor    %eax,%eax
    2a15:	mov    0x0(%rip),%rdx        # 2a1c <pgot_zlib_tr_init_all_pgot+0x14c>
			2a18: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a1c:	mov    $0x8,%ebx
    2a21:	mov    %bx,0x2(%rdx,%rax,1)
    2a26:	add    $0x4,%rax
    2a2a:	cmp    $0x240,%rax
    2a30:	jne    2a15 <pgot_zlib_tr_init_all_pgot+0x145>
    2a32:	movzwl -0x3e(%rbp),%esi
    2a36:	mov    0x0(%rip),%rdx        # 2a3d <pgot_zlib_tr_init_all_pgot+0x16d>
			2a39: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a3d:	mov    $0x9,%r11d
    2a43:	mov    %r11w,0x2(%rdx,%rax,1)
    2a49:	add    $0x4,%rax
    2a4d:	cmp    $0x400,%rax
    2a53:	jne    2a36 <pgot_zlib_tr_init_all_pgot+0x166>
    2a55:	lea    0x70(%rsi),%edx
    2a58:	movzwl -0x42(%rbp),%esi
    2a5c:	mov    %dx,-0x3e(%rbp)
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2a39, pgot_static_ltree_all_pgot

```asm
    2a32:	movzwl -0x3e(%rbp),%esi
    2a36:	mov    0x0(%rip),%rdx        # 2a3d <pgot_zlib_tr_init_all_pgot+0x16d>
			2a39: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a3d:	mov    $0x9,%r11d
    2a43:	mov    %r11w,0x2(%rdx,%rax,1)
    2a49:	add    $0x4,%rax
    2a4d:	cmp    $0x400,%rax
    2a53:	jne    2a36 <pgot_zlib_tr_init_all_pgot+0x166>
    2a55:	lea    0x70(%rsi),%edx
    2a58:	movzwl -0x42(%rbp),%esi
    2a5c:	mov    %dx,-0x3e(%rbp)
    2a60:	mov    0x0(%rip),%rdx        # 2a67 <pgot_zlib_tr_init_all_pgot+0x197>
			2a63: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a67:	mov    $0x7,%r10d
    2a6d:	mov    %r10w,0x2(%rdx,%rax,1)
    2a73:	add    $0x4,%rax
    2a77:	cmp    $0x460,%rax
    2a7d:	jne    2a60 <pgot_zlib_tr_init_all_pgot+0x190>
    2a7f:	lea    0x18(%rsi),%edx
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2a63, pgot_static_ltree_all_pgot

```asm
    2a5c:	mov    %dx,-0x3e(%rbp)
    2a60:	mov    0x0(%rip),%rdx        # 2a67 <pgot_zlib_tr_init_all_pgot+0x197>
			2a63: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a67:	mov    $0x7,%r10d
    2a6d:	mov    %r10w,0x2(%rdx,%rax,1)
    2a73:	add    $0x4,%rax
    2a77:	cmp    $0x460,%rax
    2a7d:	jne    2a60 <pgot_zlib_tr_init_all_pgot+0x190>
    2a7f:	lea    0x18(%rsi),%edx
    2a82:	mov    %dx,-0x42(%rbp)
    2a86:	mov    0x0(%rip),%rdx        # 2a8d <pgot_zlib_tr_init_all_pgot+0x1bd>
			2a89: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a8d:	mov    $0x8,%r9d
    2a93:	mov    %r9w,0x2(%rdx,%rax,1)
    2a99:	add    $0x4,%rax
    2a9d:	cmp    $0x480,%rax
    2aa3:	jne    2a86 <pgot_zlib_tr_init_all_pgot+0x1b6>
    2aa5:	mov    0x0(%rip),%rdi        # 2aac <pgot_zlib_tr_init_all_pgot+0x1dc>
			2aa8: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2a89, pgot_static_ltree_all_pgot

```asm
    2a82:	mov    %dx,-0x42(%rbp)
    2a86:	mov    0x0(%rip),%rdx        # 2a8d <pgot_zlib_tr_init_all_pgot+0x1bd>
			2a89: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2a8d:	mov    $0x8,%r9d
    2a93:	mov    %r9w,0x2(%rdx,%rax,1)
    2a99:	add    $0x4,%rax
    2a9d:	cmp    $0x480,%rax
    2aa3:	jne    2a86 <pgot_zlib_tr_init_all_pgot+0x1b6>
    2aa5:	mov    0x0(%rip),%rdi        # 2aac <pgot_zlib_tr_init_all_pgot+0x1dc>
			2aa8: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2aac:	lea    -0x50(%rbp),%rdx
    2ab0:	mov    $0x11f,%esi
    2ab5:	xor    %ebx,%ebx
    2ab7:	lea    0x98(%rcx),%eax
    2abd:	mov    %ax,-0x40(%rbp)
    2ac1:	call   e30 <gen_codes>
    2ac6:	mov    0x0(%rip),%rax        # 2acd <pgot_zlib_tr_init_all_pgot+0x1fd>
			2ac9: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    2acd:	lea    0x0(,%rbx,4),%r12
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2aa8, pgot_static_ltree_all_pgot

```asm
    2aa3:	jne    2a86 <pgot_zlib_tr_init_all_pgot+0x1b6>
    2aa5:	mov    0x0(%rip),%rdi        # 2aac <pgot_zlib_tr_init_all_pgot+0x1dc>
			2aa8: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    2aac:	lea    -0x50(%rbp),%rdx
    2ab0:	mov    $0x11f,%esi
    2ab5:	xor    %ebx,%ebx
    2ab7:	lea    0x98(%rcx),%eax
    2abd:	mov    %ax,-0x40(%rbp)
    2ac1:	call   e30 <gen_codes>
    2ac6:	mov    0x0(%rip),%rax        # 2acd <pgot_zlib_tr_init_all_pgot+0x1fd>
			2ac9: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    2acd:	lea    0x0(,%rbx,4),%r12
    2ad5:	mov    $0x5,%r8d
    2adb:	movslq %ebx,%rsi
    2ade:	mov    %r8w,0x2(%rax,%r12,1)
    2ae4:	cmp    $0xff,%rsi
    2aeb:	ja     2cea <pgot_zlib_tr_init_all_pgot+0x41a>
    2af1:	movzbl 0x0(%rbx),%eax
			2af4: R_X86_64_32S	byte_rev_table
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2ac9, pgot_static_dtree_all_pgot

```asm
    2ac1:	call   e30 <gen_codes>
    2ac6:	mov    0x0(%rip),%rax        # 2acd <pgot_zlib_tr_init_all_pgot+0x1fd>
			2ac9: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    2acd:	lea    0x0(,%rbx,4),%r12
    2ad5:	mov    $0x5,%r8d
    2adb:	movslq %ebx,%rsi
    2ade:	mov    %r8w,0x2(%rax,%r12,1)
    2ae4:	cmp    $0xff,%rsi
    2aeb:	ja     2cea <pgot_zlib_tr_init_all_pgot+0x41a>
    2af1:	movzbl 0x0(%rbx),%eax
			2af4: R_X86_64_32S	byte_rev_table
    2af8:	mov    0x0(%rip),%rdx        # 2aff <pgot_zlib_tr_init_all_pgot+0x22f>
			2afb: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    2aff:	add    $0x1,%rbx
    2b03:	shr    $0x3,%eax
    2b06:	mov    %ax,(%rdx,%r12,1)
    2b0b:	cmp    $0x1e,%rbx
    2b0f:	jne    2ac6 <pgot_zlib_tr_init_all_pgot+0x1f6>
    2b11:	movl   $0x1,0x0(%rip)        # 2b1b <pgot_zlib_tr_init_all_pgot+0x24b>
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2afb, pgot_static_dtree_all_pgot

```asm
			2af4: R_X86_64_32S	byte_rev_table
    2af8:	mov    0x0(%rip),%rdx        # 2aff <pgot_zlib_tr_init_all_pgot+0x22f>
			2afb: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    2aff:	add    $0x1,%rbx
    2b03:	shr    $0x3,%eax
    2b06:	mov    %ax,(%rdx,%r12,1)
    2b0b:	cmp    $0x1e,%rbx
    2b0f:	jne    2ac6 <pgot_zlib_tr_init_all_pgot+0x1f6>
    2b11:	movl   $0x1,0x0(%rip)        # 2b1b <pgot_zlib_tr_init_all_pgot+0x24b>
			2b13: R_X86_64_PC32	.bss-0x8
    2b1b:	lea    0xbc(%r13),%rax
    2b22:	xor    %edi,%edi
    2b24:	xor    %ebx,%ebx
    2b26:	movq   $0x0,0x1710(%r13)
    2b31:	mov    %rax,0xb40(%r13)
    2b38:	lea    0x9b0(%r13),%rax
    2b3f:	mov    %rax,0xb58(%r13)
    2b46:	lea    0xaa4(%r13),%rax
    2b4d:	movq   $0x0,0xb50(%r13)
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2c62, pgot_length_code_all_pgot

```asm
    2c5e:	int3   
    2c5f:	mov    0x0(%rip),%rdx        # 2c66 <pgot_zlib_tr_init_all_pgot+0x396>
			2c62: R_X86_64_PC32	pgot_length_code_all_pgot-0x4
    2c66:	lea    -0x1(%r12),%eax
    2c6b:	xor    %r15d,%r15d
    2c6e:	xor    %r14d,%r14d
    2c71:	cltq   
    2c73:	mov    $0x1,%r9d
    2c79:	movb   $0x1c,(%rdx,%rax,1)
    2c7d:	mov    0x0(%rip),%rax        # 2c84 <pgot_zlib_tr_init_all_pgot+0x3b4>
			2c80: R_X86_64_PC32	pgot_base_dist_all_pgot-0x4
    2c84:	lea    0x0(,%r14,4),%r8
    2c8c:	xor    %ebx,%ebx
    2c8e:	mov    %r15d,(%rax,%r14,4)
    2c92:	jmp    2ca5 <pgot_zlib_tr_init_all_pgot+0x3d5>
    2c94:	mov    0x0(%rip),%rax        # 2c9b <pgot_zlib_tr_init_all_pgot+0x3cb>
			2c97: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    2c9b:	movslq %r12d,%r12
    2c9e:	add    $0x1,%ebx
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2c80, pgot_base_dist_all_pgot

```asm
    2c79:	movb   $0x1c,(%rdx,%rax,1)
    2c7d:	mov    0x0(%rip),%rax        # 2c84 <pgot_zlib_tr_init_all_pgot+0x3b4>
			2c80: R_X86_64_PC32	pgot_base_dist_all_pgot-0x4
    2c84:	lea    0x0(,%r14,4),%r8
    2c8c:	xor    %ebx,%ebx
    2c8e:	mov    %r15d,(%rax,%r14,4)
    2c92:	jmp    2ca5 <pgot_zlib_tr_init_all_pgot+0x3d5>
    2c94:	mov    0x0(%rip),%rax        # 2c9b <pgot_zlib_tr_init_all_pgot+0x3cb>
			2c97: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    2c9b:	movslq %r12d,%r12
    2c9e:	add    $0x1,%ebx
    2ca1:	mov    %r14b,(%rax,%r12,1)
    2ca5:	mov    0x0(%rip),%rax        # 2cac <pgot_zlib_tr_init_all_pgot+0x3dc>
			2ca8: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    2cac:	lea    (%rbx,%r15,1),%r12d
    2cb0:	mov    (%rax,%r8,1),%ecx
    2cb4:	cmp    $0x1f,%ecx
    2cb7:	ja     2cbd <pgot_zlib_tr_init_all_pgot+0x3ed>
			2cb9: R_X86_64_PC32	.text.unlikely+0x9d8
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2c97, pgot_dist_code_all_pgot

```asm
    2c92:	jmp    2ca5 <pgot_zlib_tr_init_all_pgot+0x3d5>
    2c94:	mov    0x0(%rip),%rax        # 2c9b <pgot_zlib_tr_init_all_pgot+0x3cb>
			2c97: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    2c9b:	movslq %r12d,%r12
    2c9e:	add    $0x1,%ebx
    2ca1:	mov    %r14b,(%rax,%r12,1)
    2ca5:	mov    0x0(%rip),%rax        # 2cac <pgot_zlib_tr_init_all_pgot+0x3dc>
			2ca8: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    2cac:	lea    (%rbx,%r15,1),%r12d
    2cb0:	mov    (%rax,%r8,1),%ecx
    2cb4:	cmp    $0x1f,%ecx
    2cb7:	ja     2cbd <pgot_zlib_tr_init_all_pgot+0x3ed>
			2cb9: R_X86_64_PC32	.text.unlikely+0x9d8
    2cbd:	mov    %r9d,%eax
    2cc0:	shl    %cl,%eax
    2cc2:	cmp    %eax,%ebx
    2cc4:	jl     2c94 <pgot_zlib_tr_init_all_pgot+0x3c4>
    2cc6:	add    $0x1,%r14
    2cca:	cmp    $0x10,%r14
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot, 2ca8, pgot_extra_dbits_all_pgot

```asm
    2ca1:	mov    %r14b,(%rax,%r12,1)
    2ca5:	mov    0x0(%rip),%rax        # 2cac <pgot_zlib_tr_init_all_pgot+0x3dc>
			2ca8: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    2cac:	lea    (%rbx,%r15,1),%r12d
    2cb0:	mov    (%rax,%r8,1),%ecx
    2cb4:	cmp    $0x1f,%ecx
    2cb7:	ja     2cbd <pgot_zlib_tr_init_all_pgot+0x3ed>
			2cb9: R_X86_64_PC32	.text.unlikely+0x9d8
    2cbd:	mov    %r9d,%eax
    2cc0:	shl    %cl,%eax
    2cc2:	cmp    %eax,%ebx
    2cc4:	jl     2c94 <pgot_zlib_tr_init_all_pgot+0x3c4>
    2cc6:	add    $0x1,%r14
    2cca:	cmp    $0x10,%r14
    2cce:	je     2970 <pgot_zlib_tr_init_all_pgot+0xa0>
    2cd4:	mov    %r12d,%r15d
    2cd7:	jmp    2c7d <pgot_zlib_tr_init_all_pgot+0x3ad>
    2cd9:	mov    $0x0,%rdi
			2cdc: R_X86_64_32S	.data+0x200
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_deflateReset_all_pgot, 2de7, pgot_memset_table_all_pgot

```asm
    2de1:	lea    -0x1(%rax),%edx
    2de4:	mov    0x0(%rip),%rax        # 2deb <pgot_zlib_deflateReset_all_pgot+0xab>
			2de7: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    2deb:	add    %rdx,%rdx
    2dee:	jmp    2e02 <pgot_zlib_deflateReset_all_pgot+0xc2>
    2df0:	call   2dfc <pgot_zlib_deflateReset_all_pgot+0xbc>
    2df5:	pause  
    2df7:	lfence 
    2dfa:	jmp    2df5 <pgot_zlib_deflateReset_all_pgot+0xb5>
    2dfc:	mov    %rax,(%rsp)
    2e00:	ret    
    2e01:	int3   
    2e02:	call   2df0 <pgot_zlib_deflateReset_all_pgot+0xb0>
    2e07:	movslq 0xac(%rbx),%rax
    2e0e:	shl    $0x4,%rax
    2e12:	add    0x0(%rip),%rax        # 2e19 <pgot_zlib_deflateReset_all_pgot+0xd9>
			2e15: R_X86_64_PC32	pgot_configuration_table_all_pgot-0x4
    2e19:	movzwl 0x2(%rax),%edx
    2e1d:	mov    %edx,0xa8(%rbx)
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_deflateReset_all_pgot, 2e15, pgot_configuration_table_all_pgot

```asm
    2e0e:	shl    $0x4,%rax
    2e12:	add    0x0(%rip),%rax        # 2e19 <pgot_zlib_deflateReset_all_pgot+0xd9>
			2e15: R_X86_64_PC32	pgot_configuration_table_all_pgot-0x4
    2e19:	movzwl 0x2(%rax),%edx
    2e1d:	mov    %edx,0xa8(%rbx)
    2e23:	movzwl (%rax),%edx
    2e26:	mov    %edx,0xb4(%rbx)
    2e2c:	movzwl 0x4(%rax),%edx
    2e30:	mov    %edx,0xb8(%rbx)
    2e36:	movzwl 0x6(%rax),%eax
    2e3a:	movq   $0x0,0x80(%rbx)
    2e45:	movl   $0x2,0x88(%rbx)
    2e4f:	movq   $0x0,0x90(%rbx)
    2e5a:	movl   $0x0,0x68(%rbx)
    2e61:	mov    %eax,0xa4(%rbx)
    2e67:	movabs $0x200000000,%rax
    2e71:	mov    %rax,0x9c(%rbx)
    2e78:	xor    %eax,%eax
    2e7a:	mov    -0x8(%rbp),%rbx
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_stored_block_all_pgot, 31ba, pgot_memcpy_table_all_pgot

```asm
    31b3:	movslq 0x28(%rbx),%rdi
    31b7:	mov    0x0(%rip),%rax        # 31be <pgot_zlib_tr_stored_block_all_pgot+0x17e>
			31ba: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    31be:	add    0x10(%rbx),%rdi
    31c2:	jmp    31d6 <pgot_zlib_tr_stored_block_all_pgot+0x196>
    31c4:	call   31d0 <pgot_zlib_tr_stored_block_all_pgot+0x190>
    31c9:	pause  
    31cb:	lfence 
    31ce:	jmp    31c9 <pgot_zlib_tr_stored_block_all_pgot+0x189>
    31d0:	mov    %rax,(%rsp)
    31d4:	ret    
    31d5:	int3   
    31d6:	call   31c4 <pgot_zlib_tr_stored_block_all_pgot+0x184>
    31db:	add    %r12d,0x28(%rbx)
    31df:	add    $0x8,%rsp
    31e3:	pop    %rbx
    31e4:	pop    %r12
    31e6:	pop    %r13
    31e8:	pop    %r14
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_align_all_pgot, 33dd, pgot_static_ltree_all_pgot

```asm
    33d3:	mov    %ax,0x1720(%rbx)
    33da:	mov    0x0(%rip),%rax        # 33e1 <pgot_zlib_tr_align_all_pgot+0xa1>
			33dd: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    33e1:	mov    $0x10,%esi
    33e6:	mov    %ecx,0x1724(%rbx)
    33ec:	movzwl 0x402(%rax),%r12d
    33f4:	movzwl 0x400(%rax),%eax
    33fb:	sub    %r12d,%esi
    33fe:	mov    %eax,%r13d
    3401:	cmp    %ecx,%esi
    3403:	jge    364e <pgot_zlib_tr_align_all_pgot+0x30e>
    3409:	cmp    $0x1f,%edx
    340c:	ja     3412 <pgot_zlib_tr_align_all_pgot+0xd2>
			340e: R_X86_64_PC32	.text.unlikely+0xb94
    3412:	movslq 0x28(%rbx),%rdx
    3416:	mov    %eax,%edi
    3418:	mov    0x10(%rbx),%rsi
    341c:	shl    %cl,%edi
    341e:	mov    %edi,%ecx
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_align_all_pgot, 355c, pgot_static_ltree_all_pgot

```asm
    3552:	mov    %ax,0x1720(%rbx)
    3559:	mov    0x0(%rip),%rsi        # 3560 <pgot_zlib_tr_align_all_pgot+0x220>
			355c: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    3560:	mov    %ecx,0x1724(%rbx)
    3566:	movzwl 0x402(%rsi),%eax
    356d:	movzwl 0x400(%rsi),%r12d
    3575:	mov    $0x10,%esi
    357a:	sub    %eax,%esi
    357c:	mov    %r12d,%r13d
    357f:	cmp    %ecx,%esi
    3581:	jge    36fa <pgot_zlib_tr_align_all_pgot+0x3ba>
    3587:	cmp    $0x1f,%edx
    358a:	ja     3590 <pgot_zlib_tr_align_all_pgot+0x250>
			358c: R_X86_64_PC32	.text.unlikely+0xc1e
    3590:	movslq 0x28(%rbx),%rdx
    3594:	mov    %r12d,%edi
    3597:	mov    0x10(%rbx),%rsi
    359b:	shl    %cl,%edi
    359d:	mov    %edi,%ecx
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_deflate_all_pgot, 383d, pgot_configuration_table_all_pgot

```asm
    3836:	shl    $0x4,%rax
    383a:	add    0x0(%rip),%rax        # 3841 <pgot_zlib_deflate_all_pgot+0xd1>
			383d: R_X86_64_PC32	pgot_configuration_table_all_pgot-0x4
    3841:	mov    0x8(%rax),%rax
    3845:	jmp    3859 <pgot_zlib_deflate_all_pgot+0xe9>
    3847:	call   3853 <pgot_zlib_deflate_all_pgot+0xe3>
    384c:	pause  
    384e:	lfence 
    3851:	jmp    384c <pgot_zlib_deflate_all_pgot+0xdc>
    3853:	mov    %rax,(%rsp)
    3857:	ret    
    3858:	int3   
    3859:	call   3847 <pgot_zlib_deflate_all_pgot+0xd7>
    385e:	lea    -0x2(%rax),%edx
    3861:	cmp    $0x1,%edx
    3864:	jbe    39ac <pgot_zlib_deflate_all_pgot+0x23c>
    386a:	test   $0xfffffffd,%eax
    386f:	je     39bc <pgot_zlib_deflate_all_pgot+0x24c>
    3875:	cmp    $0x1,%eax
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_deflate_all_pgot, 38ca, pgot_memset_table_all_pgot

```asm
    38c4:	lea    -0x1(%rax),%edx
    38c7:	mov    0x0(%rip),%rax        # 38ce <pgot_zlib_deflate_all_pgot+0x15e>
			38ca: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    38ce:	add    %rdx,%rdx
    38d1:	jmp    38e5 <pgot_zlib_deflate_all_pgot+0x175>
    38d3:	call   38df <pgot_zlib_deflate_all_pgot+0x16f>
    38d8:	pause  
    38da:	lfence 
    38dd:	jmp    38d8 <pgot_zlib_deflate_all_pgot+0x168>
    38df:	mov    %rax,(%rsp)
    38e3:	ret    
    38e4:	int3   
    38e5:	call   38d3 <pgot_zlib_deflate_all_pgot+0x163>
    38ea:	mov    0x38(%r12),%r15
    38ef:	mov    0x20(%r12),%rax
    38f4:	mov    0x28(%r15),%edx
    38f8:	mov    %rdx,%r14
    38fb:	cmp    %rax,%rdx
    38fe:	cmova  %eax,%r14d
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_deflate_all_pgot, 391d, memcpy

```asm
    3918:	mov    %rdx,-0x38(%rbp)
    391c:	call   3921 <pgot_zlib_deflate_all_pgot+0x1b1>
			391d: R_X86_64_PLT32	memcpy-0x4
    3921:	mov    -0x38(%rbp),%rdx
    3925:	add    %rdx,0x18(%r12)
    392a:	add    %rdx,0x20(%r15)
    392e:	add    %rdx,0x28(%r12)
    3933:	sub    %rdx,0x20(%r12)
    3938:	sub    %r14d,0x28(%r15)
    393c:	jne    3946 <pgot_zlib_deflate_all_pgot+0x1d6>
    393e:	mov    0x10(%r15),%rax
    3942:	mov    %rax,0x20(%r15)
    3946:	mov    0x20(%r12),%rax
    394b:	test   %rax,%rax
    394e:	je     39c4 <pgot_zlib_deflate_all_pgot+0x254>
    3950:	cmp    $0x5,%r13d
    3954:	jne    39cf <pgot_zlib_deflate_all_pgot+0x25f>
    3956:	mov    -0x30(%rbp),%rdi
    395a:	mov    $0x1,%eax
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_deflate_all_pgot, 3ac6, memcpy

```asm
    3ac1:	mov    %rdx,-0x38(%rbp)
    3ac5:	call   3aca <pgot_zlib_deflate_all_pgot+0x35a>
			3ac6: R_X86_64_PLT32	memcpy-0x4
    3aca:	mov    -0x38(%rbp),%rdx
    3ace:	add    %rdx,0x18(%r12)
    3ad3:	add    %rdx,0x20(%r15)
    3ad7:	add    %rdx,0x28(%r12)
    3adc:	sub    %rdx,0x20(%r12)
    3ae1:	sub    %r14d,0x28(%r15)
    3ae5:	je     3c37 <pgot_zlib_deflate_all_pgot+0x4c7>
    3aeb:	mov    0x20(%r12),%rax
    3af0:	test   %rax,%rax
    3af3:	je     39c4 <pgot_zlib_deflate_all_pgot+0x254>
    3af9:	mov    -0x30(%rbp),%rdx
    3afd:	mov    0x8(%r12),%rax
    3b02:	cmpl   $0x29a,0x8(%rdx)
    3b09:	jne    3b3b <pgot_zlib_deflate_all_pgot+0x3cb>
    3b0b:	test   %rax,%rax
    3b0e:	je     3998 <pgot_zlib_deflate_all_pgot+0x228>
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_deflate_all_pgot, 3bed, memcpy

```asm
    3be9:	mov    %r15,%rdx
    3bec:	call   3bf1 <pgot_zlib_deflate_all_pgot+0x481>
			3bed: R_X86_64_PLT32	memcpy-0x4
    3bf1:	add    %r15,0x18(%r12)
    3bf6:	add    %r15,0x20(%r14)
    3bfa:	add    %r15,0x28(%r12)
    3bff:	sub    %r15,0x20(%r12)
    3c04:	sub    %r13d,0x28(%r14)
    3c08:	jne    3c12 <pgot_zlib_deflate_all_pgot+0x4a2>
    3c0a:	mov    0x10(%r14),%rax
    3c0e:	mov    %rax,0x20(%r14)
    3c12:	mov    -0x30(%rbp),%rax
    3c16:	mov    0x28(%rax),%edx
    3c19:	movl   $0xffffffff,0x2c(%rax)
    3c20:	xor    %eax,%eax
    3c22:	test   %edx,%edx
    3c24:	sete   %al
    3c27:	add    $0x10,%rsp
    3c2b:	pop    %rbx
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_flush_block_all_pgot, 3d8d, pgot_bl_order_all_pgot

```asm
    3d85:	call   f90 <build_tree>
    3d8a:	mov    0x0(%rip),%rcx        # 3d91 <pgot_zlib_tr_flush_block_all_pgot+0xc1>
			3d8d: R_X86_64_PC32	pgot_bl_order_all_pgot-0x4
    3d91:	movzbl (%rcx,%rbx,1),%edx
    3d95:	mov    %ebx,%eax
    3d97:	cmp    $0x26,%rdx
    3d9b:	ja     467f <pgot_zlib_tr_flush_block_all_pgot+0x9af>
    3da1:	cmpw   $0x0,0xaa6(%r12,%rdx,4)
    3dab:	jne    43f6 <pgot_zlib_tr_flush_block_all_pgot+0x726>
    3db1:	sub    $0x1,%rbx
    3db5:	cmp    $0x2,%rbx
    3db9:	jne    3d91 <pgot_zlib_tr_flush_block_all_pgot+0xc1>
    3dbb:	mov    $0x17,%edx
    3dc0:	mov    $0x3,%ebx
    3dc5:	mov    $0x2,%eax
    3dca:	mov    0x1708(%r12),%rdi
    3dd2:	add    0x1700(%r12),%rdx
    3dda:	mov    %rdx,0x1700(%r12)
    3de2:	add    $0xa,%rdx
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_flush_block_all_pgot, 4183, pgot_bl_order_all_pgot

```asm
    417e:	je     41c7 <pgot_zlib_tr_flush_block_all_pgot+0x4f7>
    4180:	mov    0x0(%rip),%rdx        # 4187 <pgot_zlib_tr_flush_block_all_pgot+0x4b7>
			4183: R_X86_64_PC32	pgot_bl_order_all_pgot-0x4
    4187:	movzbl (%rdx,%rbx,1),%edx
    418b:	movslq %edx,%r15
    418e:	cmp    $0xd,%ecx
    4191:	jg     40d7 <pgot_zlib_tr_flush_block_all_pgot+0x407>
    4197:	cmp    $0x26,%dl
    419a:	ja     465f <pgot_zlib_tr_flush_block_all_pgot+0x98f>
    41a0:	movzwl 0xaa6(%r12,%r15,4),%r15d
    41a9:	cmp    $0x1f,%ecx
    41ac:	ja     41b2 <pgot_zlib_tr_flush_block_all_pgot+0x4e2>
			41ae: R_X86_64_PC32	.text.unlikely+0xec6
    41b2:	mov    %ecx,%esi
    41b4:	mov    %r15d,%edx
    41b7:	shl    %cl,%edx
    41b9:	lea    0x3(%rsi),%ecx
    41bc:	or     0x1720(%r12),%dx
    41c5:	jmp    4166 <pgot_zlib_tr_flush_block_all_pgot+0x496>
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_flush_block_all_pgot, 4357, pgot_static_ltree_all_pgot

```asm
    434b:	mov    %ax,0x1720(%r12)
    4354:	mov    0x0(%rip),%rsi        # 435b <pgot_zlib_tr_flush_block_all_pgot+0x68b>
			4357: R_X86_64_PC32	pgot_static_ltree_all_pgot-0x4
    435b:	mov    %r12,%rdi
    435e:	mov    %edx,0x1724(%r12)
    4366:	mov    0x0(%rip),%rdx        # 436d <pgot_zlib_tr_flush_block_all_pgot+0x69d>
			4369: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    436d:	call   2280 <compress_block>
    4372:	mov    0x1708(%r12),%rax
    437a:	add    0x1710(%r12),%rax
    4382:	add    $0x3,%rax
    4386:	mov    %rax,0x1710(%r12)
    438e:	jmp    4215 <pgot_zlib_tr_flush_block_all_pgot+0x545>
    4393:	mov    0x1724(%r12),%eax
    439b:	cmp    $0x8,%eax
    439e:	jg     4499 <pgot_zlib_tr_flush_block_all_pgot+0x7c9>
    43a4:	test   %eax,%eax
    43a6:	jle    43c6 <pgot_zlib_tr_flush_block_all_pgot+0x6f6>
    43a8:	movzwl 0x1720(%r12),%ecx
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_flush_block_all_pgot, 4369, pgot_static_dtree_all_pgot

```asm
    435e:	mov    %edx,0x1724(%r12)
    4366:	mov    0x0(%rip),%rdx        # 436d <pgot_zlib_tr_flush_block_all_pgot+0x69d>
			4369: R_X86_64_PC32	pgot_static_dtree_all_pgot-0x4
    436d:	call   2280 <compress_block>
    4372:	mov    0x1708(%r12),%rax
    437a:	add    0x1710(%r12),%rax
    4382:	add    $0x3,%rax
    4386:	mov    %rax,0x1710(%r12)
    438e:	jmp    4215 <pgot_zlib_tr_flush_block_all_pgot+0x545>
    4393:	mov    0x1724(%r12),%eax
    439b:	cmp    $0x8,%eax
    439e:	jg     4499 <pgot_zlib_tr_flush_block_all_pgot+0x7c9>
    43a4:	test   %eax,%eax
    43a6:	jle    43c6 <pgot_zlib_tr_flush_block_all_pgot+0x6f6>
    43a8:	movzwl 0x1720(%r12),%ecx
    43b1:	movslq 0x28(%r12),%rax
    43b6:	mov    0x10(%r12),%rdx
    43bb:	lea    0x1(%rax),%esi
    43be:	mov    %esi,0x28(%r12)
```

## 03_zlib_deflate/retpoline/all_pgot: deflate_stored, 478d, memcpy

```asm
    4788:	mov    %rdx,-0x30(%rbp)
    478c:	call   4791 <deflate_stored+0xd1>
			478d: R_X86_64_PLT32	memcpy-0x4
    4791:	mov    -0x30(%rbp),%rdx
    4795:	add    %rdx,0x18(%r14)
    4799:	add    %rdx,0x20(%r13)
    479d:	add    %rdx,0x28(%r14)
    47a1:	sub    %rdx,0x20(%r14)
    47a5:	sub    %r15d,0x28(%r13)
    47a9:	jne    47b3 <deflate_stored+0xf3>
    47ab:	mov    0x10(%r13),%rax
    47af:	mov    %rax,0x20(%r13)
    47b3:	mov    (%rbx),%rax
    47b6:	mov    0x20(%rax),%rax
    47ba:	test   %rax,%rax
    47bd:	je     4973 <deflate_stored+0x2b3>
    47c3:	mov    0x94(%rbx),%eax
    47c9:	mov    0x80(%rbx),%rcx
    47d0:	mov    0x38(%rbx),%edi
```

## 03_zlib_deflate/retpoline/all_pgot: deflate_stored, 488b, memcpy

```asm
    4886:	mov    %rdx,-0x30(%rbp)
    488a:	call   488f <deflate_stored+0x1cf>
			488b: R_X86_64_PLT32	memcpy-0x4
    488f:	mov    -0x30(%rbp),%rdx
    4893:	add    %rdx,0x18(%r14)
    4897:	mov    -0x40(%rbp),%rcx
    489b:	add    %rdx,0x20(%rcx)
    489f:	add    %rdx,0x28(%r14)
    48a3:	sub    %rdx,0x20(%r14)
    48a7:	sub    %r15d,0x28(%rcx)
    48ab:	jne    48b5 <deflate_stored+0x1f5>
    48ad:	mov    0x10(%rcx),%rax
    48b1:	mov    %rax,0x20(%rcx)
    48b5:	mov    (%rbx),%rax
    48b8:	mov    0x20(%rax),%rax
    48bc:	test   %rax,%rax
    48bf:	je     498f <deflate_stored+0x2cf>
    48c5:	xor    %eax,%eax
    48c7:	cmpl   $0x5,-0x34(%rbp)
```

## 03_zlib_deflate/retpoline/all_pgot: deflate_stored, 4941, memcpy

```asm
    493c:	mov    %rdx,-0x30(%rbp)
    4940:	call   4945 <deflate_stored+0x285>
			4941: R_X86_64_PLT32	memcpy-0x4
    4945:	mov    -0x30(%rbp),%rdx
    4949:	add    %rdx,0x18(%r14)
    494d:	mov    -0x40(%rbp),%rcx
    4951:	add    %rdx,0x20(%rcx)
    4955:	add    %rdx,0x28(%r14)
    4959:	sub    %rdx,0x20(%r14)
    495d:	sub    %r15d,0x28(%rcx)
    4961:	je     4985 <deflate_stored+0x2c5>
    4963:	mov    (%rbx),%rax
    4966:	mov    0x20(%rax),%rax
    496a:	test   %rax,%rax
    496d:	jne    47e5 <deflate_stored+0x125>
    4973:	xor    %eax,%eax
    4975:	add    $0x18,%rsp
    4979:	pop    %rbx
    497a:	pop    %r12
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_tally_all_pgot, 4a27, pgot_extra_dbits_all_pgot

```asm
    4a21:	mov    %r15d,%r13d
    4a24:	mov    0x0(%rip),%r14        # 4a2b <pgot_zlib_tr_tally_all_pgot+0x8b>
			4a27: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
    4a2b:	xor    %ebx,%ebx
    4a2d:	mov    0x94(%r12),%ecx
    4a35:	mov    0x80(%r12),%r8
    4a3d:	shl    $0x3,%r13
    4a41:	movslq %ebx,%rsi
    4a44:	cmp    $0x3c,%rsi
    4a48:	ja     4b37 <pgot_zlib_tr_tally_all_pgot+0x197>
    4a4e:	movzwl 0x9b0(%r12,%rbx,4),%edx
    4a57:	movslq (%r14,%rbx,4),%rax
    4a5b:	add    $0x1,%rbx
    4a5f:	add    $0x5,%rax
    4a63:	imul   %rdx,%rax
    4a67:	add    %rax,%r13
    4a6a:	cmp    $0x1e,%rbx
    4a6e:	jne    4a41 <pgot_zlib_tr_tally_all_pgot+0xa1>
    4a70:	mov    %r15d,%eax
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_tally_all_pgot, 4aaa, pgot_length_code_all_pgot

```asm
    4aa6:	int3   
    4aa7:	mov    0x0(%rip),%rax        # 4aae <pgot_zlib_tr_tally_all_pgot+0x10e>
			4aaa: R_X86_64_PC32	pgot_length_code_all_pgot-0x4
    4aae:	mov    %edx,%edx
    4ab0:	lea    -0x1(%rsi),%ebx
    4ab3:	addl   $0x1,0x1718(%r12)
    4abc:	movzbl (%rax,%rdx,1),%eax
    4ac0:	lea    0x101(%rax),%r13
    4ac7:	cmp    $0x23c,%r13
    4ace:	ja     4b67 <pgot_zlib_tr_tally_all_pgot+0x1c7>
    4ad4:	addw   $0x1,0xbc(%r12,%r13,4)
    4ade:	mov    0x0(%rip),%rdx        # 4ae5 <pgot_zlib_tr_tally_all_pgot+0x145>
			4ae1: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    4ae5:	cmp    $0xff,%ebx
    4aeb:	jbe    4b12 <pgot_zlib_tr_tally_all_pgot+0x172>
    4aed:	mov    %ebx,%esi
    4aef:	shr    $0x7,%esi
    4af2:	lea    0x100(%rsi),%eax
    4af8:	movzbl (%rdx,%rax,1),%eax
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_tally_all_pgot, 4ae1, pgot_dist_code_all_pgot

```asm
    4ad4:	addw   $0x1,0xbc(%r12,%r13,4)
    4ade:	mov    0x0(%rip),%rdx        # 4ae5 <pgot_zlib_tr_tally_all_pgot+0x145>
			4ae1: R_X86_64_PC32	pgot_dist_code_all_pgot-0x4
    4ae5:	cmp    $0xff,%ebx
    4aeb:	jbe    4b12 <pgot_zlib_tr_tally_all_pgot+0x172>
    4aed:	mov    %ebx,%esi
    4aef:	shr    $0x7,%esi
    4af2:	lea    0x100(%rsi),%eax
    4af8:	movzbl (%rdx,%rax,1),%eax
    4afc:	movslq %eax,%rbx
    4aff:	cmp    $0x3c,%al
    4b01:	ja     4b56 <pgot_zlib_tr_tally_all_pgot+0x1b6>
    4b03:	addw   $0x1,0x9b0(%r12,%rbx,4)
    4b0d:	jmp    4a05 <pgot_zlib_tr_tally_all_pgot+0x65>
    4b12:	mov    %ebx,%esi
    4b14:	movzbl (%rdx,%rsi,1),%eax
    4b18:	jmp    4afc <pgot_zlib_tr_tally_all_pgot+0x15c>
    4b1a:	sub    %r8,%rcx
    4b1d:	shr    $0x3,%r13
```

## 03_zlib_deflate/retpoline/all_pgot: deflate_slow, 4dd2, memcpy

```asm
    4dcd:	mov    %rdx,-0x30(%rbp)
    4dd1:	call   4dd6 <deflate_slow+0x246>
			4dd2: R_X86_64_PLT32	memcpy-0x4
    4dd6:	mov    -0x30(%rbp),%rdx
    4dda:	add    %rdx,0x18(%r13)
    4dde:	mov    -0x38(%rbp),%rcx
    4de2:	add    %rdx,0x20(%rcx)
    4de6:	add    %rdx,0x28(%r13)
    4dea:	sub    %rdx,0x20(%r13)
    4dee:	sub    %r15d,0x28(%rcx)
    4df2:	jne    4dfc <deflate_slow+0x26c>
    4df4:	mov    0x10(%rcx),%rax
    4df8:	mov    %rax,0x20(%rcx)
    4dfc:	mov    (%rbx),%rax
    4dff:	mov    0x20(%rax),%rax
    4e03:	test   %rax,%rax
    4e06:	je     4f86 <deflate_slow+0x3f6>
    4e0c:	mov    0x9c(%rbx),%eax
    4e12:	cmp    $0x105,%eax
```

## 03_zlib_deflate/retpoline/all_pgot: deflate_slow, 4f31, memcpy

```asm
    4f2c:	mov    %r8,-0x30(%rbp)
    4f30:	call   4f35 <deflate_slow+0x3a5>
			4f31: R_X86_64_PLT32	memcpy-0x4
    4f35:	add    %r13,0x18(%r15)
    4f39:	mov    -0x38(%rbp),%ecx
    4f3c:	mov    -0x30(%rbp),%r8
    4f40:	add    %r13,0x20(%r8)
    4f44:	add    %r13,0x28(%r15)
    4f48:	sub    %r13,0x20(%r15)
    4f4c:	sub    %ecx,0x28(%r8)
    4f50:	jne    4f5a <deflate_slow+0x3ca>
    4f52:	mov    0x10(%r8),%rax
    4f56:	mov    %rax,0x20(%r8)
    4f5a:	mov    0x94(%rbx),%eax
    4f60:	mov    (%rbx),%r15
    4f63:	add    $0x1,%eax
    4f66:	mov    %eax,0x94(%rbx)
    4f6c:	mov    0x9c(%rbx),%eax
    4f72:	sub    $0x1,%eax
```

## 03_zlib_deflate/retpoline/all_pgot: deflate_slow, 5075, memcpy

```asm
    5070:	mov    %rdx,-0x30(%rbp)
    5074:	call   5079 <deflate_slow+0x4e9>
			5075: R_X86_64_PLT32	memcpy-0x4
    5079:	mov    -0x30(%rbp),%rdx
    507d:	add    %rdx,0x18(%r14)
    5081:	mov    -0x38(%rbp),%rcx
    5085:	add    %rdx,0x20(%rcx)
    5089:	add    %rdx,0x28(%r14)
    508d:	sub    %rdx,0x20(%r14)
    5091:	sub    %r15d,0x28(%rcx)
    5095:	je     50c0 <deflate_slow+0x530>
    5097:	mov    (%rbx),%rax
    509a:	mov    0x20(%rax),%rax
    509e:	test   %rax,%rax
    50a1:	je     50f4 <deflate_slow+0x564>
    50a3:	xor    %eax,%eax
    50a5:	cmp    $0x5,%r12d
    50a9:	sete   %al
    50ac:	add    $0x10,%rsp
```

## 03_zlib_deflate/retpoline/all_pgot: deflate_fast, 52d4, memcpy

```asm
    52cf:	mov    %rdx,-0x30(%rbp)
    52d3:	call   52d8 <deflate_fast+0x1c8>
			52d4: R_X86_64_PLT32	memcpy-0x4
    52d8:	mov    -0x30(%rbp),%rdx
    52dc:	add    %rdx,0x18(%r13)
    52e0:	add    %rdx,0x20(%r12)
    52e5:	add    %rdx,0x28(%r13)
    52e9:	sub    %rdx,0x20(%r13)
    52ed:	sub    %r15d,0x28(%r12)
    52f2:	jne    52fe <deflate_fast+0x1ee>
    52f4:	mov    0x10(%r12),%rax
    52f9:	mov    %rax,0x20(%r12)
    52fe:	mov    (%rbx),%rax
    5301:	mov    0x20(%rax),%rax
    5305:	test   %rax,%rax
    5308:	jne    512f <deflate_fast+0x1f>
    530e:	add    $0x18,%rsp
    5312:	xor    %eax,%eax
    5314:	pop    %rbx
```

## 03_zlib_deflate/retpoline/all_pgot: deflate_fast, 5479, memcpy

```asm
    5474:	mov    %rdx,-0x30(%rbp)
    5478:	call   547d <deflate_fast+0x36d>
			5479: R_X86_64_PLT32	memcpy-0x4
    547d:	mov    -0x30(%rbp),%rdx
    5481:	add    %rdx,0x18(%r14)
    5485:	mov    -0x40(%rbp),%rcx
    5489:	add    %rdx,0x20(%rcx)
    548d:	add    %rdx,0x28(%r14)
    5491:	sub    %rdx,0x20(%r14)
    5495:	sub    %r15d,0x28(%rcx)
    5499:	je     54c4 <deflate_fast+0x3b4>
    549b:	mov    (%rbx),%rax
    549e:	mov    0x20(%rax),%rax
    54a2:	test   %rax,%rax
    54a5:	je     54ce <deflate_fast+0x3be>
    54a7:	xor    %eax,%eax
    54a9:	cmpl   $0x5,-0x34(%rbp)
    54ad:	sete   %al
    54b0:	add    $0x18,%rsp
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot.cold, 9f7, pgot_extra_dbits_all_pgot

```asm
			9f0: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     9f4:	mov    0x0(%rip),%rax        # 9fb <pgot_zlib_tr_init_all_pgot.cold+0x1f>
			9f7: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
     9fb:	mov    -0x58(%rbp),%r8
     9ff:	mov    $0x1,%r9d
     a05:	mov    (%rax,%r8,1),%ecx
     a09:	jmp    a0e <pgot_zlib_tr_init_all_pgot.cold+0x32>
			a0a: R_X86_64_PC32	.text+0x2cb9
     a0e:	movslq %ecx,%rdx
     a11:	mov    $0x1,%esi
     a16:	mov    $0x0,%rdi
			a19: R_X86_64_32S	.data+0x13c0
     a1d:	mov    %r8,-0x58(%rbp)
     a21:	call   a26 <pgot_zlib_tr_init_all_pgot.cold+0x4a>
			a22: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a26:	mov    0x0(%rip),%rax        # a2d <pgot_zlib_tr_init_all_pgot.cold+0x51>
			a29: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
     a2d:	mov    -0x58(%rbp),%r8
     a31:	mov    $0x1,%r9d
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot.cold, a29, pgot_extra_lbits_all_pgot

```asm
			a22: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a26:	mov    0x0(%rip),%rax        # a2d <pgot_zlib_tr_init_all_pgot.cold+0x51>
			a29: R_X86_64_PC32	pgot_extra_lbits_all_pgot-0x4
     a2d:	mov    -0x58(%rbp),%r8
     a31:	mov    $0x1,%r9d
     a37:	mov    (%rax,%r8,1),%ecx
     a3b:	jmp    a40 <pgot_zlib_tr_init_all_pgot.cold+0x64>
			a3c: R_X86_64_PC32	.text+0x2950
     a40:	movslq %ecx,%rdx
     a43:	mov    $0x1,%esi
     a48:	mov    $0x0,%rdi
			a4b: R_X86_64_32S	.data+0x1380
     a4f:	mov    %eax,-0x58(%rbp)
     a52:	call   a57 <pgot_zlib_tr_init_all_pgot.cold+0x7b>
			a53: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a57:	mov    0x0(%rip),%rdx        # a5e <pgot_zlib_tr_init_all_pgot.cold+0x82>
			a5a: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
     a5e:	mov    -0x58(%rbp),%eax
     a61:	mov    $0x1,%r8d
```

## 03_zlib_deflate/retpoline/all_pgot: pgot_zlib_tr_init_all_pgot.cold, a5a, pgot_extra_dbits_all_pgot

```asm
			a53: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a57:	mov    0x0(%rip),%rdx        # a5e <pgot_zlib_tr_init_all_pgot.cold+0x82>
			a5a: R_X86_64_PC32	pgot_extra_dbits_all_pgot-0x4
     a5e:	mov    -0x58(%rbp),%eax
     a61:	mov    $0x1,%r8d
     a67:	mov    (%rdx,%r14,1),%ecx
     a6b:	sub    $0x7,%ecx
     a6e:	jmp    a73 <pgot_zlib_tr_stored_block_all_pgot.cold>
			a6f: R_X86_64_PC32	.text+0x29cb

```

## 03_zlib_deflate/retpoline/data_pgot: compress_block, 1333, pgot_length_code_data_pgot

```asm
    132a:	je     1262 <compress_block+0x42>
    1330:	mov    0x0(%rip),%rdx        # 1337 <compress_block+0x117>
			1333: R_X86_64_PC32	pgot_length_code_data_pgot-0x4
    1337:	movzbl (%rdx,%rax,1),%eax
    133b:	mov    %r9d,%edx
    133e:	mov    %rax,%r15
    1341:	lea    0x404(%r8,%rax,4),%rax
    1349:	movzwl 0x2(%rax),%r10d
    134e:	movzwl (%rax),%eax
    1351:	sub    %r10d,%edx
    1354:	mov    %eax,%r11d
    1357:	cmp    %ecx,%edx
    1359:	jge    16ad <compress_block+0x48d>
    135f:	cmp    $0x1f,%ecx
    1362:	ja     1368 <compress_block+0x148>
			1364: R_X86_64_PC32	.text.unlikely+0x8ff
    1368:	movslq 0x28(%rbx),%rdx
    136c:	mov    %eax,%edi
    136e:	mov    0x10(%rbx),%rsi
```

## 03_zlib_deflate/retpoline/data_pgot: compress_block, 13d5, pgot_extra_lbits_data_pgot

```asm
    13cb:	mov    %ax,0x1720(%rbx)
    13d2:	mov    0x0(%rip),%rax        # 13d9 <compress_block+0x1b9>
			13d5: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
    13d9:	mov    %ecx,0x1724(%rbx)
    13df:	mov    (%rax,%r15,4),%eax
    13e3:	test   %eax,%eax
    13e5:	je     1482 <compress_block+0x262>
    13eb:	mov    0x0(%rip),%rsi        # 13f2 <compress_block+0x1d2>
			13ee: R_X86_64_PC32	pgot_base_length_data_pgot-0x4
    13f2:	sub    (%rsi,%r15,4),%r13d
    13f6:	mov    %r9d,%esi
    13f9:	sub    %eax,%esi
    13fb:	cmp    %ecx,%esi
    13fd:	jge    1750 <compress_block+0x530>
    1403:	cmp    $0x1f,%edx
    1406:	ja     140c <compress_block+0x1ec>
			1408: R_X86_64_PC32	.text.unlikely+0x88c
    140c:	movslq 0x28(%rbx),%rdx
    1410:	mov    %r13d,%edi
```

## 03_zlib_deflate/retpoline/data_pgot: compress_block, 13ee, pgot_base_length_data_pgot

```asm
    13e5:	je     1482 <compress_block+0x262>
    13eb:	mov    0x0(%rip),%rsi        # 13f2 <compress_block+0x1d2>
			13ee: R_X86_64_PC32	pgot_base_length_data_pgot-0x4
    13f2:	sub    (%rsi,%r15,4),%r13d
    13f6:	mov    %r9d,%esi
    13f9:	sub    %eax,%esi
    13fb:	cmp    %ecx,%esi
    13fd:	jge    1750 <compress_block+0x530>
    1403:	cmp    $0x1f,%edx
    1406:	ja     140c <compress_block+0x1ec>
			1408: R_X86_64_PC32	.text.unlikely+0x88c
    140c:	movslq 0x28(%rbx),%rdx
    1410:	mov    %r13d,%edi
    1413:	mov    0x10(%rbx),%rsi
    1417:	movzwl %r13w,%r13d
    141b:	shl    %cl,%edi
    141d:	mov    %edi,%ecx
    141f:	lea    0x1(%rdx),%edi
    1422:	or     0x1720(%rbx),%cx
```

## 03_zlib_deflate/retpoline/data_pgot: compress_block, 1489, pgot_dist_code_data_pgot

```asm
    1482:	sub    $0x1,%r12d
    1486:	mov    0x0(%rip),%rsi        # 148d <compress_block+0x26d>
			1489: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    148d:	cmp    $0xff,%r12d
    1494:	ja     16ec <compress_block+0x4cc>
    149a:	mov    %r12d,%eax
    149d:	movzbl (%rsi,%rax,1),%r13d
    14a2:	mov    -0x30(%rbp),%rax
    14a6:	lea    (%rax,%r13,4),%rsi
    14aa:	movzwl 0x2(%rsi),%eax
    14ae:	movzwl (%rsi),%r15d
    14b2:	mov    %r9d,%esi
    14b5:	sub    %eax,%esi
    14b7:	mov    %r15d,%r10d
    14ba:	cmp    %ecx,%esi
    14bc:	jge    16cc <compress_block+0x4ac>
    14c2:	cmp    $0x1f,%edx
    14c5:	ja     14cb <compress_block+0x2ab>
			14c7: R_X86_64_PC32	.text.unlikely+0x819
```

## 03_zlib_deflate/retpoline/data_pgot: compress_block, 1532, pgot_extra_dbits_data_pgot

```asm
    152d:	mov    %eax,%ecx
    152f:	mov    0x0(%rip),%rdx        # 1536 <compress_block+0x316>
			1532: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    1536:	mov    %r15w,0x1720(%rbx)
    153e:	mov    %ecx,0x1724(%rbx)
    1544:	mov    (%rdx,%r13,4),%r15d
    1548:	test   %r15d,%r15d
    154b:	je     12f9 <compress_block+0xd9>
    1551:	mov    0x0(%rip),%rdx        # 1558 <compress_block+0x338>
			1554: R_X86_64_PC32	pgot_base_dist_data_pgot-0x4
    1558:	sub    (%rdx,%r13,4),%r12d
    155c:	mov    %r9d,%edx
    155f:	sub    %r15d,%edx
    1562:	cmp    %ecx,%edx
    1564:	jge    1729 <compress_block+0x509>
    156a:	cmp    $0x1f,%eax
    156d:	ja     1573 <compress_block+0x353>
			156f: R_X86_64_PC32	.text.unlikely+0x7b1
    1573:	movslq 0x28(%rbx),%rax
```

## 03_zlib_deflate/retpoline/data_pgot: compress_block, 1554, pgot_base_dist_data_pgot

```asm
    154b:	je     12f9 <compress_block+0xd9>
    1551:	mov    0x0(%rip),%rdx        # 1558 <compress_block+0x338>
			1554: R_X86_64_PC32	pgot_base_dist_data_pgot-0x4
    1558:	sub    (%rdx,%r13,4),%r12d
    155c:	mov    %r9d,%edx
    155f:	sub    %r15d,%edx
    1562:	cmp    %ecx,%edx
    1564:	jge    1729 <compress_block+0x509>
    156a:	cmp    $0x1f,%eax
    156d:	ja     1573 <compress_block+0x353>
			156f: R_X86_64_PC32	.text.unlikely+0x7b1
    1573:	movslq 0x28(%rbx),%rax
    1577:	mov    %r12d,%edx
    157a:	movzwl %r12w,%r12d
    157e:	shl    %cl,%edx
    1580:	mov    0x10(%rbx),%rcx
    1584:	or     0x1720(%rbx),%dx
    158b:	lea    0x1(%rax),%esi
    158e:	mov    %dx,0x1720(%rbx)
```

## 03_zlib_deflate/retpoline/data_pgot: fill_window, 2446, memcpy

```asm
    2442:	add    %rax,%rdi
    2445:	call   244a <fill_window+0x10a>
			2446: R_X86_64_PLT32	memcpy-0x4
    244a:	mov    -0x70(%rbp),%rcx
    244e:	mov    -0x74(%rbp),%eax
    2451:	add    %rbx,(%rcx)
    2454:	add    %rbx,0x10(%rcx)
    2458:	mov    -0x58(%rbp),%rbx
    245c:	add    0x9c(%rbx),%eax
    2462:	mov    %eax,-0x5c(%rbp)
    2465:	mov    -0x58(%rbp),%rdi
    2469:	mov    -0x5c(%rbp),%eax
    246c:	mov    %eax,0x9c(%rdi)
    2472:	cmp    $0x2,%eax
    2475:	jbe    24bc <fill_window+0x17c>
    2477:	mov    0x94(%rdi),%ecx
    247d:	mov    0x48(%rdi),%rax
    2481:	mov    %rcx,%rdx
    2484:	movzbl (%rax,%rcx,1),%ebx
```

## 03_zlib_deflate/retpoline/data_pgot: fill_window, 26f1, memcpy

```asm
    26ed:	mov    %r15,%rdx
    26f0:	call   26f5 <fill_window+0x3b5>
			26f1: R_X86_64_PLT32	memcpy-0x4
    26f5:	mov    0x6c(%r14),%ecx
    26f9:	mov    0x60(%r14),%rax
    26fd:	xor    %esi,%esi
    26ff:	mov    -0x94(%rbp),%r8d
    2706:	sub    %r15,0x80(%r14)
    270d:	mov    %rcx,%rdx
    2710:	sub    %r8d,0x98(%r14)
    2717:	lea    (%rax,%rcx,2),%rax
    271b:	sub    %r8d,0x94(%r14)
    2722:	sub    $0x1,%edx
    2725:	not    %rdx
    2728:	lea    (%rax,%rdx,2),%rdi
    272c:	movzwl -0x2(%rax),%ecx
    2730:	sub    $0x2,%rax
    2734:	mov    %ecx,%edx
    2736:	sub    %r8d,%edx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 28d7, pgot_base_length_data_pgot

```asm
    28ce:	mov    $0x1,%r9d
    28d4:	mov    0x0(%rip),%rax        # 28db <pgot_zlib_tr_init_data_pgot+0x4b>
			28d7: R_X86_64_PC32	pgot_base_length_data_pgot-0x4
    28db:	lea    0x0(,%r14,4),%r8
    28e3:	xor    %ebx,%ebx
    28e5:	mov    %r15d,(%rax,%r14,4)
    28e9:	jmp    28fc <pgot_zlib_tr_init_data_pgot+0x6c>
    28eb:	mov    0x0(%rip),%rax        # 28f2 <pgot_zlib_tr_init_data_pgot+0x62>
			28ee: R_X86_64_PC32	pgot_length_code_data_pgot-0x4
    28f2:	movslq %r12d,%r12
    28f5:	add    $0x1,%ebx
    28f8:	mov    %r14b,(%rax,%r12,1)
    28fc:	mov    0x0(%rip),%rax        # 2903 <pgot_zlib_tr_init_data_pgot+0x73>
			28ff: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
    2903:	lea    (%rbx,%r15,1),%r12d
    2907:	mov    (%rax,%r8,1),%ecx
    290b:	cmp    $0x1f,%ecx
    290e:	ja     2914 <pgot_zlib_tr_init_data_pgot+0x84>
			2910: R_X86_64_PC32	.text.unlikely+0xa0a
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 28ee, pgot_length_code_data_pgot

```asm
    28e9:	jmp    28fc <pgot_zlib_tr_init_data_pgot+0x6c>
    28eb:	mov    0x0(%rip),%rax        # 28f2 <pgot_zlib_tr_init_data_pgot+0x62>
			28ee: R_X86_64_PC32	pgot_length_code_data_pgot-0x4
    28f2:	movslq %r12d,%r12
    28f5:	add    $0x1,%ebx
    28f8:	mov    %r14b,(%rax,%r12,1)
    28fc:	mov    0x0(%rip),%rax        # 2903 <pgot_zlib_tr_init_data_pgot+0x73>
			28ff: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
    2903:	lea    (%rbx,%r15,1),%r12d
    2907:	mov    (%rax,%r8,1),%ecx
    290b:	cmp    $0x1f,%ecx
    290e:	ja     2914 <pgot_zlib_tr_init_data_pgot+0x84>
			2910: R_X86_64_PC32	.text.unlikely+0xa0a
    2914:	mov    %r9d,%eax
    2917:	shl    %cl,%eax
    2919:	cmp    %eax,%ebx
    291b:	jl     28eb <pgot_zlib_tr_init_data_pgot+0x5b>
    291d:	add    $0x1,%r14
    2921:	cmp    $0x1c,%r14
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 28ff, pgot_extra_lbits_data_pgot

```asm
    28f8:	mov    %r14b,(%rax,%r12,1)
    28fc:	mov    0x0(%rip),%rax        # 2903 <pgot_zlib_tr_init_data_pgot+0x73>
			28ff: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
    2903:	lea    (%rbx,%r15,1),%r12d
    2907:	mov    (%rax,%r8,1),%ecx
    290b:	cmp    $0x1f,%ecx
    290e:	ja     2914 <pgot_zlib_tr_init_data_pgot+0x84>
			2910: R_X86_64_PC32	.text.unlikely+0xa0a
    2914:	mov    %r9d,%eax
    2917:	shl    %cl,%eax
    2919:	cmp    %eax,%ebx
    291b:	jl     28eb <pgot_zlib_tr_init_data_pgot+0x5b>
    291d:	add    $0x1,%r14
    2921:	cmp    $0x1c,%r14
    2925:	je     2c1f <pgot_zlib_tr_init_data_pgot+0x38f>
    292b:	mov    %r12d,%r15d
    292e:	jmp    28d4 <pgot_zlib_tr_init_data_pgot+0x44>
    2930:	sar    $0x7,%r12d
    2934:	mov    $0x40,%r14d
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2949, pgot_base_dist_data_pgot

```asm
    2940:	mov    $0x1,%r8d
    2946:	mov    0x0(%rip),%rax        # 294d <pgot_zlib_tr_init_data_pgot+0xbd>
			2949: R_X86_64_PC32	pgot_base_dist_data_pgot-0x4
    294d:	mov    %r12d,%edx
    2950:	mov    %r12d,%ebx
    2953:	shl    $0x7,%edx
    2956:	mov    %edx,(%rax,%r14,1)
    295a:	mov    %r12d,%eax
    295d:	jmp    2975 <pgot_zlib_tr_init_data_pgot+0xe5>
    295f:	mov    0x0(%rip),%rdx        # 2966 <pgot_zlib_tr_init_data_pgot+0xd6>
			2962: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    2966:	add    $0x100,%ebx
    296c:	movslq %ebx,%rbx
    296f:	mov    %r15b,(%rdx,%rbx,1)
    2973:	mov    %esi,%ebx
    2975:	mov    0x0(%rip),%rdx        # 297c <pgot_zlib_tr_init_data_pgot+0xec>
			2978: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    297c:	mov    %ebx,%r12d
    297f:	mov    (%rdx,%r14,1),%ecx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2962, pgot_dist_code_data_pgot

```asm
    295d:	jmp    2975 <pgot_zlib_tr_init_data_pgot+0xe5>
    295f:	mov    0x0(%rip),%rdx        # 2966 <pgot_zlib_tr_init_data_pgot+0xd6>
			2962: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    2966:	add    $0x100,%ebx
    296c:	movslq %ebx,%rbx
    296f:	mov    %r15b,(%rdx,%rbx,1)
    2973:	mov    %esi,%ebx
    2975:	mov    0x0(%rip),%rdx        # 297c <pgot_zlib_tr_init_data_pgot+0xec>
			2978: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    297c:	mov    %ebx,%r12d
    297f:	mov    (%rdx,%r14,1),%ecx
    2983:	sub    $0x7,%ecx
    2986:	cmp    $0x1f,%ecx
    2989:	ja     298f <pgot_zlib_tr_init_data_pgot+0xff>
			298b: R_X86_64_PC32	.text.unlikely+0xa3c
    298f:	mov    %r8d,%edi
    2992:	mov    %ebx,%edx
    2994:	lea    0x1(%rbx),%esi
    2997:	shl    %cl,%edi
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2978, pgot_extra_dbits_data_pgot

```asm
    2973:	mov    %esi,%ebx
    2975:	mov    0x0(%rip),%rdx        # 297c <pgot_zlib_tr_init_data_pgot+0xec>
			2978: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    297c:	mov    %ebx,%r12d
    297f:	mov    (%rdx,%r14,1),%ecx
    2983:	sub    $0x7,%ecx
    2986:	cmp    $0x1f,%ecx
    2989:	ja     298f <pgot_zlib_tr_init_data_pgot+0xff>
			298b: R_X86_64_PC32	.text.unlikely+0xa3c
    298f:	mov    %r8d,%edi
    2992:	mov    %ebx,%edx
    2994:	lea    0x1(%rbx),%esi
    2997:	shl    %cl,%edi
    2999:	sub    %eax,%edx
    299b:	cmp    %edx,%edi
    299d:	jg     295f <pgot_zlib_tr_init_data_pgot+0xcf>
    299f:	add    $0x1,%r15d
    29a3:	add    $0x4,%r14
    29a7:	cmp    $0x1e,%r15d
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 29d8, pgot_static_ltree_data_pgot

```asm
    29d3:	xor    %eax,%eax
    29d5:	mov    0x0(%rip),%rdx        # 29dc <pgot_zlib_tr_init_data_pgot+0x14c>
			29d8: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    29dc:	mov    $0x8,%ebx
    29e1:	mov    %bx,0x2(%rdx,%rax,1)
    29e6:	add    $0x4,%rax
    29ea:	cmp    $0x240,%rax
    29f0:	jne    29d5 <pgot_zlib_tr_init_data_pgot+0x145>
    29f2:	movzwl -0x3e(%rbp),%esi
    29f6:	mov    0x0(%rip),%rdx        # 29fd <pgot_zlib_tr_init_data_pgot+0x16d>
			29f9: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    29fd:	mov    $0x9,%r11d
    2a03:	mov    %r11w,0x2(%rdx,%rax,1)
    2a09:	add    $0x4,%rax
    2a0d:	cmp    $0x400,%rax
    2a13:	jne    29f6 <pgot_zlib_tr_init_data_pgot+0x166>
    2a15:	lea    0x70(%rsi),%edx
    2a18:	movzwl -0x42(%rbp),%esi
    2a1c:	mov    %dx,-0x3e(%rbp)
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 29f9, pgot_static_ltree_data_pgot

```asm
    29f2:	movzwl -0x3e(%rbp),%esi
    29f6:	mov    0x0(%rip),%rdx        # 29fd <pgot_zlib_tr_init_data_pgot+0x16d>
			29f9: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    29fd:	mov    $0x9,%r11d
    2a03:	mov    %r11w,0x2(%rdx,%rax,1)
    2a09:	add    $0x4,%rax
    2a0d:	cmp    $0x400,%rax
    2a13:	jne    29f6 <pgot_zlib_tr_init_data_pgot+0x166>
    2a15:	lea    0x70(%rsi),%edx
    2a18:	movzwl -0x42(%rbp),%esi
    2a1c:	mov    %dx,-0x3e(%rbp)
    2a20:	mov    0x0(%rip),%rdx        # 2a27 <pgot_zlib_tr_init_data_pgot+0x197>
			2a23: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a27:	mov    $0x7,%r10d
    2a2d:	mov    %r10w,0x2(%rdx,%rax,1)
    2a33:	add    $0x4,%rax
    2a37:	cmp    $0x460,%rax
    2a3d:	jne    2a20 <pgot_zlib_tr_init_data_pgot+0x190>
    2a3f:	lea    0x18(%rsi),%edx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2a23, pgot_static_ltree_data_pgot

```asm
    2a1c:	mov    %dx,-0x3e(%rbp)
    2a20:	mov    0x0(%rip),%rdx        # 2a27 <pgot_zlib_tr_init_data_pgot+0x197>
			2a23: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a27:	mov    $0x7,%r10d
    2a2d:	mov    %r10w,0x2(%rdx,%rax,1)
    2a33:	add    $0x4,%rax
    2a37:	cmp    $0x460,%rax
    2a3d:	jne    2a20 <pgot_zlib_tr_init_data_pgot+0x190>
    2a3f:	lea    0x18(%rsi),%edx
    2a42:	mov    %dx,-0x42(%rbp)
    2a46:	mov    0x0(%rip),%rdx        # 2a4d <pgot_zlib_tr_init_data_pgot+0x1bd>
			2a49: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a4d:	mov    $0x8,%r9d
    2a53:	mov    %r9w,0x2(%rdx,%rax,1)
    2a59:	add    $0x4,%rax
    2a5d:	cmp    $0x480,%rax
    2a63:	jne    2a46 <pgot_zlib_tr_init_data_pgot+0x1b6>
    2a65:	mov    0x0(%rip),%rdi        # 2a6c <pgot_zlib_tr_init_data_pgot+0x1dc>
			2a68: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2a49, pgot_static_ltree_data_pgot

```asm
    2a42:	mov    %dx,-0x42(%rbp)
    2a46:	mov    0x0(%rip),%rdx        # 2a4d <pgot_zlib_tr_init_data_pgot+0x1bd>
			2a49: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a4d:	mov    $0x8,%r9d
    2a53:	mov    %r9w,0x2(%rdx,%rax,1)
    2a59:	add    $0x4,%rax
    2a5d:	cmp    $0x480,%rax
    2a63:	jne    2a46 <pgot_zlib_tr_init_data_pgot+0x1b6>
    2a65:	mov    0x0(%rip),%rdi        # 2a6c <pgot_zlib_tr_init_data_pgot+0x1dc>
			2a68: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a6c:	lea    -0x50(%rbp),%rdx
    2a70:	mov    $0x11f,%esi
    2a75:	xor    %ebx,%ebx
    2a77:	lea    0x98(%rcx),%eax
    2a7d:	mov    %ax,-0x40(%rbp)
    2a81:	call   17a0 <gen_codes>
    2a86:	mov    0x0(%rip),%rax        # 2a8d <pgot_zlib_tr_init_data_pgot+0x1fd>
			2a89: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    2a8d:	lea    0x0(,%rbx,4),%r12
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2a68, pgot_static_ltree_data_pgot

```asm
    2a63:	jne    2a46 <pgot_zlib_tr_init_data_pgot+0x1b6>
    2a65:	mov    0x0(%rip),%rdi        # 2a6c <pgot_zlib_tr_init_data_pgot+0x1dc>
			2a68: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    2a6c:	lea    -0x50(%rbp),%rdx
    2a70:	mov    $0x11f,%esi
    2a75:	xor    %ebx,%ebx
    2a77:	lea    0x98(%rcx),%eax
    2a7d:	mov    %ax,-0x40(%rbp)
    2a81:	call   17a0 <gen_codes>
    2a86:	mov    0x0(%rip),%rax        # 2a8d <pgot_zlib_tr_init_data_pgot+0x1fd>
			2a89: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    2a8d:	lea    0x0(,%rbx,4),%r12
    2a95:	mov    $0x5,%r8d
    2a9b:	movslq %ebx,%rsi
    2a9e:	mov    %r8w,0x2(%rax,%r12,1)
    2aa4:	cmp    $0xff,%rsi
    2aab:	ja     2caa <pgot_zlib_tr_init_data_pgot+0x41a>
    2ab1:	movzbl 0x0(%rbx),%eax
			2ab4: R_X86_64_32S	byte_rev_table
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2a89, pgot_static_dtree_data_pgot

```asm
    2a81:	call   17a0 <gen_codes>
    2a86:	mov    0x0(%rip),%rax        # 2a8d <pgot_zlib_tr_init_data_pgot+0x1fd>
			2a89: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    2a8d:	lea    0x0(,%rbx,4),%r12
    2a95:	mov    $0x5,%r8d
    2a9b:	movslq %ebx,%rsi
    2a9e:	mov    %r8w,0x2(%rax,%r12,1)
    2aa4:	cmp    $0xff,%rsi
    2aab:	ja     2caa <pgot_zlib_tr_init_data_pgot+0x41a>
    2ab1:	movzbl 0x0(%rbx),%eax
			2ab4: R_X86_64_32S	byte_rev_table
    2ab8:	mov    0x0(%rip),%rdx        # 2abf <pgot_zlib_tr_init_data_pgot+0x22f>
			2abb: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    2abf:	add    $0x1,%rbx
    2ac3:	shr    $0x3,%eax
    2ac6:	mov    %ax,(%rdx,%r12,1)
    2acb:	cmp    $0x1e,%rbx
    2acf:	jne    2a86 <pgot_zlib_tr_init_data_pgot+0x1f6>
    2ad1:	movl   $0x1,0x0(%rip)        # 2adb <pgot_zlib_tr_init_data_pgot+0x24b>
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2abb, pgot_static_dtree_data_pgot

```asm
			2ab4: R_X86_64_32S	byte_rev_table
    2ab8:	mov    0x0(%rip),%rdx        # 2abf <pgot_zlib_tr_init_data_pgot+0x22f>
			2abb: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    2abf:	add    $0x1,%rbx
    2ac3:	shr    $0x3,%eax
    2ac6:	mov    %ax,(%rdx,%r12,1)
    2acb:	cmp    $0x1e,%rbx
    2acf:	jne    2a86 <pgot_zlib_tr_init_data_pgot+0x1f6>
    2ad1:	movl   $0x1,0x0(%rip)        # 2adb <pgot_zlib_tr_init_data_pgot+0x24b>
			2ad3: R_X86_64_PC32	.bss-0x8
    2adb:	lea    0xbc(%r13),%rax
    2ae2:	xor    %edi,%edi
    2ae4:	xor    %ebx,%ebx
    2ae6:	movq   $0x0,0x1710(%r13)
    2af1:	mov    %rax,0xb40(%r13)
    2af8:	lea    0x9b0(%r13),%rax
    2aff:	mov    %rax,0xb58(%r13)
    2b06:	lea    0xaa4(%r13),%rax
    2b0d:	movq   $0x0,0xb50(%r13)
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2c22, pgot_length_code_data_pgot

```asm
    2c1e:	int3   
    2c1f:	mov    0x0(%rip),%rdx        # 2c26 <pgot_zlib_tr_init_data_pgot+0x396>
			2c22: R_X86_64_PC32	pgot_length_code_data_pgot-0x4
    2c26:	lea    -0x1(%r12),%eax
    2c2b:	xor    %r15d,%r15d
    2c2e:	xor    %r14d,%r14d
    2c31:	cltq   
    2c33:	mov    $0x1,%r9d
    2c39:	movb   $0x1c,(%rdx,%rax,1)
    2c3d:	mov    0x0(%rip),%rax        # 2c44 <pgot_zlib_tr_init_data_pgot+0x3b4>
			2c40: R_X86_64_PC32	pgot_base_dist_data_pgot-0x4
    2c44:	lea    0x0(,%r14,4),%r8
    2c4c:	xor    %ebx,%ebx
    2c4e:	mov    %r15d,(%rax,%r14,4)
    2c52:	jmp    2c65 <pgot_zlib_tr_init_data_pgot+0x3d5>
    2c54:	mov    0x0(%rip),%rax        # 2c5b <pgot_zlib_tr_init_data_pgot+0x3cb>
			2c57: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    2c5b:	movslq %r12d,%r12
    2c5e:	add    $0x1,%ebx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2c40, pgot_base_dist_data_pgot

```asm
    2c39:	movb   $0x1c,(%rdx,%rax,1)
    2c3d:	mov    0x0(%rip),%rax        # 2c44 <pgot_zlib_tr_init_data_pgot+0x3b4>
			2c40: R_X86_64_PC32	pgot_base_dist_data_pgot-0x4
    2c44:	lea    0x0(,%r14,4),%r8
    2c4c:	xor    %ebx,%ebx
    2c4e:	mov    %r15d,(%rax,%r14,4)
    2c52:	jmp    2c65 <pgot_zlib_tr_init_data_pgot+0x3d5>
    2c54:	mov    0x0(%rip),%rax        # 2c5b <pgot_zlib_tr_init_data_pgot+0x3cb>
			2c57: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    2c5b:	movslq %r12d,%r12
    2c5e:	add    $0x1,%ebx
    2c61:	mov    %r14b,(%rax,%r12,1)
    2c65:	mov    0x0(%rip),%rax        # 2c6c <pgot_zlib_tr_init_data_pgot+0x3dc>
			2c68: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    2c6c:	lea    (%rbx,%r15,1),%r12d
    2c70:	mov    (%rax,%r8,1),%ecx
    2c74:	cmp    $0x1f,%ecx
    2c77:	ja     2c7d <pgot_zlib_tr_init_data_pgot+0x3ed>
			2c79: R_X86_64_PC32	.text.unlikely+0x9d8
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2c57, pgot_dist_code_data_pgot

```asm
    2c52:	jmp    2c65 <pgot_zlib_tr_init_data_pgot+0x3d5>
    2c54:	mov    0x0(%rip),%rax        # 2c5b <pgot_zlib_tr_init_data_pgot+0x3cb>
			2c57: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    2c5b:	movslq %r12d,%r12
    2c5e:	add    $0x1,%ebx
    2c61:	mov    %r14b,(%rax,%r12,1)
    2c65:	mov    0x0(%rip),%rax        # 2c6c <pgot_zlib_tr_init_data_pgot+0x3dc>
			2c68: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    2c6c:	lea    (%rbx,%r15,1),%r12d
    2c70:	mov    (%rax,%r8,1),%ecx
    2c74:	cmp    $0x1f,%ecx
    2c77:	ja     2c7d <pgot_zlib_tr_init_data_pgot+0x3ed>
			2c79: R_X86_64_PC32	.text.unlikely+0x9d8
    2c7d:	mov    %r9d,%eax
    2c80:	shl    %cl,%eax
    2c82:	cmp    %eax,%ebx
    2c84:	jl     2c54 <pgot_zlib_tr_init_data_pgot+0x3c4>
    2c86:	add    $0x1,%r14
    2c8a:	cmp    $0x10,%r14
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot, 2c68, pgot_extra_dbits_data_pgot

```asm
    2c61:	mov    %r14b,(%rax,%r12,1)
    2c65:	mov    0x0(%rip),%rax        # 2c6c <pgot_zlib_tr_init_data_pgot+0x3dc>
			2c68: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    2c6c:	lea    (%rbx,%r15,1),%r12d
    2c70:	mov    (%rax,%r8,1),%ecx
    2c74:	cmp    $0x1f,%ecx
    2c77:	ja     2c7d <pgot_zlib_tr_init_data_pgot+0x3ed>
			2c79: R_X86_64_PC32	.text.unlikely+0x9d8
    2c7d:	mov    %r9d,%eax
    2c80:	shl    %cl,%eax
    2c82:	cmp    %eax,%ebx
    2c84:	jl     2c54 <pgot_zlib_tr_init_data_pgot+0x3c4>
    2c86:	add    $0x1,%r14
    2c8a:	cmp    $0x10,%r14
    2c8e:	je     2930 <pgot_zlib_tr_init_data_pgot+0xa0>
    2c94:	mov    %r12d,%r15d
    2c97:	jmp    2c3d <pgot_zlib_tr_init_data_pgot+0x3ad>
    2c99:	mov    $0x0,%rdi
			2c9c: R_X86_64_32S	.data+0x200
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_deflateReset_data_pgot, 2da8, memset

```asm
    2da4:	add    %rdx,%rdx
    2da7:	call   2dac <pgot_zlib_deflateReset_data_pgot+0xac>
			2da8: R_X86_64_PLT32	memset-0x4
    2dac:	movslq 0xac(%rbx),%rax
    2db3:	shl    $0x4,%rax
    2db7:	add    0x0(%rip),%rax        # 2dbe <pgot_zlib_deflateReset_data_pgot+0xbe>
			2dba: R_X86_64_PC32	pgot_configuration_table_data_pgot-0x4
    2dbe:	movzwl 0x2(%rax),%edx
    2dc2:	mov    %edx,0xa8(%rbx)
    2dc8:	movzwl (%rax),%edx
    2dcb:	mov    %edx,0xb4(%rbx)
    2dd1:	movzwl 0x4(%rax),%edx
    2dd5:	mov    %edx,0xb8(%rbx)
    2ddb:	movzwl 0x6(%rax),%eax
    2ddf:	movq   $0x0,0x80(%rbx)
    2dea:	movl   $0x2,0x88(%rbx)
    2df4:	movq   $0x0,0x90(%rbx)
    2dff:	movl   $0x0,0x68(%rbx)
    2e06:	mov    %eax,0xa4(%rbx)
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_deflateReset_data_pgot, 2dba, pgot_configuration_table_data_pgot

```asm
    2db3:	shl    $0x4,%rax
    2db7:	add    0x0(%rip),%rax        # 2dbe <pgot_zlib_deflateReset_data_pgot+0xbe>
			2dba: R_X86_64_PC32	pgot_configuration_table_data_pgot-0x4
    2dbe:	movzwl 0x2(%rax),%edx
    2dc2:	mov    %edx,0xa8(%rbx)
    2dc8:	movzwl (%rax),%edx
    2dcb:	mov    %edx,0xb4(%rbx)
    2dd1:	movzwl 0x4(%rax),%edx
    2dd5:	mov    %edx,0xb8(%rbx)
    2ddb:	movzwl 0x6(%rax),%eax
    2ddf:	movq   $0x0,0x80(%rbx)
    2dea:	movl   $0x2,0x88(%rbx)
    2df4:	movq   $0x0,0x90(%rbx)
    2dff:	movl   $0x0,0x68(%rbx)
    2e06:	mov    %eax,0xa4(%rbx)
    2e0c:	movabs $0x200000000,%rax
    2e16:	mov    %rax,0x9c(%rbx)
    2e1d:	xor    %eax,%eax
    2e1f:	mov    -0x8(%rbp),%rbx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_stored_block_data_pgot, 316c, memcpy

```asm
    3167:	add    0x10(%rbx),%rdi
    316b:	call   3170 <pgot_zlib_tr_stored_block_data_pgot+0x180>
			316c: R_X86_64_PLT32	memcpy-0x4
    3170:	add    %r12d,0x28(%rbx)
    3174:	add    $0x8,%rsp
    3178:	pop    %rbx
    3179:	pop    %r12
    317b:	pop    %r13
    317d:	pop    %r14
    317f:	pop    %rbp
    3180:	ret    
    3181:	int3   
    3182:	cmp    $0x1f,%ecx
    3185:	ja     318b <pgot_zlib_tr_stored_block_data_pgot+0x19b>
			3187: R_X86_64_PC32	.text.unlikely+0xa6f
    318b:	mov    %ecx,%eax
    318d:	mov    %r13d,%edx
    3190:	shl    %cl,%edx
    3192:	lea    0x3(%rax),%ecx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_align_data_pgot, 336d, pgot_static_ltree_data_pgot

```asm
    3363:	mov    %ax,0x1720(%rbx)
    336a:	mov    0x0(%rip),%rax        # 3371 <pgot_zlib_tr_align_data_pgot+0xa1>
			336d: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    3371:	mov    $0x10,%esi
    3376:	mov    %ecx,0x1724(%rbx)
    337c:	movzwl 0x402(%rax),%r12d
    3384:	movzwl 0x400(%rax),%eax
    338b:	sub    %r12d,%esi
    338e:	mov    %eax,%r13d
    3391:	cmp    %ecx,%esi
    3393:	jge    35de <pgot_zlib_tr_align_data_pgot+0x30e>
    3399:	cmp    $0x1f,%edx
    339c:	ja     33a2 <pgot_zlib_tr_align_data_pgot+0xd2>
			339e: R_X86_64_PC32	.text.unlikely+0xb94
    33a2:	movslq 0x28(%rbx),%rdx
    33a6:	mov    %eax,%edi
    33a8:	mov    0x10(%rbx),%rsi
    33ac:	shl    %cl,%edi
    33ae:	mov    %edi,%ecx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_align_data_pgot, 34ec, pgot_static_ltree_data_pgot

```asm
    34e2:	mov    %ax,0x1720(%rbx)
    34e9:	mov    0x0(%rip),%rsi        # 34f0 <pgot_zlib_tr_align_data_pgot+0x220>
			34ec: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    34f0:	mov    %ecx,0x1724(%rbx)
    34f6:	movzwl 0x402(%rsi),%eax
    34fd:	movzwl 0x400(%rsi),%r12d
    3505:	mov    $0x10,%esi
    350a:	sub    %eax,%esi
    350c:	mov    %r12d,%r13d
    350f:	cmp    %ecx,%esi
    3511:	jge    368a <pgot_zlib_tr_align_data_pgot+0x3ba>
    3517:	cmp    $0x1f,%edx
    351a:	ja     3520 <pgot_zlib_tr_align_data_pgot+0x250>
			351c: R_X86_64_PC32	.text.unlikely+0xc1e
    3520:	movslq 0x28(%rbx),%rdx
    3524:	mov    %r12d,%edi
    3527:	mov    0x10(%rbx),%rsi
    352b:	shl    %cl,%edi
    352d:	mov    %edi,%ecx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_deflate_data_pgot, 37cd, pgot_configuration_table_data_pgot

```asm
    37c6:	shl    $0x4,%rax
    37ca:	add    0x0(%rip),%rax        # 37d1 <pgot_zlib_deflate_data_pgot+0xd1>
			37cd: R_X86_64_PC32	pgot_configuration_table_data_pgot-0x4
    37d1:	mov    0x8(%rax),%rax
    37d5:	jmp    37e9 <pgot_zlib_deflate_data_pgot+0xe9>
    37d7:	call   37e3 <pgot_zlib_deflate_data_pgot+0xe3>
    37dc:	pause  
    37de:	lfence 
    37e1:	jmp    37dc <pgot_zlib_deflate_data_pgot+0xdc>
    37e3:	mov    %rax,(%rsp)
    37e7:	ret    
    37e8:	int3   
    37e9:	call   37d7 <pgot_zlib_deflate_data_pgot+0xd7>
    37ee:	lea    -0x2(%rax),%edx
    37f1:	cmp    $0x1,%edx
    37f4:	jbe    3921 <pgot_zlib_deflate_data_pgot+0x221>
    37fa:	test   $0xfffffffd,%eax
    37ff:	je     3931 <pgot_zlib_deflate_data_pgot+0x231>
    3805:	cmp    $0x1,%eax
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_deflate_data_pgot, 385b, memset

```asm
    3857:	add    %rdx,%rdx
    385a:	call   385f <pgot_zlib_deflate_data_pgot+0x15f>
			385b: R_X86_64_PLT32	memset-0x4
    385f:	mov    0x38(%r12),%r15
    3864:	mov    0x20(%r12),%rax
    3869:	mov    0x28(%r15),%edx
    386d:	mov    %rdx,%r14
    3870:	cmp    %rax,%rdx
    3873:	cmova  %eax,%r14d
    3877:	test   %r14d,%r14d
    387a:	je     38c0 <pgot_zlib_deflate_data_pgot+0x1c0>
    387c:	mov    0x18(%r12),%rdi
    3881:	mov    %r14d,%edx
    3884:	test   %rdi,%rdi
    3887:	je     389f <pgot_zlib_deflate_data_pgot+0x19f>
    3889:	mov    0x20(%r15),%rsi
    388d:	mov    %rdx,-0x38(%rbp)
    3891:	call   3896 <pgot_zlib_deflate_data_pgot+0x196>
			3892: R_X86_64_PLT32	memcpy-0x4
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_deflate_data_pgot, 3892, memcpy

```asm
    388d:	mov    %rdx,-0x38(%rbp)
    3891:	call   3896 <pgot_zlib_deflate_data_pgot+0x196>
			3892: R_X86_64_PLT32	memcpy-0x4
    3896:	mov    -0x38(%rbp),%rdx
    389a:	add    %rdx,0x18(%r12)
    389f:	add    %rdx,0x20(%r15)
    38a3:	add    %rdx,0x28(%r12)
    38a8:	sub    %rdx,0x20(%r12)
    38ad:	sub    %r14d,0x28(%r15)
    38b1:	jne    38bb <pgot_zlib_deflate_data_pgot+0x1bb>
    38b3:	mov    0x10(%r15),%rax
    38b7:	mov    %rax,0x20(%r15)
    38bb:	mov    0x20(%r12),%rax
    38c0:	test   %rax,%rax
    38c3:	je     3939 <pgot_zlib_deflate_data_pgot+0x239>
    38c5:	cmp    $0x5,%r13d
    38c9:	jne    3944 <pgot_zlib_deflate_data_pgot+0x244>
    38cb:	mov    -0x30(%rbp),%rdi
    38cf:	mov    $0x1,%eax
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_deflate_data_pgot, 3a3b, memcpy

```asm
    3a36:	mov    %rdx,-0x38(%rbp)
    3a3a:	call   3a3f <pgot_zlib_deflate_data_pgot+0x33f>
			3a3b: R_X86_64_PLT32	memcpy-0x4
    3a3f:	mov    -0x38(%rbp),%rdx
    3a43:	add    %rdx,0x18(%r12)
    3a48:	add    %rdx,0x20(%r15)
    3a4c:	add    %rdx,0x28(%r12)
    3a51:	sub    %rdx,0x20(%r12)
    3a56:	sub    %r14d,0x28(%r15)
    3a5a:	je     3bac <pgot_zlib_deflate_data_pgot+0x4ac>
    3a60:	mov    0x20(%r12),%rax
    3a65:	test   %rax,%rax
    3a68:	je     3939 <pgot_zlib_deflate_data_pgot+0x239>
    3a6e:	mov    -0x30(%rbp),%rdx
    3a72:	mov    0x8(%r12),%rax
    3a77:	cmpl   $0x29a,0x8(%rdx)
    3a7e:	jne    3ab0 <pgot_zlib_deflate_data_pgot+0x3b0>
    3a80:	test   %rax,%rax
    3a83:	je     390d <pgot_zlib_deflate_data_pgot+0x20d>
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_deflate_data_pgot, 3b62, memcpy

```asm
    3b5e:	mov    %r15,%rdx
    3b61:	call   3b66 <pgot_zlib_deflate_data_pgot+0x466>
			3b62: R_X86_64_PLT32	memcpy-0x4
    3b66:	add    %r15,0x18(%r12)
    3b6b:	add    %r15,0x20(%r14)
    3b6f:	add    %r15,0x28(%r12)
    3b74:	sub    %r15,0x20(%r12)
    3b79:	sub    %r13d,0x28(%r14)
    3b7d:	jne    3b87 <pgot_zlib_deflate_data_pgot+0x487>
    3b7f:	mov    0x10(%r14),%rax
    3b83:	mov    %rax,0x20(%r14)
    3b87:	mov    -0x30(%rbp),%rax
    3b8b:	mov    0x28(%rax),%edx
    3b8e:	movl   $0xffffffff,0x2c(%rax)
    3b95:	xor    %eax,%eax
    3b97:	test   %edx,%edx
    3b99:	sete   %al
    3b9c:	add    $0x10,%rsp
    3ba0:	pop    %rbx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_flush_block_data_pgot, 3d0d, pgot_bl_order_data_pgot

```asm
    3d05:	call   1900 <build_tree>
    3d0a:	mov    0x0(%rip),%rcx        # 3d11 <pgot_zlib_tr_flush_block_data_pgot+0xc1>
			3d0d: R_X86_64_PC32	pgot_bl_order_data_pgot-0x4
    3d11:	movzbl (%rcx,%rbx,1),%edx
    3d15:	mov    %ebx,%eax
    3d17:	cmp    $0x26,%rdx
    3d1b:	ja     45ff <pgot_zlib_tr_flush_block_data_pgot+0x9af>
    3d21:	cmpw   $0x0,0xaa6(%r12,%rdx,4)
    3d2b:	jne    4376 <pgot_zlib_tr_flush_block_data_pgot+0x726>
    3d31:	sub    $0x1,%rbx
    3d35:	cmp    $0x2,%rbx
    3d39:	jne    3d11 <pgot_zlib_tr_flush_block_data_pgot+0xc1>
    3d3b:	mov    $0x17,%edx
    3d40:	mov    $0x3,%ebx
    3d45:	mov    $0x2,%eax
    3d4a:	mov    0x1708(%r12),%rdi
    3d52:	add    0x1700(%r12),%rdx
    3d5a:	mov    %rdx,0x1700(%r12)
    3d62:	add    $0xa,%rdx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_flush_block_data_pgot, 4103, pgot_bl_order_data_pgot

```asm
    40fe:	je     4147 <pgot_zlib_tr_flush_block_data_pgot+0x4f7>
    4100:	mov    0x0(%rip),%rdx        # 4107 <pgot_zlib_tr_flush_block_data_pgot+0x4b7>
			4103: R_X86_64_PC32	pgot_bl_order_data_pgot-0x4
    4107:	movzbl (%rdx,%rbx,1),%edx
    410b:	movslq %edx,%r15
    410e:	cmp    $0xd,%ecx
    4111:	jg     4057 <pgot_zlib_tr_flush_block_data_pgot+0x407>
    4117:	cmp    $0x26,%dl
    411a:	ja     45df <pgot_zlib_tr_flush_block_data_pgot+0x98f>
    4120:	movzwl 0xaa6(%r12,%r15,4),%r15d
    4129:	cmp    $0x1f,%ecx
    412c:	ja     4132 <pgot_zlib_tr_flush_block_data_pgot+0x4e2>
			412e: R_X86_64_PC32	.text.unlikely+0xec6
    4132:	mov    %ecx,%esi
    4134:	mov    %r15d,%edx
    4137:	shl    %cl,%edx
    4139:	lea    0x3(%rsi),%ecx
    413c:	or     0x1720(%r12),%dx
    4145:	jmp    40e6 <pgot_zlib_tr_flush_block_data_pgot+0x496>
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_flush_block_data_pgot, 42d7, pgot_static_ltree_data_pgot

```asm
    42cb:	mov    %ax,0x1720(%r12)
    42d4:	mov    0x0(%rip),%rsi        # 42db <pgot_zlib_tr_flush_block_data_pgot+0x68b>
			42d7: R_X86_64_PC32	pgot_static_ltree_data_pgot-0x4
    42db:	mov    %r12,%rdi
    42de:	mov    %edx,0x1724(%r12)
    42e6:	mov    0x0(%rip),%rdx        # 42ed <pgot_zlib_tr_flush_block_data_pgot+0x69d>
			42e9: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    42ed:	call   1220 <compress_block>
    42f2:	mov    0x1708(%r12),%rax
    42fa:	add    0x1710(%r12),%rax
    4302:	add    $0x3,%rax
    4306:	mov    %rax,0x1710(%r12)
    430e:	jmp    4195 <pgot_zlib_tr_flush_block_data_pgot+0x545>
    4313:	mov    0x1724(%r12),%eax
    431b:	cmp    $0x8,%eax
    431e:	jg     4419 <pgot_zlib_tr_flush_block_data_pgot+0x7c9>
    4324:	test   %eax,%eax
    4326:	jle    4346 <pgot_zlib_tr_flush_block_data_pgot+0x6f6>
    4328:	movzwl 0x1720(%r12),%ecx
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_flush_block_data_pgot, 42e9, pgot_static_dtree_data_pgot

```asm
    42de:	mov    %edx,0x1724(%r12)
    42e6:	mov    0x0(%rip),%rdx        # 42ed <pgot_zlib_tr_flush_block_data_pgot+0x69d>
			42e9: R_X86_64_PC32	pgot_static_dtree_data_pgot-0x4
    42ed:	call   1220 <compress_block>
    42f2:	mov    0x1708(%r12),%rax
    42fa:	add    0x1710(%r12),%rax
    4302:	add    $0x3,%rax
    4306:	mov    %rax,0x1710(%r12)
    430e:	jmp    4195 <pgot_zlib_tr_flush_block_data_pgot+0x545>
    4313:	mov    0x1724(%r12),%eax
    431b:	cmp    $0x8,%eax
    431e:	jg     4419 <pgot_zlib_tr_flush_block_data_pgot+0x7c9>
    4324:	test   %eax,%eax
    4326:	jle    4346 <pgot_zlib_tr_flush_block_data_pgot+0x6f6>
    4328:	movzwl 0x1720(%r12),%ecx
    4331:	movslq 0x28(%r12),%rax
    4336:	mov    0x10(%r12),%rdx
    433b:	lea    0x1(%rax),%esi
    433e:	mov    %esi,0x28(%r12)
```

## 03_zlib_deflate/retpoline/data_pgot: deflate_stored, 470d, memcpy

```asm
    4708:	mov    %rdx,-0x30(%rbp)
    470c:	call   4711 <deflate_stored+0xd1>
			470d: R_X86_64_PLT32	memcpy-0x4
    4711:	mov    -0x30(%rbp),%rdx
    4715:	add    %rdx,0x18(%r14)
    4719:	add    %rdx,0x20(%r13)
    471d:	add    %rdx,0x28(%r14)
    4721:	sub    %rdx,0x20(%r14)
    4725:	sub    %r15d,0x28(%r13)
    4729:	jne    4733 <deflate_stored+0xf3>
    472b:	mov    0x10(%r13),%rax
    472f:	mov    %rax,0x20(%r13)
    4733:	mov    (%rbx),%rax
    4736:	mov    0x20(%rax),%rax
    473a:	test   %rax,%rax
    473d:	je     48f3 <deflate_stored+0x2b3>
    4743:	mov    0x94(%rbx),%eax
    4749:	mov    0x80(%rbx),%rcx
    4750:	mov    0x38(%rbx),%edi
```

## 03_zlib_deflate/retpoline/data_pgot: deflate_stored, 480b, memcpy

```asm
    4806:	mov    %rdx,-0x30(%rbp)
    480a:	call   480f <deflate_stored+0x1cf>
			480b: R_X86_64_PLT32	memcpy-0x4
    480f:	mov    -0x30(%rbp),%rdx
    4813:	add    %rdx,0x18(%r14)
    4817:	mov    -0x40(%rbp),%rcx
    481b:	add    %rdx,0x20(%rcx)
    481f:	add    %rdx,0x28(%r14)
    4823:	sub    %rdx,0x20(%r14)
    4827:	sub    %r15d,0x28(%rcx)
    482b:	jne    4835 <deflate_stored+0x1f5>
    482d:	mov    0x10(%rcx),%rax
    4831:	mov    %rax,0x20(%rcx)
    4835:	mov    (%rbx),%rax
    4838:	mov    0x20(%rax),%rax
    483c:	test   %rax,%rax
    483f:	je     490f <deflate_stored+0x2cf>
    4845:	xor    %eax,%eax
    4847:	cmpl   $0x5,-0x34(%rbp)
```

## 03_zlib_deflate/retpoline/data_pgot: deflate_stored, 48c1, memcpy

```asm
    48bc:	mov    %rdx,-0x30(%rbp)
    48c0:	call   48c5 <deflate_stored+0x285>
			48c1: R_X86_64_PLT32	memcpy-0x4
    48c5:	mov    -0x30(%rbp),%rdx
    48c9:	add    %rdx,0x18(%r14)
    48cd:	mov    -0x40(%rbp),%rcx
    48d1:	add    %rdx,0x20(%rcx)
    48d5:	add    %rdx,0x28(%r14)
    48d9:	sub    %rdx,0x20(%r14)
    48dd:	sub    %r15d,0x28(%rcx)
    48e1:	je     4905 <deflate_stored+0x2c5>
    48e3:	mov    (%rbx),%rax
    48e6:	mov    0x20(%rax),%rax
    48ea:	test   %rax,%rax
    48ed:	jne    4765 <deflate_stored+0x125>
    48f3:	xor    %eax,%eax
    48f5:	add    $0x18,%rsp
    48f9:	pop    %rbx
    48fa:	pop    %r12
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_tally_data_pgot, 49a7, pgot_extra_dbits_data_pgot

```asm
    49a1:	mov    %r15d,%r13d
    49a4:	mov    0x0(%rip),%r14        # 49ab <pgot_zlib_tr_tally_data_pgot+0x8b>
			49a7: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
    49ab:	xor    %ebx,%ebx
    49ad:	mov    0x94(%r12),%ecx
    49b5:	mov    0x80(%r12),%r8
    49bd:	shl    $0x3,%r13
    49c1:	movslq %ebx,%rsi
    49c4:	cmp    $0x3c,%rsi
    49c8:	ja     4ab7 <pgot_zlib_tr_tally_data_pgot+0x197>
    49ce:	movzwl 0x9b0(%r12,%rbx,4),%edx
    49d7:	movslq (%r14,%rbx,4),%rax
    49db:	add    $0x1,%rbx
    49df:	add    $0x5,%rax
    49e3:	imul   %rdx,%rax
    49e7:	add    %rax,%r13
    49ea:	cmp    $0x1e,%rbx
    49ee:	jne    49c1 <pgot_zlib_tr_tally_data_pgot+0xa1>
    49f0:	mov    %r15d,%eax
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_tally_data_pgot, 4a2a, pgot_length_code_data_pgot

```asm
    4a26:	int3   
    4a27:	mov    0x0(%rip),%rax        # 4a2e <pgot_zlib_tr_tally_data_pgot+0x10e>
			4a2a: R_X86_64_PC32	pgot_length_code_data_pgot-0x4
    4a2e:	mov    %edx,%edx
    4a30:	lea    -0x1(%rsi),%ebx
    4a33:	addl   $0x1,0x1718(%r12)
    4a3c:	movzbl (%rax,%rdx,1),%eax
    4a40:	lea    0x101(%rax),%r13
    4a47:	cmp    $0x23c,%r13
    4a4e:	ja     4ae7 <pgot_zlib_tr_tally_data_pgot+0x1c7>
    4a54:	addw   $0x1,0xbc(%r12,%r13,4)
    4a5e:	mov    0x0(%rip),%rdx        # 4a65 <pgot_zlib_tr_tally_data_pgot+0x145>
			4a61: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    4a65:	cmp    $0xff,%ebx
    4a6b:	jbe    4a92 <pgot_zlib_tr_tally_data_pgot+0x172>
    4a6d:	mov    %ebx,%esi
    4a6f:	shr    $0x7,%esi
    4a72:	lea    0x100(%rsi),%eax
    4a78:	movzbl (%rdx,%rax,1),%eax
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_tally_data_pgot, 4a61, pgot_dist_code_data_pgot

```asm
    4a54:	addw   $0x1,0xbc(%r12,%r13,4)
    4a5e:	mov    0x0(%rip),%rdx        # 4a65 <pgot_zlib_tr_tally_data_pgot+0x145>
			4a61: R_X86_64_PC32	pgot_dist_code_data_pgot-0x4
    4a65:	cmp    $0xff,%ebx
    4a6b:	jbe    4a92 <pgot_zlib_tr_tally_data_pgot+0x172>
    4a6d:	mov    %ebx,%esi
    4a6f:	shr    $0x7,%esi
    4a72:	lea    0x100(%rsi),%eax
    4a78:	movzbl (%rdx,%rax,1),%eax
    4a7c:	movslq %eax,%rbx
    4a7f:	cmp    $0x3c,%al
    4a81:	ja     4ad6 <pgot_zlib_tr_tally_data_pgot+0x1b6>
    4a83:	addw   $0x1,0x9b0(%r12,%rbx,4)
    4a8d:	jmp    4985 <pgot_zlib_tr_tally_data_pgot+0x65>
    4a92:	mov    %ebx,%esi
    4a94:	movzbl (%rdx,%rsi,1),%eax
    4a98:	jmp    4a7c <pgot_zlib_tr_tally_data_pgot+0x15c>
    4a9a:	sub    %r8,%rcx
    4a9d:	shr    $0x3,%r13
```

## 03_zlib_deflate/retpoline/data_pgot: deflate_slow, 4d52, memcpy

```asm
    4d4d:	mov    %rdx,-0x30(%rbp)
    4d51:	call   4d56 <deflate_slow+0x246>
			4d52: R_X86_64_PLT32	memcpy-0x4
    4d56:	mov    -0x30(%rbp),%rdx
    4d5a:	add    %rdx,0x18(%r13)
    4d5e:	mov    -0x38(%rbp),%rcx
    4d62:	add    %rdx,0x20(%rcx)
    4d66:	add    %rdx,0x28(%r13)
    4d6a:	sub    %rdx,0x20(%r13)
    4d6e:	sub    %r15d,0x28(%rcx)
    4d72:	jne    4d7c <deflate_slow+0x26c>
    4d74:	mov    0x10(%rcx),%rax
    4d78:	mov    %rax,0x20(%rcx)
    4d7c:	mov    (%rbx),%rax
    4d7f:	mov    0x20(%rax),%rax
    4d83:	test   %rax,%rax
    4d86:	je     4f06 <deflate_slow+0x3f6>
    4d8c:	mov    0x9c(%rbx),%eax
    4d92:	cmp    $0x105,%eax
```

## 03_zlib_deflate/retpoline/data_pgot: deflate_slow, 4eb1, memcpy

```asm
    4eac:	mov    %r8,-0x30(%rbp)
    4eb0:	call   4eb5 <deflate_slow+0x3a5>
			4eb1: R_X86_64_PLT32	memcpy-0x4
    4eb5:	add    %r13,0x18(%r15)
    4eb9:	mov    -0x38(%rbp),%ecx
    4ebc:	mov    -0x30(%rbp),%r8
    4ec0:	add    %r13,0x20(%r8)
    4ec4:	add    %r13,0x28(%r15)
    4ec8:	sub    %r13,0x20(%r15)
    4ecc:	sub    %ecx,0x28(%r8)
    4ed0:	jne    4eda <deflate_slow+0x3ca>
    4ed2:	mov    0x10(%r8),%rax
    4ed6:	mov    %rax,0x20(%r8)
    4eda:	mov    0x94(%rbx),%eax
    4ee0:	mov    (%rbx),%r15
    4ee3:	add    $0x1,%eax
    4ee6:	mov    %eax,0x94(%rbx)
    4eec:	mov    0x9c(%rbx),%eax
    4ef2:	sub    $0x1,%eax
```

## 03_zlib_deflate/retpoline/data_pgot: deflate_slow, 4ff5, memcpy

```asm
    4ff0:	mov    %rdx,-0x30(%rbp)
    4ff4:	call   4ff9 <deflate_slow+0x4e9>
			4ff5: R_X86_64_PLT32	memcpy-0x4
    4ff9:	mov    -0x30(%rbp),%rdx
    4ffd:	add    %rdx,0x18(%r14)
    5001:	mov    -0x38(%rbp),%rcx
    5005:	add    %rdx,0x20(%rcx)
    5009:	add    %rdx,0x28(%r14)
    500d:	sub    %rdx,0x20(%r14)
    5011:	sub    %r15d,0x28(%rcx)
    5015:	je     5040 <deflate_slow+0x530>
    5017:	mov    (%rbx),%rax
    501a:	mov    0x20(%rax),%rax
    501e:	test   %rax,%rax
    5021:	je     5074 <deflate_slow+0x564>
    5023:	xor    %eax,%eax
    5025:	cmp    $0x5,%r12d
    5029:	sete   %al
    502c:	add    $0x10,%rsp
```

## 03_zlib_deflate/retpoline/data_pgot: deflate_fast, 5254, memcpy

```asm
    524f:	mov    %rdx,-0x30(%rbp)
    5253:	call   5258 <deflate_fast+0x1c8>
			5254: R_X86_64_PLT32	memcpy-0x4
    5258:	mov    -0x30(%rbp),%rdx
    525c:	add    %rdx,0x18(%r13)
    5260:	add    %rdx,0x20(%r12)
    5265:	add    %rdx,0x28(%r13)
    5269:	sub    %rdx,0x20(%r13)
    526d:	sub    %r15d,0x28(%r12)
    5272:	jne    527e <deflate_fast+0x1ee>
    5274:	mov    0x10(%r12),%rax
    5279:	mov    %rax,0x20(%r12)
    527e:	mov    (%rbx),%rax
    5281:	mov    0x20(%rax),%rax
    5285:	test   %rax,%rax
    5288:	jne    50af <deflate_fast+0x1f>
    528e:	add    $0x18,%rsp
    5292:	xor    %eax,%eax
    5294:	pop    %rbx
```

## 03_zlib_deflate/retpoline/data_pgot: deflate_fast, 53f9, memcpy

```asm
    53f4:	mov    %rdx,-0x30(%rbp)
    53f8:	call   53fd <deflate_fast+0x36d>
			53f9: R_X86_64_PLT32	memcpy-0x4
    53fd:	mov    -0x30(%rbp),%rdx
    5401:	add    %rdx,0x18(%r14)
    5405:	mov    -0x40(%rbp),%rcx
    5409:	add    %rdx,0x20(%rcx)
    540d:	add    %rdx,0x28(%r14)
    5411:	sub    %rdx,0x20(%r14)
    5415:	sub    %r15d,0x28(%rcx)
    5419:	je     5444 <deflate_fast+0x3b4>
    541b:	mov    (%rbx),%rax
    541e:	mov    0x20(%rax),%rax
    5422:	test   %rax,%rax
    5425:	je     544e <deflate_fast+0x3be>
    5427:	xor    %eax,%eax
    5429:	cmpl   $0x5,-0x34(%rbp)
    542d:	sete   %al
    5430:	add    $0x18,%rsp
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot.cold, 9f7, pgot_extra_dbits_data_pgot

```asm
			9f0: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     9f4:	mov    0x0(%rip),%rax        # 9fb <pgot_zlib_tr_init_data_pgot.cold+0x1f>
			9f7: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
     9fb:	mov    -0x58(%rbp),%r8
     9ff:	mov    $0x1,%r9d
     a05:	mov    (%rax,%r8,1),%ecx
     a09:	jmp    a0e <pgot_zlib_tr_init_data_pgot.cold+0x32>
			a0a: R_X86_64_PC32	.text+0x2c79
     a0e:	movslq %ecx,%rdx
     a11:	mov    $0x1,%esi
     a16:	mov    $0x0,%rdi
			a19: R_X86_64_32S	.data+0x13c0
     a1d:	mov    %r8,-0x58(%rbp)
     a21:	call   a26 <pgot_zlib_tr_init_data_pgot.cold+0x4a>
			a22: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a26:	mov    0x0(%rip),%rax        # a2d <pgot_zlib_tr_init_data_pgot.cold+0x51>
			a29: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
     a2d:	mov    -0x58(%rbp),%r8
     a31:	mov    $0x1,%r9d
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot.cold, a29, pgot_extra_lbits_data_pgot

```asm
			a22: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a26:	mov    0x0(%rip),%rax        # a2d <pgot_zlib_tr_init_data_pgot.cold+0x51>
			a29: R_X86_64_PC32	pgot_extra_lbits_data_pgot-0x4
     a2d:	mov    -0x58(%rbp),%r8
     a31:	mov    $0x1,%r9d
     a37:	mov    (%rax,%r8,1),%ecx
     a3b:	jmp    a40 <pgot_zlib_tr_init_data_pgot.cold+0x64>
			a3c: R_X86_64_PC32	.text+0x2910
     a40:	movslq %ecx,%rdx
     a43:	mov    $0x1,%esi
     a48:	mov    $0x0,%rdi
			a4b: R_X86_64_32S	.data+0x1380
     a4f:	mov    %eax,-0x58(%rbp)
     a52:	call   a57 <pgot_zlib_tr_init_data_pgot.cold+0x7b>
			a53: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a57:	mov    0x0(%rip),%rdx        # a5e <pgot_zlib_tr_init_data_pgot.cold+0x82>
			a5a: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
     a5e:	mov    -0x58(%rbp),%eax
     a61:	mov    $0x1,%r8d
```

## 03_zlib_deflate/retpoline/data_pgot: pgot_zlib_tr_init_data_pgot.cold, a5a, pgot_extra_dbits_data_pgot

```asm
			a53: R_X86_64_PLT32	__ubsan_handle_shift_out_of_bounds-0x4
     a57:	mov    0x0(%rip),%rdx        # a5e <pgot_zlib_tr_init_data_pgot.cold+0x82>
			a5a: R_X86_64_PC32	pgot_extra_dbits_data_pgot-0x4
     a5e:	mov    -0x58(%rbp),%eax
     a61:	mov    $0x1,%r8d
     a67:	mov    (%rdx,%r14,1),%ecx
     a6b:	sub    $0x7,%ecx
     a6e:	jmp    a73 <pgot_zlib_tr_stored_block_data_pgot.cold>
			a6f: R_X86_64_PC32	.text+0x298b

```

## 03_zlib_deflate/retpoline/func_pgot: fill_window, a7c, pgot_memcpy_table_func_pgot

```asm
     a76:	mov    %rbx,%rdx
     a79:	mov    0x0(%rip),%rax        # a80 <fill_window+0x110>
			a7c: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     a80:	jmp    a94 <fill_window+0x124>
     a82:	call   a8e <fill_window+0x11e>
     a87:	pause  
     a89:	lfence 
     a8c:	jmp    a87 <fill_window+0x117>
     a8e:	mov    %rax,(%rsp)
     a92:	ret    
     a93:	int3   
     a94:	call   a82 <fill_window+0x112>
     a99:	mov    -0x70(%rbp),%rax
     a9d:	mov    -0x58(%rbp),%rcx
     aa1:	add    %rbx,(%rax)
     aa4:	add    %rbx,0x10(%rax)
     aa8:	mov    -0x74(%rbp),%eax
     aab:	add    0x9c(%rcx),%eax
     ab1:	mov    %eax,-0x5c(%rbp)
```

## 03_zlib_deflate/retpoline/func_pgot: fill_window, d3b, pgot_memcpy_table_func_pgot

```asm
     d35:	mov    %rcx,%r14
     d38:	mov    0x0(%rip),%rax        # d3f <fill_window+0x3cf>
			d3b: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     d3f:	lea    (%rdi,%r15,1),%rsi
     d43:	mov    %r15,%rdx
     d46:	jmp    d5a <fill_window+0x3ea>
     d48:	call   d54 <fill_window+0x3e4>
     d4d:	pause  
     d4f:	lfence 
     d52:	jmp    d4d <fill_window+0x3dd>
     d54:	mov    %rax,(%rsp)
     d58:	ret    
     d59:	int3   
     d5a:	call   d48 <fill_window+0x3d8>
     d5f:	mov    0x6c(%r14),%ecx
     d63:	mov    -0x94(%rbp),%r8d
     d6a:	xor    %esi,%esi
     d6c:	mov    0x60(%r14),%rax
     d70:	sub    %r8d,0x98(%r14)
```

## 03_zlib_deflate/retpoline/func_pgot: pgot_zlib_deflateReset_func_pgot, 3379, pgot_memset_table_func_pgot

```asm
    3373:	lea    -0x1(%rax),%edx
    3376:	mov    0x0(%rip),%rax        # 337d <pgot_zlib_deflateReset_func_pgot+0xad>
			3379: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    337d:	add    %rdx,%rdx
    3380:	jmp    3394 <pgot_zlib_deflateReset_func_pgot+0xc4>
    3382:	call   338e <pgot_zlib_deflateReset_func_pgot+0xbe>
    3387:	pause  
    3389:	lfence 
    338c:	jmp    3387 <pgot_zlib_deflateReset_func_pgot+0xb7>
    338e:	mov    %rax,(%rsp)
    3392:	ret    
    3393:	int3   
    3394:	call   3382 <pgot_zlib_deflateReset_func_pgot+0xb2>
    3399:	movslq 0xac(%rbx),%r12
    33a0:	cmp    $0x9,%r12
    33a4:	ja     348a <pgot_zlib_deflateReset_func_pgot+0x1ba>
    33aa:	mov    %r12,%rax
    33ad:	shl    $0x4,%rax
    33b1:	movzwl 0x0(%rax),%eax
```

## 03_zlib_deflate/retpoline/func_pgot: pgot_zlib_tr_stored_block_func_pgot, 37ea, pgot_memcpy_table_func_pgot

```asm
    37e3:	movslq 0x28(%rbx),%rdi
    37e7:	mov    0x0(%rip),%rax        # 37ee <pgot_zlib_tr_stored_block_func_pgot+0x17e>
			37ea: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    37ee:	add    0x10(%rbx),%rdi
    37f2:	jmp    3806 <pgot_zlib_tr_stored_block_func_pgot+0x196>
    37f4:	call   3800 <pgot_zlib_tr_stored_block_func_pgot+0x190>
    37f9:	pause  
    37fb:	lfence 
    37fe:	jmp    37f9 <pgot_zlib_tr_stored_block_func_pgot+0x189>
    3800:	mov    %rax,(%rsp)
    3804:	ret    
    3805:	int3   
    3806:	call   37f4 <pgot_zlib_tr_stored_block_func_pgot+0x184>
    380b:	add    %r12d,0x28(%rbx)
    380f:	add    $0x8,%rsp
    3813:	pop    %rbx
    3814:	pop    %r12
    3816:	pop    %r13
    3818:	pop    %r14
```

## 03_zlib_deflate/retpoline/func_pgot: pgot_zlib_deflate_func_pgot, 3ef4, pgot_memset_table_func_pgot

```asm
    3eee:	lea    -0x1(%rax),%edx
    3ef1:	mov    0x0(%rip),%rax        # 3ef8 <pgot_zlib_deflate_func_pgot+0x168>
			3ef4: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    3ef8:	add    %rdx,%rdx
    3efb:	jmp    3f0f <pgot_zlib_deflate_func_pgot+0x17f>
    3efd:	call   3f09 <pgot_zlib_deflate_func_pgot+0x179>
    3f02:	pause  
    3f04:	lfence 
    3f07:	jmp    3f02 <pgot_zlib_deflate_func_pgot+0x172>
    3f09:	mov    %rax,(%rsp)
    3f0d:	ret    
    3f0e:	int3   
    3f0f:	call   3efd <pgot_zlib_deflate_func_pgot+0x16d>
    3f14:	mov    0x38(%r12),%r15
    3f19:	mov    0x20(%r12),%rax
    3f1e:	mov    0x28(%r15),%edx
    3f22:	mov    %rdx,%r14
    3f25:	cmp    %rax,%rdx
    3f28:	cmova  %eax,%r14d
```

## 03_zlib_deflate/retpoline/func_pgot: pgot_zlib_deflate_func_pgot, 3f47, memcpy

```asm
    3f42:	mov    %rdx,-0x38(%rbp)
    3f46:	call   3f4b <pgot_zlib_deflate_func_pgot+0x1bb>
			3f47: R_X86_64_PLT32	memcpy-0x4
    3f4b:	mov    -0x38(%rbp),%rdx
    3f4f:	add    %rdx,0x18(%r12)
    3f54:	add    %rdx,0x20(%r15)
    3f58:	add    %rdx,0x28(%r12)
    3f5d:	sub    %rdx,0x20(%r12)
    3f62:	sub    %r14d,0x28(%r15)
    3f66:	jne    3f70 <pgot_zlib_deflate_func_pgot+0x1e0>
    3f68:	mov    0x10(%r15),%rax
    3f6c:	mov    %rax,0x20(%r15)
    3f70:	mov    0x20(%r12),%rax
    3f75:	test   %rax,%rax
    3f78:	je     415e <pgot_zlib_deflate_func_pgot+0x3ce>
    3f7e:	cmp    $0x5,%r13d
    3f82:	jne    3fde <pgot_zlib_deflate_func_pgot+0x24e>
    3f84:	mov    -0x30(%rbp),%rdi
    3f88:	mov    $0x1,%eax
```

## 03_zlib_deflate/retpoline/func_pgot: pgot_zlib_deflate_func_pgot, 40d5, memcpy

```asm
    40d0:	mov    %rdx,-0x38(%rbp)
    40d4:	call   40d9 <pgot_zlib_deflate_func_pgot+0x349>
			40d5: R_X86_64_PLT32	memcpy-0x4
    40d9:	mov    -0x38(%rbp),%rdx
    40dd:	add    %rdx,0x18(%r12)
    40e2:	add    %rdx,0x20(%r15)
    40e6:	add    %rdx,0x28(%r12)
    40eb:	sub    %rdx,0x20(%r12)
    40f0:	sub    %r14d,0x28(%r15)
    40f4:	je     4274 <pgot_zlib_deflate_func_pgot+0x4e4>
    40fa:	mov    0x20(%r12),%rax
    40ff:	test   %rax,%rax
    4102:	je     415e <pgot_zlib_deflate_func_pgot+0x3ce>
    4104:	mov    -0x30(%rbp),%rdx
    4108:	mov    0x8(%r12),%rax
    410d:	cmpl   $0x29a,0x8(%rdx)
    4114:	jne    4178 <pgot_zlib_deflate_func_pgot+0x3e8>
    4116:	test   %rax,%rax
    4119:	je     3fc6 <pgot_zlib_deflate_func_pgot+0x236>
```

## 03_zlib_deflate/retpoline/func_pgot: pgot_zlib_deflate_func_pgot, 422a, memcpy

```asm
    4226:	mov    %r15,%rdx
    4229:	call   422e <pgot_zlib_deflate_func_pgot+0x49e>
			422a: R_X86_64_PLT32	memcpy-0x4
    422e:	add    %r15,0x18(%r12)
    4233:	add    %r15,0x20(%r14)
    4237:	add    %r15,0x28(%r12)
    423c:	sub    %r15,0x20(%r12)
    4241:	sub    %r13d,0x28(%r14)
    4245:	jne    424f <pgot_zlib_deflate_func_pgot+0x4bf>
    4247:	mov    0x10(%r14),%rax
    424b:	mov    %rax,0x20(%r14)
    424f:	mov    -0x30(%rbp),%rax
    4253:	mov    0x28(%rax),%edx
    4256:	movl   $0xffffffff,0x2c(%rax)
    425d:	xor    %eax,%eax
    425f:	test   %edx,%edx
    4261:	sete   %al
    4264:	add    $0x10,%rsp
    4268:	pop    %rbx
```

## 03_zlib_deflate/retpoline/func_pgot: deflate_stored, 4f0d, memcpy

```asm
    4f08:	mov    %rdx,-0x30(%rbp)
    4f0c:	call   4f11 <deflate_stored+0xd1>
			4f0d: R_X86_64_PLT32	memcpy-0x4
    4f11:	mov    -0x30(%rbp),%rdx
    4f15:	add    %rdx,0x18(%r14)
    4f19:	add    %rdx,0x20(%r13)
    4f1d:	add    %rdx,0x28(%r14)
    4f21:	sub    %rdx,0x20(%r14)
    4f25:	sub    %r15d,0x28(%r13)
    4f29:	jne    4f33 <deflate_stored+0xf3>
    4f2b:	mov    0x10(%r13),%rax
    4f2f:	mov    %rax,0x20(%r13)
    4f33:	mov    (%rbx),%rax
    4f36:	mov    0x20(%rax),%rax
    4f3a:	test   %rax,%rax
    4f3d:	je     50f3 <deflate_stored+0x2b3>
    4f43:	mov    0x94(%rbx),%eax
    4f49:	mov    0x80(%rbx),%rcx
    4f50:	mov    0x38(%rbx),%edi
```

## 03_zlib_deflate/retpoline/func_pgot: deflate_stored, 500b, memcpy

```asm
    5006:	mov    %rdx,-0x30(%rbp)
    500a:	call   500f <deflate_stored+0x1cf>
			500b: R_X86_64_PLT32	memcpy-0x4
    500f:	mov    -0x30(%rbp),%rdx
    5013:	add    %rdx,0x18(%r14)
    5017:	mov    -0x40(%rbp),%rcx
    501b:	add    %rdx,0x20(%rcx)
    501f:	add    %rdx,0x28(%r14)
    5023:	sub    %rdx,0x20(%r14)
    5027:	sub    %r15d,0x28(%rcx)
    502b:	jne    5035 <deflate_stored+0x1f5>
    502d:	mov    0x10(%rcx),%rax
    5031:	mov    %rax,0x20(%rcx)
    5035:	mov    (%rbx),%rax
    5038:	mov    0x20(%rax),%rax
    503c:	test   %rax,%rax
    503f:	je     510f <deflate_stored+0x2cf>
    5045:	xor    %eax,%eax
    5047:	cmpl   $0x5,-0x34(%rbp)
```

## 03_zlib_deflate/retpoline/func_pgot: deflate_stored, 50c1, memcpy

```asm
    50bc:	mov    %rdx,-0x30(%rbp)
    50c0:	call   50c5 <deflate_stored+0x285>
			50c1: R_X86_64_PLT32	memcpy-0x4
    50c5:	mov    -0x30(%rbp),%rdx
    50c9:	add    %rdx,0x18(%r14)
    50cd:	mov    -0x40(%rbp),%rcx
    50d1:	add    %rdx,0x20(%rcx)
    50d5:	add    %rdx,0x28(%r14)
    50d9:	sub    %rdx,0x20(%r14)
    50dd:	sub    %r15d,0x28(%rcx)
    50e1:	je     5105 <deflate_stored+0x2c5>
    50e3:	mov    (%rbx),%rax
    50e6:	mov    0x20(%rax),%rax
    50ea:	test   %rax,%rax
    50ed:	jne    4f65 <deflate_stored+0x125>
    50f3:	xor    %eax,%eax
    50f5:	add    $0x18,%rsp
    50f9:	pop    %rbx
    50fa:	pop    %r12
```

## 03_zlib_deflate/retpoline/func_pgot: deflate_slow, 55f2, memcpy

```asm
    55ed:	mov    %rdx,-0x30(%rbp)
    55f1:	call   55f6 <deflate_slow+0x246>
			55f2: R_X86_64_PLT32	memcpy-0x4
    55f6:	mov    -0x30(%rbp),%rdx
    55fa:	add    %rdx,0x18(%r13)
    55fe:	mov    -0x38(%rbp),%rcx
    5602:	add    %rdx,0x20(%rcx)
    5606:	add    %rdx,0x28(%r13)
    560a:	sub    %rdx,0x20(%r13)
    560e:	sub    %r15d,0x28(%rcx)
    5612:	jne    561c <deflate_slow+0x26c>
    5614:	mov    0x10(%rcx),%rax
    5618:	mov    %rax,0x20(%rcx)
    561c:	mov    (%rbx),%rax
    561f:	mov    0x20(%rax),%rax
    5623:	test   %rax,%rax
    5626:	je     57a6 <deflate_slow+0x3f6>
    562c:	mov    0x9c(%rbx),%eax
    5632:	cmp    $0x105,%eax
```

## 03_zlib_deflate/retpoline/func_pgot: deflate_slow, 5751, memcpy

```asm
    574c:	mov    %r8,-0x30(%rbp)
    5750:	call   5755 <deflate_slow+0x3a5>
			5751: R_X86_64_PLT32	memcpy-0x4
    5755:	add    %r13,0x18(%r15)
    5759:	mov    -0x38(%rbp),%ecx
    575c:	mov    -0x30(%rbp),%r8
    5760:	add    %r13,0x20(%r8)
    5764:	add    %r13,0x28(%r15)
    5768:	sub    %r13,0x20(%r15)
    576c:	sub    %ecx,0x28(%r8)
    5770:	jne    577a <deflate_slow+0x3ca>
    5772:	mov    0x10(%r8),%rax
    5776:	mov    %rax,0x20(%r8)
    577a:	mov    0x94(%rbx),%eax
    5780:	mov    (%rbx),%r15
    5783:	add    $0x1,%eax
    5786:	mov    %eax,0x94(%rbx)
    578c:	mov    0x9c(%rbx),%eax
    5792:	sub    $0x1,%eax
```

## 03_zlib_deflate/retpoline/func_pgot: deflate_slow, 5895, memcpy

```asm
    5890:	mov    %rdx,-0x30(%rbp)
    5894:	call   5899 <deflate_slow+0x4e9>
			5895: R_X86_64_PLT32	memcpy-0x4
    5899:	mov    -0x30(%rbp),%rdx
    589d:	add    %rdx,0x18(%r14)
    58a1:	mov    -0x38(%rbp),%rcx
    58a5:	add    %rdx,0x20(%rcx)
    58a9:	add    %rdx,0x28(%r14)
    58ad:	sub    %rdx,0x20(%r14)
    58b1:	sub    %r15d,0x28(%rcx)
    58b5:	je     58e0 <deflate_slow+0x530>
    58b7:	mov    (%rbx),%rax
    58ba:	mov    0x20(%rax),%rax
    58be:	test   %rax,%rax
    58c1:	je     5914 <deflate_slow+0x564>
    58c3:	xor    %eax,%eax
    58c5:	cmp    $0x5,%r12d
    58c9:	sete   %al
    58cc:	add    $0x10,%rsp
```

## 03_zlib_deflate/retpoline/func_pgot: deflate_fast, 5af4, memcpy

```asm
    5aef:	mov    %rdx,-0x30(%rbp)
    5af3:	call   5af8 <deflate_fast+0x1c8>
			5af4: R_X86_64_PLT32	memcpy-0x4
    5af8:	mov    -0x30(%rbp),%rdx
    5afc:	add    %rdx,0x18(%r13)
    5b00:	add    %rdx,0x20(%r12)
    5b05:	add    %rdx,0x28(%r13)
    5b09:	sub    %rdx,0x20(%r13)
    5b0d:	sub    %r15d,0x28(%r12)
    5b12:	jne    5b1e <deflate_fast+0x1ee>
    5b14:	mov    0x10(%r12),%rax
    5b19:	mov    %rax,0x20(%r12)
    5b1e:	mov    (%rbx),%rax
    5b21:	mov    0x20(%rax),%rax
    5b25:	test   %rax,%rax
    5b28:	jne    594f <deflate_fast+0x1f>
    5b2e:	add    $0x18,%rsp
    5b32:	xor    %eax,%eax
    5b34:	pop    %rbx
```

## 03_zlib_deflate/retpoline/func_pgot: deflate_fast, 5c99, memcpy

```asm
    5c94:	mov    %rdx,-0x30(%rbp)
    5c98:	call   5c9d <deflate_fast+0x36d>
			5c99: R_X86_64_PLT32	memcpy-0x4
    5c9d:	mov    -0x30(%rbp),%rdx
    5ca1:	add    %rdx,0x18(%r14)
    5ca5:	mov    -0x40(%rbp),%rcx
    5ca9:	add    %rdx,0x20(%rcx)
    5cad:	add    %rdx,0x28(%r14)
    5cb1:	sub    %rdx,0x20(%r14)
    5cb5:	sub    %r15d,0x28(%rcx)
    5cb9:	je     5ce4 <deflate_fast+0x3b4>
    5cbb:	mov    (%rbx),%rax
    5cbe:	mov    0x20(%rax),%rax
    5cc2:	test   %rax,%rax
    5cc5:	je     5cee <deflate_fast+0x3be>
    5cc7:	xor    %eax,%eax
    5cc9:	cmpl   $0x5,-0x34(%rbp)
    5ccd:	sete   %al
    5cd0:	add    $0x18,%rsp
```

## 03_zlib_deflate/retpoline/origin: fill_window, 2546, memcpy

```asm
    2542:	add    %rax,%rdi
    2545:	call   254a <fill_window+0x10a>
			2546: R_X86_64_PLT32	memcpy-0x4
    254a:	mov    -0x70(%rbp),%rcx
    254e:	mov    -0x74(%rbp),%eax
    2551:	add    %rbx,(%rcx)
    2554:	add    %rbx,0x10(%rcx)
    2558:	mov    -0x58(%rbp),%rbx
    255c:	add    0x9c(%rbx),%eax
    2562:	mov    %eax,-0x5c(%rbp)
    2565:	mov    -0x58(%rbp),%rdi
    2569:	mov    -0x5c(%rbp),%eax
    256c:	mov    %eax,0x9c(%rdi)
    2572:	cmp    $0x2,%eax
    2575:	jbe    25bc <fill_window+0x17c>
    2577:	mov    0x94(%rdi),%ecx
    257d:	mov    0x48(%rdi),%rax
    2581:	mov    %rcx,%rdx
    2584:	movzbl (%rax,%rcx,1),%ebx
```

## 03_zlib_deflate/retpoline/origin: fill_window, 27f1, memcpy

```asm
    27ed:	mov    %r15,%rdx
    27f0:	call   27f5 <fill_window+0x3b5>
			27f1: R_X86_64_PLT32	memcpy-0x4
    27f5:	mov    0x6c(%r14),%ecx
    27f9:	mov    0x60(%r14),%rax
    27fd:	xor    %esi,%esi
    27ff:	mov    -0x94(%rbp),%r8d
    2806:	sub    %r15,0x80(%r14)
    280d:	mov    %rcx,%rdx
    2810:	sub    %r8d,0x98(%r14)
    2817:	lea    (%rax,%rcx,2),%rax
    281b:	sub    %r8d,0x94(%r14)
    2822:	sub    $0x1,%edx
    2825:	not    %rdx
    2828:	lea    (%rax,%rdx,2),%rdi
    282c:	movzwl -0x2(%rax),%ecx
    2830:	sub    $0x2,%rax
    2834:	mov    %ecx,%edx
    2836:	sub    %r8d,%edx
```

## 03_zlib_deflate/retpoline/origin: pgot_zlib_deflateReset_origin, 333a, memset

```asm
    3336:	add    %rdx,%rdx
    3339:	call   333e <pgot_zlib_deflateReset_origin+0xae>
			333a: R_X86_64_PLT32	memset-0x4
    333e:	movslq 0xac(%rbx),%r12
    3345:	cmp    $0x9,%r12
    3349:	ja     342f <pgot_zlib_deflateReset_origin+0x19f>
    334f:	mov    %r12,%rax
    3352:	shl    $0x4,%rax
    3356:	movzwl 0x0(%rax),%eax
			3359: R_X86_64_32S	.rodata+0x182
    335d:	mov    %eax,0xa8(%rbx)
    3363:	cmp    $0x9,%r12
    3367:	ja     3443 <pgot_zlib_deflateReset_origin+0x1b3>
    336d:	mov    %r12,%rax
    3370:	shl    $0x4,%rax
    3374:	movzwl 0x0(%rax),%eax
			3377: R_X86_64_32S	.rodata+0x180
    337b:	mov    %eax,0xb4(%rbx)
    3381:	cmp    $0x9,%r12
```

## 03_zlib_deflate/retpoline/origin: pgot_zlib_tr_stored_block_origin, 378c, memcpy

```asm
    3787:	add    0x10(%rbx),%rdi
    378b:	call   3790 <pgot_zlib_tr_stored_block_origin+0x180>
			378c: R_X86_64_PLT32	memcpy-0x4
    3790:	add    %r12d,0x28(%rbx)
    3794:	add    $0x8,%rsp
    3798:	pop    %rbx
    3799:	pop    %r12
    379b:	pop    %r13
    379d:	pop    %r14
    379f:	pop    %rbp
    37a0:	ret    
    37a1:	int3   
    37a2:	cmp    $0x1f,%ecx
    37a5:	ja     37ab <pgot_zlib_tr_stored_block_origin+0x19b>
			37a7: R_X86_64_PC32	.text.unlikely+0xa06
    37ab:	mov    %ecx,%eax
    37ad:	mov    %r13d,%edx
    37b0:	shl    %cl,%edx
    37b2:	lea    0x3(%rax),%ecx
```

## 03_zlib_deflate/retpoline/origin: pgot_zlib_deflate_origin, 3e75, memset

```asm
    3e71:	add    %rdx,%rdx
    3e74:	call   3e79 <pgot_zlib_deflate_origin+0x169>
			3e75: R_X86_64_PLT32	memset-0x4
    3e79:	mov    0x38(%r12),%r15
    3e7e:	mov    0x20(%r12),%rax
    3e83:	mov    0x28(%r15),%edx
    3e87:	mov    %rdx,%r14
    3e8a:	cmp    %rax,%rdx
    3e8d:	cmova  %eax,%r14d
    3e91:	test   %r14d,%r14d
    3e94:	je     3eda <pgot_zlib_deflate_origin+0x1ca>
    3e96:	mov    0x18(%r12),%rdi
    3e9b:	mov    %r14d,%edx
    3e9e:	test   %rdi,%rdi
    3ea1:	je     3eb9 <pgot_zlib_deflate_origin+0x1a9>
    3ea3:	mov    0x20(%r15),%rsi
    3ea7:	mov    %rdx,-0x38(%rbp)
    3eab:	call   3eb0 <pgot_zlib_deflate_origin+0x1a0>
			3eac: R_X86_64_PLT32	memcpy-0x4
```

## 03_zlib_deflate/retpoline/origin: pgot_zlib_deflate_origin, 3eac, memcpy

```asm
    3ea7:	mov    %rdx,-0x38(%rbp)
    3eab:	call   3eb0 <pgot_zlib_deflate_origin+0x1a0>
			3eac: R_X86_64_PLT32	memcpy-0x4
    3eb0:	mov    -0x38(%rbp),%rdx
    3eb4:	add    %rdx,0x18(%r12)
    3eb9:	add    %rdx,0x20(%r15)
    3ebd:	add    %rdx,0x28(%r12)
    3ec2:	sub    %rdx,0x20(%r12)
    3ec7:	sub    %r14d,0x28(%r15)
    3ecb:	jne    3ed5 <pgot_zlib_deflate_origin+0x1c5>
    3ecd:	mov    0x10(%r15),%rax
    3ed1:	mov    %rax,0x20(%r15)
    3ed5:	mov    0x20(%r12),%rax
    3eda:	test   %rax,%rax
    3edd:	je     40c3 <pgot_zlib_deflate_origin+0x3b3>
    3ee3:	cmp    $0x5,%r13d
    3ee7:	jne    3f43 <pgot_zlib_deflate_origin+0x233>
    3ee9:	mov    -0x30(%rbp),%rdi
    3eed:	mov    $0x1,%eax
```

## 03_zlib_deflate/retpoline/origin: pgot_zlib_deflate_origin, 403a, memcpy

```asm
    4035:	mov    %rdx,-0x38(%rbp)
    4039:	call   403e <pgot_zlib_deflate_origin+0x32e>
			403a: R_X86_64_PLT32	memcpy-0x4
    403e:	mov    -0x38(%rbp),%rdx
    4042:	add    %rdx,0x18(%r12)
    4047:	add    %rdx,0x20(%r15)
    404b:	add    %rdx,0x28(%r12)
    4050:	sub    %rdx,0x20(%r12)
    4055:	sub    %r14d,0x28(%r15)
    4059:	je     41d9 <pgot_zlib_deflate_origin+0x4c9>
    405f:	mov    0x20(%r12),%rax
    4064:	test   %rax,%rax
    4067:	je     40c3 <pgot_zlib_deflate_origin+0x3b3>
    4069:	mov    -0x30(%rbp),%rdx
    406d:	mov    0x8(%r12),%rax
    4072:	cmpl   $0x29a,0x8(%rdx)
    4079:	jne    40dd <pgot_zlib_deflate_origin+0x3cd>
    407b:	test   %rax,%rax
    407e:	je     3f2b <pgot_zlib_deflate_origin+0x21b>
```

## 03_zlib_deflate/retpoline/origin: pgot_zlib_deflate_origin, 418f, memcpy

```asm
    418b:	mov    %r15,%rdx
    418e:	call   4193 <pgot_zlib_deflate_origin+0x483>
			418f: R_X86_64_PLT32	memcpy-0x4
    4193:	add    %r15,0x18(%r12)
    4198:	add    %r15,0x20(%r14)
    419c:	add    %r15,0x28(%r12)
    41a1:	sub    %r15,0x20(%r12)
    41a6:	sub    %r13d,0x28(%r14)
    41aa:	jne    41b4 <pgot_zlib_deflate_origin+0x4a4>
    41ac:	mov    0x10(%r14),%rax
    41b0:	mov    %rax,0x20(%r14)
    41b4:	mov    -0x30(%rbp),%rax
    41b8:	mov    0x28(%rax),%edx
    41bb:	movl   $0xffffffff,0x2c(%rax)
    41c2:	xor    %eax,%eax
    41c4:	test   %edx,%edx
    41c6:	sete   %al
    41c9:	add    $0x10,%rsp
    41cd:	pop    %rbx
```

## 03_zlib_deflate/retpoline/origin: deflate_stored, 4e7d, memcpy

```asm
    4e78:	mov    %rdx,-0x30(%rbp)
    4e7c:	call   4e81 <deflate_stored+0xd1>
			4e7d: R_X86_64_PLT32	memcpy-0x4
    4e81:	mov    -0x30(%rbp),%rdx
    4e85:	add    %rdx,0x18(%r14)
    4e89:	add    %rdx,0x20(%r13)
    4e8d:	add    %rdx,0x28(%r14)
    4e91:	sub    %rdx,0x20(%r14)
    4e95:	sub    %r15d,0x28(%r13)
    4e99:	jne    4ea3 <deflate_stored+0xf3>
    4e9b:	mov    0x10(%r13),%rax
    4e9f:	mov    %rax,0x20(%r13)
    4ea3:	mov    (%rbx),%rax
    4ea6:	mov    0x20(%rax),%rax
    4eaa:	test   %rax,%rax
    4ead:	je     5063 <deflate_stored+0x2b3>
    4eb3:	mov    0x94(%rbx),%eax
    4eb9:	mov    0x80(%rbx),%rcx
    4ec0:	mov    0x38(%rbx),%edi
```

## 03_zlib_deflate/retpoline/origin: deflate_stored, 4f7b, memcpy

```asm
    4f76:	mov    %rdx,-0x30(%rbp)
    4f7a:	call   4f7f <deflate_stored+0x1cf>
			4f7b: R_X86_64_PLT32	memcpy-0x4
    4f7f:	mov    -0x30(%rbp),%rdx
    4f83:	add    %rdx,0x18(%r14)
    4f87:	mov    -0x40(%rbp),%rcx
    4f8b:	add    %rdx,0x20(%rcx)
    4f8f:	add    %rdx,0x28(%r14)
    4f93:	sub    %rdx,0x20(%r14)
    4f97:	sub    %r15d,0x28(%rcx)
    4f9b:	jne    4fa5 <deflate_stored+0x1f5>
    4f9d:	mov    0x10(%rcx),%rax
    4fa1:	mov    %rax,0x20(%rcx)
    4fa5:	mov    (%rbx),%rax
    4fa8:	mov    0x20(%rax),%rax
    4fac:	test   %rax,%rax
    4faf:	je     507f <deflate_stored+0x2cf>
    4fb5:	xor    %eax,%eax
    4fb7:	cmpl   $0x5,-0x34(%rbp)
```

## 03_zlib_deflate/retpoline/origin: deflate_stored, 5031, memcpy

```asm
    502c:	mov    %rdx,-0x30(%rbp)
    5030:	call   5035 <deflate_stored+0x285>
			5031: R_X86_64_PLT32	memcpy-0x4
    5035:	mov    -0x30(%rbp),%rdx
    5039:	add    %rdx,0x18(%r14)
    503d:	mov    -0x40(%rbp),%rcx
    5041:	add    %rdx,0x20(%rcx)
    5045:	add    %rdx,0x28(%r14)
    5049:	sub    %rdx,0x20(%r14)
    504d:	sub    %r15d,0x28(%rcx)
    5051:	je     5075 <deflate_stored+0x2c5>
    5053:	mov    (%rbx),%rax
    5056:	mov    0x20(%rax),%rax
    505a:	test   %rax,%rax
    505d:	jne    4ed5 <deflate_stored+0x125>
    5063:	xor    %eax,%eax
    5065:	add    $0x18,%rsp
    5069:	pop    %rbx
    506a:	pop    %r12
```

## 03_zlib_deflate/retpoline/origin: deflate_slow, 5562, memcpy

```asm
    555d:	mov    %rdx,-0x30(%rbp)
    5561:	call   5566 <deflate_slow+0x246>
			5562: R_X86_64_PLT32	memcpy-0x4
    5566:	mov    -0x30(%rbp),%rdx
    556a:	add    %rdx,0x18(%r13)
    556e:	mov    -0x38(%rbp),%rcx
    5572:	add    %rdx,0x20(%rcx)
    5576:	add    %rdx,0x28(%r13)
    557a:	sub    %rdx,0x20(%r13)
    557e:	sub    %r15d,0x28(%rcx)
    5582:	jne    558c <deflate_slow+0x26c>
    5584:	mov    0x10(%rcx),%rax
    5588:	mov    %rax,0x20(%rcx)
    558c:	mov    (%rbx),%rax
    558f:	mov    0x20(%rax),%rax
    5593:	test   %rax,%rax
    5596:	je     5716 <deflate_slow+0x3f6>
    559c:	mov    0x9c(%rbx),%eax
    55a2:	cmp    $0x105,%eax
```

## 03_zlib_deflate/retpoline/origin: deflate_slow, 56c1, memcpy

```asm
    56bc:	mov    %r8,-0x30(%rbp)
    56c0:	call   56c5 <deflate_slow+0x3a5>
			56c1: R_X86_64_PLT32	memcpy-0x4
    56c5:	add    %r13,0x18(%r15)
    56c9:	mov    -0x38(%rbp),%ecx
    56cc:	mov    -0x30(%rbp),%r8
    56d0:	add    %r13,0x20(%r8)
    56d4:	add    %r13,0x28(%r15)
    56d8:	sub    %r13,0x20(%r15)
    56dc:	sub    %ecx,0x28(%r8)
    56e0:	jne    56ea <deflate_slow+0x3ca>
    56e2:	mov    0x10(%r8),%rax
    56e6:	mov    %rax,0x20(%r8)
    56ea:	mov    0x94(%rbx),%eax
    56f0:	mov    (%rbx),%r15
    56f3:	add    $0x1,%eax
    56f6:	mov    %eax,0x94(%rbx)
    56fc:	mov    0x9c(%rbx),%eax
    5702:	sub    $0x1,%eax
```

## 03_zlib_deflate/retpoline/origin: deflate_slow, 5805, memcpy

```asm
    5800:	mov    %rdx,-0x30(%rbp)
    5804:	call   5809 <deflate_slow+0x4e9>
			5805: R_X86_64_PLT32	memcpy-0x4
    5809:	mov    -0x30(%rbp),%rdx
    580d:	add    %rdx,0x18(%r14)
    5811:	mov    -0x38(%rbp),%rcx
    5815:	add    %rdx,0x20(%rcx)
    5819:	add    %rdx,0x28(%r14)
    581d:	sub    %rdx,0x20(%r14)
    5821:	sub    %r15d,0x28(%rcx)
    5825:	je     5850 <deflate_slow+0x530>
    5827:	mov    (%rbx),%rax
    582a:	mov    0x20(%rax),%rax
    582e:	test   %rax,%rax
    5831:	je     5884 <deflate_slow+0x564>
    5833:	xor    %eax,%eax
    5835:	cmp    $0x5,%r12d
    5839:	sete   %al
    583c:	add    $0x10,%rsp
```

## 03_zlib_deflate/retpoline/origin: deflate_fast, 5a64, memcpy

```asm
    5a5f:	mov    %rdx,-0x30(%rbp)
    5a63:	call   5a68 <deflate_fast+0x1c8>
			5a64: R_X86_64_PLT32	memcpy-0x4
    5a68:	mov    -0x30(%rbp),%rdx
    5a6c:	add    %rdx,0x18(%r13)
    5a70:	add    %rdx,0x20(%r12)
    5a75:	add    %rdx,0x28(%r13)
    5a79:	sub    %rdx,0x20(%r13)
    5a7d:	sub    %r15d,0x28(%r12)
    5a82:	jne    5a8e <deflate_fast+0x1ee>
    5a84:	mov    0x10(%r12),%rax
    5a89:	mov    %rax,0x20(%r12)
    5a8e:	mov    (%rbx),%rax
    5a91:	mov    0x20(%rax),%rax
    5a95:	test   %rax,%rax
    5a98:	jne    58bf <deflate_fast+0x1f>
    5a9e:	add    $0x18,%rsp
    5aa2:	xor    %eax,%eax
    5aa4:	pop    %rbx
```

## 03_zlib_deflate/retpoline/origin: deflate_fast, 5c09, memcpy

```asm
    5c04:	mov    %rdx,-0x30(%rbp)
    5c08:	call   5c0d <deflate_fast+0x36d>
			5c09: R_X86_64_PLT32	memcpy-0x4
    5c0d:	mov    -0x30(%rbp),%rdx
    5c11:	add    %rdx,0x18(%r14)
    5c15:	mov    -0x40(%rbp),%rcx
    5c19:	add    %rdx,0x20(%rcx)
    5c1d:	add    %rdx,0x28(%r14)
    5c21:	sub    %rdx,0x20(%r14)
    5c25:	sub    %r15d,0x28(%rcx)
    5c29:	je     5c54 <deflate_fast+0x3b4>
    5c2b:	mov    (%rbx),%rax
    5c2e:	mov    0x20(%rax),%rax
    5c32:	test   %rax,%rax
    5c35:	je     5c5e <deflate_fast+0x3be>
    5c37:	xor    %eax,%eax
    5c39:	cmpl   $0x5,-0x34(%rbp)
    5c3d:	sete   %al
    5c40:	add    $0x18,%rsp
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_execSequenceLast7_all_pgot.isra.0, 5d3, pgot_memmove_table_all_pgot

```asm
     5cc:	mov    0x18(%rbp),%r14
     5d0:	mov    0x0(%rip),%rcx        # 5d7 <pgot_ZSTD_execSequenceLast7_all_pgot.isra.0+0xd7>
			5d3: R_X86_64_PC32	pgot_memmove_table_all_pgot-0x4
     5d7:	sub    %rsi,%r14
     5da:	mov    0x28(%rbp),%rsi
     5de:	sub    %r14,%rsi
     5e1:	lea    (%rsi,%r10,1),%rax
     5e5:	cmp    %rax,0x28(%rbp)
     5e9:	jae    670 <pgot_ZSTD_execSequenceLast7_all_pgot.isra.0+0x170>
     5ef:	mov    %r14,%rdx
     5f2:	mov    %r12,%rdi
     5f5:	call   *%rcx
     5f7:	mov    0x18(%rbp),%rsi
     5fb:	lea    (%r12,%r14,1),%rax
     5ff:	cmp    %rax,%rbx
     602:	jbe    62d <pgot_ZSTD_execSequenceLast7_all_pgot.isra.0+0x12d>
     604:	sub    %rax,%rbx
     607:	xor    %edx,%edx
     609:	movzbl (%rsi,%rdx,1),%ecx
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decompressBegin_all_pgot, b39, pgot_memcpy_table_all_pgot

```asm
     b35:	push   %rbp
     b36:	mov    0x0(%rip),%rax        # b3d <pgot_ZSTD_decompressBegin_all_pgot+0xd>
			b39: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     b3d:	mov    $0xc,%edx
     b42:	mov    $0x0,%rsi
			b45: R_X86_64_32S	.rodata+0x700
     b49:	mov    %rsp,%rbp
     b4c:	push   %rbx
     b4d:	mov    %rdi,%rbx
     b50:	lea    0x6030(%rdi),%rdi
     b57:	movq   $0x5,0x30(%rdi)
     b5f:	movq   $0x0,0x10(%rdi)
     b67:	movq   $0x0,0x18(%rdi)
     b6f:	movq   $0x0,0x20(%rdi)
     b77:	movq   $0x0,0x28(%rdi)
     b7f:	movl   $0xc00000c,-0x4c04(%rdi)
     b89:	movl   $0x0,0x54(%rdi)
     b90:	movq   $0x0,0x58(%rdi)
     b98:	movl   $0x0,0xb8(%rdi)
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_createDCtx_advanced_all_pgot, d17, pgot_memcpy_table_all_pgot

```asm
     d0f:	mov    $0x18,%edx
     d14:	mov    0x0(%rip),%rax        # d1b <pgot_ZSTD_createDCtx_advanced_all_pgot+0x4b>
			d17: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     d1b:	lea    0x10(%rbp),%rsi
     d1f:	call   *%rax
     d21:	mov    %r12,%rdi
     d24:	call   d29 <pgot_ZSTD_createDCtx_advanced_all_pgot+0x59>
			d25: R_X86_64_PLT32	pgot_ZSTD_decompressBegin_all_pgot-0x4
     d29:	mov    %r12,%rax
     d2c:	mov    -0x8(%rbp),%r12
     d30:	leave  
     d31:	ret    
     d32:	int3   
     d33:	xor    %r12d,%r12d
     d36:	mov    %r12,%rax
     d39:	mov    -0x8(%rbp),%r12
     d3d:	leave  
     d3e:	ret    
     d3f:	int3   
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_copyDCtx_all_pgot, dd9, pgot_memcpy_table_all_pgot

```asm
     dd5:	push   %rbp
     dd6:	mov    0x0(%rip),%rax        # ddd <pgot_ZSTD_copyDCtx_all_pgot+0xd>
			dd9: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     ddd:	mov    $0x6126,%edx
     de2:	mov    %rsp,%rbp
     de5:	call   *%rax
     de7:	pop    %rbp
     de8:	ret    
     de9:	int3   
     dea:	nopw   0x0(%rax,%rax,1)

```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_getFrameParams_all_pgot, e85, pgot_memset_table_all_pgot

```asm
     e80:	jbe    ea5 <pgot_ZSTD_getFrameParams_all_pgot+0x75>
     e82:	mov    0x0(%rip),%rax        # e89 <pgot_ZSTD_getFrameParams_all_pgot+0x59>
			e85: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
     e89:	mov    $0x18,%edx
     e8e:	xor    %esi,%esi
     e90:	call   *%rax
     e92:	mov    0x4(%r12),%eax
     e97:	movl   $0x0,0x8(%r13)
     e9f:	mov    %rax,0x0(%r13)
     ea3:	xor    %eax,%eax
     ea5:	add    $0x18,%rsp
     ea9:	pop    %rbx
     eaa:	pop    %r12
     eac:	pop    %r13
     eae:	pop    %r14
     eb0:	pop    %r15
     eb2:	pop    %rbp
     eb3:	ret    
     eb4:	int3   
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decodeLiteralsBlock_all_pgot, 1279, pgot_memcpy_table_all_pgot

```asm
    1273:	mov    %rbx,%rdx
    1276:	mov    0x0(%rip),%rax        # 127d <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x9d>
			1279: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    127d:	mov    %r14,%rdi
    1280:	call   *%rax
    1282:	mov    %r14,0x60f0(%r12)
    128a:	lea    (%r14,%rbx,1),%rdi
    128e:	xor    %esi,%esi
    1290:	mov    %rbx,0x6110(%r12)
    1298:	mov    $0x8,%edx
    129d:	mov    0x0(%rip),%rax        # 12a4 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xc4>
			12a0: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    12a4:	call   *%rax
    12a6:	jmp    12fb <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x11b>
    12a8:	mov    0x6088(%rdi),%esi
    12ae:	mov    $0xffffffffffffffed,%r13
    12b5:	test   %esi,%esi
    12b7:	je     12fb <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x11b>
    12b9:	cmp    $0x4,%rdx
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decodeLiteralsBlock_all_pgot, 12a0, pgot_memset_table_all_pgot

```asm
    1298:	mov    $0x8,%edx
    129d:	mov    0x0(%rip),%rax        # 12a4 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xc4>
			12a0: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    12a4:	call   *%rax
    12a6:	jmp    12fb <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x11b>
    12a8:	mov    0x6088(%rdi),%esi
    12ae:	mov    $0xffffffffffffffed,%r13
    12b5:	test   %esi,%esi
    12b7:	je     12fb <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x11b>
    12b9:	cmp    $0x4,%rdx
    12bd:	jbe    12f4 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x114>
    12bf:	mov    (%r9),%r8d
    12c2:	shr    $0x2,%al
    12c5:	and    $0x3,%eax
    12c8:	mov    %r8d,%ecx
    12cb:	shr    $0x4,%ecx
    12ce:	cmp    $0x2,%al
    12d0:	je     13ce <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x1ee>
    12d6:	cmp    $0x3,%al
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decodeLiteralsBlock_all_pgot, 13c3, pgot_memset_table_all_pgot

```asm
    13be:	xor    %esi,%esi
    13c0:	mov    0x0(%rip),%rax        # 13c7 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x1e7>
			13c3: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    13c7:	call   *%rax
    13c9:	jmp    12fb <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x11b>
    13ce:	mov    %ecx,%r14d
    13d1:	shr    $0x12,%r8d
    13d5:	xor    %eax,%eax
    13d7:	mov    $0x4,%esi
    13dc:	and    $0x3fff,%r14d
    13e3:	mov    %r8d,%ecx
    13e6:	jmp    1330 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x150>
    13eb:	movzwl (%rsi),%ebx
    13ee:	mov    $0x2,%esi
    13f3:	shr    $0x4,%bx
    13f7:	movzwl %bx,%ebx
    13fa:	jmp    124e <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x6e>
    13ff:	mov    %eax,%ecx
    1401:	shr    $0x2,%cl
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decodeLiteralsBlock_all_pgot, 143a, pgot_memset_table_all_pgot

```asm
    1433:	lea    0x8(%rbx),%rdx
    1437:	mov    0x0(%rip),%rax        # 143e <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x25e>
			143a: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    143e:	mov    %r14,%rdi
    1441:	call   *%rax
    1443:	mov    %r14,0x60f0(%r12)
    144b:	mov    %rbx,0x6110(%r12)
    1453:	jmp    12fb <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x11b>
    1458:	add    %r9,%rsi
    145b:	mov    %rbx,0x6110(%r12)
    1463:	mov    %rsi,0x60f0(%r12)
    146b:	jmp    12fb <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x11b>
    1470:	movzbl 0x2(%rsi),%ebx
    1474:	movzwl (%rsi),%eax
    1477:	mov    $0x3,%esi
    147c:	shl    $0x10,%ebx
    147f:	add    %eax,%ebx
    1481:	shr    $0x4,%ebx
    1484:	jmp    124e <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x6e>
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decodeSeqHeaders_all_pgot, 15f0, pgot_LL_defaultDTable_all_pgot

```asm
    15eb:	sub    %r9,%rax
    15ee:	push   0x0(%rip)        # 15f4 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x94>
			15f0: R_X86_64_PC32	pgot_LL_defaultDTable_all_pgot-0x4
    15f4:	push   %rax
    15f5:	call   400 <ZSTD_buildSeqTable.constprop.0>
    15fa:	mov    -0x30(%rbp),%r9
    15fe:	add    $0x20,%rsp
    1602:	cmp    $0xffffffffffffffea,%rax
    1606:	ja     16f7 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x197>
    160c:	push   %r15
    160e:	add    %rax,%r9
    1611:	mov    0x608c(%r13),%eax
    1618:	mov    %r14d,%edx
    161b:	shr    $0x4,%dl
    161e:	lea    0x10(%r13),%rsi
    1622:	mov    $0x1c,%ecx
    1627:	mov    %r9,-0x30(%rbp)
    162b:	push   %rax
    162c:	mov    %rbx,%rax
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decodeSeqHeaders_all_pgot, 163e, pgot_OF_defaultDTable_all_pgot

```asm
    1639:	sub    %r9,%rax
    163c:	push   0x0(%rip)        # 1642 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0xe2>
			163e: R_X86_64_PC32	pgot_OF_defaultDTable_all_pgot-0x4
    1642:	mov    $0x8,%r8d
    1648:	push   %rax
    1649:	call   400 <ZSTD_buildSeqTable.constprop.0>
    164e:	add    $0x20,%rsp
    1652:	cmp    $0xffffffffffffffea,%rax
    1656:	ja     16f7 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x197>
    165c:	mov    -0x30(%rbp),%r9
    1660:	push   %r15
    1662:	mov    %r14d,%edx
    1665:	lea    0x8(%r13),%rsi
    1669:	shr    $0x2,%dl
    166c:	mov    $0x9,%r8d
    1672:	mov    $0x34,%ecx
    1677:	add    %rax,%r9
    167a:	mov    0x608c(%r13),%eax
    1681:	and    $0x3,%edx
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decodeSeqHeaders_all_pgot, 1695, pgot_ML_defaultDTable_all_pgot

```asm
    1692:	push   %rax
    1693:	push   0x0(%rip)        # 1699 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x139>
			1695: R_X86_64_PC32	pgot_ML_defaultDTable_all_pgot-0x4
    1699:	push   %rbx
    169a:	call   400 <ZSTD_buildSeqTable.constprop.0>
    169f:	add    $0x20,%rsp
    16a3:	cmp    $0xffffffffffffffea,%rax
    16a7:	ja     16f7 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x197>
    16a9:	mov    -0x30(%rbp),%r9
    16ad:	add    %r9,%rax
    16b0:	sub    %r12,%rax
    16b3:	jmp    16fe <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x19e>
    16b5:	cmp    $0xff,%eax
    16ba:	je     1729 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x1c9>
    16bc:	cmp    %r9,%rbx
    16bf:	jbe    16e0 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x180>
    16c1:	lea    0x2(%rdx),%r9
    16c5:	add    $0xffffff80,%eax
    16c8:	movzbl 0x1(%rdx),%edx
```

## 04_zstd_decompress/no_retpoline/all_pgot: ZSTD_decompressSequencesLong, 1871, pgot_memcpy_table_all_pgot

```asm
    186b:	mov    %r13,%rsi
    186e:	mov    0x0(%rip),%rax        # 1875 <ZSTD_decompressSequencesLong+0x125>
			1871: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    1875:	call   *%rax
    1877:	mov    -0x120(%rbp),%r11
    187e:	add    %r11,%rbx
    1881:	sub    -0x118(%rbp),%rbx
    1888:	mov    %rbx,%r12
    188b:	mov    -0x38(%rbp),%rax
    188f:	sub    %gs:0x28,%rax
    1898:	jne    2548 <ZSTD_decompressSequencesLong+0xdf8>
    189e:	lea    -0x30(%rbp),%rsp
    18a2:	mov    %r12,%rax
    18a5:	pop    %rbx
    18a6:	pop    %r10
    18a8:	pop    %r12
    18aa:	pop    %r13
    18ac:	pop    %r14
    18ae:	pop    %r15
```

## 04_zstd_decompress/no_retpoline/all_pgot: ZSTD_decompressSequencesLong, 1d49, pgot_memmove_table_all_pgot

```asm
    1d40:	jb     191f <ZSTD_decompressSequencesLong+0x1cf>
    1d46:	mov    0x0(%rip),%rax        # 1d4d <ZSTD_decompressSequencesLong+0x5fd>
			1d49: R_X86_64_PC32	pgot_memmove_table_all_pgot-0x4
    1d4d:	lea    (%rsi,%rcx,1),%rdx
    1d51:	cmp    %rdx,-0x130(%rbp)
    1d58:	jae    252d <ZSTD_decompressSequencesLong+0xddd>
    1d5e:	mov    -0x130(%rbp),%rdx
    1d65:	mov    %r9,-0x178(%rbp)
    1d6c:	mov    %r14,%rdi
    1d6f:	mov    %rcx,-0x160(%rbp)
    1d76:	sub    %rsi,%rdx
    1d79:	mov    %r8,-0x168(%rbp)
    1d80:	mov    %rdx,-0x128(%rbp)
    1d87:	call   *%rax
    1d89:	mov    -0x128(%rbp),%rdx
    1d90:	mov    -0x160(%rbp),%rcx
    1d97:	mov    -0x178(%rbp),%r9
    1d9e:	sub    %rdx,%rcx
    1da1:	add    %rdx,%r14
```

## 04_zstd_decompress/no_retpoline/all_pgot: ZSTD_decompressSequencesLong, 1e20, pgot_memcpy_table_all_pgot

```asm
    1e1a:	add    %rax,%rsi
    1e1d:	mov    0x0(%rip),%rax        # 1e24 <ZSTD_decompressSequencesLong+0x6d4>
			1e20: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    1e24:	mov    %rsi,-0x160(%rbp)
    1e2b:	call   *%rax
    1e2d:	movslq -0x128(%rbp),%rax
    1e34:	mov    -0x160(%rbp),%rsi
    1e3b:	mov    -0x168(%rbp),%rcx
    1e42:	mov    -0x178(%rbp),%r9
    1e49:	sub    %rax,%rsi
    1e4c:	lea    0x8(%r14),%rax
    1e50:	add    $0x8,%rsi
    1e54:	cmp    -0x150(%rbp),%rbx
    1e5b:	jbe    24b8 <ZSTD_decompressSequencesLong+0xd68>
    1e61:	cmp    -0x138(%rbp),%rax
    1e68:	jb     24d4 <ZSTD_decompressSequencesLong+0xd84>
    1e6e:	cmp    %rax,%rbx
    1e71:	jbe    1e88 <ZSTD_decompressSequencesLong+0x738>
    1e73:	sub    %rax,%rbx
```

## 04_zstd_decompress/no_retpoline/all_pgot: ZSTD_decompressSequencesLong, 2040, pgot_memmove_table_all_pgot

```asm
    2037:	jb     191f <ZSTD_decompressSequencesLong+0x1cf>
    203d:	mov    0x0(%rip),%rax        # 2044 <ZSTD_decompressSequencesLong+0x8f4>
			2040: R_X86_64_PC32	pgot_memmove_table_all_pgot-0x4
    2044:	lea    (%rsi,%rcx,1),%rdx
    2048:	cmp    %rdx,-0x130(%rbp)
    204f:	jae    241d <ZSTD_decompressSequencesLong+0xccd>
    2055:	mov    -0x130(%rbp),%rdx
    205c:	mov    %r10d,-0x180(%rbp)
    2063:	mov    %r14,%rdi
    2066:	mov    %rcx,-0x178(%rbp)
    206d:	sub    %rsi,%rdx
    2070:	mov    %r9,-0x160(%rbp)
    2077:	mov    %rdx,-0x158(%rbp)
    207e:	mov    %r8,-0x188(%rbp)
    2085:	call   *%rax
    2087:	mov    -0x158(%rbp),%rdx
    208e:	mov    -0x178(%rbp),%rcx
    2095:	mov    -0x160(%rbp),%r9
    209c:	mov    -0x180(%rbp),%r10d
```

## 04_zstd_decompress/no_retpoline/all_pgot: ZSTD_decompressSequencesLong, 22d5, pgot_memcpy_table_all_pgot

```asm
    22cf:	add    %rax,%rsi
    22d2:	mov    0x0(%rip),%rax        # 22d9 <ZSTD_decompressSequencesLong+0xb89>
			22d5: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    22d9:	mov    %rsi,-0x160(%rbp)
    22e0:	call   *%rax
    22e2:	movslq -0x158(%rbp),%rax
    22e9:	mov    -0x160(%rbp),%rsi
    22f0:	mov    -0x178(%rbp),%r9
    22f7:	mov    -0x180(%rbp),%rcx
    22fe:	mov    -0x188(%rbp),%r10d
    2305:	sub    %rax,%rsi
    2308:	jmp    215e <ZSTD_decompressSequencesLong+0xa0e>
    230d:	push   -0x130(%rbp)
    2313:	mov    %rdi,%rsi
    2316:	lea    -0xe0(%rbp),%r9
    231d:	mov    %rax,%rdx
    2320:	push   -0x148(%rbp)
    2326:	mov    %r15,%rdi
    2329:	push   -0x128(%rbp)
```

## 04_zstd_decompress/no_retpoline/all_pgot: ZSTD_decompressSequences, 26b2, pgot_memcpy_table_all_pgot

```asm
    26ad:	jb     26d1 <ZSTD_decompressSequences+0x131>
    26af:	mov    0x0(%rip),%rax        # 26b6 <ZSTD_decompressSequences+0x116>
			26b2: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    26b6:	mov    %rbx,%rdx
    26b9:	mov    %r9,%rsi
    26bc:	mov    %r15,%rdi
    26bf:	call   *%rax
    26c1:	mov    %r15,%rax
    26c4:	add    %rbx,%rax
    26c7:	sub    -0xc8(%rbp),%rax
    26ce:	mov    %rax,%r14
    26d1:	mov    -0x30(%rbp),%rax
    26d5:	sub    %gs:0x28,%rax
    26de:	jne    314b <ZSTD_decompressSequences+0xbab>
    26e4:	lea    -0x28(%rbp),%rsp
    26e8:	mov    %r14,%rax
    26eb:	pop    %rbx
    26ec:	pop    %r12
    26ee:	pop    %r13
```

## 04_zstd_decompress/no_retpoline/all_pgot: ZSTD_decompressSequences, 2c36, pgot_memmove_table_all_pgot

```asm
    2c2c:	sub    -0xe8(%rbp),%rbx
    2c33:	mov    0x0(%rip),%rax        # 2c3a <ZSTD_decompressSequences+0x69a>
			2c36: R_X86_64_PC32	pgot_memmove_table_all_pgot-0x4
    2c3a:	lea    (%rdi,%rbx,1),%rsi
    2c3e:	lea    (%rsi,%r12,1),%rdx
    2c42:	cmp    %rdx,%rdi
    2c45:	jae    2fc3 <ZSTD_decompressSequences+0xa23>
    2c4b:	mov    %rbx,%rdx
    2c4e:	mov    %rcx,-0x110(%rbp)
    2c55:	mov    %r15,%rdi
    2c58:	add    %rbx,%r12
    2c5b:	neg    %rdx
    2c5e:	mov    %r8,-0x118(%rbp)
    2c65:	mov    %rdx,-0x108(%rbp)
    2c6c:	call   *%rax
    2c6e:	mov    -0x108(%rbp),%rdx
    2c75:	mov    -0x110(%rbp),%rcx
    2c7c:	add    %rdx,%r15
    2c7f:	cmp    $0x2,%r12
```

## 04_zstd_decompress/no_retpoline/all_pgot: ZSTD_decompressSequences, 2f56, pgot_memcpy_table_all_pgot

```asm
    2f50:	add    %rax,%rsi
    2f53:	mov    0x0(%rip),%rax        # 2f5a <ZSTD_decompressSequences+0x9ba>
			2f56: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2f5a:	mov    %rsi,-0x100(%rbp)
    2f61:	call   *%rax
    2f63:	mov    -0x100(%rbp),%rsi
    2f6a:	mov    -0x108(%rbp),%r8
    2f71:	mov    -0x110(%rbp),%rcx
    2f78:	sub    %rbx,%rsi
    2f7b:	jmp    2df2 <ZSTD_decompressSequences+0x852>
    2f80:	mov    %rcx,%rdi
    2f83:	mov    %rcx,%rax
    2f86:	sub    %r10,%rdi
    2f89:	mov    %edi,%edx
    2f8b:	mov    %edi,%edi
    2f8d:	sub    %rdi,%rax
    2f90:	jmp    28ff <ZSTD_decompressSequences+0x35f>
    2f95:	mov    %rcx,%r8
    2f98:	sub    %rdi,%r8
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_generateNxBytes_all_pgot, 3521, pgot_memset_table_all_pgot

```asm
    351b:	movzbl %dl,%esi
    351e:	mov    0x0(%rip),%rax        # 3525 <pgot_ZSTD_generateNxBytes_all_pgot+0x15>
			3521: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    3525:	mov    %rcx,%rdx
    3528:	mov    %rsp,%rbp
    352b:	push   %rbx
    352c:	mov    %rcx,%rbx
    352f:	call   *%rax
    3531:	mov    %rbx,%rax
    3534:	mov    -0x8(%rbp),%rbx
    3538:	leave  
    3539:	ret    
    353a:	int3   
    353b:	mov    $0xfffffffffffffff4,%rax
    3542:	ret    
    3543:	int3   
    3544:	data16 cs nopw 0x0(%rax,%rax,1)
    354f:	nop

```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3a67, pgot_memcpy_table_all_pgot

```asm
    3a61:	mov    %rcx,%rsi
    3a64:	mov    0x0(%rip),%rax        # 3a6b <pgot_ZSTD_decompressContinue_all_pgot+0x1fb>
			3a67: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3a6b:	mov    $0x5,%edx
    3a70:	mov    %r12,%rdi
    3a73:	call   *%rax
    3a75:	mov    0x60e0(%rbx),%rax
    3a7c:	mov    -0x30(%rbp),%rcx
    3a80:	cmp    $0x5,%rax
    3a84:	ja     3ce3 <pgot_ZSTD_decompressContinue_all_pgot+0x473>
    3a8a:	movq   $0x0,0x6060(%rbx)
    3a95:	xor    %r8d,%r8d
    3a98:	jmp    3aee <pgot_ZSTD_decompressContinue_all_pgot+0x27e>
    3a9a:	mov    $0xfffffffffffffff3,%r12
    3aa1:	jmp    396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3aa6:	mov    $0xffffffffffffffff,%r12
    3aad:	jmp    396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3ab2:	mov    0x0(%rip),%rax        # 3ab9 <pgot_ZSTD_decompressContinue_all_pgot+0x249>
			3ab5: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3ab5, pgot_memcpy_table_all_pgot

```asm
    3aad:	jmp    396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3ab2:	mov    0x0(%rip),%rax        # 3ab9 <pgot_ZSTD_decompressContinue_all_pgot+0x249>
			3ab5: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3ab9:	mov    %r8,%rdx
    3abc:	mov    %rcx,%rsi
    3abf:	xor    %r12d,%r12d
    3ac2:	lea    0x2612d(%rbx),%rdi
    3ac9:	call   *%rax
    3acb:	mov    0x2612c(%rbx),%eax
    3ad1:	movl   $0x7,0x6084(%rbx)
    3adb:	mov    %rax,0x6060(%rbx)
    3ae2:	jmp    396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3ae7:	lea    0x26128(%rbx),%r12
    3aee:	mov    %r8,%rdx
    3af1:	mov    %rcx,%rsi
    3af4:	lea    0x2612d(%rbx),%rdi
    3afb:	mov    0x0(%rip),%rax        # 3b02 <pgot_ZSTD_decompressContinue_all_pgot+0x292>
			3afe: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3b02:	call   *%rax
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3afe, pgot_memcpy_table_all_pgot

```asm
    3af4:	lea    0x2612d(%rbx),%rdi
    3afb:	mov    0x0(%rip),%rax        # 3b02 <pgot_ZSTD_decompressContinue_all_pgot+0x292>
			3afe: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3b02:	call   *%rax
    3b04:	mov    0x60e0(%rbx),%rdx
    3b0b:	mov    %r12,%rsi
    3b0e:	mov    %rbx,%rdi
    3b11:	call   1090 <ZSTD_decodeFrameHeader>
    3b16:	mov    %rax,%r12
    3b19:	cmp    $0xffffffffffffffea,%rax
    3b1d:	ja     396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3b23:	movq   $0x3,0x6060(%rbx)
    3b2e:	xor    %r12d,%r12d
    3b31:	movl   $0x2,0x6084(%rbx)
    3b3b:	jmp    396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3b40:	mov    0x6080(%rbx),%eax
    3b46:	cmp    $0x1,%eax
    3b49:	je     3be3 <pgot_ZSTD_decompressContinue_all_pgot+0x373>
    3b4f:	cmp    $0x2,%eax
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3b6f, pgot_memcpy_table_all_pgot

```asm
    3b67:	jmp    396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3b6c:	mov    0x0(%rip),%rax        # 3b73 <pgot_ZSTD_decompressContinue_all_pgot+0x303>
			3b6f: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3b73:	lea    0x26128(%rbx),%rdi
    3b7a:	mov    %rcx,%rsi
    3b7d:	xor    %r12d,%r12d
    3b80:	mov    $0x5,%edx
    3b85:	call   *%rax
    3b87:	movq   $0x3,0x6060(%rbx)
    3b92:	movl   $0x6,0x6084(%rbx)
    3b9c:	jmp    396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3ba1:	movq   $0x3,0x6060(%rbx)
    3bac:	xor    %r12d,%r12d
    3baf:	jmp    396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3bb4:	movq   $0x1,0x6060(%rbx)
    3bbf:	mov    %edx,%eax
    3bc1:	movl   $0x1,0x6080(%rbx)
    3bcb:	mov    %rax,0x6118(%rbx)
    3bd2:	add    $0x3,%ecx
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3c03, pgot_memset_table_all_pgot

```asm
    3bfd:	movzbl (%rcx),%esi
    3c00:	mov    0x0(%rip),%rax        # 3c07 <pgot_ZSTD_decompressContinue_all_pgot+0x397>
			3c03: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    3c07:	mov    %r12,%rdx
    3c0a:	mov    %r13,%rdi
    3c0d:	call   *%rax
    3c0f:	cmp    $0xffffffffffffffea,%r12
    3c13:	ja     396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3c19:	mov    0x6078(%rbx),%edx
    3c1f:	test   %edx,%edx
    3c21:	jne    3ca0 <pgot_ZSTD_decompressContinue_all_pgot+0x430>
    3c23:	cmpl   $0x4,0x6084(%rbx)
    3c2a:	je     3d00 <pgot_ZSTD_decompressContinue_all_pgot+0x490>
    3c30:	movl   $0x2,0x6084(%rbx)
    3c3a:	add    %r12,%r13
    3c3d:	movq   $0x3,0x6060(%rbx)
    3c48:	mov    %r13,0x6040(%rbx)
    3c4f:	jmp    396f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3c54:	mov    $0xfffffffffffffff4,%r12
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3c74, pgot_memcpy_table_all_pgot

```asm
    3c6e:	mov    %r13,%rdi
    3c71:	mov    0x0(%rip),%rax        # 3c78 <pgot_ZSTD_decompressContinue_all_pgot+0x408>
			3c74: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3c78:	call   *%rax
    3c7a:	mov    -0x30(%rbp),%r12
    3c7e:	jmp    3c0f <pgot_ZSTD_decompressContinue_all_pgot+0x39f>
    3c80:	cmp    $0x1ffff,%r8
    3c87:	ja     3a9a <pgot_ZSTD_decompressContinue_all_pgot+0x22a>
    3c8d:	mov    %r13,%rsi
    3c90:	mov    %rbx,%rdi
    3c93:	call   33d0 <ZSTD_decompressBlock_internal.part.0>
    3c98:	mov    %rax,%r12
    3c9b:	jmp    3c0f <pgot_ZSTD_decompressContinue_all_pgot+0x39f>
    3ca0:	lea    0x6090(%rbx),%rdi
    3ca7:	mov    %r12,%rdx
    3caa:	mov    %r13,%rsi
    3cad:	call   3cb2 <pgot_ZSTD_decompressContinue_all_pgot+0x442>
			3cae: R_X86_64_PLT32	xxh64_update-0x4
    3cb2:	cmpl   $0x4,0x6084(%rbx)
```

## 04_zstd_decompress/no_retpoline/all_pgot: ZSTD_decompressMultiFrame, 3f3a, pgot_memcpy_table_all_pgot

```asm
    3f34:	mov    %rbx,%rdi
    3f37:	mov    0x0(%rip),%rax        # 3f3e <ZSTD_decompressMultiFrame+0xee>
			3f3a: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3f3e:	call   *%rax
    3f40:	mov    -0x58(%rbp),%r8
    3f44:	mov    %r8,%r15
    3f47:	mov    0x6078(%r13),%ecx
    3f4e:	test   %ecx,%ecx
    3f50:	jne    414d <ZSTD_decompressMultiFrame+0x2fd>
    3f56:	mov    -0x48(%rbp),%edx
    3f59:	sub    %r8,%r14
    3f5c:	add    %r15,%rbx
    3f5f:	lea    (%r12,%r8,1),%r11
    3f63:	mov    %r14,%r9
    3f66:	test   %edx,%edx
    3f68:	jne    41c3 <ZSTD_decompressMultiFrame+0x373>
    3f6e:	cmp    $0x2,%r14
    3f72:	ja     4086 <ZSTD_decompressMultiFrame+0x236>
    3f78:	mov    $0xfffffffffffffff3,%r15
```

## 04_zstd_decompress/no_retpoline/all_pgot: ZSTD_decompressMultiFrame, 4194, pgot_memset_table_all_pgot

```asm
    418f:	jb     41ab <ZSTD_decompressMultiFrame+0x35b>
    4191:	mov    0x0(%rip),%rax        # 4198 <ZSTD_decompressMultiFrame+0x348>
			4194: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    4198:	mov    %r15,%rdx
    419b:	mov    %rbx,%rdi
    419e:	call   *%rax
    41a0:	mov    $0x1,%r8d
    41a6:	jmp    3f47 <ZSTD_decompressMultiFrame+0xf7>
    41ab:	mov    $0xfffffffffffffff4,%r15
    41b2:	jmp    3f07 <ZSTD_decompressMultiFrame+0xb7>
    41b7:	mov    $0xfffffffffffffffe,%r15
    41be:	jmp    3f07 <ZSTD_decompressMultiFrame+0xb7>
    41c3:	mov    0x6078(%r13),%eax
    41ca:	mov    %rbx,%r15
    41cd:	mov    -0x60(%rbp),%r14
    41d1:	mov    %r9,%rbx
    41d4:	test   %eax,%eax
    41d6:	jne    41f4 <ZSTD_decompressMultiFrame+0x3a4>
    41d8:	mov    %r15,%r12
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_initDStream_all_pgot, 46c3, pgot_memset_table_all_pgot

```asm
    46be:	xor    %esi,%esi
    46c0:	mov    0x0(%rip),%rax        # 46c7 <pgot_ZSTD_initDStream_all_pgot+0x87>
			46c3: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    46c7:	call   *%rax
    46c9:	lea    0xa0(%r12),%rdi
    46d1:	mov    $0x18,%edx
    46d6:	lea    -0x38(%rbp),%rsi
    46da:	mov    0x0(%rip),%rax        # 46e1 <pgot_ZSTD_initDStream_all_pgot+0xa1>
			46dd: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    46e1:	call   *%rax
    46e3:	push   -0x28(%rbp)
    46e6:	push   -0x30(%rbp)
    46e9:	push   -0x38(%rbp)
    46ec:	call   46f1 <pgot_ZSTD_initDStream_all_pgot+0xb1>
			46ed: R_X86_64_PLT32	pgot_ZSTD_createDCtx_advanced_all_pgot-0x4
    46f1:	mov    %rax,(%r12)
    46f5:	add    $0x18,%rsp
    46f9:	test   %rax,%rax
    46fc:	je     47fe <pgot_ZSTD_initDStream_all_pgot+0x1be>
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_initDStream_all_pgot, 46dd, pgot_memcpy_table_all_pgot

```asm
    46d6:	lea    -0x38(%rbp),%rsi
    46da:	mov    0x0(%rip),%rax        # 46e1 <pgot_ZSTD_initDStream_all_pgot+0xa1>
			46dd: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    46e1:	call   *%rax
    46e3:	push   -0x28(%rbp)
    46e6:	push   -0x30(%rbp)
    46e9:	push   -0x38(%rbp)
    46ec:	call   46f1 <pgot_ZSTD_initDStream_all_pgot+0xb1>
			46ed: R_X86_64_PLT32	pgot_ZSTD_createDCtx_advanced_all_pgot-0x4
    46f1:	mov    %rax,(%r12)
    46f5:	add    $0x18,%rsp
    46f9:	test   %rax,%rax
    46fc:	je     47fe <pgot_ZSTD_initDStream_all_pgot+0x1be>
    4702:	mov    0x8(%r12),%rdi
    4707:	mov    %rbx,0x50(%r12)
    470c:	movl   $0x1,0x30(%r12)
    4715:	movq   $0x0,0x70(%r12)
    471e:	movq   $0x0,0x68(%r12)
    4727:	movq   $0x0,0x48(%r12)
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decompressStream_all_pgot, 498e, pgot_memcpy_table_all_pgot

```asm
    4984:	sub    0x98(%rbx),%rcx
    498b:	mov    0x0(%rip),%rax        # 4992 <pgot_ZSTD_decompressStream_all_pgot+0xc2>
			498e: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4992:	sub    %r12,%rdx
    4995:	add    %r14,%rdi
    4998:	cmp    %rcx,%rdx
    499b:	jb     4e52 <pgot_ZSTD_decompressStream_all_pgot+0x582>
    49a1:	mov    %rcx,-0x40(%rbp)
    49a5:	mov    %rcx,%rdx
    49a8:	mov    %r12,%rsi
    49ab:	call   *%rax
    49ad:	mov    -0x40(%rbp),%rcx
    49b1:	mov    0x30(%rbx),%eax
    49b4:	mov    %r15,0x98(%rbx)
    49bb:	add    %rcx,%r12
    49be:	cmp    $0x2,%eax
    49c1:	jne    493f <pgot_ZSTD_decompressStream_all_pgot+0x6f>
    49c7:	mov    (%rbx),%rdi
    49ca:	mov    0x6060(%rdi),%r8
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decompressStream_all_pgot, 4a64, pgot_memcpy_table_all_pgot

```asm
    4a5e:	mov    %r13,%rdi
    4a61:	mov    0x0(%rip),%rax        # 4a68 <pgot_ZSTD_decompressStream_all_pgot+0x198>
			4a64: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4a68:	sub    %r13,%rcx
    4a6b:	cmp    %rcx,%r15
    4a6e:	mov    %rcx,%rdx
    4a71:	mov    %rcx,-0x48(%rbp)
    4a75:	cmovbe %r15,%rdx
    4a79:	add    0x58(%rbx),%rsi
    4a7d:	mov    %rdx,-0x40(%rbp)
    4a81:	call   *%rax
    4a83:	mov    -0x40(%rbp),%rdx
    4a87:	mov    -0x48(%rbp),%rcx
    4a8b:	add    %rdx,%r13
    4a8e:	add    0x68(%rbx),%rdx
    4a92:	mov    %rdx,0x68(%rbx)
    4a96:	cmp    %rcx,%r15
    4a99:	ja     49e1 <pgot_ZSTD_decompressStream_all_pgot+0x111>
    4a9f:	movl   $0x2,0x30(%rbx)
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_ZSTD_decompressStream_all_pgot, 4b3b, pgot_memcpy_table_all_pgot

```asm
    4b35:	mov    %r12,%rsi
    4b38:	mov    0x0(%rip),%rax        # 4b3f <pgot_ZSTD_decompressStream_all_pgot+0x26f>
			4b3b: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4b3f:	sub    %r12,%r15
    4b42:	cmp    %rcx,%r15
    4b45:	cmova  %rcx,%r15
    4b49:	add    0x38(%rbx),%rdi
    4b4d:	mov    %r15,%rdx
    4b50:	add    %r15,%r12
    4b53:	call   *%rax
    4b55:	mov    -0x48(%rbp),%rcx
    4b59:	add    %r15,0x48(%rbx)
    4b5d:	mov    -0x40(%rbp),%r8
    4b61:	cmp    %r15,%rcx
    4b64:	ja     49e1 <pgot_ZSTD_decompressStream_all_pgot+0x111>
    4b6a:	mov    (%rbx),%rdi
    4b6d:	mov    0x68(%rbx),%rsi
    4b71:	mov    0x60(%rbx),%rdx
    4b75:	mov    0x38(%rbx),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_FSE_readNCount_all_pgot, 279, memset

```asm
 274:	lea    (%rax,%r8,2),%rdi
 278:	call   27d <pgot_FSE_readNCount_all_pgot+0x21d>
			279: R_X86_64_PLT32	memset-0x4
 27d:	mov    -0x4c(%rbp),%r8d
 281:	mov    -0x58(%rbp),%ecx
 284:	mov    %r13d,%eax
 287:	sar    $0x3,%eax
 28a:	cltq   
 28c:	add    %r12,%rax
 28f:	cmp    -0x40(%rbp),%r12
 293:	jbe    2a2 <pgot_FSE_readNCount_all_pgot+0x242>
 295:	shr    $0x2,%ecx
 298:	cmp    -0x48(%rbp),%rax
 29c:	ja     195 <pgot_FSE_readNCount_all_pgot+0x135>
 2a2:	mov    (%rax),%esi
 2a4:	and    $0x7,%r13d
 2a8:	mov    %rax,%r12
 2ab:	mov    %r13d,%ecx
 2ae:	shr    %cl,%esi
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_readStats_wksp_all_pgot, 3bd, pgot_memset_table_all_pgot

```asm
 3b6:	mov    %r8,-0x38(%rbp)
 3ba:	mov    0x0(%rip),%rax        # 3c1 <pgot_HUF_readStats_wksp_all_pgot+0xa1>
			3bd: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
 3c1:	xor    %esi,%esi
 3c3:	mov    %r15,%rdi
 3c6:	mov    $0x34,%edx
 3cb:	call   *%rax
 3cd:	mov    -0x38(%rbp),%r8
 3d1:	xor    %r12d,%r12d
 3d4:	xor    %r9d,%r9d
 3d7:	xor    %eax,%eax
 3d9:	mov    $0x1,%r11d
 3df:	jmp    409 <pgot_HUF_readStats_wksp_all_pgot+0xe9>
 3e1:	addl   $0x1,(%r15,%rdx,4)
 3e6:	movzbl (%rax),%ecx
 3e9:	cmp    $0x1f,%cl
 3ec:	ja     3f2 <pgot_HUF_readStats_wksp_all_pgot+0xd2>
			3ee: R_X86_64_PC32	.text.unlikely+0x37
 3f2:	mov    %r11d,%eax
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_readStats_wksp_all_pgot, 462, pgot_memset_table_all_pgot

```asm
 45b:	mov    %r8,-0x38(%rbp)
 45f:	mov    0x0(%rip),%rax        # 466 <pgot_HUF_readStats_wksp_all_pgot+0x146>
			462: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
 466:	xor    %esi,%esi
 468:	mov    %r15,%rdi
 46b:	mov    $0x34,%edx
 470:	call   *%rax
 472:	mov    -0x38(%rbp),%r8
 476:	test   %r8,%r8
 479:	jne    3d1 <pgot_HUF_readStats_wksp_all_pgot+0xb1>
 47f:	jmp    414 <pgot_HUF_readStats_wksp_all_pgot+0xf4>
 481:	test   %r9d,%r9d
 484:	je     414 <pgot_HUF_readStats_wksp_all_pgot+0xf4>
 486:	bsr    %r9d,%edx
 48a:	mov    $0x20,%eax
 48f:	xor    $0x1f,%edx
 492:	mov    %eax,%ecx
 494:	sub    %edx,%ecx
 496:	cmp    $0xc,%ecx
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_FSE_buildDTable_wksp_all_pgot, 267, pgot_memcpy_table_all_pgot

```asm
 260:	mov    %r9,-0x50(%rbp)
 264:	mov    0x0(%rip),%rax        # 26b <pgot_FSE_buildDTable_wksp_all_pgot+0x12b>
			267: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
 26b:	call   *%rax
 26d:	mov    -0x48(%rbp),%eax
 270:	mov    -0x50(%rbp),%r9
 274:	xor    %r10d,%r10d
 277:	mov    -0x58(%rbp),%rcx
 27b:	mov    %eax,%edx
 27d:	shr    %eax
 27f:	shr    $0x3,%edx
 282:	lea    0x3(%rdx,%rax,1),%edx
 286:	xor    %eax,%eax
 288:	xor    %esi,%esi
 28a:	cmpw   $0x0,0x0(%r13,%r10,2)
 291:	mov    %r10d,%edi
 294:	jle    2b5 <pgot_FSE_buildDTable_wksp_all_pgot+0x175>
 296:	mov    %eax,%r8d
 299:	mov    %dil,0x2(%r9,%r8,4)
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_fillDTableX4Level2, 4b, pgot_memcpy_table_all_pgot

```asm
      46:	xor    %eax,%eax
      48:	mov    0x0(%rip),%rax        # 4f <HUF_fillDTableX4Level2+0x4f>
			4b: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
      4f:	call   *%rax
      51:	cmp    $0x1,%r12d
      55:	mov    -0x70(%rbp),%r9d
      59:	jle    93 <HUF_fillDTableX4Level2+0x93>
      5b:	movslq %r12d,%r8
      5e:	cmp    $0xc,%r8
      62:	ja     1f4 <HUF_fillDTableX4Level2+0x1f4>
      68:	mov    -0x64(%rbp,%r8,4),%ecx
      6d:	mov    %r15d,%edx
      70:	test   %ecx,%ecx
      72:	je     93 <HUF_fillDTableX4Level2+0x93>
      74:	sub    $0x1,%ecx
      77:	mov    %r13,%rax
      7a:	lea    0x4(%r13,%rcx,4),%rcx
      7f:	mov    %r9w,(%rax)
      83:	add    $0x4,%rax
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decodeLastSymbolX4.isra.0, 38a, pgot_memcpy_table_all_pgot

```asm
     383:	lea    (%rdx,%rax,4),%r12
     387:	mov    0x0(%rip),%rax        # 38e <HUF_decodeLastSymbolX4.isra.0+0x2e>
			38a: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     38e:	mov    $0x1,%edx
     393:	mov    %r12,%rsi
     396:	call   *%rax
     398:	cmpb   $0x1,0x3(%r12)
     39e:	je     3c3 <HUF_decodeLastSymbolX4.isra.0+0x63>
     3a0:	mov    0x8(%rbx),%edx
     3a3:	cmp    $0x3f,%edx
     3a6:	ja     3bd <HUF_decodeLastSymbolX4.isra.0+0x5d>
     3a8:	movzbl 0x2(%r12),%eax
     3ae:	add    %edx,%eax
     3b0:	mov    $0x40,%edx
     3b5:	cmp    %edx,%eax
     3b7:	cmova  %edx,%eax
     3ba:	mov    %eax,0x8(%rbx)
     3bd:	pop    %rbx
     3be:	pop    %r12
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress1X2_usingDTable_internal, 423, pgot_memcpy_table_all_pgot

```asm
     41e:	xor    %eax,%eax
     420:	mov    0x0(%rip),%rax        # 427 <HUF_decompress1X2_usingDTable_internal+0x47>
			423: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     427:	call   *%rax
     429:	movzbl -0x4e(%rbp),%eax
     42d:	mov    %r14,%rsi
     430:	lea    -0x50(%rbp),%rdi
     434:	mov    %r13,%rdx
     437:	mov    %al,-0x51(%rbp)
     43a:	call   220 <BIT_initDStream>
     43f:	mov    %rax,%rdi
     442:	mov    %rax,%r14
     445:	call   44a <HUF_decompress1X2_usingDTable_internal+0x6a>
			446: R_X86_64_PLT32	pgot_HUF_isError_all_pgot-0x4
     44a:	test   %eax,%eax
     44c:	jne    573 <HUF_decompress1X2_usingDTable_internal+0x193>
     452:	mov    -0x48(%rbp),%eax
     455:	movzbl -0x51(%rbp),%esi
     459:	lea    (%rbx,%r12,1),%rdi
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 78a, pgot_memcpy_table_all_pgot

```asm
     783:	mov    %rbx,-0x60(%rbp)
     787:	mov    0x0(%rip),%rax        # 78e <HUF_decompress1X4_usingDTable_internal+0x6e>
			78a: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     78e:	lea    0x4(%r14),%r12
     792:	call   *%rax
     794:	movzbl -0x52(%rbp),%eax
     798:	mov    -0x48(%rbp),%ecx
     79b:	mov    %eax,-0x64(%rbp)
     79e:	cmp    $0x40,%ecx
     7a1:	ja     a15 <HUF_decompress1X4_usingDTable_internal+0x2f5>
     7a7:	neg    %eax
     7a9:	lea    -0x7(%rbx),%r15
     7ad:	mov    %eax,%ebx
     7af:	and    $0x3f,%ebx
     7b2:	jmp    8db <HUF_decompress1X4_usingDTable_internal+0x1bb>
     7b7:	cmp    %rsi,%rax
     7ba:	je     911 <HUF_decompress1X4_usingDTable_internal+0x1f1>
     7c0:	mov    %ecx,%edx
     7c2:	mov    %rax,%r8
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 811, pgot_memcpy_table_all_pgot

```asm
     80a:	lea    (%r12,%rax,4),%r14
     80e:	mov    0x0(%rip),%rax        # 815 <HUF_decompress1X4_usingDTable_internal+0xf5>
			811: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     815:	mov    %r14,%rsi
     818:	call   *%rax
     81a:	mov    -0x50(%rbp),%rax
     81e:	movzbl 0x2(%r14),%ecx
     823:	mov    $0x2,%edx
     828:	add    -0x48(%rbp),%ecx
     82b:	movzbl 0x3(%r14),%edi
     830:	mov    %ecx,-0x48(%rbp)
     833:	shl    %cl,%rax
     836:	mov    %ebx,%ecx
     838:	shr    %cl,%rax
     83b:	add    %rdi,%r13
     83e:	lea    (%r12,%rax,4),%r14
     842:	mov    %r13,%rdi
     845:	mov    0x0(%rip),%rax        # 84c <HUF_decompress1X4_usingDTable_internal+0x12c>
			848: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 848, pgot_memcpy_table_all_pgot

```asm
     842:	mov    %r13,%rdi
     845:	mov    0x0(%rip),%rax        # 84c <HUF_decompress1X4_usingDTable_internal+0x12c>
			848: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     84c:	mov    %r14,%rsi
     84f:	call   *%rax
     851:	movzbl 0x3(%r14),%eax
     856:	movzbl 0x2(%r14),%ecx
     85b:	mov    $0x2,%edx
     860:	add    -0x48(%rbp),%ecx
     863:	add    %rax,%r13
     866:	mov    -0x50(%rbp),%rax
     86a:	mov    %ecx,-0x48(%rbp)
     86d:	mov    %r13,%rdi
     870:	shl    %cl,%rax
     873:	mov    %ebx,%ecx
     875:	shr    %cl,%rax
     878:	lea    (%r12,%rax,4),%r14
     87c:	mov    0x0(%rip),%rax        # 883 <HUF_decompress1X4_usingDTable_internal+0x163>
			87f: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 87f, pgot_memcpy_table_all_pgot

```asm
     878:	lea    (%r12,%rax,4),%r14
     87c:	mov    0x0(%rip),%rax        # 883 <HUF_decompress1X4_usingDTable_internal+0x163>
			87f: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     883:	mov    %r14,%rsi
     886:	call   *%rax
     888:	mov    -0x50(%rbp),%rax
     88c:	movzbl 0x2(%r14),%ecx
     891:	mov    $0x2,%edx
     896:	add    -0x48(%rbp),%ecx
     899:	movzbl 0x3(%r14),%r9d
     89e:	mov    %ecx,-0x48(%rbp)
     8a1:	shl    %cl,%rax
     8a4:	mov    %ebx,%ecx
     8a6:	shr    %cl,%rax
     8a9:	add    %r9,%r13
     8ac:	lea    (%r12,%rax,4),%r14
     8b0:	mov    %r13,%rdi
     8b3:	mov    0x0(%rip),%rax        # 8ba <HUF_decompress1X4_usingDTable_internal+0x19a>
			8b6: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 8b6, pgot_memcpy_table_all_pgot

```asm
     8b0:	mov    %r13,%rdi
     8b3:	mov    0x0(%rip),%rax        # 8ba <HUF_decompress1X4_usingDTable_internal+0x19a>
			8b6: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     8ba:	mov    %r14,%rsi
     8bd:	call   *%rax
     8bf:	movzbl 0x3(%r14),%eax
     8c4:	movzbl 0x2(%r14),%ecx
     8c9:	add    -0x48(%rbp),%ecx
     8cc:	mov    %ecx,-0x48(%rbp)
     8cf:	add    %rax,%r13
     8d2:	cmp    $0x40,%ecx
     8d5:	ja     a15 <HUF_decompress1X4_usingDTable_internal+0x2f5>
     8db:	mov    -0x38(%rbp),%rsi
     8df:	mov    -0x40(%rbp),%rax
     8e3:	lea    0x8(%rsi),%rdi
     8e7:	cmp    %rdi,%rax
     8ea:	jb     7b7 <HUF_decompress1X4_usingDTable_internal+0x97>
     8f0:	mov    %ecx,%edx
     8f2:	and    $0x7,%ecx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 991, pgot_memcpy_table_all_pgot

```asm
     98a:	lea    (%r12,%rax,4),%r14
     98e:	mov    0x0(%rip),%rax        # 995 <HUF_decompress1X4_usingDTable_internal+0x275>
			991: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     995:	mov    %r14,%rsi
     998:	call   *%rax
     99a:	movzbl 0x3(%r14),%edx
     99f:	movzbl 0x2(%r14),%eax
     9a4:	add    -0x48(%rbp),%eax
     9a7:	mov    %eax,-0x48(%rbp)
     9aa:	add    %rdx,%r13
     9ad:	cmp    $0x40,%eax
     9b0:	ja     a1d <HUF_decompress1X4_usingDTable_internal+0x2fd>
     9b2:	mov    -0x38(%rbp),%rsi
     9b6:	lea    0x8(%rsi),%rdi
     9ba:	mov    -0x40(%rbp),%rdx
     9be:	cmp    %rdi,%rdx
     9c1:	jb     935 <HUF_decompress1X4_usingDTable_internal+0x215>
     9c7:	mov    %eax,%ecx
     9c9:	and    $0x7,%eax
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, a4c, pgot_memcpy_table_all_pgot

```asm
     a45:	lea    (%r12,%rax,4),%r14
     a49:	mov    0x0(%rip),%rax        # a50 <HUF_decompress1X4_usingDTable_internal+0x330>
			a4c: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     a50:	mov    %r14,%rsi
     a53:	call   *%rax
     a55:	movzbl 0x3(%r14),%eax
     a5a:	movzbl 0x2(%r14),%ecx
     a5f:	add    -0x48(%rbp),%ecx
     a62:	add    %rax,%r13
     a65:	mov    %ecx,-0x48(%rbp)
     a68:	cmp    %rbx,%r13
     a6b:	jbe    a30 <HUF_decompress1X4_usingDTable_internal+0x310>
     a6d:	cmp    %r13,-0x60(%rbp)
     a71:	ja     aa6 <HUF_decompress1X4_usingDTable_internal+0x386>
     a73:	mov    -0x38(%rbp),%rax
     a77:	mov    $0xfffffffffffffff2,%r12
     a7e:	cmp    %rax,-0x40(%rbp)
     a82:	je     aba <HUF_decompress1X4_usingDTable_internal+0x39a>
     a84:	mov    -0x30(%rbp),%rax
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X2_usingDTable_internal, b54, pgot_memcpy_table_all_pgot

```asm
     b4e:	sub    %rax,%r12
     b51:	mov    0x0(%rip),%rax        # b58 <HUF_decompress4X2_usingDTable_internal+0x88>
			b54: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     b58:	call   *%rax
     b5a:	mov    -0xc0(%rbp),%rcx
     b61:	movzbl -0x4e(%rbp),%eax
     b65:	mov    -0xc8(%rbp),%r9
     b6c:	cmp    %r12,%rcx
     b6f:	mov    %al,-0xe0(%rbp)
     b75:	jae    ba7 <HUF_decompress4X2_usingDTable_internal+0xd7>
     b77:	mov    $0xfffffffffffffff2,%r15
     b7e:	mov    -0x30(%rbp),%rax
     b82:	sub    %gs:0x28,%rax
     b8b:	jne    213f <HUF_decompress4X2_usingDTable_internal+0x166f>
     b91:	add    $0x110,%rsp
     b98:	mov    %r15,%rax
     b9b:	pop    %rbx
     b9c:	pop    %r12
     b9e:	pop    %r13
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 21d3, pgot_memcpy_table_all_pgot

```asm
    21cd:	sub    %rax,%r13
    21d0:	mov    0x0(%rip),%rax        # 21d7 <HUF_decompress4X4_usingDTable_internal+0x87>
			21d3: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    21d7:	call   *%rax
    21d9:	mov    -0xb8(%rbp),%rcx
    21e0:	movzbl -0x4e(%rbp),%eax
    21e4:	mov    -0xc0(%rbp),%r9
    21eb:	cmp    %r13,%rcx
    21ee:	mov    %al,-0xdc(%rbp)
    21f4:	jae    2226 <HUF_decompress4X4_usingDTable_internal+0xd6>
    21f6:	mov    $0xfffffffffffffff2,%r14
    21fd:	mov    -0x30(%rbp),%rax
    2201:	sub    %gs:0x28,%rax
    220a:	jne    3cfa <HUF_decompress4X4_usingDTable_internal+0x1baa>
    2210:	add    $0xe0,%rsp
    2217:	mov    %r14,%rax
    221a:	pop    %rbx
    221b:	pop    %r12
    221d:	pop    %r13
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 270a, pgot_memcpy_table_all_pgot

```asm
    2703:	lea    (%r12,%rax,4),%rcx
    2707:	mov    0x0(%rip),%rax        # 270e <HUF_decompress4X4_usingDTable_internal+0x5be>
			270a: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    270e:	mov    %rcx,%rsi
    2711:	mov    %rcx,-0xc0(%rbp)
    2718:	call   *%rax
    271a:	mov    -0xc0(%rbp),%rcx
    2721:	mov    %r15,%rdi
    2724:	mov    $0x2,%edx
    2729:	movzbl 0x2(%rcx),%eax
    272d:	add    %eax,-0xa8(%rbp)
    2733:	movzbl 0x3(%rcx),%eax
    2737:	mov    -0x88(%rbp),%ecx
    273d:	add    %rax,%r13
    2740:	mov    -0x90(%rbp),%rax
    2747:	shl    %cl,%rax
    274a:	movzbl -0xb8(%rbp),%ecx
    2751:	shr    %cl,%rax
    2754:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 275b, pgot_memcpy_table_all_pgot

```asm
    2754:	lea    (%r12,%rax,4),%rcx
    2758:	mov    0x0(%rip),%rax        # 275f <HUF_decompress4X4_usingDTable_internal+0x60f>
			275b: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    275f:	mov    %rcx,%rsi
    2762:	mov    %rcx,-0xc0(%rbp)
    2769:	call   *%rax
    276b:	mov    -0xc0(%rbp),%rcx
    2772:	mov    %r14,%rdi
    2775:	mov    $0x2,%edx
    277a:	movzbl 0x2(%rcx),%eax
    277e:	add    %eax,-0x88(%rbp)
    2784:	movzbl 0x3(%rcx),%eax
    2788:	mov    -0x68(%rbp),%ecx
    278b:	add    %rax,%r15
    278e:	mov    -0x70(%rbp),%rax
    2792:	shl    %cl,%rax
    2795:	movzbl -0xb8(%rbp),%ecx
    279c:	shr    %cl,%rax
    279f:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 27a6, pgot_memcpy_table_all_pgot

```asm
    279f:	lea    (%r12,%rax,4),%rcx
    27a3:	mov    0x0(%rip),%rax        # 27aa <HUF_decompress4X4_usingDTable_internal+0x65a>
			27a6: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    27aa:	mov    %rcx,%rsi
    27ad:	mov    %rcx,-0xc0(%rbp)
    27b4:	call   *%rax
    27b6:	mov    -0xc0(%rbp),%rcx
    27bd:	mov    %rbx,%rdi
    27c0:	mov    $0x2,%edx
    27c5:	movzbl 0x2(%rcx),%eax
    27c9:	add    %eax,-0x68(%rbp)
    27cc:	movzbl 0x3(%rcx),%eax
    27d0:	mov    -0x48(%rbp),%ecx
    27d3:	add    %rax,%r14
    27d6:	mov    -0x50(%rbp),%rax
    27da:	shl    %cl,%rax
    27dd:	movzbl -0xb8(%rbp),%ecx
    27e4:	shr    %cl,%rax
    27e7:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 27ee, pgot_memcpy_table_all_pgot

```asm
    27e7:	lea    (%r12,%rax,4),%rcx
    27eb:	mov    0x0(%rip),%rax        # 27f2 <HUF_decompress4X4_usingDTable_internal+0x6a2>
			27ee: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    27f2:	mov    %rcx,%rsi
    27f5:	mov    %rcx,-0xc0(%rbp)
    27fc:	call   *%rax
    27fe:	mov    -0xc0(%rbp),%rcx
    2805:	mov    %r13,%rdi
    2808:	mov    $0x2,%edx
    280d:	movzbl 0x2(%rcx),%eax
    2811:	add    %eax,-0x48(%rbp)
    2814:	movzbl 0x3(%rcx),%eax
    2818:	mov    -0xa8(%rbp),%ecx
    281e:	add    %rax,%rbx
    2821:	mov    -0xb0(%rbp),%rax
    2828:	shl    %cl,%rax
    282b:	movzbl -0xb8(%rbp),%ecx
    2832:	shr    %cl,%rax
    2835:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 283c, pgot_memcpy_table_all_pgot

```asm
    2835:	lea    (%r12,%rax,4),%rcx
    2839:	mov    0x0(%rip),%rax        # 2840 <HUF_decompress4X4_usingDTable_internal+0x6f0>
			283c: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2840:	mov    %rcx,%rsi
    2843:	mov    %rcx,-0xc0(%rbp)
    284a:	call   *%rax
    284c:	mov    -0xc0(%rbp),%rcx
    2853:	mov    %r15,%rdi
    2856:	mov    $0x2,%edx
    285b:	movzbl 0x2(%rcx),%eax
    285f:	add    %eax,-0xa8(%rbp)
    2865:	movzbl 0x3(%rcx),%eax
    2869:	mov    -0x88(%rbp),%ecx
    286f:	add    %rax,%r13
    2872:	mov    -0x90(%rbp),%rax
    2879:	shl    %cl,%rax
    287c:	movzbl -0xb8(%rbp),%ecx
    2883:	shr    %cl,%rax
    2886:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 288d, pgot_memcpy_table_all_pgot

```asm
    2886:	lea    (%r12,%rax,4),%rcx
    288a:	mov    0x0(%rip),%rax        # 2891 <HUF_decompress4X4_usingDTable_internal+0x741>
			288d: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2891:	mov    %rcx,%rsi
    2894:	mov    %rcx,-0xc0(%rbp)
    289b:	call   *%rax
    289d:	mov    -0xc0(%rbp),%rcx
    28a4:	mov    %r14,%rdi
    28a7:	mov    $0x2,%edx
    28ac:	movzbl 0x2(%rcx),%eax
    28b0:	add    %eax,-0x88(%rbp)
    28b6:	movzbl 0x3(%rcx),%eax
    28ba:	mov    -0x68(%rbp),%ecx
    28bd:	add    %rax,%r15
    28c0:	mov    -0x70(%rbp),%rax
    28c4:	shl    %cl,%rax
    28c7:	movzbl -0xb8(%rbp),%ecx
    28ce:	shr    %cl,%rax
    28d1:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 28d8, pgot_memcpy_table_all_pgot

```asm
    28d1:	lea    (%r12,%rax,4),%rcx
    28d5:	mov    0x0(%rip),%rax        # 28dc <HUF_decompress4X4_usingDTable_internal+0x78c>
			28d8: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    28dc:	mov    %rcx,%rsi
    28df:	mov    %rcx,-0xc0(%rbp)
    28e6:	call   *%rax
    28e8:	mov    -0xc0(%rbp),%rcx
    28ef:	mov    %rbx,%rdi
    28f2:	mov    $0x2,%edx
    28f7:	movzbl 0x2(%rcx),%eax
    28fb:	add    %eax,-0x68(%rbp)
    28fe:	movzbl 0x3(%rcx),%eax
    2902:	mov    -0x48(%rbp),%ecx
    2905:	add    %rax,%r14
    2908:	mov    -0x50(%rbp),%rax
    290c:	shl    %cl,%rax
    290f:	movzbl -0xb8(%rbp),%ecx
    2916:	shr    %cl,%rax
    2919:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2920, pgot_memcpy_table_all_pgot

```asm
    2919:	lea    (%r12,%rax,4),%rcx
    291d:	mov    0x0(%rip),%rax        # 2924 <HUF_decompress4X4_usingDTable_internal+0x7d4>
			2920: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2924:	mov    %rcx,%rsi
    2927:	mov    %rcx,-0xc0(%rbp)
    292e:	call   *%rax
    2930:	mov    -0xc0(%rbp),%rcx
    2937:	mov    %r13,%rdi
    293a:	mov    $0x2,%edx
    293f:	movzbl 0x2(%rcx),%eax
    2943:	add    %eax,-0x48(%rbp)
    2946:	movzbl 0x3(%rcx),%eax
    294a:	mov    -0xa8(%rbp),%ecx
    2950:	add    %rax,%rbx
    2953:	mov    -0xb0(%rbp),%rax
    295a:	shl    %cl,%rax
    295d:	movzbl -0xb8(%rbp),%ecx
    2964:	shr    %cl,%rax
    2967:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 296e, pgot_memcpy_table_all_pgot

```asm
    2967:	lea    (%r12,%rax,4),%rcx
    296b:	mov    0x0(%rip),%rax        # 2972 <HUF_decompress4X4_usingDTable_internal+0x822>
			296e: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2972:	mov    %rcx,%rsi
    2975:	mov    %rcx,-0xc0(%rbp)
    297c:	call   *%rax
    297e:	mov    -0xc0(%rbp),%rcx
    2985:	mov    %r15,%rdi
    2988:	mov    $0x2,%edx
    298d:	movzbl 0x2(%rcx),%eax
    2991:	add    %eax,-0xa8(%rbp)
    2997:	movzbl 0x3(%rcx),%eax
    299b:	mov    -0x88(%rbp),%ecx
    29a1:	add    %rax,%r13
    29a4:	mov    -0x90(%rbp),%rax
    29ab:	shl    %cl,%rax
    29ae:	movzbl -0xb8(%rbp),%ecx
    29b5:	shr    %cl,%rax
    29b8:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 29bf, pgot_memcpy_table_all_pgot

```asm
    29b8:	lea    (%r12,%rax,4),%rcx
    29bc:	mov    0x0(%rip),%rax        # 29c3 <HUF_decompress4X4_usingDTable_internal+0x873>
			29bf: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    29c3:	mov    %rcx,%rsi
    29c6:	mov    %rcx,-0xc0(%rbp)
    29cd:	call   *%rax
    29cf:	mov    -0xc0(%rbp),%rcx
    29d6:	mov    %r14,%rdi
    29d9:	mov    $0x2,%edx
    29de:	movzbl 0x2(%rcx),%eax
    29e2:	add    %eax,-0x88(%rbp)
    29e8:	movzbl 0x3(%rcx),%eax
    29ec:	mov    -0x68(%rbp),%ecx
    29ef:	add    %rax,%r15
    29f2:	mov    -0x70(%rbp),%rax
    29f6:	shl    %cl,%rax
    29f9:	movzbl -0xb8(%rbp),%ecx
    2a00:	shr    %cl,%rax
    2a03:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2a0a, pgot_memcpy_table_all_pgot

```asm
    2a03:	lea    (%r12,%rax,4),%rcx
    2a07:	mov    0x0(%rip),%rax        # 2a0e <HUF_decompress4X4_usingDTable_internal+0x8be>
			2a0a: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2a0e:	mov    %rcx,%rsi
    2a11:	mov    %rcx,-0xc0(%rbp)
    2a18:	call   *%rax
    2a1a:	mov    -0xc0(%rbp),%rcx
    2a21:	mov    %rbx,%rdi
    2a24:	mov    $0x2,%edx
    2a29:	movzbl 0x2(%rcx),%eax
    2a2d:	add    %eax,-0x68(%rbp)
    2a30:	movzbl 0x3(%rcx),%eax
    2a34:	mov    -0x48(%rbp),%ecx
    2a37:	add    %rax,%r14
    2a3a:	mov    -0x50(%rbp),%rax
    2a3e:	shl    %cl,%rax
    2a41:	movzbl -0xb8(%rbp),%ecx
    2a48:	shr    %cl,%rax
    2a4b:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2a52, pgot_memcpy_table_all_pgot

```asm
    2a4b:	lea    (%r12,%rax,4),%rcx
    2a4f:	mov    0x0(%rip),%rax        # 2a56 <HUF_decompress4X4_usingDTable_internal+0x906>
			2a52: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2a56:	mov    %rcx,%rsi
    2a59:	mov    %rcx,-0xc0(%rbp)
    2a60:	call   *%rax
    2a62:	mov    -0xc0(%rbp),%rcx
    2a69:	mov    %r13,%rdi
    2a6c:	mov    $0x2,%edx
    2a71:	movzbl 0x2(%rcx),%eax
    2a75:	add    %eax,-0x48(%rbp)
    2a78:	movzbl 0x3(%rcx),%eax
    2a7c:	mov    -0xa8(%rbp),%ecx
    2a82:	add    %rax,%rbx
    2a85:	mov    -0xb0(%rbp),%rax
    2a8c:	shl    %cl,%rax
    2a8f:	movzbl -0xb8(%rbp),%ecx
    2a96:	shr    %cl,%rax
    2a99:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2aa0, pgot_memcpy_table_all_pgot

```asm
    2a99:	lea    (%r12,%rax,4),%rcx
    2a9d:	mov    0x0(%rip),%rax        # 2aa4 <HUF_decompress4X4_usingDTable_internal+0x954>
			2aa0: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2aa4:	mov    %rcx,%rsi
    2aa7:	mov    %rcx,-0xc0(%rbp)
    2aae:	call   *%rax
    2ab0:	mov    -0xc0(%rbp),%rcx
    2ab7:	mov    %r15,%rdi
    2aba:	mov    $0x2,%edx
    2abf:	movzbl 0x2(%rcx),%eax
    2ac3:	add    %eax,-0xa8(%rbp)
    2ac9:	movzbl 0x3(%rcx),%eax
    2acd:	mov    -0x88(%rbp),%ecx
    2ad3:	add    %rax,%r13
    2ad6:	mov    -0x90(%rbp),%rax
    2add:	shl    %cl,%rax
    2ae0:	movzbl -0xb8(%rbp),%ecx
    2ae7:	shr    %cl,%rax
    2aea:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2af1, pgot_memcpy_table_all_pgot

```asm
    2aea:	lea    (%r12,%rax,4),%rcx
    2aee:	mov    0x0(%rip),%rax        # 2af5 <HUF_decompress4X4_usingDTable_internal+0x9a5>
			2af1: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2af5:	mov    %rcx,%rsi
    2af8:	mov    %rcx,-0xc0(%rbp)
    2aff:	call   *%rax
    2b01:	mov    -0xc0(%rbp),%rcx
    2b08:	mov    %r14,%rdi
    2b0b:	mov    $0x2,%edx
    2b10:	movzbl 0x2(%rcx),%eax
    2b14:	add    %eax,-0x88(%rbp)
    2b1a:	movzbl 0x3(%rcx),%eax
    2b1e:	mov    -0x68(%rbp),%ecx
    2b21:	add    %rax,%r15
    2b24:	mov    -0x70(%rbp),%rax
    2b28:	shl    %cl,%rax
    2b2b:	movzbl -0xb8(%rbp),%ecx
    2b32:	shr    %cl,%rax
    2b35:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2b3c, pgot_memcpy_table_all_pgot

```asm
    2b35:	lea    (%r12,%rax,4),%rcx
    2b39:	mov    0x0(%rip),%rax        # 2b40 <HUF_decompress4X4_usingDTable_internal+0x9f0>
			2b3c: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2b40:	mov    %rcx,%rsi
    2b43:	mov    %rcx,-0xc0(%rbp)
    2b4a:	call   *%rax
    2b4c:	mov    -0xc0(%rbp),%rcx
    2b53:	mov    $0x2,%edx
    2b58:	mov    %rbx,%rdi
    2b5b:	movzbl 0x2(%rcx),%eax
    2b5f:	add    %eax,-0x68(%rbp)
    2b62:	movzbl 0x3(%rcx),%eax
    2b66:	mov    -0x48(%rbp),%ecx
    2b69:	add    %rax,%r14
    2b6c:	mov    -0x50(%rbp),%rax
    2b70:	shl    %cl,%rax
    2b73:	movzbl -0xb8(%rbp),%ecx
    2b7a:	shr    %cl,%rax
    2b7d:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2b84, pgot_memcpy_table_all_pgot

```asm
    2b7d:	lea    (%r12,%rax,4),%rcx
    2b81:	mov    0x0(%rip),%rax        # 2b88 <HUF_decompress4X4_usingDTable_internal+0xa38>
			2b84: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2b88:	mov    %rcx,-0xc0(%rbp)
    2b8f:	mov    %rcx,%rsi
    2b92:	call   *%rax
    2b94:	mov    -0xc0(%rbp),%rcx
    2b9b:	movzbl 0x3(%rcx),%edx
    2b9f:	movzbl 0x2(%rcx),%eax
    2ba3:	mov    -0xa8(%rbp),%ecx
    2ba9:	add    -0x48(%rbp),%eax
    2bac:	add    %rdx,%rbx
    2baf:	mov    %eax,-0x48(%rbp)
    2bb2:	mov    $0x3,%edx
    2bb7:	cmp    $0x40,%ecx
    2bba:	ja     258f <HUF_decompress4X4_usingDTable_internal+0x43f>
    2bc0:	mov    -0x98(%rbp),%rdi
    2bc7:	mov    -0xa0(%rbp),%rsi
    2bce:	lea    0x8(%rdi),%rdx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2ce8, pgot_memcpy_table_all_pgot

```asm
    2ce1:	lea    (%r12,%rax,4),%r14
    2ce5:	mov    0x0(%rip),%rax        # 2cec <HUF_decompress4X4_usingDTable_internal+0xb9c>
			2ce8: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2cec:	mov    %r14,%rsi
    2cef:	call   *%rax
    2cf1:	movzbl 0x3(%r14),%eax
    2cf6:	movzbl 0x2(%r14),%ecx
    2cfb:	mov    $0x2,%edx
    2d00:	add    -0xa8(%rbp),%ecx
    2d06:	add    %rax,%r13
    2d09:	mov    -0xb0(%rbp),%rax
    2d10:	mov    %ecx,-0xa8(%rbp)
    2d16:	mov    %r13,%rdi
    2d19:	shl    %cl,%rax
    2d1c:	mov    %ebx,%ecx
    2d1e:	shr    %cl,%rax
    2d21:	lea    (%r12,%rax,4),%r14
    2d25:	mov    0x0(%rip),%rax        # 2d2c <HUF_decompress4X4_usingDTable_internal+0xbdc>
			2d28: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2d28, pgot_memcpy_table_all_pgot

```asm
    2d21:	lea    (%r12,%rax,4),%r14
    2d25:	mov    0x0(%rip),%rax        # 2d2c <HUF_decompress4X4_usingDTable_internal+0xbdc>
			2d28: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2d2c:	mov    %r14,%rsi
    2d2f:	call   *%rax
    2d31:	mov    -0xb0(%rbp),%rax
    2d38:	movzbl 0x2(%r14),%ecx
    2d3d:	mov    $0x2,%edx
    2d42:	add    -0xa8(%rbp),%ecx
    2d48:	movzbl 0x3(%r14),%edi
    2d4d:	mov    %ecx,-0xa8(%rbp)
    2d53:	shl    %cl,%rax
    2d56:	mov    %ebx,%ecx
    2d58:	shr    %cl,%rax
    2d5b:	add    %rdi,%r13
    2d5e:	lea    (%r12,%rax,4),%r14
    2d62:	mov    %r13,%rdi
    2d65:	mov    0x0(%rip),%rax        # 2d6c <HUF_decompress4X4_usingDTable_internal+0xc1c>
			2d68: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2d68, pgot_memcpy_table_all_pgot

```asm
    2d62:	mov    %r13,%rdi
    2d65:	mov    0x0(%rip),%rax        # 2d6c <HUF_decompress4X4_usingDTable_internal+0xc1c>
			2d68: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2d6c:	mov    %r14,%rsi
    2d6f:	call   *%rax
    2d71:	mov    -0xb0(%rbp),%rax
    2d78:	movzbl 0x2(%r14),%ecx
    2d7d:	mov    $0x2,%edx
    2d82:	add    -0xa8(%rbp),%ecx
    2d88:	movzbl 0x3(%r14),%r8d
    2d8d:	mov    %ecx,-0xa8(%rbp)
    2d93:	shl    %cl,%rax
    2d96:	mov    %ebx,%ecx
    2d98:	shr    %cl,%rax
    2d9b:	add    %r8,%r13
    2d9e:	lea    (%r12,%rax,4),%r14
    2da2:	mov    %r13,%rdi
    2da5:	mov    0x0(%rip),%rax        # 2dac <HUF_decompress4X4_usingDTable_internal+0xc5c>
			2da8: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2da8, pgot_memcpy_table_all_pgot

```asm
    2da2:	mov    %r13,%rdi
    2da5:	mov    0x0(%rip),%rax        # 2dac <HUF_decompress4X4_usingDTable_internal+0xc5c>
			2da8: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2dac:	mov    %r14,%rsi
    2daf:	call   *%rax
    2db1:	movzbl 0x3(%r14),%eax
    2db6:	movzbl 0x2(%r14),%ecx
    2dbb:	add    -0xa8(%rbp),%ecx
    2dc1:	mov    %ecx,-0xa8(%rbp)
    2dc7:	add    %rax,%r13
    2dca:	cmp    $0x40,%ecx
    2dcd:	ja     2ebf <HUF_decompress4X4_usingDTable_internal+0xd6f>
    2dd3:	mov    -0x98(%rbp),%rsi
    2dda:	mov    -0xa0(%rbp),%rax
    2de1:	lea    0x8(%rsi),%rdi
    2de5:	cmp    %rdi,%rax
    2de8:	jb     2c81 <HUF_decompress4X4_usingDTable_internal+0xb31>
    2dee:	mov    %ecx,%edx
    2df0:	and    $0x7,%ecx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2f48, pgot_memcpy_table_all_pgot

```asm
    2f41:	lea    (%r12,%rax,4),%r14
    2f45:	mov    0x0(%rip),%rax        # 2f4c <HUF_decompress4X4_usingDTable_internal+0xdfc>
			2f48: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2f4c:	mov    %r14,%rsi
    2f4f:	call   *%rax
    2f51:	movzbl 0x3(%r14),%eax
    2f56:	movzbl 0x2(%r14),%ecx
    2f5b:	add    -0xa8(%rbp),%ecx
    2f61:	add    %rax,%r13
    2f64:	mov    %ecx,-0xa8(%rbp)
    2f6a:	cmp    %rbx,%r13
    2f6d:	jbe    2f29 <HUF_decompress4X4_usingDTable_internal+0xdd9>
    2f6f:	mov    %r13,-0xc8(%rbp)
    2f76:	mov    -0xb8(%rbp),%r15
    2f7d:	mov    -0xc0(%rbp),%r14
    2f84:	mov    -0x108(%rbp),%r13
    2f8b:	mov    -0xc8(%rbp),%rbx
    2f92:	cmp    %rbx,-0xe8(%rbp)
    2f99:	ja     3cbb <HUF_decompress4X4_usingDTable_internal+0x1b6b>
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3044, pgot_memcpy_table_all_pgot

```asm
    303d:	lea    (%r12,%rax,4),%r14
    3041:	mov    0x0(%rip),%rax        # 3048 <HUF_decompress4X4_usingDTable_internal+0xef8>
			3044: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3048:	mov    %r14,%rsi
    304b:	call   *%rax
    304d:	movzbl 0x3(%r14),%eax
    3052:	movzbl 0x2(%r14),%ecx
    3057:	mov    $0x2,%edx
    305c:	add    -0x88(%rbp),%ecx
    3062:	add    %rax,%r13
    3065:	mov    -0x90(%rbp),%rax
    306c:	mov    %ecx,-0x88(%rbp)
    3072:	mov    %r13,%rdi
    3075:	shl    %cl,%rax
    3078:	mov    %ebx,%ecx
    307a:	shr    %cl,%rax
    307d:	lea    (%r12,%rax,4),%r14
    3081:	mov    0x0(%rip),%rax        # 3088 <HUF_decompress4X4_usingDTable_internal+0xf38>
			3084: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3084, pgot_memcpy_table_all_pgot

```asm
    307d:	lea    (%r12,%rax,4),%r14
    3081:	mov    0x0(%rip),%rax        # 3088 <HUF_decompress4X4_usingDTable_internal+0xf38>
			3084: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3088:	mov    %r14,%rsi
    308b:	call   *%rax
    308d:	mov    -0x90(%rbp),%rax
    3094:	movzbl 0x2(%r14),%ecx
    3099:	mov    $0x2,%edx
    309e:	add    -0x88(%rbp),%ecx
    30a4:	movzbl 0x3(%r14),%edi
    30a9:	mov    %ecx,-0x88(%rbp)
    30af:	shl    %cl,%rax
    30b2:	mov    %ebx,%ecx
    30b4:	shr    %cl,%rax
    30b7:	add    %rdi,%r13
    30ba:	lea    (%r12,%rax,4),%r14
    30be:	mov    %r13,%rdi
    30c1:	mov    0x0(%rip),%rax        # 30c8 <HUF_decompress4X4_usingDTable_internal+0xf78>
			30c4: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 30c4, pgot_memcpy_table_all_pgot

```asm
    30be:	mov    %r13,%rdi
    30c1:	mov    0x0(%rip),%rax        # 30c8 <HUF_decompress4X4_usingDTable_internal+0xf78>
			30c4: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    30c8:	mov    %r14,%rsi
    30cb:	call   *%rax
    30cd:	mov    -0x90(%rbp),%rax
    30d4:	movzbl 0x2(%r14),%ecx
    30d9:	mov    $0x2,%edx
    30de:	add    -0x88(%rbp),%ecx
    30e4:	movzbl 0x3(%r14),%r8d
    30e9:	mov    %ecx,-0x88(%rbp)
    30ef:	shl    %cl,%rax
    30f2:	mov    %ebx,%ecx
    30f4:	shr    %cl,%rax
    30f7:	add    %r8,%r13
    30fa:	lea    (%r12,%rax,4),%r14
    30fe:	mov    %r13,%rdi
    3101:	mov    0x0(%rip),%rax        # 3108 <HUF_decompress4X4_usingDTable_internal+0xfb8>
			3104: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3104, pgot_memcpy_table_all_pgot

```asm
    30fe:	mov    %r13,%rdi
    3101:	mov    0x0(%rip),%rax        # 3108 <HUF_decompress4X4_usingDTable_internal+0xfb8>
			3104: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3108:	mov    %r14,%rsi
    310b:	call   *%rax
    310d:	movzbl 0x3(%r14),%eax
    3112:	movzbl 0x2(%r14),%ecx
    3117:	add    -0x88(%rbp),%ecx
    311d:	mov    %ecx,-0x88(%rbp)
    3123:	add    %rax,%r13
    3126:	cmp    $0x40,%ecx
    3129:	ja     3168 <HUF_decompress4X4_usingDTable_internal+0x1018>
    312b:	mov    -0x78(%rbp),%rsi
    312f:	mov    -0x80(%rbp),%rax
    3133:	lea    0x8(%rsi),%rdi
    3137:	cmp    %rdi,%rax
    313a:	jb     2fe0 <HUF_decompress4X4_usingDTable_internal+0xe90>
    3140:	mov    %ecx,%edx
    3142:	and    $0x7,%ecx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 31e3, pgot_memcpy_table_all_pgot

```asm
    31dc:	lea    (%r12,%rax,4),%r15
    31e0:	mov    0x0(%rip),%rax        # 31e7 <HUF_decompress4X4_usingDTable_internal+0x1097>
			31e3: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    31e7:	mov    %r15,%rsi
    31ea:	call   *%rax
    31ec:	movzbl 0x3(%r15),%eax
    31f1:	movzbl 0x2(%r15),%ecx
    31f6:	add    -0x88(%rbp),%ecx
    31fc:	add    %rax,%r14
    31ff:	mov    %ecx,-0x88(%rbp)
    3205:	cmp    %rbx,%r14
    3208:	jbe    31c4 <HUF_decompress4X4_usingDTable_internal+0x1074>
    320a:	mov    %r14,%r15
    320d:	mov    -0xc0(%rbp),%r13
    3214:	mov    -0xb8(%rbp),%r14
    321b:	cmp    %r15,-0xf0(%rbp)
    3222:	ja     3c9e <HUF_decompress4X4_usingDTable_internal+0x1b4e>
    3228:	mov    -0x68(%rbp),%ecx
    322b:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 32b4, pgot_memcpy_table_all_pgot

```asm
    32ad:	lea    (%r12,%rax,4),%r15
    32b1:	mov    0x0(%rip),%rax        # 32b8 <HUF_decompress4X4_usingDTable_internal+0x1168>
			32b4: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    32b8:	mov    %r15,%rsi
    32bb:	call   *%rax
    32bd:	movzbl 0x3(%r15),%eax
    32c2:	movzbl 0x2(%r15),%ecx
    32c7:	mov    $0x2,%edx
    32cc:	add    -0x68(%rbp),%ecx
    32cf:	add    %rax,%r14
    32d2:	mov    -0x70(%rbp),%rax
    32d6:	mov    %ecx,-0x68(%rbp)
    32d9:	mov    %r14,%rdi
    32dc:	shl    %cl,%rax
    32df:	mov    %ebx,%ecx
    32e1:	shr    %cl,%rax
    32e4:	lea    (%r12,%rax,4),%r15
    32e8:	mov    0x0(%rip),%rax        # 32ef <HUF_decompress4X4_usingDTable_internal+0x119f>
			32eb: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 32eb, pgot_memcpy_table_all_pgot

```asm
    32e4:	lea    (%r12,%rax,4),%r15
    32e8:	mov    0x0(%rip),%rax        # 32ef <HUF_decompress4X4_usingDTable_internal+0x119f>
			32eb: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    32ef:	mov    %r15,%rsi
    32f2:	call   *%rax
    32f4:	movzbl 0x3(%r15),%eax
    32f9:	movzbl 0x2(%r15),%ecx
    32fe:	mov    $0x2,%edx
    3303:	add    -0x68(%rbp),%ecx
    3306:	add    %rax,%r14
    3309:	mov    -0x70(%rbp),%rax
    330d:	mov    %ecx,-0x68(%rbp)
    3310:	mov    %r14,%rdi
    3313:	shl    %cl,%rax
    3316:	mov    %ebx,%ecx
    3318:	shr    %cl,%rax
    331b:	lea    (%r12,%rax,4),%r15
    331f:	mov    0x0(%rip),%rax        # 3326 <HUF_decompress4X4_usingDTable_internal+0x11d6>
			3322: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3322, pgot_memcpy_table_all_pgot

```asm
    331b:	lea    (%r12,%rax,4),%r15
    331f:	mov    0x0(%rip),%rax        # 3326 <HUF_decompress4X4_usingDTable_internal+0x11d6>
			3322: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3326:	mov    %r15,%rsi
    3329:	call   *%rax
    332b:	mov    -0x70(%rbp),%rax
    332f:	movzbl 0x2(%r15),%ecx
    3334:	mov    $0x2,%edx
    3339:	add    -0x68(%rbp),%ecx
    333c:	movzbl 0x3(%r15),%edi
    3341:	mov    %ecx,-0x68(%rbp)
    3344:	shl    %cl,%rax
    3347:	mov    %ebx,%ecx
    3349:	shr    %cl,%rax
    334c:	lea    (%r14,%rdi,1),%r15
    3350:	lea    (%r12,%rax,4),%r14
    3354:	mov    %r15,%rdi
    3357:	mov    0x0(%rip),%rax        # 335e <HUF_decompress4X4_usingDTable_internal+0x120e>
			335a: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 335a, pgot_memcpy_table_all_pgot

```asm
    3354:	mov    %r15,%rdi
    3357:	mov    0x0(%rip),%rax        # 335e <HUF_decompress4X4_usingDTable_internal+0x120e>
			335a: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    335e:	mov    %r14,%rsi
    3361:	call   *%rax
    3363:	movzbl 0x3(%r14),%eax
    3368:	movzbl 0x2(%r14),%ecx
    336d:	add    -0x68(%rbp),%ecx
    3370:	mov    %ecx,-0x68(%rbp)
    3373:	lea    (%r15,%rax,1),%r14
    3377:	cmp    $0x40,%ecx
    337a:	ja     379a <HUF_decompress4X4_usingDTable_internal+0x164a>
    3380:	mov    -0x58(%rbp),%rsi
    3384:	mov    -0x60(%rbp),%rax
    3388:	lea    0x8(%rsi),%rdi
    338c:	cmp    %rdi,%rax
    338f:	jb     3256 <HUF_decompress4X4_usingDTable_internal+0x1106>
    3395:	mov    %ecx,%edx
    3397:	and    $0x7,%ecx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 344b, pgot_memcpy_table_all_pgot

```asm
    3444:	lea    (%r12,%rax,4),%r15
    3448:	mov    0x0(%rip),%rax        # 344f <HUF_decompress4X4_usingDTable_internal+0x12ff>
			344b: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    344f:	mov    %r15,%rsi
    3452:	call   *%rax
    3454:	movzbl 0x3(%r15),%edx
    3459:	movzbl 0x2(%r15),%eax
    345e:	add    -0x68(%rbp),%eax
    3461:	mov    %eax,-0x68(%rbp)
    3464:	add    %rdx,%r14
    3467:	cmp    $0x40,%eax
    346a:	ja     37a5 <HUF_decompress4X4_usingDTable_internal+0x1655>
    3470:	mov    -0x58(%rbp),%rsi
    3474:	lea    0x8(%rsi),%rdi
    3478:	mov    -0x60(%rbp),%rdx
    347c:	cmp    %rdi,%rdx
    347f:	jb     33eb <HUF_decompress4X4_usingDTable_internal+0x129b>
    3485:	mov    %eax,%ecx
    3487:	and    $0x7,%eax
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 35d4, pgot_memcpy_table_all_pgot

```asm
    35cd:	lea    (%r12,%rax,4),%r13
    35d1:	mov    0x0(%rip),%rax        # 35d8 <HUF_decompress4X4_usingDTable_internal+0x1488>
			35d4: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    35d8:	mov    %r13,%rsi
    35db:	call   *%rax
    35dd:	movzbl 0x3(%r13),%edx
    35e2:	movzbl 0x2(%r13),%eax
    35e7:	add    -0xa8(%rbp),%eax
    35ed:	mov    %eax,-0xa8(%rbp)
    35f3:	add    %rdx,%rbx
    35f6:	cmp    $0x40,%eax
    35f9:	ja     3640 <HUF_decompress4X4_usingDTable_internal+0x14f0>
    35fb:	mov    -0x98(%rbp),%rsi
    3602:	lea    0x8(%rsi),%rdi
    3606:	mov    -0xa0(%rbp),%rdx
    360d:	cmp    %rdi,%rdx
    3610:	jb     3564 <HUF_decompress4X4_usingDTable_internal+0x1414>
    3616:	mov    %eax,%ecx
    3618:	and    $0x7,%eax
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 371e, pgot_memcpy_table_all_pgot

```asm
    3717:	lea    (%r12,%rax,4),%rbx
    371b:	mov    0x0(%rip),%rax        # 3722 <HUF_decompress4X4_usingDTable_internal+0x15d2>
			371e: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3722:	mov    %rbx,%rsi
    3725:	call   *%rax
    3727:	movzbl 0x3(%rbx),%edx
    372b:	movzbl 0x2(%rbx),%eax
    372f:	add    -0x88(%rbp),%eax
    3735:	mov    %eax,-0x88(%rbp)
    373b:	add    %rdx,%r15
    373e:	cmp    $0x40,%eax
    3741:	ja     318a <HUF_decompress4X4_usingDTable_internal+0x103a>
    3747:	mov    -0x78(%rbp),%rsi
    374b:	lea    0x8(%rsi),%rdi
    374f:	mov    -0x80(%rbp),%rdx
    3753:	cmp    %rdi,%rdx
    3756:	jb     36b1 <HUF_decompress4X4_usingDTable_internal+0x1561>
    375c:	mov    %eax,%ecx
    375e:	and    $0x7,%eax
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 37de, pgot_memcpy_table_all_pgot

```asm
    37d7:	lea    (%r12,%rax,4),%r13
    37db:	mov    0x0(%rip),%rax        # 37e2 <HUF_decompress4X4_usingDTable_internal+0x1692>
			37de: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    37e2:	mov    %r13,%rsi
    37e5:	call   *%rax
    37e7:	movzbl 0x3(%r13),%eax
    37ec:	movzbl 0x2(%r13),%ecx
    37f1:	add    -0x68(%rbp),%ecx
    37f4:	add    %rax,%r14
    37f7:	mov    %ecx,-0x68(%rbp)
    37fa:	cmp    %rbx,%r14
    37fd:	jbe    37c2 <HUF_decompress4X4_usingDTable_internal+0x1672>
    37ff:	mov    -0xb8(%rbp),%r13
    3806:	cmp    %r14,-0xf8(%rbp)
    380d:	ja     3c84 <HUF_decompress4X4_usingDTable_internal+0x1b34>
    3813:	mov    -0x48(%rbp),%ecx
    3816:	cmp    $0x40,%ecx
    3819:	ja     3a9a <HUF_decompress4X4_usingDTable_internal+0x194a>
    381f:	mov    -0xdc(%rbp),%ebx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3890, pgot_memcpy_table_all_pgot

```asm
    3889:	lea    (%r12,%rax,4),%r15
    388d:	mov    0x0(%rip),%rax        # 3894 <HUF_decompress4X4_usingDTable_internal+0x1744>
			3890: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3894:	mov    %r15,%rsi
    3897:	call   *%rax
    3899:	movzbl 0x3(%r15),%eax
    389e:	movzbl 0x2(%r15),%ecx
    38a3:	mov    $0x2,%edx
    38a8:	add    -0x48(%rbp),%ecx
    38ab:	add    %rax,%r13
    38ae:	mov    -0x50(%rbp),%rax
    38b2:	mov    %ecx,-0x48(%rbp)
    38b5:	mov    %r13,%rdi
    38b8:	shl    %cl,%rax
    38bb:	mov    %ebx,%ecx
    38bd:	shr    %cl,%rax
    38c0:	lea    (%r12,%rax,4),%r15
    38c4:	mov    0x0(%rip),%rax        # 38cb <HUF_decompress4X4_usingDTable_internal+0x177b>
			38c7: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 38c7, pgot_memcpy_table_all_pgot

```asm
    38c0:	lea    (%r12,%rax,4),%r15
    38c4:	mov    0x0(%rip),%rax        # 38cb <HUF_decompress4X4_usingDTable_internal+0x177b>
			38c7: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    38cb:	mov    %r15,%rsi
    38ce:	call   *%rax
    38d0:	movzbl 0x3(%r15),%eax
    38d5:	movzbl 0x2(%r15),%ecx
    38da:	mov    $0x2,%edx
    38df:	add    -0x48(%rbp),%ecx
    38e2:	add    %rax,%r13
    38e5:	mov    -0x50(%rbp),%rax
    38e9:	mov    %ecx,-0x48(%rbp)
    38ec:	mov    %r13,%rdi
    38ef:	shl    %cl,%rax
    38f2:	mov    %ebx,%ecx
    38f4:	shr    %cl,%rax
    38f7:	lea    (%r12,%rax,4),%r15
    38fb:	mov    0x0(%rip),%rax        # 3902 <HUF_decompress4X4_usingDTable_internal+0x17b2>
			38fe: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 38fe, pgot_memcpy_table_all_pgot

```asm
    38f7:	lea    (%r12,%rax,4),%r15
    38fb:	mov    0x0(%rip),%rax        # 3902 <HUF_decompress4X4_usingDTable_internal+0x17b2>
			38fe: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3902:	mov    %r15,%rsi
    3905:	call   *%rax
    3907:	movzbl 0x3(%r15),%eax
    390c:	movzbl 0x2(%r15),%ecx
    3911:	mov    $0x2,%edx
    3916:	add    -0x48(%rbp),%ecx
    3919:	add    %rax,%r13
    391c:	mov    -0x50(%rbp),%rax
    3920:	mov    %ecx,-0x48(%rbp)
    3923:	mov    %r13,%rdi
    3926:	shl    %cl,%rax
    3929:	mov    %ebx,%ecx
    392b:	shr    %cl,%rax
    392e:	lea    (%r12,%rax,4),%r15
    3932:	mov    0x0(%rip),%rax        # 3939 <HUF_decompress4X4_usingDTable_internal+0x17e9>
			3935: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3935, pgot_memcpy_table_all_pgot

```asm
    392e:	lea    (%r12,%rax,4),%r15
    3932:	mov    0x0(%rip),%rax        # 3939 <HUF_decompress4X4_usingDTable_internal+0x17e9>
			3935: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3939:	mov    %r15,%rsi
    393c:	call   *%rax
    393e:	movzbl 0x3(%r15),%eax
    3943:	movzbl 0x2(%r15),%ecx
    3948:	add    -0x48(%rbp),%ecx
    394b:	mov    %ecx,-0x48(%rbp)
    394e:	add    %rax,%r13
    3951:	cmp    $0x40,%ecx
    3954:	ja     3a9a <HUF_decompress4X4_usingDTable_internal+0x194a>
    395a:	mov    -0x38(%rbp),%rsi
    395e:	mov    -0x40(%rbp),%rax
    3962:	lea    0x8(%rsi),%rdi
    3966:	cmp    %rdi,%rax
    3969:	jb     3836 <HUF_decompress4X4_usingDTable_internal+0x16e6>
    396f:	mov    %ecx,%edx
    3971:	and    $0x7,%ecx
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3a16, pgot_memcpy_table_all_pgot

```asm
    3a0f:	lea    (%r12,%rax,4),%r15
    3a13:	mov    0x0(%rip),%rax        # 3a1a <HUF_decompress4X4_usingDTable_internal+0x18ca>
			3a16: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3a1a:	mov    %r15,%rsi
    3a1d:	call   *%rax
    3a1f:	movzbl 0x3(%r15),%edx
    3a24:	movzbl 0x2(%r15),%eax
    3a29:	add    -0x48(%rbp),%eax
    3a2c:	mov    %eax,-0x48(%rbp)
    3a2f:	add    %rdx,%r13
    3a32:	cmp    $0x40,%eax
    3a35:	ja     3aa5 <HUF_decompress4X4_usingDTable_internal+0x1955>
    3a37:	mov    -0x38(%rbp),%rsi
    3a3b:	lea    0x8(%rsi),%rdi
    3a3f:	mov    -0x40(%rbp),%rdx
    3a43:	cmp    %rdi,%rdx
    3a46:	jb     39ba <HUF_decompress4X4_usingDTable_internal+0x186a>
    3a4c:	mov    %eax,%ecx
    3a4e:	and    $0x7,%eax
```

## 04_zstd_decompress/no_retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3ad7, pgot_memcpy_table_all_pgot

```asm
    3ad0:	lea    (%r12,%rax,4),%r15
    3ad4:	mov    0x0(%rip),%rax        # 3adb <HUF_decompress4X4_usingDTable_internal+0x198b>
			3ad7: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3adb:	mov    %r15,%rsi
    3ade:	call   *%rax
    3ae0:	movzbl 0x3(%r15),%eax
    3ae5:	movzbl 0x2(%r15),%ecx
    3aea:	add    -0x48(%rbp),%ecx
    3aed:	add    %rax,%r13
    3af0:	mov    %ecx,-0x48(%rbp)
    3af3:	cmp    %rbx,%r13
    3af6:	jbe    3abb <HUF_decompress4X4_usingDTable_internal+0x196b>
    3af8:	cmp    %r13,-0x100(%rbp)
    3aff:	ja     3c6a <HUF_decompress4X4_usingDTable_internal+0x1b1a>
    3b05:	mov    -0x98(%rbp),%rbx
    3b0c:	xor    %eax,%eax
    3b0e:	cmp    %rbx,-0xa0(%rbp)
    3b15:	je     3ce9 <HUF_decompress4X4_usingDTable_internal+0x1b99>
    3b1b:	mov    -0x78(%rbp),%rbx
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_readDTableX2_wksp_all_pgot, 3da0, pgot_memcpy_table_all_pgot

```asm
    3d98:	mov    $0x4,%edx
    3d9d:	mov    0x0(%rip),%rax        # 3da4 <pgot_HUF_readDTableX2_wksp_all_pgot+0xa4>
			3da0: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3da4:	mov    %rbx,%rsi
    3da7:	lea    -0x34(%rbp),%rdi
    3dab:	call   *%rax
    3dad:	movzbl -0x34(%rbp),%eax
    3db1:	mov    -0x3c(%rbp),%edx
    3db4:	add    $0x1,%eax
    3db7:	cmp    %edx,%eax
    3db9:	jb     3eaf <pgot_HUF_readDTableX2_wksp_all_pgot+0x1af>
    3dbf:	mov    %dl,-0x32(%rbp)
    3dc2:	lea    -0x34(%rbp),%rsi
    3dc6:	mov    %rbx,%rdi
    3dc9:	mov    0x0(%rip),%rax        # 3dd0 <pgot_HUF_readDTableX2_wksp_all_pgot+0xd0>
			3dcc: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3dd0:	movb   $0x0,-0x33(%rbp)
    3dd4:	mov    $0x4,%edx
    3dd9:	call   *%rax
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_readDTableX2_wksp_all_pgot, 3dcc, pgot_memcpy_table_all_pgot

```asm
    3dc6:	mov    %rbx,%rdi
    3dc9:	mov    0x0(%rip),%rax        # 3dd0 <pgot_HUF_readDTableX2_wksp_all_pgot+0xd0>
			3dcc: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3dd0:	movb   $0x0,-0x33(%rbp)
    3dd4:	mov    $0x4,%edx
    3dd9:	call   *%rax
    3ddb:	mov    -0x3c(%rbp),%r9d
    3ddf:	lea    0x1(%r9),%esi
    3de3:	cmp    $0x1,%esi
    3de6:	jbe    3e2a <pgot_HUF_readDTableX2_wksp_all_pgot+0x12a>
    3de8:	mov    0x4(%r12),%r10d
    3ded:	lea    0x4(%r12),%r8
    3df2:	xor    %edx,%edx
    3df4:	mov    $0x1,%eax
    3df9:	jmp    3e13 <pgot_HUF_readDTableX2_wksp_all_pgot+0x113>
    3dfb:	mov    %r11d,%edx
    3dfe:	lea    (%r12,%rdx,4),%r8
    3e02:	mov    (%r8),%r10d
    3e05:	cmp    $0x1f,%eax
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress1X2_usingDTable_all_pgot, 3f03, pgot_memcpy_table_all_pgot

```asm
    3efe:	xor    %eax,%eax
    3f00:	mov    0x0(%rip),%rax        # 3f07 <pgot_HUF_decompress1X2_usingDTable_all_pgot+0x47>
			3f03: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3f07:	call   *%rax
    3f09:	cmpb   $0x0,-0x33(%rbp)
    3f0d:	mov    $0xffffffffffffffff,%rax
    3f14:	jne    3f2a <pgot_HUF_decompress1X2_usingDTable_all_pgot+0x6a>
    3f16:	mov    %rbx,%r8
    3f19:	mov    %r15,%rcx
    3f1c:	mov    %r14,%rdx
    3f1f:	mov    %r13,%rsi
    3f22:	mov    %r12,%rdi
    3f25:	call   3e0 <HUF_decompress1X2_usingDTable_internal>
    3f2a:	mov    -0x30(%rbp),%rdx
    3f2e:	sub    %gs:0x28,%rdx
    3f37:	jne    3f49 <pgot_HUF_decompress1X2_usingDTable_all_pgot+0x89>
    3f39:	add    $0x10,%rsp
    3f3d:	pop    %rbx
    3f3e:	pop    %r12
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress4X2_usingDTable_all_pgot, 4023, pgot_memcpy_table_all_pgot

```asm
    401e:	xor    %eax,%eax
    4020:	mov    0x0(%rip),%rax        # 4027 <pgot_HUF_decompress4X2_usingDTable_all_pgot+0x47>
			4023: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4027:	call   *%rax
    4029:	cmpb   $0x0,-0x33(%rbp)
    402d:	mov    $0xffffffffffffffff,%rax
    4034:	jne    404a <pgot_HUF_decompress4X2_usingDTable_all_pgot+0x6a>
    4036:	mov    %rbx,%r8
    4039:	mov    %r15,%rcx
    403c:	mov    %r14,%rdx
    403f:	mov    %r13,%rsi
    4042:	mov    %r12,%rdi
    4045:	call   ad0 <HUF_decompress4X2_usingDTable_internal>
    404a:	mov    -0x30(%rbp),%rdx
    404e:	sub    %gs:0x28,%rdx
    4057:	jne    4069 <pgot_HUF_decompress4X2_usingDTable_all_pgot+0x89>
    4059:	add    $0x10,%rsp
    405d:	pop    %rbx
    405e:	pop    %r12
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_readDTableX4_wksp_all_pgot, 4148, pgot_memcpy_table_all_pgot

```asm
    4143:	xor    %eax,%eax
    4145:	mov    0x0(%rip),%rax        # 414c <pgot_HUF_readDTableX4_wksp_all_pgot+0x4c>
			4148: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    414c:	call   *%rax
    414e:	movzbl -0x68(%rbp),%r12d
    4153:	mov    %r12b,-0xbd(%rbp)
    415a:	cmp    $0x5db,%rbx
    4161:	jbe    4501 <pgot_HUF_readDTableX4_wksp_all_pgot+0x401>
    4167:	lea    0x270(%r14),%r15
    416e:	xor    %esi,%esi
    4170:	mov    $0x6c,%edx
    4175:	mov    0x0(%rip),%rax        # 417c <pgot_HUF_readDTableX4_wksp_all_pgot+0x7c>
			4178: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    417c:	mov    %r15,%rdi
    417f:	call   *%rax
    4181:	cmp    $0xc,%r12d
    4185:	ja     4501 <pgot_HUF_readDTableX4_wksp_all_pgot+0x401>
    418b:	mov    %r13,%r9
    418e:	lea    -0x70(%rbp),%r8
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_readDTableX4_wksp_all_pgot, 4178, pgot_memset_table_all_pgot

```asm
    4170:	mov    $0x6c,%edx
    4175:	mov    0x0(%rip),%rax        # 417c <pgot_HUF_readDTableX4_wksp_all_pgot+0x7c>
			4178: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    417c:	mov    %r15,%rdi
    417f:	call   *%rax
    4181:	cmp    $0xc,%r12d
    4185:	ja     4501 <pgot_HUF_readDTableX4_wksp_all_pgot+0x401>
    418b:	mov    %r13,%r9
    418e:	lea    -0x70(%rbp),%r8
    4192:	lea    -0x6c(%rbp),%rcx
    4196:	mov    %r15,%rdx
    4199:	lea    0x5dc(%r14),%rax
    41a0:	sub    $0x5dc,%rbx
    41a7:	mov    $0x100,%esi
    41ac:	push   %rbx
    41ad:	lea    0x4dc(%r14),%rdi
    41b4:	push   %rax
    41b5:	push   -0x80(%rbp)
    41b8:	call   41bd <pgot_HUF_readDTableX4_wksp_all_pgot+0xbd>
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_readDTableX4_wksp_all_pgot, 4388, pgot_memcpy_table_all_pgot

```asm
    437f:	mov    %eax,-0xb8(%rbp)
    4385:	mov    0x0(%rip),%rax        # 438c <pgot_HUF_readDTableX4_wksp_all_pgot+0x28c>
			4388: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    438c:	call   *%rax
    438e:	mov    -0x84(%rbp),%r10d
    4395:	test   %r10d,%r10d
    4398:	je     4536 <pgot_HUF_readDTableX4_wksp_all_pgot+0x436>
    439e:	lea    -0x1(%r10),%eax
    43a2:	sub    %ebx,%r12d
    43a5:	mov    %r14,%r11
    43a8:	mov    %r10d,-0xbc(%rbp)
    43af:	lea    0x2de(%r14,%rax,2),%rax
    43b7:	mov    %r12d,-0x88(%rbp)
    43be:	mov    -0xb0(%rbp),%r15
    43c5:	mov    %ebx,%r10d
    43c8:	mov    %rax,-0xa0(%rbp)
    43cf:	jmp    4485 <pgot_HUF_readDTableX4_wksp_all_pgot+0x385>
    43d4:	mov    %eax,-0x98(%rbp)
    43da:	mov    -0xb8(%rbp),%eax
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_readDTableX4_wksp_all_pgot, 4554, pgot_memcpy_table_all_pgot

```asm
    454e:	mov    %al,-0x66(%rbp)
    4551:	mov    0x0(%rip),%rax        # 4558 <pgot_HUF_readDTableX4_wksp_all_pgot+0x458>
			4554: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4558:	call   *%rax
    455a:	jmp    450c <pgot_HUF_readDTableX4_wksp_all_pgot+0x40c>
    455c:	lea    0x1(%r11),%r8d
    4560:	mov    %r11d,%eax
    4563:	jmp    420b <pgot_HUF_readDTableX4_wksp_all_pgot+0x10b>
    4568:	mov    -0x6c(%rbp),%ebx
    456b:	lea    0x2dc(%r14),%rsi
    4572:	xor    %r10d,%r10d
    4575:	movl   $0x0,0x2a8(%r14)
    4580:	mov    %rsi,-0xb0(%rbp)
    4587:	test   %ebx,%ebx
    4589:	jne    4265 <pgot_HUF_readDTableX4_wksp_all_pgot+0x165>
    458f:	jmp    42f2 <pgot_HUF_readDTableX4_wksp_all_pgot+0x1f2>
    4594:	movl   $0x0,0x2a8(%r14)
    459f:	mov    %r12d,%ecx
    45a2:	sub    %r11d,%ecx
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress1X4_usingDTable_all_pgot, 4663, pgot_memcpy_table_all_pgot

```asm
    465e:	xor    %eax,%eax
    4660:	mov    0x0(%rip),%rax        # 4667 <pgot_HUF_decompress1X4_usingDTable_all_pgot+0x47>
			4663: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4667:	call   *%rax
    4669:	cmpb   $0x1,-0x33(%rbp)
    466d:	mov    $0xffffffffffffffff,%rax
    4674:	jne    468a <pgot_HUF_decompress1X4_usingDTable_all_pgot+0x6a>
    4676:	mov    %rbx,%r8
    4679:	mov    %r15,%rcx
    467c:	mov    %r14,%rdx
    467f:	mov    %r13,%rsi
    4682:	mov    %r12,%rdi
    4685:	call   720 <HUF_decompress1X4_usingDTable_internal>
    468a:	mov    -0x30(%rbp),%rdx
    468e:	sub    %gs:0x28,%rdx
    4697:	jne    46a9 <pgot_HUF_decompress1X4_usingDTable_all_pgot+0x89>
    4699:	add    $0x10,%rsp
    469d:	pop    %rbx
    469e:	pop    %r12
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress4X4_usingDTable_all_pgot, 4783, pgot_memcpy_table_all_pgot

```asm
    477e:	xor    %eax,%eax
    4780:	mov    0x0(%rip),%rax        # 4787 <pgot_HUF_decompress4X4_usingDTable_all_pgot+0x47>
			4783: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4787:	call   *%rax
    4789:	cmpb   $0x1,-0x33(%rbp)
    478d:	mov    $0xffffffffffffffff,%rax
    4794:	jne    47aa <pgot_HUF_decompress4X4_usingDTable_all_pgot+0x6a>
    4796:	mov    %rbx,%r8
    4799:	mov    %r15,%rcx
    479c:	mov    %r14,%rdx
    479f:	mov    %r13,%rsi
    47a2:	mov    %r12,%rdi
    47a5:	call   2150 <HUF_decompress4X4_usingDTable_internal>
    47aa:	mov    -0x30(%rbp),%rdx
    47ae:	sub    %gs:0x28,%rdx
    47b7:	jne    47c9 <pgot_HUF_decompress4X4_usingDTable_all_pgot+0x89>
    47b9:	add    $0x10,%rsp
    47bd:	pop    %rbx
    47be:	pop    %r12
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress1X_usingDTable_all_pgot, 48a3, pgot_memcpy_table_all_pgot

```asm
    489e:	xor    %eax,%eax
    48a0:	mov    0x0(%rip),%rax        # 48a7 <pgot_HUF_decompress1X_usingDTable_all_pgot+0x47>
			48a3: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    48a7:	call   *%rax
    48a9:	cmpb   $0x0,-0x33(%rbp)
    48ad:	mov    %rbx,%r8
    48b0:	mov    %r15,%rcx
    48b3:	mov    %r14,%rdx
    48b6:	mov    %r13,%rsi
    48b9:	mov    %r12,%rdi
    48bc:	je     48e2 <pgot_HUF_decompress1X_usingDTable_all_pgot+0x82>
    48be:	call   720 <HUF_decompress1X4_usingDTable_internal>
    48c3:	mov    -0x30(%rbp),%rdx
    48c7:	sub    %gs:0x28,%rdx
    48d0:	jne    48e9 <pgot_HUF_decompress1X_usingDTable_all_pgot+0x89>
    48d2:	add    $0x10,%rsp
    48d6:	pop    %rbx
    48d7:	pop    %r12
    48d9:	pop    %r13
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress4X_usingDTable_all_pgot, 4933, pgot_memcpy_table_all_pgot

```asm
    492e:	xor    %eax,%eax
    4930:	mov    0x0(%rip),%rax        # 4937 <pgot_HUF_decompress4X_usingDTable_all_pgot+0x47>
			4933: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4937:	call   *%rax
    4939:	cmpb   $0x0,-0x33(%rbp)
    493d:	mov    %rbx,%r8
    4940:	mov    %r15,%rcx
    4943:	mov    %r14,%rdx
    4946:	mov    %r13,%rsi
    4949:	mov    %r12,%rdi
    494c:	je     4972 <pgot_HUF_decompress4X_usingDTable_all_pgot+0x82>
    494e:	call   2150 <HUF_decompress4X4_usingDTable_internal>
    4953:	mov    -0x30(%rbp),%rdx
    4957:	sub    %gs:0x28,%rdx
    4960:	jne    4979 <pgot_HUF_decompress4X_usingDTable_all_pgot+0x89>
    4962:	add    $0x10,%rsp
    4966:	pop    %rbx
    4967:	pop    %r12
    4969:	pop    %r13
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_selectDecoder_all_pgot, 49a6, pgot_algoTime_all_pgot

```asm
    499f:	lea    (%rax,%rax,2),%rdx
    49a3:	mov    0x0(%rip),%rax        # 49aa <pgot_HUF_selectDecoder_all_pgot+0x2a>
			49a6: R_X86_64_PC32	pgot_algoTime_all_pgot-0x4
    49aa:	lea    (%rax,%rdx,8),%rdx
    49ae:	mov    0xc(%rdx),%eax
    49b1:	imul   %ecx,%eax
    49b4:	add    0x8(%rdx),%eax
    49b7:	mov    %eax,%esi
    49b9:	imul   0x4(%rdx),%ecx
    49bd:	add    (%rdx),%ecx
    49bf:	shr    $0x3,%esi
    49c2:	add    %esi,%eax
    49c4:	cmp    %eax,%ecx
    49c6:	seta   %al
    49c9:	movzbl %al,%eax
    49cc:	ret    
    49cd:	int3   
    49ce:	xchg   %ax,%ax

```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress4X_DCtx_wksp_all_pgot, 4a48, pgot_algoTime_all_pgot

```asm
    4a41:	lea    (%rax,%rax,2),%rdx
    4a45:	mov    0x0(%rip),%rax        # 4a4c <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x7c>
			4a48: R_X86_64_PC32	pgot_algoTime_all_pgot-0x4
    4a4c:	lea    (%rax,%rdx,8),%rdx
    4a50:	mov    0xc(%rdx),%eax
    4a53:	imul   %edi,%eax
    4a56:	add    0x8(%rdx),%eax
    4a59:	mov    %eax,%r8d
    4a5c:	imul   0x4(%rdx),%edi
    4a60:	add    (%rdx),%edi
    4a62:	mov    %r15,%rdx
    4a65:	shr    $0x3,%r8d
    4a69:	add    %r8d,%eax
    4a6c:	mov    0x10(%rbp),%r8
    4a70:	cmp    %eax,%edi
    4a72:	mov    %rbx,%rdi
    4a75:	jbe    4ac6 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xf6>
    4a77:	call   4a7c <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xac>
			4a78: R_X86_64_PLT32	pgot_HUF_readDTableX4_wksp_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress4X_DCtx_wksp_all_pgot, 4b03, pgot_memcpy_table_all_pgot

```asm
    4afe:	jmp    4ab3 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xe3>
    4b00:	mov    0x0(%rip),%rax        # 4b07 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x137>
			4b03: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4b07:	mov    %r14,%rdi
    4b0a:	mov    %r12,%r13
    4b0d:	call   *%rax
    4b0f:	jmp    4ab3 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xe3>
    4b11:	movzbl (%rcx),%esi
    4b14:	mov    0x0(%rip),%rax        # 4b1b <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x14b>
			4b17: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    4b1b:	mov    %r14,%rdi
    4b1e:	mov    %r12,%r13
    4b21:	call   *%rax
    4b23:	jmp    4ab3 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xe3>
    4b25:	mov    $0xfffffffffffffff3,%r13
    4b2c:	jmp    4ab3 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xe3>
    4b2e:	xchg   %ax,%ax

```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress4X_DCtx_wksp_all_pgot, 4b17, pgot_memset_table_all_pgot

```asm
    4b11:	movzbl (%rcx),%esi
    4b14:	mov    0x0(%rip),%rax        # 4b1b <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x14b>
			4b17: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    4b1b:	mov    %r14,%rdi
    4b1e:	mov    %r12,%r13
    4b21:	call   *%rax
    4b23:	jmp    4ab3 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xe3>
    4b25:	mov    $0xfffffffffffffff3,%r13
    4b2c:	jmp    4ab3 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xe3>
    4b2e:	xchg   %ax,%ax

```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress4X_hufOnly_wksp_all_pgot, 4b9b, pgot_algoTime_all_pgot

```asm
    4b94:	lea    (%rax,%rax,2),%rdx
    4b98:	mov    0x0(%rip),%rax        # 4b9f <pgot_HUF_decompress4X_hufOnly_wksp_all_pgot+0x6f>
			4b9b: R_X86_64_PC32	pgot_algoTime_all_pgot-0x4
    4b9f:	lea    (%rax,%rdx,8),%rdx
    4ba3:	mov    0xc(%rdx),%eax
    4ba6:	imul   %edi,%eax
    4ba9:	add    0x8(%rdx),%eax
    4bac:	mov    %eax,%r8d
    4baf:	imul   0x4(%rdx),%edi
    4bb3:	add    (%rdx),%edi
    4bb5:	mov    %rbx,%rdx
    4bb8:	shr    $0x3,%r8d
    4bbc:	add    %r8d,%eax
    4bbf:	mov    0x10(%rbp),%r8
    4bc3:	cmp    %eax,%edi
    4bc5:	mov    %r14,%rdi
    4bc8:	jbe    4c15 <pgot_HUF_decompress4X_hufOnly_wksp_all_pgot+0xe5>
    4bca:	call   4bcf <pgot_HUF_decompress4X_hufOnly_wksp_all_pgot+0x9f>
			4bcb: R_X86_64_PLT32	pgot_HUF_readDTableX4_wksp_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress1X_DCtx_wksp_all_pgot, 4ce8, pgot_algoTime_all_pgot

```asm
    4ce1:	lea    (%rax,%rax,2),%rdx
    4ce5:	mov    0x0(%rip),%rax        # 4cec <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x7c>
			4ce8: R_X86_64_PC32	pgot_algoTime_all_pgot-0x4
    4cec:	lea    (%rax,%rdx,8),%rdx
    4cf0:	mov    0xc(%rdx),%eax
    4cf3:	imul   %edi,%eax
    4cf6:	add    0x8(%rdx),%eax
    4cf9:	mov    %eax,%r8d
    4cfc:	imul   0x4(%rdx),%edi
    4d00:	add    (%rdx),%edi
    4d02:	mov    %r15,%rdx
    4d05:	shr    $0x3,%r8d
    4d09:	add    %r8d,%eax
    4d0c:	mov    0x10(%rbp),%r8
    4d10:	cmp    %eax,%edi
    4d12:	mov    %rbx,%rdi
    4d15:	jbe    4d66 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xf6>
    4d17:	call   4d1c <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xac>
			4d18: R_X86_64_PLT32	pgot_HUF_readDTableX4_wksp_all_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress1X_DCtx_wksp_all_pgot, 4da3, pgot_memcpy_table_all_pgot

```asm
    4d9e:	jmp    4d53 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xe3>
    4da0:	mov    0x0(%rip),%rax        # 4da7 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x137>
			4da3: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4da7:	mov    %r14,%rdi
    4daa:	mov    %r12,%r13
    4dad:	call   *%rax
    4daf:	jmp    4d53 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xe3>
    4db1:	movzbl (%rcx),%esi
    4db4:	mov    0x0(%rip),%rax        # 4dbb <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x14b>
			4db7: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    4dbb:	mov    %r14,%rdi
    4dbe:	mov    %r12,%r13
    4dc1:	call   *%rax
    4dc3:	jmp    4d53 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xe3>
    4dc5:	mov    $0xfffffffffffffff3,%r13
    4dcc:	jmp    4d53 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xe3>

Disassembly of section .text.unlikely:

```

## 04_zstd_decompress/no_retpoline/all_pgot: pgot_HUF_decompress1X_DCtx_wksp_all_pgot, 4db7, pgot_memset_table_all_pgot

```asm
    4db1:	movzbl (%rcx),%esi
    4db4:	mov    0x0(%rip),%rax        # 4dbb <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x14b>
			4db7: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    4dbb:	mov    %r14,%rdi
    4dbe:	mov    %r12,%r13
    4dc1:	call   *%rax
    4dc3:	jmp    4d53 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xe3>
    4dc5:	mov    $0xfffffffffffffff3,%r13
    4dcc:	jmp    4d53 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xe3>

Disassembly of section .text.unlikely:

```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_execSequenceLast7_data_pgot.isra.0, 5e6, memmove

```asm
     5e2:	mov    %r13,%rdx
     5e5:	call   5ea <pgot_ZSTD_execSequenceLast7_data_pgot.isra.0+0xea>
			5e6: R_X86_64_PLT32	memmove-0x4
     5ea:	mov    0x18(%rbp),%rsi
     5ee:	lea    (%rax,%r13,1),%rax
     5f2:	cmp    %rax,%rbx
     5f5:	jbe    61e <pgot_ZSTD_execSequenceLast7_data_pgot.isra.0+0x11e>
     5f7:	sub    %rax,%rbx
     5fa:	xor    %edx,%edx
     5fc:	movzbl (%rsi,%rdx,1),%ecx
     600:	mov    %cl,(%rax,%rdx,1)
     603:	add    $0x1,%rdx
     607:	cmp    %rbx,%rdx
     60a:	jne    5fc <pgot_ZSTD_execSequenceLast7_data_pgot.isra.0+0xfc>
     60c:	pop    %rbx
     60d:	mov    %r12,%rax
     610:	pop    %r12
     612:	pop    %r13
     614:	pop    %rbp
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_execSequenceLast7_data_pgot.isra.0, 65f, memmove

```asm
     65b:	mov    %r10,%rdx
     65e:	call   663 <pgot_ZSTD_execSequenceLast7_data_pgot.isra.0+0x163>
			65f: R_X86_64_PLT32	memmove-0x4
     663:	jmp    61e <pgot_ZSTD_execSequenceLast7_data_pgot.isra.0+0x11e>
     665:	data16 cs nopw 0x0(%rax,%rax,1)

```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_copyDCtx_data_pgot, def, memcpy

```asm
     deb:	mov    %rsp,%rbp
     dee:	call   df3 <pgot_ZSTD_copyDCtx_data_pgot+0x13>
			def: R_X86_64_PLT32	memcpy-0x4
     df3:	pop    %rbp
     df4:	ret    
     df5:	int3   
     df6:	cs nopw 0x0(%rax,%rax,1)

```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decodeLiteralsBlock_data_pgot, 1282, memcpy

```asm
    127e:	mov    %rcx,%rdi
    1281:	call   1286 <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x96>
			1282: R_X86_64_PLT32	memcpy-0x4
    1286:	mov    %rbx,0x6110(%r12)
    128e:	mov    %rax,0x60f0(%r12)
    1296:	movq   $0x0,(%rax,%rbx,1)
    129e:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x104>
    12a0:	mov    0x6088(%r12),%esi
    12a8:	mov    $0xffffffffffffffed,%r13
    12af:	test   %esi,%esi
    12b1:	je     12f4 <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x104>
    12b3:	cmp    $0x4,%rdx
    12b7:	jbe    12ed <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0xfd>
    12b9:	mov    (%rdi),%r8d
    12bc:	shr    $0x2,%al
    12bf:	and    $0x3,%eax
    12c2:	mov    %r8d,%ecx
    12c5:	shr    $0x4,%ecx
    12c8:	cmp    $0x2,%al
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decodeLiteralsBlock_data_pgot, 1427, memset

```asm
    1423:	mov    %rcx,%rdi
    1426:	call   142b <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x23b>
			1427: R_X86_64_PLT32	memset-0x4
    142b:	mov    %rbx,0x6110(%r12)
    1433:	mov    %rax,0x60f0(%r12)
    143b:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x104>
    1440:	add    %rdi,%rsi
    1443:	mov    %rbx,0x6110(%r12)
    144b:	mov    %rsi,0x60f0(%r12)
    1453:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x104>
    1458:	movzbl 0x2(%rsi),%ebx
    145c:	movzwl (%rsi),%eax
    145f:	mov    $0x3,%esi
    1464:	shl    $0x10,%ebx
    1467:	add    %eax,%ebx
    1469:	shr    $0x4,%ebx
    146c:	jmp    125a <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x6a>
    1471:	movzbl 0x2(%rsi),%ebx
    1475:	movzwl (%rsi),%eax
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decodeSeqHeaders_data_pgot, 15e0, pgot_LL_defaultDTable_data_pgot

```asm
    15db:	sub    %r9,%rax
    15de:	push   0x0(%rip)        # 15e4 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x94>
			15e0: R_X86_64_PC32	pgot_LL_defaultDTable_data_pgot-0x4
    15e4:	push   %rax
    15e5:	call   400 <ZSTD_buildSeqTable.constprop.0>
    15ea:	mov    -0x30(%rbp),%r9
    15ee:	add    $0x20,%rsp
    15f2:	cmp    $0xffffffffffffffea,%rax
    15f6:	ja     16e7 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x197>
    15fc:	push   %r15
    15fe:	add    %rax,%r9
    1601:	mov    0x608c(%r13),%eax
    1608:	mov    %r14d,%edx
    160b:	shr    $0x4,%dl
    160e:	lea    0x10(%r13),%rsi
    1612:	mov    $0x1c,%ecx
    1617:	mov    %r9,-0x30(%rbp)
    161b:	push   %rax
    161c:	mov    %rbx,%rax
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decodeSeqHeaders_data_pgot, 162e, pgot_OF_defaultDTable_data_pgot

```asm
    1629:	sub    %r9,%rax
    162c:	push   0x0(%rip)        # 1632 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0xe2>
			162e: R_X86_64_PC32	pgot_OF_defaultDTable_data_pgot-0x4
    1632:	mov    $0x8,%r8d
    1638:	push   %rax
    1639:	call   400 <ZSTD_buildSeqTable.constprop.0>
    163e:	add    $0x20,%rsp
    1642:	cmp    $0xffffffffffffffea,%rax
    1646:	ja     16e7 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x197>
    164c:	mov    -0x30(%rbp),%r9
    1650:	push   %r15
    1652:	mov    %r14d,%edx
    1655:	lea    0x8(%r13),%rsi
    1659:	shr    $0x2,%dl
    165c:	mov    $0x9,%r8d
    1662:	mov    $0x34,%ecx
    1667:	add    %rax,%r9
    166a:	mov    0x608c(%r13),%eax
    1671:	and    $0x3,%edx
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decodeSeqHeaders_data_pgot, 1685, pgot_ML_defaultDTable_data_pgot

```asm
    1682:	push   %rax
    1683:	push   0x0(%rip)        # 1689 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x139>
			1685: R_X86_64_PC32	pgot_ML_defaultDTable_data_pgot-0x4
    1689:	push   %rbx
    168a:	call   400 <ZSTD_buildSeqTable.constprop.0>
    168f:	add    $0x20,%rsp
    1693:	cmp    $0xffffffffffffffea,%rax
    1697:	ja     16e7 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x197>
    1699:	mov    -0x30(%rbp),%r9
    169d:	add    %r9,%rax
    16a0:	sub    %r12,%rax
    16a3:	jmp    16ee <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x19e>
    16a5:	cmp    $0xff,%eax
    16aa:	je     1719 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x1c9>
    16ac:	cmp    %r9,%rbx
    16af:	jbe    16d0 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x180>
    16b1:	lea    0x2(%rdx),%r9
    16b5:	add    $0xffffff80,%eax
    16b8:	movzbl 0x1(%rdx),%edx
```

## 04_zstd_decompress/no_retpoline/data_pgot: ZSTD_decompressSequencesLong, 1854, memcpy

```asm
    1850:	mov    %r11,%rdi
    1853:	call   1858 <ZSTD_decompressSequencesLong+0x118>
			1854: R_X86_64_PLT32	memcpy-0x4
    1858:	add    %rax,%rbx
    185b:	sub    -0x118(%rbp),%rbx
    1862:	mov    %rbx,%r12
    1865:	mov    -0x38(%rbp),%rax
    1869:	sub    %gs:0x28,%rax
    1872:	jne    24ab <ZSTD_decompressSequencesLong+0xd6b>
    1878:	lea    -0x30(%rbp),%rsp
    187c:	mov    %r12,%rax
    187f:	pop    %rbx
    1880:	pop    %r10
    1882:	pop    %r12
    1884:	pop    %r13
    1886:	pop    %r14
    1888:	pop    %r15
    188a:	pop    %rbp
    188b:	lea    -0x8(%r10),%rsp
```

## 04_zstd_decompress/no_retpoline/data_pgot: ZSTD_decompressSequencesLong, 1d5a, memmove

```asm
    1d52:	mov    %r10,-0x158(%rbp)
    1d59:	call   1d5e <ZSTD_decompressSequencesLong+0x61e>
			1d5a: R_X86_64_PLT32	memmove-0x4
    1d5e:	mov    -0x140(%rbp),%rdx
    1d65:	mov    -0x170(%rbp),%r11
    1d6c:	mov    %rax,%rdi
    1d6f:	mov    -0x178(%rbp),%r9
    1d76:	sub    %rdx,%r11
    1d79:	add    %rdx,%rdi
    1d7c:	cmp    $0x2,%r11
    1d80:	jbe    2464 <ZSTD_decompressSequencesLong+0xd24>
    1d86:	cmp    %r13,%rdi
    1d89:	mov    -0x158(%rbp),%r10
    1d90:	mov    -0x160(%rbp),%r8
    1d97:	mov    %r14,%rsi
    1d9a:	ja     2464 <ZSTD_decompressSequencesLong+0xd24>
    1da0:	cmp    $0x7,%r10
    1da4:	ja     2400 <ZSTD_decompressSequencesLong+0xcc0>
    1daa:	movzbl (%rsi),%eax
```

## 04_zstd_decompress/no_retpoline/data_pgot: ZSTD_decompressSequencesLong, 200e, memmove

```asm
    2006:	mov    %r8,-0x180(%rbp)
    200d:	call   2012 <ZSTD_decompressSequencesLong+0x8d2>
			200e: R_X86_64_PLT32	memmove-0x4
    2012:	mov    -0x170(%rbp),%rcx
    2019:	mov    -0x158(%rbp),%r9
    2020:	mov    %rax,%rdi
    2023:	mov    -0x178(%rbp),%r10d
    202a:	add    %rbx,%rdi
    202d:	sub    %rbx,%rcx
    2030:	cmp    %rdi,%r9
    2033:	jb     204d <ZSTD_decompressSequencesLong+0x90d>
    2035:	cmp    $0x2,%rcx
    2039:	mov    -0x128(%rbp),%rsi
    2040:	mov    -0x180(%rbp),%r8
    2047:	ja     20d6 <ZSTD_decompressSequencesLong+0x996>
    204d:	test   %rcx,%rcx
    2050:	je     2071 <ZSTD_decompressSequencesLong+0x931>
    2052:	mov    -0x128(%rbp),%r8
    2059:	xor    %edx,%edx
```

## 04_zstd_decompress/no_retpoline/data_pgot: ZSTD_decompressSequencesLong, 235a, memmove

```asm
    2352:	mov    %r10d,-0x158(%rbp)
    2359:	call   235e <ZSTD_decompressSequencesLong+0xc1e>
			235a: R_X86_64_PLT32	memmove-0x4
    235e:	mov    -0x158(%rbp),%r10d
    2365:	jmp    2071 <ZSTD_decompressSequencesLong+0x931>
    236a:	mov    %rbx,%r14
    236d:	mov    %r13,%r11
    2370:	mov    -0x160(%rbp),%rbx
    2377:	mov    %r10d,%r13d
    237a:	jmp    1c42 <ZSTD_decompressSequencesLong+0x502>
    237f:	push   -0x138(%rbp)
    2385:	mov    %r10,%r8
    2388:	mov    %r11,%rcx
    238b:	mov    %rbx,%rdi
    238e:	push   -0x148(%rbp)
    2394:	lea    -0xe0(%rbp),%r9
    239b:	mov    -0x130(%rbp),%rsi
    23a2:	push   %r14
    23a4:	push   -0x120(%rbp)
```

## 04_zstd_decompress/no_retpoline/data_pgot: ZSTD_decompressSequencesLong, 249b, memmove

```asm
    2493:	mov    %r9,-0x140(%rbp)
    249a:	call   249f <ZSTD_decompressSequencesLong+0xd5f>
			249b: R_X86_64_PLT32	memmove-0x4
    249f:	mov    -0x140(%rbp),%r9
    24a6:	jmp    1e28 <ZSTD_decompressSequencesLong+0x6e8>
    24ab:	call   24b0 <ZSTD_decompressSequencesLong+0xd70>
			24ac: R_X86_64_PLT32	__stack_chk_fail-0x4
    24b0:	mov    -0xe0(%rbp),%rax
    24b7:	mov    -0x68(%rbp),%rdx
    24bb:	mov    %rax,%r14
    24be:	mov    %edx,0x6030(%rbx)
    24c4:	mov    -0x60(%rbp),%rdx
    24c8:	mov    %edx,0x6034(%rbx)
    24ce:	mov    -0x58(%rbp),%rdx
    24d2:	mov    %edx,0x6038(%rbx)
    24d8:	jmp    182a <ZSTD_decompressSequencesLong+0xea>
    24dd:	mov    %rbx,%r11
    24e0:	mov    -0x128(%rbp),%rbx
    24e7:	jmp    24b7 <ZSTD_decompressSequencesLong+0xd77>
```

## 04_zstd_decompress/no_retpoline/data_pgot: ZSTD_decompressSequences, 2601, memcpy

```asm
    25fd:	mov    %r13,%rdi
    2600:	call   2605 <ZSTD_decompressSequences+0x105>
			2601: R_X86_64_PLT32	memcpy-0x4
    2605:	lea    0x0(%r13,%rbx,1),%rax
    260a:	sub    -0xd0(%rbp),%rax
    2611:	mov    %rax,%r14
    2614:	mov    -0x30(%rbp),%rax
    2618:	sub    %gs:0x28,%rax
    2621:	jne    3015 <ZSTD_decompressSequences+0xb15>
    2627:	lea    -0x28(%rbp),%rsp
    262b:	mov    %r14,%rax
    262e:	pop    %rbx
    262f:	pop    %r12
    2631:	pop    %r13
    2633:	pop    %r14
    2635:	pop    %r15
    2637:	pop    %rbp
    2638:	ret    
    2639:	int3   
```

## 04_zstd_decompress/no_retpoline/data_pgot: ZSTD_decompressSequences, 2b82, memmove

```asm
    2b7a:	mov    %rdx,-0xc8(%rbp)
    2b81:	call   2b86 <ZSTD_decompressSequences+0x686>
			2b82: R_X86_64_PLT32	memmove-0x4
    2b86:	mov    -0xc8(%rbp),%rdx
    2b8d:	mov    -0x110(%rbp),%rcx
    2b94:	mov    %rax,%rdi
    2b97:	add    %rdx,%rdi
    2b9a:	add    %rcx,%r12
    2b9d:	cmp    %rdi,%r15
    2ba0:	jb     2bb3 <ZSTD_decompressSequences+0x6b3>
    2ba2:	mov    -0xf0(%rbp),%rcx
    2ba9:	cmp    $0x2,%r12
    2bad:	ja     2cee <ZSTD_decompressSequences+0x7ee>
    2bb3:	test   %r12,%r12
    2bb6:	je     2d8f <ZSTD_decompressSequences+0x88f>
    2bbc:	mov    -0xf0(%rbp),%rsi
    2bc3:	xor    %edx,%edx
    2bc5:	xor    %eax,%eax
    2bc7:	movzbl (%rsi,%rax,1),%ecx
```

## 04_zstd_decompress/no_retpoline/data_pgot: ZSTD_decompressSequences, 2e98, memmove

```asm
    2e94:	mov    %r12,%rdx
    2e97:	call   2e9c <ZSTD_decompressSequences+0x99c>
			2e98: R_X86_64_PLT32	memmove-0x4
    2e9c:	jmp    2d8f <ZSTD_decompressSequences+0x88f>
    2ea1:	mov    -0x58(%rbp),%rcx
    2ea5:	cmp    $0x1,%rcx
    2ea9:	adc    $0x0,%rcx
    2ead:	mov    %rcx,-0x108(%rbp)
    2eb4:	mov    %esi,%ebx
    2eb6:	mov    -0x118(%rbp),%rdi
    2ebd:	mov    %rdi,-0x58(%rbp)
    2ec1:	mov    -0x108(%rbp),%rdi
    2ec8:	mov    %rdi,-0x60(%rbp)
    2ecc:	jmp    299c <ZSTD_decompressSequences+0x49c>
    2ed1:	mov    -0xc8(%rbp),%rcx
    2ed8:	mov    -0xe0(%rbp),%rdx
    2edf:	add    $0x8,%rcx
    2ee3:	add    $0x8,%rdx
    2ee7:	mov    (%rcx),%rsi
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_generateNxBytes_data_pgot, 33e9, memset

```asm
    33e5:	mov    %rcx,%rbx
    33e8:	call   33ed <pgot_ZSTD_generateNxBytes_data_pgot+0x1d>
			33e9: R_X86_64_PLT32	memset-0x4
    33ed:	mov    %rbx,%rax
    33f0:	mov    -0x8(%rbp),%rbx
    33f4:	leave  
    33f5:	ret    
    33f6:	int3   
    33f7:	mov    $0xfffffffffffffff4,%rax
    33fe:	ret    
    33ff:	int3   

```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decompressContinue_data_pgot, 3963, memcpy

```asm
    395f:	xor    %r12d,%r12d
    3962:	call   3967 <pgot_ZSTD_decompressContinue_data_pgot+0x247>
			3963: R_X86_64_PLT32	memcpy-0x4
    3967:	mov    0x2612c(%rbx),%eax
    396d:	movl   $0x7,0x6084(%rbx)
    3977:	mov    %rax,0x6060(%rbx)
    397e:	jmp    381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    3983:	lea    0x26128(%rbx),%r13
    398a:	mov    %r8,%rdx
    398d:	mov    %rcx,%rsi
    3990:	lea    0x2612d(%rbx),%rdi
    3997:	call   399c <pgot_ZSTD_decompressContinue_data_pgot+0x27c>
			3998: R_X86_64_PLT32	memcpy-0x4
    399c:	mov    0x60e0(%rbx),%rdx
    39a3:	mov    %r13,%rsi
    39a6:	mov    %rbx,%rdi
    39a9:	call   10a0 <ZSTD_decodeFrameHeader>
    39ae:	mov    %rax,%r12
    39b1:	cmp    $0xffffffffffffffea,%rax
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decompressContinue_data_pgot, 3998, memcpy

```asm
    3990:	lea    0x2612d(%rbx),%rdi
    3997:	call   399c <pgot_ZSTD_decompressContinue_data_pgot+0x27c>
			3998: R_X86_64_PLT32	memcpy-0x4
    399c:	mov    0x60e0(%rbx),%rdx
    39a3:	mov    %r13,%rsi
    39a6:	mov    %rbx,%rdi
    39a9:	call   10a0 <ZSTD_decodeFrameHeader>
    39ae:	mov    %rax,%r12
    39b1:	cmp    $0xffffffffffffffea,%rax
    39b5:	ja     381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    39bb:	movq   $0x3,0x6060(%rbx)
    39c6:	xor    %r12d,%r12d
    39c9:	movl   $0x2,0x6084(%rbx)
    39d3:	jmp    381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    39d8:	mov    0x6080(%rbx),%eax
    39de:	cmp    $0x1,%eax
    39e1:	je     3a73 <pgot_ZSTD_decompressContinue_data_pgot+0x353>
    39e7:	cmp    $0x2,%eax
    39ea:	je     3b08 <pgot_ZSTD_decompressContinue_data_pgot+0x3e8>
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decompressContinue_data_pgot, 3a97, memset

```asm
    3a93:	mov    %r13,%rdi
    3a96:	call   3a9b <pgot_ZSTD_decompressContinue_data_pgot+0x37b>
			3a97: R_X86_64_PLT32	memset-0x4
    3a9b:	cmp    $0xffffffffffffffea,%r12
    3a9f:	ja     381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    3aa5:	mov    0x6078(%rbx),%edx
    3aab:	test   %edx,%edx
    3aad:	jne    3b28 <pgot_ZSTD_decompressContinue_data_pgot+0x408>
    3aaf:	cmpl   $0x4,0x6084(%rbx)
    3ab6:	je     3b88 <pgot_ZSTD_decompressContinue_data_pgot+0x468>
    3abc:	movl   $0x2,0x6084(%rbx)
    3ac6:	add    %r12,%r13
    3ac9:	movq   $0x3,0x6060(%rbx)
    3ad4:	mov    %r13,0x6040(%rbx)
    3adb:	jmp    381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    3ae0:	mov    $0xfffffffffffffff4,%r12
    3ae7:	cmp    %rdx,%r8
    3aea:	ja     381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    3af0:	mov    %r8,%rdx
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decompressContinue_data_pgot, 3afe, memcpy

```asm
    3af9:	mov    %r8,-0x30(%rbp)
    3afd:	call   3b02 <pgot_ZSTD_decompressContinue_data_pgot+0x3e2>
			3afe: R_X86_64_PLT32	memcpy-0x4
    3b02:	mov    -0x30(%rbp),%r12
    3b06:	jmp    3a9b <pgot_ZSTD_decompressContinue_data_pgot+0x37b>
    3b08:	cmp    $0x1ffff,%r8
    3b0f:	ja     393a <pgot_ZSTD_decompressContinue_data_pgot+0x21a>
    3b15:	mov    %r13,%rsi
    3b18:	mov    %rbx,%rdi
    3b1b:	call   3290 <ZSTD_decompressBlock_internal.part.0>
    3b20:	mov    %rax,%r12
    3b23:	jmp    3a9b <pgot_ZSTD_decompressContinue_data_pgot+0x37b>
    3b28:	lea    0x6090(%rbx),%rdi
    3b2f:	mov    %r12,%rdx
    3b32:	mov    %r13,%rsi
    3b35:	call   3b3a <pgot_ZSTD_decompressContinue_data_pgot+0x41a>
			3b36: R_X86_64_PLT32	xxh64_update-0x4
    3b3a:	cmpl   $0x4,0x6084(%rbx)
    3b41:	jne    3abc <pgot_ZSTD_decompressContinue_data_pgot+0x39c>
```

## 04_zstd_decompress/no_retpoline/data_pgot: ZSTD_decompressMultiFrame, 3dc8, memcpy

```asm
    3dc3:	mov    %r8,-0x58(%rbp)
    3dc7:	call   3dcc <ZSTD_decompressMultiFrame+0xec>
			3dc8: R_X86_64_PLT32	memcpy-0x4
    3dcc:	mov    -0x58(%rbp),%r8
    3dd0:	mov    %r8,%r15
    3dd3:	mov    0x6078(%r13),%ecx
    3dda:	test   %ecx,%ecx
    3ddc:	jne    3fd9 <ZSTD_decompressMultiFrame+0x2f9>
    3de2:	mov    -0x48(%rbp),%edx
    3de5:	sub    %r8,%r14
    3de8:	add    %r15,%rbx
    3deb:	lea    (%r12,%r8,1),%r11
    3def:	mov    %r14,%r9
    3df2:	test   %edx,%edx
    3df4:	jne    404b <ZSTD_decompressMultiFrame+0x36b>
    3dfa:	cmp    $0x2,%r14
    3dfe:	ja     3f12 <ZSTD_decompressMultiFrame+0x232>
    3e04:	mov    $0xfffffffffffffff3,%r15
    3e0b:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
```

## 04_zstd_decompress/no_retpoline/data_pgot: ZSTD_decompressMultiFrame, 4024, memset

```asm
    4020:	mov    %rbx,%rdi
    4023:	call   4028 <ZSTD_decompressMultiFrame+0x348>
			4024: R_X86_64_PLT32	memset-0x4
    4028:	mov    $0x1,%r8d
    402e:	jmp    3dd3 <ZSTD_decompressMultiFrame+0xf3>
    4033:	mov    $0xfffffffffffffff4,%r15
    403a:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
    403f:	mov    $0xfffffffffffffffe,%r15
    4046:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
    404b:	mov    0x6078(%r13),%eax
    4052:	mov    %rbx,%r15
    4055:	mov    -0x60(%rbp),%r14
    4059:	mov    %r9,%rbx
    405c:	test   %eax,%eax
    405e:	jne    407c <ZSTD_decompressMultiFrame+0x39c>
    4060:	mov    %r15,%r12
    4063:	sub    %r14,%r12
    4066:	cmp    $0xffffffffffffffea,%r12
    406a:	ja     3f8d <ZSTD_decompressMultiFrame+0x2ad>
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decompressStream_data_pgot, 4855, memcpy

```asm
    4850:	mov    %rcx,-0x40(%rbp)
    4854:	call   4859 <pgot_ZSTD_decompressStream_data_pgot+0xd9>
			4855: R_X86_64_PLT32	memcpy-0x4
    4859:	mov    -0x40(%rbp),%rcx
    485d:	mov    0x30(%rbx),%eax
    4860:	mov    %r15,0x98(%rbx)
    4867:	add    %rcx,%r12
    486a:	cmp    $0x2,%eax
    486d:	jne    47ef <pgot_ZSTD_decompressStream_data_pgot+0x6f>
    486f:	mov    (%rbx),%rdi
    4872:	mov    0x6060(%rdi),%r8
    4879:	test   %r8,%r8
    487c:	jne    4b3e <pgot_ZSTD_decompressStream_data_pgot+0x3be>
    4882:	movl   $0x0,0x30(%rbx)
    4889:	mov    -0x68(%rbp),%rax
    488d:	mov    -0x58(%rbp),%rsi
    4891:	sub    -0x50(%rbp),%r12
    4895:	sub    -0x60(%rbp),%r13
    4899:	add    %r12,0x10(%rsi)
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decompressStream_data_pgot, 4923, memcpy

```asm
    491e:	mov    %rdx,-0x40(%rbp)
    4922:	call   4927 <pgot_ZSTD_decompressStream_data_pgot+0x1a7>
			4923: R_X86_64_PLT32	memcpy-0x4
    4927:	mov    -0x40(%rbp),%rdx
    492b:	mov    -0x48(%rbp),%rcx
    492f:	add    %rdx,%r13
    4932:	add    0x68(%rbx),%rdx
    4936:	mov    %rdx,0x68(%rbx)
    493a:	cmp    %r15,%rcx
    493d:	jb     4889 <pgot_ZSTD_decompressStream_data_pgot+0x109>
    4943:	movl   $0x2,0x30(%rbx)
    494a:	add    0x78(%rbx),%rdx
    494e:	cmp    0x60(%rbx),%rdx
    4952:	jbe    47e3 <pgot_ZSTD_decompressStream_data_pgot+0x63>
    4958:	movq   $0x0,0x70(%rbx)
    4960:	movq   $0x0,0x68(%rbx)
    4968:	jmp    47e3 <pgot_ZSTD_decompressStream_data_pgot+0x63>
    496d:	movl   $0x1,0x30(%rbx)
    4974:	xor    %edx,%edx
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decompressStream_data_pgot, 49f1, memcpy

```asm
    49ed:	add    %r15,%r12
    49f0:	call   49f5 <pgot_ZSTD_decompressStream_data_pgot+0x275>
			49f1: R_X86_64_PLT32	memcpy-0x4
    49f5:	mov    -0x48(%rbp),%rcx
    49f9:	add    %r15,0x48(%rbx)
    49fd:	mov    -0x40(%rbp),%r8
    4a01:	cmp    %r15,%rcx
    4a04:	ja     4889 <pgot_ZSTD_decompressStream_data_pgot+0x109>
    4a0a:	mov    (%rbx),%rdi
    4a0d:	mov    0x68(%rbx),%rsi
    4a11:	mov    0x60(%rbx),%rdx
    4a15:	mov    0x38(%rbx),%rcx
    4a19:	mov    0x6084(%rdi),%eax
    4a1f:	sub    %rsi,%rdx
    4a22:	add    0x58(%rbx),%rsi
    4a26:	mov    %eax,-0x40(%rbp)
    4a29:	call   4a2e <pgot_ZSTD_decompressStream_data_pgot+0x2ae>
			4a2a: R_X86_64_PLT32	pgot_ZSTD_decompressContinue_data_pgot-0x4
    4a2e:	mov    %rax,%r15
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_ZSTD_decompressStream_data_pgot, 4cfe, memcpy

```asm
    4cf9:	mov    %rax,-0x38(%rbp)
    4cfd:	call   4d02 <pgot_ZSTD_decompressStream_data_pgot+0x582>
			4cfe: R_X86_64_PLT32	memcpy-0x4
    4d02:	mov    -0x58(%rbp),%rsi
    4d06:	mov    -0x30(%rbp),%rdx
    4d0a:	add    %rdx,0x98(%rbx)
    4d11:	mov    -0x38(%rbp),%r9
    4d15:	mov    $0x3,%edx
    4d1a:	mov    0x8(%rsi),%rax
    4d1e:	mov    %rax,0x10(%rsi)
    4d22:	mov    $0x6,%eax
    4d27:	sub    0x98(%rbx),%rdx
    4d2e:	cmp    %rax,%r9
    4d31:	cmovae %r9,%rax
    4d35:	lea    (%rdx,%rax,1),%r9
    4d39:	jmp    4c7d <pgot_ZSTD_decompressStream_data_pgot+0x4fd>
    4d3e:	mov    $0xfffffffffffffff9,%r9
    4d45:	jmp    4c7d <pgot_ZSTD_decompressStream_data_pgot+0x4fd>
    4d4a:	mov    -0x58(%rbp),%rsi
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_FSE_readNCount_data_pgot, 279, memset

```asm
 274:	lea    (%rax,%r8,2),%rdi
 278:	call   27d <pgot_FSE_readNCount_data_pgot+0x21d>
			279: R_X86_64_PLT32	memset-0x4
 27d:	mov    -0x4c(%rbp),%r8d
 281:	mov    -0x58(%rbp),%ecx
 284:	mov    %r13d,%eax
 287:	sar    $0x3,%eax
 28a:	cltq   
 28c:	add    %r12,%rax
 28f:	cmp    -0x40(%rbp),%r12
 293:	jbe    2a2 <pgot_FSE_readNCount_data_pgot+0x242>
 295:	shr    $0x2,%ecx
 298:	cmp    -0x48(%rbp),%rax
 29c:	ja     195 <pgot_FSE_readNCount_data_pgot+0x135>
 2a2:	mov    (%rax),%esi
 2a4:	and    $0x7,%r13d
 2a8:	mov    %rax,%r12
 2ab:	mov    %r13d,%ecx
 2ae:	shr    %cl,%esi
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_HUF_selectDecoder_data_pgot, 4126, pgot_algoTime_data_pgot

```asm
    411f:	lea    (%rax,%rax,2),%rdx
    4123:	mov    0x0(%rip),%rax        # 412a <pgot_HUF_selectDecoder_data_pgot+0x2a>
			4126: R_X86_64_PC32	pgot_algoTime_data_pgot-0x4
    412a:	lea    (%rax,%rdx,8),%rdx
    412e:	mov    0xc(%rdx),%eax
    4131:	imul   %ecx,%eax
    4134:	add    0x8(%rdx),%eax
    4137:	mov    %eax,%esi
    4139:	imul   0x4(%rdx),%ecx
    413d:	add    (%rdx),%ecx
    413f:	shr    $0x3,%esi
    4142:	add    %esi,%eax
    4144:	cmp    %eax,%ecx
    4146:	seta   %al
    4149:	movzbl %al,%eax
    414c:	ret    
    414d:	int3   
    414e:	xchg   %ax,%ax

```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_HUF_decompress4X_DCtx_wksp_data_pgot, 41a1, pgot_algoTime_data_pgot

```asm
    419a:	lea    (%rax,%rax,2),%rdx
    419e:	mov    0x0(%rip),%rax        # 41a5 <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0x55>
			41a1: R_X86_64_PC32	pgot_algoTime_data_pgot-0x4
    41a5:	lea    (%rax,%rdx,8),%rdx
    41a9:	mov    0xc(%rdx),%eax
    41ac:	imul   %esi,%eax
    41af:	add    0x8(%rdx),%eax
    41b2:	mov    %eax,%r11d
    41b5:	imul   0x4(%rdx),%esi
    41b9:	add    (%rdx),%esi
    41bb:	shr    $0x3,%r11d
    41bf:	add    %r11d,%eax
    41c2:	cmp    %eax,%esi
    41c4:	jbe    41de <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0x8e>
    41c6:	push   0x10(%rbp)
    41c9:	mov    %r12,%rdx
    41cc:	mov    %r10,%rsi
    41cf:	call   41d4 <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0x84>
			41d0: R_X86_64_PLT32	pgot_HUF_decompress4X4_DCtx_wksp_data_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_HUF_decompress4X_DCtx_wksp_data_pgot, 41fb, memcpy

```asm
    41f7:	mov    %r10,%rdi
    41fa:	call   41ff <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0xaf>
			41fb: R_X86_64_PLT32	memcpy-0x4
    41ff:	mov    %r12,%rax
    4202:	mov    -0x8(%rbp),%r12
    4206:	leave  
    4207:	ret    
    4208:	int3   
    4209:	movzbl (%rcx),%esi
    420c:	mov    %r10,%rdi
    420f:	call   4214 <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0xc4>
			4210: R_X86_64_PLT32	memset-0x4
    4214:	mov    %r12,%rax
    4217:	mov    -0x8(%rbp),%r12
    421b:	leave  
    421c:	ret    
    421d:	int3   
    421e:	xchg   %ax,%ax

```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_HUF_decompress4X_DCtx_wksp_data_pgot, 4210, memset

```asm
    420c:	mov    %r10,%rdi
    420f:	call   4214 <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0xc4>
			4210: R_X86_64_PLT32	memset-0x4
    4214:	mov    %r12,%rax
    4217:	mov    -0x8(%rbp),%r12
    421b:	leave  
    421c:	ret    
    421d:	int3   
    421e:	xchg   %ax,%ax

```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_HUF_decompress4X_hufOnly_wksp_data_pgot, 4264, pgot_algoTime_data_pgot

```asm
    425d:	lea    (%rax,%rax,2),%rdx
    4261:	mov    0x0(%rip),%rax        # 4268 <pgot_HUF_decompress4X_hufOnly_wksp_data_pgot+0x48>
			4264: R_X86_64_PC32	pgot_algoTime_data_pgot-0x4
    4268:	lea    (%rax,%rdx,8),%rdx
    426c:	mov    0xc(%rdx),%eax
    426f:	imul   %r11d,%eax
    4273:	add    0x8(%rdx),%eax
    4276:	mov    %eax,%ebx
    4278:	imul   0x4(%rdx),%r11d
    427d:	add    (%rdx),%r11d
    4280:	shr    $0x3,%ebx
    4283:	add    %ebx,%eax
    4285:	cmp    %eax,%r11d
    4288:	ja     429d <pgot_HUF_decompress4X_hufOnly_wksp_data_pgot+0x7d>
    428a:	push   0x10(%rbp)
    428d:	mov    %r10,%rdx
    4290:	call   4295 <pgot_HUF_decompress4X_hufOnly_wksp_data_pgot+0x75>
			4291: R_X86_64_PLT32	pgot_HUF_decompress4X2_DCtx_wksp_data_pgot-0x4
    4295:	mov    -0x8(%rbp),%rbx
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_HUF_decompress1X_DCtx_wksp_data_pgot, 4338, pgot_algoTime_data_pgot

```asm
    4331:	lea    (%rax,%rax,2),%rdx
    4335:	mov    0x0(%rip),%rax        # 433c <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0x7c>
			4338: R_X86_64_PC32	pgot_algoTime_data_pgot-0x4
    433c:	lea    (%rax,%rdx,8),%rdx
    4340:	mov    0xc(%rdx),%eax
    4343:	imul   %edi,%eax
    4346:	add    0x8(%rdx),%eax
    4349:	mov    %eax,%r8d
    434c:	imul   0x4(%rdx),%edi
    4350:	add    (%rdx),%edi
    4352:	mov    %r15,%rdx
    4355:	shr    $0x3,%r8d
    4359:	add    %r8d,%eax
    435c:	mov    0x10(%rbp),%r8
    4360:	cmp    %eax,%edi
    4362:	mov    %rbx,%rdi
    4365:	jbe    43b6 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xf6>
    4367:	call   436c <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xac>
			4368: R_X86_64_PLT32	pgot_HUF_readDTableX4_wksp_data_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_HUF_decompress1X_DCtx_wksp_data_pgot, 43f7, memcpy

```asm
    43f3:	mov    %r12,%r13
    43f6:	call   43fb <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0x13b>
			43f7: R_X86_64_PLT32	memcpy-0x4
    43fb:	jmp    43a3 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xe3>
    43fd:	movzbl (%rcx),%esi
    4400:	mov    %r14,%rdi
    4403:	mov    %r12,%r13
    4406:	call   440b <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0x14b>
			4407: R_X86_64_PLT32	memset-0x4
    440b:	jmp    43a3 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xe3>
    440d:	mov    $0xfffffffffffffff3,%r13
    4414:	jmp    43a3 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xe3>

Disassembly of section .text.unlikely:

```

## 04_zstd_decompress/no_retpoline/data_pgot: pgot_HUF_decompress1X_DCtx_wksp_data_pgot, 4407, memset

```asm
    4403:	mov    %r12,%r13
    4406:	call   440b <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0x14b>
			4407: R_X86_64_PLT32	memset-0x4
    440b:	jmp    43a3 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xe3>
    440d:	mov    $0xfffffffffffffff3,%r13
    4414:	jmp    43a3 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xe3>

Disassembly of section .text.unlikely:

```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_execSequenceLast7_func_pgot.isra.0, 5d3, pgot_memmove_table_func_pgot

```asm
     5cc:	mov    0x18(%rbp),%r14
     5d0:	mov    0x0(%rip),%rcx        # 5d7 <pgot_ZSTD_execSequenceLast7_func_pgot.isra.0+0xd7>
			5d3: R_X86_64_PC32	pgot_memmove_table_func_pgot-0x4
     5d7:	sub    %rsi,%r14
     5da:	mov    0x28(%rbp),%rsi
     5de:	sub    %r14,%rsi
     5e1:	lea    (%rsi,%r10,1),%rax
     5e5:	cmp    %rax,0x28(%rbp)
     5e9:	jae    670 <pgot_ZSTD_execSequenceLast7_func_pgot.isra.0+0x170>
     5ef:	mov    %r14,%rdx
     5f2:	mov    %r12,%rdi
     5f5:	call   *%rcx
     5f7:	mov    0x18(%rbp),%rsi
     5fb:	lea    (%r12,%r14,1),%rax
     5ff:	cmp    %rax,%rbx
     602:	jbe    62d <pgot_ZSTD_execSequenceLast7_func_pgot.isra.0+0x12d>
     604:	sub    %rax,%rbx
     607:	xor    %edx,%edx
     609:	movzbl (%rsi,%rdx,1),%ecx
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decompressBegin_func_pgot, b39, pgot_memcpy_table_func_pgot

```asm
     b35:	push   %rbp
     b36:	mov    0x0(%rip),%rax        # b3d <pgot_ZSTD_decompressBegin_func_pgot+0xd>
			b39: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     b3d:	mov    $0xc,%edx
     b42:	mov    $0x0,%rsi
			b45: R_X86_64_32S	.rodata+0x700
     b49:	mov    %rsp,%rbp
     b4c:	push   %rbx
     b4d:	mov    %rdi,%rbx
     b50:	lea    0x6030(%rdi),%rdi
     b57:	movq   $0x5,0x30(%rdi)
     b5f:	movq   $0x0,0x10(%rdi)
     b67:	movq   $0x0,0x18(%rdi)
     b6f:	movq   $0x0,0x20(%rdi)
     b77:	movq   $0x0,0x28(%rdi)
     b7f:	movl   $0xc00000c,-0x4c04(%rdi)
     b89:	movl   $0x0,0x54(%rdi)
     b90:	movq   $0x0,0x58(%rdi)
     b98:	movl   $0x0,0xb8(%rdi)
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_createDCtx_advanced_func_pgot, d17, pgot_memcpy_table_func_pgot

```asm
     d0f:	mov    $0x18,%edx
     d14:	mov    0x0(%rip),%rax        # d1b <pgot_ZSTD_createDCtx_advanced_func_pgot+0x4b>
			d17: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     d1b:	lea    0x10(%rbp),%rsi
     d1f:	call   *%rax
     d21:	mov    %r12,%rdi
     d24:	call   d29 <pgot_ZSTD_createDCtx_advanced_func_pgot+0x59>
			d25: R_X86_64_PLT32	pgot_ZSTD_decompressBegin_func_pgot-0x4
     d29:	mov    %r12,%rax
     d2c:	mov    -0x8(%rbp),%r12
     d30:	leave  
     d31:	ret    
     d32:	int3   
     d33:	xor    %r12d,%r12d
     d36:	mov    %r12,%rax
     d39:	mov    -0x8(%rbp),%r12
     d3d:	leave  
     d3e:	ret    
     d3f:	int3   
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_copyDCtx_func_pgot, dd9, pgot_memcpy_table_func_pgot

```asm
     dd5:	push   %rbp
     dd6:	mov    0x0(%rip),%rax        # ddd <pgot_ZSTD_copyDCtx_func_pgot+0xd>
			dd9: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     ddd:	mov    $0x6126,%edx
     de2:	mov    %rsp,%rbp
     de5:	call   *%rax
     de7:	pop    %rbp
     de8:	ret    
     de9:	int3   
     dea:	nopw   0x0(%rax,%rax,1)

```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_getFrameParams_func_pgot, e85, pgot_memset_table_func_pgot

```asm
     e80:	jbe    ea5 <pgot_ZSTD_getFrameParams_func_pgot+0x75>
     e82:	mov    0x0(%rip),%rax        # e89 <pgot_ZSTD_getFrameParams_func_pgot+0x59>
			e85: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
     e89:	mov    $0x18,%edx
     e8e:	xor    %esi,%esi
     e90:	call   *%rax
     e92:	mov    0x4(%r12),%eax
     e97:	movl   $0x0,0x8(%r13)
     e9f:	mov    %rax,0x0(%r13)
     ea3:	xor    %eax,%eax
     ea5:	add    $0x18,%rsp
     ea9:	pop    %rbx
     eaa:	pop    %r12
     eac:	pop    %r13
     eae:	pop    %r14
     eb0:	pop    %r15
     eb2:	pop    %rbp
     eb3:	ret    
     eb4:	int3   
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decodeLiteralsBlock_func_pgot, 1279, pgot_memcpy_table_func_pgot

```asm
    1273:	mov    %rbx,%rdx
    1276:	mov    0x0(%rip),%rax        # 127d <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x9d>
			1279: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    127d:	mov    %r14,%rdi
    1280:	call   *%rax
    1282:	mov    %r14,0x60f0(%r12)
    128a:	lea    (%r14,%rbx,1),%rdi
    128e:	xor    %esi,%esi
    1290:	mov    %rbx,0x6110(%r12)
    1298:	mov    $0x8,%edx
    129d:	mov    0x0(%rip),%rax        # 12a4 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xc4>
			12a0: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    12a4:	call   *%rax
    12a6:	jmp    12fb <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x11b>
    12a8:	mov    0x6088(%rdi),%esi
    12ae:	mov    $0xffffffffffffffed,%r13
    12b5:	test   %esi,%esi
    12b7:	je     12fb <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x11b>
    12b9:	cmp    $0x4,%rdx
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decodeLiteralsBlock_func_pgot, 12a0, pgot_memset_table_func_pgot

```asm
    1298:	mov    $0x8,%edx
    129d:	mov    0x0(%rip),%rax        # 12a4 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xc4>
			12a0: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    12a4:	call   *%rax
    12a6:	jmp    12fb <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x11b>
    12a8:	mov    0x6088(%rdi),%esi
    12ae:	mov    $0xffffffffffffffed,%r13
    12b5:	test   %esi,%esi
    12b7:	je     12fb <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x11b>
    12b9:	cmp    $0x4,%rdx
    12bd:	jbe    12f4 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x114>
    12bf:	mov    (%r9),%r8d
    12c2:	shr    $0x2,%al
    12c5:	and    $0x3,%eax
    12c8:	mov    %r8d,%ecx
    12cb:	shr    $0x4,%ecx
    12ce:	cmp    $0x2,%al
    12d0:	je     13ce <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x1ee>
    12d6:	cmp    $0x3,%al
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decodeLiteralsBlock_func_pgot, 13c3, pgot_memset_table_func_pgot

```asm
    13be:	xor    %esi,%esi
    13c0:	mov    0x0(%rip),%rax        # 13c7 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x1e7>
			13c3: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    13c7:	call   *%rax
    13c9:	jmp    12fb <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x11b>
    13ce:	mov    %ecx,%r14d
    13d1:	shr    $0x12,%r8d
    13d5:	xor    %eax,%eax
    13d7:	mov    $0x4,%esi
    13dc:	and    $0x3fff,%r14d
    13e3:	mov    %r8d,%ecx
    13e6:	jmp    1330 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x150>
    13eb:	movzwl (%rsi),%ebx
    13ee:	mov    $0x2,%esi
    13f3:	shr    $0x4,%bx
    13f7:	movzwl %bx,%ebx
    13fa:	jmp    124e <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x6e>
    13ff:	mov    %eax,%ecx
    1401:	shr    $0x2,%cl
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decodeLiteralsBlock_func_pgot, 143a, pgot_memset_table_func_pgot

```asm
    1433:	lea    0x8(%rbx),%rdx
    1437:	mov    0x0(%rip),%rax        # 143e <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x25e>
			143a: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    143e:	mov    %r14,%rdi
    1441:	call   *%rax
    1443:	mov    %r14,0x60f0(%r12)
    144b:	mov    %rbx,0x6110(%r12)
    1453:	jmp    12fb <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x11b>
    1458:	add    %r9,%rsi
    145b:	mov    %rbx,0x6110(%r12)
    1463:	mov    %rsi,0x60f0(%r12)
    146b:	jmp    12fb <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x11b>
    1470:	movzbl 0x2(%rsi),%ebx
    1474:	movzwl (%rsi),%eax
    1477:	mov    $0x3,%esi
    147c:	shl    $0x10,%ebx
    147f:	add    %eax,%ebx
    1481:	shr    $0x4,%ebx
    1484:	jmp    124e <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x6e>
```

## 04_zstd_decompress/no_retpoline/func_pgot: ZSTD_decompressSequencesLong, 1871, pgot_memcpy_table_func_pgot

```asm
    186b:	mov    %r13,%rsi
    186e:	mov    0x0(%rip),%rax        # 1875 <ZSTD_decompressSequencesLong+0x125>
			1871: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    1875:	call   *%rax
    1877:	mov    -0x120(%rbp),%r11
    187e:	add    %r11,%rbx
    1881:	sub    -0x118(%rbp),%rbx
    1888:	mov    %rbx,%r12
    188b:	mov    -0x38(%rbp),%rax
    188f:	sub    %gs:0x28,%rax
    1898:	jne    2548 <ZSTD_decompressSequencesLong+0xdf8>
    189e:	lea    -0x30(%rbp),%rsp
    18a2:	mov    %r12,%rax
    18a5:	pop    %rbx
    18a6:	pop    %r10
    18a8:	pop    %r12
    18aa:	pop    %r13
    18ac:	pop    %r14
    18ae:	pop    %r15
```

## 04_zstd_decompress/no_retpoline/func_pgot: ZSTD_decompressSequencesLong, 1d49, pgot_memmove_table_func_pgot

```asm
    1d40:	jb     191f <ZSTD_decompressSequencesLong+0x1cf>
    1d46:	mov    0x0(%rip),%rax        # 1d4d <ZSTD_decompressSequencesLong+0x5fd>
			1d49: R_X86_64_PC32	pgot_memmove_table_func_pgot-0x4
    1d4d:	lea    (%rsi,%rcx,1),%rdx
    1d51:	cmp    %rdx,-0x130(%rbp)
    1d58:	jae    252d <ZSTD_decompressSequencesLong+0xddd>
    1d5e:	mov    -0x130(%rbp),%rdx
    1d65:	mov    %r9,-0x178(%rbp)
    1d6c:	mov    %r14,%rdi
    1d6f:	mov    %rcx,-0x160(%rbp)
    1d76:	sub    %rsi,%rdx
    1d79:	mov    %r8,-0x168(%rbp)
    1d80:	mov    %rdx,-0x128(%rbp)
    1d87:	call   *%rax
    1d89:	mov    -0x128(%rbp),%rdx
    1d90:	mov    -0x160(%rbp),%rcx
    1d97:	mov    -0x178(%rbp),%r9
    1d9e:	sub    %rdx,%rcx
    1da1:	add    %rdx,%r14
```

## 04_zstd_decompress/no_retpoline/func_pgot: ZSTD_decompressSequencesLong, 1e20, pgot_memcpy_table_func_pgot

```asm
    1e1a:	add    %rax,%rsi
    1e1d:	mov    0x0(%rip),%rax        # 1e24 <ZSTD_decompressSequencesLong+0x6d4>
			1e20: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    1e24:	mov    %rsi,-0x160(%rbp)
    1e2b:	call   *%rax
    1e2d:	movslq -0x128(%rbp),%rax
    1e34:	mov    -0x160(%rbp),%rsi
    1e3b:	mov    -0x168(%rbp),%rcx
    1e42:	mov    -0x178(%rbp),%r9
    1e49:	sub    %rax,%rsi
    1e4c:	lea    0x8(%r14),%rax
    1e50:	add    $0x8,%rsi
    1e54:	cmp    -0x150(%rbp),%rbx
    1e5b:	jbe    24b8 <ZSTD_decompressSequencesLong+0xd68>
    1e61:	cmp    -0x138(%rbp),%rax
    1e68:	jb     24d4 <ZSTD_decompressSequencesLong+0xd84>
    1e6e:	cmp    %rax,%rbx
    1e71:	jbe    1e88 <ZSTD_decompressSequencesLong+0x738>
    1e73:	sub    %rax,%rbx
```

## 04_zstd_decompress/no_retpoline/func_pgot: ZSTD_decompressSequencesLong, 2040, pgot_memmove_table_func_pgot

```asm
    2037:	jb     191f <ZSTD_decompressSequencesLong+0x1cf>
    203d:	mov    0x0(%rip),%rax        # 2044 <ZSTD_decompressSequencesLong+0x8f4>
			2040: R_X86_64_PC32	pgot_memmove_table_func_pgot-0x4
    2044:	lea    (%rsi,%rcx,1),%rdx
    2048:	cmp    %rdx,-0x130(%rbp)
    204f:	jae    241d <ZSTD_decompressSequencesLong+0xccd>
    2055:	mov    -0x130(%rbp),%rdx
    205c:	mov    %r10d,-0x180(%rbp)
    2063:	mov    %r14,%rdi
    2066:	mov    %rcx,-0x178(%rbp)
    206d:	sub    %rsi,%rdx
    2070:	mov    %r9,-0x160(%rbp)
    2077:	mov    %rdx,-0x158(%rbp)
    207e:	mov    %r8,-0x188(%rbp)
    2085:	call   *%rax
    2087:	mov    -0x158(%rbp),%rdx
    208e:	mov    -0x178(%rbp),%rcx
    2095:	mov    -0x160(%rbp),%r9
    209c:	mov    -0x180(%rbp),%r10d
```

## 04_zstd_decompress/no_retpoline/func_pgot: ZSTD_decompressSequencesLong, 22d5, pgot_memcpy_table_func_pgot

```asm
    22cf:	add    %rax,%rsi
    22d2:	mov    0x0(%rip),%rax        # 22d9 <ZSTD_decompressSequencesLong+0xb89>
			22d5: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    22d9:	mov    %rsi,-0x160(%rbp)
    22e0:	call   *%rax
    22e2:	movslq -0x158(%rbp),%rax
    22e9:	mov    -0x160(%rbp),%rsi
    22f0:	mov    -0x178(%rbp),%r9
    22f7:	mov    -0x180(%rbp),%rcx
    22fe:	mov    -0x188(%rbp),%r10d
    2305:	sub    %rax,%rsi
    2308:	jmp    215e <ZSTD_decompressSequencesLong+0xa0e>
    230d:	push   -0x130(%rbp)
    2313:	mov    %rdi,%rsi
    2316:	lea    -0xe0(%rbp),%r9
    231d:	mov    %rax,%rdx
    2320:	push   -0x148(%rbp)
    2326:	mov    %r15,%rdi
    2329:	push   -0x128(%rbp)
```

## 04_zstd_decompress/no_retpoline/func_pgot: ZSTD_decompressSequences, 26b2, pgot_memcpy_table_func_pgot

```asm
    26ad:	jb     26d1 <ZSTD_decompressSequences+0x131>
    26af:	mov    0x0(%rip),%rax        # 26b6 <ZSTD_decompressSequences+0x116>
			26b2: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    26b6:	mov    %rbx,%rdx
    26b9:	mov    %r9,%rsi
    26bc:	mov    %r15,%rdi
    26bf:	call   *%rax
    26c1:	mov    %r15,%rax
    26c4:	add    %rbx,%rax
    26c7:	sub    -0xc8(%rbp),%rax
    26ce:	mov    %rax,%r14
    26d1:	mov    -0x30(%rbp),%rax
    26d5:	sub    %gs:0x28,%rax
    26de:	jne    314b <ZSTD_decompressSequences+0xbab>
    26e4:	lea    -0x28(%rbp),%rsp
    26e8:	mov    %r14,%rax
    26eb:	pop    %rbx
    26ec:	pop    %r12
    26ee:	pop    %r13
```

## 04_zstd_decompress/no_retpoline/func_pgot: ZSTD_decompressSequences, 2c36, pgot_memmove_table_func_pgot

```asm
    2c2c:	sub    -0xe8(%rbp),%rbx
    2c33:	mov    0x0(%rip),%rax        # 2c3a <ZSTD_decompressSequences+0x69a>
			2c36: R_X86_64_PC32	pgot_memmove_table_func_pgot-0x4
    2c3a:	lea    (%rdi,%rbx,1),%rsi
    2c3e:	lea    (%rsi,%r12,1),%rdx
    2c42:	cmp    %rdx,%rdi
    2c45:	jae    2fc3 <ZSTD_decompressSequences+0xa23>
    2c4b:	mov    %rbx,%rdx
    2c4e:	mov    %rcx,-0x110(%rbp)
    2c55:	mov    %r15,%rdi
    2c58:	add    %rbx,%r12
    2c5b:	neg    %rdx
    2c5e:	mov    %r8,-0x118(%rbp)
    2c65:	mov    %rdx,-0x108(%rbp)
    2c6c:	call   *%rax
    2c6e:	mov    -0x108(%rbp),%rdx
    2c75:	mov    -0x110(%rbp),%rcx
    2c7c:	add    %rdx,%r15
    2c7f:	cmp    $0x2,%r12
```

## 04_zstd_decompress/no_retpoline/func_pgot: ZSTD_decompressSequences, 2f56, pgot_memcpy_table_func_pgot

```asm
    2f50:	add    %rax,%rsi
    2f53:	mov    0x0(%rip),%rax        # 2f5a <ZSTD_decompressSequences+0x9ba>
			2f56: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2f5a:	mov    %rsi,-0x100(%rbp)
    2f61:	call   *%rax
    2f63:	mov    -0x100(%rbp),%rsi
    2f6a:	mov    -0x108(%rbp),%r8
    2f71:	mov    -0x110(%rbp),%rcx
    2f78:	sub    %rbx,%rsi
    2f7b:	jmp    2df2 <ZSTD_decompressSequences+0x852>
    2f80:	mov    %rcx,%rdi
    2f83:	mov    %rcx,%rax
    2f86:	sub    %r10,%rdi
    2f89:	mov    %edi,%edx
    2f8b:	mov    %edi,%edi
    2f8d:	sub    %rdi,%rax
    2f90:	jmp    28ff <ZSTD_decompressSequences+0x35f>
    2f95:	mov    %rcx,%r8
    2f98:	sub    %rdi,%r8
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_generateNxBytes_func_pgot, 3521, pgot_memset_table_func_pgot

```asm
    351b:	movzbl %dl,%esi
    351e:	mov    0x0(%rip),%rax        # 3525 <pgot_ZSTD_generateNxBytes_func_pgot+0x15>
			3521: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    3525:	mov    %rcx,%rdx
    3528:	mov    %rsp,%rbp
    352b:	push   %rbx
    352c:	mov    %rcx,%rbx
    352f:	call   *%rax
    3531:	mov    %rbx,%rax
    3534:	mov    -0x8(%rbp),%rbx
    3538:	leave  
    3539:	ret    
    353a:	int3   
    353b:	mov    $0xfffffffffffffff4,%rax
    3542:	ret    
    3543:	int3   
    3544:	data16 cs nopw 0x0(%rax,%rax,1)
    354f:	nop

```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3a67, pgot_memcpy_table_func_pgot

```asm
    3a61:	mov    %rcx,%rsi
    3a64:	mov    0x0(%rip),%rax        # 3a6b <pgot_ZSTD_decompressContinue_func_pgot+0x1fb>
			3a67: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3a6b:	mov    $0x5,%edx
    3a70:	mov    %r12,%rdi
    3a73:	call   *%rax
    3a75:	mov    0x60e0(%rbx),%rax
    3a7c:	mov    -0x30(%rbp),%rcx
    3a80:	cmp    $0x5,%rax
    3a84:	ja     3ce3 <pgot_ZSTD_decompressContinue_func_pgot+0x473>
    3a8a:	movq   $0x0,0x6060(%rbx)
    3a95:	xor    %r8d,%r8d
    3a98:	jmp    3aee <pgot_ZSTD_decompressContinue_func_pgot+0x27e>
    3a9a:	mov    $0xfffffffffffffff3,%r12
    3aa1:	jmp    396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3aa6:	mov    $0xffffffffffffffff,%r12
    3aad:	jmp    396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3ab2:	mov    0x0(%rip),%rax        # 3ab9 <pgot_ZSTD_decompressContinue_func_pgot+0x249>
			3ab5: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3ab5, pgot_memcpy_table_func_pgot

```asm
    3aad:	jmp    396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3ab2:	mov    0x0(%rip),%rax        # 3ab9 <pgot_ZSTD_decompressContinue_func_pgot+0x249>
			3ab5: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3ab9:	mov    %r8,%rdx
    3abc:	mov    %rcx,%rsi
    3abf:	xor    %r12d,%r12d
    3ac2:	lea    0x2612d(%rbx),%rdi
    3ac9:	call   *%rax
    3acb:	mov    0x2612c(%rbx),%eax
    3ad1:	movl   $0x7,0x6084(%rbx)
    3adb:	mov    %rax,0x6060(%rbx)
    3ae2:	jmp    396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3ae7:	lea    0x26128(%rbx),%r12
    3aee:	mov    %r8,%rdx
    3af1:	mov    %rcx,%rsi
    3af4:	lea    0x2612d(%rbx),%rdi
    3afb:	mov    0x0(%rip),%rax        # 3b02 <pgot_ZSTD_decompressContinue_func_pgot+0x292>
			3afe: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3b02:	call   *%rax
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3afe, pgot_memcpy_table_func_pgot

```asm
    3af4:	lea    0x2612d(%rbx),%rdi
    3afb:	mov    0x0(%rip),%rax        # 3b02 <pgot_ZSTD_decompressContinue_func_pgot+0x292>
			3afe: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3b02:	call   *%rax
    3b04:	mov    0x60e0(%rbx),%rdx
    3b0b:	mov    %r12,%rsi
    3b0e:	mov    %rbx,%rdi
    3b11:	call   1090 <ZSTD_decodeFrameHeader>
    3b16:	mov    %rax,%r12
    3b19:	cmp    $0xffffffffffffffea,%rax
    3b1d:	ja     396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3b23:	movq   $0x3,0x6060(%rbx)
    3b2e:	xor    %r12d,%r12d
    3b31:	movl   $0x2,0x6084(%rbx)
    3b3b:	jmp    396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3b40:	mov    0x6080(%rbx),%eax
    3b46:	cmp    $0x1,%eax
    3b49:	je     3be3 <pgot_ZSTD_decompressContinue_func_pgot+0x373>
    3b4f:	cmp    $0x2,%eax
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3b6f, pgot_memcpy_table_func_pgot

```asm
    3b67:	jmp    396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3b6c:	mov    0x0(%rip),%rax        # 3b73 <pgot_ZSTD_decompressContinue_func_pgot+0x303>
			3b6f: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3b73:	lea    0x26128(%rbx),%rdi
    3b7a:	mov    %rcx,%rsi
    3b7d:	xor    %r12d,%r12d
    3b80:	mov    $0x5,%edx
    3b85:	call   *%rax
    3b87:	movq   $0x3,0x6060(%rbx)
    3b92:	movl   $0x6,0x6084(%rbx)
    3b9c:	jmp    396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3ba1:	movq   $0x3,0x6060(%rbx)
    3bac:	xor    %r12d,%r12d
    3baf:	jmp    396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3bb4:	movq   $0x1,0x6060(%rbx)
    3bbf:	mov    %edx,%eax
    3bc1:	movl   $0x1,0x6080(%rbx)
    3bcb:	mov    %rax,0x6118(%rbx)
    3bd2:	add    $0x3,%ecx
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3c03, pgot_memset_table_func_pgot

```asm
    3bfd:	movzbl (%rcx),%esi
    3c00:	mov    0x0(%rip),%rax        # 3c07 <pgot_ZSTD_decompressContinue_func_pgot+0x397>
			3c03: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    3c07:	mov    %r12,%rdx
    3c0a:	mov    %r13,%rdi
    3c0d:	call   *%rax
    3c0f:	cmp    $0xffffffffffffffea,%r12
    3c13:	ja     396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3c19:	mov    0x6078(%rbx),%edx
    3c1f:	test   %edx,%edx
    3c21:	jne    3ca0 <pgot_ZSTD_decompressContinue_func_pgot+0x430>
    3c23:	cmpl   $0x4,0x6084(%rbx)
    3c2a:	je     3d00 <pgot_ZSTD_decompressContinue_func_pgot+0x490>
    3c30:	movl   $0x2,0x6084(%rbx)
    3c3a:	add    %r12,%r13
    3c3d:	movq   $0x3,0x6060(%rbx)
    3c48:	mov    %r13,0x6040(%rbx)
    3c4f:	jmp    396f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3c54:	mov    $0xfffffffffffffff4,%r12
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3c74, pgot_memcpy_table_func_pgot

```asm
    3c6e:	mov    %r13,%rdi
    3c71:	mov    0x0(%rip),%rax        # 3c78 <pgot_ZSTD_decompressContinue_func_pgot+0x408>
			3c74: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3c78:	call   *%rax
    3c7a:	mov    -0x30(%rbp),%r12
    3c7e:	jmp    3c0f <pgot_ZSTD_decompressContinue_func_pgot+0x39f>
    3c80:	cmp    $0x1ffff,%r8
    3c87:	ja     3a9a <pgot_ZSTD_decompressContinue_func_pgot+0x22a>
    3c8d:	mov    %r13,%rsi
    3c90:	mov    %rbx,%rdi
    3c93:	call   33d0 <ZSTD_decompressBlock_internal.part.0>
    3c98:	mov    %rax,%r12
    3c9b:	jmp    3c0f <pgot_ZSTD_decompressContinue_func_pgot+0x39f>
    3ca0:	lea    0x6090(%rbx),%rdi
    3ca7:	mov    %r12,%rdx
    3caa:	mov    %r13,%rsi
    3cad:	call   3cb2 <pgot_ZSTD_decompressContinue_func_pgot+0x442>
			3cae: R_X86_64_PLT32	xxh64_update-0x4
    3cb2:	cmpl   $0x4,0x6084(%rbx)
```

## 04_zstd_decompress/no_retpoline/func_pgot: ZSTD_decompressMultiFrame, 3f3a, pgot_memcpy_table_func_pgot

```asm
    3f34:	mov    %rbx,%rdi
    3f37:	mov    0x0(%rip),%rax        # 3f3e <ZSTD_decompressMultiFrame+0xee>
			3f3a: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3f3e:	call   *%rax
    3f40:	mov    -0x58(%rbp),%r8
    3f44:	mov    %r8,%r15
    3f47:	mov    0x6078(%r13),%ecx
    3f4e:	test   %ecx,%ecx
    3f50:	jne    414d <ZSTD_decompressMultiFrame+0x2fd>
    3f56:	mov    -0x48(%rbp),%edx
    3f59:	sub    %r8,%r14
    3f5c:	add    %r15,%rbx
    3f5f:	lea    (%r12,%r8,1),%r11
    3f63:	mov    %r14,%r9
    3f66:	test   %edx,%edx
    3f68:	jne    41c3 <ZSTD_decompressMultiFrame+0x373>
    3f6e:	cmp    $0x2,%r14
    3f72:	ja     4086 <ZSTD_decompressMultiFrame+0x236>
    3f78:	mov    $0xfffffffffffffff3,%r15
```

## 04_zstd_decompress/no_retpoline/func_pgot: ZSTD_decompressMultiFrame, 4194, pgot_memset_table_func_pgot

```asm
    418f:	jb     41ab <ZSTD_decompressMultiFrame+0x35b>
    4191:	mov    0x0(%rip),%rax        # 4198 <ZSTD_decompressMultiFrame+0x348>
			4194: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    4198:	mov    %r15,%rdx
    419b:	mov    %rbx,%rdi
    419e:	call   *%rax
    41a0:	mov    $0x1,%r8d
    41a6:	jmp    3f47 <ZSTD_decompressMultiFrame+0xf7>
    41ab:	mov    $0xfffffffffffffff4,%r15
    41b2:	jmp    3f07 <ZSTD_decompressMultiFrame+0xb7>
    41b7:	mov    $0xfffffffffffffffe,%r15
    41be:	jmp    3f07 <ZSTD_decompressMultiFrame+0xb7>
    41c3:	mov    0x6078(%r13),%eax
    41ca:	mov    %rbx,%r15
    41cd:	mov    -0x60(%rbp),%r14
    41d1:	mov    %r9,%rbx
    41d4:	test   %eax,%eax
    41d6:	jne    41f4 <ZSTD_decompressMultiFrame+0x3a4>
    41d8:	mov    %r15,%r12
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_initDStream_func_pgot, 46c3, pgot_memset_table_func_pgot

```asm
    46be:	xor    %esi,%esi
    46c0:	mov    0x0(%rip),%rax        # 46c7 <pgot_ZSTD_initDStream_func_pgot+0x87>
			46c3: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    46c7:	call   *%rax
    46c9:	lea    0xa0(%r12),%rdi
    46d1:	mov    $0x18,%edx
    46d6:	lea    -0x38(%rbp),%rsi
    46da:	mov    0x0(%rip),%rax        # 46e1 <pgot_ZSTD_initDStream_func_pgot+0xa1>
			46dd: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    46e1:	call   *%rax
    46e3:	push   -0x28(%rbp)
    46e6:	push   -0x30(%rbp)
    46e9:	push   -0x38(%rbp)
    46ec:	call   46f1 <pgot_ZSTD_initDStream_func_pgot+0xb1>
			46ed: R_X86_64_PLT32	pgot_ZSTD_createDCtx_advanced_func_pgot-0x4
    46f1:	mov    %rax,(%r12)
    46f5:	add    $0x18,%rsp
    46f9:	test   %rax,%rax
    46fc:	je     47fe <pgot_ZSTD_initDStream_func_pgot+0x1be>
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_initDStream_func_pgot, 46dd, pgot_memcpy_table_func_pgot

```asm
    46d6:	lea    -0x38(%rbp),%rsi
    46da:	mov    0x0(%rip),%rax        # 46e1 <pgot_ZSTD_initDStream_func_pgot+0xa1>
			46dd: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    46e1:	call   *%rax
    46e3:	push   -0x28(%rbp)
    46e6:	push   -0x30(%rbp)
    46e9:	push   -0x38(%rbp)
    46ec:	call   46f1 <pgot_ZSTD_initDStream_func_pgot+0xb1>
			46ed: R_X86_64_PLT32	pgot_ZSTD_createDCtx_advanced_func_pgot-0x4
    46f1:	mov    %rax,(%r12)
    46f5:	add    $0x18,%rsp
    46f9:	test   %rax,%rax
    46fc:	je     47fe <pgot_ZSTD_initDStream_func_pgot+0x1be>
    4702:	mov    0x8(%r12),%rdi
    4707:	mov    %rbx,0x50(%r12)
    470c:	movl   $0x1,0x30(%r12)
    4715:	movq   $0x0,0x70(%r12)
    471e:	movq   $0x0,0x68(%r12)
    4727:	movq   $0x0,0x48(%r12)
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decompressStream_func_pgot, 498e, pgot_memcpy_table_func_pgot

```asm
    4984:	sub    0x98(%rbx),%rcx
    498b:	mov    0x0(%rip),%rax        # 4992 <pgot_ZSTD_decompressStream_func_pgot+0xc2>
			498e: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4992:	sub    %r12,%rdx
    4995:	add    %r14,%rdi
    4998:	cmp    %rcx,%rdx
    499b:	jb     4e52 <pgot_ZSTD_decompressStream_func_pgot+0x582>
    49a1:	mov    %rcx,-0x40(%rbp)
    49a5:	mov    %rcx,%rdx
    49a8:	mov    %r12,%rsi
    49ab:	call   *%rax
    49ad:	mov    -0x40(%rbp),%rcx
    49b1:	mov    0x30(%rbx),%eax
    49b4:	mov    %r15,0x98(%rbx)
    49bb:	add    %rcx,%r12
    49be:	cmp    $0x2,%eax
    49c1:	jne    493f <pgot_ZSTD_decompressStream_func_pgot+0x6f>
    49c7:	mov    (%rbx),%rdi
    49ca:	mov    0x6060(%rdi),%r8
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decompressStream_func_pgot, 4a64, pgot_memcpy_table_func_pgot

```asm
    4a5e:	mov    %r13,%rdi
    4a61:	mov    0x0(%rip),%rax        # 4a68 <pgot_ZSTD_decompressStream_func_pgot+0x198>
			4a64: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4a68:	sub    %r13,%rcx
    4a6b:	cmp    %rcx,%r15
    4a6e:	mov    %rcx,%rdx
    4a71:	mov    %rcx,-0x48(%rbp)
    4a75:	cmovbe %r15,%rdx
    4a79:	add    0x58(%rbx),%rsi
    4a7d:	mov    %rdx,-0x40(%rbp)
    4a81:	call   *%rax
    4a83:	mov    -0x40(%rbp),%rdx
    4a87:	mov    -0x48(%rbp),%rcx
    4a8b:	add    %rdx,%r13
    4a8e:	add    0x68(%rbx),%rdx
    4a92:	mov    %rdx,0x68(%rbx)
    4a96:	cmp    %rcx,%r15
    4a99:	ja     49e1 <pgot_ZSTD_decompressStream_func_pgot+0x111>
    4a9f:	movl   $0x2,0x30(%rbx)
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_ZSTD_decompressStream_func_pgot, 4b3b, pgot_memcpy_table_func_pgot

```asm
    4b35:	mov    %r12,%rsi
    4b38:	mov    0x0(%rip),%rax        # 4b3f <pgot_ZSTD_decompressStream_func_pgot+0x26f>
			4b3b: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4b3f:	sub    %r12,%r15
    4b42:	cmp    %rcx,%r15
    4b45:	cmova  %rcx,%r15
    4b49:	add    0x38(%rbx),%rdi
    4b4d:	mov    %r15,%rdx
    4b50:	add    %r15,%r12
    4b53:	call   *%rax
    4b55:	mov    -0x48(%rbp),%rcx
    4b59:	add    %r15,0x48(%rbx)
    4b5d:	mov    -0x40(%rbp),%r8
    4b61:	cmp    %r15,%rcx
    4b64:	ja     49e1 <pgot_ZSTD_decompressStream_func_pgot+0x111>
    4b6a:	mov    (%rbx),%rdi
    4b6d:	mov    0x68(%rbx),%rsi
    4b71:	mov    0x60(%rbx),%rdx
    4b75:	mov    0x38(%rbx),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_FSE_readNCount_func_pgot, 279, memset

```asm
 274:	lea    (%rax,%r8,2),%rdi
 278:	call   27d <pgot_FSE_readNCount_func_pgot+0x21d>
			279: R_X86_64_PLT32	memset-0x4
 27d:	mov    -0x4c(%rbp),%r8d
 281:	mov    -0x58(%rbp),%ecx
 284:	mov    %r13d,%eax
 287:	sar    $0x3,%eax
 28a:	cltq   
 28c:	add    %r12,%rax
 28f:	cmp    -0x40(%rbp),%r12
 293:	jbe    2a2 <pgot_FSE_readNCount_func_pgot+0x242>
 295:	shr    $0x2,%ecx
 298:	cmp    -0x48(%rbp),%rax
 29c:	ja     195 <pgot_FSE_readNCount_func_pgot+0x135>
 2a2:	mov    (%rax),%esi
 2a4:	and    $0x7,%r13d
 2a8:	mov    %rax,%r12
 2ab:	mov    %r13d,%ecx
 2ae:	shr    %cl,%esi
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_readStats_wksp_func_pgot, 3bd, pgot_memset_table_func_pgot

```asm
 3b6:	mov    %r8,-0x38(%rbp)
 3ba:	mov    0x0(%rip),%rax        # 3c1 <pgot_HUF_readStats_wksp_func_pgot+0xa1>
			3bd: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
 3c1:	xor    %esi,%esi
 3c3:	mov    %r15,%rdi
 3c6:	mov    $0x34,%edx
 3cb:	call   *%rax
 3cd:	mov    -0x38(%rbp),%r8
 3d1:	xor    %r12d,%r12d
 3d4:	xor    %r9d,%r9d
 3d7:	xor    %eax,%eax
 3d9:	mov    $0x1,%r11d
 3df:	jmp    409 <pgot_HUF_readStats_wksp_func_pgot+0xe9>
 3e1:	addl   $0x1,(%r15,%rdx,4)
 3e6:	movzbl (%rax),%ecx
 3e9:	cmp    $0x1f,%cl
 3ec:	ja     3f2 <pgot_HUF_readStats_wksp_func_pgot+0xd2>
			3ee: R_X86_64_PC32	.text.unlikely+0x37
 3f2:	mov    %r11d,%eax
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_readStats_wksp_func_pgot, 462, pgot_memset_table_func_pgot

```asm
 45b:	mov    %r8,-0x38(%rbp)
 45f:	mov    0x0(%rip),%rax        # 466 <pgot_HUF_readStats_wksp_func_pgot+0x146>
			462: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
 466:	xor    %esi,%esi
 468:	mov    %r15,%rdi
 46b:	mov    $0x34,%edx
 470:	call   *%rax
 472:	mov    -0x38(%rbp),%r8
 476:	test   %r8,%r8
 479:	jne    3d1 <pgot_HUF_readStats_wksp_func_pgot+0xb1>
 47f:	jmp    414 <pgot_HUF_readStats_wksp_func_pgot+0xf4>
 481:	test   %r9d,%r9d
 484:	je     414 <pgot_HUF_readStats_wksp_func_pgot+0xf4>
 486:	bsr    %r9d,%edx
 48a:	mov    $0x20,%eax
 48f:	xor    $0x1f,%edx
 492:	mov    %eax,%ecx
 494:	sub    %edx,%ecx
 496:	cmp    $0xc,%ecx
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_FSE_buildDTable_wksp_func_pgot, 267, pgot_memcpy_table_func_pgot

```asm
 260:	mov    %r9,-0x50(%rbp)
 264:	mov    0x0(%rip),%rax        # 26b <pgot_FSE_buildDTable_wksp_func_pgot+0x12b>
			267: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
 26b:	call   *%rax
 26d:	mov    -0x48(%rbp),%eax
 270:	mov    -0x50(%rbp),%r9
 274:	xor    %r10d,%r10d
 277:	mov    -0x58(%rbp),%rcx
 27b:	mov    %eax,%edx
 27d:	shr    %eax
 27f:	shr    $0x3,%edx
 282:	lea    0x3(%rdx,%rax,1),%edx
 286:	xor    %eax,%eax
 288:	xor    %esi,%esi
 28a:	cmpw   $0x0,0x0(%r13,%r10,2)
 291:	mov    %r10d,%edi
 294:	jle    2b5 <pgot_FSE_buildDTable_wksp_func_pgot+0x175>
 296:	mov    %eax,%r8d
 299:	mov    %dil,0x2(%r9,%r8,4)
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_fillDTableX4Level2, 4b, pgot_memcpy_table_func_pgot

```asm
      46:	xor    %eax,%eax
      48:	mov    0x0(%rip),%rax        # 4f <HUF_fillDTableX4Level2+0x4f>
			4b: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
      4f:	call   *%rax
      51:	cmp    $0x1,%r12d
      55:	mov    -0x70(%rbp),%r9d
      59:	jle    93 <HUF_fillDTableX4Level2+0x93>
      5b:	movslq %r12d,%r8
      5e:	cmp    $0xc,%r8
      62:	ja     1f4 <HUF_fillDTableX4Level2+0x1f4>
      68:	mov    -0x64(%rbp,%r8,4),%ecx
      6d:	mov    %r15d,%edx
      70:	test   %ecx,%ecx
      72:	je     93 <HUF_fillDTableX4Level2+0x93>
      74:	sub    $0x1,%ecx
      77:	mov    %r13,%rax
      7a:	lea    0x4(%r13,%rcx,4),%rcx
      7f:	mov    %r9w,(%rax)
      83:	add    $0x4,%rax
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decodeLastSymbolX4.isra.0, 38a, pgot_memcpy_table_func_pgot

```asm
     383:	lea    (%rdx,%rax,4),%r12
     387:	mov    0x0(%rip),%rax        # 38e <HUF_decodeLastSymbolX4.isra.0+0x2e>
			38a: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     38e:	mov    $0x1,%edx
     393:	mov    %r12,%rsi
     396:	call   *%rax
     398:	cmpb   $0x1,0x3(%r12)
     39e:	je     3c3 <HUF_decodeLastSymbolX4.isra.0+0x63>
     3a0:	mov    0x8(%rbx),%edx
     3a3:	cmp    $0x3f,%edx
     3a6:	ja     3bd <HUF_decodeLastSymbolX4.isra.0+0x5d>
     3a8:	movzbl 0x2(%r12),%eax
     3ae:	add    %edx,%eax
     3b0:	mov    $0x40,%edx
     3b5:	cmp    %edx,%eax
     3b7:	cmova  %edx,%eax
     3ba:	mov    %eax,0x8(%rbx)
     3bd:	pop    %rbx
     3be:	pop    %r12
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress1X2_usingDTable_internal, 423, pgot_memcpy_table_func_pgot

```asm
     41e:	xor    %eax,%eax
     420:	mov    0x0(%rip),%rax        # 427 <HUF_decompress1X2_usingDTable_internal+0x47>
			423: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     427:	call   *%rax
     429:	movzbl -0x4e(%rbp),%eax
     42d:	mov    %r14,%rsi
     430:	lea    -0x50(%rbp),%rdi
     434:	mov    %r13,%rdx
     437:	mov    %al,-0x51(%rbp)
     43a:	call   220 <BIT_initDStream>
     43f:	mov    %rax,%rdi
     442:	mov    %rax,%r14
     445:	call   44a <HUF_decompress1X2_usingDTable_internal+0x6a>
			446: R_X86_64_PLT32	pgot_HUF_isError_func_pgot-0x4
     44a:	test   %eax,%eax
     44c:	jne    573 <HUF_decompress1X2_usingDTable_internal+0x193>
     452:	mov    -0x48(%rbp),%eax
     455:	movzbl -0x51(%rbp),%esi
     459:	lea    (%rbx,%r12,1),%rdi
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 78a, pgot_memcpy_table_func_pgot

```asm
     783:	mov    %rbx,-0x60(%rbp)
     787:	mov    0x0(%rip),%rax        # 78e <HUF_decompress1X4_usingDTable_internal+0x6e>
			78a: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     78e:	lea    0x4(%r14),%r12
     792:	call   *%rax
     794:	movzbl -0x52(%rbp),%eax
     798:	mov    -0x48(%rbp),%ecx
     79b:	mov    %eax,-0x64(%rbp)
     79e:	cmp    $0x40,%ecx
     7a1:	ja     a15 <HUF_decompress1X4_usingDTable_internal+0x2f5>
     7a7:	neg    %eax
     7a9:	lea    -0x7(%rbx),%r15
     7ad:	mov    %eax,%ebx
     7af:	and    $0x3f,%ebx
     7b2:	jmp    8db <HUF_decompress1X4_usingDTable_internal+0x1bb>
     7b7:	cmp    %rsi,%rax
     7ba:	je     911 <HUF_decompress1X4_usingDTable_internal+0x1f1>
     7c0:	mov    %ecx,%edx
     7c2:	mov    %rax,%r8
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 811, pgot_memcpy_table_func_pgot

```asm
     80a:	lea    (%r12,%rax,4),%r14
     80e:	mov    0x0(%rip),%rax        # 815 <HUF_decompress1X4_usingDTable_internal+0xf5>
			811: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     815:	mov    %r14,%rsi
     818:	call   *%rax
     81a:	mov    -0x50(%rbp),%rax
     81e:	movzbl 0x2(%r14),%ecx
     823:	mov    $0x2,%edx
     828:	add    -0x48(%rbp),%ecx
     82b:	movzbl 0x3(%r14),%edi
     830:	mov    %ecx,-0x48(%rbp)
     833:	shl    %cl,%rax
     836:	mov    %ebx,%ecx
     838:	shr    %cl,%rax
     83b:	add    %rdi,%r13
     83e:	lea    (%r12,%rax,4),%r14
     842:	mov    %r13,%rdi
     845:	mov    0x0(%rip),%rax        # 84c <HUF_decompress1X4_usingDTable_internal+0x12c>
			848: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 848, pgot_memcpy_table_func_pgot

```asm
     842:	mov    %r13,%rdi
     845:	mov    0x0(%rip),%rax        # 84c <HUF_decompress1X4_usingDTable_internal+0x12c>
			848: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     84c:	mov    %r14,%rsi
     84f:	call   *%rax
     851:	movzbl 0x3(%r14),%eax
     856:	movzbl 0x2(%r14),%ecx
     85b:	mov    $0x2,%edx
     860:	add    -0x48(%rbp),%ecx
     863:	add    %rax,%r13
     866:	mov    -0x50(%rbp),%rax
     86a:	mov    %ecx,-0x48(%rbp)
     86d:	mov    %r13,%rdi
     870:	shl    %cl,%rax
     873:	mov    %ebx,%ecx
     875:	shr    %cl,%rax
     878:	lea    (%r12,%rax,4),%r14
     87c:	mov    0x0(%rip),%rax        # 883 <HUF_decompress1X4_usingDTable_internal+0x163>
			87f: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 87f, pgot_memcpy_table_func_pgot

```asm
     878:	lea    (%r12,%rax,4),%r14
     87c:	mov    0x0(%rip),%rax        # 883 <HUF_decompress1X4_usingDTable_internal+0x163>
			87f: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     883:	mov    %r14,%rsi
     886:	call   *%rax
     888:	mov    -0x50(%rbp),%rax
     88c:	movzbl 0x2(%r14),%ecx
     891:	mov    $0x2,%edx
     896:	add    -0x48(%rbp),%ecx
     899:	movzbl 0x3(%r14),%r9d
     89e:	mov    %ecx,-0x48(%rbp)
     8a1:	shl    %cl,%rax
     8a4:	mov    %ebx,%ecx
     8a6:	shr    %cl,%rax
     8a9:	add    %r9,%r13
     8ac:	lea    (%r12,%rax,4),%r14
     8b0:	mov    %r13,%rdi
     8b3:	mov    0x0(%rip),%rax        # 8ba <HUF_decompress1X4_usingDTable_internal+0x19a>
			8b6: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 8b6, pgot_memcpy_table_func_pgot

```asm
     8b0:	mov    %r13,%rdi
     8b3:	mov    0x0(%rip),%rax        # 8ba <HUF_decompress1X4_usingDTable_internal+0x19a>
			8b6: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     8ba:	mov    %r14,%rsi
     8bd:	call   *%rax
     8bf:	movzbl 0x3(%r14),%eax
     8c4:	movzbl 0x2(%r14),%ecx
     8c9:	add    -0x48(%rbp),%ecx
     8cc:	mov    %ecx,-0x48(%rbp)
     8cf:	add    %rax,%r13
     8d2:	cmp    $0x40,%ecx
     8d5:	ja     a15 <HUF_decompress1X4_usingDTable_internal+0x2f5>
     8db:	mov    -0x38(%rbp),%rsi
     8df:	mov    -0x40(%rbp),%rax
     8e3:	lea    0x8(%rsi),%rdi
     8e7:	cmp    %rdi,%rax
     8ea:	jb     7b7 <HUF_decompress1X4_usingDTable_internal+0x97>
     8f0:	mov    %ecx,%edx
     8f2:	and    $0x7,%ecx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 991, pgot_memcpy_table_func_pgot

```asm
     98a:	lea    (%r12,%rax,4),%r14
     98e:	mov    0x0(%rip),%rax        # 995 <HUF_decompress1X4_usingDTable_internal+0x275>
			991: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     995:	mov    %r14,%rsi
     998:	call   *%rax
     99a:	movzbl 0x3(%r14),%edx
     99f:	movzbl 0x2(%r14),%eax
     9a4:	add    -0x48(%rbp),%eax
     9a7:	mov    %eax,-0x48(%rbp)
     9aa:	add    %rdx,%r13
     9ad:	cmp    $0x40,%eax
     9b0:	ja     a1d <HUF_decompress1X4_usingDTable_internal+0x2fd>
     9b2:	mov    -0x38(%rbp),%rsi
     9b6:	lea    0x8(%rsi),%rdi
     9ba:	mov    -0x40(%rbp),%rdx
     9be:	cmp    %rdi,%rdx
     9c1:	jb     935 <HUF_decompress1X4_usingDTable_internal+0x215>
     9c7:	mov    %eax,%ecx
     9c9:	and    $0x7,%eax
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, a4c, pgot_memcpy_table_func_pgot

```asm
     a45:	lea    (%r12,%rax,4),%r14
     a49:	mov    0x0(%rip),%rax        # a50 <HUF_decompress1X4_usingDTable_internal+0x330>
			a4c: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     a50:	mov    %r14,%rsi
     a53:	call   *%rax
     a55:	movzbl 0x3(%r14),%eax
     a5a:	movzbl 0x2(%r14),%ecx
     a5f:	add    -0x48(%rbp),%ecx
     a62:	add    %rax,%r13
     a65:	mov    %ecx,-0x48(%rbp)
     a68:	cmp    %rbx,%r13
     a6b:	jbe    a30 <HUF_decompress1X4_usingDTable_internal+0x310>
     a6d:	cmp    %r13,-0x60(%rbp)
     a71:	ja     aa6 <HUF_decompress1X4_usingDTable_internal+0x386>
     a73:	mov    -0x38(%rbp),%rax
     a77:	mov    $0xfffffffffffffff2,%r12
     a7e:	cmp    %rax,-0x40(%rbp)
     a82:	je     aba <HUF_decompress1X4_usingDTable_internal+0x39a>
     a84:	mov    -0x30(%rbp),%rax
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X2_usingDTable_internal, b54, pgot_memcpy_table_func_pgot

```asm
     b4e:	sub    %rax,%r12
     b51:	mov    0x0(%rip),%rax        # b58 <HUF_decompress4X2_usingDTable_internal+0x88>
			b54: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     b58:	call   *%rax
     b5a:	mov    -0xc0(%rbp),%rcx
     b61:	movzbl -0x4e(%rbp),%eax
     b65:	mov    -0xc8(%rbp),%r9
     b6c:	cmp    %r12,%rcx
     b6f:	mov    %al,-0xe0(%rbp)
     b75:	jae    ba7 <HUF_decompress4X2_usingDTable_internal+0xd7>
     b77:	mov    $0xfffffffffffffff2,%r15
     b7e:	mov    -0x30(%rbp),%rax
     b82:	sub    %gs:0x28,%rax
     b8b:	jne    213f <HUF_decompress4X2_usingDTable_internal+0x166f>
     b91:	add    $0x110,%rsp
     b98:	mov    %r15,%rax
     b9b:	pop    %rbx
     b9c:	pop    %r12
     b9e:	pop    %r13
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 21d3, pgot_memcpy_table_func_pgot

```asm
    21cd:	sub    %rax,%r13
    21d0:	mov    0x0(%rip),%rax        # 21d7 <HUF_decompress4X4_usingDTable_internal+0x87>
			21d3: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    21d7:	call   *%rax
    21d9:	mov    -0xb8(%rbp),%rcx
    21e0:	movzbl -0x4e(%rbp),%eax
    21e4:	mov    -0xc0(%rbp),%r9
    21eb:	cmp    %r13,%rcx
    21ee:	mov    %al,-0xdc(%rbp)
    21f4:	jae    2226 <HUF_decompress4X4_usingDTable_internal+0xd6>
    21f6:	mov    $0xfffffffffffffff2,%r14
    21fd:	mov    -0x30(%rbp),%rax
    2201:	sub    %gs:0x28,%rax
    220a:	jne    3cfa <HUF_decompress4X4_usingDTable_internal+0x1baa>
    2210:	add    $0xe0,%rsp
    2217:	mov    %r14,%rax
    221a:	pop    %rbx
    221b:	pop    %r12
    221d:	pop    %r13
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 270a, pgot_memcpy_table_func_pgot

```asm
    2703:	lea    (%r12,%rax,4),%rcx
    2707:	mov    0x0(%rip),%rax        # 270e <HUF_decompress4X4_usingDTable_internal+0x5be>
			270a: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    270e:	mov    %rcx,%rsi
    2711:	mov    %rcx,-0xc0(%rbp)
    2718:	call   *%rax
    271a:	mov    -0xc0(%rbp),%rcx
    2721:	mov    %r15,%rdi
    2724:	mov    $0x2,%edx
    2729:	movzbl 0x2(%rcx),%eax
    272d:	add    %eax,-0xa8(%rbp)
    2733:	movzbl 0x3(%rcx),%eax
    2737:	mov    -0x88(%rbp),%ecx
    273d:	add    %rax,%r13
    2740:	mov    -0x90(%rbp),%rax
    2747:	shl    %cl,%rax
    274a:	movzbl -0xb8(%rbp),%ecx
    2751:	shr    %cl,%rax
    2754:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 275b, pgot_memcpy_table_func_pgot

```asm
    2754:	lea    (%r12,%rax,4),%rcx
    2758:	mov    0x0(%rip),%rax        # 275f <HUF_decompress4X4_usingDTable_internal+0x60f>
			275b: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    275f:	mov    %rcx,%rsi
    2762:	mov    %rcx,-0xc0(%rbp)
    2769:	call   *%rax
    276b:	mov    -0xc0(%rbp),%rcx
    2772:	mov    %r14,%rdi
    2775:	mov    $0x2,%edx
    277a:	movzbl 0x2(%rcx),%eax
    277e:	add    %eax,-0x88(%rbp)
    2784:	movzbl 0x3(%rcx),%eax
    2788:	mov    -0x68(%rbp),%ecx
    278b:	add    %rax,%r15
    278e:	mov    -0x70(%rbp),%rax
    2792:	shl    %cl,%rax
    2795:	movzbl -0xb8(%rbp),%ecx
    279c:	shr    %cl,%rax
    279f:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 27a6, pgot_memcpy_table_func_pgot

```asm
    279f:	lea    (%r12,%rax,4),%rcx
    27a3:	mov    0x0(%rip),%rax        # 27aa <HUF_decompress4X4_usingDTable_internal+0x65a>
			27a6: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    27aa:	mov    %rcx,%rsi
    27ad:	mov    %rcx,-0xc0(%rbp)
    27b4:	call   *%rax
    27b6:	mov    -0xc0(%rbp),%rcx
    27bd:	mov    %rbx,%rdi
    27c0:	mov    $0x2,%edx
    27c5:	movzbl 0x2(%rcx),%eax
    27c9:	add    %eax,-0x68(%rbp)
    27cc:	movzbl 0x3(%rcx),%eax
    27d0:	mov    -0x48(%rbp),%ecx
    27d3:	add    %rax,%r14
    27d6:	mov    -0x50(%rbp),%rax
    27da:	shl    %cl,%rax
    27dd:	movzbl -0xb8(%rbp),%ecx
    27e4:	shr    %cl,%rax
    27e7:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 27ee, pgot_memcpy_table_func_pgot

```asm
    27e7:	lea    (%r12,%rax,4),%rcx
    27eb:	mov    0x0(%rip),%rax        # 27f2 <HUF_decompress4X4_usingDTable_internal+0x6a2>
			27ee: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    27f2:	mov    %rcx,%rsi
    27f5:	mov    %rcx,-0xc0(%rbp)
    27fc:	call   *%rax
    27fe:	mov    -0xc0(%rbp),%rcx
    2805:	mov    %r13,%rdi
    2808:	mov    $0x2,%edx
    280d:	movzbl 0x2(%rcx),%eax
    2811:	add    %eax,-0x48(%rbp)
    2814:	movzbl 0x3(%rcx),%eax
    2818:	mov    -0xa8(%rbp),%ecx
    281e:	add    %rax,%rbx
    2821:	mov    -0xb0(%rbp),%rax
    2828:	shl    %cl,%rax
    282b:	movzbl -0xb8(%rbp),%ecx
    2832:	shr    %cl,%rax
    2835:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 283c, pgot_memcpy_table_func_pgot

```asm
    2835:	lea    (%r12,%rax,4),%rcx
    2839:	mov    0x0(%rip),%rax        # 2840 <HUF_decompress4X4_usingDTable_internal+0x6f0>
			283c: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2840:	mov    %rcx,%rsi
    2843:	mov    %rcx,-0xc0(%rbp)
    284a:	call   *%rax
    284c:	mov    -0xc0(%rbp),%rcx
    2853:	mov    %r15,%rdi
    2856:	mov    $0x2,%edx
    285b:	movzbl 0x2(%rcx),%eax
    285f:	add    %eax,-0xa8(%rbp)
    2865:	movzbl 0x3(%rcx),%eax
    2869:	mov    -0x88(%rbp),%ecx
    286f:	add    %rax,%r13
    2872:	mov    -0x90(%rbp),%rax
    2879:	shl    %cl,%rax
    287c:	movzbl -0xb8(%rbp),%ecx
    2883:	shr    %cl,%rax
    2886:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 288d, pgot_memcpy_table_func_pgot

```asm
    2886:	lea    (%r12,%rax,4),%rcx
    288a:	mov    0x0(%rip),%rax        # 2891 <HUF_decompress4X4_usingDTable_internal+0x741>
			288d: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2891:	mov    %rcx,%rsi
    2894:	mov    %rcx,-0xc0(%rbp)
    289b:	call   *%rax
    289d:	mov    -0xc0(%rbp),%rcx
    28a4:	mov    %r14,%rdi
    28a7:	mov    $0x2,%edx
    28ac:	movzbl 0x2(%rcx),%eax
    28b0:	add    %eax,-0x88(%rbp)
    28b6:	movzbl 0x3(%rcx),%eax
    28ba:	mov    -0x68(%rbp),%ecx
    28bd:	add    %rax,%r15
    28c0:	mov    -0x70(%rbp),%rax
    28c4:	shl    %cl,%rax
    28c7:	movzbl -0xb8(%rbp),%ecx
    28ce:	shr    %cl,%rax
    28d1:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 28d8, pgot_memcpy_table_func_pgot

```asm
    28d1:	lea    (%r12,%rax,4),%rcx
    28d5:	mov    0x0(%rip),%rax        # 28dc <HUF_decompress4X4_usingDTable_internal+0x78c>
			28d8: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    28dc:	mov    %rcx,%rsi
    28df:	mov    %rcx,-0xc0(%rbp)
    28e6:	call   *%rax
    28e8:	mov    -0xc0(%rbp),%rcx
    28ef:	mov    %rbx,%rdi
    28f2:	mov    $0x2,%edx
    28f7:	movzbl 0x2(%rcx),%eax
    28fb:	add    %eax,-0x68(%rbp)
    28fe:	movzbl 0x3(%rcx),%eax
    2902:	mov    -0x48(%rbp),%ecx
    2905:	add    %rax,%r14
    2908:	mov    -0x50(%rbp),%rax
    290c:	shl    %cl,%rax
    290f:	movzbl -0xb8(%rbp),%ecx
    2916:	shr    %cl,%rax
    2919:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2920, pgot_memcpy_table_func_pgot

```asm
    2919:	lea    (%r12,%rax,4),%rcx
    291d:	mov    0x0(%rip),%rax        # 2924 <HUF_decompress4X4_usingDTable_internal+0x7d4>
			2920: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2924:	mov    %rcx,%rsi
    2927:	mov    %rcx,-0xc0(%rbp)
    292e:	call   *%rax
    2930:	mov    -0xc0(%rbp),%rcx
    2937:	mov    %r13,%rdi
    293a:	mov    $0x2,%edx
    293f:	movzbl 0x2(%rcx),%eax
    2943:	add    %eax,-0x48(%rbp)
    2946:	movzbl 0x3(%rcx),%eax
    294a:	mov    -0xa8(%rbp),%ecx
    2950:	add    %rax,%rbx
    2953:	mov    -0xb0(%rbp),%rax
    295a:	shl    %cl,%rax
    295d:	movzbl -0xb8(%rbp),%ecx
    2964:	shr    %cl,%rax
    2967:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 296e, pgot_memcpy_table_func_pgot

```asm
    2967:	lea    (%r12,%rax,4),%rcx
    296b:	mov    0x0(%rip),%rax        # 2972 <HUF_decompress4X4_usingDTable_internal+0x822>
			296e: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2972:	mov    %rcx,%rsi
    2975:	mov    %rcx,-0xc0(%rbp)
    297c:	call   *%rax
    297e:	mov    -0xc0(%rbp),%rcx
    2985:	mov    %r15,%rdi
    2988:	mov    $0x2,%edx
    298d:	movzbl 0x2(%rcx),%eax
    2991:	add    %eax,-0xa8(%rbp)
    2997:	movzbl 0x3(%rcx),%eax
    299b:	mov    -0x88(%rbp),%ecx
    29a1:	add    %rax,%r13
    29a4:	mov    -0x90(%rbp),%rax
    29ab:	shl    %cl,%rax
    29ae:	movzbl -0xb8(%rbp),%ecx
    29b5:	shr    %cl,%rax
    29b8:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 29bf, pgot_memcpy_table_func_pgot

```asm
    29b8:	lea    (%r12,%rax,4),%rcx
    29bc:	mov    0x0(%rip),%rax        # 29c3 <HUF_decompress4X4_usingDTable_internal+0x873>
			29bf: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    29c3:	mov    %rcx,%rsi
    29c6:	mov    %rcx,-0xc0(%rbp)
    29cd:	call   *%rax
    29cf:	mov    -0xc0(%rbp),%rcx
    29d6:	mov    %r14,%rdi
    29d9:	mov    $0x2,%edx
    29de:	movzbl 0x2(%rcx),%eax
    29e2:	add    %eax,-0x88(%rbp)
    29e8:	movzbl 0x3(%rcx),%eax
    29ec:	mov    -0x68(%rbp),%ecx
    29ef:	add    %rax,%r15
    29f2:	mov    -0x70(%rbp),%rax
    29f6:	shl    %cl,%rax
    29f9:	movzbl -0xb8(%rbp),%ecx
    2a00:	shr    %cl,%rax
    2a03:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2a0a, pgot_memcpy_table_func_pgot

```asm
    2a03:	lea    (%r12,%rax,4),%rcx
    2a07:	mov    0x0(%rip),%rax        # 2a0e <HUF_decompress4X4_usingDTable_internal+0x8be>
			2a0a: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2a0e:	mov    %rcx,%rsi
    2a11:	mov    %rcx,-0xc0(%rbp)
    2a18:	call   *%rax
    2a1a:	mov    -0xc0(%rbp),%rcx
    2a21:	mov    %rbx,%rdi
    2a24:	mov    $0x2,%edx
    2a29:	movzbl 0x2(%rcx),%eax
    2a2d:	add    %eax,-0x68(%rbp)
    2a30:	movzbl 0x3(%rcx),%eax
    2a34:	mov    -0x48(%rbp),%ecx
    2a37:	add    %rax,%r14
    2a3a:	mov    -0x50(%rbp),%rax
    2a3e:	shl    %cl,%rax
    2a41:	movzbl -0xb8(%rbp),%ecx
    2a48:	shr    %cl,%rax
    2a4b:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2a52, pgot_memcpy_table_func_pgot

```asm
    2a4b:	lea    (%r12,%rax,4),%rcx
    2a4f:	mov    0x0(%rip),%rax        # 2a56 <HUF_decompress4X4_usingDTable_internal+0x906>
			2a52: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2a56:	mov    %rcx,%rsi
    2a59:	mov    %rcx,-0xc0(%rbp)
    2a60:	call   *%rax
    2a62:	mov    -0xc0(%rbp),%rcx
    2a69:	mov    %r13,%rdi
    2a6c:	mov    $0x2,%edx
    2a71:	movzbl 0x2(%rcx),%eax
    2a75:	add    %eax,-0x48(%rbp)
    2a78:	movzbl 0x3(%rcx),%eax
    2a7c:	mov    -0xa8(%rbp),%ecx
    2a82:	add    %rax,%rbx
    2a85:	mov    -0xb0(%rbp),%rax
    2a8c:	shl    %cl,%rax
    2a8f:	movzbl -0xb8(%rbp),%ecx
    2a96:	shr    %cl,%rax
    2a99:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2aa0, pgot_memcpy_table_func_pgot

```asm
    2a99:	lea    (%r12,%rax,4),%rcx
    2a9d:	mov    0x0(%rip),%rax        # 2aa4 <HUF_decompress4X4_usingDTable_internal+0x954>
			2aa0: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2aa4:	mov    %rcx,%rsi
    2aa7:	mov    %rcx,-0xc0(%rbp)
    2aae:	call   *%rax
    2ab0:	mov    -0xc0(%rbp),%rcx
    2ab7:	mov    %r15,%rdi
    2aba:	mov    $0x2,%edx
    2abf:	movzbl 0x2(%rcx),%eax
    2ac3:	add    %eax,-0xa8(%rbp)
    2ac9:	movzbl 0x3(%rcx),%eax
    2acd:	mov    -0x88(%rbp),%ecx
    2ad3:	add    %rax,%r13
    2ad6:	mov    -0x90(%rbp),%rax
    2add:	shl    %cl,%rax
    2ae0:	movzbl -0xb8(%rbp),%ecx
    2ae7:	shr    %cl,%rax
    2aea:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2af1, pgot_memcpy_table_func_pgot

```asm
    2aea:	lea    (%r12,%rax,4),%rcx
    2aee:	mov    0x0(%rip),%rax        # 2af5 <HUF_decompress4X4_usingDTable_internal+0x9a5>
			2af1: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2af5:	mov    %rcx,%rsi
    2af8:	mov    %rcx,-0xc0(%rbp)
    2aff:	call   *%rax
    2b01:	mov    -0xc0(%rbp),%rcx
    2b08:	mov    %r14,%rdi
    2b0b:	mov    $0x2,%edx
    2b10:	movzbl 0x2(%rcx),%eax
    2b14:	add    %eax,-0x88(%rbp)
    2b1a:	movzbl 0x3(%rcx),%eax
    2b1e:	mov    -0x68(%rbp),%ecx
    2b21:	add    %rax,%r15
    2b24:	mov    -0x70(%rbp),%rax
    2b28:	shl    %cl,%rax
    2b2b:	movzbl -0xb8(%rbp),%ecx
    2b32:	shr    %cl,%rax
    2b35:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2b3c, pgot_memcpy_table_func_pgot

```asm
    2b35:	lea    (%r12,%rax,4),%rcx
    2b39:	mov    0x0(%rip),%rax        # 2b40 <HUF_decompress4X4_usingDTable_internal+0x9f0>
			2b3c: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2b40:	mov    %rcx,%rsi
    2b43:	mov    %rcx,-0xc0(%rbp)
    2b4a:	call   *%rax
    2b4c:	mov    -0xc0(%rbp),%rcx
    2b53:	mov    $0x2,%edx
    2b58:	mov    %rbx,%rdi
    2b5b:	movzbl 0x2(%rcx),%eax
    2b5f:	add    %eax,-0x68(%rbp)
    2b62:	movzbl 0x3(%rcx),%eax
    2b66:	mov    -0x48(%rbp),%ecx
    2b69:	add    %rax,%r14
    2b6c:	mov    -0x50(%rbp),%rax
    2b70:	shl    %cl,%rax
    2b73:	movzbl -0xb8(%rbp),%ecx
    2b7a:	shr    %cl,%rax
    2b7d:	lea    (%r12,%rax,4),%rcx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2b84, pgot_memcpy_table_func_pgot

```asm
    2b7d:	lea    (%r12,%rax,4),%rcx
    2b81:	mov    0x0(%rip),%rax        # 2b88 <HUF_decompress4X4_usingDTable_internal+0xa38>
			2b84: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2b88:	mov    %rcx,-0xc0(%rbp)
    2b8f:	mov    %rcx,%rsi
    2b92:	call   *%rax
    2b94:	mov    -0xc0(%rbp),%rcx
    2b9b:	movzbl 0x3(%rcx),%edx
    2b9f:	movzbl 0x2(%rcx),%eax
    2ba3:	mov    -0xa8(%rbp),%ecx
    2ba9:	add    -0x48(%rbp),%eax
    2bac:	add    %rdx,%rbx
    2baf:	mov    %eax,-0x48(%rbp)
    2bb2:	mov    $0x3,%edx
    2bb7:	cmp    $0x40,%ecx
    2bba:	ja     258f <HUF_decompress4X4_usingDTable_internal+0x43f>
    2bc0:	mov    -0x98(%rbp),%rdi
    2bc7:	mov    -0xa0(%rbp),%rsi
    2bce:	lea    0x8(%rdi),%rdx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2ce8, pgot_memcpy_table_func_pgot

```asm
    2ce1:	lea    (%r12,%rax,4),%r14
    2ce5:	mov    0x0(%rip),%rax        # 2cec <HUF_decompress4X4_usingDTable_internal+0xb9c>
			2ce8: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2cec:	mov    %r14,%rsi
    2cef:	call   *%rax
    2cf1:	movzbl 0x3(%r14),%eax
    2cf6:	movzbl 0x2(%r14),%ecx
    2cfb:	mov    $0x2,%edx
    2d00:	add    -0xa8(%rbp),%ecx
    2d06:	add    %rax,%r13
    2d09:	mov    -0xb0(%rbp),%rax
    2d10:	mov    %ecx,-0xa8(%rbp)
    2d16:	mov    %r13,%rdi
    2d19:	shl    %cl,%rax
    2d1c:	mov    %ebx,%ecx
    2d1e:	shr    %cl,%rax
    2d21:	lea    (%r12,%rax,4),%r14
    2d25:	mov    0x0(%rip),%rax        # 2d2c <HUF_decompress4X4_usingDTable_internal+0xbdc>
			2d28: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2d28, pgot_memcpy_table_func_pgot

```asm
    2d21:	lea    (%r12,%rax,4),%r14
    2d25:	mov    0x0(%rip),%rax        # 2d2c <HUF_decompress4X4_usingDTable_internal+0xbdc>
			2d28: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2d2c:	mov    %r14,%rsi
    2d2f:	call   *%rax
    2d31:	mov    -0xb0(%rbp),%rax
    2d38:	movzbl 0x2(%r14),%ecx
    2d3d:	mov    $0x2,%edx
    2d42:	add    -0xa8(%rbp),%ecx
    2d48:	movzbl 0x3(%r14),%edi
    2d4d:	mov    %ecx,-0xa8(%rbp)
    2d53:	shl    %cl,%rax
    2d56:	mov    %ebx,%ecx
    2d58:	shr    %cl,%rax
    2d5b:	add    %rdi,%r13
    2d5e:	lea    (%r12,%rax,4),%r14
    2d62:	mov    %r13,%rdi
    2d65:	mov    0x0(%rip),%rax        # 2d6c <HUF_decompress4X4_usingDTable_internal+0xc1c>
			2d68: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2d68, pgot_memcpy_table_func_pgot

```asm
    2d62:	mov    %r13,%rdi
    2d65:	mov    0x0(%rip),%rax        # 2d6c <HUF_decompress4X4_usingDTable_internal+0xc1c>
			2d68: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2d6c:	mov    %r14,%rsi
    2d6f:	call   *%rax
    2d71:	mov    -0xb0(%rbp),%rax
    2d78:	movzbl 0x2(%r14),%ecx
    2d7d:	mov    $0x2,%edx
    2d82:	add    -0xa8(%rbp),%ecx
    2d88:	movzbl 0x3(%r14),%r8d
    2d8d:	mov    %ecx,-0xa8(%rbp)
    2d93:	shl    %cl,%rax
    2d96:	mov    %ebx,%ecx
    2d98:	shr    %cl,%rax
    2d9b:	add    %r8,%r13
    2d9e:	lea    (%r12,%rax,4),%r14
    2da2:	mov    %r13,%rdi
    2da5:	mov    0x0(%rip),%rax        # 2dac <HUF_decompress4X4_usingDTable_internal+0xc5c>
			2da8: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2da8, pgot_memcpy_table_func_pgot

```asm
    2da2:	mov    %r13,%rdi
    2da5:	mov    0x0(%rip),%rax        # 2dac <HUF_decompress4X4_usingDTable_internal+0xc5c>
			2da8: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2dac:	mov    %r14,%rsi
    2daf:	call   *%rax
    2db1:	movzbl 0x3(%r14),%eax
    2db6:	movzbl 0x2(%r14),%ecx
    2dbb:	add    -0xa8(%rbp),%ecx
    2dc1:	mov    %ecx,-0xa8(%rbp)
    2dc7:	add    %rax,%r13
    2dca:	cmp    $0x40,%ecx
    2dcd:	ja     2ebf <HUF_decompress4X4_usingDTable_internal+0xd6f>
    2dd3:	mov    -0x98(%rbp),%rsi
    2dda:	mov    -0xa0(%rbp),%rax
    2de1:	lea    0x8(%rsi),%rdi
    2de5:	cmp    %rdi,%rax
    2de8:	jb     2c81 <HUF_decompress4X4_usingDTable_internal+0xb31>
    2dee:	mov    %ecx,%edx
    2df0:	and    $0x7,%ecx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2f48, pgot_memcpy_table_func_pgot

```asm
    2f41:	lea    (%r12,%rax,4),%r14
    2f45:	mov    0x0(%rip),%rax        # 2f4c <HUF_decompress4X4_usingDTable_internal+0xdfc>
			2f48: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2f4c:	mov    %r14,%rsi
    2f4f:	call   *%rax
    2f51:	movzbl 0x3(%r14),%eax
    2f56:	movzbl 0x2(%r14),%ecx
    2f5b:	add    -0xa8(%rbp),%ecx
    2f61:	add    %rax,%r13
    2f64:	mov    %ecx,-0xa8(%rbp)
    2f6a:	cmp    %rbx,%r13
    2f6d:	jbe    2f29 <HUF_decompress4X4_usingDTable_internal+0xdd9>
    2f6f:	mov    %r13,-0xc8(%rbp)
    2f76:	mov    -0xb8(%rbp),%r15
    2f7d:	mov    -0xc0(%rbp),%r14
    2f84:	mov    -0x108(%rbp),%r13
    2f8b:	mov    -0xc8(%rbp),%rbx
    2f92:	cmp    %rbx,-0xe8(%rbp)
    2f99:	ja     3cbb <HUF_decompress4X4_usingDTable_internal+0x1b6b>
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3044, pgot_memcpy_table_func_pgot

```asm
    303d:	lea    (%r12,%rax,4),%r14
    3041:	mov    0x0(%rip),%rax        # 3048 <HUF_decompress4X4_usingDTable_internal+0xef8>
			3044: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3048:	mov    %r14,%rsi
    304b:	call   *%rax
    304d:	movzbl 0x3(%r14),%eax
    3052:	movzbl 0x2(%r14),%ecx
    3057:	mov    $0x2,%edx
    305c:	add    -0x88(%rbp),%ecx
    3062:	add    %rax,%r13
    3065:	mov    -0x90(%rbp),%rax
    306c:	mov    %ecx,-0x88(%rbp)
    3072:	mov    %r13,%rdi
    3075:	shl    %cl,%rax
    3078:	mov    %ebx,%ecx
    307a:	shr    %cl,%rax
    307d:	lea    (%r12,%rax,4),%r14
    3081:	mov    0x0(%rip),%rax        # 3088 <HUF_decompress4X4_usingDTable_internal+0xf38>
			3084: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3084, pgot_memcpy_table_func_pgot

```asm
    307d:	lea    (%r12,%rax,4),%r14
    3081:	mov    0x0(%rip),%rax        # 3088 <HUF_decompress4X4_usingDTable_internal+0xf38>
			3084: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3088:	mov    %r14,%rsi
    308b:	call   *%rax
    308d:	mov    -0x90(%rbp),%rax
    3094:	movzbl 0x2(%r14),%ecx
    3099:	mov    $0x2,%edx
    309e:	add    -0x88(%rbp),%ecx
    30a4:	movzbl 0x3(%r14),%edi
    30a9:	mov    %ecx,-0x88(%rbp)
    30af:	shl    %cl,%rax
    30b2:	mov    %ebx,%ecx
    30b4:	shr    %cl,%rax
    30b7:	add    %rdi,%r13
    30ba:	lea    (%r12,%rax,4),%r14
    30be:	mov    %r13,%rdi
    30c1:	mov    0x0(%rip),%rax        # 30c8 <HUF_decompress4X4_usingDTable_internal+0xf78>
			30c4: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 30c4, pgot_memcpy_table_func_pgot

```asm
    30be:	mov    %r13,%rdi
    30c1:	mov    0x0(%rip),%rax        # 30c8 <HUF_decompress4X4_usingDTable_internal+0xf78>
			30c4: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    30c8:	mov    %r14,%rsi
    30cb:	call   *%rax
    30cd:	mov    -0x90(%rbp),%rax
    30d4:	movzbl 0x2(%r14),%ecx
    30d9:	mov    $0x2,%edx
    30de:	add    -0x88(%rbp),%ecx
    30e4:	movzbl 0x3(%r14),%r8d
    30e9:	mov    %ecx,-0x88(%rbp)
    30ef:	shl    %cl,%rax
    30f2:	mov    %ebx,%ecx
    30f4:	shr    %cl,%rax
    30f7:	add    %r8,%r13
    30fa:	lea    (%r12,%rax,4),%r14
    30fe:	mov    %r13,%rdi
    3101:	mov    0x0(%rip),%rax        # 3108 <HUF_decompress4X4_usingDTable_internal+0xfb8>
			3104: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3104, pgot_memcpy_table_func_pgot

```asm
    30fe:	mov    %r13,%rdi
    3101:	mov    0x0(%rip),%rax        # 3108 <HUF_decompress4X4_usingDTable_internal+0xfb8>
			3104: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3108:	mov    %r14,%rsi
    310b:	call   *%rax
    310d:	movzbl 0x3(%r14),%eax
    3112:	movzbl 0x2(%r14),%ecx
    3117:	add    -0x88(%rbp),%ecx
    311d:	mov    %ecx,-0x88(%rbp)
    3123:	add    %rax,%r13
    3126:	cmp    $0x40,%ecx
    3129:	ja     3168 <HUF_decompress4X4_usingDTable_internal+0x1018>
    312b:	mov    -0x78(%rbp),%rsi
    312f:	mov    -0x80(%rbp),%rax
    3133:	lea    0x8(%rsi),%rdi
    3137:	cmp    %rdi,%rax
    313a:	jb     2fe0 <HUF_decompress4X4_usingDTable_internal+0xe90>
    3140:	mov    %ecx,%edx
    3142:	and    $0x7,%ecx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 31e3, pgot_memcpy_table_func_pgot

```asm
    31dc:	lea    (%r12,%rax,4),%r15
    31e0:	mov    0x0(%rip),%rax        # 31e7 <HUF_decompress4X4_usingDTable_internal+0x1097>
			31e3: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    31e7:	mov    %r15,%rsi
    31ea:	call   *%rax
    31ec:	movzbl 0x3(%r15),%eax
    31f1:	movzbl 0x2(%r15),%ecx
    31f6:	add    -0x88(%rbp),%ecx
    31fc:	add    %rax,%r14
    31ff:	mov    %ecx,-0x88(%rbp)
    3205:	cmp    %rbx,%r14
    3208:	jbe    31c4 <HUF_decompress4X4_usingDTable_internal+0x1074>
    320a:	mov    %r14,%r15
    320d:	mov    -0xc0(%rbp),%r13
    3214:	mov    -0xb8(%rbp),%r14
    321b:	cmp    %r15,-0xf0(%rbp)
    3222:	ja     3c9e <HUF_decompress4X4_usingDTable_internal+0x1b4e>
    3228:	mov    -0x68(%rbp),%ecx
    322b:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 32b4, pgot_memcpy_table_func_pgot

```asm
    32ad:	lea    (%r12,%rax,4),%r15
    32b1:	mov    0x0(%rip),%rax        # 32b8 <HUF_decompress4X4_usingDTable_internal+0x1168>
			32b4: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    32b8:	mov    %r15,%rsi
    32bb:	call   *%rax
    32bd:	movzbl 0x3(%r15),%eax
    32c2:	movzbl 0x2(%r15),%ecx
    32c7:	mov    $0x2,%edx
    32cc:	add    -0x68(%rbp),%ecx
    32cf:	add    %rax,%r14
    32d2:	mov    -0x70(%rbp),%rax
    32d6:	mov    %ecx,-0x68(%rbp)
    32d9:	mov    %r14,%rdi
    32dc:	shl    %cl,%rax
    32df:	mov    %ebx,%ecx
    32e1:	shr    %cl,%rax
    32e4:	lea    (%r12,%rax,4),%r15
    32e8:	mov    0x0(%rip),%rax        # 32ef <HUF_decompress4X4_usingDTable_internal+0x119f>
			32eb: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 32eb, pgot_memcpy_table_func_pgot

```asm
    32e4:	lea    (%r12,%rax,4),%r15
    32e8:	mov    0x0(%rip),%rax        # 32ef <HUF_decompress4X4_usingDTable_internal+0x119f>
			32eb: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    32ef:	mov    %r15,%rsi
    32f2:	call   *%rax
    32f4:	movzbl 0x3(%r15),%eax
    32f9:	movzbl 0x2(%r15),%ecx
    32fe:	mov    $0x2,%edx
    3303:	add    -0x68(%rbp),%ecx
    3306:	add    %rax,%r14
    3309:	mov    -0x70(%rbp),%rax
    330d:	mov    %ecx,-0x68(%rbp)
    3310:	mov    %r14,%rdi
    3313:	shl    %cl,%rax
    3316:	mov    %ebx,%ecx
    3318:	shr    %cl,%rax
    331b:	lea    (%r12,%rax,4),%r15
    331f:	mov    0x0(%rip),%rax        # 3326 <HUF_decompress4X4_usingDTable_internal+0x11d6>
			3322: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3322, pgot_memcpy_table_func_pgot

```asm
    331b:	lea    (%r12,%rax,4),%r15
    331f:	mov    0x0(%rip),%rax        # 3326 <HUF_decompress4X4_usingDTable_internal+0x11d6>
			3322: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3326:	mov    %r15,%rsi
    3329:	call   *%rax
    332b:	mov    -0x70(%rbp),%rax
    332f:	movzbl 0x2(%r15),%ecx
    3334:	mov    $0x2,%edx
    3339:	add    -0x68(%rbp),%ecx
    333c:	movzbl 0x3(%r15),%edi
    3341:	mov    %ecx,-0x68(%rbp)
    3344:	shl    %cl,%rax
    3347:	mov    %ebx,%ecx
    3349:	shr    %cl,%rax
    334c:	lea    (%r14,%rdi,1),%r15
    3350:	lea    (%r12,%rax,4),%r14
    3354:	mov    %r15,%rdi
    3357:	mov    0x0(%rip),%rax        # 335e <HUF_decompress4X4_usingDTable_internal+0x120e>
			335a: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 335a, pgot_memcpy_table_func_pgot

```asm
    3354:	mov    %r15,%rdi
    3357:	mov    0x0(%rip),%rax        # 335e <HUF_decompress4X4_usingDTable_internal+0x120e>
			335a: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    335e:	mov    %r14,%rsi
    3361:	call   *%rax
    3363:	movzbl 0x3(%r14),%eax
    3368:	movzbl 0x2(%r14),%ecx
    336d:	add    -0x68(%rbp),%ecx
    3370:	mov    %ecx,-0x68(%rbp)
    3373:	lea    (%r15,%rax,1),%r14
    3377:	cmp    $0x40,%ecx
    337a:	ja     379a <HUF_decompress4X4_usingDTable_internal+0x164a>
    3380:	mov    -0x58(%rbp),%rsi
    3384:	mov    -0x60(%rbp),%rax
    3388:	lea    0x8(%rsi),%rdi
    338c:	cmp    %rdi,%rax
    338f:	jb     3256 <HUF_decompress4X4_usingDTable_internal+0x1106>
    3395:	mov    %ecx,%edx
    3397:	and    $0x7,%ecx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 344b, pgot_memcpy_table_func_pgot

```asm
    3444:	lea    (%r12,%rax,4),%r15
    3448:	mov    0x0(%rip),%rax        # 344f <HUF_decompress4X4_usingDTable_internal+0x12ff>
			344b: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    344f:	mov    %r15,%rsi
    3452:	call   *%rax
    3454:	movzbl 0x3(%r15),%edx
    3459:	movzbl 0x2(%r15),%eax
    345e:	add    -0x68(%rbp),%eax
    3461:	mov    %eax,-0x68(%rbp)
    3464:	add    %rdx,%r14
    3467:	cmp    $0x40,%eax
    346a:	ja     37a5 <HUF_decompress4X4_usingDTable_internal+0x1655>
    3470:	mov    -0x58(%rbp),%rsi
    3474:	lea    0x8(%rsi),%rdi
    3478:	mov    -0x60(%rbp),%rdx
    347c:	cmp    %rdi,%rdx
    347f:	jb     33eb <HUF_decompress4X4_usingDTable_internal+0x129b>
    3485:	mov    %eax,%ecx
    3487:	and    $0x7,%eax
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 35d4, pgot_memcpy_table_func_pgot

```asm
    35cd:	lea    (%r12,%rax,4),%r13
    35d1:	mov    0x0(%rip),%rax        # 35d8 <HUF_decompress4X4_usingDTable_internal+0x1488>
			35d4: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    35d8:	mov    %r13,%rsi
    35db:	call   *%rax
    35dd:	movzbl 0x3(%r13),%edx
    35e2:	movzbl 0x2(%r13),%eax
    35e7:	add    -0xa8(%rbp),%eax
    35ed:	mov    %eax,-0xa8(%rbp)
    35f3:	add    %rdx,%rbx
    35f6:	cmp    $0x40,%eax
    35f9:	ja     3640 <HUF_decompress4X4_usingDTable_internal+0x14f0>
    35fb:	mov    -0x98(%rbp),%rsi
    3602:	lea    0x8(%rsi),%rdi
    3606:	mov    -0xa0(%rbp),%rdx
    360d:	cmp    %rdi,%rdx
    3610:	jb     3564 <HUF_decompress4X4_usingDTable_internal+0x1414>
    3616:	mov    %eax,%ecx
    3618:	and    $0x7,%eax
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 371e, pgot_memcpy_table_func_pgot

```asm
    3717:	lea    (%r12,%rax,4),%rbx
    371b:	mov    0x0(%rip),%rax        # 3722 <HUF_decompress4X4_usingDTable_internal+0x15d2>
			371e: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3722:	mov    %rbx,%rsi
    3725:	call   *%rax
    3727:	movzbl 0x3(%rbx),%edx
    372b:	movzbl 0x2(%rbx),%eax
    372f:	add    -0x88(%rbp),%eax
    3735:	mov    %eax,-0x88(%rbp)
    373b:	add    %rdx,%r15
    373e:	cmp    $0x40,%eax
    3741:	ja     318a <HUF_decompress4X4_usingDTable_internal+0x103a>
    3747:	mov    -0x78(%rbp),%rsi
    374b:	lea    0x8(%rsi),%rdi
    374f:	mov    -0x80(%rbp),%rdx
    3753:	cmp    %rdi,%rdx
    3756:	jb     36b1 <HUF_decompress4X4_usingDTable_internal+0x1561>
    375c:	mov    %eax,%ecx
    375e:	and    $0x7,%eax
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 37de, pgot_memcpy_table_func_pgot

```asm
    37d7:	lea    (%r12,%rax,4),%r13
    37db:	mov    0x0(%rip),%rax        # 37e2 <HUF_decompress4X4_usingDTable_internal+0x1692>
			37de: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    37e2:	mov    %r13,%rsi
    37e5:	call   *%rax
    37e7:	movzbl 0x3(%r13),%eax
    37ec:	movzbl 0x2(%r13),%ecx
    37f1:	add    -0x68(%rbp),%ecx
    37f4:	add    %rax,%r14
    37f7:	mov    %ecx,-0x68(%rbp)
    37fa:	cmp    %rbx,%r14
    37fd:	jbe    37c2 <HUF_decompress4X4_usingDTable_internal+0x1672>
    37ff:	mov    -0xb8(%rbp),%r13
    3806:	cmp    %r14,-0xf8(%rbp)
    380d:	ja     3c84 <HUF_decompress4X4_usingDTable_internal+0x1b34>
    3813:	mov    -0x48(%rbp),%ecx
    3816:	cmp    $0x40,%ecx
    3819:	ja     3a9a <HUF_decompress4X4_usingDTable_internal+0x194a>
    381f:	mov    -0xdc(%rbp),%ebx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3890, pgot_memcpy_table_func_pgot

```asm
    3889:	lea    (%r12,%rax,4),%r15
    388d:	mov    0x0(%rip),%rax        # 3894 <HUF_decompress4X4_usingDTable_internal+0x1744>
			3890: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3894:	mov    %r15,%rsi
    3897:	call   *%rax
    3899:	movzbl 0x3(%r15),%eax
    389e:	movzbl 0x2(%r15),%ecx
    38a3:	mov    $0x2,%edx
    38a8:	add    -0x48(%rbp),%ecx
    38ab:	add    %rax,%r13
    38ae:	mov    -0x50(%rbp),%rax
    38b2:	mov    %ecx,-0x48(%rbp)
    38b5:	mov    %r13,%rdi
    38b8:	shl    %cl,%rax
    38bb:	mov    %ebx,%ecx
    38bd:	shr    %cl,%rax
    38c0:	lea    (%r12,%rax,4),%r15
    38c4:	mov    0x0(%rip),%rax        # 38cb <HUF_decompress4X4_usingDTable_internal+0x177b>
			38c7: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 38c7, pgot_memcpy_table_func_pgot

```asm
    38c0:	lea    (%r12,%rax,4),%r15
    38c4:	mov    0x0(%rip),%rax        # 38cb <HUF_decompress4X4_usingDTable_internal+0x177b>
			38c7: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    38cb:	mov    %r15,%rsi
    38ce:	call   *%rax
    38d0:	movzbl 0x3(%r15),%eax
    38d5:	movzbl 0x2(%r15),%ecx
    38da:	mov    $0x2,%edx
    38df:	add    -0x48(%rbp),%ecx
    38e2:	add    %rax,%r13
    38e5:	mov    -0x50(%rbp),%rax
    38e9:	mov    %ecx,-0x48(%rbp)
    38ec:	mov    %r13,%rdi
    38ef:	shl    %cl,%rax
    38f2:	mov    %ebx,%ecx
    38f4:	shr    %cl,%rax
    38f7:	lea    (%r12,%rax,4),%r15
    38fb:	mov    0x0(%rip),%rax        # 3902 <HUF_decompress4X4_usingDTable_internal+0x17b2>
			38fe: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 38fe, pgot_memcpy_table_func_pgot

```asm
    38f7:	lea    (%r12,%rax,4),%r15
    38fb:	mov    0x0(%rip),%rax        # 3902 <HUF_decompress4X4_usingDTable_internal+0x17b2>
			38fe: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3902:	mov    %r15,%rsi
    3905:	call   *%rax
    3907:	movzbl 0x3(%r15),%eax
    390c:	movzbl 0x2(%r15),%ecx
    3911:	mov    $0x2,%edx
    3916:	add    -0x48(%rbp),%ecx
    3919:	add    %rax,%r13
    391c:	mov    -0x50(%rbp),%rax
    3920:	mov    %ecx,-0x48(%rbp)
    3923:	mov    %r13,%rdi
    3926:	shl    %cl,%rax
    3929:	mov    %ebx,%ecx
    392b:	shr    %cl,%rax
    392e:	lea    (%r12,%rax,4),%r15
    3932:	mov    0x0(%rip),%rax        # 3939 <HUF_decompress4X4_usingDTable_internal+0x17e9>
			3935: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3935, pgot_memcpy_table_func_pgot

```asm
    392e:	lea    (%r12,%rax,4),%r15
    3932:	mov    0x0(%rip),%rax        # 3939 <HUF_decompress4X4_usingDTable_internal+0x17e9>
			3935: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3939:	mov    %r15,%rsi
    393c:	call   *%rax
    393e:	movzbl 0x3(%r15),%eax
    3943:	movzbl 0x2(%r15),%ecx
    3948:	add    -0x48(%rbp),%ecx
    394b:	mov    %ecx,-0x48(%rbp)
    394e:	add    %rax,%r13
    3951:	cmp    $0x40,%ecx
    3954:	ja     3a9a <HUF_decompress4X4_usingDTable_internal+0x194a>
    395a:	mov    -0x38(%rbp),%rsi
    395e:	mov    -0x40(%rbp),%rax
    3962:	lea    0x8(%rsi),%rdi
    3966:	cmp    %rdi,%rax
    3969:	jb     3836 <HUF_decompress4X4_usingDTable_internal+0x16e6>
    396f:	mov    %ecx,%edx
    3971:	and    $0x7,%ecx
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3a16, pgot_memcpy_table_func_pgot

```asm
    3a0f:	lea    (%r12,%rax,4),%r15
    3a13:	mov    0x0(%rip),%rax        # 3a1a <HUF_decompress4X4_usingDTable_internal+0x18ca>
			3a16: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3a1a:	mov    %r15,%rsi
    3a1d:	call   *%rax
    3a1f:	movzbl 0x3(%r15),%edx
    3a24:	movzbl 0x2(%r15),%eax
    3a29:	add    -0x48(%rbp),%eax
    3a2c:	mov    %eax,-0x48(%rbp)
    3a2f:	add    %rdx,%r13
    3a32:	cmp    $0x40,%eax
    3a35:	ja     3aa5 <HUF_decompress4X4_usingDTable_internal+0x1955>
    3a37:	mov    -0x38(%rbp),%rsi
    3a3b:	lea    0x8(%rsi),%rdi
    3a3f:	mov    -0x40(%rbp),%rdx
    3a43:	cmp    %rdi,%rdx
    3a46:	jb     39ba <HUF_decompress4X4_usingDTable_internal+0x186a>
    3a4c:	mov    %eax,%ecx
    3a4e:	and    $0x7,%eax
```

## 04_zstd_decompress/no_retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3ad7, pgot_memcpy_table_func_pgot

```asm
    3ad0:	lea    (%r12,%rax,4),%r15
    3ad4:	mov    0x0(%rip),%rax        # 3adb <HUF_decompress4X4_usingDTable_internal+0x198b>
			3ad7: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3adb:	mov    %r15,%rsi
    3ade:	call   *%rax
    3ae0:	movzbl 0x3(%r15),%eax
    3ae5:	movzbl 0x2(%r15),%ecx
    3aea:	add    -0x48(%rbp),%ecx
    3aed:	add    %rax,%r13
    3af0:	mov    %ecx,-0x48(%rbp)
    3af3:	cmp    %rbx,%r13
    3af6:	jbe    3abb <HUF_decompress4X4_usingDTable_internal+0x196b>
    3af8:	cmp    %r13,-0x100(%rbp)
    3aff:	ja     3c6a <HUF_decompress4X4_usingDTable_internal+0x1b1a>
    3b05:	mov    -0x98(%rbp),%rbx
    3b0c:	xor    %eax,%eax
    3b0e:	cmp    %rbx,-0xa0(%rbp)
    3b15:	je     3ce9 <HUF_decompress4X4_usingDTable_internal+0x1b99>
    3b1b:	mov    -0x78(%rbp),%rbx
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_readDTableX2_wksp_func_pgot, 3da0, pgot_memcpy_table_func_pgot

```asm
    3d98:	mov    $0x4,%edx
    3d9d:	mov    0x0(%rip),%rax        # 3da4 <pgot_HUF_readDTableX2_wksp_func_pgot+0xa4>
			3da0: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3da4:	mov    %rbx,%rsi
    3da7:	lea    -0x34(%rbp),%rdi
    3dab:	call   *%rax
    3dad:	movzbl -0x34(%rbp),%eax
    3db1:	mov    -0x3c(%rbp),%edx
    3db4:	add    $0x1,%eax
    3db7:	cmp    %edx,%eax
    3db9:	jb     3eaf <pgot_HUF_readDTableX2_wksp_func_pgot+0x1af>
    3dbf:	mov    %dl,-0x32(%rbp)
    3dc2:	lea    -0x34(%rbp),%rsi
    3dc6:	mov    %rbx,%rdi
    3dc9:	mov    0x0(%rip),%rax        # 3dd0 <pgot_HUF_readDTableX2_wksp_func_pgot+0xd0>
			3dcc: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3dd0:	movb   $0x0,-0x33(%rbp)
    3dd4:	mov    $0x4,%edx
    3dd9:	call   *%rax
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_readDTableX2_wksp_func_pgot, 3dcc, pgot_memcpy_table_func_pgot

```asm
    3dc6:	mov    %rbx,%rdi
    3dc9:	mov    0x0(%rip),%rax        # 3dd0 <pgot_HUF_readDTableX2_wksp_func_pgot+0xd0>
			3dcc: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3dd0:	movb   $0x0,-0x33(%rbp)
    3dd4:	mov    $0x4,%edx
    3dd9:	call   *%rax
    3ddb:	mov    -0x3c(%rbp),%r9d
    3ddf:	lea    0x1(%r9),%esi
    3de3:	cmp    $0x1,%esi
    3de6:	jbe    3e2a <pgot_HUF_readDTableX2_wksp_func_pgot+0x12a>
    3de8:	mov    0x4(%r12),%r10d
    3ded:	lea    0x4(%r12),%r8
    3df2:	xor    %edx,%edx
    3df4:	mov    $0x1,%eax
    3df9:	jmp    3e13 <pgot_HUF_readDTableX2_wksp_func_pgot+0x113>
    3dfb:	mov    %r11d,%edx
    3dfe:	lea    (%r12,%rdx,4),%r8
    3e02:	mov    (%r8),%r10d
    3e05:	cmp    $0x1f,%eax
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_decompress1X2_usingDTable_func_pgot, 3f03, pgot_memcpy_table_func_pgot

```asm
    3efe:	xor    %eax,%eax
    3f00:	mov    0x0(%rip),%rax        # 3f07 <pgot_HUF_decompress1X2_usingDTable_func_pgot+0x47>
			3f03: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3f07:	call   *%rax
    3f09:	cmpb   $0x0,-0x33(%rbp)
    3f0d:	mov    $0xffffffffffffffff,%rax
    3f14:	jne    3f2a <pgot_HUF_decompress1X2_usingDTable_func_pgot+0x6a>
    3f16:	mov    %rbx,%r8
    3f19:	mov    %r15,%rcx
    3f1c:	mov    %r14,%rdx
    3f1f:	mov    %r13,%rsi
    3f22:	mov    %r12,%rdi
    3f25:	call   3e0 <HUF_decompress1X2_usingDTable_internal>
    3f2a:	mov    -0x30(%rbp),%rdx
    3f2e:	sub    %gs:0x28,%rdx
    3f37:	jne    3f49 <pgot_HUF_decompress1X2_usingDTable_func_pgot+0x89>
    3f39:	add    $0x10,%rsp
    3f3d:	pop    %rbx
    3f3e:	pop    %r12
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_decompress4X2_usingDTable_func_pgot, 4023, pgot_memcpy_table_func_pgot

```asm
    401e:	xor    %eax,%eax
    4020:	mov    0x0(%rip),%rax        # 4027 <pgot_HUF_decompress4X2_usingDTable_func_pgot+0x47>
			4023: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4027:	call   *%rax
    4029:	cmpb   $0x0,-0x33(%rbp)
    402d:	mov    $0xffffffffffffffff,%rax
    4034:	jne    404a <pgot_HUF_decompress4X2_usingDTable_func_pgot+0x6a>
    4036:	mov    %rbx,%r8
    4039:	mov    %r15,%rcx
    403c:	mov    %r14,%rdx
    403f:	mov    %r13,%rsi
    4042:	mov    %r12,%rdi
    4045:	call   ad0 <HUF_decompress4X2_usingDTable_internal>
    404a:	mov    -0x30(%rbp),%rdx
    404e:	sub    %gs:0x28,%rdx
    4057:	jne    4069 <pgot_HUF_decompress4X2_usingDTable_func_pgot+0x89>
    4059:	add    $0x10,%rsp
    405d:	pop    %rbx
    405e:	pop    %r12
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_readDTableX4_wksp_func_pgot, 4148, pgot_memcpy_table_func_pgot

```asm
    4143:	xor    %eax,%eax
    4145:	mov    0x0(%rip),%rax        # 414c <pgot_HUF_readDTableX4_wksp_func_pgot+0x4c>
			4148: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    414c:	call   *%rax
    414e:	movzbl -0x68(%rbp),%r12d
    4153:	mov    %r12b,-0xbd(%rbp)
    415a:	cmp    $0x5db,%rbx
    4161:	jbe    4501 <pgot_HUF_readDTableX4_wksp_func_pgot+0x401>
    4167:	lea    0x270(%r14),%r15
    416e:	xor    %esi,%esi
    4170:	mov    $0x6c,%edx
    4175:	mov    0x0(%rip),%rax        # 417c <pgot_HUF_readDTableX4_wksp_func_pgot+0x7c>
			4178: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    417c:	mov    %r15,%rdi
    417f:	call   *%rax
    4181:	cmp    $0xc,%r12d
    4185:	ja     4501 <pgot_HUF_readDTableX4_wksp_func_pgot+0x401>
    418b:	mov    %r13,%r9
    418e:	lea    -0x70(%rbp),%r8
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_readDTableX4_wksp_func_pgot, 4178, pgot_memset_table_func_pgot

```asm
    4170:	mov    $0x6c,%edx
    4175:	mov    0x0(%rip),%rax        # 417c <pgot_HUF_readDTableX4_wksp_func_pgot+0x7c>
			4178: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    417c:	mov    %r15,%rdi
    417f:	call   *%rax
    4181:	cmp    $0xc,%r12d
    4185:	ja     4501 <pgot_HUF_readDTableX4_wksp_func_pgot+0x401>
    418b:	mov    %r13,%r9
    418e:	lea    -0x70(%rbp),%r8
    4192:	lea    -0x6c(%rbp),%rcx
    4196:	mov    %r15,%rdx
    4199:	lea    0x5dc(%r14),%rax
    41a0:	sub    $0x5dc,%rbx
    41a7:	mov    $0x100,%esi
    41ac:	push   %rbx
    41ad:	lea    0x4dc(%r14),%rdi
    41b4:	push   %rax
    41b5:	push   -0x80(%rbp)
    41b8:	call   41bd <pgot_HUF_readDTableX4_wksp_func_pgot+0xbd>
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_readDTableX4_wksp_func_pgot, 4388, pgot_memcpy_table_func_pgot

```asm
    437f:	mov    %eax,-0xb8(%rbp)
    4385:	mov    0x0(%rip),%rax        # 438c <pgot_HUF_readDTableX4_wksp_func_pgot+0x28c>
			4388: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    438c:	call   *%rax
    438e:	mov    -0x84(%rbp),%r10d
    4395:	test   %r10d,%r10d
    4398:	je     4536 <pgot_HUF_readDTableX4_wksp_func_pgot+0x436>
    439e:	lea    -0x1(%r10),%eax
    43a2:	sub    %ebx,%r12d
    43a5:	mov    %r14,%r11
    43a8:	mov    %r10d,-0xbc(%rbp)
    43af:	lea    0x2de(%r14,%rax,2),%rax
    43b7:	mov    %r12d,-0x88(%rbp)
    43be:	mov    -0xb0(%rbp),%r15
    43c5:	mov    %ebx,%r10d
    43c8:	mov    %rax,-0xa0(%rbp)
    43cf:	jmp    4485 <pgot_HUF_readDTableX4_wksp_func_pgot+0x385>
    43d4:	mov    %eax,-0x98(%rbp)
    43da:	mov    -0xb8(%rbp),%eax
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_readDTableX4_wksp_func_pgot, 4554, pgot_memcpy_table_func_pgot

```asm
    454e:	mov    %al,-0x66(%rbp)
    4551:	mov    0x0(%rip),%rax        # 4558 <pgot_HUF_readDTableX4_wksp_func_pgot+0x458>
			4554: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4558:	call   *%rax
    455a:	jmp    450c <pgot_HUF_readDTableX4_wksp_func_pgot+0x40c>
    455c:	lea    0x1(%r11),%r8d
    4560:	mov    %r11d,%eax
    4563:	jmp    420b <pgot_HUF_readDTableX4_wksp_func_pgot+0x10b>
    4568:	mov    -0x6c(%rbp),%ebx
    456b:	lea    0x2dc(%r14),%rsi
    4572:	xor    %r10d,%r10d
    4575:	movl   $0x0,0x2a8(%r14)
    4580:	mov    %rsi,-0xb0(%rbp)
    4587:	test   %ebx,%ebx
    4589:	jne    4265 <pgot_HUF_readDTableX4_wksp_func_pgot+0x165>
    458f:	jmp    42f2 <pgot_HUF_readDTableX4_wksp_func_pgot+0x1f2>
    4594:	movl   $0x0,0x2a8(%r14)
    459f:	mov    %r12d,%ecx
    45a2:	sub    %r11d,%ecx
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_decompress1X4_usingDTable_func_pgot, 4663, pgot_memcpy_table_func_pgot

```asm
    465e:	xor    %eax,%eax
    4660:	mov    0x0(%rip),%rax        # 4667 <pgot_HUF_decompress1X4_usingDTable_func_pgot+0x47>
			4663: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4667:	call   *%rax
    4669:	cmpb   $0x1,-0x33(%rbp)
    466d:	mov    $0xffffffffffffffff,%rax
    4674:	jne    468a <pgot_HUF_decompress1X4_usingDTable_func_pgot+0x6a>
    4676:	mov    %rbx,%r8
    4679:	mov    %r15,%rcx
    467c:	mov    %r14,%rdx
    467f:	mov    %r13,%rsi
    4682:	mov    %r12,%rdi
    4685:	call   720 <HUF_decompress1X4_usingDTable_internal>
    468a:	mov    -0x30(%rbp),%rdx
    468e:	sub    %gs:0x28,%rdx
    4697:	jne    46a9 <pgot_HUF_decompress1X4_usingDTable_func_pgot+0x89>
    4699:	add    $0x10,%rsp
    469d:	pop    %rbx
    469e:	pop    %r12
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_decompress4X4_usingDTable_func_pgot, 4783, pgot_memcpy_table_func_pgot

```asm
    477e:	xor    %eax,%eax
    4780:	mov    0x0(%rip),%rax        # 4787 <pgot_HUF_decompress4X4_usingDTable_func_pgot+0x47>
			4783: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4787:	call   *%rax
    4789:	cmpb   $0x1,-0x33(%rbp)
    478d:	mov    $0xffffffffffffffff,%rax
    4794:	jne    47aa <pgot_HUF_decompress4X4_usingDTable_func_pgot+0x6a>
    4796:	mov    %rbx,%r8
    4799:	mov    %r15,%rcx
    479c:	mov    %r14,%rdx
    479f:	mov    %r13,%rsi
    47a2:	mov    %r12,%rdi
    47a5:	call   2150 <HUF_decompress4X4_usingDTable_internal>
    47aa:	mov    -0x30(%rbp),%rdx
    47ae:	sub    %gs:0x28,%rdx
    47b7:	jne    47c9 <pgot_HUF_decompress4X4_usingDTable_func_pgot+0x89>
    47b9:	add    $0x10,%rsp
    47bd:	pop    %rbx
    47be:	pop    %r12
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_decompress1X_usingDTable_func_pgot, 48a3, pgot_memcpy_table_func_pgot

```asm
    489e:	xor    %eax,%eax
    48a0:	mov    0x0(%rip),%rax        # 48a7 <pgot_HUF_decompress1X_usingDTable_func_pgot+0x47>
			48a3: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    48a7:	call   *%rax
    48a9:	cmpb   $0x0,-0x33(%rbp)
    48ad:	mov    %rbx,%r8
    48b0:	mov    %r15,%rcx
    48b3:	mov    %r14,%rdx
    48b6:	mov    %r13,%rsi
    48b9:	mov    %r12,%rdi
    48bc:	je     48e2 <pgot_HUF_decompress1X_usingDTable_func_pgot+0x82>
    48be:	call   720 <HUF_decompress1X4_usingDTable_internal>
    48c3:	mov    -0x30(%rbp),%rdx
    48c7:	sub    %gs:0x28,%rdx
    48d0:	jne    48e9 <pgot_HUF_decompress1X_usingDTable_func_pgot+0x89>
    48d2:	add    $0x10,%rsp
    48d6:	pop    %rbx
    48d7:	pop    %r12
    48d9:	pop    %r13
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_decompress4X_usingDTable_func_pgot, 4933, pgot_memcpy_table_func_pgot

```asm
    492e:	xor    %eax,%eax
    4930:	mov    0x0(%rip),%rax        # 4937 <pgot_HUF_decompress4X_usingDTable_func_pgot+0x47>
			4933: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4937:	call   *%rax
    4939:	cmpb   $0x0,-0x33(%rbp)
    493d:	mov    %rbx,%r8
    4940:	mov    %r15,%rcx
    4943:	mov    %r14,%rdx
    4946:	mov    %r13,%rsi
    4949:	mov    %r12,%rdi
    494c:	je     4972 <pgot_HUF_decompress4X_usingDTable_func_pgot+0x82>
    494e:	call   2150 <HUF_decompress4X4_usingDTable_internal>
    4953:	mov    -0x30(%rbp),%rdx
    4957:	sub    %gs:0x28,%rdx
    4960:	jne    4979 <pgot_HUF_decompress4X_usingDTable_func_pgot+0x89>
    4962:	add    $0x10,%rsp
    4966:	pop    %rbx
    4967:	pop    %r12
    4969:	pop    %r13
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_decompress4X_DCtx_wksp_func_pgot, 4bd8, pgot_memcpy_table_func_pgot

```asm
    4bd3:	jmp    4b8b <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x12b>
    4bd5:	mov    0x0(%rip),%rax        # 4bdc <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x17c>
			4bd8: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4bdc:	mov    %rcx,%rsi
    4bdf:	mov    %r10,%rdi
    4be2:	mov    %r12,%r13
    4be5:	call   *%rax
    4be7:	jmp    4b8b <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x12b>
    4be9:	movzbl (%rcx),%esi
    4bec:	mov    0x0(%rip),%rax        # 4bf3 <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x193>
			4bef: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    4bf3:	mov    %r10,%rdi
    4bf6:	mov    %r12,%r13
    4bf9:	call   *%rax
    4bfb:	jmp    4b8b <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x12b>
    4bfd:	mov    $0xfffffffffffffff3,%r13
    4c04:	jmp    4b8b <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x12b>
    4c06:	mov    %r13,%rsi
    4c09:	mov    $0x0,%rdi
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_decompress4X_DCtx_wksp_func_pgot, 4bef, pgot_memset_table_func_pgot

```asm
    4be9:	movzbl (%rcx),%esi
    4bec:	mov    0x0(%rip),%rax        # 4bf3 <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x193>
			4bef: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    4bf3:	mov    %r10,%rdi
    4bf6:	mov    %r12,%r13
    4bf9:	call   *%rax
    4bfb:	jmp    4b8b <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x12b>
    4bfd:	mov    $0xfffffffffffffff3,%r13
    4c04:	jmp    4b8b <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x12b>
    4c06:	mov    %r13,%rsi
    4c09:	mov    $0x0,%rdi
			4c0c: R_X86_64_32S	.data+0x100
    4c10:	mov    %rdx,-0x50(%rbp)
    4c14:	mov    %r9,-0x48(%rbp)
    4c18:	mov    %r10,-0x40(%rbp)
    4c1c:	mov    %r8d,-0x38(%rbp)
    4c20:	mov    %eax,-0x30(%rbp)
    4c23:	call   4c28 <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x1c8>
			4c24: R_X86_64_PLT32	__ubsan_handle_out_of_bounds-0x4
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_decompress1X_DCtx_wksp_func_pgot, 50a8, pgot_memcpy_table_func_pgot

```asm
    50a3:	jmp    505b <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x12b>
    50a5:	mov    0x0(%rip),%rax        # 50ac <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x17c>
			50a8: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    50ac:	mov    %rcx,%rsi
    50af:	mov    %r10,%rdi
    50b2:	mov    %r12,%r13
    50b5:	call   *%rax
    50b7:	jmp    505b <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x12b>
    50b9:	movzbl (%rcx),%esi
    50bc:	mov    0x0(%rip),%rax        # 50c3 <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x193>
			50bf: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    50c3:	mov    %r10,%rdi
    50c6:	mov    %r12,%r13
    50c9:	call   *%rax
    50cb:	jmp    505b <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x12b>
    50cd:	mov    $0xfffffffffffffff3,%r13
    50d4:	jmp    505b <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x12b>
    50d6:	mov    %r13,%rsi
    50d9:	mov    $0x0,%rdi
```

## 04_zstd_decompress/no_retpoline/func_pgot: pgot_HUF_decompress1X_DCtx_wksp_func_pgot, 50bf, pgot_memset_table_func_pgot

```asm
    50b9:	movzbl (%rcx),%esi
    50bc:	mov    0x0(%rip),%rax        # 50c3 <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x193>
			50bf: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    50c3:	mov    %r10,%rdi
    50c6:	mov    %r12,%r13
    50c9:	call   *%rax
    50cb:	jmp    505b <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x12b>
    50cd:	mov    $0xfffffffffffffff3,%r13
    50d4:	jmp    505b <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x12b>
    50d6:	mov    %r13,%rsi
    50d9:	mov    $0x0,%rdi
			50dc: R_X86_64_32S	.data
    50e0:	mov    %rdx,-0x50(%rbp)
    50e4:	mov    %r9,-0x48(%rbp)
    50e8:	mov    %r10,-0x40(%rbp)
    50ec:	mov    %r8d,-0x38(%rbp)
    50f0:	mov    %eax,-0x30(%rbp)
    50f3:	call   50f8 <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x1c8>
			50f4: R_X86_64_PLT32	__ubsan_handle_out_of_bounds-0x4
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_execSequenceLast7_origin.isra.0, 5e6, memmove

```asm
     5e2:	mov    %r13,%rdx
     5e5:	call   5ea <pgot_ZSTD_execSequenceLast7_origin.isra.0+0xea>
			5e6: R_X86_64_PLT32	memmove-0x4
     5ea:	mov    0x18(%rbp),%rsi
     5ee:	lea    (%rax,%r13,1),%rax
     5f2:	cmp    %rax,%rbx
     5f5:	jbe    61e <pgot_ZSTD_execSequenceLast7_origin.isra.0+0x11e>
     5f7:	sub    %rax,%rbx
     5fa:	xor    %edx,%edx
     5fc:	movzbl (%rsi,%rdx,1),%ecx
     600:	mov    %cl,(%rax,%rdx,1)
     603:	add    $0x1,%rdx
     607:	cmp    %rbx,%rdx
     60a:	jne    5fc <pgot_ZSTD_execSequenceLast7_origin.isra.0+0xfc>
     60c:	pop    %rbx
     60d:	mov    %r12,%rax
     610:	pop    %r12
     612:	pop    %r13
     614:	pop    %rbp
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_execSequenceLast7_origin.isra.0, 65f, memmove

```asm
     65b:	mov    %r10,%rdx
     65e:	call   663 <pgot_ZSTD_execSequenceLast7_origin.isra.0+0x163>
			65f: R_X86_64_PLT32	memmove-0x4
     663:	jmp    61e <pgot_ZSTD_execSequenceLast7_origin.isra.0+0x11e>
     665:	data16 cs nopw 0x0(%rax,%rax,1)

```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_copyDCtx_origin, def, memcpy

```asm
     deb:	mov    %rsp,%rbp
     dee:	call   df3 <pgot_ZSTD_copyDCtx_origin+0x13>
			def: R_X86_64_PLT32	memcpy-0x4
     df3:	pop    %rbp
     df4:	ret    
     df5:	int3   
     df6:	cs nopw 0x0(%rax,%rax,1)

```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_decodeLiteralsBlock_origin, 1282, memcpy

```asm
    127e:	mov    %rcx,%rdi
    1281:	call   1286 <pgot_ZSTD_decodeLiteralsBlock_origin+0x96>
			1282: R_X86_64_PLT32	memcpy-0x4
    1286:	mov    %rbx,0x6110(%r12)
    128e:	mov    %rax,0x60f0(%r12)
    1296:	movq   $0x0,(%rax,%rbx,1)
    129e:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_origin+0x104>
    12a0:	mov    0x6088(%r12),%esi
    12a8:	mov    $0xffffffffffffffed,%r13
    12af:	test   %esi,%esi
    12b1:	je     12f4 <pgot_ZSTD_decodeLiteralsBlock_origin+0x104>
    12b3:	cmp    $0x4,%rdx
    12b7:	jbe    12ed <pgot_ZSTD_decodeLiteralsBlock_origin+0xfd>
    12b9:	mov    (%rdi),%r8d
    12bc:	shr    $0x2,%al
    12bf:	and    $0x3,%eax
    12c2:	mov    %r8d,%ecx
    12c5:	shr    $0x4,%ecx
    12c8:	cmp    $0x2,%al
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_decodeLiteralsBlock_origin, 1427, memset

```asm
    1423:	mov    %rcx,%rdi
    1426:	call   142b <pgot_ZSTD_decodeLiteralsBlock_origin+0x23b>
			1427: R_X86_64_PLT32	memset-0x4
    142b:	mov    %rbx,0x6110(%r12)
    1433:	mov    %rax,0x60f0(%r12)
    143b:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_origin+0x104>
    1440:	add    %rdi,%rsi
    1443:	mov    %rbx,0x6110(%r12)
    144b:	mov    %rsi,0x60f0(%r12)
    1453:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_origin+0x104>
    1458:	movzbl 0x2(%rsi),%ebx
    145c:	movzwl (%rsi),%eax
    145f:	mov    $0x3,%esi
    1464:	shl    $0x10,%ebx
    1467:	add    %eax,%ebx
    1469:	shr    $0x4,%ebx
    146c:	jmp    125a <pgot_ZSTD_decodeLiteralsBlock_origin+0x6a>
    1471:	movzbl 0x2(%rsi),%ebx
    1475:	movzwl (%rsi),%eax
```

## 04_zstd_decompress/no_retpoline/origin: ZSTD_decompressSequencesLong, 1854, memcpy

```asm
    1850:	mov    %r11,%rdi
    1853:	call   1858 <ZSTD_decompressSequencesLong+0x118>
			1854: R_X86_64_PLT32	memcpy-0x4
    1858:	add    %rax,%rbx
    185b:	sub    -0x118(%rbp),%rbx
    1862:	mov    %rbx,%r12
    1865:	mov    -0x38(%rbp),%rax
    1869:	sub    %gs:0x28,%rax
    1872:	jne    24ab <ZSTD_decompressSequencesLong+0xd6b>
    1878:	lea    -0x30(%rbp),%rsp
    187c:	mov    %r12,%rax
    187f:	pop    %rbx
    1880:	pop    %r10
    1882:	pop    %r12
    1884:	pop    %r13
    1886:	pop    %r14
    1888:	pop    %r15
    188a:	pop    %rbp
    188b:	lea    -0x8(%r10),%rsp
```

## 04_zstd_decompress/no_retpoline/origin: ZSTD_decompressSequencesLong, 1d5a, memmove

```asm
    1d52:	mov    %r10,-0x158(%rbp)
    1d59:	call   1d5e <ZSTD_decompressSequencesLong+0x61e>
			1d5a: R_X86_64_PLT32	memmove-0x4
    1d5e:	mov    -0x140(%rbp),%rdx
    1d65:	mov    -0x170(%rbp),%r11
    1d6c:	mov    %rax,%rdi
    1d6f:	mov    -0x178(%rbp),%r9
    1d76:	sub    %rdx,%r11
    1d79:	add    %rdx,%rdi
    1d7c:	cmp    $0x2,%r11
    1d80:	jbe    2464 <ZSTD_decompressSequencesLong+0xd24>
    1d86:	cmp    %r13,%rdi
    1d89:	mov    -0x158(%rbp),%r10
    1d90:	mov    -0x160(%rbp),%r8
    1d97:	mov    %r14,%rsi
    1d9a:	ja     2464 <ZSTD_decompressSequencesLong+0xd24>
    1da0:	cmp    $0x7,%r10
    1da4:	ja     2400 <ZSTD_decompressSequencesLong+0xcc0>
    1daa:	movzbl (%rsi),%eax
```

## 04_zstd_decompress/no_retpoline/origin: ZSTD_decompressSequencesLong, 200e, memmove

```asm
    2006:	mov    %r8,-0x180(%rbp)
    200d:	call   2012 <ZSTD_decompressSequencesLong+0x8d2>
			200e: R_X86_64_PLT32	memmove-0x4
    2012:	mov    -0x170(%rbp),%rcx
    2019:	mov    -0x158(%rbp),%r9
    2020:	mov    %rax,%rdi
    2023:	mov    -0x178(%rbp),%r10d
    202a:	add    %rbx,%rdi
    202d:	sub    %rbx,%rcx
    2030:	cmp    %rdi,%r9
    2033:	jb     204d <ZSTD_decompressSequencesLong+0x90d>
    2035:	cmp    $0x2,%rcx
    2039:	mov    -0x128(%rbp),%rsi
    2040:	mov    -0x180(%rbp),%r8
    2047:	ja     20d6 <ZSTD_decompressSequencesLong+0x996>
    204d:	test   %rcx,%rcx
    2050:	je     2071 <ZSTD_decompressSequencesLong+0x931>
    2052:	mov    -0x128(%rbp),%r8
    2059:	xor    %edx,%edx
```

## 04_zstd_decompress/no_retpoline/origin: ZSTD_decompressSequencesLong, 235a, memmove

```asm
    2352:	mov    %r10d,-0x158(%rbp)
    2359:	call   235e <ZSTD_decompressSequencesLong+0xc1e>
			235a: R_X86_64_PLT32	memmove-0x4
    235e:	mov    -0x158(%rbp),%r10d
    2365:	jmp    2071 <ZSTD_decompressSequencesLong+0x931>
    236a:	mov    %rbx,%r14
    236d:	mov    %r13,%r11
    2370:	mov    -0x160(%rbp),%rbx
    2377:	mov    %r10d,%r13d
    237a:	jmp    1c42 <ZSTD_decompressSequencesLong+0x502>
    237f:	push   -0x138(%rbp)
    2385:	mov    %r10,%r8
    2388:	mov    %r11,%rcx
    238b:	mov    %rbx,%rdi
    238e:	push   -0x148(%rbp)
    2394:	lea    -0xe0(%rbp),%r9
    239b:	mov    -0x130(%rbp),%rsi
    23a2:	push   %r14
    23a4:	push   -0x120(%rbp)
```

## 04_zstd_decompress/no_retpoline/origin: ZSTD_decompressSequencesLong, 249b, memmove

```asm
    2493:	mov    %r9,-0x140(%rbp)
    249a:	call   249f <ZSTD_decompressSequencesLong+0xd5f>
			249b: R_X86_64_PLT32	memmove-0x4
    249f:	mov    -0x140(%rbp),%r9
    24a6:	jmp    1e28 <ZSTD_decompressSequencesLong+0x6e8>
    24ab:	call   24b0 <ZSTD_decompressSequencesLong+0xd70>
			24ac: R_X86_64_PLT32	__stack_chk_fail-0x4
    24b0:	mov    -0xe0(%rbp),%rax
    24b7:	mov    -0x68(%rbp),%rdx
    24bb:	mov    %rax,%r14
    24be:	mov    %edx,0x6030(%rbx)
    24c4:	mov    -0x60(%rbp),%rdx
    24c8:	mov    %edx,0x6034(%rbx)
    24ce:	mov    -0x58(%rbp),%rdx
    24d2:	mov    %edx,0x6038(%rbx)
    24d8:	jmp    182a <ZSTD_decompressSequencesLong+0xea>
    24dd:	mov    %rbx,%r11
    24e0:	mov    -0x128(%rbp),%rbx
    24e7:	jmp    24b7 <ZSTD_decompressSequencesLong+0xd77>
```

## 04_zstd_decompress/no_retpoline/origin: ZSTD_decompressSequences, 2601, memcpy

```asm
    25fd:	mov    %r13,%rdi
    2600:	call   2605 <ZSTD_decompressSequences+0x105>
			2601: R_X86_64_PLT32	memcpy-0x4
    2605:	lea    0x0(%r13,%rbx,1),%rax
    260a:	sub    -0xd0(%rbp),%rax
    2611:	mov    %rax,%r14
    2614:	mov    -0x30(%rbp),%rax
    2618:	sub    %gs:0x28,%rax
    2621:	jne    3015 <ZSTD_decompressSequences+0xb15>
    2627:	lea    -0x28(%rbp),%rsp
    262b:	mov    %r14,%rax
    262e:	pop    %rbx
    262f:	pop    %r12
    2631:	pop    %r13
    2633:	pop    %r14
    2635:	pop    %r15
    2637:	pop    %rbp
    2638:	ret    
    2639:	int3   
```

## 04_zstd_decompress/no_retpoline/origin: ZSTD_decompressSequences, 2b82, memmove

```asm
    2b7a:	mov    %rdx,-0xc8(%rbp)
    2b81:	call   2b86 <ZSTD_decompressSequences+0x686>
			2b82: R_X86_64_PLT32	memmove-0x4
    2b86:	mov    -0xc8(%rbp),%rdx
    2b8d:	mov    -0x110(%rbp),%rcx
    2b94:	mov    %rax,%rdi
    2b97:	add    %rdx,%rdi
    2b9a:	add    %rcx,%r12
    2b9d:	cmp    %rdi,%r15
    2ba0:	jb     2bb3 <ZSTD_decompressSequences+0x6b3>
    2ba2:	mov    -0xf0(%rbp),%rcx
    2ba9:	cmp    $0x2,%r12
    2bad:	ja     2cee <ZSTD_decompressSequences+0x7ee>
    2bb3:	test   %r12,%r12
    2bb6:	je     2d8f <ZSTD_decompressSequences+0x88f>
    2bbc:	mov    -0xf0(%rbp),%rsi
    2bc3:	xor    %edx,%edx
    2bc5:	xor    %eax,%eax
    2bc7:	movzbl (%rsi,%rax,1),%ecx
```

## 04_zstd_decompress/no_retpoline/origin: ZSTD_decompressSequences, 2e98, memmove

```asm
    2e94:	mov    %r12,%rdx
    2e97:	call   2e9c <ZSTD_decompressSequences+0x99c>
			2e98: R_X86_64_PLT32	memmove-0x4
    2e9c:	jmp    2d8f <ZSTD_decompressSequences+0x88f>
    2ea1:	mov    -0x58(%rbp),%rcx
    2ea5:	cmp    $0x1,%rcx
    2ea9:	adc    $0x0,%rcx
    2ead:	mov    %rcx,-0x108(%rbp)
    2eb4:	mov    %esi,%ebx
    2eb6:	mov    -0x118(%rbp),%rdi
    2ebd:	mov    %rdi,-0x58(%rbp)
    2ec1:	mov    -0x108(%rbp),%rdi
    2ec8:	mov    %rdi,-0x60(%rbp)
    2ecc:	jmp    299c <ZSTD_decompressSequences+0x49c>
    2ed1:	mov    -0xc8(%rbp),%rcx
    2ed8:	mov    -0xe0(%rbp),%rdx
    2edf:	add    $0x8,%rcx
    2ee3:	add    $0x8,%rdx
    2ee7:	mov    (%rcx),%rsi
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_generateNxBytes_origin, 33e9, memset

```asm
    33e5:	mov    %rcx,%rbx
    33e8:	call   33ed <pgot_ZSTD_generateNxBytes_origin+0x1d>
			33e9: R_X86_64_PLT32	memset-0x4
    33ed:	mov    %rbx,%rax
    33f0:	mov    -0x8(%rbp),%rbx
    33f4:	leave  
    33f5:	ret    
    33f6:	int3   
    33f7:	mov    $0xfffffffffffffff4,%rax
    33fe:	ret    
    33ff:	int3   

```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_decompressContinue_origin, 3963, memcpy

```asm
    395f:	xor    %r12d,%r12d
    3962:	call   3967 <pgot_ZSTD_decompressContinue_origin+0x247>
			3963: R_X86_64_PLT32	memcpy-0x4
    3967:	mov    0x2612c(%rbx),%eax
    396d:	movl   $0x7,0x6084(%rbx)
    3977:	mov    %rax,0x6060(%rbx)
    397e:	jmp    381f <pgot_ZSTD_decompressContinue_origin+0xff>
    3983:	lea    0x26128(%rbx),%r13
    398a:	mov    %r8,%rdx
    398d:	mov    %rcx,%rsi
    3990:	lea    0x2612d(%rbx),%rdi
    3997:	call   399c <pgot_ZSTD_decompressContinue_origin+0x27c>
			3998: R_X86_64_PLT32	memcpy-0x4
    399c:	mov    0x60e0(%rbx),%rdx
    39a3:	mov    %r13,%rsi
    39a6:	mov    %rbx,%rdi
    39a9:	call   10a0 <ZSTD_decodeFrameHeader>
    39ae:	mov    %rax,%r12
    39b1:	cmp    $0xffffffffffffffea,%rax
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_decompressContinue_origin, 3998, memcpy

```asm
    3990:	lea    0x2612d(%rbx),%rdi
    3997:	call   399c <pgot_ZSTD_decompressContinue_origin+0x27c>
			3998: R_X86_64_PLT32	memcpy-0x4
    399c:	mov    0x60e0(%rbx),%rdx
    39a3:	mov    %r13,%rsi
    39a6:	mov    %rbx,%rdi
    39a9:	call   10a0 <ZSTD_decodeFrameHeader>
    39ae:	mov    %rax,%r12
    39b1:	cmp    $0xffffffffffffffea,%rax
    39b5:	ja     381f <pgot_ZSTD_decompressContinue_origin+0xff>
    39bb:	movq   $0x3,0x6060(%rbx)
    39c6:	xor    %r12d,%r12d
    39c9:	movl   $0x2,0x6084(%rbx)
    39d3:	jmp    381f <pgot_ZSTD_decompressContinue_origin+0xff>
    39d8:	mov    0x6080(%rbx),%eax
    39de:	cmp    $0x1,%eax
    39e1:	je     3a73 <pgot_ZSTD_decompressContinue_origin+0x353>
    39e7:	cmp    $0x2,%eax
    39ea:	je     3b08 <pgot_ZSTD_decompressContinue_origin+0x3e8>
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_decompressContinue_origin, 3a97, memset

```asm
    3a93:	mov    %r13,%rdi
    3a96:	call   3a9b <pgot_ZSTD_decompressContinue_origin+0x37b>
			3a97: R_X86_64_PLT32	memset-0x4
    3a9b:	cmp    $0xffffffffffffffea,%r12
    3a9f:	ja     381f <pgot_ZSTD_decompressContinue_origin+0xff>
    3aa5:	mov    0x6078(%rbx),%edx
    3aab:	test   %edx,%edx
    3aad:	jne    3b28 <pgot_ZSTD_decompressContinue_origin+0x408>
    3aaf:	cmpl   $0x4,0x6084(%rbx)
    3ab6:	je     3b88 <pgot_ZSTD_decompressContinue_origin+0x468>
    3abc:	movl   $0x2,0x6084(%rbx)
    3ac6:	add    %r12,%r13
    3ac9:	movq   $0x3,0x6060(%rbx)
    3ad4:	mov    %r13,0x6040(%rbx)
    3adb:	jmp    381f <pgot_ZSTD_decompressContinue_origin+0xff>
    3ae0:	mov    $0xfffffffffffffff4,%r12
    3ae7:	cmp    %rdx,%r8
    3aea:	ja     381f <pgot_ZSTD_decompressContinue_origin+0xff>
    3af0:	mov    %r8,%rdx
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_decompressContinue_origin, 3afe, memcpy

```asm
    3af9:	mov    %r8,-0x30(%rbp)
    3afd:	call   3b02 <pgot_ZSTD_decompressContinue_origin+0x3e2>
			3afe: R_X86_64_PLT32	memcpy-0x4
    3b02:	mov    -0x30(%rbp),%r12
    3b06:	jmp    3a9b <pgot_ZSTD_decompressContinue_origin+0x37b>
    3b08:	cmp    $0x1ffff,%r8
    3b0f:	ja     393a <pgot_ZSTD_decompressContinue_origin+0x21a>
    3b15:	mov    %r13,%rsi
    3b18:	mov    %rbx,%rdi
    3b1b:	call   3290 <ZSTD_decompressBlock_internal.part.0>
    3b20:	mov    %rax,%r12
    3b23:	jmp    3a9b <pgot_ZSTD_decompressContinue_origin+0x37b>
    3b28:	lea    0x6090(%rbx),%rdi
    3b2f:	mov    %r12,%rdx
    3b32:	mov    %r13,%rsi
    3b35:	call   3b3a <pgot_ZSTD_decompressContinue_origin+0x41a>
			3b36: R_X86_64_PLT32	xxh64_update-0x4
    3b3a:	cmpl   $0x4,0x6084(%rbx)
    3b41:	jne    3abc <pgot_ZSTD_decompressContinue_origin+0x39c>
```

## 04_zstd_decompress/no_retpoline/origin: ZSTD_decompressMultiFrame, 3dc8, memcpy

```asm
    3dc3:	mov    %r8,-0x58(%rbp)
    3dc7:	call   3dcc <ZSTD_decompressMultiFrame+0xec>
			3dc8: R_X86_64_PLT32	memcpy-0x4
    3dcc:	mov    -0x58(%rbp),%r8
    3dd0:	mov    %r8,%r15
    3dd3:	mov    0x6078(%r13),%ecx
    3dda:	test   %ecx,%ecx
    3ddc:	jne    3fd9 <ZSTD_decompressMultiFrame+0x2f9>
    3de2:	mov    -0x48(%rbp),%edx
    3de5:	sub    %r8,%r14
    3de8:	add    %r15,%rbx
    3deb:	lea    (%r12,%r8,1),%r11
    3def:	mov    %r14,%r9
    3df2:	test   %edx,%edx
    3df4:	jne    404b <ZSTD_decompressMultiFrame+0x36b>
    3dfa:	cmp    $0x2,%r14
    3dfe:	ja     3f12 <ZSTD_decompressMultiFrame+0x232>
    3e04:	mov    $0xfffffffffffffff3,%r15
    3e0b:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
```

## 04_zstd_decompress/no_retpoline/origin: ZSTD_decompressMultiFrame, 4024, memset

```asm
    4020:	mov    %rbx,%rdi
    4023:	call   4028 <ZSTD_decompressMultiFrame+0x348>
			4024: R_X86_64_PLT32	memset-0x4
    4028:	mov    $0x1,%r8d
    402e:	jmp    3dd3 <ZSTD_decompressMultiFrame+0xf3>
    4033:	mov    $0xfffffffffffffff4,%r15
    403a:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
    403f:	mov    $0xfffffffffffffffe,%r15
    4046:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
    404b:	mov    0x6078(%r13),%eax
    4052:	mov    %rbx,%r15
    4055:	mov    -0x60(%rbp),%r14
    4059:	mov    %r9,%rbx
    405c:	test   %eax,%eax
    405e:	jne    407c <ZSTD_decompressMultiFrame+0x39c>
    4060:	mov    %r15,%r12
    4063:	sub    %r14,%r12
    4066:	cmp    $0xffffffffffffffea,%r12
    406a:	ja     3f8d <ZSTD_decompressMultiFrame+0x2ad>
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_decompressStream_origin, 4855, memcpy

```asm
    4850:	mov    %rcx,-0x40(%rbp)
    4854:	call   4859 <pgot_ZSTD_decompressStream_origin+0xd9>
			4855: R_X86_64_PLT32	memcpy-0x4
    4859:	mov    -0x40(%rbp),%rcx
    485d:	mov    0x30(%rbx),%eax
    4860:	mov    %r15,0x98(%rbx)
    4867:	add    %rcx,%r12
    486a:	cmp    $0x2,%eax
    486d:	jne    47ef <pgot_ZSTD_decompressStream_origin+0x6f>
    486f:	mov    (%rbx),%rdi
    4872:	mov    0x6060(%rdi),%r8
    4879:	test   %r8,%r8
    487c:	jne    4b3e <pgot_ZSTD_decompressStream_origin+0x3be>
    4882:	movl   $0x0,0x30(%rbx)
    4889:	mov    -0x68(%rbp),%rax
    488d:	mov    -0x58(%rbp),%rsi
    4891:	sub    -0x50(%rbp),%r12
    4895:	sub    -0x60(%rbp),%r13
    4899:	add    %r12,0x10(%rsi)
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_decompressStream_origin, 4923, memcpy

```asm
    491e:	mov    %rdx,-0x40(%rbp)
    4922:	call   4927 <pgot_ZSTD_decompressStream_origin+0x1a7>
			4923: R_X86_64_PLT32	memcpy-0x4
    4927:	mov    -0x40(%rbp),%rdx
    492b:	mov    -0x48(%rbp),%rcx
    492f:	add    %rdx,%r13
    4932:	add    0x68(%rbx),%rdx
    4936:	mov    %rdx,0x68(%rbx)
    493a:	cmp    %r15,%rcx
    493d:	jb     4889 <pgot_ZSTD_decompressStream_origin+0x109>
    4943:	movl   $0x2,0x30(%rbx)
    494a:	add    0x78(%rbx),%rdx
    494e:	cmp    0x60(%rbx),%rdx
    4952:	jbe    47e3 <pgot_ZSTD_decompressStream_origin+0x63>
    4958:	movq   $0x0,0x70(%rbx)
    4960:	movq   $0x0,0x68(%rbx)
    4968:	jmp    47e3 <pgot_ZSTD_decompressStream_origin+0x63>
    496d:	movl   $0x1,0x30(%rbx)
    4974:	xor    %edx,%edx
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_decompressStream_origin, 49f1, memcpy

```asm
    49ed:	add    %r15,%r12
    49f0:	call   49f5 <pgot_ZSTD_decompressStream_origin+0x275>
			49f1: R_X86_64_PLT32	memcpy-0x4
    49f5:	mov    -0x48(%rbp),%rcx
    49f9:	add    %r15,0x48(%rbx)
    49fd:	mov    -0x40(%rbp),%r8
    4a01:	cmp    %r15,%rcx
    4a04:	ja     4889 <pgot_ZSTD_decompressStream_origin+0x109>
    4a0a:	mov    (%rbx),%rdi
    4a0d:	mov    0x68(%rbx),%rsi
    4a11:	mov    0x60(%rbx),%rdx
    4a15:	mov    0x38(%rbx),%rcx
    4a19:	mov    0x6084(%rdi),%eax
    4a1f:	sub    %rsi,%rdx
    4a22:	add    0x58(%rbx),%rsi
    4a26:	mov    %eax,-0x40(%rbp)
    4a29:	call   4a2e <pgot_ZSTD_decompressStream_origin+0x2ae>
			4a2a: R_X86_64_PLT32	pgot_ZSTD_decompressContinue_origin-0x4
    4a2e:	mov    %rax,%r15
```

## 04_zstd_decompress/no_retpoline/origin: pgot_ZSTD_decompressStream_origin, 4cfe, memcpy

```asm
    4cf9:	mov    %rax,-0x38(%rbp)
    4cfd:	call   4d02 <pgot_ZSTD_decompressStream_origin+0x582>
			4cfe: R_X86_64_PLT32	memcpy-0x4
    4d02:	mov    -0x58(%rbp),%rsi
    4d06:	mov    -0x30(%rbp),%rdx
    4d0a:	add    %rdx,0x98(%rbx)
    4d11:	mov    -0x38(%rbp),%r9
    4d15:	mov    $0x3,%edx
    4d1a:	mov    0x8(%rsi),%rax
    4d1e:	mov    %rax,0x10(%rsi)
    4d22:	mov    $0x6,%eax
    4d27:	sub    0x98(%rbx),%rdx
    4d2e:	cmp    %rax,%r9
    4d31:	cmovae %r9,%rax
    4d35:	lea    (%rdx,%rax,1),%r9
    4d39:	jmp    4c7d <pgot_ZSTD_decompressStream_origin+0x4fd>
    4d3e:	mov    $0xfffffffffffffff9,%r9
    4d45:	jmp    4c7d <pgot_ZSTD_decompressStream_origin+0x4fd>
    4d4a:	mov    -0x58(%rbp),%rsi
```

## 04_zstd_decompress/no_retpoline/origin: pgot_FSE_readNCount_origin, 279, memset

```asm
 274:	lea    (%rax,%r8,2),%rdi
 278:	call   27d <pgot_FSE_readNCount_origin+0x21d>
			279: R_X86_64_PLT32	memset-0x4
 27d:	mov    -0x4c(%rbp),%r8d
 281:	mov    -0x58(%rbp),%ecx
 284:	mov    %r13d,%eax
 287:	sar    $0x3,%eax
 28a:	cltq   
 28c:	add    %r12,%rax
 28f:	cmp    -0x40(%rbp),%r12
 293:	jbe    2a2 <pgot_FSE_readNCount_origin+0x242>
 295:	shr    $0x2,%ecx
 298:	cmp    -0x48(%rbp),%rax
 29c:	ja     195 <pgot_FSE_readNCount_origin+0x135>
 2a2:	mov    (%rax),%esi
 2a4:	and    $0x7,%r13d
 2a8:	mov    %rax,%r12
 2ab:	mov    %r13d,%ecx
 2ae:	shr    %cl,%esi
```

## 04_zstd_decompress/no_retpoline/origin: pgot_HUF_decompress4X_DCtx_wksp_origin, 42ff, memcpy

```asm
    42fb:	mov    %rcx,%rsi
    42fe:	call   4303 <pgot_HUF_decompress4X_DCtx_wksp_origin+0x123>
			42ff: R_X86_64_PLT32	memcpy-0x4
    4303:	lea    -0x28(%rbp),%rsp
    4307:	mov    %r12,%rax
    430a:	pop    %rbx
    430b:	pop    %r12
    430d:	pop    %r13
    430f:	pop    %r14
    4311:	pop    %r15
    4313:	pop    %rbp
    4314:	ret    
    4315:	int3   
    4316:	movzbl (%rcx),%esi
    4319:	mov    %r13,%rdi
    431c:	call   4321 <pgot_HUF_decompress4X_DCtx_wksp_origin+0x141>
			431d: R_X86_64_PLT32	memset-0x4
    4321:	lea    -0x28(%rbp),%rsp
    4325:	mov    %r12,%rax
```

## 04_zstd_decompress/no_retpoline/origin: pgot_HUF_decompress4X_DCtx_wksp_origin, 431d, memset

```asm
    4319:	mov    %r13,%rdi
    431c:	call   4321 <pgot_HUF_decompress4X_DCtx_wksp_origin+0x141>
			431d: R_X86_64_PLT32	memset-0x4
    4321:	lea    -0x28(%rbp),%rsp
    4325:	mov    %r12,%rax
    4328:	pop    %rbx
    4329:	pop    %r12
    432b:	pop    %r13
    432d:	pop    %r14
    432f:	pop    %r15
    4331:	pop    %rbp
    4332:	ret    
    4333:	int3   
    4334:	mov    %rbx,%rsi
    4337:	mov    $0x0,%rdi
			433a: R_X86_64_32S	.data+0x100
    433e:	mov    %r9,-0x50(%rbp)
    4342:	mov    %r8,-0x48(%rbp)
    4346:	mov    %rcx,-0x40(%rbp)
```

## 04_zstd_decompress/no_retpoline/origin: pgot_HUF_decompress1X_DCtx_wksp_origin, 476f, memcpy

```asm
    476b:	mov    %r12,%r13
    476e:	call   4773 <pgot_HUF_decompress1X_DCtx_wksp_origin+0x183>
			476f: R_X86_64_PLT32	memcpy-0x4
    4773:	jmp    471b <pgot_HUF_decompress1X_DCtx_wksp_origin+0x12b>
    4775:	movzbl (%rcx),%esi
    4778:	mov    %r10,%rdi
    477b:	mov    %r12,%r13
    477e:	call   4783 <pgot_HUF_decompress1X_DCtx_wksp_origin+0x193>
			477f: R_X86_64_PLT32	memset-0x4
    4783:	jmp    471b <pgot_HUF_decompress1X_DCtx_wksp_origin+0x12b>
    4785:	mov    $0xfffffffffffffff3,%r13
    478c:	jmp    471b <pgot_HUF_decompress1X_DCtx_wksp_origin+0x12b>
    478e:	mov    %r13,%rsi
    4791:	mov    $0x0,%rdi
			4794: R_X86_64_32S	.data
    4798:	mov    %rdx,-0x50(%rbp)
    479c:	mov    %r9,-0x48(%rbp)
    47a0:	mov    %r10,-0x40(%rbp)
    47a4:	mov    %r8d,-0x38(%rbp)
```

## 04_zstd_decompress/no_retpoline/origin: pgot_HUF_decompress1X_DCtx_wksp_origin, 477f, memset

```asm
    477b:	mov    %r12,%r13
    477e:	call   4783 <pgot_HUF_decompress1X_DCtx_wksp_origin+0x193>
			477f: R_X86_64_PLT32	memset-0x4
    4783:	jmp    471b <pgot_HUF_decompress1X_DCtx_wksp_origin+0x12b>
    4785:	mov    $0xfffffffffffffff3,%r13
    478c:	jmp    471b <pgot_HUF_decompress1X_DCtx_wksp_origin+0x12b>
    478e:	mov    %r13,%rsi
    4791:	mov    $0x0,%rdi
			4794: R_X86_64_32S	.data
    4798:	mov    %rdx,-0x50(%rbp)
    479c:	mov    %r9,-0x48(%rbp)
    47a0:	mov    %r10,-0x40(%rbp)
    47a4:	mov    %r8d,-0x38(%rbp)
    47a8:	mov    %eax,-0x30(%rbp)
    47ab:	call   47b0 <pgot_HUF_decompress1X_DCtx_wksp_origin+0x1c0>
			47ac: R_X86_64_PLT32	__ubsan_handle_out_of_bounds-0x4
    47b0:	mov    -0x50(%rbp),%rdx
    47b4:	mov    -0x48(%rbp),%r9
    47b8:	mov    -0x40(%rbp),%r10
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_execSequenceLast7_all_pgot.isra.0, 5d3, pgot_memmove_table_all_pgot

```asm
     5cc:	mov    0x18(%rbp),%r14
     5d0:	mov    0x0(%rip),%rcx        # 5d7 <pgot_ZSTD_execSequenceLast7_all_pgot.isra.0+0xd7>
			5d3: R_X86_64_PC32	pgot_memmove_table_all_pgot-0x4
     5d7:	sub    %rsi,%r14
     5da:	mov    0x28(%rbp),%rsi
     5de:	sub    %r14,%rsi
     5e1:	lea    (%rsi,%r10,1),%rax
     5e5:	cmp    %rax,0x28(%rbp)
     5e9:	jae    687 <pgot_ZSTD_execSequenceLast7_all_pgot.isra.0+0x187>
     5ef:	mov    %r14,%rdx
     5f2:	mov    %r12,%rdi
     5f5:	jmp    609 <pgot_ZSTD_execSequenceLast7_all_pgot.isra.0+0x109>
     5f7:	call   603 <pgot_ZSTD_execSequenceLast7_all_pgot.isra.0+0x103>
     5fc:	pause  
     5fe:	lfence 
     601:	jmp    5fc <pgot_ZSTD_execSequenceLast7_all_pgot.isra.0+0xfc>
     603:	mov    %rcx,(%rsp)
     607:	ret    
     608:	int3   
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decompressBegin_all_pgot, b69, pgot_memcpy_table_all_pgot

```asm
     b65:	push   %rbp
     b66:	mov    0x0(%rip),%rax        # b6d <pgot_ZSTD_decompressBegin_all_pgot+0xd>
			b69: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     b6d:	mov    $0xc,%edx
     b72:	mov    $0x0,%rsi
			b75: R_X86_64_32S	.rodata+0x700
     b79:	mov    %rsp,%rbp
     b7c:	push   %rbx
     b7d:	mov    %rdi,%rbx
     b80:	lea    0x6030(%rdi),%rdi
     b87:	movq   $0x5,0x30(%rdi)
     b8f:	movq   $0x0,0x10(%rdi)
     b97:	movq   $0x0,0x18(%rdi)
     b9f:	movq   $0x0,0x20(%rdi)
     ba7:	movq   $0x0,0x28(%rdi)
     baf:	movl   $0xc00000c,-0x4c04(%rdi)
     bb9:	movl   $0x0,0x54(%rdi)
     bc0:	movq   $0x0,0x58(%rdi)
     bc8:	movl   $0x0,0xb8(%rdi)
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_createDCtx_advanced_all_pgot, d57, pgot_memcpy_table_all_pgot

```asm
     d4f:	mov    $0x18,%edx
     d54:	mov    0x0(%rip),%rax        # d5b <pgot_ZSTD_createDCtx_advanced_all_pgot+0x4b>
			d57: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     d5b:	lea    0x10(%rbp),%rsi
     d5f:	jmp    d73 <pgot_ZSTD_createDCtx_advanced_all_pgot+0x63>
     d61:	call   d6d <pgot_ZSTD_createDCtx_advanced_all_pgot+0x5d>
     d66:	pause  
     d68:	lfence 
     d6b:	jmp    d66 <pgot_ZSTD_createDCtx_advanced_all_pgot+0x56>
     d6d:	mov    %rax,(%rsp)
     d71:	ret    
     d72:	int3   
     d73:	call   d61 <pgot_ZSTD_createDCtx_advanced_all_pgot+0x51>
     d78:	mov    %r12,%rdi
     d7b:	call   d80 <pgot_ZSTD_createDCtx_advanced_all_pgot+0x70>
			d7c: R_X86_64_PLT32	pgot_ZSTD_decompressBegin_all_pgot-0x4
     d80:	mov    %r12,%rax
     d83:	mov    -0x8(%rbp),%r12
     d87:	leave  
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_copyDCtx_all_pgot, e39, pgot_memcpy_table_all_pgot

```asm
     e35:	push   %rbp
     e36:	mov    0x0(%rip),%rax        # e3d <pgot_ZSTD_copyDCtx_all_pgot+0xd>
			e39: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     e3d:	mov    $0x6126,%edx
     e42:	mov    %rsp,%rbp
     e45:	jmp    e59 <pgot_ZSTD_copyDCtx_all_pgot+0x29>
     e47:	call   e53 <pgot_ZSTD_copyDCtx_all_pgot+0x23>
     e4c:	pause  
     e4e:	lfence 
     e51:	jmp    e4c <pgot_ZSTD_copyDCtx_all_pgot+0x1c>
     e53:	mov    %rax,(%rsp)
     e57:	ret    
     e58:	int3   
     e59:	call   e47 <pgot_ZSTD_copyDCtx_all_pgot+0x17>
     e5e:	pop    %rbp
     e5f:	ret    
     e60:	int3   
     e61:	data16 cs nopw 0x0(%rax,%rax,1)
     e6c:	nopl   0x0(%rax)
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_getFrameParams_all_pgot, f09, pgot_memset_table_all_pgot

```asm
     f04:	jbe    f40 <pgot_ZSTD_getFrameParams_all_pgot+0x90>
     f06:	mov    0x0(%rip),%rax        # f0d <pgot_ZSTD_getFrameParams_all_pgot+0x5d>
			f09: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
     f0d:	mov    $0x18,%edx
     f12:	xor    %esi,%esi
     f14:	jmp    f28 <pgot_ZSTD_getFrameParams_all_pgot+0x78>
     f16:	call   f22 <pgot_ZSTD_getFrameParams_all_pgot+0x72>
     f1b:	pause  
     f1d:	lfence 
     f20:	jmp    f1b <pgot_ZSTD_getFrameParams_all_pgot+0x6b>
     f22:	mov    %rax,(%rsp)
     f26:	ret    
     f27:	int3   
     f28:	call   f16 <pgot_ZSTD_getFrameParams_all_pgot+0x66>
     f2d:	mov    0x4(%r12),%eax
     f32:	movl   $0x0,0x8(%r13)
     f3a:	mov    %rax,0x0(%r13)
     f3e:	xor    %eax,%eax
     f40:	add    $0x18,%rsp
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decodeLiteralsBlock_all_pgot, 1319, pgot_memcpy_table_all_pgot

```asm
    1313:	mov    %rbx,%rdx
    1316:	mov    0x0(%rip),%rax        # 131d <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x9d>
			1319: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    131d:	mov    %r14,%rdi
    1320:	jmp    1334 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xb4>
    1322:	call   132e <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xae>
    1327:	pause  
    1329:	lfence 
    132c:	jmp    1327 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xa7>
    132e:	mov    %rax,(%rsp)
    1332:	ret    
    1333:	int3   
    1334:	call   1322 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xa2>
    1339:	mov    %r14,0x60f0(%r12)
    1341:	lea    (%r14,%rbx,1),%rdi
    1345:	xor    %esi,%esi
    1347:	mov    %rbx,0x6110(%r12)
    134f:	mov    $0x8,%edx
    1354:	mov    0x0(%rip),%rax        # 135b <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xdb>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decodeLiteralsBlock_all_pgot, 1357, pgot_memset_table_all_pgot

```asm
    134f:	mov    $0x8,%edx
    1354:	mov    0x0(%rip),%rax        # 135b <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xdb>
			1357: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    135b:	jmp    136f <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xef>
    135d:	call   1369 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xe9>
    1362:	pause  
    1364:	lfence 
    1367:	jmp    1362 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xe2>
    1369:	mov    %rax,(%rsp)
    136d:	ret    
    136e:	int3   
    136f:	call   135d <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0xdd>
    1374:	jmp    13c9 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x149>
    1376:	mov    0x6088(%rdi),%esi
    137c:	mov    $0xffffffffffffffed,%r13
    1383:	test   %esi,%esi
    1385:	je     13c9 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x149>
    1387:	cmp    $0x4,%rdx
    138b:	jbe    13c2 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x142>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decodeLiteralsBlock_all_pgot, 1491, pgot_memset_table_all_pgot

```asm
    148c:	xor    %esi,%esi
    148e:	mov    0x0(%rip),%rax        # 1495 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x215>
			1491: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    1495:	jmp    14a9 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x229>
    1497:	call   14a3 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x223>
    149c:	pause  
    149e:	lfence 
    14a1:	jmp    149c <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x21c>
    14a3:	mov    %rax,(%rsp)
    14a7:	ret    
    14a8:	int3   
    14a9:	call   1497 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x217>
    14ae:	jmp    13c9 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x149>
    14b3:	mov    %ecx,%r14d
    14b6:	shr    $0x12,%r8d
    14ba:	xor    %eax,%eax
    14bc:	mov    $0x4,%esi
    14c1:	and    $0x3fff,%r14d
    14c8:	mov    %r8d,%ecx
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decodeLiteralsBlock_all_pgot, 1523, pgot_memset_table_all_pgot

```asm
    151c:	lea    0x8(%rbx),%rdx
    1520:	mov    0x0(%rip),%rax        # 1527 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x2a7>
			1523: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    1527:	mov    %r14,%rdi
    152a:	jmp    153e <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x2be>
    152c:	call   1538 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x2b8>
    1531:	pause  
    1533:	lfence 
    1536:	jmp    1531 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x2b1>
    1538:	mov    %rax,(%rsp)
    153c:	ret    
    153d:	int3   
    153e:	call   152c <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x2ac>
    1543:	mov    %r14,0x60f0(%r12)
    154b:	mov    %rbx,0x6110(%r12)
    1553:	jmp    13c9 <pgot_ZSTD_decodeLiteralsBlock_all_pgot+0x149>
    1558:	add    %r9,%rsi
    155b:	mov    %rbx,0x6110(%r12)
    1563:	mov    %rsi,0x60f0(%r12)
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decodeSeqHeaders_all_pgot, 16f0, pgot_LL_defaultDTable_all_pgot

```asm
    16eb:	sub    %r9,%rax
    16ee:	push   0x0(%rip)        # 16f4 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x94>
			16f0: R_X86_64_PC32	pgot_LL_defaultDTable_all_pgot-0x4
    16f4:	push   %rax
    16f5:	call   400 <ZSTD_buildSeqTable.constprop.0>
    16fa:	mov    -0x30(%rbp),%r9
    16fe:	add    $0x20,%rsp
    1702:	cmp    $0xffffffffffffffea,%rax
    1706:	ja     17f7 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x197>
    170c:	push   %r15
    170e:	add    %rax,%r9
    1711:	mov    0x608c(%r13),%eax
    1718:	mov    %r14d,%edx
    171b:	shr    $0x4,%dl
    171e:	lea    0x10(%r13),%rsi
    1722:	mov    $0x1c,%ecx
    1727:	mov    %r9,-0x30(%rbp)
    172b:	push   %rax
    172c:	mov    %rbx,%rax
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decodeSeqHeaders_all_pgot, 173e, pgot_OF_defaultDTable_all_pgot

```asm
    1739:	sub    %r9,%rax
    173c:	push   0x0(%rip)        # 1742 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0xe2>
			173e: R_X86_64_PC32	pgot_OF_defaultDTable_all_pgot-0x4
    1742:	mov    $0x8,%r8d
    1748:	push   %rax
    1749:	call   400 <ZSTD_buildSeqTable.constprop.0>
    174e:	add    $0x20,%rsp
    1752:	cmp    $0xffffffffffffffea,%rax
    1756:	ja     17f7 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x197>
    175c:	mov    -0x30(%rbp),%r9
    1760:	push   %r15
    1762:	mov    %r14d,%edx
    1765:	lea    0x8(%r13),%rsi
    1769:	shr    $0x2,%dl
    176c:	mov    $0x9,%r8d
    1772:	mov    $0x34,%ecx
    1777:	add    %rax,%r9
    177a:	mov    0x608c(%r13),%eax
    1781:	and    $0x3,%edx
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decodeSeqHeaders_all_pgot, 1795, pgot_ML_defaultDTable_all_pgot

```asm
    1792:	push   %rax
    1793:	push   0x0(%rip)        # 1799 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x139>
			1795: R_X86_64_PC32	pgot_ML_defaultDTable_all_pgot-0x4
    1799:	push   %rbx
    179a:	call   400 <ZSTD_buildSeqTable.constprop.0>
    179f:	add    $0x20,%rsp
    17a3:	cmp    $0xffffffffffffffea,%rax
    17a7:	ja     17f7 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x197>
    17a9:	mov    -0x30(%rbp),%r9
    17ad:	add    %r9,%rax
    17b0:	sub    %r12,%rax
    17b3:	jmp    17fe <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x19e>
    17b5:	cmp    $0xff,%eax
    17ba:	je     1829 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x1c9>
    17bc:	cmp    %r9,%rbx
    17bf:	jbe    17e0 <pgot_ZSTD_decodeSeqHeaders_all_pgot+0x180>
    17c1:	lea    0x2(%rdx),%r9
    17c5:	add    $0xffffff80,%eax
    17c8:	movzbl 0x1(%rdx),%edx
```

## 04_zstd_decompress/retpoline/all_pgot: ZSTD_decompressSequencesLong, 1971, pgot_memcpy_table_all_pgot

```asm
    196b:	mov    %r13,%rsi
    196e:	mov    0x0(%rip),%rax        # 1975 <ZSTD_decompressSequencesLong+0x125>
			1971: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    1975:	jmp    1989 <ZSTD_decompressSequencesLong+0x139>
    1977:	call   1983 <ZSTD_decompressSequencesLong+0x133>
    197c:	pause  
    197e:	lfence 
    1981:	jmp    197c <ZSTD_decompressSequencesLong+0x12c>
    1983:	mov    %rax,(%rsp)
    1987:	ret    
    1988:	int3   
    1989:	call   1977 <ZSTD_decompressSequencesLong+0x127>
    198e:	mov    -0x120(%rbp),%r11
    1995:	add    %r11,%rbx
    1998:	sub    -0x118(%rbp),%rbx
    199f:	mov    %rbx,%r12
    19a2:	mov    -0x38(%rbp),%rax
    19a6:	sub    %gs:0x28,%rax
    19af:	jne    26e9 <ZSTD_decompressSequencesLong+0xe99>
```

## 04_zstd_decompress/retpoline/all_pgot: ZSTD_decompressSequencesLong, 1e60, pgot_memmove_table_all_pgot

```asm
    1e57:	jb     1a36 <ZSTD_decompressSequencesLong+0x1e6>
    1e5d:	mov    0x0(%rip),%rax        # 1e64 <ZSTD_decompressSequencesLong+0x614>
			1e60: R_X86_64_PC32	pgot_memmove_table_all_pgot-0x4
    1e64:	lea    (%rsi,%rcx,1),%rdx
    1e68:	cmp    %rdx,-0x130(%rbp)
    1e6f:	jae    26b7 <ZSTD_decompressSequencesLong+0xe67>
    1e75:	mov    -0x130(%rbp),%rdx
    1e7c:	mov    %r9,-0x178(%rbp)
    1e83:	mov    %r14,%rdi
    1e86:	mov    %rcx,-0x160(%rbp)
    1e8d:	sub    %rsi,%rdx
    1e90:	mov    %r8,-0x168(%rbp)
    1e97:	mov    %rdx,-0x128(%rbp)
    1e9e:	jmp    1eb2 <ZSTD_decompressSequencesLong+0x662>
    1ea0:	call   1eac <ZSTD_decompressSequencesLong+0x65c>
    1ea5:	pause  
    1ea7:	lfence 
    1eaa:	jmp    1ea5 <ZSTD_decompressSequencesLong+0x655>
    1eac:	mov    %rax,(%rsp)
```

## 04_zstd_decompress/retpoline/all_pgot: ZSTD_decompressSequencesLong, 1f4e, pgot_memcpy_table_all_pgot

```asm
    1f48:	add    %rax,%rsi
    1f4b:	mov    0x0(%rip),%rax        # 1f52 <ZSTD_decompressSequencesLong+0x702>
			1f4e: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    1f52:	mov    %rsi,-0x160(%rbp)
    1f59:	jmp    1f6d <ZSTD_decompressSequencesLong+0x71d>
    1f5b:	call   1f67 <ZSTD_decompressSequencesLong+0x717>
    1f60:	pause  
    1f62:	lfence 
    1f65:	jmp    1f60 <ZSTD_decompressSequencesLong+0x710>
    1f67:	mov    %rax,(%rsp)
    1f6b:	ret    
    1f6c:	int3   
    1f6d:	call   1f5b <ZSTD_decompressSequencesLong+0x70b>
    1f72:	movslq -0x128(%rbp),%rax
    1f79:	mov    -0x160(%rbp),%rsi
    1f80:	mov    -0x168(%rbp),%rcx
    1f87:	mov    -0x178(%rbp),%r9
    1f8e:	sub    %rax,%rsi
    1f91:	lea    0x8(%r14),%rax
```

## 04_zstd_decompress/retpoline/all_pgot: ZSTD_decompressSequencesLong, 2185, pgot_memmove_table_all_pgot

```asm
    217c:	jb     1a36 <ZSTD_decompressSequencesLong+0x1e6>
    2182:	mov    0x0(%rip),%rax        # 2189 <ZSTD_decompressSequencesLong+0x939>
			2185: R_X86_64_PC32	pgot_memmove_table_all_pgot-0x4
    2189:	lea    (%rsi,%rcx,1),%rdx
    218d:	cmp    %rdx,-0x130(%rbp)
    2194:	jae    2590 <ZSTD_decompressSequencesLong+0xd40>
    219a:	mov    -0x130(%rbp),%rdx
    21a1:	mov    %r10d,-0x180(%rbp)
    21a8:	mov    %r14,%rdi
    21ab:	mov    %rcx,-0x178(%rbp)
    21b2:	sub    %rsi,%rdx
    21b5:	mov    %r9,-0x160(%rbp)
    21bc:	mov    %rdx,-0x158(%rbp)
    21c3:	mov    %r8,-0x188(%rbp)
    21ca:	jmp    21de <ZSTD_decompressSequencesLong+0x98e>
    21cc:	call   21d8 <ZSTD_decompressSequencesLong+0x988>
    21d1:	pause  
    21d3:	lfence 
    21d6:	jmp    21d1 <ZSTD_decompressSequencesLong+0x981>
```

## 04_zstd_decompress/retpoline/all_pgot: ZSTD_decompressSequencesLong, 2431, pgot_memcpy_table_all_pgot

```asm
    242b:	add    %rax,%rsi
    242e:	mov    0x0(%rip),%rax        # 2435 <ZSTD_decompressSequencesLong+0xbe5>
			2431: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2435:	mov    %rsi,-0x160(%rbp)
    243c:	jmp    2450 <ZSTD_decompressSequencesLong+0xc00>
    243e:	call   244a <ZSTD_decompressSequencesLong+0xbfa>
    2443:	pause  
    2445:	lfence 
    2448:	jmp    2443 <ZSTD_decompressSequencesLong+0xbf3>
    244a:	mov    %rax,(%rsp)
    244e:	ret    
    244f:	int3   
    2450:	call   243e <ZSTD_decompressSequencesLong+0xbee>
    2455:	movslq -0x158(%rbp),%rax
    245c:	mov    -0x160(%rbp),%rsi
    2463:	mov    -0x178(%rbp),%r9
    246a:	mov    -0x180(%rbp),%rcx
    2471:	mov    -0x188(%rbp),%r10d
    2478:	sub    %rax,%rsi
```

## 04_zstd_decompress/retpoline/all_pgot: ZSTD_decompressSequences, 2856, pgot_memcpy_table_all_pgot

```asm
    2851:	jb     288c <ZSTD_decompressSequences+0x14c>
    2853:	mov    0x0(%rip),%rax        # 285a <ZSTD_decompressSequences+0x11a>
			2856: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    285a:	mov    %rbx,%rdx
    285d:	mov    %r9,%rsi
    2860:	mov    %r15,%rdi
    2863:	jmp    2877 <ZSTD_decompressSequences+0x137>
    2865:	call   2871 <ZSTD_decompressSequences+0x131>
    286a:	pause  
    286c:	lfence 
    286f:	jmp    286a <ZSTD_decompressSequences+0x12a>
    2871:	mov    %rax,(%rsp)
    2875:	ret    
    2876:	int3   
    2877:	call   2865 <ZSTD_decompressSequences+0x125>
    287c:	mov    %r15,%rax
    287f:	add    %rbx,%rax
    2882:	sub    -0xc8(%rbp),%rax
    2889:	mov    %rax,%r14
```

## 04_zstd_decompress/retpoline/all_pgot: ZSTD_decompressSequences, 2df1, pgot_memmove_table_all_pgot

```asm
    2de7:	sub    -0xe8(%rbp),%rbx
    2dee:	mov    0x0(%rip),%rax        # 2df5 <ZSTD_decompressSequences+0x6b5>
			2df1: R_X86_64_PC32	pgot_memmove_table_all_pgot-0x4
    2df5:	lea    (%rdi,%rbx,1),%rsi
    2df9:	lea    (%rsi,%r12,1),%rdx
    2dfd:	cmp    %rdx,%rdi
    2e00:	jae    31ac <ZSTD_decompressSequences+0xa6c>
    2e06:	mov    %rbx,%rdx
    2e09:	mov    %rcx,-0x110(%rbp)
    2e10:	mov    %r15,%rdi
    2e13:	add    %rbx,%r12
    2e16:	neg    %rdx
    2e19:	mov    %r8,-0x118(%rbp)
    2e20:	mov    %rdx,-0x108(%rbp)
    2e27:	jmp    2e3b <ZSTD_decompressSequences+0x6fb>
    2e29:	call   2e35 <ZSTD_decompressSequences+0x6f5>
    2e2e:	pause  
    2e30:	lfence 
    2e33:	jmp    2e2e <ZSTD_decompressSequences+0x6ee>
```

## 04_zstd_decompress/retpoline/all_pgot: ZSTD_decompressSequences, 3128, pgot_memcpy_table_all_pgot

```asm
    3122:	add    %rax,%rsi
    3125:	mov    0x0(%rip),%rax        # 312c <ZSTD_decompressSequences+0x9ec>
			3128: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    312c:	mov    %rsi,-0x100(%rbp)
    3133:	jmp    3147 <ZSTD_decompressSequences+0xa07>
    3135:	call   3141 <ZSTD_decompressSequences+0xa01>
    313a:	pause  
    313c:	lfence 
    313f:	jmp    313a <ZSTD_decompressSequences+0x9fa>
    3141:	mov    %rax,(%rsp)
    3145:	ret    
    3146:	int3   
    3147:	call   3135 <ZSTD_decompressSequences+0x9f5>
    314c:	mov    -0x100(%rbp),%rsi
    3153:	mov    -0x108(%rbp),%r8
    315a:	mov    -0x110(%rbp),%rcx
    3161:	sub    %rbx,%rsi
    3164:	jmp    2fc4 <ZSTD_decompressSequences+0x884>
    3169:	mov    %rcx,%rdi
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_generateNxBytes_all_pgot, 3721, pgot_memset_table_all_pgot

```asm
    371b:	movzbl %dl,%esi
    371e:	mov    0x0(%rip),%rax        # 3725 <pgot_ZSTD_generateNxBytes_all_pgot+0x15>
			3721: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    3725:	mov    %rcx,%rdx
    3728:	mov    %rsp,%rbp
    372b:	push   %rbx
    372c:	mov    %rcx,%rbx
    372f:	jmp    3743 <pgot_ZSTD_generateNxBytes_all_pgot+0x33>
    3731:	call   373d <pgot_ZSTD_generateNxBytes_all_pgot+0x2d>
    3736:	pause  
    3738:	lfence 
    373b:	jmp    3736 <pgot_ZSTD_generateNxBytes_all_pgot+0x26>
    373d:	mov    %rax,(%rsp)
    3741:	ret    
    3742:	int3   
    3743:	call   3731 <pgot_ZSTD_generateNxBytes_all_pgot+0x21>
    3748:	mov    %rbx,%rax
    374b:	mov    -0x8(%rbp),%rbx
    374f:	leave  
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3c77, pgot_memcpy_table_all_pgot

```asm
    3c71:	mov    %rcx,%rsi
    3c74:	mov    0x0(%rip),%rax        # 3c7b <pgot_ZSTD_decompressContinue_all_pgot+0x1fb>
			3c77: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3c7b:	mov    $0x5,%edx
    3c80:	mov    %r12,%rdi
    3c83:	jmp    3c97 <pgot_ZSTD_decompressContinue_all_pgot+0x217>
    3c85:	call   3c91 <pgot_ZSTD_decompressContinue_all_pgot+0x211>
    3c8a:	pause  
    3c8c:	lfence 
    3c8f:	jmp    3c8a <pgot_ZSTD_decompressContinue_all_pgot+0x20a>
    3c91:	mov    %rax,(%rsp)
    3c95:	ret    
    3c96:	int3   
    3c97:	call   3c85 <pgot_ZSTD_decompressContinue_all_pgot+0x205>
    3c9c:	mov    0x60e0(%rbx),%rax
    3ca3:	mov    -0x30(%rbp),%rcx
    3ca7:	cmp    $0x5,%rax
    3cab:	ja     3f84 <pgot_ZSTD_decompressContinue_all_pgot+0x504>
    3cb1:	movq   $0x0,0x6060(%rbx)
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3cdc, pgot_memcpy_table_all_pgot

```asm
    3cd4:	jmp    3b7f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3cd9:	mov    0x0(%rip),%rax        # 3ce0 <pgot_ZSTD_decompressContinue_all_pgot+0x260>
			3cdc: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3ce0:	mov    %r8,%rdx
    3ce3:	mov    %rcx,%rsi
    3ce6:	xor    %r12d,%r12d
    3ce9:	lea    0x2612d(%rbx),%rdi
    3cf0:	jmp    3d04 <pgot_ZSTD_decompressContinue_all_pgot+0x284>
    3cf2:	call   3cfe <pgot_ZSTD_decompressContinue_all_pgot+0x27e>
    3cf7:	pause  
    3cf9:	lfence 
    3cfc:	jmp    3cf7 <pgot_ZSTD_decompressContinue_all_pgot+0x277>
    3cfe:	mov    %rax,(%rsp)
    3d02:	ret    
    3d03:	int3   
    3d04:	call   3cf2 <pgot_ZSTD_decompressContinue_all_pgot+0x272>
    3d09:	mov    0x2612c(%rbx),%eax
    3d0f:	movl   $0x7,0x6084(%rbx)
    3d19:	mov    %rax,0x6060(%rbx)
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3d3c, pgot_memcpy_table_all_pgot

```asm
    3d32:	lea    0x2612d(%rbx),%rdi
    3d39:	mov    0x0(%rip),%rax        # 3d40 <pgot_ZSTD_decompressContinue_all_pgot+0x2c0>
			3d3c: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3d40:	jmp    3d54 <pgot_ZSTD_decompressContinue_all_pgot+0x2d4>
    3d42:	call   3d4e <pgot_ZSTD_decompressContinue_all_pgot+0x2ce>
    3d47:	pause  
    3d49:	lfence 
    3d4c:	jmp    3d47 <pgot_ZSTD_decompressContinue_all_pgot+0x2c7>
    3d4e:	mov    %rax,(%rsp)
    3d52:	ret    
    3d53:	int3   
    3d54:	call   3d42 <pgot_ZSTD_decompressContinue_all_pgot+0x2c2>
    3d59:	mov    0x60e0(%rbx),%rdx
    3d60:	mov    %r12,%rsi
    3d63:	mov    %rbx,%rdi
    3d66:	call   1130 <ZSTD_decodeFrameHeader>
    3d6b:	mov    %rax,%r12
    3d6e:	cmp    $0xffffffffffffffea,%rax
    3d72:	ja     3b7f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3dc4, pgot_memcpy_table_all_pgot

```asm
    3dbc:	jmp    3b7f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3dc1:	mov    0x0(%rip),%rax        # 3dc8 <pgot_ZSTD_decompressContinue_all_pgot+0x348>
			3dc4: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3dc8:	lea    0x26128(%rbx),%rdi
    3dcf:	mov    %rcx,%rsi
    3dd2:	xor    %r12d,%r12d
    3dd5:	mov    $0x5,%edx
    3dda:	jmp    3dee <pgot_ZSTD_decompressContinue_all_pgot+0x36e>
    3ddc:	call   3de8 <pgot_ZSTD_decompressContinue_all_pgot+0x368>
    3de1:	pause  
    3de3:	lfence 
    3de6:	jmp    3de1 <pgot_ZSTD_decompressContinue_all_pgot+0x361>
    3de8:	mov    %rax,(%rsp)
    3dec:	ret    
    3ded:	int3   
    3dee:	call   3ddc <pgot_ZSTD_decompressContinue_all_pgot+0x35c>
    3df3:	movq   $0x3,0x6060(%rbx)
    3dfe:	movl   $0x6,0x6084(%rbx)
    3e08:	jmp    3b7f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3e6f, pgot_memset_table_all_pgot

```asm
    3e69:	movzbl (%rcx),%esi
    3e6c:	mov    0x0(%rip),%rax        # 3e73 <pgot_ZSTD_decompressContinue_all_pgot+0x3f3>
			3e6f: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    3e73:	mov    %r12,%rdx
    3e76:	mov    %r13,%rdi
    3e79:	jmp    3e8d <pgot_ZSTD_decompressContinue_all_pgot+0x40d>
    3e7b:	call   3e87 <pgot_ZSTD_decompressContinue_all_pgot+0x407>
    3e80:	pause  
    3e82:	lfence 
    3e85:	jmp    3e80 <pgot_ZSTD_decompressContinue_all_pgot+0x400>
    3e87:	mov    %rax,(%rsp)
    3e8b:	ret    
    3e8c:	int3   
    3e8d:	call   3e7b <pgot_ZSTD_decompressContinue_all_pgot+0x3fb>
    3e92:	cmp    $0xffffffffffffffea,%r12
    3e96:	ja     3b7f <pgot_ZSTD_decompressContinue_all_pgot+0xff>
    3e9c:	mov    0x6078(%rbx),%edx
    3ea2:	test   %edx,%edx
    3ea4:	jne    3f41 <pgot_ZSTD_decompressContinue_all_pgot+0x4c1>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decompressContinue_all_pgot, 3efb, pgot_memcpy_table_all_pgot

```asm
    3ef5:	mov    %r13,%rdi
    3ef8:	mov    0x0(%rip),%rax        # 3eff <pgot_ZSTD_decompressContinue_all_pgot+0x47f>
			3efb: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3eff:	jmp    3f13 <pgot_ZSTD_decompressContinue_all_pgot+0x493>
    3f01:	call   3f0d <pgot_ZSTD_decompressContinue_all_pgot+0x48d>
    3f06:	pause  
    3f08:	lfence 
    3f0b:	jmp    3f06 <pgot_ZSTD_decompressContinue_all_pgot+0x486>
    3f0d:	mov    %rax,(%rsp)
    3f11:	ret    
    3f12:	int3   
    3f13:	call   3f01 <pgot_ZSTD_decompressContinue_all_pgot+0x481>
    3f18:	mov    -0x30(%rbp),%r12
    3f1c:	jmp    3e92 <pgot_ZSTD_decompressContinue_all_pgot+0x412>
    3f21:	cmp    $0x1ffff,%r8
    3f28:	ja     3cc1 <pgot_ZSTD_decompressContinue_all_pgot+0x241>
    3f2e:	mov    %r13,%rsi
    3f31:	mov    %rbx,%rdi
    3f34:	call   35d0 <ZSTD_decompressBlock_internal.part.0>
```

## 04_zstd_decompress/retpoline/all_pgot: ZSTD_decompressMultiFrame, 41de, pgot_memcpy_table_all_pgot

```asm
    41d8:	mov    %rbx,%rdi
    41db:	mov    0x0(%rip),%rax        # 41e2 <ZSTD_decompressMultiFrame+0xf2>
			41de: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    41e2:	jmp    41f6 <ZSTD_decompressMultiFrame+0x106>
    41e4:	call   41f0 <ZSTD_decompressMultiFrame+0x100>
    41e9:	pause  
    41eb:	lfence 
    41ee:	jmp    41e9 <ZSTD_decompressMultiFrame+0xf9>
    41f0:	mov    %rax,(%rsp)
    41f4:	ret    
    41f5:	int3   
    41f6:	call   41e4 <ZSTD_decompressMultiFrame+0xf4>
    41fb:	mov    -0x58(%rbp),%r8
    41ff:	mov    %r8,%r15
    4202:	mov    0x6078(%r13),%ecx
    4209:	test   %ecx,%ecx
    420b:	jne    440b <ZSTD_decompressMultiFrame+0x31b>
    4211:	mov    -0x48(%rbp),%edx
    4214:	sub    %r8,%r14
```

## 04_zstd_decompress/retpoline/all_pgot: ZSTD_decompressMultiFrame, 4452, pgot_memset_table_all_pgot

```asm
    444d:	jb     4480 <ZSTD_decompressMultiFrame+0x390>
    444f:	mov    0x0(%rip),%rax        # 4456 <ZSTD_decompressMultiFrame+0x366>
			4452: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    4456:	mov    %r15,%rdx
    4459:	mov    %rbx,%rdi
    445c:	jmp    4470 <ZSTD_decompressMultiFrame+0x380>
    445e:	call   446a <ZSTD_decompressMultiFrame+0x37a>
    4463:	pause  
    4465:	lfence 
    4468:	jmp    4463 <ZSTD_decompressMultiFrame+0x373>
    446a:	mov    %rax,(%rsp)
    446e:	ret    
    446f:	int3   
    4470:	call   445e <ZSTD_decompressMultiFrame+0x36e>
    4475:	mov    $0x1,%r8d
    447b:	jmp    4202 <ZSTD_decompressMultiFrame+0x112>
    4480:	mov    $0xfffffffffffffff4,%r15
    4487:	jmp    41ab <ZSTD_decompressMultiFrame+0xbb>
    448c:	mov    $0xfffffffffffffffe,%r15
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_initDStream_all_pgot, 49a3, pgot_memset_table_all_pgot

```asm
    499e:	xor    %esi,%esi
    49a0:	mov    0x0(%rip),%rax        # 49a7 <pgot_ZSTD_initDStream_all_pgot+0x87>
			49a3: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    49a7:	jmp    49bb <pgot_ZSTD_initDStream_all_pgot+0x9b>
    49a9:	call   49b5 <pgot_ZSTD_initDStream_all_pgot+0x95>
    49ae:	pause  
    49b0:	lfence 
    49b3:	jmp    49ae <pgot_ZSTD_initDStream_all_pgot+0x8e>
    49b5:	mov    %rax,(%rsp)
    49b9:	ret    
    49ba:	int3   
    49bb:	call   49a9 <pgot_ZSTD_initDStream_all_pgot+0x89>
    49c0:	lea    0xa0(%r12),%rdi
    49c8:	mov    $0x18,%edx
    49cd:	lea    -0x38(%rbp),%rsi
    49d1:	mov    0x0(%rip),%rax        # 49d8 <pgot_ZSTD_initDStream_all_pgot+0xb8>
			49d4: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    49d8:	jmp    49ec <pgot_ZSTD_initDStream_all_pgot+0xcc>
    49da:	call   49e6 <pgot_ZSTD_initDStream_all_pgot+0xc6>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_initDStream_all_pgot, 49d4, pgot_memcpy_table_all_pgot

```asm
    49cd:	lea    -0x38(%rbp),%rsi
    49d1:	mov    0x0(%rip),%rax        # 49d8 <pgot_ZSTD_initDStream_all_pgot+0xb8>
			49d4: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    49d8:	jmp    49ec <pgot_ZSTD_initDStream_all_pgot+0xcc>
    49da:	call   49e6 <pgot_ZSTD_initDStream_all_pgot+0xc6>
    49df:	pause  
    49e1:	lfence 
    49e4:	jmp    49df <pgot_ZSTD_initDStream_all_pgot+0xbf>
    49e6:	mov    %rax,(%rsp)
    49ea:	ret    
    49eb:	int3   
    49ec:	call   49da <pgot_ZSTD_initDStream_all_pgot+0xba>
    49f1:	push   -0x28(%rbp)
    49f4:	push   -0x30(%rbp)
    49f7:	push   -0x38(%rbp)
    49fa:	call   49ff <pgot_ZSTD_initDStream_all_pgot+0xdf>
			49fb: R_X86_64_PLT32	pgot_ZSTD_createDCtx_advanced_all_pgot-0x4
    49ff:	mov    %rax,(%r12)
    4a03:	add    $0x18,%rsp
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decompressStream_all_pgot, 4c9e, pgot_memcpy_table_all_pgot

```asm
    4c94:	sub    0x98(%rbx),%rcx
    4c9b:	mov    0x0(%rip),%rax        # 4ca2 <pgot_ZSTD_decompressStream_all_pgot+0xc2>
			4c9e: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4ca2:	sub    %r12,%rdx
    4ca5:	add    %r14,%rdi
    4ca8:	cmp    %rcx,%rdx
    4cab:	jb     51a7 <pgot_ZSTD_decompressStream_all_pgot+0x5c7>
    4cb1:	mov    %rcx,-0x40(%rbp)
    4cb5:	mov    %rcx,%rdx
    4cb8:	mov    %r12,%rsi
    4cbb:	jmp    4ccf <pgot_ZSTD_decompressStream_all_pgot+0xef>
    4cbd:	call   4cc9 <pgot_ZSTD_decompressStream_all_pgot+0xe9>
    4cc2:	pause  
    4cc4:	lfence 
    4cc7:	jmp    4cc2 <pgot_ZSTD_decompressStream_all_pgot+0xe2>
    4cc9:	mov    %rax,(%rsp)
    4ccd:	ret    
    4cce:	int3   
    4ccf:	call   4cbd <pgot_ZSTD_decompressStream_all_pgot+0xdd>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decompressStream_all_pgot, 4d8b, pgot_memcpy_table_all_pgot

```asm
    4d85:	mov    %r13,%rdi
    4d88:	mov    0x0(%rip),%rax        # 4d8f <pgot_ZSTD_decompressStream_all_pgot+0x1af>
			4d8b: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4d8f:	sub    %r13,%rcx
    4d92:	cmp    %rcx,%r15
    4d95:	mov    %rcx,%rdx
    4d98:	mov    %rcx,-0x48(%rbp)
    4d9c:	cmovbe %r15,%rdx
    4da0:	add    0x58(%rbx),%rsi
    4da4:	mov    %rdx,-0x40(%rbp)
    4da8:	jmp    4dbc <pgot_ZSTD_decompressStream_all_pgot+0x1dc>
    4daa:	call   4db6 <pgot_ZSTD_decompressStream_all_pgot+0x1d6>
    4daf:	pause  
    4db1:	lfence 
    4db4:	jmp    4daf <pgot_ZSTD_decompressStream_all_pgot+0x1cf>
    4db6:	mov    %rax,(%rsp)
    4dba:	ret    
    4dbb:	int3   
    4dbc:	call   4daa <pgot_ZSTD_decompressStream_all_pgot+0x1ca>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_ZSTD_decompressStream_all_pgot, 4e79, pgot_memcpy_table_all_pgot

```asm
    4e73:	mov    %r12,%rsi
    4e76:	mov    0x0(%rip),%rax        # 4e7d <pgot_ZSTD_decompressStream_all_pgot+0x29d>
			4e79: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4e7d:	sub    %r12,%r15
    4e80:	cmp    %rcx,%r15
    4e83:	cmova  %rcx,%r15
    4e87:	add    0x38(%rbx),%rdi
    4e8b:	mov    %r15,%rdx
    4e8e:	add    %r15,%r12
    4e91:	jmp    4ea5 <pgot_ZSTD_decompressStream_all_pgot+0x2c5>
    4e93:	call   4e9f <pgot_ZSTD_decompressStream_all_pgot+0x2bf>
    4e98:	pause  
    4e9a:	lfence 
    4e9d:	jmp    4e98 <pgot_ZSTD_decompressStream_all_pgot+0x2b8>
    4e9f:	mov    %rax,(%rsp)
    4ea3:	ret    
    4ea4:	int3   
    4ea5:	call   4e93 <pgot_ZSTD_decompressStream_all_pgot+0x2b3>
    4eaa:	mov    -0x48(%rbp),%rcx
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_FSE_readNCount_all_pgot, 279, memset

```asm
 274:	lea    (%rax,%r8,2),%rdi
 278:	call   27d <pgot_FSE_readNCount_all_pgot+0x21d>
			279: R_X86_64_PLT32	memset-0x4
 27d:	mov    -0x4c(%rbp),%r8d
 281:	mov    -0x58(%rbp),%ecx
 284:	mov    %r13d,%eax
 287:	sar    $0x3,%eax
 28a:	cltq   
 28c:	add    %r12,%rax
 28f:	cmp    -0x40(%rbp),%r12
 293:	jbe    2a2 <pgot_FSE_readNCount_all_pgot+0x242>
 295:	shr    $0x2,%ecx
 298:	cmp    -0x48(%rbp),%rax
 29c:	ja     195 <pgot_FSE_readNCount_all_pgot+0x135>
 2a2:	mov    (%rax),%esi
 2a4:	and    $0x7,%r13d
 2a8:	mov    %rax,%r12
 2ab:	mov    %r13d,%ecx
 2ae:	shr    %cl,%esi
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_readStats_wksp_all_pgot, 3bd, pgot_memset_table_all_pgot

```asm
 3b6:	mov    %r8,-0x38(%rbp)
 3ba:	mov    0x0(%rip),%rax        # 3c1 <pgot_HUF_readStats_wksp_all_pgot+0xa1>
			3bd: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
 3c1:	xor    %esi,%esi
 3c3:	mov    %r15,%rdi
 3c6:	mov    $0x34,%edx
 3cb:	jmp    3df <pgot_HUF_readStats_wksp_all_pgot+0xbf>
 3cd:	call   3d9 <pgot_HUF_readStats_wksp_all_pgot+0xb9>
 3d2:	pause  
 3d4:	lfence 
 3d7:	jmp    3d2 <pgot_HUF_readStats_wksp_all_pgot+0xb2>
 3d9:	mov    %rax,(%rsp)
 3dd:	ret    
 3de:	int3   
 3df:	call   3cd <pgot_HUF_readStats_wksp_all_pgot+0xad>
 3e4:	mov    -0x38(%rbp),%r8
 3e8:	xor    %r12d,%r12d
 3eb:	xor    %r9d,%r9d
 3ee:	xor    %eax,%eax
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_readStats_wksp_all_pgot, 47d, pgot_memset_table_all_pgot

```asm
 476:	mov    %r8,-0x38(%rbp)
 47a:	mov    0x0(%rip),%rax        # 481 <pgot_HUF_readStats_wksp_all_pgot+0x161>
			47d: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
 481:	xor    %esi,%esi
 483:	mov    %r15,%rdi
 486:	mov    $0x34,%edx
 48b:	jmp    49f <pgot_HUF_readStats_wksp_all_pgot+0x17f>
 48d:	call   499 <pgot_HUF_readStats_wksp_all_pgot+0x179>
 492:	pause  
 494:	lfence 
 497:	jmp    492 <pgot_HUF_readStats_wksp_all_pgot+0x172>
 499:	mov    %rax,(%rsp)
 49d:	ret    
 49e:	int3   
 49f:	call   48d <pgot_HUF_readStats_wksp_all_pgot+0x16d>
 4a4:	mov    -0x38(%rbp),%r8
 4a8:	test   %r8,%r8
 4ab:	jne    3e8 <pgot_HUF_readStats_wksp_all_pgot+0xc8>
 4b1:	jmp    42f <pgot_HUF_readStats_wksp_all_pgot+0x10f>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_FSE_buildDTable_wksp_all_pgot, 267, pgot_memcpy_table_all_pgot

```asm
 260:	mov    %r9,-0x50(%rbp)
 264:	mov    0x0(%rip),%rax        # 26b <pgot_FSE_buildDTable_wksp_all_pgot+0x12b>
			267: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
 26b:	jmp    27f <pgot_FSE_buildDTable_wksp_all_pgot+0x13f>
 26d:	call   279 <pgot_FSE_buildDTable_wksp_all_pgot+0x139>
 272:	pause  
 274:	lfence 
 277:	jmp    272 <pgot_FSE_buildDTable_wksp_all_pgot+0x132>
 279:	mov    %rax,(%rsp)
 27d:	ret    
 27e:	int3   
 27f:	call   26d <pgot_FSE_buildDTable_wksp_all_pgot+0x12d>
 284:	mov    -0x48(%rbp),%eax
 287:	mov    -0x50(%rbp),%r9
 28b:	xor    %r10d,%r10d
 28e:	mov    -0x58(%rbp),%rcx
 292:	mov    %eax,%edx
 294:	shr    %eax
 296:	shr    $0x3,%edx
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_fillDTableX4Level2, 4b, pgot_memcpy_table_all_pgot

```asm
      46:	xor    %eax,%eax
      48:	mov    0x0(%rip),%rax        # 4f <HUF_fillDTableX4Level2+0x4f>
			4b: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
      4f:	jmp    63 <HUF_fillDTableX4Level2+0x63>
      51:	call   5d <HUF_fillDTableX4Level2+0x5d>
      56:	pause  
      58:	lfence 
      5b:	jmp    56 <HUF_fillDTableX4Level2+0x56>
      5d:	mov    %rax,(%rsp)
      61:	ret    
      62:	int3   
      63:	call   51 <HUF_fillDTableX4Level2+0x51>
      68:	cmp    $0x1,%r12d
      6c:	mov    -0x70(%rbp),%r9d
      70:	jle    aa <HUF_fillDTableX4Level2+0xaa>
      72:	movslq %r12d,%r8
      75:	cmp    $0xc,%r8
      79:	ja     20b <HUF_fillDTableX4Level2+0x20b>
      7f:	mov    -0x64(%rbp,%r8,4),%ecx
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decodeLastSymbolX4.isra.0, 39a, pgot_memcpy_table_all_pgot

```asm
     393:	lea    (%rdx,%rax,4),%r12
     397:	mov    0x0(%rip),%rax        # 39e <HUF_decodeLastSymbolX4.isra.0+0x2e>
			39a: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     39e:	mov    $0x1,%edx
     3a3:	mov    %r12,%rsi
     3a6:	jmp    3ba <HUF_decodeLastSymbolX4.isra.0+0x4a>
     3a8:	call   3b4 <HUF_decodeLastSymbolX4.isra.0+0x44>
     3ad:	pause  
     3af:	lfence 
     3b2:	jmp    3ad <HUF_decodeLastSymbolX4.isra.0+0x3d>
     3b4:	mov    %rax,(%rsp)
     3b8:	ret    
     3b9:	int3   
     3ba:	call   3a8 <HUF_decodeLastSymbolX4.isra.0+0x38>
     3bf:	cmpb   $0x1,0x3(%r12)
     3c5:	je     3ea <HUF_decodeLastSymbolX4.isra.0+0x7a>
     3c7:	mov    0x8(%rbx),%edx
     3ca:	cmp    $0x3f,%edx
     3cd:	ja     3e4 <HUF_decodeLastSymbolX4.isra.0+0x74>
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress1X2_usingDTable_internal, 443, pgot_memcpy_table_all_pgot

```asm
     43e:	xor    %eax,%eax
     440:	mov    0x0(%rip),%rax        # 447 <HUF_decompress1X2_usingDTable_internal+0x47>
			443: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     447:	jmp    45b <HUF_decompress1X2_usingDTable_internal+0x5b>
     449:	call   455 <HUF_decompress1X2_usingDTable_internal+0x55>
     44e:	pause  
     450:	lfence 
     453:	jmp    44e <HUF_decompress1X2_usingDTable_internal+0x4e>
     455:	mov    %rax,(%rsp)
     459:	ret    
     45a:	int3   
     45b:	call   449 <HUF_decompress1X2_usingDTable_internal+0x49>
     460:	movzbl -0x4e(%rbp),%eax
     464:	mov    %r14,%rsi
     467:	lea    -0x50(%rbp),%rdi
     46b:	mov    %r13,%rdx
     46e:	mov    %al,-0x51(%rbp)
     471:	call   230 <BIT_initDStream>
     476:	mov    %rax,%rdi
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 7ba, pgot_memcpy_table_all_pgot

```asm
     7b3:	mov    %rbx,-0x60(%rbp)
     7b7:	mov    0x0(%rip),%rax        # 7be <HUF_decompress1X4_usingDTable_internal+0x6e>
			7ba: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     7be:	lea    0x4(%r14),%r12
     7c2:	jmp    7d6 <HUF_decompress1X4_usingDTable_internal+0x86>
     7c4:	call   7d0 <HUF_decompress1X4_usingDTable_internal+0x80>
     7c9:	pause  
     7cb:	lfence 
     7ce:	jmp    7c9 <HUF_decompress1X4_usingDTable_internal+0x79>
     7d0:	mov    %rax,(%rsp)
     7d4:	ret    
     7d5:	int3   
     7d6:	call   7c4 <HUF_decompress1X4_usingDTable_internal+0x74>
     7db:	movzbl -0x52(%rbp),%eax
     7df:	mov    -0x48(%rbp),%ecx
     7e2:	mov    %eax,-0x64(%rbp)
     7e5:	cmp    $0x40,%ecx
     7e8:	ja     ad2 <HUF_decompress1X4_usingDTable_internal+0x382>
     7ee:	neg    %eax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 858, pgot_memcpy_table_all_pgot

```asm
     851:	lea    (%r12,%rax,4),%r14
     855:	mov    0x0(%rip),%rax        # 85c <HUF_decompress1X4_usingDTable_internal+0x10c>
			858: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     85c:	mov    %r14,%rsi
     85f:	jmp    873 <HUF_decompress1X4_usingDTable_internal+0x123>
     861:	call   86d <HUF_decompress1X4_usingDTable_internal+0x11d>
     866:	pause  
     868:	lfence 
     86b:	jmp    866 <HUF_decompress1X4_usingDTable_internal+0x116>
     86d:	mov    %rax,(%rsp)
     871:	ret    
     872:	int3   
     873:	call   861 <HUF_decompress1X4_usingDTable_internal+0x111>
     878:	mov    -0x50(%rbp),%rax
     87c:	movzbl 0x2(%r14),%ecx
     881:	mov    $0x2,%edx
     886:	add    -0x48(%rbp),%ecx
     889:	movzbl 0x3(%r14),%edi
     88e:	mov    %ecx,-0x48(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 8a6, pgot_memcpy_table_all_pgot

```asm
     8a0:	mov    %r13,%rdi
     8a3:	mov    0x0(%rip),%rax        # 8aa <HUF_decompress1X4_usingDTable_internal+0x15a>
			8a6: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     8aa:	mov    %r14,%rsi
     8ad:	jmp    8c1 <HUF_decompress1X4_usingDTable_internal+0x171>
     8af:	call   8bb <HUF_decompress1X4_usingDTable_internal+0x16b>
     8b4:	pause  
     8b6:	lfence 
     8b9:	jmp    8b4 <HUF_decompress1X4_usingDTable_internal+0x164>
     8bb:	mov    %rax,(%rsp)
     8bf:	ret    
     8c0:	int3   
     8c1:	call   8af <HUF_decompress1X4_usingDTable_internal+0x15f>
     8c6:	movzbl 0x3(%r14),%eax
     8cb:	movzbl 0x2(%r14),%ecx
     8d0:	mov    $0x2,%edx
     8d5:	add    -0x48(%rbp),%ecx
     8d8:	add    %rax,%r13
     8db:	mov    -0x50(%rbp),%rax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 8f4, pgot_memcpy_table_all_pgot

```asm
     8ed:	lea    (%r12,%rax,4),%r14
     8f1:	mov    0x0(%rip),%rax        # 8f8 <HUF_decompress1X4_usingDTable_internal+0x1a8>
			8f4: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     8f8:	mov    %r14,%rsi
     8fb:	jmp    90f <HUF_decompress1X4_usingDTable_internal+0x1bf>
     8fd:	call   909 <HUF_decompress1X4_usingDTable_internal+0x1b9>
     902:	pause  
     904:	lfence 
     907:	jmp    902 <HUF_decompress1X4_usingDTable_internal+0x1b2>
     909:	mov    %rax,(%rsp)
     90d:	ret    
     90e:	int3   
     90f:	call   8fd <HUF_decompress1X4_usingDTable_internal+0x1ad>
     914:	mov    -0x50(%rbp),%rax
     918:	movzbl 0x2(%r14),%ecx
     91d:	mov    $0x2,%edx
     922:	add    -0x48(%rbp),%ecx
     925:	movzbl 0x3(%r14),%r9d
     92a:	mov    %ecx,-0x48(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, 942, pgot_memcpy_table_all_pgot

```asm
     93c:	mov    %r13,%rdi
     93f:	mov    0x0(%rip),%rax        # 946 <HUF_decompress1X4_usingDTable_internal+0x1f6>
			942: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     946:	mov    %r14,%rsi
     949:	jmp    95d <HUF_decompress1X4_usingDTable_internal+0x20d>
     94b:	call   957 <HUF_decompress1X4_usingDTable_internal+0x207>
     950:	pause  
     952:	lfence 
     955:	jmp    950 <HUF_decompress1X4_usingDTable_internal+0x200>
     957:	mov    %rax,(%rsp)
     95b:	ret    
     95c:	int3   
     95d:	call   94b <HUF_decompress1X4_usingDTable_internal+0x1fb>
     962:	movzbl 0x3(%r14),%eax
     967:	movzbl 0x2(%r14),%ecx
     96c:	add    -0x48(%rbp),%ecx
     96f:	mov    %ecx,-0x48(%rbp)
     972:	add    %rax,%r13
     975:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, a34, pgot_memcpy_table_all_pgot

```asm
     a2d:	lea    (%r12,%rax,4),%r14
     a31:	mov    0x0(%rip),%rax        # a38 <HUF_decompress1X4_usingDTable_internal+0x2e8>
			a34: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     a38:	mov    %r14,%rsi
     a3b:	jmp    a4f <HUF_decompress1X4_usingDTable_internal+0x2ff>
     a3d:	call   a49 <HUF_decompress1X4_usingDTable_internal+0x2f9>
     a42:	pause  
     a44:	lfence 
     a47:	jmp    a42 <HUF_decompress1X4_usingDTable_internal+0x2f2>
     a49:	mov    %rax,(%rsp)
     a4d:	ret    
     a4e:	int3   
     a4f:	call   a3d <HUF_decompress1X4_usingDTable_internal+0x2ed>
     a54:	movzbl 0x3(%r14),%edx
     a59:	movzbl 0x2(%r14),%eax
     a5e:	add    -0x48(%rbp),%eax
     a61:	mov    %eax,-0x48(%rbp)
     a64:	add    %rdx,%r13
     a67:	cmp    $0x40,%eax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress1X4_usingDTable_internal, b09, pgot_memcpy_table_all_pgot

```asm
     b02:	lea    (%r12,%rax,4),%r14
     b06:	mov    0x0(%rip),%rax        # b0d <HUF_decompress1X4_usingDTable_internal+0x3bd>
			b09: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     b0d:	mov    %r14,%rsi
     b10:	jmp    b24 <HUF_decompress1X4_usingDTable_internal+0x3d4>
     b12:	call   b1e <HUF_decompress1X4_usingDTable_internal+0x3ce>
     b17:	pause  
     b19:	lfence 
     b1c:	jmp    b17 <HUF_decompress1X4_usingDTable_internal+0x3c7>
     b1e:	mov    %rax,(%rsp)
     b22:	ret    
     b23:	int3   
     b24:	call   b12 <HUF_decompress1X4_usingDTable_internal+0x3c2>
     b29:	movzbl 0x3(%r14),%eax
     b2e:	movzbl 0x2(%r14),%ecx
     b33:	add    -0x48(%rbp),%ecx
     b36:	add    %rax,%r13
     b39:	mov    %ecx,-0x48(%rbp)
     b3c:	cmp    %rbx,%r13
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X2_usingDTable_internal, c28, pgot_memcpy_table_all_pgot

```asm
     c22:	sub    %rax,%r12
     c25:	mov    0x0(%rip),%rax        # c2c <HUF_decompress4X2_usingDTable_internal+0x8c>
			c28: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
     c2c:	jmp    c40 <HUF_decompress4X2_usingDTable_internal+0xa0>
     c2e:	call   c3a <HUF_decompress4X2_usingDTable_internal+0x9a>
     c33:	pause  
     c35:	lfence 
     c38:	jmp    c33 <HUF_decompress4X2_usingDTable_internal+0x93>
     c3a:	mov    %rax,(%rsp)
     c3e:	ret    
     c3f:	int3   
     c40:	call   c2e <HUF_decompress4X2_usingDTable_internal+0x8e>
     c45:	mov    -0xc0(%rbp),%rcx
     c4c:	movzbl -0x4e(%rbp),%eax
     c50:	mov    -0xc8(%rbp),%r9
     c57:	cmp    %r12,%rcx
     c5a:	mov    %al,-0xe0(%rbp)
     c60:	jae    c92 <HUF_decompress4X2_usingDTable_internal+0xf2>
     c62:	mov    $0xfffffffffffffff2,%r15
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 22b7, pgot_memcpy_table_all_pgot

```asm
    22b1:	sub    %rax,%r13
    22b4:	mov    0x0(%rip),%rax        # 22bb <HUF_decompress4X4_usingDTable_internal+0x8b>
			22b7: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    22bb:	jmp    22cf <HUF_decompress4X4_usingDTable_internal+0x9f>
    22bd:	call   22c9 <HUF_decompress4X4_usingDTable_internal+0x99>
    22c2:	pause  
    22c4:	lfence 
    22c7:	jmp    22c2 <HUF_decompress4X4_usingDTable_internal+0x92>
    22c9:	mov    %rax,(%rsp)
    22cd:	ret    
    22ce:	int3   
    22cf:	call   22bd <HUF_decompress4X4_usingDTable_internal+0x8d>
    22d4:	mov    -0xb8(%rbp),%rcx
    22db:	movzbl -0x4e(%rbp),%eax
    22df:	mov    -0xc0(%rbp),%r9
    22e6:	cmp    %r13,%rcx
    22e9:	mov    %al,-0xdc(%rbp)
    22ef:	jae    2321 <HUF_decompress4X4_usingDTable_internal+0xf1>
    22f1:	mov    $0xfffffffffffffff2,%r14
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2805, pgot_memcpy_table_all_pgot

```asm
    27fe:	lea    (%r12,%rax,4),%rcx
    2802:	mov    0x0(%rip),%rax        # 2809 <HUF_decompress4X4_usingDTable_internal+0x5d9>
			2805: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2809:	mov    %rcx,%rsi
    280c:	mov    %rcx,-0xc0(%rbp)
    2813:	jmp    2827 <HUF_decompress4X4_usingDTable_internal+0x5f7>
    2815:	call   2821 <HUF_decompress4X4_usingDTable_internal+0x5f1>
    281a:	pause  
    281c:	lfence 
    281f:	jmp    281a <HUF_decompress4X4_usingDTable_internal+0x5ea>
    2821:	mov    %rax,(%rsp)
    2825:	ret    
    2826:	int3   
    2827:	call   2815 <HUF_decompress4X4_usingDTable_internal+0x5e5>
    282c:	mov    -0xc0(%rbp),%rcx
    2833:	mov    %r15,%rdi
    2836:	mov    $0x2,%edx
    283b:	movzbl 0x2(%rcx),%eax
    283f:	add    %eax,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 286d, pgot_memcpy_table_all_pgot

```asm
    2866:	lea    (%r12,%rax,4),%rcx
    286a:	mov    0x0(%rip),%rax        # 2871 <HUF_decompress4X4_usingDTable_internal+0x641>
			286d: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2871:	mov    %rcx,%rsi
    2874:	mov    %rcx,-0xc0(%rbp)
    287b:	jmp    288f <HUF_decompress4X4_usingDTable_internal+0x65f>
    287d:	call   2889 <HUF_decompress4X4_usingDTable_internal+0x659>
    2882:	pause  
    2884:	lfence 
    2887:	jmp    2882 <HUF_decompress4X4_usingDTable_internal+0x652>
    2889:	mov    %rax,(%rsp)
    288d:	ret    
    288e:	int3   
    288f:	call   287d <HUF_decompress4X4_usingDTable_internal+0x64d>
    2894:	mov    -0xc0(%rbp),%rcx
    289b:	mov    %r14,%rdi
    289e:	mov    $0x2,%edx
    28a3:	movzbl 0x2(%rcx),%eax
    28a7:	add    %eax,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 28cf, pgot_memcpy_table_all_pgot

```asm
    28c8:	lea    (%r12,%rax,4),%rcx
    28cc:	mov    0x0(%rip),%rax        # 28d3 <HUF_decompress4X4_usingDTable_internal+0x6a3>
			28cf: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    28d3:	mov    %rcx,%rsi
    28d6:	mov    %rcx,-0xc0(%rbp)
    28dd:	jmp    28f1 <HUF_decompress4X4_usingDTable_internal+0x6c1>
    28df:	call   28eb <HUF_decompress4X4_usingDTable_internal+0x6bb>
    28e4:	pause  
    28e6:	lfence 
    28e9:	jmp    28e4 <HUF_decompress4X4_usingDTable_internal+0x6b4>
    28eb:	mov    %rax,(%rsp)
    28ef:	ret    
    28f0:	int3   
    28f1:	call   28df <HUF_decompress4X4_usingDTable_internal+0x6af>
    28f6:	mov    -0xc0(%rbp),%rcx
    28fd:	mov    %rbx,%rdi
    2900:	mov    $0x2,%edx
    2905:	movzbl 0x2(%rcx),%eax
    2909:	add    %eax,-0x68(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 292e, pgot_memcpy_table_all_pgot

```asm
    2927:	lea    (%r12,%rax,4),%rcx
    292b:	mov    0x0(%rip),%rax        # 2932 <HUF_decompress4X4_usingDTable_internal+0x702>
			292e: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2932:	mov    %rcx,%rsi
    2935:	mov    %rcx,-0xc0(%rbp)
    293c:	jmp    2950 <HUF_decompress4X4_usingDTable_internal+0x720>
    293e:	call   294a <HUF_decompress4X4_usingDTable_internal+0x71a>
    2943:	pause  
    2945:	lfence 
    2948:	jmp    2943 <HUF_decompress4X4_usingDTable_internal+0x713>
    294a:	mov    %rax,(%rsp)
    294e:	ret    
    294f:	int3   
    2950:	call   293e <HUF_decompress4X4_usingDTable_internal+0x70e>
    2955:	mov    -0xc0(%rbp),%rcx
    295c:	mov    %r13,%rdi
    295f:	mov    $0x2,%edx
    2964:	movzbl 0x2(%rcx),%eax
    2968:	add    %eax,-0x48(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2993, pgot_memcpy_table_all_pgot

```asm
    298c:	lea    (%r12,%rax,4),%rcx
    2990:	mov    0x0(%rip),%rax        # 2997 <HUF_decompress4X4_usingDTable_internal+0x767>
			2993: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2997:	mov    %rcx,%rsi
    299a:	mov    %rcx,-0xc0(%rbp)
    29a1:	jmp    29b5 <HUF_decompress4X4_usingDTable_internal+0x785>
    29a3:	call   29af <HUF_decompress4X4_usingDTable_internal+0x77f>
    29a8:	pause  
    29aa:	lfence 
    29ad:	jmp    29a8 <HUF_decompress4X4_usingDTable_internal+0x778>
    29af:	mov    %rax,(%rsp)
    29b3:	ret    
    29b4:	int3   
    29b5:	call   29a3 <HUF_decompress4X4_usingDTable_internal+0x773>
    29ba:	mov    -0xc0(%rbp),%rcx
    29c1:	mov    %r15,%rdi
    29c4:	mov    $0x2,%edx
    29c9:	movzbl 0x2(%rcx),%eax
    29cd:	add    %eax,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 29fb, pgot_memcpy_table_all_pgot

```asm
    29f4:	lea    (%r12,%rax,4),%rcx
    29f8:	mov    0x0(%rip),%rax        # 29ff <HUF_decompress4X4_usingDTable_internal+0x7cf>
			29fb: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    29ff:	mov    %rcx,%rsi
    2a02:	mov    %rcx,-0xc0(%rbp)
    2a09:	jmp    2a1d <HUF_decompress4X4_usingDTable_internal+0x7ed>
    2a0b:	call   2a17 <HUF_decompress4X4_usingDTable_internal+0x7e7>
    2a10:	pause  
    2a12:	lfence 
    2a15:	jmp    2a10 <HUF_decompress4X4_usingDTable_internal+0x7e0>
    2a17:	mov    %rax,(%rsp)
    2a1b:	ret    
    2a1c:	int3   
    2a1d:	call   2a0b <HUF_decompress4X4_usingDTable_internal+0x7db>
    2a22:	mov    -0xc0(%rbp),%rcx
    2a29:	mov    %r14,%rdi
    2a2c:	mov    $0x2,%edx
    2a31:	movzbl 0x2(%rcx),%eax
    2a35:	add    %eax,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2a5d, pgot_memcpy_table_all_pgot

```asm
    2a56:	lea    (%r12,%rax,4),%rcx
    2a5a:	mov    0x0(%rip),%rax        # 2a61 <HUF_decompress4X4_usingDTable_internal+0x831>
			2a5d: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2a61:	mov    %rcx,%rsi
    2a64:	mov    %rcx,-0xc0(%rbp)
    2a6b:	jmp    2a7f <HUF_decompress4X4_usingDTable_internal+0x84f>
    2a6d:	call   2a79 <HUF_decompress4X4_usingDTable_internal+0x849>
    2a72:	pause  
    2a74:	lfence 
    2a77:	jmp    2a72 <HUF_decompress4X4_usingDTable_internal+0x842>
    2a79:	mov    %rax,(%rsp)
    2a7d:	ret    
    2a7e:	int3   
    2a7f:	call   2a6d <HUF_decompress4X4_usingDTable_internal+0x83d>
    2a84:	mov    -0xc0(%rbp),%rcx
    2a8b:	mov    %rbx,%rdi
    2a8e:	mov    $0x2,%edx
    2a93:	movzbl 0x2(%rcx),%eax
    2a97:	add    %eax,-0x68(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2abc, pgot_memcpy_table_all_pgot

```asm
    2ab5:	lea    (%r12,%rax,4),%rcx
    2ab9:	mov    0x0(%rip),%rax        # 2ac0 <HUF_decompress4X4_usingDTable_internal+0x890>
			2abc: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2ac0:	mov    %rcx,%rsi
    2ac3:	mov    %rcx,-0xc0(%rbp)
    2aca:	jmp    2ade <HUF_decompress4X4_usingDTable_internal+0x8ae>
    2acc:	call   2ad8 <HUF_decompress4X4_usingDTable_internal+0x8a8>
    2ad1:	pause  
    2ad3:	lfence 
    2ad6:	jmp    2ad1 <HUF_decompress4X4_usingDTable_internal+0x8a1>
    2ad8:	mov    %rax,(%rsp)
    2adc:	ret    
    2add:	int3   
    2ade:	call   2acc <HUF_decompress4X4_usingDTable_internal+0x89c>
    2ae3:	mov    -0xc0(%rbp),%rcx
    2aea:	mov    %r13,%rdi
    2aed:	mov    $0x2,%edx
    2af2:	movzbl 0x2(%rcx),%eax
    2af6:	add    %eax,-0x48(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2b21, pgot_memcpy_table_all_pgot

```asm
    2b1a:	lea    (%r12,%rax,4),%rcx
    2b1e:	mov    0x0(%rip),%rax        # 2b25 <HUF_decompress4X4_usingDTable_internal+0x8f5>
			2b21: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2b25:	mov    %rcx,%rsi
    2b28:	mov    %rcx,-0xc0(%rbp)
    2b2f:	jmp    2b43 <HUF_decompress4X4_usingDTable_internal+0x913>
    2b31:	call   2b3d <HUF_decompress4X4_usingDTable_internal+0x90d>
    2b36:	pause  
    2b38:	lfence 
    2b3b:	jmp    2b36 <HUF_decompress4X4_usingDTable_internal+0x906>
    2b3d:	mov    %rax,(%rsp)
    2b41:	ret    
    2b42:	int3   
    2b43:	call   2b31 <HUF_decompress4X4_usingDTable_internal+0x901>
    2b48:	mov    -0xc0(%rbp),%rcx
    2b4f:	mov    %r15,%rdi
    2b52:	mov    $0x2,%edx
    2b57:	movzbl 0x2(%rcx),%eax
    2b5b:	add    %eax,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2b89, pgot_memcpy_table_all_pgot

```asm
    2b82:	lea    (%r12,%rax,4),%rcx
    2b86:	mov    0x0(%rip),%rax        # 2b8d <HUF_decompress4X4_usingDTable_internal+0x95d>
			2b89: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2b8d:	mov    %rcx,%rsi
    2b90:	mov    %rcx,-0xc0(%rbp)
    2b97:	jmp    2bab <HUF_decompress4X4_usingDTable_internal+0x97b>
    2b99:	call   2ba5 <HUF_decompress4X4_usingDTable_internal+0x975>
    2b9e:	pause  
    2ba0:	lfence 
    2ba3:	jmp    2b9e <HUF_decompress4X4_usingDTable_internal+0x96e>
    2ba5:	mov    %rax,(%rsp)
    2ba9:	ret    
    2baa:	int3   
    2bab:	call   2b99 <HUF_decompress4X4_usingDTable_internal+0x969>
    2bb0:	mov    -0xc0(%rbp),%rcx
    2bb7:	mov    %r14,%rdi
    2bba:	mov    $0x2,%edx
    2bbf:	movzbl 0x2(%rcx),%eax
    2bc3:	add    %eax,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2beb, pgot_memcpy_table_all_pgot

```asm
    2be4:	lea    (%r12,%rax,4),%rcx
    2be8:	mov    0x0(%rip),%rax        # 2bef <HUF_decompress4X4_usingDTable_internal+0x9bf>
			2beb: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2bef:	mov    %rcx,%rsi
    2bf2:	mov    %rcx,-0xc0(%rbp)
    2bf9:	jmp    2c0d <HUF_decompress4X4_usingDTable_internal+0x9dd>
    2bfb:	call   2c07 <HUF_decompress4X4_usingDTable_internal+0x9d7>
    2c00:	pause  
    2c02:	lfence 
    2c05:	jmp    2c00 <HUF_decompress4X4_usingDTable_internal+0x9d0>
    2c07:	mov    %rax,(%rsp)
    2c0b:	ret    
    2c0c:	int3   
    2c0d:	call   2bfb <HUF_decompress4X4_usingDTable_internal+0x9cb>
    2c12:	mov    -0xc0(%rbp),%rcx
    2c19:	mov    %rbx,%rdi
    2c1c:	mov    $0x2,%edx
    2c21:	movzbl 0x2(%rcx),%eax
    2c25:	add    %eax,-0x68(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2c4a, pgot_memcpy_table_all_pgot

```asm
    2c43:	lea    (%r12,%rax,4),%rcx
    2c47:	mov    0x0(%rip),%rax        # 2c4e <HUF_decompress4X4_usingDTable_internal+0xa1e>
			2c4a: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2c4e:	mov    %rcx,%rsi
    2c51:	mov    %rcx,-0xc0(%rbp)
    2c58:	jmp    2c6c <HUF_decompress4X4_usingDTable_internal+0xa3c>
    2c5a:	call   2c66 <HUF_decompress4X4_usingDTable_internal+0xa36>
    2c5f:	pause  
    2c61:	lfence 
    2c64:	jmp    2c5f <HUF_decompress4X4_usingDTable_internal+0xa2f>
    2c66:	mov    %rax,(%rsp)
    2c6a:	ret    
    2c6b:	int3   
    2c6c:	call   2c5a <HUF_decompress4X4_usingDTable_internal+0xa2a>
    2c71:	mov    -0xc0(%rbp),%rcx
    2c78:	mov    %r13,%rdi
    2c7b:	mov    $0x2,%edx
    2c80:	movzbl 0x2(%rcx),%eax
    2c84:	add    %eax,-0x48(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2caf, pgot_memcpy_table_all_pgot

```asm
    2ca8:	lea    (%r12,%rax,4),%rcx
    2cac:	mov    0x0(%rip),%rax        # 2cb3 <HUF_decompress4X4_usingDTable_internal+0xa83>
			2caf: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2cb3:	mov    %rcx,%rsi
    2cb6:	mov    %rcx,-0xc0(%rbp)
    2cbd:	jmp    2cd1 <HUF_decompress4X4_usingDTable_internal+0xaa1>
    2cbf:	call   2ccb <HUF_decompress4X4_usingDTable_internal+0xa9b>
    2cc4:	pause  
    2cc6:	lfence 
    2cc9:	jmp    2cc4 <HUF_decompress4X4_usingDTable_internal+0xa94>
    2ccb:	mov    %rax,(%rsp)
    2ccf:	ret    
    2cd0:	int3   
    2cd1:	call   2cbf <HUF_decompress4X4_usingDTable_internal+0xa8f>
    2cd6:	mov    -0xc0(%rbp),%rcx
    2cdd:	mov    %r15,%rdi
    2ce0:	mov    $0x2,%edx
    2ce5:	movzbl 0x2(%rcx),%eax
    2ce9:	add    %eax,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2d17, pgot_memcpy_table_all_pgot

```asm
    2d10:	lea    (%r12,%rax,4),%rcx
    2d14:	mov    0x0(%rip),%rax        # 2d1b <HUF_decompress4X4_usingDTable_internal+0xaeb>
			2d17: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2d1b:	mov    %rcx,%rsi
    2d1e:	mov    %rcx,-0xc0(%rbp)
    2d25:	jmp    2d39 <HUF_decompress4X4_usingDTable_internal+0xb09>
    2d27:	call   2d33 <HUF_decompress4X4_usingDTable_internal+0xb03>
    2d2c:	pause  
    2d2e:	lfence 
    2d31:	jmp    2d2c <HUF_decompress4X4_usingDTable_internal+0xafc>
    2d33:	mov    %rax,(%rsp)
    2d37:	ret    
    2d38:	int3   
    2d39:	call   2d27 <HUF_decompress4X4_usingDTable_internal+0xaf7>
    2d3e:	mov    -0xc0(%rbp),%rcx
    2d45:	mov    %r14,%rdi
    2d48:	mov    $0x2,%edx
    2d4d:	movzbl 0x2(%rcx),%eax
    2d51:	add    %eax,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2d79, pgot_memcpy_table_all_pgot

```asm
    2d72:	lea    (%r12,%rax,4),%rcx
    2d76:	mov    0x0(%rip),%rax        # 2d7d <HUF_decompress4X4_usingDTable_internal+0xb4d>
			2d79: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2d7d:	mov    %rcx,%rsi
    2d80:	mov    %rcx,-0xc0(%rbp)
    2d87:	jmp    2d9b <HUF_decompress4X4_usingDTable_internal+0xb6b>
    2d89:	call   2d95 <HUF_decompress4X4_usingDTable_internal+0xb65>
    2d8e:	pause  
    2d90:	lfence 
    2d93:	jmp    2d8e <HUF_decompress4X4_usingDTable_internal+0xb5e>
    2d95:	mov    %rax,(%rsp)
    2d99:	ret    
    2d9a:	int3   
    2d9b:	call   2d89 <HUF_decompress4X4_usingDTable_internal+0xb59>
    2da0:	mov    -0xc0(%rbp),%rcx
    2da7:	mov    $0x2,%edx
    2dac:	mov    %rbx,%rdi
    2daf:	movzbl 0x2(%rcx),%eax
    2db3:	add    %eax,-0x68(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2dd8, pgot_memcpy_table_all_pgot

```asm
    2dd1:	lea    (%r12,%rax,4),%rcx
    2dd5:	mov    0x0(%rip),%rax        # 2ddc <HUF_decompress4X4_usingDTable_internal+0xbac>
			2dd8: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2ddc:	mov    %rcx,-0xc0(%rbp)
    2de3:	mov    %rcx,%rsi
    2de6:	jmp    2dfa <HUF_decompress4X4_usingDTable_internal+0xbca>
    2de8:	call   2df4 <HUF_decompress4X4_usingDTable_internal+0xbc4>
    2ded:	pause  
    2def:	lfence 
    2df2:	jmp    2ded <HUF_decompress4X4_usingDTable_internal+0xbbd>
    2df4:	mov    %rax,(%rsp)
    2df8:	ret    
    2df9:	int3   
    2dfa:	call   2de8 <HUF_decompress4X4_usingDTable_internal+0xbb8>
    2dff:	mov    -0xc0(%rbp),%rcx
    2e06:	movzbl 0x3(%rcx),%edx
    2e0a:	movzbl 0x2(%rcx),%eax
    2e0e:	mov    -0xa8(%rbp),%ecx
    2e14:	add    -0x48(%rbp),%eax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2f53, pgot_memcpy_table_all_pgot

```asm
    2f4c:	lea    (%r12,%rax,4),%r14
    2f50:	mov    0x0(%rip),%rax        # 2f57 <HUF_decompress4X4_usingDTable_internal+0xd27>
			2f53: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2f57:	mov    %r14,%rsi
    2f5a:	jmp    2f6e <HUF_decompress4X4_usingDTable_internal+0xd3e>
    2f5c:	call   2f68 <HUF_decompress4X4_usingDTable_internal+0xd38>
    2f61:	pause  
    2f63:	lfence 
    2f66:	jmp    2f61 <HUF_decompress4X4_usingDTable_internal+0xd31>
    2f68:	mov    %rax,(%rsp)
    2f6c:	ret    
    2f6d:	int3   
    2f6e:	call   2f5c <HUF_decompress4X4_usingDTable_internal+0xd2c>
    2f73:	movzbl 0x3(%r14),%eax
    2f78:	movzbl 0x2(%r14),%ecx
    2f7d:	mov    $0x2,%edx
    2f82:	add    -0xa8(%rbp),%ecx
    2f88:	add    %rax,%r13
    2f8b:	mov    -0xb0(%rbp),%rax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 2faa, pgot_memcpy_table_all_pgot

```asm
    2fa3:	lea    (%r12,%rax,4),%r14
    2fa7:	mov    0x0(%rip),%rax        # 2fae <HUF_decompress4X4_usingDTable_internal+0xd7e>
			2faa: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    2fae:	mov    %r14,%rsi
    2fb1:	jmp    2fc5 <HUF_decompress4X4_usingDTable_internal+0xd95>
    2fb3:	call   2fbf <HUF_decompress4X4_usingDTable_internal+0xd8f>
    2fb8:	pause  
    2fba:	lfence 
    2fbd:	jmp    2fb8 <HUF_decompress4X4_usingDTable_internal+0xd88>
    2fbf:	mov    %rax,(%rsp)
    2fc3:	ret    
    2fc4:	int3   
    2fc5:	call   2fb3 <HUF_decompress4X4_usingDTable_internal+0xd83>
    2fca:	mov    -0xb0(%rbp),%rax
    2fd1:	movzbl 0x2(%r14),%ecx
    2fd6:	mov    $0x2,%edx
    2fdb:	add    -0xa8(%rbp),%ecx
    2fe1:	movzbl 0x3(%r14),%edi
    2fe6:	mov    %ecx,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3001, pgot_memcpy_table_all_pgot

```asm
    2ffb:	mov    %r13,%rdi
    2ffe:	mov    0x0(%rip),%rax        # 3005 <HUF_decompress4X4_usingDTable_internal+0xdd5>
			3001: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3005:	mov    %r14,%rsi
    3008:	jmp    301c <HUF_decompress4X4_usingDTable_internal+0xdec>
    300a:	call   3016 <HUF_decompress4X4_usingDTable_internal+0xde6>
    300f:	pause  
    3011:	lfence 
    3014:	jmp    300f <HUF_decompress4X4_usingDTable_internal+0xddf>
    3016:	mov    %rax,(%rsp)
    301a:	ret    
    301b:	int3   
    301c:	call   300a <HUF_decompress4X4_usingDTable_internal+0xdda>
    3021:	mov    -0xb0(%rbp),%rax
    3028:	movzbl 0x2(%r14),%ecx
    302d:	mov    $0x2,%edx
    3032:	add    -0xa8(%rbp),%ecx
    3038:	movzbl 0x3(%r14),%r8d
    303d:	mov    %ecx,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3058, pgot_memcpy_table_all_pgot

```asm
    3052:	mov    %r13,%rdi
    3055:	mov    0x0(%rip),%rax        # 305c <HUF_decompress4X4_usingDTable_internal+0xe2c>
			3058: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    305c:	mov    %r14,%rsi
    305f:	jmp    3073 <HUF_decompress4X4_usingDTable_internal+0xe43>
    3061:	call   306d <HUF_decompress4X4_usingDTable_internal+0xe3d>
    3066:	pause  
    3068:	lfence 
    306b:	jmp    3066 <HUF_decompress4X4_usingDTable_internal+0xe36>
    306d:	mov    %rax,(%rsp)
    3071:	ret    
    3072:	int3   
    3073:	call   3061 <HUF_decompress4X4_usingDTable_internal+0xe31>
    3078:	movzbl 0x3(%r14),%eax
    307d:	movzbl 0x2(%r14),%ecx
    3082:	add    -0xa8(%rbp),%ecx
    3088:	mov    %ecx,-0xa8(%rbp)
    308e:	add    %rax,%r13
    3091:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 320f, pgot_memcpy_table_all_pgot

```asm
    3208:	lea    (%r12,%rax,4),%r14
    320c:	mov    0x0(%rip),%rax        # 3213 <HUF_decompress4X4_usingDTable_internal+0xfe3>
			320f: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3213:	mov    %r14,%rsi
    3216:	jmp    322a <HUF_decompress4X4_usingDTable_internal+0xffa>
    3218:	call   3224 <HUF_decompress4X4_usingDTable_internal+0xff4>
    321d:	pause  
    321f:	lfence 
    3222:	jmp    321d <HUF_decompress4X4_usingDTable_internal+0xfed>
    3224:	mov    %rax,(%rsp)
    3228:	ret    
    3229:	int3   
    322a:	call   3218 <HUF_decompress4X4_usingDTable_internal+0xfe8>
    322f:	movzbl 0x3(%r14),%eax
    3234:	movzbl 0x2(%r14),%ecx
    3239:	add    -0xa8(%rbp),%ecx
    323f:	add    %rax,%r13
    3242:	mov    %ecx,-0xa8(%rbp)
    3248:	cmp    %rbx,%r13
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3322, pgot_memcpy_table_all_pgot

```asm
    331b:	lea    (%r12,%rax,4),%r14
    331f:	mov    0x0(%rip),%rax        # 3326 <HUF_decompress4X4_usingDTable_internal+0x10f6>
			3322: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3326:	mov    %r14,%rsi
    3329:	jmp    333d <HUF_decompress4X4_usingDTable_internal+0x110d>
    332b:	call   3337 <HUF_decompress4X4_usingDTable_internal+0x1107>
    3330:	pause  
    3332:	lfence 
    3335:	jmp    3330 <HUF_decompress4X4_usingDTable_internal+0x1100>
    3337:	mov    %rax,(%rsp)
    333b:	ret    
    333c:	int3   
    333d:	call   332b <HUF_decompress4X4_usingDTable_internal+0x10fb>
    3342:	movzbl 0x3(%r14),%eax
    3347:	movzbl 0x2(%r14),%ecx
    334c:	mov    $0x2,%edx
    3351:	add    -0x88(%rbp),%ecx
    3357:	add    %rax,%r13
    335a:	mov    -0x90(%rbp),%rax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3379, pgot_memcpy_table_all_pgot

```asm
    3372:	lea    (%r12,%rax,4),%r14
    3376:	mov    0x0(%rip),%rax        # 337d <HUF_decompress4X4_usingDTable_internal+0x114d>
			3379: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    337d:	mov    %r14,%rsi
    3380:	jmp    3394 <HUF_decompress4X4_usingDTable_internal+0x1164>
    3382:	call   338e <HUF_decompress4X4_usingDTable_internal+0x115e>
    3387:	pause  
    3389:	lfence 
    338c:	jmp    3387 <HUF_decompress4X4_usingDTable_internal+0x1157>
    338e:	mov    %rax,(%rsp)
    3392:	ret    
    3393:	int3   
    3394:	call   3382 <HUF_decompress4X4_usingDTable_internal+0x1152>
    3399:	mov    -0x90(%rbp),%rax
    33a0:	movzbl 0x2(%r14),%ecx
    33a5:	mov    $0x2,%edx
    33aa:	add    -0x88(%rbp),%ecx
    33b0:	movzbl 0x3(%r14),%edi
    33b5:	mov    %ecx,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 33d0, pgot_memcpy_table_all_pgot

```asm
    33ca:	mov    %r13,%rdi
    33cd:	mov    0x0(%rip),%rax        # 33d4 <HUF_decompress4X4_usingDTable_internal+0x11a4>
			33d0: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    33d4:	mov    %r14,%rsi
    33d7:	jmp    33eb <HUF_decompress4X4_usingDTable_internal+0x11bb>
    33d9:	call   33e5 <HUF_decompress4X4_usingDTable_internal+0x11b5>
    33de:	pause  
    33e0:	lfence 
    33e3:	jmp    33de <HUF_decompress4X4_usingDTable_internal+0x11ae>
    33e5:	mov    %rax,(%rsp)
    33e9:	ret    
    33ea:	int3   
    33eb:	call   33d9 <HUF_decompress4X4_usingDTable_internal+0x11a9>
    33f0:	mov    -0x90(%rbp),%rax
    33f7:	movzbl 0x2(%r14),%ecx
    33fc:	mov    $0x2,%edx
    3401:	add    -0x88(%rbp),%ecx
    3407:	movzbl 0x3(%r14),%r8d
    340c:	mov    %ecx,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3427, pgot_memcpy_table_all_pgot

```asm
    3421:	mov    %r13,%rdi
    3424:	mov    0x0(%rip),%rax        # 342b <HUF_decompress4X4_usingDTable_internal+0x11fb>
			3427: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    342b:	mov    %r14,%rsi
    342e:	jmp    3442 <HUF_decompress4X4_usingDTable_internal+0x1212>
    3430:	call   343c <HUF_decompress4X4_usingDTable_internal+0x120c>
    3435:	pause  
    3437:	lfence 
    343a:	jmp    3435 <HUF_decompress4X4_usingDTable_internal+0x1205>
    343c:	mov    %rax,(%rsp)
    3440:	ret    
    3441:	int3   
    3442:	call   3430 <HUF_decompress4X4_usingDTable_internal+0x1200>
    3447:	movzbl 0x3(%r14),%eax
    344c:	movzbl 0x2(%r14),%ecx
    3451:	add    -0x88(%rbp),%ecx
    3457:	mov    %ecx,-0x88(%rbp)
    345d:	add    %rax,%r13
    3460:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 351d, pgot_memcpy_table_all_pgot

```asm
    3516:	lea    (%r12,%rax,4),%r15
    351a:	mov    0x0(%rip),%rax        # 3521 <HUF_decompress4X4_usingDTable_internal+0x12f1>
			351d: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3521:	mov    %r15,%rsi
    3524:	jmp    3538 <HUF_decompress4X4_usingDTable_internal+0x1308>
    3526:	call   3532 <HUF_decompress4X4_usingDTable_internal+0x1302>
    352b:	pause  
    352d:	lfence 
    3530:	jmp    352b <HUF_decompress4X4_usingDTable_internal+0x12fb>
    3532:	mov    %rax,(%rsp)
    3536:	ret    
    3537:	int3   
    3538:	call   3526 <HUF_decompress4X4_usingDTable_internal+0x12f6>
    353d:	movzbl 0x3(%r15),%eax
    3542:	movzbl 0x2(%r15),%ecx
    3547:	add    -0x88(%rbp),%ecx
    354d:	add    %rax,%r14
    3550:	mov    %ecx,-0x88(%rbp)
    3556:	cmp    %rbx,%r14
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3605, pgot_memcpy_table_all_pgot

```asm
    35fe:	lea    (%r12,%rax,4),%r15
    3602:	mov    0x0(%rip),%rax        # 3609 <HUF_decompress4X4_usingDTable_internal+0x13d9>
			3605: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3609:	mov    %r15,%rsi
    360c:	jmp    3620 <HUF_decompress4X4_usingDTable_internal+0x13f0>
    360e:	call   361a <HUF_decompress4X4_usingDTable_internal+0x13ea>
    3613:	pause  
    3615:	lfence 
    3618:	jmp    3613 <HUF_decompress4X4_usingDTable_internal+0x13e3>
    361a:	mov    %rax,(%rsp)
    361e:	ret    
    361f:	int3   
    3620:	call   360e <HUF_decompress4X4_usingDTable_internal+0x13de>
    3625:	movzbl 0x3(%r15),%eax
    362a:	movzbl 0x2(%r15),%ecx
    362f:	mov    $0x2,%edx
    3634:	add    -0x68(%rbp),%ecx
    3637:	add    %rax,%r14
    363a:	mov    -0x70(%rbp),%rax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3653, pgot_memcpy_table_all_pgot

```asm
    364c:	lea    (%r12,%rax,4),%r15
    3650:	mov    0x0(%rip),%rax        # 3657 <HUF_decompress4X4_usingDTable_internal+0x1427>
			3653: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3657:	mov    %r15,%rsi
    365a:	jmp    366e <HUF_decompress4X4_usingDTable_internal+0x143e>
    365c:	call   3668 <HUF_decompress4X4_usingDTable_internal+0x1438>
    3661:	pause  
    3663:	lfence 
    3666:	jmp    3661 <HUF_decompress4X4_usingDTable_internal+0x1431>
    3668:	mov    %rax,(%rsp)
    366c:	ret    
    366d:	int3   
    366e:	call   365c <HUF_decompress4X4_usingDTable_internal+0x142c>
    3673:	movzbl 0x3(%r15),%eax
    3678:	movzbl 0x2(%r15),%ecx
    367d:	mov    $0x2,%edx
    3682:	add    -0x68(%rbp),%ecx
    3685:	add    %rax,%r14
    3688:	mov    -0x70(%rbp),%rax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 36a1, pgot_memcpy_table_all_pgot

```asm
    369a:	lea    (%r12,%rax,4),%r15
    369e:	mov    0x0(%rip),%rax        # 36a5 <HUF_decompress4X4_usingDTable_internal+0x1475>
			36a1: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    36a5:	mov    %r15,%rsi
    36a8:	jmp    36bc <HUF_decompress4X4_usingDTable_internal+0x148c>
    36aa:	call   36b6 <HUF_decompress4X4_usingDTable_internal+0x1486>
    36af:	pause  
    36b1:	lfence 
    36b4:	jmp    36af <HUF_decompress4X4_usingDTable_internal+0x147f>
    36b6:	mov    %rax,(%rsp)
    36ba:	ret    
    36bb:	int3   
    36bc:	call   36aa <HUF_decompress4X4_usingDTable_internal+0x147a>
    36c1:	mov    -0x70(%rbp),%rax
    36c5:	movzbl 0x2(%r15),%ecx
    36ca:	mov    $0x2,%edx
    36cf:	add    -0x68(%rbp),%ecx
    36d2:	movzbl 0x3(%r15),%edi
    36d7:	mov    %ecx,-0x68(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 36f0, pgot_memcpy_table_all_pgot

```asm
    36ea:	mov    %r15,%rdi
    36ed:	mov    0x0(%rip),%rax        # 36f4 <HUF_decompress4X4_usingDTable_internal+0x14c4>
			36f0: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    36f4:	mov    %r14,%rsi
    36f7:	jmp    370b <HUF_decompress4X4_usingDTable_internal+0x14db>
    36f9:	call   3705 <HUF_decompress4X4_usingDTable_internal+0x14d5>
    36fe:	pause  
    3700:	lfence 
    3703:	jmp    36fe <HUF_decompress4X4_usingDTable_internal+0x14ce>
    3705:	mov    %rax,(%rsp)
    3709:	ret    
    370a:	int3   
    370b:	call   36f9 <HUF_decompress4X4_usingDTable_internal+0x14c9>
    3710:	movzbl 0x3(%r14),%eax
    3715:	movzbl 0x2(%r14),%ecx
    371a:	add    -0x68(%rbp),%ecx
    371d:	mov    %ecx,-0x68(%rbp)
    3720:	lea    (%r15,%rax,1),%r14
    3724:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 37f8, pgot_memcpy_table_all_pgot

```asm
    37f1:	lea    (%r12,%rax,4),%r15
    37f5:	mov    0x0(%rip),%rax        # 37fc <HUF_decompress4X4_usingDTable_internal+0x15cc>
			37f8: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    37fc:	mov    %r15,%rsi
    37ff:	jmp    3813 <HUF_decompress4X4_usingDTable_internal+0x15e3>
    3801:	call   380d <HUF_decompress4X4_usingDTable_internal+0x15dd>
    3806:	pause  
    3808:	lfence 
    380b:	jmp    3806 <HUF_decompress4X4_usingDTable_internal+0x15d6>
    380d:	mov    %rax,(%rsp)
    3811:	ret    
    3812:	int3   
    3813:	call   3801 <HUF_decompress4X4_usingDTable_internal+0x15d1>
    3818:	movzbl 0x3(%r15),%edx
    381d:	movzbl 0x2(%r15),%eax
    3822:	add    -0x68(%rbp),%eax
    3825:	mov    %eax,-0x68(%rbp)
    3828:	add    %rdx,%r14
    382b:	cmp    $0x40,%eax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3998, pgot_memcpy_table_all_pgot

```asm
    3991:	lea    (%r12,%rax,4),%r13
    3995:	mov    0x0(%rip),%rax        # 399c <HUF_decompress4X4_usingDTable_internal+0x176c>
			3998: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    399c:	mov    %r13,%rsi
    399f:	jmp    39b3 <HUF_decompress4X4_usingDTable_internal+0x1783>
    39a1:	call   39ad <HUF_decompress4X4_usingDTable_internal+0x177d>
    39a6:	pause  
    39a8:	lfence 
    39ab:	jmp    39a6 <HUF_decompress4X4_usingDTable_internal+0x1776>
    39ad:	mov    %rax,(%rsp)
    39b1:	ret    
    39b2:	int3   
    39b3:	call   39a1 <HUF_decompress4X4_usingDTable_internal+0x1771>
    39b8:	movzbl 0x3(%r13),%edx
    39bd:	movzbl 0x2(%r13),%eax
    39c2:	add    -0xa8(%rbp),%eax
    39c8:	mov    %eax,-0xa8(%rbp)
    39ce:	add    %rdx,%rbx
    39d1:	cmp    $0x40,%eax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3af9, pgot_memcpy_table_all_pgot

```asm
    3af2:	lea    (%r12,%rax,4),%rbx
    3af6:	mov    0x0(%rip),%rax        # 3afd <HUF_decompress4X4_usingDTable_internal+0x18cd>
			3af9: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3afd:	mov    %rbx,%rsi
    3b00:	jmp    3b14 <HUF_decompress4X4_usingDTable_internal+0x18e4>
    3b02:	call   3b0e <HUF_decompress4X4_usingDTable_internal+0x18de>
    3b07:	pause  
    3b09:	lfence 
    3b0c:	jmp    3b07 <HUF_decompress4X4_usingDTable_internal+0x18d7>
    3b0e:	mov    %rax,(%rsp)
    3b12:	ret    
    3b13:	int3   
    3b14:	call   3b02 <HUF_decompress4X4_usingDTable_internal+0x18d2>
    3b19:	movzbl 0x3(%rbx),%edx
    3b1d:	movzbl 0x2(%rbx),%eax
    3b21:	add    -0x88(%rbp),%eax
    3b27:	mov    %eax,-0x88(%rbp)
    3b2d:	add    %rdx,%r15
    3b30:	cmp    $0x40,%eax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3bd0, pgot_memcpy_table_all_pgot

```asm
    3bc9:	lea    (%r12,%rax,4),%r13
    3bcd:	mov    0x0(%rip),%rax        # 3bd4 <HUF_decompress4X4_usingDTable_internal+0x19a4>
			3bd0: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3bd4:	mov    %r13,%rsi
    3bd7:	jmp    3beb <HUF_decompress4X4_usingDTable_internal+0x19bb>
    3bd9:	call   3be5 <HUF_decompress4X4_usingDTable_internal+0x19b5>
    3bde:	pause  
    3be0:	lfence 
    3be3:	jmp    3bde <HUF_decompress4X4_usingDTable_internal+0x19ae>
    3be5:	mov    %rax,(%rsp)
    3be9:	ret    
    3bea:	int3   
    3beb:	call   3bd9 <HUF_decompress4X4_usingDTable_internal+0x19a9>
    3bf0:	movzbl 0x3(%r13),%eax
    3bf5:	movzbl 0x2(%r13),%ecx
    3bfa:	add    -0x68(%rbp),%ecx
    3bfd:	add    %rax,%r14
    3c00:	mov    %ecx,-0x68(%rbp)
    3c03:	cmp    %rbx,%r14
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3c99, pgot_memcpy_table_all_pgot

```asm
    3c92:	lea    (%r12,%rax,4),%r15
    3c96:	mov    0x0(%rip),%rax        # 3c9d <HUF_decompress4X4_usingDTable_internal+0x1a6d>
			3c99: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3c9d:	mov    %r15,%rsi
    3ca0:	jmp    3cb4 <HUF_decompress4X4_usingDTable_internal+0x1a84>
    3ca2:	call   3cae <HUF_decompress4X4_usingDTable_internal+0x1a7e>
    3ca7:	pause  
    3ca9:	lfence 
    3cac:	jmp    3ca7 <HUF_decompress4X4_usingDTable_internal+0x1a77>
    3cae:	mov    %rax,(%rsp)
    3cb2:	ret    
    3cb3:	int3   
    3cb4:	call   3ca2 <HUF_decompress4X4_usingDTable_internal+0x1a72>
    3cb9:	movzbl 0x3(%r15),%eax
    3cbe:	movzbl 0x2(%r15),%ecx
    3cc3:	mov    $0x2,%edx
    3cc8:	add    -0x48(%rbp),%ecx
    3ccb:	add    %rax,%r13
    3cce:	mov    -0x50(%rbp),%rax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3ce7, pgot_memcpy_table_all_pgot

```asm
    3ce0:	lea    (%r12,%rax,4),%r15
    3ce4:	mov    0x0(%rip),%rax        # 3ceb <HUF_decompress4X4_usingDTable_internal+0x1abb>
			3ce7: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3ceb:	mov    %r15,%rsi
    3cee:	jmp    3d02 <HUF_decompress4X4_usingDTable_internal+0x1ad2>
    3cf0:	call   3cfc <HUF_decompress4X4_usingDTable_internal+0x1acc>
    3cf5:	pause  
    3cf7:	lfence 
    3cfa:	jmp    3cf5 <HUF_decompress4X4_usingDTable_internal+0x1ac5>
    3cfc:	mov    %rax,(%rsp)
    3d00:	ret    
    3d01:	int3   
    3d02:	call   3cf0 <HUF_decompress4X4_usingDTable_internal+0x1ac0>
    3d07:	movzbl 0x3(%r15),%eax
    3d0c:	movzbl 0x2(%r15),%ecx
    3d11:	mov    $0x2,%edx
    3d16:	add    -0x48(%rbp),%ecx
    3d19:	add    %rax,%r13
    3d1c:	mov    -0x50(%rbp),%rax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3d35, pgot_memcpy_table_all_pgot

```asm
    3d2e:	lea    (%r12,%rax,4),%r15
    3d32:	mov    0x0(%rip),%rax        # 3d39 <HUF_decompress4X4_usingDTable_internal+0x1b09>
			3d35: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3d39:	mov    %r15,%rsi
    3d3c:	jmp    3d50 <HUF_decompress4X4_usingDTable_internal+0x1b20>
    3d3e:	call   3d4a <HUF_decompress4X4_usingDTable_internal+0x1b1a>
    3d43:	pause  
    3d45:	lfence 
    3d48:	jmp    3d43 <HUF_decompress4X4_usingDTable_internal+0x1b13>
    3d4a:	mov    %rax,(%rsp)
    3d4e:	ret    
    3d4f:	int3   
    3d50:	call   3d3e <HUF_decompress4X4_usingDTable_internal+0x1b0e>
    3d55:	movzbl 0x3(%r15),%eax
    3d5a:	movzbl 0x2(%r15),%ecx
    3d5f:	mov    $0x2,%edx
    3d64:	add    -0x48(%rbp),%ecx
    3d67:	add    %rax,%r13
    3d6a:	mov    -0x50(%rbp),%rax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3d83, pgot_memcpy_table_all_pgot

```asm
    3d7c:	lea    (%r12,%rax,4),%r15
    3d80:	mov    0x0(%rip),%rax        # 3d87 <HUF_decompress4X4_usingDTable_internal+0x1b57>
			3d83: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3d87:	mov    %r15,%rsi
    3d8a:	jmp    3d9e <HUF_decompress4X4_usingDTable_internal+0x1b6e>
    3d8c:	call   3d98 <HUF_decompress4X4_usingDTable_internal+0x1b68>
    3d91:	pause  
    3d93:	lfence 
    3d96:	jmp    3d91 <HUF_decompress4X4_usingDTable_internal+0x1b61>
    3d98:	mov    %rax,(%rsp)
    3d9c:	ret    
    3d9d:	int3   
    3d9e:	call   3d8c <HUF_decompress4X4_usingDTable_internal+0x1b5c>
    3da3:	movzbl 0x3(%r15),%eax
    3da8:	movzbl 0x2(%r15),%ecx
    3dad:	add    -0x48(%rbp),%ecx
    3db0:	mov    %ecx,-0x48(%rbp)
    3db3:	add    %rax,%r13
    3db6:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3e7b, pgot_memcpy_table_all_pgot

```asm
    3e74:	lea    (%r12,%rax,4),%r15
    3e78:	mov    0x0(%rip),%rax        # 3e7f <HUF_decompress4X4_usingDTable_internal+0x1c4f>
			3e7b: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3e7f:	mov    %r15,%rsi
    3e82:	jmp    3e96 <HUF_decompress4X4_usingDTable_internal+0x1c66>
    3e84:	call   3e90 <HUF_decompress4X4_usingDTable_internal+0x1c60>
    3e89:	pause  
    3e8b:	lfence 
    3e8e:	jmp    3e89 <HUF_decompress4X4_usingDTable_internal+0x1c59>
    3e90:	mov    %rax,(%rsp)
    3e94:	ret    
    3e95:	int3   
    3e96:	call   3e84 <HUF_decompress4X4_usingDTable_internal+0x1c54>
    3e9b:	movzbl 0x3(%r15),%edx
    3ea0:	movzbl 0x2(%r15),%eax
    3ea5:	add    -0x48(%rbp),%eax
    3ea8:	mov    %eax,-0x48(%rbp)
    3eab:	add    %rdx,%r13
    3eae:	cmp    $0x40,%eax
```

## 04_zstd_decompress/retpoline/all_pgot: HUF_decompress4X4_usingDTable_internal, 3f56, pgot_memcpy_table_all_pgot

```asm
    3f4f:	lea    (%r12,%rax,4),%r15
    3f53:	mov    0x0(%rip),%rax        # 3f5a <HUF_decompress4X4_usingDTable_internal+0x1d2a>
			3f56: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    3f5a:	mov    %r15,%rsi
    3f5d:	jmp    3f71 <HUF_decompress4X4_usingDTable_internal+0x1d41>
    3f5f:	call   3f6b <HUF_decompress4X4_usingDTable_internal+0x1d3b>
    3f64:	pause  
    3f66:	lfence 
    3f69:	jmp    3f64 <HUF_decompress4X4_usingDTable_internal+0x1d34>
    3f6b:	mov    %rax,(%rsp)
    3f6f:	ret    
    3f70:	int3   
    3f71:	call   3f5f <HUF_decompress4X4_usingDTable_internal+0x1d2f>
    3f76:	movzbl 0x3(%r15),%eax
    3f7b:	movzbl 0x2(%r15),%ecx
    3f80:	add    -0x48(%rbp),%ecx
    3f83:	add    %rax,%r13
    3f86:	mov    %ecx,-0x48(%rbp)
    3f89:	cmp    %rbx,%r13
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_readDTableX2_wksp_all_pgot, 4240, pgot_memcpy_table_all_pgot

```asm
    4238:	mov    $0x4,%edx
    423d:	mov    0x0(%rip),%rax        # 4244 <pgot_HUF_readDTableX2_wksp_all_pgot+0xa4>
			4240: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4244:	mov    %rbx,%rsi
    4247:	lea    -0x34(%rbp),%rdi
    424b:	jmp    425f <pgot_HUF_readDTableX2_wksp_all_pgot+0xbf>
    424d:	call   4259 <pgot_HUF_readDTableX2_wksp_all_pgot+0xb9>
    4252:	pause  
    4254:	lfence 
    4257:	jmp    4252 <pgot_HUF_readDTableX2_wksp_all_pgot+0xb2>
    4259:	mov    %rax,(%rsp)
    425d:	ret    
    425e:	int3   
    425f:	call   424d <pgot_HUF_readDTableX2_wksp_all_pgot+0xad>
    4264:	movzbl -0x34(%rbp),%eax
    4268:	mov    -0x3c(%rbp),%edx
    426b:	add    $0x1,%eax
    426e:	cmp    %edx,%eax
    4270:	jb     437d <pgot_HUF_readDTableX2_wksp_all_pgot+0x1dd>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_readDTableX2_wksp_all_pgot, 4283, pgot_memcpy_table_all_pgot

```asm
    427d:	mov    %rbx,%rdi
    4280:	mov    0x0(%rip),%rax        # 4287 <pgot_HUF_readDTableX2_wksp_all_pgot+0xe7>
			4283: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4287:	movb   $0x0,-0x33(%rbp)
    428b:	mov    $0x4,%edx
    4290:	jmp    42a4 <pgot_HUF_readDTableX2_wksp_all_pgot+0x104>
    4292:	call   429e <pgot_HUF_readDTableX2_wksp_all_pgot+0xfe>
    4297:	pause  
    4299:	lfence 
    429c:	jmp    4297 <pgot_HUF_readDTableX2_wksp_all_pgot+0xf7>
    429e:	mov    %rax,(%rsp)
    42a2:	ret    
    42a3:	int3   
    42a4:	call   4292 <pgot_HUF_readDTableX2_wksp_all_pgot+0xf2>
    42a9:	mov    -0x3c(%rbp),%r9d
    42ad:	lea    0x1(%r9),%esi
    42b1:	cmp    $0x1,%esi
    42b4:	jbe    42f8 <pgot_HUF_readDTableX2_wksp_all_pgot+0x158>
    42b6:	mov    0x4(%r12),%r10d
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress1X2_usingDTable_all_pgot, 43d3, pgot_memcpy_table_all_pgot

```asm
    43ce:	xor    %eax,%eax
    43d0:	mov    0x0(%rip),%rax        # 43d7 <pgot_HUF_decompress1X2_usingDTable_all_pgot+0x47>
			43d3: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    43d7:	jmp    43eb <pgot_HUF_decompress1X2_usingDTable_all_pgot+0x5b>
    43d9:	call   43e5 <pgot_HUF_decompress1X2_usingDTable_all_pgot+0x55>
    43de:	pause  
    43e0:	lfence 
    43e3:	jmp    43de <pgot_HUF_decompress1X2_usingDTable_all_pgot+0x4e>
    43e5:	mov    %rax,(%rsp)
    43e9:	ret    
    43ea:	int3   
    43eb:	call   43d9 <pgot_HUF_decompress1X2_usingDTable_all_pgot+0x49>
    43f0:	cmpb   $0x0,-0x33(%rbp)
    43f4:	mov    $0xffffffffffffffff,%rax
    43fb:	jne    4411 <pgot_HUF_decompress1X2_usingDTable_all_pgot+0x81>
    43fd:	mov    %rbx,%r8
    4400:	mov    %r15,%rcx
    4403:	mov    %r14,%rdx
    4406:	mov    %r13,%rsi
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress4X2_usingDTable_all_pgot, 4513, pgot_memcpy_table_all_pgot

```asm
    450e:	xor    %eax,%eax
    4510:	mov    0x0(%rip),%rax        # 4517 <pgot_HUF_decompress4X2_usingDTable_all_pgot+0x47>
			4513: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4517:	jmp    452b <pgot_HUF_decompress4X2_usingDTable_all_pgot+0x5b>
    4519:	call   4525 <pgot_HUF_decompress4X2_usingDTable_all_pgot+0x55>
    451e:	pause  
    4520:	lfence 
    4523:	jmp    451e <pgot_HUF_decompress4X2_usingDTable_all_pgot+0x4e>
    4525:	mov    %rax,(%rsp)
    4529:	ret    
    452a:	int3   
    452b:	call   4519 <pgot_HUF_decompress4X2_usingDTable_all_pgot+0x49>
    4530:	cmpb   $0x0,-0x33(%rbp)
    4534:	mov    $0xffffffffffffffff,%rax
    453b:	jne    4551 <pgot_HUF_decompress4X2_usingDTable_all_pgot+0x81>
    453d:	mov    %rbx,%r8
    4540:	mov    %r15,%rcx
    4543:	mov    %r14,%rdx
    4546:	mov    %r13,%rsi
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_readDTableX4_wksp_all_pgot, 4658, pgot_memcpy_table_all_pgot

```asm
    4653:	xor    %eax,%eax
    4655:	mov    0x0(%rip),%rax        # 465c <pgot_HUF_readDTableX4_wksp_all_pgot+0x4c>
			4658: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    465c:	jmp    4670 <pgot_HUF_readDTableX4_wksp_all_pgot+0x60>
    465e:	call   466a <pgot_HUF_readDTableX4_wksp_all_pgot+0x5a>
    4663:	pause  
    4665:	lfence 
    4668:	jmp    4663 <pgot_HUF_readDTableX4_wksp_all_pgot+0x53>
    466a:	mov    %rax,(%rsp)
    466e:	ret    
    466f:	int3   
    4670:	call   465e <pgot_HUF_readDTableX4_wksp_all_pgot+0x4e>
    4675:	movzbl -0x68(%rbp),%r12d
    467a:	mov    %r12b,-0xbd(%rbp)
    4681:	cmp    $0x5db,%rbx
    4688:	jbe    4a56 <pgot_HUF_readDTableX4_wksp_all_pgot+0x446>
    468e:	lea    0x270(%r14),%r15
    4695:	xor    %esi,%esi
    4697:	mov    $0x6c,%edx
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_readDTableX4_wksp_all_pgot, 469f, pgot_memset_table_all_pgot

```asm
    4697:	mov    $0x6c,%edx
    469c:	mov    0x0(%rip),%rax        # 46a3 <pgot_HUF_readDTableX4_wksp_all_pgot+0x93>
			469f: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    46a3:	mov    %r15,%rdi
    46a6:	jmp    46ba <pgot_HUF_readDTableX4_wksp_all_pgot+0xaa>
    46a8:	call   46b4 <pgot_HUF_readDTableX4_wksp_all_pgot+0xa4>
    46ad:	pause  
    46af:	lfence 
    46b2:	jmp    46ad <pgot_HUF_readDTableX4_wksp_all_pgot+0x9d>
    46b4:	mov    %rax,(%rsp)
    46b8:	ret    
    46b9:	int3   
    46ba:	call   46a8 <pgot_HUF_readDTableX4_wksp_all_pgot+0x98>
    46bf:	cmp    $0xc,%r12d
    46c3:	ja     4a56 <pgot_HUF_readDTableX4_wksp_all_pgot+0x446>
    46c9:	mov    %r13,%r9
    46cc:	lea    -0x70(%rbp),%r8
    46d0:	lea    -0x6c(%rbp),%rcx
    46d4:	mov    %r15,%rdx
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_readDTableX4_wksp_all_pgot, 48c6, pgot_memcpy_table_all_pgot

```asm
    48bd:	mov    %eax,-0xb8(%rbp)
    48c3:	mov    0x0(%rip),%rax        # 48ca <pgot_HUF_readDTableX4_wksp_all_pgot+0x2ba>
			48c6: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    48ca:	jmp    48de <pgot_HUF_readDTableX4_wksp_all_pgot+0x2ce>
    48cc:	call   48d8 <pgot_HUF_readDTableX4_wksp_all_pgot+0x2c8>
    48d1:	pause  
    48d3:	lfence 
    48d6:	jmp    48d1 <pgot_HUF_readDTableX4_wksp_all_pgot+0x2c1>
    48d8:	mov    %rax,(%rsp)
    48dc:	ret    
    48dd:	int3   
    48de:	call   48cc <pgot_HUF_readDTableX4_wksp_all_pgot+0x2bc>
    48e3:	mov    -0x84(%rbp),%r10d
    48ea:	test   %r10d,%r10d
    48ed:	je     4a8b <pgot_HUF_readDTableX4_wksp_all_pgot+0x47b>
    48f3:	lea    -0x1(%r10),%eax
    48f7:	sub    %ebx,%r12d
    48fa:	mov    %r14,%r11
    48fd:	mov    %r10d,-0xbc(%rbp)
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_readDTableX4_wksp_all_pgot, 4aa9, pgot_memcpy_table_all_pgot

```asm
    4aa3:	mov    %al,-0x66(%rbp)
    4aa6:	mov    0x0(%rip),%rax        # 4aad <pgot_HUF_readDTableX4_wksp_all_pgot+0x49d>
			4aa9: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4aad:	jmp    4ac1 <pgot_HUF_readDTableX4_wksp_all_pgot+0x4b1>
    4aaf:	call   4abb <pgot_HUF_readDTableX4_wksp_all_pgot+0x4ab>
    4ab4:	pause  
    4ab6:	lfence 
    4ab9:	jmp    4ab4 <pgot_HUF_readDTableX4_wksp_all_pgot+0x4a4>
    4abb:	mov    %rax,(%rsp)
    4abf:	ret    
    4ac0:	int3   
    4ac1:	call   4aaf <pgot_HUF_readDTableX4_wksp_all_pgot+0x49f>
    4ac6:	jmp    4a61 <pgot_HUF_readDTableX4_wksp_all_pgot+0x451>
    4ac8:	lea    0x1(%r11),%r8d
    4acc:	mov    %r11d,%eax
    4acf:	jmp    4749 <pgot_HUF_readDTableX4_wksp_all_pgot+0x139>
    4ad4:	mov    -0x6c(%rbp),%ebx
    4ad7:	lea    0x2dc(%r14),%rsi
    4ade:	xor    %r10d,%r10d
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress1X4_usingDTable_all_pgot, 4bd3, pgot_memcpy_table_all_pgot

```asm
    4bce:	xor    %eax,%eax
    4bd0:	mov    0x0(%rip),%rax        # 4bd7 <pgot_HUF_decompress1X4_usingDTable_all_pgot+0x47>
			4bd3: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4bd7:	jmp    4beb <pgot_HUF_decompress1X4_usingDTable_all_pgot+0x5b>
    4bd9:	call   4be5 <pgot_HUF_decompress1X4_usingDTable_all_pgot+0x55>
    4bde:	pause  
    4be0:	lfence 
    4be3:	jmp    4bde <pgot_HUF_decompress1X4_usingDTable_all_pgot+0x4e>
    4be5:	mov    %rax,(%rsp)
    4be9:	ret    
    4bea:	int3   
    4beb:	call   4bd9 <pgot_HUF_decompress1X4_usingDTable_all_pgot+0x49>
    4bf0:	cmpb   $0x1,-0x33(%rbp)
    4bf4:	mov    $0xffffffffffffffff,%rax
    4bfb:	jne    4c11 <pgot_HUF_decompress1X4_usingDTable_all_pgot+0x81>
    4bfd:	mov    %rbx,%r8
    4c00:	mov    %r15,%rcx
    4c03:	mov    %r14,%rdx
    4c06:	mov    %r13,%rsi
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress4X4_usingDTable_all_pgot, 4d13, pgot_memcpy_table_all_pgot

```asm
    4d0e:	xor    %eax,%eax
    4d10:	mov    0x0(%rip),%rax        # 4d17 <pgot_HUF_decompress4X4_usingDTable_all_pgot+0x47>
			4d13: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4d17:	jmp    4d2b <pgot_HUF_decompress4X4_usingDTable_all_pgot+0x5b>
    4d19:	call   4d25 <pgot_HUF_decompress4X4_usingDTable_all_pgot+0x55>
    4d1e:	pause  
    4d20:	lfence 
    4d23:	jmp    4d1e <pgot_HUF_decompress4X4_usingDTable_all_pgot+0x4e>
    4d25:	mov    %rax,(%rsp)
    4d29:	ret    
    4d2a:	int3   
    4d2b:	call   4d19 <pgot_HUF_decompress4X4_usingDTable_all_pgot+0x49>
    4d30:	cmpb   $0x1,-0x33(%rbp)
    4d34:	mov    $0xffffffffffffffff,%rax
    4d3b:	jne    4d51 <pgot_HUF_decompress4X4_usingDTable_all_pgot+0x81>
    4d3d:	mov    %rbx,%r8
    4d40:	mov    %r15,%rcx
    4d43:	mov    %r14,%rdx
    4d46:	mov    %r13,%rsi
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress1X_usingDTable_all_pgot, 4e53, pgot_memcpy_table_all_pgot

```asm
    4e4e:	xor    %eax,%eax
    4e50:	mov    0x0(%rip),%rax        # 4e57 <pgot_HUF_decompress1X_usingDTable_all_pgot+0x47>
			4e53: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4e57:	jmp    4e6b <pgot_HUF_decompress1X_usingDTable_all_pgot+0x5b>
    4e59:	call   4e65 <pgot_HUF_decompress1X_usingDTable_all_pgot+0x55>
    4e5e:	pause  
    4e60:	lfence 
    4e63:	jmp    4e5e <pgot_HUF_decompress1X_usingDTable_all_pgot+0x4e>
    4e65:	mov    %rax,(%rsp)
    4e69:	ret    
    4e6a:	int3   
    4e6b:	call   4e59 <pgot_HUF_decompress1X_usingDTable_all_pgot+0x49>
    4e70:	cmpb   $0x0,-0x33(%rbp)
    4e74:	mov    %rbx,%r8
    4e77:	mov    %r15,%rcx
    4e7a:	mov    %r14,%rdx
    4e7d:	mov    %r13,%rsi
    4e80:	mov    %r12,%rdi
    4e83:	je     4ea9 <pgot_HUF_decompress1X_usingDTable_all_pgot+0x99>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress4X_usingDTable_all_pgot, 4f03, pgot_memcpy_table_all_pgot

```asm
    4efe:	xor    %eax,%eax
    4f00:	mov    0x0(%rip),%rax        # 4f07 <pgot_HUF_decompress4X_usingDTable_all_pgot+0x47>
			4f03: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    4f07:	jmp    4f1b <pgot_HUF_decompress4X_usingDTable_all_pgot+0x5b>
    4f09:	call   4f15 <pgot_HUF_decompress4X_usingDTable_all_pgot+0x55>
    4f0e:	pause  
    4f10:	lfence 
    4f13:	jmp    4f0e <pgot_HUF_decompress4X_usingDTable_all_pgot+0x4e>
    4f15:	mov    %rax,(%rsp)
    4f19:	ret    
    4f1a:	int3   
    4f1b:	call   4f09 <pgot_HUF_decompress4X_usingDTable_all_pgot+0x49>
    4f20:	cmpb   $0x0,-0x33(%rbp)
    4f24:	mov    %rbx,%r8
    4f27:	mov    %r15,%rcx
    4f2a:	mov    %r14,%rdx
    4f2d:	mov    %r13,%rsi
    4f30:	mov    %r12,%rdi
    4f33:	je     4f59 <pgot_HUF_decompress4X_usingDTable_all_pgot+0x99>
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_selectDecoder_all_pgot, 4f96, pgot_algoTime_all_pgot

```asm
    4f8f:	lea    (%rax,%rax,2),%rdx
    4f93:	mov    0x0(%rip),%rax        # 4f9a <pgot_HUF_selectDecoder_all_pgot+0x2a>
			4f96: R_X86_64_PC32	pgot_algoTime_all_pgot-0x4
    4f9a:	lea    (%rax,%rdx,8),%rdx
    4f9e:	mov    0xc(%rdx),%eax
    4fa1:	imul   %ecx,%eax
    4fa4:	add    0x8(%rdx),%eax
    4fa7:	mov    %eax,%esi
    4fa9:	imul   0x4(%rdx),%ecx
    4fad:	add    (%rdx),%ecx
    4faf:	shr    $0x3,%esi
    4fb2:	add    %esi,%eax
    4fb4:	cmp    %eax,%ecx
    4fb6:	seta   %al
    4fb9:	movzbl %al,%eax
    4fbc:	ret    
    4fbd:	int3   
    4fbe:	xchg   %ax,%ax

```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress4X_DCtx_wksp_all_pgot, 5038, pgot_algoTime_all_pgot

```asm
    5031:	lea    (%rax,%rax,2),%rdx
    5035:	mov    0x0(%rip),%rax        # 503c <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x7c>
			5038: R_X86_64_PC32	pgot_algoTime_all_pgot-0x4
    503c:	lea    (%rax,%rdx,8),%rdx
    5040:	mov    0xc(%rdx),%eax
    5043:	imul   %edi,%eax
    5046:	add    0x8(%rdx),%eax
    5049:	mov    %eax,%r8d
    504c:	imul   0x4(%rdx),%edi
    5050:	add    (%rdx),%edi
    5052:	mov    %r15,%rdx
    5055:	shr    $0x3,%r8d
    5059:	add    %r8d,%eax
    505c:	mov    0x10(%rbp),%r8
    5060:	cmp    %eax,%edi
    5062:	mov    %rbx,%rdi
    5065:	jbe    50b6 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xf6>
    5067:	call   506c <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xac>
			5068: R_X86_64_PLT32	pgot_HUF_readDTableX4_wksp_all_pgot-0x4
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress4X_DCtx_wksp_all_pgot, 50f3, pgot_memcpy_table_all_pgot

```asm
    50ee:	jmp    50a3 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xe3>
    50f0:	mov    0x0(%rip),%rax        # 50f7 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x137>
			50f3: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    50f7:	mov    %r14,%rdi
    50fa:	mov    %r12,%r13
    50fd:	jmp    5111 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x151>
    50ff:	call   510b <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x14b>
    5104:	pause  
    5106:	lfence 
    5109:	jmp    5104 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x144>
    510b:	mov    %rax,(%rsp)
    510f:	ret    
    5110:	int3   
    5111:	call   50ff <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x13f>
    5116:	jmp    50a3 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xe3>
    5118:	movzbl (%rcx),%esi
    511b:	mov    0x0(%rip),%rax        # 5122 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x162>
			511e: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    5122:	mov    %r14,%rdi
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress4X_DCtx_wksp_all_pgot, 511e, pgot_memset_table_all_pgot

```asm
    5118:	movzbl (%rcx),%esi
    511b:	mov    0x0(%rip),%rax        # 5122 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x162>
			511e: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    5122:	mov    %r14,%rdi
    5125:	mov    %r12,%r13
    5128:	jmp    513c <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x17c>
    512a:	call   5136 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x176>
    512f:	pause  
    5131:	lfence 
    5134:	jmp    512f <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x16f>
    5136:	mov    %rax,(%rsp)
    513a:	ret    
    513b:	int3   
    513c:	call   512a <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0x16a>
    5141:	jmp    50a3 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xe3>
    5146:	mov    $0xfffffffffffffff3,%r13
    514d:	jmp    50a3 <pgot_HUF_decompress4X_DCtx_wksp_all_pgot+0xe3>
    5152:	data16 cs nopw 0x0(%rax,%rax,1)
    515d:	nopl   (%rax)
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress4X_hufOnly_wksp_all_pgot, 51cb, pgot_algoTime_all_pgot

```asm
    51c4:	lea    (%rax,%rax,2),%rdx
    51c8:	mov    0x0(%rip),%rax        # 51cf <pgot_HUF_decompress4X_hufOnly_wksp_all_pgot+0x6f>
			51cb: R_X86_64_PC32	pgot_algoTime_all_pgot-0x4
    51cf:	lea    (%rax,%rdx,8),%rdx
    51d3:	mov    0xc(%rdx),%eax
    51d6:	imul   %edi,%eax
    51d9:	add    0x8(%rdx),%eax
    51dc:	mov    %eax,%r8d
    51df:	imul   0x4(%rdx),%edi
    51e3:	add    (%rdx),%edi
    51e5:	mov    %rbx,%rdx
    51e8:	shr    $0x3,%r8d
    51ec:	add    %r8d,%eax
    51ef:	mov    0x10(%rbp),%r8
    51f3:	cmp    %eax,%edi
    51f5:	mov    %r14,%rdi
    51f8:	jbe    5245 <pgot_HUF_decompress4X_hufOnly_wksp_all_pgot+0xe5>
    51fa:	call   51ff <pgot_HUF_decompress4X_hufOnly_wksp_all_pgot+0x9f>
			51fb: R_X86_64_PLT32	pgot_HUF_readDTableX4_wksp_all_pgot-0x4
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress1X_DCtx_wksp_all_pgot, 5318, pgot_algoTime_all_pgot

```asm
    5311:	lea    (%rax,%rax,2),%rdx
    5315:	mov    0x0(%rip),%rax        # 531c <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x7c>
			5318: R_X86_64_PC32	pgot_algoTime_all_pgot-0x4
    531c:	lea    (%rax,%rdx,8),%rdx
    5320:	mov    0xc(%rdx),%eax
    5323:	imul   %edi,%eax
    5326:	add    0x8(%rdx),%eax
    5329:	mov    %eax,%r8d
    532c:	imul   0x4(%rdx),%edi
    5330:	add    (%rdx),%edi
    5332:	mov    %r15,%rdx
    5335:	shr    $0x3,%r8d
    5339:	add    %r8d,%eax
    533c:	mov    0x10(%rbp),%r8
    5340:	cmp    %eax,%edi
    5342:	mov    %rbx,%rdi
    5345:	jbe    5396 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xf6>
    5347:	call   534c <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xac>
			5348: R_X86_64_PLT32	pgot_HUF_readDTableX4_wksp_all_pgot-0x4
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress1X_DCtx_wksp_all_pgot, 53d3, pgot_memcpy_table_all_pgot

```asm
    53ce:	jmp    5383 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xe3>
    53d0:	mov    0x0(%rip),%rax        # 53d7 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x137>
			53d3: R_X86_64_PC32	pgot_memcpy_table_all_pgot-0x4
    53d7:	mov    %r14,%rdi
    53da:	mov    %r12,%r13
    53dd:	jmp    53f1 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x151>
    53df:	call   53eb <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x14b>
    53e4:	pause  
    53e6:	lfence 
    53e9:	jmp    53e4 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x144>
    53eb:	mov    %rax,(%rsp)
    53ef:	ret    
    53f0:	int3   
    53f1:	call   53df <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x13f>
    53f6:	jmp    5383 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xe3>
    53f8:	movzbl (%rcx),%esi
    53fb:	mov    0x0(%rip),%rax        # 5402 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x162>
			53fe: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    5402:	mov    %r14,%rdi
```

## 04_zstd_decompress/retpoline/all_pgot: pgot_HUF_decompress1X_DCtx_wksp_all_pgot, 53fe, pgot_memset_table_all_pgot

```asm
    53f8:	movzbl (%rcx),%esi
    53fb:	mov    0x0(%rip),%rax        # 5402 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x162>
			53fe: R_X86_64_PC32	pgot_memset_table_all_pgot-0x4
    5402:	mov    %r14,%rdi
    5405:	mov    %r12,%r13
    5408:	jmp    541c <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x17c>
    540a:	call   5416 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x176>
    540f:	pause  
    5411:	lfence 
    5414:	jmp    540f <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x16f>
    5416:	mov    %rax,(%rsp)
    541a:	ret    
    541b:	int3   
    541c:	call   540a <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0x16a>
    5421:	jmp    5383 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xe3>
    5426:	mov    $0xfffffffffffffff3,%r13
    542d:	jmp    5383 <pgot_HUF_decompress1X_DCtx_wksp_all_pgot+0xe3>

Disassembly of section .text.unlikely:
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_execSequenceLast7_data_pgot.isra.0, 5e6, memmove

```asm
     5e2:	mov    %r13,%rdx
     5e5:	call   5ea <pgot_ZSTD_execSequenceLast7_data_pgot.isra.0+0xea>
			5e6: R_X86_64_PLT32	memmove-0x4
     5ea:	mov    0x18(%rbp),%rsi
     5ee:	lea    (%rax,%r13,1),%rax
     5f2:	cmp    %rax,%rbx
     5f5:	jbe    61e <pgot_ZSTD_execSequenceLast7_data_pgot.isra.0+0x11e>
     5f7:	sub    %rax,%rbx
     5fa:	xor    %edx,%edx
     5fc:	movzbl (%rsi,%rdx,1),%ecx
     600:	mov    %cl,(%rax,%rdx,1)
     603:	add    $0x1,%rdx
     607:	cmp    %rbx,%rdx
     60a:	jne    5fc <pgot_ZSTD_execSequenceLast7_data_pgot.isra.0+0xfc>
     60c:	pop    %rbx
     60d:	mov    %r12,%rax
     610:	pop    %r12
     612:	pop    %r13
     614:	pop    %rbp
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_execSequenceLast7_data_pgot.isra.0, 65f, memmove

```asm
     65b:	mov    %r10,%rdx
     65e:	call   663 <pgot_ZSTD_execSequenceLast7_data_pgot.isra.0+0x163>
			65f: R_X86_64_PLT32	memmove-0x4
     663:	jmp    61e <pgot_ZSTD_execSequenceLast7_data_pgot.isra.0+0x11e>
     665:	data16 cs nopw 0x0(%rax,%rax,1)

```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_copyDCtx_data_pgot, def, memcpy

```asm
     deb:	mov    %rsp,%rbp
     dee:	call   df3 <pgot_ZSTD_copyDCtx_data_pgot+0x13>
			def: R_X86_64_PLT32	memcpy-0x4
     df3:	pop    %rbp
     df4:	ret    
     df5:	int3   
     df6:	cs nopw 0x0(%rax,%rax,1)

```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decodeLiteralsBlock_data_pgot, 1282, memcpy

```asm
    127e:	mov    %rcx,%rdi
    1281:	call   1286 <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x96>
			1282: R_X86_64_PLT32	memcpy-0x4
    1286:	mov    %rbx,0x6110(%r12)
    128e:	mov    %rax,0x60f0(%r12)
    1296:	movq   $0x0,(%rax,%rbx,1)
    129e:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x104>
    12a0:	mov    0x6088(%r12),%esi
    12a8:	mov    $0xffffffffffffffed,%r13
    12af:	test   %esi,%esi
    12b1:	je     12f4 <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x104>
    12b3:	cmp    $0x4,%rdx
    12b7:	jbe    12ed <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0xfd>
    12b9:	mov    (%rdi),%r8d
    12bc:	shr    $0x2,%al
    12bf:	and    $0x3,%eax
    12c2:	mov    %r8d,%ecx
    12c5:	shr    $0x4,%ecx
    12c8:	cmp    $0x2,%al
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decodeLiteralsBlock_data_pgot, 1427, memset

```asm
    1423:	mov    %rcx,%rdi
    1426:	call   142b <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x23b>
			1427: R_X86_64_PLT32	memset-0x4
    142b:	mov    %rbx,0x6110(%r12)
    1433:	mov    %rax,0x60f0(%r12)
    143b:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x104>
    1440:	add    %rdi,%rsi
    1443:	mov    %rbx,0x6110(%r12)
    144b:	mov    %rsi,0x60f0(%r12)
    1453:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x104>
    1458:	movzbl 0x2(%rsi),%ebx
    145c:	movzwl (%rsi),%eax
    145f:	mov    $0x3,%esi
    1464:	shl    $0x10,%ebx
    1467:	add    %eax,%ebx
    1469:	shr    $0x4,%ebx
    146c:	jmp    125a <pgot_ZSTD_decodeLiteralsBlock_data_pgot+0x6a>
    1471:	movzbl 0x2(%rsi),%ebx
    1475:	movzwl (%rsi),%eax
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decodeSeqHeaders_data_pgot, 15e0, pgot_LL_defaultDTable_data_pgot

```asm
    15db:	sub    %r9,%rax
    15de:	push   0x0(%rip)        # 15e4 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x94>
			15e0: R_X86_64_PC32	pgot_LL_defaultDTable_data_pgot-0x4
    15e4:	push   %rax
    15e5:	call   400 <ZSTD_buildSeqTable.constprop.0>
    15ea:	mov    -0x30(%rbp),%r9
    15ee:	add    $0x20,%rsp
    15f2:	cmp    $0xffffffffffffffea,%rax
    15f6:	ja     16e7 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x197>
    15fc:	push   %r15
    15fe:	add    %rax,%r9
    1601:	mov    0x608c(%r13),%eax
    1608:	mov    %r14d,%edx
    160b:	shr    $0x4,%dl
    160e:	lea    0x10(%r13),%rsi
    1612:	mov    $0x1c,%ecx
    1617:	mov    %r9,-0x30(%rbp)
    161b:	push   %rax
    161c:	mov    %rbx,%rax
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decodeSeqHeaders_data_pgot, 162e, pgot_OF_defaultDTable_data_pgot

```asm
    1629:	sub    %r9,%rax
    162c:	push   0x0(%rip)        # 1632 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0xe2>
			162e: R_X86_64_PC32	pgot_OF_defaultDTable_data_pgot-0x4
    1632:	mov    $0x8,%r8d
    1638:	push   %rax
    1639:	call   400 <ZSTD_buildSeqTable.constprop.0>
    163e:	add    $0x20,%rsp
    1642:	cmp    $0xffffffffffffffea,%rax
    1646:	ja     16e7 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x197>
    164c:	mov    -0x30(%rbp),%r9
    1650:	push   %r15
    1652:	mov    %r14d,%edx
    1655:	lea    0x8(%r13),%rsi
    1659:	shr    $0x2,%dl
    165c:	mov    $0x9,%r8d
    1662:	mov    $0x34,%ecx
    1667:	add    %rax,%r9
    166a:	mov    0x608c(%r13),%eax
    1671:	and    $0x3,%edx
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decodeSeqHeaders_data_pgot, 1685, pgot_ML_defaultDTable_data_pgot

```asm
    1682:	push   %rax
    1683:	push   0x0(%rip)        # 1689 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x139>
			1685: R_X86_64_PC32	pgot_ML_defaultDTable_data_pgot-0x4
    1689:	push   %rbx
    168a:	call   400 <ZSTD_buildSeqTable.constprop.0>
    168f:	add    $0x20,%rsp
    1693:	cmp    $0xffffffffffffffea,%rax
    1697:	ja     16e7 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x197>
    1699:	mov    -0x30(%rbp),%r9
    169d:	add    %r9,%rax
    16a0:	sub    %r12,%rax
    16a3:	jmp    16ee <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x19e>
    16a5:	cmp    $0xff,%eax
    16aa:	je     1719 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x1c9>
    16ac:	cmp    %r9,%rbx
    16af:	jbe    16d0 <pgot_ZSTD_decodeSeqHeaders_data_pgot+0x180>
    16b1:	lea    0x2(%rdx),%r9
    16b5:	add    $0xffffff80,%eax
    16b8:	movzbl 0x1(%rdx),%edx
```

## 04_zstd_decompress/retpoline/data_pgot: ZSTD_decompressSequencesLong, 1854, memcpy

```asm
    1850:	mov    %r11,%rdi
    1853:	call   1858 <ZSTD_decompressSequencesLong+0x118>
			1854: R_X86_64_PLT32	memcpy-0x4
    1858:	add    %rax,%rbx
    185b:	sub    -0x118(%rbp),%rbx
    1862:	mov    %rbx,%r12
    1865:	mov    -0x38(%rbp),%rax
    1869:	sub    %gs:0x28,%rax
    1872:	jne    24ab <ZSTD_decompressSequencesLong+0xd6b>
    1878:	lea    -0x30(%rbp),%rsp
    187c:	mov    %r12,%rax
    187f:	pop    %rbx
    1880:	pop    %r10
    1882:	pop    %r12
    1884:	pop    %r13
    1886:	pop    %r14
    1888:	pop    %r15
    188a:	pop    %rbp
    188b:	lea    -0x8(%r10),%rsp
```

## 04_zstd_decompress/retpoline/data_pgot: ZSTD_decompressSequencesLong, 1d5a, memmove

```asm
    1d52:	mov    %r10,-0x158(%rbp)
    1d59:	call   1d5e <ZSTD_decompressSequencesLong+0x61e>
			1d5a: R_X86_64_PLT32	memmove-0x4
    1d5e:	mov    -0x140(%rbp),%rdx
    1d65:	mov    -0x170(%rbp),%r11
    1d6c:	mov    %rax,%rdi
    1d6f:	mov    -0x178(%rbp),%r9
    1d76:	sub    %rdx,%r11
    1d79:	add    %rdx,%rdi
    1d7c:	cmp    $0x2,%r11
    1d80:	jbe    2464 <ZSTD_decompressSequencesLong+0xd24>
    1d86:	cmp    %r13,%rdi
    1d89:	mov    -0x158(%rbp),%r10
    1d90:	mov    -0x160(%rbp),%r8
    1d97:	mov    %r14,%rsi
    1d9a:	ja     2464 <ZSTD_decompressSequencesLong+0xd24>
    1da0:	cmp    $0x7,%r10
    1da4:	ja     2400 <ZSTD_decompressSequencesLong+0xcc0>
    1daa:	movzbl (%rsi),%eax
```

## 04_zstd_decompress/retpoline/data_pgot: ZSTD_decompressSequencesLong, 200e, memmove

```asm
    2006:	mov    %r8,-0x180(%rbp)
    200d:	call   2012 <ZSTD_decompressSequencesLong+0x8d2>
			200e: R_X86_64_PLT32	memmove-0x4
    2012:	mov    -0x170(%rbp),%rcx
    2019:	mov    -0x158(%rbp),%r9
    2020:	mov    %rax,%rdi
    2023:	mov    -0x178(%rbp),%r10d
    202a:	add    %rbx,%rdi
    202d:	sub    %rbx,%rcx
    2030:	cmp    %rdi,%r9
    2033:	jb     204d <ZSTD_decompressSequencesLong+0x90d>
    2035:	cmp    $0x2,%rcx
    2039:	mov    -0x128(%rbp),%rsi
    2040:	mov    -0x180(%rbp),%r8
    2047:	ja     20d6 <ZSTD_decompressSequencesLong+0x996>
    204d:	test   %rcx,%rcx
    2050:	je     2071 <ZSTD_decompressSequencesLong+0x931>
    2052:	mov    -0x128(%rbp),%r8
    2059:	xor    %edx,%edx
```

## 04_zstd_decompress/retpoline/data_pgot: ZSTD_decompressSequencesLong, 235a, memmove

```asm
    2352:	mov    %r10d,-0x158(%rbp)
    2359:	call   235e <ZSTD_decompressSequencesLong+0xc1e>
			235a: R_X86_64_PLT32	memmove-0x4
    235e:	mov    -0x158(%rbp),%r10d
    2365:	jmp    2071 <ZSTD_decompressSequencesLong+0x931>
    236a:	mov    %rbx,%r14
    236d:	mov    %r13,%r11
    2370:	mov    -0x160(%rbp),%rbx
    2377:	mov    %r10d,%r13d
    237a:	jmp    1c42 <ZSTD_decompressSequencesLong+0x502>
    237f:	push   -0x138(%rbp)
    2385:	mov    %r10,%r8
    2388:	mov    %r11,%rcx
    238b:	mov    %rbx,%rdi
    238e:	push   -0x148(%rbp)
    2394:	lea    -0xe0(%rbp),%r9
    239b:	mov    -0x130(%rbp),%rsi
    23a2:	push   %r14
    23a4:	push   -0x120(%rbp)
```

## 04_zstd_decompress/retpoline/data_pgot: ZSTD_decompressSequencesLong, 249b, memmove

```asm
    2493:	mov    %r9,-0x140(%rbp)
    249a:	call   249f <ZSTD_decompressSequencesLong+0xd5f>
			249b: R_X86_64_PLT32	memmove-0x4
    249f:	mov    -0x140(%rbp),%r9
    24a6:	jmp    1e28 <ZSTD_decompressSequencesLong+0x6e8>
    24ab:	call   24b0 <ZSTD_decompressSequencesLong+0xd70>
			24ac: R_X86_64_PLT32	__stack_chk_fail-0x4
    24b0:	mov    -0xe0(%rbp),%rax
    24b7:	mov    -0x68(%rbp),%rdx
    24bb:	mov    %rax,%r14
    24be:	mov    %edx,0x6030(%rbx)
    24c4:	mov    -0x60(%rbp),%rdx
    24c8:	mov    %edx,0x6034(%rbx)
    24ce:	mov    -0x58(%rbp),%rdx
    24d2:	mov    %edx,0x6038(%rbx)
    24d8:	jmp    182a <ZSTD_decompressSequencesLong+0xea>
    24dd:	mov    %rbx,%r11
    24e0:	mov    -0x128(%rbp),%rbx
    24e7:	jmp    24b7 <ZSTD_decompressSequencesLong+0xd77>
```

## 04_zstd_decompress/retpoline/data_pgot: ZSTD_decompressSequences, 2601, memcpy

```asm
    25fd:	mov    %r13,%rdi
    2600:	call   2605 <ZSTD_decompressSequences+0x105>
			2601: R_X86_64_PLT32	memcpy-0x4
    2605:	lea    0x0(%r13,%rbx,1),%rax
    260a:	sub    -0xd0(%rbp),%rax
    2611:	mov    %rax,%r14
    2614:	mov    -0x30(%rbp),%rax
    2618:	sub    %gs:0x28,%rax
    2621:	jne    3015 <ZSTD_decompressSequences+0xb15>
    2627:	lea    -0x28(%rbp),%rsp
    262b:	mov    %r14,%rax
    262e:	pop    %rbx
    262f:	pop    %r12
    2631:	pop    %r13
    2633:	pop    %r14
    2635:	pop    %r15
    2637:	pop    %rbp
    2638:	ret    
    2639:	int3   
```

## 04_zstd_decompress/retpoline/data_pgot: ZSTD_decompressSequences, 2b82, memmove

```asm
    2b7a:	mov    %rdx,-0xc8(%rbp)
    2b81:	call   2b86 <ZSTD_decompressSequences+0x686>
			2b82: R_X86_64_PLT32	memmove-0x4
    2b86:	mov    -0xc8(%rbp),%rdx
    2b8d:	mov    -0x110(%rbp),%rcx
    2b94:	mov    %rax,%rdi
    2b97:	add    %rdx,%rdi
    2b9a:	add    %rcx,%r12
    2b9d:	cmp    %rdi,%r15
    2ba0:	jb     2bb3 <ZSTD_decompressSequences+0x6b3>
    2ba2:	mov    -0xf0(%rbp),%rcx
    2ba9:	cmp    $0x2,%r12
    2bad:	ja     2cee <ZSTD_decompressSequences+0x7ee>
    2bb3:	test   %r12,%r12
    2bb6:	je     2d8f <ZSTD_decompressSequences+0x88f>
    2bbc:	mov    -0xf0(%rbp),%rsi
    2bc3:	xor    %edx,%edx
    2bc5:	xor    %eax,%eax
    2bc7:	movzbl (%rsi,%rax,1),%ecx
```

## 04_zstd_decompress/retpoline/data_pgot: ZSTD_decompressSequences, 2e98, memmove

```asm
    2e94:	mov    %r12,%rdx
    2e97:	call   2e9c <ZSTD_decompressSequences+0x99c>
			2e98: R_X86_64_PLT32	memmove-0x4
    2e9c:	jmp    2d8f <ZSTD_decompressSequences+0x88f>
    2ea1:	mov    -0x58(%rbp),%rcx
    2ea5:	cmp    $0x1,%rcx
    2ea9:	adc    $0x0,%rcx
    2ead:	mov    %rcx,-0x108(%rbp)
    2eb4:	mov    %esi,%ebx
    2eb6:	mov    -0x118(%rbp),%rdi
    2ebd:	mov    %rdi,-0x58(%rbp)
    2ec1:	mov    -0x108(%rbp),%rdi
    2ec8:	mov    %rdi,-0x60(%rbp)
    2ecc:	jmp    299c <ZSTD_decompressSequences+0x49c>
    2ed1:	mov    -0xc8(%rbp),%rcx
    2ed8:	mov    -0xe0(%rbp),%rdx
    2edf:	add    $0x8,%rcx
    2ee3:	add    $0x8,%rdx
    2ee7:	mov    (%rcx),%rsi
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_generateNxBytes_data_pgot, 33e9, memset

```asm
    33e5:	mov    %rcx,%rbx
    33e8:	call   33ed <pgot_ZSTD_generateNxBytes_data_pgot+0x1d>
			33e9: R_X86_64_PLT32	memset-0x4
    33ed:	mov    %rbx,%rax
    33f0:	mov    -0x8(%rbp),%rbx
    33f4:	leave  
    33f5:	ret    
    33f6:	int3   
    33f7:	mov    $0xfffffffffffffff4,%rax
    33fe:	ret    
    33ff:	int3   

```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decompressContinue_data_pgot, 3963, memcpy

```asm
    395f:	xor    %r12d,%r12d
    3962:	call   3967 <pgot_ZSTD_decompressContinue_data_pgot+0x247>
			3963: R_X86_64_PLT32	memcpy-0x4
    3967:	mov    0x2612c(%rbx),%eax
    396d:	movl   $0x7,0x6084(%rbx)
    3977:	mov    %rax,0x6060(%rbx)
    397e:	jmp    381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    3983:	lea    0x26128(%rbx),%r13
    398a:	mov    %r8,%rdx
    398d:	mov    %rcx,%rsi
    3990:	lea    0x2612d(%rbx),%rdi
    3997:	call   399c <pgot_ZSTD_decompressContinue_data_pgot+0x27c>
			3998: R_X86_64_PLT32	memcpy-0x4
    399c:	mov    0x60e0(%rbx),%rdx
    39a3:	mov    %r13,%rsi
    39a6:	mov    %rbx,%rdi
    39a9:	call   10a0 <ZSTD_decodeFrameHeader>
    39ae:	mov    %rax,%r12
    39b1:	cmp    $0xffffffffffffffea,%rax
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decompressContinue_data_pgot, 3998, memcpy

```asm
    3990:	lea    0x2612d(%rbx),%rdi
    3997:	call   399c <pgot_ZSTD_decompressContinue_data_pgot+0x27c>
			3998: R_X86_64_PLT32	memcpy-0x4
    399c:	mov    0x60e0(%rbx),%rdx
    39a3:	mov    %r13,%rsi
    39a6:	mov    %rbx,%rdi
    39a9:	call   10a0 <ZSTD_decodeFrameHeader>
    39ae:	mov    %rax,%r12
    39b1:	cmp    $0xffffffffffffffea,%rax
    39b5:	ja     381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    39bb:	movq   $0x3,0x6060(%rbx)
    39c6:	xor    %r12d,%r12d
    39c9:	movl   $0x2,0x6084(%rbx)
    39d3:	jmp    381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    39d8:	mov    0x6080(%rbx),%eax
    39de:	cmp    $0x1,%eax
    39e1:	je     3a73 <pgot_ZSTD_decompressContinue_data_pgot+0x353>
    39e7:	cmp    $0x2,%eax
    39ea:	je     3b08 <pgot_ZSTD_decompressContinue_data_pgot+0x3e8>
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decompressContinue_data_pgot, 3a97, memset

```asm
    3a93:	mov    %r13,%rdi
    3a96:	call   3a9b <pgot_ZSTD_decompressContinue_data_pgot+0x37b>
			3a97: R_X86_64_PLT32	memset-0x4
    3a9b:	cmp    $0xffffffffffffffea,%r12
    3a9f:	ja     381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    3aa5:	mov    0x6078(%rbx),%edx
    3aab:	test   %edx,%edx
    3aad:	jne    3b28 <pgot_ZSTD_decompressContinue_data_pgot+0x408>
    3aaf:	cmpl   $0x4,0x6084(%rbx)
    3ab6:	je     3b88 <pgot_ZSTD_decompressContinue_data_pgot+0x468>
    3abc:	movl   $0x2,0x6084(%rbx)
    3ac6:	add    %r12,%r13
    3ac9:	movq   $0x3,0x6060(%rbx)
    3ad4:	mov    %r13,0x6040(%rbx)
    3adb:	jmp    381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    3ae0:	mov    $0xfffffffffffffff4,%r12
    3ae7:	cmp    %rdx,%r8
    3aea:	ja     381f <pgot_ZSTD_decompressContinue_data_pgot+0xff>
    3af0:	mov    %r8,%rdx
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decompressContinue_data_pgot, 3afe, memcpy

```asm
    3af9:	mov    %r8,-0x30(%rbp)
    3afd:	call   3b02 <pgot_ZSTD_decompressContinue_data_pgot+0x3e2>
			3afe: R_X86_64_PLT32	memcpy-0x4
    3b02:	mov    -0x30(%rbp),%r12
    3b06:	jmp    3a9b <pgot_ZSTD_decompressContinue_data_pgot+0x37b>
    3b08:	cmp    $0x1ffff,%r8
    3b0f:	ja     393a <pgot_ZSTD_decompressContinue_data_pgot+0x21a>
    3b15:	mov    %r13,%rsi
    3b18:	mov    %rbx,%rdi
    3b1b:	call   3290 <ZSTD_decompressBlock_internal.part.0>
    3b20:	mov    %rax,%r12
    3b23:	jmp    3a9b <pgot_ZSTD_decompressContinue_data_pgot+0x37b>
    3b28:	lea    0x6090(%rbx),%rdi
    3b2f:	mov    %r12,%rdx
    3b32:	mov    %r13,%rsi
    3b35:	call   3b3a <pgot_ZSTD_decompressContinue_data_pgot+0x41a>
			3b36: R_X86_64_PLT32	xxh64_update-0x4
    3b3a:	cmpl   $0x4,0x6084(%rbx)
    3b41:	jne    3abc <pgot_ZSTD_decompressContinue_data_pgot+0x39c>
```

## 04_zstd_decompress/retpoline/data_pgot: ZSTD_decompressMultiFrame, 3dc8, memcpy

```asm
    3dc3:	mov    %r8,-0x58(%rbp)
    3dc7:	call   3dcc <ZSTD_decompressMultiFrame+0xec>
			3dc8: R_X86_64_PLT32	memcpy-0x4
    3dcc:	mov    -0x58(%rbp),%r8
    3dd0:	mov    %r8,%r15
    3dd3:	mov    0x6078(%r13),%ecx
    3dda:	test   %ecx,%ecx
    3ddc:	jne    3fd9 <ZSTD_decompressMultiFrame+0x2f9>
    3de2:	mov    -0x48(%rbp),%edx
    3de5:	sub    %r8,%r14
    3de8:	add    %r15,%rbx
    3deb:	lea    (%r12,%r8,1),%r11
    3def:	mov    %r14,%r9
    3df2:	test   %edx,%edx
    3df4:	jne    404b <ZSTD_decompressMultiFrame+0x36b>
    3dfa:	cmp    $0x2,%r14
    3dfe:	ja     3f12 <ZSTD_decompressMultiFrame+0x232>
    3e04:	mov    $0xfffffffffffffff3,%r15
    3e0b:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
```

## 04_zstd_decompress/retpoline/data_pgot: ZSTD_decompressMultiFrame, 4024, memset

```asm
    4020:	mov    %rbx,%rdi
    4023:	call   4028 <ZSTD_decompressMultiFrame+0x348>
			4024: R_X86_64_PLT32	memset-0x4
    4028:	mov    $0x1,%r8d
    402e:	jmp    3dd3 <ZSTD_decompressMultiFrame+0xf3>
    4033:	mov    $0xfffffffffffffff4,%r15
    403a:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
    403f:	mov    $0xfffffffffffffffe,%r15
    4046:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
    404b:	mov    0x6078(%r13),%eax
    4052:	mov    %rbx,%r15
    4055:	mov    -0x60(%rbp),%r14
    4059:	mov    %r9,%rbx
    405c:	test   %eax,%eax
    405e:	jne    407c <ZSTD_decompressMultiFrame+0x39c>
    4060:	mov    %r15,%r12
    4063:	sub    %r14,%r12
    4066:	cmp    $0xffffffffffffffea,%r12
    406a:	ja     3f8d <ZSTD_decompressMultiFrame+0x2ad>
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decompressStream_data_pgot, 4855, memcpy

```asm
    4850:	mov    %rcx,-0x40(%rbp)
    4854:	call   4859 <pgot_ZSTD_decompressStream_data_pgot+0xd9>
			4855: R_X86_64_PLT32	memcpy-0x4
    4859:	mov    -0x40(%rbp),%rcx
    485d:	mov    0x30(%rbx),%eax
    4860:	mov    %r15,0x98(%rbx)
    4867:	add    %rcx,%r12
    486a:	cmp    $0x2,%eax
    486d:	jne    47ef <pgot_ZSTD_decompressStream_data_pgot+0x6f>
    486f:	mov    (%rbx),%rdi
    4872:	mov    0x6060(%rdi),%r8
    4879:	test   %r8,%r8
    487c:	jne    4b3e <pgot_ZSTD_decompressStream_data_pgot+0x3be>
    4882:	movl   $0x0,0x30(%rbx)
    4889:	mov    -0x68(%rbp),%rax
    488d:	mov    -0x58(%rbp),%rsi
    4891:	sub    -0x50(%rbp),%r12
    4895:	sub    -0x60(%rbp),%r13
    4899:	add    %r12,0x10(%rsi)
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decompressStream_data_pgot, 4923, memcpy

```asm
    491e:	mov    %rdx,-0x40(%rbp)
    4922:	call   4927 <pgot_ZSTD_decompressStream_data_pgot+0x1a7>
			4923: R_X86_64_PLT32	memcpy-0x4
    4927:	mov    -0x40(%rbp),%rdx
    492b:	mov    -0x48(%rbp),%rcx
    492f:	add    %rdx,%r13
    4932:	add    0x68(%rbx),%rdx
    4936:	mov    %rdx,0x68(%rbx)
    493a:	cmp    %r15,%rcx
    493d:	jb     4889 <pgot_ZSTD_decompressStream_data_pgot+0x109>
    4943:	movl   $0x2,0x30(%rbx)
    494a:	add    0x78(%rbx),%rdx
    494e:	cmp    0x60(%rbx),%rdx
    4952:	jbe    47e3 <pgot_ZSTD_decompressStream_data_pgot+0x63>
    4958:	movq   $0x0,0x70(%rbx)
    4960:	movq   $0x0,0x68(%rbx)
    4968:	jmp    47e3 <pgot_ZSTD_decompressStream_data_pgot+0x63>
    496d:	movl   $0x1,0x30(%rbx)
    4974:	xor    %edx,%edx
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decompressStream_data_pgot, 49f1, memcpy

```asm
    49ed:	add    %r15,%r12
    49f0:	call   49f5 <pgot_ZSTD_decompressStream_data_pgot+0x275>
			49f1: R_X86_64_PLT32	memcpy-0x4
    49f5:	mov    -0x48(%rbp),%rcx
    49f9:	add    %r15,0x48(%rbx)
    49fd:	mov    -0x40(%rbp),%r8
    4a01:	cmp    %r15,%rcx
    4a04:	ja     4889 <pgot_ZSTD_decompressStream_data_pgot+0x109>
    4a0a:	mov    (%rbx),%rdi
    4a0d:	mov    0x68(%rbx),%rsi
    4a11:	mov    0x60(%rbx),%rdx
    4a15:	mov    0x38(%rbx),%rcx
    4a19:	mov    0x6084(%rdi),%eax
    4a1f:	sub    %rsi,%rdx
    4a22:	add    0x58(%rbx),%rsi
    4a26:	mov    %eax,-0x40(%rbp)
    4a29:	call   4a2e <pgot_ZSTD_decompressStream_data_pgot+0x2ae>
			4a2a: R_X86_64_PLT32	pgot_ZSTD_decompressContinue_data_pgot-0x4
    4a2e:	mov    %rax,%r15
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_ZSTD_decompressStream_data_pgot, 4cfe, memcpy

```asm
    4cf9:	mov    %rax,-0x38(%rbp)
    4cfd:	call   4d02 <pgot_ZSTD_decompressStream_data_pgot+0x582>
			4cfe: R_X86_64_PLT32	memcpy-0x4
    4d02:	mov    -0x58(%rbp),%rsi
    4d06:	mov    -0x30(%rbp),%rdx
    4d0a:	add    %rdx,0x98(%rbx)
    4d11:	mov    -0x38(%rbp),%r9
    4d15:	mov    $0x3,%edx
    4d1a:	mov    0x8(%rsi),%rax
    4d1e:	mov    %rax,0x10(%rsi)
    4d22:	mov    $0x6,%eax
    4d27:	sub    0x98(%rbx),%rdx
    4d2e:	cmp    %rax,%r9
    4d31:	cmovae %r9,%rax
    4d35:	lea    (%rdx,%rax,1),%r9
    4d39:	jmp    4c7d <pgot_ZSTD_decompressStream_data_pgot+0x4fd>
    4d3e:	mov    $0xfffffffffffffff9,%r9
    4d45:	jmp    4c7d <pgot_ZSTD_decompressStream_data_pgot+0x4fd>
    4d4a:	mov    -0x58(%rbp),%rsi
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_FSE_readNCount_data_pgot, 279, memset

```asm
 274:	lea    (%rax,%r8,2),%rdi
 278:	call   27d <pgot_FSE_readNCount_data_pgot+0x21d>
			279: R_X86_64_PLT32	memset-0x4
 27d:	mov    -0x4c(%rbp),%r8d
 281:	mov    -0x58(%rbp),%ecx
 284:	mov    %r13d,%eax
 287:	sar    $0x3,%eax
 28a:	cltq   
 28c:	add    %r12,%rax
 28f:	cmp    -0x40(%rbp),%r12
 293:	jbe    2a2 <pgot_FSE_readNCount_data_pgot+0x242>
 295:	shr    $0x2,%ecx
 298:	cmp    -0x48(%rbp),%rax
 29c:	ja     195 <pgot_FSE_readNCount_data_pgot+0x135>
 2a2:	mov    (%rax),%esi
 2a4:	and    $0x7,%r13d
 2a8:	mov    %rax,%r12
 2ab:	mov    %r13d,%ecx
 2ae:	shr    %cl,%esi
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_HUF_selectDecoder_data_pgot, 4126, pgot_algoTime_data_pgot

```asm
    411f:	lea    (%rax,%rax,2),%rdx
    4123:	mov    0x0(%rip),%rax        # 412a <pgot_HUF_selectDecoder_data_pgot+0x2a>
			4126: R_X86_64_PC32	pgot_algoTime_data_pgot-0x4
    412a:	lea    (%rax,%rdx,8),%rdx
    412e:	mov    0xc(%rdx),%eax
    4131:	imul   %ecx,%eax
    4134:	add    0x8(%rdx),%eax
    4137:	mov    %eax,%esi
    4139:	imul   0x4(%rdx),%ecx
    413d:	add    (%rdx),%ecx
    413f:	shr    $0x3,%esi
    4142:	add    %esi,%eax
    4144:	cmp    %eax,%ecx
    4146:	seta   %al
    4149:	movzbl %al,%eax
    414c:	ret    
    414d:	int3   
    414e:	xchg   %ax,%ax

```

## 04_zstd_decompress/retpoline/data_pgot: pgot_HUF_decompress4X_DCtx_wksp_data_pgot, 41a1, pgot_algoTime_data_pgot

```asm
    419a:	lea    (%rax,%rax,2),%rdx
    419e:	mov    0x0(%rip),%rax        # 41a5 <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0x55>
			41a1: R_X86_64_PC32	pgot_algoTime_data_pgot-0x4
    41a5:	lea    (%rax,%rdx,8),%rdx
    41a9:	mov    0xc(%rdx),%eax
    41ac:	imul   %esi,%eax
    41af:	add    0x8(%rdx),%eax
    41b2:	mov    %eax,%r11d
    41b5:	imul   0x4(%rdx),%esi
    41b9:	add    (%rdx),%esi
    41bb:	shr    $0x3,%r11d
    41bf:	add    %r11d,%eax
    41c2:	cmp    %eax,%esi
    41c4:	jbe    41de <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0x8e>
    41c6:	push   0x10(%rbp)
    41c9:	mov    %r12,%rdx
    41cc:	mov    %r10,%rsi
    41cf:	call   41d4 <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0x84>
			41d0: R_X86_64_PLT32	pgot_HUF_decompress4X4_DCtx_wksp_data_pgot-0x4
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_HUF_decompress4X_DCtx_wksp_data_pgot, 41fb, memcpy

```asm
    41f7:	mov    %r10,%rdi
    41fa:	call   41ff <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0xaf>
			41fb: R_X86_64_PLT32	memcpy-0x4
    41ff:	mov    %r12,%rax
    4202:	mov    -0x8(%rbp),%r12
    4206:	leave  
    4207:	ret    
    4208:	int3   
    4209:	movzbl (%rcx),%esi
    420c:	mov    %r10,%rdi
    420f:	call   4214 <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0xc4>
			4210: R_X86_64_PLT32	memset-0x4
    4214:	mov    %r12,%rax
    4217:	mov    -0x8(%rbp),%r12
    421b:	leave  
    421c:	ret    
    421d:	int3   
    421e:	xchg   %ax,%ax

```

## 04_zstd_decompress/retpoline/data_pgot: pgot_HUF_decompress4X_DCtx_wksp_data_pgot, 4210, memset

```asm
    420c:	mov    %r10,%rdi
    420f:	call   4214 <pgot_HUF_decompress4X_DCtx_wksp_data_pgot+0xc4>
			4210: R_X86_64_PLT32	memset-0x4
    4214:	mov    %r12,%rax
    4217:	mov    -0x8(%rbp),%r12
    421b:	leave  
    421c:	ret    
    421d:	int3   
    421e:	xchg   %ax,%ax

```

## 04_zstd_decompress/retpoline/data_pgot: pgot_HUF_decompress4X_hufOnly_wksp_data_pgot, 4264, pgot_algoTime_data_pgot

```asm
    425d:	lea    (%rax,%rax,2),%rdx
    4261:	mov    0x0(%rip),%rax        # 4268 <pgot_HUF_decompress4X_hufOnly_wksp_data_pgot+0x48>
			4264: R_X86_64_PC32	pgot_algoTime_data_pgot-0x4
    4268:	lea    (%rax,%rdx,8),%rdx
    426c:	mov    0xc(%rdx),%eax
    426f:	imul   %r11d,%eax
    4273:	add    0x8(%rdx),%eax
    4276:	mov    %eax,%ebx
    4278:	imul   0x4(%rdx),%r11d
    427d:	add    (%rdx),%r11d
    4280:	shr    $0x3,%ebx
    4283:	add    %ebx,%eax
    4285:	cmp    %eax,%r11d
    4288:	ja     429d <pgot_HUF_decompress4X_hufOnly_wksp_data_pgot+0x7d>
    428a:	push   0x10(%rbp)
    428d:	mov    %r10,%rdx
    4290:	call   4295 <pgot_HUF_decompress4X_hufOnly_wksp_data_pgot+0x75>
			4291: R_X86_64_PLT32	pgot_HUF_decompress4X2_DCtx_wksp_data_pgot-0x4
    4295:	mov    -0x8(%rbp),%rbx
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_HUF_decompress1X_DCtx_wksp_data_pgot, 4338, pgot_algoTime_data_pgot

```asm
    4331:	lea    (%rax,%rax,2),%rdx
    4335:	mov    0x0(%rip),%rax        # 433c <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0x7c>
			4338: R_X86_64_PC32	pgot_algoTime_data_pgot-0x4
    433c:	lea    (%rax,%rdx,8),%rdx
    4340:	mov    0xc(%rdx),%eax
    4343:	imul   %edi,%eax
    4346:	add    0x8(%rdx),%eax
    4349:	mov    %eax,%r8d
    434c:	imul   0x4(%rdx),%edi
    4350:	add    (%rdx),%edi
    4352:	mov    %r15,%rdx
    4355:	shr    $0x3,%r8d
    4359:	add    %r8d,%eax
    435c:	mov    0x10(%rbp),%r8
    4360:	cmp    %eax,%edi
    4362:	mov    %rbx,%rdi
    4365:	jbe    43b6 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xf6>
    4367:	call   436c <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xac>
			4368: R_X86_64_PLT32	pgot_HUF_readDTableX4_wksp_data_pgot-0x4
```

## 04_zstd_decompress/retpoline/data_pgot: pgot_HUF_decompress1X_DCtx_wksp_data_pgot, 43f7, memcpy

```asm
    43f3:	mov    %r12,%r13
    43f6:	call   43fb <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0x13b>
			43f7: R_X86_64_PLT32	memcpy-0x4
    43fb:	jmp    43a3 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xe3>
    43fd:	movzbl (%rcx),%esi
    4400:	mov    %r14,%rdi
    4403:	mov    %r12,%r13
    4406:	call   440b <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0x14b>
			4407: R_X86_64_PLT32	memset-0x4
    440b:	jmp    43a3 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xe3>
    440d:	mov    $0xfffffffffffffff3,%r13
    4414:	jmp    43a3 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xe3>

Disassembly of section .text.unlikely:

```

## 04_zstd_decompress/retpoline/data_pgot: pgot_HUF_decompress1X_DCtx_wksp_data_pgot, 4407, memset

```asm
    4403:	mov    %r12,%r13
    4406:	call   440b <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0x14b>
			4407: R_X86_64_PLT32	memset-0x4
    440b:	jmp    43a3 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xe3>
    440d:	mov    $0xfffffffffffffff3,%r13
    4414:	jmp    43a3 <pgot_HUF_decompress1X_DCtx_wksp_data_pgot+0xe3>

Disassembly of section .text.unlikely:

```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_execSequenceLast7_func_pgot.isra.0, 5d3, pgot_memmove_table_func_pgot

```asm
     5cc:	mov    0x18(%rbp),%r14
     5d0:	mov    0x0(%rip),%rcx        # 5d7 <pgot_ZSTD_execSequenceLast7_func_pgot.isra.0+0xd7>
			5d3: R_X86_64_PC32	pgot_memmove_table_func_pgot-0x4
     5d7:	sub    %rsi,%r14
     5da:	mov    0x28(%rbp),%rsi
     5de:	sub    %r14,%rsi
     5e1:	lea    (%rsi,%r10,1),%rax
     5e5:	cmp    %rax,0x28(%rbp)
     5e9:	jae    687 <pgot_ZSTD_execSequenceLast7_func_pgot.isra.0+0x187>
     5ef:	mov    %r14,%rdx
     5f2:	mov    %r12,%rdi
     5f5:	jmp    609 <pgot_ZSTD_execSequenceLast7_func_pgot.isra.0+0x109>
     5f7:	call   603 <pgot_ZSTD_execSequenceLast7_func_pgot.isra.0+0x103>
     5fc:	pause  
     5fe:	lfence 
     601:	jmp    5fc <pgot_ZSTD_execSequenceLast7_func_pgot.isra.0+0xfc>
     603:	mov    %rcx,(%rsp)
     607:	ret    
     608:	int3   
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decompressBegin_func_pgot, b69, pgot_memcpy_table_func_pgot

```asm
     b65:	push   %rbp
     b66:	mov    0x0(%rip),%rax        # b6d <pgot_ZSTD_decompressBegin_func_pgot+0xd>
			b69: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     b6d:	mov    $0xc,%edx
     b72:	mov    $0x0,%rsi
			b75: R_X86_64_32S	.rodata+0x700
     b79:	mov    %rsp,%rbp
     b7c:	push   %rbx
     b7d:	mov    %rdi,%rbx
     b80:	lea    0x6030(%rdi),%rdi
     b87:	movq   $0x5,0x30(%rdi)
     b8f:	movq   $0x0,0x10(%rdi)
     b97:	movq   $0x0,0x18(%rdi)
     b9f:	movq   $0x0,0x20(%rdi)
     ba7:	movq   $0x0,0x28(%rdi)
     baf:	movl   $0xc00000c,-0x4c04(%rdi)
     bb9:	movl   $0x0,0x54(%rdi)
     bc0:	movq   $0x0,0x58(%rdi)
     bc8:	movl   $0x0,0xb8(%rdi)
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_createDCtx_advanced_func_pgot, d57, pgot_memcpy_table_func_pgot

```asm
     d4f:	mov    $0x18,%edx
     d54:	mov    0x0(%rip),%rax        # d5b <pgot_ZSTD_createDCtx_advanced_func_pgot+0x4b>
			d57: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     d5b:	lea    0x10(%rbp),%rsi
     d5f:	jmp    d73 <pgot_ZSTD_createDCtx_advanced_func_pgot+0x63>
     d61:	call   d6d <pgot_ZSTD_createDCtx_advanced_func_pgot+0x5d>
     d66:	pause  
     d68:	lfence 
     d6b:	jmp    d66 <pgot_ZSTD_createDCtx_advanced_func_pgot+0x56>
     d6d:	mov    %rax,(%rsp)
     d71:	ret    
     d72:	int3   
     d73:	call   d61 <pgot_ZSTD_createDCtx_advanced_func_pgot+0x51>
     d78:	mov    %r12,%rdi
     d7b:	call   d80 <pgot_ZSTD_createDCtx_advanced_func_pgot+0x70>
			d7c: R_X86_64_PLT32	pgot_ZSTD_decompressBegin_func_pgot-0x4
     d80:	mov    %r12,%rax
     d83:	mov    -0x8(%rbp),%r12
     d87:	leave  
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_copyDCtx_func_pgot, e39, pgot_memcpy_table_func_pgot

```asm
     e35:	push   %rbp
     e36:	mov    0x0(%rip),%rax        # e3d <pgot_ZSTD_copyDCtx_func_pgot+0xd>
			e39: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     e3d:	mov    $0x6126,%edx
     e42:	mov    %rsp,%rbp
     e45:	jmp    e59 <pgot_ZSTD_copyDCtx_func_pgot+0x29>
     e47:	call   e53 <pgot_ZSTD_copyDCtx_func_pgot+0x23>
     e4c:	pause  
     e4e:	lfence 
     e51:	jmp    e4c <pgot_ZSTD_copyDCtx_func_pgot+0x1c>
     e53:	mov    %rax,(%rsp)
     e57:	ret    
     e58:	int3   
     e59:	call   e47 <pgot_ZSTD_copyDCtx_func_pgot+0x17>
     e5e:	pop    %rbp
     e5f:	ret    
     e60:	int3   
     e61:	data16 cs nopw 0x0(%rax,%rax,1)
     e6c:	nopl   0x0(%rax)
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_getFrameParams_func_pgot, f09, pgot_memset_table_func_pgot

```asm
     f04:	jbe    f40 <pgot_ZSTD_getFrameParams_func_pgot+0x90>
     f06:	mov    0x0(%rip),%rax        # f0d <pgot_ZSTD_getFrameParams_func_pgot+0x5d>
			f09: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
     f0d:	mov    $0x18,%edx
     f12:	xor    %esi,%esi
     f14:	jmp    f28 <pgot_ZSTD_getFrameParams_func_pgot+0x78>
     f16:	call   f22 <pgot_ZSTD_getFrameParams_func_pgot+0x72>
     f1b:	pause  
     f1d:	lfence 
     f20:	jmp    f1b <pgot_ZSTD_getFrameParams_func_pgot+0x6b>
     f22:	mov    %rax,(%rsp)
     f26:	ret    
     f27:	int3   
     f28:	call   f16 <pgot_ZSTD_getFrameParams_func_pgot+0x66>
     f2d:	mov    0x4(%r12),%eax
     f32:	movl   $0x0,0x8(%r13)
     f3a:	mov    %rax,0x0(%r13)
     f3e:	xor    %eax,%eax
     f40:	add    $0x18,%rsp
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decodeLiteralsBlock_func_pgot, 1319, pgot_memcpy_table_func_pgot

```asm
    1313:	mov    %rbx,%rdx
    1316:	mov    0x0(%rip),%rax        # 131d <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x9d>
			1319: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    131d:	mov    %r14,%rdi
    1320:	jmp    1334 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xb4>
    1322:	call   132e <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xae>
    1327:	pause  
    1329:	lfence 
    132c:	jmp    1327 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xa7>
    132e:	mov    %rax,(%rsp)
    1332:	ret    
    1333:	int3   
    1334:	call   1322 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xa2>
    1339:	mov    %r14,0x60f0(%r12)
    1341:	lea    (%r14,%rbx,1),%rdi
    1345:	xor    %esi,%esi
    1347:	mov    %rbx,0x6110(%r12)
    134f:	mov    $0x8,%edx
    1354:	mov    0x0(%rip),%rax        # 135b <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xdb>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decodeLiteralsBlock_func_pgot, 1357, pgot_memset_table_func_pgot

```asm
    134f:	mov    $0x8,%edx
    1354:	mov    0x0(%rip),%rax        # 135b <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xdb>
			1357: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    135b:	jmp    136f <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xef>
    135d:	call   1369 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xe9>
    1362:	pause  
    1364:	lfence 
    1367:	jmp    1362 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xe2>
    1369:	mov    %rax,(%rsp)
    136d:	ret    
    136e:	int3   
    136f:	call   135d <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0xdd>
    1374:	jmp    13c9 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x149>
    1376:	mov    0x6088(%rdi),%esi
    137c:	mov    $0xffffffffffffffed,%r13
    1383:	test   %esi,%esi
    1385:	je     13c9 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x149>
    1387:	cmp    $0x4,%rdx
    138b:	jbe    13c2 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x142>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decodeLiteralsBlock_func_pgot, 1491, pgot_memset_table_func_pgot

```asm
    148c:	xor    %esi,%esi
    148e:	mov    0x0(%rip),%rax        # 1495 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x215>
			1491: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    1495:	jmp    14a9 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x229>
    1497:	call   14a3 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x223>
    149c:	pause  
    149e:	lfence 
    14a1:	jmp    149c <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x21c>
    14a3:	mov    %rax,(%rsp)
    14a7:	ret    
    14a8:	int3   
    14a9:	call   1497 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x217>
    14ae:	jmp    13c9 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x149>
    14b3:	mov    %ecx,%r14d
    14b6:	shr    $0x12,%r8d
    14ba:	xor    %eax,%eax
    14bc:	mov    $0x4,%esi
    14c1:	and    $0x3fff,%r14d
    14c8:	mov    %r8d,%ecx
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decodeLiteralsBlock_func_pgot, 1523, pgot_memset_table_func_pgot

```asm
    151c:	lea    0x8(%rbx),%rdx
    1520:	mov    0x0(%rip),%rax        # 1527 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x2a7>
			1523: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    1527:	mov    %r14,%rdi
    152a:	jmp    153e <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x2be>
    152c:	call   1538 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x2b8>
    1531:	pause  
    1533:	lfence 
    1536:	jmp    1531 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x2b1>
    1538:	mov    %rax,(%rsp)
    153c:	ret    
    153d:	int3   
    153e:	call   152c <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x2ac>
    1543:	mov    %r14,0x60f0(%r12)
    154b:	mov    %rbx,0x6110(%r12)
    1553:	jmp    13c9 <pgot_ZSTD_decodeLiteralsBlock_func_pgot+0x149>
    1558:	add    %r9,%rsi
    155b:	mov    %rbx,0x6110(%r12)
    1563:	mov    %rsi,0x60f0(%r12)
```

## 04_zstd_decompress/retpoline/func_pgot: ZSTD_decompressSequencesLong, 1971, pgot_memcpy_table_func_pgot

```asm
    196b:	mov    %r13,%rsi
    196e:	mov    0x0(%rip),%rax        # 1975 <ZSTD_decompressSequencesLong+0x125>
			1971: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    1975:	jmp    1989 <ZSTD_decompressSequencesLong+0x139>
    1977:	call   1983 <ZSTD_decompressSequencesLong+0x133>
    197c:	pause  
    197e:	lfence 
    1981:	jmp    197c <ZSTD_decompressSequencesLong+0x12c>
    1983:	mov    %rax,(%rsp)
    1987:	ret    
    1988:	int3   
    1989:	call   1977 <ZSTD_decompressSequencesLong+0x127>
    198e:	mov    -0x120(%rbp),%r11
    1995:	add    %r11,%rbx
    1998:	sub    -0x118(%rbp),%rbx
    199f:	mov    %rbx,%r12
    19a2:	mov    -0x38(%rbp),%rax
    19a6:	sub    %gs:0x28,%rax
    19af:	jne    26e9 <ZSTD_decompressSequencesLong+0xe99>
```

## 04_zstd_decompress/retpoline/func_pgot: ZSTD_decompressSequencesLong, 1e60, pgot_memmove_table_func_pgot

```asm
    1e57:	jb     1a36 <ZSTD_decompressSequencesLong+0x1e6>
    1e5d:	mov    0x0(%rip),%rax        # 1e64 <ZSTD_decompressSequencesLong+0x614>
			1e60: R_X86_64_PC32	pgot_memmove_table_func_pgot-0x4
    1e64:	lea    (%rsi,%rcx,1),%rdx
    1e68:	cmp    %rdx,-0x130(%rbp)
    1e6f:	jae    26b7 <ZSTD_decompressSequencesLong+0xe67>
    1e75:	mov    -0x130(%rbp),%rdx
    1e7c:	mov    %r9,-0x178(%rbp)
    1e83:	mov    %r14,%rdi
    1e86:	mov    %rcx,-0x160(%rbp)
    1e8d:	sub    %rsi,%rdx
    1e90:	mov    %r8,-0x168(%rbp)
    1e97:	mov    %rdx,-0x128(%rbp)
    1e9e:	jmp    1eb2 <ZSTD_decompressSequencesLong+0x662>
    1ea0:	call   1eac <ZSTD_decompressSequencesLong+0x65c>
    1ea5:	pause  
    1ea7:	lfence 
    1eaa:	jmp    1ea5 <ZSTD_decompressSequencesLong+0x655>
    1eac:	mov    %rax,(%rsp)
```

## 04_zstd_decompress/retpoline/func_pgot: ZSTD_decompressSequencesLong, 1f4e, pgot_memcpy_table_func_pgot

```asm
    1f48:	add    %rax,%rsi
    1f4b:	mov    0x0(%rip),%rax        # 1f52 <ZSTD_decompressSequencesLong+0x702>
			1f4e: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    1f52:	mov    %rsi,-0x160(%rbp)
    1f59:	jmp    1f6d <ZSTD_decompressSequencesLong+0x71d>
    1f5b:	call   1f67 <ZSTD_decompressSequencesLong+0x717>
    1f60:	pause  
    1f62:	lfence 
    1f65:	jmp    1f60 <ZSTD_decompressSequencesLong+0x710>
    1f67:	mov    %rax,(%rsp)
    1f6b:	ret    
    1f6c:	int3   
    1f6d:	call   1f5b <ZSTD_decompressSequencesLong+0x70b>
    1f72:	movslq -0x128(%rbp),%rax
    1f79:	mov    -0x160(%rbp),%rsi
    1f80:	mov    -0x168(%rbp),%rcx
    1f87:	mov    -0x178(%rbp),%r9
    1f8e:	sub    %rax,%rsi
    1f91:	lea    0x8(%r14),%rax
```

## 04_zstd_decompress/retpoline/func_pgot: ZSTD_decompressSequencesLong, 2185, pgot_memmove_table_func_pgot

```asm
    217c:	jb     1a36 <ZSTD_decompressSequencesLong+0x1e6>
    2182:	mov    0x0(%rip),%rax        # 2189 <ZSTD_decompressSequencesLong+0x939>
			2185: R_X86_64_PC32	pgot_memmove_table_func_pgot-0x4
    2189:	lea    (%rsi,%rcx,1),%rdx
    218d:	cmp    %rdx,-0x130(%rbp)
    2194:	jae    2590 <ZSTD_decompressSequencesLong+0xd40>
    219a:	mov    -0x130(%rbp),%rdx
    21a1:	mov    %r10d,-0x180(%rbp)
    21a8:	mov    %r14,%rdi
    21ab:	mov    %rcx,-0x178(%rbp)
    21b2:	sub    %rsi,%rdx
    21b5:	mov    %r9,-0x160(%rbp)
    21bc:	mov    %rdx,-0x158(%rbp)
    21c3:	mov    %r8,-0x188(%rbp)
    21ca:	jmp    21de <ZSTD_decompressSequencesLong+0x98e>
    21cc:	call   21d8 <ZSTD_decompressSequencesLong+0x988>
    21d1:	pause  
    21d3:	lfence 
    21d6:	jmp    21d1 <ZSTD_decompressSequencesLong+0x981>
```

## 04_zstd_decompress/retpoline/func_pgot: ZSTD_decompressSequencesLong, 2431, pgot_memcpy_table_func_pgot

```asm
    242b:	add    %rax,%rsi
    242e:	mov    0x0(%rip),%rax        # 2435 <ZSTD_decompressSequencesLong+0xbe5>
			2431: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2435:	mov    %rsi,-0x160(%rbp)
    243c:	jmp    2450 <ZSTD_decompressSequencesLong+0xc00>
    243e:	call   244a <ZSTD_decompressSequencesLong+0xbfa>
    2443:	pause  
    2445:	lfence 
    2448:	jmp    2443 <ZSTD_decompressSequencesLong+0xbf3>
    244a:	mov    %rax,(%rsp)
    244e:	ret    
    244f:	int3   
    2450:	call   243e <ZSTD_decompressSequencesLong+0xbee>
    2455:	movslq -0x158(%rbp),%rax
    245c:	mov    -0x160(%rbp),%rsi
    2463:	mov    -0x178(%rbp),%r9
    246a:	mov    -0x180(%rbp),%rcx
    2471:	mov    -0x188(%rbp),%r10d
    2478:	sub    %rax,%rsi
```

## 04_zstd_decompress/retpoline/func_pgot: ZSTD_decompressSequences, 2856, pgot_memcpy_table_func_pgot

```asm
    2851:	jb     288c <ZSTD_decompressSequences+0x14c>
    2853:	mov    0x0(%rip),%rax        # 285a <ZSTD_decompressSequences+0x11a>
			2856: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    285a:	mov    %rbx,%rdx
    285d:	mov    %r9,%rsi
    2860:	mov    %r15,%rdi
    2863:	jmp    2877 <ZSTD_decompressSequences+0x137>
    2865:	call   2871 <ZSTD_decompressSequences+0x131>
    286a:	pause  
    286c:	lfence 
    286f:	jmp    286a <ZSTD_decompressSequences+0x12a>
    2871:	mov    %rax,(%rsp)
    2875:	ret    
    2876:	int3   
    2877:	call   2865 <ZSTD_decompressSequences+0x125>
    287c:	mov    %r15,%rax
    287f:	add    %rbx,%rax
    2882:	sub    -0xc8(%rbp),%rax
    2889:	mov    %rax,%r14
```

## 04_zstd_decompress/retpoline/func_pgot: ZSTD_decompressSequences, 2df1, pgot_memmove_table_func_pgot

```asm
    2de7:	sub    -0xe8(%rbp),%rbx
    2dee:	mov    0x0(%rip),%rax        # 2df5 <ZSTD_decompressSequences+0x6b5>
			2df1: R_X86_64_PC32	pgot_memmove_table_func_pgot-0x4
    2df5:	lea    (%rdi,%rbx,1),%rsi
    2df9:	lea    (%rsi,%r12,1),%rdx
    2dfd:	cmp    %rdx,%rdi
    2e00:	jae    31ac <ZSTD_decompressSequences+0xa6c>
    2e06:	mov    %rbx,%rdx
    2e09:	mov    %rcx,-0x110(%rbp)
    2e10:	mov    %r15,%rdi
    2e13:	add    %rbx,%r12
    2e16:	neg    %rdx
    2e19:	mov    %r8,-0x118(%rbp)
    2e20:	mov    %rdx,-0x108(%rbp)
    2e27:	jmp    2e3b <ZSTD_decompressSequences+0x6fb>
    2e29:	call   2e35 <ZSTD_decompressSequences+0x6f5>
    2e2e:	pause  
    2e30:	lfence 
    2e33:	jmp    2e2e <ZSTD_decompressSequences+0x6ee>
```

## 04_zstd_decompress/retpoline/func_pgot: ZSTD_decompressSequences, 3128, pgot_memcpy_table_func_pgot

```asm
    3122:	add    %rax,%rsi
    3125:	mov    0x0(%rip),%rax        # 312c <ZSTD_decompressSequences+0x9ec>
			3128: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    312c:	mov    %rsi,-0x100(%rbp)
    3133:	jmp    3147 <ZSTD_decompressSequences+0xa07>
    3135:	call   3141 <ZSTD_decompressSequences+0xa01>
    313a:	pause  
    313c:	lfence 
    313f:	jmp    313a <ZSTD_decompressSequences+0x9fa>
    3141:	mov    %rax,(%rsp)
    3145:	ret    
    3146:	int3   
    3147:	call   3135 <ZSTD_decompressSequences+0x9f5>
    314c:	mov    -0x100(%rbp),%rsi
    3153:	mov    -0x108(%rbp),%r8
    315a:	mov    -0x110(%rbp),%rcx
    3161:	sub    %rbx,%rsi
    3164:	jmp    2fc4 <ZSTD_decompressSequences+0x884>
    3169:	mov    %rcx,%rdi
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_generateNxBytes_func_pgot, 3721, pgot_memset_table_func_pgot

```asm
    371b:	movzbl %dl,%esi
    371e:	mov    0x0(%rip),%rax        # 3725 <pgot_ZSTD_generateNxBytes_func_pgot+0x15>
			3721: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    3725:	mov    %rcx,%rdx
    3728:	mov    %rsp,%rbp
    372b:	push   %rbx
    372c:	mov    %rcx,%rbx
    372f:	jmp    3743 <pgot_ZSTD_generateNxBytes_func_pgot+0x33>
    3731:	call   373d <pgot_ZSTD_generateNxBytes_func_pgot+0x2d>
    3736:	pause  
    3738:	lfence 
    373b:	jmp    3736 <pgot_ZSTD_generateNxBytes_func_pgot+0x26>
    373d:	mov    %rax,(%rsp)
    3741:	ret    
    3742:	int3   
    3743:	call   3731 <pgot_ZSTD_generateNxBytes_func_pgot+0x21>
    3748:	mov    %rbx,%rax
    374b:	mov    -0x8(%rbp),%rbx
    374f:	leave  
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3c77, pgot_memcpy_table_func_pgot

```asm
    3c71:	mov    %rcx,%rsi
    3c74:	mov    0x0(%rip),%rax        # 3c7b <pgot_ZSTD_decompressContinue_func_pgot+0x1fb>
			3c77: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3c7b:	mov    $0x5,%edx
    3c80:	mov    %r12,%rdi
    3c83:	jmp    3c97 <pgot_ZSTD_decompressContinue_func_pgot+0x217>
    3c85:	call   3c91 <pgot_ZSTD_decompressContinue_func_pgot+0x211>
    3c8a:	pause  
    3c8c:	lfence 
    3c8f:	jmp    3c8a <pgot_ZSTD_decompressContinue_func_pgot+0x20a>
    3c91:	mov    %rax,(%rsp)
    3c95:	ret    
    3c96:	int3   
    3c97:	call   3c85 <pgot_ZSTD_decompressContinue_func_pgot+0x205>
    3c9c:	mov    0x60e0(%rbx),%rax
    3ca3:	mov    -0x30(%rbp),%rcx
    3ca7:	cmp    $0x5,%rax
    3cab:	ja     3f84 <pgot_ZSTD_decompressContinue_func_pgot+0x504>
    3cb1:	movq   $0x0,0x6060(%rbx)
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3cdc, pgot_memcpy_table_func_pgot

```asm
    3cd4:	jmp    3b7f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3cd9:	mov    0x0(%rip),%rax        # 3ce0 <pgot_ZSTD_decompressContinue_func_pgot+0x260>
			3cdc: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3ce0:	mov    %r8,%rdx
    3ce3:	mov    %rcx,%rsi
    3ce6:	xor    %r12d,%r12d
    3ce9:	lea    0x2612d(%rbx),%rdi
    3cf0:	jmp    3d04 <pgot_ZSTD_decompressContinue_func_pgot+0x284>
    3cf2:	call   3cfe <pgot_ZSTD_decompressContinue_func_pgot+0x27e>
    3cf7:	pause  
    3cf9:	lfence 
    3cfc:	jmp    3cf7 <pgot_ZSTD_decompressContinue_func_pgot+0x277>
    3cfe:	mov    %rax,(%rsp)
    3d02:	ret    
    3d03:	int3   
    3d04:	call   3cf2 <pgot_ZSTD_decompressContinue_func_pgot+0x272>
    3d09:	mov    0x2612c(%rbx),%eax
    3d0f:	movl   $0x7,0x6084(%rbx)
    3d19:	mov    %rax,0x6060(%rbx)
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3d3c, pgot_memcpy_table_func_pgot

```asm
    3d32:	lea    0x2612d(%rbx),%rdi
    3d39:	mov    0x0(%rip),%rax        # 3d40 <pgot_ZSTD_decompressContinue_func_pgot+0x2c0>
			3d3c: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3d40:	jmp    3d54 <pgot_ZSTD_decompressContinue_func_pgot+0x2d4>
    3d42:	call   3d4e <pgot_ZSTD_decompressContinue_func_pgot+0x2ce>
    3d47:	pause  
    3d49:	lfence 
    3d4c:	jmp    3d47 <pgot_ZSTD_decompressContinue_func_pgot+0x2c7>
    3d4e:	mov    %rax,(%rsp)
    3d52:	ret    
    3d53:	int3   
    3d54:	call   3d42 <pgot_ZSTD_decompressContinue_func_pgot+0x2c2>
    3d59:	mov    0x60e0(%rbx),%rdx
    3d60:	mov    %r12,%rsi
    3d63:	mov    %rbx,%rdi
    3d66:	call   1130 <ZSTD_decodeFrameHeader>
    3d6b:	mov    %rax,%r12
    3d6e:	cmp    $0xffffffffffffffea,%rax
    3d72:	ja     3b7f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3dc4, pgot_memcpy_table_func_pgot

```asm
    3dbc:	jmp    3b7f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3dc1:	mov    0x0(%rip),%rax        # 3dc8 <pgot_ZSTD_decompressContinue_func_pgot+0x348>
			3dc4: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3dc8:	lea    0x26128(%rbx),%rdi
    3dcf:	mov    %rcx,%rsi
    3dd2:	xor    %r12d,%r12d
    3dd5:	mov    $0x5,%edx
    3dda:	jmp    3dee <pgot_ZSTD_decompressContinue_func_pgot+0x36e>
    3ddc:	call   3de8 <pgot_ZSTD_decompressContinue_func_pgot+0x368>
    3de1:	pause  
    3de3:	lfence 
    3de6:	jmp    3de1 <pgot_ZSTD_decompressContinue_func_pgot+0x361>
    3de8:	mov    %rax,(%rsp)
    3dec:	ret    
    3ded:	int3   
    3dee:	call   3ddc <pgot_ZSTD_decompressContinue_func_pgot+0x35c>
    3df3:	movq   $0x3,0x6060(%rbx)
    3dfe:	movl   $0x6,0x6084(%rbx)
    3e08:	jmp    3b7f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3e6f, pgot_memset_table_func_pgot

```asm
    3e69:	movzbl (%rcx),%esi
    3e6c:	mov    0x0(%rip),%rax        # 3e73 <pgot_ZSTD_decompressContinue_func_pgot+0x3f3>
			3e6f: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    3e73:	mov    %r12,%rdx
    3e76:	mov    %r13,%rdi
    3e79:	jmp    3e8d <pgot_ZSTD_decompressContinue_func_pgot+0x40d>
    3e7b:	call   3e87 <pgot_ZSTD_decompressContinue_func_pgot+0x407>
    3e80:	pause  
    3e82:	lfence 
    3e85:	jmp    3e80 <pgot_ZSTD_decompressContinue_func_pgot+0x400>
    3e87:	mov    %rax,(%rsp)
    3e8b:	ret    
    3e8c:	int3   
    3e8d:	call   3e7b <pgot_ZSTD_decompressContinue_func_pgot+0x3fb>
    3e92:	cmp    $0xffffffffffffffea,%r12
    3e96:	ja     3b7f <pgot_ZSTD_decompressContinue_func_pgot+0xff>
    3e9c:	mov    0x6078(%rbx),%edx
    3ea2:	test   %edx,%edx
    3ea4:	jne    3f41 <pgot_ZSTD_decompressContinue_func_pgot+0x4c1>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decompressContinue_func_pgot, 3efb, pgot_memcpy_table_func_pgot

```asm
    3ef5:	mov    %r13,%rdi
    3ef8:	mov    0x0(%rip),%rax        # 3eff <pgot_ZSTD_decompressContinue_func_pgot+0x47f>
			3efb: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3eff:	jmp    3f13 <pgot_ZSTD_decompressContinue_func_pgot+0x493>
    3f01:	call   3f0d <pgot_ZSTD_decompressContinue_func_pgot+0x48d>
    3f06:	pause  
    3f08:	lfence 
    3f0b:	jmp    3f06 <pgot_ZSTD_decompressContinue_func_pgot+0x486>
    3f0d:	mov    %rax,(%rsp)
    3f11:	ret    
    3f12:	int3   
    3f13:	call   3f01 <pgot_ZSTD_decompressContinue_func_pgot+0x481>
    3f18:	mov    -0x30(%rbp),%r12
    3f1c:	jmp    3e92 <pgot_ZSTD_decompressContinue_func_pgot+0x412>
    3f21:	cmp    $0x1ffff,%r8
    3f28:	ja     3cc1 <pgot_ZSTD_decompressContinue_func_pgot+0x241>
    3f2e:	mov    %r13,%rsi
    3f31:	mov    %rbx,%rdi
    3f34:	call   35d0 <ZSTD_decompressBlock_internal.part.0>
```

## 04_zstd_decompress/retpoline/func_pgot: ZSTD_decompressMultiFrame, 41de, pgot_memcpy_table_func_pgot

```asm
    41d8:	mov    %rbx,%rdi
    41db:	mov    0x0(%rip),%rax        # 41e2 <ZSTD_decompressMultiFrame+0xf2>
			41de: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    41e2:	jmp    41f6 <ZSTD_decompressMultiFrame+0x106>
    41e4:	call   41f0 <ZSTD_decompressMultiFrame+0x100>
    41e9:	pause  
    41eb:	lfence 
    41ee:	jmp    41e9 <ZSTD_decompressMultiFrame+0xf9>
    41f0:	mov    %rax,(%rsp)
    41f4:	ret    
    41f5:	int3   
    41f6:	call   41e4 <ZSTD_decompressMultiFrame+0xf4>
    41fb:	mov    -0x58(%rbp),%r8
    41ff:	mov    %r8,%r15
    4202:	mov    0x6078(%r13),%ecx
    4209:	test   %ecx,%ecx
    420b:	jne    440b <ZSTD_decompressMultiFrame+0x31b>
    4211:	mov    -0x48(%rbp),%edx
    4214:	sub    %r8,%r14
```

## 04_zstd_decompress/retpoline/func_pgot: ZSTD_decompressMultiFrame, 4452, pgot_memset_table_func_pgot

```asm
    444d:	jb     4480 <ZSTD_decompressMultiFrame+0x390>
    444f:	mov    0x0(%rip),%rax        # 4456 <ZSTD_decompressMultiFrame+0x366>
			4452: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    4456:	mov    %r15,%rdx
    4459:	mov    %rbx,%rdi
    445c:	jmp    4470 <ZSTD_decompressMultiFrame+0x380>
    445e:	call   446a <ZSTD_decompressMultiFrame+0x37a>
    4463:	pause  
    4465:	lfence 
    4468:	jmp    4463 <ZSTD_decompressMultiFrame+0x373>
    446a:	mov    %rax,(%rsp)
    446e:	ret    
    446f:	int3   
    4470:	call   445e <ZSTD_decompressMultiFrame+0x36e>
    4475:	mov    $0x1,%r8d
    447b:	jmp    4202 <ZSTD_decompressMultiFrame+0x112>
    4480:	mov    $0xfffffffffffffff4,%r15
    4487:	jmp    41ab <ZSTD_decompressMultiFrame+0xbb>
    448c:	mov    $0xfffffffffffffffe,%r15
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_initDStream_func_pgot, 49a3, pgot_memset_table_func_pgot

```asm
    499e:	xor    %esi,%esi
    49a0:	mov    0x0(%rip),%rax        # 49a7 <pgot_ZSTD_initDStream_func_pgot+0x87>
			49a3: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    49a7:	jmp    49bb <pgot_ZSTD_initDStream_func_pgot+0x9b>
    49a9:	call   49b5 <pgot_ZSTD_initDStream_func_pgot+0x95>
    49ae:	pause  
    49b0:	lfence 
    49b3:	jmp    49ae <pgot_ZSTD_initDStream_func_pgot+0x8e>
    49b5:	mov    %rax,(%rsp)
    49b9:	ret    
    49ba:	int3   
    49bb:	call   49a9 <pgot_ZSTD_initDStream_func_pgot+0x89>
    49c0:	lea    0xa0(%r12),%rdi
    49c8:	mov    $0x18,%edx
    49cd:	lea    -0x38(%rbp),%rsi
    49d1:	mov    0x0(%rip),%rax        # 49d8 <pgot_ZSTD_initDStream_func_pgot+0xb8>
			49d4: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    49d8:	jmp    49ec <pgot_ZSTD_initDStream_func_pgot+0xcc>
    49da:	call   49e6 <pgot_ZSTD_initDStream_func_pgot+0xc6>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_initDStream_func_pgot, 49d4, pgot_memcpy_table_func_pgot

```asm
    49cd:	lea    -0x38(%rbp),%rsi
    49d1:	mov    0x0(%rip),%rax        # 49d8 <pgot_ZSTD_initDStream_func_pgot+0xb8>
			49d4: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    49d8:	jmp    49ec <pgot_ZSTD_initDStream_func_pgot+0xcc>
    49da:	call   49e6 <pgot_ZSTD_initDStream_func_pgot+0xc6>
    49df:	pause  
    49e1:	lfence 
    49e4:	jmp    49df <pgot_ZSTD_initDStream_func_pgot+0xbf>
    49e6:	mov    %rax,(%rsp)
    49ea:	ret    
    49eb:	int3   
    49ec:	call   49da <pgot_ZSTD_initDStream_func_pgot+0xba>
    49f1:	push   -0x28(%rbp)
    49f4:	push   -0x30(%rbp)
    49f7:	push   -0x38(%rbp)
    49fa:	call   49ff <pgot_ZSTD_initDStream_func_pgot+0xdf>
			49fb: R_X86_64_PLT32	pgot_ZSTD_createDCtx_advanced_func_pgot-0x4
    49ff:	mov    %rax,(%r12)
    4a03:	add    $0x18,%rsp
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decompressStream_func_pgot, 4c9e, pgot_memcpy_table_func_pgot

```asm
    4c94:	sub    0x98(%rbx),%rcx
    4c9b:	mov    0x0(%rip),%rax        # 4ca2 <pgot_ZSTD_decompressStream_func_pgot+0xc2>
			4c9e: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4ca2:	sub    %r12,%rdx
    4ca5:	add    %r14,%rdi
    4ca8:	cmp    %rcx,%rdx
    4cab:	jb     51a7 <pgot_ZSTD_decompressStream_func_pgot+0x5c7>
    4cb1:	mov    %rcx,-0x40(%rbp)
    4cb5:	mov    %rcx,%rdx
    4cb8:	mov    %r12,%rsi
    4cbb:	jmp    4ccf <pgot_ZSTD_decompressStream_func_pgot+0xef>
    4cbd:	call   4cc9 <pgot_ZSTD_decompressStream_func_pgot+0xe9>
    4cc2:	pause  
    4cc4:	lfence 
    4cc7:	jmp    4cc2 <pgot_ZSTD_decompressStream_func_pgot+0xe2>
    4cc9:	mov    %rax,(%rsp)
    4ccd:	ret    
    4cce:	int3   
    4ccf:	call   4cbd <pgot_ZSTD_decompressStream_func_pgot+0xdd>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decompressStream_func_pgot, 4d8b, pgot_memcpy_table_func_pgot

```asm
    4d85:	mov    %r13,%rdi
    4d88:	mov    0x0(%rip),%rax        # 4d8f <pgot_ZSTD_decompressStream_func_pgot+0x1af>
			4d8b: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4d8f:	sub    %r13,%rcx
    4d92:	cmp    %rcx,%r15
    4d95:	mov    %rcx,%rdx
    4d98:	mov    %rcx,-0x48(%rbp)
    4d9c:	cmovbe %r15,%rdx
    4da0:	add    0x58(%rbx),%rsi
    4da4:	mov    %rdx,-0x40(%rbp)
    4da8:	jmp    4dbc <pgot_ZSTD_decompressStream_func_pgot+0x1dc>
    4daa:	call   4db6 <pgot_ZSTD_decompressStream_func_pgot+0x1d6>
    4daf:	pause  
    4db1:	lfence 
    4db4:	jmp    4daf <pgot_ZSTD_decompressStream_func_pgot+0x1cf>
    4db6:	mov    %rax,(%rsp)
    4dba:	ret    
    4dbb:	int3   
    4dbc:	call   4daa <pgot_ZSTD_decompressStream_func_pgot+0x1ca>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_ZSTD_decompressStream_func_pgot, 4e79, pgot_memcpy_table_func_pgot

```asm
    4e73:	mov    %r12,%rsi
    4e76:	mov    0x0(%rip),%rax        # 4e7d <pgot_ZSTD_decompressStream_func_pgot+0x29d>
			4e79: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4e7d:	sub    %r12,%r15
    4e80:	cmp    %rcx,%r15
    4e83:	cmova  %rcx,%r15
    4e87:	add    0x38(%rbx),%rdi
    4e8b:	mov    %r15,%rdx
    4e8e:	add    %r15,%r12
    4e91:	jmp    4ea5 <pgot_ZSTD_decompressStream_func_pgot+0x2c5>
    4e93:	call   4e9f <pgot_ZSTD_decompressStream_func_pgot+0x2bf>
    4e98:	pause  
    4e9a:	lfence 
    4e9d:	jmp    4e98 <pgot_ZSTD_decompressStream_func_pgot+0x2b8>
    4e9f:	mov    %rax,(%rsp)
    4ea3:	ret    
    4ea4:	int3   
    4ea5:	call   4e93 <pgot_ZSTD_decompressStream_func_pgot+0x2b3>
    4eaa:	mov    -0x48(%rbp),%rcx
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_FSE_readNCount_func_pgot, 279, memset

```asm
 274:	lea    (%rax,%r8,2),%rdi
 278:	call   27d <pgot_FSE_readNCount_func_pgot+0x21d>
			279: R_X86_64_PLT32	memset-0x4
 27d:	mov    -0x4c(%rbp),%r8d
 281:	mov    -0x58(%rbp),%ecx
 284:	mov    %r13d,%eax
 287:	sar    $0x3,%eax
 28a:	cltq   
 28c:	add    %r12,%rax
 28f:	cmp    -0x40(%rbp),%r12
 293:	jbe    2a2 <pgot_FSE_readNCount_func_pgot+0x242>
 295:	shr    $0x2,%ecx
 298:	cmp    -0x48(%rbp),%rax
 29c:	ja     195 <pgot_FSE_readNCount_func_pgot+0x135>
 2a2:	mov    (%rax),%esi
 2a4:	and    $0x7,%r13d
 2a8:	mov    %rax,%r12
 2ab:	mov    %r13d,%ecx
 2ae:	shr    %cl,%esi
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_readStats_wksp_func_pgot, 3bd, pgot_memset_table_func_pgot

```asm
 3b6:	mov    %r8,-0x38(%rbp)
 3ba:	mov    0x0(%rip),%rax        # 3c1 <pgot_HUF_readStats_wksp_func_pgot+0xa1>
			3bd: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
 3c1:	xor    %esi,%esi
 3c3:	mov    %r15,%rdi
 3c6:	mov    $0x34,%edx
 3cb:	jmp    3df <pgot_HUF_readStats_wksp_func_pgot+0xbf>
 3cd:	call   3d9 <pgot_HUF_readStats_wksp_func_pgot+0xb9>
 3d2:	pause  
 3d4:	lfence 
 3d7:	jmp    3d2 <pgot_HUF_readStats_wksp_func_pgot+0xb2>
 3d9:	mov    %rax,(%rsp)
 3dd:	ret    
 3de:	int3   
 3df:	call   3cd <pgot_HUF_readStats_wksp_func_pgot+0xad>
 3e4:	mov    -0x38(%rbp),%r8
 3e8:	xor    %r12d,%r12d
 3eb:	xor    %r9d,%r9d
 3ee:	xor    %eax,%eax
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_readStats_wksp_func_pgot, 47d, pgot_memset_table_func_pgot

```asm
 476:	mov    %r8,-0x38(%rbp)
 47a:	mov    0x0(%rip),%rax        # 481 <pgot_HUF_readStats_wksp_func_pgot+0x161>
			47d: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
 481:	xor    %esi,%esi
 483:	mov    %r15,%rdi
 486:	mov    $0x34,%edx
 48b:	jmp    49f <pgot_HUF_readStats_wksp_func_pgot+0x17f>
 48d:	call   499 <pgot_HUF_readStats_wksp_func_pgot+0x179>
 492:	pause  
 494:	lfence 
 497:	jmp    492 <pgot_HUF_readStats_wksp_func_pgot+0x172>
 499:	mov    %rax,(%rsp)
 49d:	ret    
 49e:	int3   
 49f:	call   48d <pgot_HUF_readStats_wksp_func_pgot+0x16d>
 4a4:	mov    -0x38(%rbp),%r8
 4a8:	test   %r8,%r8
 4ab:	jne    3e8 <pgot_HUF_readStats_wksp_func_pgot+0xc8>
 4b1:	jmp    42f <pgot_HUF_readStats_wksp_func_pgot+0x10f>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_FSE_buildDTable_wksp_func_pgot, 267, pgot_memcpy_table_func_pgot

```asm
 260:	mov    %r9,-0x50(%rbp)
 264:	mov    0x0(%rip),%rax        # 26b <pgot_FSE_buildDTable_wksp_func_pgot+0x12b>
			267: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
 26b:	jmp    27f <pgot_FSE_buildDTable_wksp_func_pgot+0x13f>
 26d:	call   279 <pgot_FSE_buildDTable_wksp_func_pgot+0x139>
 272:	pause  
 274:	lfence 
 277:	jmp    272 <pgot_FSE_buildDTable_wksp_func_pgot+0x132>
 279:	mov    %rax,(%rsp)
 27d:	ret    
 27e:	int3   
 27f:	call   26d <pgot_FSE_buildDTable_wksp_func_pgot+0x12d>
 284:	mov    -0x48(%rbp),%eax
 287:	mov    -0x50(%rbp),%r9
 28b:	xor    %r10d,%r10d
 28e:	mov    -0x58(%rbp),%rcx
 292:	mov    %eax,%edx
 294:	shr    %eax
 296:	shr    $0x3,%edx
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_fillDTableX4Level2, 4b, pgot_memcpy_table_func_pgot

```asm
      46:	xor    %eax,%eax
      48:	mov    0x0(%rip),%rax        # 4f <HUF_fillDTableX4Level2+0x4f>
			4b: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
      4f:	jmp    63 <HUF_fillDTableX4Level2+0x63>
      51:	call   5d <HUF_fillDTableX4Level2+0x5d>
      56:	pause  
      58:	lfence 
      5b:	jmp    56 <HUF_fillDTableX4Level2+0x56>
      5d:	mov    %rax,(%rsp)
      61:	ret    
      62:	int3   
      63:	call   51 <HUF_fillDTableX4Level2+0x51>
      68:	cmp    $0x1,%r12d
      6c:	mov    -0x70(%rbp),%r9d
      70:	jle    aa <HUF_fillDTableX4Level2+0xaa>
      72:	movslq %r12d,%r8
      75:	cmp    $0xc,%r8
      79:	ja     20b <HUF_fillDTableX4Level2+0x20b>
      7f:	mov    -0x64(%rbp,%r8,4),%ecx
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decodeLastSymbolX4.isra.0, 39a, pgot_memcpy_table_func_pgot

```asm
     393:	lea    (%rdx,%rax,4),%r12
     397:	mov    0x0(%rip),%rax        # 39e <HUF_decodeLastSymbolX4.isra.0+0x2e>
			39a: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     39e:	mov    $0x1,%edx
     3a3:	mov    %r12,%rsi
     3a6:	jmp    3ba <HUF_decodeLastSymbolX4.isra.0+0x4a>
     3a8:	call   3b4 <HUF_decodeLastSymbolX4.isra.0+0x44>
     3ad:	pause  
     3af:	lfence 
     3b2:	jmp    3ad <HUF_decodeLastSymbolX4.isra.0+0x3d>
     3b4:	mov    %rax,(%rsp)
     3b8:	ret    
     3b9:	int3   
     3ba:	call   3a8 <HUF_decodeLastSymbolX4.isra.0+0x38>
     3bf:	cmpb   $0x1,0x3(%r12)
     3c5:	je     3ea <HUF_decodeLastSymbolX4.isra.0+0x7a>
     3c7:	mov    0x8(%rbx),%edx
     3ca:	cmp    $0x3f,%edx
     3cd:	ja     3e4 <HUF_decodeLastSymbolX4.isra.0+0x74>
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress1X2_usingDTable_internal, 443, pgot_memcpy_table_func_pgot

```asm
     43e:	xor    %eax,%eax
     440:	mov    0x0(%rip),%rax        # 447 <HUF_decompress1X2_usingDTable_internal+0x47>
			443: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     447:	jmp    45b <HUF_decompress1X2_usingDTable_internal+0x5b>
     449:	call   455 <HUF_decompress1X2_usingDTable_internal+0x55>
     44e:	pause  
     450:	lfence 
     453:	jmp    44e <HUF_decompress1X2_usingDTable_internal+0x4e>
     455:	mov    %rax,(%rsp)
     459:	ret    
     45a:	int3   
     45b:	call   449 <HUF_decompress1X2_usingDTable_internal+0x49>
     460:	movzbl -0x4e(%rbp),%eax
     464:	mov    %r14,%rsi
     467:	lea    -0x50(%rbp),%rdi
     46b:	mov    %r13,%rdx
     46e:	mov    %al,-0x51(%rbp)
     471:	call   230 <BIT_initDStream>
     476:	mov    %rax,%rdi
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 7ba, pgot_memcpy_table_func_pgot

```asm
     7b3:	mov    %rbx,-0x60(%rbp)
     7b7:	mov    0x0(%rip),%rax        # 7be <HUF_decompress1X4_usingDTable_internal+0x6e>
			7ba: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     7be:	lea    0x4(%r14),%r12
     7c2:	jmp    7d6 <HUF_decompress1X4_usingDTable_internal+0x86>
     7c4:	call   7d0 <HUF_decompress1X4_usingDTable_internal+0x80>
     7c9:	pause  
     7cb:	lfence 
     7ce:	jmp    7c9 <HUF_decompress1X4_usingDTable_internal+0x79>
     7d0:	mov    %rax,(%rsp)
     7d4:	ret    
     7d5:	int3   
     7d6:	call   7c4 <HUF_decompress1X4_usingDTable_internal+0x74>
     7db:	movzbl -0x52(%rbp),%eax
     7df:	mov    -0x48(%rbp),%ecx
     7e2:	mov    %eax,-0x64(%rbp)
     7e5:	cmp    $0x40,%ecx
     7e8:	ja     ad2 <HUF_decompress1X4_usingDTable_internal+0x382>
     7ee:	neg    %eax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 858, pgot_memcpy_table_func_pgot

```asm
     851:	lea    (%r12,%rax,4),%r14
     855:	mov    0x0(%rip),%rax        # 85c <HUF_decompress1X4_usingDTable_internal+0x10c>
			858: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     85c:	mov    %r14,%rsi
     85f:	jmp    873 <HUF_decompress1X4_usingDTable_internal+0x123>
     861:	call   86d <HUF_decompress1X4_usingDTable_internal+0x11d>
     866:	pause  
     868:	lfence 
     86b:	jmp    866 <HUF_decompress1X4_usingDTable_internal+0x116>
     86d:	mov    %rax,(%rsp)
     871:	ret    
     872:	int3   
     873:	call   861 <HUF_decompress1X4_usingDTable_internal+0x111>
     878:	mov    -0x50(%rbp),%rax
     87c:	movzbl 0x2(%r14),%ecx
     881:	mov    $0x2,%edx
     886:	add    -0x48(%rbp),%ecx
     889:	movzbl 0x3(%r14),%edi
     88e:	mov    %ecx,-0x48(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 8a6, pgot_memcpy_table_func_pgot

```asm
     8a0:	mov    %r13,%rdi
     8a3:	mov    0x0(%rip),%rax        # 8aa <HUF_decompress1X4_usingDTable_internal+0x15a>
			8a6: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     8aa:	mov    %r14,%rsi
     8ad:	jmp    8c1 <HUF_decompress1X4_usingDTable_internal+0x171>
     8af:	call   8bb <HUF_decompress1X4_usingDTable_internal+0x16b>
     8b4:	pause  
     8b6:	lfence 
     8b9:	jmp    8b4 <HUF_decompress1X4_usingDTable_internal+0x164>
     8bb:	mov    %rax,(%rsp)
     8bf:	ret    
     8c0:	int3   
     8c1:	call   8af <HUF_decompress1X4_usingDTable_internal+0x15f>
     8c6:	movzbl 0x3(%r14),%eax
     8cb:	movzbl 0x2(%r14),%ecx
     8d0:	mov    $0x2,%edx
     8d5:	add    -0x48(%rbp),%ecx
     8d8:	add    %rax,%r13
     8db:	mov    -0x50(%rbp),%rax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 8f4, pgot_memcpy_table_func_pgot

```asm
     8ed:	lea    (%r12,%rax,4),%r14
     8f1:	mov    0x0(%rip),%rax        # 8f8 <HUF_decompress1X4_usingDTable_internal+0x1a8>
			8f4: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     8f8:	mov    %r14,%rsi
     8fb:	jmp    90f <HUF_decompress1X4_usingDTable_internal+0x1bf>
     8fd:	call   909 <HUF_decompress1X4_usingDTable_internal+0x1b9>
     902:	pause  
     904:	lfence 
     907:	jmp    902 <HUF_decompress1X4_usingDTable_internal+0x1b2>
     909:	mov    %rax,(%rsp)
     90d:	ret    
     90e:	int3   
     90f:	call   8fd <HUF_decompress1X4_usingDTable_internal+0x1ad>
     914:	mov    -0x50(%rbp),%rax
     918:	movzbl 0x2(%r14),%ecx
     91d:	mov    $0x2,%edx
     922:	add    -0x48(%rbp),%ecx
     925:	movzbl 0x3(%r14),%r9d
     92a:	mov    %ecx,-0x48(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, 942, pgot_memcpy_table_func_pgot

```asm
     93c:	mov    %r13,%rdi
     93f:	mov    0x0(%rip),%rax        # 946 <HUF_decompress1X4_usingDTable_internal+0x1f6>
			942: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     946:	mov    %r14,%rsi
     949:	jmp    95d <HUF_decompress1X4_usingDTable_internal+0x20d>
     94b:	call   957 <HUF_decompress1X4_usingDTable_internal+0x207>
     950:	pause  
     952:	lfence 
     955:	jmp    950 <HUF_decompress1X4_usingDTable_internal+0x200>
     957:	mov    %rax,(%rsp)
     95b:	ret    
     95c:	int3   
     95d:	call   94b <HUF_decompress1X4_usingDTable_internal+0x1fb>
     962:	movzbl 0x3(%r14),%eax
     967:	movzbl 0x2(%r14),%ecx
     96c:	add    -0x48(%rbp),%ecx
     96f:	mov    %ecx,-0x48(%rbp)
     972:	add    %rax,%r13
     975:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, a34, pgot_memcpy_table_func_pgot

```asm
     a2d:	lea    (%r12,%rax,4),%r14
     a31:	mov    0x0(%rip),%rax        # a38 <HUF_decompress1X4_usingDTable_internal+0x2e8>
			a34: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     a38:	mov    %r14,%rsi
     a3b:	jmp    a4f <HUF_decompress1X4_usingDTable_internal+0x2ff>
     a3d:	call   a49 <HUF_decompress1X4_usingDTable_internal+0x2f9>
     a42:	pause  
     a44:	lfence 
     a47:	jmp    a42 <HUF_decompress1X4_usingDTable_internal+0x2f2>
     a49:	mov    %rax,(%rsp)
     a4d:	ret    
     a4e:	int3   
     a4f:	call   a3d <HUF_decompress1X4_usingDTable_internal+0x2ed>
     a54:	movzbl 0x3(%r14),%edx
     a59:	movzbl 0x2(%r14),%eax
     a5e:	add    -0x48(%rbp),%eax
     a61:	mov    %eax,-0x48(%rbp)
     a64:	add    %rdx,%r13
     a67:	cmp    $0x40,%eax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress1X4_usingDTable_internal, b09, pgot_memcpy_table_func_pgot

```asm
     b02:	lea    (%r12,%rax,4),%r14
     b06:	mov    0x0(%rip),%rax        # b0d <HUF_decompress1X4_usingDTable_internal+0x3bd>
			b09: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     b0d:	mov    %r14,%rsi
     b10:	jmp    b24 <HUF_decompress1X4_usingDTable_internal+0x3d4>
     b12:	call   b1e <HUF_decompress1X4_usingDTable_internal+0x3ce>
     b17:	pause  
     b19:	lfence 
     b1c:	jmp    b17 <HUF_decompress1X4_usingDTable_internal+0x3c7>
     b1e:	mov    %rax,(%rsp)
     b22:	ret    
     b23:	int3   
     b24:	call   b12 <HUF_decompress1X4_usingDTable_internal+0x3c2>
     b29:	movzbl 0x3(%r14),%eax
     b2e:	movzbl 0x2(%r14),%ecx
     b33:	add    -0x48(%rbp),%ecx
     b36:	add    %rax,%r13
     b39:	mov    %ecx,-0x48(%rbp)
     b3c:	cmp    %rbx,%r13
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X2_usingDTable_internal, c28, pgot_memcpy_table_func_pgot

```asm
     c22:	sub    %rax,%r12
     c25:	mov    0x0(%rip),%rax        # c2c <HUF_decompress4X2_usingDTable_internal+0x8c>
			c28: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
     c2c:	jmp    c40 <HUF_decompress4X2_usingDTable_internal+0xa0>
     c2e:	call   c3a <HUF_decompress4X2_usingDTable_internal+0x9a>
     c33:	pause  
     c35:	lfence 
     c38:	jmp    c33 <HUF_decompress4X2_usingDTable_internal+0x93>
     c3a:	mov    %rax,(%rsp)
     c3e:	ret    
     c3f:	int3   
     c40:	call   c2e <HUF_decompress4X2_usingDTable_internal+0x8e>
     c45:	mov    -0xc0(%rbp),%rcx
     c4c:	movzbl -0x4e(%rbp),%eax
     c50:	mov    -0xc8(%rbp),%r9
     c57:	cmp    %r12,%rcx
     c5a:	mov    %al,-0xe0(%rbp)
     c60:	jae    c92 <HUF_decompress4X2_usingDTable_internal+0xf2>
     c62:	mov    $0xfffffffffffffff2,%r15
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 22b7, pgot_memcpy_table_func_pgot

```asm
    22b1:	sub    %rax,%r13
    22b4:	mov    0x0(%rip),%rax        # 22bb <HUF_decompress4X4_usingDTable_internal+0x8b>
			22b7: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    22bb:	jmp    22cf <HUF_decompress4X4_usingDTable_internal+0x9f>
    22bd:	call   22c9 <HUF_decompress4X4_usingDTable_internal+0x99>
    22c2:	pause  
    22c4:	lfence 
    22c7:	jmp    22c2 <HUF_decompress4X4_usingDTable_internal+0x92>
    22c9:	mov    %rax,(%rsp)
    22cd:	ret    
    22ce:	int3   
    22cf:	call   22bd <HUF_decompress4X4_usingDTable_internal+0x8d>
    22d4:	mov    -0xb8(%rbp),%rcx
    22db:	movzbl -0x4e(%rbp),%eax
    22df:	mov    -0xc0(%rbp),%r9
    22e6:	cmp    %r13,%rcx
    22e9:	mov    %al,-0xdc(%rbp)
    22ef:	jae    2321 <HUF_decompress4X4_usingDTable_internal+0xf1>
    22f1:	mov    $0xfffffffffffffff2,%r14
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2805, pgot_memcpy_table_func_pgot

```asm
    27fe:	lea    (%r12,%rax,4),%rcx
    2802:	mov    0x0(%rip),%rax        # 2809 <HUF_decompress4X4_usingDTable_internal+0x5d9>
			2805: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2809:	mov    %rcx,%rsi
    280c:	mov    %rcx,-0xc0(%rbp)
    2813:	jmp    2827 <HUF_decompress4X4_usingDTable_internal+0x5f7>
    2815:	call   2821 <HUF_decompress4X4_usingDTable_internal+0x5f1>
    281a:	pause  
    281c:	lfence 
    281f:	jmp    281a <HUF_decompress4X4_usingDTable_internal+0x5ea>
    2821:	mov    %rax,(%rsp)
    2825:	ret    
    2826:	int3   
    2827:	call   2815 <HUF_decompress4X4_usingDTable_internal+0x5e5>
    282c:	mov    -0xc0(%rbp),%rcx
    2833:	mov    %r15,%rdi
    2836:	mov    $0x2,%edx
    283b:	movzbl 0x2(%rcx),%eax
    283f:	add    %eax,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 286d, pgot_memcpy_table_func_pgot

```asm
    2866:	lea    (%r12,%rax,4),%rcx
    286a:	mov    0x0(%rip),%rax        # 2871 <HUF_decompress4X4_usingDTable_internal+0x641>
			286d: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2871:	mov    %rcx,%rsi
    2874:	mov    %rcx,-0xc0(%rbp)
    287b:	jmp    288f <HUF_decompress4X4_usingDTable_internal+0x65f>
    287d:	call   2889 <HUF_decompress4X4_usingDTable_internal+0x659>
    2882:	pause  
    2884:	lfence 
    2887:	jmp    2882 <HUF_decompress4X4_usingDTable_internal+0x652>
    2889:	mov    %rax,(%rsp)
    288d:	ret    
    288e:	int3   
    288f:	call   287d <HUF_decompress4X4_usingDTable_internal+0x64d>
    2894:	mov    -0xc0(%rbp),%rcx
    289b:	mov    %r14,%rdi
    289e:	mov    $0x2,%edx
    28a3:	movzbl 0x2(%rcx),%eax
    28a7:	add    %eax,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 28cf, pgot_memcpy_table_func_pgot

```asm
    28c8:	lea    (%r12,%rax,4),%rcx
    28cc:	mov    0x0(%rip),%rax        # 28d3 <HUF_decompress4X4_usingDTable_internal+0x6a3>
			28cf: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    28d3:	mov    %rcx,%rsi
    28d6:	mov    %rcx,-0xc0(%rbp)
    28dd:	jmp    28f1 <HUF_decompress4X4_usingDTable_internal+0x6c1>
    28df:	call   28eb <HUF_decompress4X4_usingDTable_internal+0x6bb>
    28e4:	pause  
    28e6:	lfence 
    28e9:	jmp    28e4 <HUF_decompress4X4_usingDTable_internal+0x6b4>
    28eb:	mov    %rax,(%rsp)
    28ef:	ret    
    28f0:	int3   
    28f1:	call   28df <HUF_decompress4X4_usingDTable_internal+0x6af>
    28f6:	mov    -0xc0(%rbp),%rcx
    28fd:	mov    %rbx,%rdi
    2900:	mov    $0x2,%edx
    2905:	movzbl 0x2(%rcx),%eax
    2909:	add    %eax,-0x68(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 292e, pgot_memcpy_table_func_pgot

```asm
    2927:	lea    (%r12,%rax,4),%rcx
    292b:	mov    0x0(%rip),%rax        # 2932 <HUF_decompress4X4_usingDTable_internal+0x702>
			292e: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2932:	mov    %rcx,%rsi
    2935:	mov    %rcx,-0xc0(%rbp)
    293c:	jmp    2950 <HUF_decompress4X4_usingDTable_internal+0x720>
    293e:	call   294a <HUF_decompress4X4_usingDTable_internal+0x71a>
    2943:	pause  
    2945:	lfence 
    2948:	jmp    2943 <HUF_decompress4X4_usingDTable_internal+0x713>
    294a:	mov    %rax,(%rsp)
    294e:	ret    
    294f:	int3   
    2950:	call   293e <HUF_decompress4X4_usingDTable_internal+0x70e>
    2955:	mov    -0xc0(%rbp),%rcx
    295c:	mov    %r13,%rdi
    295f:	mov    $0x2,%edx
    2964:	movzbl 0x2(%rcx),%eax
    2968:	add    %eax,-0x48(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2993, pgot_memcpy_table_func_pgot

```asm
    298c:	lea    (%r12,%rax,4),%rcx
    2990:	mov    0x0(%rip),%rax        # 2997 <HUF_decompress4X4_usingDTable_internal+0x767>
			2993: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2997:	mov    %rcx,%rsi
    299a:	mov    %rcx,-0xc0(%rbp)
    29a1:	jmp    29b5 <HUF_decompress4X4_usingDTable_internal+0x785>
    29a3:	call   29af <HUF_decompress4X4_usingDTable_internal+0x77f>
    29a8:	pause  
    29aa:	lfence 
    29ad:	jmp    29a8 <HUF_decompress4X4_usingDTable_internal+0x778>
    29af:	mov    %rax,(%rsp)
    29b3:	ret    
    29b4:	int3   
    29b5:	call   29a3 <HUF_decompress4X4_usingDTable_internal+0x773>
    29ba:	mov    -0xc0(%rbp),%rcx
    29c1:	mov    %r15,%rdi
    29c4:	mov    $0x2,%edx
    29c9:	movzbl 0x2(%rcx),%eax
    29cd:	add    %eax,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 29fb, pgot_memcpy_table_func_pgot

```asm
    29f4:	lea    (%r12,%rax,4),%rcx
    29f8:	mov    0x0(%rip),%rax        # 29ff <HUF_decompress4X4_usingDTable_internal+0x7cf>
			29fb: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    29ff:	mov    %rcx,%rsi
    2a02:	mov    %rcx,-0xc0(%rbp)
    2a09:	jmp    2a1d <HUF_decompress4X4_usingDTable_internal+0x7ed>
    2a0b:	call   2a17 <HUF_decompress4X4_usingDTable_internal+0x7e7>
    2a10:	pause  
    2a12:	lfence 
    2a15:	jmp    2a10 <HUF_decompress4X4_usingDTable_internal+0x7e0>
    2a17:	mov    %rax,(%rsp)
    2a1b:	ret    
    2a1c:	int3   
    2a1d:	call   2a0b <HUF_decompress4X4_usingDTable_internal+0x7db>
    2a22:	mov    -0xc0(%rbp),%rcx
    2a29:	mov    %r14,%rdi
    2a2c:	mov    $0x2,%edx
    2a31:	movzbl 0x2(%rcx),%eax
    2a35:	add    %eax,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2a5d, pgot_memcpy_table_func_pgot

```asm
    2a56:	lea    (%r12,%rax,4),%rcx
    2a5a:	mov    0x0(%rip),%rax        # 2a61 <HUF_decompress4X4_usingDTable_internal+0x831>
			2a5d: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2a61:	mov    %rcx,%rsi
    2a64:	mov    %rcx,-0xc0(%rbp)
    2a6b:	jmp    2a7f <HUF_decompress4X4_usingDTable_internal+0x84f>
    2a6d:	call   2a79 <HUF_decompress4X4_usingDTable_internal+0x849>
    2a72:	pause  
    2a74:	lfence 
    2a77:	jmp    2a72 <HUF_decompress4X4_usingDTable_internal+0x842>
    2a79:	mov    %rax,(%rsp)
    2a7d:	ret    
    2a7e:	int3   
    2a7f:	call   2a6d <HUF_decompress4X4_usingDTable_internal+0x83d>
    2a84:	mov    -0xc0(%rbp),%rcx
    2a8b:	mov    %rbx,%rdi
    2a8e:	mov    $0x2,%edx
    2a93:	movzbl 0x2(%rcx),%eax
    2a97:	add    %eax,-0x68(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2abc, pgot_memcpy_table_func_pgot

```asm
    2ab5:	lea    (%r12,%rax,4),%rcx
    2ab9:	mov    0x0(%rip),%rax        # 2ac0 <HUF_decompress4X4_usingDTable_internal+0x890>
			2abc: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2ac0:	mov    %rcx,%rsi
    2ac3:	mov    %rcx,-0xc0(%rbp)
    2aca:	jmp    2ade <HUF_decompress4X4_usingDTable_internal+0x8ae>
    2acc:	call   2ad8 <HUF_decompress4X4_usingDTable_internal+0x8a8>
    2ad1:	pause  
    2ad3:	lfence 
    2ad6:	jmp    2ad1 <HUF_decompress4X4_usingDTable_internal+0x8a1>
    2ad8:	mov    %rax,(%rsp)
    2adc:	ret    
    2add:	int3   
    2ade:	call   2acc <HUF_decompress4X4_usingDTable_internal+0x89c>
    2ae3:	mov    -0xc0(%rbp),%rcx
    2aea:	mov    %r13,%rdi
    2aed:	mov    $0x2,%edx
    2af2:	movzbl 0x2(%rcx),%eax
    2af6:	add    %eax,-0x48(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2b21, pgot_memcpy_table_func_pgot

```asm
    2b1a:	lea    (%r12,%rax,4),%rcx
    2b1e:	mov    0x0(%rip),%rax        # 2b25 <HUF_decompress4X4_usingDTable_internal+0x8f5>
			2b21: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2b25:	mov    %rcx,%rsi
    2b28:	mov    %rcx,-0xc0(%rbp)
    2b2f:	jmp    2b43 <HUF_decompress4X4_usingDTable_internal+0x913>
    2b31:	call   2b3d <HUF_decompress4X4_usingDTable_internal+0x90d>
    2b36:	pause  
    2b38:	lfence 
    2b3b:	jmp    2b36 <HUF_decompress4X4_usingDTable_internal+0x906>
    2b3d:	mov    %rax,(%rsp)
    2b41:	ret    
    2b42:	int3   
    2b43:	call   2b31 <HUF_decompress4X4_usingDTable_internal+0x901>
    2b48:	mov    -0xc0(%rbp),%rcx
    2b4f:	mov    %r15,%rdi
    2b52:	mov    $0x2,%edx
    2b57:	movzbl 0x2(%rcx),%eax
    2b5b:	add    %eax,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2b89, pgot_memcpy_table_func_pgot

```asm
    2b82:	lea    (%r12,%rax,4),%rcx
    2b86:	mov    0x0(%rip),%rax        # 2b8d <HUF_decompress4X4_usingDTable_internal+0x95d>
			2b89: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2b8d:	mov    %rcx,%rsi
    2b90:	mov    %rcx,-0xc0(%rbp)
    2b97:	jmp    2bab <HUF_decompress4X4_usingDTable_internal+0x97b>
    2b99:	call   2ba5 <HUF_decompress4X4_usingDTable_internal+0x975>
    2b9e:	pause  
    2ba0:	lfence 
    2ba3:	jmp    2b9e <HUF_decompress4X4_usingDTable_internal+0x96e>
    2ba5:	mov    %rax,(%rsp)
    2ba9:	ret    
    2baa:	int3   
    2bab:	call   2b99 <HUF_decompress4X4_usingDTable_internal+0x969>
    2bb0:	mov    -0xc0(%rbp),%rcx
    2bb7:	mov    %r14,%rdi
    2bba:	mov    $0x2,%edx
    2bbf:	movzbl 0x2(%rcx),%eax
    2bc3:	add    %eax,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2beb, pgot_memcpy_table_func_pgot

```asm
    2be4:	lea    (%r12,%rax,4),%rcx
    2be8:	mov    0x0(%rip),%rax        # 2bef <HUF_decompress4X4_usingDTable_internal+0x9bf>
			2beb: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2bef:	mov    %rcx,%rsi
    2bf2:	mov    %rcx,-0xc0(%rbp)
    2bf9:	jmp    2c0d <HUF_decompress4X4_usingDTable_internal+0x9dd>
    2bfb:	call   2c07 <HUF_decompress4X4_usingDTable_internal+0x9d7>
    2c00:	pause  
    2c02:	lfence 
    2c05:	jmp    2c00 <HUF_decompress4X4_usingDTable_internal+0x9d0>
    2c07:	mov    %rax,(%rsp)
    2c0b:	ret    
    2c0c:	int3   
    2c0d:	call   2bfb <HUF_decompress4X4_usingDTable_internal+0x9cb>
    2c12:	mov    -0xc0(%rbp),%rcx
    2c19:	mov    %rbx,%rdi
    2c1c:	mov    $0x2,%edx
    2c21:	movzbl 0x2(%rcx),%eax
    2c25:	add    %eax,-0x68(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2c4a, pgot_memcpy_table_func_pgot

```asm
    2c43:	lea    (%r12,%rax,4),%rcx
    2c47:	mov    0x0(%rip),%rax        # 2c4e <HUF_decompress4X4_usingDTable_internal+0xa1e>
			2c4a: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2c4e:	mov    %rcx,%rsi
    2c51:	mov    %rcx,-0xc0(%rbp)
    2c58:	jmp    2c6c <HUF_decompress4X4_usingDTable_internal+0xa3c>
    2c5a:	call   2c66 <HUF_decompress4X4_usingDTable_internal+0xa36>
    2c5f:	pause  
    2c61:	lfence 
    2c64:	jmp    2c5f <HUF_decompress4X4_usingDTable_internal+0xa2f>
    2c66:	mov    %rax,(%rsp)
    2c6a:	ret    
    2c6b:	int3   
    2c6c:	call   2c5a <HUF_decompress4X4_usingDTable_internal+0xa2a>
    2c71:	mov    -0xc0(%rbp),%rcx
    2c78:	mov    %r13,%rdi
    2c7b:	mov    $0x2,%edx
    2c80:	movzbl 0x2(%rcx),%eax
    2c84:	add    %eax,-0x48(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2caf, pgot_memcpy_table_func_pgot

```asm
    2ca8:	lea    (%r12,%rax,4),%rcx
    2cac:	mov    0x0(%rip),%rax        # 2cb3 <HUF_decompress4X4_usingDTable_internal+0xa83>
			2caf: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2cb3:	mov    %rcx,%rsi
    2cb6:	mov    %rcx,-0xc0(%rbp)
    2cbd:	jmp    2cd1 <HUF_decompress4X4_usingDTable_internal+0xaa1>
    2cbf:	call   2ccb <HUF_decompress4X4_usingDTable_internal+0xa9b>
    2cc4:	pause  
    2cc6:	lfence 
    2cc9:	jmp    2cc4 <HUF_decompress4X4_usingDTable_internal+0xa94>
    2ccb:	mov    %rax,(%rsp)
    2ccf:	ret    
    2cd0:	int3   
    2cd1:	call   2cbf <HUF_decompress4X4_usingDTable_internal+0xa8f>
    2cd6:	mov    -0xc0(%rbp),%rcx
    2cdd:	mov    %r15,%rdi
    2ce0:	mov    $0x2,%edx
    2ce5:	movzbl 0x2(%rcx),%eax
    2ce9:	add    %eax,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2d17, pgot_memcpy_table_func_pgot

```asm
    2d10:	lea    (%r12,%rax,4),%rcx
    2d14:	mov    0x0(%rip),%rax        # 2d1b <HUF_decompress4X4_usingDTable_internal+0xaeb>
			2d17: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2d1b:	mov    %rcx,%rsi
    2d1e:	mov    %rcx,-0xc0(%rbp)
    2d25:	jmp    2d39 <HUF_decompress4X4_usingDTable_internal+0xb09>
    2d27:	call   2d33 <HUF_decompress4X4_usingDTable_internal+0xb03>
    2d2c:	pause  
    2d2e:	lfence 
    2d31:	jmp    2d2c <HUF_decompress4X4_usingDTable_internal+0xafc>
    2d33:	mov    %rax,(%rsp)
    2d37:	ret    
    2d38:	int3   
    2d39:	call   2d27 <HUF_decompress4X4_usingDTable_internal+0xaf7>
    2d3e:	mov    -0xc0(%rbp),%rcx
    2d45:	mov    %r14,%rdi
    2d48:	mov    $0x2,%edx
    2d4d:	movzbl 0x2(%rcx),%eax
    2d51:	add    %eax,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2d79, pgot_memcpy_table_func_pgot

```asm
    2d72:	lea    (%r12,%rax,4),%rcx
    2d76:	mov    0x0(%rip),%rax        # 2d7d <HUF_decompress4X4_usingDTable_internal+0xb4d>
			2d79: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2d7d:	mov    %rcx,%rsi
    2d80:	mov    %rcx,-0xc0(%rbp)
    2d87:	jmp    2d9b <HUF_decompress4X4_usingDTable_internal+0xb6b>
    2d89:	call   2d95 <HUF_decompress4X4_usingDTable_internal+0xb65>
    2d8e:	pause  
    2d90:	lfence 
    2d93:	jmp    2d8e <HUF_decompress4X4_usingDTable_internal+0xb5e>
    2d95:	mov    %rax,(%rsp)
    2d99:	ret    
    2d9a:	int3   
    2d9b:	call   2d89 <HUF_decompress4X4_usingDTable_internal+0xb59>
    2da0:	mov    -0xc0(%rbp),%rcx
    2da7:	mov    $0x2,%edx
    2dac:	mov    %rbx,%rdi
    2daf:	movzbl 0x2(%rcx),%eax
    2db3:	add    %eax,-0x68(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2dd8, pgot_memcpy_table_func_pgot

```asm
    2dd1:	lea    (%r12,%rax,4),%rcx
    2dd5:	mov    0x0(%rip),%rax        # 2ddc <HUF_decompress4X4_usingDTable_internal+0xbac>
			2dd8: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2ddc:	mov    %rcx,-0xc0(%rbp)
    2de3:	mov    %rcx,%rsi
    2de6:	jmp    2dfa <HUF_decompress4X4_usingDTable_internal+0xbca>
    2de8:	call   2df4 <HUF_decompress4X4_usingDTable_internal+0xbc4>
    2ded:	pause  
    2def:	lfence 
    2df2:	jmp    2ded <HUF_decompress4X4_usingDTable_internal+0xbbd>
    2df4:	mov    %rax,(%rsp)
    2df8:	ret    
    2df9:	int3   
    2dfa:	call   2de8 <HUF_decompress4X4_usingDTable_internal+0xbb8>
    2dff:	mov    -0xc0(%rbp),%rcx
    2e06:	movzbl 0x3(%rcx),%edx
    2e0a:	movzbl 0x2(%rcx),%eax
    2e0e:	mov    -0xa8(%rbp),%ecx
    2e14:	add    -0x48(%rbp),%eax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2f53, pgot_memcpy_table_func_pgot

```asm
    2f4c:	lea    (%r12,%rax,4),%r14
    2f50:	mov    0x0(%rip),%rax        # 2f57 <HUF_decompress4X4_usingDTable_internal+0xd27>
			2f53: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2f57:	mov    %r14,%rsi
    2f5a:	jmp    2f6e <HUF_decompress4X4_usingDTable_internal+0xd3e>
    2f5c:	call   2f68 <HUF_decompress4X4_usingDTable_internal+0xd38>
    2f61:	pause  
    2f63:	lfence 
    2f66:	jmp    2f61 <HUF_decompress4X4_usingDTable_internal+0xd31>
    2f68:	mov    %rax,(%rsp)
    2f6c:	ret    
    2f6d:	int3   
    2f6e:	call   2f5c <HUF_decompress4X4_usingDTable_internal+0xd2c>
    2f73:	movzbl 0x3(%r14),%eax
    2f78:	movzbl 0x2(%r14),%ecx
    2f7d:	mov    $0x2,%edx
    2f82:	add    -0xa8(%rbp),%ecx
    2f88:	add    %rax,%r13
    2f8b:	mov    -0xb0(%rbp),%rax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 2faa, pgot_memcpy_table_func_pgot

```asm
    2fa3:	lea    (%r12,%rax,4),%r14
    2fa7:	mov    0x0(%rip),%rax        # 2fae <HUF_decompress4X4_usingDTable_internal+0xd7e>
			2faa: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    2fae:	mov    %r14,%rsi
    2fb1:	jmp    2fc5 <HUF_decompress4X4_usingDTable_internal+0xd95>
    2fb3:	call   2fbf <HUF_decompress4X4_usingDTable_internal+0xd8f>
    2fb8:	pause  
    2fba:	lfence 
    2fbd:	jmp    2fb8 <HUF_decompress4X4_usingDTable_internal+0xd88>
    2fbf:	mov    %rax,(%rsp)
    2fc3:	ret    
    2fc4:	int3   
    2fc5:	call   2fb3 <HUF_decompress4X4_usingDTable_internal+0xd83>
    2fca:	mov    -0xb0(%rbp),%rax
    2fd1:	movzbl 0x2(%r14),%ecx
    2fd6:	mov    $0x2,%edx
    2fdb:	add    -0xa8(%rbp),%ecx
    2fe1:	movzbl 0x3(%r14),%edi
    2fe6:	mov    %ecx,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3001, pgot_memcpy_table_func_pgot

```asm
    2ffb:	mov    %r13,%rdi
    2ffe:	mov    0x0(%rip),%rax        # 3005 <HUF_decompress4X4_usingDTable_internal+0xdd5>
			3001: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3005:	mov    %r14,%rsi
    3008:	jmp    301c <HUF_decompress4X4_usingDTable_internal+0xdec>
    300a:	call   3016 <HUF_decompress4X4_usingDTable_internal+0xde6>
    300f:	pause  
    3011:	lfence 
    3014:	jmp    300f <HUF_decompress4X4_usingDTable_internal+0xddf>
    3016:	mov    %rax,(%rsp)
    301a:	ret    
    301b:	int3   
    301c:	call   300a <HUF_decompress4X4_usingDTable_internal+0xdda>
    3021:	mov    -0xb0(%rbp),%rax
    3028:	movzbl 0x2(%r14),%ecx
    302d:	mov    $0x2,%edx
    3032:	add    -0xa8(%rbp),%ecx
    3038:	movzbl 0x3(%r14),%r8d
    303d:	mov    %ecx,-0xa8(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3058, pgot_memcpy_table_func_pgot

```asm
    3052:	mov    %r13,%rdi
    3055:	mov    0x0(%rip),%rax        # 305c <HUF_decompress4X4_usingDTable_internal+0xe2c>
			3058: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    305c:	mov    %r14,%rsi
    305f:	jmp    3073 <HUF_decompress4X4_usingDTable_internal+0xe43>
    3061:	call   306d <HUF_decompress4X4_usingDTable_internal+0xe3d>
    3066:	pause  
    3068:	lfence 
    306b:	jmp    3066 <HUF_decompress4X4_usingDTable_internal+0xe36>
    306d:	mov    %rax,(%rsp)
    3071:	ret    
    3072:	int3   
    3073:	call   3061 <HUF_decompress4X4_usingDTable_internal+0xe31>
    3078:	movzbl 0x3(%r14),%eax
    307d:	movzbl 0x2(%r14),%ecx
    3082:	add    -0xa8(%rbp),%ecx
    3088:	mov    %ecx,-0xa8(%rbp)
    308e:	add    %rax,%r13
    3091:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 320f, pgot_memcpy_table_func_pgot

```asm
    3208:	lea    (%r12,%rax,4),%r14
    320c:	mov    0x0(%rip),%rax        # 3213 <HUF_decompress4X4_usingDTable_internal+0xfe3>
			320f: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3213:	mov    %r14,%rsi
    3216:	jmp    322a <HUF_decompress4X4_usingDTable_internal+0xffa>
    3218:	call   3224 <HUF_decompress4X4_usingDTable_internal+0xff4>
    321d:	pause  
    321f:	lfence 
    3222:	jmp    321d <HUF_decompress4X4_usingDTable_internal+0xfed>
    3224:	mov    %rax,(%rsp)
    3228:	ret    
    3229:	int3   
    322a:	call   3218 <HUF_decompress4X4_usingDTable_internal+0xfe8>
    322f:	movzbl 0x3(%r14),%eax
    3234:	movzbl 0x2(%r14),%ecx
    3239:	add    -0xa8(%rbp),%ecx
    323f:	add    %rax,%r13
    3242:	mov    %ecx,-0xa8(%rbp)
    3248:	cmp    %rbx,%r13
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3322, pgot_memcpy_table_func_pgot

```asm
    331b:	lea    (%r12,%rax,4),%r14
    331f:	mov    0x0(%rip),%rax        # 3326 <HUF_decompress4X4_usingDTable_internal+0x10f6>
			3322: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3326:	mov    %r14,%rsi
    3329:	jmp    333d <HUF_decompress4X4_usingDTable_internal+0x110d>
    332b:	call   3337 <HUF_decompress4X4_usingDTable_internal+0x1107>
    3330:	pause  
    3332:	lfence 
    3335:	jmp    3330 <HUF_decompress4X4_usingDTable_internal+0x1100>
    3337:	mov    %rax,(%rsp)
    333b:	ret    
    333c:	int3   
    333d:	call   332b <HUF_decompress4X4_usingDTable_internal+0x10fb>
    3342:	movzbl 0x3(%r14),%eax
    3347:	movzbl 0x2(%r14),%ecx
    334c:	mov    $0x2,%edx
    3351:	add    -0x88(%rbp),%ecx
    3357:	add    %rax,%r13
    335a:	mov    -0x90(%rbp),%rax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3379, pgot_memcpy_table_func_pgot

```asm
    3372:	lea    (%r12,%rax,4),%r14
    3376:	mov    0x0(%rip),%rax        # 337d <HUF_decompress4X4_usingDTable_internal+0x114d>
			3379: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    337d:	mov    %r14,%rsi
    3380:	jmp    3394 <HUF_decompress4X4_usingDTable_internal+0x1164>
    3382:	call   338e <HUF_decompress4X4_usingDTable_internal+0x115e>
    3387:	pause  
    3389:	lfence 
    338c:	jmp    3387 <HUF_decompress4X4_usingDTable_internal+0x1157>
    338e:	mov    %rax,(%rsp)
    3392:	ret    
    3393:	int3   
    3394:	call   3382 <HUF_decompress4X4_usingDTable_internal+0x1152>
    3399:	mov    -0x90(%rbp),%rax
    33a0:	movzbl 0x2(%r14),%ecx
    33a5:	mov    $0x2,%edx
    33aa:	add    -0x88(%rbp),%ecx
    33b0:	movzbl 0x3(%r14),%edi
    33b5:	mov    %ecx,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 33d0, pgot_memcpy_table_func_pgot

```asm
    33ca:	mov    %r13,%rdi
    33cd:	mov    0x0(%rip),%rax        # 33d4 <HUF_decompress4X4_usingDTable_internal+0x11a4>
			33d0: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    33d4:	mov    %r14,%rsi
    33d7:	jmp    33eb <HUF_decompress4X4_usingDTable_internal+0x11bb>
    33d9:	call   33e5 <HUF_decompress4X4_usingDTable_internal+0x11b5>
    33de:	pause  
    33e0:	lfence 
    33e3:	jmp    33de <HUF_decompress4X4_usingDTable_internal+0x11ae>
    33e5:	mov    %rax,(%rsp)
    33e9:	ret    
    33ea:	int3   
    33eb:	call   33d9 <HUF_decompress4X4_usingDTable_internal+0x11a9>
    33f0:	mov    -0x90(%rbp),%rax
    33f7:	movzbl 0x2(%r14),%ecx
    33fc:	mov    $0x2,%edx
    3401:	add    -0x88(%rbp),%ecx
    3407:	movzbl 0x3(%r14),%r8d
    340c:	mov    %ecx,-0x88(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3427, pgot_memcpy_table_func_pgot

```asm
    3421:	mov    %r13,%rdi
    3424:	mov    0x0(%rip),%rax        # 342b <HUF_decompress4X4_usingDTable_internal+0x11fb>
			3427: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    342b:	mov    %r14,%rsi
    342e:	jmp    3442 <HUF_decompress4X4_usingDTable_internal+0x1212>
    3430:	call   343c <HUF_decompress4X4_usingDTable_internal+0x120c>
    3435:	pause  
    3437:	lfence 
    343a:	jmp    3435 <HUF_decompress4X4_usingDTable_internal+0x1205>
    343c:	mov    %rax,(%rsp)
    3440:	ret    
    3441:	int3   
    3442:	call   3430 <HUF_decompress4X4_usingDTable_internal+0x1200>
    3447:	movzbl 0x3(%r14),%eax
    344c:	movzbl 0x2(%r14),%ecx
    3451:	add    -0x88(%rbp),%ecx
    3457:	mov    %ecx,-0x88(%rbp)
    345d:	add    %rax,%r13
    3460:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 351d, pgot_memcpy_table_func_pgot

```asm
    3516:	lea    (%r12,%rax,4),%r15
    351a:	mov    0x0(%rip),%rax        # 3521 <HUF_decompress4X4_usingDTable_internal+0x12f1>
			351d: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3521:	mov    %r15,%rsi
    3524:	jmp    3538 <HUF_decompress4X4_usingDTable_internal+0x1308>
    3526:	call   3532 <HUF_decompress4X4_usingDTable_internal+0x1302>
    352b:	pause  
    352d:	lfence 
    3530:	jmp    352b <HUF_decompress4X4_usingDTable_internal+0x12fb>
    3532:	mov    %rax,(%rsp)
    3536:	ret    
    3537:	int3   
    3538:	call   3526 <HUF_decompress4X4_usingDTable_internal+0x12f6>
    353d:	movzbl 0x3(%r15),%eax
    3542:	movzbl 0x2(%r15),%ecx
    3547:	add    -0x88(%rbp),%ecx
    354d:	add    %rax,%r14
    3550:	mov    %ecx,-0x88(%rbp)
    3556:	cmp    %rbx,%r14
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3605, pgot_memcpy_table_func_pgot

```asm
    35fe:	lea    (%r12,%rax,4),%r15
    3602:	mov    0x0(%rip),%rax        # 3609 <HUF_decompress4X4_usingDTable_internal+0x13d9>
			3605: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3609:	mov    %r15,%rsi
    360c:	jmp    3620 <HUF_decompress4X4_usingDTable_internal+0x13f0>
    360e:	call   361a <HUF_decompress4X4_usingDTable_internal+0x13ea>
    3613:	pause  
    3615:	lfence 
    3618:	jmp    3613 <HUF_decompress4X4_usingDTable_internal+0x13e3>
    361a:	mov    %rax,(%rsp)
    361e:	ret    
    361f:	int3   
    3620:	call   360e <HUF_decompress4X4_usingDTable_internal+0x13de>
    3625:	movzbl 0x3(%r15),%eax
    362a:	movzbl 0x2(%r15),%ecx
    362f:	mov    $0x2,%edx
    3634:	add    -0x68(%rbp),%ecx
    3637:	add    %rax,%r14
    363a:	mov    -0x70(%rbp),%rax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3653, pgot_memcpy_table_func_pgot

```asm
    364c:	lea    (%r12,%rax,4),%r15
    3650:	mov    0x0(%rip),%rax        # 3657 <HUF_decompress4X4_usingDTable_internal+0x1427>
			3653: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3657:	mov    %r15,%rsi
    365a:	jmp    366e <HUF_decompress4X4_usingDTable_internal+0x143e>
    365c:	call   3668 <HUF_decompress4X4_usingDTable_internal+0x1438>
    3661:	pause  
    3663:	lfence 
    3666:	jmp    3661 <HUF_decompress4X4_usingDTable_internal+0x1431>
    3668:	mov    %rax,(%rsp)
    366c:	ret    
    366d:	int3   
    366e:	call   365c <HUF_decompress4X4_usingDTable_internal+0x142c>
    3673:	movzbl 0x3(%r15),%eax
    3678:	movzbl 0x2(%r15),%ecx
    367d:	mov    $0x2,%edx
    3682:	add    -0x68(%rbp),%ecx
    3685:	add    %rax,%r14
    3688:	mov    -0x70(%rbp),%rax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 36a1, pgot_memcpy_table_func_pgot

```asm
    369a:	lea    (%r12,%rax,4),%r15
    369e:	mov    0x0(%rip),%rax        # 36a5 <HUF_decompress4X4_usingDTable_internal+0x1475>
			36a1: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    36a5:	mov    %r15,%rsi
    36a8:	jmp    36bc <HUF_decompress4X4_usingDTable_internal+0x148c>
    36aa:	call   36b6 <HUF_decompress4X4_usingDTable_internal+0x1486>
    36af:	pause  
    36b1:	lfence 
    36b4:	jmp    36af <HUF_decompress4X4_usingDTable_internal+0x147f>
    36b6:	mov    %rax,(%rsp)
    36ba:	ret    
    36bb:	int3   
    36bc:	call   36aa <HUF_decompress4X4_usingDTable_internal+0x147a>
    36c1:	mov    -0x70(%rbp),%rax
    36c5:	movzbl 0x2(%r15),%ecx
    36ca:	mov    $0x2,%edx
    36cf:	add    -0x68(%rbp),%ecx
    36d2:	movzbl 0x3(%r15),%edi
    36d7:	mov    %ecx,-0x68(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 36f0, pgot_memcpy_table_func_pgot

```asm
    36ea:	mov    %r15,%rdi
    36ed:	mov    0x0(%rip),%rax        # 36f4 <HUF_decompress4X4_usingDTable_internal+0x14c4>
			36f0: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    36f4:	mov    %r14,%rsi
    36f7:	jmp    370b <HUF_decompress4X4_usingDTable_internal+0x14db>
    36f9:	call   3705 <HUF_decompress4X4_usingDTable_internal+0x14d5>
    36fe:	pause  
    3700:	lfence 
    3703:	jmp    36fe <HUF_decompress4X4_usingDTable_internal+0x14ce>
    3705:	mov    %rax,(%rsp)
    3709:	ret    
    370a:	int3   
    370b:	call   36f9 <HUF_decompress4X4_usingDTable_internal+0x14c9>
    3710:	movzbl 0x3(%r14),%eax
    3715:	movzbl 0x2(%r14),%ecx
    371a:	add    -0x68(%rbp),%ecx
    371d:	mov    %ecx,-0x68(%rbp)
    3720:	lea    (%r15,%rax,1),%r14
    3724:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 37f8, pgot_memcpy_table_func_pgot

```asm
    37f1:	lea    (%r12,%rax,4),%r15
    37f5:	mov    0x0(%rip),%rax        # 37fc <HUF_decompress4X4_usingDTable_internal+0x15cc>
			37f8: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    37fc:	mov    %r15,%rsi
    37ff:	jmp    3813 <HUF_decompress4X4_usingDTable_internal+0x15e3>
    3801:	call   380d <HUF_decompress4X4_usingDTable_internal+0x15dd>
    3806:	pause  
    3808:	lfence 
    380b:	jmp    3806 <HUF_decompress4X4_usingDTable_internal+0x15d6>
    380d:	mov    %rax,(%rsp)
    3811:	ret    
    3812:	int3   
    3813:	call   3801 <HUF_decompress4X4_usingDTable_internal+0x15d1>
    3818:	movzbl 0x3(%r15),%edx
    381d:	movzbl 0x2(%r15),%eax
    3822:	add    -0x68(%rbp),%eax
    3825:	mov    %eax,-0x68(%rbp)
    3828:	add    %rdx,%r14
    382b:	cmp    $0x40,%eax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3998, pgot_memcpy_table_func_pgot

```asm
    3991:	lea    (%r12,%rax,4),%r13
    3995:	mov    0x0(%rip),%rax        # 399c <HUF_decompress4X4_usingDTable_internal+0x176c>
			3998: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    399c:	mov    %r13,%rsi
    399f:	jmp    39b3 <HUF_decompress4X4_usingDTable_internal+0x1783>
    39a1:	call   39ad <HUF_decompress4X4_usingDTable_internal+0x177d>
    39a6:	pause  
    39a8:	lfence 
    39ab:	jmp    39a6 <HUF_decompress4X4_usingDTable_internal+0x1776>
    39ad:	mov    %rax,(%rsp)
    39b1:	ret    
    39b2:	int3   
    39b3:	call   39a1 <HUF_decompress4X4_usingDTable_internal+0x1771>
    39b8:	movzbl 0x3(%r13),%edx
    39bd:	movzbl 0x2(%r13),%eax
    39c2:	add    -0xa8(%rbp),%eax
    39c8:	mov    %eax,-0xa8(%rbp)
    39ce:	add    %rdx,%rbx
    39d1:	cmp    $0x40,%eax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3af9, pgot_memcpy_table_func_pgot

```asm
    3af2:	lea    (%r12,%rax,4),%rbx
    3af6:	mov    0x0(%rip),%rax        # 3afd <HUF_decompress4X4_usingDTable_internal+0x18cd>
			3af9: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3afd:	mov    %rbx,%rsi
    3b00:	jmp    3b14 <HUF_decompress4X4_usingDTable_internal+0x18e4>
    3b02:	call   3b0e <HUF_decompress4X4_usingDTable_internal+0x18de>
    3b07:	pause  
    3b09:	lfence 
    3b0c:	jmp    3b07 <HUF_decompress4X4_usingDTable_internal+0x18d7>
    3b0e:	mov    %rax,(%rsp)
    3b12:	ret    
    3b13:	int3   
    3b14:	call   3b02 <HUF_decompress4X4_usingDTable_internal+0x18d2>
    3b19:	movzbl 0x3(%rbx),%edx
    3b1d:	movzbl 0x2(%rbx),%eax
    3b21:	add    -0x88(%rbp),%eax
    3b27:	mov    %eax,-0x88(%rbp)
    3b2d:	add    %rdx,%r15
    3b30:	cmp    $0x40,%eax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3bd0, pgot_memcpy_table_func_pgot

```asm
    3bc9:	lea    (%r12,%rax,4),%r13
    3bcd:	mov    0x0(%rip),%rax        # 3bd4 <HUF_decompress4X4_usingDTable_internal+0x19a4>
			3bd0: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3bd4:	mov    %r13,%rsi
    3bd7:	jmp    3beb <HUF_decompress4X4_usingDTable_internal+0x19bb>
    3bd9:	call   3be5 <HUF_decompress4X4_usingDTable_internal+0x19b5>
    3bde:	pause  
    3be0:	lfence 
    3be3:	jmp    3bde <HUF_decompress4X4_usingDTable_internal+0x19ae>
    3be5:	mov    %rax,(%rsp)
    3be9:	ret    
    3bea:	int3   
    3beb:	call   3bd9 <HUF_decompress4X4_usingDTable_internal+0x19a9>
    3bf0:	movzbl 0x3(%r13),%eax
    3bf5:	movzbl 0x2(%r13),%ecx
    3bfa:	add    -0x68(%rbp),%ecx
    3bfd:	add    %rax,%r14
    3c00:	mov    %ecx,-0x68(%rbp)
    3c03:	cmp    %rbx,%r14
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3c99, pgot_memcpy_table_func_pgot

```asm
    3c92:	lea    (%r12,%rax,4),%r15
    3c96:	mov    0x0(%rip),%rax        # 3c9d <HUF_decompress4X4_usingDTable_internal+0x1a6d>
			3c99: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3c9d:	mov    %r15,%rsi
    3ca0:	jmp    3cb4 <HUF_decompress4X4_usingDTable_internal+0x1a84>
    3ca2:	call   3cae <HUF_decompress4X4_usingDTable_internal+0x1a7e>
    3ca7:	pause  
    3ca9:	lfence 
    3cac:	jmp    3ca7 <HUF_decompress4X4_usingDTable_internal+0x1a77>
    3cae:	mov    %rax,(%rsp)
    3cb2:	ret    
    3cb3:	int3   
    3cb4:	call   3ca2 <HUF_decompress4X4_usingDTable_internal+0x1a72>
    3cb9:	movzbl 0x3(%r15),%eax
    3cbe:	movzbl 0x2(%r15),%ecx
    3cc3:	mov    $0x2,%edx
    3cc8:	add    -0x48(%rbp),%ecx
    3ccb:	add    %rax,%r13
    3cce:	mov    -0x50(%rbp),%rax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3ce7, pgot_memcpy_table_func_pgot

```asm
    3ce0:	lea    (%r12,%rax,4),%r15
    3ce4:	mov    0x0(%rip),%rax        # 3ceb <HUF_decompress4X4_usingDTable_internal+0x1abb>
			3ce7: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3ceb:	mov    %r15,%rsi
    3cee:	jmp    3d02 <HUF_decompress4X4_usingDTable_internal+0x1ad2>
    3cf0:	call   3cfc <HUF_decompress4X4_usingDTable_internal+0x1acc>
    3cf5:	pause  
    3cf7:	lfence 
    3cfa:	jmp    3cf5 <HUF_decompress4X4_usingDTable_internal+0x1ac5>
    3cfc:	mov    %rax,(%rsp)
    3d00:	ret    
    3d01:	int3   
    3d02:	call   3cf0 <HUF_decompress4X4_usingDTable_internal+0x1ac0>
    3d07:	movzbl 0x3(%r15),%eax
    3d0c:	movzbl 0x2(%r15),%ecx
    3d11:	mov    $0x2,%edx
    3d16:	add    -0x48(%rbp),%ecx
    3d19:	add    %rax,%r13
    3d1c:	mov    -0x50(%rbp),%rax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3d35, pgot_memcpy_table_func_pgot

```asm
    3d2e:	lea    (%r12,%rax,4),%r15
    3d32:	mov    0x0(%rip),%rax        # 3d39 <HUF_decompress4X4_usingDTable_internal+0x1b09>
			3d35: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3d39:	mov    %r15,%rsi
    3d3c:	jmp    3d50 <HUF_decompress4X4_usingDTable_internal+0x1b20>
    3d3e:	call   3d4a <HUF_decompress4X4_usingDTable_internal+0x1b1a>
    3d43:	pause  
    3d45:	lfence 
    3d48:	jmp    3d43 <HUF_decompress4X4_usingDTable_internal+0x1b13>
    3d4a:	mov    %rax,(%rsp)
    3d4e:	ret    
    3d4f:	int3   
    3d50:	call   3d3e <HUF_decompress4X4_usingDTable_internal+0x1b0e>
    3d55:	movzbl 0x3(%r15),%eax
    3d5a:	movzbl 0x2(%r15),%ecx
    3d5f:	mov    $0x2,%edx
    3d64:	add    -0x48(%rbp),%ecx
    3d67:	add    %rax,%r13
    3d6a:	mov    -0x50(%rbp),%rax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3d83, pgot_memcpy_table_func_pgot

```asm
    3d7c:	lea    (%r12,%rax,4),%r15
    3d80:	mov    0x0(%rip),%rax        # 3d87 <HUF_decompress4X4_usingDTable_internal+0x1b57>
			3d83: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3d87:	mov    %r15,%rsi
    3d8a:	jmp    3d9e <HUF_decompress4X4_usingDTable_internal+0x1b6e>
    3d8c:	call   3d98 <HUF_decompress4X4_usingDTable_internal+0x1b68>
    3d91:	pause  
    3d93:	lfence 
    3d96:	jmp    3d91 <HUF_decompress4X4_usingDTable_internal+0x1b61>
    3d98:	mov    %rax,(%rsp)
    3d9c:	ret    
    3d9d:	int3   
    3d9e:	call   3d8c <HUF_decompress4X4_usingDTable_internal+0x1b5c>
    3da3:	movzbl 0x3(%r15),%eax
    3da8:	movzbl 0x2(%r15),%ecx
    3dad:	add    -0x48(%rbp),%ecx
    3db0:	mov    %ecx,-0x48(%rbp)
    3db3:	add    %rax,%r13
    3db6:	cmp    $0x40,%ecx
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3e7b, pgot_memcpy_table_func_pgot

```asm
    3e74:	lea    (%r12,%rax,4),%r15
    3e78:	mov    0x0(%rip),%rax        # 3e7f <HUF_decompress4X4_usingDTable_internal+0x1c4f>
			3e7b: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3e7f:	mov    %r15,%rsi
    3e82:	jmp    3e96 <HUF_decompress4X4_usingDTable_internal+0x1c66>
    3e84:	call   3e90 <HUF_decompress4X4_usingDTable_internal+0x1c60>
    3e89:	pause  
    3e8b:	lfence 
    3e8e:	jmp    3e89 <HUF_decompress4X4_usingDTable_internal+0x1c59>
    3e90:	mov    %rax,(%rsp)
    3e94:	ret    
    3e95:	int3   
    3e96:	call   3e84 <HUF_decompress4X4_usingDTable_internal+0x1c54>
    3e9b:	movzbl 0x3(%r15),%edx
    3ea0:	movzbl 0x2(%r15),%eax
    3ea5:	add    -0x48(%rbp),%eax
    3ea8:	mov    %eax,-0x48(%rbp)
    3eab:	add    %rdx,%r13
    3eae:	cmp    $0x40,%eax
```

## 04_zstd_decompress/retpoline/func_pgot: HUF_decompress4X4_usingDTable_internal, 3f56, pgot_memcpy_table_func_pgot

```asm
    3f4f:	lea    (%r12,%rax,4),%r15
    3f53:	mov    0x0(%rip),%rax        # 3f5a <HUF_decompress4X4_usingDTable_internal+0x1d2a>
			3f56: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    3f5a:	mov    %r15,%rsi
    3f5d:	jmp    3f71 <HUF_decompress4X4_usingDTable_internal+0x1d41>
    3f5f:	call   3f6b <HUF_decompress4X4_usingDTable_internal+0x1d3b>
    3f64:	pause  
    3f66:	lfence 
    3f69:	jmp    3f64 <HUF_decompress4X4_usingDTable_internal+0x1d34>
    3f6b:	mov    %rax,(%rsp)
    3f6f:	ret    
    3f70:	int3   
    3f71:	call   3f5f <HUF_decompress4X4_usingDTable_internal+0x1d2f>
    3f76:	movzbl 0x3(%r15),%eax
    3f7b:	movzbl 0x2(%r15),%ecx
    3f80:	add    -0x48(%rbp),%ecx
    3f83:	add    %rax,%r13
    3f86:	mov    %ecx,-0x48(%rbp)
    3f89:	cmp    %rbx,%r13
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_readDTableX2_wksp_func_pgot, 4240, pgot_memcpy_table_func_pgot

```asm
    4238:	mov    $0x4,%edx
    423d:	mov    0x0(%rip),%rax        # 4244 <pgot_HUF_readDTableX2_wksp_func_pgot+0xa4>
			4240: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4244:	mov    %rbx,%rsi
    4247:	lea    -0x34(%rbp),%rdi
    424b:	jmp    425f <pgot_HUF_readDTableX2_wksp_func_pgot+0xbf>
    424d:	call   4259 <pgot_HUF_readDTableX2_wksp_func_pgot+0xb9>
    4252:	pause  
    4254:	lfence 
    4257:	jmp    4252 <pgot_HUF_readDTableX2_wksp_func_pgot+0xb2>
    4259:	mov    %rax,(%rsp)
    425d:	ret    
    425e:	int3   
    425f:	call   424d <pgot_HUF_readDTableX2_wksp_func_pgot+0xad>
    4264:	movzbl -0x34(%rbp),%eax
    4268:	mov    -0x3c(%rbp),%edx
    426b:	add    $0x1,%eax
    426e:	cmp    %edx,%eax
    4270:	jb     437d <pgot_HUF_readDTableX2_wksp_func_pgot+0x1dd>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_readDTableX2_wksp_func_pgot, 4283, pgot_memcpy_table_func_pgot

```asm
    427d:	mov    %rbx,%rdi
    4280:	mov    0x0(%rip),%rax        # 4287 <pgot_HUF_readDTableX2_wksp_func_pgot+0xe7>
			4283: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4287:	movb   $0x0,-0x33(%rbp)
    428b:	mov    $0x4,%edx
    4290:	jmp    42a4 <pgot_HUF_readDTableX2_wksp_func_pgot+0x104>
    4292:	call   429e <pgot_HUF_readDTableX2_wksp_func_pgot+0xfe>
    4297:	pause  
    4299:	lfence 
    429c:	jmp    4297 <pgot_HUF_readDTableX2_wksp_func_pgot+0xf7>
    429e:	mov    %rax,(%rsp)
    42a2:	ret    
    42a3:	int3   
    42a4:	call   4292 <pgot_HUF_readDTableX2_wksp_func_pgot+0xf2>
    42a9:	mov    -0x3c(%rbp),%r9d
    42ad:	lea    0x1(%r9),%esi
    42b1:	cmp    $0x1,%esi
    42b4:	jbe    42f8 <pgot_HUF_readDTableX2_wksp_func_pgot+0x158>
    42b6:	mov    0x4(%r12),%r10d
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_decompress1X2_usingDTable_func_pgot, 43d3, pgot_memcpy_table_func_pgot

```asm
    43ce:	xor    %eax,%eax
    43d0:	mov    0x0(%rip),%rax        # 43d7 <pgot_HUF_decompress1X2_usingDTable_func_pgot+0x47>
			43d3: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    43d7:	jmp    43eb <pgot_HUF_decompress1X2_usingDTable_func_pgot+0x5b>
    43d9:	call   43e5 <pgot_HUF_decompress1X2_usingDTable_func_pgot+0x55>
    43de:	pause  
    43e0:	lfence 
    43e3:	jmp    43de <pgot_HUF_decompress1X2_usingDTable_func_pgot+0x4e>
    43e5:	mov    %rax,(%rsp)
    43e9:	ret    
    43ea:	int3   
    43eb:	call   43d9 <pgot_HUF_decompress1X2_usingDTable_func_pgot+0x49>
    43f0:	cmpb   $0x0,-0x33(%rbp)
    43f4:	mov    $0xffffffffffffffff,%rax
    43fb:	jne    4411 <pgot_HUF_decompress1X2_usingDTable_func_pgot+0x81>
    43fd:	mov    %rbx,%r8
    4400:	mov    %r15,%rcx
    4403:	mov    %r14,%rdx
    4406:	mov    %r13,%rsi
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_decompress4X2_usingDTable_func_pgot, 4513, pgot_memcpy_table_func_pgot

```asm
    450e:	xor    %eax,%eax
    4510:	mov    0x0(%rip),%rax        # 4517 <pgot_HUF_decompress4X2_usingDTable_func_pgot+0x47>
			4513: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4517:	jmp    452b <pgot_HUF_decompress4X2_usingDTable_func_pgot+0x5b>
    4519:	call   4525 <pgot_HUF_decompress4X2_usingDTable_func_pgot+0x55>
    451e:	pause  
    4520:	lfence 
    4523:	jmp    451e <pgot_HUF_decompress4X2_usingDTable_func_pgot+0x4e>
    4525:	mov    %rax,(%rsp)
    4529:	ret    
    452a:	int3   
    452b:	call   4519 <pgot_HUF_decompress4X2_usingDTable_func_pgot+0x49>
    4530:	cmpb   $0x0,-0x33(%rbp)
    4534:	mov    $0xffffffffffffffff,%rax
    453b:	jne    4551 <pgot_HUF_decompress4X2_usingDTable_func_pgot+0x81>
    453d:	mov    %rbx,%r8
    4540:	mov    %r15,%rcx
    4543:	mov    %r14,%rdx
    4546:	mov    %r13,%rsi
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_readDTableX4_wksp_func_pgot, 4658, pgot_memcpy_table_func_pgot

```asm
    4653:	xor    %eax,%eax
    4655:	mov    0x0(%rip),%rax        # 465c <pgot_HUF_readDTableX4_wksp_func_pgot+0x4c>
			4658: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    465c:	jmp    4670 <pgot_HUF_readDTableX4_wksp_func_pgot+0x60>
    465e:	call   466a <pgot_HUF_readDTableX4_wksp_func_pgot+0x5a>
    4663:	pause  
    4665:	lfence 
    4668:	jmp    4663 <pgot_HUF_readDTableX4_wksp_func_pgot+0x53>
    466a:	mov    %rax,(%rsp)
    466e:	ret    
    466f:	int3   
    4670:	call   465e <pgot_HUF_readDTableX4_wksp_func_pgot+0x4e>
    4675:	movzbl -0x68(%rbp),%r12d
    467a:	mov    %r12b,-0xbd(%rbp)
    4681:	cmp    $0x5db,%rbx
    4688:	jbe    4a56 <pgot_HUF_readDTableX4_wksp_func_pgot+0x446>
    468e:	lea    0x270(%r14),%r15
    4695:	xor    %esi,%esi
    4697:	mov    $0x6c,%edx
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_readDTableX4_wksp_func_pgot, 469f, pgot_memset_table_func_pgot

```asm
    4697:	mov    $0x6c,%edx
    469c:	mov    0x0(%rip),%rax        # 46a3 <pgot_HUF_readDTableX4_wksp_func_pgot+0x93>
			469f: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    46a3:	mov    %r15,%rdi
    46a6:	jmp    46ba <pgot_HUF_readDTableX4_wksp_func_pgot+0xaa>
    46a8:	call   46b4 <pgot_HUF_readDTableX4_wksp_func_pgot+0xa4>
    46ad:	pause  
    46af:	lfence 
    46b2:	jmp    46ad <pgot_HUF_readDTableX4_wksp_func_pgot+0x9d>
    46b4:	mov    %rax,(%rsp)
    46b8:	ret    
    46b9:	int3   
    46ba:	call   46a8 <pgot_HUF_readDTableX4_wksp_func_pgot+0x98>
    46bf:	cmp    $0xc,%r12d
    46c3:	ja     4a56 <pgot_HUF_readDTableX4_wksp_func_pgot+0x446>
    46c9:	mov    %r13,%r9
    46cc:	lea    -0x70(%rbp),%r8
    46d0:	lea    -0x6c(%rbp),%rcx
    46d4:	mov    %r15,%rdx
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_readDTableX4_wksp_func_pgot, 48c6, pgot_memcpy_table_func_pgot

```asm
    48bd:	mov    %eax,-0xb8(%rbp)
    48c3:	mov    0x0(%rip),%rax        # 48ca <pgot_HUF_readDTableX4_wksp_func_pgot+0x2ba>
			48c6: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    48ca:	jmp    48de <pgot_HUF_readDTableX4_wksp_func_pgot+0x2ce>
    48cc:	call   48d8 <pgot_HUF_readDTableX4_wksp_func_pgot+0x2c8>
    48d1:	pause  
    48d3:	lfence 
    48d6:	jmp    48d1 <pgot_HUF_readDTableX4_wksp_func_pgot+0x2c1>
    48d8:	mov    %rax,(%rsp)
    48dc:	ret    
    48dd:	int3   
    48de:	call   48cc <pgot_HUF_readDTableX4_wksp_func_pgot+0x2bc>
    48e3:	mov    -0x84(%rbp),%r10d
    48ea:	test   %r10d,%r10d
    48ed:	je     4a8b <pgot_HUF_readDTableX4_wksp_func_pgot+0x47b>
    48f3:	lea    -0x1(%r10),%eax
    48f7:	sub    %ebx,%r12d
    48fa:	mov    %r14,%r11
    48fd:	mov    %r10d,-0xbc(%rbp)
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_readDTableX4_wksp_func_pgot, 4aa9, pgot_memcpy_table_func_pgot

```asm
    4aa3:	mov    %al,-0x66(%rbp)
    4aa6:	mov    0x0(%rip),%rax        # 4aad <pgot_HUF_readDTableX4_wksp_func_pgot+0x49d>
			4aa9: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4aad:	jmp    4ac1 <pgot_HUF_readDTableX4_wksp_func_pgot+0x4b1>
    4aaf:	call   4abb <pgot_HUF_readDTableX4_wksp_func_pgot+0x4ab>
    4ab4:	pause  
    4ab6:	lfence 
    4ab9:	jmp    4ab4 <pgot_HUF_readDTableX4_wksp_func_pgot+0x4a4>
    4abb:	mov    %rax,(%rsp)
    4abf:	ret    
    4ac0:	int3   
    4ac1:	call   4aaf <pgot_HUF_readDTableX4_wksp_func_pgot+0x49f>
    4ac6:	jmp    4a61 <pgot_HUF_readDTableX4_wksp_func_pgot+0x451>
    4ac8:	lea    0x1(%r11),%r8d
    4acc:	mov    %r11d,%eax
    4acf:	jmp    4749 <pgot_HUF_readDTableX4_wksp_func_pgot+0x139>
    4ad4:	mov    -0x6c(%rbp),%ebx
    4ad7:	lea    0x2dc(%r14),%rsi
    4ade:	xor    %r10d,%r10d
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_decompress1X4_usingDTable_func_pgot, 4bd3, pgot_memcpy_table_func_pgot

```asm
    4bce:	xor    %eax,%eax
    4bd0:	mov    0x0(%rip),%rax        # 4bd7 <pgot_HUF_decompress1X4_usingDTable_func_pgot+0x47>
			4bd3: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4bd7:	jmp    4beb <pgot_HUF_decompress1X4_usingDTable_func_pgot+0x5b>
    4bd9:	call   4be5 <pgot_HUF_decompress1X4_usingDTable_func_pgot+0x55>
    4bde:	pause  
    4be0:	lfence 
    4be3:	jmp    4bde <pgot_HUF_decompress1X4_usingDTable_func_pgot+0x4e>
    4be5:	mov    %rax,(%rsp)
    4be9:	ret    
    4bea:	int3   
    4beb:	call   4bd9 <pgot_HUF_decompress1X4_usingDTable_func_pgot+0x49>
    4bf0:	cmpb   $0x1,-0x33(%rbp)
    4bf4:	mov    $0xffffffffffffffff,%rax
    4bfb:	jne    4c11 <pgot_HUF_decompress1X4_usingDTable_func_pgot+0x81>
    4bfd:	mov    %rbx,%r8
    4c00:	mov    %r15,%rcx
    4c03:	mov    %r14,%rdx
    4c06:	mov    %r13,%rsi
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_decompress4X4_usingDTable_func_pgot, 4d13, pgot_memcpy_table_func_pgot

```asm
    4d0e:	xor    %eax,%eax
    4d10:	mov    0x0(%rip),%rax        # 4d17 <pgot_HUF_decompress4X4_usingDTable_func_pgot+0x47>
			4d13: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4d17:	jmp    4d2b <pgot_HUF_decompress4X4_usingDTable_func_pgot+0x5b>
    4d19:	call   4d25 <pgot_HUF_decompress4X4_usingDTable_func_pgot+0x55>
    4d1e:	pause  
    4d20:	lfence 
    4d23:	jmp    4d1e <pgot_HUF_decompress4X4_usingDTable_func_pgot+0x4e>
    4d25:	mov    %rax,(%rsp)
    4d29:	ret    
    4d2a:	int3   
    4d2b:	call   4d19 <pgot_HUF_decompress4X4_usingDTable_func_pgot+0x49>
    4d30:	cmpb   $0x1,-0x33(%rbp)
    4d34:	mov    $0xffffffffffffffff,%rax
    4d3b:	jne    4d51 <pgot_HUF_decompress4X4_usingDTable_func_pgot+0x81>
    4d3d:	mov    %rbx,%r8
    4d40:	mov    %r15,%rcx
    4d43:	mov    %r14,%rdx
    4d46:	mov    %r13,%rsi
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_decompress1X_usingDTable_func_pgot, 4e53, pgot_memcpy_table_func_pgot

```asm
    4e4e:	xor    %eax,%eax
    4e50:	mov    0x0(%rip),%rax        # 4e57 <pgot_HUF_decompress1X_usingDTable_func_pgot+0x47>
			4e53: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4e57:	jmp    4e6b <pgot_HUF_decompress1X_usingDTable_func_pgot+0x5b>
    4e59:	call   4e65 <pgot_HUF_decompress1X_usingDTable_func_pgot+0x55>
    4e5e:	pause  
    4e60:	lfence 
    4e63:	jmp    4e5e <pgot_HUF_decompress1X_usingDTable_func_pgot+0x4e>
    4e65:	mov    %rax,(%rsp)
    4e69:	ret    
    4e6a:	int3   
    4e6b:	call   4e59 <pgot_HUF_decompress1X_usingDTable_func_pgot+0x49>
    4e70:	cmpb   $0x0,-0x33(%rbp)
    4e74:	mov    %rbx,%r8
    4e77:	mov    %r15,%rcx
    4e7a:	mov    %r14,%rdx
    4e7d:	mov    %r13,%rsi
    4e80:	mov    %r12,%rdi
    4e83:	je     4ea9 <pgot_HUF_decompress1X_usingDTable_func_pgot+0x99>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_decompress4X_usingDTable_func_pgot, 4f03, pgot_memcpy_table_func_pgot

```asm
    4efe:	xor    %eax,%eax
    4f00:	mov    0x0(%rip),%rax        # 4f07 <pgot_HUF_decompress4X_usingDTable_func_pgot+0x47>
			4f03: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    4f07:	jmp    4f1b <pgot_HUF_decompress4X_usingDTable_func_pgot+0x5b>
    4f09:	call   4f15 <pgot_HUF_decompress4X_usingDTable_func_pgot+0x55>
    4f0e:	pause  
    4f10:	lfence 
    4f13:	jmp    4f0e <pgot_HUF_decompress4X_usingDTable_func_pgot+0x4e>
    4f15:	mov    %rax,(%rsp)
    4f19:	ret    
    4f1a:	int3   
    4f1b:	call   4f09 <pgot_HUF_decompress4X_usingDTable_func_pgot+0x49>
    4f20:	cmpb   $0x0,-0x33(%rbp)
    4f24:	mov    %rbx,%r8
    4f27:	mov    %r15,%rcx
    4f2a:	mov    %r14,%rdx
    4f2d:	mov    %r13,%rsi
    4f30:	mov    %r12,%rdi
    4f33:	je     4f59 <pgot_HUF_decompress4X_usingDTable_func_pgot+0x99>
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_decompress4X_DCtx_wksp_func_pgot, 51c8, pgot_memcpy_table_func_pgot

```asm
    51c3:	jmp    517b <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x12b>
    51c5:	mov    0x0(%rip),%rax        # 51cc <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x17c>
			51c8: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    51cc:	mov    %rcx,%rsi
    51cf:	mov    %r10,%rdi
    51d2:	mov    %r12,%r13
    51d5:	jmp    51e9 <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x199>
    51d7:	call   51e3 <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x193>
    51dc:	pause  
    51de:	lfence 
    51e1:	jmp    51dc <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x18c>
    51e3:	mov    %rax,(%rsp)
    51e7:	ret    
    51e8:	int3   
    51e9:	call   51d7 <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x187>
    51ee:	jmp    517b <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x12b>
    51f0:	movzbl (%rcx),%esi
    51f3:	mov    0x0(%rip),%rax        # 51fa <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x1aa>
			51f6: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_decompress4X_DCtx_wksp_func_pgot, 51f6, pgot_memset_table_func_pgot

```asm
    51f0:	movzbl (%rcx),%esi
    51f3:	mov    0x0(%rip),%rax        # 51fa <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x1aa>
			51f6: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    51fa:	mov    %r10,%rdi
    51fd:	mov    %r12,%r13
    5200:	jmp    5214 <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x1c4>
    5202:	call   520e <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x1be>
    5207:	pause  
    5209:	lfence 
    520c:	jmp    5207 <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x1b7>
    520e:	mov    %rax,(%rsp)
    5212:	ret    
    5213:	int3   
    5214:	call   5202 <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x1b2>
    5219:	jmp    517b <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x12b>
    521e:	mov    $0xfffffffffffffff3,%r13
    5225:	jmp    517b <pgot_HUF_decompress4X_DCtx_wksp_func_pgot+0x12b>
    522a:	mov    %r13,%rsi
    522d:	mov    $0x0,%rdi
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_decompress1X_DCtx_wksp_func_pgot, 56c8, pgot_memcpy_table_func_pgot

```asm
    56c3:	jmp    567b <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x12b>
    56c5:	mov    0x0(%rip),%rax        # 56cc <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x17c>
			56c8: R_X86_64_PC32	pgot_memcpy_table_func_pgot-0x4
    56cc:	mov    %rcx,%rsi
    56cf:	mov    %r10,%rdi
    56d2:	mov    %r12,%r13
    56d5:	jmp    56e9 <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x199>
    56d7:	call   56e3 <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x193>
    56dc:	pause  
    56de:	lfence 
    56e1:	jmp    56dc <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x18c>
    56e3:	mov    %rax,(%rsp)
    56e7:	ret    
    56e8:	int3   
    56e9:	call   56d7 <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x187>
    56ee:	jmp    567b <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x12b>
    56f0:	movzbl (%rcx),%esi
    56f3:	mov    0x0(%rip),%rax        # 56fa <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x1aa>
			56f6: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
```

## 04_zstd_decompress/retpoline/func_pgot: pgot_HUF_decompress1X_DCtx_wksp_func_pgot, 56f6, pgot_memset_table_func_pgot

```asm
    56f0:	movzbl (%rcx),%esi
    56f3:	mov    0x0(%rip),%rax        # 56fa <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x1aa>
			56f6: R_X86_64_PC32	pgot_memset_table_func_pgot-0x4
    56fa:	mov    %r10,%rdi
    56fd:	mov    %r12,%r13
    5700:	jmp    5714 <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x1c4>
    5702:	call   570e <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x1be>
    5707:	pause  
    5709:	lfence 
    570c:	jmp    5707 <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x1b7>
    570e:	mov    %rax,(%rsp)
    5712:	ret    
    5713:	int3   
    5714:	call   5702 <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x1b2>
    5719:	jmp    567b <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x12b>
    571e:	mov    $0xfffffffffffffff3,%r13
    5725:	jmp    567b <pgot_HUF_decompress1X_DCtx_wksp_func_pgot+0x12b>
    572a:	mov    %r13,%rsi
    572d:	mov    $0x0,%rdi
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_execSequenceLast7_origin.isra.0, 5e6, memmove

```asm
     5e2:	mov    %r13,%rdx
     5e5:	call   5ea <pgot_ZSTD_execSequenceLast7_origin.isra.0+0xea>
			5e6: R_X86_64_PLT32	memmove-0x4
     5ea:	mov    0x18(%rbp),%rsi
     5ee:	lea    (%rax,%r13,1),%rax
     5f2:	cmp    %rax,%rbx
     5f5:	jbe    61e <pgot_ZSTD_execSequenceLast7_origin.isra.0+0x11e>
     5f7:	sub    %rax,%rbx
     5fa:	xor    %edx,%edx
     5fc:	movzbl (%rsi,%rdx,1),%ecx
     600:	mov    %cl,(%rax,%rdx,1)
     603:	add    $0x1,%rdx
     607:	cmp    %rbx,%rdx
     60a:	jne    5fc <pgot_ZSTD_execSequenceLast7_origin.isra.0+0xfc>
     60c:	pop    %rbx
     60d:	mov    %r12,%rax
     610:	pop    %r12
     612:	pop    %r13
     614:	pop    %rbp
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_execSequenceLast7_origin.isra.0, 65f, memmove

```asm
     65b:	mov    %r10,%rdx
     65e:	call   663 <pgot_ZSTD_execSequenceLast7_origin.isra.0+0x163>
			65f: R_X86_64_PLT32	memmove-0x4
     663:	jmp    61e <pgot_ZSTD_execSequenceLast7_origin.isra.0+0x11e>
     665:	data16 cs nopw 0x0(%rax,%rax,1)

```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_copyDCtx_origin, def, memcpy

```asm
     deb:	mov    %rsp,%rbp
     dee:	call   df3 <pgot_ZSTD_copyDCtx_origin+0x13>
			def: R_X86_64_PLT32	memcpy-0x4
     df3:	pop    %rbp
     df4:	ret    
     df5:	int3   
     df6:	cs nopw 0x0(%rax,%rax,1)

```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_decodeLiteralsBlock_origin, 1282, memcpy

```asm
    127e:	mov    %rcx,%rdi
    1281:	call   1286 <pgot_ZSTD_decodeLiteralsBlock_origin+0x96>
			1282: R_X86_64_PLT32	memcpy-0x4
    1286:	mov    %rbx,0x6110(%r12)
    128e:	mov    %rax,0x60f0(%r12)
    1296:	movq   $0x0,(%rax,%rbx,1)
    129e:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_origin+0x104>
    12a0:	mov    0x6088(%r12),%esi
    12a8:	mov    $0xffffffffffffffed,%r13
    12af:	test   %esi,%esi
    12b1:	je     12f4 <pgot_ZSTD_decodeLiteralsBlock_origin+0x104>
    12b3:	cmp    $0x4,%rdx
    12b7:	jbe    12ed <pgot_ZSTD_decodeLiteralsBlock_origin+0xfd>
    12b9:	mov    (%rdi),%r8d
    12bc:	shr    $0x2,%al
    12bf:	and    $0x3,%eax
    12c2:	mov    %r8d,%ecx
    12c5:	shr    $0x4,%ecx
    12c8:	cmp    $0x2,%al
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_decodeLiteralsBlock_origin, 1427, memset

```asm
    1423:	mov    %rcx,%rdi
    1426:	call   142b <pgot_ZSTD_decodeLiteralsBlock_origin+0x23b>
			1427: R_X86_64_PLT32	memset-0x4
    142b:	mov    %rbx,0x6110(%r12)
    1433:	mov    %rax,0x60f0(%r12)
    143b:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_origin+0x104>
    1440:	add    %rdi,%rsi
    1443:	mov    %rbx,0x6110(%r12)
    144b:	mov    %rsi,0x60f0(%r12)
    1453:	jmp    12f4 <pgot_ZSTD_decodeLiteralsBlock_origin+0x104>
    1458:	movzbl 0x2(%rsi),%ebx
    145c:	movzwl (%rsi),%eax
    145f:	mov    $0x3,%esi
    1464:	shl    $0x10,%ebx
    1467:	add    %eax,%ebx
    1469:	shr    $0x4,%ebx
    146c:	jmp    125a <pgot_ZSTD_decodeLiteralsBlock_origin+0x6a>
    1471:	movzbl 0x2(%rsi),%ebx
    1475:	movzwl (%rsi),%eax
```

## 04_zstd_decompress/retpoline/origin: ZSTD_decompressSequencesLong, 1854, memcpy

```asm
    1850:	mov    %r11,%rdi
    1853:	call   1858 <ZSTD_decompressSequencesLong+0x118>
			1854: R_X86_64_PLT32	memcpy-0x4
    1858:	add    %rax,%rbx
    185b:	sub    -0x118(%rbp),%rbx
    1862:	mov    %rbx,%r12
    1865:	mov    -0x38(%rbp),%rax
    1869:	sub    %gs:0x28,%rax
    1872:	jne    24ab <ZSTD_decompressSequencesLong+0xd6b>
    1878:	lea    -0x30(%rbp),%rsp
    187c:	mov    %r12,%rax
    187f:	pop    %rbx
    1880:	pop    %r10
    1882:	pop    %r12
    1884:	pop    %r13
    1886:	pop    %r14
    1888:	pop    %r15
    188a:	pop    %rbp
    188b:	lea    -0x8(%r10),%rsp
```

## 04_zstd_decompress/retpoline/origin: ZSTD_decompressSequencesLong, 1d5a, memmove

```asm
    1d52:	mov    %r10,-0x158(%rbp)
    1d59:	call   1d5e <ZSTD_decompressSequencesLong+0x61e>
			1d5a: R_X86_64_PLT32	memmove-0x4
    1d5e:	mov    -0x140(%rbp),%rdx
    1d65:	mov    -0x170(%rbp),%r11
    1d6c:	mov    %rax,%rdi
    1d6f:	mov    -0x178(%rbp),%r9
    1d76:	sub    %rdx,%r11
    1d79:	add    %rdx,%rdi
    1d7c:	cmp    $0x2,%r11
    1d80:	jbe    2464 <ZSTD_decompressSequencesLong+0xd24>
    1d86:	cmp    %r13,%rdi
    1d89:	mov    -0x158(%rbp),%r10
    1d90:	mov    -0x160(%rbp),%r8
    1d97:	mov    %r14,%rsi
    1d9a:	ja     2464 <ZSTD_decompressSequencesLong+0xd24>
    1da0:	cmp    $0x7,%r10
    1da4:	ja     2400 <ZSTD_decompressSequencesLong+0xcc0>
    1daa:	movzbl (%rsi),%eax
```

## 04_zstd_decompress/retpoline/origin: ZSTD_decompressSequencesLong, 200e, memmove

```asm
    2006:	mov    %r8,-0x180(%rbp)
    200d:	call   2012 <ZSTD_decompressSequencesLong+0x8d2>
			200e: R_X86_64_PLT32	memmove-0x4
    2012:	mov    -0x170(%rbp),%rcx
    2019:	mov    -0x158(%rbp),%r9
    2020:	mov    %rax,%rdi
    2023:	mov    -0x178(%rbp),%r10d
    202a:	add    %rbx,%rdi
    202d:	sub    %rbx,%rcx
    2030:	cmp    %rdi,%r9
    2033:	jb     204d <ZSTD_decompressSequencesLong+0x90d>
    2035:	cmp    $0x2,%rcx
    2039:	mov    -0x128(%rbp),%rsi
    2040:	mov    -0x180(%rbp),%r8
    2047:	ja     20d6 <ZSTD_decompressSequencesLong+0x996>
    204d:	test   %rcx,%rcx
    2050:	je     2071 <ZSTD_decompressSequencesLong+0x931>
    2052:	mov    -0x128(%rbp),%r8
    2059:	xor    %edx,%edx
```

## 04_zstd_decompress/retpoline/origin: ZSTD_decompressSequencesLong, 235a, memmove

```asm
    2352:	mov    %r10d,-0x158(%rbp)
    2359:	call   235e <ZSTD_decompressSequencesLong+0xc1e>
			235a: R_X86_64_PLT32	memmove-0x4
    235e:	mov    -0x158(%rbp),%r10d
    2365:	jmp    2071 <ZSTD_decompressSequencesLong+0x931>
    236a:	mov    %rbx,%r14
    236d:	mov    %r13,%r11
    2370:	mov    -0x160(%rbp),%rbx
    2377:	mov    %r10d,%r13d
    237a:	jmp    1c42 <ZSTD_decompressSequencesLong+0x502>
    237f:	push   -0x138(%rbp)
    2385:	mov    %r10,%r8
    2388:	mov    %r11,%rcx
    238b:	mov    %rbx,%rdi
    238e:	push   -0x148(%rbp)
    2394:	lea    -0xe0(%rbp),%r9
    239b:	mov    -0x130(%rbp),%rsi
    23a2:	push   %r14
    23a4:	push   -0x120(%rbp)
```

## 04_zstd_decompress/retpoline/origin: ZSTD_decompressSequencesLong, 249b, memmove

```asm
    2493:	mov    %r9,-0x140(%rbp)
    249a:	call   249f <ZSTD_decompressSequencesLong+0xd5f>
			249b: R_X86_64_PLT32	memmove-0x4
    249f:	mov    -0x140(%rbp),%r9
    24a6:	jmp    1e28 <ZSTD_decompressSequencesLong+0x6e8>
    24ab:	call   24b0 <ZSTD_decompressSequencesLong+0xd70>
			24ac: R_X86_64_PLT32	__stack_chk_fail-0x4
    24b0:	mov    -0xe0(%rbp),%rax
    24b7:	mov    -0x68(%rbp),%rdx
    24bb:	mov    %rax,%r14
    24be:	mov    %edx,0x6030(%rbx)
    24c4:	mov    -0x60(%rbp),%rdx
    24c8:	mov    %edx,0x6034(%rbx)
    24ce:	mov    -0x58(%rbp),%rdx
    24d2:	mov    %edx,0x6038(%rbx)
    24d8:	jmp    182a <ZSTD_decompressSequencesLong+0xea>
    24dd:	mov    %rbx,%r11
    24e0:	mov    -0x128(%rbp),%rbx
    24e7:	jmp    24b7 <ZSTD_decompressSequencesLong+0xd77>
```

## 04_zstd_decompress/retpoline/origin: ZSTD_decompressSequences, 2601, memcpy

```asm
    25fd:	mov    %r13,%rdi
    2600:	call   2605 <ZSTD_decompressSequences+0x105>
			2601: R_X86_64_PLT32	memcpy-0x4
    2605:	lea    0x0(%r13,%rbx,1),%rax
    260a:	sub    -0xd0(%rbp),%rax
    2611:	mov    %rax,%r14
    2614:	mov    -0x30(%rbp),%rax
    2618:	sub    %gs:0x28,%rax
    2621:	jne    3015 <ZSTD_decompressSequences+0xb15>
    2627:	lea    -0x28(%rbp),%rsp
    262b:	mov    %r14,%rax
    262e:	pop    %rbx
    262f:	pop    %r12
    2631:	pop    %r13
    2633:	pop    %r14
    2635:	pop    %r15
    2637:	pop    %rbp
    2638:	ret    
    2639:	int3   
```

## 04_zstd_decompress/retpoline/origin: ZSTD_decompressSequences, 2b82, memmove

```asm
    2b7a:	mov    %rdx,-0xc8(%rbp)
    2b81:	call   2b86 <ZSTD_decompressSequences+0x686>
			2b82: R_X86_64_PLT32	memmove-0x4
    2b86:	mov    -0xc8(%rbp),%rdx
    2b8d:	mov    -0x110(%rbp),%rcx
    2b94:	mov    %rax,%rdi
    2b97:	add    %rdx,%rdi
    2b9a:	add    %rcx,%r12
    2b9d:	cmp    %rdi,%r15
    2ba0:	jb     2bb3 <ZSTD_decompressSequences+0x6b3>
    2ba2:	mov    -0xf0(%rbp),%rcx
    2ba9:	cmp    $0x2,%r12
    2bad:	ja     2cee <ZSTD_decompressSequences+0x7ee>
    2bb3:	test   %r12,%r12
    2bb6:	je     2d8f <ZSTD_decompressSequences+0x88f>
    2bbc:	mov    -0xf0(%rbp),%rsi
    2bc3:	xor    %edx,%edx
    2bc5:	xor    %eax,%eax
    2bc7:	movzbl (%rsi,%rax,1),%ecx
```

## 04_zstd_decompress/retpoline/origin: ZSTD_decompressSequences, 2e98, memmove

```asm
    2e94:	mov    %r12,%rdx
    2e97:	call   2e9c <ZSTD_decompressSequences+0x99c>
			2e98: R_X86_64_PLT32	memmove-0x4
    2e9c:	jmp    2d8f <ZSTD_decompressSequences+0x88f>
    2ea1:	mov    -0x58(%rbp),%rcx
    2ea5:	cmp    $0x1,%rcx
    2ea9:	adc    $0x0,%rcx
    2ead:	mov    %rcx,-0x108(%rbp)
    2eb4:	mov    %esi,%ebx
    2eb6:	mov    -0x118(%rbp),%rdi
    2ebd:	mov    %rdi,-0x58(%rbp)
    2ec1:	mov    -0x108(%rbp),%rdi
    2ec8:	mov    %rdi,-0x60(%rbp)
    2ecc:	jmp    299c <ZSTD_decompressSequences+0x49c>
    2ed1:	mov    -0xc8(%rbp),%rcx
    2ed8:	mov    -0xe0(%rbp),%rdx
    2edf:	add    $0x8,%rcx
    2ee3:	add    $0x8,%rdx
    2ee7:	mov    (%rcx),%rsi
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_generateNxBytes_origin, 33e9, memset

```asm
    33e5:	mov    %rcx,%rbx
    33e8:	call   33ed <pgot_ZSTD_generateNxBytes_origin+0x1d>
			33e9: R_X86_64_PLT32	memset-0x4
    33ed:	mov    %rbx,%rax
    33f0:	mov    -0x8(%rbp),%rbx
    33f4:	leave  
    33f5:	ret    
    33f6:	int3   
    33f7:	mov    $0xfffffffffffffff4,%rax
    33fe:	ret    
    33ff:	int3   

```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_decompressContinue_origin, 3963, memcpy

```asm
    395f:	xor    %r12d,%r12d
    3962:	call   3967 <pgot_ZSTD_decompressContinue_origin+0x247>
			3963: R_X86_64_PLT32	memcpy-0x4
    3967:	mov    0x2612c(%rbx),%eax
    396d:	movl   $0x7,0x6084(%rbx)
    3977:	mov    %rax,0x6060(%rbx)
    397e:	jmp    381f <pgot_ZSTD_decompressContinue_origin+0xff>
    3983:	lea    0x26128(%rbx),%r13
    398a:	mov    %r8,%rdx
    398d:	mov    %rcx,%rsi
    3990:	lea    0x2612d(%rbx),%rdi
    3997:	call   399c <pgot_ZSTD_decompressContinue_origin+0x27c>
			3998: R_X86_64_PLT32	memcpy-0x4
    399c:	mov    0x60e0(%rbx),%rdx
    39a3:	mov    %r13,%rsi
    39a6:	mov    %rbx,%rdi
    39a9:	call   10a0 <ZSTD_decodeFrameHeader>
    39ae:	mov    %rax,%r12
    39b1:	cmp    $0xffffffffffffffea,%rax
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_decompressContinue_origin, 3998, memcpy

```asm
    3990:	lea    0x2612d(%rbx),%rdi
    3997:	call   399c <pgot_ZSTD_decompressContinue_origin+0x27c>
			3998: R_X86_64_PLT32	memcpy-0x4
    399c:	mov    0x60e0(%rbx),%rdx
    39a3:	mov    %r13,%rsi
    39a6:	mov    %rbx,%rdi
    39a9:	call   10a0 <ZSTD_decodeFrameHeader>
    39ae:	mov    %rax,%r12
    39b1:	cmp    $0xffffffffffffffea,%rax
    39b5:	ja     381f <pgot_ZSTD_decompressContinue_origin+0xff>
    39bb:	movq   $0x3,0x6060(%rbx)
    39c6:	xor    %r12d,%r12d
    39c9:	movl   $0x2,0x6084(%rbx)
    39d3:	jmp    381f <pgot_ZSTD_decompressContinue_origin+0xff>
    39d8:	mov    0x6080(%rbx),%eax
    39de:	cmp    $0x1,%eax
    39e1:	je     3a73 <pgot_ZSTD_decompressContinue_origin+0x353>
    39e7:	cmp    $0x2,%eax
    39ea:	je     3b08 <pgot_ZSTD_decompressContinue_origin+0x3e8>
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_decompressContinue_origin, 3a97, memset

```asm
    3a93:	mov    %r13,%rdi
    3a96:	call   3a9b <pgot_ZSTD_decompressContinue_origin+0x37b>
			3a97: R_X86_64_PLT32	memset-0x4
    3a9b:	cmp    $0xffffffffffffffea,%r12
    3a9f:	ja     381f <pgot_ZSTD_decompressContinue_origin+0xff>
    3aa5:	mov    0x6078(%rbx),%edx
    3aab:	test   %edx,%edx
    3aad:	jne    3b28 <pgot_ZSTD_decompressContinue_origin+0x408>
    3aaf:	cmpl   $0x4,0x6084(%rbx)
    3ab6:	je     3b88 <pgot_ZSTD_decompressContinue_origin+0x468>
    3abc:	movl   $0x2,0x6084(%rbx)
    3ac6:	add    %r12,%r13
    3ac9:	movq   $0x3,0x6060(%rbx)
    3ad4:	mov    %r13,0x6040(%rbx)
    3adb:	jmp    381f <pgot_ZSTD_decompressContinue_origin+0xff>
    3ae0:	mov    $0xfffffffffffffff4,%r12
    3ae7:	cmp    %rdx,%r8
    3aea:	ja     381f <pgot_ZSTD_decompressContinue_origin+0xff>
    3af0:	mov    %r8,%rdx
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_decompressContinue_origin, 3afe, memcpy

```asm
    3af9:	mov    %r8,-0x30(%rbp)
    3afd:	call   3b02 <pgot_ZSTD_decompressContinue_origin+0x3e2>
			3afe: R_X86_64_PLT32	memcpy-0x4
    3b02:	mov    -0x30(%rbp),%r12
    3b06:	jmp    3a9b <pgot_ZSTD_decompressContinue_origin+0x37b>
    3b08:	cmp    $0x1ffff,%r8
    3b0f:	ja     393a <pgot_ZSTD_decompressContinue_origin+0x21a>
    3b15:	mov    %r13,%rsi
    3b18:	mov    %rbx,%rdi
    3b1b:	call   3290 <ZSTD_decompressBlock_internal.part.0>
    3b20:	mov    %rax,%r12
    3b23:	jmp    3a9b <pgot_ZSTD_decompressContinue_origin+0x37b>
    3b28:	lea    0x6090(%rbx),%rdi
    3b2f:	mov    %r12,%rdx
    3b32:	mov    %r13,%rsi
    3b35:	call   3b3a <pgot_ZSTD_decompressContinue_origin+0x41a>
			3b36: R_X86_64_PLT32	xxh64_update-0x4
    3b3a:	cmpl   $0x4,0x6084(%rbx)
    3b41:	jne    3abc <pgot_ZSTD_decompressContinue_origin+0x39c>
```

## 04_zstd_decompress/retpoline/origin: ZSTD_decompressMultiFrame, 3dc8, memcpy

```asm
    3dc3:	mov    %r8,-0x58(%rbp)
    3dc7:	call   3dcc <ZSTD_decompressMultiFrame+0xec>
			3dc8: R_X86_64_PLT32	memcpy-0x4
    3dcc:	mov    -0x58(%rbp),%r8
    3dd0:	mov    %r8,%r15
    3dd3:	mov    0x6078(%r13),%ecx
    3dda:	test   %ecx,%ecx
    3ddc:	jne    3fd9 <ZSTD_decompressMultiFrame+0x2f9>
    3de2:	mov    -0x48(%rbp),%edx
    3de5:	sub    %r8,%r14
    3de8:	add    %r15,%rbx
    3deb:	lea    (%r12,%r8,1),%r11
    3def:	mov    %r14,%r9
    3df2:	test   %edx,%edx
    3df4:	jne    404b <ZSTD_decompressMultiFrame+0x36b>
    3dfa:	cmp    $0x2,%r14
    3dfe:	ja     3f12 <ZSTD_decompressMultiFrame+0x232>
    3e04:	mov    $0xfffffffffffffff3,%r15
    3e0b:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
```

## 04_zstd_decompress/retpoline/origin: ZSTD_decompressMultiFrame, 4024, memset

```asm
    4020:	mov    %rbx,%rdi
    4023:	call   4028 <ZSTD_decompressMultiFrame+0x348>
			4024: R_X86_64_PLT32	memset-0x4
    4028:	mov    $0x1,%r8d
    402e:	jmp    3dd3 <ZSTD_decompressMultiFrame+0xf3>
    4033:	mov    $0xfffffffffffffff4,%r15
    403a:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
    403f:	mov    $0xfffffffffffffffe,%r15
    4046:	jmp    3d97 <ZSTD_decompressMultiFrame+0xb7>
    404b:	mov    0x6078(%r13),%eax
    4052:	mov    %rbx,%r15
    4055:	mov    -0x60(%rbp),%r14
    4059:	mov    %r9,%rbx
    405c:	test   %eax,%eax
    405e:	jne    407c <ZSTD_decompressMultiFrame+0x39c>
    4060:	mov    %r15,%r12
    4063:	sub    %r14,%r12
    4066:	cmp    $0xffffffffffffffea,%r12
    406a:	ja     3f8d <ZSTD_decompressMultiFrame+0x2ad>
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_decompressStream_origin, 4855, memcpy

```asm
    4850:	mov    %rcx,-0x40(%rbp)
    4854:	call   4859 <pgot_ZSTD_decompressStream_origin+0xd9>
			4855: R_X86_64_PLT32	memcpy-0x4
    4859:	mov    -0x40(%rbp),%rcx
    485d:	mov    0x30(%rbx),%eax
    4860:	mov    %r15,0x98(%rbx)
    4867:	add    %rcx,%r12
    486a:	cmp    $0x2,%eax
    486d:	jne    47ef <pgot_ZSTD_decompressStream_origin+0x6f>
    486f:	mov    (%rbx),%rdi
    4872:	mov    0x6060(%rdi),%r8
    4879:	test   %r8,%r8
    487c:	jne    4b3e <pgot_ZSTD_decompressStream_origin+0x3be>
    4882:	movl   $0x0,0x30(%rbx)
    4889:	mov    -0x68(%rbp),%rax
    488d:	mov    -0x58(%rbp),%rsi
    4891:	sub    -0x50(%rbp),%r12
    4895:	sub    -0x60(%rbp),%r13
    4899:	add    %r12,0x10(%rsi)
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_decompressStream_origin, 4923, memcpy

```asm
    491e:	mov    %rdx,-0x40(%rbp)
    4922:	call   4927 <pgot_ZSTD_decompressStream_origin+0x1a7>
			4923: R_X86_64_PLT32	memcpy-0x4
    4927:	mov    -0x40(%rbp),%rdx
    492b:	mov    -0x48(%rbp),%rcx
    492f:	add    %rdx,%r13
    4932:	add    0x68(%rbx),%rdx
    4936:	mov    %rdx,0x68(%rbx)
    493a:	cmp    %r15,%rcx
    493d:	jb     4889 <pgot_ZSTD_decompressStream_origin+0x109>
    4943:	movl   $0x2,0x30(%rbx)
    494a:	add    0x78(%rbx),%rdx
    494e:	cmp    0x60(%rbx),%rdx
    4952:	jbe    47e3 <pgot_ZSTD_decompressStream_origin+0x63>
    4958:	movq   $0x0,0x70(%rbx)
    4960:	movq   $0x0,0x68(%rbx)
    4968:	jmp    47e3 <pgot_ZSTD_decompressStream_origin+0x63>
    496d:	movl   $0x1,0x30(%rbx)
    4974:	xor    %edx,%edx
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_decompressStream_origin, 49f1, memcpy

```asm
    49ed:	add    %r15,%r12
    49f0:	call   49f5 <pgot_ZSTD_decompressStream_origin+0x275>
			49f1: R_X86_64_PLT32	memcpy-0x4
    49f5:	mov    -0x48(%rbp),%rcx
    49f9:	add    %r15,0x48(%rbx)
    49fd:	mov    -0x40(%rbp),%r8
    4a01:	cmp    %r15,%rcx
    4a04:	ja     4889 <pgot_ZSTD_decompressStream_origin+0x109>
    4a0a:	mov    (%rbx),%rdi
    4a0d:	mov    0x68(%rbx),%rsi
    4a11:	mov    0x60(%rbx),%rdx
    4a15:	mov    0x38(%rbx),%rcx
    4a19:	mov    0x6084(%rdi),%eax
    4a1f:	sub    %rsi,%rdx
    4a22:	add    0x58(%rbx),%rsi
    4a26:	mov    %eax,-0x40(%rbp)
    4a29:	call   4a2e <pgot_ZSTD_decompressStream_origin+0x2ae>
			4a2a: R_X86_64_PLT32	pgot_ZSTD_decompressContinue_origin-0x4
    4a2e:	mov    %rax,%r15
```

## 04_zstd_decompress/retpoline/origin: pgot_ZSTD_decompressStream_origin, 4cfe, memcpy

```asm
    4cf9:	mov    %rax,-0x38(%rbp)
    4cfd:	call   4d02 <pgot_ZSTD_decompressStream_origin+0x582>
			4cfe: R_X86_64_PLT32	memcpy-0x4
    4d02:	mov    -0x58(%rbp),%rsi
    4d06:	mov    -0x30(%rbp),%rdx
    4d0a:	add    %rdx,0x98(%rbx)
    4d11:	mov    -0x38(%rbp),%r9
    4d15:	mov    $0x3,%edx
    4d1a:	mov    0x8(%rsi),%rax
    4d1e:	mov    %rax,0x10(%rsi)
    4d22:	mov    $0x6,%eax
    4d27:	sub    0x98(%rbx),%rdx
    4d2e:	cmp    %rax,%r9
    4d31:	cmovae %r9,%rax
    4d35:	lea    (%rdx,%rax,1),%r9
    4d39:	jmp    4c7d <pgot_ZSTD_decompressStream_origin+0x4fd>
    4d3e:	mov    $0xfffffffffffffff9,%r9
    4d45:	jmp    4c7d <pgot_ZSTD_decompressStream_origin+0x4fd>
    4d4a:	mov    -0x58(%rbp),%rsi
```

## 04_zstd_decompress/retpoline/origin: pgot_FSE_readNCount_origin, 279, memset

```asm
 274:	lea    (%rax,%r8,2),%rdi
 278:	call   27d <pgot_FSE_readNCount_origin+0x21d>
			279: R_X86_64_PLT32	memset-0x4
 27d:	mov    -0x4c(%rbp),%r8d
 281:	mov    -0x58(%rbp),%ecx
 284:	mov    %r13d,%eax
 287:	sar    $0x3,%eax
 28a:	cltq   
 28c:	add    %r12,%rax
 28f:	cmp    -0x40(%rbp),%r12
 293:	jbe    2a2 <pgot_FSE_readNCount_origin+0x242>
 295:	shr    $0x2,%ecx
 298:	cmp    -0x48(%rbp),%rax
 29c:	ja     195 <pgot_FSE_readNCount_origin+0x135>
 2a2:	mov    (%rax),%esi
 2a4:	and    $0x7,%r13d
 2a8:	mov    %rax,%r12
 2ab:	mov    %r13d,%ecx
 2ae:	shr    %cl,%esi
```

## 04_zstd_decompress/retpoline/origin: pgot_HUF_decompress4X_DCtx_wksp_origin, 42ff, memcpy

```asm
    42fb:	mov    %rcx,%rsi
    42fe:	call   4303 <pgot_HUF_decompress4X_DCtx_wksp_origin+0x123>
			42ff: R_X86_64_PLT32	memcpy-0x4
    4303:	lea    -0x28(%rbp),%rsp
    4307:	mov    %r12,%rax
    430a:	pop    %rbx
    430b:	pop    %r12
    430d:	pop    %r13
    430f:	pop    %r14
    4311:	pop    %r15
    4313:	pop    %rbp
    4314:	ret    
    4315:	int3   
    4316:	movzbl (%rcx),%esi
    4319:	mov    %r13,%rdi
    431c:	call   4321 <pgot_HUF_decompress4X_DCtx_wksp_origin+0x141>
			431d: R_X86_64_PLT32	memset-0x4
    4321:	lea    -0x28(%rbp),%rsp
    4325:	mov    %r12,%rax
```

## 04_zstd_decompress/retpoline/origin: pgot_HUF_decompress4X_DCtx_wksp_origin, 431d, memset

```asm
    4319:	mov    %r13,%rdi
    431c:	call   4321 <pgot_HUF_decompress4X_DCtx_wksp_origin+0x141>
			431d: R_X86_64_PLT32	memset-0x4
    4321:	lea    -0x28(%rbp),%rsp
    4325:	mov    %r12,%rax
    4328:	pop    %rbx
    4329:	pop    %r12
    432b:	pop    %r13
    432d:	pop    %r14
    432f:	pop    %r15
    4331:	pop    %rbp
    4332:	ret    
    4333:	int3   
    4334:	mov    %rbx,%rsi
    4337:	mov    $0x0,%rdi
			433a: R_X86_64_32S	.data+0x100
    433e:	mov    %r9,-0x50(%rbp)
    4342:	mov    %r8,-0x48(%rbp)
    4346:	mov    %rcx,-0x40(%rbp)
```

## 04_zstd_decompress/retpoline/origin: pgot_HUF_decompress1X_DCtx_wksp_origin, 476f, memcpy

```asm
    476b:	mov    %r12,%r13
    476e:	call   4773 <pgot_HUF_decompress1X_DCtx_wksp_origin+0x183>
			476f: R_X86_64_PLT32	memcpy-0x4
    4773:	jmp    471b <pgot_HUF_decompress1X_DCtx_wksp_origin+0x12b>
    4775:	movzbl (%rcx),%esi
    4778:	mov    %r10,%rdi
    477b:	mov    %r12,%r13
    477e:	call   4783 <pgot_HUF_decompress1X_DCtx_wksp_origin+0x193>
			477f: R_X86_64_PLT32	memset-0x4
    4783:	jmp    471b <pgot_HUF_decompress1X_DCtx_wksp_origin+0x12b>
    4785:	mov    $0xfffffffffffffff3,%r13
    478c:	jmp    471b <pgot_HUF_decompress1X_DCtx_wksp_origin+0x12b>
    478e:	mov    %r13,%rsi
    4791:	mov    $0x0,%rdi
			4794: R_X86_64_32S	.data
    4798:	mov    %rdx,-0x50(%rbp)
    479c:	mov    %r9,-0x48(%rbp)
    47a0:	mov    %r10,-0x40(%rbp)
    47a4:	mov    %r8d,-0x38(%rbp)
```

## 04_zstd_decompress/retpoline/origin: pgot_HUF_decompress1X_DCtx_wksp_origin, 477f, memset

```asm
    477b:	mov    %r12,%r13
    477e:	call   4783 <pgot_HUF_decompress1X_DCtx_wksp_origin+0x193>
			477f: R_X86_64_PLT32	memset-0x4
    4783:	jmp    471b <pgot_HUF_decompress1X_DCtx_wksp_origin+0x12b>
    4785:	mov    $0xfffffffffffffff3,%r13
    478c:	jmp    471b <pgot_HUF_decompress1X_DCtx_wksp_origin+0x12b>
    478e:	mov    %r13,%rsi
    4791:	mov    $0x0,%rdi
			4794: R_X86_64_32S	.data
    4798:	mov    %rdx,-0x50(%rbp)
    479c:	mov    %r9,-0x48(%rbp)
    47a0:	mov    %r10,-0x40(%rbp)
    47a4:	mov    %r8d,-0x38(%rbp)
    47a8:	mov    %eax,-0x30(%rbp)
    47ab:	call   47b0 <pgot_HUF_decompress1X_DCtx_wksp_origin+0x1c0>
			47ac: R_X86_64_PLT32	__ubsan_handle_out_of_bounds-0x4
    47b0:	mov    -0x50(%rbp),%rdx
    47b4:	mov    -0x48(%rbp),%r9
    47b8:	mov    -0x40(%rbp),%r10
```
