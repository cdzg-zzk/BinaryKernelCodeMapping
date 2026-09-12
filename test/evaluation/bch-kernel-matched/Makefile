obj-m += bch_matched.o
bch_matched-y := bch_impl.o module_meta.o

# Match the actual export owner's algorithm flags. Only API/module names differ.
BCH_EXPORT_RENAMES := \
	-Dbch_init=matched_bch_init \
	-Dbch_free=matched_bch_free \
	-Dbch_encode=matched_bch_encode \
	-Dbch_decode=matched_bch_decode

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
