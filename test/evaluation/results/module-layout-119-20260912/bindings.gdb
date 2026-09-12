set pagination off
set print elements 0
set debuginfod enabled off
x/s linux_banner
p/x (unsigned long)&((struct module*)0)->list
p/x (unsigned long)&((struct module_kobject*)0)->mod
p/x (unsigned long)&((struct seq_file*)0)->private
p modules_op
p modinfo_coresize
p modinfo_initsize
x/s 0xffffffff825e9aa6
x/s 0xffffffff825e9ac2
x/s 0xffffffff825f885e
