CC ?= gcc

ROOT_DIR := /home/zzk/BinaryKernelCodeMapping
PIGZ_DIR := $(ROOT_DIR)/test/test_zlib/pigz_macro/pigz-2.8
SRC_DIR := $(CURDIR)
COMMON_FLAGS_MK := $(CURDIR)/../common_zlib_build_flags.mk

include $(COMMON_FLAGS_MK)

TARGET_LIB := libzlib_user.so
TARGET_PIGZ := $(PIGZ_DIR)/pigz_user

CPPFLAGS += -I$(SRC_DIR)
CPPFLAGS += -D__used=__attribute__\(\(used\)\)
CPPFLAGS += -DHAVE_HIDDEN
CFLAGS += -std=gnu11 -fPIC -Wall -Wextra
CFLAGS += $(ZLIB_BENCH_COMMON_CFLAGS)
LDFLAGS += -shared -Wl,-soname,$(TARGET_LIB)
LDLIBS += -lm

LIB_SRCS := \
	deflate.c \
	trees.c \
	crc32.c \
	adler32.c \
	zutil.c

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

.PHONY: all clean pigz-user

all: $(TARGET_LIB)

$(TARGET_LIB): $(LIB_OBJS) Makefile $(COMMON_FLAGS_MK)
	$(CC) $(LDFLAGS) -o $@ $(LIB_OBJS) $(LDLIBS)

$(LIB_OBJS): Makefile $(COMMON_FLAGS_MK)

deflate.o: deflate.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

trees.o: trees.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

crc32.o: crc32.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

adler32.o: adler32.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

zutil.o: zutil.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

pigz-user: $(TARGET_LIB)
	$(MAKE) -C $(PIGZ_DIR) pigz
	$(CC) -o $(TARGET_PIGZ) \
		$(PIGZ_DIR)/pigz.o \
		$(PIGZ_DIR)/yarn.o \
		$(PIGZ_DIR)/try.o \
		$(PIGZ_ZOP_OBJS) \
		-Wl,-rpath,$(CURDIR) \
		$(CURDIR)/$(TARGET_LIB) \
		-lz -lm -lpthread

clean:
	rm -f $(LIB_OBJS) zutil_user.o $(TARGET_LIB) $(TARGET_PIGZ)
