# 定义要编译的模块目标
obj-m += test_macro.o

# 获取当前正在运行的内核构建目录
KDIR ?= /lib/modules/$(shell uname -r)/build

# 获取当前工作目录
PWD := $(shell pwd)

# 默认目标：先生成头文件，再编译内核模块
all: generated_calls.h
	$(MAKE) -C $(KDIR) M=$(PWD) modules

# 规则：如何生成 generated_calls.h
# 如果 gen_calls.py 被修改，会自动重新生成
generated_calls.h: gen_calls.py
	@echo "Generating 2048 macro calls via Python..."
	python3 gen_calls.py

# 清理目标：清除内核编译产物以及我们生成的头文件
clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f generated_calls.h