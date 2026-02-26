# test_PIC_LKM_latency

用于评估 PIC/LKM 改造中「**伪 GOT 读指针 + 间接调用**」带来的额外开销的微基准。该开销强依赖 **间接调用目标的可预测性**，因此本测试同时覆盖：

- `stable`：目标恒定（common-case，下界）
- `alt2`：两个目标交替（轻度不可预测）
- `randomN`：N 个目标随机（高度不可预测，上界）

注：`alt2` 在部分微架构上可能仍能被间接分支预测器“学到”（例如为同一 callsite 记住多个目标）；`randomN`（较大的 N）通常更接近 worst-case。

**实验目的**
- 定量评估 PIC/LKM 引入的「GOT 访问 + 间接调用」组合成本（cycles/call）。
- 给论文提供两类证据：
  - common-case（目标稳定）时开销接近 0；
  - worst-case（目标不可预测）时的上界量级。

**实验原理**
- 使用 `lfence + rdtsc` 读取周期计数，保证测量区间不被乱序执行打乱。
- 目标函数为一组 `bench_stub_*()`（`noinline`），函数体极短，用于最大化“调用开销”的可观测性。
- 直接调用路径：循环内 `call bench_stub_0`。
- 间接调用路径：循环内从 `got_fns[idx]`（伪 GOT 表）读取函数指针并 `call *%reg`（或 retpoline thunk）。
- `randomN` 场景：在计时区间外预先生成一个 **函数指针序列**（长度 `pattern_len`，元素取自前 N 个 stub），计时区间内只做 `fn = pattern[i]` + `fn()`，避免把“生成随机数/取 idx”的开销混入结果。
- 固定到单个 CPU 执行（`smp_call_function_single`，默认 CPU0，可通过 `cpu=` 选择），每个批次关闭抢占与中断，减少噪声。
- 采用 warm-up 预热，稳定缓存与分支预测。

---

## Skylake / Zen2 的经验量级（写论文用）

这不是本项目测得的“固定常数”，只是常见经验范围，帮助你解释为什么 **stable 间接调用**往往几乎没成本，而 **不可预测的间接调用**会很贵：

场景 | 额外代价（大致）
---|---
直接调用 | baseline
稳定间接调用（目标几乎不变） | +0~1 cycle
偶尔失误（少量 miss） | +5~8 cycles
高度不可预测（频繁 miss） | +15~25 cycles

因此论文里应同时报告 stable 与 worst-case（例如 randomN）的结果，而不是只给 stable 的“很小开销”就做总体性能结论。

**编译与运行**
```bash
make
make bench
```

## 复现流程（baseline vs modified kernel）

建议把这组数据作为“调用开销层面”的证据，并在 **baseline kernel** 与 **modified kernel** 上各跑一遍：

1. 固定测试环境（同一台机器、同一 BIOS/微码设置、固定 CPU 频率/关闭 DVFS，必要时关闭 SMT）。
2. 在 baseline kernel 下运行：`make bench`（或带参数运行）。
3. 记录模块输出的 `avg` 行（至少 `stable/alt2/randomN` 三个场景）。
4. 切换到 modified kernel，重复步骤 2~3。
5. 报告对比：`overhead(modified) - overhead(baseline)`（cycles/call），并把结论放回宏基准里验证。

建议优先选择隔离核运行（例如本机启动参数里 `isolcpus=2,3`，则用 `CPU=2`），否则 CPU0/1 可能被系统噪声影响。

如果需要手动控制：
```bash
make load
make log
make unload
```

**参数**
- `ITERATIONS` 每次 run 的总迭代次数，默认 `1000000`
- `REPEATS` 重复 run 次数，默认 `10`
- `WARMUP_RUNS` 预热次数，默认 `3`
- `WARMUP_ITERS` 每次预热迭代数，默认 `100000`
- `ALT2` 是否运行 `alt2`（两目标交替）场景，默认 `1`
- `RANDOM` 是否运行 `randomN`（多目标随机）场景，默认 `1`
- `RANDOM_SWEEP` 是否一次性测 `random4/8/16/32`（默认 `1`；开启后忽略 `RANDOM_TARGETS`）
- `RANDOM_TARGETS` `randomN` 的目标数量 N（`<=32`；小于 2 会禁用 random），默认 `16`
- `PATTERN_LEN` 随机场景的“目标序列长度”（建议 2 的幂；若不是会向下取整到最近的 2 的幂；`<=65536`），默认 `4096`
- `SEED` 随机序列 seed，默认 `1`
- `CPU` 在哪个 CPU 上运行（默认 `0`；建议选择隔离核以减少噪声）

示例：
```bash
make load ITERATIONS=2000000 REPEATS=20 WARMUP_RUNS=5 WARMUP_ITERS=200000
```

**输出解读**
- `direct`：直接调用 `bench_stub_0()` 的 cycles/call（baseline）
- `stable`：`got_fns[0]` 的间接调用 cycles/call（common-case）
- `alt2`：`got_fns[i&1]` 两目标交替 cycles/call
- `randomN`：从预生成的 **函数指针序列**中取目标并间接调用 cycles/call（N 为目标集合大小）
- `overhead`：`mode - direct`（模块会输出 avg 行的 overhead）
- 平均值以 6 位小数输出，避免整数截断导致“看似差 1 cycle”的误读。

示例（输出格式）：
```
test_lkm_latency: run=1 direct=3.900 stable=4.010 alt2=4.2xx random16=5.xxx cycles/call
...
test_lkm_latency: avg direct=3.9xxxxx cycles/call
test_lkm_latency: avg stable=4.0xxxxx cycles/call, overhead=0.xxxxxx cycles/call
test_lkm_latency: avg alt2=...
test_lkm_latency: avg random16=...
```

**如何避免优化（确保测到 GOT 访问 + 间接跳转）**
- `bench_stub_*()` 使用 `noinline` + inline asm，避免被内联/消除。
- `got_fns[]` 在 `init` 阶段用 `WRITE_ONCE()` 填表，避免编译期常量传播。
- 循环内用 `READ_ONCE(got_fns[idx])` 强制每次从内存读取指针，然后通过局部变量 `fn()` 间接调用。
- `randomN` 的 **函数指针序列**在计时区间外预生成（pattern），避免把 PRNG/取 idx 的指令成本混入“间接调用成本”。

**指令差异与开销来源（关键点）**
实际反汇编（`objdump -dr`）显示，循环内差异如下（已验证）： 

直接调用：
```asm
call   bench_stub_0
```

间接调用（伪 GOT，编译期 retpoline 形式；运行时可能被 alternatives 替换为 `call *%reg`）：
```asm
mov    got_fns(%rip), %rdx
call   __x86_indirect_thunk_rdx
```

因此多出来的周期主要来自：
- 每次循环多一次函数指针读取（GOT 访问）。
- 间接调用经过 `__x86_indirect_thunk_*`（retpoline 路径）带来的额外指令与分支开销。
- 若目标不可预测（alt2/randomN），会叠加 **间接分支预测失误** 的流水线清空代价。

说明：`randomN` 的实现不是在循环里“生成随机数再索引 got_fns”，而是循环里直接从预生成的 **函数指针序列**加载并调用，以减少无关开销。

`bench_stub_*()` 反汇编（函数体极短，但内核构建配置可能插入 `__fentry__`/`__x86_return_thunk`）： 
```asm
bench_stub_0:
  call __fentry__
  push %rbp
  mov  %rsp,%rbp
  mov  $0,%eax
  pop  %rbp
  jmp  __x86_return_thunk
```
说明：即使 stub 很短，“入口/返回”仍可能有固定基线开销，所以论文里更应该关注 **indirect - direct** 的差值。

---

## 实测结果（本机）

**环境**
- CPU：Intel Core i7-1165G7 @ 2.80GHz（4C/4T，SMT off）
- Kernel：`5.15.0-119-generic`
- Spectre v2：`Enhanced / Automatic IBRS`（见下文 “vulnerabilities/spectre_v2”）
- 启动参数（节选）：`isolcpus=2,3 nohz_full=2,3 rcu_nocbs=2,3 idle=poll intel_pstate=disable processor.max_cstate=0 intel_idle.max_cstate=0`

**运行参数（推荐 sweep 版本）**
- `iterations=10000000 repeats=20 warmup_runs=5 warmup_iterations=200000`
- `enable_alt2=1 enable_random=1 random_sweep=1 pattern_len=4096 seed=1 cpu=2`

复现命令（等价）：
```bash
cd test/test_PIC_LKM_latency
make -j"$(nproc)"
sudo dmesg -C
sudo insmod ./test_lkm_latency.ko \
  iterations=10000000 repeats=20 warmup_runs=5 warmup_iterations=200000 \
  enable_alt2=1 enable_random=1 random_sweep=1 pattern_len=4096 seed=1 \
  cpu=2
sudo dmesg | grep "test_lkm_latency: avg"
sudo rmmod test_lkm_latency
```

**结果（cycles/call）**

模式 | avg cycles/call | overhead (cycles) | overhead @2.8GHz (ns)
---|---:|---:|---:
direct | 4.018013 | - | -
stable | 4.018557 | 0.000544 | 0.0002
alt2 | 5.021719 | 1.003706 | 0.3585
random4 | 24.875599 | 20.857586 | 7.4491
random8 | 28.023198 | 24.005185 | 8.5733
random16 | 28.735535 | 24.717522 | 8.8277
random32 | 29.839624 | 25.821611 | 9.2220

**如何对比（把两类效应拆开）**

`direct` 与 `stable` 反映的是“访问方式变化”（direct → indirect + 读指针）在 **common-case（目标稳定）** 下的成本：
- `stable - direct = 0.000544 cycles/call`

`stable` 与 `alt2/randomN` 反映的是“同为 indirect 时，目标可预测性变化”带来的额外惩罚（更贴近论文里所谓 common-case vs worst-case）：
- `alt2 - stable = 1.003162 cycles/call`
- `random4 - stable = 20.857042 cycles/call`
- `random8 - stable = 24.004641 cycles/call`
- `random16 - stable = 24.716978 cycles/call`
- `random32 - stable = 25.821067 cycles/call`

结论（就“调用点开销”而言）：
- `stable` 预期可忽略：真实 OS 场景里，模块注册后函数指针通常长期稳定，属于 common-case。
- `randomN` 给出上界：用于模拟同一 callsite 目标高度多态/不可预测时的 worst-case。

注意：`pattern_len` 太大时会把额外的“读 pattern 的访存开销”带进 `randomN`，建议优先用 `pattern_len=4096` 这类能更容易常驻 L1D 的设置；需要更强压力时再增大 `pattern_len` 并单独报告。

补充说明：`randomN` 的计时区间内仍包含 `pattern[(i)&mask]` 的索引/取指针（`and/lea` + 1 次指针 load），因此它衡量的是「选目标 + 间接调用」的总成本，而不是“纯粹的间接分支预测 miss 成本”。但这部分固定开销通常远小于 `randomN` 观察到的 +20~26 cycles/call 量级（本机 `alt2` 仅 +1 cycle/call），不会改变“common-case 近 0 / worst-case 显著”的结论。

## 论文建议：怎么用这组数据“说服”

### 1) 微基准（本目录）
建议在论文里至少报告三条曲线/三个点：
- `stable`：说明 common-case 几乎无感（目标稳定）
- `alt2`：说明小规模目标集合时的代价
- `randomN`（例如 N=16/32）：给出 worst-case 上界量级（目标不可预测）

并明确说明：这只是“调用点级别”的微开销，不能替代宏基准。

### 2) 宏基准（系统整体）
为了把结论从“单个 callsite”推到“OS 性能几乎不受影响”，需要用宏基准覆盖典型内核路径（至少 2~3 类）：

- CPU/调度：`hackbench`（进程/线程调度、pipe/socket 传输）
- 存储：`fio`（冷热缓存两种场景）
- 网络：`netperf`/`iperf3`（吞吐/延迟）
- 现实工作负载（可选）：内核编译（`make -j`）或你论文的目标应用

本仓库也提供了一个更贴近“复用内核代码”的宏基准示例：`test/test_MACRO/`（fsverity-utils digest 后端替换/对照）。

做法建议：
1. baseline kernel 与 modified kernel 使用相同配置、固定 CPU 频率、相同 NUMA/SMT 设置；
2. 每项宏基准跑多次（≥10），报告 median 与 IQR/std；
3. 结果以相对差异（%）为主，并给出绝对值用于复现。

**时间换算（基于本机 2.8GHz）**
- 频率来源：`/proc/cpuinfo` 显示 `cpu MHz: 2800.000`（等价于 2.8GHz）
- 换算公式：`time(ns) = cycles / 2.8`

模块输出是 cycles/call，你可以按当前频率换算成 ns/call（论文里建议主要保留 cycles/call，避免 DVFS/频率差导致误读）。

**为什么差异很小（合理性说明）**
在 `stable` 场景观测到 overhead 小于 1 cycle 属于合理现象，原因主要来自微架构执行特性：  
1. 本实验统计的是**平均吞吐**而非指令的**串行延迟**。在超标量流水线中，多出的指令可能与循环控制/计数指令并行执行，因而未落入关键路径。  
2. `got_fns[]` 的读取通常命中 L1 cache，且可被乱序执行调度隐藏，其额外代价在吞吐视角下被大幅摊薄。  
3. 运行时观察到 retpoline 被替换为 `call *%reg`，间接调用路径更短，分支预测稳定后几乎不产生显著惩罚。  
4. `bench_stub_*()` 极短，固定的入口/返回开销占比更大，进一步压缩“差异占比”。  
因此 0.03ns 级别的差异可视为**真实工程配置下的平均额外开销**，而非理论最坏情况。  

**运行时指令（已加载内核后的真实指令）**
运行时 `gdb + /proc/kcore` 反汇编显示（节选）：

`bench_indirect_stable`（或 `bench_indirect_alt2` / `bench_indirect_random`）内层循环：
```asm
mov    0x1262(%rip), %rdx   # 读取 got_fns[idx]
call   *%rdx                # 直接间接调用
```

`bench_direct` 内层循环：
```asm
call   bench_stub_0
```

这说明运行时确实发生“访存 + 间接跳转”。同时 **retpoline thunk 被替换** 为 `call *%reg`，这会显著降低间接调用的额外开销。

**当前 Spectre v2 防护状态（实验时采样）**
```
Mitigation: Enhanced / Automatic IBRS; IBPB: conditional; RSB filling; PBRSB-eIBRS: SW sequence; BHI: SW loop, KVM: SW loop
```
该状态与运行时 `call *%reg` 的观察一致。

**如何避免替换（强制 retpoline）并做对比实验**
目标：让运行时仍走 `__x86_indirect_thunk_*`，测量“严格 retpoline”开销，与当前 `call *%reg` 进行对比。

推荐步骤：
1. 修改内核启动参数（示例）：  
   - `spectre_v2=retpoline`  
   - 或 `mitigations=auto,nosmt`（按需选择）  
   具体参数以当前内核文档为准。
2. 重启后验证：  
   ```
   cat /sys/devices/system/cpu/vulnerabilities/spectre_v2
   ```
   期望显示 `Retpolines` 或类似字样。
3. 用 `gdb + /proc/kcore` 再次反汇编：  
   - 期望看到 `call __x86_indirect_thunk_*` 而不是 `call *%reg`。
4. 运行 `make bench`，记录 cycles/call 与 ns/call。

**对比结果**
- 当前（Enhanced / Automatic IBRS；运行时替换后 `call *%reg`）：见上文 “实测结果（本机）”。
- 强制 retpoline 后：direct / stable / alt2 / randomN（待测）

**注意事项**
- 模块加载需要 root 权限。
- 关闭抢占与中断会增加系统时延，请在可控环境中测试。
- 如果写成 `got_fns[idx]()`，编译器可能做去虚拟化/常量传播；当前实现使用 `READ_ONCE(got_fns[idx])` 保证每次从内存读取。
- 如果你的 toolchain/linker 开启了 ICF（Identical Code Folding），请确认 `bench_stub_*()` 未被折叠到同一地址（否则 alt2/randomN 退化为 stable）。
