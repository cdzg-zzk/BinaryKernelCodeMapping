obj-m += bench_kmod.o
bench_kmod-y := \
	bench_kmod_main.o \
	closure_origin_huf_decompress.o \
	closure_origin_decompress.o \
	closure_origin_entropy_common.o \
	closure_origin_fse_decompress.o \
	closure_origin_zstd_common.o \
	closure_data_pgot_huf_decompress.o \
	closure_data_pgot_decompress.o \
	closure_data_pgot_entropy_common.o \
	closure_data_pgot_fse_decompress.o \
	closure_data_pgot_zstd_common.o \
	closure_func_pgot_huf_decompress.o \
	closure_func_pgot_decompress.o \
	closure_func_pgot_entropy_common.o \
	closure_func_pgot_fse_decompress.o \
	closure_func_pgot_zstd_common.o \
	closure_all_pgot_huf_decompress.o \
	closure_all_pgot_decompress.o \
	closure_all_pgot_entropy_common.o \
	closure_all_pgot_fse_decompress.o \
	closure_all_pgot_zstd_common.o

ZSTD_SRC ?= /usr/src/linux-source-5.15.0/linux-source-5.15.0/lib/zstd
ccflags-y += -I$(ZSTD_SRC)

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f Module.symvers modules.order bench_kmod_*.ko
	rm -f closure_*_huf_decompress.c closure_*_decompress.c \
	      closure_*_entropy_common.c closure_*_fse_decompress.c \
	      closure_*_zstd_common.c
