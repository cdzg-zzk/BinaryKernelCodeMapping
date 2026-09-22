#!/usr/bin/env python3
"""Prepare and collect the full kernel workload for an already registered owner.

Preparation is unprivileged and never loads modules. Collection must run inside
that owner's existing registration; it loads only the stock/matched/observer
modules and reuses the complete kernel collectors and workloads.
"""
from pathlib import Path
import argparse
import csv
import json
import os
import shutil
import subprocess

HERE = Path(__file__).resolve().parent

def copy_file(source, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)

def prepare(algorithm, owner_source, output, cpu, manifest=None):
    from kernel_cost_prepare import prepare as prepare_kernel, prepare_bch
    output, owner_source = Path(output).resolve(), Path(owner_source).resolve()
    if cpu not in os.sched_getaffinity(0):
        raise ValueError('measurement CPU is outside current affinity')
    # Resolve inputs before starting builds. No reduced input mode is offered.
    inputs = []
    if algorithm == 'lz4':
        manifest = Path(manifest).resolve()
        names = [x for x in manifest.read_text().splitlines() if x and not x.startswith('#')]
        assert len(names) == len(set(names)) == 12
        for name in names:
            source = (manifest.parent / name).resolve()
            assert source.is_file() and source.stat().st_size > 0
            inputs.append((source.name, source))
        assert len({name for name, _ in inputs}) == 12
    elif algorithm == 'xz':
        manifest = Path(manifest).resolve()
        rows = list(csv.reader(manifest.open()))
        assert len(rows) == 3 and [r[0] for r in rows] == ['bash', 'python3', 'libc.so.6']
        for row in rows:
            assert len(row) == 3
            for path in row[1:]:
                assert Path(path).is_absolute() and Path(path).is_file()
    output.mkdir(parents=True, exist_ok=False)
    payload = output / 'payload'; payload.mkdir()
    if algorithm == 'bch':
        prepare_bch(output, payload, copy_file, owner_source)
        copy_file(owner_source / 'vkso_bch.ko', payload / 'owner/vkso_bch.ko')
    else:
        prepare_kernel(algorithm, output, payload, copy_file, owner_source)
    if algorithm == 'lz4':
        (payload / 'corpus').mkdir()
        for name, source in inputs:
            copy_file(source, payload / 'corpus' / name)
        (payload / 'corpus/manifest.txt').write_text('\n'.join(name for name, _ in inputs)+'\n')
    elif algorithm == 'xz':
        corpus = payload / 'validation/corpus'; corpus.mkdir(parents=True)
        copied = []
        for name, plain, compressed in rows:
            copy_file(plain, corpus / name)
            copy_file(compressed, corpus / (name+'.xz'))
            copied.append((name, str(corpus/name), str(corpus/(name+'.xz'))))
        with (corpus / 'manifest.csv').open('w') as stream:
            csv.writer(stream).writerows(copied)
    config_path = payload / 'kernel-cost/configuration.json'
    config = json.loads(config_path.read_text())
    config.update(algorithm=algorithm, cpu=cpu,
                  scope='physical host kernel cost in the existing owner registration',
                  measurement_environment='physical-host')
    if algorithm == 'bch' and os.environ.get('BCH_ALIGNED_INPUTS') == '1':
        config['aligned_inputs'] = True
    config_path.write_text(json.dumps(config,indent=2)+'\n')
    # Keep the exact collection sources with the built observers.
    for name in ('kernel_cost_host.py','kernel_cost_guest.py','bch_kernel_guest.py','bch_kernel_audit.py'):
        copy_file(HERE/name, payload/name)
    record = dict(status='prepared', algorithm=algorithm, owner_source=str(owner_source),
                  cpu=cpu, outer_runs=config['outer_runs'], sample_ms=config['sample_ms'],
                  owner_build_id=subprocess.check_output(['readelf','-n',str(payload/'owner'/('vkso_'+algorithm+'.ko'))],text=True),
                  scope='build and full-input preparation only; no modules loaded and no performance collected')
    (output/'prepared.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

def collect(prepared, output):
    prepared, output = Path(prepared).resolve(), Path(output).resolve()
    root = prepared/'payload'
    config = json.loads((root/'kernel-cost/configuration.json').read_text())
    assert config['measurement_environment']=='physical-host'
    assert os.geteuid()==0 and os.uname().release=='5.15.0-119-generic'
    assert 'hypervisor' not in Path('/proc/cpuinfo').read_text().split()
    owner='vkso_'+config['algorithm']
    assert int(Path('/sys/module',owner,'refcnt').read_text())==1
    # Bind this collection to the exact already-loaded ELF, not merely its name.
    from kernel_cost_audit import require
    import sys
    sys.path.insert(0,str(HERE.parents[1]/'make_dll'))
    from build_PIC_so import elf_build_id
    import struct
    note=Path('/sys/module',owner,'notes/.note.gnu.build-id').read_bytes()
    namesz,descsz,kind=struct.unpack_from('III',note)
    offset=12+((namesz+3)&~3)
    require(kind==3 and note[12:12+namesz]==b'GNU\0', 'unexpected loaded build-ID note')
    require(note[offset:offset+descsz].hex()==elf_build_id(root/'owner'/(owner+'.ko')),
            'loaded owner differs from prepared kernel control')
    if config['algorithm']=='bch':
        import bch_kernel_guest as driver
        driver.WORK=root;driver.OUT=output
        if driver.main(registered=True): raise RuntimeError('BCH kernel collection failed')
        return json.loads((output/'status.json').read_text())
    from kernel_cost_guest import run
    return run(config['algorithm'],root,output)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('algorithm',choices=('lz4','bch','xz'))
    p.add_argument('--owner-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cpu',type=int,default=2);p.add_argument('--manifest',type=Path)
    p=sub.add_parser('collect');p.add_argument('--prepared',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare':
        if args.algorithm!='bch' and args.manifest is None:parser.error('LZ4/XZ require their full manifest')
        report=prepare(args.algorithm,args.owner_source,args.output,args.cpu,args.manifest)
    else: report=collect(args.prepared,args.output)
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
