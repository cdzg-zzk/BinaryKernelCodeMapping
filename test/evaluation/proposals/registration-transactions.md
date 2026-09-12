# 注册、引用和恢复的统一修订方案

状态：供用户审阅，尚未实施。此方案涉及项目基础机制，不能由补实验的授权自动推出实施授权。现有 Clocktime 冻结采集及原始结果保持其原版本身份。

## 已复现的问题与需要达到的行为

[隔离记录](../registration-evidence.md)已观察到两项直接影响契约的问题：活跃注册没有增加 owner module refcnt；同批次第二页解析失败时，第一页仍已注册，manager 仍建立 ready 并报告成功。恢复阶段也出现内核报错而 manager 返回 0。正常成功路径的 PFN/COW/释放验证不能补足这些缺口。

一次完整修订应达到：全部源 owner 在页面解析前被引用；完整计划验证后提交；内核确认成功才启动使用者；失败回滚全部已提交绑定并返回实际错误；恢复完成并撤销源页用户映射后，最后释放 owner 引用。若恢复仍有残留，保留资源和可恢复状态，不能继续报告成功或卸载 owner。

## Owner 元数据与页面归属

当前可用的模块接口包括 `__symbol_get()`、`__symbol_put()`、`try_module_get()` 和 `module_put()`。后两者要求先安全取得 `struct module *`；`__module_address()`、`find_module()` 和 `module_mutex` 不是当前外部 LKM 可以直接使用的接口。通过私有符号地址查找调用它们不属于此方案。

采用 owner 合作的 descriptor：每个参与导出的 owner 提供一个唯一命名的 `EXPORT_SYMBOL_GPL` 对象，包含 descriptor ABI 版本、`THIS_MODULE`、构建身份及允许导出的完整页范围/类别。注册模块先调用 `__symbol_get(descriptor_name)` pin owner，再读取 descriptor，核对运行 manifest，并使用 `within_module_core()` 及允许范围逐页验证归属。拒绝 init pages；每个贡献页面的 owner 都必须覆盖，同一事务内同一 owner 只计一份引用。完整恢复后用 `__symbol_put()` 对称释放。

需要共同修改三个算法 owner 的元数据，而不能假设它们现有导出相同：BCH 已有 GPL-only API anchors，LZ4 当前为普通 `EXPORT_SYMBOL`，XZ 没有导出 anchor。项目 5.15.198 的 `__symbol_get()` 拒绝非 GPL-only 符号。Descriptor 使用独立、完整对齐的管理元数据页，builder 明确排除这些页，不能因当前“导出完整 text/rodata 范围”的规则把包含 `THIS_MODULE` 的管理对象一起暴露。其新增驻留页和布局变化单列计费；新构建必须重新生成 carrier。

该路线覆盖提供 descriptor 的完整 owner，包括注册前已经驻留的 owner。若还要求无需 owner 合作地支持任意现存模块，需要另行增加受锁保护的内核 owner-lookup/pin helper；这属于更大的内核接口改动，未纳入默认方案。Built-in kernel pages 没有可卸载 owner，其页类型、范围和公开性仍需显式验证。

## 页面管理器与事务协议

`page_cache_replace/page_cache_replace.c` 与 `manager.cpp` 共同改用明确版本的事务协议。请求包含 transaction ID、sequence、operation 和实际长度；响应包含内核 errno、状态、已处理页数及失败位置。Controller 身份使用内核收到的 sender 信息，权限检查与特权 manager 边界一致。

完整计划分批 STAGE，最后 COMMIT。256 页保留为传输分块上限，不能继续作为静默溢出的全局备份容量。提交前完成文件范围、溢出、对齐、重复项、全部 owner、页类别和资源分配检查。每个事务持有目标 file/inode、完整计划、owner pin 集合、源页及原管理字段、实际 applied 标记。索引必须包含事务和 mapping，不能只用 file offset。

Manager 保持接收 socket，匹配 sequence/transaction ID 并等待真实结果。成功 COMMIT 后才建立 ready，删除目前两处 `sleep(2)`。超时表示状态未知，通过 QUERY 查询；RESTORE 按事务幂等执行，不能盲目重复替换。`vkso` 和算法 runner 必须传播恢复错误，不能吞掉错误后继续卸载 owner。

当前单个 `struct page` 的 `mapping/index` 会被注册操作改写。同一源 PFN 同时注册到不同 inode 必须明确拒绝，直到另有支持该场景的设计；多个进程使用同一 carrier 仍然共享该绑定。这个限制需进入接口契约与 B 的验证记录。

## 写保护、回滚和释放

在首个页面修改前建立文件写访问限制，检查已有写打开和可写共享映射，处理原 cache page 的 dirty/writeback 状态和错误。`deny_write_access()`、`mapping_deny_writable()` 及 immutable 的启用顺序需一起验证；不能仅将 immutable 提前就宣称完成整个 VM/file 契约。

回滚按实际成功记录逆序处理，确认当前 backing 属于该事务；某页恢复失败仍继续处理其余页并汇总错误。恢复锁序须结合原生 file fault：阻止新 fault 取得待撤销 backing，移除对应 cache entry，撤销源页 user PTE 并完成失效，再恢复源页管理字段，释放页引用，最后释放 owner pin。原文件恢复方式是重新从文件取得内容，并非恢复此前已删除 cache page 的身份。

恢复未完成则进入 `RECOVERY_REQUIRED`，保留必要的 owner/page/file 引用和文件保护状态。现有 restore 函数不能直接充当可靠回滚：它不验证当前 entry 的 source identity、部分错误路径引用不平衡、遇首错就停止，并依赖未持 file 引用的 mapping。

“失败返回前撤销全部绑定”和“所有并发观察者始终看不到提交中间状态”是不同要求。仅使用 `invalidate_lock` 不能证明后者，因为缓存命中的 file fault 不总取得该锁。新版本至少必须保证应用在成功确认前不由 runner 启动，并完成 B 中已有映射/并发 fault 的提交与恢复验证；更强的并发发布原子性需要实际的 fault/read 发布控制，不能靠措辞代替。

## 修改文件与验收

共同修改对象为：页管理模块、manager、共享协议/descriptor 头、builder/运行 manifest、`vkso` 的 ready/查询/cleanup、三算法 owner 元数据和 runner 的错误传播。Clocktime 核心计算与公开 wrapper 不在改动范围内。

验收使用完整实现，覆盖：全部正常注册；模块引用在活跃期增加并阻止卸载；最后使用者结束后的释放；首/中/末页失败与跨批次失败；ACK 丢失后的查询和幂等恢复；已有映射、私有 COW、文件操作；恢复错误时继续持有引用；多进程同一 carrier；冲突 inode 拒绝。错误注入先在私有 guest 中进行，保留失败记录，不在主机上做活跃卸载试探。

机制通过后，按原 B 计划采集三个真实闭包及 1/2/4/8/16/32 页伸缩性，关联 setup-to-first-valid-result、真实内核完成、PFN/私有支持、owner 新增驻留、manager 和释放结果。相关 C/E 用新 owner/build identity 重新执行；旧结果继续明确属于旧实现。该方案没有完成这些实验，也不缩减原 evaluation-review.md 的验收范围。
