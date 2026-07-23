// SPDX-License-Identifier: GPL-2.0

#include <linux/build_bug.h>
#include <linux/compiler.h>
#include <linux/stddef.h>
#include <linux/time.h>
#include <linux/vkso_time.h>

/* Keep the binary contract explicit before executable interfaces are added. */
static_assert(sizeof(struct vkso_time_value) == 16);
static_assert(offsetof(struct vkso_time_value, sec) == 0);
static_assert(offsetof(struct vkso_time_value, nsec) == 8);
static_assert(sizeof(union vkso_shared_page) == VKSO_SHARED_PAGE_SIZE);

__visible noinline notrace __vkso_text
int __vkso_clock_gettime(int clock_id, struct vkso_time_value *value)
{
	const struct vkso_shared_data *shared = &vkso_shared_page.data;
	u32 seq, abi_version;
	s64 sec;
	u64 nsec;

	if (clock_id != CLOCK_REALTIME_COARSE || !value)
		return VKSO_TIME_FALLBACK;

	do {
		seq = READ_ONCE(shared->seq);
		if (seq & 1)
			continue;
		smp_rmb();
		abi_version = READ_ONCE(shared->abi_version);
		sec = READ_ONCE(shared->realtime_coarse.sec);
		nsec = READ_ONCE(shared->realtime_coarse.nsec);
		smp_rmb();
	} while (seq != READ_ONCE(shared->seq));

	if (abi_version != VKSO_TIME_ABI_VERSION || nsec >= NSEC_PER_SEC)
		return VKSO_TIME_FALLBACK;

	value->sec = sec;
	value->nsec = nsec;
	return VKSO_TIME_OK;
}
