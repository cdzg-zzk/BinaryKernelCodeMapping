> 最新写作范围（2026-10-04）：采用“精炼正文＋完整附录”。正文约2,500个汉字，以真实有状态案例的选例理由、三项改造、跨域共享和维护证据、改造后的性能组织论证；保留两表两图。附录C保存完整接口、源码/二进制规模、功能验证、38项READ对照、UPDATE启动统计与记录器对照。双峰归因和机制排查保留在实验档案，不作为论文讨论任务。

> 正文落地：完整 Clocktime 小节、图表及附录C已整合到[主稿](../../../../../../paper/paper_content/Paper%20Draft.md)，[数值核对](clocktime-manuscript-check.json)通过；写作覆盖见[交接入口](evaluation-handoff.md)。

> 当前范围（2026-10-04）：按用户决定停止新增机制实验，撤回待重启验证。三项物理机制保留在探索档案，Evaluation 聚焦已实现的设计及所测效果。见[证据收束与正文取材](update-evidence-conclusions.md)；下文历史“下一项”不作为执行指令。

> 2026-10-04新增：[匹配fast顺序先导](../../../update-bench/mechanism-evidence/fast-order-boot1-review/README.md)完成40窗/79,999条及独立复算。idle顺序响应的均值/p90同向，但布局参照有失败块；COARSE原参照漂移。按协议停止，保留全部响应，三项物理解释仍未闭环。

> 2026-10-04新增：[计时序列原位对照](../../../update-bench/mechanism-evidence/timestamp-sequence-boot1-review/README.md)完成36窗/72,000条，恢复及独立复算PASS。起点/终点的小幅位置响应不能直接解释为双峰占比变化；无预定持续形状响应，按协议停止。正式READ/UPDATE结果不变，三项物理机制问题仍未完成。

> 2026-10-04新增：[PT测量扰动证据](../../../update-bench/mechanism-evidence/pt-perturbation-boot1-review/README.md)完成18窗/9,000条及独立复算。参照稳定条件未通过，trace高分位变化而主峰接近；停止用PT阶段占比外推自然双峰。此结果补充测量可靠性说明，不替代尚缺的三项物理解释，也不触发正式READ/UPDATE重采。

# Clocktime 案例：正文目标、已有证据与补齐工作

> 当前正文取材入口：[七项交付与证据审计](evaluation-handoff.md)。本次从原CSV复算全部9,424个READ批次与511,996条完整发布样本；源码切片与PFN记录同步核对通过。完整发布矩阵作为UPDATE成本主材料，旧函数内结果单列。三项物理机制仍未完成。

## 正文论证目标

以 clocktime 为案例，评估 VKSO 能否将普通内核读取与用户读取的共同计算集中到同一份内核驻留代码，减少两侧重复实现与维护，并量化为此承担的适配、发布、映射与性能成本。代码行数衡量实现规模；开发职责和修改范围衡量维护结构，不等同于工程工时。

正文包含：实现与接口范围；功能及物理共享证据；实现规模与维护职责；用户/内核 READ；UPDATE；双峰与测量可靠性解释。双峰是解释性能的证据问题，不替代上述核心目标。

## 当前证据状态（2026-10-04）

[Normal完整发布最终结果](../../../update-bench/mechanism-evidence/full-publication-recorder-normal/step-07-review/interpretation.md)
已完成8/8启动、128窗、255,999周期样本；736项归档、原CSV、32条完整ECDF、96项峰位及功能/共享/恢复核验通过。
四负载记录器相对均值效应在两块均为负，RAW/COARSE的最高1%贡献均抵消负效应；COARSE主峰选择对带宽和启动敏感。
[两配置合并材料](../../../update-bench/mechanism-evidence/full-publication-two-configurations/README.md)
覆盖16启动、256窗、511,996样本，逐启动成本、后端差、记录器效应及跨配置描述性差值已保存。
Normal的MONOTONIC记录器效应两块为负，no-retpoline两块为正；不能作为跨配置共同常数抵消。
两项矩阵均按协议停止，没有新的重启指令；clean READ与已停止机制先导保留。
UPDATE正文候选已整合两配置表格与分布解释，[80个新增表内数值及关键结论](../../../direct-api/update-evidence/full-publication-prose-binding.json)核对通过。
三个机制问题的证据边界已整理；八镜像调用/返回审计及当前启动只读指令核对已完成。
[原位返回控制](../../../update-bench/mechanism-evidence/publication-return-normal-boot1-review/interpretation.md)
完成40窗、79,997样本：三带宽峰差均−1～+1 tick，没有持续区域占比候选响应，按协议停止并恢复。
[阶段覆盖复核](../../../update-bench/mechanism-evidence/stage-coverage-audit/README.md)已完成5,000条PT配对与调用者边界核对。
历史顺序诊断有当前八镜像不存在的栈指针读取，不能沿用单一fast目标定位解释最新完整发布。
[原镜像PT技术窗口](../../../update-bench/mechanism-evidence/publication-pt-technical-boot1-review/README.md)
完成1秒、250条采集及恢复，但原始流有OVF，未通过无错误条件，停止同方案并转入离线计时包核对。
这项技术窗口不作为性能或根因证据；完整矩阵和阴性干预尚不能替代物理解释。
随后MTC周期3→6的[单字段技术窗口](../../../update-bench/mechanism-evidence/publication-pt-mtc6-boot1-review/README.md)
使AUX流量由19.73 MB降至4.96 MB，但仍有OVF，按协议停止；下一项离线审核错误之外的局部证据有效性。

下表为当前交付状态。后文按时间保留的准备记录和“下一项”描述不再作为执行指令。
[完整发布记录器矩阵](../../../update-bench/mechanism-evidence/full-publication-recorder-control/step-07-review/interpretation.md)
已完成8次不同启动、128窗口、255,997周期样本；独立复算通过，固定矩阵按协议停止。
前三负载的记录器相对均值效应方向在两块重复，COARSE为+43.365/−44.996 ticks、方向翻转；
不能以其平均−0.816 ticks声称测量无影响。完整图表和分布贡献已保存。
矩阵后的[顺序及读取器审计](../../../update-bench/mechanism-evidence/full-publication-sequence-audit/README.md)
已复核128窗、1,024分段：剔除前5%/10%不消除COARSE翻转；读取器采集中不逐批输出CSV。
[计时替换表审计](../../../update-bench/mechanism-evidence/full-publication-timestamp-audit/README.md)
确认四镜像八处替换项；启用RDTSCP时，Legacy VKSO跨行的是含填充位置，并非三字节计时操作码。
当前step-07同启动的[实际读数](../../../update-bench/mechanism-evidence/full-publication-timestamp-audit/runtime-read.json)
已确认起止计时均为RDTSCP及两字节NOP、记录缓冲区按4 KiB对齐。
其他历史启动的运行时字节未留档，这些证据用于缩小解释范围，不作为物理根因结论。
[缓冲索引筛查](../../../update-bench/mechanism-evidence/full-publication-buffer-phase/README.md)
保留全部样本，mod4分组复原主均值；跨启动关联变化、页边界代理样本稀疏，未形成统一物理解释。
[起点布局原生控制](../../../update-bench/mechanism-evidence/start-layout-boot1-review/interpretation.md)
已完成40窗、79,992样本及独立复算；两个同页位置的C−B主峰差在三个带宽下仅−2～+1 ticks，
未复现持续大幅峰移。COARSE第六块搬移参照CDF距离0.1185超出预定门槛，
按协议停止同类追加。完整均值/占比/尾部变化保留，不把主峰稳定写成分布等价。
本次与矩阵step-07同启动，不增加独立启动数；不替代双峰根因或Raw/VKSO性能证据。

[共享状态写入审计](../../../update-bench/mechanism-evidence/full-publication-write-footprint/README.md)
补齐六镜像的168处静态发布写指令，GNU独立解码通过。同后端的目标偏移/宽度集合跨所查
配置及记录器不变；静态写指令数或行数不能直接解释动态成本，亦不替代物理事件证据。

[完整API读取压力两端结果](../../../update-bench/mechanism-evidence/reader-cadence-paired-boot1-review/interpretation.md)
已完成40窗、80,000周期样本及独立复算，无丢样。两端400-tick档均只达到目标速率约75.5%，
联合判定RATE_TARGET_NOT_MET，停止该参数方案，不改门槛或追加同方案独立启动。
慢档完整均值四块下降Raw 65.346～84.353、VKSO 12.802～19.210 ticks；主峰差均−1～0。
后端响应差为+48.792～+66.434 ticks，仅为不同后端启动的描述性比较。
两端实际速率、原读取器/框架差异、区域贡献及完整尾部保留，物理根因尚未识别。
VKSO与矩阵step-07同启动；每端四窗口块不算四次独立重复。

[发布计时排序审计](../../../update-bench/mechanism-evidence/publication-ordering-audit/README.md)
核对四镜像的软件发布边界，并结合Intel指令契约区分：完整软件路径覆盖不等于
全部写入已全局可见，也不等于用户读者已经观察到新版本。
当前RDTSCP方案没有单独保证终点前存储全局可见，起点后执行排序也不能只由控制流推定。
这是测量解释边界，尚无动态重叠量或双峰根因证据；原始数据和停止决定不变。

[固定地址计时排序两端结果](../../../update-bench/mechanism-evidence/publication-ordering-paired-boot1-review/interpretation.md)
完成88窗、176,000周期样本，独立复算、功能、VKSO物理共享及恢复卸载通过。
四个后端/负载的搬移参照均未通过；联合决定STOP_SAME_ORDERING_PILOT，不追加同类启动。
终点屏障改变分布及相对均值，其后端响应差在idle和COARSE下都发生块间方向变化，不能视为共同常数。
该证据未识别原位多峰物理根因，也不能将屏障增量直接补作无插桩成本。
Raw与前项读取压力同启动，VKSO为新的独立启动；同启动四窗口块不算四次独立重复。

[UPDATE正文候选](../../../direct-api/update-evidence/evaluation-text.md)已补入完整发布矩阵小节，
分别呈现两种计时范围、逐块后端差、记录器相对效应、COARSE翻转与分布贡献，并提供对应图注。
新增表格24个差值及峰位/分位秩事实已与矩阵CSV逐项核对；物理机制未写成已解决。
该正文候选现也纳入起点布局控制的两段结果，40窗、79,992样本、峰差−2～+1 ticks、
均值差和COARSE参照未通过事实均已[逐项绑定](../../../direct-api/update-evidence/start-layout-prose-binding.json)。
读取压力先导的两端结果目前单列于内部证据材料，未作为正式后端成本表。


| 正文内容 | 已完成、可定位的材料 | 可以支持什么 | 剩余限制/工作 |
| --- | --- | --- | --- |
| 共同计算与职责 | [职责图与接口分类](../../../code-size/current-evidence/README.md)、mechanism.mmd、interfaces.csv、实际转移指令 | 用户及8个纳入范围的普通内核入口共用计算；另3个入口仅读共享状态；适配、发布、生命周期分别维护 | 不能扩展为全部内核时钟接口均共用计算 |
| 同功能规模与适配成本 | [源码及实际构建规模表](../../../code-size/current-evidence/tables.md)、逐行/逐符号清单 | 功能切片Raw 1,487/VKSO 1,624行；计入所列保留切片为1,578/1,771。集成改动账另为新增1,477/删除340/净增1,137 | 公平规模对照已补齐；不支持总体代码减少，行数不代表工时 |
| 维护简化案例 | [真实提交与等价验证](../../../code-size/current-evidence/maintenance-validation.json)、maintenance-aa1855e.patch | aa1855e修改共同cycle-delta helper及调用位置，2个生产函数；两侧适配/发布无需同步修改；100,100组输入等价 | Raw vDSO已有该特化，不能说同任务Raw必改两份；没有工时或效率百分比 |
| 功能语义与实际共享 | [当前证据包](../../../code-size/current-evidence/README.md)、8次VKSO裸机启动的机制/PFN记录及接口覆盖表 | 公开API、选定快路径、ABI/namespace/生命周期在已测范围通过；所记录共享text/data页的用户/内核PFN一致 | 裸机TSC、主机夹具及其他环境证据分开；PFN不单独证明每个接口的执行路径 |
| READ性能 | [完整READ证据](../../../direct-api/read-evidence/README.md)：16启动、38项对照、9,424批次、启动统计和图表 | 七类用户clock_gettime中位差−1.006～+1.006、三类内核READ −2.728～+1.087 TSC ticks；逐接口成本/区间齐全 | clean READ已完成并保留；不无界地称“可忽略” |
| 原函数内UPDATE成本与分布（历史计时范围） | [原函数内UPDATE证据](../../../direct-api/update-evidence/README.md)：16启动、960窗、3,599,774样本及逐启动四项分解 | 当前插桩下函数内计时区间的完整样本均值差：Normal −10.521～+5.438、no-retpoline −6.914～+9.554 ticks；条件成本、占比、尾部已量化 | 不包含锁等待、函数外序列开始、后续正式timekeeper复制/提交和完整timer interrupt；完整发布已由下方两配置矩阵覆盖。该函数内表不能称整个发布或无插桩固有成本 |
| 完整发布成本先导 | [Raw/VKSO首组配对](../../../update-bench/mechanism-evidence/full-publication-pair-boot1-review/README.md)：32窗、63,997样本；计时覆盖序列开始、UPDATE、正式复制与最终提交 | no-retpoline的idle/mono/raw/coarse均值差分别为+16.932/−91.941/−502.456/−542.012 ticks；RAW/COARSE的大差值主要来自常见样本，最高1%贡献约−7 ticks | 该先导每后端一次启动；两配置记录器对照及重复已由下行矩阵补齐；不能与旧窗口相减估计复制成本 |
| 测量可靠性 | [16启动匹配记录器矩阵](../../../update-bench/mechanism-evidence/recorder-matrix-16-boots/README.md)：383,958样本 | 记录器切换使VKSO−Raw完整均值差变化Normal +0.150～+11.951、no-retpoline +20.793～+31.027 ticks；相对成本也受测量实现影响 | 旧函数内窗口的匹配对照已补齐；新区间两配置各八项已完成，配置依赖性与COARSE变化见下行。历史启动非同期随机配对，不能选择更低记录器为“真值” |
| 完整发布成本与记录器对照（当前UPDATE成本主材料） | [两配置完整结果](../../../update-bench/mechanism-evidence/full-publication-two-configurations/README.md)：16启动、256窗、511,996样本；逐启动成本、分布及对照图齐全 | Normal四负载D两块均为负；no-retpoline的idle/RAW为负、MONOTONIC为正、COARSE翻转。记录器改变相对均值、峰位及区域占比 | 每单元两次启动，描述性比较；多缓解选项和不同时段，不是单一retpoline因果效应。完整软件路径不等于全部存储全局可见。整体记录器及布局干预，不提供无插桩成本或唯一物理机制 |
| 双峰/峰移解释 | [机制汇总](../../../update-bench/mechanism-evidence/mechanism-evidence-status.md)、两启动混合版及三项固定镜像控制，[最新主体结果](../../../update-bench/mechanism-evidence/record-body-control-boot1-review/README.md) | 业务路径不足以划分快慢；接口单独未复现持续峰移；guard、计数/指针布局、整个旧主体的峰移分别−5～0、−5～+5、−3～+3 ticks，均未达到预定重复门槛 | 三项固定镜像控制同一启动；主体在当前布局中单独不足以复现历史峰移，其他布局及交互仍未排除。自然多峰、后端占比差和配置峰位差仍无物理解释 |
| 资源代价 | [1/8/32进程资源表](../../../code-size/current-evidence/tables.md)、resource-pages.csv | 共享页与额外私有映射分开报告，披露实际记录的物理页规模 | Raw vDSO本来跨进程共享；vvar未记录present PFN不代表无状态页；不能据此声称总内存更少 |

当前主要未闭环部分是UPDATE物理机制归因及其正文解释。两配置完整发布与记录器敏感性、
每单元两次独立启动已补齐；Normal四负载D方向重复，no-retpoline COARSE仍翻转。

公平代码对照、维护案例、READ启动统计和UPDATE分布分解均已完成。
[计时依赖与边界审计](../../../update-bench/mechanism-evidence/update-dependency-audit/README.md)核对四个正式镜像：
函数返回后Raw还复制280字节、VKSO复制264字节并提交序列，现有函数内样本不覆盖这些步骤。
不能将复制字节数转换为耗时或把现有数值扩展为整个周期发布成本。
[完整发布候选](../../../update-bench/mechanism-evidence/full-publication-build/README.md)
已完成两后端、两配置的隔离构建、链接控制流检查与八次QEMU功能验证，覆盖最终复制和
序列提交，record追加在终点之后。四项有效配置与正式实验一致；
首组原生先导已固定，不自动重采整矩阵。
[完整发布首组配对](../../../update-bench/mechanism-evidence/full-publication-pair-boot1-review/README.md)已完成32窗、63,997样本，
四负载VKSO−Raw均值差为+16.932/−91.941/−502.456/−542.012 ticks；
RAW/COARSE差值主要来自常见样本，最高1%贡献约−7 ticks。每后端仅一次no-retpoline启动，
该先导单独不足以证明重复性；后续no-retpoline八次矩阵已补记录器对照与重复，物理机制仍缺。
完整发布结果单列，不并入原函数内正式表。
[共享状态访问审计](../../../update-bench/mechanism-evidence/full-publication-state-access/README.md)补充布局候选证据，尚非缓存事件归因；本组按协议停止采集。
[新区间匹配记录器控制](../../../update-bench/mechanism-evidence/full-publication-recorder-control/README.md)
已完成两个旧记录器镜像、整树源码配对、链接布局审计、4次QEMU功能/采样生命周期和
5项离线编排/分析检查。计时区间指令序列相同，函数及部分状态地址不同，效应须解释为
整个记录器实现及其布局变化。两块共8个启动项按固定顺序执行；
八项已全部完成，样本共255,997条，第一块与第二块独立列示；step 0与先导同启动，不合并为独立重复。
两块记录器相对均值变化见上表，COARSE最低90%贡献也翻转，不能只归于最高1%尾部。
736个归档文件与原CSV复算通过；完整密度、ECDF和两块对照图已完成。
归档配置和已监控后台服务检查未找到唯一物理原因；按协议停止本矩阵，不追加第三次启动。
[剩余布局假设的离线审计](../../../update-bench/mechanism-evidence/metadata-reference-audit/README.md)
记录了可控制项和现有混杂；布局先导新增83,998周期样本，完整分布分解和独立复算已完成。
1条CPU 2记录保留，敏感性不改变停止决定；该结果限制所测地址关系解释，不证明所有布局无影响。

当前源码规模证据与clean READ campaign绑定 cf9dc817f29f9c8d6f88dde0c58c4ccb75347aeb。后续完整发布及机制控制使用各自封存的构建产物和运行时修改记录，不能用共同基础提交替代实际镜像身份核对。旧七月/八月功能 SLOC 百分比、binary-evidence.csv 和历史机器码等价说明不能未经对应构建核对就移入主表。CHANGE_AUDIT/ARCHITECTURE_AUDIT 等文档中仍有早期性能 NOT_RUN 描述，判定执行状态应依据实际 campaign 和构建身份。

## 代码规模的计数边界

当前实现分为共享计算及 ABI；内核适配与系统调用边界；用户适配、初始化与头文件；状态发布；MM/time namespace；provider；构建与平台接入。通用 VKSO 设施、保留的 Linux 依赖、测试及插桩分别披露。

494 行 shared_core 包含 ABI、provider 和 getcpu，不是纯时间算法。393 行用户实现包括 255 行实现及 138 行头文件，不能与不含对应状态头及初始化的 406 行 Raw vDSO 执行切片直接计算缩减百分比。当前 +1137 是源码变更账，不是两种方案的同功能代码总量。额外删除 vDSO/兼容平台功能不应计为等功能算法节约。

## 补齐顺序与完成标准

1. 离线：固定正文问题及计数边界；生成当前构建的同功能源码/二进制规模对照和职责分配。完成标准：每个数值可定位对应版本、范围与类别，能够独立描述适配成本和共享计算，不引用旧百分比。
2. 离线：汇总当前功能/PFN/资源证据；补 READ 启动级统计及 UPDATE 各侧条件成本、占比、尾部贡献和逐启动图。完成标准：解释整体差值由什么分布变化构成，阈值敏感性不隐藏，无法分峰时不强行套入两个状态。
3. 定向目标机：补匹配记录器对照，判断测量变化是否改变 VKSO−Raw 的相对结果；固定实际运行环境。完成标准：验证相对差值、峰位差及占比差对测量方案的敏感性；不能凭更低高峰选择“更准确”的记录器。
4. 机制：由匹配对照结果选择能够区分剩余原因的干预。分别解释双峰形成、VKSO/Raw 占比差及两配置峰位差。完成标准：原因有干预和重复证据；若仍未识别，保留明确的机制缺口，不称为必然双峰。
5. 最终 UPDATE：测量方案通过上述检查后，有必要时以固定方案补齐完整四组合、四负载、每组合四次独立启动。READ 现有 clean 数据保留，诊断与旧结果单列。完成标准：形成版本一致、测量边界明确、带启动级不确定性的正式比较；未识别根因不能用于推导固有成本。

最终正文交付：职责/调用路径图；同功能实现规模与适配成本表；功能/物理共享证据摘要；分配置用户与内核 READ 结果；UPDATE 成本及分布结果；双峰和测量可靠性说明；与证据一致的结论。

## 工作 1、2 的论证口径与执行边界（2026-10-02 核对）

本节明确前两项工作的对象、证明方法、已核对事实和完成标准，供后续补证与写作使用。当前阶段先处理这两项，性能分析另行开展。下文保留计数与证明口径；执行结果见末尾完成状态及当前证据包。

### 工作 1：证明共享对象，并划清实现职责

目的：回答“用户与内核共同执行什么、哪些工作仍分属两侧”。这决定工作 2 的计数边界，也避免把共享计算、状态发布和领域适配混为同一种收益。设计/实现章节说明机制，evaluation 用调用路径和实际映射证据验证机制。

当前源码根为 `test/test_gettime/linux-5.15.198-vkso/`，项目用户入口根为 `test/test_gettime/vkso-tests/`。本次所读生产源码的 Git diff 相对 `cf9dc817` 为空；已有变更账的 `audit_changes.py --check` 本次再次 PASS。

| 职责 | 当前源码及函数证据 | 需要形成的说明 |
| --- | --- | --- |
| 共同读取计算 | `kernel/time/vkso_time_core.c` 的 `vkso_clock_gettime_hres/coarse`、`vkso_read_hres_time`；`vkso_time_internal.h` 的 `vkso_read_begin/retry`、`vkso_cycle_delta`、`vkso_apply_offset`、`vkso_read_coarse` | 序列快照与重试、周期换算、归一化和 namespace offset 的共同实现位置 |
| 用户适配 | `functional/vkso_user_entry.S` 的 `__vkso_clock_gettime`；`direct-api/vkso_public.c`、`vkso_time_init.c`；`functional/vkso_user_wrapper.c` | 分类 clock ID、注入 MM_data/context、初始化、公开 ABI/errno 和 syscall fallback；用户适配中无另一份周期换算/序列重试实现 |
| 内核适配 | `include/linux/vkso_time.h` 的 `vkso_time_get_root_hres/coarse`；`kernel/time/timekeeping.c` 的普通读取入口；`kernel/time/posix-timers.c` 的动态分派 | 固定时钟绑定 root 语义、结果类型转换；动态 POSIX 入口使用当前 MM_data；保留内核完成式 fallback |
| 全局状态发布 | `kernel/time/timekeeping.c` 的 `tk_set_read_base`、`tk_publish_read_state` | timekeeper 派生共享读取状态，并用序列协议发布；发布职责与读取计算分列 |
| namespace 和生命周期 | `arch/x86/kernel/vkso.c` 的 `vkso_install_mm_mapping`、`vkso_dup_mmap`、`vkso_destroy_context`、`vkso_time_join_namespace`、`arch_setup_additional_pages` | 安装只读 MM_data 映射，维护引用，切换 namespace backing 并失效旧 PTE；这些函数负责 MM_data，不等于通用共享代码页注册设施 |
| 保留路径 | `vkso_timekeeping_get_private`、NMI/fast、持锁等特殊读取路径；例如 `ktime_get_coarse_with_offset` 仍读取 timekeeper | 共享范围按接口逐项标明，不能概括为全部 `ktime_get*` 都执行共享核心 |

已核对的代表路径：

```text
Raw 用户：vDSO do_hres / do_hres_timens -> vdso_calc_delta -> vvar
Raw 内核：ktime_get / ktime_get_real_ts64 -> timekeeping_get_ns -> timekeeper

VKSO 用户：clock_gettime -> __vkso_clock_gettime
                           -> 注入 MM_data / 用户 context ─┐
                                                        ├-> vkso_clock_gettime_hres
VKSO 内核：ktime_get -> vkso_time_get_root_hres ───────────┘   -> vkso_read_hres_time
                          绑定 NULL MM_data / 内核 context    -> 共享读取状态

发布：timekeeper -> tk_publish_read_state -> 共享读取状态
provider 不支持：共享入口 -> 对应 context callback -> 各领域 fallback
```

Raw 路径已从缓存的上游 Linux 5.15.198 源码核对。两侧是不同的读取实现，但仍可能使用共同数学/provider helper；不能将所有 Raw helper 都算作两份。

物理证据：`../20260929T040650Z-clocktime-full/block-01` 至 `block-04` 下两种 VKSO 配置的 `read/vkso-*/sharing.json` 共 8 份。逐份查看的全部已记录 text/shared_data 页均为 `user_pfn == kernel_pfn`。PFN 证明所记录映射的物理身份；是否调用这些页上的共享入口，还需与该构建的调用/链接路径和已有快路径验证一起呈现。PFN 本身不证明每个接口都进入共享代码，也不证明总内存减少。

完成产物：一张 Raw/VKSO 对照路径图、一张职责与接口覆盖表、与当前构建对应的物理共享证据摘要。接口表分别标明“执行共享核心”“仅直接读共享状态”“保留私有路径”，不把三类合并。共享核心内部可能有编译器内联或专门化；结论是两侧共用该核心，不要求整个二进制只有一段算术指令。

### 工作 2A：公平报告规模和适配成本

要同时保留两个口径：现有改动账回答“集成改了多少”，新的同功能存量表回答“该功能现在需要维护多少”。新增/删除/净增不能替代存量。

比较范围固定为当前 x86-64 LP64 实现、相同七类共享 clock ID 和公开 time/gettimeofday/clock_gettime/clock_getres 接口，以及逐项列明的内核读取入口。getcpu 单列，时间子总计与包含 getcpu 的合计分开。namespace 和 native/provider fallback 是功能边界的一部分；provider 代码纳入实现清单并标明运行验证环境，不把源码支持当作裸机验证。

| 同功能规模表的行 | Raw 侧内容 | VKSO 侧内容 |
| --- | --- | --- |
| 读取计算 | vDSO 计算与纳入范围的普通内核读取计算，分别展示 | 共享计算定义及必要冷路径；各入口调用同一定义不重复计数 |
| 用户适配与 ABI | 对应用户入口、状态声明；明确 libc 依赖边界 | carrier 私有入口、公开库、初始化、完整用户头文件 |
| 内核适配与 ABI | syscall/分派/类型转换边界 | root adapter、动态 POSIX 分派、类型转换及领域 fallback |
| 状态发布 | update_vsyscall 及对应状态表示 | tk_publish_read_state、timezone 及对应状态表示 |
| 映射与 namespace | vDSO/vvar/time namespace 功能切片 | MM_data、namespace、exec/fork/setns/exit 接入 |
| 构建与链接 | 同功能 vDSO 构建和布局切片 | 共享段、carrier 与公共库的功能接入 |
| 单列项目 | 通用设施、共同数学/provider helper、其他内核读取依赖、测试/诊断及范围外平台支持 | 同类项目；尤其保留的私有读取依赖与通用 VKSO 注册/映射设施 |

计数规则：以当前语义职责重新选函数/范围，记录版本、文件、符号、范围、类别和纳入理由，使用非空非注释源码行。每条物理源码行仅有一个主类别，子总计必须去重；同一头文件被多个入口引用不重复累加。宏/inline 的源码规模与编译后机器码规模分开。ABI 断言等生产维护代码对称计入，测试专用代码单列。

特殊边界：Raw 普通内核 reader 是这次比较的对象，不能沿用旧表把它整体排除为“共同依赖”。VKSO 为不支持 provider 和特殊上下文保留的私有计算也要可见，不能只展示共享核心。通用 timekeeper 的计时推进/NTP 算法按共同依赖单列，不把整个 timekeeping.c 归给某一侧。

公平性核对：Raw 的 libc 解析/初始化依赖与 VKSO 的公开库/初始化要对照披露；如果尚无所用 libc 的同功能源码切片，就明确该项未计量，不能把带此缺口的局部小计命名为端到端总体规模。旧 `source-manifest.tsv` 描述早期实现，其范围和职责不得直接套到当前源码。

二进制另表：绑定实际实验包、配置、编译器和构建身份；分别报告相关内核 text、Raw vDSO 或 VKSO carrier/公共库的专有 text、共享 text 和数据/页对齐开销。共享 backing 只算一次；ELF 文件大小、有效代码字节和物理驻留页不能相互替代。通用 manager/module/exporter 的成本单列。

完成标准：每项可回溯并可复算；同功能主表、保留依赖和设施成本能分别阅读；只有总量边界齐全后才计算缩减比例。现有 1,477 新增、340 删除、净增 1,137 继续作为集成成本证据，494 不能标成纯时间算法行数，393 与 Raw 406 不能直接计算缩减率。

### 工作 2B：用真实修改展示集中维护

主要指标是需要维护的独立计算定义、必须同步的语义位置和仍需修改的适配位置；文件数与源码行数是辅助指标。按实际任务分别判断哪些位置需改，不能预设 Raw 每次改两处、VKSO 每次改一处。

已找到并核对的真实案例：`aa1855e812107757f57ef68fc537f91c48c8034c`，将 x86 共享读取的 cycle delta 专门化为全宽计数器。修改清单为：

| 位置 | 真实修改 | 维护含义 |
| --- | --- | --- |
| `vkso_time_internal.h::vkso_cycle_delta` | 去掉 mask 参数和有限位宽分支，保留 backward observation clamp | 修改一个共同计算定义 |
| `vkso_time_core.c::vkso_read_hres_time` | 去掉 mask 读取，更新 helper 调用 | 修改共同计算的调用位置；没有用户/内核各一份副本 |
| `vkso_time_test.c::vkso_cycle_delta_selftest` | 更新 helper 接口与不支持 provider 的测试输入 | 该提交含测试修改；本次仅检查补丁，不据此声称重新运行了历史测试 |
| 用户入口、内核 root adapter、publisher、MM_data | 该提交没有修改 | 此次修改没有改变这些适配契约；不能推广为所有算法修改均无需适配 |

前提可从 `arch/x86/kernel/time.c::clocksource_arch_init` 核对：mask 非 64 位的 clocksource 会禁用用户可见 mode。当前两侧普通高精度路径都调用上述共享计算，因此共享范围内的优化无需分别移植到用户和内核入口；保留私有路径不在这一覆盖声明内。

Raw 对应位置是 `arch/x86/include/asm/vdso/gettimeofday.h::vdso_calc_delta` 与 `kernel/time/timekeeping.c::timekeeping_get_ns/timekeeping_delta_to_ns` 等。核对发现 Raw x86 vDSO 本来就省略 mask 并做 backward clamp，内核路径还承担更广的 clocksource 范围。因此此真实案例足以说明 VKSO 的“一处共同实现修改覆盖两侧”，不能当作 Raw 同任务必改两处的实测证据，也不能据此给出修改点减少百分比。

如果正文要进一步量化“同一维护任务减少多少同步修改点”，需另选具有共同语义要求的真实任务，或在隔离分支完成明确标为受控任务的两侧补丁：先规定输入/输出和适用接口，再记录 Raw/VKSO 实际改动的函数、共享 helper、适配与测试，使用同一语义检查验证两者。任何 Raw 已满足要求的路径应记为无需修改，不能为了对比增加改动。

工作 2 的交付是“一张同功能规模及适配成本表 + 一个带修改清单和证据边界的维护案例”。可支持共同计算集中维护；开发工时、缺陷率和效率百分比需要额外观测，当前不作结论。

### 当前完成状态与下一步

工作 1、2 的当前结果固化于 [current-evidence/README.md](../../../code-size/current-evidence/README.md)，数值表见 [tables.md](../../../code-size/current-evidence/tables.md)，复算状态见 [verification.json](../../../code-size/current-evidence/verification.json)。前文“已有证据”表保留了本轮开始时的缺口，以下状态替代其中工作 1、2 的待办。

- 工作 1：职责图、逐接口覆盖、实际内核/carrier 调用指令，以及 8 次正式 VKSO 启动的 API、生命周期、PFN 和 1/8/32 进程资源证据已汇总。
- 工作 2A：当前同功能源码切片、逐行归属、通用设施与保留依赖、实际 clean 实验包二进制分类已固化。功能小计 Raw 1,487、VKSO 1,624 行；计入所列保留切片为 1,578、1,771 行。不据此声称总体代码减少。
- 工作 2B：真实维护提交 aa1855e 的补丁、修改职责表、100,100 组 helper 前后等价输入和当前 9 项主机契约检查已固化。支持共同计算集中维护，不提供 Raw 同任务必改两处、工时或效率百分比证据。
- READ 启动级结果及 UPDATE 条件成本、占比、尾部贡献与逐启动分布均已完成，见下节证据入口。下一步为匹配的 UPDATE 记录器对照。
- 随后补匹配的 UPDATE 记录器对照，先判断相对差值、峰位差和占比差是否受测量方案影响，再选择机制干预；已有 clean READ 保留。

## READ 结果整理完成（2026-10-02）

[完整 READ 证据包](../../../direct-api/read-evidence/README.md)已固化 16 次独立 clean READ 启动、38 项配置/接口对照及全部 9,424 个批次。点估计与原主表一致，新增绝对差的精确枚举启动 bootstrap 区间、四块结果、配对/删一块/完整均值敏感性，以及逐接口调用路径和实际构建指令。

交付：[结果表](../../../direct-api/read-evidence/tables.md)、[启动级附表](../../../direct-api/read-evidence/boot-results.md)、[正文候选段落](../../../direct-api/read-evidence/evaluation-text.md)、[核验记录](../../../direct-api/read-evidence/verification.json)，以及三组 SVG/PDF/PNG 图和六个 LaTeX 表片段。

正文主线：七类用户 clock_gettime 中位差为 −1.006～+1.006 ticks；三类内核 READ 为 −2.728～+1.087 ticks。其他五项时间快路径和 getcpu 在两种配置的全部四个启动块中均有更低中位成本。各项绝对成本、百分比和不确定性均完整保留。READ 阶段完成，后续进入 UPDATE 分布分解；未启动新的性能采集或重启。

## UPDATE 分布分解完成（2026-10-02）

[UPDATE 证据包](../../../direct-api/update-evidence/README.md)已覆盖完整 16 次 UPDATE 启动、960 个窗口和 3,599,774 个周期样本。交付包括完整均值、逐启动条件成本/占比/尾部、四项精确分解、负载相对 idle 的变化、128 项分界/尾部敏感性、五张 SVG/PDF/PNG 图和正文语料。主均值与既有表一致，原始样本未删除或修正。

新增可用于正文的结果：VKSO 随四种受测负载变化的均值范围宽度为 Retpoline 0.878、no-retpoline 2.083 ticks，Raw 为 15.585、17.843 ticks；三种读者负载相对 idle 的变化，在六项配置/负载对照的全部四块中均小于 Raw。MONOTONIC_RAW 和 MONOTONIC_COARSE 两负载的函数内计时区间完整样本均值在两配置下均降低约 5.1%～8.0%。这些结果对应当前插桩条件，idle 成本增量、区间及逐启动变动一并保留。

[结果表](../../../direct-api/update-evidence/tables.md)、[正文候选](../../../direct-api/update-evidence/evaluation-text.md)、[核验记录](../../../direct-api/update-evidence/verification.json)和[测量/机制衔接](../../../direct-api/update-evidence/measurement-and-mechanism.md)给出具体依据。

下一项仍是匹配记录器对照：保持当前 Raw/VKSO 功能实现及运行条件，只改变匹配的记录器方案，检查后端相对均值差、峰位差、占比差及负载响应。分布分解已经完成；双峰形成的因果机制和无插桩固有成本尚未由本轮验证。


## 记录器对照补齐与机制准备（2026-10-02）

[机制补充证据](../../../update-bench/mechanism-evidence/README.md)新增旧 Raw 完整源树重建及功能差异核验。旧、新 Raw 的功能源码相同，变化限于记录器及关闭的诊断钩子，原生负载二进制相同；已有 Raw 复测现在可以用于记录器接口/实现整体对照。

八次独立启动共 191,964 个样本按同一峰位口径重算：旧记录器下 VKSO−Raw 高峰位置差为 −21～−16 ticks，当前记录器下为 +11～+13 ticks。两组启动、四负载的相对峰位变化均为 +28～+34 ticks。记录器影响不能视为两后端可抵消的常数成本。均值、占比和尾部继续按启动报告；启动编号不是同期随机配对。

固定旧记录器的 Normal 控制包已构建并通过静态产物核验。其实际编译源树与已有 no-retpoline 控制版相同，新 Normal 的 carrier、读取/负载二进制与当前 Normal 包一致。两配置只差五个缓解选项，因此后续比较针对缓解配置组。下一项是该固定记录器矩阵的独立启动采集；自然双峰形成和后端占比差仍未获得唯一机制证据。


## 固定记录器的 Raw 两配置复测（两次独立启动，2026-10-02）

[四次 Raw 复核](../../../update-bench/mechanism-evidence/raw-normal-two-boots-review/README.md)已完成：Normal 两次合计 47,999 样本，四次共 95,995，全部无丢样、输入校验和环境恢复通过。约 164-tick 集中区在两次 Normal 中复现，但出现在不同负载和轮次；低侧峰位较稳定，高侧还存在约 128–132、145–150 的局部集中区。不能将两个被选中众数固定解释为两种业务或硬件状态。

两启动等权的 Normal−no-retpoline 完整均值差按 idle/mono/raw/coarse 为 +3.498/+0.789/−0.277/+0.564 ticks，任一负载的不同跨启动组合均有正负差值；这是描述结果，不是配置无影响或固定开销的证明。下一项为当前 VKSO 功能配旧记录器的 Normal 对照，具体根因仍待干预闭环。


## 固定记录器矩阵补齐（2026-10-02）

[联合复核](../../../update-bench/mechanism-evidence/fixed-recorder-summary.md)现覆盖两后端、两配置各两次启动，共 191,991 样本。新完成的 VKSO Normal 两次共 47,997 样本，无丢样、功能与共享页检查及恢复通过。Normal 中约 139–141 与 172–174 的慢侧集中区在两次启动重复，no-retpoline 对应合并分布约 125–129 与 159–160；低峰约 83–85。最强慢峰仍随混合权重变化，不能固定命名为两种物理状态。

VKSO 的 Normal−no-retpoline 完整均值差为 +12.328/+3.220/+10.018/+15.315 ticks（idle/mono/raw/coarse，启动等权），分解显示高侧条件成本增加，而占比与尾部贡献方向各异。两配置相差五个缓解选项，此结果属于配置组比较。

下一项补当前记录器的 Normal 匹配短窗口复测；当前已有 no-retpoline 旧/新记录器对照，但 Normal 尚缺匹配当前记录器单元。自然双峰形成与后端占比差的具体物理根因仍未证实。


## 当前记录器 Normal 首次复测（2026-10-02）

[VKSO Normal current boot1](../../../update-bench/mechanism-evidence/vkso-current-normal-boot1-review/README.md)完成 24,000 样本，功能、共享页、无丢样和恢复核验通过。中央慢峰约135 ticks，旧记录器 Normal 约139–141；no-retpoline 记录器切换的中央慢峰则由125–129上移至146–148。变化方向依赖配置的迹象已出现，但 Normal current 仅一次启动，仍缺 Raw 匹配单元和第二次独立重复。完整均值、尾部及占比分解保留，不据此认定物理根因。


## 匹配 recorder 矩阵推进到14次启动（2026-10-02）

[阶段矩阵](../../../update-bench/mechanism-evidence/recorder-matrix-14-boots/README.md)覆盖335,961样本、896个已校验输入文件。当前 Raw Normal boot1 新增24,001样本、无丢样，功能和恢复通过。与当前 VKSO Normal boot1 的完整均值差（VKSO−Raw）为 +8.025/−0.700/−12.118/+2.693 ticks；旧 recorder 两次等权对应 −4.730/−8.577/−9.630/−11.823。Normal 当前仅每后端一次，需两次缺失 boot2 验证重复性后再形成完整记录器结论。物理根因尚未确定。


## 匹配 recorder 矩阵推进到15次启动（2026-10-02）

[阶段矩阵](../../../update-bench/mechanism-evidence/recorder-matrix-15-boots/README.md)覆盖359,962样本、964个已校验输入文件。当前VKSO Normal boot2新增24,001样本无丢样，功能、共享页和恢复通过。VKSO记录器切换在Normal下中央慢峰下移、no-retpoline下上移的方向差异在各单元两次启动中重复；完整均值仍受占比和尾部影响。只缺Raw Normal current boot2，补齐后形成匹配测量结论。物理根因仍未确定。


## 匹配 recorder 对照完成（2026-10-02）

[完整16次矩阵](../../../update-bench/mechanism-evidence/recorder-matrix-16-boots/README.md)覆盖383,958样本、192窗口，每单元两次独立启动，无丢样、功能和恢复通过。记录器切换使启动等权VKSO−Raw完整均值差变化：Normal为+0.150～+11.951 ticks，no-retpoline为+20.793～+31.027。范围依负载而定；逐启动组合、占比、条件成本和尾部分解全部保留。此结果确认UPDATE相对比较对记录器敏感，不能将测量开销当作可抵消常数，或据任一组插桩值推断无插桩固有成本。

匹配测量对照缺口已补齐；下一步解释具体扰动机制。[离线接口干预](../../../update-bench/mechanism-evidence/recorder-codegen-audit-v4/README.md)发现，仅扩展记录器调用参数并在结束处保留tk，就改变计时区寄存器分配和函数尺寸；同参数数目但传NULL可恢复旧寄存器形式。这个编译证据尚不等于运行时性能因果证据。下一项准备当前接口配旧记录主体的隔离混合版；自然双峰与两后端占比差的物理根因仍未闭环。

### 调用接口混合版首次裸机结果（2026-10-02）

当前调用接口×旧记录器主体的VKSO no-retpoline首轮已完成：23,998样本，
无丢样，功能/共享/恢复通过。四负载高侧主峰127–128 ticks，接近旧版
125–129，未复现当前版146–148；12轮主峰126–130。此单启动结果表明
接口/代码生成变化单独尚未复现原先峰位移动，不能据此排除接口影响
或确定自然双峰物理根因。下一步保持同镜像独立重启复测。
证据：`update-bench/mechanism-evidence/interface-hybrid-boot1-review/`
（相对vkso-tests目录）；包含5启动对照、逐轮/时序统计和均值分解。

### 混合版两次独立启动完成：收敛结论（2026-10-02）

两次共47,998样本、24窗口；boot2为24,000，无丢样，功能/共享/恢复通过。
8个启动×负载主高峰125–128，未复现当前版146–148的主峰移动；但2个窗口
主峰为147，boot2完整均值增加2.817～13.894 ticks。结论是接口变化单独
未复现持续主峰移动，不能声称接口无影响或整个分布恢复。停止同条件boot3，
不立即重采正式UPDATE。自然双峰及后端占比差的因果解释仍未完成。
最新入口（相对vkso-tests目录）：
`update-bench/mechanism-evidence/interface-hybrid-two-boots-review/README.md`与
`update-bench/mechanism-evidence/mechanism-evidence-status.md`。


## 固定地址 guard 控制完成：停止同类追加（2026-10-02）

[完整分析](../../../update-bench/mechanism-evidence/guard-control-boot1-review/README.md)覆盖一次
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
