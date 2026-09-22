/* SPDX-License-Identifier: GPL-2.0-only */
/* Optional guest syntax check against the actual generated vkso_types.h:
 * gcc -std=gnu11 -fsyntax-only -DAR_CHECK_XXH32 \
 *   -DAR_GENERATED_HEADER='"/absolute/generated/vkso_types.h"' types_check.c
 * Use AR_CHECK_SORT for the separate sort workspace. */
#include "protocol.h"
#ifndef AR_GENERATED_HEADER
#error "Pass the actual generated public header path as AR_GENERATED_HEADER"
#endif
#include AR_GENERATED_HEADER
#ifdef AR_CHECK_XXH32
_Static_assert(__builtin_types_compatible_p(__typeof__(&xxh32), ar_hash_fn), "xxh32 generated signature differs");
#endif
#ifdef AR_CHECK_SORT
_Static_assert(__builtin_types_compatible_p(__typeof__(&sort), ar_sort_fn), "sort generated signature differs");
#endif
