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
static_assert(offsetof(struct vkso_shared_data, realtime_coarse) == 8);
static_assert(offsetof(struct vkso_shared_data, monotonic_coarse) == 24);
static_assert(offsetof(struct vkso_mm_data, monotonic_offset) == 8);
static_assert(sizeof(union vkso_shared_page) == VKSO_SHARED_PAGE_SIZE);
static_assert(sizeof(union vkso_mm_page) == VKSO_SHARED_PAGE_SIZE);

__visible noinline notrace __vkso_text
int __vkso_clock_gettime(const struct vkso_mm_data *mm_data, int clock_id,
			 struct vkso_time_value *value)
{
	const struct vkso_shared_data *shared = &vkso_shared_page.data;
	u32 seq, abi_version;
	s64 offset_sec = 0;
	u64 offset_nsec = 0;
	s64 sec;
	u64 nsec;
	bool monotonic;

	if (!value)
		return VKSO_TIME_FALLBACK;
	switch (clock_id) {
	case CLOCK_REALTIME_COARSE:
		monotonic = false;
		break;
	case CLOCK_MONOTONIC_COARSE:
		if (!mm_data ||
		    READ_ONCE(mm_data->abi_version) !=
			    VKSO_MM_DATA_ABI_VERSION)
			return VKSO_TIME_FALLBACK;
		offset_sec = READ_ONCE(mm_data->monotonic_offset.sec);
		offset_nsec = READ_ONCE(mm_data->monotonic_offset.nsec);
		if (offset_nsec >= NSEC_PER_SEC)
			return VKSO_TIME_FALLBACK;
		monotonic = true;
		break;
	default:
		return VKSO_TIME_FALLBACK;
	}
	do {
		seq = READ_ONCE(shared->seq);
		if (seq & 1)
			continue;
		smp_rmb();
		abi_version = READ_ONCE(shared->abi_version);
		if (monotonic) {
			sec = READ_ONCE(shared->monotonic_coarse.sec);
			nsec = READ_ONCE(shared->monotonic_coarse.nsec);
		} else {
			sec = READ_ONCE(shared->realtime_coarse.sec);
			nsec = READ_ONCE(shared->realtime_coarse.nsec);
		}
		smp_rmb();
	} while ((seq & 1) || seq != READ_ONCE(shared->seq));

	if (abi_version != VKSO_TIME_ABI_VERSION || nsec >= NSEC_PER_SEC)
		return VKSO_TIME_FALLBACK;
	nsec += offset_nsec;
	sec += offset_sec;
	if (nsec >= NSEC_PER_SEC) {
		nsec -= NSEC_PER_SEC;
		sec++;
	}

	value->sec = sec;
	value->nsec = nsec;
	return VKSO_TIME_OK;
}
