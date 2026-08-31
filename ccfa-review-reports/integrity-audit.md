# Integrity Audit: VKSO Manuscript

## Mode

Full claim, numeric, figure/table, terminology, and citation audit of `paper/paper_content/Paper Draft.md` against repository evidence.

## Claim-evidence matrix

| Claim | Manuscript location | Evidence | Status |
|---|---|---|---|
| Resident page grafting does not add measurable hot-path cost | Abstract; Evaluation first-touch | First-touch report and `first_touch_latency.svg` | Supported within the measured Linux 5.15.0-119 setup |
| Same-source algorithms remain close to native user builds | Abstract; LZ4/BCH/XZ sections | Component benchmark reports and generated SVGs | Supported, with XZ −1.61% and BCH outliers retained |
| Clocktime READ aggregate is +0.941% Normal and −0.275% no-retpoline | Abstract; clocktime section | `VKSO_READ_UPDATE性能报告_20260801.md`, READ archive | Supported |
| UPDATE mean improves 13.176% and 4.111% | Clocktime section | Final UPDATE report, Table 4 in report | Supported after precision correction |
| Concurrent writer mean improves 1.95%–12.20% | Clocktime section | Final concurrent report | Partially supported: range is the no-retpoline point-estimate range; Normal has a different 3.16%–10.73% range and must remain labeled |
| Complete product source decreases 13.29% and reader closure 22.13% | Abstract; Table 3 | Final performance report M11 scope | Supported only for the complete-product scope |
| Narrow intrinsic audit is 1,201→1,102 SLOC and 2,497→2,401 B | Source-footprint note | `VKSO开发工作量与代码规模评估_20260728.md` | Supported as a separate scope |

## Numeric consistency findings

- The manuscript now uses the precise UPDATE values `13.176%` and `4.111%` from the final report.
- Table 3 and the abstract use the complete-product scope (1,505/1,305 SLOC; 2,639/2,055 B). The text immediately below Table 3 discloses the narrower intrinsic scope and explains why the two scopes are not additive.
- The reader-closure percentages are arithmetically consistent: `(2639−2055)/2639 = 22.13%`; `(2497−2401)/2497 = 3.84%`.
- The source percentages are consistent: `(1505−1305)/1505 = 13.29%`; `(1201−1102)/1201 = 8.24%`.
- Concurrent coarse-path percentages are large because the absolute baseline is about 10 cycles; the manuscript retains this interpretation rather than calling the path universally slower.

## Figure and table consistency

- `generate_figures.py` regenerated 11 SVGs without error.
- The generator checks the primary clocktime tokens and code-size labels. Generated files include `clocktime_performance.svg`, `clocktime_code_size.svg`, `first_touch_latency.svg`, `pgot_primitive_costs.svg`, `pgot_real_closures.svg`, and the LZ4/BCH/XZ component plots.
- Captions state units, direction of favorable deltas, and error-bar summaries for the generated charts.
- The manuscript's standalone figure-label lines are readable in Markdown but should be converted to actual figure inclusions in a submission layout.

## Citation metadata and context

- All unresolved `\\cite{}` commands were removed; the manuscript now uses numbered Markdown references.
- Public source checks completed for FlexSC (USENIX OSDI 2010), Privbox (USENIX ATC 2022), Rump File Systems (USENIX ATC 2009), LKL (IEEE RoEduNet 2010), and Linux `vdso(7)`.
- The added Privbox entry is reference 35 and its URL matches the USENIX presentation page.
- The manuscript has no `.bib` file. This is consistent with the current Markdown format but is a conversion risk if the paper is later moved to LaTeX.
- General claims about Windows, macOS, and FreeBSD substrates are supported by the linked vendor/kernel documentation entries, not by peer-reviewed papers; label them as documentation-backed system facts in a future venue version.

## Terminology findings

- Canonical terms are now `reuse contract`, `rehostable closure`, `page grafting`, `Shim`, `kernel-published state`, and `address-space-local context`.
- Headings were normalized to `General-Purpose`, `Fail-Closed`, and `PIC-Compatible` forms.
- One residual stylistic issue is mixed `first-touch`/`first touch` and `page-fault`/`page fault`; this is non-blocking but should be normalized in the next writing pass.

## Severity and safe edit suggestions

- **Blocking:** none for the currently claimed numbers, provided the complete-product and narrow scopes remain explicitly labeled.
- **Major:** add repository-relative links or an appendix map from each headline number to the exact report/archive path before submission.
- **Advisory:** convert the Markdown reference list into a verified `.bib` file only if a LaTeX submission version is created; do not silently infer missing metadata.

## No-invention status

No new experimental result, baseline, citation, or reviewer conclusion was invented. The only new reference is Privbox, verified against the USENIX source page. The manuscript edits are limited to organization, wording, citation rendering, precision, and explicit disclosure of already existing evidence scopes.

## Next owner

`ccf-paper-writer` for the major audit action, then rerun this audit before any venue-specific submission check.
