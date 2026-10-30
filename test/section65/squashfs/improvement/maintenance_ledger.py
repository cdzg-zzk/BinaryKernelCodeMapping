#!/usr/bin/env python3
"""Account actual repair and codec-update artifacts; do not infer developer hours."""
import argparse,difflib,hashlib,json
from pathlib import Path
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[4]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def line_delta(before,after):
    matcher=difflib.SequenceMatcher(a=before.splitlines(),b=after.splitlines(),autojunk=False);added=removed=0
    for tag,i,j,k,l in matcher.get_opcodes():
        if tag!='equal':removed+=j-i;added+=l-k
    return dict(before_lines=len(before.splitlines()),after_lines=len(after.splitlines()),added=added,removed=removed)
def sections(p):
    with p.open('rb') as f:return {s.name:dict(bytes=s['sh_size'],sha256=hashlib.sha256(s.data()).hexdigest()) for s in ELFFile(f).iter_sections() if s['sh_flags']&2}
def transition(old,new):
    rows=[]
    for name in sorted({p.name for d in [old,new] for p in d.iterdir() if p.is_file() and (p.suffix in ['.c','.h','.ko','.so'] or p.name in ['Makefile','symbols.txt','vkso-squashfuse','vkso-squash-helper'])}):
        if name.endswith('.mod.c'):continue
        paths={k:d/name for k,d in [('old',old),('new',new)]};r=dict(file=name)
        for k,p in paths.items():r[k]=dict(sha256=sha(p),bytes=p.stat().st_size) if p.exists() else None
        r['changed']=r['old']!=r['new']
        if all(p.exists() for p in paths.values()) and all(p.read_bytes().startswith(b'\x7fELF') for p in paths.values()):
            values={k:sections(p) for k,p in paths.items()};r['allocated_sections_changed']=[n for n in sorted(set(values['old'])|set(values['new'])) if values['old'].get(n)!=values['new'].get(n)]
        elif name.endswith(('.c','.h')) or name in ['Makefile','symbols.txt']:
            r['line_delta']=line_delta(paths['old'].read_text() if paths['old'].exists() else '',paths['new'].read_text() if paths['new'].exists() else '')
        rows.append(r)
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    base=ROOT/'test/section65/build/squashfs';raw=ROOT/'test/evaluation-local/runs/iso9660'
    repaired=raw/'squash-maintenance-02/fixed-build';initial=base/'reader-adapted';small=base/'improve-native-small-copy-01';composed=base/'improve-codec-01'
    repair=json.loads((raw/'squash-maintenance-02/result.json').read_text());assert repair['status']=='complete'
    changes=dict(upstream_repair=transition(initial,repaired),bounded_copy=transition(repaired,small),combined_codec_and_adapter_update=transition(small,composed),library_vs_common_decoder_same_owner=transition(base/'improve-codec-library-01',composed))
    old_sources=base/'evaluation-fixed-06/source/squashfs';new_sources=composed/'codec-user-source'
    user_deltas={n:line_delta((old_sources/n).read_text() if (old_sources/n).exists() else '',(new_sources/n).read_text()) for n in ['user_bridge.c','posix_io.c','fuse_frontend.c','apptainer_helper.c','profile.h']}
    upstream=[ROOT/'test/section63/source/linux-5.15.0-119.129/lib/lz4/lz4_decompress.c',ROOT/'test/section65/build/native/linux-5.15.198/lib/lz4/lz4_decompress.c']
    assert sha(upstream[0])==sha(upstream[1])
    output=dict(status='complete',scope='Retained actual builds and executed deployment/regression records; lines include blanks/comments and are proxies, not developer time.',
        transitions=changes,user_source_deltas=user_deltas,codec_upstream_identity=[dict(path=str(p),sha256=sha(p)) for p in upstream],
        stages=[
          dict(task='Known upstream negative-offset repair',source='one shared_core.c guard',owner_builds=1,bridge_rebuild_required=False,frontend_rebuild_required=False,
               shared=['rebuild owner','load owner/consumer','regenerate carrier','register','start new user consumers','native and user regressions','restore and unload'],
               copied=['same owner build and export in this experiment','materialize registered instruction image','deploy copied DSO','start new user consumers','native and user regressions'],
               evidence=str(raw/'squash-maintenance-02/result.json')),
          dict(task='Compose safe LZ4 decoder',source='reuse adapted Section 6.3 decoder prefix and header; bind three private memory helpers; update native wrapper and user codec dispatch',
               shared_and_copied_builds=['common owner','native consumer','user bridge'],frontend_semantic_change_required_for_codec=False,
               additional_exports=['vkso_LZ4_decompress_safe','sq_bind_lz4'],additional_private_slots=['memcpy','memmove','memset'],
               dependencies_removed_from_user_bridge=['liblz4.so.1'],
               evidence=[str(composed/'codec-candidate.json'),str(raw/'squash-codec-functional-01/result.json'),str(raw/'squash-codec-guest-regression-01/result.json')])],
        interpretation=[
          'Copied is materialized from the same compiled owner; neither repair nor composition implies a second copied-core compilation.',
          'One common decoder implementation serves both domains; physical sharing additionally identifies the resident instruction backing. Code/source reuse also benefits copied.',
          'Dependency/interface updates require coordinated bridge and native-consumer deployment; the unchanged-adapter result of the one-line repair does not generalize to this update.',
          'The aggregate update also adds directory caching. The separate library-versus-common-decoder control retains that same frontend source; ELF allocated-section deltas distinguish executable changes from rebuild identity.',
          'Regeneration, registration and startup of new consumers are real shared-deployment steps; no hot update or automatic patching of running processes is asserted.',
          'Diagnostic profiling source and experiment runners are retained separately and excluded from application-development time claims.'],
        limitations=['No measured developer hours.','No comparison with the entire LKL codebase as an integration cost.','Artifact counts include generated output; they are not equal units of human effort.'])
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(output,indent=2)+'\n')
    print('maintenance ledger complete')
if __name__=='__main__':main()
