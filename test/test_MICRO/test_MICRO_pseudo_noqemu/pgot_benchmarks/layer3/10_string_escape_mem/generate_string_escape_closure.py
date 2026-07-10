#!/usr/bin/env python3
import argparse
from pathlib import Path


def emit_variant(suffix: str, data_pgot: bool, func_pgot: bool) -> str:
    hex_expr = f"(*pgot_hex_asc_table_{suffix})" if data_pgot else f"pgot_hex_asc_{suffix}"
    data_defs = (
        f"static const char pgot_hex_asc_storage_{suffix}[] __aligned(64) = \"0123456789abcdef\";\n"
        f"const char *pgot_hex_asc_table_{suffix}[1] __aligned(64) = {{ pgot_hex_asc_storage_{suffix} }};\n"
        if data_pgot else
        f"static const char pgot_hex_asc_{suffix}[] __aligned(64) = \"0123456789abcdef\";\n"
    )
    del func_pgot
    return f"""#include <linux/kernel.h>
#include <linux/string.h>
#include <linux/ctype.h>
#include <linux/string_helpers.h>
#include <linux/types.h>

#ifndef __aligned
#define __aligned(x) __attribute__((aligned(x)))
#endif

{data_defs}
#define pgot_hex_asc_hi_{suffix}(x) {hex_expr}[((x) & 0xf0) >> 4]
#define pgot_hex_asc_lo_{suffix}(x) {hex_expr}[((x) & 0x0f)]

static bool pgot_escape_passthrough_{suffix}(unsigned char c, char **dst, char *end)
{{
\tchar *out = *dst;

\tif (out < end)
\t\t*out = c;
\t++out;
\t*dst = out;
\treturn true;
}}

static bool pgot_escape_space_{suffix}(unsigned char c, char **dst, char *end)
{{
\tchar *out = *dst;
\tunsigned char to;

\tswitch (c) {{
\tcase '\\n':
\t\tto = 'n';
\t\tbreak;
\tcase '\\r':
\t\tto = 'r';
\t\tbreak;
\tcase '\\t':
\t\tto = 't';
\t\tbreak;
\tcase '\\v':
\t\tto = 'v';
\t\tbreak;
\tcase '\\f':
\t\tto = 'f';
\t\tbreak;
\tdefault:
\t\treturn false;
\t}}

\tif (out < end)
\t\t*out = '\\\\';
\t++out;
\tif (out < end)
\t\t*out = to;
\t++out;
\t*dst = out;
\treturn true;
}}

static bool pgot_escape_special_{suffix}(unsigned char c, char **dst, char *end)
{{
\tchar *out = *dst;
\tunsigned char to;

\tswitch (c) {{
\tcase '\\\\':
\t\tto = '\\\\';
\t\tbreak;
\tcase '\\a':
\t\tto = 'a';
\t\tbreak;
\tcase '\\e':
\t\tto = 'e';
\t\tbreak;
\tcase '\"':
\t\tto = '\"';
\t\tbreak;
\tdefault:
\t\treturn false;
\t}}

\tif (out < end)
\t\t*out = '\\\\';
\t++out;
\tif (out < end)
\t\t*out = to;
\t++out;
\t*dst = out;
\treturn true;
}}

static bool pgot_escape_null_{suffix}(unsigned char c, char **dst, char *end)
{{
\tchar *out = *dst;

\tif (c)
\t\treturn false;
\tif (out < end)
\t\t*out = '\\\\';
\t++out;
\tif (out < end)
\t\t*out = '0';
\t++out;
\t*dst = out;
\treturn true;
}}

static bool pgot_escape_octal_{suffix}(unsigned char c, char **dst, char *end)
{{
\tchar *out = *dst;

\tif (out < end)
\t\t*out = '\\\\';
\t++out;
\tif (out < end)
\t\t*out = ((c >> 6) & 0x07) + '0';
\t++out;
\tif (out < end)
\t\t*out = ((c >> 3) & 0x07) + '0';
\t++out;
\tif (out < end)
\t\t*out = ((c >> 0) & 0x07) + '0';
\t++out;
\t*dst = out;
\treturn true;
}}

static bool pgot_escape_hex_{suffix}(unsigned char c, char **dst, char *end)
{{
\tchar *out = *dst;

\tif (out < end)
\t\t*out = '\\\\';
\t++out;
\tif (out < end)
\t\t*out = 'x';
\t++out;
\tif (out < end)
\t\t*out = pgot_hex_asc_hi_{suffix}(c);
\t++out;
\tif (out < end)
\t\t*out = pgot_hex_asc_lo_{suffix}(c);
\t++out;
\t*dst = out;
\treturn true;
}}

int pgot_string_escape_mem_{suffix}(const char *src, size_t isz, char *dst,
\t\t\t\t       size_t osz, unsigned int flags,
\t\t\t\t       const char *only)
{{
\tchar *p = dst;
\tchar *end = p + osz;
\tbool is_dict = only && *only;
\tbool is_append = flags & ESCAPE_APPEND;

\twhile (isz--) {{
\t\tunsigned char c = *src++;
\t\tbool in_dict = is_dict && strchr(only, c);

\t\tif (!(is_append || in_dict) && is_dict &&
\t\t    pgot_escape_passthrough_{suffix}(c, &p, end))
\t\t\tcontinue;
\t\tif (!(is_append && in_dict) && isascii(c) && isprint(c) &&
\t\t    flags & ESCAPE_NAP && pgot_escape_passthrough_{suffix}(c, &p, end))
\t\t\tcontinue;
\t\tif (!(is_append && in_dict) && isprint(c) &&
\t\t    flags & ESCAPE_NP && pgot_escape_passthrough_{suffix}(c, &p, end))
\t\t\tcontinue;
\t\tif (!(is_append && in_dict) && isascii(c) &&
\t\t    flags & ESCAPE_NA && pgot_escape_passthrough_{suffix}(c, &p, end))
\t\t\tcontinue;
\t\tif (flags & ESCAPE_SPACE && pgot_escape_space_{suffix}(c, &p, end))
\t\t\tcontinue;
\t\tif (flags & ESCAPE_SPECIAL && pgot_escape_special_{suffix}(c, &p, end))
\t\t\tcontinue;
\t\tif (flags & ESCAPE_NULL && pgot_escape_null_{suffix}(c, &p, end))
\t\t\tcontinue;
\t\tif (flags & ESCAPE_OCTAL && pgot_escape_octal_{suffix}(c, &p, end))
\t\t\tcontinue;
\t\tif (flags & ESCAPE_HEX && pgot_escape_hex_{suffix}(c, &p, end))
\t\t\tcontinue;
\t\tpgot_escape_passthrough_{suffix}(c, &p, end);
\t}}

\treturn p - dst;
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
