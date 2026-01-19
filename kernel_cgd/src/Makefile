# Makefile for building and using the `krg` tool (krg.cpp)
#
# Targets:
#   make            - 编译生成 ./krg 可执行文件
#   make krg-build  - 以 root 身份执行 krg 构图，生成 $(OUT)
#   make query      - 以 root 身份对 $(OUT) 执行查询（需传入 SYMBOL=<符号名>）
#   make clean      - 清理中间文件和可执行文件
#
# 依赖：
#   - g++ (支持 C++20)
#   - libcapstone-dev
#   - ELFIO 头文件 (header-only)；ELFIO_DIR 需指向包含 `elfio/` 目录的路径
#
# krg.cpp 命令行用法（完整）：
#   krg build vmlinux -o out.krg [-m module.ko ...] [--debug] [--dbg-sym=<name>]
#     -o <file>           必填：输出图文件（单文件 SAFE 子图，默认示例：./out.krg）
#     -m/--module <file>  可重复：追加模块（.ko / .ko.xz / .ko.gz / .ko.zst）
#     --module=<file>     同上（等价写法）
#     --debug             打印构图日志到 stderr
#     --dbg-sym=<name>    仅聚焦某函数名（配合 --debug）
#   krg query out.krg <symbol>
#     输出：每行 <name>\t<addr hex>\t<size>\t<kind>（kind: 0=code, 1=data），为目标符号的可达闭包
#
# 示例：
#   sudo apt-get update && sudo apt-get install -y g++ libcapstone-dev
#   git clone --depth 1 https://github.com/serge1/ELFIO.git
#   make
#   make krg-build                       # 调用 krg 构图 → 生成 out.krg
#   make krg-build MODULES="a.ko b.ko"  # 追加多个模块
#   make krg-build DEBUG=1 DBG_SYM=memcpy
#   make query SYMBOL=memcpy             # 查询某个符号的闭包并打印运行时地址
#
# 说明：
#   - krg.cpp 中已默认使用 x86-64 + capstone 反汇编，并对可用的 BTF/KASLR 做兼容处理。
#   - 需要 root 权限读取 /proc/kallsyms（查询运行时地址），因此 krg-build/query 目标使用 sudo 调用。
#   - 如果你的 vmlinux 路径不同，可在命令行覆盖 VMLINUX 变量：
#       make krg-build VMLINUX=/path/to/vmlinux
#   - 如果 out.krg 文件名希望自定义，可覆盖 OUT 变量：
#       make krg-build OUT=mygraph.krg

# ---------------- 基本配置（可按需修改/覆盖） ----------------
CXX              ?= g++
CXXFLAGS         ?= -O3 -std=c++2a -Wall -Wextra -Wpedantic -fno-omit-frame-pointer
LDFLAGS          ?=

# ELFIO header-only 库所在目录（应包含子目录 `elfio/`）
ELFIO_DIR        ?= ./ELFIO

# capstone 的编译/链接参数（优先使用 pkg-config，找不到则退回 -lcapstone）
CAPSTONE_PC      ?= capstone
CAPSTONE_CFLAGS  := $(shell pkg-config --cflags $(CAPSTONE_PC) 2>/dev/null)
CAPSTONE_LIBS    := $(shell pkg-config --libs   $(CAPSTONE_PC) 2>/dev/null)
ifeq ($(strip $(CAPSTONE_LIBS)),)
  CAPSTONE_LIBS := -lcapstone
endif

# ---------------- 变量（用于 krg 运行） ----------------
# vmlinux 路径（默认：系统 debug vmlinux）
VMLINUX ?= /usr/lib/debug/boot/vmlinux-$(shell uname -r)
# 输出的图文件名
OUT     ?= out.krg
# 查询目标函数名（make query SYMBOL=xxx）
SYMBOL  ?= memcpy
# 追加模块（空格分隔），如：MODULES="a.ko b.ko"
MODULES ?=
# 调试开关（DEBUG=1 启用 --debug）
DEBUG   ?= 0
# 调试聚焦符号（DBG_SYM=xxx → --dbg-sym=xxx）
DBG_SYM ?=
# DEBUG 日志输出文件（相对当前目录）
LOGFILE ?= build.log

# ---------------- 源/目标文件 ----------------
SRC   := krg.cpp
OBJ   := $(SRC:.cpp=.o)
BIN   := krg
KRG   := out.krg*

# ---------------- 规则 ----------------
.PHONY: all clean krg-build query

all: $(BIN)

$(BIN): $(OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS) $(CAPSTONE_LIBS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) $(CAPSTONE_CFLAGS) -I$(ELFIO_DIR) -c $< -o $@

# 以 root 身份调用 krg 构图（默认使用 $(VMLINUX)，输出 $(OUT)）
krg-build: $(BIN)
	@echo ">> Building KRG graph to $(OUT) using VMLINUX=$(VMLINUX)"
	@cmd="./$(BIN) build $(VMLINUX) -o $(OUT) \
	  $(if $(MODULES),$(foreach m,$(MODULES),-m $(m)),) \
	  $(if $(filter 1,$(DEBUG)),--debug,) \
	  $(if $(DBG_SYM),--dbg-sym=$(DBG_SYM),)"; \
	if [ "$(filter 1,$(DEBUG))" = "1" ]; then \
	  echo ">> DEBUG=1: stderr will be redirected to $(LOGFILE)"; \
	  sudo $$cmd 2>$(LOGFILE); \
	else \
	  sudo $$cmd; \
	fi

# 以 root 身份查询某个 symbol 的闭包（需先执行 krg-build 生成 $(OUT)）
# 用法：make query SYMBOL=<你的符号名>
query: $(BIN)
	@if [ ! -f "$(OUT)" ]; then \
	  echo "ERR: $(OUT) 不存在，请先执行 'make krg-build' 生成图文件"; \
	  exit 1; \
	fi
	@if [ -z "$(SYMBOL)" ]; then \
	  echo "用法：make query SYMBOL=<符号名>"; \
	  exit 1; \
	fi
	@echo ">> Querying symbol '$(SYMBOL)' in $(OUT)"
	sudo ./$(BIN) query $(OUT) $(SYMBOL)

clean:
	$(RM) $(OBJ) $(BIN) $(KRG)
