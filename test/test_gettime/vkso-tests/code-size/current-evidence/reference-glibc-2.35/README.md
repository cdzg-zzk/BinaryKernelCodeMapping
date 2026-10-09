# glibc 入口参考源码

来源：本机 `/usr/src/glibc/glibc-2.35`；所列十个源文件按原样保存，版权声明和许可见各文件及 COPYING.LIB。

用途：展示两种方案共同依赖的 libc 入口、vDSO 解析与分派，范围由上级 source-manifest.json 固定。这是 glibc 2.35 参考源码，不证明目标机发行版补丁身份，不计入功能主表，也不将 VKSO 使用公开库视为删除了原 libc 入口。
