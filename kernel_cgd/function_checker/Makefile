# ==========================================
# LKM Reuse Checker 自动化驱动脚本
# ==========================================

# --- 变量配置区 ---
# 待分析的 LKM 模块列表 (留空则只分析 vmlinux 原生函数)
TARGET_MODULES := 
# 你希望抠出的核心函数入口 (例如内核自带的红黑树插入函数)
ENTRY_FUNC     := rb_insert_color
# 存放 Shim 平替白名单的文本文件路径
SHIM_FILE      := shim.txt
# 自动探测系统当前的 vmlinux
VMLINUX_PATH   := /usr/lib/debug/boot/vmlinux-$(shell uname -r)

# --- Python 脚本名称 ---
CHECKER_SCRIPT := lkm_checker.py

# 智能拼接模块参数
MOD_ARGS := $(if $(TARGET_MODULES),-m $(TARGET_MODULES),)
SHIM_ARGS := $(if $(wildcard $(SHIM_FILE)),-s $(SHIM_FILE),)

.PHONY: all check help clean

all: help

check:
	@echo "=================================================="
	@echo "🔍 启动 Academic Edition 物理页分析"
	@echo "📦 模块   : $(if $(TARGET_MODULES),$(TARGET_MODULES),[无 - 纯 vmlinux 穿透模式])"
	@echo "🎯 入口   : $(ENTRY_FUNC)"
	@echo "🔌 Shim表 : $(if $(wildcard $(SHIM_FILE)),$(SHIM_FILE),[未找到/未配置])"
	@echo "🌐 Vmlinux: $(VMLINUX_PATH)"
	@echo "=================================================="
	@if [ ! -f $(VMLINUX_PATH) ]; then \
		echo "❌ 错误: 找不到 vmlinux。请确认路径 $(VMLINUX_PATH) 是否存在。"; \
		exit 1; \
	fi
	python3 $(CHECKER_SCRIPT) \
		$(MOD_ARGS) \
		-t $(ENTRY_FUNC) \
		-v $(VMLINUX_PATH) \
		$(SHIM_ARGS)

help:
	@echo "LKM Reuse Checker Makefile 用法:"
	@echo "  make check  - 运行 Python 引擎进行跨界静态分析"