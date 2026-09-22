# §6.4 public-direct-v1：直接链接时间接口

基线：43c60fc68a6ec6bed5b8131927f7c17100b2f20c。主矩阵只有 Raw/VKSO × Normal/no-retpoline 配置族。共享时间核心、carrier 汇编入口、namespace 数据页和内核映射机制未修改；没有修改 libc。

## 接入约定

Raw 使用原生 libc 的 clock_gettime 等入口，由 libc 选择内核 vDSO。VKSO 应用包含 vkso_time.h，链接 functional/vkso_user_wrapper.c 与已注册的 libkernel.so，使用 vkso_clock_gettime 等显式入口。没有额外 adapter.so、LD_PRELOAD 或逐次 dlopen/dlsym/provider 分派。公开头文件只适配返回值；计算体仍在 carrier 中。

调用 vkso_time_init() 并检查成功后才能使用接口；初始化必须早于 reader 线程创建，不支持并发重新绑定。页面注册必须在任何共享范围被访问前完成，且保持到所有消费者退出。初始化和注册不计入稳态调用成本。time() 的负秒数不被转换成 errno。

```c
#define _GNU_SOURCE
#include <stdio.h>
#include "vkso_time.h"
int main(void) {
    struct timespec ts;
    if (vkso_time_init() || vkso_clock_gettime(CLOCK_MONOTONIC, &ts)) {
        perror("VKSO time");
        return 1;
    }
    printf("%lld.%09ld\n", (long long)ts.tv_sec, ts.tv_nsec);
    return 0;
}
```

在 vkso-tests 目录的链接示例：

```sh
gcc -O2 -std=gnu11 -Ipublic-api -Ifunctional app.c \
  functional/vkso_user_wrapper.c -L"$PACKAGE" \
  -Wl,--no-as-needed -lkernel -Wl,-z,now -o app
# 仅在匹配 carrier 已注册且保持有效时运行：
LD_LIBRARY_PATH="$PACKAGE" ./app
```

这是显式库接入，需要应用改用上述入口并重新链接；不是既有二进制的透明 libc/vDSO ABI 替换，也不是共享核心的静态复制。

## 本地自测

```sh
python3 -B test/test_gettime/vkso-tests/public-api/tests/test_public.py
```

无需 sudo，不安装内核、不执行仓库模块。测试使用普通用户态 mock_core.c 和原有真实汇编 veneer，只验证调用约定、errno、初始化和失败出口。mock 不能作为生产 carrier，打包器会拒绝它。模拟管理命令不执行任何实际 grafting。

Native 检查使用运行机器实际 libc/vDSO。若宿主 CLOCK_REALTIME_ALARM 返回 EINVAL，该项明确标记 SKIP；目标正式采集仍要求完整 17 条路径，不能用 --api 的局部结果代替。

## 目标构建与启动

使用原来可以构建四镜像的 GCC 11.4.0 环境及完整仓库。目标构建不能用本地其他 GCC 的通过来代替。先提交修改；或至少 git add 新文件，使候选源码身份包含它们，构建后不再修改源码。

```sh
cd test/test_gettime/vkso-tests/baremetal
export NORMAL_PACKAGE="$PWD/artifacts/public-direct-normal"
export NO_RETPOLINE_PACKAGE="$PWD/artifacts/public-direct-no-retpoline"
CC=gcc-11 ./build-all.sh
```

仍由现有 build-images.sh 生成内核/carrier，再由 public-api/build.py 在新的 .building-* 暂存包中生成两种用户程序。旧完成包不原地升级。打包保存源码、编译器、选项、符号/反汇编审计和校验和；要求两个 mitigation 包的用户程序逐字节相同。新 VKSO 程序必须 DT_NEEDED libkernel.so；Raw 不能依赖它。Redis 与 adapter 构建已移出主流程，旧代码和数据仍保留。

内核安装/GRUB/重启沿用原脚本，必须由目标机操作者明确执行，不属于本地自测。安装后，先开始一个完整启动块：

```sh
PUBLIC_BLOCK=0 ./experiment.sh begin public-direct-block-00
./experiment.sh status
# 按 next_case 明确执行 experiment.sh boot / collect。
# boot 是会重启机器的操作；不要当作普通自测命令。
```

每个块包含四个独立启动。后续以 PUBLIC_BLOCK=1、2、3 开始新 RUN_ID；四块在位置和相邻次序上平衡。增加的是独立重复，不是第五种实现。四次启动/配置只是一个平衡起点，不是精度保证。begin-normal 只供诊断，正式汇总需要全部四组。

原镜像/配置/UTS/clocksource/CPU isolation/ABI matrix 检查继续保留。原 collector 的调频设置和 irqbalance 管理仍存在；新代码不绕过这些受控环境要求。只在实际目标启动下采集。

正常完成和可处理的失败执行恢复；replace 尝试即被标记，避免忽略部分失败。restore 失败不再卸载 backing 模块。若收到信号时子操作可能仍在执行，则不贸然恢复或卸载，输出 incomplete 并要求停止消费者后人工恢复。SIGKILL、断电和内核崩溃也必须按原管理流程恢复。不要并行启动另一 manager/collector。只有清理成功后才产生外层 complete 标记。

## 测量与验证分离

17 条公开调用路径覆盖七种 global clock_gettime、process CPU/realtime alarm 回退、三种 clock_getres、gettimeofday(tv,NULL)、time(NULL/pointer)、getcpu(both/null)。不测 libc 非空约定之外的 gettimeofday(NULL,...)。回退是同一 API 实现中的参数路径，不新增第三个 backend。

每条批次是完整公开调用的平均成本。外层 RDTSCP/LFENCE 和编译器 memory clobber 包围整批；检查 invariant TSC/RDTSCP、固定 CPU、记录两端 TSC_AUX。单位是 elapsed TSC ticks/call，CSV 的 tsc_cycles 字段不代表实际 core cycles。批次尾分位数不能写成单次调用尾延迟。

计时包括公开入口、返回约定转换、循环、返回状态 OR、一次 loop 调用和最终 sink 写入；后两者按批量摊薄，不扣减估算成本。计时不包括装载、初始化、预热、输出。批内没有逐次计时器或 provider 分派。保持正常时间更新；迁移、错误或异常计数会保留记录并使采集失败，不筛选到有利样本为止。

--check 与 --check-fastpath 在独立进程运行，后者拒绝时间 syscall，并先用强制 syscall 做正向控制。性能进程不继承 seccomp。功能通过与物理页身份不是同一证据。

## 输出和汇总

新数据位于 RUN_ID/CASE/public/：public.csv、逐进程记录、检查日志、含 boot_id 的 manifest、完整 source.patch/构建源码及校验和。package-SHA256SUMS 描述原包；SHA256SUMS 校验本结果目录。旧 probe/ABI matrix 保留用于验证，不将原 v3 数据改名。

```sh
python3 ../public-api/summarize.py \
  results/public-direct-block-00 results/public-direct-block-01 \
  results/public-direct-block-02 results/public-direct-block-03 --out public-summary
```

汇总拒绝重复 boot、损坏结果、不完整参数矩阵、未成功清理的目录、缺失配置或混合构建口径。先取 boot 内批次中位数，再汇总独立 boot；VKSO/Raw 成本比大于 1 表示 VKSO 较慢。不把 31 批次当作 31 次独立启动，也不宣称已证明性能等价。

## 仍需目标机验收

本地测试不是 Linux 5.15.198 真实 grafted VKSO 验收。需要目标 GCC 11.4.0 构建、四种启动下完整 API/路径验证、实际代码页身份和 namespace/fork/exec 检查。原内核 reader/publisher 的两端评价仍是完整 RQ4 的独立证据，本次新的用户 READ 流程没有替代它们。Redis 旧计时问题未修复，因为它已退出本轮主实验。
