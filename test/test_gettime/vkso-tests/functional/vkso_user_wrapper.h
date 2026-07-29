/* SPDX-License-Identifier: GPL-2.0 */
#ifndef VKSO_USER_WRAPPER_H
#define VKSO_USER_WRAPPER_H

/* Bind auxv-provided per-MM state to libkernel.so once per process image. */
int vkso_user_wrapper_init(void);

#endif /* VKSO_USER_WRAPPER_H */
