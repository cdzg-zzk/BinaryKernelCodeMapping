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

#define NETLINK_MODIFY 30  // 自定义 Netlink 协议号
#define NETLINK_RESTORE 29  // 恢复操作的 Netlink 协议号

#define FILEPATH "/home/zzk/workspace/KernelCodeMapping/so/libstub.so"
#define OFFSET 0
#define PAGE_SIZE 4096

// Netlink 消息格式
struct nl_msg {
    char filepath[256];
    loff_t offset;
    unsigned long addr;
};

// 恢复请求消息格式
struct restore_msg {
    char filepath[256];
    loff_t offset;
};

// 打印内存内容的辅助函数
void print_memory_content(const char *label, const void *addr, size_t size) {
    printf("%s:\n", label);
    const unsigned char *data = (const unsigned char *)addr;
    for (size_t i = 0; i < size && i < 64; i++) {  // 只打印前64字节
        printf("%02x ", data[i]);
        if ((i + 1) % 16 == 0) printf("\n");
    }
    printf("\n");
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

int main(int argc, char **argv) {
    int fd;
    struct stat st;
    void *mapped_addr;
    struct nl_msg replace_msg;
    struct restore_msg restore_msg;
    char original_content[PAGE_SIZE];
    char current_content[PAGE_SIZE];

    printf("=== Page Cache Replace Test ===\n");
    printf("Target file: %s\n", FILEPATH);
    printf("Target offset: %d\n", OFFSET);

    // 1. 打开文件
    fd = open(FILEPATH, O_RDONLY);
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
    // 直接通过read系统调用读取前64字节
    lseek(fd, OFFSET, SEEK_SET);
    char read_buf[64] = {0};
    ssize_t n = read(fd, read_buf, 64);
    if (n < 0) {
        perror("read");
        close(fd);
        return -1;
    }
    printf("使用read系统调用读取的前64字节内容:\n");
    for (int i = 0; i < n; i++) {
        printf("%02x ", (unsigned char)read_buf[i]);
        if ((i + 1) % 16 == 0) printf("\n");
    }
    printf("\n");
    return 0;

    // 2. 映射文件到内存
    mapped_addr = mmap(NULL, PAGE_SIZE, PROT_READ, MAP_PRIVATE, fd, OFFSET);
    if (mapped_addr == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return -1;
    }

    // 3. 读取原始内容（这会触发页缓存加载）
    printf("\n=== Step 1: Reading original content ===\n");
    
    memcpy(original_content, mapped_addr, PAGE_SIZE);
    print_memory_content("Original content (first 64 bytes)", original_content, 64);
    return 0;
    // 3. 发送 add 消息
    printf("\n=== Step 1: Sending add request ===\n");
    memset(&replace_msg, 0, sizeof(replace_msg));
    strncpy(replace_msg.filepath, FILEPATH, sizeof(replace_msg.filepath) - 1);
    replace_msg.offset = OFFSET;
    replace_msg.addr = (unsigned long)mapped_addr;
    if (send_netlink_message(NETLINK_MODIFY, &replace_msg, sizeof(replace_msg)) < 0) {
        printf("Failed to send add message\n");
        goto cleanup;
    }

    // 等待一下让内核处理
    printf("Waiting for kernel to process add request...\n");
    sleep(2);

    // 4. 读取当前内容（应该已经被替换）
    printf("\n=== Step 2: Reading content after add ===\n");
    memcpy(current_content, mapped_addr, PAGE_SIZE);
    print_memory_content("Current content after add (first 64 bytes)", current_content, 64);

    // // 6. 比较内容是否改变
    // if (memcmp(original_content, current_content, PAGE_SIZE) == 0) {
    //     printf("WARNING: Content appears unchanged after add operation\n");
    // } else {
    //     printf("SUCCESS: Content has been modified by add operation\n");
    // }
    // printf("Press Enter to continue...\n");
    // getchar();

    // 5. 发送 restore 消息
    printf("\n=== Step 3: Sending restore request ===\n");
    memset(&restore_msg, 0, sizeof(restore_msg));
    strncpy(restore_msg.filepath, FILEPATH, sizeof(restore_msg.filepath) - 1);
    restore_msg.offset = OFFSET;

    if (send_netlink_message(NETLINK_RESTORE, &restore_msg, sizeof(restore_msg)) < 0) {
        printf("Failed to send restore message\n");
        goto cleanup;
    }

    // 等待一下让内核处理
    printf("Waiting for kernel to process restore request...\n");
    sleep(2);

    // 6. 读取恢复后的内容
    printf("\n=== Step 4: Reading content after restore ===\n");
    memcpy(original_content, mapped_addr, PAGE_SIZE);
    print_memory_content("Content after restore (first 64 bytes)", original_content, 64);

    // 7. 验证是否恢复到原始内容
    if (memcmp(original_content, current_content, PAGE_SIZE) == 0) {
        printf("WARNING: Content appears unchanged after add operation\n");
    } else {
        printf("SUCCESS: Content has been modified by add operation\n");
    }
    printf("\n=== Test completed ===\n");

cleanup:
    munmap(mapped_addr, PAGE_SIZE);
    close(fd);
    return 0;
}