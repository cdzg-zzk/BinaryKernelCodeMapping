# 核心文件入口（路径相对包根）

## 先恢复目标、版本和证据

- `HANDOFF_PROMPT.md`：完整任务与授权边界。
- `repo/test/section65/STATUS.md`：上一轮完成状态及最终结果。
- `repo/test/section65/claim-experiment-map.md`、`claim-verdicts.json`：主张、实验、判定和限制。
- `repo/test/section65/squashfs/refinement/PROTOCOL.md`、`RESULTS.md`、`README.md`：固定矩阵、取舍与复现。
- `repo/test/section65/backend-conditions.md`：各 baseline 真实配置与计时范围。
- `repo/paper/filesystem-section-preview.pdf`：当前完整论文预览。

## XZ 诊断和实现入口

- `repo/test/section65/squashfs/refinement/build_xz.py`、`xz_services.h`：共同 XZ 的准备/绑定。
- `repo/test/section65/squashfs/posix_io.c`、`build_user.py`：用户模式、解码器选取和依赖。
- `repo/test/section65/squashfs/refinement/decoder_controls.py`：同 owner 的解码/依赖诊断对照。
- `repo/test/section65/build/squashfs/refine-xz-01/`：实际当前源码、对象、模块、用户前端、Makefile/命令。
- `repo/test/section65/build/squashfs/evaluation-improved-01/build/`：上一版同类构建。
- `repo/test/section65/build/native/linux-5.15.198/lib/xz/`：同源原始 XZ 文件。
- `repo/test/section65/build/native/linux-5.15.198/fs/squashfs/xz_wrapper.c`：原生调用模式参考。

## 缓存与实际应用入口

- `repo/test/section65/squashfs/user_bridge.c`：inode/name 与块缓存、生命周期、共同格式核心的服务绑定。
- `repo/test/section65/squashfs/fuse_frontend.c`：文件/目录句柄和请求处理。
- `repo/test/section65/squashfs/apptainer_helper.c`：真实 fd/partition offset 参数转换。
- `repo/test/section65/squashfs/apptainer_bench.py`、`apptainer_shared.py`：真实应用、结果验证、资源和 PFN。
- `repo/test/section65/squashfs/native_cost.py`：原生配对、格式与 fresh/warm 对照。

## 数据和复算

- `repo/test/section65/squashfs/refinement/formal-queue.json`：当前 30 个完整 campaign 的唯一正式选择。
- `repo/test/evaluation-local/runs/iso9660/`：选定的原始样本、环境、日志、PFN 和诊断。
- `repo/test/section65/build/squashfs/refined-analysis-01/`：403 项比较、独立复算、成本/资源、正文数字。
- `repo/test/section65/squashfs/refinement/analyze.py`、`audit.py`、`resources.py`：生成这些结果的代码。
- `repo/test/section65/build/squashfs/refinement-reuse-audit-03/`：内核消费者和组合补丁、代码分类。
- `repo/test/section65/build/squashfs/refinement-baseline-audit-02/`：LKL heap pilot 与 stock helper 核对。

## 维护、调试和论文

- `repo/test/section65/squashfs/maintenance.py`、`maintenance_guest.py`、`maintenance_reference.py`。
- `repo/test/evaluation-local/runs/iso9660/squash-maintenance-02/`、`squash-refine-xz-guest-01/`。
- `repo/test/evaluation-local/runs/iso9660/squash-refine-xz-execution-01/`、`maintenance-oneshot-01/evidence/debug/`。
- `repo/paper/paper_content/sections/06-evaluation.tex`：canonical Section 6.5，其他小节保持原样。
- `repo/paper/plot_filesystem_refined.py`、`build_filesystem_section.py`。
- `repo/test/section65/squashfs/refinement/write_section.py`、`section65-template.tex`。
- `repo/test/section65/build/squashfs/evaluation-refined-02/`：上一轮最终冻结，禁止原地改写。
- `repo/paper/build/section65-composed-publication-01/`：前版 39-campaign 论文与材料归档。

原始数值和路径保持原样；部分 JSON 内绝对路径指向原工作区。仅有本包时，不要声称
已在缺少镜像/SDK 的环境中完成硬件复现。缺失大资产见 `EXTERNAL_ASSETS.json`。
