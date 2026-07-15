# 手动构建 ELF64 动态库任务说明

  ## 1. 项目目标

  - 不依赖标准编译工具链（gcc / ld 等），通过手动拼接字节构造一个合法的 ELF64 共享库（.so）。
  - 在 x86_64 Linux 上满足：
      - readelf -a 能正常解析文件；
      - nm -D 能列出 symbols.txt 中的所有符号；
      - 可被动态加载器当作普通共享库使用（用于符号 → 地址映射等场景）。
  - 动态库的核心作用是：提供「符号名 → 虚拟地址」映射，再通过固定规则把虚拟地址映射回内核实际地址。
  - 不要求 .text / .rodata 包含真实机器码或真实数据内容，只要大小和布局正确即可（可以全部填零）。

  ## 2. 运行环境与约束

  - 目标平台：x86_64 Linux，ELF64，e_machine = EM_X86_64 (62)。
  - 禁止在构建程序中调用：
      - gcc / ld / objcopy 等工具生成 .so；
      - 任何通过现有工具自动生成 ELF 的方案。
  - 禁止构建程序在运行时：
      - 读取或拷贝模板库 ../make_so/libstub_template_clean.so 的字节，然后「改一改再写回」。
  - 允许：
      - 人工使用 readelf 等工具分析模板库的结构、字段和对齐方式；
      - 在构建程序中把这些结构信息和常量硬编码进去（但不直接拷贝整块二进制）。
  - 构建程序推荐使用 Python 编写（也可以用 C / C++ / Rust 等），只要逻辑清晰、结构可读。

  ## 3. 输入与输出

  ### 3.1 输入文件：symbols.txt

  - 现在仅列出「根模块需要导出的符号名」，每行一个（空白后内容和以 # 开头的注释会被忽略）。
  - 所有根符号必须来自同一个模块；构建器会从 out.krg 中解析地址、大小、kind 与依赖。
  - 行规则：忽略空行；忽略以 # 开头的注释行。
  - 示例（当前仓库中的 symbols.txt）：

    LZ4_compress_HC_continue
    LZ4_compress_HC

  ### 3.2 其他输入

  - out.krg：由 krg.cpp 生成的 SAFE 图（v2，包含 module 信息）。
  - shim.txt（可选）：列出需要由用户态 shim 提供的依赖符号；symbols.txt 显式导出的同名顶层符号仍使用真实内核实现。普通 shim 由 libshim.so 提供；`__x86_indirect_thunk_*` 由构造器在 libkernel.so 原相对地址生成 direct-jump 内置 thunk。

  ### 3.2 输出文件：generated_library.so

  - 默认输出路径：当前目录下的 generated_library.so（允许通过命令行参数自定义）。
  - 输出必须是合法 ELF64 共享库：
      - file generated_library.so 能识别为 ELF 64-bit LSB shared object, x86-64；
      - readelf -a、nm -D 对其操作正常；
      - ELF 头、程序头、节头的字段满足本文件后续规范。

  ### 3.3 自动生成的中间/辅助文件
  - resolved_symbol_addresses.txt：汇总所有构建出的模块符号（符号、地址、大小、所属模块、角色 export/internal/import）。
  - module_deps.txt：模块依赖摘要（形如 A -> kernel: memcpy memset）。
  - 最终 .so 命名规则：根模块生成 lib<module>.so，递归为依赖模块也生成对应 .so；shim 只作为外部依赖，不在此处生成。

  ## 4. 符号分组与地址映射规则

  ### 4.1 符号分组

  - 从 symbols.txt 中读入所有符号后，按 kind 分成两类：
      - 代码符号集合：kind == 0；
      - 只读数据符号集合：kind == 1。
  - 分别按照 address 升序排序，用于决定在各自节中的布局。

  ### 4.2 虚拟地址映射

  目标：在 .so 中构造一套新的虚拟地址空间，使：

  - 每个符号在库中的虚拟地址（st_value）是连续的一段空间，大小等于 size；
  - 同类符号之间（同属 .text 或 .rodata）在库中的相对距离与在内核中的相对距离一致；
  - .text / .rodata / .data 分别落入三个不同的页对齐段，便于通过程序头进行映射。

  具体规则：

  1. 对代码符号：
      - 若存在代码符号集合：
          - min_text_addr = min(address for kind == 0)
      - 定义：
          - .text 虚拟地址基址：TEXT_VADDR_BASE = 0x0000000000001000
          - 对每个符号：
              - rel_text = orig_addr - min_text_addr
              - 虚拟地址：st_value = TEXT_VADDR_BASE + rel_text
              - 对应 .text 节内偏移：rel_text
  2. 对只读数据符号：
      - 若存在只读数据符号集合：
          - min_ro_addr = min(address for kind == 1)
      - .rodata 虚拟地址基址 RODATA_VADDR_BASE 定义为：
          - .text 结束虚拟地址按 4KB（0x1000）对齐后的新一页起始；
      - 对每个符号：
          - rel_ro = orig_addr - min_ro_addr
          - 虚拟地址：st_value = RODATA_VADDR_BASE + rel_ro
          - 对应 .rodata 节内偏移：rel_ro
  3. .data 虚拟地址基址 DATA_VADDR_BASE：
      - 定义为 .rodata 结束虚拟地址按 4KB 对齐后的新一页起始（即 .data 单独占用一个 R/W 段）。

  ### 4.3 节内容

  - .text 节：
      - 大小至少覆盖所有代码符号的范围：
          - text_size = max(rel_text + size) over all 代码符号；
      - 文件内容可全部填充为 0x00，不要求是真实机器指令；
      - 符号在节内区域 [rel_text, rel_text + size) 仅以「占位」形式存在。
  - .rodata 节：
      - 类似 .text，大小覆盖所有只读数据符号范围；
      - 内容可全为 0x00。
  - .data / .bss：
      - .data 可以固定为一个小的常量大小（例如 0x40 字节，全部为零），主要用于放置 .dynamic 之前的对齐区；
      - .bss 为 SHT_NOBITS，文件中不占空间，仅在节头和程序头中体现大小（可以设置为一个固定小值）。

  ## 5. ELF 文件整体布局（文件偏移）

  按文件顺序布局如下（偏移为相对于文件开头的字节数）：

  1. ELF 头：
      - 大小：e_ehsize = 64。
  2. 程序头表（Program Headers）：
      - 4 个条目，每个 e_phentsize = 56 字节，总共 224 字节。
  3. 填充区：
      - 从结尾填充到偏移 0x1000；
      - .text 文件偏移固定为 0x1000，同时满足页对齐要求。
  4. .text 节数据：
      - 文件偏移：TEXT_FILE_OFFSET = 0x1000；
      - 大小：text_size（根据符号布局计算）。
  5. 填充区：
      - 将文件偏移向上对齐到 4KB，作为 .rodata 文件偏移。
  6. .rodata 节数据：
      - 文件偏移：RODATA_FILE_OFFSET（4KB 对齐）；
      - 大小：rodata_size。
  7. 填充区：
      - 将文件偏移向上对齐到 4KB，作为 .data 文件偏移。
  8. .data 节数据：
      - 文件偏移：DATA_FILE_OFFSET（4KB 对齐）；
      - 大小：固定值（如 0x40 字节，全部为 0）。
  9. .bss：
      - 类型为 SHT_NOBITS，不占文件空间，仅在节头与程序头中记录 sh_size / p_memsz。
  10. .dynstr / .dynsym / .gnu.hash / .dynamic：
      - 按顺序紧凑排布在 .data 段之后，注意对齐要求（例如 8 字节对齐）。
  11. .strtab / .symtab：
      - 供调试工具使用，可做最简单的实现：
          - .symtab 中至少包含一个 STN_UNDEF 和一组指向 .text / .rodata 的符号；
          - .strtab 中存放对应的符号名。
  12. .shstrtab：
      - 存放所有节名（.text、.rodata 等）的字符串表。
  13. 节头表（Section Headers）：
      - 12 个节头，e_shentsize = 64，e_shnum = 12；
      - 文件偏移 e_shoff 为前面所有内容结束后的对齐位置。

  ## 6. ELF 头与程序头 / 节头字段规范

  ### 6.1 ELF 头

  - e_ident：
      - 魔数：0x7f 'E' 'L' 'F'；
      - Class：ELFCLASS64；
      - Data：ELFDATA2LSB；
      - Version：EV_CURRENT 等。
  - 关键字段：
      - e_type = ET_DYN (3)；
      - e_machine = EM_X86_64 (62)；
      - e_version = EV_CURRENT (1)；
      - e_entry = TEXT_VADDR_BASE (例如 0x1000)；
      - e_phoff = 64；
      - e_shoff = <由实际布局计算>；
      - e_flags = 0；
      - e_ehsize = 64；
      - e_phentsize = 56，e_phnum = 4；
      - e_shentsize = 64，e_shnum = 12；
      - e_shstrndx = 11（.shstrtab 的节索引）。

  ### 6.2 程序头（4 个）

  - PHDR[0]：代码段
      - p_type = PT_LOAD；
      - p_flags = PF_R | PF_X；
      - p_offset = TEXT_FILE_OFFSET (0x1000)；
      - p_vaddr = TEXT_VADDR_BASE (0x1000)；
      - p_paddr = p_vaddr（可与 p_vaddr 相同）；
      - p_filesz = text_size；
      - p_memsz = 向上按 4KB 对齐；
      - p_align = 0x1000。
  - PHDR[1]：只读数据段
      - p_type = PT_LOAD；
      - p_flags = PF_R；
      - p_offset = RODATA_FILE_OFFSET；
      - p_vaddr = RODATA_VADDR_BASE；
      - 其他字段对应 .rodata 区域。
  - PHDR[2]：数据段
      - p_type = PT_LOAD；
      - p_flags = PF_R | PF_W；
      - 覆盖 .data、.bss、.dynstr、.dynsym、.gnu.hash、.dynamic 等；
      - p_align = 0x1000。
  - PHDR[3]：动态段
      - p_type = PT_DYNAMIC；
      - p_flags = PF_R | PF_W；
      - p_offset / p_vaddr 指向 .dynamic。

  ### 6.3 节头（12 个）

  按索引约定（便于在代码中固定）：

  0. [0]：SHT_NULL（全 0）。
  1. [1] .text
      - sh_type = SHT_PROGBITS；
      - sh_flags = SHF_ALLOC | SHF_EXECINSTR；
      - sh_addr = TEXT_VADDR_BASE；
      - sh_offset = TEXT_FILE_OFFSET；
      - sh_size = text_size；
      - sh_addralign = 0x1000。
  2. [2] .rodata
      - sh_type = SHT_PROGBITS；
      - sh_flags = SHF_ALLOC；
      - sh_addralign = 4（或 0x10）。
  3. [3] .data
      - sh_type = SHT_PROGBITS；
      - sh_flags = SHF_ALLOC | SHF_WRITE；
      - sh_addralign = 0x10。
  4. [4] .bss
      - sh_type = SHT_NOBITS；
      - sh_flags = SHF_ALLOC | SHF_WRITE。
  5. [5] .dynstr
      - sh_type = SHT_STRTAB；
      - sh_flags = SHF_ALLOC；
      - sh_addralign = 1。
  6. [6] .dynsym
      - sh_type = SHT_DYNSYM；
      - sh_flags = SHF_ALLOC；
      - sh_link = 5（指向 .dynstr）；
      - sh_info：本节中本地符号数量（可以简单设置为 1，即保留的 STN_UNDEF）。
  7. [7] .gnu.hash
      - sh_type = SHT_GNU_HASH；
      - sh_flags = SHF_ALLOC；
      - sh_link = 6（指向 .dynsym）。
  8. [8] .dynamic
      - sh_type = SHT_DYNAMIC；
      - sh_flags = SHF_ALLOC | SHF_WRITE；
      - sh_link = 5（指向 .dynstr）。
  9. [9] .strtab
      - sh_type = SHT_STRTAB。
  10. [10] .symtab
      - sh_type = SHT_SYMTAB；
      - sh_link = 9（指向 .strtab）；
      - sh_info：本地符号数量（可根据实现决定）。
  11. [11] .shstrtab
      - sh_type = SHT_STRTAB；
      - sh_addralign = 1。

  ## 7. 动态符号表、字符串表与 GNU 哈希

  ### 7.1 .dynstr（动态字符串表）

  - 第一个字节必须为 0x00，表示空字符串，对应 STN_UNDEF。
  - 之后依次追加所有需要导出的符号名（即 symbols.txt 中的符号名），每个以 \0 结尾。
  - 记录每个符号名在 .dynstr 中的偏移，用于 .dynsym.st_name 字段。

  ### 7.2 .dynsym（动态符号表）

  - 使用 ELF64 符号表结构，条目大小固定为 24 字节。
  - 条目 0：保留的 STN_UNDEF：
      - st_name = 0，st_shndx = SHN_UNDEF，其他字段为 0。
  - 从条目 1 开始为 symbols.txt 中的符号：
      - st_name：符号名在 .dynstr 中的偏移；
      - st_info：
          - 代码符号：STB_GLOBAL | STT_FUNC；
          - 只读数据符号：STB_GLOBAL | STT_OBJECT；
      - st_other = 0；
      - st_shndx：
          - 代码符号：指向 .text 的节索引（1）；
          - 只读数据符号：指向 .rodata 的节索引（2）；
      - st_value：按前述地址映射规则（4.2）计算；
      - st_size：来自 symbols.txt。

  ### 7.3 .gnu.hash（GNU 哈希表）

  - 采用标准 GNU hash 格式，为 .dynsym 中的可见符号生成哈希表。
  - 结构包括：
      - 头部：nbuckets、symoffset、bloom_size、bloom_shift；
      - Bloom filter 区；
      - 桶数组（buckets）；
      - 链表数组（chains）。
  - 可以选择固定的 bloom_size / nbuckets 等常量，根据符号个数计算每个条目，保证：
      - 对于每个导出的符号，动态链接器可以通过 .gnu.hash 找到对应的 .dynsym 条目。

  ### 7.4 .dynamic（动态段）

  - 至少包含以下条目（ELF64 动态结构，每项 16 字节）：
      - DT_GNU_HASH：值为 .gnu.hash 的虚拟地址；
      - DT_STRTAB：值为 .dynstr 的虚拟地址；
      - DT_SYMTAB：值为 .dynsym 的虚拟地址；
      - DT_STRSZ：.dynstr 的总大小（字节数）；
      - DT_SYMENT：单个符号表项大小（24 字节）；
      - DT_NULL：终止条目（tag = 0，val = 0）。

  ## 8. 验证步骤

  构建完成后，采用以下步骤验证：

  1. 结构完整性：
      - readelf -hW generated_library.so
          - 检查 ELF 头、程序头数量、节头数量等是否符合本文件描述；
      - readelf -lW generated_library.so
          - 检查 4 个程序头的类型、权限、对齐是否正确；
      - readelf -SW generated_library.so
          - 检查 .text / .rodata / .data / .bss 等节的偏移、大小、标志。
  2. 动态信息：
      - readelf -dW generated_library.so
          - 确认存在 GNU_HASH、STRTAB、SYMTAB、STRSZ、SYMENT 等条目；
          - 指向的虚拟地址与相应节头的 sh_addr 一致。
  3. 符号验证：
      - nm -D generated_library.so
          - 输出中应包含 symbols.txt 中的全部符号名；
          - 符号的地址与映射规则计算出的值相符。
  4. 可选验证：
      - 尝试使用 LD_PRELOAD=./generated_library.so 运行简单程序，确认动态加载器不拒绝该库。

  ## 9. 实现建议（非强制）

  - 将构建逻辑拆解为清晰的几个步骤：
      1. 解析 symbols.txt，按 kind 分组并排序；
      2. 根据规则计算 .text / .rodata 的大小、虚拟地址与文件偏移；
      3. 设计固定的 ELF/PHDR/SHDR 布局常量；
      4. 先在内存中创建一个足够大的 bytearray，按顺序写入：
          - ELF 头 → 程序头表 → 填充 → 各节数据 → 节头表；
      5. 最后一次性写入 generated_libra
      ry.so。
  - 在代码中为 ELF 头、程序头、节头、符号表等定义结构体或打包函数，避免散落的魔法数字。
