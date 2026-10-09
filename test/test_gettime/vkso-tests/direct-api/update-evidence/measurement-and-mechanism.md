> 当前范围（2026-10-04）：按用户决定停止新增机制实验，撤回待重启验证。三项物理机制作为未识别边界陈述，不再阻塞 Evaluation 整理。见[证据收束与正文取材](../../baremetal/results/paper-clocktime-results-20261002/update-evidence-conclusions.md)；下文历史“下一项”不作为执行指令。

> 新增顺序证据：[匹配fast发布顺序](../../update-bench/mechanism-evidence/fast-order-boot1-review/README.md)完成40窗/79,999条，独立复算及恢复PASS。idle均值/p90有六块同向下降，但布局参照未全部通过；COARSE原始参照漂移。保留响应并停止追加，不能据此命名原双峰原因或完成后端/配置归因。

> 新增计时序列证据：[36窗原位起止对照](../../update-bench/mechanism-evidence/timestamp-sequence-boot1-review/README.md)完成72,000条且独立复算PASS。两端分别产生小幅位置响应，两端同时替换中位数0～+1tick；没有达到预定持续形状响应条件。固定tick区域占比会受小幅平移影响，不能直接视为物理快慢状态占比。停止本候选追加，三项物理解释仍未完成。

> 最新测量证据：[PT扰动对照](../../update-bench/mechanism-evidence/pt-perturbation-boot1-review/README.md)已完成18窗、9,000条。主峰接近但高分位变化，off参照KS=0.12超过预定0.10，停止同类先导。PT阶段占比不能直接解释未跟踪自然分布；两份无OVF窗口也不能替代扰动参照。正式READ与完整发布矩阵不变，三个物理机制问题仍未完成。

# UPDATE 测量与机制证据衔接

分布分解回答“整体差值由哪些统计变化构成”。已完成的匹配记录器实验回答“这些相对变化是否由测量方案改变”。两项证据分别记录。

## 当前完整证据与三个机制问题（2026-10-04）

[两配置完整发布汇总](../../update-bench/mechanism-evidence/full-publication-two-configurations/README.md)
已完成16次独立启动、256窗、511,996周期样本，每后端/记录器/配置两次启动。
Normal与no-retpoline均按固定矩阵停止；功能/共享/恢复与分布核验通过。
[正文候选](evaluation-text.md)现已纳入两配置的32个绝对均值和48个逐块差值，
[新增正文数字核对](full-publication-prose-binding.json)通过，另保留原函数内窗口及其四启动统计。
两种计时范围不能相减来估计复制成本，完整软件路径也不等于存储全局可见延迟。

| 要解释的问题 | 已有直接证据 | 现在能写的解释 | 仍需解决的物理问题 |
| --- | --- | --- | --- |
| 自然多峰如何形成 | 显式业务路径各含快慢样本；原位PMU诊断改变分布；有高侧样本没有记录到RFO miss；计时排序控制的搬移参照改变分布 | 已观察集中区不能一一命名为进位/NTP状态或cache hit/miss；计时排序会影响搬移环境的分布 | 需要在保持原分布的条件下，将特定执行/硬件状态与集中区联系起来，并用干预验证；现有屏障增量不能回填原始成本 |
| VKSO/Raw占比为何不同 | 函数内窗口的四项分解完整还原均值；完整发布两配置有条件成本/区域占比/秩尾部分解；读字段与写指令位置有后端差异；两端节流先导有成本响应 | 低侧成本、占比和尾部可方向相反；RAW/COARSE完整发布的大差值不限于极端尾部；仅静态行数不足以预测成本 | 状态访问位置、实际读取/重试活动和发布次序尚未被单独区分；节流框架和未达目标速率不能支持单一缓存事件归因 |
| 两配置峰位为何不同 | 完整记录器对照显示MONOTONIC相对均值效应在两配置方向相反；Normal COARSE的主峰选择随带宽/启动切换；固定guard/主体/所测布局均未重建历史峰移 | 先区分同一局部峰的位移与最高峰身份切换；记录器影响依赖配置，不能作通用常数抵消 | 配置同时改变缓解选项、代码与部分状态布局，采集时段也不同；尚需能区分这些因素的控制，不能只称为retpoline成本 |

这三个问题允许由不同机制解释，不要求一个因素统一解释所有分布。
完整成本及测量敏感性已有重复证据；物理解释的完成标准是有可区分预测和重复干预支持，
而不是增加相同条件样本或把统计分解改名为物理归因。

[八镜像实际路径审计](../../update-bench/mechanism-evidence/full-publication-config-paths/README.md)已完成。
当前Normal启动的只读指令证明ITS返回路由依赖地址，通知链间接调用实际已改写为call rax；
Normal表示编译配置，不能从CONFIG_RETPOLINE=y直接断言每个调用实际执行retpoline序列。
[随后两个返回位点的原位干预](../../update-bench/mechanism-evidence/publication-return-normal-boot1-review/interpretation.md)
完成40窗、79,997样本，主峰变化在三带宽下均仅−1～+1 tick，没有持续的区域占比候选响应。
idle/COARSE参照通过，MONO/RAW部分参照漂移；各负载完整均值差均有反转，尾部贡献完整保留。
按协议停止同类返回先导，原字节及环境恢复通过。静态路径差异未转化成所求的重复峰位/占比解释。
[阶段覆盖复核](../../update-bench/mechanism-evidence/stage-coverage-audit/README.md)已核对5,000条历史PT调用。
顺序诊断镜像的两次fast调用之间有栈指针读取，当前八份完整发布镜像没有；调用者区间必须单列。
两次fast解码区间均短的样本中仍有大量中央高侧，不能把全部变化归于一个fast目标。
这些是历史诊断中的区间与指令证据，未识别该指令的硬件停顿，也不能直接外推最新完整发布路径。
[原镜像PT技术窗口](../../update-bench/mechanism-evidence/publication-pt-technical-boot1-review/README.md)
已采集1秒、250条并恢复环境；结构上可重建所需调用，但原始PT流含OVF，未通过预定无错误条件。
停止该技术先导，不将其纳入性能或根因论证；下一项先离线核对计时包配置。
后文保留此前阶段记录，其中“尚缺另一配置”和旧执行描述以本节与NEXT_RUN.md为准。

## 完整软件路径与可见性边界（2026-10-03）

[计时排序审计](../../update-bench/mechanism-evidence/publication-ordering-audit/README.md)核对了
Current/Legacy × Raw/VKSO四个no-retpoline镜像的起止控制流边缘。
完整发布计时覆盖复制和最终序列提交指令，但RDTSCP执行路径没有单独保证终点前全部写入
全局可见，起点之后的执行也不能只由控制流顺序推断为严格晚于时间戳读取。
evaluation候选文本已明确这一计时约定；已有数值不改写为远端读者的观察延迟。

[固定地址排序控制两端结果](../../update-bench/mechanism-evidence/publication-ordering-paired-boot1-review/interpretation.md)
已完成88窗、176,000周期样本及独立复算。四个后端/负载的搬移参照均未通过，
终点屏障的后端响应差在两负载下均有块间方向变化。联合决定STOP_SAME_ORDERING_PILOT。
屏障响应不能直接解释原位根因或修补无插桩成本；当前没有新的采集或重启指令。
下文历史阶段中的执行描述以[NEXT_RUN.md](../../update-bench/mechanism-evidence/NEXT_RUN.md)为准。

## 计时范围

当前生产 `kernel/time/timekeeping.c::timekeeping_update` 在已持有 timekeeper_lock 时进入。正式包启用 CONFIG_TIMEKEEPING_UPDATE_BENCH，stage/cache-prep/per-call PMU/business 诊断均未启用，配置记录见 configurations.csv。启用采集时，timekeeping_update_bench_start 读取 rdtsc_ordered；函数完成状态维护、用户可见状态发布、两个 fast timekeeper 更新后，finish 先取结束时间戳，再追加记录。主表覆盖 action=0 的周期更新，不包含锁等待和完整定时中断。

输入为正式 `20260929T040650Z-clocktime-full` UPDATE 数据。后续短复测、旧包和 recorder 控制不参与当前主表。正式运行的源码版本、包及 boot ID 可从 identities.csv 定位。960 个窗口都有可核对的 writer 起止时间；有读者时窗口嵌在已开始运行的读者区间中。

## 新核对的函数外发布工作

[实际镜像审计](../../update-bench/mechanism-evidence/update-dependency-audit/README.md)
覆盖四个正式镜像和接口混合版。周期调用传入shadow_timekeeper；进入UPDATE前已有
序列开始，返回后才复制到tk_core.timekeeper并结束序列。Raw复制280字节、VKSO 264字节，
这些步骤不在现有函数内时间戳之间。此前材料未明确列出这段排除项，现已补正。

现有均值、区间、尾部及记录器敏感性结果均保留，只描述既定函数内计时区间。
字节差不能换算为耗时，也不能认为未计入成本自动抵消。原目标中覆盖最终状态提交的
完整发布成本尚缺相应边界的成对、独立启动性能证据。直接外包时间戳会将现有record追加也包入，
因此补测方案须先处理计时边界和记录位置，再决定上机；当前不发新命令。

[完整发布候选](../../update-bench/mechanism-evidence/full-publication-build/README.md)现已完成
四镜像构建、链接路径和八次QEMU验证。起点在序列开始前，终点在最终复制/序列结束后，
record位于终点之外；仅采样TK_ADV_TICK实际发布。它补齐计时覆盖；[首组配对](../../update-bench/mechanism-evidence/full-publication-pair-boot1-review/README.md)已完成63,997样本，
但仅每后端一次no-retpoline启动，仍缺独立启动重复和新区间记录器敏感性证据。
四负载均值差为+16.932/−91.941/−502.456/−542.012 ticks；新旧结果不直接相减。
[状态访问审计](../../update-bench/mechanism-evidence/full-publication-state-access/README.md)提供候选机制，
尚不解决双峰物理归因。首组先导已停止，后续先固定有区分力的测量和机制控制。

## 新区间记录器对照的最终结果

[八次启动矩阵](../../update-bench/mechanism-evidence/full-publication-recorder-control/step-07-review/interpretation.md)
已完成no-retpoline两后端×两记录器×两次启动，128窗口、255,997样本。独立核验及两块精确复算通过。
计时区间指令序列相同，记录器主体及部分代码/状态地址不同，结果归于整个实现干预范围。

Current−Legacy对VKSO−Raw均值差的变化（idle/mono/raw/coarse）为：
第一块−51.459/+66.804/−72.785/+43.365，第二块−30.250/+31.887/−53.817/−44.996 ticks。
CPU 0子集方向相同；前三负载方向重复，COARSE翻转，其两块平均−0.816不能解释为无影响。
COARSE最低90%贡献从+43.498变为−40.273 ticks，而峰位差变化为+82/+81；三种指标不能互相代替。
逐区域条件成本、占比、完整尾部及图表见最终结果目录。

归档配置、除镜像名外的命令行、诊断开关及tuning快照一致，已监控服务无重启；
未找到唯一物理机制。固定矩阵按协议停止，不追加同条件启动；另一配置和物理解释仍未完成。
历史阶段的执行指令不再有效，当前没有新的原生采集命令。

## 早期干预记录（后续完成状态见下文）

| 证据 | 已观察到的结果 | 与下一步的关系 |
| --- | --- | --- |
| [VKSO recorder crossover](../../baremetal/results/update-recorder-crossover-20260930/README.md) | 保持当前 VKSO 功能，恢复旧 recorder 后，no-retpoline 高侧中央条件中位数回落；切回当前 recorder 后再升高。占比方向没有全部复现 | 已证实测量代码能改变 VKSO 高侧，需要同样控制 Raw |
| [Raw 旧/当前包对照](../../baremetal/results/raw-recorder-crossover-20261002/README.md) | 两次启动均观察到当前 Raw 主高峰低于旧包 | 这是完整版本对照，尚未隔离 recorder 单项影响 |
| [正式采集审阅记录](../../baremetal/results/paper-clocktime-results-20261002/user-review.md) | 正式 UPDATE 存在后台服务重启活动 | 匹配控制中需固定后台运行条件，避免把时段变化归于代码 |
| [现有机制诊断](../../update-bench/BIMODAL_DIAGNOSIS.md) | 业务分支无法唯一对应双峰；缓存和顺序干预有影响 | 分布的低/高侧不能直接命名为业务状态或 cache hit/miss |

## 匹配记录器实验的原始问题（现已完成）

在保持当前 Raw/VKSO 功能版本、公开读者、负载、缓解配置和运行条件不变时，仅切换匹配的 recorder 接口/实现及调用形式，比较：

1. VKSO−Raw 的完整均值差是否变化；同时观察读者负载相对 idle 的变化差。
2. 两后端的峰位差是否变化；使用相同峰定位规则并报告无法分峰的窗口。
3. 高侧占比差和尾部贡献是否变化；给出固定分界与各自谷值的敏感性。

已有 VKSO recorder 控制和 Raw 整包对照不能组成上述完整配对实验。下一轮先固定功能版本并核对 recorder 的匹配差异，再安排交替启动重复。是否需要补正式 UPDATE，以及随后选择何种机制干预，应由这个对照决定。

本轮完成的是正式数据的全成本分解、负载响应和正文材料。双峰根因与无插桩固有成本的验证仍归属于后续任务。


## 2026-10-02 匹配记录器对照补充

[16次启动对照](../../update-bench/mechanism-evidence/recorder-matrix-16-boots/README.md)现已完成。两后端、两缓解配置组、两记录器各两次独立启动，共383,958周期样本。当前−旧记录器的VKSO−Raw完整均值差变化为Normal +0.150～+11.951、no-retpoline +20.793～+31.027 TSC ticks，具体值随负载变化。这些启动级结果直接限制了原有正式UPDATE表的解释：相对成本也对记录器实现敏感，不能仅扣除公共计时开销后称为固有成本。现有正式样本、分布分解和表值均保留，结论必须绑定其插桩条件。

测量敏感性已有匹配重复证据；具体原因仍待验证。新增离线接口编译干预显示，计时结束处向记录器传递tk会改变被测UPDATE寄存器分配和函数尺寸；该结果不等于确定了峰位或双峰的物理原因。后续先分离接口和记录主体，再根据干预结果确定测量方案及是否需要定向重采正式UPDATE。

## 混合版独立重复与当前结论

[混合版两次启动](../../update-bench/mechanism-evidence/interface-hybrid-two-boots-review/README.md)
已完成47,998样本：当前调用接口配旧记录器主体的8个启动×负载主高峰为125–128，
接近旧版125–129，没有复现当前版146–148的启动级主峰移动。但24个窗口中有2个
主峰为147，且boot2完整均值增加2.817～13.894 ticks；因此只能限制接口单独解释，
不能声称整个分布恢复、接口无影响或记录主体的某项访问已被证明为根因。

两次启动等权的混合版−旧版完整均值差为+6.362/+0.223/+4.073/+7.089 ticks；
混合版−当前版为−15.176/−10.421/−7.774/−10.071，依次对应idle/mono/raw/coarse。
逐启动差值、低/高侧条件成本、占比和尾部贡献全部保存。历史启动不是随机同期配对。

当前不追加同条件boot3，不以旧/混合版更低峰位选择“准确”的记录器，也不立即重采
正式UPDATE。自然双峰、后端占比差、配置峰位差分别保留机制缺口；详见
[统一证据状态与停止条件](../../update-bench/mechanism-evidence/mechanism-evidence-status.md)。
现有正式表的解释仍限定为指定插桩条件下的函数内计时成本，不包含锁等待、函数外复制/序列提交和完整定时中断。

## 实测机器码与布局证据

[实测镜像审计](../../update-bench/mechanism-evidence/recorder-layout-audit-v2/README.md)
进一步确认：当前版与混合版的UPDATE符号化指令序列相同，实际代码/数据地址不同；
当前记录器在计时结束后仍检查诊断flag，相关静态元数据分散到三个64字节对齐区域，
旧版/混合版为一个。记录器指令和布局尚未独立控制，不能把这些地址事实解释为缓存事件。
该离线证据缩小了下一项干预的范围，没有新增性能数据或解决自然双峰物理根因。


## 固定地址 guard 控制完成：停止同类追加（2026-10-02）

[完整分析](../../update-bench/mechanism-evidence/guard-control-boot1-review/README.md)覆盖一次
VKSO no-retpoline启动、36窗、71,997周期样本，原指令恢复与模块卸载、
功能/共享/环境检查全部通过；独立原始CSV复算通过。
两个负载的四块基线主高峰均复现140–155范围，去掉额外flag比较/条件跳转后的
B−A主峰差：idle为0/−5/−3/−1、monotonic为−1/−2/−2/−1 ticks。
未达到预设四块同向且各≥10 ticks，因此不追加同类第二次启动。

窗口等权完整均值差为−3.251/−6.966 ticks，但各块差异明显，占比和尾部贡献
完整保留，不据此声称稳定固有收益。该检查不足以在本次条件下单独复现历史
约20 ticks持续峰移；这不是无影响或等价证明，也没有确定自然双峰物理根因。
匹配记录器对照已经证明相对成本对测量实现敏感，接口混合版和本次固定地址
控制进一步限制了单因素解释。元数据/链接布局及交互仍未分离。
当前不要求新的重启/采集，先整理剩余假设及evaluation证据。

## 元数据布局先导完成（2026-10-02）

[完整结果](../../update-bench/mechanism-evidence/layout-control-boot1-review/README.md)
包含42窗、83,998周期样本，无丢样，功能/共享/恢复卸载通过。保留guard、计时函数、
样本缓冲和指令长度，在两个地址位置比较计数/样本指针同一或不同64字节区域。
原版及全部spread参照主高峰复现140–155；16个块级compact−spread峰移为−5～+5 ticks，
两个负载均未达到预定同向且各≥10 ticks条件，停止同类第二次启动。

四块等权均值差（位置0/1）为idle −6.847/−10.246、monotonic +6.833/−0.927 ticks。
四组对照的逐块方向均有变化，条件成本、占比与尾部的完整分解已经保存。
主分析保留1条CPU 2样本；原分析器CPU 0断言未修改，使用单独复核入口披露偏移，
独立原始CSV复算通过，CPU 0子集不改变任何峰位或停止决定。
本次与guard来自同一boot ID，不能作为两次独立启动。

该特定地址关系的干预未复现历史约20 ticks持续峰移；结果不是所有布局无影响的证明。
其他代码/状态布局及交互、自然多峰、后端占比与配置峰位的因果解释仍未完成。
当前没有新的上机命令，也不据此自动重采正式UPDATE。

## 固定入口记录主体先导完成（2026-10-02）

[完整报告](../../update-bench/mechanism-evidence/record-body-control-boot1-review/README.md)
新增36窗、71,996周期样本，全CPU 0、无丢样。当前入口及状态地址不变，仅放回重定位的旧主体。
原版四块和装载前后参照均复现140–155 ticks，八块旧主体−原主体主峰差为−3～+3 ticks；
所有旧主体窗口的主峰仍在145–151。按预定规则STOP_SAME_BODY_PILOT，不追加同类启动。

完整均值差idle −3.528、monotonic −7.027 ticks，逐块方向均有变化，
占比项分别−3.974/−5.547，完整条件成本和尾部分解已独立复算。
当前整体布局中，旧记录主体单独未复现历史约20 ticks持续移动；这限制了主体充分性的解释，
不能据此认定其他链接布局就是根因。与guard及元数据先导来自同一boot ID，三者不是独立启动，
也不能跨实验时段相减归因剩余指令成本。当前无新的采集命令，不自动重采正式UPDATE。
