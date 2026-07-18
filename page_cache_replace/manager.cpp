// compile: g++ -o manager -std=c++17 -g manager.cpp
// run:
//   sudo ./manager replace <stub-so> <page-map> --hold
//   sudo ./manager restore <stub-so> <page-map>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <sys/socket.h>
#include <linux/netlink.h>
#include <linux/fs.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <errno.h>
#include <fstream>
#include <limits.h>
#include <time.h>
#include <algorithm>
#include <map>
#include <vector>
#include <string>

#define NETLINK_MODIFY 30  // 自定义 Netlink 协议号
#define NETLINK_RESTORE 29  // 恢复操作的 Netlink 协议号
#define MAX_PAGES_PER_OPERATION 256  // 每次操作的最大页面数（需与内核模块保持一致）

// #define PAGE_SIZE 4096
#define PAGE_SIZE 4096
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

struct page_plan_entry {
    loff_t file_offset;
    unsigned long kernel_vaddr;
    std::string kind;
    std::string section;
};

using PageMappingList = std::vector<page_plan_entry>;

static volatile sig_atomic_t g_restore_requested = 0;

static void signal_handler(int) {
    g_restore_requested = 1;
}

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

static std::string dirname_of(const std::string &path) {
    size_t pos = path.find_last_of('/');
    if (pos == std::string::npos) {
        return ".";
    }
    if (pos == 0) {
        return "/";
    }
    return path.substr(0, pos);
}

static std::string executable_dir(const char *argv0) {
    char resolved[PATH_MAX];
    if (realpath(argv0, resolved)) {
        return dirname_of(resolved);
    }
    return source_dir();
}

static std::string runtime_dir_for(const char *argv0) {
    return join_path(executable_dir(argv0), "runtime");
}

static std::string state_path_for(const char *argv0) {
    return join_path(runtime_dir_for(argv0), "manager.state");
}

static std::string pid_path_for(const char *argv0) {
    return join_path(runtime_dir_for(argv0), "manager.pid");
}

static bool ensure_runtime_dir(const char *argv0) {
    std::string dir = runtime_dir_for(argv0);
    if (mkdir(dir.c_str(), 0755) != 0 && errno != EEXIST) {
        perror("mkdir runtime");
        return false;
    }
    return true;
}

static bool write_manager_state(const char *argv0,
                                const char *filepath,
                                const char *page_map_file,
                                bool hold,
                                bool immutable_added) {
    if (!ensure_runtime_dir(argv0)) {
        return false;
    }

    std::string state_path = state_path_for(argv0);
    std::string pid_path = pid_path_for(argv0);
    FILE *state = fopen(state_path.c_str(), "w");
    if (!state) {
        perror("fopen manager.state");
        return false;
    }

    time_t now = time(NULL);
    fprintf(state, "manager_pid=%ld\n", hold ? (long)getpid() : 0L);
    fprintf(state, "stub_so=%s\n", filepath);
    fprintf(state, "page_map=%s\n", page_map_file);
    fprintf(state, "immutable_added=%d\n", immutable_added ? 1 : 0);
    fprintf(state, "created_at=%ld\n", (long)now);
    fclose(state);

    if (hold) {
        FILE *pid = fopen(pid_path.c_str(), "w");
        if (pid) {
            fprintf(pid, "%ld\n", (long)getpid());
            fclose(pid);
        }
    }

    printf("Wrote manager state: %s\n", state_path.c_str());
    return true;
}

static void remove_manager_state(const char *argv0) {
    std::string state_path = state_path_for(argv0);
    std::string pid_path = pid_path_for(argv0);
    unlink(state_path.c_str());
    unlink(pid_path.c_str());
}

static bool protect_file_immutable(const char *filepath, bool *added) {
    int fd = open(filepath, O_RDONLY | O_CLOEXEC);
    int flags = 0;

    *added = false;

    if (fd < 0) {
        perror("open immutable target");
        return false;
    }
    if (ioctl(fd, FS_IOC_GETFLAGS, &flags) != 0) {
        perror("FS_IOC_GETFLAGS");
        close(fd);
        return false;
    }

    if (flags & FS_IMMUTABLE_FL) {
        close(fd);
        printf("Immutable flag was already set on %s\n", filepath);
        return true;
    }
    int new_flags = flags | FS_IMMUTABLE_FL;
    if (ioctl(fd, FS_IOC_SETFLAGS, &new_flags) != 0) {
        perror("set immutable");
        close(fd);
        return false;
    }

    close(fd);
    *added = true;
    printf("Set immutable flag on %s\n", filepath);
    return true;
}

static bool clear_managed_immutable(const char *filepath, bool immutable_added) {
    if (!immutable_added) {
        printf("Preserving pre-existing immutable state on %s\n", filepath);
        return true;
    }

    int fd = open(filepath, O_RDONLY | O_CLOEXEC);
    int flags = 0;
    if (fd < 0) {
        perror("open immutable target");
        return false;
    }
    if (ioctl(fd, FS_IOC_GETFLAGS, &flags) != 0) {
        perror("FS_IOC_GETFLAGS");
        close(fd);
        return false;
    }
    int new_flags = flags & ~FS_IMMUTABLE_FL;
    if (new_flags != flags && ioctl(fd, FS_IOC_SETFLAGS, &new_flags) != 0) {
        perror("clear immutable");
        close(fd);
        return false;
    }
    close(fd);
    printf("Cleared manager-added immutable flag on %s\n", filepath);
    return true;
}

static bool load_managed_immutable_state(const char *argv0,
                                         const char *filepath,
                                         bool *immutable_added) {
    std::ifstream state(state_path_for(argv0));
    std::string line;
    std::string state_filepath;
    bool found = false;

    while (std::getline(state, line)) {
        if (line.rfind("stub_so=", 0) == 0) {
            state_filepath = line.substr(strlen("stub_so="));
        } else if (line.rfind("immutable_added=", 0) == 0) {
            *immutable_added = line.substr(strlen("immutable_added=")) == "1";
            found = true;
        }
    }
    return found && state_filepath == filepath;
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

static bool parse_u64(const char *text,
                      unsigned long long *value,
                      const char *field,
                      size_t line_number,
                      const char *filename) {
    if (text[0] == '-') {
        fprintf(stderr, "Invalid %s '%s' on line %zu in %s\n",
                field, text, line_number, filename);
        return false;
    }
    errno = 0;
    char *end = nullptr;
    unsigned long long parsed = strtoull(text, &end, 0);
    if (errno != 0 || end == text || *trim_whitespace(end) != '\0') {
        fprintf(stderr, "Invalid %s '%s' on line %zu in %s\n",
                field, text, line_number, filename);
        return false;
    }
    *value = parsed;
    return true;
}

bool load_page_mappings(const char *filename, PageMappingList &mappings) {
    FILE *fp = fopen(filename, "r");
    char line[512];
    size_t line_number = 0;
    std::map<loff_t, size_t> seen_offsets;
    std::map<unsigned long, size_t> seen_kernel_pages;

    if (!fp) {
        perror("fopen page map");
        return false;
    }

    mappings.clear();
    while (fgets(line, sizeof(line), fp)) {
        line_number++;
        line[strcspn(line, "\r\n")] = '\0';
        const char *trimmed = trim_whitespace(line);
        if (trimmed[0] == '\0' || trimmed[0] == '#') {
            continue;
        }

        char *comma1 = strchr(line, ',');
        char *comma2 = comma1 ? strchr(comma1 + 1, ',') : nullptr;
        char *comma3 = comma2 ? strchr(comma2 + 1, ',') : nullptr;
        if (!comma1 || !comma2 || !comma3) {
            fprintf(stderr, "Malformed page-map line %zu in %s\n",
                    line_number, filename);
            fclose(fp);
            return false;
        }
        *comma1 = '\0';
        *comma2 = '\0';
        *comma3 = '\0';
        const char *file_offset_text = trim_whitespace(line);
        const char *kernel_vaddr_text = trim_whitespace(comma1 + 1);
        const char *kind = trim_whitespace(comma2 + 1);
        const char *section = trim_whitespace(comma3 + 1);

        if (strchr(section, ',') != nullptr) {
            fprintf(stderr, "Too many fields on page-map line %zu in %s\n",
                    line_number, filename);
            fclose(fp);
            return false;
        }

        unsigned long long file_offset = 0;
        unsigned long long kernel_vaddr = 0;
        if (!parse_u64(file_offset_text, &file_offset, "file offset",
                       line_number, filename) ||
            !parse_u64(kernel_vaddr_text, &kernel_vaddr, "kernel address",
                       line_number, filename)) {
            fclose(fp);
            return false;
        }
        if (file_offset == 0 || file_offset % PAGE_SIZE != 0 ||
            kernel_vaddr == 0 || kernel_vaddr % PAGE_SIZE != 0) {
            fprintf(stderr, "Unaligned or zero page mapping on line %zu in %s\n",
                    line_number, filename);
            fclose(fp);
            return false;
        }
        if (file_offset > static_cast<unsigned long long>(LLONG_MAX) ||
            kernel_vaddr > static_cast<unsigned long long>(ULONG_MAX)) {
            fprintf(stderr, "Page mapping value is out of range on line %zu in %s\n",
                    line_number, filename);
            fclose(fp);
            return false;
        }
        if ((strcmp(kind, "text") != 0 && strcmp(kind, "rodata") != 0) ||
            section[0] == '\0') {
            fprintf(stderr, "Invalid reusable page kind/section on line %zu in %s\n",
                    line_number, filename);
            fclose(fp);
            return false;
        }
        if (seen_offsets.count((loff_t)file_offset) ||
            seen_kernel_pages.count((unsigned long)kernel_vaddr)) {
            fprintf(stderr, "Duplicate file or kernel page on line %zu in %s\n",
                    line_number, filename);
            fclose(fp);
            return false;
        }

        seen_offsets[(loff_t)file_offset] = line_number;
        seen_kernel_pages[(unsigned long)kernel_vaddr] = line_number;
        mappings.push_back({
            (loff_t)file_offset,
            (unsigned long)kernel_vaddr,
            kind,
            section,
        });
    }
    fclose(fp);

    if (mappings.empty()) {
        fprintf(stderr, "No reusable page mappings loaded from %s\n", filename);
        return false;
    }
    std::sort(mappings.begin(), mappings.end(),
              [](const page_plan_entry &a, const page_plan_entry &b) {
                  return a.file_offset < b.file_offset;
              });
    printf("Loaded %zu explicit reusable page mappings from %s\n",
           mappings.size(), filename);
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

static bool validate_page_mappings_for_file(const char *filepath,
                                            const PageMappingList &mappings) {
    struct stat st;
    if (stat(filepath, &st) != 0) {
        perror("stat stub DSO");
        return false;
    }
    for (const auto &entry : mappings) {
        if (entry.file_offset < 0 ||
            entry.file_offset > st.st_size - PAGE_SIZE) {
            fprintf(stderr,
                    "Page mapping file offset 0x%llx is outside %s (size 0x%llx)\n",
                    (unsigned long long)entry.file_offset,
                    filepath,
                    (unsigned long long)st.st_size);
            return false;
        }
    }
    return true;
}

int replace_elf_sections_by_page_info(const char *filepath,
                                      void *mapped_addr,
                                      const PageMappingList &plan) {
    if (plan.empty()) {
        fprintf(stderr, "No explicit page mappings available for replacement\n");
        return -1;
    }

    printf("\n=== Using builder-generated replacement plan ===\n");
    printf("Target file: %s\n", filepath);
    printf("Reusable pages: %zu\n", plan.size());

    std::vector<loff_t> page_offsets;
    std::vector<unsigned long> kernel_vaddrs;
    page_offsets.reserve(plan.size());
    kernel_vaddrs.reserve(plan.size());

    for (size_t idx = 0; idx < plan.size(); ++idx) {
        const auto &entry = plan[idx];
        page_offsets.push_back(entry.file_offset);
        kernel_vaddrs.push_back(entry.kernel_vaddr);

        printf("  [%03zu] file_offset=0x%llx kernel_vaddr=0x%lx kind=%s section=%s\n",
               idx,
               (unsigned long long)entry.file_offset,
               entry.kernel_vaddr,
               entry.kind.c_str(),
               entry.section.c_str());
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
    printf("SUCCESS: ELF section replace completed\n");
    return 0;
}

int restore_elf_sections_by_page_info(const char *filepath,
                                      const PageMappingList &plan) {
    if (plan.empty()) {
        fprintf(stderr, "No explicit page mappings available for restore\n");
        return -1;
    }

    printf("\n=== Using builder-generated restore plan ===\n");
    printf("Target file: %s\n", filepath);
    printf("Reusable pages: %zu\n", plan.size());

    std::vector<loff_t> page_offsets;
    std::vector<unsigned long> kernel_vaddrs;
    page_offsets.reserve(plan.size());
    kernel_vaddrs.reserve(plan.size());

    for (size_t idx = 0; idx < plan.size(); ++idx) {
        const auto &entry = plan[idx];
        page_offsets.push_back(entry.file_offset);
        kernel_vaddrs.push_back(entry.kernel_vaddr);

        printf("  [%03zu] file_offset=0x%llx kernel_vaddr=0x%lx kind=%s section=%s\n",
               idx,
               (unsigned long long)entry.file_offset,
               entry.kernel_vaddr,
               entry.kind.c_str(),
               entry.section.c_str());
    }

    printf("Total unique pages to restore: %zu\n", plan.size());
    dump_page_mappings(page_offsets.data(),
                       kernel_vaddrs.data(),
                       static_cast<int>(plan.size()),
                       "Planned restore mappings");

    printf("\n=== Sending restore batches ===\n");
    if (send_restore_batches(filepath, page_offsets, kernel_vaddrs) < 0) {
        printf("Failed to send restore batches\n");
        return -1;
    }
    
    // 等待一下让内核处理
    printf("Waiting for kernel to process restore request...\n");
    sleep(2);
    
    printf("SUCCESS: ELF section restore completed\n");
    return 0;
}

static void usage(const char *prog) {
    fprintf(stderr,
            "Usage:\n"
            "  %s validate <stub-so> <page-map>\n"
            "  %s replace <stub-so> <page-map> [--hold]\n"
            "  %s restore <stub-so> <page-map>\n"
            "\n"
            "The page map is generated by make_dll and contains exact DSO file\n"
            "offset to runtime kernel virtual page mappings.\n"
            "replace sends page-cache replacement requests. With --hold, the\n"
            "manager stays alive and restores automatically on SIGTERM/SIGINT/SIGHUP.\n"
            "restore sends restore requests and exits.\n",
            prog, prog, prog);
}

int main(int argc, char **argv) {
    int fd;
    int result = 0;
    struct stat st;
    void *mapped_addr = MAP_FAILED;
    const char *command = NULL;
    const char *filepath = NULL;
    const char *page_map_file = NULL;
    bool hold = false;
    bool immutable_added = false;

    if (argc < 4) {
        usage(argv[0]);
        return 1;
    }

    command = argv[1];
    filepath = argv[2];
    page_map_file = argv[3];
    for (int i = 4; i < argc; ++i) {
        if (strcmp(argv[i], "--hold") == 0) {
            hold = true;
        } else {
            fprintf(stderr, "Unknown argument: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (strcmp(command, "validate") != 0 &&
        strcmp(command, "replace") != 0 &&
        strcmp(command, "restore") != 0) {
        fprintf(stderr, "Unknown command: %s\n", command);
        usage(argv[0]);
        return 1;
    }
    if (hold && strcmp(command, "replace") != 0) {
        fprintf(stderr, "--hold is only valid with the replace command.\n");
        usage(argv[0]);
        return 1;
    }
    
    printf("=== ELF Section Replace Tool ===\n");
    printf("Command: %s%s\n", command, hold ? " --hold" : "");
    printf("\nTarget file: %s\n", filepath);
    printf("Page map: %s\n", page_map_file);

    PageMappingList page_mappings;
    if (!load_page_mappings(page_map_file, page_mappings)) {
        fprintf(stderr, "Failed to load explicit page mappings, aborting.\n");
        return -1;
    }
    if (!validate_page_mappings_for_file(filepath, page_mappings)) {
        fprintf(stderr, "Page map does not match the generated DSO, aborting.\n");
        return -1;
    }

    if (strcmp(command, "validate") == 0) {
        printf("SUCCESS: page map is valid for the generated DSO\n");
        return 0;
    }
    if (strlen(filepath) >= sizeof(((struct nl_msg *)nullptr)->filepath)) {
        fprintf(stderr, "Target path is too long for the kernel message: %s\n",
                filepath);
        return 1;
    }

    if (strcmp(command, "restore") == 0) {
        int restore_ret = restore_elf_sections_by_page_info(filepath, page_mappings);
        if (restore_ret == 0) {
            bool managed_immutable = false;
            if (load_managed_immutable_state(argv[0], filepath,
                                             &managed_immutable)) {
                clear_managed_immutable(filepath, managed_immutable);
            } else {
                printf("No matching immutable state; preserving file flags on %s\n",
                       filepath);
            }
            remove_manager_state(argv[0]);
        }
        return restore_ret;
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
            filepath, mapped_addr, page_mappings) < 0) {
        printf("ELF section replace failed\n");
        result = -1;
        goto cleanup;
    }

    printf("\n=== ELF section replace completed successfully ===\n");

    if (!protect_file_immutable(filepath, &immutable_added)) {
        printf("Failed to protect replaced file; restoring before exit\n");
        restore_elf_sections_by_page_info(filepath, page_mappings);
        result = -1;
        goto cleanup;
    }

    if (!write_manager_state(argv[0], filepath, page_map_file,
                             hold, immutable_added)) {
        printf("Failed to write manager state; restoring before exit\n");
        if (restore_elf_sections_by_page_info(filepath, page_mappings) == 0) {
            clear_managed_immutable(filepath, immutable_added);
        }
        result = -1;
        goto cleanup;
    }

    if (hold) {
        signal(SIGTERM, signal_handler);
        signal(SIGINT, signal_handler);
        signal(SIGHUP, signal_handler);

        printf("Holding active replacement session. Send SIGTERM/SIGINT/SIGHUP to restore.\n");
        fflush(stdout);
        while (!g_restore_requested) {
            pause();
        }

        printf("Restore signal received; restoring active replacement session...\n");
        if (restore_elf_sections_by_page_info(filepath, page_mappings) == 0) {
            clear_managed_immutable(filepath, immutable_added);
            remove_manager_state(argv[0]);
        }
        printf("Manager hold session restored and exiting.\n");
    }

cleanup:
    if (mapped_addr != MAP_FAILED) {
        munmap(mapped_addr, st.st_size);
    }
    close(fd);
    return result;
}
