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
#define OFFSET 4096
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
void *mapped_addr;
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
int test()
{
    struct nl_msg replace_msg;
    struct restore_msg restore_msg;
    char original_content[PAGE_SIZE];
    char current_content[PAGE_SIZE];
    // 3. 读取原始内容（这会触发页缓存加载）
    printf("\n=== Step 1: Reading original content ===\n");
    // 强制触发页缓存加载
    volatile char *ptr = (volatile char *)mapped_addr;

    memcpy(original_content, mapped_addr, PAGE_SIZE);
    print_memory_content("Original content (first 64 bytes)", original_content, 64);

    // 4. 发送 replace 消息
    printf("\n=== Step 2: Sending replace request ===\n");
    memset(&replace_msg, 0, sizeof(replace_msg));
    strncpy(replace_msg.filepath, FILEPATH, sizeof(replace_msg.filepath) - 1);
    replace_msg.offset = OFFSET;
    replace_msg.addr = (unsigned long)mapped_addr;
    if (send_netlink_message(NETLINK_MODIFY, &replace_msg, sizeof(replace_msg)) < 0) {
        printf("Failed to send replace message\n");
        return -1;
    }

    // 等待一下让内核处理
    printf("Waiting for kernel to process replace request...\n");
    sleep(2);

    // 5. 读取当前内容（应该已经被替换）
    printf("\n=== Step 3: Reading content after replace ===\n");
    memcpy(current_content, mapped_addr, PAGE_SIZE);
    print_memory_content("Current content after replace (first 64 bytes)", current_content, 64);

    // 6. 比较内容是否改变
    if (memcmp(original_content, current_content, PAGE_SIZE) == 0) {
        printf("WARNING: Content appears unchanged after replace operation\n");
    } else {
        printf("SUCCESS: Content has been modified by replace operation\n");
    }

    // 7. 发送 restore 消息
    printf("\n=== Step 4: Sending restore request ===\n");
    memset(&restore_msg, 0, sizeof(restore_msg));
    strncpy(restore_msg.filepath, FILEPATH, sizeof(restore_msg.filepath) - 1);
    restore_msg.offset = OFFSET;

    if (send_netlink_message(NETLINK_RESTORE, &restore_msg, sizeof(restore_msg)) < 0) {
        printf("Failed to send restore message\n");
        return -1;
    }

    // 等待一下让内核处理
    printf("Waiting for kernel to process restore request...\n");
    sleep(2);

    // 8. 读取恢复后的内容
    printf("\n=== Step 5: Reading content after restore ===\n");
    memcpy(current_content, mapped_addr, PAGE_SIZE);
    print_memory_content("Content after restore (first 64 bytes)", current_content, 64);

    // 9. 验证是否恢复到原始内容
    if (memcmp(original_content, current_content, PAGE_SIZE) == 0) {
        printf("SUCCESS: Content has been restored to original state\n");
    } else {
        printf("WARNING: Content restoration may have failed\n");
    }

    printf("\n=== Test completed ===\n");
    return 0;
}

int main(int argc, char **argv) {
    int fd;
    struct stat st;

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

    // 2. 映射文件到内存
    mapped_addr = mmap(NULL, PAGE_SIZE, PROT_READ | PROT_EXEC, MAP_PRIVATE, fd, OFFSET & ~(PAGE_SIZE - 1));
    if (mapped_addr == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return -1;
    }

    if(test() != 0) {
        goto cleanup;
    }
    if(test() != 0) {
        goto cleanup;
    }
    if(test() != 0) {
        goto cleanup;
    }
    if(test() != 0) {
        goto cleanup;
    }
cleanup:
    munmap(mapped_addr, PAGE_SIZE);
    close(fd);
    return 0;
}