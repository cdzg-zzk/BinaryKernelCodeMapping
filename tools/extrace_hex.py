#!/usr/bin/env python3
import sys
import re
import argparse

def parse_disasm_line(line):
    # 解析行，如：ffffffffc05e1076:  7e 18        jle ...
    match = re.match(r"^\s*([0-9a-fA-F]+):\s+((?:[0-9a-fA-F]{2}\s+)+)", line)
    if match:
        addr = int(match.group(1), 16)
        byte_list = match.group(2).strip().split()
        return addr, byte_list
    return None, None

def extract_binary(input_path, output_path, start_addr, byte_limit=None, end_addr=None):
    byte_array = bytearray()
    collected = 0
    collecting = False

    with open(input_path, 'r') as f:
        for line in f:
            addr, byte_list = parse_disasm_line(line)
            if addr is None:
                continue

            # 开始收集
            if not collecting and addr >= start_addr:
                collecting = True

            if not collecting:
                continue

            for i, b in enumerate(byte_list):
                byte_offset = addr + i
                if byte_offset < start_addr:
                    continue
                if byte_limit is not None and collected >= byte_limit:
                    break
                if end_addr is not None and byte_offset > end_addr:
                    collecting = False
                    break
                byte_array.append(int(b, 16))
                collected += 1

            if (byte_limit is not None and collected >= byte_limit) or (end_addr is not None and not collecting):
                break

    with open(output_path, 'wb') as out_file:
        out_file.write(byte_array)

def main():
    parser = argparse.ArgumentParser(description="从反汇编文本中提取字节码并输出为 .bin 文件")
    parser.add_argument("input_file", help="输入的反汇编文本")
    parser.add_argument("output_file", help="输出的 .bin 文件")
    parser.add_argument("--start", required=True, help="起始地址（十六进制，如 ffffffffc05e1076）", type=lambda x: int(x, 16))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--length", help="提取的字节数", type=int)
    group.add_argument("--end", help="结束地址（十六进制，包含）", type=lambda x: int(x, 16))

    args = parser.parse_args()

    try:
        extract_binary(args.input_file, args.output_file, args.start, args.length, args.end)
        print(f"已生成二进制文件: {args.output_file}")
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()
