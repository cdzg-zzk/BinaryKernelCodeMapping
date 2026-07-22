/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_VKSO_TIME_H
#define _LINUX_VKSO_TIME_H

#include <linux/compiler_types.h>
#include <vkso/time.h>

#define VKSO_TEXT_SECTION		".vkso.text"
#define VKSO_SHARED_DATA_SECTION	".vkso.shared_data"

#define __vkso_text		__section(VKSO_TEXT_SECTION)
#define __vkso_shared_data	__section(VKSO_SHARED_DATA_SECTION)

extern char __vkso_text_start[];
extern char __vkso_text_end[];
extern char __vkso_shared_data_start[];
extern char __vkso_shared_data_end[];

#endif /* _LINUX_VKSO_TIME_H */
