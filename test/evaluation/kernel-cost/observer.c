// SPDX-License-Identifier: GPL-2.0
#include <linux/module.h>
#include <linux/debugfs.h>
#include <linux/fs.h>
#include <linux/slab.h>
#include <linux/mm.h>
#include <linux/vmalloc.h>
#include <linux/mutex.h>
#include <linux/ktime.h>
#include <linux/uaccess.h>
#include <linux/sched.h>
#include <linux/seq_file.h>
#include <linux/lz4.h>
#include <linux/xz.h>

#ifdef OBSERVE_LZ4
extern typeof(LZ4_compress_default) vkso_LZ4_compress_default, matched_LZ4_compress_default;
extern typeof(LZ4_decompress_safe) vkso_LZ4_decompress_safe, matched_LZ4_decompress_safe;
struct backend { const char *name; typeof(&LZ4_compress_default) compress; typeof(&LZ4_decompress_safe) decode; };
static struct backend backends[] = {
    {"stock-kernel",LZ4_compress_default,LZ4_decompress_safe},
    {"matched-build-kernel",matched_LZ4_compress_default,matched_LZ4_decompress_safe},
    {"owner-kernel",vkso_LZ4_compress_default,vkso_LZ4_decompress_safe},
};
#else
extern typeof(xz_dec_init) vkso_xz_dec_init, matched_xz_dec_init;
extern typeof(xz_dec_run) vkso_xz_dec_run, matched_xz_dec_run;
extern typeof(xz_dec_reset) vkso_xz_dec_reset, matched_xz_dec_reset;
extern typeof(xz_dec_end) vkso_xz_dec_end, matched_xz_dec_end;
extern void vkso_xz_crc32_init(void);
#ifndef XZ_STOCK_SOURCE_MATCHED
extern void matched_xz_crc32_init(void);
#endif
struct backend { const char *name; typeof(&xz_dec_init) init; typeof(&xz_dec_run) run;
    typeof(&xz_dec_reset) reset; typeof(&xz_dec_end) end; void (*crc_init)(void); };
static struct backend backends[] = {
    {"stock-kernel",xz_dec_init,xz_dec_run,xz_dec_reset,xz_dec_end,NULL},
#ifdef XZ_STOCK_SOURCE_MATCHED
    {"matched-build-kernel",matched_xz_dec_init,matched_xz_dec_run,matched_xz_dec_reset,matched_xz_dec_end,NULL},
#else
    {"matched-direct-kernel",matched_xz_dec_init,matched_xz_dec_run,matched_xz_dec_reset,matched_xz_dec_end,matched_xz_crc32_init},
#endif
    {"owner-kernel",vkso_xz_dec_init,vkso_xz_dec_run,vkso_xz_dec_reset,vkso_xz_dec_end,vkso_xz_crc32_init},
};
#endif

static DEFINE_MUTEX(lock);
static struct dentry *directory;
static unsigned char *plain,*encoded,*stock,*allocation,*output,*cross;
static size_t plain_size,encoded_size,stock_size;
static char result[2048],label[96];
static int last_error;
#ifdef OBSERVE_LZ4
struct block { size_t input,offset; int bytes,capacity,stock_length,length; };
static struct block *blocks;
static unsigned int block_count,block_size;
static void *workmem;
#endif

static void clear_input(void)
{
    kvfree(plain);kvfree(encoded);kvfree(stock);kvfree(allocation);kvfree(cross);
    plain=encoded=stock=allocation=output=cross=NULL;
    plain_size=encoded_size=stock_size=0;
#ifdef OBSERVE_LZ4
    kvfree(blocks);kvfree(workmem);blocks=NULL;workmem=NULL;block_count=0;
#endif
}

static int load_file(const char *path,unsigned char **data,size_t *size)
{
    struct file *file=filp_open(path,O_RDONLY,0);
    loff_t position=0,length;ssize_t got;size_t done=0;
    if (IS_ERR(file)) return PTR_ERR(file);
    length=i_size_read(file_inode(file));
    if (length<=0 || length>64*1024*1024) {filp_close(file,NULL);return -EINVAL;}
    *data=kvmalloc(length,GFP_KERNEL);
    if (!*data) {filp_close(file,NULL);return -ENOMEM;}
    while (done<length) {
        got=kernel_read(file,*data+done,length-done,&position);
        if (got<=0) {filp_close(file,NULL);return got ? got : -EIO;}
        done+=got;
    }
    filp_close(file,NULL);*size=length;return 0;
}

static bool guard_ok(const unsigned char *p)
{
    size_t i;for(i=0;i<64;i++) if(p[i]!=0xa5)return false;return true;
}

static int prepare(const char *path,const char *compressed,unsigned int block)
{
    int error;
    clear_input();error=load_file(path,&plain,&plain_size);if(error)return error;
    allocation=kvmalloc(plain_size+128,GFP_KERNEL);cross=kvmalloc(plain_size,GFP_KERNEL);
    if(!allocation || !cross)return -ENOMEM;
    memset(allocation,0xa5,plain_size+128);output=allocation+64;
#ifdef OBSERVE_LZ4
    {
        unsigned int i;size_t total=0;
        if(block!=65536 && block!=1048576)return -EINVAL;
        block_size=block;block_count=DIV_ROUND_UP(plain_size,block);
        blocks=kvcalloc(block_count,sizeof(*blocks),GFP_KERNEL);
        workmem=kvmalloc(LZ4_MEM_COMPRESS,GFP_KERNEL);
        if(!blocks || !workmem)return -ENOMEM;
        for(i=0;i<block_count;i++) {
            struct block *b=&blocks[i];b->input=(size_t)i*block;
            b->bytes=min_t(size_t,block,plain_size-b->input);
            b->capacity=LZ4_COMPRESSBOUND(b->bytes);b->offset=total+64;
            total+=b->capacity+128;
        }
        encoded_size=stock_size=total;
        encoded=kvmalloc(total,GFP_KERNEL);stock=kvmalloc(total,GFP_KERNEL);
        if(!encoded || !stock)return -ENOMEM;
        memset(encoded,0xa5,total);memset(stock,0xa5,total);
        for(i=0;i<block_count;i++) {
            struct block *b=&blocks[i];
            b->stock_length=LZ4_compress_default(plain+b->input,stock+b->offset,b->bytes,b->capacity,workmem);
            if(b->stock_length<=0 || b->stock_length>b->capacity)return -EILSEQ;
        }
    }
#else
    if(block)return -EINVAL;
    error=load_file(compressed,&stock,&stock_size);if(error)return error;
#endif
    return 0;
}

#ifdef OBSERVE_LZ4
static int full_pass(struct backend *backend,bool compress)
{
    unsigned int i;int length;
    for(i=0;i<block_count;i++) {
        struct block *b=&blocks[i];
        if(compress) {
            length=backend->compress(plain+b->input,encoded+b->offset,b->bytes,b->capacity,workmem);
            if(length<=0 || length>b->capacity)return -EILSEQ;
            b->length=length;
        } else {
            length=backend->decode(stock+b->offset,output+b->input,b->stock_length,b->bytes);
            if(length!=b->bytes)return -EILSEQ;
        }
    }
    return 0;
}

static int validate_pass(bool compress)
{
    unsigned int i;
    if(compress) {
        for(i=0;i<block_count;i++) {
            struct block *b=&blocks[i];
            if(!guard_ok(encoded+b->offset-64) || !guard_ok(encoded+b->offset+b->capacity))return -EILSEQ;
            if(LZ4_decompress_safe(encoded+b->offset,cross+b->input,b->length,b->bytes)!=b->bytes)return -EILSEQ;
        }
        if(memcmp(cross,plain,plain_size))return -EILSEQ;
    } else if(memcmp(output,plain,plain_size) || !guard_ok(allocation) || !guard_ok(output+plain_size))return -EILSEQ;
    return 0;
}
#else
static int decode_pass(struct backend *backend,struct xz_dec *decoder)
{
    struct xz_buf b={.in=stock,.in_size=stock_size,.out=output,.out_size=plain_size};
    enum xz_ret ret;
    backend->reset(decoder);ret=backend->run(decoder,&b);
    return ret==XZ_STREAM_END && b.in_pos==stock_size && b.out_pos==plain_size ? 0 : -EILSEQ;
}
#endif

static int measure(unsigned int index,unsigned int outer,unsigned int milliseconds)
{
    struct backend *backend;u64 start,elapsed;unsigned int repeats;int error,cpu;
    if(!plain || index>=ARRAY_SIZE(backends) || outer>=100 || !milliseconds || milliseconds>1000)return -EINVAL;
    backend=&backends[index];cpu=raw_smp_processor_id();result[0]=0;
    memset(allocation,0xa5,plain_size+128);memset(cross,0xa5,plain_size);
#ifdef OBSERVE_LZ4
    memset(encoded,0xa5,encoded_size);
#endif
#ifdef OBSERVE_LZ4
    {
        int operation;size_t used=0;
        for(operation=0;operation<2;operation++) {
            bool compress=operation==0;unsigned int i;size_t bytes=0;
            error=full_pass(backend,compress);if(error)return error;
            error=validate_pass(compress);if(error)return error;
            repeats=0;start=ktime_get_raw_ns();
            do {
                error=full_pass(backend,compress);if(error)return error;
                repeats++;elapsed=ktime_get_raw_ns()-start;
                if(elapsed<(u64)milliseconds*1000000)cond_resched();
            } while(elapsed<(u64)milliseconds*1000000);
            error=validate_pass(compress);if(error)return error;
            for(i=0;i<block_count;i++)bytes+=compress?blocks[i].length:blocks[i].stock_length;
            used+=scnprintf(result+used,sizeof(result)-used,
                "%s,%s,%u,%s,%u,%zu,%zu,%u,%llu,%d,%u,pass\n",backend->name,label,outer,
                compress?"compress":"decompress",block_size,plain_size,bytes,repeats,elapsed,cpu,block_count);
        }
    }
#else
    {
        struct xz_dec *decoder;
        if(backend->crc_init)backend->crc_init();
        decoder=backend->init(XZ_SINGLE,0);if(!decoder)return -ENOMEM;
        error=decode_pass(backend,decoder);
        if(error || memcmp(output,plain,plain_size)){backend->end(decoder);return -EILSEQ;}
        repeats=0;start=ktime_get_raw_ns();
        do {
            error=decode_pass(backend,decoder);if(error)break;
            repeats++;elapsed=ktime_get_raw_ns()-start;
            if(elapsed<(u64)milliseconds*1000000)cond_resched();
        } while(elapsed<(u64)milliseconds*1000000);
        backend->end(decoder);if(error)return error;
        if(memcmp(output,plain,plain_size) || !guard_ok(allocation) || !guard_ok(output+plain_size))return -EILSEQ;
        scnprintf(result,sizeof(result),"%s,%s,%u,decompress,0,%zu,%zu,%u,%llu,%d,1,pass\n",
                  backend->name,label,outer,plain_size,stock_size,repeats,elapsed,cpu);
    }
#endif
    return 0;
}

static ssize_t command_write(struct file *f,const char __user *buffer,size_t size,loff_t *position)
{
    char *command,path[384],compressed[384],name[96];unsigned int a,b,c;int error;
    if(size>=1024)return -E2BIG;
    command=memdup_user_nul(buffer,size);
    if(IS_ERR(command))return PTR_ERR(command);
    mutex_lock(&lock);
    if(sscanf(command,"LOAD %95s %383s %383s %u",name,path,compressed,&a)==4) {
        strscpy(label,name,sizeof(label));error=prepare(path,compressed,a);result[0]=0;
    } else if(sscanf(command,"RUN %u %u %u",&a,&b,&c)==3)error=measure(a,b,c);
    else error=-EINVAL;
    last_error=error;mutex_unlock(&lock);kfree(command);return error?error:size;
}
static const struct file_operations control_ops={.owner=THIS_MODULE,.write=command_write,.llseek=no_llseek};

static int results_show(struct seq_file *s,void *unused)
{
    mutex_lock(&lock);
    seq_puts(s,"backend,case,outer_run,operation,block_bytes,bytes,compressed_bytes,repeats,elapsed_ns,cpu,blocks,status\n");
    if(!last_error)seq_puts(s,result);
    mutex_unlock(&lock);return 0;
}
DEFINE_SHOW_ATTRIBUTE(results);
static int status_show(struct seq_file *s,void *unused)
{
    unsigned int i;seq_printf(s,"errno=%d\ninput_bytes=%zu\n",last_error,plain_size);
    for(i=0;i<ARRAY_SIZE(backends);i++) {
#ifdef OBSERVE_LZ4
        seq_printf(s,"%s compress=%px decode=%px\n",backends[i].name,backends[i].compress,backends[i].decode);
#else
        seq_printf(s,"%s init=%px run=%px reset=%px end=%px crc_init=%px\n",backends[i].name,
            backends[i].init,backends[i].run,backends[i].reset,backends[i].end,backends[i].crc_init);
#endif
    }
    return 0;
}
DEFINE_SHOW_ATTRIBUTE(status);
static ssize_t output_read(struct file *f,char __user *buffer,size_t size,loff_t *position)
{
    ssize_t ret;mutex_lock(&lock);ret=simple_read_from_buffer(buffer,size,position,output,plain_size);mutex_unlock(&lock);return ret;
}
static const struct file_operations output_ops={.owner=THIS_MODULE,.read=output_read,.llseek=default_llseek};
#ifdef OBSERVE_LZ4
static ssize_t encoded_read(struct file *f,char __user *buffer,size_t size,loff_t *position)
{
    ssize_t ret;mutex_lock(&lock);ret=simple_read_from_buffer(buffer,size,position,encoded,encoded_size);mutex_unlock(&lock);return ret;
}
static const struct file_operations encoded_ops={.owner=THIS_MODULE,.read=encoded_read,.llseek=default_llseek};
static int blocks_show(struct seq_file *s,void *unused)
{
    unsigned int i;mutex_lock(&lock);seq_puts(s,"input_offset,encoded_offset,input_bytes,encoded_bytes,capacity\n");
    for(i=0;i<block_count;i++)seq_printf(s,"%zu,%zu,%d,%d,%d\n",blocks[i].input,blocks[i].offset,blocks[i].bytes,blocks[i].length,blocks[i].capacity);
    mutex_unlock(&lock);return 0;
}
DEFINE_SHOW_ATTRIBUTE(blocks);
#endif
static int __init observer_init(void)
{
    directory=debugfs_create_dir("vkso_kernel_cost",NULL);if(IS_ERR(directory))return PTR_ERR(directory);
    debugfs_create_file("control",0200,directory,NULL,&control_ops);
    debugfs_create_file("results",0400,directory,NULL,&results_fops);
    debugfs_create_file("status",0400,directory,NULL,&status_fops);
    debugfs_create_file("output",0400,directory,NULL,&output_ops);
#ifdef OBSERVE_LZ4
    debugfs_create_file("encoded",0400,directory,NULL,&encoded_ops);
    debugfs_create_file("blocks",0400,directory,NULL,&blocks_fops);
#endif
    return 0;
}
static void __exit observer_exit(void){debugfs_remove_recursive(directory);clear_input();}
module_init(observer_init);module_exit(observer_exit);MODULE_LICENSE("GPL");
