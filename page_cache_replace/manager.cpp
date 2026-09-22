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
#include <sstream>
#include <limits.h>
#include <time.h>
#include <algorithm>
#include <map>
#include <vector>
#include <string>

#include <poll.h>
#include <sys/random.h>
#include <sys/file.h>
#include "protocol.h"

#define PAGE_SIZE 4096

struct page_plan_entry {
    loff_t file_offset;
    unsigned long kernel_vaddr;
    std::string kind;
    std::string section;
};

using PageMappingList = std::vector<page_plan_entry>;
static std::vector<struct vkso_owner_request> requested_owners;
static unsigned long long active_transaction;
static bool transaction_absent;
static unsigned long long carrier_device, carrier_inode;
static std::string notify_fifo;
static int notify_fd = -1;

static bool notify_session(const char *event, int status) {
    if (notify_fd < 0) return true;
    char message[128];
    int size = snprintf(message, sizeof(message), "%s %d %ld %llu\n", event,
                        status, (long)getpid(), active_transaction);
    ssize_t written;
    do { written = write(notify_fd, message, size); } while (written < 0 && errno == EINTR);
    return written == size;
}


static void test_checkpoint(const char *name) {
    const char *selected = getenv("VKSO_TEST_STOP_AT");
    if (selected && strcmp(selected, name) == 0) {
        fprintf(stderr, "VKSO_TEST_STOP_AT=%s\n", name);
        fflush(nullptr);
        raise(SIGSTOP);
    }
}



struct owner_image_identity {
    std::string symbol, module, build_id;
};
static std::vector<owner_image_identity> owner_images;
static std::string kernel_build_id;

static bool valid_build_id(const std::string &id) {
    return !id.empty() && id.size() <= 128 && id.size() % 2 == 0 &&
        id.find_first_not_of("0123456789abcdef") == std::string::npos;
}

static bool note_build_id(const std::string &path, std::string &id) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) return false;
    std::vector<unsigned char> data((std::istreambuf_iterator<char>(stream)), {});
    size_t offset = 0;
    unsigned matches = 0;
    while (offset < data.size()) {
        if (data.size() - offset < 12) {
            if (std::any_of(data.begin() + offset, data.end(), [](unsigned char c) { return c != 0; }))
                return false;
            break;
        }
        uint32_t namesz, descsz, kind;
        memcpy(&namesz, data.data() + offset, 4);
        memcpy(&descsz, data.data() + offset + 4, 4);
        memcpy(&kind, data.data() + offset + 8, 4);
        size_t name = offset + 12;
        size_t desc = name + ((static_cast<size_t>(namesz) + 3) & ~size_t(3));
        size_t end = desc + ((static_cast<size_t>(descsz) + 3) & ~size_t(3));
        if (end > data.size()) return false;
        if (kind == 3 && namesz == 4 && memcmp(data.data() + name, "GNU\0", 4) == 0) {
            if (!descsz || descsz > 64 || ++matches != 1) return false;
            static const char hex[] = "0123456789abcdef";
            id.clear();
            for (size_t i = desc; i < desc + descsz; ++i) {
                id += hex[data[i] >> 4]; id += hex[data[i] & 15];
            }
        }
        offset = end;
    }
    return matches == 1;
}

static bool load_owner_descriptors(const char *page_map) {
    std::string path(page_map);
    auto slash = path.find_last_of('/');
    path = (slash == std::string::npos ? "." : path.substr(0, slash));
    std::ifstream stream(path + "/owner_descriptors.txt");
    std::ifstream kernel(path + "/kernel_identity.txt");
    if (!stream || !kernel) return false;
    std::string line;
    while (std::getline(stream, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream fields(line);
        std::string name, version, module, build_id, extra;
        if (!(fields >> name >> version >> module >> build_id) || (fields >> extra) ||
            name.size() >= sizeof(vkso_owner_request::symbol) ||
            version.size() >= sizeof(vkso_owner_request::srcversion) ||
            module.empty() || module.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_") != std::string::npos ||
            !valid_build_id(build_id) || requested_owners.size() == VKSO_MAX_OWNERS)
            return false;
        if (std::any_of(owner_images.begin(), owner_images.end(), [&](const owner_image_identity &i) { return i.symbol == name; }))
            return false;
        struct vkso_owner_request entry = {};
        strcpy(entry.symbol, name.c_str());
        strcpy(entry.srcversion, version.c_str());
        requested_owners.push_back(entry);
        owner_images.push_back({name, module, build_id});
    }
    while (std::getline(kernel, line)) {
        if (line.empty() || line[0] == '#') continue;
        std::istringstream fields(line);
        std::string kind, id, extra;
        if (!(fields >> kind >> id) || (fields >> extra) || kind != "kernel" ||
            !valid_build_id(id) || !kernel_build_id.empty()) return false;
        kernel_build_id = id;
    }
    return !kernel_build_id.empty();
}

// BEGIN pins the descriptor owners. Check their linked images while those
// references are held, before sending any source pages to STAGE.
static bool verify_pinned_images() {
    std::string observed;
    if (!note_build_id("/sys/kernel/notes", observed) || observed != kernel_build_id) {
        fprintf(stderr, "VKSO_IMAGE kernel mismatch expected=%s observed=%s phase=after-begin\n",
                kernel_build_id.c_str(), observed.c_str());
        return false;
    }
    printf("VKSO_IMAGE kernel build_id=%s phase=after-begin\n", observed.c_str());
    std::map<std::string, std::vector<std::string>> symbol_modules;
    std::ifstream kallsyms("/proc/kallsyms");
    if (!kallsyms) return false;
    std::string line;
    while (std::getline(kallsyms, line)) {
        std::istringstream fields(line);
        std::string address, type, name, module;
        if (!(fields >> address >> type >> name)) continue;
        if (!std::any_of(owner_images.begin(), owner_images.end(), [&](const owner_image_identity &i) { return i.symbol == name; })) continue;
        fields >> module;
        symbol_modules[name].push_back(module);
    }
    for (const auto &i : owner_images) {
        const auto &modules = symbol_modules[i.symbol];
        if (modules.size() != 1 || modules[0] != "[" + i.module + "]") {
            fprintf(stderr, "VKSO_IMAGE owner mismatch symbol=%s expected_module=%s phase=after-begin\n",
                    i.symbol.c_str(), i.module.c_str());
            return false;
        }
        observed.clear();
        if (!note_build_id("/sys/module/" + i.module + "/notes/.note.gnu.build-id", observed) || observed != i.build_id) {
            fprintf(stderr, "VKSO_IMAGE module=%s mismatch expected=%s observed=%s phase=after-begin\n",
                    i.module.c_str(), i.build_id.c_str(), observed.c_str());
            return false;
        }
        printf("VKSO_IMAGE module=%s symbol=%s build_id=%s phase=after-begin\n",
               i.module.c_str(), i.symbol.c_str(), observed.c_str());
    }
    fflush(stdout);
    return true;
}


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
    const std::string temporary = state_path + ".tmp";
    FILE *state = fopen(temporary.c_str(), "w");
    if (!state) {
        perror("fopen manager.state");
        return false;
    }

    time_t now = time(NULL);
    fprintf(state, "manager_pid=%ld\n", hold ? (long)getpid() : 0L);
    fprintf(state, "process_pid=%ld\nnotify_fifo=%s\n", (long)getpid(), notify_fifo.c_str());
    fprintf(state, "stub_so=%s\n", filepath);
    fprintf(state, "page_map=%s\n", page_map_file);
    fprintf(state, "immutable_added=%d\n", immutable_added ? 1 : 0);
    fprintf(state, "created_at=%ld\n", (long)now);
    fprintf(state, "transaction_id=%llu\n", active_transaction);
    fprintf(state, "carrier_device=%llu\ncarrier_inode=%llu\n", carrier_device, carrier_inode);
    if (fflush(state) || fsync(fileno(state))) { fclose(state); return false; }
    if (fclose(state) || rename(temporary.c_str(), state_path.c_str())) return false;
    int directory = open(runtime_dir_for(argv0).c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
    if (directory < 0) return false;
    int synced = fsync(directory);
    close(directory);
    if (synced) return false;

    if (hold) {
        FILE *pid = fopen(pid_path.c_str(), "w");
        if (!pid) return false;
        fprintf(pid, "%ld\n", (long)getpid());
        if (fclose(pid)) return false;
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

static bool protect_file_immutable(int fd, const char *filepath, int original_flags) {
    if (original_flags & FS_IMMUTABLE_FL) return true;
    int flags = original_flags | FS_IMMUTABLE_FL;
    if (ioctl(fd, FS_IOC_SETFLAGS, &flags)) { perror("set immutable"); return false; }
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
    struct stat st;
    if (fstat(fd, &st) || static_cast<unsigned long long>(st.st_dev) != carrier_device ||
        static_cast<unsigned long long>(st.st_ino) != carrier_inode) {
        fprintf(stderr, "Carrier identity changed; retaining recovery state\n");
        close(fd); return false;
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
        if ((strcmp(kind, "text") != 0 && strcmp(kind, "rodata") != 0 &&
             strcmp(kind, "shared_data") != 0) ||
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
static unsigned long long monotonic_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return static_cast<unsigned long long>(ts.tv_sec) * 1000000000ULL + ts.tv_nsec;
}

static int exchange_result(int fd, int protocol, const void *data, size_t size,
                           unsigned short type, unsigned expected_pages) {
    static unsigned sequence = 0;
    const unsigned seq = ++sequence;
    std::vector<char> request(NLMSG_SPACE(size), 0);
    auto *header = reinterpret_cast<struct nlmsghdr *>(request.data());
    header->nlmsg_len = NLMSG_LENGTH(size);
    header->nlmsg_type = type;
    header->nlmsg_flags = NLM_F_REQUEST;
    header->nlmsg_seq = seq;
    memcpy(NLMSG_DATA(header), data, size);
    struct sockaddr_nl kernel = {};
    kernel.nl_family = AF_NETLINK;
    const auto started = monotonic_ns();
    if (sendto(fd, header, header->nlmsg_len, 0,
               reinterpret_cast<struct sockaddr *>(&kernel), sizeof(kernel)) !=
        static_cast<ssize_t>(header->nlmsg_len)) {
        perror("sendto");
        return -1;
    }
    // A timeout means unknown state, never successful completion or permission
    // to repeat a modifying request. This exchange only negotiates the protocol.
    const auto deadline = monotonic_ns() + 5000000000ULL;
    struct pollfd pending = {fd, POLLIN, 0};
    int ready;
    do {
        const auto now = monotonic_ns();
        if (now >= deadline) { ready = 0; break; }
        ready = poll(&pending, 1, static_cast<int>((deadline - now + 999999) / 1000000));
    } while (ready < 0 && errno == EINTR);
    if (ready <= 0 || !(pending.revents & POLLIN)) {
        fprintf(stderr, "No kernel completion: protocol=%d sequence=%u; state unknown\n", protocol, seq);
        errno = ready == 0 ? ETIMEDOUT : EIO;
        return -1;
    }
    alignas(struct nlmsghdr) char buffer[NLMSG_SPACE(sizeof(struct vkso_result))] = {};
    struct sockaddr_nl sender = {};
    struct iovec iov = {buffer, sizeof(buffer)};
    struct msghdr message = {};
    message.msg_name = &sender;
    message.msg_namelen = sizeof(sender);
    message.msg_iov = &iov;
    message.msg_iovlen = 1;
    ssize_t received;
    do { received = recvmsg(fd, &message, 0); } while (received < 0 && errno == EINTR);
    const auto finished = monotonic_ns();
    const auto *reply = reinterpret_cast<const struct nlmsghdr *>(buffer);
    if (received != NLMSG_LENGTH(sizeof(struct vkso_result)) ||
        (message.msg_flags & MSG_TRUNC) || sender.nl_pid != 0 ||
        sender.nl_family != AF_NETLINK ||
        reply->nlmsg_len != received || reply->nlmsg_seq != seq ||
        reply->nlmsg_type != VKSO_RESULT_V2) {
        fprintf(stderr, "Invalid kernel completion envelope; state unknown\n");
        errno = EPROTO;
        return -1;
    }
    struct vkso_result result;
    memcpy(&result, NLMSG_DATA(reply), sizeof(result));
    if (result.version != VKSO_PROTOCOL_VERSION || result.operation != static_cast<unsigned>(protocol) ||
        result.status > 0 || result.completed > expected_pages ||
        (result.status == 0 && (result.completed != expected_pages || result.failed_page != -1))) {
        fprintf(stderr, "Invalid kernel completion payload; state unknown\n");
        errno = EPROTO;
        return -1;
    }
    printf("VKSO_RESULT version=%u operation=%u sequence=%u hello=%u status=%d completed=%u "
           "failed_page=%d kernel_operation_ns=%llu exchange_wall_ns=%llu\n",
           result.version, result.operation, seq, type == VKSO_HELLO_V2, result.status,
           result.completed, result.failed_page,
           static_cast<unsigned long long>(result.operation_ns), finished - started);
    fflush(stdout);
    if (result.status) {
        fprintf(stderr, "Kernel operation failed: %s; completed prefix=%u, failed page=%d\n",
                strerror(-result.status), result.completed, result.failed_page);
        errno = -result.status;
        return -1;
    }
    return 0;
}

static int transaction_socket() {
    int fd = socket(PF_NETLINK, SOCK_RAW | SOCK_CLOEXEC, NETLINK_MODIFY);
    if (fd < 0) return -1;
    struct sockaddr_nl local = {};
    local.nl_family = AF_NETLINK;
    if (bind(fd, reinterpret_cast<struct sockaddr *>(&local), sizeof(local)) < 0) {
        close(fd); return -1;
    }
    struct nl_msg hello = {};
    if (exchange_result(fd, NETLINK_MODIFY, &hello, sizeof(hello), VKSO_HELLO_V2, 0) < 0) {
        close(fd); return -1;
    }
    return fd;
}

static int tx_exchange(int fd, struct vkso_tx_request &request,
                       struct vkso_tx_result &result, unsigned &seq) {
    static unsigned next_sequence = 1000;
    seq = ++next_sequence;
    std::vector<char> buffer(NLMSG_SPACE(sizeof(request)), 0);
    auto *h = reinterpret_cast<struct nlmsghdr *>(buffer.data());
    h->nlmsg_len = NLMSG_LENGTH(sizeof(request)); h->nlmsg_seq = seq;
    h->nlmsg_type = VKSO_TX_REQUEST; h->nlmsg_flags = NLM_F_REQUEST;
    request.version = VKSO_PROTOCOL_VERSION;
    memcpy(NLMSG_DATA(h), &request, sizeof(request));
    struct sockaddr_nl kernel = {};
    kernel.nl_family = AF_NETLINK;
    auto started = monotonic_ns();
    if (sendto(fd, h, h->nlmsg_len, 0, reinterpret_cast<struct sockaddr *>(&kernel), sizeof(kernel)) !=
        static_cast<ssize_t>(h->nlmsg_len)) return -1;
    const auto deadline = monotonic_ns() + 5000000000ULL;
    while (monotonic_ns() < deadline) {
        struct pollfd pending = {fd, POLLIN, 0};
        const auto now = monotonic_ns();
        if (now >= deadline) break;
        int ready = poll(&pending, 1, static_cast<int>((deadline - now + 999999) / 1000000));
        if (ready < 0 && errno == EINTR) continue;
        if (ready <= 0) break;
        alignas(struct nlmsghdr) char reply_buffer[NLMSG_SPACE(sizeof(result))] = {};
        struct sockaddr_nl sender = {};
        struct iovec iov = {reply_buffer, sizeof(reply_buffer)};
        struct msghdr message = {};
        message.msg_name = &sender; message.msg_namelen = sizeof(sender);
        message.msg_iov = &iov; message.msg_iovlen = 1;
        auto received = recvmsg(fd, &message, 0);
        if (received < 0 && errno == EINTR) continue;
        const auto *reply = reinterpret_cast<const struct nlmsghdr *>(reply_buffer);
        if (received != NLMSG_LENGTH(sizeof(result)) || message.msg_flags & MSG_TRUNC ||
            sender.nl_family != AF_NETLINK || sender.nl_pid || reply->nlmsg_len != received ||
            reply->nlmsg_type != VKSO_TX_RESULT) { errno = EPROTO; return -1; }
        if (reply->nlmsg_seq != seq) continue; // A late ACK from the preceding operation.
        memcpy(&result, NLMSG_DATA(reply), sizeof(result));
        if (result.version != VKSO_PROTOCOL_VERSION || result.transaction != request.transaction ||
            result.operation != request.operation || result.status > 0 ||
            result.state > VKSO_RECOVERY_REQUIRED || result.applied > result.total ||
            result.staged > result.total) { errno = EPROTO; return -1; }
        printf("VKSO_TRANSACTION id=%llu operation=%u sequence=%u status=%d state=%u "
               "total=%u staged=%u applied=%u failed_page=%d kernel_operation_ns=%llu "
               "prepare_ns=%llu apply_ns=%llu release_ns=%llu exchange_wall_ns=%llu\n",
               static_cast<unsigned long long>(result.transaction), result.operation, seq,
               result.status, result.state, result.total, result.staged, result.applied,
               result.failed_page, static_cast<unsigned long long>(result.operation_ns),
               static_cast<unsigned long long>(result.prepare_ns),
               static_cast<unsigned long long>(result.apply_ns),
               static_cast<unsigned long long>(result.release_ns), monotonic_ns() - started);
        fflush(stdout);
        return 0;
    }
    errno = ETIMEDOUT;
    return -1;
}

static int tx_request(int fd, struct vkso_tx_request &r, struct vkso_tx_result &result) {
    unsigned seq;
    if (tx_exchange(fd, r, result, seq) < 0) {
        const int delivery_error = errno;
        fprintf(stderr, "Transaction operation %u has no confirmed reply (%s); querying id=%llu\n",
                r.operation, strerror(delivery_error), static_cast<unsigned long long>(r.transaction));
        struct vkso_tx_request query = {};
        query.operation = VKSO_QUERY; query.transaction = r.transaction;
        unsigned query_seq;
        const int query_ret = tx_exchange(fd, query, result, query_seq);
        // FORGET removes its own result record. A confirmed absence is the
        // successful terminal state when its acknowledgement was lost.
        if (query_ret == 0 && r.operation == VKSO_FORGET &&
            result.status == -ENOENT && result.state == VKSO_UNKNOWN) {
            printf("VKSO_TRANSACTION recovered_absence id=%llu operation=%u\n",
                   static_cast<unsigned long long>(r.transaction), r.operation);
            result.status = 0;
            return 0;
        }
        if (query_ret < 0 || result.status ||
            result.last_operation != r.operation || result.last_sequence != seq) {
            fprintf(stderr, "Transaction state remains unconfirmed; retaining recovery state\n");
            errno = delivery_error; return -1;
        }
        result.status = result.last_status;
        printf("VKSO_TRANSACTION recovered_reply id=%llu operation=%u sequence=%u status=%d\n",
               static_cast<unsigned long long>(r.transaction), r.operation, seq, result.status);
    }
    if (result.status) { errno = -result.status; return -1; }
    return 0;
}

int send_replace_batches(const char *filepath, void *,
                         const std::vector<loff_t> &offsets,
                         const std::vector<unsigned long> &sources,
                         const std::vector<unsigned int> &kinds) {
    if (offsets.size() != sources.size() || offsets.size() != kinds.size() || offsets.size() > UINT_MAX) return -1;
    transaction_absent = true; // No BEGIN has been attempted by this manager.
    int fd = transaction_socket();
    if (fd < 0) return -1;
    struct stat st;
    if (stat(filepath, &st)) { close(fd); return -1; }
    struct vkso_tx_request r = {};
    struct vkso_tx_result result = {};
    r.operation = VKSO_BEGIN; r.transaction = active_transaction;
    r.total = offsets.size(); r.device = st.st_dev; r.inode = st.st_ino;
    strncpy(r.filepath, filepath, sizeof(r.filepath)-1);
    r.owner_count = requested_owners.size();
    std::copy(requested_owners.begin(), requested_owners.end(), r.owners);
    transaction_absent = false;
    int ret = tx_request(fd, r, result);
    if (ret < 0) {
        // A confirmed rejected BEGIN made no binding. Unknown delivery keeps
        // the durable state, since it may name a staged transaction.
        transaction_absent = result.status < 0 && result.state == VKSO_UNKNOWN;
        close(fd); return -1;
    }
    test_checkpoint("begin-confirmed");
    if (!verify_pinned_images()) { close(fd); errno = ESTALE; return -1; }
    for (size_t start = 0; start < offsets.size(); start += MAX_PAGES_PER_OPERATION) {
        r = {}; r.operation = VKSO_STAGE; r.transaction = active_transaction;
        r.total = offsets.size(); r.start = start;
        r.count = std::min<size_t>(MAX_PAGES_PER_OPERATION, offsets.size() - start);
        for (unsigned i = 0; i < r.count; i++) {
            r.pages[i].offset = offsets[start+i]; r.pages[i].source = sources[start+i];
            r.pages[i].kind = kinds[start+i];
        }
        ret = tx_request(fd, r, result);
        if (ret < 0) break;
        test_checkpoint("staged");
    }
    if (ret == 0) {
        r = {}; r.operation = VKSO_COMMIT; r.transaction = active_transaction;
        ret = tx_request(fd, r, result);
        if (ret == 0 && (result.state != VKSO_ACTIVE || result.applied != offsets.size())) {
            errno = EPROTO; ret = -1;
        }
    }
    if (!ret) test_checkpoint("committed");
    close(fd);
    return ret;
}

int send_restore_batches(const char *, const std::vector<loff_t> &,
                         const std::vector<unsigned long> &) {
    if (!active_transaction) { fprintf(stderr, "No transaction ID for recovery\n"); return -1; }
    if (transaction_absent) return 0;
    int fd = transaction_socket();
    if (fd < 0) return -1;
    struct vkso_tx_request r = {};
    struct vkso_tx_result result = {};
    r.operation = VKSO_RELEASE; r.transaction = active_transaction;
    int ret = tx_request(fd, r, result);
    if (ret && result.version == VKSO_PROTOCOL_VERSION &&
        result.transaction == active_transaction && result.status == -ENOENT &&
        result.state == VKSO_UNKNOWN) {
        // A live transaction pins this module. An explicit kernel absence
        // therefore permits cleanup even if the manager died before BEGIN,
        // or the terminal record disappeared on a later module reload.
        printf("Transaction %llu absent; no active bindings to release\n", active_transaction);
        close(fd); return 0;
    }
    if (!ret && (result.applied || (result.state != VKSO_RESTORED && result.state != VKSO_ABORTED))) {
        errno = EPROTO; ret = -1;
    }
    if (!ret) {
        test_checkpoint("released-confirmed");
        r = {}; r.operation = VKSO_FORGET; r.transaction = active_transaction;
        ret = tx_request(fd, r, result);
        if (!ret) {
            transaction_absent = true;
            test_checkpoint("forgotten-confirmed");
        }
    }
    // Keep durable local recovery state if either operation is unconfirmed.
    // After confirmed FORGET a reconnecting RELEASE observes ENOENT, which
    // also permits recovery of flags/state if this process exits here.
    close(fd);
    return ret;
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
    std::vector<unsigned int> page_kinds;
    page_offsets.reserve(plan.size());
    kernel_vaddrs.reserve(plan.size());

    for (size_t idx = 0; idx < plan.size(); ++idx) {
        const auto &entry = plan[idx];
        page_offsets.push_back(entry.file_offset);
        kernel_vaddrs.push_back(entry.kernel_vaddr);
        page_kinds.push_back(entry.kind == "text" ? VKSO_PAGE_TEXT :
                             entry.kind == "rodata" ? VKSO_PAGE_RODATA : VKSO_PAGE_SHARED_DATA);

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
    if (send_replace_batches(filepath, mapped_addr, page_offsets, kernel_vaddrs, page_kinds) < 0) {
        printf("Failed to send replace batches\n");
        return -1;
    }
    
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
    
    
    printf("SUCCESS: ELF section restore completed\n");
    return 0;
}

static void usage(const char *prog) {
    fprintf(stderr,
            "Usage:\n"
            "  %s validate <stub-so> <page-map>\n"
            "  %s replace <stub-so> <page-map> [--hold [--notify-fifo <path>]]\n"
            "  %s restore <stub-so> <page-map>\n"
            "\n"
            "The page map is generated by make_dll and contains exact DSO file\n"
            "offset to runtime kernel virtual page mappings.\n"
            "replace sends page-cache replacement requests. With --hold, the\n"
            "manager stays alive and restores automatically on SIGTERM/SIGINT/SIGHUP.\n"
            "restore sends restore requests and exits.\n",
            prog, prog, prog);
}

static int manager_main(int argc, char **argv) {
    int fd;
    int result = 0;
    struct stat st;
    void *mapped_addr = MAP_FAILED;
    const char *command = NULL;
    const char *filepath = NULL;
    const char *page_map_file = NULL;
    bool hold = false;
    bool immutable_added = false;
    sigset_t hold_signals, previous_mask;

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
        } else if (strcmp(argv[i], "--notify-fifo") == 0 && i + 1 < argc) {
            notify_fifo = argv[++i];
        } else {
            fprintf(stderr, "Unknown argument: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (!notify_fifo.empty()) {
        if (!hold || notify_fifo.find('\n') != std::string::npos) return 1;
        notify_fd = open(notify_fifo.c_str(), O_WRONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW);
        struct stat notification;
        if (notify_fd < 0 || fstat(notify_fd, &notification) || !S_ISFIFO(notification.st_mode)) {
            if (notify_fd >= 0) close(notify_fd);
            notify_fd = -1;
            fprintf(stderr, "Notification destination must be an openable FIFO\n"); return 1;
        }
        signal(SIGPIPE, SIG_IGN);
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

    // One recovery file belongs to one manager session. The kernel itself
    // supports independent transactions; separate runtime directories can use them.
    if (!ensure_runtime_dir(argv[0])) return 1;
    int state_lock = open(join_path(runtime_dir_for(argv[0]), "manager.lock").c_str(),
                          O_CREAT | O_RDWR | O_CLOEXEC, 0600);
    if (state_lock < 0 || flock(state_lock, LOCK_EX | LOCK_NB)) {
        fprintf(stderr, "Another manager owns this runtime directory\n"); return 1;
    }

    if (strcmp(command, "replace") == 0 && !load_owner_descriptors(page_map_file)) {
        fprintf(stderr, "Invalid owner descriptor manifest\n");
        return 1;
    }

    if (strcmp(command, "restore") == 0) {
        std::ifstream state(state_path_for(argv[0]));
        std::string line, saved_path;
        while (std::getline(state, line)) {
            if (line.rfind("transaction_id=", 0) == 0) {
                try { active_transaction = std::stoull(line.substr(15)); }
                catch (...) { return 1; }
            }
            if (line.rfind("stub_so=", 0) == 0) saved_path = line.substr(8);
            try {
                if (line.rfind("carrier_device=", 0) == 0) carrier_device = std::stoull(line.substr(15));
                if (line.rfind("carrier_inode=", 0) == 0) carrier_inode = std::stoull(line.substr(14));
            } catch (...) { return 1; }
        }
        if (!active_transaction || saved_path != filepath) {
            fprintf(stderr, "No matching transaction state for restore\n"); return 1;
        }
        struct stat recovery_st;
        if (!carrier_inode || stat(filepath, &recovery_st) ||
            static_cast<unsigned long long>(recovery_st.st_dev) != carrier_device ||
            static_cast<unsigned long long>(recovery_st.st_ino) != carrier_inode) {
            fprintf(stderr, "Recovery target does not match the saved carrier inode\n"); return 1;
        }
        int restore_ret = restore_elf_sections_by_page_info(filepath, page_mappings);
        if (restore_ret == 0) {
            bool managed_immutable = false;
            if (load_managed_immutable_state(argv[0], filepath,
                                             &managed_immutable)) {
                if (!clear_managed_immutable(filepath, managed_immutable))
                    return -1;
            } else {
                printf("No matching immutable state; preserving file flags on %s\n",
                       filepath);
            }
            remove_manager_state(argv[0]);
        }
        return restore_ret;
    }

    if (access(state_path_for(argv[0]).c_str(), F_OK) == 0) {
        fprintf(stderr, "Existing manager state requires recovery before replacement\n");
        return 1;
    }
    if (getrandom(&active_transaction, sizeof(active_transaction), 0) != sizeof(active_transaction) ||
        !active_transaction) { perror("transaction ID"); return 1; }

    if (hold) {
        sigemptyset(&hold_signals);
        sigaddset(&hold_signals, SIGTERM);
        sigaddset(&hold_signals, SIGINT);
        sigaddset(&hold_signals, SIGHUP);
        signal(SIGTERM, signal_handler);
        signal(SIGINT, signal_handler);
        signal(SIGHUP, signal_handler);
        sigprocmask(SIG_BLOCK, &hold_signals, &previous_mask);
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

    carrier_device = st.st_dev;
    carrier_inode = st.st_ino;
    int original_flags = 0;
    if (ioctl(fd, FS_IOC_GETFLAGS, &original_flags)) { perror("FS_IOC_GETFLAGS"); close(fd); return 1; }
    immutable_added = !(original_flags & FS_IMMUTABLE_FL);
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
    // Persist intended flag ownership before changing the file. Recovery can
    // undo it whether the crash occurs before or after the ioctl or BEGIN.
    if (!write_manager_state(argv[0], filepath, page_map_file, false, immutable_added)) {
        result = -1; goto cleanup;
    }
    if (!notify_session("START", 0)) { remove_manager_state(argv[0]); result = -1; goto cleanup; }
    test_checkpoint("state-persisted");
    if (!protect_file_immutable(fd, filepath, original_flags)) {
        if (clear_managed_immutable(filepath, immutable_added)) remove_manager_state(argv[0]);
        result = -1; goto cleanup;
    }
    test_checkpoint("immutable-set");
    if (replace_elf_sections_by_page_info(filepath, mapped_addr, page_mappings) < 0) {
        fprintf(stderr, "Transaction did not commit; releasing staged/applied resources\n");
        if (restore_elf_sections_by_page_info(filepath, page_mappings) == 0 &&
            clear_managed_immutable(filepath, immutable_added)) remove_manager_state(argv[0]);
        result = -1; goto cleanup;
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
        printf("Holding active replacement session. Send SIGTERM/SIGINT/SIGHUP to restore.\n");
        fflush(stdout);
        if (!notify_session("READY", 0)) g_restore_requested = 1;
        while (!g_restore_requested) {
            sigsuspend(&previous_mask);
        }

        printf("Restore signal received; restoring active replacement session...\n");
        if (restore_elf_sections_by_page_info(filepath, page_mappings) == 0) {
            if (!clear_managed_immutable(filepath, immutable_added)) {
                result = -1;
            } else {
                remove_manager_state(argv[0]);
                printf("Manager hold session restored and exiting.\n");
            }
        } else {
            fprintf(stderr, "Restore failed; retaining manager state for recovery.\n");
            result = -1;
        }
    }

cleanup:
    if (mapped_addr != MAP_FAILED) {
        munmap(mapped_addr, st.st_size);
    }
    close(fd);
    return result;
}

int main(int argc, char **argv) {
    int result = manager_main(argc, argv);
    notify_session("DONE", result);
    if (notify_fd >= 0) close(notify_fd);
    return result;
}
