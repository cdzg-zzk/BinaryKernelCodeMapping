
/home/zzk/BinaryKernelCodeMapping/test/test_BCH/kmod/vkso_bch.ko:     file format elf64-x86-64


Disassembly of section .text:

00000000000000d0 <load_ecc8>:
      d0:	55                   	push   rbp	64: R_X86_64_PC32	.rodata+0x3c
      d1:	48 89 e5             	mov    rbp,rsp
      d4:	41 56                	push   r14
      d6:	41 55                	push   r13
      d8:	49 89 f5             	mov    r13,rsi
      db:	48 89 d6             	mov    rsi,rdx
      de:	41 54                	push   r12
      e0:	53                   	push   rbx
      e1:	48 89 fb             	mov    rbx,rdi
      e4:	48 83 ec 08          	sub    rsp,0x8
      e8:	8b 07                	mov    eax,DWORD PTR [rdi]
      ea:	0f af 47 08          	imul   eax,DWORD PTR [rdi+0x8]
      ee:	c7 45 dc 00 00 00 00 	mov    DWORD PTR [rbp-0x24],0x0
      f5:	8d 50 1f             	lea    edx,[rax+0x1f]
      f8:	c1 ea 05             	shr    edx,0x5
      fb:	41 89 d4             	mov    r12d,edx
      fe:	41 83 ec 01          	sub    r12d,0x1
     102:	0f 84 35 01 00 00    	je     23d <load_ecc8+0x16d>
     108:	8d 42 fe             	lea    eax,[rdx-0x2]
     10b:	4c 89 ef             	mov    rdi,r13
     10e:	4c 8d 44 86 04       	lea    r8,[rsi+rax*4+0x4]
     113:	eb 4d                	jmp    162 <load_ecc8+0x92>
     115:	4c 8d 35 00 00 00 00 	lea    r14,[rip+0x0]        # 11c <load_ecc8+0x4c>	118: R_X86_64_PC32	.rodata+0x3c
     11c:	48 8d 05 00 00 00 00 	lea    rax,[rip+0x0]        # 123 <load_ecc8+0x53>	11f: R_X86_64_PC32	.rodata+0x3c
     123:	4c 8d 1d 00 00 00 00 	lea    r11,[rip+0x0]        # 12a <load_ecc8+0x5a>	126: R_X86_64_PC32	.rodata+0x3c
     12a:	0f b6 04 10          	movzx  eax,BYTE PTR [rax+rdx*1]
     12e:	43 0f b6 14 16       	movzx  edx,BYTE PTR [r14+r10*1]
     133:	c1 e0 10             	shl    eax,0x10
     136:	c1 e2 18             	shl    edx,0x18
     139:	09 d0                	or     eax,edx
     13b:	43 0f b6 14 0b       	movzx  edx,BYTE PTR [r11+r9*1]
     140:	c1 e2 08             	shl    edx,0x8
     143:	09 d0                	or     eax,edx
     145:	48 8d 15 00 00 00 00 	lea    rdx,[rip+0x0]        # 14c <load_ecc8+0x7c>	148: R_X86_64_PC32	.rodata+0x3c
     14c:	0f b6 0c 0a          	movzx  ecx,BYTE PTR [rdx+rcx*1]
     150:	09 c1                	or     ecx,eax
     152:	48 83 c6 04          	add    rsi,0x4
     156:	48 83 c7 04          	add    rdi,0x4
     15a:	89 4f fc             	mov    DWORD PTR [rdi-0x4],ecx
     15d:	49 39 f0             	cmp    r8,rsi
     160:	74 30                	je     192 <load_ecc8+0xc2>
     162:	80 bb 80 00 00 00 00 	cmp    BYTE PTR [rbx+0x80],0x0
     169:	44 0f b6 16          	movzx  r10d,BYTE PTR [rsi]
     16d:	0f b6 4e 03          	movzx  ecx,BYTE PTR [rsi+0x3]
     171:	44 0f b6 4e 02       	movzx  r9d,BYTE PTR [rsi+0x2]
     176:	0f b6 56 01          	movzx  edx,BYTE PTR [rsi+0x1]
     17a:	75 99                	jne    115 <load_ecc8+0x45>
     17c:	41 c1 e2 18          	shl    r10d,0x18
     180:	0f b6 c2             	movzx  eax,dl
     183:	41 c1 e1 08          	shl    r9d,0x8
     187:	c1 e0 10             	shl    eax,0x10
     18a:	44 09 d0             	or     eax,r10d
     18d:	44 09 c8             	or     eax,r9d
     190:	eb be                	jmp    150 <load_ecc8+0x80>
     192:	8b 43 08             	mov    eax,DWORD PTR [rbx+0x8]
     195:	0f af 03             	imul   eax,DWORD PTR [rbx]
     198:	8d 50 07             	lea    edx,[rax+0x7]
     19b:	42 8d 04 a5 00 00 00 00 	lea    eax,[r12*4+0x0]
     1a3:	4c 89 c6             	mov    rsi,r8
     1a6:	c1 ea 03             	shr    edx,0x3
     1a9:	48 8d 7d dc          	lea    rdi,[rbp-0x24]
     1ad:	29 c2                	sub    edx,eax
     1af:	48 8b 05 00 00 00 00 	mov    rax,QWORD PTR [rip+0x0]        # 1b6 <load_ecc8+0xe6>	1b2: R_X86_64_PC32	vkso_bch_memcpy_slot-0x4
     1b6:	ff d0                	call   rax
     1b8:	80 bb 80 00 00 00 00 	cmp    BYTE PTR [rbx+0x80],0x0
     1bf:	0f b6 55 dc          	movzx  edx,BYTE PTR [rbp-0x24]
     1c3:	74 5d                	je     222 <load_ecc8+0x152>
     1c5:	48 8d 35 00 00 00 00 	lea    rsi,[rip+0x0]        # 1cc <load_ecc8+0xfc>	1c8: R_X86_64_PC32	.rodata+0x3c
     1cc:	48 8d 3d 00 00 00 00 	lea    rdi,[rip+0x0]        # 1d3 <load_ecc8+0x103>	1cf: R_X86_64_PC32	.rodata+0x3c
     1d3:	48 8d 0d 00 00 00 00 	lea    rcx,[rip+0x0]        # 1da <load_ecc8+0x10a>	1d6: R_X86_64_PC32	.rodata+0x3c
     1da:	0f b6 45 dd          	movzx  eax,BYTE PTR [rbp-0x23]
     1de:	0f b6 14 16          	movzx  edx,BYTE PTR [rsi+rdx*1]
     1e2:	0f b6 04 07          	movzx  eax,BYTE PTR [rdi+rax*1]
     1e6:	c1 e2 18             	shl    edx,0x18
     1e9:	c1 e0 10             	shl    eax,0x10
     1ec:	09 d0                	or     eax,edx
     1ee:	0f b6 55 de          	movzx  edx,BYTE PTR [rbp-0x22]
     1f2:	0f b6 14 11          	movzx  edx,BYTE PTR [rcx+rdx*1]
     1f6:	c1 e2 08             	shl    edx,0x8
     1f9:	09 d0                	or     eax,edx
     1fb:	48 8d 0d 00 00 00 00 	lea    rcx,[rip+0x0]        # 202 <load_ecc8+0x132>	1fe: R_X86_64_PC32	.rodata+0x3c
     202:	0f b6 55 df          	movzx  edx,BYTE PTR [rbp-0x21]
     206:	0f b6 14 11          	movzx  edx,BYTE PTR [rcx+rdx*1]
     20a:	45 89 e4             	mov    r12d,r12d
     20d:	09 d0                	or     eax,edx
     20f:	43 89 44 a5 00       	mov    DWORD PTR [r13+r12*4+0x0],eax
     214:	48 83 c4 08          	add    rsp,0x8
     218:	5b                   	pop    rbx
     219:	41 5c                	pop    r12
     21b:	41 5d                	pop    r13
     21d:	41 5e                	pop    r14
     21f:	5d                   	pop    rbp
     220:	c3                   	ret    
     221:	cc                   	int3   
     222:	0f b6 45 dd          	movzx  eax,BYTE PTR [rbp-0x23]
     226:	c1 e2 18             	shl    edx,0x18
     229:	c1 e0 10             	shl    eax,0x10
     22c:	09 d0                	or     eax,edx
     22e:	0f b6 55 de          	movzx  edx,BYTE PTR [rbp-0x22]
     232:	c1 e2 08             	shl    edx,0x8
     235:	09 d0                	or     eax,edx
     237:	0f b6 55 df          	movzx  edx,BYTE PTR [rbp-0x21]
     23b:	eb cd                	jmp    20a <load_ecc8+0x13a>
     23d:	49 89 f0             	mov    r8,rsi
     240:	e9 53 ff ff ff       	jmp    198 <load_ecc8+0xc8>

Disassembly of section .init.text:

Disassembly of section .exit.text:
