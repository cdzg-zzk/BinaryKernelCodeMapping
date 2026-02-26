obj-m += test_lkm_latency.o

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)
MOD := test_lkm_latency
SUDO ?= sudo

ITERATIONS ?= 1000000
REPEATS ?= 10
WARMUP_RUNS ?= 3
WARMUP_ITERS ?= 100000

ALT2 ?= 1
RANDOM ?= 1
RANDOM_SWEEP ?= 1
RANDOM_TARGETS ?= 16
PATTERN_LEN ?= 4096
SEED ?= 1
CPU ?= 0

PARAMS := iterations=$(ITERATIONS) repeats=$(REPEATS) \
	warmup_runs=$(WARMUP_RUNS) warmup_iterations=$(WARMUP_ITERS) \
	enable_alt2=$(ALT2) enable_random=$(RANDOM) \
	random_sweep=$(RANDOM_SWEEP) random_targets=$(RANDOM_TARGETS) \
	pattern_len=$(PATTERN_LEN) seed=$(SEED) \
	cpu=$(CPU)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

load: all
	$(SUDO) insmod $(MOD).ko $(PARAMS)

unload:
	$(SUDO) rmmod $(MOD)

reload: unload load

log:
	$(SUDO) dmesg | tail -n 50

bench:
	@set -e; \
	if lsmod | awk '{print $$1}' | grep -q "^$(MOD)$$"; then \
		echo "[bench] $(MOD) loaded: unloading first"; \
		$(SUDO) rmmod $(MOD); \
	else \
		echo "[bench] $(MOD) not loaded: skip unload"; \
	fi; \
	$(SUDO) dmesg -C; \
	$(SUDO) insmod $(MOD).ko $(PARAMS); \
	$(SUDO) dmesg | tail -n 50
