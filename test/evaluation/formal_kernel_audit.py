#!/usr/bin/env python3
"""Reconstruct a completed physical-host kernel collection from retained records.

This reads a complete owner deployment. It does not run workloads or treat a
guest archive as a host sample. PFN experiments remain separately attributed;
the host evidence here is actual owner/API binding and completed registration.
"""
from pathlib import Path
from collections import Counter
import argparse
import csv
import json
import re
import subprocess

from kernel_cost_audit import BACKENDS, SILESIA, require, sha
from bch_kernel_audit import audit as audit_bch, new_log_window


def read(path):
    return json.loads(path.read_text())


def audit(deployment):
    deployment = Path(deployment).resolve()
    identity = read(deployment / 'identity.json')
    complete = read(deployment / 'complete.json')
    fresh = (deployment / 'prepared').is_dir()
    directory = deployment / ('results/kernel' if fresh else 'results/kernel-cost')
    prepared = deployment / ('prepared' if fresh else 'results/kernel-cost-prepared')
    algorithm = read(prepared / 'prepared.json')['algorithm']
    record = read(directory / ('status.json' if algorithm == 'bch' else 'collection.json'))
    config = record['configuration']; cpu = config['cpu']
    backends = config.get('backends', BACKENDS)
    new_xz = config.get('matched_definition') == 'original-source-owner-codegen'
    require(config['measurement_environment'] == 'physical-host' and record['status'] == 'pass',
            'not a completed physical-host collection')
    require(identity['kernel'] == '5.15.0-119-generic' and complete['owner_unloaded'], 'deployment incomplete')
    require(identity['boot_id'] == complete['boot_id'] == record['boot_id'], 'boot identity differs')
    require(config['outer_runs'] == 11 and config['sample_ms'] == 10, 'full sampling configuration differs')
    owner = (deployment.parent / 'owners' / algorithm / ('vkso_'+algorithm+'.ko')
             if fresh else deployment / 'owner.ko')
    require(owner.read_bytes() == (prepared / f'payload/owner/vkso_{algorithm}.ko').read_bytes(),
            'retained owner differs from prepared control')
    build_id = re.search(r'Build ID: ([0-9a-f]+)', subprocess.check_output(['readelf','-n',owner],text=True)).group(1)
    metadata = deployment / 'work/vkso/metadata'
    descriptors = [x.split() for x in (metadata/'owner_descriptors.txt').read_text().splitlines()
                   if x and not x.startswith('#')]
    require(len(descriptors) == 1 and descriptors[0][2:] == ['vkso_'+algorithm,build_id], 'owner descriptor differs')
    log = (metadata/'page_replace.log').read_text()
    require(f'VKSO_IMAGE module=vkso_{algorithm} symbol={descriptors[0][0]} build_id={build_id} phase=after-begin' in log,
            'manager did not identify actual owner')
    transactions = {}
    for line in log.splitlines():
        if line.startswith('VKSO_TRANSACTION id='):
            row = {k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
            transactions.setdefault(row['id'],[]).append(row)
    require(bool(transactions), 'missing registration records')
    for rows in transactions.values():
        require([r['operation'] for r in rows] == [1,2,3,5,6] and all(r['status']==0 for r in rows),
                'registration or release incomplete')
        require(rows[2]['applied'] == (5 if algorithm=='lz4' else 4) and rows[3]['applied']==0,
                'wrong applied/released page count')
    compiler = read(prepared/'kernel-cost-build/compiler-comparison.json')
    require(compiler['status']=='pass', 'compiler control failed')
    if algorithm=='bch':
        require(compiler['records'][0]['normalized_compiler_argv'] == compiler['records'][1]['normalized_compiler_argv'],
                'BCH compiler options differ')
        require(config['measure'] and config['correctness_vectors']==128, 'BCH workload reduced')
        detail = audit_bch(directory,measure=True,expected_cpu=cpu,correctness_vectors=128,outer_runs=11,sample_ms=10,
                          aligned_inputs=config.get('aligned_inputs', False))
        detail['scope'] = 'complete physical-host kernel-driver record replay'
        refs = [int(read(directory/f'modules-{name}.json')['vkso_bch']['refcnt'])
                for name in ('before-driver','with-driver','after-driver')]
        require(refs==[1,2,1] and record['same_registered_owner'], 'BCH owner references differ')
        prior = (directory/'dmesg-before-driver.txt').read_text()
        after = (directory/'dmesg-after-driver.txt').read_text()
        window = (directory/'dmesg-driver-window.txt').read_text()
        require(new_log_window(prior,after)==window, 'BCH driver log window differs')
        symbols = read(directory/'public-api-symbols.json')
        require(len(symbols)==12 and {s['name'] for s in symbols} ==
                {prefix+api for prefix in ('bch_','matched_bch_','vkso_bch_') for api in ('init','free','encode','decode')},
                'BCH API matrix differs')
        for symbol in symbols:
            provider = '[vkso_bch]' if symbol['name'].startswith('vkso_') else '[bch_matched]' if symbol['name'].startswith('matched_') else '[bch]'
            addresses = re.findall(r'BCH_KERNEL_BENCH api [^\n]*\b'+re.escape(symbol['name'])+r'=([0-9a-fA-F]+)\b',window)
            require(symbol['module']==[provider] and len(addresses)==1 and
                    int(addresses[0],16)==int(symbol['address'],16)!=0, 'BCH actual API target differs')
    else:
        require(record['cpu_affinity']==[cpu] and [record['owner_refcnt_'+s] for s in ('before','active','after')]==[1,2,1],
                'CPU affinity or registered owner references differ')
        require(all(x['returncode']==0 for x in record['module_commands']), 'module command failed')
        require(len(compiler['objects'])==(2 if algorithm=='lz4' else 3 if new_xz else 4), 'compiler object matrix differs')
        for obj in compiler['objects']:
            require(obj['records'][0]['normalized']==obj['records'][1]['normalized'], 'compiler options differ')
        cases = [(n,b) for n in SILESIA for b in (65536,1048576)] if algorithm=='lz4' else [(n,0) for n in ('bash','python3','libc.so.6')]
        require([(r['case'],r['block_bytes']) for r in record['inputs']]==cases, 'input matrix differs')
        inputs = {}
        for item in record['inputs']:
            path = Path(item['path']); require(path.is_relative_to(prepared), 'input outside retained preparation')
            require(path.stat().st_size==item['bytes'] and sha(path)==item['sha256'], 'full input differs')
            if algorithm=='xz':
                path = Path(item['compressed_path']); require(path.is_relative_to(prepared), 'compressed input outside preparation')
                require(path.stat().st_size==item['compressed_bytes'] and sha(path)==item['compressed_sha256'], 'compressed input differs')
            inputs[item['case'],item['block_bytes']] = item
        if algorithm=='lz4':require(sum(i['bytes'] for i in record['inputs'])==2*211938580, 'Silesia corpus reduced')
        expected = Counter((n,b,r,backends[(p+r+i)%3],p) for i,(n,b) in enumerate(cases) for r in range(11) for p in range(3))
        require(Counter((t['case'],t['block_bytes'],t['outer_run'],t['backend'],t['position']) for t in record['trials'])==expected,
                'trial matrix/order differs')
        operations = ('compress','decompress') if algorithm=='lz4' else ('decompress',)
        for trial in record['trials']:
            item = inputs[trial['case'],trial['block_bytes']]
            require(trial['full_output_match'] and trial['output_sha256']==item['sha256'] and
                    trial['bytes']==item['bytes'] and trial['rows']==len(operations), 'output validation differs')
            if algorithm=='lz4':
                require(trial['independent_cross_decode_match'] and trial['blocks']==(item['bytes']+item['block_bytes']-1)//item['block_bytes'],
                        'independent complete block decoding differs')
        raw = list(csv.DictReader((directory/'raw.csv').open()))
        require(Counter((r['case'],int(r['block_bytes']),int(r['outer_run']),r['backend'],r['operation']) for r in raw)==
                Counter((n,b,r,backend,op) for n,b in cases for r in range(11) for backend in backends for op in operations), 'raw matrix differs')
        for row in raw:
            item = inputs[row['case'],int(row['block_bytes'])]
            require(row['status']=='pass' and int(row['cpu'])==cpu and int(row['bytes'])==item['bytes'] and
                    int(row['repeats'])>0 and int(row['elapsed_ns'])>=10000000, 'invalid raw timing')
            require(int(row['blocks']) == ((item['bytes']+item['block_bytes']-1)//item['block_bytes'] if algorithm=='lz4' else 1), 'incomplete blocks')
            if algorithm=='xz':require(int(row['compressed_bytes'])==item['compressed_bytes'], 'incomplete compressed bytes')
        symbols = {}
        for line in (directory/'kallsyms.txt').read_text().splitlines():
            fields=line.split()
            if len(fields)>=3:symbols.setdefault(fields[2],[]).append((int(fields[0],16),fields[3].strip('[]') if len(fields)>3 else 'vmlinux'))
        methods = {'compress':'LZ4_compress_default','decode':'LZ4_decompress_safe'} if algorithm=='lz4' else {
            'init':'xz_dec_init','run':'xz_dec_run','reset':'xz_dec_reset','end':'xz_dec_end','crc_init':'xz_crc32_init'}
        require(Counter((b['backend'],b['method'],b['symbol']) for b in record['bindings'])==
                Counter((backend,method,prefix+symbol) for backend,prefix in zip(backends,('','matched_','vkso_'))
                        for method,symbol in methods.items() if not (method=='crc_init' and
                        (backend=='stock-kernel' or (new_xz and backend=='matched-build-kernel')))), 'API matrix differs')
        for binding in record['bindings']:
            address=int(binding['address'],16)
            provider = 'vkso_'+algorithm if binding['backend']=='owner-kernel' else 'matched_'+algorithm if binding['backend'] in ('matched-direct-kernel','matched-build-kernel') else 'lz4_compress' if algorithm=='lz4' and binding['method']=='compress' else 'vmlinux'
            require(address and binding['provider']==provider and symbols.get(binding['symbol'])==[(address,provider)], 'actual API target differs')
        detail=dict(timing_rows=len(raw),trials=len(record['trials']),full_input_cases=len(cases),
                    timed_full_file_passes=sum(int(r['repeats']) for r in raw))
    return dict(status='pass',algorithm=algorithm,deployment=deployment.name,boot_id=identity['boot_id'],
                cpu=cpu,owner_build_id=build_id,registration_sessions=len(transactions),detail=detail,
                scope='physical-host raw measurement, full-input and API/owner identity reconstruction; PFN evidence separately archived')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deployment',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=audit(args.deployment)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
