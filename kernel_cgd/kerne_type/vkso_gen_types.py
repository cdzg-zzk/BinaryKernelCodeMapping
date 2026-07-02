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

DEFAULT_VMLINUX_BTF = "/sys/kernel/btf/vmlinux"
MODULE_BTF_DIR = "/sys/kernel/btf"
KALLSYMS_PATH = "/proc/kallsyms"
GLOBAL_TEXT_SYMBOL_TYPES = ("T", "W")
KSYMTAB_PREFIXES = (
    "__ksymtab_",
    "__ksymtab_gpl_",
    "__ksymtab_unused_",
    "__ksymtab_unused_gpl_",
)

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

def load_btf_json(bpftool, btf_path=None, vmlinux=None, base_btf=None):
    """Try multiple json styles:
       1) btf dump file ... -j
       2) -j btf dump file ...
       3) btf dump file ... format json
       Return a list[dict] of types.
    """
    path = vmlinux if vmlinux else (btf_path or DEFAULT_VMLINUX_BTF)
    variants = [
        ["btf","dump","file",path,"-j"],
        ["-j","btf","dump","file",path],
        ["btf","dump","file",path,"format","json"],
    ]
    if base_btf and path != base_btf:
        variants.extend([
            ["btf","dump","file",path,"-j","--base-btf",base_btf],
            ["-j","btf","dump","file",path,"--base-btf",base_btf],
            ["btf","dump","file",path,"format","json","--base-btf",base_btf],
        ])
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

def _kallsyms_owner(parts):
    if len(parts) >= 4 and parts[3].startswith("[") and parts[3].endswith("]"):
        return parts[3][1:-1]
    return "vmlinux"

def _remember_unique_owner(owners, duplicates, name, owner):
    prev = owners.get(name)
    if prev is None:
        owners[name] = owner
    elif prev != owner:
        duplicates.add(name)

def load_kallsyms_owner_hints(kallsyms_path=KALLSYMS_PATH):
    global_text_owners = {}
    exported_symbol_owners = {}
    global_text_duplicates = set()
    exported_symbol_duplicates = set()
    if not os.path.exists(kallsyms_path):
        return global_text_owners, exported_symbol_owners
    try:
        with open(kallsyms_path, encoding="utf-8") as f:
            for raw in f:
                parts = raw.split()
                if len(parts) < 3:
                    continue
                sym_type = parts[1]
                sym = parts[2]
                owner = _kallsyms_owner(parts)
                if sym_type in GLOBAL_TEXT_SYMBOL_TYPES:
                    _remember_unique_owner(
                        global_text_owners, global_text_duplicates, sym, owner
                    )
                prefix = next((p for p in KSYMTAB_PREFIXES if sym.startswith(p)), None)
                if prefix is None:
                    continue
                exported = sym[len(prefix):]
                if not exported:
                    continue
                _remember_unique_owner(
                    exported_symbol_owners, exported_symbol_duplicates, exported, owner
                )
        for sym in global_text_duplicates:
            global_text_owners.pop(sym, None)
        for exported in exported_symbol_duplicates:
            exported_symbol_owners.pop(exported, None)
    except OSError as e:
        sys.stderr.write(f"WARN: failed to read {kallsyms_path}: {e}\n")
    return global_text_owners, exported_symbol_owners

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
            btf_path = f"{MODULE_BTF_DIR}/{mod_name}"
            if os.path.exists(btf_path):
                return btf_path
        return mod
    candidates = []
    if "/" not in mod:
        candidates.append(f"{MODULE_BTF_DIR}/{mod}")
        if mod.endswith(".ko"):
            candidates.append(f"{MODULE_BTF_DIR}/{mod[:-3]}")
    for c in candidates:
        if os.path.exists(c):
            return c
    raise ValueError(f"module BTF not found for '{mod}' (tried {', '.join(candidates)})")

def add_type_closure(src, root_id):
    if not root_id:
        return
    if root_id in src.marked:
        return
    o = src.by_id.get(root_id)
    if not o and src.base is not None and root_id in src.base.by_id:
        add_type_closure(src.base, root_id)
        return
    src.marked.add(root_id)
    if not o: return
    k = o.get("kind")
    if k in ("TYPEDEF","CONST","VOLATILE","RESTRICT"):
        add_type_closure(src, o.get("type_id")); return
    if k == "PTR":
        add_type_closure(src, o.get("type_id")); return
    if k == "ARRAY":
        add_type_closure(src, o.get("elem_type_id")); return
    if k in ("STRUCT","UNION"):
        for m in (o.get("members") or []):
            add_type_closure(src, m.get("type_id"))
        return
    if k in ("ENUM","ENUM64"):
        return
    if k == "FUNC_PROTO":
        add_type_closure(src, o.get("ret_type_id"))
        for p in (o.get("params") or []):
            add_type_closure(src, p.get("type_id"))
        return
    if k == "FUNC":
        add_type_closure(src, o.get("type_id")); return
    # VAR / DATASEC / SEC etc. ignored

import re

SAFE_KRG_MAGIC = 0x3147524B  # 'KRG1'

@dataclass
class FunctionRequest:
    name: str
    source_id: Optional[str] = None
    required: bool = True
    origin: str = ""

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

def _looks_like_resolved_entry(line):
    parts = [p.strip() for p in line.split(",")]
    return len(parts) == 5 and parts[-1] in ("0", "1")

def load_requests_from_file(path):
    lower = path.lower()
    try_text_first = not lower.endswith(".krg")
    if try_text_first:
        try:
            with open(path, encoding="utf-8") as f:
                for lineno, raw in enumerate(f, start=1):
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if _looks_like_resolved_entry(line):
                        raise ValueError(
                            f"{path}:{lineno}: resolved_symbol_addresses.txt is no longer accepted by --funcs-file; "
                            "pass a plain API symbol list such as symbols.txt"
                        )
                    break
            return [FunctionRequest(name=n, required=True, origin=path)
                    for n in _read_funcs_from_text(path)]
        except UnicodeDecodeError:
            pass  # fall back to SAFE decoding
    return [FunctionRequest(name=n, required=True, origin=path)
            for n in _load_safe_func_list(path)]

def dump_c_for_ids(bpftool, by_id, layout_ids, out, btf_path=None, vmlinux=None, base_btf=None):
    """
    Try per-id dump (new and old syntaxes). If both unsupported, fall back to
    dumping the whole C and slicing out only the needed decls by kind+name,
    using brace-depth counting to handle nested unions/structs.
    """
    printed_txt = set()
    path = vmlinux if vmlinux else (btf_path or DEFAULT_VMLINUX_BTF)
    allow_suffix_alias = bool(base_btf and path != base_btf)

    def canonical_name(name, targets):
        if name in targets:
            return name
        if allow_suffix_alias:
            m = re.match(r"^(.*)___\d+$", name)
            if m and m.group(1) in targets:
                return m.group(1)
        return None

    def normalize_block_text(text, targets):
        if not allow_suffix_alias:
            return text
        replacements = {}
        for name in targets:
            for m in re.finditer(r"\b" + re.escape(name) + r"___\d+\b", text):
                replacements[m.group(0)] = name
        if not replacements:
            return text
        for old, new in sorted(replacements.items(), key=lambda kv: len(kv[0]), reverse=True):
            text = re.sub(r"\b" + re.escape(old) + r"\b", new, text)
        return text

    # 1) Fast path: per-id dump (old/new syntaxes)
    all_ok = True
    for tid in sorted(layout_ids):
        # old syntax: ... type id <T> ...
        cmd_args = ["btf","dump","file", path, "type", "id", str(tid), "format", "c"]
        if base_btf and path != base_btf:
            cmd_args.extend(["--base-btf", base_btf])
        rc, txt, err, cmd = run(bpftool, cmd_args)
        if rc != 0:
            # new syntax: ... id <T> ...
            cmd_args = ["btf","dump","file", path, "id", str(tid), "format", "c"]
            if base_btf and path != base_btf:
                cmd_args.extend(["--base-btf", base_btf])
            rc2, txt2, err2, cmd2 = run(bpftool, cmd_args)
            if rc2 != 0:
                all_ok = False
                break
            txt = txt2
        if allow_suffix_alias:
            o = by_id.get(tid)
            name = o.get("name") if o else None
            if name and name != "(anon)":
                txt = normalize_block_text(txt, {name})
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
    cmd_args = ["btf","dump","file", path, "format", "c"]
    if base_btf and path != base_btf:
        cmd_args.extend(["--base-btf", base_btf])
    rc, full, err, cmd = run(bpftool, cmd_args)
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
    all_targets = targets_struct | targets_union | targets_enum | targets_typedef
    prefer_suffixed = set()
    if allow_suffix_alias:
        for name in all_targets:
            if re.search(r"\b" + re.escape(name) + r"___\d+\b", full):
                prefer_suffixed.add(name)

    def canonical_name_for_dump(name, targets):
        if name in targets:
            if name in prefer_suffixed:
                return None
            return name
        if allow_suffix_alias:
            m = re.match(r"^(.*)___\d+$", name)
            if m and m.group(1) in targets:
                return m.group(1)
        return None

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

    def extract_typedef_name(block_text):
        m = re.search(r"\(\s*\*\s*([A-Za-z_]\w*)\s*\)\s*\(", block_text, re.S)
        if m:
            return m.group(1)
        m = re.search(r"\b([A-Za-z_]\w*)\s*(?:\[[^\]]+\])?\s*;\s*$", block_text, re.S)
        if m:
            return m.group(1)
        return None

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
            raw_name = m.group(1)
            name = canonical_name_for_dump(raw_name, targets_struct)
            if name and name not in emitted_struct:
                block, nxt = capture_braced_block(i)
                block_text = normalize_block_text("".join(block), all_targets)
                out.write(f"/* --- struct {name} --- */\n")
                out.write(block_text)
                if not block_text.endswith("\n"): out.write("\n")
                out.write("\n")
                emitted_struct.add(name)
                i = nxt
                continue

        m = union_pat.match(s)
        if m:
            raw_name = m.group(1)
            name = canonical_name_for_dump(raw_name, targets_union)
            if name and name not in emitted_union:
                block, nxt = capture_braced_block(i)
                block_text = normalize_block_text("".join(block), all_targets)
                out.write(f"/* --- union {name} --- */\n")
                out.write(block_text)
                if not block_text.endswith("\n"): out.write("\n")
                out.write("\n")
                emitted_union.add(name)
                i = nxt
                continue

        m = enum_pat.match(s)
        if m:
            raw_name = m.group(1)
            name = canonical_name_for_dump(raw_name, targets_enum)
            if name and name not in emitted_enum:
                block, nxt = capture_braced_block(i)
                block_text = normalize_block_text("".join(block), all_targets)
                out.write(f"/* --- enum {name} --- */\n")
                out.write(block_text)
                if not block_text.endswith("\n"): out.write("\n")
                out.write("\n")
                emitted_enum.add(name)
                i = nxt
                continue

        if typedef_pat.search(s):
            block, nxt = capture_typedef(i)
            if targets_typedef:
                block_text = "".join(block)
                typedef_name = extract_typedef_name(block_text)
                canonical = canonical_name_for_dump(typedef_name, targets_typedef) if typedef_name else None
                if canonical and canonical not in emitted_typedef:
                    block_text = normalize_block_text(block_text, all_targets)
                    out.write(f"/* --- typedef {canonical} --- */\n")
                    out.write(block_text)
                    if not block_text.endswith("\n"): out.write("\n")
                    out.write("\n")
                    emitted_typedef.add(canonical)
                    i = nxt
                    continue
            i += 1
            continue
        else:
            i += 1

    # 小提示：有的结构可能是匿名+typedef 的组合，若没截出来，可以把名字加到 typedef 名单再跑一次


@dataclass
class BtfSource:
    source_id: str
    label: str
    btf_path: Optional[str]
    vmlinux: Optional[str]
    by_id: dict
    base: Optional["BtfSource"] = None
    marked: set = field(default_factory=set)

def list_module_btf_candidates():
    try:
        names = sorted(os.listdir(MODULE_BTF_DIR))
    except OSError:
        return []
    out = []
    for name in names:
        if name == os.path.basename(DEFAULT_VMLINUX_BTF):
            continue
        path = os.path.join(MODULE_BTF_DIR, name)
        if os.path.isfile(path):
            out.append(path)
    return out

def ensure_source_loaded(bpftool, source_id, sources_by_id, source_order, base_source, base_btf_path):
    if source_id in sources_by_id:
        return sources_by_id[source_id]
    if source_id == base_btf_path:
        return base_source
    mod_objs = load_btf_json(bpftool, btf_path=source_id, base_btf=base_btf_path)
    src = BtfSource(
        source_id=source_id,
        label=os.path.basename(source_id),
        btf_path=source_id,
        vmlinux=None,
        by_id=build_index(mod_objs),
        base=base_source,
    )
    sources_by_id[source_id] = src
    source_order.append(source_id)
    return src

def discover_sources_for_func(fn, bpftool, sources_by_id, source_order, base_source, base_btf_path, module_candidates):
    matches = []
    if find_func_proto_id(base_source.by_id, fn) is not None:
        matches.append(base_source)
    for source_id in module_candidates:
        src = ensure_source_loaded(bpftool, source_id, sources_by_id, source_order, base_source, base_btf_path)
        if find_func_proto_id(src.by_id, fn) is not None:
            matches.append(src)
    return matches

def filter_matches_by_owner_hints(fn, matches, global_text_owners, exported_symbol_owners):
    for owners in (global_text_owners, exported_symbol_owners):
        owner = owners.get(fn)
        if owner is None:
            continue
        filtered = [src for src in matches if src.label == owner]
        if filtered:
            return filtered
    return matches

def lookup_type(src, tid):
    cur = src
    while cur is not None:
        obj = cur.by_id.get(tid)
        if obj is not None:
            return cur, obj
        cur = cur.base
    return src, None

def _group_decl_if_needed(decl):
    if decl and any(ch in decl for ch in "*[("):
        return f"({decl})"
    return decl

def render_c_decl(src, tid, decl=""):
    if tid == 0:
        return f"void {decl}".strip()
    owner, obj = lookup_type(src, tid)
    if obj is None:
        return f"/* unresolved_btf_{tid} */ {decl}".strip()
    kind = obj.get("kind")
    name = obj.get("name")

    if kind == "TYPEDEF":
        return f"{name} {decl}".strip()
    if kind == "INT":
        return f"{name} {decl}".strip()
    if kind == "FLOAT":
        return f"{name} {decl}".strip()
    if kind == "VOID":
        return f"void {decl}".strip()
    if kind == "ENUM":
        base = f"enum {name}" if name and name != "(anon)" else "enum"
        return f"{base} {decl}".strip()
    if kind == "ENUM64":
        base = f"enum {name}" if name and name != "(anon)" else "enum"
        return f"{base} {decl}".strip()
    if kind == "STRUCT":
        base = f"struct {name}" if name and name != "(anon)" else "struct"
        return f"{base} {decl}".strip()
    if kind == "UNION":
        base = f"union {name}" if name and name != "(anon)" else "union"
        return f"{base} {decl}".strip()
    if kind == "PTR":
        inner_decl = "*" if not decl else "*" + _group_decl_if_needed(decl)
        return render_c_decl(owner, obj.get("type_id"), inner_decl)
    if kind == "ARRAY":
        nr_elems = obj.get("nr_elems", 0)
        inner_decl = f"{decl}[{nr_elems}]" if decl else f"[{nr_elems}]"
        return render_c_decl(owner, obj.get("elem_type_id"), inner_decl)
    if kind in ("CONST", "VOLATILE", "RESTRICT"):
        qualifier = kind.lower()
        rendered = render_c_decl(owner, obj.get("type_id"), decl)
        if decl and rendered.endswith(decl):
            prefix = rendered[:-len(decl)].rstrip()
            return f"{qualifier} {prefix} {decl}".strip()
        return f"{qualifier} {rendered}".strip()
    if kind == "FUNC_PROTO":
        params = []
        for idx, p in enumerate(obj.get("params") or []):
            p_name = p.get("name") or f"arg{idx}"
            p_tid = p.get("type_id")
            if p_tid == 0:
                params.append("...")
            else:
                params.append(render_c_decl(owner, p_tid, p_name))
        params_text = ", ".join(params) if params else "void"
        inner_decl = f"{_group_decl_if_needed(decl)}({params_text})" if decl else f"({params_text})"
        return render_c_decl(owner, obj.get("ret_type_id"), inner_decl)
    return f"/* unsupported_{kind}_{tid} */ {decl}".strip()

def render_function_decl(src, fn):
    func_id = None
    proto_id = None
    for tid, obj in src.by_id.items():
        if obj.get("kind") == "FUNC" and obj.get("name") == fn:
            func_id = tid
            proto_id = obj.get("type_id")
            break
    if proto_id is None:
        return None
    return render_c_decl(src, proto_id, fn) + ";"




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

    base_btf_path = args.vmlinux if args.vmlinux else (args.btf_path or DEFAULT_VMLINUX_BTF)
    requests = []
    if args.funcs_file:
        try:
            requests.extend(load_requests_from_file(args.funcs_file))
        except (OSError, ValueError) as e:
            sys.stderr.write(f"Failed to read --funcs-file {args.funcs_file}: {e}\n")
            sys.exit(1)
    if args.funcs:
        for n in args.funcs.split(","):
            n = n.strip()
            if n:
                requests.append(FunctionRequest(name=n, required=True, origin="--funcs"))
    if not requests:
        sys.stderr.write("No functions provided (use --funcs-file or --funcs)\n"); sys.exit(1)

    module_inputs = list(args.module or [])
    if args.modules:
        module_inputs.extend([m.strip() for m in args.modules.split(",") if m.strip()])
    module_candidates = []
    seen_candidates = set()
    for mod in module_inputs:
        try:
            source_id = resolve_module_btf_path(mod)
        except ValueError as e:
            sys.stderr.write(f"ERROR: {e}\n")
            sys.exit(1)
        if source_id not in seen_candidates:
            seen_candidates.add(source_id)
            module_candidates.append(source_id)
    for source_id in list_module_btf_candidates():
        if source_id not in seen_candidates:
            seen_candidates.add(source_id)
            module_candidates.append(source_id)

    base_objs = load_btf_json(bpftool, btf_path=base_btf_path)
    base_source = BtfSource(
        source_id=base_btf_path,
        label="vmlinux",
        btf_path=base_btf_path,
        vmlinux=None,
        by_id=build_index(base_objs),
    )
    sources_by_id = {base_btf_path: base_source}
    source_order = [base_btf_path]
    global_text_owners, exported_symbol_owners = load_kallsyms_owner_hints()
    matched = {base_btf_path: []}
    missing_required = []
    matched_count = 0
    decl_order = []
    seen_decl_keys = set()

    for req in requests:
        if req.source_id is not None:
            src = ensure_source_loaded(
                bpftool, req.source_id, sources_by_id, source_order, base_source, base_btf_path
            )
            matched.setdefault(src.source_id, [])
            proto = find_func_proto_id(src.by_id, req.name)
            if proto is None:
                level = "ERROR" if req.required else "WARN"
                sys.stderr.write(
                    f"{level}: func={req.name} not found in BTF source '{src.label}'"
                    f" (origin={req.origin or 'unknown'})\n"
                )
                if req.required:
                    missing_required.append(req.name)
                continue
            sys.stderr.write(f"INFO: func={req.name} resolved in BTF source '{src.label}'\n")
            add_type_closure(src, proto)
            matched[src.source_id].append(req.name)
            matched_count += 1
            decl_key = (src.source_id, req.name)
            if decl_key not in seen_decl_keys:
                seen_decl_keys.add(decl_key)
                decl_order.append(decl_key)
            continue

        matches = discover_sources_for_func(
            req.name, bpftool, sources_by_id, source_order, base_source, base_btf_path, module_candidates
        )
        matches = filter_matches_by_owner_hints(
            req.name, matches, global_text_owners, exported_symbol_owners
        )
        if not matches:
            level = "ERROR" if req.required else "WARN"
            sys.stderr.write(
                f"{level}: func={req.name} not found in vmlinux or any loaded module"
                f" (origin={req.origin or 'unknown'})\n"
            )
            if req.required:
                missing_required.append(req.name)
            continue
        if len(matches) > 1:
            labels = ", ".join(src.label for src in matches)
            sys.stderr.write(
                f"ERROR: func={req.name} matched multiple BTF sources: {labels}"
                f" (origin={req.origin or 'unknown'})\n"
            )
            missing_required.append(req.name)
            continue
        src = matches[0]
        matched.setdefault(src.source_id, [])
        sys.stderr.write(f"INFO: func={req.name} auto-resolved to BTF source '{src.label}'\n")
        add_type_closure(src, find_func_proto_id(src.by_id, req.name))
        matched[src.source_id].append(req.name)
        matched_count += 1
        decl_key = (src.source_id, req.name)
        if decl_key not in seen_decl_keys:
            seen_decl_keys.add(decl_key)
            decl_order.append(decl_key)

    if missing_required:
        sys.stderr.write("ERROR: required functions were not resolved:\n")
        for fn in sorted(set(missing_required)):
            sys.stderr.write(f"  - {fn}\n")
        sys.exit(1)
    if matched_count == 0:
        sys.stderr.write("ERROR: no functions were resolved from the provided inputs\n")
        sys.exit(1)

    for source_id in source_order:
        src = sources_by_id[source_id]
        hits = matched.get(source_id, [])
        if hits:
            sys.stderr.write(f"INFO: BTF source '{src.label}' matched {len(hits)} functions\n")

    out = open(args.out,"w") if args.out else sys.stdout
    out.write("/* Auto-generated by vkso-gen-types (safe funcs only). */\n")
    out.write("#pragma once\n#include <stddef.h>\n#include <stdint.h>\n\n")
    emitted = set()
    emit_order = [sid for sid in source_order if sid != base_btf_path] + [base_btf_path]
    for source_id in emit_order:
        src = sources_by_id[source_id]
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
        src_path = src.vmlinux or src.btf_path or DEFAULT_VMLINUX_BTF
        out.write(f"/* --- BTF source: {src.label} ({src_path}) --- */\n")
        dump_c_for_ids(bpftool, src.by_id, layout_ids, out,
                       btf_path=src.btf_path, vmlinux=src.vmlinux,
                       base_btf=base_btf_path if src.base is not None else None)
    if decl_order:
        out.write("/* --- API function declarations --- */\n")
        for source_id, fn in decl_order:
            src = sources_by_id[source_id]
            decl = render_function_decl(src, fn)
            if decl is None:
                sys.stderr.write(f"WARN: failed to render declaration for {fn} from {src.label}\n")
                continue
            out.write(decl)
            out.write("\n")
    if out is not sys.stdout: out.close()

if __name__ == "__main__":
    main()
