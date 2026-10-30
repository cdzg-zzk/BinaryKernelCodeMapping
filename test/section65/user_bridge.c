// SPDX-License-Identifier: GPL-2.0-only
/* Private ISO image adapter. Kernel layouts are an internal, pinned ABI.
 * One handle is owned by one thread; independent handles have independent state.
 * Cached inodes live until close. No shared kernel cache or device is accessed.
 */
#include <linux/slab.h>
#include <linux/blkdev.h>
#include <linux/nls.h>
#include "isofs.h"

extern void *malloc(size_t);
extern void *calloc(size_t, size_t);
extern void free(void *);
extern int open(const char *, int, ...);
extern int close(int);
extern ssize_t pread(int, void *, size_t, long);
extern int vsnprintf(char *, size_t, const char *, va_list);
extern ssize_t write(int, const void *, size_t);

struct cached_inode { struct iso_inode_info info; struct cached_inode *next; int state; };
#ifdef ISO_LOOKUP_CACHE
struct cached_name {
    struct cached_name *next;
    struct inode *parent, *inode;
    unsigned int length;
    char name[];
};
#endif
struct iso_image {
    struct super_block sb;
    struct cached_inode *inodes;
    int fd;
    int table;
    unsigned long bytes_read, io_calls, inode_count;
#ifdef ISO_LOOKUP_CACHE
    struct cached_name *names[256];
    unsigned long lookup_calls, lookup_hits, cached_names;
#endif
};
struct iso_metadata { u64 size, ino; s64 mtime_sec, mtime_nsec; u32 mode, uid, gid, nlink; };
struct list_context { struct dir_context ctx; int (*emit)(void *, const char *, int); void *arg; };

static struct iso_image *image_of(struct super_block *s)
{ return container_of(s, struct iso_image, sb); }

void *__kmalloc(size_t n, gfp_t flags)
{ return (flags & __GFP_ZERO) ? calloc(1, n) : malloc(n); }
void kfree(const void *p) { free((void *)p); }

static int read_exact(struct iso_image *im, void *data, size_t n, u64 offset)
{
    size_t done = 0;
    while (done < n) {
        ssize_t count = pread(im->fd, (char *)data + done, n - done, offset + done);
        im->io_calls++;
        if (count <= 0) return -EIO;
        done += count;
        im->bytes_read += count;
    }
    return 0;
}
struct buffer_head *iso_kernel_getblk(struct super_block *s, sector_t b)
{
    struct buffer_head *bh = calloc(1, sizeof(*bh) + s->s_blocksize);
    if (!bh) return NULL;
    bh->b_blocknr = b;
    bh->b_size = s->s_blocksize;
    bh->b_data = (char *)(bh + 1);
    return bh;
}
struct buffer_head *iso_kernel_bread(struct super_block *s, sector_t b)
{
    struct buffer_head *bh = iso_kernel_getblk(s, b);
    if (!bh) return NULL;
    if (read_exact(image_of(s), bh->b_data, s->s_blocksize, (u64)b * s->s_blocksize)) {
        free(bh); return NULL;
    }
    return bh;
}
void iso_kernel_brelse(struct buffer_head *b) { free(b); }
void iso_kernel_put_bh(struct buffer_head *b) { free(b); }

struct inode *__isofs_iget(struct super_block *s, unsigned long b, unsigned long o, int relocated)
{
    struct iso_image *im = image_of(s);
    struct cached_inode *p;
    int ret;
    for (p = im->inodes; p; p = p->next) {
        if (p->info.i_iget5_block == b && p->info.i_iget5_offset == o)
            return p->state == 1 ? &p->info.vfs_inode : ERR_PTR(-EIO);
    }
    p = calloc(1, sizeof(*p));
    if (!p) return ERR_PTR(-ENOMEM);
    p->next = im->inodes; im->inodes = p; im->inode_count++;
    p->info.i_iget5_block = b; p->info.i_iget5_offset = o;
    p->info.vfs_inode.i_sb = s;
    p->info.vfs_inode.i_blkbits = s->s_blocksize_bits;
    p->info.vfs_inode.i_mapping = &p->info.vfs_inode.i_data;
    p->info.vfs_inode.i_data.host = &p->info.vfs_inode;
    ret = isofs_read_inode(&p->info.vfs_inode, relocated);
    p->state = ret ? -1 : 1;
    return ret ? ERR_PTR(ret) : &p->info.vfs_inode;
}
/* Handle-owned cache: dropping a temporary reference retains the cached inode. */
void iput(struct inode *i) { }
void set_nlink(struct inode *i, unsigned int n) { i->__i_nlink = n; }
void iso_kernel_uid(struct inode *i, uid_t u) { i->i_uid.val = u; }
void iso_kernel_gid(struct inode *i, gid_t g) { i->i_gid.val = g; }
int sb_set_blocksize(struct super_block *s, int n)
{
    unsigned int bits = 0;
    if (n != 512 && n != 1024 && n != 2048) return 0;
    s->s_blocksize = n;
    while (n >>= 1) bits++;
    s->s_blocksize_bits = bits;
    return s->s_blocksize;
}
struct dentry *d_make_root(struct inode *i)
{
    struct dentry *d = calloc(1, sizeof(*d));
    if (d) { d->d_inode = i; d->d_sb = i->i_sb; d->d_parent = d; }
    return d;
}
struct dentry *d_splice_alias(struct inode *i, struct dentry *d)
{
    if (IS_ERR(i)) return (void *)i;
    d->d_inode = i;
    return NULL;
}
/* Only UTF-8 is in the selected profile; other NLS choices fail explicitly. */
struct nls_table *load_nls(const char *name) { return NULL; }
struct nls_table *load_nls_default(void) { return NULL; }
void unload_nls(struct nls_table *nls) { }
int iso_kernel_attach_inode(struct inode *i)
{
    return (S_ISREG(i->i_mode) || S_ISDIR(i->i_mode) || S_ISLNK(i->i_mode) ||
            S_ISCHR(i->i_mode) || S_ISBLK(i->i_mode) || S_ISFIFO(i->i_mode) ||
            S_ISSOCK(i->i_mode)) ? 0 : -EIO;
}
void iso_kernel_attach_super(struct super_block *s, int table) { image_of(s)->table = table; }
bool iso_kernel_dotdot(struct file *f, struct dir_context *ctx)
{ return ctx->actor(ctx, "..", 2, ctx->pos, 0, DT_DIR) == 0; }
int _printk(const char *format, ...)
{
    char buf[512]; va_list ap; int n;
    va_start(ap, format); n = vsnprintf(buf, sizeof(buf), format, ap); va_end(ap);
    if (n > 0) write(2, buf, n < sizeof(buf) ? n : sizeof(buf)-1);
    return n;
}
/* Linux mktime64 arithmetic, kernel/time/time.c (GPL-2.0). */
time64_t mktime64(unsigned int year0, unsigned int mon0, unsigned int day,
                 unsigned int hour, unsigned int min, unsigned int sec)
{
    unsigned int mon = mon0, year = year0;
    if (0 >= (int)(mon -= 2)) { mon += 12; year -= 1; }
    return ((((time64_t)(year/4 - year/100 + year/400 + 367*mon/12 + day) +
            year*365 - 719499)*24 + hour)*60 + min)*60 + sec;
}
/* Same trailing-dot and ASCII case rules as isofs_dentry_cmp_common. */
static int compare_name(unsigned int len, const char *str, const struct qstr *name, int ms, int ci)
{
    unsigned int a = name->len, b = len, j;
    if (ms) { while (a && name->name[a-1] == '.') a--; while (b && str[b-1] == '.') b--; }
    if (a != b) return 1;
    for (j = 0; j < a; j++) {
        unsigned char x = name->name[j], y = str[j];
        if (ci) { if (x >= 'A' && x <= 'Z') x += 32; if (y >= 'A' && y <= 'Z') y += 32; }
        if (x != y) return 1;
    }
    return 0;
}
static int cmp1(const struct dentry *d, unsigned int n, const char *s, const struct qstr *q)
{ return compare_name(n,s,q,0,1); }
static int cmp2(const struct dentry *d, unsigned int n, const char *s, const struct qstr *q)
{ return compare_name(n,s,q,1,0); }
static int cmp3(const struct dentry *d, unsigned int n, const char *s, const struct qstr *q)
{ return compare_name(n,s,q,1,1); }
static const struct dentry_operations comparisons[] = {
    {.d_compare=cmp1}, {.d_compare=cmp2}, {.d_compare=cmp3}
};

void iso_close_image(struct iso_image *im)
{
    struct cached_inode *p, *next;
    if (!im) return;
#ifdef ISO_LOOKUP_CACHE
    unsigned int j;
    for (j=0; j<ARRAY_SIZE(im->names); j++) {
        struct cached_name *entry=im->names[j];
        while (entry) { struct cached_name *next_name=entry->next; free(entry); entry=next_name; }
    }
#endif
    for (p = im->inodes; p; p = next) { next = p->next; free(p); }
    free(im->sb.s_root); free(im->sb.s_fs_info);
    if (im->fd >= 0) close(im->fd);
    free(im);
}
struct iso_image *iso_open_image(const char *path, int norock)
{
    struct iso_image *im = calloc(1, sizeof(*im));
    struct iso9660_options opt = { .rock=1, .joliet=1, .map='n', .check='u', .blocksize=1024,
        .fmode=ISOFS_INVALID_MODE, .dmode=ISOFS_INVALID_MODE, .session=-1, .sbsector=-1 };
    int ret;
    if (!im) return NULL;
    im->fd = open(path, 0);
    if (im->fd < 0) { free(im); return NULL; }
    opt.rock = !norock;
    im->sb.s_flags = SB_RDONLY;
    sb_set_blocksize(&im->sb, opt.blocksize);
    ret = iso_read_super(&im->sb, &opt, 0, 0);
    if (ret) { iso_close_image(im); return NULL; }
    return im;
}
struct inode *iso_root_inode(struct iso_image *im) { return im->sb.s_root->d_inode; }
struct inode *iso_lookup_child(struct inode *parent, const char *name, unsigned int n)
{
    struct dentry d = { .d_name = { .name = name, .len = n } };
    struct iso_image *im = image_of(parent->i_sb);
    struct dentry *result;
    struct inode *inode;
    if (!S_ISDIR(parent->i_mode)) return NULL;
#ifdef ISO_LOOKUP_CACHE
    /* Exact positive lookups are stable for this immutable, handle-owned image.
     * Misses and case-folded aliases still go through the kernel implementation.
     */
    unsigned int j, hash=(unsigned long)parent >> 4;
    struct cached_name *entry;
    im->lookup_calls++;
    for (j=0; j<n; j++) hash=(hash ^ (unsigned char)name[j])*16777619U;
    hash &= ARRAY_SIZE(im->names)-1;
    for (entry=im->names[hash]; entry; entry=entry->next) {
        if (entry->parent==parent && entry->length==n && !memcmp(entry->name,name,n)) {
            im->lookup_hits++;
            return entry->inode;
        }
    }
#endif
    if (im->table) d.d_op = &comparisons[im->table-1];
    result = isofs_lookup(parent, &d, 0);
    if (IS_ERR(result)) return NULL;
    inode=result ? result->d_inode : d.d_inode;
#ifdef ISO_LOOKUP_CACHE
    if (inode && (entry=malloc(sizeof(*entry)+n))) {
        entry->parent=parent; entry->inode=inode; entry->length=n;
        memcpy(entry->name,name,n);
        entry->next=im->names[hash]; im->names[hash]=entry; im->cached_names++;
    }
#endif
    return inode;
}
#ifdef ISO_LOOKUP_CACHE
void iso_lookup_stats(struct iso_image *im, unsigned long values[3])
{ values[0]=im->lookup_calls; values[1]=im->lookup_hits; values[2]=im->cached_names; }
#endif
void iso_inode_metadata(struct inode *i, struct iso_metadata *m)
{
    m->size=i->i_size; m->ino=i->i_ino; m->mode=i->i_mode;
    m->uid=i->i_uid.val; m->gid=i->i_gid.val; m->nlink=i->i_nlink;
    m->mtime_sec=i->i_mtime.tv_sec; m->mtime_nsec=i->i_mtime.tv_nsec;
}
static int actor(struct dir_context *ctx, const char *name, int n, loff_t pos, u64 ino, unsigned int type)
{
    struct list_context *list = container_of(ctx, struct list_context, ctx);
    if ((n == 1 && name[0] == '.') || (n == 2 && name[0] == '.' && name[1] == '.')) return 0;
    return list->emit(list->arg, name, n);
}
int iso_list_inode(struct inode *i, int (*emit)(void *, const char *, int), void *arg)
{
    struct dentry d = { .d_inode=i };
    struct file f = { .f_inode=i, .f_path = { .dentry=&d } };
    struct list_context c = { .ctx = { .actor=actor }, .emit=emit, .arg=arg };
    if (!S_ISDIR(i->i_mode)) return -ENOTDIR;
    return isofs_readdir(&f, &c.ctx);
}
int iso_inode_readlink(struct inode *i, char *out, size_t n)
{
    if (!S_ISLNK(i->i_mode) || n < PAGE_SIZE) return -EINVAL;
    return iso_readlink(i, out);
}
ssize_t iso_read_inode_data(struct inode *i, void *out, size_t n, u64 offset)
{
    struct iso_image *im = image_of(i->i_sb);
    size_t done = 0;
    if (!S_ISREG(i->i_mode)) return -EINVAL;
    if (ISOFS_I(i)->i_file_format != isofs_file_normal) return -EOPNOTSUPP;
    if (offset >= i->i_size) return 0;
    if (n > i->i_size - offset) n = i->i_size - offset;
    while (done < n) {
        struct buffer_head bh = {0}, *p = &bh;
        size_t skip = (offset + done) & (im->sb.s_blocksize-1);
        size_t count = min_t(size_t, n - done, im->sb.s_blocksize - skip);
        int ret = isofs_get_blocks(i, (offset+done) >> im->sb.s_blocksize_bits, &p, 1);
        if (ret != 1) return -EIO;
        ret = read_exact(im, (char *)out+done, count, bh.b_blocknr*im->sb.s_blocksize+skip);
        if (ret) return ret;
        done += count;
    }
    return done;
}
