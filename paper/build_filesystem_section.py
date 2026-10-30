#!/usr/bin/env python3
"""Export the canonical Section 6.5 and assemble its standalone preview."""
import argparse
import json
from pathlib import Path
import shutil

PAPER=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--figures',required=True,type=Path)
    p.add_argument('--business-costs',type=Path,help='Derived filesystem ledger with platform costs separated')
    p.add_argument('--allow-draft',action='store_true');a=p.parse_args()
    source=(PAPER/'paper_content/sections/06-evaluation.tex').read_text()
    marker=r'\subsection{Filesystem Reuse in Applications}'
    assert source.count(marker)==1
    section=marker+source.split(marker,1)[1].split(r'\subsection{',1)[0]
    if not a.allow_draft:assert '% Work in progress:' not in section and 'TBD' not in section,'Complete the evidence/results text before final export.'
    figure_dir=PAPER/'figures/section65';figure_dir.mkdir(parents=True,exist_ok=True)
    data_dir=PAPER/'data/section65';data_dir.mkdir(parents=True,exist_ok=True)
    provenance=json.loads((a.figures/'provenance.json').read_text())
    for path in a.figures.iterdir():
        if path.suffix in ['.pdf','.svg','.png']:shutil.copy2(path,figure_dir/path.name)
        elif path.name.startswith('source-') or path.name in ['provenance.json','detail-labels.json']:shutil.copy2(path,data_dir/path.name)
    shutil.copy2(a.figures/'filesystem-detail.tex',PAPER/'tables/filesystem-detail.tex')
    if (a.figures/'filesystem-xz-detail.tex').exists():shutil.copy2(a.figures/'filesystem-xz-detail.tex',PAPER/'tables/filesystem-xz-detail.tex')
    for path in a.figures.glob('filesystem-loader-*.tex'):shutil.copy2(path,PAPER/'tables'/path.name)
    for path in a.figures.glob('filesystem-singlecpu-*.tex'):shutil.copy2(path,PAPER/'tables'/path.name)
    for path in a.figures.glob('filesystem-refinement-*.tex'):shutil.copy2(path,PAPER/'tables'/path.name)
    for destination in [PAPER/'tables',PAPER/'paper_content/tables']:
        shutil.copy2(a.figures/'filesystem-resources.tex',destination/'filesystem-resources.tex')
        if (a.figures/'filesystem-business.tex').exists():
            shutil.copy2(a.figures/'filesystem-business.tex',destination/'filesystem-business.tex')
    if a.business_costs:
        business=json.loads(a.business_costs.read_text())
        assert business['status']=='complete' and business['platform']['charged_to_business_bytes']==0
        shutil.copy2(a.business_costs,data_dir/'business-costs.json')
        shutil.copy2(PAPER/'tables/filesystem-business.tex',PAPER/'paper_content/tables/filesystem-business.tex')
    elif r'\input{tables/filesystem-business.tex}' in section:
        raise ValueError('This section requires --business-costs and its generated table')
    if (a.figures/'filesystem-cache.tex').exists():
        shutil.copy2(a.figures/'filesystem-cache.tex',PAPER/'tables/filesystem-cache.tex')
        shutil.copy2(a.figures/'filesystem-cache.tex',PAPER/'paper_content/tables/filesystem-cache.tex')
    (PAPER/'filesystem-section.tex').write_text(section)
    preview=r'''\documentclass[10pt,twocolumn,letterpaper]{article}
\usepackage[margin=0.75in,columnsep=0.25in]{geometry}
\usepackage[T1]{fontenc}
\usepackage{newtxtext,newtxmath,graphicx,booktabs,longtable,microtype}
\usepackage[hidelinks]{hyperref}
\setlength{\parindent}{1em}
\raggedbottom
\begin{document}
\setcounter{section}{6}\setcounter{subsection}{4}
\input{filesystem-section.tex}
\bibliographystyle{plain}
\bibliography{paper_content/references}
\clearpage\onecolumn
\section*{Filesystem evaluation: complete results}
\small
The table retains every paired comparison from the 34 formal campaigns
(13,968 timed observations). SF denotes SquashFUSE; SF+T adds the C
translator; copy uses identical core instructions with separate physical
backing. LKL64 and LKL512 give configured heap MiB; LKL512c adds one-second
positive FUSE caches. Diag. marks the separate cache-policy campaigns.
Module and Relaxed are the normal and relaxed native module references.
\setlength{\LTcapwidth}{\linewidth}
\input{tables/filesystem-detail.tex}
\clearpage
\begin{figure}[t]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-native-warm.pdf}
\caption{Warm native traversals after a fresh-mount traversal, with warmed image backing. Points are prepared/reference time changes; intervals use campaign-level paired estimates. Reference schemes retain their separate campaign groups. Panels use separate vertical scales.}
\end{figure}
\begin{figure}[t]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-stream-native.pdf}
\caption{Native preparation effects when archiving two 128 MiB files. Fresh and warm filesystem phases are separate. Points and intervals use three independent campaigns on the same host/boot.}
\end{figure}
\clearpage
\begin{figure}[t]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-lkl-cache-effect.pdf}
\caption{Effect of changing LKL positive-entry and attribute timeouts from zero to one second. Both configurations use a 512 MiB heap. Ratios and pointwise 95\% intervals use three paired campaigns per codec.}
\end{figure}
\begin{figure}[t]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-lkl-matched.pdf}
\caption{Complete VKSO/LKL costs with matched one-second positive FUSE cache timeouts. Other backend differences remain as described in the main text. Ratios and pointwise 95\% intervals use the same three diagnostic campaigns per codec.}
\end{figure}
\end{document}
'''
    if (a.figures/'source-improvement-analysis.json').exists():
        data=json.loads((a.figures/'source-improvement-analysis.json').read_text())
        prefix=preview.split(r'\section*{Filesystem evaluation: complete results}',1)[0]
        supplement=r'''\section*{Filesystem evaluation: complete results}
\small
The table retains every paired comparison from the final improvement matrix
(__CAMPAIGNS__ campaigns, __OBSERVATIONS__ timed observations). Absolute table
times are sample medians; paired ratios give each campaign equal weight.
O denotes original native; P0, P16 and PC denote previous prepared,
bounded-copy prepared and composed prepared. N, N16 and NR16 denote normal
native, optimized normal native and optimized relaxed native modules.
SF is SquashFUSE; SF+T adds the translator. A0, AD, AX and AL are copied
controls with the old adapter, directory caching, direct decoder output,
and both adapter changes with liblz4. C and V are the complete copied and
VKSO implementations. L and LC are LKL512 with default and matched positive
FUSE caches. Warm and fresh phases remain separate.
\setlength{\LTcapwidth}{\linewidth}
\input{tables/filesystem-detail.tex}
\clearpage
\begin{figure}[t]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-native-controls.pdf}
\caption{Effect of the same bounded-copy change in prepared and unadapted
native code, and residual prepared cost against optimized normal and relaxed
references. Three independent campaigns per comparison; pointwise 95\% intervals.}
\label{fig:filesystem-native-controls}
\end{figure}
\begin{figure}[t]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-native-warm.pdf}
\caption{Warm native traversals after the fresh-mount traversal. Points
compare each prepared version with original native; campaign intervals and
the distinct panel scales retain uncertainty in these shorter tasks.}
\end{figure}
\clearpage
\begin{figure}[t]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-stream-native.pdf}
\caption{Fresh native archive of the two 128 MiB files. Each prepared version
is paired with original native over three campaigns of eight blocks.}
\end{figure}
\begin{figure}[t]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-stream-native-warm.pdf}
\caption{Warm native archive of the same files on the same mounts. These
traversals benefit from filesystem caches populated by the fresh phase.}
\end{figure}
\end{document}
'''.replace('__CAMPAIGNS__',str(len(data['inputs']))).replace('__OBSERVATIONS__',f"{data['observations']:,}")
        if (a.figures/'filesystem-xz-detail.tex').exists():
            diagnostic=r'''\clearpage
\section*{Additional xz attribution}
Three additional campaigns (672 observations) examine the xz regression
identified in the main matrix. They use the same input and four tasks,
with all adapter controls, and are not pooled into the main estimates.
\begin{figure}[h]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-xz-attribution.pdf}
\caption{Additional xz adapter attribution. Ratios compare copied controls
with the old adapter on identical composed core instructions. LZ4 decoding
is unused by this xz image; the last two controls distinguish the presence
of the liblz4 dependency. Pointwise 95\% campaign intervals are shown.}
\label{fig:filesystem-xz-attribution}
\end{figure}
\input{tables/filesystem-xz-detail.tex}
'''
            supplement=supplement.replace(r'\end{document}',diagnostic+'\n'+r'\end{document}')
        if (a.figures/'filesystem-loader-detail.tex').exists():
            controlled=r'''\clearpage
\section*{Equal-loader-path application controls}
Nine additional campaigns (1,440 observations) execute all four tasks on
gzip, xz and lz4 SIFs. The frontend, bridge and core use hardlinks with equal
path lengths across reader variants. Four blocks per campaign use padding
0 and four use padding 16, in randomized order. Production binaries and
inputs are unchanged. These estimates remain separate from the original
matrix and the additional xz attribution campaigns.
Figure~\ref{fig:filesystem-sharing} compares the balanced backing estimates.
\input{tables/filesystem-loader-detail.tex}
\clearpage\subsection*{Padding 0}
\input{tables/filesystem-loader-padding-0.tex}
\clearpage\subsection*{Padding 16}
\input{tables/filesystem-loader-padding-16.tex}
'''
            supplement=supplement.replace(r'\end{document}',controlled+'\n'+r'\end{document}')
        if (a.figures/'filesystem-singlecpu-detail.tex').exists():
            single=r'''\clearpage
\section*{Single-CPU placement diagnostic}
Nine additional campaigns (1,440 observations) retain the same five backends,
three SIF codecs, four tasks and balanced loader padding. Application and
helper execution is restricted to CPU 1; the common outer launcher is retained.
This conditional comparison excludes cross-CPU application/helper parallelism
and does not replace the default two-CPU results. Live process affinities are
recorded in the untimed observations.
\begin{figure}[h]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-loader-padding.pdf}
\caption{Every loader-padding stratum for both CPU budgets. Each stratum
contains four paired blocks in each of three independent campaigns; intervals
are pointwise 95\% campaign intervals. No padding is selected for favorable time.}
\end{figure}
\input{tables/filesystem-singlecpu-detail.tex}
\clearpage\subsection*{Single CPU, padding 0}
\input{tables/filesystem-singlecpu-padding-0.tex}
\clearpage\subsection*{Single CPU, padding 16}
\input{tables/filesystem-singlecpu-padding-16.tex}
'''
            supplement=supplement.replace(r'\end{document}',single+'\n'+r'\end{document}')
        preview=prefix+supplement
    if (a.figures/'source-refinement-analysis.json').exists():
        data=json.loads((a.figures/'source-refinement-analysis.json').read_text())
        prefix=preview.split(r'\section*{Filesystem evaluation: complete results}',1)[0]
        supplement=r'''\section*{Filesystem evaluation: final-owner results}
\small
The final XZ-composed owner is evaluated in __CAMPAIGNS__ campaigns with
__OBSERVATIONS__ observations. The table retains all paired comparisons.
Absolute times are means of campaign medians. Ratios instead average paired
log ratios within each campaign and weight the three campaigns equally;
adjacent absolute times therefore need not divide to the paired ratio.
Intervals are pointwise 95\% Student-t intervals over campaign estimates.

O denotes original native, N the equally optimized normal native reference,
NR its relaxed-options counterpart, PL the preceding LZ4-composed owner, and
PX the final XZ-composed owner. SF and SF1 are the same squashfuse\_ll binary
with default and single-thread operation; SF+T adds the common translator.
C and V use identical common instructions with copied and kernel-shared
backing. L and LC are LKL512 with default and matched positive caches.
CL uses library decoders with both libraries present; CR uses common
decoders while retaining both libraries. Their separate diagnostic uses
equal-length loader paths. The single-CPU group is separate from the default
two-CPU application matrix.

\begin{figure}[h]\centering
\includegraphics[width=\textwidth]{figures/section65/filesystem-native-warm.pdf}
\caption{Warm traversals after the fresh-mount native task. These accesses
can bypass common-core work and are not the sole preparation-cost evidence.}
\end{figure}
\begin{figure}[h]\centering
\includegraphics[width=.9\textwidth]{figures/section65/filesystem-memory-scale.pdf}
\caption{Untimed metadata-scale observations after complete include archives.
The tree distribution is replicated with distinct inodes; SquashFS may
deduplicate file data. Each point is one separate process/mount observation,
not a population confidence interval or a whole-machine memory measurement.}
\end{figure}
\clearpage
\section*{Bounded diagnostic evidence}
\input{tables/filesystem-refinement-hardening.tex}
\input{tables/filesystem-refinement-work.tex}
\input{tables/filesystem-refinement-heap.tex}
\clearpage
\setlength{\LTcapwidth}{\linewidth}
\input{tables/filesystem-detail.tex}
\end{document}
'''.replace('__CAMPAIGNS__',str(len(data['inputs']))).replace('__OBSERVATIONS__',f"{data['observations']:,}")
        preview=prefix+supplement
    (PAPER/'filesystem-section-preview.tex').write_text(preview)
    print(json.dumps(dict(section=str(PAPER/'filesystem-section.tex'),source_datasets=len(provenance['sources']))))


if __name__=='__main__':main()
