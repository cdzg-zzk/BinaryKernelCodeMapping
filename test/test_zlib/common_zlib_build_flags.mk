# Flags we intentionally keep aligned across the B/C/D zlib library builds.
# Kernel-specific or user-space-only environment flags stay in each Makefile.
ZLIB_BENCH_COMMON_CFLAGS := \
	-O2 \
	-fcf-protection=none \
	-fno-omit-frame-pointer \
	-fno-inline \
	-fno-optimize-sibling-calls \
	-fno-stack-protector \
	-fno-ipa-cp \
	-fno-ipa-sra \
	-fno-tree-ccp \
	-fno-strict-aliasing \
	-fno-strict-overflow
