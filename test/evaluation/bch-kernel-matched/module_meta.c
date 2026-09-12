#include <linux/init.h>
#include <linux/module.h>

static int __init bch_matched_init(void)
{
	return 0;
}

static void __exit bch_matched_exit(void)
{
}

module_init(bch_matched_init);
module_exit(bch_matched_exit);
/* The included original BCH source supplies its GPL license declaration. */
