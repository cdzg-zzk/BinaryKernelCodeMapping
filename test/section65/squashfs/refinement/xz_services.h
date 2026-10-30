/* Domain-private services for the unchanged Linux XZ decoder bodies. */
#ifndef VKSO_SQ_XZ_SERVICES_H
#define VKSO_SQ_XZ_SERVICES_H
#include "sq_xz_api.h"
struct sq_xz_services {
    void *(*alloc)(size_t);
    void *(*valloc)(size_t);
    void (*free)(const void *);
    void (*vfree)(const void *);
    void *(*copy)(void *, const void *, size_t);
    void *(*move)(void *, const void *, size_t);
    void *(*set)(void *, int, size_t);
    int (*compare)(const void *, const void *, size_t);
    uint32_t (*crc32)(const uint8_t *, size_t, uint32_t);
};
extern struct sq_xz_services sq_xz_services;
void sq_bind_xz(const struct sq_xz_services *);
void *sq_xz_support_address(void);
#endif
