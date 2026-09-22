// SPDX-License-Identifier: GPL-2.0
#include <stdio.h>
#include "vkso_time.h"

/* Launch only after the package's manager has registered this carrier. */
int main(void)
{
	struct timespec now;
	if (vkso_time_init() || vkso_time_clock_gettime(CLOCK_MONOTONIC, &now)) {
		perror("VKSO time");
		return 1;
	}
	printf("%lld.%09ld\n", (long long)now.tv_sec, now.tv_nsec);
	return 0;
}
