// SPDX-License-Identifier: GPL-2.0-only
/* Read-only FUSE frontend. All image parsing remains in the Linux SquashFS core.
 * The existing image adapter owns one handle, so this daemon is single-threaded.
 */
#define FUSE_USE_VERSION 31
#define _FILE_OFFSET_BITS 64
#include <fuse.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysmacros.h>

/* Matches the explicitly exposed adapter ABI; kernel objects remain opaque. */
struct sq_metadata {
    uint64_t size, ino, blocks, rdev;
    int64_t mtime_sec, mtime_nsec;
    uint32_t mode, uid, gid, nlink;
};
static struct {
    void *(*open_image)(const char *, uint64_t);
    void (*close_image)(void *);
    void *(*root_inode)(void *);
    void *(*lookup_child)(void *, const char *, unsigned int);
    void (*inode_metadata)(void *, struct sq_metadata *);
    int (*list_inode)(void *, int (*)(void *, const char *, int), void *);
    int (*inode_readlink)(void *, char *, size_t);
    ssize_t (*read_inode_data)(void *, void *, size_t, uint64_t);
    int (*inode_getxattr)(void *, const char *, void *, size_t);
    ssize_t (*inode_listxattr)(void *, char *, size_t);
    void (*image_statfs)(void *, uint64_t *);
} api;
static void *image_handle;
struct names { char **items; size_t n, cap; };
#ifdef VKSO_SQ_DIRECTORY_CACHE
struct directory_handle { void *inode; struct names names; int ready; };
/* fh is an opaque integer. Its low bit distinguishes an aligned directory
 * allocation from the existing image-owned inode handle used by files. */
static void *handle_inode(const struct fuse_file_info *fi)
{
    uintptr_t value=fi->fh;
    return value&1 ? ((struct directory_handle *)(value&~(uintptr_t)1))->inode : (void *)value;
}
#else
static void *handle_inode(const struct fuse_file_info *fi) { return (void *)(uintptr_t)fi->fh; }
#endif
#ifdef VKSO_SQ_PROFILE
static unsigned long long readdir_calls, listed_entries, returned_entries;
static unsigned long long directory_opens, getattr_calls, read_calls, read_bytes;
#endif
void *debug_entry;
__attribute__((noinline)) void debug_ready(void) { __asm__ volatile("" ::: "memory"); }

static void *lookup(const char *path)
{
    void *inode = api.root_inode(image_handle);
    while (*path) {
        const char *end;
        while (*path == '/') path++;
        if (!*path) break;
        end = strchr(path, '/');
        size_t n = end ? (size_t)(end - path) : strlen(path);
        inode = api.lookup_child(inode, path, n);
        if (!inode) return NULL;
        path += n;
    }
    return inode;
}
static int sq_getattr(const char *path, struct stat *st, struct fuse_file_info *fi)
{
#ifdef VKSO_SQ_PROFILE
    getattr_calls++;
#endif
    void *inode = fi && fi->fh ? handle_inode(fi) : lookup(path);
    struct sq_metadata m;
    if (!inode) return -ENOENT;
    api.inode_metadata(inode, &m);
    memset(st, 0, sizeof(*st));
    st->st_mode=m.mode; st->st_uid=m.uid; st->st_gid=m.gid;
    st->st_nlink=m.nlink; st->st_size=m.size; st->st_ino=m.ino;
    st->st_mtim.tv_sec=m.mtime_sec; st->st_mtim.tv_nsec=m.mtime_nsec;
    st->st_atim=st->st_ctim=st->st_mtim;
    st->st_blksize=4096; st->st_blocks=m.blocks;
    st->st_rdev=makedev(m.rdev>>20,m.rdev&((1U<<20)-1));
    return 0;
}
static int collect_name(void *arg, const char *name, int length)
{
    struct names *names=arg;
    if (names->n == names->cap) {
        size_t cap = names->cap ? names->cap * 2 : 32;
        char **items = realloc(names->items, cap * sizeof(*items));
        if (!items) return -ENOMEM;
        names->items=items; names->cap=cap;
    }
    char *copy = strndup(name, length);
    if (!copy) return -ENOMEM;
    names->items[names->n++]=copy;
#ifdef VKSO_SQ_PROFILE
    listed_entries++;
#endif
    return 0;
}
static void free_names(struct names *names)
{
    for (size_t i=0;i<names->n;i++) free(names->items[i]);
    free(names->items);memset(names,0,sizeof(*names));
}
static int sq_readdir(const char *path, void *buf, fuse_fill_dir_t fill,
                       off_t offset, struct fuse_file_info *fi,
                       enum fuse_readdir_flags flags)
{
    (void)flags;
    void *inode=fi && fi->fh ? handle_inode(fi) : lookup(path);
    struct names temporary={0},*names=&temporary;
    int ret=0,build_list=1;
#ifdef VKSO_SQ_DIRECTORY_CACHE
    struct directory_handle *handle=fi && (fi->fh&1) ?
        (void *)((uintptr_t)fi->fh&~(uintptr_t)1) : NULL;
    if (handle) { names=&handle->names;build_list=!handle->ready; }
#endif
    if (!inode) return -ENOENT;
    if (offset < 0) return -EINVAL;
#ifdef VKSO_SQ_PROFILE
    readdir_calls++;
    unsigned long long returned_before=returned_entries;
#endif
    if (build_list) {
        ret=collect_name(names,".",1);
        if (!ret) ret=collect_name(names,"..",2);
        if (!ret) ret=api.list_inode(inode,collect_name,names);
#ifdef VKSO_SQ_DIRECTORY_CACHE
        if (handle && !ret) handle->ready=1;
#endif
    }
    if (!ret) {
        for (size_t i=offset; i<names->n; i++) {
            if (fill(buf,names->items[i],NULL,i+1,0)) break;
#ifdef VKSO_SQ_PROFILE
            returned_entries++;
#endif
        }
    }
#ifdef VKSO_SQ_PROFILE
    fprintf(stderr,"SQ_READDIR {\"inode\":\"%p\",\"offset\":%lld,\"listed\":%zu,\"returned\":%llu}\n",
            inode,(long long)offset,build_list ? names->n : 0,returned_entries-returned_before);
#endif
    if (ret || names==&temporary) free_names(names);
    return ret;
}
static int sq_open(const char *path, struct fuse_file_info *fi)
{
    struct sq_metadata m;
    void *inode;
    if ((fi->flags & O_ACCMODE) != O_RDONLY) return -EROFS;
    inode=lookup(path);
    if (!inode) return -ENOENT;
    api.inode_metadata(inode,&m);
    if (!S_ISREG(m.mode)) return -EISDIR;
    fi->fh=(uintptr_t)inode;
    return 0;
}
static int sq_opendir(const char *path, struct fuse_file_info *fi)
{
#ifdef VKSO_SQ_PROFILE
    directory_opens++;
#endif
    struct sq_metadata m;
    void *inode=lookup(path);
    if (!inode) return -ENOENT;
    api.inode_metadata(inode,&m);
    if (!S_ISDIR(m.mode)) return -ENOTDIR;
#ifdef VKSO_SQ_DIRECTORY_CACHE
    struct directory_handle *handle=calloc(1,sizeof(*handle));
    if (!handle) return -ENOMEM;
    handle->inode=inode;fi->fh=(uintptr_t)handle|1;
#else
    fi->fh=(uintptr_t)inode;
#endif
    return 0;
}
#ifdef VKSO_SQ_DIRECTORY_CACHE
static int sq_releasedir(const char *path, struct fuse_file_info *fi)
{
    (void)path;
    struct directory_handle *handle=(void *)((uintptr_t)fi->fh&~(uintptr_t)1);
    if (handle) { free_names(&handle->names);free(handle);fi->fh=0; }
    return 0;
}
#endif
static int sq_read(const char *path, char *buf, size_t size, off_t offset,
                    struct fuse_file_info *fi)
{
#ifdef VKSO_SQ_PROFILE
    read_calls++; read_bytes+=size;
#endif
    void *inode=fi && fi->fh ? handle_inode(fi) : lookup(path);
    if (!inode) return -ENOENT;
    if (offset < 0) return -EINVAL;
    return api.read_inode_data(inode,buf,size,offset);
}
static int sq_readlink(const char *path, char *buf, size_t size)
{
    void *inode=lookup(path);
    char link[4096];
    int ret;
    if (!inode) return -ENOENT;
    ret=api.inode_readlink(inode,link,sizeof(link));
    if (ret) return ret;
    if (size) snprintf(buf,size,"%s",link);
    return 0;
}
static void *sq_init(struct fuse_conn_info *conn, struct fuse_config *config)
{
    (void)conn;
    /* Open files/directories retain image-owned inodes until unmount. */
    config->nullpath_ok=1;
    config->use_ino=1;
    return NULL;
}
static int sq_getxattr(const char *path, const char *name, char *buf, size_t size)
{
    void *inode=lookup(path);
    return inode ? api.inode_getxattr(inode,name,size ? buf : NULL,size) : -ENOENT;
}
static int sq_listxattr(const char *path, char *buf, size_t size)
{
    void *inode=lookup(path);
    return inode ? api.inode_listxattr(inode,size ? buf : NULL,size) : -ENOENT;
}
static int sq_statfs(const char *path, struct statvfs *st)
{
    uint64_t v[3]; (void)path;
    api.image_statfs(image_handle,v); memset(st,0,sizeof(*st));
    st->f_bsize=st->f_frsize=v[2]; st->f_blocks=(v[0]+v[2]-1)/v[2];
    st->f_files=v[1]; st->f_namemax=256;
    return 0;
}
static const struct fuse_operations ops = {
    .init=sq_init, .getattr=sq_getattr, .readdir=sq_readdir, .open=sq_open,
    .opendir=sq_opendir,
#ifdef VKSO_SQ_DIRECTORY_CACHE
    .releasedir=sq_releasedir,
#endif
    .read=sq_read, .readlink=sq_readlink,
    .getxattr=sq_getxattr, .listxattr=sq_listxattr, .statfs=sq_statfs,
};
int main(int argc, char **argv)
{
    if (argc != 6 && argc != 7) {
        fprintf(stderr,"usage: %s CORE|- BRIDGE IMAGE OFFSET MOUNT|--probe [FUSE_OPTIONS]\n",argv[0]);
        return 2;
    }
    void *core=NULL, *bridge;
    if (strcmp(argv[1],"-")) {
        core=dlopen(argv[1],RTLD_NOW|RTLD_GLOBAL);
        if (!core) { fprintf(stderr,"core: %s\n",dlerror()); return 1; }
    }
    bridge=dlopen(argv[2],RTLD_NOW|RTLD_GLOBAL);
    if (!bridge) { fprintf(stderr,"bridge: %s\n",dlerror()); return 1; }
#define LOAD(name) do { api.name=dlsym(bridge,"sq_" #name); \
    if (!api.name) { fprintf(stderr,"symbol: %s\n",dlerror()); return 1; } } while(0)
    LOAD(open_image); LOAD(close_image); LOAD(root_inode); LOAD(lookup_child);
    LOAD(inode_metadata); LOAD(list_inode); LOAD(inode_readlink); LOAD(read_inode_data);
    LOAD(inode_getxattr); LOAD(inode_listxattr); LOAD(image_statfs);
    debug_entry=dlsym(core ? core : bridge,"read_blocklist");
    image_handle=api.open_image(argv[3],strtoull(argv[4],NULL,0));
    if (!image_handle) { fprintf(stderr,"image open failed\n"); return 1; }
    if (getenv("VKSO_SQ_STATE")) {
        void *(*address)(void)=dlsym(core ? core : bridge,"sq_support_address");
        if (!address) return 1;
        fprintf(stderr,"sq_private_bindings=%p\n",address());
        fflush(stderr);
    }
    debug_ready();
    int ret;
    if (!strcmp(argv[5],"--probe")) {
        struct stat st;
        ret=sq_getattr("/",&st,NULL);
        printf("probe_root_mode=%o size=%ld\n",st.st_mode,(long)st.st_size);
    } else {
        char *args[]={argv[0],argv[5],"-f","-s","-o","ro,fsname=vkso-squashfs",
                      argc==7 ? "-o" : NULL,argc==7 ? argv[6] : NULL,NULL};
        ret=fuse_main(argc==7 ? 8 : 6,args,&ops,NULL);
    }
#ifdef VKSO_SQ_PROFILE
    void (*report)(void)=dlsym(bridge,"sq_profile_report");
    if (!report) { fprintf(stderr,"missing diagnostic bridge counters\n"); return 1; }
    report();
    fprintf(stderr,"SQ_FRONTEND {\"readdir_calls\":%llu,\"listed_entries\":%llu,\"returned_entries\":%llu,\"directory_opens\":%llu,\"getattr_calls\":%llu,\"read_calls\":%llu,\"requested_read_bytes\":%llu}\n",
            readdir_calls,listed_entries,returned_entries,directory_opens,getattr_calls,read_calls,read_bytes);
#endif
    api.close_image(image_handle);
    dlclose(bridge);
    if (core) dlclose(core);
    return ret ? 1 : 0;
}
