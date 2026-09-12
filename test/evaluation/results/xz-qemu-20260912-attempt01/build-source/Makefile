CC ?= gcc
BUILD_DIR ?= build

COMMON_FLAGS := -O2 -g -std=gnu11 -Wall -Wextra
XZ_SOURCES := kmod/xz_dec_stream.c kmod/xz_dec_lzma2.c \
	kmod/xz_dec_bcj.c kmod/xz_crc32.c
XZ_HEADERS := kmod/xz.h kmod/xz_private.h kmod/xz_lzma2.h \
	kmod/xz_stream.h userspace/xz_config.h

.PHONY: all clean

all: $(BUILD_DIR)/xz-bench $(BUILD_DIR)/libxz-native.so

$(BUILD_DIR):
	mkdir -p $@

$(BUILD_DIR)/xz-bench: src/xz-bench.c kmod/xz.h | $(BUILD_DIR)
	$(CC) $(COMMON_FLAGS) -Ikmod $< -ldl -o $@

$(BUILD_DIR)/libxz-native.so: $(XZ_SOURCES) $(XZ_HEADERS) \
		userspace/exports.map | $(BUILD_DIR)
	$(CC) $(COMMON_FLAGS) -fPIC -shared -Iuserspace -Ikmod \
		$(XZ_SOURCES) -Wl,--version-script=userspace/exports.map \
		-Wl,-soname,libxz-native.so -o $@

clean:
	rm -rf $(BUILD_DIR)
