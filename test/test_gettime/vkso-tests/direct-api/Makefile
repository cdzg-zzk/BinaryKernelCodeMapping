# SPDX-License-Identifier: GPL-2.0
SHELL := /bin/bash
HERE := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
FUNCTIONAL := $(HERE)../functional
OUT ?= $(HERE)build
CC ?= gcc
AR ?= ar
CFLAGS ?= -O2 -g -std=gnu11 -Wall -Wextra -Werror -fno-lto -fno-builtin
CPPFLAGS += -D_GNU_SOURCE -I$(HERE) -I$(FUNCTIONAL)

.PHONY: native vkso check
native: $(OUT)/native-bench
vkso: $(OUT)/vkso-bench $(OUT)/libvkso_time_init.a

$(OUT):
	mkdir -p "$@"
$(OUT)/native-bench: $(HERE)time_bench.c $(HERE)vkso_time.h | $(OUT)
	$(CC) $(CPPFLAGS) $(CFLAGS) "$<" -o "$@"
$(OUT)/vkso_time_init.o: $(HERE)vkso_time_init.c $(HERE)vkso_time.h $(FUNCTIONAL)/vkso_abi.h | $(OUT)
	$(CC) $(CPPFLAGS) $(CFLAGS) -pthread -c "$<" -o "$@"
$(OUT)/vkso_user_wrapper.o: $(FUNCTIONAL)/vkso_user_wrapper.c $(FUNCTIONAL)/vkso_abi.h $(FUNCTIONAL)/vkso_user_wrapper.h | $(OUT)
	$(CC) $(CPPFLAGS) $(CFLAGS) -pthread -c "$<" -o "$@"
$(OUT)/libvkso_time_init.a: $(OUT)/vkso_time_init.o $(OUT)/vkso_user_wrapper.o
	$(AR) rcs "$@" $^
# The bundle builder puts a link to the REGISTERED carrier at this exact path.
# Never replace it with a copied/synthetic DSO in a target experiment.
$(OUT)/vkso-bench: $(HERE)time_bench.c $(HERE)vkso_time.h $(OUT)/libvkso_time_init.a
	test -s "$(OUT)/carrier/libkernel.so"
	$(CC) $(CPPFLAGS) $(CFLAGS) -DUSE_VKSO "$<" \
		"$(OUT)/libvkso_time_init.a" -pthread -L"$(OUT)/carrier" \
		-Wl,--no-as-needed -lkernel -Wl,--as-needed \
		-Wl,-rpath,'$$ORIGIN/carrier' -o "$@"
check:
	python3 "$(HERE)tests/test_direct.py"
