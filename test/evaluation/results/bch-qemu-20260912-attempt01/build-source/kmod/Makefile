obj-m += vkso_bch.o
vkso_bch-y := bch_impl.o module_meta.o

BCH_EXPORT_RENAMES := \
	-Dbch_init=vkso_bch_init \
	-Dbch_free=vkso_bch_free \
	-Dbch_encode=vkso_bch_encode \
	-Dbch_decode=vkso_bch_decode

# The owner module is compiled as reusable user-mode machine code.  Remove
# kernel-only compiler instrumentation from the algorithm object and keep the
# code scalar.  BCH itself contains no SIMD implementation.
ccflags-y += $(BCH_EXPORT_RENAMES) \
	-D__NO_FORTIFY -fno-stack-protector -fno-sanitize=all -fno-jump-tables \
	-mno-sse -mno-sse2 -mno-mmx -mno-avx -mno-red-zone \
	-mfunction-return=keep -mindirect-branch=keep

CFLAGS_REMOVE_bch_impl.o += \
	-pg -mrecord-mcount -mfentry -fstack-protector-strong \
	-fsanitize=bounds -fsanitize=shift
CFLAGS_bch_impl.o += -fno-sanitize=all
UBSAN_SANITIZE_bch_impl.o := n
CFLAGS_REMOVE_module_meta.o += -pg -mrecord-mcount -mfentry
