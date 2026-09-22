本报告评估 VKSO 当前 Evaluation 的证据完整性，并按共同修改对象组织后续工作。更新日期：2026-09-18；原评估基线为 `849ecf6`，实验修订分支为 `experiment/clocktime-evaluation-revision`，Clocktime 无人值守交接基线为 `9a0e3e5`，后续实际执行进展记录在下文。输入为前次评估、[当前完整草稿](../paper/paper_content/Paper%20Draft.md)、已有实验归档，以及新增的 [Clocktime 实验说明](../test/test_gettime/vkso-tests/revision/README.md)、[验证记录](../test/test_gettime/vkso-tests/revision/VALIDATION.md)和[采集核查记录](../test/test_gettime/vkso-tests/revision/COLLECTION_NOTES.md)。`paper/paper_draft.md` 是前半部分大纲，不作为当前 Evaluation。前次修订仅更新评估报告与修改规划；目前按用户授权进入实际执行，并逐组更新论文 Evaluation。

## 当前目标与收尾标准（2026-09-12，按用户要求重新收敛）

**本轮目标：形成能够写入论文、支撑 VKSO 核心贡献的充分证据。** 研究问题是在明确的复用条件下，能否让用户程序以普通函数调用正确执行内核已驻留的计算，减少重复执行体或实现，并量化适配、部署和实际使用的代价。收益是否成立由实验决定；不预设所有案例更快、所有部署净省内存或所有内核函数均可复用。

本节是后续执行依据，优先于下方历史记录中的待办和“整组完成”要求。A–F 继续作为共同代码和构建流程的分组，实验取舍以论文主张为依据。历史失败、未实现能力及不利结果均保留；将某项移出当前目标不等于它已经实现或验证。目标收敛时未启动新实验或改动底层实现；后续实际进展单列于本节末。

| 论文需要回答的问题 | 足够的证据与比较 | 当前取舍及停止条件 |
| --- | --- | --- |
| 同一 resident kernel execution body 能否在用户态正确使用？ | 实际 carrier 的 kernel/user PFN、完整算法输入输出、Clocktime ABI 和共享状态语义；应用确实调用该 carrier | 复用已通过的完整证据。不继续增加类似故障矩阵；只有实际用于论文的配置存在功能或测量错误时才修复 |
| 复用减少了什么重复，又付出了什么资源代价？ | Clocktime 源码/执行体规模，普通同源 DSO 与 VKSO 的唯一物理执行页及 owner、私有支持成本；明确已有 DSO 的进程间共享 | 收敛为一份有明确范围的代码和资源账本。未覆盖项标明，不把局部页数当全系统净收益；不以精确归因整个内核 allocator 的每张页作为收尾前提 |
| 稳态调用及适配对用户端、原有内核使用者有多大影响？ | 保留 PGOT/完整 closure 对照；LZ4/BCH/XZ 同源编译条件下的实际两端成本；Clocktime 现有完整跨启动结果 | A 保持完成。补当前算法构建的正式部署结果，保留退化及区间。只有影响结论的配置或测量错误触发重采 |
| 建立与释放的成本在真实工作流中是否值得承担？ | 从命令启动到有效结果的 setup、释放，以及同一完整 LZ4 工作流的 Native/VKSO 对比；区分一次性成本与复用后的成本 | C/E 共用部署、输入和采集安排，形成主结果表。Guest 通过不替代正式性能；不为完成而再扩展多应用或所有参数的笛卡尔积 |
| 哪些依赖形态适用，需要付出多少适配工作？ | 固定八例的成功/失败分类，既有成功案例的闭包、helper/context、修改量和构建条件；Clocktime 作为完整子系统案例 | D 保持完成。报告固定分母及失败，不继续扩大候选集合，不把 SLOC 等同于实际维护工时 |

### 收敛后的三个交付

1. **正式成本与应用结果。** 以当前已通过完整验证的算法构建为候选冻结版本，把 C 的算法两端成本、E 的完整 LZ4 工作流及直接相关 setup 测量集中安排。沿用原始完整输入与合理 baseline；先消除妨碍结果解释的测量问题，再进行既定独立部署重复。物理机权限是明确的外部执行条件，不能用反复 guest 回归替代。
2. **资源与异常结果解释。** 整理已有物理页及支持成本账本，补足所选计费范围内影响判断的缺项，保留 BCH 所测范围没有净节省的结果。BCH 性能退化先从已有证据提出有限的具体假设，再做能区分假设的一组诊断；没有因果证据时报告观察及解释边界，不要求追查到每条指令，也不反复采到有利数字。
3. **论文整合。** 按上述问题组织 Evaluation，每项保留主结果、关键对照及解释。工程恢复矩阵和详细日志主要作为附录/复现材料；核对正文、表图、摘要及结论，保持旧结果与新实现身份清楚。写作与实验同步推进，不等所有工程待办清空才整理论文。

### 不再默认扩展的工作

- 通用注册协议继续升级、更多 crash/权限组合、全 Linux 自动准入、全部运行时改写的通用认证，转为后续工程方向。已知边界如实写入适用条件。若边界使论文所选实际案例的正确性、共享语义或保护主张不成立，则必须修复该案例或撤回对应主张，不能用一句 limitation 掩盖。
- Clocktime 不因其它案例的注册协议升级而自动重做 20 次采集。仅当论文实际采用新协议承载 Clocktime，才核对该完整配置的功能与共享状态；不强求不同内核案例使用同一个版本号。
- 不追加相似算法、第二个真实应用、第二台 CPU 或新 ISA 来追求覆盖面。只有新的泛化主张需要它们时再设计。
- 不追逐 writer 稳定收益、压力下的 major-fault 优势或全系统净内存收益；现有无收益和不确定结果同样属于论文结论。

### 新实验准入与完成判据

每个新增实验在执行前必须写清：**它支撑哪条论文主张、现有证据缺什么、用哪个完整配置和 baseline、结果会改变哪张表或哪段结论、什么情况下停止。** 如果不能回答这些问题，暂不执行。新增假设只有在已有结果无法判别且会改变核心结论时才触发追加实验。

实现修复必须关联到所选实验中已观察到的问题；回归覆盖实际受影响的路径和配置，复用未受影响的证据。没有新的失败或结论风险，就结束该轮验证并进入正式采集/写作。已经完成的 A/D 不因其它工作组更新而自动重新打开。

**Evaluation 的完成标准是：五个问题均有与实际配置一致的证据或明确限制，关键成本与真实应用比较完整，异常结果不被掩盖，表图和正文一致。** 工程 backlog 清零、所有测试均重复通过、测得正收益均不是完成标准。若执行资源无法支撑某条保留主张，明确该缺口并调整主张或解决执行条件，不无限添加替代性验证。

### §6.3 不稳定性复测（2026-09-20，完成）

按用户要求，BCH 新增九次完整两端部署，保留原三次，共十二次；LZ4/XZ 各三次不变。当前正式结果共十八次部署、13,239 条用户记录、17,721 条内核记录，384 项比较全部重放通过。[复测报告](../test/section63/results/repeat-bch/findings.md)分别列出原三次和新增九次，并给出完整范围。

两错误 precomputed 用户变化为 t=4 −8.62%、t=8 −10.00%；t=8 八错误仍为 +3.73%。用户 PMU 分别显示两错误指令数下降、八错误指令数和分支失误增加，解释了路径相关的性能方向。独立内核同上下文轮换中两错误收益仍保留。零错误短路径仍跨零波动，计数器和地址检查没有给出唯一微架构原因；正文保留范围，不以其负中位数主张加速。

新增内核诊断为三次装载、每次三个同上下文阶段，保留 9,504 个完整操作和 47,520 个事件记录；用户 PMU 为三次实际 carrier 注册，保留 3,168 个操作和 15,840 个事件记录。它们不混入正式计时。Owner 和三种算法二进制保持不变。首个新增尝试因启动器 CPU 亲和性在内核计时前退出，原记录与恢复过程保留。

Paper Draft 的 6.3、引言、实验设置、图表及复现入口已同步更新。[完成核验](../test/section63/results/validation/completion.json)覆盖主矩阵、诊断完整向量、上下文交叉、计数器运行时间、论文与图一致性，以及模块卸载。当前工作结束，不追加追逐零错误微架构原因的实验。

### §6.3 初始六版本实验（2026-09-20，完成；当前数值见上述复测）

LZ4/BCH/XZ 已统一切换新对照：用户端 Native DSO / Adapted DSO / VKSO，内核端 Stock / 原始源码 Matched / Owner。九次完整部署通过原始重放，共 3,735 行用户数据、8,217 行内核数据及 384 项比较。[完整报告](../test/section63/results/report.md)集中给出实验设计、全部结果、部署变化和原因分析；[最终核验](../test/section63/results/validation/completion.json)记录实际完成证据。

BCH 的缓存循环对两错误 precomputed 有可测收益，但 loop-only 和 helper 对照没有解释 Owner 的全部收益。t=8、八错误仍保留 +3.71% 用户开销。XZ 的 +4.33%–5.21% 内核开销由 CRC 替换对照定位，后续可采用域内 CRC 绑定；本轮没有修改实际 Owner 来替换不利结果。三组诊断分别完成三次装载，BCH loop/helper 各 3,168 行，XZ CRC 297 行，与主实验分开。

`test/README.md` 按 6.1/6.2/6.3 区分入口。旧 Matched 原始数据、独立旧 XZ 对照与旧三算法图已清理，仅保留紧凑历史记录。独立应用/setup 数据在清理后重放，全部数值保持一致。Paper Draft 的 6.3、引言相关数值、源码账本及图表引用已更新，后续表号连续调整；[英文 LaTeX](../test/section63/results/paper-material/section63.tex)和图已生成。本轮收尾完成，剩余 BCH 归因边界和可选 CRC 优化不进入自动追加实验队列。

### §6.3 先前执行记录（由新实验替换）

XZ 内核端已按新的 Matched 定义重新完成三次装载、十一轮配对采集，共 297 条记录。新 Matched 使用对应发行版原始源码、内核 CRC32 和完整原生功能配置，仅对齐 owner 代码生成选项。Owner 二进制与先前用户测量一致。Stock 为主基线，新结果为 Owner/Stock +4.73%–+5.51%、Matched/Stock -2.85%–-2.20%、Owner/Matched +7.14%–+7.81%。[已归档的旧结果说明](../test/section63/results/validation/retired-provenance/old-findings.md)已集中保存。旧 XZ helper 对照及其内核结果由本次数据替换；LZ4/BCH 和用户数据不变。

下面记录 2026-09-18 的公共源码修改和完整采集背景，其中 XZ 内核对照已由上述定义替换。

用户已授权应用 XZ memcpy 显式绑定和字典复制循环缓存，并完整重跑 LZ4/BCH/XZ 的用户、内核两端实验。BCH 保留已完成的公共源码优化；普通 DSO 和内核 matched 参考使用相同的优化循环。新一轮仍为每算法三次完整部署，BCH 统一两域与两种 decode 路径的输入。

[当前唯一结果入口](../test/evaluation/results/section63/README.md)集中保存原始采集、配对统计、源码账本和论文表格。[方法说明](../test/evaluation/section63-methods.md)记录对照和计时边界。九次完整部署已全部完成，4,050 行用户记录、8,217 行内核记录及 263 项比较由原始记录重建通过。论文表 9–13、摘要/引言中的算法结论和源码账本已更新，以本次结果为准。旧算法结果及诊断产物已清理。

本次发现首次 XZ 导出的旧审计脚本仍要求 memcpy 符号，未识别新增 bridge，在性能计时前退出。页面恢复已核实，更新审计要求后继续同一计划；已完成 BCH 部署保留，失败 XZ 尝试不进入统计。

其他章节的 LZ4 应用/setup 原始记录已抽离到[独立目录](../test/evaluation/results/application-setup/README.md)，表 28–30 及全部阶段统计重建后逐项不变。Clocktime、资源与适用范围的既有结果保持各自证据范围；适配源码计数随 BCH/XZ 的修改更新。本轮完整采集、论文同步和旧 6.3 文件清理均已完成，不扩大算法或平台集合。XZ 用户成本增加 1.15%–1.38%；BCH 两错误 precomputed 的 t=4/t=8 成本比为 0.906/0.990，t=8 的五至八错误仍有 4.06%–5.38% 开销，正文与完整表格均保留。

## 收敛前的执行记录与工程状态

以下记录保留产物来源、失败及各阶段当时的判断；其中超出上述主张范围的“仍需完成”不再自动进入当前执行队列。


**更新结论：Clocktime 完整跨启动数据支持代码共享和具体入口成本的报告，但不支持稳定降低 writer 平均与长尾的概括。** Clocktime 冻结采集期间没有修改其核心算法、公共 wrapper 或打包的页面注册实现。公开 READ 的 20 项等权平均开销为 0.922%，短入口和普通内核 coarse reader 存在可见代价。整篇 Evaluation 的适用范围、装载成本、净内存和真实应用成本仍需 B–E 的实际工作闭合，不能将 A 的完成视为整篇 Evaluation 完成。

评估的目的，是回答：哪些 resident kernel computations 可以复用；真正复用了哪些物理页、维护量减少多少；建立与释放成本是多少；用户端和原有内核使用者分别付出什么代价；这些结论覆盖哪些输入、构建和运行条件。性能接近、收益为零或出现退化都应如实进入结论。已有正确性证据直接复用，只补与具体主张相关的缺口。

**本次状态快照（2026-09-12）：** Clocktime 的 20 项采集全部完成，服务 inactive，机器恢复 `5.15.0-119-generic`。60,195 个标准化值覆盖完整，43,095 个 reader 值和 17,100 个 writer 值均从原始记录重算一致，30 份 ABI 与 20 份 PFN 记录通过核验。729 项比较及 bootstrap 区间逐字节重现。已生成[三方法结果报告](../test/test_gettime/vkso-tests/revision/NORMAL_RESULTS.md)，并更新正文 setup、表 2、Clocktime 表 15–20 及摘要/结论。Writer 启动间变化较大，撤回稳定降低平均及长尾成本的概括；A 的完整采集、核验和结果解释已完成；D 随下述当前 owner 两域验证完成验收，B/C/E/F 仍未完成。

| 工作组 | 本轮进展 | 下一步具体交付 |
| --- | --- | --- |
| A：Clocktime | 20 次采集、全量原始记录核验、三方法结果报告及正文更新已完成 | 保留 writer 不确定性；如需解释其原因，另定诊断，不追逐有利重复 |
| B：页面复用与装载 | 已验证映射/释放及部分失败问题；完成 BCH 库/owner 页账本及 63 个 loader 的活动对象字节和 PFN 覆盖核算 | v3 完整计划、300 页跨批次回滚、QUERY、恢复重试及 LZ4 完整 CLI 已验证；槽位内替换、启动中断恢复及三算法新 owner runtime 已通过；manager 的链接产物身份核对、FIFO 完成通知、root/sudo 会话和普通 ext4 文件/VMA 矩阵已通过；三算法 setup、96 次规模会话、first-touch 3,800 个原始调用及 60 次压力/恢复调用已验证；终态对象正常回收及其中断恢复已通过；v4 类型与实际权限、三算法及 built-in 两入口回归通过；仍需正式性能、完整物理计费及源页边界 |
| C：PGOT 与真实算法 | 重复层次、BCH decode 边界、LZ4 libc 对照与完整 runner 已核实；三算法当前 owner 在同一注册会话的完整内核及用户工作负载通过，共 2,739 行内核采集记录 | 完整独立部署重复、BCH 退化归因及实际 owner 的物理机内核成本；guest 记录不进入正式性能表 |
| D：适用范围与导出工具 | 已完成：固定 8/8 终态（2 PASS、6 FAIL）；六个成功案例的闭包、绑定、页、构建限制和源码账本；全部成功案例的两域功能证据 | 保留固定分母和失败分类；后续构建变动同步维护账本，不以扩大候选数作为完成条件 |
| E：真实应用集成 | 修改后 registered LZ4 完成全部 24 组压缩/解压与 stock 交叉校验，48 份调用记录及 5 页 PFN 核对通过 | libc 对照及完整四后端 workflow 已验证；在 C 的独立部署会话内采集完整应用性能 |
| F：论文与结果呈现 | 已更新 Clocktime、注册与资源表 21–23、适用范围表 24–26，以及当前 owner 内核执行小节；表 26 的 XZ support 更新为 27 SLOC | 随 B/C/E 的剩余结果继续更新，再做正文/附录、图表和全文一致性验收 |

**源页类型及实际权限已接通并验证（2026-09-12）：** [类型准入记录](../test/evaluation/registration-typed-evidence.md)将 manifest 的 text/rodata/shared_data 传入内核，按 owner 范围和实际页表权限检查。协议更新为 v4，binding 为 64 B；完整三/300 页事务及 96 次规模会话通过，48 个 manager 终态均回收。相同完整 LZ4 owner 在正常与 `rodata=off` 两次 guest 启动完成 18 个直接协议组合及 16 次 manager 拒绝检查：正常 text/rodata 可注册；关闭保护后的可写页即使类型匹配也在应用前被拒绝。新增字段、旧版本拒绝、源 PFN 和完整恢复均核对。该结果不解决 built-in 宽范围的公开性及后续运行时改写；三算法当前 owner 的完整两端回归、LZ4 六/四后端及三算法 setup 已通过，共 2,739 行内核采集和六次 setup 注册。built-in xxh32/sort 又通过完整 247/1,152 个两域功能组合及 4 KiB/2 MiB 页表映射核验；其 launcher 已修正旧 prepared 产品复用问题。Clocktime 新协议共享状态仍需核对，冻结 A 数据不重采。

**完成事务回收已修复并验证（2026-09-12）：** [新回收记录](../test/evaluation/registration-retirement-evidence.md)在确认 RELEASE 后发送 FORGET；丢失 FORGET 回复时以 QUERY 的明确 ENOENT 完成恢复，本地清理后才通知 DONE。完整三/300 页矩阵、两个新增释放中断点、丢回复、root/sudo 和普通文件/VMA 检查通过，17 个 manager 事务最终全部不存在。原 96 次规模扫描重做通过，48 次 manager 会话在 DONE 后均无终态记录，1,008 个活动及 1,008 个恢复 PFN 通过；直接协议对照仍自行 FORGET。实际完整 LZ4 又通过 24 组功能、36 行 component、192 次完整 CLI 和两次 setup 注册/回收。新 manager 不再累积旧版本每会话 688 B 的终态对象；这不等于 allocator 立即归还 slab 页，完整物理计费仍未完成。

当前源页准入已增加声明类型及实际页表权限检查，但 built-in image 仍使用宽范围，manager 的 GNU build-ID 核对也没有逐指令认证运行时代码。正文保留这一实现边界；B 的源页公开性、共享状态及运行时改写验证仍未闭合。

**当前 owner 两域验证与 D 验收已完成（2026-09-12）：** [三算法内核端实验](../test/evaluation/kernel-cost-evidence.md)在三个 exact119 guest 中复用同一次 owner 装载、导出和注册，先运行原完整用户工作负载，再调用内核公开 API。LZ4 的全部 12 个 Silesia 文件及两种块大小完成 792 个三后端试验、1,584 行计时，完整输出与独立 liblz4 交叉解码通过；BCH 完成 10,752 次正确性 decode 检查和 1,056 行计时；XZ 三个完整输入完成 99 个内核试验，原有 882 次用户解码也通过。十三个声明页 PFN、owner 引用 1→2→1、正常恢复与卸载均通过。XZ 补充五个公开 GPL 模块导出后 support 为 27 SLOC，四个算法对象的执行代码与先前构建逐字节相同。

[新账本及重放](../test/evaluation/results/applicability-ledger-20260912-attempt06/independent-audit.json)合入三次实际会话，六个案例结构、二十个声明页、十一处算法 helper slots 和 44 个源文件补丁全部通过。固定八例仍为 2 PASS/6 FAIL。D 按既定交付已完成；C 的 guest 功能及采集验证完成不等于正式成本完成。B 的完整物理计费/源页边界、C 的独立部署/物理机内核成本/BCH 归因、E 的正式应用性能以及 F 的最终验收仍未完成。以下记录保留各阶段当时的实现身份与缺口。

**跨案例适配账本已统一（2026-09-12）：** [完整账本](../test/evaluation/applicability-ledger-evidence.md)保留固定八例的 2 PASS/6 FAIL，并合入四个既有集成。六个成功案例的实际 carrier、二十个声明页 PFN、代码/thunk 闭包及十一处算法 helper slots 均已重建；Clocktime 的 40 B context 单列两个函数与三个数据地址，sort 的回调参数不算 PGOT。三算法源码差分仍为 LZ4 45/7、BCH 37/9、XZ 52/9 行，但当前 cooperative owner support 分别为 18/19/21 SLOC，旧 support 数保留历史身份。Clocktime 原始 v5.15.198、M11 与最终语义范围逐行复算为 Raw/VKSO 1,505/1,305 SLOC，32 个完整源文件补丁重放通过；当前产品范围与冻结终点相同。正文新增表 25–26。账本明确当前 LZ4/XZ owner 的完整内核侧 workload 尚缺，BCH 内核矩阵属于较早 owner；这部分与 C 的 kernel-cost 实验合并完成，D 尚不标为整组完成。

**实际回收压力与恢复已观察（2026-09-12）：** [同一 first-touch runner 的压力场景](../test/evaluation/first-touch-evidence.md#reclaim-pressure-scenario--2026-09-12)在一个 exact119 guest 完成 baseline/pressure/recovery 各十对调用，共 60 次，全部保留。后台持有 2,903,486,464 B 匿名内存，每对压力调用前完整读取两遍 1 GiB 文件；十窗均有实际扫描/回收，合计 5,238,600 个回收页事件，无 OOM。Native 和 Stub 在所有调用前均驻留，调用均为一次 minor fault，因而没有观察到避免 native major fault 的收益；这限制了 post-drop 结果的外推。30 次 Stub 调用 PFN、压力前后各 247 个完整向量、恢复和卸载全部通过。该场景没有 drop_caches，复用实际 owner/export/注册流程；压力 guest 诊断已闭合，正式物理机性能、净内存及源页边界仍待完成。

**完整 first-touch 原始采集已通过（2026-09-12）：** [注册态记录](../test/evaluation/first-touch-evidence.md#registered-raw-protocol-run--2026-09-12)在 exact119 guest 完成 Native/Stub × hot/PTE-cold/post-drop，保持 100 calls、90% 阈值、每组五个合格批次及最多 20 次尝试。38 批、3,800 次准备成功调用全部保存；Native/post-drop 的八个拒绝批次也进入未筛选分布。独立重放确认 3,564 个 IQR 样本和 2,859 个 accepted-batch 样本，各组均达到目标。原 XXH32 汇编的 338 个字节在 native、owner 和实际载入函数中一致，247 个独立 oracle 向量及一页 PFN 通过，恢复与卸载正常。为缺少 BTF 原型的原汇编入口补充了显式 API header；合作 owner 使用统一 descriptor，核心汇编未改。功能校验进程现先退出，避免其 native 映射阻止驱逐；空 expected-fault class 现保留全部调用并拒绝该批而非中止后续组。原始格式记为 v2，计时体不变，十项测试通过。Guest 延迟不替代物理机结果；正式重复、完整 setup/计费和压力仍未完成。

**规模扫描与事务对象计费已执行（2026-09-12）：** [完整记录](../test/evaluation/registration-scale-evidence.md)在 exact119 guest 覆盖 1/2/4/8/16/32 页 × 文件页已驻留/逐文件驱逐 × 完整 manager/直接 v3 传输 × 四轮，共 96 会话；所有页在计时前以 mincore 核对缓存状态，1,008 个活动 PFN 和 1,008 个释放后 PFN 逐项核对通过。Guest CPU 固定为 1，内核阶段与外部 READY/DONE 分开保存。真实模块的 transaction/binding 大小分别为 688/56 B；活动请求量为 688+56N，RELEASE 后保留 688 B 的终态对象，测试显式 FORGET 后 QUERY 为 ENOENT。该归档的 manager 未发送 FORGET；后续已按上方回收记录修复，旧账本仍保留这部分成本。48 个 manager 的 smaps_rollup RSS 为 1,540–1,560 KiB；status VmRSS 明显偏低，已保留原始值并使用前者。六个 FD 和 FIFO 容量单列，未将容量视为物理驻留。该 guest 同环境完成 30 次时钟 helper 开销观测。规模采集流程通过，正式物理机伸缩性、完整物理计费和压力仍未完成。

**三算法 setup 采集入口已验证（2026-09-12）：** [装载采集证据](../test/evaluation/setup-evidence.md)在三个独立 exact119 guest 中运行实际完整 `vkso exec` 和复用已构造 carrier 的 `exec-ready`，共六次注册、36 个新进程。完整 LZ4 语料往返、BCH 初始化到纠错恢复及 XZ 全文件解码使用原有算法和校验函数；每进程一次或三次完整任务。采集统一使用 CLOCK_MONOTONIC_RAW，重建外部命令到首个有效结果、进程装载/符号解析、内核 COMMIT 与释放范围，保留嵌套关系。全部原始时间戳、两次事务和释放结果重放通过，三算法原完整功能矩阵仍通过。Shell 阶段标记有外部 helper 进程开销，这批 guest 数据只用于采集验证。正式重复前仍需匹配普通 DSO 的完整命令路径、同环境 observer 校准及无插桩外部对照、缓存顺序和 CPU 记录；完整计费、规模扫描、first-touch/压力及源页边界仍未完成。

**注册通知及文件操作更新（2026-09-12）：** [最新完整记录](../test/evaluation/registration-notification-evidence.md)通过 exact119 guest 的三/300 页事务全矩阵，并新增实际 `vkso` 会话函数的 START/READY/DONE FIFO 通知、竞争启动与遗留状态保留、wrapper 退出后的恢复。普通 UID 65534 经真实 `sudo -b` 启动 root manager，应用保留 UID 65534，释放完成通知通过。七种文件操作在同用户普通文件上成功，在 carrier 及其既有 hardlink 上均返回 EPERM；共享写升级返回 EACCES，私有写/fork 和 cache hints 保持源内容，前后 PFN 相同。普通 ext4 文件/VMA 矩阵不再笼统列为未做。

当前同一 manager/模块/vkso 又分别通过 LZ4、BCH、XZ 的完整功能及 PFN 会话。LZ4 同时重放六后端正确性、36 行 component 与 192 行完整四后端 CLI 采集验证；这些 guest 时间不进入正式性能表。取消 250 ms ready 轮询不代表已经测得相应延迟收益。B 下一步仍是完整 setup、1/2/4/8/16/32 页扫描、净资源账本（含 FIFO/pipe、FD 和终态事务记录）、未筛选 first-touch 与压力；源页公开性和运行时重写边界仍需处理。C/E 的独立正式部署尚未执行，D 的跨案例账本和 F 的最终全文验收也未完成。

**自动接续的实际终态（2026-09-12）：** 此前启用的 `vkso-evaluation-followup.service` 在 Clocktime 完成后的原内核启动中触发，已完成覆盖核验及全部 15 个 UPDATE 方法目录的 writer 原始记录审计。随后 `algorithm-and-cli-deployments` 在开始构建/部署之前的 `git diff HEAD` 源码归档步骤失败（exit 129）；算法部署和后续 D 检查没有执行。服务按设计在进入时停用，目前 `ActiveState=failed`、`MainPID=0`、`UnitFileState=disabled`，不会在下次启动自动重试。失败日志和原输出目录保留，详见[接续记录](../test/evaluation/FOLLOWUP.md)。

此前已向用户说明这项新增系统级安排并询问是否取消，未收到明确答复；上述触发是既有配置的实际行为，不视为新的授权。当前不重启或重新启用该服务，不扩展其队列。继续已授权的结果核对、论文修订和普通构建准备；如需再次安排系统级自动执行，须先明确该边界。

各组先核对现有材料，列清剩余修改对象、运行成本和验收产物，再集中实施。新增性能采集先验证完整实现和测量路径，再安排正式重复；启动次数、候选数量和硬件矩阵是针对主张的预算，不是统一门槛。当前已运行的 Clocktime 计划保持原样，不因更新本报告而重启或扩大。若任何组确实需要改动项目基础功能，先报告具体不一致与原因；不能把“补证据”默认变成基础功能重写。

当前所需的底层修订已按共同文件整理为[分析/导出工具、注册会话/owner 构建两组清单](../test/evaluation/proposals/implementation-handoff.md)，链接具体补丁、编译证据和待实施接口。分析器/导出器、LZ4 bridge 与显式数据绑定已在工作树实施并通过离线验证；完成通知和错误传播已通过新 guest；cooperative owner descriptor/pin 已实施且 LZ4 生命周期通过；v3 动态事务、跨批次回滚和 QUERY/恢复重试已实施并实测；其余要求见 B 的最新记录。原八例旧任务已停止并保留历史记录，修订 checker 已在新目录完成 8/8 静态终态。

这里以 SOSP/OSDI 论文为参照，依据是各篇论文如何验证自己的主张，并非声称这些会议规定了统一的实验清单。本文的分组、样本量建议和实验设计是针对 VKSO 的判断，不是引用论文的硬性要求。

下列评估参照中，µFork、Userspace Bypass、Orbit 的原始论文 Evaluation 已在实际执行阶段重新核对；其余两篇沿用前次核查。具体借鉴与任务对应见[执行说明](../test/evaluation/README.md#evaluation-design-references)。

| 论文 | 核查的位置和证据结构 | 对 VKSO 的启示 |
| --- | --- | --- |
| [μFork，SOSP 2025](https://owl.eu.com/papers/ufork-sosp25.pdf) | §5 的四个 RQ 分别覆盖轻量性、应用性能、功能使用价值和 CoPA/CoA/full-copy 对比；§5.1–5.2 同时报告创建延迟、内存和应用结果 | 将“能以低开销执行”与“共享机制带来什么收益”分开验证；用有语义的替代设计解释收益 |
| [Userspace Bypass，OSDI 2023](https://www.usenix.org/system/files/osdi23-zhou-zhe.pdf) | §6：I/O 微基准、Redis/Nginx 应用、其他 I/O 技术比较，以及 KPTI on/off × VM/物理机；Table 2 保留不同环境下的负收益 | 严格控制机制成本之外，还需交代部署条件和用户实际可选方案；受控最优场景不能外推成普遍收益 |
| [Operating System Support for Safe and Efficient Auxiliary Execution（Orbit），OSDI 2022](https://www.usenix.org/system/files/osdi22-jing.pdf) | §5.2 测创建和调用开销；§5.3 在六个应用中实现八个任务；§5.4 验证隔离；§5.5 测应用性能，Table 5 分解优化作用 | 新 OS 抽象需要同时回答适用性、建立成本、语义/隔离和净效果；“新增抽象”与“顺带优化数据布局”的效果需要区分 |
| [Practical, Transparent Operating System Support for Superpages，OSDI 2002](https://www.usenix.org/legacy/event/osdi02/tech/full_papers/navarro/navarro_html/) | §6 明确区分资源充裕时的收益、压力下的收益保持、病态情况开销和设计选择 | 用它指导 residency/内存压力问题即可；不需要机械照搬所有压力测试，也不以旧硬件的数字作性能基线 |
| [Producing Wrong Data Without Doing Anything Obviously Wrong!，ASPLOS 2009](https://sape.inf.usi.ch/publications/asplos09.html) | 研究编译链接布局和环境造成的测量偏差，提出因果分析及实验设置随机化 | 多轮重复不能自动消除固定布局或一次启动造成的偏差；跨启动与布局敏感性是不同的问题 |

μFork 的正式发表位置是 SOSP 2025，不应把它当成 USENIX/OSDI 论文；附件没有提供其正式链接。以上前三篇可作为主要评估参照，后两篇分别提供内存机制和测量方法的依据。它们是评估范式参照，不是必须复现的 VKSO 性能基线。

当前主张与证据的对应关系如下。A/D 已完成既定交付；B/C/E 已有新的功能、PFN、资源及失败诊断记录。各组的具体证据和剩余交付见后文。“未见”表示在所列正文和归档中未找到足够证据，不等于断言整个仓库从未做过。

| 需要支撑的主张 | 当前可核查证据 | 判断与补充要求 |
| --- | --- | --- |
| grafting 不增加装载后执行路径成本 | 草稿 Table 3；first-touch CSV 中 hot 两侧均为 71 cycles，resident fault 接近 | 有较强受控证据；只能支撑所测单页函数和环境，不能代表部署总时间或所有闭包 |
| PGOT 代价可控且受依赖结构影响 | primitives、retpoline 对照、四个完整 copied closures | 应保留；copied closures 是同域适配实验，不能计入实际成功导出的功能数量 |
| 真实 resident export 保留功能及同源性能 | 旧算法对照；新 BCH/XZ 完整功能与 PFN 验证；修改后 LZ4 完整 CLI 和五页 PFN 验证 | 修改后功能通过，跨部署性能仍缺；新旧 owner 与 helper 构建分开报告 |
| 是具有清楚边界的复用机制 | 四个既有集成案例；固定八例 8/8 静态终态；六个成功案例的结构/源码/构建账本及两域功能验证 | 支持所列显式输入、回调与适配配置；固定案例研究不能估计 Linux 整体可复用比例 |
| 消除了第二份物理执行体并有资源净收益 | Clocktime 共享/复制 PFN 对照；BCH/XZ 各四页共享；BCH 1/4/16 loader 的库/owner 账本 | 共享目标已验证；BCH 所测库与完整 owner 范围没有净节省，全系统及剩余资源归因尚未完成 |
| 建立后可像普通 DSO 一样使用 | 旧性能表从 dlopen/dlsym 后开始计时；三个 guest 已完成完整导出、ready-carrier 及新进程的 setup 采集 | 阶段边界和完整任务已验证，正式物理机 setup-to-first-call、匹配的 Native 命令全程及短生命周期比较仍缺 |
| Clocktime 读写代价可接受 | 20 次完整采集及原始记录核验；正文表 15–20 已更新公开/内核 reader、writer 与并发结果 | 支持所测入口成本和共享关系；writer 区间不能证明稳定改善或无开销，三方法不能单独分离 snapshot 布局优化 |
| 保持保护和生命周期契约 | 既有 ABI/namespace/fallback；新 guest 的权限/COW/正常恢复及注册部分失败记录 | v3 已验证 owner 引用、跨批次回滚、恢复重试及若干文件边界；提交槽位和启动中断恢复已补齐；manager 的链接产物身份核对已补齐，其余边界仍待完成 |

工作按共同修改的代码、构建和采集流程分成六类。字母只用于引用，不代表重要程度或执行顺序。每类按“确认现有实现和统计口径 → 集中修改 → 验证 → 一次组织正式采集 → 汇总结果”推进，减少同一批脚本或内核镜像反复修改和重跑。实际需要分开的镜像和诊断采集仍保留区别。

| 类别 | 共同修改对象 | 放在一起完成的内容 | 本类交付 |
| --- | --- | --- | --- |
| A：Clocktime 整套实验 | `test/test_gettime/vkso-tests/revision/`、既有结果报告 | 跨启动统计、公开/内核 reader、UPDATE、多 reader、物理代码共享对照、已有 ABI 与代码规模口径 | 已完成的 READ/UPDATE/CONCURRENT 综合结果及全量核验 |
| B：页面复用与装载 | `page_cache_replace/` 周边观测工具、`test/test_first_call/matrix_bench/`、各导出 runner | setup、注册完成时点核验、PFN/内存计费、权限/lifetime、first-touch 筛选与内存压力 | 一套注册到释放的采集流程，setup/footprint/边界验证结果 |
| C：PGOT 与真实算法 | `pgot_benchmarks/`、`test/test_lz4/`、`test/test_BCH/`、`test/test_xz/` | 重复单位、baseline/构建条件、BCH 诊断、实际适配算法的内核端成本、统一统计 | 完整算法对照表、BCH 诊断及适配记录 |
| D：适用范围与导出工具 | `make_dll/`、`kernel_cgd/`、`vkso`、候选清单 | 固定候选集、分阶段成功/失败分类、closure 特征、人工改造量、构建支持范围 | 候选全集、统一导出记录和 applicability 表 |
| E：真实应用集成 | 选定应用的调用路径和 benchmark 驱动 | 接入已完成的 Clocktime 或算法接口，检查功能，测完整工作流 | 一项真实应用对照及实际 VKSO 调用证据 |
| F：论文与结果呈现 | `paper/paper_content/Paper Draft.md`、各实验报告及表图 | RQ/证据对应、统一单位与术语、补入新结果、保留异常、正文/附录安排 | 与本轮实验版本一致的 Evaluation |

各类之间只传递必要产物：A 已有的 Clocktime PFN 采集方法可供 B 参考，B 再处理其他 owner/装载路径及完整计费，A 无需等待 B 重做相同检查；C 的算法适配记录交给 D，D 不重新测一遍算法性能；E 复用 A 或 C 的完整稳定接口；F 随各类验收更新对应段落，最后统一检查。第二台 CPU 的复测如确有主张需要，分别归入 A/C；内存压力归入 B，不另建一类重复流程。

下面保留原核查证据，并按六类展开修改范围和验收结果。

**A 类：Clocktime 整套实验。**

**完成更新（2026-09-12）：** 下列设计与验收要求已由[结果报告](../test/test_gettime/vkso-tests/revision/NORMAL_RESULTS.md)及其原始/派生记录落实。4,275 个 writer 窗口共 13,893,682 样本、无 dropped；131 个非 CPU0 样本保留，CPU0-only 敏感性的最大点比值变化为 0.1861 个百分点。全部 19 个场景的 writer Mean 与 P99 的 Raw/VKSO 95% 区间均包含 1。定速实际值/目标范围为 0.9999968368–1.0000032182，late batches 为零；最小单窗口 Jain fairness 为 0.922232，已保留并报告。新 Normal 表替换旧单启动主表，no-retpoline 原归档保留为诊断。下面带“前次”“已准备”的条目记录设计和阶段证据，当前终态以本段及结果报告为准。

共同修改位置：[新增实验目录](../test/test_gettime/vkso-tests/revision/)及最终结果报告，复用既有 `baremetal/`、`update-bench/`、`functional/`、`code-size/` 的完整实现和证据。本轮已经集中实现采集工具与对照，不再把内核 reader、多 reader、跨启动控制写成待开发项目。核心 Clocktime、公共 wrapper 和页面注册代码未改，现有采集与分析均已完成。

前次草稿和[旧统一性能报告](../test/test_gettime/vkso-tests/VKSO_READ_UPDATE性能报告_20260801.md)明确将每个 backend/build 的正式批次限定为一次启动；当前草稿已替换为本轮跨启动结果。31 个 READ rounds、7 个进程、15 个 UPDATE rounds 都不能估计 boot-to-boot 变化。IQR、P10–P90 目前被正确标注为描述统计，但描述统计不能证明“等效”或小于某阈值。

新的 Normal 计划已经固定为 READ/UPDATE 两类镜像 × Raw/VKSO 两种 backend × 5 次独立启动，共 20 次；每次 VKSO 启动内测 VKSO 与完整代码复制对照，并交替方法顺序。每方法每次 UPDATE 测 19 场景 × 15 轮，读负载 15 秒、writer 记录其内部 13 秒；整轮预计约 19 小时加重启时间。该数量是本轮已经采用的预算，不是获得可信结果的硬性门槛，也不是经功效分析证明充分的样本量。后续其他组分别估算完整路径的小规模验证与正式采集成本，再决定分配；不直接套用五次启动。本轮保留已冻结分配，不改参数或追加次数来追逐有利结果。

以 boot 为汇总和区间估计单位；Raw/VKSO 来自不同启动，不伪装为同轮配对，VKSO/copy 才在同一次启动内配对。no-retpoline 旧归档继续作为机制诊断，不能与本轮 Normal 数据拼接成同一批正式跨启动结果。

对“没有实际性能损失”，先根据使用场景约定可接受退化范围，再报告差异及置信区间；区间包含 0 不能证明等效。对 1–2 cycles 的短路径同时报告绝对差和相对差。UPDATE 的平均值与每轮分位数分别估计，不能把跨轮次 IQR 当成 P99 改善的置信区间。

重新启动本身也不会随机化所有编译链接布局。对固定 `setarch -R` 的 Clocktime 或固定 ELF，要另外做默认 ASLR/多个合法布局的诊断，或限定结论适用的布局；不必对全部 workload 重跑完整布局矩阵。

已增加测试模块，直接批量调用 `ktime_get_ts64`、`ktime_get_raw_ts64` 和 `ktime_get_coarse_ts64`，覆盖普通内核 hres/raw/coarse 入口；功能验证及实际 VKSO shared-core/fallback 调用路径核查已有记录。已有 syscall fallback 继续保留，但不代替这些普通内核 API。正式结果已并列用户 reader、这三个内核 reader 和 writer，以检查两侧成本；不能把三个代表性 API 称为所有内核使用情境的覆盖。

Clocktime 的既有设计同时改变共享计算、snapshot 字段组织、发布路径和入口。Raw→VKSO 的 UPDATE 变化只能先视为子系统重构的组合效果。本轮新增的 `compact-split` 复制完整实时 carrier，保留算法、支持代码、虚拟偏移、公共 wrapper 和共享状态，仅让用户代码使用独立物理后备，运行于同一 VKSO 内核。名称中的 compact 不能作为“只改 compact snapshot”的证据。

**修正前次归因规划：** VKSO↔copy 可检验共享与复制代码后备的差异；Raw↔copy 仍混合 snapshot、发布和入口重构，无法单独量化状态布局收益。原报告把后一比较直接解释为布局/发布优化、把前一比较解释为入口重构，隔离程度说得过强，应撤回。当前无需为补全组件排列组合再改基础实现；最终报告先给三种完整方法的结果及其可解释范围。如果之后确实要主张某一布局优化是原因，再单独提出所需实现、成本和验证依据。

旧归档是一个 reader 配正常 writer；新协议已经覆盖 monotonic/raw/coarse × 1/2/3 个独立绑核读进程 × 饱和/每读者 1,000,000 calls/s，并保留 idle writer。读进程使用 CPU 1–3，控制任务使用 CPU 0。结果已输出总吞吐、各 reader 成本与实际速率、公平性、writer mean/median/P95/P99；sequence retry 单独作为诊断。该范围是当前四核机器上的最多三个用户 reader，不能外推为大核数或跨插槽扩展性。

固定速率统计包含预热和正式计时调用，采用批次节流。必须检查实际速率和 late batches，不能用相同目标值自动证明相同实际负载；这些数据也不是平滑请求到达或逐请求尾延迟。窗口检查确认 writer 记录位于所有 reader 的负载区间内部。无需为常态并发结论额外提高系统 writer 频率。

采集记录还修正了 writer 的解释：`action==0` 不唯一对应周期 tick，当前 recorder 没有 caller-mode 字段；早期窗口中已有少量 CPU 1/2 记录。因此主结果保持冻结的全部 action-zero 样本，报告实际 CPU 分布，不按预期亲和性删样本或断言其具体来源。如小差异的解释依赖这些记录，再提供 CPU0-only 敏感性结果，并与主结果分别标明。平均值与尾部分位数的改善方向可以不同。

既有四种 Clocktime READ 镜像的 `functional.matrix` 各有 98 行，均包含 namespace lifecycle、exec、setns 和单次 fallback syscall 的 pass 记录；前次核查未发现 `=fail` 行。现有 LZ4/BCH/XZ 也有输出一致性证据。因此“正确性完全没测”不成立。

旧归档 READ 的 20 个入口等权几何平均为约 ±1%，并不意味着每个路径均在 ±1% 内，也不是应用调用频率加权的总体效果。旧性能报告已揭示 `gettimeofday(NULL,NULL)` 约 2 cycles、约 33% 的差异，以及并发 coarse 约 9%–14% 的差异。正文需要同时保留分组、最差真实路径及绝对数；本轮正式结果按相同原则重新解释，不能预设仍得到旧幅度。

本类已完成所有计划启动的身份/数据覆盖核验、原始 writer 与汇总值一致性、实际速率/late batches/窗口重叠、ABI/sequence/PFN 记录检查，以及最终三方法结果报告。READ 使用不带 writer recorder 的配置，UPDATE/CONCURRENT 使用 recorder；诊断另采。历史 SLOC/符号规模证据对应既有完整实现，新增测试代码不计入产品缩减。已有 PFN 验证在声明闭包中观察到 VKSO 三个唯一页、复制对照五个唯一页；它证明两张代码页共享关系的差别，不代表全系统净节省两页，也不代替 B 类的开销账本。

**reader 审计的前期验证：** [独立审计脚本](../test/test_gettime/vkso-tests/revision/audit_reader_records.py)核对原始 READ/CONCURRENT CSV 与标准化值，重算调用速率、公平性和 kernel cycles，检查批次计数、CPU、读写窗口及 sequence counters。首个物理实验块 steps 000–003 的三方法共 8,619 个 reader 标准化值全部匹配；该块定速实际值/目标范围为 0.9999970704–1.0000032182，late batches 为零。五项测试确认错误身份、计数、窗口和汇总值会被拒绝，并保留合法的不等速负载及 late batches。该首块验证随后扩展至全部 43,095 个 reader 值，最终结果见本报告状态快照；ABI/PFN 由单独脚本核验。详见[验证记录](../test/test_gettime/vkso-tests/revision/VALIDATION.md#reader-record-auditor-validation--2026-09-11)。

**归档核验扩展（2026-09-12 01:21 UTC）：** 已在 CPU 0 对全部 19 个完成启动执行 reader 与独立 ABI/PFN 审计，结果保存在 `revision/results/record-audit-20260912T012130Z/`。15 个 READ 方法记录和 13 个 UPDATE 方法记录的 38,775 个 reader 值重算一致，sequence 计数一致；全部已核验并发窗口满足 writer 控制区间包含关系，定速实际值/目标范围仍为 0.9999970704–1.0000032182，late batches 为零。28 份 ABI 日志各有 51 条 PASS 和 49 条路径记录，均只使用一个允许 CPU；18 份 PFN 记录保持 VKSO/compact-split 的声明闭包并集为 3/5 页。这扩展了归档一致性证据，未产生新性能测量，也未覆盖最后一步或原始 writer 记录；该次中间核验之后已完成全量数据检查及正式三方法解释。

**ABI/PFN 审计的前期验证：** [支持记录审计脚本](../test/test_gettime/vkso-tests/revision/audit_support_records.py)已核对同一首块的六份 ABI 日志和四份 PFN 记录：各 ABI 日志的 51 个 pass 记录、49 个 fast/fallback 路径均符合默认模式；两次 VKSO 启动分别重算出共享方法 3 页、复制方法 5 页的声明闭包并集，源页面 PFN 在同启动两方法间一致，记录的 text/state loader 权限分别为 RX/R--。六项测试验证错误状态、页面关系、权限和计数会被拒绝。这些是首块保存记录的核验，不是新运行的 VM/lifetime 测试或全系统净内存结果。

**多核功能证据范围已澄清：** 本轮默认 ABI 继承 collector 的 CPU 0 亲和性，`multicpu_threads=pass threads=1` 实际只覆盖一个允许 CPU。已有 [20260801T164548Z-vkso-final 归档](../test/test_gettime/vkso-tests/baremetal/results/20260801T164548Z-vkso-final/)中 Raw/VKSO × normal/no-retpoline 四个完成案例均保留 `threads=4` 的功能记录，可按原构建身份引用，无须将 Raw/VKSO 的多核验证重新列为完全缺失；该历史证据不包含 compact-split。最终正文须分别说明历史功能证据、本轮逐启动 ABI 与多读者性能覆盖，不把单线程 PASS 写成新增多核验证。

| 结果表 | 行的组织 | 必须提供的列/注释 |
| --- | --- | --- |
| 公开/内核 READ | 20 个公开 API 路径与 3 个普通内核 API 分组列出 | 方法、独立启动数、cycles/call、绝对差、相对差和 boot 区间；明确独立比较与同启动配对 |
| UPDATE 与并发 | idle，以及 clock × reader 数 × 负载类型 | writer mean/median/P95/P99；并发项另列各 reader 代价、实际速率、总吞吐与公平性；尾分位数按窗口计算后再跨启动汇总 |
| 代码与页面 | 产品 SLOC、符号闭包字节、声明闭包唯一 PFN 分开列 | 对照身份、计费范围、共享 text/state 与私有支持页；不同范围不相加 |

A 类验收以这些交付及结论范围为准。`complete.json`、功能 PASS 或无失败标记不能单独代替性能结论和全量核验。详细构建与参数已在新实验 README 中冻结，不在本报告再复制一套可分叉的运行配置。

**B 类：页面复用、装载和释放。**

共同修改位置：[页面复用模块与管理器](../page_cache_replace/)周边的计时/观测工具、[first-touch runner](../test/test_first_call/matrix_bench/)，以及实际调用部署流程的算法 runner。共同对象是一次 grafting session：准备、注册、触达、使用、释放。先定位已有生命周期和权限机制、复用现有证据，再补 setup 与 footprint 采集。若发现基础实现与契约确实不一致，记录触发条件、受影响主张和必要修改，先向用户报告原因；本类规划不预先授权修改页面注册、权限或引用所有权机制。

first-touch 第 331 行、算法第 431 行、XZ 第 509 行分别排除了装载部署或初始化。分三种生命周期测量：每 kernel build 的离线 closure/carrier 准备；每次注册的验证/页绑定；每个进程的装载、私有绑定和首次调用。不要把一次性工作对每个进程重复计费，也不要漏掉每个进程必须做的工作。

对普通同源 DSO 与完整 VKSO，使用相同入口和输入，分别测 ready-carrier 的装载到首个有效结果、当前实际部署命令到首个有效结果、已经注册后的新进程，以及使用结束后的释放。内部阶段按实际代码顺序计时，避免把嵌套阶段相加两遍；外部 wall-time 单独测全程。

**链接产物身份已核对并实测（2026-09-12）：** [当前证据](../test/evaluation/registration-transaction-evidence.md#linked-image-identity-before-staging)记录 builder 的 owner/vmlinux GNU build ID，以及 manager 在 BEGIN 持有引用后、STAGE 前对 sysfs notes 和 descriptor 所属模块的核对。同目录同源码用不同编译选项生成的真实 owner 具有相同 srcversion、不同 build ID 和初始化代码；另一构建 ID、错误模块、错误内核身份均被拒绝并清理，日志确认未发送 STAGE/COMMIT。完整 300 页与五个启动中断点仍通过。三个完整算法再次通过相同 manager/注册模块：BCH 10,752 个 decode checks、XZ 882 次完整解码及 LZ4 24 组/48 操作，分别四/四/五页共享并正常释放；独立核验确认所有实际日志均先匹配 owner/vmlinux ID 再进入 STAGE。同样两个 built-in PASS 入口也在新流程下完成 247/1,152 个功能组合和每入口两页 PFN 核验，确认无 owner 时的内核身份核对；固定八例分母不变。身份检查位于 manager，未更改协议或 owner 布局；GNU build ID 不覆盖保留 note 的后续修改或运行时重写。下面较早记录中的“构建身份未完成”描述相应历史时点。正式 setup/资源、其余文件与重写边界仍待闭合。

**提交资源与中断恢复已补齐（2026-09-12）：** [当前记录](../test/evaluation/registration-transaction-evidence.md#prepared-slots-and-interruption-recovery)以占用中的 xarray 槽位直接替换页面，提交体不再删除槽位后重新分配节点；旧普通 file page 的计费和引用显式释放，源页不继承其 memcg charge。除完整三页/300 页矩阵外，索引 1、64、4096、262144 的稀疏槽位也通过。Manager 在改变 immutable 前持久化目标 inode 与标志归属，五个真实启动阶段被终止后均可由新 manager 恢复；丢失 BEGIN 拒绝响应可查询原 errno。BCH、XZ 和完整 LZ4 CLI 均已在相同注册构建下通过新 owner runtime，活跃引用为 1，分别四/四/五页共享且正常释放。BCH 10,752 个 decode checks、XZ 42 行/882 次完整解码和 LZ4 24 组/48 操作均核验。没有新增正式性能；完整 ELF/build identity、其余文件边界、setup/完整内存及压力测量仍待完成。下面的初始 v3、v2 和 v1 记录保留当时的实现身份。

**动态事务已实施并实测（2026-09-12）：** [v3 证据](../test/evaluation/registration-transaction-evidence.md)记录按事务分配的完整计划、STAGE/COMMIT、QUERY 和幂等 RELEASE。300 页分为 256+44 两批；第 0、150、255、256、299 项提交错误均使已应用绑定全部回滚，所有文件页恢复原内容。恢复遇错继续处理其余页，残留保留引用并可重试；实际 manager 通过丢失提交/释放响应后的 QUERY、ready 后进程终止后的接续恢复、恢复非零后的新进程重试。已有写 fd/shared writable VMA 被拒绝；持久只读/COW 及三进程并发 fault 通过。两个不同 carrier 可使用不相交 PFN，同一源 PFN 的冲突提交被拒绝。完整 LZ4 CLI 在同一注册构建下再次通过 24 组、48 操作与五页 PFN。无 guest panic/BUG/WARNING，未采集正式性能。该初始 v3 仍有删除 cache page 后 xarray 节点可能重新分配的问题；后续槽位内替换已解决，见上文。完整 ELF/build identity、其余文件边界和 B 的 setup/资源结果仍未完成。下述 v1/v2 文字保留对应历史构建身份。

**Owner 引用已实施并实测（2026-09-12）：** [新证据](../test/evaluation/registration-owner-evidence.md)记录 protocol v2 与三算法 owner descriptor 的实现；LZ4 在 exact119 guest 的活跃期 owner/page-module refcnt 均为 1，卸载均被拒绝。源版本不匹配、管理页导出及冲突 inode 分别拒绝；错误 mapping 恢复保留引用。正确恢复后，持久只读映射读回原文件，私有 COW 保留，引用归零且模块可卸载。新 owner 的完整 LZ4 CLI 24 组及五页 PFN 同时通过。该 v2 时点 BCH/XZ 新 owner 仅完成编译；后续完整 runtime 见上文；srcversion 也不等于独立完整 ELF/build identity。该 v2 归档仍是单 carrier、固定容量的批次 registry；后续 v3 的事务证据见上文。管理页在 carrier 私有数据中保留零窗口，未宣称净内存收益。

**完成通知已修订（2026-09-12）：** 旧 manager 在 replace/restore 发出后各 `sleep(2)`，旧部署全程时间应保留这些等待。当前两端使用共享版本协议，内核返回真实 errno、完成页前缀、失败下标及 callback 纳秒；manager 核对内核 sender 和 sequence，收到全部成功结果才发布 ready，并已删除固定睡眠。[新验证](../test/evaluation/registration-completion-evidence.md)包括 exact119 正常/部分失败/恢复错误/版本不匹配矩阵和完整 LZ4 24 组 CLI，均通过。第二页失败现返回 ENOMEM、completed=1，manager 非零退出且不发布 ready；首个绑定仍存在，需显式恢复。恢复失败保留 state 并非零退出，vkso 和算法 runner 传播错误并保留模块。该 protocol v1 归档中 owner refcount 为零；后续 v2 的引用证据见上文，完成通知本身不代表事务完成。现有计时含逐页 debug 日志与 guest 开销，只验证边界；完整 setup 和其余 lifetime 边界仍须落实；v3 已补入动态 stage/commit、QUERY/回滚证据。

先测三个真实闭包，再增加 1/2/4/8/16/32 页的合成规模扫描，观察页数、批次数、bindings 数的作用；后者只解释机制伸缩性。分别测缓存已热与自然首次装载，若保留 `drop_caches`，把它作为额外控制条件。

用短任务、重复调用任务报告完整耗时。只有稳态每次调用确有节省时，才计算额外 setup 的盈亏平衡调用次数；若稳态持平或更慢，不能给出虚构的“足够多次就回本”，应把收益定位于实现复用或内存。

Clocktime 的 2,639→2,055 B 是 reader symbol closure，减少 584 B 不意味着减少一个 4 KiB 物理页。[XZ DSO audit](../test/evaluation/results/section63/raw/deployment-00-xz/results/kernel-dso-audit.md)记录四个 reusable pages，但[审计程序](../test/test_xz/scripts/audit_kernel_dso.py)检查的是 ELF dependencies、exports、relocations 和 page-map 数量，没有读取活跃 kernel/user PTE 的 PFN。不能把此 PASS 写成运行时 PFN 一致性测试。

Clocktime 的声明闭包运行时 PFN 检查已经补入 A；B 应复用其方法和结果，把尚缺的多进程与其他算法 owner 的对应关系、私有支持开销和完整计费补上。对所需目标触达页面后记录 kernel alias 与用户 alias，按物理页去重；正文只给匹配页数和分类。分别统计共享 text/rodata/shared state、私有 PGOT/wrapper/MM_data、carrier 实际驻留页、页表和 manager 元数据；运行前后在同一归因口径内比较。RSS/PSS 可作辅助，不能单独完成跨 kernel/user PFN 的全系统计费。

尤其检查：测试用 `vkso_xz.ko` 等专用 owner module 是原本就提供内核功能的那一份，还是为了实验新增的驻留副本？如果原有内核实现仍保留，必须把两者一起计入净内存；如果其替换了原实现，需说明并验证原内核使用者仍使用完整适配版本。专用模块仍能证明 export 机制，不能自动证明现有内核/用户重复已被消除。Clocktime 的真实替换案例在这方面更有价值。

**Owner 驻留身份已核实：** [驻留证据](../test/evaluation/residency-evidence.md)结合精确 5.15.0-119 配置、debug ELF、原模块重定位及专用 owner 构建记录确认：LZ4 解压和 XZ 的原实现在非 init kernel text 中保留；BCH 与 LZ4 压缩的原实现为可加载模块，配置不能证明历史会话中已经加载。三个 `vkso_*` owner 使用改名 API，runner 没有替换原内核调用者。正文算法节已明确这一实验对象。B 的新增 owner 场景必须计入整个专用模块；“该适配 owner 已驻留”的边际场景仍可单列，但不能把人为预加载等同于原内核本来需要它。目前没有据此推定净内存节省或具体页数。

建议同时报告两个场景：原有目标已经驻留时的边际内存成本，以及为了启用 VKSO 新增加载/常驻目标时的总成本。这样才能评价附件所说的 residency 收益是否免费获得。

**BCH 同会话资源观测已完成（2026-09-12）：** 在精确 119 私有 guest 中，按“普通 DSO/owner 未加载、普通 DSO/owner 已加载、registered carrier”三个角色分别运行 1/4/16 个同时存活的独立 loader，共 63 个进程。完整原有 BCH 功能矩阵在同一注册会话中另行通过。全部目标 PT_LOAD 页触达后，从原始 pagemap 重建 PFN 并集：普通 DSO 为 7/13/37 页，普通 DSO 加完整专用 owner core 为 13/19/43 页，registered carrier 加所需 shim 和完整 owner core 为 13/25/73 页。注册目标的 kernel/user 并集始终四页，普通 DSO 的 executable 并集也始终三页。该实际库/owner 范围在单进程条件下相等，在 4/16 进程时 VKSO 分别多六/三十页，不能据共享目标页数宣称净内存节省。论文新增表 22，见[完整资源记录](../test/evaluation/results/bch_resource-qemu-20260912-attempt03/README.md)。

完整 owner core 六页/24 KiB、observer 四页/16 KiB、page-cache 模块十二页/48 KiB，所有 core 页均观测到，且注册前后至卸载前保持相同 PFN。范围以实际 coresize 为准，精确 119 debug ELF 已核实 `/proc/modules` 的总大小还含 init size，不能用它猜测连续的 core+init 区间。活动 manager 的 VmRSS 1,216 KiB、PSS 1,212 KiB、VmPTE 28 KiB 单列，不与库页盲目相加。Loader 本次 VmPTE 增量为零，但绝对值为 88–100 KiB。此观测尚未归因 BCH control objects、工作负载堆、模块外分配和完整 allocator/slab 成本；人工预加载专用 owner 也不证明实际内核需要它。B 的全系统净计费、完整 setup 和生命周期修订仍未完成。

**BCH 活动对象核算已补齐（2026-09-12）：** 新的 exact119 私有 guest 沿用三个角色及 1/4/16 个同时存活 loader，每进程使用一个完整后端，保留 m13/t4、t8 两个 control 和 codeword，一次只保留一个原 benchmark 的 full-decode context。复用原 C 分配、错误向量及完整输出/位置校验函数，没有修改算法、owner 或注册工具；原三后端全量正确性矩阵在同一注册会话中另行通过。63 个 loader、九阶段的 567 份原始快照重放通过；真实 ELF、源身份、API 地址及完整 owner core 另行核对。两个参数组的 control 及持久表分别请求 41,448/49,896 B；加两个 codeword 后为 92,388 B，t4/t8 context 存活时为 92,930/92,958 B，普通 DSO 与 VKSO 一致。正文新增表 23，见[活动对象证据](../test/evaluation/bch-heap-evidence.md)。

该观测同时保留 requested/allocator-usable 字节以及两种区间的 PFN 覆盖。Control 覆盖页在同组进程之间均不同，control 与工作缓冲区又存在同页重叠，因此按 PFN 求并集，不能由对象字节数直接向上取整或逐项加页数。普通 DSO 与 VKSO 的覆盖页数还受此次 Python/C 观测进程的分配布局影响，覆盖页可能包含其他对象；不把该差异当成 BCH 独占成本或全系统净收益。释放后不再解引用旧地址，进程页数变化也不单独归因 BCH。此项补充活动对象账本，初始化时已释放的临时分配、峰值、allocator 元数据、模块外/slab 成本和 B 的其余要求仍保留。

结果表字段：`target / native unique pages / VKSO unique pages / shared PFN matches / private bytes or pages / incremental pinned pages / net difference`。无法干净分离的通用基础设施开销单列，而非隐去。跨进程的普通 DSO 本来可以共享文件后备，因此不能将用户 text 节省按进程数线性相乘；还应允许私有支持页随进程数量增长，使小闭包的净收益为零或负。

先前草稿的 Registering Resident Backing 声称 module/page references 维护 lifetime，Threat Model and Security Boundary 又将普通进程的 mmap/mprotect/文件操作列入威胁模型。这是需要补证据的明确契约边界。正常退出时先停止 benchmark、再恢复映射和卸载模块，不等于活跃使用者仍在访问时的 lifetime 保证；当前正文已按下述源码和隔离观察校正，B 的完整要求仍保留。

最小验证矩阵应覆盖：共享页用户写保护；私有可写数据不落在 kernel PFN；对声明支持的映射操作仍保持不变量；源模块有活跃映射时的卸载/拒绝策略；最后一个使用者结束后的释放；部分注册失败后的回滚；普通 text 页内共置符号的可公开性/隔离布局。mprotect 后若是合法私有 COW，判据应是无法修改 kernel backing，而非强求所有操作都返回同一个 errno。

对 mmap/mprotect/MAP_SHARED 等测试，限定在项目控制的内核和合成测试页，检验契约即可；无须扩成攻击评测或完整 VM 证明。已有 namespace/exec/fallback 案例直接引用，不重复堆测试。建立 `invariant / exercised path / expected behavior / observed result / implementation location` 表，每项明确实际测过的行为。

实际执行已进一步追踪 `run.sh → vkso exec → manager replace --hold → nl_recv_msg → batch_process_pages → add_page_to_cache` 以及恢复路径，见[注册证据记录](../test/evaluation/registration-evidence.md)。该旧版本注册代码获取/释放 page references，但请求、备份记录及当时调用链没有获取/释放 owner module references；runner 的先恢复后卸载是正常流程约束，不能代替并发 owner lifetime 保证。逐页注册遇错会退出批次，已成功页面留在备份中，callback 只记录错误；manager 没有接收逐请求结果，仍以等待两秒后的流程作为成功。这些代码事实不足以支撑正文中的完整 module-reference、失败原子性和精确完成确认主张。

该旧版本审计结论来自实际入口、数据结构及清理调用链；活跃映射下的引用变化和特定两页计划的部分失败行为已由下述隔离会话观察。其余失败路径仍需验证，不能将已测触发条件推广为任意运行时破坏。已向用户报告这一基础实现边界，该审计时点尚未修改注册协议、页引用或权限代码。后续已按统一方案实施 module pinning、完成通知与事务恢复，当前证据见本节开头；性能测量与契约验证分别报告。普通页面权限也不能证明用户无法跳到所有其他可执行地址，控制闭包保证需保持明确的适用范围。

**隔离执行更新（2026-09-12）：** [完整记录和验证矩阵](../test/evaluation/registration-evidence.md#isolated-runtime-observations-2026-09-12)保存两次独立 KVM guest 的实际结果。使用既有完整 5.15.198 镜像、owner、manager 与页注册模块，将一张 source text page 注册到合成文件偏移。首次会话有三个 reader；第二次增加 UID/GID 65534、无有效 capabilities 的 reader，四个进程均匹配源 PFN。只读 store 触发 SIGSEGV；私有 mprotect(RW) 后写入产生独立 COW，源内容不变。非特权用户对其拥有的 0666 文件在 ready 后进行写打开和 truncate，均得到 EPERM；只读 fd 的 MAP_SHARED 转 RW 得到 EACCES。关闭全部 reader 后恢复原文件内容，随后正常卸载 owner。两次会话的 owner refcnt 全程均为 0，未尝试活跃卸载，也未注入部分注册失败。两台 guest 均结束，无内核 panic/BUG/WARNING，未加载 host 模块。

Evaluation 新增 Registration and Mapping Behavior 和表 21；Implementation 按实际页引用、runner owner 顺序及逐页失败处理改写，撤回独立 module 引用和事务式完整撤销的断言。Discussion 明确所测操作及其时间区间，不将 closure 分析描述成进程级控制流限制。此处使用合成文件验证完整注册机制，不计入算法性能或 setup 数据。三个真实闭包、规模扫描、页引用平衡、全系统净计费、注册前已有可写描述符和剩余生命周期/失败路径仍是 B 的待办；不能因文字校正而删除这些要求。

**部分失败已复现：** 第三个私有 guest 使用同批次“有效源页 + 无 present PTE 的源地址”。内核在第二项报 -ENOMEM，但 manager 仍打印 SUCCESS 并建立 ready，首个注册 PFN 仍可访问。显式恢复先恢复首项，再因第二项无备份报 -ENOENT；manager 仍打印恢复成功并退出 0。该 fixture 的两页最终都恢复原内容，owner 正常卸载；不能把这一局部恢复推为任意跨批次错误均可恢复。结果及两侧日志见[部分失败证据](../test/evaluation/registration-evidence.md#partial-registration-and-completion-reporting)，已补入表 21。此处的 observation complete 表示记录完成，失败原子性并未通过。

[统一修订方案](../test/evaluation/proposals/registration-transactions.md)已列出 owner descriptor/pin、完整计划 stage/commit、真实完成响应、回滚和最终释放顺序，以及共同修改文件和验收项。可用内核 API 的核查发现 owner-from-address 私有接口不能由现有 LKM 直接调用；方案采用公开导出接口和显式 owner 合作，不使用私有符号地址调用。方案中的 descriptor、完整计划、回滚和恢复已分阶段实施；槽位内替换已消除提交中的 xarray 分配；manager 的链接产物身份核对已补齐，其余要求仍待完成。三算法元数据改变后必须以新构建重新生成 carrier 并测量相应 B/C/E。

first-touch 有 expected-fault filtering、IQR filtering 和 accepted-batch 筛选，适合估计给定 fault class 的条件延迟。应一并报告总尝试数、各原因剔除数和未筛选分布；不能用过滤后的结果来声称真实 p99 或“永不发生某种 fault”。若原始日志没有保留被丢弃样本，后续采集需补记录，不能反推。

**first-touch 原始证据已核对：** `Grand_Median` 实为合格批次中位数的算术平均，`Avg_P25/P75/P95` 也是批次分位数的平均，并非所有调用合并后的分位数。已修正正文表 2/3 和实验 Markdown 表的统计标签，数值不变。C 程序未输出逐样本记录，shell runner 未保存每次 stdout 或被拒批次，因此现有归档无法重建未筛选分布、总尝试数及各原因剔除数。后续 B 采样须保存所有调用及准备结果、每批次筛选/接受记录和实际亲和性，详见[first-touch 证据与采集修改](../test/evaluation/first-touch-evidence.md)。当前 latency runner 本身不绑核，归档也未记录外层亲和性；不能据此确认或否定历史 CPU-2 配置。该项需在新采集元数据中闭合，未修改计时体或启动补测。

正文现将 CPU-2 配置限定到其他已列明实验；first-touch 表 2 保留 CSV 可证实的五个合格批次，不再把默认每批次 100 calls 写成已归档的运行参数。这些修订不推定历史运行使用了不同参数，而是保留可核验的描述范围。

**first-touch 留档工具已准备：** C collector 新增筛选前的逐样本导出，保留准备失败状态；runner 保存全部尝试的 raw/stdout/stderr、筛选和接受记录、配置与实际亲和性，并保留所执行二进制。已有输出不覆盖，未达到合格批次数返回 incomplete，benchmark 错误保留记录并停止。三项合成输出测试及 shell 语法检查通过。2026-09-12 已以 `-O3 -Wall -Wextra -Werror -std=c11` 编译，并用实际 Native DSO 的 20 次 hot calls 验证按序留档；重复输出路径被拒绝且文件不变。这是采集工具验证，未新增正式 Native/Stub 性能结果；完整注册会话集成仍待完成，未加入系统服务。

**first-touch 离线结果视图已补齐：** [分析脚本](../test/test_first_call/matrix_bench/analyze_first_touch.py)从 raw 独立重建 fault-class 和 IQR 筛选，并与批次 stdout、接受记录互相核对；分别给出全部已准备调用、预期 fault class、IQR 保留及合格批次样本的描述分布，另列批次统计量均值。准备失败不作为零延迟样本，未记入 ledger 的 raw 文件会报错。新增六项分析测试，连同三项留档测试共九项通过；测试发现并修复了 shell 统计解析提前关闭管道导致的偶发 exit 141。完整 Native/registered-Stub 会话的新采集及重建仍待完成。

当前 53.5× 是 Native 已被逐出文件缓存而 kernel backing 仍驻留的受控比例。正文已经写明这一点，无须再把它当成尚未修正的夸大。若将 residency 作为重要收益，再用受控内存压力测实际驻留、minor/major fault 发生率和未经延迟裁剪的 first-use 分布，并记账额外 pinned memory。可加入正常用户 DSO 的预取/常驻策略作为 residency 对照，连同其代价一起报告；不必把特权驻留策略当成默认应用配置。

本类完成时：同一注册会话能关联阶段耗时、kernel/user PFN、共享/私有页计费和释放结果；setup 全程与机制阶段不重复相加；正常路径与针对性边界测试结果分开记录；first-touch 保留筛选前样本和剔除原因。内存压力是该 runner 的一种场景，依是否主张实际 residency 收益决定采集范围，不单独再建部署工具。PFN/权限诊断与无插桩性能采集分开执行。

**C 类：PGOT、LZ4、BCH、XZ 算法实验。**

**LZ4 对照与完整采集流程已统一并实测（2026-09-12）：** [新证据](../test/evaluation/lz4-helper-baseline-evidence.md)新增 `kernel-userspace-libc`，保留旧 REP 对照。两者的算法源码与编译选项相同，新 DSO 的算法体无 SIMD，外部 helper 使用 libc；实际 GOT/PLT target 与 VKSO bridge provider 三项完全一致。完整 guest 通过 6×6×12 正确性、18 个官方 harness 进程/36 行和全部 12 文件的 192 次完整 CLI 工作流，五页 PFN 与恢复通过。旧 REP DSO 被 libc 身份核对拒绝。第一次因 parser 仍要求五后端停止，修复后完整重跑通过，失败归档保留。正式 LZ4 队列改为六后端/252 行，每部署 CLI 仍为四轮/768 次；采集器会拒绝缺少新后端，旧 210 行只能显式作为历史矩阵核对。Git 忽略的 owner 源码、新文件和每次 Kbuild 命令亦纳入实际归档。Owner 的 Kbuild/-O2/kernel ABI 与用户 DSO 的 -O3/PIC 仍不同，未声称单因素 PGOT 消融或新增正式性能。

**实际 owner 内核端对照已准备并验证（2026-09-12）：** 新增独立 GPL 实验 driver，通过十二个公开导入直接调用 Ubuntu119 stock BCH、完整未适配源码的匹配编译模块，以及现有完整 `vkso_bch` owner。Matched 与 owner 的实际算法编译命令除命名和构建路径外逐 token 一致；stock 的 stack protector、UBSAN、FORTIFY、thunks、内联策略及 compiler package 差异单列，不能冒充同编译条件。两次精确 119 guest 会话各通过两种 t、各 128 轮、全部错误数、三个后端与两种 decode 的 10,752 次完整检查；另一次完整 measure 模式产生并核验 1,056 行。实际 API 指针及模块归属已核对，driver 正常依赖产生的 refcnt 0→1→0 不作为注册 pin 修复证据。首次 BusyBox 参数失败完整保留；没有修改原 owner/core 或装载 host 模块。详见[内核端记录](../test/evaluation/bch-kernel-evidence.md)。Guest 时间只用于采集工具验证，实际内核成本仍待物理机正式重复。

**新增完整功能验证（2026-09-12）：** BCH 使用全新独立构建的未修改 owner、benchmark 和两个普通 DSO，在精确 `5.15.0-119-generic` 私有 guest 中执行实际 `vkso init/exec`；四个导出入口的原 closure checks 均通过。原有 `--correctness-only` 矩阵完整覆盖 m=13、t=4/8、各 128 轮错误位置试验、全部 0..t 错误数、三个 backend 与两种 decode 路径，并通过完整输出/错误位置检查。单独 loader 进程观察到三个 RX text 页和一个只读 rodata 页的 user/source PFN 一致；恢复后的四个新映射均不再使用源 PFN，随后模块正常卸载。该会话没有性能采样，不能作为部署重复、BCH 退化解释或净内存结果。证据见 [BCH 功能记录](../test/evaluation/bch-functional-evidence.md)。

**XZ 完整功能与运行时 PFN 已通过：** 另一精确 119 guest 使用全新构建的未修改完整 XZ owner，经过原 checker/exporter 和 DSO audit，对全部 bash、python3、libc.so.6 输入执行原有 CRC32/x86 BCJ/1 MiB LZMA2 工作流。两 backend × 三输入 × 七轮形成 42 行，含 warm-up 共 882 次完整解码、84 次完整输出比较、42 对 guard 检查，五个接口均覆盖；所有检查通过。单独 loader 进程在工作负载前后均确认四个声明页的 source/user PFN 一致，恢复后的四个新映射不再使用源 PFN，再正常卸载模块。原有 benchmark 的 guest 计时字段仅作诊断，未加入正式性能表。Owner refcnt 仍为 0，生命周期和全系统净内存要求仍未闭合。详见 [XZ 功能记录](../test/evaluation/xz-functional-evidence.md)。

**LZ4 helper 口径修正：** 旧归档包含原生内核 memory helpers 所在页，动态重定位记录也不能证明直接调用经过声明的 Shim。SIMD audit 只覆盖四个普通 DSO，旧记录没有实际 helper 执行地址。因此保留 Table 9 数值，撤回“kernel-backed 与同源 no-SIMD 使用相同 REP helpers”的未经验证断言；当前比值作为具体构建/部署整体对照，补采实际调用路径后再解释差异。详见[导出绑定方案的历史证据核对](../test/evaluation/proposals/export-direct-calls.md#historical-memory-helper-claim)。

**部署入口更新（2026-09-12）：** 已将 Git 源码归档检查提前到创建 campaign 目录之前，并保留 Git 的原始拒绝原因及实际/仓库 owner UID。普通 owner 会话的归档通过；真实无凭据执行检查在创建目录和模块操作之前被拒绝。当前账户 `sudo -n` 返回需要密码，未启动新模块装载/注册。已复核[前台采集指令](../test/evaluation/README.md#algorithm-deployments)：原 5.15.0-119 内核、CPU 2、三算法各三次完整部署并包含 LZ4 CLI。需要仓库 owner 在其终端通过正常 sudo 会话启动；不重新启用已停用的服务，也不修改 Git trust 或系统权限。

**实际执行更新（2026-09-11 17:23 UTC）：** [算法证据记录](../test/evaluation/algorithm-evidence.md)已列出基线身份、部署与进程边界、现有原始矩阵和 BCH 诊断目标。三份旧 raw 分别核验 210/1,056/42 行，缺行/重复行变体均被拒绝；四份报告重新生成后，五份数值 CSV 与全部 Markdown 数值表保持不变。LZ4/BCH runner 补齐新工作目录初始化，BCH 修正 root 执行时误把 `-v` 当命令的问题；均为实验 harness 改动，未改项目基础功能。

[完整部署入口](../test/evaluation/algorithm_deployments.py)已准备，每算法先安排三次完整部署，保留原始全量配置，按部署块轮换算法顺序，并为每次 owner 装载/注册保留单独目录、boot identity 和逐行重复身份。三次用于检查重新部署敏感性，不能当作独立启动或等效性证明。早期验证中，入口曾在 Clocktime 服务 active 时按预期拒绝启动；现在 Clocktime 已完成并恢复原内核。LZ4 绑定、libc 对照和完整 runner 的 guest 验证现已通过；正式执行仍需结束其他分析/测量任务，并由用户在正常特权终端启动。该入口尚未经完整部署验收，PMU 诊断及实际 owner 内核端对照也尚未完成。

共同修改位置：[PGOT 实验](../test/test_MICRO/test_MICRO_pseudo_noqemu/pgot_benchmarks/)、[LZ4](../test/test_lz4/)、[BCH](../test/test_BCH/)、[XZ](../test/test_xz/) 的 runner、构建配置、统计脚本和适配记录。先统一统计字段和对照身份，再修改各自 runner；算法专用 harness 继续保留。BCH 的诊断与本类正式算法采集一起准备。

**前次已发现：算法的 outer run 也未必是重新部署。** 草稿第 431 行说每次正式 run 都重新加载 owner module；但 [XZ run.sh](../test/test_xz/run.sh)在进入 benchmark 前只部署一次，[xz-bench.c](../test/test_xz/src/xz-bench.c)第 244–259 行先加载两个 DSO，再在同一进程中循环七个 outer runs。LZ4/BCH 的顶层脚本也把多个 outer runs 交给一次部署下的 runner。因此要明确区分“一次完整脚本运行”和“程序内 outer round”，不能把后者描述为重新注册、重新分配布局或独立启动。现有比值可保留为该次部署内重复；需要部署泛化的结论应另做少量完整部署重复。

实际 export owner 的内核执行对照已选用 BCH，完整语义与输入验证、匹配编译 baseline 和采集入口均已通过上述 guest 验收；后续在物理机上正式测量，并与 stock 发行构建分列。现有 copied closures 保留为同域 PGOT 机制对照，不能替代该实际 owner 对照的正式成本结果。

已核对轮次顺序及同一路径内的配对输入；接下来补重新部署的完整重复，再选择最大 regression、相同 t 的 0-error，以及 full-decode 路径作定向诊断。若要比较两个 decode 的阶段成本，诊断 harness 必须在两条路径间复用同一 payload 和错误位置，保存实际向量与调用顺序，不能沿用旧表作配对阶段差。采集 cycles、instructions、branch misses 和与代码/数据布局相关的 cache 事件，配合 syndrome、错误定位多项式及二次求根路径的反汇编/运行时记录。每次只改变一个可解释因素，验证 slowdown 是否随其变化；计数器相关性不等于因果证明。不需一开始采满所有 PMU 事件，诊断运行也不替代正式无插桩延迟。

保留 BCH，报告“何时退化、幅度多少、能解释到什么程度”；不要通过删去路径或平均其它算法来隐藏它。LZ4 的 upstream/native 对照也应保留：1 MiB 解压吞吐比为 0.9228，含义是吞吐低 7.72%，不是延迟恰好高 7.72%。

[XZ ADAPTATIONS](../test/test_xz/ADAPTATIONS.md)已明确需要关闭 fentry、sanitizers、stack protector、retpoline/return thunks 和 SIMD/FPU，并修复表基址和四类 helper slots。它是很好的第一张 adaptation card，但意味着“Linux 5.15 原生算法”不等于“发行版原封不动的最终代码”。PGOT 或 Clocktime 做过 Normal/retpoline 对照，不能替 XZ 证明其在相同条件下可导出。新增一列“stock/default build、所需修改、完整支持/拒绝”比单纯再加算法更有价值。

LZ4 官方 harness 的最快循环估计的是吞吐能力，不提供请求尾延迟。统一结果表时应保留各算法的实际估计量，不能为了统一格式把吞吐能力、单次延迟和尾延迟混为一项。

第二台 x86 CPU 复测对微架构敏感的 Func-PGOT、BCH 异常、Clocktime 短路径，而不是完整复刻全部矩阵。如果最终声称跨 CPU/发行版泛化，需要相应证据；如果明确限定当前平台，则记录尚未验证的范围。不需要为“通用设计”一句话立即移植另一 ISA，但需要区分通用设计与已实现验证的 Linux/x86-64 原型。

本类完成时：每个结果能定位到 deployment/process/round；同源 baseline、用户实际 baseline 与实际内核执行对照区分清楚；BCH 退化有原始分布及针对性解释；保留 PGOT primitive 和完整 copied closures；算法适配记录交给 D 类直接复用。诊断代码若引入持久运行时修改，正式结果需要在修改后的完整实现上重新采集。

**D 类：适用范围、闭包特征和导出改造。**

**新确认的导出边界（2026-09-12）：** 完整 LZ4 CLI 运行证明了直接 Shim 相对引用的风险。checker、exporter 和显式私有数据 binding contract 已在当前工作树实现，并通过机器码案例、真实 owner/KRG 离线重放及合成 binding 测试；没有重绑定位置的直接引用现在准确拒绝，数据 slot 只接受完整、对齐且可审计的重定位。该修订已在 exact119 guest 完成 LZ4 注册和全部 24 组完整应用验收；本次提供功能及映射证据，正式应用性能仍待采集。

**本批实际导出已补齐两个入口（2026-09-12 08:33 UTC）：** 在精确 Ubuntu119 私有 guest 中，使用现有完整 `vkso exec`、checker、exporter、manager 和注册模块，分别导出实际 built-in `xxh32` 与 `sort`，未重编译或修改目标算法。GPL 观测 driver 通过公开内核符号调用原入口，用户 driver 调用实际生成的公开 API，并对生成 header 做类型一致性编译检查。XXH32 的 247 个向量在两侧分别匹配独立 libxxhash 参考；sort 的 1,152 个组合覆盖长度、宽度、对齐、输入分布、比较方向和默认/自定义 swap，完整输出及逐例 callback 次数一致。两侧各观测 95,384 次 comparator 和 35,252 次 custom swap 调用。完整证据及复现见[适用范围记录](../test/evaluation/applicability-evidence.md)。

两个 carrier 各有两个 source-backed RX 页，独立 loader 的四页 raw pagemap 与 source PFN 全部一致。XXH32 共享原 return thunk；sort 使用现有 exporter 生成的一个额外 thunk 页，它不属于 kernel PFN 共享页。真实 ELF 的 API offset、生成 thunk 字节和完整 page-map 覆盖已独立核对；恢复后新映射均不再使用原源页，实验模块正常卸载，guest 无 panic/BUG/WARNING。PFN observer 与功能 driver 是同一注册 inode 下的不同进程，未将前者的页表观测冒称为后者的。原始输入、输出及参考重算通过，八项真实归档变异测试验证了审计器；guest 功能组合不计入性能重复或应用结果。

**静态任务终态更新（2026-09-12 08:54 UTC）：** 使用当前 checker 在新目录完成固定八例，得到 2 PASS/6 FAIL；早期中断的六例快照原样保留，未混入修订分母。`rhashtable_insert_slow` 现为 FAIL（访问 1,844 个函数，3,530 条硬失败、721 条未解析记录），`get_random_bytes` 现为 FAIL（访问 28 个函数，36 条硬失败、4 条未解析记录）。六个 FAIL 均按静态拒绝处理，不构造 carrier，也不计为运行时失败。正文表 24、适用范围证据和语义记录已同步；D 仍待回顾性适配账本及必要的其他 runtime case，不能标为整组完成。

正文 Implementation 与 Applicability 已同步撤回“Analyzer 自动证明完整 binding/page identity、所有未解析间接跳转均拒绝”的断言。实际 checker 的 FAIL/INCOMPLETE/PASS 条件已从源码核实；间接控制流、插桩和 Shim 命中分开记录，PFN 验证属于运行时观测。完整依赖绑定仍是实现与验收要求，文字修正不代替该项工作。

**较早的构建身份表述修正（2026-09-12，后续实现见 B 最新记录）：** 当时 [`vkso`](../vkso) 的 replace/exec 会先重新构建 workspace；KRG 缓存指纹使用 boot ID 以及 vmlinux/模块的路径、大小、mtime，显式 `--krg` 则可复用给定图。它们不是 carrier 与当前内核的独立运行时身份校验。[manager](../page_cache_replace/manager.cpp) 的 page-map 检查关注语法、对齐、范围和文件内偏移；内核请求也没有 build identity 字段。实验 guest 固定检查内核 release，只能证明相应会话的前置条件。正文已删除“运行端拒绝 build identity 不匹配 carrier”的完成式，保留每次部署需核实构建及运行地址的要求。此核对没有修改工具或注册机制。

**分析器性能修订已落地：** hex_dump_to_buffer 的直接目标查询缓存方案已应用并通过边界/实际镜像查询对照；固定八例在新目录完整重检。保持符号顺序、首匹配及全部判定规则，早期六例记录仍原样保留。修订批次现为 2 PASS/6 FAIL，完整计数见[适用范围证据](../test/evaluation/applicability-evidence.md)。

**第 4 例依赖展开已解释（2026-09-12 06:56 UTC）：** 对原进程日志的只读快照恢复了 `hex_dump_to_buffer → snprintf → vsnprintf → format_decode → __warn_printk → vprintk`，继而沿调度、错误处理、回收及 swap/discard 扩展到 `blkg_create` 的 44 条首次入队祖先边。精确 119 ELF 的八条关键边核对确认，入口传入固定格式，而后续包含通用格式警告和调度器损坏检查分支。分析器逐条扫描整个函数、不按调用参数专化；已在 vmlinux 中定义的 `vprintk` 也不会被仅对 undefined symbol 生效的 Shim 规则截断。这解释了静态依赖规模的扩张，不说明这些分支在同一次运行中可达，也不是第 4 例的最终结果。见[原始摘录与独立重建](../test/evaluation/results/applicability-path-20260912/README.md)。原检查继续运行，固定八例、源码和 Shim 未改。

**后续终态更新（2026-09-12 08:02 UTC）：** 原检查已完成六例。新增 `hex_dump_to_buffer` FAIL，访问 1,834 个函数，记录 3,537 条绝对地址和五条特权/控制寄存器问题；其 716 条不可分析记录涉及 347 个不同函数，不能按原字段标签误写为 716 个函数。`string_escape_mem` 因四处绝对地址引用 FAIL，`sort` 为 checker PASS，但仍记录五个 retpoline 包装的间接点。当前共 2 PASS/4 FAIL，第七例 `rhashtable_insert_slow` 执行中，最后一例尚未开始；不将未完成候选计为失败或从分母删除。全部候选尚无本批 carrier/runtime 结果。见[六例记录和计数核对](../test/evaluation/results/applicability-terminal-20260912/README.md)。未停止、重启或修改原检查。

**执行更新（2026-09-12）：** 已启动固定 8 个 API 的普通账户顺序静态检查，输出 `test/evaluation/results/applicability-static-20260912/`；xxh32、crc32_le、sha256 的结果已落盘，完整矩阵仍在执行。[语义核查记录](../test/evaluation/applicability-semantics.md)已区分八例的 caller-owned state、只读依赖、callback 与 kernel-private state。当前 `/proc/kallsyms` 地址均被屏蔽为零，checker 的 runtime 展示列不可用；源码确认其只影响地址展示，静态判定仍使用配置 ELF。该 ELF 的 `.rodata` 带 WA 标志，不能把 checker 的 WRITABLE 标签当作内核运行时可写证据。未构造/注册 carrier，也未改变 checker 或访问限制。

**实际执行更新（2026-09-11 17:51 UTC）：** [固定清单](../test/evaluation/applicability-candidates.json)纳入 `xxh32`、`crc32_le`、`sha256`、`hex_dump_to_buffer`、`string_escape_mem`、`sort`、`rhashtable_insert_slow`、`get_random_bytes` 八个本批待检查 API，按显式输入、只读表、内部闭包、可变输出、callback、同步环境和私有状态等差异选择；LZ4/BCH/XZ/Clocktime 四个已知集成单独作为回顾性案例。该清单是有意选择的分层案例，不能用总成功率估计 Linux 整体可复用比例。“本批待检查”不表示仓库从未探索过 xxHash 或 copied closures。

[检查入口及口径](../test/evaluation/applicability.md)保留每个 API 的完整静态 manifest、编译插桩/间接控制流计数、carrier 构造结果及单独的 runtime 状态；不会注册页面或调用新导出的函数。核对发现当前 checker 的 PASS 可伴随插桩和间接跳转记录，故不能直接归并为“完整成功导出”。同步/私有 RNG 状态两例先做静态检查，语义未解决前不构造 carrier。Python 解析及计划入口验证已通过，早期执行曾被 active Clocktime 服务拒绝；现在原八例检查已启动，xxh32 为 checker PASS，crc32_le/sha256 为 checker FAIL，第四例 hex_dump_to_buffer 仍在展开依赖，其余四例尚未进入。已有结果未执行 runtime 验证，不能写成应用成功率。

共同修改位置：[builder](../make_dll/)、[分析器](../kernel_cgd/)、[vkso 入口](../vkso)，以及新增的固定候选清单和导出记录。先规定清单与分类字段，再批量尝试候选；现有算法和 Clocktime 作为已检查案例纳入相同口径。

将候选集在尝试导出之前固定：从一个明确 Linux 版本/配置的若干功能目录中，按导出 API、功能类别和可公开输入状态规则取样，保留成功与失败。前次提出的 20–30 个入口、5–8 类仅是预算示例；下一步先列已有案例及尚未覆盖的依赖/构建类型，再确定有限清单与成本，不为达到数量增加相似目标。若每类只有少量目标，应称为分层案例研究，不能报告“Linux 百分之多少可复用”。

结果分为：无语义改造即可导出；地址/依赖绑定后导出；需要状态或接口重构；语义不适合；语义可能适合但当前工具不支持。`unresolved indirect target` 和 `privileged kernel state` 应分开，前者可能是分析器限制，后者是语义边界。

每行给出 closure 函数数、text/RO 页数、PGOT slots、helper 类别、人工改动类型与 SLOC、编译限制，以及最终是否在 kernel/user 两端正确执行。不要把成功静态检查、构造 DSO 和运行成功合成一个“成功”；copied-closure-only 目标不能算已经 rehosted。人工工时只有真实记录才报告，不能从 diff 行数反推。

本类完成时：候选分母固定且失败项不丢失；语义不适合与工具暂不支持分开；静态检查、carrier 构造、实际运行分别记录；每个成功目标列出 closure/页数、绑定、编译限制和真实人工改造量。C 类已有适配证据直接导入，Clocktime 既有结构性重构与本轮仅新增测量工具分开记录。候选失败先归类并保留；涉及导出器等基础功能修改时先报告原因，不把修复全部失败候选或全候选性能重测作为本类默认任务。

**源码适配量更新（2026-09-12）：** [三算法账本](../test/evaluation/results/adaptation-ledger-20260912-attempt02/README.md)归档了 Linux 5.15 安装源码基线、当前完整适配源文件、支持文件和差分。BCH/LZ4/XZ 分别涉及 1/3/8 个比较文件，新增/删除有效代码行为 37/9、45/7、52/9；module metadata 与 Kbuild 单列。差分行数与补丁一致，三组补丁均重放得到完整适配源文件。该基线可能含 exact119 二进制之后的 5.15 backports，不能用它宣称精确重构发行版二进制。此处未计通用 builder/shim、用户对照兼容层和测试工具，也没有从行数推算工时。D 仍需合并 Clocktime 既有结构性适配，以及成功案例的 closure、slots、页和构建限制，不能将这份源文件账本当作完整适配成本。

**E 类：真实应用集成。**

**修改后完整应用已通过（2026-09-12）：** [binding attempt06](../test/evaluation/results/lz4-binding-qemu-20260912-attempt06/result.json)在 exact119 guest 中完成实际分析、构造、注册及全部 12 个 Silesia 文件 × 64 KiB/1 MiB 的压缩、解压和 stock 交叉校验。48 份调用记录核对到选中 carrier，三个私有 slots 的目标为唯一 libshim bridge 及 libc helper。独立 observer 的四张 text 页和一张 rodata 页与 kernel PFN 相同；释放后五个偏移的新映射均不再指向源页，模块正常卸载。该旧归档注册期间 owner refcount 为零；后续 v2/v3 的引用和事务证据见 B 最新记录。本次没有性能样本。先前 KVM 启动限制已解除；BTF 和 guest `libdl.a` 准备问题修正后运行通过，失败尝试仍单独归档。见[完整应用记录](../test/evaluation/lz4-application-evidence.md)。

**完整 helper 绑定路线已实现：** [LZ4 绑定契约](../test/evaluation/proposals/lz4-helper-binding.md)将完整 owner 的外部 memory-helper 调用接入三个私有数据 slots，并由显式数据重定位契约绑定到现有 libshim 中唯一命名、负责栈对齐的用户入口。Owner 候选保留全部 21 个函数；bridge、builder/vkso 集成和 resolved-binding 归档均已编译验证。新的 guest 构建已准备，但当前 host 没有 `/dev/kvm`，因此尚无修改后 owner 的注册或应用运行结果，不能沿用旧失败前的性能数据。

**真实 registered carrier 失败已定位（2026-09-12）：** 精确 `5.15.0-119-generic=5.15.0-119.129` 私有 guest 执行实际 KRG、原静态检查、carrier 构造和注册。第六次尝试重新构建未改动的当前 owner，独立 loader 进程逐页确认三个 RX text 页和一个只读 rodata 页的 user/source PFN 一致；完整 CLI 仍在首个 dickens/64 KiB 压缩操作中 SIGSEGV，完成 0/24 个 input/block 组合。GDB 记录证明：内核 memset 直接调用位移 −1049945565 平移到用户 call 地址后，计算出的 `0x7fffb94398a0` 与实际 RIP 完全相同，且目标未映射。Exporter 把该依赖列为 undefined Shim import，却没有重绑定共享 text 中的直接调用或保留目标页。这是已确认的运行时闭包绑定失败，不是性能结论。恢复后的四个新映射 PFN 均不同于源页，随后模块卸载成功；该观测不证明原字节恢复或存活旧映射撤销。[完整证据记录](../test/evaluation/lz4-application-evidence.md)保留六次尝试、构建差异、GDB 与 PFN 原始记录。未修改基础 exporter；准确拒绝的补丁方案已准备，完整调用绑定和应用矩阵仍待完成。

**实际验证更新（2026-09-12）：** 完整 stock/adapted CLI 编译通过；使用 upstream-default 与实际 Linux-source no-SIMD 普通用户 DSO，在全 12 个 Silesia 输入、64 KiB/1 MiB 两种块大小的 48 个案例中验证了真实 API 调用、目标 DSO、公共 stock 压缩输入的解码及 stock 对 adapted 输出的交叉解码，完整输出均匹配。这些是功能验证，不产生正式吞吐结论。Live registered carrier 的后续失败见上方更新，C 的完整性能部署仍待执行，详见 [LZ4 CLI 验证记录](../test/evaluation/lz4-cli/README.md#build-and-ordinary-dso-validation--2026-09-12)。

**实际执行更新（2026-09-11 17:51 UTC）：** 已选择[完整 LZ4 CLI 文件工作流](../test/evaluation/lz4-cli/README.md)，沿用 upstream 1.9.3 的 CLI、framing、内容校验及文件 I/O，通过独立块压缩/解压接口接入现有 carrier。四个对照为原版 CLI、upstream DSO、同源 Linux DSO 和 kernel-backed DSO；输入为完整 Silesia 文件，64 KiB/1 MiB 独立块，每部署四轮，使四个后端在每个输入/块配置下各占一次运行位置。解压使用相同的原版编码输入，各编码器输出也经原版解码和完整文件校验；调用计数/目标 DSO 验证单独执行，不混入计时。

编译入口、适配层和采集程序已写好，并以 `--with-lz4-workflow` 接入 C 的三次完整 LZ4 部署。Python/脚本语法、计划配置和不等大小文件的聚合计算已检查；当时为避免干扰 Clocktime，未编译或执行真实应用；2026-09-12 已完成上段所列编译和普通 DSO 功能验证，正式性能结果仍待采集。该实验测缓存已热、buffered I/O 的完整进程成本，不主张持久化写入吞吐、支持所有 CLI 选项或删除整个应用中的所有原版代码；实际 PFN 关系仍由 B 的观测补齐。

共同修改对象是一个选定应用的实际调用链与完整工作流。依赖 A 或 C 中选定接口和构建稳定，不需要等待无关类别完成。选定 Clocktime 或 LZ4 等一条集成路线后，集中处理 API/装载接入、正确性和应用测量。

如果要说明 1–2 cycles 的调用差距对应用是否重要，使用一个确实频繁调用时间接口的现有应用，并确认调用落在最终 VKSO 公开入口，报告吞吐/延迟和功能等价；也可为 LZ4 选择真正使用其接口的端到端工作流。应用应按实际调用路径选，而非为了出现 Redis/Nginx 名字。当前 Clocktime 已是完整子系统案例，不能说“没有任何 end-to-end”；但它仍不是服务级的应用收益证明。若主要贡献是去重复且性能接近，应用结果检验真实使用代价；若主打应用加速，它直接承担该主张的证据。

本类完成时：有证据表明目标工作确实经过最终 VKSO 接口；对照两侧完成相同工作；报告完整工作流吞吐/延迟及适用的资源成本。无需为增加应用数量而接入多个不使用目标功能的系统。

**F 类：论文、表图和实验报告同步。**

共同修改位置：[当前完整草稿](../paper/paper_content/Paper%20Draft.md)和各实验的结果报告。每一类完成后更新其对应段落，最后统一全文口径。A–E 的工作分类用于执行，不要求论文也照这个顺序组织。当前已修改正文中可由现有证据确定的算法重复单位、Table 2 和部署说明；数值表保留原归档身份。

A 完成后，正文已更新重复单位与隔离核配置、Normal 三方法定义、普通内核 reader、多 reader/固定负载、writer action-zero 统计范围和 PFN 计费说明。表 13–14 保留已有代码规模证据，表 15–20 改用完整新 Normal 数据。摘要、Introduction 与 Conclusion 同步改为约 0.92% 的接口等权平均开销，并保留短入口代价和 writer 启动间变化；不再概括“不牺牲稳态性能”或“稳定降低 UPDATE 长尾”。B–E 的后续证据尚未补齐，F 整体验收仍待完成。

**新增证据的整体口径核对（2026-09-12）：** 引言已将“无法满足约束的目标不会进入流程”改为设计条件，避免与当前 LZ4 错误放行相冲突。摘要、引言和结论的零开销表述限定到字节一致的 XXH32 hot-call 对照；摘要/引言保留 BCH 20.9% 的具体退化，结论明确 BCH 所测库/owner 范围没有净节省。Evaluation 的问题组织纳入资源账本、完整应用及注册行为，setup 与复现说明区分 KVM 功能/采集验证和旧物理机性能，补上表 21–22 的来源。性能表数据未改，新增内核端工具通过不视为物理机内核成本已经测得。

正文的实验组织建议是：先列 RQ 与候选/闭包特征，再用简洁案例说明去重复的实际收益；接着给 setup 和机制成本、真实算法与 baseline、Clocktime 两端性能和并发，最后给边界验证表。正文保留 first-touch 三状态、Data/Func-PGOT、完整 copied closures、LZ4/BCH/XZ 和 Clocktime 的关键结果。work-placement sweep、细 PMU 表、sequence diagnostic 与重叠 SLOC 口径适合附录；此处仅建议，没有移动或删除现有内容。

无需为了“全面”增加十个相似算法、无限扩展硬件矩阵、做全 Linux 自动语义证明，或强行复现与本系统接口不相同的 prior systems。最接近用户选择的正式 baseline 仍是普通同源 DSO、合理优化的用户实现和原生 vDSO；源码复用/复制计算体的对照用于分离物理共享价值。syscall/IPC 对照只在确实提供相同语义且论文要论证避免跨域成本时加入，不能用其较高固定成本替代普通 DSO 这一严格基线。

统一处理 run/boot/process/deployment 定义、描述分位数与置信区间的区别、吞吐比与延迟比方向、SLOC/符号字节/物理页计费范围，以及条件 first-touch 与部署总时间的区别。保留 BCH 异常、Clocktime 短路径代价和受控 residency 条件；尚未采集的项目只写入工作记录，不作为论文结果。

本类完成时：每个主张指向相应完整实现的结果；新表和已有表单位一致；正文/附录分工明确；待验证内容与已完成实验分开。原始数据保持原样，不通过修改数据来适配文字。

当前 A/D 已完成既定交付并同步论文。B 已完成注册、FIFO、普通 ext4 文件/VMA、setup、规模扫描、原始 first-touch 和一次实际回收压力的 guest 验证；继续匹配的正式 setup 性能、完整物理计费、源页公开性与运行时重写边界。C 已完成三算法当前 owner 的同一注册两域完整功能及内核采集入口，继续独立正式部署、物理机内核成本和 BCH 退化归因。E 已完成实际 LZ4 接入和完整四后端 workflow，正式应用性能复用 C 的部署会话采集。F 已加入内核执行小节并更新适配表，待 B/C/E 结果后统一正文/附录、图表与全文口径。

前次核查包括：阅读 Evaluation/Implementation/Discussion，核对 first-touch/PGOT/算法/Clocktime 的材料，复算 first-touch 汇总和 BCH 报告点，检查 XZ 重复层次、Clocktime 功能记录及所列公开文献。本次继承这些证据记录，没有重复执行这些核查或将其视为最新数据。

前次报告修订核查了旧评估、草稿、分支改动、Clocktime 协议及功能/采集记录，并纠正工具缺失、归因、PFN 和预算等判断。当前实际执行又完成 C/F 的重复单位核实与修正，检查三算法旧 raw 矩阵、重算 BCH 四组对照点，并重新核对三篇主要论文的 Evaluation；B 已追踪实际注册及恢复路径，记录 module-reference、完成结果和部分失败处理的证据缺口。D/E 的固定案例、完整 CLI 接入与采集入口也已准备，并已安装完成后的自动接续服务。此后已完成 Clocktime 全量采集、核验和正文更新，未更改冻结协议。完整算法部署变化、实际应用性能和全系统净内存仍待相应证据。
