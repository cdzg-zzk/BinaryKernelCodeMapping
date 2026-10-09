# Render QA

Figures are internal evaluation evidence, not a final venue-sized manuscript layout.

| Issue | Artifact | Fix / evidence | Status |
| --- | --- | --- | --- |
| Nearby value labels touched | interaction | Place both block labels above points; rendered PNG re-inspected | Resolved |
| Truncated display could hide tails | density-central | Full-range density, ECDF, and exact point CSVs accompany the central view; all-sample normalization | Resolved |
| Averages could hide COARSE reversal | interaction | Both block points and zero reference shown; no average-only plot | Resolved |
| Source/count mismatch | all | 32 histograms match per-boot counts; density mass sums to 1 and ECDF endpoints equal 1 | PASS |
| Text and panel boundaries | all four PNGs | Inspected actual renders; no clipped legends, axes or titles | PASS |

SVG text/paths remain editable; PDF is vector export through CairoSVG. Color uses gray/Okabe-Ito blue,
recorder identity uses solid/dashed lines; interaction blocks also have distinct markers.
Final manuscript sizing and grayscale print suitability require assessment at the chosen insertion size.
