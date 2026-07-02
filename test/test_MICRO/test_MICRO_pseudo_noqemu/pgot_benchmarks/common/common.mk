CC ?= gcc
COMMON_DIR ?= ../../common

CFLAGS_COMMON := -O2 -std=gnu11 -Wall -Wextra -Wshadow -fno-omit-frame-pointer \
	-fno-tree-vectorize -fno-unroll-loops -I$(COMMON_DIR)

LDFLAGS_COMMON :=

RETPOLINE_CFLAGS := -DRETPOLINE_BUILD -mindirect-branch=thunk-inline \
	-mindirect-branch-register -fcf-protection=none
