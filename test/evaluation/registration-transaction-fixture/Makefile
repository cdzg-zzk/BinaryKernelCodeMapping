obj-m += vkso_tx_fixture.o
vkso_tx_fixture-y := pages.o metadata.o
ccflags-y += -I$(src)/../../../page_cache_replace
KDIR ?= /lib/modules/$(shell uname -r)/build
all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules
