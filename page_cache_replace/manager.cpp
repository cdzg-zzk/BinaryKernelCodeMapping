#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <linux/netlink.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <errno.h>
#include <algorithm>
#include <map>
#include <vector>
#include <string>

#define NETLINK_MODIFY 30  // 自定义 Netlink 协议号
#define NETLINK_RESTORE 29  // 恢复操作的 Netlink 协议号
#define MAX_PAGES_PER_OPERATION 100  // 每次操作的最大页面数

// #define PAGE_SIZE 4096
#define PAGE_SIZE 4096
#define REL_FILEPATH "../make_dll/libgenerated_library.so"
#define REL_SYMBOL_ADDR_FILE "../make_dll/resolved_symbol_addresses.txt"

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

struct SymbolAddressEntry {
    std::string name;
    unsigned long address;
    unsigned long size;
};

using SymbolAddressList = std::vector<SymbolAddressEntry>;

static std::string join_path(const std::string &base, const char *suffix) {
    if (base.empty()) {
        return std::string(suffix);
    }
    if (base.back() == '/') {
        return base + suffix;
    }
    return base + "/" + suffix;
}

static std::string source_dir() {
    std::string path(__FILE__);
    size_t pos = path.find_last_of('/');
    if (pos == std::string::npos) {
        return ".";
    }
    return path.substr(0, pos);
}

static std::string default_path(const char *relative_path) {
    return join_path(source_dir(), relative_path);
}

void dump_page_mappings(const loff_t *offsets,
                        const unsigned long *kernel_addrs,
                        int page_count,
                        const char *tag) {
    printf("%s (page_count=%d)\n", tag, page_count);
    for (int idx = 0; idx < page_count; ++idx) {
        printf("  [%03d] file_offset=0x%llx kernel_vaddr=0x%lx\n",
               idx,
               (unsigned long long)offsets[idx],
               kernel_addrs[idx]);
    }
}

static const char *trim_whitespace(char *text) {
    if (!text) {
        return "";
    }
    while (*text == ' ' || *text == '\t') {
        ++text;
    }
    char *end = text + strlen(text);
    while (end > text && (end[-1] == ' ' || end[-1] == '\t')) {
        --end;
    }
    *end = '\0';
    return text;
}

bool load_symbol_addresses(const char *filename, SymbolAddressList &symbol_addresses) {
    FILE *fp = fopen(filename, "r");
    char line[512];
    size_t line_number = 0;

    if (!fp) {
        perror("fopen symbol address file");
        return false;
    }

    symbol_addresses.clear();

    while (fgets(line, sizeof(line), fp)) {
        line_number++;
        line[strcspn(line, "\r\n")] = '\0';
        if (line[0] == '\0') {
            continue;
        }

        char *comma = strchr(line, ',');
        if (!comma) {
            fprintf(stderr,
                    "Skipping malformed line %zu in %s: %s\n",
                    line_number,
                    filename,
                    line);
            continue;
        }

        *comma = '\0';
        const char *symbol_name = trim_whitespace(line);
        char *rest = comma + 1;
        char *comma2 = strchr(rest, ',');
        if (comma2) {
            *comma2 = '\0';
        }
        const char *addr_text = trim_whitespace(rest);
        const char *size_text = comma2 ? trim_whitespace(comma2 + 1) : NULL;

        if (symbol_name[0] == '\0' || addr_text[0] == '\0') {
            fprintf(stderr,
                    "Skipping incomplete line %zu in %s\n",
                    line_number,
                    filename);
            continue;
        }

        errno = 0;
        unsigned long long addr = strtoull(addr_text, nullptr, 16);
        if (errno != 0) {
            fprintf(stderr,
                    "Invalid address '%s' on line %zu in %s\n",
                    addr_text,
                    line_number,
                    filename);
            continue;
        }

        unsigned long long size = 0;
        if (size_text && size_text[0] != '\0') {
            errno = 0;
            size = strtoull(size_text, nullptr, 16);
            if (errno != 0) {
                fprintf(stderr,
                        "Invalid size '%s' on line %zu in %s\n",
                        size_text,
                        line_number,
                        filename);
                continue;
            }
        }

        SymbolAddressEntry entry;
        entry.name = symbol_name;
        entry.address = (unsigned long)addr;
        entry.size = (unsigned long)size;
        symbol_addresses.push_back(entry);
    }

    fclose(fp);

    if (symbol_addresses.empty()) {
        fprintf(stderr, "No symbol addresses loaded from %s\n", filename);
        return false;
    }

    printf("Loaded %zu symbol addresses from %s\n",
           symbol_addresses.size(),
           filename);
    return true;
}

// 替换计划条目
struct page_plan_entry {
    loff_t file_offset;
    unsigned long kernel_vaddr;
    std::vector<std::string> symbols;
};

bool build_page_replacement_plan(const SymbolAddressList &symbol_addresses,
                                 std::vector<page_plan_entry> &plan) {
    std::map<unsigned long, page_plan_entry> page_map;

    for (const auto &entry : symbol_addresses) {
        if (entry.address == 0) {
            continue;
        }

        unsigned long symbol_size = entry.size ? entry.size : 1;
        unsigned long start = entry.address & ~(PAGE_SIZE - 1);
        unsigned long end = (entry.address + symbol_size - 1) & ~(PAGE_SIZE - 1);
        for (unsigned long page_addr = start; page_addr <= end; ) {
            auto &slot = page_map[page_addr];
            slot.kernel_vaddr = page_addr;
            slot.symbols.push_back(entry.name);
            if (page_addr > end - PAGE_SIZE) {
                break;
            }
            page_addr += PAGE_SIZE;
        }
    }

    if (page_map.empty()) {
        fprintf(stderr, "No unique kernel pages found in symbol address file\n");
        return false;
    }

    plan.clear();
    plan.reserve(page_map.size());

    size_t idx = 0;
    for (auto &kv : page_map) {
        // 构建的ELF将页面按内核地址排序写入，因此文件偏移按照顺序映射
        // 因为so的磁盘文件不会有空洞，所以可以直接从[1, ] 开始计算偏移，然后也是按照相对地址，所以for()循环的顺序跟so中symbol出现顺序一致
        kv.second.file_offset = (loff_t)(idx + 1) * PAGE_SIZE;
        plan.push_back(kv.second);
        ++idx;
    }

    printf("Constructed replacement plan for %zu unique pages\n", plan.size());
    return true;
}

// 发送 netlink 消息的通用函数
int send_netlink_message(int protocol, void *data, size_t data_size) {
    struct sockaddr_nl src_addr, dest_addr;
    struct nlmsghdr *nlh = NULL;
    int sock_fd, ret;

    // 创建 Netlink Socket
    sock_fd = socket(PF_NETLINK, SOCK_RAW, protocol);
    if (sock_fd < 0) {
        perror("socket");
        return -1;
    }

    memset(&src_addr, 0, sizeof(src_addr));
    src_addr.nl_family = AF_NETLINK;
    src_addr.nl_pid = getpid();

    if (bind(sock_fd, (struct sockaddr *)&src_addr, sizeof(src_addr)) < 0) {
        perror("bind");
        close(sock_fd);
        return -1;
    }

    memset(&dest_addr, 0, sizeof(dest_addr));
    dest_addr.nl_family = AF_NETLINK;
    dest_addr.nl_pid = 0;
    dest_addr.nl_groups = 0;

    // 构造 Netlink 消息头
    nlh = (struct nlmsghdr *)malloc(NLMSG_SPACE(data_size));
    if (!nlh) {
        perror("malloc");
        close(sock_fd);
        return -1;
    }

    memcpy(NLMSG_DATA(nlh), data, data_size);
    nlh->nlmsg_len = NLMSG_SPACE(data_size);
    nlh->nlmsg_pid = getpid();
    nlh->nlmsg_flags = 0;

    // 发送消息
    ret = sendto(sock_fd, nlh, nlh->nlmsg_len, 0,
                (struct sockaddr *)&dest_addr, sizeof(dest_addr));
    if (ret < 0) {
        perror("sendto");
        free(nlh);
        close(sock_fd);
        return -1;
    }

    printf("Sent netlink message with protocol %d\n", protocol);

    free(nlh);
    close(sock_fd);
    return 0;
}

int send_replace_batches(const char *filepath,
                         void *mapped_addr,
                         const std::vector<loff_t> &page_offsets,
                         const std::vector<unsigned long> &kernel_vaddrs) {
    size_t total_pages = page_offsets.size();
    if (total_pages != kernel_vaddrs.size()) {
        fprintf(stderr, "Page offset and kernel address counts do not match\n");
        return -1;
    }

    size_t total_batches = (total_pages + MAX_PAGES_PER_OPERATION - 1) /
                           MAX_PAGES_PER_OPERATION;

    for (size_t batch_idx = 0; batch_idx < total_batches; ++batch_idx) {
        size_t start = batch_idx * MAX_PAGES_PER_OPERATION;
        size_t batch_pages = std::min(static_cast<size_t>(MAX_PAGES_PER_OPERATION),
                                      total_pages - start);

        struct nl_msg replace_msg;
        memset(&replace_msg, 0, sizeof(replace_msg));
        strncpy(replace_msg.filepath, filepath, sizeof(replace_msg.filepath) - 1);
        replace_msg.offset = page_offsets[start];
        replace_msg.addr = (unsigned long)mapped_addr;
        replace_msg.page_count = static_cast<int>(batch_pages);

        for (size_t i = 0; i < batch_pages; ++i) {
            replace_msg.page_offsets[i] = page_offsets[start + i];
            replace_msg.kernel_vaddrs[i] = kernel_vaddrs[start + i];
        }

        printf("Sending replace batch %zu/%zu (%zu pages)\n",
               batch_idx + 1,
               total_batches,
               batch_pages);
        dump_page_mappings(&replace_msg.page_offsets[0],
                           &replace_msg.kernel_vaddrs[0],
                           replace_msg.page_count,
                           "Netlink replace payload");

        if (send_netlink_message(NETLINK_MODIFY,
                                 &replace_msg,
                                 sizeof(replace_msg)) < 0) {
            return -1;
        }
    }

    return 0;
}

int send_restore_batches(const char *filepath,
                         const std::vector<loff_t> &page_offsets,
                         const std::vector<unsigned long> &kernel_vaddrs) {
    size_t total_pages = page_offsets.size();
    size_t total_batches = (total_pages + MAX_PAGES_PER_OPERATION - 1) /
                           MAX_PAGES_PER_OPERATION;

    for (size_t batch_idx = 0; batch_idx < total_batches; ++batch_idx) {
        size_t start = batch_idx * MAX_PAGES_PER_OPERATION;
        size_t batch_pages = std::min(static_cast<size_t>(MAX_PAGES_PER_OPERATION),
                                      total_pages - start);

        struct restore_msg restore_msg;
        memset(&restore_msg, 0, sizeof(restore_msg));
        strncpy(restore_msg.filepath, filepath, sizeof(restore_msg.filepath) - 1);
        restore_msg.offset = page_offsets[start];
        restore_msg.page_count = static_cast<int>(batch_pages);

        for (size_t i = 0; i < batch_pages; ++i) {
            restore_msg.page_offsets[i] = page_offsets[start + i];
        }

        printf("Sending restore batch %zu/%zu (%zu pages)\n",
               batch_idx + 1,
               total_batches,
               batch_pages);
        dump_page_mappings(&restore_msg.page_offsets[0],
                           &kernel_vaddrs[start],
                           restore_msg.page_count,
                           "Netlink restore payload (addresses shown for reference)");

        if (send_netlink_message(NETLINK_RESTORE,
                                 &restore_msg,
                                 sizeof(restore_msg)) < 0) {
            return -1;
        }
    }

    return 0;
}

// 替换基于符号地址的ELF段
int replace_elf_sections_by_page_info(const char *filepath,
                                      void *mapped_addr,
                                      const SymbolAddressList &symbol_addresses) {
    if (symbol_addresses.empty()) {
        fprintf(stderr, "No symbol addresses available for building replacement plan\n");
        return -1;
    }

    printf("\n=== Building replacement plan from resolved symbols ===\n");
    printf("Target file: %s\n", filepath);
    printf("Resolved symbols: %zu\n", symbol_addresses.size());

    std::vector<page_plan_entry> plan;
    if (!build_page_replacement_plan(symbol_addresses, plan)) {
        fprintf(stderr, "Failed to construct page replacement plan\n");
        return -1;
    }

    std::vector<loff_t> page_offsets;
    std::vector<unsigned long> kernel_vaddrs;
    page_offsets.reserve(plan.size());
    kernel_vaddrs.reserve(plan.size());

    for (size_t idx = 0; idx < plan.size(); ++idx) {
        const auto &entry = plan[idx];
        page_offsets.push_back(entry.file_offset);
        kernel_vaddrs.push_back(entry.kernel_vaddr);

        printf("  [%03zu] file_offset=0x%llx kernel_vaddr=0x%lx symbols:",
               idx,
               (unsigned long long)entry.file_offset,
               entry.kernel_vaddr);
        if (entry.symbols.empty()) {
            printf(" <none>\n");
        } else {
            for (size_t s = 0; s < entry.symbols.size(); ++s) {
                printf(" %s%s",
                       entry.symbols[s].c_str(),
                       (s + 1 == entry.symbols.size()) ? "" : ",");
            }
            printf("\n");
        }
    }

    printf("Total unique pages to replace: %zu\n", plan.size());
    dump_page_mappings(page_offsets.data(),
                       kernel_vaddrs.data(),
                       static_cast<int>(plan.size()),
                       "Planned replace mappings");

    printf("\n=== Sending replace batches ===\n");
    if (send_replace_batches(filepath, mapped_addr, page_offsets, kernel_vaddrs) < 0) {
        printf("Failed to send replace batches\n");
        return -1;
    }
    
    // 等待一下让内核处理
    printf("Waiting for kernel to process replace request...\n");
    sleep(2);
    printf("Press Enter to continue...\n");
    getchar();
    
    printf("\n=== Sending restore batches ===\n");
    if (send_restore_batches(filepath, page_offsets, kernel_vaddrs) < 0) {
        printf("Failed to send restore batches\n");
        return -1;
    }
    
    // 等待一下让内核处理
    printf("Waiting for kernel to process restore request...\n");
    sleep(2);
    
    printf("SUCCESS: ELF section replace completed\n");
    return 0;
}

int main(int argc, char **argv) {
    int fd;
    struct stat st;
    void *mapped_addr;
    std::string default_filepath = default_path(REL_FILEPATH);
    std::string default_symbol_addr = default_path(REL_SYMBOL_ADDR_FILE);
    const char *filepath = default_filepath.c_str();
    const char *symbol_addr_file = default_symbol_addr.c_str();

    printf("=== ELF Section Replace Tool ===\n");
    printf("Usage: %s [filepath] [symbol_addr_file]\n", argv[0]);
    printf("  filepath: target .so file (default: %s)\n", default_filepath.c_str());
    printf("  symbol_addr_file: resolved address file (optional, default: %s)\n",
           default_symbol_addr.c_str());
    printf("Example: %s /path/to/lib.so /path/to/resolved_addresses.txt\n",
           argv[0]);
    
    // 解析命令行参数
    if (argc >= 2) {
        filepath = argv[1];
    }
    if (argc >= 3) {
        symbol_addr_file = argv[2];
    }
    
    printf("\nTarget file: %s\n", filepath);
    printf("Symbol address file: %s\n", symbol_addr_file);

    SymbolAddressList symbol_addresses;
    if (!load_symbol_addresses(symbol_addr_file, symbol_addresses)) {
        fprintf(stderr, "Failed to load symbol addresses, aborting.\n");
        return -1;
    }

    // 1. 打开文件
    fd = open(filepath, O_RDONLY);
    if (fd < 0) {
        perror("open");
        return -1;
    }

    // 获取文件大小
    if (fstat(fd, &st) < 0) {
        perror("fstat");
        close(fd);
        return -1;
    }

    printf("File size: %ld bytes\n", st.st_size);

    // 2. 映射文件到内存
    mapped_addr = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (mapped_addr == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return -1;
    }
    for(int i = 1; i< st.st_size; i+= PAGE_SIZE) {
        printf("page %d: %lx\n", i, (unsigned long)mapped_addr + i);
    }
    // 3. 替换ELF段
    // 使用页面信息文件
    if (replace_elf_sections_by_page_info(
            filepath, mapped_addr, symbol_addresses) < 0) {
        printf("ELF section replace failed\n");
        goto cleanup;
    }

    printf("\n=== ELF section replace completed successfully ===\n");

cleanup:
    munmap(mapped_addr, st.st_size);
    close(fd);
    return 0;
}
