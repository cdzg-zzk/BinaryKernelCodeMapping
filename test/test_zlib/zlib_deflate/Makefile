obj-m += mz_zlib_deflate.o
mz_zlib_deflate-y := deflate.o deftree.o deflate_syms.o

UBSAN_SANITIZE := n

ccflags-y += -I$(src)
# Keep the generated code easy to read in objdump output.
ccflags-y += -O2 -fno-omit-frame-pointer -fno-inline -fno-optimize-sibling-calls
ccflags-y += -fno-sanitize=all -fno-stack-protector
# Keep pseudo-GOT accesses in data-flow form even when optimization level changes.
ccflags-y += -fno-ipa-cp -fno-ipa-sra -fno-tree-ccp
ccflags-remove-y += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
ccflags-remove-y += -fstack-protector-strong
ccflags-remove-y += -pg -mrecord-mcount -mfentry
ccflags-remove-y += -fpatchable-function-entry=16,16

CFLAGS_REMOVE_deflate.o += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
CFLAGS_REMOVE_deflate.o += -fstack-protector-strong
CFLAGS_REMOVE_deflate.o += -pg -mrecord-mcount -mfentry
CFLAGS_REMOVE_deflate.o += -fpatchable-function-entry=16,16
CFLAGS_REMOVE_deftree.o += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
CFLAGS_REMOVE_deftree.o += -fstack-protector-strong
CFLAGS_REMOVE_deftree.o += -pg -mrecord-mcount -mfentry
CFLAGS_REMOVE_deftree.o += -fpatchable-function-entry=16,16
CFLAGS_REMOVE_deflate_syms.o += -fsanitize=bounds -fsanitize=shift -fsanitize=bool -fsanitize=enum
CFLAGS_REMOVE_deflate_syms.o += -fstack-protector-strong
CFLAGS_REMOVE_deflate_syms.o += -pg -mrecord-mcount -mfentry
CFLAGS_REMOVE_deflate_syms.o += -fpatchable-function-entry=16,16

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
