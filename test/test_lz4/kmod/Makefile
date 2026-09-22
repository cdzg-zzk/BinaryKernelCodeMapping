obj-m += vkso_lz4.o
vkso_lz4-y := lz4_compress.o lz4_decompress.o module_meta.o

# Runtime module pages normally rely on ftrace patching the __fentry__ sites.
# The benchmark DSO does not map the ftrace trampoline, so omit those entry
# calls from the two algorithm objects at compile time.
CFLAGS_REMOVE_lz4_compress.o += -pg -mrecord-mcount -mfentry
CFLAGS_REMOVE_lz4_decompress.o += -pg -mrecord-mcount -mfentry

# Rename every externally visible LZ4 API so this benchmark module can coexist
# with the running kernel's built-in decompressor and packaged compressor.
ccflags-y += \
	-mfunction-return=keep \
	-mindirect-branch=keep \
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
