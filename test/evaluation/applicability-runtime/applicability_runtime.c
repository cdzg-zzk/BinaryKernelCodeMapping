// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/debugfs.h>
#include <linux/fs.h>
#include <linux/slab.h>
#include <linux/mm.h>
#include <linux/vmalloc.h>
#include <linux/sort.h>
#include <linux/xxhash.h>
#include <linux/sched.h>

static void *ar_allocate(size_t size) { return kmalloc(size, GFP_KERNEL); }
static void ar_release(void *pointer) { kfree(pointer); }
#define AR_CALLBACK noinline
#include "engine.h"

static unsigned int roots = 3;
module_param(roots, uint, 0444);
MODULE_PARM_DESC(roots, "Functional root mask: 1=xxh32, 2=sort, 3=both; no timing");
static struct ar_text hash_text, sort_text, status_text;
static struct dentry *directory;

/* Assignment to the shared complete signature is checked against real kernel
 * public headers; ordinary imports retain normal module dependency semantics. */
static ar_hash_fn const kernel_hash = xxh32;
static ar_sort_fn const kernel_sort = sort;

static ssize_t ar_read(struct file *file, char __user *buffer, size_t count, loff_t *position)
{
	struct ar_text *text = file->private_data;
	return simple_read_from_buffer(buffer, count, position, text->data, text->length);
}

static const struct file_operations ar_operations = {
	.owner = THIS_MODULE, .open = simple_open, .read = ar_read, .llseek = default_llseek,
};

static void ar_cleanup(void)
{
	debugfs_remove_recursive(directory);
	directory = NULL;
	kvfree(hash_text.data); kvfree(sort_text.data); kvfree(status_text.data);
	hash_text.data = sort_text.data = status_text.data = NULL;
}

static int __init ar_init(void)
{
	struct ar_stats stats = {0};
	struct dentry *entry;
	int result;
	if (!roots || roots > 3) return -EINVAL;
	hash_text.capacity = AR_HASH_CAPACITY;
	sort_text.capacity = AR_SORT_CAPACITY;
	status_text.capacity = 4096;
	hash_text.data = kvzalloc(hash_text.capacity, GFP_KERNEL);
	sort_text.data = kvzalloc(sort_text.capacity, GFP_KERNEL);
	status_text.data = kvzalloc(status_text.capacity, GFP_KERNEL);
	if (!hash_text.data || !sort_text.data || !status_text.data) { result = -ENOMEM; goto fail; }
	ar_headers(&hash_text, &sort_text);
	result = ar_execute(roots, kernel_hash, kernel_sort, &hash_text, &sort_text, &stats);
	ar_append(&status_text,
		"{\"schema_version\":1,\"backend\":\"kernel-public-imports\",\"status\":\"%s\","
		"\"errno\":%d,\"roots\":%u,\"xxh32_checks\":%u,\"xxh32_kats\":%u,\"sort_checks\":%u,"
		"\"failed_case\":%d,\"cmp_calls\":%llu,\"swap_calls\":%llu,"
		"\"api_addresses\":{\"xxh32\":%lu,\"sort\":%lu},"
		"\"callback_addresses\":{\"comparator\":%lu,\"swap\":%lu},"
		"\"callback_swap_size_bytes\":%zu,\"pointer_bytes\":%zu,\"size_t_bytes\":%zu,"
		"\"workload_buffers_released\":true,\"measurement\":false}\n",
		result ? "fail" : "pass", result, roots, stats.hash_checks, stats.hash_kats,
		stats.sort_checks, stats.failed_case, (unsigned long long)stats.cmp_calls,
		(unsigned long long)stats.swap_calls, (unsigned long)kernel_hash, (unsigned long)kernel_sort,
		(unsigned long)ar_comparator, (unsigned long)ar_swapper, sizeof(int), sizeof(void *), sizeof(size_t));
	if (status_text.error) { result = status_text.error; goto fail; }
	directory = debugfs_create_dir("applicability_runtime", NULL);
	if (IS_ERR_OR_NULL(directory)) { result = directory ? PTR_ERR(directory) : -ENOMEM; directory = NULL; goto fail; }
#define AR_FILE(name, object) do { \
	entry = debugfs_create_file(name, 0400, directory, &(object), &ar_operations); \
	if (IS_ERR_OR_NULL(entry)) { result = entry ? PTR_ERR(entry) : -ENOMEM; goto fail; } \
} while (0)
	AR_FILE("status", status_text); AR_FILE("xxh32.csv", hash_text); AR_FILE("sort.csv", sort_text);
#undef AR_FILE
	pr_info("APPLICABILITY_RUNTIME status=%s errno=%d roots=%u xxh32_checks=%u sort_checks=%u failed_case=%d xxh32=%px sort=%px cmp=%px swap=%px\n",
		stats.error ? "fail" : "pass", stats.error, roots, stats.hash_checks, stats.sort_checks,
		stats.failed_case, kernel_hash, kernel_sort, ar_comparator, ar_swapper);
	/* Retain immutable diagnostics even for a functional failure. The controller
 * must check status/errno; successful insmod alone is not a test PASS. */
	return 0;
fail:
	pr_err("APPLICABILITY_RUNTIME status=setup-fail errno=%d\n", result);
	ar_cleanup();
	return result;
}

static void __exit ar_exit(void) { ar_cleanup(); }
module_init(ar_init);
module_exit(ar_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Independent functional observations of original built-in xxh32/sort");
