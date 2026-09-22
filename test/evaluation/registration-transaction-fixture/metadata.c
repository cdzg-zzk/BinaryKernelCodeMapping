// SPDX-License-Identifier: GPL-2.0
/* Synthetic source pages for transport-boundary and rollback tests only. */
#include <linux/module.h>
#include "owner.h"
VKSO_DECLARE_OWNER(vkso_fixture_owner);
static int __init fixture_init(void) { return vkso_initialize_owner(&vkso_fixture_owner); }
static void __exit fixture_exit(void) { }
module_init(fixture_init);
module_exit(fixture_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("300 inert resident pages for VKSO transaction validation");
