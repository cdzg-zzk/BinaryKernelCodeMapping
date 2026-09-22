/* Cooperative owner descriptor. This entire management page is excluded from
 * the user carrier, including its private data image and dynamic relocations.
 */
#ifndef VKSO_OWNER_H
#define VKSO_OWNER_H
#include <linux/module.h>
#include <linux/string.h>
#include <linux/mm.h>
#define VKSO_OWNER_MAGIC 0x564b534f4f574e52ULL
#define VKSO_OWNER_ABI 1
struct vkso_owner_descriptor {
    u64 magic;
    u32 abi;
    u32 reserved;
    struct module *owner;
    unsigned long text_start, text_end;
    unsigned long ro_start, ro_end;
    char srcversion[25];
} __aligned(PAGE_SIZE);

#define VKSO_DECLARE_OWNER(symbol) \
    struct vkso_owner_descriptor symbol __section(".vkso_owner") = { \
        .magic = VKSO_OWNER_MAGIC, .abi = VKSO_OWNER_ABI, .owner = THIS_MODULE, \
    }; \
    EXPORT_SYMBOL_GPL(symbol)

static inline int vkso_initialize_owner(struct vkso_owner_descriptor *d)
{
    struct module *m = THIS_MODULE;
    unsigned long base = (unsigned long)m->core_layout.base;
    BUILD_BUG_ON(sizeof(*d) != PAGE_SIZE);
    if (!m->srcversion || !m->srcversion[0] ||
        strlen(m->srcversion) >= sizeof(d->srcversion) ||
        !IS_ALIGNED(base, PAGE_SIZE) ||
        !IS_ALIGNED(m->core_layout.text_size, PAGE_SIZE) ||
        !IS_ALIGNED(m->core_layout.ro_size, PAGE_SIZE))
        return -EINVAL;
    d->text_start = base;
    d->text_end = base + m->core_layout.text_size;
    d->ro_start = d->text_end;
    d->ro_end = base + m->core_layout.ro_size;
    strscpy(d->srcversion, m->srcversion, sizeof(d->srcversion));
    return 0;
}
#endif
