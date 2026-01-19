obj-m += page_cache_replace.o

all:
	make -C  /lib/modules/$(shell uname -r)/build M=$(PWD) modules CFLAGS="-fno-inline -g"
clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
#!/bin/bash
update:
	@echo "Checking if 'page_cache_replace' module is loaded..."
	@if sudo lsmod | grep -q page_cache_replace; then \
		echo "Module 'page_cache_replace' is loaded, removing page_cache_replace..."; \
		sudo rmmod page_cache_replace; \
	fi
	@echo "Running make..."
	make
	@echo "Inserting page_cache_replace module..."
	sudo insmod page_cache_replace.ko
	sudo ../disassemble/gdb_disasseble.sh page_cache_replace
	sudo objdump -d -r  page_cache_replace.ko > ../disassemble/page_cache_replace_disassemble.txt