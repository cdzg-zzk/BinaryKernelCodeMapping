/* Diagnostic only: read the libfuse 3.10.5 x86-64 private ABI, never mutate it.
 * Layout facts checked against the matching upstream lib/fuse.c tag:
 * https://github.com/libfuse/libfuse/blob/fuse-3.10.5/lib/fuse.c
 * Not installed in the production frontend; assertions reject ABI mismatch.
 */
#include <assert.h>
#include <stddef.h>
#include <pthread.h>
#include <malloc.h>
struct probe_table { void *buckets; size_t count, capacity, split; };
struct probe_link { struct probe_link *next,*previous; };
struct probe_fuse {
    void *session;
    struct probe_table names,identities;
    struct probe_link retention;
    uint64_t serial;
    unsigned generation,hidden;
    pthread_mutex_t mutex;
    struct fuse_config configuration;
    int signal_installed;
    void *filesystem,*waiters;
    int page_bytes;
    struct probe_link partial,full;
};
struct probe_slab {
    struct probe_link link,available;
    int occupied;
};
static void probe_slabs(const void *address, size_t *pages,size_t *occupied)
{
    const struct probe_link *head=address;
    struct probe_link link;
    memcpy(&link,head,sizeof(link));
    const struct probe_link *cursor=link.next;
    while(cursor!=head) {
        struct probe_slab slab;memcpy(&slab,cursor,sizeof(slab));
        assert(slab.occupied>0 && slab.occupied<64);
        *occupied+=(size_t)slab.occupied;(*pages)++;
        assert(*pages<1000000);
        cursor=slab.link.next;
    }
}
static void probe_memory(void)
{
    struct fuse_context *context=fuse_get_context();assert(context && context->fuse);
    struct probe_fuse value;memcpy(&value,context->fuse,sizeof(value));
    assert(fuse_version()==310 && value.page_bytes==4096);
    assert(value.configuration.use_ino==1 && value.configuration.nullpath_ok==1);
    assert(value.configuration.remember==0);
    assert(value.identities.count==value.names.count+1);
    assert(value.identities.count>0 && value.identities.count<1000000);
    assert(value.names.capacity>=8192 && value.names.capacity<4000000);
    assert(value.identities.capacity>=8192 && value.identities.capacity<4000000);
    size_t pages=0,occupied=0;
    probe_slabs((char*)context->fuse+offsetof(struct probe_fuse,partial),&pages,&occupied);
    probe_slabs((char*)context->fuse+offsetof(struct probe_fuse,full),&pages,&occupied);
    assert(occupied==value.identities.count);
    uint64_t counters[8]={0};
    void (*stats)(void*,uint64_t*)=dlsym(RTLD_DEFAULT,"sq_cache_stats");assert(stats);
    stats(image_handle,counters);
    struct mallinfo2 allocator=mallinfo2();
    fprintf(stderr,"FUSE_MEMORY {\"nodes\":%zu,\"names\":%zu,\"node_slab_pages\":%zu,\"node_slab_mapped_bytes\":%zu,\"name_buckets\":%zu,\"id_buckets\":%zu,\"hash_requested_bytes\":%zu,\"malloc_arena_used_bytes\":%zu,\"malloc_arena_free_bytes\":%zu,\"malloc_mmap_bytes\":%zu,\"bridge_inodes\":%llu,\"bridge_names\":%llu,\"inode_evictions\":%llu,\"name_evictions\":%llu}\n",
        value.identities.count,value.names.count,pages,pages*4096,
        value.names.capacity,value.identities.capacity,
        (value.names.capacity+value.identities.capacity)*sizeof(void*),
        allocator.uordblks,allocator.fordblks,allocator.hblkhd,
        (unsigned long long)counters[0],(unsigned long long)counters[1],
        (unsigned long long)counters[2],(unsigned long long)counters[3]);
    fflush(stderr);
}
