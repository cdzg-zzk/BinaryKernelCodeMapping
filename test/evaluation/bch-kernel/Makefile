ifneq ($(KERNELRELEASE),)
obj-m += bch_kernel_bench.o
else
KDIR ?= /lib/modules/$(shell uname -r)/build
OWNER_SYMVERS ?= $(abspath ../../test_BCH/kmod/Module.symvers)
MATCHED_SYMVERS ?=

.PHONY: all clean
all:
	@test -r "$(OWNER_SYMVERS)" || { echo "Missing original owner Module.symvers: $(OWNER_SYMVERS)"; exit 1; }
	@test -r "$(MATCHED_SYMVERS)" || { echo "Set MATCHED_SYMVERS to the complete matched-source module's Module.symvers"; exit 1; }
	$(MAKE) -C "$(KDIR)" M="$(CURDIR)" KBUILD_EXTRA_SYMBOLS="$(abspath $(OWNER_SYMVERS)) $(abspath $(MATCHED_SYMVERS))" modules

clean:
	$(MAKE) -C "$(KDIR)" M="$(CURDIR)" clean
endif
