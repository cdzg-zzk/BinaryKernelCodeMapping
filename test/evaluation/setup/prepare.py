"""Copy a built setup observer and its exact benchmark sources into a guest."""
from pathlib import Path
import importlib.util,shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def prepare(output,payload,copy_file):
    spec=importlib.util.spec_from_file_location('setup_builder',HERE/'build.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    binaries=module.build(Path(output)/'setup-build')
    for item in binaries.iterdir(): copy_file(item,Path(payload)/'setup'/item.name)
    for item in HERE.iterdir():
        if item.suffix in {'.py','.c','.h'}: copy_file(item,Path(payload)/'setup'/item.name)
    for name in ('test_lz4/src/lz4-bench.c','test_BCH/src/bch_bench.c','test_xz/src/xz-bench.c','test_xz/kmod/xz.h'):
        copy_file(ROOT/'test'/name,Path(output)/'setup-source/test'/name)
