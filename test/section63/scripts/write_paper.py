#!/usr/bin/env python3
"""Render the section's current evidence-backed prose and tables in LaTeX/Markdown."""
import csv
import json
from pathlib import Path
import argparse
import re


def build(base):
    out=base/'paper-material'
    data=list(csv.DictReader((base/'analysis/summary.csv').open()))
    lookup={(r['algorithm'],r['domain'],r['workload'],r['target'],r['baseline']):r for r in data}
    def overhead(a,d,w,t,b):return 100*(float(lookup[a,d,w,t,b]['median_cost_ratio'])-1)
    def user(a,w):return overhead(a,'user',w,'kernel-vkso','native-dso')
    b4=-user('bch','m=13/t=4/bytes=512/errors=2/decode-precomputed')
    b8=-user('bch','m=13/t=8/bytes=512/errors=2/decode-precomputed')
    b8worst=user('bch','m=13/t=8/bytes=512/errors=8/decode-precomputed')
    b8full=user('bch','m=13/t=8/bytes=512/errors=8/decode-full')
    kencode=overhead('bch','kernel','m=13/t=4/bytes=512/errors=0/encode','owner-kernel','stock-kernel')
    audit=__import__('json').loads((base/'analysis/audit.json').read_text())
    n_bch=audit.get('repetition_count',{'bch':3})['bch']
    assert n_bch==12, 'current manuscript requires the completed BCH follow-up'
    diag=list(csv.DictReader((base/'diagnostics/summary.csv').open()))
    def diagnostic(a,w,t,b):return 100*(float(next(r for r in diag if (r['algorithm'],r['workload'],r['target'],r['baseline'])==(a,w,t,b))['median_cost_ratio'])-1)
    c4=-diagnostic('bch','t=4/errors=2/decode-precomputed','cached-matched','original-matched')
    c8=-diagnostic('bch','t=8/errors=2/decode-precomputed','cached-matched','original-matched')
    pmu=json.loads((base/'repeat-bch/pmu-facts.json').read_text())
    u42=pmu['user']['t4-e2'];u82=pmu['user']['t8-e2'];u88=pmu['user']['t8-e8']
    k88=pmu['kernel']['t8-e8']
    unstable=lookup['bch','kernel','m=13/t=4/bytes=512/errors=0/decode-precomputed','owner-kernel','matched-kernel']
    unstable_lo=100*(float(unstable['minimum_deployment_ratio'])-1)
    unstable_hi=100*(float(unstable['maximum_deployment_ratio'])-1)
    paragraphs=[
('',r'''We evaluate LZ4, BCH, and XZ through their actual VKSO carriers,
then invoke the same export owners from kernel benchmarks.
The user comparison includes an ordinary port of the original Linux
algorithm (\emph{Native}), a user DSO containing the owner's algorithm
rewrites and feature configuration (\emph{Adapted}), and \emph{VKSO}.
Native and Adapted use the same \texttt{-O2} user compiler options.
In the kernel, we compare the distribution implementation (\emph{Stock}),
the original source and dependencies under the owner's code-generation
options (\emph{Matched}), and the exported \emph{Owner}.
VKSO/Native and Owner/Stock measure the complete execution cost of
adopting the export. The intermediate versions help explain that cost.'''),
('',rf'''LZ4 processes all twelve Silesia files at three user block sizes
(4\,KiB, 64\,KiB, and 1\,MiB); the kernel uses the latter two. BCH uses 512-byte inputs with $m=13$,
$t\in\{{4,8\}}$, and zero through $t$ errors. XZ decodes three complete
streams. On a pinned core of an i7-1165G7 running Linux 5.15.0-119,
we use {n_bch} BCH module loads and three loads each for LZ4 and XZ,
summarizing paired costs by their median within and then across loads. Timing
includes algorithm reset and helper calls, with loading and binding
completed beforehand.'''),
('User execution.',r'''Figure~\ref{fig:exported-algorithms} shows that LZ4 compression
costs 0.5--1.4\% less than Native, while decompression costs
1.5--2.0\% more. The decompression difference is already present
in the Adapted DSO: VKSO differs from Adapted by approximately
$-0.1$\% to $+0.1$\%. XZ's complete-stream cost is 0.8--0.9\%
above Native and 1.1--1.2\% above Adapted. These comparisons include
the domain-local helper calls and their ABI bridges.'''),
('',rf'''BCH's response depends on the decode path. Precomputed decode
receives an ECC difference and measures syndrome computation and
error-location search. With two errors, VKSO reduces this cost by
{b4:.1f}\% for $t=4$ and {b8:.1f}\% for $t=8$ relative to Native.
The reduction does not extend across the error-count sweep:
with eight errors at $t=8$, precomputed and full decode cost
{b8worst:.1f}\% and {b8full:.1f}\% more, respectively. The full sweep is
retained with the experiment results.'''),
('Kernel consumers.',rf'''Table~\ref{{tab:export-kernel}} reports the costs of the dedicated
export owners. LZ4 is within 0.4\% of Stock for compression and
2.6--3.1\% faster for decompression. BCH includes both reductions
in decode cost and a {kencode:.1f}\% increase for $t=4$ encoding. XZ adds
4.3--5.2\% relative to Stock, although Matched is approximately
2.5--2.6\% below Stock. The XZ increase therefore appears when
applying the export's source and dependency adaptations to the
matched build.'''),
('BCH execution paths.',rf'''The adopted syndrome loop caches its table pointer explicitly.
The original kernel build reloads this pointer inside the loop,
whereas the ordinary user build hoists the load. Disabling strict-alias
analysis in the original user build reproduces the reload.
The loop-only kernel control reduces two-error precomputed cost
by {c4:.1f}\% at $t=4$ and {c8:.1f}\% at $t=8$.
Independent user-space PMU measurements show that the complete VKSO
operation retires {u42['kernel-vkso']['instructions']:,.0f} rather than
{u42['native-dso']['instructions']:,.0f} instructions at $t=4$, and
{u82['kernel-vkso']['instructions']:,.0f} rather than {u82['native-dso']['instructions']:,.0f}
at $t=8$. The reduction in executed work accompanies the gains in
both two-error configurations.'''),
('',rf'''At higher error counts, root finding changes the balance of work.
Linux BCH uses specialized solvers through degree four and polynomial
factorization above that degree. With eight errors, VKSO retires
{u88['kernel-vkso']['instructions']:,.0f} instructions versus
{u88['native-dso']['instructions']:,.0f} for Native, while branch misses rise
from {u88['native-dso']['branch_misses']:.2f} to {u88['kernel-vkso']['branch_misses']:.2f}
per operation. The kernel comparison has the opposite instruction-count
direction: Owner retires approximately {k88['owner-kernel']['instructions']:,.0f}
instructions versus {k88['stock-kernel']['instructions']:,.0f} for Stock.
The two domains compare different generated implementations, explaining
why the user-side increase coexists with a kernel-side reduction.'''),
('Variation across loads.',rf'''The $t=4$ zero-error path varies across loads:
Owner/Matched ranges from {unstable_lo:.1f}\% to {unstable_hi:+.1f}\%
across twelve loads. Its diagnostic instruction count, branch-miss
count, L1D misses, and cycle/reference-cycle ratio remain nearly
constant despite latency variation. The two-error reductions persist
when all three kernel implementations rotate through the same allocated
contexts within each diagnostic load. Figure~\ref{{fig:exported-algorithms}}
and Table~\ref{{tab:export-kernel}} retain the full load ranges.'''),
('XZ dependency cost.',r'''The XZ difference is dominated by its CRC dependency. Stock and
Matched call the kernel CRC32 implementation, whereas the export
contains XZ's compact internal CRC32 routine. In a separate kernel
control, we retain the owner's decoder, feature configuration, and
helper slots, and replace the CRC body with a call to kernel CRC32.
The original owner costs 7.1--7.8\% more than this control. The
control is 2.3--3.2\% below Stock. Replacing this dependency thus
removes the observed kernel-side regression. Both user DSOs use
the portable internal CRC32 routine, explaining why the user comparison
has a much smaller gap. We next examine shared state and concurrency
using Linux clocktime.''')]
    figure=r'''\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth]{figures/exported_algorithms.pdf}
  \caption{Execution overhead of actual user-space exports. Points show
  medians of paired load results. Whiskers span the load medians (twelve for BCH, three for LZ4/XZ).
  LZ4 C/D denote compression/decompression. BCH Full/Pre denote full
  and precomputed decode with two errors. The complete BCH error-count
  sweep and initialization costs are reported separately.}
  \label{fig:exported-algorithms}
\end{figure*}'''
    tex=[r'\subsection{Exported Kernel Algorithms}',r'\label{sec:exported-algorithms}','']
    md=['## Exported Kernel Algorithms','']
    kernel=list(csv.DictReader((out/'kernel-table.csv').open()))
    for i,(heading,text) in enumerate(paragraphs):
        tex += [(r'\paragraph{'+heading+'}\n' if heading else '')+text,'']
        plain=text.replace('Figure~\\ref{fig:exported-algorithms}','The user results figure').replace('Table~\\ref{tab:export-kernel}','Table 9')
        plain=re.sub(r'\\(?:emph|texttt)\{([^{}]*)\}',r'`\1`',plain)
        plain=plain.replace(r'\%', '%').replace(r'\,',' ').replace('--','–')
        md += [('**'+heading+'** ' if heading else '')+' '.join(plain.split()),'']
        if i==1:
            tex += [figure,'']
            md += ['![Execution overhead of actual user-space exports](figures/exported_algorithms.svg)','',
                '**Figure: Execution overhead of actual user-space exports.** Points show medians of paired load results; whiskers span load medians (twelve for BCH, three for LZ4/XZ). LZ4 C/D denote compression/decompression. BCH Full/Pre use two errors; the full error-count sweep and initialization costs are in the [complete results](../../test/section63/results/paper-material/tables.md).','']
        if i==4:
            tex += [(out/'kernel-table.tex').read_text(),'']
            md += ['**Table 9: Kernel execution costs of the actual export owners.** Stock is the distribution implementation; Matched retains original source and dependencies with owner code-generation options. Brackets span load medians (twelve for BCH, three for LZ4/XZ). BCH decode rows use two errors.','',
                   '| Algorithm | Operation/input | Owner / Stock | Owner / Matched |','| --- | --- | --- | --- |']
            md += ['| '+' | '.join((r['algorithm'].upper(),r['label'],r['owner_stock'],r['owner_matched']))+' |' for r in kernel]
            md += ['']
    md += ['The [experiment report](../../test/section63/results/report.md) provides the six version definitions, complete paired results, source and compiler records, and separate causal controls.','']
    (out/'section63.tex').write_text('\n'.join(tex).replace('}\\n','}\n'))
    (out/'section63.md').write_text('\n'.join(md))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();build(a.directory.resolve())
