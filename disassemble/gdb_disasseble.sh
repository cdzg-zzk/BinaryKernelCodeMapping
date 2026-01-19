#!/bin/bash

# === 用户配置 ===
MODNAME="$1"
VMLINUX_PATH="/usr/lib/debug/boot/vmlinux-$(uname -r)"  # 可调整
DUMP_SIZE=0x1000  # 可调整
TMP_GDB_SCRIPT="dump.gdb"
TEXT_BIN="text_section.bin"
DISASM_OUT="$(dirname "$0")/${MODNAME}_disassembly.txt"

# 自动清理 GDB 脚本
trap 'rm -f "$TMP_GDB_SCRIPT"' EXIT

# === 参数检查 ===
if [ -z "$MODNAME" ]; then
  echo "用法: $0 <module_name>"
  exit 1
fi

# === 自动清理 ===
cleanup() {
  rm -f "$TMP_GDB_SCRIPT"
  [ -f "$TEXT_BIN" ] && rm -f "$TEXT_BIN"
}
trap cleanup EXIT

if [ ! -f "$VMLINUX_PATH" ]; then
  echo "错误: 找不到 vmlinux 文件: $VMLINUX_PATH"
  exit 2
fi

# TEXT_ADDR_FILE="/sys/module/$MODNAME/sections/.text"
TEXT_ADDR_FILE="/sys/module/$MODNAME/sections/.init.text"
if [ ! -f "$TEXT_ADDR_FILE" ]; then
  echo "错误: 找不到模块 $MODNAME 的 .text 地址文件：$TEXT_ADDR_FILE"
  exit 3
fi

TEXT_ADDR=$(cat "$TEXT_ADDR_FILE")
echo "[+] 模块 $MODNAME 的 .text 起始地址: $TEXT_ADDR"

# 将十六进制地址转换为十进制
TEXT_ADDR_DEC=$(perl -e "print hex('$TEXT_ADDR')")
echo "[+] 模块 $MODNAME 的 .text 起始地址: $TEXT_ADDR_DEC"

# === 获取架构 ===
ARCH=$(uname -m)
case "$ARCH" in
  x86_64) OBJDUMP_ARCH="i386:x86-64" ;;
  aarch64) OBJDUMP_ARCH="aarch64" ;;
  *) OBJDUMP_ARCH="$ARCH" ;;
esac

# === 生成 GDB 脚本 ===
cat > "$TMP_GDB_SCRIPT" <<EOF
set pagination off
set confirm off
dump memory $TEXT_BIN $TEXT_ADDR $TEXT_ADDR+${DUMP_SIZE}
quit
EOF

echo "[+] 运行 GDB 提取模块 .text 段..."
sudo gdb -q -n -batch "$VMLINUX_PATH" /proc/kcore -x "$TMP_GDB_SCRIPT"

if [ ! -f "$TEXT_BIN" ]; then
  echo "错误: 未能生成内存转储文件 $TEXT_BIN"
  exit 4
fi

echo "[+] Dump 成功，开始反汇编..."

# === 反汇编（不含虚拟地址）===
# objdump -D -b binary -m "$OBJDUMP_ARCH" "$TEXT_BIN" > "$DISASM_OUT"

objdump -D -b binary -m "$OBJDUMP_ARCH" --adjust-vma=$TEXT_ADDR_DEC "$TEXT_BIN" > "$DISASM_OUT"

echo "[+] 反汇编完成，输出保存为 $DISASM_OUT"
echo "✅ 全部完成！"
