增强的安全性策略 (W^X & MPK)
虽然让用户态执行内核代码听起来有风险，但配合现代硬件特性，它实际上可以很安全。

W^X (Write XOR Execute)： 映射的VMA被设置为只读可执行（RX）。用户程序无法修改这些内核指令，防止了代码篡改。

Intel MPK (Memory Protection Keys)： 利用Intel MPK (PKU) 技术，我们可以将映射的内核代码页标记为仅在特定密钥下可访问。用户程序在调用Stub函数前启用密钥，返回后立即禁用。这实现了进程内的硬件级隔离，防止攻击者利用这些映射页作为ROP（Return-Oriented Programming）攻击的跳板 gadget 。这比传统的动态库更加安全，因为它是按需授权执行的。