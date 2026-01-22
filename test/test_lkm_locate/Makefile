obj-m += lkm_locate.o

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD  := $(shell pwd)

# Keep the generated code easy to read in objdump output.
ccflags-y += -O0 -g3 -fno-omit-frame-pointer -fno-inline -fno-optimize-sibling-calls
ccflags-y += -fno-sanitize=all -fno-stack-protector
ccflags-y += -fno-builtin-memcpy

.PHONY: all clean analyze usertest

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

analyze: all
	readelf -h lkm_locate.ko > lkm_locate.readelf.h.txt
	readelf -S lkm_locate.ko > lkm_locate.readelf.S.txt
	readelf -sW lkm_locate.ko > lkm_locate.readelf.sym.txt
	readelf -rW lkm_locate.ko > lkm_locate.readelf.rel.txt
	objdump -drwC lkm_locate.ko > lkm_locate.objdump.dr.txt

usertest: test_liblkm_locate.c
	gcc -Wall -Wextra -g -o test_liblkm_locate test_liblkm_locate.c \
		-L../../make_dll -llkm_locate -lshim -Wl,-rpath,'$$ORIGIN/../../make_dll'

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f lkm_locate.readelf.*.txt lkm_locate.objdump.*.txt
