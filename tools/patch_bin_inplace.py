#!/usr/bin/env python3
import sys
import argparse
import os

def patch_binary_inplace(file_a, file_b, offset):
    # 检查 A 文件是否存在
    if not os.path.isfile(file_a):
        raise FileNotFoundError(f"A 文件不存在：{file_a}")

    # 检查 B 文件是否存在
    if not os.path.isfile(file_b):
        raise FileNotFoundError(f"B 文件不存在：{file_b}")

    with open(file_b, 'rb') as f_b:
        data_b = f_b.read()

    with open(file_a, 'r+b') as f_a:
        f_a.seek(0, os.SEEK_END)
        size_a = f_a.tell()

        if offset + len(data_b) > size_a:
            raise ValueError(f"替换越界：A 文件大小为 {size_a} 字节，但从偏移 {offset} 写入 {len(data_b)} 字节会越界。")

        f_a.seek(offset)
        f_a.write(data_b)

    print(f"✅ 已将 {file_b} 写入 {file_a} 的偏移 {hex(offset)}，修改已生效。")

def main():
    parser = argparse.ArgumentParser(description="直接修改 A 文件内容：从指定偏移处写入 B 文件数据")
    parser.add_argument("file_a", help="要修改的目标文件（A）")
    parser.add_argument("file_b", help="要写入的源文件（B）")
    parser.add_argument("--offset", required=True, help="写入偏移（支持十六进制，如 0x200）")

    args = parser.parse_args()

    try:
        offset = int(args.offset, 0)  # 自动识别十六进制/十进制
        patch_binary_inplace(args.file_a, args.file_b, offset)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
