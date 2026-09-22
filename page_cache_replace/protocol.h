/* Native x86-64 ABI. Legacy structures are used only for safe negotiation. */
#ifndef VKSO_PAGE_PROTOCOL_H
#define VKSO_PAGE_PROTOCOL_H
#include <linux/types.h>
#define NETLINK_MODIFY 30
#define NETLINK_RESTORE 29
#define MAX_PAGES_PER_OPERATION 256
#define VKSO_PROTOCOL_VERSION 4
#define VKSO_REQUEST_V2 0x20
#define VKSO_RESULT_V2 0x21
#define VKSO_HELLO_V2 0x22

#define VKSO_MAX_OWNERS 8
struct vkso_owner_request {
    char symbol[64];
    char srcversion[25];
    unsigned char reserved[7];
};

// Netlink 消息格式 - 支持多页面
struct nl_msg {
    char filepath[256];
    loff_t offset;                 // 起始偏移量（单页面模式）
    unsigned long addr;            // 用户空间地址
    int page_count;                // 页面数量，1表示单页面模式
    loff_t page_offsets[MAX_PAGES_PER_OPERATION];  // 每个页面的偏移量
    unsigned long kernel_vaddrs[MAX_PAGES_PER_OPERATION];  // 每个页面对应的内核虚拟地址
    unsigned int owner_count;
    struct vkso_owner_request owners[VKSO_MAX_OWNERS];
};

// 恢复请求消息格式 - 支持多页面
struct restore_msg {
    char filepath[256];  // 要恢复的文件路径
    loff_t offset;       // 起始偏移量（单页面模式）
    int page_count;      // 要恢复的页面数量，1表示单页面模式
    loff_t page_offsets[MAX_PAGES_PER_OPERATION];  // 每个页面的偏移量
};

struct vkso_result {
    __u32 version;
    __u32 operation;       /* Netlink protocol: MODIFY or RESTORE */
    __s32 status;          /* kernel errno, zero only on complete success */
    __u32 completed;       /* successfully processed prefix of this batch */
    __s32 failed_page;     /* zero-based batch index; -1 for request-level errors */
    __u32 reserved;
    __u64 operation_ns;    /* callback entry through file close, before reply */
};

#define VKSO_TX_REQUEST 0x30
#define VKSO_TX_RESULT 0x31
enum vkso_operation { VKSO_BEGIN = 1, VKSO_STAGE, VKSO_COMMIT,
                      VKSO_QUERY, VKSO_RELEASE, VKSO_FORGET };
enum vkso_state { VKSO_UNKNOWN, VKSO_STAGING, VKSO_ACTIVE, VKSO_ABORTED,
                  VKSO_RESTORED, VKSO_RECOVERY_REQUIRED };
enum vkso_page_kind { VKSO_PAGE_TEXT = 1, VKSO_PAGE_RODATA,
                      VKSO_PAGE_SHARED_DATA };
struct vkso_page_spec {
    __u64 offset, source;
    __u32 kind, reserved;
};
struct vkso_tx_request {
    __u32 version, operation;
    __u64 transaction;
    __u32 total, start, count, owner_count;
    __u64 device, inode;
    char filepath[256];
    struct vkso_owner_request owners[VKSO_MAX_OWNERS];
    struct vkso_page_spec pages[MAX_PAGES_PER_OPERATION];
};
struct vkso_tx_result {
    __u32 version, operation;
    __u64 transaction;
    __s32 status;
    __u32 state, total, staged, applied;
    __s32 failed_page;
    __u32 last_operation, last_sequence;
    __s32 last_status;
    __u32 reserved;
    __u64 operation_ns, prepare_ns, apply_ns, release_ns;
};
#endif
