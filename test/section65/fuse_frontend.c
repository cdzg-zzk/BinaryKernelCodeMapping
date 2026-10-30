// SPDX-License-Identifier: GPL-2.0-only
/* Read-only FUSE frontend. All image parsing remains in the Linux isofs core.
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

/* Matches the explicitly exposed adapter ABI; kernel objects remain opaque. */
struct iso_metadata {
    uint64_t size, ino;
    int64_t mtime_sec, mtime_nsec;
    uint32_t mode, uid, gid, nlink;
};
static struct {
    void *(*open_image)(const char *, int);
    void (*close_image)(void *);
    void *(*root_inode)(void *);
    void *(*lookup_child)(void *, const char *, unsigned int);
    void (*inode_metadata)(void *, struct iso_metadata *);
    int (*list_inode)(void *, int (*)(void *, const char *, int), void *);
    int (*inode_readlink)(void *, char *, size_t);
    ssize_t (*read_inode_data)(void *, void *, size_t, uint64_t);
} api;
static void *image_handle;
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
static int iso_getattr(const char *path, struct stat *st, struct fuse_file_info *fi)
{
    void *inode = fi && fi->fh ? (void *)(uintptr_t)fi->fh : lookup(path);
    struct iso_metadata m;
    if (!inode) return -ENOENT;
    api.inode_metadata(inode, &m);
    memset(st, 0, sizeof(*st));
    st->st_mode=m.mode; st->st_uid=m.uid; st->st_gid=m.gid;
    st->st_nlink=m.nlink; st->st_size=m.size; st->st_ino=m.ino;
    st->st_mtim.tv_sec=m.mtime_sec; st->st_mtim.tv_nsec=m.mtime_nsec;
    st->st_atim=st->st_ctim=st->st_mtim;
    st->st_blksize=2048; st->st_blocks=(m.size+511)/512;
    return 0;
}
struct names { char **items; size_t n, cap; };
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
    return 0;
}
static int iso_readdir(const char *path, void *buf, fuse_fill_dir_t fill,
                       off_t offset, struct fuse_file_info *fi,
                       enum fuse_readdir_flags flags)
{
    (void)flags;
    void *inode=fi && fi->fh ? (void *)(uintptr_t)fi->fh : lookup(path);
    struct names names={0};
    int ret;
    if (!inode) return -ENOENT;
    if (offset < 0) return -EINVAL;
    ret=collect_name(&names,".",1);
    if (!ret) ret=collect_name(&names,"..",2);
    if (!ret) ret=api.list_inode(inode,collect_name,&names);
    if (!ret) {
        for (size_t i=offset; i<names.n; i++)
            if (fill(buf,names.items[i],NULL,i+1,0)) break;
    }
    for (size_t i=0; i<names.n; i++) free(names.items[i]);
    free(names.items);
    return ret;
}
static int iso_open(const char *path, struct fuse_file_info *fi)
{
    struct iso_metadata m;
    void *inode;
    if ((fi->flags & O_ACCMODE) != O_RDONLY) return -EROFS;
    inode=lookup(path);
    if (!inode) return -ENOENT;
    api.inode_metadata(inode,&m);
    if (!S_ISREG(m.mode)) return -EISDIR;
    fi->fh=(uintptr_t)inode;
    return 0;
}
static int iso_opendir(const char *path, struct fuse_file_info *fi)
{
    struct iso_metadata m;
    void *inode=lookup(path);
    if (!inode) return -ENOENT;
    api.inode_metadata(inode,&m);
    if (!S_ISDIR(m.mode)) return -ENOTDIR;
    fi->fh=(uintptr_t)inode;
    return 0;
}
static int iso_read(const char *path, char *buf, size_t size, off_t offset,
                    struct fuse_file_info *fi)
{
    void *inode=fi && fi->fh ? (void *)(uintptr_t)fi->fh : lookup(path);
    if (!inode) return -ENOENT;
    if (offset < 0) return -EINVAL;
    return api.read_inode_data(inode,buf,size,offset);
}
static int iso_readlink(const char *path, char *buf, size_t size)
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
static void *iso_init(struct fuse_conn_info *conn, struct fuse_config *config)
{
    (void)conn;
    /* Open files/directories retain image-owned inodes until unmount. */
    config->nullpath_ok=1;
    config->use_ino=1;
    return NULL;
}
static const struct fuse_operations ops = {
    .init=iso_init, .getattr=iso_getattr, .readdir=iso_readdir, .open=iso_open,
    .opendir=iso_opendir,
    .read=iso_read, .readlink=iso_readlink,
};
int main(int argc, char **argv)
{
    if (argc != 6 && argc != 7) {
        fprintf(stderr,"usage: %s CORE|- BRIDGE IMAGE NOROCK MOUNT|--probe [FUSE_OPTIONS]\n",argv[0]);
        return 2;
    }
    void *core=NULL, *bridge;
    if (strcmp(argv[1],"-")) {
        core=dlopen(argv[1],RTLD_NOW|RTLD_GLOBAL);
        if (!core) { fprintf(stderr,"core: %s\n",dlerror()); return 1; }
    }
    bridge=dlopen(argv[2],RTLD_NOW|RTLD_GLOBAL);
    if (!bridge) { fprintf(stderr,"bridge: %s\n",dlerror()); return 1; }
#define LOAD(name) do { api.name=dlsym(bridge,"iso_" #name); \
    if (!api.name) { fprintf(stderr,"symbol: %s\n",dlerror()); return 1; } } while(0)
    LOAD(open_image); LOAD(close_image); LOAD(root_inode); LOAD(lookup_child);
    LOAD(inode_metadata); LOAD(list_inode); LOAD(inode_readlink); LOAD(read_inode_data);
    debug_entry=dlsym(core ? core : bridge,"isofs_get_blocks");
    image_handle=api.open_image(argv[3],atoi(argv[4]));
    if (!image_handle) { fprintf(stderr,"image open failed\n"); return 1; }
    debug_ready();
    int ret;
    if (!strcmp(argv[5],"--probe")) {
        struct stat st;
        ret=iso_getattr("/",&st,NULL);
        printf("probe_root_mode=%o size=%ld\n",st.st_mode,(long)st.st_size);
    } else {
        char *args[]={argv[0],argv[5],"-f","-s","-o","ro,fsname=vkso-isofs",
                      argc==7 ? "-o" : NULL,argc==7 ? argv[6] : NULL,NULL};
        ret=fuse_main(argc==7 ? 8 : 6,args,&ops,NULL);
    }
    if (getenv("VKSO_ISOFUSE_STATS")) {
        void (*stats)(void *, unsigned long *)=dlsym(bridge,"iso_lookup_stats");
        if (stats) {
            unsigned long values[3]; stats(image_handle,values);
            fprintf(stderr,"iso_lookup_stats calls=%lu hits=%lu entries=%lu\n",values[0],values[1],values[2]);
        }
    }
    api.close_image(image_handle);
    dlclose(bridge);
    if (core) dlclose(core);
    return ret ? 1 : 0;
}
