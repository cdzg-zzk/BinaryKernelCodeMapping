// SPDX-License-Identifier: GPL-2.0-only
/* Temporary native-only diagnostic probes. Never loaded for performance/PFN runs. */
#include <linux/module.h>
#include <linux/kprobes.h>
#include <linux/debugfs.h>
#include <linux/seq_file.h>
#include <linux/uaccess.h>
#include <linux/percpu.h>
#include <linux/sched.h>

#define MAX_PROBES 24
static unsigned long addresses[MAX_PROBES];
static unsigned int address_count;
module_param_array(addresses,ulong,&address_count,0400);
static int copy_index=-1;
module_param(copy_index,int,0400);
struct probe_record { struct kprobe probe; unsigned int index; };
static struct probe_record probes[MAX_PROBES];
struct cpu_counts { u64 hits[MAX_PROBES]; u64 copy_sizes[258]; u64 skipped_copy; };
static DEFINE_PER_CPU(struct cpu_counts,counts);
static struct dentry *directory;
static bool enabled;
static unsigned int registered;

static int before(struct kprobe *p,struct pt_regs *regs)
{
    struct probe_record *record=container_of(p,struct probe_record,probe);
    if (READ_ONCE(enabled) && raw_smp_processor_id()==1 && !strcmp(current->comm,"find")) {
        struct cpu_counts *c=this_cpu_ptr(&counts);
        c->hits[record->index]++;
        if (record->index==copy_index) {
            unsigned int length=(unsigned int)regs->cx;
            if (!regs->di) c->skipped_copy++;
            else c->copy_sizes[length<=256 ? length : 257]++;
        }
    }
    return 0;
}
NOKPROBE_SYMBOL(before);

static int show(struct seq_file *s,void *unused)
{
    unsigned int i;int cpu;
    for (i=0;i<address_count;i++) {
        u64 sum=0;
        for_each_possible_cpu(cpu) sum+=per_cpu(counts,cpu).hits[i];
        seq_printf(s,"%u %llu\n",i,sum);
    }
    return 0;
}
static int open_counts(struct inode *inode,struct file *file) { return single_open(file,show,NULL); }
static int show_sizes(struct seq_file *s,void *unused)
{
    unsigned int i;int cpu;u64 skipped=0;
    for (i=0;i<258;i++) {
        u64 sum=0;
        for_each_possible_cpu(cpu) sum+=per_cpu(counts,cpu).copy_sizes[i];
        if (sum) seq_printf(s,"%u %llu\n",i,sum);
    }
    for_each_possible_cpu(cpu) skipped+=per_cpu(counts,cpu).skipped_copy;
    seq_printf(s,"null_destination %llu\n",skipped);
    return 0;
}
static int open_sizes(struct inode *inode,struct file *file) { return single_open(file,show_sizes,NULL); }
static const struct file_operations size_operations={.owner=THIS_MODULE,.open=open_sizes,
    .read=seq_read,.llseek=seq_lseek,.release=single_release};
static ssize_t control(struct file *file,const char __user *buffer,size_t size,loff_t *position)
{
    char command;int cpu;
    if (size!=1 && size!=2) return -EINVAL;
    if (copy_from_user(&command,buffer,1)) return -EFAULT;
    if (command=='1') WRITE_ONCE(enabled,true);
    else if (command=='0') WRITE_ONCE(enabled,false);
    else if (command=='r') {
        if (READ_ONCE(enabled)) return -EBUSY;
        for_each_possible_cpu(cpu) memset(&per_cpu(counts,cpu),0,sizeof(struct cpu_counts));
    } else return -EINVAL;
    return size;
}
static const struct file_operations operations={.owner=THIS_MODULE,.open=open_counts,
    .read=seq_read,.write=control,.llseek=seq_lseek,.release=single_release};
static int __init start(void)
{
    unsigned int i;int ret;
    if (!address_count) return -EINVAL;
    for (i=0;i<address_count;i++) {
        probes[i].index=i;probes[i].probe.addr=(kprobe_opcode_t *)addresses[i];
        probes[i].probe.pre_handler=before;
        ret=register_kprobe(&probes[i].probe);
        if (ret) goto fail;
        registered++;
    }
    directory=debugfs_create_dir("vkso_sq_service_count",NULL);
    if (IS_ERR(directory)) { ret=PTR_ERR(directory);goto fail; }
    if (!debugfs_create_file("counts",0600,directory,NULL,&operations)) {
        ret=-ENOMEM;debugfs_remove_recursive(directory);goto fail;
    }
    if (!debugfs_create_file("copy_sizes",0400,directory,NULL,&size_operations)) {
        ret=-ENOMEM;debugfs_remove_recursive(directory);goto fail;
    }
    return 0;
fail:
    while (registered) unregister_kprobe(&probes[--registered].probe);
    return ret;
}
static void __exit stop(void)
{
    WRITE_ONCE(enabled,false);debugfs_remove_recursive(directory);
    while (registered) unregister_kprobe(&probes[--registered].probe);
}
module_init(start);module_exit(stop);MODULE_LICENSE("GPL");
