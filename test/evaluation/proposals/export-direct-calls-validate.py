#!/usr/bin/env python3
"""Validate only isolated copies of the unapplied direct-call rejection proposal."""
from pathlib import Path
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PATCH = HERE / 'export-direct-calls.patch'
SOURCES = ['make_dll/build_PIC_so.py', 'kernel_cgd/function_checker/functions_checker.py']
ASSEMBLY = r'''
.text
.type root_direct,@function
.globl root_direct
root_direct:
 call helper_external
 ret
.size root_direct,.-root_direct
.type root_jump,@function
.globl root_jump
root_jump:
 jmp helper_external
.size root_jump,.-root_jump
.type root_address,@function
.globl root_address
root_address:
 lea helper_external(%rip),%rax
 ret
.size root_address,.-root_address
.type root_pgot,@function
.globl root_pgot
root_pgot:
 call *helper_slot(%rip)
 ret
.size root_pgot,.-root_pgot
.type root_local,@function
.globl root_local
root_local:
 call local_helper
 ret
.size root_local,.-root_local
.type local_helper,@function
local_helper:
 ret
.size local_helper,.-local_helper
.type root_zero,@function
.globl root_zero
root_zero:
 ret
.type root_bad_decode,@function
.globl root_bad_decode
root_bad_decode:
 .byte 0x0f
.size root_bad_decode,.-root_bad_decode
.type root_thunk,@function
.globl root_thunk
root_thunk:
 call __x86_indirect_thunk_rax
 ret
.size root_thunk,.-root_thunk
.data
.globl helper_slot
.type helper_slot,@object
helper_slot:
 .quad helper_external
.size helper_slot,8
.section .note.GNU-stack,"",@progbits
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    before = {name: digest(ROOT / name) for name in SOURCES}
    report = {'scope': 'isolated proposal validation; no core edits, host modules, QEMU or campaign',
              'source_sha256': before, 'patch_sha256': digest(PATCH), 'fixtures': []}
    with tempfile.TemporaryDirectory(prefix='vkso-export-direct-validation-') as directory:
        temporary = Path(directory)
        for name in SOURCES:
            target = temporary / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        subprocess.run(['git', 'apply', str(PATCH)], cwd=temporary, check=True)
        for name in SOURCES:
            ast.parse((temporary / name).read_text(), filename=name)
        proposed = load_module('proposed_pic_direct_calls', temporary / SOURCES[0])
        original = load_module('original_pic_direct_calls', ROOT / SOURCES[0])
        assembly = temporary / 'bindings.s'
        assembly.write_text(ASSEMBLY)
        obj = temporary / 'bindings.o'
        subprocess.run(['as', '--64', str(assembly), '-o', str(obj)], check=True)
        ko = proposed.KoFile(obj)

        def selected(name, owner='fixture-owner'):
            found = ko.find_symbol(name)
            size = found[1].st_size if found else 0
            return proposed.ResolvedSymbol(name=name, source='libfixture.so', defined=True,
                st_type=proposed.STT_FUNC, module_name=owner, exported=True, size=size)

        def imported(name, module='shim'):
            return proposed.ResolvedSymbol(name=name, source='libshim.so', defined=False,
                st_type=proposed.STT_FUNC, module_name=module)

        cases = [
            ('direct-PLT32-call', [selected('root_direct'), imported('helper_external')], True),
            ('direct-PLT32-tail-jump', [selected('root_jump'), imported('helper_external')], True),
            ('immutable-PC32-address', [selected('root_address'), imported('helper_external')], True),
            ('PGOT-data-slot-with-unselected-direct-call-in-same-text',
             [selected('root_pgot'), imported('helper_external')], False),
            ('local-direct-call-without-relocation', [selected('root_local'), imported('local_helper')], True),
            ('zero-size-native-body', [selected('root_zero'), imported('helper_external')], True),
            ('incomplete-decode', [selected('root_bad_decode'), imported('helper_external')], True),
            ('missing-owner-symbol', [selected('missing'), imported('helper_external')], True),
            ('native-helper-not-declared-Shim', [selected('root_direct')], False),
            ('synthetic-builtin-thunk-not-dynamic-Shim',
             [selected('root_thunk'), imported('__x86_indirect_thunk_rax', 'builtin_thunk'),
              imported('helper_external')], False),
        ]
        for name, symbols, rejected in cases:
            message = None
            try:
                proposed.validate_executable_shim_bindings(ko, symbols, 'fixture-owner')
            except ValueError as error:
                message = str(error)
            assert (message is not None) == rejected, (name, message)
            report['fixtures'].append({'name': name, 'rejected': rejected, 'message': message})
        shims = temporary / 'shims.txt'
        shims.write_text('helper_external\n')
        report['checker'] = []
        for variant, checker in [('original', ROOT / SOURCES[1]), ('proposed', temporary / SOURCES[1])]:
            for root, expected in [('root_direct', 0 if variant == 'original' else 1), ('root_pgot', 0)]:
                command = [sys.executable, str(checker), '-v', str(obj), '-m', str(obj),
                           '-t', root, '-s', str(shims)]
                result = subprocess.run(command, capture_output=True, text=True)
                assert result.returncode == expected, (variant, root, result.stdout, result.stderr)
                report['checker'].append({'variant': variant, 'entry': root,
                    'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
        # Replay the real, freshly built owner and its original live-guest KRG offline.
        attempt = ROOT / 'test/evaluation/results/lz4-cli-qemu-20260912-attempt06'
        owner = attempt / 'owner-build-evidence/vkso_lz4.ko'
        krg = attempt / 'evidence/validation/export/vkso/metadata/out.krg'
        symbols = ROOT / 'test/test_lz4/config/symbols.txt'
        report['real_artifact'] = {'owner_sha256': digest(owner), 'krg_sha256': digest(krg),
                                  'symbols_sha256': digest(symbols), 'variants': []}
        for variant, module in [('original', original), ('proposed', proposed)]:
            destination = temporary / ('offline-' + variant)
            destination.mkdir()
            # The builder writes module_deps next to symbols; keep every output isolated.
            requested = destination / 'symbols.txt'
            requested.write_bytes(symbols.read_bytes())
            previous = Path.cwd()
            error = None
            captured = io.StringIO()
            try:
                os.chdir(destination)
                with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
                    module.build_shared_object(requested, krg,
                        shim_list_path=ROOT / 'make_dll/shim.txt', ko_path=owner,
                        symbol_dump_path=destination / 'resolved.txt',
                        page_map_path=destination / 'pages.txt',
                        vmlinux_path=Path('/usr/lib/debug/boot/vmlinux-5.15.0-119-generic'))
            except ValueError as exception:
                error = str(exception)
            finally:
                os.chdir(previous)
            if variant == 'original':
                assert error is None and (destination / 'libvkso_lz4.so').exists(), error
            else:
                assert error and 'unsupported executable Shim binding' in error, error
                assert not (destination / 'libvkso_lz4.so').exists()
                assert not (destination / 'pages.txt').exists()
                assert not (destination / 'module_deps.txt').exists()
            report['real_artifact']['variants'].append({'variant': variant, 'error': error,
                'dso_emitted': (destination / 'libvkso_lz4.so').exists(), 'output': captured.getvalue()})
    report['actual_core_unchanged'] = before == {name: digest(ROOT / name) for name in SOURCES}
    assert report['actual_core_unchanged']
    report['status'] = 'pass'
    (HERE / 'export-direct-calls-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: 10 binding fixtures, 4 checker cases, original/proposed real-artifact export replay; actual core unchanged')


if __name__ == '__main__':
    main()
