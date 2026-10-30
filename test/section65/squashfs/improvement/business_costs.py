#!/usr/bin/env python3
"""Separate installed VKSO infrastructure from measured filesystem business costs."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--resources', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--table', type=Path, required=True)
    a = p.parse_args()
    data = json.loads(a.resources.read_text())
    assert data['status'] == 'complete'
    modules = data['kernel_module_residency']
    references = data['native_preparation_module_residency']
    assert {r['reference_module_bytes'] for r in references} == {61440}
    core, consumer = modules['vkso_sq_core'], modules['vkso_squashfs']
    delta = core + consumer - references[0]['reference_module_bytes']
    assert delta == 36864 and data['unique_shared_bytes'] == 28672
    reg = data['registration']
    assert reg['direct_requested_bytes'] == reg['transaction_requested_bytes'] + data['shared_pages'] * reg['binding_requested_bytes']
    stages = {r['stage']: {s['campaign']: s['seconds'] for s in r['samples']}
              for r in data['stages']}
    definitions = {
        'core_export_registration': ['krg', 'export', 'register'],
        'business_load_export_registration': [
            'load-vkso_sq_core', 'load-vkso_squashfs',
            'load-vkso_kernel_reader', 'krg', 'export', 'register'],
    }
    timing = {}
    for name, names in definitions.items():
        campaigns = sorted(stages[names[0]])
        assert len(campaigns) == 9
        assert all(set(stages[n]) == set(campaigns) for n in names)
        samples = [dict(campaign=c, seconds=sum(stages[n][c] for n in names))
                   for c in campaigns]
        values = [s['seconds'] for s in samples]
        timing[name] = dict(stages=names, samples=samples,
                            median=statistics.median(values),
                            minimum=min(values), maximum=max(values))
    output = dict(
        status='complete',
        premise='VKSO platform installed; page_cache_replace is a one-time system-wide cost, excluded from filesystem business subtotals.',
        source=dict(path=str(a.resources.resolve()),
                    sha256=hashlib.sha256(a.resources.read_bytes()).hexdigest()),
        platform=dict(module='page_cache_replace', resident_bytes=modules['page_cache_replace'],
                      charged_to_business_bytes=0, allocation='once per installed system, not per core or process'),
        business=dict(owner_resident_bytes=core, native_consumer_resident_bytes=consumer,
                      prepared_native_resident_bytes=core+consumer,
                      native_reference_resident_bytes=references[0]['reference_module_bytes'],
                      native_preparation_delta_bytes=delta,
                      shared_backing_avoided_once_bytes=data['unique_shared_bytes'],
                      registration_requested_bytes=reg['direct_requested_bytes'],
                      extra_owner_bytes_when_prepared_native_already_resident=0,
                      user_only_owner_resident_bytes=core),
        timing=timing,
        accounting_rules=[
            'Preparation remains a business cost when starting with the original native module; do not silently treat it as already paid.',
            'Adding a user consumer to an already prepared native service needs no second owner; its requested registration metadata and private objects remain business costs.',
            '28 KiB is an avoided backing, not a process-count multiplier or a whole-machine net saving.',
            'Per-helper PSS includes required frontend/bridge/runtime/decompressor mappings for every backend, including LKL; no backend-specific working memory is subtracted.',
            'Module sizes, requested metadata and process PSS are separate ledgers, not quantities to sum into a calibrated system total.',
            'Stage times are sums within each recorded campaign before aggregation; core export/registration excludes module loads, compilation and validation.',
        ])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(output, indent=2)+'\n')
    table = r'''\begin{table*}[t]
\centering\small
\caption{Filesystem-specific kernel and backing costs with VKSO infrastructure
already installed. Module residency, avoided backing and requested metadata
are distinct quantities. User-process costs appear separately in
Table~\ref{tab:filesystem-resources}.}
\label{tab:filesystem-business}
\begin{tabular}{lr}
\toprule
Item & Size \\
\midrule
Original native module & __ORIGINAL__~KiB \\
Prepared owner + native consumer & __PREPARED__~KiB \\
Native preparation increment & __DELTA__~KiB \\
Avoided duplicate core backing & __SHARED__~KiB \\
Requested registration metadata & __REG__ bytes \\
\bottomrule
\end{tabular}
\end{table*}
'''
    for key, value in dict(ORIGINAL=references[0]['reference_module_bytes']//1024,
                           PREPARED=(core+consumer)//1024, DELTA=delta//1024,
                           SHARED=data['unique_shared_bytes']//1024,
                           REG=f"{reg['direct_requested_bytes']:,}").items():
        table = table.replace('__'+key+'__', str(value))
    a.table.parent.mkdir(parents=True, exist_ok=True)
    a.table.write_text(table)
    print(json.dumps(dict(status='complete', native_preparation_delta_bytes=delta,
                          export_registration=timing['core_export_registration']['median'])))


if __name__ == '__main__':
    main()
