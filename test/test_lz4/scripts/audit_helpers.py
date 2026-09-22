#!/usr/bin/env python3
"""Compare resolved libc memory targets in the actual baseline and carrier.

Run outside timed commands, while the carrier is registered. Resolve the
baseline's real ELF GOT/PLT relocations, not a separate dlsym lookup on it.
"""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
from elftools.elf.elffile import ELFFile

NAMES = ('memcpy', 'memmove', 'memset')

class DlInfo(C.Structure):
    _fields_ = [('name', C.c_char_p), ('base', C.c_void_p),
                ('symbol', C.c_char_p), ('address', C.c_void_p)]


def inspect(library, same_source, bindings, *, native_api='vkso_LZ4_compress_default',
            carrier_api='vkso_LZ4_compress_default', names=NAMES, allow_no_import=False):
    library, same_source, bindings = map(lambda p: Path(p).resolve(), (library, same_source, bindings))
    carrier = C.CDLL(str(library), mode=os.RTLD_NOW | os.RTLD_LOCAL)
    native = C.CDLL(str(same_source), mode=os.RTLD_NOW | os.RTLD_LOCAL)
    libc = C.CDLL('libc.so.6')
    dladdr = libc.dladdr
    dladdr.argtypes = [C.c_void_p, C.POINTER(DlInfo)]
    dladdr.restype = C.c_int

    def address(fn): return C.cast(fn, C.c_void_p).value

    def location(pointer):
        info = DlInfo()
        if not pointer or not dladdr(pointer, C.byref(info)):
            raise ValueError('cannot resolve helper target DSO')
        return dict(address=hex(pointer), dso=str(Path(info.name.decode()).resolve()),
                    dso_offset=hex(pointer - info.base))

    def bias(path, handle, api):
        with path.open('rb') as stream:
            elf = ELFFile(stream)
            syms = elf.get_section_by_name('.dynsym').get_symbol_by_name(api)
            if not syms or len(syms) != 1: raise ValueError('ambiguous baseline API')
            return address(getattr(handle, api)) - syms[0]['st_value']

    native_bias = bias(same_source, native, native_api)
    carrier_bias = bias(library, carrier, carrier_api)
    native_targets = {name: [] for name in NAMES}
    with same_source.open('rb') as stream:
        elf = ELFFile(stream)
        for section in elf.iter_sections():
            if section['sh_type'] != 'SHT_RELA': continue
            symbols = elf.get_section(section['sh_link'])
            for relocation in section.iter_relocations():
                name = symbols.get_symbol(relocation['r_info_sym']).name
                if name not in NAMES: continue
                if relocation['r_info_type'] not in (6, 7):
                    raise ValueError('memory import is not a GOT/PLT relocation')
                slot = native_bias + relocation['r_offset']
                native_targets[name].append(dict(slot=hex(slot), file_vaddr=hex(relocation['r_offset']),
                    relocation_type=relocation['r_info_type'], target=C.c_void_p.from_address(slot).value))
    resolved = json.loads(bindings.read_text())['bindings']
    by_name = {r['user_symbol']: r for r in resolved}
    provider = carrier.vkso_abi_memory_target
    provider.argtypes = [C.c_uint]; provider.restype = C.c_void_p
    report = dict(status='running', library=str(library), same_source=str(same_source),
                  bindings=str(bindings), pid=os.getpid(), helpers=[],
                  scope='untimed resolved dependency targets; libc may use SIMD; compiler conditions remain distinct')
    for name in names:
        i = NAMES.index(name)
        expected = address(getattr(libc, name))
        entry = 'vkso_abi_' + name
        slot = carrier_bias + by_name[entry]['dso_vaddr']
        bridge = address(getattr(carrier, entry))
        if C.c_void_p.from_address(slot).value != bridge:
            raise ValueError('carrier slot does not target its ABI bridge')
        observed = provider(i)
        imports = native_targets[name]
        if observed != expected or (not imports and not allow_no_import) or any(r['target'] != expected for r in imports):
            raise ValueError(f'{name}: baseline, bridge and libc resolve to different implementations')
        for r in imports:
            r['target'] = location(r['target'])
        report['helpers'].append(dict(name=name, baseline_imports=imports,
            baseline_dynamic_import_present=bool(imports),
            carrier_slot=hex(slot), bridge=location(bridge), provider=location(observed)))
    report['status'] = 'pass'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('library', 'same-source', 'bindings', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--native-api', default='vkso_LZ4_compress_default')
    parser.add_argument('--carrier-api', default='vkso_LZ4_compress_default')
    parser.add_argument('--helpers', nargs='+', choices=NAMES, default=NAMES)
    parser.add_argument('--allow-no-import', action='store_true', help='ordinary optimized baselines may inline memory operations')
    args = parser.parse_args()
    report = inspect(args.library, args.same_source, args.bindings,
                     native_api=args.native_api, carrier_api=args.carrier_api,
                     names=args.helpers, allow_no_import=args.allow_no_import)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
