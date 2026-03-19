obj-m += micro_pseudo.o

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

ifneq ($(wildcard $(src)/micro.c),)
obj-m += micro.o
endif

.PHONY: all clean analyze

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

analyze: all
ifneq ($(wildcard $(obj)/micro.ko),)
	readelf -sW micro.ko > micro.readelf.sym.txt
	readelf -rW micro.ko > micro.readelf.rel.txt
	objdump -drwC micro.ko > micro.objdump.dr.txt
endif
	readelf -sW micro_pseudo.ko > micro_pseudo.readelf.sym.txt
	readelf -rW micro_pseudo.ko > micro_pseudo.readelf.rel.txt
	objdump -drwC micro_pseudo.ko > micro_pseudo.objdump.dr.txt

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f micro.readelf.*.txt micro.objdump.*.txt
	rm -f micro_pseudo.readelf.*.txt micro_pseudo.objdump.*.txt
