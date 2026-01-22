1. 输入
（1）我们仍然提供symbol.txt，里面依旧只有我们需要的符号名
（2）提供一个out.krg，这里功能跟之前类似，还是通过symbol.txt的符号名查询到所有依赖的符号的基本信息，{addr,size,kind,module}，module也会给出.ko的路径。给你.ko的路径后，相关信息你需要自己获取。并且out.krg能够提供的函数都是无绝对寻址的，已经证明完成。
（3）提供一个shim.txt，里面的符号都会被libshim.so重新实现

2. 输出
（1）首先就是需要借助symbol.txt和out.krg去创建中间文件resolved_symbol_addresses.txt，里面记录了所有依赖的符号的基本信息，out.krg只提供{symbol_name, address, size, module_path}，其他的信息比如is_shim或者role(export/internal/import)你自己获取。LKM 给出运行时的 section 也需要你自己获取，out.krg只提供给你了module_path
（2）最终的产出就是最终的动态库，动态库可以在用户态运行，没有绝对寻址，并且部分函数可用libshim.so中的实现进行替换

3. 基本要求
（1）我们规定：处于kernel模块的所有符号不会出现伪造GOT的情况，其他所有出现的LKM都是存在伪造GOT的情况
（2）我们还规定：目前我们只处理一种情况，就是LKM只依赖kernel和自身，不会依赖其他LKM，这是我们简化的场景，但实际上可能LKM之间会出现相互依赖等情况，你可以预留接口，但是目前我们只处理LKM只依赖其自身以及kernel，不会依赖其他LKM。如果存在其他LKM可以直接报错
（3）symbol.txt中出现的符号是动态库需要导出的符号export，意思是需要给外部使用，而在LKM中伪造GOT出现的是import依赖的符号，意思是需要填入实际运行时地址。其他的就是inter，只供内部使用，RIP/PC rela相对寻址。
（4）我们将LKM的.rela.data转换成so的.rela.dyn的时候（转换伪造GOT），其实并不需要所有条目都有，这是因为我们可能并没有使用到LKM中所有的符号，记不记得resolved_symbol_addresses.txt这里记下来所有依赖的符号，所以将条目与resolved_symbol_addresses.txt中内容进行比较，即可确定哪些需要转换，哪些不需要添加到动态库中
（5）虽然我们有了伪造GOT，但并不是所有的内容都依赖伪造GOT，所以为了兼容，所有代码还是要按照相对位置不变布局，.text*等内容还是跟之前一样制作
