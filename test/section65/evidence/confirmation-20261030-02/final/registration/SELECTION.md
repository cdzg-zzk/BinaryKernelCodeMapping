# Candidate decision before confirmation

The 16-slot pilot improves Python/XZ by 9.03% against the old private adapter,
but LZ4 stream costs 8.91% more. Instrumented streams find no additional cache
hits. A single-buffer admission rule based on file size does not solve that
tradeoff: its LZ4 stream point is +6.98%, while Python improves only 1.85%.
That candidate is rejected. Its gzip scan +10.46% elapsed result has nearly
unchanged CPU samples, but remains in the record; no samples are discarded.

Select the already specified 48-slot candidate for confirmation after its
correctness gates. This is an explicit revision of the preference for 16,
not an additional capacity search. Its original pilots show Python/XZ −11.29%,
LZ4 stream +2.64%, and no >5% regression against the old adapter across the
fourteen ordinary/Python cells. As a control in the second pilot it again
improves Python/XZ by 10.91%. These are descriptive development observations,
not confirmatory intervals or a guarantee of no regression.

The cost is a lazy private data budget of 48 × 128 KiB = 6 MiB, matching the
data-slot count of the multithread-built stock backend. Fragment slots remain
3, not stock's 48; the policies are not fully equivalent. The measured 16x
copied PSS is 25,999 KiB versus default stock 31,557 and stock-single 13,237.
Thus this choice improves the time/memory tradeoff relative to the old
unbounded adapter but does not minimize memory among all backends. No claim
of cost-free optimization, constant process memory, or universal superiority
is intended. The stream-admission rule and tree-unrolling decoder are excluded.

Freeze the same owner/native consumer plus this private adapter. Retain the
four completed native campaigns only after binary and runner identity checks;
finish their two missing campaigns. Rerun every affected user campaign with
three repetitions of the registered campaign protocol. Add old copied only
to the ordinary and Python cells as a direct cache-policy ablation, retaining
all existing baselines and inputs: 30 campaigns, 8,172 observations in the
final analysis, including 2,688 reusable native observations and 5,484 new
observations. Pilot data never enter those intervals. Stop after the fixed
matrix regardless of the direction or significance of the results.

Existing normal/relaxed native controls, hardening limitations, same-boot
inference, source-maintenance boundaries, and deployment accounting remain.
Large-file random-read throughput and concurrent throughput are not newly
claimed. Any final adverse cells are reported with their uncertainty.
