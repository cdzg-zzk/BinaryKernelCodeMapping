# READ 图表契约与检查

用途：evaluation 的定量结果图。输入固定为 summary.csv 和 block-deltas.csv；不修改统计口径，不以筛选接口改善图形结论。

主图覆盖七类用户 clock_gettime 与三个普通内核 READ；其他快路径图覆盖五项时间调用和 getcpu；fallback 图覆盖三项 syscall 路径。三图共覆盖 19 个工作负载、两配置，和主表 38 行一一对应。Raw/VKSO 的绝对成本在表中，图展示差值和启动变动。

横轴使用线性 TSC ticks/call、零点线，负方向标为 VKSO 成本更低。每图统一轴同时覆盖所有区间和四块差值，三图因尺度不同分别定轴。蓝圆为 Retpoline，橙方为 no-retpoline，使用 Okabe–Ito 配色；形状保留灰度区分。实心为中位数差，横线为独立启动 95% bootstrap 区间，空心为匹配块差值；重合数据点覆盖绘制。空心点不表示 bootstrap 重采样次数。

输出 SVG、矢量 PDF 和 PNG；read_report.py 以数值位置确定全部图形。可编辑 SVG 保留文本和图形。LaTeX 表是 booktabs 内容片段，由论文宿主提供 booktabs 包和浮动体。

渲染检查：三张 PNG 已逐张查看，轴标签、点、区间、图例无裁切或遮挡，所有区间端点及块差值位于轴内。主图分隔用户与内核接口。fallback 保留 process CPU time 的宽区间。SVG 源图与渲染输出对应，最终核验记录在 verification.json。
