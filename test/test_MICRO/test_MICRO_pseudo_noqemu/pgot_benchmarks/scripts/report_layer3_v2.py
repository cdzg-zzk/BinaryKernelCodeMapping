#!/usr/bin/env python3
"""Evidence-linked interpretation and review tables, without changing paper prose."""
import argparse
import csv
from pathlib import Path
from layer3_v2 import ROOT, ROUTINES, BUILDS, VARIANTS, write_csv

def read(p):return list(csv.DictReader(p.open()))
def main(a):
    old=read(a.fixed/'ablation.csv');new=read(a.campaign/'ablation.csv')
    history=read(a.fixed/'historical-vs-fixed.csv')
    lookup=lambda rows:{(r['routine'],r['build'],r['variant']):r for r in rows}
    h,f,c=map(lookup,[history,old,new]);changes=[]
    lines=['# Layer-3 fixed-batch final assessment','',
        'All four routines, both builds and all applicable ablations have completed formal timing: '
        '64 module loads, 2,400 paired inner records and 160 outer-run comparison estimates. '
        'No formal measurements are pending. Each configuration uses eight module loads and 15 paired '
        'ABBA/BAAB rounds per comparison. Reported costs are TSC ticks per operation.','',
        '## Historical reconstruction and new confirmation','',
        'The historical selected report does not match the available raw archive in any of its 20 rows. '
        'Its percentages are retained as reported values; the available raw data are the source for '
        'the fixed-batch reconstruction. Changes between these columns cannot all be attributed to '
        'batch selection. `../layer3-fixed-batch-v2/historical-vs-fixed.csv` also applies the old '
        'batch choices to the available raw data, separating selection changes from provenance differences.','',
        '| Routine | Build | Variant | Historical report (%) | Fixed-batch archive (%) | Confirmatory (%) | 95% CI | Outer-run range (%) |',
        '|---|---|---|---:|---:|---:|---|---|']
    for name in ROUTINES:
        for b in BUILDS:
            for v in (('data_pgot',) if name.startswith('01') else VARIANTS):
                key=(name,b,v);r=c[key];p=float(r['overhead_pct'])
                changes.append(dict(routine=name,build=b,variant=v,historical_reported_pct=h[key]['historical_reported_pct'],
                    fixed_archive_pct=f[key]['overhead_pct'],confirmatory_pct=r['overhead_pct'],
                    ci_low_pct=r['ci_low_pct'],ci_high_pct=r['ci_high_pct'],outer_min_pct=r['run_min_pct'],outer_max_pct=r['run_max_pct']))
                lines.append(f"| {name[3:]} | {b} | {v} | {float(h[key]['historical_reported_pct']):+.3f} | {float(f[key]['overhead_pct']):+.3f} | {p:+.3f} | [{float(r['ci_low_pct']):+.3f}, {float(r['ci_high_pct']):+.3f}] | [{float(r['run_min_pct']):+.3f}, {float(r['run_max_pct']):+.3f}] |")
    lines+=['','## Answers to the prespecified interpretation questions','',
        '1. **SHA-256 remains close to Origin.** The archive and confirmatory medians are below 0.1% '
        'in magnitude in both builds. Confirmatory outer-bootstrap intervals cross zero. '
        'The archived SHA benchmark had no explicit output check; the new run validates both '
        'transform states and the padded-block digest outside timing.','',
        '2. **BCH no-retpoline requires a variability qualification.** The fixed-batch archive gives '
        '6.329% All-PGOT, rather than the historical reported 1.976%. The confirmation median is '
        '1.945% with a 95% median CI of [1.859%, 2.359%], but one of eight loads reaches 17.000%. '
        'Data-PGOT rises to 16.593% in that same load (run_id=6), whereas Func-PGOT stays at 1.286% '
        'and paired Origin costs remain about 5,490 ticks. Every load is retained. A small median '
        'does not establish uniformly small per-load cost. The source of this load-specific '
        'data-path slowdown is not established by the collected diagnostics.','',
        '3. **BCH retpoline: the archive does not preserve Func dominance; the confirmation does.** '
        'Archive Data/Func/All medians are 7.152/2.835/9.648%. In the confirmation they are '
        '0.514/2.944/3.408%; the helper-only intervention reproduces most of the full-adaptation '
        'increase. Four rewritten memcpy sites each execute once per encode, and their formal '
        'objects contain the protected indirect sequences. This supports helper adaptation as '
        'the principal observed contribution in the new retpoline run; it is not a decomposition '
        'of the total into a fixed per-thunk price.','',
        '4. **Zstd Data-only stays small.** Confirmation Data medians are -0.266% and -0.158%. '
        'The no-retpoline Func median is 0.336%, so Data and Func are both small there. Under '
        'retpoline the Func and All medians are 7.560% and 6.551%; the corresponding archive '
        'values are 7.789% and 6.624%. The helper-only intervention reproduces the substantial '
        'retpoline-build increase. Its value exceeding All also shows why ablation deltas '
        'cannot be added as independent components.','',
        '5. **zlib remains near Origin at the complete-adaptation level, without an optimization claim.** '
        'Confirmatory All medians are +0.763% and -0.750%. The retpoline All interval lies below '
        'zero in this particular campaign; the sign is reported as observed, not called noise '
        'by fiat. Data-only is +2.023% in that build and Func-only +0.044%. This non-additive '
        'pattern, together with the machine-code differences documented below, means the '
        'negative aggregate result does not establish an intrinsic PGOT speedup. The specific '
        'instruction/layout cause of that small change has not been isolated.','',
        '6. **The original qualitative story is only partly preserved by reanalysis.** SHA, zlib '
        'and retpoline Zstd broadly retain it. BCH in the available archive changes materially; '
        'the new campaign recovers small typical BCH costs but also exposes a large no-retpoline '
        'load-specific increase. The archived and new results are presented separately.','',
        'The confirmatory figure shows all outer-run points alongside the medians and CIs; '
        'the large BCH observation is visible. No batch was selected using an adapted cost or '
        'delta. Neither cross-build subtraction nor division by helper count is used for '
        'causal retpoline attribution. The workloads remain the four fixed inputs specified '
        'in the task.','',
        '## Evidence locations','',
        '- `ablation.csv`: all 20 comparisons with paired Origin/adapted costs, deltas, percentages, ranges and CIs.',
        '- `origin-and-variants.csv`: explicit backend rows, with Origin retained per comparison.',
        '- `outer-runs.csv`, per-routine `raw.csv`, logs and `sessions.json`: all repetition levels.',
        '- `figures/ablation.pdf` and `.png`: two-panel grayscale ablation figure.',
        '- `MECHANISM-EVIDENCE.md`, `static-evidence/` and `diagnostics/`: source/object and non-timed execution evidence.',
        '- `../layer3-fixed-batch-v2/README.md`: reproduction and artifact map.','',
        'Historical data are preserved and paper prose has not been edited in this revision.']
    if a.campaign.resolve()!=(ROOT/'results/layer3-confirmatory-v2').resolve():
        # The reviewed interpretation above belongs to the preserved reference
        # campaign. A fresh campaign gets its actual table, never old claims.
        lines=lines[:lines.index('## Answers to the prespecified interpretation questions')]+[
            '## Interpretation for this reproduction', '',
            'The table above is regenerated from this campaign. The reviewed narrative in '
            '../layer3-confirmatory-v2/FINAL-ASSESSMENT.md belongs to the reference campaign '
            'and is not automatically transferred to these new measurements. All raw values, '
            'outer-run ranges, intervals and the figure above use this reproduction.']
    (a.campaign/'FINAL-ASSESSMENT.md').write_text('\n'.join(lines)+'\n');write_csv(a.campaign/'historical-fixed-confirmatory.csv',changes)
    mechanism(a)

def mechanism(a):
    stats=read(a.campaign/'static-evidence/object-summary.csv')
    lines=['# Mechanism evidence','',
        'Formal timings have no diagnostic counters. A separately compiled BCH module uses '
        '`PGOT_DIAGNOSTIC=1` and returns after its checks, emitting no raw timing records. '
        'Static evidence was generated from the actual formal objects; complete linked-module '
        'objdump output is saved in every routine/build directory.','',
        '## SHA-256','',
        'Origin and Data each have an 872-byte transform with 214 static instructions in both '
        'builds. Data contains the `pgot_k_table` slot reference; Origin references the constant '
        'table directly. Both contain zero indirect transfers and zero retpoline loops in the '
        'transform. Thus the small signed timing changes do not involve a new helper-call path.','',
        '## BCH','',
        '| Diagnostic site | Source operation | Executions per fixed encode |',
        '|---|---|---:|',
        '| 0 | `load_ecc8`: copy remaining ECC bytes to pad | 1 |',
        '| 1 | `bch_encode`: copy ECC words into local r | 1 |',
        '| 2 | `bch_encode`: copy local r back into ECC words | 1 |',
        '| 3 | `store_ecc8`: copy remaining pad bytes to output | 1 |','',
        '`diagnostics/bch-helper-counts.csv` records these counts for Origin, Data, Func and All '
        'in both builds (32 records). Origin/Data contain four direct memcpy sites. Func/All '
        'contain four helper-slot references and either four ordinary indirect transfers '
        '(no retpoline) or four inline-retpoline loops. The additional direct memory call '
        'in the algorithm is memset in the no-ECC branch, not a rewritten memcpy site. '
        'Internal algorithm helpers remain direct.','',
        'For example, in `static-evidence/02_bch_encode-retpoline-bench_kmod.txt`, '
        '`load_ecc8_func_pgot` loads `pgot_memcpy_table` at relocation 0x489, then uses '
        'the call/pause/lfence loop at 0x4ab–0x4b5 and stores the target at (%rsp) before ret. '
        'The instruction context and all other sites are indexed in `binding-sites.csv` '
        'and `binding-contexts.md`. These are formal uninstrumented objects.','',
        '## zlib','',
        'Four rewritten source locations are enumerated in `helper-source-sites.csv`: '
        'CLEAR_HASH memset, read_buf memcpy, fill_window sliding-window memcpy, and copy_block '
        'pending-buffer memcpy. Macro expansion/inlining produces five helper-slot references '
        'in each Func/All object. Other direct memory-helper operations introduced through '
        'included code or compilation remain direct; Func-PGOT here means the existing selected '
        'source transformations, not replacement of every possible memory operation.','',
        'Origin already dispatches through its compression configuration table, so its '
        'retpoline object already has one protected indirect path. Data retains that one; '
        'Func/All have six. Data also changes code generation beyond a single address-load '
        'instruction. In the retpoline build, `zlib_tr_init` sizes are 2300/1123/2300/1123 '
        'bytes for Origin/Data/Func/All, and `zlib_deflateReset` sizes are 475/325/502/352 '
        'bytes. `function-sizes.csv` and the six `zlib-*.diff` files show the full '
        'comparison. These are static code sizes, not counts of dynamically retired '
        'instructions. They demonstrate nonlocal compiler effects but do not by themselves '
        'prove which change caused the small negative All timing.','',
        '## Zstd','',
        'Data redirects LL_defaultDTable, ML_defaultDTable, OF_defaultDTable and algoTime. '
        'Func redirects the existing memcpy/memset/memmove source locations across the five '
        'copied compilation units. Every rewritten source statement has its generated-file '
        'line and context in `helper-source-sites.csv`. The final objects contain 102 helper '
        'slot references and 109 protected indirect paths in each Func/All retpoline variant. '
        'Slot-reference and transfer counts need not coincide because a loaded target can '
        'feed multiple branches; neither number is a dynamic call count for the fixed input. '
        'Origin/Data already contain two protected indirect paths.','',
        '`closure_func_pgot_decompress.o` provides concrete examples: '
        '`pgot_ZSTD_execSequenceLast7_func_pgot.isra.0` references `pgot_memmove_table_func_pgot` '
        'at 0x5d3 and has its protected call at 0x5f7–0x609; '
        '`pgot_ZSTD_decompressBegin_func_pgot` references the memcpy slot at 0xb69. '
        'Checking only decompressDCtx would miss these lower-level sites. Static evidence '
        'and the Data/Func/All timing interventions together support the mechanism '
        'interpretation; they do not assign the full percentage solely to thunk instructions.','',
        '## Static object inventory','',
        'Text bytes sum function-symbol sizes; alignment padding is excluded. Relocations '
        'count static references, and retpoline loops count static pause sites in inspected '
        'algorithm functions. Timed body wrappers are excluded.','',
        '| Routine/build/variant | Text bytes | Data slot refs | Helper slot refs | Direct memory calls | Indirect transfers | Inline-retpoline loops |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in stats:lines.append('| '+ '/'.join(r[k] for k in ('routine','build','variant'))+' | '+ ' | '.join(r[k] for k in ('text_bytes','data_slot_references','helper_slot_references','direct_memory_calls','indirect_transfers','inline_retpoline_loops'))+' |')
    if a.campaign.resolve()!=(ROOT/'results/layer3-confirmatory-v2').resolve():
        lines=['# Static evidence for this reproduction', '',
               'Object-derived inventory follows. Exact object offsets and reviewed source '
               'interpretation in the reference campaign must be checked against this '
               'campaign before reuse.', '']+lines[lines.index('## Static object inventory'):]
    (a.campaign/'MECHANISM-EVIDENCE.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixed',type=Path,required=True);p.add_argument('--campaign',type=Path,required=True);main(p.parse_args())
