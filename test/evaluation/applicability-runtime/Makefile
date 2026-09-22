ifneq ($(KERNELRELEASE),)
obj-m := applicability_runtime.o
else
KDIR ?= /lib/modules/5.15.0-119-generic/build
CC ?= gcc
USER_FLAGS := -O2 -g -std=gnu11 -Wall -Wextra -Werror \
	-fno-strict-aliasing -fno-stack-protector -fno-builtin \
	-fno-tree-vectorize -fno-tree-slp-vectorize \
	-mno-sse -mno-sse2 -mno-mmx -mno-avx -mno-red-zone \
	-mfunction-return=keep -mindirect-branch=keep
.PHONY: all module user clean
all: module user
module:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules
user: applicability-user
applicability-user: applicability_user.c engine.h protocol.h
	$(CC) $(USER_FLAGS) applicability_user.c -ldl -o $@
clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
	rm -f applicability-user
endif
