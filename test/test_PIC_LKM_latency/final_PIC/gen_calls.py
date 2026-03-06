import random

# 你可以随时在这里增加规模，比如 [8, 16, 32, 64, 128, 512, 1024, 4096]
sizes = [8, 16, 32, 64, 128, 512, 1024, 4096, 8192, 16384] 
MAX_CALLS = max(sizes)

with open("generated_calls.h", "w") as f:
    f.write("// Auto-generated macro benchmark sweep (Randomized Order)\n\n")
    f.write(f"#define MAX_CALLS {MAX_CALLS}\n")
    f.write("static void (*pseudo_got[MAX_CALLS])(void);\n\n")
    
    # 1. 生成空函数
    for i in range(MAX_CALLS):
        f.write(f"static noinline void notrace target_func_{i}(void) {{ asm volatile(\"\"); }}\n")
    
    # 2. 生成初始化 GOT 表的宏
    f.write("\n#define INIT_GOT_TABLE() do { \\\n")
    for i in range(MAX_CALLS):
        f.write(f"    pseudo_got[{i}] = target_func_{i}; \\\n")
    f.write("} while(0)\n\n")
    
    # 3. 生成执行和打印逻辑
    f.write("static void run_all_sizes(void) {\n")
    f.write("    u64 start, end, direct_total, pic_total;\n")
    f.write("    unsigned long flags;\n")
    
    f.write("    pr_info(\"\\n--- Macro-benchmark (Randomized) Results ---\\n\");\n")
    f.write("    pr_info(\"%-6s | %-15s | %-15s | %-10s\\n\", \"Calls\", \"Direct (Avg)\", \"PIC (Avg)\", \"Penalty\");\n")
    f.write("    pr_info(\"----------------------------------------------------------\\n\");\n\n")

    for s in sizes:
        # 核心改动：生成一个打乱的调用序列，模拟真实的跳跃执行
        seq = list(range(s))
        random.shuffle(seq)

        # Direct 调用展开宏（按乱序序列生成）
        f.write(f"    #define RUN_DIRECT_{s}() do {{ \\\n")
        for idx in seq: 
            f.write(f"        target_func_{idx}(); \\\n")
        f.write(f"    }} while(0)\n\n")

        # PIC 调用展开宏（同样的乱序序列，导致 GOT 表被随机跳跃访问）
        f.write(f"    #define RUN_PIC_{s}() do {{ \\\n")
        for idx in seq:
            f.write(f"        {{ void (*fn)(void) = READ_ONCE(pseudo_got[{idx}]); asm volatile(\"\" : \"+r\"(fn)); fn(); }} \\\n")
        f.write(f"    }} while(0)\n\n")

        # 测量的执行逻辑
        f.write(f"    RUN_DIRECT_{s}(); RUN_PIC_{s}(); // Warm-up\n")
        f.write("    preempt_disable(); local_irq_save(flags);\n")
        
        f.write(f"    start = rdtsc_begin(); RUN_DIRECT_{s}(); end = rdtsc_end(); direct_total = end - start;\n")
        f.write(f"    start = rdtsc_begin(); RUN_PIC_{s}(); end = rdtsc_end(); pic_total = end - start;\n")
        
        f.write("    local_irq_restore(flags); preempt_enable();\n")

        # 打印结果
        f.write(f"    pr_info(\"%-6d | %llu (%llu/call) | %llu (%llu/call) | +%lld cycles\\n\", \n")
        f.write(f"            {s}, direct_total, direct_total/{s}, pic_total, pic_total/{s}, \n")
        f.write(f"            (s64)(pic_total/{s}) - (s64)(direct_total/{s}));\n\n")

        # 释放宏定义避免冲突
        f.write(f"    #undef RUN_DIRECT_{s}\n")
        f.write(f"    #undef RUN_PIC_{s}\n\n")

    f.write("}\n")
    
print("generated_calls.h created successfully with randomized execution order!")