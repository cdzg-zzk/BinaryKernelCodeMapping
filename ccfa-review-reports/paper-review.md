# Assessment-only Review: VKSO

## Mode and assumptions

Full scientific and writing review of `paper/paper_content/Paper Draft.md`. No target venue or LaTeX template was supplied, so the review uses a generic CCF-A systems standard. The review does not rewrite manuscript text.

## Paper summary

VKSO proposes rehosting resident kernel machine-code pages as a standard user-space shared object. A reuse contract constrains state, control flow, and code shape; a carrier and page grafting preserve ELF object semantics while rebinding selected pages to resident kernel pages; Shim and private bindings supply domain-local dependencies. The evaluation covers first-touch behavior, PGOT and copied closures, LZ4/BCH/XZ components, and a Linux clocktime case study.

## Quantitative scorecard

| Dimension | Score (1–5) | Confidence | Evidence basis | Deduction and repair condition |
|---|---:|---|---|---|
| Contribution and novelty | 4 | medium | Clear function-level resident-binary rehosting boundary and explicit state/control/code-shape contract | The closest prior-art boundary is still described mostly by category. Add a direct comparison against the nearest binary-reuse or kernel-code-sharing systems to reach 5. |
| Significance and impact | 4 | medium | Addresses duplicate kernel/user implementations and syscall cost; clocktime demonstrates a stateful case | Scope is Linux/x86-64 and build-specific. A sharper workload-selection rule would strengthen general impact. |
| Technical soundness | 3 | medium | Contract, PIC handling, page lifetime, permissions, and fail-closed validation are specified | The manuscript states manager checks and security properties but does not expose a complete formal manifest schema or failure matrix. Include one concrete manifest example and enumerate rejection conditions. |
| Evidence and evaluation | 4 | high | Multiple mechanism and end-to-end experiments with matched-run statistics and negative results retained | First-touch and component data are well described, but the raw result paths are not linked from the manuscript and no compact numerical table covers all component medians. Add artifact pointers or an appendix table. |
| Clarity and organization | 4 | high | Mechanism-first Design and question-oriented Evaluation are recoverable | Terminology remains mixed Chinese/English and several captions are standalone labels. Normalize terms and attach every figure label to a rendered asset. |
| Positioning and related work | 3 | medium | Covers shared objects, LKL/Rump, vDSO, syscall optimization, and kernel bypass | WinVFS was removed as an unsupported named claim, but the related-work section still needs one direct paragraph on binary-level reuse and loader rebinding. Add verified primary citations or narrow the claim. |
| Reproducibility and auditability | 4 | high | Reports identify kernel, compiler, CPU, repetitions, manifests, and figure generator | The Markdown manuscript has no machine-readable bibliography and does not link each number to a source file. Add a short artifact map or repository-relative links. |
| Ethics, limitations, and responsible research | 4 | medium | Threat model, permission boundary, page disclosure, side channels, and build identity are explicit | The security discussion is scoped to the prototype. State which permission tests were actually executed versus design requirements in an artifact note. |

Overall stance: **borderline accept after a focused revision**. The mechanism and evidence package are promising, but a top systems venue would likely request stronger nearest-work positioning and a more inspectable manifest/security validation example.

## Major concerns

1. **Binary-reuse novelty boundary.** The paper claims a combination of final-binary closure, resident backing, and explicit environment binding, but does not compare against the closest binary translation, kernel-code sharing, or loader-rebinding systems. Repair condition: add a verified comparison table with mechanism granularity, whether a second execution body is created, state handling, and call-path cost.
2. **Manifest and runtime validation remain descriptive.** The Design and Implementation sections state fail-closed behavior, but a reviewer cannot reconstruct the exact manifest fields or the order in which runtime checks reject a page. Repair condition: include one representative manifest excerpt and a short acceptance/rejection trace tied to the page-map evidence.
3. **Scope of code-size claims.** The manuscript now reports the complete-product 1,505/1,305 SLOC and 2,639/2,055 B scope and separately discloses the narrower 1,201/1,102 and 2,497/2,401 audit. Repair condition: preserve both labels in every future table or figure; never quote the percentage without its scope.

## Writing and presentation concerns

- Mixed-language terminology is acceptable for this draft format but should be normalized before venue submission, especially `first-touch`, `first touch`, `file-backed`, and `page-fault`.
- Figure captions are present, but several standalone lines such as “Clocktime performance” and “Resident kernel-code rehosting architecture” should be rendered as figure labels or removed in the final layout.
- The prose-quality check reports one uniform-sentence warning; no em-dash limit violation remains.

## Concern-to-action table

| Concern | Severity | Evidence | Owner |
|---|---|---|---|
| Nearest binary-reuse comparison is thin | Major | Related Work paragraphs 401–405 | `ccf-paper-writer` + `ccf-literature-searcher` |
| Runtime manifest schema not inspectable | Major | Implementation paragraphs 163–217 | `ccf-paper-writer` |
| Dual code-size scopes could confuse readers | Major | Evaluation paragraph 361 onward | `ccf-integrity-auditor` + `ccf-paper-writer` |
| Standalone figure labels | Advisory | Evaluation captions | `ccf-visual-composer` |

## Checks run

- `check_prose_quality.py`: 0 em-dash errors; one uniform-sentence warning.
- Figure generator: 11 SVG figures regenerated successfully.
- Numeric token scan: primary and narrow code-size scopes both present; no unresolved `\\cite{}` keys.
- Public source verification: USENIX pages for FlexSC, Privbox, and Rump; Linux `vdso(7)`; IEEE record for LKL.

## Unresolved or unverified

- No target venue, page budget, or LaTeX template was supplied.
- The manuscript's numbered references are Markdown entries rather than a `.bib` database; metadata is manually listed and should be checked before LaTeX conversion.
- The review does not claim a complete novelty search for all binary-reuse systems.

## Recommended next owner

`ccf-paper-writer` should address the three major concerns, followed by `ccf-integrity-auditor` for a full claim/numeric/citation audit.
