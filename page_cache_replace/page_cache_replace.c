#include <linux/module.h>
#include <linux/fs.h>
#include <linux/pagemap.h>
#include <linux/netlink.h>
#include <net/sock.h>
#include <linux/uaccess.h>
#include <linux/slab.h>
#include <linux/mm.h>
#include <linux/highmem.h>
#include <asm/cacheflush.h>
#include <asm/tlbflush.h>
#include <linux/mm_types.h>
#include <linux/hugetlb.h>

#include <asm/page.h>
#include <asm/pgtable.h>
#include <linux/vmalloc.h>

#define NETLINK_MODIFY 30  // 自定义 Netlink 协议号
#define NETLINK_RESTORE 29  // 恢复操作的 Netlink 协议号
#define MAX_PAGES_PER_OPERATION 100  // 每次操作的最大页面数

static struct sock *nl_sk = NULL;
static struct sock *nl_restore_sk = NULL;
static struct file *target_file = NULL;

// 保存原始页信息用于恢复（当前实现仅使用 add 模式，下列 original_* 字段为未来扩展预留）
struct page_backup {
    struct page *original_page;     // 预留：原始页面指针（当前实现恒为 NULL）
    unsigned long original_flags;   // 预留：原始页面的标志位
    void *original_mapping;         // 预留：原始页面的地址空间映射指针
    unsigned long original_index;   // 预留：原始页面在地址空间中的索引位置
    bool is_backed_up;             // 备份状态标志：true表示已备份，false表示未备份
    pgoff_t backup_index;          // 被备份页面在页缓存中的索引，用于定位恢复位置
    struct address_space *target_mapping; // 目标文件的地址空间映射，用于恢复操作
};

// 多页面备份管理结构
struct multi_page_backup {
    struct page_backup backup_array[MAX_PAGES_PER_OPERATION];  // 备份页面数组
    int backup_count;               // 备份的页面数量
    bool is_active;                 // 是否有活跃的备份
};

static struct multi_page_backup page_backup_manager = {
    .backup_count = 0,
    .is_active = false
};

// 初始化多页面备份管理器
static void init_multi_page_backup(void) {
    int i;
    memset(&page_backup_manager, 0, sizeof(page_backup_manager));
    for (i = 0; i < MAX_PAGES_PER_OPERATION; i++) {
        page_backup_manager.backup_array[i].is_backed_up = false;
        page_backup_manager.backup_array[i].original_page = NULL;
    }
}

// 单页面备份（保持原有逻辑）
// static struct page_backup page_backup_info = {0};  // 已不再使用

// Netlink 消息格式 - 支持多页面
struct nl_msg {
    char filepath[256];
    loff_t offset;                 // 起始偏移量（单页面模式）
    unsigned long addr;            // 用户空间地址
    int page_count;                // 页面数量，1表示单页面模式
    loff_t page_offsets[MAX_PAGES_PER_OPERATION];  // 每个页面的偏移量
    unsigned long kernel_vaddrs[MAX_PAGES_PER_OPERATION];  // 每个页面对应的内核虚拟地址
};

// 恢复请求消息格式 - 支持多页面
struct restore_msg {
    char filepath[256];  // 要恢复的文件路径
    loff_t offset;       // 起始偏移量（单页面模式）
    int page_count;      // 要恢复的页面数量，1表示单页面模式
    loff_t page_offsets[MAX_PAGES_PER_OPERATION];  // 每个页面的偏移量
};

unsigned long filemap_addr;

// 函数声明
static struct page *get_kernel_code_page(unsigned long kernel_vaddr);
static void backup_page_info(struct page *original_page, pgoff_t index, struct address_space *mapping);
static struct page_backup* find_backup_info(pgoff_t index);
static void clear_backup_info(pgoff_t index);
static int batch_process_pages(struct file *file, struct nl_msg *msg);
static int batch_restore_pages(struct file *file, struct restore_msg *msg);

void test_page_lru(struct page *page)
{
    if (!PageLRU(page)) {
        pr_info("LRU: not on any LRU\n");
        return;
    }

    if (PageUnevictable(page))
        pr_info("LRU: on unevictable LRU\n");
    else if (PageActive(page))
        pr_info("LRU: on active LRU\n");
    else
        pr_info("LRU: on inactive LRU\n");
}
int pmd_huge(pmd_t pmd)
{
    return !pmd_none(pmd) && 
            (pmd_val(pmd) & (_PAGE_PRESENT|_PAGE_PSE)) != _PAGE_PRESENT;
}
int get_page_table(unsigned long addr)
{
    pgd_t *pgd;
    p4d_t *p4d;
    pud_t *pud;
    pmd_t *pmd;
    pte_t *pte;
    struct mm_struct *mm;
    struct page *tmp_page;
    
    if(addr == 0) {
        printk(KERN_INFO "skip walk page table\n");
        return 0;
    }
    printk(KERN_INFO "%s\n", __func__);
    printk(KERN_INFO "%lx\n", addr);

    mm = current->mm;
    printk(KERN_INFO "current->pid is %d   addr: %lx    mm: %p\n", current->pid, addr, mm);   // 检查PGD是否一致，虽然一致，但是还挺重要的
    if(!mm) {
        printk(KERN_ERR "No mm_struct for current process\n");
        return 1;
    }
    pgd = pgd_offset(mm, addr);
    if(pgd_none(*pgd) || pgd_bad(*pgd)) {
        printk(KERN_INFO "PGD invalid or not present for address 0x%lx\n", addr);
         return 2;
    }
    printk(KERN_INFO "PGD found at %p, value: 0x%lx\n", pgd, pgd_val(*pgd));
     printk(KERN_INFO "Protection bits: %s%s%s\n", 
        (pgd_val(*pgd) & _PAGE_USER) ? "USER " : "", 
        (pgd_val(*pgd) & _PAGE_RW) ? "RW " : "RO ",
        (pgd_val(*pgd) & _PAGE_NX) ? "NO-EXEC" : "EXEC"); 


    printk(KERN_INFO "if have p4d: %d\n", pgtable_l5_enabled());
    p4d = p4d_offset(pgd, addr);
    if(p4d_none(*p4d) || p4d_bad(*p4d)) {
        printk(KERN_INFO "P4D invalid or not present for address 0x%lx\n", addr);
         return 3;
    }
    printk(KERN_INFO "P4D found at %p, value: 0x%lx\n", p4d, p4d_val(*p4d));
    printk(KERN_INFO "Protection bits: %s%s%s\n", 
        (p4d_val(*p4d) & _PAGE_USER) ? "USER " : "", 
         (p4d_val(*p4d) & _PAGE_RW) ? "RW " : "RO ",
        (p4d_val(*p4d) & _PAGE_NX) ? "NO-EXEC" : "EXEC"); 


    pud = pud_offset(p4d, addr);
    if(pud_none(*pud) || pud_bad(*pud)) {
        printk(KERN_INFO "PUD invalid or not present for address 0x%lx\n", addr);
        return 4;
    }
    printk(KERN_INFO "PUD found at %p, value: 0x%lx\n", pud, pud_val(*pud));
    printk(KERN_INFO "Protection bits: %s%s%s\n", 
        (pud_val(*pud) & _PAGE_USER) ? "USER " : "", 
        (pud_val(*pud) & _PAGE_RW) ? "RW " : "RO ",
        (pud_val(*pud) & _PAGE_NX) ? "NO-EXEC" : "EXEC"); 


    pmd = pmd_offset(pud, addr);
    if(pmd_none(*pmd) || pmd_bad(*pmd)) {
        printk(KERN_INFO "PMD invalid or not present for address 0x%lx\n", addr);
        return 5;
    }
    printk(KERN_INFO "PMD found at %p, value: 0x%lx\n", pmd, pmd_val(*pmd));
    if(pmd_huge(*pmd)) {
        printk(KERN_INFO "This is a huge page mapping at PMD level\n");
        printk(KERN_INFO "PMD flags: %s %s %s\n", (pmd_val(*pmd) & _PAGE_USER) ? "USER " : "",
                                                    (pmd_val(*pmd) & _PAGE_RW) ? "RW " : "RO ",
                                                    (pmd_val(*pmd) & _PAGE_NX) ? "EXEC " : "NO-EXEC");
        return 6;
    }
    printk(KERN_INFO "Protection bits: %s%s%s\n", 
            (pmd_val(*pmd) & _PAGE_USER) ? "USER " : "", 
            (pmd_val(*pmd) & _PAGE_RW) ? "RW " : "RO ",
            (pmd_val(*pmd) & _PAGE_NX) ? "NO-EXEC" : "EXEC"); 
    
    
    pte = pte_offset_map(pmd, addr);
    if(!pte) {
         printk(KERN_INFO "Filed to map PTE for address 0x%lx\n", addr);
        return 7;
    }
    if(pte_none(*pte)) {
        printk(KERN_INFO "PTE not present for address 0x%lx\n", addr);
        pte_unmap(pte);
         return 8;
    }
    printk(KERN_INFO "PTE found at %p, value: 0x%lx\n", pte, pte_val(*pte)); 
    printk(KERN_INFO "Page frame number: 0x%lx\n", pte_pfn(*pte)); 
    printk(KERN_INFO "Protection bits: %s%s%s\n", 
            (pte_val(*pte) & _PAGE_USER) ? "USER " : "", 
            (pte_val(*pte) & _PAGE_RW) ? "RW " : "RO ",
            (pte_val(*pte) & _PAGE_NX) ? "NO-EXEC" : "EXEC"); 
    if (!(pte_val(*pte) & _PAGE_PRESENT)) 
         printk(KERN_INFO "Warning: Page is not present!\n");
    tmp_page = pfn_to_page(pte_pfn(*pte));
    pr_info("tmp_page refcount: %d\n", atomic_read(&tmp_page->_refcount));
    pr_info("tmp_page mapcount: %d\n", atomic_read(&tmp_page->_mapcount));

    return -1;
}

// 添加新页到页缓存（之前没有页缓存的情况）
static int add_page_to_cache(struct file *file, pgoff_t index, struct page *new_page) {
    struct address_space *mapping = file->f_mapping;
    struct page *existing_page;
    int ret = 0;
    struct page *verify_page;
    XA_STATE(xas, &mapping->i_pages, index);
    
    pr_info("add_page_to_cache start mapping: %p  i_pages: %p\n", mapping, &mapping->i_pages);

    /* 确认这是文件页而不是 swap-backed 页 */
    VM_BUG_ON_PAGE(PageSwapBacked(new_page), new_page);

    /* 遵守通用约定：插入 page cache 期间保持 PageLocked */
    lock_page(new_page);

    /*
     * 核心内核在使用 xarray 更新 page cache 时会调用 mapping_set_update()
     * 配合 workingset 做更精细的回收统计。但该 helper 只在核心 mm 内部使用，
     * 对模块不可见。这里直接略过它，只使用 xas_lock/xas_store 即可，正确性不受影响。
     */

    xas_lock(&xas);
    
    // 确认该位置确实没有页
    existing_page = xas_load(&xas);
    if (existing_page) {
        /*
         * xarray 里既可能存真正的 struct page*，也可能是 workingset
         * 留下的 shadow entry（xa_is_value(entry) 为真）。
         *
         * - 如果是 shadow entry：说明之前这里有过页被回收，
         *   但现在只剩一块“墓碑”，可以安全覆盖为我们的 code_page。
         * - 如果是实际的 page*：说明页缓存里已经有有效页，
         *   当前只支持 add 模式，视为冲突。
         */
        if (!xa_is_value(existing_page)) {
            pr_warn("Page already exists at index %lu, add mode does not overwrite existing cache\n", index);
            ret = -EEXIST;
            goto unlock_xas;
        }
        pr_info("Found shadow entry at index %lu, will overwrite with code page\n", index);
    }
    
    // 设置新页的映射信息
    new_page->mapping = mapping;
    new_page->index = index;
    
    // 设置页为最新状态
    SetPageUptodate(new_page);
    
    // 增加新页引用计数
    get_page(new_page);
    
    // 备份添加操作的信息 - 使用新的多页面备份管理
    backup_page_info(NULL, index, mapping);

    // 使用 xarray state + xas_store 插入页，配合 mapping_set_update
    xas_store(&xas, new_page);
    if (xas_error(&xas)) {
        int err = xas_error(&xas);

        put_page(new_page);
        pr_err("Failed to store page in cache: %d\n", err);
        ret = err;
        goto unlock_xas;
    }
    
    // 增加页面计数器（add操作增加了页面数量）
    mapping->nrpages++;
    
    pr_info("New page added to cache: %p at index %lu (nrpages: %lu)\n",
            new_page, index, mapping->nrpages);

unlock_xas:
    xas_unlock(&xas);
    unlock_page(new_page);
    
    if (ret == 0) {
        // 刷新CPU缓存确保一致性
        // flush_dcache_page(new_page);
        if(PageDirty(new_page)) {
            pr_info("PageDirty: %p\n", new_page);
        }
        get_page_table(filemap_addr);
        pr_info("new page refcount: %d\n", atomic_read(&new_page->_refcount));
        pr_info("new page mapcount: %d\n", atomic_read(&new_page->_mapcount));
        // 清除所有映射该文件的进程的PTE，让后续访问触发page fault
        unmap_mapping_range(mapping, (loff_t)index << PAGE_SHIFT, PAGE_SIZE, 0);
        get_page_table(filemap_addr);
        pr_info("new page refcount: %d\n", atomic_read(&new_page->_refcount));
        pr_info("new page mapcount: %d\n", atomic_read(&new_page->_mapcount));
        pr_info("Page addition to cache completed successfully\n");
    }
    {
        verify_page = xa_load(&mapping->i_pages, index);
        pr_info("Page cache add: old=NULL, new=%p at index %lu (验证成功)\n", verify_page, index);
   
    }
    return ret;
}

// 恢复原始页缓存
static int restore_page_cache(struct file *file, pgoff_t index) {
    struct address_space *mapping = file->f_mapping;
    struct page *current_page;
    int ret = 0;
    struct page_backup *backup_entry;
    XA_STATE(xas, &mapping->i_pages, index);
    
    pr_info("restore_page_cache start mapping: %p  i_pages: %p\n", mapping, &mapping->i_pages);
    
    if (!page_backup_manager.is_active) {
        pr_err("No backup information available\n");
        return -ENOENT;
    }
    
    // 查找备份信息
    backup_entry = find_backup_info(index);
    if (!backup_entry) {
        pr_err("No backup found for index %lu\n", index);
        return -ENOENT;
    }
    xas_lock(&xas);
    
    current_page = xas_load(&xas);
    pr_info("xa_load done");
    test_page_lru(current_page);
    if (!current_page) {
        pr_err("No current page found at index %lu\n", index);
        ret = -ENOENT;
        goto unlock_xas;
    }
    get_page(current_page);
    
    /*
     * 当前实现只支持 add 模式：backup_entry->original_page 始终为 NULL。
     * 这里统一走“删除 LKM 页”的路径：
     * - xas_store(NULL) 从 i_pages 删除条目
     * - nrpages-- 保持 mapping 统计一致
     * - put_page(current_page) 撤销 page cache 持有的那一份引用
     */
    pr_info("Removing added page from add operation\n");
    
    // 从页缓存中删除（使用 xas_store(NULL) 与 add 路径保持一致）
    xas_store(&xas, NULL);
    if (xas_error(&xas)) {
        int err = xas_error(&xas);

        pr_err("xas_store(NULL) failed during restore: %d\n", err);
        ret = err;
        goto unlock_xas;
    }
    
    // 减少页面计数器（删除操作减少了页面数量）
    if (mapping->nrpages > 0) {
        mapping->nrpages--;
    }
    
    // 减少LKM页在page cache中的引用
    put_page(current_page);
    
    pr_info("Added page removed from cache at index %lu (nrpages: %lu)\n", 
            index, mapping->nrpages);
    
unlock_xas:
    xas_unlock(&xas);
    
    if (ret == 0) {
        // 清除所有映射该文件的进程的PTE，让后续访问触发page fault
        unmap_mapping_range(mapping, (loff_t)index << PAGE_SHIFT, PAGE_SIZE, 0);

        // 清除该页面的备份信息
        clear_backup_info(index);
        
        pr_info("current_page refcount: %d\n", atomic_read(&current_page->_refcount));
        pr_info("current_page mapcount: %d\n", atomic_read(&current_page->_mapcount));
        current_page->mapping = NULL;
        current_page->index = 0;
        put_page(current_page); // 本进程的struct page*引用
        pr_info("Page cache restore completed successfully\n");
    }
    pr_info("================== END ==================\n");
    return ret;
}

// 批量处理多页面操作 - 封装现有逻辑
static int batch_process_pages(struct file *file, struct nl_msg *msg) {
    struct page *code_page;
    int ret = 0;
    int i;
    
    pr_info("Processing %d pages for file: %s\n", msg->page_count, msg->filepath);
    
    // 处理每个页面
    for (i = 0; i < msg->page_count; i++) {
        pgoff_t index = msg->page_offsets[i] >> PAGE_SHIFT;
        struct page *existing_page;
        unsigned long kernel_vaddr = msg->kernel_vaddrs[i];
        
        pr_info("Processing page %d: offset=%lld, index=%lu, kernel_vaddr=0x%lx\n", 
                i, msg->page_offsets[i], index, kernel_vaddr);
        
        // 获取指定内核虚拟地址对应的物理页
        code_page = get_kernel_code_page(kernel_vaddr);
        if (!code_page) {
            pr_err("Failed to get LKM code page for kernel_vaddr: 0x%lx\n", kernel_vaddr);
            ret = -ENOMEM;
            break;
        }
        
        // 检查页缓存中是否已存在该页
        existing_page = pagecache_get_page(file->f_mapping, index, FGP_LOCK, 0);
        if(existing_page) {
            pr_info("existing_page refcount: %d\n", atomic_read(&existing_page->_refcount));
            pr_info("existing_page mapcount: %d\n", atomic_read(&existing_page->_mapcount));
            test_page_lru(existing_page);
            // 页缓存中已存在页面，需要删除这个页
            unmap_mapping_range(file->f_mapping, (loff_t)index << PAGE_SHIFT, PAGE_SIZE, 0);
            delete_from_page_cache(existing_page);
            unlock_page(existing_page);
            test_page_lru(existing_page);
            pr_info("existing_page refcount: %d\n", atomic_read(&existing_page->_refcount));
            pr_info("existing_page mapcount: %d\n", atomic_read(&existing_page->_mapcount));
            put_page(existing_page);  // 至此完全释放
        }
        pr_info("Page not in cache at index %lu, adding new page...\n", index);
        ret = add_page_to_cache(file, index, code_page);
        if (ret) {
            pr_err("Failed to add page at index %lu: %d\n", index, ret);
            break;
        }
    }
    
    return ret;
}

// 批量恢复多页面操作 - 封装现有逻辑
static int batch_restore_pages(struct file *file, struct restore_msg *msg) {
    int ret = 0;
    int i;
    
    pr_info("Restoring %d pages for file: %s\n", msg->page_count, msg->filepath);
    
    // 处理每个页面
    for (i = 0; i < msg->page_count; i++) {
        pgoff_t index = msg->page_offsets[i] >> PAGE_SHIFT;
        
        pr_info("Restoring page %d: offset=%lld, index=%lu\n", i, msg->page_offsets[i], index);
        
        ret = restore_page_cache(file, index);
        if (ret) {
            pr_err("Failed to restore page at index %lu: %d\n", index, ret);
            break;
        }
    }
    
    return ret;
}

// 多页面备份管理函数
static void backup_page_info(struct page *original_page, pgoff_t index, struct address_space *mapping) {
    if (page_backup_manager.backup_count < MAX_PAGES_PER_OPERATION) {
        struct page_backup *backup_entry = &page_backup_manager.backup_array[page_backup_manager.backup_count];
        
        /*
         * 当前实现只支持 add 模式：不会备份原始页，只记录 index/mapping。
         * 保留 original_* 字段仅作为未来扩展的占位，不在当前逻辑中使用。
         */
        backup_entry->original_page = NULL;
        backup_entry->original_flags = 0;
        backup_entry->original_mapping = NULL;
        backup_entry->original_index = 0;
        backup_entry->backup_index = index;
        backup_entry->target_mapping = mapping;
        backup_entry->is_backed_up = true;
        
        page_backup_manager.backup_count++;
        page_backup_manager.is_active = true;
        
        pr_info("Backed up page info: index=%lu, original_page=%p\n", index, original_page);
    } else {
        pr_err("Backup array is full, cannot backup more pages\n");
    }
}

// 查找备份信息
static struct page_backup* find_backup_info(pgoff_t index) {
    int i;
    for (i = 0; i < page_backup_manager.backup_count; i++) {
        if (page_backup_manager.backup_array[i].backup_index == index && 
            page_backup_manager.backup_array[i].is_backed_up) {
            return &page_backup_manager.backup_array[i];
        }
    }
    return NULL;
}

// 清除备份信息
static void clear_backup_info(pgoff_t index) {
    struct page_backup *backup_entry = find_backup_info(index);
    if (backup_entry) {
        /* 目前 original_page 始终为 NULL，这里只清理标志位 */
        backup_entry->is_backed_up = false;
        pr_info("Cleared backup info for index %lu\n", index);
    }
}

void inspect_page_content(struct page *page) {
    void *vaddr;
    int i;
    char *content;

    // 1. 将物理页临时映射到内核虚拟地址空间
    vaddr = kmap(page);
    if (!vaddr) {
        pr_err("kmap failed!\n");
        return;
    }

    // 2. 现在 vaddr 是一个指向该页面起始地址的指针
    content = (char *)vaddr;

    // 3. 示例：打印页面开头的前 128 个字节
    pr_info("Content of page %p (PFN: %lu):\n", page, page_to_pfn(page));
    for (i = 0; i < 128; i++) {
        if (i % 16 == 0) {
            pr_cont("\n%04x: ", i);
        }
        pr_cont("%02x ", content[i+0x900] & 0xff);
    }
    pr_cont("\n");

    // 4. 重要：解除映射
    kunmap(page);
}

static struct page *lookup_kernel_page(unsigned long kernel_vaddr, unsigned int *level_out)
{
    unsigned int level = PG_LEVEL_NONE;
    pte_t *pte = lookup_address(kernel_vaddr, &level);
    unsigned long pfn = 0;

    if (!pte) {
        return NULL;
    }

    // lookup_address() returns a pte_t* for 4K, or a casted pmd/pud for huge pages.
    switch (level) {
    case PG_LEVEL_4K:
        if (!pte_present(*pte)) {
            return NULL;
        }
        pfn = pte_pfn(*pte);
        break;
    case PG_LEVEL_2M: {
        pmd_t *pmd = (pmd_t *)pte;
        if (!pmd_present(*pmd)) {
            return NULL;
        }
        pfn = pmd_pfn(*pmd) + ((kernel_vaddr & ~PMD_MASK) >> PAGE_SHIFT);
        break;
    }
    case PG_LEVEL_1G: {
        pud_t *pud = (pud_t *)pte;
        if (!pud_present(*pud)) {
            return NULL;
        }
        pfn = pud_pfn(*pud) + ((kernel_vaddr & ~PUD_MASK) >> PAGE_SHIFT);
        break;
    }
    default:
        return NULL;
    }

    if (level_out) {
        *level_out = level;
    }
    if (!pfn_valid(pfn)) {
        return NULL;
    }
    return pfn_to_page(pfn);
}

// 获取内核代码页 - 通用版本（支持LKM和内核核心代码）
static struct page *get_kernel_code_page(unsigned long kernel_vaddr) {
    struct page *code_page = NULL;
    phys_addr_t pa = 0;
    unsigned long pfn = 0;
    unsigned int level = PG_LEVEL_NONE;
    
    // 验证内核虚拟地址是否有效
    if (!kernel_vaddr) {
        pr_err("Invalid kernel virtual address: 0x%lx\n", kernel_vaddr);
        return NULL;
    }

    pr_info("Attempting to get page for kernel virtual address: 0x%lx\n", kernel_vaddr);

    // 0) 直接查页表（最可靠：模块/直映射/内核文本都能覆盖）
    code_page = lookup_kernel_page(kernel_vaddr, &level);
    if (code_page) {
        pr_info("Successfully got page via lookup_address (level=%u): %p\n", level, code_page);
        goto out;
    }
    
    // 1) vmalloc/module_alloc 区（LKM/BPF/execmem）
    code_page = vmalloc_to_page((void *)kernel_vaddr);
    if (code_page) {
        pr_info("Successfully got page via vmalloc_to_page: %p\n", code_page);
        goto out;
    }
    
    // 2) 直接映射（线性映射）区
    if (virt_addr_valid((void *)kernel_vaddr)) {
        pr_info("Address is in direct mapping (virt_addr_valid)\n");
        code_page = virt_to_page((void *)kernel_vaddr);
        if (code_page) {
            pr_info("Successfully got page via virt_to_page: %p\n", code_page);
            goto out;
        }
    }
    
    // 3) vmlinux 核心镜像（.text/.rodata/.data 等）
    pr_info("Trying core image (__pa_symbol)\n");
    pa = __pa_symbol(kernel_vaddr);
    pfn = PHYS_PFN(pa);
    if (pfn_valid(pfn)) {
        code_page = pfn_to_page(pfn);
        if (code_page) {
            pr_info("Successfully got page via __pa_symbol->pfn_to_page: %p\n", code_page);
            goto out;
        }
    }

out:
    if (!code_page) {
        pr_err("Failed to resolve struct page* for vaddr: 0x%lx\n", kernel_vaddr);
        return NULL;
    }
    
    // 检查页面状态
    if (PageReserved(code_page)) {
        pr_info("Code page is reserved: %p (vaddr: 0x%lx)\n", code_page, kernel_vaddr);
    } else {
        pr_info("Code page is not reserved: %p (vaddr: 0x%lx)\n", code_page, kernel_vaddr);
    }
    
    // 强制设置页面为最新状态（注意：对于内核核心代码页要谨慎）
    SetPageUptodate(code_page);
    
    pr_info("Code page obtained: %p (vaddr: 0x%lx)\n", code_page, kernel_vaddr);
    pr_info("Code page mapping: %p\n", code_page->mapping);
    pr_info("Code page index: %lu\n", code_page->index);
    pr_info("Code page flags: %lu\n", code_page->flags);
    pr_info("Code page refcount: %d\n", atomic_read(&code_page->_refcount));
    pr_info("Code page mapcount: %d\n", atomic_read(&code_page->_mapcount));
    inspect_page_content(code_page);
    return code_page;
}

// 恢复消息处理回调 - 支持多页面
static void nl_recv_restore_msg(struct sk_buff *skb) {
    struct nlmsghdr *nlh = nlmsg_hdr(skb);
    struct restore_msg *msg = nlmsg_data(nlh);
    struct file *target_file = NULL;  // 初始化为NULL
    int err;
    int i;

    pr_info("Received page cache restore request for file: %s, page_count: %d\n", 
            msg->filepath, msg->page_count);

    // 验证参数
    if (msg->page_count <= 0 || msg->page_count > MAX_PAGES_PER_OPERATION) {
        pr_err("Invalid page count: %d\n", msg->page_count);
        goto out;  // 跳转到清理点
    }
    
    // 验证所有offset是否合法
    for (i = 0; i < msg->page_count; i++) {
        if (msg->page_offsets[i] < 0) {
            pr_err("Invalid negative offset at index %d: %lld\n", i, msg->page_offsets[i]);
            goto out;  // 跳转到清理点
        }
    }

    // 打开目标文件
    target_file = filp_open(msg->filepath, O_RDONLY, 0);
    if (IS_ERR(target_file)) {
        pr_err("Failed to open file: %s, error: %ld\n", msg->filepath, PTR_ERR(target_file));
        goto out;  // 跳转到清理点
    }

    // 验证备份信息是否匹配
    if (!page_backup_manager.is_active) {
        pr_err("No backup information available for restore\n");
        goto out;  // 跳转到清理点
    }

    // 批量恢复页面
    err = batch_restore_pages(target_file, msg);
    if (err) {
        pr_err("Failed to restore page cache: %d\n", err);
    } else {
        pr_info("Page cache restored successfully!\n");
    }

out:
    if (target_file && !IS_ERR(target_file)) {
        filp_close(target_file, NULL);
    }
}

// Netlink 消息处理回调 - 支持多页面
static void nl_recv_msg(struct sk_buff *skb) {
    struct nlmsghdr *nlh = nlmsg_hdr(skb);
    struct nl_msg *msg = nlmsg_data(nlh);
    int err;
    int i;

    pr_info("Received page cache request for file: %s, page_count: %d\n", 
            msg->filepath, msg->page_count);

    // 验证参数
    if (msg->page_count <= 0 || msg->page_count > MAX_PAGES_PER_OPERATION) {
        pr_err("Invalid page count: %d\n", msg->page_count);
        goto out;  // 跳转到清理点
    }
    
    // 验证所有offset是否合法
    for (i = 0; i < msg->page_count; i++) {
        if (msg->page_offsets[i] < 0) {
            pr_err("Invalid negative offset at index %d: %lld\n", i, msg->page_offsets[i]);
            goto out;  // 跳转到清理点
        }
    }
    
    // 验证所有内核虚拟地址是否合法
    for (i = 0; i < msg->page_count; i++) {
        if (msg->kernel_vaddrs[i] == 0) {
            pr_err("Invalid kernel virtual address at index %d: 0x%lx\n", i, msg->kernel_vaddrs[i]);
            goto out;  // 跳转到清理点
        }
    }

    // 打开目标文件
    target_file = filp_open(msg->filepath, O_RDONLY, 0);
    if (IS_ERR(target_file)) {
        pr_err("Failed to open file: %s, error: %ld\n", msg->filepath, PTR_ERR(target_file));
        goto out;  // 跳转到清理点
    }

    filemap_addr = msg->addr;
    
    // 批量处理页面
    err = batch_process_pages(target_file, msg);
    if (err) {
        pr_err("Failed to process pages: %d\n", err);
    } else {
        pr_info("Page cache operation completed successfully!\n");
        pr_info("Next file access will trigger page fault and establish PTE mapping automatically\n");
    }

out:
    if (target_file && !IS_ERR(target_file)) {
        filp_close(target_file, NULL);
    }
}

// Netlink 初始化
static int __init page_replace_init(void) {
    struct netlink_kernel_cfg cfg = {
        .input = nl_recv_msg,
    };
    struct netlink_kernel_cfg restore_cfg = {
        .input = nl_recv_restore_msg,
    };

    pr_info("Initializing Page Replace LKM...\n");
    pr_info("Attempting to create Netlink socket with protocol %d\n", NETLINK_MODIFY);

    // 初始化多页面备份管理器
    init_multi_page_backup();

    // 创建页面替换/添加的netlink套接字
    nl_sk = (struct sock *)netlink_kernel_create(&init_net, NETLINK_MODIFY, &cfg);
    if (!nl_sk) {
        pr_err("Failed to create Netlink socket with protocol %d\n", NETLINK_MODIFY);
        return -ENOMEM;
    }
    pr_info("Successfully created Netlink socket with protocol %d\n", NETLINK_MODIFY);

    pr_info("Attempting to create restore Netlink socket with protocol %d\n", NETLINK_RESTORE);

    // 创建页面恢复的netlink套接字
    nl_restore_sk = (struct sock *)netlink_kernel_create(&init_net, NETLINK_RESTORE, &restore_cfg);
    if (!nl_restore_sk) {
        pr_err("Failed to create restore Netlink socket with protocol %d\n", NETLINK_RESTORE);
        pr_err("Cleaning up previously created socket\n");
        netlink_kernel_release(nl_sk);
        nl_sk = NULL;
        return -ENOMEM;
    }
    pr_info("Successfully created restore Netlink socket with protocol %d\n", NETLINK_RESTORE);

    pr_info("Page Replace LKM loaded successfully\n");
    pr_info("Use protocol %d for replace/add operations\n", NETLINK_MODIFY);
    pr_info("Use protocol %d for restore operations\n", NETLINK_RESTORE);
    return 0;
}

static void __exit page_replace_exit(void) {
    int i;
    
    pr_info("Unloading Page Replace LKM...\n");
    
    // 在模块退出时自动恢复页缓存
    if (page_backup_manager.is_active) {
        pr_info("Auto-restoring page cache during module unload\n");
        
        for (i = 0; i < page_backup_manager.backup_count; i++) {
            struct page_backup *backup_entry = &page_backup_manager.backup_array[i];
            if (backup_entry->is_backed_up && backup_entry->target_mapping) {
                struct file temp_file = {
                    .f_mapping = backup_entry->target_mapping
                };
                
                int ret = restore_page_cache(&temp_file, backup_entry->backup_index);
                if (ret == 0) {
                    pr_info("Page cache auto-restore completed successfully for index %lu\n", 
                           backup_entry->backup_index);
                } else {
                    pr_err("Page cache auto-restore failed for index %lu: %d\n", 
                          backup_entry->backup_index, ret);
                    pr_warn("Some pages may remain modified in cache\n");
                }
            }
        }
        
        page_backup_manager.backup_count = 0;
        page_backup_manager.is_active = false;
    }
    
    // 释放netlink套接字
    if (nl_restore_sk) {
        pr_info("Releasing restore Netlink socket\n");
        netlink_kernel_release(nl_restore_sk);
        nl_restore_sk = NULL;
    }
    if (nl_sk) {
        pr_info("Releasing main Netlink socket\n");
        netlink_kernel_release(nl_sk);
        nl_sk = NULL;
    }
    pr_info("Page Replace LKM unloaded successfully\n");
}

module_init(page_replace_init);
module_exit(page_replace_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("YourName");
MODULE_DESCRIPTION("Page Cache Replacement LKM");
