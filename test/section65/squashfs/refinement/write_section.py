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
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads(a.analysis.read_text());audit=json.loads(a.audit.read_text());mem=json.loads(a.resources.read_text())
    assert data['status']==audit['status']==mem['status']=='complete'
    assert data['observations']==audit['observations']==6540
    rows=data['results'];paragraphs={}
    native=[r for r in rows if r['kind']=='native-final' and r['phase']=='fresh-mount' and r['baseline']=='native-small-normal' and r['treatment']=='prepared-xz']
    assert len(native)==10
    seq=[one(rows,kind='native-stream',codec=c,workload='archive',phase='fresh-mount',baseline='native-small-normal',treatment='prepared-xz') for c in ['xz','lz4']]
    increment=one(rows,kind='native-stream',codec='xz',workload='archive',phase='fresh-mount',baseline='prepared-composed',treatment='prepared-xz')
    paragraphs['NATIVE_RESULTS']=(
        'Against the equally optimized normal native reference, final fresh-mount scan changes range from '+
        span([r for r in native if r['workload']=='scan'])+', and archive changes from '+
        span([r for r in native if r['workload']=='archive'])+
        r' (Figure~\ref{fig:filesystem-native}). The largest upper interval endpoint across these ten cells is '+
        pc(max(r['ratio_ci95'][1] for r in native))+
        '. The larger xz and lz4 archives change by '+effect(seq[0])+' and '+effect(seq[1])+
        ', respectively. Relative to the preceding LZ4-composed owner, adding common XZ changes the native xz sequential task by '+effect(increment)+'.')
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
        '; the full table retains their per-task intervals.')
    threaded=[one(rows,kind='application-final',codec=c,workload='archive',baseline='stock-single',treatment='vkso') for c in ['gzip','lz4']]
    xz_threaded=one(rows,kind='application-final',codec='xz',workload='scan',baseline='stock-single',treatment='vkso')
    paragraphs['THREAD_RESULTS']=(
        'Against single-thread SquashFUSE, gzip and lz4 include archives instead change by '+
        effect(threaded[0])+' and '+effect(threaded[1])+'. The corresponding scans are close in point estimate, whereas xz scan remains faster at '+
        effect(xz_threaded)+'. Thus stock threading explains much of the gzip/lz4 metadata advantage over its default configuration, but not the large xz difference.')
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
    paragraphs['MEMORY_RESULTS']=(
        'After the include archive, VKSO helper PSS is '+memory_range('vkso')+
        ', compared with '+memory_range('stock')+' for default SquashFUSE, '+
        memory_range('stock-single')+' for single-thread SquashFUSE, and '+
        memory_range('lkl-cache-512')+' for cache-matched LKL. In separate untimed metadata-scale runs, VKSO retained PSS is '+
        ', '.join(f"{r['pss_kib']/1024:.2f}" for r in scale)+
        r'~MiB after visiting 5,866, 23,464 and 93,856 entries. At the largest scale, default/single-thread SquashFUSE and cache-matched LKL retain '+
        ', '.join(f"{r['pss_kib']/1024:.2f}" for r in large)+
        r'~MiB, respectively. The scale result exposes the cost of retaining private metadata; the small-tree footprint is not a fixed runtime-memory bound.')
    deploy=mem['deployment_summary']['core_export_registration']
    paragraphs['DEPLOYMENT_RESULTS']=(
        'Across nine ordinary application campaigns, core construction, export and registration take a median '+
        f"{deploy['median']:.3f}"+r'~s (observed range '+
        f"[{deploy['minimum']:.3f}, {deploy['maximum']:.3f}]"+r'~s), excluding compilation, module loading and validation. '+
        'This setup is reused by later invocations while the owner and registration remain installed; an owner reload or version change requires fresh deployment. Copied artifact construction also has a setup cost, so these measurements do not assume that its preparation is free.')
    text=Path(__file__).with_name('section65-template.tex').read_text()
    if audit.get('interrupted_campaigns'):
        assert len(audit['interrupted_campaigns'])==1 and audit['interrupted_campaigns'][0]['partial_observations']==28
        text=text.replace('Instrumented diagnostics and pilots supply no formal times.',
            'Instrumented diagnostics and pilots supply no formal times. A server restart interrupted one campaign after 28 observations; those records remain separate, and the whole campaign was rerun with the same parameters.')
    for key,value in paragraphs.items():
        token='@@'+key+'@@';assert text.count(token)==1;text=text.replace(token,value)
    assert '@@' not in text
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    a.output.with_suffix('.numbers.json').write_text(json.dumps(dict(status='complete',analysis=str(a.analysis.resolve()),
        audit=str(a.audit.resolve()),resources=str(a.resources.resolve()),paragraphs=paragraphs,
        selected_evidence=dict(native=native,sequential=seq,composition_increment=increment,sharing=sharing,matched_sharing=matched,single_cpu=single,application=app,lkl=lkl,heldout=held,decoder=dec,scale=scale)),indent=2)+'\n')
    print('wrote evidence-backed section draft',a.output)


if __name__=='__main__':main()
