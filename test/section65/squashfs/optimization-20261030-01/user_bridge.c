// SPDX-License-Identifier: GPL-2.0-or-later
/* Domain-private state for the pinned SquashFS ABI. One image handle is
 * accessed by one thread. Native kernel caches/locks are never accessed here.
 */
#include <linux/slab.h>
#include <linux/blkdev.h>
#include <linux/fs_context.h>
#include <linux/xattr.h>
#include "squashfs_fs.h"
#include "squashfs_fs_sb.h"
#include "squashfs_fs_i.h"
#include "squashfs.h"
#include "decompressor.h"
#include "page_actor.h"
#include "profile.h"
#ifdef VKSO_SQ_PROFILE
struct sq_work_profile sq_work;
#endif

extern void *malloc(size_t), *calloc(size_t,size_t);
extern void free(void *);
extern int close(int), vsnprintf(char *,size_t,const char *,va_list);
extern ssize_t pread(int,void *,size_t,long), write(int,const void *,size_t);
extern int sq_posix_open(const char *,u64,u64 *);
extern void *sq_codec_open(int);
extern void sq_codec_close(void *);
extern int sq_codec_decode(void *,const void *,size_t,void *,size_t);

/* Single-threaded, read-only images: cached names use stable image-local inode
 * numbers and on-disk locations, never pointers into the evictable inode cache.
 * Borrowed lookup results survive until the next lookup/allocation. Open file
 * and directory handles explicitly pin their inodes. Root stays pinned.
 * Retention is bounded by these budgets plus live pinned handles, not image size.
 */
#define SQ_INODE_BUDGET 2048U
#define SQ_NAME_BUDGET 4096U
struct cached_inode {
    struct squashfs_inode_info info;
    struct cached_inode *next,*prev,*hash_next,*older,*newer;
    long long location;
    unsigned int pins;
    int valid,on_lru;
};
struct cached_name {
    struct cached_name *next,*older,*newer;
    unsigned long parent,number;
    long long location;
    unsigned int length,slot;
    char name[];
};
struct sq_image {
    struct super_block sb;
    struct cached_inode *inodes,*index[1024];
    struct cached_name *names[1024];
    struct cached_inode *inode_oldest,*inode_newest;
    struct cached_name *name_oldest,*name_newest;
    u64 inode_count,name_count,inode_evictions,name_evictions;
    u64 inode_peak,name_peak;
    struct squashfs_cache_entry busy;
    int fd;
    u64 offset,bytes;
};
struct raw_bytes { size_t length; unsigned char bytes[]; };
struct user_stream { void *codec,*output; size_t capacity; };
struct sq_metadata { u64 size,ino,blocks,rdev; s64 mtime_sec,mtime_nsec; u32 mode,uid,gid,nlink; };
struct list_context { struct dir_context ctx; int (*emit)(void *,const char *,int); void *arg; };
static struct sq_image *image_of(struct super_block *s) { return container_of(s,struct sq_image,sb); }
static void *u_alloc(size_t n,gfp_t g) { return (g&__GFP_ZERO) ? calloc(1,n) : malloc(n); }
static void *u_array(size_t n,size_t z,gfp_t g) { return calloc(n,z); }
static void u_free(const void *p) { free((void *)p); }
static void u_mutex(struct mutex *m) { }
static int u_print(const char *fmt,...)
{
    char b[1024]; va_list ap; int n;
    va_start(ap,fmt); n=vsnprintf(b,sizeof(b),fmt,ap); va_end(ap);
    if (n>0) write(2,b,min_t(size_t,n,sizeof(b)-1));
    return n;
}
static void u_error(struct fs_context *fc,const char *fmt,...)
{
    char b[1024]; va_list ap; int n;
    va_start(ap,fmt); n=vsnprintf(b,sizeof(b),fmt,ap); va_end(ap);
    if (n>0) { write(2,b,min_t(size_t,n,sizeof(b)-1)); write(2,"\n",1); }
}
static void u_debug(struct _ddebug *d,const char *fmt,...) { }
static void u_fatal(const char *s) { u_print("%s\n",s); }

static void *actor_first(struct squashfs_page_actor *a) { a->next_page=1; return a->buffer[0]; }
static void *actor_next(struct squashfs_page_actor *a) { return a->next_page==a->pages ? NULL : a->buffer[a->next_page++]; }
static void actor_finish(struct squashfs_page_actor *a) { }
static struct squashfs_page_actor *u_actor(void **data,int pages,int length)
{
    struct squashfs_page_actor *a=calloc(1,sizeof(*a));
    if (!a) return NULL;
    a->buffer=data; a->pages=pages; a->length=length ?: pages*PAGE_SIZE;
    a->squashfs_first_page=actor_first; a->squashfs_next_page=actor_next; a->squashfs_finish_page=actor_finish;
    return a;
}
static int scatter(struct squashfs_page_actor *a,const void *data,int length)
{
    SQ_START(start);
    int done=0;
    if (length<0 || length>a->length) return -EIO;
    while (done<length) {
        int n=min_t(int,length-done,PAGE_SIZE);
        memcpy(a->buffer[done/PAGE_SIZE],(const char *)data+done,n); done+=n;
    }
    SQ_COUNT(scatter_calls,1); SQ_COUNT(scatter_bytes,done); SQ_ELAPSED(scatter_ns,start);
    return done;
}
static int u_read_raw(struct super_block *sb,u64 index,int n,struct bio **output,int *offset)
{
    struct sq_image *im=image_of(sb);
    struct raw_bytes *b;
    int done=0;
    if (n<0 || index>im->bytes || (u64)n>im->bytes-index) return -EIO;
    SQ_COUNT(raw_calls,1); SQ_COUNT(raw_bytes,n);
    b=malloc(sizeof(*b)+n);
    if (!b) return -ENOMEM;
    b->length=n;
    while (done<n) {
        ssize_t r=pread(im->fd,b->bytes+done,n-done,im->offset+index+done);
        if (r<=0) { free(b); return -EIO; }
        done+=r;
    }
    *output=(struct bio *)b; *offset=0; return 0;
}
static int u_byte(struct bio *bio,int offset)
{
    struct raw_bytes *b=(void *)bio;
    return offset<0 || (size_t)offset>=b->length ? -EIO : b->bytes[offset];
}
static void u_free_raw(struct bio *b) { free(b); }
static int u_copy_raw(struct bio *bio,struct squashfs_page_actor *a,int offset,int n)
{
    struct raw_bytes *b=(void *)bio;
    if (offset<0 || n<0 || (size_t)offset>b->length || (size_t)n>b->length-offset) return -EIO;
    return scatter(a,b->bytes+offset,n);
}

static void u_cache_delete(struct squashfs_cache *c)
{
    int i;
    if (!c) return;
    for (i=0;c->entry && i<c->entries;i++) {
        if (c->entry[i].data) free(c->entry[i].data[0]);
        free(c->entry[i].data); free(c->entry[i].actor);
    }
    free(c->entry); free(c);
}
static struct squashfs_cache *u_cache_init(char *name,int entries,int blocksize)
{
    struct squashfs_cache *c=calloc(1,sizeof(*c)); int i,j;
    if (!c) return NULL;
    c->entries=entries; c->block_size=blocksize; c->pages=DIV_ROUND_UP(blocksize,PAGE_SIZE); c->name=name;
    c->entry=calloc(entries,sizeof(*c->entry));
    if (!c->entry) goto fail;
    for (i=0;i<entries;i++) {
        struct squashfs_cache_entry *e=&c->entry[i];
        e->cache=c; e->block=SQUASHFS_INVALID_BLK;
        e->data=calloc(c->pages,sizeof(void *));
        if (!e->data) goto fail;
        e->data[0]=malloc(c->pages*PAGE_SIZE);
        if (!e->data[0]) goto fail;
        for (j=1;j<c->pages;j++) e->data[j]=(char *)e->data[0]+j*PAGE_SIZE;
        e->actor=u_actor(e->data,c->pages,blocksize);
        if (!e->actor) goto fail;
    }
    return c;
fail: u_cache_delete(c); return NULL;
}
static struct squashfs_cache_entry *u_cache_get(struct super_block *sb,struct squashfs_cache *c,u64 block,int length)
{
    int i;
    struct squashfs_cache_entry *e;
    SQ_COUNT(cache_gets,1);
    for (i=0;i<c->entries;i++) if (c->entry[i].block==block) {
        SQ_COUNT(cache_hits,1);
        c->entry[i].refcount++; return &c->entry[i];
    }
    for (i=0;i<c->entries;i++) {
        e=&c->entry[c->next_blk]; c->next_blk=(c->next_blk+1)%c->entries;
        if (e->refcount) continue;
        SQ_COUNT(cache_misses,1);
        e->block=block; e->refcount=1;
        e->length=squashfs_read_data(sb,block,length,&e->next_index,e->actor);
        e->error=e->length<0 ? e->length : 0;
        return e;
    }
    image_of(sb)->busy.error=-EBUSY;
    return &image_of(sb)->busy;
}
static void u_cache_put(struct squashfs_cache_entry *e) { if (e->cache) e->refcount--; }

static const struct squashfs_decompressor codecs[]={
    {.id=1,.name="gzip",.supported=1}, {.id=3,.name="lzo",.supported=1},
    {.id=4,.name="xz",.supported=1,.comp_opts=squashfs_xz_comp_opts},
    {.id=5,.name="lz4",.supported=1,.comp_opts=lz4_comp_opts},
    {.id=6,.name="zstd",.supported=1}, {.id=0,.name="unsupported",.supported=0}
};
static const struct squashfs_decompressor *u_lookup_codec(int id)
{ int i; for (i=0;codecs[i].id && codecs[i].id!=id;i++); return &codecs[i]; }
static int u_max_codecs(void) { return 1; }
static void *u_codec_create(struct squashfs_sb_info *s,void *options)
{
    struct user_stream *p=calloc(1,sizeof(*p));
    if (!p) return ERR_PTR(-ENOMEM);
    p->capacity=max_t(int,s->block_size,SQUASHFS_METADATA_SIZE);
    p->codec=sq_codec_open(s->decompressor->id); p->output=malloc(p->capacity);
    if (!p->codec || !p->output) { sq_codec_close(p->codec); free(p->output); free(p); return ERR_PTR(-ENOMEM); }
    free(options); return p;
}
static void u_codec_destroy(struct squashfs_sb_info *s)
{
    struct user_stream *p=(void *)s->stream;
    if (p) { sq_codec_close(p->codec); free(p->output); free(p); }
}
static int u_decompress(struct squashfs_sb_info *s,struct bio *bio,int offset,int length,struct squashfs_page_actor *a)
{
    struct user_stream *p=(void *)s->stream;
    struct raw_bytes *b=(void *)bio; int ret;
    if (offset<0 || length<0 || (size_t)offset>b->length || (size_t)length>b->length-offset || a->length>p->capacity) return -EIO;
#ifdef VKSO_SQ_DIRECT_DECODE
    /* These callbacks identify our user-owned actor, whose page vector can
     * represent either contiguous cache storage or a scattered fallback. */
    if (a->squashfs_first_page==actor_first && a->length>0 &&
        a->pages>0 && a->length<=(size_t)a->pages*PAGE_SIZE && a->buffer[0]) {
        int j,contiguous=1;
        for (j=1;j<DIV_ROUND_UP(a->length,PAGE_SIZE);j++)
            if (a->buffer[j]!=(char *)a->buffer[0]+j*PAGE_SIZE) { contiguous=0;break; }
        if (contiguous)
            return sq_codec_decode(p->codec,b->bytes+offset,length,a->buffer[0],a->length);
    }
#endif
    ret=sq_codec_decode(p->codec,b->bytes+offset,length,p->output,a->length);
    return ret<0 ? ret : scatter(a,p->output,ret);
}

static struct cached_inode *cached(struct inode *i)
{ return container_of(squashfs_i(i),struct cached_inode,info); }
static void inode_unqueue(struct sq_image *im,struct cached_inode *p)
{
    if (!p->on_lru) return;
    if (p->older) p->older->newer=p->newer; else im->inode_oldest=p->newer;
    if (p->newer) p->newer->older=p->older; else im->inode_newest=p->older;
    p->older=p->newer=NULL;p->on_lru=0;
}
static void inode_touch(struct sq_image *im,struct cached_inode *p)
{
    if (p->pins || !p->valid) return;
    inode_unqueue(im,p);p->older=im->inode_newest;
    if (p->older) p->older->newer=p; else im->inode_oldest=p;
    im->inode_newest=p;p->on_lru=1;
}
static void inode_destroy(struct sq_image *im,struct cached_inode *p)
{
    struct cached_inode **q;
    inode_unqueue(im,p);
    if (p->valid) {
        q=&im->index[p->info.vfs_inode.i_ino%ARRAY_SIZE(im->index)];
        while (*q && *q!=p) q=&(*q)->hash_next;
        if (*q) *q=p->hash_next;
    }
    if (p->prev) p->prev->next=p->next; else im->inodes=p->next;
    if (p->next) p->next->prev=p->prev;
    im->inode_count--;free(p);
}
static void inode_trim(struct sq_image *im,unsigned int target)
{
    while (im->inode_count>target && im->inode_oldest) {
        inode_destroy(im,im->inode_oldest);im->inode_evictions++;
    }
}
void sq_inode_pin(struct inode *i)
{
    struct cached_inode *p=cached(i);
    inode_unqueue(image_of(i->i_sb),p);p->pins++;
}
static void inode_unpin(struct inode *i)
{
    struct cached_inode *p=cached(i);
    if (p->pins && !--p->pins) inode_touch(image_of(i->i_sb),p);
}
void sq_inode_release(struct inode *i)
{
    struct sq_image *im=image_of(i->i_sb);
    inode_unpin(i);inode_trim(im,SQ_INODE_BUDGET);
}
static struct inode *u_new_inode(struct super_block *sb)
{
    SQ_COUNT(new_inodes,1);
    struct sq_image *im=image_of(sb);
    struct cached_inode *p;
    struct inode *i;
    inode_trim(im,SQ_INODE_BUDGET-1);
    p=calloc(1,sizeof(*p));
    if (!p) return NULL;
    p->next=im->inodes;if (p->next) p->next->prev=p;
    im->inodes=p;im->inode_count++;
    im->inode_peak=max(im->inode_peak,im->inode_count);i=&p->info.vfs_inode;
    i->i_sb=sb; i->i_mapping=&i->i_data; i->i_data.host=i;
    return i;
}
static void u_insert(struct inode *i)
{
    struct cached_inode *p=container_of(squashfs_i(i),struct cached_inode,info);
    struct sq_image *im=image_of(i->i_sb); unsigned int slot=i->i_ino%ARRAY_SIZE(im->index);
    p->valid=1; p->hash_next=im->index[slot]; im->index[slot]=p;inode_touch(im,p);
}
static struct inode *u_iget(struct super_block *sb,long long location,unsigned int number)
{
    struct cached_inode *p; struct inode *i; int ret;
    for (p=image_of(sb)->index[number%ARRAY_SIZE(image_of(sb)->index)];p;p=p->hash_next)
        if (p->info.vfs_inode.i_ino==number) {
            inode_touch(image_of(sb),p);return &p->info.vfs_inode;
        }
    i=u_new_inode(sb); if (!i) return ERR_PTR(-ENOMEM);
    cached(i)->location=location;
    ret=squashfs_read_inode(i,location);
    if (ret) { inode_destroy(image_of(sb),cached(i));return ERR_PTR(ret); }
    u_insert(i); return i;
}
static void u_inode_noop(struct inode *i) { }
static void u_iput(struct inode *i)
{ if (i && !cached(i)->valid) inode_destroy(image_of(i->i_sb),cached(i)); }
static void u_nlink(struct inode *i,unsigned int n) { i->__i_nlink=n; }
static void u_uid(struct inode *i,uid_t n) { i->i_uid.val=n; }
static void u_gid(struct inode *i,gid_t n) { i->i_gid.val=n; }
static void u_special(struct inode *i,umode_t mode,dev_t dev) { i->i_mode=mode; i->i_rdev=dev; }
static int u_blocksize(struct super_block *sb,int size)
{ sb->s_blocksize=size; sb->s_blocksize_bits=__builtin_ctz(size); return size; }
static loff_t u_size(struct super_block *sb) { return image_of(sb)->bytes; }
static struct dentry *u_make_root(struct inode *i)
{ struct dentry *d=calloc(1,sizeof(*d)); if (d) { d->d_inode=i; d->d_sb=i->i_sb; d->d_parent=d; sq_inode_pin(i); } return d; }
static struct dentry *u_splice(struct inode *i,struct dentry *d)
{ if (IS_ERR(i)) return (void *)i; d->d_inode=i; return NULL; }
static const struct xattr_handler user_xattr={.prefix="user."}, security_xattr={.prefix="security."};
static const struct xattr_handler *u_xattr_handler(int type)
{
    if (type&~(SQUASHFS_XATTR_PREFIX_MASK|SQUASHFS_XATTR_VALUE_OOL)) return NULL;
    switch (type&SQUASHFS_XATTR_PREFIX_MASK) {
    case SQUASHFS_XATTR_USER: return &user_xattr;
    case SQUASHFS_XATTR_SECURITY: return &security_xattr;
    default: return NULL;
    }
}
static const struct sq_support bindings={
    .alloc=u_alloc,.alloc_array=u_array,.free=u_free,
    .mutex_init=u_mutex,.mutex_lock=u_mutex,.mutex_unlock=u_mutex,
    .cache_init=u_cache_init,.cache_delete=u_cache_delete,.cache_get=u_cache_get,.cache_put=u_cache_put,
    .actor_init=u_actor,.iget=u_iget,.new_inode=u_new_inode,.bad_inode=u_inode_noop,.insert_inode=u_insert,
    .iput=u_iput,.nlink=u_nlink,.uid=u_uid,.gid=u_gid,.special_inode=u_special,.nohighmem=u_inode_noop,
    .blocksize=u_blocksize,.device_size=u_size,.make_root=u_make_root,.splice_alias=u_splice,
    .lookup_decompressor=u_lookup_codec,.max_decompressors=u_max_codecs,
    .decompressor_create=u_codec_create,.decompressor_destroy=u_codec_destroy,
    .read_raw=u_read_raw,.input_byte=u_byte,.free_raw=u_free_raw,.decompress=u_decompress,.copy_raw=u_copy_raw,
    .error=u_error,.print=u_print,.dynamic_debug=u_debug,.fatal=u_fatal,
    .memcpy=memcpy,.memset=memset,.memcmp=memcmp,.strcmp=strcmp,.strncmp=strncmp,.strncpy=strncpy,
    .strlen=strlen,.xattr_handler=u_xattr_handler
};
struct sq_support sq_support;
void __attribute__((constructor)) sq_user_init(void) { sq_bind_support(&bindings); }

void sq_close_image(struct sq_image *im)
{
    struct cached_inode *p,*next; unsigned int j;
    struct squashfs_sb_info *s;
    if (!im) return;
    s=im->sb.s_fs_info;
    if (s) {
        u_cache_delete(s->block_cache); u_cache_delete(s->fragment_cache); u_cache_delete(s->read_page);
        u_codec_destroy(s); free(s->inode_lookup_table); free(s->fragment_index);
        free(s->id_table); free(s->xattr_id_table); free(s->meta_index); free(s);
    }
    for (p=im->inodes;p;p=next) { next=p->next; free(p); }
    for (j=0;j<ARRAY_SIZE(im->names);j++) {
        struct cached_name *n=im->names[j];
        while (n) { struct cached_name *next_name=n->next; free(n); n=next_name; }
    }
    free(im->sb.s_root); if (im->fd>=0) close(im->fd); free(im);
}
struct sq_image *sq_open_image(const char *path,u64 offset)
{
    struct sq_image *im=calloc(1,sizeof(*im));
    struct squashfs_mount_opts opts={.errors=Opt_errors_continue};
    struct fs_context fc={.fs_private=&opts}; int ret;
    if (!im) return NULL;
    im->offset=offset; im->fd=sq_posix_open(path,offset,&im->bytes);
    if (im->fd<0) { free(im); return NULL; }
    im->sb.s_flags=SB_RDONLY;
    ret=squashfs_fill_super(&im->sb,&fc);
    if (ret) { u_print("squashfs open failed: %d\n",ret); sq_close_image(im); return NULL; }
    return im;
}
struct inode *sq_root_inode(struct sq_image *im) { return im->sb.s_root->d_inode; }
static void name_unqueue(struct sq_image *im,struct cached_name *e)
{
    if (e->older) e->older->newer=e->newer; else im->name_oldest=e->newer;
    if (e->newer) e->newer->older=e->older; else im->name_newest=e->older;
}
static void name_touch(struct sq_image *im,struct cached_name *e)
{
    e->newer=NULL;e->older=im->name_newest;
    if (e->older) e->older->newer=e; else im->name_oldest=e;
    im->name_newest=e;
}
static void name_evict(struct sq_image *im)
{
    struct cached_name *e=im->name_oldest,**p=&im->names[e->slot];
    while (*p!=e) p=&(*p)->next;
    *p=e->next;name_unqueue(im,e);free(e);im->name_count--;im->name_evictions++;
}
struct inode *sq_lookup_child(struct inode *parent,const char *name,unsigned int n)
{
    struct sq_image *im=image_of(parent->i_sb); unsigned int j,hash=parent->i_ino;
    struct cached_name *e; struct inode *i; struct dentry *r;
    struct dentry d={.d_name={.name=name,.len=n}};
    SQ_COUNT(lookup_calls,1);
    if (!S_ISDIR(parent->i_mode)) return NULL;
    sq_inode_pin(parent);
    for (j=0;j<n;j++) hash=(hash^(unsigned char)name[j])*16777619U;
    hash&=ARRAY_SIZE(im->names)-1;
    for (e=im->names[hash];e;e=e->next)
        if (e->parent==parent->i_ino && e->length==n && !memcmp(e->name,name,n)) {
            SQ_COUNT(name_hits,1);name_unqueue(im,e);name_touch(im,e);
            i=u_iget(parent->i_sb,e->location,e->number);
            inode_unpin(parent);return IS_ERR(i) ? NULL : i;
        }
    r=squashfs_lookup(parent,&d,0);
    if (IS_ERR(r)) { inode_unpin(parent);return NULL; }
    i=r ? r->d_inode : d.d_inode;
    if (i && (e=malloc(sizeof(*e)+n))) {
        if (im->name_count>=SQ_NAME_BUDGET) name_evict(im);
        e->parent=parent->i_ino;e->number=i->i_ino;e->location=cached(i)->location;
        e->length=n;e->slot=hash;memcpy(e->name,name,n);
        e->next=im->names[hash]; im->names[hash]=e;
        name_touch(im,e);im->name_count++;
        im->name_peak=max(im->name_peak,im->name_count);
    }
    inode_unpin(parent);
    return i;
}
void sq_cache_stats(struct sq_image *im,u64 values[8])
{
    values[0]=im->inode_count;values[1]=im->name_count;
    values[2]=im->inode_evictions;values[3]=im->name_evictions;
    values[4]=im->inode_peak;values[5]=im->name_peak;
    values[6]=SQ_INODE_BUDGET;values[7]=SQ_NAME_BUDGET;
}
void sq_inode_metadata(struct inode *i,struct sq_metadata *m)
{
    m->size=i->i_size; m->ino=i->i_ino; m->blocks=i->i_blocks; m->rdev=i->i_rdev;
    m->mode=i->i_mode; m->uid=i->i_uid.val; m->gid=i->i_gid.val; m->nlink=i->i_nlink;
    m->mtime_sec=i->i_mtime.tv_sec; m->mtime_nsec=i->i_mtime.tv_nsec;
}
static int u_emit(struct dir_context *ctx,const char *name,int n,loff_t pos,u64 ino,unsigned int type)
{
    struct list_context *c=container_of(ctx,struct list_context,ctx);
    if ((n==1 && name[0]=='.') || (n==2 && name[0]=='.' && name[1]=='.')) return 0;
    SQ_COUNT(list_entries,1);
    return c->emit(c->arg,name,n);
}
int sq_list_inode(struct inode *i,int (*emit)(void *,const char *,int),void *arg)
{
    SQ_COUNT(list_calls,1);
    struct file f={.f_inode=i}; struct list_context c={.ctx={.actor=u_emit},.emit=emit,.arg=arg};
    return S_ISDIR(i->i_mode) ? squashfs_readdir(&f,&c.ctx) : -ENOTDIR;
}
int sq_inode_readlink(struct inode *i,char *out,size_t n)
{
    u64 block=squashfs_i(i)->start; int offset=squashfs_i(i)->offset,ret;
    if (!S_ISLNK(i->i_mode) || i->i_size>=n) return -EINVAL;
    ret=squashfs_read_metadata(i->i_sb,out,&block,&offset,i->i_size);
    if (ret<0) return ret;
    out[i->i_size]=0; return 0;
}
ssize_t sq_read_inode_data(struct inode *i,void *out,size_t n,u64 offset)
{
    SQ_COUNT(read_calls,1);
    struct squashfs_sb_info *s=i->i_sb->s_fs_info; size_t done=0;
    if (!S_ISREG(i->i_mode)) return -EINVAL;
    if (offset>=i->i_size) return 0;
    n=min_t(u64,n,i->i_size-offset);
    while (done<n) {
        u64 position=offset+done,block=0;
        int index=position>>s->block_log,skip=position&(s->block_size-1),length,ret;
        size_t take=min_t(size_t,n-done,s->block_size-skip);
        struct squashfs_cache_entry *e;
        if (index<(i->i_size>>s->block_log) || squashfs_i(i)->fragment_block==SQUASHFS_INVALID_BLK) {
            length=read_blocklist(i,index,&block); if (length<0) return length;
            if (!length) { memset((char *)out+done,0,take); done+=take; continue; }
            e=squashfs_get_datablock(i->i_sb,block,length);
        } else {
            e=squashfs_get_fragment(i->i_sb,squashfs_i(i)->fragment_block,squashfs_i(i)->fragment_size);
            skip+=squashfs_i(i)->fragment_offset;
        }
        ret=e->error ?: squashfs_copy_data((char *)out+done,e,skip,take);
        u_cache_put(e); if (ret<0) return ret; if (ret!=take) return -EIO;
        done+=take;
    }
    SQ_COUNT(read_bytes,done); return done;
}
int sq_inode_getxattr(struct inode *i,const char *name,void *buffer,size_t size)
{
    int prefix,skip;
    if (!strncmp(name,"user.",5)) { prefix=SQUASHFS_XATTR_USER; skip=5; }
    else if (!strncmp(name,"security.",9)) { prefix=SQUASHFS_XATTR_SECURITY; skip=9; }
    else return -EOPNOTSUPP;
    return squashfs_xattr_get(i,prefix,name+skip,buffer,size);
}
ssize_t sq_inode_listxattr(struct inode *i,char *buffer,size_t size)
{ struct dentry d={.d_inode=i}; return squashfs_listxattr(&d,buffer,size); }
void sq_image_statfs(struct sq_image *im,u64 values[3])
{ struct squashfs_sb_info *s=im->sb.s_fs_info; values[0]=s->bytes_used; values[1]=s->inodes; values[2]=s->block_size; }
#ifdef VKSO_SQ_PROFILE
void sq_profile_report(void)
{
    u_print("SQ_PROFILE {\"raw_calls\":%llu,\"raw_bytes\":%llu,\"cache_gets\":%llu,\"cache_hits\":%llu,\"cache_misses\":%llu,\"codec_calls\":%llu,\"codec_input_bytes\":%llu,\"codec_output_bytes\":%llu,\"codec_ns\":%llu,\"scatter_calls\":%llu,\"scatter_bytes\":%llu,\"scatter_ns\":%llu,\"list_calls\":%llu,\"list_entries\":%llu,\"lookup_calls\":%llu,\"name_hits\":%llu,\"new_inodes\":%llu,\"read_calls\":%llu,\"read_bytes\":%llu}\n",
        sq_work.raw_calls,sq_work.raw_bytes,sq_work.cache_gets,sq_work.cache_hits,sq_work.cache_misses,
        sq_work.codec_calls,sq_work.codec_input_bytes,sq_work.codec_output_bytes,sq_work.codec_ns,
        sq_work.scatter_calls,sq_work.scatter_bytes,sq_work.scatter_ns,sq_work.list_calls,sq_work.list_entries,
        sq_work.lookup_calls,sq_work.name_hits,sq_work.new_inodes,sq_work.read_calls,sq_work.read_bytes);
}
#endif
