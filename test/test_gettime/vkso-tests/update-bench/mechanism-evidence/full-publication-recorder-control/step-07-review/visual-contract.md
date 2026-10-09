# Visual contract: full-publication recorder matrix

Destination: evaluation evidence / supplementary quantitative figures, not a mechanism diagram or final manuscript layout.
Question: Does changing the recorder alter VKSO−Raw, and does the direction repeat across the two blocks?
Evidence: robustness and measurement limitations; no physical-cause claim.
Sources: report.json and histograms.csv; block 0 audit in ../step-03-review/block-audit.json, block 1 audit here.
Units: TSC ticks. One independent boot per cell per block; all periodic CPUs and tails retained.
Uncertainty: show both observed blocks, no confidence intervals or significance markers.

Figures:
- interaction.svg: four workloads, two block points; zero reference, exact labels. COARSE sign reversal stays visible.
- density-central.svg: four workload rows × two block columns; 0–1600 ticks, Gaussian σ=3, 1-tick bins, normalization by all samples.
- density-full.svg: same panels; log2 x-axis 64–16384 ticks, includes all nonzero smoothed support.
- ecdf-full.svg: same panels; log2 x-axis 64–16384 ticks, complete empirical CDF without truncation.

Curve encoding: Raw gray, VKSO blue; Current solid, Legacy dashed. Common y scale across blocks per workload.
Separate legend strip; font DejaVu Sans; white background. No external reference images, icons or data.
SVG retains editable text/paths; PDF exported from SVG; PNG for local visual inspection.
Exact ECDF points and displayed density arrays saved next to plots. All figure inputs remain unchanged.
Recipe basis: CCFA standard-library Canvas/Theme primitives, adapted to these empirical distributions.
Full-page evidence layout; final paper placement/size remains a later manuscript decision.
