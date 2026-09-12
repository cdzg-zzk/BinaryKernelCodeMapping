#ifndef VKSO_BCH_KERNEL_COMPAT_H
#define VKSO_BCH_KERNEL_COMPAT_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef uint8_t u8;
typedef uint32_t u32;

/* Linux 5.15 bch.c uses WARN_ON only as a defensive size guard. */
#define WARN_ON(condition) (!!(condition))

#endif
