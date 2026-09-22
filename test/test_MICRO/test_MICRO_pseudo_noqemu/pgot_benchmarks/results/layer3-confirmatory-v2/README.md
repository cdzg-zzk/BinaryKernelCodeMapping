# Layer-3 PGOT confirmatory campaign

Formal measurements are complete: 64 module loads, 2,400 paired records,
four fixed workloads, both builds, all applicable ablations. See
[the methodology and reproduction guide](../layer3-fixed-batch-v2/README.md),
[final assessment](FINAL-ASSESSMENT.md),
[mechanism evidence](MECHANISM-EVIDENCE.md), and
[the two-panel figure](figures/ablation.pdf).

Every original load is retained, including BCH no-retpoline load 6. The paper
prose has not been changed. `source/` is the immutable collection-time snapshot;
`../layer3-fixed-batch-v2/analysis-source/` records final analysis and reproduction
scripts. Builds retain their actual objects, verbose commands and generated C.
