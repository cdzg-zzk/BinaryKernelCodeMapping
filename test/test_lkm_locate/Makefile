obj-m += lkm_locate.o

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD  := $(shell pwd)

# Keep the generated code easy to read in objdump output.
ccflags-y += -O2 -g3 -fno-omit-frame-pointer -fno-inline -fno-optimize-sibling-calls
ccflags-y += -fno-sanitize=all -fno-stack-protector
# Keep pseudo-GOT accesses in data-flow form even when optimization level changes.
ccflags-y += -fno-ipa-cp -fno-ipa-sra -fno-tree-ccp
.PHONY: all clean analyze usertest check_reloc_guard

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules
	$(MAKE) check_reloc_guard

check_reloc_guard:
	@readelf -rW lkm_locate.ko | awk '\
	/Relocation section '\''.rela.text'\''/ {intext=1; next} \
	/Relocation section/ {intext=0} \
	intext && /R_X86_64_32S/ && ($$0 ~ /\.data \+/ || $$0 ~ /\.rodata \+/) {print; bad=1} \
	END { \
		if (bad) { \
			print "ERROR: forbidden R_X86_64_32S to .data/.rodata detected in .rela.text"; \
			exit 1; \
		} \
	}'

analyze: all
	readelf -h lkm_locate.ko > lkm_locate.readelf.h.txt
	readelf -S lkm_locate.ko > lkm_locate.readelf.S.txt
	readelf -sW lkm_locate.ko > lkm_locate.readelf.sym.txt
	readelf -rW lkm_locate.ko > lkm_locate.readelf.rel.txt
	objdump -drwC lkm_locate.ko > lkm_locate.objdump.dr.txt

usertest: test_liblkm_locate.c liblkm_locate.so ../../make_dll/libshim.so
	gcc -Wall -Wextra -g -o test_liblkm_locate test_liblkm_locate.c \
		-L. -L../../make_dll -llkm_locate \
		-Wl,-rpath,'$$ORIGIN' -Wl,-rpath,'$$ORIGIN/../../make_dll'
	LD_LIBRARY_PATH=.:../../make_dll ./test_liblkm_locate

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
	rm -f lkm_locate.readelf.*.txt lkm_locate.objdump.*.txt
