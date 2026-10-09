# Normal完整发布图表约定

用途：evaluation候选主图与附录证据图，确定性SVG/PDF输出，PNG预览。
源数据：本目录report.json、histograms.csv，两块原CSV复算见block-0-audit.json和block-1-audit.json。
问题：记录器是否改变VKSO−Raw均值差，以及相近主峰/均值是否隐藏不同占比与尾部。
统计：八次独立启动，每组合两次；全部255,999周期样本保留。块内每曲线是一次启动，不提供总体置信区间。
主图interaction：四负载、每负载两块D点，D=(VKSO−Raw)Current−(VKSO−Raw)Legacy；显示每个块的实测值和零线。
附录density-central：四行负载×两列块，0..1600 ticks，Gaussian σ=3，按全部样本归一化；主峰解释还须引用σ=2/5核验。
附录density-full/ecdf-full：同一面板布局，64..16384 ticks对数横轴，覆盖全部观察值138..13775及密度核尾部；不删尾部。
曲线：Raw灰色，VKSO蓝色；Current实线，Legacy虚线。块图另用圆/方标识两块，不仅依赖颜色。
主图候选全栏；八面板图放附录，不缩为单栏。保留旧no-retpoline图和其源码。
标签：Idle、MONOTONIC、MONOTONIC_RAW、MONOTONIC_COARSE，TSC ticks，Normal，Raw/VKSO，Current/Legacy。
图注职责：区分软件发布覆盖、观察分布和物理因果；主峰身份可变，主峰不代替均值或占比。
复现：../plot_matrix.py导出四套SVG/PDF/PNG，以及完整CDF/density CSV；数值再与原CSV/直方图核对。
