// SPDX-License-Identifier: GPL-2.0
#include <errno.h>
#include <pthread.h>
#include <sys/auxv.h>
#include "vkso_time.h"
#include "vkso_user_wrapper.h"

static pthread_once_t init_once = PTHREAD_ONCE_INIT;
static int init_error;

static void initialize(void)
{
	/* Reject a non-VKSO boot before executing any carrier code. This is not
	 * proof of registration: the external manager must establish backing.
	 */
	errno = 0;
	if (!getauxval(AT_VKSO_MM_DATA) || errno) {
		init_error = ENOSYS;
		return;
	}
	if (vkso_user_wrapper_init() != 0)
		init_error = errno ? errno : EPROTO;
}

int vkso_time_init(void)
{
	int saved_errno = errno;
	int result = pthread_once(&init_once, initialize);

	if (result || init_error) {
		errno = result ? result : init_error;
		return -1;
	}
	errno = saved_errno;
	return 0;
}
