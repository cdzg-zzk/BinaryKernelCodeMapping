#!/usr/bin/env python3
import argparse
from pathlib import Path


def emit_variant(suffix: str, data_pgot: bool, func_pgot: bool) -> str:
    hex_expr = f"(*pgot_hex_asc_table_{suffix})" if data_pgot else f"pgot_hex_asc_{suffix}"
    data_defs = (
        f"static const char pgot_hex_asc_storage_{suffix}[] __aligned(64) = \"0123456789abcdef\";\n"
        f"const char *pgot_hex_asc_table_{suffix}[1] __aligned(64) = {{ pgot_hex_asc_storage_{suffix} }};\n"
        f"#define PGOT_HEX_ASC_{suffix} (*pgot_hex_asc_table_{suffix})\n"
        if data_pgot else
        f"static const char pgot_hex_asc_{suffix}[] __aligned(64) = \"0123456789abcdef\";\n"
    )
    del func_pgot
    return f"""#include <linux/kernel.h>
#include <linux/types.h>
#include <linux/ctype.h>
#include <linux/minmax.h>
#include <asm/unaligned.h>

#ifndef __aligned
#define __aligned(x) __attribute__((aligned(x)))
#endif

{data_defs}
#define pgot_hex_asc_hi_{suffix}(x) {hex_expr}[((x) & 0xf0) >> 4]
#define pgot_hex_asc_lo_{suffix}(x) {hex_expr}[((x) & 0x0f)]

int pgot_hex_dump_to_buffer_{suffix}(const void *buf, size_t len,
\t\t\t\t\t    int rowsize, int groupsize,
\t\t\t\t\t    char *linebuf, size_t linebuflen,
\t\t\t\t\t    bool ascii)
{{
\tconst u8 *ptr = buf;
\tint ngroups;
\tu8 ch;
\tint j, lx = 0;
\tint ascii_column;
\tint ret;

\tif (rowsize != 16 && rowsize != 32)
\t\trowsize = 16;
\tif (len > rowsize)
\t\tlen = rowsize;
\tif (!is_power_of_2(groupsize) || groupsize > 8)
\t\tgroupsize = 1;
\tif ((len % groupsize) != 0)
\t\tgroupsize = 1;

\tngroups = len / groupsize;
\tascii_column = rowsize * 2 + rowsize / groupsize + 1;

\tif (!linebuflen)
\t\tgoto overflow1;
\tif (!len)
\t\tgoto nil;

\tif (groupsize == 8) {{
\t\tconst u64 *ptr8 = buf;
\t\tfor (j = 0; j < ngroups; j++) {{
\t\t\tret = snprintf(linebuf + lx, linebuflen - lx,
\t\t\t\t       \"%s%16.16llx\", j ? \" \" : \"\",
\t\t\t\t       get_unaligned(ptr8 + j));
\t\t\tif (ret >= linebuflen - lx)
\t\t\t\tgoto overflow1;
\t\t\tlx += ret;
\t\t}}
\t}} else if (groupsize == 4) {{
\t\tconst u32 *ptr4 = buf;
\t\tfor (j = 0; j < ngroups; j++) {{
\t\t\tret = snprintf(linebuf + lx, linebuflen - lx,
\t\t\t\t       \"%s%8.8x\", j ? \" \" : \"\",
\t\t\t\t       get_unaligned(ptr4 + j));
\t\t\tif (ret >= linebuflen - lx)
\t\t\t\tgoto overflow1;
\t\t\tlx += ret;
\t\t}}
\t}} else if (groupsize == 2) {{
\t\tconst u16 *ptr2 = buf;
\t\tfor (j = 0; j < ngroups; j++) {{
\t\t\tret = snprintf(linebuf + lx, linebuflen - lx,
\t\t\t\t       \"%s%4.4x\", j ? \" \" : \"\",
\t\t\t\t       get_unaligned(ptr2 + j));
\t\t\tif (ret >= linebuflen - lx)
\t\t\t\tgoto overflow1;
\t\t\tlx += ret;
\t\t}}
\t}} else {{
\t\tfor (j = 0; j < len; j++) {{
\t\t\tif (linebuflen < lx + 2)
\t\t\t\tgoto overflow2;
\t\t\tch = ptr[j];
\t\t\tlinebuf[lx++] = pgot_hex_asc_hi_{suffix}(ch);
\t\t\tif (linebuflen < lx + 2)
\t\t\t\tgoto overflow2;
\t\t\tlinebuf[lx++] = pgot_hex_asc_lo_{suffix}(ch);
\t\t\tif (linebuflen < lx + 2)
\t\t\t\tgoto overflow2;
\t\t\tlinebuf[lx++] = ' ';
\t\t}}
\t\tif (j)
\t\t\tlx--;
\t}}
\tif (!ascii)
\t\tgoto nil;

\twhile (lx < ascii_column) {{
\t\tif (linebuflen < lx + 2)
\t\t\tgoto overflow2;
\t\tlinebuf[lx++] = ' ';
\t}}
\tfor (j = 0; j < len; j++) {{
\t\tif (linebuflen < lx + 2)
\t\t\tgoto overflow2;
\t\tch = ptr[j];
\t\tlinebuf[lx++] = (isascii(ch) && isprint(ch)) ? ch : '.';
\t}}
nil:
\tlinebuf[lx] = '\\0';
\treturn lx;
overflow2:
\tlinebuf[lx++] = '\\0';
overflow1:
\treturn ascii ? ascii_column + len : (groupsize * 2 + 1) * ngroups - 1;
}}
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    variants = [
        ("origin", False, False),
        ("data_pgot", True, False),
        ("func_pgot", False, True),
        ("all_pgot", True, True),
    ]
    for suffix, data_pgot, func_pgot in variants:
        (args.out_dir / f"closure_{suffix}.c").write_text(
            emit_variant(suffix, data_pgot, func_pgot)
        )


if __name__ == "__main__":
    main()
