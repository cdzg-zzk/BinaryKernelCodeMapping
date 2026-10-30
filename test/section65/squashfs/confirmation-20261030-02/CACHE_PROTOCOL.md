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
