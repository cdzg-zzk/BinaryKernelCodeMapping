# End-to-end kernel-function microbenchmarks

Common variants:

- native
- data-PGOT
- function-PGOT
- all-PGOT

Common build modes:

- no-ret
- ret

Common output:

- TSC cycles per call
- PMU cycles per call
- instructions per call
- branch misses per call

Kept candidate functions under the helper-only function-PGOT rule:

1. SHA-256: K/padding data; external memory helpers.
2. BCH encoding: `swap_bits_table`; `memcpy` and `memset`.
3. LZ4 decompression: offset-copy tables; `memcpy` and `memmove`.
4. zlib-deflate: configuration/Huffman tables; external memory helpers.
5. Zstandard decompression: FSE/default decoding tables and external memory
   helpers; kept as a backup candidate.

Only calls crossing the copied closure boundary are transformed by
function-PGOT. Internal algorithm calls remain direct.
