# Improvement figure contract

Destination: operating-systems paper, quantitative figures with vector PDF/SVG
and a PNG inspection copy. No generated-image or decorative diagram is needed.
Source: complete `improvement/analyze.py` outputs and resource ledger; no pilot
point is a main performance result. Preserve raw source JSON and its hash beside
each figure. Primary intervals are campaign-level Student-t, pointwise 95%.

| Figure | Question and evidence | Panels and labels |
|---|---|---|
| Native preparation | What did the intervention change, and what remains relative to original? | Fresh include archive/scan, all five codecs; prepared before, bounded-copy-only, composed prepared; paired percent time change and intervals |
| Physical sharing | What changes only with physical backing? | All four application tasks, gzip/xz/lz4; VKSO/copied ratio with intervals |
| Full application | What is the complete cost against competitive existing alternatives? | Four task panels, absolute seconds; stock, copied, VKSO, LKL512 default and cache-matched; all three application codecs |
| Adapter ablations | Which internal changes help the same-core application? | gzip/lz4 panels, four tasks each; directory-only, direct-output-only, both with library LZ4, both with common LZ4; ratios to old adapter |
| Native optimized reference | Is bounded copying generally beneficial or adaptation-specific? | Three codecs, fresh scan; normal/optimized native and prepared comparisons, including relaxed optimized reference; separate from main matrix |
| Warm native | Does the cache-bypassing phase agree or remain less informative? | Same five codecs and three prepared variants as main; appendix, no use as sole core-overhead evidence |

The main application figure omits diagnostic variants only from bars for
readability; the full paired table retains every planned cell, including
stock-with-translator, all ablations and adverse tasks. Source snapshots contain
per-campaign ratios and absolute times. No figure omits negative outcomes.

Style follows existing paper figures: VKSO/composed orange-red (#D55E00),
copied/bounded-copy blue (#0072B2), old/stock gray, LKL green/black, with marker
shape or hatch redundancy. Use zero-baseline bars for seconds and explicit
one/zero reference lines for ratios/percent changes. Do not clip intervals.
Separate panel scales are labeled; fonts remain readable at full text width.
Inspect rendered PNGs and the compiled manuscript for clipping, legend overlap,
caption placement, cross-references and traceability before delivery.
