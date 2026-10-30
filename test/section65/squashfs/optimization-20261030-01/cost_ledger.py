#!/usr/bin/env python3
"""Account source categories and ELF scope without converting lines into hours."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from elftools.elf.elffile import ELFFile

OPT=Path(__file__).resolve().parent
HERE=OPT.parent
sys.path.insert(0,str(HERE))
from prepare import span

SECTION=HERE.parent
ROOT=SECTION.parents[1]

def profile_source(path):
    lines=path.read_text().splitlines();ranges=[];start=None;depth=0
    for number,line in enumerate(lines,1):
        stripped=line.strip()
        if start is None and stripped=='#ifdef VKSO_SQ_PROFILE':start=number;depth=1;continue
        if start is not None:
            if re.match(r'#\s*(if|ifdef|ifndef)\b',stripped):depth+=1
            elif re.match(r'#\s*endif\b',stripped):
                depth-=1
                if depth==0:ranges.append([start,number]);start=None
    assert start is None
    calls=[n for n,line in enumerate(lines,1) if re.search(r'\bSQ_(START|COUNT|ELAPSED)\s*\(',line)]
    return dict(path=str(path),profile_conditional_ranges=ranges,profile_conditional_lines=sum(b-a+1 for a,b in ranges),macro_call_lines=calls,
        scope='Physical source footprint within the reported file; conditional ranges include preprocessor lines. Macro-call lines can also contain functional statements, so these counts are not subtracted as disjoint semantic SLOC. Profiling is compiled out of production.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--source-dir',type=Path,help='Exact user C sources used by this build; defaults to the current source tree')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build=a.build.resolve();user_source=(a.source_dir or HERE).resolve()
    adaptation=json.loads((build/'adaptation.json').read_text())
    shared=(build/'shared_core.c').read_text();changes=[]
    for row in adaptation['functions']:
        original=(Path(adaptation['source'])/row['source']).read_text()
        begin,end=span(original,row['function']);before=re.sub(r'^static\s+','',original[begin:end]).splitlines()
        begin,end=span(shared,row['function']);after=re.sub(r'^static\s+','',shared[begin:end]).splitlines()
        added=removed=0
        for op,i,j,k,l in difflib.SequenceMatcher(a=before,b=after,autojunk=False).get_opcodes():
            if op in ('replace','delete'):removed+=j-i
            if op in ('replace','insert'):added+=l-k
        changes.append(dict(function=row['function'],source=row['source'],original_lines=len(before),
                            added=added,removed=removed,body_changed=before!=after))
    groups={
        'handwritten_preparation_generator':[HERE/'prepare.py'],
        'first_user_integration':[user_source/'user_bridge.c',user_source/'posix_io.c',user_source/'fuse_frontend.c'],
        'specific_apptainer_integration':[user_source/'apptainer_helper.c'],
        'user_build_generator':[HERE/'build_user.py'],
        'generated_native_support':[build/n for n in ['kernel_support.c','core_metadata.c','shared_types.h','shared_remap.h']],
        'generated_common_owner':[build/'shared_core.c'],
        'inherited_owner_runtime_header':[build/'owner.h'],
        'lkl_application_generator':[SECTION/'lkl/sif_frontend.py'],
        'lkl_cache_diagnostic_generator':[SECTION/'lkl/cache_frontend.py'],
        'experimental_harness':[f for f in HERE.glob('*.py') if f.name not in ['prepare.py','build_user.py','apptainer_helper.py']]}
    if (build/'shared_lz4.c').exists():
        groups['assembled_existing_codec_sources']=[build/'shared_lz4.c',build/'lz4defs.h']
        groups['improvement_build_generators']=[HERE/'improvement/build_native_copy.py',HERE/'improvement/build_codec.py']
        groups['experimental_harness'] += sorted((HERE/'improvement').glob('*.py'))
        groups['experimental_harness']=[f for f in groups['experimental_harness'] if f not in groups['improvement_build_generators']]
        groups['diagnostic_profile_header']=[user_source/'profile.h']
    if (build/'xz-composition.json').exists():
        groups['reused_and_modified_xz_algorithm_sources']=[build/(n+'.c') for n in ['xz_dec_stream','xz_dec_lzma2','xz_dec_bcj']]
        groups['xz_headers_and_generated_service_binding']=[build/n for n in ['xz_lzma2.h','xz_stream.h','xz_private.h','sq_xz_api.h','xz_names.h','xz_services.h','xz_support.c']]
        groups['xz_composition_generator']=[HERE/'refinement/build_xz.py']
        groups['experimental_harness'] += [f for f in sorted((HERE/'refinement').glob('*.py')) if f.name!='build_xz.py']
        groups['optimization_build_generators']=[OPT/'build_candidate.py',OPT/'build_native_controls.py']
        groups['optimization_algorithm_patch']=[OPT/'dictionary_word.inc']
        groups['experimental_harness'] += [f for f in sorted(OPT.glob('*.py')) if f not in groups['optimization_build_generators']]
    lines=[]
    for category,paths in groups.items():
        for path in paths:
            text=path.read_text().splitlines()
            label=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
            lines.append(dict(category=category,path=label,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),physical_lines=len(text),
                              nonblank_lines=sum(bool(l.strip()) for l in text)))
    native_files=[]
    for source in sorted(Path(adaptation['source']).iterdir()):
        if source.suffix not in ['.c','.h'] or not (build/source.name).exists():continue
        before=source.read_text().splitlines();after=(build/source.name).read_text().splitlines()
        added=removed=0
        for op,i,j,k,l in difflib.SequenceMatcher(a=before,b=after,autojunk=False).get_opcodes():
            if op in ('replace','delete'):removed+=j-i
            if op in ('replace','insert'):added+=l-k
        native_files.append(dict(file=source.name,upstream_lines=len(before),prepared_lines=len(after),
            changed=before!=after,added=added,removed=removed,
            extracted_functions=[r['function'] for r in adaptation['functions'] if r['source']==source.name]))
    lkl_record=json.loads((SECTION/'build/lkl/build-squash-only/sif-frontend/build.json').read_text())
    binaries=[]
    for name in ['vkso_sq_core.ko','vkso_squashfs.ko','libsq-bridge.so','vkso-squashfuse','vkso-squash-helper']:
        path=build/name
        with path.open('rb') as stream:
            elf=ELFFile(stream)
            sections=[dict(name=s.name,bytes=s['sh_size'],writable=bool(s['sh_flags']&1),
                          executable=bool(s['sh_flags']&4),initialization=s.name.startswith(('.init','.exit')))
                      for s in elf.iter_sections() if s['sh_flags']&2]
        binaries.append(dict(path=str(path),disk_bytes=path.stat().st_size,allocated_sections=sections,
                             note='Allocated ELF bytes are not page-rounded module residency or process RSS.'))
    diff=subprocess.check_output(['git','diff','--numstat','HEAD','--','make_dll/build_PIC_so.py'],cwd=ROOT,text=True).strip()
    result=dict(accounting='Physical lines include comments/blanks; no reliable developer-hour measurements.',
                services=adaptation['services'],operation_tables=adaptation['operation_tables'],
                moved_functions=changes,source_lines=lines,binaries=binaries,
                inline_profiling_source=[profile_source(user_source/n) for n in ['user_bridge.c','posix_io.c','fuse_frontend.c']],
                native_files=native_files,
                native_file_accounting='Raw upstream-to-generated-consumer deltas include mechanical extraction, public declarations, native service exposure, owner binding and filesystem renaming. They are not handwritten semantic-edit counts. See kernel.patch in the frozen build.',
                native_changed_file_count=sum(r['changed'] for r in native_files),
                lkl_application_added_lines=lkl_record['added_lines'],
                lkl_cache_diagnostic='Two timeout assignments changed in a separate frontend; not part of the 30-line SIF application integration.',
                runtime_support='Existing page_cache_replace/manager/krg and owner ABI reused; no new registration implementation for this SquashFS case. Incremental exporter corrections are accounted separately.',
                tracked_exporter_change_numstat=diff,
                exporter_attribution=dict(
                    baseline='Git HEAD; current worktree diff retained in the evaluation freeze',
                    inspected_changes=['Retain relocation-referenced readonly sections, including local literals and section-symbol addends (squash-export-02 failure).',
                        'Preserve the page-aligned ro-after-init group and validate runtime symbol offsets (squash-export-03 failure).'],
                    exporter_sha256=hashlib.sha256((ROOT/'make_dll/build_PIC_so.py').read_bytes()).hexdigest(),
                    scope='All current exporter diff hunks implement these two fixes. This is incremental general-exporter work, not the cost of developing the whole exporter.',
                    regression_sources=['make_dll/tests/test_module_ro_closure.py','make_dll/tests/test_ko_core_layout.py']),
                limitations=[
                 'Generated glue and its generator are distinct maintenance surfaces; do not sum them as handwritten implementation.',
                 'Baseline begins with existing SquashFUSE/LKL and existing Apptainer. LKL project size is not integration effort.',
                 'Source inventory describes the retained implementation, not cumulative development work, discarded prototypes or developer hours. Inline disabled profiling source is identified separately within file totals.',
                 'Known upstream patch is reproduced, not independently discovered.'])
    if (build/'shared_lz4.c').exists():
        result['codec_composition']=dict(additional_service_slots=3,additional_callable_exports=2,
            source='Existing adapted Section 6.3 safe LZ4 decoder and header; retain the generic decoder plus safe entry, omit other API entries.',
            handwritten_changes='Rename exported safe entry, define/bind private memory-helper slots, redirect native wrapper and user dispatch, update export/build lists.',
            source_reuse_accounting='The assembled codec and header include reused code and generated binding additions. They are not new handwritten lines or an independent implementation.',
            user_source_directory=str(user_source))
    if (build/'xz-composition.json').exists():
        composition=json.loads((build/'xz-composition.json').read_text())
        algorithm_deltas=[]
        for row in composition['original_decoder_sources']:
            original=Path(row['path']);candidate=build/original.name
            assert hashlib.sha256(original.read_bytes()).hexdigest()==row['sha256'], 'upstream provenance changed'
            before=original.read_text();after=candidate.read_text()
            changed_bodies=[]
            if original.name=='xz_dec_lzma2.c':
                b,e=span(before,'dict_repeat');c,d=span(after,'dict_repeat')
                assert before[:b]==after[:c] and before[e:]==after[d:], 'unexpected changes outside dict_repeat'
                assert before[b:e]!=after[c:d]
                changed_bodies=['dict_repeat']
            else:
                assert before==after, 'unexpected non-LZMA2 algorithm change'
            added=removed=0
            for op,i,j,k,l in difflib.SequenceMatcher(a=before.splitlines(),b=after.splitlines(),autojunk=False).get_opcodes():
                if op in ('replace','delete'):removed+=j-i
                if op in ('replace','insert'):added+=l-k
            algorithm_deltas.append(dict(file=original.name,original_sha256=row['sha256'],
                candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                original_physical_lines=len(before.splitlines()),candidate_physical_lines=len(after.splitlines()),
                added=added,removed=removed,body_edits=changed_bodies,unchanged=before==after,
                patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='upstream/'+original.name,tofile='optimized/'+original.name))))
        result['xz_composition']=dict(original_sources=composition['original_decoder_sources'],
            additional_service_slots=9,additional_callable_exports=6,
            original_algorithm_physical_lines=composition['original_decoder_physical_lines'],
            candidate_algorithm_physical_lines=sum(r['candidate_physical_lines'] for r in algorithm_deltas),
            algorithm_deltas=algorithm_deltas,edited_algorithm_bodies=['dict_repeat'],
            interpretation='Originally 2604 physical algorithm lines; this version modifies dict_repeat in the shared native/user XZ core. It is not a zero-body-edit port. Lines include comments/blanks and conditional paths; executed coverage requires runtime evidence and source size is not developer time.',
            native_changes='XZ wrapper include redirects the public API to owner exports; native PREALLOC allocation semantics are retained. Kernel support binds nine private environment services.',
            user_changes='Bind private allocator/memory/CRC services and select the common XZ SINGLE-mode API for complete contiguous compressed blocks; remove liblzma dependency.')
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(moved_functions=len(changes),original_lines=sum(r['original_lines'] for r in changes),
        changed_bodies=[r['function'] for r in changes if r['body_changed']],services=result['services'])))


if __name__=='__main__':main()
