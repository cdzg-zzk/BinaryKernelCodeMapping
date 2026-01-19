# add_to_page_cache_lru()解析

本文基于你给出的 Linux 内核代码，梳理 `add_to_page_cache_lru()` 及其依赖函数在“将页加入页缓存并挂到 LRU”这一过程中的完整行为，重点放在：

- 做了哪些状态修改（`page->mapping/index`、LRU 标志、memcg、统计）
- 如何与 xarray (`mapping->i_pages`) 交互
- 引用计数的大致变化

---

## 1. 调用关系总览

典型路径（缺页或读文件时）：

- 上层：`filemap_add_folio()` / 旧代码中的 `pagecache_get_page()`、`grab_cache_page_nowait()` 等
  - → `add_to_page_cache_lru(page, mapping, index, gfp)`
    - → `__SetPageLocked(page)`（标记页已被锁住）
    - → `__add_to_page_cache_locked(page, mapping, index, gfp, &shadow)`
      - 设置 `page->mapping` / `page->index`
      - memcg 计费：`mem_cgroup_charge()` → `__mem_cgroup_charge()` → `charge_memcg()` → `try_charge()`/`commit_charge()`
      - 将页插入 `mapping->i_pages`（xarray），更新 `mapping->nrpages`、`NR_FILE_PAGES`
      - 可能返回旧的 `shadow` entry
    - 成功后：
      - 针对 `shadow` 调 `workingset_refault(page, shadow)`（仅在读路径：无 `__GFP_WRITE` 时）
      - `lru_cache_add(page)`（加入 per-cpu pagevec，稍后真正挂 LRU）
        - → `__pagevec_lru_add()`（flush pagevec）
          - → `__pagevec_lru_add_fn(page, lruvec)`（设置 LRU 标志、决定 active/unevictable，并链到对应 LRU）

失败时，`add_to_page_cache_lru()` 会清除 `PageLocked` 并返回错误，不会把页插入 page cache。

---

## 2. add_to_page_cache_lru() 主流程

```c
int add_to_page_cache_lru(struct page *page,
			  struct address_space *mapping,
			  pgoff_t offset, gfp_t gfp_mask)
{
	void *shadow = NULL;
	int ret;

	__SetPageLocked(page);
	ret = __add_to_page_cache_locked(page, mapping, offset,
					 gfp_mask, &shadow);
	if (unlikely(ret))
		__ClearPageLocked(page);
	else {
		WARN_ON_ONCE(PageActive(page));
		if (!(gfp_mask & __GFP_WRITE) && shadow)
			workingset_refault(page, shadow);
		lru_cache_add(page);
	}
	return ret;
}
```

关键点：

- 先把页标记为 Locked：`__SetPageLocked(page)`  
  确保后续插入 page cache 时不会被并发回收/截断等路径干扰，BUG_ON 里也依赖这个前提。
- 调用 `__add_to_page_cache_locked()` 真正完成：
  - 建立 `page` 与 `mapping` / `index` 的绑定；
  - memcg 计费；
  - 插入到 `mapping->i_pages`（xarray）；
  - 更新 `mapping->nrpages` 和节点文件页统计。
- 若失败（如 memcg charge 失败、xarray 插入失败）：
  - 清除 `PageLocked`，保持页处于“还未加入 page cache”的状态；
  - 返回错误码。
- 若成功：
  - 断言该页当前不在 Active LRU：`WARN_ON_ONCE(PageActive(page))`；
  - 如果是读路径（`!(gfp_mask & __GFP_WRITE)`），且 xarray 中之前存在 `shadow` entry，则：
    - 调 `workingset_refault(page, shadow)`：记录“工作集再引用”信息，决定是否立即把页激活等。
  - 调 `lru_cache_add(page)`：将页排队加入 LRU（真正挂 LRU 由 pagevec flush 时完成）。

小结：`add_to_page_cache_lru()` 是一个“包装函数”，保证：

- 页在插入 page cache 期间是 Locked；
- 插入成功后，将其纳入 workingset（通过 shadow/refault）和 LRU 管理。

---

## 3. __add_to_page_cache_locked()：插入 page cache（xarray）并计费

```c
noinline int __add_to_page_cache_locked(struct page *page,
					struct address_space *mapping,
					pgoff_t offset, gfp_t gfp,
					void **shadowp)
{
	XA_STATE(xas, &mapping->i_pages, offset);
	int huge = PageHuge(page);
	int error;
	bool charged = false;

	VM_BUG_ON_PAGE(!PageLocked(page), page);
	VM_BUG_ON_PAGE(PageSwapBacked(page), page);
	mapping_set_update(&xas, mapping);
```

- 此函数要求：
  - `PageLocked(page)`：调用者必须先锁好页面；
  - `!PageSwapBacked(page)`：不能是 swap backed 页（匿名页/SwapCache）。
- `XA_STATE` 初始化一个 xarray 遍历/修改状态，定位到 `mapping->i_pages` 中的 `offset`。
- `mapping_set_update(&xas, mapping)`：告知 mapping 正在更新，配合 xarray 元数据（如顺序号）以支持并发截断/回收。

```c
	get_page(page);
	page->mapping = mapping;
	page->index = offset;
```

- `get_page(page)`：引用计数 +1。对调用者来说：
  - 调用前，通常页的 `refcount` 已经因为分配或其他持有路径为 1；
  - 这里额外 +1，可理解为“page cache 自身的持有”。
- 记录 `page->mapping` 和 `page->index`，正式把页与该文件的 address_space 绑定。

```c
	if (!huge) {
		error = mem_cgroup_charge(page, NULL, gfp);
		if (error)
			goto error;
		charged = true;
	}
```

- 对非 HugeTLB 页进行 memcg 计费：
  - `mem_cgroup_charge()` → `__mem_cgroup_charge(page, NULL, gfp)`：
    - `memcg = get_mem_cgroup_from_mm(mm)`（这里 mm 为 NULL，表示使用“当前活动 memcg”）；
    - `charge_memcg(page, memcg, gfp)`：
      - `try_charge()`：检查 cgroup 内存限制，必要时触发 reclaim；
      - 成功后 `commit_charge(page, memcg)`：把页绑定到 `memcg`；
      - 更新 memcg 统计：`mem_cgroup_charge_statistics()`、`memcg_check_events()`。
- 如果计费失败（内存管控拒绝这次分配），跳到 `error`：撤销 `page->mapping` 等并 `put_page()`。

```c
	gfp &= GFP_RECLAIM_MASK;
```

- 只保留与 reclaim 相关的 GFP 标志，用于后续 xarray 内部内存分配（`xas_nomem()` 重试）。

### 3.1 xarray 插入逻辑与 shadow entry

核心循环：

```c
	do {
		unsigned int order = xa_get_order(xas.xa, xas.xa_index);
		void *entry, *old = NULL;

		if (order > thp_order(page))
			xas_split_alloc(&xas, xa_load(xas.xa, xas.xa_index),
					order, gfp);
		xas_lock_irq(&xas);
		xas_for_each_conflict(&xas, entry) {
			old = entry;
			if (!xa_is_value(entry)) {
				xas_set_err(&xas, -EEXIST);
				goto unlock;
			}
		}

		if (old) {
			if (shadowp)
				*shadowp = old;
			/* entry may have been split before we acquired lock */
			order = xa_get_order(xas.xa, xas.xa_index);
			if (order > thp_order(page)) {
				xas_split(&xas, old, order);
				xas_reset(&xas);
			}
		}

		xas_store(&xas, page);
		if (xas_error(&xas))
			goto unlock;

		mapping->nrpages++;

		if (!huge)
			__inc_lruvec_page_state(page, NR_FILE_PAGES);
unlock:
		xas_unlock_irq(&xas);
	} while (xas_nomem(&xas, gfp));
```

说明：

- xarray 支持以“多 slot 条目”描述 THP 等大页，因此先通过 `xa_get_order()` 获取当前索引处已有条目的“order”（覆盖多少连续索引）。
  - 若当前 order 大于新页的 `thp_order(page)`，需要调用 `xas_split_alloc()` 为拆分预先分配节点。
- `xas_lock_irq()`：加锁保护 xarray 修改。
- `xas_for_each_conflict(&xas, entry)`：
  - 遍历该索引处的“冲突条目”。如果遇到“不是 value 的条目”（即真实的 page/folio），说明该 offset 上已经有了真正的页：
    - 设置错误 `-EEXIST` 并退出；
  - 若只是 value（`xa_is_value(entry)` 为真），则这是一个“shadow entry”：用于工作集跟踪的轻量条目。
    - 把它记到 `old`，稍后返回给调用者。
- 如果 `old` 存在：
  - 若 `shadowp` 不为 NULL，则 `*shadowp = old`：
    - 这就是 `add_to_page_cache_lru()` 之后 `shadow` 参数的来源，用于 `workingset_refault()`。
  - 由于在我们加锁前，有可能已有线程对 xarray 进行了拆分，需重新检查 `order` 并调用 `xas_split()` 真正拆分旧条目。
- `xas_store(&xas, page)`：
  - 将当前索引处的条目设为此 `page`。
  - 注意：这是在持锁情况下完成的，保证不会与并发截断/回收冲突。
- 成功后：
  - `mapping->nrpages++`：该文件的页缓存计数 +1；
  - 非 huge 页：`__inc_lruvec_page_state(page, NR_FILE_PAGES)`：
    - 最终通过 `__mod_node_page_state()` → `node_page_state_add()`：
      - 更新该 NUMA 节点上的 `NR_FILE_PAGES` 全局统计和 per-node 统计。
- `xas_nomem(&xas, gfp)`：
  - 如果 xarray 内部内存不足，会返回 true，触发 `do {...} while(...)` 再试一次。

### 3.2 错误处理

```c
	if (xas_error(&xas)) {
		error = xas_error(&xas);
		if (charged)
			mem_cgroup_uncharge(page);
		goto error;
	}

	trace_mm_filemap_add_to_page_cache(page);
	return 0;
error:
	page->mapping = NULL;
	/* Leave page->index set: truncation relies upon it */
	put_page(page);
	return error;
}
```

- 如果 xarray 操作出错（`-EEXIST` 或其它错误）：
  - 若已经做过 memcg 计费，则调用 `mem_cgroup_uncharge(page)` 取消；
  - 进入 `error`：
    - 清空 `page->mapping`（表示尚未加入 page cache）；
    - 保留 `page->index` 不变（截断路径可能依赖 index）；
    - `put_page(page)`：撤销前面那次 `get_page()`，使引用计数回退。
- 成功时，返回 0，并打 tracepoint。

---

## 4. workingset_refault() 与 shadow entry

在 `add_to_page_cache_lru()` 中：

```c
if (!(gfp_mask & __GFP_WRITE) && shadow)
	workingset_refault(page, shadow);
```

- `shadow` 非空，意味着：
  - 当前 offset 之前曾经有一个 cache 页被回收；
  - 回收时没有简单“空洞化”，而是留了一个 `shadow` entry 作为“这儿以前有个页”的痕迹。
- 当新页再次插入同一 offset 时：
  - 这是一次“refault”——工作集跟踪用它来估算该页在 LRU 中存活时间、refault 距离等；
  - `workingset_refault()` 利用 `shadow` 中编码的信息，决定：
    - 是否将此页直接加入 active list；
    - 是否认为该页属于“工作集”。
- `!(gfp_mask & __GFP_WRITE)` 排除了写路径：
  - 写请求触发的页插入通常只是为了覆盖写入，不代表热数据；
  - 不希望因为写导致工作集统计被污染。

---

## 5. lru_cache_add()：延迟挂 LRU（pagevec + LRU）

```c
void lru_cache_add(struct page *page)
{
	struct pagevec *pvec;

	VM_BUG_ON_PAGE(PageActive(page) && PageUnevictable(page), page);
	VM_BUG_ON_PAGE(PageLRU(page), page);

	get_page(page);
	local_lock(&lru_pvecs.lock);
	pvec = this_cpu_ptr(&lru_pvecs.lru_add);
	if (pagevec_add_and_need_flush(pvec, page))
		__pagevec_lru_add(pvec);
	local_unlock(&lru_pvecs.lock);
}
```

说明：

- 断言：
  - 不允许一个页同时是 Active 又 Unevictable；
  - 此时页尚未在 LRU 上（`PageLRU(page)` 必须为 0）。
- `get_page(page)`：
  - 再次增加引用计数（为“被 pagevec 暂时持有”增加一份）。
- 使用 per-CPU 的 `lru_pvecs.lru_add`：
  - `pagevec_add_and_need_flush()` 将页加入当前 CPU 的 pagevec；
  - 如果 pagevec 已满，调用 `__pagevec_lru_add()` 立刻 flush。
- `local_lock()` / `local_unlock()`：
  - 使用 per-CPU 自旋锁保护本 CPU 的 pagevec。

### 5.1 __pagevec_lru_add()：flush pagevec，真正挂 LRU

```c
void __pagevec_lru_add(struct pagevec *pvec)
{
	int i;
	struct lruvec *lruvec = NULL;
	unsigned long flags = 0;

	for (i = 0; i < pagevec_count(pvec); i++) {
		struct page *page = pvec->pages[i];

		lruvec = relock_page_lruvec_irqsave(page, lruvec, &flags);
		__pagevec_lru_add_fn(page, lruvec);
	}
	if (lruvec)
		unlock_page_lruvec_irqrestore(lruvec, flags);
	release_pages(pvec->pages, pvec->nr);
	pagevec_reinit(pvec);
}
```

- 对 pagevec 中的每个页：
  - 根据页所属的 `lruvec`（memcg + NUMA 节点）获取锁：`relock_page_lruvec_irqsave()`；
  - 调 `__pagevec_lru_add_fn(page, lruvec)` 将其真正挂到 LRU。
- flush 结束后：
  - 释放最后一个 `lruvec` 锁；
  - `release_pages(pvec->pages, pvec->nr)`：
    - 对每个页做一次 `put_page()`：
      - 与 `lru_cache_add()` 的 `get_page()` 成对，撤销 pagevec 自己的那份引用；
  - `pagevec_reinit(pvec)` 清空 pagevec。

### 5.2 __pagevec_lru_add_fn()：设置 LRU 标志并放入对应 LRU 链表

```c
static void __pagevec_lru_add_fn(struct page *page, struct lruvec *lruvec)
{
	int was_unevictable = TestClearPageUnevictable(page);
	int nr_pages = thp_nr_pages(page);

	VM_BUG_ON_PAGE(PageLRU(page), page);

	SetPageLRU(page);
	smp_mb__after_atomic();

	if (page_evictable(page)) {
		if (was_unevictable)
			__count_vm_events(UNEVICTABLE_PGRESCUED, nr_pages);
	} else {
		ClearPageActive(page);
		SetPageUnevictable(page);
		if (!was_unevictable)
			__count_vm_events(UNEVICTABLE_PGCULLED, nr_pages);
	}

	add_page_to_lru_list(page, lruvec);
	trace_mm_lru_insertion(page);
}
```

说明：

- 若之前是 Unevictable，则先清掉该标志并记录 `was_unevictable`。
- 断言页当前不在 LRU（`PageLRU(page)` 必须为 0）。
- `SetPageLRU(page)` 并发屏障：
  - 标记该页现在属于某个 LRU；
  - `smp_mb__after_atomic()` 与 mlock 路径形成严格顺序，避免“evictable 页卡在 unevictable LRU”的竞态。
- 判断页是否可回收 `page_evictable(page)`：
  - 可回收（evictable）：
    - 如果之前是 unevictable，现在被“救”出来，计数 `UNEVICTABLE_PGRESCUED`。
  - 不可回收：
    - 清除 Active 标志；
    - 设置 Unevictable；
    - 若从可回收变为不可回收，计数 `UNEVICTABLE_PGCULLED`。
- `add_page_to_lru_list(page, lruvec)`：
  - 按照 file/anon、active/inactive、evictable/unevictable 等属性，放到对应的 LRU 链表。
- tracepoint 记录 LRU 插入事件。

---

## 6. 引用计数大致变化（典型场景）

假设：

- 页是新分配的，调用 `add_to_page_cache_lru()` 前 `refcount == 1`（调用者手上的引用）。

典型顺序：

1. `__add_to_page_cache_locked()`：
   - `get_page(page)` → `refcount: 1 → 2`  
     - 可以理解为“page cache 这份引用”；
2. `lru_cache_add()`：
   - `get_page(page)` → `refcount: 2 → 3`  
     - 这份引用由 per-CPU pagevec 持有；
3. `__pagevec_lru_add()` → `release_pages()`：
   - 对每个页 `put_page()` → `refcount: 3 → 2`  
     - 撤销 pagevec 对页的临时引用；
4. 此时：
   - page cache 自身 + 调用者路径 ≈ 2 份引用；
   - 当调用者后续使用完页后 `put_page()` 一次，`refcount: 2 → 1`，只剩 page cache 持有；
   - 再 `delete_from_page_cache()` 时，会在移除 xarray 条目后 `put_page()` 一次，使 `refcount: 1 → 0`，从而进入 `__put_page()`/`free_unref_page()` 真正释放物理页。

上述是简化模型，真实内核中还可能有额外的 get/put（如故障路径、I/O、GUP 等），但核心思想是：

- `__add_to_page_cache_locked()` 为“被 page cache 持有”增加 1；
- `lru_cache_add()` 为“等待挂 LRU”增加 1，之后由 pagevec flush 撤销；
- 最终 page cache 对页的生命周期由 “插入 page cache + delete_from_page_cache() + 其他引用” 共同决定。

---

## 7. 与 delete_from_page_cache() 的对称关系

结合之前你提到的：

- 加入 page cache：`add_to_page_cache_lru()`：
  - 负责：
    - 绑定 `page->mapping/index`；
    - memcg 计费；
    - 插入 `mapping->i_pages`；
    - 更新 `mapping->nrpages` + `NR_FILE_PAGES`；
    - 将页加入 LRU；
    - 更新 workingset（shadow/refault）。
- 删除 page cache：`delete_from_page_cache()`：
  - 负责：
    - 从 xarray 中移除该页（或设置 `shadow` entry）；
    - 从 LRU 中摘掉；
    - 更新 `mapping->nrpages` 和统计；
    - memcg uncharge；
    - `put_page()` 对应的 page cache 引用，必要时触发真正释放。

两者一起，构成了“文件页缓存”在 address_space 中生命周期的核心：**从磁盘读入 → 插入 page cache + LRU → 使用/映射 → 回收/删除**。

---

## 8. 本项目的特殊设计：借用内核代码页作为文件页缓存

本项目的核心目标是：**把内核自身的一页代码（或数据）“借用”给某个普通文件的 page cache，使该文件的某个 offset 直接映射到这块内核代码页**。这样：

- 内存中只有一份物理页，避免拷贝代码或重复存储；
- 用户态只要访问这个文件对应 offset，一次 minor page fault 即可把该内核代码页映射进来执行/访问；
- 内核仍然把这页视为自己的代码页（`PageReserved`），不会作为普通 file cache 被回收。

整体思路是：

- 通过 `get_kernel_code_page(kernel_vaddr)` 找到目标内核虚拟地址对应的 `struct page`（通常是 reserved 的内核 text 页）；
- 用自定义的 `add_page_to_cache()` 把这页挂到 `file->f_mapping->i_pages[index]`；
- 后续通过 `restore_page_cache()` 删除这些借用的 code_page 条目，恢复文件原有的 page cache 视图。

对应的主要函数：

- `get_kernel_code_page()`：从内核虚拟地址解析到 reserved 代码页；
- `add_page_to_cache()`：在 *不存在* 原有 cache 的情况下，把 code_page 挂到 page cache；
- `batch_process_pages()`：批量处理多个 offset/kernel_vaddr，对每页执行“删除原 cache（如有）+ add code_page”；
- `restore_page_cache()` / `batch_restore_pages()`：删除我们注入的 code_page 条目，并清理备份信息；
- `page_backup_info` / `page_backup_manager`：记录哪些 index 被我们修改过，方便恢复。

下面逐条对照实现逻辑和行为（尤其是 refcount / mapcount / LRU），并结合 dmesg 验证。

---

## 9. get_kernel_code_page()：如何拿到内核代码页

路径：`get_kernel_code_page(unsigned long kernel_vaddr)`。

目标：给定内核虚拟地址 `kernel_vaddr`，得到对应的 `struct page *code_page`，并验证这是我们预期的“内核代码页/保留页”。

步骤：

1. **检查地址合法性**
   - `if (!kernel_vaddr) return NULL;`
2. **vmalloc/module 区处理**
   - 如果 `is_vmalloc_addr((void *)kernel_vaddr)` 为真：
     - 使用 `vmalloc_to_page()` 解析；
     - 典型用于 LKM 代码、BPF JIT 等。
3. **直接映射（线性映射）处理**
   - 如果 `virt_addr_valid((void *)kernel_vaddr)` 为真：
     - 使用 `virt_to_page()` 得到页；
     - 对于很多内核 text/data 区，直接映射可行。
4. **core image (__pa_symbol) 路径**
   - 调用 `__pa_symbol(kernel_vaddr)` 得到物理地址，再 `PHYS_PFN` + `pfn_valid()` + `pfn_to_page()`。

成功后的检查：

- 打印并检查：
  - `PageReserved(code_page)`：确认是内核保留页；
  - `mapping == NULL`、`index == 0`、`mapcount == -1`、`refcount == 1` 等；
- `SetPageUptodate(code_page)` 确保被视为 up-to-date；
- 仅返回指针，不额外 `get_page()`，不改变 refcount。

从 dmesg 可以看到典型输出：

- `Code page is reserved: ...`  
- `Code page mapping: 0000000000000000`  
- `Code page refcount: 1`  
- `Code page mapcount: -1`

这说明：我们拿到的是内核代码的 reserved 页，尚未被挂入任何 mapping 或 LRU。

---

## 10. add_page_to_cache()：把内核代码页挂入文件 page cache

路径：`static int add_page_to_cache(struct file *file, pgoff_t index, struct page *new_page)`。

调用场景：

- 在 `batch_process_pages()` 中，对于每个 `(file, index, kernel_vaddr)`：
  - 先 `get_kernel_code_page(kernel_vaddr)` 得到 `code_page`；
  - 再用 `pagecache_get_page(..., FGP_LOCK, 0)` 检查是否已有页：
    - 如果有现有页 `existing_page`：
      - 用 `delete_from_page_cache(existing_page)` + `put_page(existing_page)` 完全删除原文件页；
    - 如果没有页（以及没有留下 shadow），则直接 add。

### 10.1 前置约束与锁

在 `add_page_to_cache()` 内部：

- 断言不是 swap-backed 页：
  ```c
  VM_BUG_ON_PAGE(PageSwapBacked(new_page), new_page);
  ```
  确保只能把 file-backed / reserved 页（如内核代码页）挂入文件 page cache。

- 遵守 PageLocked 约定：
  ```c
  lock_page(new_page);
  ...
  unlock_page(new_page);
  ```
  虽然在我们这个特殊场景下并不会真的与 truncate/invalidate 并发，但保持和内核通用约定一致，避免未来扩展出问题。

### 10.2 使用 xarray 插入，并处理 shadow entry

使用 `XA_STATE` 和 `xas_*` 操作 `mapping->i_pages`：

```c
XA_STATE(xas, &mapping->i_pages, index);
xas_lock(&xas);

existing_page = xas_load(&xas);
if (existing_page) {
    if (!xa_is_value(existing_page)) {
        pr_warn("Page already exists at index %lu, add mode does not overwrite existing cache\n", index);
        ret = -EEXIST;
        goto unlock_xas;
    }
    pr_info("Found shadow entry at index %lu, will overwrite with code page\n", index);
}
```

说明：

- `xas_load()` 返回的 `existing_page` 可能是：
  - 真实的 `struct page *`：说明这个 index 上已有一个有效 cache 页；
  - 一个 `xa_is_value(entry)` 的 shadow entry：workingset 留下的“旧页墓碑”。
- 我们的策略：
  - **真实 page**：当前实现只支持 add 模式，不覆盖已有 cache，返回 `-EEXIST`；
  - **shadow entry**：视为“可覆盖的墓碑”，允许我们直接写入新的 code_page。

随后设置新页的 mapping/index 和状态：

```c
new_page->mapping = mapping;
new_page->index = index;
SetPageUptodate(new_page);
get_page(new_page);          // 为 page cache 增加一份引用
backup_page_info(NULL, index, mapping);

xas_store(&xas, new_page);
if (xas_error(&xas)) { ... }

mapping->nrpages++;
```

关键点：

- `get_page(new_page)`：把 `_refcount` 从 1 增加到 2，表示：
  - 1：内核代码页的原始 base 引用（reserved）；
  - +1：page cache 的持有引用。
- `backup_page_info(NULL, ...)`：
  - 记录这是一次 add 操作；
  - 当前实现不备份原始页（`original_page` 恒为 `NULL`），只备份 index/mapping，供 restore 用。
- `mapping->nrpages++`：
  - 和页表插入对称，保证 `address_space` 内部统计正确。

最后释放 xarray 锁和 page 锁，并做一些调试操作：

- 调用 `get_page_table(filemap_addr)` 检查用户地址对应的 PTE 当前不存在；
- 调 `unmap_mapping_range(mapping, index << PAGE_SHIFT, PAGE_SIZE, 0)` 清理任何可能的旧 PTE；
- 再次 `get_page_table()` 确认 PTE 仍然 not present；
- 打印 `new page refcount` 和 `mapcount`，dmesg 中看到：
  - `new page refcount: 2`；
  - `new page mapcount: -1`。

### 10.3 add 之后 page 的状态小结

对每个被借用的内核代码页 `code_page`：

- 物理页属性：
  - `PageReserved(code_page) == 1`；
  - 不在任何 LRU 上（`PageLRU == 0`）。
- page cache 层：
  - `code_page->mapping = file->f_mapping;`
  - `code_page->index = index;`
  - `mapping->i_pages[index] = code_page;`
  - `mapping->nrpages` 增加 1。
- 引用计数：
  - 原始 base refcount：约为 1（reserved 代码页的内部引用）；
  - add 后 `get_page()` 一次 → `_refcount == 2`（从 dmesg 验证）；
  - 后续不会额外 `get_page()` 或 `put_page()`，直到 restore。
- mapcount：
  - `_mapcount == -1` 始终保持，说明尚未建立任何 PTE；
  - PTE 建立会在用户态第一次访问文件该 offset 时，由通用 filemap fault 路径完成，与本模块解耦。

---

## 11. restore_page_cache()：删除借用的 code_page 条目

路径：`static int restore_page_cache(struct file *file, pgoff_t index)`。

调用场景：

- 在 `batch_restore_pages()` 中，对每个需要恢复的 index 调用 `restore_page_cache(file, index)`；
- 只存在 add 模式：`backup_page_info` 中 `original_page` 恒为 `NULL`。

### 11.1 找到当前页和备份信息

前半部：

```c
struct address_space *mapping = file->f_mapping;
XA_STATE(xas, &mapping->i_pages, index);
...
if (!page_backup_manager.is_active) return -ENOENT;
backup_entry = find_backup_info(index);
if (!backup_entry) return -ENOENT;

xas_lock(&xas);
current_page = xas_load(&xas);
pr_info("xa_load done");
test_page_lru(current_page);       // dmesg: "LRU: not on any LRU"
if (!current_page) { ret = -ENOENT; goto unlock_xas; }
get_page(current_page);
```

说明：

- `find_backup_info(index)` 确认该 index 曾在 add 阶段被修改过；
- `xas_load(&xas)` 得到当前 index 上的页，应当就是之前的 `code_page`；
- `test_page_lru()` 打印 “not on any LRU”，符合我们从未调用过 `lru_cache_add()` 的设计；
- `get_page(current_page)`：为本函数持有一份临时引用：
  - 此时 `_refcount` 从 2 → 3。

### 11.2 删除 page cache 条目并调回 refcount

当前实现只支持 add 模式（不恢复原始页），因此统一走“删除 LKM 页”的路径：

```c
pr_info("Removing added page from add operation\n");

// 从页缓存中删除（使用 xas_store(NULL) 与 add 路径保持一致）
xas_store(&xas, NULL);
if (xas_error(&xas)) { ... }

// 减少页面计数器（删除操作减少了页面数量）
if (mapping->nrpages > 0)
    mapping->nrpages--;

// 减少 LKM 页在 page cache 中的引用
put_page(current_page);

pr_info("Added page removed from cache at index %lu (nrpages: %lu)\n", index, mapping->nrpages);
```

此时：

- `mapping->i_pages[index]` 被置为 NULL，page cache 不再指向 `code_page`；
- `mapping->nrpages` 与 add 阶段对称递减；
- `put_page(current_page)` 把 `_refcount` 从 3 → 2，刚好撤销 page cache 在 add 阶段的那一份引用。

随后解锁 xarray：

```c
unlock_xas:
    xas_unlock(&xas);
```

### 11.3 清理备份信息和本函数临时引用

锁外处理：

```c
if (ret == 0) {
    unmap_mapping_range(mapping, index << PAGE_SHIFT, PAGE_SIZE, 0);

    clear_backup_info(index);      // 标记该 index 不再有备份

    pr_info("current_page refcount: %d\n", atomic_read(&current_page->_refcount));
    pr_info("current_page mapcount: %d\n", atomic_read(&current_page->_mapcount));

    current_page->mapping = NULL;
    current_page->index = 0;
    put_page(current_page);        // 撤销本函数持有的临时引用
    pr_info("Page cache restore completed successfully\n");
}
```

重要几点：

- dmesg 中 `current_page refcount: 2` 恰好对应：
  - 1（原始 base 引用）；
  - +1（本函数临时 `get_page`）；
  - page cache 那一份引用已经在前面的 `put_page(current_page)` 中被撤销；
- 最后的 `put_page(current_page)` 把 `_refcount` 从 2 → 1，使 refcount 回到 **恢复前 add 之前的状态**；
- `current_page->mapping = NULL; index = 0` 恢复为“裸 reserved 页”；
- `_mapcount` 在整个过程中始终是 -1（没有 PTE），符合 dmesg 输出。

因此，整个 add/restore 流程对于 refcount 的净效应是 **0**：

- add 时：`+1`（page cache 持有）；
- restore 时：`-1`（删除 page cache 持有）；
- 净结果：reserved 代码页的 `_refcount` 保持和我们接手前一致（通常为 1）。

---

## 12. LRU 与 memcg/NR_FILE_PAGES：为什么完全不接入回收体系

综合前面的实现，可以看到：

- **不调用 `lru_cache_add()`**
  - `PageLRU(code_page) == 0`，`test_page_lru()` 始终打印 “LRU: not on any LRU”；
  - 页不在 file/anon/unevictable LRU 链表上，reclaim 不会扫描、也不会尝试回收它。

- **不做 memcg 计费**
  - 不调用 `mem_cgroup_charge()`；  
  - 这些页不会被记入任何 cgroup 的 file cache 账本，不会参与 memcg 的回收决策。

- **不更新 `NR_FILE_PAGES`**
  - 不调用 `__inc_lruvec_page_state(page, NR_FILE_PAGES)`；  
  - 全局/节点的 file cache 统计不会包括这部分“内核借用页”，但这更符合它们作为“内核常驻内存”的真实身份。

语义上的好处：

- 保证内核代码页完全不在回收器的候选集合中（既不是 LRU 页，也不是普通 file cache）；
- 不会把这些“不可回收”的页误算进某个 cgroup 的可回收 cache；
- 统计上的偏差（`NR_FILE_PAGES` 略低）与我们的设计目标一致：这部分内存本来就不该被当成“普通 file cache”来回收。

---

## 13. shadow entry 与 workingset：只做兼容，不做统计

正如前面在理论部分所分析的，workingset 会在某些回收路径上在 `mapping->i_pages` 中留下 **shadow entry**（`xa_is_value(entry)`）作为墓碑，用于未来的 refault 统计。

本模块对 shadow 的策略是：

- **不主动创建 shadow entry**
  - 我们不调用 workingset 的相关接口，也不在删除 code_page 时留下自己的 shadow；
  - 删除时直接 `xas_store(&xas, NULL)`。

- **在 add 时对 shadow 做兼容处理**
  - `add_page_to_cache()` 中，如果 `xas_load(&xas)` 得到的是一个 `xa_is_value(entry)` 的 shadow：
    - 把它当作“旧页墓碑”，允许覆盖；
    - 不当成冲突，也不返回 `-EEXIST`。
  - 如果 `xas_load()` 得到的是一个真实的 `page *`：
    - 当前只支持 add 模式，不覆盖现有 page，直接返回 `-EEXIST`，由上层决定是否走其它路径。

这样设计的目的：

- 保证在存在 workingset shadow 的环境下，add 逻辑仍然健壮，不会因为墓碑而拒绝挂 code_page；
- 同时又不引入 workingset 的内部符号（如 `workingset_update_node`、`workingset_refault`），保持模块简单可加载。

---

## 14. 为什么不使用 mapping_set_update()

在核心内核的 page cache 更新路径中（如 `__add_to_page_cache_locked()`），通常会在使用 `XA_STATE` 时调用：

```c
mapping_set_update(&xas, mapping);
```

它的作用是：

- 对非 DAX/shmem 的 mapping：
  - 调用 `xas_set_update(&xas, workingset_update_node)`；
  - 使 workingset 能在节点更新时刷新自身的统计信息（例如 refault 距离）。

在本模块中，我们 **没有** 调用 `mapping_set_update()`，原因有二：

1. **符号可用性问题**
   - `workingset_update_node` 通常不对模块导出（没有 `EXPORT_SYMBOL`）；
   - 在模块中即使包含 `<linux/workingset.h>`，`mapping_set_update()` 宏展开后也会引用该符号，导致模块加载失败。

2. **语义上只影响统计，不影响功能正确性**
   - `mapping_set_update()` 不改变 `i_pages` 中存放的实际对象，不影响 `nrpages`、refcount 或 LRU；
   - 对于我们这种“不进 LRU、不做 workingset 热度统计”的设计，它的缺失只意味着：
     - workingset 无法从这些节点获得额外统计信息；
     - 但不会影响我们对 page cache 行为的预期（add/restore 的正确性）。

因此，本模块选择：

- 在 xarray 层只使用 `XA_STATE` + `xas_lock/load/store/error`；
- 不启用 workingset 的 update 回调。

在论文/汇报中可以说明：

- 我们在锁、数据结构和 refcount 语义上与内核保持一致；
- 出于模块可加载性和项目需求的考虑，有意跳过 workingset 统计相关步骤，这只影响缓存热度统计，不影响功能正确性与安全性。

---

## 15. 综合小结（结合 dmesg 验证）

结合代码和 dmesg，可以得到如下整体结论：

- 对每个 kernel code page：
  - add 前：`refcount == 1`、`mapcount == -1`、`PageReserved == 1`、不在 LRU；
  - add 后：挂入 `mapping->i_pages[index]`，`mapping->nrpages++`，`refcount == 2`、`mapcount == -1`；
  - restore 后：从 `i_pages` 删除条目，`mapping->nrpages--`，`refcount 回到 1`、`mapcount 仍为 -1`、`mapping/index` 复位为 `NULL/0`，始终不进入 LRU。

- 整个过程中：
  - 我们从不把这些 reserved 代码页放入 LRU 或 memcg 记账；
  - 不会触发 `free_unref_page()`，因此不会出现 “freeing reserved page” 的 warning/BUG；
  - page cache 只是一层“借用视图”，本质所有权仍属于内核代码。

这套设计既保持了内核代码页的常驻性质，又通过 page cache 给用户态提供了一个高效、标准的访问入口，适合作为论文中“虚拟化/重定向内核代码到用户态视图”的一个核心案例。 
