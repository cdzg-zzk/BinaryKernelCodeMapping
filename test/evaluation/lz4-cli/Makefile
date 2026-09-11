CC ?= gcc
BUILD_DIR ?= build
SOURCE := vendor/lz4-1.9.3
CFLAGS := -O3 -g -Wall -Wextra
CPPFLAGS := -I$(SOURCE)/lib -DXXH_NAMESPACE=LZ4_
SOURCES := $(wildcard $(SOURCE)/lib/*.c) $(wildcard $(SOURCE)/programs/*.c)
WRAP := -Wl,--wrap=LZ4_compress_fast_extState_fastReset \
        -Wl,--wrap=LZ4_decompress_safe_usingDict \
        -Wl,--wrap=LZ4_decompress_safe

.PHONY: all
all: $(BUILD_DIR)/lz4-stock $(BUILD_DIR)/lz4-adapted

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/lz4-stock: $(SOURCES) | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(SOURCES) -o $@

$(BUILD_DIR)/lz4-adapted: $(SOURCES) backend_adapter.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(SOURCES) backend_adapter.c $(WRAP) -ldl -o $@
