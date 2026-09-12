#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse
from collections import defaultdict

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection
from elftools.elf.sections import SymbolTableSection
from capstone import *
from capstone.x86 import *

# ================= 全局规则配置 =================
PRIV_INSNS = {'cli', 'sti', 'hlt', 'invlpg', 'rdmsr', 'wrmsr', 'in', 'out', 'sysret', 'sysexit'}
CR_REGS = {X86_REG_CR0, X86_REG_CR2, X86_REG_CR3, X86_REG_CR4, X86_REG_CR8}

INSTRUMENTATION_EXACT = {'__fentry__', 'mcount', '__stack_chk_fail', '__stack_chk_fail_local'}
INSTRUMENTATION_PREFIXES = (
    '__asan_',
    '__ubsan_',
    '__tsan_',
    '__kcfi_',
    '__llvm_profile_',
    '__sanitizer_',
)

RETPOLINE_INDIRECT = '__x86_indirect_thunk_'
RETPOLINE_RETURN = ('__x86_return_thunk', '__x86_return_thunk_')

ABSOLUTE_RELOC_TYPES = {1, 10, 11}
PC_REL_RELOC_TYPES = {2, 4}


class C:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


REG_ALIAS_GROUPS = {
    'rax': {'rax', 'eax', 'ax', 'al', 'ah'},
    'rbx': {'rbx', 'ebx', 'bx', 'bl', 'bh'},
    'rcx': {'rcx', 'ecx', 'cx', 'cl', 'ch'},
    'rdx': {'rdx', 'edx', 'dx', 'dl', 'dh'},
    'rsi': {'rsi', 'esi', 'si', 'sil'},
    'rdi': {'rdi', 'edi', 'di', 'dil'},
    'rbp': {'rbp', 'ebp', 'bp', 'bpl'},
    'rsp': {'rsp', 'esp', 'sp', 'spl'},
    'rip': {'rip', 'eip', 'ip'},
    'r8': {'r8', 'r8d', 'r8w', 'r8b'},
    'r9': {'r9', 'r9d', 'r9w', 'r9b'},
    'r10': {'r10', 'r10d', 'r10w', 'r10b'},
    'r11': {'r11', 'r11d', 'r11w', 'r11b'},
    'r12': {'r12', 'r12d', 'r12w', 'r12b'},
    'r13': {'r13', 'r13d', 'r13w', 'r13b'},
    'r14': {'r14', 'r14d', 'r14w', 'r14b'},
    'r15': {'r15', 'r15d', 'r15w', 'r15b'},
}


def load_token_file(filepath):
    tokens = []
    if not filepath or not os.path.exists(filepath):
        return tokens

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            clean_line = line.split('#', 1)[0].strip()
            if clean_line:
                tokens.extend(clean_line.split())
    return tokens


class ELFObj:
    def __init__(self, path, is_vmlinux=False):
        self.path = path
        self.name = os.path.basename(path)
        self.is_vmlinux = is_vmlinux
        self.fp = open(path, 'rb')
        self.elf = ELFFile(self.fp)
        self.symtab = self.elf.get_section_by_name('.symtab')

        if not isinstance(self.symtab, SymbolTableSection):
            raise ValueError(f'[{self.name}] 未找到符号表，文件可能已被 strip。')

        self.sym_dict = {}
        for sym in self.symtab.iter_symbols():
            if sym.name and sym['st_shndx'] != 'SHN_UNDEF':
                self.sym_dict[sym.name] = sym

        self.reloc_cache = {}

    def get_symbol(self, name):
        return self.sym_dict.get(name)

    def get_relocations(self, section_name):
        if section_name in self.reloc_cache:
            return self.reloc_cache[section_name]

        reloc_sec = self.elf.get_section_by_name(f'.rela{section_name}')
        if not isinstance(reloc_sec, RelocationSection):
            reloc_sec = self.elf.get_section_by_name(f'.rel{section_name}')

        relocs = {}
        if isinstance(reloc_sec, RelocationSection):
            for reloc in reloc_sec.iter_relocations():
                relocs[reloc['r_offset']] = reloc

        self.reloc_cache[section_name] = relocs
        return relocs

    def resolve_func_by_offset(self, sec_idx, offset):
        for sym in self.symtab.iter_symbols():
            if sym['st_info']['type'] != 'STT_FUNC':
                continue
            if sym['st_shndx'] != sec_idx:
                continue

            start = sym['st_value']
            end = start + sym['st_size']
            if sym['st_size'] == 0 and start == offset:
                return sym.name
            if start <= offset < end:
                return sym.name
        return None


class AcademicReuseEngine:
    def __init__(self, modules, target_func, shims, vmlinux_path, extra_inst_prefixes=None):
        print(f'{C.BOLD}{C.BLUE}=== LKM 跨边界二进制静态分析引擎 ==={C.RESET}')

        self.modules = [ELFObj(module_path) for module_path in modules] if modules else []
        self.target_func = target_func
        self.shims = set(shims) if shims else set()
        self.inst_exact = set(INSTRUMENTATION_EXACT)
        self.inst_prefixes = tuple(INSTRUMENTATION_PREFIXES) + tuple(extra_inst_prefixes or [])

        if self.modules:
            print(f'[*] 已加载 {len(self.modules)} 个模块对象。')
            for mod in self.modules:
                print(f'    - {mod.name}')
        else:
            print(f'{C.YELLOW}[*] 未提供模块列表，将只在 vmlinux 中解析符号。{C.RESET}')

        if self.shims:
            print(f'[*] 已加载 {len(self.shims)} 个 Shim 平替规则。')
        else:
            print(f'{C.YELLOW}[*] 未提供 Shim 白名单，所有未定义符号都将继续尝试闭包解析。{C.RESET}')

        if extra_inst_prefixes:
            print(f'[*] 已加载 {len(extra_inst_prefixes)} 个额外插桩前缀。')

        print(f'[*] 正在解析 vmlinux: {vmlinux_path}')
        self.vmlinux = ELFObj(vmlinux_path, is_vmlinux=True)
        print('[*] vmlinux 解析完成。')

        self.live_syms = self._load_kallsyms()
        self.cs = Cs(CS_ARCH_X86, CS_MODE_64)
        self.cs.detail = True

        self.queue = [self.target_func]
        self.visited = set()

        self.static_refs = []
        self.manifest_got = []
        self.manifest_instrumentation = []
        self.hard_fails = []
        self.missing_deps = set()
        self.shim_hits = defaultdict(list)
        self.unanalyzable_funcs = []
        self.analysis_trace = []

    def _canonical_reg_name(self, reg_name):
        if not reg_name:
            return ''
        reg_name = reg_name.lower()
        for canonical, aliases in REG_ALIAS_GROUPS.items():
            if reg_name in aliases:
                return canonical
        return reg_name

    def _load_kallsyms(self):
        syms = {}
        kallsyms_path = '/proc/kallsyms'
        if not os.path.exists(kallsyms_path):
            print(f'{C.YELLOW}[*] 未发现 /proc/kallsyms，报告中将仅显示静态地址。{C.RESET}')
            return syms

        try:
            print('[*] 正在尝试读取 /proc/kallsyms 以补充运行时虚拟地址...')
            with open(kallsyms_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        syms[parts[2]] = int(parts[0], 16)
            print(f'[*] 已载入 {len(syms)} 个活体内核符号。')
        except Exception as exc:
            print(f'{C.YELLOW}[*] 读取 /proc/kallsyms 失败: {exc}。将退回静态地址显示。{C.RESET}')
        return syms

    def _trace(self, message, color=C.CYAN):
        print(f'  {color}├─ [Trace] {message}{C.RESET}')

    def _warn(self, message):
        print(f'  {C.YELLOW}├─ [Warn] {message}{C.RESET}')

    def _record_missing_dep(self, func_name, source_func=None, source_owner=None):
        self.missing_deps.add(func_name)
        src = f'，来源 {source_owner.name}:{source_func}' if source_func and source_owner else ''
        self._warn(f'闭包断裂，未解析到符号: {func_name}{src}')

    def _record_unanalyzable(self, owner_elf, func_name, reason, detail=''):
        entry = {
            'mod': owner_elf.name,
            'func': func_name,
            'reason': reason,
            'detail': detail,
        }
        self.unanalyzable_funcs.append(entry)
        suffix = f' ({detail})' if detail else ''
        self._warn(f'函数无法继续分析: {owner_elf.name}:{func_name} -> {reason}{suffix}')

    def _record_static_ref(self, owner_elf, func_name, local_offset, addr_display, asm_str, target_sec, target_name, reloc_type):
        self.static_refs.append({
            'mod': owner_elf.name,
            'func': func_name,
            'addr': local_offset,
            'run_addr': addr_display,
            'asm': asm_str,
            'section': target_sec.name,
            'section_flags': target_sec['sh_flags'],
            'sym': target_name,
            'target_desc': target_name,
            'reloc_type': reloc_type,
        })
        sec_label = f'{target_sec.name}:{target_name}' if target_name and target_name != target_sec.name else target_sec.name
        self._trace(f'记录静态引用事实: {func_name} -> {sec_label} (reloc={reloc_type})')

    def _is_instrumentation_symbol(self, name):
        if not name:
            return False
        return name in self.inst_exact or name.startswith(self.inst_prefixes)

    def _get_runtime_display(self, func_name, local_offset_val, instr_addr):
        live_func_base = self.live_syms.get(func_name)
        if live_func_base is not None:
            run_addr = hex(live_func_base + local_offset_val)
            return f'{C.BOLD}{run_addr}{C.RESET}'
        return f'未加载 (静态: {hex(instr_addr)})'

    def _find_relocation_for_instruction(self, relocs, instr):
        for reloc_offset in range(instr.address, instr.address + instr.size):
            reloc = relocs.get(reloc_offset)
            if reloc is not None:
                return reloc
        return None

    def _describe_relocation_target(self, owner_elf, reloc):
        if reloc is None:
            return ''
        target_sym = owner_elf.symtab.get_symbol(reloc['r_info_sym'])
        if target_sym is None:
            return f'r_info_sym={reloc["r_info_sym"]}'
        target_name = target_sym.name
        if not target_name and target_sym['st_shndx'] != 'SHN_UNDEF':
            target_sec = owner_elf.elf.get_section(target_sym['st_shndx'])
            target_name = target_sec.name if target_sec is not None else '<anonymous>'
        return self._format_target_desc(owner_elf, target_sym, target_name, reloc)

    def _display_addend(self, reloc, addend):
        display_addend = addend
        if reloc is not None and reloc['r_info_type'] in PC_REL_RELOC_TYPES:
            # x86_64 RIP-relative relocations store an addend relative to the
            # relocation field; the effective slot is at addend + 4.
            display_addend += 4
        return display_addend

    def _format_addend(self, addend):
        sign = '+' if addend >= 0 else '-'
        return f'{sign}0x{abs(addend):x}'

    def _format_target_desc(self, owner_elf, target_sym, target_name, reloc):
        addend = 0
        if reloc is not None:
            addend = reloc.entry.get('r_addend', 0)
        addend = self._display_addend(reloc, addend)

        if target_sym is None:
            return target_name or ''

        if target_name and target_sym['st_info']['type'] != 'STT_SECTION':
            return f'{target_name}{self._format_addend(addend)}'

        if target_sym['st_shndx'] == 'SHN_UNDEF':
            base = target_name or '<undef>'
            return f'{base}{self._format_addend(addend)}'

        target_sec = owner_elf.elf.get_section(target_sym['st_shndx'])
        base = target_sec.name if target_sec is not None else (target_name or '<anonymous>')
        return f'{base}{self._format_addend(addend)}'

    def _collect_branch_source_regs(self, instr):
        regs = []
        if not instr.operands:
            return regs

        operand = instr.operands[0]
        if operand.type == X86_OP_REG:
            regs.append(self._canonical_reg_name(instr.reg_name(operand.reg)))
        elif operand.type == X86_OP_MEM:
            if operand.mem.base:
                regs.append(self._canonical_reg_name(instr.reg_name(operand.mem.base)))
            if operand.mem.index:
                regs.append(self._canonical_reg_name(instr.reg_name(operand.mem.index)))
        return [reg for reg in regs if reg]

    def _collect_retpoline_source_regs(self, thunk_name):
        if not thunk_name or not thunk_name.startswith(RETPOLINE_INDIRECT):
            return []
        suffix = thunk_name[len(RETPOLINE_INDIRECT):].strip()
        if not suffix:
            return []
        reg_name = self._canonical_reg_name(suffix)
        return [reg_name] if reg_name else []

    def _find_prior_write(self, instructions, current_index, target_reg):
        if not target_reg:
            return None

        for prev_index in range(current_index - 1, -1, -1):
            prev_instr = instructions[prev_index]
            try:
                _, regs_write = prev_instr.regs_access()
            except CsError:
                regs_write = []

            written = {
                self._canonical_reg_name(prev_instr.reg_name(reg_id))
                for reg_id in regs_write
                if prev_instr.reg_name(reg_id)
            }
            if target_reg in written:
                return prev_instr
        return None

    def _describe_instruction_location(self, func_name, base_addr, instr):
        local_offset_val = instr.address - base_addr
        return {
            'offset': hex(local_offset_val),
            'runtime': self._get_runtime_display(func_name, local_offset_val, instr.address),
            'static': hex(instr.address),
            'asm': f'{instr.mnemonic} {instr.op_str}'.strip(),
        }

    def _normalize_imm_target(self, imm_value):
        if imm_value is None:
            return None
        if imm_value < 0:
            return imm_value & ((1 << 64) - 1)
        return imm_value

    def _explain_indirect_branch(self, owner_elf, func_name, disasm_base, instructions, instr_index, relocs):
        instr = instructions[instr_index]
        source_regs = self._collect_branch_source_regs(instr)
        sources = []

        for reg_name in source_regs:
            if reg_name == 'rip':
                sources.append({
                    'reg': reg_name,
                    'kind': 'implicit',
                    'detail': 'RIP 相对寻址，目标由当前指令位置决定',
                })
                continue

            writer = self._find_prior_write(instructions, instr_index, reg_name)
            if writer is None:
                sources.append({
                    'reg': reg_name,
                    'kind': 'unknown',
                    'detail': '在当前函数内未找到更早的写入指令',
                })
                continue

            writer_loc = self._describe_instruction_location(func_name, disasm_base, writer)
            writer_reloc = self._find_relocation_for_instruction(relocs, writer)
            reloc_target = self._describe_relocation_target(owner_elf, writer_reloc)
            try:
                regs_read, _ = writer.regs_access()
            except CsError:
                regs_read = []

            read_regs = [
                self._canonical_reg_name(writer.reg_name(reg_id))
                for reg_id in regs_read
                if writer.reg_name(reg_id)
            ]
            read_regs = [name for name in read_regs if name and name not in {reg_name, 'rip'}]

            detail = f'{writer_loc["asm"]} @ {writer_loc["offset"]} | 运行基址: {writer_loc["runtime"]}'
            if reloc_target:
                detail += f' | 关联重定位: {reloc_target}'
            if read_regs:
                detail += f' | 读取寄存器: {", ".join(dict.fromkeys(read_regs))}'

            sources.append({
                'reg': reg_name,
                'kind': 'backtrack',
                'detail': detail,
            })

        return sources

    def _explain_retpoline_branch(self, owner_elf, func_name, disasm_base, instructions, instr_index, relocs, thunk_name):
        source_regs = self._collect_retpoline_source_regs(thunk_name)
        sources = []

        for reg_name in source_regs:
            writer = self._find_prior_write(instructions, instr_index, reg_name)
            if writer is None:
                sources.append({
                    'reg': reg_name,
                    'kind': 'unknown',
                    'detail': f'根据 thunk 名称推断目标寄存器为 {reg_name}，但在当前函数内未找到更早的写入指令',
                })
                continue

            writer_loc = self._describe_instruction_location(func_name, disasm_base, writer)
            writer_reloc = self._find_relocation_for_instruction(relocs, writer)
            reloc_target = self._describe_relocation_target(owner_elf, writer_reloc)
            try:
                regs_read, _ = writer.regs_access()
            except CsError:
                regs_read = []

            read_regs = [
                self._canonical_reg_name(writer.reg_name(reg_id))
                for reg_id in regs_read
                if writer.reg_name(reg_id)
            ]
            read_regs = [name for name in read_regs if name and name not in {reg_name, 'rip'}]

            detail = f'{writer_loc["asm"]} @ {writer_loc["offset"]} | 运行基址: {writer_loc["runtime"]}'
            if reloc_target:
                detail += f' | 关联重定位: {reloc_target}'
            if read_regs:
                detail += f' | 读取寄存器: {", ".join(dict.fromkeys(read_regs))}'

            sources.append({
                'reg': reg_name,
                'kind': 'retpoline-backtrack',
                'detail': detail,
            })

        return source_regs, sources

    def resolve_symbol_owner(self, func_name):
        for mod in self.modules:
            if mod.get_symbol(func_name):
                return mod
        if self.vmlinux.get_symbol(func_name):
            return self.vmlinux
        return None

    def queue_func(self, name, reason=''):
        if not name:
            return
        if name in self.visited or name in self.queue:
            return
        self.queue.append(name)
        if reason:
            self._trace(f'加入待分析队列: {name} <- {reason}')

    def analyze(self):
        print(f'{C.BOLD}[*] 开始构建依赖闭包并执行扫描...{C.RESET}')
        while self.queue:
            func_name = self.queue.pop(0)
            if func_name in self.visited:
                continue

            self.visited.add(func_name)
            owner = self.resolve_symbol_owner(func_name)
            if not owner:
                self._record_missing_dep(func_name)
                continue

            queue_left = len(self.queue)
            self._trace(f'深入分析: {owner.name} -> {func_name} (剩余队列: {queue_left})')
            self.analysis_trace.append((owner.name, func_name))
            self._analyze_function(func_name, owner)

    def _analyze_function(self, func_name, owner_elf):
        sym = owner_elf.get_symbol(func_name)
        if sym is None:
            self._record_missing_dep(func_name)
            return

        sec_idx = sym['st_shndx']
        sec = owner_elf.elf.get_section(sec_idx)
        if sec is None:
            self._record_unanalyzable(owner_elf, func_name, '找不到所属节区', str(sec_idx))
            return

        if owner_elf.elf.header['e_type'] in ('ET_EXEC', 'ET_DYN'):
            offset = sym['st_value'] - sec['sh_addr']
            disasm_base = sym['st_value']
        else:
            offset = sym['st_value']
            disasm_base = sym['st_value']

        size = sym['st_size']
        section_data = sec.data()
        data_len = len(section_data)
        tag = f'[{owner_elf.name}]'

        if size == 0:
            self._record_unanalyzable(owner_elf, func_name, '函数 size 为 0', f'symbol={hex(sym["st_value"])}')
            return

        if offset < 0 or offset + size > data_len:
            detail = f'offset={offset}, size={size}, section_size={data_len}, sh_addr={hex(sec["sh_addr"])}'
            self._record_unanalyzable(owner_elf, func_name, '节区切片越界', detail)
            return

        code = section_data[offset:offset + size]
        relocs = owner_elf.get_relocations(sec.name)
        insn_count = 0

        instructions = list(self.cs.disasm(code, disasm_base))
        for instr_index, instr in enumerate(instructions):
            insn_count += 1
            local_offset_val = instr.address - disasm_base
            local_offset = hex(local_offset_val)
            addr_display = self._get_runtime_display(func_name, local_offset_val, instr.address)
            asm_str = f'{instr.mnemonic} {instr.op_str}'.strip()

            is_priv = instr.mnemonic in PRIV_INSNS
            if not is_priv:
                for operand in instr.operands:
                    if operand.type == X86_OP_REG and operand.reg in CR_REGS:
                        is_priv = True
                        break

            if is_priv:
                self.hard_fails.append({
                    'mod': tag,
                    'func': func_name,
                    'addr': local_offset,
                    'run_addr': addr_display,
                    'asm': asm_str,
                    'type': '特权指令 / 控制寄存器访问',
                })
                self._warn(f'命中特权指令: {func_name} +{local_offset} -> {asm_str}')
                return

            reloc = self._find_relocation_for_instruction(relocs, instr)

            is_branch = instr.id in (X86_INS_CALL, X86_INS_JMP)
            is_indirect = False

            if is_branch and instr.operands:
                operand = instr.operands[0]
                if operand.type != X86_OP_IMM and reloc is None:
                    is_indirect = True
                    self.manifest_got.append({
                        'mod': owner_elf.name,
                        'func': func_name,
                        'addr': local_offset,
                        'run_addr': addr_display,
                        'asm': asm_str,
                        'type': '原生函数指针 / 寄存器盲跳',
                        'sym': '',
                        'source_regs': self._collect_branch_source_regs(instr),
                        'sources': self._explain_indirect_branch(owner_elf, func_name, disasm_base, instructions, instr_index, relocs),
                    })
                    self._trace(f'捕获盲跳: {func_name} +{local_offset} -> {asm_str}', C.YELLOW)

            if reloc:
                r_type = reloc['r_info_type']
                target_sym = owner_elf.symtab.get_symbol(reloc['r_info_sym'])
                if target_sym is None:
                    self._record_unanalyzable(owner_elf, func_name, '重定位目标缺失', f'r_info_sym={reloc["r_info_sym"]}')
                    continue

                target_name = target_sym.name
                if not target_name and target_sym['st_shndx'] != 'SHN_UNDEF':
                    target_sec = owner_elf.elf.get_section(target_sym['st_shndx'])
                    target_name = target_sec.name if target_sec else ''

                target_desc = self._format_target_desc(owner_elf, target_sym, target_name, reloc)

                if r_type in PC_REL_RELOC_TYPES and is_branch and target_name:
                    asm_str = f'{instr.mnemonic} {target_name}'

                target_sec = None
                if target_sym['st_shndx'] != 'SHN_UNDEF':
                    target_sec = owner_elf.elf.get_section(target_sym['st_shndx'])
                    if target_sec is not None and (target_sec['sh_flags'] & 4) == 0:
                        self._record_static_ref(
                            owner_elf,
                            func_name,
                            local_offset,
                            addr_display,
                            asm_str,
                            target_sec,
                            target_desc,
                            r_type,
                        )

                if r_type in ABSOLUTE_RELOC_TYPES:
                    self.hard_fails.append({
                        'mod': tag,
                        'func': func_name,
                        'addr': local_offset,
                        'run_addr': addr_display,
                        'asm': asm_str,
                        'type': f'绝对地址寻址 ({target_desc})',
                    })
                    self._warn(f'命中绝对地址重定位: {func_name} +{local_offset} -> {asm_str}')
                    continue

                if r_type in PC_REL_RELOC_TYPES:
                    if self._is_instrumentation_symbol(target_name):
                        self._trace(f'截获编译器插桩: {target_name}', C.YELLOW)
                        self.manifest_instrumentation.append({
                            'mod': owner_elf.name,
                            'func': func_name,
                            'addr': local_offset,
                            'run_addr': addr_display,
                            'asm': asm_str,
                            'sym': target_name,
                        })
                        continue

                    if target_name and target_name.startswith(RETPOLINE_INDIRECT):
                        self._trace(f'截获 Retpoline 间接跳: {target_name}', C.YELLOW)
                        source_regs, sources = self._explain_retpoline_branch(
                            owner_elf,
                            func_name,
                            disasm_base,
                            instructions,
                            instr_index,
                            relocs,
                            target_name,
                        )
                        self.manifest_got.append({
                            'mod': owner_elf.name,
                            'func': func_name,
                            'addr': local_offset,
                            'run_addr': addr_display,
                            'asm': asm_str,
                            'type': 'Retpoline 包装的盲跳',
                            'sym': target_name,
                            'source_regs': source_regs,
                            'sources': sources,
                        })
                        continue

                    if target_name and target_name.startswith(RETPOLINE_RETURN):
                        self._trace(f'截获 Retpoline 安全返回: {target_name} (忽略)')
                        continue

                    if target_sym['st_shndx'] == 'SHN_UNDEF':
                        if target_name in self.shims:
                            self.shim_hits[target_name].append({
                                'func': func_name,
                                'addr': local_offset,
                                'run_addr': addr_display,
                                'asm': asm_str,
                            })
                            self._trace(f'Shim 截断成功: {func_name} -> {target_name}', C.GREEN)
                        else:
                            self.queue_func(target_name, f'{func_name} -> 外部符号')
                    else:
                        if target_sec is None:
                            self._record_unanalyzable(owner_elf, func_name, '重定位目标节区缺失', target_name or '<anonymous>')
                            continue

                        is_exec = (target_sec['sh_flags'] & 4) != 0
                        if not is_exec:
                            continue
                        else:
                            if target_sym['st_info']['type'] == 'STT_FUNC' and target_sym.name:
                                self.queue_func(target_sym.name, f'{func_name} -> 本 ELF 可执行符号')
                            else:
                                target_offset = reloc['r_addend'] - reloc['r_offset'] + instr.address + instr.size
                                resolved_func = owner_elf.resolve_func_by_offset(target_sym['st_shndx'], target_offset)
                                if resolved_func:
                                    self.queue_func(resolved_func, f'{func_name} -> 节内偏移解析')
                                else:
                                    detail = f'symbol={target_name or "<anonymous>"}, target_offset={hex(target_offset)}'
                                    self._record_unanalyzable(owner_elf, func_name, '无法从节内偏移解析目标函数', detail)
            else:
                if is_branch and not is_indirect and instr.operands:
                    target_addr = self._normalize_imm_target(instr.operands[0].imm)
                    resolved_func = owner_elf.resolve_func_by_offset(sec_idx, target_addr)
                    if resolved_func and resolved_func != func_name:
                        self.queue_func(resolved_func, f'{func_name} -> 同节直接跳转')

        if insn_count == 0:
            detail = f'offset={offset}, size={size}, section={sec.name}'
            self._record_unanalyzable(owner_elf, func_name, '反汇编结果为空', detail)

    def generate_report(self):
        print(f'\n{C.BOLD}{C.BLUE}========================================================================{C.RESET}')
        print(f'{C.BOLD}{C.BLUE}====================== FINAL REUSE MANIFEST =========================={C.RESET}')
        print(f'{C.BOLD}{C.BLUE}========================================================================{C.RESET}\n')

        print(f'{C.BOLD}[摘要]{C.RESET}')
        print(f'  - 已访问函数: {len(self.visited)}')
        print(f'  - Shim 命中数: {sum(len(v) for v in self.shim_hits.values())}')
        print(f'  - 静态数据/地址引用数: {len(self.static_refs)}')
        print(f'  - 间接控制流命中数: {len(self.manifest_got)}')
        print(f'  - 编译器插桩命中数: {len(self.manifest_instrumentation)}')
        print(f'  - 致命失败数: {len(self.hard_fails)}')
        print(f'  - 丢失符号数: {len(self.missing_deps)}')
        print(f'  - 不可分析函数数: {len(self.unanalyzable_funcs)}\n')

        if self.manifest_instrumentation:
            print(f'{C.YELLOW}[⚠️ 编译器插桩残留]{C.RESET}')
            for inst in self.manifest_instrumentation:
                print(f'  [{inst["mod"]}] 目标符号: {C.RED}{inst["sym"]}{C.RESET}')
                print(f'    ├─ 案发现场: {inst["func"]} (+{inst["addr"]} | 运行基址: {inst["run_addr"]})')
                print(f'    └─ 机器汇编: {inst["asm"]}')
            print()

        if self.hard_fails:
            print(f'{C.RED}[❌ HARD FAILS - 物理层崩溃预警]{C.RESET}')
            for fail in self.hard_fails:
                print(f'  {fail["mod"]} 崩溃类型: {fail["type"]}')
                print(f'    ├─ 案发现场: {fail["func"]} (+{fail["addr"]} | 运行基址: {fail["run_addr"]})')
                print(f'    └─ 触发指令: {fail["asm"]}')
            print()

        if self.missing_deps or self.unanalyzable_funcs:
            print(f'{C.YELLOW}[⚠️ 分析不完整 / 结果不可信]{C.RESET}')
            if self.unanalyzable_funcs:
                print('  - 无法可靠分析的函数:')
                for item in self.unanalyzable_funcs:
                    detail = f' ({item["detail"]})' if item['detail'] else ''
                    print(f'    * [{item["mod"]}] {item["func"]}: {item["reason"]}{detail}')
            if self.missing_deps:
                print('  - 闭包中丢失的符号:')
                for name in sorted(self.missing_deps):
                    print(f'    * {name}')
            print(f'  {C.YELLOW}由于存在上述盲区，工具拒绝给出安全放行结论。{C.RESET}\n')

        if not self.hard_fails:
            print(f'{C.GREEN}[ℹ️ 基础检查]{C.RESET} 未发现特权指令、控制寄存器访问或绝对地址重定位。')
            if not self.missing_deps and not self.unanalyzable_funcs:
                print(f'  {C.GREEN}闭包路径在当前输入范围内是完整的。{C.RESET}')
            print()

        print(f'{C.CYAN}[📦 静态数据 / 地址引用事实]{C.RESET}')
        if self.static_refs:
            for ref in self.static_refs:
                flags = ref['section_flags']
                prot = 'R' + ('W' if (flags & 1) else '-') + ('X' if (flags & 4) else '-')
                sec_kind = f'{C.YELLOW}[WRITABLE]{C.RESET}' if (flags & 1) else f'{C.GREEN}[READONLY]{C.RESET}'
                target_hint = f' (目标: {ref["target_desc"]})' if ref['target_desc'] else ''
                print(f'  [{ref["mod"]}] {sec_kind} {ref["section"]} | 节区权限: {prot} | reloc={ref["reloc_type"]}')
                print(f'    ├─ 所在函数: {ref["func"]} (+{ref["addr"]} | 运行基址: {ref["run_addr"]})')
                print(f'    └─ 指令事实: {ref["asm"]}{target_hint}')
        else:
            print('  - 无静态数据 / 地址引用事实')

        print(f'\n{C.CYAN}[🔌 Shim 边界成功拦截]{C.RESET}')
        if self.shim_hits:
            for sym, hits in sorted(self.shim_hits.items()):
                print(f'  拦截 API: {C.GREEN}{sym}{C.RESET} (共 {len(hits)} 处调用)')
                for hit in hits:
                    print(f'    └─ 来自: {hit["func"]} (+{hit["addr"]} | 运行基址: {hit["run_addr"]}) -> {hit["asm"]}')
        else:
            print('  - 无或未命中')

        print(f'\n{C.CYAN}[🔀 间接控制流 / 盲跳]{C.RESET}')
        print(f'  {C.YELLOW}注意: 请在用户态确认这些位置的函数指针或跳转表已被合法初始化。{C.RESET}')
        if self.manifest_got:
            for got in self.manifest_got:
                sym_hint = f' ({got["sym"]})' if got['sym'] else ''
                print(f'  [{got["mod"]}] 控制流: {got["type"]}{sym_hint}')
                print(f'    ├─ 所在函数: {got["func"]} (+{got["addr"]} | 运行基址: {got["run_addr"]})')
                print(f'    ├─ 执行指令: {got["asm"]}')
                if got.get('source_regs'):
                    print(f'    ├─ 参与寻址的寄存器: {", ".join(got["source_regs"])}')
                if got.get('sources'):
                    for idx, source in enumerate(got['sources']):
                        prefix = '└─' if idx == len(got['sources']) - 1 else '├─'
                        print(f'    {prefix} 来源追踪 [{source["reg"]}]: {source["detail"]}')
                else:
                    print('    └─ 来源追踪: 未找到可用线索')
        else:
            print('  - 无间接跳转')

        if self.hard_fails:
            exit_code = 1
            verdict = f'{C.RED}FAIL{C.RESET}'
        elif self.missing_deps or self.unanalyzable_funcs:
            exit_code = 2
            verdict = f'{C.YELLOW}INCOMPLETE{C.RESET}'
        else:
            exit_code = 0
            verdict = f'{C.GREEN}PASS{C.RESET}'

        print(f'\n{C.BOLD}[最终结论]{C.RESET} {verdict} (exit code: {exit_code})')
        print(f'{C.BOLD}{C.BLUE}=========================== 报告结束 ==========================={C.RESET}')
        return exit_code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--modules', nargs='*', default=[], help='传入所有 .ko 模块路径')
    parser.add_argument('-t', '--target', required=True, help='核心入口函数')
    parser.add_argument('-v', '--vmlinux', required=True, help='系统 vmlinux 文件路径')
    parser.add_argument('-s', '--shim-file', help='包含用户态平替白名单的文件路径')
    parser.add_argument('-i', '--inst-file', help='包含额外插桩前缀的文件路径')
    args = parser.parse_args()

    shim_set = set(load_token_file(args.shim_file))
    extra_inst_prefixes = tuple(load_token_file(args.inst_file))

    engine = AcademicReuseEngine(
        args.modules,
        args.target,
        shim_set,
        args.vmlinux,
        extra_inst_prefixes=extra_inst_prefixes,
    )
    engine.analyze()
    sys.exit(engine.generate_report())
