#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/mman.h>
#include <sys/stat.h>

int main()
{
    pid_t pid = getpid();
    printf("当前进程 PID: %d\n", pid);
    getchar();
    // // 清空trace buffer
    // system("echo > /sys/kernel/tracing/trace");
    // system("echo 0 > /sys/kernel/tracing/tracing_on");
    
    // // 设置当前tracer为function_graph以获取更详细的调用栈信息
    // system("echo function_graph > /sys/kernel/tracing/current_tracer");
    
    // // 设置要追踪的函数为sys_read
    // system("echo __x64_sys_mmap > /sys/kernel/tracing/set_graph_function");
    
    // // 设置追踪当前进程
    // char pid_cmd[128];
    // snprintf(pid_cmd, sizeof(pid_cmd), "echo %d > /sys/kernel/tracing/set_ftrace_pid", pid);
    // system(pid_cmd);
    
    // // 开启函数调用栈追踪
    // system("echo 1 > /sys/kernel/tracing/options/func_stack_trace");
    
    // // 设置最大深度
    // system("echo 15 > /sys/kernel/tracing/max_graph_depth");
    
    // // 开启追踪
    system("echo 1 > /sys/kernel/tracing/tracing_on");
    
    // printf("ftrace 设置完成，按 Enter 开始 read 操作...");
    // getchar();
    
    int fd = open("/home/zzk/workspace/KernelCodeMapping/so/Makefile", O_RDONLY);
    if (fd == -1) {
        perror("open");
        return 1;
    }
    void *addr = mmap(NULL, 1024, PROT_READ, MAP_PRIVATE, fd, 0);
    if (addr == MAP_FAILED) {
        perror("mmap");
        return 1;
    }
    printf("mmap addr: %p\n", addr);
    char buff[50] = {0};
    memcpy(buff, addr, 50);
    buff[49] = '\0';
    printf("buff: %s\n", buff);
    munmap(addr, 1024);
    close(fd);
    
    // 停止追踪
    // system("echo 0 > /sys/kernel/tracing/tracing_on");
    
    // // 显示追踪结果
    // printf("\n=== Ftrace 追踪结果 ===\n");
    // // system("cat /sys/kernel/tracing/trace");
    
    // // 清空并关闭ftrace功能
    // system("echo nop > /sys/kernel/tracing/current_tracer");
    // system("echo > /sys/kernel/tracing/set_graph_function");
    // system("echo > /sys/kernel/tracing/set_ftrace_pid");
    // system("echo 0 > /sys/kernel/tracing/options/func_stack_trace");

    return 0;
}