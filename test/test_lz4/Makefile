CC ?= gcc
BUILD_DIR ?= build
VENDOR_DIR := vendor/lz4-1.9.3/lib
VENDOR_PROGRAMS_DIR := vendor/lz4-1.9.3/programs
KERNEL_SRC_DIR := kmod
KERNEL_USER_DIR := userspace_kernel

COMMON_WARNINGS := -std=gnu11 -Wall -Wextra -Wpedantic
OFFICIAL_WARNINGS := -std=gnu11 -Wall -Wextra
DEFAULT_LZ4_FLAGS := -O3 -g -fPIC -march=native
NOSIMD_LZ4_FLAGS := -O3 -g -fPIC -fno-tree-vectorize -fno-tree-slp-vectorize \
	-fno-tree-loop-vectorize -fno-tree-loop-distribute-patterns -fno-builtin \
	-mno-mmx -mno-3dnow -mno-sse -mno-sse2 -mno-sse3 -mno-ssse3 \
	-mno-sse4 -mno-sse4.1 -mno-sse4.2 -mno-avx -mno-avx2 \
	-mno-avx512f -mno-avx512bw -mno-avx512dq -mno-avx512vl
KERNEL_USER_COMMON_FLAGS := -DVKSO_LZ4_USERSPACE -ffunction-sections \
	-fdata-sections
KERNEL_LZ4_RENAMES := \
	-DLZ4_compress_fast=vkso_LZ4_compress_fast \
	-DLZ4_compress_default=vkso_LZ4_compress_default \
	-DLZ4_compress_destSize=vkso_LZ4_compress_destSize \
	-DLZ4_resetStream=vkso_LZ4_resetStream \
	-DLZ4_loadDict=vkso_LZ4_loadDict \
	-DLZ4_saveDict=vkso_LZ4_saveDict \
	-DLZ4_compress_fast_continue=vkso_LZ4_compress_fast_continue \
	-DLZ4_decompress_safe=vkso_LZ4_decompress_safe \
	-DLZ4_decompress_safe_partial=vkso_LZ4_decompress_safe_partial \
	-DLZ4_decompress_fast=vkso_LZ4_decompress_fast \
	-DLZ4_decompress_safe_forceExtDict=vkso_LZ4_decompress_safe_forceExtDict \
	-DLZ4_decompress_safe_doubleDict=vkso_LZ4_decompress_safe_doubleDict \
	-DLZ4_decompress_fast_doubleDict=vkso_LZ4_decompress_fast_doubleDict \
	-DLZ4_setStreamDecode=vkso_LZ4_setStreamDecode \
	-DLZ4_decompress_safe_continue=vkso_LZ4_decompress_safe_continue \
	-DLZ4_decompress_fast_continue=vkso_LZ4_decompress_fast_continue \
	-DLZ4_decompress_safe_usingDict=vkso_LZ4_decompress_safe_usingDict \
	-DLZ4_decompress_fast_usingDict=vkso_LZ4_decompress_fast_usingDict
KERNEL_USER_SOURCES := $(KERNEL_SRC_DIR)/lz4_compress.c \
	$(KERNEL_SRC_DIR)/lz4_decompress.c
KERNEL_USER_LINK_FLAGS := -Wl,--gc-sections -Wl,-Bsymbolic-functions \
	-Wl,--version-script=$(KERNEL_USER_DIR)/exports.map

.PHONY: all clean audit-simd

all: $(BUILD_DIR)/lz4-bench $(BUILD_DIR)/official-lz4-bench \
	$(BUILD_DIR)/liblz4-default.so \
	$(BUILD_DIR)/liblz4-nosimd.so \
	$(BUILD_DIR)/libkernel-userspace-native.so \
	$(BUILD_DIR)/libkernel-userspace-nosimd.so \
	$(BUILD_DIR)/libkernel-userspace-libc.so

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/lz4-bench: src/lz4-bench.c | $(BUILD_DIR)
	$(CC) -O2 -g $(COMMON_WARNINGS) $< -ldl -o $@

$(BUILD_DIR)/official-lz4-bench: src/official_bench_driver.c \
	src/official_backend_adapter.c $(VENDOR_PROGRAMS_DIR)/bench.c \
	$(VENDOR_PROGRAMS_DIR)/bench.h $(VENDOR_PROGRAMS_DIR)/datagen.c \
	$(VENDOR_PROGRAMS_DIR)/datagen.h $(VENDOR_PROGRAMS_DIR)/platform.h \
	$(VENDOR_PROGRAMS_DIR)/util.h $(VENDOR_DIR)/lz4.c $(VENDOR_DIR)/lz4.h \
	$(VENDOR_DIR)/lz4hc.c $(VENDOR_DIR)/lz4hc.h \
	$(VENDOR_DIR)/xxhash.c $(VENDOR_DIR)/xxhash.h | $(BUILD_DIR)
	$(CC) -O2 -g $(OFFICIAL_WARNINGS) \
		-Isrc -I$(VENDOR_PROGRAMS_DIR) -I$(VENDOR_DIR) \
		src/official_bench_driver.c src/official_backend_adapter.c \
		$(VENDOR_PROGRAMS_DIR)/bench.c $(VENDOR_PROGRAMS_DIR)/datagen.c \
		$(VENDOR_DIR)/lz4.c $(VENDOR_DIR)/lz4hc.c $(VENDOR_DIR)/xxhash.c \
		-Wl,--wrap=LZ4_compress_fast \
		-Wl,--wrap=LZ4_decompress_safe_usingDict -ldl -lm -o $@

$(BUILD_DIR)/liblz4-default.so: $(VENDOR_DIR)/lz4.c $(VENDOR_DIR)/lz4.h | $(BUILD_DIR)
	$(CC) $(DEFAULT_LZ4_FLAGS) $(COMMON_WARNINGS) -shared $< \
		-Wl,-soname,liblz4-vkso-default.so -o $@

$(BUILD_DIR)/liblz4-nosimd.so: $(VENDOR_DIR)/lz4.c $(VENDOR_DIR)/lz4.h \
	$(KERNEL_USER_DIR)/scalar_mem.c | $(BUILD_DIR)
	$(CC) $(NOSIMD_LZ4_FLAGS) $(COMMON_WARNINGS) -shared \
		$(VENDOR_DIR)/lz4.c $(KERNEL_USER_DIR)/scalar_mem.c \
		-Wl,-Bsymbolic-functions \
		-Wl,-soname,liblz4-vkso-nosimd.so -o $@

$(BUILD_DIR)/libkernel-userspace-native.so: $(KERNEL_USER_SOURCES) \
	$(KERNEL_SRC_DIR)/lz4defs.h $(KERNEL_USER_DIR)/kernel_compat.h \
	$(KERNEL_USER_DIR)/exports.map | $(BUILD_DIR)
	$(CC) $(DEFAULT_LZ4_FLAGS) $(KERNEL_USER_COMMON_FLAGS) \
		$(KERNEL_LZ4_RENAMES) $(COMMON_WARNINGS) -shared \
		$(KERNEL_USER_SOURCES) $(KERNEL_USER_LINK_FLAGS) \
		-Wl,-soname,libkernel-userspace-native.so -o $@

$(BUILD_DIR)/libkernel-userspace-nosimd.so: $(KERNEL_USER_SOURCES) \
	$(KERNEL_SRC_DIR)/lz4defs.h $(KERNEL_USER_DIR)/kernel_compat.h \
	$(KERNEL_USER_DIR)/scalar_mem.c $(KERNEL_USER_DIR)/exports.map | $(BUILD_DIR)
	$(CC) $(NOSIMD_LZ4_FLAGS) $(KERNEL_USER_COMMON_FLAGS) \
		$(KERNEL_LZ4_RENAMES) $(COMMON_WARNINGS) -shared \
		$(KERNEL_USER_SOURCES) $(KERNEL_USER_DIR)/scalar_mem.c \
		$(KERNEL_USER_LINK_FLAGS) \
		-Wl,-soname,libkernel-userspace-nosimd.so -o $@

# Identical algorithm flags to the REP/no-SIMD DSO, but resolve ordinary
# memory calls through libc, as the registered carrier's ABI bridges do.
$(BUILD_DIR)/libkernel-userspace-libc.so: $(KERNEL_USER_SOURCES) \
	$(KERNEL_SRC_DIR)/lz4defs.h $(KERNEL_USER_DIR)/kernel_compat.h \
	$(KERNEL_USER_DIR)/exports.map | $(BUILD_DIR)
	$(CC) $(NOSIMD_LZ4_FLAGS) $(KERNEL_USER_COMMON_FLAGS) \
		$(KERNEL_LZ4_RENAMES) $(COMMON_WARNINGS) -shared \
		$(KERNEL_USER_SOURCES) $(KERNEL_USER_LINK_FLAGS) \
		-Wl,-soname,libkernel-userspace-libc.so -o $@

audit-simd: all
	python3 scripts/audit_simd.py \
		--default $(BUILD_DIR)/liblz4-default.so \
		--nosimd $(BUILD_DIR)/liblz4-nosimd.so \
		--kernel-native $(BUILD_DIR)/libkernel-userspace-native.so \
		--kernel-nosimd $(BUILD_DIR)/libkernel-userspace-nosimd.so \
		--kernel-libc $(BUILD_DIR)/libkernel-userspace-libc.so

clean:
	rm -rf $(BUILD_DIR)
