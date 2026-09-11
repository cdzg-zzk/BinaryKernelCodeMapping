本报告评估 VKSO 当前 Evaluation 的证据完整性，并按共同修改对象组织后续工作。更新日期：2026-09-11；原评估基线为 `849ecf6`，本次核对的实验修订分支为 `experiment/clocktime-evaluation-revision`，提交至 `9a0e3e5`。输入为前次评估、[当前完整草稿](../paper/paper_content/Paper%20Draft.md)、已有实验归档，以及新增的 [Clocktime 实验说明](../test/test_gettime/vkso-tests/revision/README.md)、[验证记录](../test/test_gettime/vkso-tests/revision/VALIDATION.md)和[采集核查记录](../test/test_gettime/vkso-tests/revision/COLLECTION_NOTES.md)。`paper/paper_draft.md` 是前半部分大纲，不作为当前 Evaluation。前次修订仅更新评估报告与修改规划；目前按用户授权进入实际执行，并逐组更新论文 Evaluation。

**更新结论：Clocktime 的测量工具和对照设计已补齐一批缺口，正式证据仍在采集；整篇 Evaluation 的适用范围、装载成本、净内存和真实使用成本仍需分别闭合。** Clocktime 修订集中在新增 `revision/` 实验目录，没有修改其核心算法、公共 wrapper 或页面注册实现。后续 C/F 工作已修正算法报告及正文的重复单位，尚未用新数据替换旧性能表。因此，应把“实验方法已修订”“功能检查已通过”“正式数据已完成并支持结论”分开，不能把正在运行的实验写成已证明的性能收益。

评估的目的，是回答：哪些 resident kernel computations 可以复用；真正复用了哪些物理页、维护量减少多少；建立与释放成本是多少；用户端和原有内核使用者分别付出什么代价；这些结论覆盖哪些输入、构建和运行条件。性能接近、收益为零或出现退化都应如实进入结论。已有正确性证据直接复用，只补与具体主张相关的缺口。

**本次状态快照（2026-09-11 16:36 UTC）：** `normal-campaign` 的 20 项计划中，前 11 项有完成记录，第 12 项仍未完成；整轮完成标记尚未生成。这是落盘进度，不等于前 11 项已完成全面原始数据审计，更不等于整轮验收。实验已交给 systemd 无人值守执行，运行方法见 [交接说明](../test/test_gettime/vkso-tests/revision/AUTONOMOUS_RUN.md)。本报告不承担持续监测。

| 工作组 | 本轮进展 | 下一步具体交付 |
| --- | --- | --- |
| A：Clocktime | 用户/内核 reader、多 reader、完整代码复制对照、PFN 检查及跨启动采集工具已实现；正式采集中 | 完整结果核验、三种方法的性能表、准确的归因结论 |
| B：页面复用与装载 | Clocktime 已提供局部 PFN 证据；通用 setup、净内存和 lifetime 账本仍未闭合 | 同一注册会话的阶段时间、物理页分类及释放证据 |
| C：PGOT 与真实算法 | 已核实三算法的部署/进程/轮次关系，修正报告生成器，复算 BCH 对照点；完整部署采集入口已准备 | Clocktime 结束后执行完整部署重复，分析 BCH 及实际 owner 内核成本 |
| D：适用范围与导出工具 | 已有成功案例和适配记录；本轮未建立固定候选全集 | 带分母、失败原因、人工改造和构建约束的适用范围表 |
| E：真实应用集成 | Clocktime 是完整子系统案例；本轮未新增服务级应用结果 | 一项确实调用 VKSO 的完整工作流对照 |
| F：论文与结果呈现 | 已修正算法方法段落、表 2 及部署说明；Clocktime 正文仍使用旧单启动数据 | 各类新证据验收后更新结果表，最后同步摘要与结论 |

各组先核对现有材料，列清剩余修改对象、运行成本和验收产物，再集中实施。新增性能采集先验证完整实现和测量路径，再安排正式重复；启动次数、候选数量和硬件矩阵是针对主张的预算，不是统一门槛。当前已运行的 Clocktime 计划保持原样，不因更新本报告而重启或扩大。若任何组确实需要改动项目基础功能，先报告具体不一致与原因；不能把“补证据”默认变成基础功能重写。

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

当前主张与证据的对应关系如下。Clocktime 状态按本轮材料更新；C 已完成重复结构核对及三份旧归档的矩阵检查、BCH 定向复算，其他组尚待逐项执行。“未见”表示在所列正文和归档中未找到足够证据，不等于断言整个仓库从未做过。

| 需要支撑的主张 | 当前可核查证据 | 判断与补充要求 |
| --- | --- | --- |
| grafting 不增加装载后执行路径成本 | 草稿 Table 3；first-touch CSV 中 hot 两侧均为 71 cycles，resident fault 接近 | 有较强受控证据；只能支撑所测单页函数和环境，不能代表部署总时间或所有闭包 |
| PGOT 代价可控且受依赖结构影响 | primitives、retpoline 对照、四个完整 copied closures | 应保留；copied closures 是同域适配实验，不能计入实际成功导出的功能数量 |
| 真实 resident export 保留功能及同源性能 | LZ4/Silesia、BCH、XZ；交叉输出校验和 DSO/page-map 记录 | 有支持但范围窄；要保留 regression、编译限制和 helper 条件 |
| 是具有清楚边界的复用机制 | 设计约束和三个算法、一个状态子系统 | 缺固定候选集合的分母、失败原因、人工改造量及最终可运行比例 |
| 消除了第二份物理执行体并有资源净收益 | Clocktime SLOC/符号大小；新实验已有 VKSO/完整代码复制对照的运行时 PFN 检查；XZ 四页 page map | Clocktime 声明闭包的共享/复制关系已有证据；全系统净内存与其他算法的运行时 PFN/完整账本仍需补齐 |
| 建立后可像普通 DSO 一样使用 | 目前从 dlopen/dlsym 后开始计时 | 建立/绑定/注册成本被排除，setup-to-first-call 和短生命周期成本尚未测量 |
| Clocktime 读写代价可接受 | 正文仍是旧单启动结果；新工具覆盖多启动、1/2/3 reader、普通内核 API、固定速率与饱和负载 | 工具和功能验证已补，正式采集及全面核验尚未结束；新增代码复制对照可分离物理代码后备，不能单独分离 snapshot 布局优化 |
| 保持保护和生命周期契约 | 四个 READ 镜像的 ABI/namespace/fallback 归档；草稿明确正常 loader 权限测试边界 | 已有语义测试，缺针对 VM/file 操作、源模块寿命和部署失败的契约证据；不能用 ABI PASS 替代 |

工作按共同修改的代码、构建和采集流程分成六类。字母只用于引用，不代表重要程度或执行顺序。每类按“确认现有实现和统计口径 → 集中修改 → 验证 → 一次组织正式采集 → 汇总结果”推进，减少同一批脚本或内核镜像反复修改和重跑。实际需要分开的镜像和诊断采集仍保留区别。

| 类别 | 共同修改对象 | 放在一起完成的内容 | 本类交付 |
| --- | --- | --- | --- |
| A：Clocktime 整套实验 | `test/test_gettime/vkso-tests/revision/`、既有结果报告 | 跨启动统计、公开/内核 reader、UPDATE、多 reader、物理代码共享对照、已有 ABI 与代码规模口径 | 已实现的采集计划及待完成的 READ/UPDATE/CONCURRENT 综合结果 |
| B：页面复用与装载 | `page_cache_replace/` 周边观测工具、`test/test_first_call/matrix_bench/`、各导出 runner | setup、注册完成时点核验、PFN/内存计费、权限/lifetime、first-touch 筛选与内存压力 | 一套注册到释放的采集流程，setup/footprint/边界验证结果 |
| C：PGOT 与真实算法 | `pgot_benchmarks/`、`test/test_lz4/`、`test/test_BCH/`、`test/test_xz/` | 重复单位、baseline/构建条件、BCH 诊断、实际适配算法的内核端成本、统一统计 | 完整算法对照表、BCH 诊断及适配记录 |
| D：适用范围与导出工具 | `make_dll/`、`kernel_cgd/`、`vkso`、候选清单 | 固定候选集、分阶段成功/失败分类、closure 特征、人工改造量、构建支持范围 | 候选全集、统一导出记录和 applicability 表 |
| E：真实应用集成 | 选定应用的调用路径和 benchmark 驱动 | 接入已完成的 Clocktime 或算法接口，检查功能，测完整工作流 | 一项真实应用对照及实际 VKSO 调用证据 |
| F：论文与结果呈现 | `paper/paper_content/Paper Draft.md`、各实验报告及表图 | RQ/证据对应、统一单位与术语、补入新结果、保留异常、正文/附录安排 | 与本轮实验版本一致的 Evaluation |

各类之间只传递必要产物：A 已有的 Clocktime PFN 采集方法可供 B 参考，B 再处理其他 owner/装载路径及完整计费，A 无需等待 B 重做相同检查；C 的算法适配记录交给 D，D 不重新测一遍算法性能；E 复用 A 或 C 的完整稳定接口；F 随各类验收更新对应段落，最后统一检查。第二台 CPU 的复测如确有主张需要，分别归入 A/C；内存压力归入 B，不另建一类重复流程。

下面保留原核查证据，并按六类展开修改范围和验收结果。

**A 类：Clocktime 整套实验。**

共同修改位置：[新增实验目录](../test/test_gettime/vkso-tests/revision/)及最终结果报告，复用既有 `baremetal/`、`update-bench/`、`functional/`、`code-size/` 的完整实现和证据。本轮已经集中实现采集工具与对照，不再把内核 reader、多 reader、跨启动控制写成待开发项目。核心 Clocktime、公共 wrapper 和页面注册代码未改，后续首先完成现有采集与分析。

[当前草稿](../paper/paper_content/Paper%20Draft.md)第 307 行和[统一性能报告](../test/test_gettime/vkso-tests/VKSO_READ_UPDATE性能报告_20260801.md)第 570 行明确说，每个 backend/build 正式批次仅来自一次启动。31 个 READ rounds、7 个进程、15 个 UPDATE rounds 都不能估计 boot-to-boot 变化。IQR、P10–P90 目前被正确标注为描述统计，但描述统计不能证明“等效”或小于某阈值。

新的 Normal 计划已经固定为 READ/UPDATE 两类镜像 × Raw/VKSO 两种 backend × 5 次独立启动，共 20 次；每次 VKSO 启动内测 VKSO 与完整代码复制对照，并交替方法顺序。每方法每次 UPDATE 测 19 场景 × 15 轮，读负载 15 秒、writer 记录其内部 13 秒；整轮预计约 19 小时加重启时间。该数量是本轮已经采用的预算，不是获得可信结果的硬性门槛，也不是经功效分析证明充分的样本量。后续其他组分别估算完整路径的小规模验证与正式采集成本，再决定分配；不直接套用五次启动。本轮保留已冻结分配，不改参数或追加次数来追逐有利结果。

以 boot 为汇总和区间估计单位；Raw/VKSO 来自不同启动，不伪装为同轮配对，VKSO/copy 才在同一次启动内配对。no-retpoline 旧归档继续作为机制诊断，不能与本轮 Normal 数据拼接成同一批正式跨启动结果。

对“没有实际性能损失”，先根据使用场景约定可接受退化范围，再报告差异及置信区间；区间包含 0 不能证明等效。对 1–2 cycles 的短路径同时报告绝对差和相对差。UPDATE 的平均值与每轮分位数分别估计，不能把跨轮次 IQR 当成 P99 改善的置信区间。

重新启动本身也不会随机化所有编译链接布局。对固定 `setarch -R` 的 Clocktime 或固定 ELF，要另外做默认 ASLR/多个合法布局的诊断，或限定结论适用的布局；不必对全部 workload 重跑完整布局矩阵。

已增加测试模块，直接批量调用 `ktime_get_ts64`、`ktime_get_raw_ts64` 和 `ktime_get_coarse_ts64`，覆盖普通内核 hres/raw/coarse 入口；功能验证及实际 VKSO shared-core/fallback 调用路径核查已有记录。已有 syscall fallback 继续保留，但不代替这些普通内核 API。下一步在正式结果中并列用户 reader、这三个内核 reader 和 writer，检查成本是否转移到另一端；不能把三个代表性 API 称为所有内核使用情境的覆盖。

Clocktime 的既有设计同时改变共享计算、snapshot 字段组织、发布路径和入口。Raw→VKSO 的 UPDATE 变化只能先视为子系统重构的组合效果。本轮新增的 `compact-split` 复制完整实时 carrier，保留算法、支持代码、虚拟偏移、公共 wrapper 和共享状态，仅让用户代码使用独立物理后备，运行于同一 VKSO 内核。名称中的 compact 不能作为“只改 compact snapshot”的证据。

**修正前次归因规划：** VKSO↔copy 可检验共享与复制代码后备的差异；Raw↔copy 仍混合 snapshot、发布和入口重构，无法单独量化状态布局收益。原报告把后一比较直接解释为布局/发布优化、把前一比较解释为入口重构，隔离程度说得过强，应撤回。当前无需为补全组件排列组合再改基础实现；最终报告先给三种完整方法的结果及其可解释范围。如果之后确实要主张某一布局优化是原因，再单独提出所需实现、成本和验证依据。

旧归档是一个 reader 配正常 writer；新协议已经覆盖 monotonic/raw/coarse × 1/2/3 个独立绑核读进程 × 饱和/每读者 1,000,000 calls/s，并保留 idle writer。读进程使用 CPU 1–3，控制任务使用 CPU 0。后续输出总吞吐、各 reader 成本与实际速率、公平性、writer mean/median/P95/P99；sequence retry 单独作为诊断。该范围是当前四核机器上的最多三个用户 reader，不能外推为大核数或跨插槽扩展性。

固定速率统计包含预热和正式计时调用，采用批次节流。必须检查实际速率和 late batches，不能用相同目标值自动证明相同实际负载；这些数据也不是平滑请求到达或逐请求尾延迟。窗口检查确认 writer 记录位于所有 reader 的负载区间内部。无需为常态并发结论额外提高系统 writer 频率。

采集记录还修正了 writer 的解释：`action==0` 不唯一对应周期 tick，当前 recorder 没有 caller-mode 字段；早期窗口中已有少量 CPU 1/2 记录。因此主结果保持冻结的全部 action-zero 样本，报告实际 CPU 分布，不按预期亲和性删样本或断言其具体来源。如小差异的解释依赖这些记录，再提供 CPU0-only 敏感性结果，并与主结果分别标明。平均值与尾部分位数的改善方向可以不同。

既有四种 Clocktime READ 镜像的 `functional.matrix` 各有 98 行，均包含 namespace lifecycle、exec、setns 和单次 fallback syscall 的 pass 记录；前次核查未发现 `=fail` 行。现有 LZ4/BCH/XZ 也有输出一致性证据。因此“正确性完全没测”不成立。

旧归档 READ 的 20 个入口等权几何平均为约 ±1%，并不意味着每个路径均在 ±1% 内，也不是应用调用频率加权的总体效果。旧性能报告已揭示 `gettimeofday(NULL,NULL)` 约 2 cycles、约 33% 的差异，以及并发 coarse 约 9%–14% 的差异。正文需要同时保留分组、最差真实路径及绝对数；本轮正式结果按相同原则重新解释，不能预设仍得到旧幅度。

本类剩余交付包括：所有计划启动的身份/数据覆盖核验、原始 writer 与汇总值一致性、实际速率/late batches/窗口重叠、ABI/sequence/PFN 记录检查，以及最终三方法结果报告。READ 使用不带 writer recorder 的配置，UPDATE/CONCURRENT 使用 recorder；诊断另采。历史 SLOC/符号规模证据对应既有完整实现，新增测试代码不计入产品缩减。已有 PFN 验证在声明闭包中观察到 VKSO 三个唯一页、复制对照五个唯一页；它证明两张代码页共享关系的差别，不代表全系统净节省两页，也不代替 B 类的开销账本。

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

**当前实现细节会实质影响结果：** [manager.cpp](../page_cache_replace/manager.cpp)第 620 和 668 行在 replace/restore 发出后各有 `sleep(2)`。实际部署总时间必须包含这些等待；机制分解应独立记录 kernel 完成时间和等待/日志等管理开销。固定睡眠不是完成确认，不能简单扣掉 2 秒就把剩余时间当成可靠 registration cost；若后续实现显式完成通知，应作为新实现重新测量并注明区别。

先测三个真实闭包，再增加 1/2/4/8/16/32 页的合成规模扫描，观察页数、批次数、bindings 数的作用；后者只解释机制伸缩性。分别测缓存已热与自然首次装载，若保留 `drop_caches`，把它作为额外控制条件。

用短任务、重复调用任务报告完整耗时。只有稳态每次调用确有节省时，才计算额外 setup 的盈亏平衡调用次数；若稳态持平或更慢，不能给出虚构的“足够多次就回本”，应把收益定位于实现复用或内存。

Clocktime 的 2,639→2,055 B 是 reader symbol closure，减少 584 B 不意味着减少一个 4 KiB 物理页。[XZ DSO audit](../test/test_xz/results/formal-20260806/kernel-dso-audit.md)记录四个 reusable pages，但[审计程序](../test/test_xz/scripts/audit_kernel_dso.py)检查的是 ELF dependencies、exports、relocations 和 page-map 数量，没有读取活跃 kernel/user PTE 的 PFN。不能把此 PASS 写成运行时 PFN 一致性测试。

Clocktime 的声明闭包运行时 PFN 检查已经补入 A；B 应复用其方法和结果，把尚缺的多进程与其他算法 owner 的对应关系、私有支持开销和完整计费补上。对所需目标触达页面后记录 kernel alias 与用户 alias，按物理页去重；正文只给匹配页数和分类。分别统计共享 text/rodata/shared state、私有 PGOT/wrapper/MM_data、carrier 实际驻留页、页表和 manager 元数据；运行前后在同一归因口径内比较。RSS/PSS 可作辅助，不能单独完成跨 kernel/user PFN 的全系统计费。

尤其检查：测试用 `vkso_xz.ko` 等专用 owner module 是原本就提供内核功能的那一份，还是为了实验新增的驻留副本？如果原有内核实现仍保留，必须把两者一起计入净内存；如果其替换了原实现，需说明并验证原内核使用者仍使用完整适配版本。专用模块仍能证明 export 机制，不能自动证明现有内核/用户重复已被消除。Clocktime 的真实替换案例在这方面更有价值。

建议同时报告两个场景：原有目标已经驻留时的边际内存成本，以及为了启用 VKSO 新增加载/常驻目标时的总成本。这样才能评价附件所说的 residency 收益是否免费获得。

结果表字段：`target / native unique pages / VKSO unique pages / shared PFN matches / private bytes or pages / incremental pinned pages / net difference`。无法干净分离的通用基础设施开销单列，而非隐去。跨进程的普通 DSO 本来可以共享文件后备，因此不能将用户 text 节省按进程数线性相乘；还应允许私有支持页随进程数量增长，使小闭包的净收益为零或负。

但草稿第 232 行声称 module/page references 维护 lifetime，第 705 行将普通进程的 mmap/mprotect/文件操作列入威胁模型，第 707 行又说权限测试只覆盖正常 loader。这是需要补证据的明确契约边界。正常退出时先停止 benchmark、再恢复映射和卸载模块，不等于活跃使用者仍在访问时的 lifetime 保证。

最小验证矩阵应覆盖：共享页用户写保护；私有可写数据不落在 kernel PFN；对声明支持的映射操作仍保持不变量；源模块有活跃映射时的卸载/拒绝策略；最后一个使用者结束后的释放；部分注册失败后的回滚；普通 text 页内共置符号的可公开性/隔离布局。mprotect 后若是合法私有 COW，判据应是无法修改 kernel backing，而非强求所有操作都返回同一个 errno。

对 mmap/mprotect/MAP_SHARED 等测试，限定在项目控制的内核和合成测试页，检验契约即可；无须扩成攻击评测或完整 VM 证明。已有 namespace/exec/fallback 案例直接引用，不重复堆测试。建立 `invariant / exercised path / expected behavior / observed result / implementation location` 表，每项明确实际测过的行为。

前次局部查看旧的 `page_cache_replace.c` 未发现 `try_module_get/module_put` 的直接调用，但这不足以证明其他组件没有实现 pinning，本次也未对该机制重新作出缺陷认定。因此应先定位最终运行路径和引用所有权，再决定缺少哪项 lifetime 证据；若确认实现缺机制，按用户约束先报告，不直接修改。普通页面权限也不能证明用户无法跳到所有其他可执行地址，控制闭包保证需保持明确的适用范围。

first-touch 有 expected-fault filtering、IQR filtering 和 accepted-batch 筛选，适合估计给定 fault class 的条件延迟。应一并报告总尝试数、各原因剔除数和未筛选分布；不能用过滤后的结果来声称真实 p99 或“永不发生某种 fault”。若原始日志没有保留被丢弃样本，后续采集需补记录，不能反推。

当前 53.5× 是 Native 已被逐出文件缓存而 kernel backing 仍驻留的受控比例。正文已经写明这一点，无须再把它当成尚未修正的夸大。若将 residency 作为重要收益，再用受控内存压力测实际驻留、minor/major fault 发生率和未经延迟裁剪的 first-use 分布，并记账额外 pinned memory。可加入正常用户 DSO 的预取/常驻策略作为 residency 对照，连同其代价一起报告；不必把特权驻留策略当成默认应用配置。

本类完成时：同一注册会话能关联阶段耗时、kernel/user PFN、共享/私有页计费和释放结果；setup 全程与机制阶段不重复相加；正常路径与针对性边界测试结果分开记录；first-touch 保留筛选前样本和剔除原因。内存压力是该 runner 的一种场景，依是否主张实际 residency 收益决定采集范围，不单独再建部署工具。PFN/权限诊断与无插桩性能采集分开执行。

**C 类：PGOT、LZ4、BCH、XZ 算法实验。**

**实际执行更新（2026-09-11 17:23 UTC）：** [算法证据记录](../test/evaluation/algorithm-evidence.md)已列出基线身份、部署与进程边界、现有原始矩阵和 BCH 诊断目标。三份旧 raw 分别核验 210/1,056/42 行，缺行/重复行变体均被拒绝；四份报告重新生成后，五份数值 CSV 与全部 Markdown 数值表保持不变。LZ4/BCH runner 补齐新工作目录初始化，BCH 修正 root 执行时误把 `-v` 当命令的问题；均为实验 harness 改动，未改项目基础功能。

[完整部署入口](../test/evaluation/algorithm_deployments.py)已准备，每算法先安排三次完整部署，保留原始全量配置，按部署块轮换算法顺序，并为每次 owner 装载/注册保留单独目录、boot identity 和逐行重复身份。三次用于检查重新部署敏感性，不能当作独立启动或等效性证明。当前真实服务检查确认 Clocktime 仍 active，入口按预期拒绝启动算法；待采集结束、恢复原算法内核后执行。该入口尚未经完整部署验收，PMU 诊断及实际 owner 内核端对照也尚未完成。

共同修改位置：[PGOT 实验](../test/test_MICRO/test_MICRO_pseudo_noqemu/pgot_benchmarks/)、[LZ4](../test/test_lz4/)、[BCH](../test/test_BCH/)、[XZ](../test/test_xz/) 的 runner、构建配置、统计脚本和适配记录。先统一统计字段和对照身份，再修改各自 runner；算法专用 harness 继续保留。BCH 的诊断与本类正式算法采集一起准备。

**前次已发现：算法的 outer run 也未必是重新部署。** 草稿第 431 行说每次正式 run 都重新加载 owner module；但 [XZ run.sh](../test/test_xz/run.sh)在进入 benchmark 前只部署一次，[xz-bench.c](../test/test_xz/src/xz-bench.c)第 244–259 行先加载两个 DSO，再在同一进程中循环七个 outer runs。LZ4/BCH 的顶层脚本也把多个 outer runs 交给一次部署下的 runner。因此要明确区分“一次完整脚本运行”和“程序内 outer round”，不能把后者描述为重新注册、重新分配布局或独立启动。现有比值可保留为该次部署内重复；需要部署泛化的结论应另做少量完整部署重复。

对一个经较多改造的算法，比较原内核实现与实际 export owner 的内核执行；两侧语义、工作量和可比构建条件一致，另列 stock 与 export-required 编译条件造成的差异。现有 copied closures 保留为同域 PGOT 机制对照，但不能替代实际 export owner 在内核端的验证。

前次直接从 [BCH raw.csv](../test/test_BCH/results/raw.csv)重算 `t=8 / errors=2 / decode-precomputed` 的 11 个轮内比值，中位数为 `1.209496`，即约慢 20.95%；全部比值范围约为 `1.0777–1.5187`。这支持已报告的负收益方向，同时表明不能只用一个 20.9% 代表所有运行的幅度。这个范围不是置信区间。

先检查轮次顺序、实际输入/错误位置和计时工作是否一致，补若干重新部署的完整重复；之后选最大 regression、相同 t 的 0-error，以及 full-decode 路径作为对照。采集 cycles、instructions、branch misses 和与代码/数据布局相关的 cache 事件，配合反汇编和 helper 调用计数。每次只改变一个可解释因素，验证 slowdown 是否随其变化；计数器相关性不等于因果证明。不需一开始采满所有 PMU 事件，诊断运行也不替代正式无插桩延迟。

保留 BCH，报告“何时退化、幅度多少、能解释到什么程度”；不要通过删去路径或平均其它算法来隐藏它。LZ4 的 upstream/native 对照也应保留：1 MiB 解压吞吐比为 0.9228，含义是吞吐低 7.72%，不是延迟恰好高 7.72%。

[XZ ADAPTATIONS](../test/test_xz/ADAPTATIONS.md)已明确需要关闭 fentry、sanitizers、stack protector、retpoline/return thunks 和 SIMD/FPU，并修复表基址和四类 helper slots。它是很好的第一张 adaptation card，但意味着“Linux 5.15 原生算法”不等于“发行版原封不动的最终代码”。PGOT 或 Clocktime 做过 Normal/retpoline 对照，不能替 XZ 证明其在相同条件下可导出。新增一列“stock/default build、所需修改、完整支持/拒绝”比单纯再加算法更有价值。

LZ4 官方 harness 的最快循环估计的是吞吐能力，不提供请求尾延迟。统一结果表时应保留各算法的实际估计量，不能为了统一格式把吞吐能力、单次延迟和尾延迟混为一项。

第二台 x86 CPU 复测对微架构敏感的 Func-PGOT、BCH 异常、Clocktime 短路径，而不是完整复刻全部矩阵。如果最终声称跨 CPU/发行版泛化，需要相应证据；如果明确限定当前平台，则记录尚未验证的范围。不需要为“通用设计”一句话立即移植另一 ISA，但需要区分通用设计与已实现验证的 Linux/x86-64 原型。

本类完成时：每个结果能定位到 deployment/process/round；同源 baseline、用户实际 baseline 与实际内核执行对照区分清楚；BCH 退化有原始分布及针对性解释；保留 PGOT primitive 和完整 copied closures；算法适配记录交给 D 类直接复用。诊断代码若引入持久运行时修改，正式结果需要在修改后的完整实现上重新采集。

**D 类：适用范围、闭包特征和导出改造。**

共同修改位置：[builder](../make_dll/)、[分析器](../kernel_cgd/)、[vkso 入口](../vkso)，以及新增的固定候选清单和导出记录。先规定清单与分类字段，再批量尝试候选；现有算法和 Clocktime 作为已检查案例纳入相同口径。

将候选集在尝试导出之前固定：从一个明确 Linux 版本/配置的若干功能目录中，按导出 API、功能类别和可公开输入状态规则取样，保留成功与失败。前次提出的 20–30 个入口、5–8 类仅是预算示例；下一步先列已有案例及尚未覆盖的依赖/构建类型，再确定有限清单与成本，不为达到数量增加相似目标。若每类只有少量目标，应称为分层案例研究，不能报告“Linux 百分之多少可复用”。

结果分为：无语义改造即可导出；地址/依赖绑定后导出；需要状态或接口重构；语义不适合；语义可能适合但当前工具不支持。`unresolved indirect target` 和 `privileged kernel state` 应分开，前者可能是分析器限制，后者是语义边界。

每行给出 closure 函数数、text/RO 页数、PGOT slots、helper 类别、人工改动类型与 SLOC、编译限制，以及最终是否在 kernel/user 两端正确执行。不要把成功静态检查、构造 DSO 和运行成功合成一个“成功”；copied-closure-only 目标不能算已经 rehosted。人工工时只有真实记录才报告，不能从 diff 行数反推。

本类完成时：候选分母固定且失败项不丢失；语义不适合与工具暂不支持分开；静态检查、carrier 构造、实际运行分别记录；每个成功目标列出 closure/页数、绑定、编译限制和真实人工改造量。C 类已有适配证据直接导入，Clocktime 既有结构性重构与本轮仅新增测量工具分开记录。候选失败先归类并保留；涉及导出器等基础功能修改时先报告原因，不把修复全部失败候选或全候选性能重测作为本类默认任务。

**E 类：真实应用集成。**

共同修改对象是一个选定应用的实际调用链与完整工作流。依赖 A 或 C 中选定接口和构建稳定，不需要等待无关类别完成。选定 Clocktime 或 LZ4 等一条集成路线后，集中处理 API/装载接入、正确性和应用测量。

如果要说明 1–2 cycles 的调用差距对应用是否重要，使用一个确实频繁调用时间接口的现有应用，并确认调用落在最终 VKSO 公开入口，报告吞吐/延迟和功能等价；也可为 LZ4 选择真正使用其接口的端到端工作流。应用应按实际调用路径选，而非为了出现 Redis/Nginx 名字。当前 Clocktime 已是完整子系统案例，不能说“没有任何 end-to-end”；但它仍不是服务级的应用收益证明。若主要贡献是去重复且性能接近，应用结果检验真实使用代价；若主打应用加速，它直接承担该主张的证据。

本类完成时：有证据表明目标工作确实经过最终 VKSO 接口；对照两侧完成相同工作；报告完整工作流吞吐/延迟及适用的资源成本。无需为增加应用数量而接入多个不使用目标功能的系统。

**F 类：论文、表图和实验报告同步。**

共同修改位置：[当前完整草稿](../paper/paper_content/Paper%20Draft.md)和各实验的结果报告。每一类完成后更新其对应段落，最后统一全文口径。A–E 的工作分类用于执行，不要求论文也照这个顺序组织。当前已修改正文中可由现有证据确定的算法重复单位、Table 2 和部署说明；数值表保留原归档身份。

本次核对确认，正文 Experimental Setup 仍声明 Clocktime 每 backend/build 仅一次启动，表 13–20 仍来自旧代码规模与性能归档。这些数字保留其原来的证据身份，不替换为未收齐的新数据。A 验收后，集中修改重复单位/隔离核配置、Normal 三方法定义、普通内核 reader 结果、多 reader/固定负载结果、writer action-zero 的统计范围和 PFN 计费说明，并同步摘要、Introduction 与 Conclusion 中“约 ±1%”“不牺牲性能”“降低 UPDATE 长尾”等概括是否仍被支持。

正文的实验组织建议是：先列 RQ 与候选/闭包特征，再用简洁案例说明去重复的实际收益；接着给 setup 和机制成本、真实算法与 baseline、Clocktime 两端性能和并发，最后给边界验证表。正文保留 first-touch 三状态、Data/Func-PGOT、完整 copied closures、LZ4/BCH/XZ 和 Clocktime 的关键结果。work-placement sweep、细 PMU 表、sequence diagnostic 与重叠 SLOC 口径适合附录；此处仅建议，没有移动或删除现有内容。

无需为了“全面”增加十个相似算法、无限扩展硬件矩阵、做全 Linux 自动语义证明，或强行复现与本系统接口不相同的 prior systems。最接近用户选择的正式 baseline 仍是普通同源 DSO、合理优化的用户实现和原生 vDSO；源码复用/复制计算体的对照用于分离物理共享价值。syscall/IPC 对照只在确实提供相同语义且论文要论证避免跨域成本时加入，不能用其较高固定成本替代普通 DSO 这一严格基线。

统一处理 run/boot/process/deployment 定义、描述分位数与置信区间的区别、吞吐比与延迟比方向、SLOC/符号字节/物理页计费范围，以及条件 first-touch 与部署总时间的区别。保留 BCH 异常、Clocktime 短路径代价和受控 residency 条件；尚未采集的项目只写入工作记录，不作为论文结果。

本类完成时：每个主张指向相应完整实现的结果；新表和已有表单位一致；正文/附录分工明确；待验证内容与已完成实验分开。原始数据保持原样，不通过修改数据来适配文字。

当前 A 的采集继续无人值守运行，结束后按本报告完成验收和结果解释。其他组可先整理现有归档、对照身份、候选清单和结果表字段；在当前测量机器上新增 benchmark 或构建任务，留到采集结束后安排。后续选择一组时，以其具体交付为边界推进，例如 B 围绕同一注册会话完成时间/页面/释放账本，C 围绕重复单位和构建对照完成算法表。用户已授权按六组推进；当前先完成不会干扰 Clocktime 计时的源码核对、工具准备和文稿修正，后续采集按依赖顺序执行。

前次核查包括：阅读 Evaluation/Implementation/Discussion，核对 first-touch/PGOT/算法/Clocktime 的材料，复算 first-touch 汇总和 BCH 报告点，检查 XZ 重复层次、Clocktime 功能记录及所列公开文献。本次继承这些证据记录，没有重复执行这些核查或将其视为最新数据。

前次报告修订核查了旧评估、草稿、分支改动、Clocktime 协议及功能/采集记录，并纠正工具缺失、归因、PFN 和预算等判断。当前实际执行又完成 C/F 的重复单位核实与修正，检查三算法旧 raw 矩阵、重算 BCH 四组对照点，并重新核对三篇主要论文的 Evaluation。没有更改 Clocktime 冻结协议，没有启动并行 benchmark；最终跨启动性能、完整部署变化和全系统净内存仍待相应证据。
