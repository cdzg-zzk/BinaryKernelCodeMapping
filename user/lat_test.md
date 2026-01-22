# 测试方式
## 1. 同页同段
gcc -shared -fPIC -O2 -o libclone.so xxh_clone.c

uint32_t xxh32_clone(const void *input, size_t len, uint32_t seed)

## 2. 不同页同段
gcc -O2 -shared -fPIC -Wl,-T,same_seg.ld -Wl,-soname,libclone.so -o libclone.so xxh_clone.c

uint32_t __attribute__((section(".text"), aligned(4096)))
xxh32_clone(const void *input, size_t len, uint32_t seed)

## 3. 不同页不同段
gcc -O2 -shared -fPIC -Wl,-T,diff_seg.ld -Wl,-soname,libclone.so -o libclone.so xxh_clone.c

uint32_t __attribute__((section(".text"), aligned(4096)))
xxh32_clone(const void *input, size_t len, uint32_t seed)

## 4. 没有.init*
gcc -O2 -fPIC -c xxh_clone.c -o xxh_clone.o
ld -shared -T text_ro_noinit.ld -soname libclone.so -o libclone.so xxh_clone.o

## 编译user进程
gcc -g -O2 user.c -L. -lclone  -L../make_dll -lgenerated_library -ldl -lrt -Wl,-rpath,"$ORIGIN:/home/zzk/workspace/KernelCodeMapping/make_dll" -o user

# 测试内容

## 不同页不同段

这一节整理的是“不同页不同段”配置下，`xxh32()` 与 `xxh32_clone()` 首次调用延迟差异的完整分析，将在写论文时用作背景与实验说明。

### 实验设置与现象

- 程序结构：
  - 可执行文件 `user`：
    - PIE，动态链接，解释器：`/lib64/ld-linux-x86-64.so.2`；
    - 动态段中包含：
      - `FLAGS              BIND_NOW`
      - `FLAGS_1            Flags: NOW PIE`
    - `.rela.plt` 中对两个目标函数有：
      - `R_X86_64_JUMP_SLOT    xxh32`
      - `R_X86_64_JUMP_SLOT    xxh32_clone`
  - 动态库：
    - `libclone.so`：实现 `xxh32_clone()`；
    - `libgenerated_library.so`：实现 `xxh32()`。
- 用户态测试代码（简化）：

  ```c
  uint64_t s1 = get_time_ns();
  uint32_t r1 = xxh32(msg, strlen(msg), seed);
  uint64_t e1 = get_time_ns();

  uint64_t s2 = get_time_ns();
  uint32_t r2 = xxh32_clone(msg, strlen(msg), seed);
  uint64_t e2 = get_time_ns();
  ```

  同时在 steady-state 中分别循环调用两者 1e8 次，测平均耗时。

- 代表性测量结果（顺序：先 `xxh32`，再 `xxh32_clone`）：

  ```text
  === First-call measurement ===
  xxh32 first:  14010 ns (0xbe39fa47)
  clone first:    520 ns (0xbe39fa47)

  === VKSO Performance Test ===
  xxh32 avg:       ≈10.1 ns/call
  xxh32_clone avg: ≈10.6 ns/call
  ```

现象总结：

- 两个函数 steady-state 平均耗时几乎相同，说明纯计算开销基本等价；
- first call 上 `xxh32` 比 `xxh32_clone` 慢了约一个数量级（10 µs vs 0.5 µs 左右）。

接下来从三个层面：动态链接器、页表状态、内核调用栈，来解释这一差异。

### 1. 动态链接器视角（LD_DEBUG=all）

运行：

```bash
LD_DEBUG=all ./user 2> tmp.out
```

在 `tmp.out` 中，与两个符号有关的关键日志为（略去无关行）：

```text
relocation processing: ./user
    symbol=xxh32_clone;  lookup in file=./user [0]
    symbol=xxh32_clone;  lookup in file=libclone.so [0]
    binding file ./user [0] to libclone.so [0]: normal symbol `xxh32_clone'

    symbol=xxh32;  lookup in file=./user [0]
    symbol=xxh32;  lookup in file=libclone.so [0]
    symbol=xxh32;  lookup in file=/home/.../libgenerated_library.so [0]
    binding file ./user [0] to /home/.../libgenerated_library.so [0]: normal symbol `xxh32'
```

特点：

- `xxh32` 与 `xxh32_clone` 的符号查找与绑定都发生在 `relocation processing: ./user` 阶段；
- 在整个 `tmp.out` 中，这两条 `binding file ...` 日志各只出现一次；
- 之后在 first-call 的执行时刻，不再有新的 `binding` 或 `_dl_runtime_resolve` 相关日志。

结合动态段中的 `FLAGS BIND_NOW` / `FLAGS_1 NOW PIE`：

- 所有 `R_X86_64_JUMP_SLOT` 重定位在进入 `main()` 前完成；
- first call 时 PLT 已直接指向最终目标地址，不再触发动态链接器逻辑；
- ld.so 对 `xxh32` 与 `xxh32_clone` 的处理在本质上完全对称，仅有的微小差异是：
  - `xxh32` 需要先在 `libclone.so` 中查找，再落到 `libgenerated_library.so`；
  - 这一查找发生在启动阶段，不在 first-call 计时窗口内。

**结论 1（链接器层面）：**  
first call 的明显延迟差异，不来自 ld.so 在“第一次调用时”做了额外解析工作；链接器在进入 `main()` 前已经为两个函数完成了对称的绑定。

### 2. 页表视角（page_walk LKM + netlink）

为了观察 first call 前后两个地址的页表状态，编写了一个简单的 LKM `page_walk.c`：

- 内核侧：
  - 创建 Netlink（协议号 28）监听；
  - 用户态发送消息载荷为：一个 `unsigned long` 用户态虚拟地址，`nlmsg_pid` 填发送进程 pid；
  - 内核通过：
    - `find_get_pid(nlmsg_pid)` / `get_pid_task()` 获取 `task_struct`；
    - `get_task_mm()` 获取 `mm_struct`；
    - 在 `mmap_read_lock(mm)` 下，使用 `pgd_offset()`→`p4d_offset()`→`pud_offset()`→`pmd_offset()`→`pte_offset_map()` 依次遍历页表；
  - 在 dmesg 输出各级表项值、flags 和 PFN。

- 用户态：在 `user.c` 中实现：

  ```c
  void walk_page_table(void)
  {
      int sockfd = socket(AF_NETLINK, SOCK_RAW, 28); // NETLINK_PAGE_WALK
      ...
      send_walk_req(sockfd, (unsigned long)(uintptr_t)xxh32);
      send_walk_req(sockfd, (unsigned long)(uintptr_t)xxh32_clone);
      close(sockfd);
  }
  ```

在 first-call 之前调用一次 `walk_page_table()`，得到的 dmesg 输出（只保留关键部分）：

```text
walk request: pid=... addr=0x7f2a38343900   # xxh32()
PGD ... flags: USER RW EXEC
P4D ...
PUD ...
PMD ...
PTE not present for address 0x7f2a38343900

walk request: pid=... addr=0x7f2a38a81000   # xxh32_clone()
PGD ... flags: USER RW EXEC
P4D ...
PUD ...
PMD ...
PTE 0x1300c0025 flags: USER RO EXEC
PFN: 0x1300c0
page refcount: 3 mapcount: 0
```

含义：

- 对 `xxh32()`：在 first call 前，其虚拟地址对应的 PTE 为 “not present”；
- 对 `xxh32_clone()`：在同一时刻，PTE 已存在，PFN 正常，代码页已经驻留。

**结论 2（页表层面）：**  
在首次调用前，`xxh32` 对应代码页尚未映射到当前进程的页表，而 `xxh32_clone` 的代码页已经映射并可能被预热。这为解释 first call 延迟差异提供了直接证据。

### 3. 内核调用栈视角（ftrace / function_graph）

为了精确了解 first call 时内核做了什么，在 `user.c` 中利用 `getchar()` 人为切分时间窗口，并使用 ftrace 的 `function_graph` tracer 仅跟踪该 pid：

用户态结构（简化）：

```c
getchar();                          // 控制起点
uint64_t s1 = get_time_ns();
uint32_t r1 = xxh32(...);           // first call A
uint64_t e1 = get_time_ns();

getchar();                          // 再停一下

uint64_t s2 = get_time_ns();
uint32_t r2 = xxh32_clone(...);     // first call B
uint64_t e2 = get_time_ns();
getchar();                          // 末尾再停
```

在 ftrace 中：

```bash
echo function_graph > current_tracer
echo <pid> > set_ftrace_pid
echo 1 > tracing_on    # 在第一个 getchar 之后打开
... 执行 first call ...
echo 0 > tracing_on    # 在第二个 getchar 之后关闭
cat trace > tmp.out
```

从 `tmp.out` 中抽取到的关键调用栈片段如下：

```text
handle_mm_fault() {
  mem_cgroup_from_task();
  __count_memcg_events() {
    cgroup_rstat_updated();
  }
  __handle_mm_fault() {
    do_fault() {
      filemap_map_pages() {
        next_uptodate_page();
        _raw_spin_lock();
        PageHuge();
        do_set_pte() {
          page_add_file_rmap() {
            lock_page_memcg();
            __mod_lruvec_page_state();
            unlock_page_memcg();
          }
        }
        unlock_page();
        next_uptodate_page();
        rcu_read_unlock_strict();
      }
    }
  }
}
up_read();
exit_to_user_mode_prepare();

__x64_sys_read() {      # 后续 getchar() 对应的 read -> tty_read -> schedule 路径
  ...
}
```

重要观察：

- 整个 trace 中 **只出现一次** `handle_mm_fault()`；
- 这次 `handle_mm_fault` 之后紧跟着的是 `__x64_sys_read()`，对应的是 first call 完成后、下一次 `getchar()` 等待键盘输入的路径；
- 在整个 first-call 窗口内没有第二次 `handle_mm_fault` 或 `do_user_addr_fault`。

结合调用顺序（先 `xxh32` 再 `xxh32_clone`）可以明确：

- 这一次 `handle_mm_fault()` 对应 `xxh32()` 的 first call；
- `xxh32_clone()` 的 first call 在这次窗口内没有发生新的缺页。

从调用栈结构可见，这是典型的 **file-backed minor page fault**：

- `filemap_map_pages()` + `next_uptodate_page()`：页已在 page cache 中，说明不需要从磁盘读入，只是缺少 PTE；
- `do_set_pte()` + `page_add_file_rmap()`：建立 PTE 和 rmap（把物理页挂到进程地址空间）；
- `lock_page_memcg()` / `__mod_lruvec_page_state()` / `unlock_page_memcg()`：更新 LRU 与 memcg 的相关统计。

**结论 3（内核栈层面）：**  
在 first-call 窗口中，只有 `xxh32()` 触发了一次 file-backed minor page fault 的完整内核路径；`xxh32_clone()` first call 没有缺页。

### 4. 两次 first call 的行为对比

综合以上三个视角，可以把两次 first call 的行为归纳为：

#### 4.1 `xxh32()` first call

- 初次访问 `libgenerated_library.so` 的 `.text` 段，虚拟地址对应的 PTE 尚未存在；
- CPU 触发用户态页故障，内核走：

  ```text
  handle_mm_fault
    -> __handle_mm_fault
      -> do_fault
        -> filemap_map_pages
           -> next_uptodate_page       # 页已在 page cache
           -> do_set_pte
              -> page_add_file_rmap
              -> memcg / LRU 统计更新
  ```

- 这一套缺页 + 记账的成本完全落在 `xxh32()` 的 first call 时间窗口内，构成额外几微秒到十几微秒的开销；
- 加上 hash 本身的计算与 `clock_gettime()` 的代价，总体 first-call 延迟约 `10^1 µs` 量级。

#### 4.2 `xxh32_clone()` first call

- 在 first call 前：
  - `page_walk` 显示其 PTE 已经 present，PFN 正常；
  - 这说明：
    - 代码页要么在动态链接/重定位阶段被触碰，要么内核在装载小库时一次性把整个 RX 段预热到了页表中。
- 在 first call 窗口内：
  - ftrace 没有记录到新的 `handle_mm_fault()`；
  - 仅有用户态计算与 `clock_gettime()`/`getchar()` 等常规系统调用。
- 因此 `xxh32_clone()` first call 延迟只包含：
  - hash 计算本身；
  - `clock_gettime()` 的少量开销（大多通过 vDSO 走用户态）；
  - 非冷页情况下的 cache/TLB 开销；
  - 总体在数百 ns 量级。

### 5. 总体结论与启示

1. **动态链接器并不是 first-call 差异的根源**  
   BIND_NOW 使得 ld.so 在进入 `main()` 前就完成了所有 PLT/GOT 重定位；`LD_DEBUG` 证明两符号的绑定各只发生一次，first call 不再进入 ld.so。

2. **first-call 延迟差异主要来自 file-backed minor page fault**  
   页表与 ftrace 实验结合清晰地表明：
   - `xxh32()` first call：“页在 page cache，PTE 不存在” → 触发一次 file-backed minor fault，并进行 memcg/LRU 记账；
   - `xxh32_clone()` first call：“页已经映射且 PTE 存在” → 不再缺页。

3. **纯计算部分的开销可以忽略不计**  
   steady-state 中两函数平均耗时均 ≈10 ns/call，说明 hash 算法和编译优化带来的差异在纳秒级；first-call 的 10 µs 级差异完全由内核缺页与统计行为主导。

4. **如何控制/复现 first-call 行为**  
   - 若在测量前先显式调用一次 `xxh32()`，或对其代码页执行 `mlock()` / `madvise(MADV_WILLNEED)`，再测 first call，延迟会收敛到与 `xxh32_clone()` 相近；
   - 若在 `libgenerated_library.so` 中添加一个轻量级 `.init_array` 函数，启动阶段访问 `xxh32` 所在页，同样可以提前完成映射与预热；
   - 通过 LKM `page_walk` 与 ftrace `function_graph` 的联合使用，可以系统地分析任意函数 first call 时页表、缺页与内核调用栈的关系。

5. **对论文写作的启示**  
   在分析“首次调用延迟”时，应同时考虑：
   - 链接策略（lazy vs BIND_NOW）仅决定“解析何时发生”，但在 BIND_NOW 场景中对首次调用不再有额外影响；
   - 段/页布局（同页/异页、同段/异段）影响“某段代码首次是否会被碰到，从而触发缺页”；
   - 缺页路径（特别是 file-backed minor fault）及其 memcg/LRU 统计可能引入数微秒级开销；
   - CPU 前端与 cache/TLB 的冷启动则进一步放大此差异。

   在本实验环境中，**first-call latency 的主因可以归结为：是否在首次调用前已经为目标函数所在页建立了 PTE，并将其预热到内存与缓存中。**

### 7. 去除 init/fini 之后的再次对比（两边都发生 first fault）

为了进一步验证结论，并排除 `.init/.fini/.init_array` 对 `libclone.so` 的潜在预热影响，进行了第二组实验：构造一个**完全没有 init/fini/init_array** 的 `libclone.so`，同时保持 `.text` 单独成页但仍处于同一个 RX 段，然后再次测量并用 ftrace 抓取 first-call 行为。

#### 7.1 链接脚本与构建方式

- 新的链接脚本 `same_seg_noinit.ld`：

  ```ld
  OUTPUT_FORMAT(elf64-x86-64)
  OUTPUT_ARCH(i386:x86-64)

  PHDRS {
    text    PT_LOAD    FLAGS(0x5);   /* PF_R | PF_X */
    data    PT_LOAD    FLAGS(0x6);   /* PF_R | PF_W */
    dynamic PT_DYNAMIC FLAGS(0x6);
  }

  SECTIONS {
    . = 0x1000;

    . = ALIGN(0x1000);
    .text :
    {
        *(.text .text.*)
        *(.plt .plt.*)
        *(.plt.got)
        *(.plt.sec)
    } :text

    .rodata ALIGN(0x1000) :
    {
        *(.rodata .rodata.*)
        *(.eh_frame .eh_frame.*)
        *(.note.gnu.property)
        *(.note.gnu.build-id)
    } :text

    .dynamic ALIGN(0x1000) :
    {
        *(.dynamic)
    } :data :dynamic

    .dynsym ALIGN(0x1000)  : { *(.dynsym)  } :data
    .dynstr ALIGN(0x1000)  : { *(.dynstr)  } :data
    .gnu.hash ALIGN(0x1000): { *(.gnu.hash) } :data
    .hash ALIGN(0x1000)    : { *(.hash)    } :data
    .rela.dyn ALIGN(0x1000): { *(.rela.dyn) } :data

    /* 显式丢弃 init_array/fini_array/init/fini，避免任何启动期构造函数预热 .text。 */
    /DISCARD/ : {
        *(.init)
        *(.fini)
        *(.init_array*)
        *(.fini_array*)
    }
  }
  ```

- 关键点：
  - 直接使用 `ld` 链接，不通过 `gcc -shared`，避免自动拉入 `crti.o / crtn.o / crtbeginS.o` 等 CRT 对象；
  - 生成方式：

    ```bash
    gcc -O2 -fPIC -c xxh_clone.c -o xxh_clone.o
    ld -shared -T same_seg_noinit.ld -soname libclone.so -o libclone.so xxh_clone.o
    ```

  - `readelf -S libclone.so`：只有 `.text/.rodata/.dynamic/.dynsym/.dynstr/.gnu.hash/.hash/...`，**没有 `.init/.fini/.init_array/.fini_array`**；
  - `readelf -d libclone.so`：没有 `DT_INIT/DT_FINI/DT_INIT_ARRAY/DT_FINI_ARRAY`，只有 SONAME/HASH/GNU_HASH/STR* 等 8 项，动态链接器不会再试图调用 `_init/_fini`。

在这一构建下，`libclone.so` 的代码页在进入 `main()` 前不会被 `.init` 或构造函数触碰，两边的代码都“同样冷”。

#### 7.2 新的 first-call 测量结果

在新的 `libclone.so` 下重新运行 `user`，得到代表性结果：

```text
=== First-call measurement ===
xxh32 first:  3690 ns (0xbe39fa47)
clone first:  5729 ns (0xbe39fa47)

=== VKSO Performance Test ===
xxh32 avg:       ≈10.1 ns/call
xxh32_clone avg: ≈10.6 ns/call
```

与之前相比：

- 原先：`xxh32 first` 明显较慢，`xxh32_clone first` 接近“热”状态；
- 现在：两者 first call 都从纳秒级跃升至微秒级，且 `xxh32_clone()` 的 first call 甚至略慢于 `xxh32()`。

这说明在“无 init/fini/init_array 预热”的场景下，**两个库的 first-call 都触发了内核缺页与统计路径**，只是第二次做的工作更多一些。

#### 7.3 ftrace：两次 handle_mm_fault 的对比

再次使用 `function_graph` + `getchar()` 按照如下顺序划定时间窗口：

```c
getchar();                          // 窗口开始
uint64_t s1 = get_time_ns();
uint32_t r1 = xxh32(...);           // first call: xxh32
uint64_t e1 = get_time_ns();
getchar();                          // 窗口中点

uint64_t s2 = get_time_ns();
uint32_t r2 = xxh32_clone(...);     // first call: xxh32_clone
uint64_t e2 = get_time_ns();
getchar();                          // 窗口结束
```

在这一窗口内，`tmp.out` 中可以看到 **两次** `handle_mm_fault()`，分别对应 `xxh32` 和 `xxh32_clone` 的首次执行。

第一次 `handle_mm_fault()`（对应 `xxh32()`）的大致调用栈如下：

```text
find_vma()
handle_mm_fault() {
  mem_cgroup_from_task();
  __count_memcg_events() {
    cgroup_rstat_updated();
  }
  rcu_read_unlock_strict();
  __handle_mm_fault() {
    do_fault() {
      filemap_map_pages() {
        next_uptodate_page();       # 从 page cache 找到已存在的文件页
        _raw_spin_lock();
        PageHuge();
        do_set_pte() {
          page_add_file_rmap() {
            lock_page_memcg();
            __mod_lruvec_page_state();  # 更新 lru/memcg 统计
            unlock_page_memcg();
          }
        }
        unlock_page();
        next_uptodate_page();
        rcu_read_unlock_strict();
      }
    }
  }
}
up_read();
exit_to_user_mode_prepare();
__x64_sys_read() { ... }            # 后续 getchar()
```

第二次 `handle_mm_fault()`（对应 `xxh32_clone()`）的大致调用栈为：

```text
...（前一个 __x64_sys_read / getchar() 结束）...
find_vma()
handle_mm_fault() {
  mem_cgroup_from_task();
  __count_memcg_events() {
    cgroup_rstat_updated();
  }
  rcu_read_unlock_strict();
  __handle_mm_fault() {
    do_fault() {
      filemap_map_pages() {
        next_uptodate_page();
        _raw_spin_lock();
        PageHuge();
        do_set_pte() {
          page_add_file_rmap() {
            lock_page_memcg();
            __mod_lruvec_page_state() {
              __mod_lruvec_state() {
                __mod_node_page_state();
                __mod_memcg_lruvec_state() {
                  cgroup_rstat_updated();
                }
              }
              rcu_read_unlock_strict();
            }
            unlock_page_memcg();
          }
        }
        unlock_page();
        next_uptodate_page();
        PageHuge();
        do_set_pte() {              # 同一次 fault 中的第二个 do_set_pte
          page_add_file_rmap() {    # 对相邻页重复 rmap + memcg 更新
            ...
          }
        }
        unlock_page();
        next_uptodate_page();
        rcu_read_unlock_strict();
      }
    }
  }
}
up_read();
exit_to_user_mode_prepare();
__x64_sys_read() { ... }            # 随后的 getchar()
```

对比可以看出：

- 两次 `handle_mm_fault()` **走的是同一条逻辑路径**：
  - 都是 `find_vma → handle_mm_fault → __handle_mm_fault → do_fault → filemap_map_pages`；
  - 都是 file-backed minor fault：`next_uptodate_page()` 说明页已在 page cache，只是 PTE 缺失；
  - 都调用 `do_set_pte → page_add_file_rmap` 给进程建立 PTE 且挂 rmap；
  - 都有 `__mod_lruvec_page_state` / `__mod_memcg_lruvec_state` 等 memcg/LRU 统计更新。
- 区别在于**工作量**：
  - `xxh32` 的那次 fault，在 `filemap_map_pages()` 中只对一页执行 `do_set_pte`（单页映射）；
  - `xxh32_clone` 的那次 fault，在同一次 `filemap_map_pages()` 调用中对两页执行了 `do_set_pte` / `page_add_file_rmap`，即一次 fault 映射两页代码；
  - 因此第二次 fault 需要更多 memcg/LRU 更新，ftrace 中 `handle_mm_fault` 的 duration 也明显更大（约 `+15–16 µs`，对应 `clone first ≈ 5.7 µs`）。

**结论 4（无 init/fini 场景）：**

- 在完全消除 `.init/.fini/.init_array/.fini_array` 后：
  - `libclone.so` 和 `libgenerated_library.so` 的代码页在进入 `main()` 前都没有被启动期构造函数预热；
  - 两边的 first call 都触发了 file-backed minor page fault，走同一套 `handle_mm_fault → filemap_map_pages → do_set_pte → page_add_file_rmap` 路径；
  - 区别只在于一次 fault 映射的页数量和 memcg 统计的工作量：`xxh32` 映射一页，`xxh32_clone` 映射两页，因此后者 first call 稍慢。

这组实验进一步强化了前面的总体结论：

- **first-call latency 的本质来源不是 ld.so，也不是函数本身的计算复杂度，而是“这一次调用是否触发 file-backed minor fault，以及在一次 fault 中映射了多少页并伴随多少 memcg/LRU 记账工作”。**  
- 一旦消除布局和 init 预热差别，让两个库在 first-call 时都处于“同样冷”的状态，它们在内核中的行为模式就非常一致，仅仅因为映射页数不同而出现细微的时间差异。  

从论文写作角度看，这提供了一个很好的对照组：  
同一算法、同一编译优化、同一链接器行为下，通过精确控制 init/布局，first-call latency 可以从纳秒级稳定性能上方增加一个数量级以上，但整个差异完全可通过 page-fault 路径和 memcg/LRU 统计行为来解释，而不是“神秘”的动态链接开销。***


# 内核执行路径不同
是的，你推的这个猜测基本就是原因：

  - 你把一个 .so 的 page cache 条目硬绑到了“内核 text 所在的物理页”上，这个物理页在内核里本来就是 kernel text，用的是“内核自己的生命
    周期+记账”，没有 memcg 记账；
  - 所以 page_memcg(head) 返回 NULL，__mod_lruvec_page_state() 走了 !memcg 分支，只更新 node 统计，不更新 memcg，这就解释了你看到的那
    种 __mod_lruvec_page_state() 调用路径。

  换句话说：同样是一次 file-backed page fault，你人为塞进去的“内核 text 页”在 memcg 看来是“untracked page”，而普通 .so 页是 “被 memcg
  charge 过的 page”，所以统计路径不一样。
```c
  0)  user-201138   |               |  handle_mm_fault() {
  0)  user-201138   |   0.179 us    |    mem_cgroup_from_task();
  0)  user-201138   |               |    __count_memcg_events() {
  0)  user-201138   |               |      cgroup_rstat_updated() {
  0)  user-201138   |   0.211 us    |        _raw_spin_lock_irqsave();
  0)  user-201138   |   0.129 us    |        _raw_spin_unlock_irqrestore();
  0)  user-201138   |   2.160 us    |      }
  0)  user-201138   |   2.930 us    |    }
  0)  user-201138   |   0.110 us    |    rcu_read_unlock_strict();
  0)  user-201138   |               |    __handle_mm_fault() {
  0)  user-201138   |               |      do_fault() {
  0)  user-201138   |               |        filemap_map_pages() {
  0)  user-201138   |   0.640 us    |          next_uptodate_page();
  0)  user-201138   |   0.229 us    |          _raw_spin_lock();
  0)  user-201138   |   0.110 us    |          PageHuge();
  0)  user-201138   |               |          do_set_pte() {
  0)  user-201138   |               |            page_add_file_rmap() {
  0)  user-201138   |   0.129 us    |              lock_page_memcg();
  0)  user-201138   |               |              __mod_lruvec_page_state() {
  0)  user-201138   |               |                __mod_lruvec_state() {
  0)  user-201138   |   0.230 us    |                  __mod_node_page_state();
  0)  user-201138   |               |                  __mod_memcg_lruvec_state() {
  0)  user-201138   |   0.120 us    |                    cgroup_rstat_updated();
  0)  user-201138   |   0.480 us    |                  }
  0)  user-201138   |   1.050 us    |                }
  0)  user-201138   |   0.130 us    |                rcu_read_unlock_strict();
  0)  user-201138   |   1.580 us    |              }
  0)  user-201138   |               |              unlock_page_memcg() {
  0)  user-201138   |               |                __unlock_page_memcg() {
  0)  user-201138   |   0.109 us    |                  rcu_read_unlock_strict();
  0)  user-201138   |   0.310 us    |                }
  0)  user-201138   |   0.571 us    |              }
  0)  user-201138   |   2.730 us    |            }
  0)  user-201138   |   3.040 us    |          }
  0)  user-201138   |   0.111 us    |          unlock_page();
  0)  user-201138   |   0.120 us    |          next_uptodate_page();
  0)  user-201138   |   0.190 us    |          rcu_read_unlock_strict();
  0)  user-201138   |   7.291 us    |        }
  0)  user-201138   |   7.849 us    |      }
  0)  user-201138   |   9.381 us    |    }
  0)  user-201138   | + 13.590 us   |  }


  0)  user-201138   |               |  handle_mm_fault() {
  0)  user-201138   |   0.120 us    |    mem_cgroup_from_task();
  0)  user-201138   |               |    __count_memcg_events() {
  0)  user-201138   |   0.390 us    |      cgroup_rstat_updated();
  0)  user-201138   |   1.011 us    |    }
  0)  user-201138   |   0.109 us    |    rcu_read_unlock_strict();
  0)  user-201138   |               |    __handle_mm_fault() {
  0)  user-201138   |               |      do_fault() {
  0)  user-201138   |               |        filemap_map_pages() {
  0)  user-201138   |   0.540 us    |          next_uptodate_page();
  0)  user-201138   |   0.250 us    |          _raw_spin_lock();
  0)  user-201138   |   0.120 us    |          PageHuge();
  0)  user-201138   |               |          do_set_pte() {
  0)  user-201138   |               |            page_add_file_rmap() {
  0)  user-201138   |   0.120 us    |              lock_page_memcg();
  0)  user-201138   |               |              __mod_lruvec_page_state() {
  0)  user-201138   |   0.100 us    |                rcu_read_unlock_strict();
  0)  user-201138   |   0.250 us    |                __mod_node_page_state();
  0)  user-201138   |   0.699 us    |              }
  0)  user-201138   |               |              unlock_page_memcg() {
  0)  user-201138   |               |                __unlock_page_memcg() {
  0)  user-201138   |   0.099 us    |                  rcu_read_unlock_strict();
  0)  user-201138   |   0.320 us    |                }
  0)  user-201138   |   0.539 us    |              }
  0)  user-201138   |   1.809 us    |            }
  0)  user-201138   |   2.120 us    |          }
  0)  user-201138   |   0.101 us    |          unlock_page();
  0)  user-201138   |   0.120 us    |          next_uptodate_page();
  0)  user-201138   |   0.110 us    |          rcu_read_unlock_strict();
  0)  user-201138   |   5.351 us    |        }
  0)  user-201138   |   5.840 us    |      }
  0)  user-201138   |   6.901 us    |    }
  0)  user-201138   |   8.830 us    |  }
```
## memcg
*路径不同就是因为内核页不走cgroup的记账*
- memcg = memory cgroup，是内核里“按 cgroup 分账的内存子系统”。
  - 它给每个 cgroup（容器、服务组）单独记：
      - 占用了多少匿名内存、page cache、部分内核内存；
      - 各种统计（fault 次数、reclaim 次数、RSS、cache 等）。
  - 它还能对每个 cgroup 单独施加策略：
      - memory.max / memory.limit_in_bytes：超出就优先在本 cgroup 里 reclaim / OOM kill；
      - memory.high：超到高水位就提前回收，防止占用过多；
      - per‑cgroup 的 reclaim、pressure、OOM 通知等。

  没有 memcg 的情况下（或者 CONFIG_MEMCG=n / 整体禁用）：

  - 所有进程的内存只按“全局系统”一个桶来算：
      - 没有 per‑cgroup 限制，也看不到 per‑cgroup 统计；
      - 只有系统级 reclaim 和系统级 OOM，谁多占内存并不会按服务边界区分。
  - 优点：
      - 少了一层 per‑page 的 memcg 元数据和 rstat 路径，开销略小、代码简单些（你看到的 page_memcg() 通常直接是 NULL，
        __mod_lruvec_page_state() 只更新 node）。
  - 缺点：
      - 容器/服务之间不能在内存上做硬隔离，某个容器暴涨会把整个机子的内存吃光，触发全局 OOM，可能杀到无辜进程；
      - 运维和监控没法看到“每个 cgroup 用了多少内存”，只能看系统总量。

  结合你前面的实验：
  page_memcg(page) == NULL 就是“这个页没被 memcg 记账，所以不属于任何 cgroup 的内存用量”，这在不开/少用 memcg 的场景或那些本来就不做
  memcg 计费的页（例如内核 text、某些内核内存）上是正常现象。
