CC ?= gcc

ROOT_DIR := /home/zzk/BinaryKernelCodeMapping
UPSTREAM_SRC_DIR := $(ROOT_DIR)/test/test_zlib/pigz_macro/zlib-1.2.11
PIGZ_DIR := $(ROOT_DIR)/test/test_zlib/pigz_macro/pigz-2.8
COMMON_FLAGS_MK := $(CURDIR)/../common_zlib_build_flags.mk

include $(COMMON_FLAGS_MK)

TARGET_LIB := libzlib_upstream_user_trim.so
TARGET_PIGZ := $(PIGZ_DIR)/pigz_upstream_user_trim
EXPORT_MAP := $(CURDIR)/exports.map

CPPFLAGS += -I$(UPSTREAM_SRC_DIR)
CPPFLAGS += -D_LARGEFILE64_SOURCE=1 -DHAVE_HIDDEN
CFLAGS += -std=gnu11 -fPIC -Wall -Wextra
CFLAGS += $(ZLIB_BENCH_COMMON_CFLAGS)
LDFLAGS += -shared -Wl,-soname,$(TARGET_LIB) -Wl,--version-script,$(EXPORT_MAP)
LDLIBS += -lm

# Minimal upstream zlib closure needed by pigz:
# - deflate-side compression entry points
# - checksum helpers
# - inflateBack* decompression path used by pigz
LIB_SRCS := \
	$(UPSTREAM_SRC_DIR)/deflate.c \
	$(UPSTREAM_SRC_DIR)/trees.c \
	$(UPSTREAM_SRC_DIR)/crc32.c \
	$(UPSTREAM_SRC_DIR)/adler32.c \
	$(UPSTREAM_SRC_DIR)/zutil.c \
	$(UPSTREAM_SRC_DIR)/inffast.c \
	$(UPSTREAM_SRC_DIR)/inftrees.c \
	$(UPSTREAM_SRC_DIR)/infback.c

LIB_OBJS := $(patsubst %.c,%.o,$(notdir $(LIB_SRCS)))

PIGZ_ZOP_OBJS := \
	$(PIGZ_DIR)/deflate.o \
	$(PIGZ_DIR)/blocksplitter.o \
	$(PIGZ_DIR)/tree.o \
	$(PIGZ_DIR)/lz77.o \
	$(PIGZ_DIR)/cache.o \
	$(PIGZ_DIR)/hash.o \
	$(PIGZ_DIR)/util.o \
	$(PIGZ_DIR)/squeeze.o \
	$(PIGZ_DIR)/katajainen.o \
	$(PIGZ_DIR)/symbols.o

.PHONY: all clean pigz-upstream-user-trim

all: $(TARGET_LIB)

$(TARGET_LIB): $(LIB_OBJS) Makefile $(COMMON_FLAGS_MK) $(EXPORT_MAP)
	$(CC) $(LDFLAGS) -o $@ $(LIB_OBJS) $(LDLIBS)

$(LIB_OBJS): Makefile $(COMMON_FLAGS_MK)

%.o: $(UPSTREAM_SRC_DIR)/%.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

pigz-upstream-user-trim: $(TARGET_LIB)
	$(MAKE) -C $(PIGZ_DIR) pigz
	$(CC) -o $(TARGET_PIGZ) \
		$(PIGZ_DIR)/pigz.o \
		$(PIGZ_DIR)/yarn.o \
		$(PIGZ_DIR)/try.o \
		$(PIGZ_ZOP_OBJS) \
		-Wl,-rpath,$(CURDIR) \
		$(CURDIR)/$(TARGET_LIB) \
		-lm -lpthread

clean:
	rm -f $(LIB_OBJS) $(TARGET_LIB) $(TARGET_PIGZ)
