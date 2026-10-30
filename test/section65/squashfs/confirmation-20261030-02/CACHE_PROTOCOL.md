# Private data working-set follow-up

The complete three-campaign Python decoder contrast shows common-retained /
library time +2.599%, but library / stock +13.008%. Three instrumented full
compilations produce identical 647-file output and repeat exactly 352 decodes /
37,602,020 output bytes for the common parser versus 243 / 26,999,864 for stock.
Changing only FUSE keep-cache-on-open leaves those counts unchanged.

The private cache request trace has 190 data requests / 97 unique blocks,
654 fragment requests / 98 unique blocks, and 153,954 metadata requests /
12 unique blocks. The production data cache inherits one native scratch slot
through max_decompressors=1, while the stock multithread build has 48 data and
48 fragment slots (also retained when launched with -s). Native kernel pages
and FUSE application access are different caching environments.

Test exactly two private data-cache candidates: 16 slots (2 MiB at 128 KiB
blocks) and 48 slots (same data capacity as stock). Buffers allocate lazily;
metadata remains 8 FIFO slots, fragments 3, inode/name LRU 2048/4096. No other
policy, decoder, frontend, translator, image, thread or compiler change.
The owner and native consumer stay byte-identical. This changes private data
memory, which must be measured, not described as free acceleration.

Before promotion, run actual five-format native/copied/shared checks and the
existing private-adapter sanitizer/lifetime path. Four-block full-task pilots
cover all original gzip/xz/lz4 application tasks and gzip/xz Python compilation.
Compare stock, stock-single, old copied, each candidate copied, candidate
shared and both LKL configurations. These are pilots, excluded from inference.
Retain all results. A >5% unchanged-task point regression triggers investigation.

Prefer the 16-slot candidate only if it reduces Python/XZ full-task point time
by at least 5% versus old copied, keeps the 16x metadata-scale PSS below default
stock, and passes correctness/lifetime checks. The 48-slot row explains the
time/memory tradeoff, not an implicit substitute for the smaller candidate.
If the criterion is not met, review the measured tradeoff explicitly; do not
try further capacities or omit adverse workloads. The tree-unrolling candidate
is separate and not silently combined with these cache controls.

After selection, freeze the bridge and confirm the original application matrix
with three independent campaigns. Unchanged owner/native timing is reusable
only with byte identity and the original native protocol; finish its missing
registered third campaign rather than relabel private-adapter samples as native.
The old 14-campaign closeout remains a separate historical analysis. No claim
of no memory cost, universal superiority or net machine savings follows.

## Streaming admission follow-up (before final promotion)

The first full pilots retain an LZ4 stream regression of 8.91% for copied
16-slot versus old copied. The 16-slot Python/XZ point improvement is 9.03%.
The original three memory scales meet the default-stock criterion but still
exceed stock-single at 16x. These observations do not permit promotion yet.

An instrumented replay of each original stream finds the same 1,027 decoder
calls and 2,052 cache misses for 1/16/48 data slots. The larger working set
therefore adds no hits in that task. Diagnostic elapsed/counter timings are
not formal samples and do not establish an exact hardware cause.

One admission candidate retains the 16-slot cache for files fitting its byte
budget and uses one reusable scratch slot for files larger than that budget.
The threshold is cache capacity, independent of codec and test filename.
This adds at most one block buffer and its actor to private memory. The native
owner, instructions, decoder and native consumer remain byte-identical.
Do not tune additional capacities or thresholds against the results.

Before selection, validate five-format content/PFNs, private-adapter sanitizers
and real FUSE handle/cursor lifetimes. Replay the three existing ordinary
application pilots and Python/XZ with the original stock, LKL, old copied and
48-slot controls, four blocks each (416 observations). Preserve all cells.
Use the same >5% regression investigation rule and Python/memory criteria.
If selected, remeasure resource scales and rerun the full affected application
confirmation; pilot samples remain outside formal inference.
