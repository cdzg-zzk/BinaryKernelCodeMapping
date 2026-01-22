// krg.cpp — SAFE-only build/query for Linux vmlinux (x86-64)
// Fast + clean: primary-only ranges, ABSMEM support, global binary searches, deep logs.
//
// Build: g++ -O3 -std=c++2a -Wall -Wextra -Wpedantic krg.cpp -o krg -lcapstone -I ./ELFIO
// Usage: sudo ./krg build /usr/lib/debug/boot/vmlinux-$(uname -r) -o out.krg [--debug] [--dbg-sym=<name>]
//        sudo ./krg query out.krg <symbol>


// sudo ./krg build /usr/lib/debug/boot/vmlinux-$(uname -r) \                                                                INT ✘  zzk@zzk200  00:43:12  
//    -o /home/zzk/workspace/BinaryKernelCodeMapping/kernel_cgd/src/out.krg \
//    -m /home/zzk/workspace/BinaryKernelCodeMapping/test/test_lkm_locate/lkm_locate.ko 
//
#include <elfio/elfio.hpp>
#include <capstone/capstone.h>

#include <algorithm>
#include <cstdint>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using u8 = uint8_t; using u16 = uint16_t; using u32 = uint32_t; using u64 = uint64_t; using i32 = int32_t; using i64 = long long;

struct Node { u64 addr; u32 size; u16 module; u8 kind; u8 pad{0}; };   // kind: 0=code, 1=data; module: 0=kernel, >0=modules
struct BuildSym { std::string name; Node n{}; u16 sec_idx{0}; bool defined{false}; u8 is_primary{0}; u32 origin{0}; };
struct SectionInfo { ELFIO::section* sec{nullptr}; std::string name; u64 addr{0}, size{0}, offset{0}, flags{0}; u32 idx{0}; };
struct Range { u64 start, end; u32 id; }; // [start,end)

struct FileHeader {
    u32 magic{0x3147524b}; // 'KRG1'
    u32 version{2};
    u32 n_nodes{0};
    u32 n_edges{0};
    u32 name_blob_bytes{0};
    u32 arch{0}; // 0=x86_64
    u32 is_runtime_address{0};
    u32 reserved1{0};
    u32 n_modules{0};
    u32 module_blob_bytes{0};
};

struct FileHeaderV1 {
    u32 magic{0x3147524b};
    u32 version{1};
    u32 n_nodes{0};
    u32 n_edges{0};
    u32 name_blob_bytes{0};
    u32 arch{0};
    u32 is_runtime_address{0};
    u32 reserved1{0};
};

static inline bool is_exec(u64 f){ return (f & ELFIO::SHF_EXECINSTR) != 0; }
static inline bool is_write(u64 f){ return (f & ELFIO::SHF_WRITE)     != 0; }
static inline bool starts_with_dot(const std::string& n){ return !n.empty() && n[0]=='.'; }
static inline bool has_prefix(const std::string& s, const std::string& p){
    return s.size() >= p.size() && std::memcmp(s.data(), p.data(), p.size()) == 0;
}
static inline u64 align_up(u64 v, u64 a){ return (a<=1) ? v : (v + a - 1) & ~(a - 1); }
static constexpr const char* KERNEL_MODULE_LABEL = "kernel";
static constexpr unsigned R_X86_64_64  = 1;
static constexpr unsigned R_X86_64_PC32 = 2;
static inline u64 sec_off_key(u32 sec_idx, u32 off){ return (u64(sec_idx) << 32) | u64(off); }

static std::string basename_noext(const std::string& path){
    size_t pos = path.find_last_of('/');
    std::string base = (pos == std::string::npos) ? path : path.substr(pos + 1);
    const std::string exts[] = {".ko.xz", ".ko.gz", ".ko.zst", ".ko"};
    for (const auto& ext : exts){
        if (base.size() >= ext.size() && base.compare(base.size() - ext.size(), ext.size(), ext) == 0){
            base.resize(base.size() - ext.size());
            break;
        }
    }
    return base;
}

static std::optional<std::string> modinfo_name(const ELFIO::elfio& r){
    const ELFIO::section* modinfo = nullptr;
    for (u32 i = 0; i < r.sections.size(); ++i){
        const auto* s = r.sections[i];
        if (s && s->get_name() == ".modinfo") { modinfo = s; break; }
    }
    if (!modinfo) return std::nullopt;
    const char* data = modinfo->get_data();
    if (!data) return std::nullopt;
    const size_t size = modinfo->get_size();
    size_t i = 0;
    while (i < size){
        const char* cur = data + i;
        const char* end = static_cast<const char*>(std::memchr(cur, '\0', size - i));
        const size_t len = end ? (size_t)(end - cur) : (size - i);
        if (len == 0) { ++i; continue; }
        if (len > 5 && std::strncmp(cur, "name=", 5) == 0){
            return std::string(cur + 5, len - 5);
        }
        if (!end) break;
        i += len + 1;
    }
    return std::nullopt;
}

static std::string module_sys_name(const std::string& path, const ELFIO::elfio& r){
    if (auto n = modinfo_name(r)) return *n;
    std::string base = basename_noext(path);
    for (char& c : base){
        if (c == '-') c = '_';
    }
    return base;
}

static const std::vector<std::string>& default_stop_names() {
    static const std::vector<std::string> names = {
        "__kmalloc", "kmalloc", "kfree", "printk", "vprintk", "kstrdup",
        "ktime_get", "ktime_get_ns", "ktime_get_real_ts64", "do_gettimeofday"
    };
    return names;
}

static std::vector<std::string> read_symbol_list(const std::string& path){
    std::vector<std::string> out;
    std::ifstream in(path);
    if (!in) return out;
    std::string line;
    while (std::getline(in, line)){
        auto pos_hash = line.find('#');
        if (pos_hash != std::string::npos) line.resize(pos_hash);
        // trim
        auto l = line.find_first_not_of(" \t\r\n");
        if (l == std::string::npos) continue;
        auto r = line.find_last_not_of(" \t\r\n");
        std::string tok = line.substr(l, r - l + 1);
        if (!tok.empty()) out.push_back(tok);
    }
    return out;
}

static std::optional<u64> read_hex_file(const std::string& path){
    std::ifstream in(path);
    if (!in) return std::nullopt;
    std::string s;
    in >> s;
    if (s.rfind("0x", 0) == 0 || s.rfind("0X", 0) == 0) s = s.substr(2);
    if (s.empty()) return std::nullopt;
    try {
        return std::stoull(s, nullptr, 16);
    } catch (...) {
        return std::nullopt;
    }
}

static std::optional<u64> read_kallsyms_addr(const std::string& name){
    std::ifstream in("/proc/kallsyms");
    if(!in) return std::nullopt;
    std::string line;
    while(std::getline(in,line)){
        size_t sp=line.find_last_of(' ');
        if(sp==std::string::npos) continue;
        std::string nm=line.substr(sp+1);
        if(nm==name){
            size_t psp=line.find(' ');
            if(psp==std::string::npos) continue;
            std::string hex=line.substr(0,psp);
            try{ u64 v=std::stoull(hex,nullptr,16); return v; }catch(...){ return std::nullopt; }
        }
    }
    return std::nullopt;
}

struct Builder {
    // 基本
    struct InputFile {
        std::string path;
        std::unique_ptr<ELFIO::elfio> reader;
        u64 base{0};
        bool is_relocatable{false};
        std::vector<u32> sec_map;
    };
    std::vector<InputFile> inputs;
    std::vector<SectionInfo> secs;                 // 所有节
    std::vector<BuildSym>    syms;                 // 所有符号
    std::unordered_map<std::string,u32> name2id;

    // 仅“主函数入口”的节内表（按地址排序）
    std::vector<std::vector<u32>> sec_primary_funcs;
    // 全局主函数区间表（按 start 升序）
    std::vector<Range> fun_ranges_;
    // 数据符号区间表（按 start 升序），用于将“section+addend”映射回具体 data 符号
    std::vector<Range> data_ranges_;
    // 同起始地址的别名函数（alias）：start_addr -> [func_ids...]
    std::unordered_map<u64, std::vector<u32>> alias_by_start_;
    // 可分配节的区间表（按 start 升序），用于 ABS/RIP 指针定位
    std::vector<Range> alloc_secs_;

    // 边
    std::vector<std::vector<u32>> adj;       // code -> code
    std::vector<std::vector<u32>> data_refs; // code -> data

    // 安全辅助
    std::vector<u8> data_is_writable;
    std::vector<u8> calls_blacklisted;

    // 硬黑名单前缀（CALL 命中 → 过滤 + 标 caller 不安全；JMP 命中 → 仅过滤）
    const std::vector<std::string> hard_bl_prefix = {
        "schedule", "preempt_", "cond_resched", "msleep", "udelay", "mdelay",
        "copy_to_user", "copy_from_user", "get_user", "put_user",
        "ioremap", "iounmap",
        "pci_", "net_", "sock_", "blk_", "vfs_", "fs_", "dev_",
        "__sanitizer_"
    };
    // 软忽略（CALL/JMP 命中 → 仅不过边）
    const std::vector<std::string> soft_ig = {
        "__fentry__", "mcount", "__stack_chk_fail"
    };

    // Debug
    bool debug{false};
    std::string dbg_sym;
    inline bool want(u32 u) const {
        if (!debug) return false;
        if (dbg_sym.empty()) return true;
        return syms[u].name == dbg_sym;
    }
    inline void dlog(const char* fmt, ...) const {
        if (!debug) return;
        va_list ap; va_start(ap, fmt);
        vfprintf(stderr, fmt, ap);
        va_end(ap);
    }

    // 基础
    bool add_input(const std::string& p, u64 base){
        InputFile in;
        in.path = p;
        in.base = base;
        in.reader = std::make_unique<ELFIO::elfio>();
        if (!in.reader->load(p)) return false;
        in.is_relocatable = (in.reader->get_type() == ELFIO::ET_REL);
        inputs.push_back(std::move(in));
        return true;
    }

    u16 map_sec_idx(const InputFile& in, ELFIO::Elf_Half si) const {
        if (si == ELFIO::SHN_UNDEF) return ELFIO::SHN_UNDEF;
        if (si < in.sec_map.size()) return (u16)in.sec_map[si];
        return si;
    }

    u64 sym_addr(const InputFile& in, ELFIO::Elf_Half si, ELFIO::Elf64_Addr v) const {
        if (si == ELFIO::SHN_UNDEF || si == ELFIO::SHN_ABS) return v;
        if (in.is_relocatable) {
            if (si < in.sec_map.size()) return secs[in.sec_map[si]].addr + v;
            return v;
        }
        return in.base + v;
    }

    void collect_sections(){
        secs.clear(); sec_primary_funcs.clear(); alloc_secs_.clear();
        size_t total = 0;
        for (const auto& in : inputs){
            total += in.reader->sections.size();
        }
        secs.reserve(total);
        for (auto& in : inputs){
            auto &r = *in.reader;
            in.sec_map.assign(r.sections.size(), 0);
            u64 cur = in.base;
            for (u32 i=0;i<r.sections.size();++i){
                const auto* s = r.sections[i];
                u64 addr = 0;
                if (in.is_relocatable) {
                    if (s->get_flags() & ELFIO::SHF_ALLOC) {
                        u64 align = s->get_addr_align();
                        cur = align_up(cur, align);
                        addr = cur;
                        cur += s->get_size();
                    }
                } else {
                    addr = in.base + s->get_address();
                }
                const u32 gid = (u32)secs.size();
            SectionInfo si;
            si.sec    = const_cast<ELFIO::section*>(s);
            si.name   = s->get_name();
            si.addr   = addr;
            si.size   = s->get_size();
            si.offset = s->get_offset();
            si.flags  = s->get_flags();
            si.idx    = gid;
            secs.push_back(std::move(si));
                in.sec_map[i] = gid;
            }
        }
        sec_primary_funcs.resize(secs.size());

        // 构建 alloc 节区间表（只含 SHF_ALLOC）
        alloc_secs_.reserve(secs.size());
        for (const auto &S : secs){
            if (!S.sec) continue;
            if (!(S.flags & ELFIO::SHF_ALLOC)) continue;
            alloc_secs_.push_back({S.addr, S.addr+S.size, S.idx});
        }
        std::sort(alloc_secs_.begin(), alloc_secs_.end(),
                  [](const Range&a, const Range&b){ return a.start < b.start; });
    }

    u32 add_symbol(const std::string& nm, u64 addr, u64 size, unsigned char type, u16 sec_idx, u32 origin, bool* was_new=nullptr){
        if(nm.empty()){
            if (was_new) *was_new = false;
            return UINT32_MAX;
        }
        BuildSym bs; bs.name=nm;
        bs.n.addr=addr; bs.n.size=(u32)size; bs.sec_idx=sec_idx; bs.defined=(sec_idx!=ELFIO::SHN_UNDEF);
        if (type==ELFIO::STT_FUNC) bs.n.kind=0;
        else if (type==ELFIO::STT_OBJECT) bs.n.kind=1;
        else bs.n.kind = (bs.defined && sec_idx<secs.size() && is_exec(secs[sec_idx].flags))?0:1;
        bs.is_primary = (bs.n.kind==0 && !starts_with_dot(nm)) ? 1 : 0;
        bs.origin = origin;

        auto it=name2id.find(bs.name);
        if(it==name2id.end()){
            u32 id=(u32)syms.size();
            syms.push_back(std::move(bs));
            name2id[syms.back().name]=id;
            if (was_new) *was_new = true;
            return id;
        }else{
            auto &cur=syms[it->second];
            if(!cur.defined && bs.defined) cur=std::move(bs);
            if (was_new) *was_new = false;
            return it->second;
        }
    }

    void collect_symbols(){
        // 收集所有符号
        for (u32 fi=0; fi<inputs.size(); ++fi){
            auto &in = inputs[fi];
            auto &r = *in.reader;
            for (u32 si=0; si<r.sections.size(); ++si){
                ELFIO::section* S = r.sections[si];
                if(!S) continue;
                auto t=S->get_type();
                if (t==ELFIO::SHT_SYMTAB || t==ELFIO::SHT_DYNSYM){
                    ELFIO::symbol_section_accessor acc(r, S);
                    const auto n = acc.get_symbols_num();
                    for (ELFIO::Elf_Xword i=0;i<n;++i){
                        std::string nstr; ELFIO::Elf64_Addr v; ELFIO::Elf_Xword sz;
                        unsigned char b,t,other; ELFIO::Elf_Half si;
                        acc.get_symbol(i,nstr,v,sz,b,t,si,other);
                        u16 sec_idx = map_sec_idx(in, si);
                        u64 addr = sym_addr(in, si, v);
                        add_symbol(nstr, addr, sz, t, sec_idx, fi);
                    }
                }
            }
        }

        const u32 N = (u32)syms.size();
        adj.assign(N, {}); data_refs.assign(N, {});
        data_is_writable.assign(N, 0); calls_blacklisted.assign(N, 0);

        // 标记 data 可写
        for (u32 i=0;i<N;++i){
            auto &s = syms[i];
            if (s.defined && s.n.kind==1 && s.sec_idx<secs.size() && is_write(secs[s.sec_idx].flags)){
                data_is_writable[i]=1;
            }
        }
        // 组建“主函数入口”表
        for (u32 i=0;i<N;++i){
            auto &s = syms[i];
            if (!s.defined || s.n.kind!=0 || !s.is_primary) continue;
            if (s.sec_idx >= secs.size()) continue;
            sec_primary_funcs[s.sec_idx].push_back(i);
        }
        // 按地址排序 + 统一重算主函数区间
        fun_ranges_.clear();
        alias_by_start_.clear();
        for (u32 sid=0; sid<sec_primary_funcs.size(); ++sid){
            auto &vec = sec_primary_funcs[sid];
            std::sort(vec.begin(), vec.end(),
                      [&](u32 a,u32 b){ return syms[a].n.addr < syms[b].n.addr; });
            const u64 sec_end = (sid < secs.size()) ? secs[sid].addr + secs[sid].size : ~0ULL;
            for (size_t k=0;k<vec.size();){
                const u64 cur = syms[vec[k]].n.addr;
                size_t k2 = k + 1;
                while (k2 < vec.size() && syms[vec[k2]].n.addr == cur) ++k2;
                const u64 nxt = (k2 < vec.size()) ? syms[vec[k2]].n.addr : sec_end;
                const u64 span = (nxt>cur && (nxt-cur)<(1ull<<31)) ? (nxt-cur) : 1u;
                if (k2 - k > 1) {
                    auto &grp = alias_by_start_[cur];
                    grp.clear();
                    grp.reserve(k2 - k);
                    for (size_t j=k; j<k2; ++j) grp.push_back(vec[j]);
                }
                for (size_t j=k; j<k2; ++j){
                    BuildSym &fn = syms[vec[j]];
                    fn.n.size = (u32)span;
                    fun_ranges_.push_back({cur, cur+fn.n.size, vec[j]});
                }
                k = k2;
            }
        }
        std::sort(fun_ranges_.begin(), fun_ranges_.end(),
                  [](const Range&a, const Range&b){ return a.start < b.start; });

        // dbg：打印 dbg_sym 所在节的主入口表
        if (debug && !dbg_sym.empty()){
            auto it=name2id.find(dbg_sym);
            if (it!=name2id.end()){
                u32 id=it->second;
                if (syms[id].defined && syms[id].n.kind==0){
                    u16 sid=syms[id].sec_idx;
                    dlog("[RANGE] dbg_sym=%s sec=%s idx=%u start=0x%llx size=%u (primary=%u)\n",
                         syms[id].name.c_str(), (sid<secs.size()?secs[sid].name.c_str():"?"),
                         (unsigned)sid, (unsigned long long)syms[id].n.addr, syms[id].n.size, syms[id].is_primary);
                    dlog("[RANGE] section %s primary table:\n",
                         (sid<secs.size()?secs[sid].name.c_str():"?"));
                    for (u32 fid: sec_primary_funcs[sid]){
                        dlog("  %-40s [0x%llx, 0x%llx)\n",
                             syms[fid].name.c_str(),
                             (unsigned long long)syms[fid].n.addr,
                             (unsigned long long)(syms[fid].n.addr + syms[fid].n.size));
                    }
                }
            }
        }

        // 构建 data_ranges_（用于把“section 符号 + addend”映射回具体数据符号）
        data_ranges_.clear();
        std::vector<std::vector<u32>> sec_data;
        sec_data.resize(secs.size());
        for (u32 i=0;i<N;++i){
            auto &s = syms[i];
            if (!s.defined || s.n.kind!=1) continue;
            if (s.name.empty() || starts_with_dot(s.name)) continue;
            if (s.sec_idx >= secs.size()) continue;
            const auto &S = secs[s.sec_idx];
            if (!(S.flags & ELFIO::SHF_ALLOC)) continue;
            if (is_exec(S.flags)) continue;
            sec_data[s.sec_idx].push_back(i);
        }
        for (u32 sid=0; sid<sec_data.size(); ++sid){
            auto &vec = sec_data[sid];
            if (vec.empty()) continue;
            std::sort(vec.begin(), vec.end(),
                      [&](u32 a,u32 b){ return syms[a].n.addr < syms[b].n.addr; });
            const u64 sec_end = (sid < secs.size()) ? secs[sid].addr + secs[sid].size : ~0ULL;
            for (size_t k=0;k<vec.size();++k){
                const u32 id = vec[k];
                const u64 cur = syms[id].n.addr;
                u64 end = cur;
                if (syms[id].n.size) {
                    end = cur + syms[id].n.size;
                } else {
                    const u64 nxt = (k+1<vec.size()) ? syms[vec[k+1]].n.addr : sec_end;
                    end = (nxt>cur && (nxt-cur)<(1ull<<31)) ? nxt : (cur + 1);
                }
                if (end <= cur) end = cur + 1;
                data_ranges_.push_back({cur, end, id});
            }
        }
        std::sort(data_ranges_.begin(), data_ranges_.end(),
                  [](const Range&a, const Range&b){ return a.start < b.start; });
    }

    // 名单判定
    bool in_hard_bl(const std::string& n) const {
        for (const auto& p: hard_bl_prefix) if (n.rfind(p, 0) == 0) return true;
        return false;
    }
    bool in_soft_ig(const std::string& n) const {
        for (const auto& p: soft_ig) if (n.rfind(p, 0) == 0) return true;
        return false;
    }

    // 二分：fun_ranges_ 中查 addr 落入哪个函数
    std::optional<u32> target_func_by_addr(u64 addr, u32* near_below=nullptr, u32* near_above=nullptr) const {
        i64 lo=0, hi=(i64)fun_ranges_.size()-1, ans=-1;
        while (lo<=hi){
            i64 mid=(lo+hi)>>1;
            const auto &r = fun_ranges_[(size_t)mid];
            if (addr < r.start) hi=mid-1;
            else { ans=mid; lo=mid+1; }
        }
        if (ans>=0){
            const auto &r = fun_ranges_[(size_t)ans];
            if (addr>=r.start && addr<r.end){
                if (near_below) *near_below = r.id;
                if (near_above && (size_t)ans+1<fun_ranges_.size())
                    *near_above = fun_ranges_[(size_t)ans+1].id;
                return r.id;
            }
            if (near_below) *near_below = r.id;
            if (near_above && (size_t)ans+1<fun_ranges_.size())
                *near_above = fun_ranges_[(size_t)ans+1].id;
        }
        return std::nullopt;
    }

    // 二分：data_ranges_ 中查 addr 落入哪个数据符号
    std::optional<u32> target_data_by_addr(u64 addr) const {
        i64 lo=0, hi=(i64)data_ranges_.size()-1, ans=-1;
        while (lo<=hi){
            i64 mid=(lo+hi)>>1;
            const auto &r = data_ranges_[(size_t)mid];
            if (addr < r.start) hi=mid-1;
            else { ans=mid; lo=mid+1; }
        }
        if (ans>=0){
            const auto &r = data_ranges_[(size_t)ans];
            if (addr>=r.start && addr<r.end) return r.id;
        }
        return std::nullopt;
    }

    // 二分：alloc_secs_ 中查 ptr_va 属于哪个节
    const SectionInfo* find_alloc_section(u64 ptr_va) const {
        i64 lo=0, hi=(i64)alloc_secs_.size()-1, ans=-1;
        while (lo<=hi){
            i64 mid=(lo+hi)>>1;
            const auto &r = alloc_secs_[(size_t)mid];
            if (ptr_va < r.start) hi=mid-1;
            else { ans=mid; lo=mid+1; }
        }
        if (ans>=0){
            const auto &r = alloc_secs_[(size_t)ans];
            if (ptr_va>=r.start && ptr_va<r.end) return secs[r.id].sec ? &secs[r.id] : nullptr;
        }
        return nullptr;
    }

    // 写边
    const std::vector<u32>* alias_group(u32 u) const {
        auto it = alias_by_start_.find(syms[u].n.addr);
        return (it == alias_by_start_.end()) ? nullptr : &it->second;
    }
    void mark_calls_blacklisted(u32 u){
        if (auto g = alias_group(u)){
            for (u32 uu : *g) calls_blacklisted[uu] = 1;
        } else {
            calls_blacklisted[u] = 1;
        }
    }
    void add_edge(u32 u,u32 v){
        if(u==v) return;
        if (auto g = alias_group(u)){
            for (u32 uu : *g){
                if (uu==v) continue;
                auto &vct=adj[uu];
                if(std::find(vct.begin(),vct.end(),v)==vct.end()) vct.push_back(v);
            }
            return;
        }
        auto &vct=adj[u];
        if(std::find(vct.begin(),vct.end(),v)==vct.end()) vct.push_back(v);
    }
    void add_data_ref(u32 u,u32 v){
        if(u==v) return;
        if (auto g = alias_group(u)){
            for (u32 uu : *g){
                if (uu==v) continue;
                auto &vct=data_refs[uu];
                if(std::find(vct.begin(),vct.end(),v)==vct.end()) vct.push_back(v);
            }
            return;
        }
        auto &vct=data_refs[u];
        if(std::find(vct.begin(),vct.end(),v)==vct.end()) vct.push_back(v);
    }

    // 重定位：owner/target 用主表（更稳）
    void add_edges_from_relocs(){
        // 伪 GOT：先从 .rela.data* 收集“slot(offset) -> imported symbol”
        // 然后在 .rela.text* 里识别 RIP-relative 访问到该 slot 的指令，补齐 code->import 边。
        std::unordered_map<u64, u32> pseudo_got_import_slots;
        pseudo_got_import_slots.reserve(4096);

        for (u32 fi=0; fi<inputs.size(); ++fi){
            auto &in = inputs[fi];
            if (!in.is_relocatable) continue; // 伪 GOT 仅出现在可重定位的 LKM
            auto &r = *in.reader;
            for (u32 si=0; si<r.sections.size(); ++si){
                ELFIO::section* s = r.sections[si];
                if(!s) { continue; }
                auto ty=s->get_type();
                if (ty!=ELFIO::SHT_REL && ty!=ELFIO::SHT_RELA) { continue; }

                auto info=s->get_info();
                if (info>=r.sections.size()) { continue; }
                u16 targ_idx = map_sec_idx(in, (ELFIO::Elf_Half)info);
                if (targ_idx>=secs.size()) { continue; }

                const auto& tsec = secs[targ_idx];
                if (!(tsec.flags & ELFIO::SHF_ALLOC)) continue;
                if (is_exec(tsec.flags)) continue;
                if (!is_write(tsec.flags)) continue; // 只关心可写 data（伪 GOT）

                auto link_idx = s->get_link();
                if (link_idx>=r.sections.size()) { continue; }
                ELFIO::section* link = r.sections[link_idx];
                if (!link) { continue; }
                auto tlink = link->get_type();
                if (tlink!=ELFIO::SHT_SYMTAB && tlink!=ELFIO::SHT_DYNSYM) { continue; }

                ELFIO::symbol_section_accessor acc(r, const_cast<ELFIO::section*>(link));
                ELFIO::relocation_section_accessor rels(r, s);
                for (ELFIO::Elf_Xword i=0;i<rels.get_entries_num();++i){
                    ELFIO::Elf64_Addr off=0; ELFIO::Elf_Word sym=0; unsigned type=0; ELFIO::Elf_Sxword addend=0;
                    rels.get_entry(i,off,sym,type,addend);
                    if (type != R_X86_64_64) continue;

                    std::string nm; ELFIO::Elf64_Addr v; ELFIO::Elf_Xword sz; unsigned char b,t,other; ELFIO::Elf_Half sidx;
                    acc.get_symbol(sym,nm,v,sz,b,t,sidx,other);
                    if (nm.empty()) continue;
                    if (sidx != ELFIO::SHN_UNDEF) continue; // 只记录 import

                    u16 sec_idx = map_sec_idx(in, sidx);
                    u64 addr = sym_addr(in, sidx, v);
                    bool was_new = false;
                    u32 vid = add_symbol(nm, addr, sz, t, sec_idx, fi, &was_new);
                    if (vid==UINT32_MAX) continue;
                    if (was_new){
                        adj.emplace_back(); data_refs.emplace_back();
                        data_is_writable.push_back(0); calls_blacklisted.push_back(0);
                        if (syms[vid].defined && syms[vid].n.kind==1 && sec_idx<secs.size() && is_write(secs[sec_idx].flags)){
                            data_is_writable[vid]=1;
                        }
                    }

                    pseudo_got_import_slots.emplace(sec_off_key((u32)targ_idx, (u32)off), vid);
                }
            }
        }

        // PC32 的 addend 并不总是 “-4”，取决于重定位字段在指令中的位置（例如 mov imm->mem 的 disp32 不在指令末尾）。
        // 为了正确反推出“真实目标地址”，需要计算 (insn_end - reloc_field_addr) 这个 delta。
        csh cs_h = 0;
        bool cs_ready = false;
        std::unordered_map<u64, u32> pc32_delta_cache;
        pc32_delta_cache.reserve(4096);
        auto pc32_delta = [&](u16 sec_idx, u64 reloc_at) -> u32 {
            auto it = pc32_delta_cache.find(reloc_at);
            if (it != pc32_delta_cache.end()) return it->second;
            const auto &S = secs[sec_idx];
            u32 delta = 4;
            if (!S.sec || !is_exec(S.flags)) { pc32_delta_cache.emplace(reloc_at, delta); return delta; }
            const uint8_t* buf = reinterpret_cast<const uint8_t*>(S.sec->get_data());
            if (!buf || S.size == 0) { pc32_delta_cache.emplace(reloc_at, delta); return delta; }
            if (!cs_ready) {
                if (cs_open(CS_ARCH_X86, CS_MODE_64, &cs_h) != CS_ERR_OK) {
                    pc32_delta_cache.emplace(reloc_at, delta);
                    return delta;
                }
                cs_option(cs_h, CS_OPT_DETAIL, CS_OPT_OFF);
                cs_ready = true;
            }
            cs_insn* insn = cs_malloc(cs_h);
            if (!insn) { pc32_delta_cache.emplace(reloc_at, delta); return delta; }
            const uint8_t* p = buf;
            size_t len = (size_t)S.size;
            u64 va = S.addr;
            while (len > 0) {
                const uint8_t* p_before = p; u64 va_before = va; size_t len_before = len;
                if (!cs_disasm_iter(cs_h, &p, &len, &va, insn)) {
                    if (len_before <= 1) break;
                    p = p_before + 1; len = len_before - 1; va = va_before + 1;
                    continue;
                }
                const u64 insn_end = insn->address + insn->size;
                if (reloc_at >= insn->address && reloc_at < insn_end) {
                    delta = (u32)(insn_end - reloc_at);
                    break;
                }
            }
            cs_free(insn, 1);
            pc32_delta_cache.emplace(reloc_at, delta);
            return delta;
        };

        for (u32 fi=0; fi<inputs.size(); ++fi){
            auto &in = inputs[fi];
            auto &r = *in.reader;
            for (u32 si=0; si<r.sections.size(); ++si){
                ELFIO::section* s = r.sections[si];
                if(!s) { continue; }
                auto ty=s->get_type();
                if (ty!=ELFIO::SHT_REL && ty!=ELFIO::SHT_RELA) { continue; }

                auto info=s->get_info();
                if (info>=r.sections.size()) { continue; }
                u16 targ_idx = map_sec_idx(in, (ELFIO::Elf_Half)info);
                if (targ_idx>=secs.size()) { continue; }

                ELFIO::relocation_section_accessor rels(r, s);
                for (ELFIO::Elf_Xword i=0;i<rels.get_entries_num();++i){
                    ELFIO::Elf64_Addr off=0; ELFIO::Elf_Word sym=0; unsigned type=0; ELFIO::Elf_Sxword addend=0;
                    rels.get_entry(i,off,sym,type,addend);
                    u64 at = secs[targ_idx].addr + off;

                    // owner by ranges
                    auto owner = target_func_by_addr(at);
                    if (!owner) { continue; }
                    u32 u = *owner;
                    u32 pc32_adj = 4;
                    if (type == R_X86_64_PC32 && in.is_relocatable && is_exec(secs[targ_idx].flags)) {
                        pc32_adj = pc32_delta(targ_idx, at);
                    }

                auto link_idx = s->get_link();
                if (link_idx>=r.sections.size()) { continue; }
                ELFIO::section* link = r.sections[link_idx];
                    if (!link) { continue; }
                    auto tlink = link->get_type();
                    if (tlink!=ELFIO::SHT_SYMTAB && tlink!=ELFIO::SHT_DYNSYM) { continue; }

                    ELFIO::symbol_section_accessor acc(r, const_cast<ELFIO::section*>(link));
                    std::string nm; ELFIO::Elf64_Addr v; ELFIO::Elf_Xword sz; unsigned char b,t,other; ELFIO::Elf_Half sidx;
                    acc.get_symbol(sym,nm,v,sz,b,t,sidx,other);
                    // 对于 STT_SECTION 符号，symtab 的 st_name 往往为空；但重定位会用它来表示 .text/.data/.bss 等。
                    // 若直接跳过，会漏掉“伪 GOT”以及大量 RIP-relative data 引用。
                    if (nm.empty() && sidx != ELFIO::SHN_UNDEF && sidx != ELFIO::SHN_ABS &&
                        sidx < r.sections.size() && r.sections[sidx]) {
                        nm = r.sections[sidx]->get_name();
                        if (!nm.empty()) nm += "@" + std::to_string(fi);
                    }

                    u16 sec_idx = map_sec_idx(in, sidx);
                    u64 addr = sym_addr(in, sidx, v);
                    bool was_new = false;
                    u32 vid = add_symbol(nm, addr, sz, t, sec_idx, fi, &was_new);
                    if (vid==UINT32_MAX) continue;
                    if (was_new){
                        adj.emplace_back(); data_refs.emplace_back();
                        data_is_writable.push_back(0); calls_blacklisted.push_back(0);
                        if (syms[vid].defined && syms[vid].n.kind==1 && sec_idx<secs.size() && is_write(secs[sec_idx].flags)){
                            data_is_writable[vid]=1;
                        }
                    }

                    // 若这是 RIP-relative 访问伪 GOT slot（典型 R_X86_64_PC32），补齐对 slot 指向的 import 的依赖
                    if (type == R_X86_64_PC32 && syms[vid].defined && syms[vid].sec_idx < secs.size()){
                        const u16 dsec = syms[vid].sec_idx;
                        const auto& ds = secs[dsec];
                        if ((ds.flags & ELFIO::SHF_ALLOC) && !is_exec(ds.flags) && is_write(ds.flags)){
                            const i64 sym_off = (i64)syms[vid].n.addr - (i64)ds.addr;
                            const i64 slot_off = sym_off + (i64)addend + (i64)pc32_adj;
                            if (slot_off >= 0 && (u64)slot_off < ds.size){
                                auto it = pseudo_got_import_slots.find(sec_off_key((u32)dsec, (u32)slot_off));
                                if (it != pseudo_got_import_slots.end()){
                                    const u32 imp = it->second;
                                    if (syms[imp].n.kind==0){
                                        const std::string &nm2 = syms[imp].name;
                                        if (in_soft_ig(nm2)) { if (want(u)) dlog("[PSEUDOGOT] %s -> %s (soft-ignore)\n", syms[u].name.c_str(), nm2.c_str()); }
                                        else if (in_hard_bl(nm2)) { if (want(u)) dlog("[PSEUDOGOT] %s -> %s (hard-BL; mark UNSAFE)\n", syms[u].name.c_str(), nm2.c_str()); mark_calls_blacklisted(u); }
                                        else { if (want(u)) dlog("[PSEUDOGOT] %s -> %s (edge)\n", syms[u].name.c_str(), nm2.c_str()); add_edge(u, imp); }
                                    } else {
                                        if (want(u)) dlog("[PSEUDOGOT] %s -> DATA[%s]\n", syms[u].name.c_str(), syms[imp].name.c_str());
                                        add_data_ref(u, imp);
                                    }
                                }
                            }
                        }
                    }

                    if (syms[vid].n.kind==0){
                        u32 tgt = vid;
                        // 对于 R_X86_64_PC32，很多 LKM 会用 section 符号（如 .text）+ addend 表示“模块内目标地址”。
                        // 这里用 S + A + (insn_end - reloc_field) 反算真实目标虚拟地址，并映射到主函数区间。
                        if (type == R_X86_64_PC32){
                            const u64 tgt_va = syms[vid].n.addr + (i64)addend + (i64)pc32_adj;
                            if (auto to = target_func_by_addr(tgt_va)) tgt = *to;
                        }
                        const std::string &nm2 = syms[tgt].name;
                        if (in_soft_ig(nm2)) { if (want(u)) dlog("[RELOC] %s -> %s (soft-ignore)\n", syms[u].name.c_str(), nm2.c_str()); continue; }
                        if (in_hard_bl(nm2)) { if (want(u)) dlog("[RELOC] %s -> %s (hard-BL; mark UNSAFE)\n", syms[u].name.c_str(), nm2.c_str()); mark_calls_blacklisted(u); continue; }
                        if (want(u)) dlog("[RELOC] %s -> %s (edge)\n", syms[u].name.c_str(), nm2.c_str());
                        add_edge(u, tgt);
                    } else {
                        u32 ref = vid;
                        if (type == R_X86_64_PC32 && syms[vid].defined){
                            const u64 tgt_va = syms[vid].n.addr + (i64)addend + (i64)pc32_adj;
                            if (auto to = target_data_by_addr(tgt_va)) ref = *to;
                        }
                        if (want(u)) dlog("[RELOC] %s -> DATA[%s]\n", syms[u].name.c_str(), syms[ref].name.c_str());
                        add_data_ref(u, ref);
                    }
                }
            }
        }
        if (cs_ready) cs_close(&cs_h);
    }

    // 反汇编：IMM + MEM(RIP/ABS)
    void add_edges_from_disasm(){
        csh h; if (cs_open(CS_ARCH_X86, CS_MODE_64, &h)!=CS_ERR_OK) return;
        cs_option(h, CS_OPT_DETAIL, CS_OPT_ON);

        for (auto &sec: secs){
            if(!sec.sec) { continue; }
            if(!is_exec(sec.flags)) { continue; }

            const uint8_t* buf = reinterpret_cast<const uint8_t*>(sec.sec->get_data());
            if(!buf || sec.size==0) { continue; }

            cs_insn* insn = cs_malloc(h);
            if (!insn) { continue; }

            const uint8_t* p = buf; size_t len = (size_t)sec.size; u64 va = sec.addr;

            while (len > 0){
                const uint8_t* p_before = p; u64 va_before = va; size_t len_before = len;
                if (!cs_disasm_iter(h, &p, &len, &va, insn)){
                    if (len_before <= 1) { break; }
                    p = p_before + 1; len = len_before - 1; va = va_before + 1;
                    continue;
                }

                // owner by ranges
                auto owner = target_func_by_addr(insn->address);
                if (!owner) { continue; }
                u32 u = *owner;
                const cs_detail* d = insn->detail;
                bool is_call = (insn->id==X86_INS_CALL);
                bool is_jmp  = (insn->id==X86_INS_JMP);

                // CALL IMM：ABS→REL
                if (is_call){
                    for (u8 oi=0; oi<d->x86.op_count; ++oi){
                        const auto &op = d->x86.operands[oi];
                        if (op.type!=X86_OP_IMM) { continue; }
                        u64 tgt_abs=(u64)op.imm, tgt_rel=insn->address+insn->size+(i64)op.imm;
                        u32 nb=UINT32_MAX, na=UINT32_MAX;
                        auto to=target_func_by_addr(tgt_abs,&nb,&na);
                        if(!to) to=target_func_by_addr(tgt_rel,&nb,&na);
                        if (!to){
                            if (want(u)) dlog("[CALL IMM] %s @0x%llx -> abs=0x%llx rel=0x%llx (no-map; near=[%s|%s])\n",
                                              syms[u].name.c_str(),
                                              (unsigned long long)insn->address,
                                              (unsigned long long)tgt_abs, (unsigned long long)tgt_rel,
                                              (nb!=UINT32_MAX? syms[nb].name.c_str():"-"),
                                              (na!=UINT32_MAX? syms[na].name.c_str():"-"));
                            continue;
                        }
                        u32 v=*to; const std::string &nm=syms[v].name;
                        if (in_soft_ig(nm)) { if (want(u)) dlog("[CALL IMM] %s -> %s (soft-ignore)\n", syms[u].name.c_str(), nm.c_str()); continue; }
                        if (in_hard_bl(nm)) { if (want(u)) dlog("[CALL IMM] %s -> %s (HARD-BL; mark UNSAFE)\n", syms[u].name.c_str(), nm.c_str()); mark_calls_blacklisted(u); continue; }
                        if (want(u)) dlog("[CALL IMM] %s -> %s (edge)\n", syms[u].name.c_str(), nm.c_str());
                        add_edge(u,v);
                    }
                }

                // MEM：RIP+disp 或 ABS
                for (u8 oi=0; oi<d->x86.op_count; ++oi){
                    const auto &op = d->x86.operands[oi];
                    if (op.type!=X86_OP_MEM) { continue; }
                    if (!(is_call || is_jmp)) { continue; }

                    u64 ptr_va = 0;
                    const char* tag = nullptr;

                    if (op.mem.base == X86_REG_RIP){
                        ptr_va = insn->address + insn->size + (i64)op.mem.disp;
                        tag = "RIP+";
                    } else if (op.mem.base == X86_REG_INVALID){
                        ptr_va = (u64)op.mem.disp; // ABS
                        tag = "ABS";
                    } else {
                        if (want(u)) dlog("[%s MEM] %s -> [reg-base=%d] ignored\n", is_call?"CALL":"JMP", syms[u].name.c_str(), op.mem.base);
                        continue;
                    }

                    const SectionInfo* secp = find_alloc_section(ptr_va);
                    if (!secp){
                        if (want(u)) dlog("[%s %sMEM] %s -> ptr 0x%llx (no-seg)\n",
                                          is_call?"CALL":"JMP", tag, syms[u].name.c_str(), (unsigned long long)ptr_va);
                        continue;
                    }
                    const char* base = secp->sec->get_data();
                    if (!base){
                        if (want(u)) dlog("[%s %sMEM] %s -> ptr 0x%llx (no-data)\n",
                                          is_call?"CALL":"JMP", tag, syms[u].name.c_str(), (unsigned long long)ptr_va);
                        continue;
                    }

                    u64 tgt_va=0;
                    std::memcpy(&tgt_va, base + (ptr_va - secp->addr), sizeof(u64));

                    u32 nb=UINT32_MAX, na=UINT32_MAX;
                    auto to = target_func_by_addr(tgt_va,&nb,&na);
                    if (!to){
                        if (want(u)) dlog("[%s %sMEM] %s -> *0x%llx (no-map; near=[%s|%s])\n",
                                          is_call?"CALL":"JMP", tag, syms[u].name.c_str(), (unsigned long long)tgt_va,
                                          (nb!=UINT32_MAX? syms[nb].name.c_str():"-"),
                                          (na!=UINT32_MAX? syms[na].name.c_str():"-"));
                        continue;
                    }
                    u32 v=*to; const std::string &nm=syms[v].name;
                    if (in_soft_ig(nm)) { if (want(u)) dlog("[%s %sMEM] %s -> %s (soft-ignore)\n", is_call?"CALL":"JMP", tag, syms[u].name.c_str(), nm.c_str()); continue; }
                    if (is_call && in_hard_bl(nm)) { if (want(u)) dlog("[CALL %sMEM] %s -> %s (HARD-BL; mark UNSAFE)\n", tag, syms[u].name.c_str(), nm.c_str()); mark_calls_blacklisted(u); continue; }
                    if (is_jmp && v==u) { if (want(u)) dlog("[JMP %sMEM] %s -> (intra) ignored\n", tag, syms[u].name.c_str()); continue; }
                    if (want(u)) dlog("[%s %sMEM] %s -> %s (edge)\n", is_call?"CALL":"JMP", tag, syms[u].name.c_str(), nm.c_str());
                    add_edge(u,v);
                }

                // JMP IMM：仅跨函数
                if (is_jmp){
                    for (u8 oi=0; oi<d->x86.op_count; ++oi){
                        const auto &op = d->x86.operands[oi];
                        if (op.type!=X86_OP_IMM) { continue; }
                        u64 tgt_abs=(u64)op.imm, tgt_rel=insn->address+insn->size+(i64)op.imm;
                        u32 nb=UINT32_MAX, na=UINT32_MAX;
                        auto to=target_func_by_addr(tgt_abs,&nb,&na);
                        if(!to) to=target_func_by_addr(tgt_rel,&nb,&na);
                        if (!to){
                            if (want(u)) dlog("[JMP IMM] %s -> abs=0x%llx rel=0x%llx (no-map; near=[%s|%s])\n",
                                              syms[u].name.c_str(),
                                              (unsigned long long)tgt_abs, (unsigned long long)tgt_rel,
                                              (nb!=UINT32_MAX? syms[nb].name.c_str():"-"),
                                              (na!=UINT32_MAX? syms[na].name.c_str():"-"));
                            continue;
                        }
                        u32 v=*to;
                        if (v==u) { if (want(u)) dlog("[JMP IMM] %s -> (intra) ignored\n", syms[u].name.c_str()); continue; }
                        const std::string &nm=syms[v].name;
                        if (in_soft_ig(nm)) { if (want(u)) dlog("[JMP IMM] %s -> %s (soft-ignore)\n", syms[u].name.c_str(), nm.c_str()); continue; }
                        if (in_hard_bl(nm)) { if (want(u)) dlog("[JMP IMM] %s -> %s (hard-BL filtered)\n", syms[u].name.c_str(), nm.c_str()); continue; }
                        if (want(u)) dlog("[JMP IMM] %s -> %s (edge)\n", syms[u].name.c_str(), nm.c_str());
                        add_edge(u,v);
                    }
                }
            }
            cs_free(insn,1);
        }
    }

    // SAFE 剪枝
    std::vector<u8> prune_to_safe_subgraph(){
        const u32 N=(u32)syms.size();
        std::vector<u8> ok(N,0);

        auto data_refs_ok = [&](u32 u)->bool{
            for (u32 v: data_refs[u]){
                if (v>=N) continue;
                if (syms[v].n.kind!=1) continue;
                if (!data_is_writable[v]) continue;
                // LKM 的“伪 GOT”是写段 data：允许访问本模块内的可写 data（地址填充压力转移到数据段）
                if (syms[u].origin != 0 && syms[u].origin == syms[v].origin) continue;
                return false;
            }
            return true;
        };

        // 初筛
        for (u32 u=0; u<N; ++u){
            if (syms[u].n.kind!=0) continue;
            if (!syms[u].defined) continue;
            if (calls_blacklisted[u]) {
                if (want(u)) dlog("[PRUNE] drop %s : CALL-hardBL\n", syms[u].name.c_str());
                continue;
            }
            if (!data_refs_ok(u)) {
                if (want(u)) dlog("[PRUNE] drop %s : writable-data\n", syms[u].name.c_str());
                continue;
            }
            ok[u]=1;
        }
        // 清空不安全函数出边
        for (u32 u=0; u<N; ++u){
            if (syms[u].n.kind!=0) continue;
            if (!ok[u]){
                adj[u].clear(); data_refs[u].clear();
            } else if (want(u)){
                dlog("[PRUNE] keep %s\n", syms[u].name.c_str());
            }
        }
        return ok;
    }

    // 保存 SAFE 子图
    bool save(const std::string& out_path){
        std::vector<u8> ok = prune_to_safe_subgraph();

        const u32 N=(u32)syms.size();
        std::vector<u8> need(N, 0);
        for (u32 i=0;i<N;++i){
            if (syms[i].n.kind==0 && ok[i]) need[i]=1;
        }
        // 额外包含 SAFE code 直接调用到的函数（即便它们本身不在 SAFE 集内，也需要作为“依赖叶子”输出）
        for (u32 u=0; u<N; ++u){
            if (syms[u].n.kind!=0 || !ok[u]) continue;
            for (u32 v: adj[u]){
                if (v>=N) continue;
                if (syms[v].n.kind!=0) continue;
                if (!syms[v].defined) continue;
                need[v]=1;
            }
        }
        // 保留 safe code 直接引用的数据符号（用于下游处理 rodata/data 依赖；伪 GOT 也在 data）
        for (u32 u=0; u<N; ++u){
            if (!need[u]) continue;
            if (syms[u].n.kind!=0) continue;
            for (u32 v: data_refs[u]){
                if (v>=N) continue;
                if (syms[v].n.kind!=1) continue;
                if (!syms[v].defined) continue;
                if (starts_with_dot(syms[v].name)) continue;
                need[v]=1;
            }
        }

        std::vector<i32> idmap(N,-1);
        u32 M=0;
        for (u32 i=0;i<N;++i){
            if (!need[i]) continue;
            idmap[i]=(i32)M++;
        }

        // [KASLR@build] 计算 delta（run__stext - vml__stext），并在 header 标记为 runtime
        u64 delta = 0;
        bool have_delta = false;
        {
            // 找到 vmlinux 中的 _stext 静态地址
            auto it = name2id.find("_stext");
            if (it != name2id.end()) {
                u32 gid = it->second;
                u64 vml_stext = syms[gid].n.addr;

                // 读运行时 /proc/kallsyms 的 _stext
                if (auto run_stext = read_kallsyms_addr("_stext")) {
                    // 非特权环境下 /proc/kallsyms 可能被 kptr_restrict 隐藏为 0
                    if (*run_stext != 0) {
                        delta = *run_stext - vml_stext;
                        have_delta = true;
                    }
                }
            }
        }

        // 计算模块运行时 section base（用于把合成地址转换为真实内核地址）
        std::vector<std::unordered_map<u32,u64>> mod_sec_base(inputs.size());
        std::vector<std::optional<u64>> mod_text_base(inputs.size());
        std::vector<std::string> mod_sys_names(inputs.size());
        std::vector<std::string> mod_out_names(inputs.size());
        if (!mod_sys_names.empty()) mod_sys_names[0] = "kernel";
        if (!mod_out_names.empty()) mod_out_names[0] = KERNEL_MODULE_LABEL;
        for (u32 fi=1; fi<inputs.size(); ++fi){
            const auto& in = inputs[fi];
            std::string mod = module_sys_name(in.path, *in.reader);
            if (mod.empty()){
                std::fprintf(stderr, "[KRG] module path '%s' has empty name\n", in.path.c_str());
                return false;
            }
            mod_sys_names[fi] = mod;
            mod_out_names[fi] = in.path;
            auto text = read_hex_file("/sys/module/" + mod + "/sections/.text");
            if (!text || *text == 0){
                // 无权限或模块未加载：允许继续构图，但地址为“静态/合成地址”，而非真实运行时地址。
                std::fprintf(stderr,
                             "[KRG] module '%s': runtime section base unavailable; using static addresses for this module\n",
                             mod.c_str());
                continue;
            }
            mod_text_base[fi] = *text;
            auto &r = *in.reader;
            for (u32 si=0; si<r.sections.size(); ++si){
                ELFIO::section* s = r.sections[si];
                if (!s) continue;
                if (!(s->get_flags() & ELFIO::SHF_ALLOC)) continue;
                const std::string &sec_name = s->get_name();
                auto sec_base = read_hex_file("/sys/module/" + mod + "/sections/" + sec_name);
                if (!sec_base) continue;
                if (si < in.sec_map.size()){
                    mod_sec_base[fi][in.sec_map[si]] = *sec_base;
                }
            }
        }

        // 模块字符串表（输出用：kernel 固定为 "[kernel]"，其余为 .ko 路径）
        std::vector<u32> module_off; module_off.reserve(mod_out_names.size());
        std::string module_blob; module_blob.reserve(mod_out_names.size() * 32);
        for (const auto& mn : mod_out_names){
            std::string name = mn.empty() ? KERNEL_MODULE_LABEL : mn;
            module_off.push_back((u32)module_blob.size());
            module_blob.append(name);
            module_blob.push_back('\0');
        }

        // 节点 + 名字
        std::vector<Node> nodes; nodes.reserve(M);
        std::vector<u32> name_off; name_off.reserve(M);
        std::string blob; blob.reserve(M*16);
        for (u32 i=0;i<N;++i){
            i32 ni=idmap[i]; if (ni<0) continue;
            Node out = syms[i].n;
            out.module = (syms[i].origin < module_off.size()) ? (u16)syms[i].origin : 0;
            if (syms[i].origin == 0) {
                if (have_delta) out.addr += delta;
            } else {
                const u32 origin = syms[i].origin;
                const bool have_mod_runtime =
                    (origin < mod_text_base.size() && mod_text_base[origin].has_value()) ||
                    (origin < mod_sec_base.size() && !mod_sec_base[origin].empty());
                if (have_mod_runtime) {
                    bool adjusted = false;
                    if (origin < mod_sec_base.size()) {
                        auto it = mod_sec_base[origin].find(syms[i].sec_idx);
                        if (it != mod_sec_base[origin].end() && syms[i].sec_idx < secs.size()) {
                            u64 off = syms[i].n.addr - secs[syms[i].sec_idx].addr;
                            out.addr = it->second + off;
                            adjusted = true;
                        }
                    }
                    if (!adjusted && origin < mod_text_base.size() && mod_text_base[origin].has_value() &&
                        syms[i].sec_idx < secs.size() && secs[syms[i].sec_idx].name == ".text") {
                        u64 off = syms[i].n.addr - secs[syms[i].sec_idx].addr;
                        out.addr = *mod_text_base[origin] + off;
                        adjusted = true;
                    }
                    if (!adjusted) {
                        const char* mod = (origin < mod_sys_names.size() && !mod_sys_names[origin].empty()) ? mod_sys_names[origin].c_str() : "?";
                        const char* sec = (syms[i].sec_idx < secs.size()) ? secs[syms[i].sec_idx].name.c_str() : "?";
                        std::fprintf(stderr, "[KRG] module '%s' section '%s' runtime base missing; rebuild with module loaded\n", mod, sec);
                        return false;
                    }
                }
            }
            nodes.push_back(out);
            name_off.push_back((u32)blob.size());
            blob.append(syms[i].name); blob.push_back('\0');
        }

        // CSR（仅保留被序列化的 node 之间的边；code->data 也会写入）
        std::vector<u32> row_ptr(M+1,0), col_idx; col_idx.reserve(M*2);
        for (u32 i=0;i<N;++i){
            i32 ui=idmap[i]; if (ui<0) continue;
            row_ptr[ui]=(u32)col_idx.size();
            std::vector<u32> tmp = adj[i];
            tmp.insert(tmp.end(), data_refs[i].begin(), data_refs[i].end());
            std::sort(tmp.begin(), tmp.end());
            tmp.erase(std::unique(tmp.begin(), tmp.end()), tmp.end());
            for (u32 x : tmp){
                i32 vx=idmap[x]; if (vx<0) continue;
                if (ui==vx) continue;
                col_idx.push_back((u32)vx);
            }
        }
        row_ptr[M]=(u32)col_idx.size();

        FileHeader H;
        H.n_nodes = M;
        H.n_edges = (u32)col_idx.size();
        H.name_blob_bytes = (u32)blob.size();
        H.arch = 0;
        H.n_modules = (u32)module_off.size();
        H.module_blob_bytes = (u32)module_blob.size();

        std::FILE* f=std::fopen(out_path.c_str(),"wb");
        if(!f){ std::perror("fopen"); return false; }
        auto W=[&](const void* p,size_t n){
            if(std::fwrite(p,1,n,f)!=n){ std::perror("fwrite"); std::fclose(f); return false;}
            return true;
        };

        if(!W(&H,sizeof(H))) return false;
        if(M && !W(nodes.data(), nodes.size()*sizeof(Node))) return false;
        if((M+1)&&!W(row_ptr.data(), row_ptr.size()*sizeof(u32))) return false;
        if(H.n_edges && !W(col_idx.data(), col_idx.size()*sizeof(u32))) return false;
        if(M && !W(name_off.data(), name_off.size()*sizeof(u32))) return false;
        if(H.name_blob_bytes && !W(blob.data(), blob.size())) return false;
        if(H.n_modules && !W(module_off.data(), module_off.size()*sizeof(u32))) return false;
        if(H.module_blob_bytes && !W(module_blob.data(), module_blob.size())) return false;
        std::fclose(f);

        if (debug) std::fprintf(stderr,"[SAVE] safe nodes=%u, edges=%u -> %s\n", M, H.n_edges, out_path.c_str());
        else       std::fprintf(stderr,"Built SAFE graph: nodes=%u edges=%u -> %s\n", M, H.n_edges, out_path.c_str());
        return true;
    }
};

// ---------- Graph & Query ----------
struct Graph {
    FileHeader H{};
    std::vector<Node> nodes;
    std::vector<u32> row_ptr, col_idx, name_off;
    std::string blob;
    std::unordered_map<std::string,u32> name2id;
    std::vector<u32> module_off;
    std::string module_blob;
    std::vector<std::string> module_names;
    std::unordered_set<std::string> stop_set;

    Graph(){
        set_stop_names({});
    }

    void set_stop_names(const std::vector<std::string>& extra){
        stop_set.clear();
        for (const auto& s : default_stop_names()) stop_set.insert(s);
        for (const auto& s : extra){
            if (!s.empty()) stop_set.insert(s);
        }
    }

    bool load(const std::string& path){
        std::FILE* f=std::fopen(path.c_str(),"rb");
        if(!f){ std::perror("fopen"); return false; }
        auto R=[&](void* p,size_t n){ return std::fread(p,1,n,f)==n; };

        FileHeaderV1 Hv1{};
        if(!R(&Hv1,sizeof(Hv1))){ std::cerr<<"bad header\n"; std::fclose(f); return false; }
        if(Hv1.magic!=0x3147524b){ std::cerr<<"bad magic\n"; std::fclose(f); return false; }
        H.magic = Hv1.magic;
        H.version = Hv1.version;
        H.n_nodes = Hv1.n_nodes;
        H.n_edges = Hv1.n_edges;
        H.name_blob_bytes = Hv1.name_blob_bytes;
        H.arch = Hv1.arch;
        H.is_runtime_address = Hv1.is_runtime_address;
        H.reserved1 = Hv1.reserved1;
        if (Hv1.version >= 2){
            u32 extra[2]{0,0};
            if(!R(extra, sizeof(extra))){ std::cerr<<"bad header (v2)\n"; std::fclose(f); return false; }
            H.n_modules = extra[0];
            H.module_blob_bytes = extra[1];
        } else {
            H.n_modules = 1;
            H.module_blob_bytes = 0;
        }
        if(H.version!=1 && H.version!=2){
            std::cerr<<"unsupported version\n"; std::fclose(f); return false;
        }

        if (H.version == 1){
            struct NodeV1 { u64 addr; u32 size; u8 kind; u8 pad[3]; };
            std::vector<NodeV1> nodes_v1;
            nodes_v1.resize(H.n_nodes);
            if(H.n_nodes && !R(nodes_v1.data(), nodes_v1.size()*sizeof(NodeV1))){
                std::cerr<<"bad nodes\n"; std::fclose(f); return false;
            }
            nodes.resize(H.n_nodes);
            for (u32 i=0;i<H.n_nodes;++i){
                nodes[i].addr = nodes_v1[i].addr;
                nodes[i].size = nodes_v1[i].size;
                nodes[i].kind = nodes_v1[i].kind;
                nodes[i].module = 0;
                nodes[i].pad = 0;
            }
        } else {
            nodes.resize(H.n_nodes);
            if(H.n_nodes && !R(nodes.data(), nodes.size()*sizeof(Node))){
                std::cerr<<"bad nodes\n"; std::fclose(f); return false;
            }
        }
        row_ptr.resize(H.n_nodes+1);
        if((H.n_nodes+1)&&!R(row_ptr.data(), row_ptr.size()*sizeof(u32))){
            std::cerr<<"bad row_ptr\n"; std::fclose(f); return false;
        }
        col_idx.resize(H.n_edges);
        if(H.n_edges && !R(col_idx.data(), col_idx.size()*sizeof(u32))){
            std::cerr<<"bad col_idx\n"; std::fclose(f); return false;
        }
        name_off.resize(H.n_nodes);
        if(H.n_nodes && !R(name_off.data(), name_off.size()*sizeof(u32))){
            std::cerr<<"bad name_off\n"; std::fclose(f); return false;
        }
        blob.resize(H.name_blob_bytes);
        if(H.name_blob_bytes && !R(blob.data(), blob.size())){
            std::cerr<<"bad blob\n"; std::fclose(f); return false;
        }

        if (H.version >= 2){
            module_off.resize(H.n_modules);
            if(H.n_modules && !R(module_off.data(), module_off.size()*sizeof(u32))){
                std::cerr<<"bad module_off\n"; std::fclose(f); return false;
            }
            module_blob.resize(H.module_blob_bytes);
            if(H.module_blob_bytes && !R(module_blob.data(), module_blob.size())){
                std::cerr<<"bad module_blob\n"; std::fclose(f); return false;
            }
            module_names.clear();
            module_names.reserve(H.n_modules);
            for (u32 i=0;i<H.n_modules;++i){
                if (module_off[i] >= module_blob.size()){
                    std::cerr<<"bad module offset\n"; std::fclose(f); return false;
                }
                const char* s = module_blob.data() + module_off[i];
                module_names.emplace_back(s);
            }
        } else {
            module_names = {KERNEL_MODULE_LABEL};
            module_off = {0};
            module_blob = std::string(KERNEL_MODULE_LABEL);
            module_blob.push_back('\0');
        }
        if (module_names.empty()){
            module_names.push_back(KERNEL_MODULE_LABEL);
        }
        std::fclose(f);

        for (u32 i=0;i<H.n_nodes;++i){
            const char* s = blob.data()+name_off[i];
            name2id.emplace(s,i);
        }
        return true;
    }

    std::optional<u32> id_of(const std::string& name) const {
        auto it=name2id.find(name);
        if(it==name2id.end()) return std::nullopt;
        return it->second;
    }

    void closure_and_print(u32 root) {
        const u32 N = H.n_nodes;
        std::vector<u8> stop_expand(N, 0);
        for (u32 i = 0; i < N; ++i) {
            const char* nm = blob.data() + name_off[i];
            if (stop_set.find(nm) != stop_set.end()) stop_expand[i] = 1;
        }
    
        // 先做一次可达性标记，避免对未达节点输出
        std::vector<u8> seen(N, 0);
        seen[root] = 1;
        std::vector<u32> st; st.reserve(N);
        st.push_back(root);
        while (!st.empty()) {
            u32 u = st.back(); st.pop_back();
            if (stop_expand[u]) continue;
            for (u32 i = row_ptr[u]; i < row_ptr[u + 1]; ++i) {
                u32 v = col_idx[i];
                if (!seen[v]) { seen[v] = 1; st.push_back(v); }
            }
        }
        // build 阶段已将地址固化为 runtime，直接输出
        for (u32 i = 0; i < N; ++i) {
            if (!seen[i]) continue;
            const char* nm = blob.data() + name_off[i];
            const char* mod = KERNEL_MODULE_LABEL;
            if (!module_names.empty() && nodes[i].module < module_names.size()){
                mod = module_names[nodes[i].module].c_str();
            }
            std::printf("%s\t0x%llx\t%u\t%u\t%s\n",
                        nm,
                        (unsigned long long)nodes[i].addr,
                        nodes[i].size,
                        (unsigned)nodes[i].kind,
                        mod);
        }
    }
    
};

static void usage(){
    std::fprintf(stderr,
        "Usage:\n"
        "  krg build vmlinux -o out.krg [-m module.ko ...] [--debug] [--dbg-sym=<name>]\n"
        "  krg query out.krg <symbol>\n");
}

int main(int argc, char** argv){
    if(argc<2){ usage(); return 1; }
    std::string cmd=argv[1];

    if(cmd=="build"){
        if(argc<5){ usage(); return 1; }
        std::string vmlinux=argv[2], out; bool dbg=false; std::string dbg_sym;
        std::vector<std::string> mods;
        for(int i=3;i<argc;++i){
            std::string a=argv[i];
            if(a=="-o" && i+1<argc){ out=argv[++i]; }
            else if(a=="--debug"){ dbg=true; }
            else if(a.rfind("--dbg-sym=",0)==0){ dbg_sym=a.substr(10); }
            else if((a=="-m" || a=="--module") && i+1<argc){ mods.push_back(argv[++i]); }
            else if(a.rfind("--module=",0)==0){ mods.push_back(a.substr(9)); }
        }
        if(out.empty()){
            std::fprintf(stderr,"-o out.krg required\n"); return 1;
        }

        Builder B; B.debug=dbg; B.dbg_sym=dbg_sym;

        if(!B.add_input(vmlinux, 0)){
            std::fprintf(stderr,"Failed to load %s\n", vmlinux.c_str()); return 2;
        }
        const u64 mod_base = 0x1000000000ULL;
        const u64 mod_stride = 0x10000000ULL;
        for (size_t i=0; i<mods.size(); ++i){
            u64 base = mod_base + (u64)i * mod_stride;
            if(!B.add_input(mods[i], base)){
                std::fprintf(stderr,"Failed to load module %s\n", mods[i].c_str()); return 2;
            }
        }
        B.collect_sections();
        B.collect_symbols();
        B.add_edges_from_relocs();
        B.add_edges_from_disasm();

        if(!B.save(out)){
            std::fprintf(stderr,"Save failed\n"); return 3;
        }
        return 0;

    } else if(cmd=="query"){
        if(argc<4){ usage(); return 1; }
        std::string krg_path = argv[2];
        std::string sym;
        std::string shim_path;
        for (int i=3; i<argc; ++i){
            std::string a = argv[i];
            if (a.rfind("--shim=", 0) == 0){
                shim_path = a.substr(7);
            } else if (a == "--shim" && i+1 < argc){
                shim_path = argv[++i];
            } else if (sym.empty()){
                sym = a;
            } else {
                sym = a;
            }
        }
        if (sym.empty()){ usage(); return 1; }

        Graph G; if(!G.load(krg_path)) return 2;
        if (!shim_path.empty()){
            auto syms = read_symbol_list(shim_path);
            G.set_stop_names(syms);
        }
        auto id = G.id_of(sym);
        if(!id){
            std::fprintf(stderr,"Symbol not found: %s\n", sym.c_str()); return 3;
        }
        G.closure_and_print(id.value());
        return 0;

    } else {
        usage(); return 1;
    }
}
