# VKSO clocktime experiments

本目录保存用 VKSO 替代 x86-64 原生 vDSO time/getcpu 路径的最终实现、功能验证和
性能实验。它不仅验证 `clock_gettime` 算法共享，还形成了“共享机器码 + 显式运行时
依赖”的机制实例：内核和用户入口执行同一份 global-time reader，而全局快照、
per-MM namespace 数据与用户私有 context 分别管理。

## 功能边界

最终实现覆盖：

- `clock_gettime`、`clock_getres`、`gettimeofday`、`time` 和 `getcpu`；
- realtime、monotonic、monotonic-raw、boottime、TAI 与两类 coarse clock；
- time namespace，以及 TSC、PVClock 和 Hyper-V cycle provider；
- CPU/alarm/dynamic/非法 clock ID 的原生 syscall 或 `k_clock` fallback。

普通 global-time 内核 reader 和用户入口复用同一 shared core。NMI、early-boot、
writer-locked 和 provider failure 等不能安全使用共享状态的路径仍保留私有
timekeeper 读取，不能据此声称旧内核 reader 已被全部删除。

## 状态与执行模型

```text
                   kernel-owned
 timekeeping  ──publish──> vkso_shared_page (global, R--/NX in DSO)
      │                            │
      │ namespace commit          │ shared core reads under seq
      v                            v
 per-mm vkso_mm_page ─────> shared clock/time/getcpu machine code
 (kernel RW alias, user R--)       ^
      │                            │ inject dependencies once
      └─ AT_VKSO_MM_DATA ─> private user entry/context/fallback
```

状态按所有权拆成三类：

1. `vkso_shared_page` 是全局 canonical reader snapshot。timekeeping writer 用 seq
   协议发布，所有内核普通 reader 和用户进程读取同一页。它不是每进程副本。
2. `vkso_mm_page` 属于一个 `mm_struct`，当前 payload 是 `abi_version`、
   `clock_mask`、monotonic offset 和 boottime offset。用户映射只读，内核通过
   `vkso_mm_kdata` 写别名更新。
3. `vkso_context` 与用户入口位于 DSO 私有 wrapper 中，保存当前地址空间有效的
   provider 数据别名和 failure callback。共享代码不硬编码用户地址，也不直接
   发起 syscall。

`MM_data` 不是 process namespace 的通用副本，而是当前 `mm` 所需的最小 time
namespace 视图。root time namespace 的 `clock_mask` 为零；offset 只在 namespace
commit/setns 等语义变化时更新，不随每次 timekeeping update 刷新。

## per-MM 生命周期

- `exec`：`arch_setup_additional_pages()` 创建零填充页面、安装只读
  `[vkso_mm_data]` special mapping，并写入当前 time namespace offset。
- `auxv`：`AT_VKSO_MM_DATA` 暴露该映射的用户虚拟地址，不暴露内核写地址。
- `fork`：新建 `mm` 时显式复制 payload 并在相同用户地址安装新页；共享同一
  `mm` 的线程自然共享该页。
- `setns`/namespace commit：更新已存在页面中的 offset，最后发布 `clock_mask`。
- `exit`/`exec` replacement：随 `mm` 清理页面引用；禁止 `mremap`，并标记
  `VM_DONTCOPY`，避免绕开显式复制逻辑。
- 用户启动：`vkso_user_wrapper_init()` 校验 shared/MM ABI version，从 auxv 取得
  MM_data，再调用 `__vkso_bind_context()` 完成一次性绑定。

对应实现入口：

- 数据 ABI：[`include/vkso/time.h`](../linux-5.15.198-vkso/include/vkso/time.h)
- per-MM 映射与生命周期：
  [`arch/x86/kernel/vkso.c`](../linux-5.15.198-vkso/arch/x86/kernel/vkso.c)
- MM 初始化、复制和销毁钩子：
  [`arch/x86/include/asm/mmu_context.h`](../linux-5.15.198-vkso/arch/x86/include/asm/mmu_context.h)
- auxv：[`arch/x86/include/asm/elf.h`](../linux-5.15.198-vkso/arch/x86/include/asm/elf.h)
- namespace 更新：
  [`kernel/time/namespace.c`](../linux-5.15.198-vkso/kernel/time/namespace.c)
- 共享 reader：
  [`kernel/time/vkso_time_core.c`](../linux-5.15.198-vkso/kernel/time/vkso_time_core.c)
- 用户私有入口和绑定：[`functional/vkso_user_entry.S`](functional/vkso_user_entry.S)、
  [`functional/vkso_user_wrapper.c`](functional/vkso_user_wrapper.c)

## 对通用 VKSO 机制的增量

clocktime 实验验证了下列可推广能力：

- 页对齐内核数据可以通过 `shared_data` 清单作为 `R--/NX` 页复用；
- private ET_REL wrapper 可以携带用户私有状态，并把显式依赖注入共享 text；
- per-address-space 状态可以通过稳定的只读映射和 auxv 发现，而不把地址编码进
  共享机器码；
- 环境差异应在入口或 failure callback 处处理，shared core 只保留共同算法；
- 启动期改写的 thunk/ITS 目标使用通用 `reusable_text` 闭包和逐页映射，不在
  clocktime 路径中继续追加特例。

其中，builder 的 `shared_data`、private wrapper 和 reusable-text 能力是通用项目
机制；当前 per-MM payload、auxv 编号和 namespace hook 仍是时间专用实例。其他
子模块复用该模式时必须重新定义最小只读 ABI，并证明更新协议、生命周期和失败
路径，不能直接共享任意可写内核对象。

## 维护中的验证路径

- `functional/`：用户 ABI matrix、private `libkernel.so` 入口和 namespace/provider
  功能验证。
- `baremetal/`：可复现的四镜像独立 READ 实验。
- `update-bench/`：UPDATE 与 READ/UPDATE CONCURRENT 实验。

最终 READ、UPDATE、CONCURRENT 结果、测量窗口、完整表格与统一解释见
[`VKSO_READ_UPDATE性能报告_20260801.md`](VKSO_READ_UPDATE性能报告_20260801.md)。
历史 milestone 目录和旧结果分析不属于当前维护路径。
