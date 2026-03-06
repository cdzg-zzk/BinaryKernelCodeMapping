# 定义要生成的模块
obj-m += test_btb_jitter.o

# 极其关键：告诉内核编译系统，这个文件包含非标准的汇编指令（如原生的 call *%reg）
# 请跳过 objtool 的 retpoline 静态检查，否则会报 "unannotated indirect jump" 错误并终止编译。
OBJECT_FILES_NON_STANDARD_test_btb_jitter.o := y

# 指向当前系统的内核构建目录
KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

install:
	sudo insmod test_btb_jitter.ko cpu=1 repeats=10 iterations=100 warmup_runs=10
update_new:
	sudo rmmod test_btb_jitter
	make
	sudo insmod test_btb_jitter.ko cpu=1 repeats=10 iterations=100 warmup_runs=10
update:
	sudo rmmod test_btb_jitter
	make
	sudo insmod test_btb_jitter.ko cpu=1 repeats=10 iterations=100 warmup_runs=10