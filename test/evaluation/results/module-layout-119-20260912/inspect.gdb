set pagination off
set debuginfod enabled off
x/s linux_banner
p/x (unsigned long)&((struct module*)0)->core_layout
p/x (unsigned long)&((struct module*)0)->init_layout
p/x (unsigned long)&((struct module*)0)->core_layout.base
p/x (unsigned long)&((struct module*)0)->core_layout.size
p/x (unsigned long)&((struct module*)0)->init_layout.base
p/x (unsigned long)&((struct module*)0)->init_layout.size
ptype /o struct module_layout
disassemble /r '/build/linux-3OY0c7/linux-5.15.0/kernel/module.c'::m_show
disassemble /r show_coresize
disassemble /r show_initsize
disassemble /r do_init_module
