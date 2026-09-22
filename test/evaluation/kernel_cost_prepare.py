"""Build complete current owners and helper-binding controls for private guests."""
from pathlib import Path
import difflib
import json
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RELEASE = '5.15.0-119-generic'


def prepare(algorithm, output, payload, copy_file, owner_source=None):
    assert algorithm in ('lz4', 'xz')
    build = Path(output) / 'kernel-cost-build'
    build.mkdir()
    commands = []

    def command(argv, name):
        argv = list(map(str, argv))
        with (build / name).open('w') as stream:
            result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
        commands.append(dict(argv=argv, log=name, returncode=result.returncode))
        (build / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        if result.returncode:
            raise RuntimeError(f'kernel comparison preparation failed: {build / name}')

    owner_name = 'vkso_' + algorithm
    matched_name = 'matched_' + algorithm
    if owner_source is None:
        owner_source = build / 'owner'
        for path in (ROOT / f'test/test_{algorithm}/kmod').iterdir():
            if path.is_file() and (path.name == 'Makefile' or path.suffix in ('.c', '.h')):
                if not path.name.endswith('.mod.c'):
                    copy_file(path, owner_source / path.name)
        command(['make', '-C', f'/lib/modules/{RELEASE}/build',
                 f'M={owner_source}', '-j2', 'modules'], 'owner-build.log')
        command(['pahole', '-J', '--skip_encoding_btf_enum64', '--btf_base',
                 '/sys/kernel/btf/vmlinux', owner_source / (owner_name + '.ko')], 'owner-btf.log')
    owner_source = Path(owner_source)
    copy_file(owner_source / (owner_name + '.ko'), payload / 'owner' / (owner_name + '.ko'))
    matched = build / 'matched'
    matched.mkdir()
    if algorithm == 'xz':
        from xz_kernel_reference import prepare_source
        prepare_source(owner_source, matched)
    else:
        source = ROOT / 'test/section63/source/linux-5.15.0-119.129/lib/lz4'
        for name in ('lz4_compress.c', 'lz4_decompress.c', 'lz4defs.h'):
            copy_file(source / name, matched / name)
        makefile = (owner_source/'Makefile').read_text().replace(owner_name,matched_name).replace('vkso_LZ4','matched_LZ4')
        (matched/'Makefile').write_text(makefile)
        (matched/'module_meta.c').write_text('#include <linux/module.h>\nMODULE_LICENSE("GPL");\n')
        (build/'matched-source.json').write_text(json.dumps(dict(
            definition='original-source-owner-codegen',source_version='Ubuntu 5.15.0-119.129',algorithm_edits=[]),indent=2)+'\n')
    command(['make', '-C', f'/lib/modules/{RELEASE}/build',
             f'M={matched}', '-j2', 'modules'], 'matched-build.log')
    objects = ['lz4_compress', 'lz4_decompress'] if algorithm == 'lz4' else [
        'xz_dec_stream', 'xz_dec_lzma2', 'xz_dec_bcj', 'xz_crc32']
    comparisons = []
    for obj in objects if algorithm == 'lz4' else []:
        records = []
        for directory, namespace in ((owner_source, owner_name), (matched, matched_name)):
            original = (directory / ('.' + obj + '.o.cmd')).read_text().splitlines()[0]
            tokens = shlex.split(original.split(' := ', 1)[1])
            normalized = [token.replace(str(directory), '<build>').replace(namespace, '<namespace>')
                          .replace('vkso_LZ4', '<API>').replace('matched_LZ4', '<API>')
                          for token in tokens]
            records.append(dict(command=original, normalized=normalized))
        assert records[0]['normalized'] == records[1]['normalized'], (obj, records)
        comparisons.append(dict(object=obj, records=records, status='pass'))
    comparison = dict(status='pass',
        allowed_differences=['module/API namespace', 'module build directory'],
        intervention='original source and dependencies versus complete export adaptation',
        objects=comparisons)
    if algorithm == 'xz':
        from xz_kernel_reference import compare_commands
        comparison = compare_commands(owner_source, matched)
    (build / 'compiler-comparison.json').write_text(json.dumps(comparison, indent=2) + '\n')
    driver = build / 'driver'
    copy_file(HERE / 'kernel-cost/observer.c', driver / 'observer.c')
    observer = algorithm + '_kernel_bench'
    (driver / 'Makefile').write_text(f'obj-m += {observer}.o\n{observer}-y := observer.o\n' +
                                   ('ccflags-y += -DOBSERVE_LZ4\n' if algorithm == 'lz4' else
                                    'ccflags-y += -DXZ_STOCK_SOURCE_MATCHED\n'))
    command(['make', '-C', f'/lib/modules/{RELEASE}/build', f'M={driver}',
             f'KBUILD_EXTRA_SYMBOLS={owner_source / "Module.symvers"} {matched / "Module.symvers"}',
             '-j2', 'modules'], 'observer-build.log')
    destination = payload / 'kernel-cost'
    modules = [(matched_name, matched / (matched_name + '.ko')),
               (observer, driver / (observer + '.ko'))]
    if algorithm == 'lz4':
        modules.insert(0, ('lz4_compress', Path(f'/lib/modules/{RELEASE}/kernel/lib/lz4/lz4_compress.ko')))
        copy_file(Path('/usr/lib/x86_64-linux-gnu/liblz4.so.1'), destination / 'liblz4.so.1')
    for name, module in modules:
        copy_file(module, destination / (name + '.ko'))
        command(['modinfo', module], name + '-modinfo.txt')
        command(['nm', '-u', module], name + '-imports.txt')
    command(['readelf', '-rW', driver / (observer + '.ko')], 'observer-relocations.txt')
    command(['objdump', '-drwC', '-Mintel', driver / (observer + '.ko')], 'observer-disassembly.txt')
    copy_file(HERE / 'kernel_cost_guest.py', payload / 'kernel_cost_guest.py')
    copy_file(Path(__file__), build / 'kernel_cost_prepare.py')
    configuration = dict(algorithm=algorithm,
        modules=[name for name, _ in modules], cpu=1, outer_runs=11, sample_ms=10,
        scope='private guest collection validation; not physical performance')
    configuration['backends'] = ['stock-kernel', 'matched-build-kernel', 'owner-kernel']
    configuration['matched_definition'] = 'original-source-owner-codegen'
    (destination / 'configuration.json').write_text(json.dumps(configuration, indent=2) + '\n')


def prepare_bch(output, payload, copy_file, owner_source):
    """Build the original BCH algorithm with the owner's code-generation options."""
    from bch_kernel_qemu import compare_algorithm_commands
    build = Path(output) / 'kernel-cost-build'
    build.mkdir()
    commands = []

    def command(argv, name):
        argv = list(map(str, argv))
        with (build / name).open('w') as stream:
            result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
        commands.append(dict(argv=argv, log=name, returncode=result.returncode))
        (build / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        if result.returncode:
            raise RuntimeError(f'BCH kernel preparation failed: {build / name}')

    for directory, source in [('driver', HERE / 'bch-kernel'), ('matched', HERE / 'bch-kernel-matched')]:
        for path in source.iterdir():
            if path.is_file() and (path.name == 'Makefile' or path.suffix in ('.c', '.h')):
                if not path.name.endswith('.mod.c'):
                    copy_file(path, build / directory / path.name)
    copy_file(ROOT / 'test/section63/source/linux-5.15.0-119.129/lib/bch.c', build / 'original/bch.c')
    (build/'matched-source.json').write_text(json.dumps(dict(
        definition='original-source-owner-codegen',source_version='Ubuntu 5.15.0-119.129',algorithm_edits=[]),indent=2)+'\n')
    headers = f'/lib/modules/{RELEASE}/build'
    command(['make', '-C', headers, f'M={build / "matched"}', '-j2', 'modules'], 'matched-build.log')
    (build / 'compiler-comparison.json').write_text(json.dumps(
        compare_algorithm_commands(build, owner_source), indent=2) + '\n')
    command(['make', '-C', headers, f'M={build / "driver"}',
             f'KBUILD_EXTRA_SYMBOLS={owner_source / "Module.symvers"} {build / "matched/Module.symvers"}',
             '-j2', 'modules'], 'observer-build.log')
    for name, source in [('bch', Path(f'/lib/modules/{RELEASE}/kernel/lib/bch.ko')),
                         ('bch_matched', build / 'matched/bch_matched.ko'),
                         ('bch_kernel_bench', build / 'driver/bch_kernel_bench.ko')]:
        copy_file(source, payload / 'kernel-cost' / (name + '.ko'))
        command(['modinfo', source], name + '-modinfo.txt')
        command(['nm', '-u', source], name + '-imports.txt')
    for name in ('bch_kernel_guest.py', 'bch_kernel_audit.py'):
        copy_file(HERE / name, payload / name)
    copy_file(Path(__file__), build / 'kernel_cost_prepare.py')
    (payload / 'kernel-cost/configuration.json').write_text(json.dumps(dict(
        measure=True, correctness_vectors=128, outer_runs=11, sample_ms=10, cpu=1,
        matched_definition='original-source-owner-codegen'), indent=2) + '\n')
