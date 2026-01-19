#!/usr/bin/env python3
# vkso_gen_types.py — generate C mirror of ONLY the types needed by a set of functions (from kernel BTF)
# Zero libbpf deps; shells out to `bpftool` and tolerates old bpftool variants.
# Usage:
#   ./vkso_gen_types.py --funcs-file out.krg.safe --out vkso_types.h
#   ./vkso_gen_types.py --funcs klist_add_head,xxh32 --out vkso_types.h
#   ./vkso_gen_types.py --funcs-file symbols.txt --module lz4_compress --module lz4hc_compress --out vkso_types.h
#   [--btf /sys/kernel/btf/vmlinux | --vmlinux /usr/lib/debug/boot/vmlinux-$(uname -r)]
#   [--module /path/to/foo.ko | --module foo | --modules foo,bar]
#   [--bpftool /full/path/to/bpftool]
#   [--module /path/to/foo.ko | --module foo | --modules foo,bar]

import argparse, json, subprocess, sys, os, shutil, platform, struct
from dataclasses import dataclass, field
from typing import Optional

def find_bpftool(explicit):
    if explicit: return explicit
    p = shutil.which("bpftool")
    if p: return p
    rel = platform.uname().release
    for c in (f"/usr/lib/linux-tools-{rel}/bpftool",
              f"/usr/libexec/linux-tools-{rel}/bpftool",
              "/usr/sbin/bpftool","/usr/local/sbin/bpftool","/usr/bin/bpftool"):
        if os.path.exists(c) and os.access(c, os.X_OK): return c
    sys.stderr.write("ERROR: bpftool not found. Install it or pass --bpftool /path/to/bpftool\n")
    sys.stderr.write("  Ubuntu: sudo apt-get install -y bpftool  或  sudo apt-get install -y linux-tools-$(uname -r) linux-tools-common\n")
    return None

def run(bpftool, args):
    cmd = [bpftool] + args
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
    return p.returncode, p.stdout, p.stderr, " ".join(cmd)

def load_btf_json(bpftool, btf_path=None, vmlinux=None):
    """Try multiple json styles:
       1) btf dump file ... -j
       2) -j btf dump file ...
       3) btf dump file ... format json
       Return a list[dict] of types.
    """
    path = vmlinux if vmlinux else (btf_path or "/sys/kernel/btf/vmlinux")
    variants = [
        ["btf","dump","file",path,"-j"],
        ["-j","btf","dump","file",path],
        ["btf","dump","file",path,"format","json"],
    ]
    last_err = ""
    for v in variants:
        rc,out,err,cmd = run(bpftool, v)
        if rc != 0:
            last_err = f"{cmd}\n{err}"
            continue
        try:
            obj = json.loads(out)
            # Some very old bpftool wrap JSON array in a string (!) — try unwrapping once.
            if isinstance(obj, str):
                obj = json.loads(obj)
            # Accept either list[types] or dict with 'types' key
            if isinstance(obj, list):
                return obj
            if isinstance(obj, dict):
                # bpftool sometimes returns {"btf": [...]} or {"types":[...]} — try common keys
                for key in ("types","btf","data","objs"):
                    if key in obj and isinstance(obj[key], list):
                        return obj[key]
                # If dict of many entries that each is a type:
                vals = [v for v in obj.values() if isinstance(v, dict) and "kind" in v]
                if vals: return vals
        except Exception as e:
            last_err = f"{cmd}\n{e}\nstdout:\n{out}\nstderr:\n{err}\n"
            continue
    sys.stderr.write(f"[bpftool json] failed to parse BTF from {path}\n{last_err}\n")
    sys.exit(1)

def build_index(objs):
    by_id = {}
    for o in objs:
        if not isinstance(o, dict):  # defensively skip junk
            continue
        tid = o.get("id")
        if tid is not None:
            by_id[tid] = o
    return by_id

def find_func_proto_id(by_id, name):
    for tid,o in by_id.items():
        if o.get("kind") == "FUNC" and o.get("name") == name:
            return o.get("type_id")  # FUNC_PROTO id
    return None

def _strip_ko_ext(name):
    for ext in (".ko.xz", ".ko.gz", ".ko.zst", ".ko"):
        if name.endswith(ext):
            return name[:-len(ext)]
    return name

def resolve_module_btf_path(mod):
    mod = mod.strip()
    if not mod:
        raise ValueError("empty module path")
    if os.path.exists(mod):
        base = os.path.basename(mod)
        mod_name = _strip_ko_ext(base)
        if mod_name:
            btf_path = f"/sys/kernel/btf/{mod_name}"
            if os.path.exists(btf_path):
                return btf_path
        return mod
    candidates = []
    if "/" not in mod:
        candidates.append(f"/sys/kernel/btf/{mod}")
        if mod.endswith(".ko"):
            candidates.append(f"/sys/kernel/btf/{mod[:-3]}")
    for c in candidates:
        if os.path.exists(c):
            return c
    raise ValueError(f"module BTF not found for '{mod}' (tried {', '.join(candidates)})")

def add_type_closure(by_id, root_id, marked):
    if not root_id or root_id in marked: return
    marked.add(root_id)
    o = by_id.get(root_id)
    if not o: return
    k = o.get("kind")
    if k in ("TYPEDEF","CONST","VOLATILE","RESTRICT"):
        add_type_closure(by_id, o.get("type_id"), marked); return
    if k == "PTR":
        add_type_closure(by_id, o.get("type_id"), marked); return
    if k == "ARRAY":
        add_type_closure(by_id, o.get("elem_type_id"), marked); return
    if k in ("STRUCT","UNION"):
        for m in (o.get("members") or []):
            add_type_closure(by_id, m.get("type_id"), marked)
        return
    if k in ("ENUM","ENUM64"):
        return
    if k == "FUNC_PROTO":
        add_type_closure(by_id, o.get("ret_type_id"), marked)
        for p in (o.get("params") or []):
            add_type_closure(by_id, p.get("type_id"), marked)
        return
    if k == "FUNC":
        add_type_closure(by_id, o.get("type_id"), marked); return
    # VAR / DATASEC / SEC etc. ignored

import re

SAFE_KRG_MAGIC = 0x3147524B  # 'KRG1'

def _read_funcs_from_text(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            n = line.strip()
            if n and not n.startswith("#"):
                yield n

def _read_exact(f, size, desc):
    if size <= 0:
        return b""
    data = f.read(size)
    if len(data) != size:
        raise ValueError(f"SAFE graph truncated while reading {desc}")
    return data

def _load_safe_func_list(path):
    """Parse SAFE (.krg) graph and extract symbol names."""
    with open(path, "rb") as f:
        header = _read_exact(f, 32, "header")
        magic, version, n_nodes, n_edges, blob_bytes, arch, is_rt, res = struct.unpack("<8I", header)
        if magic != SAFE_KRG_MAGIC:
            raise ValueError("not a SAFE/krg graph (unexpected magic)")
        f.seek(n_nodes * 16, os.SEEK_CUR)          # node info
        f.seek((n_nodes + 1) * 4, os.SEEK_CUR)     # row_ptr
        f.seek(n_edges * 4, os.SEEK_CUR)           # col_idx
        if n_nodes:
            name_offsets_raw = _read_exact(f, n_nodes * 4, "name offsets")
            name_offsets = struct.unpack(f"<{n_nodes}I", name_offsets_raw)
        else:
            name_offsets = []
        blob = _read_exact(f, blob_bytes, "string blob")
    names = []
    for off in name_offsets:
        if off >= len(blob):
            continue
        end = blob.find(b"\0", off)
        if end == -1:
            continue
        name = blob[off:end].decode("utf-8", "ignore").strip()
        if name:
            names.append(name)
    if not names:
        raise ValueError("SAFE graph contained no symbol names")
    return names

def iter_funcs_from_file(path):
    lower = path.lower()
    try_text_first = not lower.endswith(".krg")
    if try_text_first:
        try:
            yield from _read_funcs_from_text(path)
            return
        except UnicodeDecodeError:
            pass  # fall back to SAFE decoding
    for name in _load_safe_func_list(path):
        yield name

def dump_c_for_ids(bpftool, by_id, layout_ids, out, btf_path=None, vmlinux=None):
    """
    Try per-id dump (new and old syntaxes). If both unsupported, fall back to
    dumping the whole C and slicing out only the needed decls by kind+name,
    using brace-depth counting to handle nested unions/structs.
    """
    printed_txt = set()
    path = vmlinux if vmlinux else (btf_path or "/sys/kernel/btf/vmlinux")

    # 1) Fast path: per-id dump (old/new syntaxes)
    all_ok = True
    for tid in sorted(layout_ids):
        # old syntax: ... type id <T> ...
        rc, txt, err, cmd = run(bpftool, ["btf","dump","file", path, "type", "id", str(tid), "format", "c"])
        if rc != 0:
            # new syntax: ... id <T> ...
            rc2, txt2, err2, cmd2 = run(bpftool, ["btf","dump","file", path, "id", str(tid), "format", "c"])
            if rc2 != 0:
                all_ok = False
                break
            txt = txt2
        if txt in printed_txt:
            continue
        printed_txt.add(txt)
        out.write(f"/* --- id {tid} --- */\n")
        out.write(txt)
        if not txt.endswith("\n"):
            out.write("\n")
        out.write("\n")

    if all_ok:
        return  # done

    # 2) Fallback: dump full C then slice out required decls with brace-depth tracking
    rc, full, err, cmd = run(bpftool, ["btf","dump","file", path, "format", "c"])
    if rc != 0:
        sys.stderr.write(f"[bpftool] error (full dump failed): {cmd}\n{err}\n")
        sys.exit(1)

    lines = full.splitlines(True)
    L = len(lines)

    # Build target name sets by kind
    targets_struct = set()
    targets_union  = set()
    targets_enum   = set()
    targets_typedef= set()
    for tid in sorted(layout_ids):
        o = by_id.get(tid)
        if not o: continue
        nm = o.get("name")
        if not nm: continue
        k  = o.get("kind")
        if   k == "STRUCT": targets_struct.add(nm)
        elif k == "UNION":  targets_union.add(nm)
        elif k in ("ENUM","ENUM64"): targets_enum.add(nm)
        elif k == "TYPEDEF": targets_typedef.add(nm)

    # helper: capture a balanced-brace block starting at line i that already contains an opening '{'
    def capture_braced_block(i):
        block = []
        depth = 0
        seen_open = False
        j = i
        while j < L:
            s = lines[j]
            # count braces
            # once we've seen the first '{', start tracking depth; include current line regardless
            if not seen_open:
                if '{' in s:
                    seen_open = True
            if seen_open:
                # naive count is fine for C decl dumps (strings/comments rarely contain braces in bpftool output)
                depth += s.count('{')
                depth -= s.count('}')
            block.append(s)
            # end when the outermost brace closes AND there is a semicolon on this line (end of decl)
            if seen_open and depth == 0 and ';' in s:
                return block, j+1
            j += 1
        return block, j

    # helper: capture typedef (may or may not include braces)
    def capture_typedef(i):
        block = []
        depth = 0
        j = i
        started = False
        while j < L:
            s = lines[j]
            # start collecting at first line
            block.append(s)
            # if this typedef contains a braced struct/union, track depth
            if '{' in s: started = True
            if started:
                depth += s.count('{') - s.count('}')
                if depth == 0 and ';' in s:
                    return block, j+1
            else:
                # no braces seen; stop at first semicolon
                if ';' in s:
                    return block, j+1
            j += 1
        return block, j

    # emit sets to avoid duplicates
    emitted_struct = set()
    emitted_union  = set()
    emitted_enum   = set()
    emitted_typedef= set()

    i = 0
    # precompile quick patterns
    struct_pat = re.compile(r'^\s*struct\s+([A-Za-z_]\w*)\s*\{')
    union_pat  = re.compile(r'^\s*union\s+([A-Za-z_]\w*)\s*\{')
    enum_pat   = re.compile(r'^\s*enum\s+([A-Za-z_]\w*)\s*\{')
    typedef_pat= re.compile(r'\btypedef\b')

    while i < L:
        s = lines[i]

        m = struct_pat.match(s)
        if m:
            name = m.group(1)
            if name in targets_struct and name not in emitted_struct:
                block, nxt = capture_braced_block(i)
                out.write(f"/* --- struct {name} --- */\n")
                out.writelines(block)
                if not block[-1].endswith("\n"): out.write("\n")
                out.write("\n")
                emitted_struct.add(name)
                i = nxt
                continue

        m = union_pat.match(s)
        if m:
            name = m.group(1)
            if name in targets_union and name not in emitted_union:
                block, nxt = capture_braced_block(i)
                out.write(f"/* --- union {name} --- */\n")
                out.writelines(block)
                if not block[-1].endswith("\n"): out.write("\n")
                out.write("\n")
                emitted_union.add(name)
                i = nxt
                continue

        m = enum_pat.match(s)
        if m:
            name = m.group(1)
            if name in targets_enum and name not in emitted_enum:
                block, nxt = capture_braced_block(i)
                out.write(f"/* --- enum {name} --- */\n")
                out.writelines(block)
                if not block[-1].endswith("\n"): out.write("\n")
                out.write("\n")
                emitted_enum.add(name)
                i = nxt
                continue

        if typedef_pat.search(s):
            block, nxt = capture_typedef(i)
            if targets_typedef:
                block_text = "".join(block)
                hits = []
                for name in (targets_typedef - emitted_typedef):
                    if re.search(r"\b" + re.escape(name) + r"\b", block_text):
                        hits.append(name)
                if hits:
                    out.write(f"/* --- typedef {hits[0]} --- */\n")
                    out.writelines(block)
                    if not block[-1].endswith("\n"): out.write("\n")
                    out.write("\n")
                    for name in hits:
                        emitted_typedef.add(name)
                    i = nxt
                    continue
            i += 1
            continue
        else:
            i += 1

    # 小提示：有的结构可能是匿名+typedef 的组合，若没截出来，可以把名字加到 typedef 名单再跑一次


@dataclass
class BtfSource:
    label: str
    btf_path: Optional[str]
    vmlinux: Optional[str]
    by_id: dict
    marked: set = field(default_factory=set)




def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--funcs-file")
    ap.add_argument("--funcs")
    ap.add_argument("--out")
    ap.add_argument("--btf", dest="btf_path")
    ap.add_argument("--vmlinux")
    ap.add_argument("--bpftool")
    ap.add_argument("--module", action="append", default=[],
                    help="Module BTF source (.ko or /sys/kernel/btf/<name>), can be repeated")
    ap.add_argument("--modules",
                    help="Comma-separated module BTF sources (.ko paths or names)")
    args = ap.parse_args()

    bpftool = find_bpftool(args.bpftool)
    if not bpftool: sys.exit(1)

    roots = set()
    if args.funcs_file:
        try:
            for n in iter_funcs_from_file(args.funcs_file):
                roots.add(n)
        except (OSError, ValueError) as e:
            sys.stderr.write(f"Failed to read --funcs-file {args.funcs_file}: {e}\n")
            sys.exit(1)
    if args.funcs:
        for n in args.funcs.split(","):
            n=n.strip()
            if n: roots.add(n)
    if not roots:
        sys.stderr.write("No functions provided (use --funcs-file or --funcs)\n"); sys.exit(1)

    module_inputs = list(args.module or [])
    if args.modules:
        module_inputs.extend([m.strip() for m in args.modules.split(",") if m.strip()])

    sources = []
    objs = load_btf_json(bpftool, args.btf_path, args.vmlinux)
    sources.append(BtfSource(label="vmlinux",
                             btf_path=args.btf_path,
                             vmlinux=args.vmlinux,
                             by_id=build_index(objs)))
    for mod in module_inputs:
        try:
            mod_path = resolve_module_btf_path(mod)
        except ValueError as e:
            sys.stderr.write(f"ERROR: {e}\n")
            sys.exit(1)
        mod_objs = load_btf_json(bpftool, btf_path=mod_path)
        sources.append(BtfSource(label=os.path.basename(mod_path),
                                 btf_path=mod_path,
                                 vmlinux=None,
                                 by_id=build_index(mod_objs)))

    missing = []
    matched = {src.label: [] for src in sources}
    for fn in sorted(roots):
        found_any = False
        for src in sources:
            proto = find_func_proto_id(src.by_id, fn)
            if proto is None:
                continue
            add_type_closure(src.by_id, proto, src.marked)
            matched[src.label].append(fn)
            found_any = True
        if not found_any:
            missing.append(fn)

    if missing:
        sys.stderr.write("ERROR: functions not found in any BTF source:\n")
        for fn in missing:
            sys.stderr.write(f"  - {fn}\n")
        sys.exit(1)

    if module_inputs:
        for src in sources[1:]:
            hits = matched.get(src.label, [])
            if not hits:
                sys.stderr.write(f"WARN: no functions matched in module BTF source '{src.label}'\n")
            else:
                sys.stderr.write(f"INFO: module BTF source '{src.label}' matched {len(hits)} functions\n")

    out = open(args.out,"w") if args.out else sys.stdout
    out.write("/* Auto-generated by vkso-gen-types (safe funcs only). */\n")
    out.write("#pragma once\n#include <stddef.h>\n#include <stdint.h>\n\n")
    emitted = set()
    for src in sources:
        if not src.marked:
            continue
        layout_ids = set()
        for tid in src.marked:
            o = src.by_id.get(tid)
            if not o:
                continue
            kind = o.get("kind")
            name = o.get("name")
            if kind in ("STRUCT","UNION","ENUM","ENUM64","TYPEDEF"):
                if not name or name == "(anon)":
                    key = (kind, src.label, tid)
                else:
                    key = (kind, name)
                if key in emitted:
                    if name and name != "(anon)":
                        sys.stderr.write(f"WARN: duplicate type {kind} {name} from {src.label}, skip\n")
                    continue
                emitted.add(key)
                layout_ids.add(tid)
        if not layout_ids:
            continue
        src_path = src.vmlinux or src.btf_path or "/sys/kernel/btf/vmlinux"
        out.write(f"/* --- BTF source: {src.label} ({src_path}) --- */\n")
        dump_c_for_ids(bpftool, src.by_id, layout_ids, out,
                       btf_path=src.btf_path, vmlinux=src.vmlinux)
    if out is not sys.stdout: out.close()

if __name__ == "__main__":
    main()
