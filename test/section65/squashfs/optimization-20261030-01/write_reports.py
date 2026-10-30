#!/usr/bin/env python3
"""Generate current-version review documents from completed, audited evidence."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path('/home/zzk/BinaryKernelCodeMapping');SECTION=ROOT/'test/section65'
RUNS=(SECTION/'build/squashfs/optimization-runs-01').resolve()
REL='test/section65/build/squashfs/optimization-runs-01/'
def read(p):return json.loads(p.read_text())
def one(rows,**keys):
    found=[r for r in rows if all(r.get(k)==v for k,v in keys.items())];assert len(found)==1,(keys,len(found));return found[0]
def pct(x):return f'{100*(x-1):+.2f}%'
def effect(r):return f"{pct(r['time_ratio'])} [{pct(r['ratio_ci95'][0])}, {pct(r['ratio_ci95'][1])}]"
def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path,required=True);a=p.parse_args();analysis=a.analysis.resolve()
    data=read(analysis/'analysis.json');audit=read(analysis/'audit.json');mem=read(analysis/'resource-ledger/resources.json');cost=read(analysis/'costs.json')
    assert data['status']==audit['status']==mem['status']=='complete'
    assert data['observations']==audit['observations']==7692 and len(data['inputs'])==30
    out=analysis/'documents';out.mkdir();rows=data['results'];rel=REL+analysis.name+'/'
    get=lambda **kw:one(rows,**kw)
    native=[r for r in rows if r['kind']=='native-final' and r['phase']=='fresh-mount' and r['baseline']=='native-word-normal' and r['treatment']=='prepared-optimized']
    sharing=[r for r in rows if r['kind']=='application-final' and r['workload']!='startup' and r['baseline']=='copied' and r['treatment']=='vkso']
    streams={c:get(kind='application-final',codec=c,workload='stream',baseline='stock',treatment='vkso') for c in ['gzip','xz','lz4']}
    python={b:get(kind='heldout',codec='xz',workload='compile',baseline=b,treatment='vkso') for b in ['stock','stock-single','copied','lkl-cache-512']}
    warm=get(kind='native-final',codec='xz',workload='archive',phase='warm',baseline='native-word-normal',treatment='prepared-optimized')
    scale={v:[one(mem['scale'],scale=n,variant=v)['pss_kib']/1024 for n in [1,4,16]] for v in ['vkso','copied-unbounded','stock','stock-single','lkl-cache-512']}
    b=mem['business'];deploy=mem['deployment_summary']['core_export_registration']
    verdicts=read(SECTION/'claim-verdicts.json');assert len(verdicts['claims'])==13
    mapping={c['id']:c for c in verdicts['claims']}
    def setclaim(id,finding,evidence,limits=None):
        c=mapping[id];c['finding']=finding;c['evidence']=evidence
        if limits is not None:c['limits']=limits
    setclaim('C1','Current binaries pass 30 five-format-plus-BCJ mounts; common XZ/LZ4 native calls are 190/73. Copied and shared instructions match byte-for-byte but only shared execution matches nine native PFNs. Actual native and conflicting SIF B/C consumers preserve private state and independent lifetimes; 160 additional decoder observations and retained-handle/cursor churn pass.',
        [REL+n+'/result.json' for n in ['functional-01','simultaneous-01','native-calls-01','shared-decoder-01']]+['test/section65/build/squashfs/optimization-cache-guest-01/result.json'])
    setclaim('C2',f"The seven-condition native matrix includes identical word-edited normal/relaxed XZ references, prior normal/relaxed references and prior prepared XZ. Fresh scan/archive points span {min(r['time_ratio'] for r in native):.4f}-{max(r['time_ratio'] for r in native):.4f}; the largest upper CI endpoint is {max(r['ratio_ci95'][1] for r in native):.4f}. Warm XZ include archive changes {effect(warm)} against matched optimized normal native.",
        [rel+'analysis.json',rel+'audit.json',REL+'hardening-01/result.json'],
        'No further hardening relaxation, but inherited canary/external-thunk runtime parity remains unimplemented. Optimized references bundle XZ whereas older native references call host XZ; residency boundaries differ. One host/boot, no pure-PGOT or zero-cost inference.')
    setclaim('C3',f"Nine nonempty ordinary VKSO/copied points span {min(r['time_ratio'] for r in sharing):.4f}-{max(r['time_ratio'] for r in sharing):.4f}; their pointwise CI endpoints span {min(r['ratio_ci95'][0] for r in sharing):.4f}-{max(r['ratio_ci95'][1] for r in sharing):.4f}. All startup, equal-path and single-CPU estimates are separately retained in the complete table.",
        [rel+'analysis.json',rel+'audit.json'],
        'Matching instructions, bridge, frontend and cache policy isolate backing within each condition. Small point estimates or nonsignificance do not prove equivalence, a universal overhead bound, or general preference over copied.')
    setclaim('C4','XZ sequential VKSO/default-stock change is '+effect(streams['xz'])+'. Fixed Python XZ compilation changes '+effect(python['stock'])+' versus default stock and '+effect(python['lkl-cache-512'])+' versus matched-cache LKL. All codecs/tasks, startup and both stock threading/LKL cache policies remain in the table.',
        [rel+'analysis.json',rel+'audit.json',REL+'metadata-work-01/result.json','test/section65/backend-conditions.md'],
        'Python was a holdout in the predecessor evaluation, but was consulted in this optimization; it is a fixed separate workload, not unseen validation here. Backend/codecs/threads/mitigations differ. No universal speed, zstd/lzo application-speed or concurrent-throughput claim.')
    linecounts={Path(r['path']).name:r['physical_lines'] for r in cost['source_lines'] if r['category']=='first_user_integration'}
    setclaim('C5',f"34 filesystem functions cover 2103 original physical lines; three filesystem bodies and 16 native files differ. XZ source extent is 2604 original / 2637 candidate lines, with dict_repeat explicitly edited (35 added/2 removed by line diff). Owner text is 28052 B, up 224 B from the preceding common-XZ owner. Bridge/POSIX/frontend line counts are {linecounts['user_bridge.c']}/{linecounts['posix_io.c']}/{linecounts['fuse_frontend.c']}; inode pinning/eviction is charged as adapter work.",
        [rel+'costs.json',rel+'reuse-audit/result.json'],
        'This is not zero-body-edit XZ reuse. Original physical extent, line deltas, generated support and semantic edits are separate measures, not developer hours. LKL application-only extension remains 30 lines at its existing-frontend starting point.')
    setclaim('C6','Original-scale VKSO retained PSS is '+', '.join(f'{x:.2f}' for x in scale['vkso'])+' MiB; same-core unbounded-copied is '+', '.join(f'{x:.2f}' for x in scale['copied-unbounded'])+f" MiB. Largest-scale single-thread stock retains {scale['stock-single'][-1]:.2f} MiB. Direct-adapter repeated scans hold 2048 inode/4096 name entries. One resident native owner avoids {b['shared_backing_avoided_once_bytes']//1024} KiB backing and requests {b['registration_requested_bytes']} B registration metadata.",
        [rel+'resource-ledger/resources.json',REL+'cache-scale-direct-01/result.json',REL+'minimal-deployment-01/result.json'],
        'Cache limits exclude active pinned handles and open-directory listings. Entire FUSE process memory still grows and is not uniformly below stock. Single untimed scale observations are not peaks/CIs. Component residency/PSS/metadata are separate, not whole-machine net saving.')
    setclaim('C7','The original guest-only old/fixed repair experiment remains unchanged. The optimized final owner retains the repaired filesystem source; current native/copied/shared malformed-input regressions return EIO, user daemons survive, normal regressions and cleanup pass. New dictionary and cache changes are separate from the historical unchanged-adapter repair experiment.',
        ['test/evaluation-local/runs/iso9660/squash-maintenance-02/result.json','test/section65/build/squashfs/improvement-analysis-01/maintenance.json','test/section65/build/squashfs/optimization-cache-guest-01/result.json'])
    setclaim('C8','Current real-SIF hardware breakpoint reaches common XZ with arguments/available stack; native/shared PFNs remain identical afterward and native regression/cleanup pass. Historical ISO9660 additionally supplies single-step evidence.',
        [REL+'simultaneous-01/result.json','test/evaluation-local/runs/iso9660/maintenance-oneshot-01/evidence/debug/result.json'])
    setclaim('C9','Actual algorithm/source reuse, explicit edits and common repair are measured. No reliable developer/debugger hours or controlled human-task experiment exists.',[rel+'costs.json','test/evaluation-local/runs/iso9660/squash-maintenance-02/result.json'])
    setclaim('C10',f"Whole-machine net saving remains unmeasured. Owner/consumer residency is {b['owner_resident_bytes']//1024}+{b['native_consumer_resident_bytes']//1024} KiB; optimized bundled-XZ native reference is {b['native_reference_resident_bytes']//1024} KiB, with a different packaging boundary from host-XZ native. Construction/export/registration median is {deploy['median']:.3f} s, range [{deploy['minimum']:.3f}, {deploy['maximum']:.3f}], excluding compilation/module load. Generic 32 KiB platform residency is charged once, not per filesystem.",
        [rel+'resource-ledger/resources.json',REL+'minimal-deployment-01/result.json'])
    setclaim('C11','Simultaneous consumers demonstrate private state and lifetimes. Thirty confirmation campaigns use new process/mount/module cycles on one host/boot; no throughput curve, running-process update or cross-host/boot replication is supplied.',
        ['test/section65/squashfs/optimization-20261030-01/PROTOCOL.md',REL+'simultaneous-01/result.json',rel+'audit.json'])
    setclaim('C12','Copied receives the same word-copy, cache and common-repair benefits and runs after all task modules unload. VKSO additionally reuses the native physical backing, conditional on owner/support residency. General preference over copied is not established.',
        [rel+'resource-ledger/resources.json',rel+'costs.json',REL+'minimal-deployment-01/result.json'])
    setclaim('C13','A current shared filesystem/decoder body serves real native and SIF consumers with private objects, explicit source-edit costs and common maintenance. Original-workload timing and metadata-scale evidence delimit usefulness; Python cost, startup uncertainty, hardening and total-memory limits are preserved.',
        [rel+'analysis.json',rel+'audit.json',rel+'resource-ledger/resources.json',rel+'costs.json',REL+'simultaneous-01/result.json'],
        'The optimization is common to copied and shared execution. No universal speed/compactness/adoption preference follows. Rump is conceptual related work, not a measured timing baseline; the Python workload is not unseen for this optimization.')
    for id in ['C9','C10','C11','C12']:assert mapping[id]['verdict']=='not-supported'
    verdicts.update(status='complete',version='xz-word-bounded-cache',scope='30 fresh complete campaigns / 7692 observations, independently replayed. No predecessor or development samples pooled. Fixed Python workload consulted during optimization, not unseen holdout.',
        predecessor='test/section65/build/squashfs/evaluation-refined-02/identity.json')
    for c in verdicts['claims']:
        assert all((ROOT/name).exists() for name in c['evidence']),c['id']
        c['paper_action']='Report the finding and retained limits above in the current Section 6.5; do not substitute predecessor numbers.'
    (out/'claim-verdicts.json').write_text(json.dumps(verdicts,indent=2)+'\n')
    lines=['# Section 6.5 claim-to-experiment map','',
        'Current version: `xz-word-bounded-cache`. The Introduction asks what resident bodies can be reused, how independent environments execute them, and what duplication/execution/deployment costs result. Section 6.5 supplies a read-only filesystem and real SIF case, not a precondition of universal performance advantage. Section 6.4 shares published time state; this case preserves independent native/user objects. Sections 6.1-6.4 remain unchanged.','',
        'The frozen matrix has 30 campaigns / 7,692 observations on one host/boot. Selection and original workload/block/seed definitions are in `squashfs/optimization-20261030-01/confirmation-registration.json`; statistics are independently replayed. The preceding 6,540-observation implementation, all failed candidates, and partial historical runs remain separate. Python was consulted during this optimization and is not an unseen holdout.','',
        '| Claim | Verdict | Current finding | Retained limits |','| --- | --- | --- | --- |']
    for c in verdicts['claims']:lines.append('| '+ ' | '.join(str(c[k]).replace('|','/').replace('\n',' ') for k in ['id','verdict','finding','limits'])+' |')
    lines+=['','Exact evidence paths and testable questions are in [claim-verdicts.json](claim-verdicts.json).','',
        'Correctness/PFN/lifetime failures block promotion. All original task directions, startup, warm phases and imprecise/adverse intervals remain. No significance-based stopping or favorable-block selection is used. Code volume is not human time; simultaneous lifetime is not throughput scaling; process PSS is not whole-machine memory.','',
        'The generic 32 KiB page_cache_replace module is installed-platform infrastructure. Owner/consumer preparation, per-core registration and private runtime state remain business costs. Ordinary copied DSOs also share among user processes; avoided backing has no per-process multiplier.']
    (out/'claim-experiment-map.md').write_text('\n'.join(lines)+'\n')
    result=['# Section 6.5 optimization results','',f"Version: `xz-word-bounded-cache`. {len(data['inputs'])} completed campaigns, {data['observations']:,} fresh observations, {len(data['results'])} audited paired comparisons; no development/historical times pooled.",'',
        '## Complete-task effects','', '| Task / baseline | Elapsed change [pointwise 95% CI] |','| --- | --- |']
    for c,r in streams.items():result.append(f'| {c} stream / default stock | {effect(r)} |')
    for base,r in python.items():result.append(f'| Python XZ / {base} | {effect(r)} |')
    for c in ['gzip','xz','lz4']:
        for base in ['stock','copied']:result.append(f"| {c} startup / {base} | {effect(get(kind='application-final',codec=c,workload='startup',baseline=base,treatment='vkso'))} |")
    result+=['', 'Absolute times and every codec/task/control/phase are in analysis.json and summary.csv. Ratios use equal-weight campaign mean log paired ratios; absolute times use means of campaign medians. Three campaigns are the independent analysis units, not thousands of independent replications. CIs are pointwise and same-boot.','',
        '## Memory and adoption boundaries','', '| Backend | 5,866 entries | 23,464 entries | 93,856 entries |','| --- | ---: | ---: | ---: |']
    for v,values in scale.items():result.append('| '+v+' | '+' | '.join(f'{x:.2f} MiB' for x in values)+' |')
    result+=['','Retained helper PSS; one separate untimed process/mount per point, not peaks or CIs. Traversal counts include one root entry beyond the labels. Direct-adapter counters remain 2048/4096 across three scans at each scale, but open handles, directory lists and other FUSE/runtime state are outside these budgets. Entire process memory is not constant and is not uniformly lower than stock.','',
        '## Implementation and rejected hypotheses','',mapping['C5']['finding'],'',
        'The selected common dictionary optimization retains baseline ISA/compiler/hardening policy. Word repetition has overlap/wrap/tail guards. Jump tables, small service inlining, O3 and scalar-mask rc_bit were not selected. Branchless masks passed differential/stream checks but increased instructions and elapsed time on the fixed Python block. No further unbounded code/layout/input search was performed.','',
        'API lifetime churn, over-budget pinned handles, sanitized private adapter, real FUSE cursors/descriptors, final native/copied/shared guest regressions, BCJ, actual common decoder calls, simultaneous conflicting SIFs, breakpoint/PFNs, and owner-only/copied-minimal deployment all passed. Sanitizer core/leak coverage and contiguous-buffer decoder diagnostic limits remain explicit.','',
        '## Claims and remaining costs','',mapping['C2']['finding'],'',mapping['C3']['finding'],'',mapping['C10']['finding'],'',
        'The predecessor Python workload was consulted in development and is not an unseen holdout here. Native hardening equivalence, developer/debugger hours, hot update, throughput scaling, cross-boot generality, whole-machine net memory and universal preference over copied remain unsupported.','',
        'See the registered queue, independent audit, exact source/binary freeze, provenance-backed figures and preserved pre-optimization publication. No commit, push, reboot, kernel configuration change, malformed-input host mount or credential persistence is part of this work.']
    (out/'RESULTS.md').write_text('\n'.join(result)+'\n')
    status=['# Section 6.5 - word-copy XZ and bounded-cache evaluation','',
        f"The selected implementation has completed 30 fresh campaigns / 7,692 timed observations and independent replay of {len(data['results'])} paired comparisons. The current source, correctness/physical evidence, component accounting and results are separate from all predecessor versions.",'',
        '## Key findings','',mapping['C4']['finding'],'',mapping['C6']['finding'],'',mapping['C5']['finding'],'',mapping['C3']['finding'],'',
        '## Current evidence','',
        '- Protocol, exact selection and queues: `squashfs/optimization-20261030-01/`.',
        '- Fresh analysis, independent audit, code and resource ledgers: `build/squashfs/optimization-runs-01/analysis-final-01/`.',
        '- Final binary/source freeze: `build/squashfs/evaluation-optimized-01/identity.json`.',
        '- Current paper: `../../paper/filesystem-section-preview.pdf`; canonical source: `../../paper/paper_content/sections/06-evaluation.tex`.',
        '- Current claim map/judgments: `claim-experiment-map.md`, `claim-verdicts.json`; publication completion: `final-evidence.json`.',
        '- Prior publication, including exact old PDF, source and figures: `../../paper/build/section65-preoptimization-publication-01/identity.json`.',
        '- Detailed result and limits: `squashfs/optimization-20261030-01/RESULTS.md`.',
        '', '## Scope and preserved history','',
        'Only Section 6.5 is updated; the preceding Evaluation content is hash-checked unchanged. This is a standalone Section 6.5 preview, not a whole-paper rebuild. The general 32 KiB platform remains one-time infrastructure; preparation, per-core metadata and private runtime are retained costs.','',
        'The common-XZ predecessor has 30 campaigns / 6,540 observations and remains in `refined-analysis-01` / `evaluation-refined-02`. The composed-LZ4 39-campaign / 11,328-observation and initial 34-campaign / 13,968-observation versions also remain intact. Their adverse results and interrupted partial runs are not relabeled or pooled.','',
        'Python was consulted during this optimization, not an unseen holdout. No universal speed/compactness, human-time, hardening-equivalence, hot-update, concurrent scaling, cross-host/boot or whole-machine saving claim follows. Copied receives the same algorithm/cache/repair benefits.']
    (out/'STATUS.md').write_text('\n'.join(status)+'\n')
    print('generated current-version claim map, 13 judgments, results and status; canonical files not changed')
if __name__=='__main__':main()
