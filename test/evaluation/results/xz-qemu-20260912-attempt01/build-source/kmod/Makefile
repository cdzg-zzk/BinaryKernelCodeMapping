obj-m += vkso_xz.o
vkso_xz-y := module_meta.o xz_dec_stream.o xz_dec_lzma2.o xz_dec_bcj.o xz_crc32.o

XZ_RENAMES := \
	-Dxz_dec_init=vkso_xz_dec_init \
	-Dxz_dec_run=vkso_xz_dec_run \
	-Dxz_dec_reset=vkso_xz_dec_reset \
	-Dxz_dec_end=vkso_xz_dec_end \
	-Dxz_dec_lzma2_create=vkso_xz_dec_lzma2_create \
	-Dxz_dec_lzma2_reset=vkso_xz_dec_lzma2_reset \
	-Dxz_dec_lzma2_run=vkso_xz_dec_lzma2_run \
	-Dxz_dec_lzma2_end=vkso_xz_dec_lzma2_end \
	-Dxz_dec_bcj_create=vkso_xz_dec_bcj_create \
	-Dxz_dec_bcj_reset=vkso_xz_dec_bcj_reset \
	-Dxz_dec_bcj_run=vkso_xz_dec_bcj_run \
	-Dxz_crc32_init=vkso_xz_crc32_init \
	-Dxz_crc32=vkso_xz_crc32

# XZ Embedded has a documented single-call configuration. The benchmark keeps
# the x86 BCJ filter and the decoder's compact internal CRC32 implementation.
ccflags-y += $(XZ_RENAMES) -DXZ_DEC_SINGLE -DXZ_INTERNAL_CRC32=1 \
	-fno-stack-protector -fno-sanitize=all -fno-jump-tables \
	-mno-sse -mno-sse2 -mno-mmx -mno-avx -mno-red-zone \
	-mfunction-return=keep -mindirect-branch=keep

XZ_OBJECTS := xz_dec_stream.o xz_dec_lzma2.o xz_dec_bcj.o xz_crc32.o
$(foreach obj,$(XZ_OBJECTS),$(eval CFLAGS_REMOVE_$(obj) += \
	-pg -mrecord-mcount -mfentry -fstack-protector-strong \
	-fsanitize=bounds -fsanitize=shift))
$(foreach obj,$(XZ_OBJECTS),$(eval CFLAGS_$(obj) += -fno-sanitize=all))
$(foreach obj,$(XZ_OBJECTS),$(eval UBSAN_SANITIZE_$(obj) := n))
