obj-m += bench_kmod.o
bench_kmod-y := \
	bench_kmod_main.o \
	closure_origin.o \
	closure_data_pgot.o \
	closure_func_pgot.o \
	closure_all_pgot.o

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f Module.symvers modules.order bench_kmod_*.ko
	rm -f closure_origin.c closure_data_pgot.c closure_func_pgot.c closure_all_pgot.c
