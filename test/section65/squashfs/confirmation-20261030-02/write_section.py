#!/usr/bin/env python3
"""Fill the result paragraphs from audited final data, retaining all task directions."""
import argparse
import json
from pathlib import Path

def one(rows,**keys):
    found=[r for r in rows if all(r.get(k)==v for k,v in keys.items())]
    assert len(found)==1,(keys,len(found));return found[0]
def pc(value):return f'{100*(value-1):+.2f}'+r'\%'
def effect(row):
    low,high=row['ratio_ci95']
    return pc(row['time_ratio'])+' ['+pc(low)+', '+pc(high)+']'
def span(rows):
    values=[r['time_ratio'] for r in rows]
    return pc(min(values))+' to '+pc(max(values))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--resources',type=Path,required=True)
    p.add_argument('--costs',type=Path,required=True)
    p.add_argument('--reuse-audit',type=Path,required=True)
    p.add_argument('--diagnostics',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads(a.analysis.read_text());audit=json.loads(a.audit.read_text());mem=json.loads(a.resources.read_text())
    assert data['status']==audit['status']==mem['status']=='complete'
    assert data['observations']==audit['observations']==8172
    costs=json.loads(a.costs.read_text());reuse=json.loads(a.reuse_audit.read_text())
    rows=data['results'];paragraphs={}
    native=[r for r in rows if r['kind']=='native-final' and r['phase']=='fresh-mount' and r['baseline']=='native-word-normal' and r['treatment']=='prepared-optimized']
    assert len(native)==10
    seq=[one(rows,kind='native-stream',codec=c,workload='archive',phase='fresh-mount',baseline='native-word-normal',treatment='prepared-optimized') for c in ['xz','lz4']]
    increment=one(rows,kind='native-stream',codec='xz',workload='archive',phase='fresh-mount',baseline='prepared-xz',treatment='prepared-optimized')
    warm=one(rows,kind='native-final',codec='xz',workload='archive',phase='warm',baseline='native-word-normal',treatment='prepared-optimized')
    paragraphs['NATIVE_RESULTS']=(
        'Against the equally optimized normal native reference, final fresh-mount scan changes range from '+
        span([r for r in native if r['workload']=='scan'])+', and archive changes from '+
        span([r for r in native if r['workload']=='archive'])+
        r' (Figure~\ref{fig:filesystem-native}). The largest upper interval endpoint across these ten cells is '+
        pc(max(r['ratio_ci95'][1] for r in native))+
        '. The larger xz and lz4 archives change by '+effect(seq[0])+' and '+effect(seq[1])+
        ', respectively. Relative to the preceding common-XZ owner, the dictionary edit changes the native xz sequential task by '+effect(increment)+
        '. Warm xz include archive changes by '+effect(warm)+'.')
    sharing=[r for r in rows if r['kind']=='application-final' and r['workload']!='startup' and r['baseline']=='copied' and r['treatment']=='vkso'];assert len(sharing)==9
    single=one(rows,kind='sharing-singlecpu',codec='gzip',workload='stream',baseline='copied',treatment='vkso')
    matched=[r for r in rows if r['kind']=='decoder-diagnostic' and r['baseline']=='copied' and r['treatment']=='vkso'];assert len(matched)==4
    paragraphs['SHARING_RESULTS']=(
        r'For the nine nonempty ordinary application tasks, VKSO/copied point estimates range from '+
        f"{min(r['time_ratio'] for r in sharing):.4f} to {max(r['time_ratio'] for r in sharing):.4f}"+
        ', with pointwise interval endpoints spanning '+
        f"[{min(r['ratio_ci95'][0] for r in sharing):.4f}, {max(r['ratio_ci95'][1] for r in sharing):.4f}]"+
        r' (Figure~\ref{fig:filesystem-sharing}). Equal-length-path xz/lz4 scan/stream controls have point estimates '+
        f"{min(r['time_ratio'] for r in matched):.4f}--{max(r['time_ratio'] for r in matched):.4f}"+
        ' and interval endpoints '+
        f"[{min(r['ratio_ci95'][0] for r in matched):.4f}, {max(r['ratio_ci95'][1] for r in matched):.4f}]"+
        '. The single-CPU gzip-stream change is '+effect(single)+
        '. The observed interval widths bound the precision of the sharing-cost conclusion; they do not establish universal equivalence.')
    app=[r for r in rows if r['kind']=='application-final' and r['baseline']=='stock' and r['treatment']=='vkso'];assert len(app)==12
    streams=[one(app,codec=c,workload='stream') for c in ['gzip','xz','lz4']]
    lkl=[r for r in rows if r['kind']=='application-final' and r['baseline']=='lkl-cache-512' and r['treatment']=='vkso'];assert len(lkl)==12
    paragraphs['APPLICATION_RESULTS']=(
        'Relative to default SquashFUSE, include-scan elapsed changes range from '+
        span([r for r in app if r['workload']=='scan'])+' and include-archive changes from '+
        span([r for r in app if r['workload']=='archive'])+
        '. Sequential gzip, xz and lz4 changes are '+', '.join(effect(r) for r in streams)+
        r', respectively (Figure~\ref{fig:filesystem-application}). Across all twelve ordinary tasks, final VKSO/cache-matched-LKL time ratios range from '+
        f"{min(r['time_ratio'] for r in lkl):.4f} to {max(r['time_ratio'] for r in lkl):.4f}"+
        '; the full table retains their per-task intervals. Startup changes relative to default SquashFUSE are '+
        ', '.join(effect(one(app,codec=c,workload='startup')) for c in ['gzip','xz','lz4'])+' for gzip, xz and lz4.')
    threaded=[one(rows,kind='application-final',codec=c,workload='archive',baseline='stock-single',treatment='vkso') for c in ['gzip','lz4']]
    xz_threaded=one(rows,kind='application-final',codec='xz',workload='scan',baseline='stock-single',treatment='vkso')
    paragraphs['THREAD_RESULTS']=(
        'Against single-thread SquashFUSE, gzip and lz4 include archives instead change by '+
        effect(threaded[0])+' and '+effect(threaded[1])+'. The xz include scan changes by '+
        effect(xz_threaded)+'. Threading policy is therefore a separate baseline condition, not an effect attributed to native/user physical sharing.')
    held=[one(rows,kind='heldout',codec=c,workload='compile',baseline=b,treatment='vkso') for b in ['stock','lkl-cache-512'] for c in ['gzip','xz']]
    paragraphs['HELDOUT_RESULTS']=(
        'VKSO changes complete compilation time by '+effect(held[0])+' (gzip) and '+effect(held[1])+
        ' (xz) relative to default SquashFUSE. Against cache-matched LKL, the changes are '+
        effect(held[2])+' and '+effect(held[3])+r', respectively (Figure~\ref{fig:filesystem-heldout}).')
    dec=[one(rows,kind='decoder-diagnostic',codec=c,workload='stream',baseline=b,treatment=t) for b,t in [('copied-library','copied-retained'),('copied-retained','copied')] for c in ['xz','lz4']]
    paragraphs['DECODER_RESULTS']=(
        'With both external libraries retained, switching from library to common decoding changes xz/lz4 sequential time by '+
        effect(dec[0])+' / '+effect(dec[1])+
        '. Removing the now-unused dependencies while retaining common decoding changes it by '+
        effect(dec[2])+' / '+effect(dec[3])+'. The xz decoder switch changes measured child CPU time by '+
        pc(dec[0]['cpu_ratio'])+', consistent with an execution-cost difference.')
    def memory_range(variant):
        values=[r['pss_kib']/1024 for r in mem['records'] if r['variant']==variant and r['phase']=='after']
        return f'{min(values):.2f}--{max(values):.2f}'+r'~MiB'
    scale=[one(mem['scale'],scale=n,variant='vkso') for n in [1,4,16]]
    large=[one(mem['scale'],scale=16,variant=v) for v in ['stock','stock-single','lkl-cache-512']]
    unbounded=[one(mem['scale'],scale=n,variant='copied-unbounded') for n in [1,4,16]]
    paragraphs['MEMORY_RESULTS']=(
        'After the include archive, VKSO helper PSS is '+memory_range('vkso')+
        ', compared with '+memory_range('stock')+' for default SquashFUSE, '+
        memory_range('stock-single')+' for single-thread SquashFUSE, and '+
        memory_range('lkl-cache-512')+' for cache-matched LKL. In separate untimed metadata-scale runs, VKSO retained PSS is '+
        ', '.join(f"{r['pss_kib']/1024:.2f}" for r in scale)+
        r'~MiB after visiting 5,866, 23,464 and 93,856 entries. At the largest scale, default/single-thread SquashFUSE and cache-matched LKL retain '+
        ', '.join(f"{r['pss_kib']/1024:.2f}" for r in large)+
        r'~MiB, respectively. The same-core unbounded-copied control retains '+
        ', '.join(f"{r['pss_kib']/1024:.2f}" for r in unbounded)+
        r'~MiB over the three scales. These are single untimed observations per scale/backend, not interval estimates or peaks. The small-tree footprint is not a fixed runtime-memory bound.')
    deploy=mem['deployment_summary']['core_export_registration']
    paragraphs['DEPLOYMENT_RESULTS']=(
        'Across nine ordinary application campaigns, core construction, export and registration take a median '+
        f"{deploy['median']:.3f}"+r'~s (observed range '+
        f"[{deploy['minimum']:.3f}, {deploy['maximum']:.3f}]"+r'~s), excluding compilation, module loading and validation. '+
        'This setup is reused by later invocations while the owner and registration remain installed; an owner reload or version change requires fresh deployment. Copied artifact construction also has a setup cost, so these measurements do not assume that its preparation is free.')
    sizes=[r['text_bytes'] for r in reuse['owner_executable_text']];assert len(sizes)==3
    paragraphs['REUSE_RESULTS']=(f"The owner's executable text is {sizes[2]:,} bytes, versus {sizes[1]:,} for the preceding common-XZ version and {sizes[0]:,} for the older LZ4-composed owner. Physical sharing is measured separately below.")
    lines={Path(r['path']).name:r['physical_lines'] for r in costs['source_lines'] if r['category']=='first_user_integration'}
    support=sum(r['physical_lines'] for r in costs['source_lines'] if r['category']=='generated_native_support')
    translator=sum(r['physical_lines'] for r in costs['source_lines'] if r['category']=='specific_apptainer_integration')
    xz=costs['xz_composition'];assert xz['edited_algorithm_bodies']==['dict_repeat']
    paragraphs['ENGINEERING_RESULTS']=(f"Generated kernel support and contract headers occupy {support:,} physical lines. The first user integration contains a {lines['user_bridge.c']:,}-line bridge, {lines['posix_io.c']:,}-line POSIX/codec binding and {lines['fuse_frontend.c']:,}-line FUSE frontend; the application translator adds {translator:,} lines. The XZ source extent changes from {xz['original_algorithm_physical_lines']:,} to {xz['candidate_algorithm_physical_lines']:,} physical lines, with one edited algorithm body in addition to the three filesystem bodies. Cache lifetime and eviction work is included in the user integration totals.")
    cache=[one(rows,kind='heldout',codec=c,workload='compile',baseline='copied-small',treatment='copied') for c in ['gzip','xz']]
    stream_cache=[one(rows,kind='application-final',codec=c,workload='stream',baseline='copied-small',treatment='copied') for c in ['gzip','xz','lz4']]
    paragraphs['OPTIMIZATION_RESULTS']=(
        'The common XZ dictionary-repetition loop uses scalar eight-byte copies, preserving overlap, wrap and tail semantics. The native reference receives the same edit. '
        'Separately, the user bridge replaces its inherited one-slot data scratch cache with the bounded private data cache. Against the one-slot copied bridge on the same owner, complete Python compilation changes by '+effect(cache[0])+' (gzip) and '+effect(cache[1])+' (xz). Ordinary gzip/xz/lz4 sequential tasks change by '+', '.join(effect(r) for r in stream_cache)+'. These cache effects apply to both copied and shared execution; the additional private memory is included below.')
    b=mem['business'];oldref=mem['native_reference_residencies']['native-small-normal']
    paragraphs['COMPONENT_RESULTS']=(
        f"An already prepared native service can avoid one {b['shared_backing_avoided_once_bytes']//1024}"+r'~KiB user backing while requesting '+f"{b['registration_requested_bytes']:,}"+' bytes of registration metadata. The owner and native consumer occupy '+f"{b['owner_resident_bytes']//1024} and {b['native_consumer_resident_bytes']//1024}"+r'~KiB. The normal native reference with bundled optimized XZ occupies '+f"{b['native_reference_resident_bytes']//1024}"+r'~KiB; the preceding reference calling the host XZ decoder occupies '+f'{oldref//1024}'+r'~KiB. These distinct packaging boundaries are not a calibrated kernel-replacement or whole-machine saving. User-only SIF execution succeeds without the native consumer or construction observer; copied execution also succeeds after all task modules unload.')
    text=Path(__file__).with_name('section65-template.tex').read_text()
    if audit.get('interrupted_campaigns'):
        raise AssertionError('New confirmation interruption requires explicit publication accounting')
        text=text.replace('Instrumented diagnostics and pilots supply no formal times.',
            'Instrumented diagnostics and pilots supply no formal times. A server restart interrupted one campaign after 28 observations; those records remain separate, and the whole campaign was rerun with the same parameters.')
    for key,value in paragraphs.items():
        token='@@'+key+'@@';assert text.count(token)==1;text=text.replace(token,value)
    assert '@@' not in text
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    a.output.with_suffix('.numbers.json').write_text(json.dumps(dict(status='complete',analysis=str(a.analysis.resolve()),
        audit=str(a.audit.resolve()),resources=str(a.resources.resolve()),costs=str(a.costs.resolve()),paragraphs=paragraphs,
        selected_evidence=dict(native=native,sequential=seq,composition_increment=increment,sharing=sharing,matched_sharing=matched,single_cpu=single,application=app,lkl=lkl,heldout=held,decoder=dec,scale=scale)),indent=2)+'\n')
    print('wrote evidence-backed section draft',a.output)


if __name__=='__main__':main()
