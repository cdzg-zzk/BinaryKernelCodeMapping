CC ?= gcc
BUILD_DIR ?= build

WARNINGS := -std=gnu11 -Wall -Wextra
KERNEL_NATIVE_FLAGS := -O2 -g -fPIC -fno-stack-protector \
	-fno-tree-vectorize -fno-tree-slp-vectorize \
	-mno-sse -mno-sse2 -mno-mmx -mno-avx -mno-red-zone \
	-mfunction-return=keep -mindirect-branch=keep
AUTHOR_FLAGS := -O3 -g -fPIC -mtune=native
KERNEL_COMPAT := -include userspace/kernel_compat.h \
	-Ivendor/linux-5.15/include -Ivendor/parrot-bch/standalone
AUTHOR_COMPAT := -Ivendor/parrot-bch/standalone \
	-Ivendor/parrot-bch/include

.PHONY: all clean

all: $(BUILD_DIR)/bch-bench \
	$(BUILD_DIR)/libbch-kernel-native.so \
	$(BUILD_DIR)/libbch-author-standalone.so

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/bch-bench: src/bch_bench.c | $(BUILD_DIR)
	$(CC) -O2 -g $(WARNINGS) $< -ldl -o $@

$(BUILD_DIR)/libbch-kernel-native.so: adapted/bch.c \
	vendor/linux-5.15/include/linux/bch.h userspace/kernel_compat.h \
	userspace/kernel-native.map | $(BUILD_DIR)
	$(CC) $(KERNEL_NATIVE_FLAGS) $(WARNINGS) $(KERNEL_COMPAT) -shared \
		adapted/bch.c -Wl,-Bsymbolic-functions \
		-Wl,--version-script=userspace/kernel-native.map \
		-Wl,-soname,libbch-kernel-native.so -o $@

$(BUILD_DIR)/libbch-author-standalone.so: \
	vendor/parrot-bch/lib/bch.c vendor/parrot-bch/include/linux/bch.h \
	userspace/standalone.map | $(BUILD_DIR)
	$(CC) $(AUTHOR_FLAGS) $(WARNINGS) $(AUTHOR_COMPAT) -shared \
		vendor/parrot-bch/lib/bch.c -Wl,-Bsymbolic-functions \
		-Wl,--version-script=userspace/standalone.map \
		-Wl,-soname,libbch-author-standalone.so -o $@

clean:
	rm -rf $(BUILD_DIR)
