// SPDX-License-Identifier: GPL-2.0
/* Resident-page transactions for the controlled VKSO research kernel. */
#include <linux/module.h>
#include <linux/fs.h>
#include <linux/file.h>
#include <linux/pagemap.h>
#include <linux/netlink.h>
#include <net/sock.h>
#include <linux/slab.h>
#include <linux/vmalloc.h>
#include <linux/ktime.h>
#include <linux/mutex.h>
#include <linux/kdev_t.h>
#include <linux/cleancache.h>
#include <linux/memcontrol.h>
#include <linux/sched.h>
#include <asm/pgtable.h>
#include "protocol.h"
#include "owner.h"

static DEFINE_MUTEX(operation_lock);
static LIST_HEAD(transactions);
static struct sock *nl_sk, *nl_restore_sk;

/* One-shot fault injection, disabled in ordinary runs. Only the administrator
 * of the private evaluation guest writes these module parameters. */
static int test_fail_apply = -1, test_fail_release = -1;
static unsigned int test_drop_reply;
module_param(test_fail_apply, int, 0600);
module_param(test_fail_release, int, 0600);
module_param(test_drop_reply, uint, 0600);

struct owner_pin {
    char symbol[64];
    const struct vkso_owner_descriptor *descriptor;
};
struct binding {
    struct vkso_page_spec spec;
    struct page *source, *old_cache;
    void *saved_mapping;
    unsigned long saved_index;
    bool saved_uptodate, applied;
};
struct transaction {
    struct list_head list;
    u64 id;
    u32 controller_port, total, staged, applied, state;
    u32 last_operation, last_sequence;
    int last_status, failed_page;
    u64 prepare_ns, apply_ns, release_ns;
    struct file *file;
    struct binding *pages;
    struct owner_pin owners[VKSO_MAX_OWNERS];
    u32 owner_count;
    bool write_denied, mapping_denied, module_held;
};

static struct transaction *find_transaction(u64 id)
{
    struct transaction *t;
    list_for_each_entry(t, &transactions, list)
        if (t->id == id)
            return t;
    return NULL;
}

static void drop_resources(struct transaction *t)
{
    u32 i;
    if (t->applied)
        return;
    for (i = 0; i < t->total; i++) {
        if (t->pages[i].old_cache) {
            put_page(t->pages[i].old_cache);
            t->pages[i].old_cache = NULL;
        }
        if (t->pages[i].source) {
            put_page(t->pages[i].source);
            t->pages[i].source = NULL;
        }
    }
    kvfree(t->pages);
    t->pages = NULL;
    for (i = 0; i < t->owner_count; i++)
        __symbol_put(t->owners[i].symbol);
    t->owner_count = 0;
    if (t->file) {
        if (t->mapping_denied)
            mapping_allow_writable(t->file->f_mapping);
        if (t->write_denied)
            allow_write_access(t->file);
        fput(t->file);
        t->file = NULL;
    }
    t->mapping_denied = t->write_denied = false;
    if (t->module_held) {
        t->module_held = false;
        module_put(THIS_MODULE);
    }
}

static int pin_owners(struct transaction *t, const struct vkso_tx_request *r)
{
    u32 i, j;
    for (i = 0; i < r->owner_count; i++) {
        const struct vkso_owner_request *o = &r->owners[i];
        const struct vkso_owner_descriptor *d;
        if (!memchr(o->symbol, 0, sizeof(o->symbol)) || !o->symbol[0] ||
            !memchr(o->srcversion, 0, sizeof(o->srcversion)) || !o->srcversion[0] ||
            memchr_inv(o->reserved, 0, sizeof(o->reserved)))
            return -EINVAL;
        for (j = 0; j < i; j++)
            if (!strcmp(o->symbol, r->owners[j].symbol))
                return -EEXIST;
        d = __symbol_get(o->symbol);
        if (!d)
            return -ENOENT;
        if (!IS_ALIGNED((unsigned long)d, PAGE_SIZE) || d->magic != VKSO_OWNER_MAGIC ||
            d->abi != VKSO_OWNER_ABI || !d->owner ||
            !within_module_core((unsigned long)d, d->owner) ||
            !within_module_core((unsigned long)d + PAGE_SIZE - 1, d->owner)) {
            __symbol_put(o->symbol);
            return -EINVAL;
        }
        strscpy(t->owners[i].symbol, o->symbol, sizeof(t->owners[i].symbol));
        t->owners[i].descriptor = d;
        t->owner_count++;
        if (!memchr(d->srcversion, 0, sizeof(d->srcversion)) ||
            strcmp(d->srcversion, o->srcversion) || !d->owner->srcversion ||
            strcmp(d->owner->srcversion, o->srcversion))
            return -ESTALE;
        if (d->text_start != (unsigned long)d->owner->core_layout.base ||
            d->text_end != d->text_start + d->owner->core_layout.text_size ||
            d->ro_start != d->text_end ||
            d->ro_end != d->text_start + d->owner->core_layout.ro_size)
            return -EINVAL;
    }
    return 0;
}

static bool source_allowed(struct transaction *t, const struct vkso_page_spec *spec)
{
    unsigned long address = spec->source;
    u32 i;
    if (!IS_ALIGNED(address, PAGE_SIZE) || address > ULONG_MAX - PAGE_SIZE)
        return false;
    for (i = 0; i < t->owner_count; i++) {
        const struct vkso_owner_descriptor *d = t->owners[i].descriptor;
        if (address >= d->text_start && address + PAGE_SIZE <= d->text_end)
            return spec->kind == VKSO_PAGE_TEXT;
        if (address >= d->ro_start && address + PAGE_SIZE <= d->ro_end)
            return spec->kind == VKSO_PAGE_RODATA;
    }
    return address >= __START_KERNEL_map && address + PAGE_SIZE <= MODULES_VADDR;
}
/* Effective permissions combine every level, including huge-page leaves.
 * Read the requesting task's active kernel page table, not ELF section flags.
 * Owner pins keep the resident module alive; this is admission-time checking,
 * not serialization against later privileged text/page-table rewriting. */
static bool accumulate_permissions(u64 entry, u64 *permissions)
{
    if (!(entry & _PAGE_PRESENT)) return false;
    *permissions &= entry | ~((u64)_PAGE_RW | _PAGE_USER);
    *permissions |= entry & _PAGE_NX;
    return true;
}

static struct page *lookup_kernel_page(unsigned long address, u64 *permissions)
{
    pgd_t *pgdp, pgd;
    p4d_t *p4dp, p4d;
    pud_t *pudp, pud;
    pmd_t *pmdp, pmd;
    pte_t pte;
    unsigned long pfn;
    if (!current->active_mm) return NULL;
    *permissions = _PAGE_RW | _PAGE_USER;
    pgdp = pgd_offset(current->active_mm, address); pgd = READ_ONCE(*pgdp);
    if (!accumulate_permissions(pgd_val(pgd), permissions)) return NULL;
    p4dp = p4d_offset(pgdp, address); p4d = READ_ONCE(*p4dp);
    if (!accumulate_permissions(p4d_val(p4d), permissions) || p4d_large(p4d)) return NULL;
    pudp = pud_offset(p4dp, address); pud = READ_ONCE(*pudp);
    if (!accumulate_permissions(pud_val(pud), permissions)) return NULL;
    if (pud_large(pud)) {
        pfn = pud_pfn(pud) + ((address & ~PUD_MASK) >> PAGE_SHIFT);
        goto resolved;
    }
    pmdp = pmd_offset(pudp, address); pmd = READ_ONCE(*pmdp);
    if (!accumulate_permissions(pmd_val(pmd), permissions)) return NULL;
    if (pmd_large(pmd)) {
        pfn = pmd_pfn(pmd) + ((address & ~PMD_MASK) >> PAGE_SHIFT);
        goto resolved;
    }
    pte = READ_ONCE(*pte_offset_kernel(pmdp, address));
    if (!accumulate_permissions(pte_val(pte), permissions)) return NULL;
    pfn = pte_pfn(pte);
resolved:
    return pfn_valid(pfn) ? pfn_to_page(pfn) : NULL;
}

static bool source_permissions_allowed(u32 kind, u64 permissions)
{
    bool writable = permissions & _PAGE_RW;
    bool executable = !(permissions & _PAGE_NX);
    if (permissions & _PAGE_USER) return false;
    switch (kind) {
    case VKSO_PAGE_TEXT: return !writable && executable;
    case VKSO_PAGE_RODATA: return !writable && !executable;
    case VKSO_PAGE_SHARED_DATA: return writable && !executable;
    default: return false;
    }
}


static int begin_transaction(const struct vkso_tx_request *r, u32 port,
                             struct transaction **out)
{
    struct transaction *t, *other;
    struct inode *inode;
    int ret;
    if (!r->transaction || !r->total || r->owner_count > VKSO_MAX_OWNERS ||
        r->start || r->count || !memchr(r->filepath, 0, sizeof(r->filepath)))
        return -EINVAL;
    t = kzalloc(sizeof(*t), GFP_KERNEL);
    if (!t)
        return -ENOMEM;
    t->pages = kvcalloc(r->total, sizeof(*t->pages), GFP_KERNEL);
    if (!t->pages) { kfree(t); return -ENOMEM; }
    t->total = r->total;
    t->id = r->transaction;
    t->controller_port = port;
    t->state = VKSO_STAGING;
    t->failed_page = -1;
    t->file = filp_open(r->filepath, O_RDONLY | O_NOFOLLOW, 0);
    if (IS_ERR(t->file)) { ret = PTR_ERR(t->file); t->file = NULL; goto fail; }
    inode = file_inode(t->file);
    if (!S_ISREG(inode->i_mode) || IS_DAX(inode)) { ret = -EOPNOTSUPP; goto fail; }
    if (huge_encode_dev(inode->i_sb->s_dev) != r->device || inode->i_ino != r->inode) {
        ret = -ESTALE; goto fail;
    }
    list_for_each_entry(other, &transactions, list)
        if (other->file && other->file->f_mapping == t->file->f_mapping) {
            ret = -EBUSY; goto fail;
        }
    if (!try_module_get(THIS_MODULE)) { ret = -ENODEV; goto fail; }
    t->module_held = true;
    ret = pin_owners(t, r);
    if (ret) goto fail;
    /* Atomic counters reject existing write fds and writable shared VMAs,
     * including read-only VMAs that retain VM_MAYWRITE from a write fd. */
    inode_lock(inode);
    ret = deny_write_access(t->file);
    if (!ret) {
        t->write_denied = true;
        ret = mapping_deny_writable(t->file->f_mapping);
        if (!ret) t->mapping_denied = true;
    }
    inode_unlock(inode);
    if (ret) goto fail;
    list_add_tail(&t->list, &transactions);
    *out = t;
    return 0;
fail:
    drop_resources(t);
    /* Keep a terminal result when BEGIN reached an allocated transaction.
     * A lost rejection ACK can then be recovered with its exact errno. */
    t->state = VKSO_ABORTED;
    list_add_tail(&t->list, &transactions);
    *out = t;
    return ret;
}

static int stage_transaction(struct transaction *t, const struct vkso_tx_request *r)
{
    u32 i, j;
    if (t->state != VKSO_STAGING) return -EBUSY;
    if (r->total != t->total || !r->count || r->count > MAX_PAGES_PER_OPERATION ||
        r->start > t->total || r->count > t->total - r->start)
        return -EINVAL;
    if (r->start < t->staged) {
        if (r->count > t->staged - r->start) return -EINVAL;
        for (i = 0; i < r->count; i++)
            if (memcmp(&t->pages[r->start+i].spec, &r->pages[i], sizeof(r->pages[i])))
                return -EALREADY;
        return 0; /* Exact retransmission is idempotent. */
    }
    if (r->start != t->staged) return -EINVAL;
    for (i = 0; i < r->count; i++) {
        const struct vkso_page_spec *p = &r->pages[i];
        t->failed_page = r->start + i;
        if (!IS_ALIGNED(p->offset, PAGE_SIZE) || p->offset > S64_MAX - PAGE_SIZE ||
            !IS_ALIGNED(p->source, PAGE_SIZE) || !p->source || p->reserved ||
            p->kind < VKSO_PAGE_TEXT || p->kind > VKSO_PAGE_SHARED_DATA)
            return -EINVAL;
        for (j = 0; j < t->staged; j++)
            if (t->pages[j].spec.offset == p->offset || t->pages[j].spec.source == p->source)
                return -EEXIST;
        for (j = 0; j < i; j++)
            if (r->pages[j].offset == p->offset || r->pages[j].source == p->source)
                return -EEXIST;
    }
    for (i = 0; i < r->count; i++)
        t->pages[t->staged+i].spec = r->pages[i];
    t->staged += r->count;
    t->failed_page = -1;
    return 0;
}

/* Validate and resolve every source before changing any target cache entry.
 * Owner pins precede lookup; source references outlive rollback and unmapping. */
static int prepare_sources(struct transaction *t)
{
    u32 i, j;
    struct transaction *other;
    for (i = 0; i < t->total; i++) {
        struct binding *b = &t->pages[i];
        struct page *p;
        u64 permissions;
        t->failed_page = i;
        if (i_size_read(file_inode(t->file)) < PAGE_SIZE ||
            b->spec.offset > i_size_read(file_inode(t->file)) - PAGE_SIZE)
            return -EINVAL;
        if (!source_allowed(t, &b->spec)) return -EACCES;
        p = lookup_kernel_page(b->spec.source, &permissions);
        if (!p) return -EFAULT;
        if (!source_permissions_allowed(b->spec.kind, permissions)) return -EACCES;
        for (j = 0; j < i; j++)
            if (t->pages[j].source == p) return -EEXIST;
        list_for_each_entry(other, &transactions, list) {
            if (other == t || !other->pages) continue;
            for (j = 0; j < other->total; j++)
                if (other->pages[j].source == p) return -EBUSY;
        }
        lock_page(p);
        if (p->mapping || PageLRU(p) || PageCompound(p) || PageSlab(p) ||
            PageSwapBacked(p) || PagePrivate(p) || PageDirty(p) || PageWriteback(p)) {
            unlock_page(p); return -EBUSY;
        }
        get_page(p);
        b->source = p;
        b->saved_mapping = p->mapping;
        b->saved_index = p->index;
        b->saved_uptodate = PageUptodate(p);
        unlock_page(p);
    }
    t->failed_page = -1;
    return 0;
}

/* invalidate_lock -> page lock -> xarray lock, as in the release path. */
static int apply_binding(struct transaction *t, struct binding *b)
{
    struct address_space *mapping = t->file->f_mapping;
    struct page *p = b->source, *old = b->old_cache;
    pgoff_t index = b->spec.offset >> PAGE_SHIFT;
    int ret = 0;
    XA_STATE(xas, &mapping->i_pages, index);
    lock_page(old);
    if (old->mapping != mapping || old->index != index || PageDirty(old) ||
        PageWriteback(old) || PageCompound(old) || PageSwapBacked(old)) {
        unlock_page(old); return -EBUSY;
    }
    lock_page(p);
    if (p->mapping || PageLRU(p) || PageCompound(p)) { ret = -EBUSY; goto out; }
    unmap_mapping_range(mapping, b->spec.offset, PAGE_SIZE, 0);
    if (page_mapped(old)) { ret = -EBUSY; goto out; }
    xas_lock_irq(&xas);
    /* Retain the occupied slot. With an ordinary one-page entry and both
     * pages locked, this store neither expands nor contracts the xarray.
     * delete_from_page_cache() + insert could free the last leaf node. */
    if (xas_load(&xas) != old) {
        ret = -ESTALE;
        goto unlock_xarray;
    }
    get_page(p);
    p->mapping = mapping;
    p->index = index;
    SetPageUptodate(p);
    xas_store(&xas, p);
    ret = xas_error(&xas);
    if (ret) {
        p->mapping = b->saved_mapping;
        p->index = b->saved_index;
        if (!b->saved_uptodate) ClearPageUptodate(p);
        put_page(p);
        goto unlock_xarray;
    }
    /* The resident source was already allocated as kernel memory. Do not
     * transfer the file page's memcg charge to it. The displaced ordinary
     * page keeps its own charge until its last reference is dropped, just
     * as with delete_from_page_cache(). nrpages is unchanged: one file
     * slot still exists, but the separate ordinary file page is removed. */
    __mod_lruvec_page_state(old, NR_FILE_PAGES, -1);
    old->mapping = NULL;
    xas_init_marks(&xas);
    b->applied = true;
    t->applied++;
unlock_xarray:
    xas_unlock_irq(&xas);
    if (!ret) {
        if (mapping->a_ops->freepage)
            mapping->a_ops->freepage(old);
        put_page(old); /* original cache reference; preparation still holds it */
        unmap_mapping_range(mapping, b->spec.offset, PAGE_SIZE, 0);
    }
out:
    unlock_page(p);
    unlock_page(old);
    if (!ret) {
        put_page(old); /* preparation reference */
        b->old_cache = NULL;
    }
    return ret;
}

static int release_binding(struct transaction *t, struct binding *b)
{
    struct address_space *mapping = t->file->f_mapping;
    struct page *p = b->source;
    pgoff_t index = b->spec.offset >> PAGE_SHIFT;
    int ret = 0;
    XA_STATE(xas, &mapping->i_pages, index);
    lock_page(p);
    xas_lock_irq(&xas);
    if (xas_load(&xas) != p || p->mapping != mapping || p->index != index) {
        ret = -ESTALE;
    } else {
        xas_store(&xas, NULL);
        ret = xas_error(&xas);
        if (!ret) mapping->nrpages--;
    }
    xas_unlock_irq(&xas);
    if (!ret) {
        /* Keep PageLocked through invalidation: a file fault holding an old
         * page reference must recheck mapping before it can install a PTE. */
        unmap_mapping_range(mapping, b->spec.offset, PAGE_SIZE, 0);
        p->mapping = b->saved_mapping;
        p->index = b->saved_index;
        if (!b->saved_uptodate) ClearPageUptodate(p);
        b->applied = false;
        t->applied--;
    }
    unlock_page(p);
    if (!ret) put_page(p); /* insertion reference */
    return ret;
}

/* Called with inode and invalidate locks held; continue past a failed page. */
static int rollback_bindings(struct transaction *t)
{
    u32 i = t->total;
    int first_error = 0;
    while (i--) {
        int ret;
        if (!t->pages[i].applied) continue;
        if (test_fail_release == i) {
            test_fail_release = -1;
            ret = -EIO;
        } else ret = release_binding(t, &t->pages[i]);
        if (ret && !first_error) {
            first_error = ret;
            t->failed_page = i;
        }
    }
    return first_error;
}

static int commit_transaction(struct transaction *t)
{
    struct address_space *mapping;
    u64 started = ktime_get_ns(), applying;
    u32 i;
    int ret;
    if (t->state == VKSO_ACTIVE) return 0;
    if (t->state != VKSO_STAGING || t->staged != t->total) return -EINVAL;
    mapping = t->file->f_mapping;
    inode_lock(file_inode(t->file));
    ret = filemap_write_and_wait(mapping);
    if (ret) goto unlock_inode;
    filemap_invalidate_lock(mapping);
    ret = prepare_sources(t);
    if (ret) goto unlock_mapping;
    for (i = 0; i < t->total; i++) {
        struct page *p = read_mapping_page(mapping, t->pages[i].spec.offset >> PAGE_SHIFT, NULL);
        if (IS_ERR(p)) { ret = PTR_ERR(p); t->failed_page = i; goto unlock_mapping; }
        t->pages[i].old_cache = p;
        lock_page(p);
        if (p->mapping != mapping || PageCompound(p) || PageSwapBacked(p) ||
            PageDirty(p) || PageWriteback(p)) {
            unlock_page(p);
            ret = -EOPNOTSUPP; t->failed_page = i; goto unlock_mapping;
        }
        /* Discard an optional secondary clean-cache copy before apply; a
         * later restore reloads the unchanged file through its filesystem. */
        cleancache_invalidate_page(mapping, p);
        unlock_page(p);
    }
    t->prepare_ns = ktime_get_ns() - started;
    applying = ktime_get_ns();
    for (i = 0; i < t->total; i++) {
        if (test_fail_apply == i) { test_fail_apply = -1; ret = -EIO; }
        else ret = apply_binding(t, &t->pages[i]);
        if (ret) { t->failed_page = i; break; }
    }
    t->apply_ns = ktime_get_ns() - applying;
    if (ret) {
        u64 releasing = ktime_get_ns();
        rollback_bindings(t);
        t->release_ns += ktime_get_ns() - releasing;
    }
unlock_mapping:
    filemap_invalidate_unlock(mapping);
unlock_inode:
    inode_unlock(file_inode(t->file));
    if (ret) {
        t->state = t->applied ? VKSO_RECOVERY_REQUIRED : VKSO_ABORTED;
        drop_resources(t);
    } else {
        t->state = VKSO_ACTIVE;
        t->failed_page = -1;
    }
    return ret;
}

static int release_transaction(struct transaction *t)
{
    u64 started = ktime_get_ns();
    int ret = 0;
    if (t->state == VKSO_RESTORED || t->state == VKSO_ABORTED) return 0;
    t->failed_page = -1;
    if (t->file) {
        inode_lock(file_inode(t->file));
        filemap_invalidate_lock(t->file->f_mapping);
        ret = rollback_bindings(t);
        filemap_invalidate_unlock(t->file->f_mapping);
        inode_unlock(file_inode(t->file));
    }
    t->state = t->applied ? VKSO_RECOVERY_REQUIRED : VKSO_RESTORED;
    t->release_ns += ktime_get_ns() - started;
    drop_resources(t);
    return ret;
}

static void snapshot(struct transaction *t, struct vkso_tx_result *r)
{
    if (!t) return;
    r->state = t->state; r->total = t->total;
    r->staged = t->staged; r->applied = t->applied;
    r->failed_page = t->failed_page;
    r->last_operation = t->last_operation;
    r->last_sequence = t->last_sequence;
    r->last_status = t->last_status;
    r->prepare_ns = t->prepare_ns; r->apply_ns = t->apply_ns;
    r->release_ns = t->release_ns;
}

static void reply_payload(struct sock *socket, struct sk_buff *request,
                          const struct nlmsghdr *h, u16 type, const void *data, size_t size)
{
    struct sk_buff *reply = nlmsg_new(size, GFP_KERNEL);
    struct nlmsghdr *out;
    if (!reply) return; /* QUERY retains the result when delivery fails. */
    out = nlmsg_put(reply, 0, h->nlmsg_seq, type, size, 0);
    if (!out) { kfree_skb(reply); return; }
    memcpy(nlmsg_data(out), data, size);
    nlmsg_unicast(socket, reply, NETLINK_CB(request).portid);
}

static void receive(struct sk_buff *skb, bool restore_socket)
{
    struct sock *socket = restore_socket ? nl_restore_sk : nl_sk;
    struct nlmsghdr *h;
    const struct vkso_tx_request *r;
    struct transaction *t = NULL;
    struct vkso_tx_result result = { .version = VKSO_PROTOCOL_VERSION, .failed_page = -1 };
    u64 started = ktime_get_ns();
    int ret = 0;
    bool forget = false;
    if (skb->len < NLMSG_HDRLEN) return;
    h = nlmsg_hdr(skb);
    if (!nlmsg_ok(h, skb->len) || h->nlmsg_len != skb->len) return;
    /* New and old managers negotiate without issuing a replacement. */
    if (h->nlmsg_type == VKSO_HELLO_V2 || h->nlmsg_type == VKSO_REQUEST_V2) {
        struct vkso_result legacy = { .version = VKSO_PROTOCOL_VERSION,
            .operation = restore_socket ? NETLINK_RESTORE : NETLINK_MODIFY,
            .failed_page = -1 };
        legacy.status = h->nlmsg_type == VKSO_HELLO_V2 ? 0 : -EPROTONOSUPPORT;
        if (!netlink_capable(skb, CAP_SYS_ADMIN)) legacy.status = -EPERM;
        reply_payload(socket, skb, h, VKSO_RESULT_V2, &legacy, sizeof(legacy));
        return;
    }
    if (h->nlmsg_type != VKSO_TX_REQUEST || nlmsg_len(h) < 16) return;
    r = nlmsg_data(h);
    result.transaction = r->transaction; result.operation = r->operation;
    if (!netlink_capable(skb, CAP_SYS_ADMIN)) { ret = -EPERM; goto reply; }
    if (r->version != VKSO_PROTOCOL_VERSION) { ret = -EPROTONOSUPPORT; goto reply; }
    if (nlmsg_len(h) != sizeof(*r)) { ret = -EMSGSIZE; goto reply; }
    mutex_lock(&operation_lock);
    t = find_transaction(r->transaction);
    if (r->operation == VKSO_BEGIN) {
        if (t) ret = -EEXIST;
        else ret = begin_transaction(r, NETLINK_CB(skb).portid, &t);
    } else if (!t) ret = -ENOENT;
    else if (r->operation == VKSO_QUERY) { /* Privileged recovery may reconnect. */ }
    else if (r->operation == VKSO_RELEASE) ret = release_transaction(t);
    else if (r->operation == VKSO_FORGET) {
        if (t->file || t->applied) ret = -EBUSY;
        else forget = true;
    } else if (NETLINK_CB(skb).portid != t->controller_port) ret = -EPERM;
    else if (r->operation == VKSO_STAGE) ret = stage_transaction(t, r);
    else if (r->operation == VKSO_COMMIT) ret = commit_transaction(t);
    else ret = -EINVAL;
    if (t && r->operation != VKSO_QUERY) {
        t->last_operation = r->operation; t->last_sequence = h->nlmsg_seq;
        t->last_status = ret;
    }
    snapshot(t, &result);
    if (forget) { list_del(&t->list); kvfree(t->pages); kfree(t); }
    if (test_drop_reply == r->operation) {
        test_drop_reply = 0;
        mutex_unlock(&operation_lock);
        return;
    }
    mutex_unlock(&operation_lock);
reply:
    result.status = ret;
    result.operation_ns = ktime_get_ns() - started;
    reply_payload(socket, skb, h, VKSO_TX_RESULT, &result, sizeof(result));
}
static void nl_recv_msg(struct sk_buff *skb) { receive(skb, false); }
static void nl_recv_restore_msg(struct sk_buff *skb) { receive(skb, true); }
static int __init page_replace_init(void)
{
    struct netlink_kernel_cfg cfg = { .input = nl_recv_msg };
    struct netlink_kernel_cfg restore_cfg = { .input = nl_recv_restore_msg };
    nl_sk = netlink_kernel_create(&init_net, NETLINK_MODIFY, &cfg);
    if (!nl_sk) return -ENOMEM;
    nl_restore_sk = netlink_kernel_create(&init_net, NETLINK_RESTORE, &restore_cfg);
    if (!nl_restore_sk) { netlink_kernel_release(nl_sk); return -ENOMEM; }
    return 0;
}
static void __exit page_replace_exit(void)
{
    struct transaction *t, *next;
    netlink_kernel_release(nl_restore_sk);
    netlink_kernel_release(nl_sk);
    /* A live transaction pins this module. Only terminal query records remain. */
    list_for_each_entry_safe(t, next, &transactions, list) {
        list_del(&t->list); kvfree(t->pages); kfree(t);
    }
}
module_init(page_replace_init);
module_exit(page_replace_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("VKSO resident-page registration transactions");
