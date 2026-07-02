obj-m += zzk_xxh32_lkm.o
zzk_xxh32_lkm-objs := zzk_xxh32_module.o zzk_xxh32_kernel.o
CFLAGS_zzk_xxh32_module.o := -mfunction-return=keep
OBJECT_FILES_NON_STANDARD_zzk_xxh32_module.o := y

KDIR ?= /lib/modules/$(shell uname -r)/build
PAHOLE ?= pahole
VMLINUX_BTF ?= /sys/kernel/btf/vmlinux
BTF_COMPAT_FLAGS ?= --skip_encoding_btf_enum64

ROOT := $(abspath ../../..)
MAKE_DLL := $(ROOT)/make_dll
SYMBOLS := $(abspath ../symbols.txt)
KRG := $(abspath ../out.krg)
BENCH_DIR := $(abspath ../matrix_bench)

STUB_SO_BUILD := libzzk_xxh32_lkm.so
STUB_SO := zzk_xxh32_lkm.so
NATIVE_SO := libclone_xxh32.so
LOCAL_SYMBOLS := .stub_symbols.txt

.PHONY: all module native-dso user stub-dso dsos install-to-bench check-asm clean

all: module native-dso

dsos: module native-dso stub-dso

module: zzk_xxh32_module.c zzk_xxh32_kernel.S
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules
	$(PAHOLE) -J --btf_base=$(VMLINUX_BTF) $(BTF_COMPAT_FLAGS) $(CURDIR)/zzk_xxh32_lkm.ko

native-dso user: clone_xxh32_user.S clone_xxh32_min.ld
	gcc -fPIC -O2 -c clone_xxh32_user.S -o clone_xxh32_user.o
	ld -shared --build-id=none --hash-style=gnu -z norelro -T clone_xxh32_min.ld -soname $(NATIVE_SO) -o $(NATIVE_SO) clone_xxh32_user.o
	strip --strip-unneeded $(NATIVE_SO)

stub-dso: module
	cp $(SYMBOLS) $(LOCAL_SYMBOLS)
	python3 $(MAKE_DLL)/build_LKM_so.py --symbols $(LOCAL_SYMBOLS) --krg $(KRG) --shim $(MAKE_DLL)/shim.txt --shim-lib $(MAKE_DLL)/libshim.so
	cp $(STUB_SO_BUILD) $(STUB_SO)

install-to-bench: native-dso stub-dso
	cp $(NATIVE_SO) $(BENCH_DIR)/$(NATIVE_SO)
	cp $(STUB_SO) $(BENCH_DIR)/$(STUB_SO)

check-asm: module native-dso
	python3 compare_xxh32_bytes.py zzk_xxh32_lkm.ko $(NATIVE_SO)

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
	rm -f $(NATIVE_SO) clone_xxh32_user.o $(STUB_SO_BUILD) $(STUB_SO) $(LOCAL_SYMBOLS) resolved_symbol_addresses.txt
