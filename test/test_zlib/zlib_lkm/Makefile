obj-m += zlib_lkm.o

zlib_lkm-objs := zlib_lkm_module.o deflate.o trees.o crc32.o adler32.o zutil.o

KDIR ?= /lib/modules/$(shell uname -r)/build
PAHOLE ?= pahole
VMLINUX_BTF ?= /sys/kernel/btf/vmlinux
BTF_COMPAT_FLAGS ?= --skip_encoding_btf_enum64

UBSAN_SANITIZE := n

ccflags-y += -I$(src)
# Keep the generated code readable and avoid kernel-side instrumentation that
# would complicate later user-space mapping and binary analysis.
ccflags-y += -O2 -fno-omit-frame-pointer -fno-inline -fno-optimize-sibling-calls
ccflags-y += -fno-sanitize=all -fno-stack-protector
ccflags-y += -fno-ipa-cp -fno-ipa-sra -fno-tree-ccp
ccflags-remove-y += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
ccflags-remove-y += -fstack-protector-strong
ccflags-remove-y += -pg -mrecord-mcount -mfentry
ccflags-remove-y += -fpatchable-function-entry=16,16

CFLAGS_REMOVE_deflate.o += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
CFLAGS_REMOVE_deflate.o += -fstack-protector-strong
CFLAGS_REMOVE_deflate.o += -pg -mrecord-mcount -mfentry
CFLAGS_REMOVE_deflate.o += -fpatchable-function-entry=16,16

CFLAGS_REMOVE_trees.o += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
CFLAGS_REMOVE_trees.o += -fstack-protector-strong
CFLAGS_REMOVE_trees.o += -pg -mrecord-mcount -mfentry
CFLAGS_REMOVE_trees.o += -fpatchable-function-entry=16,16

CFLAGS_REMOVE_crc32.o += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
CFLAGS_REMOVE_crc32.o += -fstack-protector-strong
CFLAGS_REMOVE_crc32.o += -pg -mrecord-mcount -mfentry
CFLAGS_REMOVE_crc32.o += -fpatchable-function-entry=16,16

CFLAGS_REMOVE_adler32.o += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
CFLAGS_REMOVE_adler32.o += -fstack-protector-strong
CFLAGS_REMOVE_adler32.o += -pg -mrecord-mcount -mfentry
CFLAGS_REMOVE_adler32.o += -fpatchable-function-entry=16,16

CFLAGS_REMOVE_zutil.o += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
CFLAGS_REMOVE_zutil.o += -fstack-protector-strong
CFLAGS_REMOVE_zutil.o += -pg -mrecord-mcount -mfentry
CFLAGS_REMOVE_zutil.o += -fpatchable-function-entry=16,16

CFLAGS_REMOVE_zlib_lkm_module.o += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
CFLAGS_REMOVE_zlib_lkm_module.o += -fstack-protector-strong
CFLAGS_REMOVE_zlib_lkm_module.o += -pg -mrecord-mcount -mfentry
CFLAGS_REMOVE_zlib_lkm_module.o += -fpatchable-function-entry=16,16

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules
	$(PAHOLE) -J --btf_base=$(VMLINUX_BTF) $(BTF_COMPAT_FLAGS) $(PWD)/zlib_lkm.ko

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
