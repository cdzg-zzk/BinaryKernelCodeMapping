#1.关闭追踪
sudo sh -c 'echo 0 > /sys/kernel/tracing/tracing_on'
#2.将追踪器重置为默认的 nop(这一步会触发内核把插桩改回 nop 指令)
sudo sh -c 'echo nop > /sys/kernel/tracing/current_tracer'
#3.清空追踪日志
sudo sh -c 'echo > /sys/kernel/tracing/trace'
#4.清空所有的追踪过滤规则(如果有的话)
sudo sh -c 'echo > /sys/kernel/tracing/set_ftrace_filter'
sudo sh -c 'echo > /sys/kernel/tracing/set_graph_function'