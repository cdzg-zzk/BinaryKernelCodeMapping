# Final-owner decisions and limits

The 30 completed confirmation campaigns contain 6,540 observations. The
independent replay checks all 403 paired comparisons. Three separate resource
runs cover 5,866/23,464/93,856 entries. The interrupted campaign's 28 partial
observations remain separate; the whole same-parameter rerun supplies its
confirmation cell. No completed-campaign sample is discarded.

## Reuse extension accepted with its measured tradeoff

Common XZ adds 2,604 unchanged algorithm lines and raises the owner executable
text from 16,695 to 27,828 bytes. Native call counts, actual SIF breakpoints,
private bindings and nine shared pages establish execution, not dormant code
inclusion. This implements the protocol's functionality/reuse-based selection;
it was not selected for a favorable performance result.

The final native xz sequential task is 1.90% faster than the preceding
LZ4-composed owner, but the complete user xz sequential task is 13.10% slower
than default SquashFUSE. Held-out xz Python compilation is 16.18% slower than
default SquashFUSE and 6.72% slower than matched-cache LKL. These losses remain
in the main text and plots. The held-out task limits general application-speed
claims; it is not replaced by another task.

The same-owner, equal-path diagnostic retains both external dependencies and
switches library decoding to common decoding. Its xz stream time increases
14.79% [13.43%, 16.16%], and measured child CPU time increases 14.87%.
Removing unused dependencies with common decoding held fixed changes time by
-0.51% [-2.45%, 1.47%]. Matching outputs and controls reveal no input/semantic
mismatch. This isolates a decoder-execution tradeoff, not a physical-sharing
penalty. It does not establish an inner-loop cause or a pure service-call cost.
Rewriting the upstream decoder to chase this result would change the reuse
experiment; the retained library control documents the alternative.

## Stock threading materially changes the comparison

Default SquashFUSE metadata tasks favor the complete backend. Against the
same stock helper with `-s`, gzip/lz4 include archives instead cost 1.18%/0.89%
more, and their scan point estimates are close. The xz scan remains 53.59%
faster. Three untimed work-count replays show stock decodes 137 blocks and
1,106,363 bytes, versus 76 blocks and 558,231 bytes with the common parser.
The stock single-thread replay has the same decompression work as default.
Thus threading explains much of the gzip/lz4 metadata difference; reduced
decoder work contributes to xz behavior without a complete causal partition.

## Compact memory is conditional on metadata population

The bridge's `u_new_inode` allocates cached inode objects, `sq_lookup_child`
retains cached names, `u_inode_noop` does not release references, and `sq_close`
frees the lists at unmount. Source inspection and the scale ladder identify a
deliberate retained-cache policy, not shared mutable kernel objects or a
cross-domain page leak. Final helper PSS grows from 7.02 to 23.43 to 88.89 MiB.
At the largest scale it exceeds default/single-thread SquashFUSE's 28.52/12.91
MiB, while matched-cache LKL retains 500.92 MiB. A generally smaller user
runtime is therefore unsupported. Bounded eviction would require new inode,
name and open-handle lifetime rules and corresponding performance validation;
it is not presumed present in this evaluated implementation.

## Scope of the positive result

Both domains execute a larger shared body with independent state. Default
metadata tasks, gzip/lz4 sequential access and the measured small-tree helper
footprint show useful conditional effects; final native costs and sharing
increments have explicit intervals. All twelve ordinary tasks beat the chosen
matched-cache LKL configuration, but the independent xz task does not.

Generic platform residency remains outside the filesystem subtotal as requested.
The native owner/consumer increment is 48 KiB over the matched module reference,
whereas an already prepared native service avoids one 36 KiB copied backing.
Neither quantity alone is a whole-machine balance. Current shared code also
does not retain native canaries/thunks; the build-only PIC probe distinguishes
compiler feasibility from an implemented cross-domain hardening ABI.

No additional workload, layout or optimization is selected after confirmation
to remove these unfavorable outcomes. The preceding publication and every
failed candidate remain available under their own implementation identities.
