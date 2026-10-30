# Improvement decisions and retained evidence

These are diagnostic and pilot findings, not replacements for formal campaigns.

## Native copy boundary

`.../runs/iso9660/squash-native-service-counts-01` finds exactly the same
1,267,721 copy/cache calls for original and prepared scans in gzip/lz4/xz.
Input-byte calls are only 162 and uid/gid updates 5,865 each.
`squash-native-copy-sizes-01` additionally finds 673,396 requests of eight bytes;
the complete histogram is retained per format/domain. Request lengths exclude
null destinations and are not asserted to equal cross-page chunk lengths.

`improve-native-copy-02` was rejected before execution because a generic builtin
introduced an external memcpy dependency. The forced-inline candidate 03 kept
the dependency closure and passed all 25 functional mounts, but fresh scan
regressed 47.6–64.3% versus original in its five-format pilot. Its sampled
copy_data share rose to about 35%; gzip kernel cycles rose from 165.7M to
269.7M despite fewer retired instructions. Both final and loop copy sites used
rep movsq. The original kernel uses a direct __memcpy call for the final copy,
so the earlier observation that original also contains rep movsq did not imply
that the same common path used it. Preserve this rejected build and all data.

The next candidate (`improve-native-small-copy-01`) uses bounded constant
loads/stores for at most 16 bytes, with no overread and the original service
fallback for larger copies. It retains one core for both domains. All five
formats/25 mounts and PFN/restore/unload passed. Its five-format pilot returns
fresh scan to near original time; this is a candidate for formal paired
before/after campaigns, not a completed speed claim. PMU diagnostic gzip kernel
cycles: original 165.8M, candidate 163.4M; instructions 356.5M and 372.8M.
These distinct campaign medians are diagnostic, not subtraction-based overhead
estimates.

## User adapter ablations

Directory-handle caching lowers include workload frontend enumerations from
38,318 to 6,425; direct decoding removes the compressed-output scatter while
retaining uncompressed-input and cache-to-request copies. For the 256 MiB task,
about 128 MiB of scatter is removed. The temporary decoder output allocation
is retained to isolate copying; no memory saving is attributed to this step.
All three codec task outputs and five-format combined functional checks pass.

`squash-user-ablation-{gzip,xz,lz4}-pilot-01` compares stock, old copied,
directory-only, direct-only, combined copied and combined VKSO with two blocks.
End-to-end improvements are modest and some cells regress; retain all twelve
tasks and collect sufficient independent campaigns. No zero-copy or broad
application-speed claim follows from internal counters alone.

## Simultaneous consumers

`squash-simultaneous-01` failed at import before any module was loaded.
Round 02 correctly detected that native and Apptainer archives do not preserve
identical uid/gid: Apptainer supplies uid/gid=1000 FUSE mount overrides. The
revised check models that explicit application behavior and still checks
image-specific content, mode, timestamp, hardlinks, symlinks and range reads.
Round 02 cleanup initially left the native module in use by orphaned
fuse-overlayfs namespaces. The two identified FUSE readers and two overlay
helpers were terminated and both modules were successfully unloaded. The
runner now tracks its own descendants for cleanup; historical failed result
remains unchanged.

## Resource route

`resource-inventory.json` records allocated ELF sections, not resident memory.
The baseline's 24 KiB physical sharing did not establish net deployment savings.
The full Section 6.3 LZ4 owner includes compression and unused decoder APIs;
importing it wholesale would add an extra module/descriptor and unneeded code.
A bounded integration candidate will reuse its adapted safe block decoder in
the existing SquashFS owner, with explicit private memory helpers in each
domain. This can remove the user bridge's liblz4 dependency without adding a
second registration facility. It still requires measured code-page and module
residency accounting; neither file size nor extra exported pages is a net
memory result. Five formats remain supported; only LZ4 codec implementation
changes. The dependency/interface change also supplies a concrete maintenance
workflow case, including required bridge rebuild and redeployment costs.

The composed candidate passed five-format hardware tests (25 mounts), then
`squash-codec-guest-regression-01` passed the malformed-input repair and full
five-format native/copied/shared regressions. The candidate native negative-offset read returns EIO; user backends also return
EIO and remain alive. This matches the retained repaired baseline guest outcome;
internal short-copy handling is not itself an application read result. The additional codec bindings are private and all seven code/RO
pages share physical backing. `squash-composed-native-call-counts-01` confirms
the prepared LZ4 mount actually calls the common safe decoder; gzip/xz do not.

The LZ4 composition pilot compares the same composed owner with user-lib-LZ4
versus common-core decoding, under the same directory/direct-output adapters.
The four-block copied stream ratio is about 0.971; startup/scan/archive are
about 1.006/1.010/1.005. These are pilots, not confidence-backed final claims.
Owner reported residency is 56 KiB versus 52 KiB before; consumer remains
40 KiB and registration 32 KiB. An observed 48 KiB helper RSS reduction from
removing liblz4 is not a whole-machine saving. Formal resource snapshots now
precede PFN/debugger page touches, and will include per-mapping smaps records.


## Final measurement and interpretation controls

The first three complete native campaigns retain 2,880 observations. Compared
with the repeated previous prepared version, the composed version lowers fresh
include scans by 3.57–4.94% across five codecs, with all five primary intervals
below equal time. Its point estimates against original native are near/below
one. These results do not isolate service-indirection cost: the same bounded
copy is also being applied to unadapted normal/relaxed native controls before
interpreting the residual preparation difference.

The copy-entry histogram contains 1,203,880 requests of at most 16 bytes among
1,267,715 non-null requests (94.9646%). This is a request-length statistic,
not a claim about all actual cross-page chunks. In the gzip include archive,
output-scatter bytes fall from 36,279,697 to 204 with direct output; values for
other codecs remain in their own records and are not substituted into that cell.

Before the final composed-core simultaneous run, the runner now records user
start/done file timestamps and native task timestamps, launches the native task
after user task-start markers, and requires at least one observed A/B/C task
lifecycle overlap per backing variant. This measures overlapping task envelopes,
not sampled simultaneous instructions or throughput. Earlier simultaneous runs
remain unchanged. The final native-control runner also records actual loaded
module sizes outside timing, so optimized reference residency is observable.

## Additional xz attribution and loader controls

All main 18 campaigns (7,776 observations), final simultaneous/deployment
checks, optimized-native references and native stream reruns completed.
The xz extension adds three campaigns (672 observations). Its direct-only
and both-adapter/library controls do not reproduce the complete copied
stream slowdown; complete copied/library is +4.148% [3.416%, 4.886%]. The
same VKSO binary also changes relative to copied across these contexts.
Thus neither direct output nor page sharing has been identified as the cause.

`squash-path-layout-01` varies only path spelling for hardlinks to identical
files and records altered private allocation offsets. The 40 mounted archive
observations have median times 0.3475--0.3506 s across five paddings. This
less-than-1% spread does not explain the full-application 4--5% difference.
The diagnostic uses fresh mounts and warmed backing, not Apptainer lifecycle
timing. Its first pilot failed because GDB lacked the external DWARF types;
the second loads the existing types object and passes. No timing exclusions
or production changes follow from this diagnostic.

The next finite matrix therefore directly equalizes loader path lengths in
the actual application, balancing two padding levels. The first runner pilot
found that registration makes the carrier immutable and prohibits new
hardlinks. It restored and unloaded successfully; its failure is retained.
The corrected runner creates shared aliases before registration. Copied and
shared resource snapshots then have equal image/filesystem/stream page
offsets. Production frontend, bridge, owner and copied instruction bytes
remain unchanged. Three campaigns per codec are evaluated separately from
the earlier estimates; unexplained context sensitivity remains a limitation.

The first full analysis queue failed under root's Python because NumPy was
unavailable. Its dependent xz queue stopped without starting experiments.
The restarted queue uses the retained plotting venv executable without
resolving its symlink, preserving that environment. Both failure logs and the
successful independent numerical replays remain in the run directory.

## Completed loader controls and bounded placement diagnostic

The nine equal-loader-path campaigns and their independent audit are complete
(1,440 observations, 96 balanced comparisons and 192 padding-stratum comparisons).
xz VKSO/copied stream becomes 1.0021 [0.9905, 1.0138]; complete copied/library
still regresses 4.00% [3.34%, 4.67%]. lz4 copied/library stream is +0.60%
[-0.38%, 1.59%], so the primary decoder-build speedup is not robust across
these contexts. Neither result is substituted for the original estimate.

gzip scan/stream paired intervals remain broad. The raw campaign-2/block-1
copied stream consumes 0.569 CPU seconds in 0.456 elapsed seconds, versus
0.565 CPU seconds in 0.621 elapsed seconds for VKSO. Other scan delays also
occur without similar CPU-work changes. The fixed single-CPU extension in
the protocol tests placement sensitivity with the same five variants and
all tasks/codecs. It keeps every prior sample and has no further extension
condition based on a favorable result. Its precheck confirms CPU 1 affinity
for every observed application/helper process; the common outer runuser
launcher remains outside that taskset boundary.

The first single-CPU queue stopped at argument parsing because a manifest
string replacement also renamed `--equal-loader-paths`. No experiment output
directory or sample was created. The failed queue/log is retained; the corrected
second queue uses the existing flag and a separate `--cpus 1` argument.

The claim ledger now explicitly distinguishes a general adoption advantage
over copied (not established) from resident physical reuse (observed). Copied
also receives common-adapter performance and repair benefits and can execute
after all task modules unload. This distinction is required by the actual
cost evidence, not a removal of an inconvenient result.

## Final placement results and completion

The fixed nine-campaign single-CPU extension is complete: 1,440 observations,
96 balanced comparisons and 192 padding-stratum comparisons, independently
recomputed. Observed application/helper affinity is CPU 1; the common outer
runuser launcher remains outside the taskset boundary. No observation is
excluded and no further measurement extension is selected for significance.

For nonempty tasks, VKSO/copied point ratios are 0.9927–1.0062 and pointwise
interval endpoints span 0.9684–1.0308. The complete adapter's metadata point
reductions relative to the old adapter are 0.77–2.93%; five of six intervals
exclude equal time. xz stream remains 4.92% [3.87%, 5.98%] slower than the
library control. lz4 complete/library stream is +0.58% [-0.38%, +1.56%], so
its primary-context speedup is not robust across the extra contexts. These
conditional results are reported alongside every original two-CPU estimate.

The complete improved record is 39 campaigns / 11,328 timed observations,
with main, xz-attribution, equal-loader-path and single-CPU analyses kept
separate. Final prose, figures and the full 1,002-row appendix retain negative
results and scope limits. The canonical section's selected numerical claims
are independently checked against source analyses. The preceding baseline
publication and all runner failures remain preserved.

## Installed-platform business scope and application motivation

The user clarified that page_cache_replace is shared platform infrastructure,
not a new LKM specific to this filesystem. The main cost model now assumes
that platform is installed and excludes its one-time 32 KiB from business
subtotals. `business_costs.py` derives the business ledger from the unchanged
resource observations; owner/consumer preparation, per-core metadata and
private runtime remain included. Full deployment records retain the platform
cost once. This replaces the earlier per-case allocation of all infrastructure
as the primary premise, not the actual observations or their historical scope.

The section now explicitly connects the motivation to executed SquashFUSE
and LKL application comparisons, with Rump as cited context and copied as
an attribution control. Existing xz losses and loader/CPU sensitivity remain.
The measured helper footprint is a complete-backend resource result; physical
sharing is independently established by PFNs. Common maintenance is not
presented as unique to VKSO or as measured developer-time reduction. This
change affects interpretation/prose/derived accounting only, not the formal
binaries or samples, so no timing campaign is rerun.
