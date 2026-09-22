# Visual contract
Artifact: two-panel ablation bar chart for a double-column systems paper.
Question: how do data and helper adaptation appear in the complete routine?
Panels: no retpoline; inline retpoline. Within-build Origin is the zero baseline.
Source: ../ablation.csv and ../outer-runs.csv, regenerated from raw measurements.
Bars: median of module-load overhead estimates. SHA has Data only; missing bars
are inapplicable, never numerical zeros. Gray fills and hatches encode variants.
Uncertainty: confirmatory 95% percentile bootstrap over 8 module loads; archive
range of its 3 module-load estimates. Dots retain every outer-run estimate,
including the BCH outlier. No truncation, decorative images, or external assets.
Outputs: vector PDF, 300 dpi PNG, exact bar and dot CSVs, Python source.
Manuscript placement: standalone artifact; paper prose is not edited.
