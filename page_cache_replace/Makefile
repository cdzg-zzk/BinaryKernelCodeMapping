obj-m += page_cache_replace.o

KDIR ?= /lib/modules/$(shell uname -r)/build
CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra

.PHONY: all module clean update

all: module manager

module:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules EXTRA_CFLAGS="-fno-inline -g"

manager: manager.cpp
	$(CXX) $(CXXFLAGS) $< -o $@

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
	$(RM) manager

update: module
	@echo "Checking if 'page_cache_replace' module is loaded..."
	@if sudo lsmod | grep -q page_cache_replace; then \
		echo "Module 'page_cache_replace' is loaded, removing page_cache_replace..."; \
		sudo rmmod page_cache_replace; \
	fi
	@echo "Inserting page_cache_replace module..."
	sudo insmod page_cache_replace.ko
	sudo ../disassemble/gdb_disasseble.sh page_cache_replace
	sudo objdump -d -r  page_cache_replace.ko > ../disassemble/page_cache_replace_disassemble.txt
