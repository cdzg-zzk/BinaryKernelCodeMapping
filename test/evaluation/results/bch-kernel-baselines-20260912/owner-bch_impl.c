/*
 * Build the running kernel's BCH implementation as an owner LKM while
 * namespacing its public API so it can coexist with lib/bch.ko.
 *
 * The included file is the minimally adapted Linux 5.15 lib/bch.c. Keeping
 * the namespacing here makes the boundary explicit, while both this LKM and
 * the native user-space comparison compile the same adapted source file.
 */
#define bch_init vkso_bch_init
#define bch_free vkso_bch_free
#define bch_encode vkso_bch_encode
#define bch_decode vkso_bch_decode

#include "../adapted/bch.c"
