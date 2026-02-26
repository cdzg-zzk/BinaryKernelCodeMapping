#!/bin/bash
# 必须以 root 权限运行

TRACE_DIR="/sys/kernel/tracing"
# 如果你的系统较老，可能是 TRACE_DIR="/sys/kernel/debug/tracing"

echo "Configuring ftrace for Page Fault analysis..."

# 1. 先关闭追踪，清空历史日志
echo 0 > $TRACE_DIR/tracing_on
echo > $TRACE_DIR/trace

# 消除Bad file descriptor报错（你的系统内核 ftrace 环形缓冲区 (Ring Buffer) 还没有被初始化/分配）
echo 1024 > /sys/kernel/tracing/buffer_size_kb

# 2. 设置为函数调用图模式 (树状结构)
echo function_graph > $TRACE_DIR/current_tracer

# 3. 【核心过滤】只追踪 handle_mm_fault 这个函数的内部调用栈！
# 这样能完全屏蔽掉 rdtsc, printf 等无关的系统活动
# echo handle_mm_fault > $TRACE_DIR/set_graph_function

# 4. 允许进程挂起追踪 (我们在 C 代码里自己接管 tracing_on)
echo 0 > $TRACE_DIR/tracing_on

echo "ftrace is ready. Now run your benchmark program."